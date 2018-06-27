from aggie.native.typedef import aggie_void, aggie_memory, aggie_int, aggie_str, ptr, aggie_bool, dirty, aggie_float, \
    aggie_bytes
from aggie.native.utils import NativeFunction


def make_native_functions():
    l = [
        ("aggie_str_new", aggie_void, aggie_memory, aggie_int, dirty[aggie_str]),
        ("aggie_str_del", aggie_void, aggie_str),
        ("aggie_str_copy", aggie_void, dirty[aggie_str], aggie_str),
        ("aggie_str_len", aggie_int, aggie_str),
        ("aggie_str_concat", aggie_void, aggie_str, aggie_str, dirty[aggie_str]),
        ("aggie_str_toint", aggie_int, aggie_str, ptr[aggie_bool]),
        ("aggie_str_tofloat", aggie_float, aggie_str, ptr[aggie_bool]),
        ("aggie_str_tobool", aggie_bool, aggie_str),
        ("aggie_str_hash", aggie_int, aggie_str, aggie_int),
        ("aggie_str_startswith", aggie_bool, aggie_str, aggie_str),
        ("aggie_str_endswith", aggie_bool, aggie_str, aggie_str),
        ("aggie_str_fromint", aggie_void, aggie_int, aggie_int, dirty[aggie_str]),
        ("aggie_str_fromfloat", aggie_void, aggie_float, dirty[aggie_str]),
        ("aggie_str_index", aggie_int, aggie_str, aggie_str),
        ("aggie_str_rindex", aggie_int, aggie_str, aggie_str),
        ("aggie_str_contains", aggie_bool, aggie_str, aggie_str),
        ("aggie_str_compare", aggie_int, aggie_str, aggie_str),
        ("aggie_str_at", aggie_void, aggie_str, dirty[aggie_str]),
        ("aggie_str_mid", aggie_void, aggie_str, aggie_int, aggie_int, aggie_int, dirty[aggie_str]),
        ("aggie_str_duplicate", aggie_void, aggie_str, aggie_int, dirty[aggie_str]),
        ("aggie_str_count", aggie_int, aggie_str, aggie_str),
        # ("aggie_str_replace", aggie_void, aggie_str, aggie_str, aggie_str, dirty[aggie_str]),
        # ("aggie_str_encode", aggie_void, aggie_str, aggie_str, dirty[aggie_bytes]),
    ]
    return NativeFunction.from_table(l)
