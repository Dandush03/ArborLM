"""ADR-0033 addendum 1, section 4 (steps 1 to 4) and section 4A stage 3: the cluster partition.

A pure function from (map of record, candidate list, seed) to the partition. Standard library only,
no hash(), no dependence on set iteration order, deterministic bytes out. Written from the approved
text of the addendum (commit 2c944302) and from nothing else.

Command line (the lead runs it once, with the registered seed, on the real candidate list):

    PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 uv run --locked python partition.py \
        --map MAP.json --candidates CANDIDATES.json --seed SEED --out OUT.json

Part names follow the text: A is the teaching-eligible side, B the held-out side.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

EVALS: tuple[str, ...] = ("R1", "R2", "M1", "C1")  # section 4 step 3: the order of the evaluations
LABEL = "cluster-partition"  # section 4: the label of every stream of this role


# ---------------------------------------------------------------- section 4: the mechanics


def derive(seed: int, *labels: str) -> int:
    """The integer that seeds stream(seed, labels): section 4, first bullet."""
    text = "|".join([str(seed), *labels])
    return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")


def stream(seed: int, *labels: str) -> random.Random:
    """stream(seed, l1, ..., lk) of section 4 (CPython 3.12 random.Random, Mersenne Twister)."""
    return random.Random(derive(seed, *labels))


def shuffled(identities: Iterable[str], rng: random.Random) -> list[str]:
    """Section 4, third bullet: sort by Unicode code-point order, then call shuffle once."""
    out = sorted(identities)
    rng.shuffle(out)
    return out


def components(nodes: Iterable[str], links: Iterable[tuple[str, str]]) -> dict[str, list[str]]:
    """Connected components. Key: the smallest node in code-point order (section 3 item 1).

    Values are sorted member lists. Nothing depends on the order of the inputs.
    """
    node_list = sorted(set(nodes))
    parent = {x: x for x in node_list}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in links:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    members: dict[str, list[str]] = {}
    for x in node_list:
        members.setdefault(find(x), []).append(x)
    return {min(v): sorted(v) for v in members.values()}


# ---------------------------------------------------------------- section 3 and section 4 step 1


def build_structure(
    lineage_eval: dict[str, str],
    links: Iterable[Sequence[str]],
    borderline: Iterable[Sequence[str]],
    candidates: Iterable[str],
) -> dict[str, Any]:
    """Global clusters (section 3 item 1), the cluster graph of borderline pairs, the groups of
    step 1.

    lineage_eval: every written lineage id -> its evaluation. links: same-procedure pairs of
    lineages.
    borderline: borderline pairs of lineages. candidates: the candidate lineage ids.
    """
    cand = sorted(set(candidates))
    for x in cand:
        if x not in lineage_eval:
            raise ValueError(f"candidate {x!r} is not a lineage of the map")
    cand_set = set(cand)
    link_pairs = [(a, b) for a, b in (tuple(p) for p in links)]
    for a, b in link_pairs:
        if a not in lineage_eval or b not in lineage_eval:
            raise ValueError(f"link {a!r}, {b!r} names a lineage not in the map")
    clusters = components(lineage_eval, link_pairs)  # global clusters over ALL written lineages
    where = {x: cid for cid, mem in clusters.items() for x in mem}
    # evaluations in which a cluster has a candidate lineage
    cand_evals = {
        cid: sorted({lineage_eval[x] for x in mem if x in cand_set})
        for cid, mem in clusters.items()
    }
    has_candidate = {cid: bool(ev) for cid, ev in cand_evals.items()}
    cluster_pairs: set[tuple[str, str]] = set()
    for a, b in (tuple(p) for p in borderline):
        if a not in where or b not in where:
            raise ValueError(f"borderline pair {a!r}, {b!r} names a lineage not in the map")
        if where[a] != where[b]:  # section 4 step 1: pairs between two different clusters
            cluster_pairs.add((min(where[a], where[b]), max(where[a], where[b])))
    pairs = sorted(cluster_pairs)
    # every cluster, with or without candidate lineage, is a node (item 17: it passes a group on)
    raw_groups = components(clusters, pairs)
    groups: dict[str, list[str]] = {}  # identity -> clusters with a candidate lineage
    group_of: dict[str, str] = {}  # every cluster -> identity of its group, or "" if unassigned
    tied: set[str] = set()
    for a, b in pairs:
        tied.add(a)
        tied.add(b)
    for mem in raw_groups.values():
        with_cand = sorted(c for c in mem if has_candidate[c])
        gid = with_cand[0] if with_cand else ""  # smallest identity among clusters with a candidate
        if with_cand:
            groups[gid] = with_cand
        for c in mem:
            group_of[c] = gid
    group_evals = {g: sorted({e for c in cs for e in cand_evals[c]}) for g, cs in groups.items()}
    return {
        "clusters": clusters,
        "where": where,
        "cand_evals": cand_evals,
        "has_candidate": has_candidate,
        "pairs": pairs,
        "raw_groups": raw_groups,
        "groups": groups,
        "group_of": group_of,
        "group_evals": group_evals,
        "tied": tied,
    }


def w_e(st: dict[str, Any], g: str, e: str) -> int:
    """w_e(g): the number of clusters of group g with a candidate lineage in evaluation e."""
    return sum(1 for c in st["groups"][g] if e in st["cand_evals"][c])


# ---------------------------------------------------------------- section 4 steps 2 and 3


def step2(st: dict[str, Any], seed: int) -> dict[str, Any]:
    """Cross-evaluation groups first. A group goes to B if B holds no more clusters than A, else
    A."""
    cross = [g for g in st["groups"] if len(st["group_evals"][g]) >= 2]  # X
    order = shuffled(cross, stream(seed, LABEL, "cross"))
    placed: dict[str, str] = {}
    trace: list[dict[str, Any]] = []
    in_a = in_b = 0
    for g in order:
        weight = len(st["groups"][g])  # w(g)
        to_b = in_b <= in_a
        trace.append(
            {
                "group": g,
                "w": weight,
                "b_before": in_b,
                "a_before": in_a,
                "part": "B" if to_b else "A",
            }
        )
        placed[g] = "B" if to_b else "A"
        if to_b:
            in_b += weight
        else:
            in_a += weight
    return {
        "order": order,
        "part": placed,
        "trace": trace,
        "clusters_in_A": in_a,
        "clusters_in_B": in_b,
    }


def step3(st: dict[str, Any], seed: int, x_part: dict[str, str]) -> dict[str, dict[str, Any]]:
    """Then each evaluation, in the order R1, R2, M1, C1. Returns per evaluation the placement."""
    out: dict[str, dict[str, Any]] = {}
    for e in EVALS:
        n_e = sum(1 for c in st["clusters"] if e in st["cand_evals"][c])
        half = n_e // 2
        a_e = sum(w_e(st, g, e) for g, p in sorted(x_part.items()) if p == "A")
        local = [g for g in st["groups"] if st["group_evals"][g] == [e]]  # L_e
        order = shuffled(local, stream(seed, LABEL, e))
        p_placed = 0
        part: dict[str, str] = {}
        trace: list[dict[str, Any]] = []
        for g in order:
            weight = w_e(st, g, e)
            fits = a_e + p_placed + weight <= half
            if fits:
                part[g] = "A"
                p_placed += weight
            else:
                part[g] = "B"
            trace.append({"group": g, "w_e": weight, "fits": fits, "part": part[g]})
        out[e] = {
            "N_e": n_e,
            "half": half,
            "a_e": a_e,
            "L_e_size": len(local),
            "order": order,
            "part": part,
            "p": p_placed,
            "trace": trace,
        }
    return out


# ---------------------------------------------------------------- the partition


def partition(
    lineage_eval: dict[str, str],
    links: Iterable[Sequence[str]],
    borderline: Iterable[Sequence[str]],
    candidates: Iterable[str],
    seed: int,
) -> dict[str, Any]:
    """The partition of section 4 with every decided option. Pure: no I/O, no clock, no hash()."""
    st = build_structure(lineage_eval, links, borderline, candidates)
    s2 = step2(st, seed)
    s3 = step3(st, seed, s2["part"])
    group_part: dict[str, str] = dict(s2["part"])
    for e in EVALS:
        group_part.update(s3[e]["part"])
    # a group with a candidate cluster is in X or in exactly one L_e, so it is placed exactly once
    assert sorted(group_part) == sorted(st["groups"]), "a group with a candidate was not placed"
    # step 4: every cluster with a candidate lineage takes its group's part
    cluster_part = {c: group_part[g] for g, cs in sorted(st["groups"].items()) for c in cs}
    # a cluster with no candidate lineage has no part; the part of its group is printed beside it
    no_candidate = {}
    for c in sorted(st["clusters"]):
        if st["has_candidate"][c]:
            continue
        gid = st["group_of"][c]
        no_candidate[c] = {
            "tied_by_borderline_pair": c in st["tied"],
            "group": gid or None,
            "group_part": group_part[gid] if gid else None,
        }
    counts: dict[str, dict[str, Any]] = {}
    for e in EVALS:
        cs = [c for c in sorted(st["clusters"]) if e in st["cand_evals"][c]]
        gs = [g for g in sorted(st["groups"]) if w_e(st, g, e) > 0]
        counts[e] = {
            "N_e": len(cs),
            "half_floor": len(cs) // 2,
            "clusters_A": sum(1 for c in cs if cluster_part[c] == "A"),
            "clusters_B": sum(1 for c in cs if cluster_part[c] == "B"),
            "groups_A": sum(1 for g in gs if group_part[g] == "A"),
            "groups_B": sum(1 for g in gs if group_part[g] == "B"),
            "groups_with_candidate_cluster": len(gs),
            "group_sizes_in_candidate_clusters": sorted(w_e(st, g, e) for g in gs),
            "step3": {
                "a_e": s3[e]["a_e"],
                "L_e_groups": s3[e]["L_e_size"],
                "p_placed_in_A": s3[e]["p"],
                "order": s3[e]["order"],
                "trace": s3[e]["trace"],
            },
        }
    return {
        "seed": seed,
        "derived_integers": {
            "cross": derive(seed, LABEL, "cross"),
            **{e: derive(seed, LABEL, e) for e in EVALS},
        },
        "step2": {
            "order": s2["order"],
            "trace": s2["trace"],
            "clusters_in_A": s2["clusters_in_A"],
            "clusters_in_B": s2["clusters_in_B"],
        },
        "counts": counts,
        "cluster_part": {c: cluster_part[c] for c in sorted(cluster_part)},
        "cluster_groups": {c: g for g, cs in sorted(st["groups"].items()) for c in cs},
        "clusters_without_candidate": no_candidate,
        "n_clusters": len(st["clusters"]),
        "n_clusters_with_candidate": len(cluster_part),
        "n_groups_with_candidate": len(st["groups"]),
    }


# ---------------------------------------------------------------- files and command line


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def candidate_ids(candidate_list: dict[str, Any]) -> list[str]:
    """The ids of a candidate list file (build_candidates.py form): every evaluation's list."""
    ids: list[str] = []
    for e in sorted(candidate_list["candidates"]):
        ids.extend(candidate_list["candidates"][e])
    if len(ids) != len(set(ids)):
        raise ValueError("a lineage is a candidate twice")
    return sorted(ids)


