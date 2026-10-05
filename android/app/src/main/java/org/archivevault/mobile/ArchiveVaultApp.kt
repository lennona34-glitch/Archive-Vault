package org.archivevault.mobile

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build

class ArchiveVaultApp : Application() {

    companion object {
        const val DOWNLOAD_CHANNEL_ID = "archivevault_downloads"
        const val AUDIO_CHANNEL_ID = "archivevault_audio"
    }

    override fun onCreate() {
        super.onCreate()
        createNotificationChannels()
    }

    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val notificationManager = getSystemService(NotificationManager::class.java)

            val downloadChannel = NotificationChannel(
                DOWNLOAD_CHANNEL_ID,
                "Archive Downloads",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Shows progress and controls for active file downloads"
            }

            val audioChannel = NotificationChannel(
                AUDIO_CHANNEL_ID,
                "Archive Audio Playback",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Shows media controls for background audio streams"
            }

            notificationManager?.createNotificationChannel(downloadChannel)
            notificationManager?.createNotificationChannel(audioChannel)
        }
    }
}
