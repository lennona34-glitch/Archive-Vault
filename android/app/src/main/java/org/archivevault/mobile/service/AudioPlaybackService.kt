package org.archivevault.mobile.service

import android.app.Notification
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.os.IBinder
import androidx.core.app.NotificationCompat
import kotlinx.coroutines.*
import org.archivevault.mobile.ArchiveVaultApp
import org.archivevault.mobile.MainActivity
import org.archivevault.mobile.player.AudioPlayerController

class AudioPlaybackService : Service() {

    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())
    private lateinit var audioController: AudioPlayerController

    override fun onCreate() {
        super.onCreate()
        audioController = AudioPlayerController.getInstance(this)

        scope.launch {
            audioController.trackState.collect { state ->
                if (state.isVisible) {
                    val notif = createNotification(state.title, state.isPlaying)
                    startForeground(1002, notif)
                } else {
                    stopForeground(STOP_FOREGROUND_REMOVE)
                    stopSelf()
                }
            }
        }
    }

    private fun createNotification(title: String, isPlaying: Boolean): Notification {
        val intent = Intent(this, MainActivity::class.java)
        val pendingIntent = PendingIntent.getActivity(
            this, 0, intent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        return NotificationCompat.Builder(this, ArchiveVaultApp.AUDIO_CHANNEL_ID)
            .setContentTitle("ArchiveVault Audio")
            .setContentText(title)
            .setSmallIcon(android.R.drawable.ic_media_play)
            .setContentIntent(pendingIntent)
            .setOngoing(isPlaying)
            .build()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }
}
