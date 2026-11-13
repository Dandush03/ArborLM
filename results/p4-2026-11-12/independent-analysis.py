"""Independent ADR-0009 arithmetic/event audit; no ArborLM imports.

Run from repository root only after all registered cells finish. Reads raw
records and writes derived tables, never model/data artifacts.
"""

import csv
import json
import math
import statistics as stats
import struct
from pathlib import Path

ROOT = Path("results/p4-2026-11-12")


def read(path):
    return json.loads(path.read_text())


def equal(a, b):
    return struct.pack("!d", a) == struct.pack("!d", b)


def dist(values):
    return dict(
        mean=stats.mean(values),
        sample_sd=stats.stdev(values),
        minimum=min(values),
        maximum=max(values),
        positive=sum(x > 0 for x in values),
        negative=sum(x < 0 for x in values),
        zero=sum(x == 0 for x in values),
    )


records = []
identities = {
    k: set()
    for k in (
        "source_sha256",
        "spec_sha256",
        "config_sha256",
        "lock_sha256",
        "dataset_manifest_sha256",
    )
}
events_count = dict(train=0, initial=0, final=0, interventions=0, old_panel=0, checkpoints=0)
for b in (101, 102, 103):
    for o in (301, 302, 303):
        for seed, variant in [(0, "baseline")] + [
            (s, v) for s in (401, 402, 403) for v in ("memory", "dense")
        ]:
            tag = variant if variant == "baseline" else f"{variant}-s{seed}"
            folder = ROOT / f"b{b}-o{o}-{tag}"
            r, m, t = (
                read(folder / name) for name in ("result.json", "manifest.json", "terminal.json")
            )
            assert r["outcome"] == t["status"] == "completed"
            assert r["cell"] == dict(backbone=b, order=o, seed=seed, variant=variant)
            nsteps = 0 if variant == "baseline" else 512
            assert r["completed_steps"] == nsteps
            assert r["additional_training_targets"] == nsteps * 512
            assert r["parent_checkpoint_unchanged"]
            expected_snapshots = (
                ["checkpoint-0"]
                if not nsteps
                else ["checkpoint-0", "checkpoint-256", "checkpoint-512"]
            )
            assert set(r["checkpoint_state_sha256"]) == set(expected_snapshots)
            for name in expected_snapshots:
                assert (
                    read(folder / name / "index.json")["state_sha256"]
                    == r["checkpoint_state_sha256"][name]
                )
            events_count["checkpoints"] += len(expected_snapshots)
            for k in identities:
                identities[k].add(m[k])
            assert m["model"]["parameters_frozen"] == 27392
            assert m["model"]["parameters_trainable"] == (198401 if nsteps else 0)
            assert m["model"]["parameters_stored"] == (225793 if nsteps else 27392)
            events = [
                json.loads(line) for line in (folder / "metrics.jsonl").read_text().splitlines()
            ]
            train = [e for e in events if e["event"] == "train_step"]
            initial = [e for e in events if e["event"] == "initial_evaluation"]
            final = [e for e in events if e["event"] == "final_evaluation"]
            interventions = [e for e in events if e["event"] == "intervention_evaluation"]
            old = [e for e in events if e["event"] == "parent_restore_integrity"]
            assert [e["additional_step"] for e in train] == list(range(1, nsteps + 1))
            for e in train:
                s = e["additional_step"]
                assert e["order_offset_for_update"] == ((s - 1) * 8) % 2048
                assert e["absolute_order_cursor"] == s * 8
                assert e["next_cyclic_order_cursor"] == s * 8 % 2048
                assert e["additional_targets"] == s * 512
                assert math.isfinite(e["pre_update_loss"]) and math.isfinite(
                    e["pre_clip_gradient_norm"]
                )
            assert len(initial) == int(nsteps > 0) and len(final) == 1
            assert len(old) == int(nsteps == 0)
            if old:
                assert old[0]["panel"] == "P3_integrity_only" and old[0]["bitwise_passed"]
                assert old[0]["excluded_from_scientific_analysis"]
                assert equal(old[0]["nll"], old[0]["recorded_parent_nll"])
            for e in initial + final + interventions + old:
                assert e["target_tokens"] == 32768 and e["training_target_tokens"] == 0
                assert math.isfinite(e["nll"])
            assert all(e["panel"] == "P4_scientific" for e in initial + final + interventions)
            assert final[0]["additional_step"] == nsteps and equal(
                final[0]["nll"], r["final"]["nll"]
            )
            if initial:
                assert initial[0]["additional_step"] == 0 and equal(
                    initial[0]["nll"], r["initial"]["nll"]
                )
            expected_tags = (
                {"enabled"}
                if not nsteps
                else {"enabled", "disabled"}
                if variant == "dense"
                else {"enabled", "disabled", "values_permuted", "joint_within_branch"}
            )
            assert set(r["interventions"]) == expected_tags
            assert len(interventions) == len(expected_tags)
            for tag, block in r["interventions"].items():
                event = next(e for e in interventions if e["condition"] == tag)
                assert equal(event["nll"], block["nll"])
                assert block["checkpoint_unchanged"]
                if tag != "values_permuted":
                    assert block["invariance_passed"]
                if tag == "joint_within_branch":
                    assert abs(block["nll"] - r["final"]["nll"]) <= 1e-6
            assert equal(r["interventions"]["enabled"]["nll"], r["final"]["nll"])
            for k, values in [
                ("train", train),
                ("initial", initial),
                ("final", final),
                ("interventions", interventions),
                ("old_panel", old),
            ]:
                events_count[k] += len(values)
            records.append(
                dict(
                    backbone=b,
                    order=o,
                    seed=seed,
                    variant=variant,
                    initial_nll=r["initial"]["nll"] if initial else None,
                    final_nll=r["final"]["nll"],
                    final_minus_initial=r["final"]["nll"] - r["initial"]["nll"]
                    if initial
                    else None,
                    disabled_nll=r["interventions"].get("disabled", {}).get("nll"),
                    shuffled_nll=r["interventions"].get("values_permuted", {}).get("nll"),
                    frozen_backbone_sha256=r["backbone_sha256"],
                    wall_seconds=t["process_wall_seconds"],
                    rss_bytes=t["peak_process_tree_rss_bytes"],
                )
            )

