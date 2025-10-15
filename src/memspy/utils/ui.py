from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QFont


def emoji_icon(emoji: str, size: int = 32) -> QIcon:
    """
    Create a QIcon by painting the given emoji onto a transparent pixmap.
    """
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    # pick a font large enough to fill the pixmap
    font = QFont()
    font.setPixelSize(int(size * 0.8))
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, emoji)
    painter.end()

    return QIcon(pixmap)
