package com.example.aeon

import android.app.Application
import android.content.Context
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.aeon.audio.WavPlayer
import com.example.aeon.audio.WavRecorder
import com.example.aeon.model.HubSnapshot
import com.example.aeon.net.HubClient
import com.example.aeon.net.SarvamClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

enum class Mic { Idle, Listening, Thinking }

data class UiState(
    val linked: Boolean = false,
    val linkNote: String = "not connected",
    val mic: Mic = Mic.Idle,
    val heard: String = "",
    val notice: String? = null,
    val snapshot: HubSnapshot? = null,
    val host: String = "",
    val port: Int = 8800,
    val showSettings: Boolean = false,
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

    private val hub = HubClient(
        onSnapshot = { snap -> _ui.value = _ui.value.copy(snapshot = snap) },
        onLink = { linked, note -> _ui.value = _ui.value.copy(linked = linked, linkNote = note) },
    )

    init {
        val host = _ui.value.host
        if (host.isNotBlank()) hub.connect(host, _ui.value.port)
        else _ui.value = _ui.value.copy(showSettings = true, linkNote = "set the hub address")

        if (!sarvam.configured) {
            _ui.value = _ui.value.copy(
                notice = "No Sarvam key in the build. Voice is off; the controls still work."
            )
        }
    }

    // -- connection --------------------------------------------------------

    fun setHub(host: String, port: Int) {
        prefs.edit().putString("host", host.trim()).putInt("port", port).apply()
        _ui.value = _ui.value.copy(host = host.trim(), port = port, showSettings = false)
        if (host.isNotBlank()) hub.connect(host.trim(), port)
    }

    fun toggleSettings() {
        _ui.value = _ui.value.copy(showSettings = !_ui.value.showSettings)
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

    /** Send a sentence to the hub and confirm it aloud. */
    fun send(text: String) {
        if (text.isBlank()) return
        _ui.value = _ui.value.copy(heard = text)

        val delivered = hub.speak(text)
        if (!delivered) {
            _ui.value = _ui.value.copy(notice = "Not connected to the hub - check the address.")
            return
        }
        confirmAloud("Okay. $text")
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
