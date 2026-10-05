import os
import sys
import webbrowser
from PyQt6.QtCore import QObject, Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from archivevault.core.api import ia_api
from archivevault.core.settings import settings

class CredentialTesterSignals(QObject):
    result = pyqtSignal(bool, str)

class CredentialTesterWorker(QThread):
    def __init__(self, access: str, secret: str, cookie: str):
        super().__init__()
        self.access = access
        self.secret = secret
        self.cookie = cookie
        self.signals = CredentialTesterSignals()

    def run(self):
        valid, msg = ia_api.test_credentials(self.access, self.secret, self.cookie)
        self.signals.result.emit(valid, msg)

class SettingsTab(QWidget):
    """Application settings, IA account credentials, and download preferences."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._test_worker: Optional[CredentialTesterWorker] = None
        self._init_ui()
        self._load_values()

    def _init_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(18)

        # Title
        title_lbl = QLabel("Settings & Configuration")
        title_lbl.setStyleSheet("font-size: 20px; font-weight: 700; color: #f4f4f5;")
        layout.addWidget(title_lbl)

        # --- Section 1: Internet Archive Account ---
        account_box = QFrame()
        account_box.setObjectName("card")
        acc_layout = QVBoxLayout(account_box)
        acc_layout.setContentsMargins(18, 16, 18, 16)
        acc_layout.setSpacing(12)

        acc_header = QLabel("🔐 Internet Archive Account")
        acc_header.setStyleSheet("font-size: 15px; font-weight: 600; color: #38bdf8;")
        acc_layout.addWidget(acc_header)

        acc_desc = QLabel(
            "Entering your Internet Archive account credentials enables authenticated downloads, "
            "prevents IP rate limiting, and allows access to restricted collections and borrowing libraries.<br>"
            "You can generate your free S3 API Keys directly from the official Archive.org S3 portal."
        )
        acc_desc.setTextFormat(Qt.TextFormat.RichText)
        acc_desc.setStyleSheet("color: #a1a1aa; font-size: 12px; line-height: 1.4;")
        acc_desc.setWordWrap(True)
        acc_layout.addWidget(acc_desc)

        # Open S3 portal button
        s3_link_btn = QPushButton("Open Archive.org S3 Portal in Browser 🌐")
        s3_link_btn.clicked.connect(lambda: webbrowser.open("https://archive.org/account/s3.php"))
        acc_layout.addWidget(s3_link_btn)

        # Access Key
        row_access = QHBoxLayout()
        acc_lbl = QLabel("S3 Access Key:")
        acc_lbl.setFixedWidth(130)
        row_access.addWidget(acc_lbl)
        self.access_input = QLineEdit()
        self.access_input.setPlaceholderText("e.g. 16-character alphanumeric access key")
        row_access.addWidget(self.access_input)
        acc_layout.addLayout(row_access)

        # Secret Key
        row_secret = QHBoxLayout()
        sec_lbl = QLabel("S3 Secret Key:")
        sec_lbl.setFixedWidth(130)
        row_secret.addWidget(sec_lbl)
        self.secret_input = QLineEdit()
        self.secret_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.secret_input.setPlaceholderText("e.g. 16-character alphanumeric secret key")
        row_secret.addWidget(self.secret_input)

        self.toggle_sec_btn = QPushButton("Show")
        self.toggle_sec_btn.setFixedWidth(60)
        self.toggle_sec_btn.clicked.connect(self._toggle_secret_visibility)
        row_secret.addWidget(self.toggle_sec_btn)
        acc_layout.addLayout(row_secret)

        # Cookie (optional)
        row_cookie = QHBoxLayout()
        cookie_lbl = QLabel("Session Cookie:")
        cookie_lbl.setFixedWidth(130)
        row_cookie.addWidget(cookie_lbl)
        self.cookie_input = QLineEdit()
        self.cookie_input.setPlaceholderText("Optional: logged-in-user=...; logged-in-sig=... (for loaned books)")
        row_cookie.addWidget(self.cookie_input)
        acc_layout.addLayout(row_cookie)

        # Test & Status
        test_row = QHBoxLayout()
        self.test_btn = QPushButton("Test Credentials 🔍")
        self.test_btn.clicked.connect(self._test_credentials)
        test_row.addWidget(self.test_btn)

        self.test_status_lbl = QLabel("")
        self.test_status_lbl.setStyleSheet("font-size: 12px; font-weight: 500;")
        test_row.addWidget(self.test_status_lbl, stretch=1)
        acc_layout.addLayout(test_row)

        layout.addWidget(account_box)

        # --- Section 2: Download Preferences ---
        pref_box = QFrame()
        pref_box.setObjectName("card")
        pref_layout = QVBoxLayout(pref_box)
        pref_layout.setContentsMargins(18, 16, 18, 16)
        pref_layout.setSpacing(12)

        pref_header = QLabel("⬇️ Download Preferences")
        pref_header.setStyleSheet("font-size: 15px; font-weight: 600; color: #38bdf8;")
        pref_layout.addWidget(pref_header)

        # Download Directory
        dir_row = QHBoxLayout()
        dir_lbl = QLabel("Save Location:")
        dir_lbl.setFixedWidth(130)
        dir_row.addWidget(dir_lbl)

        self.dir_input = QLineEdit()
        dir_row.addWidget(self.dir_input, stretch=1)

        browse_btn = QPushButton("Browse... 📁")
        browse_btn.clicked.connect(self._browse_directory)
        dir_row.addWidget(browse_btn)
        pref_layout.addLayout(dir_row)

        # Subfolders
        self.subfolder_cb = QCheckBox("Organize downloads into subfolders per item (e.g. Downloads/InternetArchive/<item-id>/)")
        pref_layout.addWidget(self.subfolder_cb)

        # Max Concurrent Downloads
        conc_row = QHBoxLayout()
        conc_lbl = QLabel("Max Concurrent Downloads:")
        conc_lbl.setFixedWidth(200)
        conc_row.addWidget(conc_lbl)

        self.conc_spin = QSpinBox()
        self.conc_spin.setRange(1, 6)
        self.conc_spin.setValue(2)
        conc_row.addWidget(self.conc_spin)
        conc_row.addStretch(1)
        pref_layout.addLayout(conc_row)

        # Chunk / Buffer size
        chunk_row = QHBoxLayout()
        chunk_lbl = QLabel("Streaming Chunk Size:")
        chunk_lbl.setFixedWidth(200)
        chunk_row.addWidget(chunk_lbl)

        self.chunk_combo = QComboBox()
        self.chunk_combo.addItem("128 KB (Lightweight)", 128)
        self.chunk_combo.addItem("256 KB (Recommended)", 256)
        self.chunk_combo.addItem("512 KB (High Throughput)", 512)
        self.chunk_combo.addItem("1024 KB (Fast Connections)", 1024)
        chunk_row.addWidget(self.chunk_combo)
        chunk_row.addStretch(1)
        pref_layout.addLayout(chunk_row)

        # Auto resume
        self.auto_resume_cb = QCheckBox("Auto-resume unfinished downloads when application starts")
        pref_layout.addWidget(self.auto_resume_cb)

        layout.addWidget(pref_box)

        # --- Section 3: Save Button ---
        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("Save Settings 💾")
        self.save_btn.setObjectName("primaryBtn")
        self.save_btn.setStyleSheet("font-size: 14px; padding: 10px 24px;")
        self.save_btn.clicked.connect(self._save_settings)
        btn_row.addWidget(self.save_btn)

        self.save_msg_lbl = QLabel("")
        self.save_msg_lbl.setStyleSheet("color: #10b981; font-weight: 600;")
        btn_row.addWidget(self.save_msg_lbl)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        # --- Section 4: Internet Archive Tribute ---
        tribute_box = QFrame()
        tribute_box.setObjectName("card")
        trib_layout = QVBoxLayout(tribute_box)
        trib_layout.setContentsMargins(14, 12, 14, 12)
        trib_text = QLabel(
            "🏛️ <b>Internet Archive</b> is a 501(c)(3) non-profit digital library offering free universal access "
            "to books, movies, software, music, websites, and 25+ years of digital history.<br>"
            "<span style='color: #71717a;'>Truly the greatest site on earth. Please consider donating at archive.org/donate.</span>"
        )
        trib_text.setTextFormat(Qt.TextFormat.RichText)
        trib_text.setStyleSheet("color: #a1a1aa; font-size: 12px;")
        trib_text.setWordWrap(True)
        trib_layout.addWidget(trib_text)
        layout.addWidget(tribute_box)

        layout.addStretch(1)
        scroll.setWidget(container)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)

    def _load_values(self):
        self.access_input.setText(settings.s3_access_key)
        self.secret_input.setText(settings.s3_secret_key)
        self.cookie_input.setText(settings.cookies)
        self.dir_input.setText(settings.download_dir)
        self.subfolder_cb.setChecked(settings.create_item_subfolders)
        self.conc_spin.setValue(settings.max_concurrent_downloads)
        self.auto_resume_cb.setChecked(settings.auto_resume_startup)

        idx = self.chunk_combo.findData(settings.chunk_size_kb)
        if idx >= 0:
            self.chunk_combo.setCurrentIndex(idx)

    def _toggle_secret_visibility(self):
        if self.secret_input.echoMode() == QLineEdit.EchoMode.Password:
            self.secret_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_sec_btn.setText("Hide")
        else:
            self.secret_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_sec_btn.setText("Show")

    def _browse_directory(self):
        current = self.dir_input.text() or settings.download_dir
        selected = QFileDialog.getExistingDirectory(self, "Select Download Directory", current)
        if selected:
            self.dir_input.setText(selected)

    def _test_credentials(self):
        acc = self.access_input.text().strip()
        sec = self.secret_input.text().strip()
        cookie = self.cookie_input.text().strip()

        if not acc and not sec and not cookie:
            self.test_status_lbl.setText("⚠️ Please enter Access Key and Secret Key first.")
            self.test_status_lbl.setStyleSheet("color: #f59e0b;")
            return

        self.test_btn.setEnabled(False)
        self.test_status_lbl.setText("Testing connection with archive.org...")
        self.test_status_lbl.setStyleSheet("color: #38bdf8;")

        self._test_worker = CredentialTesterWorker(acc, sec, cookie)
        self._test_worker.signals.result.connect(self._on_test_result)
        self._test_worker.start()

    def _on_test_result(self, valid: bool, message: str):
        self.test_btn.setEnabled(True)
        if valid:
            self.test_status_lbl.setText(f"✅ {message}")
            self.test_status_lbl.setStyleSheet("color: #10b981; font-weight: 600;")
        else:
            self.test_status_lbl.setText(f"❌ {message}")
            self.test_status_lbl.setStyleSheet("color: #ef4444; font-weight: 600;")

    def _save_settings(self):
        settings.s3_access_key = self.access_input.text().strip()
        settings.s3_secret_key = self.secret_input.text().strip()
        settings.cookies = self.cookie_input.text().strip()
        settings.download_dir = self.dir_input.text().strip() or settings.download_dir
        settings.create_item_subfolders = self.subfolder_cb.isChecked()
        settings.max_concurrent_downloads = self.conc_spin.value()
        settings.chunk_size_kb = self.chunk_combo.currentData()
        settings.auto_resume_startup = self.auto_resume_cb.isChecked()
        settings.save()

        self.save_msg_lbl.setText("Settings saved successfully! ✓")
        import threading
        def clear_msg():
            import time
            time.sleep(3)
            self.save_msg_lbl.setText("")
        threading.Thread(target=clear_msg, daemon=True).start()
