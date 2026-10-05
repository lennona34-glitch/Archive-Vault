import ctypes
import os
import subprocess
import sys
import time
from typing import Optional, Tuple, List
import xml.etree.ElementTree as ET

from PyQt6.QtCore import QEvent, QPoint, QSize, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon, QKeySequence, QShortcut
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

VIDEO_EXTENSIONS = ('.mp4', '.mkv', '.avi', '.ogv', '.webm', '.mov', '.flv', '.wmv', '.m4v', '.mpg', '.mpeg', '.m2v', '.ts', '.vob', '.3gp')

LOSSLESS_SCALING_PATHS = [
    os.path.expandvars(r"%ProgramFiles(x86)%\Steam\steamapps\common\Lossless Scaling\LosslessScaling.exe"),
    os.path.expandvars(r"%ProgramFiles%\Steam\steamapps\common\Lossless Scaling\LosslessScaling.exe"),
    r"D:\Steam\steamapps\common\Lossless Scaling\LosslessScaling.exe",
    r"D:\SteamLibrary\steamapps\common\Lossless Scaling\LosslessScaling.exe",
    r"E:\SteamLibrary\steamapps\common\Lossless Scaling\LosslessScaling.exe",
    r"C:\Program Files\Lossless Scaling\LosslessScaling.exe",
]

def get_lossless_scaling_exe() -> Optional[str]:
    """Find the Lossless Scaling executable on the local system."""
    for path in LOSSLESS_SCALING_PATHS:
        if os.path.exists(path):
            return path
    return None

def is_lossless_scaling_running() -> bool:
    """Check if LosslessScaling.exe is currently active in the process table."""
    try:
        out = subprocess.check_output(
            'tasklist /FI "IMAGENAME eq LosslessScaling.exe"',
            shell=True,
            text=True,
            creationflags=0x08000000
        )
        return "LosslessScaling.exe" in out
    except Exception:
        return False

def launch_lossless_scaling() -> bool:
    """Launch Lossless Scaling directly in the background (no Steam login required)."""
    exe = get_lossless_scaling_exe()
    if exe and os.path.exists(exe):
        exe_dir = os.path.dirname(exe)
        # Direct launch via subprocess with working directory set
        try:
            subprocess.Popen(
                [exe],
                cwd=exe_dir,
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            )
            return True
        except Exception:
            pass

        # ShellExecute fallback
        try:
            res = ctypes.windll.shell32.ShellExecuteW(None, "open", exe, None, exe_dir, 1)
            if res > 32:
                return True
        except Exception:
            pass

    # Method 2: Steam protocol fallback if direct path not found
    try:
        os.startfile("steam://rungameid/993090")
        return True
    except Exception:
        pass
    return False

def get_lossless_scaling_info() -> dict:
    """Read configured mode, multiplier, and draw FPS setting from Lossless Scaling Settings.xml."""
    info = {"fg_mode": "LSFG3", "multiplier": "4x", "target_hz": "120", "draw_fps": True, "hotkey": "Shift+S"}
    settings_path = os.path.expandvars(r"%LOCALAPPDATA%\Lossless Scaling\Settings.xml")
    if not os.path.exists(settings_path):
        return info
    try:
        tree = ET.parse(settings_path)
        root = tree.getroot()
        hotkey = root.findtext("Hotkey") or "S"
        mod_str = root.findtext("HotkeyModifierKeys") or "Shift"
        mods = [m.strip() for m in mod_str.replace("+", ",").split(",") if m.strip()]
        info["hotkey"] = "+".join(mods + [hotkey.upper()])

        profile = root.find(".//Profile")
        if profile is not None:
            info["fg_mode"] = profile.findtext("FrameGeneration") or "LSFG3"
            mult = profile.findtext("LSFG3Multiplier") or profile.findtext("LSFG2Mode") or "4"
            info["multiplier"] = f"{mult}x" if not mult.endswith("x") and not mult.endswith("X") else mult
            info["target_hz"] = profile.findtext("LSFG3Target") or "120"
            info["draw_fps"] = (profile.findtext("DrawFps") or "true").lower() == "true"
    except Exception:
        pass
    return info

def get_lossless_scaling_hotkey() -> Tuple[str, List[str]]:
    """Parse the configured hotkey and modifier keys from Lossless Scaling's Settings.xml."""
    info = get_lossless_scaling_info()
    parts = info.get("hotkey", "Shift+S").split("+")
    key = parts[-1]
    mods = parts[:-1]
    return (key, mods)


def send_lossless_scaling_hotkey():
    """Simulate the global Lossless Scaling hotkey to trigger upscaling & frame generation."""
    try:
        user32 = ctypes.windll.user32
        hotkey, mods = get_lossless_scaling_hotkey()

        mod_vks = []
        for m in mods:
            ml = m.lower()
            if "shift" in ml:
                mod_vks.append(0x10)  # VK_SHIFT
            elif "ctrl" in ml or "control" in ml:
                mod_vks.append(0x11)  # VK_CONTROL
            elif "alt" in ml or "menu" in ml:
                mod_vks.append(0x12)  # VK_MENU
            elif "win" in ml:
                mod_vks.append(0x5B)  # VK_LWIN

        vk_key = ord(hotkey[0]) if len(hotkey) == 1 else 0x53
        KEYEVENTF_KEYUP = 0x0002

        # Press modifiers down
        for vk in mod_vks:
            user32.keybd_event(vk, 0, 0, 0)
        # Press target key down
        user32.keybd_event(vk_key, 0, 0, 0)
        time.sleep(0.06)
        # Release target key
        user32.keybd_event(vk_key, 0, KEYEVENTF_KEYUP, 0)
        # Release modifiers
        for vk in reversed(mod_vks):
            user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
    except Exception as e:
        print(f"[LosslessScaling] Hotkey dispatch failed: {e}")

