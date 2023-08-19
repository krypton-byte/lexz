import argparse
import json


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
parse = arg.parse_args()
extractor = VarExtractor(parse.f.name, parse.f.read())
extract = extractor.extract()
if parse.g:
    parse.g.write(extract.graph_gen())
if parse.o:
    parse.o.write(json.dumps(extract.Normalizer(), indent=4))
