# 🏛️ ArchiveVault — Internet Archive Downloader, Media Center & Retro Arcade

**ArchiveVault** is an all-in-one desktop & mobile suite built specifically for exploring, searching, streaming, and reliably downloading content from the [Internet Archive (archive.org)](https://archive.org) — the greatest digital library on Earth.

Built with **PyQt6** on desktop and **Kotlin / Jetpack Compose** on mobile, ArchiveVault solves the most common frustration with Internet Archive downloads: interrupted connections on large files. With true **HTTP Range-based chunk streaming**, you can pause, resume, and recover downloads seamlessly anytime — even across massive archives with 40,000+ files.

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

- 🕹️ **Dedicated DOSBox Retro Arcade & Emulator**:
  - **Direct Menu Access**: Dedicated sidebar button to access retro gaming instantly without needing to search for an item first.
  - **Hard Drive Game Loader**: Click *"📁 Load Game from Hard Drive..."* to select any game or executable (`.exe`, `.com`, `.bat`, `.zip`, `.iso`, `.rom`, `.dsk`, `.adf`, `.cpr`) from your PC and launch it immediately.
  - **Local Games Library Scanner**: Automatically indexes downloaded ROMs and games from your download repository with 1-click launch and folder access.
  - **Native DOSBox & LaunchBox Integration**: Automatically discovers local DOSBox installations (e.g. `LaunchBox\ThirdParty\DOSBox\DOSBox.exe` or standard DOSBox) with custom path configuration in Settings.
  - **In-App WebAssembly Retro Theater**: Full-screen in-app player with CRT scanlines, native controller / gamepad auto-mapping (Xbox, PlayStation, USB), aspect ratio toggling, and microcomputer command auto-typing (Amstrad CPC, C64, ZX Spectrum).
  - **Instant Classics Gallery**: 1-click play for legendary titles: *Doom*, *Prince of Persia*, *The Secret of Monkey Island*, *SimCity 2000*, *Wolfenstein 3D*, *Pac-Man*, *Street Fighter II*, and *Amstrad CPC*.

- ⚡ **In-App Torrent & Archive Batch Processor**:
  - Inspect and process any `.torrent` file or full collection metadata directly inside ArchiveVault — **no external BitTorrent client or open ports required**.
  - Multi-select, filter by extension, and download individual files or entire 40,000+ ROM sets via direct high-speed HTTP resume.
  - Live metadata upgrade engine: automatically synchronizes stale `.torrent` file lists with live Archive.org item manifests.

- 🎬 **In-App Video Cinema**:
  - Stream and watch movies, documentaries, and vintage video directly inside the app without external media players.
  - Supports MP4, WebM, MKV, AVI, and more with full transport controls and Zen Mode fullscreen.

- 🎵 **In-App Hi-Fi Audio Player**:
  - Stream and play live music concerts, vintage 78rpm/vinyl transfers, radio broadcasts, and audiobooks.
  - Continuous playback, persistent dock across tabs, seek bar, and volume controls.

- 🔍 **Search & Explore**:
  - Search across millions of items: vintage MS-DOS games, console ROMs, classic movies, audio recordings, books, magazines, and ISO disc images.
  - Filter by category: *Retro Games*, *Feature Films*, *78rpm & Vinyl*, *Live Music*, *Books & Mags*, *Software Vault*.
  - Sort by *Most Downloads*, *Date Added (Newest)*, *Weekly Trending*, or *Title (A-Z)*.
  - Async cached thumbnails and metadata preview cards.
  - **Quick Item / URL Resolver**: Directly paste any Archive.org URL (e.g. `https://archive.org/details/...`) or item identifier to jump straight to file inspection.

- 📖 **Subject Dossier & Curated Vault**:
  - Magazine-style feature article with historical context and documentation.
  - High-visibility vertical scrollbars (`ScrollBarAlwaysOn`) so you can immediately see and scroll down to all curated files when opening an item fresh.
  - Formatted, unclipped action buttons for 1-click downloads or batch archive processing.

- 🔐 **Internet Archive Account Integration**:
  - Full support for Archive.org S3 API keys (`Access Key` + `Secret Key`).
  - Access keys bypass anonymous IP rate limits and grant access to restricted or member collections.
  - Built-in credential test tool.
  - Auto-imports existing credentials if you have used the official `ia` CLI (`~/.ia` or `~/.config/ia.ini`).

- 📱 **Native Android App (`android/`)**:
  - Full-featured companion Android app built with Kotlin, Jetpack Compose, and Material 3.
  - Background pausable download service, background audio player, and on-screen virtual gamepads for mobile DOSBox gaming.

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

## 📱 Android App Setup

The `android/` directory contains the native Android companion project:
* Open `android/` in **Android Studio**.
* Build and deploy directly to your Android device or emulator.
* Includes background downloader service, touch gamepads, and persistent media player.

---

## 🧪 Testing & Verification

ArchiveVault includes automated unit tests verifying API calls, UI components, DOSBox integration, and live HTTP Range pause/resume operations against the Internet Archive:

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
├── android/                       # Native Android application (Kotlin + Jetpack Compose)
│   ├── app/                       # Android app module (sources, manifests, resources)
│   ├── gradle/                    # Gradle wrapper
│   ├── build.gradle.kts           # Root Gradle build configuration
│   └── settings.gradle.kts        # Android settings
├── archivevault/                  # Core desktop application (Python / PyQt6)
│   ├── core/
│   │   ├── api.py                 # Archive.org search, metadata, and auth APIs
│   │   ├── downloader.py          # Range-based worker and debounced queue manager
│   │   ├── settings.py            # Persistent settings, DOSBox path & IA credentials
│   │   ├── torrent.py             # Torrent metadata parsing & live manifest builder
│   │   └── utils.py               # Size/speed formatting, DOSBox and 7-Zip launcher
│   └── ui/
│       ├── main_window.py         # Main shell with sidebar navigation
│       ├── styles.py              # Dark theme styling, high-visibility scrollbars
│       ├── search_tab.py          # Search & browse with 3-tier layout & async thumbnails
│       ├── item_tab.py            # Subject dossier, always-on scrollbar & batch downloader
│       ├── arcade_tab.py          # Dedicated DOSBox Arcade, hard drive game browser & classics
│       ├── downloads_tab.py       # Queue table with in-place updates & action buttons
│       ├── audio_player.py        # Hi-Fi audio player widget & stream controller
│       ├── video_player.py        # Video player dialog & cinema view
│       ├── dosbox_player.py       # Retro arcade & DOSBox emulation runner
│       ├── torrent_dialog.py      # Torrent & full archive batch inspector
│       └── settings_tab.py        # Account credentials, DOSBox path and download options
└── tests/
    ├── test_api.py                # Search and API unit tests
    ├── test_audio.py              # Audio player and format tests
    ├── test_dosbox.py             # Emulation & ArcadeTab tests
    ├── test_downloader.py         # Queue management tests
    ├── test_live_download_resume.py# Real pause/resume verification against IA
    ├── test_torrent.py            # Torrent parser tests
    ├── test_ui.py                 # PyQt6 window and 5-page navigation tests
    └── test_video.py              # Video player tests
```
