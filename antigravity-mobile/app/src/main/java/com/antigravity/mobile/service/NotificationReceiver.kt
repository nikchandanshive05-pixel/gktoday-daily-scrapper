package com.antigravity.mobile.service

import android.app.NotificationManager
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log
import com.antigravity.mobile.MainActivity

class NotificationReceiver : BroadcastReceiver() {

    companion object {
        const val ACTION_APPROVE = "com.antigravity.mobile.ACTION_APPROVE"
        const val ACTION_DENY = "com.antigravity.mobile.ACTION_DENY"
        const val EXTRA_ACTION_ID = "action_id"
    }

    override fun onReceive(context: Context, intent: Intent) {
        val actionId = intent.getStringExtra(EXTRA_ACTION_ID) ?: return
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.cancel(AntigravityForegroundService.APPROVAL_NOTIFICATION_ID)

        when (intent.action) {
            ACTION_APPROVE -> {
                Log.d("NotificationReceiver", "User tapped APPROVE for action: $actionId")
                MainActivity.instance?.resolveAction(actionId, approve = true)
            }
            ACTION_DENY -> {
                Log.d("NotificationReceiver", "User tapped DENY for action: $actionId")
                MainActivity.instance?.resolveAction(actionId, approve = false)
            }
        }
    }
}
