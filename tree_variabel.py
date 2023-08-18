"""
Remapping Variable
"""

import ast
from typing import Any, Callable, List, Literal, Optional, Type
from dict2object import JSObject
import json
from typing import TypeVar

T = TypeVar("T")


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
            else {
                "filename": self.filename,
                "vars": {},
            }
        )

    def create(
        self,
        name: str,
        alias: str,
        node: Any = None,
        annotate: Literal["Type", "Any", "Self"] = "Any",
    ):
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
                    }
                }
            )
        else:
            self.vars["vars"].update(
                {name: {"alias": alias, "vars": {}, "name": name, "annotate": annotate}}
            )
        return self.__class__(self.filename, self.vars, [*self.position, name])

    def create_class(self, name: str, alias: str, node: Any = None):
        n = self.create(name, alias, node, annotate="Type")
        return n

    def current(self):
        data = self.vars
        for i in self.position:
            data = data["vars"][i]
        return data

    def find_variable(self, vname):
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
        del self.__class__(
            self.filename, self.vars, self.position.copy()[:-1]
        ).current()[self.position[-1]]

    def to_globals(self):
        cr = self.current()
        self.vars["vars"].update({cr["name"]: cr})

    def parent(self):
        return self.jump(1)

    def jump(self, level: int):
        return self.__class__(self.filename, self.vars, self.position[:-level])

    def copy(self):
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

    def Node(self, node: Type[T]):
        def Func(f: Callable[[T, VariableMapping], None]):
            if ast.AST in node.__bases__:
                self.__ast.append((f, node))
            elif ast.expr in node.__bases__:
                self.__expr.append((f, node))
            elif ast.stmt in node.__bases__:
                self.__stmt.append((f, node))

        return Func

    def send_node(self, node: object, var: VariableMapping):
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


collect = Collector()


@collect.Node(ast.Name)
def Name(node: ast.Name, var: VariableMapping):
    if isinstance(node.ctx, ast.Store):
        var.create(node.id, node.id)


@collect.Node(ast.Assign)
def Assign(node: ast.Assign, var: VariableMapping):
    for target in node.targets:
        collect.send_node(target, var)


@collect.Node(ast.FunctionDef)
def FunctionDef(node: ast.FunctionDef, var: VariableMapping):
    n_var = var.create(node.name, node.name)
    collect.send_node(node.args, n_var)
    for body in node.body:
        collect.send_node(body, var)


@collect.Node(ast.arguments)
def arguments(node: ast.arguments, var: VariableMapping):
    for arg in node.args:
        collect.send_node(arg, var)


@collect.Node(ast.arg)
def arg(node: ast.arg, var: VariableMapping):
    var.create(
        node.arg,
        node.arg,
        annotate=(
            "Self"
            if var.parent().current()["annotate"] == "Type"
            and not var.current()["vars"].__len__()
            else "Any"
        ),
    )


@collect.Node(ast.ClassDef)
def ClassDef(node: ast.ClassDef, var: VariableMapping):
    n_var = var.create_class(node.name, node.name)
    for body in node.body:
        collect.send_node(body, n_var)


@collect.Node(ast.Import)
def Import(node: ast.Import, var: VariableMapping):
    for i in node.names:
        collect.send_node(i, var)


@collect.Node(ast.alias)
def alias(node: ast.alias, var: VariableMapping):
    var.create(node.asname or node.name, node.asname or node.name)


# collect.send_node(ast.Name(id='a', ctx=ast.Store()),VariableMapping('e'))


class VarExtractor:
    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.var = VariableMapping(self.filename)
        self.source = open(self.filename, "r").read()

    def run(self):
        Node = ast.parse(self.source)
        for body in Node.body:
            collect.send_node(body, self.var)
        print(self.var)


VarExtractor("test.py").run()

# class_=VariableMapping('a.py').create_class('HelloWorld', 'HelloWorld')
# class_.create('B', 'B')
# class_.create('__init__','__init__').create('yahaha','ko')
# print(class_)
