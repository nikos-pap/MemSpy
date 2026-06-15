import io
import os
import tempfile
from typing import TypeAlias

import pickle
from numpy.typing import NDArray, DTypeLike

from memspy.utils.pointer_scan import PointerScanInfo
from memspy.utils.types import ScanType

OutputFile: TypeAlias = io.BufferedWriter | tempfile._TemporaryFileWrapper


class FileWriter:
    """
    A simple file writer to write the scan results to disk.

    Attributes:
        dtype: Optional NumPy dtype-like object.
        __filepath: Optional file path as a string.
        __file: Optional binary file object.
    """

    def __init__(self, out_dir: str | os.PathLike = tempfile.gettempdir()) -> None:
        self.dtype: DTypeLike | None = None
        self.__filepath: str | None = None
        self.__file: OutputFile | None = None
        self.__out_dir: str | os.PathLike = out_dir

    # noinspection PyTypeHints
    def open_file(self, file_path: str, dtype: DTypeLike) -> None:
        dirpath, filename = os.path.split(file_path)
        if dirpath and not os.path.exists(dirpath):
            raise FileNotFoundError(f"Path {dirpath} does not exist")

        file = open(file_path, "wb")
        self.__set_file(file, dtype)

    # noinspection PyTypeHints
    def temp_file(self, dtype: DTypeLike) -> None:
        file = tempfile.NamedTemporaryFile(delete=False, dir=self.__out_dir, mode="wb+")
        self.__set_file(file, dtype)

    # noinspection PyTypeHints
    def __set_file(self, file: OutputFile, dtype: DTypeLike) -> None:
        self.__file = file
        self.__filepath = file.name
        self.dtype = dtype

    def write(
        self,
        data: NDArray,
        scan_type: ScanType | None,
        scan_info: PointerScanInfo | None = None,
    ) -> None:
        """
        Writes data to file.

        Args:
            data: [NDArray] the nparray data to write to the file.
            scan_type: Optional[ScanType] the scan type.
            scan_info: Optional[PointerScanInfo] the scan info.
        Returns:
            None:
        """
        if not self.__file:
            raise RuntimeError("File not set or closed.")
        if scan_type == ScanType.POINTER_SCAN:
            pickle.dump(scan_info, self.__file)
            for d in data:
                pickle.dump(d, self.__file)
        else:
            result = data.tobytes(order="C")
            self.__file.write(result)
        self.__file.flush()

    @property
    def filepath(self) -> str | None:
        return self.__filepath

    def close(self) -> None:
        """Closes the open file handle if any."""
        if self.__file and not self.__file.closed:
            self.__file.close()
        self.__file = None
        self.__filepath = None

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.__file and not self.__file.closed:
            self.__file.close()
