package org.archivevault.mobile.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.SportsEsports
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import kotlinx.coroutines.launch
import org.archivevault.mobile.data.ArchiveRepository
import org.archivevault.mobile.model.ArchiveFile
import org.archivevault.mobile.model.ItemMetadata
import org.archivevault.mobile.ui.theme.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DossierScreen(
    identifier: String,
    onBack: () -> Unit,
    onPlayGame: (String, String) -> Unit,
    onPlayAudio: (String, String) -> Unit,
    onDownloadFile: (String, String, Long) -> Unit,
    modifier: Modifier = Modifier
) {
    var metadata by remember { mutableStateOf<ItemMetadata?>(null) }
    var isLoading by remember { mutableStateOf(true) }
    val scope = rememberCoroutineScope()

    LaunchedEffect(identifier) {
        scope.launch {
            isLoading = true
            metadata = ArchiveRepository.getItemMetadata(identifier)
            isLoading = false
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Subject Dossier", color = Color.White, fontSize = 16.sp, fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back", tint = Color.White)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = VaultSurface)
            )
        },
        containerColor = VaultBackground
    ) { padding ->
        if (isLoading) {
            Box(modifier = Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = VaultPrimary)
            }
        } else if (metadata == null) {
            Box(modifier = Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                Text("Failed to load archive documentation.", color = Color.Gray)
            }
        } else {
            val meta = metadata!!
            val scrollState = rememberScrollState()

            Column(
                modifier = modifier
                    .fillMaxSize()
                    .padding(padding)
                    .verticalScroll(scrollState)
                    .padding(16.dp)
            ) {
                // Hero Header Card
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = VaultSurface)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Row(horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                            AsyncImage(
                                model = "https://archive.org/services/img/${meta.identifier}",
                                contentDescription = meta.title,
                                contentScale = ContentScale.Crop,
                                modifier = Modifier
                                    .size(110.dp)
                                    .clip(RoundedCornerShape(12.dp))
                                    .background(Color(0xFF27272A))
                            )
                            Column(modifier = Modifier.weight(1f)) {
                                Surface(
                                    color = VaultPrimary,
                                    shape = RoundedCornerShape(4.dp),
                                    modifier = Modifier.padding(bottom = 6.dp)
                                ) {
                                    Text(
                                        text = meta.mediatype.uppercase(),
                                        color = Color.Black,
                                        fontSize = 10.sp,
                                        fontWeight = FontWeight.Black,
                                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                    )
                                }
                                Text(
                                    text = meta.title,
                                    color = Color.White,
                                    fontSize = 17.sp,
                                    fontWeight = FontWeight.Bold,
                                    maxLines = 3
                                )
                                if (meta.creator.isNotBlank()) {
                                    Text(
                                        text = "By ${meta.creator}",
                                        color = Color.Gray,
                                        fontSize = 12.sp,
                                        modifier = Modifier.padding(top = 4.dp)
                                    )
                                }
                            }
                        }

                        Spacer(modifier = Modifier.height(14.dp))

                        // Action Buttons Row
                        val isGame = meta.mediatype == "software" || meta.identifier.startsWith("msdos_")
                        val audioFile = meta.files.firstOrNull { it.name.lowercase().let { n -> n.endsWith(".mp3") || n.endsWith(".flac") || n.endsWith(".ogg") } }

                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(10.dp)
                        ) {
                            if (isGame) {
                                Button(
                                    onClick = { onPlayGame(meta.identifier, meta.title) },
                                    colors = ButtonDefaults.buttonColors(containerColor = VaultSecondary),
                                    shape = RoundedCornerShape(10.dp),
                                    contentPadding = PaddingValues(horizontal = 10.dp, vertical = 8.dp),
                                    modifier = Modifier.weight(1f).heightIn(min = 48.dp)
                                ) {
                                    Icon(Icons.Default.SportsEsports, contentDescription = null, tint = Color.Black, modifier = Modifier.size(18.dp))
                                    Spacer(modifier = Modifier.width(6.dp))
                                    Text("Play DOSBox", color = Color.Black, fontSize = 12.sp, fontWeight = FontWeight.ExtraBold, maxLines = 1)
                                }
                            } else if (audioFile != null) {
                                Button(
                                    onClick = { onPlayAudio(audioFile.url, "${meta.title} — ${audioFile.name}") },
                                    colors = ButtonDefaults.buttonColors(containerColor = VaultPrimary),
                                    shape = RoundedCornerShape(10.dp),
                                    contentPadding = PaddingValues(horizontal = 10.dp, vertical = 8.dp),
                                    modifier = Modifier.weight(1f).heightIn(min = 48.dp)
                                ) {
                                    Icon(Icons.Default.PlayArrow, contentDescription = null, tint = Color.Black, modifier = Modifier.size(18.dp))
                                    Spacer(modifier = Modifier.width(6.dp))
                                    Text("Play Audio", color = Color.Black, fontSize = 12.sp, fontWeight = FontWeight.ExtraBold, maxLines = 1)
                                }
                            }

                            val primaryFile = meta.files.firstOrNull()
                            if (primaryFile != null) {
                                Button(
                                    onClick = { onDownloadFile(meta.identifier, primaryFile.name, primaryFile.sizeBytes) },
                                    colors = ButtonDefaults.buttonColors(containerColor = VaultSurfaceVariant),
                                    shape = RoundedCornerShape(10.dp),
                                    contentPadding = PaddingValues(horizontal = 10.dp, vertical = 8.dp),
                                    modifier = Modifier.weight(1f).heightIn(min = 48.dp)
                                ) {
                                    Icon(Icons.Default.Download, contentDescription = null, tint = VaultPrimary, modifier = Modifier.size(18.dp))
                                    Spacer(modifier = Modifier.width(6.dp))
                                    Text("Download", color = Color.White, fontSize = 12.sp, fontWeight = FontWeight.Bold, maxLines = 1)
                                }
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(18.dp))

                // Subject Dossier / Article Card
                if (meta.description.isNotBlank()) {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(14.dp),
                        colors = CardDefaults.cardColors(containerColor = VaultSurface)
                    ) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Text(
                                text = "📖 Historical Dossier & Details",
                                color = Color.White,
                                fontSize = 15.sp,
                                fontWeight = FontWeight.Bold
                            )
                            Spacer(modifier = Modifier.height(8.dp))
                            // Simple HTML tag cleanup
                            val cleanDesc = meta.description.replace(Regex("<[^>]*>"), "")
                            Text(
                                text = cleanDesc,
                                color = Color(0xFFD4D4D8),
                                fontSize = 13.sp,
                                lineHeight = 20.sp
                            )
                        }
                    }
                    Spacer(modifier = Modifier.height(18.dp))
                }

                // Curated Files Section
                Text(
                    text = "📦 Curated Download Links (${meta.files.size} files)",
                    color = Color.White,
                    fontSize = 15.sp,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(bottom = 10.dp)
                )

                meta.files.take(20).forEach { file ->
                    CuratedMobileCard(
                        file = file,
                        onDownload = { onDownloadFile(meta.identifier, file.name, file.sizeBytes) },
                        onListen = { onPlayAudio(file.url, "${meta.title} — ${file.name}") }
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                }
            }
        }
    }
}

