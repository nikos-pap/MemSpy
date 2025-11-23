import os
import pickle

import pytest

from tests.helpers import ensure_numpy_stub, ensure_pillow_stub

ensure_numpy_stub()
ensure_pillow_stub()

from memspy.fileio import FileWriter
from memspy.utils.pointer_scan import PointerScanInfo
from memspy.utils.types.scan_types import ScanType


class FakeArray:
    def __init__(self, data: bytes):
        self._data = data

    def tobytes(self, order: str = "C") -> bytes:  # pragma: no cover - thin wrapper
        return self._data


def test_set_file_writes_raw_bytes(tmp_path):
    target = tmp_path / "raw.bin"
    writer = FileWriter()

    writer.set_file(str(target), dtype="<i4")
    writer.write(FakeArray(b"\x01\x02\x03\x04"), scan_type=None)
    writer.close()

    with open(target, "rb") as fp:
        assert fp.read() == b"\x01\x02\x03\x04"


def test_temp_file_pointer_scan_serializes_results(tmp_path):
    writer = FileWriter(out_dir=tmp_path)

    writer.temp_file(dtype="<i4")
    scan_info = PointerScanInfo(entries=2, max_depth=3)
    pointer_data = [b"first", b"second"]

    writer.write(pointer_data, scan_type=ScanType.POINTER_SCAN, scan_info=scan_info)
    writer.close()

    assert writer.filepath and os.path.exists(writer.filepath)

    with open(writer.filepath, "rb") as fp:
        restored_info = pickle.load(fp)
        restored_first = pickle.load(fp)
        restored_second = pickle.load(fp)

    assert restored_info == scan_info
    assert restored_first == b"first"
    assert restored_second == b"second"


def test_set_file_validates_directory(tmp_path):
    writer = FileWriter()
    missing_dir = tmp_path / "missing" / "output.bin"

    with pytest.raises(FileNotFoundError):
        writer.set_file(str(missing_dir), dtype="<i4")