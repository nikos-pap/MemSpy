import os
from numpy.typing import DTypeLike
from typing import Optional, BinaryIO
from logging import Logger, getLogger
from collections.abc import Iterable


class FileStreamReader:

    __logger: Logger = getLogger(__qualname__)

    def __init__(self):
        self.__size: int = 0
        self.__data_size: Optional[int] = None
        self.__filepath: Optional[str] = None
        self.__stream: Optional[BinaryIO] = None

    def set_file(self, filepath: str, element_size: int) -> None:
        self.__filepath = filepath
        self.__size = os.path.getsize(filepath)
        if self.__size % element_size != 0:
            raise ValueError(f"File size is not a multiple of {element_size}")
        self.__stream = open(filepath, "rb")
        self.__data_size = element_size
        self.__logger.debug(f'File {filepath} loaded')

    def read(self, size: int) -> bytes:
        return self.__stream.read(size)

    def read_elements(self, items: int) -> bytes:
        return self.__stream.read(min(items * self.__data_size, self.size))

    def seek(self, offset: int) -> None:
        self.__stream.seek(offset)

    @property
    def size(self) -> int:
        return self.__size

    def reset(self):
        self.__data_size: Optional[DTypeLike] = None
        self.__filepath: Optional[str] = None

    def close(self) -> None:
        self.reset()
        if self.__stream:
            self.__stream.close()

    def __iter__(self) -> Iterable[bytes]:
        result = self.__stream.read(self.__data_size)
        while result:
            yield result
            result = self.__stream.read(self.__data_size)

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.__stream and not self.__stream.closed:
            self.__stream.close()