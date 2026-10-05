import ctypes
from ctypes import wintypes
import json
import math
import sys
import time
import webbrowser
from typing import Optional
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

    if any(k in id_lower for k in ("cpc", "amstrad", "6128", "464", "664")):
        default_cmd = "RUN\"GOBLINS" if "goblins" in id_lower else "RUN\"DISC"
        return {
            "name": "Amstrad CPC",
            "badge": "AMSTRAD CPC",
            "badge_color": "#0891b2",
            "default_cmd": default_cmd,
            "tip": "Amstrad CPC: Click screen & type RUN\"<NAME> (or CAT for disk files) then press Enter!"
        }
    if any(k in id_lower for k in ("zx_", "spectrum", "sinclair")):
        return {
            "name": "ZX Spectrum",
            "badge": "ZX SPECTRUM",
            "badge_color": "#d97706",
            "default_cmd": "LOAD \"\"",
            "tip": "ZX Spectrum: Press J for LOAD, then Symbol Shift + P twice for \"\" and Enter!"
        }
    if any(k in id_lower for k in ("c64", "commodore", "vic20", "plus-4")):
        return {
            "name": "Commodore 64",
            "badge": "C64",
            "badge_color": "#4f46e5",
            "default_cmd": "LOAD \"*\",8,1",
            "tip": "C64: Click screen & type LOAD \"*\",8,1 then Enter, then RUN!"
        }
    if any(k in id_lower for k in ("amiga", "a500", "a1200")):
        return {
            "name": "Amiga",
            "badge": "AMIGA",
            "badge_color": "#ea580c",
            "default_cmd": "",
            "tip": "Amiga: Insert floppy or let Workbench autoboot."
        }
    if any(k in id_lower for k in ("arcade", "mame", "fbn", "fbneo", "neogeo", "capcom", "cps1", "cps2", "cps3")):
        return {
            "name": "Arcade",
            "badge": "ARCADE",
            "badge_color": "#dc2626",
            "default_cmd": "",
            "tip": "Arcade: Press 5 or 6 to insert coins, 1 or 2 for Player Start!"
        }
    if any(k in id_lower for k in ("snes", "super_nintendo", "sfc", "nes", "famico", "n64", "gba", "gameboy", "gbc", "genesis", "megadrive", "hearto")):
        return {
            "name": "Console",
            "badge": "CONSOLE",
            "badge_color": "#7c3aed",
            "default_cmd": "",
            "tip": "Console: Use gamepad or keyboard controls to play."
        }
    if any(k in id_lower for k in ("atari", "a2600", "a7800")):
        return {
            "name": "Atari",
            "badge": "ATARI",
            "badge_color": "#b45309",
            "default_cmd": "",
            "tip": "Atari: Press F2 for Game Reset / Start."
        }
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

