import os
import shutil
import tempfile
import time
import unittest
from PyQt6.QtCore import QCoreApplication
from archivevault.core.downloader import DownloadManager, STATUS_COMPLETED, STATUS_DOWNLOADING, STATUS_PAUSED
from archivevault.core.settings import settings

class TestDownloader(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.orig_queue_file = settings.queue_file
        settings.queue_file = os.path.join(self.temp_dir, "test_queue.json")
        settings.download_dir = self.temp_dir
        settings.create_item_subfolders = False
        self.mgr = DownloadManager()
        self.mgr.items = []

    def tearDown(self):
        self.mgr.pause_all()
        settings.queue_file = self.orig_queue_file
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_add_and_queue(self):
        item = self.mgr.add_download(
            identifier="test-item",
            filename="sample.txt",
            url="https://archive.org/download/test-item/sample.txt",
            total_bytes=5000,
            target_dir=self.temp_dir
        )
        self.assertIsNotNone(item)
        self.assertEqual(len(self.mgr.items), 1)
        self.assertEqual(item.filename, "sample.txt")

if __name__ == "__main__":
    unittest.main()
