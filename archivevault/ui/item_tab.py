import os
import urllib.parse
import webbrowser
from typing import Dict, List, Optional, Tuple
import requests
from PyQt6.QtCore import QObject, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon, QKeySequence, QPixmap, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from archivevault.core.api import ia_api
from archivevault.core.utils import format_size
from archivevault.ui.audio_player import AudioPlayerWidget
from archivevault.ui.styles import get_mediatype_badge_color

CONTENT_EXTENSIONS = (
    '.zip', '.iso', '.bin', '.cue', '.chd', '.img', '.rom', '.exe',
    '.mp4', '.mkv', '.avi', '.ogv', '.webm', '.mov', '.flv', '.wmv', '.m4v',
    '.mpg', '.mpeg', '.m2v', '.ts', '.vob', '.3gp',
    '.mp3', '.flac', '.ogg', '.wav', '.m4a', '.aac', '.opus', '.shn', '.mid', '.midi',
    '.pdf', '.epub', '.djvu', '.cbr', '.cbz', '.tar', '.7z', '.gz'
)

AUDIO_EXTENSIONS = ('.mp3', '.flac', '.ogg', '.wav', '.m4a', '.aac', '.opus', '.wma', '.aiff', '.shn', '.mid', '.midi', '.wv', '.ape')
VIDEO_EXTENSIONS = ('.mp4', '.mkv', '.avi', '.ogv', '.webm', '.mov', '.flv', '.wmv', '.m4v', '.mpg', '.mpeg', '.m2v', '.ts', '.vob', '.3gp')

def classify_item_files(files: List[dict]) -> Tuple[List[dict], List[dict]]:
    """
    Intelligently separate files into curated primary content releases
    and raw supplementary/derivative files.
    """
    curated = []
    supplementary = []

    for f in files:
        name_lower = f["name"].lower()
        # Skip technical metadata
        is_meta = name_lower.endswith(('.xml', '.sqlite', '_files.xml', '_meta.xml', '.torrent', '.json', '.sha1', '.md5'))
        is_content = name_lower.endswith(CONTENT_EXTENSIONS) and not is_meta
        
        if is_content:
            curated.append(f)
        else:
            supplementary.append(f)

    # Sort curated by size descending (largest main releases first)
    curated.sort(key=lambda x: x.get("size_bytes", 0), reverse=True)
    return curated, supplementary

class ItemLoaderSignals(QObject):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

class ItemLoaderWorker(QThread):
    def __init__(self, identifier: str):
        super().__init__()
        self.identifier = identifier
        self.signals = ItemLoaderSignals()

    def run(self):
        try:
            data = ia_api.get_item_metadata(self.identifier)
            self.signals.finished.emit(data)
        except Exception as e:
            self.signals.error.emit(str(e))

class CuratedFileCard(QFrame):
    """Card widget for a curated primary content file with 1-click download."""
    download_clicked = pyqtSignal(dict)
    listen_clicked = pyqtSignal(dict)
    watch_clicked = pyqtSignal(dict)
    process_torrent_clicked = pyqtSignal(dict)
    checked_changed = pyqtSignal()

    def __init__(self, file_info: dict, parent=None):
        super().__init__(parent)
        self.file_info = file_info
        self.is_playing = False
        self.listen_btn: Optional[QPushButton] = None
        self.watch_btn: Optional[QPushButton] = None
        self.setObjectName("curatedCard")
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        self.checkbox = QCheckBox()
        self.checkbox.stateChanged.connect(lambda: self.checked_changed.emit())
        layout.addWidget(self.checkbox)

        # File icon according to extension
        fname = self.file_info["name"].lower()
        if fname.endswith(('.zip', '.7z', '.iso', '.bin', '.rom', '.exe')):
            icon_str = "🎮"
        elif fname.endswith(VIDEO_EXTENSIONS):
            icon_str = "🎬"
        elif fname.endswith(AUDIO_EXTENSIONS):
            icon_str = "🎵"
        elif fname.endswith(('.pdf', '.epub', '.djvu')):
            icon_str = "📖"
        else:
            icon_str = "💿"

        icon_lbl = QLabel(icon_str)
        icon_lbl.setStyleSheet("font-size: 18px;")
        layout.addWidget(icon_lbl)

        # File details
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        name_lbl = QLabel(self.file_info["name"])
        name_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #f4f4f5;")
        name_lbl.setWordWrap(True)
        info_layout.addWidget(name_lbl)

        fmt = self.file_info.get("format", "FILE")
        sz = self.file_info.get("size_formatted", "?")
        src = self.file_info.get("source", "original").capitalize()
        meta_lbl = QLabel(f"Format: {fmt}  •  Size: {sz}  •  Type: {src}")
        meta_lbl.setStyleSheet("font-size: 11px; color: #a1a1aa;")
        info_layout.addWidget(meta_lbl)

        layout.addLayout(info_layout, stretch=1)

        # Action Buttons on right: Listen/Watch + Download
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        if fname.endswith(AUDIO_EXTENSIONS):
            self.listen_btn = QPushButton("▶ Listen")
            self.listen_btn.setObjectName("listenBtn")
            self.listen_btn.setFixedSize(92, 32)
            self.listen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.listen_btn.setStyleSheet("""
                QPushButton#listenBtn {
                    background-color: #065f46;
                    color: #a7f3d0;
                    border: 1px solid #047857;
                    border-radius: 6px;
                    font-weight: 600;
                    font-size: 12px;
                }
                QPushButton#listenBtn:hover {
                    background-color: #047857;
                    color: #ffffff;
                }
            """)
            self.listen_btn.clicked.connect(lambda: self.listen_clicked.emit(self.file_info))
            btn_layout.addWidget(self.listen_btn)
        elif fname.endswith(VIDEO_EXTENSIONS):
            self.watch_btn = QPushButton("🎬 Watch")
            self.watch_btn.setObjectName("listenBtn")
            self.watch_btn.setFixedSize(92, 32)
            self.watch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.watch_btn.setStyleSheet("""
                QPushButton#listenBtn {
                    background-color: #1e3a8a;
                    color: #bfdbfe;
                    border: 1px solid #1d4ed8;
                    border-radius: 6px;
                    font-weight: 600;
                    font-size: 12px;
                }
                QPushButton#listenBtn:hover {
                    background-color: #1d4ed8;
                    color: #ffffff;
                }
            """)
            self.watch_btn.clicked.connect(lambda: self.watch_clicked.emit(self.file_info))
            btn_layout.addWidget(self.watch_btn)
        elif fname.endswith('.torrent'):
            self.proc_torrent_btn = QPushButton("⚡ Process")
            self.proc_torrent_btn.setFixedSize(92, 32)
            self.proc_torrent_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.proc_torrent_btn.setStyleSheet("""
                QPushButton {
                    background-color: #581c87;
                    color: #e9d5ff;
                    border: 1px solid #7e22ce;
                    border-radius: 6px;
                    font-weight: 700;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #7e22ce;
                    color: #ffffff;
                }
            """)
            self.proc_torrent_btn.setToolTip("Inspect torrent payload files and download directly via HTTP resume")
            self.proc_torrent_btn.clicked.connect(lambda: self.process_torrent_clicked.emit(self.file_info))
            btn_layout.addWidget(self.proc_torrent_btn)

        # Direct 1-click Download button
        dl_btn = QPushButton("⬇️ Download")
        dl_btn.setObjectName("primaryBtn")
        dl_btn.setFixedSize(110, 32)
        dl_btn.clicked.connect(lambda: self.download_clicked.emit(self.file_info))
        btn_layout.addWidget(dl_btn)

        layout.addLayout(btn_layout)

    def set_playing_state(self, playing: bool):
        if self.listen_btn:
            self.is_playing = playing
            if playing:
                self.listen_btn.setText("⏸ Pause")
                self.listen_btn.setStyleSheet("""
                    QPushButton#listenBtn {
                        background-color: #2563eb;
                        color: #ffffff;
                        border: 1px solid #1d4ed8;
                        border-radius: 6px;
                        font-weight: 700;
                        font-size: 12px;
                    }
                    QPushButton#listenBtn:hover {
                        background-color: #1d4ed8;
                    }
                """)
            else:
                self.listen_btn.setText("▶ Listen")
                self.listen_btn.setStyleSheet("""
                    QPushButton#listenBtn {
                        background-color: #065f46;
                        color: #a7f3d0;
                        border: 1px solid #047857;
                        border-radius: 6px;
                        font-weight: 600;
                        font-size: 12px;
                    }
                    QPushButton#listenBtn:hover {
                        background-color: #047857;
                        color: #ffffff;
                    }
                """)

    def is_checked(self) -> bool:
        return self.checkbox.isChecked()

    def set_checked(self, checked: bool):
        self.checkbox.setChecked(checked)

