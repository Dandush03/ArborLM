"""EXPLORATORY operator-level profile of the EXISTING Memory.lookup (synthetic tensors).

Not a registered experiment. Times only unmodified code and a stage decomposition that
executes the same operations in the same order. No alternative implementation is timed.
"""

from __future__ import annotations

import gc
import json
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

import torch
from torch.nn import functional as F

from arborlm.pilot_model import EPS, PER_BRANCH, TEMP, TOP, Memory

torch.set_num_threads(1)
torch.set_num_interop_threads(1)

OUT = Path(__file__).resolve().parent
SEED = 9001  # not a registered project seed
ROUNDS, WARMUPS, CALLS = 8, 2, 10
SIZES = (512, 64)
VARIANTS = ("flat", "fixed_tree", "learned_tree")
PROFILE_CALLS = 20


def stats(samples: list[int], round_medians: list[float]) -> dict:
    s = sorted(samples)
    q = lambda p: s[min(len(s) - 1, int(p * (len(s) - 1) + 0.5))]  # noqa: E731
    return {
        "median_ns": statistics.median(samples),
        "p10_ns": q(0.10),
        "p90_ns": q(0.90),
        "min_ns": s[0],
        "max_ns": s[-1],
        "round_medians_ns": round_medians,
        "n_samples": len(samples),
    }


def tensors_of(obj) -> dict:
    return obj if isinstance(obj, dict) else {"out": obj}


class Stage:
    def __init__(self, name, group, fn, inputs):
        self.name, self.group, self.fn, self.inputs = name, group, fn, inputs
        self.samples: list[int] = []
        self.round_medians: list[float] = []


def stable_top_stages(prefix, group, scores, count, ids=None):
    """Mirror stable_top line by line; returns stages and the (selected, indices) result.

    Each stage's input is a real intermediate tensor produced by the previous stage.
    """
    stages = []
    cur = scores
    if ids is not None:
        by_id = ids.argsort(dim=-1)
        stages.append(Stage(f"{prefix}ids.argsort", group, lambda: ids.argsort(dim=-1), [ids]))
        s2, i2 = scores.gather(-1, by_id), ids.gather(-1, by_id)
        stages.append(
            Stage(f"{prefix}gather scores by_id", group, lambda: scores.gather(-1, by_id), [scores, by_id])
        )
        stages.append(Stage(f"{prefix}gather ids by_id", group, lambda: ids.gather(-1, by_id), [ids, by_id]))
        cur = s2
    sc = cur
    assert sc.shape[-1] > count
    top, chosen = sc.topk(count + 1, sorted=True)
    stages.append(
        Stage(f"{prefix}topk({count + 1})", group, lambda: dict(zip(("top", "chosen"), sc.topk(count + 1, sorted=True))), [sc])
    )
    safe = (top[..., :-1] > top[..., 1:]).all(dim=-1)
    stages.append(
        Stage(
            f"{prefix}tie-safety check",
            group,
            lambda: {"safe": (top[..., :-1] > top[..., 1:]).all(dim=-1), "all": bool(safe.all())},
            [top],
        )
    )
    assert bool(safe.all()), "ties found: fallback path would run; synthetic data should not tie"
    indices = chosen[..., :count].contiguous()
    stages.append(
        Stage(f"{prefix}slice+contiguous", group, lambda: chosen[..., :count].contiguous(), [chosen])
    )
    selected = sc.gather(-1, indices)
    stages.append(Stage(f"{prefix}final gather scores", group, lambda: sc.gather(-1, indices), [sc, indices]))
    if ids is None:
        return stages, selected, indices
    final_ids = i2.gather(-1, indices)
    stages.append(Stage(f"{prefix}final gather ids", group, lambda: i2.gather(-1, indices), [i2, indices]))
    return stages, selected, final_ids


def flat_stages(m: Memory, q):
    st = []
    nk = F.normalize(m.keys, dim=-1, eps=EPS)
    st.append(Stage("F1 normalize(keys)", "normalize keys", lambda: F.normalize(m.keys, dim=-1, eps=EPS), [m.keys]))
    scores = (q @ nk.T) / TEMP
    st.append(Stage("F2 q@nk.T / TEMP", "matmul+div", lambda: (q @ nk.T) / TEMP, [q, nk]))
    sub, w, sel = stable_top_stages("F3 ", "stable_top(scores, 8)", scores, TOP)
    return st + sub, w, sel


