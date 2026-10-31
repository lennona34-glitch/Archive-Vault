import os
import sys
from typing import List, Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon
from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
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
    QTabWidget,
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
    # MS-DOS PC & Archives
    '.zip', '.exe', '.com', '.bat', '.iso', '.bin', '.cue', '.rom', '.img', '.7z', '.tar', '.gz', '.conf', '.vhd',
    # Atari ST (Floppy & Disk Images)
    '.st', '.msa', '.stx', '.dim',
    # Atari 8-Bit & Consoles
    '.atr', '.xfd', '.atx', '.a26', '.a78',
    # Amiga & Amstrad CPC
    '.adf', '.ipf', '.hdf', '.dsk', '.cpr',
    # Commodore 64 & VIC-20
    '.d64', '.t64', '.crt', '.prg', '.g64',
    # ZX Spectrum
    '.tap', '.tzx', '.z80', '.sna',
    # Retro Consoles & Optical
    '.smc', '.sfc', '.nes', '.gen', '.md', '.smd', '.chd', '.pbp'
)

# Curated Legit Online Retro Game Catalog (Free, Legal, Open Source, and Public Domain Preservation)
ONLINE_LEGIT_GAMES = [
    # --- COIN-OP ARCADE (MAME / Internet Arcade) ---
    {
        "id": "arcade_outrun",
        "title": "Out Run (Arcade 1986)",
        "platform": "Arcade",
        "category": "arcade",
        "license": "Arcade Preservation",
        "badge_color": "#dc2626",
        "desc": "Yu Suzuki & Sega's legendary Ferrari Testarossa arcade racer.",
        "icon": "🏎️"
    },
    {
        "id": "arcade_1941",
        "title": "1941: Counter Attack (Arcade)",
        "platform": "Arcade",
        "category": "arcade",
        "license": "Arcade Preservation",
        "badge_color": "#dc2626",
        "desc": "Capcom's classic vertical-scrolling WWII aircraft shooter.",
        "icon": "✈️"
    },
    {
        "id": "arcade_defender",
        "title": "Defender (Arcade 1981)",
        "platform": "Arcade",
        "category": "arcade",
        "license": "Arcade Preservation",
        "badge_color": "#dc2626",
        "desc": "Williams' blistering twin-stick side-scrolling space defender.",
        "icon": "🚀"
    },
    {
        "id": "arcade_10yard",
        "title": "10-Yard Fight (Arcade)",
        "platform": "Arcade",
        "category": "arcade",
        "license": "Arcade Preservation",
        "badge_color": "#dc2626",
        "desc": "Irem's pioneering American football coin-op arcade game.",
        "icon": "🏈"
    },
    {
        "id": "arcade_joust",
        "title": "Joust (Arcade 1982)",
        "platform": "Arcade",
        "category": "arcade",
        "license": "Arcade Preservation",
        "badge_color": "#dc2626",
        "desc": "Williams' flying ostrich jousting tournament masterpiece.",
        "icon": "🦤"
    },
    {
        "id": "arcade_galaxian",
        "title": "Galaxian (Arcade 1979)",
        "platform": "Arcade",
        "category": "arcade",
        "license": "Arcade Preservation",
        "badge_color": "#dc2626",
        "desc": "Namco's genre-defining RGB multi-color alien armada shooter.",
        "icon": "👾"
    },
    {
        "id": "arcade_frogger",
        "title": "Frogger (Arcade 1981)",
        "platform": "Arcade",
        "category": "arcade",
        "license": "Arcade Preservation",
        "badge_color": "#dc2626",
        "desc": "Konami's timeless highway and river hopping arcade puzzle.",
        "icon": "🐸"
    },
    {
        "id": "arcade_digdug",
        "title": "Dig Dug (Arcade 1982)",
        "platform": "Arcade",
        "category": "arcade",
        "license": "Arcade Preservation",
        "badge_color": "#dc2626",
        "desc": "Namco's underground tunneling and Pookas harpoon classic.",
        "icon": "⛏️"
    },
    {
        "id": "arcade_dkong",
        "title": "Donkey Kong (Arcade 1981)",
        "platform": "Arcade",
        "category": "arcade",
        "license": "Arcade Preservation",
        "badge_color": "#dc2626",
        "desc": "Shigeru Miyamoto's foundational platformer introducing Jumpman.",
        "icon": "🦍"
    },
    # --- MS-DOS PC CLASSICS ---
    {
        "id": "msdos_Prince_of_Persia_1990",
        "title": "Prince of Persia (1990)",
        "platform": "MS-DOS",
        "category": "dos",
        "license": "Historic Preservation",
        "badge_color": "#065f46",
        "desc": "Jordan Mechner's rotoscoped cinematic platforming masterpiece.",
        "icon": "🗡️"
    },
    {
        "id": "msdos_Wolfenstein_3D_1992",
        "title": "Wolfenstein 3D (1992)",
        "platform": "MS-DOS",
        "category": "dos",
        "license": "Shareware / ID Software",
        "badge_color": "#065f46",
        "desc": "Id Software's grandfather of the first-person shooter genre.",
        "icon": "🏰"
    },
    {
        "id": "Doom-2",
        "title": "Doom II: Hell on Earth (1994)",
        "platform": "MS-DOS",
        "category": "dos",
        "license": "Historic Preservation",
        "badge_color": "#065f46",
        "desc": "The legendary sci-fi FPS that redefined video games forever.",
        "icon": "🔫"
    },
    {
        "id": "msdos_Oregon_Trail_The_1990",
        "title": "The Oregon Trail (1990)",
        "platform": "MS-DOS",
        "category": "dos",
        "license": "Educational Freeware",
        "badge_color": "#065f46",
        "desc": "MECC's timeless pioneer trail survival and resource simulation.",
        "icon": "🏕️"
    },
    {
        "id": "msdos_SimCity_1989",
        "title": "SimCity (1989)",
        "platform": "MS-DOS",
        "category": "dos",
        "license": "Classic Preservation",
        "badge_color": "#065f46",
        "desc": "Will Wright's iconic urban planning and city simulator.",
        "icon": "🏙️"
    },
    {
        "id": "msdos_Golden_Axe_1990",
        "title": "Golden Axe (1990)",
        "platform": "MS-DOS",
        "category": "dos",
        "license": "Classic Preservation",
        "badge_color": "#065f46",
        "desc": "Sega's classic high-fantasy hack-and-slash arcade adventure.",
        "icon": "⚔️"
    },
    {
        "id": "msdos_Commander_Keen_4_-_Secret_of_the_Oracle_1991",
        "title": "Commander Keen 4: Secret of the Oracle (1991)",
        "platform": "MS-DOS",
        "category": "dos",
        "license": "Apogee Shareware",
        "badge_color": "#065f46",
        "desc": "Id Software & Apogee's legendary smooth-scrolling EGA platformer.",
        "icon": "🚀"
    },
    {
        "id": "msdos_Secret_of_Monkey_Island_The_1990",
        "title": "The Secret of Monkey Island (1990)",
        "platform": "MS-DOS",
        "category": "dos",
        "license": "Classic Preservation",
        "badge_color": "#065f46",
        "desc": "Ron Gilbert & LucasArts' hilarious pirate graphic adventure.",
        "icon": "🏴‍☠️"
    },
    # --- SCUMMVM & LEGAL FREEWARE RELEASES ---
    {
        "id": "Beneath_a_Steel_Sky_Floppy_DOS",
        "title": "Beneath a Steel Sky (1994)",
        "platform": "ScummVM / DOS",
        "category": "scummvm",
        "license": "Official Freeware (Revolution)",
        "badge_color": "#7c3aed",
        "desc": "Revolution Software's dystopian cyberpunk adventure with comic art by Dave Gibbons.",
        "icon": "🤖"
    },
    {
        "id": "flight-of-the-amazon-queen",
        "title": "Flight of the Amazon Queen (1995)",
        "platform": "ScummVM / DOS",
        "category": "scummvm",
        "license": "Official Freeware (IBI)",
        "badge_color": "#7c3aed",
        "desc": "Pulp 1940s South American jungle expedition point-and-click comedy.",
        "icon": "✈️"
    },
    {
        "id": "lure-of-the-temptress",
        "title": "Lure of the Temptress (1992)",
        "platform": "ScummVM / DOS",
        "category": "scummvm",
        "license": "Official Freeware (Revolution)",
        "badge_color": "#7c3aed",
        "desc": "Revolution Software's pioneering Virtual Theatre fantasy adventure.",
        "icon": "🧙"
    },
    {
        "id": "msdos_Dreamweb_1994",
        "title": "Dreamweb (1994)",
        "platform": "ScummVM / DOS",
        "category": "scummvm",
        "license": "Official Freeware (Creative Reality)",
        "badge_color": "#7c3aed",
        "desc": "Dark top-down cyberpunk thriller with atmospheric synthesized audio.",
        "icon": "🌧️"
    },
    {
        "id": "msdos_Sfinx_1997",
        "title": "Sfinx (1997)",
        "platform": "ScummVM / DOS",
        "category": "scummvm",
        "license": "Open Source / GPL",
        "badge_color": "#7c3aed",
        "desc": "Quirky time-travel Egyptian adventure officially open-sourced by LK Avalon.",
        "icon": "🗿"
    },
    # --- ATARI ST, AMIGA & 8-BIT COMPUTERS ---
    {
        "id": "atari_st_Dungeon_Master_1987_FTL",
        "title": "Dungeon Master (Atari ST 1987)",
        "platform": "Atari ST",
        "category": "computers",
        "license": "Historic Preservation",
        "badge_color": "#b45309",
        "desc": "FTL's groundbreaking real-time 3D grid dungeon crawler that defined a generation.",
        "icon": "🛡️"
    },
    {
        "id": "lemmings_amiga",
        "title": "Lemmings (Commodore Amiga 1991)",
        "platform": "Amiga",
        "category": "computers",
        "license": "Historic Preservation",
        "badge_color": "#2563eb",
        "desc": "DMA Design's iconic lemming rescue puzzle strategy with authentic Paula audio.",
        "icon": "🐹"
    },
    {
        "id": "Oh_Mummy_1984_Amsoft",
        "title": "Oh Mummy!! (Amstrad CPC)",
        "platform": "Amstrad CPC",
        "category": "computers",
        "license": "Historic Preservation",
        "badge_color": "#0891b2",
        "desc": "The quintessential Amstrad CPC 464 pack-in pyramid maze game.",
        "icon": "🏺"
    },
    {
        "id": "atari_st_Speedball_2_Brutal_Deluxe_1990_Bitmap_Brothers",
        "title": "Speedball 2: Brutal Deluxe (Atari ST 1990)",
        "platform": "Atari ST",
        "category": "computers",
        "license": "Historic Preservation",
        "badge_color": "#b45309",
        "desc": "The Bitmap Brothers' futuristic cyberpunk violent sports game masterpiece.",
        "icon": "🏈"
    }
]

