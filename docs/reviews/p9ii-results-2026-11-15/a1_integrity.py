"""P9-II results audit, part A1: integrity of the registered run (independent code; imports nothing from studies/ or arborlm).

Usage (from the repository root):
    python3 -I docs/reviews/p9ii-results-2026-11-15/a1_integrity.py <repo-root> <raw-run-dir> <experiments-dir> <scratch-dir>

Checks:
  1. code identity: re-derives source/spec/config/frozen-source digests from `git archive` of the freeze commit (and of the
     generation commit a1685d0 and the pre-fix commit 51c00b2) and compares them with every identity field in the run;
  2. committed copies under results/p9ii-run-2026-11-15 equal the raw records byte for byte, and SHA256SUMS holds;
  3. plan.json hashes (calibration, projection, stage caps, draw plan, sixteen data manifests) hold for the raw run dir;
  4. the cell census against ADR-0019 section 5 given the gate decisions; status, update counts, readouts, no re-run;
  5. seeds: registered layout of section 7, init/target/stream seeds per cell; disjointness from calibration/rehearsal seeds;
  6. ledgers and caps (Budget A 4 h, Budget B 3 h, per-stage caps, 3 GiB per worker, 24 GiB aggregate);
  7. gate records (G1, G2, G4, G5, G6) and per-cell G5.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tarfile
import io
import tomllib
from pathlib import Path

REPO, RAW, EXPS, SCRATCH = (Path(a) for a in sys.argv[1:5])
COMMITTED = REPO / "results" / "p9ii-run-2026-11-15"
FREEZE = "d2746d3ba57b9666a6100bda8b5d0e7414883e3a"
GEN = "a1685d019c9bcfe4afe2b55115d6a43ab961d24c"
PREFIX = "51c00b2dc39facf0a07f024cb6fb4c6661caa4c0"
P9_MODULES = ("__init__", "controls", "core", "data", "evaluate", "model", "objective", "pool", "train")
P9I_MODULES = ("__init__", "classes", "core", "evaluate", "model", "report", "stages", "train")
problems: list[str] = []


def say(*a: object) -> None:
    print(*a, flush=True)


def bad(msg: str) -> None:
    problems.append(msg)
    say("PROBLEM:", msg)


def fsha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def cj(obj: object) -> bytes:  # canonical JSON as written in the ADR's records (sorted keys, compact, newline)
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def load(p: Path) -> object:
    return json.loads(p.read_text())


def export(commit: str) -> Path:
    out = SCRATCH / f"tree-{commit[:7]}"
    if not out.exists():
        out.mkdir(parents=True)
        data = subprocess.run(["git", "-C", str(REPO), "archive", commit], check=True, capture_output=True).stdout
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(out, filter="data")
    return out


def identity_of(root: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for p in sorted((root / "studies" / "p9ii").glob("*.py")):
        hashes[f"studies/p9ii/{p.name}"] = fsha(p)
    for p in sorted((root / "studies" / "p9ii" / "launch").glob("*.sh")):
        hashes[f"studies/p9ii/launch/{p.name}"] = fsha(p)
    for n in P9I_MODULES:
        hashes[f"studies/p9i/{n}.py"] = fsha(root / "studies" / "p9i" / f"{n}.py")
    for n in P9_MODULES:
        hashes[f"studies/p9/{n}.py"] = fsha(root / "studies" / "p9" / f"{n}.py")
    src = root / "src" / "arborlm"
    frozen = {f"src/arborlm/{p.relative_to(src).as_posix()}": fsha(p) for p in sorted(src.rglob("*.py"))}
    with (root / "configs" / "p9ii_addressing.toml").open("rb") as s:
        cfg = tomllib.load(s)
    return {
        "source_sha256": hashlib.sha256(cj(hashes)).hexdigest(),
        "spec_sha256": fsha(root / "docs" / "decisions" / "ADR-0019-robust-sparse-address-learning.md"),
        "config_sha256": hashlib.sha256(cj(cfg)).hexdigest(),
        "frozen_source_sha256": hashlib.sha256(cj(frozen)).hexdigest(),
    }


# ---------------------------------------------------------------------------------------------------------------- 1
say("== 1. code identity")
ids = {c: identity_of(export(c)) for c in (FREEZE, GEN, PREFIX)}
for c, v in ids.items():
    say(c[:7], v)
freeze_id = ids[FREEZE]
gen_id = ids[GEN]
# the freeze differs from the generation commit only by the ADR (freeze record), plan.json and stage_caps.json
say("source digest freeze == generation commit:", freeze_id["source_sha256"] == gen_id["source_sha256"])
say("source digest generation commit != pre-fix commit (generate.sh flag):", gen_id["source_sha256"] != ids[PREFIX]["source_sha256"])
diff = subprocess.run(["git", "-C", str(REPO), "diff", "--stat", FREEZE, "HEAD", "--", "studies", "configs", "tests", "src",
                       "docs/decisions"], capture_output=True, text=True, check=True).stdout
say("diff freeze..HEAD in studies/configs/tests/src/docs/decisions:", repr(diff))
if diff.strip():
    bad("code changed between the freeze commit and HEAD")

identity_records: list[tuple[str, dict]] = []
for p in sorted(RAW.glob("cells/*/train.json")) + sorted(RAW.glob("cells/*/eval/*/eval.json")):
    identity_records.append((str(p.relative_to(RAW)), load(p)["identity"]))
for p in sorted(RAW.glob("*/manifest.json")):
    identity_records.append((str(p.relative_to(RAW)), load(p)["identity"]))
identity_records.append(("gates.json", load(RAW / "gates.json")["identity"]))
data_ids = [(str(p.relative_to(RAW)), load(p)["identity"]) for p in sorted(RAW.glob("draws/*/data_manifest.json"))]
# attempt 1 compared the sixteen generate-* stage manifests with the freeze identity; they were written at the generation
# commit a1685d0 (before the freeze commit added the freeze record to the ADR), so they are compared with that identity.
mism = [n for n, i in identity_records if i != (gen_id if n.startswith("generate-") else freeze_id)]
say(f"run records carrying an identity: {len(identity_records)}; equal to the re-derived identity (freeze commit; generate-* at a1685d0): "
    f"{len(identity_records) - len(mism)}")
if mism:
    bad(f"identity mismatch in {len(mism)} records, e.g. {mism[:3]}")
mism_d = [n for n, i in data_ids if i != gen_id]
say(f"data manifests: {len(data_ids)}; equal to the generation commit a1685d0's identity: {len(data_ids) - len(mism_d)}")
if mism_d:
    bad(f"data-manifest identity mismatch {mism_d}")
manifest_stages = sorted(p.parent.name for p in RAW.glob("*/manifest.json"))
say("stage manifests in raw run dir:", manifest_stages)

# ---------------------------------------------------------------------------------------------------------------- 2
say("== 2. committed copies vs raw records")
sums = {}
for line in (COMMITTED / "SHA256SUMS").read_text().splitlines():
    h, name = line.split(None, 1)
    sums[name.removeprefix("./")] = h
committed_files = sorted(str(p.relative_to(COMMITTED)) for p in COMMITTED.rglob("*") if p.is_file() and p.name != "SHA256SUMS")
missing_from_sums = [f for f in committed_files if f not in sums]
bad_sums = [f for f, h in sums.items() if not (COMMITTED / f).exists() or fsha(COMMITTED / f) != h]
say(f"SHA256SUMS entries: {len(sums)}; committed files (excluding SHA256SUMS): {len(committed_files)}; "
    f"not listed: {missing_from_sums}; failing: {bad_sums}")
if bad_sums:
    bad("SHA256SUMS failures")


def raw_of(rel: str) -> Path | None:
    if rel.startswith("cells/"):
        return RAW / rel
    if rel.startswith("manifests/"):
        return RAW / rel.split("/")[1].removesuffix("_manifest.json") / "manifest.json"
    if rel.startswith("P9II-ledger-"):
        return EXPS / rel
    if rel in ("RESULTS.md", "cells.csv", "classes.csv", "results.json"):
        return RAW / "results" / rel
    if rel in ("analysis.json", "gates.json", "stage_gate_1.json", "stage_gate_3.json", "draw_plan.json"):
        return RAW / rel
    return None


unequal, no_raw = [], []
for rel in committed_files:
    r = raw_of(rel)
    if r is None:
        no_raw.append(rel)
        continue
    if not r.exists() or r.read_bytes() != (COMMITTED / rel).read_bytes():
        unequal.append(rel)
say(f"committed files with a raw counterpart: {len(committed_files) - len(no_raw)}; byte-identical: "
    f"{len(committed_files) - len(no_raw) - len(unequal)}; differing: {unequal}")
say("committed files with no raw counterpart (written by the lead):", no_raw)
if unequal:
    bad(f"committed copies differ from raw: {unequal}")
raw_cells = sorted(p.name for p in (RAW / "cells").iterdir())
com_cells = sorted(p.name for p in (COMMITTED / "cells").iterdir())
raw_evals = sorted(str(p.relative_to(RAW)) for p in RAW.glob("cells/*/eval/*/eval.json"))
com_evals = sorted(str(p.relative_to(COMMITTED)) for p in COMMITTED.glob("cells/*/eval/*/eval.json"))
say(f"raw cells {len(raw_cells)}, committed cells {len(com_cells)}, same set: {raw_cells == com_cells}; "
    f"raw eval records {len(raw_evals)}, committed {len(com_evals)}, same set: {raw_evals == com_evals}")
# the manifests' result hashes point at the raw records
mres_bad = []
for p in sorted(RAW.glob("*/manifest.json")):
    for t in load(p).get("tasks", []):
        rp = t.get("result_path")
        if rp and Path(rp).exists() and fsha(Path(rp)) != t["result_sha256"]:
            mres_bad.append(rp)
say("manifest task result_sha256 mismatches against the raw files:", mres_bad)
if mres_bad:
    bad("manifest result hashes do not hold")

# ---------------------------------------------------------------------------------------------------------------- 3
say("== 3. frozen plan")
plan = load(REPO / "studies" / "p9ii" / "freeze" / "plan.json")
checks = {
    "plan.json sha (freeze record b4c057e9...)": fsha(REPO / "studies/p9ii/freeze/plan.json")
    == "b4c057e9739e5f162089eba0f56594461c3b3051f0f7bdd10b9fbaa134fff722",
    "calibration": fsha(REPO / plan["calibration"]["path"]) == plan["calibration"]["sha256"],
    "projection": fsha(REPO / plan["projection"]["path"]) == plan["projection"]["sha256"],
    "stage_caps": fsha(REPO / "studies/p9ii/freeze/stage_caps.json") == plan["stage_caps_sha256"],
    "draw_plan": fsha(RAW / "draw_plan.json") == plan["draw_plan"]["sha256"],
    "run_dir": Path(plan["run_dir"]).resolve() == RAW.resolve(),
}
for name, h in plan["data_manifests"].items():
    checks[f"data manifest {name}"] = fsha(RAW / "draws" / name / "data_manifest.json") == h
for k, v in checks.items():
    if not v:
        bad(f"plan check failed: {k}")
say(f"plan checks: {sum(checks.values())} of {len(checks)} hold")
dp = load(RAW / "draw_plan.json")
say("draw plan ok:", dp["ok"], "replacements:", dp["replacements"], "all G1:", all(dp["g1"].values()), len(dp["g1"]))

# ---------------------------------------------------------------------------------------------------------------- 4
say("== 4. census")
sg1 = load(RAW / "stage_gate_1.json")
sg3 = load(RAW / "stage_gate_3.json")
s2_arms = ["A0", *sg1["advancing"]] + (["A1-S"] if {"A1", "A2"} & set(sg1["advancing"]) else [])
expected = set()
for arm in ["A0", "A1", "A2", "A4", "A5-C", "A5-D", "A1-S"]:
    expected |= {f"S1-{arm}-n4096-d{d:02d}-j{j}" for d in range(1, 9) for j in (0, 1)}
for arm in ["A6", "A7"]:
    expected |= {f"S1-{arm}-n4096-d{d:02d}-j0" for d in range(1, 9)}
for arm in s2_arms:
    expected |= {f"S2-{arm}-n16384-d{d:02d}-j{j}" for d in range(9, 13) for j in (0, 1)}
for arm in ["A6", "A7"]:
    expected |= {f"S2-{arm}-n16384-d{d:02d}-j0" for d in range(9, 13)}
s3_arms = ["A0", "A6", "A7"] if sg3["selected"] == "A0" else ["A0", sg3["selected"], "A6", "A7"]
for arm in s3_arms:
    expected |= {f"S3-{arm}-n65536-d{d:02d}-j0" for d in (13, 14)}
say(f"Stage 2 arms by the gate record: {s2_arms}; Stage 3 arms: {s3_arms}; expected cells {len(expected)}")
say("missing:", sorted(expected - set(raw_cells)), "unexpected:", sorted(set(raw_cells) - expected))
if expected != set(raw_cells):
    bad("census differs from expectation")
task_labels: dict[str, list[str]] = {}
for st in ("train1", "train2", "train3", "evaluate1", "evaluate2", "evaluate3"):
    m = load(RAW / st / "manifest.json")
    labs = [t["label"] for t in m["tasks"]]
    nonzero = [t["label"] for t in m["tasks"] if t["returncode"] != 0 or t["status"] != "completed"]
    task_labels[st] = labs
    say(f"{st}: status {m['status']}, tasks {len(labs)}, unique {len(set(labs))}, non-completed {nonzero}, "
        f"skipped_for_dependency {m['skipped_for_dependency']}, workers {m['workers']}, started {m['started_utc']}, "
        f"finished {m['finished_utc']}")
train_all = task_labels["train1"] + task_labels["train2"] + task_labels["train3"]
say("each cell trained exactly once across stage manifests:", sorted(train_all) == sorted(expected))
logs = {st: sorted(p.name for p in (RAW / st).glob("*.log")) for st in ("train1", "train2", "train3")}
say("train log files per stage:", {k: len(v) for k, v in logs.items()})
upd_bad, ro_bad = [], []
for lab in sorted(expected):
    t = load(RAW / "cells" / lab / "train.json")
    stage = int(lab[1])
    want_upd = 32768 if stage == 2 else 8192
    if t["status"] != "completed" or t["run_updates"] != want_upd or t["reason"] is not None:
        upd_bad.append((lab, t["status"], t["run_updates"]))
    ro = sorted(p.name for p in (RAW / "cells" / lab / "eval").iterdir())
    want_ro = ["u0008192", "u0032768"] if stage == 2 else ["u0008192"]
    if ro != want_ro:
        ro_bad.append((lab, ro))
    n_upd = sum(1 for _ in (RAW / "cells" / lab / "updates.jsonl").open()) if (RAW / "cells" / lab / "updates.jsonl").exists() else None
    if n_upd is not None and n_upd != want_upd:
        upd_bad.append((lab, "updates.jsonl lines", n_upd))
say("cells with wrong status/update count:", upd_bad)
say("cells with wrong readouts:", ro_bad)
if upd_bad or ro_bad:
    bad("cell status/readouts")

# ---------------------------------------------------------------------------------------------------------------- 5
say("== 5. seeds")
seed_bad = []
for lab in sorted(expected):
    t = load(RAW / "cells" / lab / "train.json")
    d, j = t["draw"], t["seed_index"]
    base = 190001 + 100 * (d - 1)
    want = {"seed_set": f"p9ii-draw-{d}", "init_seed": 1901 + j, "target_seed": base + 40 + j, "stream_seed": base + 60 + j}
    got = {k: t[k] for k in want}
    if got != want:
        seed_bad.append((lab, got, want))
    lab_d, lab_j = int(lab.split("-d")[1][:2]), int(lab[-1])
    if (lab_d, lab_j) != (d, j):
        seed_bad.append((lab, "label vs record", d, j))
    stage = int(lab[1])
    if not ((stage == 1 and 1 <= d <= 8) or (stage == 2 and 9 <= d <= 12) or (stage == 3 and d in (13, 14))):
        seed_bad.append((lab, "draw outside its stage", d))
say("cells whose seeds differ from section 7:", seed_bad)
if seed_bad:
    bad("seed layout")
layout_bad = []
registered_seeds: set[int] = set()
for k in range(1, 17):
    name = f"p9ii-draw-{k}" if k <= 14 else f"p9ii-reserve-{k - 14}"
    base = 190001 + 100 * (k - 1)
    s = load(RAW / "draws" / name / "data_manifest.json")["seeds"]
    scalars = sorted(v for kk, v in s.items() if isinstance(v, int))
    if scalars != list(range(base, base + 14)) or s["null_seeds_a"] != [base + 14, base + 15, base + 16] or s[
        "null_seeds_b"
    ] != [base + 17, base + 18, base + 19]:
        layout_bad.append(name)
    registered_seeds |= set(scalars) | set(s["null_seeds_a"]) | set(s["null_seeds_b"]) | {base + 40, base + 41, base + 60, base + 61}
say("data seed sets violating the base+0..19 layout:", layout_bad)
# every other P9II run directory (calibration, rehearsals, attempt 1): collect their seeds
other: dict[str, set[int]] = {}
for d in sorted(EXPS.glob("P9II*")):
    if d.resolve() == RAW.resolve() or not d.is_dir():
        continue
    seeds: set[int] = set()
    for p in d.rglob("data_manifest.json"):
        s = load(p)["seeds"]
        seeds |= {v for v in s.values() if isinstance(v, int)} | set(s.get("null_seeds_a", [])) | set(s.get("null_seeds_b", []))
    inits = set()
    for p in d.rglob("train.json"):
        t = load(p)
        inits.add(t.get("init_seed"))
        seeds |= {t.get("target_seed"), t.get("stream_seed")} - {None}
    other[d.name] = seeds
    say(f"{d.name}: data/target/stream seeds {len(seeds)} (range {min(seeds) if seeds else None}..{max(seeds) if seeds else None}),"
        f" init seeds {sorted(x for x in inits if x is not None)}, overlap with registered {sorted(seeds & registered_seeds)}")
    if seeds & registered_seeds or (inits & {1901, 1902}):
        bad(f"seed overlap with {d.name}")

# ---------------------------------------------------------------------------------------------------------------- 6
say("== 6. ledgers and caps")
caps = load(REPO / "studies/p9ii/freeze/stage_caps.json")
la, lb = load(EXPS / "P9II-ledger-A.json"), load(EXPS / "P9II-ledger-B.json")
sa = sum(e["seconds"] for e in la["entries"])
sb = sum(e["seconds"] for e in lb["entries"])
say(f"Budget A charged {sa:.1f} s of {la['cap_seconds']} (entries {len(la['entries'])}); Budget B charged {sb:.1f} s of "
    f"{lb['cap_seconds']} (entries {len(lb['entries'])})")
reg_a = [e for e in la["entries"] if e["run"] == RAW.name]
say("Budget A registered-run entries:", [(e["stage"], round(e["seconds"], 1)) for e in reg_a])
pre_stage1 = sum(e["seconds"] for e in la["entries"] if e["utc"] < "2026-11-15T08:48")
s1_cap = caps["stage1"]["train"] + caps["stage1"]["evaluate"]
say(f"Budget A charged before Stage 1: {pre_stage1:.1f} s; Stage 1 doubled projection (cap) {s1_cap:.1f} s; fits in "
    f"remaining {14400 - pre_stage1:.1f} s: {s1_cap <= 14400 - pre_stage1}")
config = "+".join(a for a in sg1["advancing"]) if sg1["advancing"] else "A0-only"
# the cap table is keyed in the advance order
keys = [k for k in caps["stage2"] if set(k.split("+")) == set(sg1["advancing"])]
s2_key = keys[0] if keys else None
s2_cap = caps["stage2"][s2_key]["train"] + caps["stage2"][s2_key]["evaluate"]
say(f"Stage 2 configuration {sg1['advancing']} -> cap-table key {s2_key}: doubled projection {s2_cap:.1f} s; "
    f"gate record required {sg1['budget']['required_seconds']:.1f} s; within 10,800 s: {s2_cap <= 10800}")
s2_charged = sum(e["seconds"] for e in lb["entries"] if e["stage"] in ("train2", "evaluate2"))
s3_cap = caps["stage3"][sg3["selected"]]["train"] + caps["stage3"][sg3["selected"]]["evaluate"]
say(f"Stage 2 charged {s2_charged:.1f} s; Budget B remaining {10800 - s2_charged:.1f} s (gate record "
    f"{sg3['budget']['remaining_seconds']:.1f}); Stage 3 ({sg3['selected']}) doubled projection {s3_cap:.1f} s; fits: "
    f"{s3_cap <= 10800 - s2_charged}")
stage_caps = {"train1": caps["stage1"]["train"], "evaluate1": caps["stage1"]["evaluate"], "train2": caps["stage2"][s2_key]["train"],
              "evaluate2": caps["stage2"][s2_key]["evaluate"], "train3": caps["stage3"][sg3["selected"]]["train"],
              "evaluate3": caps["stage3"][sg3["selected"]]["evaluate"], "gates": caps["gates"], "analyze": caps["analysis"],
              "report": caps["report"]}
peak_all = 0
for st, cap in stage_caps.items():
    m = load(RAW / st / "manifest.json")
    charged = [e["seconds"] for e in la["entries"] + lb["entries"] if e["run"] == RAW.name and e["stage"] == st]
    peaks = [t.get("peak_rss_bytes") or 0 for t in m["tasks"]]
    peak_all = max(peak_all, max(peaks))
    agg = max(peaks) * m["workers"]
    say(f"{st}: charged {charged} s, cap {cap:.1f} s (manifest cap {m['caps']['stage_seconds']:.1f}), within: "
        f"{all(c <= cap for c in charged)}; max task peak RSS {max(peaks) / 2**30:.3f} GiB (cap 3); workers {m['workers']}; "
        f"workers x max peak {agg / 2**30:.2f} GiB (cap 24)")
    if any(c > cap for c in charged) or max(peaks) > 3 * 2**30 or agg > 24 * 2**30:
        bad(f"cap exceeded in {st}")
    if abs(m["caps"]["stage_seconds"] - cap) > 1e-6:
        bad(f"{st}: manifest cap differs from the frozen table")
cell_peak = max(load(p)["peak_rss_bytes"] for p in RAW.glob("cells/*/train.json"))
say(f"largest per-cell training peak RSS {cell_peak / 2**30:.3f} GiB; largest task peak {peak_all / 2**30:.3f} GiB")

# ---------------------------------------------------------------------------------------------------------------- 7
say("== 7. gates")
g = load(RAW / "gates.json")
say({k: g[k] for k in ("g1_passed", "g2_passed", "g4_passed", "g4_defects", "g5_passed", "g6_passed", "dry")})
say("G1 by draw all:", all(g["g1_by_draw"].values()), "G2 by draw all:", all(g["g2_by_draw"].values()))
say("G2 results:", [(r["name"], r["correct"], r["interval"], r["inside"]) for r in g["g2"]["results"]])
g5_bad = [str(p.relative_to(RAW)) for p in RAW.glob("cells/*/eval/*/eval.json") if not load(p)["g5"]["passed"]]
say("eval records with G5 not passed:", g5_bad)
if not all(g[k] for k in ("g1_passed", "g2_passed", "g4_passed", "g5_passed", "g6_passed")) or g5_bad or g["dry"]:
    bad("gate failure")
say("gate-record mode dry:", g["dry"], "; G4 a2 schedule u_pre in gate test:", g["checks"]["schedules"]["a2"]["u_pre"])

say("\n== SUMMARY: problems found:", len(problems))
for p in problems:
    say(" -", p)
