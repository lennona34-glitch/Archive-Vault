import html
import urllib.parse
from typing import Dict, List, Optional
import requests
from PyQt6.QtCore import QObject, QSize, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from archivevault.core.api import ia_api
from archivevault.core.utils import extract_identifier, format_size
from archivevault.ui.styles import get_mediatype_badge_color

# Thread-safe in-memory thumbnail cache
_THUMB_CACHE: Dict[str, QPixmap] = {}

CURATED_COLLECTIONS = {
    "trending": {
        "title": "🔥 Popular Classics & Highlights",
        "query": "collection:(softwarelibrary_msdos_games OR feature_films OR audio_music) AND NOT mediatype:collection",
        "sort": "-downloads",
        "mediatype": None,
    },
    "games": {
        "title": "🎮 MS-DOS & Retro Games",
        "query": "collection:softwarelibrary_msdos_games AND mediatype:software",
        "sort": "-downloads",
        "mediatype": "software",
    },
    "movies": {
        "title": "🎬 Classic Feature Films & Sci-Fi",
        "query": "collection:feature_films AND mediatype:movies",
        "sort": "-downloads",
        "mediatype": "movies",
    },
    "records": {
        "title": "📻 Historic 78rpm & Vinyl Records",
        "query": "collection:(georgeblood OR 78rpm OR 78rpm_unfiltered OR album_recordings OR vinylrecords) AND NOT mediatype:collection",
        "sort": "-downloads",
        "mediatype": "audio",
    },
    "music": {
        "title": "🎵 Live Music & Audio Archive",
        "query": "collection:(etree OR audio_music OR 78rpm OR album_recordings) AND mediatype:(audio OR etree)",
        "sort": "-downloads",
        "mediatype": None,
    },
    "books": {
        "title": "📚 Vintage Magazines & Literature",
        "query": "collection:computermagazines AND mediatype:texts",
        "sort": "-downloads",
        "mediatype": "texts",
    },
    "software": {
        "title": "💿 Software & Disc Image Archives",
        "query": "collection:(tosec OR classicpcgames) AND mediatype:software",
        "sort": "-downloads",
        "mediatype": "software",
    },
}

FEATURED_LANDMARKS = [
    {
        "identifier": "msdos_Oregon_Trail_The_1990",
        "title": "The Oregon Trail (MS-DOS, 1990)",
        "mediatype": "software",
        "year": "1990",
        "downloads": 13973361,
        "description": "The quintessential pioneer survival simulation game produced by MECC.",
        "creator": "MECC",
        "thumbnail_url": "https://archive.org/services/img/msdos_Oregon_Trail_The_1990",
        "details_url": "https://archive.org/details/msdos_Oregon_Trail_The_1990"
    },
    {
        "identifier": "msdos_Prince_of_Persia_1990",
        "title": "Prince of Persia (MS-DOS, 1990)",
        "mediatype": "software",
        "year": "1990",
        "downloads": 2164473,
        "description": "Jordan Mechner's legendary cinematic rotoscoped platformer.",
        "creator": "Brøderbund Software",
        "thumbnail_url": "https://archive.org/services/img/msdos_Prince_of_Persia_1990",
        "details_url": "https://archive.org/details/msdos_Prince_of_Persia_1990"
    },
    {
        "identifier": "NightOfTheLivingDead_1080p",
        "title": "Night of the Living Dead (1968, 1080p)",
        "mediatype": "movies",
        "year": "1968",
        "downloads": 4820120,
        "description": "George A. Romero's foundational horror classic in restored high definition.",
        "creator": "George A. Romero",
        "thumbnail_url": "https://archive.org/services/img/NightOfTheLivingDead_1080p",
        "details_url": "https://archive.org/details/NightOfTheLivingDead_1080p"
    },
    {
        "identifier": "GratefulDead",
        "title": "Grateful Dead Live Concert Archive",
        "mediatype": "audio",
        "year": "1977",
        "downloads": 230684040,
        "description": "Tens of thousands of live soundboard and audience recordings.",
        "creator": "Grateful Dead",
        "thumbnail_url": "https://archive.org/services/img/GratefulDead",
        "details_url": "https://archive.org/details/GratefulDead"
    },
    {
        "identifier": "byte-magazine-1977-09",
        "title": "Byte Magazine - Volume 02 Number 09 (1977)",
        "mediatype": "texts",
        "year": "1977",
        "downloads": 650000,
        "description": "The Small Systems Journal vintage computing magazine archive.",
        "creator": "McGraw-Hill",
        "thumbnail_url": "https://archive.org/services/img/byte-magazine-1977-09",
        "details_url": "https://archive.org/details/byte-magazine-1977-09"
    },
    {
        "identifier": "tosec",
        "title": "The TOSEC Software & ROM Archive",
        "mediatype": "software",
        "year": "2024",
        "downloads": 18500000,
        "description": "The Old School Emulation Center preservation project for classic systems.",
        "creator": "TOSEC Project",
        "thumbnail_url": "https://archive.org/services/img/tosec",
        "details_url": "https://archive.org/details/tosec"
    }
]

