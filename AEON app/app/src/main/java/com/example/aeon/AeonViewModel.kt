package com.example.aeon

import android.app.Application
import android.content.Context
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.aeon.audio.WavPlayer
import com.example.aeon.audio.WavRecorder
import com.example.aeon.model.HubSnapshot
import com.example.aeon.net.HubClient
import com.example.aeon.net.HubDiscovery
import com.example.aeon.net.LanNetwork
import com.example.aeon.net.SarvamClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

enum class Mic { Idle, Listening, Thinking }

/** How long a spoken sentence waits for the socket before it is given up on. */
private const val LINK_WAIT_MS = 5000L
private const val LINK_POLL_MS = 150L

data class UiState(
    val linked: Boolean = false,
    val linkNote: String = "not connected",
    val mic: Mic = Mic.Idle,
    val heard: String = "",
    val notice: String? = null,
    val snapshot: HubSnapshot? = null,
    // Kept in state so the socket can be reopened, never rendered. The address
    // is discovered, not configured -- see AeonViewModel.locate().
    val host: String = "",
    val port: Int = 8800,
)

class AeonViewModel(app: Application) : AndroidViewModel(app) {

    private val prefs = app.getSharedPreferences("aeon", Context.MODE_PRIVATE)
    private val sarvam = SarvamClient()
    private val player = WavPlayer(app)
    private val recorder = WavRecorder()

    private val _ui = MutableStateFlow(
        UiState(
            host = prefs.getString("host", "") ?: "",
            port = prefs.getInt("port", 8800),
        )
    )
    val ui: StateFlow<UiState> = _ui.asStateFlow()

    private val appContext = app.applicationContext

    private val hub = HubClient(
        context = appContext,
        onSnapshot = { snap -> _ui.value = _ui.value.copy(snapshot = snap) },
        onLink = { linked, note -> _ui.value = _ui.value.copy(linked = linked, linkNote = note) },
    )

    init {
        locate()

        if (!sarvam.configured) {
            _ui.value = _ui.value.copy(
                notice = "No Sarvam key in the build. Voice is off; the controls still work."
            )
        }
    }

    // -- connection --------------------------------------------------------

    /**
     * Work out where the hub is, without asking anyone.
     *
     * Three sources, in order of how much they can be trusted right now:
     *
     *   1. UDP discovery -- what the hub says about itself, on this network,
     *      this minute. Correct even after the laptop's IP changes.
     *   2. The last address that worked, remembered from a previous run. Covers
     *      a network that drops broadcast but is otherwise fine.
     *   3. BuildConfig.HUB_HOST, baked in at build time from local.properties.
     *
     * Discovery runs off the main thread and takes at most a couple of seconds,
     * so the app opens on the remembered address immediately and quietly
     * corrects itself if discovery disagrees.
     */
    fun locate() {
        val remembered = _ui.value.host
        val baked = BuildConfig.HUB_HOST
        val fallback = remembered.ifBlank { baked }
        if (fallback.isNotBlank()) hub.connect(fallback, _ui.value.port)

        viewModelScope.launch {
            val found = withContext(Dispatchers.IO) { HubDiscovery.find(appContext) }
            if (found == null) {
                // Name the actual cause. "Could not find the hub" sends someone
                // debugging the laptop when the phone is on mobile data.
                val onWifi = LanNetwork.wifi(appContext) != null
                _ui.value = _ui.value.copy(
                    linkNote = if (onWifi) "no hub found on this WiFi"
                    else "phone is on mobile data",
                    notice = if (onWifi)
                        "Could not find the hub. Is the AI PC on this same WiFi? " +
                            "Some networks block phone-to-laptop traffic."
                    else
                        "This phone is on mobile data, not WiFi. Join the same " +
                            "WiFi as the AI PC - turn mobile data off if it keeps " +
                            "switching back.",
                )
                return@launch
            }
            if (found.host == _ui.value.host && _ui.value.linked) return@launch

            prefs.edit().putString("host", found.host).putInt("port", found.port).apply()
            _ui.value = _ui.value.copy(host = found.host, port = found.port)
            hub.connect(found.host, found.port)
        }
    }

    /**
     * Open the socket if it is not already open.
     *
     * Called when the microphone is pressed, so connecting is never something
     * the user has to think about or press a button for. Holding the socket open
     * from app start is not enough on a phone: Android suspends background
     * sockets aggressively, so the link is frequently dead by the time someone
     * actually speaks, and the first sentence of a demo is exactly the wrong
     * moment to discover that.
     *
     * Safe to call repeatedly -- it is a no-op while linked.
     */
    private fun ensureConnected(): Boolean {
        val host = _ui.value.host
        if (host.isBlank()) {
            // Nothing to connect to yet: re-run discovery rather than asking the
            // user for an address they should never have to know.
            locate()
            return false
        }
        if (!_ui.value.linked) hub.connect(host, _ui.value.port)
        return true
    }

