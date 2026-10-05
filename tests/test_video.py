import os
import sys
import unittest
from PyQt6.QtWidgets import QApplication

from archivevault.ui.video_player import VideoPlayerDialog, format_video_time
from archivevault.ui.main_window import MainWindow
from archivevault.ui.downloads_tab import DownloadsTab, is_emulated_item

class TestVideoAndMediaIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_format_video_time(self):
        self.assertEqual(format_video_time(0), "00:00")
        self.assertEqual(format_video_time(65000), "01:05")
        self.assertEqual(format_video_time(3665000), "1:01:05")

    def test_video_dialog_initialization(self):
        dialog = VideoPlayerDialog(
            source="https://archive.org/download/test/test.mp4",
            title="Kung Fu Dragon"
        )
        self.assertIsNotNone(dialog)
        self.assertIn("Kung Fu Dragon", dialog.windowTitle())
        self.assertEqual(dialog.source, "https://archive.org/download/test/test.mp4")
        self.assertIsNotNone(dialog.player)
        self.assertIsNotNone(dialog.timeline_slider)

        # Test volume change
        dialog._on_volume_changed(50)
        self.assertAlmostEqual(dialog.audio_output.volume(), 0.50, delta=0.05)

        # Test fullscreen toggle
        self.assertFalse(dialog.is_custom_fullscreen)
        dialog.toggle_fullscreen()
        self.assertTrue(dialog.is_custom_fullscreen)
        dialog.toggle_fullscreen()
        self.assertFalse(dialog.is_custom_fullscreen)

        dialog.close()

    def test_is_emulated_item(self):
        self.assertTrue(is_emulated_item("msdos_Prince_of_Persia_1990"))
        self.assertTrue(is_emulated_item("amiga_Monkey_Island"))
        self.assertTrue(is_emulated_item("arcade_pacman"))
        self.assertFalse(is_emulated_item("Commodore_Amiga_TOSEC_2012_04_10"))
        self.assertFalse(is_emulated_item("Return_of_the_Kung_Fu_Dragon"))

    def test_main_window_video_signal(self):
        window = MainWindow()
        self.assertTrue(hasattr(window, "play_video"))
        self.assertTrue(hasattr(window.item_tab, "play_video_requested"))
        self.assertTrue(hasattr(window.downloads_tab, "play_video_requested"))
        self.assertTrue(hasattr(window.downloads_tab, "play_dosbox_requested"))
        window.close()

if __name__ == "__main__":
    unittest.main()
