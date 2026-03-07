import os

from numpy.typing import NDArray, DTypeLike
from typing import BinaryIO
from logging import Logger, getLogger
import numpy as np


class MappedFileReader:

    __logger: Logger = getLogger(__qualname__)

    def __init__(self, page_size: int = 100):
        self.__page_size: int = page_size

        self.__dtype: DTypeLike | None = None
        self.__address_list: NDArray | None = None
        self.__filepath: str | None = None
        self.__current_page_number: int = 0
        self.__total_page_number: int = 0

    def set_file(self, filepath: str, dtype: DTypeLike) -> None:
        self.reset()
        self.__filepath = filepath
        self.__dtype = dtype
        if os.path.getsize(filepath) == 0:
            self.__address_list = np.empty((0,), dtype=dtype)
        else:
            self.__address_list = np.memmap(filepath, dtype=dtype, mode="r")
        self.__total_page_number = len(self.__address_list) // self.__page_size
        self.__current_page_number = 0
        self.__logger.debug(f'File {filepath} loaded')

    def read_chunk(self, start: int, chunk_size: int = 100) -> NDArray:
        return self.__address_list[start:start + chunk_size]

    def next_page(self) -> int:
        self.__current_page_number = min(self.__current_page_number + 1, self.__total_page_number)
        return self.__current_page_number

    def prev_page(self) -> int:
        self.__current_page_number = max(self.__current_page_number - 1, 0)
        return self.__current_page_number

    def read_page(self) -> NDArray:
        if self.__address_list is None or len(self.__address_list) == 0:
            return np.empty((0, ), dtype=self.__dtype)
        page_start = max(min(self.__page_size * self.__current_page_number, self.size), 0)
        page_end = min(self.size, page_start + self.__page_size)
        return self.__address_list[page_start:page_end]

    def reload_file(self) -> None:
        del self.__address_list
        self.set_file(self.__filepath, self.__dtype)

    def filter_addresses(self, out_file: BinaryIO, filter_string: str = '', chunk_size: int = 100_000) -> int:
        if self.__address_list is None:
            self.__logger.debug(f'Address list is empty')
            return 0

        file_size = len(self.__address_list)
        if filter_string == '':
            self.__logger.debug(f'filter_string is empty')
            return file_size

        vectorized_checker = np.vectorize(lambda number, search_str: search_str in hex(number)[2:])

        if chunk_size == -1:
            chunk_size = file_size

        data_written = 0

        with open(self.__filepath, "rb") as f:
            for i in range(0, file_size, chunk_size):
                data = f.read(chunk_size)
                arr = np.frombuffer(data, dtype=self.dtype)
                mask = vectorized_checker(arr[:]['num'], search_str=vectorized_checker)
                result = arr[mask].tobytes()
                data_written += len(result)
                out_file.write(result)
        self.__logger.debug(f'Filtered {data_written} bytes')

        return data_written

    @property
    def filepath(self) -> str:
        return self.__filepath

    @property
    def dtype(self) -> DTypeLike:
        return self.__dtype

    @property
    def size(self) -> int:
        if self.__address_list is None:
            return 0
        return len(self.__address_list)

    @property
    def page_size(self) -> int:
        return self.__page_size

    def reset(self):
        self.__dtype = None
        self.__address_list = None
        self.__filepath = None
        self.__current_page_number = 0
        self.__total_page_number = 0

    def close(self) -> None:
        del self.__address_list

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        del self.__address_list
