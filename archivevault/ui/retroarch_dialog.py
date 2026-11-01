import os
import subprocess
import threading
from typing import Optional
from PyQt6.QtCore import QObject, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon
from PyQt6.QtWidgets import (
    QDialog,
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
    QVBoxLayout,
    QWidget,
)

from archivevault.core.settings import settings
from archivevault.core.utils import (
    CORE_DISPLAY_NAMES,
    download_retroarch_core,
    get_retroarch_cores_dir,
    get_retroarch_info,
    get_retroarch_path,
    install_portable_retroarch,
)

CORE_CATALOG = [
    ("Atari ST", "hatari_libretro.dll", "hatari2014_libretro.dll", "Atari ST / STE / TT / Falcon (Motorola 68000)"),
    ("Commodore Amiga", "puae_libretro.dll", "puae2021_libretro.dll", "Amiga 500 / 1200 / 4000 (Workbench & Paula Audio)"),
    ("Arcade (Coin-Op)", "fbneo_libretro.dll", "mame_libretro.dll", "FinalBurn Neo & MAME (Capcom, Neo Geo, Konami, Sega)"),
    ("ZX Spectrum", "fuse_libretro.dll", None, "Sinclair ZX Spectrum 48K / 128K (+2, +3)"),
    ("Amstrad CPC", "cap32_libretro.dll", "crocods_libretro.dll", "Amstrad CPC 464 / 664 / 6128"),
    ("Commodore 64", "vice_x64sc_libretro.dll", "vice_x128_libretro.dll", "C64 Accurate (SID 6581/8580 Sound & VIC-II Video)"),
    ("Sega Genesis / CD", "genesis_plus_gx_libretro.dll", "picodrive_libretro.dll", "Sega Genesis / Mega Drive / Master System / Sega CD"),
    ("Super Nintendo", "snes9x_libretro.dll", None, "SNES / Super Famicom (16-bit)"),
    ("Nintendo NES", "nestopia_libretro.dll", None, "NES / Famicom (Cycle-accurate 8-bit)"),
    ("Sony PlayStation", "pcsx_rearmed_libretro.dll", "beetle_psx_libretro.dll", "PS1 / PSX (CD-ROM .cue/.bin/.chd/.iso)"),
    ("MS-DOS Pure", "dosbox_pure_libretro.dll", None, "MS-DOS with Auto-Mounting ISOs, ZIPs & Gamepad controls"),
]


class CoreDownloadWorker(QThread):
    finished = pyqtSignal(bool, str, str) # success, core_dll, message
    progress = pyqtSignal(int, str)

    def __init__(self, core_dll: str, parent=None):
        super().__init__(parent)
        self.core_dll = core_dll

    def run(self):
        def cb(pct, msg):
            self.progress.emit(pct, msg)
        success, msg = download_retroarch_core(self.core_dll, progress_callback=cb)
        self.finished.emit(success, self.core_dll, msg)


class RetroArchInstallerWorker(QThread):
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(int, str)

    def run(self):
        def cb(pct, msg):
            self.progress.emit(pct, msg)
        success, msg = install_portable_retroarch(progress_callback=cb)
        self.finished.emit(success, msg)


