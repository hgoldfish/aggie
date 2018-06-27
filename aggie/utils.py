from enum import Enum


class ParseError(Exception):
    pass


class CodegenError(Exception):
    pass


class FunctionNotFound(CodegenError):
    pass


class Safety(Enum):
    NoSafe = 0
    ThreadSafe = 1
    Reenterence = 2
