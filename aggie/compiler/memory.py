from collections import OrderedDict

import llvmlite.ir as ir

from aggie.utils import CodegenError


class Value:
    type = ""  # type qname
    ir_type = ir.VoidType()
    value = None  # built by builder, like builder.alloca() or builder.phi()

    def __init__(self, type: str, ir_type: ir.Type):
        self.type = type
        self.ir_type = ir_type

    def __bool__(self):
        return self.type != ""

    def incref(self, function_builder):
        return False

    def decref(self, function_builder):
        return False


class RefMixin:
    ref = None

    def incref(self, function_builder):
        if not self.ref:
            return False

        ir_builder = function_builder.ir_builder

        # check invalid pointer
        i = ir_builder.ptrtoint(self.ref, function_builder.compiler.get_ir_type("int"))
        is_null_pointer = ir_builder.icmp_signed("!=", i, function_builder.ir_const(0))

        incref_block = ir_builder.append_basic_block("incref.{}".format(self.type))
        done_block = ir_builder.append_basic_block(ir_builder.block.name)

        ir_builder.cbranch(is_null_pointer, done_block, incref_block)

        ir_builder.position_at_end(incref_block)
        old_ref_value = ir_builder.load(self.ref)
        new_ref_value = ir_builder.add(old_ref_value, MemoryManager.ReferenceCountIrType(1))
        ir_builder.store(self.ref, new_ref_value)

        ir_builder.position_at_end(done_block)
        function_builder.memory_manager.branch_version(done_block)
        return True

    def decref(self, function_builder):
        if not self.ref:
            return False

        ir_builder = function_builder.ir_builder

        i = ir_builder.ptrtoint(self.ref, function_builder.compiler.get_ir_type("int"))
        is_null_pointer = ir_builder.icmp_signed("!=",i, function_builder.ir_const(0))

        decref_block = ir_builder.append_basic_block("decref.{}".format(self.type))
        desctructor_block = ir_builder.append_basic_block("desctructor.{}".format(self.type))
        done_block = ir_builder.append_basic_block(ir_builder.block.name)

        ir_builder.cbranch(is_null_pointer, done_block, decref_block)

        old_ref_value = ir_builder.load(self.ref)
        new_ref_value = ir_builder.sub(old_ref_value, MemoryManager.ReferenceCountIrType(1))
        ir_builder.store(self.ref, new_ref_value)
        iszero = ir_builder.icmp_signed("<=", new_ref_value, MemoryManager.ReferenceCountIrType(0))
        ir_builder.cbranch(iszero, desctructor_block, done_block)

        ir_builder.position_at_end(desctructor_block)
        self.delete(function_builder)
        ir_builder.branch(done_block)

        ir_builder.position_at_end(done_block)
        function_builder.memory_manager.branch_version(done_block)

        return True

    def delete(self, function_builder):
        if not self.type:
            raise CodegenError("Value.delete() is called without being managed by memory manager.")
        function_builder.make_call("{}.__del__".format(self.type), self)


class PrimitiveValue(Value):
    pass


class NoneValue(PrimitiveValue):
    def __init__(self):
        super(NoneValue, self).__init__("None", ir.VoidType())

    def incref(self, function_builder):
        raise CodegenError("None is not supported by Aggie language.")

    def decref(self, function_builder):
        raise CodegenError("None is not supported by Aggie language.")


class Slot(RefMixin, Value):
    # used for local objects, all primitive objects or complext objects used as parameters or return values.
    is_tmp = True

    def __init__(self, type: str, ir_type: ir.Type, is_tmp: bool):
        super().__init__(type, ir_type)
        self.is_tmp = is_tmp

    def incref(self, function_builder):
        self.is_tmp = False
        return super(Slot, self).incref(function_builder)

    def decref(self, function_builder):
        if self.is_tmp:
            return False
        return super(Slot, self).decref(function_builder)


class Phi(RefMixin, Value):
    # used for local named variables
    pass


class Variables(OrderedDict):
    block = None


