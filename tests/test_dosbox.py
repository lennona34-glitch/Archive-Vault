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
        window.close()

if __name__ == "__main__":
    unittest.main()
