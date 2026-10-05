package org.archivevault.mobile.service

import android.app.Notification
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.os.IBinder
import androidx.core.app.NotificationCompat
import kotlinx.coroutines.*
import org.archivevault.mobile.ArchiveVaultApp
import org.archivevault.mobile.MainActivity
import org.archivevault.mobile.downloader.MobileDownloadManager
import org.archivevault.mobile.model.DownloadStatus

class DownloadService : Service() {

    private val serviceScope = CoroutineScope(Dispatchers.Main + SupervisorJob())
    private lateinit var downloadManager: MobileDownloadManager

    override fun onCreate() {
        super.onCreate()
        downloadManager = MobileDownloadManager.getInstance(this)
        startForeground(1001, createNotification("Starting downloads...", 0, 0))

        serviceScope.launch {
            downloadManager.items.collect { items ->
                val downloading = items.filter { it.status == DownloadStatus.DOWNLOADING }
                if (downloading.isNotEmpty()) {
                    val first = downloading.first()
                    val totalSpeed = downloading.sumOf { it.speedBps }
                    val speedStr = String.format("%.1f MB/s", totalSpeed / (1024f * 1024f))
                    val title = "Downloading ${downloading.size} item(s) ($speedStr)"
                    val content = first.filename
                    val notif = createNotification(title, (first.progress * 100).toInt(), 100, content)
                    getSystemService(NotificationManager::class.java)?.notify(1001, notif)
                } else {
                    stopForeground(STOP_FOREGROUND_REMOVE)
                    stopSelf()
                }
            }
        }
    }

    private fun createNotification(title: String, progress: Int, max: Int, content: String = ""): Notification {
        val intent = Intent(this, MainActivity::class.java)
        val pendingIntent = PendingIntent.getActivity(
            this, 0, intent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        return NotificationCompat.Builder(this, ArchiveVaultApp.DOWNLOAD_CHANNEL_ID)
            .setContentTitle(title)
            .setContentText(content)
            .setSmallIcon(android.R.drawable.stat_sys_download)
            .setContentIntent(pendingIntent)
            .setProgress(max, progress, max == 0)
            .setOngoing(true)
            .build()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        serviceScope.cancel()
        super.onDestroy()
    }
}
