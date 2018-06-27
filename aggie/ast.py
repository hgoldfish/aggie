#!/usr/bin/env python

import io


class ASTNode:
    def dump(self):
        return ""


class Expression(ASTNode):
    pass


class Statement(ASTNode):
    pass


class Suite(ASTNode):
    statements = list()   # list[Statement]()

    def __init__(self):
        self.statements = []

    def dump(self):
        buf = io.StringIO()
        for statement in self.statements:
            lines = statement.dump().split("\n")
            for line in lines:
                buf.write(" " * 4 + line + "\n")
        return buf.getvalue()


class BinaryExpression(Expression):
    operator = ""
    lhs = Expression()
    rhs = Expression()

    def __init__(self, operator, lhs, rhs):
        self.operator = operator
        self.lhs = lhs
        self.rhs = rhs

    def dump(self):
        return self.lhs.dump() + " " + self.operator + " " + self.rhs.dump()


class VariableExpression(Expression):
    name = ""

    def __init__(self, name):
        self.name = name

    def dump(self):
        return self.name


class CallExpression(Expression):
    target = Expression()
    args = []

    def __init__(self, target, args):
        self.target = target
        self.args = args

    def dump(self):
        l = []
        for arg in self.args:
            l.append(arg.dump())
        return self.target.dump() + "(" + ", ".join(l) + ")"


class GetAttrExpression(Expression):
    target = Expression()
    item = ""

    def __init__(self, target, item):
        self.target = target
        self.item = item

    def dump(self):
        return "{}.{}".format(self.target.dump(), self.item)


class GetItemExpression(Expression):
    target = Expression()
    args = []

    def __init__(self, target, args):
        self.target = target
        self.args = args

    def dump(self):
        l = []
        for arg in self.args:
            l.append(arg.dump())
        return self.target.dump() + "[" + ", ".join(l) + "]"


class ConditionExpression(Expression):
    condition = Expression()
    true_value = Expression()
    false_value = Expression()

    def __init__(self, condition, true_value, false_value):
        self.condition = condition
        self.true_value = true_value
        self.false_value = false_value

    def dump(self):
        return "{} if {} else {}".format(self.true_value.dump(), self.condition.dump(), self.false_value.dump())


class UnaryExpression(Expression):
    operator = ""
    value = Expression()

    def dump(self):
        if self.operator == "not":
            return "not {}".format(self.value)
        else:
            return "{}{}".format(self.operator, self.value)


class TupleExpression(Expression):
    items = []

    def __init__(self, items):
        self.items = items

    def dump(self):
        l = []
        for item in self.items:
            l.append(item.dump())
        return "(" + ",".join(l) + ")"


class ListExpression(Expression):
    items = []

    def __init__(self, items):
        self.items = items

    def dump(self):
        l = []
        for item in self.items:
            l.append(item.dump())
        return "[" + ",".join(l) + "]"


class DictExpression(Expression):
    ordered_items = []

    def __init__(self, ordered_items):
        self.ordered_items = ordered_items

    def dump(self):
        l = []
        for key, value in self.ordered_items:
            l.append("    " + key.dump() + ": " + value.dump() + "\n")
        return "{\n" + "".join(l) + "}"


class SubscriptExpression(Expression):
    start = Expression()
    end = Expression()
    step = Expression()

    def __init__(self, start, end, step):
        self.start = start
        self.end = end
        self.step = step

    def dump(self):
        buf = io.StringIO()
        if not (isinstance(self.start, IntegerConstant) and self.start.value == 0):
            buf.write(self.start.dump())
        buf.write(":")
        if not (isinstance(self.start, IntegerConstant) and self.end.value == -1):
            buf.write(self.end.dump())
        if not (isinstance(self.step, IntegerConstant) and self.step.value == 1):
            buf.write(":")
            buf.write(self.step.dump())


class StringConstant(Expression):
    value = ""

    def __init__(self, value):
        self.value = value

    def dump(self):
        return repr(self.value)


class BytesConstant(Expression):
    value = b""

    def __init__(self, value):
        self.value = value

    def dump(self):
        return repr(self.value)


class IntegerConstant(Expression):
    value = 0

    def __init__(self, value):
        self.value = value

    def dump(self):
        return str(self.value)


class FloatConstant(Expression):
    value = 0.0

    def __init__(self, value):
        self.value = value

    def dump(self):
        return str(self.value)


class TrueConstant(Expression):
    def dump(self):
        return "True"


class FalseConstant(Expression):
    def dump(self):
        return "False"


class NoneConstant(Expression):
    def dump(self):
        return "None"


class ExpressionStatement(Statement):
    variable = ""
    expression = Expression()

    def dump(self):
        if self.variable:
            return self.variable + " = " + self.expression.dump()
        else:
            return self.expression.dump()


class DelStatement(Statement):
    expressions = list()

    def __init__(self):
        self.expressions = []

    def dump(self):
        return "del {}".format(", ".join(expression.dump() for expression in self.expressions))


class PassStatement(Statement):
    def dump(self):
        return "pass"


class ReturnStatement(Statement):
    expression = Expression()

    def __init__(self):
        self.expression = None

    def dump(self):
        if self.expression:
            return "return " + self.expression.dump()
        else:
            return "return"


class BreakStatement(Statement):
    def dump(self):
        return "break"


class ContinueStatement(Statement):
    def dump(self):
        return "continue"


class FunctionDefinationStatement(Statement):
    name = ""
    args = []
    rtype = ""
    suite = Suite()

    upper = None
    qname = ""

    def __init__(self):
        self.args = []

    def dump(self):
        buf = io.StringIO()
        buf2 = []
        for arg in self.args:
            buf2.append("{0}: {1}".format(arg[0], arg[1]))

        if self.name:
            buf.write("def {0}({1}) -> {2}:\n".format(self.name, ", ".join(buf2), self.rtype))
            buf.write(self.suite.dump())
        else:
            lines = self.suite.dump().split("\n")
            for line in lines:
                line = line[4:]
                buf.write(line + "\n")
        return buf.getvalue()


class IfStatement(Statement):
    flow = []
    otherwise = Suite()

    def __init__(self):
        self.flow = []
        self.otherwise = None

    def dump(self):
        assert self.flow
        first_conditon, first_suite = self.flow[0]
        buf = io.StringIO()
        buf.write("if {}:\n".format(first_conditon.dump()))
        buf.write(first_suite.dump())
        for condition, suite in self.flow[1:]:
            buf.write("elif {}:\n".format(condition.dump()))
            buf.write(suite.dump())
        if self.otherwise:
            buf.write("else:\n")
            buf.write(self.otherwise.dump())
        return buf.getvalue()


class WhileStatement(Statement):
    condition = Expression()
    suite = Suite()
    otherwise = Suite()

    def __init__(self, ):
        self.condition = None
        self.suite = None
        self.otherwise = None

    def dump(self):
        buf = "while {}:\n{}".format(self.condition.dump(), self.suite.dump())
        if self.otherwise:
            buf += "else:{}\n".format(self.otherwise.dump())
        return buf


class ForStatement(Statement):
    variable = ""
    iterator = Expression()
    suite = Suite()

    def dump(self):
        buf = io.StringIO()
        buf.write("for {} in {}:\n".format(self.variable, self.iterator.dump()))
        buf.write(self.suite.dump())
        return buf.getvalue()
