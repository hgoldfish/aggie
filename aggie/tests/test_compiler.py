import io
import unittest

from aggie.compiler import Compiler
from aggie.lexer import Lexer
from aggie.parser import parse


class CompilerTest(unittest.TestCase):
    def test_simple(self):
        prog = """
def add(x: int, y: int) -> int:
    z = x + y
    return z

def main() -> int:
    return add(1, 2)

main()
"""
        print(self.compile(prog))

    def compile(self, prog):
        lexer = Lexer(io.StringIO(prog))
        function = parse(lexer)
        compiler = Compiler()
        compiler.compile("main", function)
        return str(compiler.ir_module)

    def test_compare(self):
        print(self.compile("1 > 2"))
        print(self.compile("1 < 2"))
        print(self.compile("1.0 == 1.1"))

    def test_if(self):
        prog = """
def choose(x: int) -> int:
    if x == 1:
        return 11
    elif x == 2:
        return 22
    elif x == 3:
        return 33
    else:
        return 44
choose(1)
"""
        print(self.compile(prog))

    def test_while(self):
        prog = """
def factor(n: int) -> int:
    result = 1
    i = 2
    while i < n:
        result = result * i
        i = i + 1
    else:
        pass
    return result
"""
        print(self.compile(prog))
