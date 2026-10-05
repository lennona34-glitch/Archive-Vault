package org.archivevault.mobile.downloader

import android.content.Context
import android.os.Environment
import kotlinx.coroutines.*
import kotlin.coroutines.coroutineContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import okhttp3.OkHttpClient
import okhttp3.Request
import org.archivevault.mobile.model.DownloadItem
import org.archivevault.mobile.model.DownloadStatus
import java.io.File
import java.io.FileOutputStream
import java.io.RandomAccessFile
import java.util.UUID
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.TimeUnit

class MobileDownloadManager(private val context: Context) {

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private val client = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    private val _items = MutableStateFlow<List<DownloadItem>>(emptyList())
    val items: StateFlow<List<DownloadItem>> = _items.asStateFlow()

    private val activeJobs = ConcurrentHashMap<String, Job>()

    private val defaultDownloadDir: File by lazy {
        val publicDownloads = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS)
        val vaultDir = File(publicDownloads, "ArchiveVault")
        if (!vaultDir.exists()) {
            vaultDir.mkdirs()
        }
        if (vaultDir.exists() && vaultDir.canWrite()) {
            vaultDir
        } else if (publicDownloads.exists() && publicDownloads.canWrite()) {
            publicDownloads
        } else {
            context.getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS)
                ?: File(context.filesDir, "downloads").apply { mkdirs() }
        }
    }

    fun enqueueDownload(identifier: String, filename: String, url: String, totalBytes: Long): String {
        val id = UUID.randomUUID().toString()
        val safeName = filename.replace(Regex("[^a-zA-Z0-9._-]"), "_")
        val targetFile = File(defaultDownloadDir, safeName)

        val item = DownloadItem(
            id = id,
            identifier = identifier,
            filename = filename,
            url = url,
            savePath = targetFile.absolutePath,
            totalBytes = totalBytes,
            downloadedBytes = 0L,
            status = DownloadStatus.QUEUED
        )

        _items.value = _items.value + item
        startDownload(item.id)
        return id
    }

    fun startDownload(itemId: String) {
        val currentItem = _items.value.find { it.id == itemId } ?: return
        if (currentItem.status == DownloadStatus.DOWNLOADING) return

        updateItem(itemId) { it.copy(status = DownloadStatus.DOWNLOADING, errorMessage = "") }

        val job = scope.launch {
            runDownloadLoop(itemId)
        }
        activeJobs[itemId] = job
    }

    fun pauseDownload(itemId: String) {
        activeJobs[itemId]?.cancel()
        activeJobs.remove(itemId)
        updateItem(itemId) { it.copy(status = DownloadStatus.PAUSED, speedBps = 0L, etaSeconds = 0L) }
    }

    fun resumeDownload(itemId: String) {
        startDownload(itemId)
    }

    fun cancelDownload(itemId: String) {
        activeJobs[itemId]?.cancel()
        activeJobs.remove(itemId)
        val item = _items.value.find { it.id == itemId }
        item?.let {
            val partFile = File(it.savePath + ".part")
            if (partFile.exists()) partFile.delete()
        }
        _items.value = _items.value.filter { it.id != itemId }
    }

    fun pauseAll() {
        _items.value.filter { it.status == DownloadStatus.DOWNLOADING }.forEach {
            pauseDownload(it.id)
        }
    }

    fun resumeAll() {
        _items.value.filter { it.status in listOf(DownloadStatus.PAUSED, DownloadStatus.QUEUED, DownloadStatus.FAILED) }.forEach {
            startDownload(it.id)
        }
    }

    fun clearCompleted() {
        _items.value = _items.value.filter { it.status != DownloadStatus.COMPLETED }
    }

    private suspend fun runDownloadLoop(itemId: String) {
        val item = _items.value.find { it.id == itemId } ?: return
        val finalFile = File(item.savePath)
        val partFile = File(item.savePath + ".part")

        var downloaded = if (partFile.exists()) partFile.length() else 0L

        try {
            val requestBuilder = Request.Builder().url(item.url)
            if (downloaded > 0) {
                requestBuilder.header("Range", "bytes=$downloaded-")
            }

            val response = client.newCall(requestBuilder.build()).execute()
            if (!response.isSuccessful && response.code != 206) {
                // If 416 Range Not Satisfiable, file might already be complete
                if (response.code == 416 && partFile.exists()) {
                    partFile.renameTo(finalFile)
                    updateItem(itemId) { it.copy(status = DownloadStatus.COMPLETED, downloadedBytes = it.totalBytes, speedBps = 0L) }
                    return
                }
                updateItem(itemId) { it.copy(status = DownloadStatus.FAILED, errorMessage = "HTTP ${response.code}") }
                return
            }

            val body = response.body ?: throw Exception("Empty response body")
            val contentLength = body.contentLength()
            val total = if (contentLength > 0) downloaded + contentLength else item.totalBytes

            updateItem(itemId) { it.copy(totalBytes = total) }

            val stream = if (downloaded > 0) {
                RandomAccessFile(partFile, "rw").apply { seek(downloaded) }
            } else {
                FileOutputStream(partFile, false)
            }

            val buffer = ByteArray(64 * 1024)
            val inputStream = body.byteStream()
            var lastTime = System.currentTimeMillis()
            var bytesSinceLast = 0L

            inputStream.use { input ->
                while (coroutineContext.isActive) {
                    val read = input.read(buffer)
                    if (read == -1) break
                    if (stream is RandomAccessFile) {
                        stream.write(buffer, 0, read)
                    } else if (stream is FileOutputStream) {
                        stream.write(buffer, 0, read)
                    }
                    downloaded += read
                    bytesSinceLast += read

                    val now = System.currentTimeMillis()
                    val dt = now - lastTime
                    if (dt >= 500) {
                        val speed = (bytesSinceLast * 1000) / dt
                        val remaining = if (total > downloaded) total - downloaded else 0L
                        val eta = if (speed > 0) remaining / speed else 0L

                        updateItem(itemId) {
                            it.copy(
                                downloadedBytes = downloaded,
                                speedBps = speed,
                                etaSeconds = eta
                            )
                        }
                        lastTime = now
                        bytesSinceLast = 0L
                    }
                }
            }

            if (stream is RandomAccessFile) stream.close()
            if (stream is FileOutputStream) stream.close()

            if (coroutineContext.isActive) {
                if (partFile.exists()) {
                    if (finalFile.exists()) finalFile.delete()
                    partFile.renameTo(finalFile)
                }
                try {
                    android.media.MediaScannerConnection.scanFile(
                        context,
                        arrayOf(finalFile.absolutePath),
                        null,
                        null
                    )
                } catch (_: Exception) {}
                updateItem(itemId) {
                    it.copy(
                        status = DownloadStatus.COMPLETED,
                        downloadedBytes = it.totalBytes,
                        speedBps = 0L,
                        etaSeconds = 0L
                    )
                }
            }
        } catch (e: CancellationException) {
            // Paused normally
        } catch (e: Exception) {
            updateItem(itemId) {
                it.copy(
                    status = DownloadStatus.FAILED,
                    errorMessage = e.message ?: "Download error",
                    speedBps = 0L
                )
            }
        } finally {
            activeJobs.remove(itemId)
        }
    }

    private fun updateItem(itemId: String, transform: (DownloadItem) -> DownloadItem) {
        _items.value = _items.value.map { if (it.id == itemId) transform(it) else it }
    }

    companion object {
        @Volatile
        private var instance: MobileDownloadManager? = null

        fun getInstance(context: Context): MobileDownloadManager {
            return instance ?: synchronized(this) {
                instance ?: MobileDownloadManager(context.applicationContext).also { instance = it }
            }
        }
    }
}
