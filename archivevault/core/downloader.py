import json
import os
import sys
import time
import urllib.parse
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional
import requests
from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal

from archivevault.core.api import ia_api
from archivevault.core.settings import settings
from archivevault.core.utils import format_eta, format_size, format_speed, sanitize_filename

# Download statuses
STATUS_QUEUED = "QUEUED"
STATUS_DOWNLOADING = "DOWNLOADING"
STATUS_PAUSED = "PAUSED"
STATUS_COMPLETED = "COMPLETED"
STATUS_FAILED = "FAILED"
STATUS_CANCELLED = "CANCELLED"

@dataclass
class DownloadItem:
    id: str
    identifier: str
    filename: str
    url: str
    save_path: str
    part_path: str
    total_bytes: int
    downloaded_bytes: int = 0
    status: str = STATUS_QUEUED
    speed: float = 0.0
    eta: float = 0.0
    error_message: str = ""
    created_at: float = 0.0
    completed_at: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "DownloadItem":
        return cls(**data)

class DownloadWorkerSignals(QObject):
    progress = pyqtSignal(str, 'qint64', 'qint64', float, float) # item_id, downloaded, total, speed, eta
    status_changed = pyqtSignal(str, str, str)         # item_id, status, error_message

class DownloadWorker(QThread):
    """
    Dedicated worker thread for handling a single file download with
    full HTTP Range-based pause and resume capabilities.
    """
    
    def __init__(self, item: DownloadItem, parent=None):
        super().__init__(parent)
        self.item = item
        self.signals = DownloadWorkerSignals()
        self._is_paused = False
        self._is_cancelled = False
        self.max_retries = 5

    def pause(self):
        self._is_paused = True

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        item = self.item
        self._is_paused = False
        self._is_cancelled = False

        # Ensure parent directory exists
        os.makedirs(os.path.dirname(os.path.abspath(item.save_path)), exist_ok=True)

        retry_count = 0
        while retry_count <= self.max_retries and not self._is_paused and not self._is_cancelled:
            try:
                self._download_loop()
                break
            except Exception as e:
                if self._is_paused or self._is_cancelled:
                    break
                retry_count += 1
                if retry_count > self.max_retries:
                    err_msg = f"Download failed after {self.max_retries} attempts: {e}"
                    item.status = STATUS_FAILED
                    item.error_message = err_msg
                    self.signals.status_changed.emit(item.id, STATUS_FAILED, err_msg)
                    return
                else:
                    backoff = min(2 ** retry_count, 15)
                    self.signals.status_changed.emit(
                        item.id,
                        STATUS_DOWNLOADING,
                        f"Network drop. Reconnecting in {backoff}s (attempt {retry_count}/{self.max_retries})..."
                    )
                    time.sleep(backoff)

    def _download_loop(self):
        item = self.item
        part_path = item.part_path
        
        # Determine existing byte count from .part file
        current_offset = 0
        if os.path.exists(part_path):
            current_offset = os.path.getsize(part_path)
            
        # If .part is already full size
        if item.total_bytes > 0 and current_offset >= item.total_bytes:
            self._finalize_file()
            return

        headers = ia_api.get_headers()
        open_mode = "ab" if current_offset > 0 else "wb"
        
        if current_offset > 0:
            headers["Range"] = f"bytes={current_offset}-"
            
        chunk_size = max(16, settings.chunk_size_kb) * 1024
        
        self.signals.status_changed.emit(item.id, STATUS_DOWNLOADING, "")

        session = ia_api.get_session()
        with session.get(item.url, headers=headers, stream=True, timeout=30) as resp:
            # Check response status
            if resp.status_code == 416: # Range Not Satisfiable
                if item.total_bytes > 0 and current_offset >= item.total_bytes:
                    self._finalize_file()
                    return
                # Server disagrees with offset, restart from 0
                current_offset = 0
                open_mode = "wb"
                headers.pop("Range", None)
                resp = session.get(item.url, headers=headers, stream=True, timeout=30)

            if resp.status_code in (401, 403):
                err_msg = "Internet Archive login required for this item. Add free S3 keys in Settings."
                item.status = STATUS_FAILED
                item.error_message = err_msg
                self.signals.status_changed.emit(item.id, STATUS_FAILED, err_msg)
                self._is_cancelled = True
                return

            if resp.status_code not in (200, 206):
                resp.raise_for_status()

            # If server sent 200 instead of 206 on range request, range wasn't accepted
            if current_offset > 0 and resp.status_code == 200:
                current_offset = 0
                open_mode = "wb"

            # Parse content length / total size if not already set or invalid
            content_length = resp.headers.get("Content-Length")
            if content_length:
                try:
                    cl = int(content_length)
                    if cl > 0:
                        if resp.status_code == 206:
                            # Content-Range: bytes START-END/TOTAL
                            content_range = resp.headers.get("Content-Range")
                            if content_range and "/" in content_range:
                                try:
                                    cr_tot = int(content_range.split("/")[-1])
                                    if cr_tot > 0:
                                        item.total_bytes = cr_tot
                                except ValueError:
                                    item.total_bytes = current_offset + cl
                            else:
                                item.total_bytes = current_offset + cl
                        else:
                            item.total_bytes = cl
                except (ValueError, TypeError):
                    pass

            downloaded = current_offset
            item.downloaded_bytes = downloaded

            # Rolling speed calculator
            window_size = 1.5 # seconds
            samples = [] # [(timestamp, bytes_count)]
            samples.append((time.time(), downloaded))
            last_progress_emit = 0.0

            with open(part_path, open_mode) as f:
                for chunk in resp.iter_content(chunk_size=chunk_size):
                    if self._is_paused:
                        f.flush()
                        item.status = STATUS_PAUSED
                        item.downloaded_bytes = downloaded
                        item.speed = 0.0
                        self.signals.status_changed.emit(item.id, STATUS_PAUSED, "Paused by user")
                        return

                    if self._is_cancelled:
                        f.flush()
                        item.status = STATUS_CANCELLED
                        self.signals.status_changed.emit(item.id, STATUS_CANCELLED, "Cancelled")
                        return

                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        item.downloaded_bytes = downloaded

                        now = time.time()
                        samples.append((now, downloaded))

                        # Purge old speed samples
                        while samples and (now - samples[0][0]) > window_size:
                            samples.pop(0)

                        # Emit throttled progress update (up to 4 times per second)
                        if (now - last_progress_emit) >= 0.25:
                            if len(samples) > 1:
                                dt = now - samples[0][0]
                                db = downloaded - samples[0][1]
                                speed = (db / dt) if dt > 0 else 0.0
                            else:
                                speed = 0.0

                            item.speed = speed
                            remaining_bytes = max(0, item.total_bytes - downloaded)
                            eta = (remaining_bytes / speed) if speed > 0 else 0.0
                            item.eta = eta

                            self.signals.progress.emit(
                                item.id,
                                downloaded,
                                item.total_bytes,
                                speed,
                                eta
                            )
                            last_progress_emit = now

                f.flush()

        # Download stream completed successfully
        self._finalize_file()

    def _finalize_file(self):
        item = self.item
        part_path = item.part_path
        save_path = item.save_path

        # Verify sizes if total_bytes is known
        if os.path.exists(part_path):
            actual_size = os.path.getsize(part_path)
            item.downloaded_bytes = actual_size
            if item.total_bytes == 0:
                item.total_bytes = actual_size

            # Atomic / safe rename on Windows
            if os.path.exists(save_path):
                try:
                    os.remove(save_path)
                except Exception:
                    pass
            os.rename(part_path, save_path)

        item.status = STATUS_COMPLETED
        item.speed = 0.0
        item.eta = 0.0
        item.completed_at = time.time()
        self.signals.progress.emit(item.id, item.total_bytes, item.total_bytes, 0.0, 0.0)
        self.signals.status_changed.emit(item.id, STATUS_COMPLETED, "")

