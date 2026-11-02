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

from archivevault.ui.main_window import MainWindow

class TestUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_main_window_init_and_zen_mode(self):
        window = MainWindow()
        self.assertIsNotNone(window)
        self.assertEqual(window.pages.count(), 6)
        
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
        self.assertIsNotNone(window.downloads_tab.clear_list_btn)
        self.assertIsNotNone(window.downloads_tab.clear_done_btn)

        # Test download manager clear operations
        from archivevault.core.downloader import download_manager, DownloadItem, STATUS_COMPLETED, STATUS_FAILED
        orig_items = list(download_manager.items)
        try:
            download_manager.items = []
            download_manager.items.append(DownloadItem(id="test1", identifier="item1", filename="test1.txt", url="http://example.com/1", save_path="test1.txt", part_path="test1.part", total_bytes=1000, status=STATUS_COMPLETED))
            download_manager.items.append(DownloadItem(id="test2", identifier="item2", filename="test2.txt", url="http://example.com/2", save_path="test2.txt", part_path="test2.part", total_bytes=2000, status=STATUS_FAILED))
            download_manager.clear_inactive()
            self.assertEqual(len(download_manager.items), 0)

            download_manager.items.append(DownloadItem(id="test3", identifier="item3", filename="test3.txt", url="http://example.com/3", save_path="test3.txt", part_path="test3.part", total_bytes=3000))
            download_manager.clear_all(cancel_active=False)
            self.assertEqual(len(download_manager.items), 0)
        finally:
            download_manager.items = orig_items
            download_manager.save_queue()

        window.btn_arcade.click()
        self.assertEqual(window.pages.currentIndex(), 3)
        self.assertEqual(window.arcade_tab.tab_widget.count(), 3)

        window.btn_upload.click()
        self.assertEqual(window.pages.currentIndex(), 4)
        self.assertIsNotNone(window.upload_tab.btn_start_upload)

        window.btn_settings.click()
        self.assertEqual(window.pages.currentIndex(), 5)

        window.btn_search.click()
        self.assertEqual(window.pages.currentIndex(), 0)

        window.close()

if __name__ == "__main__":
    unittest.main()
