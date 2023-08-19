import os
from typing import List, Type
from pathlib import Path
from typing import Optional

from lexz.exceptions import AliasBackendNotFound
from .default import AliasBackend

backends: List[Type[AliasBackend]] = []


def import_dir(cdir: Optional[Path] = None):
    cpath = cdir if cdir else Path(__file__).parent
    for path in os.listdir(cpath):
        name_split = path.split(".")
        n_path = cpath / path
        if (
            n_path.is_file()
            and name_split.__len__() == 2
            and name_split[1] == "py"
            and n_path.__str__() != __file__
        ):
            py_file = n_path.relative_to(os.getcwd()).__str__()[:-3]
            module = __import__(py_file.replace("/", "."))
            for attr in py_file.split("/")[1:]:
                module = getattr(module, attr)
            for backend in dir(module):
                obj = getattr(module, backend)
                if isinstance(obj, type) and AliasBackend in obj.__bases__:
                    yield obj
        elif n_path.is_dir():
            yield from import_dir(n_path)


def get_backend_by_name(name: str):
    for backend in backends:
        if backend.name == name:
            return backend
    raise AliasBackendNotFound()


for backend in import_dir():
    backends.append(backend)
