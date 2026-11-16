"""Per-step parameter trace of two identical P9-II Trainer runs (test seeds p10s0-test-7). Claude (Opus 5.5) review."""
import sys, json, torch
sys.argv = [sys.argv[0]]
exec(open(__file__.replace("a5c_debug_steps.py", "a5_arms_identity.py")).read().split("HY = core.HYPER")[0])
HY = core.HYPER._replace(u_pre=2048.0)
data = data_for(2048)
def trace(arm):
    tr, m9, stream = p9ii_trainer(arm, 4096, 1, data, HY)
    snaps = []
    for u in range(1, 13):
        rec = tr.step(stream.batch(u))
        snaps.append((rec["task_loss"], {n: p.detach().clone() for n, p in tr.named}))
    return snaps, m9, tr
a, ma, ta = trace("A0"); b, mb, tb = trace("A0")
rows = []
for i, ((la, pa), (lb, pb)) in enumerate(zip(a, b), start=1):
    rows.append({"update": i, "loss_equal": la == lb, "max_param_diff": max(float((pa[n] - pb[n]).abs().max()) for n in pa)})
final = max(float((p - dict(mb.named_parameters())[n]).abs().max()) for n, p in ma.named_parameters())
same_obj = [n for n, p in ta.named if p is not dict(ma.named_parameters())[n]]
print(json.dumps({"rows": rows, "final_model_param_diff": final, "trainer_params_not_the_model_params": same_obj}, indent=1))
