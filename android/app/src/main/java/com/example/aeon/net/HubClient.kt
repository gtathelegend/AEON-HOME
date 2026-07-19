package com.example.aeon.net

import android.content.Context
import android.util.Log
import com.example.aeon.model.HubSnapshot
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import org.json.JSONObject
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean

/**
 * The phone talks to the central node, not to the PC.
 *
 * Same WebSocket the browser client uses, so the phone is not a second protocol
 * to keep in step -- it is the same one.
 */
class HubClient(
    private val context: Context,
    private val onSnapshot: (HubSnapshot) -> Unit,
    private val onLink: (Boolean, String) -> Unit,
) {
    /**
     * Built per connection, not once, so it can be pinned to the CURRENT WiFi
     * network. Android will happily route a LAN address over cellular when it
     * considers WiFi to have no internet -- the socket then leaves from
     * 192.0.0.4 and times out against a hub three metres away.
     */
    private fun newClient(host: String): OkHttpClient {
        val builder = OkHttpClient.Builder()
            .readTimeout(0, TimeUnit.MILLISECONDS)   // a socket that never idles out
            .pingInterval(20, TimeUnit.SECONDS)      // notice a dead AP instead of hanging
            .connectTimeout(6, TimeUnit.SECONDS)     // fail fast; 10 s is a long stare

        // Pin to WiFi ONLY when the target is not already on a local subnet.
        // A directly connected link -- a USB tether, the phone's own hotspot --
        // must be left to the kernel to route, or the pin sends the packet out
        // of the WiFi interface and it never reaches a laptop sitting on the
        // other end of a USB cable.
        if (!LanNetwork.isDirectlyReachable(host)) {
            LanNetwork.wifi(context)?.let { builder.socketFactory(it.socketFactory) }
        }
        return builder.build()
    }

    private var socket: WebSocket? = null
    private var url: String = ""
    private var host: String = ""
    private val closedByUs = AtomicBoolean(false)
    private var attempt = 0

    /** True only between onOpen and onClosed/onFailure. The one honest signal. */
    @Volatile
    var linked: Boolean = false
        private set

    fun connect(host: String, port: Int) {
        disconnect()
        closedByUs.set(false)
        // ?client=phone identifies this socket as a handset rather than a
        // screen, so the dashboard can show that the phone is actually attached
        // instead of the presenter discovering it never connected mid-demo.
        this.host = host
        url = "ws://$host:$port/ws?client=phone"
        open()
    }

    private fun open() {
        linked = false
        onLink(false, "connecting")
        val onWifi = LanNetwork.wifi(context) != null
        Log.i(HubDiscovery.TAG, "ws: opening $url (wifi=$onWifi)")
        if (!onWifi) {
            onLink(false, "phone is on mobile data, not WiFi")
        }
        val request = Request.Builder().url(url).build()
        socket = newClient(host).newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                attempt = 0
                Log.i(HubDiscovery.TAG, "ws: OPEN $url")
                linked = true
                onLink(true, "linked")
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                try {
                    val obj = JSONObject(text)
                    if (obj.optString("typ") == "state") onSnapshot(HubSnapshot.from(obj))
                } catch (_: Exception) {
                    // A malformed frame must not kill the socket. The hub is the
                    // source of truth; the next snapshot will correct us.
                }
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                // The single most useful line when the phone will not connect:
                // it names the exception. ETIMEDOUT means the packets are being
                // dropped (client isolation, wrong network); ECONNREFUSED means
                // the phone reached the laptop and nothing was listening.
                Log.w(HubDiscovery.TAG,
                    "ws: FAILED $url -> ${t.javaClass.simpleName}: ${t.message}" +
                        (response?.let { " (http ${it.code})" } ?: ""))
                // Print what addresses this phone actually holds. If none of
                // them share a subnet with the hub, the phone is on a different
                // network and no retry will ever succeed.
                LanNetwork.logAddresses()
                linked = false
                onLink(false, t.message ?: "no route to hub")
                scheduleReconnect()
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                Log.i(HubDiscovery.TAG, "ws: CLOSED $code $reason")
                linked = false
                onLink(false, "closed")
                scheduleReconnect()
            }
        })
    }

    private fun scheduleReconnect() {
        if (closedByUs.get()) return
        attempt += 1
        val delayMs = minOf(500L * attempt, 5_000L)
        Thread {
            Thread.sleep(delayMs)
            if (!closedByUs.get()) open()
        }.apply { isDaemon = true }.start()
    }

    fun disconnect() {
        closedByUs.set(true)
        socket?.close(1000, "bye")
        socket = null
    }

    // -- outbound -----------------------------------------------------------

    private fun send(obj: JSONObject): Boolean {
        val queued = socket?.send(obj.toString()) ?: false
        // QUEUED, not delivered. okhttp accepts a frame into its buffer while
        // the socket is still connecting and returns true, so this says nothing
        // about the hub having received anything -- an earlier version logged
        // "sent" here and read like success while every connection was timing
        // out. Only `linked` means delivered.
        val state = if (linked) "queued+linked" else "queued, NOT LINKED - going nowhere"
        if (queued) Log.i(HubDiscovery.TAG, "ws: $state ${obj.optString("typ")} $obj")
        else Log.w(HubDiscovery.TAG, "ws: refused (no socket) $obj")
        return queued && linked
    }

    /** A spoken sentence. The hub parses it and fans it out. */
    fun speak(text: String) = send(JSONObject().put("typ", "speak").put("text", text))

    /** A tile or slider: an instruction for right now. */
    fun command(device: String, on: Boolean, level: Double?, spoken: String) = send(
        JSONObject()
            .put("typ", "command")
            .put("device", device)
            .put("on", on)
            .put("level", level ?: JSONObject.NULL)
            .put("spoken", spoken)
    )
}
