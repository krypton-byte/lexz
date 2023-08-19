from __future__ import annotations
from abc import ABCMeta, abstractmethod
import secrets
from typing import TYPE_CHECKING
import random


if TYPE_CHECKING:
    from ..LexZ import VariableMapping


class DoubleUnderscoreNotAllowed(Exception):
    pass


class ReferenceError(Exception):
    pass


class AliasBackend(metaclass=ABCMeta):
    name: str
    desc: str

    def __preinit__(self):
        pass

    def __init__(self, ref: bool = True) -> None:
        self.reference = []
        self.ref = ref
        self.__preinit__()

    def middleware(self, var: VariableMapping) -> str:
        result = self.gen_alias(var)
        if (
            result != var.current()["alias"]
            and result.startswith("__")
            and var.parent().current()["annotate"] in ["Self", "Type"]
        ):
            raise DoubleUnderscoreNotAllowed()
        if self.ref:
            if result in self.reference:
                raise ReferenceError()
            self.reference.append(result)
        return result

    @abstractmethod
    def gen_alias(self, var: VariableMapping) -> str:
        ...


class FakeInstruction(AliasBackend):
    name = "FakeInstruction"
    desc = "rename Alias to fake instruction"

    def __preinit__(self) -> None:
        self.Instruction = [
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

    def gen_alias(self, var: VariableMapping) -> str:
        return random.choice(self.Instruction) + "_0x" + secrets.token_hex(5)


class UniqChar(AliasBackend):
    name = "UniqChar"
    desc = "rename Alias to Uniq character/non alphabetic"

    def gen_alias(
        self,
        var: VariableMapping
    ) -> str:
        return "".join([chr(random.randint(1000, 3000)) for _ in range(9)])
