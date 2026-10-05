package org.archivevault.mobile.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import org.archivevault.mobile.data.ArchiveRepository
import org.archivevault.mobile.downloader.MobileDownloadManager
import org.archivevault.mobile.model.DownloadItem
import org.archivevault.mobile.model.DownloadStatus
import org.archivevault.mobile.ui.theme.*

@Composable
fun DownloadsScreen(
    downloadManager: MobileDownloadManager,
    onPlayAudio: (String, String) -> Unit,
    onPlayGame: (String, String) -> Unit,
    modifier: Modifier = Modifier
) {
    val items by downloadManager.items.collectAsState()

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(VaultBackground)
            .padding(horizontal = 14.dp, vertical = 8.dp)
    ) {
        // Top Card with Stats and Batch actions
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(containerColor = VaultSurface)
        ) {
            Column(modifier = Modifier.padding(12.dp)) {
                val activeCount = items.count { it.status == DownloadStatus.DOWNLOADING }
                val totalSpeed = items.filter { it.status == DownloadStatus.DOWNLOADING }.sumOf { it.speedBps }
                val speedStr = String.format("%.1f MB/s", totalSpeed / (1024f * 1024f))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "⬇️ Downloads Queue",
                        color = Color.White,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = if (activeCount > 0) "Speed: $speedStr ($activeCount active)" else "Idle",
                        color = if (activeCount > 0) VaultPrimary else Color.Gray,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold
                    )
                }

                Spacer(modifier = Modifier.height(10.dp))

                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(
                        onClick = { downloadManager.pauseAll() },
                        colors = ButtonDefaults.buttonColors(containerColor = VaultSurfaceVariant),
                        shape = RoundedCornerShape(8.dp),
                        contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp),
                        modifier = Modifier.height(34.dp)
                    ) {
                        Text("Pause All ⏸️", color = Color.White, fontSize = 11.sp)
                    }

                    Button(
                        onClick = { downloadManager.resumeAll() },
                        colors = ButtonDefaults.buttonColors(containerColor = VaultPrimary),
                        shape = RoundedCornerShape(8.dp),
                        contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp),
                        modifier = Modifier.height(34.dp)
                    ) {
                        Text("Resume All ▶️", color = Color.Black, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                    }

                    Button(
                        onClick = { downloadManager.clearCompleted() },
                        colors = ButtonDefaults.buttonColors(containerColor = VaultSurfaceVariant),
                        shape = RoundedCornerShape(8.dp),
                        contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp),
                        modifier = Modifier.height(34.dp)
                    ) {
                        Text("Clear 🧹", color = Color.Gray, fontSize = 11.sp)
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        if (items.isEmpty()) {
            Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Icon(
                        imageVector = Icons.Default.CloudDownload,
                        contentDescription = null,
                        tint = Color.DarkGray,
                        modifier = Modifier.size(64.dp)
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text("No active downloads", color = Color.Gray, fontSize = 14.sp)
                    Text("Explore archive releases and tap download", color = Color.DarkGray, fontSize = 12.sp)
                }
            }
        } else {
            LazyColumn(
                contentPadding = PaddingValues(bottom = 80.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                items(items, key = { it.id }) { item ->
                    DownloadItemCard(
                        item = item,
                        onPause = { downloadManager.pauseDownload(item.id) },
                        onResume = { downloadManager.resumeDownload(item.id) },
                        onCancel = { downloadManager.cancelDownload(item.id) },
                        onPlayAudio = { onPlayAudio(item.savePath, item.filename) },
                        onPlayGame = { onPlayGame(item.identifier, item.filename) }
                    )
                }
            }
        }
    }
}

