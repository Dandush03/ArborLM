# ruff: noqa: E501
"""Independent recomputation from the stored per-item records (ADR-0025 section 8.6; audit R5, N5; rulings 8 and 11) and the A4 report readings (sections 5.3 and 8.5; ruling 23).

The evaluate stage stores, for every registered score that has items, the per-item scores (chrF-norm per item), the exact-match flags and the greedy token sequences (``item_records.json``, keyed by the registry key
of the read), for GEN the per-window negative log-likelihoods of the unmodified student and of the arm at both decision positions with the router's decisions and the window strata, and for E_A and E_B the
word-level edit-distance-1 flag of each item against the replicate's training sources. This module recomputes every figure that rests on them from those records ALONE, in plain Python (no model, no engine, no
torch): the mean of the stored per-item scores is the read, the exact-match rate is the ``em:`` read, and a ``gen:`` read is the panel loss increase (equal weight on the marker and ordinary stratum means) of the
stored per-window losses. ``recompute_registry`` returns what the stored records reproduce; ``compare`` lists every registry key whose stored value differs.

What remains NOT item-based, and is not reproduced here: ``modification`` (recomputable from the snapshots with one's own code), the router's route accuracy and false-trigger counts, R-exact hit counts, and the
combined C1/C2 means (their records carry item scores; ``partt_recompute.combined_means`` compares them by the frozen code only). The records do NOT recompute the per-item chrF from text: that needs a decoder
and a chrF of one's own, for which the stored sequences, the teacher's stored answer texts and the references in the bundle are enough."""

import math
from collections.abc import Mapping, Sequence
from typing import Any

TOLERANCE = 1e-12  # the mean of floats summed in a fixed order: the stored items are the very numbers the mean was taken over
STRATA = ("marker", "ordinary")


def _mean(xs: Sequence[float]) -> float:
    return math.fsum(xs) / len(xs) if xs else float("nan")


def panel_mean(values: Sequence[float], strata: Sequence[str]) -> float:
    """The GEN panel loss: the equal-weight mean of the marker-like and the ordinary stratum means (the lead's ruling of 2026-11-16), a stratum with no window left out."""
    means = [_mean([v for v, s in zip(values, strata, strict=True) if s == name]) for name in STRATA if any(s == name for s in strata)]
    return math.fsum(means) / len(means) if means else float("nan")


def gen_value(rec: Mapping[str, Any]) -> float:
    """``gen:token64`` / ``gen:first_marker`` from a stored per-window record: the arm's panel loss less the unmodified student's."""
    g = rec["gen"]
    return panel_mean(g["nll_arm"], g["strata"]) - panel_mean(g["nll_base"], g["strata"])


def recompute_registry(items: Mapping[str, Mapping[str, Any]]) -> dict[str, float]:
    """Registry key -> value, from the per-item records only. A record keyed ``arm|order|rep|s:E_A`` gives that key (mean of items) and ``arm|order|rep|em:E_A`` (mean of exact flags, 1.0 for true); a ``gen:`` record
    gives its loss increase; every other record with items (``lr:``, ``dcon:``, ``sub:*``, ``seen:``, ``open:``) gives its own key (mean of items). Flag records (``edit1``) give nothing."""
    out: dict[str, float] = {}
    for k, rec in items.items():
        if "gen" in rec:
            out[k] = gen_value(rec)
            continue
        if "items" not in rec:
            continue
        out[k] = _mean(rec["items"])
        if k.rsplit("|", 1)[1].startswith("s:") and "exact" in rec:
            out[k.rsplit("|", 1)[0] + "|em:" + k.rsplit("|", 1)[1][2:]] = _mean([1.0 if x else 0.0 for x in rec["exact"]])
    return out


def compare(registry: Mapping[str, float], items: Mapping[str, Mapping[str, Any]], tolerance: float = TOLERANCE) -> dict[str, Any]:
    """Every key the stored items reproduce, against the registry: the keys that differ, the keys the items reproduce that the registry lacks, and the registry keys no item record covers."""
    again = recompute_registry(items)
    differ = [{"key": k, "registry": registry[k], "from_items": v} for k, v in sorted(again.items()) if k in registry and abs(registry[k] - v) > tolerance]
    return {"checked": sum(1 for k in again if k in registry), "differ": differ, "not_in_registry": sorted(k for k in again if k not in registry), "not_covered_by_items": sorted(k for k in registry if k not in again)}


