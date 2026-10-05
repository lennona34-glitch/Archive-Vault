import os
import sys
import tempfile
import unittest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from archivevault.core.downloader import STATUS_COMPLETED, DownloadItem, download_manager
from archivevault.ui.main_window import MainWindow

class TestAudioIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_audio_playback_local_and_remote(self):
        window = MainWindow()
        window.show()
        self.assertIsNotNone(window.audio_player)
        self.assertTrue(window.audio_player.isHidden())

        # Create dummy audio file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"ID3" + b"\x00" * 100) # minimal mock mp3 header
            temp_audio_path = f.name

        try:
            # 1. Test playing local file
            window.play_audio(temp_audio_path, "Test Song.mp3")
            self.assertFalse(window.audio_player.isHidden())
            self.assertEqual(window.audio_player.current_title, "Test Song.mp3")
            self.assertEqual(window.audio_player.badge.text(), "LOCAL PLAY")

            # 2. Test stopping and closing
            window.audio_player.hide_and_stop()
            self.assertTrue(window.audio_player.isHidden())

            # 3. Test playing remote stream
            window.play_audio("https://archive.org/download/test/track01.mp3", "Remote Stream")
            self.assertFalse(window.audio_player.isHidden())
            self.assertEqual(window.audio_player.current_title, "Remote Stream")
            self.assertIn(window.audio_player.badge.text(), ("BUFFERING...", "LIVE AUDIO"))

            window.audio_player.hide_and_stop()

            # 4. Test DownloadsTab row actions for audio files
            item = DownloadItem(
                id="test_audio_item_1",
                identifier="test_archive_item",
                filename="song.mp3",
                url="https://archive.org/download/test/song.mp3",
                save_path=temp_audio_path,
                part_path=temp_audio_path + ".part",
                total_bytes=1024,
                downloaded_bytes=1024,
                status=STATUS_COMPLETED
            )
            download_manager.items = [item]
            window.downloads_tab.refresh_table()

            # Verify action widget has Play button
            action_widget = window.downloads_tab.table.cellWidget(0, 6)
            self.assertIsNotNone(action_widget)
            buttons = [b.text() for b in action_widget.findChildren(type(window.downloads_tab.pause_all_btn))]
            self.assertTrue(any("Play" in b for b in buttons), f"Buttons found: {buttons}")

        finally:
            window.audio_player.player.stop()
            from PyQt6.QtCore import QUrl
            window.audio_player.player.setSource(QUrl())
            window.close()
            try:
                if os.path.exists(temp_audio_path):
                    os.remove(temp_audio_path)
            except Exception:
                pass

if __name__ == "__main__":
    unittest.main()
