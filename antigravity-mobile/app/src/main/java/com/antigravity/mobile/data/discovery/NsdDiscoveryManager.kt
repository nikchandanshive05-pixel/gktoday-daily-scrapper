package com.antigravity.mobile.data.discovery

import android.content.Context
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import android.util.Log
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow

sealed class DiscoveryEvent {
    data class Found(val serviceName: String, val host: String, val port: Int) : DiscoveryEvent()
    data class Lost(val serviceName: String) : DiscoveryEvent()
    data class Error(val message: String) : DiscoveryEvent()
}

class NsdDiscoveryManager(private val context: Context) {
    private val nsdManager = context.getSystemService(Context.NSD_SERVICE) as NsdManager
    private val serviceType = "_antigravity._tcp."

    fun discoverServices(): Flow<DiscoveryEvent> = callbackFlow {
        val discoveryListener = object : NsdManager.DiscoveryListener {
            override fun onDiscoveryStarted(regType: String) {
                Log.d("NSD", "Service discovery started: $regType")
            }

            override fun onServiceFound(service: NsdServiceInfo) {
                Log.d("NSD", "Service found: ${service.serviceName}")
                if (service.serviceType.contains("antigravity")) {
                    resolveService(service) { host, port ->
                        trySend(DiscoveryEvent.Found(service.serviceName, host, port))
                    }
                }
            }

            override fun onServiceLost(service: NsdServiceInfo) {
                Log.d("NSD", "Service lost: ${service.serviceName}")
                trySend(DiscoveryEvent.Lost(service.serviceName))
            }

            override fun onDiscoveryStopped(serviceType: String) {
                Log.d("NSD", "Discovery stopped: $serviceType")
            }

            override fun onStartDiscoveryFailed(serviceType: String, errorCode: Int) {
                Log.e("NSD", "Discovery start failed: $errorCode")
                trySend(DiscoveryEvent.Error("Discovery failed with error $errorCode"))
            }

            override fun onStopDiscoveryFailed(serviceType: String, errorCode: Int) {
                Log.e("NSD", "Discovery stop failed: $errorCode")
            }
        }

        try {
            nsdManager.discoverServices(serviceType, NsdManager.PROTOCOL_DNS_SD, discoveryListener)
        } catch (e: Exception) {
            trySend(DiscoveryEvent.Error(e.message ?: "Unknown discovery error"))
        }

        awaitClose {
            try {
                nsdManager.stopServiceDiscovery(discoveryListener)
            } catch (e: Exception) {
                Log.w("NSD", "Error stopping discovery: ${e.message}")
            }
        }
    }

    private fun resolveService(serviceInfo: NsdServiceInfo, onResolved: (String, Int) -> Unit) {
        val resolveListener = object : NsdManager.ResolveListener {
            override fun onResolveFailed(serviceInfo: NsdServiceInfo, errorCode: Int) {
                Log.e("NSD", "Resolve failed: $errorCode")
            }

            override fun onServiceResolved(resolved: NsdServiceInfo) {
                val host = resolved.host?.hostAddress ?: return
                val port = resolved.port
                Log.d("NSD", "Resolved host: $host:$port")
                onResolved(host, port)
            }
        }
        try {
            nsdManager.resolveService(serviceInfo, resolveListener)
        } catch (e: Exception) {
            Log.e("NSD", "Failed to invoke resolveService: ${e.message}")
        }
    }
}
