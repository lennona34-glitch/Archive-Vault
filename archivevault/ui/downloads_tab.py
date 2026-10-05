import os
import sys
from typing import Dict, List, Optional
from PyQt6.QtCore import QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QFont, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from archivevault.core.downloader import (
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_DOWNLOADING,
    STATUS_FAILED,
    STATUS_PAUSED,
    STATUS_QUEUED,
    DownloadItem,
    download_manager,
)
from archivevault.core.settings import settings
from archivevault.core.utils import (
    format_eta,
    format_size,
    format_speed,
    get_7zip_path,
    open_containing_folder,
    open_file,
    open_with_7zip,
)

AUDIO_EXTENSIONS = ('.mp3', '.flac', '.ogg', '.wav', '.m4a', '.aac', '.opus', '.wma', '.aiff', '.mid', '.midi')
VIDEO_EXTENSIONS = ('.mp4', '.mkv', '.avi', '.ogv', '.webm', '.mov', '.flv', '.wmv', '.m4v', '.mpg', '.mpeg', '.m2v', '.ts', '.vob', '.3gp')
RETRO_PREFIXES = ('msdos_', 'amiga_', 'arcade_', 'c64_', 'zx_', 'atari_', 'apple2_', 'classicpcgames', 'softwarelibrary_')

def is_emulated_item(identifier: str) -> bool:
    return identifier.lower().startswith(RETRO_PREFIXES)

