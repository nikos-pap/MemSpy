import math
import sys
import types
import typing as t


def ensure_numpy_stub() -> None:
    """Install a minimal numpy stub if the real dependency is unavailable."""
    if "numpy" in sys.modules:
        return

    numpy_module = types.ModuleType("numpy")
    numpy_typing_module = types.ModuleType("numpy.typing")

    class FakeNDArray:
        def __init__(self, data: bytes | bytearray | memoryview):
            self._buffer = bytes(data)

        def tobytes(self, order: str = "C") -> bytes:  # pragma: no cover - passthrough
            return self._buffer

        def __iter__(self):  # pragma: no cover - supports pointer scan writes
            return iter(self._buffer)

    class FakeScalar:
        def __init__(self, value: t.Any):
            self._value = value

        def astype(self, dtype: t.Any):
            self._value = _coerce(self._value, dtype)
            return self

        def item(self):
            return self._value

    def _coerce(value: t.Any, dtype: t.Any):
        if dtype in (float, "float32", "float64"):
            return float(value)
        if dtype in (int, "int8", "int16", "int32", "int64", "uint8", "uint16", "uint32", "uint64"):
            return int(value)
        return value

    numpy_module.int8 = "int8"
    numpy_module.int16 = "int16"
    numpy_module.int32 = "int32"
    numpy_module.int64 = "int64"
    numpy_module.uint8 = "uint8"
    numpy_module.uint16 = "uint16"
    numpy_module.uint32 = "uint32"
    numpy_module.uint64 = "uint64"
    numpy_module.float32 = "float32"
    numpy_module.float64 = "float64"
    numpy_module.ndarray = FakeNDArray
    numpy_module.floating = float

    numpy_module.dtype = lambda spec: spec
    numpy_module.array = lambda value: FakeScalar(value)
    numpy_module.issubdtype = lambda dtype, target: target is float and dtype in ("float32", "float64", float)
    numpy_module.isfinite = lambda value: math.isfinite(value)

    numpy_typing_module.NDArray = t.Any
    numpy_typing_module.DTypeLike = t.Any

    sys.modules["numpy"] = numpy_module
    sys.modules["numpy.typing"] = numpy_typing_module


def ensure_pillow_stub() -> None:
    """Install a minimal Pillow stub that only exposes :class:`Image`."""
    if "PIL.Image" in sys.modules:
        return

    pil_module = types.ModuleType("PIL")
    image_module = types.ModuleType("PIL.Image")

    class Image:  # pragma: no cover - placeholder for type imports
        pass

    image_module.Image = Image
    pil_module.Image = Image

    sys.modules["PIL"] = pil_module
    sys.modules["PIL.Image"] = image_module