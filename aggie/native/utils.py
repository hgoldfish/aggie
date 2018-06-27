import llvmlite.ir as ir

from aggie.native.typedef import aggie_bool
from aggie.utils import CodegenError, Safety


class CanNotInvoke(Exception):
    pass


class NativeFunction:
    def __init__(self, name, rtype, *arguments):
        self.name = name
        self.rtype = rtype
        self.arguments = arguments
        self.safe = Safety.ThreadSafe
        self.f = None

    def generator_ir_function(self, ir_module):
        ft = ir.FunctionType(self.rtype, self.arguments)
        self.f = ir.Function(ir_module, ft, self.name)

    def __call__(self, function_compiler, *args):
        ir_builder = function_compiler.ir_builder
        if len(args) != len(self.arguments):
            raise CodegenError("native function call `{}` called without match arguments. ")

        arg_values = []
        for expr_value, expected_arg_native_type in zip(args, self.arguments):
            if expected_arg_native_type is aggie_bool:
                v = ir_builder.zext(expr_value, aggie_bool)
                arg_values.append(v)
            else:
                arg_values.append(expr_value)

        if not self.f:
            self.generator_ir_function(function_compiler.compiler.ir_module)
        return ir_builder.call(self.f, arg_values, name = "{}.rvalue".format(self.name))

    @staticmethod
    def from_table(l):
        d = {}
        for desc in l:
            name = desc[0]
            rtype = desc[1]
            args = desc[2:]
            native_function = NativeFunction(name, rtype, *args)
            d[name] = native_function
        return d
