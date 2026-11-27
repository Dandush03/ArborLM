"""Copy auditor, step 6: (a) the SHA-256 pairs recorded in the four COPIES.md and in the four plans against mine (copy_hashes.json);
(b) end-of-file bytes of original and copy (a1 printed this wrongly: its f-string compared with a two-character backslash-n; see COPY_AUDIT.md);
(c) every changed line is not whitespace-only. python3 -I a6_hash_records.py"""
import hashlib, json, re, subprocess, difflib
from pathlib import Path
H = Path(__file__).resolve().parent
WT = Path("/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f")
C = "b78e58b1f47619f070dfc6c0a88999d345b1a34b"
mine = json.loads((H / "copy_hashes.json").read_text())
out = []
NL = b"\n"
for cp, e in sorted(mine.items()):
    a = subprocess.run(["git", "-C", str(WT), "show", f"{C}:{e['original_path']}"], capture_output=True, check=True).stdout
    b = (WT / cp).read_bytes()
    assert hashlib.sha256(a).hexdigest() == e["original_sha256"] and hashlib.sha256(b).hexdigest() == e["copy_sha256"]
    ws = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a.decode().splitlines(), b=b.decode().splitlines(), autojunk=False).get_opcodes():
        if tag == "replace":
            x = a.decode().splitlines()[i1:i2]; y = b.decode().splitlines()[j1:j2]
            if ["".join(s.split()) for s in x] == ["".join(s.split()) for s in y]: ws.append((i1, j1))
    out.append(f"{cp}: orig ends with newline {a.endswith(NL)}, copy {b.endswith(NL)}; whitespace-only replaced hunks {ws}")
for ev in ("r1", "r2", "m1", "c1"):
    md = (WT / f"studies/m0/fresh_run/{ev}/COPIES.md").read_text()
    shas = re.findall(r"[0-9a-f]{64}", md)
    plan = (WT / f"studies/m0/fresh_run/{ev}/run_plan_{ev}.json").read_text()
    pshas = set(re.findall(r"[0-9a-f]{64}", plan))
    for cp, e in sorted(mine.items()):
        if f"/{ev}/" not in cp: continue
        okmd = e["original_sha256"] in shas and e["copy_sha256"] in shas
        okplan = e["copy_sha256"] in pshas
        out.append(f"{ev}: {Path(cp).name}: both hashes in COPIES.md {okmd}; copy hash in plan {okplan}; original hash in plan {e['original_sha256'] in pshas}")
    unknown = [s for s in set(shas) if s not in {v for e in mine.values() for v in (e['original_sha256'], e['copy_sha256'])}]
    out.append(f"{ev}: hashes in COPIES.md that are not copy/original hashes: {unknown}")
txt = "\n".join(out) + "\n"
(H / "a6_hash_records.out.txt").write_text(txt)
print(txt)
