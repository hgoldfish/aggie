from aggie.builtins.utils import SubBuilder


class RangeType(SubBuilder):
    def dot__iter__(self, x):
        return x

    def dot__next__(self, x):
        expr_type, expr_value = x

