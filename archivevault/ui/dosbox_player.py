import ctypes
from ctypes import wintypes
import json
import math
import os
import sys
import time
import webbrowser
from typing import Optional

# Ensure Chromium autoplay and audio features are enabled before WebEngine initializes
os.environ.setdefault(
    "QTWEBENGINE_CHROMIUM_FLAGS",
    "--autoplay-policy=no-user-gesture-required --enable-features=SharedArrayBuffer"
)
from PyQt6.QtCore import QSettings, QSize, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon, QKeySequence, QShortcut
from PyQt6.QtWebEngineCore import (
    QWebEngineFullScreenRequest,
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineScript,
    QWebEngineSettings,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

def detect_retro_platform(identifier: str) -> dict:
    id_lower = identifier.lower()

    # Asset / Non-playable theme check
    if any(k in id_lower for k in ("emulationstation-assets", "theme", "artwork", "media", "video_snap", "marquee", "wheel")):
        return {
            "name": "Media / Assets",
            "badge": "MEDIA",
            "badge_color": "#475569",
            "default_cmd": "",
            "tip": "Artwork / UI assets for frontends and themes."
        }

    # Atari ST (Motorola 68000 16/32-bit computer: .st, .msa, .stx, .dim)
    if id_lower.endswith((".st", ".msa", ".stx", ".dim")) or any(k in id_lower for k in ("atarist", "atari_st", "atari-st", "hatari", "steem", "tos_")):
        return {
            "name": "Atari ST",
            "badge": "ATARI ST",
            "badge_color": "#d97706",
            "default_cmd": "",
            "tip": "Atari ST: 16/32-bit Motorola 68000 GEM desktop / TOS floppy auto-boot."
        }

    # Atari 8-Bit (400 / 800 / XL / XE: .atr, .xfd, .atx)
    if id_lower.endswith((".atr", ".xfd", ".atx")) or any(k in id_lower for k in ("atari800", "atari_800", "atari-800")):
        return {
            "name": "Atari 8-bit",
            "badge": "ATARI 8-BIT",
            "badge_color": "#b45309",
            "default_cmd": "",
            "tip": "Atari 8-bit: Auto-booting disk image."
        }

    # Atari Consoles (2600 / 7800 / Jaguar / Lynx)
    if id_lower.endswith((".a26", ".a78")) or any(k in id_lower for k in ("a2600", "a7800", "atari2600", "atari7800", "jaguar", "lynx")):
        return {
            "name": "Atari Console",
            "badge": "ATARI",
            "badge_color": "#92400e",
            "default_cmd": "",
            "tip": "Atari Console: Press F2 for Game Reset / Start."
        }

    # Amstrad CPC
    if id_lower.endswith((".dsk", ".cpr")) or any(k in id_lower for k in ("cpc", "amstrad", "6128", "464", "664")):
        default_cmd = "RUN\"GOBLINS" if "goblins" in id_lower else "RUN\"DISC"
        return {
            "name": "Amstrad CPC",
            "badge": "AMSTRAD CPC",
            "badge_color": "#0891b2",
            "default_cmd": default_cmd,
            "tip": "Amstrad CPC: Click screen & type RUN\"<NAME> (or CAT for disk files) then press Enter!"
        }

    # ZX Spectrum
    if id_lower.endswith((".tap", ".tzx", ".z80", ".sna")) or any(k in id_lower for k in ("zx_", "spectrum", "sinclair")):
        return {
            "name": "ZX Spectrum",
            "badge": "ZX SPECTRUM",
            "badge_color": "#d97706",
            "default_cmd": "LOAD \"\"",
            "tip": "ZX Spectrum: Press J for LOAD, then Symbol Shift + P twice for \"\" and Enter!"
        }

    # Commodore 64
    if id_lower.endswith((".d64", ".t64", ".crt", ".prg", ".g64")) or any(k in id_lower for k in ("c64", "commodore", "vic20", "plus-4")):
        return {
            "name": "Commodore 64",
            "badge": "C64",
            "badge_color": "#4f46e5",
            "default_cmd": "LOAD \"*\",8,1",
            "tip": "C64: Click screen & type LOAD \"*\",8,1 then Enter, then RUN!"
        }

    # Commodore Amiga
    if id_lower.endswith((".adf", ".ipf", ".hdf")) or any(k in id_lower for k in ("amiga", "a500", "a1200")):
        return {
            "name": "Amiga",
            "badge": "AMIGA",
            "badge_color": "#ea580c",
            "default_cmd": "",
            "tip": "Amiga: Insert floppy or let Workbench autoboot."
        }

    # Arcade (MAME / FBNeo)
    if any(k in id_lower for k in ("arcade", "mame", "fbn", "fbneo", "neogeo", "capcom", "cps1", "cps2", "cps3")):
        return {
            "name": "Arcade",
            "badge": "ARCADE",
            "badge_color": "#dc2626",
            "default_cmd": "",
            "tip": "Arcade: Press 5 or 6 to insert coins, 1 or 2 for Player Start!"
        }

    # Consoles (SNES, NES, Genesis, Game Boy, GBA, etc.)
    if id_lower.endswith((".smc", ".sfc", ".nes", ".gen", ".md", ".smd", ".pbp", ".gba", ".gbc", ".gb", ".n64", ".z64")) or any(k in id_lower for k in ("snes", "super_nintendo", "sfc", "nes", "famico", "n64", "gba", "gameboy", "gbc", "genesis", "megadrive", "hearto")):
        p_name = "Sega Genesis" if any(k in id_lower for k in ("genesis", "megadrive", "gen", ".md", ".smd")) else "Console"
        return {
            "name": p_name,
            "badge": p_name.upper(),
            "badge_color": "#7c3aed",
            "default_cmd": "",
            "tip": f"{p_name}: Launch with RetroArch or in-app theater."
        }

    # CD-ROM & Disc Images (.cue, .bin, .iso, .chd, .img, .vhd)
    if id_lower.endswith((".cue", ".bin", ".iso", ".chd", ".img", ".vhd")):
        # 1. PlayStation 1
        if any(k in id_lower for k in ("psx", "ps1", "playstation", "sony", "slus", "sles", "scus", "sces")):
            return {
                "name": "PlayStation",
                "badge": "PS1",
                "badge_color": "#3b82f6",
                "default_cmd": "",
                "tip": "Sony PlayStation: Launch with RetroArch (PCSX ReARMed) or In-App."
            }
        # 2. Sega CD / Saturn / Dreamcast / Genesis (.bin)
        if any(k in id_lower for k in ("genesis", "megadrive", "sega", "segacd", "saturn", "dreamcast", "sonic")):
            return {
                "name": "Sega Genesis",
                "badge": "SEGA",
                "badge_color": "#2563eb",
                "default_cmd": "",
                "tip": "Sega Mega Drive / CD: Launch with RetroArch (Genesis Plus GX / Flycast)."
            }
        # 3. Atari 2600 (.bin cartridge dumps)
        if any(k in id_lower for k in ("a2600", "2600", "atari2600", "stella")):
            return {
                "name": "Atari Console",
                "badge": "ATARI 2600",
                "badge_color": "#92400e",
                "default_cmd": "",
                "tip": "Atari 2600: Launch with RetroArch (Stella) or In-App."
            }
        # 4. Explicit MS-DOS PC CD-ROM
        if any(k in id_lower for k in ("msdos", "dos_", "dosbox", "pc_", "ibm", "windows3x", "win3x", "win95")):
            return {
                "name": "MS-DOS (CD-ROM)",
                "badge": "MS-DOS CD",
                "badge_color": "#065f46",
                "default_cmd": "",
                "tip": "MS-DOS CD-ROM: Auto-mounted in DOSBox HD / RetroArch (DOSBox Pure)."
            }
        # 5. General Optical Disc Image (.bin/.cue/.iso/.chd)
        return {
            "name": "Disc Image (CD-ROM)",
            "badge": "DISC / CD",
            "badge_color": "#8b5cf6",
            "default_cmd": "",
            "tip": "Optical Disc Image: Launch with RetroArch or mount in DOSBox."
        }

    # Generic Atari fallback
    if "atari" in id_lower:
        return {
            "name": "Atari",
            "badge": "ATARI",
            "badge_color": "#b45309",
            "default_cmd": "",
            "tip": "Atari: Press F2 for Game Reset / Start."
        }

    # Apple II
    if any(k in id_lower for k in ("apple2", "appleii", "apple_")):
        return {
            "name": "Apple II",
            "badge": "APPLE II",
            "badge_color": "#15803d",
            "default_cmd": "",
            "tip": "Apple II: Auto-booting floppy."
        }
    return {
        "name": "MS-DOS",
        "badge": "MS-DOS",
        "badge_color": "#065f46",
        "default_cmd": "",
        "tip": "DOSBox: Click to lock mouse, use keyboard or controller to play!"
    }

class XINPUT_STATE(ctypes.Structure):
    _fields_ = [
        ('dwPacketNumber', wintypes.DWORD),
        ('wButtons', wintypes.WORD),
        ('bLeftTrigger', wintypes.BYTE),
        ('bRightTrigger', wintypes.BYTE),
        ('sThumbLX', wintypes.SHORT),
        ('sThumbLY', wintypes.SHORT),
        ('sThumbRX', wintypes.SHORT),
        ('sThumbRY', wintypes.SHORT),
    ]

class GamepadPoller:
    """Zero-dependency Windows controller driver supporting XInput with zero latency."""
    def __init__(self):
        self.xi = None
        for dll in ["xinput1_4.dll", "xinput1_3.dll", "xinput9_1_0.dll"]:
            try:
                self.xi = ctypes.windll.LoadLibrary(dll)
                break
            except Exception:
                pass
        self.connected = False
        self.controller_name = "None"
        self.last_keys = set()
        self.key_press_times = {}
        self.last_repeat_times = {}
        self._was_rest = True

    def poll(self):
        now = time.time()
        connected = False
        name = "None"
        axes = [0.0, 0.0, 0.0, 0.0]  # lx, ly, rx, ry
        buttons = [0.0] * 17
        keys = set()
        mdx, mdy = 0, 0
        m_left, m_right = False, False

        # Try XInput (fast, sub-millisecond, non-blocking)
        if self.xi:
            for user_idx in range(4):
                state = XINPUT_STATE()
                if self.xi.XInputGetState(user_idx, ctypes.byref(state)) == 0:
                    connected = True
                    name = f"Wireless/USB Controller (P{user_idx + 1})"
                    btn = state.wButtons

                    def norm(v):
                        return max(-1.0, min(1.0, v / 32767.0))

                    raw_lx = norm(state.sThumbLX)
                    raw_ly = norm(-state.sThumbLY)  # invert Y for HTML5 Gamepad standard
                    raw_rx = norm(state.sThumbRX)
                    raw_ry = norm(-state.sThumbRY)

                    def dz(v, deadzone=0.14):
                        if abs(v) < deadzone:
                            return 0.0
                        return math.copysign((abs(v) - deadzone) / (1.0 - deadzone), v)

                    lx = dz(raw_lx)
                    ly = dz(raw_ly)
                    rx = dz(raw_rx)
                    ry = dz(raw_ry)
                    axes = [round(lx, 3), round(ly, 3), round(rx, 3), round(ry, 3)]

                    lt = state.bLeftTrigger / 255.0
                    rt = state.bRightTrigger / 255.0

                    # 17 HTML5 Standard Gamepad buttons:
                    # 0:A, 1:B, 2:X, 3:Y, 4:LB, 5:RB, 6:LT, 7:RT, 8:Back, 9:Start,
                    # 10:LStick, 11:RStick, 12:Up, 13:Down, 14:Left, 15:Right, 16:Guide
                    buttons[0] = 1.0 if (btn & 0x1000) else 0.0   # A
                    buttons[1] = 1.0 if (btn & 0x2000) else 0.0   # B
                    buttons[2] = 1.0 if (btn & 0x4000) else 0.0   # X
                    buttons[3] = 1.0 if (btn & 0x8000) else 0.0   # Y
                    buttons[4] = 1.0 if (btn & 0x0100) else 0.0   # LB
                    buttons[5] = 1.0 if (btn & 0x0200) else 0.0   # RB
                    buttons[6] = round(lt, 2)                      # LT
                    buttons[7] = round(rt, 2)                      # RT
                    buttons[8] = 1.0 if (btn & 0x0020) else 0.0   # Back
                    buttons[9] = 1.0 if (btn & 0x0010) else 0.0   # Start
                    buttons[10] = 1.0 if (btn & 0x0040) else 0.0  # LStick
                    buttons[11] = 1.0 if (btn & 0x0080) else 0.0  # RStick
                    buttons[12] = 1.0 if (btn & 0x0001) else 0.0  # Up
                    buttons[13] = 1.0 if (btn & 0x0002) else 0.0  # Down
                    buttons[14] = 1.0 if (btn & 0x0004) else 0.0  # Left
                    buttons[15] = 1.0 if (btn & 0x0008) else 0.0  # Right

                    # Virtual Mouse: Right stick controls mouse look / cursor
                    if abs(rx) > 0.01 or abs(ry) > 0.01:
                        speed = 18.0
                        mdx = int(math.copysign((abs(rx) ** 1.6) * speed, rx))
                        mdy = int(math.copysign((abs(ry) ** 1.6) * speed, ry))
                    m_left = bool(buttons[0] > 0.5 or rt > 0.4)
                    m_right = bool(buttons[1] > 0.5 or lt > 0.4)

                    # Retro Keyboard Mapping (D-Pad & Left Stick)
                    if (btn & 0x0001) or ly < -0.35:
                        keys.add(('ArrowUp', 'ArrowUp', 38))
                    if (btn & 0x0002) or ly > 0.35:
                        keys.add(('ArrowDown', 'ArrowDown', 40))
                    if (btn & 0x0004) or lx < -0.35:
                        keys.add(('ArrowLeft', 'ArrowLeft', 37))
                    if (btn & 0x0008) or lx > 0.35:
                        keys.add(('ArrowRight', 'ArrowRight', 39))
                    if btn & 0x1000:
                        keys.add(('Control', 'ControlLeft', 17))
                    if btn & 0x2000:
                        keys.add(('Alt', 'AltLeft', 18))
                    if btn & 0x4000:
                        keys.add((' ', 'Space', 32))
                    if btn & 0x8000:
                        keys.add(('Shift', 'ShiftLeft', 16))
                    if btn & 0x0010:
                        keys.add(('Enter', 'Enter', 13))
                    if btn & 0x0020:
                        keys.add(('Escape', 'Escape', 27))
                    if btn & 0x0100:
                        keys.add(('Tab', 'Tab', 9))
                    if btn & 0x0200:
                        keys.add(('1', 'Digit1', 49))
                    break

        # Typematic repeat calculation
        released_keys = self.last_keys - keys
        for k in released_keys:
            self.key_press_times.pop(k, None)
            self.last_repeat_times.pop(k, None)

        new_keys = keys - self.last_keys
        repeat_keys = set()
        for k in new_keys:
            self.key_press_times[k] = now
            self.last_repeat_times[k] = now

        for k in (keys & self.last_keys):
            first_time = self.key_press_times.get(k, now)
            last_rep = self.last_repeat_times.get(k, now)
            if (now - first_time) >= 0.22 and (now - last_rep) >= 0.05:
                repeat_keys.add(k)
                self.last_repeat_times[k] = now

        self.last_keys = keys

        key_events = []
        for key, code, key_code in new_keys:
            key_events.append(['down', key, code, key_code, False])
        for key, code, key_code in repeat_keys:
            key_events.append(['down', key, code, key_code, True])
        for key, code, key_code in released_keys:
            key_events.append(['up', key, code, key_code, False])

        is_rest = (
            axes == [0.0, 0.0, 0.0, 0.0] and
            all(b == 0.0 for b in buttons) and
            mdx == 0 and mdy == 0 and
            not m_left and not m_right and
            len(key_events) == 0
        )

        changed = False
        if connected != self.connected:
            changed = True
            self.connected = connected
            self.controller_name = name
        elif not is_rest:
            changed = True
            self._was_rest = False
        elif not self._was_rest:
            changed = True
            self._was_rest = True

        return {
            'connected': connected,
            'name': name,
            'axes': axes,
            'buttons': buttons,
            'mouse': {'dx': mdx, 'dy': mdy, 'left': m_left, 'right': m_right},
            'keys': key_events,
            'active_keys_count': len(keys),
            'changed': changed
        }

class DOSBoxWebPage(QWebEnginePage):
    """Custom WebEnginePage with fullscreen support and automatic pointer lock / mouse permissions."""
    fullscreen_toggled = pyqtSignal(bool)

    def __init__(self, profile=None, parent=None):
        super().__init__(profile, parent)
        self.featurePermissionRequested.connect(self._on_feature_permission_requested)
        if hasattr(self, "permissionRequested"):
            self.permissionRequested.connect(self._on_permission_requested)

    def _on_feature_permission_requested(self, securityOrigin, feature):
        # Automatically grant MouseLock (pointer lock) and web features for retro game controls
        self.setFeaturePermission(securityOrigin, feature, QWebEnginePage.PermissionPolicy.PermissionGrantedByUser)

    def _on_permission_requested(self, permission):
        try:
            permission.grant()
        except Exception:
            pass

    def fullScreenRequested(self, request: QWebEngineFullScreenRequest):
        request.accept()
        self.fullscreen_toggled.emit(request.toggleOn())

class DOSBoxPlayerDialog(QDialog):
    """
    In-App Fullscreen & Windowed Retro Gaming Theater for Internet Archive
    MS-DOS, Amiga, and Arcade emulated games via WebAssembly & EM-DOSBox.
    """

    def __init__(self, identifier: str, title: str, parent=None):
        super().__init__(parent)
        self.identifier = identifier
        self.game_title = title
        self.is_muted = False
        self.is_custom_fullscreen = False
        self._autoboot_timer: Optional[QTimer] = None
        self._autoboot_attempts: int = 0

        # Persisted settings
        self.settings = QSettings("ArchiveVault", "DOSBoxPlayer")
        self.easy_crt_enabled = self.settings.value("easy_crt", False, type=bool)
        self.aspect_mode = self.settings.value("aspect_mode", "4:3", type=str)

        # Platform detection & retro metadata
        self.platform_info = detect_retro_platform(self.identifier)
        self.emulator_start = ""

        self.setWindowTitle(f"🕹️ {self.game_title} — ArchiveVault Retro Theater [{self.platform_info['name']}]")
        self.resize(1140, 780)
        self.setMinimumSize(880, 560)
        self.setStyleSheet("""
            QDialog {
                background-color: #0c0c0e;
                color: #f4f4f5;
            }
        """)

        self.gamepad_poller = GamepadPoller()
        self._last_gamepad_state = False
        self._last_keys_active = False
        self._gamepad_timer = QTimer(self)
        self._gamepad_timer.setInterval(50)
        self._gamepad_timer.timeout.connect(self._poll_gamepad)
        self._gamepad_timer.start()

        self._load_retries = 0

        self._init_ui()
        self._setup_shortcuts()
        self._fetch_emulator_metadata()

        self._load_timer = QTimer(self)
        self._load_timer.setSingleShot(True)
        self._load_timer.setInterval(120)
        self._load_timer.timeout.connect(self._load_game)
        self._load_timer.start()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Top Arcade Control Bar ---
        self.header_bar = QFrame()
        self.header_bar.setObjectName("headerBar")
        self.header_bar.setStyleSheet("""
            QFrame#headerBar {
                background-color: #141417;
                border-bottom: 1px solid #27272a;
                min-height: 44px;
                max-height: 44px;
                padding: 0 8px;
            }
        """)
        header_layout = QHBoxLayout(self.header_bar)
        header_layout.setContentsMargins(10, 0, 10, 0)
        header_layout.setSpacing(6)

        # Title & Badges
        icon_lbl = QLabel("🕹️")
        icon_lbl.setStyleSheet("font-size: 16px;")
        header_layout.addWidget(icon_lbl)

        title_lbl = QLabel(self.game_title)
        title_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #ffffff;")
        header_layout.addWidget(title_lbl)

        self.badge_lbl = QLabel(self.platform_info.get("badge", "MS-DOS"))
        self.badge_lbl.setStyleSheet(f"""
            background-color: {self.platform_info.get("badge_color", "#065f46")};
            color: #ffffff;
            font-size: 9px;
            font-weight: 800;
            padding: 3px 6px;
            border-radius: 4px;
        """)
        self.badge_lbl.setToolTip(f"{self.platform_info.get('name', 'Retro')} Emulation Engine via WebAssembly")
        header_layout.addWidget(self.badge_lbl)

        mouse_badge = QLabel("🖱️ Mouse")
        mouse_badge.setStyleSheet("""
            background-color: #1e1b4b;
            color: #c7d2fe;
            border: 1px solid #3730a3;
            font-size: 9px;
            font-weight: 700;
            padding: 3px 6px;
            border-radius: 4px;
        """)
        mouse_badge.setToolTip("Mouse: Click canvas to lock • Esc to release\nVirtual Mouse also active on Controller Right Stick!")
        header_layout.addWidget(mouse_badge)

        self.gamepad_badge = QLabel("🎮 Standby")
        self.gamepad_badge.setStyleSheet("""
            background-color: #1e1b4b;
            color: #c7d2fe;
            border: 1px solid #3730a3;
            font-size: 9px;
            font-weight: 700;
            padding: 3px 6px;
            border-radius: 4px;
        """)
        self.gamepad_badge.setToolTip(
            "🎮 Controller Active!\n"
            "• Left Stick / D-Pad: Movement / Arrow Keys\n"
            "• Right Stick: Virtual Mouse Aim & Look\n"
            "• A / RT: Fire / Left Click / Enter\n"
            "• B / LT: Strafe / Right Click\n"
            "• X: Space (Jump / Open Door)\n"
            "• Y: Shift (Run)\n"
            "• Start: Enter | Back: Esc\n"
            "• Native DOSBox Gameport & HTML5 Gamepad API fully enabled"
        )
        header_layout.addWidget(self.gamepad_badge)

        # Microcomputer Command Automation (Amstrad CPC, C64, Spectrum, etc.)
        self.type_cmd_btn = QPushButton("⌨️ Auto-Type")
        self.type_cmd_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.type_cmd_btn.setStyleSheet("""
            QPushButton {
                background-color: #0e7490;
                color: #ffffff;
                border: 1px solid #06b6d4;
                border-radius: 5px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #0891b2;
            }
        """)
        self.type_cmd_btn.clicked.connect(lambda: self._auto_type_game_command())
        if self.platform_info["name"] in ("Amstrad CPC", "ZX Spectrum", "Commodore 64"):
            default_start = self.platform_info.get("default_cmd", "RUN\"")
            self.type_cmd_btn.setText(f"⌨️ Auto-Type ({default_start})")
            self.type_cmd_btn.setToolTip(f"Auto-type '{default_start}' and press Enter into the {self.platform_info['name']}")
            self.type_cmd_btn.show()
        else:
            self.type_cmd_btn.hide()
        header_layout.addWidget(self.type_cmd_btn)

        self.cat_btn = QPushButton("📁 CAT (Files)")
        self.cat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cat_btn.setStyleSheet("""
            QPushButton {
                background-color: #27272a;
                color: #67e8f9;
                border: 1px solid #0891b2;
                border-radius: 5px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #164e63;
                color: #ffffff;
            }
        """)
        self.cat_btn.setToolTip("Type 'CAT' and press Enter to list files on the floppy disc")
        self.cat_btn.clicked.connect(lambda: self._auto_type_game_command("CAT"))
        if self.platform_info["name"] == "Amstrad CPC":
            self.cat_btn.show()
        else:
            self.cat_btn.hide()
        header_layout.addWidget(self.cat_btn)

        header_layout.addStretch(1)

        # Controls: Easy CRT, Aspect Ratio, Mute, Restart, Fullscreen, Open in Browser, Close
        btn_style = """
            QPushButton {
                background-color: #27272a;
                color: #e4e4e7;
                border: 1px solid #3f3f46;
                border-radius: 5px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #3f3f46;
                color: #ffffff;
            }
        """

        # Easy CRT Filter Toggle
        self.crt_btn = QPushButton("📺 CRT: " + ("ON" if self.easy_crt_enabled else "OFF"))
        self.crt_btn.setToolTip("Toggle retro CRT scanlines and phosphor aperture grille filter (Ctrl+C)")
        self._update_crt_btn_style()
        self.crt_btn.clicked.connect(self._toggle_easy_crt)
        header_layout.addWidget(self.crt_btn)

        # Aspect Ratio Toggle (4:3 vs Stretch)
        self.aspect_btn = QPushButton("📐 4:3" if self.aspect_mode == "4:3" else "📐 Stretch")
        self.aspect_btn.setStyleSheet(btn_style)
        self.aspect_btn.setToolTip("Toggle aspect ratio: 4:3 CRT pillarbox vs Full Stretch (Ctrl+A)")
        self.aspect_btn.clicked.connect(self._toggle_aspect_mode)
        header_layout.addWidget(self.aspect_btn)

        self.mute_btn = QPushButton("🔊 Audio")
        self.mute_btn.setStyleSheet(btn_style)
        self.mute_btn.setToolTip("Toggle game audio mute/unmute (Ctrl+M)")
        self.mute_btn.clicked.connect(self._toggle_mute)
        header_layout.addWidget(self.mute_btn)

        self.reload_btn = QPushButton("↺ Restart")
        self.reload_btn.setStyleSheet(btn_style)
        self.reload_btn.setToolTip("Reload / Restart the game (Ctrl+R)")
        self.reload_btn.clicked.connect(self._reload_game)
        header_layout.addWidget(self.reload_btn)

        self.fs_btn = QPushButton("⛶ Full")
        self.fs_btn.setStyleSheet(btn_style)
        self.fs_btn.setToolTip("Toggle fullscreen (F11)")
        self.fs_btn.clicked.connect(self._toggle_fullscreen)
        header_layout.addWidget(self.fs_btn)

        self.browser_btn = QPushButton("🌐 Web")
        self.browser_btn.setStyleSheet(btn_style)
        self.browser_btn.setToolTip("Open game embed in external web browser")
        self.browser_btn.clicked.connect(self._open_in_browser)
        header_layout.addWidget(self.browser_btn)

        self.close_btn = QPushButton("✕ Exit")
        self.close_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setMinimumSize(80, 28)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #991b1b;
                color: #ffffff;
                border: 1px solid #b91c1c;
                border-radius: 5px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #dc2626;
                border-color: #ef4444;
            }
        """)
        self.close_btn.setToolTip("Close game and return to ArchiveVault (Esc)")
        self.close_btn.clicked.connect(self._force_close)
        header_layout.addWidget(self.close_btn)

        main_layout.addWidget(self.header_bar)

        # Loading Progress Bar
        self.loading_bar = QProgressBar()
        self.loading_bar.setRange(0, 100)
        self.loading_bar.setFixedHeight(3)
        self.loading_bar.setTextVisible(False)
        self.loading_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background: #18181b;
            }
            QProgressBar::chunk {
                background: #3b82f6;
            }
        """)
        main_layout.addWidget(self.loading_bar)

        # --- QWebEngineView Area ---
        self.web_view = QWebEngineView(self)
        self.web_view.setStyleSheet("background-color: #000000; border: none;")
        self.web_page = DOSBoxWebPage(self.web_view.page().profile(), self.web_view)
        self.web_view.setPage(self.web_page)
        self.web_page.setAudioMuted(False)
        self.web_page.fullscreen_toggled.connect(self._on_html5_fullscreen)

        # Early CSS & Gamepad injection via QWebEngineScript at DocumentCreation
        early_script = QWebEngineScript()
        early_script.setName("av_early_suppress")
        early_script.setSourceCode("""
            // Unmute cookie for Archive.org Emularity engine
            try {
                document.cookie = "unmute=1; path=/; max-age=31536000";
                document.cookie = "unmute=1; path=/details; max-age=31536000";
                document.cookie = "unmute=1; path=/embed; max-age=31536000";
            } catch(e) {}

            // Auto-resume WebAudio AudioContext immediately upon instantiation
            try {
                var _AC = window.AudioContext || window.webkitAudioContext;
                if (_AC) {
                    window.__av_audio_contexts = window.__av_audio_contexts || [];
                    var PatchedAC = function() {
                        var ctx = new _AC();
                        window.__av_audio_contexts.push(ctx);
                        if (ctx.state === 'suspended') {
                            ctx.resume().catch(function() {});
                        }
                        ctx.addEventListener('statechange', function() {
                            if (ctx.state === 'suspended') {
                                ctx.resume().catch(function() {});
                            }
                        });
                        return ctx;
                    };
                    PatchedAC.prototype = _AC.prototype;
                    window.AudioContext = PatchedAC;
                    window.webkitAudioContext = PatchedAC;
                }
            } catch(e) {}

            // Early CSS to suppress splash and zero borders before 1st paint
            var style = document.createElement('style');
            style.id = 'av-early-style';
            style.textContent = `
                html, body {
                    margin: 0 !important;
                    padding: 0 !important;
                    background: #000000 !important;
                    overflow: hidden !important;
                }
                #jsmessSS img.ghost, .ghost, img[src*="start.png"], .emularity-splash-image, img[src*="dosbox.png"], .emularity-splash-screen > img, #jsmessSS #screenshot {
                    display: none !important;
                    opacity: 0 !important;
                    visibility: hidden !important;
                    width: 0 !important;
                    height: 0 !important;
                    pointer-events: none !important;
                }
                #wrap, #emulate, .ia-module {
                    background: #000000 !important;
                    margin: 0 !important;
                    padding: 0 !important;
                }
                #gamepadtext {
                    display: none !important;
                }
            `;
            if (document.head) {
                document.head.appendChild(style);
            } else {
                document.addEventListener('DOMContentLoaded', function() {
                    if (document.head) document.head.appendChild(style);
                });
            }

            // Early polyfill for HTML5 Gamepad API so Emscripten sees it immediately on init
            if (!window.__av_gamepad_state) {
                window.__av_gamepad_state = {
                    id: "Wireless Controller (STANDARD GAMEPAD)",
                    index: 0,
                    connected: false,
                    mapping: "standard",
                    timestamp: performance.now(),
                    axes: [0, 0, 0, 0],
                    buttons: Array.from({length: 17}, function() {
                        return { pressed: false, touched: false, value: 0 };
                    })
                };
            }
            if (!window.__av_gamepads_shimmed) {
                window.__av_gamepads_shimmed = true;
                var _orig = navigator.getGamepads ? navigator.getGamepads.bind(navigator) : null;
                try {
                    Object.defineProperty(navigator, 'getGamepads', {
                        value: function() {
                            if (window.__av_gamepad_state && window.__av_gamepad_state.connected) {
                                return [window.__av_gamepad_state, null, null, null];
                            }
                            if (_orig) {
                                try {
                                    var p = _orig();
                                    if (p && (p[0] || p[1])) return p;
                                } catch(e) {}
                            }
                            return [null, null, null, null];
                        },
                        configurable: true,
                        enumerable: true
                    });
                } catch(e) {}
            }
        """)
        early_script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        early_script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        self.web_page.scripts().insert(early_script)

        # Configure WebEngine Settings for WebAssembly gaming
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AutoLoadImages, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False)

        self.web_view.loadProgress.connect(self._on_load_progress)
        self.web_view.loadFinished.connect(self._on_load_finished)

        # Content Container with Stacked Layout (explicitly set contents margins to 0 to eliminate borders)
        self.content_container = QWidget(self)
        self.content_container.setStyleSheet("background-color: #000000; border: none;")
        self.stack_layout = QStackedLayout(self.content_container)
        self.stack_layout.setContentsMargins(0, 0, 0, 0)
        self.stack_layout.setStackingMode(QStackedLayout.StackingMode.StackAll)
        self.stack_layout.addWidget(self.web_view)

        # Sleek Native Arcade Loading Overlay
        self.loading_overlay = QWidget(self.content_container)
        self.loading_overlay.setStyleSheet("background-color: #0c0c0e; border: none;")
        ol_layout = QVBoxLayout(self.loading_overlay)
        ol_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ol_layout.setSpacing(14)

        self.loading_title_lbl = QLabel(f"🕹️ {self.game_title}")
        self.loading_title_lbl.setStyleSheet("font-size: 22px; font-weight: 800; color: #f4f4f5; background: transparent;")
        self.loading_title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ol_layout.addWidget(self.loading_title_lbl)

        self.loading_status_lbl = QLabel(f"⚡ Preparing {self.platform_info['name']} WebAssembly Engine...")
        self.loading_status_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #60a5fa; background: transparent;")
        self.loading_status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ol_layout.addWidget(self.loading_status_lbl)

        self.loading_pbar = QProgressBar()
        self.loading_pbar.setRange(0, 0)
        self.loading_pbar.setFixedSize(300, 6)
        self.loading_pbar.setStyleSheet("""
            QProgressBar {
                background-color: #1f1f23;
                border-radius: 3px;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #3b82f6;
                border-radius: 3px;
            }
        """)
        ol_layout.addWidget(self.loading_pbar)

        self.stack_layout.addWidget(self.loading_overlay)
        main_layout.addWidget(self.content_container, stretch=1)

    def showEvent(self, event):
        super().showEvent(event)
        try:
            from archivevault.ui.main_window import apply_windows_dark_titlebar
            apply_windows_dark_titlebar(self)
        except Exception:
            pass

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            if self.is_custom_fullscreen:
                self._toggle_fullscreen()
                event.accept()
                return
            self._force_close()
            event.accept()
            return
        super().keyPressEvent(event)

    def _force_close(self):
        """Immediately and safely shut down all emulation timers and close dialog without freezing."""
        self._shutdown()
        self.accept()

    def reject(self):
        self._shutdown()
        super().reject()

    def closeEvent(self, event):
        self._shutdown()
        event.accept()
        super().closeEvent(event)

    def _shutdown(self):
        if hasattr(self, "_load_timer") and self._load_timer.isActive():
            self._load_timer.stop()
        if hasattr(self, "_gamepad_timer") and self._gamepad_timer.isActive():
            self._gamepad_timer.stop()
        if hasattr(self, "_autoboot_timer") and self._autoboot_timer and self._autoboot_timer.isActive():
            self._autoboot_timer.stop()
        try:
            self.web_page.setAudioMuted(True)
            self.web_view.page().runJavaScript("if (document.exitPointerLock) document.exitPointerLock();")
            self.web_view.stop()
            self.web_view.setUrl(QUrl("about:blank"))
        except Exception:
            pass

    def _toggle_easy_crt(self):
        self.easy_crt_enabled = not self.easy_crt_enabled
        self.settings.setValue("easy_crt", self.easy_crt_enabled)
        self._update_crt_btn_style()
        self._apply_easy_crt()

    def _update_crt_btn_style(self):
        if self.easy_crt_enabled:
            self.crt_btn.setText("📺 CRT: ON")
            self.crt_btn.setStyleSheet("""
                QPushButton {
                    background-color: #064e3b;
                    color: #6ee7b7;
                    border: 1px solid #059669;
                    border-radius: 5px;
                    padding: 4px 8px;
                    font-size: 11px;
                    font-weight: 700;
                }
                QPushButton:hover {
                    background-color: #047857;
                    color: #ffffff;
                }
            """)
        else:
            self.crt_btn.setText("📺 CRT: OFF")
            self.crt_btn.setStyleSheet("""
                QPushButton {
                    background-color: #27272a;
                    color: #e4e4e7;
                    border: 1px solid #3f3f46;
                    border-radius: 5px;
                    padding: 4px 8px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #3f3f46;
                    color: #ffffff;
                }
            """)

    def _apply_easy_crt(self):
        val = "true" if self.easy_crt_enabled else "false"
        self.web_view.page().runJavaScript(f"window.__av_toggle_crt && window.__av_toggle_crt({val});")

    def _toggle_aspect_mode(self):
        if self.aspect_mode == "4:3":
            self.aspect_mode = "stretch"
            self.aspect_btn.setText("📐 Stretch")
        else:
            self.aspect_mode = "4:3"
            self.aspect_btn.setText("📐 4:3")
        self.settings.setValue("aspect_mode", self.aspect_mode)
        self._apply_aspect_mode()

    def _apply_aspect_mode(self):
        mode = self.aspect_mode
        self.web_view.page().runJavaScript(f"window.__av_set_aspect && window.__av_set_aspect('{mode}');")

    def _poll_gamepad(self):
        if not hasattr(self, "gamepad_poller") or not self.isVisible():
            return
        try:
            state = self.gamepad_poller.poll()
            connected = state["connected"]
            name = state["name"]
            active_keys = state["active_keys_count"]
            changed = state["changed"]

            # Update badge only on state changes to conserve UI thread resources
            is_active = (active_keys > 0)
            if connected != self._last_gamepad_state or is_active != getattr(self, "_last_keys_active", False):
                self._last_gamepad_state = connected
                self._last_keys_active = is_active
                if connected:
                    if is_active:
                        self.gamepad_badge.setText(f"🎮 Active ({active_keys})")
                        self.gamepad_badge.setStyleSheet("""
                            background-color: #064e3b;
                            color: #6ee7b7;
                            border: 1px solid #059669;
                            font-size: 9px;
                            font-weight: 700;
                            padding: 3px 6px;
                            border-radius: 4px;
                        """)
                    else:
                        self.gamepad_badge.setText("🎮 P1 Connected")
                        self.gamepad_badge.setStyleSheet("""
                            background-color: #065f46;
                            color: #a7f3d0;
                            border: 1px solid #047857;
                            font-size: 9px;
                            font-weight: 700;
                            padding: 3px 6px;
                            border-radius: 4px;
                        """)
                else:
                    self.gamepad_badge.setText("🎮 Standby")
                    self.gamepad_badge.setStyleSheet("""
                        background-color: #27272a;
                        color: #a1a1aa;
                        border: 1px solid #3f3f46;
                        font-size: 9px;
                        font-weight: 700;
                        padding: 3px 6px;
                        border-radius: 4px;
                    """)

            # CRITICAL: Only dispatch runJavaScript across IPC when inputs or connection state CHANGED!
            if connected and changed:
                payload = json.dumps(state)
                self.web_view.page().runJavaScript(f"window.__av_controller_tick && window.__av_controller_tick({payload});")
        except Exception:
            pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        try:
            self.web_view.page().runJavaScript("window.__av_fit_canvas && window.__av_fit_canvas();")
        except Exception:
            pass

    def _setup_shortcuts(self):
        # Escape key exits fullscreen or safely closes arcade player
        esc_sc = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        esc_sc.activated.connect(self._handle_esc_shortcut)

        # Alt+F4 closes dialog
        close_sc = QShortcut(QKeySequence("Alt+F4"), self)
        close_sc.activated.connect(self._force_close)

        # Ctrl+W closes dialog
        close_w_sc = QShortcut(QKeySequence("Ctrl+W"), self)
        close_w_sc.activated.connect(self._force_close)

        # F11 toggles Fullscreen
        f11_sc = QShortcut(QKeySequence(Qt.Key.Key_F11), self)
        f11_sc.activated.connect(self._toggle_fullscreen)

        # Ctrl+C toggles Easy CRT
        crt_sc = QShortcut(QKeySequence("Ctrl+C"), self)
        crt_sc.activated.connect(self._toggle_easy_crt)

        # Ctrl+A toggles Aspect Ratio
        ar_sc = QShortcut(QKeySequence("Ctrl+A"), self)
        ar_sc.activated.connect(self._toggle_aspect_mode)

        # Ctrl+M toggles Audio Mute
        mute_sc = QShortcut(QKeySequence("Ctrl+M"), self)
        mute_sc.activated.connect(self._toggle_mute)

        # Ctrl+R reloads
        reload_sc = QShortcut(QKeySequence("Ctrl+R"), self)
        reload_sc.activated.connect(self._reload_game)

    def _handle_esc_shortcut(self):
        if self.is_custom_fullscreen:
            self._toggle_fullscreen()
            return
        self._force_close()

    def _fetch_emulator_metadata(self):
        """Asynchronously query item metadata to detect specific emulators and start commands."""
        def _fetch():
            try:
                import requests
                r = requests.get(f"https://archive.org/metadata/{self.identifier}", timeout=5)
                if r.status_code == 200:
                    meta = r.json().get("metadata", {})
                    emu = str(meta.get("emulator", "")).lower()
                    start = str(meta.get("emulator_start", "")).strip()
                    QTimer.singleShot(0, lambda: self._apply_fetched_metadata(emu, start))
            except Exception:
                pass
        import threading
        threading.Thread(target=_fetch, daemon=True).start()

    def _apply_fetched_metadata(self, emu: str, start: str):
        if emu:
            if "cpc" in emu:
                self.platform_info = detect_retro_platform("cpc")
            elif "spectrum" in emu or "spec" in emu:
                self.platform_info = detect_retro_platform("spectrum")
            elif "c64" in emu:
                self.platform_info = detect_retro_platform("c64")
            elif "amiga" in emu:
                self.platform_info = detect_retro_platform("amiga")
            
            if hasattr(self, "badge_lbl"):
                self.badge_lbl.setText(self.platform_info["badge"])
                self.badge_lbl.setStyleSheet(f"""
                    background-color: {self.platform_info.get("badge_color", "#065f46")};
                    color: #ffffff;
                    font-size: 9px;
                    font-weight: 800;
                    padding: 3px 6px;
                    border-radius: 4px;
                """)
                self.badge_lbl.setToolTip(f"{self.platform_info.get('name', 'Retro')} Emulation Engine via WebAssembly")
            self.setWindowTitle(f"🕹️ {self.game_title} — ArchiveVault Retro Theater [{self.platform_info['name']}]")

        if start:
            self.emulator_start = start
            if hasattr(self, "type_cmd_btn"):
                self.type_cmd_btn.setText(f"⌨️ Auto-Type ({start})")
                self.type_cmd_btn.setToolTip(f"Auto-type '{start}' and press Enter into the {self.platform_info['name']}")
                self.type_cmd_btn.show()

    def _auto_type_game_command(self, cmd: Optional[str] = None):
        """Type a command into the emulated computer (e.g. RUN\"GOBLINS or CAT) and press Enter."""
        target_cmd = cmd or self.emulator_start or self.platform_info.get("default_cmd") or "RUN\""
        if not target_cmd.endswith("\n"):
            target_cmd += "\n"
        
        self.web_view.setFocus()
        js_code = f"""
        (function() {{
            var can = document.getElementById('canvas');
            if (can) can.focus();
            var text = {json.dumps(target_cmd)};
            var i = 0;
            function sendNext() {{
                if (i >= text.length) return;
                var ch = text[i++];
                var isEnter = (ch === '\\n' || ch === '\\r');
                var code = isEnter ? 13 : ch.charCodeAt(0);
                var keyName = isEnter ? 'Enter' : ch;
                
                var kd = new KeyboardEvent('keydown', {{
                    key: keyName,
                    code: isEnter ? 'Enter' : ('Key' + ch.toUpperCase()),
                    keyCode: code,
                    which: keyCode,
                    bubbles: true,
                    cancelable: true
                }});
                var kp = new KeyboardEvent('keypress', {{
                    key: keyName,
                    charCode: code,
                    keyCode: code,
                    which: keyCode,
                    bubbles: true,
                    cancelable: true
                }});
                var ku = new KeyboardEvent('keyup', {{
                    key: keyName,
                    keyCode: code,
                    which: keyCode,
                    bubbles: true,
                    cancelable: true
                }});
                
                var targets = [can, document, window];
                for (var t = 0; t < targets.length; t++) {{
                    if (targets[t]) {{
                        targets[t].dispatchEvent(kd);
                        targets[t].dispatchEvent(kp);
                        targets[t].dispatchEvent(ku);
                    }}
                }}
                setTimeout(sendNext, 50);
            }}
            sendNext();
        }})();
        """
        self.web_view.page().runJavaScript(js_code)

    def _show_emulation_error_card(self, title: str, message: str):
        """Display an actionable, stylish error card when an item has no online emulator."""
        if hasattr(self, "_load_timer") and self._load_timer.isActive():
            self._load_timer.stop()
        if self._autoboot_timer and self._autoboot_timer.isActive():
            self._autoboot_timer.stop()

        if hasattr(self, "loading_pbar"):
            self.loading_pbar.hide()
        if hasattr(self, "loading_status_lbl"):
            self.loading_status_lbl.hide()

        if not hasattr(self, "error_card"):
            self.error_card = QFrame(self.loading_overlay)
            self.error_card.setStyleSheet("""
                QFrame {
                    background-color: #18181b;
                    border: 1px solid #ef4444;
                    border-radius: 12px;
                    padding: 24px;
                    max-width: 580px;
                }
            """)
            err_layout = QVBoxLayout(self.error_card)
            err_layout.setSpacing(16)

            self.err_badge = QLabel("❌ Online Emulation Not Found")
            self.err_badge.setStyleSheet("color: #ef4444; font-size: 17px; font-weight: 800; background: transparent;")
            self.err_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            err_layout.addWidget(self.err_badge)

            self.err_msg_lbl = QLabel()
            self.err_msg_lbl.setStyleSheet("color: #d4d4d8; font-size: 13px; line-height: 1.6; background: transparent;")
            self.err_msg_lbl.setWordWrap(True)
            self.err_msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            err_layout.addWidget(self.err_msg_lbl)

            # Two spacious, clearly organized rows of action buttons to prevent squashing
            row1_box = QHBoxLayout()
            row1_box.setSpacing(12)
            row1_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

            self.btn_err_retry = QPushButton("Retry / Reload ↺")
            self.btn_err_retry.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_err_retry.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.btn_err_retry.setMinimumSize(160, 40)
            self.btn_err_retry.setStyleSheet("""
                QPushButton {
                    background-color: #0284c7;
                    color: #ffffff;
                    font-weight: 700;
                    padding: 8px 18px;
                    border-radius: 8px;
                    font-size: 13px;
                    border: 1px solid #0ea5e9;
                }
                QPushButton:hover {
                    background-color: #0369a1;
                    border-color: #38bdf8;
                }
            """)
            self.btn_err_retry.clicked.connect(self._reload_game)
            row1_box.addWidget(self.btn_err_retry)

            self.btn_err_ra = QPushButton("Play in Easy Retro ⚡")
            self.btn_err_ra.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_err_ra.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.btn_err_ra.setMinimumSize(170, 40)
            self.btn_err_ra.setStyleSheet("""
                QPushButton {
                    background-color: #7c3aed;
                    color: #ffffff;
                    font-weight: 700;
                    padding: 8px 18px;
                    border-radius: 8px;
                    font-size: 13px;
                    border: 1px solid #8b5cf6;
                }
                QPushButton:hover {
                    background-color: #6d28d9;
                    border-color: #a78bfa;
                }
            """)
            self.btn_err_ra.clicked.connect(self._launch_easy_retro_fallback)
            row1_box.addWidget(self.btn_err_ra)
            err_layout.addLayout(row1_box)

            row2_box = QHBoxLayout()
            row2_box.setSpacing(12)
            row2_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

            self.btn_err_web = QPushButton("View on Archive.org 🌐")
            self.btn_err_web.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_err_web.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.btn_err_web.setMinimumSize(160, 36)
            self.btn_err_web.setStyleSheet("""
                QPushButton {
                    background-color: #27272a;
                    color: #93c5fd;
                    font-weight: 600;
                    padding: 7px 16px;
                    border: 1px solid #3f3f46;
                    border-radius: 6px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #3f3f46;
                    color: #bfdbfe;
                }
            """)
            self.btn_err_web.clicked.connect(self._open_in_browser)
            row2_box.addWidget(self.btn_err_web)

            self.btn_err_close = QPushButton("Close Arcade ✕")
            self.btn_err_close.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_err_close.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.btn_err_close.setMinimumSize(140, 36)
            self.btn_err_close.setStyleSheet("""
                QPushButton {
                    background-color: #3f3f46;
                    color: #f4f4f5;
                    font-weight: 600;
                    padding: 7px 16px;
                    border: 1px solid #52525b;
                    border-radius: 6px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #52525b;
                    color: #ffffff;
                }
            """)
            self.btn_err_close.clicked.connect(self._force_close)
            row2_box.addWidget(self.btn_err_close)
            err_layout.addLayout(row2_box)

            self.loading_overlay.layout().addWidget(self.error_card)

        self.err_badge.setText(f"❌ {title}")
        self.err_msg_lbl.setText(message)
        self.error_card.show()
        self.loading_overlay.show()
        self.loading_overlay.raise_()

    def _launch_easy_retro_fallback(self):
        """Launch the current game in RetroArch if a local ROM exists, or open the Easy Retro Station dialog."""
        from archivevault.core.utils import find_local_game_rom, get_retroarch_path, launch_retroarch
        from archivevault.ui.retroarch_dialog import EasyRetroDialog

        rom = find_local_game_rom(self.identifier)
        if rom and os.path.exists(rom):
            success = launch_retroarch(rom, self.platform_info.get("name"))
            if success:
                self._force_close()
                return

        dlg = EasyRetroDialog(parent=self.parent())
        self._force_close()
        dlg.exec()

    def _load_game(self):
        if self._autoboot_timer and self._autoboot_timer.isActive():
            self._autoboot_timer.stop()
        if hasattr(self, "loading_overlay"):
            self.loading_overlay.show()
            self.loading_overlay.raise_()
        if hasattr(self, "loading_pbar"):
            self.loading_pbar.show()
        if hasattr(self, "loading_status_lbl"):
            self.loading_status_lbl.show()
            self.loading_status_lbl.setText(f"⚡ Preparing {self.platform_info['name']} WebAssembly Engine...")
        if hasattr(self, "error_card"):
            self.error_card.hide()
        embed_url = f"https://archive.org/embed/{self.identifier}"
        self.loading_bar.show()
        try:
            self.web_page.runJavaScript("window.__av_start_triggered = false;")
        except Exception:
            pass
        self.web_view.setUrl(QUrl(embed_url))

    def _retry_game_load(self):
        if hasattr(self, "error_card"):
            self.error_card.hide()
        if hasattr(self, "loading_overlay"):
            self.loading_overlay.show()
            self.loading_overlay.raise_()
        if hasattr(self, "loading_pbar"):
            self.loading_pbar.show()
        self.loading_bar.show()
        embed_url = f"https://archive.org/embed/{self.identifier}"
        self.web_view.setUrl(QUrl(embed_url))

    def _on_load_progress(self, progress: int):
        self.loading_bar.setValue(progress)

    def _on_load_finished(self, success: bool):
        self.loading_bar.hide()
        if success:
            self._load_retries = 0
            self._inject_center_styling()
            self._apply_easy_crt()
            self._apply_aspect_mode()
            self._start_autoboot_poller()
        else:
            if self._load_retries < 2:
                self._load_retries += 1
                if hasattr(self, "loading_status_lbl"):
                    self.loading_status_lbl.setText(
                        f"⏳ Connecting to Internet Archive (Attempt {self._load_retries + 1}/3)..."
                    )
                QTimer.singleShot(900, self._retry_game_load)
                return

            self._show_emulation_error_card(
                title="Page Load Failed",
                message=(
                    f"Could not connect to Internet Archive for <b>'{self.identifier}'</b>.<br><br>"
                    "Internet Archive may be experiencing high server traffic, or the connection timed out.<br>"
                    "Click <b>'Retry / Reload ↺'</b> to try again, or launch offline in <b>Easy Retro</b>."
                )
            )
        self.web_view.setFocus()

    def _start_autoboot_poller(self):
        """Poll the page until the WebAssembly DOSBox engine boots and canvas is running."""
        if self._autoboot_timer and self._autoboot_timer.isActive():
            self._autoboot_timer.stop()
        self._autoboot_attempts = 0
        self._autoboot_timer = QTimer(self)
        self._autoboot_timer.setInterval(600)
        self._autoboot_timer.timeout.connect(self._poll_autoboot)
        self._autoboot_timer.start()

    def _poll_autoboot(self):
        self._autoboot_attempts += 1
        if self._autoboot_attempts > 55:  # Allow up to ~33 seconds
            if self._autoboot_timer:
                self._autoboot_timer.stop()
            self._show_emulation_error_card(
                title="Emulation Timed Out",
                message=(
                    f"The game <b>'{self.identifier}'</b> did not start rendering within 30 seconds.<br><br>"
                    "Internet Archive may be experiencing high server load, or this item may require local emulation in <b>Easy Retro (RetroArch)</b>."
                )
            )
            return

        def on_result(res):
            if not res:
                if self._autoboot_attempts >= 25:  # ~15 seconds for scripts
                    if self._autoboot_timer:
                        self._autoboot_timer.stop()
                    self._show_emulation_error_card(
                        title="Online Emulation Not Available",
                        message=(
                            f"<b>'{self.identifier}'</b> does not have an in-browser WebAssembly emulator configured on the Internet Archive.<br><br>"
                            "Offline MAME and local ROMs can be played directly with <b>Easy Retro (RetroArch)</b>."
                        )
                    )
                return

            if isinstance(res, dict):
                status = res.get('status')
                splash = res.get('splash')

                if status == 'no_emulator' or res.get('is404'):
                    if self._autoboot_attempts >= 6:  # ~3.6 seconds to detect 404
                        if self._autoboot_timer:
                            self._autoboot_timer.stop()
                        self._show_emulation_error_card(
                            title="Online Emulation Not Available",
                            message=(
                                f"<b>'{self.identifier}'</b> does not have an in-browser WebAssembly emulator on the Internet Archive.<br><br>"
                                "This happens when opening an offline ROM file (like MAME non-merged zips or microcomputer disk images) rather than a pre-configured Internet Arcade game."
                            )
                        )
                        return

                if splash and hasattr(self, 'loading_status_lbl'):
                    self.loading_status_lbl.setText(f"📥 {splash}")
                if status == 'running':
                    if self._autoboot_timer:
                        self._autoboot_timer.stop()
                    if hasattr(self, 'loading_overlay'):
                        self.loading_overlay.hide()
                    self._apply_easy_crt()
                    self._apply_aspect_mode()
                    self.web_view.setFocus()
            elif res is True:
                if self._autoboot_timer:
                    self._autoboot_timer.stop()
                if hasattr(self, 'loading_overlay'):
                    self.loading_overlay.hide()
                self._apply_easy_crt()
                self._apply_aspect_mode()
                self.web_view.setFocus()

        self.web_view.page().runJavaScript(
            "window.__av_boot ? window.__av_boot() : false;",
            on_result
        )

    def _inject_center_styling(self):
        """
        Inject CSS & JS to dynamically scale the canvas to fill the viewport (windowed and fullscreen),
        eliminate borders and letterbox bleeding, implement 'Easy CRT' retro shader overlays,
        provide HTML5 Gamepad API polyfill + Virtual Mouse for joysticks, and auto-dismiss splash screens.
        """
        script = """
        (function() {
            if (window.__av_styled) {
                if (window.__av_fit_canvas) window.__av_fit_canvas();
                return;
            }
            window.__av_styled = true;

            // --- Inject Core Stylesheet ---
            var el = document.getElementById('av-arcade-style');
            if (!el) {
                var s = document.createElement('style');
                s.id = 'av-arcade-style';
                s.textContent = [
                    'html, body {',
                    '    width: 100vw !important;',
                    '    height: 100vh !important;',
                    '    margin: 0 !important;',
                    '    padding: 0 !important;',
                    '    overflow: hidden !important;',
                    '    background: #000000 !important;',
                    '}',
                    '#wrap, #emulate, .ia-module {',
                    '    width: 100% !important;',
                    '    height: 100% !important;',
                    '    margin: 0 !important;',
                    '    padding: 0 !important;',
                    '    background: #000000 !important;',
                    '    position: relative !important;',
                    '    display: flex !important;',
                    '    justify-content: center !important;',
                    '    align-items: center !important;',
                    '    overflow: hidden !important;',
                    '}',
                    '#canvasholder {',
                    '    position: absolute !important;',
                    '    top: 0 !important;',
                    '    left: 0 !important;',
                    '    width: 100% !important;',
                    '    height: 100% !important;',
                    '    transform: none !important;',
                    '    -webkit-transform: none !important;',
                    '    display: flex !important;',
                    '    justify-content: center !important;',
                    '    align-items: center !important;',
                    '    margin: 0 !important;',
                    '    padding: 0 !important;',
                    '    border: none !important;',
                    '    background: #000000 !important;',
                    '    z-index: 1 !important;',
                    '    overflow: hidden !important;',
                    '}',
                    '#canvasholder canvas, #canvas {',
                    '    display: block !important;',
                    '    position: relative !important;',
                    '    margin: auto !important;',
                    '    border: none !important;',
                    '    outline: none !important;',
                    '    image-rendering: pixelated !important;',
                    '    image-rendering: crisp-edges !important;',
                    '    box-shadow: 0 0 50px rgba(0, 0, 0, 0.95) !important;',
                    '    cursor: crosshair !important;',
                    '}',
                    '#gamepadtext {',
                    '    display: none !important;',
                    '}',
                    '#jsmessSS img.ghost, .ghost, img[src*="start.png"], .emularity-splash-image, img[src*="dosbox.png"], .emularity-splash-screen > img {',
                    '    display: none !important;',
                    '    opacity: 0 !important;',
                    '    visibility: hidden !important;',
                    '    pointer-events: none !important;',
                    '    width: 0 !important;',
                    '    height: 0 !important;',
                    '}',
                    '#jsmessSS {',
                    '    position: absolute;',
                    '    top: 50%;',
                    '    left: 50%;',
                    '    transform: translate(-50%, -50%);',
                    '    z-index: 10;',
                    '    cursor: pointer;',
                    '    display: flex;',
                    '    flex-direction: column;',
                    '    justify-content: center;',
                    '    align-items: center;',
                    '    transition: opacity 0.3s ease;',
                    '}',
                    '#jsmessSS #screenshot {',
                    '    display: none !important;',
                    '}',
                    '.emularity-splash-screen {',
                    '    background: #09090b !important;',
                    '    color: #e4e4e7 !important;',
                    '    border: 1px solid #27272a !important;',
                    '    border-radius: 8px !important;',
                    '    padding: 24px !important;',
                    '    box-shadow: 0 8px 30px rgba(0,0,0,0.8) !important;',
                    '}',
                    '.emularity-splash-title {',
                    '    color: #60a5fa !important;',
                    '    font-weight: 700 !important;',
                    '    font-size: 16px !important;',
                    '    margin-bottom: 12px !important;',
                    '    display: block !important;',
                    '}',
                    '.av-game-running #jsmessSS, #jsmessSS.av-started, #jsmessSS.av-hidden, #jsmessSS[style*="display: none"], #jsmessSS[style*="display:none"], .av-game-running .emularity-splash-screen {',
                    '    display: none !important;',
                    '    visibility: hidden !important;',
                    '    opacity: 0 !important;',
                    '    pointer-events: none !important;',
                    '}',
                    '.hidden-for-screen-readers, .navia-header, .ia-topnav, #theatre-controls {',
                    '    display: none !important;',
                    '}'
                ].join('\\n');
                document.head.appendChild(s);
            }

            // --- Easy CRT Shader Overlay ---
            window.__av_toggle_crt = function(enable) {
                var el = document.getElementById('av-crt-overlay');
                if (!el) {
                    el = document.createElement('div');
                    el.id = 'av-crt-overlay';
                    el.style.cssText = [
                        'position: fixed !important',
                        'top: 0 !important',
                        'left: 0 !important',
                        'width: 100vw !important',
                        'height: 100vh !important',
                        'pointer-events: none !important',
                        'z-index: 99999 !important',
                        'background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.28) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.035), rgba(0, 255, 0, 0.015), rgba(0, 0, 255, 0.035)) !important',
                        'background-size: 100% 3px, 3px 100% !important',
                        'box-shadow: inset 0 0 80px rgba(0, 0, 0, 0.7) !important',
                        'transition: opacity 0.15s ease-in-out !important'
                    ].join(';') + ';';
                    document.body.appendChild(el);
                }
                el.style.display = enable ? 'block' : 'none';
                var can = document.getElementById('canvas');
                if (can) {
                    if (enable) {
                        can.style.setProperty('filter', 'contrast(1.08) brightness(1.05) saturate(1.15)', 'important');
                    } else {
                        can.style.setProperty('filter', 'none', 'important');
                    }
                }
            };

            // --- Aspect Ratio Mode Controller ('4:3' or 'stretch') ---
            window.__av_aspect_mode = '4:3';
            window.__av_set_aspect = function(mode) {
                window.__av_aspect_mode = mode;
                fitCanvas();
            };

            // --- Dynamic Canvas Scaler ---
            function fitCanvas() {
                var can = document.getElementById('canvas');
                if (!can) return;

                var mode = window.__av_aspect_mode || '4:3';
                if (mode === 'stretch') {
                    can.style.setProperty('width', '100vw', 'important');
                    can.style.setProperty('height', '100vh', 'important');
                    can.style.setProperty('max-width', '100vw', 'important');
                    can.style.setProperty('max-height', '100vh', 'important');
                    can.style.setProperty('margin', '0', 'important');
                    return;
                }

                // Default 4:3 or original aspect ratio mode
                var cw = can.width;
                var ch = can.height;
                var ar = 4 / 3;
                if (cw && ch && cw > 0 && ch > 0 && !(cw === 300 && ch === 150)) {
                    if ((cw === 320 && ch === 200) || (cw === 640 && ch === 400)) {
                        ar = 4 / 3;
                    } else {
                        ar = cw / ch;
                    }
                }

                var vw = window.innerWidth || document.documentElement.clientWidth;
                var vh = window.innerHeight || document.documentElement.clientHeight;
                if (vw <= 0 || vh <= 0) return;

                var targetW, targetH;
                if (vw / vh > ar) {
                    targetH = vh;
                    targetW = Math.round(vh * ar);
                } else {
                    targetW = vw;
                    targetH = Math.round(vw / ar);
                }

                var newW = targetW + 'px';
                var newH = targetH + 'px';
                if (can.style.width !== newW) can.style.setProperty('width', newW, 'important');
                if (can.style.height !== newH) can.style.setProperty('height', newH, 'important');
                can.style.setProperty('max-width', '100vw', 'important');
                can.style.setProperty('max-height', '100vh', 'important');
                can.style.setProperty('margin', 'auto', 'important');
            }
            window.__av_fit_canvas = fitCanvas;
            fitCanvas();
            window.removeEventListener('resize', fitCanvas);
            window.addEventListener('resize', fitCanvas);
            setInterval(fitCanvas, 500);

            // --- HTML5 Gamepad Polyfill & Virtual Mouse / Typematic Bridge ---
            if (!window.__av_gamepad_state) {
                window.__av_gamepad_state = {
                    id: "Xbox 360 Controller (XInput STANDARD GAMEPAD)",
                    index: 0,
                    connected: false,
                    mapping: "standard",
                    timestamp: performance.now(),
                    axes: [0, 0, 0, 0],
                    buttons: Array.from({length: 17}, function() {
                        return { pressed: false, touched: false, value: 0 };
                    })
                };
            }
            if (!window.__av_gamepads_shimmed) {
                window.__av_gamepads_shimmed = true;
                var _orig = navigator.getGamepads ? navigator.getGamepads.bind(navigator) : null;
                try {
                    Object.defineProperty(navigator, 'getGamepads', {
                        value: function() {
                            if (window.__av_gamepad_state && window.__av_gamepad_state.connected) {
                                return [window.__av_gamepad_state, null, null, null];
                            }
                            if (_orig) {
                                try {
                                    var p = _orig();
                                    if (p && (p[0] || p[1])) return p;
                                } catch(e) {}
                            }
                            return [null, null, null, null];
                        },
                        configurable: true,
                        enumerable: true
                    });
                } catch(e) {}
            }

            window.__av_controller_tick = function(data) {
                if (!data) return;

                // 1. Update Gamepad API
                var pad = window.__av_gamepad_state;
                var wasConnected = pad.connected;
                pad.connected = !!data.connected;
                pad.timestamp = performance.now();
                if (data.axes) pad.axes = data.axes;
                if (data.buttons) {
                    for (var i = 0; i < data.buttons.length; i++) {
                        var val = data.buttons[i];
                        pad.buttons[i] = { pressed: val > 0.5, touched: val > 0.1, value: val };
                    }
                }
                if (!wasConnected && pad.connected) {
                    try {
                        var ev = new GamepadEvent('gamepadconnected', { gamepad: pad });
                        window.dispatchEvent(ev);
                    } catch(e) {
                        var ev2 = new Event('gamepadconnected');
                        ev2.gamepad = pad;
                        window.dispatchEvent(ev2);
                    }
                } else if (wasConnected && !pad.connected) {
                    try {
                        window.dispatchEvent(new GamepadEvent('gamepaddisconnected', { gamepad: pad }));
                    } catch(e) {
                        window.dispatchEvent(new Event('gamepaddisconnected'));
                    }
                }

                // 2. Virtual Mouse (for mouse-driven DOS games)
                var m = data.mouse;
                if (m) {
                    var can = document.getElementById('canvas');
                    if (!window.__av_mouse_pos) {
                        window.__av_mouse_pos = { x: window.innerWidth / 2, y: window.innerHeight / 2 };
                    }
                    if (m.dx !== 0 || m.dy !== 0) {
                        window.__av_mouse_pos.x = Math.max(0, Math.min(window.innerWidth, window.__av_mouse_pos.x + m.dx));
                        window.__av_mouse_pos.y = Math.max(0, Math.min(window.innerHeight, window.__av_mouse_pos.y + m.dy));
                        var moveEv = new MouseEvent('mousemove', {
                            bubbles: true,
                            cancelable: true,
                            clientX: window.__av_mouse_pos.x,
                            clientY: window.__av_mouse_pos.y,
                            movementX: m.dx,
                            movementY: m.dy,
                            view: window
                        });
                        if (can) can.dispatchEvent(moveEv);
                        document.dispatchEvent(moveEv);
                    }
                    if (window.__av_last_mleft !== m.left) {
                        window.__av_last_mleft = m.left;
                        var typeL = m.left ? 'mousedown' : 'mouseup';
                        var btnEv = new MouseEvent(typeL, {
                            bubbles: true,
                            cancelable: true,
                            clientX: window.__av_mouse_pos.x,
                            clientY: window.__av_mouse_pos.y,
                            button: 0,
                            buttons: m.left ? 1 : 0,
                            view: window
                        });
                        if (can) can.dispatchEvent(btnEv);
                        document.dispatchEvent(btnEv);
                        if (!m.left) {
                            var clickEv = new MouseEvent('click', {
                                bubbles: true,
                                cancelable: true,
                                clientX: window.__av_mouse_pos.x,
                                clientY: window.__av_mouse_pos.y,
                                button: 0,
                                view: window
                            });
                            if (can) can.dispatchEvent(clickEv);
                            document.dispatchEvent(clickEv);
                        }
                    }
                    if (window.__av_last_mright !== m.right) {
                        window.__av_last_mright = m.right;
                        var typeR = m.right ? 'mousedown' : 'mouseup';
                        var rEv = new MouseEvent(typeR, {
                            bubbles: true,
                            cancelable: true,
                            clientX: window.__av_mouse_pos.x,
                            clientY: window.__av_mouse_pos.y,
                            button: 2,
                            buttons: m.right ? 2 : 0,
                            view: window
                        });
                        if (can) can.dispatchEvent(rEv);
                        document.dispatchEvent(rEv);
                    }
                }

                // 3. Typematic Keyboard Events (for keyboard-driven DOS games)
                if (data.keys && data.keys.length > 0) {
                    var canK = document.getElementById('canvas');
                    for (var k = 0; k < data.keys.length; k++) {
                        var item = data.keys[k]; // [action, key, code, keyCode, repeat]
                        var evType = (item[0] === 'down') ? 'keydown' : 'keyup';
                        var kev = new KeyboardEvent(evType, {
                            key: item[1],
                            code: item[2],
                            keyCode: item[3],
                            which: item[3],
                            repeat: !!item[4],
                            bubbles: false,
                            cancelable: true,
                            view: window
                        });
                        try {
                            Object.defineProperty(kev, 'keyCode', { get: function() { return item[3]; } });
                            Object.defineProperty(kev, 'which', { get: function() { return item[3]; } });
                        } catch(e) {}
                        if (canK) {
                            canK.dispatchEvent(kev);
                        } else {
                            document.dispatchEvent(kev);
                        }
                    }
                }
                if (window.__av_unmute_audio) window.__av_unmute_audio();
            };

            // --- Pointer Lock Setup for Mouse-Controlled Retro Games ---
            function setupPointerLock() {
                var can = document.getElementById('canvas');
                var holder = document.getElementById('canvasholder');
                var target = can || holder;
                if (target && !target.__av_mouse_bound) {
                    target.__av_mouse_bound = true;
                    target.addEventListener('click', function() {
                        try {
                            target.tabIndex = 1;
                            target.focus();
                        } catch(e) {}
                    });
                }
            }
            setupPointerLock();

            // Pointer lock toast feedback
            if (!document.__av_lock_listener_bound) {
                document.__av_lock_listener_bound = true;
                document.addEventListener('pointerlockchange', function() {
                    var isLocked = (document.pointerLockElement !== null);
                    var toast = document.getElementById('av-mouse-toast');
                    if (!toast) {
                        toast = document.createElement('div');
                        toast.id = 'av-mouse-toast';
                        toast.style.cssText = 'position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:rgba(15,23,42,0.92);color:#93c5fd;border:1px solid #3b82f6;padding:8px 18px;border-radius:20px;font-size:12px;font-family:Segoe UI,sans-serif;font-weight:700;z-index:999999;pointer-events:none;transition:opacity 0.3s ease;box-shadow:0 4px 15px rgba(0,0,0,0.6);';
                        document.body.appendChild(toast);
                    }
                    if (isLocked) {
                        toast.textContent = '🖱️ Mouse Locked to Game — Press Esc to Release';
                        toast.style.opacity = '1';
                        clearTimeout(toast.__timeout);
                        toast.__timeout = setTimeout(function() {
                            toast.style.opacity = '0';
                        }, 3000);
                    } else {
                        toast.textContent = '🖱️ Mouse Released';
                        toast.style.opacity = '1';
                        clearTimeout(toast.__timeout);
                        toast.__timeout = setTimeout(function() {
                            toast.style.opacity = '0';
                        }, 1500);
                    }
                });
            }

            // --- Start Overlay Dismissal ---
            function dismissStartOverlay() {
                var btn = document.getElementById('jsmessSS');
                if (btn) {
                    btn.classList.add('av-started');
                    btn.classList.add('av-hidden');
                    btn.style.setProperty('display', 'none', 'important');
                }
                var splash = document.querySelector('.emularity-splash-screen');
                if (splash) {
                    splash.style.setProperty('display', 'none', 'important');
                }
                document.body.classList.add('av-game-running');
            }

            var btn = document.getElementById('jsmessSS');
            if (btn && !btn.__av_click_bound) {
                btn.__av_click_bound = true;
                btn.addEventListener('click', function() {
                    dismissStartOverlay();
                });
            }

            // Audio Unmuler and AudioContext Resumer
            window.__av_unmute_audio = function() {
                try {
                    // 1. Archive.org Emularity Unmute
                    if (window.rr) {
                        if (typeof window.rr.setMute === 'function') window.rr.setMute(false);
                        if (typeof window.rr.unmute === 'function') window.rr.unmute();
                    }
                    var muteClick = document.querySelector('.js-emulation-mute-click');
                    var muteIcon = document.querySelector('.iconochive-mute');
                    if (muteIcon && muteIcon.style.display !== 'none' && muteClick) {
                        try { muteClick.click(); } catch(e) {}
                    }

                    // 2. Emscripten & SDL AudioContext Resumption
                    if (window.Module) {
                        if (window.Module.SDL2 && window.Module.SDL2.audioContext && window.Module.SDL2.audioContext.state === 'suspended') {
                            window.Module.SDL2.audioContext.resume().catch(function() {});
                        }
                        if (window.Module.audioContext && window.Module.audioContext.state === 'suspended') {
                            window.Module.audioContext.resume().catch(function() {});
                        }
                    }

                    // 3. Tracked WebAudio Contexts
                    if (window.__av_audio_contexts) {
                        for (var i = 0; i < window.__av_audio_contexts.length; i++) {
                            var ctx = window.__av_audio_contexts[i];
                            if (ctx && ctx.state === 'suspended') {
                                ctx.resume().catch(function() {});
                            }
                        }
                    }
                } catch(e) {}
            };

            // Prevent inadvertent pause from freezing the game loop
            function guardPause() {
                try {
                    if (window.Module && window.Module.pauseMainLoop && !window.Module.__av_pause_guarded) {
                        window.Module.__av_pause_guarded = true;
                        var origPause = window.Module.pauseMainLoop;
                        window.Module.pauseMainLoop = function() {
                            if (window.__av_explicit_pause) {
                                origPause.apply(this, arguments);
                            }
                        };
                    }
                    if (window.rr && window.rr.pause && !window.rr.__av_pause_guarded) {
                        window.rr.__av_pause_guarded = true;
                        var origRrPause = window.rr.pause;
                        window.rr.pause = function() {
                            if (window.__av_explicit_pause) {
                                origRrPause.apply(this, arguments);
                            }
                        };
                    }
                } catch(e) {}
            }
            setInterval(guardPause, 500);

            // --- Main Auto-Boot Trigger ---
            window.__av_boot = function() {
                try {
                    var btn = document.getElementById('jsmessSS');
                    var can = document.getElementById('canvas');
                    var splash = document.querySelector('.emularity-splash-screen');
                    var emuWrap = document.getElementById('emulate') || document.querySelector('.ia-module');

                    var hasEmu = !!(can || btn || splash || emuWrap || window.Module);
                    var is404 = document.title.includes('404') || (document.body && (document.body.innerText.includes('does not exist') || document.body.innerText.includes('problem with your request') || document.body.innerText.includes('cannot be found')));

                    if (!hasEmu) {
                        return { status: 'no_emulator', is404: is404 };
                    }

                    setupPointerLock();
                    fitCanvas();

                    // 1. Check if canvas is actively rendering game graphics
                    var isRendering = false;
                    if (can && (can.width > 300 || can.height > 150)) {
                        isRendering = true;
                    }

                    if (isRendering) {
                        dismissStartOverlay();
                        fitCanvas();
                        if (window.__av_unmute_audio) window.__av_unmute_audio();
                        if (can) {
                            try {
                                can.tabIndex = 1;
                                can.focus();
                            } catch(e) {}
                        }
                        return { status: 'running', w: can.width, h: can.height };
                    }

                    // 2. Single-shot trigger start: ONLY fire start once to avoid spawning duplicate WASM workers
                    if (!window.__av_start_triggered) {
                        var startTargets = [
                            document.getElementById('jsmessSS'),
                            document.querySelector('.js-emulation-emulate'),
                            document.querySelector('.emularity-splash-screen'),
                            document.querySelector('button[data-action="start"]'),
                            document.querySelector('.ia-module button'),
                            document.getElementById('screenshot')
                        ];
                        for (var sIdx = 0; sIdx < startTargets.length; sIdx++) {
                            var st = startTargets[sIdx];
                            if (st) {
                                window.__av_start_triggered = true;
                                try { st.click(); } catch(e) {}
                                try {
                                    var ev = new MouseEvent('click', { bubbles: true, cancelable: true, view: window });
                                    st.dispatchEvent(ev);
                                } catch(e) {}
                                break;
                            }
                        }
                        if (window.rr && typeof window.rr.start === 'function' && !window.rr.running) {
                            try {
                                window.__av_start_triggered = true;
                                window.rr.start({ hasCustomCSS: true });
                            } catch(e) {}
                        }
                    }

                    var splashText = splash ? (splash.innerText || splash.textContent || '').split('\\n')[0] : '';
                    return { status: 'waiting', splash: splashText };
                } catch(e) {
                    return { status: 'error', error: e.toString() };
                }
            };
        })();
        """
        try:
            self.web_view.page().runJavaScript(script)
        except Exception:
            pass

    def _toggle_mute(self):
        self.is_muted = not self.is_muted
        self.web_page.setAudioMuted(self.is_muted)
        if self.is_muted:
            self.mute_btn.setText("🔇 Muted")
            self.mute_btn.setStyleSheet("""
                QPushButton {
                    background-color: #7f1d1d;
                    color: #ffffff;
                    border: 1px solid #991b1b;
                    border-radius: 6px;
                    padding: 5px 10px;
                    font-size: 12px;
                    font-weight: 600;
                }
            """)
            try:
                self.web_view.page().runJavaScript("if (window.rr && window.rr.mute) window.rr.mute();")
            except Exception:
                pass
        else:
            self.mute_btn.setText("🔊 Audio")
            self.mute_btn.setStyleSheet("""
                QPushButton {
                    background-color: #27272a;
                    color: #e4e4e7;
                    border: 1px solid #3f3f46;
                    border-radius: 6px;
                    padding: 5px 10px;
                    font-size: 12px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #3f3f46;
                    color: #ffffff;
                }
            """)
            try:
                self.web_view.page().runJavaScript("if (window.__av_unmute_audio) window.__av_unmute_audio();")
            except Exception:
                pass

    def _reload_game(self):
        self._load_retries = 0
        if self._autoboot_timer and self._autoboot_timer.isActive():
            self._autoboot_timer.stop()
        if hasattr(self, "error_card"):
            self.error_card.hide()
        if hasattr(self, "loading_overlay"):
            self.loading_overlay.show()
            self.loading_overlay.raise_()
        if hasattr(self, "loading_pbar"):
            self.loading_pbar.show()
        if hasattr(self, "loading_status_lbl"):
            self.loading_status_lbl.show()
            self.loading_status_lbl.setText(f"⚡ Preparing {self.platform_info['name']} WebAssembly Engine...")
        self.loading_bar.show()
        self.web_view.reload()

    def _toggle_fullscreen(self):
        self.is_custom_fullscreen = not self.is_custom_fullscreen
        if self.is_custom_fullscreen:
            self.showFullScreen()
            self.fs_btn.setText("⛶ Win")
        else:
            self.showNormal()
            self.fs_btn.setText("⛶ Full")

    def _on_html5_fullscreen(self, enabled: bool):
        if enabled:
            self.showFullScreen()
            self.header_bar.hide()
        else:
            self.showNormal()
            self.header_bar.show()

    def _open_in_browser(self):
        embed_url = f"https://archive.org/embed/{self.identifier}"
        webbrowser.open(embed_url)
