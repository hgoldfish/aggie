from aggie.builtins.utils import SubBuilder
from aggie.compiler.memory import Phi


class BoolType(SubBuilder):
    def dot__int__(self, x):
        assert x.type == "bool"
        result = self.ir_builder.select(x.value, self.ir_const(1), self.ir_const(0))
        return self.primitive("int", result)

    def dot__float__(self, x):
        assert x.type == "bool"
        result = self.ir_builder.select(x.value, self.ir_const(1.0), self.ir_const(0.0))
        return self.primitive("float", result)

    def dot__str__(self, r, x):
        assert x.type == "bool"
        current_block = self.ir_builder.block
        true_block = self.ir_builder.append_basic_block(name = "booltostr.true")
        false_block = self.ir_builder.append_basic_block(name = "booltostr.false")
        done_block = self.ir_builder.append_basic_block(name = current_block.name)

        self.ir_builder.cbranch(x.value, true_block, false_block)

        self.ir_builder.position_at_end(true_block)
        true_slot = self.function_builder.build_string("True")
        self.ir_builder.branch(done_block)

        self.ir_builder.position_at_end(false_block)
        false_slot = self.function_builder.build_string("False")
        self.ir_builder.branch(done_block)

        self.ir_builder.position_at_end(done_block)
        self.function_builder.memory_manager.branch_version(done_block)

        result = Phi(true_slot.type, true_slot.ir_type)
        result.value = self.ir_builder.phi(true_slot.ir_type)
        result.value.add_incoming(true_slot.value, true_block)
        result.value.add_incoming(false_slot.value, false_block)
        # nothing to do for result.ref
        return result
