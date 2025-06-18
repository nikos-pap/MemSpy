import sys
from PyQt6.QtWidgets import QApplication
from gui import MemoryScannerUI
import logging

# logging.basicConfig(
#     level=logging.INFO,
#     format="[%(name)s] %(levelname)s: %(message)s"
# )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('QtCurve')
    window = MemoryScannerUI()
    window.show()
    sys.exit(app.exec())
