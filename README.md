# 🏛️ ArchiveVault — Internet Archive Downloader, Media Center & Retro Player

**ArchiveVault** is an all-in-one Windows desktop application built specifically for exploring, searching, streaming, and reliably downloading content from the [Internet Archive (archive.org)](https://archive.org) — the greatest digital library on Earth.

Built with **PyQt6**, ArchiveVault solves the most common frustration with Internet Archive downloads: interrupted connections on large files. With true **HTTP Range-based chunk streaming**, you can pause, resume, and recover downloads seamlessly anytime — even across massive archives with 40,000+ files.

---

## ✨ Features

- ⏸️ **True Pause & Resume Download Engine**:
  - Leverages HTTP `Range: bytes={offset}-` headers to resume partially downloaded `.part` files byte-for-byte.
  - Automatic reconnection with exponential backoff on dropped Wi-Fi / network blips.
  - Pause individual downloads or all downloads at once with a single click.
  - **Persistent Queue**: Downloads and pause states are preserved in local storage (`queue.json`), allowing you to close the app, reboot your PC, and resume right where you left off.
  - Ultra-optimized for massive archives: debounced I/O and $O(1)$ item indexing capable of running smoothly with queues containing **40,000+ files**.
  - Real-time rolling speed measurement, estimated time remaining (ETA), and progress bars.
  - Native Windows integration: "Open Containing Folder" and "Open File".

- ⚡ **In-App Torrent & Archive Batch Processor**:
  - Inspect and process any `.torrent` file or full collection metadata directly inside ArchiveVault — **no external BitTorrent client or open ports required**.
  - Multi-select, filter by extension, and download individual files or entire 40,000+ ROM sets via direct high-speed HTTP resume.
  - Live metadata upgrade engine: automatically synchronizes stale `.torrent` file lists with live Archive.org item manifests.

- 🎬 **In-App Video Cinema**:
  - Stream and watch movies, documentaries, and vintage video directly inside the app without external media players.
  - Supports MP4, WebM, MKV, AVI, and more with full transport controls.

- 🎵 **In-App Hi-Fi Audio Player**:
  - Stream and play live music concerts, vintage 78rpm/vinyl transfers, radio broadcasts, and audiobooks.
  - Continuous playback, seek bar, volume control, and metadata display.

- 🎮 **Retro Arcade & Classic Game Player**:
  - Built-in embedded DOSBox and retro emulation integration.
  - 1-click play for vintage MS-DOS games, Amstrad CPC, Amiga, C64, Atari, and arcade software libraries directly from Archive.org.

- 🔍 **Search & Explore**:
  - Search across millions of items: vintage MS-DOS games, console ROMs, classic movies, audio recordings, books, magazines, and ISO disc images.
  - Filter by category: *Retro Games*, *Feature Films*, *78rpm & Vinyl*, *Live Music*, *Books & Mags*, *Software Vault*.
  - Sort by *Most Downloads*, *Date Added (Newest)*, *Weekly Trending*, or *Title (A-Z)*.
  - Async cached thumbnails and metadata preview cards.
  - **Quick Item / URL Resolver**: Directly paste any Archive.org URL (e.g. `https://archive.org/details/...`) or item identifier to jump straight to file inspection.

- 📂 **Item Inspector & File Browser**:
  - View full item details: description, creator, upload date, collections, and total size.
  - Browse every file within an item with real-time name and extension filtering.
  - Format filters: ISO disc images, ZIP/7z archives, MP3/FLAC audio, MP4/MKV video, PDF/EPUB documents.
  - Convenient selection helpers: "Select All", "Select Originals" (avoids downloading derivative preview files/torrents), or select custom files.
  - Download individual files or batch download selected files to the queue.

- 🔐 **Internet Archive Account Integration**:
  - Full support for Archive.org S3 API keys (`Access Key` + `Secret Key`).
  - Access keys bypass anonymous IP rate limits and grant access to restricted or member collections.
  - Direct 1-click link to generate your free keys at [archive.org/account/s3.php](https://archive.org/account/s3.php).
  - Built-in credential test tool.
  - Auto-imports existing credentials if you have used the official `ia` CLI (`~/.ia` or `~/.config/ia.ini`).

- ⚙️ **Customizable Preferences**:
  - Choose your custom download directory.
  - Optional automatic subfolder organization per item (`Downloads/InternetArchive/<item-id>/<file>`).
  - Configurable concurrency (1 to 6 simultaneous downloads).
  - Streaming chunk size tuning (128 KB, 256 KB, 512 KB, 1024 KB).
  - Optional auto-resume of unfinished downloads on application launch.
  - Dark modern theme.

---

## 🚀 Quick Start on Windows

### 1. Launch with Batch Script
Double-click `launch_app.bat` inside this folder:
```cmd
launch_app.bat
```

### 2. Launch with `uv` or Python
From PowerShell or Command Prompt:
```powershell
uv run python run.py
```

---

## 🧪 Testing & Verification

ArchiveVault includes automated unit tests verifying API calls, UI components, and live HTTP Range pause/resume operations against the Internet Archive:

```powershell
python -m unittest discover tests
```

---

## 📁 Project Structure

```
Archive-Vault/
├── launch_app.bat                 # 1-click launcher for Windows Explorer
├── create_desktop_shortcut.bat    # Creates desktop shortcut for 1-click launch
├── run.py                         # Application entry point
├── pyproject.toml                 # Project configuration and dependencies
├── README.md                      # Documentation
├── archivevault/
│   ├── core/
│   │   ├── api.py                 # Archive.org search, metadata, and auth APIs
│   │   ├── downloader.py          # Range-based worker and debounced queue manager
│   │   ├── settings.py            # Persistent settings and IA CLI config loader
│   │   ├── torrent.py             # Torrent metadata parsing & live manifest builder
│   │   └── utils.py               # Size/speed formatting, file management helpers
│   └── ui/
│       ├── main_window.py         # Main shell with sidebar navigation
│       ├── styles.py              # Dark theme styling & color palettes
│       ├── search_tab.py          # Search & browse with 3-tier layout & async thumbnails
│       ├── item_tab.py            # Item details, file filter, and batch downloader
│       ├── downloads_tab.py       # Queue table with in-place updates & action buttons
│       ├── audio_player.py        # Hi-Fi audio player widget & stream controller
│       ├── video_player.py        # Video player dialog & cinema view
│       ├── dosbox_player.py       # Retro arcade & DOSBox emulation runner
│       ├── torrent_dialog.py      # Torrent & full archive batch inspector
│       └── settings_tab.py        # Account credentials and download options
└── tests/
    ├── test_api.py                # Search and API unit tests
    ├── test_audio.py              # Audio player and format tests
    ├── test_dosbox.py             # Emulation tests
    ├── test_downloader.py         # Queue management tests
    ├── test_live_download_resume.py# Real pause/resume verification against IA
    ├── test_torrent.py            # Torrent parser tests
    ├── test_ui.py                 # PyQt6 window and navigation tests
    └── test_video.py              # Video player tests
```

---

## 💡 Pro Tips

1. **Get your S3 Keys**: Visit [archive.org/account/s3.php](https://archive.org/account/s3.php) while logged into your Internet Archive account, generate your S3 keys, and paste them into the **Settings** tab.
2. **Selective Downloads**: When downloading software collections or multi-disc games, use the **Item Inspector** to download only the `.iso` or `.bin/.cue` you need without pulling unnecessary derived preview files.
3. **Closing the App**: If you need to restart or shut down your PC during large downloads, click **Pause All** or simply close the application. Your downloaded progress is safely preserved in `.part` files, and you can resume right where you left off when you open ArchiveVault again.
4. **Massive ROM Sets**: You can process 40,000+ file collections smoothly. ArchiveVault automatically caches and optimizes memory and disk I/O to keep Windows running fast.
