package com.antigravity.mobile.service

import android.app.*
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import com.antigravity.mobile.MainActivity

class AntigravityForegroundService : Service() {

    companion object {
        const val CHANNEL_ID = "antigravity_companion"
        const val NOTIFICATION_ID = 1001
        const val APPROVAL_NOTIFICATION_ID = 1002
    }

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val notification = createServiceNotification()
        startForeground(NOTIFICATION_ID, notification)

        // Check if an action approval needs a heads-up notification
        val actionId = intent?.getStringExtra("action_id")
        val actionDesc = intent?.getStringExtra("action_desc")
        if (actionId != null && actionDesc != null) {
            showApprovalNotification(actionId, actionDesc)
        }

        return START_STICKY
    }

    private fun createServiceNotification(): Notification {
        val launchIntent = Intent(this, MainActivity::class.java)
        val pendingIntent = PendingIntent.getActivity(
            this, 0, launchIntent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Antigravity Companion Active")
            .setContentText("Connected to PC • Monitoring agent workflows")
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .build()
    }

    private fun showApprovalNotification(actionId: String, description: String) {
        val approveIntent = Intent(this, NotificationReceiver::class.java).apply {
            action = NotificationReceiver.ACTION_APPROVE
            putExtra(NotificationReceiver.EXTRA_ACTION_ID, actionId)
        }
        val approvePendingIntent = PendingIntent.getBroadcast(
            this, 1, approveIntent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        val denyIntent = Intent(this, NotificationReceiver::class.java).apply {
            action = NotificationReceiver.ACTION_DENY
            putExtra(NotificationReceiver.EXTRA_ACTION_ID, actionId)
        }
        val denyPendingIntent = PendingIntent.getBroadcast(
            this, 2, denyIntent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Action Approval Required")
            .setContentText(description)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .addAction(android.R.drawable.checkbox_on_background, "Approve", approvePendingIntent)
            .addAction(android.R.drawable.ic_delete, "Deny", denyPendingIntent)
            .setAutoCancel(true)
            .build()

        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.notify(APPROVAL_NOTIFICATION_ID, notification)
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Antigravity Status & Approvals",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Live connection and lock-screen command approvals"
            }
            val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            manager.createNotificationChannel(channel)
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