class SearchWorkerSignals(QObject):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

class SearchWorker(QThread):
    def __init__(self, query: str, mediatype: Optional[str], sort: str, page: int, rows: int = 24):
        super().__init__()
        self.query = query
        self.mediatype = mediatype
        self.sort = sort
        self.page = page
        self.rows = rows
        self.signals = SearchWorkerSignals()

    def run(self):
        try:
            results = ia_api.search(
                query=self.query,
                mediatype=self.mediatype,
                sort=self.sort,
                page=self.page,
                rows=self.rows
            )
            self.signals.finished.emit(results)
        except Exception as e:
            self.signals.error.emit(str(e))

class ThumbnailWorkerSignals(QObject):
    loaded = pyqtSignal(str, QPixmap)

class ThumbnailWorker(QThread):
    def __init__(self, identifier: str, url: str):
        super().__init__()
        self.identifier = identifier
        self.url = url
        self.signals = ThumbnailWorkerSignals()

    def run(self):
        if self.identifier in _THUMB_CACHE:
            self.signals.loaded.emit(self.identifier, _THUMB_CACHE[self.identifier])
            return

        try:
            resp = requests.get(self.url, headers={"User-Agent": "ArchiveVault/1.0"}, timeout=10)
            if resp.status_code == 200:
                pixmap = QPixmap()
                pixmap.loadFromData(resp.content)
                if not pixmap.isNull():
                    scaled = pixmap.scaled(
                        100, 100,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    _THUMB_CACHE[self.identifier] = scaled
                    self.signals.loaded.emit(self.identifier, scaled)
        except Exception:
            pass

class ItemCardWidget(QFrame):
    """
    Clickable subject banner in the opening menu.
    Clicking anywhere on the bar opens the full subject feature article & curated vault.
    """
    inspect_requested = pyqtSignal(str)

    def __init__(self, doc: dict, parent=None):
        super().__init__(parent)
        self.doc = doc
        self.setObjectName("card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Click to open subject article, play online, and view curated downloads")
        self._thumb_worker: Optional[ThumbnailWorker] = None
        self._init_ui()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.inspect_requested.emit(self.doc["identifier"])
        super().mousePressEvent(event)

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 16, 12)
        layout.setSpacing(16)

        # Left: Thumbnail Artwork
        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(96, 96)
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setStyleSheet("background-color: #27272a; border-radius: 8px; border: 1px solid #333338;")
        self.thumb_label.setText("📦")
        layout.addWidget(self.thumb_label)

        # Center: Info & Metadata
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        # Title & Badge row
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        mediatype = self.doc.get("mediatype", "data").upper()
        badge = QLabel(mediatype)
        badge_color = get_mediatype_badge_color(self.doc.get("mediatype", ""))
        badge.setStyleSheet(
            f"background-color: {badge_color}; color: #ffffff; font-size: 10px; "
            f"font-weight: 700; padding: 2px 7px; border-radius: 4px;"
        )
        badge.setFixedHeight(20)
        header_row.addWidget(badge)

        title_text = self.doc.get("title", "")
        title_label = QLabel(title_text)
        title_label.setStyleSheet("font-size: 15px; font-weight: 700; color: #f4f4f5;")
        title_label.setWordWrap(True)
        header_row.addWidget(title_label, stretch=1)
        info_layout.addLayout(header_row)

        # Meta line: Creator | Year | Views
        meta_parts = []
        creator = self.doc.get("creator")
        if creator:
            meta_parts.append(f"By {creator}")
        year = self.doc.get("year")
        if year:
            meta_parts.append(f"Year: {year}")
        downloads = self.doc.get("downloads", 0)
        meta_parts.append(f"👁️ {downloads:,} views")
        meta_label = QLabel(" • ".join(meta_parts))
        meta_label.setStyleSheet("font-size: 11px; color: #a1a1aa;")
        info_layout.addWidget(meta_label)

        # Description summary
        desc_text = self.doc.get("description", "")
        if desc_text:
            desc_label = QLabel(desc_text)
            desc_label.setStyleSheet("font-size: 12px; color: #71717a;")
            desc_label.setWordWrap(True)
            desc_label.setMaximumHeight(36)
            info_layout.addWidget(desc_label)

        layout.addLayout(info_layout, stretch=1)

        # Right: Clean Action Pill
        right_layout = QVBoxLayout()
        right_layout.setSpacing(6)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        m_type = self.doc.get("mediatype", "").lower()
        if m_type == "collection":
            pill_text = "📂 Explore Collection ➔"
            pill_style = "background-color: #065f46; color: #a7f3d0; border: 1px solid #047857; font-size: 12px; font-weight: 700; padding: 8px 16px; border-radius: 16px;"
            hint_text = "Browse collection items"
        elif m_type == "software":
            pill_text = "🎮 Play & Download ➔"
            pill_style = "background-color: #2563eb; color: #ffffff; border: 1px solid #1d4ed8; font-size: 12px; font-weight: 600; padding: 8px 16px; border-radius: 16px;"
            hint_text = "Play in-app or download"
        elif m_type in ("audio", "etree"):
            pill_text = "🎵 Listen & Download ➔"
            pill_style = "background-color: #d97706; color: #ffffff; border: 1px solid #b45309; font-size: 12px; font-weight: 600; padding: 8px 16px; border-radius: 16px;"
            hint_text = "Stream in-app or download"
        elif m_type in ("movies", "video"):
            pill_text = "🎬 Watch & Download ➔"
            pill_style = "background-color: #dc2626; color: #ffffff; border: 1px solid #b91c1c; font-size: 12px; font-weight: 600; padding: 8px 16px; border-radius: 16px;"
            hint_text = "Watch cinema or download"
        elif m_type == "texts":
            pill_text = "📖 Read & Download ➔"
            pill_style = "background-color: #7c3aed; color: #ffffff; border: 1px solid #6d28d9; font-size: 12px; font-weight: 600; padding: 8px 16px; border-radius: 16px;"
            hint_text = "Read book or download"
        else:
            pill_text = "Inspect & Download ➔"
            pill_style = "font-size: 12px; font-weight: 600; padding: 8px 16px; border-radius: 16px;"
            hint_text = "Click to explore"

        open_pill = QPushButton(pill_text)
        open_pill.setObjectName("primaryBtn")
        open_pill.setCursor(Qt.CursorShape.PointingHandCursor)
        open_pill.setStyleSheet(pill_style)
        open_pill.clicked.connect(lambda: self.inspect_requested.emit(self.doc["identifier"]))
        right_layout.addWidget(open_pill)

        hint_label = QLabel(hint_text)
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_label.setStyleSheet("font-size: 10px; color: #71717a;")
        right_layout.addWidget(hint_label)

        layout.addLayout(right_layout)

        self._load_thumbnail()

    def _copy_link(self):
        url = self.doc.get("details_url", f"https://archive.org/details/{self.doc['identifier']}")
        QApplication.clipboard().setText(url)

    def _load_thumbnail(self):
        ident = self.doc["identifier"]
        if ident in _THUMB_CACHE:
            self.thumb_label.setPixmap(_THUMB_CACHE[ident])
            self.thumb_label.setText("")
        else:
            self._thumb_worker = ThumbnailWorker(ident, self.doc["thumbnail_url"])
            self._thumb_worker.signals.loaded.connect(self._on_thumbnail_loaded)
            self._thumb_worker.start()

    def _on_thumbnail_loaded(self, ident: str, pixmap: QPixmap):
        if ident == self.doc["identifier"] and not pixmap.isNull():
            self.thumb_label.setPixmap(pixmap)
            self.thumb_label.setText("")

