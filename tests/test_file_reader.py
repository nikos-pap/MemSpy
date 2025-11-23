import os
import struct

import pytest

from tests.helpers import ensure_numpy_stub, ensure_pillow_stub

ensure_numpy_stub()
ensure_pillow_stub()

from memspy.fileio import FileStreamReader


@pytest.fixture
def binary_file(tmp_path):
    values = list(range(10))
    file_path = tmp_path / "data.bin"
    with open(file_path, "wb") as fp:
        for value in values:
            fp.write(struct.pack("<i", value))
    return file_path, values


def test_set_file_tracks_size(binary_file):
    file_path, values = binary_file
    reader = FileStreamReader()

    reader.set_file(str(file_path), element_size=4)

    assert reader.size == os.path.getsize(file_path)
    assert reader.size == len(values) * 4

    reader.close()


def test_read_elements_respects_item_count(binary_file):
    file_path, values = binary_file
    reader = FileStreamReader()
    reader.set_file(str(file_path), element_size=4)

    payload = reader.read_elements(3)
    numbers = [struct.unpack("<i", payload[i : i + 4])[0] for i in range(0, len(payload), 4)]

    assert numbers == values[:3]

    reader.close()


def test_seek_moves_cursor(binary_file):
    file_path, values = binary_file
    reader = FileStreamReader()
    reader.set_file(str(file_path), element_size=4)

    reader.seek(6 * 4)
    data = reader.read(4)

    assert struct.unpack("<i", data)[0] == values[6]

    reader.close()


def test_iteration_yields_chunks(binary_file):
    file_path, values = binary_file
    reader = FileStreamReader()
    reader.set_file(str(file_path), element_size=4)

    collected = [struct.unpack("<i", chunk)[0] for chunk in reader]

    assert collected == values

    reader.close()


def test_invalid_element_size_raises(tmp_path):
    file_path = tmp_path / "invalid.bin"
    file_path.write_bytes(b"\x00" * 10)

    reader = FileStreamReader()
    with pytest.raises(ValueError):
        reader.set_file(str(file_path), element_size=3)


def test_reset_on_close(binary_file):
    file_path, _ = binary_file
    reader = FileStreamReader()
    reader.set_file(str(file_path), element_size=4)
    reader.close()

    assert getattr(reader, "_FileStreamReader__filepath") is None
    assert getattr(reader, "_FileStreamReader__data_size") is None