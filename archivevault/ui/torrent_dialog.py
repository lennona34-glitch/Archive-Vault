"""
ArchiveVault Torrent Inspector & Processor Dialog
Inspects .torrent files in-app, displays all payload files and directories,
and enables 1-click downloading of selected files via ArchiveVault's high-speed HTTP resume downloader.
"""

import os
import webbrowser
from typing import List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from archivevault.core.torrent import TorrentFileEntry, TorrentMetadata, parse_torrent_bytes, parse_torrent_file
from archivevault.core.utils import format_size


class TorrentDialog(QDialog):
    """
    In-App BitTorrent Inspector & HTTP Downloader Dialog.
    Allows users to examine .torrent contents without an external torrent client,
    and download any or all files directly using ArchiveVault's resume engine.
    """
    download_files_requested = pyqtSignal(list, str) # list of TorrentFileEntry, str item_id

    def __init__(self, metadata: TorrentMetadata, parent=None, raw_bytes: bytes = b"", torrent_path: str = ""):
        super().__init__(parent)
        self.metadata = metadata
        self.raw_bytes = raw_bytes
        self.torrent_path = torrent_path
        self.setWindowTitle(f"⚡ Archive & Torrent Processor — {self.metadata.name}")
        self.resize(1020, 680)
        self.setMinimumSize(850, 520)
        self.setStyleSheet("""
            QDialog {
                background-color: #0c0c0e;
                color: #f4f4f5;
            }
        """)

        self._init_ui()
        self._populate_table()
        self._update_selection_summary()

    def showEvent(self, event):
        super().showEvent(event)
        try:
            from archivevault.ui.main_window import apply_windows_dark_titlebar
            apply_windows_dark_titlebar(self)
        except Exception:
            pass

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        # --- Top Header Frame ---
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #141417;
                border: 1px solid #27272a;
                border-radius: 8px;
                padding: 14px;
            }
        """)
        header_layout = QVBoxLayout(header_frame)
        header_layout.setSpacing(8)

        # Title Row
        title_row = QHBoxLayout()
        title_row.setSpacing(10)

        icon_lbl = QLabel("⚡")
        icon_lbl.setStyleSheet("font-size: 22px;")
        title_row.addWidget(icon_lbl)

        self.title_lbl = QLabel(self.metadata.name)
        self.title_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #ffffff;")
        self.title_lbl.setWordWrap(True)
        title_row.addWidget(self.title_lbl, stretch=1)

        is_full = getattr(self.metadata, 'is_full_repository', False)
        self.badge = QLabel("COMPLETE ARCHIVE REPOSITORY" if is_full else "BITTORRENT PAYLOAD")
        badge_bg = "#065f46" if is_full else "#581c87"
        badge_fg = "#a7f3d0" if is_full else "#d8b4fe"
        badge_border = "#047857" if is_full else "#7e22ce"
        self.badge.setStyleSheet(f"""
            background-color: {badge_bg};
            color: {badge_fg};
            border: 1px solid {badge_border};
            font-size: 10px;
            font-weight: 800;
            padding: 4px 8px;
            border-radius: 4px;
        """)
        title_row.addWidget(self.badge)
        header_layout.addLayout(title_row)

        # Stats Row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)

        stats_text = (
            f"📦 <b>Total Size:</b> {self.metadata.total_size_formatted}  •  "
            f"📄 <b>Files:</b> {len(self.metadata.files):,} items  •  "
            f"🆔 <b>Identifier:</b> {self.metadata.identifier}"
        )
        if self.metadata.creation_date:
            stats_text += f"  •  📅 <b>Created:</b> {self.metadata.creation_date}"

        self.stats_lbl = QLabel(stats_text)
        self.stats_lbl.setTextFormat(Qt.TextFormat.RichText)
        self.stats_lbl.setStyleSheet("color: #a1a1aa; font-size: 12px;")
        stats_row.addWidget(self.stats_lbl, stretch=1)

        header_layout.addLayout(stats_row)
        main_layout.addWidget(header_frame)

        # --- Filter & Search Toolbar ---
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        # Quick select buttons
        btn_style = """
            QPushButton {
                background-color: #1e1e24;
                color: #e4e4e7;
                border: 1px solid #3f3f46;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #27272a;
                color: #ffffff;
                border-color: #52525b;
            }
        """

        self.btn_select_all = QPushButton("☑️ Select All")
        self.btn_select_all.setStyleSheet(btn_style)
        self.btn_select_all.clicked.connect(self._select_all)
        toolbar.addWidget(self.btn_select_all)

        self.btn_deselect_all = QPushButton("⬜ Deselect All")
        self.btn_deselect_all.setStyleSheet(btn_style)
        self.btn_deselect_all.clicked.connect(self._deselect_all)
        toolbar.addWidget(self.btn_deselect_all)

        self.btn_select_video = QPushButton("🎬 Videos")
        self.btn_select_video.setStyleSheet(btn_style)
        self.btn_select_video.clicked.connect(lambda: self._select_by_extensions(('.mp4', '.mkv', '.avi', '.ogv', '.mov', '.webm')))
        toolbar.addWidget(self.btn_select_video)

        self.btn_select_audio = QPushButton("🎵 Audio")
        self.btn_select_audio.setStyleSheet(btn_style)
        self.btn_select_audio.clicked.connect(lambda: self._select_by_extensions(('.mp3', '.flac', '.ogg', '.wav', '.m4a', '.aac')))
        toolbar.addWidget(self.btn_select_audio)

        # Button to fetch full live archive if currently viewing stale/partial torrent
        self.btn_load_full = QPushButton("🌐 Load Full Online Archive")
        self.btn_load_full.setStyleSheet("""
            QPushButton {
                background-color: #1e3a8a;
                color: #bfdbfe;
                border: 1px solid #1d4ed8;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
                color: #ffffff;
            }
        """)
        self.btn_load_full.setToolTip("Query Internet Archive for 100% of files in this repository (e.g. if the .torrent is stale or partial)")
        self.btn_load_full.clicked.connect(self._fetch_and_load_full_archive)
        if getattr(self.metadata, 'is_full_repository', False):
            self.btn_load_full.hide()
        toolbar.addWidget(self.btn_load_full)

        toolbar.addStretch(1)

        # Search filter input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Filter files in archive...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #18181b;
                color: #f4f4f5;
                border: 1px solid #3f3f46;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                min-width: 220px;
            }
            QLineEdit:focus {
                border-color: #3b82f6;
            }
        """)
        self.search_input.textChanged.connect(self._filter_table_rows)
        toolbar.addWidget(self.search_input)

        main_layout.addLayout(toolbar)

        # --- Files Table ---
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Filename / Path", "Size", "Type"])
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #121215;
                color: #f4f4f5;
                border: 1px solid #27272a;
                border-radius: 6px;
                gridline-color: #1e1e24;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 6px;
            }
            QTableWidget::item:selected {
                background-color: #1e293b;
            }
            QHeaderView::section {
                background-color: #18181b;
                color: #a1a1aa;
                font-weight: 700;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #27272a;
            }
        """)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.itemChanged.connect(self._on_item_changed)
        main_layout.addWidget(self.table, stretch=1)

        # --- Bottom Control Panel (2 clean tiers to prevent text truncation) ---
        bottom_container = QVBoxLayout()
        bottom_container.setSpacing(10)

        # Tier 1: Selection Status & Quick Links
        tier1_bar = QHBoxLayout()
        tier1_bar.setSpacing(12)

        self.summary_label = QLabel("Selected: 0 files (0 MB)")
        self.summary_label.setStyleSheet("color: #38bdf8; font-weight: 700; font-size: 13px;")
        tier1_bar.addWidget(self.summary_label, stretch=1)

        self.btn_copy_urls = QPushButton("📋 Copy Direct Links")
        self.btn_copy_urls.setStyleSheet(btn_style)
        self.btn_copy_urls.clicked.connect(self._copy_selected_urls)
        tier1_bar.addWidget(self.btn_copy_urls)

        self.btn_view_web = QPushButton("🌐 View on Web")
        self.btn_view_web.setStyleSheet(btn_style)
        self.btn_view_web.clicked.connect(self._open_in_browser)
        tier1_bar.addWidget(self.btn_view_web)

        self.btn_save_torrent = QPushButton("💾 Save .torrent")
        self.btn_save_torrent.setStyleSheet("""
            QPushButton {
                background: #27272a;
                color: #e4e4e7;
                border: 1px solid #3f3f46;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #3f3f46;
                color: #ffffff;
            }
        """)
        self.btn_save_torrent.setToolTip("Save official .torrent metadata file to your download directory")
        self.btn_save_torrent.clicked.connect(self._save_or_open_torrent)
        tier1_bar.addWidget(self.btn_save_torrent)

        bottom_container.addLayout(tier1_bar)

        # Tier 2: Primary Action & Close Button
        tier2_bar = QHBoxLayout()
        tier2_bar.setSpacing(10)
        tier2_bar.addStretch(1)

        self.btn_download = QPushButton("⚡ Download Selected in ArchiveVault")
        self.btn_download.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                color: #ffffff;
                border: 1px solid #10b981;
                border-radius: 6px;
                padding: 8px 22px;
                font-size: 13px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #10b981;
            }
            QPushButton:disabled {
                background-color: #27272a;
                color: #71717a;
                border-color: #3f3f46;
            }
        """)
        self.btn_download.setToolTip("Download selected files directly in ArchiveVault's resume queue")
        self.btn_download.clicked.connect(self._on_download_clicked)
        tier2_bar.addWidget(self.btn_download)

        self.btn_close = QPushButton("✕ Close")
        self.btn_close.setStyleSheet("""
            QPushButton {
                background-color: #27272a;
                color: #f87171;
                border: 1px solid #7f1d1d;
                border-radius: 6px;
                padding: 8px 18px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #7f1d1d;
                color: #ffffff;
            }
        """)
        self.btn_close.clicked.connect(self.close)
        tier2_bar.addWidget(self.btn_close)

        bottom_container.addLayout(tier2_bar)
        main_layout.addLayout(bottom_container)

    def _populate_table(self):
        self.table.blockSignals(True)
        self.table.setUpdatesEnabled(False)
        default_state = Qt.CheckState.Checked if len(self.metadata.files) <= 25 else Qt.CheckState.Unchecked
        self.table.setRowCount(len(self.metadata.files))
        for row, entry in enumerate(self.metadata.files):
            # Checkbox + Filename
            item_name = QTableWidgetItem(entry.path)
            item_name.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            item_name.setCheckState(default_state)
            self.table.setItem(row, 0, item_name)

            # Size
            item_size = QTableWidgetItem(entry.size_formatted)
            item_size.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_size.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row, 1, item_size)

            # Type / Extension
            ext_label = entry.extension.upper().lstrip('.') or "FILE"
            item_type = QTableWidgetItem(ext_label)
            item_type.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_type.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row, 2, item_type)

        self.table.setUpdatesEnabled(True)
        self.table.blockSignals(False)

    def _apply_metadata(self, new_meta: TorrentMetadata):
        """Update dialog state with a new (or complete) TorrentMetadata payload."""
        self.metadata = new_meta
        is_full = getattr(self.metadata, 'is_full_repository', False)
        self.title_lbl.setText(self.metadata.name)
        self.badge.setText("COMPLETE ARCHIVE REPOSITORY" if is_full else "BITTORRENT PAYLOAD")
        badge_bg = "#065f46" if is_full else "#581c87"
        badge_fg = "#a7f3d0" if is_full else "#d8b4fe"
        badge_border = "#047857" if is_full else "#7e22ce"
        self.badge.setStyleSheet(f"""
            background-color: {badge_bg};
            color: {badge_fg};
            border: 1px solid {badge_border};
            font-size: 10px;
            font-weight: 800;
            padding: 4px 8px;
            border-radius: 4px;
        """)
        stats_text = (
            f"📦 <b>Total Size:</b> {self.metadata.total_size_formatted}  •  "
            f"📄 <b>Files:</b> {len(self.metadata.files):,} items  •  "
            f"🆔 <b>Identifier:</b> {self.metadata.identifier}"
        )
        if self.metadata.creation_date:
            stats_text += f"  •  📅 <b>Created:</b> {self.metadata.creation_date}"
        self.stats_lbl.setText(stats_text)
        if is_full and hasattr(self, 'btn_load_full'):
            self.btn_load_full.hide()
        self._populate_table()
        self._update_selection_summary()

    def _fetch_and_load_full_archive(self):
        """Query Internet Archive live API for all files in this item if the torrent was partial."""
        from archivevault.core.api import ia_api
        from archivevault.core.torrent import create_torrent_metadata_from_item
        self.btn_load_full.setEnabled(False)
        self.btn_load_full.setText("⏳ Fetching Full Archive...")
        QApplication.processEvents()
        try:
            data = ia_api.get_item_metadata(self.metadata.identifier)
            if data and data.get("files"):
                full_meta = create_torrent_metadata_from_item(data)
                self._apply_metadata(full_meta)
                self.btn_load_full.setText(f"✓ Loaded {len(full_meta.files):,} Files")
            else:
                QMessageBox.warning(self, "Archive Lookup", "No additional files found on Archive.org.")
                self.btn_load_full.setText("🌐 Load Full Online Archive")
                self.btn_load_full.setEnabled(True)
        except Exception as e:
            QMessageBox.warning(self, "Lookup Error", f"Could not fetch full archive:\n{e}")
            self.btn_load_full.setText("🌐 Load Full Online Archive")
            self.btn_load_full.setEnabled(True)

    def _on_item_changed(self, item: QTableWidgetItem):
        if item.column() == 0:
            self._update_selection_summary()

    def _update_selection_summary(self):
        selected_count = 0
        selected_bytes = 0
        for row, entry in enumerate(self.metadata.files):
            item = self.table.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                selected_count += 1
                selected_bytes += entry.size_bytes

        fmt = format_size(selected_bytes)
        self.summary_label.setText(f"Selected: {selected_count:,} / {len(self.metadata.files):,} files ({fmt})")
        self.btn_download.setEnabled(selected_count > 0)

    def _select_all(self):
        self.table.blockSignals(True)
        self.table.setUpdatesEnabled(False)
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                item.setCheckState(Qt.CheckState.Checked)
        self.table.setUpdatesEnabled(True)
        self.table.blockSignals(False)
        self._update_selection_summary()

    def _deselect_all(self):
        self.table.blockSignals(True)
        self.table.setUpdatesEnabled(False)
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                item.setCheckState(Qt.CheckState.Unchecked)
        self.table.setUpdatesEnabled(True)
        self.table.blockSignals(False)
        self._update_selection_summary()

    def _select_by_extensions(self, exts: tuple):
        self.table.blockSignals(True)
        self.table.setUpdatesEnabled(False)
        for row, entry in enumerate(self.metadata.files):
            item = self.table.item(row, 0)
            if item:
                if entry.extension.lower() in exts:
                    item.setCheckState(Qt.CheckState.Checked)
                else:
                    item.setCheckState(Qt.CheckState.Unchecked)
        self.table.setUpdatesEnabled(True)
        self.table.blockSignals(False)
        self._update_selection_summary()

    def _filter_table_rows(self, text: str):
        query = text.strip().lower()
        self.table.setUpdatesEnabled(False)
        for row, entry in enumerate(self.metadata.files):
            match = not query or query in entry.path.lower()
            self.table.setRowHidden(row, not match)
        self.table.setUpdatesEnabled(True)

    def get_selected_files(self) -> List[TorrentFileEntry]:
        selected: List[TorrentFileEntry] = []
        for row, entry in enumerate(self.metadata.files):
            item = self.table.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                selected.append(entry)
        return selected

    def _copy_selected_urls(self):
        selected = self.get_selected_files()
        if not selected:
            return
        urls = [entry.download_url for entry in selected]
        QApplication.clipboard().setText("\n".join(urls))
        QMessageBox.information(
            self,
            "Links Copied",
            f"Copied {len(urls)} direct Archive.org download link(s) to clipboard!"
        )

    def _save_or_open_torrent(self):
        from archivevault.core.settings import settings
        save_dir = settings.download_dir
        os.makedirs(save_dir, exist_ok=True)
        filename = f"{self.metadata.identifier}_archive.torrent"
        target_path = os.path.join(save_dir, filename)

        try:
            if self.raw_bytes:
                with open(target_path, "wb") as f:
                    f.write(self.raw_bytes)
            elif self.torrent_path and os.path.exists(self.torrent_path):
                import shutil
                shutil.copy2(self.torrent_path, target_path)
            else:
                from archivevault.core.api import ia_api
                url = f"https://archive.org/download/{self.metadata.identifier}/{filename}"
                r = ia_api.get_session().get(url, headers=ia_api.get_headers(), timeout=25)
                r.raise_for_status()
                with open(target_path, "wb") as f:
                    f.write(r.content)

            QMessageBox.information(
                self,
                "Torrent File Saved",
                f"BitTorrent metadata file saved successfully to:\n{target_path}"
            )
        except Exception as e:
            QMessageBox.warning(self, "Error Saving Torrent", f"Could not save torrent file:\n{e}")

    def _open_in_browser(self):
        url = f"https://archive.org/details/{self.metadata.identifier}"
        webbrowser.open(url)

    def _on_download_clicked(self):
        selected = self.get_selected_files()
        if not selected:
            return

        if len(selected) > 100:
            total_sz = format_size(sum(e.size_bytes for e in selected))
            reply = QMessageBox.question(
                self,
                "Queue Downloads",
                f"Add {len(selected):,} files ({total_sz}) to ArchiveVault's download queue?\n\n"
                f"They will download directly inside ArchiveVault with resume support.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self.download_files_requested.emit(selected, self.metadata.identifier)
        self.accept()
