import os
import re
import time
from typing import Dict, List, Optional
from PyQt6.QtCore import QObject, QThread, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from archivevault.core.api import ia_api
from archivevault.core.settings import settings
from archivevault.core.utils import format_eta, format_size, format_speed, open_file

COLLECTION_PRESETS = [
    ("Community Media (community)", "community"),
    ("Open Source Software & Apps (opensource_media)", "opensource_media"),
    ("Computer History & Technology (folkscanomy_computer)", "folkscanomy_computer"),
    ("Community Video & Movies (opensource_movies)", "opensource_movies"),
    ("Community Audio & Music (opensource_audio)", "opensource_audio"),
    ("Community Texts & Documents (opensource)", "opensource"),
]

LICENSE_PRESETS = [
    ("Creative Commons: Public Domain Dedication (CC0 1.0)", "https://creativecommons.org/publicdomain/zero/1.0/"),
    ("Creative Commons: Attribution 4.0 International (CC BY 4.0)", "https://creativecommons.org/licenses/by/4.0/"),
    ("Creative Commons: Attribution-ShareAlike 4.0 (CC BY-SA 4.0)", "https://creativecommons.org/licenses/by-sa/4.0/"),
    ("GNU General Public License (GPL v3)", "https://www.gnu.org/licenses/gpl-3.0.html"),
    ("Public Domain Mark 1.0", "https://creativecommons.org/publicdomain/mark/1.0/"),
    ("Freeware / Historic Preservation (Fair Use)", ""),
]


class UploadWorkerSignals(QObject):
    file_started = pyqtSignal(str, int, int) # filename, file_idx, total_files
    file_progress = pyqtSignal(str, int, int, float, float) # filename, uploaded_bytes, total_bytes, speed, eta
    file_finished = pyqtSignal(str, bool, str) # filename, success, message
    all_finished = pyqtSignal(bool, str, str) # success, identifier, summary_message
    log_message = pyqtSignal(str)


class UploadWorker(QThread):
    """Background worker to upload files sequentially to Internet Archive S3."""

    def __init__(self, identifier: str, files: List[dict], metadata: Dict[str, str], parent=None):
        super().__init__(parent)
        self.identifier = identifier
        self.files = files
        self.metadata = metadata
        self.signals = UploadWorkerSignals()
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def is_cancelled(self) -> bool:
        return self._cancelled

    def run(self):
        total_files = len(self.files)
        success_count = 0
        overall_start_time = time.time()

        self.signals.log_message.emit(f"🚀 Initializing upload for item '{self.identifier}' ({total_files} file(s))...")

        for idx, f_info in enumerate(self.files):
            if self._cancelled:
                self.signals.all_finished.emit(False, self.identifier, "Upload was cancelled by user.")
                return

            f_path = f_info["path"]
            f_name = f_info["target_name"]
            f_size = f_info["size"]

            self.signals.file_started.emit(f_name, idx + 1, total_files)
            self.signals.log_message.emit(f"📤 [{idx+1}/{total_files}] Uploading {f_name} ({format_size(f_size)})...")

            # Attach metadata only to the first file to create and configure the item bucket
            effective_meta = self.metadata if idx == 0 else None

            start_t = time.time()
            last_report_t = [start_t]
            last_bytes = [0]

            def on_progress(uploaded, total):
                now = time.time()
                dt = now - last_report_t[0]
                if dt >= 0.25 or uploaded >= total:
                    db = uploaded - last_bytes[0]
                    speed = db / max(dt, 0.001)
                    eta = (total - uploaded) / max(speed, 1) if speed > 0 else 0
                    self.signals.file_progress.emit(f_name, uploaded, total, speed, eta)
                    last_report_t[0] = now
                    last_bytes[0] = uploaded

            success, msg = ia_api.upload_file(
                identifier=self.identifier,
                file_path=f_path,
                target_name=f_name,
                metadata=effective_meta,
                progress_callback=on_progress,
                cancel_check=self.is_cancelled
            )

            if success:
                success_count += 1
                self.signals.file_finished.emit(f_name, True, msg)
                self.signals.log_message.emit(f"✅ [{idx+1}/{total_files}] Completed {f_name} successfully.")
            else:
                self.signals.file_finished.emit(f_name, False, msg)
                self.signals.log_message.emit(f"❌ [{idx+1}/{total_files}] Error on {f_name}: {msg}")
                # If bucket creation failed on first file, stop early
                if idx == 0:
                    self.signals.all_finished.emit(False, self.identifier, f"Item creation failed on {f_name}: {msg}")
                    return

        total_elapsed = time.time() - overall_start_time
        if success_count == total_files:
            summary = f"All {total_files} file(s) published successfully in {total_elapsed:.1f}s!"
            self.signals.log_message.emit(f"🎉 {summary}")
            self.signals.all_finished.emit(True, self.identifier, summary)
        else:
            summary = f"Uploaded {success_count} of {total_files} files with errors."
            self.signals.all_finished.emit(False, self.identifier, summary)


