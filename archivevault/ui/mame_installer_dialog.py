import os
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from archivevault.core.settings import settings
from archivevault.core.utils import get_launchbox_path, install_portable_mame, launch_launchbox


class MameInstallWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)

    def run(self):
        def cb(pct: int, msg: str):
            self.progress.emit(pct, msg)

        success, res = install_portable_mame(progress_callback=cb)
        self.finished.emit(success, res)


class MameInstallerDialog(QDialog):
    """Modern dark-themed dialog for 1-click automatic download and setup of official portable MAME."""

    installation_finished = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚡ Official MAME Arcade Setup (1-Click)")
        self.setFixedSize(520, 270)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setStyleSheet("""
            QDialog {
                background-color: #12131a;
                color: #ffffff;
            }
            QLabel {
                color: #e4e4e7;
            }
            QPushButton {
                background-color: #27272a;
                color: #ffffff;
                border: 1px solid #3f3f46;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #3f3f46;
            }
            QPushButton#primaryBtn {
                background-color: #10b981;
                border: none;
                color: #ffffff;
                font-weight: 700;
            }
            QPushButton#primaryBtn:hover {
                background-color: #059669;
            }
            QProgressBar {
                border: 1px solid #3f3f46;
                border-radius: 6px;
                background-color: #18181b;
                text-align: center;
                color: #ffffff;
                font-weight: 600;
                font-size: 11px;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #10b981;
                border-radius: 5px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header Banner
        header = QHBoxLayout()
        header.setSpacing(12)

        icon_lbl = QLabel("🕹️")
        icon_lbl.setStyleSheet("font-size: 28px;")
        header.addWidget(icon_lbl)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        t_lbl = QLabel("Official MAME Arcade Emulator")
        t_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #ffffff;")
        title_box.addWidget(t_lbl)

        sub_lbl = QLabel("Zero-configuration portable setup for playing offline arcade ROMs.")
        sub_lbl.setStyleSheet("font-size: 12px; color: #a1a1aa;")
        title_box.addWidget(sub_lbl)
        header.addLayout(title_box, stretch=1)
        layout.addLayout(header)

        # Description / Info
        desc_box = QFrame()
        desc_box.setStyleSheet("background-color: #18181b; border: 1px solid #27272a; border-radius: 8px; padding: 10px;")
        desc_layout = QVBoxLayout(desc_box)
        desc_layout.setContentsMargins(10, 8, 10, 8)
        desc_layout.setSpacing(4)

        info_lbl = QLabel(
            "ArchiveVault will download the official MAME standalone emulator (~83 MB) "
            "and unpack it locally into your user directory. You'll be able to launch "
            "any arcade ROM instantly without manual emulator setup."
        )
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet("font-size: 11px; color: #d4d4d8; line-height: 1.4;")
        desc_layout.addWidget(info_lbl)
        layout.addWidget(desc_box)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Status Label
        self.status_lbl = QLabel("Ready to start setup.")
        self.status_lbl.setStyleSheet("font-size: 12px; color: #38bdf8;")
        layout.addWidget(self.status_lbl)

        # Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)
        btn_box.addStretch(1)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self._on_cancel)
        btn_box.addWidget(self.btn_cancel)

        self.btn_start = QPushButton("⚡ Download & Install MAME")
        self.btn_start.setObjectName("primaryBtn")
        self.btn_start.clicked.connect(self.start_installation)
        btn_box.addWidget(self.btn_start)

        layout.addLayout(btn_box)

        self.worker: MameInstallWorker | None = None
        self.installed_path: str = ""

    def start_installation(self):
        self.btn_start.setEnabled(False)
        self.btn_cancel.setText("Cancel")
        self.progress_bar.setValue(5)
        self.status_lbl.setText("Starting MAME portable download...")

        self.worker = MameInstallWorker()
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        self.status_lbl.setText(msg)

    def _on_finished(self, success: bool, result: str):
        if success:
            self.installed_path = result
            self.progress_bar.setValue(100)
            self.status_lbl.setText("✅ MAME installed & ready to play!")
            self.status_lbl.setStyleSheet("font-size: 12px; color: #10b981; font-weight: 700;")
            self.btn_cancel.setVisible(False)
            self.btn_start.setText("Done ▶")
            self.btn_start.setEnabled(True)
            self.btn_start.clicked.disconnect()
            self.btn_start.clicked.connect(self.accept)
            self.installation_finished.emit(result)
        else:
            self.progress_bar.setValue(0)
            self.status_lbl.setText(f"❌ Error: {result}")
            self.status_lbl.setStyleSheet("font-size: 12px; color: #ef4444; font-weight: 600;")
            self.btn_start.setEnabled(True)
            self.btn_start.setText("Retry Setup 🔄")
            self.btn_cancel.setText("Close")

    def _on_cancel(self):
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait(1000)
        self.reject()


class LaunchBoxGuideDialog(QDialog):
    """Explains how LaunchBox's built-in emulator downloader works in 3 clicks."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🚀 LaunchBox MAME Setup (3 Quick Clicks)")
        self.setFixedSize(540, 340)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setStyleSheet("""
            QDialog {
                background-color: #12131a;
                color: #ffffff;
            }
            QLabel {
                color: #e4e4e7;
            }
            QPushButton {
                background-color: #27272a;
                color: #ffffff;
                border: 1px solid #3f3f46;
                border-radius: 6px;
                padding: 7px 16px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #3f3f46;
            }
            QPushButton#lbBtn {
                background-color: #2563eb;
                border: none;
                color: #ffffff;
                font-weight: 700;
            }
            QPushButton#lbBtn:hover {
                background-color: #1d4ed8;
            }
            QPushButton#mameBtn {
                background-color: #10b981;
                border: none;
                color: #ffffff;
                font-weight: 700;
            }
            QPushButton#mameBtn:hover {
                background-color: #059669;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header
        header = QHBoxLayout()
        header.setSpacing(12)

        icon_lbl = QLabel("🚀")
        icon_lbl.setStyleSheet("font-size: 28px;")
        header.addWidget(icon_lbl)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        t_lbl = QLabel("Configuring MAME in LaunchBox")
        t_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #38bdf8;")
        title_box.addWidget(t_lbl)

        sub_lbl = QLabel("LaunchBox has a built-in auto-downloader for MAME.")
        sub_lbl.setStyleSheet("font-size: 12px; color: #a1a1aa;")
        title_box.addWidget(sub_lbl)
        header.addLayout(title_box, stretch=1)
        layout.addLayout(header)

        # Instructions Frame
        guide_box = QFrame()
        guide_box.setStyleSheet("background-color: #18181b; border: 1px solid #27272a; border-radius: 8px; padding: 12px;")
        guide_layout = QVBoxLayout(guide_box)
        guide_layout.setContentsMargins(12, 10, 12, 10)
        guide_layout.setSpacing(8)

        guide_html = """
        <div style="font-size: 12px; color: #d4d4d8; line-height: 1.6;">
            <b>1. Open LaunchBox.</b><br>
            <b>2. Click Menu:</b> <code>Tools</code> ➔ <code>Manage</code> ➔ <code>Emulators...</code><br>
            <b>3. Click Add:</b> In the Emulators window, click the <b>Add...</b> button.<br>
            <b>4. Select MAME:</b> In the <i>Emulator Name</i> dropdown, select <b>MAME</b>.<br>
            <b>5. Click Download:</b> LaunchBox will show a <b>"Download MAME"</b> button. Click it!<br>
            <b>6. Save:</b> Click <b>OK</b>. LaunchBox will automatically install MAME.
        </div>
        """
        guide_lbl = QLabel(guide_html)
        guide_lbl.setTextFormat(Qt.TextFormat.RichText)
        guide_layout.addWidget(guide_lbl)
        layout.addWidget(guide_box)

        tip_lbl = QLabel("💡 <i>Once configured, ArchiveVault will also automatically link to this MAME setup!</i>")
        tip_lbl.setStyleSheet("font-size: 11px; color: #10b981;")
        layout.addWidget(tip_lbl)

        # Action Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)

        self.btn_open_lb = QPushButton("LaunchBox 🚀")
        self.btn_open_lb.setObjectName("lbBtn")
        self.btn_open_lb.clicked.connect(self._open_launchbox)
        btn_box.addWidget(self.btn_open_lb)

        self.btn_install_direct = QPushButton("⚡ Or 1-Click Install in ArchiveVault")
        self.btn_install_direct.setObjectName("mameBtn")
        self.btn_install_direct.clicked.connect(self._launch_direct_installer)
        btn_box.addWidget(self.btn_install_direct)

        btn_box.addStretch(1)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btn_box.addWidget(btn_close)

        layout.addLayout(btn_box)

    def _open_launchbox(self):
        launch_launchbox()
        self.accept()

    def _launch_direct_installer(self):
        self.done(2)  # Return code 2 to indicate direct installer requested
