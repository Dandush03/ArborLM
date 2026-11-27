# ruff: noqa
# ruff: noqa
"""Print a module's source with docstrings and comments removed (ast round trip).

Used so the auditor reads generator logic without the author's prose about
which lineages are similar. Read-only on the target file.
"""
import ast
import sys


def strip(path: str) -> str:
    tree = ast.parse(open(path, encoding="utf-8").read())
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) and isinstance(body[0].value.value, str):
                node.body = body[1:] or [ast.Pass()]
    return ast.unparse(tree)


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(f"######## {p}")
        print(strip(p))
