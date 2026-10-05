package org.archivevault.mobile.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.GridView
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.ViewList
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import kotlinx.coroutines.launch
import org.archivevault.mobile.data.ArchiveRepository
import org.archivevault.mobile.model.ArchiveItem
import org.archivevault.mobile.ui.theme.VaultBackground
import org.archivevault.mobile.ui.theme.VaultPrimary
import org.archivevault.mobile.ui.theme.VaultSecondary
import org.archivevault.mobile.ui.theme.VaultSurface

import androidx.compose.ui.platform.LocalContext
import org.archivevault.mobile.data.BrowseStateHolder

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BrowseScreen(
    onItemSelected: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    val categories = listOf(
        "software" to "🎮 Games & DOS",
        "movies" to "🎬 Movies & TV",
        "audio" to "🎵 Music & Audio",
        "texts" to "📖 Books & Text",
        "all" to "🌐 All Vaults"
    )

    fun loadData() {
        scope.launch {
            BrowseStateHolder.isLoading = true
            BrowseStateHolder.items = ArchiveRepository.searchItems(
                query = BrowseStateHolder.searchQuery,
                mediatype = BrowseStateHolder.selectedMediaType
            )
            BrowseStateHolder.isLoading = false
            BrowseStateHolder.savePrefs(context)
        }
    }

    LaunchedEffect(Unit) {
        BrowseStateHolder.init(context)
        if (BrowseStateHolder.items.isEmpty()) {
            loadData()
        }
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(VaultBackground)
            .padding(horizontal = 14.dp, vertical = 8.dp)
    ) {
        // App Headline & View Mode Switcher
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(bottom = 6.dp, top = 4.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "🏛️ ArchiveVault Explorer",
                color = Color.White,
                fontSize = 20.sp,
                fontWeight = FontWeight.ExtraBold
            )

            // Grid / List View Toggle
            IconButton(
                onClick = {
                    BrowseStateHolder.isGridView = !BrowseStateHolder.isGridView
                    BrowseStateHolder.savePrefs(context)
                },
                modifier = Modifier.size(36.dp)
            ) {
                Icon(
                    imageVector = if (BrowseStateHolder.isGridView) Icons.Default.ViewList else Icons.Default.GridView,
                    contentDescription = "Toggle View",
                    tint = VaultPrimary
                )
            }
        }

        // Search Bar with persistence & clear button
        OutlinedTextField(
            value = BrowseStateHolder.searchQuery,
            onValueChange = { BrowseStateHolder.searchQuery = it },
            placeholder = { Text("Search games, films, music, books...", color = Color.Gray, fontSize = 13.sp) },
            leadingIcon = { Icon(Icons.Default.Search, contentDescription = null, tint = VaultPrimary) },
            trailingIcon = {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    if (BrowseStateHolder.searchQuery.isNotBlank()) {
                        IconButton(
                            onClick = {
                                BrowseStateHolder.searchQuery = ""
                                loadData()
                            },
                            modifier = Modifier.size(32.dp)
                        ) {
                            Icon(Icons.Default.Close, contentDescription = "Clear", tint = Color.Gray, modifier = Modifier.size(18.dp))
                        }
                        Spacer(modifier = Modifier.width(4.dp))
                        Button(
                            onClick = { loadData() },
                            colors = ButtonDefaults.buttonColors(containerColor = VaultPrimary),
                            shape = RoundedCornerShape(8.dp),
                            modifier = Modifier.padding(end = 4.dp).height(36.dp)
                        ) {
                            Text("Search", color = Color.Black, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                        }
                    }
                }
            },
            keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(
                imeAction = androidx.compose.ui.text.input.ImeAction.Search
            ),
            keyboardActions = androidx.compose.foundation.text.KeyboardActions(
                onSearch = { loadData() }
            ),
            singleLine = true,
            shape = RoundedCornerShape(12.dp),
            colors = OutlinedTextFieldDefaults.colors(
                focusedContainerColor = VaultSurface,
                unfocusedContainerColor = VaultSurface,
                focusedBorderColor = VaultPrimary,
                unfocusedBorderColor = Color(0xFF3F3F46),
                focusedTextColor = Color.White,
                unfocusedTextColor = Color.White
            ),
            modifier = Modifier.fillMaxWidth()
        )

        // Smooth Horizontally Scrollable Category Chips Row
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState())
                .padding(vertical = 10.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            categories.forEach { (type, label) ->
                val isSelected = BrowseStateHolder.selectedMediaType == type
                FilterChip(
                    selected = isSelected,
                    onClick = {
                        if (BrowseStateHolder.selectedMediaType != type) {
                            BrowseStateHolder.selectedMediaType = type
                            loadData()
                        }
                    },
                    label = { Text(label, fontSize = 11.sp, fontWeight = FontWeight.Bold) },
                    colors = FilterChipDefaults.filterChipColors(
                        selectedContainerColor = VaultPrimary,
                        selectedLabelColor = Color.Black,
                        containerColor = VaultSurface,
                        labelColor = Color.LightGray
                    ),
                    shape = RoundedCornerShape(8.dp)
                )
            }
        }

        if (BrowseStateHolder.isLoading) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = VaultPrimary)
            }
        } else if (BrowseStateHolder.isGridView) {
            // 2-Column Grid Layout
            LazyVerticalGrid(
                columns = GridCells.Fixed(2),
                contentPadding = PaddingValues(bottom = 80.dp),
                horizontalArrangement = Arrangement.spacedBy(10.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp),
                modifier = Modifier.fillMaxSize()
            ) {
                items(BrowseStateHolder.items) { item ->
                    ArchiveItemCard(item = item, onClick = { onItemSelected(item.identifier) })
                }
            }
        } else {
            // Dense, High-Efficiency List Layout (see 6-8 items on screen at once)
            LazyColumn(
                contentPadding = PaddingValues(bottom = 80.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.fillMaxSize()
            ) {
                items(BrowseStateHolder.items) { item ->
                    ArchiveItemListRow(item = item, onClick = { onItemSelected(item.identifier) })
                }
            }
        }
    }
}