    fun dismissNotice() {
        _ui.value = _ui.value.copy(notice = null)
    }

    // -- direct control ----------------------------------------------------

    fun toggle(deviceId: String, turnOn: Boolean, level: Double?) {
        val label = _ui.value.snapshot?.devices?.find { it.id == deviceId }?.label ?: deviceId
        hub.command(
            deviceId, turnOn, if (turnOn) level else null,
            "turn ${if (turnOn) "on" else "off"} the ${label.lowercase()}",
        )
    }

    fun setLevel(deviceId: String, level: Double) {
        val device = _ui.value.snapshot?.devices?.find { it.id == deviceId }
        val label = device?.label ?: deviceId
        hub.command(deviceId, true, level, "set ${label.lowercase()} to $level")
    }

    // -- voice -------------------------------------------------------------

    fun startListening() {
        if (_ui.value.mic != Mic.Idle) return
        if (!sarvam.configured) {
            _ui.value = _ui.value.copy(
                notice = "No Sarvam key in the build. Add sarvam.key to local.properties."
            )
            return
        }
        // Pressing the mic IS the connect action. The socket opens while the
        // user is still drawing breath, so by the time there is a transcript to
        // send -- a second or two later, after Sarvam answers -- the link is up.
        if (!ensureConnected()) return
        try {
            recorder.start()
            _ui.value = _ui.value.copy(mic = Mic.Listening, heard = "", notice = null)
        } catch (e: Exception) {
            _ui.value = _ui.value.copy(mic = Mic.Idle, notice = e.message ?: "microphone failed")
        }
    }

    /**
     * Release: stop recording, transcribe, send to the hub, confirm aloud.
     *
     * The confirmation matters. The user needs to know what was understood
     * before it reprograms their house.
     */
    fun stopListeningAndSend() {
        if (_ui.value.mic != Mic.Listening) return
        _ui.value = _ui.value.copy(mic = Mic.Thinking)

        viewModelScope.launch {
            val wav = withContext(Dispatchers.IO) { recorder.stop() }
            if (wav == null) {
                _ui.value = _ui.value.copy(mic = Mic.Idle, notice = "Too short - hold and speak.")
                return@launch
            }

            val transcript = try {
                withContext(Dispatchers.IO) { sarvam.transcribe(wav) }
            } catch (e: Exception) {
                _ui.value = _ui.value.copy(mic = Mic.Idle, notice = e.message ?: "transcription failed")
                return@launch
            }

            if (transcript.isBlank()) {
                _ui.value = _ui.value.copy(mic = Mic.Idle, notice = "Didn't catch that.")
                return@launch
            }

            _ui.value = _ui.value.copy(heard = transcript, mic = Mic.Idle)
            send(transcript)
        }
    }

    fun cancelListening() {
        recorder.cancel()
        _ui.value = _ui.value.copy(mic = Mic.Idle)
    }

    /**
     * Send a sentence to the hub and confirm it aloud.
     *
     * Waits for the link rather than failing on the first attempt. The socket
     * was opened when the mic was pressed and may still be completing its
     * handshake, so a bare `speak()` here would drop a sentence the user has
     * already said out loud -- the one failure they would never forgive,
     * because from their side they spoke and nothing happened.
     *
     * okhttp's send() returns false without queueing anything when the socket
     * is not open, so retrying cannot duplicate a delivered command.
     */
    fun send(text: String) {
        if (text.isBlank()) return
        _ui.value = _ui.value.copy(heard = text)
        if (!ensureConnected()) return

        viewModelScope.launch {
            var waited = 0L
            while (!_ui.value.linked && waited < LINK_WAIT_MS) {
                delay(LINK_POLL_MS)
                waited += LINK_POLL_MS
            }

            if (!hub.speak(text)) {
                _ui.value = _ui.value.copy(
                    notice = "Could not reach the hub at ${_ui.value.host}. " +
                        "Same WiFi? Some networks block phone-to-laptop traffic."
                )
                return@launch
            }
            confirmAloud("Okay. $text")
        }
    }

    private fun confirmAloud(line: String) {
        if (!sarvam.configured) return
        viewModelScope.launch {
            try {
                val wav = withContext(Dispatchers.IO) { sarvam.synthesize(line) }
                player.play(wav)
            } catch (_: Exception) {
                // A failed confirmation must not look like a failed command --
                // the appliance already switched. Stay quiet about it.
            }
        }
    }

    override fun onCleared() {
        super.onCleared()
        recorder.cancel()
        player.stop()
        hub.disconnect()
    }
}
