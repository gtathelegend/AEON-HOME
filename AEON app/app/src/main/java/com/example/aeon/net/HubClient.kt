package com.example.aeon.net

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
    private val onSnapshot: (HubSnapshot) -> Unit,
    private val onLink: (Boolean, String) -> Unit,
) {
    private val client = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS)       // a socket that never idles out
        .pingInterval(20, TimeUnit.SECONDS)          // notice a dead AP instead of hanging
        .build()

    private var socket: WebSocket? = null
    private var url: String = ""
    private val closedByUs = AtomicBoolean(false)
    private var attempt = 0

    fun connect(host: String, port: Int) {
        disconnect()
        closedByUs.set(false)
        url = "ws://$host:$port/ws"
        open()
    }

    private fun open() {
        onLink(false, "connecting")
        val request = Request.Builder().url(url).build()
        socket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                attempt = 0
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
                onLink(false, t.message ?: "no route to hub")
                scheduleReconnect()
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
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

    private fun send(obj: JSONObject): Boolean = socket?.send(obj.toString()) ?: false

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