class DownloadManager(QObject):
    """
    Central manager for download queue, concurrency control,
    persistence, and thread orchestration.
    """
    queue_updated = pyqtSignal()
    item_progress = pyqtSignal(str, 'qint64', 'qint64', float, float)
    item_status = pyqtSignal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.items: List[DownloadItem] = []
        self._items_by_id: Dict[str, DownloadItem] = {}
        self.workers: Dict[str, DownloadWorker] = {}
        self._last_save_time: float = 0.0
        self._save_pending: bool = False
        self._save_timer = QTimer(self)
        self._save_timer.setInterval(3000)
        self._save_timer.timeout.connect(self._flush_pending_save)
        self._save_timer.start()
        self.load_queue()

    def _flush_pending_save(self):
        if self._save_pending:
            self.save_queue(force=True)

    def load_queue(self):
        """Restore previous downloads from persistent JSON file."""
        if os.path.exists(settings.queue_file):
            try:
                with open(settings.queue_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.items = [DownloadItem.from_dict(d) for d in data]
                    # Reset any active states to PAUSED on application boot
                    for item in self.items:
                        if item.status == STATUS_DOWNLOADING:
                            item.status = STATUS_PAUSED
                            item.speed = 0.0
                            item.eta = 0.0
                        if item.total_bytes < 0:
                            # Heal 32-bit signed overflow if previous run recorded corrupted value
                            item.total_bytes = 0
                    self._items_by_id = {it.id: it for it in self.items}
            except Exception as e:
                print(f"[DownloadManager] Error loading queue: {e}")
                self.items = []
                self._items_by_id = {}

    def save_queue(self, force: bool = False):
        """Save queue state to disk with throttling and atomic replacement."""
        now = time.time()
        if not force and (now - self._last_save_time) < 3.0:
            self._save_pending = True
            return

        self._save_pending = False
        self._last_save_time = now
        try:
            data = [item.to_dict() for item in self.items]
            tmp_file = f"{settings.queue_file}.tmp"
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, separators=(',', ':'))
            if os.path.exists(settings.queue_file):
                try:
                    os.remove(settings.queue_file)
                except Exception:
                    pass
            os.replace(tmp_file, settings.queue_file)
        except Exception as e:
            print(f"[DownloadManager] Error saving queue: {e}")

    def add_download(
        self,
        identifier: str,
        filename: str,
        url: str,
        total_bytes: int,
        target_dir: Optional[str] = None
    ) -> DownloadItem:
        """Add a file to the download queue."""
        clean_filename = sanitize_filename(filename)
        
        base_dir = target_dir or settings.download_dir
        if settings.create_item_subfolders:
            item_folder = sanitize_filename(identifier)
            save_dir = os.path.join(base_dir, item_folder)
        else:
            save_dir = base_dir
            
        os.makedirs(save_dir, exist_ok=True)
        
        save_path = os.path.join(save_dir, clean_filename)
        part_path = f"{save_path}.part"
        
        # Check if already in queue
        for existing in self.items:
            if existing.url == url and existing.status in (STATUS_QUEUED, STATUS_DOWNLOADING, STATUS_PAUSED):
                return existing

        item_id = f"{identifier}_{clean_filename}_{int(time.time() * 1000)}"
        
        # Check if partial download already exists on disk
        downloaded = 0
        if os.path.exists(part_path):
            downloaded = os.path.getsize(part_path)

        item = DownloadItem(
            id=item_id,
            identifier=identifier,
            filename=clean_filename,
            url=url,
            save_path=save_path,
            part_path=part_path,
            total_bytes=total_bytes,
            downloaded_bytes=downloaded,
            status=STATUS_QUEUED,
            created_at=time.time()
        )
        self.items.append(item)
        self._items_by_id[item.id] = item
        self.save_queue()
        self.queue_updated.emit()
        self._process_queue()
        return item

    def add_batch_downloads(self, file_specs: List[dict], identifier: str):
        """Add multiple files from an item to the queue efficiently in a single batch."""
        base_dir = settings.download_dir
        if settings.create_item_subfolders:
            item_folder = sanitize_filename(identifier)
            save_dir = os.path.join(base_dir, item_folder)
        else:
            save_dir = base_dir
            
        os.makedirs(save_dir, exist_ok=True)
        existing_urls = {existing.url for existing in self.items if existing.status in (STATUS_QUEUED, STATUS_DOWNLOADING, STATUS_PAUSED)}

        now = time.time()
        new_items = []
        for i, spec in enumerate(file_specs):
            url = spec.get("download_url") or spec.get("url", "")
            if not url and identifier and spec.get("name"):
                url = f"https://archive.org/download/{identifier}/{urllib.parse.quote(spec['name'], safe='/')}"
            
            if not url or url in existing_urls:
                continue
            existing_urls.add(url)

            rel_path = spec.get("path") or spec.get("name", "download.bin")
            norm_rel = os.path.normpath(rel_path).lstrip("/\\")
            clean_filename = sanitize_filename(os.path.basename(norm_rel))
            subdirs = os.path.dirname(norm_rel)
            if subdirs:
                target_folder = os.path.join(save_dir, subdirs)
                os.makedirs(target_folder, exist_ok=True)
                save_path = os.path.join(target_folder, clean_filename)
            else:
                save_path = os.path.join(save_dir, clean_filename)
            part_path = f"{save_path}.part"

            downloaded = 0
            if os.path.exists(part_path):
                try:
                    downloaded = os.path.getsize(part_path)
                except OSError:
                    downloaded = 0

            item = DownloadItem(
                id=f"{identifier}_{clean_filename}_{int((now + i*0.001) * 1000)}",
                identifier=identifier,
                filename=clean_filename,
                url=url,
                save_path=save_path,
                part_path=part_path,
                total_bytes=spec.get("size_bytes", 0),
                downloaded_bytes=downloaded,
                status=STATUS_QUEUED,
                created_at=now + i * 0.001
            )
            new_items.append(item)

        if new_items:
            self.items.extend(new_items)
            for it in new_items:
                self._items_by_id[it.id] = it
            self.save_queue()
            self.queue_updated.emit()
            self._process_queue()

    def get_item(self, item_id: str) -> Optional[DownloadItem]:
        """Fast O(1) item lookup by ID."""
        return self._items_by_id.get(item_id)

    def get_total_speed(self) -> float:
        """Fast aggregate speed across active workers only."""
        return sum(w.item.speed for w in self.workers.values() if w.isRunning() and w.item.status == STATUS_DOWNLOADING)

    def pause_download(self, item_id: str):
        """Pause an active or queued download."""
        if item_id in self.workers:
            self.workers[item_id].pause()
        item = self._items_by_id.get(item_id)
        if item and item.status in (STATUS_QUEUED, STATUS_DOWNLOADING):
            item.status = STATUS_PAUSED
            item.speed = 0.0
            item.eta = 0.0
            self.item_status.emit(item_id, STATUS_PAUSED, "Paused by user")
        self.save_queue()
        QTimer.singleShot(0, self._process_queue)

    def resume_download(self, item_id: str):
        """Resume a paused or failed download."""
        item = self._items_by_id.get(item_id)
        if item:
            item.status = STATUS_QUEUED
            item.error_message = ""
            self.item_status.emit(item_id, STATUS_QUEUED, "")
        self.save_queue()
        QTimer.singleShot(0, self._process_queue)

    def cancel_download(self, item_id: str, delete_part: bool = True):
        """Cancel and remove a download."""
        if item_id in self.workers:
            self.workers[item_id].cancel()
            
        target_item = self._items_by_id.pop(item_id, None)
        if target_item:
            if delete_part and os.path.exists(target_item.part_path):
                try:
                    os.remove(target_item.part_path)
                except Exception:
                    pass
            try:
                self.items.remove(target_item)
            except ValueError:
                pass
            
        self.save_queue()
        self.queue_updated.emit()
        QTimer.singleShot(0, self._process_queue)

    def pause_all(self):
        for item in self.items:
            if item.status in (STATUS_QUEUED, STATUS_DOWNLOADING):
                self.pause_download(item.id)

    def resume_all(self):
        for item in self.items:
            if item.status in (STATUS_PAUSED, STATUS_FAILED):
                item.status = STATUS_QUEUED
        self.save_queue()
        self.queue_updated.emit()
        QTimer.singleShot(0, self._process_queue)

    def clear_completed(self):
        self.items = [i for i in self.items if i.status != STATUS_COMPLETED]
        self._items_by_id = {it.id: it for it in self.items}
        self.save_queue()
        self.queue_updated.emit()

    def _process_queue(self):
        """Ensure active downloads match settings.max_concurrent_downloads."""
        # Clean finished workers
        finished_ids = [k for k, w in self.workers.items() if not w.isRunning()]
        for fid in finished_ids:
            del self.workers[fid]

        active_count = len(self.workers)
        if active_count >= settings.max_concurrent_downloads:
            return

        for item in self.items:
            if item.status == STATUS_QUEUED:
                self._start_worker(item)
                active_count += 1
                if active_count >= settings.max_concurrent_downloads:
                    break

    def _start_worker(self, item: DownloadItem):
        item.status = STATUS_DOWNLOADING
        worker = DownloadWorker(item)
        worker.signals.progress.connect(self._on_worker_progress)
        worker.signals.status_changed.connect(self._on_worker_status)
        self.workers[item.id] = worker
        worker.start()
        self.item_status.emit(item.id, STATUS_DOWNLOADING, "")

    def _on_worker_progress(self, item_id: str, downloaded: int, total: int, speed: float, eta: float):
        item = self._items_by_id.get(item_id)
        if item:
            item.downloaded_bytes = downloaded
            item.total_bytes = total
            item.speed = speed
            item.eta = eta
        self.item_progress.emit(item_id, downloaded, total, speed, eta)

    def _on_worker_status(self, item_id: str, status: str, error_message: str):
        item = self._items_by_id.get(item_id)
        if item:
            item.status = status
            item.error_message = error_message
            if status == STATUS_COMPLETED:
                item.speed = 0.0
                item.eta = 0.0
        self.save_queue()
        self.item_status.emit(item_id, status, error_message)
        # Defer next queue processing back to event loop to avoid call-stack recursion
        QTimer.singleShot(0, self._process_queue)

_manager_instance: Optional[DownloadManager] = None

def get_download_manager() -> DownloadManager:
    global _manager_instance
    if _manager_instance is not None:
        try:
            # Check if underlying Qt C++ object is alive
            _manager_instance.objectName()
        except RuntimeError:
            _manager_instance = None
    if _manager_instance is None:
        _manager_instance = DownloadManager()
    return _manager_instance

class _DownloadManagerProxy:
    """Proxy object so callers can import download_manager directly."""
    def __getattr__(self, name):
        return getattr(get_download_manager(), name)

download_manager = _DownloadManagerProxy()

