import io
import unittest

from aggie.lexer import Lexer
from aggie.parser import parse


class ParseTestCase(unittest.TestCase):
    def test_simple(self):
        prog = """
# comment appear here
def add(x: int, y: int) -> int:
    return x + y + 1.0 / 3

def main() -> int:
    return add(1, 2)

def max(x: int, y: int) -> int:
    if x > y:
        return x
    else:
        return y

def sum(l: list) -> int:
    total = 0
    for i in l:
        total = total + i
    return total

if __name__ == "__main__":
    main()

"""
        lexer = Lexer(io.StringIO(prog))
        function = parse(lexer)
        print(function.dump())

    def test_oneline(self):
        line = "1 < 2"
        lexer = Lexer(io.StringIO(line))
        function = parse(lexer)
        print(function.dump())

