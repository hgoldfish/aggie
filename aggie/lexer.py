#!/usr/bin/env python

from enum import Enum


__all__ = ["TokenKind", "Lexer"]


class TokenKind(Enum):
    BAD = 0
    NEW_LINE = 1
    INDENT = 2
    DEDENT = 3
    IDENTIFIER = 4
    EOF = 5

    NUMBER = 11
    STRING = 12
    BYTES = 13

    COLON = 30
    ARROW = 31
    LEFT_BRACKET = 32
    RIGHT_BRACKET = 33
    LEFT_SQUARE = 34
    RIGHT_SQUARE = 35
    LEFT_CURLY = 36
    RIGHT_CURLY = 37
    COMMA = 38
    OPERATOR = 39
    ASSIGN = 40
    SEMICOLON = 41
    AT = 42

    TRUE = 101
    FALSE = 102
    NONE = 103
    #AND = 104
    AS = 105
    ASSERT = 106
    BREAK = 107
    CLASS = 108
    CONTINUE = 109
    DEF = 110
    DEL = 111
    ELIF = 112
    ELSE = 113
    EXCEPT = 114
    FINALLY = 115
    FOR = 116
    FROM = 117
    GLOBAL = 118
    IF = 119
    IMPORT = 120
    #IN = 121
    #IS = 122
    LAMBDA = 123
    NONLOCAL = 124
    #NOT = 125
    #OR = 126
    PASS = 127
    RAISE = 128
    RETURN = 129
    TRY = 130
    WHILE = 131
    WITH = 132
    YIELD = 133


class Token:
    pos = 0
    line = 0
    kind = TokenKind.BAD
    value = None

    def __repr__(self):
        return str(self)

    def __str__(self):
        if self.value:
            return "Token<{}({})@{}>".format(self.kind, self.value, self.line)
        else:
            return "Token<{}@{}>".format(self.kind, self.line)