def compare_items(stored: Mapping[str, Mapping[str, Any]], again: Mapping[str, Mapping[str, Any]], tolerance: float = 0.0) -> list[dict[str, Any]]:
    """The stored per-item records against re-scored ones (the recomputation): any key present in both whose items, exact flags, greedy sequences, per-window losses or flags differ."""
    out: list[dict[str, Any]] = []
    for k in sorted(set(stored) & set(again)):
        a, b = stored[k], again[k]
        bad = [f for f in ("exact", "sequences", "texts", "flags") if f in a and f in b and a[f] != b[f]]
        if "items" in a and "items" in b and (len(a["items"]) != len(b["items"]) or any(abs(x - y) > tolerance for x, y in zip(a["items"], b["items"], strict=True))):
            bad.append("items")
        if "gen" in a and "gen" in b and any(a["gen"][f] != b["gen"][f] if f in ("strata", "preds") else (len(a["gen"][f]) != len(b["gen"][f]) or any(abs(x - y) > tolerance for x, y in zip(a["gen"][f], b["gen"][f], strict=True))) for f in ("nll_base", "nll_arm", "strata", "preds")):
            bad.append("gen")
        if bad:
            out.append({"key": k, "differs_in": bad, "why": "stored per-item record differs from the recomputation"})
    return out


# --- the A4 readings: edit-distance-1 flags, scores without those items, seen-item and E_open scores ----------------------------------------------------------
def word_distance_one(a: tuple[str, ...], b: tuple[str, ...]) -> bool:
    """Word-level Levenshtein distance exactly 1 (a substitution, an insertion or a deletion of one word)."""
    if a == b:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b, strict=True)) == 1
    if abs(len(a) - len(b)) != 1:
        return False
    s, longer = (a, b) if len(a) < len(b) else (b, a)
    return any(longer[:i] + longer[i + 1 :] == s for i in range(len(longer)))


def edit1_flags(eval_keys: Sequence[str], train_keys: Sequence[str]) -> list[bool]:
    """For each evaluation sentence: does a training sentence lie at word-level edit distance 1 (the share of ADR-0025 section 5.3, per item)."""
    by_len: dict[int, list[tuple[str, ...]]] = {}
    for k in train_keys:
        w = tuple(k.split())
        by_len.setdefault(len(w), []).append(w)
    out = []
    for k in eval_keys:
        w = tuple(k.split())
        out.append(any(word_distance_one(w, t) for ln in (len(w) - 1, len(w), len(w) + 1) for t in by_len.get(ln, ())))
    return out


def a4_lines(registry: Mapping[str, float], items: Mapping[str, Mapping[str, Any]] | None) -> list[str]:
    """The reported readings of sections 5.3 and 8.5 (they enter no label): the edit-distance-1 share of E_A and E_B per replicate, every ``s:E_x`` mean per arm over its cells with and without those items, and the
    seen-item and E_open scores per arm (mean over its cells), M1 and M-append being the arms the ADR names for the seen items."""
    out: list[str] = []
    cells: dict[str, dict[str, list[float]]] = {}
    for k, v in registry.items():
        arm, _o, _r, read = k.split("|", 3)
        if read.startswith(("seen:", "open:")):
            cells.setdefault(f"{arm} {read}", {"v": []})["v"].append(v)
    for name, d in sorted(cells.items()):
        kind = "seen-item score (300 training items of Part Q's seen order)" if " seen:" in name else "E_open score (oracle route, descriptive)"
        out.append(f"{kind}, {name}: {_mean(d['v']):.4f} over {len(d['v'])} cells")
    if items:
        flags = {k: rec["flags"] for k, rec in items.items() if "flags" in rec}
        for k, fl in sorted(flags.items()):
            _a, _o, r, read = k.split("|", 3)
            out.append(f"edit-distance-1 share of {read.removeprefix('edit1:')}, replicate {r}: {sum(fl) / max(1, len(fl)):.4f} ({sum(fl)} of {len(fl)} items have a training source at word-level edit distance 1)")
        by_arm: dict[tuple[str, str], list[tuple[float, float]]] = {}
        for k, rec in items.items():
            if "items" not in rec:
                continue
            arm, _o, r, read = k.split("|", 3)
            if not read.startswith("s:E_") or f"edit1|-|{r}|edit1:{read[2:]}" not in flags:
                continue
            fl = flags[f"edit1|-|{r}|edit1:{read[2:]}"]
            kept = [x for x, f in zip(rec["items"], fl, strict=True) if not f]
            by_arm.setdefault((arm, read), []).append((_mean(rec["items"]), _mean(kept) if kept else float("nan")))
        for (arm, read), pairs in sorted(by_arm.items()):
            out.append(f"{arm} {read} with all items {_mean([a for a, _ in pairs]):.4f}, without the edit-distance-1 items {_mean([b for _, b in pairs]):.4f} (mean over {len(pairs)} cells)")
    return out
