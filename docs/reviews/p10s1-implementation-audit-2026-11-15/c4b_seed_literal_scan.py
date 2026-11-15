"""Every integer literal in src/arborlm/*.py and studies/p9*/*.py (ast scan) intersected with S1's namespaces (auditor's enumeration in c4).
Literals are not all seeds; a hit is listed for inspection, not counted as an overlap by itself.
Run: PYTHONPATH=. uv run --locked python docs/reviews/p10s1-implementation-audit-2026-11-15/c4b_seed_literal_scan.py
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval."""
import ast, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import c4_registry_seeds as c4
ROOT = Path(__file__).resolve().parents[3]
ns = c4.my_s1_seeds()
hits = {}
for p in sorted(list((ROOT / "src/arborlm").glob("*.py")) + list((ROOT / "studies").glob("p9*/*.py"))):
    for node in ast.walk(ast.parse(p.read_text())):
        if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
            for k, v in ns.items():
                if node.value in v:
                    hits.setdefault(k, []).append(f"{p.relative_to(ROOT)}:{node.lineno}={node.value}")
json.dump({k: v[:40] for k, v in hits.items()} | {"counts": {k: len(v) for k, v in hits.items()}}, sys.stdout, indent=1)
print()
