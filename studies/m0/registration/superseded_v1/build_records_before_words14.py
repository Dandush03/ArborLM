#!/usr/bin/env python3
# ruff: noqa: E501  (long prose strings of the records are kept on one line each)
"""Assemble, by code and with no judgement, the records of ADR-0033 addendum 1 section 4A stages 5 and 6.

Writes three files (deterministic: sorted keys, indent 2, trailing newline, no timestamp):

  studies/m0/manifests/status_record_v1.json        (stage 6: first version of the status record)
  studies/m0/manifests/registration_record.json     (stage 5: registration)
  studies/m0/manifests/g_gen_record.json            (stage 6: G-gen's record of record)

Run from the root of the implementation worktree:

    PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 uv run --locked python \
        studies/m0/registration/build_records.py [--root ROOT] [--out OUT]

``--root`` is the worktree that holds the inputs (default: the current directory). ``--out`` is the directory the three files
are written under, mirroring the worktree paths (default: the root). An existing output file is never overwritten with other
content: the script stops. Standard library only. It reads no model output and runs no model.

The script stops (exit 1, nothing written) if an input hash does not equal a hash recorded elsewhere, if the registered
lineages differ from the expected table, or if its own counts differ from the partition record or the capacity record.
"""

from __future__ import annotations

import argparse
import ast
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------------------------------------------------
# Inputs (paths relative to the root of the implementation worktree)
# --------------------------------------------------------------------------------------------------------------------

MANIFESTS = "studies/m0/manifests"
RUN_DIR = "docs/reviews/m0-fresh-run-2026-11-26"
SURVIVORS = f"{MANIFESTS}/survivor_list_of_record.json"
MAP = f"{MANIFESTS}/map_of_record.json"
STAGE2 = f"{MANIFESTS}/stage2_conditions.json"
PARTITION = f"{MANIFESTS}/partition_of_record.json"
CAPACITY = f"{MANIFESTS}/capacity_of_record.json"
CANDIDATES = "studies/m0/registration/candidate_list.json"
DROPPED = f"{RUN_DIR}/run/pooled/dropped.json"
POOLED_SUMS = f"{RUN_DIR}/run/pooled/SHA256SUMS_pooled.txt"
POOLED_TABLE_GZ = f"{RUN_DIR}/run/pooled/pooled_table.json.gz"
HASHES_SEEDS = [f"{RUN_DIR}/run/hashes_seed{i}.json" for i in (1, 2, 3)]
HASH_RECORD = f"{RUN_DIR}/HASH_RECORD.json"
HASH_RECORD_2_4 = f"{RUN_DIR}/HASH_RECORD_STAGES_2_TO_4.json"
RULINGS_8 = f"{RUN_DIR}/LEAD_RULINGS_8.md"
RULINGS_9 = f"{RUN_DIR}/LEAD_RULINGS_9.md"
DOMAIN_LIST = f"{MANIFESTS}/domain_list.json"
WORDS_13 = "docs/reviews/m0-lineage-decision-2026-11-25/HUMAN_LEAD_WORDS_13.md"
ADR_0033 = "docs/decisions/ADR-0033-m0-reference-models-and-evaluation-harness.md"
RECORDS_CHECK = f"{RUN_DIR}/records_check/RECORDS_CHECK.md"
GENERATOR_FILES = f"{RUN_DIR}/records_check/registered_generator_files.json"
WORDS_11 = "docs/reviews/m0-lineage-decision-2026-11-25/HUMAN_LEAD_WORDS_11.md"
DROPS_AFTER_FINAL = (
    "docs/reviews/m0-lineage-decision-2026-11-25/cross_evaluation_map/drops_after_final_checks.txt"
)
FIX4 = {
    "R1": f"{MANIFESTS}/r1_fix4_survivors.json",
    "R2": f"{MANIFESTS}/r2_fix4_survivors.json",
    "M1": f"{MANIFESTS}/m1_fix4_survivors.json",
    "C1": f"{MANIFESTS}/c1_fix4_survivors.json",
}
LINEAGE_MODULE_GLOB = "studies/m0/lineages_*.py"

OUT_STATUS = f"{MANIFESTS}/status_record_v1.json"
OUT_REGISTRATION = f"{MANIFESTS}/registration_record.json"
OUT_GGEN = f"{MANIFESTS}/g_gen_record.json"

EVALS = ["R1", "R2", "M1", "C1"]
PARTS = ["A", "B"]

# The expected registration table (the brief's): evaluation -> part -> (clusters, lineages).
EXPECTED = {
    "R1": {"A": (4, 5), "B": (1, 1)},
    "R2": {"A": (8, 9), "B": (6, 6)},
    "M1": {"A": (8, 15), "B": (6, 8)},
    "C1": {"A": (13, 17), "B": (4, 4)},
}
EXPECTED_REGISTERED_TOTAL = 65

# The seven drops that come from the rule's wording (HUMAN_LEAD_WORDS_11.md): the note added, no status changed.
WORDING_SEVEN = [
    "R1.spatial_grid_walk_r5",
    "R1.swap_tracking_r5",
    "C1.circle_elimination_r2",
    "C1.cond_chain_f3",
    "C1.shared_lists_f3",
    "C1.union_find_links_f3",
    "R2.list_ops",
]
WORDING_NOTE = (
    "the drop comes from the rule's wording and not from an exploitable shortcut, as the recomputation establishes it "
    "(HUMAN_LEAD_WORDS_11.md, the lead's reading of the human lead's words 'Let them stand'); that note changes no status"
)

NO_REASON = "not on the survivor list of record; superseded or dropped before it (no single committed reason found)"

GGEN_STATUS = (
    "G-GEN'S RECORD OF RECORD (ADR-0033 addendum 1, section 4A stage 6), made at the human lead's domain list of "
    "2026-11-26. It freezes the generators at commit 7cd0ac5a. No model has been run on any M0 item."
)

# Names of top-level literal tables in the lineage modules, read with ``ast`` (nothing is imported or executed).
PRIMARY_TABLE_WORD = "NOT_REGISTERED"
SUPPLEMENTARY_TABLES = {
    "SUPERSEDED",
    "DROPPED_AUDIT4",
    "AUDIT4_DROPS",
    "SECOND_STAGE_DROPS",
    "DROPPED_AFTER_REMEASURE",
}


class Stop(Exception):
    """An inconsistency between inputs; nothing is written."""


# --------------------------------------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------------------------------------


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


