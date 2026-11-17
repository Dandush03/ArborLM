# ruff: noqa: E501
"""The implementer-worded strings of P10S0 (the re-check's N7): module-level string constants of ``classes``, ``core``, ``report`` and ``analysis`` that a reader of a result sees and that ADR-0019 and ADR-0020 do
not contain. The freeze record template lists them (``studies/p10s0/freeze/README.md``) so the human lead approves each wording there; a test requires the README to list every one this scan finds.

``uv run --locked python -m studies.p10s0.implementer_strings`` prints the markdown section for the README. A string the ADRs contain verbatim is not implementer-worded and is not listed.
"""

import ast
from pathlib import Path

MODULES = ("classes", "core", "report", "analysis")
BODY_MODULES = ("classes", "analysis")  # their function-body strings are the labels, statuses and readings a result prints; report's and core's are layout and error text (not scanned)
MIN_WORDS = 3


def adr_text(root: Path) -> str:
    folder = root / "docs/decisions"
    return "\n".join(p.read_text(encoding="utf-8") for pattern in ("ADR-0019*.md", "ADR-0020*.md") for p in sorted(folder.glob(pattern)))


def _leaves(node: ast.AST) -> list[tuple[str, str]]:
    """(path inside the constant, string) for a str constant or a tuple, list, set or dict of them."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [("", node.value)]
    out: list[tuple[str, str]] = []
    if isinstance(node, ast.Tuple | ast.List | ast.Set):
        for i, elt in enumerate(node.elts):
            out += [(f"[{i}]{p}", v) for p, v in _leaves(elt)]
    elif isinstance(node, ast.Dict):
        for key, value in zip(node.keys, node.values, strict=True):
            label = ast.literal_eval(key) if isinstance(key, ast.Constant) else "?"
            out += [(f"[{label!r}]{p}", v) for p, v in _leaves(value)]
    return out


def scan(root: Path) -> dict[str, str]:
    """``module.NAME[path]`` -> string, for every module-level upper-case string constant of at least ``MIN_WORDS`` words that the ADRs do not contain."""
    adr = adr_text(root)
    found: dict[str, str] = {}
    for module in MODULES:
        tree = ast.parse((root / "studies/p10s0" / f"{module}.py").read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.Assign):
                names = [t.id for t in node.targets if isinstance(t, ast.Name) and t.id.isupper()]
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id.isupper() and node.value is not None:
                names = [node.target.id]
            else:
                continue
            value = node.value
            if not names or value is None:
                continue
            for sub, text in _leaves(value):
                if len(text.split()) >= MIN_WORDS and text not in adr:
                    found[f"{module}.{names[0]}{sub}"] = text
    for module in BODY_MODULES:
        tree = ast.parse((root / "studies/p10s0" / f"{module}.py").read_text(encoding="utf-8"))
        docstrings = {id(n.body[0].value) for n in ast.walk(tree) if isinstance(n, ast.FunctionDef | ast.ClassDef | ast.Module) and n.body and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
        for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
            for leaf in ast.walk(func):
                if isinstance(leaf, ast.Constant) and isinstance(leaf.value, str) and id(leaf) not in docstrings and len(leaf.value.split()) >= MIN_WORDS and leaf.value not in adr:
                    found.setdefault(f"{module}.{func.name}: {leaf.value[:40]}", leaf.value)
    return found


def markdown(root: Path) -> str:
    lines = ["| constant | wording |", "| --- | --- |"]
    for name, text in scan(root).items():
        lines.append(f"| `{name}` | {text.replace('|', '\\|')} |")
    return "\n".join(lines)


if __name__ == "__main__":
    print(markdown(Path(__file__).resolve().parents[2]))
