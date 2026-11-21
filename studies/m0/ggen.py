# ruff: noqa: E501
"""Stage G-gen (ADR-0033 sections 6.2 and 8): build the pools and run the generator gates, with no model involved.

Gates: validity (both solvers agree on every item; C1 programs also run twice in two fresh restricted processes; the
answer is in the scorer's grammar and unchanged by its normalisation), reproducibility (the pools are built twice in
two processes with PYTHONHASHSEED=0 and the hashes compared), capacity (for every lineage and level, at least ten
times the demanded number of distinct items can be exhibited), disjointness (tuning, development and sealed items are
pairwise disjoint and unique after normalisation).

This module can only REHEARSE the stage: its record is never the record of record, which waits for the human lead's G
and domain list. Run: ``uv run --locked python -m studies.m0.ggen rehearse --out <new directory>``.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import os
import stat
import subprocess
import sys
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from studies.m0 import c1grammar
from studies.m0 import config as cfgmod
from studies.m0.core import (
    CORE_LEVELS,
    Item,
    check_disjoint,
    family_partition,
    generate_pool,
    keyed_fingerprint,
    lineages_of,
    m0_draw,
    ngram_fingerprints,
    part_lineages,
    pool_hash,
    stream,
    summarise,
    text_hash,
)
from studies.m0.scoring import canon, in_grammar, normalise_answer

PRIVATE_EVALS = ("R1", "R2", "M1", "C1")
PARTS = ("A", "B")
ALL_ROLES = ("tuning", "development", "sealed")
REHEARSAL_SEED_BLOCK = 409001  # capacity-gate stream (rehearsal draws 409001-409099)


def _solvers(eval_id: str) -> dict[str, Any]:
    return importlib.import_module(f"studies.m0.solvers_{eval_id.lower()}").SOLVERS  # type: ignore[no-any-return]


@dataclass
class Sizes:
    tuning_per_level: int = 100
    development: int = 4000
    m0_draw: int = 1500
    sealed: int = 20000
    k0_development: int = 500
    k0_sealed: int = 20000
    capacity_factor: int = 10

    @classmethod
    def from_config(cls, cfg: dict[str, Any]) -> Sizes:
        s = cfg["sizes"]
        return cls(s["tuning_items_per_level_and_part"], s["development_pool_per_part"], s["m0_draw_per_part"], s["sealed_pool_per_part"], s["k0_development"], s["k0_sealed_pool"], cfg["generators"]["capacity_factor"])


def level_mix(levels: Sequence[int] = CORE_LEVELS) -> dict[int, float]:
    """Placeholder mix for the rehearsal (uniform over the five core levels): the real mix is chosen by code in stage R1
    from the tuning scores, which do not exist."""
    return {lv: 1.0 for lv in levels}


@dataclass
class Pools:
    items: dict[tuple[str, str, str], list[Item]]  # (eval, part, role) -> items
    shortfalls: dict[tuple[str, str, str], list[tuple[str, int, int, int]]] = field(default_factory=dict)  # capacity failures

    def hashes(self) -> dict[str, str]:
        return {"/".join(k): pool_hash(v) for k, v in sorted(self.items.items())}


def build_pools(salt: bytes, sizes: Sizes, evals: Sequence[str] = (*PRIVATE_EVALS, "K0"), seeds: tuple[int, int, int] = (400001, 400002, 400003), strict: bool = True) -> Pools:
    """Tuning (seed 400001), development (400002) and sealed (400003 with the salt) pools, disjoint by construction.

    ``strict`` raises when a lineage cannot supply its quota. Otherwise (rehearsal) the pool is built short and the
    shortfall is recorded: that is a capacity failure of the generator, never padded with mechanical variants."""
    tuning_seed, dev_seed, sealed_seed = seeds
    out: dict[tuple[str, str, str], list[Item]] = {}
    short: dict[tuple[str, str, str], list[tuple[str, int, int, int]]] = {}
    for ev in evals:
        parts = ("K",) if ev == "K0" else PARTS
        for part in parts:
            taken: set[str] = set()
            if ev != "K0":
                out[(ev, part, "tuning")] = tun = []
                for lv in (0, *CORE_LEVELS, 6):
                    sf: list[tuple[str, int, int, int]] | None = None if strict else []
                    tun.extend(generate_pool(ev, part, "tuning", tuning_seed, sizes.tuning_per_level, {lv: 1.0}, taken, shortfalls=sf))
                    if sf:
                        short.setdefault((ev, part, "tuning"), []).extend(sf)
            dev_n = sizes.k0_development if ev == "K0" else sizes.development
            sealed_n = sizes.k0_sealed if ev == "K0" else sizes.sealed
            mix = {1: 1.0} if ev == "K0" else level_mix()
            for role, seed, n in (("development", dev_seed, dev_n), ("sealed", sealed_seed, sealed_n)):
                sf2: list[tuple[str, int, int, int]] | None = None if strict else []
                out[(ev, part, role)] = generate_pool(ev, part, role, seed, n, mix, taken, salt_label=salt.hex() if role == "sealed" else "", shortfalls=sf2)
                if sf2:
                    short[(ev, part, role)] = sf2
    return Pools(out, short)


# ------------------------------------------------------------------ gates


def validity_gate(items: Sequence[Item], isolated_batch: int = 1000) -> dict[str, Any]:
    """Both solvers agree on every item; the answer is in the grammar and unchanged by normalisation; for C1 two fresh
    restricted processes reproduce the answer. Returns counts and the first problems (never raises)."""
    problems: list[str] = []
    by_eval: dict[str, list[Item]] = {}
    for it in items:
        by_eval.setdefault(it.eval, []).append(it)
    n_checked = 0
    for ev, its in sorted(by_eval.items()):
        solvers = _solvers(ev)
        for it in its:
            n_checked += 1
            try:
                got = solvers[it.lineage](json.loads(json.dumps(it.structured)))
            except Exception as ex:  # noqa: BLE001
                problems.append(f"{it.id}: second solver raised {type(ex).__name__}: {ex}")
                continue
            if got != it.answer:
                problems.append(f"{it.id}: solvers disagree ({it.answer!r} vs {got!r})")
            norm = normalise_answer(it.answer)
            if not in_grammar(it.answer_type, norm):
                problems.append(f"{it.id}: answer {it.answer!r} not in the grammar of {it.answer_type}")
            elif canon(it.answer_type, norm) != canon(it.answer_type, normalise_answer(norm)):
                problems.append(f"{it.id}: answer not stable under normalisation")
            if it.k is not None and it.answer_type in ("name", "text", "word", "letter", "ynu", "yn") and it.k < 2:
                problems.append(f"{it.id}: closed answer with k < 2")
        if ev == "C1":
            for lo in range(0, len(its), isolated_batch):
                batch = its[lo : lo + isolated_batch]
                srcs = [c1grammar.render(it.structured["program"]) for it in batch]
                r1, r2 = c1grammar.run_isolated(srcs), c1grammar.run_isolated(srcs)  # two separate fresh processes
                for it, a, b in zip(batch, r1, r2, strict=True):
                    if a["err"] or b["err"] or a["out"] != b["out"] or a["out"] != it.answer:
                        problems.append(f"{it.id}: isolated runs {a!r} / {b!r} vs {it.answer!r}")
    return {"checked": n_checked, "problems": len(problems), "first_problems": problems[:20]}


def disjointness_gate(pools: Pools) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for ev in sorted({k[0] for k in pools.items}):
        for part in sorted({k[1] for k in pools.items if k[0] == ev}):
            named = {role: pools.items[(ev, part, role)] for role in ALL_ROLES if (ev, part, role) in pools.items}
            prob = check_disjoint(named)
            out[f"{ev}/{part}"] = {"roles": sorted(named), "problems": len(prob), "first_problems": prob[:5]}
    return out


@dataclass
class CapacityRow:
    lineage: str
    level: int
    clusters_in_part: int
    demand: int
    needed: int
    found: int
    attempts: int
    passed: bool
    passes_at_g_300: bool  # informational: would the exhibited count meet the factor at the proposed minimum G (demand / 300 per lineage)?


def demand_per_level(sizes: Sizes, g_part: int, level: int, kind: str = "worst") -> int:
    """Items one lineage must be able to supply at one level.

    ``worst`` (the reading used, least favourable): the whole development and sealed pools of the part could fall on one
    level (the level mix is chosen later), so the demand is (development + sealed) / G plus the tuning draw. ``even``:
    the pools are spread evenly over the five core levels. Reserve levels demand the tuning draw only.
    """
    if level in (0, 6):
        return sizes.tuning_per_level
    share = (sizes.development + sizes.sealed) / g_part
    if kind == "even":
        share /= len(CORE_LEVELS)
    return math.ceil(share) + sizes.tuning_per_level


def exhibit(eval_id: str, lin_id: str, level: int, need: int, label: str, attempt_factor: int = 3) -> tuple[int, int]:
    """Draw items until ``need`` distinct (after normalisation) have been exhibited or the attempt budget is spent."""
    lin = next(x for x in lineages_of(eval_id) if x.id == lin_id)
    taken: set[str] = set()
    rng = stream(REHEARSAL_SEED_BLOCK, "capacity", label, lin_id, str(level))
    from studies.m0.core import build_item

    attempts = 0
    while len(taken) < need and attempts < attempt_factor * need + 1000:
        attempts += 1
        it = build_item(lin, level, rng, "A", "cap")
        taken.add(text_hash(it.question))
    return len(taken), attempts


def _cap_task(args: tuple[str, str, int, int, str]) -> tuple[str, int, int, int]:
    ev, lid, level, need, label = args
    found, att = exhibit(ev, lid, level, need, label)
    return lid, level, found, att


def capacity_gate(sizes: Sizes, evals: Sequence[str] = PRIVATE_EVALS, kind: str = "worst", workers: int = 2, levels: Sequence[int] = (0, 1, 2, 3, 4, 5, 6), g_min: int = 300) -> list[CapacityRow]:
    tasks = []
    meta: dict[tuple[str, int], tuple[int, int]] = {}
    for ev in evals:
        pmap = family_partition(ev)
        gpart = {p: len(part_lineages(ev, p)) for p in PARTS}
        for lin in lineages_of(ev):
            g = gpart[pmap[lin.family]]
            for lv in levels:
                dem = demand_per_level(sizes, g, lv, kind)
                meta[(lin.id, lv)] = (g, dem)
                tasks.append((ev, lin.id, lv, sizes.capacity_factor * dem, kind))
    if workers > 1:
        import multiprocessing as mp

        with mp.get_context("spawn").Pool(workers) as pool:
            res = pool.map(_cap_task, tasks, chunksize=1)
    else:
        res = [_cap_task(t) for t in tasks]
    rows = []
    for lid, lv, found, att in res:
        g, dem = meta[(lid, lv)]
        need = sizes.capacity_factor * dem
        rows.append(CapacityRow(lid, lv, g, dem, need, found, att, found >= need, found >= sizes.capacity_factor * demand_per_level(sizes, g_min, lv, kind)))
    return rows


# ------------------------------------------------------------------ the rehearsal record


def _fingerprint_file(path: Path, items: Sequence[Item], salt: bytes, n: int) -> int:
    count = 0
    with open(path, "wb") as fh:
        for it in items:
            fps = [keyed_fingerprint(it.question, salt), *ngram_fingerprints(it.question, salt, n)]
            fh.write(len(fps).to_bytes(2, "big"))
            for fp in fps:
                fh.write(fp)
            count += len(fps)
    return count


def manifest_main(salt_hex: str, small: bool) -> None:
    """Child process of the reproducibility gate: build every pool and print the hash manifest as JSON."""
    sizes = Sizes.from_config(cfgmod.load()) if not small else Sizes(tuning_per_level=5, development=120, sealed=240, k0_development=20, k0_sealed=40)
    pools = build_pools(bytes.fromhex(salt_hex), sizes, strict=False)
    json.dump(pools.hashes(), sys.stdout, sort_keys=True)


def reproducibility_gate(salt: bytes, small: bool = False, python: str | None = None) -> dict[str, Any]:
    """Two fresh processes with PYTHONHASHSEED=0 build every pool; their hash manifests must agree."""
    outs = []
    for _ in range(2):
        p = subprocess.run(
            [python or sys.executable, "-m", "studies.m0.ggen", "manifest", "--salt-hex", salt.hex()] + (["--small"] if small else []),
            capture_output=True, text=True, check=False, env={"PYTHONHASHSEED": "0", "PATH": os.environ.get("PATH", "")}, cwd=str(Path(__file__).resolve().parents[2]),
        )
        if p.returncode != 0:
            return {"equal": False, "error": p.stderr[-500:]}
        outs.append(json.loads(p.stdout))
    return {"equal": outs[0] == outs[1], "n_pools": len(outs[0]), "manifest_sha256": hashlib.sha256(json.dumps(outs[0], sort_keys=True).encode()).hexdigest(), "manifest": outs[0]}


def rehearse(out: Path, workers: int = 2, remove_read: bool = False) -> dict[str, Any]:
    cfg = cfgmod.load()
    sizes = Sizes.from_config(cfg)
    if out.exists():
        raise SystemExit(f"refusing: {out} exists")
    out.mkdir(parents=True)
    (out / "README_REHEARSAL.txt").write_text(
        "REHEARSAL of stage G-gen at the proposed numbers (ADR-0033, Decision 1 limited to locked-environment work).\n"
        "This is NOT the record of record. The generators are not frozen. G (the number of lineages) and the domain list are the human lead's.\n"
        "The sealed pools below were made with a REHEARSAL salt; they are not the sealed pools of the study. No model was run; no score exists.\n"
        "The sealed directory keeps its normal permissions in this rehearsal (the specified removal of read permission was not performed; it is a --remove-read option).\n"
    )
    t0 = time.time()
    salt = os.urandom(cfg["generators"]["salt_bytes"])
    log: dict[str, Any] = {"rehearsal": True, "record_of_record": False, "start": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    pools = build_pools(salt, sizes, strict=False)
    log["shortfalls"] = {"/".join(k): v for k, v in sorted(pools.shortfalls.items())}
    log["build_seconds"] = round(time.time() - t0, 1)

    # counts per part
    parts: dict[str, Any] = {}
    for ev in (*PRIVATE_EVALS, "K0"):
        pm = {} if ev == "K0" else family_partition(ev)
        for part in ("K",) if ev == "K0" else PARTS:
            lins = part_lineages(ev, part)
            parts[f"{ev}/{part}"] = {
                "families": sorted({x.family for x in lins}),
                "lineages": [x.id for x in lins],
                "G": len(lins),
                "minimum_proposed": cfg["sizes"]["min_clusters_per_part"],
                "shortfall_factor": round(cfg["sizes"]["min_clusters_per_part"] / max(1, len(lins)), 1),
            }
        parts[f"{ev}/partition"] = pm
    log["parts"] = parts

    # validity
    t1 = time.time()
    val: dict[str, Any] = {}
    for key in sorted(pools.items):
        r = validity_gate(pools.items[key])
        val["/".join(key)] = r
    log["validity"] = val
    log["validity_seconds"] = round(time.time() - t1, 1)
    # disjointness
    log["disjointness"] = disjointness_gate(pools)
    # pool records
    recs = {}
    for key, items in sorted(pools.items.items()):
        rec = summarise(items, key[0], key[1], key[2])
        recs["/".join(key)] = asdict(rec)
    log["pools"] = recs
    # M0 draw (development only)
    m0 = {}
    for ev in PRIVATE_EVALS:
        for part in PARTS:
            d = m0_draw(pools.items[(ev, part, "development")], sizes.m0_draw, allow_short=True)
            m0[f"{ev}/{part}"] = {"size": len(d), "wanted": sizes.m0_draw, "sha256": pool_hash(d)}
    log["m0_draw"] = m0
    # write the development and tuning pools (open) and the sealed pools (read permission removed)
    (out / "open").mkdir()
    for key, items in sorted(pools.items.items()):
        if key[2] == "sealed":
            continue
        with open(out / "open" / ("_".join(key) + ".jsonl"), "w") as fh:
            for it in items:
                fh.write(it.to_json() + "\n")
    sealed = out / "sealed"
    sealed.mkdir()
    fp_counts = {}
    for key, items in sorted(pools.items.items()):
        if key[2] != "sealed":
            continue
        path = sealed / ("_".join(key) + ".jsonl")
        with open(path, "w") as fh:
            for it in items:
                fh.write(it.to_json() + "\n")
        fp_counts["/".join(key)] = _fingerprint_file(sealed / ("_".join(key) + ".fingerprints.bin"), items, salt, cfg["generators"]["ngram_length"])
    (sealed / "salt.bin").write_bytes(salt)
    log["salt_sha256"] = hashlib.sha256(salt).hexdigest()
    log["fingerprint_counts"] = fp_counts
    # reproducibility in two fresh processes
    t2 = time.time()
    repro = reproducibility_gate(salt)
    log["reproducibility"] = {k: v for k, v in repro.items() if k != "manifest"}
    mine = pools.hashes()
    log["reproducibility"]["equals_this_process"] = repro.get("manifest") == mine
    log["reproducibility_seconds"] = round(time.time() - t2, 1)
    # capacity
    t3 = time.time()
    rows = capacity_gate(sizes, workers=workers)
    log["capacity"] = {
        "reading": "worst case: the whole development and sealed pools of the part could fall on one level; reserve levels demand the tuning draw only",
        "factor": sizes.capacity_factor,
        "rows": [asdict(r) for r in rows],
        "failed": [asdict(r) for r in rows if not r.passed],
        "n_rows": len(rows),
    }
    log["capacity_seconds"] = round(time.time() - t3, 1)
    # audit samples (for the auditor contexts; not a gate)
    audit = out / "audit_samples"
    audit.mkdir()
    r = stream(REHEARSAL_SEED_BLOCK + 1, "audit-samples")
    for ev in PRIVATE_EVALS:
        pool = pools.items[(ev, "A", "development")] + pools.items[(ev, "B", "development")]
        pick = r.sample(pool, 50)
        (audit / f"{ev}_50_items.txt").write_text("\n\n".join(f"[{it.id}] level {it.level}\n{it.question}\nANSWER: {it.answer}" for it in pick))
        fams: dict[str, list] = {}
        for lin in lineages_of(ev):
            fams.setdefault(lin.family, []).append(lin)
        best = max(sorted(fams), key=lambda f: len(fams[f]))
        ls = fams[best]
        pairs = [(a, b) for i, a in enumerate(ls) for b in ls[i + 1 :]]
        chosen = r.sample(pairs, min(50, len(pairs))) if pairs else []
        lines = []
        for a, b in chosen:
            ia = next(it for it in pool if it.lineage == a.id)
            ib = next(it for it in pool if it.lineage == b.id)
            lines.append(f"PAIR {a.id} / {b.id}\n--- {a.id}\n{ia.question}\n--- {b.id}\n{ib.question}")
        (audit / f"{ev}_lineage_pairs_family_{best}.txt").write_text("\n\n".join(lines) or "(the family has one lineage only)")
    log["audit_samples"] = "50 development items per evaluation; one rendered item from each of up to 50 random lineage pairs of the largest family"
    log["registry_check"] = "NOT RUN: the seed registry revision 6 and its checker are the auditor's and are not in this tree"
    log["total_seconds"] = round(time.time() - t0, 1)
    (out / "rehearsal_record.json").write_text(json.dumps(log, indent=1, sort_keys=True))
    # the specification removes read permission from the sealed directory; that is a permission change, so it is done only on request
    if remove_read:
        for p in sorted(sealed.iterdir()):
            os.chmod(p, 0)
        os.chmod(sealed, stat.S_IWUSR | stat.S_IXUSR)
    return log


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    rp = sub.add_parser("rehearse")
    rp.add_argument("--out", required=True)
    rp.add_argument("--workers", type=int, default=2)
    rp.add_argument("--remove-read", action="store_true")
    mp_ = sub.add_parser("manifest")
    mp_.add_argument("--salt-hex", required=True)
    mp_.add_argument("--small", action="store_true")
    a = ap.parse_args()
    if a.cmd == "manifest":
        manifest_main(a.salt_hex, a.small)
        return
    log = rehearse(Path(a.out), a.workers, a.remove_read)
    print(json.dumps({k: v for k, v in log.items() if k in ("total_seconds", "build_seconds", "validity_seconds", "reproducibility_seconds", "capacity_seconds")}))


if __name__ == "__main__":
    main()
