from llvmlite import ir

from aggie.compiler.memory import NoneValue
from aggie.utils import CodegenError
from .utils import CanNotInline, SubBuilder, ComparableType


class StringType(ComparableType, SubBuilder):
    def dot__copy__(self, x, y):
        aggie_str_copy = self.native_invoker.aggie_str_copy
        aggie_str_copy(self.function_builder, x.value, y.value)
        self.try_free_temporary([y])
        return self.none()

    def dot__del__(self, x):
        aggie_str_del = self.native_invoker.aggie_str_del
        aggie_str_del(self.function_builder, x.value)
        return self.none()

    def dot__len__(self, x):
        aggie_str_len = self.native_invoker.aggie_str_len
        result = aggie_str_len(self.function_builder, x.value)
        self.try_free_temporary([x])
        return self.primitive("int", result)

    def dot__str__(self, x):
        return x

    def dot__int__(self, x):
        aggie_str_toint = self.native_invoker.aggie_str_toint
        ok_ptr = self.bool_to_charptr(name = "ok_ptr")
        result = aggie_str_toint(self.function_builder, x.value, self.ir_const(10), ok_ptr, name = "str.toint")
        ok = self.charptr_to_bool(ok_ptr, name = "ok")
        #TODO 这里应该抛出异常才对。
        i = self.ir_builder.select(ok, result, self.ir_const(0))
        self.try_free_temporary([x])
        return self.primitive("int", i)

    def dot__float__(self, x):
        aggie_str_tofloat = self.native_invoker.aggie_str_tofloat
        ok_ptr = self.bool_to_charptr(name = "ok_ptr")
        result = aggie_str_tofloat(self.function_builder, x.value, ok_ptr, name = "str.tofloat")
        ok = self.charptr_to_bool(ok_ptr, name = "ok")
        #TODO 这里应该抛出异常才对。
        f = self.ir_builder.select(ok, result, self.ir_const(0.0))
        self.try_free_temporary([x])
        return self.primitive("float", f)

    def dot__bool__(self, x):
        aggie_str_tobool = self.native_invoker.aggie_str_tobool
        result = aggie_str_tobool(self.function_builder, x.value)
        b = self.char_to_bool(result, name = "str.tobool")
        self.try_free_temporary([x])
        return self.primitive("bool", b)

    def dot__add__(self, x, y):
        if x.type != "str" or y.type != "str":
            raise CodegenError("str can only concat with another str, not {}".format(y.type))
        result_slot = self.function_builder.memory_manager.allocate_slot("str")
        aggie_str_concat = self.native_invoker.aggie_str_concat
        aggie_str_concat(self.function_builder, x.value, y.value, result_slot.value)
        self.try_free_temporary([x, y])
        return result_slot

    def dot__contains__(self, x, y):
        if x.type != "str" or y.type != "str":
            raise CodegenError("contains operation of str require str, not {}".format(y.type))
        aggie_str_contains = self.native_invoker.aggie_str_contains
        bool_result = aggie_str_contains(self.function_builder, x.value, y.value)
        b = self.ir_builder.icmp_signed("!=", bool_result, self.ir_const(0), name = "booltmp")
        self.try_free_temporary([x, y])
        return self.primitive("bool", b)

    def rich_compare(self, x, y, operator, name):
        if x.type != "str" or y.type != "str":
            raise CodegenError("str can only compare to another str, but not {}".format(y.type))
        aggie_str_compare = self.native_invoker.aggie_str_compare
        compare_result = aggie_str_compare(self.function_builder, x.value, y.value)
        b = self.ir_builder.icmp_signed(operator, compare_result, self.ir_const(0), name = name)
        self.try_free_temporary([x, y])
        return "bool",

    def dot__getitem__(self, x, y):
        if y.type == "int":
            ptr_char = self.function_builder.memory_manager.allocate_slot("str")
            aggie_str_at = self.native_invoker.aggie_str_at
            aggie_str_at(self.function_builder, x.value, y.value, ptr_char)
            self.try_free_temporary([x])
            return ptr_char
        elif y.type == "slice":
            ptr_substr = self.function_builder.memory_manager.allocate_slot("str")
            aggie_str_mid = self.native_invoker.aggie_str_mid
            start = self.function_builder.get_attribute(y, "start")
            end = self.function_builder.get_attribute(y, "end")
            step = self.function_builder.get_attribute(y, "step")
            aggie_str_mid(self.function_builder, x.value, start.value, end.value, step.value, ptr_substr)
            self.try_free_temporary([x, y])
            return ptr_substr
        else:
            raise CodegenError("str indices require int or slice, but not {}".format(y.type))

    def dot__hash__(self, x):
        aggie_str_hash = self.native_invoker.aggie_str_hash
        result = aggie_str_hash(self.function_builder, x.value, self.ir_const(0))
        self.try_free_temporary([x])
        return self.primitive("int", result)

    def dot__mul__(self, x, y):
        if y.type != "int":
            raise CodegenError("duplicate str require an integer times, but given {}.".format(y.type))
        aggie_str_duplicate = self.native_invoker.aggie_str_duplicate
        ptr_result = self.function_builder.memory_manager.allocate_slot("str")
        aggie_str_duplicate(self.function_builder, x.value, y.value, ptr_result.value)
        self.try_free_temporary([x, y])
        return ptr_result

    def dot__repr__(self, x):
        pass

    def dot_capitalize(self, x):
        pass

    def dot_casefold(self, x):
        pass

    def dot_center(self, x):
        pass

    def dot_count(self, x, y):
        if x.type != "str" or y.type != "str":
            raise CodegenError("str.count() require a str argument, but given {}".format(y.type))
        aggie_str_count = self.native_invoker.aggie_str_count
        result = aggie_str_count(self.function_builder, x.value, y.value)
        self.try_free_temporary([x, y])
        return self.primitive("int", result)

    def dot_encode(self, x):
        pass

    def dot_endswith(self, x, y):
        if x.type != "str" or y.type != "str":
            raise CodegenError("str.endswith() require a str argument, but given {}.".format(y.type))

        aggie_str_endswith = self.native_invoker.aggie_str_endswith
        result = aggie_str_endswith(self.function_builder, x.value, y.value)
        b = self.char_to_bool(result, name = "str.endswith")
        self.try_free_temporary([x, y])
        return self.primitive("bool", b)

    def dot_expandtabs(self, x):
        pass

    def dot_find(self, x):
        pass

    def dot_format(self, x, y):
        pass

    def dot_format_map(self, x, y):
        pass

    def dot_index(self, x, y):
        pass

    def dot_isalnum(self, x):
        pass

    def dot_isalpha(self, x):
        pass

    def dot_isdecimal(self, x):
        pass

    def dot_isdigit(self, x):
        pass

    def dot_isidentifier(self, x):
        pass

    def dot_islower(self, x):
        pass

    def dot_isnumeric(self, x):
        pass

    def dot_isprintable(self, x):
        pass

    def dot_isspace(self, x):
        pass

    def dot_istitle(self, x):
        pass

    def dot_isupper(self, x):
        pass

    def dot_join(self, x, y):
        raise CanNotInline()

    def dot_ljust(self, x, y):
        pass

    def dot_lower(self, x):
        pass

    def dot_lstrip(self, x):
        pass

    def dot_maketrans(self, x, y):
        pass

    def dot_partition(self, x, y):
        pass

    def dot_replace(self, x, y):
        pass

    def dot_rfind(self, x, y):
        pass

    def dot_rindex(self, x, y):
        pass

    def dot_rjust(self, x, y):
        pass

    def dot_rpartition(self, x, y):
        pass

    def dot_rsplit(self, x, y):
        pass

    def dot_rstrip(self, x):
        pass

    def dot_split(self, x):
        raise CanNotInline()

    def dot_splitlines(self, x):
        pass

    def dot_startswith(self, x, y):
        if x.type != "str" or y.type != "str":
            raise CodegenError("str.startswith() require a str argument, but given {}.".format(y.type))

        aggie_str_startswith = self.native_invoker.aggie_str_startswith
        result = aggie_str_startswith(self.function_builder, x.value, y.value)
        b = self.char_to_bool(result, name = "str.startswith")
        self.try_free_temporary([x, y])
        return self.primitive("bool", b)

    def dot_strip(self, x):
        pass

    def dot_swapcase(self, x):
        pass

    def dot_title(self, x):
        pass

    def dot_translate(self, x, y):
        pass

    def dot_upper(self, x):
        pass

    def dot_zfill(self, x, y):
        pass






