# ruff: noqa: E501
"""P10IR gates (ADR-0029 section 11). Each gate returns a dict ``{"scope", "passed", "status", ...detail}``; ``passed`` is True, False, or None where a bit-exact gate was skipped because the machine is not
the platform of record (section 13). The scope says which label a failure voids (section 11): ``tree`` (the T-OQ checkpoint), ``f0`` (F0 of the F-OQ checkpoint: voids both labels) or ``index``.

Gate 1 identities, gate 2 count reproduction (bit-exact), gate 3 recall reproduction (sealed values; equal or not equal only), gate 4 exactness identities (tolerance gates, with the float-tie
definition of the third review R3-6), gate 5 rehearsal, gate 6 seeds, the adapter identity gate (stage A2). Gates 1 to 3, the index rebuild and the adapter identity gate are bit-exact and are
made on the platform of record only; elsewhere they are recorded as skipped and the tolerance gates still run.
"""

import platform
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import torch

from arborlm.io import file_sha256, sha256
from studies.p10s1 import core as s1core
from studies.p10s1 import index as s1index

from . import core, reads, sealed

if TYPE_CHECKING:
    from torch import Tensor

    from studies.p10s1.model import S1Memory

PASSED, FAILED, SKIPPED = "passed", "failed", "skipped"


# --- the platform of record (section 13) ---------------------------------------------------------------------------------------------------------------------
def platform_record() -> dict[str, Any]:
    return {
        "system": platform.system(), "machine": platform.machine(), "release": platform.release(), "platform": platform.platform(), "torch": torch.__version__,
        "torch_num_threads": torch.get_num_threads(), "torch_interop_threads": torch.get_num_interop_threads(), "deterministic_algorithms": bool(torch.are_deterministic_algorithms_enabled()),
    }  # fmt: skip


def platform_problems(cfg: Mapping[str, Any] | None = None, record: Mapping[str, Any] | None = None) -> list[str]:
    """What differs from the platform of record: macOS arm64, torch 2.8.0, one thread, one interop thread, deterministic algorithms on."""
    want = (cfg or core.load_config())["platform"]
    have = record or platform_record()
    problems = []
    for k_have, k_want in (("system", "system"), ("machine", "machine"), ("torch", "torch"), ("torch_num_threads", "torch_num_threads"), ("torch_interop_threads", "torch_interop_threads"), ("deterministic_algorithms", "deterministic_algorithms")):
        if have[k_have] != want[k_want] and not (k_have == "torch" and str(have[k_have]).split("+")[0] == want[k_want]):
            problems.append(f"{k_have}: {have[k_have]!r}, the platform of record has {want[k_want]!r}")
    return problems


def on_platform_of_record(cfg: Mapping[str, Any] | None = None, record: Mapping[str, Any] | None = None) -> bool:
    return not platform_problems(cfg, record)


def gate(scope: str, passed: bool | None, **detail: Any) -> dict[str, Any]:
    """A gate result. ``passed`` None means skipped (not the platform of record)."""
    if scope not in ("tree", "f0", "index"):
        raise ValueError(f"unknown gate scope {scope!r}")
    return {"scope": scope, "passed": passed, "status": SKIPPED if passed is None else PASSED if passed else FAILED, **detail}