class MemoryManager:
    ReferenceCountIrType = ir.IntType(16)
    MaxReferenceCount = ReferenceCountIrType(0x7fff)
    InvalidRefenceCount = ReferenceCountIrType(0x3fff)

    def __init__(self, function_builder):
        self.function_builder = function_builder
        self.slots = []
        self.variables = Variables()

    def allocate_slot(self, slot_type: (str, ir.Type), with_ref = True, init_callback = None):
        slot_name = "slot_" + str(len(self.slots))
        ref_name = "ref_" + str(len(self.slots))

        if isinstance(slot_type, str):
            slot = Slot(slot_type, self.function_builder.compiler.get_ir_type(slot_type), is_tmp = True)
        else:
            if with_ref:
                raise CodegenError("slot with type {} is not managed by memory manager, must set with_ref = False.".format(slot_type))
            slot = Slot("", slot_type, is_tmp = True)

        ir_builder = self.function_builder.ir_builder

        current_block = ir_builder.block
        ir_builder.position_at_end(self.function_builder.vars_block)

        slot.value = ir_builder.alloca(slot.ir_type, name = slot_name)

        if with_ref:
            slot.ref = ir_builder.alloca(MemoryManager.ReferenceCountIrType, name = ref_name)
        else:
            slot.ref = None

        if init_callback:
            try:
                init_callback(slot)
            except:
                raise CodegenError("call init_callback failed while allocating slot.")

        ir_builder.position_at_end(current_block)
        self.slots.append(slot)
        return slot

    def allocate_invalid_ref(self):
        pointer_type = self.ReferenceCountIrType.as_pointer()
        return pointer_type(0)

    def free_slots(self):
        for slot in reversed(self.slots):
            if not slot.type:  # not managed by memory manager.
                continue
            if not slot.ref:
                continue
            if slot.is_tmp:  # temporary slot is freed immedially after building statments.
                continue
            ir_builder = self.function_builder.ir_builder
            current_block = ir_builder.block

            desctructor_block = ir_builder.append_basic_block("desctructor.{}".format(slot.type))
            done_block = ir_builder.append_basic_block(current_block.name)

            ref_value = ir_builder.load(slot.ref)
            condition1 = ir_builder.icmp_signed(">", ref_value, MemoryManager.ReferenceCountIrType(0))
            # FIXME how to detect invalid ref count?
            condition2 = ir_builder.icmp_signed("<", ref_value, MemoryManager.ReferenceCountIrType(0x0fff))
            valid_ref = ir_builder.and_(condition1, condition2)
            ir_builder.cbranch(valid_ref, desctructor_block, done_block)

            ir_builder.position_at_end(desctructor_block)
            slot.delete(self.function_builder)
            ir_builder.branch(done_block)

            ir_builder.position_at_end(done_block)

    def get_variable(self, name: str, version: Variables = None):
        if version is None:
            version = self.variables
        return version.get(name)

    def assign_variable(self, name: str, value: Value, version: Variables = None):
        if version is None:
            version = self.variables
        old_value = version.get(name)
        if old_value:
            if old_value.type != value.type:
                raise CodegenError("can not reassign `{}` from `{}` type to `{}` type.".format(name, old_value.type, value.type))
            old_value.decref(self.function_builder)
        version[name] = value
        value.incref(self.function_builder)

    def delete_variable(self, name: str, version: Variables = None):
        if version is None:
            version = self.variables

        old_value = version.get(name)
        if old_value:
            old_value.decref(self.function_builder)
        else:
            raise CodegenError("NameError: name '{}' is not defined.".format(name))

    def copy_version(self, old_version: Variables = None):
        if old_version is None:
            old_version = self.variables
        return old_version.copy()

    def branch_version(self, block: ir.Block) -> Variables:
        new_version = self.variables.copy()
        new_version.block = block
        self.variables = new_version
        return new_version

    def merge_versions(self, old_versions, new_version = None):
        if new_version is None:
            new_version = Variables()
            no_new_value_flag = False
        else:
            no_new_value_flag = True
        if not old_versions:
            return new_version

        # find a common names and their types
        name_and_types = list()
        for variable_name in (new_version.keys() if no_new_value_flag else old_versions[0].keys()):
            variable_type = ""

            for old_version in old_versions:
                if variable_name not in old_version:
                    variable_type = ""
                    break
                old_value = old_version[variable_name]
                if variable_type and variable_type != old_value.type:
                    raise CodegenError("{} is redefined to type %s, must be %s".format(variable_name, old_value.type, variable_type))
                variable_type = old_value.type

            if variable_type:
                name_and_types.append((variable_name, variable_type))

        for old_version in old_versions:
            for variable_name, variable_type in name_and_types:
                old_value = old_version.get(variable_name)
                with_ref = isinstance(old_value, Slot) or (isinstance(old_value, Phi) and old_value.ref is not None)
                if variable_name not in new_version:
                    if no_new_value_flag:
                        raise CodegenError("{} is not initialized in all branches.".format(variable_name))
                    else:
                        new_value = Phi(variable_type, old_value.ir_type)
                        new_value.value = self.function_builder.ir_builder.phi(old_value.ir_type)
                        if with_ref:
                            new_value.ref = self.function_builder.ir_builder.phi(MemoryManager.ReferenceCountIrType)
                        new_version[variable_name] = new_value
                else:
                    new_value = new_version[variable_name]
                new_value.value.add_incoming(old_value.value, old_version.block)
                if with_ref:
                    if not new_value.ref:
                        raise CodegenError("refcount of {} is not initialized in all branches.".format(variable_name))
                    else:
                        if old_value.ref:
                            new_value.ref.add_incoming(old_value.ref, old_value.block)
                        else:
                            new_value.ref.add_incoming(self.allocate_invalid_ref(), old_value.block)
                else:
                    if new_value.ref:
                        raise CodegenError("newvalue.ref phi of {} is initialized unexpected.".format(variable_name))
        return new_version

    def try_free_temporary(self, values: list) -> bool: # list[Value]
        found = False
        for value in values:
            if type(value) is Slot and value.is_tmp:
                value.delete(self.function_builder)
                found = True
        return found
