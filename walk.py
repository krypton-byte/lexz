import ast

parse=ast.parse(open('test.py').read())
print(list(ast.walk(parse)))