class UploadTab(QWidget):
    """
    Dedicated Internet Archive Publisher & Uploader.
    Allows logged-in users to create items and upload files, games,
    documents, and media directly to Internet Archive.
    """
    inspect_item_requested = pyqtSignal(str) # identifier
    open_settings_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.files_to_upload: List[dict] = []
        self._upload_worker: Optional[UploadWorker] = None
        self._init_ui()
        self.refresh_auth_status()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Outer Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        canvas = QWidget()
        canvas_layout = QVBoxLayout(canvas)
        canvas_layout.setContentsMargins(28, 24, 28, 24)
        canvas_layout.setSpacing(20)

        # --- Top Hero Banner ---
        hero_card = QFrame()
        hero_card.setObjectName("articleCard")
        hero_layout = QVBoxLayout(hero_card)
        hero_layout.setContentsMargins(22, 20, 22, 20)
        hero_layout.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setSpacing(14)

        icon_lbl = QLabel("📤")
        icon_lbl.setStyleSheet("font-size: 38px;")
        top_row.addWidget(icon_lbl)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        title_lbl = QLabel("Internet Archive Uploader & Publisher")
        title_lbl.setStyleSheet("font-size: 22px; font-weight: 800; color: #ffffff;")
        info_layout.addWidget(title_lbl)

        sub_lbl = QLabel("Preserve and publish your games, software, audio, books, films, and collections to the universal permanent library.")
        sub_lbl.setStyleSheet("font-size: 13px; color: #a1a1aa;")
        sub_lbl.setWordWrap(True)
        info_layout.addWidget(sub_lbl)
        top_row.addLayout(info_layout, stretch=1)
        hero_layout.addLayout(top_row)

        # Authentication Banner
        self.auth_card = QFrame()
        self.auth_card.setStyleSheet("""
            QFrame {
                background-color: #18181b;
                border: 1px solid #27272a;
                border-radius: 8px;
                padding: 10px 14px;
            }
        """)
        auth_box = QHBoxLayout(self.auth_card)
        auth_box.setContentsMargins(4, 4, 4, 4)
        auth_box.setSpacing(12)

        self.auth_status_lbl = QLabel("Checking Internet Archive login...")
        self.auth_status_lbl.setStyleSheet("font-size: 12px; font-weight: 600;")
        auth_box.addWidget(self.auth_status_lbl, stretch=1)

        self.btn_auth_settings = QPushButton("⚙️ Configure Keys")
        self.btn_auth_settings.setStyleSheet("font-size: 11px; padding: 4px 12px;")
        self.btn_auth_settings.clicked.connect(self.open_settings_requested.emit)
        auth_box.addWidget(self.btn_auth_settings)

        self.btn_get_keys = QPushButton("🔑 Get IA S3 Keys")
        self.btn_get_keys.setStyleSheet("font-size: 11px; padding: 4px 12px;")
        self.btn_get_keys.setToolTip("Open official Internet Archive S3 keys management page in your browser")
        self.btn_get_keys.clicked.connect(lambda: open_file("https://archive.org/account/s3.php"))
        auth_box.addWidget(self.btn_get_keys)

        hero_layout.addWidget(self.auth_card)
        canvas_layout.addWidget(hero_card)

        # --- Main Form Container (Two Column Grid: Left Files, Right Metadata) ---
        form_card = QFrame()
        form_card.setObjectName("articleCard")
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(22, 20, 22, 20)
        form_layout.setSpacing(18)

        cols_layout = QHBoxLayout()
        cols_layout.setSpacing(20)

        # === LEFT COLUMN: File Selection ===
        left_col = QVBoxLayout()
        left_col.setSpacing(12)

        sec_files_title = QLabel("📁 Files to Upload")
        sec_files_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #38bdf8;")
        left_col.addWidget(sec_files_title)

        btn_files_row = QHBoxLayout()
        btn_files_row.setSpacing(8)

        self.btn_add_files = QPushButton("➕ Add File(s)...")
        self.btn_add_files.setObjectName("primaryBtn")
        self.btn_add_files.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_files.clicked.connect(self._on_add_files)
        btn_files_row.addWidget(self.btn_add_files)

        self.btn_add_folder = QPushButton("📂 Add Folder...")
        self.btn_add_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_folder.clicked.connect(self._on_add_folder)
        btn_files_row.addWidget(self.btn_add_folder)

        self.btn_remove_file = QPushButton("🗑️ Remove")
        self.btn_remove_file.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_remove_file.clicked.connect(self._on_remove_selected_file)
        btn_files_row.addWidget(self.btn_remove_file)

        btn_files_row.addStretch(1)
        left_col.addLayout(btn_files_row)

        # Files Table
        self.files_table = QTableWidget()
        self.files_table.setColumnCount(3)
        self.files_table.setHorizontalHeaderLabels(["Archive File Name", "Size", "Local Path"])
        self.files_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.files_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.files_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.files_table.verticalHeader().setVisible(False)
        self.files_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.files_table.setMinimumHeight(240)
        left_col.addWidget(self.files_table)

        self.files_summary_lbl = QLabel("0 files selected • 0 B total")
        self.files_summary_lbl.setStyleSheet("color: #a1a1aa; font-size: 12px;")
        left_col.addWidget(self.files_summary_lbl)

        cols_layout.addLayout(left_col, stretch=1)

        # === RIGHT COLUMN: Item Metadata ===
        right_col = QVBoxLayout()
        right_col.setSpacing(10)

        sec_meta_title = QLabel("📝 Item Details & Metadata")
        sec_meta_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #38bdf8;")
        right_col.addWidget(sec_meta_title)

        # Title
        lbl_t = QLabel("Item Title *")
        lbl_t.setStyleSheet("font-size: 11px; font-weight: 700; color: #d4d4d8;")
        right_col.addWidget(lbl_t)
        self.input_title = QLineEdit()
        self.input_title.setPlaceholderText("e.g. My Cool Retro Game (1995) or Space Station Audio")
        self.input_title.textChanged.connect(self._on_title_changed)
        right_col.addWidget(self.input_title)

        # Identifier with Availability Check
        lbl_id = QLabel("Identifier (Archive.org URL Slug) *")
        lbl_id.setStyleSheet("font-size: 11px; font-weight: 700; color: #d4d4d8;")
        right_col.addWidget(lbl_id)

        id_row = QHBoxLayout()
        id_row.setSpacing(6)
        self.input_identifier = QLineEdit()
        self.input_identifier.setPlaceholderText("e.g. my-cool-retro-game-1995")
        id_row.addWidget(self.input_identifier, stretch=1)

        self.btn_check_id = QPushButton("Check 🔍")
        self.btn_check_id.setFixedWidth(75)
        self.btn_check_id.clicked.connect(self._on_check_identifier)
        id_row.addWidget(self.btn_check_id)
        right_col.addLayout(id_row)

        self.id_status_lbl = QLabel("Lowercase letters, numbers, dashes (min 5 chars)")
        self.id_status_lbl.setStyleSheet("font-size: 11px; color: #71717a;")
        right_col.addWidget(self.id_status_lbl)

        # Mediatype & Creator Row
        row_media_creator = QHBoxLayout()
        row_media_creator.setSpacing(10)

        box_media = QVBoxLayout()
        box_media.setSpacing(4)
        lbl_m = QLabel("Media Type *")
        lbl_m.setStyleSheet("font-size: 11px; font-weight: 700; color: #d4d4d8;")
        box_media.addWidget(lbl_m)
        self.combo_mediatype = QComboBox()
        self.combo_mediatype.addItem("🎮 Software & Games", "software")
        self.combo_mediatype.addItem("🎬 Movies & Video", "movies")
        self.combo_mediatype.addItem("🎵 Audio & Music", "audio")
        self.combo_mediatype.addItem("📚 Books & Texts", "texts")
        self.combo_mediatype.addItem("🖼️ Images & Art", "image")
        self.combo_mediatype.addItem("💾 Data & Archives", "data")
        box_media.addWidget(self.combo_mediatype)
        row_media_creator.addLayout(box_media, stretch=1)

        box_creator = QVBoxLayout()
        box_creator.setSpacing(4)
        lbl_c = QLabel("Creator / Author")
        lbl_c.setStyleSheet("font-size: 11px; font-weight: 700; color: #d4d4d8;")
        box_creator.addWidget(lbl_c)
        self.input_creator = QLineEdit()
        self.input_creator.setPlaceholderText("Developer, author, or creator")
        box_creator.addWidget(self.input_creator)
        row_media_creator.addLayout(box_creator, stretch=1)

        right_col.addLayout(row_media_creator)

        # Date & Collection Row
        row_date_col = QHBoxLayout()
        row_date_col.setSpacing(10)

        box_date = QVBoxLayout()
        box_date.setSpacing(4)
        lbl_d = QLabel("Date / Year")
        lbl_d.setStyleSheet("font-size: 11px; font-weight: 700; color: #d4d4d8;")
        box_date.addWidget(lbl_d)
        self.input_date = QLineEdit()
        self.input_date.setPlaceholderText(time.strftime("%Y"))
        box_date.addWidget(self.input_date)
        row_date_col.addLayout(box_date, stretch=1)

        box_col = QVBoxLayout()
        box_col.setSpacing(4)
        lbl_col = QLabel("Collection")
        lbl_col.setStyleSheet("font-size: 11px; font-weight: 700; color: #d4d4d8;")
        box_col.addWidget(lbl_col)
        self.combo_collection = QComboBox()
        for label, val in COLLECTION_PRESETS:
            self.combo_collection.addItem(label, val)
        box_col.addWidget(self.combo_collection)
        row_date_col.addLayout(box_col, stretch=2)

        right_col.addLayout(row_date_col)

        # Subject Tags
        lbl_tags = QLabel("Subject / Tags (comma-separated)")
        lbl_tags.setStyleSheet("font-size: 11px; font-weight: 700; color: #d4d4d8;")
        right_col.addWidget(lbl_tags)
        self.input_subjects = QLineEdit()
        self.input_subjects.setPlaceholderText("retro, msdos, utility, classic, open-source")
        right_col.addWidget(self.input_subjects)

        # License
        lbl_lic = QLabel("License")
        lbl_lic.setStyleSheet("font-size: 11px; font-weight: 700; color: #d4d4d8;")
        right_col.addWidget(lbl_lic)
        self.combo_license = QComboBox()
        for label, url in LICENSE_PRESETS:
            self.combo_license.addItem(label, url)
        right_col.addWidget(self.combo_license)

        # Description
        lbl_desc = QLabel("Description & Release Notes")
        lbl_desc.setStyleSheet("font-size: 11px; font-weight: 700; color: #d4d4d8;")
        right_col.addWidget(lbl_desc)
        self.input_desc = QTextEdit()
        self.input_desc.setPlaceholderText("Describe the item, controls, history, or contents...")
        self.input_desc.setMaximumHeight(85)
        right_col.addWidget(self.input_desc)

        cols_layout.addLayout(right_col, stretch=1)
        form_layout.addLayout(cols_layout)

        # --- Upload Controls & Progress ---
        progress_box = QVBoxLayout()
        progress_box.setSpacing(8)

        action_row = QHBoxLayout()
        action_row.setSpacing(10)

        self.btn_start_upload = QPushButton("🚀 Start Upload to Internet Archive")
        self.btn_start_upload.setObjectName("primaryBtn")
        self.btn_start_upload.setStyleSheet("font-size: 13px; font-weight: 700; padding: 10px 24px;")
        self.btn_start_upload.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start_upload.clicked.connect(self._on_start_upload)
        action_row.addWidget(self.btn_start_upload)

        self.btn_cancel_upload = QPushButton("⏹ Cancel Upload")
        self.btn_cancel_upload.setEnabled(False)
        self.btn_cancel_upload.clicked.connect(self._on_cancel_upload)
        action_row.addWidget(self.btn_cancel_upload)

        action_row.addStretch(1)
        progress_box.addLayout(action_row)

        self.upload_progress_bar = QProgressBar()
        self.upload_progress_bar.setRange(0, 100)
        self.upload_progress_bar.setValue(0)
        self.upload_progress_bar.setFixedHeight(8)
        self.upload_progress_bar.setTextVisible(False)
        progress_box.addWidget(self.upload_progress_bar)

        self.upload_status_lbl = QLabel("Ready to upload.")
        self.upload_status_lbl.setStyleSheet("font-size: 12px; color: #a1a1aa;")
        progress_box.addWidget(self.upload_status_lbl)

        # Log display
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(90)
        self.log_text.setStyleSheet("background-color: #09090b; color: #a1a1aa; font-family: monospace; font-size: 11px;")
        progress_box.addWidget(self.log_text)

        form_layout.addLayout(progress_box)
        canvas_layout.addWidget(form_card)

        # --- Completion Success Card (Hidden until successful upload) ---
        self.success_card = QFrame()
        self.success_card.setObjectName("articleCard")
        self.success_card.setStyleSheet("""
            QFrame {
                background-color: #064e3b;
                border: 1px solid #059669;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        self.success_card.hide()
        succ_layout = QVBoxLayout(self.success_card)
        succ_layout.setSpacing(10)

        succ_title = QLabel("🎉 Item Published Successfully to Internet Archive!")
        succ_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #ecfdf5;")
        succ_layout.addWidget(succ_title)

        self.succ_desc_lbl = QLabel()
        self.succ_desc_lbl.setStyleSheet("font-size: 12px; color: #d1fae5;")
        succ_layout.addWidget(self.succ_desc_lbl)

        succ_btns = QHBoxLayout()
        succ_btns.setSpacing(10)

        self.btn_open_dossier = QPushButton("📖 Inspect in Subject Dossier")
        self.btn_open_dossier.setObjectName("primaryBtn")
        self.btn_open_dossier.setCursor(Qt.CursorShape.PointingHandCursor)
        succ_btns.addWidget(self.btn_open_dossier)

        self.btn_view_web = QPushButton("🌐 View on Archive.org")
        self.btn_view_web.setCursor(Qt.CursorShape.PointingHandCursor)
        succ_btns.addWidget(self.btn_view_web)

        self.btn_copy_link = QPushButton("📋 Copy Link")
        self.btn_copy_link.setCursor(Qt.CursorShape.PointingHandCursor)
        succ_btns.addWidget(self.btn_copy_link)

        succ_btns.addStretch(1)
        succ_layout.addLayout(succ_btns)
        canvas_layout.addWidget(self.success_card)

        canvas_layout.addStretch(1)
        self.scroll_area.setWidget(canvas)
        main_layout.addWidget(self.scroll_area, stretch=1)

    def refresh_auth_status(self):
        """Update authentication banner based on current S3 keys in settings."""
        has_keys = bool(settings.s3_access_key.strip() and settings.s3_secret_key.strip())
        if has_keys:
            masked = f"{settings.s3_access_key[:4]}...{settings.s3_access_key[-3:]}" if len(settings.s3_access_key) >= 7 else "Active"
            self.auth_status_lbl.setText(
                f"✅ <b>Authenticated:</b> S3 Access Key: <code>{masked}</code> &nbsp;•&nbsp; Ready to upload and publish items to Internet Archive."
            )
            self.auth_status_lbl.setStyleSheet("font-size: 12px; color: #4ade80;")
            self.btn_start_upload.setEnabled(True)
        else:
            self.auth_status_lbl.setText(
                "⚠️ <b>Internet Archive S3 Credentials Required:</b> To publish items, configure your S3 Access and Secret Keys in Settings."
            )
            self.auth_status_lbl.setStyleSheet("font-size: 12px; color: #fbbf24;")
            self.btn_start_upload.setEnabled(False)

    def _on_title_changed(self, text: str):
        # Auto-suggest clean identifier if user hasn't explicitly edited identifier
        if not self.input_identifier.text() or self.input_identifier.property("auto_generated"):
            slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
            if slug:
                self.input_identifier.setText(slug[:60])
                self.input_identifier.setProperty("auto_generated", True)

    def _on_check_identifier(self):
        ident = self.input_identifier.text().strip().lower()
        if not ident:
            self.id_status_lbl.setText("⚠️ Please enter an identifier first.")
            self.id_status_lbl.setStyleSheet("font-size: 11px; color: #fbbf24;")
            return

        self.id_status_lbl.setText("Checking availability with Archive.org...")
        self.id_status_lbl.setStyleSheet("font-size: 11px; color: #38bdf8;")
        QApplication.processEvents()

        avail, msg = ia_api.check_identifier_available(ident)
        if avail:
            self.id_status_lbl.setText(f"✅ {msg}")
            self.id_status_lbl.setStyleSheet("font-size: 11px; color: #4ade80;")
        else:
            self.id_status_lbl.setText(f"ℹ️ {msg}")
            self.id_status_lbl.setStyleSheet("font-size: 11px; color: #f59e0b;")

    def _on_add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Files to Upload",
            settings.download_dir,
            "All Files (*.*)"
        )
        if paths:
            for p in paths:
                self._add_file_entry(p)
            self._update_files_table()

    def _on_add_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Folder to Upload",
            settings.download_dir
        )
        if folder:
            for root, _, files in os.walk(folder):
                for f in files:
                    full_p = os.path.join(root, f)
                    rel_p = os.path.relpath(full_p, folder).replace("\\", "/")
                    self._add_file_entry(full_p, target_name=rel_p)
            self._update_files_table()

    def _add_file_entry(self, full_path: str, target_name: Optional[str] = None):
        if not os.path.exists(full_path):
            return
        t_name = target_name or os.path.basename(full_path)
        # Avoid duplicate target paths
        if any(f["target_name"] == t_name for f in self.files_to_upload):
            return
        try:
            sz = os.path.getsize(full_path)
        except OSError:
            sz = 0
        self.files_to_upload.append({
            "path": full_path,
            "target_name": t_name,
            "size": sz
        })

    def _on_remove_selected_file(self):
        selected_rows = sorted(set(idx.row() for idx in self.files_table.selectedIndexes()), reverse=True)
        for r in selected_rows:
            if 0 <= r < len(self.files_to_upload):
                self.files_to_upload.pop(r)
        self._update_files_table()

    def _update_files_table(self):
        self.files_table.setRowCount(len(self.files_to_upload))
        total_bytes = 0
        for row, f in enumerate(self.files_to_upload):
            total_bytes += f["size"]
            self.files_table.setItem(row, 0, QTableWidgetItem(f["target_name"]))
            sz_item = QTableWidgetItem(format_size(f["size"]))
            sz_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.files_table.setItem(row, 1, sz_item)
            self.files_table.setItem(row, 2, QTableWidgetItem(f["path"]))

        self.files_summary_lbl.setText(
            f"{len(self.files_to_upload)} file(s) selected • {format_size(total_bytes)} total"
        )

    def _on_start_upload(self):
        # Validate credentials
        if not settings.s3_access_key.strip() or not settings.s3_secret_key.strip():
            QMessageBox.warning(
                self,
                "Authentication Required",
                "Please configure your Internet Archive S3 Access & Secret Keys in Settings before uploading."
            )
            self.open_settings_requested.emit()
            return

        # Validate files
        if not self.files_to_upload:
            QMessageBox.warning(self, "No Files", "Please add at least one file or folder to upload.")
            return

        # Validate title & identifier
        title = self.input_title.text().strip()
        if not title:
            QMessageBox.warning(self, "Title Required", "Please provide a title for the archive item.")
            self.input_title.setFocus()
            return

        ident = self.input_identifier.text().strip().lower()
        if not ident or not re.match(r"^[a-z0-9][a-z0-9_\-\.]{4,99}$", ident):
            QMessageBox.warning(
                self,
                "Valid Identifier Required",
                "Identifier must be 5-100 characters and contain only lowercase letters, digits, dashes, and underscores."
            )
            self.input_identifier.setFocus()
            return

        metadata = {
            "title": title,
            "mediatype": self.combo_mediatype.currentData() or "data",
            "creator": self.input_creator.text().strip(),
            "date": self.input_date.text().strip() or time.strftime("%Y"),
            "collection": self.combo_collection.currentData() or "opensource_media",
            "description": self.input_desc.toPlainText().strip(),
            "subject": self.input_subjects.text().strip(),
            "licenseurl": self.combo_license.currentData() or ""
        }

        # UI locking
        self.btn_start_upload.setEnabled(False)
        self.btn_cancel_upload.setEnabled(True)
        self.upload_progress_bar.setValue(0)
        self.upload_status_lbl.setText("Starting upload to Internet Archive...")
        self.log_text.clear()
        self.success_card.hide()

        self._upload_worker = UploadWorker(ident, list(self.files_to_upload), metadata, parent=self)
        self._upload_worker.signals.log_message.connect(self._append_log)
        self._upload_worker.signals.file_progress.connect(self._on_file_progress)
        self._upload_worker.signals.all_finished.connect(self._on_upload_all_finished)
        self._upload_worker.start()

    def _on_cancel_upload(self):
        if self._upload_worker and self._upload_worker.isRunning():
            self._upload_worker.cancel()
            self.upload_status_lbl.setText("Cancelling upload...")
            self.btn_cancel_upload.setEnabled(False)

    def _append_log(self, msg: str):
        self.log_text.append(msg)

    def _on_file_progress(self, fname: str, uploaded: int, total: int, speed: float, eta: float):
        pct = int((uploaded / max(total, 1)) * 100)
        self.upload_progress_bar.setValue(pct)
        sp_str = format_speed(speed)
        eta_str = format_eta(eta)
        self.upload_status_lbl.setText(
            f"Uploading {fname}: {format_size(uploaded)} / {format_size(total)} ({pct}%) • {sp_str} • ETA: {eta_str}"
        )

    def _on_upload_all_finished(self, success: bool, identifier: str, message: str):
        self.btn_start_upload.setEnabled(True)
        self.btn_cancel_upload.setEnabled(False)
        if success:
            self.upload_progress_bar.setValue(100)
            self.upload_status_lbl.setText("✅ Upload completed successfully!")
            self._show_success_card(identifier)
        else:
            self.upload_status_lbl.setText(f"⚠️ {message}")
            QMessageBox.warning(self, "Upload Incomplete", f"Upload finished with notices:\n\n{message}")

    def _show_success_card(self, identifier: str):
        url = f"https://archive.org/details/{identifier}"
        self.succ_desc_lbl.setText(
            f"Your item is now live on the Internet Archive at:<br>"
            f"<a href='{url}' style='color: #6ee7b7; font-weight: 700;'>{url}</a>"
        )
        self.btn_open_dossier.clicked.disconnect() if self.btn_open_dossier.receivers(self.btn_open_dossier.clicked) else None
        self.btn_open_dossier.clicked.connect(lambda: self.inspect_item_requested.emit(identifier))

        self.btn_view_web.clicked.disconnect() if self.btn_view_web.receivers(self.btn_view_web.clicked) else None
        self.btn_view_web.clicked.connect(lambda: open_file(url))

        self.btn_copy_link.clicked.disconnect() if self.btn_copy_link.receivers(self.btn_copy_link.clicked) else None
        self.btn_copy_link.clicked.connect(lambda: QApplication.clipboard().setText(url))

        self.success_card.show()
