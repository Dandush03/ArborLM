"""Root scientific audit: standard-library recomputation, no ArborLM imports.

Run from the repository root after all 36 P3 cells complete. This writes derived
summaries only; raw experiments are read-only. All thresholds come from ADR-0008.
"""

import csv
import json
import math
import statistics as stats
from pathlib import Path

ROOT = Path("results/p3-lt-2026-11-12")
STEPS = (256, 512, 1024)


def read(path):
    return json.loads(path.read_text())


def distribution(values):
    return dict(
        mean=stats.mean(values),
        sample_sd=stats.stdev(values),
        minimum=min(values),
        maximum=max(values),
        positive=sum(x > 0 for x in values),
        zero=sum(x == 0 for x in values),
        negative=sum(x < 0 for x in values),
    )


def factor_summary(rows, metric):
    grand = stats.mean(row[metric] for row in rows)
    means = {
        factor: {
            str(level): stats.mean(row[metric] for row in rows if row[factor] == level)
            for level in sorted({row[factor] for row in rows})
        }
        for factor in ("backbone", "memory", "order")
    }
    residuals = [
        row[metric] - sum(means[f][str(row[f])] for f in means) + 2 * grand for row in rows
    ]
    return dict(
        grand_mean=grand,
        marginal_means=means,
        marginal_ranges={f: max(v.values()) - min(v.values()) for f, v in means.items()},
        interaction_rms=math.sqrt(stats.mean(x * x for x in residuals)),
    )


records = []
identities = {
    key: set()
    for key in (
        "source_sha256",
        "spec_sha256",
        "config_sha256",
        "dataset_manifest_sha256",
        "lock_sha256",
    )
}
events_count = dict(training=0, references=0, interventions=0, parent_integrity=0)
for b in (101, 102, 103):
    for o in (301, 302, 303):
        for tag in ("control", "m201", "m202", "m203"):
            folder = ROOT / f"b{b}-o{o}-{tag}"
            result, manifest, terminal = (
                read(folder / name) for name in ("result.json", "manifest.json", "terminal.json")
            )
            assert result["outcome"] == terminal["status"] == "completed"
            assert result["additional_training_targets"] == 393216
            assert result["lifetime_training_targets"] == 524288
            assert result["original_parent_checkpoint_unchanged"]
            for key in identities:
                identities[key].add(manifest[key])
            events = [
                json.loads(line) for line in (folder / "metrics.jsonl").read_text().splitlines()
            ]
            training = [e for e in events if e["event"] == "train_step"]
            assert [e["global_step"] for e in training] == list(range(257, 1025))
            for e in training:
                s = e["global_step"]
                assert e["order_offset_for_update"] == ((s - 1) * 8) % 2048
                assert e["absolute_order_cursor"] == s * 8
                assert e["next_cyclic_order_cursor"] == (s * 8) % 2048
                assert e["cumulative_targets"] == s * 512
                assert e["additional_targets"] == (s - 256) * 512
            ref = [e for e in events if e["event"] == "duration_reference"]
            inter = [e for e in events if e["event"] == "duration_intervention"]
            parent = [e for e in events if e["event"] == "parent_restore_integrity"]
            assert [e["global_step"] for e in ref] == list(STEPS)
            assert len(inter) == (3 if tag == "control" else 12)
            assert len(parent) == 1 and parent[0]["bitwise_passed"]
            assert parent[0]["panel"] == "P2_integrity_only"
            assert parent[0]["excluded_from_scientific_analysis"]
            assert all(
                e["target_tokens"] == 32768 and e["training_target_tokens"] == 0
                for e in ref + inter + parent
            )
            assert all(e["panel"] == "P3_scientific" for e in ref + inter)
            events_count["training"] += len(training)
            events_count["references"] += len(ref)
            events_count["interventions"] += len(inter)
            events_count["parent_integrity"] += len(parent)
            for s in STEPS:
                block = result["durations"][str(s)]
                nll = block["reference"]["nll"]
                conditions = block["interventions"]
                assert conditions["enabled"]["nll"] == nll
                assert all(v["checkpoint_unchanged"] for v in conditions.values())
                assert conditions["enabled"]["invariance_passed"]
                if tag != "control":
                    assert conditions["joint_within_branch"]["invariance_passed"]
                    assert abs(conditions["joint_within_branch"]["nll"] - nll) <= 1e-6
                assert nll == next(e["nll"] for e in ref if e["global_step"] == s)
                for condition, measured in conditions.items():
                    raw = next(
                        e for e in inter if e["global_step"] == s and e["condition"] == condition
                    )
                    assert measured["nll"] == raw["nll"]
                records.append(
                    dict(
                        backbone=b,
                        memory=None if tag == "control" else int(tag[1:]),
                        order=o,
                        kind=tag,
                        step=s,
                        nll=nll,
                        disabled_nll=conditions["disabled"]["nll"] if tag != "control" else None,
                        shuffled_nll=conditions["values_permuted"]["nll"]
                        if tag != "control"
                        else None,
                        D=conditions["disabled"]["nll"] - nll if tag != "control" else None,
                        P=conditions["values_permuted"]["nll"] - nll if tag != "control" else None,
                    )
                )

assert all(len(v) == 1 for v in identities.values())
assert events_count == dict(training=27648, references=108, interventions=351, parent_integrity=36)
controls = {
    (r["backbone"], r["order"], r["step"]): r["nll"] for r in records if r["kind"] == "control"
}
learned = [r for r in records if r["kind"] != "control"]
for r in learned:
    r["G"] = controls[r["backbone"], r["order"], r["step"]] - r["nll"]
    r["S"] = controls[r["backbone"], r["order"], r["step"]] - r["disabled_nll"]
    assert abs(r["G"] - r["D"] - r["S"]) <= 1e-12