LEGIT_ONLINE_SOURCES = [
    {
        "name": "The Internet Arcade (MAME Coin-Op)",
        "desc": "Thousands of authentic coin-operated arcade cabinets emulated in your browser.",
        "url": "https://archive.org/details/internetarcade",
        "tag": "Arcade Cabinets"
    },
    {
        "name": "Internet Archive MS-DOS Games Library",
        "desc": "Thousands of playable MS-DOS PC games, shareware, and CD-ROM releases.",
        "url": "https://archive.org/details/softwarelibrary_msdos_games",
        "tag": "MS-DOS & PC"
    },
    {
        "name": "ScummVM Official Freeware Games",
        "desc": "Beneath a Steel Sky, Flight of the Amazon Queen, and classics released legally free.",
        "url": "https://www.scummvm.org/games/",
        "tag": "100% Legal Freeware"
    },
    {
        "name": "FreeDOS Software & Games Repository",
        "desc": "Open-source DOS applications, utilities, packages, and games for genuine DOS environments.",
        "url": "https://www.freedos.org/software/",
        "tag": "Open Source DOS"
    },
    {
        "name": "Libregamewiki (Free & Open Source Games)",
        "desc": "Comprehensive directory of 100% free/libre open-source games with source code.",
        "url": "https://libregamewiki.org/",
        "tag": "FLOSS Games"
    },
    {
        "name": "TOSEC Preservation Vault",
        "desc": "The Online Software Encyclopedia master catalog of vintage microcomputer software.",
        "url": "https://archive.org/details/tosec",
        "tag": "Preservation Catalog"
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
    Provides complete multi-folder local ROM & ISO sourcing ("Play Anything"),
    instant 1-click downloads from legitimate online sources, and hardware/emulator tuning.
    """
    play_dosbox_requested = pyqtSignal(str, str) # identifier, display_title
    inspect_item_requested = pyqtSignal(str) # identifier
    browse_retro_requested = pyqtSignal()
    download_requested = pyqtSignal(list, str) # files, identifier

    def __init__(self, parent=None):
        super().__init__(parent)
        self.local_games: List[dict] = []
        self._current_filter_platform: Optional[str] = None
        self._current_online_category: Optional[str] = None
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

        canvas = QWidget()
        canvas_layout = QVBoxLayout(canvas)
        canvas_layout.setContentsMargins(24, 20, 24, 20)
        canvas_layout.setSpacing(18)

        # --- Top Hero Banner ---
        hero_card = QFrame()
        hero_card.setObjectName("articleCard")
        hero_layout = QVBoxLayout(hero_card)
        hero_layout.setContentsMargins(22, 18, 22, 18)
        hero_layout.setSpacing(12)

        top_row = QHBoxLayout()
        top_row.setSpacing(14)

        icon_lbl = QLabel("🕹️")
        icon_lbl.setStyleSheet("font-size: 38px;")
        top_row.addWidget(icon_lbl)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        title_lbl = QLabel("DOSBox Retro Arcade & Universal Game Station")
        title_lbl.setStyleSheet("font-size: 22px; font-weight: 800; color: #ffffff;")
        info_layout.addWidget(title_lbl)

        sub_lbl = QLabel(
            "Play Anything: Launch MS-DOS games, CD-ROM ISOs, CUE/BIN disc images, Arcade MAME ROMs, "
            "Atari ST, and Amiga disks directly from your hard drives or stream instantly from verified online repositories."
        )
        sub_lbl.setStyleSheet("font-size: 13px; color: #a1a1aa;")
        sub_lbl.setWordWrap(True)
        info_layout.addWidget(sub_lbl)
        top_row.addLayout(info_layout, stretch=1)
        hero_layout.addLayout(top_row)

        # Emulator Status Quick Bar (DOSBox & MAME Arcade)
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

        # --- Tabbed Content Sections: Local Library, Online Legit Vault, Emulators & Controls ---
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #27272a;
                background-color: #121214;
                border-radius: 8px;
            }
            QTabBar::tab {
                background-color: #18181b;
                color: #a1a1aa;
                font-size: 13px;
                font-weight: 700;
                padding: 10px 20px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background-color: #27272a;
                color: #38bdf8;
                border-bottom: 2px solid #38bdf8;
            }
        """)

        # Tab 1: Local Library & Multi-Folder Sourcing
        self.tab_local = QWidget()
        self._init_local_library_tab(self.tab_local)
        self.tab_widget.addTab(self.tab_local, "💾  My Games & ROMs (Local Library)")

        # Tab 2: Legit Online Game Vault & Multi-Source Downloader
        self.tab_online = QWidget()
        self._init_online_vault_tab(self.tab_online)
        self.tab_widget.addTab(self.tab_online, "🌐  Online Legit Game Vault & Downloader")

        # Tab 3: Hardware, Emulators & Controller Guide
        self.tab_controls = QWidget()
        self._init_controls_guide_tab(self.tab_controls)
        self.tab_widget.addTab(self.tab_controls, "🎮  Emulators & Controller Guide")

        canvas_layout.addWidget(self.tab_widget)

        self.scroll_area.setWidget(canvas)
        main_layout.addWidget(self.scroll_area, stretch=1)

    # =========================================================================
    # TAB 1: LOCAL GAMES LIBRARY & MULTI-FOLDER SOURCING
    # =========================================================================
    def _init_local_library_tab(self, parent: QWidget):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        # Sourcing & Actions Toolbar
        bar_layout = QHBoxLayout()
        bar_layout.setSpacing(8)

        self.btn_load_file = QPushButton("📁 Load Any Game / ISO / ROM...")
        self.btn_load_file.setObjectName("primaryBtn")
        self.btn_load_file.setStyleSheet("font-size: 12px; font-weight: 700; padding: 7px 14px;")
        self.btn_load_file.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_load_file.clicked.connect(self._on_pick_local_game)
        bar_layout.addWidget(self.btn_load_file)

        self.btn_add_source_folder = QPushButton("➕ Add ROM / Game Folder...")
        self.btn_add_source_folder.setStyleSheet("font-size: 12px; font-weight: 600; padding: 7px 12px;")
        self.btn_add_source_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_source_folder.clicked.connect(self._on_add_source_folder)
        bar_layout.addWidget(self.btn_add_source_folder)

        self.btn_manage_folders = QPushButton("📂 Sourced Directories")
        self.btn_manage_folders.setStyleSheet("font-size: 12px; font-weight: 600; padding: 7px 12px;")
        self.btn_manage_folders.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_manage_folders.clicked.connect(self._show_sourced_folders_dialog)
        bar_layout.addWidget(self.btn_manage_folders)

        # Backwards compatibility aliases
        self.btn_load_pc = self.btn_load_file
        self.btn_open_folder = self.btn_manage_folders

        bar_layout.addStretch(1)

        self.search_filter = QLineEdit()
        self.search_filter.setPlaceholderText("🔍 Filter games by title, format (.iso, .st), or platform...")
        self.search_filter.setFixedWidth(280)
        self.search_filter.textChanged.connect(self._apply_local_filters)
        bar_layout.addWidget(self.search_filter)

        btn_rescan = QPushButton("🔄 Rescan All")
        btn_rescan.setFixedWidth(95)
        btn_rescan.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_rescan.clicked.connect(self.scan_local_games)
        bar_layout.addWidget(btn_rescan)

        layout.addLayout(bar_layout)

        # Platform Filter Pills Row
        pills_layout = QHBoxLayout()
        pills_layout.setSpacing(6)

        lbl_filter = QLabel("Quick Filter:")
        lbl_filter.setStyleSheet("font-size: 11px; font-weight: 700; color: #a1a1aa;")
        pills_layout.addWidget(lbl_filter)

        self.platform_pills_group = QButtonGroup(self)
        self.platform_pills_group.setExclusive(True)

        platform_filters = [
            ("All", None),
            ("🎮 MS-DOS & PC", "MS-DOS"),
            ("🕹️ Arcade (MAME)", "Arcade"),
            ("🖥️ Atari ST", "Atari ST"),
            ("🐬 Amiga", "Amiga"),
            ("📼 C64 & 8-Bit", "Commodore 64"),
            ("💿 ISOs & Disc Images", "ISO"),
        ]

        for idx, (label, val) in enumerate(platform_filters):
            btn = QPushButton(label)
            btn.setObjectName("categoryPill")
            btn.setCheckable(True)
            if idx == 0:
                btn.setChecked(True)
            btn.clicked.connect(lambda _, v=val: self._on_filter_platform_clicked(v))
            self.platform_pills_group.addButton(btn, idx)
            pills_layout.addWidget(btn)

        pills_layout.addStretch(1)
        layout.addLayout(pills_layout)

        # Sourced directories summary label
        self.sec_sub = QLabel("Scanning your download repository and sourced game folders...")
        self.sec_sub.setStyleSheet("font-size: 11.5px; color: #a1a1aa;")
        layout.addWidget(self.sec_sub)

        # Local Games Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Game / ROM File", "Platform", "Format", "Size & Location", "Actions"])
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
        self.table.setMinimumHeight(280)
        layout.addWidget(self.table)

    # =========================================================================
    # TAB 2: ONLINE LEGIT GAME VAULT & MULTI-SOURCE DOWNLOADER
    # =========================================================================
    def _init_online_vault_tab(self, parent: QWidget):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        # Header description
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        info_box = QVBoxLayout()
        info_box.setSpacing(2)
        v_title = QLabel("🌐 Verified Legit Online Games & Multi-Source Repositories")
        v_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #38bdf8;")
        info_box.addWidget(v_title)

        v_sub = QLabel("Stream and play instantly or download directly into your local library from legitimate, copyright-compliant repositories.")
        v_sub.setStyleSheet("font-size: 12px; color: #a1a1aa;")
        info_box.addWidget(v_sub)
        top_bar.addLayout(info_box, stretch=1)

        self.online_search = QLineEdit()
        self.online_search.setPlaceholderText("🔍 Search online games catalog...")
        self.online_search.setFixedWidth(240)
        self.online_search.textChanged.connect(self._filter_online_games)
        top_bar.addWidget(self.online_search)

        layout.addLayout(top_bar)

        # Category Filter Pills
        cat_pills = QHBoxLayout()
        cat_pills.setSpacing(6)

        lbl_cat = QLabel("Category:")
        lbl_cat.setStyleSheet("font-size: 11px; font-weight: 700; color: #a1a1aa;")
        cat_pills.addWidget(lbl_cat)

        self.online_cat_group = QButtonGroup(self)
        self.online_cat_group.setExclusive(True)

        categories = [
            ("🌟 All Legit Classics", None),
            ("🕹️ Coin-Op Arcade", "arcade"),
            ("💾 MS-DOS Legends", "dos"),
            ("🧭 ScummVM Freeware", "scummvm"),
            ("🖥️ Atari ST & Amiga", "computers"),
        ]

        for idx, (label, key) in enumerate(categories):
            btn = QPushButton(label)
            btn.setObjectName("categoryPill")
            btn.setCheckable(True)
            if idx == 0:
                btn.setChecked(True)
            btn.clicked.connect(lambda _, k=key: self._on_filter_online_category(k))
            self.online_cat_group.addButton(btn, idx)
            cat_pills.addWidget(btn)

        cat_pills.addStretch(1)
        layout.addLayout(cat_pills)

        # Online Games Grid Scroll Container
        self.online_cards_container = QWidget()
        self.online_cards_layout = QHBoxLayout(self.online_cards_container)
        self.online_cards_layout.setContentsMargins(0, 4, 0, 4)
        self.online_cards_layout.setSpacing(12)

        self.col_left = QVBoxLayout()
        self.col_left.setSpacing(10)
        self.col_right = QVBoxLayout()
        self.col_right.setSpacing(10)

        self.online_cards_layout.addLayout(self.col_left, stretch=1)
        self.online_cards_layout.addLayout(self.col_right, stretch=1)

        layout.addWidget(self.online_cards_container)
        self._populate_online_cards(ONLINE_LEGIT_GAMES)

        # Legitimate External Sources Bar
        sources_card = QFrame()
        sources_card.setStyleSheet("""
            QFrame {
                background-color: #141417;
                border: 1px solid #27272a;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        s_layout = QVBoxLayout(sources_card)
        s_layout.setSpacing(8)

        s_title = QLabel("📚 Multi-Source Legitimate Preservation Directories & Downloads")
        s_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #f59e0b;")
        s_layout.addWidget(s_title)

        s_grid = QHBoxLayout()
        s_grid.setSpacing(10)

        for src in LEGIT_ONLINE_SOURCES:
            btn_src = QPushButton(f"🌐 {src['name']}")
            btn_src.setToolTip(f"{src['desc']}\nTag: {src['tag']}")
            btn_src.setStyleSheet("font-size: 11px; padding: 6px 10px; text-align: left;")
            btn_src.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_src.clicked.connect(lambda _, u=src["url"]: open_file(u))
            s_grid.addWidget(btn_src)

        s_layout.addLayout(s_grid)
        layout.addWidget(sources_card)

    # =========================================================================
    # TAB 3: EMULATOR ENGINE & CONTROLS GUIDE
    # =========================================================================
    def _init_controls_guide_tab(self, parent: QWidget):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        guide_card = QFrame()
        guide_card.setObjectName("articleCard")
        guide_layout = QVBoxLayout(guide_card)
        guide_layout.setContentsMargins(20, 18, 20, 18)
        guide_layout.setSpacing(14)

        guide_title = QLabel("⌨️ Hardware Emulation, Wireless Gamepad & Controller Setup Guide")
        guide_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #38bdf8;")
        guide_layout.addWidget(guide_title)

        guide_html = """
        <div style="font-size: 12.5px; color: #d4d4d8; line-height: 1.6;">
            <div style="margin-bottom: 12px;">
                <b style="color: #f59e0b; font-size: 14px;">🕹️ MAME Arcade Cabinets (Coin-Op Controls):</b><br>
                <b>• Tab:</b> In-Game Master Menu — Remap buttons for this game or all games, calibrate sticks, configure dips.<br>
                <b>• 5 / 6:</b> Insert Coin (Player 1 / Player 2).<br>
                <b>• 1 / 2:</b> Start Game (Player 1 / Player 2).<br>
                <b>• Arrow Keys / Gamepad Stick:</b> 8-Way directional joystick movement.<br>
                <b>• Ctrl / Alt / Space (or Gamepad A / B / X):</b> Primary arcade punch/kick/fire buttons.<br>
                <b>• Mouse & Trackball:</b> Automatically mapped for spinners (e.g. <i>Arkanoid</i>), trackballs (<i>Centipede</i>), and lightguns.<br>
                <b>• Wireless Gamepads:</b> Native Windows Hybrid input provider supports Xbox, PlayStation, and 8BitDo Bluetooth gamepads without third-party drivers.<br>
                <b>• Alt + Enter:</b> Toggle Fullscreen &nbsp;|&nbsp; <b>Esc:</b> Exit Arcade Machine.
            </div>

            <div style="border-top: 1px solid #27272a; padding-top: 10px; margin-bottom: 12px;">
                <b style="color: #38bdf8; font-size: 14px;">💾 DOSBox & CD-ROM ISO Emulation:</b><br>
                <b>• ISO & CUE/BIN Mounting:</b> ArchiveVault mounts disc images automatically (e.g. <code>imgmount d "game.iso" -t iso</code>) with CD audio support.<br>
                <b>• Mouse Locking:</b> Click inside DOSBox to capture mouse. Press <b>Ctrl + F10</b> at any time to release mouse back to desktop.<br>
                <b>• High-Definition Scaler:</b> Custom 1280x960 4:3 aspect-corrected output (<code>normal3x</code> or <code>openglnb</code>) eliminates pixel distortion.<br>
                <b>• Speed / CPU Turbo:</b> Press <b>Ctrl + F11</b> to decrease CPU cycles or <b>Ctrl + F12</b> to increase cycles.<br>
                <b>• Sound Cards:</b> Emulates Sound Blaster 16 (IRQ 7, DMA 1, Port 220), Sound Blaster Pro, and Intelligent MPU-401 General MIDI / Roland MT-32.<br>
                <b>• In-Game Joystick Activation:</b> Some classic games (like <i>Prince of Persia</i>) start in keyboard mode; press <b>Ctrl + J</b> in-game to switch to Joystick!
            </div>

            <div style="border-top: 1px solid #27272a; padding-top: 10px;">
                <b style="color: #a855f7; font-size: 14px;">🚀 LaunchBox & Microcomputer Frontends:</b><br>
                <b>• LaunchBox Integration:</b> Games can be sent directly to LaunchBox for advanced per-game custom emulator cores (Hatari for Atari ST, WinUAE for Amiga, VICE for C64).<br>
                <b>• 1-Click Portable MAME:</b> ArchiveVault can download and install official portable MAME with full Windows joystick configuration in 1 click.
            </div>
        </div>
        """
        guide_lbl = QLabel(guide_html)
        guide_lbl.setTextFormat(Qt.TextFormat.RichText)
        guide_layout.addWidget(guide_lbl)

        layout.addWidget(guide_card)
        layout.addStretch(1)

    # =========================================================================
    # SOURCED FOLDERS MANAGEMENT
    # =========================================================================
    def _on_add_source_folder(self):
        """Allow user to pick any folder containing games/ISOs/ROMs on their PC."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Game, ISO, or ROM Folder to Source",
            settings.download_dir
        )
        if folder and os.path.exists(folder):
            norm_folder = os.path.normpath(folder)
            if norm_folder not in settings.game_source_dirs and norm_folder != os.path.normpath(settings.download_dir):
                settings.game_source_dirs.append(norm_folder)
                settings.save()
                QMessageBox.information(
                    self,
                    "Folder Sourced",
                    f"Successfully added game directory:\n{norm_folder}\n\nRescanning library now!"
                )
                self.scan_local_games()
            else:
                QMessageBox.information(self, "Already Sourced", "This directory is already in your active game sources.")

    def _show_sourced_folders_dialog(self):
        """Dialog to view and remove configured game source folders."""
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Configured Game & ROM Source Directories")
        dlg.setIcon(QMessageBox.Icon.Information)

        sources = [f"📁 [Primary] {settings.download_dir}"]
        for d in settings.game_source_dirs:
            sources.append(f"📁 {d}")

        text = (
            "<b>Active Game & ROM Source Directories:</b><br><br>" +
            "<br>".join(sources) +
            "<br><br>ArchiveVault scans all of these locations recursively for playable retro games and disc images."
        )
        dlg.setText(text)
        btn_open = dlg.addButton("Open Primary Folder", QMessageBox.ButtonRole.ActionRole)
        btn_clear_custom = dlg.addButton("Clear Custom Folders", QMessageBox.ButtonRole.DestructiveRole)
        btn_close = dlg.addButton("Close", QMessageBox.ButtonRole.RejectRole)

        dlg.exec()
        if dlg.clickedButton() == btn_open:
            open_containing_folder(settings.download_dir)
        elif dlg.clickedButton() == btn_clear_custom:
            settings.game_source_dirs = []
            settings.save()
            self.scan_local_games()

    # =========================================================================
    # SCANNING & LOCAL GAMES
    # =========================================================================
    def scan_local_games(self):
        """Scan primary download directory AND all custom sourced folders for game files."""
        self.local_games.clear()
        scan_dirs = [settings.download_dir] + list(settings.game_source_dirs)

        # Check standard common game locations if they exist on the user's PC
        user_home = os.path.expanduser("~")
        common_candidates = [
            os.path.join(user_home, "LaunchBox", "Games"),
            r"C:\Games",
            r"D:\Games",
            r"D:\ROMs",
            os.path.join(user_home, "RetroArch", "downloads"),
        ]
        for c in common_candidates:
            if os.path.exists(c) and c not in scan_dirs:
                scan_dirs.append(c)

        found = []
        max_scan = 1000
        count = 0

        for s_dir in scan_dirs:
            if not os.path.exists(s_dir):
                continue
            for root, dirs, files in os.walk(s_dir):
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
                        platform_name = p_info["name"]

                        # Disc image flag
                        ext_upper = os.path.splitext(f)[1].upper()
                        is_disc = ext_upper in ('.ISO', '.BIN', '.CUE', '.IMG', '.VHD')

                        found.append({
                            "filename": f,
                            "path": full_p,
                            "source_dir": s_dir,
                            "rel_dir": os.path.relpath(root, s_dir),
                            "size": sz,
                            "platform": platform_name,
                            "is_disc": is_disc,
                            "badge_color": p_info.get("badge_color", "#065f46"),
                            "ext": ext_upper
                        })
                        count += 1
                        if count >= max_scan:
                            break
                if count >= max_scan:
                    break
            if count >= max_scan:
                break

        found.sort(key=lambda x: x["filename"].lower())
        self.local_games = found
        self._apply_local_filters()

        dirs_count = len([d for d in scan_dirs if os.path.exists(d)])
        self.sec_sub.setText(
            f"Found {len(found):,} game(s), ROMs, and disc images across {dirs_count} sourced directory location(s)."
        )

    def _on_filter_platform_clicked(self, platform: Optional[str]):
        self._current_filter_platform = platform
        self._apply_local_filters()

    def _apply_local_filters(self):
        query = self.search_filter.text().strip().lower()
        p_filter = self._current_filter_platform

        filtered = []
        for g in self.local_games:
            # Platform filter
            if p_filter:
                if p_filter == "ISO" and not g["is_disc"]:
                    continue
                elif p_filter != "ISO" and p_filter.lower() not in g["platform"].lower():
                    continue

            # Text query
            if query:
                if (query not in g["filename"].lower() and
                    query not in g["platform"].lower() and
                    query not in g["ext"].lower() and
                    query not in g["rel_dir"].lower()):
                    continue

            filtered.append(g)

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

            loc_text = f"📁 {os.path.basename(g['source_dir'])}"
            if g["rel_dir"] and g["rel_dir"] != ".":
                loc_text += f" / {g['rel_dir']}"
            dir_lbl = QLabel(loc_text)
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

    # =========================================================================
    # ONLINE CARDS & MULTI-SOURCE DOWNLOADS
    # =========================================================================
    def _on_filter_online_category(self, key: Optional[str]):
        self._current_online_category = key
        self._filter_online_games()

    def _filter_online_games(self):
        query = self.online_search.text().strip().lower()
        cat = self._current_online_category

        filtered = []
        for g in ONLINE_LEGIT_GAMES:
            if cat and g["category"] != cat:
                continue
            if query:
                if (query not in g["title"].lower() and
                    query not in g["platform"].lower() and
                    query not in g["desc"].lower() and
                    query not in g["license"].lower()):
                    continue
            filtered.append(g)

        self._populate_online_cards(filtered)

    def _populate_online_cards(self, games: List[dict]):
        # Clear existing
        while self.col_left.count():
            item = self.col_left.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        while self.col_right.count():
            item = self.col_right.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, classic in enumerate(games):
            card = self._create_online_card(classic)
            if i % 2 == 0:
                self.col_left.addWidget(card)
            else:
                self.col_right.addWidget(card)

        self.col_left.addStretch(1)
        self.col_right.addStretch(1)

    def _create_online_card(self, classic: dict) -> QFrame:
        card = QFrame()
        card.setObjectName("curatedCard")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(14, 10, 14, 10)
        card_layout.setSpacing(12)

        icon_lbl = QLabel(classic.get("icon", "🕹️"))
        icon_lbl.setStyleSheet("font-size: 26px;")
        card_layout.addWidget(icon_lbl)

        info = QVBoxLayout()
        info.setSpacing(3)

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

        lic_badge = QLabel(classic.get("license", "Preservation"))
        lic_badge.setStyleSheet("""
            background-color: #1e293b;
            color: #94a3b8;
            font-size: 9px;
            font-weight: 600;
            padding: 2px 6px;
            border-radius: 4px;
            border: 1px solid #334155;
        """)
        t_row.addWidget(lic_badge)

        t_row.addStretch(1)
        info.addLayout(t_row)

        d_lbl = QLabel(classic["desc"])
        d_lbl.setStyleSheet("font-size: 11px; color: #a1a1aa;")
        d_lbl.setWordWrap(True)
        info.addWidget(d_lbl)

        card_layout.addLayout(info, stretch=1)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(6)

        play_btn = QPushButton("▶ Play")
        play_btn.setObjectName("primaryBtn")
        play_btn.setFixedSize(70, 30)
        play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        play_btn.clicked.connect(lambda _, c=classic: self.play_dosbox_requested.emit(c["id"], c["title"]))
        btn_box.addWidget(play_btn)

        dossier_btn = QPushButton("📖 Dossier")
        dossier_btn.setToolTip("View full Internet Archive Subject Dossier & Files")
        dossier_btn.setFixedSize(80, 30)
        dossier_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        dossier_btn.clicked.connect(lambda _, c=classic: self.inspect_item_requested.emit(c["id"]))
        btn_box.addWidget(dossier_btn)

        card_layout.addLayout(btn_box)
        return card

    # =========================================================================
    # LAUNCHERS ("PLAY ANYTHING")
    # =========================================================================
    def _on_pick_local_game(self):
        """Prompt user to pick any game file, disc image, or ROM from hard drive."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Game, Disc Image, or ROM from Hard Drive",
            settings.download_dir,
            "Playable Games & Images (*.iso *.bin *.cue *.img *.vhd *.zip *.exe *.com *.bat *.st *.msa *.adf *.ipf *.dsk *.d64 *.tap *.7z *.smc *.nes *.gen);;All Files (*.*)"
        )
        if file_path:
            self._launch_game_file(file_path)

    def _launch_game_file(self, file_path: str):
        """Launch any game file, mounting CD-ROM ISOs, MAME arcade ROMs, or microcomputer disks."""
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

        # 2. MICROCOMPUTERS & CONSOLES (Atari ST, Amiga, C64, ZX Spectrum, Amstrad, etc.)
        if platform_name in ("Atari ST", "Atari 8-bit", "Atari Console", "Atari", "Amstrad CPC", "ZX Spectrum", "Commodore 64", "Amiga", "Apple II", "Console"):
            self._handle_non_dos_microcomputer_launch(file_path, fname, platform_name)
            return

        # 3. CD-ROM ISOS & DISC IMAGES (.iso, .cue, .bin, .img, .vhd)
        if ext in ('.iso', '.cue', '.bin', '.img', '.vhd'):
            dosbox_exe = get_dosbox_path()
            if dosbox_exe:
                reply = QMessageBox.question(
                    self,
                    "Mount & Launch Disc Image in DOSBox",
                    f"Mount '{fname}' as CD-ROM (Drive D:) in high-resolution scaled DOSBox?\n\n"
                    "ArchiveVault will configure CD audio, mount the directory, and boot DOSBox automatically.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
                )
                if reply == QMessageBox.StandardButton.Yes:
                    launch_local_dosbox(file_path)
                elif reply == QMessageBox.StandardButton.No:
                    open_containing_folder(file_path)
            else:
                open_file(file_path)
            return

        # 4. DIRECT DOS EXECUTABLES (.exe, .com, .bat, .conf)
        if ext in ('.exe', '.com', '.bat', '.conf'):
            dosbox_exe = get_dosbox_path()
            if dosbox_exe:
                success = launch_local_dosbox(file_path)
                if not success:
                    open_file(file_path)
            else:
                open_file(file_path)
            return

        # 5. DOS ZIP ARCHIVES / OTHER ARCHIVES
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
            </div>
            """
        elif verified_arcade:
            ia_id, ia_title = verified_arcade
            html_text = f"""
            <div style='font-size: 13px; line-height: 1.5;'>
                <h3 style='margin: 0 0 8px 0; color: #f43f5e;'>🕹️ Arcade Cabinet ROM: {ia_title}</h3>
                <p><b>{fname}</b> matches verified Internet Arcade game <b>{ia_title}</b>!</p>
                <p style='color: #a1a1aa;'>
                    Play this arcade classic directly inside ArchiveVault via WebAssembly MAME, or install standalone MAME for offline play.
                </p>
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
        """Handle Atari ST, Amiga, C64, ZX Spectrum, Amstrad CPC files."""
        lb_exe = get_launchbox_path()
        has_lb = bool(lb_exe and os.path.exists(lb_exe))

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(f"{platform_name} Game Detected")
        msg_box.setIcon(QMessageBox.Icon.Information)

        html_text = f"""
        <div style='font-size: 13px; line-height: 1.5;'>
            <h3 style='margin: 0 0 8px 0; color: #38bdf8;'>💾 {platform_name} Software: {fname}</h3>
            <p><b>{fname}</b> is an authentic <b>{platform_name}</b> disk/tape image.</p>
            <p style='color: #a1a1aa;'>
                • <b>Platform Architecture:</b> {platform_name} runs on specialized microcomputer hardware (Motorola 68000 / Z80 / 6502).<br>
                • <b>How to play:</b> Stream it directly through ArchiveVault's built-in WebAssembly theater, or launch via LaunchBox with your retro core (Hatari, Steem, WinUAE, RetroArch).
            </p>
        </div>
        """
        msg_box.setText(html_text)

        btn_inapp = msg_box.addButton("🌐 Play in ArchiveVault Theater", QMessageBox.ButtonRole.ActionRole)
        btn_lb = msg_box.addButton("🚀 Open in LaunchBox", QMessageBox.ButtonRole.ActionRole) if has_lb else None
        btn_open = msg_box.addButton("📂 Open File / Folder", QMessageBox.ButtonRole.ActionRole)
        btn_cancel = msg_box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)

        msg_box.exec()
        clicked = msg_box.clickedButton()

        if clicked == btn_inapp:
            stem = os.path.splitext(fname)[0]
            ident = f"{platform_name.lower().replace(' ', '_')}_{stem}"
            self.play_dosbox_requested.emit(ident, f"{platform_name}: {stem}")
        elif has_lb and clicked == btn_lb:
            launch_launchbox(file_path)
        elif clicked == btn_open:
            open_containing_folder(file_path)

    # =========================================================================
    # CONFIGURATION & STATUS
    # =========================================================================
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
                f"🎮 <b>DOSBox:</b> <span style='color: #4ade80;'>Ready ({origin_desc} • HD 1280x960 4:3)</span> &nbsp;•&nbsp; <code>{dosbox_path}</code>"
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
