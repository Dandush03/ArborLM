# ruff: noqa: E501
"""A synthetic Part Q directory shaped like the real one and the child-process side of the Part T launch tests (ADR-0025 section 10; audit B1).

``make_part_q`` writes ``outputs/bundle/*`` (the same files ``write_bundle`` writes for the real bundle: no Q_check panel), ``outputs/gloss_bank.json``, ``generation/result.json`` (DISJOINT DRAWS) and the public
Q_check batch keys, and a ``manifest.json`` listing each by SHA-256, from P10-S2's synthetic stand-ins (a made-up word-for-word pair, a tiny random student, lexicon teachers). ``install`` runs inside every child
process (through ``sitecustomize``): the tiny run configuration in place of the real one and the registry-checker gate answered by a fake (the checker is exercised on the real tree by its own test). Everything
else on the path is the real code. Nothing here is a result. Self-check only."""

import dataclasses
import os
import stat
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from arborlm.io import file_sha256, write_json  # noqa: E402

TESTS = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[1]
SITE = TESTS / "p10is2_partt_e2e_site"
TINY_CALIB = {"U": 2, "converged": True, "store_rate": 0.003, "lora_rate": 0.001, "etable_rate": 0.003, "read_layer": 1, "pilot": {"passed": True}, "records": {}}


def fake_gloss_bank(w: Any, pool: Any) -> dict[str, Any]:
    from studies.p10is2.common import core
    from studies.p10s2.text import normalize

    v = w.cfg.vocab

    def ids(x: str) -> list[int]:
        return [1 + (sum(map(ord, x)) % (v - 2))]

    words: dict[str, dict[str, list[int]]] = {c: {} for c in core.TASKS}
    for c in core.TASKS:  # every word of every accepted pool (the real bank covers the whole pools, so any draw finds its words)
        for x in pool[c]:
            for t in normalize(x.target).split():
                words[c][t] = ids(t)
    return {"source_words": {x: ids(x) for x in w.partition.vocab}, "source_words_after_newline": {x: [3, *ids(x)] for x in w.partition.vocab}, "words": words, "separator": [2], "newline": [3], "last_newline": {"rule": "own-segment"}}


def make_part_q(qdir: Path) -> Path:
    """The synthetic Part Q run directory of record, listed in its own manifest by SHA-256."""
    from p10is2_engine_fixtures import bundle, draws, world

    from studies.p10is2.common import core
    from studies.p10s2.worldio import write_bundle

    b0 = bundle()
    a_keys = {x.key for x in b0.accepted["A"]}
    accepted = {"A": list(b0.accepted["A"]), "B": [x for x in b0.accepted["B"] if x.key not in a_keys]}  # the registered split is made before generation: B's sources are disjoint from A's
    b = dataclasses.replace(b0, accepted=accepted)
    write_bundle(dataclasses.replace(b, panels={k: v for k, v in b.panels.items() if k != "Q_check"}), qdir / "outputs/bundle")
    pool = {c: list(b.accepted[c]) for c in core.TASKS}
    pos = {c: {x.key: i for i, x in enumerate(pool[c])} for c in core.TASKS}
    indices = {c: [[pos[c][x.key] for x in d[c]] for d in draws(3, 20)] for c in core.TASKS}
    for d in ("generation", "outputs", "qcheck/teacher_A/block_0"):
        (qdir / d).mkdir(parents=True, exist_ok=True)
    write_json(qdir / "generation/result.json", {"draws_label": "DISJOINT DRAWS", "draws": {"indices": indices}})
    write_json(qdir / "outputs/gloss_bank.json", fake_gloss_bank(world(updates=2, n_reps=1), pool))
    write_json(qdir / "qcheck/teacher_A/block_0/batch_0.json", {"keys": ["a q check sentence that no training stream holds", "another q check sentence"]})
    files = sorted(str(p.relative_to(qdir)) for p in qdir.rglob("*") if p.is_file() and p.name != "manifest.json")
    write_json(qdir / "manifest.json", {"files": {rel: file_sha256(qdir / rel) for rel in files}})
    return qdir


def fake_uv(tmp: Path) -> dict[str, str]:
    """A ``uv`` that runs ``python -m <module> <args>`` with the lock environment's interpreter, the tiny-world ``sitecustomize`` on PYTHONPATH (never the durable packages), and no other change."""
    bindir = tmp / "bin"
    bindir.mkdir(exist_ok=True)
    uv = bindir / "uv"
    uv.write_text('#!/bin/sh\nwhile [ "$1" != "python" ]; do shift; done\nshift\nPYTHONPATH="$E2E_SITE" exec "$E2E_PY" "$@"\n')
    uv.chmod(uv.stat().st_mode | stat.S_IEXEC)
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "OMP_NUM_THREADS")}
    env.update(PATH=f"{bindir}:{env['PATH']}", E2E_PY=sys.executable, E2E_SITE=str(SITE), E2E_SRC=str(ROOT / "src"), E2E_ROOT=str(ROOT), E2E_TESTS=str(TESTS), PYTHONDONTWRITEBYTECODE="1")
    return env


def install() -> None:
    """Inside a child: the tiny run configuration and the faked registry-checker gate (everything else is the real code)."""
    from studies.p10is2 import engine
    from studies.p10is2.common import gates
    from studies.p10s2.routing import RouterSpec

    real = engine.run_config

    def tiny(cfg: Any, *, layer: int, updates: int, store_rate: float, lora_rate: float, device: str, **_rest: Any) -> Any:
        return real(cfg, layer=layer, updates=updates, store_rate=store_rate, lora_rate=lora_rate, device=device, batch=4, rows=16, router=RouterSpec.dry(), decision_token=8, window_tokens=24, ranks=(2, 4), replay=4)

    engine.run_config = tiny  # type: ignore[assignment]
    gates.seed_gate = lambda part, cfg, **k: {"passed": True, "problems": [], "checker": {"faked_in_this_test": True}}  # type: ignore[assignment]
