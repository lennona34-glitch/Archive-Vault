import ctypes
import os
import shutil
import sys
from typing import Optional
from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtGui import QAction, QFont, QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from archivevault.core.downloader import (
    STATUS_DOWNLOADING,
    STATUS_QUEUED,
    download_manager,
)
from archivevault.core.settings import settings
from archivevault.core.utils import format_size, format_speed
from archivevault.ui.arcade_tab import ArcadeTab
from archivevault.ui.audio_player import AudioPlayerWidget
from archivevault.ui.downloads_tab import DownloadsTab, VIDEO_EXTENSIONS
from archivevault.ui.item_tab import ItemTab
from archivevault.ui.search_tab import SearchTab
from archivevault.ui.settings_tab import SettingsTab
from archivevault.ui.styles import DARK_THEME

def apply_windows_dark_titlebar(window: QMainWindow):
    """
    Apply Windows DWM attributes to force a sleek dark title bar
    and eliminate any Windows accent colors (like purple).
    """
    if sys.platform != "win32":
        return
    try:
        hwnd = int(window.winId())
        # DWMWA_USE_IMMERSIVE_DARK_MODE (20 on Win11/Win10 20H1+, 19 on older Win10)
        val = ctypes.c_int(1)
        res = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 20, ctypes.byref(val), ctypes.sizeof(val)
        )
        if res != 0:
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 19, ctypes.byref(val), ctypes.sizeof(val)
            )

        # DWMWA_CAPTION_COLOR (35) - COLORREF 0x00BBGGRR for #121214 (R=0x12, G=0x12, B=0x14)
        caption_color = ctypes.c_int(0x00141212)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 35, ctypes.byref(caption_color), ctypes.sizeof(caption_color)
        )

        # DWMWA_TEXT_COLOR (36) - COLORREF 0x00BBGGRR for #F4F4F5
        text_color = ctypes.c_int(0x00F5F4F4)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 36, ctypes.byref(text_color), ctypes.sizeof(text_color)
        )
    except Exception as e:
        print(f"[MainWindow] DWM titlebar customization notice: {e}")