class DownloadsTab(QWidget):
    """
    Download queue & active manager with full pause, resume,
    cancellation controls, in-app media watching, and retro gaming launching.
    """
    play_media_requested = pyqtSignal(str, str) # file_path, display_title
    play_video_requested = pyqtSignal(str, str) # file_path, display_title
    play_dosbox_requested = pyqtSignal(str, str) # identifier, display_title
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.item_row_map: Dict[str, int] = {}
        self.displayed_items: List[DownloadItem] = []
        self.currently_playing_path: Optional[str] = None
        self.is_playing: bool = False
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(400)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self.refresh_table)
        self._init_ui()
        self._connect_signals()
        self.refresh_table()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        # --- Top Action Bar ---
        top_card = QFrame()
        top_card.setObjectName("card")
        top_layout = QHBoxLayout(top_card)
        top_layout.setContentsMargins(14, 12, 14, 12)
        top_layout.setSpacing(10)

        self.pause_all_btn = QPushButton("Pause All ⏸️")
        self.pause_all_btn.clicked.connect(self._pause_all)
        top_layout.addWidget(self.pause_all_btn)

        self.resume_all_btn = QPushButton("Resume All ▶️")
        self.resume_all_btn.setObjectName("primaryBtn")
        self.resume_all_btn.clicked.connect(self._resume_all)
        top_layout.addWidget(self.resume_all_btn)

        self.clear_done_btn = QPushButton("Clear Completed 🧹")
        self.clear_done_btn.clicked.connect(self._clear_completed)
        top_layout.addWidget(self.clear_done_btn)

        self.open_dir_btn = QPushButton("Open Folder 📁")
        self.open_dir_btn.clicked.connect(self._open_downloads_dir)
        top_layout.addWidget(self.open_dir_btn)

        self.process_torrent_btn = QPushButton("⚡ Process .torrent...")
        self.process_torrent_btn.setStyleSheet("""
            QPushButton {
                background-color: #581c87;
                color: #e9d5ff;
                border: 1px solid #7e22ce;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 700;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #7e22ce;
                color: #ffffff;
            }
        """)
        self.process_torrent_btn.setToolTip("Inspect and download contents of any .torrent file via high-speed HTTP resume")
        self.process_torrent_btn.clicked.connect(self._on_pick_and_process_torrent)
        top_layout.addWidget(self.process_torrent_btn)

        top_layout.addStretch(1)

        # Aggregate Speed & Counts
        self.speed_label = QLabel("Speed: --")
        self.speed_label.setStyleSheet("font-size: 13px; font-weight: 700; color: #38bdf8;")
        top_layout.addWidget(self.speed_label)

        self.stats_label = QLabel("0 active")
        self.stats_label.setStyleSheet("font-size: 12px; color: #a1a1aa;")
        top_layout.addWidget(self.stats_label)

        main_layout.addWidget(top_card)

        # --- Downloads Table ---
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "File & Item", "Progress", "Size", "Speed", "ETA", "Status", "Actions"
        ])
        
        # Set generous default row height so text and buttons are never chopped off
        self.table.verticalHeader().setDefaultSectionSize(54)
        self.table.verticalHeader().setVisible(False)

        # Column layout
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 160)
        
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 95)
        
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 85)
        
        # Generous 135px for status badge so "DOWNLOADING" / "PAUSED" never truncate
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 135)
        
        # Generous 210px for Action buttons so Play / Folder / Cancel never clip
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 210)

        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        main_layout.addWidget(self.table, stretch=1)

    def _connect_signals(self):
        download_manager.queue_updated.connect(self._schedule_refresh)
        download_manager.item_progress.connect(self._on_item_progress)
        download_manager.item_status.connect(self._on_item_status)

    def _schedule_refresh(self):
        if not self._refresh_timer.isActive():
            self._refresh_timer.start()

    def refresh_table(self):
        """Re-render table from download_manager.items efficiently without UI thread locking."""
        items = download_manager.items
        self.item_row_map.clear()

        total_speed = 0.0
        active_count = 0
        paused_count = 0
        completed_count = 0
        failed_count = 0
        queued_count = 0

        for item in items:
            if item.status == STATUS_DOWNLOADING:
                active_count += 1
                total_speed += item.speed
            elif item.status == STATUS_PAUSED:
                paused_count += 1
            elif item.status == STATUS_COMPLETED:
                completed_count += 1
            elif item.status == STATUS_FAILED:
                failed_count += 1
            elif item.status == STATUS_QUEUED:
                queued_count += 1

        # Prioritize active items, then paused, failed, queued, and completed
        display_limit = 100
        if len(items) > display_limit:
            priority_order = {
                STATUS_DOWNLOADING: 0,
                STATUS_PAUSED: 1,
                STATUS_FAILED: 2,
                STATUS_QUEUED: 3,
                STATUS_COMPLETED: 4
            }
            display_items = sorted(items, key=lambda x: priority_order.get(x.status, 5))[:display_limit]
        else:
            display_items = list(items)

        self.displayed_items = display_items
        self.table.setRowCount(len(display_items))

        for row, item in enumerate(display_items):
            self.item_row_map[item.id] = row

            # 0: File & Item
            title_widget = QWidget()
            t_layout = QVBoxLayout(title_widget)
            t_layout.setContentsMargins(8, 6, 8, 6)
            t_layout.setSpacing(2)
            fname_lbl = QLabel(item.filename)
            fname_lbl.setStyleSheet("font-weight: 600; color: #f4f4f5; font-size: 13px;")
            fname_lbl.setToolTip(item.filename)
            item_lbl = QLabel(f"📦 {item.identifier}")
            item_lbl.setStyleSheet("font-size: 11px; color: #a1a1aa;")
            t_layout.addWidget(fname_lbl)
            t_layout.addWidget(item_lbl)
            self.table.setCellWidget(row, 0, title_widget)

            # 1: Progress Bar
            pb_container = QWidget()
            pb_layout = QVBoxLayout(pb_container)
            pb_layout.setContentsMargins(6, 6, 6, 6)
            pb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pb = QProgressBar()
            if item.total_bytes > 0:
                pb.setRange(0, 100)
                pct = int((item.downloaded_bytes / item.total_bytes) * 100)
                pb.setValue(min(100, max(0, pct)))
            else:
                pb.setRange(0, 0)
            pb_layout.addWidget(pb)
            self.table.setCellWidget(row, 1, pb_container)

            # 2: Size
            cur_sz = format_size(item.downloaded_bytes)
            tot_sz = format_size(item.total_bytes) if item.total_bytes > 0 else "?"
            sz_item = QTableWidgetItem(f"{cur_sz} / {tot_sz}")
            sz_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 2, sz_item)

            # 3: Speed
            spd_text = format_speed(item.speed) if item.status == STATUS_DOWNLOADING else "--"
            spd_item = QTableWidgetItem(spd_text)
            spd_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, spd_item)

            # 4: ETA
            eta_text = format_eta(item.eta) if item.status == STATUS_DOWNLOADING else "--"
            eta_item = QTableWidgetItem(eta_text)
            eta_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, eta_item)

            # 5: Status Badge (comfortable width & padding)
            badge = self._create_status_badge(item.status)
            self.table.setCellWidget(row, 5, badge)

            # 6: Action buttons (proper height & unclipped text)
            actions_widget = self._create_row_actions(item)
            self.table.setCellWidget(row, 6, actions_widget)

        # Update stats
        self.speed_label.setText(f"Speed: {format_speed(total_speed)}")
        if len(items) > display_limit:
            self.stats_label.setText(
                f"Active: {active_count}  •  Queued: {queued_count}  •  Paused: {paused_count}  •  Done: {completed_count}  (Showing top {len(display_items)} of {len(items):,})"
            )
        else:
            self.stats_label.setText(
                f"Active: {active_count}  •  Queued: {queued_count}  •  Paused: {paused_count}  •  Done: {completed_count}"
            )

    def _create_status_badge(self, status: str) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(2, 4, 2, 4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        badge = QLabel(status)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedHeight(24)
        badge.setMinimumWidth(108)
        
        color_map = {
            STATUS_DOWNLOADING: ("#0284c7", "#ffffff"),
            STATUS_PAUSED: ("#d97706", "#ffffff"),
            STATUS_COMPLETED: ("#16a34a", "#ffffff"),
            STATUS_FAILED: ("#dc2626", "#ffffff"),
            STATUS_QUEUED: ("#4b5563", "#ffffff"),
        }
        bg, fg = color_map.get(status, ("#4b5563", "#ffffff"))
        badge.setStyleSheet(
            f"background-color: {bg}; color: {fg}; font-size: 11px; "
            f"font-weight: 700; padding: 2px 6px; border-radius: 5px;"
        )
        layout.addWidget(badge)
        return container

    def _create_row_actions(self, item: DownloadItem) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if item.status == STATUS_DOWNLOADING:
            pause_btn = QPushButton("Pause ⏸️")
            pause_btn.setObjectName("tablePauseBtn")
            pause_btn.clicked.connect(lambda _, i_id=item.id: download_manager.pause_download(i_id))
            layout.addWidget(pause_btn)
        elif item.status in (STATUS_PAUSED, STATUS_FAILED, STATUS_QUEUED):
            resume_btn = QPushButton("Resume ▶️")
            resume_btn.setObjectName("tableActionBtn")
            resume_btn.clicked.connect(lambda _, i_id=item.id: download_manager.resume_download(i_id))
            layout.addWidget(resume_btn)
        elif item.status == STATUS_COMPLETED:
            is_audio = item.filename.lower().endswith(AUDIO_EXTENSIONS)
            is_video = item.filename.lower().endswith(VIDEO_EXTENSIONS)
            is_game = is_emulated_item(item.identifier)

            if is_audio:
                is_this_playing = (
                    self.is_playing and
                    self.currently_playing_path and
                    (os.path.normcase(os.path.abspath(self.currently_playing_path)) == os.path.normcase(os.path.abspath(item.save_path)))
                )
                play_btn = QPushButton("⏸ Pause" if is_this_playing else "▶ Play")
                play_btn.setFixedSize(68, 28)
                play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                if is_this_playing:
                    play_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #2563eb;
                            color: #ffffff;
                            border: 1px solid #1d4ed8;
                            border-radius: 5px;
                            font-weight: 700;
                            font-size: 11px;
                        }
                        QPushButton:hover {
                            background-color: #1d4ed8;
                        }
                    """)
                else:
                    play_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #065f46;
                            color: #a7f3d0;
                            border: 1px solid #047857;
                            border-radius: 5px;
                            font-weight: 600;
                            font-size: 11px;
                        }
                        QPushButton:hover {
                            background-color: #047857;
                            color: #ffffff;
                        }
                    """)
                play_btn.clicked.connect(lambda _, it=item: self._on_play_clicked(it))
                layout.addWidget(play_btn)
            elif is_video:
                watch_btn = QPushButton("🎬 Watch")
                watch_btn.setFixedSize(68, 28)
                watch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                watch_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #1e3a8a;
                        color: #bfdbfe;
                        border: 1px solid #1d4ed8;
                        border-radius: 5px;
                        font-weight: 600;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background-color: #1d4ed8;
                        color: #ffffff;
                    }
                """)
                watch_btn.clicked.connect(lambda _, it=item: self._on_watch_clicked(it))
                layout.addWidget(watch_btn)
            elif is_game:
                game_btn = QPushButton("🎮 Play")
                game_btn.setFixedSize(68, 28)
                game_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                game_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #065f46;
                        color: #a7f3d0;
                        border: 1px solid #047857;
                        border-radius: 5px;
                        font-weight: 700;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background-color: #047857;
                        color: #ffffff;
                    }
                """)
                game_btn.clicked.connect(lambda _, it=item: self._on_dosbox_clicked(it))
                layout.addWidget(game_btn)
            elif item.filename.lower().endswith(".torrent"):
                proc_btn = QPushButton("⚡ Process")
                proc_btn.setFixedSize(72, 28)
                proc_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                proc_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #581c87;
                        color: #e9d5ff;
                        border: 1px solid #7e22ce;
                        border-radius: 5px;
                        font-weight: 700;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background-color: #7e22ce;
                        color: #ffffff;
                    }
                """)
                proc_btn.setToolTip("Inspect and download torrent contents via ArchiveVault HTTP resume")
                proc_btn.clicked.connect(lambda _, p=item.save_path: self._process_local_torrent(p))
                layout.addWidget(proc_btn)
            else:
                open_btn = QPushButton("Open ↗")
                open_btn.setObjectName("tableActionBtn")
                open_btn.setFixedSize(65, 28)
                open_btn.clicked.connect(lambda _, p=item.save_path: open_file(p))
                layout.addWidget(open_btn)

            open_folder_btn = QPushButton("Folder 📁")
            open_folder_btn.setObjectName("tablePauseBtn")
            open_folder_btn.setFixedSize(65, 28)
            open_folder_btn.clicked.connect(lambda _, p=item.save_path: open_containing_folder(p))
            layout.addWidget(open_folder_btn)

        # Cancel / Remove button
        cancel_btn = QPushButton("✕")
        cancel_btn.setObjectName("tableCancelBtn")
        cancel_btn.setToolTip("Remove from list")
        cancel_btn.clicked.connect(lambda _, i_id=item.id: download_manager.cancel_download(i_id, delete_part=False))
        layout.addWidget(cancel_btn)

        return container

    def _on_pick_and_process_torrent(self):
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select BitTorrent File",
            "",
            "BitTorrent Files (*.torrent);;All Files (*.*)"
        )
        if not path:
            return
        self._process_local_torrent(path)

    def _process_local_torrent(self, path: str):
        if not os.path.exists(path):
            QMessageBox.warning(self, "File Not Found", f"Torrent file not found:\n{path}")
            return
        try:
            from archivevault.core.torrent import parse_torrent_file
            from archivevault.ui.torrent_dialog import TorrentDialog
            meta = parse_torrent_file(path)
            dlg = TorrentDialog(meta, self, torrent_path=path)
            dlg.download_files_requested.connect(self._on_torrent_files_download)
            dlg.exec()
        except Exception as e:
            QMessageBox.warning(self, "Torrent Processing Error", f"Could not inspect torrent file:\n{e}")

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
        download_manager.add_batch_downloads(file_dicts, item_id)

    def _on_play_clicked(self, item: DownloadItem):
        if not os.path.exists(item.save_path):
            QMessageBox.warning(
                self,
                "File Not Found",
                f"File '{item.filename}' was not found at:\n{item.save_path}\n\nIt may have been moved or deleted."
            )
            return
        title = f"{item.filename}"
        self.play_media_requested.emit(item.save_path, title)

    def _on_watch_clicked(self, item: DownloadItem):
        if not os.path.exists(item.save_path):
            QMessageBox.warning(
                self,
                "File Not Found",
                f"File '{item.filename}' was not found at:\n{item.save_path}\n\nIt may have been moved or deleted."
            )
            return
        title = f"{item.filename}"
        self.play_video_requested.emit(item.save_path, title)

    def _on_dosbox_clicked(self, item: DownloadItem):
        title = f"{item.filename}"
        self.play_dosbox_requested.emit(item.identifier, title)

    def _on_cell_double_clicked(self, row: int, col: int):
        if row < 0 or row >= len(self.displayed_items):
            return
        item = self.displayed_items[row]
        if item.status == STATUS_COMPLETED:
            if item.filename.lower().endswith(AUDIO_EXTENSIONS):
                self._on_play_clicked(item)
            elif item.filename.lower().endswith(VIDEO_EXTENSIONS):
                self._on_watch_clicked(item)
            elif item.filename.lower().endswith(".torrent"):
                self._process_local_torrent(item.save_path)
            elif is_emulated_item(item.identifier):
                self._on_dosbox_clicked(item)
            else:
                open_file(item.save_path)

    def update_playback_state(self, current_path: str, is_playing: bool):
        self.currently_playing_path = current_path
        self.is_playing = is_playing
        for item in download_manager.items:
            if item.status == STATUS_COMPLETED and item.id in self.item_row_map:
                row = self.item_row_map[item.id]
                if row < self.table.rowCount():
                    actions_widget = self._create_row_actions(item)
                    self.table.setCellWidget(row, 6, actions_widget)

    def _on_item_progress(self, item_id: str, downloaded: int, total: int, speed: float, eta: float):
        row = self.item_row_map.get(item_id)
        if row is None or row >= self.table.rowCount():
            return

        # Update Progress Bar
        pb_container = self.table.cellWidget(row, 1)
        if pb_container:
            pb = pb_container.findChild(QProgressBar)
            if pb:
                if total > 0:
                    pb.setRange(0, 100)
                    pct = int((downloaded / total) * 100)
                    pb.setValue(min(100, max(0, pct)))
                else:
                    pb.setRange(0, 0)

        # Update Size
        sz_item = self.table.item(row, 2)
        if sz_item:
            tot_str = format_size(total) if total > 0 else "?"
            sz_item.setText(f"{format_size(downloaded)} / {tot_str}")

        # Update Speed
        spd_item = self.table.item(row, 3)
        if spd_item:
            spd_item.setText(format_speed(speed))

        # Update ETA
        eta_item = self.table.item(row, 4)
        if eta_item:
            eta_item.setText(format_eta(eta))

        # Aggregate speed
        self.speed_label.setText(f"Speed: {format_speed(download_manager.get_total_speed())}")

    def _on_item_status(self, item_id: str, status: str, error_message: str):
        row = self.item_row_map.get(item_id)
        if row is not None and row < self.table.rowCount():
            item = download_manager.get_item(item_id)
            if item:
                # Update status badge in-place
                badge = self._create_status_badge(status)
                self.table.setCellWidget(row, 5, badge)
                
                # Update action buttons in-place
                actions_widget = self._create_row_actions(item)
                self.table.setCellWidget(row, 6, actions_widget)
                
                if status == STATUS_COMPLETED:
                    # Update progress bar to 100%
                    pb_container = self.table.cellWidget(row, 1)
                    if pb_container:
                        pb = pb_container.findChild(QProgressBar)
                        if pb:
                            pb.setRange(0, 100)
                            pb.setValue(100)
                    sz_item = self.table.item(row, 2)
                    if sz_item and item.total_bytes > 0:
                        tot_str = format_size(item.total_bytes)
                        sz_item.setText(f"{tot_str} / {tot_str}")
                    spd_item = self.table.item(row, 3)
                    if spd_item:
                        spd_item.setText("--")
                    eta_item = self.table.item(row, 4)
                    if eta_item:
                        eta_item.setText("--")

        # Debounce full table refresh to avoid UI thread freeze or stack overflow
        self._schedule_refresh()

    def _show_context_menu(self, pos: QPoint):
        row = self.table.rowAt(pos.y())
        if row < 0 or row >= len(self.displayed_items):
            return

        item = self.displayed_items[row]
        menu = QMenu(self)

        if item.status == STATUS_DOWNLOADING:
            act_pause = menu.addAction("Pause Download")
            act_pause.triggered.connect(lambda: download_manager.pause_download(item.id))
        elif item.status in (STATUS_PAUSED, STATUS_FAILED, STATUS_QUEUED):
            act_resume = menu.addAction("Resume Download")
            act_resume.triggered.connect(lambda: download_manager.resume_download(item.id))

        menu.addSeparator()

        if item.status == STATUS_COMPLETED:
            if item.filename.lower().endswith(AUDIO_EXTENSIONS):
                act_play = menu.addAction("▶ Play in ArchiveVault")
                act_play.triggered.connect(lambda: self._on_play_clicked(item))
            if item.filename.lower().endswith(VIDEO_EXTENSIONS):
                act_watch = menu.addAction("🎬 Watch in ArchiveVault Cinema")
                act_watch.triggered.connect(lambda: self._on_watch_clicked(item))
            if is_emulated_item(item.identifier) or item.filename.lower().endswith(('.zip', '.exe', '.com')):
                act_game = menu.addAction("🎮 Play in DOSBox Player")
                act_game.triggered.connect(lambda: self._on_dosbox_clicked(item))
            if item.filename.lower().endswith(('.zip', '.7z', '.rar', '.tar', '.gz', '.iso', '.bin')) and get_7zip_path():
                act_7z = menu.addAction("Open with 7-Zip File Manager 🗜️")
                act_7z.triggered.connect(lambda: open_with_7zip(item.save_path))
            act_open = menu.addAction("Open with Default Application ↗")
            act_open.triggered.connect(lambda: open_file(item.save_path))

        act_folder = menu.addAction("Open Containing Folder 📁")
        act_folder.triggered.connect(lambda: open_containing_folder(item.save_path))

        act_copy_path = menu.addAction("Copy File Path")
        act_copy_path.triggered.connect(lambda: QApplication.clipboard().setText(item.save_path))

        act_copy_url = menu.addAction("Copy Download URL")
        act_copy_url.triggered.connect(lambda: QApplication.clipboard().setText(item.url))

        menu.addSeparator()

        act_remove = menu.addAction("Remove from List")
        act_remove.triggered.connect(lambda: download_manager.cancel_download(item.id, delete_part=False))

        act_delete = menu.addAction("Delete File from Disk")
        act_delete.triggered.connect(lambda: self._confirm_delete(item))

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _confirm_delete(self, item: DownloadItem):
        reply = QMessageBox.question(
            self,
            "Delete File",
            f"Are you sure you want to delete '{item.filename}' from disk?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            download_manager.cancel_download(item.id, delete_part=True)
            if os.path.exists(item.save_path):
                try:
                    os.remove(item.save_path)
                except Exception:
                    pass

    def _pause_all(self):
        download_manager.pause_all()

    def _resume_all(self):
        download_manager.resume_all()

    def _clear_completed(self):
        download_manager.clear_completed()

    def _open_downloads_dir(self):
        os.makedirs(settings.download_dir, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(settings.download_dir)
        else:
            open_containing_folder(settings.download_dir)
