import ast
import typing

from sqlalchemy import and_, not_, or_, select

_SUPPORTED_NODES = (
    ast.Eq,
    ast.NotEq,
    ast.In,
    ast.NotIn,
    ast.Load,
    ast.Expression,
    ast.Name,
    ast.Compare,
    ast.BoolOp,
    ast.Or,
    ast.And,
    ast.Constant,
    ast.UnaryOp,
    ast.Not,
)


class PyToSQLException(Exception):
    pass


class PyToSQLParsingError(PyToSQLException):
    pass


class _QueryVisitor(ast.NodeVisitor):
    def __init__(self, table):
        self.table = table

    def _get_sides_of_compare(self, node: ast.Compare):
        return node.left, node.comparators[0]

    def _get_field(self, node: ast.Compare) -> str:
        for possible in self._get_sides_of_compare(node):
            if isinstance(possible, ast.Name):
                return possible.id
        raise PyToSQLParsingError(f"Node {node} does not have a name")

    def _get_value(self, node: ast.Compare) -> str:
        for possible in self._get_sides_of_compare(node):
            if isinstance(possible, ast.Constant):
                return possible.value
        raise PyToSQLParsingError(f"Node {node} does not have a value")

    def visit_BoolOp(self, node: ast.BoolOp):
        if isinstance(node.op, ast.Or):
            op = or_
        elif isinstance(node.op, ast.And):
            op = and_
        else:
            raise PyToSQLParsingError(f"Unsupported bool operation {node.op}")
        conditions = []
        for value in node.values:
            conditions.append(self.visit(value))
        return op(*conditions)

    def visit_UnaryOp(self, node: ast.UnaryOp):
        if isinstance(node.op, ast.Not):
            op = not_
        else:
            raise PyToSQLParsingError(f"Unsupported unary operation {node.op}")
        condition = self.visit(node.operand)
        return op(condition)

    def visit_Compare(self, node: ast.Compare):
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
        else:
            raise PyToSQLParsingError(f"Unsupported operation {node.ops[0]}")
        return condition

    def visit_Expression(self, node: ast.Expression):
        return [self.visit(node.body)]


def python_to_sqlalchemy_conditions(table, query):
    try:
        tree = ast.parse(query, mode="eval")
    except SyntaxError as e:
        raise PyToSQLParsingError(f"Invalid syntax in query `{query}`: {e.msg}") from e
    visitor = _QueryVisitor(table)
    conditions = visitor.visit(tree)
    return conditions


def python_to_sqlalchemy(table, query):
    return select(table).where(*python_to_sqlalchemy_conditions(table, query))
