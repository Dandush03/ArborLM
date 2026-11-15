"""Re-check auditor A: compare every hash constant in fetch_guard.py with the saved Hub trees and the ADR text,
character for character, using my own parsing (the constants are read from the source text by regex, not imported)."""
import json, re, sys, hashlib
from pathlib import Path
P = Path(sys.argv[1])
web = P / "docs/reviews/p10-design-2026-11-15/adr-0022-review/web"
src = (P / "studies/p10s2/fetch_guard.py").read_text()
adr = (P / "docs/decisions/ADR-0022-p10-s2-two-teacher-transfer.md").read_text()
# constants by regex from source text
const = {}
for m in re.finditer(r'"((?:teacher_a|teacher_b|student|fallback)/[^"]+)": \("([0-9a-f]+)", (\d+)\)', src):
    const[m.group(1)] = (m.group(2), int(m.group(3)))
print("constants parsed from source:", len(const))
revs = dict(re.findall(r'(TEACHER_A|TEACHER_B|STUDENT|FALLBACK) = \("[^"]+", "([0-9a-f]{40})"\)', src))
print("revisions in source:", revs)
trees = {"teacher_a": "opus_en-de", "teacher_b": "opus_en-fr", "student": "smol", "fallback": "opus_en-es"}
revkey = {"teacher_a": "TEACHER_A", "teacher_b": "TEACHER_B", "student": "STUDENT", "fallback": "FALLBACK"}
bad = 0
total_small = {"teacher_a": 0, "teacher_b": 0, "student": 0, "fallback": 0}
total_large = {}
for lab, t in trees.items():
    tree = json.loads((web / f"{t}_tree.json").read_text())
    rev = json.loads((web / f"{t}_rev.json").read_text())["sha"]
    ok = rev == revs[revkey[lab]]
    print(f"== {lab}: saved rev {rev} == source {revs[revkey[lab]]}: {ok}; in ADR text: {rev in adr}")
    bad += not ok
    byp = {e["path"]: e for e in tree if e.get("type") == "file"}
    for name, (h, size) in sorted(const.items()):
        if not name.startswith(lab + "/"):
            continue
        f = name.split("/", 1)[1]
        e = byp.get(f)
        if e is None:
            print("   MISSING in tree:", f); bad += 1; continue
        if "lfs" in e:
            want, wsize, kind = e["lfs"]["oid"], e["lfs"]["size"], "lfs-sha256"
            total_large[name] = size
        else:
            want, wsize, kind = e["oid"], e["size"], "git-blob-sha1"
            total_small[lab] += size
        eq = (want == h and wsize == size)
        print(f"   {f:26s} {kind:14s} tree {want} {wsize}  const {h} {size}  equal={eq}  len={len(h)}")
        bad += not eq
        if kind == "git-blob-sha1" and len(h) != 40: bad += 1
        if kind == "lfs-sha256":
            inadr = h in adr and f"{size:,}" in adr
            print(f"      large digest and size in ADR text: {inadr}")
            bad += not inadr
    # files in tree that are LFS but treated as small?
    for f, e in byp.items():
        if f"{lab}/{f}" in const and "lfs" in e and f"{lab}/{f}" not in total_large:
            print("   LFS file treated as small:", f); bad += 1
# saved config.json copies: blob hash and suspicious keys
for lab, t in trees.items():
    cfgp = web / ("smol_config.json" if lab == "student" else f"{t}_config.json")
    data = cfgp.read_bytes()
    blob = hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()
    cfg = json.loads(data)
    sus = [k for k in cfg if k.startswith("_") or k in ("auto_map", "trust_remote_code", "custom_pipelines")]
    print(f"config {lab}: blob {blob} == const {const[lab + '/config.json'][0]}: {blob == const[lab + '/config.json'][0]}; suspicious keys {sus}")
    bad += blob != const[lab + '/config.json'][0]
print("small totals per repo:", total_small, "sum primary:", sum(v for k, v in total_small.items() if k != "fallback"))
print("large primary:", sum(v for k, v in total_large.items() if not k.startswith("fallback")))
prim = sum(v for k, v in total_small.items() if k != "fallback") + sum(v for k, v in total_large.items() if not k.startswith("fallback"))
print("model rows 1-3 total bytes:", prim)
for lab in ("teacher_a", "teacher_b", "student", "fallback"):
    s = total_small[lab] + sum(v for k, v in total_large.items() if k.startswith(lab))
    print(f"  {lab}: {s} B = {s/1e6:.1f} MB")
tat = [int(x) for x in re.findall(r'\("[a-z]{3}/[a-z\-_]+\.tsv\.bz2", (\d+)\)', src)]
print("tatoeba sizes in source:", tat, "sum primary 7:", sum(tat[:7]), "row4 5 files:", sum(tat[:5]), "links 2:", sum(tat[5:7]), "fallback:", sum(tat[7:]))
for x in tat:
    if f"{x:,}" not in adr: print("  tatoeba size not in ADR:", x); bad += 1
print("total primary download:", prim + sum(tat[:7]))
print("DISCREPANCIES:", bad)
