def main():
    import sys
    from PyQt6.QtWidgets import QApplication
    from memspy.gui import MemoryScannerUI
    import logging

    if sys.gettrace() is not None:
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s: [%(name)s] %(levelname)s: %(message)s")
        logging.getLogger("numba.cuda.cudadrv.driver").setLevel(logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO, format="[%(name)s] %(levelname)s: %(message)s")
        logging.getLogger("numba.cuda.cudadrv.driver").setLevel(logging.ERROR)

    app = QApplication(sys.argv)
    window = MemoryScannerUI()
    window.show()
    sys.exit(app.exec())