def tree_stages(m: Memory, q):
    def _bmm_div():
        b = torch.bmm(local, q.unsqueeze(-1))
        return {"bmm": b, "scaled": b.squeeze(-1) / TEMP}

    st = []
    rn = F.normalize(m.router, dim=-1, eps=EPS)
    st.append(Stage("T1 normalize(router)", "router normalize", lambda: F.normalize(m.router, dim=-1, eps=EPS), [m.router]))
    routes = (q @ rn.T) / TEMP
    st.append(Stage("T2 route q@rn.T / TEMP", "route matmul+div", lambda: (q @ rn.T) / TEMP, [q, rn]))
    sub, _, branch_ids = stable_top_stages("T3 ", "branch stable_top(routes, 2)", routes, 2)
    st += sub
    ar = torch.arange(PER_BRANCH, device="cpu")
    indices = (branch_ids[..., None] * PER_BRANCH + ar).flatten(1)
    st.append(
        Stage(
            "T4 candidate index build",
            "candidate indices",
            lambda: (branch_ids[..., None] * PER_BRANCH + torch.arange(PER_BRANCH, device="cpu")).flatten(1),
            [branch_ids],
        )
    )
    gathered = m.keys[indices]
    st.append(Stage("T5 keys[indices] gather", "gather keys", lambda: m.keys[indices], [m.keys, indices]))
    local = F.normalize(gathered, dim=-1, eps=EPS)
    st.append(Stage("T6 normalize(gathered)", "normalize gathered", lambda: F.normalize(gathered, dim=-1, eps=EPS), [gathered]))
    scores = torch.bmm(local, q.unsqueeze(-1)).squeeze(-1) / TEMP
    st.append(
        Stage(
            "T7 bmm + squeeze + / TEMP",
            "bmm+div",
            _bmm_div,
            [local, q],
        )
    )
    ls = routes.log_softmax(-1)
    st.append(Stage("T8a routes.log_softmax", "prior", lambda: routes.log_softmax(-1), [routes]))
    prior = ls.gather(-1, branch_ids)
    st.append(Stage("T8b prior gather(branch_ids)", "prior", lambda: ls.gather(-1, branch_ids), [ls, branch_ids]))
    rep = prior.repeat_interleave(PER_BRANCH, dim=-1)
    st.append(Stage("T8c prior.repeat_interleave", "prior", lambda: prior.repeat_interleave(PER_BRANCH, dim=-1), [prior]))
    scores = scores + rep
    st.append(Stage("T8d scores + prior", "prior", lambda: scores + rep, [scores, rep]))
    sub, w, sel = stable_top_stages("T9 ", "final stable_top(scores, 8, indices)", scores, TOP, indices)
    return st + sub, w, sel, routes, branch_ids, indices


def time_things(entries: dict[str, callable], per_round_pre=None) -> dict[str, tuple[list[int], list[float]]]:
    """entries: name -> zero-arg callable. Rounds interleave all entries."""
    samples = {k: [] for k in entries}
    rmeds = {k: [] for k in entries}
    for _ in range(ROUNDS):
        gc.collect()
        gc.disable()
        try:
            for k, fn in entries.items():
                for _ in range(WARMUPS):
                    r = fn()
                    del r
                row = []
                for _ in range(CALLS):
                    t0 = time.perf_counter_ns()
                    r = fn()
                    t1 = time.perf_counter_ns()
                    del r  # deallocation outside the timed region
                    row.append(t1 - t0)
                samples[k] += row
                rmeds[k].append(statistics.median(row))
        finally:
            gc.enable()
    return {k: (samples[k], rmeds[k]) for k in entries}


def out_info(result, input_ptrs):
    info = []
    for name, v in tensors_of(result).items():
        if not isinstance(v, torch.Tensor):
            info.append({"name": name, "python_value": type(v).__name__})
            continue
        view = v.untyped_storage().data_ptr() in input_ptrs
        info.append(
            {
                "name": name,
                "shape": list(v.shape),
                "dtype": str(v.dtype),
                "numel": v.numel(),
                "itemsize": v.element_size(),
                "bytes": v.numel() * v.element_size(),
                "materialized_new_storage": not view,
                "bytes_materialized": 0 if view else v.numel() * v.element_size(),
            }
        )
    return info


def make_queries(n: int):
    g = torch.Generator(device="cpu").manual_seed(SEED)
    return F.normalize(torch.randn(n, 16, generator=g, dtype=torch.float32), dim=-1, eps=EPS)


