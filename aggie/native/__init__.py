import llvmlite.ir as ir
from .utils import CanNotInvoke, NativeFunction
from . import runtime
from . import string_type

class NativeInvoker:
    def __init__(self, compiler):
        self.compiler = compiler
        self.ir_module = compiler.ir_module
        self.functions = {}
        self.add_symbols()

    def __getattr__(self, item):
        return self.functions[item]

    def add_symbols(self):
        self.functions.update(string_type.make_native_functions())
        self.functions.update(runtime.make_native_functions())
