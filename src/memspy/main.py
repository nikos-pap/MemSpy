def main():
    import sys
    from PyQt6.QtWidgets import QApplication
    import logging

    if sys.gettrace() is not None:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s: [%(name)s] %(levelname)s: %(message)s",
        )
    else:
        logging.basicConfig(
            level=logging.INFO, format="[%(name)s] %(levelname)s: %(message)s"
        )
    logging.getLogger("numba").setLevel(logging.ERROR)

    app = QApplication(sys.argv)

    from memspy.gui import MemoryScannerUI

    window = MemoryScannerUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
