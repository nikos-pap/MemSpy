from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QAction, QFont
from PyQt6.QtWidgets import QMenuBar, QMessageBox


class MenuBar(QMenuBar):
    openSettingsSignal = pyqtSignal()

    def __init__(self, parent=None):
        super(MenuBar, self).__init__(parent)
        self.__create_menu_bar()

    def __create_menu_bar(self) -> None:
        main_font = QFont()
        secondary_font = QFont()
        main_font.setPointSize(16)
        secondary_font.setPointSize(14)

        self.setFont(main_font)
        self.file_menu = self.addMenu("File")
        self.file_menu.setFont(secondary_font)

        self.open_action = QAction("Open", self)
        self.open_action.triggered.connect(lambda: self.__show_message("Open clicked"))
        self.file_menu.addAction(self.open_action)

        tools = self.addMenu('Tools')
        tools.setFont(secondary_font)
        settings = QAction("Settings", self)
        settings.triggered.connect(self.openSettingsSignal)
        tools.addAction(settings)

        self.__exit_action = QAction("Exit", self)
        self.__exit_action.triggered.connect(self.close)
        self.file_menu.addAction(self.__exit_action)

        self.__view_menu = self.addMenu("View")
        self.__view_menu.setFont(secondary_font)

        self.search_table_action = QAction('Search Address Table', self)
        self.search_table_action.setCheckable(True)
        self.search_table_action.setChecked(True)
        self.__view_menu.addAction(self.search_table_action)

        self.saved_table_action = QAction('Saved Address Table', self)
        self.saved_table_action.setCheckable(True)
        self.saved_table_action.setChecked(True)
        self.__view_menu.addAction(self.saved_table_action)

        self.search_pointer_action = QAction('Pointer Scan Table', self)
        self.search_pointer_action.setCheckable(True)
        self.search_pointer_action.setChecked(True)
        self.__view_menu.addAction(self.search_pointer_action)

        self.__help_menu = self.addMenu("Help")
        self.__help_menu.setFont(secondary_font)
        __about_action = QAction("About", self)
        __about_action.triggered.connect(
            lambda: self.__show_message("This is a PyQt6 app")
        )
        self.__help_menu.addAction(__about_action)

    def __show_message(self, message):
        QMessageBox.information(self, "Info", message)