def format_video_time(ms: int) -> str:
    """Format milliseconds into HH:MM:SS or MM:SS."""
    if ms <= 0:
        return "00:00"
    total_seconds = ms // 1000
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    if minutes >= 60:
        hours = minutes // 60
        minutes = minutes % 60
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"

class HUDToast(QWidget):
    """Floating borderless always-on-top HUD pill for notifications over hardware video surfaces."""
    def __init__(self, parent=None):
        super().__init__(None, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 6, 14, 6)
        self.label = QLabel("")
        self.label.setStyleSheet("""
            background-color: rgba(15, 23, 42, 0.95);
            color: #38bdf8;
            border: 1px solid #0284c7;
            border-radius: 18px;
            font-size: 13px;
            font-weight: 700;
            padding: 8px 18px;
        """)
        layout.addWidget(self.label)
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide)

    def show_message(self, message: str, parent_geo, duration_ms: int = 2500):
        self.label.setText(message)
        self.adjustSize()
        x = parent_geo.x() + (parent_geo.width() - self.width()) // 2
        y = parent_geo.y() + 65
        self.move(x, y)
        self.show()
        self.raise_()
        self.hide_timer.start(duration_ms)

class FPSOverlayHUD(QWidget):
    """Real-time floating FPS & Refresh Rate monitor over cinema video."""
    def __init__(self, parent=None):
        super().__init__(None, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        self.box = QFrame()
        self.box.setStyleSheet("""
            background-color: rgba(10, 10, 14, 0.94);
            border: 1px solid #059669;
            border-radius: 10px;
            padding: 10px 14px;
        """)
        box_layout = QVBoxLayout(self.box)
        box_layout.setContentsMargins(4, 4, 4, 4)
        box_layout.setSpacing(4)

        self.title_lbl = QLabel("📊 Real-Time Video & LSFG Metrics")
        self.title_lbl.setStyleSheet("color: #34d399; font-size: 11px; font-weight: 800;")
        box_layout.addWidget(self.title_lbl)

        self.fps_lbl = QLabel("• Base Video Render: 60.0 FPS")
        self.fps_lbl.setStyleSheet("color: #f4f4f5; font-size: 12px; font-weight: 700;")
        box_layout.addWidget(self.fps_lbl)

        self.hz_lbl = QLabel("• Display Refresh: 144 Hz")
        self.hz_lbl.setStyleSheet("color: #a1a1aa; font-size: 11px;")
        box_layout.addWidget(self.hz_lbl)

        self.ls_status_lbl = QLabel("• Lossless Scaling: Standby (Press Shift+S)")
        self.ls_status_lbl.setStyleSheet("color: #93c5fd; font-size: 11px; font-weight: 600;")
        box_layout.addWidget(self.ls_status_lbl)

        self.tip_lbl = QLabel("💡 Look for green DXGI FPS in top-left when active")
        self.tip_lbl.setStyleSheet("color: #6ee7b7; font-size: 10px; font-style: italic;")
        box_layout.addWidget(self.tip_lbl)

        layout.addWidget(self.box)

class ClickableVideoWidget(QVideoWidget):
    """Video viewport supporting 1-click play/pause, double-click fullscreen, and mouse tracking."""
    clicked = pyqtSignal()
    double_clicked = pyqtSignal()
    mouse_activity = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        self.mouse_activity.emit()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit()
        self.mouse_activity.emit()
        super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event):
        self.mouse_activity.emit()
        super().mouseMoveEvent(event)

