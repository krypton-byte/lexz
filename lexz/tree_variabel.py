"""
Remapping Variable
"""
from __future__ import annotations
import ast
from typing import Optional

from lexz.alias_backend.default import AliasBackend
from .LexZ import Collector, VariableMapping


collect = Collector()


@collect.Node(ast.Lambda)
def Lambda(node: ast.Lambda, var: VariableMapping):
    collect.send_node(node.args, var)
    collect.send_node(node.body, var)
    return var


@collect.Node(ast.Expr)
def Expr(node: ast.Expr, var: VariableMapping):
    collect.send_node(node.value, var)
    return var


@collect.Node(ast.NamedExpr)
def NamedExpr(node: ast.NamedExpr, var: VariableMapping):
    collect.send_node(node.target, var)
    collect.send_node(node.value, var)
    return var


@collect.Node(ast.For | ast.AsyncFor)
def For(node: ast.For | ast.AsyncFor, var: VariableMapping):
    collect.send_node(node.target, var)
    collect.send_node(node.iter, var)
    for body in node.body:
        collect.send_node(body, var)
    return var


@collect.Node(ast.Name)
def Name(node: ast.Name, var: VariableMapping):
    if isinstance(node.ctx, ast.Store):
        var.create(node.id, node.id, node)
        return var
    try:
        return var.find_variable(node.id)
    except IndexError:
        return var


@collect.Node(ast.Assign)
def Assign(node: ast.Assign, var: VariableMapping):
    for target in node.targets:
        collect.send_node(target, var)
    collect.send_node(node.value, var)
    return var


@collect.Node(ast.Attribute)
def Attribute(node: ast.Attribute, var: VariableMapping):
    n_var = collect.send_node(node.value, var)
    if isinstance(node.ctx, ast.Store):
        n_var.create(node.attr, node.attr, node)
    return n_var


@collect.Node(ast.FunctionDef | ast.AsyncFunctionDef)
def FunctionDef(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    var: VariableMapping
):
    for decorator in node.decorator_list:
        collect.send_node(decorator, var)
    n_var = var.create(node.name, node.name, node)
    collect.send_node(node.args, n_var)
    for body in node.body:
        collect.send_node(body, n_var)
    return var


@collect.Node(ast.Await)
def Await(node: ast.Await, var: VariableMapping):
    collect.send_node(node.value, var)
    return var


@collect.Node(ast.Yield | ast.YieldFrom)
def Yield(node: ast.Yield | ast.YieldFrom, var: VariableMapping):
    if node.value:
        collect.send_node(node.value, var)
    return var


@collect.Node(ast.arguments)
def arguments(node: ast.arguments, var: VariableMapping):
    for arg in node.args:
        collect.send_node(arg, var)
    if node.vararg:
        collect.send_node(node.vararg, var)
    if node.kwarg:
        collect.send_node(node.kwarg, var)
    return var


@collect.Node(ast.arg)
def arg(node: ast.arg, var: VariableMapping):
    var.create(
        node.arg,
        node.arg,
        node,
        annotate=(
            "Self"
            if var.parent().current()["annotate"] == "Type"
            and not var.current()["vars"].__len__()
            else "Any"
        ),
    )
    return var


@collect.Node(ast.Tuple)
def Tuple(node: ast.Tuple, var: VariableMapping):
    for elt in node.elts:
        collect.send_node(elt, var)
    return var


@collect.Node(ast.ClassDef)
def ClassDef(node: ast.ClassDef, var: VariableMapping):
    for decorator in node.decorator_list:
        collect.send_node(decorator, var)
    for base in node.bases:
        collect.send_node(base, var)
    n_var = var.create_class(node.name, node.name, node)
    for body in node.body:
        collect.send_node(body, n_var)
    return var


@collect.Node(ast.Import)
def Import(node: ast.Import, var: VariableMapping):
    for i in node.names:
        collect.send_node(i, var)
    return var


@collect.Node(ast.alias)
def alias(node: ast.alias, var: VariableMapping):
    var.create(node.asname or node.name, node.asname or node.name, node)
    return var


@collect.Node(ast.Call)
def Call(node: ast.Call, var: VariableMapping):
    collect.send_node(node.func, var)
    for arg in node.args:
        collect.send_node(arg, var)
    return var


@collect.Node(ast.With | ast.AsyncWith)
def With(node: ast.With | ast.AsyncWith, var: VariableMapping):
    for item in node.items:
        collect.send_node(item, var)
    for body in node.body:
        collect.send_node(body, var)
    return var


@collect.Node(ast.withitem)
def withitem(node: ast.withitem, var: VariableMapping):
    collect.send_node(node.context_expr, var)
    if node.optional_vars:
        collect.send_node(node.optional_vars, var)
    return var


@collect.Node(ast.Try)
def Try(node: ast.Try, var: VariableMapping):
    for body in node.body:
        collect.send_node(body, var)
    for handler in node.handlers:
        collect.send_node(handler, var)
    return var


@collect.Node(ast.ExceptHandler)
def ExceptHandler(node: ast.ExceptHandler, var: VariableMapping):
    if node.type:
        collect.send_node(node.type, var)
    for body in node.body:
        collect.send_node(body, var)
    return var


@collect.Node(ast.GeneratorExp | ast.ListComp | ast.SetComp | ast.DictComp)
def GeneratorExp(
    node: ast.GeneratorExp | ast.ListComp | ast.SetComp | ast.DictComp,
    var: VariableMapping,
):
    if isinstance(node, ast.DictComp):
        collect.send_node(node.key, var)
    else:
        collect.send_node(node.elt, var)
    for generator in node.generators:
        collect.send_node(generator, var)
    return var


@collect.Node(ast.comprehension)
def comprehension(node: ast.comprehension, var: VariableMapping):
    collect.send_node(node.target, var)
    collect.send_node(node.iter, var)
    for if_ in node.ifs:
        collect.send_node(if_, var)
    return var


@collect.Node(ast.If)
def If(node: ast.If, var: VariableMapping):
    collect.send_node(node.test, var)
    for body in node.body:
        collect.send_node(body, var)
    return var


@collect.Node(ast.Compare)
def Compare(node: ast.Compare, var: VariableMapping):
    collect.send_node(node.left, var)
    for op in node.ops:
        collect.send_node(op, var)
    for comparator in node.comparators:
        collect.send_node(comparator, var)
    return var


@collect.Node(ast.Dict)
def Dict(node: ast.Dict, var: VariableMapping):
    for key in node.keys:
        if key:
            collect.send_node(key, var)
    for val in node.values:
        collect.send_node(val, var)
    return var


# collect.send_node(ast.Name(id='a', ctx=ast.Store()),VariableMapping('e'))


class VarExtractor:
    def __init__(
        self,
        filename: str,
        source: str,
        alias_backend: Optional[AliasBackend] = None
    ) -> None:
        self.filename = filename
        self.var = VariableMapping(
            self.filename,
            alias_backend=alias_backend
        )
        self.source = source

    @classmethod
    def from_file_source(
        cls,
        filename: str
    ):
        return cls(open(filename, "r").read(), filename)

    def extract(self):
        Node = ast.parse(self.source)
        for body in Node.body:
            collect.send_node(body, self.var)
        # print(ast.dump(Node))
        return self.var
