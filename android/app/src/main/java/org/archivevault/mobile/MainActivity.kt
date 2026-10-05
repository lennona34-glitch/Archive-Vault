package org.archivevault.mobile

import android.Manifest
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.view.KeyEvent
import android.view.MotionEvent
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import org.archivevault.mobile.input.GameInputHandler
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.Explore
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import org.archivevault.mobile.downloader.MobileDownloadManager
import org.archivevault.mobile.model.DownloadStatus
import org.archivevault.mobile.player.AudioPlayerController
import org.archivevault.mobile.service.AudioPlaybackService
import org.archivevault.mobile.service.DownloadService
import org.archivevault.mobile.ui.components.MiniAudioPlayer
import org.archivevault.mobile.ui.screens.*
import org.archivevault.mobile.ui.theme.ArchiveVaultTheme
import org.archivevault.mobile.ui.theme.VaultBackground
import org.archivevault.mobile.ui.theme.VaultPrimary
import org.archivevault.mobile.ui.theme.VaultSurface

sealed class Screen {
    object Browse : Screen()
    data class Dossier(val identifier: String) : Screen()
    data class DOSBox(val identifier: String, val title: String) : Screen()
    object Downloads : Screen()
    object Settings : Screen()
}

enum class BottomTab(val label: String, val icon: ImageVector) {
    EXPLORE("Explore", Icons.Default.Explore),
    DOWNLOADS("Downloads", Icons.Default.Download),
    SETTINGS("Settings", Icons.Default.Settings)
}

class MainActivity : ComponentActivity() {

    private lateinit var downloadManager: MobileDownloadManager
    private lateinit var audioController: AudioPlayerController
    private val gameInputHandler = GameInputHandler()

    private val notificationPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { /* Permission handled */ }

    override fun dispatchKeyEvent(event: KeyEvent): Boolean {
        if (gameInputHandler.handleKeyEvent(event)) {
            return true
        }
        return super.dispatchKeyEvent(event)
    }

    override fun dispatchGenericMotionEvent(event: MotionEvent): Boolean {
        if (gameInputHandler.handleMotionEvent(event)) {
            return true
        }
        return super.dispatchGenericMotionEvent(event)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        downloadManager = MobileDownloadManager.getInstance(this)
        audioController = AudioPlayerController.getInstance(this)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
        }

        setContent {
            ArchiveVaultTheme {
                MainAppContainer(
                    downloadManager = downloadManager,
                    audioController = audioController,
                    gameInputHandler = gameInputHandler,
                    onStartDownloadService = {
                        val intent = Intent(this, DownloadService::class.java)
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                            startForegroundService(intent)
                        } else {
                            startService(intent)
                        }
                    },
                    onStartAudioService = {
                        val intent = Intent(this, AudioPlaybackService::class.java)
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                            startForegroundService(intent)
                        } else {
                            startService(intent)
                        }
                    }
                )
            }
        }
    }
}

@Composable
fun MainAppContainer(
    downloadManager: MobileDownloadManager,
    audioController: AudioPlayerController,
    gameInputHandler: GameInputHandler,
    onStartDownloadService: () -> Unit,
    onStartAudioService: () -> Unit
) {
    var currentScreen by remember { mutableStateOf<Screen>(Screen.Browse) }
    var selectedBottomTab by remember { mutableStateOf(BottomTab.EXPLORE) }

    val audioState by audioController.trackState.collectAsState()
    val downloads by downloadManager.items.collectAsState()
    val activeDownloadsCount = downloads.count { it.status == DownloadStatus.DOWNLOADING }

    // If on DOSBox fullscreen screen, hide standard bottom navigation
    val isFullscreenGame = currentScreen is Screen.DOSBox

    Scaffold(
        bottomBar = {
            if (!isFullscreenGame) {
                Column(modifier = Modifier.background(VaultSurface)) {
                    // Floating Mini Audio Player Dock
                    MiniAudioPlayer(
                        state = audioState,
                        onTogglePlay = { audioController.togglePlayPause() },
                        onClose = { audioController.stop() }
                    )

                    // Bottom Navigation Bar
                    NavigationBar(
                        containerColor = VaultSurface,
                        tonalElevation = 4.dp
                    ) {
                        BottomTab.values().forEach { tab ->
                            val isSelected = selectedBottomTab == tab && currentScreen !is Screen.Dossier
                            NavigationBarItem(
                                selected = isSelected,
                                onClick = {
                                    selectedBottomTab = tab
                                    currentScreen = when (tab) {
                                        BottomTab.EXPLORE -> Screen.Browse
                                        BottomTab.DOWNLOADS -> Screen.Downloads
                                        BottomTab.SETTINGS -> Screen.Settings
                                    }
                                },
                                icon = {
                                    if (tab == BottomTab.DOWNLOADS && activeDownloadsCount > 0) {
                                        BadgedBox(
                                            badge = {
                                                Badge(containerColor = VaultPrimary) {
                                                    Text("$activeDownloadsCount", color = Color.Black, fontSize = 10.sp)
                                                }
                                            }
                                        ) {
                                            Icon(tab.icon, contentDescription = tab.label)
                                        }
                                    } else {
                                        Icon(tab.icon, contentDescription = tab.label)
                                    }
                                },
                                label = { Text(tab.label, fontSize = 11.sp) },
                                colors = NavigationBarItemDefaults.colors(
                                    selectedIconColor = Color.Black,
                                    selectedTextColor = VaultPrimary,
                                    indicatorColor = VaultPrimary,
                                    unselectedIconColor = Color.Gray,
                                    unselectedTextColor = Color.Gray
                                )
                            )
                        }
                    }
                }
            }
        },
        containerColor = VaultBackground
    ) { padding ->
        Box(modifier = Modifier.padding(if (isFullscreenGame) PaddingValues(0.dp) else padding)) {
            when (val screen = currentScreen) {
                is Screen.Browse -> {
                    BrowseScreen(
                        onItemSelected = { ident ->
                            currentScreen = Screen.Dossier(ident)
                        }
                    )
                }
                is Screen.Dossier -> {
                    DossierScreen(
                        identifier = screen.identifier,
                        onBack = { currentScreen = Screen.Browse },
                        onPlayGame = { ident, title ->
                            currentScreen = Screen.DOSBox(ident, title)
                        },
                        onPlayAudio = { url, title ->
                            audioController.play(url, title)
                            onStartAudioService()
                        },
                        onDownloadFile = { ident, fname, size ->
                            val fileUrl = "https://archive.org/download/$ident/${java.net.URLEncoder.encode(fname, "UTF-8").replace("+", "%20")}"
                            downloadManager.enqueueDownload(ident, fname, fileUrl, size)
                            onStartDownloadService()
                            selectedBottomTab = BottomTab.DOWNLOADS
                            currentScreen = Screen.Downloads
                        }
                    )
                }
                is Screen.DOSBox -> {
                    DOSBoxScreen(
                        identifier = screen.identifier,
                        title = screen.title,
                        inputHandler = gameInputHandler,
                        onClose = { currentScreen = Screen.Browse }
                    )
                }
                is Screen.Downloads -> {
                    DownloadsScreen(
                        downloadManager = downloadManager,
                        onPlayAudio = { url, title ->
                            audioController.play(url, title)
                            onStartAudioService()
                        },
                        onPlayGame = { ident, title ->
                            currentScreen = Screen.DOSBox(ident, title)
                        }
                    )
                }
                is Screen.Settings -> {
                    SettingsScreen()
                }
            }
        }
    }
}
