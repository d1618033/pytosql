import ast

from sqlalchemy import and_, or_, select


class _QueryVisitor(ast.NodeVisitor):
    def __init__(self, table):
        self.table = table
        self.conditions = []

    def _get_sides_of_compare(self, node):
        return node.left, node.comparators[0]

    def _get_field(self, node):
        for possible in self._get_sides_of_compare(node):
            if isinstance(possible, ast.Name):
                return possible.id

    def _get_value(self, node):
        for possible in self._get_sides_of_compare(node):
            if isinstance(possible, ast.Constant):
                return possible.value

    def visit_BoolOp(self, node):
        if isinstance(node.op, ast.Or):
            op = or_
        elif isinstance(node.op, ast.And):
            op = and_
        self.generic_visit(node)
        condition = op(*self.conditions)
        self.conditions = [condition]

    def visit_Compare(self, node):
        field = self._get_field(node)
        column = getattr(self.table, field)
        value = self._get_value(node)
        if isinstance(node.ops[0], ast.Eq):
            condition = column == value
        elif isinstance(node.ops[0], ast.NotEq):
            condition = column != value
        elif isinstance(node.ops[0], ast.In):
            condition = column.any(name=value)
        elif isinstance(node.ops[0], ast.NotIn):
            condition = ~column.any(name=value)
        self.conditions.append(condition)


def python_to_sqlalchemy(table, query):
    tree = ast.parse(query, mode="eval")
    visitor = _QueryVisitor(table)
    visitor.visit(tree)
    return select(table).where(*visitor.conditions)
