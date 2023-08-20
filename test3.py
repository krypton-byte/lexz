from __future__ import annotations
import ast
from lexz.tree_variabel import collect, VariableMapping
var = VariableMapping('test.py')
for body in ast.parse(open('test.py').read()).body:
    print(collect.send_node(body, var))

class a:
    def __init__(self) -> None:
        self.b=4
        