@Composable
fun DownloadItemCard(
    item: DownloadItem,
    onPause: () -> Unit,
    onResume: () -> Unit,
    onCancel: () -> Unit,
    onPlayAudio: () -> Unit,
    onPlayGame: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = VaultSurface)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = item.filename,
                    color = Color.White,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Bold,
                    maxLines = 1,
                    modifier = Modifier.weight(1f).padding(end = 8.dp)
                )

                // Status Badge
                val (badgeBg, badgeFg) = when (item.status) {
                    DownloadStatus.DOWNLOADING -> VaultPrimary to Color.Black
                    DownloadStatus.COMPLETED -> VaultSecondary to Color.Black
                    DownloadStatus.PAUSED -> Color(0xFFF59E0B) to Color.Black
                    DownloadStatus.FAILED -> Color(0xFFEF4444) to Color.White
                    else -> Color(0xFF3F3F46) to Color.White
                }

                Surface(
                    color = badgeBg,
                    shape = RoundedCornerShape(4.dp)
                ) {
                    Text(
                        text = item.status.name,
                        color = badgeFg,
                        fontSize = 9.sp,
                        fontWeight = FontWeight.Black,
                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            // Progress Bar
            LinearProgressIndicator(
                progress = { item.progress },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(6.dp)
                    .clip(RoundedCornerShape(3.dp)),
                color = when (item.status) {
                    DownloadStatus.COMPLETED -> VaultSecondary
                    DownloadStatus.PAUSED -> Color(0xFFF59E0B)
                    else -> VaultPrimary
                },
                trackColor = Color(0xFF27272A)
            )

            Spacer(modifier = Modifier.height(8.dp))

            // Progress & Speed text
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                val downloadedStr = ArchiveRepository.formatSize(item.downloadedBytes)
                val totalStr = ArchiveRepository.formatSize(item.totalBytes)
                val pct = (item.progress * 100).toInt()

                Text(
                    text = "$downloadedStr / $totalStr ($pct%)",
                    color = Color.Gray,
                    fontSize = 11.sp
                )

                if (item.status == DownloadStatus.DOWNLOADING && item.speedBps > 0) {
                    val spdStr = String.format("%.1f MB/s", item.speedBps / (1024f * 1024f))
                    Text(
                        text = "$spdStr • ETA: ${item.etaSeconds}s",
                        color = VaultPrimary,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            // Action Buttons
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.End,
                verticalAlignment = Alignment.CenterVertically
            ) {
                if (item.status == DownloadStatus.COMPLETED) {
                    if (item.isAudio) {
                        Button(
                            onClick = onPlayAudio,
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF065F46)),
                            shape = RoundedCornerShape(6.dp),
                            modifier = Modifier.height(32.dp)
                        ) {
                            Text("▶ Play", color = Color(0xFFA7F3D0), fontSize = 11.sp, fontWeight = FontWeight.Bold)
                        }
                        Spacer(modifier = Modifier.width(6.dp))
                    } else if (item.isGame) {
                        Button(
                            onClick = onPlayGame,
                            colors = ButtonDefaults.buttonColors(containerColor = VaultSecondary),
                            shape = RoundedCornerShape(6.dp),
                            modifier = Modifier.height(32.dp)
                        ) {
                            Text("🎮 Play", color = Color.Black, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                        }
                        Spacer(modifier = Modifier.width(6.dp))
                    }
                } else if (item.status == DownloadStatus.DOWNLOADING) {
                    Button(
                        onClick = onPause,
                        colors = ButtonDefaults.buttonColors(containerColor = VaultSurfaceVariant),
                        shape = RoundedCornerShape(6.dp),
                        modifier = Modifier.height(32.dp)
                    ) {
                        Text("Pause ⏸️", color = Color.White, fontSize = 11.sp)
                    }
                    Spacer(modifier = Modifier.width(6.dp))
                } else if (item.status in listOf(DownloadStatus.PAUSED, DownloadStatus.FAILED, DownloadStatus.QUEUED)) {
                    Button(
                        onClick = onResume,
                        colors = ButtonDefaults.buttonColors(containerColor = VaultPrimary),
                        shape = RoundedCornerShape(6.dp),
                        modifier = Modifier.height(32.dp)
                    ) {
                        Text("Resume ▶️", color = Color.Black, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                    }
                    Spacer(modifier = Modifier.width(6.dp))
                }

                IconButton(
                    onClick = onCancel,
                    modifier = Modifier.size(32.dp)
                ) {
                    Icon(Icons.Default.Close, contentDescription = "Cancel", tint = Color.Gray, modifier = Modifier.size(18.dp))
                }
            }
        }
    }
}
