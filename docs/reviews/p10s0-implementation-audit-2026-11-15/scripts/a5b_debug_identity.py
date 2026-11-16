"""Debug of a5's parameter mismatch: determinism of each side and which tensors differ. Test seeds p10s0-test-7 only. Claude (Opus 5.5) review."""
import sys, json, torch
sys.argv = [sys.argv[0]]
exec(open(__file__.replace("a5b_debug_identity.py", "a5_arms_identity.py")).read().split("HY = core.HYPER")[0])
HY = core.HYPER._replace(u_pre=2048.0)
data = data_for(2048)
def p9side(arm, steps=12):
    tr, m9, stream = p9ii_trainer(arm, 4096, 1, data, HY)
    tr.anchor = {n: p.detach().clone() for n, p in tr.named}
    ls = [tr.step(stream.batch(u))["task_loss"] for u in range(1, steps + 1)]
    return m9, ls
out = {}
for arm in ("A0", "A6"):
    a, la = p9side(arm); b, lb = p9side(arm)
    s1 = s0_run(arm, "2K/4K", data, HY, 12); s2 = s0_run(arm, "2K/4K", data, HY, 12)
    pa, pb = dict(a.named_parameters()), dict(b.named_parameters())
    q1, q2 = dict(s1.model.named_parameters()), dict(s2.model.named_parameters())
    out[arm] = {
        "p9_side_deterministic": all(torch.equal(pa[n], pb[n]) for n in pa) and la == lb,
        "s0_side_deterministic": all(torch.equal(q1[n], q2[n]) for n in q1),
        "differ_s0_vs_p9": {n: float((q1[n] - pa[n]).abs().max()) for n in q1 if not torch.equal(q1[n], pa[n])},
        "loss_first_diff_index": next((i for i, (x, y) in enumerate(zip([r["task_loss"] for r in s1.updates], la)) if x != y), None),
        "torch_threads": torch.get_num_threads(),
    }
print(json.dumps(out, indent=1))
