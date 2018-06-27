import llvmlite.ir as ir

from . import __bulid__


class _Ptr(ir.PointerType):
    pass


class Ptr:
    def __getitem__(self, item):
        return _Ptr(item)


class Dirty:
    def __getitem__(self, item):
        item.is_dirty = True
        return item


def is_ptr(ptr):
    return isinstance(ptr, _Ptr)


def is_dirty(type):
    return getattr(type, "is_dirty", False)


ptr = Ptr()
dirty = Dirty()

aggie_int = ir.IntType(64)
aggie_bool = ir.IntType(8)
aggie_float = ir.DoubleType()
aggie_void = ir.VoidType()

aggie_object = ir.PointerType(ir.IntType(8))
aggie_memory = ir.PointerType(ir.IntType(8))
aggie_machine = ir.PointerType(ir.IntType(8))

aggie_str_raw = ir.ArrayType(ir.IntType(8), __bulid__.STR_IR_SIZE)
aggie_bytes_raw = ir.ArrayType(ir.IntType(8), __bulid__.BYTES_IR_SIZE)
aggie_list_raw = ir.ArrayType(ir.IntType(8), __bulid__.LIST_IR_SIZE)
aggie_tuple_raw = ir.ArrayType(ir.IntType(8), __bulid__.LIST_IR_SIZE)
aggie_dict_raw = ir.ArrayType(ir.IntType(8), __bulid__.DICT_IR_SIZE)
aggie_set_raw = ir.ArrayType(ir.IntType(8), __bulid__.SET_IR_SIZE)

aggie_str = ir.PointerType(aggie_str_raw)
aggie_bytes = ir.PointerType(aggie_bytes_raw)
aggie_list = ir.PointerType(aggie_list_raw)
aggie_tuple = ir.PointerType(aggie_tuple_raw)
aggie_dict = ir.PointerType(aggie_dict_raw)
aggie_set = ir.PointerType(aggie_set_raw)