class EasyRetroDialog(QDialog):
    """
    Big, Juicy 'Easy Retro' RetroArch Universal Emulator Setup Station.
    Allows configuring RetroArch, downloading Libretro cores, and managing
    instant 1-click execution for all retro systems.
    """
    setup_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🕹️ Easy Retro — Universal RetroArch Gaming Station")
        self.resize(840, 680)
        self.setStyleSheet("""
            QDialog {
                background-color: #121214;
                color: #f4f4f5;
            }
            QFrame#card {
                background-color: #18181b;
                border: 1px solid #27272a;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        self._dl_worker: Optional[CoreDownloadWorker] = None
        self._inst_worker: Optional[RetroArchInstallerWorker] = None
        self._init_ui()
        self.refresh_status()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # Header
        head_layout = QHBoxLayout()
        head_layout.setSpacing(14)

        icon_lbl = QLabel("🕹️")
        icon_lbl.setStyleSheet("font-size: 36px;")
        head_layout.addWidget(icon_lbl)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("Easy Retro — Universal RetroArch Station")
        title.setStyleSheet("font-size: 20px; font-weight: 800; color: #38bdf8;")
        title_box.addWidget(title)

        sub = QLabel(
            "Play Anything: Seamlessly launch Atari ST, Amiga, C64, ZX Spectrum, Amstrad, Arcade, "
            "and Console games downloaded from Internet Archive with automatic Libretro core mapping."
        )
        sub.setStyleSheet("font-size: 12px; color: #a1a1aa;")
        sub.setWordWrap(True)
        title_box.addWidget(sub)
        head_layout.addLayout(title_box, stretch=1)
        main_layout.addLayout(head_layout)

        # Scroll Area for Content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 8, 0)
        c_layout.setSpacing(16)

        # --- Section 1: RetroArch Status Card ---
        self.status_card = QFrame()
        self.status_card.setObjectName("card")
        sc_layout = QVBoxLayout(self.status_card)
        sc_layout.setSpacing(12)

        s_header = QLabel("⚡ RetroArch Engine Status")
        s_header.setStyleSheet("font-size: 15px; font-weight: 700; color: #ffffff;")
        sc_layout.addWidget(s_header)

        self.lbl_ra_path = QLabel()
        self.lbl_ra_path.setStyleSheet("font-size: 13px;")
        sc_layout.addWidget(self.lbl_ra_path)

        ra_btn_row = QHBoxLayout()
        ra_btn_row.setSpacing(8)

        self.btn_launch_ra = QPushButton("Launch RetroArch Menu 🚀")
        self.btn_launch_ra.setObjectName("primaryBtn")
        self.btn_launch_ra.setStyleSheet("font-size: 12px; font-weight: 700; padding: 7px 16px;")
        self.btn_launch_ra.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_launch_ra.clicked.connect(self._launch_retroarch_gui)
        ra_btn_row.addWidget(self.btn_launch_ra)

        self.btn_browse_ra = QPushButton("Browse / Change Path...")
        self.btn_browse_ra.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_browse_ra.clicked.connect(self._on_browse_ra)
        ra_btn_row.addWidget(self.btn_browse_ra)

        self.btn_autodetect = QPushButton("Auto-Detect 🔍")
        self.btn_autodetect.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_autodetect.clicked.connect(self._on_autodetect)
        ra_btn_row.addWidget(self.btn_autodetect)

        self.btn_install_portable = QPushButton("⚡ 1-Click Install Portable")
        self.btn_install_portable.setStyleSheet("background-color: #10b981; color: #ffffff; font-weight: 600;")
        self.btn_install_portable.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_install_portable.clicked.connect(self._on_install_portable_ra)
        ra_btn_row.addWidget(self.btn_install_portable)

        ra_btn_row.addStretch(1)
        sc_layout.addLayout(ra_btn_row)

        self.ra_progress_bar = QProgressBar()
        self.ra_progress_bar.setRange(0, 100)
        self.ra_progress_bar.setFixedHeight(6)
        self.ra_progress_bar.setTextVisible(False)
        self.ra_progress_bar.hide()
        sc_layout.addWidget(self.ra_progress_bar)

        self.ra_action_lbl = QLabel("")
        self.ra_action_lbl.setStyleSheet("font-size: 11px; color: #38bdf8;")
        sc_layout.addWidget(self.ra_action_lbl)

        c_layout.addWidget(self.status_card)

        # --- Section 2: Essential Libretro Cores Manager ---
        cores_card = QFrame()
        cores_card.setObjectName("card")
        cores_layout = QVBoxLayout(cores_card)
        cores_layout.setSpacing(12)

        c_header = QLabel("🎮 Essential Libretro Cores (Play Any System)")
        c_header.setStyleSheet("font-size: 15px; font-weight: 700; color: #ffffff;")
        cores_layout.addWidget(c_header)

        c_sub = QLabel(
            "ArchiveVault automatically pairs each retro game with its optimal Libretro core. "
            "Click 'Install Core' for any missing system to download it directly from the official Libretro buildbot."
        )
        c_sub.setStyleSheet("font-size: 11.5px; color: #a1a1aa;")
        c_sub.setWordWrap(True)
        cores_layout.addWidget(c_sub)

        # Cores Table
        self.cores_table = QTableWidget()
        self.cores_table.setColumnCount(4)
        self.cores_table.setHorizontalHeaderLabels(["Platform / System", "Primary Core", "Status", "Action"])
        self.cores_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.cores_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.cores_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.cores_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.cores_table.setColumnWidth(3, 140)
        self.cores_table.verticalHeader().setVisible(False)
        self.cores_table.verticalHeader().setDefaultSectionSize(40)
        self.cores_table.setMinimumHeight(320)
        self.cores_table.setAlternatingRowColors(True)
        cores_layout.addWidget(self.cores_table)

        c_layout.addWidget(cores_card)

        # --- Section 3: Gamepad & Hotkeys Reference ---
        tips_card = QFrame()
        tips_card.setObjectName("card")
        tips_layout = QVBoxLayout(tips_card)
        tips_layout.setSpacing(8)

        t_header = QLabel("🕹️ Controller Autoconfig & In-Game Hotkeys")
        t_header.setStyleSheet("font-size: 13px; font-weight: 700; color: #f59e0b;")
        tips_layout.addWidget(t_header)

        t_text = QLabel(
            "• <b>Wireless Gamepads:</b> Xbox Series/One, PlayStation DualShock/DualSense, Switch Pro, and 8BitDo Bluetooth controllers are instantly recognized with zero driver setup.<br>"
            "• <b>In-Game Master Menu:</b> Press <b>F1</b> (or press Xbox/PS Guide Button or L3+R3) to pause game, save state, or tweak shaders.<br>"
            "• <b>Instant Save / Load:</b> <b>F2</b> to Save State, <b>F4</b> to Load State.<br>"
            "• <b>Quit to ArchiveVault:</b> Press <b>Esc</b> twice or select Close Content in RetroArch menu."
        )
        t_text.setTextFormat(Qt.TextFormat.RichText)
        t_text.setStyleSheet("font-size: 12px; color: #d4d4d8; line-height: 1.5;")
        tips_layout.addWidget(t_text)

        c_layout.addWidget(tips_card)
        c_layout.addStretch(1)

        scroll.setWidget(container)
        main_layout.addWidget(scroll, stretch=1)

        # Close Row
        bot_row = QHBoxLayout()
        bot_row.addStretch(1)
        btn_close = QPushButton("Done")
        btn_close.setFixedWidth(100)
        btn_close.clicked.connect(self.accept)
        bot_row.addWidget(btn_close)
        main_layout.addLayout(bot_row)

    def refresh_status(self):
        info = get_retroarch_info()
        ra_path = info.get("path")
        cores = set(c.lower() for c in info.get("cores", []))

        if ra_path and os.path.exists(ra_path):
            self.lbl_ra_path.setText(
                f"✅ <b>RetroArch Ready:</b> <code>{ra_path}</code><br>"
                f"<span style='color: #4ade80;'>Source: {info.get('source')} &nbsp;•&nbsp; {info.get('cores_count')} Core(s) Available</span>"
            )
            self.btn_launch_ra.setEnabled(True)
            self.btn_install_portable.setVisible(False)
        else:
            self.lbl_ra_path.setText(
                "⚠️ <b>RetroArch Not Detected:</b> Click <b>Browse</b> if already installed on your PC, or click <b>1-Click Install Portable</b>."
            )
            self.lbl_ra_path.setStyleSheet("color: #f59e0b;")
            self.btn_launch_ra.setEnabled(False)
            self.btn_install_portable.setVisible(True)

        # Populate Cores Table
        self.cores_table.setRowCount(len(CORE_CATALOG))
        for row, (platform, primary_core, alt_core, desc) in enumerate(CORE_CATALOG):
            # 0: Platform
            p_item = QTableWidgetItem(platform)
            p_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            p_item.setToolTip(desc)
            self.cores_table.setItem(row, 0, p_item)

            # 1: Primary Core
            c_name = primary_core.replace("_libretro.dll", "")
            c_item = QTableWidgetItem(c_name)
            self.cores_table.setItem(row, 1, c_item)

            # 2: Status
            is_installed = primary_core.lower() in cores or (alt_core and alt_core.lower() in cores)
            active_core = primary_core if primary_core.lower() in cores else (alt_core if alt_core and alt_core.lower() in cores else primary_core)

            if is_installed:
                st_text = f"✅ Installed ({active_core})"
                st_item = QTableWidgetItem(st_text)
                st_item.setForeground(QColor("#4ade80"))
            else:
                st_text = "❌ Missing (Click to Install)"
                st_item = QTableWidgetItem(st_text)
                st_item.setForeground(QColor("#f87171"))
            self.cores_table.setItem(row, 2, st_item)

            # 3: Action Button
            btn_act = QPushButton("Reinstall" if is_installed else "⚡ Install Core")
            btn_act.setFixedSize(115, 26)
            if not is_installed:
                btn_act.setStyleSheet("background-color: #2563eb; color: #ffffff; font-weight: 700; font-size: 11px;")
            else:
                btn_act.setStyleSheet("font-size: 11px;")
            btn_act.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_act.clicked.connect(lambda _, c=primary_core: self._on_download_core_clicked(c))
            self.cores_table.setCellWidget(row, 3, btn_act)

    def _launch_retroarch_gui(self):
        ra_path = get_retroarch_path()
        if ra_path and os.path.exists(ra_path):
            try:
                subprocess.Popen([ra_path], cwd=os.path.dirname(ra_path))
            except Exception as e:
                QMessageBox.warning(self, "Launch Error", f"Could not launch RetroArch: {e}")

    def _on_browse_ra(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select RetroArch Executable",
            r"C:\RetroArch-Win64",
            "RetroArch Executable (retroarch.exe);;All Files (*.*)"
        )
        if file_path and os.path.exists(file_path):
            settings.retroarch_path = file_path
            settings.save()
            self.refresh_status()
            self.setup_changed.emit()
            QMessageBox.information(self, "RetroArch Configured", f"RetroArch successfully set to:\n{file_path}")

    def _on_autodetect(self):
        settings.retroarch_path = ""
        settings.save()
        info = get_retroarch_info()
        ra_path = info.get("path")
        self.refresh_status()
        self.setup_changed.emit()
        if ra_path and os.path.exists(ra_path):
            QMessageBox.information(self, "RetroArch Detected", f"Found RetroArch at:\n{ra_path} ({info.get('source')})")
        else:
            QMessageBox.warning(self, "Not Found", "Could not locate standard RetroArch installation. Try '1-Click Install Portable'.")

    def _on_install_portable_ra(self):
        self.ra_progress_bar.setValue(0)
        self.ra_progress_bar.show()
        self.ra_action_lbl.setText("Starting portable RetroArch download from Libretro buildbot...")
        self.btn_install_portable.setEnabled(False)

        self._inst_worker = RetroArchInstallerWorker(parent=self)
        self._inst_worker.progress.connect(lambda pct, msg: (self.ra_progress_bar.setValue(pct), self.ra_action_lbl.setText(msg)))
        self._inst_worker.finished.connect(self._on_install_finished)
        self._inst_worker.start()

    def _on_install_finished(self, success: bool, msg: str):
        self.ra_progress_bar.hide()
        self.btn_install_portable.setEnabled(True)
        self.ra_action_lbl.setText("")
        if success:
            self.refresh_status()
            self.setup_changed.emit()
            QMessageBox.information(self, "Installation Complete", f"Portable RetroArch installed successfully!\n{msg}")
        else:
            QMessageBox.warning(self, "Installation Error", f"Could not install RetroArch:\n{msg}")

    def _on_download_core_clicked(self, core_dll: str):
        self.ra_progress_bar.setValue(0)
        self.ra_progress_bar.show()
        self.ra_action_lbl.setText(f"Downloading core {core_dll} from Libretro...")

        self._dl_worker = CoreDownloadWorker(core_dll, parent=self)
        self._dl_worker.progress.connect(lambda pct, msg: (self.ra_progress_bar.setValue(pct), self.ra_action_lbl.setText(msg)))
        self._dl_worker.finished.connect(self._on_core_download_finished)
        self._dl_worker.start()

    def _on_core_download_finished(self, success: bool, core_dll: str, msg: str):
        self.ra_progress_bar.hide()
        self.ra_action_lbl.setText("")
        if success:
            self.refresh_status()
            self.setup_changed.emit()
            QMessageBox.information(self, "Core Installed", f"Core '{core_dll}' installed successfully and is ready to play!")
        else:
            QMessageBox.warning(self, "Download Error", f"Could not install core '{core_dll}':\n{msg}")
