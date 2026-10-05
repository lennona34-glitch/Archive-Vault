import sys
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

# Crucial: QtWebEngine requires AA_ShareOpenGLContexts set before QApplication instantiation
if hasattr(Qt.ApplicationAttribute, "AA_ShareOpenGLContexts"):
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)
try:
    import PyQt6.QtWebEngineWidgets
except ImportError:
    pass

from archivevault.ui.main_window import MainWindow

def main():
    # Enable High DPI scaling
    if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("ArchiveVault")
    app.setOrganizationName("InternetArchiveTools")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
