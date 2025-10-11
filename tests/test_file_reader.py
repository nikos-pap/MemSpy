import os
import numpy as np
import pytest
from file_handle_engine import FileStreamReader, FileWriter


@pytest.fixture
def temp_binary_file(tmp_path):
    """Creates a temporary binary file with known data using FileWriter."""
    data = np.arange(10, dtype=np.int32)
    file_path = tmp_path / "test_data.bin"

    writer = FileWriter()
    writer.set_file(str(file_path), dtype=np.int32)
    writer.write(data)
    writer.close()

    return file_path, data


def test_set_file_and_size(temp_binary_file):
    file_path, data = temp_binary_file
    reader = FileStreamReader()
    reader.set_file(str(file_path), element_size=4)

    assert reader.size == os.path.getsize(file_path)
    assert reader.size == len(data) * 4

    reader.close()


def test_read_elements(temp_binary_file):
    file_path, data = temp_binary_file
    reader = FileStreamReader()
    reader.set_file(str(file_path), element_size=4)

    first_two = reader.read_elements(2)
    result = np.frombuffer(first_two, dtype=np.int32)
    np.testing.assert_array_equal(result, data[:2])

    reader.close()


def test_seek_and_read(temp_binary_file):
    file_path, data = temp_binary_file
    reader = FileStreamReader()
    reader.set_file(str(file_path), element_size=4)

    # Move to element 5 (offset = 5 * 4 bytes)
    reader.seek(5 * 4)
    read_data = np.frombuffer(reader.read(4), dtype=np.int32)
    assert read_data[0] == data[5]

    reader.close()


def test_iteration(temp_binary_file):
    file_path, data = temp_binary_file
    reader = FileStreamReader()
    reader.set_file(str(file_path), element_size=4)

    result = []
    for element_bytes in reader:
        result.append(np.frombuffer(element_bytes, dtype=np.int32)[0])

    np.testing.assert_array_equal(result, data)

    reader.close()


def test_invalid_element_size(tmp_path):
    # Create file of 10 bytes
    file_path = tmp_path / "bad_size.bin"
    file_path.write_bytes(b"\x00" * 10)

    reader = FileStreamReader()
    with pytest.raises(ValueError):
        reader.set_file(str(file_path), element_size=3)


def test_reset_and_close(temp_binary_file):
    file_path, _ = temp_binary_file
    reader = FileStreamReader()
    reader.set_file(str(file_path), element_size=4)
    reader.close()

    # After close, internal attributes should be reset
    assert getattr(reader, '_FileStreamReader__filepath') is None
    assert getattr(reader, '_FileStreamReader__data_size') is None
