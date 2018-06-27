import io
import os
import llvmlite.ir as ir
from aggie.ast import DelStatement, ContinueStatement, FunctionDefinationStatement, IfStatement, WhileStatement, \
    ForStatement, BinaryExpression, VariableExpression, CallExpression, IntegerConstant, FloatConstant, TrueConstant, \
    FalseConstant, UnaryExpression, ExpressionStatement, PassStatement, ReturnStatement, BreakStatement, \
    GetAttrExpression, DictExpression, ListExpression, TupleExpression, GetItemExpression, ASTNode, Suite, \
    StringConstant, BytesConstant, SubscriptExpression
from aggie.builtins import BuiltinsBuilder, CanNotInline
from aggie.compiler.memory import MemoryManager, PrimitiveValue, Slot, NoneValue, Phi
from aggie.lexer import Lexer
from aggie.parser import COMPILE_METHOD, make_qname, Parser
from aggie.utils import CodegenError, FunctionNotFound
from aggie.native import NativeInvoker
from .bricks import Function, Module, Type


# XXX what name should I call? Compiler or Buidler.
class Compiler:
    def __init__(self):
        self.ir_module = ir.Module("aggie")
        self.ir_true = ir.Constant(ir.IntType(1), 1)
        self.ir_false = ir.Constant(ir.IntType(1), 0)

        self.functions = dict()
        self.modules = dict()
        self.types = dict()
        self.const_string_table = list()

        self.builtins_builder = BuiltinsBuilder(self)
        self.native_invoker = NativeInvoker(self)

    def compile_file(self, filepath: str) -> str:
        module_name = os.path.splitext(os.path.basename(filepath))[0]
        with io.open(filepath, "r", encoding = "utf-8") as input_file:
            lexer = Lexer(input_file)
            parser = Parser(module_name)
            module_function = parser.parse(lexer)
            self.compile(module_name, module_function)
        return module_name

    def compile(self, module_name, module_ast_function, replace = True):
        function = Function(ast = module_ast_function)
        module = Module(module_name, function)

        if module_name in self.modules:
            if replace:
                module.functions = self.modules[module_name].functions
            else:
                raise CodegenError("module {} has been defined.".format(module_name))

        module_builder = ModuleBuilder(module, self)
        module_builder.build()

        self.modules[module_name] = module

    def bootstrap(self, module_name):
        # FIXME this is a very simple libc-amd64 version, do more when porting to windows..
        ir_main_function_type = ir.FunctionType(ir.IntType(32), [])
        function = ir.Function(self.ir_module, ir_main_function_type, "main")
        entry = function.append_basic_block("entry")
        builder = ir.IRBuilder(entry)

        qname = module_name + COMPILE_METHOD
        callee = self.ir_module.globals.get(qname)
        if not callee:
            raise CodegenError("can not find main function.")

        builder.call(callee, [])
        builder.ret(ir.Constant(ir.IntType(32), 0))

    def create_type(self, name, ir_type):
        if name in self.types:
            raise CodegenError("duplicated type.")
        t = Type(name)
        if ir_type:  # if ir_type is not provided, use make_ir_type() to generate an ir_type later.
            t.ir_type = ir_type
        self.types[name] = t
        return t

    def get_ir_type(self, name):
        if name in self.types:
            return self.types[name].ir_type
        else:
            raise CodegenError("unhandled type: {}".format(name))

    def get_type(self, name):
        if name in self.types:
            return self.types[name]
        else:
            raise CodegenError("unhandled type: {}".format(name))


class ModuleBuilder:
    def __init__(self, module, compiler):
        self.module = module
        self.compiler = compiler

    def build(self):
        function_builder = FunctionBuilder(self.module.init_function, self.module, self.compiler)
        function_builder.build()


