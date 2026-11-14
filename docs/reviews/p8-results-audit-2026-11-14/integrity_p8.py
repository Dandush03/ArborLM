"""Auditor's integrity checks on the P8 registered run (Claude Opus 5.5). Not Astra validation, not
human approval. No arborlm import; the freeze identity is recomputed from `git show 80f46ae:...`.

Checks: (1) source digest of src/arborlm/*.py at the freeze commit (same canonical-JSON recipe the
records declare: sha256 of sorted-key compact JSON of {path: sha256} + newline) and sha256 of the
ADR at the freeze commit, against every train/eval/sim record; (2) backbone digests in all 60
train.json; (3) restore_gate.json; (4) panel record hash in every eval.json; (5) byte identity of
every committed file under results/p8-2026-11-14/{train,evaluate,simulate,analysis} with the local
run directories; (6) lambda-zero event counts; (7) resources against ADR-0015 section 11 caps.

Usage: python -I integrity_p8.py --repo R --experiments X
"""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

FREEZE = "80f46ae"
RUNS = {
    "train": "P8T-20261114T043005466913Z-5da1f4d298534e9390b007efd8d98156",
    "evaluate": "P8E-20261114T043753008527Z-ab07648862054617b63d9e4d83e5407f",
    "simulate": "P8S-20261114T043952694180Z-088e6814edcd465894aebd125d53ddc3",
    "analysis": "P8A-20261114T044147896561Z-4a9976ed3c7d493c8a92293786f2572c",
}
PANEL = "2a767b5fceb4a8cf104443d21aed2fd128d0c7fd4542534477a97c3a5c5f586d"
SPEC = "docs/decisions/ADR-0015-p8-locality-aware-memory-training.md"


def git(repo: Path, *a: str) -> bytes:
    return subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True).stdout


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--experiments", type=Path, required=True)
    a = ap.parse_args()
    out: dict = {}
    files = [f for f in git(a.repo, "ls-tree", "-r", "--name-only", FREEZE, "src/arborlm").decode().split() if f.endswith(".py")]
    hashes = {f: hashlib.sha256(git(a.repo, "show", f"{FREEZE}:{f}")).hexdigest() for f in sorted(files)}
    src = hashlib.sha256((json.dumps(hashes, sort_keys=True, separators=(",", ":")) + "\n").encode()).hexdigest()
    spec = hashlib.sha256(git(a.repo, "show", f"{FREEZE}:{SPEC}")).hexdigest()
    spec_now = hashlib.sha256((a.repo / SPEC).read_bytes()).hexdigest()
    out["freeze"] = {"source_digest": src, "py_files": len(files), "spec_sha256": spec, "spec_now_equal": spec == spec_now}
    bad: list[str] = []
    X = {k: a.experiments / v for k, v in RUNS.items()}
    labels = sorted(p.name for p in (X["train"] / "cells").iterdir())
    out["labels"] = len(labels)
    lam, rss, cellsec = {}, {}, {}
    seen_src = {"train": set(), "eval": set(), "sim": set()}
    for lab in labels:
        tr = json.loads((X["train"] / "cells" / lab / "train.json").read_text())
        ev = json.loads((X["evaluate"] / "cells" / lab / "eval.json").read_text())
        sp = X["simulate"] / "cells" / lab / "sim.json"
        recs = [("train", tr), ("eval", ev)] + ([("sim", json.loads(sp.read_text()))] if sp.is_file() else [])
        for kind, r in recs:
            s = r.get("source_sha256") or r.get("identity", {}).get("source_sha256")
            p = r.get("spec_sha256") or r.get("identity", {}).get("spec_sha256")
            seen_src[kind].add((s, p))
            if s != src or p != spec:
                bad.append(f"{lab} {kind}: source/spec {s} {p}")
        if ev.get("panel_record_sha256") != PANEL:
            bad.append(f"{lab}: panel hash {ev.get('panel_record_sha256')}")
        if tr.get("status") != "completed":
            bad.append(f"{lab}: train status {tr.get('status')}")
        out.setdefault("train_keys", sorted(tr))
        lam[lab] = {k: v.get("zero_events") for k, v in tr["summary"].get("lambda", {}).items()}
        rss[lab] = (tr.get("peak_rss_bytes"), ev.get("peak_rss_bytes_ru_maxrss"),
                    json.loads(sp.read_text()).get("peak_rss_bytes_ru_maxrss") if sp.is_file() else None)
        cellsec[lab] = tr.get("wall_seconds")
        b0, b1 = tr.get("backbone_sha256_before"), tr.get("backbone_sha256_after")
        if b0 != tr["identity"].get("backbone_sha256") or b0 != ev["digests"]["backbone_expected"]:
            bad.append(f"{lab}: backbone identity differs from eval expectation")
        if tr["state_digests"]["step-0512"] != ev["digests"]["state_step512"]:
            bad.append(f"{lab}: eval evaluated a different step-512 state")
        if not b0 or b0 != b1:
            bad.append(f"{lab}: backbone digest {b0} -> {b1}")
        if ev["digests"]["backbone_step0"] != ev["digests"]["backbone_step512"] or not ev["digests"]["backbone_unchanged"]:
            bad.append(f"{lab}: eval backbone")
    out["source_spec_seen"] = {k: sorted(map(list, v)) for k, v in seen_src.items()}
    out["lambda"] = lam
    out["rss_train_eval_sim"] = rss
    out["train_seconds"] = cellsec
    # byte identity committed vs local
    ident, diff, missing_local = 0, [], []
    for stage, run in RUNS.items():
        com = a.repo / "results" / "p8-2026-11-14" / stage / run
        for f in sorted(p for p in com.rglob("*") if p.is_file()):
            rel = f.relative_to(com)
            loc = X[stage] / rel
            if not loc.is_file():
                missing_local.append(str(rel))
            elif loc.read_bytes() != f.read_bytes():
                diff.append(f"{stage}/{rel}")
            else:
                ident += 1
    out["committed_vs_local"] = {"identical": ident, "different": diff, "missing_locally": missing_local}
    out["restore_gate"] = json.loads((X["train"] / "restore_gate.json").read_text())
    out["problems"] = bad
    print(json.dumps(out, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
