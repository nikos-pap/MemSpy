import re
from logging import getLogger

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QFont
from numba.cuda import CudaSupportError
from numba.cuda.cudadrv.driver import CudaAPIError
from numba.cuda.cudadrv.error import CudaDriverError
import pywintypes
import wmi
from enum import Enum, auto


def _list_cpus() -> list[str]:
    """Return a list of CPU names on Windows via WMI."""
    cpus = []
    try:
        c = wmi.WMI()
        for cpu in c.Win32_Processor():
            cpus.append(cpu.Name.strip())
    except pywintypes.com_error as e:
        print("⚠️ WMI COM error:", e)
    except wmi.x_wmi as e:
        print("⚠️ WMI query error:", e)
    return cpus


def _list_gpus() -> list[str]:
    """Return a list of CUDA-capable GPU names via Numba."""
    gpu_list = []
    try:
        from numba import cuda
        if cuda.is_available():
            for dev in cuda.gpus:
                # .name is a bytestring, decode to UTF-8
                gpu_list.append(dev.name.decode('utf-8'))
    except (CudaSupportError, CudaDriverError, CudaAPIError) as e:
        print("⚠️ CUDA driver error:", e)
    except UnicodeDecodeError as e:
        print("⚠️ GPU name decoding error:", e)
    return gpu_list


def list_devices() -> list[dict[str, str | int]]:
    logger = getLogger('Device Manager')
    devices = []
    # CPUs
    cpus = _list_cpus()
    for idx, name in enumerate(cpus, start=1):
        devices.append({
            'type': 'CPU',
            'index': idx,
            'name': name
        })

    # GPUs
    gpus = _list_gpus()
    for idx, name in enumerate(gpus, start=1):
        devices.append({
            'type': 'GPU',
            'index': idx,
            'name': name
        })

    # Print summary
    if not devices:
        logger.debug("No devices found.")
    else:
        text = 'Detected devices:'

        for dev in devices:
            text += f"\n  [{dev['type']} {dev['index']}] {dev['name']}"

        logger.info(text)
    return devices


class SavedTreeTypes(Enum):
    POINTER = auto()
    GROUP = auto()
    ADDRESS = auto()


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


def is_uint64_hex(s: str, allow_prefix: bool = True) -> bool:
    # 1) Optionally strip "0x"/"0X"
    if allow_prefix:
        if s.startswith(('0x','0X')):
            s = s[2:]
    # 2) Check that what's left is 1 or more hex digits
    if not re.fullmatch(r'[0-9A-Fa-f]+', s):
        return False
    # 3) Parse and make sure it fits in 0 .. 2**64-1
    try:
        val = int(s, 16)
    except ValueError:
        return False
    return 0 <= val <= 0xFFFFFFFFFFFFFFFF
