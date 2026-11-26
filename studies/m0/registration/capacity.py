# ruff: noqa: E501
"""ADR-0033 addendum 1, section 4A stage 4: capacity, per evaluation part, to a fixed point.

The sentences of the approved text this module implements, and where, are in ``NOTES.md`` (sentence-to-code
map). In short:

* ``count`` is "how a count is made": one lineage, one level, one target T; the fresh stream
  ``stream(400002, "capacity", e, id of x, str(v))``; a key set that starts empty; items built one after
  another with the builder's own ``build_item`` as ``draw_items`` of ``studies/m0/core.py`` does; an item
  whose key (``distinct_key``) is in the set is discarded; the draw stops at T keys, or when the attempts
  exceed 40 * T + 1,000, or when ``build_item`` gives up after 500 consecutive retries.
* ``run_stage4`` is "one round" and the fixed point, for each of the eight evaluation parts.

No set of keys or texts is shared between lineages, levels, clusters, parts or roles; the only thing two
draws share is the stream's label, and that differs for every (lineage, level).

Command line (the lead runs it on the partition of record; nothing here runs by itself)::

    PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 uv run --locked python -m \\
        studies.m0.registration.capacity --candidates candidate_list.json --partition partition.json \\
        --map studies/m0/manifests/map_of_record.json --out capacity_stage4.json --workers 8 \\
        [--cache-dir DIR --cache-tag TAG] [--timings-out timings.json]
"""

from __future__ import annotations

import argparse
import array
import bisect
import copy
import hashlib
import json
import multiprocessing
import os
import random
import signal
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import FIRST_COMPLETED, Future, ProcessPoolExecutor, wait
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from studies.m0.core import Lineage, build_item, stream
from studies.m0.registration import distinct_key
from studies.m0.registration.distinct_key import KEY_BYTES, item_key

SEED = 400002
LABEL = "capacity"
EVALS = ("R1", "R2", "M1", "C1")
PARTS = ("A", "B")
LEVELS = (0, 1, 2, 3, 4, 5, 6)
ATTEMPT_FACTOR = 40  # the budget of draw_items as written: 40 * T + 1,000 attempts
ATTEMPT_BASE = 1000
DEV, POOL, TUNING = 4000, 20000, 100  # section 10 part A item 2: development, sealed, tuning
SOLVER_SECONDS = 20  # per-item wall limit of the pair audit
DISAGREEMENT_DETAILS = 20  # details kept per draw; the count and every attempt position are kept in full

KeyFn = Callable[[str, str, Mapping[str, Any]], bytes]
Solver = Callable[[str, Any], Any]


# ------------------------------------------------------------------------------------------ demands


