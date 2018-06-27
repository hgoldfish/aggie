#!/usr/bin/env python
from aggie.ast import FunctionDefinationStatement, Suite, PassStatement, ExpressionStatement, ReturnStatement, \
    BinaryExpression, VariableExpression, IntegerConstant, FloatConstant, StringConstant, NoneConstant, TrueConstant, \
    FalseConstant, CallExpression, IfStatement, WhileStatement, BreakStatement, ContinueStatement, ForStatement, \
    ConditionExpression, UnaryExpression, DelStatement, GetItemExpression, GetAttrExpression, TupleExpression, \
    ListExpression, DictExpression, BytesConstant, SubscriptExpression
from aggie.lexer import TokenKind
from .utils import ParseError

COMPILE_METHOD = ".__compile__"


def make_qname(upper_name, basename):
    if upper_name.endswith(COMPILE_METHOD):
        return upper_name[:-len(COMPILE_METHOD)] + "." + basename
    else:
        return upper_name + "." + basename


class Parser:
    def __init__(self, module_name):
        self.module_name = module_name
        self.function = None

    @staticmethod
    def match(token, kind, value = None, exception = ParseError):
        if token.kind != kind or (value is not None and value != token.value):
            raise exception("need {0}({1})but got {2}({3})".format(kind, value, token.kind, token.value))

    def parse(self, lexer):
        token = lexer.peek()
        if not token:
            return

        function = FunctionDefinationStatement()
        function.name = ""
        function.args = []
        function.rtype = "None"
        function.qname = self.module_name + COMPILE_METHOD
        function.upper = None
        self.function = function
        function.suite = self.parse_suite(lexer)
        del self.function
        return function

    def parse_function(self, lexer):
        function = FunctionDefinationStatement()
        token = lexer.get()
        self.match(token, TokenKind.DEF)
        token = lexer.get()
        self.match(token, TokenKind.IDENTIFIER)
        function.name = token.value
        function.qname = make_qname(self.function.qname, function.name)
        function.upper = self.function
        self.match(lexer.get(), TokenKind.LEFT_BRACKET)
        while True:
            if lexer.peek().kind != TokenKind.IDENTIFIER:
                break
            token = lexer.get()
            arg_name = token.value
            token = lexer.get()
            self.match(token, TokenKind.COLON)
            token = lexer.get()
            self.match(token, TokenKind.IDENTIFIER)
            arg_type = token.value
            function.args.append((arg_name, arg_type))
            if lexer.peek().kind == TokenKind.COMMA:
                lexer.get()
        self.match(lexer.get(), TokenKind.RIGHT_BRACKET)
        token = lexer.get()
        if token.kind == TokenKind.ARROW:
            token = lexer.get()
            if token.kind == TokenKind.NONE:
                function.rtype = "None"
            else:
                self.match(token, TokenKind.IDENTIFIER)
                function.rtype = token.value
            self.match(lexer.get(), TokenKind.COLON)
        else:
            function.rtype = "None"
            self.match(token, TokenKind.COLON)
        self.function = function
        function.suite = self.parse_suite(lexer)
        self.function = function.upper
        return function

    def parse_suite(self, lexer):
        suite = Suite()
        if lexer.peek().kind == TokenKind.NEW_LINE:
            self.match(lexer.get(), TokenKind.NEW_LINE)
            self.match(lexer.get(), TokenKind.INDENT)
            while True:
                statement = self.parse_compound_statement(lexer)
                if statement:
                    suite.statements.append(statement)
                else:
                    statements = self.parse_simple_statement(lexer)
                    suite.statements.extend(statements)
                token = lexer.peek()
                if token.kind == TokenKind.DEDENT:
                    lexer.get()
                    break
        else:
            suite.statements = self.parse_simple_statement(lexer)
            if not suite.statements:
                raise ParseError("suite requires statements.")
        return suite

    def parse_simple_statement(self, lexer):
        statements = []
        while True:
            token = lexer.peek()
            if token.kind == TokenKind.DEL:
                statements.append(self.parse_del_statement(lexer))
            elif token.kind == TokenKind.PASS:
                lexer.get()
                statements.append(PassStatement())
            elif token.kind == TokenKind.BREAK:
                lexer.get()
                statements.append(BreakStatement())
            elif token.kind == TokenKind.CONTINUE:
                statements.append(ContinueStatement())
            elif token.kind == TokenKind.RETURN:
                statements.append(self.parse_return_statement(lexer))
            else:
                statements.append(self.parse_expression_statement(lexer))
            if lexer.peek().kind == TokenKind.SEMICOLON:
                lexer.get()
            if lexer.peek().kind == TokenKind.NEW_LINE:
                lexer.get()
                break
        return statements

    def parse_compound_statement(self, lexer):
        token = lexer.peek()
        if token.kind == TokenKind.DEF:
            return self.parse_function(lexer)
        elif token.kind == TokenKind.IF:
            return self.parse_if(lexer)
        elif token.kind == TokenKind.WHILE:
            return self.parse_while(lexer)
        elif token.kind == TokenKind.FOR:
            return self.parse_for(lexer)
        return None

    def parse_expression_statement(self, lexer):
        statement = ExpressionStatement()
        expression = self.parse_test(lexer)
        token = lexer.peek()
        if token.kind == TokenKind.ASSIGN:
            lexer.get()
            if type(expression) is not VariableExpression:
                raise ParseError("must assign to a variable.")
            statement.variable = expression.name
            statement.expression = self.parse_test(lexer)
        else:
            statement.variable = ""
            statement.expression = expression
        return statement

    def parse_del_statement(self, lexer):
        statement = DelStatement()
        self.match(lexer.get(), TokenKind.DEL)
        while True:
            expression = self.parse_expression(lexer)
            statement.expressions.append(expression)
            if lexer.peek() != TokenKind.COMMA:
                break
            lexer.get()
            if lexer.peek() in (TokenKind.NEW_LINE, TokenKind.SEMICOLON):
                break
        return statement

    def parse_return_statement(self, lexer):
        statement = ReturnStatement()
        token = lexer.get()
        self.match(token, TokenKind.RETURN)
        if lexer.peek().kind in (TokenKind.NEW_LINE, TokenKind.SEMICOLON):
            return statement
        statement.expression = self.parse_test(lexer)
        return statement

    def parse_if(self, lexer):
        statement = IfStatement()
        self.match(lexer.get(), TokenKind.IF)
        first_condition = self.parse_test(lexer)
        self.match(lexer.get(), TokenKind.COLON)
        first_suite = self.parse_suite(lexer)
        statement.flow.append([first_condition, first_suite])
        while True:
            token = lexer.peek()
            if token.kind == TokenKind.ELIF:
                self.match(lexer.get(), TokenKind.ELIF)
                condition = self.parse_test(lexer)
                self.match(lexer.get(), TokenKind.COLON)
                suite = self.parse_suite(lexer)
                statement.flow.append([condition, suite])
            elif token.kind == TokenKind.ELSE:
                self.match(lexer.get(), TokenKind.ELSE)
                self.match(lexer.get(), TokenKind.COLON)
                statement.otherwise = self.parse_suite(lexer)
            else:
                break
        return statement

    def parse_while(self, lexer):
        statement = WhileStatement()
        self.match(lexer.get(), TokenKind.WHILE)
        statement.condition = self.parse_test(lexer)
        self.match(lexer.get(), TokenKind.COLON)
        statement.suite = self.parse_suite(lexer)
        token = lexer.peek()
        if token.kind == TokenKind.ELSE:
            self.match(lexer.get(), TokenKind.ELSE)
            self.match(lexer.get(), TokenKind.COLON)
            statement.otherwise = self.parse_suite(lexer)
        return statement

    def parse_for(self, lexer):
        statement = ForStatement()
        self.match(lexer.get(), TokenKind.FOR)
        token = lexer.get()
        self.match(token, TokenKind.IDENTIFIER)
        statement.variable = token.value
        self.match(lexer.get(), TokenKind.OPERATOR, "in")
        statement.iterator = self.parse_expression(lexer)
        self.match(lexer.get(), TokenKind.COLON)
        statement.suite = self.parse_suite(lexer)
        return statement

    def parse_subscript(self, lexer):
        token = lexer.peek()
        if token.kind == TokenKind.COLON:
            start = IntegerConstant(0)
        else:
            start = self.parse_test(lexer)
        token = lexer.peek()
        if token.kind != TokenKind.COLON:
            return start
        token.get()  # first colon

        token = lexer.peek()
        if token.kind == TokenKind.COMMA or token.kind == TokenKind.RIGHT_SQUARE:  # no second colon
            end = IntegerConstant(-1)
            step = IntegerConstant(1)
            return SubscriptExpression(start, end, step)
        elif token.kind == TokenKind.COLON:  # second colon
            end = IntegerConstant(-1)
            lexer.get()
        else:  # may be has second colon, but first parse the end expression
            end = self.parse_test(lexer)
            token = lexer.peek()
            if token.kind != TokenKind.COLON:  # second colon
                end = IntegerConstant(-1)
                step = IntegerConstant(1)
                return SubscriptExpression(start, end, step)
            else:
                lexer.get()
        token = lexer.peek()
        if token.kind == TokenKind.COMMA or token.kind == TokenKind.RIGHT_SQUARE:
            step = IntegerConstant(1)
        else:
            step = self.parse_test(lexer)
        return SubscriptExpression(start, end, step)

    def parse_test(self, lexer):
        or_test = self.try_parse_or_test(lexer)
        token = lexer.peek()
        if token.kind != TokenKind.IF:
            return or_test
        lexer.get()
        condition = self.try_parse_or_test(lexer)
        self.match(lexer.get(), TokenKind.ELSE)
        false_value = self.parse_test(lexer)
        return ConditionExpression(condition, or_test, false_value)

    def try_parse_or_test(self, lexer):
        return self.try_parse_binary(lexer, ("or", ), self.try_parse_and_test)

    def try_parse_and_test(self, lexer):
        return self.try_parse_binary(lexer, ("and", ), self.try_parse_not_test)

    def try_parse_not_test(self, lexer):
        token = lexer.peek()
        if token.kind == TokenKind.OPERATOR and token.value == "not":
            lexer.get()
            expr = UnaryExpression()
            expr.operator = "not"
            expr.value = self.try_parse_not_test(lexer)
            return expr
        else:
            return self.try_parse_comparison(lexer)

    def try_parse_comparison(self, lexer):
        return self.try_parse_binary(lexer, ("<", ">", "==", ">=", "<=", "!=", "in", "not in", "is", "is not"), self.parse_expression)

    def parse_expression(self, lexer):
        return self.try_parse_binary(lexer, ("|", ), self.try_parse_xor_expr)

    def try_parse_xor_expr(self, lexer):
        return self.try_parse_binary(lexer, ("^", ), self.try_parse_and_expr)

    def try_parse_and_expr(self, lexer):
        return self.try_parse_binary(lexer, ("&", ), self.try_parse_shift_expr)

    def try_parse_shift_expr(self, lexer):
        return self.try_parse_binary(lexer, ("<<", ">>"), self.try_parse_arith_expr)

    def try_parse_arith_expr(self, lexer):
        return self.try_parse_binary(lexer, ("+", "-"), self.try_parse_term)

    def try_parse_term(self, lexer):
        return self.try_parse_binary(lexer, ("*", "/", "//", "%"), self.try_parse_factor)

    def try_parse_factor(self, lexer):
        token = lexer.peek()
        if token.kind == TokenKind.OPERATOR and token.value in ("+", "-", "~"):
            lexer.get()
            expr = UnaryExpression()
            expr.operator = token.value
            expr.value = self.try_parse_factor(lexer)
            return expr
        else:
            return self.try_parse_power(lexer)

    def try_parse_power(self, lexer):
        atom_expr = self.try_parse_atom_expr(lexer)
        token = lexer.peek()
        if token.kind == TokenKind.OPERATOR and token.value == "**":
            exp = self.try_parse_power(lexer)
            return BinaryExpression("**", atom_expr, exp)
        else:
            return atom_expr

    @staticmethod
    def try_parse_binary(lexer, operators, callback):
        lhs = None
        operator = None
        while True:
            sub_expression = callback(lexer)
            if lhs is not None:
                lhs = BinaryExpression(operator, lhs, sub_expression)
            else:
                lhs = sub_expression
            token = lexer.peek()
            if token.kind == TokenKind.OPERATOR and token.value in operators:
                lexer.get()
                operator = token.value
            else:
                break
        return lhs

    def try_parse_atom_expr(self, lexer):
        left = self.try_parse_atom(lexer)
        while True:
            token = lexer.peek()
            if token.kind == TokenKind.LEFT_BRACKET:
                args = []
                self.match(lexer.get(), TokenKind.LEFT_BRACKET)
                while lexer.peek().kind != TokenKind.RIGHT_BRACKET:
                    args.append(self.parse_test(lexer))
                    if lexer.peek().kind == TokenKind.COMMA:
                        lexer.get()
                    else:
                        break
                self.match(lexer.get(), TokenKind.RIGHT_BRACKET)
                left = CallExpression(left, args)
            elif token.kind == TokenKind.LEFT_SQUARE:
                args = []
                self.match(token.get(), TokenKind.LEFT_SQUARE)
                while lexer.peek().kind != TokenKind.RIGHT_SQUARE:
                    args.append(self.parse_subscript(lexer))
                    if lexer.peek().kind == TokenKind.COMMA:
                        lexer.get()
                    else:
                        break
                self.match(lexer.get(), TokenKind.RIGHT_SQUARE)
                left = GetItemExpression(left, args)
            elif token.kind == TokenKind.OPERATOR and token.value == ".":
                lexer.get()
                token = lexer.get()
                self.match(token, TokenKind.IDENTIFIER)
                left = GetAttrExpression(left, token.value)
            else:
                break
        return left

    def try_parse_atom(self, lexer):
        token = lexer.get()
        if token.kind == TokenKind.LEFT_BRACKET:
            testlist = []
            is_tuple = False
            while lexer.peek().kind != TokenKind.RIGHT_BRACKET:
                testlist.append(self.parse_test(lexer))
                is_tuple = False
                if lexer.peek().kind == TokenKind.COMMA:
                    is_tuple = True
                    lexer.get()
                else:
                    break
            self.match(lexer.get(), TokenKind.RIGHT_BRACKET)
            if not testlist:
                return TupleExpression(testlist)
            elif len(testlist) == 1 and not is_tuple:
                return testlist[0]
            else:
                return TupleExpression(testlist)
        elif token.kind == TokenKind.LEFT_SQUARE:
            testlist = []
            while lexer.peek().kind != TokenKind.RIGHT_SQUARE:
                testlist.append(self.parse_test(lexer))
                if lexer.peek().kind == TokenKind.COMMA:
                    lexer.get()
                else:
                    break
            self.match(lexer.get(), TokenKind.RIGHT_SQUARE)
            return ListExpression(testlist)
        elif token.kind == TokenKind.LEFT_CURLY:
            ordered_items = []
            while lexer.peek().kind != TokenKind.RIGHT_CURLY:
                key = self.parse_test(lexer)
                self.match(lexer.get(), TokenKind.COLON)
                value = self.parse_test(lexer)
                ordered_items.append((key, value))
                if lexer.peek().kind == TokenKind.COMMA:
                    lexer.get()
                else:
                    break
            self.match(lexer.get(), TokenKind.RIGHT_CURLY)
            return DictExpression(ordered_items)
        elif token.kind == TokenKind.IDENTIFIER:
                return VariableExpression(token.value)
        elif token.kind == TokenKind.NUMBER:
            if type(token.value) is int:
                return IntegerConstant(token.value)
            else:
                return FloatConstant(token.value)
        elif token.kind == TokenKind.STRING:
            return StringConstant(token.value)
        elif token.kind == TokenKind.BYTES:
            return BytesConstant(token.value.encode("utf-8"))
        elif token.kind == TokenKind.NONE:
            return NoneConstant()
        elif token.kind == TokenKind.TRUE:
            return TrueConstant()
        elif token.kind == TokenKind.FALSE:
            return FalseConstant()
        else:
            raise ParseError("unhandled atom token: {}".format(token.kind))


def parse(lexer, name = "main"):
    return Parser(name).parse(lexer)
