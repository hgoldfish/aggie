from .utils import CanNotInline, SubBuilder, ComparableType


class FloatType(SubBuilder, ComparableType):
    def convert_bool(self, bool_expr):
        return self.ir_builder.select(bool_expr, self.ir_const(1.0), self.ir_const(0.0))

    def rich_compare(self, x, y, operator, name):
        if y.type == "int":
            converted_y = self.ir_builder.sitofp(y.value, self.function_builder.get_ir_type("float"))
            result = self.ir_builder.fcmp_ordered(operator, x.value, converted_y, name = name)
        elif y.type == "float":
            result = self.ir_builder.fcmp_ordered(operator, x.value, y.value, name = name)
        elif y.type == "bool":
            converted_y = self.convert_bool(y.value)
            result = self.ir_builder.fcmp_ordered(operator, x.value, converted_y, name = name)
        else:
            raise CanNotInline()
        return self.primitive("bool", result)

    def arithmetic(self, x, y, irbuild_function, name):
        if x.type == "int":
            converted_x = self.ir_builder.sitofp(x.value, self.function_builder.get_ir_type("float"))
        elif x.type == "float":
            converted_x = x.value
        elif x.type == "bool":
            converted_x = self.ir_builder.select(x.value, self.ir_const(1.0), self.ir_const(0.0))
        else:
            raise CanNotInline()

        if y.type == "int":
            converted_y = self.ir_builder.sitofp(y.value, self.function_builder.get_ir_type("float"))
        elif y.type == "float":
            converted_y = y.value
        elif y.type == "bool":
            converted_y = self.convert_bool(y.value)
        else:
            raise CanNotInline()

        result = irbuild_function(converted_x, converted_y, name = name)
        return self.primitive("float", result)

    def dot__abs__(self, x):
        less_than_zero = self.ir_builder.fcmp_ordered("<", x.value, self.ir_const(0.0),
            name = "abs.less_than_zero")
        result = self.ir_builder.select(less_than_zero, self.ir_builder.fneg(x.value, name = "negtmp"), x.value)
        return self.primitive("float", result)

    def dot__add__(self, x, y):
        return self.arithmetic(x, y, self.ir_builder.fadd, "addtmp")

    def dot__bool__(self, x):
        result = self.ir_builder.fcmp_ordered("!=", x.value, self.ir_const(0.0), name = "booltmp")
        return self.primitive("bool", result)

    def dot__float__(self, x):
        return x

    def dot__floordiv__(self, x, y):
        if y.type == "int":
            converted_y = self.ir_builder.sitofp(y.value, self.function_builder.get_ir_type("float"))
            t1 = self.ir_builder.frem(x.value, converted_y)
            t2 = self.ir_builder.sub(x.value, t1)
            result = self.ir_builder.fdiv(t2, converted_y, name = "ffdivtmp")
        elif y.type == "float":
            t1 = self.ir_builder.frem(x.value, y.value)
            t2 = self.ir_builder.sub(x.value, t1)
            result = self.ir_builder.fdiv(t2, y.value, name = "ffdivtmp")
        elif y.type == "bool":
            converted_y = self.convert_bool(y.value)
            t1 = self.ir_builder.frem(x.value, converted_y)
            t2 = self.ir_builder.sub(x.value, t1)
            result = self.ir_builder.fdiv(t2, converted_y, name = "ffdivtmp")
        else:
            raise CanNotInline()
        return self.primitive("float", result)

    def dot__int__(self, x):
        result = self.ir_builder.fptosi(x.value, self.function_builder.get_ir_type("int"), name = "inttmp")
        return self.primitive("int", result)

    def dot__mod__(self, x, y):
        return self.arithmetic(x, y, self.ir_builder.frem, "modtmp")

    def dot__mul__(self, x, y):
        return self.arithmetic(x, y, self.ir_builder.fmul, "multmp")

    def dot__neg__(self, x):
        result = self.ir_builder.fneg(x.value, name = "negtmp")
        return self.primitive("float", result)

    def dot__pos__(self, x):
        return x

    def dot__pow__(self, x, y):
        raise CanNotInline()

    def dot__radd__(self, y, x):
        return self.arithmetic(x, y, self.ir_builder.fadd, "addtmp")

    def dot__rfloordiv__(self, y, x):
        if x.type == "int":
            converted_x = self.ir_builder.sitofp(x.type, self.function_builder.get_ir_type("float"))
            t1 = self.ir_builder.frem(converted_x, y.value)
            t2 = self.ir_builder.sub(converted_x, t1)
            result = self.ir_builder.fdiv(t2, y.value, name = "ffdivtmp")
        elif x.type == "bool":
            converted_x = self.convert_bool(x.value)
            t1 = self.ir_builder.frem(converted_x, y.value)
            t2 = self.ir_builder.sub(converted_x, t1)
            result = self.ir_builder.fdiv(t2, y.value, name = "ffdivtmp")
        else:
            raise CanNotInline()
        return self.primitive("float", result)

    def dot__rmod__(self, y, x):
        return self.arithmetic(x, y, self.ir_builder.frem, "modtmp")

    def dot__rmul__(self, y, x):
        return self.arithmetic(x, y, self.ir_builder.fmul, "multmp")

    def dot__rpow__(self, y, x):
        raise CanNotInline()

    def dot__round__(self, x):
        raise CanNotInline()

    def dot__rsub__(self, y, x):
        return self.arithmetic(x, y, self.ir_builder.fsub, "subtmp")

    def dot__rtruediv__(self, y, x):
        return self.arithmetic(x, y, self.ir_builder.fdiv, "divtmp")

    def dot__sizeof__(self):
        return self.ir_const(8)

    def dot__str__(self, x):
        raise CanNotInline()

    def dot__sub__(self, x, y):
        return self.arithmetic(x, y, self.ir_builder.fsub, "subtmp")

    def dot__truediv__(self, x, y):
        return self.arithmetic(x, y, self.ir_builder.fdiv, "divtmp")
