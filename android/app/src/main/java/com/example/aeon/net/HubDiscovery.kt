package com.example.aeon.net

import android.content.Context
import android.util.Log
import org.json.JSONObject
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.net.NetworkInterface
import java.net.SocketTimeoutException

/**
 * Find the hub on this WiFi, so the app never asks a person for an IP address.
 *
 * One UDP broadcast, one reply:
 *
 *     phone ── "AEON?" ──▶ 255.255.255.255:8801
 *     hub   ── {"aeon":1,"host":...,"port":8800} ──▶ phone
 *
 * A baked-in address does not survive reality: this project's hub moved from
 * 172.20.10.8 to 10.92.213.203 in one night just by changing WiFi, and a venue
 * will move it again. Discovery makes that a non-event.
 *
 * Returns null rather than throwing when nothing answers -- some networks drop
 * broadcast, and the caller falls back to BuildConfig.HUB_HOST. Blocking, so
 * call it off the main thread.
 */
object HubDiscovery {

    const val TAG = "AeonNet"

    private const val PORT = 8801
    private const val PROBE = "AEON?"
    private const val BUFFER = 512

    data class Found(val host: String, val port: Int)

    fun find(context: Context, timeoutMs: Int = 1200, attempts: Int = 2): Found? {
        repeat(attempts) { i ->
            Log.i(TAG, "discovery: broadcasting '$PROBE' on port $PORT " +
                "(attempt ${i + 1}/$attempts, timeout ${timeoutMs}ms)")
            val found = probeOnce(context, timeoutMs)
            if (found != null) {
                Log.i(TAG, "discovery: found hub at ${found.host}:${found.port}")
                return found
            }
        }
        Log.w(TAG, "discovery: no hub answered. Either the phone is on a " +
            "different network, or this WiFi drops broadcast (client isolation).")
        return null
    }

    /**
     * Every address worth broadcasting to.
     *
     * 255.255.255.255 alone is not enough on Android: the limited broadcast is
     * frequently not routed off the device, which looks exactly like a hub that
     * is not there. The subnet-directed address for each live interface -- e.g.
     * 10.92.213.255 for a /24 -- is the one that actually leaves the phone.
     * Send to all of them and let the first reply win.
     */
    private fun broadcastTargets(): List<InetAddress> {
        val targets = mutableListOf<InetAddress>()
        try {
            targets.add(InetAddress.getByName("255.255.255.255"))
        } catch (_: Exception) {
        }
        try {
            for (nif in NetworkInterface.getNetworkInterfaces()) {
                if (!nif.isUp || nif.isLoopback) continue
                for (addr in nif.interfaceAddresses) {
                    addr.broadcast?.let { targets.add(it) }
                }
            }
        } catch (e: Exception) {
            Log.w(TAG, "discovery: could not enumerate interfaces: ${e.message}")
        }
        val unique = targets.distinctBy { it.hostAddress ?: "" }
        Log.i(TAG, "discovery: targets = ${unique.mapNotNull { it.hostAddress }}")
        return unique
    }

    private fun probeOnce(context: Context, timeoutMs: Int): Found? {
        var socket: DatagramSocket? = null
        return try {
            socket = DatagramSocket().apply {
                broadcast = true
                soTimeout = timeoutMs
            }
            // Pin the probe to WiFi. Without this Android may route it over
            // cellular, where a LAN broadcast means nothing and no hub can
            // possibly answer.
            LanNetwork.wifi(context)?.bindSocket(socket)
            val payload = PROBE.toByteArray()
            var sent = 0
            for (target in broadcastTargets()) {
                try {
                    socket.send(DatagramPacket(payload, payload.size, target, PORT))
                    sent++
                } catch (e: Exception) {
                    Log.w(TAG, "discovery: send to ${target.hostAddress} failed: ${e.message}")
                }
            }
            if (sent == 0) {
                Log.w(TAG, "discovery: no reachable broadcast address - is WiFi on?")
                return null
            }

            val buf = ByteArray(BUFFER)
            val reply = DatagramPacket(buf, buf.size)
            socket.receive(reply)
            Log.i(TAG, "discovery: reply from ${reply.address?.hostAddress}: " +
                String(reply.data, 0, reply.length))

            val obj = JSONObject(String(reply.data, 0, reply.length))
            if (obj.optInt("aeon") != 1) {
                Log.w(TAG, "discovery: reply was not an AEON hub, ignoring")
                return null
            }

            // Prefer the address the hub reported. Fall back to the packet's
            // source: a hub behind two interfaces may name the wrong one, but
            // the packet demonstrably came from somewhere reachable.
            val host = obj.optString("host").ifBlank { reply.address.hostAddress ?: "" }
            if (host.isBlank()) null else Found(host, obj.optInt("port", 8800))
        } catch (_: SocketTimeoutException) {
            Log.i(TAG, "discovery: no reply within ${timeoutMs}ms")
            null
        } catch (e: Exception) {
            Log.w(TAG, "discovery: probe failed: ${e.javaClass.simpleName}: ${e.message}")
            null
        } finally {
            socket?.close()
        }
    }
}
