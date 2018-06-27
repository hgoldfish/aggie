import llvmlite.ir as ir
from aggie.ast import FunctionDefinationStatement
from aggie.utils import CodegenError


class Function:
    ast = None

    def __init__(self, ast: FunctionDefinationStatement):
        self.ast = ast

    @property
    def is_native(self):
        return self.ast is None

    @property
    def name(self):
        if self.ast:
            return self.ast.name
        else:
            return ""

    @property
    def qname(self):
        if self.ast:
            return self.ast.qname
        else:
            return ""

    def has_child(self, other_function):
        return other_function.ast.upper is self.ast


class Module:
    name = ""
    functions = {}
    types = {}
    init_function = None

    def __init__(self, name, init_function):
        self.name = name
        self.functions = {}
        self.types = {}
        self.init_function = init_function


class Field:
    type = ""
    name = ""

    def __init__(self, name, type):
        self.name = name
        self.type = type


class Type:
    id = 0
    name = ""
    base = None
    fields = []
    methods = {}

    def __init__(self, name, base = None):
        self.id = Type._next_type_id
        Type._next_type_id += 1
        self.name = name
        self.base = base
        self.fields = []
        self.methods = {}
        if base:
            self.fields.extend(base.fields)
        self._ir_type = None

    def add_field(self, name: str, type_: type("Type")) -> bool:
        new_field = Field(name, type_)
        for old_field in self.fields:
            if old_field.name == name:
                return False
        self.fields.append(new_field)
        return True

    def add_method(self, name: str, method: (FunctionDefinationStatement, Function)) -> bool:
        if name in self.methods:
            return False
        if type(method) is FunctionDefinationStatement:
            f = Function(method)
        else:
            f = method
        self.methods[name] = f
        return True

    def get_method(self, name: str):
        t = self
        while t is not None:
            if name in t.methods:
                return t[name]
            else:
                t = t.base
        return None

    def get_method_qname(self, name: str) -> str:
        t = self
        while t is not None:
            if name in t.methods:
                return t.name + "." + name
            else:
                t = t.base
        return ""

    def make_ir_type(self, compiler):
        if not self.fields:
            raise CodegenError("type {} has no defined field.".format(self.name))
        else:
            elems = []
            for field in self.fields:
                try:
                    field_type = compiler.types[field.type]
                except KeyError:
                    raise CodegenError("unknown field type: {}".format(field.type))
                elems.append(field_type.ir_type)
            self.ir_type = ir.LiteralStructType(elems)

    @property
    def ir_type(self):
        if not self._ir_type:
            raise CodegenError("use ir_type of {} before make_ir_type() called.".format(self.name))
        return self._ir_type

    @ir_type.setter
    def ir_type(self, ir_type):
        if self._ir_type:
            raise CodegenError("set ir_type of {} twice.".format(self.name))
        self._ir_type = ir_type

    _next_type_id = 1


class TemplateType:
    name = ""
