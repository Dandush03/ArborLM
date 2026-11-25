# ruff: noqa
"""Print a Python source file with docstrings and comments removed (so the auditor can read code
without reading the author's similarity claims). Usage: python strip_doc.py FILE [FILE...]"""
import ast
import io
import sys
import tokenize


def strip(src: str) -> str:
    tree = ast.parse(src)
    doc_lines = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.body and isinstance(node.body[0], ast.Expr) and isinstance(getattr(node.body[0], "value", None), ast.Constant) and isinstance(node.body[0].value.value, str):
                d = node.body[0]
                for ln in range(d.lineno, d.end_lineno + 1):
                    doc_lines.add(ln)
    out_tokens = []
    toks = tokenize.generate_tokens(io.StringIO(src).readline)
    lines = src.splitlines()
    keep = []
    comment_cols = {}
    for t in toks:
        if t.type == tokenize.COMMENT:
            comment_cols[t.start[0]] = t.start[1]
    for i, line in enumerate(lines, 1):
        if i in doc_lines:
            continue
        if i in comment_cols:
            line = line[: comment_cols[i]].rstrip()
            if not line.strip():
                continue
        keep.append(f"{i:5d} {line}")
    return "\n".join(keep)


for f in sys.argv[1:]:
    print(f"===== {f}")
    print(strip(open(f, encoding="utf-8").read()))
