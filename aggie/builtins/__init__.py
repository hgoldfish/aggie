import llvmlite.ir as ir

from aggie.native.typedef import aggie_int, aggie_float, aggie_str_raw, aggie_bytes_raw
from .bool_type import BoolType
from .bytes_type import BytesType
from .float_type import FloatType
from .integer_type import IntegerType
from .string_type import StringType
from .functions import Functions

from .utils import CanNotInline


class BuiltinsBuilder:
    def __init__(self, compiler):
        self.compiler = compiler
        self.function_builder = None

        self.functions = {}
        self.sub_builders = []
        self.add_symbols()

    def set_function_builder(self, function_builder):
        self.function_builder = function_builder
        for sub_builder in self.sub_builders:
            sub_builder.set_function_builder(function_builder)

    def add_symbols(self):
        int_type = self.compiler.create_type("int", aggie_int)
        float_type = self.compiler.create_type("float", aggie_float)
        bool_type = self.compiler.create_type("bool", ir.IntType(1))
        str_type = self.compiler.create_type("str", aggie_str_raw)
        bytes_type = self.compiler.create_type("bytes", aggie_bytes_raw)

        slice_type = self.compiler.create_type("slice", ir_type = None)
        slice_type.add_field("start", "int")
        slice_type.add_field("end", "int")
        slice_type.add_field("step", "int")
        slice_type.make_ir_type(self.compiler)

        for type_name, aggie_type, sub_builder in (
            ("int", int_type, IntegerType()),
            ("float", float_type, FloatType()),
            ("bool", bool_type, BoolType()),
            ("str", str_type, StringType()),
            ("bytes", bytes_type, BytesType()),
        ):
            self.sub_builders.append(sub_builder)
            for attr_name in dir(sub_builder):
                if attr_name.startswith("dot__"):
                    # used for magic method, like dot__getitem__()
                    # however, if implement _get_user(), the method is rewrote to dot___get_user(), three underscope...
                    # through it is very ugly, but fortunely, there is few native method like that.
                    function_name = (type_name + attr_name).replace("dot", ".")
                elif attr_name.startswith("dot_"):  # used for common method, like dot_get_user()
                    function_name = (type_name + attr_name).replace("dot_", ".")
                else:
                    continue
                aggie_type.add_method(function_name, None)
                self.functions[function_name] = getattr(sub_builder, attr_name)
        function_sub_builder = Functions()
        self.sub_builders.append(function_sub_builder)
        for attr_name in dir(function_sub_builder):
            if attr_name.startswith("dot_"):
                function_name = attr_name.replace("dot_", "")
                self.functions[function_name] = getattr(function_sub_builder, attr_name)

    def try_inline(self, function_name, *args):
        assert self.function_builder is not None
        try:
            function = self.functions[function_name]
        except KeyError:
            raise CanNotInline()
        try:
            return function(*args)
        except ValueError:
            raise CanNotInline()

    def is_primitive_type(self, type_name):
        return type_name in ("int", "float", "bool", "slice")


