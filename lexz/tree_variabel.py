"""
Remapping Variable
"""
from __future__ import annotations
import re
import secrets
import ast
import types
from typing import (
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Type
)
import typing
from dict2object import JSObject
from typing import TypeVar

T = TypeVar("T")


def remove_circular_refs(ob, _seen=None):
    if _seen is None:
        _seen = set()
    if id(ob) in _seen:
        # circular reference, remove it.
        return {}
    _seen.add(id(ob))
    res = ob
    if isinstance(ob, dict):
        res = {
            remove_circular_refs(k, _seen): remove_circular_refs(v, _seen)
            for k, v in ob.items()
        }
    elif isinstance(ob, (list, tuple, set, frozenset)):
        res = type(ob)(remove_circular_refs(v, _seen) for v in ob)
    # remove id again; only *nested* references count
    _seen.remove(id(ob))
    return res


class GraphGen:
    def __init__(self, var: dict) -> None:
        self.initial = []
        self.arrow = []  # 'A->B'
        self.var = var
        self.filename = re.findall(
            r"^[a-z][a-z0-9]+", self.var["filename"], re.IGNORECASE
        )[0]

    def build_graph_string(self):
        self.gen()
        return "\n".join(
            [
                "digraph %s {" % self.filename,
                " " * 4 + ("\n" + " " * 4).join([*self.initial, *self.arrow]),
                "}",
            ]
        )

    def shape(self, annotate: Literal["Type", "Self", "Any", "Module"]):
        match annotate:
            case "Type":
                return "component"
            case "Module":
                return "note"
            case "Self":
                return "cds"
        return "hexagon"

    def gen(self, var: Optional[Dict] = None, parent: Optional[str] = None):
        r_name = "_" + secrets.token_hex(5)
        n_var = var if var else self.var
        if parent:
            for node_name, node_val in n_var["vars"].items():
                r_name = "_" + secrets.token_hex(5)
                self.initial.append(
                    '%s [label="%s" shape="%s"]'
                    % (r_name, node_name, self.shape(node_val["annotate"]))
                )
                self.arrow.append(f"{parent} -> {r_name}")
                self.gen(node_val, r_name)
        else:
            self.initial.append(
                '%s [label="%s" shape="folder"]' % (r_name, n_var["filename"])
            )
            self.gen(n_var, r_name)


class VariableMapping:
    def __init__(
        self,
        filename: str,
        vars: Optional[dict] = None,
        position: Optional[List] = None,
    ) -> None:
        self.position = position if position else []
        self.filename = filename
        self.vars = (
            vars
            if vars
            else {"filename": self.filename, "vars": {}, "annotate": "Module"}
        )

    def graph_gen(self):
        dot = GraphGen(self.Normalizer())
        return dot.build_graph_string()

    def create(
        self,
        name: str,
        alias: str,
        node: ast.AST,
        annotate: Literal["Type", "Any", "Self", "Callable"] = "Any",
    ):
        """
        creating variable
        """
        if self.position:
            data = self.vars
            for i in self.position:
                data = data["vars"][i]
            data["vars"].update(
                {
                    name: {
                        "alias": alias,
                        "vars": self.parent().current()["vars"]
                        if annotate == "Self"
                        else {},
                        "name": name,
                        "annotate": annotate,
                        "node": {
                            "line_no": [node.lineno, node.end_lineno],
                            "col_offset": [node.col_offset, node.end_col_offset],
                        },
                    }
                }
            )
        else:
            self.vars["vars"].update(
                {name: {"alias": alias, "vars": {}, "name": name, "annotate": annotate}}
            )
        return self.__class__(self.filename, self.vars, [*self.position, name])

    def Normalizer(self):
        """
        Remove Circular Reference
        """
        return remove_circular_refs(self.vars.copy())

    def create_class(self, name: str, alias: str, node: ast.AST):
        n = self.create(name, alias, node, annotate="Type")
        return n

    def current(self):
        data = self.vars
        for i in self.position:
            data = data["vars"][i]
        return data

    def find_variable(self, vname):
        """
        find variable from down to top
        """
        if self.position:
            for i in range(self.position.__len__(), 0, -1):
                post = self.position.copy()[:i]
                data = self.vars
                for sc in post:
                    data = data["vars"][sc]
                if not (data["vars"].get(vname) is None):
                    return self.__class__(self.filename, self.vars, [*post, vname])
        else:
            if vname in self.vars["vars"].keys():
                return self.__class__(self.filename, self.vars, [vname])
        raise IndexError

    def delete(self):
        """
        Delete Variable
        """
        del self.__class__(
            self.filename, self.vars, self.position.copy()[:-1]
        ).current()[self.position[-1]]

    def to_globals(self):
        cr = self.current()
        self.vars["vars"].update({cr["name"]: cr})

    def parent(self):
        return self.jump(1)

    def jump(self, level: int):
        """
        jump to parent stack
        """
        return self.__class__(self.filename, self.vars, self.position[:-level])

    def copy(self):
        """
        copy variable with vars reference
        """
        return self.__class__(self.filename, self.vars, self.position.copy())

    def __repr__(self) -> str:
        return (
            JSObject(indent="  ").fromDict(js=self.current()).__repr__()
        )  # self.current().__str__()


class Collector:
    def __init__(self) -> None:
        self.__stmt = []
        self.__expr = []
        self.__ast = []

    def Node(
        self, ast_node: typing.Union[Type[T], types.UnionType]
    ) -> Callable[
        [Callable[[T, VariableMapping], VariableMapping]],
        Callable[[T, VariableMapping], VariableMapping],
    ]:
        def Func(f: Callable[[T, VariableMapping], VariableMapping]):
            if isinstance(ast_node, types.UnionType):
                for node_type in ast_node.__args__:
                    self.Node(node_type)(f)
            else:
                if ast.AST in ast_node.__bases__:
                    self.__ast.append((f, ast_node))
                elif ast.expr in ast_node.__bases__:
                    self.__expr.append((f, ast_node))
                elif ast.stmt in ast_node.__bases__:
                    self.__stmt.append((f, ast_node))
            return f

        return Func

    def send_node(self, node: ast.AST, var: VariableMapping) -> VariableMapping:
        functions = []
        if ast.AST in node.__class__.__bases__:
            functions = self.__ast
        elif ast.expr in node.__class__.__bases__:
            functions = self.__expr
        elif ast.stmt in node.__class__.__bases__:
            functions = self.__stmt
        for func, ast_type in functions:
            if isinstance(node, ast_type):
                return func(node, var)
        return var


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
    return var


@collect.Node(ast.Attribute)
def Attribute(node: ast.Attribute, var: VariableMapping):
    n_var = collect.send_node(node.value, var)
    if isinstance(node.ctx, ast.Store):
        n_var.create(node.attr, node.attr, node)
    return n_var


@collect.Node(ast.FunctionDef | ast.AsyncFunctionDef)
def FunctionDef(node: ast.FunctionDef | ast.AsyncFunctionDef, var: VariableMapping):
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


@collect.Node(ast.ClassDef)
def ClassDef(node: ast.ClassDef, var: VariableMapping):
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


# collect.send_node(ast.Name(id='a', ctx=ast.Store()),VariableMapping('e'))


class VarExtractor:
    def __init__(self, filename: str, source: str) -> None:
        self.filename = filename
        self.var = VariableMapping(self.filename)
        self.source = source

    @classmethod
    def from_file_source(cls, filename: str):
        return cls(open(filename, 'r').read(), filename)

    def extract(self):
        Node = ast.parse(self.source)
        for body in Node.body:
            collect.send_node(body, self.var)
        return self.var
