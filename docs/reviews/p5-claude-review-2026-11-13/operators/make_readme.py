"""Assemble README.md tables from operator_profile.json and p5_retained_timing_summary.json."""
import json
from pathlib import Path

H = Path(__file__).parent
d = json.loads((H / "operator_profile.json").read_text())
p5 = {(c["variant"], c["scope"], c["batch_size"]): c for c in json.loads((H / "p5_retained_timing_summary.json").read_text())["cells"]}
us = lambda x: f"{x/1e3:,.1f}"  # noqa: E731


def stage_table(n, v):
    r = d["runs"][n][v]
    out = ["| Stage | median us | p10-p90 us | share of stage-sum | bytes materialized (outputs only) | output shape / dtype |", "|---|---:|---|---:|---:|---|"]
    for s in r["stages"]:
        sh = "; ".join(f"{o['shape']} {o['dtype'].replace('torch.','')}" if "shape" in o else o["python_value"] for o in s["outputs"])
        out.append(f"| {s['stage']} | {us(s['median_ns'])} | {us(s['p10_ns'])}-{us(s['p90_ns'])} | {100*s['share_of_stage_sum']:.1f}% | {s['bytes_materialized']:,} | {sh} |")
    e = r["end_to_end"]
    out.append(f"| **stage-median sum** | **{us(r['stage_median_sum_ns'])}** | | 100% | {r['total_bytes_materialized_stage_outputs']:,} | |")
    out.append(f"| **end-to-end Memory.lookup** | **{us(e['median_ns'])}** | {us(e['p10_ns'])}-{us(e['p90_ns'])} | | | |")
    out.append(f"| stage sum / end-to-end | {r['stage_sum_over_end_to_end']:.3f} | | | | |")
    return "\n".join(out)


def group_table(n, v):
    r = d["runs"][n][v]
    g = {}
    for s in r["stages"]:
        key = s["group"]
        g.setdefault(key, [0, 0])
        g[key][0] += s["median_ns"]
        g[key][1] += s["bytes_materialized"]
    tot = r["stage_median_sum_ns"]
    rows = ["| Group | summed median us | share | bytes materialized |", "|---|---:|---:|---:|"]
    for k, (t, b) in sorted(g.items(), key=lambda kv: -kv[1][0]):
        rows.append(f"| {k} | {us(t)} | {100*t/tot:.1f}% | {b:,} |")
    return "\n".join(rows)


def e2e_table():
    rows = ["| N | variant | end-to-end median us | p10-p90 us | stage sum us | sum/e2e | bitwise equal |", "|---|---|---:|---|---:|---:|---|"]
    for n in ("N512", "N64"):
        for v in ("flat", "fixed_tree", "learned_tree"):
            r = d["runs"][n][v]; e = r["end_to_end"]
            rows.append(f"| {n[1:]} | {v} | {us(e['median_ns'])} | {us(e['p10_ns'])}-{us(e['p90_ns'])} | {us(r['stage_median_sum_ns'])} | {r['stage_sum_over_end_to_end']:.3f} | {r['bitwise_equal_to_Memory.lookup']} |")
    return "\n".join(rows)


def p5_table():
    rows = ["| workload | variant | P5 retained lookup_score_select: median across 27 workers of median_ns (us) [worker min-max] | synthetic end-to-end median (us) | synthetic / P5 |", "|---|---|---:|---:|---:|"]
    for n, b in (("N512", 8), ("N64", 1)):
        for v in ("flat", "fixed_tree", "learned_tree"):
            c = p5[(v, "lookup_score_select", b)]
            s = d["runs"][n][v]["end_to_end"]["median_ns"]
            m = c["median_across_workers_of_median_ns"]
            rows.append(f"| batch {b} x ctx 64 ({n[1:]} queries) | {v} | {us(m)} [{us(c['min_worker_median_ns'])}-{us(c['max_worker_median_ns'])}] | {us(s)} | {s/m:.3f} |")
    return "\n".join(rows)


def ratios():
    out = []
    for n, b in (("N512", 8), ("N64", 1)):
        syn = d["runs"][n]["fixed_tree"]["end_to_end"]["median_ns"] / d["runs"][n]["flat"]["end_to_end"]["median_ns"]
        ret = p5[("fixed_tree", "lookup_score_select", b)]["median_across_workers_of_median_ns"] / p5[("flat", "lookup_score_select", b)]["median_across_workers_of_median_ns"]
        out.append(f"| {n[1:]} | {syn:.2f} | {ret:.2f} |")
    return "| N | synthetic fixed_tree/flat | retained P5 fixed_tree/flat |\n|---|---:|---:|\n" + "\n".join(out)


(H / "tables.md").write_text("\n\n".join([
    "## e2e\n" + e2e_table(), "## p5\n" + p5_table(), "## ratios\n" + ratios(),
    "## tree512\n" + stage_table("N512", "fixed_tree"), "## flat512\n" + stage_table("N512", "flat"),
    "## tree512 groups\n" + group_table("N512", "fixed_tree"),
    "## tree64\n" + stage_table("N64", "fixed_tree"), "## flat64\n" + stage_table("N64", "flat"),
    "## learned512\n" + stage_table("N512", "learned_tree"),
]))