def get_tokens(f):
    c = f.read(1)
    line = 0
    pos = 0
    current_intent = 0
    last_token = None

    def make_token(kind, value = None):
        nonlocal last_token
        token = Token()
        token.pos = pos
        token.line = line
        token.kind = kind
        token.value = value
        last_token = token
        return token

    def nextchar():
        nonlocal pos, c
        c = f.read(1)
        if c:
            pos +=1

    def read_str(as_bytes = False, ignore_escape = False):
        nonlocal line, c
        terminator = c
        nextchar() #ignore quote
        str_str = ""
        while True:
            if not c or c == "\n":
                line += 1
                return make_token(TokenKind.BAD)
            elif not ignore_escape and c == "\\":
                nextchar()
                if c in ("n", "r", "t", "v", "a", "b", "f", "\\", "\"", "'"):
                    nextchar()
                    str_str += c
                elif c == "x":
                    nextchar()
                    h = c
                    nextchar()
                    h += c
                    nextchar()
                    try:
                        char_code = int(h, 16)
                    except ValueError:
                        return make_token(TokenKind.BAD, h)
                    else:
                        str_str += chr(char_code)
                elif c in "01234567":
                    o = c
                    nextchar()
                    o += c
                    nextchar()
                    o += c
                    nextchar()
                    try:
                        char_code = int(o, 8)
                    except ValueError:
                        return make_token(TokenKind.BAD, o)
                    else:
                        str_str += chr(char_code)
                elif not as_bytes and c == "u":
                    nextchar()
                    h = ""
                    for i in range(4):
                        h += c
                        nextchar()
                    try:
                        char_code = int(h, 16)
                    except ValueError:
                        return make_token(TokenKind.BAD, h)
                    else:
                        str_str += chr(char_code)
                elif not as_bytes and c == "U":
                    nextchar()
                    h = ""
                    for i in range(8):
                        h += c
                        nextchar()
                    try:
                        char_code = int(h, 16)
                    except ValueError:
                        return make_token(TokenKind.BAD, h)
                    else:
                        str_str += chr(char_code)
                else:
                    return make_token(TokenKind.BAD)
            elif c == terminator:
                nextchar()
                if as_bytes:
                    return make_token(TokenKind.BYTES, str_str)
                else:
                    return make_token(TokenKind.STRING, str_str)
            else:
                str_str += c
                nextchar()

    while True:
        if c == " ":
            nextchar()
        elif c == "\n":
            line += 1
            nextchar()
        elif c == "#":
            nextchar()
            while c != "\n":
                nextchar()
        else:
            break

    yield make_token(TokenKind.NEW_LINE)
    yield make_token(TokenKind.INDENT) # 额外的缩进

    while True:
        if not c:
            if last_token and last_token.kind != TokenKind.NEW_LINE:
                yield make_token(TokenKind.NEW_LINE)
            for i in range(current_intent):
                yield make_token(TokenKind.DEDENT)
            yield make_token(TokenKind.DEDENT)  # 文件一开始有个额外的缩进
            yield make_token(TokenKind.EOF)
            return
        elif c == "\n":
            if last_token.kind == TokenKind.COMMA:   # Implicit line joining
                line += 1
                nextchar()
                continue

            emited = False
            while True:
                line += 1
                nextchar()
                if not emited:
                    emited = True
                    yield make_token(TokenKind.NEW_LINE)
                spaces = 0
                while c == " ":
                    spaces += 1
                    nextchar()
                if c == "\n":
                    continue
                elif c == "#":
                    nextchar()
                    while c != "\n":
                        nextchar()
                    continue
                else:
                    break
            if not c:
                continue

            if spaces % 4 != 0:
                yield make_token(TokenKind.BAD)
            else:
                intent = spaces // 4
                if intent > current_intent:
                    for i in range(intent - current_intent):
                        yield make_token(TokenKind.INDENT)
                    current_intent = intent
                elif intent < current_intent:
                    for i in range(current_intent - intent):
                        yield make_token(TokenKind.DEDENT)
                    current_intent = intent
                else:
                    pass
        elif c == "\\":  # Explicit line joining
            while c != "\n":
                nextchar()
            line += 1
            nextchar()
        elif c.isalpha() or c == "_": # 是不是应该支持一下中文？
            id_str = ''
            while c.isalnum() or c == "_":
                id_str += c
                nextchar()

            if id_str == "and":
                yield make_token(TokenKind.OPERATOR, "and")
            elif id_str == "as":
                yield make_token(TokenKind.AS)
            elif id_str == "assert":
                yield make_token(TokenKind.ASSERT)
            elif id_str == "break":
                yield make_token(TokenKind.BREAK)
            elif id_str == "class":
                yield make_token(TokenKind.CLASS)
            elif id_str == "continue":
                yield make_token(TokenKind.CONTINUE)
            elif id_str == "def":
                yield make_token(TokenKind.DEF)
            elif id_str == "del":
                yield make_token(TokenKind.DEL)
            elif id_str == "elif":
                yield make_token(TokenKind.ELIF)
            elif id_str == "else":
                yield make_token(TokenKind.ELSE)
            elif id_str == "except":
                yield make_token(TokenKind.EXCEPT)
            elif id_str == "False":
                yield make_token(TokenKind.FALSE)
            elif id_str == "finally":
                yield make_token(TokenKind.FINALLY)
            elif id_str == "for":
                yield make_token(TokenKind.FOR)
            elif id_str == "from":
                yield make_token(TokenKind.FROM)
            elif id_str == "global":
                yield make_token(TokenKind.GLOBAL)
            elif id_str == "if":
                yield make_token(TokenKind.IF)
            elif id_str == "import":
                yield make_token(TokenKind.IMPORT)
            elif id_str == "in":
                yield make_token(TokenKind.OPERATOR, "in")
            elif id_str == "is":
                yield make_token(TokenKind.OPERATOR, "is")
            elif id_str == "lambda":
                yield make_token(TokenKind.LAMBDA)
            elif id_str == "None":
                yield make_token(TokenKind.NONE)
            elif id_str == "nonlocal":
                yield make_token(TokenKind.NONLOCAL)
            elif id_str == "not":
                yield make_token(TokenKind.OPERATOR, "not")
            elif id_str == "or":
                yield make_token(TokenKind.OPERATOR, "or")
            elif id_str == "pass":
                yield make_token(TokenKind.PASS)
            elif id_str == "raise":
                yield make_token(TokenKind.RAISE)
            elif id_str == "return":
                yield make_token(TokenKind.RETURN)
            elif id_str == "True":
                yield make_token(TokenKind.TRUE)
            elif id_str == "try":
                yield make_token(TokenKind.TRY)
            elif id_str == "while":
                yield make_token(TokenKind.WHILE)
            elif id_str == "with":
                yield make_token(TokenKind.WITH)
            elif id_str == "yield":
                yield make_token(TokenKind.YIELD)
            elif id_str.lower() in ("u", "b", "r", "br", "rb"):
                if c == "\"" or c == "'":
                    yield read_str(as_bytes = ("b" in id_str), ignore_escape = ("r" in id_str))
                else:
                    yield make_token(TokenKind.IDENTIFIER, id_str)
            else:
                yield make_token(TokenKind.IDENTIFIER, id_str)
        elif c.isdigit():
            num_str = ""
            while c.isdigit() or c == ".":
                num_str += c
                nextchar()
            if num_str.count(".") > 1:
                yield make_token(TokenKind.BAD)
            else:
                if "." in num_str:
                    try:
                        num_f = float(num_str)
                    except ValueError:
                        yield make_token(TokenKind.BAD, num_str)
                    else:
                        yield make_token(TokenKind.NUMBER, num_f)
                else:
                    try:
                        num_i = int(num_str)
                    except ValueError:
                        yield make_token(TokenKind.BAD, num_str)
                    else:
                        yield make_token(TokenKind.NUMBER, num_i)
        elif c == "#":
            nextchar()
            while c and c != "\n":
                nextchar()
        elif c == ":":
            nextchar()
            yield make_token(TokenKind.COLON)
        elif c == "-":
            nextchar()
            if c == ">":
                nextchar()
                yield make_token(TokenKind.ARROW)
            else:
                yield make_token(TokenKind.OPERATOR, "-")
        elif c == "+":
            nextchar()
            yield make_token(TokenKind.OPERATOR, "+")
        elif c == "*":
            nextchar()
            if c == "*":
                nextchar()
                yield make_token(TokenKind.OPERATOR, "**")
            else:
                yield make_token(TokenKind.OPERATOR, "*")
        elif c == "@":
            nextchar()
            yield make_token(TokenKind.AT)
        elif c == "/":
            nextchar()
            if c == "/":
                nextchar()
                yield make_token(TokenKind.OPERATOR, "//")
            else:
                yield make_token(TokenKind.OPERATOR, "/")
        elif c == "%":
            nextchar()
            yield make_token(TokenKind.OPERATOR, "%")
        elif c == "<":
            nextchar()
            if c == "=":
                nextchar()
                yield make_token(TokenKind.OPERATOR, "<=")
            elif c == "<":
                nextchar()
                yield make_token(TokenKind.OPERATOR, "<<")
            else:
                yield make_token(TokenKind.OPERATOR, "<")
        elif c == ">":
            nextchar()
            if c == "=":
                nextchar()
                yield make_token(TokenKind.OEPRATOR, ">=")
            elif c == ">":
                nextchar()
                yield make_token(TokenKind.OPERATOR, ">>")
            else:
                yield make_token(TokenKind.OPERATOR, ">")
        elif c == "=":
            nextchar()
            if c == "=":
                nextchar()
                yield make_token(TokenKind.OPERATOR, "==")
            else:
                yield make_token(TokenKind.ASSIGN)
        elif c == "!":
            nextchar()
            if c == "=":
                nextchar()
                yield make_token(TokenKind.OPERATOR, "!=")
            else:
                yield make_token(TokenKind.BAD, "!")
        elif c == "~":
            nextchar()
            yield make_token(TokenKind.OPERATOR, "~")
        elif c == "|":
            nextchar()
            yield make_token(TokenKind.OPERATOR, "|")
        elif c == "&":
            nextchar()
            yield make_token(TokenKind.OPERATOR, "&")
        elif c == "^":
            nextchar()
            yield make_token(TokenKind.OPERATOR, "^")
        elif c == "(":
            nextchar()
            yield make_token(TokenKind.LEFT_BRACKET)
        elif c == ")":
            nextchar()
            yield make_token(TokenKind.RIGHT_BRACKET)
        elif c == "[":
            nextchar()
            yield make_token(TokenKind.LEFT_SQUARE)
        elif c == "]":
            nextchar()
            yield make_token(TokenKind.RIGHT_SQUARE)
        elif c == "{":
            nextchar()
            yield make_token(TokenKind.LEFT_CURLY)
        elif c == "}":
            nextchar()
            yield make_token(TokenKind.RIGHT_CURLY)
        elif c == ",":
            nextchar()
            yield make_token(TokenKind.COMMA)
        elif c == ".":
            nextchar()
            yield make_token(TokenKind.OPERATOR, ".")
        elif c == "\"" or c == "'":
            yield read_str(as_bytes = False, ignore_escape = False)
        elif c == ";":
            nextchar()
            yield make_token(TokenKind.SEMICOLON)
        elif c == " ":
            nextchar()
        else:
            print(pos, c)
            nextchar()
            yield make_token(TokenKind.BAD)


class Lexer:
    def __init__(self, f):
        self.tokens = get_tokens(f)
        try:
            self.current_token = next(self.tokens)
        except StopIteration:
            self.current_token = None

    def peek(self):
        return self.current_token

    def get(self):
        token = self.current_token
        if token:
            try:
                self.current_token = next(self.tokens)
            except StopIteration:
                self.current_token = None
            if token.kind == TokenKind.OPERATOR and token.value == "is" and \
                    self.current_token and self.current_token.kind == TokenKind.OPERATOR and \
                    self.current_token.value == "not":
                token.value = "is not"
                try:
                    self.current_token = next(self.tokens)
                except StopIteration:
                    self.current_token = None
            elif token.kind == TokenKind.OPERATOR and token.value == "not" and \
                    self.current_token and self.current_token.kind == TokenKind.OPERATOR and \
                    self.current_token.value == "in":
                token.value = "not in"
                try:
                    self.current_token = next(self.tokens)
                except StopIteration:
                    self.current_token = None
        return token