def _ceil_div(a: int, b: int) -> int:
    return -(-a // b)


def demand(g: int) -> int:
    """D(G) = 10 * (ceil(4,000 / G) + ceil(20,000 / G) + 100): keys a cluster must hold at each level."""
    if g < 1:
        raise ValueError("G must be at least 1")
    return 10 * (_ceil_div(DEV, g) + _ceil_div(POOL, g) + TUNING)


def demand_lin(g: int, k: int) -> int:
    """D_lin(G, k) = 10 * (ceil(ceil(4,000 / G) / k) + ceil(ceil(20,000 / G) / k) + ceil(100 / k))."""
    if g < 1 or k < 1:
        raise ValueError("G and k must be at least 1")
    return 10 * (
        _ceil_div(_ceil_div(DEV, g), k) + _ceil_div(_ceil_div(POOL, g), k) + _ceil_div(TUNING, k)
    )


def demand_w(lineages: int) -> int:
    """D_w(L): the option NOT taken (section 10 part B, item 6 (b)); kept only for the comparison."""
    return demand(lineages)


# ----------------------------------------------------------------------------------- one draw


@dataclass
class Disagreement:
    attempt: int  # 1-based position of the item in the stream of this (lineage, level)
    reason: str  # mismatch | error:<Type> | non-str | timeout
    key_answer: str
    solver_answer: str


@dataclass
class Draw:
    """The result of ``count``: c(x, v, T) is ``count``; ``keys`` are the 16-byte keys, first occurrence first."""

    lineage: str
    level: int
    target: int
    count: int
    ended: str  # target | budget | gave_up
    attempts: int  # attempts begun when the draw stopped (the failed one included for gave_up)
    keys: bytes
    solver_checked: bool
    n_disagreements: int
    disagreements: tuple[Disagreement, ...]
    first_disagreement_attempt: int | None
    seconds: float = 0.0  # wall time; never written to the deterministic output

    def summary(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "target": self.target,
            "ended": self.ended,
            "attempts": self.attempts,
            "solver_disagreements": self.n_disagreements,
        }


@dataclass
class _Trace:
    """The stream of one (lineage, level) as far as it has been drawn, independent of any target."""

    lineage: str
    level: int
    keys: bytearray = field(default_factory=bytearray)  # 16 bytes per distinct key, first occurrence first
    first_attempt: array.array[int] = field(default_factory=lambda: array.array("I"))
    dis_attempts: array.array[int] = field(default_factory=lambda: array.array("I"))
    dis_detail: list[Disagreement] = field(default_factory=list)
    attempts: int = 0  # attempts fully executed (an item built, and checked if a solver was given)
    gave_up_at: int | None = None  # the attempt at which build_item raised after 500 retries
    rng_state: tuple[Any, ...] | None = None  # state after `attempts` attempts, for continuing the stream


def stream_labels(lin: Lineage, level: int) -> tuple[str, ...]:
    """The labels after the seed: ``capacity``, e, id of x, the level's decimal digit."""
    return (LABEL, lin.eval, lin.id, str(level))


def _call_solver(solver: Solver, question: str, structured: Any) -> Any:
    """Apply a second solver as the pair audit did: a deep copy of the JSON form, a wall limit per item."""
    st = copy.deepcopy(json.loads(json.dumps(structured)))
    use_alarm = hasattr(signal, "SIGALRM") and _is_main_thread()
    if use_alarm:
        signal.alarm(SOLVER_SECONDS)
    try:
        return solver(question, st)
    finally:
        if use_alarm:
            signal.alarm(0)


def _is_main_thread() -> bool:
    import threading

    return threading.current_thread() is threading.main_thread()


class _SolverTimeout(Exception):
    pass


def _on_alarm(*_: Any) -> None:
    raise _SolverTimeout()


def _check(solver: Solver, question: str, structured: Any, answer: str, attempt: int) -> Disagreement | None:
    """None when the second solver returns exactly the builder's key (a ``str``); else the disagreement."""
    try:
        got = _call_solver(solver, question, structured)
    except _SolverTimeout:
        return Disagreement(attempt, "timeout", answer[:120], "")
    except Exception as exc:  # noqa: BLE001 - an exception is a disagreement, never hidden
        return Disagreement(attempt, f"error:{type(exc).__name__}", answer[:120], str(exc)[:120])
    if not isinstance(got, str):
        return Disagreement(attempt, "non-str", answer[:120], repr(got)[:120])
    if got != answer:
        return Disagreement(attempt, "mismatch", answer[:120], got[:120])
    return None


def _advance(
    lin: Lineage,
    level: int,
    target: int,
    tr: _Trace,
    seen: set[bytes],
    rng: random.Random,
    solver: Solver | None,
    key_fn: KeyFn,
) -> None:
    """Continue the stream until ``target`` keys, the target's own budget, or the give-up of build_item.

    This is the loop of ``draw_items`` (``studies/m0/core.py``) with the key of section 10 part A item 1
    in place of the text hash, and with the give-up of ``build_item`` ending the draw instead of raising.
    The solver, when given, is applied to every item built, discarded ones included.
    """
    budget = ATTEMPT_FACTOR * target + ATTEMPT_BASE
    if solver is not None and hasattr(signal, "SIGALRM") and _is_main_thread():
        signal.signal(signal.SIGALRM, _on_alarm)
    while len(tr.keys) // KEY_BYTES < target:
        n = tr.attempts + 1
        if n > budget:
            break
        try:
            it = build_item(lin, level, rng, "-", f"{lin.id}/{LABEL}/L{level}/{len(tr.keys) // KEY_BYTES}")
        except RuntimeError as exc:
            if "consecutive retries" not in str(exc):
                raise
            tr.gave_up_at = n
            break
        tr.attempts = n
        if solver is not None:
            bad = _check(solver, it.question, it.structured, it.answer, n)
            if bad is not None:
                tr.dis_attempts.append(n)
                if len(tr.dis_detail) < DISAGREEMENT_DETAILS:
                    tr.dis_detail.append(bad)
        k = key_fn(lin.id, it.question, it.structured)
        if k in seen:
            continue
        seen.add(k)
        tr.keys += k
        tr.first_attempt.append(n)
    tr.rng_state = rng.getstate()


def _derive(tr: _Trace, target: int, solver_checked: bool) -> Draw | None:
    """The draw for ``target`` read off a trace of the same stream, or None if the trace is too short.

    Prefix property (proved in NOTES.md): the item at attempt n of the stream of (x, v) does not depend on the
    target, on the key set or on anything drawn by another cell. So the draw for any target is a prefix
    of one trace: it stops at the attempt where the key count first reaches the target, or after the target's
    own budget, or at the give-up, whichever comes first.
    """
    budget = ATTEMPT_FACTOR * target + ATTEMPT_BASE
    m = len(tr.keys) // KEY_BYTES
    if m >= target and tr.first_attempt[target - 1] <= budget:
        stop, ended, n_keys = tr.first_attempt[target - 1], "target", target
        attempts = stop
    elif tr.gave_up_at is not None and tr.gave_up_at <= budget:
        stop, ended, n_keys = tr.gave_up_at - 1, "gave_up", m
        attempts = tr.gave_up_at
    elif budget <= tr.attempts:
        stop, ended = budget, "budget"
        n_keys = bisect.bisect_right(tr.first_attempt, budget)
        attempts = budget
    else:
        return None
    n_dis = bisect.bisect_right(tr.dis_attempts, stop)
    details = tuple(d for d in tr.dis_detail if d.attempt <= stop)
    return Draw(
        lineage=tr.lineage,
        level=tr.level,
        target=target,
        count=n_keys,
        ended=ended,
        attempts=attempts,
        keys=bytes(tr.keys[: n_keys * KEY_BYTES]),
        solver_checked=solver_checked,
        n_disagreements=n_dis,
        disagreements=details,
        first_disagreement_attempt=tr.dis_attempts[0] if n_dis else None,
    )


# ----------------------------------------------------------------------------------- disk cache


class TraceCache:
    """Traces of the stream of each (lineage, level), on disk, so that a later round can be answered from them.

    What is cached is the stream, not a count: the first-occurrence order of the keys and the attempt at which
    each appeared, the attempts at which the solvers disagreed, and the generator's state after the last attempt.
    A request for target T is answered from the longest trace when it reaches T keys, or the target's own
    budget, or the give-up; if the trace stops short it is continued from its stored state. The answer is the
    one a draw from the start of the stream would give (``_derive``; tests compare the two). A file is named by its
    horizon, is written once (never rewritten) and carries its own checksum; a file with another tag, another
    stream or a bad checksum is ignored. ``tag`` names the generators and the key function the cache was made
    with and must change when either does.
    """

    MAGIC = b"ARBCAP1\n"

    def __init__(self, directory: str | Path, tag: str) -> None:
        if not tag:
            raise ValueError("a cache needs a non-empty tag naming the generators and the key function")
        if array.array("I").itemsize != 4:
            raise RuntimeError("unsigned int is not 4 bytes on this platform")
        self.dir = Path(directory)
        self.tag = tag
        self.dir.mkdir(parents=True, exist_ok=True)

    def _files(self, lid: str, level: int) -> list[tuple[int, Path]]:
        prefix = f"{lid}__L{level}__H"
        out = []
        for p in self.dir.iterdir():
            if p.name.startswith(prefix) and p.name.endswith(".trace"):
                try:
                    out.append((int(p.name[len(prefix) : -len(".trace")].rstrip("g")), p))
                except ValueError:
                    continue
        return sorted(out, reverse=True)

    def _header(self, lin: Lineage, level: int, solver_checked: bool) -> dict[str, Any]:
        return {
            "tag": self.tag,
            "solver_checked": solver_checked,
            "stream": [str(SEED), *stream_labels(lin, level)],
            "key_version": distinct_key.KEY_VERSION,
            "key_bytes": KEY_BYTES,
        }

    def load(self, lin: Lineage, level: int, solver_checked: bool) -> _Trace | None:
        want = self._header(lin, level, solver_checked)
        for _, path in self._files(lin.id, level):
            blob = path.read_bytes()
            if len(blob) < len(self.MAGIC) + 8 + 32 or not blob.startswith(self.MAGIC):
                continue
            if hashlib.sha256(blob[:-32]).digest() != blob[-32:]:
                continue
            hl = int.from_bytes(blob[len(self.MAGIC) : len(self.MAGIC) + 8], "big")
            body = len(self.MAGIC) + 8
            head = json.loads(blob[body : body + hl].decode("utf-8"))
            if any(head.get(k) != v for k, v in want.items()):
                continue
            pos = body + hl
            n_keys, n_dis = head["n_keys"], head["n_dis"]
            tr = _Trace(lin.id, level)
            tr.keys = bytearray(blob[pos : pos + n_keys * KEY_BYTES])
            pos += n_keys * KEY_BYTES
            tr.first_attempt = array.array("I")
            tr.first_attempt.frombytes(blob[pos : pos + 4 * n_keys])
            pos += 4 * n_keys
            tr.dis_attempts = array.array("I")
            tr.dis_attempts.frombytes(blob[pos : pos + 4 * n_dis])
            if sys.byteorder == "big":
                tr.first_attempt.byteswap()
                tr.dis_attempts.byteswap()
            tr.dis_detail = [Disagreement(**d) for d in head["dis_detail"]]
            tr.attempts = head["attempts"]
            tr.gave_up_at = head["gave_up_at"]
            st = head["rng_state"]
            tr.rng_state = None if st is None else (st[0], tuple(st[1]), st[2])
            return tr
        return None

    def store(self, lin: Lineage, tr: _Trace, solver_checked: bool) -> None:
        head = self._header(lin, tr.level, solver_checked)
        st = tr.rng_state
        head.update(
            {
                "n_keys": len(tr.keys) // KEY_BYTES,
                "n_dis": len(tr.dis_attempts),
                "dis_detail": [d.__dict__ for d in tr.dis_detail],
                "attempts": tr.attempts,
                "gave_up_at": tr.gave_up_at,
                "rng_state": None if st is None else [st[0], list(st[1]), st[2]],
            }
        )
        hb = json.dumps(head, sort_keys=True).encode("utf-8")
        fa, da = array.array("I", tr.first_attempt), array.array("I", tr.dis_attempts)
        if sys.byteorder == "big":
            fa.byteswap()
            da.byteswap()
        body = self.MAGIC + len(hb).to_bytes(8, "big") + hb + bytes(tr.keys) + fa.tobytes() + da.tobytes()
        body += hashlib.sha256(body).digest()
        flag = "g" if tr.gave_up_at is not None else ""
        path = self.dir / f"{tr.lineage}__L{tr.level}__H{tr.attempts:012d}{flag}.trace"
        try:
            with open(path, "xb") as f:
                f.write(body)
        except FileExistsError:
            pass  # same stream, same horizon: the same content


def count(
    lin: Lineage,
    level: int,
    target: int,
    *,
    solver: Solver | None = None,
    cache: TraceCache | None = None,
    key_fn: KeyFn = item_key,
) -> Draw:
    """c(x, v, T) of section 4A stage 4, "how a count is made": see the module docstring."""
    if target < 1:
        raise ValueError("the target must be at least 1")
    t0 = time.perf_counter()
    checked = solver is not None
    tr = cache.load(lin, level, checked) if cache is not None else None
    if tr is not None:
        d = _derive(tr, target, checked)
        if d is not None:
            d.seconds = time.perf_counter() - t0
            return d
    if tr is not None and tr.gave_up_at is None and tr.rng_state is not None:
        rng = random.Random()
        rng.setstate(tr.rng_state)
        seen = {bytes(tr.keys[i : i + KEY_BYTES]) for i in range(0, len(tr.keys), KEY_BYTES)}
    else:
        tr = _Trace(lin.id, level)
        rng = stream(SEED, *stream_labels(lin, level))
        seen = set()
    grown_from = tr.attempts
    _advance(lin, level, target, tr, seen, rng, solver, key_fn)
    if cache is not None and (tr.attempts > grown_from or tr.gave_up_at is not None):
        cache.store(lin, tr, checked)
    d = _derive(tr, target, checked)
    if d is None:  # cannot happen: _advance stops only at the target, the budget or the give-up
        raise RuntimeError("internal error: a continued draw does not answer its own target")
    d.seconds = time.perf_counter() - t0
    return d


# ------------------------------------------------------------------------- where lineages come from


class RealSource:
    """The committed lineages and second solvers, loaded as the second-solver fixtures and the pair audit
    loaded them (``studies/m0/lineages_r1_fix4_clusters``, ``r2_fix4_set``, ``lineages_m1_fix4``,
    ``lineages_c1_fix4``; ``studies/m0/solvers2/solver2_*.py`` by file path). Picklable: a worker loads its own."""

    def __init__(self) -> None:
        self._lins: dict[str, Lineage] | None = None
        self._solvers: dict[str, Solver] | None = None

    def __getstate__(self) -> dict[str, Any]:
        return {}

    def __setstate__(self, state: dict[str, Any]) -> None:
        self._lins = None
        self._solvers = None

    def _load_lineages(self) -> dict[str, Lineage]:
        from studies.m0.lineages_c1_fix4 import all_written
        from studies.m0.lineages_m1_fix4 import load_registered
        from studies.m0.lineages_r1_fix4_clusters import candidates_v4, registered_v4
        from studies.m0.r2_fix4_set import fix4_set

        out: dict[str, Lineage] = {}
        for ev, got in (
            ("R1", {x.id: x for x in [*candidates_v4(), *registered_v4()]}),
            ("R2", dict(fix4_set())),
            ("M1", {x.id: x for x in load_registered()}),
            ("C1", dict(all_written())),
        ):
            for lid, lin in got.items():
                if lid in out:
                    raise RuntimeError(f"lineage {lid} is defined twice")
                if lin.eval != ev:
                    raise RuntimeError(f"lineage {lid} has evaluation {lin.eval}, expected {ev}")
                out[lid] = lin
        return out

    def lineage(self, lid: str) -> Lineage:
        if self._lins is None:
            self._lins = self._load_lineages()
        return self._lins[lid]

    def solver(self, lid: str) -> Solver:
        if self._solvers is None:
            import importlib.util

            import studies.m0 as m0

            root = Path(m0.__file__).resolve().parent / "solvers2"
            out: dict[str, Solver] = {}
            for path in sorted(root.glob("solver2_*.py")):
                spec = importlib.util.spec_from_file_location(f"capacity_{path.stem}", path)
                if spec is None or spec.loader is None:
                    raise RuntimeError(f"cannot load {path}")
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                for sid, fn in mod.SOLVERS.items():
                    if sid in out:
                        raise RuntimeError(f"two second solvers for {sid}")
                    out[sid] = fn
            self._solvers = out
        if lid not in self._solvers:
            raise KeyError(f"no second solver for {lid}")
        return self._solvers[lid]


# ---------------------------------------------------------------------- the cells (lineage, level)

_W: dict[str, Any] = {}


def _init_worker(source: Any, cache_dir: str | None, cache_tag: str | None, check: bool) -> None:
    _W["source"] = source
    _W["cache"] = TraceCache(cache_dir, cache_tag or "") if cache_dir else None
    _W["check"] = check


def _run_cell(task: tuple[str, int, int]) -> Draw:
    lid, level, target = task
    src = _W["source"]
    lin = src.lineage(lid)
    solver = src.solver(lid) if _W["check"] else None
    return count(lin, level, target, solver=solver, cache=_W["cache"])


class CellRunner:
    """Runs (lineage, level, target) cells, in this process or in ``workers`` processes.

    A cell is a pure function of its three fields (and of the generators), so the result does not depend on
    the number of workers, on the order the cells are run in or on which worker runs which.
    """

    def __init__(
        self,
        source: Any,
        *,
        workers: int = 1,
        cache_dir: str | Path | None = None,
        cache_tag: str | None = None,
        check_solvers: bool = True,
        mp_context: str | None = None,
    ) -> None:
        if cache_dir is not None and not cache_tag:
            raise ValueError("--cache-dir needs --cache-tag")
        args = (source, None if cache_dir is None else str(cache_dir), cache_tag, check_solvers)
        self.workers = max(1, workers)
        self._pool: ProcessPoolExecutor | None = None
        if self.workers > 1:
            ctx = multiprocessing.get_context(mp_context) if mp_context else None
            self._pool = ProcessPoolExecutor(
                max_workers=self.workers, mp_context=ctx, initializer=_init_worker, initargs=args
            )
        else:
            _init_worker(*args)

    def submit(self, task: tuple[str, int, int]) -> Future[Draw]:
        if self._pool is not None:
            return self._pool.submit(_run_cell, task)
        done: Future[Draw] = Future()
        try:
            done.set_result(_run_cell(task))
        except BaseException as exc:  # noqa: BLE001 - re-raised by result()
            done.set_exception(exc)
        return done

    def run(self, tasks: Sequence[tuple[str, int, int]]) -> list[Draw]:
        order = sorted(range(len(tasks)), key=lambda i: (-tasks[i][2], tasks[i]))  # large cells first
        futures = {i: self.submit(tasks[i]) for i in order}
        return [futures[i].result() for i in range(len(tasks))]

    def close(self) -> None:
        if self._pool is not None:
            self._pool.shutdown(cancel_futures=True)
            self._pool = None


class _InjectedRunner:
    """Tests only: cells answered by a function (a model of the draws) instead of by ``count``."""

    def __init__(self, fn: Callable[[str, int, int], Draw]) -> None:
        self.fn = fn

    def submit(self, task: tuple[str, int, int]) -> Future[Draw]:
        done: Future[Draw] = Future()
        done.set_result(self.fn(*task))
        return done

    def close(self) -> None:
        pass


# --------------------------------------------------------------------------------- the rounds


@dataclass
class _Part:
    e: str
    p: str
    start: dict[str, list[str]]
    live: dict[str, list[str]]
    rounds: list[dict[str, Any]] = field(default_factory=list)
    removed: list[dict[str, Any]] = field(default_factory=list)
    done: bool = False
    inflight: dict[tuple[str, int, int], Future[Draw]] | None = None


def build_parts(
    candidates: Mapping[str, Any], partition: Mapping[str, Any], map_obj: Mapping[str, Any]
) -> dict[tuple[str, str], dict[str, list[str]]]:
    """For each evaluation part (e, p): the clusters with a candidate lineage of e, and those lineages.

    ``candidates``: ``{"candidates": {e: [ids]}}`` (or ``{e: [ids]}``); ``partition``: the partition code's
    output (``cluster_part``: cluster id -> "A" or "B"); ``map_obj``: the map of record (``clusters``).
    """
    cand = candidates.get("candidates", candidates)
    cluster_of: dict[str, str] = {}
    for c in map_obj["clusters"]:
        for m in c["members"]:
            if m in cluster_of:
                raise ValueError(f"lineage {m} is in two clusters")
            cluster_of[m] = c["cluster_id"]
    cluster_part = partition["cluster_part"]
    parts: dict[tuple[str, str], dict[str, list[str]]] = {(e, p): {} for e in EVALS for p in PARTS}
    seen: set[str] = set()
    for e in sorted(cand):
        if e not in EVALS:
            raise ValueError(f"unknown evaluation {e!r} in the candidate list")
        for x in sorted(cand[e]):
            if not x.startswith(e + ".") or x in seen:
                raise ValueError(f"candidate {x!r} is not a lineage of {e} or is listed twice")
            seen.add(x)
            if x not in cluster_of:
                raise ValueError(f"candidate {x} is in no cluster of the map")
            c = cluster_of[x]
            if c not in cluster_part:
                raise ValueError(f"cluster {c} of candidate {x} has no part in the partition")
            parts[(e, cluster_part[c])].setdefault(c, []).append(x)
    return parts


def _union_count(blobs: Sequence[bytes]) -> int:
    seen: set[bytes] = set()
    for b in blobs:
        seen.update(b[i : i + KEY_BYTES] for i in range(0, len(b), KEY_BYTES))
    return len(seen)


def _round_record(
    ps: _Part, index: int, draws: Mapping[tuple[str, int], Draw], levels: Sequence[int]
) -> list[str]:
    """Apply (i), (ii), (iii) to one part's round; append its record; return the lineages that fail."""
    live = ps.live
    g = len(live)
    d_g = demand(g)
    rec: dict[str, Any] = {"round": index, "G": g, "D_G": d_g, "clusters": {}, "failing": []}
    reasons: dict[str, list[dict[str, Any]]] = {}
    for c in sorted(live):
        k = len(live[c])
        t = demand_lin(g, k)
        crec: dict[str, Any] = {"k": k, "D_lin": t, "lineages": {}, "union_evaluated": False}
        own_fail: dict[str, dict[str, Any]] = {}
        for x in live[c]:
            per_level: dict[str, Any] = {}
            for v in levels:
                dr = draws[(x, v)]
                per_level[str(v)] = dr.summary()
                if dr.count < t:
                    own_fail.setdefault(x, {})[str(v)] = {"count": dr.count, "demand": t, "ended": dr.ended}
            crec["lineages"][x] = per_level
        for x, failed_at in own_fail.items():
            reasons.setdefault(x, []).append({"kind": "own_demand", "levels": failed_at})
        if not own_fail:  # (ii) is read only on a cluster all of whose lineages meet their own demand
            crec["union_evaluated"] = True
            unions = {
                str(v): _union_count([draws[(x, v)].keys for x in live[c]]) for v in levels
            }
            crec["union_by_level"] = unions
            short = {v: n for v, n in unions.items() if n < d_g}
            if short:
                for x in live[c]:
                    reasons.setdefault(x, []).append(
                        {
                            "kind": "cluster_union",
                            "cluster": c,
                            "demand": d_g,
                            "levels": {v: {"union": n, "demand": d_g} for v, n in short.items()},
                        }
                    )
        rec["clusters"][c] = crec
    for c in sorted(live):  # (iii): any disagreement on any item built at any level
        for x in live[c]:
            bad_levels: dict[str, Any] = {}
            for v in levels:
                dr = draws[(x, v)]
                if dr.n_disagreements:
                    first = dr.disagreements[0] if dr.disagreements else None
                    bad_levels[str(v)] = {
                        "n_items": dr.n_disagreements,
                        "first_attempt": dr.first_disagreement_attempt,
                        "first": None
                        if first is None
                        else {
                            "reason": first.reason,
                            "key_answer": first.key_answer,
                            "solver_answer": first.solver_answer,
                        },
                    }
            if bad_levels:
                reasons.setdefault(x, []).append({"kind": "solver_disagreement", "levels": bad_levels})
    failing = sorted(x for x, r in reasons.items() if r)
    rec["failing"] = failing
    cluster_of = {x: c for c in live for x in live[c]}
    for x in failing:
        ps.removed.append(
            {
                "lineage": x,
                "cluster": cluster_of[x],
                "round": index,
                "G": g,
                "k": len(live[cluster_of[x]]),
                "reasons": reasons[x],
            }
        )
    ps.rounds.append(rec)
    return failing


def run_stage4(
    candidates: Mapping[str, Any],
    partition: Mapping[str, Any],
    map_obj: Mapping[str, Any],
    source: Any,
    *,
    workers: int = 1,
    cache_dir: str | Path | None = None,
    cache_tag: str | None = None,
    check_solvers: bool = True,
    levels: Sequence[int] = LEVELS,
    count_fn: Callable[[str, int, int], Draw] | None = None,
    mp_context: str | None = None,
    timings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Section 4A stage 4 for the eight evaluation parts: rounds to a fixed point. Returns the record.

    ``levels`` and ``count_fn`` exist for the tests (a reduced level set, a model of the draws); the run of
    record uses neither, and the record says so. Nothing in the returned record depends on ``workers``.
    """
    parts = build_parts(candidates, partition, map_obj)
    states = [
        _Part(e, p, {c: list(v) for c, v in parts[(e, p)].items()}, {c: list(v) for c, v in parts[(e, p)].items()})
        for e in EVALS
        for p in PARTS
    ]
    runner: CellRunner | _InjectedRunner
    if count_fn is None:
        runner = CellRunner(
            source,
            workers=workers,
            cache_dir=cache_dir,
            cache_tag=cache_tag,
            check_solvers=check_solvers,
            mp_context=mp_context,
        )
    else:
        runner = _InjectedRunner(count_fn)

    def start_round(ps: _Part) -> None:
        """Submit the cells of the part's next round, or close the part if no cluster is left."""
        if not ps.live:
            ps.rounds.append({"round": len(ps.rounds) + 1, "G": 0, "D_G": None, "clusters": {}, "failing": []})
            ps.done = True
            return
        g = len(ps.live)
        tasks: list[tuple[str, int, int]] = []
        for c in sorted(ps.live):
            target = demand_lin(g, len(ps.live[c]))
            tasks.extend((x, v, target) for x in ps.live[c] for v in levels)
        tasks.sort(key=lambda t: (-t[2], t))  # large cells first
        ps.inflight = {t: runner.submit(t) for t in tasks}

    try:
        for ps in states:
            start_round(ps)
        while True:
            running = [ps for ps in states if ps.inflight is not None]
            if not running:
                break
            wait([f for ps in running for f in (ps.inflight or {}).values() if not f.done()], return_when=FIRST_COMPLETED)
            for ps in running:
                assert ps.inflight is not None
                if not all(f.done() for f in ps.inflight.values()):
                    continue
                results = {t: f.result() for t, f in ps.inflight.items()}
                ps.inflight = None
                if timings is not None:
                    for t, r in sorted(results.items()):
                        timings.append({"part": f"{ps.e}{ps.p}", "round": len(ps.rounds) + 1, "lineage": t[0], "level": t[1],
                                        "target": t[2], "seconds": r.seconds, "attempts": r.attempts, "ended": r.ended})
                failing = _round_record(ps, len(ps.rounds) + 1, {(t[0], t[1]): r for t, r in results.items()}, levels)
                if not failing:
                    ps.done = True
                    continue
                gone = set(failing)
                ps.live = {c: [x for x in v if x not in gone] for c, v in ps.live.items()}
                ps.live = {c: v for c, v in ps.live.items() if v}
                start_round(ps)
    finally:
        runner.close()
    out_parts: dict[str, dict[str, Any]] = {e: {} for e in EVALS}
    for ps in states:
        families: list[str] | None = None  # stage 5: the family count of section 4 item 6 is read on the registered lineages
        if source is not None:
            families = sorted({source.lineage(x).family for v in ps.live.values() for x in v})
        out_parts[ps.e][ps.p] = {
            "families": families,
            "n_families": None if families is None else len(families),
            "start": ps.start,
            "rounds": ps.rounds,
            "removed": ps.removed,
            "registered": ps.live,
            "G_start": len(ps.start),
            "G_registered": len(ps.live),
            "lineages_start": sum(len(v) for v in ps.start.values()),
            "lineages_registered": sum(len(v) for v in ps.live.values()),
        }
    return {
        "stage": "ADR-0033 addendum 1 section 4A stage 4",
        "spec": {
            "seed": SEED,
            "stream_labels": [LABEL, "<e>", "<lineage id>", "<level>"],
            "levels": list(levels),
            "attempt_budget": f"{ATTEMPT_FACTOR} * T + {ATTEMPT_BASE}",
            "retry_limit": 500,
            "development_sealed_tuning": [DEV, POOL, TUNING],
            "key": distinct_key.KEY_VERSION,
            "key_bytes": KEY_BYTES,
            "solvers_checked": count_fn is None and check_solvers,
            "counting": "capacity.count" if count_fn is None else "INJECTED count function (tests only)",
            "reduced_levels": list(levels) != list(LEVELS),
        },
        "parts": out_parts,
    }


def dumps(obj: Any) -> bytes:
    return (json.dumps(obj, sort_keys=True, indent=1, ensure_ascii=True) + "\n").encode("ascii")


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--candidates", required=True)
    ap.add_argument("--partition", required=True)
    ap.add_argument("--map", required=True, dest="map_path")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--cache-dir")
    ap.add_argument("--cache-tag")
    ap.add_argument("--no-solvers", action="store_true", help="skip the second-solver check (recorded in the output)")
    ap.add_argument("--timings-out")
    ap.add_argument("--mp-context", choices=["fork", "spawn", "forkserver"], help="start method of the worker processes")
    a = ap.parse_args(argv)
    if os.path.exists(a.out) or (a.timings_out and os.path.exists(a.timings_out)):
        print("refusing to overwrite an output file", file=sys.stderr)
        return 2
    cand = json.load(open(a.candidates))
    part = json.load(open(a.partition))
    mp = json.load(open(a.map_path))
    timings: list[dict[str, Any]] | None = [] if a.timings_out else None
    t0 = time.time()
    out = run_stage4(
        cand, part, mp, RealSource(), workers=a.workers, cache_dir=a.cache_dir, cache_tag=a.cache_tag,
        check_solvers=not a.no_solvers, timings=timings, mp_context=a.mp_context,
    )
    out["inputs"] = {
        "candidates": a.candidates, "partition": a.partition, "map": a.map_path,
        "sha256": {
            k: hashlib.sha256(Path(v).read_bytes()).hexdigest()
            for k, v in (("candidates", a.candidates), ("partition", a.partition), ("map", a.map_path))
        },
        "cache_tag": a.cache_tag,
    }
    with open(a.out, "xb") as f:
        f.write(dumps(out))
    if a.timings_out and timings is not None:
        with open(a.timings_out, "xb") as f:
            f.write(dumps({"wall_seconds": round(time.time() - t0, 1), "cells": timings}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