def run(map_obj: dict[str, Any], candidate_list: dict[str, Any], seed: int) -> dict[str, Any]:
    lineage_eval = {x: v["evaluation"] for x, v in map_obj["lineages"].items()}
    for x, e in lineage_eval.items():
        if x.split(".", 1)[0] != e or e not in EVALS:
            raise ValueError(f"lineage {x!r} has evaluation {e!r}")
    ids = candidate_ids(candidate_list)
    for e, lst in candidate_list["candidates"].items():
        for x in lst:
            if lineage_eval.get(x) != e:
                raise ValueError(f"candidate {x!r} listed under {e!r} is not of that evaluation")
    result = partition(lineage_eval, map_obj["links"], map_obj["borderline_pairs"], ids, seed)
    # consistency of the file's own derived fields with what the code derives from links and pairs
    st = build_structure(lineage_eval, map_obj["links"], map_obj["borderline_pairs"], ids)
    file_clusters = {c["cluster_id"]: sorted(c["members"]) for c in map_obj["clusters"]}
    result["map_consistency"] = {
        "clusters_equal_map_field": file_clusters == st["clusters"],
        "groups_equal_map_field": sorted(sorted(g) for g in map_obj["groups"])
        == sorted(sorted(g) for g in st["raw_groups"].values()),
    }
    return result


def dumps(obj: Any) -> bytes:
    return (json.dumps(obj, sort_keys=True, indent=1, ensure_ascii=True) + "\n").encode("ascii")


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--map", required=True, type=Path)
    ap.add_argument("--candidates", required=True, type=Path)
    ap.add_argument("--seed", required=True, type=int)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(argv)
    if sys.version_info[:2] != (3, 12):
        print(
            f"stop: the text names CPython 3.12, this is {sys.version.split()[0]}", file=sys.stderr
        )
        return 2
    map_obj = json.loads(args.map.read_text(encoding="utf-8"))
    cand_obj = json.loads(args.candidates.read_text(encoding="utf-8"))
    if args.out.exists():
        print("stop: the output exists; the partition is computed once", file=sys.stderr)
        return 4
    result = run(map_obj, cand_obj, args.seed)
    result["inputs"] = {
        "map_sha256": _sha256_file(args.map),
        "candidates_sha256": _sha256_file(args.candidates),
        "code_sha256": _sha256_file(Path(__file__)),
    }
    if not all(result["map_consistency"].values()):
        print(
            "stop: the map's clusters or groups differ from what its links and pairs give",
            file=sys.stderr,
        )
        return 3
    args.out.write_bytes(dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