class GamepadPoller:
    """Zero-dependency Windows controller driver supporting XInput & DirectInput/WinMM."""
    def __init__(self):
        self.xi = None
        for dll in ["xinput1_4.dll", "xinput1_3.dll", "xinput9_1_0.dll"]:
            try:
                self.xi = ctypes.windll.LoadLibrary(dll)
                break
            except Exception:
                pass
        self.winmm = getattr(ctypes.windll, "winmm", None)
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

        # 1. Try XInput
        if self.xi:
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

        # 2. Try WinMM fallback if XInput didn't connect
        if not connected and self.winmm:
            try:
                class JOYINFOEX(ctypes.Structure):
                    _fields_ = [
                        ('dwSize', wintypes.DWORD),
                        ('dwFlags', wintypes.DWORD),
                        ('dwXpos', wintypes.DWORD),
                        ('dwYpos', wintypes.DWORD),
                        ('dwZpos', wintypes.DWORD),
                        ('dwRpos', wintypes.DWORD),
                        ('dwUpos', wintypes.DWORD),
                        ('dwVpos', wintypes.DWORD),
                        ('dwButtons', wintypes.DWORD),
                        ('dwButtonNumber', wintypes.DWORD),
                        ('dwPOV', wintypes.DWORD),
                        ('dwReserved1', wintypes.DWORD),
                        ('dwReserved2', wintypes.DWORD),
                    ]
                for i in range(4):
                    info = JOYINFOEX()
                    info.dwSize = ctypes.sizeof(JOYINFOEX)
                    info.dwFlags = 0xFF
                    if self.winmm.joyGetPosEx(i, ctypes.byref(info)) == 0:
                        connected = True
                        name = f"DirectInput Joystick {i + 1}"

                        norm_x = (info.dwXpos - 32767) / 32767.0
                        norm_y = (info.dwYpos - 32767) / 32767.0
                        axes[0] = round(norm_x, 3)
                        axes[1] = round(norm_y, 3)

                        if info.dwXpos < 18000:
                            keys.add(('ArrowLeft', 'ArrowLeft', 37))
                        elif info.dwXpos > 47000:
                            keys.add(('ArrowRight', 'ArrowRight', 39))
                        if info.dwYpos < 18000:
                            keys.add(('ArrowUp', 'ArrowUp', 38))
                        elif info.dwYpos > 47000:
                            keys.add(('ArrowDown', 'ArrowDown', 40))

                        for b_idx in range(16):
                            if info.dwButtons & (1 << b_idx):
                                buttons[b_idx] = 1.0

                        if info.dwButtons & 0x01:
                            keys.add(('Control', 'ControlLeft', 17))
                            m_left = True
                        if info.dwButtons & 0x02:
                            keys.add(('Alt', 'AltLeft', 18))
                            m_right = True
                        if info.dwButtons & 0x04:
                            keys.add((' ', 'Space', 32))
                        if info.dwButtons & 0x08:
                            keys.add(('Shift', 'ShiftLeft', 16))
                        if info.dwButtons & 0x10:
                            keys.add(('Enter', 'Enter', 13))
                        if info.dwButtons & 0x20:
                            keys.add(('Escape', 'Escape', 27))
                        break
            except Exception:
                pass

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
        self._gamepad_timer = QTimer(self)
        self._gamepad_timer.setInterval(16)
        self._gamepad_timer.timeout.connect(self._poll_gamepad)
        self._gamepad_timer.start()

        self._init_ui()
        self._setup_shortcuts()
        self._fetch_emulator_metadata()
        self._load_game()

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
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #991b1b;
                color: #ffffff;
                border: 1px solid #b91c1c;
                border-radius: 5px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
        """)
        self.close_btn.setToolTip("Close game and return to ArchiveVault")
        self.close_btn.clicked.connect(self.close)
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
        self.web_page.fullscreen_toggled.connect(self._on_html5_fullscreen)

        # Early CSS & Gamepad injection via QWebEngineScript at DocumentCreation
        early_script = QWebEngineScript()
        early_script.setName("av_early_suppress")
        early_script.setSourceCode("""
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
            # Let the game / webview receive Esc to free mouse or handle in-game pause menu without closing dialog
            event.ignore()
            return
        super().keyPressEvent(event)

    def reject(self):
        self._shutdown()
        super().reject()

    def closeEvent(self, event):
        self._shutdown()
        event.accept()
        super().closeEvent(event)

    def _shutdown(self):
        if hasattr(self, "_gamepad_timer") and self._gamepad_timer.isActive():
            self._gamepad_timer.stop()
        if self._autoboot_timer and self._autoboot_timer.isActive():
            self._autoboot_timer.stop()
        try:
            self.web_page.setAudioMuted(True)
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
        if not hasattr(self, "gamepad_poller"):
            return
        try:
            state = self.gamepad_poller.poll()
            connected = state["connected"]
            name = state["name"]
            active_keys = state["active_keys_count"]
            changed = state["changed"]

            if connected != self._last_gamepad_state or active_keys > 0:
                self._last_gamepad_state = connected
                if connected:
                    if active_keys > 0:
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

            if changed and connected:
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
                    border-radius: 10px;
                    padding: 20px;
                    max-width: 520px;
                }
            """)
            err_layout = QVBoxLayout(self.error_card)
            err_layout.setSpacing(14)

            self.err_badge = QLabel("❌ Online Emulation Not Found")
            self.err_badge.setStyleSheet("color: #ef4444; font-size: 16px; font-weight: 800; background: transparent;")
            self.err_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            err_layout.addWidget(self.err_badge)

            self.err_msg_lbl = QLabel()
            self.err_msg_lbl.setStyleSheet("color: #d4d4d8; font-size: 12px; line-height: 1.5; background: transparent;")
            self.err_msg_lbl.setWordWrap(True)
            err_layout.addWidget(self.err_msg_lbl)

            btn_box = QHBoxLayout()
            btn_box.setSpacing(10)
            btn_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

            from archivevault.core.utils import get_launchbox_path, launch_launchbox
            lb_path = get_launchbox_path()
            if lb_path:
                self.btn_err_lb = QPushButton("Open LaunchBox 🚀")
                self.btn_err_lb.setStyleSheet("background-color: #3b82f6; color: #ffffff; font-weight: 700; padding: 6px 14px; border-radius: 5px;")
                self.btn_err_lb.clicked.connect(lambda: (launch_launchbox(), self.close()))
                btn_box.addWidget(self.btn_err_lb)

            self.btn_err_web = QPushButton("View on Archive.org 🌐")
            self.btn_err_web.setStyleSheet("background-color: #27272a; color: #60a5fa; font-weight: 600; padding: 6px 12px; border: 1px solid #3f3f46; border-radius: 5px;")
            self.btn_err_web.clicked.connect(self._open_in_browser)
            btn_box.addWidget(self.btn_err_web)

            self.btn_err_close = QPushButton("Close ✕")
            self.btn_err_close.setStyleSheet("background-color: #3f3f46; color: #ffffff; font-weight: 600; padding: 6px 14px; border-radius: 5px;")
            self.btn_err_close.clicked.connect(self.close)
            btn_box.addWidget(self.btn_err_close)

            err_layout.addLayout(btn_box)
            self.loading_overlay.layout().addWidget(self.error_card)

        self.err_badge.setText(f"❌ {title}")
        self.err_msg_lbl.setText(message)
        self.error_card.show()
        self.loading_overlay.show()
        self.loading_overlay.raise_()

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
        self.web_view.setUrl(QUrl(embed_url))

    def _on_load_progress(self, progress: int):
        self.loading_bar.setValue(progress)

    def _on_load_finished(self, success: bool):
        self.loading_bar.hide()
        if success:
            self._inject_center_styling()
            self._apply_easy_crt()
            self._apply_aspect_mode()
            self._start_autoboot_poller()
        else:
            self._show_emulation_error_card(
                title="Page Load Failed",
                message=(
                    f"Could not connect to Internet Archive for <b>'{self.identifier}'</b>.<br><br>"
                    "Please check your internet connection or verify this item on archive.org."
                )
            )
        self.web_view.setFocus()

    def _start_autoboot_poller(self):
        """Poll the page until the WebAssembly DOSBox engine boots and canvas is running."""
        if self._autoboot_timer and self._autoboot_timer.isActive():
            self._autoboot_timer.stop()
        self._autoboot_attempts = 0
        self._autoboot_timer = QTimer(self)
        self._autoboot_timer.setInterval(400)
        self._autoboot_timer.timeout.connect(self._poll_autoboot)
        self._autoboot_timer.start()

    def _poll_autoboot(self):
        self._autoboot_attempts += 1
        if self._autoboot_attempts > 120:  # Allow up to 60 seconds
            if self._autoboot_timer:
                self._autoboot_timer.stop()
            self._show_emulation_error_card(
                title="Emulation Timed Out",
                message=(
                    f"The game <b>'{self.identifier}'</b> did not start rendering within 60 seconds.<br><br>"
                    "Internet Archive may be experiencing high server load, or this item may require local emulation."
                )
            )
            return

        def on_result(res):
            if not res:
                if self._autoboot_attempts >= 15:
                    self._show_emulation_error_card(
                        title="Online Emulation Not Available",
                        message=(
                            f"<b>'{self.identifier}'</b> does not have an in-browser WebAssembly emulator configured on the Internet Archive.<br><br>"
                            "Offline MAME and local ROMs should be played through <b>LaunchBox</b> with local arcade cores."
                        )
                    )
                return

            if isinstance(res, dict):
                status = res.get('status')
                splash = res.get('splash')

                if status == 'no_emulator' or res.get('is404'):
                    if self._autoboot_attempts >= 8:  # give ~3.2 seconds
                        self._show_emulation_error_card(
                            title="Online Emulation Not Available",
                            message=(
                                f"<b>'{self.identifier}'</b> does not have an in-browser WebAssembly emulator on the Internet Archive.<br><br>"
                                "This happens when opening an offline ROM file (like MAME non-merged zips) rather than a pre-configured Internet Arcade game."
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
                            bubbles: true,
                            cancelable: true,
                            view: window
                        });
                        try {
                            Object.defineProperty(kev, 'keyCode', { get: function() { return item[3]; } });
                            Object.defineProperty(kev, 'which', { get: function() { return item[3]; } });
                        } catch(e) {}
                        if (canK) canK.dispatchEvent(kev);
                        document.dispatchEvent(kev);
                        window.dispatchEvent(kev);
                    }
                }
            };

            // --- Pointer Lock Setup for Mouse-Controlled Retro Games ---
            function setupPointerLock() {
                var can = document.getElementById('canvas');
                var holder = document.getElementById('canvasholder');
                var target = can || holder;
                if (target && !target.__av_mouse_bound) {
                    target.__av_mouse_bound = true;
                    target.addEventListener('click', function() {
                        if (target.requestPointerLock && document.pointerLockElement !== target) {
                            try { target.requestPointerLock(); } catch(e) {}
                        }
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

            // --- Main Auto-Boot Trigger ---
            if (window.__av_boot_dispatched === undefined) {
                window.__av_boot_dispatched = false;
            }
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
                        return { status: 'running', w: can.width, h: can.height };
                    }

                    // 2. Click start button as soon as Archive.org jQuery handler is ready
                    if (window.$ && window.$._data && btn) {
                        var evData = window.$._data(btn, 'events');
                        if (evData && evData.click && evData.click.length > 0) {
                            if (!window.__av_boot_dispatched) {
                                window.__av_boot_dispatched = true;
                                window.$(btn).trigger('click');
                            }
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

    def _reload_game(self):
        if self._autoboot_timer and self._autoboot_timer.isActive():
            self._autoboot_timer.stop()
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