assert events_count == dict(
    train=27648, initial=54, final=63, interventions=171, old_panel=9, checkpoints=171
)
assert all(len(v) == 1 for v in identities.values())
baselines = {(r["backbone"], r["order"]): r for r in records if r["variant"] == "baseline"}
models = {
    (r["backbone"], r["order"], r["seed"], r["variant"]): r
    for r in records
    if r["variant"] != "baseline"
}
paired = []
for b, o in baselines:
    base = baselines[b, o]
    for s in (401, 402, 403):
        h = models[b, o, s, "memory"]
        a = models[b, o, s, "dense"]
        assert (
            h["frozen_backbone_sha256"]
            == a["frozen_backbone_sha256"]
            == base["frozen_backbone_sha256"]
        )
        assert equal(h["disabled_nll"], base["final_nll"]) and equal(
            a["disabled_nll"], base["final_nll"]
        )
        c = base["final_nll"] - h["final_nll"]
        d = h["disabled_nll"] - h["final_nll"]
        p = h["shuffled_nll"] - h["final_nll"]
        cd = base["final_nll"] - a["final_nll"]
        q = a["final_nll"] - h["final_nll"]
        assert c == d and abs(q - (c - cd)) <= 1e-12
        paired.append(dict(backbone=b, order=o, seed=s, C=c, D=d, P=p, C_dense=cd, Q=q))
