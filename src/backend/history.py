from typing import Optional
from utils.operation import Operation, GenericOperation, FilterOperation
from utils.condition import FilterCondition


class History:
    def __init__(self):
        self.__history: list[Operation] = []
        self.__current_filter: Optional[FilterOperation] = None
        self.__last_scan: Optional[Operation] = None

    def append(self, operation: GenericOperation) -> None:
        if isinstance(operation, FilterOperation):
            self.__current_filter = operation

        if isinstance(operation, Operation):
            self.__history.append(operation)
            self.__last_scan = operation

    def filter(self, filter_str: str, filepath: str) -> None:
        if filter_str == '':
            self.__current_filter = None
            return
        self.__current_filter = FilterOperation(
            condition=FilterCondition.FILTER_ADDRESS,
            dtype=self.last.dtype,
            filepath=filepath,
            parent=self.last,
            filter_str=filter_str
        )

    @property
    def last(self) -> Operation:
        return self[-1]

    def get_current_filter(self) -> FilterOperation:
        return self.__current_filter

    def empty(self) -> bool:
        return len(self.__history) == 0

    def __getitem__(self, index: int) -> Operation:
        return self.__history[index]