@Composable
fun CuratedMobileCard(
    file: ArchiveFile,
    onDownload: () -> Unit,
    onListen: () -> Unit
) {
    val isAudio = file.name.lowercase().let { it.endsWith(".mp3") || it.endsWith(".flac") || it.endsWith(".ogg") }

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(10.dp),
        colors = CardDefaults.cardColors(containerColor = VaultSurface)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Column(modifier = Modifier.weight(1f).padding(end = 8.dp)) {
                Text(
                    text = file.name,
                    color = Color.White,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.SemiBold,
                    maxLines = 1
                )
                Text(
                    text = "${file.format} • ${file.sizeFormatted}",
                    color = Color.Gray,
                    fontSize = 11.sp
                )
            }

            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                if (isAudio) {
                    IconButton(
                        onClick = onListen,
                        modifier = Modifier
                            .size(34.dp)
                            .clip(RoundedCornerShape(6.dp))
                            .background(Color(0xFF065F46))
                    ) {
                        Icon(Icons.Default.PlayArrow, contentDescription = "Play", tint = Color.White, modifier = Modifier.size(18.dp))
                    }
                }

                Button(
                    onClick = onDownload,
                    colors = ButtonDefaults.buttonColors(containerColor = VaultSurfaceVariant),
                    shape = RoundedCornerShape(6.dp),
                    contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp),
                    modifier = Modifier.height(34.dp)
                ) {
                    Text("⬇️ Get", color = Color.White, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                }
            }
        }
    }
}
