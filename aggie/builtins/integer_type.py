from .utils import CanNotInline, SubBuilder, ComparableType


class IntegerType(SubBuilder, ComparableType):
    def rich_compare(self, x, y, operator, name):
        if y.type == "int":
            result = self.ir_builder.icmp_signed(operator, x.value, y.value, name = name)
        elif y.type == "bool":
            converted_y = self.ir_builder.select(y.value, self.ir_const(1), self.ir_const(0))
            result = self.ir_builder.icmp_signed(operator, x.value, converted_y, name = name)
        elif y.type == "float":
            converted_x = self.ir_builder.sitofp(x.value, self.function_builder.get_ir_type("float"))
            result = self.ir_builder.fcmp_ordered(operator, converted_x, y.value, name = name)
        else:
            raise CanNotInline()
        return self.primitive("bool", result)

    def arithmetic(self, x, y, ir_build_function, name):
        if x.type == "int":
            converted_x = x.value
        elif x.type == "bool":
            converted_x = self.ir_builder.select(x.value, self.ir_const(1), self.ir_const(0))
        else:
            raise CanNotInline()

        if y.type == "int":
            converted_y = y.value
        elif y.type == "bool":
            converted_y = self.ir_builder.select(y.value, self.ir_const(1), self.ir_const(0))
        else:
            raise CanNotInline()

        result = ir_build_function(converted_x, converted_y, name = name)
        return self.primitive("int", result)

    def dot__abs__(self, x):
        less_than_zero = self.ir_builder.icmp_signed("<", x.value, self.ir_const(0), name = "abs.less_than_zero")
        neg = self.ir_builder.neg(x.value, name = "negtmp")
        result = self.ir_builder.select(less_than_zero, neg, x.value)
        return self.primitive("int", result)

    def dot__add__(self, x, y):
        return self.arithmetic(x, y, self.ir_builder.add, "addtmp")

    def dot__and__(self, x, y):
        return self.arithmetic(x, y, self.ir_builder.and_, "andtmp")

    def dot__bool__(self, x):
        result = self.ir_builder.icmp_signed("!=", x.value, self.ir_const(0), name = "booltmp")
        return self.primitive("bool", result)

    def dot__float__(self, x):
        result = self.ir_builder.sitofp(x.value, self.function_builder.get_ir_type("float"), name = "floattmp")
        return self.primitive("float", result)

    def dot__floor__(self, x):
        raise CanNotInline()

    def dot__floordiv__(self, x, y):
        return self.arithmetic(x, y, self.ir_builder.div, "floordivtmp")

    def dot__int__(self, x):
        return x

    def dot__invert__(self, x):
        result = self.ir_builder.not_(x.value, name = "inverttmp")
        return self.primitive("int", result)

    def dot__lshift__(self, x, y):
        return self.arithmetic(x, y, self.ir_builder.shl, "shltmp")

    def dot__mod__(self, x, y):
        if y.type == "int":
            result = self.ir_builder.srem(x.value, y.value, name = "modtmp")
        elif y.type == "bool":
            converted_y = self.ir_builder.select(y.value, self.ir_const(1), self.ir_const(0))
            result = self.ir_builder.srem(x.value, converted_y, name = "modtmp")
        else:
            raise CanNotInline()
        return self.primitive("int", result)

    def dot__mul__(self, x, y):
        return self.arithmetic(x, y, self.ir_builder.mul, "multmp")

    def dot__neg__(self, x):
        result = self.ir_builder.neg(x.value, name = "negtmp")
        return self.primitive("int", result)

    def dot__or__(self, x, y):
        return self.arithmetic(x, y, self.ir_builder.or_, "ortmp")

    def dot__pos__(self, x):
        return x

    def dot__pow__(self, x, y):
        raise CanNotInline()

    def dot__radd__(self, y, x):
        return self.arithmetic(x, y, self.ir_builder.add, "addtmp")

    def dot__rand__(self, y, x):
        return self.arithmetic(x, y, self.ir_builder.and_, "andtmp")

    def dot__repr__(self, x):
        raise CanNotInline()

    def dot__rlshift__(self, y, x):
        return self.arithmetic(x, y, self.ir_builder.shl, "shltmp")

    def dot__rmod__(self, y, x):
        return self.arithmetic(x, y, self.ir_builder.srem, "modtmp")

    def dot__rmul__(self, y, x):
        return self.arithmetic(x, y, self.ir_builder.mul, "multmp")

    def dot__ror__(self, y, x):
        return self.arithmetic(x, y, self.ir_builder.or_, "ortmp")

    def dot__rpow__(self, y, x):
        raise CanNotInline()

    def dot__rrshift__(self, y, x):
        return self.arithmetic(x, y, self.ir_builder.ashr, "rshrtmp")

    def dot__round__(self, x, y):
        raise CanNotInline()

    def dot__rshift__(self, x, y):
        return self.arithmetic(x, y, self.ir_builder.ashr, "ashrtmp")

    def dot__rsub__(self, y, x):
        return self.arithmetic(x, y, self.ir_builder.sub, "subtmp")

    def dot__rtruediv__(self, y, x):
        if x.type == "bool":
            converted_x = self.ir_builder.select(x.value, self.ir_const(1.0), self.ir_const(0.0))
        elif x.type == "int":
            converted_x = self.ir_builder.sitofp(x.value, self.function_builder.get_ir_type("float"))
        elif x.type == "float":
            converted_x = x.value
        else:
            raise CanNotInline()
        converted_y = self.ir_builder.sitofp(y.value, self.function_builder.get_ir_type("float"))
        result = self.ir_builder.fdiv(converted_x, converted_y, naem = "truedivtmp")
        return self.primitive("float", result)

    def dot__sizeof__(self):
        return self.ir_const(8)

    def dot__str__(self, x):
        aggie_str_fromint = self.native_invoker.aggie_str_fromint
        ptr = self.function_builder.memory_manager.allocate_slot("str")
        aggie_str_fromint(self.function_builder, x.value, self.ir_const(10), ptr.value)
        return ptr

    def dot__sub__(self, x, y):
        return self.arithmetic(x, y, self.ir_builder.sub, "subtmp")

    def dot__truediv__(self, x, y):
        converted_x = self.ir_builder.sitofp(x.value, self.function_builder.get_ir_type("float"))
        if y.type == "float":
            converted_y = y.value
        elif y.type == "bool":
            converted_y = self.ir_builder.select(y.value, self.ir_const(1.0), self.ir_const(0.0))
        elif y.type == "int":
            converted_y = self.ir_builder.sitofp(y.value, self.function_builder.get_ir_type("float"))
        else:
            raise CanNotInline()
        result = self.ir_builder.fdiv(converted_x, converted_y, name = "truedivtmp")
        return self.primitive("float", result)

    def dot__xor__(self, x, y):
        return self.arithmetic(x, y, self.ir_builder.xor, "xortmp")
