# ruff: noqa: E501
"""P10IS6 end to end on tiny synthetic inputs, through the REAL launch scripts, in a throw-away git repository (a copy of the code with an injected configuration: tiny ladder, a [synthetic] section, a stub seed checker).
Chain: fetch (fixture, a copy of the ledger of record) -> D0 -> parents and identity gate (synthetic) -> R1 -> write-rate-table -> R2 (measuring, provisional caps) -> candidate plan (caps from R2) -> R3 (counting, DRY) -> freeze ->
Decision 2 -> registered launches of gates, train, eval, analysis and report. Then: freeze accepts or refuses rehearsal records; the registered launch scripts refuse without a freeze and without a committed Decision 2; the real
``caffeinate`` process tree on this platform; the public whitelist. The only stand-in is a ``uv`` shim on PATH that runs the locked environment's python (the real ``uv run --locked`` would try to sync a venv in the copy);
every launch script runs unmodified. Self-check only."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from studies.p10i_s6 import calibration, core, d0, fetch, parents, testing

REAL = core.repo_root()
RELAXED = 3000  # seconds for any one launch


def run(cmd: list[str], cwd: Path, env: dict[str, str], timeout: int = RELAXED) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout, check=False)  # noqa: S603


def git(repo: Path, *a: str) -> str:
    return subprocess.run(["git", "-C", str(repo), "-c", "commit.gpgsign=false", "-c", "user.email=t@example.invalid", "-c", "user.name=t", *a], capture_output=True, text=True, check=True).stdout.strip()  # noqa: S603, S607


def tail(o: subprocess.CompletedProcess[str]) -> str:
    return (o.stdout[-1200:] + "\n" + "\n".join(x for x in o.stderr.splitlines() if "NumPy" not in x and "_conversion_method" not in x)[-1500:])


class Chain:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.repo = root / "repo"
        self.pub = self.repo / "experiments" / "e2e_run"
        self.sealed = self.repo / "experiments" / "e2e_sealed"
        shim = root / "bin"
        shim.mkdir()
        (shim / "uv").write_text(f'#!/bin/sh\nshift 3\nexec {sys.executable} "$@"\n', encoding="utf-8")  # uv run --locked python ARGS -> the locked environment's python
        (shim / "uv").chmod(0o755)
        self.env = {**os.environ, "PATH": f"{shim}:{os.environ['PATH']}", "PYTHONDONTWRITEBYTECODE": "1"}
        self.log: dict[str, Any] = {}
        self.build_repo()

    def build_repo(self) -> None:
        r = self.repo
        r.mkdir()
        for d in ("src/arborlm", "studies", "configs"):
            shutil.copytree(REAL / d, r / d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "freeze", "superseded"))
        (r / "tests").mkdir()
        for f in (REAL / "tests").glob("test_p10i_s6_*.py"):
            shutil.copy(f, r / "tests" / f.name)
        (r / "studies/p10i_s6/freeze").mkdir(parents=True, exist_ok=True)
        for f in ("pyproject.toml", "uv.lock", ".gitignore"):
            shutil.copy(REAL / f, r / f)
        (r / "docs/decisions").mkdir(parents=True)
        shutil.copy(REAL / core.SPEC, r / core.SPEC)
        shutil.copy(REAL / "docs/decisions/ADR-0031-addendum-implementation-rulings.md", r / "docs/decisions/ADR-0031-addendum-implementation-rulings.md")
        (r / "docs/reviews").mkdir(parents=True)
        stub = r / "docs/reviews/checker_stub.py"
        rows = "".join(f'    ("P10-I-S6 ADR-0031", "row{i}", {lo}, {hi}),\n' for i, (lo, hi) in enumerate([(320001, 329299), (330701, 330799), (952001, 952999)]))
        stub.write_text(f'ALLOC = [\n{rows}]\nprint("RESULT: PASS")\n', encoding="utf-8")
        add = r / "docs/reviews/addendum_stub.md"
        add.write_text("stub addendum\n", encoding="utf-8")
        cfg_path = r / core.CONFIG
        t = cfg_path.read_text(encoding="utf-8")
        for a, b in (
            ("base_updates = 16384", "base_updates = 2"), ("below_updates = 8192", "below_updates = 1"), ("workers = 6", "workers = 4"), # wide grid: tiny runs on learnable bytes need large rates for an interior minimiser
            ("grid = [0.0001, 0.0003, 0.001, 0.003, 0.01, 0.03, 0.1]", "grid = [0.001, 0.01, 0.1, 1.0, 10.0, 100.0, 1000.0]"), ("r2_updates = 2048", "r2_updates = 6"), ("r2_min_updates = 2048", "r2_min_updates = 6"), ("dry_base_updates = 8", "dry_base_updates = 2"), ("dry_below_updates = 4", "dry_below_updates = 1"),
            ('checker = "docs/reviews/p10-i-direction-2026-11-17/seed_registry_check_r4.py"', 'checker = "docs/reviews/checker_stub.py"'),
            ('checker_sha256 = "7bc791e0f24528020b9c3f569751f6528f30444a761b6bae514efad96acd81e8"', f'checker_sha256 = "{hashlib.sha256(stub.read_bytes()).hexdigest()}"'),
            ('addendum = "docs/reviews/p10-i-direction-2026-11-17/SEED_REGISTRY_R4.md"', 'addendum = "docs/reviews/addendum_stub.md"'),
            ('addendum_sha256 = "d1d22cc45d12b0bfa2856aed00ce7e2d1cbf1eef14c366b8abcea4b7237cab7f"', f'addendum_sha256 = "{hashlib.sha256(add.read_bytes()).hexdigest()}"'),
        ):
            assert a in t, a
            t = t.replace(a, b)
        cfg_path.write_text(t + "\n[synthetic]\nregistered_pool = 200\ncalibration_pool = 100\nk_max = 2\n", encoding="utf-8")
        git(r, "init", "-q")
        git(r, "add", "-A")
        git(r, "commit", "-q", "-m", "copy for the end-to-end test")

    def script(self, name: str, *args: str) -> subprocess.CompletedProcess[str]:
        return run([str(self.repo / "studies/p10i_s6/launch" / name), *args], self.repo, self.env)

    def stages(self, *args: str) -> subprocess.CompletedProcess[str]:
        return run([sys.executable, "-m", "studies.p10i_s6.stages", *args], self.repo, self.env)

    def head(self) -> str:
        return git(self.repo, "rev-parse", "HEAD")

    # ---- the chain -----------------------------------------------------------------------------------------------------------
    def step_fetch_d0_parents(self) -> None:
        cfg = core.load_config(self.repo / core.CONFIG)
        files = {"train-00000-of-00002.parquet": b"a" * 900, "train-00001-of-00002.parquet": b"b" * 700}
        pins = {"repo": cfg["data"]["publisher_repo"], "revision": cfg["data"]["revision"], "configuration": cfg["data"]["configuration"], "files": [{"name": n, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()} for n, b in sorted(files.items())]}
        ledger = self.root / "ledger_copy.md"
        ledger.write_text((REAL / fetch.DOWNLOAD_LEDGER).read_text())

        def dl(url: str, part: Path, limit: int) -> int:
            part.write_bytes(files[url.split("?")[0].rsplit("/", 1)[1]])
            return part.stat().st_size

        self.log["fetch"] = fetch.get(self.root / "wt103", ledger, cfg, pins, dl, root=self.repo)
        import random

        rng = random.Random(1)

        def txt(n: int) -> str:
            return "".join(rng.choice("abcdefghij \n") for _ in range(n))

        def wiki(n_art: int, n: int) -> list[str]:
            rows = [txt(200)]
            for a in range(n_art):
                rows += [f" = A {a} {rng.random()} = \n", *(txt(n) for _ in range(3))]
            return rows

        led = self.root / "panel_ledger.json"
        led.write_text(json.dumps({"format": d0.LEDGER_FORMAT, "p10is2": {"end_exclusive": True}, "windows": []}, sort_keys=True, separators=(",", ":")) + "\n")  # the real format
        small = json.loads(json.dumps({"ladder": {**cfg["ladder"], "base_updates": 1, "below_updates": 1}}))
        dcfg = {**dict(cfg), "ladder": small["ladder"], "data": {**cfg["data"], "pool_chunks_for_umax": 128, "panel_walk_start": 0}, "setting": {**cfg["setting"], "panel_chunks": 8}}
        self.log["d0"] = d0.prepare(iter(wiki(120, 300)), wiki(10, 300), wiki(12, 400), led, self.root / "d0out", dcfg)
        rows = testing.random_rows(4096, core.test_seed(10, cfg))
        recorded = {p: parents.train_backbone(*core.old_parent_ids(p), rows, steps=2, control_memory=201)[1] for p in range(9)}  # the old recipe's digests (the real run reads them from the P4 records)
        gate = parents.identity_gate(self.repo, rows, cfg, steps=2, recorded=recorded)
        assert gate["passed"] and gate["control_memory"] is None
        reg = parents.train_new_parents(cfg, rows, self.root / "parents", group="registered", identity=gate, steps=2)
        calp = parents.train_new_parents(cfg, rows, self.root / "parents", group="calibration", identity=gate, steps=2)
        self.log["parents"] = (len(reg), len(calp))

    def step_rehearsals_and_freeze(self) -> None:
        syn = self.root / "syn.json"
        syn.write_text(json.dumps({"cfg_override": {}}))
        common = ["--run-dir", str(self.pub), "--sealed-dir", str(self.sealed), "--synthetic-json", str(syn)]
        self.log["r1"] = self.script("rehearse.sh", "r1", *common)
        assert self.log["r1"].returncode == 0, tail(self.log["r1"])
        self.log["rate_table_cmd"] = self.stages("write-rate-table", "--public", str(self.pub / "rehearsal_public.json"))
        assert self.log["rate_table_cmd"].returncode == 0, self.log["rate_table_cmd"].stderr
        self.log["r2"] = self.script("rehearse.sh", "r2", *common, "--k-max", "2")
        assert self.log["r2"].returncode == 0, tail(self.log["r2"])
        self.log["cand"] = self.stages("candidate-plan", "--run-dir", str(self.pub), "--k-max", "2", "--synthetic", "--r2", str(self.pub / "r2" / "r2_record.json"))
        assert self.log["cand"].returncode == 0, tail(self.log["cand"])
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "candidate plan and rate table")
        self.log["r3"] = self.script("rehearse.sh", "r3", *common)
        assert self.log["r3"].returncode == 0, tail(self.log["r3"])

    def freeze(self, rehearsal: Path) -> subprocess.CompletedProcess[str]:
        return self.stages("freeze", "--rehearsal", str(rehearsal), "--r2-record", str(self.pub / "r2" / "r2_record.json"))


@pytest.fixture(scope="module")
def chain() -> Iterator[Chain]:
    with testing.scratch("e2e") as d:
        c = Chain(d)
        c.step_fetch_d0_parents()
        c.step_rehearsals_and_freeze()
        yield c


def public(c: Chain) -> dict[str, Any]:
    return core.read_record(c.pub / "rehearsal_public.json", "rehearsal_public")


def test_chain_fetch_d0_parents_and_rehearsals(chain: Chain) -> None:
    assert chain.log["fetch"]["total_bytes"] == 1600 and chain.log["d0"]["gates"]["overlap_with_E"]["passed"] and chain.log["parents"] == (9, 3)
    pub = public(chain)
    assert {s: v["status"] for s, v in pub["stages"].items()} == {"R1": "COMPLETE", "R2": "COMPLETE", "R3": "COMPLETE"} and pub["caps_provisional"] is False
    assert calibration.public_guard({k: v for k, v in pub.items() if k != "whitelist_note"}) == []  # the public file holds no measured value
    assert set(pub["rate_table"]["rates"]) == {"M-FLAT", "D-ADAPT"} and all(all(v.values()) for v in pub["rate_table"]["interior"].values())
    assert pub["gates"]["planted_positive"] is True and all(pub["gates"]["identity"].values()) and all(pub["gates"]["neg_ref"].values())
    assert len(pub["sealed_sha256"]) == 64 and (chain.sealed / "rehearsal_sealed.json").is_file()
    sealed = (chain.sealed / "rehearsal_sealed.json").read_bytes()
    assert calibration.check_public_against_sealed(pub, sealed, core.load_config(chain.repo / core.CONFIG))["result"] == "agree"
    r2 = json.loads((chain.pub / "r2" / "r2_record.json").read_text())
    assert r2["caps_provisional"] is True and r2["unit_costs"]["process_overhead_seconds"] > 0  # whole processes, overhead separate from the per-unit rates
    for o in (chain.log["r1"], chain.log["r2"], chain.log["r3"]):
        text = (o.stdout + o.stderr).lower()
        assert not any(w in text for w in ("nll", "mean_q", "delta ")), "a rehearsal prints no measured value"
    plan = json.loads((chain.repo / core.PLAN).read_text())
    assert plan["caps_provisional"] is False and plan["caps"]["registered_hours"] == 2.0 * plan["projection"]["hours"] and plan["synthetic"] is True
    assert hashlib.sha256((chain.repo / core.PLAN).read_bytes()).hexdigest() == public(chain)["candidate"]["plan_file_sha256"]  # R3 names this exact plan file
    starts = sorted((chain.pub / "stage_starts").glob("*.json"))
    assert starts and all("load_average" in json.loads(p.read_text()) for p in starts)
    names = {n for p in starts for n in json.loads(p.read_text())["own_family_names"]}
    assert "caffeinate" in names  # the real keep-awake watcher of the launch script is part of the stage's own family (macOS)


def test_freeze_refusals_then_acceptance_then_registered_launch(chain: Chain) -> None:
    repo, pub_file = chain.repo, chain.pub / "rehearsal_public.json"
    good = json.loads(pub_file.read_text())

    def with_changes(name: str, **ch: Any) -> Path:
        rec = json.loads(json.dumps(good))
        for k, v in ch.items():
            if k == "R":
                rec["stages"].update(v)
            elif v is None:
                rec.pop(k, None)
            else:
                rec[k] = v
        p = chain.root / f"{name}.json"
        p.write_text(json.dumps(rec))
        return p

    cases = {
        "provisional": (with_changes("provisional", caps_provisional=True), "provisional"),
        "other_plan": (with_changes("other", candidate={"plan_file_sha256": "0" * 64}), "SHA-256"),
        "over_cap": (with_changes("overcap", R={"R3": {"status": "PAUSED"}}), "COMPLETE"),
        "missing_stage": (with_changes("missing", R={"R2": {"status": "NOT RUN"}}), "COMPLETE"),
        "not_interior": (with_changes("edge", rate_table={**good["rate_table"], "interior": {**good["rate_table"]["interior"], "M-FLAT": {**good["rate_table"]["interior"]["M-FLAT"], "1": False}}}), "not interior"),
    }
    for name, (path, word) in cases.items():
        o = chain.freeze(path)
        assert o.returncode == 2 and word in o.stderr, (name, o.stderr)
        assert not (repo / core.FREEZE_RECORD).exists()
    # ruling 18 (audit R7): the plan's unit costs and caps are tied to R2's record by SHA-256; a different record, or a typed unit cost, is refused
    r2 = json.loads((chain.pub / "r2" / "r2_record.json").read_text())
    r2["unit_costs"]["process_overhead_seconds"] += 1.0
    other = chain.root / "r2_other.json"
    other.write_text(json.dumps(r2))
    o = chain.stages("freeze", "--rehearsal", str(pub_file), "--r2-record", str(other))
    assert o.returncode == 2 and "R2" in o.stderr and not (repo / core.FREEZE_RECORD).exists()
    o = chain.freeze(pub_file)
    assert o.returncode == 0, o.stdout + o.stderr
    assert chain.freeze(pub_file).returncode == 2  # written once
    # the registered launch scripts refuse without a committed Decision 2, and (before the freeze commit) without a freeze
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "freeze record")
    freeze_commit = chain.head()
    for st in ("gates", "train", "eval", "analysis", "report"):
        o = chain.script(f"{st}.sh", str(chain.pub), freeze_commit)
        assert o.returncode == 2 and "Decision 2" in o.stderr, (st, o.stderr)
    d2 = repo / "results" / "p10i-s6-freeze-test"
    d2.mkdir(parents=True)
    (d2 / "DECISION_2.md").write_text(f"DECISION: DO NOT RUN\n{freeze_commit}\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "decision 2: do not run")
    assert chain.script("gates.sh", str(chain.pub), freeze_commit).returncode == 2
    (d2 / "DECISION_2.md").write_text(f"DECISION: RUN\n{freeze_commit}\n")
    git(repo, "commit", "-qam", "decision 2: run")
    dirty = repo / "stray.txt"
    dirty.write_text("x")
    o = chain.script("gates.sh", str(chain.pub), freeze_commit)
    assert o.returncode == 2 and "not clean" in o.stderr
    dirty.unlink()
    # every registered stage, in order, by the real launch scripts
    outs = {}
    for st in ("gates", "train", "eval", "analysis", "report"):
        outs[st] = chain.script(f"{st}.sh", str(chain.pub), freeze_commit)
        assert outs[st].returncode == 0, (st, outs[st].stdout[-1500:], outs[st].stderr[-1500:])
    for st in ("gates", "train", "eval"):
        man = core.read_record(chain.pub / st / "manifest.json", "stage_manifest")
        assert man["status"] == "COMPLETE" and man["identity"]["commit"] == freeze_commit and "studies/p10i_s6/analysis.py" in man["identity"]["computing_files"]
        assert "studies/p10i_s6/stages.py" in man["identity"]["computing_files"] and "studies/p10i_s6/runner.py" not in man["identity"]["computing_files"]  # everything that produces a number is in a stage record's identity; supervision is not
    res = core.read_record(chain.pub / "analysis" / "analysis.json", "analysis")["result"]
    assert res["k_max"] == 2 and res["cells"] == 27 and res["line_p"]["row"] in range(1, 13) and res["trend"]["text"].endswith("is not the label PERSISTS.")
    rep = (chain.pub / "analysis" / "report.md").read_text()
    assert res["line_p"]["label"] in rep and "X_mean_dense per rung" in rep and "Self-check output" in rep
    # a stage already complete is not rewritten and a second launch says so
    again = chain.script("gates.sh", str(chain.pub), freeze_commit)
    assert again.returncode == 0 and "already complete" in again.stdout
    assert list((chain.pub / "attempts").glob("*.json")) is not None
    # the cumulative ledgers are separate: the registered one was charged only by registered stages
    led = json.loads((chain.pub / "ledger.json").read_text())
    assert {e["stage"] for e in led["entries"]} <= {"gates", "train", "eval"}
