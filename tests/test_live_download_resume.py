import os
import shutil
import tempfile
import time
import unittest
from PyQt6.QtCore import QCoreApplication
from archivevault.core.downloader import DownloadItem, DownloadWorker, STATUS_COMPLETED, STATUS_PAUSED
from archivevault.core.settings import settings

class TestLiveDownloadResume(unittest.TestCase):
    def setUp(self):
        self.app = QCoreApplication.instance() or QCoreApplication([])
        self.temp_dir = tempfile.mkdtemp()
        settings.chunk_size_kb = 32 # 32 KB chunks to test multi-chunk pausing

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_live_range_pause_and_resume(self):
        identifier = "Frankenstein1818Edition"
        filename = "Frankenstein.djvu" # ~1.8 MB file
        url = f"https://archive.org/download/{identifier}/{filename}"
        
        save_path = os.path.join(self.temp_dir, filename)
        part_path = f"{save_path}.part"

        item = DownloadItem(
            id="test_live_1",
            identifier=identifier,
            filename=filename,
            url=url,
            save_path=save_path,
            part_path=part_path,
            total_bytes=1838121
        )

        print(f"\n[Test] Step 1: Initiating download of {filename} ({item.total_bytes} bytes)...")
        worker = DownloadWorker(item)
        worker.start()

        # Wait until at least 64 KB is downloaded, then pause
        start_wait = time.time()
        while item.downloaded_bytes < 65536 and time.time() - start_wait < 10:
            time.sleep(0.05)

        worker.pause()
        worker.wait(5000)

        # Verify .part file exists
        self.assertTrue(os.path.exists(part_path), "Expected .part file to exist after pause")
        partial_size = os.path.getsize(part_path)
        print(f"[Test] Step 2: Download paused successfully at {partial_size} bytes ({item.status}).")
        self.assertGreaterEqual(partial_size, 65536)
        self.assertEqual(item.status, STATUS_PAUSED)

        # Step 3: Resume download
        print(f"[Test] Step 3: Resuming download from byte offset {partial_size}...")
        item.status = "QUEUED"
        worker_resume = DownloadWorker(item)
        worker_resume.start()
        
        # Wait for completion or timeout
        worker_resume.wait(25000)

        # Step 4: Verify completed file
        self.assertEqual(item.status, STATUS_COMPLETED)
        self.assertTrue(os.path.exists(save_path), "Expected final file to exist after completion")
        self.assertFalse(os.path.exists(part_path), "Expected .part file to be removed after completion")
        final_size = os.path.getsize(save_path)
        print(f"[Test] Step 4: Resume completed successfully! Final file size: {final_size} bytes (matches original: {final_size == item.total_bytes}).")
        self.assertEqual(final_size, item.total_bytes)

if __name__ == "__main__":
    unittest.main()
