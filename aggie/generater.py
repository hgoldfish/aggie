import os
import llvmlite.binding as llvm
from tempfile import NamedTemporaryFile
from aggie.compiler import Compiler

c_stub = """
void __aggie__main__();

int main(int argc, char **argv, char **env) {
    __aggie__main__();
    return 0;
}

"""


class Generater:
    def __init__(self):
        self.compiler = Compiler()

        llvm.initialize()
        llvm.initialize_native_target()
        llvm.initialize_native_asmprinter()

        self.target = llvm.Target.from_default_triple()

    def generate(self, input_filepath, output_filepath, optimize = 0):
        module_name = self.compiler.compile_file(input_filepath)
        self.compiler.bootstrap(module_name)

        target_machine = self.target.create_target_machine(codemodel = 'small')

        f = self.compiler.ir_module.globals["{}.__compile__".format(module_name)]
        #print(f.basic_blocks[1])

        ir_code = str(self.compiler.ir_module)


        llvmmod = llvm.parse_assembly(ir_code)

        if optimize:
            pmb = llvm.create_pass_manager_builder()
            pmb.opt_level = optimize
            pm = llvm.create_module_pass_manager()
            pmb.populate(pm)
            pm.run(llvmmod)
        print(str(llvmmod))
        obj_code = target_machine.emit_object(llvmmod)
        #
        # with NamedTemporaryFile("w", encoding = "utf-8", suffix = ".c") as aggie_c, \
        #         NamedTemporaryFile("wb", suffix = ".o") as object_file:
        #     aggie_c.write(c_stub)
        #     aggie_c.flush()
        #     object_file.write(obj_code)
        #     object_file.flush()
        #     command = "gcc -o {} {} {}".format(output_filepath, aggie_c.name, object_file.name)
        #     print(command)
        #     os.system(command)

        rtlib = os.path.join(os.path.dirname(__file__), "runtime/release/libaggiert.a")

        with NamedTemporaryFile("wb", suffix = ".o") as object_file:
            object_file.write(obj_code)
            object_file.flush()
            command = "g++ -lQt5Core -fPIC -o {output} {input} {rtlib} ".format(
                output = output_filepath,
                input = object_file.name,
                rtlib = rtlib,
            )
            print(command)
            os.system(command)
