"""F3 (auditor, Opus 5.5): what the X1 fix writes. Reads analysis.json and results/* of the g3b S9a / S9b /
S12 run directories (synthetic, INVENTED accuracies) and checks, against expectations written by hand from
section I.8: the ratio values are the string "+inf", the labels are those of an infinite ratio, and every
JSON file is strict JSON (no NaN / Infinity tokens).

Usage: uv run --locked python <this> <g3b scratch>/g3_import_side_effect
"""
import json
import sys
from pathlib import Path

ROOT = Path(sys.argv[1])
fails = []


def check(name, ok, detail=""):
    print(f"  [{'ok' if ok else 'FAIL'}] {name}{(': ' + detail) if detail else ''}")
    if not ok:
        fails.append(name)


def strict(p: Path) -> bool:
    def bad(t):
        raise ValueError(t)
    try:
        json.loads(p.read_text(), parse_constant=bad)
        return True
    except ValueError:
        return False


def ratios(block):
    """every value under a key containing 'ratio' (the implementer's field names are not assumed)"""
    out = []
    if isinstance(block, dict):
        for k, v in block.items():
            if "ratio" in k:  # attempt 1 (kept) appended the dict itself; the ratios are its values
                out += list(v.values()) if isinstance(v, dict) else [v]
            out += ratios(v)
    elif isinstance(block, list):
        for v in block:
            out += ratios(v)
    return out


for name, arm, size in (("g3b_S9a_dense_zero", "W7", "65536"), ("g3b_S12_pool", "W7", "65536")):
    run = ROOT / name
    an = json.loads((run / "analysis.json").read_text())
    note = an["analysis"]["annotations"][arm][size]["dense_comparison"]
    print(f"== {name}: W7 65536 class {an['analysis']['classes'][arm][size]}; dense comparison {json.dumps(note)}")
    rs = ratios(note)
    check(f"{name}: dense label BEATS DENSE (min ratio +inf >= 1.10)", note["label"] == "BEATS DENSE")
    check(f"{name}: ratios written as '+inf'", bool(rs) and len(rs) == 4 and all(r == "+inf" for r in rs), str(rs))
    check(f"{name}: every JSON strict", all(strict(p) for p in run.rglob("*.json")))
    check(f"{name}: results written", (run / "results" / "results.json").is_file() and (run / "results" / "RESULTS.md").is_file())

run = ROOT / "g3b_S9b_contrast_zero"
an = json.loads((run / "analysis.json").read_text())
c = an["analysis"]["backbone_contrast"]["E7/W7"]
print(f"== g3b_S9b_contrast_zero: E7 {an['analysis']['classes']['E7']}, W7 16384 {an['analysis']['classes']['W7']['16384']}; contrast {json.dumps(c)}")
check("S9b: contrast label HURTS ADDRESSING (all ratios +inf >= 1.03)", c["label"] == "BACKBONE HURTS ADDRESSING")
check("S9b: ratios '+inf'", len(ratios(c)) == 4 and all(r == "+inf" for r in ratios(c)), str(ratios(c)))
check("S9b: every JSON strict", all(strict(p) for p in run.rglob("*.json")))
md = (run / "results" / "RESULTS.md").read_text()
check("S9b: RESULTS.md prints the contrast label", "- E7/W7: BACKBONE HURTS ADDRESSING" in md)
print(f"\nFAILED CHECKS: {len(fails)} {fails}")