class SearchTab(QWidget):
    """
    Website-style Browse & Search experience with automatic
    curated trending collections on launch.
    """
    inspect_item_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_page = 1
        self.total_pages = 1
        self.current_collection_key = "trending"
        self._active_search_worker: Optional[SearchWorker] = None
        
        self._init_ui()
        
        # Instantly show curated landmark collection on launch!
        self._populate_docs(FEATURED_LANDMARKS)
        self.status_label.setText("Showing curated landmarks • Checking live feed...")
        
        # Background live refresh
        QTimer.singleShot(300, lambda: self._load_curated_collection("trending"))

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        # --- Top Section: Search Bar & Direct Link ---
        top_box = QFrame()
        top_box.setObjectName("card")
        top_layout = QVBoxLayout(top_box)
        top_layout.setContentsMargins(14, 12, 14, 12)
        top_layout.setSpacing(10)

        # Row 1: Search bar
        search_row = QHBoxLayout()
        search_row.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search millions of vintage software, MS-DOS games, movies, books, music, ISOs...")
        self.search_input.setStyleSheet("font-size: 13px; padding: 9px 12px;")
        self.search_input.returnPressed.connect(self._on_search_clicked)
        search_row.addWidget(self.search_input, stretch=1)

        self.search_btn = QPushButton("Search 🔍")
        self.search_btn.setObjectName("primaryBtn")
        self.search_btn.setStyleSheet("font-size: 13px; padding: 8px 18px;")
        self.search_btn.clicked.connect(self._on_search_clicked)
        search_row.addWidget(self.search_btn)

        self.direct_btn = QPushButton("Direct URL / ID ⚡")
        self.direct_btn.setToolTip("Quickly paste an Archive.org link or identifier")
        self.direct_btn.clicked.connect(self._prompt_direct_open)
        search_row.addWidget(self.direct_btn)

        top_layout.addLayout(search_row)

        # Row 2: Website-style Curated Category Pills
        pills_row = QHBoxLayout()
        pills_row.setSpacing(6)

        pill_label = QLabel("Browse:")
        pill_label.setStyleSheet("font-weight: 700; color: #38bdf8; font-size: 12px; margin-right: 2px;")
        pills_row.addWidget(pill_label)

        self.pill_group = QButtonGroup(self)
        self.pill_group.setExclusive(True)

        self.pills = {}
        pill_defs = [
            ("trending", "🔥 Trending", "Explore trending releases across Internet Archive"),
            ("games", "🎮 Retro Games", "Playable MS-DOS, arcade, and classic computer games"),
            ("movies", "🎬 Feature Films", "Public domain movies, vintage cartoons, and cinematic features"),
            ("records", "📻 78rpm & Vinyl", "Historic 78rpm shellac records and vinyl audio preservation"),
            ("music", "🎵 Live Music", "Live concert soundboard recordings and etree music archives"),
            ("books", "📚 Books & Mags", "Vintage computer magazines, literature, and periodicals"),
            ("software", "💿 Software Vault", "Operating systems, CD-ROMs, TOSEC, and utility disc images"),
        ]

        for idx, (key, label, tooltip) in enumerate(pill_defs):
            btn = QPushButton(label)
            btn.setObjectName("categoryPill")
            btn.setCheckable(True)
            btn.setToolTip(tooltip)
            if key == "trending":
                btn.setChecked(True)
            btn.clicked.connect(lambda _, k=key: self._load_curated_collection(k))
            self.pill_group.addButton(btn, idx)
            self.pills[key] = btn
            pills_row.addWidget(btn)

        pills_row.addStretch(1)
        top_layout.addLayout(pills_row)

        # Row 3: Sort & Filter Refinements Bar
        controls_row = QHBoxLayout()
        controls_row.setSpacing(10)

        sort_lbl = QLabel("Sort:")
        sort_lbl.setStyleSheet("font-size: 11px; color: #a1a1aa; font-weight: 600;")
        controls_row.addWidget(sort_lbl)

        # Sort Dropdown
        self.sort_combo = QComboBox()
        self.sort_combo.addItem("Trending / Popular", "-downloads")
        self.sort_combo.addItem("Date Added (Newest)", "-publicdate")
        self.sort_combo.addItem("Weekly Activity", "-week")
        self.sort_combo.addItem("Title (A-Z)", "titleSorter asc")
        self.sort_combo.currentIndexChanged.connect(lambda: self._reload_current())
        controls_row.addWidget(self.sort_combo)

        filter_lbl = QLabel("Filter:")
        filter_lbl.setStyleSheet("font-size: 11px; color: #a1a1aa; font-weight: 600; margin-left: 6px;")
        controls_row.addWidget(filter_lbl)

        # Content Type Filter Dropdown
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("🎯 Direct Media Only", "media_only")
        self.filter_combo.addItem("📁 Collections / Libraries", "collections_only")
        self.filter_combo.addItem("🌟 All Content", "all")
        self.filter_combo.setToolTip("Filter search: Direct playable media items vs parent collection libraries")
        self.filter_combo.currentIndexChanged.connect(lambda: self._reload_current())
        controls_row.addWidget(self.filter_combo)

        controls_row.addStretch(1)
        top_layout.addLayout(controls_row)
        main_layout.addWidget(top_box)

        # --- Section Title & Loading Bar ---
        title_row = QHBoxLayout()
        title_row.setSpacing(10)

        self.feed_title_lbl = QLabel("🔥 Trending Across Internet Archive")
        self.feed_title_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #f4f4f5;")
        title_row.addWidget(self.feed_title_lbl)

        title_row.addStretch(1)

        self.status_label = QLabel("Loading curated items...")
        self.status_label.setStyleSheet("color: #a1a1aa; font-style: italic; font-size: 12px;")
        title_row.addWidget(self.status_label)

        main_layout.addLayout(title_row)

        self.loading_bar = QProgressBar()
        self.loading_bar.setRange(0, 0)
        self.loading_bar.setFixedHeight(3)
        self.loading_bar.setTextVisible(False)
        self.loading_bar.hide()
        main_layout.addWidget(self.loading_bar)

        # --- Results Area ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_layout.setSpacing(10)
        self.results_layout.addStretch(1)

        self.scroll_area.setWidget(self.results_container)
        main_layout.addWidget(self.scroll_area, stretch=1)

        # --- Pagination Bar ---
        self.pagination_box = QHBoxLayout()
        self.pagination_box.setSpacing(10)

        self.prev_btn = QPushButton("◀ Previous")
        self.prev_btn.setEnabled(False)
        self.prev_btn.clicked.connect(self._prev_page)
        self.pagination_box.addWidget(self.prev_btn)

        self.page_label = QLabel("Page 1 of 1")
        self.page_label.setStyleSheet("font-weight: 500; color: #a1a1aa;")
        self.pagination_box.addWidget(self.page_label)

        self.next_btn = QPushButton("Next ▶")
        self.next_btn.setEnabled(False)
        self.next_btn.clicked.connect(self._next_page)
        self.pagination_box.addWidget(self.next_btn)

        self.pagination_box.addStretch(1)
        main_layout.addLayout(self.pagination_box)

    def _load_curated_collection(self, key: str, page: int = 1):
        """Browse a curated Internet Archive category like a website."""
        self.current_collection_key = key
        conf = CURATED_COLLECTIONS.get(key, CURATED_COLLECTIONS["trending"])
        
        self.feed_title_lbl.setText(conf["title"])
        self.search_input.clear()
        
        # Check matching pill
        if key in self.pills:
            self.pills[key].setChecked(True)

        self.current_page = page
        self._execute_query(
            query=conf["query"],
            mediatype=conf["mediatype"],
            sort=conf["sort"] or self.sort_combo.currentData(),
            page=self.current_page
        )

    def explore_collection(self, collection_id: str, title: str):
        """Browse all playable items inside a specific archive collection."""
        self.current_collection_key = f"col_{collection_id}"
        clean_title = title if title and title != collection_id else collection_id
        self.feed_title_lbl.setText(f"📂 Collection: {clean_title}")
        self.search_input.setText(f"collection:{collection_id}")
        
        for p in self.pills.values():
            p.setChecked(False)
            
        self.current_page = 1
        query = f"collection:{collection_id} AND NOT mediatype:collection"
        self._execute_query(
            query=query,
            mediatype=None,
            sort=self.sort_combo.currentData(),
            page=1
        )

    def select_category(self, key: str):
        """Programmatically select a category pill and load its feed."""
        if key in self.pills:
            for k, p in self.pills.items():
                p.setChecked(k == key)
            self._load_curated_collection(key)

    def _on_search_clicked(self):
        text = self.search_input.text().strip()
        if not text:
            self._load_curated_collection("trending")
            return

        # Check if direct identifier / URL was pasted into search
        if "archive.org/details/" in text or "archive.org/download/" in text:
            ident = extract_identifier(text)
            if ident:
                self.inspect_item_requested.emit(ident)
                return

        # Custom search
        self.current_collection_key = "custom"
        self.feed_title_lbl.setText(f"🔍 Search Results for '{text}'")
        
        # Uncheck pills
        for p in self.pills.values():
            p.setChecked(False)

        self.current_page = 1
        
        # Apply filter mode to query
        query = text
        filter_mode = self.filter_combo.currentData()
        if filter_mode == "media_only":
            if "mediatype:" not in query and "collection:" not in query:
                query = f"({query}) AND NOT mediatype:collection"
        elif filter_mode == "collections_only":
            if "mediatype:" not in query:
                query = f"({query}) AND mediatype:collection"

        self._execute_query(
            query=query,
            mediatype=None,
            sort=self.sort_combo.currentData(),
            page=1
        )

    def _reload_current(self):
        if self.current_collection_key.startswith("col_"):
            col_id = self.current_collection_key.replace("col_", "")
            title = self.feed_title_lbl.text().replace("📂 Collection: ", "")
            self.explore_collection(col_id, title)
        elif self.current_collection_key in CURATED_COLLECTIONS:
            self._load_curated_collection(self.current_collection_key, self.current_page)
        elif self.search_input.text().strip():
            self._on_search_clicked()

    def _execute_query(self, query: str, mediatype: Optional[str], sort: str, page: int):
        self.loading_bar.show()
        self.status_label.setText("Fetching from archive.org...")
        self.search_btn.setEnabled(False)

        if self._active_search_worker and self._active_search_worker.isRunning():
            self._active_search_worker.terminate()

        self._active_search_worker = SearchWorker(
            query=query,
            mediatype=mediatype,
            sort=sort,
            page=page,
            rows=20
        )
        self._active_search_worker.signals.finished.connect(self._on_search_finished)
        self._active_search_worker.signals.error.connect(self._on_search_error)
        self._active_search_worker.start()

    def _populate_docs(self, docs: list):
        self._clear_results()
        for doc in docs:
            card = ItemCardWidget(doc)
            card.inspect_requested.connect(self.inspect_item_requested.emit)
            self.results_layout.insertWidget(self.results_layout.count() - 1, card)

    def _on_search_finished(self, data: dict):
        self.loading_bar.hide()
        self.search_btn.setEnabled(True)
        docs = data.get("docs", [])
        total = data.get("total_count", 0)
        rows = data.get("rows", 20)

        self.total_pages = max(1, (total + rows - 1) // rows)
        self.page_label.setText(f"Page {self.current_page} of {self.total_pages:,} ({total:,} items)")
        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(self.current_page < self.total_pages)

        self.status_label.setText(f"{total:,} items in collection • Live")

        if docs:
            self._populate_docs(docs)
        else:
            self._clear_results()
            empty = QLabel("No items found. Try another category or search term.")
            empty.setStyleSheet("padding: 40px; color: #a1a1aa; font-size: 14px;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_layout.insertWidget(0, empty)

    def _on_search_error(self, err_msg: str):
        self.loading_bar.hide()
        self.search_btn.setEnabled(True)
        # If cards are already populated, keep them visible so user always has items to browse!
        if self.results_layout.count() > 1:
            self.status_label.setText("⚠️ Archive.org Solr is busy • Showing curated collection")
        else:
            self._populate_docs(FEATURED_LANDMARKS)
            self.status_label.setText("⚠️ Archive.org Solr timed out • Showing curated highlights")

    def _clear_results(self):
        while self.results_layout.count() > 1:
            child = self.results_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _prev_page(self):
        if self.current_page > 1:
            if self.current_collection_key.startswith("col_"):
                col_id = self.current_collection_key.replace("col_", "")
                self.current_page -= 1
                self._execute_query(f"collection:{col_id} AND NOT mediatype:collection", None, self.sort_combo.currentData(), self.current_page)
            elif self.current_collection_key in CURATED_COLLECTIONS:
                self._load_curated_collection(self.current_collection_key, self.current_page - 1)
            else:
                self.current_page -= 1
                query = self.search_input.text().strip()
                filter_mode = self.filter_combo.currentData()
                if filter_mode == "media_only" and "mediatype:" not in query and "collection:" not in query:
                    query = f"({query}) AND NOT mediatype:collection"
                elif filter_mode == "collections_only" and "mediatype:" not in query:
                    query = f"({query}) AND mediatype:collection"
                self._execute_query(query, None, self.sort_combo.currentData(), self.current_page)

    def _next_page(self):
        if self.current_page < self.total_pages:
            if self.current_collection_key.startswith("col_"):
                col_id = self.current_collection_key.replace("col_", "")
                self.current_page += 1
                self._execute_query(f"collection:{col_id} AND NOT mediatype:collection", None, self.sort_combo.currentData(), self.current_page)
            elif self.current_collection_key in CURATED_COLLECTIONS:
                self._load_curated_collection(self.current_collection_key, self.current_page + 1)
            else:
                self.current_page += 1
                query = self.search_input.text().strip()
                filter_mode = self.filter_combo.currentData()
                if filter_mode == "media_only" and "mediatype:" not in query and "collection:" not in query:
                    query = f"({query}) AND NOT mediatype:collection"
                elif filter_mode == "collections_only" and "mediatype:" not in query:
                    query = f"({query}) AND mediatype:collection"
                self._execute_query(query, None, self.sort_combo.currentData(), self.current_page)

    def _prompt_direct_open(self):
        from PyQt6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(
            self,
            "Direct Item Identifier / URL",
            "Paste Archive.org item identifier or URL (e.g. msdos_Doom_1993):"
        )
        if ok and text.strip():
            ident = extract_identifier(text.strip())
            if ident:
                self.inspect_item_requested.emit(ident)
