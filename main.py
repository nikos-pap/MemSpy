import sys
from PyQt6.QtWidgets import QApplication
from gui import MemoryScannerUI

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('QtCurve')
    window = MemoryScannerUI()
    window.show()
    sys.exit(app.exec())