class Inputs:
    """Reads files under the root once and remembers the SHA-256 of every file it reads."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.override: dict[str, Path] = {}
        self.hashes: dict[str, str] = {}
        self._text: dict[str, bytes] = {}

    def raw(self, rel: str) -> bytes:
        if rel not in self._text:
            p = self.override.get(rel, self.root / rel)
            if not p.is_file():
                raise Stop(f"missing input: {rel}")
            data = p.read_bytes()
            self._text[rel] = data
            self.hashes[rel] = sha_bytes(data)
        return self._text[rel]

    def sha(self, rel: str) -> str:
        self.raw(rel)
        return self.hashes[rel]

    def json(self, rel: str) -> Any:
        return json.loads(self.raw(rel).decode("utf-8"))

    def text(self, rel: str) -> str:
        return self.raw(rel).decode("utf-8")

    def exists(self, rel: str) -> bool:
        return self.override.get(rel, self.root / rel).is_file()


def dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def check(cond: bool, message: str) -> None:
    if not cond:
        raise Stop(message)


def ref(inp: Inputs, rel: str) -> dict[str, str]:
    return {"path": rel, "sha256": inp.sha(rel)}


# --------------------------------------------------------------------------------------------------------------------
# reasons for lineages that are not on the survivor list
# --------------------------------------------------------------------------------------------------------------------


def literal_tables(
    inp: Inputs,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], list[str]]:
    """Top-level literal dicts of the lineage modules: (primary NOT_REGISTERED tables, supplementary tables, files read)."""
    primary: dict[str, dict[str, Any]] = {}
    supplementary: dict[str, dict[str, Any]] = {}
    files = sorted(p.relative_to(inp.root).as_posix() for p in inp.root.glob(LINEAGE_MODULE_GLOB))
    for rel in files:
        tree = ast.parse(inp.text(rel))
        for node in tree.body:
            if isinstance(node, ast.Assign):
                names = [t.id for t in node.targets if isinstance(t, ast.Name)]
                value = node.value
            elif (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.value is not None
            ):
                names = [node.target.id]
                value = node.value
            else:
                continue
            for name in names:
                is_primary = PRIMARY_TABLE_WORD in name and "CLUSTERS" not in name
                if not (is_primary or name in SUPPLEMENTARY_TABLES):
                    continue
                try:
                    table = ast.literal_eval(value)
                except (ValueError, SyntaxError):
                    continue
                if isinstance(table, dict):
                    (primary if is_primary else supplementary)[f"{rel}:{name}"] = table
    return primary, supplementary, files


def collect_reasons(inp: Inputs, lineages: set[str]) -> dict[str, Any]:
    """Every committed statement about a lineage that is not on the survivor list, by source, in the order of priority."""
    drops_text = inp.text(DROPS_AFTER_FINAL)
    drop_ids = [
        ln.strip() for ln in drops_text.splitlines() if ln.strip() and not ln.startswith("#")
    ]
    drop_header = next(
        (ln.lstrip("# ").strip() for ln in drops_text.splitlines() if ln.startswith("#")), ""
    )

    manifest_nr: dict[str, list[dict[str, Any]]] = {}
    excluded_nr: dict[str, list[dict[str, Any]]] = {}
    superseded: dict[str, list[dict[str, Any]]] = {}

    def add(store: dict[str, list[dict[str, Any]]], lin: str, entry: dict[str, Any]) -> None:
        store.setdefault(lin, []).append(entry)

    # R1: shapes, each with its status, reason and earlier id.
    r1 = inp.json(FIX4["R1"])
    for s in r1["shapes"]:
        if s["status"] == "NOT_REGISTERED":
            add(
                manifest_nr,
                s["name"],
                {
                    "source": FIX4["R1"] + ":shapes",
                    "text": s["reason"],
                    "manifest_fields": {"largest": s.get("largest"), "stage": s.get("stage")},
                },
            )
        if s.get("earlier_id"):
            add(
                superseded,
                s["earlier_id"],
                {"source": FIX4["R1"] + ":shapes.earlier_id", "text": f"superseded by {s['name']}"},
            )
    # R2: lineages, with the status before capacity.
    r2 = inp.json(FIX4["R2"])
    for x in r2["lineages"].values():
        if x["status_before_capacity"] == "NOT_REGISTERED":
            add(
                manifest_nr,
                x["id"],
                {
                    "source": FIX4["R2"] + ":lineages.status_before_capacity",
                    "text": x["reason"],
                    "manifest_fields": {
                        "max_abs_excess": x.get("max_abs_excess"),
                        "max_rule": x.get("max_rule"),
                    },
                },
            )
    # M1: candidates and the exclusions.
    m1 = inp.json(FIX4["M1"])
    for name, x in m1["candidates"].items():
        if x["status"] == "NOT_REGISTERED":
            add(
                manifest_nr,
                name,
                {"source": FIX4["M1"] + ":candidates", "text": x["reason"], "manifest_fields": {}},
            )
        if x.get("replaces"):
            for old in x["replaces"] if isinstance(x["replaces"], list) else [x["replaces"]]:
                add(
                    superseded,
                    old,
                    {
                        "source": FIX4["M1"] + ":candidates.replaces",
                        "text": f"superseded by {name}",
                    },
                )
    for name in m1["excluded_everywhere"]:
        add(
            excluded_nr,
            name,
            {
                "source": FIX4["M1"] + ":excluded_everywhere",
                "text": "listed under excluded_everywhere (no reason text in the file)",
                "manifest_fields": {},
            },
        )
    # C1: lineages, with the supersession table.
    c1 = inp.json(FIX4["C1"])
    for x in c1["lineages"]:
        if x["status"] == "NOT_REGISTERED":
            add(
                manifest_nr,
                x["name"],
                {
                    "source": FIX4["C1"] + ":lineages",
                    "text": x["reason"],
                    "manifest_fields": {"level_wide_max": x.get("level_wide_max")},
                },
            )
        sup = x.get("supersedes")
        if sup:
            for old in sup if isinstance(sup, list) else [sup]:
                add(
                    superseded,
                    old,
                    {
                        "source": FIX4["C1"] + ":lineages.supersedes",
                        "text": f"superseded by {x['name']}",
                    },
                )
    for old, new in c1["superseded"].items():
        add(superseded, old, {"source": FIX4["C1"] + ":superseded", "text": f"superseded by {new}"})

    primary, supplementary, module_files = literal_tables(inp)
    module_nr: dict[str, list[dict[str, Any]]] = {}
    unmatched_module_keys: list[str] = []
    for table_name, table in sorted(primary.items()):
        for key, val in sorted(table.items()):
            if key in lineages:
                add(module_nr, key, {"source": table_name, "text": str(val), "manifest_fields": {}})
            else:
                unmatched_module_keys.append(f"{table_name}:{key}")
    supplementary_reasons: dict[str, list[dict[str, Any]]] = {}
    for table_name, table in sorted(supplementary.items()):
        for key, val in sorted(table.items()):
            if key not in lineages:
                continue
            if table_name.endswith(":SUPERSEDED"):
                add(superseded, key, {"source": table_name, "text": f"superseded by {val}"})
            else:
                add(
                    supplementary_reasons,
                    key,
                    {"source": table_name, "text": str(val), "manifest_fields": {}},
                )

    return {
        "drop_ids": drop_ids,
        "drop_header": drop_header,
        "manifest_nr": manifest_nr,
        "excluded_nr": excluded_nr,
        "module_nr": module_nr,
        "superseded": superseded,
        "supplementary": supplementary_reasons,
        "unmatched_module_keys": unmatched_module_keys,
        "module_files": module_files,
    }


def before_survivor_reason(lin: str, rs: dict[str, Any]) -> dict[str, Any]:
    """The reason of a lineage dropped before the survivor list, by the order of priority; only committed statements."""
    statements: list[dict[str, Any]] = []
    tier = "none"
    if lin in rs["drop_ids"]:
        statements.append(
            {
                "source": DROPS_AFTER_FINAL,
                "text": f"listed in drops_after_final_checks.txt; its header reads: {rs['drop_header']!r}; the file states no figure",
                "manifest_fields": {},
            }
        )
        tier = "final_checks"
    for key, stage_detail in (
        ("manifest_nr", "fix_round_4_manifest"),
        ("module_nr", "lineage_module_table"),
        ("excluded_nr", "fix_round_4_manifest"),
    ):
        for st in rs[key].get(lin, []):
            statements.append(st)
            if tier == "none":
                tier = stage_detail
    if tier == "none":
        for st in rs["supplementary"].get(lin, []):
            statements.append(st)
            if tier == "none":
                tier = "supplementary_table"
        for st in rs["superseded"].get(lin, []):
            statements.append(st)
            if tier == "none":
                tier = "superseded"
    if not statements:
        return {
            "stage_detail": "no_single_committed_reason_found",
            "reason": NO_REASON,
            "statements": [],
        }
    first = statements[0]
    return {
        "stage_detail": tier,
        "reason": f"{first['text']} [{first['source']}]",
        "statements": statements,
    }


# --------------------------------------------------------------------------------------------------------------------
# the build
# --------------------------------------------------------------------------------------------------------------------


def adr_section_68_rows(inp: Inputs) -> tuple[list[dict[str, str]], str]:
    """The table of ADR-0033 section 6.8, read from the file, and the sentence on code writing."""
    lines = inp.text(ADR_0033).splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("### 6.8"))
    rows: list[dict[str, str]] = []
    sentence = ""
    for ln in lines[start + 1 :]:
        if ln.startswith("## ") or ln.startswith("### "):
            break
        if ln.startswith("|"):
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if cells[0] in ("Domain",) or set(cells[0]) <= {"-"}:
                continue
            rows.append(
                {"domain": cells[0], "gate_candidates": cells[1], "printed_beside": cells[2]}
            )
        elif ln.startswith("Code writing is NOT MEASURED"):
            sentence = ln.split(".")[0] + "."
    return rows, sentence


def domain_list_block(inp: Inputs) -> dict[str, Any]:
    """The domain list from the committed input file, checked against section 6.8 and the recorded decision."""
    dl = inp.json(DOMAIN_LIST)
    check(dl["record"]["path"] == WORDS_13, "domain_list.json names another decision record")
    check(
        dl["record"]["sha256"] == inp.sha(WORDS_13),
        "domain_list.json: the recorded hash of HUMAN_LEAD_WORDS_13.md differs from the file",
    )
    check(
        dl["specification"]["path"] == ADR_0033
        and dl["specification"]["sha256"] == inp.sha(ADR_0033),
        "domain_list.json: the recorded hash of ADR-0033 differs from the file",
    )
    rows, sentence = adr_section_68_rows(inp)
    check(len(rows) == 5, f"ADR-0033 section 6.8 has {len(rows)} rows, not 5")
    got = [
        {
            "domain": d["domain"],
            "gate_candidates": d["gate_candidates_as_written"],
            "printed_beside": d["printed_beside"],
        }
        for d in dl["domains"]
    ]
    check(got == rows, "domain_list.json differs from the table of ADR-0033 section 6.8")
    check(
        dl["code_writing"] == "NOT MEASURED"
        and sentence.startswith("Code writing is NOT MEASURED"),
        "code writing is not NOT MEASURED",
    )
    return {
        **dl,
        "file": ref(inp, DOMAIN_LIST),
        "checked_against_section_6_8_of_the_file_at": ref(inp, ADR_0033),
    }


def families_of(capacity: dict[str, Any], e: str, p: str) -> list[str]:
    return list(capacity["parts"][e][p]["families"])


def build(inp: Inputs, script_sha: str) -> dict[str, str]:
    survivors = inp.json(SURVIVORS)
    mp = inp.json(MAP)
    stage2 = inp.json(STAGE2)
    partition = inp.json(PARTITION)
    capacity = inp.json(CAPACITY)
    cand = inp.json(CANDIDATES)
    dropped = inp.json(DROPPED)
    hash_record = inp.json(HASH_RECORD)
    hash_record_2_4 = inp.json(HASH_RECORD_2_4)

    # ---- hash cross-checks: what the records say against the files -------------------------------------------------
    pairs: list[tuple[str, str, str]] = [
        ("survivor list", SURVIVORS, hash_record["i_survivor_list"]["sha256"]),
        ("map", MAP, hash_record["map_of_record"]["sha256"]),
        ("map (stages 2 to 4 record)", MAP, hash_record_2_4["map_of_record"]["sha256"]),
        ("stage-2 conditions", STAGE2, hash_record["stage2_conditions"]["sha256"]),
        ("candidate list", CANDIDATES, hash_record_2_4["candidate_list"]["sha256"]),
        ("partition", PARTITION, hash_record_2_4["partition_of_record"]["sha256"]),
        ("candidates (capacity record)", CANDIDATES, capacity["inputs"]["sha256"]["candidates"]),
        ("map (capacity record)", MAP, capacity["inputs"]["sha256"]["map"]),
        ("partition (capacity record)", PARTITION, capacity["inputs"]["sha256"]["partition"]),
        ("map (partition record)", MAP, partition["inputs"]["map_sha256"]),
        ("candidates (partition record)", CANDIDATES, partition["inputs"]["candidates_sha256"]),
        (
            "survivor list (candidate record)",
            SURVIVORS,
            cand["input_sha256"]["survivor_list_of_record"],
        ),
        (
            "stage-2 conditions (candidate record)",
            STAGE2,
            cand["input_sha256"]["stage2_conditions"],
        ),
        ("dropped.json (candidate record)", DROPPED, cand["input_sha256"]["dropped"]),
    ]
    for label, rel, expected in pairs:
        check(
            inp.sha(rel) == expected,
            f"hash mismatch: {label}: file {inp.sha(rel)} against record {expected}",
        )

    # Every file named with a path and a hash in the two hash records is hashed again where the file is in this worktree.
    recorded_files: list[tuple[str, str]] = []
    for _key, val in sorted(hash_record.items()):
        if isinstance(val, dict) and "path" in val and "sha256" in val:
            recorded_files.append((val["path"], val["sha256"]))
    for path, sha in sorted(hash_record["iii_run_copies"].items()):
        recorded_files.append((path, sha))
    for path, sha in sorted(hash_record["second_solvers"].items()):
        recorded_files.append((path, sha))
    for _key, val in sorted(hash_record_2_4.items()):
        if isinstance(val, dict) and "path" in val and "sha256" in val:
            recorded_files.append((val["path"], val["sha256"]))
    for path, sha in sorted(hash_record_2_4["second_solvers"].items()):
        recorded_files.append((path, sha))
    verified: dict[str, str] = {}
    not_in_worktree: list[str] = []
    for path, sha in recorded_files:
        if " (" in path or not inp.exists(path):
            not_in_worktree.append(path)
            continue
        check(
            inp.sha(path) == sha,
            f"hash mismatch against a hash record: {path}: file {inp.sha(path)} against record {sha}",
        )
        verified[path] = sha

    # ---- the map ---------------------------------------------------------------------------------------------------
    lineages = sorted(mp["lineages"])
    check(len(lineages) == 345, f"the map has {len(lineages)} written lineages, not 345")
    eval_of = {x: mp["lineages"][x]["evaluation"] for x in lineages}
    cluster_of: dict[str, str] = {}
    for c in mp["clusters"]:
        for member in c["members"]:
            check(member not in cluster_of, f"lineage in two clusters: {member}")
            cluster_of[member] = c["cluster_id"]
    check(
        set(cluster_of) == set(lineages),
        "the clusters of the map do not cover exactly its lineages",
    )
    group_of_cluster: dict[str, int] = {}
    for gi, g in enumerate(mp["groups"]):
        for c in g:
            group_of_cluster[c] = gi
    check(
        set(group_of_cluster) == {c["cluster_id"] for c in mp["clusters"]},
        "the groups of the map do not cover its clusters",
    )

    surv_ids = {x for e in EVALS for x in survivors["evaluations"][e]}
    check(len(surv_ids) == 82, f"the survivor list holds {len(surv_ids)} lineages, not 82")
    check(surv_ids <= set(lineages), "a survivor is not a written lineage of the map")
    candidates = {e: sorted(cand["candidates"][e]) for e in EVALS}
    cand_ids = {x for e in EVALS for x in candidates[e]}
    dropped_by_run = sorted(cand["dropped_by_fresh_run"])
    check(
        cand_ids == surv_ids - set(dropped_by_run),
        "candidates differ from survivors less the fresh run's drops",
    )
    check(
        len(dropped) == 15 and sorted(d["lineage"] for d in dropped) == dropped_by_run,
        "dropped.json differs from the candidate record's drops",
    )

    # ---- parts and groups from the partition record ----------------------------------------------------------------
    cluster_part: dict[str, str] = partition["cluster_part"]
    no_cand: dict[str, Any] = partition["clusters_without_candidate"]
    check(
        set(cluster_part) | set(no_cand) == {c["cluster_id"] for c in mp["clusters"]},
        "partition and map disagree on the clusters",
    )
    check(
        not (set(cluster_part) & set(no_cand)), "a cluster both with a part and without a candidate"
    )
    check(
        set(cluster_part) == {cluster_of[x] for x in cand_ids},
        "clusters with a part differ from clusters with a candidate",
    )

    def part_of_lineage(lin: str) -> str:
        return str(cluster_part.get(cluster_of[lin], "none"))

    # ---- capacity record: removed and registered -------------------------------------------------------------------
    removed: dict[str, dict[str, Any]] = {}
    for e in EVALS:
        for p in PARTS:
            for r in capacity["parts"][e][p]["removed"]:
                removed[r["lineage"]] = {"evaluation": e, "part": p, **r}
    registered_by: dict[str, dict[str, dict[str, list[str]]]] = {
        e: {p: {} for p in PARTS} for e in EVALS
    }
    for lin in sorted(cand_ids - set(removed)):
        e = eval_of[lin]
        p = part_of_lineage(lin)
        check(p in PARTS, f"candidate without a part: {lin}")
        registered_by[e][p].setdefault(cluster_of[lin], []).append(lin)
    registered = sorted(
        x for e in EVALS for p in PARTS for lst in registered_by[e][p].values() for x in lst
    )
    check(
        len(registered) == EXPECTED_REGISTERED_TOTAL,
        f"{len(registered)} registered lineages, not {EXPECTED_REGISTERED_TOTAL}",
    )
    for e in EVALS:
        for p in PARTS:
            got = (len(registered_by[e][p]), sum(len(v) for v in registered_by[e][p].values()))
            check(
                got == EXPECTED[e][p],
                f"{e} part {p}: clusters/lineages {got}, expected {EXPECTED[e][p]}",
            )
            cap = capacity["parts"][e][p]
            check(
                got == (cap["G_registered"], cap["lineages_registered"]),
                f"{e} part {p}: differs from the capacity record",
            )
            cap_reg = {k: sorted(v) for k, v in cap["registered"].items()}
            check(
                cap_reg == {k: sorted(v) for k, v in registered_by[e][p].items()},
                f"{e} part {p}: registered lineages differ from the capacity record",
            )
    for lin, info in removed.items():
        check(lin in cand_ids, f"a capacity drop that is not a candidate: {lin}")
        check(
            info["evaluation"] == eval_of[lin] and info["part"] == part_of_lineage(lin),
            f"capacity drop in the wrong part: {lin}",
        )

    # ---- reasons before the survivor list --------------------------------------------------------------------------
    rs = collect_reasons(inp, set(lineages))
    wording_text = inp.text(WORDS_11)
    dropped_by_id = {d["lineage"]: d for d in dropped}
    for lin in WORDING_SEVEN:
        check(lin in dropped_by_id, f"wording drop not in dropped.json: {lin}")
        check(
            lin.split(".", 1)[1].rsplit("_", 1)[0] in wording_text
            or lin.split(".", 1)[1] in wording_text,
            f"wording drop not named in HUMAN_LEAD_WORDS_11.md: {lin}",
        )
    check(
        len(rs["drop_ids"]) == 5 and len(set(rs["drop_ids"])) == 5,
        "drops_after_final_checks.txt does not list five ids",
    )
    check(
        set(rs["drop_ids"]) <= surv_ids | set(lineages),
        "a final-checks drop is not a written lineage",
    )

    # ---- the status record -----------------------------------------------------------------------------------------
    REGISTRATION_RECORDS = {
        "survivor_list_of_record": {
            **ref(inp, SURVIVORS),
            "role": "the lineage is on it (stage 0)",
        },
        "stage2_conditions": {**ref(inp, STAGE2), "role": "every stage-2 condition PASS (stage 2)"},
        "fresh_run_not_dropped": {
            **ref(inp, DROPPED),
            "role": "the 15 lineages the fresh run dropped; the lineage is not among them (stage 1S)",
        },
        "candidate_list": {**ref(inp, CANDIDATES), "role": "the lineage is a candidate (stage 2)"},
        "partition_of_record": {**ref(inp, PARTITION), "role": "its cluster's part (stage 3)"},
        "capacity_record": {
            **ref(inp, CAPACITY),
            "role": "the lineage is in S at the fixed point of stage 4 and its cluster holds a registered lineage",
        },
    }
    status: dict[str, dict[str, Any]] = {}
    counts: dict[str, dict[str, int]] = {e: {"REGISTERED": 0, "NOT REGISTERED": 0} for e in EVALS}
    not_registered_by_stage: dict[str, dict[str, int]] = {e: {} for e in EVALS}
    no_reason: list[str] = []
    for lin in lineages:
        e = eval_of[lin]
        cl = cluster_of[lin]
        part = part_of_lineage(lin)
        entry: dict[str, Any] = {
            "evaluation": e,
            "global_cluster": cl,
            "cluster_part": part,
            "on_survivor_list": lin in surv_ids,
            "candidate": lin in cand_ids,
        }
        if part == "none":
            nc = no_cand[cl]
            entry["group_part_beside_it"] = nc["group_part"]
            entry["group"] = nc["group"]
            entry["tied_by_borderline_pair"] = nc["tied_by_borderline_pair"]
        else:
            entry["group"] = partition["cluster_groups"][cl]
            entry["part_binds_it"] = True
        stage_key = None
        if lin in registered:
            entry["status"] = "REGISTERED"
            entry["stage"] = "stage 5, registration"
            entry["established_by"] = list(REGISTRATION_RECORDS)
        else:
            entry["status"] = "NOT REGISTERED"
            if lin in removed:
                info = removed[lin]
                entry["stage"] = "stage 4, capacity"
                levels_text = ", ".join(
                    f"level {lv} (count {v['count']} of demand {v['demand']}, ended on {v['ended']})"
                    for r in info["reasons"]
                    if r["kind"] == "own_demand"
                    for lv, v in sorted(r["levels"].items())
                )
                entry["reason"] = (
                    f"capacity, round {info['round']}, part {info['part']}, G {info['G']}, k {info['k']}: "
                    f"its own demand not met at {levels_text}"
                )
                entry["reason_detail"] = info
                entry["source_record"] = ref(inp, CAPACITY)
                stage_key = "stage 4, capacity"
            elif lin in dropped_by_id:
                d = dropped_by_id[lin]
                rd = d["reason"]
                entry["stage"] = "stage 1S, fresh run"
                entry["reason"] = (
                    f"fresh run: rule {rd['rule']!r} of unit {rd['unit']} at level {rd['level']}: pooled excess "
                    f"{rd['excess']['decimal_12dp']} ({rd['excess']['fraction']}); its absolute value plus the "
                    f"rounding uncertainty is {rd['abs_excess_plus_uncertainty']['decimal_12dp']}, above the bound "
                    f"{rd['bound']} (two-sided)"
                )
                entry["reason_detail"] = {
                    "unit": rd["unit"],
                    "rule": rd["rule"],
                    "level": rd["level"],
                    "shape": rd["shape"],
                    "source": rd["source"],
                    "reading": rd["reading"],
                    "bound": rd["bound"],
                    "excess": rd["excess"],
                    "pooled_figure": rd["pooled_figure"],
                    "rounding_uncertainty": rd["rounding_uncertainty"],
                    "abs_excess_plus_uncertainty": rd["abs_excess_plus_uncertainty"],
                    "n_rows_over_the_bound": len(d["all_rows_over_the_bound"]),
                    "source_file": DROPPED,
                }
                entry["source_record"] = ref(inp, DROPPED)
                if lin in WORDING_SEVEN:
                    entry["note"] = WORDING_NOTE
                    entry["note_source"] = WORDS_11
                stage_key = "stage 1S, fresh run"
            else:
                check(
                    lin not in surv_ids, f"a survivor that is neither registered nor dropped: {lin}"
                )
                r = before_survivor_reason(lin, rs)
                entry["stage"] = "before the survivor list"
                entry["stage_detail"] = r["stage_detail"]
                entry["reason"] = r["reason"]
                entry["reason_statements"] = r["statements"]
                stage_key = f"before the survivor list: {r['stage_detail']}"
                if r["stage_detail"] == "no_single_committed_reason_found":
                    no_reason.append(lin)
        counts[e][entry["status"]] += 1
        if stage_key:
            not_registered_by_stage[e][stage_key] = not_registered_by_stage[e].get(stage_key, 0) + 1
        status[lin] = entry

    total_counts = {s: sum(counts[e][s] for e in EVALS) for s in ("REGISTERED", "NOT REGISTERED")}
    check(
        total_counts == {"REGISTERED": 65, "NOT REGISTERED": 280},
        f"status counts differ from 65 and 280: {total_counts}",
    )
    no_reason_by_eval = {e: sum(1 for x in no_reason if eval_of[x] == e) for e in EVALS}
    only_supplementary = sorted(
        x
        for x in lineages
        if status[x].get("stage_detail") in ("superseded", "supplementary_table")
    )

    inputs_status = {
        k: inp.sha(k)
        for k in [
            SURVIVORS,
            MAP,
            PARTITION,
            CAPACITY,
            CANDIDATES,
            DROPPED,
            WORDS_11,
            DROPS_AFTER_FINAL,
            *FIX4.values(),
            *rs["module_files"],
        ]
    }
    status_record = {
        "what": (
            "First version of the status record of ADR-0033 addendum 1 section 3 item 6 and section 4A stage 6: for each of the 345 "
            "written lineages of the map of record, the evaluation, the global cluster, the cluster's part and the status with its stage "
            "and reason. Assembled by code from committed records; no judgement. The map carries no status and is not changed by this file."
        ),
        "version": 1,
        "completion_note": (
            "This is the first version of the status record as completed after the independent records check "
            "(RECORDS_CHECK.md, finding 1): each REGISTERED lineage names the stage that set its status and the records that "
            "establish it, and each capacity or fresh-run drop names its source record. No count and no status differs from the "
            "version before the check; nothing had used that version."
        ),
        "records_check": {
            **ref(inp, RECORDS_CHECK),
            "what": "independent engineering evidence, not Astra validation and not human approval",
        },
        "records_establishing_registration": REGISTRATION_RECORDS,
        "status": "First version of the status record, part of G-gen's record of record made at the human lead's domain list of 2026-11-26",
        "counts": {
            "per_evaluation_and_status": counts,
            "total_by_status": total_counts,
            "written_lineages": len(lineages),
            "not_registered_by_stage_per_evaluation": not_registered_by_stage,
            "reason_tiers_of_the_263_not_registered_before_the_survivor_list": {
                "named_sources": sum(
                    1
                    for x in lineages
                    if status[x].get("stage_detail")
                    in ("final_checks", "fix_round_4_manifest", "lineage_module_table")
                ),
                "supersession_only": len(only_supplementary),
                "no_single_committed_reason_found": len(no_reason),
                "meaning": (
                    "named_sources: drops_after_final_checks.txt, the fix-4 manifests, the NOT_REGISTERED tables of the lineage "
                    "modules; supersession_only: 'superseded by X' from committed supersession fields; no_single_committed_reason_found: "
                    "the fixed sentence"
                ),
            },
            "not_registered_with_no_single_committed_reason": {
                "total": len(no_reason),
                "per_evaluation": no_reason_by_eval,
                "lineages": no_reason,
            },
            "not_registered_whose_only_committed_statement_is_a_supplementary_one": {
                "meaning": (
                    "a statement 'superseded by ...' (or a supplementary table entry) and none from the sources the brief names; "
                    "with these counted as no reason, the number without a reason is the sum of this total and the one above"
                ),
                "total": len(only_supplementary),
                "per_evaluation": {
                    e: sum(1 for x in only_supplementary if eval_of[x] == e) for e in EVALS
                },
                "lineages": only_supplementary,
            },
        },
        "reason_policy": (
            "A reason is taken only where a committed file states it. Order: drops_after_final_checks.txt; the fix-4 manifests; the "
            "NOT_REGISTERED tables of the lineage modules (read with ast, nothing executed); then, only if none of those states one, the "
            "supplementary committed tables (SUPERSEDED, DROPPED_AUDIT4 and the like, and the supersession fields of the fix-4 manifests). "
            "Where no committed file states a reason the reason is the fixed sentence given in the field."
        ),
        "lineages": status,
        "inputs_sha256": inputs_status,
        "lineage_module_keys_not_matching_a_written_lineage": rs["unmatched_module_keys"],
        "script_sha256": script_sha,
        "map_sha256": inp.sha(MAP),
    }
    status_text = dumps(status_record)
    status_sha = sha_bytes(status_text.encode("utf-8"))

    # ---- the registration record -----------------------------------------------------------------------------------
    def groups_with_cluster_set(clusters: set[str]) -> set[int]:
        return {group_of_cluster[c] for c in clusters}

    # Alternative reading of "strictest": clusters linked only by a borderline pair whose two lineages sit in two clusters that
    # are both in the set under consideration.
    bp_cluster_pairs = {
        tuple(sorted((cluster_of[a], cluster_of[b])))
        for a, b in mp["borderline_pairs"]
        if cluster_of[a] != cluster_of[b]
    }

    def direct_components(clusters: set[str]) -> int:
        parent = {c: c for c in clusters}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for a, b in sorted(bp_cluster_pairs):
            if a in clusters and b in clusters:
                parent[find(a)] = find(b)
        return len({find(c) for c in clusters})

    reg_eval: dict[str, Any] = {}
    g_per_part: dict[str, Any] = {}
    n_e: dict[str, int] = {}
    part_counts: dict[str, Any] = {}
    departures_family: list[dict[str, Any]] = []
    section9: dict[str, Any] = {}
    for e in EVALS:
        cand_clusters = {cluster_of[x] for x in candidates[e]}
        n_e[e] = len(cand_clusters)
        pc = partition["counts"][e]
        recomputed_counts = {
            "N_e": len(cand_clusters),
            "clusters_A": sum(1 for c in cand_clusters if cluster_part[c] == "A"),
            "clusters_B": sum(1 for c in cand_clusters if cluster_part[c] == "B"),
            "groups_A": len(
                groups_with_cluster_set({c for c in cand_clusters if cluster_part[c] == "A"})
            ),
            "groups_B": len(
                groups_with_cluster_set({c for c in cand_clusters if cluster_part[c] == "B"})
            ),
        }
        for k, v in recomputed_counts.items():
            check(
                pc[k] == v,
                f"{e}: {k} is {v} by the map and candidates, {pc[k]} in the partition record",
            )
        part_counts[e] = {
            "candidate_clusters_and_groups_as_the_partition_record_carries_them": {
                "N_e": pc["N_e"],
                "clusters_A": pc["clusters_A"],
                "clusters_B": pc["clusters_B"],
                "groups_A": pc["groups_A"],
                "groups_B": pc["groups_B"],
                "half_floor": pc["half_floor"],
                "recomputed_from_map_and_candidates_equal": True,
            },
            "registered_clusters_and_groups": {},
        }
        parts_out: dict[str, Any] = {}
        fam_union: set[str] = set()
        for p in PARTS:
            reg_clusters = set(registered_by[e][p])
            cap = capacity["parts"][e][p]
            start_clusters = {c for c in cand_clusters if cluster_part[c] == p}
            lost = sorted(start_clusters - reg_clusters)
            g_n = len(reg_clusters)
            fams = families_of(capacity, e, p)
            fam_union |= set(fams)
            groups_reg = groups_with_cluster_set(reg_clusters)
            direct = direct_components(reg_clusters) if reg_clusters else 0
            if g_n == 0:
                reading = "NO CLUSTER: no pool; every outcome of this part reads NOT EVALUABLE with the reason NO CLUSTER (section 9 item 5)"
            elif g_n == 1:
                reading = (
                    "ONE CLUSTER: accuracies only; every outcome that needs an interval reads NOT EVALUABLE with the reason "
                    "ONE CLUSTER (section 9 item 5)"
                )
            else:
                reading = f"computed as written, with {g_n - 1} degrees of freedom printed beside every figure (section 9 item 5)"
            parts_out[p] = {
                "registered_by_cluster": {
                    k: sorted(v) for k, v in sorted(registered_by[e][p].items())
                },
                "G": g_n,
                "G_start_of_stage_4": cap["G_start"],
                "lineages_registered": sum(len(v) for v in registered_by[e][p].values()),
                "lineages_start_of_stage_4": cap["lineages_start"],
                "clusters_that_had_a_candidate_and_lost_every_lineage_at_capacity_and_keep_their_part": lost,
                "families_among_registered_lineages": fams,
                "n_families": len(fams),
                "n_families_as_the_capacity_record_carries_it": cap["n_families"],
                "families_fewer_than_12": len(fams) < 12,
                "section_9_item_5_reading": reading,
                "strictest_G": {
                    "reading_used": (
                        "lead ruling R-65: section 1 item 3 'the count they would give if merged': every borderline pair of the map of "
                        "record merged, transitively, whatever the status of the lineages it passes through; the number of groups that "
                        "hold a cluster with a registered lineage of this evaluation in this part"
                    ),
                    "value": len(groups_reg),
                    "direct_pairs_count_information_only_not_the_strictest_count": {
                        "reading_used": (
                            "components among the clusters with a registered lineage of this evaluation in this part, linked only by a "
                            "borderline pair whose two ends are both such clusters (no chain through a cluster not registered here)"
                        ),
                        "value": direct,
                    },
                },
            }
            check(
                len(fams) == cap["n_families"],
                f"{e} {p}: family count differs from the capacity record",
            )
            if len(fams) < 12:
                departures_family.append(
                    {"evaluation": e, "part": p, "n_families": len(fams), "families": fams}
                )
            part_counts[e]["registered_clusters_and_groups"][p] = {
                "clusters": g_n,
                "groups": len(groups_reg),
            }
            section9[f"{e}.{p}"] = reading
            g_per_part[f"{e}.{p}"] = {
                "G": g_n,
                "strictest_G": len(groups_reg),
                "direct_pairs_count_information_only_not_the_strictest_count": direct,
                "lineages": parts_out[p]["lineages_registered"],
            }
        reg_eval[e] = {
            "N_e": n_e[e],
            "parts": parts_out,
            "families_union_over_both_parts": sorted(fam_union),
            "n_families_union_over_both_parts": len(fam_union),
            "families_union_fewer_than_12": len(fam_union) < 12,
            "lineages_registered": sum(parts_out[p]["lineages_registered"] for p in PARTS),
            "lineages_not_registered": counts[e]["NOT REGISTERED"],
        }
        if len(fam_union) < 12:
            departures_family.append(
                {
                    "evaluation": e,
                    "part": "both (union of the two parts' families)",
                    "n_families": len(fam_union),
                    "families": sorted(fam_union),
                }
            )

    registration = {
        "what": (
            "ADR-0033 addendum 1 section 4A stage 5 (registration) and the counts of section 4 item 6: the lineages left in S after "
            "stage 4 are registered; G_e,A and G_e,B are the numbers of clusters with a registered lineage. Assembled by code from the "
            "map, partition, candidate and capacity records; no judgement."
        ),
        "status": (
            "Part of G-gen's record of record, made at the human lead's domain list of 2026-11-26 (ADR-0033 choice 2, option (a))"
        ),
        "evaluations": reg_eval,
        "registered_total": len(registered),
        "registration_table_clusters_over_lineages": {
            e: {
                p: f"{len(registered_by[e][p])}/{sum(len(v) for v in registered_by[e][p].values())}"
                for p in PARTS
            }
            for e in EVALS
        },
        "expected_table_equal": True,
        "N_e": n_e,
        "part_counts_in_clusters_and_in_groups": part_counts,
        "family_count": {
            "rule": (
                "section 4 item 6: the number of families among the registered lineages is printed per evaluation and per part; fewer "
                "than 12 is recorded as a departure from line 268 of ADR-0033 and stops nothing (decided, section 13 item 14 (a))"
            ),
            "carried_by": CAPACITY,
            "fewer_than_12_is_a_departure_from_ADR_0033_line_268": departures_family,
            "per_evaluation_and_part": {
                e: {p: reg_eval[e]["parts"][p]["n_families"] for p in PARTS} for e in EVALS
            },
            "per_evaluation_union_over_both_parts": {
                e: reg_eval[e]["n_families_union_over_both_parts"] for e in EVALS
            },
        },
        "section_9_item_5_reading_per_part": section9,
        "registered_lineages": registered,
        "capacity_drops": {k: removed[k] for k in sorted(removed)},
        "inputs_sha256": {k: inp.sha(k) for k in [SURVIVORS, MAP, PARTITION, CAPACITY, CANDIDATES]},
        "status_record_v1": {"path": OUT_STATUS, "sha256": status_sha},
        "script_sha256": script_sha,
    }
    registration_text = dumps(registration)
    registration_sha = sha_bytes(registration_text.encode("utf-8"))

    # ---- G-gen's record, DRAFT --------------------------------------------------------------------------------------
    pooled_sums: dict[str, str] = {}
    for ln in inp.text(POOLED_SUMS).splitlines():
        if ln.strip():
            h, name = ln.split(None, 1)
            pooled_sums[name.strip()] = h
    gz = gzip.decompress(inp.raw(POOLED_TABLE_GZ))
    check(
        pooled_sums.get("pooled_table.json") == sha_bytes(gz),
        "pooled_table.json.gz does not decompress to the hash in SHA256SUMS_pooled.txt",
    )
    check(
        pooled_sums.get("dropped.json") == inp.sha(DROPPED),
        "dropped.json differs from SHA256SUMS_pooled.txt",
    )

    seed_summary = []
    for rel in HASHES_SEEDS:
        h = inp.json(rel)
        n_files = 0
        n_attempts = 0
        statuses: list[int] = []
        all_ok = True
        for unit in h["units"].values():
            all_ok = all_ok and bool(unit["ok"])
            for att in unit["attempts"]:
                n_attempts += 1
                n_files += len(att["files"])
                all_ok = all_ok and bool(att["ok"])
                statuses.extend(c["exit_status"] for c in att["commands"])
        seed_summary.append(
            {
                **ref(inp, rel),
                "seed_set": h["seed_set"],
                "plan_sha256": h["plan_sha256"],
                "units": sorted(h["units"]),
                "n_attempts": n_attempts,
                "n_output_files_hashed": n_files,
                "n_commands": len(statuses),
                "all_exit_statuses_zero": all(s == 0 for s in statuses),
                "all_units_ok": all_ok,
            }
        )
    check(
        len({s["plan_sha256"] for s in seed_summary}) == 1,
        "the three seeds' hash records name different run plans",
    )
    check(
        seed_summary[0]["plan_sha256"] == hash_record["vii_run_plan"]["sha256"],
        "the run plan hash of the seed records differs from the hash record",
    )

    stage0_fresh = {
        "i_survivor_list": hash_record["i_survivor_list"],
        "ii_script_listing": hash_record["ii_script_listing"],
        "iii_run_copies": {
            "copy_audit": hash_record["iii_copy_audit"],
            "run_copies": hash_record["iii_run_copies"],
        },
        "iv_class_table_and_amendment_list": {
            "class_table": hash_record["iv_class_table"],
            "amendment_list": hash_record["iv_amendment_list"],
        },
        "v_pooling_script_and_field_table": {
            "pooling_script": hash_record["v_pooling_script"],
            "field_table": hash_record["v_field_table"],
        },
        "vi_dry_run": hash_record["vi_dry_run"],
        "vii_run_plan": hash_record["vii_run_plan"],
    }
    stage_0_hashes = {
        "hash_record_stage_0_and_1S": {**ref(inp, HASH_RECORD), "what": hash_record["what"]},
        "hash_record_stages_2_to_4": {**ref(inp, HASH_RECORD_2_4), "what": hash_record_2_4["what"]},
        "approved_text": hash_record["approved_text"],
        "generators_commit": hash_record["generators_commit"],
        "rule_scripts_commit": hash_record["rule_scripts_commit"],
        "survivor_list": hash_record["i_survivor_list"],
        "map_of_record": hash_record["map_of_record"],
        "runner": hash_record["runner"],
        "lead_rulings_8": hash_record["lead_rulings"],
        "second_solvers": hash_record["second_solvers"],
        "distinct_item_key": hash_record_2_4["distinct_item_key"],
        "partition_code": hash_record_2_4["partition_code"],
        "pool_builder": hash_record_2_4["pool_builder"],
        "capacity_runner": hash_record_2_4["capacity_runner"],
        "capacity_seed": hash_record_2_4["capacity_seed"],
        "capacity_label": hash_record_2_4["capacity_label"],
        "fresh_run_hashes_stage_1S_point_9": stage0_fresh,
        "verified_against_files_in_this_worktree": {k: verified[k] for k in sorted(verified)},
        "recorded_but_not_checked_here_because_the_file_is_not_in_this_worktree": sorted(
            not_in_worktree
        ),
    }

    def rulings_title(rel: str, rid: str) -> str:
        m = re.search(r"^- \*\*(" + re.escape(rid) + r"\.[^*]*)\*\*", inp.text(rel), flags=re.M)
        if m is None:
            raise Stop(f"ruling {rid} not found in {rel}")
        return m.group(1).strip()

    def ruling_entry(
        rel: str, rid: str, excerpts: list[str], classification: str
    ) -> dict[str, Any]:
        text = inp.text(rel)
        for ex in excerpts:
            check(ex in text, f"excerpt of {rid} not found in {rel}")
        return {
            **ref(inp, rel),
            "ruling": rid,
            "ruling_text_excerpts": excerpts,
            "classification_of_the_records_check": classification + " (PENDING LEAD REVIEW)",
            "records_check": ref(inp, RECORDS_CHECK),
        }

    gap_filling = [
        ruling_entry(
            RULINGS_8,
            "R-46",
            [
                "a field is a rule only if its prediction for an item can be computed without that item's answer",
                "This ruling leans toward passing for the two fields it leaves unread",
            ],
            "fills a gap (what a 'rule' is); leans toward passing; not a departure",
        ),
        ruling_entry(
            RULINGS_8,
            "R-54",
            [
                "This reading is the one favourable to the lineages and is reported to the human lead as such",
            ],
            "reads 'fixtures carry no answer' as allowing aggregate format lines from the keys; favourable to the lineages; a reading, not a departure",
        ),
    ]

    departures = {
        "lead_ruling_R_56": {
            **ref(inp, RULINGS_8),
            "title": rulings_title(RULINGS_8, "R-56"),
            "what": "a departure from the text of stage 1S point 6, in the direction unfavourable to passing, made before any fresh figure existed",
        },
        "lead_ruling_R_61": {
            **ref(inp, RULINGS_9),
            "title": rulings_title(RULINGS_9, "R-61"),
            "what": "a departure from stage 0: the distinct-item key, the pool builder and the capacity runner were hashed after the partition of record was computed",
            "hashed_late": {
                k: hash_record_2_4[k]
                for k in ("distinct_item_key", "pool_builder", "capacity_runner")
            },
        },
        "lead_ruling_R_60": ruling_entry(
            RULINGS_8,
            "R-60",
            [
                "The C1 commands that the final auditor ran with `python -I` ignore `PYTHONHASHSEED`.",
                "reproducibility across runs is not claimed for those five scripts",
            ],
            'departure from ADR-0033 section 6.2 ("Every process runs with PYTHONHASHSEED=0"): five C1 scripts run with -I ignore PYTHONHASHSEED',
        ),
        "lead_ruling_R_62_b": ruling_entry(
            RULINGS_9,
            "R-62",
            [
                "The key also relabels object words, event words and invented category words, as well as personal and place names.",
                "which is less favourable to passing",
            ],
            "departure from the decided reading (i), 'names relabelled only': the key relabels object, event and invented words as well as names; wider, less favourable to passing",
        ),
        "lead_ruling_R_62_c": ruling_entry(
            RULINGS_9,
            "R-62",
            [
                "`R2.caesar_shift` keeps its invented words: there they are the text being shifted, and relabelling them changes the answer",
                "is reported to the human lead for his confirmation with the capacity results",
            ],
            "the R2.caesar_shift exception: favourable to that registered part-B lineage, written with the partition possibly in view; awaiting the human lead's confirmation",
        ),
        "lead_ruling_R_66": ruling_entry(
            RULINGS_9,
            "R-66",
            [
                'otherwise the fixed sentence "not on the survivor list of record; superseded or dropped before it (no single committed reason found)" (141)',
            ],
            "against section 8 and section 3 item 6: 141 lineages carry no single committed reason (180 counting the superseded-by tier, 39)",
        ),
        "family_count_fewer_than_12_is_a_departure_from_ADR_0033_line_268": {
            "applies": bool(departures_family),
            "stops_nothing": True,
            "entries": departures_family,
            "source": "registration_record.json, family_count",
        },
    }

    stage4_rounds: dict[str, Any] = {
        "capacity_record": ref(inp, CAPACITY),
        "spec": capacity["spec"],
        "inputs_recorded_in_it": capacity["inputs"],
        "every_count_is_in_the_capacity_record": (
            "per round, cluster, lineage and level: target, attempts, count, ended, solver_disagreements; and the union by level"
        ),
        "per_part": {},
    }
    for e in EVALS:
        for p in PARTS:
            cap = capacity["parts"][e][p]
            stage4_rounds["per_part"][f"{e}.{p}"] = {
                "start": {k: sorted(v) for k, v in sorted(cap["start"].items())},
                "G_start": cap["G_start"],
                "G_registered": cap["G_registered"],
                "rounds": [
                    {
                        "round": r["round"],
                        "G": r["G"],
                        "D_G": r["D_G"],
                        "failing": sorted(r["failing"]),
                        "clusters": {
                            c: {
                                "k": v["k"],
                                "D_lin": v["D_lin"],
                                "union_evaluated": v["union_evaluated"],
                                "union_by_level": v.get("union_by_level"),
                            }
                            for c, v in sorted(r["clusters"].items())
                        },
                    }
                    for r in cap["rounds"]
                ],
                "removed": cap["removed"],
            }

    domain_list_out = domain_list_block(inp)
    gen = inp.json(GENERATOR_FILES)
    closure = gen["c_static_import_closure_of_b_recommended_freeze_list"]
    check(
        closure["count"] == len(closure["sha256"]) == 49,
        "the import closure does not hold 49 files",
    )
    check(
        gen["generators_commit"].startswith("7cd0ac5a"),
        "the generator file list is for another commit",
    )
    for path, sha in sorted(closure["sha256"].items()):
        check(inp.exists(path), f"frozen generator file missing: {path}")
        check(inp.sha(path) == sha, f"frozen generator file differs: {path}")
    frozen_generator_files = {
        "commit": "7cd0ac5a",
        "commit_full": gen["generators_commit"],
        "what": "the static import closure of the functions behind the builders of the 65 registered lineages",
        "source_list": ref(inp, GENERATOR_FILES),
        "unchanged_since_the_commit": gen["unchanged_since_generators_commit"],
        "count": len(closure["sha256"]),
        "files": [{"path": p, "sha256": h} for p, h in sorted(closure["sha256"].items())],
        "rehashed_in_the_worktree_and_equal": True,
    }
    ggen = {
        "status": GGEN_STATUS,
        "domain_list": domain_list_out,
        "what": (
            "G-gen's record of record (ADR-0033 addendum 1 section 4A stage 6), assembled by code. It lists, as a path and a "
            "SHA-256 or as the value itself, every item of stage 6's sentence, with the human lead's domain list. It is not a "
            "result. Astra review: NOT_PERFORMED."
        ),
        "stage_6_items": {
            "survivor_list_of_record": {
                **ref(inp, SURVIVORS),
                "lineages": {e: len(survivors["evaluations"][e]) for e in EVALS},
                "total": len(surv_ids),
            },
            "map_of_record": {
                **ref(inp, MAP),
                "written_lineages": len(lineages),
                "clusters": len(mp["clusters"]),
                "groups": len(mp["groups"]),
                "links": len(mp["links"]),
                "borderline_pairs": len(mp["borderline_pairs"]),
            },
            "fresh_run_seven_hashes_stage_1S_point_9": stage0_fresh,
            "record_of_the_stage_2_conditions": {**ref(inp, STAGE2), "lineages_read": len(stage2)},
            "hash_of_every_output_file_of_the_run_as_taken_when_its_unit_ended": {
                "hash_records": seed_summary,
                "total_output_files_hashed": sum(s["n_output_files_hashed"] for s in seed_summary),
                "the_files_themselves": (
                    "under the directories named in the `dir` fields of the hash records, in the git-ignored experiments/ tree; "
                    "they are not committed"
                ),
                "run_plan": hash_record["vii_run_plan"],
            },
            "pooled_table": {
                "pooled_table_json_sha256_from_SHA256SUMS_pooled": pooled_sums["pooled_table.json"],
                "pooled_table_json_gz_committed": ref(inp, POOLED_TABLE_GZ),
                "gz_decompresses_to_the_hash_above": True,
                "sums_file": ref(inp, POOLED_SUMS),
                "every_hash_in_the_sums_file": {k: pooled_sums[k] for k in sorted(pooled_sums)},
            },
            "lineages_dropped_by_the_fresh_run": {
                "file": ref(inp, DROPPED),
                "count": len(dropped_by_run),
                "lineages": dropped_by_run,
                "per_evaluation": {
                    e: sum(1 for x in dropped_by_run if eval_of[x] == e) for e in EVALS
                },
                "the_seven_that_come_from_the_rules_wording": {
                    "ids": sorted(WORDING_SEVEN),
                    "note_source": ref(inp, WORDS_11),
                },
            },
            "candidates": {
                **ref(inp, CANDIDATES),
                "counts": {e: len(candidates[e]) for e in EVALS},
                "total": len(cand_ids),
            },
            "partition": {
                "record": ref(inp, PARTITION),
                "code": hash_record_2_4["partition_code"],
                "seed": partition["seed"],
                "derived_integers": partition["derived_integers"],
                "step2": partition["step2"],
                "counts": partition["counts"],
            },
            "rounds_of_stage_4_with_every_count": stage4_rounds,
            "registered_lineages": {
                "total": len(registered),
                "per_evaluation_and_part": {
                    e: {
                        p: sorted(x for v in registered_by[e][p].values() for x in v) for p in PARTS
                    }
                    for e in EVALS
                },
            },
            "status_record_first_version": {"path": OUT_STATUS, "sha256": status_sha, "version": 1},
            "registration_record": {"path": OUT_REGISTRATION, "sha256": registration_sha},
            "G_per_part_with_the_strictest_counts_beside_it": {
                "reading": (
                    "strictest = the count if borderline pairs were merged (section 1 item 3; lead ruling R-65): the number of groups "
                    "(components of the graph whose links are the borderline pairs, over all clusters of the map, whatever the status of "
                    "the lineages a chain passes through) that hold a cluster with a registered lineage of the evaluation in the part. "
                    "`strictest_G_direct_pairs_only` is printed as information and is not the strictest count."
                ),
                "values": g_per_part,
            },
            "N_e": n_e,
            "counts_of_each_part_in_clusters_and_in_groups": part_counts,
            "every_hash_of_stage_0": stage_0_hashes,
        },
        "departures": departures,
        "awaiting_human_lead_confirmation": ["R-62 (c)"],
        "gap_filling_rulings_that_lean_toward_passing": gap_filling,
        "frozen_generator_files": frozen_generator_files,
        "independent_check_of_the_records": {
            **ref(inp, RECORDS_CHECK),
            "what": "independent engineering evidence, not Astra validation and not human approval",
        },
        "lead_rulings": [ref(inp, RULINGS_8), ref(inp, RULINGS_9)],
        "section_9_item_5_reading_per_part": section9,
        "inputs_sha256": {
            k: inp.sha(k)
            for k in sorted(
                {
                    SURVIVORS,
                    MAP,
                    STAGE2,
                    PARTITION,
                    CAPACITY,
                    CANDIDATES,
                    DROPPED,
                    POOLED_SUMS,
                    POOLED_TABLE_GZ,
                    HASH_RECORD,
                    HASH_RECORD_2_4,
                    RULINGS_8,
                    RULINGS_9,
                    WORDS_11,
                    WORDS_13,
                    ADR_0033,
                    RECORDS_CHECK,
                    GENERATOR_FILES,
                    DOMAIN_LIST,
                    *HASHES_SEEDS,
                }
            )
        },
        "script_sha256": script_sha,
    }
    ggen_text = dumps(ggen)
    return {OUT_STATUS: status_text, OUT_REGISTRATION: registration_text, OUT_GGEN: ggen_text}


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--root", default=".", help="the implementation worktree that holds the inputs")
    ap.add_argument(
        "--out",
        default=None,
        help="where the three files are written, mirroring the worktree paths (default: the root)",
    )
    ap.add_argument(
        "--domain-list",
        default=None,
        help="path of domain_list.json if it is not yet in the root (default: the root's file)",
    )
    args = ap.parse_args()
    root = Path(args.root).resolve()
    out = Path(args.out).resolve() if args.out else root
    script_sha = sha_bytes(Path(__file__).read_bytes())
    inp = Inputs(root)
    if args.domain_list:
        inp.override[DOMAIN_LIST] = Path(args.domain_list).resolve()
    try:
        files = build(inp, script_sha)
    except Stop as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        return 1
    for rel, text in files.items():
        dest = out / rel
        if dest.exists():
            if dest.read_text(encoding="utf-8") != text:
                print(
                    f"STOP: {dest} exists with other content; nothing overwritten", file=sys.stderr
                )
                return 1
            print(f"unchanged: {rel}")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
        print(f"wrote: {rel}")
    for rel, text in files.items():
        print(f"sha256 {sha_bytes(text.encode('utf-8'))}  {rel}")
    print(f"sha256 {script_sha}  (this script)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