def profile_table(fn, label, n):
    from torch.profiler import ProfilerActivity, profile

    for _ in range(3):
        fn()
    with profile(activities=[ProfilerActivity.CPU]) as prof:
        for _ in range(PROFILE_CALLS):
            fn()
    table = prof.key_averages().table(sort_by="self_cpu_time_total", row_limit=40)
    (OUT / f"profiler_{label}_N{n}.txt").write_text(
        f"# torch.profiler CPU, {PROFILE_CALLS} calls of unmodified Memory.lookup, N={n}, {label}\n"
        f"# profiler overhead inflates small ops; cross-check only\n{table}\n"
    )


def environment():
    try:
        cpu = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True).strip()
    except Exception:
        cpu = platform.processor()
    ci = time.get_clock_info("perf_counter")
    # timer call overhead: back-to-back perf_counter_ns pairs and empty-lambda call
    f = lambda: None  # noqa: E731
    ov = []
    for _ in range(2000):
        t0 = time.perf_counter_ns()
        r = f()
        t1 = time.perf_counter_ns()
        ov.append(t1 - t0)
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_model": cpu,
        "python": sys.version,
        "torch": torch.__version__,
        "torch_config": torch.__config__.show(),
        "torch_parallel_info": torch.__config__.parallel_info(),
        "num_threads": torch.get_num_threads(),
        "num_interop_threads": torch.get_num_interop_threads(),
        "perf_counter_info": {"implementation": ci.implementation, "resolution_s": ci.resolution, "monotonic": ci.monotonic},
        "empty_lambda_timed_call_median_ns": statistics.median(ov),
        "seed": SEED,
        "rounds_warmups_calls": [ROUNDS, WARMUPS, CALLS],
        "gc_disabled_in_timed_blocks": True,
    }


def main():
    result = {"label": "EXPLORATORY synthetic, not preregistered, not evidence for any speedup", "environment": environment(), "runs": {}}
    with torch.inference_mode():
        for n in SIZES:
            q = make_queries(n)
            mems = {v: Memory(v, SEED).eval() for v in VARIANTS}
            entries, stage_map, equal = {}, {}, {}
            for v, m in mems.items():
                entries[f"{v}|end_to_end"] = (lambda m=m: m.lookup(q))
                if v == "flat":
                    stages, w, sel = flat_stages(m, q)
                    ref_w, ref_l = m.lookup(q)
                    equal[v] = bool(torch.equal(w, ref_w) and torch.equal(sel, ref_l.selected))
                else:
                    stages, w, sel, routes, branches, indices = tree_stages(m, q)
                    ref_w, ref_l = m.lookup(q)
                    equal[v] = bool(
                        torch.equal(w, ref_w)
                        and torch.equal(sel, ref_l.selected)
                        and torch.equal(indices, ref_l.candidate_ids)
                        and torch.equal(branches, ref_l.branch_ids)
                        and torch.equal(routes, ref_l.route_scores)
                    )
                assert equal[v], f"decomposition not bitwise equal to Memory.lookup for {v} N={n}"
                stage_map[v] = stages
                for s in stages:
                    entries[f"{v}|{s.name}"] = s.fn
            timed = time_things(entries)
            run = {}
            for v in VARIANTS:
                e2e = stats(*timed[f"{v}|end_to_end"])
                rows = []
                for s in stage_map[v]:
                    ptrs = {t.untyped_storage().data_ptr() for t in s.inputs if isinstance(t, torch.Tensor)}
                    rows.append(
                        {
                            "stage": s.name,
                            "group": s.group,
                            **stats(*timed[f"{v}|{s.name}"]),
                            "outputs": out_info(s.fn(), ptrs),
                        }
                    )
                total = sum(r["median_ns"] for r in rows)
                for r in rows:
                    r["share_of_stage_sum"] = r["median_ns"] / total
                    r["bytes_materialized"] = sum(o.get("bytes_materialized", 0) for o in r["outputs"])
                run[v] = {
                    "end_to_end": e2e,
                    "stages": rows,
                    "stage_median_sum_ns": total,
                    "stage_sum_over_end_to_end": total / e2e["median_ns"],
                    "bitwise_equal_to_Memory.lookup": equal[v],
                    "total_bytes_materialized_stage_outputs": sum(r["bytes_materialized"] for r in rows),
                }
            result["runs"][f"N{n}"] = run
            for v in ("flat", "fixed_tree"):
                m = mems[v]
                profile_table(lambda m=m: m.lookup(q), v, n)
    (OUT / "operator_profile.json").write_text(json.dumps(result, indent=1))
    for n, run in result["runs"].items():
        for v, r in run.items():
            print(n, v, "e2e median us", r["end_to_end"]["median_ns"] / 1e3, "stage sum us", r["stage_median_sum_ns"] / 1e3, "ratio", round(r["stage_sum_over_end_to_end"], 3))


if __name__ == "__main__":
    main()
