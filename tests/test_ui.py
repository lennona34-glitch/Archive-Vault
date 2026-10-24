import sys
import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from archivevault.ui.main_window import MainWindow

class TestUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_main_window_init_and_zen_mode(self):
        window = MainWindow()
        self.assertIsNotNone(window)
        self.assertEqual(window.pages.count(), 5)
        
        # Test Zen Mode toggle
        self.assertFalse(window.is_zen_mode)
        window.toggle_zen_mode()
        self.assertTrue(window.is_zen_mode)
        window.toggle_zen_mode()
        self.assertFalse(window.is_zen_mode)

        # Test curated browse category switching
        search_tab = window.search_tab
        self.assertIn("trending", search_tab.pills)
        self.assertIn("games", search_tab.pills)
        self.assertIn("arcade", search_tab.pills)
        self.assertIn("computers", search_tab.pills)
        search_tab.pills["games"].click()
        self.assertEqual(search_tab.current_collection_key, "games")

        # Test search tab controls (presets, mediatype, reset)
        self.assertIsNotNone(search_tab.preset_combo)
        self.assertIsNotNone(search_tab.mediatype_combo)
        self.assertIsNotNone(search_tab.reset_btn)
        self.assertIsNotNone(search_tab.guide_btn)

        # Test fresh Subject Dossier has default showcase bars populated
        self.assertGreater(window.item_tab.curated_cards_container.count(), 0)

        # Test tab navigation
        window.btn_item.click()
        self.assertEqual(window.pages.currentIndex(), 1)
        
        window.btn_downloads.click()
        self.assertEqual(window.pages.currentIndex(), 2)

        window.btn_arcade.click()
        self.assertEqual(window.pages.currentIndex(), 3)

        window.btn_settings.click()
        self.assertEqual(window.pages.currentIndex(), 4)

        window.btn_search.click()
        self.assertEqual(window.pages.currentIndex(), 0)

        window.close()

if __name__ == "__main__":
    unittest.main()