by_duration = {}
for s in STEPS:
    rows = [r for r in learned if r["step"] == s]
    by_duration[str(s)] = {
        "learned": {k: distribution([r[k] for r in rows]) for k in ("nll", "D", "P", "G", "S")},
        "controls": distribution([v for (b, o, t), v in controls.items() if t == s]),
        "both_D_P_positive": sum(r["D"] > 0 and r["P"] > 0 for r in rows),
    }
base = {(r["backbone"], r["memory"], r["order"]): r for r in learned if r["step"] == 256}
control_changes_from_256 = {}
for s in (512, 1024):
    rows = []
    for (b, o, t), end_nll in controls.items():
        if t != s:
            continue
        baseline_nll = controls[b, o, 256]
        rows.append(
            dict(
                backbone=b,
                order=o,
                baseline_nll=baseline_nll,
                end_nll=end_nll,
                delta_nll=end_nll - baseline_nll,
            )
        )
    summary = distribution([r["delta_nll"] for r in rows])
    assert len(rows) == 9 and summary["negative"] == 9
    control_changes_from_256[str(s)] = dict(summary=summary, rows=rows)

changes = {}
for s in (512, 1024):
    rows = []
    for r in learned:
        if r["step"] != s:
            continue
        first = base[r["backbone"], r["memory"], r["order"]]
        rows.append({**r, **{k: r[k] - first[k] for k in ("nll", "D", "P", "G", "S")}})
    changes[str(s)] = dict(
        summary={k: distribution([r[k] for r in rows]) for k in ("nll", "D", "P", "G", "S")},
        both_delta_positive=sum(r["D"] > 0 and r["P"] > 0 for r in rows),
        factor_decomposition={k: factor_summary(rows, k) for k in ("D", "G")},
        rows=rows,
    )

end = by_duration["1024"]
delta = changes["1024"]
flags = dict(
    duration_increases_dependence=delta["summary"]["D"]["mean"] >= 0.005
    and delta["summary"]["P"]["mean"] >= 0.005
    and delta["both_delta_positive"] >= 22,
    endpoint_dependence=end["learned"]["D"]["mean"] >= 0.005
    and end["learned"]["P"]["mean"] >= 0.005
    and end["both_D_P_positive"] >= 22,
    endpoint_quality_guard=end["learned"]["nll"]["mean"]
    < by_duration["256"]["learned"]["nll"]["mean"]
    and end["learned"]["G"]["mean"] >= 0,
)
suite = read(ROOT / "suite/result.json")
assert suite["outcome"] == "completed"
assert suite["total_completed_additional_training_targets"] == 14155776
assert suite["total_completed_lifetime_training_targets"] == 18874368
produced = suite["descriptive_analysis"]
assert flags == produced["flags"]
for s in STEPS:
    for k in ("nll", "D", "P", "G", "S"):
        metric = "enabled" if k == "nll" else k
        assert (
            by_duration[str(s)]["learned"][k]
            == produced["by_duration"][str(s)]["learned_paired_metrics"][metric]
        )
    assert by_duration[str(s)]["controls"] == produced["by_duration"][str(s)]["unique_control_nll"]
for s in (512, 1024):
    assert (
        control_changes_from_256[str(s)]["summary"]
        == produced["changes_from_256"][str(s)]["unique_control"]
    )
    for k in ("nll", "D", "P", "G", "S"):
        metric = "enabled" if k == "nll" else k
        expected = produced["changes_from_256"][str(s)]["learned"][metric]
        actual = changes[str(s)]["summary"][k]
        for field in actual:
            assert math.isclose(actual[field], expected[field], abs_tol=1e-14, rel_tol=0)
    for metric in ("D", "G"):
        actual = changes[str(s)]["factor_decomposition"][metric]
        expected = produced["changes_from_256"][str(s)]["factor_decomposition"][metric]
        assert math.isclose(
            actual["interaction_rms"], expected["interaction_rms"], abs_tol=1e-14, rel_tol=0
        )
        for factor in ("backbone", "memory", "order"):
            assert math.isclose(
                actual["marginal_ranges"][factor],
                expected["marginal_ranges"][factor],
                abs_tol=1e-14,
                rel_tol=0,
            )

report = dict(
    method="Independent standard-library recomputation from compact raw events; "
    "no implementation analysis imports",
    event_counts=events_count,
    identities={k: next(iter(v)) for k, v in identities.items()},
    by_duration=by_duration,
    changes_from_256=changes,
    control_changes_from_256=control_changes_from_256,
    flags=flags,
    all_three_flags=all(flags.values()),
    no_arithmetic_discrepancy=True,
)
(ROOT / "root-analysis.json").write_text(json.dumps(report, indent=2) + "\n")
for r in records:
    b, o = r["backbone"], r["order"]
    baseline_nll = controls[b, o, 256] if r["kind"] == "control" else base[b, r["memory"], o]["nll"]
    r["delta_nll_from_256"] = r["nll"] - baseline_nll
fields = list(dict.fromkeys(k for r in records for k in r))
with (ROOT / "per-duration.csv").open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
print(
    json.dumps(
        {
            "by_duration": by_duration,
            "primary_changes": delta["summary"],
            "control_changes_from_256": control_changes_from_256,
            "flags": flags,
            "event_counts": events_count,
        },
        indent=2,
    )
)
