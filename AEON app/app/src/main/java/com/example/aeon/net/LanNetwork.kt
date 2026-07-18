package com.example.aeon.net

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.util.Log

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

    /** A human-readable note for the UI when there is no LAN to reach. */
    fun describe(context: Context): String =
        if (wifi(context) == null) "phone is on mobile data, not WiFi"
        else "on WiFi"
}
