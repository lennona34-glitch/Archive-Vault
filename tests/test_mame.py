import os
import sys
import unittest
from PyQt6.QtWidgets import QApplication

from archivevault.core.settings import settings
from archivevault.core.utils import (
    get_7z_cli_path,
    get_mame_info,
    get_mame_path,
    launch_mame_game,
)
from archivevault.ui.mame_installer_dialog import LaunchBoxGuideDialog, MameInstallerDialog


class TestMAMEIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_mame_info_structure(self):
        info = get_mame_info()
        self.assertIsInstance(info, dict)
        self.assertIn("path", info)
        self.assertIn("source", info)
        self.assertIn("is_launchbox", info)
        self.assertEqual(get_mame_path(), info.get("path"))

    def test_7z_cli_detection(self):
        seven_zip = get_7z_cli_path()
        # On this system, LaunchBox 7z is installed
        if seven_zip:
            self.assertTrue(os.path.exists(seven_zip))
            self.assertTrue(seven_zip.lower().endswith("7z.exe"))

    def test_launch_mame_nonexistent(self):
        # Gracefully fails on nonexistent file
        res = launch_mame_game(r"C:\fake_dir_12345\fake_game.zip")
        self.assertFalse(res)

    def test_mame_installer_dialog_init(self):
        dialog = MameInstallerDialog()
        self.assertIsNotNone(dialog)
        self.assertIn("MAME", dialog.windowTitle())
        self.assertIsNotNone(dialog.progress_bar)
        self.assertIsNotNone(dialog.status_lbl)
        dialog.close()

    def test_launchbox_guide_dialog_init(self):
        guide = LaunchBoxGuideDialog()
        self.assertIsNotNone(guide)
        self.assertIn("LaunchBox", guide.windowTitle())
        self.assertIsNotNone(guide.btn_open_lb)
        guide.close()

    def test_settings_mame_persistence(self):
        original = settings.mame_path
        try:
            settings.mame_path = r"C:\fake_mame\mame.exe"
            settings.save()
            settings.load()
            self.assertEqual(settings.mame_path, r"C:\fake_mame\mame.exe")
        finally:
            settings.mame_path = original
            settings.save()


if __name__ == "__main__":
    unittest.main()
