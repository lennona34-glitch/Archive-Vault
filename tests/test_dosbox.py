import os
import sys
import unittest
from PyQt6.QtWidgets import QApplication

from archivevault.ui.dosbox_player import DOSBoxPlayerDialog
from archivevault.ui.main_window import MainWindow

class TestDOSBoxIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_dosbox_dialog_initialization(self):
        dialog = DOSBoxPlayerDialog(
            identifier="msdos_Prince_of_Persia_1990",
            title="Prince of Persia (1990)"
        )
        self.assertIsNotNone(dialog)
        self.assertIn("Prince of Persia", dialog.windowTitle())
        self.assertEqual(dialog.identifier, "msdos_Prince_of_Persia_1990")
        self.assertIsNotNone(dialog.web_view)
        
        # Test mute toggle
        self.assertFalse(dialog.is_muted)
        dialog._toggle_mute()
        self.assertTrue(dialog.is_muted)
        dialog._toggle_mute()
        self.assertFalse(dialog.is_muted)

        # Test fullscreen toggle
        self.assertFalse(dialog.is_custom_fullscreen)
        dialog._toggle_fullscreen()
        self.assertTrue(dialog.is_custom_fullscreen)
        dialog._toggle_fullscreen()
        self.assertFalse(dialog.is_custom_fullscreen)

        dialog.close()

    def test_main_window_dosbox_signal(self):
        window = MainWindow()
        self.assertTrue(hasattr(window, "_launch_dosbox_player"))
        self.assertTrue(hasattr(window, "arcade_tab"))
        self.assertTrue(hasattr(window, "btn_arcade"))
        self.assertEqual(window.pages.count(), 5)
        window.close()

    def test_arcade_tab_initialization(self):
        from archivevault.ui.arcade_tab import ArcadeTab
        from archivevault.core.utils import get_dosbox_path, get_dosbox_info, get_dosbox_custom_conf_path, find_dos_executable
        tab = ArcadeTab()
        self.assertIsNotNone(tab.table)
        self.assertIsNotNone(tab.btn_load_pc)
        self.assertIsNotNone(tab.btn_open_folder)
        self.assertIsNotNone(tab.btn_toggle_dosbox)

        # Verify DOSBox info helper returns dictionary with valid structure
        info = get_dosbox_info()
        self.assertIsInstance(info, dict)
        self.assertIn("path", info)
        self.assertIn("source", info)
        self.assertIn("is_launchbox", info)

        # Verify high-res config generation
        conf_path = get_dosbox_custom_conf_path()
        self.assertTrue(os.path.exists(conf_path))
        with open(conf_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("windowresolution=1280x960", content)
        self.assertIn("scaler=normal3x", content)
        self.assertIn("aspect=true", content)

    def test_find_dos_executable(self):
        import tempfile
        import os
        from archivevault.core.utils import find_dos_executable

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a mock DOS game directory
            with open(os.path.join(tmpdir, "setup.exe"), "w") as f:
                f.write("mock")
            with open(os.path.join(tmpdir, "doom.exe"), "w") as f:
                f.write("mock")
            with open(os.path.join(tmpdir, "play.bat"), "w") as f:
                f.write("mock")

            # Preferred executable (play.bat) should take precedence over setup.exe
            found = find_dos_executable(tmpdir)
            self.assertEqual(found.lower(), "play.bat")

if __name__ == "__main__":
    unittest.main()
