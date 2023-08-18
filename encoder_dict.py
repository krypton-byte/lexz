from enum import Enum
import enum
import hashlib
import ast
import builtins
import random
import time
from typing import Any, Dict, List, Optional, Union
import secrets
import re
import marshal
import random


def IntObf(x):
    add = []
    while x != 0:
        if x < 0:
            add.append(-x)
            x += -x
        else:
            choice = random.randint(1, x)
            x -= choice
            add.append(choice)
    return add


secret = secrets.token_hex(2)


class ValueType(Enum):
    CONSTANT = secret[:2].encode()
    CONSTANT_NUM = secret[0] + secret[2]
    NAME = secret[2:].encode()

    @classmethod
    def get(cls, type: Union[ast.Name, ast.Constant]):
        if isinstance(type, ast.Name):
            return cls.NAME
        elif isinstance(type, ast.Constant):
            return cls.CONSTANT
        raise IndexError


# class Enc:
#     def __init__(self) -> None:
#         self.salt = secrets.token_hex().encode()

#     def hash(self, text: str, type: ValueType) -> str:
#         hash = (
#             hashlib.sha256(
#                 text + self.salt[0 : self.salt.__len__() // 2]
#                 if isinstance(text, bytes)
#                 else type.value + self.salt[self.salt.__len__() // 2 :] + text.__repr__().encode()
#             )
#             .hexdigest()
#             .lower()
#         )
#         return re.findall(r"[a-z]\w+", hash)[0][:14].upper()+'__'


class Enc:
    def __init__(self) -> None:
        self.state = 1
        self.R_OP = [
            "CMP",
            "ADD",
            "OR",
            "XOR",
            "XNAND",
            "EAX",
            "AAA",
            "CS",
            "PUSH",
            "MUL",
            "OP",
            "LOCK",
            "OUT",
            "IN",
            "INT32",
            "INT64",
            "FLOAT64",
            "DIV",
            "CALL",
            "STR",
            "NOT",
            "REP",
        ]
        self.saver = {}

    def hash(self, text, s):
        if not self.saver.get(text):
            self.saver[text] = (
                random.choice(self.R_OP) + "_0x" + secrets.token_hex(3).upper()
            )
            self.state += 1
        return self.saver[text]


