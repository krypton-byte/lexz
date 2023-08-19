from __future__ import annotations
import re
import secrets
import ast
import types
from typing import Callable, Dict, List, Literal, Optional, Type
import typing
try:
    from dict2object import JSObject
except ModuleNotFoundError:
    import pip
    pip.main([
        'install',
        'git+https://github.com/krypton-byte/dict2object.git'
    ])
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
                            "line_no": [
                                node.lineno,
                                node.end_lineno
                            ],
                            "col_offset": [
                                node.col_offset,
                                node.end_col_offset
                            ],
                        },
                    }
                }
            )
        else:
            self.vars["vars"].update(
                {
                    name: {
                        "alias": alias,
                        "vars": {},
                        "name": name,
                        "annotate": annotate
                        }
                }
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
                    return self.__class__(
                        self.filename,
                        self.vars,
                        [*post, vname]
                    )
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

    def send_node(
        self,
        node: ast.AST,
        var: VariableMapping
    ) -> VariableMapping:
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
