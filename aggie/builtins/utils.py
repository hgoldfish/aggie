import llvmlite.ir as ir

from aggie.compiler.memory import PrimitiveValue, NoneValue, Slot
from aggie.native.typedef import aggie_bool


class CanNotInline(Exception):
    pass


class SubBuilder:
    def __init__(self):
        # some objects heavily using for inlining builtin objects calls.
        self.function_builder = None
        self.compiler = None
        self.ir_builder = None
        self.module = None
        self.native_invoker = None

    def set_function_builder(self, function_builder):
        # function is called before sub builder is used to inline functions.
        # we just copy some objects from function_builder, shorten our code.
        self.function_builder = function_builder
        if function_builder:
            self.compiler = function_builder.compiler
            self.ir_builder = function_builder.ir_builder
            self.module = function_builder.module
            self.native_invoker = self.function_builder.compiler.native_invoker
        else:
            self.compiler = None
            self.ir_builder = None
            self.module = None
            self.native_invoker = None

    def bool_to_charptr(self, bool_b = None, name = "wrapbool.ptr"):
        # we define `bool` is a IntType(1), but the C api can not accept this.
        # so this function allocate a new IntType(8) slot to wrap bool value.
        charptr_slot = self.function_builder.memory_manager.allocate_slot(aggie_bool, with_ref = False)
        if bool_b is not None:
            self.ir_builder.store(charptr_slot.value, self.ir_builder.sext(bool_b, aggie_bool))
        return charptr_slot

    def charptr_to_bool(self, charptr_slot, name = "wrapbool.bool"):
        char_b = self.ir_builder.load(charptr_slot.value, name = "wrapbool.char")
        bool_b = self.ir_builder.icmp_signed("!=", char_b, aggie_bool(0), name = name)
        return bool_b

    def char_to_bool(self, char_b, name = "wrapbool.bool"):
        bool_b = self.ir_builder.icmp_signed("!=", char_b, aggie_bool(0), name = name)
        return bool_b

    def ir_const(self, o):
        return self.function_builder.ir_const(o)

    def primitive(self, type_name: str, value: ir.Value) -> PrimitiveValue:
        return self.function_builder.primitive(type_name, value)

    def none(self):
        return NoneValue()

    def allocate_slot(self, slot_type: (str, ir.Type), with_ref = True, init_callback = None):
        return self.function_builder.memory_manager.allocate_slot(slot_type, with_ref, init_callback)

    def try_free_temporary(self, values: list) -> bool: # list[Value]
        return self.function_builder.memory_manager.try_free_temporary(values)


class ComparableType:
    def rich_compare(self, x, y, operator, name):
        raise NotImplementedError()

    def dot__eq__(self, x, y):
        return self.rich_compare(x, y, "==", "eqtmp")

    def dot__ge__(self, x, y):
        return self.rich_compare(x, y, ">=", "getmp")

    def dot__gt__(self, x, y):
        return self.rich_compare(x, y, ">", "gttmp")

    def dot__le__(self, x, y):
        return self.rich_compare(x, y, "<=", "letmp")

    def dot__lt__(self, x, y):
        return self.rich_compare(x, y, "<", "lttmp")

    def dot__ne__(self, x, y):
        return self.rich_compare(x, y, "!=", "netmp")
