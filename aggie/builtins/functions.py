from aggie.builtins.utils import SubBuilder
from aggie.compiler.memory import Slot
from aggie.utils import CodegenError
from aggie.utils import FunctionNotFound


class Functions(SubBuilder):
    def dot_print(self, x):
        if x.type != "str":
            x = self.function_builder.cast(x, "str")
        converted_value = x.value

        line = self.function_builder.memory_manager.allocate_slot("str")
        sep = self.function_builder.build_string("\n")
        aggie_str_concat = self.native_invoker.aggie_str_concat
        aggie_str_concat(self.function_builder, converted_value, sep.value, line.value)

        aggie_print = self.native_invoker.aggie_print
        aggie_print(self.function_builder, line.value)

        self.try_free_temporary([x, line])
        return self.none()

    def dot_int(self, x):
        if x.type == "int":
            return x
        try:
            return self.function_builder.make_call(x.type + ".__int__", x)
        except FunctionNotFound:
            raise CodegenError("can not cast {} type to int.".format(x.type))

    def dot_float(self, x):
        if x.type == "float":
            return x
        try:
            return self.function_builder.make_call(x.type + ".__float__", x)
        except FunctionNotFound:
            raise CodegenError("can not cast {} type to float.".format(x.type))

    def dot_bool(self, x):
        if x.type == "bool":
            return x
        try:
            return self.function_builder.make_call(x.type + ".__bool__", x)
        except FunctionNotFound:
            raise CodegenError("can not cast {} type to bool.".format(x.type))

    def dot_abs(self, x):
        try:
            return self.function_builder.make_call(x.type + ".__abs__", x)
        except FunctionNotFound:
            raise CodegenError("type {} does not support abs().".format(x.type))

    def dot_str(self, x = None):
        if x is not None:
            result = self.function_builder.make_call(x.type + ".__str__", x)
            if result.type != "str":
                raise CodegenError("{}.__str__() do not return str.".format(x.type))
            return result
        else:
            return self.function_builder.build_constant("")

    def dot_len(self, x):
        try:
            return self.function_builder.make_call(x.type + ".__len__", x)
        except FunctionNotFound:
            raise CodegenError("type {} does not support len().".format(x.type))
