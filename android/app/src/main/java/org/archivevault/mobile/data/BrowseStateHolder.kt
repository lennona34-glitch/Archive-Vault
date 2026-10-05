package org.archivevault.mobile.data

import android.content.Context
import android.content.SharedPreferences
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import org.archivevault.mobile.model.ArchiveItem

object BrowseStateHolder {

    private const val PREFS_NAME = "archive_vault_browse_prefs"
    private const val KEY_LAST_QUERY = "key_last_query"
    private const val KEY_LAST_MEDIATYPE = "key_last_mediatype"
    private const val KEY_IS_GRID = "key_is_grid"

    var searchQuery by mutableStateOf("")
    var selectedMediaType by mutableStateOf("software")
    var items by mutableStateOf<List<ArchiveItem>>(emptyList())
    var isLoading by mutableStateOf(false)
    var isGridView by mutableStateOf(false)
    var hasInitialized by mutableStateOf(false)

    fun init(context: Context) {
        if (hasInitialized) return
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        searchQuery = prefs.getString(KEY_LAST_QUERY, "") ?: ""
        selectedMediaType = prefs.getString(KEY_LAST_MEDIATYPE, "software") ?: "software"
        isGridView = prefs.getBoolean(KEY_IS_GRID, false)
        hasInitialized = true
    }

    fun savePrefs(context: Context) {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        prefs.edit()
            .putString(KEY_LAST_QUERY, searchQuery)
            .putString(KEY_LAST_MEDIATYPE, selectedMediaType)
            .putBoolean(KEY_IS_GRID, isGridView)
            .apply()
    }
}
