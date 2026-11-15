# FIFO list-scheduling simulation (6 workers, tasks launched in the pool's list order) vs the projection's "rounds of six" model.
# Task order transcribed from studies/p10s0/core.py q1_cells/wx_cells/probe_cells (2K/4K block, then 8K/16K, then 8K/4K; within: arm, draw, seed). Times from my p3 recomputation logic.
import heapq, json, sys, importlib.util
spec = importlib.util.spec_from_file_location("p3", sys.argv[1]); 
src = open(sys.argv[1]).read().split("res = {")[0]
ns = {}; exec(src, ns)
r = ns["merged"](True)
def order(block, key):
    c = []
    if block == "q1":
        for ct in ("2K4K", "8K16K"):
            for arm in ("A0", "A1", "A2", "A5-D"):
                for d in range(10):
                    c += [(arm, ct)] * (1 if (key == "cut3" and ct == "8K16K") else 2)
            c += [("A6", ct)] * 10 + [("A7", ct)] * 10
        c += [("A0", "8K4K")] * 10 + [("A5-D", "8K4K")] * 10 + [("A6", "8K4K")] * 10
    elif block == "wx":
        c = [(f"WX-{key}", "2K4K")] * 10 + [(f"WX-{key}", "8K16K")] * 10
    else:
        c = [(key, "32K64K")] * 3 + [("A6", "32K64K")] * 3
    return c
def fifo(ts, w=6):
    h = [0.0] * w
    for t in ts:
        s = heapq.heappop(h); heapq.heappush(h, s + t)
    return max(h)
out = {}
for b, k in [("q1", "full"), ("q1", "cut3"), ("wx", "A5-D"), ("wx", "A1"), ("probe", "A5-D"), ("probe", "A1")]:
    cs = order(b, k)
    tr = [ns["train_s"](a, ct, r) for a, ct in cs]; ev = [ns["eval_s"](a, ct, r) for a, ct in cs]
    out[f"{b}:{k}"] = {"train_rounds": ns["rounds"](tr), "train_fifo_pool_order": fifo(tr), "train_lpt": fifo(sorted(tr, reverse=True)), "train_sum_over_6": sum(tr) / 6,
                       "eval_rounds": ns["rounds"](ev), "eval_fifo_pool_order": fifo(ev), "eval_sum_over_6": sum(ev) / 6}
    o = out[f"{b}:{k}"]; o["fifo_over_rounds_train"] = o["train_fifo_pool_order"] / o["train_rounds"]; o["fifo_over_rounds_eval"] = o["eval_fifo_pool_order"] / o["eval_rounds"]
json.dump(out, sys.stdout, indent=1)