class FunctionBuilder:
    def __init__(self, function: Function, module: Module, compiler: Compiler):
        self.function = function
        self.ast_function = function.ast
        self.module = module
        self.compiler = compiler

        self.ir_module = self.compiler.ir_module
        self.ir_function = None
        self.ir_builder = None

        self.vars_block = None
        self.entry_block = None
        self.clean_block = None

        self.loop_stack = []
        self.retvalue_versions = []
        self.string_constants = {}

        # memory_manager and builtins_builder should not be used before init blocks and ir_builder.
        self.memory_manager = MemoryManager(self)
        self.builtins_builder = compiler.builtins_builder

    def make_ir_function_type(self, ast_function):
        param_types = []
        if self.builtins_builder.is_primitive_type(ast_function.rtype):
            ir_rtype = self.compiler.get_ir_type(ast_function.rtype)
        else:
            ir_rtype = ir.VoidType()
            if ast_function.rtype != "None":
                param_types.append(ir.PointerType(self.compiler.get_ir_type(ast_function.rtype)))

        for arg_name, arg_type in ast_function.args:
            if arg_type == "None":
                raise CodegenError("None is not allow for parameters: {}, {}", ast_function.name, arg_name)
            if self.builtins_builder.is_primitive_type(arg_type):
                param_types.append(self.compiler.get_ir_type(arg_type))
            else:
                param_types.append(ir.PointerType(self.compiler.get_ir_type(arg_type)))
        return ir.FunctionType(ir_rtype, param_types)

    def build(self):
        # XXX should I use a dict to track IR function type?
        ir_function_type = self.make_ir_function_type(self.ast_function)
        self.ir_function = ir.Function(self.ir_module, ir_function_type, self.ast_function.qname)
        self.function.ir_function_type = ir_function_type

        self.compiler.functions[self.ast_function.qname] = self.function

        self.vars_block = self.ir_function.append_basic_block("vars")
        self.clean_block = self.ir_function.append_basic_block("clean")
        self.entry_block = self.ir_function.append_basic_block("entry")
        self.ir_builder = ir.IRBuilder(self.entry_block)
        self.memory_manager.variables.block = self.entry_block

        old_function_builder = self.builtins_builder.function_builder
        self.builtins_builder.set_function_builder(self)

        if self.ast_function.rtype == "None":
            retvalue_slot = None
            skip_first = False
        elif self.builtins_builder.is_primitive_type(self.ast_function.rtype):
            retvalue_slot = None
            skip_first = False
        else:
            retvalue_ir_type = self.compiler.get_ir_type(self.ast_function.rtype)
            retvalue_slot = Slot(self.ast_function.rtype, retvalue_ir_type, is_tmp = False)
            retvalue_slot.value = self.ir_function.args[0]  # ir.PointerType()!
            self.ir_function.args[0].name = "retvalue"
            # retvalue_slot.ref is not need to allocate, decref() can handle this.
            skip_first = True

        for i, (arg_name, arg_type) in enumerate(self.ast_function.args):
            ir_arg = self.ir_function.args[i + int(skip_first)]
            ir_arg.name = arg_name
            arg_ir_type = self.compiler.get_ir_type(arg_type)
            if self.builtins_builder.is_primitive_type(arg_type):
                v = PrimitiveValue(arg_type, arg_ir_type)
                v.value = ir_arg
            else:
                v = Slot(arg_type, arg_ir_type, is_tmp = False)
                v.value = ir_arg
                v.ref = None
            self.memory_manager.variables[arg_name] = v

        self.build_suite(self.ast_function.suite)

        if self.ir_builder.block.terminator is None:
            self.ir_builder.branch(self.clean_block)

        # connect entry_block to clean_block and do clean works.
        self.ir_builder.position_at_end(self.clean_block)
        self.memory_manager.free_slots()
        for slot in self.string_constants.values():
            self.make_call("str.__del__", slot)
        if self.ast_function.rtype != "None" and not self.retvalue_versions:
            raise CodegenError("function must return `{}`.".format(self.ast_function.rtype))
        elif self.ast_function.rtype == "None" and self.retvalue_versions:
            raise CodegenError("function must not return anything.")
        else:
            if self.ast_function.rtype == "None":
                self.ir_builder.ret_void()
            else:
                retvalue_ir_type = self.compiler.get_ir_type(self.ast_function.rtype)
                retvalue = Phi(self.ast_function.rtype, retvalue_ir_type)
                if self.builtins_builder.is_primitive_type(self.ast_function.rtype):
                    retvalue.value = self.ir_builder.phi(retvalue_ir_type)
                else:
                    retvalue.value = self.ir_builder.phi(ir.PointerType(retvalue_ir_type))
                for value, block in self.retvalue_versions:
                    retvalue.value.add_incoming(value, block)

                if self.builtins_builder.is_primitive_type(self.ast_function.rtype):
                    if retvalue_slot is not None:
                        raise CodegenError("retvalue_slot is created but useless.")
                    self.ir_builder.ret(retvalue.value)
                else:
                    if retvalue_slot is None:
                        raise CodegenError("retvalue_slot is required.")

                    copy_function_name = self.ast_function.rtype + ".__copy__"
                    self.make_call(copy_function_name, retvalue_slot, retvalue)
                    self.ir_builder.ret_void()
        # connect vars_block and entry_block.
        self.ir_builder.position_at_end(self.vars_block)
        self.ir_builder.branch(self.entry_block)

        self.builtins_builder.set_function_builder(old_function_builder)

    def build_suite(self, suite: Suite):
        for statement in suite.statements:
            if type(statement) is ExpressionStatement:
                self.build_expression_statement(statement)
            elif type(statement) is DelStatement:
                self.build_del_statement(statement)
            elif type(statement) is PassStatement:
                pass
            elif type(statement) is ReturnStatement:
                self.build_return_statement(statement)
            elif type(statement) is BreakStatement:
                self.build_break_statement(statement)
            elif type(statement) is ContinueStatement:
                self.build_continue_statement(statement)
            elif type(statement) is FunctionDefinationStatement:
                self.build_function_statement(statement)
            elif type(statement) is IfStatement:
                self.build_if_statement(statement)
            elif type(statement) is WhileStatement:
                self.build_while_statement(statement)
            elif type(statement) is ForStatement:
                self.build_for_statement(statement)
            else:
                raise CodegenError("{} statement is not implemented!".format(type(statement)))

    def build_expression_statement(self, expression_statement):
        value = self.build_expression(expression_statement.expression)

        if not expression_statement.variable:
            self.memory_manager.try_free_temporary([value])
            return

        if value.type == "None":
            raise CodegenError("can not assign None to variable {}.".format(expression_statement.variable))
        self.memory_manager.assign_variable(expression_statement.variable, value)

    def build_del_statement(self, del_statement):
        for expression in del_statement.expressions:
            if type(expression) is GetAttrExpression:
                obj = self.build_expression(expression.target)
                if obj.type == "None":
                    raise CodegenError("AttributeError: 'NoneType' object has no attribute '{}'.".format(expression.item))
                function_name = obj.type + ".__delattr__"
                self.make_call(function_name, obj, self.build_string(expression.item))
                self.memory_manager.try_free_temporary([obj])
            elif type(expression) is GetItemExpression:
                obj = self.build_expression(expression.target)
                if obj.type == "None":
                    raise CodegenError("TypeError: 'NoneType' object does not support item deletion.")
                function_name =  obj.type + ".__delitem__"

                args = [obj]
                for arg_ast in expression.args:
                    arg = self.build_expression(arg_ast)
                    args.append(arg)
                self.make_call(function_name, *args)
                self.memory_manager.try_free_temporary(args)
            elif type(expression) is VariableExpression:
                self.memory_manager.delete_variable(expression.name)
            else:
                raise CodegenError("can not delete {}".format(type(expression)))

    def build_break_statement(self, break_statement):
        if not self.loop_stack:
            raise CodegenError("break statement can only appear in loop.")
        loop = self.loop_stack[-1]
        loop.endloop_branch_versions.append(self.memory_manager.variables)
        self.ir_builder.branch(loop.get_endloop_block)

    def build_continue_statement(self, continue_statement):
        if not self.loop_stack:
            raise CodegenError("continue statement can only appear in loop.")
        loop = self.loop_stack[-1]
        loop.condition_branch_versions.append(self.memory_manager.variables)
        self.ir_builder.branch(loop.condition_block)

    def compile_for_statement(self, for_statement):
        raise CodegenError("for statement is not supported yet.")

    def build_return_statement(self, return_statement):
        assert self.ast_function.rtype
        if return_statement.expression:
            if self.ast_function.rtype == "None":
                raise CodegenError("function {} must not return a value.".format(self.ast_function.qname))
            expr = self.build_expression(return_statement.expression)
            if self.ir_builder.block is not self.memory_manager.variables.block:
                print(self.ir_builder.block, self.memory_manager.variables.block)
                raise CodegenError("checkpoint: variables.block is not the same as self.ir_builder.block.")
            self.retvalue_versions.append([expr.value, self.ir_builder.block])
            self.ir_builder.branch(self.clean_block)
        else:
            if self.ast_function.rtype == "None":
                if self.retvalue_versions:
                    raise CodegenError("function {} must not return any value.".format(self.ast_function.qname))
                else:
                    self.ir_builder.branch(self.clean_block)
            else:
                raise CodegenError("function must return a value.")

    def build_function_statement(self, function_statement):
        # TODO support closure, and return a value, then we can bind function to named variable.
        function = Function(function_statement)
        function_builder = FunctionBuilder(function, self.module, self.compiler)
        function_builder.build()
        if self.module.init_function.has_child(function):
            self.module.functions[function_statement.qname] = function

    def build_if_statement(self, if_statement):
        if not if_statement.flow:
            raise CodegenError("if statement must have one or more than one suite.")

        orignal_block = self.ir_builder.block
        endif_block = None

        branch_versions = []
        for condition, suite in if_statement.flow:
            true_block = self.ir_builder.append_basic_block(name = orignal_block.name + ".if")
            false_block = self.ir_builder.append_basic_block(name = orignal_block.name + ".else")
            expr = self.build_expression(condition)
            converted_value = self.cast(expr, "bool")
            condition_version = self.memory_manager.variables
            self.ir_builder.cbranch(converted_value.value, true_block, false_block)

            self.ir_builder.position_at_end(true_block)
            self.memory_manager.branch_version(true_block)
            self.build_suite(suite)
            if self.ir_builder.block.terminator is None: # 可能里面又有跳转。。所以 self.builder.block 不一定是 true_block
                if endif_block is None:
                    endif_block = self.ir_builder.append_basic_block(name = orignal_block.name + ".endif")
                self.ir_builder.branch(endif_block)
                branch_versions.append(self.memory_manager.variables)

            self.ir_builder.position_at_end(false_block)
            self.memory_manager.variables = condition_version  # restore orignal version
            self.memory_manager.branch_version(false_block)

        if if_statement.otherwise:
            self.memory_manager.branch_version(self.ir_builder.block)
            self.build_suite(if_statement.otherwise)
            if self.ir_builder.block.terminator is None:
                if endif_block is None:
                    endif_block = self.ir_builder.append_basic_block(name = orignal_block.name + ".endif")
                self.ir_builder.branch(endif_block)
                branch_versions.append(self.memory_manager.variables)

        if endif_block is not None:
            if not branch_versions:
                raise CodegenError("endif block exists while branch_versions is empty.")
            self.ir_builder.position_at_end(endif_block)
            self.memory_manager.variables = self.memory_manager.merge_versions(branch_versions)
            self.memory_manager.variables.block = endif_block
        else:
            if branch_versions:
                raise CodegenError("endif block not exists while branch_versions is not empty.")

    def build_while_statement(self, while_statement):
        orignal_block = self.ir_builder.block
        if self.memory_manager.variables.block is not orignal_block:
            raise CodegenError("checkpoint: variables.block is not the same as self.ir_builder.block.")

        condition_block = self.ir_builder.append_basic_block(name = orignal_block.name + ".while")
        true_block = self.ir_builder.append_basic_block(name = orignal_block.name + ".loop")
        false_block = self.ir_builder.append_basic_block(name = orignal_block.name + ".loopelse")

        self.ir_builder.branch(condition_block)
        self.ir_builder.position_at_end(condition_block)

        condition_version = self.memory_manager.merge_versions([self.memory_manager.variables])
        condition_version.block = condition_block
        self.memory_manager.variables = condition_version

        condition_value = self.build_expression(while_statement.condition)
        converted_value = self.cast(condition_value, "bool")
        self.ir_builder.cbranch(converted_value.value, true_block, false_block)

        self.ir_builder.position_at_end(true_block)
        self.memory_manager.branch_version(true_block)

        loop = Loop(orignal_block.name)
        loop.condition_block = condition_block
        self.loop_stack.append(loop)

        self.build_suite(while_statement.suite)
        self.loop_stack.pop()
        if self.ir_builder.block.terminator is None:
            loop.condition_branch_versions.append(self.memory_manager.variables)
            self.ir_builder.branch(condition_block)

        if loop.condition_branch_versions:
            self.memory_manager.merge_versions(loop.condition_branch_versions, condition_version)

        self.ir_builder.position_at_end(false_block)
        self.memory_manager.branch_version(false_block)

        if while_statement.otherwise:
            self.build_suite(while_statement.otherwise)

        if self.ir_builder.block.terminator is None:
            loop.endloop_branch_versions.append(self.memory_manager.variables)
            self.ir_builder.branch(loop.get_endloop_block(self.ir_builder))

        if loop.endloop_block is not None:
            self.ir_builder.position_at_end(loop.endloop_block)
            if not loop.endloop_branch_versions:
                raise CodegenError("break to endloop, but forgot to adding the branch version.")
            endloop_version = self.memory_manager.merge_versions(loop.endloop_branch_versions)
            endloop_version.block = loop.endloop_block
            self.memory_manager.variables = endloop_version

    def build_expression(self, expression):
        if type(expression) is BinaryExpression:
            lhs = self.build_expression(expression.lhs)
            rhs = self.build_expression(expression.rhs)

            if expression.operator in ("and", "or"):
                # 这里的行为和 python 不太一样。python 会发生短路，而这里不会？而且 python 的 or 可以这样用：
                # None or ""，但是这里不行。。我觉得短路功能是非常有必要的。晚点再实现吧。
                converted_lhs = self.cast(lhs, "bool")
                converted_rhs = self.cast(rhs, "bool")
                if expression.operator == "and":
                    result = self.ir_builder.and_(converted_lhs.value, converted_rhs.value, name = "andtmp")
                    return self.primitive("bool", result)
                else:
                    result = self.ir_builder.or_(converted_lhs.value, converted_rhs.value, name = "ortmp")
                    return self.primitive("bool", result)
            elif expression.operator == "not in":
                contains = self.call_magic_binary_method("in", lhs, rhs)
                if contains.type != "bool":
                    raise CodegenError("operator `not in` require `{}.__contains__()` returns bool.".format(lhs.type))
                result = self.ir_builder.not_(contains.value)
                return self.primitive("bool", result)
            else:
                return self.call_magic_binary_method(expression.operator, lhs, rhs)
        elif type(expression) is UnaryExpression:
            expr = self.build_expression(expression.value)
            if expression.operator == "not":
                converted_expr = self.cast(expr, "bool")
                result = self.ir_builder.not_(converted_expr.value, name = "nottmp")
                return self.primitive("bool", result)
            else:
                return self.call_magic_unary_method(expression.operator, expr)
        elif type(expression) is VariableExpression:
            return self.memory_manager.get_variable(expression.name)
        elif type(expression) is CallExpression:
            target = expression.target
            if type(target) is GetAttrExpression:
                obj = self.build_expression(target.target)
                args = []
                for arg_ast in expression.args:
                    arg = self.build_expression(arg_ast)
                    args.append(arg)
                try:
                    function_name = obj.type + "." + target.item
                    return self.make_call(function_name, obj, *args)
                except FunctionNotFound:
                    attr = self.get_attribute(obj, target.item)
                    function_name = attr.type + ".__call__"
                    return self.make_call(function_name, attr, *args)
            elif type(target) is VariableExpression:
                # TODO use self.memory_manager.get_variable() when function builder returns FunctionType value.
                # here we just assume the function is compiled and add to module globals.
                function_name = target.name
                args = []
                for arg in expression.args:
                    arg = self.build_expression(arg)
                    args.append(arg)
                return self.make_call(function_name, *args)
            else:
                obj = self.build_expression(target.target)
                function_name = obj.type + ".__call__"
                args = []
                for arg_ast in expression.args:
                    arg = self.build_expression(arg_ast)
                    args.append(arg)
                try:
                    return self.make_call(function_name, obj, *args)
                except FunctionNotFound:
                    raise CodegenError("{} is not callable.".format(target.dump()))
        elif type(expression) is GetAttrExpression:
            obj = self.build_expression(expression.target)
            return self.get_attribute(obj, expression.item)
        elif type(expression) is GetItemExpression:
            obj = self.build_expression(expression.target)
            function_name = obj.type + ".__getitem__"
            args = []
            for arg_ast in expression.args:
                arg = self.build_expression(arg_ast)
                args.append(arg)
            return self.make_call(function_name, obj, *args)
        elif type(expression) is SubscriptExpression:
            start = self.build_expression(expression.start)
            end = self.build_expression(expression.end)
            step = self.build_expression(expression.step)
            return self.make_call("slice", start, end, step)
        elif type(expression) is StringConstant:
            return self.build_string(expression.value)
        elif type(expression) is BytesConstant:
            return self.build_bytes(expression.value)
        elif type(expression) is TupleExpression:
            raise CodegenError("tuple is not supported yet. use generic version instead.")
        elif type(expression) is ListExpression:
            raise CodegenError("list is not supported yet. use generic version instead.")
        elif type(expression) is DictExpression:
            raise CodegenError("dict is not supported yet. use generic version instead.")
        elif type(expression) is IntegerConstant:
            return self.build_constant(expression.value)
        elif type(expression) is FloatConstant:
            return self.build_constant(expression.value)
        elif type(expression) is TrueConstant:
            return self.build_constant(True)
        elif type(expression) is FalseConstant:
            return self.build_constant(False)
        else:
            raise CodegenError("unsupported expression type: {}".format(repr(expression)))

    def call_magic_binary_method(self, operator, lhs, rhs):
        magic_methods = {
            "+": "__add__",
            "-": "__sub__",
            "*": "__mul__",
            "/": "__truediv__",
            "//": "__floordiv__",
            "%": "__mod__",
            "**": "__pow__",
            "<<": "__lshift__",
            ">>": "__rshift__",
            "|": "__or__",
            "&": "__and__",
            "^": "__xor__",
            "<": "__lt__",
            "<=": "__le__",
            "==": "__eq__",
            "!=": "__ne__",
            ">": "__gt__",
            ">=": "__ge__",
            "in": "__contains__",
        }
        reversed_magic_methods = {
            "+": "__radd__",
            "-": "__rsub__",
            "*": "__rmul__",
            "/": "__rtruediv__",
            "//": "__rfloordiv__",
            "%": "__rmod__",
            "**": "__rpow__",
            "<<": "__rlshift__",
            ">>": "__rrshift__",
            "|": "__ror__",
            "&": "__rand__",
            "^": "__rxor__",
        }
        try:
            magic_function_name = magic_methods.get(operator)
            if not magic_function_name:
                raise CodegenError("unsupported operator {} for type `{}`.".format(operator, lhs.type))
            function_name = lhs.type + "." + magic_function_name
            return self.make_call(function_name, lhs, rhs)
        except FunctionNotFound:
            magic_function_name = reversed_magic_methods.get(operator)
            if not magic_function_name:
                raise CodegenError("unsupported operator {} for type `{}`.".format(operator))
            function_name = rhs.type + "." + magic_function_name
            try:
                return self.make_call(function_name, rhs, lhs)
            except:
                raise CodegenError("unsupported operator {}".format(operator))

    def call_magic_unary_method(self, operator, expr):
        magic_methods = {
            "~": "__invert__",
            "-": "__neg__",
            "+": "__pos__",
        }
        try:
            magic_function_name = magic_methods.get(operator)
            if not magic_function_name:
                raise CodegenError("unsupported operator {}".format(operator))
            function_name = expr.type + "." + magic_function_name
            return self.make_call(function_name, expr)
        except FunctionNotFound:
            raise CodegenError("unsupported operator {}".format(operator))

    def make_call(self, function_name, *args):
        try:
            return self.builtins_builder.try_inline(function_name, *args)
        except CanNotInline:
            # TODO use memory_manager to find function by name
            ast_function = self.ast_function
            callee = None
            qname = ""
            while ast_function:
                qname = make_qname(ast_function.qname, function_name)
                callee = self.module.functions.get(qname)
                if callee:
                    break
                ast_function = ast_function.upper
            if not callee:
                raise FunctionNotFound("function named {} is not found.".format(qname))

            ir_function = self.ir_module.globals.get(qname)
            if not ir_function:
                raise FunctionNotFound("function named {} is not compile yet.".format(qname))

            if len(callee.ast.args) != len(args):
                raise FunctionNotFound("function named {} require {} arguments, but provide {}.".format(len(callee.ast.args), len(args)))

            arg_values = []
            if callee.ast.rtype != "None" and not self.builtins_builder.is_primitive_type(callee.ast.rtype):
                result_value = self.memory_manager.allocate_slot(callee.ast.rtype, with_ref = True)
                arg_values.append(result_value.value)
            else:
                result_value = None

            for i, arg in enumerate(args):
                arg_name, arg_type = callee.ast.args[i]
                if arg.type != arg_type:
                    raise CodegenError("given an unmatched argument {} type {} (wanted {}) while calling {}".format(i, arg.type, arg_type, callee.name))
                arg_values.append(arg.value)
            result_type = callee.ast.rtype
            t = self.ir_builder.call(ir_function, arg_values, name = callee.name + ".rvalue")
            self.memory_manager.try_free_temporary(args)
            if result_type == "None":
                return NoneValue()
            elif self.builtins_builder.is_primitive_type(result_type):
                return self.primitive(result_type, t)
            else:
                return result_value

    def get_attribute(self, obj, attr):
        if isinstance(attr, StringConstant):
            attr_name = attr.value
        elif isinstance(attr, str):
            attr_name = attr
        else:
            raise CodegenError("get attribute from object dynamically is not supported yet.")

        t = self.compiler.get_type(obj.type)

        for i, field in enumerate(t.fields):
            if field.name == attr_name:
                field_ptr = self.ir_builder.gep(obj.value, [
                    self.ir_const(0),
                    self.ir_const(i),
                ])
                # 不太对。。取属性的话应该使用复制构造函数弄个新的值出来。。
                if self.builtins_builder.is_primitive_type(field.type):
                    field_value = self.ir_builder.load(field_ptr)
                    return self.primitive(field.type, field_value)
                else:
                    field_ir_type = self.compiler.get_ir_type(field.type)
                    field_value = Slot(field.type, field_ir_type, is_tmp = False)
                    field_value.value = field_ptr # ir.PointerType(field_ir_type)!
                    field_value.ref = None
                    return field_value
        else:
            raise CodegenError("type {} has no field named {}".format(obj.type, attr_name))

    def build_constant(self, value: (bool, int, float, str, bytes)):
        result = self.ir_const(value)
        if value is True or value is False:
            return self.primitive("bool", result)
        elif type(value) is int:
            return self.primitive("int", result)
        elif type(value) is float:
            return self.primitive("float", result)
        elif type(value) is str:
            return self.build_string(value)
        elif type(value) is bytes:
            return self.build_bytes(value)
        else:
            raise CodegenError("unknown constant: {}", repr(value))

    def build_string(self, value: str):
        if value in self.string_constants:
            return self.string_constants[value]

        b = value.encode("utf-16-le")
        # TODO 合并重复的字符串。如果可以的话，还可以合并所有的字符串给一个表里面。减少全局变量的数量。
        try:
            const_str_id = self.compiler.const_string_table.index(value)
            global_var_name = "strconst." + str(const_str_id)
            ir_global_string = self.compiler.ir_module.globals[global_var_name]
        except ValueError:
            const_str_id = len(self.compiler.const_string_table)
            self.compiler.const_string_table.append(value)
            global_var_name = "strconst." + str(const_str_id)
            ty = ir.ArrayType(ir.IntType(8), len(b))
            ir_global_string = ir.GlobalVariable(self.ir_module, ty, global_var_name)
            ir_global_string.linkage = "private"
            ir_global_string.global_constant = True
            ir_global_string.initializer = ir.Constant(ty, list(b))

        def init_string(slot):
            aggie_str_new = self.compiler.native_invoker.aggie_str_new
            data = self.ir_builder.gep(ir_global_string, [self.ir_const(0), self.ir_const(0)])
            aggie_str_new(self, data, self.ir_const(len(b)), slot.value)

        # TODO 能这样疯狂申请内存？一些常用的字符串都要事先申请放在内存里面？
        slot = self.memory_manager.allocate_slot("str", with_ref = False, init_callback = init_string)
        slot.is_tmp = False
        slot.ref = None
        self.string_constants[value] = slot
        return slot

    def build_bytes(self, value: bytes):
        return None

    def ir_const(self, value: (bool, int, float)):
        if value is True:
            return ir.Constant(ir.IntType(1), 1)
        elif value is False:
            return ir.Constant(ir.IntType(1), 0)
        elif type(value) is int:
            return ir.Constant(ir.IntType(64), value)
        elif type(value) is float:
            return ir.Constant(ir.FloatType(), value)
        else:
            raise CodegenError("unknown constant: {}", repr(value))

    def cast(self, expr, target_type):
        if expr.type == target_type:
            return expr
        try:
            target = self.make_call(target_type, expr)
            if target.type == target_type:
                return target
            else:
                raise CodegenError("{}() must return {} type.".format(target_type, target_type))
        except FunctionNotFound:
            raise CodegenError("can not cast {} to {}.".format(expr.type, target_type))

    def primitive(self, type_name: str, value: ir.Value) -> PrimitiveValue:
        ir_type = self.compiler.get_ir_type(type_name)
        primitive_value = PrimitiveValue(type_name, ir_type)
        primitive_value.value = value
        return primitive_value


class Loop:
    condition_block = None
    endloop_block = None
    condition_branch_versions = []
    endloop_branch_versions = []

    def __init__(self, name):
        self.name = name

    def get_endloop_block(self, ir_builder):
        if self.endloop_block is None:
            self.endloop_block = ir_builder.append_basic_block(name = self.name + ".endwhile")
        return self.endloop_block
