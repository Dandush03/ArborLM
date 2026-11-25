# ruff: noqa
"""Print a module's source with every docstring and comment removed (so that the auditor reads code, not the
author's similarity opinions, before writing an own judgement). Read-only."""
import ast
import sys

for path in sys.argv[1:]:
    src = open(path).read()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            b = node.body
            if b and isinstance(b[0], ast.Expr) and isinstance(getattr(b[0], "value", None), ast.Constant) and isinstance(b[0].value.value, str):
                node.body = b[1:] or [ast.Pass()]
    print(f"######## {path}")
    print(ast.unparse(tree))
