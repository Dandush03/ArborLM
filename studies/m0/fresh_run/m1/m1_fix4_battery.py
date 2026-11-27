# ruff: noqa: E501
"""M1 fix round 4: the union cheap-rule battery on the fix-4 set (lead ruling R-24, R-26).

Union = (1) the implementer's battery ``m1_fix3_shortcuts`` run by its own scoring, (2) the audit-4 script ``shortcuts_a4.py`` (its own ``a4:`` rules, three fitted generic rules and the ``im:`` copy of (1)),
(3) the audit-3 rule definitions ``shortcuts_a3.spec`` scored as audit 3 scored them (held-out most-frequent-answer base, echo by best position). The auditors' scripts are READ from the audit directories
(``docs/reviews/m0-lineage-decision-2026-11-25/audit3_m1`` and ``audit4_m1``) with ``importlib`` and never modified; only their loader (``common_a4`` / ``common_a3``) is replaced, in memory, by the fix-4 set, so the
rule definitions and the scoring are the auditors' own. Audit-3 rules were written for the rev2 structured fields: a rule that raises on a fix-3/4 structured form (a field that no longer exists) is skipped for that
item and counted in ``a3_skipped``. Nothing here imports outside the standard library, torch or ``studies``; nothing enters ``core.REGISTRY``; no model is run.

Excluded as the correct procedure (not cheap rules; judged by the audit-4 auditor in ``short_summary_a4.PROC`` and by the implementer in ``m1_fix3_shortcuts.PROCEDURE``; names are compared without their source prefix):
see ``procedure_exclusions``. Every excluded rule's largest effect is still recorded separately so the lead can see it.

Usage (from the worktree, PYTHONHASHSEED=0 PYTHONPATH=<worktree>):
  python -m studies.m0.m1_fix4_battery --n 2000 --workers 6 --out <battery.json> [--only name,name]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
import types
from collections import Counter
from fractions import Fraction as F
from pathlib import Path
from typing import Any

from studies.m0.core import ALL_LEVELS
from studies.m0.lineages_m1_fix4 import load_all, load_registered, stem

ROOT = Path("/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f")
AUDIT_DIR = ROOT / "docs" / "reviews" / "m0-lineage-decision-2026-11-25"
A3 = AUDIT_DIR / "audit3_m1"
A4 = AUDIT_DIR / "audit4_m1"
SOURCES = ("own", "a4", "a3")
PREFIX = ("im:", "a4:", "a3:", "own:")

# audit-4 auditor's list of rules judged to be the correct procedure (short_summary_a4.PROC, copied; keys are stems, names carry their prefix)
A4_PROC: dict[str, tuple[str, ...]] = {
    "consecutive": ("im:mean_plus_step",),
    "division_counting": ("im:k_minus_remainder_ignores_exact_fit",),
    "finite_differences": ("im:next_term_when_asked_later", "im:next_term_only"),
    "gcd_lcm": ("im:product_over_gcd_of_all", "a4:product_over_gcd_pow_k_minus_1 (k>=3; a false general rule)", "a4:product_over_lcm_pow_k_minus_1 (k>=3; a false general rule)"),
    "ratio_share": ("im:largest_share", "im:smallest_share"),
    "prime_factors": ("im:largest_le_sqrt",),
    "slot_permutations": ("im:ignore_first_rule", "im:parity_fraction_of_total"),
    "last_digit_power": ("im:fermat_misapplied_e_mod_p_plus_1",),
}


def _norm(name: str) -> str:
    for p in PREFIX:
        if name.startswith(p):
            return name[len(p):]
    return name


def procedure_exclusions() -> dict[str, list[str]]:
    """stem -> sorted rule names (without prefix) excluded as the correct procedure: the audit-4 auditor's list plus the implementer's ``PROCEDURE``, plus the audit-3 name of the same rule."""
    from studies.m0.fresh_run.m1.m1_fix3_shortcuts import PROCEDURE

    out: dict[str, set[str]] = {}
    for st, names in A4_PROC.items():
        out.setdefault(st, set()).update(_norm(n) for n in names)
    for st, d in PROCEDURE.items():
        out.setdefault(st, set()).update(d)
    return {k: sorted(v) for k, v in sorted(out.items())}


def _load(path: Path, name: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, str(path))
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _current_set(include_not_registered: bool = False) -> dict[str, Any]:
    return {x.id: x for x in (load_all() if include_not_registered else load_registered())}


def a4_module() -> types.ModuleType:
    """``shortcuts_a4`` with its loader replaced by the fix-4 set (the auditor's code is unchanged)."""
    common = _load(A4 / "common_a4.py", "common_a4")
    common.current_set = _current_set  # type: ignore[attr-defined]
    common.stem = stem  # type: ignore[attr-defined]
    return _load(ROOT / "studies" / "m0" / "fresh_run" / "m1" / "shortcuts_a4.py", "shortcuts_a4_fix4")


def a3_module() -> tuple[types.ModuleType, types.ModuleType]:
    common = _load(A3 / "common_a3.py", "common_a3")
    common.current_set = _current_set  # type: ignore[attr-defined]
    return common, _load(ROOT / "studies" / "m0" / "fresh_run" / "m1" / "shortcuts_a3.py", "shortcuts_a3_fix4")


def own_task(args: tuple[str, int]) -> tuple[str, dict[str, Any]]:
    """The implementer's battery with its own scoring, on the fix-4 set (its loader and stem function are replaced in memory)."""
    import studies.m0.fresh_run.m1.m1_fix3_shortcuts as sc

    sc.all_lineages = lambda before: _current_set(True)  # type: ignore[assignment]
    sc.stem_of = stem  # type: ignore[assignment]
    lid, n = args
    return sc.run((lid, n, False))


def a4_task(args: tuple[str, int]) -> tuple[str, dict[str, Any]]:
    mod = a4_module()
    return mod.run(args)  # type: ignore[no-any-return]


def a3_task(args: tuple[str, int]) -> tuple[str, dict[str, Any]]:
    """Audit-3 scoring (``shortcuts_a3.run``) with the rev2 name mapping, and a guard around rules written for fields that no longer exist."""
    common, mod = a3_module()
    lid, n_items = args
    lin = _current_set(True)[lid]
    n = stem(lid)
    n = "power_remainder" if n == "last_digit_power" else n
    out: dict[str, Any] = {}
    skipped = 0
    for lv in ALL_LEVELS:
        its = common.items(lin, lv, n_items, mod.SEED, "short")
        ans = [F(it.answer) for it in its]
        a_, b_ = ans[0::2], ans[1::2]
        mode_a = Counter(a_).most_common(1)[0][0]
        mode_b = Counter(b_).most_common(1)[0][0]
        base = (sum(x == mode_a for x in b_) / len(b_) + sum(x == mode_b for x in a_) / len(a_)) / 2
        numl = [mod.nums(it.question) for it in its]
        cands = {"first": lambda L: L[0], "second": lambda L: L[1] if len(L) > 1 else None, "last": lambda L: L[-1], "max": max, "min": min,
                 "sum": lambda L: sum(L), "max_minus_min": lambda L: max(L) - min(L), "second_last": lambda L: L[-2] if len(L) > 1 else None}

        def rate(fn: Any, idx: list[int], numl: list[Any] = numl, ans: list[F] = ans) -> float:
            return sum(1 for i in idx if numl[i] and fn(numl[i]) == ans[i]) / len(idx)

        ev, od = list(range(0, n_items, 2)), list(range(1, n_items, 2))
        best_a = max(cands, key=lambda k: rate(cands[k], ev))
        best_b = max(cands, key=lambda k: rate(cands[k], od))
        echo = (rate(cands[best_a], od) + rate(cands[best_b], ev)) / 2
        rates: dict[str, float] = {f"echo_best_position[{best_a}/{best_b}]": echo}
        sp: list[dict[str, Any]] = []
        for it in its:
            try:
                sp.append(mod.spec(n, it.structured, it.question))
            except Exception:  # a rule written for a rev2 field that no longer exists
                skipped += 1
                sp.append({})
        for k in sorted({k for d in sp for k in d}):
            app = [(d[k], a) for d, a in zip(sp, ans, strict=True) if d.get(k) is not None]
            rates[k] = sum(1 for v, a in app if v == a) / n_items
        out[str(lv)] = {"N": n_items, "base": round(base, 4), "rates": {k: round(v, 4) for k, v in rates.items()}, "minus_base": {k: round(v - base, 4) for k, v in rates.items()}}
    out["a3_skipped_items"] = skipped  # type: ignore[assignment]
    return lid, out


def _task(args: tuple[str, str, int]) -> tuple[str, str, dict[str, Any]]:
    src, lid, n = args
    fn = {"own": own_task, "a4": a4_task, "a3": a3_task}[src]
    return src, lid, fn((lid, n))[1]


def summarise(res: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    """Per lineage and level: the largest |rate - base| over the union of non-excluded rules (with the rule's name and source), and the same for the excluded rules.
    ``rates`` are over all items (a rule that does not apply counts as a miss), as the scripts measure them; ``__within_applicable`` duplicates are not rules."""
    excl = procedure_exclusions()
    out: dict[str, Any] = {}
    lids = sorted({lid for s in res.values() for lid in s})
    for lid in lids:
        st = stem(lid)
        ex = set(excl.get(st, []))
        per: dict[str, Any] = {}
        for lv in ALL_LEVELS:
            best: tuple[float, str, str] = (0.0, "", "")
            best_ex: tuple[float, str, str] = (0.0, "", "")
            base_by: dict[str, float] = {}
            for src in SOURCES:
                r = res.get(src, {}).get(lid, {}).get(str(lv))
                if not r:
                    continue
                base_by[src] = r["base"]
                for k, v in r["minus_base"].items():
                    if k.endswith("__within_applicable"):
                        continue
                    nm = _norm(k)
                    if nm.startswith("echo_best_position["):
                        nm = "echo_best_position"
                    label = k if k.startswith(("a4:", "im:")) else f"{src}:{k}"  # the audit-4 script already prefixes its rules ("a4:" its own, "im:" the implementer's copy)
                    if nm in ex:
                        if abs(v) > abs(best_ex[0]):
                            best_ex = (v, label, src)
                    elif abs(v) > abs(best[0]):
                        best = (v, label, src)
            per[str(lv)] = {"max_abs_excess": round(abs(best[0]), 4), "signed": round(best[0], 4), "rule": best[1], "base_by_source": base_by,
                            "excluded_procedure_max_signed": round(best_ex[0], 4), "excluded_procedure_rule": best_ex[1]}
        out[lid] = per
    return out


def main() -> None:
    import multiprocessing as mp

    ap = argparse.ArgumentParser(description="M1 fix-4 union battery")
    ap.add_argument("--n", type=int, default=2000)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    ids = sorted(_current_set(True))
    if a.only:
        ids = [i for i in ids if any(o in i for o in a.only.split(","))]
    t0 = time.time()
    tasks = [(src, lid, a.n if "digit_puzzle" not in lid else min(a.n, 300)) for lid in ids for src in SOURCES]
    res: dict[str, dict[str, dict[str, Any]]] = {s: {} for s in SOURCES}
    with mp.get_context("spawn").Pool(a.workers) as pool:
        for src, lid, r in pool.imap_unordered(_task, tasks, chunksize=1):
            res[src][lid] = r
            print(src, lid, round(time.time() - t0), flush=True)
    summ = summarise(res)
    Path(a.out).write_text(json.dumps({"n": a.n, "seeds": {"own": 410302, "a4": 17, "a3": 5}, "exclusions": procedure_exclusions(), "raw": res, "summary": summ}, indent=1, sort_keys=True))
    print("seconds", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
