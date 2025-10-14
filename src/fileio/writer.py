import os
import tempfile
from os import PathLike
from typing import Optional, BinaryIO
from numpy.typing import NDArray, DTypeLike


class FileWriter:
    """
    A simple file writer to write the scan results to disk.

    Attributes:
        dtype: Optional NumPy dtype-like object.
        filepath: Optional file path as a string.
        __file: Optional binary file object.
    """
    def __init__(self, out_dir: str | PathLike = tempfile.gettempdir()) -> None:
        self.dtype: Optional[DTypeLike] = None
        self.filepath: Optional[str] = None
        self.__file: Optional[BinaryIO] = None
        self.__out_dir: Optional[str] = out_dir

    def set_file(self, file_path: str, dtype: DTypeLike) -> None:
        """
        Creates a chosen file so that it can be filled with data.
        Args:
            file_path: The file path to write.
            dtype: the numpy dtype to use.
        """
        dirpath, filename = os.path.split(file_path)
        if dirpath and not os.path.exists(dirpath):
            raise FileNotFoundError(f"Path {dirpath} does not exist")

        self.__file = open(file_path, "wb")
        self.filepath = self.__file.name
        self.dtype = dtype

    def temp_file(self, dtype: DTypeLike) -> None:
        """
        Creates a temporary file so that it can be filled with data.

        Args:
            dtype: [DTypeLike] the dtype of the written data.
        """
        self.__file = tempfile.NamedTemporaryFile(delete=False, dir=self.__out_dir, mode='wb+')
        self.filepath = self.__file.name
        self.dtype = dtype

    def write(self, data: NDArray) -> None:
        """
        Writes data to file.

        Args:
            data: [NDArray] the nparray data to write to the file.

        Returns:
            None:
        """
        if not self.__file:
            raise RuntimeError("File not set or closed.")
        self.__file.write(data.tobytes(order="C"))
        self.__file.flush()

    def close(self) -> None:
        """Closes the open file handle if any."""
        if self.__file and not self.__file.closed:
            self.__file.close()
            self.__file = None

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.__file and not self.__file.closed:
            self.__file.close()
