import os
from typing import Optional
from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

def format_time_ms(ms: int) -> str:
    """Format milliseconds into MM:SS string."""
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

class AudioPlayerWidget(QFrame):
    """
    Sleek in-app audio streaming player for Internet Archive audio recordings,
    live concerts, 78rpm vinyl records, and previews.
    """
    playback_state_changed = pyqtSignal(bool) # is_playing
    track_changed = pyqtSignal(str) # current_track_url

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setStyleSheet("""
            QFrame#card {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1a1a1f, stop:1 #1e1e26);
                border: 1px solid #3b82f6;
                border-radius: 10px;
                padding: 10px 14px;
            }
        """)

        self.current_url: str = ""
        self.current_title: str = ""
        self._is_seeking = False

        # Qt Multimedia Player setup
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.75) # 75% default volume

        self._init_ui()
        self._connect_player_signals()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 8, 10, 8)
        main_layout.setSpacing(14)

        # 1. Big Play / Pause Button
        self.play_btn = QPushButton("▶")
        self.play_btn.setObjectName("primaryBtn")
        self.play_btn.setFixedSize(40, 40)
        self.play_btn.setStyleSheet("""
            QPushButton#primaryBtn {
                background-color: #2563eb;
                border-radius: 20px;
                font-size: 16px;
                font-weight: 700;
                color: #ffffff;
            }
            QPushButton#primaryBtn:hover {
                background-color: #3b82f6;
            }
        """)
        self.play_btn.clicked.connect(self.toggle_play_pause)
        main_layout.addWidget(self.play_btn)

        # 2. Track Info & Timeline (Center)
        center_layout = QVBoxLayout()
        center_layout.setSpacing(4)

        # Top row: Title and Badge
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self.badge = QLabel("STREAMING AUDIO")
        self.badge.setStyleSheet(
            "background-color: #059669; color: #ffffff; font-size: 9px; "
            "font-weight: 800; padding: 2px 6px; border-radius: 4px;"
        )
        self.badge.setFixedHeight(18)
        top_row.addWidget(self.badge)

        self.title_label = QLabel("No track playing")
        self.title_label.setStyleSheet("font-size: 13px; font-weight: 700; color: #f4f4f5;")
        top_row.addWidget(self.title_label, stretch=1)

        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet("font-size: 11px; font-weight: 600; color: #a1a1aa;")
        top_row.addWidget(self.time_label)

        center_layout.addLayout(top_row)

        # Bottom row: Seek slider
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 0)
        self.seek_slider.setStyleSheet("""
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
                width: 12px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 6px;
            }
            QSlider::handle:horizontal:hover {
                background: #38bdf8;
            }
        """)
        self.seek_slider.sliderPressed.connect(self._on_slider_pressed)
        self.seek_slider.sliderReleased.connect(self._on_slider_released)
        self.seek_slider.sliderMoved.connect(self._on_slider_moved)
        center_layout.addWidget(self.seek_slider)

        main_layout.addLayout(center_layout, stretch=1)

        # 3. Volume & Stop controls (Right)
        right_layout = QHBoxLayout()
        right_layout.setSpacing(8)

        vol_icon = QLabel("🔊")
        vol_icon.setStyleSheet("font-size: 14px;")
        right_layout.addWidget(vol_icon)

        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(75)
        self.vol_slider.setFixedWidth(70)
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
        right_layout.addWidget(self.vol_slider)

        self.stop_btn = QPushButton("⏹")
        self.stop_btn.setFixedSize(30, 30)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #27272a;
                color: #e4e4e7;
                border: 1px solid #3f3f46;
                border-radius: 6px;
                font-size: 13px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #3f3f46;
            }
        """)
        self.stop_btn.setToolTip("Stop playback")
        self.stop_btn.clicked.connect(self.stop)
        right_layout.addWidget(self.stop_btn)

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #27272a;
                color: #f87171;
                border: 1px solid #7f1d1d;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 700;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #7f1d1d;
                color: #ffffff;
            }
        """)
        self.close_btn.setToolTip("Close audio player")
        self.close_btn.clicked.connect(self.hide_and_stop)
        right_layout.addWidget(self.close_btn)

        main_layout.addLayout(right_layout)

    def _connect_player_signals(self):
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.player.mediaStatusChanged.connect(self._on_media_status_changed)
        self.player.errorOccurred.connect(self._on_player_error)

    def play_track(self, url: str, title: str):
        """Start playing an audio stream or local file directly inside the application."""
        self.show()
        if self.current_url == url:
            # Same track, toggle play/pause
            if self.is_playing():
                self.player.pause()
            else:
                self.player.play()
            return

        self.current_url = url
        self.current_title = title
        self.title_label.setText(title)
        
        self.seek_slider.setValue(0)
        self.time_label.setText("00:00 / 00:00")
        
        # Check if local file path or remote URL
        if os.path.isabs(url) and os.path.exists(url):
            self.player.setSource(QUrl.fromLocalFile(url))
            self.badge.setText("LOCAL PLAY")
            self.badge.setStyleSheet("background-color: #2563eb; color: #ffffff; font-size: 9px; font-weight: 800; padding: 2px 6px; border-radius: 4px;")
        else:
            self.player.setSource(QUrl(url))
            self.badge.setText("BUFFERING...")
            self.badge.setStyleSheet("background-color: #d97706; color: #ffffff; font-size: 9px; font-weight: 800; padding: 2px 6px; border-radius: 4px;")
            
        self.player.play()
        self.track_changed.emit(url)

    def is_playing(self) -> bool:
        return self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    def toggle_play_pause(self):
        if self.is_playing():
            self.player.pause()
        else:
            self.player.play()

    def stop(self):
        self.player.stop()
        self.play_btn.setText("▶")
        self.seek_slider.setValue(0)
        self._update_time_label(0, self.player.duration())

    def hide_and_stop(self):
        self.stop()
        self.hide()

    def _on_playback_state_changed(self, state: QMediaPlayer.PlaybackState):
        is_playing = (state == QMediaPlayer.PlaybackState.PlayingState)
        self.play_btn.setText("⏸" if is_playing else "▶")
        self.playback_state_changed.emit(is_playing)
        if is_playing:
            if os.path.isabs(self.current_url) and os.path.exists(self.current_url):
                self.badge.setText("LOCAL PLAY")
                self.badge.setStyleSheet("background-color: #2563eb; color: #ffffff; font-size: 9px; font-weight: 800; padding: 2px 6px; border-radius: 4px;")
            else:
                self.badge.setText("LIVE AUDIO")
                self.badge.setStyleSheet("background-color: #059669; color: #ffffff; font-size: 9px; font-weight: 800; padding: 2px 6px; border-radius: 4px;")

    def _on_media_status_changed(self, status: QMediaPlayer.MediaStatus):
        if status == QMediaPlayer.MediaStatus.BufferingMedia:
            self.badge.setText("BUFFERING...")
            self.badge.setStyleSheet("background-color: #d97706; color: #ffffff; font-size: 9px; font-weight: 800; padding: 2px 6px; border-radius: 4px;")
        elif status == QMediaPlayer.MediaStatus.BufferedMedia or status == QMediaPlayer.MediaStatus.LoadedMedia:
            self.badge.setText("LIVE AUDIO")
            self.badge.setStyleSheet("background-color: #059669; color: #ffffff; font-size: 9px; font-weight: 800; padding: 2px 6px; border-radius: 4px;")
        elif status == QMediaPlayer.MediaStatus.InvalidMedia:
            self.badge.setText("ERROR")
            self.badge.setStyleSheet("background-color: #dc2626; color: #ffffff; font-size: 9px; font-weight: 800; padding: 2px 6px; border-radius: 4px;")

    def _on_player_error(self, error, error_string):
        self.badge.setText("STREAM ERROR")
        self.badge.setStyleSheet("background-color: #dc2626; color: #ffffff; font-size: 9px; font-weight: 800; padding: 2px 6px; border-radius: 4px;")
        self.title_label.setText(f"Error streaming track: {error_string}")

    def _on_position_changed(self, position: int):
        if not self._is_seeking:
            self.seek_slider.setValue(position)
            self._update_time_label(position, self.player.duration())

    def _on_duration_changed(self, duration: int):
        self.seek_slider.setRange(0, duration)
        self._update_time_label(self.player.position(), duration)

    def _update_time_label(self, pos: int, dur: int):
        pos_str = format_time_ms(pos)
        dur_str = format_time_ms(dur)
        self.time_label.setText(f"{pos_str} / {dur_str}")

    def _on_slider_pressed(self):
        self._is_seeking = True

    def _on_slider_released(self):
        self._is_seeking = False
        self.player.setPosition(self.seek_slider.value())

    def _on_slider_moved(self, value: int):
        self._update_time_label(value, self.player.duration())

    def _on_volume_changed(self, value: int):
        # AudioOutput volume takes a float 0.0 to 1.0
        self.audio_output.setVolume(value / 100.0)