def exact(scope: str, fn: Callable[[], tuple[bool, dict[str, Any]]], cfg: Mapping[str, Any] | None = None, record: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """A bit-exact gate: run ``fn`` only on the platform of record, else record it as skipped (with the reason)."""
    problems = platform_problems(cfg, record)
    if problems:
        return gate(scope, None, reason="not the platform of record: " + "; ".join(problems))
    ok, detail = fn()
    return gate(scope, bool(ok), **detail)


# --- gate 4: exactness identities, with the precision each can have ---------------------------------------------------------------------------------------------
@torch.no_grad()
def compare_selection(a_ids: "Tensor", a_vals: "Tensor", b_ids: "Tensor", b_vals: "Tensor", th: core.Thresholds) -> dict[str, Any]:
    """Two reads of the same facts (``[F, >= 9]`` ids and scores in selection order, scores = cos / 0.2 plus any prior, float32): the selected sets must be identical except at float ties, which are counted
    (more than ``tie_share_max`` of the facts fails the gate); weights equal within ``weight_tolerance`` absolute, slot by slot (aligned by slot id), on the facts whose sets are identical. A fact's
    difference is a float tie if, in either computation, the 8th and 9th largest scores differ by at most ``tie_margin``."""
    top = s1core.TOP
    n = int(a_ids.shape[0])
    sa, order_a = a_ids[:, :top].sort(dim=-1)
    sb, order_b = b_ids[:, :top].sort(dim=-1)
    equal = (sa == sb).all(dim=-1)
    gap_a = (a_vals[:, top - 1] - a_vals[:, top]).abs()
    gap_b = (b_vals[:, top - 1] - b_vals[:, top]).abs()
    tie = (gap_a <= th.tie_margin) | (gap_b <= th.tie_margin)
    differ = ~equal
    non_tie = differ & ~tie
    wa = a_vals[:, :top].softmax(-1).gather(1, order_a)
    wb = b_vals[:, :top].softmax(-1).gather(1, order_b)
    diff = (wa - wb).abs().max(dim=1).values
    max_diff = float(diff[equal].max()) if bool(equal.any()) else 0.0
    ties = int((differ & tie).sum())
    tie_share = ties / max(1, n)
    passed = int(non_tie.sum()) == 0 and tie_share <= th.tie_share_max and max_diff <= th.weight_tolerance
    return {
        "passed": bool(passed), "facts": n, "sets_differ": int(differ.sum()), "float_ties": ties, "float_tie_share": tie_share, "not_float_ties": int(non_tie.sum()), "max_weight_difference": max_diff,
        "tie_margin": th.tie_margin, "weight_tolerance": th.weight_tolerance, "tie_share_max": th.tie_share_max,
    }  # fmt: skip


@torch.no_grad()
def _collect(fn: Callable[["Tensor"], "tuple[Tensor, Tensor]"], codes: "Tensor", chunk: int) -> "tuple[Tensor, Tensor]":
    ids, vals = [], []
    for start in range(0, codes.shape[0], chunk):
        v, i = fn(codes[start : start + chunk])
        ids.append(i[:, : s1core.TOP + 1])
        vals.append(v[:, : s1core.TOP + 1])
    return torch.cat(ids), torch.cat(vals)


@torch.no_grad()
def exactness_gates(source: "S1Memory", codes: "Tensor", th: core.Thresholds, *, chunk_elements: int, chunk: int = reads.FACT_CHUNK) -> dict[str, dict[str, Any]]:
    """The tolerance gates of one tree checkpoint, all at fact level over the facts' oracle codes:

    * Tv with v = 1, priors on against off: mathematically the same read (the prior is one constant of the only branch visited);
    * T3 and T2 (the common path at v = N/256) against an independent flat computation (``q @ keys.T`` over all keys, with and without the per-key prior)."""
    keys, router = cast("Tensor", source.keys), cast("Tensor", source.router)
    per, branches = source.spec.per_branch, source.spec.branches

    def tree(v: int, prior: bool) -> Callable[["Tensor"], "tuple[Tensor, Tensor]"]:
        def run(q: "Tensor") -> "tuple[Tensor, Tensor]":
            out = reads.tree_path(keys, router, q, v, prior, prior, per=per, chunk_elements=chunk_elements)
            return out.values, out.ids

        return run

    def flat(prior: bool) -> Callable[["Tensor"], "tuple[Tensor, Tensor]"]:
        return lambda q: reads.independent_flat(keys, router, q, prior, per=per, chunk_elements=chunk_elements)

    out: dict[str, dict[str, Any]] = {}
    pairs = {
        "tv1_priors_on_against_off": (tree(1, True), tree(1, False)),
        "t3_against_independent_flat": (tree(branches, True), flat(True)),
        "t2_against_independent_flat": (tree(branches, False), flat(False)),
    }
    for name, (fa, fb) in pairs.items():
        ia, va = _collect(fa, codes, chunk)
        ib, vb = _collect(fb, codes, chunk)
        res = compare_selection(ia, va, ib, vb, th)
        out[name] = gate("tree", res.pop("passed"), **res)
    return out


def index_rebuild_gate(keys: "Tensor", seed: int, lists: int | None, cfg: Mapping[str, Any] | None = None, record: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """An index is bit-identical on rebuild with the same seed (centroids, assignment, hash), on the platform of record."""

    def run() -> tuple[bool, dict[str, Any]]:
        a = s1index.build_index(keys, seed, lists)
        b = s1index.build_index(keys, seed, lists)
        same = a.sha256() == b.sha256() and torch.equal(a.centroids, b.centroids) and torch.equal(a.assign, b.assign)
        return same, {"index_sha256": a.sha256(), "lists": a.lists, "seed": seed}

    return exact("index", run, cfg, record)


# --- gate 2: count reproduction (bit-exact) ---------------------------------------------------------------------------------------------------------------------
def counts_gate(scope: str, mine: Mapping[str, Any], recorded: Mapping[str, Any], *, source: str, cfg: Mapping[str, Any] | None = None, record: Mapping[str, Any] | None = None, extra_equal: Mapping[str, bool] | None = None) -> dict[str, Any]:
    """Correct and useful counts (and n) on both panels equal the recorded ones exactly (``source`` says what they were recorded by: P10-S1's eval record, or P10-S1's evaluation functions called from the
    adapter, for stage A2). ``extra_equal`` adds named equalities (the index hash)."""

    def run() -> tuple[bool, dict[str, Any]]:
        same = sealed.counts_equal({p: mine[p] for p in mine}, {p: recorded[p] for p in recorded})
        extra = dict(extra_equal or {})
        return same and all(extra.values()), {"source": source, "counts_equal": same, **{k: v for k, v in extra.items()}}

    return exact(scope, run, cfg, record)


def path_gate(checked: int, mismatched: int, cfg: Mapping[str, Any] | None = None, record: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Gate 2, T0's path: the common tree path's selected slot ids and scores equal the top 8 of ``S1Memory._top_tree`` bit for bit on every query of Panel A and Panel B, main and address-swap reads
    included (R3-1). ``checked`` counts the queries served, and must be positive."""

    def run() -> tuple[bool, dict[str, Any]]:
        return checked > 0 and mismatched == 0, {"queries_checked": checked, "queries_mismatched": mismatched}

    return exact("tree", run, cfg, record)


def recall_gates(run_dir: Path, tree_label: str | None, flat_label: str | None, update: int, *, tree_recall_value: float | None, ivf_recall_value: float | None, cfg: Mapping[str, Any] | None = None, record: Mapping[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    """Gate 3 (sealed values). (a) P10-S1's ``tree_recall``, recomputed as P10-S1 defined it, equals the recorded quantity at U_P (tree scope); (b) P10-S1's index recall, recomputed as P10-S1 defined it,
    equals the recorded quantity at every checkpoint read (index scope). The result is equal or not equal: no value is returned or printed. These quantities are not CR8 and enter no label."""
    out: dict[str, dict[str, Any]] = {}
    if tree_label is not None and tree_recall_value is not None:
        out["tree_recall_reproduction"] = exact("tree", lambda: _eq(sealed.sealed_equal(run_dir, tree_label, update, "tree_recall", tree_recall_value)), cfg, record)
    if flat_label is not None and ivf_recall_value is not None:
        out["ivf_recall_reproduction"] = exact("index", lambda: _eq(sealed.sealed_equal(run_dir, flat_label, update, "ivf_recall", ivf_recall_value)), cfg, record)
    return out


def _eq(equal: bool) -> tuple[bool, dict[str, Any]]:
    return equal, {"equal": equal}


# --- gate 6: seeds -------------------------------------------------------------------------------------------------------------------------------------------------
def planned_seed_values(cfg: Mapping[str, Any] | None = None) -> dict[str, frozenset[int]]:
    """Every integer the study uses by role: the bridge sets (with their H8, mask and index seeds), the bridge initialisations and their derived seeds (+ 1000 k), the I64 seeds, the rehearsal set and
    initialisation, test mode. The declared re-uses (P10-S1's draws and cell) are listed apart."""
    c = cfg or core.load_config()
    bridge: set[int] = set()
    for d in range(1, int(c["seeds"]["bridge_draws"]) + 1):
        bridge |= set(core.seed_set_values(core.bridge_seeds(d, c)))
    inits = {core.bridge_init_seed(d, c) for d in range(1, int(c["seeds"]["bridge_draws"]) + 1)} | {int(c["seeds"]["rehearsal_init"])} | {int(x) for x in c["seeds"]["test_init"]}
    derived = {i + k for i in inits for k in s1core.DERIVED_INIT_OFFSETS}
    return {
        "bridge_sets": frozenset(bridge), "i64_index_seeds": frozenset(core.i64_seeds(c)), "test_index_seeds": frozenset(core.i64_seeds(c, test=True)), "rehearsal_set": frozenset(core.seed_set_values(core.rehearsal_seeds(c))), "initialisation": frozenset(inits),
        "derived_initialisation": frozenset(derived), "test_sets": frozenset(v for k in range(9) for v in core.seed_set_values(core.test_seeds(k, c))),
    }  # fmt: skip


def declared_reuse(cfg: Mapping[str, Any] | None = None) -> dict[str, frozenset[int]]:
    c = cfg or core.load_config()
    p10s1 = frozenset(v for d in range(1, 6) for v in core.seed_set_values(core.p10s1_draw_seeds(d, c)))
    init = int(c["seeds"]["p10s1_init_base"]) + int(c["seeds"]["identity_gate_draw"])
    images = [init + k for k in s1core.DERIVED_INIT_OFFSETS]  # 3101 .. 7101 (the R2 images of the initialisation seed)
    gate_cell = frozenset([init, *images, *core.seed_set_values(core.p10s1_draw_seeds(int(c["seeds"]["identity_gate_draw"]), c))])  # 38 values: registry section 4.6
    return {"p10s1_registered_draws_160_values": p10s1, "adapter_identity_gate_draw_1": gate_cell}


# The registry's checker (revision 3) inventories every ``configs/*.toml`` and every seed-like literal of ``src``, ``studies`` and ``tests`` and asserts that no P10-I allocation collides with the inventory. Once
# this study has its own config and tests, its own allocation hits "its own inventory" and the checker as cited prints RESULT: FAIL by construction. ADR-0029 section 5 therefore says the gate runs *a copy
# extended with these named values*: the copy below differs from the cited file by exactly these three substitutions, all listed in the gate result with the SHA-256 of the copy. Nothing else is changed and
# the cited file is not edited.
CHECKER_SUBSTITUTIONS: tuple[tuple[str, str], ...] = (
    ("ROOT = Path(__file__).resolve().parents[3]", "ROOT = Path({root!r})"),
    ('for path in sorted((ROOT / "configs").glob("*.toml")):', 'for path in [q for q in sorted((ROOT / "configs").glob("*.toml")) if q.name != "p10ir_routing.toml"]:'),
    ('for path in sorted((ROOT / d).rglob("*.py")):', 'for path in [q for q in sorted((ROOT / d).rglob("*.py")) if "p10ir" not in q.name and "p10ir" not in q.parts]:'),
)


def allocation_rows(checker_text: str) -> list[tuple[str, int, int]]:
    """The rows of ADR-0029 in the cited checker's ``ALLOC`` table: (role, low, high)."""
    import re

    return [(m[1], int(m[2]), int(m[3])) for m in re.finditer(r'\("P10-I-R ADR-0029", "([^"]*)", (\d+), (\d+)\)', checker_text)]


def allocation_problems(cfg: Mapping[str, Any], rows: Sequence[tuple[str, int, int]]) -> list[str]:
    """Ruling 6, the separate check: every range the config assigns to a role of this study lies inside the registry's ALLOC row of that role, and every planned value inside the config's range of its role."""
    want = {"bridge": "data: bridge draw sets", "index": "I64 index seeds", "rehearsal": "rehearsal draw set", "init": "init sub-row", "test": "test"}
    problems = []
    for key, prefix in want.items():
        lo, hi = (int(x) for x in cfg["seed_ranges"][key])
        if not any(r[0].startswith(prefix) and r[1] <= lo and hi <= r[2] for r in rows):
            problems.append(f"the config's {key} range {lo}-{hi} is not inside a registry allocation row '{prefix}...' of ADR-0029")
    return problems


def checker_copy(original: str, root: Path) -> str:
    """The text of the extended copy: the cited file with ``CHECKER_SUBSTITUTIONS`` applied (each must match exactly once)."""
    out = original
    for old, new in CHECKER_SUBSTITUTIONS:
        if out.count(old) != 1:
            raise ValueError(f"the checker file does not contain the line to extend exactly once: {old!r}")
        out = out.replace(old, new.format(root=str(root)))
    return out


def run_checker_copy(path: Path, root: Path, timeout: float) -> dict[str, Any]:
    import tempfile

    text = checker_copy(path.read_text(encoding="utf-8"), root)
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "seed_registry_check_r3_p10ir.py"
        copy.write_text(text, encoding="utf-8")
        proc = subprocess.run([sys.executable, str(copy)], cwd=root, capture_output=True, text=True, timeout=timeout, check=False)  # noqa: S603
    result = next((line for line in proc.stdout.splitlines() if line.startswith("RESULT:")), None)
    return {"returncode": proc.returncode, "result_line": result, "copy_sha256": sha256(text.encode()), "substitutions": [old for old, _ in CHECKER_SUBSTITUTIONS]}


def seed_gate(cfg: Mapping[str, Any] | None = None, *, root: Path | None = None, run_checker: bool = True, timeout: float = 300.0) -> dict[str, Any]:
    """Gate 6. (1) every planned value lies in the range the registry allocates to its role (config ``[seed_ranges]``); (2) the planned roles are pairwise disjoint and disjoint from the declared re-uses,
    which are listed as re-used and not as new; (3) the registry's checker file (revision 3; its SHA-256 is in the config and must match) is run as the extended copy above and must print ``RESULT: PASS``."""
    c = cfg or core.load_config()
    base = root or core.repo_root()
    ranges = c["seed_ranges"]
    planned = planned_seed_values(c)
    allowed = {
        "bridge_sets": [ranges["bridge"]], "i64_index_seeds": [ranges["index"]], "test_index_seeds": [ranges["test"]], "rehearsal_set": [ranges["rehearsal"]], "initialisation": [ranges["init"]], "derived_initialisation": [],
        "test_sets": [ranges["test"]],
    }  # fmt: skip
    problems: list[str] = []
    for role, values in planned.items():
        if role == "derived_initialisation":
            continue
        out_of_range = sorted(v for v in values if not any(lo <= v <= hi for lo, hi in allowed[role]))
        if out_of_range:
            problems.append(f"{role}: values outside the registry's range: {out_of_range[:5]}")
    names = sorted(planned)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            common = planned[a] & planned[b]
            if common:
                problems.append(f"{a} and {b} share {sorted(common)[:5]}")
    reuse = declared_reuse(c)
    flat_planned = frozenset().union(*planned.values())
    for name, vals in reuse.items():
        common = flat_planned & vals
        if common:
            problems.append(f"a planned value is also a declared re-use ({name}): {sorted(common)[:5]}")
    checker_path = base / ranges["checker"]
    checker: dict[str, Any] = {"path": ranges["checker"], "expected_sha256": ranges["checker_sha256"]}
    if checker_path.is_file():
        checker["sha256"] = file_sha256(checker_path)
        if checker["sha256"] != ranges["checker_sha256"]:
            problems.append("the registry checker file differs from the SHA-256 the ADR cites")
        else:
            rows = allocation_rows(checker_path.read_text(encoding="utf-8"))
            checker["allocation_rows"] = len(rows)
            problems += allocation_problems(c, rows) if rows else ["no ADR-0029 rows in the checker's ALLOC table"]
        if checker["sha256"] == ranges["checker_sha256"] and run_checker:
            checker.update(run_checker_copy(checker_path, base, timeout))
            if checker["returncode"] != 0 or checker["result_line"] != "RESULT: PASS":
                problems.append(f"the extended registry checker did not print RESULT: PASS (returncode {checker['returncode']}, {checker['result_line']})")
    else:
        problems.append(f"the registry checker is not at {ranges['checker']}")
    return {
        "passed": not problems, "problems": problems, "roles": {k: len(v) for k, v in planned.items()},
        "declared_reuse_not_new": {k: len(v) for k, v in reuse.items()}, "checker": checker,
    }  # fmt: skip


def rehearsal_gate(record: Mapping[str, Any] | None, required: Sequence[str], *, plan_file_sha256: str | None = None) -> dict[str, Any]:
    """Gate 5: the rehearsal record (``rehearsal.py``) says every required stage ran end to end against the rehearsal's plans with status COMPLETE, that gates 1 and 2 were run on the registered checkpoints
    themselves and passed (they compare counts already seen, so this observes nothing new; gate 3 is not run before the freeze), and (ruling 5), when ``plan_file_sha256`` is given, that the candidate
    ``plan.json`` was rehearsed and that the record names the SHA-256 of the file now in ``freeze/``."""
    if record is None:
        return {"passed": False, "missing": list(required), "reason": "no rehearsal record"}
    done = {s: v for s, v in (record.get("stages") or {}).items() if v.get("status") == "COMPLETE"}
    missing = [s for s in required if s not in done]
    registered = record.get("registered_checkpoint_gates") or {}
    ok_registered = registered.get("gate1_passed") is True and registered.get("gate2_passed") is True and registered.get("gate3_run") is False
    out: dict[str, Any] = {"missing": missing, "registered_checkpoint_gates_ok": ok_registered}
    ok = not missing and ok_registered
    if plan_file_sha256 is not None:
        cand = record.get("candidate") or {}
        ok_plan = cand.get("status") == "COMPLETE" and cand.get("plan_file_sha256") == plan_file_sha256
        out["candidate_plan_rehearsed_with_this_file"] = ok_plan
        ok = ok and ok_plan
    out["passed"] = ok
    return out