@Composable
fun ArchiveItemListRow(
    item: ArchiveItem,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onClick() },
        shape = RoundedCornerShape(10.dp),
        colors = CardDefaults.cardColors(containerColor = VaultSurface)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(10.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            // Thumbnail
            Box(
                modifier = Modifier
                    .size(68.dp)
                    .clip(RoundedCornerShape(8.dp))
                    .background(Color(0xFF27272A))
            ) {
                AsyncImage(
                    model = item.imageUrl,
                    contentDescription = item.title,
                    contentScale = ContentScale.Crop,
                    modifier = Modifier.fillMaxSize()
                )
            }

            // Info
            Column(modifier = Modifier.weight(1f)) {
                // Badge + Year
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                    modifier = Modifier.padding(bottom = 2.dp)
                ) {
                    val badgeColor = when (item.mediatype) {
                        "software" -> VaultSecondary
                        "movies" -> Color(0xFF6366F1)
                        "audio" -> VaultPrimary
                        else -> Color(0xFF8B5CF6)
                    }
                    Surface(
                        color = badgeColor,
                        shape = RoundedCornerShape(4.dp)
                    ) {
                        Text(
                            text = item.mediatype.uppercase(),
                            color = Color.Black,
                            fontSize = 8.sp,
                            fontWeight = FontWeight.Black,
                            modifier = Modifier.padding(horizontal = 4.dp, vertical = 1.dp)
                        )
                    }
                    if (item.year.isNotBlank()) {
                        Text(text = item.year, color = Color(0xFFA1A1AA), fontSize = 10.sp)
                    }
                }

                Text(
                    text = item.title,
                    color = Color.White,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Bold,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis
                )

                if (item.creator.isNotBlank()) {
                    Text(
                        text = item.creator,
                        color = Color.Gray,
                        fontSize = 11.sp,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.padding(top = 1.dp)
                    )
                }

                if (item.downloads > 0) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.padding(top = 3.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Download,
                            contentDescription = null,
                            tint = VaultPrimary,
                            modifier = Modifier.size(11.dp)
                        )
                        Spacer(modifier = Modifier.width(3.dp))
                        Text(
                            text = "${item.downloads} downloads",
                            color = VaultPrimary,
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Medium
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun ArchiveItemCard(
    item: ArchiveItem,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onClick() },
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = VaultSurface)
    ) {
        Column {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(120.dp)
                    .background(Color(0xFF27272A))
            ) {
                AsyncImage(
                    model = item.imageUrl,
                    contentDescription = item.title,
                    contentScale = ContentScale.Crop,
                    modifier = Modifier.fillMaxSize()
                )
                val badgeColor = when (item.mediatype) {
                    "software" -> VaultSecondary
                    "movies" -> Color(0xFF6366F1)
                    "audio" -> VaultPrimary
                    else -> Color(0xFF8B5CF6)
                }
                Surface(
                    color = badgeColor,
                    shape = RoundedCornerShape(4.dp),
                    modifier = Modifier
                        .align(Alignment.TopStart)
                        .padding(6.dp)
                ) {
                    Text(
                        text = item.mediatype.uppercase(),
                        color = Color.Black,
                        fontSize = 9.sp,
                        fontWeight = FontWeight.Black,
                        modifier = Modifier.padding(horizontal = 4.dp, vertical = 2.dp)
                    )
                }
            }

            Column(modifier = Modifier.padding(10.dp)) {
                Text(
                    text = item.title,
                    color = Color.White,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis
                )

                if (item.creator.isNotBlank()) {
                    Text(
                        text = item.creator,
                        color = Color.Gray,
                        fontSize = 10.sp,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.padding(top = 2.dp)
                    )
                }

                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 6.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    if (item.year.isNotBlank()) {
                        Text(text = item.year, color = Color(0xFFA1A1AA), fontSize = 10.sp)
                    }
                    if (item.downloads > 0) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                imageVector = Icons.Default.Download,
                                contentDescription = null,
                                tint = VaultPrimary,
                                modifier = Modifier.size(11.dp)
                            )
                            Spacer(modifier = Modifier.width(3.dp))
                            Text(
                                text = "${item.downloads}",
                                color = VaultPrimary,
                                fontSize = 10.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }
                }
            }
        }
    }
}
