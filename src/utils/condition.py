from enum import Enum, auto
from typing import Union


class Condition(Enum):
    EQUAL = auto()
    GREATER_THAN = auto()
    LESS_THAN = auto()
    BETWEEN = auto()
    NOT_EQUAL = auto()
    CHANGED = auto()
    UNCHANGED = auto()
    INCREASED = auto()
    DECREASED = auto()

    def __init__(self, func):
        self._func = func

    def matches(self, parameters, current_value):
        match self:
            case Condition.EQUAL | Condition.UNCHANGED:
                return current_value is not None and parameters[0] == current_value
            case Condition.GREATER_THAN:
                return current_value is not None and current_value >= parameters[0]
            case Condition.LESS_THAN:
                return current_value is not None and current_value <= parameters[0]
            case Condition.BETWEEN:
                return current_value is not None and parameters[0] <= current_value <= parameters[1]
            case Condition.NOT_EQUAL | Condition.CHANGED:
                return current_value is not None and current_value != parameters[0]
            case Condition.INCREASED:
                return current_value is not None and current_value > parameters[0]
            case Condition.DECREASED:
                return current_value is not None and current_value < parameters[0]


class FilterCondition(Enum):
    FILTER_ADDRESS = auto()


OperationCondition = Union[Condition, FilterCondition]