class ItemTab(QWidget):
    """
    Subject Feature Article & Curated Vault view.
    Presents an immersive magazine-style article, online preview/play,
    and curated 1-click download links.
    """
    download_requested = pyqtSignal(list, str) # files_list, identifier
    back_to_browse_requested = pyqtSignal()
    explore_collection_requested = pyqtSignal(str, str) # identifier, title
    play_audio_requested = pyqtSignal(str, str) # source_url, title
    play_video_requested = pyqtSignal(str, str) # source_url, title
    play_dosbox_requested = pyqtSignal(str, str) # identifier, title
    open_settings_requested = pyqtSignal()
    open_item_requested = pyqtSignal(str) # identifier

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_item_data: Optional[dict] = None
        self.curated_files: List[dict] = []
        self.supplementary_files: List[dict] = []
        self.curated_cards: List[CuratedFileCard] = []
        self.current_playing_file: Optional[dict] = None
        self.is_audio_playing: bool = False
        self.current_playing_url: Optional[str] = None
        self._loader_worker: Optional[ItemLoaderWorker] = None
        self.curated_display_limit: int = 50
        
        self._init_ui()
        self._setup_shortcuts()

    def _setup_shortcuts(self):
        # Escape or Backspace takes user back to browse when this tab is active
        esc_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        esc_shortcut.activated.connect(self._on_back_pressed)

    def _on_back_pressed(self):
        self.back_to_browse_requested.emit()

    def _init_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # --- Top Navigation Bar ---
        nav_bar = QFrame()
        nav_bar.setStyleSheet("background-color: #18181b; border-bottom: 1px solid #27272a; padding: 10px 20px;")
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(16, 8, 16, 8)
        nav_layout.setSpacing(12)

        self.back_btn = QPushButton("◀ Back to Browse")
        self.back_btn.setObjectName("backBtn")
        self.back_btn.clicked.connect(self._on_back_pressed)
        nav_layout.addWidget(self.back_btn)

        self.id_pill = QLabel("Subject Dossier")
        self.id_pill.setStyleSheet("font-size: 13px; font-weight: 600; color: #a1a1aa;")
        nav_layout.addWidget(self.id_pill)

        nav_layout.addStretch(1)

        self.web_btn = QPushButton("Open on Archive.org 🌐")
        self.web_btn.clicked.connect(self._open_web)
        self.web_btn.setEnabled(False)
        nav_layout.addWidget(self.web_btn)

        self.copy_btn = QPushButton("Copy Link 🔗")
        self.copy_btn.clicked.connect(self._copy_link)
        self.copy_btn.setEnabled(False)
        nav_layout.addWidget(self.copy_btn)

        outer_layout.addWidget(nav_bar)

        # Loading bar
        self.loading_bar = QProgressBar()
        self.loading_bar.setRange(0, 0)
        self.loading_bar.setFixedHeight(3)
        self.loading_bar.setTextVisible(False)
        self.loading_bar.hide()
        outer_layout.addWidget(self.loading_bar)

        # --- Scrollable Article Canvas ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self.canvas = QWidget()
        self.canvas_layout = QVBoxLayout(self.canvas)
        self.canvas_layout.setContentsMargins(28, 24, 28, 24)
        self.canvas_layout.setSpacing(20)

        # --- Hero Header Section ---
        self.hero_frame = QFrame()
        self.hero_frame.setObjectName("articleCard")
        hero_layout = QHBoxLayout(self.hero_frame)
        hero_layout.setContentsMargins(20, 20, 20, 20)
        hero_layout.setSpacing(20)

        # Poster / Artwork
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(150, 150)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setStyleSheet("background-color: #27272a; border-radius: 10px; border: 1px solid #3f3f46;")
        self.cover_label.setText("📦")
        hero_layout.addWidget(self.cover_label)

        # Hero Info & Action Hub
        hero_info = QVBoxLayout()
        hero_info.setSpacing(8)

        # Top Badge row
        badge_row = QHBoxLayout()
        badge_row.setSpacing(8)

        self.mediatype_badge = QLabel("SUBJECT")
        self.mediatype_badge.setStyleSheet("font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 4px; background: #3b82f6; color: white;")
        badge_row.addWidget(self.mediatype_badge)

        self.meta_summary_label = QLabel("")
        self.meta_summary_label.setStyleSheet("font-size: 12px; color: #a1a1aa;")
        badge_row.addWidget(self.meta_summary_label, stretch=1)
        hero_info.addLayout(badge_row)

        # Big Headline
        self.headline_label = QLabel("Select an item from the browse feed")
        self.headline_label.setStyleSheet("font-size: 22px; font-weight: 800; color: #ffffff;")
        self.headline_label.setWordWrap(True)
        hero_info.addWidget(self.headline_label)

        # Creator / Date line
        self.author_line = QLabel("")
        self.author_line.setStyleSheet("font-size: 13px; color: #d4d4d8;")
        hero_info.addWidget(self.author_line)

        # Login Required Warning Banner (shown only for 'loggedin' restricted collections when user isn't logged in)
        self.login_warning_banner = QFrame()
        self.login_warning_banner.setStyleSheet("""
            QFrame {
                background-color: #291e10;
                border: 1px solid #d97706;
                border-radius: 6px;
                padding: 6px 12px;
            }
        """)
        lw_layout = QHBoxLayout(self.login_warning_banner)
        lw_layout.setContentsMargins(6, 2, 6, 2)
        lw_layout.setSpacing(10)
        
        lw_icon = QLabel("🔐")
        lw_icon.setStyleSheet("font-size: 16px;")
        lw_layout.addWidget(lw_icon)
        
        lw_text = QLabel(
            "<b>Internet Archive Login Required:</b> This collection requires an Archive.org account to download files. "
            "Add your free S3 keys in Settings to download, or switch to open collections like MAME 0.264."
        )
        lw_text.setTextFormat(Qt.TextFormat.RichText)
        lw_text.setStyleSheet("color: #fde68a; font-size: 11.5px;")
        lw_text.setWordWrap(True)
        lw_layout.addWidget(lw_text, stretch=1)
        
        btn_fix_login = QPushButton("⚙️ Settings")
        btn_fix_login.setFixedSize(80, 26)
        btn_fix_login.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_fix_login.setStyleSheet("""
            QPushButton {
                background-color: #d97706;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #f59e0b;
            }
        """)
        btn_fix_login.clicked.connect(self.open_settings_requested.emit)
        lw_layout.addWidget(btn_fix_login)

        self.login_warning_banner.hide()
        hero_info.addWidget(self.login_warning_banner)

        # Interactive Play / Action Buttons
        self.action_btn_row = QHBoxLayout()
        self.action_btn_row.setSpacing(12)

        self.play_online_btn = QPushButton("▶️ Play / Preview Online")
        self.play_online_btn.setObjectName("playBtn")
        self.play_online_btn.clicked.connect(self._launch_online_experience)
        self.play_online_btn.setEnabled(False)
        self.action_btn_row.addWidget(self.play_online_btn)

        self.download_primary_btn = QPushButton("⚡ Download Main Release")
        self.download_primary_btn.setObjectName("primaryBtn")
        self.download_primary_btn.setStyleSheet("font-size: 13px; font-weight: 700; padding: 8px 18px;")
        self.download_primary_btn.clicked.connect(self._download_primary_release)
        self.download_primary_btn.setEnabled(False)
        self.action_btn_row.addWidget(self.download_primary_btn)

        self.download_torrent_btn = QPushButton("🧲 Download Full Archive via Torrent")
        self.download_torrent_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7c3aed, stop:1 #6d28d9);
                color: #ffffff;
                border: 1px solid #5b21b6;
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: 700;
                font-size: 13px;
                min-height: 24px;
            }
            QPushButton:hover {
                background: #8b5cf6;
            }
        """)
        self.download_torrent_btn.clicked.connect(self._download_item_torrent)
        self.download_torrent_btn.hide()
        self.action_btn_row.addWidget(self.download_torrent_btn)

        self.action_btn_row.addStretch(1)
        hero_info.addLayout(self.action_btn_row)

        hero_layout.addLayout(hero_info, stretch=1)
        self.canvas_layout.addWidget(self.hero_frame)

        # --- The Article / Dossier Section ---
        self.article_box = QFrame()
        self.article_box.setObjectName("articleCard")
        article_layout = QVBoxLayout(self.article_box)
        article_layout.setContentsMargins(22, 18, 22, 18)
        article_layout.setSpacing(12)

        art_title = QLabel("📖 Subject Dossier & Historical Context")
        art_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #38bdf8;")
        article_layout.addWidget(art_title)

        self.article_browser = QTextBrowser()
        self.article_browser.setStyleSheet(
            "background: transparent; border: none; color: #d4d4d8; "
            "font-size: 13.5px; line-height: 1.6; selection-background-color: #2563eb;"
        )
        self.article_browser.setOpenExternalLinks(True)
        self.article_browser.setMinimumHeight(140)
        article_layout.addWidget(self.article_browser)

        self.canvas_layout.addWidget(self.article_box)

        # --- Curated Download Vault Section ---
        self.vault_box = QFrame()
        self.vault_box.setObjectName("articleCard")
        self.vault_layout = QVBoxLayout(self.vault_box)
        self.vault_layout.setContentsMargins(22, 18, 22, 18)
        self.vault_layout.setSpacing(12)

        vault_header_row = QHBoxLayout()
        vault_title_layout = QVBoxLayout()
        vault_title_layout.setSpacing(2)

        vault_title = QLabel("📥 Curated Releases & Download Links")
        vault_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #38bdf8;")
        vault_title_layout.addWidget(vault_title)

        self.vault_sub = QLabel("Primary content files verified and ready for one-click downloading with pause & resume.")
        self.vault_sub.setStyleSheet("font-size: 12px; color: #a1a1aa;")
        vault_title_layout.addWidget(self.vault_sub)

        vault_header_row.addLayout(vault_title_layout, stretch=1)

        # Batch actions
        self.btn_select_all = QPushButton("Select All")
        self.btn_select_all.clicked.connect(self._select_all_curated)
        vault_header_row.addWidget(self.btn_select_all)

        self.btn_deselect_all = QPushButton("Deselect All")
        self.btn_deselect_all.clicked.connect(self._deselect_all_curated)
        vault_header_row.addWidget(self.btn_deselect_all)

        self.btn_download_selected = QPushButton("Download Selected (0) ⬇️")
        self.btn_download_selected.setObjectName("primaryBtn")
        self.btn_download_selected.setEnabled(False)
        self.btn_download_selected.clicked.connect(self._download_selected_curated)
        vault_header_row.addWidget(self.btn_download_selected)

        self.vault_layout.addLayout(vault_header_row)

        # Curated Search Filter Bar (auto-shown for multi-file repositories)
        self.curated_filter_box = QWidget()
        filter_layout = QHBoxLayout(self.curated_filter_box)
        filter_layout.setContentsMargins(0, 4, 0, 4)
        filter_layout.setSpacing(10)

        self.curated_search = QLineEdit()
        self.curated_search.setPlaceholderText("🔍 Filter files in this archive (e.g. pacman, sf2, mslug, simpsons)...")
        self.curated_search.textChanged.connect(self._on_curated_search_changed)
        filter_layout.addWidget(self.curated_search, stretch=1)

        self.curated_filter_box.hide()
        self.vault_layout.addWidget(self.curated_filter_box)

        # Container for curated cards
        self.curated_cards_container = QVBoxLayout()
        self.curated_cards_container.setSpacing(8)
        self.vault_layout.addLayout(self.curated_cards_container)

        # Show More Button for large repositories
        self.btn_show_more_curated = QPushButton("➕ Show More Files")
        self.btn_show_more_curated.setStyleSheet("""
            QPushButton {
                background-color: #27272a;
                color: #38bdf8;
                border: 1px solid #0284c7;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 700;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #0369a1;
                color: #ffffff;
            }
        """)
        self.btn_show_more_curated.clicked.connect(self._show_more_curated)
        self.btn_show_more_curated.hide()
        self.vault_layout.addWidget(self.btn_show_more_curated)

        self.canvas_layout.addWidget(self.vault_box)

        # --- Expandable Supplementary / All Files Table ---
        self.supp_box = QFrame()
        self.supp_box.setObjectName("articleCard")
        supp_layout = QVBoxLayout(self.supp_box)
        supp_layout.setContentsMargins(22, 16, 22, 16)
        supp_layout.setSpacing(12)

        self.toggle_supp_btn = QPushButton("▶ Show All Individual Files & Derivatives (0 files)")
        self.toggle_supp_btn.setStyleSheet("text-align: left; font-weight: 600; color: #a1a1aa; padding: 8px 12px;")
        self.toggle_supp_btn.clicked.connect(self._toggle_supplementary)
        supp_layout.addWidget(self.toggle_supp_btn)

        self.supp_content = QWidget()
        self.supp_content_layout = QVBoxLayout(self.supp_content)
        self.supp_content_layout.setContentsMargins(0, 8, 0, 0)
        self.supp_content_layout.setSpacing(10)

        # Filter bar
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(10)

        self.supp_search = QLineEdit()
        self.supp_search.setPlaceholderText("Filter raw files by name or extension...")
        self.supp_search.textChanged.connect(self._filter_supp_table)
        filter_bar.addWidget(self.supp_search, stretch=1)

        self.supp_content_layout.addLayout(filter_bar)

        # Table
        self.supp_table = QTableWidget()
        self.supp_table.setColumnCount(4)
        self.supp_table.setHorizontalHeaderLabels(["File Name", "Format", "Size", "Action"])
        self.supp_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.supp_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.supp_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.supp_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.supp_table.setColumnWidth(3, 150)
        self.supp_table.verticalHeader().setDefaultSectionSize(40)
        self.supp_table.verticalHeader().setVisible(False)
        self.supp_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.supp_table.setAlternatingRowColors(True)
        self.supp_table.setMinimumHeight(240)
        self.supp_content_layout.addWidget(self.supp_table)

        self.supp_content.hide()
        supp_layout.addWidget(self.supp_content)
        self.canvas_layout.addWidget(self.supp_box)

        self.canvas_layout.addStretch(1)
        self.scroll_area.setWidget(self.canvas)
        outer_layout.addWidget(self.scroll_area, stretch=1)

    def load_item(self, identifier: str):
        """Fetch and render the complete subject feature article."""
        self.current_playing_file = None

        self.loading_bar.show()
        self.id_pill.setText(f"Loading '{identifier}'...")
        self.headline_label.setText(f"Loading '{identifier}'...")
        self.author_line.setText("Fetching archive documentation and curated files...")
        self.article_browser.clear()
        self._clear_curated_cards()
        self.supp_table.setRowCount(0)
        self.play_online_btn.setEnabled(False)
        self.download_primary_btn.setEnabled(False)
        self.web_btn.setEnabled(False)
        self.copy_btn.setEnabled(False)

        # Scroll to top
        self.scroll_area.verticalScrollBar().setValue(0)

        if self._loader_worker and self._loader_worker.isRunning():
            self._loader_worker.terminate()

        self._loader_worker = ItemLoaderWorker(identifier)
        self._loader_worker.signals.finished.connect(self._on_item_loaded)
        self._loader_worker.signals.error.connect(self._on_item_load_error)
        self._loader_worker.start()

    def _on_item_loaded(self, data: dict):
        self.loading_bar.hide()
        self.current_item_data = data
        ident = data["identifier"]
        
        self.id_pill.setText(f"🏛️ {ident}")
        self.web_btn.setEnabled(True)
        self.copy_btn.setEnabled(True)

        # Headline & Meta
        title = data.get("title", ident)
        self.headline_label.setText(title)

        mediatype = data.get("mediatype", "data").lower()
        badge_text = mediatype.upper()
        if mediatype == "software":
            badge_text = "SOFTWARE / RETRO GAME"
        elif mediatype in ("movies", "video"):
            badge_text = "FEATURE FILM / VIDEO"
        elif mediatype in ("audio", "etree"):
            badge_text = "LIVE MUSIC / AUDIO"
        elif mediatype == "texts":
            badge_text = "BOOK / MAGAZINE"
        elif mediatype == "collection":
            badge_text = "COLLECTION / REPOSITORY"

        self.mediatype_badge.setText(badge_text)
        badge_color = get_mediatype_badge_color(mediatype)
        self.mediatype_badge.setStyleSheet(
            f"font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 4px; "
            f"background-color: {badge_color}; color: white;"
        )

        creator = data.get("creator") or "Internet Archive Preservation"
        date = data.get("date") or "Classic Era"
        files_count = data.get("files_count", 0)
        total_size = data.get("total_size_formatted", "0 B")
        self.author_line.setText(f"Preserved by: {creator}  •  Date: {date}")
        self.meta_summary_label.setText(f"{files_count} files  •  {total_size} total archive size")

        # Classify files into curated vs supplementary FIRST
        files = data.get("files", [])
        self.curated_files, self.supplementary_files = classify_item_files(files)

        # Configure Play / Preview button (aware of classified audio files)
        self._configure_play_button(mediatype, ident)

        # Article text
        desc = data.get("description", "").strip()
        if not desc:
            desc = (
                f"<b>{title}</b> is an archived digital subject preserved in the permanent collections "
                f"of the Internet Archive. Universal access to human knowledge."
            )
        # Render clean rich HTML in article browser
        article_html = f"""
        <div style='line-height: 1.65; color: #d4d4d8; font-size: 13.5px;'>
            {desc}
        </div>
        """
        self.article_browser.setHtml(article_html)

        # Load cover artwork
        self._load_cover(data.get("thumbnail_url"))

        # Populate Curated Cards
        self._populate_curated_cards()

        # Configure Full Archive Batch Processor & Primary Download Buttons
        torrent_file = self._find_torrent_file()
        total_size_str = data.get("total_size_formatted") or data.get("item_size_formatted") or ""
        total_files_count = len(self.curated_files) + len(self.supplementary_files)
        if total_files_count > 1 or torrent_file:
            size_tag = f" ({total_files_count:,} files • {total_size_str})" if total_size_str else f" ({total_files_count:,} files)"
            self.download_torrent_btn.setText(f"⚡ Batch Process & Download Full Archive{size_tag}")
            self.download_torrent_btn.setToolTip(f"Inspect and batch download all {total_files_count:,} files ({total_size_str}) from this repository in ArchiveVault")
            self.download_torrent_btn.show()
        else:
            self.download_torrent_btn.hide()

        if self.curated_files:
            primary = self.curated_files[0]
            sz = primary.get("size_formatted", "")
            if len(self.curated_files) > 10:
                self.download_primary_btn.setText(f"⬇️ Download Largest Release ({sz})")
                self.download_primary_btn.setToolTip(f"Download single largest file: {primary['name']} ({sz})")
            else:
                self.download_primary_btn.setText(f"⚡ Download Main Release ({sz})")
                self.download_primary_btn.setToolTip(f"Download {primary['name']} ({sz})")
            self.download_primary_btn.setEnabled(True)
        else:
            self.download_primary_btn.setText("⚡ Download")
            self.download_primary_btn.setEnabled(False)

        # Check login requirements for restricted collections
        if self._is_login_required_item() and not self._has_ia_credentials():
            self.login_warning_banner.show()
        else:
            self.login_warning_banner.hide()

        # Populate Supplementary Table
        self._populate_supplementary_table()

    def _is_login_required_item(self) -> bool:
        if not self.current_item_data:
            return False
        collections = self.current_item_data.get("collections", [])
        return "loggedin" in collections

    def _has_ia_credentials(self) -> bool:
        from archivevault.core.settings import settings
        return bool((settings.s3_access_key and settings.s3_secret_key) or settings.cookies)

    def _show_login_required_dialog(self, action_name: str = "download from"):
        from PyQt6.QtWidgets import QMessageBox
        ident = self.current_item_data.get("identifier", "") if self.current_item_data else ""
        title = self.current_item_data.get("title", ident) if self.current_item_data else ident

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("🔐 Internet Archive Login Required")
        msg_box.setIcon(QMessageBox.Icon.Warning)
        
        msg_text = (
            f"<h3>Internet Archive Account Required</h3>"
            f"<p><b>'{title}'</b> belongs to a restricted Archive.org collection (<code>loggedin</code>) "
            f"that requires you to be logged into an Internet Archive account to {action_name}.</p>"
            f"<p><b>Recommended Solutions:</b></p>"
            f"<ul>"
            f"<li><b>Configure Free S3 Keys:</b> Internet Archive accounts are 100% free. "
            f"You can get your S3 keys in 30 seconds from Archive.org and paste them into the <b>Settings</b> tab.</li>"
            f"<li><b>Switch to Open MAME 0.264:</b> If you want full arcade emulation, "
            f"the 139 GB <b>MAME 0.264 ROMs</b> pack (<code>mame-0.264-roms-non-merged</code>) is open and requires no login.</li>"
            f"</ul>"
        )
        msg_box.setText(msg_text)
        
        btn_settings = msg_box.addButton("⚙️ Open Settings", QMessageBox.ButtonRole.ActionRole)
        btn_mame = msg_box.addButton("🕹️ Open MAME 0.264 (No Login)", QMessageBox.ButtonRole.ActionRole)
        btn_web = msg_box.addButton("🌐 View on Archive.org", QMessageBox.ButtonRole.ActionRole)
        msg_box.addButton("Close", QMessageBox.ButtonRole.RejectRole)
        
        msg_box.exec()
        
        clicked = msg_box.clickedButton()
        if clicked == btn_settings:
            self.open_settings_requested.emit()
        elif clicked == btn_mame:
            self.open_item_requested.emit("mame-0.264-roms-non-merged")
        elif clicked == btn_web:
            webbrowser.open(f"https://archive.org/details/{ident}")

    def _find_torrent_file(self) -> Optional[dict]:
        all_f = self.curated_files + self.supplementary_files
        for f in all_f:
            if f.get("name", "").lower().endswith(".torrent"):
                return f
        if self.current_item_data:
            for f in self.current_item_data.get("files", []):
                if f.get("name", "").lower().endswith(".torrent"):
                    return f
        return None

    def _download_item_torrent(self):
        if self._is_login_required_item() and not self._has_ia_credentials():
            self._show_login_required_dialog("download full archive")
            return
        if not self.current_item_data:
            return

        from archivevault.core.torrent import create_torrent_metadata_from_item
        from archivevault.ui.torrent_dialog import TorrentDialog

        # Always construct the COMPLETE archive metadata containing 100% of repository files
        meta = create_torrent_metadata_from_item(self.current_item_data)

        raw_bytes = b""
        t_file = self._find_torrent_file()
        if t_file:
            try:
                url = t_file.get("url") or f"https://archive.org/download/{meta.identifier}/{urllib.parse.quote(t_file['name'], safe='/')}"
                r = ia_api.get_session().get(url, headers=ia_api.get_headers(), timeout=10)
                if r.status_code == 200:
                    raw_bytes = r.content
            except Exception:
                pass

        dlg = TorrentDialog(meta, self, raw_bytes=raw_bytes)
        dlg.download_files_requested.connect(self._on_torrent_files_download)
        dlg.exec()

    def _on_item_load_error(self, err_msg: str):
        self.loading_bar.hide()
        self.headline_label.setText("Error loading subject")
        self.author_line.setText(err_msg)
        self.article_browser.setPlainText(f"Could not load details from Internet Archive:\n{err_msg}")

    def _find_best_audio_file(self) -> Optional[dict]:
        """Find the best audio file to stream, prioritizing mp3, then flac/ogg/wav/m4a."""
        candidates = [f for f in self.curated_files + self.supplementary_files if f["name"].lower().endswith(AUDIO_EXTENSIONS)]
        if not candidates:
            return None
        # Prefer mp3 for fast streaming
        mp3s = [f for f in candidates if f["name"].lower().endswith('.mp3')]
        if mp3s:
            return mp3s[0]
        # Next prefer flac, ogg, wav, m4a
        for ext in ('.flac', '.ogg', '.wav', '.m4a'):
            matched = [f for f in candidates if f["name"].lower().endswith(ext)]
            if matched:
                return matched[0]
        return candidates[0]

    def _find_best_video_file(self) -> Optional[dict]:
        """Find the best streaming video file (.mp4 preferred, largest file size)."""
        all_files = self.curated_files + self.supplementary_files
        vids = [f for f in all_files if f["name"].lower().endswith(VIDEO_EXTENSIONS)]
        if not vids:
            return None
        mp4s = [f for f in vids if f["name"].lower().endswith(".mp4")]
        if mp4s:
            return max(mp4s, key=lambda x: x.get("size_bytes", 0))
        return max(vids, key=lambda x: x.get("size_bytes", 0))

    def _configure_play_button(self, mediatype: str, identifier: str):
        self.play_online_btn.setEnabled(True)
        best_audio = self._find_best_audio_file()
        best_video = self._find_best_video_file()
        
        if mediatype == "collection":
            self.play_online_btn.setText("📂 Explore Collection Items In-App")
            self.play_online_btn.setToolTip("Browse and download individual releases inside this collection")
            self.play_online_btn.setStyleSheet("""
                QPushButton#playBtn {
                    background-color: #059669;
                    color: #ffffff;
                    border: 1px solid #10b981;
                    border-radius: 6px;
                    font-weight: 700;
                    font-size: 13px;
                    padding: 8px 18px;
                }
                QPushButton#playBtn:hover {
                    background-color: #10b981;
                }
            """)
            return

        # Default style for playback buttons
        self.play_online_btn.setStyleSheet("")

        # Check Movies / Video FIRST so movie releases with commentary/soundtrack MP3s are watched as videos!
        if mediatype in ("movies", "video") or (best_video is not None and mediatype not in ("audio", "etree")):
            self.play_online_btn.setText("🎬 Watch Movie In-App")
            self.play_online_btn.setToolTip("Stream video directly inside ArchiveVault's built-in cinema player")
        elif mediatype == "software":
            self.play_online_btn.setText("🎮 Play Game In-App")
            self.play_online_btn.setToolTip("Play game directly in ArchiveVault's embedded retro player")
        elif mediatype in ("audio", "etree") or best_audio is not None:
            self.play_online_btn.setText("🎵 Play Audio Preview In-App")
            self.play_online_btn.setToolTip("Stream audio preview directly inside ArchiveVault without leaving the app")
        elif mediatype == "texts":
            self.play_online_btn.setText("📖 Read Book Online")
            self.play_online_btn.setToolTip("Open BookReader on archive.org")
        else:
            self.play_online_btn.setText("▶️ Preview Online")
            self.play_online_btn.setToolTip("Preview on archive.org")

    def _launch_online_experience(self):
        if not self.current_item_data:
            return
        
        mediatype = self.current_item_data.get("mediatype", "")
        ident = self.current_item_data["identifier"]
        title = self.current_item_data.get("title", ident)

        # Collections explore in-app!
        if mediatype == "collection":
            self.explore_collection_requested.emit(ident, title)
            return

        # Check Movies / Video FIRST so movie releases with commentary/soundtrack MP3s are watched as videos!
        best_video = self._find_best_video_file()
        if mediatype in ("movies", "video") or (best_video is not None and mediatype not in ("audio", "etree")):
            if best_video:
                safe_name = urllib.parse.quote(best_video["name"], safe="/")
                video_url = f"https://archive.org/download/{ident}/{safe_name}"
                self.play_video_requested.emit(video_url, title)
            else:
                embed_url = f"https://archive.org/embed/{ident}"
                self.play_video_requested.emit(embed_url, title)
            return

        # Software / MS-DOS / Arcade games play IN-APP via DOSBoxPlayerDialog!
        if mediatype == "software":
            self.play_dosbox_requested.emit(ident, title)
            return

        # Audio items stream IN-APP via MainWindow's docked audio player!
        best_audio = self._find_best_audio_file()
        if mediatype in ("audio", "etree") or best_audio is not None:
            target = self.current_playing_file or best_audio
            if target:
                self._play_file_audio(target)
            return

        # For interactive books or other items, open the archive.org interactive viewer
        url = f"https://archive.org/details/{ident}"
        webbrowser.open(url)

    def _play_file_audio(self, file_info: dict):
        if not self.current_item_data:
            return
        ident = self.current_item_data["identifier"]
        fname = file_info["name"]
        safe_name = urllib.parse.quote(fname, safe="/")
        stream_url = f"https://archive.org/download/{ident}/{safe_name}"
        title = f"{self.current_item_data.get('title', ident)} — {fname}"
        
        self.current_playing_file = file_info
        self.play_audio_requested.emit(stream_url, title)

    def _on_card_listen_clicked(self, file_info: dict):
        self._play_file_audio(file_info)

    def _on_card_watch_clicked(self, file_info: dict):
        if not self.current_item_data:
            return
        ident = self.current_item_data["identifier"]
        safe_name = urllib.parse.quote(file_info["name"], safe="/")
        stream_url = f"https://archive.org/download/{ident}/{safe_name}"
        title = f"{self.current_item_data.get('title', ident)} — {file_info['name']}"
        self.play_video_requested.emit(stream_url, title)

    def update_playback_state(self, current_url: str, is_playing: bool):
        self.is_audio_playing = is_playing
        self.current_playing_url = current_url

        # Update cards
        if not self.current_item_data:
            return
        ident = self.current_item_data["identifier"]
        for card in self.curated_cards:
            safe_name = urllib.parse.quote(card.file_info["name"], safe="/")
            expected_url = f"https://archive.org/download/{ident}/{safe_name}"
            if current_url == expected_url:
                card.set_playing_state(is_playing)
            else:
                card.set_playing_state(False)
        
        # Update hero button
        best_audio = self._find_best_audio_file()
        if self.current_item_data.get("mediatype") == "audio" or best_audio is not None:
            if is_playing:
                self.play_online_btn.setText("⏸ Pause Audio Stream")
            else:
                self.play_online_btn.setText("▶ Resume Audio Stream")

    def _open_web(self):
        if self.current_item_data:
            webbrowser.open(self.current_item_data.get("details_url", ""))

    def _copy_link(self):
        if self.current_item_data:
            QApplication.clipboard().setText(self.current_item_data.get("details_url", ""))

    def _load_cover(self, url: Optional[str]):
        if not url:
            return
        def fetch():
            try:
                r = requests.get(url, headers={"User-Agent": "ArchiveVault/1.0"}, timeout=12)
                if r.status_code == 200:
                    pix = QPixmap()
                    pix.loadFromData(r.content)
                    if not pix.isNull():
                        scaled = pix.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        self.cover_label.setPixmap(scaled)
                        self.cover_label.setText("")
            except Exception:
                pass
        import threading
        threading.Thread(target=fetch, daemon=True).start()

    def _populate_curated_cards(self):
        self.curated_display_limit = 50
        self.curated_search.blockSignals(True)
        self.curated_search.clear()
        self.curated_search.blockSignals(False)

        if len(self.curated_files) > 25:
            self.curated_filter_box.show()
        else:
            self.curated_filter_box.hide()

        self._render_curated_cards()

    def _on_curated_search_changed(self):
        self.curated_display_limit = 50
        self._render_curated_cards()

    def _show_more_curated(self):
        self.curated_display_limit += 50
        self._render_curated_cards()

    def _render_curated_cards(self):
        self._clear_curated_cards()
        self.curated_cards = []

        if self.current_item_data and self.current_item_data.get("mediatype") == "collection":
            col_box = QFrame()
            col_box.setObjectName("curatedCard")
            col_box.setStyleSheet("""
                QFrame#curatedCard {
                    background-color: #132219;
                    border: 1px solid #065f46;
                    border-radius: 8px;
                    padding: 14px 18px;
                }
            """)
            col_layout = QHBoxLayout(col_box)
            col_layout.setSpacing(16)
            
            icon_lbl = QLabel("🏛️")
            icon_lbl.setStyleSheet("font-size: 28px;")
            col_layout.addWidget(icon_lbl)
            
            info_layout = QVBoxLayout()
            info_layout.setSpacing(4)
            h_lbl = QLabel("Master Collection Repository")
            h_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #6ee7b7;")
            info_layout.addWidget(h_lbl)
            
            sub_lbl = QLabel(
                "This archive is a master collection catalog containing multiple digital releases. "
                "Explore the collection to browse, play in-app, and download its individual records and files."
            )
            sub_lbl.setStyleSheet("font-size: 12px; color: #a7f3d0;")
            sub_lbl.setWordWrap(True)
            info_layout.addWidget(sub_lbl)
            col_layout.addLayout(info_layout, stretch=1)
            
            exp_btn = QPushButton("📂 Explore Collection Items (In-App)")
            exp_btn.setFixedSize(250, 36)
            exp_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            exp_btn.setStyleSheet("""
                QPushButton {
                    background-color: #059669;
                    color: #ffffff;
                    border: 1px solid #10b981;
                    border-radius: 6px;
                    font-weight: 700;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #10b981;
                }
            """)
            ident = self.current_item_data["identifier"]
            title = self.current_item_data.get("title", ident)
            exp_btn.clicked.connect(lambda _, i=ident, t=title: self.explore_collection_requested.emit(i, t))
            col_layout.addWidget(exp_btn)
            
            self.curated_cards_container.addWidget(col_box)
            self.btn_show_more_curated.hide()
            return

        if not self.curated_files:
            empty = QLabel("No curated standalone releases found in this archive. View raw files below.")
            empty.setStyleSheet("color: #a1a1aa; padding: 12px; font-style: italic;")
            self.curated_cards_container.addWidget(empty)
            self.btn_show_more_curated.hide()
            return

        kw = self.curated_search.text().strip().lower()
        if kw:
            matched = [f for f in self.curated_files if kw in f["name"].lower()]
        else:
            matched = self.curated_files

        if not matched:
            empty = QLabel(f"No releases matching '{kw}'. Try another search query.")
            empty.setStyleSheet("color: #a1a1aa; padding: 12px; font-style: italic;")
            self.curated_cards_container.addWidget(empty)
            self.btn_show_more_curated.hide()
            self.vault_sub.setText(f"0 files matched '{kw}'.")
            return

        visible = matched[:self.curated_display_limit]
        for f in visible:
            card = CuratedFileCard(f)
            card.download_clicked.connect(self._on_single_file_download)
            card.listen_clicked.connect(self._on_card_listen_clicked)
            card.watch_clicked.connect(self._on_card_watch_clicked)
            card.process_torrent_clicked.connect(self._process_torrent_file_info)
            card.checked_changed.connect(self._update_selected_summary)
            if self.current_playing_file and f == self.current_playing_file:
                card.set_playing_state(self.is_audio_playing)
            self.curated_cards.append(card)
            self.curated_cards_container.addWidget(card)

        # Update Vault subtitle & Show More button
        if len(matched) > len(visible):
            remaining = len(matched) - len(visible)
            show_next = min(50, remaining)
            self.vault_sub.setText(
                f"Showing {len(visible):,} of {len(matched):,} releases. Use the filter bar to search for specific ROMs/files."
            )
            self.btn_show_more_curated.setText(f"➕ Show More Files ({show_next} more, {remaining:,} remaining)")
            self.btn_show_more_curated.show()
        else:
            if kw:
                self.vault_sub.setText(f"Showing all {len(matched):,} matching releases.")
            else:
                self.vault_sub.setText(f"Showing all {len(matched):,} curated releases.")
            self.btn_show_more_curated.hide()

        self._update_selected_summary()

    def _clear_curated_cards(self):
        while self.curated_cards_container.count() > 0:
            child = self.curated_cards_container.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.curated_cards = []

    def _update_selected_summary(self):
        count = sum(1 for c in self.curated_cards if c.is_checked())
        self.btn_download_selected.setText(f"Download Selected ({count}) ⬇️")
        self.btn_download_selected.setEnabled(count > 0)

    def _select_all_curated(self):
        for c in self.curated_cards:
            c.set_checked(True)

    def _deselect_all_curated(self):
        for c in self.curated_cards:
            c.set_checked(False)

    def _download_primary_release(self):
        if self._is_login_required_item() and not self._has_ia_credentials():
            self._show_login_required_dialog("download")
            return
        if self.curated_files and self.current_item_data:
            self.download_requested.emit([self.curated_files[0]], self.current_item_data["identifier"])

    def _on_single_file_download(self, file_info: dict):
        if self._is_login_required_item() and not self._has_ia_credentials():
            self._show_login_required_dialog("download")
            return
        if self.current_item_data:
            self.download_requested.emit([file_info], self.current_item_data["identifier"])

    def _download_selected_curated(self):
        if not self.current_item_data:
            return
        if self._is_login_required_item() and not self._has_ia_credentials():
            self._show_login_required_dialog("download")
            return
        selected = [c.file_info for c in self.curated_cards if c.is_checked()]
        if selected:
            self.download_requested.emit(selected, self.current_item_data["identifier"])

    def _toggle_supplementary(self):
        if not self.supp_content.isHidden():
            self.supp_content.hide()
            self.toggle_supp_btn.setText(f"▶ Show All Individual Files & Derivatives ({len(self.supplementary_files):,} files)")
        else:
            self.supp_content.show()
            self._filter_supp_table()

    def _populate_supplementary_table(self):
        files = self.supplementary_files
        self.toggle_supp_btn.setText(f"▶ Show All Individual Files & Derivatives ({len(files):,} files)")
        if not self.supp_content.isHidden():
            self._filter_supp_table()

    def _filter_supp_table(self):
        kw = self.supp_search.text().strip().lower()
        filtered = [f for f in self.supplementary_files if not kw or kw in f["name"].lower()]

        display_limit = 150
        display_items = filtered[:display_limit]

        self.supp_table.setRowCount(len(display_items))
        for row, f in enumerate(display_items):
            # Name
            name_item = QTableWidgetItem(f["name"])
            name_item.setToolTip(f["name"])
            self.supp_table.setItem(row, 0, name_item)

            # Format
            fmt_item = QTableWidgetItem(f.get("format", "FILE"))
            fmt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.supp_table.setItem(row, 1, fmt_item)

            # Size
            sz_item = QTableWidgetItem(f.get("size_formatted", "?"))
            sz_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.supp_table.setItem(row, 2, sz_item)

            # Action buttons
            container = QWidget()
            l = QHBoxLayout(container)
            l.setContentsMargins(4, 2, 4, 2)
            l.setSpacing(6)
            l.setAlignment(Qt.AlignmentFlag.AlignCenter)

            if f["name"].lower().endswith(AUDIO_EXTENSIONS):
                play_btn = QPushButton("▶ Play")
                play_btn.setFixedSize(58, 28)
                play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                play_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #065f46;
                        color: #a7f3d0;
                        border: 1px solid #047857;
                        border-radius: 5px;
                        font-weight: 600;
                        font-size: 11px;
                        padding: 0px;
                    }
                    QPushButton:hover {
                        background-color: #047857;
                        color: #ffffff;
                    }
                """)
                play_btn.clicked.connect(lambda _, fi=f: self._play_file_audio(fi))
                l.addWidget(play_btn)
            elif f["name"].lower().endswith(VIDEO_EXTENSIONS):
                watch_btn = QPushButton("🎬 Watch")
                watch_btn.setFixedSize(62, 28)
                watch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                watch_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #1e3a8a;
                        color: #bfdbfe;
                        border: 1px solid #1d4ed8;
                        border-radius: 5px;
                        font-weight: 600;
                        font-size: 11px;
                        padding: 0px;
                    }
                    QPushButton:hover {
                        background-color: #1d4ed8;
                        color: #ffffff;
                    }
                """)
                watch_btn.clicked.connect(lambda _, fi=f: self._on_card_watch_clicked(fi))
                l.addWidget(watch_btn)
            elif f["name"].lower().endswith('.torrent'):
                proc_btn = QPushButton("⚡ Process")
                proc_btn.setFixedSize(70, 28)
                proc_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                proc_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #581c87;
                        color: #e9d5ff;
                        border: 1px solid #7e22ce;
                        border-radius: 5px;
                        font-weight: 700;
                        font-size: 11px;
                        padding: 0px;
                    }
                    QPushButton:hover {
                        background-color: #7e22ce;
                        color: #ffffff;
                    }
                """)
                proc_btn.setToolTip("Inspect torrent payload files and download directly via HTTP resume")
                proc_btn.clicked.connect(lambda _, fi=f: self._process_torrent_file_info(fi))
                l.addWidget(proc_btn)

            dl_btn = QPushButton("⬇️ Get")
            dl_btn.setObjectName("tableActionBtn")
            dl_btn.setFixedSize(58, 28)
            dl_btn.clicked.connect(lambda _, fi=f: self._on_single_file_download(fi))
            l.addWidget(dl_btn)

            self.supp_table.setCellWidget(row, 3, container)

        if not self.supp_content.isHidden():
            if len(filtered) > display_limit:
                self.toggle_supp_btn.setText(f"▼ Raw Files Table (showing {len(display_items)} of {len(filtered):,} matched files — search above to filter)")
            else:
                self.toggle_supp_btn.setText(f"▼ Raw Files Table ({len(filtered):,} files)")
        else:
            self.toggle_supp_btn.setText(f"▶ Show All Individual Files & Derivatives ({len(self.supplementary_files):,} files)")

    def _process_torrent_file_info(self, file_info: dict):
        if not self.current_item_data:
            return
        if self._is_login_required_item() and not self._has_ia_credentials():
            self._show_login_required_dialog("inspect the torrent for")
            return

        ident = self.current_item_data["identifier"]
        fname = file_info["name"]
        url = file_info.get("url") or f"https://archive.org/download/{ident}/{urllib.parse.quote(fname, safe='/')}"

        self.loading_bar.show()
        try:
            session = ia_api.get_session()
            headers = ia_api.get_headers()
            r = session.get(url, headers=headers, timeout=25)
            if r.status_code in (401, 403):
                self._show_login_required_dialog("inspect the torrent for")
                return
            r.raise_for_status()
            from archivevault.core.torrent import create_torrent_metadata_from_item, parse_torrent_bytes
            from archivevault.ui.torrent_dialog import TorrentDialog
            meta = parse_torrent_bytes(r.content)
            if not meta.identifier or meta.identifier == "archive_torrent":
                meta.identifier = ident

            # If the item repository contains more files than this .torrent file (stale IA .torrent):
            if self.current_item_data:
                full_meta = create_torrent_metadata_from_item(self.current_item_data)
                if len(full_meta.files) > len(meta.files):
                    meta = full_meta

            dlg = TorrentDialog(meta, self, raw_bytes=r.content)
            dlg.download_files_requested.connect(self._on_torrent_files_download)
            dlg.exec()
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code in (401, 403):
                self._show_login_required_dialog("inspect the torrent for")
            else:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Torrent Processing Error", f"Could not inspect torrent file:\n{e}")
        except Exception as e:
            if "401" in str(e) or "Unauthorized" in str(e):
                self._show_login_required_dialog("inspect the torrent for")
            else:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Torrent Processing Error", f"Could not inspect torrent file:\n{e}")
        finally:
            self.loading_bar.hide()

    def _on_torrent_files_download(self, files: list, item_id: str):
        file_dicts = [
            {
                "name": entry.filename,
                "url": entry.download_url,
                "size_bytes": entry.size_bytes,
                "size_formatted": entry.size_formatted,
                "path": entry.path
            }
            for entry in files
        ]
        self.download_requested.emit(file_dicts, item_id)