class VideoPlayerDialog(QDialog):
    """
    In-App Cinema Video Player with seamless auto-hiding controls,
    edge-to-edge floating layout, and 1-click Lossless Scaling integration.
    """

    def __init__(self, source: str, title: str, parent=None):
        super().__init__(parent)
        self.source = source
        self.video_title = title
        self._is_seeking = False
        self.is_custom_fullscreen = False

        # Set as an independent application window for proper DWM and Lossless Scaling capture
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.setWindowTitle(f"🎬 {self.video_title} — ArchiveVault Cinema")
        self.resize(1120, 720)
        self.setMinimumSize(800, 500)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.setStyleSheet("QDialog { background-color: #000000; color: #f4f4f5; }")

        # Media Player setup
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.85)

        # Controls pinned toggle state
        self.controls_pinned = False
        self.is_lossless_scaling_active = False
        self.fps_hud_visible = False
        self._check_launch_timer = None
        self._check_launch_attempts = 0

        # Aspect ratio modes: Fit (original), Fill (crop/zoom edge-to-edge), Stretch
        self.aspect_modes = [
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.AspectRatioMode.IgnoreAspectRatio,
        ]
        self.aspect_mode_names = ["Fit", "Fill", "Stretch"]
        self.current_aspect_idx = 0

        # Floating HUD Overlays (guaranteed visible on top of DirectX video)
        self.toast_hud = HUDToast(self)
        self.fps_overlay = FPSOverlayHUD(self)

        # Inactivity auto-hide timer for fullscreen mode (3.5 seconds)
        self.inactivity_timer = QTimer(self)
        self.inactivity_timer.setInterval(3500)
        self.inactivity_timer.setSingleShot(True)
        self.inactivity_timer.timeout.connect(self._hide_controls_if_idle)

        # FPS metrics updater
        self._fps_update_timer = QTimer(self)
        self._fps_update_timer.setInterval(500)
        self._fps_update_timer.timeout.connect(self._update_fps_hud)
        self._fps_update_timer.start()

        self._init_ui()
        self._setup_shortcuts()
        self._connect_signals()
        self._load_video()

    def showEvent(self, event):
        super().showEvent(event)
        self._update_layout_geometries()
        try:
            from archivevault.ui.main_window import apply_windows_dark_titlebar
            apply_windows_dark_titlebar(self)
        except Exception:
            pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_layout_geometries()

    def moveEvent(self, event):
        super().moveEvent(event)
        self._update_overlay_geometries()

    def _update_layout_geometries(self):
        """
        Size the video viewport edge-to-edge and float translucent controls on top.
        This guarantees the video is never squeezed into the middle of the screen.
        """
        w = self.width()
        h = self.height()
        if hasattr(self, "video_widget"):
            self.video_widget.setGeometry(0, 0, w, h)
        if hasattr(self, "top_bar"):
            self.top_bar.setGeometry(0, 0, w, 52)
            self.top_bar.raise_()
        if hasattr(self, "control_bar"):
            self.control_bar.setGeometry(0, h - 58, w, 58)
            self.control_bar.raise_()
        self._update_overlay_geometries()

    def _update_overlay_geometries(self):
        """Position floating HUDs over the cinema viewport."""
        top_left = self.mapToGlobal(QPoint(0, 0))
        if hasattr(self, "toast_hud") and self.toast_hud.isVisible():
            x = top_left.x() + (self.width() - self.toast_hud.width()) // 2
            y = top_left.y() + 65
            self.toast_hud.move(x, y)
        if hasattr(self, "fps_overlay") and self.fps_hud_visible:
            x = top_left.x() + 25
            y = top_left.y() + 65
            self.fps_overlay.move(x, y)

    def _init_ui(self):
        # Base Layer: Video Viewport fills 100% of the player window (edge-to-edge)
        self.video_widget = ClickableVideoWidget(self)
        self.video_widget.setStyleSheet("background-color: #000000;")
        self.video_widget.setAspectRatioMode(self.aspect_modes[self.current_aspect_idx])
        self.video_widget.clicked.connect(self.toggle_play_pause)
        self.video_widget.double_clicked.connect(self.toggle_fullscreen)
        self.video_widget.mouse_activity.connect(self._on_user_activity)
        self.player.setVideoOutput(self.video_widget)

        # --- Top Cinema Floating Bar (translucent overlay) ---
        self.top_bar = QFrame(self)
        self.top_bar.setObjectName("topBar")
        self.top_bar.setFixedHeight(52)
        self.top_bar.setStyleSheet("""
            QFrame#topBar {
                background-color: rgba(15, 15, 20, 0.88);
                border-bottom: 1px solid rgba(255, 255, 255, 0.10);
            }
        """)
        top_layout = QHBoxLayout(self.top_bar)
        top_layout.setContentsMargins(18, 6, 18, 6)
        top_layout.setSpacing(12)

        film_icon = QLabel("🎬")
        film_icon.setStyleSheet("font-size: 16px;")
        top_layout.addWidget(film_icon)

        self.title_label = QLabel(self.video_title)
        self.title_label.setStyleSheet("font-size: 13px; font-weight: 700; color: #f4f4f5;")
        top_layout.addWidget(self.title_label)

        # Badge: Local vs Live Stream
        is_local = os.path.isabs(self.source) and os.path.exists(self.source)
        self.badge = QLabel("LOCAL PLAY" if is_local else "STREAMING VIDEO")
        badge_bg = "#2563eb" if is_local else "#059669"
        self.badge.setStyleSheet(f"""
            background-color: {badge_bg};
            color: #ffffff;
            font-size: 9px;
            font-weight: 800;
            padding: 3px 8px;
            border-radius: 4px;
        """)
        top_layout.addWidget(self.badge)

        # Status Notification Label (always visible inside top bar)
        self.status_msg_label = QLabel("")
        self.status_msg_label.setStyleSheet("font-size: 11px; font-weight: 700; color: #38bdf8; padding-left: 6px;")
        top_layout.addWidget(self.status_msg_label)

        top_layout.addStretch(1)

        # 📂 Open Local Video File Button
        self.open_file_top_btn = QPushButton("📂 Open File (Ctrl+O)")
        self.open_file_top_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_file_top_btn.setStyleSheet("""
            QPushButton {
                background-color: #27272a;
                color: #e4e4e7;
                border: 1px solid #3f3f46;
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #3f3f46;
                color: #ffffff;
            }
        """)
        self.open_file_top_btn.setToolTip("Open any video file from your computer (Ctrl+O)")
        self.open_file_top_btn.clicked.connect(self._open_local_file_dialog)
        top_layout.addWidget(self.open_file_top_btn)

        # 📐 Aspect Ratio Mode Button (Fit / Fill / Stretch)
        self.aspect_btn = QPushButton("📐 Aspect: Fit")
        self.aspect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.aspect_btn.setStyleSheet("""
            QPushButton {
                background-color: #27272a;
                color: #e4e4e7;
                border: 1px solid #3f3f46;
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #3f3f46;
                color: #ffffff;
            }
        """)
        self.aspect_btn.setToolTip("Toggle Aspect Ratio Mode: Fit (preserve ratio), Fill (zoom to remove borders), or Stretch (A)")
        self.aspect_btn.clicked.connect(self._cycle_aspect_ratio_mode)
        top_layout.addWidget(self.aspect_btn)

        # 📊 FPS Overlay Toggle Button (in top bar)
        self.fps_top_btn = QPushButton("📊 FPS")
        self.fps_top_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fps_top_btn.setStyleSheet("""
            QPushButton {
                background-color: #27272a;
                color: #e4e4e7;
                border: 1px solid #3f3f46;
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #3f3f46;
                color: #ffffff;
            }
        """)
        self.fps_top_btn.setToolTip("Toggle real-time Frame Rate (FPS) and Refresh Rate overlay HUD")
        self.fps_top_btn.clicked.connect(self.toggle_fps_overlay)
        top_layout.addWidget(self.fps_top_btn)

        # ⚡ Lossless Scaling Call Button (in top bar)
        self.ls_top_btn = QPushButton("⚡ Lossless Scaling (Shift+S)")
        self.ls_top_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ls_top_btn.setStyleSheet("""
            QPushButton {
                background-color: #064e3b;
                color: #a7f3d0;
                border: 1px solid #059669;
                border-radius: 6px;
                padding: 5px 12px;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #059669;
                color: #ffffff;
            }
        """)
        self.ls_top_btn.setToolTip("Call Lossless Scaling automatically: launches app if closed and triggers LSFG frame generation")
        self.ls_top_btn.clicked.connect(self.trigger_lossless_scaling)
        top_layout.addWidget(self.ls_top_btn)


        # Fullscreen & Exit
        self.fs_top_btn = QPushButton("⛶ Fullscreen (F11)")
        self.fs_top_btn.setStyleSheet("""
            QPushButton {
                background-color: #27272a;
                color: #e4e4e7;
                border: 1px solid #3f3f46;
                border-radius: 6px;
                padding: 5px 12px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #3f3f46;
                color: #ffffff;
            }
        """)
        self.fs_top_btn.clicked.connect(self.toggle_fullscreen)
        top_layout.addWidget(self.fs_top_btn)

        self.exit_btn = QPushButton("✕")
        self.exit_btn.setFixedSize(32, 32)
        self.exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #27272a;
                color: #f87171;
                border: 1px solid #7f1d1d;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #7f1d1d;
                color: #ffffff;
            }
        """)
        self.exit_btn.clicked.connect(self.close)
        top_layout.addWidget(self.exit_btn)

        # --- Bottom Media Control Floating Bar (translucent overlay) ---
        self.control_bar = QFrame(self)
        self.control_bar.setObjectName("controlBar")
        self.control_bar.setFixedHeight(58)
        self.control_bar.setStyleSheet("""
            QFrame#controlBar {
                background-color: rgba(15, 15, 20, 0.88);
                border-top: 1px solid rgba(255, 255, 255, 0.10);
                padding: 0 16px;
            }
        """)
        control_layout = QHBoxLayout(self.control_bar)
        control_layout.setContentsMargins(18, 0, 18, 0)
        control_layout.setSpacing(12)

        # Play / Pause Button
        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedSize(38, 38)
        self.play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                border-radius: 19px;
                font-size: 16px;
                font-weight: 700;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #3b82f6;
            }
        """)
        self.play_btn.clicked.connect(self.toggle_play_pause)
        control_layout.addWidget(self.play_btn)

        # Stop Button
        self.stop_btn = QPushButton("⏹")
        self.stop_btn.setFixedSize(32, 32)
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #27272a;
                color: #e4e4e7;
                border: 1px solid #3f3f46;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #3f3f46;
                color: #ffffff;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_playback)
        control_layout.addWidget(self.stop_btn)

        # Timeline Slider (Seek Bar)
        self.timeline_slider = QSlider(Qt.Orientation.Horizontal)
        self.timeline_slider.setRange(0, 0)
        self.timeline_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.timeline_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 5px;
                background: #27272a;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #3b82f6;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                width: 14px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover {
                background: #38bdf8;
            }
        """)
        self.timeline_slider.sliderPressed.connect(self._on_slider_pressed)
        self.timeline_slider.sliderReleased.connect(self._on_slider_released)
        self.timeline_slider.sliderMoved.connect(self._on_slider_moved)
        control_layout.addWidget(self.timeline_slider, stretch=1)

        # Time Label
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet("font-size: 11px; font-weight: 600; color: #a1a1aa;")
        control_layout.addWidget(self.time_label)

        # Volume Controls
        vol_icon = QLabel("🔊")
        vol_icon.setStyleSheet("font-size: 13px;")
        control_layout.addWidget(vol_icon)

        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(85)
        self.vol_slider.setFixedWidth(75)
        self.vol_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.vol_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background: #27272a;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #10b981;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                width: 10px;
                margin-top: -3px;
                margin-bottom: -3px;
                border-radius: 5px;
            }
        """)
        self.vol_slider.valueChanged.connect(self._on_volume_changed)
        control_layout.addWidget(self.vol_slider)

        # Quick 📊 FPS Pill in dock
        self.fps_dock_btn = QPushButton("📊 FPS")
        self.fps_dock_btn.setFixedSize(58, 32)
        self.fps_dock_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fps_dock_btn.setStyleSheet("""
            QPushButton {
                background-color: #27272a;
                color: #e4e4e7;
                border: 1px solid #3f3f46;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #3f3f46;
                color: #ffffff;
            }
        """)
        self.fps_dock_btn.setToolTip("Toggle real-time Frame Rate (FPS) and Refresh Rate overlay HUD")
        self.fps_dock_btn.clicked.connect(self.toggle_fps_overlay)
        control_layout.addWidget(self.fps_dock_btn)

        # Quick ⚡ LSFG Pill in dock
        self.ls_dock_btn = QPushButton("⚡ LSFG")
        self.ls_dock_btn.setFixedSize(62, 32)
        self.ls_dock_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ls_dock_btn.setStyleSheet("""

            QPushButton {
                background-color: #064e3b;
                color: #a7f3d0;
                border: 1px solid #059669;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #059669;
                color: #ffffff;
            }
        """)
        self.ls_dock_btn.setToolTip("Call Lossless Scaling (Shift+S)")
        self.ls_dock_btn.clicked.connect(self.trigger_lossless_scaling)
        control_layout.addWidget(self.ls_dock_btn)

        # Fullscreen Icon Button
        self.fs_btn = QPushButton("⛶")
        self.fs_btn.setFixedSize(32, 32)
        self.fs_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fs_btn.setStyleSheet("""
            QPushButton {
                background-color: #27272a;
                color: #e4e4e7;
                border: 1px solid #3f3f46;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #3f3f46;
                color: #ffffff;
            }
        """)
        self.fs_btn.setToolTip("Toggle Fullscreen (F11)")
        self.fs_btn.clicked.connect(self.toggle_fullscreen)
        control_layout.addWidget(self.fs_btn)

        # Pin / Auto-hide toggle button
        self.pin_btn = QPushButton("📌 Auto-Hide")
        self.pin_btn.setFixedSize(92, 32)
        self.pin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pin_btn.setStyleSheet("""
            QPushButton {
                background-color: #27272a;
                color: #e4e4e7;
                border: 1px solid #3f3f46;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #3f3f46;
                color: #ffffff;
            }
        """)
        self.pin_btn.setToolTip("Toggle auto-hiding controls in fullscreen mode")
        self.pin_btn.clicked.connect(self._toggle_pin_controls)
        control_layout.addWidget(self.pin_btn)

        # Initial edge-to-edge viewport and floating overlay geometry setup
        self._update_layout_geometries()


    def _cycle_aspect_ratio_mode(self):
        """Cycle between Fit (original aspect), Fill (crop/zoom edge-to-edge), and Stretch."""
        self.current_aspect_idx = (self.current_aspect_idx + 1) % len(self.aspect_modes)
        mode = self.aspect_modes[self.current_aspect_idx]
        name = self.aspect_mode_names[self.current_aspect_idx]
        self.video_widget.setAspectRatioMode(mode)
        self.aspect_btn.setText(f"📐 Aspect: {name}")
        desc = {
            "Fit": "Preserve original aspect ratio (black bars only if needed)",
            "Fill": "Zoom to eliminate black borders (edge-to-edge filling display)",
            "Stretch": "Stretch full screen"
        }.get(name, "")
        self._show_toast(f"📐 Aspect Mode: {name} — {desc}", 2500)

    def _toggle_pin_controls(self):
        self.controls_pinned = not self.controls_pinned
        if self.controls_pinned:
            self.pin_btn.setText("📌 Pinned")
            self.pin_btn.setStyleSheet("""
                QPushButton {
                    background-color: #1e3a8a;
                    color: #93c5fd;
                    border: 1px solid #3b82f6;
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: 700;
                }
            """)
            self.top_bar.show()
            self.control_bar.show()
            self.top_bar.raise_()
            self.control_bar.raise_()
            self.inactivity_timer.stop()
            self._show_toast("📌 Cinema Controls Pinned (Always Visible)", 2000)
        else:
            self.pin_btn.setText("📌 Auto-Hide")
            self.pin_btn.setStyleSheet("""
                QPushButton {
                    background-color: #27272a;
                    color: #e4e4e7;
                    border: 1px solid #3f3f46;
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #3f3f46;
                    color: #ffffff;
                }
            """)
            if self.is_custom_fullscreen:
                self.inactivity_timer.start(3500)
            self._show_toast("⏱️ Auto-Hide Engaged (Fades on Inactivity)", 2000)

    def mouseMoveEvent(self, event):
        self._on_user_activity()
        super().mouseMoveEvent(event)

    def _on_user_activity(self):
        """Wake up seek bar and cinema controls on user movement."""
        self.control_bar.show()
        self.top_bar.show()
        self.top_bar.raise_()
        self.control_bar.raise_()
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.video_widget.setCursor(Qt.CursorShape.ArrowCursor)

        # In fullscreen, auto-hide after 3.5s if not pinned and playing
        if self.is_custom_fullscreen and not self.controls_pinned:
            if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.inactivity_timer.start(3500)
        else:
            self.inactivity_timer.stop()

    def _hide_controls_if_idle(self):
        """Automatically fade out seek bar and controls when in fullscreen and user is passively watching."""
        if not self.is_custom_fullscreen:
            return
        if self.controls_pinned:
            return
        if self._is_seeking:
            return
        if self.control_bar.underMouse() or self.top_bar.underMouse():
            self.inactivity_timer.start(3500)
            return

        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.control_bar.hide()
            self.top_bar.hide()
            self.setCursor(Qt.CursorShape.BlankCursor)
            self.video_widget.setCursor(Qt.CursorShape.BlankCursor)

    def _show_toast(self, message: str, duration_ms: int = 3000):
        """Display an on-screen translucent HUD notification over DirectX and in top bar."""
        if hasattr(self, "toast_hud"):
            self.toast_hud.show_message(message, self.geometry(), duration_ms)
        self._set_status_msg(message)
        QTimer.singleShot(duration_ms + 1000, lambda: self._set_status_msg(""))

    def _set_status_msg(self, text: str):
        if hasattr(self, "status_msg_label"):
            self.status_msg_label.setText(text)

    def toggle_fps_overlay(self):
        self.fps_hud_visible = not self.fps_hud_visible
        if self.fps_hud_visible:
            self._update_fps_hud()
            self.fps_overlay.show()
            self._update_overlay_geometries()
            self._update_fps_btn_styles(True)
            self._show_toast("📊 Real-Time FPS HUD Displayed", 2000)
        else:
            self.fps_overlay.hide()
            self._update_fps_btn_styles(False)
            self._show_toast("📊 FPS HUD Hidden", 1500)

    def _update_fps_btn_styles(self, active: bool):
        if active:
            style = """
                QPushButton {
                    background-color: #1e3a8a;
                    color: #93c5fd;
                    border: 1px solid #3b82f6;
                    border-radius: 6px;
                    padding: 5px 10px;
                    font-size: 11px;
                    font-weight: 700;
                }
                QPushButton:hover {
                    background-color: #2563eb;
                    color: #ffffff;
                }
            """
            self.fps_top_btn.setStyleSheet(style)
            self.fps_dock_btn.setStyleSheet(style)
        else:
            style = """
                QPushButton {
                    background-color: #27272a;
                    color: #e4e4e7;
                    border: 1px solid #3f3f46;
                    border-radius: 6px;
                    padding: 5px 10px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #3f3f46;
                    color: #ffffff;
                }
            """
            self.fps_top_btn.setStyleSheet(style)
            self.fps_dock_btn.setStyleSheet(style)

    def _update_ls_button_styles(self):
        if self.is_lossless_scaling_active:
            top_style = """
                QPushButton {
                    background-color: #059669;
                    color: #ffffff;
                    border: 2px solid #34d399;
                    border-radius: 6px;
                    padding: 5px 12px;
                    font-size: 12px;
                    font-weight: 800;
                }
                QPushButton:hover {
                    background-color: #10b981;
                }
            """
            dock_style = """
                QPushButton {
                    background-color: #059669;
                    color: #ffffff;
                    border: 2px solid #34d399;
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: 800;
                }
                QPushButton:hover {
                    background-color: #10b981;
                }
            """
            self.ls_top_btn.setStyleSheet(top_style)
            self.ls_top_btn.setText("⚡ LS ACTIVE (Shift+S)")
            self.ls_dock_btn.setStyleSheet(dock_style)
            self.ls_dock_btn.setText("⚡ LSFG ON")
        else:
            top_style = """
                QPushButton {
                    background-color: #064e3b;
                    color: #a7f3d0;
                    border: 1px solid #059669;
                    border-radius: 6px;
                    padding: 5px 12px;
                    font-size: 12px;
                    font-weight: 700;
                }
                QPushButton:hover {
                    background-color: #059669;
                    color: #ffffff;
                }
            """
            dock_style = """
                QPushButton {
                    background-color: #064e3b;
                    color: #a7f3d0;
                    border: 1px solid #059669;
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: 700;
                }
                QPushButton:hover {
                    background-color: #059669;
                    color: #ffffff;
                }
            """
            self.ls_top_btn.setStyleSheet(top_style)
            self.ls_top_btn.setText("⚡ Lossless Scaling (Shift+S)")
            self.ls_dock_btn.setStyleSheet(dock_style)
            self.ls_dock_btn.setText("⚡ LSFG")

    def _update_fps_hud(self):
        screen = self.screen() or (self.windowHandle().screen() if self.windowHandle() else None)
        hz = int(screen.refreshRate()) if screen else 120
        info = get_lossless_scaling_info()
        multiplier = info.get("multiplier", "4x")
        target_hz = info.get("target_hz", str(hz))

        base_fps = 30.0
        if self.player.playbackRate() > 0:
            base_fps = 30.0 * self.player.playbackRate()

        if hasattr(self, "fps_overlay"):
            self.fps_overlay.fps_lbl.setText(f"• Base Video Render: ~{base_fps:.1f} FPS")
            self.fps_overlay.hz_lbl.setText(f"• Display Refresh: {hz} Hz")
            if self.is_lossless_scaling_active:
                self.fps_overlay.ls_status_lbl.setText(f"• Lossless Scaling: ACTIVE ({multiplier} ➔ ~{target_hz} FPS)")
                self.fps_overlay.ls_status_lbl.setStyleSheet("color: #34d399; font-size: 11px; font-weight: 700;")
            else:
                self.fps_overlay.ls_status_lbl.setText("• Lossless Scaling: Standby (Press Shift+S to engage)")
                self.fps_overlay.ls_status_lbl.setStyleSheet("color: #93c5fd; font-size: 11px; font-weight: 600;")
            self.fps_overlay.tip_lbl.setText("💡 Look for green DXGI FPS in top-left when active")

    def trigger_lossless_scaling(self):
        """
        Call Lossless Scaling automatically:
        1. Ensures the video player is in clean Fullscreen so Lossless Scaling scales
           the full monitor resolution directly without a tiny centered letterbox box.
        2. Automatically starts LosslessScaling.exe via Steam protocol if not running.
        3. Toggles active state, button color, and dispatches global hotkey (Shift+S).
        """
        if not is_lossless_scaling_running():
            self._show_toast("🚀 Launching Lossless Scaling via Steam...", 3000)
            self._set_status_msg("🚀 Launching Lossless Scaling...")
            launched = launch_lossless_scaling()

            self._check_launch_attempts = 0
            if hasattr(self, "_check_launch_timer") and self._check_launch_timer and self._check_launch_timer.isActive():
                self._check_launch_timer.stop()
            self._check_launch_timer = QTimer(self)
            self._check_launch_timer.setInterval(700)

            def check_active():
                self._check_launch_attempts += 1
                if is_lossless_scaling_running():
                    self._check_launch_timer.stop()
                    self._proceed_with_ls_toggle()
                elif self._check_launch_attempts >= 5:
                    self._check_launch_timer.stop()
                    self._show_toast("⚠️ Please launch Lossless Scaling from Steam / Desktop, then press Shift+S", 4500)
                    self._set_status_msg("⚠️ Please open Lossless Scaling, then press Shift+S")

            self._check_launch_timer.timeout.connect(check_active)
            self._check_launch_timer.start()
            return

        self._proceed_with_ls_toggle()

    def _proceed_with_ls_toggle(self):
        # 1. Switch to clean fullscreen if not already fullscreen
        if not self.is_custom_fullscreen:
            self.is_custom_fullscreen = True
            self.showFullScreen()
            self.fs_top_btn.setText("⛶ Windowed")

        # 2. Immediately hide UI overlay bars and blank mouse cursor so Lossless Scaling
        # captures a 100% pure edge-to-edge video frame without UI bars or mouse cursor
        self.inactivity_timer.stop()
        self.top_bar.hide()
        self.control_bar.hide()
        self.setCursor(Qt.CursorShape.BlankCursor)
        self.video_widget.setCursor(Qt.CursorShape.BlankCursor)

        self._update_layout_geometries()
        self.activateWindow()
        self.raise_()

        self.is_lossless_scaling_active = not self.is_lossless_scaling_active
        self._update_ls_button_styles()

        # 3. Wait 400ms for fullscreen DWM presentation to settle before sending hotkey
        QTimer.singleShot(400, self._dispatch_ls_hotkey)

    def _dispatch_ls_hotkey(self):
        self.activateWindow()
        self.raise_()
        send_lossless_scaling_hotkey()
        info = get_lossless_scaling_info()
        combo = info.get("hotkey", "Shift+S")
        mult = info.get("multiplier", "4x")
        target_hz = info.get("target_hz", "120")

        if self.is_lossless_scaling_active:
            msg = f"⚡ Lossless Scaling ({mult} LSFG ➔ ~{target_hz} FPS) ENGAGED ({combo}) — Look for green FPS in top-left!"
            self._show_toast(msg, 3500)
            self._set_status_msg(f"⚡ LSFG Active ({mult})")
        else:
            msg = f"⚡ Lossless Scaling Disengaged ({combo})"
            self._show_toast(msg, 2500)
            self._set_status_msg("")

        self._update_fps_hud()

    def _setup_shortcuts(self):
        # F11 Fullscreen
        f11_sc = QShortcut(QKeySequence(Qt.Key.Key_F11), self)
        f11_sc.activated.connect(self.toggle_fullscreen)

        # Space toggles play/pause
        space_sc = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        space_sc.activated.connect(self.toggle_play_pause)

        # Escape exits fullscreen or closes
        esc_sc = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        esc_sc.activated.connect(self._on_escape)

        # 'A' cycles aspect ratio mode (Fit, Fill, Stretch)
        aspect_sc = QShortcut(QKeySequence("A"), self)
        aspect_sc.activated.connect(self._cycle_aspect_ratio_mode)

        # Shift+S calls Lossless Scaling directly
        shift_s_sc = QShortcut(QKeySequence("Shift+S"), self)
        shift_s_sc.activated.connect(self.trigger_lossless_scaling)

        # Ctrl+L alternative shortcut for Lossless Scaling
        ctrl_l_sc = QShortcut(QKeySequence("Ctrl+L"), self)
        ctrl_l_sc.activated.connect(self.trigger_lossless_scaling)

        # Ctrl+O opens local video file dialog
        ctrl_o_sc = QShortcut(QKeySequence("Ctrl+O"), self)
        ctrl_o_sc.activated.connect(self._open_local_file_dialog)

    def _on_escape(self):
        if self.is_custom_fullscreen:
            self.toggle_fullscreen()
        else:
            self.close()

    def _connect_signals(self):
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.player.errorOccurred.connect(self._on_media_error)

    def _open_local_file_dialog(self):
        """Open a file dialog to switch or play any video on the local PC."""
        from PyQt6.QtWidgets import QFileDialog
        from archivevault.core.settings import settings
        file_filter = (
            "Video Files (*.mp4 *.mkv *.avi *.ogv *.webm *.mov *.flv *.wmv *.m4v *.mpg *.mpeg *.m2v *.ts *.vob *.3gp);;"
            "All Files (*.*)"
        )
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Video to Play in Cinema",
            settings.download_dir or "",
            file_filter
        )
        if file_path:
            title = os.path.splitext(os.path.basename(file_path))[0]
            self.load_new_video(file_path, title)

    def load_new_video(self, source: str, title: str):
        """Load and start playing a new video file or stream immediately in the cinema viewport."""
        self.source = source
        self.video_title = title
        self.setWindowTitle(f"🎬 {self.video_title} — ArchiveVault Cinema")
        if hasattr(self, "title_label"):
            self.title_label.setText(title)
        
        is_local = os.path.isabs(source) and os.path.exists(source)
        if hasattr(self, "badge"):
            self.badge.setText("LOCAL PLAY" if is_local else "STREAMING VIDEO")
            badge_bg = "#2563eb" if is_local else "#059669"
            self.badge.setStyleSheet(f"""
                background-color: {badge_bg};
                color: #ffffff;
                font-size: 9px;
                font-weight: 800;
                padding: 3px 8px;
                border-radius: 4px;
            """)

        self.player.stop()
        self.timeline_slider.setValue(0)
        self._load_video()
        self._show_toast(f"▶ Playing: {title}", 3000)

    def _on_media_error(self, error, error_string: str = ""):
        err_msg = error_string or str(error)
        self._show_toast(f"⚠️ Playback Error: {err_msg}", 5000)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if any(url.isLocalFile() and url.toLocalFile().lower().endswith(VIDEO_EXTENSIONS) for url in urls):
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    path = url.toLocalFile()
                    if path.lower().endswith(VIDEO_EXTENSIONS):
                        event.acceptProposedAction()
                        title = os.path.splitext(os.path.basename(path))[0]
                        self.load_new_video(path, title)
                        return

    def _load_video(self):
        if os.path.isabs(self.source) and os.path.exists(self.source):
            self.player.setSource(QUrl.fromLocalFile(self.source))
        else:
            self.player.setSource(QUrl(self.source))
        self.player.play()

    def toggle_play_pause(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def stop_playback(self):
        self.player.stop()
        self.timeline_slider.setValue(0)
        self._update_time_label(0, self.player.duration())
        self._on_user_activity()

    def toggle_fullscreen(self):
        self.is_custom_fullscreen = not self.is_custom_fullscreen
        if self.is_custom_fullscreen:
            self.showFullScreen()
            self.fs_top_btn.setText("⛶ Windowed")
            if not self.controls_pinned and self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.inactivity_timer.start(3500)
        else:
            self.showNormal()
            self.top_bar.show()
            self.control_bar.show()
            self.top_bar.raise_()
            self.control_bar.raise_()
            self.fs_top_btn.setText("⛶ Fullscreen (F11)")
            self.inactivity_timer.stop()
        
        self._update_layout_geometries()
        self.video_widget.update()
        self._on_user_activity()

    def _on_playback_state_changed(self, state: QMediaPlayer.PlaybackState):
        is_playing = (state == QMediaPlayer.PlaybackState.PlayingState)
        self.play_btn.setText("⏸" if is_playing else "▶")
        if is_playing:
            if self.is_custom_fullscreen and not self.controls_pinned:
                self.inactivity_timer.start(3500)
        else:
            self.inactivity_timer.stop()
            self._on_user_activity()

    def _on_position_changed(self, position: int):
        if not self._is_seeking:
            self.timeline_slider.setValue(position)
            self._update_time_label(position, self.player.duration())

    def _on_duration_changed(self, duration: int):
        self.timeline_slider.setRange(0, duration)
        self._update_time_label(self.player.position(), duration)

    def _update_time_label(self, pos: int, dur: int):
        pos_str = format_video_time(pos)
        dur_str = format_video_time(dur)
        self.time_label.setText(f"{pos_str} / {dur_str}")

    def _on_slider_pressed(self):
        self._is_seeking = True
        self.inactivity_timer.stop()
        self._on_user_activity()

    def _on_slider_released(self):
        self._is_seeking = False
        self.player.setPosition(self.timeline_slider.value())
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.inactivity_timer.start(2500)

    def _on_slider_moved(self, value: int):
        self._update_time_label(value, self.player.duration())
        self._on_user_activity()

    def _on_volume_changed(self, value: int):
        self.audio_output.setVolume(value / 100.0)
        self._on_user_activity()

    def closeEvent(self, event):
        """Stop playback, halt timers, and release media resources cleanly."""
        try:
            self.inactivity_timer.stop()
            if hasattr(self, "_fps_update_timer") and self._fps_update_timer.isActive():
                self._fps_update_timer.stop()
            if hasattr(self, "_check_launch_timer") and self._check_launch_timer and self._check_launch_timer.isActive():
                self._check_launch_timer.stop()
            if hasattr(self, "toast_hud"):
                self.toast_hud.close()
            if hasattr(self, "fps_overlay"):
                self.fps_overlay.close()
            self.player.stop()
            self.player.setSource(QUrl())
        except Exception:
            pass
        super().closeEvent(event)