class Encoder:
    def __init__(self, source) -> None:
        self.enc = Enc()
        self.source = source
        self.var = {'var':{'globals':{}}}
        self.AST_TREE = []
        self.INITIALIZE_TREE = []
        self.Initialize()

    def Initialize(self):
        # self.INITIALIZE_TREE.append(ast.Import(names=[ast.alias(name="marshal")]))
        built = dir(__builtins__)
        for attr in ['eval', 'sum', 'map', 'chr']:
            if attr in built:
                built.remove(attr)
            built.insert(0, attr)
        for i in built:
            alias = self.enc.hash(i, ValueType.NAME)
            self.INITIALIZE_TREE.append(
                ast.Assign(
                    targets=[
                        ast.Name(id=alias, ctx=ast.Store())
                    ],
                    value=ast.Call(
                        func=self.Name(ast.Name(id="eval", ctx=ast.Load()), self.var),
                        args=[
                            ast.Call(
                                func=ast.Attribute(
                                    value=ast.Constant(value=""),
                                    attr="join",
                                    ctx=ast.Load(),
                                ),
                                args=[
                                    ast.Call(
                                        func=self.Name(
                                            ast.Name(id="map", ctx=ast.Load()), self.var
                                        ),
                                        args=[
                                            self.Name(
                                                ast.Name(id="chr", ctx=ast.Load()),
                                                self.var,
                                            ),
                                            ast.List(
                                                elts=[
                                                    self.Constant(
                                                        ast.Constant(value=ord(char)),
                                                        self.var,
                                                    )
                                                    for char in i
                                                ],
                                                ctx=ast.Load(),
                                            ),
                                        ],
                                        keywords=[],
                                    )
                                ],
                                keywords=[],
                            )
                        ],
                        keywords=[],
                    ),
                )
            )
            self.var.update({i:{'node': ast.Name(id=i, ctx=ast.Load()), 'alias': alias}})

    def Import(self, node: ast.Import | ast.ImportFrom, var: Dict):
        for i in range(node.names.__len__()):
            if node.names[i].asname:
                alias = self.enc.hash(
                    node.names[i].asname, ValueType.NAME
                )
                var.update({node.names[i].asname: {'node': node, 'alias': alias}})
                node.names[i].asname = alias
            else:
                alias = self.enc.hash(node.names[i].name, ValueType.NAME)
                var.update({node.names[i].name: {'node': node, 'alias': alias}})
                node.names[i].asname = alias
        return node

    def import_from(self, node: ast.ImportFrom, var):
        for i in range(node.names.__len__()):
            pass

    def Call(self, node: ast.Call, var: Dict):
        if isinstance(node.func, ast.Name):
            id = node.func.id
            if id in var:
                node.func.id = var[id]['alias']
        node.func = self.expr(node.func, var)

        for arg in range(node.args.__len__()):
            if isinstance(node.args[arg], ast.Constant):
                alias = self.enc.hash(node.args[arg].value, ValueType.CONSTANT)  # type: ignore
                self.INITIALIZE_TREE.append(
                    ast.Assign(
                        targets=[ast.Name(id=alias, ctx=ast.Store())],
                        value=self.Constant(ast.Constant(value=node.args[arg].value), var),  # type: ignore
                    )
                )
                node.args[arg] = ast.Name(id=alias, ctx=ast.Store())
            else:
                node.args[arg] = self.expr(node.args[arg], var)
        return node

    def For(self, node: ast.For, var: Dict):
        node.target = self.expr(node.target, var)
        for i, body in enumerate(node.body):
            node.body[i] = self.stmt(body, var)
        node.iter = self.expr(node.iter, var)
        return node

    def Tuple(self, node: ast.Tuple, var: Dict):
        for i, child in enumerate(node.elts):
            node.elts[i] = self.expr(child, var)
        return node

    def List_(self, node: ast.List, var: Dict):
        for i, child in enumerate(node.elts):
            node.elts[i] = self.expr(child, var)
        return node

    def BinOp(self, node: ast.BinOp, var: Dict):
        OP = {
            ast.Add: "__add__",
            ast.BitAnd: "__and__",
            ast.BitXor: "__xor__",
            ast.BitOr: "__or__",
            ast.Sub: "__sub__",
            ast.Mult: "__mul__",
            ast.Pow: "__pow__",
            ast.Div: "__truediv__",
            ast.Mod: "__mod__",
        }

        def find(op):
            for k, v in OP.items():
                if isinstance(op, k):
                    return v
            return IndexError

        node.right = self.expr(node.right, var)
        node.left = self.expr(node.left, var)
        # return node
        return ast.Call(
            func=self.Attribute(
                ast.Attribute(value=node.left, attr=find(node.op), ctx=ast.Load()), var
            ),
            args=[node.right],
            keywords=[],
        )

    def Name(self, node: ast.Name, var):
        if isinstance(node.ctx, ast.Load):
            if node.id in var:
                node.id = var[node.id]['alias']
        elif isinstance(node.ctx, ast.Store):
            id=node.id
            node.id = self.enc.hash(node.id, ValueType.NAME)
            var.update({id: {'node': node, 'alias': node.id}})
        return node

    def Expr(self, node, var: Dict):
        return ast.Expr(value=self.expr(node.value, var))

    def replace(self, node, var):
        if ast.stmt in node.__class__.__bases__:
            return self.stmt(node, var)
        elif ast.expr in node.__class__.__bases__:
            return self.expr(node, var)
        elif ast.AST in node.__class__.__bases__:
            return self.AST(node, var)
        return node

    def Assign(self, node: ast.Assign, var: Dict):
        for target in range(node.targets.__len__()):
            if isinstance(node.targets[target], ast.Attribute):
                node.targets[target] = self.Attribute(
                    node.targets[target], var, value=node.value  # type: ignore
                )
                return ast.Expr(node.targets[target])
            else:
                node.targets[target] = self.expr(node.targets[target], var)
        node.value = self.expr(node.value, var)
        return node

    def Attribute(
        self, node: ast.Attribute, var: Dict, value: Optional[ast.expr] = None
    ):
        if isinstance(node.value, ast.Name):
            if value:
                return ast.Call(
                    func=self.expr(ast.Name(id="setattr", ctx=ast.Store()), var),
                    args=[
                        self.Name(node.value, var),
                        self.Constant(ast.Constant(node.attr), var),
                        self.expr(value, var),
                    ],
                    keywords=[],
                )
            else:
                return ast.Call(
                    func=self.expr(ast.Name(id="getattr", ctx=ast.Load()), var),
                    args=[
                        self.Name(node.value, var),
                        self.Constant(ast.Constant(node.attr), var),
                    ],
                    keywords=[],
                )
        else:
            node.value = self.expr(node.value, var)
        return node

    def ConstantInt(self, i: int, var):
        return ast.Call(
            func=self.Name(ast.Name(id="sum", ctx=ast.Load()), var),
            args=[
                ast.List(
                    elts=[ast.Constant(value=x) for x in IntObf(i)], ctx=ast.Load()
                )
            ],
            keywords=[],
        )

    def ConstantString(self, i: str, var):
        return ast.Call(
            func=ast.Attribute(
                value=ast.Call(
                    func=self.Name(ast.Name(id="bytes", ctx=ast.Load()), var),
                    args=[
                        ast.List(
                            elts=[self.ConstantInt(ord(x), var) for x in i],
                            ctx=ast.Load(),
                        )
                    ],
                    keywords=[],
                ),
                attr="decode",
                ctx=ast.Load(),
            ),
            args=[ast.Constant(value="utf-8")],
            keywords=[],
        )

    def Constant(self, node: ast.Constant, var):
        if isinstance(node.value, int):
            return self.ConstantInt(node.value, var)
        elif isinstance(node.value, str):
            return self.ConstantString(node.value, var)
        return node

    def Return(self, node: ast.Return, var: Dict):
        node.value = self.expr(node.value, var)
        return node

    def Arg(self, node: ast.arg, var):
        if node.arg not in var:
            alias = self.enc.hash(node.arg, ValueType.NAME)
            var.update({node.arg: {'node': node, 'alias': alias}})
        else:
            node.arg = var[node.arg]['alias']
        return node

    def FunctionDef(self, node: ast.FunctionDef, var: Dict):
        node_name = node.name
        if node.name not in var:
            alias = self.enc.hash(node.name, ValueType.NAME)
            if var['var'].get('locals') is None:
                var['var']['globals'].update({node_name: {'node': node, 'alias': alias, 'var': {'globals':var['globals'], 'locals':{}}}})
            else:
                var['var']['locals'].update({node_name: {'node': node, 'alias': alias, 'var': {'globals':var['globals'], 'locals':{}}}})
            node.name = alias
        else:
            node.name = var[node.name]['alias']
        node.returns = None
        node.decorator_list = [self.expr(n, var) for n in node.decorator_list]
        for arg in range(node.args.args.__len__()):
            node.args.args[arg] = self.Arg(node.args.args[arg], var)
        for child in range(node.body.__len__()):
            node.body[child] = self.stmt(node.body[child], var)
        if not (var.get('attributes') is None):
            print('ada attr')            var['attributes'].update({node_name: {'node': node, 'alias': node.name, 'var': {'globals': var['globals'], 'locals':{}}}})
        return node

    def ClassDef(self, node: ast.ClassDef, var: Dict):
        r_name = node.name
        node.name = self.enc.hash(node.name, ValueType.NAME)
        var.update({r_name: {'node': node, 'alias': node.name, 'attributes':{}}})
        var = var.copy()
        node.decorator_list = [self.expr(i, var[r_name]) for i in node.decorator_list]
        node.bases = [self.expr(i, var[r_name]) for i in node.bases]
        node.body = [
            body
            if isinstance(body, (ast.Assign))
            else self.stmt(body, var)
            for body in node.body
        ]
        clsdict = ast.Dict(keys=[], values=[])
        print(var[r_name]['attributes'])
        # for i, cbody in enumerate(node.body):
        #     if isinstance(cbody, ast.FunctionDef):
        #         self.INITIALIZE_TREE.append(cbody)
        #         clsdict.keys.append(ast.Constant(value=cbody.name))
        #         node.body[i] = self.FunctionDef(cbody, var)
        #         clsdict.values.append(ast.Name(id=node.body[i].name, ctx=ast.Load()))  # type: ignore
        new_node = ast.Call(
            func=ast.Name(id="type", ctx=ast.Load()),
            args=[
                self.Constant(ast.Constant(value=secrets.token_hex(2).upper()), var),
                ast.Tuple(elts=node.bases, ctx=ast.Load()),
                clsdict,
            ],
            keywords=[],
        )
        return ast.Assign(
            targets=[ast.Name(id=node.name, ctx=ast.Store())], value=new_node
        )
    def Try(self, node: ast.Try, var: Dict):
        for i, body in enumerate(node.body):
            node.body[i] = self.stmt(body, var)
        node.handlers = [self.ExceptHandler(exc, var) for exc in node.handlers]
        return node
    def ExceptHandler(self, node: ast.ExceptHandler, var: Dict):
        alias = self.enc.hash(node.name, ValueType.NAME)
        if node.name and node.name not in var:
            var.update({node.name: {'node': node, 'alias': alias}})
        node.name = alias
        node.type = self.expr(node.type, var)
        for i, body in enumerate(node.body):
            node.body[i] = self.stmt(body, var)
        return node

    def Raise(self, node: ast.Raise, var: Dict):
        node.exc = self.expr(node.exc, var)
        return node
    def JoinedStr(self, node: ast.JoinedStr, var: Dict):
        node.values = [self.expr(value, var) for value in node.values]
        return node
    def FormattedValue(self, node: ast.FormattedValue, var: Dict):
        node.value = self.expr(node.value, var)
        return node
    def If(self, node: ast.If, var: Dict):
        node.test = self.expr(node.test, var)
        for i, body in enumerate(node.body):
            node.body[i] = self.stmt(body, var)
        return node
    def ListComp(self, node: ast.ListComp, var: Dict):
        node.generators = [self.comprehenstion(gen, var) for gen in node.generators]
        node.elt = self.expr(node.elt, var)
        return node
    def comprehenstion(self, node: ast.comprehension, var: Dict):
        node.iter = self.expr(node.iter, var)
        node.target = self.expr(node.target, var)
        node.ifs = [self.expr(_if, var) for _if in node.ifs]
        return node
    def Compare(self, node: ast.Compare, var: Dict):
        node.left = self.expr(node.left, var)
        node.comparators = [self.expr(xo, var) for xo in node.comparators]
        # if node.ops.__len__() == 1:
        #     ops = {
        #         ast.GtE: '__ge__',
        #         ast.LtE: '__le__',
        #         ast.Lt: '__lt__',
        #         ast.Gt: '__gt__',
        #         ast.Eq: '__eq__',
        #         ast.NotEq: '__ne__',
        #         ast.NotIn: ''

        #     }
        #     def find(op):
        #         for k, v in ops.items():
        #             if isinstance(node.ops, k):
        #                 return v
        #     ops_ = []
        #     for op, comp in zip(node.ops,node.comparators):
        #         ops_.append(ast.Call(func=ast.Attribute(value=node.left, attr=find(op), ctx=ast.Load()), args=[comp], keywords=[]))
        return node

    def parse(self, var: Optional[Dict] = None):
        var = var.copy() if var else self.var
        for node in ast.parse(self.source).body:
            self.AST_TREE.append(self.replace(node, var))
        return ast.fix_missing_locations(
            ast.Module(body=[*self.INITIALIZE_TREE, *self.AST_TREE], type_ignores=[])
        )

    def stmt(self, node: ast.stmt, var: Dict):
        if isinstance(node, ast.For):
            return self.For(node, var)
        elif isinstance(node, ast.FunctionDef):
            return self.FunctionDef(node, var)
        elif isinstance(node, ast.Assign):
            return self.Assign(node, var)
        elif isinstance(node, ast.Expr):
            return self.Expr(node, var)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            return self.Import(node, var)
        elif isinstance(node, ast.Return):
            return self.Return(node, var)
        elif isinstance(node, ast.ClassDef):
            return self.ClassDef(node, var)
        elif isinstance(node, ast.If):
            return self.If(node, var)
        elif isinstance(node, ast.Raise):
            return self.Raise(node, var)
        elif isinstance(node, ast.Try):
            return self.Try(node, var)
        return node

    def AST(self, node: ast.AST, var):
        if isinstance(node, ast.arg):
            return self.Arg(node, var)
        elif isinstance(node, ast.comprehension):
            return self.comprehenstion(node, var)
        return node

    def expr(self, node, var):
        if isinstance(node, ast.Constant):
            return self.Constant(node, var)
        elif isinstance(node, ast.Name):
            return self.Name(node, var)
        elif isinstance(node, ast.BinOp):
            return self.BinOp(node, var)
        elif isinstance(node, ast.Tuple):
            return self.Tuple(node, var)
        elif isinstance(node, ast.List):
            return self.List_(node, var)
        elif isinstance(node, ast.Call):
            return self.Call(node, var)
        elif isinstance(node, ast.Attribute):
            return self.Attribute(node, var)
        elif isinstance(node, ast.Compare):
            return self.Compare(node, var)
        elif isinstance(node, ast.FormattedValue):
            return self.FormattedValue(node, var)
        elif isinstance(node, ast.JoinedStr):
            return self.JoinedStr(node, var)
        elif isinstance(node, ast.ListComp):
            return self.ListComp(node, var)
        return node

# print(ast.dump(ast.parse(open("test2.py").read())))
print(ast.unparse(Encoder(open('test.py').read()).parse()))
