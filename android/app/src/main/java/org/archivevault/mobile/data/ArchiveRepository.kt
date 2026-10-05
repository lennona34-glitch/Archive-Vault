package org.archivevault.mobile.data

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.archivevault.mobile.model.ArchiveFile
import org.archivevault.mobile.model.ArchiveItem
import org.archivevault.mobile.model.ItemMetadata
import org.json.JSONObject
import java.net.URLEncoder
import java.util.concurrent.TimeUnit

object ArchiveRepository {

    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(20, TimeUnit.SECONDS)
        .build()

    fun formatSize(bytes: Long): String {
        if (bytes <= 0) return "0 B"
        val units = arrayOf("B", "KB", "MB", "GB", "TB")
        var b = bytes.toDouble()
        var idx = 0
        while (b >= 1024 && idx < units.size - 1) {
            b /= 1024
            idx++
        }
        return String.format("%.1f %s", b, units[idx])
    }

    suspend fun searchItems(
        query: String = "",
        mediatype: String = "",
        page: Int = 1,
        rows: Int = 30
    ): List<ArchiveItem> = withContext(Dispatchers.IO) {
        val queryParts = mutableListOf<String>()
        if (query.isNotBlank()) {
            queryParts.add(query)
        }
        if (mediatype.isNotBlank() && mediatype != "all") {
            queryParts.add("mediatype:$mediatype")
        }
        val finalQuery = if (queryParts.isEmpty()) "mediatype:software" else queryParts.joinToString(" AND ")
        val encodedQuery = URLEncoder.encode(finalQuery, "UTF-8")

        val url = "https://archive.org/advancedsearch.php?q=$encodedQuery&fl[]=identifier,title,description,mediatype,creator,year,downloads&sort[]=downloads+desc&rows=$rows&page=$page&output=json"

        val request = Request.Builder().url(url).build()
        val response = client.newCall(request).execute()
        val jsonStr = response.body?.string() ?: return@withContext emptyList()

        val json = JSONObject(jsonStr)
        val responseObj = json.optJSONObject("response") ?: return@withContext emptyList()
        val docs = responseObj.optJSONArray("docs") ?: return@withContext emptyList()

        val results = mutableListOf<ArchiveItem>()
        for (i in 0 until docs.length()) {
            val doc = docs.getJSONObject(i)
            val ident = doc.optString("identifier", "")
            if (ident.isNotBlank()) {
                results.add(
                    ArchiveItem(
                        identifier = ident,
                        title = doc.optString("title", ident),
                        description = doc.optString("description", ""),
                        mediatype = doc.optString("mediatype", "software"),
                        creator = doc.optString("creator", ""),
                        year = doc.optString("year", ""),
                        downloads = doc.optInt("downloads", 0)
                    )
                )
            }
        }
        results
    }

    suspend fun getItemMetadata(identifier: String): ItemMetadata? = withContext(Dispatchers.IO) {
        val url = "https://archive.org/metadata/$identifier"
        val request = Request.Builder().url(url).build()
        val response = client.newCall(request).execute()
        val bodyStr = response.body?.string() ?: return@withContext null

        val json = JSONObject(bodyStr)
        val meta = json.optJSONObject("metadata") ?: return@withContext null
        val server = json.optString("server", "")
        val dir = json.optString("dir", "")

        val filesArray = json.optJSONArray("files")
        val fileList = mutableListOf<ArchiveFile>()

        if (filesArray != null) {
            for (i in 0 until filesArray.length()) {
                val f = filesArray.getJSONObject(i)
                val fname = f.optString("name", "")
                val lowerName = fname.lowercase()
                
                // Skip internal metadata files
                val isMeta = lowerName.endsWith(".xml") || lowerName.endsWith(".sqlite") ||
                             lowerName.endsWith(".torrent") || lowerName.endsWith(".json")
                if (!isMeta) {
                    val size = f.optLong("size", 0L)
                    val format = f.optString("format", "File")
                    val fileUrl = "https://archive.org/download/$identifier/${URLEncoder.encode(fname, "UTF-8").replace("+", "%20")}"
                    fileList.add(
                        ArchiveFile(
                            name = fname,
                            format = format,
                            sizeBytes = size,
                            sizeFormatted = formatSize(size),
                            url = fileUrl
                        )
                    )
                }
            }
        }

        // Sort files: primary largest first
        fileList.sortByDescending { it.sizeBytes }

        ItemMetadata(
            identifier = identifier,
            title = meta.optString("title", identifier),
            description = meta.optString("description", ""),
            mediatype = meta.optString("mediatype", ""),
            creator = meta.optString("creator", ""),
            date = meta.optString("date", ""),
            files = fileList,
            server = server,
            dir = dir
        )
    }
}
