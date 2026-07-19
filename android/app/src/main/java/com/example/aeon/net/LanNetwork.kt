package com.example.aeon.net

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.util.Log
import java.net.Inet4Address
import java.net.InetAddress
import java.net.NetworkInterface

/**
 * Find the WiFi network, and make sockets actually use it.
 *
 * Android does not simply "use WiFi when WiFi is on". It picks a DEFAULT
 * network, and when the WiFi it is joined to looks like it has no usable
 * internet -- which is exactly how a laptop hotspot or a captive venue AP often
 * looks -- it keeps **cellular** as the default and quietly sends app traffic
 * there. The phone shows a WiFi icon while every socket leaves over mobile data.
 *
 * The symptom is unmistakable once you know it: the local address is 192.0.0.4,
 * the CLAT address Android assigns for IPv4-over-IPv6 on cellular, and every
 * connection to a LAN address times out because there is no route to it.
 *
 * ACCESS_NETWORK_STATE is enough to enumerate networks and bind to one; that
 * permission is already in the manifest. Binding a socket to a Network pins it
 * to that interface regardless of which network Android considers default.
 */
object LanNetwork {

    /** The WiFi network, or null if the phone genuinely is not on WiFi. */
    fun wifi(context: Context): Network? {
        return try {
            val cm = context.applicationContext
                .getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
                ?: return null

            @Suppress("DEPRECATION")            // allNetworks: fine down to minSdk 24
            val found = cm.allNetworks.firstOrNull { n ->
                cm.getNetworkCapabilities(n)
                    ?.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) == true
            }

            if (found == null) {
                Log.w(HubDiscovery.TAG,
                    "net: no WiFi network available - the phone is on mobile data. " +
                        "Join the same WiFi as the AI PC.")
            } else {
                Log.i(HubDiscovery.TAG, "net: binding to WiFi network $found")
            }
            found
        } catch (e: Exception) {
            Log.w(HubDiscovery.TAG, "net: could not query networks: ${e.message}")
            null
        }
    }

    /**
     * Every IPv4 address this phone actually holds, per interface.
     *
     * The one question that settles a "cannot reach the hub" report: if the hub
     * is 172.20.10.8 and this phone has no 172.20.10.x address, it is not on
     * that network and nothing in this app can fix it. An address in
     * 192.0.0.0/29 is 464XLAT -- IPv4 carried over an IPv6-only link, which
     * reaches the internet and cannot reach a machine on your LAN.
     */
    fun localAddresses(): List<String> {
        val out = mutableListOf<String>()
        try {
            for (nif in NetworkInterface.getNetworkInterfaces()) {
                if (!nif.isUp || nif.isLoopback) continue
                for (addr in nif.interfaceAddresses) {
                    val ip = addr.address
                    if (ip is Inet4Address) {
                        val bcast = addr.broadcast?.hostAddress?.let { " bcast $it" } ?: ""
                        out.add("${nif.name}: ${ip.hostAddress}/${addr.networkPrefixLength}$bcast")
                    }
                }
            }
        } catch (e: Exception) {
            out.add("could not read interfaces: ${e.message}")
        }
        return out
    }

    /**
     * Is `host` inside the subnet of an interface this phone already holds?
     *
     * If it is, the link is DIRECT -- a USB tether (rndis0), the phone's own
     * hotspot (swlan0), or the WiFi it is joined to -- and the socket must be
     * left unbound so the kernel routes it out of that interface. Pinning to
     * WiFi in that case forces the packet out of the wrong door: it is exactly
     * how a USB tether, the most reliable path available, gets ignored in
     * favour of a WiFi that cannot reach the target at all.
     *
     * Binding is only useful for the opposite case -- a target on no local
     * subnet, where Android might otherwise route it over cellular.
     */
    fun isDirectlyReachable(host: String): Boolean {
        val target = try {
            InetAddress.getByName(host)
        } catch (_: Exception) {
            return false
        }
        if (target !is Inet4Address) return false
        val t = target.address

        try {
            for (nif in NetworkInterface.getNetworkInterfaces()) {
                if (!nif.isUp || nif.isLoopback) continue
                for (addr in nif.interfaceAddresses) {
                    val local = addr.address
                    if (local !is Inet4Address) continue
                    val prefix = addr.networkPrefixLength.toInt()
                    if (prefix <= 0 || prefix > 32) continue
                    if (sameSubnet(local.address, t, prefix)) {
                        Log.i(HubDiscovery.TAG,
                            "net: $host is directly reachable on ${nif.name} " +
                                "(${local.hostAddress}/$prefix) - not pinning to WiFi")
                        return true
                    }
                }
            }
        } catch (e: Exception) {
            Log.w(HubDiscovery.TAG, "net: subnet check failed: ${e.message}")
        }
        return false
    }

    private fun sameSubnet(a: ByteArray, b: ByteArray, prefix: Int): Boolean {
        var bits = prefix
        for (i in 0 until 4) {
            if (bits <= 0) return true
            val mask = if (bits >= 8) 0xFF else (0xFF shl (8 - bits)) and 0xFF
            if ((a[i].toInt() and mask) != (b[i].toInt() and mask)) return false
            bits -= 8
        }
        return true
    }

    /** Log the phone's own addresses. Call when a connection fails. */
    fun logAddresses() {
        val addrs = localAddresses()
        if (addrs.isEmpty()) {
            Log.w(HubDiscovery.TAG, "net: this phone holds NO IPv4 address on any " +
                "interface - it is not on a WiFi network")
        } else {
            Log.i(HubDiscovery.TAG, "net: this phone's IPv4 addresses = $addrs")
        }
    }

    /** A short note for the UI: what network is this phone actually on? */
    fun describe(context: Context): String {
        val addrs = localAddresses()
        val lan = addrs.firstOrNull { !it.contains(": 192.0.0.") }
        return when {
            addrs.isEmpty() -> "no network"
            lan == null -> "mobile data only (${addrs.first().substringAfter(": ").substringBefore("/")})"
            else -> lan.substringAfter(": ").substringBefore(" ")
        }
    }
}
