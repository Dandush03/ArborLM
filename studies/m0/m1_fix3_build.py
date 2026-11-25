# ruff: noqa: E501
"""M1 fix round 3: fixtures (structurally de-duplicated across all levels), schema document, cluster map JSON and manifest. No model involved; deterministic.

Run (from the worktree root):
  PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.m1_fix3_build --stage fixtures
  PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.m1_fix3_build --stage clusters
  PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.m1_fix3_build --stage manifest --capacity <cap.json> --digit-capacity <cap_digit.json> --shortcuts <short.json> --before <short_before.json> --exact <exact.json>
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import platform
import sys
from pathlib import Path
from typing import Any

from studies.m0.core import ALL_LEVELS, build_item, stream

ROOT = Path(__file__).resolve().parents[2]
FIX_DIR = ROOT / "studies" / "m0" / "fixtures" / "m1_fix3"
MAN_DIR = ROOT / "studies" / "m0" / "manifests"
SEED = 410303  # throwaway integer for the fixtures; not a registered study seed


def write_fixtures() -> dict[str, str]:
    from studies.m0.lineages_m1_fix3 import load_registered
    from studies.m0.m1_fix3_gates import canon_key

    FIX_DIR.mkdir(parents=True, exist_ok=True)
    out: dict[str, str] = {}
    for lin in load_registered():
        lines: list[str] = []
        seen: set[str] = set()
        for lv in ALL_LEVELS:
            rng = stream(SEED, "fix3-fixture", lin.id, str(lv))
            made, guard = 0, 0
            while made < 20:
                guard += 1
                if guard > 4000:
                    raise RuntimeError(f"{lin.id} L{lv}: cannot find 20 structurally new items")
                it = build_item(lin, lv, rng, "A", f"{lin.id}/fixture/{lv}/{made}")
                ck = canon_key(lin.id, it.structured)
                if ck in seen:
                    continue
                seen.add(ck)
                made += 1
                lines.append(json.dumps({"id": it.id, "lineage": it.lineage, "level": it.level, "question": it.question, "structured": it.structured, "answer": it.answer, "answer_type": it.answer_type, "k": it.k}, sort_keys=True, ensure_ascii=True))
        text = "\n".join(lines) + "\n"
        (FIX_DIR / f"{lin.id}.jsonl").write_text(text)
        out[lin.id] = hashlib.sha256(text.encode()).hexdigest()
    schema = [
        "# M1 fix round 3: structured-form schema for the second-solver agent (registered candidates only)\n",
        "Written by the implementer. Not a result; nothing here approves anything. A second solver reads ONLY `structured` (never the question text, never the key) and returns the answer string exactly as in the fixture; "
        "it raises ValueError when the answer is not unique. Fixtures: `studies/m0/fixtures/m1_fix3/<id>.jsonl`, 20 items per level (0 and 6 reserve), structurally distinct across ALL levels of one file. "
        "NOT REGISTERED lineages have no fixtures (their builders stay on file as attempts). `min_cost_packs` is excluded everywhere.\n",
        "Every answer format and convention is stated in the item text (answer format, units, sign, inclusive or exclusive counts, leading zeros, what a perimeter counts, what a full pallet is).\n",
        "## Lineages\n",
    ]
    for lin in load_registered():
        doc = inspect.getdoc(lin.build) or ""
        it = build_item(lin, 2, stream(SEED, "fix3-schema-example", lin.id), "A", "example")
        schema.append(f"### `{lin.id}` (family {lin.family})\n\n{doc}\n\nExample (level 2):\n\n```\nquestion: {it.question}\nstructured: {json.dumps(it.structured, sort_keys=True)}\nanswer: {it.answer}\n```\n")
    (FIX_DIR / "SCHEMA.md").write_text("\n".join(schema))
    return out


def write_clusters() -> dict[str, Any]:
    from studies.m0.lineages_m1_fix3 import NOT_REGISTERED, load_all, load_registered
    from studies.m0.lineages_m1_fix3_clusters import (
        BORDERLINE,
        CROSS_EVALUATION,
        CROSS_EVALUATION_BORDERLINE,
        GROUPS,
        count_strict,
        cross_evaluation_of,
        strict_clusters,
    )

    reg = [x.id for x in load_registered()]
    allids = [x.id for x in load_all()]
    clusters = strict_clusters(reg)
    n = count_strict(reg)
    rec = {
        "note": "Strict cluster map of the fix-round-3 M1 set (auditor's strict map, rulings R-2 and R-12). Counts are over REGISTERED candidates only; a lineage marked NOT REGISTERED is excluded from the map's count; min_cost_packs is excluded everywhere. "
                "Not human approval; not Astra review.",
        "strict_cluster_count": n,
        "strict_cluster_count_if_borderline_merged": {"gcd_lcm + crt_congruence": n - 1 if "crt_congruence" in clusters and "gcd_lcm" in clusters else n, "clock_duration + S2_weighted_sum": n - 1, "both": n - 2},
        "registered_lineages": len(reg),
        "all_written_lineages": len(allids),
        "not_registered": NOT_REGISTERED,
        "groups": {k: list(v) for k, v in GROUPS.items()},
        "clusters": {k: {"members": v, "cross_evaluation_same_algorithm": cross_evaluation_of(k) or cross_evaluation_of(k.removeprefix("M1.").removesuffix("_r3"))} for k, v in sorted(clusters.items())},
        "cross_evaluation": CROSS_EVALUATION,
        "cross_evaluation_borderline": CROSS_EVALUATION_BORDERLINE,
        "borderline_not_merged": BORDERLINE,
        "excluded_everywhere": ["M1.min_cost_packs_r2", "M1.min_cost_packs"],
    }
    (MAN_DIR / "m1_fix3_cluster_map.json").write_text(json.dumps(rec, indent=1, sort_keys=True))
    return rec


def write_manifest(a: argparse.Namespace) -> dict[str, Any]:
    from studies.m0.lineages_m1_fix3 import NOT_REGISTERED, load_all
    from studies.m0.lineages_m1_fix3_clusters import cluster_of, stem
    from studies.m0.m1_fix3_gates import evaluate

    cap = json.loads(Path(a.capacity).read_text())
    if a.digit_capacity:
        cap["levels"].update(json.loads(Path(a.digit_capacity).read_text())["levels"])
    short = json.loads(Path(a.shortcuts).read_text())
    before = json.loads(Path(a.before).read_text()) if a.before else {"results": {}, "flags": {}}
    exact = json.loads(Path(a.exact).read_text()) if a.exact else {}
    rep = evaluate(cap, NOT_REGISTERED)
    (MAN_DIR / "m1_fix3_capacity.json").write_text(json.dumps({"capacity_sample": cap, "report": rep, "exact_support_analytical": exact}, indent=1, sort_keys=True))
    (MAN_DIR / "m1_fix3_shortcuts.json").write_text(json.dumps({"after": short, "before_same_battery": before}, indent=1, sort_keys=True))
    lins = []
    for lin in load_all():
        lid = lin.id
        st = stem(lid)
        fx = FIX_DIR / f"{lid}.jsonl"
        sf = short["flags"].get(lid, {})
        old_id = {"last_digit_power": "M1.power_remainder_r2"}.get(st)
        lins.append({
            "id": lid, "stem": st, "family": lin.family, "cluster": cluster_of(lid), "carried_over_unchanged": not lid.endswith("_r3"),
            "registered_candidate": lid not in NOT_REGISTERED, "not_registered_reason": NOT_REGISTERED.get(lid),
            "n_eff_per_level": rep["lineages"].get(lid, {}).get("n_eff"),
            "shortcuts_after": {"base_per_level": sf.get("base_per_level"), "max_rule_minus_base_per_level": sf.get("max_rule_minus_base_per_level"), "over_bound_excluding_procedure": sf.get("over_bound_excluding_procedure"),
                                "over_bound_procedure_rules": sf.get("over_bound_procedure_rules"), "over_bound_within_applicable": sf.get("over_bound_within_applicable")},
            "shortcuts_before_same_battery": (before["flags"].get(old_id or lid) or before["flags"].get(lid.removesuffix("_r3") + "_r2") or before["flags"].get(lid.removesuffix("_r3")) or None),
            "fixture_sha256": hashlib.sha256(fx.read_bytes()).hexdigest() if fx.exists() else None,
            "builder_source_sha256": hashlib.sha256(inspect.getsource(lin.build).encode()).hexdigest(),
        })
    man = {
        "batch": "m1_fix3",
        "note": "Fix round 3 after AUDIT3_M1 and LEAD_RULINGS_3. New revisions (ids M1.<stem>_r3) in new files; nothing enters core.REGISTRY; no model was run; no solver other than the implementer's brute-force self-check (m1_fix3_verify.py). "
                "Numbers are MEASURED on generator output unless marked ANALYTICAL (demand, exact support). n_eff is a SAMPLED lower bound. Nothing here is registered, approved or scored.",
        "environment": {"python": sys.version.split()[0], "platform": platform.platform(), "uv_lock_sha256": hashlib.sha256((ROOT / "uv.lock").read_bytes()).hexdigest()},
        "seeds": {"capacity": 410301, "shortcuts": 410302, "fixtures": SEED, "note": "throwaway integers, not registered study seeds"},
        "commands": [
            "PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.m1_fix3_gates --stage capacity --m 30000 --workers 4 --skip digit_puzzle --out <cap.json>",
            "PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.m1_fix3_gates --stage capacity --m 6000 --workers 4 --only digit_puzzle --out <cap_digit.json>",
            "PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.m1_fix3_gates --stage exact --out <exact.json>",
            "PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.m1_fix3_shortcuts --n 2000 --workers 4 --out <short.json>",
            "PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.m1_fix3_shortcuts --n 2000 --workers 3 --before --out <short_before.json> --only <names>",
            "PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.m1_fix3_build --stage fixtures | clusters | manifest ...",
        ],
        "demand": {"derivation": "R-10 and R-11: per cluster and level 10 x (ceil(4000 / G) + ceil(20000 / G) + 100), reserve levels the same; G = smaller part's cluster count", **rep["demand"]},
        "capacity_sample_per_level": cap["m"],
        "cluster_report": rep["clusters"],
        "not_registered": NOT_REGISTERED,
        "excluded_everywhere": ["M1.min_cost_packs_r2", "M1.min_cost_packs"],
        "lineages": lins,
        "working_target_note": "Shortcut target (working, not a registered bound): every rule within +-0.10 of the base rate (the held-out most frequent answer), two-sided, at every level; measured values are reported as they are, including those above the target.",
    }
    (MAN_DIR / "m1_fix3_manifest.json").write_text(json.dumps(man, indent=1, sort_keys=True))
    return man


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--stage", choices=["fixtures", "clusters", "manifest"], required=True)
    ap.add_argument("--capacity", default="")
    ap.add_argument("--digit-capacity", default="")
    ap.add_argument("--shortcuts", default="")
    ap.add_argument("--before", default="")
    ap.add_argument("--exact", default="")
    a = ap.parse_args()
    if a.stage == "fixtures":
        print(json.dumps(write_fixtures(), indent=1, sort_keys=True))
    elif a.stage == "clusters":
        rec = write_clusters()
        print("strict clusters:", rec["strict_cluster_count"], "registered lineages:", rec["registered_lineages"])
    else:
        man = write_manifest(a)
        print("manifest written;", len(man["lineages"]), "lineages")


if __name__ == "__main__":
    main()