class MainWindow(QMainWindow):
    """ArchiveVault Main Application Window with Zen Mode and Website-Style Browsing."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ArchiveVault — Internet Archive Downloader & Explorer")
        self.resize(1200, 800)
        self.setMinimumSize(920, 600)
        self.setAcceptDrops(True)
        
        self.setStyleSheet(DARK_THEME)
        self.is_zen_mode = False

        # Set App Window & Taskbar Icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "archivevault.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        if sys.platform == "win32":
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ArchiveVault.UniversalLibrary.1.0")
            except Exception:
                pass

        self._init_ui()
        self._setup_shortcuts()
        self._connect_signals()

        # Check startup auto-resume
        if settings.auto_resume_startup:
            QTimer.singleShot(1000, download_manager.resume_all)

        # Periodic disk space check
        self.disk_timer = QTimer(self)
        self.disk_timer.timeout.connect(self._update_disk_space)
        self.disk_timer.start(5000)
        self._update_disk_space()

    def showEvent(self, event):
        super().showEvent(event)
        # Apply dark title bar after native window creation
        apply_windows_dark_titlebar(self)

    def _setup_shortcuts(self):
        # F11 toggles Zen Mode
        f11_shortcut = QShortcut(QKeySequence(Qt.Key.Key_F11), self)
        f11_shortcut.activated.connect(self.toggle_zen_mode)

        # Escape exits Zen Mode
        esc_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        esc_shortcut.activated.connect(self._on_escape_pressed)

        # Ctrl+O opens local video
        ctrl_o_shortcut = QShortcut(QKeySequence("Ctrl+O"), self)
        ctrl_o_shortcut.activated.connect(self.open_local_video)

    def _on_escape_pressed(self):
        if self.is_zen_mode:
            self.toggle_zen_mode()

    def toggle_zen_mode(self):
        """Toggle Fullscreen Zen Mode for cinematic, distraction-free immersion."""
        self.is_zen_mode = not self.is_zen_mode
        if self.is_zen_mode:
            self.showFullScreen()
            self.sidebar.hide()
            self.zen_toggle_btn.setText("✕  Exit Zen Mode (Esc)")
            self.zen_toggle_btn.setObjectName("exitZenBtn")
            self.zen_toggle_btn.setToolTip("Exit fullscreen Zen Mode (Esc or F11)")
            self.zen_toggle_btn.style().unpolish(self.zen_toggle_btn)
            self.zen_toggle_btn.style().polish(self.zen_toggle_btn)
            self.header_status_label.setText("Zen Mode active • Fullscreen immersion")
            self.statusBar().showMessage("Zen Mode active • Press Esc or F11 to exit", 4000)
        else:
            self.showNormal()
            self.sidebar.show()
            self.zen_toggle_btn.setText("⛶  Zen Mode (F11)")
            self.zen_toggle_btn.setObjectName("zenBtn")
            self.zen_toggle_btn.setToolTip("Enter full screen distraction-free Zen Mode (F11)")
            self.zen_toggle_btn.style().unpolish(self.zen_toggle_btn)
            self.zen_toggle_btn.style().polish(self.zen_toggle_btn)
            self.header_status_label.setText("🏛️ Internet Archive Universal Library")
            apply_windows_dark_titlebar(self)

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Left Sidebar ---
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        side_layout = QVBoxLayout(self.sidebar)
        side_layout.setContentsMargins(10, 16, 10, 16)
        side_layout.setSpacing(6)

        # Brand / Logo
        brand_widget = QWidget()
        brand_layout = QVBoxLayout(brand_widget)
        brand_layout.setContentsMargins(8, 0, 8, 12)
        brand_layout.setSpacing(2)

        app_title = QLabel("🏛️ ArchiveVault")
        app_title.setStyleSheet("font-size: 17px; font-weight: 800; color: #ffffff;")
        brand_layout.addWidget(app_title)

        app_sub = QLabel("Universal Digital Library")
        app_sub.setStyleSheet("font-size: 11px; color: #71717a; font-weight: 500;")
        brand_layout.addWidget(app_sub)

        side_layout.addWidget(brand_widget)

        # Navigation Buttons
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        self.btn_search = QPushButton("🌟  Browse & Search")
        self.btn_search.setObjectName("navBtn")
        self.btn_search.setCheckable(True)
        self.btn_search.setChecked(True)
        self.nav_group.addButton(self.btn_search, 0)
        side_layout.addWidget(self.btn_search)

        self.btn_item = QPushButton("📖  Subject Dossier")
        self.btn_item.setObjectName("navBtn")
        self.btn_item.setCheckable(True)
        self.nav_group.addButton(self.btn_item, 1)
        side_layout.addWidget(self.btn_item)

        self.btn_downloads = QPushButton("⬇️  Downloads")
        self.btn_downloads.setObjectName("navBtn")
        self.btn_downloads.setCheckable(True)
        self.nav_group.addButton(self.btn_downloads, 2)
        side_layout.addWidget(self.btn_downloads)

        self.btn_arcade = QPushButton("🕹️  DOSBox Arcade")
        self.btn_arcade.setObjectName("navBtn")
        self.btn_arcade.setCheckable(True)
        self.nav_group.addButton(self.btn_arcade, 3)
        side_layout.addWidget(self.btn_arcade)

        self.btn_settings = QPushButton("⚙️  Settings")
        self.btn_settings.setObjectName("navBtn")
        self.btn_settings.setCheckable(True)
        self.nav_group.addButton(self.btn_settings, 4)
        side_layout.addWidget(self.btn_settings)

        side_layout.addStretch(1)

        # Disk space indicator
        self.disk_label = QLabel("💾 Free: checking...")
        self.disk_label.setStyleSheet("font-size: 11px; color: #71717a; padding: 8px 10px;")
        side_layout.addWidget(self.disk_label)

        main_layout.addWidget(self.sidebar)

        # --- Right Stacked Content Pages ---
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # --- Top Right Header Bar (Always anchored at top right) ---
        self.top_header = QFrame()
        self.top_header.setObjectName("topHeaderBar")
        self.top_header.setStyleSheet("""
            QFrame#topHeaderBar {
                background-color: #161619;
                border-bottom: 1px solid #232328;
                min-height: 40px;
                max-height: 40px;
            }
        """)
        top_header_layout = QHBoxLayout(self.top_header)
        top_header_layout.setContentsMargins(18, 0, 18, 0)
        top_header_layout.setSpacing(12)

        self.header_status_label = QLabel("🏛️ Internet Archive Universal Library")
        self.header_status_label.setStyleSheet("color: #71717a; font-size: 12px; font-weight: 500;")
        top_header_layout.addWidget(self.header_status_label)

        top_header_layout.addStretch(1)

        # Open Video Button — In-app cinema player
        self.btn_open_video = QPushButton("🎬  Open Video (Ctrl+O)")
        self.btn_open_video.setObjectName("openVideoBtn")
        self.btn_open_video.setToolTip("Open and watch any video file from your computer in ArchiveVault Cinema (Ctrl+O)")
        self.btn_open_video.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_video.clicked.connect(lambda: self.open_local_video())
        top_header_layout.addWidget(self.btn_open_video)

        # Zen Mode Button — Permanently placed at top right
        self.zen_toggle_btn = QPushButton("⛶  Zen Mode (F11)")
        self.zen_toggle_btn.setObjectName("zenBtn")
        self.zen_toggle_btn.setToolTip("Enter full screen distraction-free Zen Mode (F11)")
        self.zen_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.zen_toggle_btn.clicked.connect(self.toggle_zen_mode)
        top_header_layout.addWidget(self.zen_toggle_btn)

        content_layout.addWidget(self.top_header)

        self.pages = QStackedWidget()

        self.search_tab = SearchTab()
        self.item_tab = ItemTab()
        self.downloads_tab = DownloadsTab()
        self.arcade_tab = ArcadeTab()
        self.settings_tab = SettingsTab()

        self.pages.addWidget(self.search_tab)     # Index 0
        self.pages.addWidget(self.item_tab)       # Index 1
        self.pages.addWidget(self.downloads_tab)  # Index 2
        self.pages.addWidget(self.arcade_tab)     # Index 3
        self.pages.addWidget(self.settings_tab)   # Index 4

        content_layout.addWidget(self.pages, stretch=1)

        # Docked Audio Player (at bottom of content area, accessible across all tabs)
        self.audio_player = AudioPlayerWidget()
        self.audio_player.hide()
        content_layout.addWidget(self.audio_player)

        main_layout.addWidget(content_container, stretch=1)

        # --- Status Bar ---
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.global_speed_label = QLabel("⬇️ 0.0 B/s")
        self.global_speed_label.setStyleSheet("font-weight: 700; color: #38bdf8; margin-right: 14px;")
        self.status_bar.addPermanentWidget(self.global_speed_label)

        self.active_status_label = QLabel("Ready")
        self.active_status_label.setStyleSheet("color: #a1a1aa; margin-right: 14px;")
        self.status_bar.addPermanentWidget(self.active_status_label)

    def _connect_signals(self):
        self.nav_group.idClicked.connect(self.pages.setCurrentIndex)
        self.search_tab.inspect_item_requested.connect(self._navigate_to_item)
        self.item_tab.back_to_browse_requested.connect(self._navigate_back_to_browse)
        self.item_tab.explore_collection_requested.connect(self._explore_collection)
        self.item_tab.download_requested.connect(self._on_download_requested)
        self.item_tab.play_audio_requested.connect(self.play_audio)
        self.item_tab.play_video_requested.connect(self.play_video)
        self.item_tab.play_dosbox_requested.connect(self._launch_dosbox_player)
        self.item_tab.open_settings_requested.connect(self._navigate_to_settings)
        self.item_tab.open_item_requested.connect(self._navigate_to_item)
        self.downloads_tab.play_media_requested.connect(self.play_audio)
        self.downloads_tab.play_video_requested.connect(self.play_video)
        self.downloads_tab.play_dosbox_requested.connect(self._launch_dosbox_player)
        self.arcade_tab.play_dosbox_requested.connect(self._launch_dosbox_player)
        self.arcade_tab.inspect_item_requested.connect(self._navigate_to_item)
        self.arcade_tab.browse_retro_requested.connect(self._browse_retro_games)
        self.audio_player.playback_state_changed.connect(self._on_audio_playback_changed)
        self.audio_player.track_changed.connect(self._on_track_changed)
        download_manager.queue_updated.connect(self._on_queue_updated)
        download_manager.item_progress.connect(self._on_progress_update)

    def _launch_dosbox_player(self, identifier: str, title: str):
        """Open the embedded retro gaming theater for MS-DOS and emulated software."""
        if hasattr(self, "audio_player") and self.audio_player.is_playing():
            self.audio_player.player.pause()

        try:
            from archivevault.ui.dosbox_player import DOSBoxPlayerDialog
            dialog = DOSBoxPlayerDialog(identifier, title, parent=self)
            dialog.exec()
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            import webbrowser
            reply = QMessageBox.warning(
                self,
                "In-App Emulator Notice",
                f"Could not initialize in-app retro player: {e}\n\nWould you like to play on archive.org in your browser instead?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                webbrowser.open(f"https://archive.org/embed/{identifier}")

    def play_video(self, source: str, title: str):
        """Play an online video stream or a locally downloaded video file in ArchiveVault Cinema."""
        if hasattr(self, "audio_player") and self.audio_player.is_playing():
            self.audio_player.player.pause()

        try:
            from archivevault.ui.video_player import VideoPlayerDialog
            dialog = VideoPlayerDialog(source, title, parent=self)
            dialog.exec()
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            import webbrowser
            reply = QMessageBox.warning(
                self,
                "In-App Cinema Notice",
                f"Could not initialize in-app video player: {e}\n\nWould you like to open the video file or link in your default media player / browser?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                if os.path.isabs(source) and os.path.exists(source):
                    from archivevault.core.utils import open_file
                    open_file(source)
                else:
                    webbrowser.open(source)

    def open_local_video(self, file_path: Optional[str] = None):
        """Open a local video file from PC and launch it in ArchiveVault Cinema."""
        if not file_path or not isinstance(file_path, str):
            file_filter = (
                "Video Files (*.mp4 *.mkv *.avi *.ogv *.webm *.mov *.flv *.wmv *.m4v *.mpg *.mpeg *.m2v *.ts *.vob *.3gp);;"
                "All Files (*.*)"
            )
            selected_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select Video to Watch in ArchiveVault Cinema",
                settings.download_dir or "",
                file_filter
            )
            if not selected_path:
                return
            file_path = selected_path

        if os.path.exists(file_path):
            title = os.path.splitext(os.path.basename(file_path))[0]
            self.play_video(file_path, title)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if any(url.isLocalFile() and url.toLocalFile().lower().endswith(VIDEO_EXTENSIONS) for url in urls):
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    local_path = url.toLocalFile()
                    if local_path.lower().endswith(VIDEO_EXTENSIONS):
                        event.acceptProposedAction()
                        title = os.path.splitext(os.path.basename(local_path))[0]
                        self.play_video(local_path, title)
                        return

    def play_audio(self, source: str, title: str):
        """Play an online audio stream or a locally downloaded audio file."""
        self.audio_player.play_track(source, title)
        self.audio_player.show()

    def _on_audio_playback_changed(self, is_playing: bool):
        current_src = self.audio_player.current_url
        if hasattr(self.item_tab, "update_playback_state"):
            self.item_tab.update_playback_state(current_src, is_playing)
        if hasattr(self.downloads_tab, "update_playback_state"):
            self.downloads_tab.update_playback_state(current_src, is_playing)

        if is_playing:
            track_title = self.audio_player.current_title
            is_local = os.path.isabs(current_src) and os.path.exists(current_src)
            prefix = "🎵 Playing" if is_local else "🎵 Streaming"
            self.header_status_label.setText(f"{prefix}: {track_title}")
        else:
            if not self.is_zen_mode:
                self.header_status_label.setText("🏛️ Internet Archive Universal Library")

    def _on_track_changed(self, url: str):
        is_playing = self.audio_player.is_playing()
        if hasattr(self.item_tab, "update_playback_state"):
            self.item_tab.update_playback_state(url, is_playing)
        if hasattr(self.downloads_tab, "update_playback_state"):
            self.downloads_tab.update_playback_state(url, is_playing)

    def _navigate_to_item(self, identifier: str):
        self.item_tab.load_item(identifier)
        self.btn_item.setChecked(True)
        self.pages.setCurrentIndex(1)

    def _navigate_to_settings(self):
        self.btn_settings.setChecked(True)
        self.pages.setCurrentIndex(4)

    def _navigate_to_arcade(self):
        self.btn_arcade.setChecked(True)
        self.pages.setCurrentIndex(3)

    def _browse_retro_games(self):
        self.btn_search.setChecked(True)
        self.pages.setCurrentIndex(0)
        self.search_tab.select_category("games")

    def _navigate_back_to_browse(self):
        self.btn_search.setChecked(True)
        self.pages.setCurrentIndex(0)

    def _explore_collection(self, collection_id: str, title: str):
        self.search_tab.explore_collection(collection_id, title)
        self.btn_search.setChecked(True)
        self.pages.setCurrentIndex(0)

    def _on_download_requested(self, files: list, identifier: str):
        download_manager.add_batch_downloads(files, identifier)
        self.btn_downloads.setChecked(True)
        self.pages.setCurrentIndex(2)

    def _on_queue_updated(self):
        active = sum(1 for it in download_manager.items if it.status == STATUS_DOWNLOADING)
        queued = sum(1 for it in download_manager.items if it.status == STATUS_QUEUED)

        badge_text = f"⬇️  Downloads ({active})" if active > 0 else "⬇️  Downloads"
        self.btn_downloads.setText(badge_text)

        if active > 0:
            self.active_status_label.setText(f"Downloading {active} item(s)...")
        elif queued > 0:
            self.active_status_label.setText(f"{queued} item(s) in queue")
        else:
            self.active_status_label.setText("Ready")

    def _on_progress_update(self, item_id: str, downloaded: int, total: int, speed: float, eta: float):
        total_speed = sum(it.speed for it in download_manager.items if it.status == STATUS_DOWNLOADING)
        self.global_speed_label.setText(f"⬇️ {format_speed(total_speed)}")

    def _update_disk_space(self):
        try:
            target_dir = settings.download_dir
            if not os.path.exists(target_dir):
                target_dir = os.path.dirname(os.path.abspath(target_dir))
            stat = shutil.disk_usage(target_dir)
            free_str = format_size(stat.free)
            self.disk_label.setText(f"💾 Free: {free_str}")
        except Exception:
            self.disk_label.setText("💾 Ready")
