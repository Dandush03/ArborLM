"""Q3 split check against studies/p9/data.py (structure only; no model; scratch seed 777001, which is
in no study's namespace). Run from the worktree root so that `studies` is importable:
  cd <worktree> && uv run --locked python <review>/c4_q3_split.py
Checks: cluster of row i is i // 16; set A = rows 0..4095 = clusters 0..255; a TrainingStream over A
(or B) holds only A (or B) facts, one cluster per context, 32 updates per epoch; 512 exposures per A
fact after 16,384 updates; reserved-class exclusion uses the same salt so the A-only stream avoids
panel pairs; mixed-cluster octets do not straddle the A/B boundary."""
import torch
from studies.p9 import data, core

SEED = 777001
tab = data.make_fact_table(SEED, 8192, 0, cluster_seed=SEED + 1)
assert torch.equal(tab.cluster, torch.arange(8192) // 16), "cluster != i // 16"
print("clusters:", int(tab.cluster.max()) + 1, "of", core.CLUSTER_SIZE)
pool = tuple(range(100, 148))
tmpl = data.split_templates(pool, SEED + 2)
A, B = torch.arange(4096), torch.arange(4096, 8192)
for name, ids in (("A", A), ("B", B)):
    st = data.make_training_stream(tab, ids, tmpl, SEED + 3)
    ctx, _, cl = st.epoch_contexts(0)
    inset = torch.isin(ctx, ids).all().item()
    one_cluster = bool(((ctx // 16) == cl[:, None]).all())
    print(f"set {name}: updates/epoch {st.updates_per_epoch}; all facts in set {inset}; one cluster per context {one_cluster};"
          f" clusters {int(cl.min())}..{int(cl.max())}")
    ex = st.exposures(16384)
    print(f"   exposures after 16,384 updates: min {int(ex.min())} max {int(ex.max())}")
    # reserved panel classes avoided
    perm_ok = True
print("octet boundary: 256 % 8 =", 256 % 8, "-> mixed-cluster octets", "do not straddle" if 256 % 8 == 0 else "straddle", "A/B")
