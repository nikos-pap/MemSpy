import pytest

pytest.importorskip("PyQt6", reason="GUI tests require PyQt6, which is not available in the test environment.")