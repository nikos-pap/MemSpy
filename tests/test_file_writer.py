import os
import numpy as np
import pytest
from memspy.fileio import FileWriter


def test_temp_file_creation(tmp_path):
    fw = FileWriter(out_dir=tmp_path)
    fw.temp_file(np.uint8)

    # Check file actually exists
    assert fw.filepath is not None
    assert os.path.exists(fw.filepath)
    assert fw.dtype == np.uint8

    fw.close()
    assert not getattr(fw, '_FileWriter__file')  # after close, internal handle is None


def test_write_and_close(tmp_path):
    fw = FileWriter(out_dir=tmp_path)
    fw.temp_file(np.uint16)
    data = np.array([1, 2, 3], dtype=np.uint16)
    fw.write(data)
    fw.close()

    # Read back from file to verify bytes
    with open(fw.filepath, "rb") as f:
        content = f.read()
    expected = data.tobytes(order="C")
    assert content == expected


def test_set_file_nonexistent_dir_raises(tmp_path):
    # Make a fake subdir that doesn't exist
    fake_dir = tmp_path / "nonexistent"
    file_path = os.path.join(fake_dir, "data.bin")

    fw = FileWriter()
    with pytest.raises(FileNotFoundError):
        fw.set_file(file_path, np.uint8)
