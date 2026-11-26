"""(v3: section 6.8 parse stops at the next level-2 heading; v2: survivor counts compared as counts.)
Independent check of the M0 stage-5/6 records (registration, status record v1, G-gen's record).

Auditor's script; build_records.py is NOT imported. Standard library only.
Computes NO stream with the label `cluster-partition` (addendum 1 section 4 item 7: the partition is
computed once); each cluster's part is read from partition_of_record.json and checked for consistency only.

Usage (from the implementation worktree root):
  PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 uv run --locked python <this> --root . \
      --spec-root <m0-spec worktree> --families <families.json> --out <out.json>
"""

from __future__ import annotations

import argparse
import ast
import gzip
import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

EVALS = ("R1", "R2", "M1", "C1")
PARTS = ("A", "B")
FR = "docs/reviews/m0-fresh-run-2026-11-26"
WORDS = "docs/reviews/m0-lineage-decision-2026-11-25"
MAN = "studies/m0/manifests"
NOREASON = "not on the survivor list of record; superseded or dropped before it (no single committed reason found)"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


class UF:
    def __init__(self) -> None:
        self.p: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)


def s9(g: int) -> str:
    if g == 0:
        return "NO CLUSTER"
    if g == 1:
        return "ONE CLUSTER"
    return f"computed as written, {g - 1} df"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--spec-root", required=True)
    ap.add_argument("--families", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sample-seed", type=int, default=20261126)
    a = ap.parse_args()
    root = Path(a.root).resolve()
    spec_root = Path(a.spec_root).resolve()

    def load(rel: str):
        return json.loads((root / rel).read_text(encoding="utf-8"))

    out: dict = {}
    mp = load(f"{MAN}/map_of_record.json")
    surv = load(f"{MAN}/survivor_list_of_record.json")["evaluations"]
    s2 = load(f"{MAN}/stage2_conditions.json")
    part_rec = load(f"{MAN}/partition_of_record.json")
    cap = load(f"{MAN}/capacity_of_record.json")
    cand_file = load("studies/m0/registration/candidate_list.json")
    dropped = load(f"{FR}/run/pooled/dropped.json")
    reg = load(f"{MAN}/registration_record.json")
    st = load(f"{MAN}/status_record_v1.json")
    gg = load(f"{MAN}/g_gen_record.json")
    fam = json.loads(Path(a.families).read_text())["family"]

    # ---------------------------------------------------------------- the map
    ev_of = {x: v["evaluation"] for x, v in mp["lineages"].items()}
    cl_of = {x: c["cluster_id"] for c in mp["clusters"] for x in c["members"]}
    assert set(ev_of) == set(cl_of)
    out["map_cluster_identity_is_smallest_member"] = all(c["cluster_id"] == min(c["members"]) for c in mp["clusters"])
    ufl = UF()
    for x in ev_of:
        ufl.find(x)
    for p, q in mp["links"]:
        ufl.union(p, q)
    comp = defaultdict(set)
    for x in ev_of:
        comp[ufl.find(x)].add(x)
    out["map_clusters_equal_link_components"] = {min(v): sorted(v) for v in comp.values()} == {
        c["cluster_id"]: sorted(c["members"]) for c in mp["clusters"]
    }
    ufg = UF()
    for c in mp["clusters"]:
        ufg.find(c["cluster_id"])
    for p, q in mp["borderline_pairs"]:
        if cl_of[p] != cl_of[q]:
            ufg.union(cl_of[p], cl_of[q])
    groups_all = defaultdict(set)
    for c in mp["clusters"]:
        groups_all[ufg.find(c["cluster_id"])].add(c["cluster_id"])
    out["map_groups_equal_borderline_components"] = sorted(sorted(g) for g in groups_all.values()) == sorted(
        sorted(g) for g in mp["groups"]
    )
    out["borderline_pairs_within_one_cluster"] = sum(cl_of[p] == cl_of[q] for p, q in mp["borderline_pairs"])
    grp = {c: ufg.find(c) for c in set(cl_of.values())}
    out["n_groups"] = len(groups_all)
    out["largest_group"] = max(len(g) for g in groups_all.values())

    # ---------------------------------------------------------------- item 1: candidates
    drop_ids = {d["lineage"] for d in dropped}
    surv_all = {x for e in EVALS for x in surv[e]}
    s2_rows = {k: v for k, v in s2.items() if isinstance(v, dict) and "all_conditions" in v}
    s2_pass = {x for x, v in s2_rows.items() if v["all_conditions"] == "PASS"}
    out["stage2_rows"] = len(s2_rows)
    out["stage2_rows_equal_survivors"] = set(s2_rows) == surv_all
    out["stage2_pass"] = len(s2_pass)
    out["stage2_cluster_equals_map"] = all(v["map"]["cluster_id"] == cl_of[x] for x, v in s2_rows.items())
    cands = {e: sorted(x for x in surv[e] if x not in drop_ids and x in s2_pass) for e in EVALS}
    out["survivors_per_eval"] = {e: len(surv[e]) for e in EVALS}
    out["candidates_per_eval"] = {e: len(cands[e]) for e in EVALS}
    out["candidates_equal_candidate_list"] = all(cands[e] == sorted(cand_file["candidates"][e]) for e in EVALS)
    out["dropped"] = {"n": len(drop_ids), "subset_of_survivors": drop_ids <= surv_all}
    cand_all = {x for e in EVALS for x in cands[e]}
    cand_clusters = {cl_of[x] for x in cand_all}
    part_of = part_rec["cluster_part"]
    out["partition_clusters_equal_candidate_clusters"] = set(part_of) == cand_clusters
    gp: dict[str, set] = defaultdict(set)
    for c in cand_clusters:
        gp[grp[c]].add(part_of[c])
    out["one_part_per_group"] = all(len(v) == 1 for v in gp.values())
    group_part = {g: next(iter(v)) for g, v in gp.items()}
    gid = {}
    for g, members in groups_all.items():
        cc = sorted(m for m in members if m in cand_clusters)
        gid[g] = cc[0] if cc else None
    out["partition_cluster_groups_equal"] = all(part_rec["cluster_groups"][c] == gid[grp[c]] for c in cand_clusters)
    nocand = sorted(set(cl_of.values()) - cand_clusters)
    mism = []
    for c in nocand:
        got = part_rec["clusters_without_candidate"].get(c)
        exp = (gid[grp[c]], group_part.get(grp[c]))
        if got is None or (got["group"], got["group_part"]) != exp:
            mism.append([c, got, exp])
    out["clusters_without_candidate"] = {"n": len(nocand), "mismatch": mism,
                                         "n_with_group_part": sum(group_part.get(grp[c]) is not None for c in nocand)}
    N_e, cand_counts = {}, {}
    for e in EVALS:
        ce = {cl_of[x] for x in cands[e]}
        N_e[e] = len(ce)
        cand_counts[e] = {
            "clusters_A": sum(part_of[c] == "A" for c in ce),
            "clusters_B": sum(part_of[c] == "B" for c in ce),
            "groups_A": len({grp[c] for c in ce if part_of[c] == "A"}),
            "groups_B": len({grp[c] for c in ce if part_of[c] == "B"}),
        }
    out["N_e"] = N_e
    out["candidate_part_counts"] = cand_counts
    out["candidate_part_counts_equal_partition_record"] = all(
        part_rec["counts"][e][k] == v for e in EVALS for k, v in cand_counts[e].items()
    ) and all(part_rec["counts"][e]["N_e"] == N_e[e] for e in EVALS)

    # ---------------------------------------------------------------- item 1: capacity replay (logic of stage 4)
    registered: dict = {}
    issues: list[str] = []
    dlin: dict = defaultdict(set)
    dg: dict = defaultdict(set)
    cap_removed: dict = {}
    for e in EVALS:
        registered[e] = {}
        for p in PARTS:
            S = {x for x in cands[e] if part_of[cl_of[x]] == p}
            rec = cap["parts"][e][p]
            if {x for v in rec["start"].values() for x in v} != S:
                issues.append(f"{e}.{p}: start != candidates of the part")
            fixed = False
            for rd in rec["rounds"]:
                Gr = len({cl_of[x] for x in S})
                if rd["G"] != Gr:
                    issues.append(f"{e}.{p} r{rd['round']}: G")
                dg[Gr].add(rd["D_G"])
                if set(rd["clusters"]) != {cl_of[x] for x in S}:
                    issues.append(f"{e}.{p} r{rd['round']}: clusters")
                fail = set()
                for c, cr in rd["clusters"].items():
                    members = {x for x in S if cl_of[x] == c}
                    if set(cr["lineages"]) != members or cr["k"] != len(members):
                        issues.append(f"{e}.{p} r{rd['round']} {c}: members/k")
                    dlin[(Gr, cr["k"])].add(cr["D_lin"])
                    own = set()
                    for x, lv in cr["lineages"].items():
                        if sorted(lv) != [str(i) for i in range(7)]:
                            issues.append(f"{x}: levels")
                        for v, d in lv.items():
                            if d["target"] != cr["D_lin"]:
                                issues.append(f"{x} L{v}: target")
                            if d["count"] > d["target"] or (d["ended"] == "target") != (d["count"] == d["target"]):
                                issues.append(f"{x} L{v}: count/ended")
                            if d["count"] < cr["D_lin"] or d["solver_disagreements"] > 0:
                                own.add(x)
                    fail |= own
                    if own:
                        if cr.get("union_evaluated"):
                            issues.append(f"{c}: union evaluated with a failing lineage")
                    else:
                        if not cr.get("union_evaluated"):
                            issues.append(f"{c}: union not evaluated")
                        elif any(n < rd["D_G"] for n in cr["union_by_level"].values()):
                            fail |= members
                        if cr["k"] * cr["D_lin"] < rd["D_G"]:
                            issues.append(f"{c}: k*D_lin < D_G")
                if sorted(rd["failing"]) != sorted(fail):
                    issues.append(f"{e}.{p} r{rd['round']}: failing differs")
                S -= fail
                if not fail:
                    fixed = True
                    break
            if not fixed:
                issues.append(f"{e}.{p}: no round without removals")
            for r_ in rec["removed"]:
                cap_removed[r_["lineage"]] = r_
            if {x for v in rec["registered"].values() for x in v} != S:
                issues.append(f"{e}.{p}: registered != replay")
            byc: dict = defaultdict(list)
            for x in sorted(S):
                byc[cl_of[x]].append(x)
            registered[e][p] = dict(sorted(byc.items()))
    out["capacity_replay_issues"] = issues
    out["D_lin_one_value_per_G_k"] = all(len(v) == 1 for v in dlin.values())
    out["D_G_one_value_per_G"] = all(len(v) == 1 for v in dg.values())
    out["D_G_seen"] = {str(g): sorted(v) for g, v in sorted(dg.items())}
    out["capacity_removed"] = sorted(cap_removed)
    reg_all = sorted(x for e in EVALS for p in PARTS for v in registered[e][p].values() for x in v)
    out["registered_total"] = len(reg_all)
    out["registered_per_eval"] = {e: sum(len(v) for p in PARTS for v in registered[e][p].values()) for e in EVALS}
    G = {e: {p: len(registered[e][p]) for p in PARTS} for e in EVALS}
    out["G"] = G
    out["table"] = {e: {p: f"{G[e][p]}/{sum(len(v) for v in registered[e][p].values())}" for p in PARTS} for e in EVALS}
    out["registered_by_cluster"] = registered
    reg_groups = {e: {p: len({grp[c] for c in registered[e][p]}) for p in PARTS} for e in EVALS}
    out["registered_groups"] = reg_groups
    strict = reg_groups  # R-65: groups over all clusters, statuses ignored, holding a registered cluster of e,p
    direct: dict = {}
    for e in EVALS:
        direct[e] = {}
        for p in PARTS:
            cs = set(registered[e][p])
            u = UF()
            for c in cs:
                u.find(c)
            for x, y in mp["borderline_pairs"]:
                if cl_of[x] != cl_of[y] and cl_of[x] in cs and cl_of[y] in cs:
                    u.union(cl_of[x], cl_of[y])
            direct[e][p] = len({u.find(c) for c in cs})
    out["strictest_R65"] = strict
    out["direct_pairs_information"] = direct
    out["section_9_item_5"] = {f"{e}.{p}": s9(G[e][p]) for e in EVALS for p in PARTS}
    lost = {f"{e}.{p}": sorted(c for c in part_of if part_of[c] == p and any(cl_of[x] == c for x in cands[e])
                               and c not in registered[e][p]) for e in EVALS for p in PARTS}
    out["clusters_that_lost_every_candidate_at_capacity"] = lost
    families = {e: {p: sorted({fam[x] for v in registered[e][p].values() for x in v}) for p in PARTS} for e in EVALS}
    out["families_per_part"] = {e: {p: len(families[e][p]) for p in PARTS} for e in EVALS}
    out["families_union"] = {e: len(set(families[e]["A"]) | set(families[e]["B"])) for e in EVALS}
    out["families_lists"] = families
    # families of the 67 candidates and of the 82 survivors, for information
    out["families_candidates_per_eval"] = {e: len({fam[x] for x in cands[e]}) for e in EVALS}
    out["families_survivors_per_eval"] = {e: len({fam[x] for x in surv[e]}) for e in EVALS}

    # compare with registration_record.json
    ri = []
    if reg["registered_total"] != len(reg_all) or sorted(reg["registered_lineages"]) != reg_all:
        ri.append("registered_lineages")
    for e in EVALS:
        er = reg["evaluations"][e]
        if er["N_e"] != N_e[e] or reg["N_e"][e] != N_e[e]:
            ri.append(f"{e} N_e")
        n_e = sum(ev_of[x] == e for x in ev_of)
        if er["lineages_registered"] != out["registered_per_eval"][e] or er["lineages_not_registered"] != n_e - out["registered_per_eval"][e]:
            ri.append(f"{e} lineage counts")
        if er["n_families_union_over_both_parts"] != out["families_union"][e]:
            ri.append(f"{e} family union")
        for p in PARTS:
            pr = er["parts"][p]
            if pr["registered_by_cluster"] != registered[e][p]:
                ri.append(f"{e}.{p} registered_by_cluster")
            if pr["G"] != G[e][p]:
                ri.append(f"{e}.{p} G")
            if pr["G_start_of_stage_4"] != cand_counts[e][f"clusters_{p}"]:
                ri.append(f"{e}.{p} G_start")
            if pr["strictest_G"]["value"] != strict[e][p]:
                ri.append(f"{e}.{p} strictest")
            if pr["strictest_G"]["direct_pairs_count_information_only_not_the_strictest_count"]["value"] != direct[e][p]:
                ri.append(f"{e}.{p} direct")
            if sorted(pr["families_among_registered_lineages"]) != families[e][p] or pr["n_families"] != len(families[e][p]):
                ri.append(f"{e}.{p} families")
            if pr["families_fewer_than_12"] != (len(families[e][p]) < 12):
                ri.append(f"{e}.{p} family flag")
            got9 = pr["section_9_item_5_reading"]
            if (G[e][p] == 1) != got9.startswith("ONE CLUSTER") or (G[e][p] >= 2 and f"with {G[e][p] - 1} degrees of freedom" not in got9):
                ri.append(f"{e}.{p} section 9 item 5")
            if sorted(pr["clusters_that_had_a_candidate_and_lost_every_lineage_at_capacity_and_keep_their_part"]) != lost[f"{e}.{p}"]:
                ri.append(f"{e}.{p} lost clusters: record {pr['clusters_that_had_a_candidate_and_lost_every_lineage_at_capacity_and_keep_their_part']} vs {lost[f'{e}.{p}']}")
            if reg["part_counts_in_clusters_and_in_groups"][e]["registered_clusters_and_groups"][p] != {"clusters": G[e][p], "groups": reg_groups[e][p]}:
                ri.append(f"{e}.{p} clusters/groups")
            if reg["section_9_item_5_reading_per_part"][f"{e}.{p}"] != got9:
                ri.append(f"{e}.{p} s9 top-level")
    if reg["registration_table_clusters_over_lineages"] != out["table"]:
        ri.append("table")
    for x, v in reg["capacity_drops"].items():
        exp = dict(cap_removed[x], evaluation=ev_of[x], part=part_of[cl_of[x]])
        if v != exp:
            ri.append(f"capacity drop {x}")
    if sorted(reg["capacity_drops"]) != sorted(cap_removed):
        ri.append("capacity drop ids")
    out["registration_record_differences"] = ri
    out["expected_65_6_15_23_21"] = (len(reg_all), out["registered_per_eval"]) == (65, {"R1": 6, "R2": 15, "M1": 23, "C1": 21})

    # ---------------------------------------------------------------- item 2: status record
    L = st["lineages"]
    si: list[str] = []
    if set(L) != set(ev_of):
        si.append("ids differ from the map")
    w11 = (root / WORDS / "HUMAN_LEAD_WORDS_11.md").read_text()
    seven = ["R1.spatial_grid_walk_r5", "R1.swap_tracking_r5", "C1.circle_elimination_r2", "C1.cond_chain_f3",
             "C1.shared_lists_f3", "C1.union_find_links_f3", "R2.list_ops"]
    out["seven_named_in_words_11"] = {x: f"`{x.split('.', 1)[1]}`" in w11 or x.split(".", 1)[1] in w11 for x in seven}
    drop_by = {d["lineage"]: d for d in dropped}
    stage_counts: Counter = Counter()
    for x in sorted(ev_of):
        v = L.get(x, {})
        c = cl_of[x]
        exp = {"evaluation": ev_of[x], "global_cluster": c, "on_survivor_list": x in surv_all, "candidate": x in cand_all,
               "status": "REGISTERED" if x in reg_all else "NOT REGISTERED", "group": gid[grp[c]],
               "cluster_part": part_of.get(c, "none")}
        if c not in part_of:
            exp["group_part_beside_it"] = group_part.get(grp[c])
            exp["tied_by_borderline_pair"] = len(groups_all[grp[c]]) > 1
        else:
            exp["part_binds_it"] = True
        for k, val in exp.items():
            if v.get(k) != val:
                si.append(f"{x}: {k} {v.get(k)!r} != {val!r}")
        if x in reg_all:
            stage = None
        elif x in drop_by:
            stage = "stage 1S, fresh run"
        elif x in cap_removed:
            stage = "stage 4, capacity"
        elif x not in surv_all:
            stage = "before the survivor list"
        else:
            stage = "UNEXPLAINED"
        stage_counts[stage] += 1
        if v.get("stage") != stage:
            si.append(f"{x}: stage {v.get('stage')!r} != {stage!r}")
        if stage == "stage 1S, fresh run":
            src = drop_by[x]["reason"]
            rd = v.get("reason_detail", {})
            for k in src:
                if rd.get(k) != src[k]:
                    si.append(f"{x}: reason_detail.{k}")
            if rd.get("n_rows_over_the_bound") != len(drop_by[x]["all_rows_over_the_bound"]):
                si.append(f"{x}: n_rows")
            best = max(Fraction(r["abs_excess_plus_uncertainty"]["fraction"]) for r in drop_by[x]["all_rows_over_the_bound"])
            if best != Fraction(src["abs_excess_plus_uncertainty"]["fraction"]):
                si.append(f"{x}: the reason row is not the largest row of dropped.json")
            exv, un = Fraction(src["excess"]["fraction"]), Fraction(src["rounding_uncertainty"]["fraction"])
            if abs(exv) + un != Fraction(src["abs_excess_plus_uncertainty"]["fraction"]) or not abs(exv) + un > Fraction(15, 100):
                si.append(f"{x}: arithmetic or bound")
            if Fraction(src["pooled_figure"]["fraction"]) != exv:
                si.append(f"{x}: pooled figure != excess (base rate not zero?)")
            for needle in (f"'{src['rule']}'", f"unit {src['unit']}", f"level {src['level']}", src["excess"]["decimal_12dp"],
                           src["excess"]["fraction"], src["abs_excess_plus_uncertainty"]["decimal_12dp"], "15/100"):
                if needle not in v.get("reason", ""):
                    si.append(f"{x}: reason text lacks {needle!r}")
        if stage == "stage 4, capacity":
            exp_d = dict(cap_removed[x], evaluation=ev_of[x], part=part_of[c])
            if v.get("reason_detail") != exp_d:
                si.append(f"{x}: capacity reason_detail")
            r0 = cap_removed[x]
            if f"round {r0['round']}, part {part_of[c]}, G {r0['G']}, k {r0['k']}" not in v.get("reason", ""):
                si.append(f"{x}: capacity reason head")
            for lvl, d in r0["reasons"][0]["levels"].items():
                if f"level {lvl} (count {d['count']} of demand {d['demand']}, ended on {d['ended']})" not in v.get("reason", ""):
                    si.append(f"{x}: capacity reason level {lvl}")
        if ("note" in v) != (x in seven):
            si.append(f"{x}: wording note presence")
        if "note" in v and (v["status"] != "NOT REGISTERED" or v.get("stage") != "stage 1S, fresh run"):
            si.append(f"{x}: note with another status")
        if "note" in v and v.get("note_source") != f"{WORDS}/HUMAN_LEAD_WORDS_11.md":
            si.append(f"{x}: note source")
    out["status_stage_counts"] = {str(k): n for k, n in stage_counts.items()}
    out["status_record_differences"] = si
    out["status_counts_block_vs_mine"] = {
        e: {k: n for k, n in st["counts"]["not_registered_by_stage_per_evaluation"][e].items()} for e in EVALS
    }
    out["cellular_update"] = {
        "part": part_of.get("C1.cellular_update"),
        "members": sorted(x for x in ev_of if cl_of[x] == "C1.cellular_update"),
        "candidates": sorted(x for x in cand_all if cl_of[x] == "C1.cellular_update"),
        "registered": sorted(x for x in reg_all if cl_of[x] == "C1.cellular_update"),
        "status_record": {x: [L[x]["cluster_part"], L[x]["status"], L[x].get("stage")] for x in ev_of if cl_of[x] == "C1.cellular_update"},
        "registration_record_R2_B_lost": reg["evaluations"]["R2"]["parts"]["B"]["clusters_that_had_a_candidate_and_lost_every_lineage_at_capacity_and_keep_their_part"],
    }

    # tiers of the lineages dropped before the survivor list (R-66)
    before = sorted(x for x in ev_of if x not in surv_all)
    named = [x for x in before if L[x].get("stage_detail") in ("final_checks", "fix_round_4_manifest", "lineage_module_table")]
    supers = [x for x in before if L[x].get("stage_detail") == "superseded"]
    none_ = [x for x in before if L[x].get("stage_detail") == "no_single_committed_reason_found"]
    out["before_survivor_list"] = {"n": len(before), "named": len(named), "superseded": len(supers), "none": len(none_),
                                   "other": sorted(set(before) - set(named) - set(supers) - set(none_))}
    srcs = Sources(root)
    rng = random.Random(a.sample_seed)
    samp_n = sorted(rng.sample(named, 40))
    samp_s = sorted(rng.sample(supers, 20))
    out["sample_seed"] = a.sample_seed
    out["sample_named_40"] = [srcs.check(x, L[x]) for x in samp_n]
    out["sample_superseded_20"] = [srcs.check(x, L[x]) for x in samp_s]
    all_checks = [srcs.check(x, L[x]) for x in named + supers]
    out["all_named_and_superseded_verdicts"] = dict(Counter(r["verdict"] for r in all_checks))
    out["all_named_and_superseded_not_found"] = [r for r in all_checks if r["verdict"] != "FOUND"]
    out["none_tier_sentence_exact"] = all(L[x]["reason"] == NOREASON and L[x].get("reason_statements") == [] for x in none_)
    out["none_tier_mentioned_in_named_sources"] = {x: m for x in none_ if (m := srcs.mentions(x))}
    out["superseded_tier_mentioned_in_named_sources"] = {x: m for x in supers if (m := srcs.mentions(x))}
    out["truncated_reasons"] = sorted(x for x in named + supers if L[x]["reason"].split(" [")[0].endswith("..."))
    out["named_reason_is_not_a_reason"] = sorted(
        x for x in named if "no reason text in the file" in L[x]["reason"] or "states no figure" in L[x]["reason"]
    )

    # ---------------------------------------------------------------- item 3: G-gen's record
    def walk(o, path=""):
        if isinstance(o, dict):
            if isinstance(o.get("path"), str) and isinstance(o.get("sha256"), str):
                yield path, o["path"], o["sha256"]
            for k, v in o.items():
                if isinstance(v, str) and re.fullmatch(r"[0-9a-f]{64}", v) and "/" in k:
                    yield f"{path}/{k}", k, v
                else:
                    yield from walk(v, f"{path}/{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                yield from walk(v, f"{path}[{i}]")

    ok, bad, nofile = [], [], []
    for name, rec in (("g_gen_record", gg), ("registration_record", reg), ("status_record", st)):
        for where, pth, h in walk(rec):
            on_spec = pth.endswith("(claude/m0-spec)")
            f = (spec_root if on_spec else root) / pth.replace(" (claude/m0-spec)", "")
            if f.is_file():
                (ok if sha(f) == h else bad).append([name + where, pth, h, sha(f)])
            else:
                nofile.append([name + where, pth])
        for k, v in rec.get("inputs_sha256", {}).items():
            f = root / k
            if not f.is_file():
                nofile.append([name + "/inputs_sha256", k])
            elif sha(f) != v:
                bad.append([name + "/inputs_sha256", k, v, sha(f)])
            else:
                ok.append([name + "/inputs_sha256", k, v, v])
    out["hash_checks"] = {"n_ok": len(ok), "bad": bad, "no_file": nofile, "distinct_files_ok": len({r[1] for r in ok})}
    out["chain"] = {
        "registration->status_v1": reg["status_record_v1"]["sha256"] == sha(root / f"{MAN}/status_record_v1.json"),
        "ggen->registration": gg["stage_6_items"]["registration_record"]["sha256"] == sha(root / f"{MAN}/registration_record.json"),
        "ggen->status_v1": gg["stage_6_items"]["status_record_first_version"]["sha256"] == sha(root / f"{MAN}/status_record_v1.json"),
        "ggen->domain_list": gg["domain_list"]["file"]["sha256"] == sha(root / f"{MAN}/domain_list.json"),
        "script_sha_build_records": [reg["script_sha256"], st["script_sha256"], gg["script_sha256"],
                                     sha(root / "studies/m0/registration/build_records.py")],
    }
    sums = {}
    for line in (root / f"{FR}/run/pooled/SHA256SUMS_pooled.txt").read_text().splitlines():
        if line.strip():
            h, n = line.split(maxsplit=1)
            sums[n.strip().lstrip("*").split("/")[-1]] = h
    raw = gzip.decompress((root / f"{FR}/run/pooled/pooled_table.json.gz").read_bytes())
    out["pooled"] = {
        "sums": sums,
        "gz_decompresses_to": hashlib.sha256(raw).hexdigest(),
        "gz_matches_sums": hashlib.sha256(raw).hexdigest() == sums.get("pooled_table.json"),
        "committed_files_match_sums": {n: (root / f"{FR}/run/pooled/{n}").is_file() and sha(root / f"{FR}/run/pooled/{n}") == h
                                       for n, h in sums.items() if n != "pooled_table.json"},
        "ggen_every_hash_in_sums_equal": gg["stage_6_items"]["pooled_table"]["every_hash_in_the_sums_file"] == sums,
    }
    hrs = {}
    for i in (1, 2, 3):
        rel = f"{FR}/run/hashes_seed{i}.json"
        d = load(rel)
        hexes = []

        def rec_(o, k0=""):
            if isinstance(o, dict):
                for k, v in o.items():
                    if isinstance(v, str) and re.fullmatch(r"[0-9a-f]{64}", v):
                        hexes.append(k)
                    rec_(v, k)
            elif isinstance(o, list):
                for v in o:
                    rec_(v, k0)

        rec_(d)
        tracked = __import__("subprocess").run(["git", "-C", str(root), "ls-files", "--error-unmatch", rel],
                                               capture_output=True).returncode == 0
        hrs[rel] = {"sha256": sha(root / rel), "tracked_in_git": tracked, "hex64_by_key": dict(Counter(hexes)),
                    "top_keys": sorted(d) if isinstance(d, dict) else None}
    out["run_hash_records"] = hrs
    out["run_hash_records_in_ggen"] = [[x["path"], x["sha256"] == sha(root / x["path"]), x["n_output_files_hashed"]]
                                       for x in gg["stage_6_items"]["hash_of_every_output_file_of_the_run_as_taken_when_its_unit_ended"]["hash_records"]]
    s6 = gg["stage_6_items"]
    gi = []
    for e in EVALS:
        if s6["N_e"][e] != N_e[e]:
            gi.append(f"N_e {e}")
        cc = s6["counts_of_each_part_in_clusters_and_in_groups"][e]
        if any(cc["candidate_clusters_and_groups_as_the_partition_record_carries_them"][k] != v for k, v in cand_counts[e].items()):
            gi.append(f"candidate counts {e}")
        for p in PARTS:
            vv = s6["G_per_part_with_the_strictest_counts_beside_it"]["values"][f"{e}.{p}"]
            if (vv["G"], vv["strictest_G"], vv["direct_pairs_count_information_only_not_the_strictest_count"]) != (G[e][p], strict[e][p], direct[e][p]):
                gi.append(f"G/strictest {e}.{p}")
            if sorted(s6["registered_lineages"]["per_evaluation_and_part"][e][p]) != sorted(x for v in registered[e][p].values() for x in v):
                gi.append(f"registered {e}.{p}")
            if cc["registered_clusters_and_groups"][p] != {"clusters": G[e][p], "groups": reg_groups[e][p]}:
                gi.append(f"registered counts {e}.{p}")
            if gg["section_9_item_5_reading_per_part"][f"{e}.{p}"] != reg["section_9_item_5_reading_per_part"][f"{e}.{p}"]:
                gi.append(f"s9 {e}.{p}")
    if sorted(s6["lineages_dropped_by_the_fresh_run"]["lineages"]) != sorted(drop_ids):
        gi.append("dropped list")
    if sorted(s6["lineages_dropped_by_the_fresh_run"]["the_seven_that_come_from_the_rules_wording"]["ids"]) != sorted(seven):
        gi.append("seven")
    if s6["candidates"]["counts"] != out["candidates_per_eval"] or s6["candidates"]["total"] != len(cand_all):
        gi.append("candidates")
    if s6["survivor_list_of_record"]["lineages"] != {e: len(surv[e]) for e in EVALS} or s6["survivor_list_of_record"]["total"] != len(surv_all):
        gi.append("survivor list")
    m6 = s6["map_of_record"]
    if (m6["clusters"], m6["links"], m6["borderline_pairs"], m6["written_lineages"], m6["groups"]) != (
            len(mp["clusters"]), len(mp["links"]), len(mp["borderline_pairs"]), len(mp["lineages"]), len(mp["groups"])):
        gi.append("map counts")
    if s6["partition"]["derived_integers"] != part_rec["derived_integers"] or s6["partition"]["seed"] != 400004:
        gi.append("partition integers/seed")
    if s6["record_of_the_stage_2_conditions"]["lineages_read"] != len(s2_rows):
        gi.append("stage-2 lineages read")
    out["ggen_value_differences"] = gi
    out["ggen_departures"] = sorted(gg["departures"])
    exp_dep = []
    for e in EVALS:
        for p in PARTS:
            if len(families[e][p]) < 12:
                exp_dep.append([e, p, len(families[e][p])])
        un = set(families[e]["A"]) | set(families[e]["B"])
        if len(un) < 12:
            exp_dep.append([e, "both", len(un)])
    got_dep = [[d["evaluation"], "both" if d["part"].startswith("both") else d["part"], d["n_families"]]
               for d in gg["departures"]["family_count_fewer_than_12_is_a_departure_from_ADR_0033_line_268"]["entries"]]
    out["family_departure_entries"] = {"equal": sorted(got_dep) == sorted(exp_dep), "expected": exp_dep}
    out["lead_rulings_hashes"] = {x["path"]: x["sha256"] == sha(root / x["path"]) for x in gg["lead_rulings"]}

    # domain list
    adr = (root / "docs/decisions/ADR-0033-m0-reference-models-and-evaluation-harness.md").read_text()
    sec = adr.split("### 6.8 Domain list as proposed", 1)[1].split("\n### ", 1)[0].split("\n## ", 1)[0]
    rows = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in sec.splitlines()
            if ln.startswith("| ") and not ln.startswith("| Domain")]
    dl = load(f"{MAN}/domain_list.json")
    out["domain"] = {
        "adr_rows": rows,
        "rows_equal": rows == [[d["domain"], d["gate_candidates_as_written"], d["printed_beside"]] for d in dl["domains"]],
        "ggen_copy_equal_file": {k: v for k, v in gg["domain_list"].items() if k not in ("file", "checked_against_section_6_8_of_the_file_at")} == dl,
        "words13_quote": "> Yes, the five" in (root / WORDS / "HUMAN_LEAD_WORDS_13.md").read_text(),
        "code_writing_not_measured_in_adr": "Code writing is NOT MEASURED in M0" in sec,
        "private_public_split_consistent": all(
            sorted(d["private"] + d["public"]) == sorted(d["gate_candidates"]) for d in dl["domains"]),
        "adr0033_same_bytes_on_spec_worktree": sha(spec_root / "docs/decisions/ADR-0033-m0-reference-models-and-evaluation-harness.md")
        == sha(root / "docs/decisions/ADR-0033-m0-reference-models-and-evaluation-harness.md"),
    }
    Path(a.out).write_text(json.dumps(out, indent=1, sort_keys=True, default=str) + "\n")
    print("done")
    return 0


class Sources:
    """Reads the committed files a reason cites and says whether the reason is stated there."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.cache: dict = {}

    def js(self, rel):
        if rel not in self.cache:
            self.cache[rel] = json.loads((self.root / rel).read_text())
        return self.cache[rel]

    def pytab(self, rel, name):
        key = (rel, name)
        if key not in self.cache:
            val = None
            for node in ast.parse((self.root / rel).read_text()).body:
                if isinstance(node, ast.Assign):
                    tg, v = [t.id for t in node.targets if isinstance(t, ast.Name)], node.value
                elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                    tg, v = [node.target.id], node.value
                else:
                    continue
                if name in tg and v is not None:
                    try:
                        val = ast.literal_eval(v)
                    except Exception:
                        val = ("UNPARSEABLE", ast.unparse(v)[:200])
            self.cache[key] = val
        return self.cache[key]

    @staticmethod
    def strings(o):
        if isinstance(o, str):
            yield o
        elif isinstance(o, dict):
            for k, v in o.items():
                yield str(k)
                yield from Sources.strings(v)
        elif isinstance(o, (list, tuple)):
            for v in o:
                yield from Sources.strings(v)

    @staticmethod
    def entries(o, lid):
        hits = []

        def rec(x):
            if isinstance(x, dict):
                for k, v in x.items():
                    if k == lid:
                        hits.append(v)
                    rec(v)
                if any(v == lid for v in x.values() if isinstance(v, str)):
                    hits.append(x)
            elif isinstance(x, list):
                for v in x:
                    rec(v)

        rec(o)
        return hits

    def mentions(self, lid):
        m = []
        t = (self.root / "docs/reviews/m0-lineage-decision-2026-11-25/cross_evaluation_map/drops_after_final_checks.txt").read_text()
        if re.search(r"(?<![\w.])" + re.escape(lid) + r"(?!\w)", t):
            m.append("drops_after_final_checks.txt")
        for f in ("c1", "m1", "r1", "r2"):
            rel = f"studies/m0/manifests/{f}_fix4_survivors.json"
            if any(s == lid for s in self.strings(self.js(rel))):
                m.append(rel)
        for py in sorted((self.root / "studies/m0").glob("lineages_*.py")):
            for node in ast.parse(py.read_text()).body:
                if isinstance(node, ast.Assign):
                    names = [t.id for t in node.targets if isinstance(t, ast.Name)]
                    if any(n.startswith(("NOT_REGISTERED", "DROPPED")) for n in names):
                        try:
                            val = ast.literal_eval(node.value)
                        except Exception:
                            continue
                        if isinstance(val, dict) and lid in val:
                            m.append(f"{py.name}:{names[0]}")
        return m

    def check(self, lid, rec):
        sts = rec.get("reason_statements", [])
        res = {"lineage": lid, "stage_detail": rec.get("stage_detail"), "reason": rec.get("reason", "")[:220], "statements": []}
        ok_all = bool(sts)
        first = bool(sts) and rec.get("reason", "").startswith(sts[0]["text"])
        for s in sts:
            src, text = s["source"], s["text"]
            found, how = False, ""
            core = text[:-3] if text.endswith("...") else text
            if src.endswith("drops_after_final_checks.txt"):
                t = (self.root / src).read_text()
                found = bool(re.search(r"(?<![\w.])" + re.escape(lid) + r"(?!\w)", t)) and "drops under LEAD_RULINGS_7 (R-38), 2026-11-25" in t
                how = "id in the file; header as quoted"
            elif ".json:" in src:
                rel, field = src.split(":", 1)
                o = self.js(rel)
                if text.startswith("superseded by "):
                    newer = text[len("superseded by "):].strip()
                    found = any(lid in list(self.strings(sv)) for sv in self.entries(o, newer)) or any(
                        sv == newer for sv in self.entries(o, lid) if isinstance(sv, str))
                    how = f"'{field}' ties {lid} and {newer}"
                elif text.startswith("listed under excluded_everywhere"):
                    found = lid in o.get("excluded_everywhere", [])
                    how = "id in excluded_everywhere"
                else:
                    found = any(core in s_ for sv in self.entries(o, lid) for s_ in self.strings(sv))
                    how = "text in the lineage's entry" if found else "text NOT in the lineage's entry"
            elif ".py:" in src:
                rel, name = src.split(":", 1)
                tab = self.pytab(rel, name)
                val = tab.get(lid) if isinstance(tab, dict) else None
                if text.startswith("superseded by "):
                    newer = text[len("superseded by "):].strip()
                    found = val == newer or (isinstance(val, (list, tuple)) and newer in val)
                else:
                    found = val is not None and any(core in s_ for s_ in self.strings(val))
                how = f"{name}[{lid}] present: {val is not None}"
            res["statements"].append({"source": src, "found": found, "how": how, "text": text[:200]})
            ok_all = ok_all and found
        res["first_statement_is_the_reason"] = first
        res["verdict"] = "FOUND" if ok_all and first else "NOT FOUND"
        return res


if __name__ == "__main__":
    raise SystemExit(main())
