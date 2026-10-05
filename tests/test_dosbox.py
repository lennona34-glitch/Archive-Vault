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
        from archivevault.core.utils import get_dosbox_path
        tab = ArcadeTab()
        self.assertIsNotNone(tab.table)
        self.assertIsNotNone(tab.btn_load_pc)
        self.assertIsNotNone(tab.btn_open_folder)
        # Verify DOSBox detection helper runs without error
        path = get_dosbox_path()
        self.assertTrue(path is None or isinstance(path, str))

if __name__ == "__main__":
    unittest.main()
