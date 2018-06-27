import io
import unittest

from aggie.lexer import Lexer


class LexerTest(unittest.TestCase):
    def test_oneline(self):
        prog = "1 < 2"
        lexer = Lexer(io.StringIO(prog))
        while True:
            token = lexer.get()
            if not token:
                break
            print(repr(token))
