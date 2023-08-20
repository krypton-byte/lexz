import argparse
import json
from .alias_backend.backend import backends, get_backend_by_name
from . import VarExtractor


arg = argparse.ArgumentParser()
arg.add_argument(
    '-f',
    help='python file',
    type=argparse.FileType('r'),
    required=True
)
arg.add_argument('-g', help='Graph Output', type=argparse.FileType('w'))
arg.add_argument(
    '-o',
    help='save var dump (json file)',
    type=argparse.FileType('w')
)
arg.add_argument(
    '-b',
    help='set alias backend',
    choices=[backend.name for backend in backends],
    default=None
)
arg.add_argument('-r', help='Variable Reference', type=bool, default=True)
parse = arg.parse_args()
extractor = VarExtractor(
    parse.f.name,
    parse.f.read(),
    alias_backend=get_backend_by_name(
        parse.b)(ref=parse.r) if parse.b else None
)
extract = extractor.extract()
if parse.g:
    parse.g.write(extract.graph_gen())
if parse.o:
    parse.o.write(json.dumps(extract.Normalizer(), indent=4))
