from PyQt6.QtCore import Qt, QRect
from PyQt6.QtWidgets import (
    QWidget, QComboBox, QLineEdit,
    QHBoxLayout
)
from PyQt6.QtGui import QFont, QPainter
from utils import Type, TYPE_RANGES


class ArrowComboBox(QComboBox):
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setPen(Qt.GlobalColor.white)
        painter.setFont(QFont("Segoe UI", 12))
        arrow = "▼"
        rect = self.rect()
        painter.drawText(rect.adjusted(-10, 0, -5, 0), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, arrow)
        painter.end()


class EmojiLineEdit(QLineEdit):
    def __init__(self):
        super().__init__()
        self.emoji = ""
        self.setTextMargins(0, 0, 28, 0)  # Reserve space on the right for the emoji

    def set_emoji(self, emoji: str):
        self.emoji = emoji
        self.update()  # Trigger repaint

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.emoji:
            painter = QPainter(self)
            rect = self.rect()
            size = 20
            margin = 8
            x = rect.right() - size - margin
            y = (rect.height() - size - 7) // 2
            painter.drawText(QRect(x, y, size+5, size+5), Qt.AlignmentFlag.AlignCenter, self.emoji)


class ValueSearchBox(QLineEdit):
    def __init__(self, message_callable):
        super().__init__()
        self.message_command = message_callable
        font = QFont()
        font.setPointSize(16)
        self.setFont(font)
        self.setPlaceholderText("Search...")
        self.textChanged.connect(self.validate_input)


class SearchBox(QWidget):
    def __init__(self, message_callable):
        super().__init__()
        self.valid_input = False
        self.message_command = message_callable
        # self.setFixedWidth(500)
        font = QFont()
        font.setPointSize(16)
        # Dropdown
        self.combo = QComboBox()
        self.combo.setFixedWidth(100)
        self.combo.setFont(font)

        # Search field
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search...")
        self.search_input.setFont(font)
        self.search_input.textChanged.connect(self.validate_input)

        self.condition_combo = QComboBox()
        self.condition_combo.setFixedWidth(100)
        self.condition_combo.setFont(font)
        # Layout: ComboBox + Search
        search_layout = QHBoxLayout()
        search_layout.setSpacing(10)
        search_layout.addWidget(self.combo)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.condition_combo)
        # search_layout.setSpacing(0)
        self.setLayout(search_layout)

        # Optional: minimal style to simulate clean look
        # self.setStyleSheet("""
        #     QComboBox::drop-down {
        #         width: 0;
        #     }
        #     QComboBox {
        #         border-right: solid;
        #         padding-left: 5px;
        #         border-radius: 6px;
        #         border-top-right-radius: 0px;
        #         border-bottom-right-radius: 0px;
        #     }
        #     QLineEdit {
        #         border-right: 1px solid #888;
        #         border-left: 1px solid #888;
        #         border-top-left-radius: 0px;
        #         border-bottom-left-radius: 0px;
        #     }
        # """)
        #
        # self.condition_combo.setStyleSheet("""
        #         QComboBox {
        #         border-radius: 6px;
        #         border-top-left-radius: 0px;
        #         border-bottom-left-radius: 0px;
        #     }
        #     """
        # )

    def addItems(self, items) -> None:
        for item in items:
            self.combo.addItem(*item)
        # self.combo.addItems(items)

    def setDefault(self, index: int):
        self.combo.setCurrentIndex(index)

    def validate_input(self, text):
        t = self.combo.currentData()

        self.message_command('')

        if t == Type.String:
            # self.status_label.setText("✅ Valid string.")
            self.search_input.setStyleSheet(self.build_stylesheet('limegreen'))
            self.valid_input = True
            return

        if not text.strip():
            self.valid_input = False
            # self.search_input.set_emoji("⚠️")
            self.message_command('⚠️ Empty input.')
            self.search_input.setStyleSheet(self.build_stylesheet('white'))
            # self.status_label.setText("⚠️ Empty input.")
            return

        try:
            if "Float" in t.name or "Double" in t.name:
                value = float(text)
            else:
                if "." in text:
                    raise ValueError("Integer type cannot contain a decimal point.")
                value = int(text)

            min_val, max_val = TYPE_RANGES[t]
            if min_val <= value <= max_val:
                # self.search_input.set_emoji("✅")
                self.search_input.setStyleSheet(self.build_stylesheet('white'))
                # self.status_label.setText(f"✅ Valid {t.value} value.")
                self.valid_input = True
            else:
                self.valid_input = False
                # self.search_input.set_emoji("❌")
                self.search_input.setStyleSheet(self.build_stylesheet('#B22222'))
                self.message_command(f'❌ Out of range for {t.value} ({min_val} to {max_val}).')
                # self.status_label.setText(f"❌ Out of range for {t.value} ({min_val} to {max_val}).")
        except ValueError as e:
            # self.search_input.set_emoji("❌")
            # self.search_input.setStyleSheet("color: red;")
            self.search_input.setStyleSheet(self.build_stylesheet('#B22222'))
            self.message_command(f'❌ Invalid input: {e}')
            # self.status_label.setText(f"❌ Invalid input: {e}")
            self.valid_input = False
        print(self.valid_input)

    def build_stylesheet(self, color: str) -> str:
        return f"""
            QLineEdit {{
                color: {color};
            }}
        """
