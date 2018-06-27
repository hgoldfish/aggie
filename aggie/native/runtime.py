from aggie.native.typedef import aggie_void, aggie_memory, aggie_int, aggie_machine, aggie_str
from aggie.native.utils import NativeFunction


def make_native_functions():
    l = [
        ("aggie_initialize", aggie_machine),
        ("aggie_finallize", aggie_void, aggie_machine),
        ("aggie_malloc", aggie_memory, aggie_int),
        ("aggie_free", aggie_void, aggie_memory),
        ("aggie_memzero", aggie_void, aggie_memory, aggie_int),
        ("aggie_print", aggie_void, aggie_str),
    ]
    return NativeFunction.from_table(l)

