"""
Modern dark styling inspired by Windows 11 Fluent Design and Internet Archive aesthetics.
"""

DARK_THEME = """
/* Global Application Styles */
QWidget {
    background-color: #121214;
    color: #e4e4e7;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}

/* Sidebar and Navigation */
#sidebar {
    background-color: #18181b;
    border-right: 1px solid #27272a;
    min-width: 210px;
    max-width: 230px;
}

#navBtn {
    background-color: transparent;
    color: #a1a1aa;
    text-align: left;
    padding: 10px 16px;
    font-size: 13px;
    font-weight: 500;
    border: none;
    border-radius: 8px;
    margin: 2px 8px;
}

#navBtn:hover {
    background-color: #27272a;
    color: #f4f4f5;
}

#navBtn:checked {
    background-color: #2563eb;
    color: #ffffff;
    font-weight: 600;
}

/* Zen Mode Top Right Button */
#zenBtn {
    background-color: #27272a;
    color: #38bdf8;
    border: 1px solid #38bdf8;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 600;
    font-size: 12px;
}

#zenBtn:hover {
    background-color: #0284c7;
    color: #ffffff;
    border-color: #0284c7;
}

/* Open Video Top Right Button */
#openVideoBtn {
    background-color: #1e1b4b;
    color: #c7d2fe;
    border: 1px solid #4f46e5;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 600;
    font-size: 12px;
}

#openVideoBtn:hover {
    background-color: #4338ca;
    color: #ffffff;
    border-color: #6366f1;
}

/* Exit Zen Mode Button */
#exitZenBtn {
    background-color: #3f1515;
    color: #fca5a5;
    border: 1px solid #7f1d1d;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 600;
    font-size: 12px;
}

#exitZenBtn:hover {
    background-color: #991b1b;
    color: #ffffff;
    border-color: #b91c1c;
}

/* Header & Panels */
#headerWidget {
    background-color: #18181b;
    border-bottom: 1px solid #27272a;
    padding: 12px 20px;
}

/* Clickable Item Card in Opening Menu */
#card {
    background-color: #18181b;
    border: 1px solid #27272a;
    border-radius: 10px;
    padding: 14px;
}

#card:hover {
    background-color: #202025;
    border-color: #3b82f6;
}

/* Article Page Hero & Container */
#articleCard {
    background-color: #18181b;
    border: 1px solid #27272a;
    border-radius: 12px;
    padding: 20px;
}

#curatedCard {
    background-color: #1c1c20;
    border: 1px solid #2e2e34;
    border-radius: 8px;
    padding: 10px 14px;
}

#curatedCard:hover {
    border-color: #3b82f6;
    background-color: #232329;
}

/* Play / Preview Hero Button */
#playBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #059669);
    color: #ffffff;
    border: 1px solid #047857;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: 700;
    font-size: 13px;
    min-height: 24px;
}

#playBtn:hover {
    background: #10b981;
}

/* Back to Browse Button */
#backBtn {
    background-color: #27272a;
    color: #38bdf8;
    border: 1px solid #38bdf8;
    border-radius: 6px;
    padding: 6px 16px;
    font-weight: 600;
    font-size: 13px;
}

#backBtn:hover {
    background-color: #0284c7;
    color: #ffffff;
    border-color: #0284c7;
}

/* Text Inputs & Search Bars */
QLineEdit, QComboBox, QSpinBox {
    background-color: #1f1f23;
    border: 1px solid #2e2e33;
    border-radius: 6px;
    padding: 7px 12px;
    color: #fafafa;
    font-size: 13px;
    min-height: 20px;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #3b82f6;
    background-color: #232328;
}

/* Category Pills for Website-Style Browsing */
#categoryPill {
    background-color: #1f1f23;
    color: #a1a1aa;
    border: 1px solid #2e2e33;
    border-radius: 14px;
    padding: 5px 11px;
    font-weight: 600;
    font-size: 12px;
}

#categoryPill:hover {
    background-color: #27272a;
    color: #f4f4f5;
    border-color: #3f3f46;
}

#categoryPill:checked {
    background-color: #2563eb;
    color: #ffffff;
    border-color: #3b82f6;
    font-weight: 600;
}

/* Buttons */
QPushButton {
    background-color: #27272a;
    color: #f4f4f5;
    border: 1px solid #3f3f46;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
    font-size: 13px;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #323238;
    border-color: #52525b;
}

QPushButton:pressed {
    background-color: #1c1c1f;
}

/* Primary Action Buttons */
QPushButton#primaryBtn {
    background-color: #2563eb;
    color: #ffffff;
    border: 1px solid #1d4ed8;
    font-weight: 600;
}

QPushButton#primaryBtn:hover {
    background-color: #3b82f6;
    border-color: #2563eb;
}

QPushButton#primaryBtn:pressed {
    background-color: #1d4ed8;
}

/* Danger / Cancel Buttons */
QPushButton#dangerBtn {
    background-color: #7f1d1d;
    color: #fecaca;
    border: 1px solid #991b1b;
}

QPushButton#dangerBtn:hover {
    background-color: #991b1b;
}

/* Success Buttons */
QPushButton#successBtn {
    background-color: #065f46;
    color: #a7f3d0;
    border: 1px solid #047857;
}

QPushButton#successBtn:hover {
    background-color: #047857;
}

/* Table Specific Buttons */
QPushButton#tableActionBtn {
    background-color: #2563eb;
    color: #ffffff;
    border: 1px solid #1d4ed8;
    border-radius: 5px;
    padding: 2px 10px;
    font-weight: 600;
    font-size: 12px;
    min-height: 28px;
    max-height: 28px;
}

QPushButton#tableActionBtn:hover {
    background-color: #3b82f6;
}

QPushButton#tablePauseBtn {
    background-color: #27272a;
    color: #f4f4f5;
    border: 1px solid #3f3f46;
    border-radius: 5px;
    padding: 2px 10px;
    font-weight: 500;
    font-size: 12px;
    min-height: 28px;
    max-height: 28px;
}

QPushButton#tablePauseBtn:hover {
    background-color: #323238;
}

QPushButton#tableCancelBtn {
    background-color: #451a1a;
    color: #fca5a5;
    border: 1px solid #7f1d1d;
    border-radius: 5px;
    padding: 0px;
    font-weight: 700;
    font-size: 13px;
    min-height: 28px;
    max-height: 28px;
    min-width: 28px;
    max-width: 28px;
}

QPushButton#tableCancelBtn:hover {
    background-color: #7f1d1d;
    color: #ffffff;
}

/* Tables & Tree Views */
QTableWidget {
    background-color: #18181b;
    border: 1px solid #27272a;
    border-radius: 8px;
    gridline-color: #222226;
    alternate-background-color: #141416;
}

QTableWidget::item {
    padding: 4px 8px;
    border-bottom: 1px solid #202024;
}

QTableWidget::item:selected {
    background-color: #1e3a5f;
    color: #ffffff;
}

QHeaderView::section {
    background-color: #1f1f23;
    color: #a1a1aa;
    font-weight: 600;
    font-size: 12px;
    padding: 8px 10px;
    border: none;
    border-bottom: 2px solid #27272a;
    border-right: 1px solid #27272a;
}

/* Progress Bars */
QProgressBar {
    background-color: #27272a;
    border: 1px solid #3f3f46;
    border-radius: 5px;
    text-align: center;
    color: #ffffff;
    font-size: 11px;
    font-weight: 600;
    min-height: 20px;
    max-height: 20px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #2563eb, stop:1 #06b6d4);
    border-radius: 4px;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    border-left: 1px solid #27272a;
    background: #141416;
    width: 14px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #52525b;
    min-height: 36px;
    border-radius: 6px;
    margin: 2px;
}

QScrollBar::handle:vertical:hover {
    background: #71717a;
}

QScrollBar::handle:vertical:pressed {
    background: #38bdf8;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

QScrollBar:horizontal {
    border: none;
    border-top: 1px solid #27272a;
    background: #141416;
    height: 12px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background: #52525b;
    min-width: 36px;
    border-radius: 5px;
    margin: 2px;
}

QScrollBar::handle:horizontal:hover {
    background: #71717a;
}

QScrollBar::handle:horizontal:pressed {
    background: #38bdf8;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
}

/* Status Bar */
QStatusBar {
    background-color: #121214;
    border-top: 1px solid #27272a;
    color: #a1a1aa;
    font-size: 12px;
    padding: 4px 10px;
}

/* Checkboxes */
QCheckBox {
    color: #e4e4e7;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #3f3f46;
    border-radius: 4px;
    background-color: #1f1f23;
}

QCheckBox::indicator:checked {
    background-color: #2563eb;
    border-color: #3b82f6;
}

/* Tooltips */
QToolTip {
    background-color: #27272a;
    color: #f4f4f5;
    border: 1px solid #3f3f46;
    padding: 4px 8px;
    border-radius: 4px;
}
"""

def get_mediatype_badge_color(mediatype: str) -> str:
    """Return an aesthetic hex color badge according to IA media type."""
    mapping = {
        "software": "#10b981", # Emerald
        "movies": "#ef4444",   # Red
        "audio": "#f59e0b",    # Amber
        "texts": "#8b5cf6",    # Purple
        "image": "#ec4899",    # Pink
        "data": "#06b6d4",     # Cyan
        "collection": "#6366f1"# Indigo
    }
    return mapping.get(mediatype.lower(), "#64748b")
