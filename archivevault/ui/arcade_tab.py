import os
import sys
from typing import List, Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
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
    format_size,
    get_dosbox_info,
    get_dosbox_path,
    get_launchbox_path,
    get_mame_info,
    get_mame_path,
    launch_launchbox,
    launch_local_dosbox,
    launch_mame_game,
    open_containing_folder,
    open_file,
    open_with_7zip,
)
from archivevault.ui.dosbox_player import detect_retro_platform
from archivevault.ui.mame_installer_dialog import LaunchBoxGuideDialog, MameInstallerDialog

RETRO_FILE_EXTENSIONS = (
    '.zip', '.exe', '.com', '.bat', '.iso', '.bin', '.cue', '.rom',
    '.dsk', '.adf', '.cpr', '.chd', '.img', '.7z', '.tar', '.gz'
)

# Legendary instant-play classics from the Internet Archive
CURATED_CLASSICS = [
    {
        "id": "msdos_Prince_of_Persia_1990",
        "title": "Prince of Persia (1990)",
        "platform": "MS-DOS",
        "badge_color": "#065f46",
        "desc": "Jordan Mechner's rotoscoped cinematic platforming masterpiece.",
        "icon": "🗡️"
    },
    {
        "id": "msdos_Wolfenstein_3D_1992",
        "title": "Wolfenstein 3D (1992)",
        "platform": "MS-DOS",
        "badge_color": "#065f46",
        "desc": "Id Software's grandfather of the first-person shooter genre.",
        "icon": "🏰"
    },
    {
        "id": "Doom-2",
        "title": "Doom II: Hell on Earth (1994)",
        "platform": "MS-DOS",
        "badge_color": "#065f46",
        "desc": "The legendary sci-fi FPS that redefined video games forever.",
        "icon": "🔫"
    },
    {
        "id": "msdos_Oregon_Trail_The_1990",
        "title": "The Oregon Trail (1990)",
        "platform": "MS-DOS",
        "badge_color": "#065f46",
        "desc": "MECC's timeless pioneer trail survival and resource simulation.",
        "icon": "🏕️"
    },
    {
        "id": "msdos_SimCity_1989",
        "title": "SimCity (1989)",
        "platform": "MS-DOS",
        "badge_color": "#065f46",
        "desc": "Will Wright's iconic urban planning and city simulator.",
        "icon": "🏙️"
    },
    {
        "id": "msdos_Golden_Axe_1990",
        "title": "Golden Axe (1990)",
        "platform": "MS-DOS",
        "badge_color": "#065f46",
        "desc": "Sega's classic high-fantasy hack-and-slash arcade adventure.",
        "icon": "⚔️"
    },
    {
        "id": "msdos_Pac-Man_1983",
        "title": "Pac-Man (MS-DOS 1983)",
        "platform": "MS-DOS",
        "badge_color": "#065f46",
        "desc": "The official IBM PC port of Namco's immortal arcade maze runner.",
        "icon": "🟡"
    },
    {
        "id": "msdos_Disneys_Aladdin_1994",
        "title": "Disney's Aladdin (1994)",
        "platform": "MS-DOS",
        "badge_color": "#065f46",
        "desc": "Virgin Interactive's beloved Arabian Nights side-scrolling platformer.",
        "icon": "🧞"
    },
    {
        "id": "arcade_outrun",
        "title": "Out Run (Arcade 1986)",
        "platform": "Arcade",
        "badge_color": "#dc2626",
        "desc": "Yu Suzuki & Sega's legendary Ferrari Testarossa arcade racer.",
        "icon": "🏎️"
    },
    {
        "id": "arcade_1941",
        "title": "1941: Counter Attack (Arcade)",
        "platform": "Arcade",
        "badge_color": "#dc2626",
        "desc": "Capcom's classic vertical-scrolling WWII aircraft shooter.",
        "icon": "✈️"
    },
    {
        "id": "arcade_10yard",
        "title": "10-Yard Fight (Arcade)",
        "platform": "Arcade",
        "badge_color": "#dc2626",
        "desc": "Irem's pioneering American football coin-op arcade game.",
        "icon": "🏈"
    },
    {
        "id": "arcade_defender",
        "title": "Defender (Arcade 1981)",
        "platform": "Arcade",
        "badge_color": "#dc2626",
        "desc": "Williams' blistering twin-stick side-scrolling space defender.",
        "icon": "🚀"
    },
    {
        "id": "lemmings_cpc",
        "title": "Lemmings (Amstrad CPC)",
        "platform": "Amstrad CPC",
        "badge_color": "#0891b2",
        "desc": "DMA Design's iconic puzzle-strategy game ported to the CPC 6128.",
        "icon": "🐹"
    },
    {
        "id": "Oh_Mummy_1984_Amsoft",
        "title": "Oh Mummy!! (Amstrad CPC)",
        "platform": "Amstrad CPC",
        "badge_color": "#0891b2",
        "desc": "The quintessential Amstrad CPC 464 pack-in pyramid maze game.",
        "icon": "🏺"
    }
]

