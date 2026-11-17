"""Audit A, check 6b: the reviewer's saved Hub records (adr-0022-review/web, read-only, no network) give the git-blob SHA-1 of every small file
the fetch needs; the saved config.json copies are checked against those blob ids and for the advisory's key. Written by the auditor (Claude Opus 5.5).
Run from the pinned tree:  <python> <this file>
"""

import hashlib
import json
import sys
from pathlib import Path

PIN = Path.cwd()
sys.path.insert(0, str(PIN))
sys.path.insert(0, str(PIN / "src"))
from studies.p10s2 import fetch_guard as g  # noqa: E402

W = PIN / "docs/reviews/p10-design-2026-11-15/adr-0022-review/web"
out: list[str] = []


def say(s: str) -> None:
    out.append(s)
    print(s)


def blob(b: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()  # noqa: S324


for label, prefix, (repo, rev), files, big in (
    ("teacher_a", "opus_en-de", g.TEACHER_A, g.MARIAN_FILES, "pytorch_model.bin"),
    ("teacher_b", "opus_en-fr", g.TEACHER_B, g.MARIAN_FILES, "pytorch_model.bin"),
    ("student", "smol", g.STUDENT, g.STUDENT_FILES, "model.safetensors"),
    ("fallback", "opus_en-es", g.FALLBACK, g.MARIAN_FILES, "pytorch_model.bin"),
):
    revrec = json.loads((W / f"{prefix}_rev.json").read_text()) if (W / f"{prefix}_rev.json").exists() else {}
    tree = json.loads((W / f"{prefix}_tree.json").read_text())
    by = {e["path"]: e for e in tree}
    say(f"== {label} {repo}: saved rev record sha = {revrec.get('sha')}; pinned {rev}; equal: {revrec.get('sha') == rev}")
    lfs = by.get(big, {}).get("lfs", {})
    say(f"   {big}: tree lfs sha256 {lfs.get('oid')} size {lfs.get('size')}; pinned {g.LARGE[f'{label}/{big}']}; equal: {(lfs.get('oid'), lfs.get('size')) == tuple(g.LARGE[f'{label}/{big}'])}")
    for f in files:
        e = by.get(f)
        say(f"   {f}: git-blob sha1 {e['oid'] if e else 'ABSENT FROM SAVED TREE'} size {e['size'] if e else '-'}{' (LFS: ' + e['lfs']['oid'] + ')' if e and 'lfs' in e else ''}")
    cfgp = W / f"{prefix}_config.json"
    if cfgp.exists():
        b = cfgp.read_bytes()
        say(f"   saved config.json blob {blob(b)}; equals tree's: {blob(b) == by.get('config.json', {}).get('oid')}; contains '_attn_implementation': {'_attn_implementation' in b.decode()}")
Path(__file__).with_suffix(".out.txt").write_text("\n".join(out) + "\n")