effects = ("C", "D", "P", "C_dense", "Q")
summary = {k: dist([r[k] for r in paired]) for k in effects}
parents = [
    dict(
        backbone=b,
        order=o,
        means={
            k: stats.mean(r[k] for r in paired if r["backbone"] == b and r["order"] == o)
            for k in effects
        },
    )
    for b, o in baselines
]
counts = dict(
    C_positive_cells=sum(r["C"] > 0 for r in paired),
    C_and_P_positive_cells=sum(r["C"] > 0 and r["P"] > 0 for r in paired),
    Q_tolerance_cells=sum(r["Q"] >= -0.005 for r in paired),
    Q_positive_cells=sum(r["Q"] > 0 for r in paired),
    C_positive_parents=sum(r["means"]["C"] > 0 for r in parents),
    P_positive_parents=sum(r["means"]["P"] > 0 for r in parents),
    Q_tolerance_parents=sum(r["means"]["Q"] >= -0.005 for r in parents),
    Q_positive_parents=sum(r["means"]["Q"] > 0 for r in parents),
)
memory = [r for r in records if r["variant"] == "memory"]
dense = [r for r in records if r["variant"] == "dense"]
flags = dict(
    added_predictive_capacity=summary["C"]["mean"] >= 0.005
    and counts["C_positive_cells"] >= 22
    and counts["C_positive_parents"] >= 8
    and stats.mean(r["final_nll"] for r in memory) < stats.mean(r["initial_nll"] for r in memory),
    useful_slot_association_dependence=summary["P"]["mean"] >= 0.005
    and counts["C_and_P_positive_cells"] >= 22
    and counts["P_positive_parents"] >= 8,
    within_dense_quality_tolerance=summary["Q"]["mean"] >= -0.005
    and counts["Q_tolerance_cells"] >= 22
    and counts["Q_tolerance_parents"] >= 8,
    secondary_memory_advantage=summary["Q"]["mean"] >= 0.005
    and counts["Q_positive_cells"] >= 22
    and counts["Q_positive_parents"] >= 8,
)
composite = all(flags[k] for k in list(flags)[:3])
marginals = {
    f: {
        str(level): {k: stats.mean(r[k] for r in paired if r[f] == level) for k in effects}
        for level in sorted({r[f] for r in paired})
    }
    for f in ("backbone", "order", "seed")
}
suite = read(ROOT / "suite/result.json")
assert suite["outcome"] == "completed"
assert suite["counts"] == dict(
    additional_training_targets=14155776,
    snapshots=171,
    scientific_evaluations=288,
    integrity_evaluations=9,
)
produced = suite["descriptive_analysis"]
assert flags == produced["flags"] and composite == produced["composite_success"]
assert counts == produced["counts"] and summary == produced["summary"]
assert marginals == produced["marginal_means"]
assert parents == [{k: v for k, v in r.items() if k != "seeds"} for r in produced["per_parent"]]
baseline_summary = dist([r["final_nll"] for r in baselines.values()])
assert baseline_summary == produced["baseline_nll"]
nll = {}
for name, rows in [("memory", memory), ("dense", dense)]:
    nll[name] = {
        tag: dist([r[field] for r in rows])
        for tag, field in [
            ("initial", "initial_nll"),
            ("final", "final_nll"),
            ("final_minus_initial", "final_minus_initial"),
        ]
    }
    assert nll[name] == produced[f"{name}_nll"]
report = dict(
    method="Independent standard-library recomputation from raw events, "
    "no implementation analysis imports",
    event_counts=events_count,
    identities={k: next(iter(v)) for k, v in identities.items()},
    baseline_nll=baseline_summary,
    nll=nll,
    paired=paired,
    summary=summary,
    per_parent=parents,
    marginal_means=marginals,
    counts=counts,
    flags=flags,
    composite_success=composite,
    no_arithmetic_discrepancy=True,
)
(ROOT / "root-analysis.json").write_text(json.dumps(report, indent=2) + "\n")
for filename, rows in [("per-run.csv", records), ("paired-effects.csv", paired)]:
    with (ROOT / filename).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
print(
    json.dumps(
        {
            k: report[k]
            for k in (
                "event_counts",
                "baseline_nll",
                "nll",
                "summary",
                "counts",
                "flags",
                "composite_success",
            )
        },
        indent=2,
    )
)