KNOWN_IA_ARCADE_ROMS = {
    "1941": ("arcade_1941", "1941: Counter Attack"),
    "10yard": ("arcade_10yard", "10-Yard Fight"),
    "outrun": ("arcade_outrun", "Out Run"),
    "defender": ("arcade_defender", "Defender"),
    "joust": ("arcade_joust", "Joust"),
    "berzerk": ("arcade_berzerk", "Berzerk"),
    "mrdo": ("arcade_mrdo", "Mr. Do!"),
    "qbert": ("arcade_qbert", "Q*Bert"),
    "astrob": ("arcade_astrob", "Astro Blaster"),
    "paperboy": ("arcade_paperboy", "Paperboy"),
    "galaxian": ("arcade_galaxian", "Galaxian"),
    "frogger": ("arcade_frogger", "Frogger"),
    "digdug": ("arcade_digdug", "Dig Dug"),
    "centiped": ("arcade_centiped", "Centipede"),
    "dkong": ("arcade_dkong", "Donkey Kong"),
    "mario": ("arcade_mario", "Mario Bros"),
}

class ArcadeTab(QWidget):
    """
    Dedicated Retro Arcade & DOSBox Hub.
    Allows browsing & launching local games on the hard drive,
    configuring native DOSBox, and 1-click playing Internet Archive classics.
    """
    play_dosbox_requested = pyqtSignal(str, str) # identifier, display_title
    inspect_item_requested = pyqtSignal(str) # identifier
    browse_retro_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.local_games: List[dict] = []
        self._init_ui()
        self.scan_local_games()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Outer Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        canvas = QWidget()
        canvas_layout = QVBoxLayout(canvas)
        canvas_layout.setContentsMargins(28, 24, 28, 24)
        canvas_layout.setSpacing(22)

        # --- Top Hero Banner ---
        hero_card = QFrame()
        hero_card.setObjectName("articleCard")
        hero_layout = QVBoxLayout(hero_card)
        hero_layout.setContentsMargins(22, 20, 22, 20)
        hero_layout.setSpacing(14)

        top_row = QHBoxLayout()
        top_row.setSpacing(14)

        icon_lbl = QLabel("🕹️")
        icon_lbl.setStyleSheet("font-size: 38px;")
        top_row.addWidget(icon_lbl)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        title_lbl = QLabel("DOSBox Retro Arcade & Emulator")
        title_lbl.setStyleSheet("font-size: 22px; font-weight: 800; color: #ffffff;")
        info_layout.addWidget(title_lbl)

        sub_lbl = QLabel("Launch vintage MS-DOS, Amstrad CPC, Amiga, Arcade, and retro console games directly from your hard drive or the Internet Archive.")
        sub_lbl.setStyleSheet("font-size: 13px; color: #a1a1aa;")
        sub_lbl.setWordWrap(True)
        info_layout.addWidget(sub_lbl)
        top_row.addLayout(info_layout, stretch=1)

        hero_layout.addLayout(top_row)

        # Action Buttons Row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_load_pc = QPushButton("📁 Load Game from Hard Drive...")
        self.btn_load_pc.setObjectName("primaryBtn")
        self.btn_load_pc.setStyleSheet("font-size: 13px; font-weight: 700; padding: 9px 18px;")
        self.btn_load_pc.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_load_pc.clicked.connect(self._on_pick_local_game)
        btn_row.addWidget(self.btn_load_pc)

        self.btn_open_folder = QPushButton("📂 Open Games Folder")
        self.btn_open_folder.setStyleSheet("font-size: 12px; font-weight: 600; padding: 8px 14px;")
        self.btn_open_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_folder.clicked.connect(self._open_games_folder)
        btn_row.addWidget(self.btn_open_folder)

        self.btn_browse_online = QPushButton("🌐 Browse Retro Vault Online")
        self.btn_browse_online.setStyleSheet("font-size: 12px; font-weight: 600; padding: 8px 14px;")
        self.btn_browse_online.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_browse_online.clicked.connect(self.browse_retro_requested.emit)
        btn_row.addWidget(self.btn_browse_online)

        btn_row.addStretch(1)
        hero_layout.addLayout(btn_row)

        # Emulator Status Card (DOSBox & MAME Arcade)
        self.dosbox_cfg_card = QFrame()
        self.dosbox_cfg_card.setStyleSheet("""
            QFrame {
                background-color: #141417;
                border: 1px solid #27272a;
                border-radius: 8px;
                padding: 6px 12px;
            }
        """)
        cfg_layout = QVBoxLayout(self.dosbox_cfg_card)
        cfg_layout.setContentsMargins(8, 6, 8, 6)
        cfg_layout.setSpacing(6)

        # Row 1: DOSBox
        row_dosbox = QHBoxLayout()
        row_dosbox.setSpacing(10)
        self.dosbox_status_lbl = QLabel()
        self.dosbox_status_lbl.setStyleSheet("font-size: 12px; color: #d4d4d8;")
        row_dosbox.addWidget(self.dosbox_status_lbl, stretch=1)

        self.btn_toggle_dosbox = QPushButton("Disable External")
        self.btn_toggle_dosbox.setFixedSize(120, 26)
        self.btn_toggle_dosbox.setStyleSheet("font-size: 11px; font-weight: 600;")
        self.btn_toggle_dosbox.setToolTip("Toggle between local DOSBox executable and ArchiveVault's built-in WebAssembly player")
        self.btn_toggle_dosbox.clicked.connect(self._on_toggle_disable_dosbox)
        row_dosbox.addWidget(self.btn_toggle_dosbox)

        btn_change_dosbox = QPushButton("Configure DOSBox...")
        btn_change_dosbox.setFixedSize(130, 26)
        btn_change_dosbox.setStyleSheet("font-size: 11px; font-weight: 600;")
        btn_change_dosbox.clicked.connect(self._on_configure_dosbox)
        row_dosbox.addWidget(btn_change_dosbox)
        cfg_layout.addLayout(row_dosbox)

        # Row 2: MAME Arcade
        row_mame = QHBoxLayout()
        row_mame.setSpacing(10)
        self.mame_status_lbl = QLabel()
        self.mame_status_lbl.setStyleSheet("font-size: 12px; color: #d4d4d8;")
        row_mame.addWidget(self.mame_status_lbl, stretch=1)

        self.btn_open_lb = QPushButton("LaunchBox 🚀")
        self.btn_open_lb.setFixedSize(115, 26)
        self.btn_open_lb.setStyleSheet("font-size: 11px; font-weight: 600; background-color: #3b82f6; color: #ffffff;")
        self.btn_open_lb.setToolTip("Open LaunchBox frontend or view LaunchBox emulator setup guide")
        self.btn_open_lb.clicked.connect(self._on_launchbox_action)
        row_mame.addWidget(self.btn_open_lb)

        self.btn_mame_action = QPushButton("⚡ Install MAME")
        self.btn_mame_action.setFixedSize(130, 26)
        self.btn_mame_action.setStyleSheet("font-size: 11px; font-weight: 600; background-color: #10b981; color: #ffffff;")
        self.btn_mame_action.clicked.connect(self._on_mame_action)
        row_mame.addWidget(self.btn_mame_action)
        cfg_layout.addLayout(row_mame)

        self._update_dosbox_status_label()

        hero_layout.addWidget(self.dosbox_cfg_card)
        canvas_layout.addWidget(hero_card)

        # --- Section 1: Local Games Library (On Your PC) ---
        local_card = QFrame()
        local_card.setObjectName("articleCard")
        local_layout = QVBoxLayout(local_card)
        local_layout.setContentsMargins(22, 18, 22, 18)
        local_layout.setSpacing(14)

        sec_header = QHBoxLayout()
        sec_header.setSpacing(12)

        sec_title_box = QVBoxLayout()
        sec_title_box.setSpacing(2)
        sec_title = QLabel("💾 Local Games Library (On Your PC)")
        sec_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #38bdf8;")
        sec_title_box.addWidget(sec_title)

        self.sec_sub = QLabel("Scanning your download repository for playable MS-DOS, Arcade, and retro console ROMs.")
        self.sec_sub.setStyleSheet("font-size: 12px; color: #a1a1aa;")
        sec_title_box.addWidget(self.sec_sub)
        sec_header.addLayout(sec_title_box, stretch=1)

        self.search_filter = QLineEdit()
        self.search_filter.setPlaceholderText("🔍 Filter local games by name or format...")
        self.search_filter.setFixedWidth(280)
        self.search_filter.textChanged.connect(self._filter_local_table)
        sec_header.addWidget(self.search_filter)

        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.setFixedWidth(90)
        btn_refresh.clicked.connect(self.scan_local_games)
        sec_header.addWidget(btn_refresh)

        local_layout.addLayout(sec_header)

        # Local Games Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Game / ROM File", "Platform", "Format", "Size", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 210)
        self.table.verticalHeader().setDefaultSectionSize(46)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setMinimumHeight(240)
        local_layout.addWidget(self.table)

        canvas_layout.addWidget(local_card)

        # --- Section 2: Online Instant Classics (Internet Archive WebAssembly Theater) ---
        online_card = QFrame()
        online_card.setObjectName("articleCard")
        online_layout = QVBoxLayout(online_card)
        online_layout.setContentsMargins(22, 18, 22, 18)
        online_layout.setSpacing(14)

        onl_title_box = QVBoxLayout()
        onl_title_box.setSpacing(2)
        onl_title = QLabel("🌐 Instant Internet Archive Classics")
        onl_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #38bdf8;")
        onl_title_box.addWidget(onl_title)

        onl_sub = QLabel("Stream and play directly inside ArchiveVault via WebAssembly emulation with CRT filters, full gamepad support, and auto-typing.")
        onl_sub.setStyleSheet("font-size: 12px; color: #a1a1aa;")
        onl_title_box.addWidget(onl_sub)
        online_layout.addLayout(onl_title_box)

        # Grid of Curated Classics
        grid_widget = QWidget()
        grid_layout = QHBoxLayout(grid_widget)
        grid_layout.setContentsMargins(0, 4, 0, 4)
        grid_layout.setSpacing(12)

        # Two columns or flow of cards
        col1 = QVBoxLayout()
        col1.setSpacing(10)
        col2 = QVBoxLayout()
        col2.setSpacing(10)

        for i, classic in enumerate(CURATED_CLASSICS):
            card = self._create_classic_card(classic)
            if i % 2 == 0:
                col1.addWidget(card)
            else:
                col2.addWidget(card)

        col1.addStretch(1)
        col2.addStretch(1)
        grid_layout.addLayout(col1, stretch=1)
        grid_layout.addLayout(col2, stretch=1)
        online_layout.addWidget(grid_widget)

        canvas_layout.addWidget(online_card)

        # --- Section 3: Emulator Controls & Hotkeys Guide ---
        guide_card = QFrame()
        guide_card.setObjectName("articleCard")
        guide_layout = QVBoxLayout(guide_card)
        guide_layout.setContentsMargins(22, 16, 22, 16)
        guide_layout.setSpacing(10)

        guide_title = QLabel("⌨️ DOSBox Controls & Hotkeys Reference")
        guide_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #38bdf8;")
        guide_layout.addWidget(guide_title)

        guide_html = """
        <div style="font-size: 12px; color: #d4d4d8; line-height: 1.6;">
            <b>• Alt + Enter:</b> Toggle Fullscreen mode.<br>
            <b>• Ctrl + F10:</b> Lock / Unlock mouse cursor to DOSBox window.<br>
            <b>• Ctrl + F11 / F12:</b> Decrease / Increase CPU Cycles (Game Speed / Turbo).<br>
            <b>• Ctrl + F9:</b> Quick terminate DOSBox session.<br>
            <b>• Gamepad / Controller:</b> Plug in any Xbox, PlayStation, or USB controller. Left Stick / D-Pad controls direction, Right Stick controls mouse, and A/B/X/Y map to action buttons.
        </div>
        """
        guide_lbl = QLabel(guide_html)
        guide_lbl.setTextFormat(Qt.TextFormat.RichText)
        guide_layout.addWidget(guide_lbl)

        canvas_layout.addWidget(guide_card)

        canvas_layout.addStretch(1)
        self.scroll_area.setWidget(canvas)
        main_layout.addWidget(self.scroll_area, stretch=1)

    def _update_dosbox_status_label(self):
        info = get_dosbox_info()
        dosbox_path = info.get("path")
        source = info.get("source")

        if source == "Disabled":
            self.dosbox_status_lbl.setText(
                "🎮 <b>DOSBox:</b> <span style='color: #f59e0b;'>In-App WebAssembly Player</span> &nbsp;•&nbsp; External DOSBox disabled"
            )
            if hasattr(self, "btn_toggle_dosbox"):
                self.btn_toggle_dosbox.setText("Enable DOSBox")
        elif dosbox_path and os.path.exists(dosbox_path):
            origin_desc = "LaunchBox 0.74" if info.get("is_launchbox") else source
            self.dosbox_status_lbl.setText(
                f"🎮 <b>DOSBox:</b> <span style='color: #4ade80;'>Ready ({origin_desc} • HD 1280x960)</span> &nbsp;•&nbsp; <code>{dosbox_path}</code>"
            )
            if hasattr(self, "btn_toggle_dosbox"):
                self.btn_toggle_dosbox.setText("Disable External")
        else:
            self.dosbox_status_lbl.setText(
                "🎮 <b>DOSBox:</b> <span style='color: #f59e0b;'>Not Configured</span> &nbsp;•&nbsp; Games launch via built-in WebAssembly player"
            )
            if hasattr(self, "btn_toggle_dosbox"):
                self.btn_toggle_dosbox.setText("Disable External")

        # Update MAME Arcade status
        mame_info = get_mame_info()
        mame_path = mame_info.get("path")
        if hasattr(self, "mame_status_lbl"):
            if mame_path and os.path.exists(mame_path):
                self.mame_status_lbl.setText(
                    f"🕹️ <b>MAME Arcade:</b> <span style='color: #4ade80;'>Ready ({mame_info.get('source')})</span> &nbsp;•&nbsp; <code>{mame_path}</code>"
                )
                if hasattr(self, "btn_mame_action"):
                    self.btn_mame_action.setText("Configure MAME...")
                    self.btn_mame_action.setStyleSheet("font-size: 11px; font-weight: 600;")
            else:
                self.mame_status_lbl.setText(
                    "🕹️ <b>MAME Arcade:</b> <span style='color: #f59e0b;'>Not Configured</span> &nbsp;•&nbsp; 1-Click portable setup available"
                )
                if hasattr(self, "btn_mame_action"):
                    self.btn_mame_action.setText("⚡ Install MAME")
                    self.btn_mame_action.setStyleSheet("font-size: 11px; font-weight: 600; background-color: #10b981; color: #ffffff;")

        lb_path = info.get("launchbox_path")
        if hasattr(self, "btn_open_lb"):
            self.btn_open_lb.setVisible(bool(lb_path and os.path.exists(lb_path)))

    def _on_toggle_disable_dosbox(self):
        if settings.dosbox_path.lower() == "disabled":
            settings.dosbox_path = ""
            settings.save()
            QMessageBox.information(
                self,
                "DOSBox Enabled",
                "External DOSBox has been re-enabled and will auto-detect installed versions."
            )
        else:
            settings.dosbox_path = "disabled"
            settings.save()
            QMessageBox.information(
                self,
                "In-App Player Active",
                "External DOSBox disabled. All retro games will now play directly in ArchiveVault's built-in WebAssembly Theater."
            )
        self._update_dosbox_status_label()

    def _on_launchbox_action(self):
        mame_path = get_mame_path()
        if not mame_path or not os.path.exists(mame_path):
            dlg = LaunchBoxGuideDialog(self)
            res = dlg.exec()
            if res == 2:
                self._on_mame_action()
        else:
            launch_launchbox()

    def _on_mame_action(self):
        mame_path = get_mame_path()
        if mame_path and os.path.exists(mame_path):
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select MAME Arcade Executable",
                os.path.dirname(mame_path),
                "MAME Executable (*mame*.exe);;All Files (*.*)"
            )
            if file_path and os.path.exists(file_path):
                settings.mame_path = file_path
                settings.save()
                self._update_dosbox_status_label()
                QMessageBox.information(
                    self,
                    "MAME Configured",
                    f"MAME Arcade executable successfully set to:\n{file_path}"
                )
        else:
            dlg = MameInstallerDialog(self)
            dlg.installation_finished.connect(lambda _: self._update_dosbox_status_label())
            dlg.exec()

    def _on_configure_dosbox(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select DOSBox Executable",
            os.path.expanduser("~"),
            "DOSBox Executable (*.exe);;All Files (*.*)"
        )
        if file_path and os.path.exists(file_path):
            settings.dosbox_path = file_path
            settings.save()
            self._update_dosbox_status_label()
            QMessageBox.information(
                self,
                "DOSBox Configured",
                f"DOSBox executable successfully set to:\n{file_path}"
            )

    def _create_classic_card(self, classic: dict) -> QFrame:
        card = QFrame()
        card.setObjectName("curatedCard")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(14, 10, 14, 10)
        card_layout.setSpacing(12)

        icon_lbl = QLabel(classic.get("icon", "🕹️"))
        icon_lbl.setStyleSheet("font-size: 24px;")
        card_layout.addWidget(icon_lbl)

        info = QVBoxLayout()
        info.setSpacing(2)

        t_row = QHBoxLayout()
        t_row.setSpacing(8)

        t_lbl = QLabel(classic["title"])
        t_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #ffffff;")
        t_row.addWidget(t_lbl)

        badge = QLabel(classic["platform"])
        badge.setStyleSheet(f"""
            background-color: {classic.get("badge_color", "#065f46")};
            color: #ffffff;
            font-size: 9px;
            font-weight: 800;
            padding: 2px 6px;
            border-radius: 4px;
        """)
        t_row.addWidget(badge)
        t_row.addStretch(1)
        info.addLayout(t_row)

        d_lbl = QLabel(classic["desc"])
        d_lbl.setStyleSheet("font-size: 11px; color: #a1a1aa;")
        d_lbl.setWordWrap(True)
        info.addWidget(d_lbl)

        card_layout.addLayout(info, stretch=1)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(6)

        play_btn = QPushButton("▶ Play In-App")
        play_btn.setObjectName("primaryBtn")
        play_btn.setFixedSize(100, 30)
        play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        play_btn.clicked.connect(lambda _, c=classic: self.play_dosbox_requested.emit(c["id"], c["title"]))
        btn_box.addWidget(play_btn)

        dossier_btn = QPushButton("📖")
        dossier_btn.setToolTip("View Subject Dossier & Historical Context")
        dossier_btn.setFixedSize(32, 30)
        dossier_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        dossier_btn.clicked.connect(lambda _, c=classic: self.inspect_item_requested.emit(c["id"]))
        btn_box.addWidget(dossier_btn)

        card_layout.addLayout(btn_box)
        return card

    def _open_games_folder(self):
        folder = settings.download_dir
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
        open_containing_folder(folder)

    def _on_pick_local_game(self):
        """Prompt user to select any game or executable from their hard drive and launch it."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Game or ROM from Hard Drive",
            settings.download_dir,
            "Retro Games & Executables (*.zip *.exe *.com *.bat *.iso *.bin *.cue *.rom *.dsk *.adf *.cpr *.7z);;All Files (*.*)"
        )
        if not file_path:
            return

        self._launch_game_file(file_path)

    def _launch_game_file(self, file_path: str):
        """Intelligently launch a game file in high-res DOSBox, In-App Player, or LaunchBox."""
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "File Not Found", f"Game file not found:\n{file_path}")
            return

        fname = os.path.basename(file_path)
        ext = os.path.splitext(fname)[1].lower()
        parent_dir = os.path.basename(os.path.dirname(file_path))
        combined_name = f"{parent_dir}_{fname}"
        platform_info = detect_retro_platform(combined_name)
        platform_name = platform_info.get("name", "MS-DOS")

        is_arcade = (
            platform_name == "Arcade" or
            "mame" in parent_dir.lower() or
            "arcade" in parent_dir.lower() or
            "mame" in fname.lower()
        )

        # 1. ARCADE / MAME ROMS
        if is_arcade:
            self._handle_arcade_rom_launch(file_path, fname, parent_dir)
            return

        # 2. MICROCOMPUTERS / CONSOLES (Amstrad CPC, Amiga, C64, ZX Spectrum, etc.)
        if platform_name in ("Amstrad CPC", "ZX Spectrum", "Commodore 64", "Amiga", "Atari", "Apple II"):
            self._handle_non_dos_microcomputer_launch(file_path, fname, platform_name)
            return

        # 3. DIRECT DOS EXECUTABLES (.exe, .com, .bat, .conf)
        if ext in ('.exe', '.com', '.bat', '.conf'):
            dosbox_exe = get_dosbox_path()
            if dosbox_exe:
                success = launch_local_dosbox(file_path)
                if not success:
                    open_file(file_path)
            else:
                open_file(file_path)
            return

        # 4. DOS ZIP ARCHIVES / OTHER ARCHIVES
        if ext in ('.zip', '.7z', '.gz', '.tar'):
            dosbox_exe = get_dosbox_path()
            if dosbox_exe:
                reply = QMessageBox.question(
                    self,
                    "Launch DOS Game Archive",
                    f"Launch MS-DOS game '{fname}' in high-resolution scaled DOSBox?\n\n"
                    "ArchiveVault will automatically unpack and run the game (1280x960 4:3).\n\n"
                    "Yes: Launch in DOSBox\n"
                    "No: Open containing folder",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
                )
                if reply == QMessageBox.StandardButton.Yes:
                    launch_local_dosbox(file_path)
                elif reply == QMessageBox.StandardButton.No:
                    open_containing_folder(file_path)
            else:
                open_containing_folder(file_path)
            return

        # Fallback
        open_file(file_path)

    def _handle_arcade_rom_launch(self, file_path: str, fname: str, parent_dir: str):
        """Handle user launching an Arcade / MAME ROM with direct MAME support and guides."""
        mame_path = get_mame_path()
        has_mame = bool(mame_path and os.path.exists(mame_path))
        lb_exe = get_launchbox_path()
        has_lb = bool(lb_exe and os.path.exists(lb_exe))
        rom_stem = os.path.splitext(fname)[0].lower()

        verified_arcade = KNOWN_IA_ARCADE_ROMS.get(rom_stem)

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Arcade ROM (MAME)")
        msg_box.setIcon(QMessageBox.Icon.Information)

        if has_mame:
            mame_info = get_mame_info()
            src = mame_info.get("source", "MAME")
            html_text = f"""
            <div style='font-size: 13px; line-height: 1.5;'>
                <h3 style='margin: 0 0 8px 0; color: #10b981;'>🕹️ Arcade Cabinet ROM: {fname}</h3>
                <p><b>{fname}</b> is ready to play in <b>MAME Arcade Emulator</b> ({src}).</p>
                <p style='color: #a1a1aa;'>
                    Click <b>Play in MAME Arcade</b> below to launch directly with authentic video scaling, sound, and arcade controller support.
                </p>
                <p><b>Choose an action:</b></p>
            </div>
            """
        elif verified_arcade:
            ia_id, ia_title = verified_arcade
            html_text = f"""
            <div style='font-size: 13px; line-height: 1.5;'>
                <h3 style='margin: 0 0 8px 0; color: #f43f5e;'>🕹️ Arcade Cabinet ROM: {ia_title}</h3>
                <p><b>{fname}</b> matches verified Internet Arcade game <b>{ia_title}</b>!</p>
                <p style='color: #a1a1aa;'>
                    You can play this arcade classic directly inside ArchiveVault via WebAssembly MAME, or install standalone MAME for offline play.
                </p>
                <p><b>Choose an action:</b></p>
            </div>
            """
        else:
            lb_hint = "LaunchBox is installed on your PC, but needs MAME enabled (Tools > Manage > Emulators > Add > Download MAME)." if has_lb else "Install MAME to run offline arcade ROMs."
            html_text = f"""
            <div style='font-size: 13px; line-height: 1.5;'>
                <h3 style='margin: 0 0 8px 0; color: #f43f5e;'>🕹️ Offline Arcade ROM (MAME)</h3>
                <p><b>{fname}</b> is an offline Arcade Machine ROM from your downloaded <i>{parent_dir}</i> collection.</p>
                <p style='color: #a1a1aa;'>
                    • <b>MAME Required:</b> Arcade ROMs need the MAME emulator to run.<br>
                    • <b>Setup Options:</b> Use ArchiveVault's <b>1-Click MAME Install</b> (~83 MB portable), or follow the 3-step LaunchBox setup guide.<br>
                    • <i>{lb_hint}</i>
                </p>
                <p><b>Choose an action:</b></p>
            </div>
            """

        msg_box.setText(html_text)

        btn_direct_mame = None
        btn_install_mame = None
        btn_lb = None
        btn_ia = None

        if has_mame:
            btn_direct_mame = msg_box.addButton("▶ Play in MAME Arcade (Direct)", QMessageBox.ButtonRole.ActionRole)
        else:
            btn_install_mame = msg_box.addButton("⚡ 1-Click Install MAME", QMessageBox.ButtonRole.ActionRole)

        if verified_arcade:
            btn_ia = msg_box.addButton("🌐 Play In-App (Online MAME)", QMessageBox.ButtonRole.ActionRole)

        if has_lb:
            lb_btn_text = "🚀 LaunchBox" if has_mame else "🚀 LaunchBox (Setup Guide)"
            btn_lb = msg_box.addButton(lb_btn_text, QMessageBox.ButtonRole.ActionRole)

        btn_folder = msg_box.addButton("📂 Open ROM Folder", QMessageBox.ButtonRole.ActionRole)
        btn_cancel = msg_box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)

        msg_box.exec()
        clicked = msg_box.clickedButton()

        if btn_direct_mame and clicked == btn_direct_mame:
            success = launch_mame_game(file_path)
            if not success:
                QMessageBox.warning(self, "Launch Error", f"Could not launch MAME with {fname}. Check MAME configuration.")
        elif btn_install_mame and clicked == btn_install_mame:
            dlg = MameInstallerDialog(self)
            def on_installed(path):
                self._update_dosbox_status_label()
                launch_mame_game(file_path)
            dlg.installation_finished.connect(on_installed)
            dlg.exec()
        elif btn_ia and clicked == btn_ia:
            ia_id, ia_title = verified_arcade
            self.play_dosbox_requested.emit(ia_id, f"Arcade: {ia_title}")
        elif has_lb and clicked == btn_lb:
            if not has_mame:
                dlg = LaunchBoxGuideDialog(self)
                res = dlg.exec()
                if res == 2:
                    self._on_mame_action()
            else:
                launch_launchbox(file_path)
        elif clicked == btn_folder:
            open_containing_folder(file_path)

    def _handle_non_dos_microcomputer_launch(self, file_path: str, fname: str, platform_name: str):
        """Handle Amstrad CPC, Amiga, C64, ZX Spectrum files."""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(f"{platform_name} Game")
        msg_box.setIcon(QMessageBox.Icon.Information)

        html_text = f"""
        <div style='font-size: 13px; line-height: 1.5;'>
            <h3 style='margin: 0 0 8px 0; color: #38bdf8;'>💾 {platform_name} Software</h3>
            <p><b>{fname}</b> is a <b>{platform_name}</b> disk/tape image, not an MS-DOS PC executable.</p>
            <p style='color: #a1a1aa;'>
                DOSBox is an MS-DOS PC emulator. To play this {platform_name} title, you can stream it through ArchiveVault's built-in WebAssembly multi-system theater or open your local emulator.
            </p>
        </div>
        """
        msg_box.setText(html_text)

        btn_inapp = msg_box.addButton("🌐 Play in ArchiveVault Theater", QMessageBox.ButtonRole.ActionRole)
        btn_open = msg_box.addButton("📂 Open File / Folder", QMessageBox.ButtonRole.ActionRole)
        btn_cancel = msg_box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)

        msg_box.exec()
        clicked = msg_box.clickedButton()

        if clicked == btn_inapp:
            stem = os.path.splitext(fname)[0]
            ident = f"{platform_name.lower().replace(' ', '_')}_{stem}"
            self.play_dosbox_requested.emit(ident, f"{platform_name}: {stem}")
        elif clicked == btn_open:
            open_containing_folder(file_path)

    def scan_local_games(self):
        """Scan settings.download_dir for all retro game files."""
        self.local_games.clear()
        scan_dir = settings.download_dir

        if not os.path.exists(scan_dir):
            self.table.setRowCount(0)
            self.sec_sub.setText("No games directory found. Download games from ArchiveVault or pick a file from PC.")
            return

        found = []
        max_scan = 500
        count = 0

        for root, dirs, files in os.walk(scan_dir):
            for f in files:
                if f.lower().endswith(RETRO_FILE_EXTENSIONS):
                    full_p = os.path.join(root, f)
                    try:
                        sz = os.path.getsize(full_p)
                    except OSError:
                        sz = 0

                    # Detect platform
                    parent_name = os.path.basename(root)
                    combined_name = f"{parent_name}_{f}"
                    p_info = detect_retro_platform(combined_name)
                    
                    found.append({
                        "filename": f,
                        "path": full_p,
                        "rel_dir": os.path.relpath(root, scan_dir),
                        "size": sz,
                        "platform": p_info["name"],
                        "badge_color": p_info.get("badge_color", "#065f46"),
                        "ext": os.path.splitext(f)[1].upper()
                    })
                    count += 1
                    if count >= max_scan:
                        break
            if count >= max_scan:
                break

        # Sort by filename
        found.sort(key=lambda x: x["filename"].lower())
        self.local_games = found
        self._populate_table(found)
        self.sec_sub.setText(f"Found {len(found)} retro game(s) and ROMs in: {scan_dir}")

    def _filter_local_table(self, query: str):
        q = query.strip().lower()
        if not q:
            self._populate_table(self.local_games)
            return
        filtered = [g for g in self.local_games if q in g["filename"].lower() or q in g["platform"].lower() or q in g["ext"].lower()]
        self._populate_table(filtered)

    def _populate_table(self, games: List[dict]):
        self.table.setRowCount(len(games))
        for row, g in enumerate(games):
            # 0: Name & path
            name_widget = QWidget()
            nw_layout = QVBoxLayout(name_widget)
            nw_layout.setContentsMargins(6, 4, 6, 4)
            nw_layout.setSpacing(2)

            name_lbl = QLabel(g["filename"])
            name_lbl.setStyleSheet("font-weight: 600; color: #f4f4f5; font-size: 13px;")
            name_lbl.setToolTip(g["path"])
            nw_layout.addWidget(name_lbl)

            if g["rel_dir"] and g["rel_dir"] != ".":
                dir_lbl = QLabel(f"📁 {g['rel_dir']}")
                dir_lbl.setStyleSheet("font-size: 11px; color: #71717a;")
                nw_layout.addWidget(dir_lbl)

            self.table.setCellWidget(row, 0, name_widget)

            # 1: Platform Badge
            badge_widget = QWidget()
            bw_layout = QHBoxLayout(badge_widget)
            bw_layout.setContentsMargins(4, 4, 4, 4)
            bw_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            p_badge = QLabel(g["platform"])
            p_badge.setStyleSheet(f"""
                background-color: {g['badge_color']};
                color: #ffffff;
                font-size: 10px;
                font-weight: 700;
                padding: 3px 7px;
                border-radius: 4px;
            """)
            bw_layout.addWidget(p_badge)
            self.table.setCellWidget(row, 1, badge_widget)

            # 2: Format
            fmt_item = QTableWidgetItem(g["ext"])
            fmt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, fmt_item)

            # 3: Size
            sz_item = QTableWidgetItem(format_size(g["size"]))
            sz_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 3, sz_item)

            # 4: Actions
            actions_widget = QWidget()
            act_layout = QHBoxLayout(actions_widget)
            act_layout.setContentsMargins(4, 4, 4, 4)
            act_layout.setSpacing(6)
            act_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            play_btn = QPushButton("▶ Play")
            play_btn.setObjectName("tableActionBtn")
            play_btn.setFixedSize(70, 28)
            play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            play_btn.clicked.connect(lambda _, p=g["path"]: self._launch_game_file(p))
            act_layout.addWidget(play_btn)

            folder_btn = QPushButton("Folder 📁")
            folder_btn.setObjectName("tablePauseBtn")
            folder_btn.setFixedSize(70, 28)
            folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            folder_btn.clicked.connect(lambda _, p=g["path"]: open_containing_folder(p))
            act_layout.addWidget(folder_btn)

            self.table.setCellWidget(row, 4, actions_widget)
