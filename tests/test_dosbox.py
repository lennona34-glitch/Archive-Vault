import os
import sys
import unittest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

if hasattr(Qt.ApplicationAttribute, "AA_ShareOpenGLContexts"):
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)
try:
    import PyQt6.QtWebEngineWidgets
except ImportError:
    pass

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

        # Test error card creation: Verify LaunchBox is completely removed and Easy Retro / Retry are present
        dialog._show_emulation_error_card("Test Error", "Test message")
        self.assertTrue(hasattr(dialog, "btn_err_retry"))
        self.assertTrue(hasattr(dialog, "btn_err_ra"))
        self.assertFalse(hasattr(dialog, "btn_err_lb"))
        self.assertIn("Retry", dialog.btn_err_retry.text())
        self.assertIn("Easy Retro", dialog.btn_err_ra.text())

        dialog.close()

    def test_main_window_dosbox_signal(self):
        window = MainWindow()
        self.assertTrue(hasattr(window, "_launch_dosbox_player"))
        self.assertTrue(hasattr(window, "arcade_tab"))
        self.assertTrue(hasattr(window, "btn_arcade"))
        self.assertGreaterEqual(window.pages.count(), 5)
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

    def test_detect_retro_platform_atari_st_and_microcomputers(self):
        from archivevault.ui.dosbox_player import detect_retro_platform
        from archivevault.ui.arcade_tab import RETRO_FILE_EXTENSIONS

        # Verify Atari ST extensions are present
        self.assertIn('.st', RETRO_FILE_EXTENSIONS)
        self.assertIn('.msa', RETRO_FILE_EXTENSIONS)

        # Verify detection
        st_game = detect_retro_platform("Carrier_Command.st")
        self.assertEqual(st_game["name"], "Atari ST")
        self.assertEqual(st_game["badge"], "ATARI ST")

        msa_game = detect_retro_platform("Speedball_2.msa")
        self.assertEqual(msa_game["name"], "Atari ST")

        amiga_game = detect_retro_platform("Lemmings.adf")
        self.assertEqual(amiga_game["name"], "Amiga")

        c64_game = detect_retro_platform("Giana_Sisters.d64")
        self.assertEqual(c64_game["name"], "Commodore 64")

        spectrum_game = detect_retro_platform("Manic_Miner.tap")
        self.assertEqual(spectrum_game["name"], "ZX Spectrum")

    def test_bin_cue_disc_and_console_platform_detection(self):
        from archivevault.ui.dosbox_player import detect_retro_platform

        # General CD-ROM / Disc Image .bin should NOT be detected as MS-DOS
        generic_bin = detect_retro_platform("GameDisk.bin")
        self.assertNotEqual(generic_bin["name"], "MS-DOS")
        self.assertIn("Disc", generic_bin["name"])

        generic_cue = detect_retro_platform("Quake.cue")
        self.assertIn("Disc", generic_cue["name"])

        # PlayStation .bin/.cue should be detected as PlayStation
        ps1_bin = detect_retro_platform("Crash_Bandicoot_PS1.bin")
        self.assertEqual(ps1_bin["name"], "PlayStation")

        # Sega Genesis .bin should be detected as Sega Genesis
        md_bin = detect_retro_platform("Sonic_The_Hedgehog_Genesis.bin")
        self.assertEqual(md_bin["name"], "Sega Genesis")

        # ISO disc image
        iso_game = detect_retro_platform("Warcraft_2_CD.iso")
        self.assertIn("Disc", iso_game["name"])

    def test_retroarch_info_and_core_resolution(self):
        from archivevault.core.utils import (
            get_retroarch_info,
            get_retroarch_path,
            get_retroarch_cores_dir,
            get_best_retroarch_core
        )

        info = get_retroarch_info()
        self.assertIsInstance(info, dict)
        self.assertIn("path", info)
        self.assertIn("cores_dir", info)
        self.assertIn("cores", info)
        self.assertIn("cores_count", info)

        # On this machine, RetroArch exists at C:\RetroArch-Win64\retroarch.exe
        if info["path"]:
            self.assertTrue(os.path.exists(info["path"]))
            cores_dir = get_retroarch_cores_dir()
            self.assertIsNotNone(cores_dir)

            # Test core preference resolution for Atari ST
            core = get_best_retroarch_core("Atari ST")
            if "hatari2014_libretro.dll" in info["cores"] or "hatari_libretro.dll" in info["cores"]:
                self.assertIsNotNone(core)
                self.assertTrue(core.endswith(".dll"))

    def test_easy_retro_dialog_initialization(self):
        from archivevault.ui.retroarch_dialog import EasyRetroDialog
        dlg = EasyRetroDialog()
        self.assertIsNotNone(dlg.cores_table)
        self.assertGreater(dlg.cores_table.rowCount(), 5)
        self.assertIn("Easy Retro", dlg.windowTitle())
        dlg.close()

if __name__ == "__main__":
    unittest.main()
