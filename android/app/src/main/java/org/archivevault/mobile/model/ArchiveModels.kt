package org.archivevault.mobile.model

enum class DownloadStatus {
    QUEUED,
    DOWNLOADING,
    PAUSED,
    COMPLETED,
    FAILED,
    CANCELLED
}

data class ArchiveItem(
    val identifier: String,
    val title: String,
    val description: String = "",
    val mediatype: String = "software",
    val creator: String = "",
    val year: String = "",
    val downloads: Int = 0,
    val imageUrl: String = "https://archive.org/services/img/$identifier"
)

data class ArchiveFile(
    val name: String,
    val format: String = "File",
    val sizeBytes: Long = 0L,
    val sizeFormatted: String = "",
    val url: String = ""
)

data class ItemMetadata(
    val identifier: String,
    val title: String,
    val description: String = "",
    val mediatype: String = "",
    val creator: String = "",
    val date: String = "",
    val files: List<ArchiveFile> = emptyList(),
    val server: String = "",
    val dir: String = ""
)

data class DownloadItem(
    val id: String,
    val identifier: String,
    val filename: String,
    val url: String,
    val savePath: String,
    val totalBytes: Long,
    val downloadedBytes: Long = 0L,
    val status: DownloadStatus = DownloadStatus.QUEUED,
    val speedBps: Long = 0L,
    val etaSeconds: Long = 0L,
    val errorMessage: String = ""
) {
    val progress: Float
        get() = if (totalBytes > 0) (downloadedBytes.toFloat() / totalBytes).coerceIn(0f, 1f) else 0f

    val isAudio: Boolean
        get() = filename.lowercase().let { 
            it.endsWith(".mp3") || it.endsWith(".flac") || it.endsWith(".ogg") || it.endsWith(".wav") || it.endsWith(".m4a")
        }

    val isVideo: Boolean
        get() = filename.lowercase().let {
            it.endsWith(".mp4") || it.endsWith(".mkv") || it.endsWith(".avi") || it.endsWith(".webm") || it.endsWith(".ogv")
        }

    val isGame: Boolean
        get() = identifier.lowercase().let {
            it.startsWith("msdos_") || it.startsWith("amiga_") || it.startsWith("arcade_") || it.startsWith("c64_") || it.startsWith("zx_")
        }
}
