# ruff: noqa  (auditor's script, recorded as run except for this line)
# ruff: noqa
"""Audit 21 probe: why my per-window GEN NLL (float64 log-softmax of the float32 logits) differs from the stored one by up to 4.5e-5.
Computes, for the first N windows, the NLL three ways: float32 log_softmax (as the stored value is described), float64 log_softmax, and float32 with
the mean taken in float64; prints each against the stored M1|AB|0 gen:token64 nll_base."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import a21_lib as L
import torch

torch.set_num_threads(6)
N = int(sys.argv[1]) if len(sys.argv) > 1 else 12
stored = json.loads((L.RUN / "item_records.json").read_text())["items"]["M1|AB|0|gen:token64"]["gen"]["nll_base"]
data = L.Data(check_hashes=False)
model = L.Model(data)
rows = []
for k, w in enumerate(data.windows[:N]):
    logits = model.fwd(w["ids"])[0][L.FIRST_NLL - 1 : -1]
    tgt = torch.tensor(w["ids"][L.FIRST_NLL:])
    f32 = float(-torch.log_softmax(logits, dim=-1).gather(1, tgt[:, None]).mean())
    f64 = float(-torch.log_softmax(logits.double(), dim=-1).gather(1, tgt[:, None]).mean())
    f32m64 = float(-torch.log_softmax(logits, dim=-1).gather(1, tgt[:, None]).double().mean())
    rows.append((k, stored[k], f32, f64, f32m64, float(logits.abs().max())))
    print(f"w{k}: stored {stored[k]!r} f32 {f32!r} (eq {f32 == stored[k]}) f64 {f64!r} |f64-stored| {abs(f64 - stored[k]):.3e} |f32m64-f64| {abs(f32m64 - f64):.3e} max|logit| {rows[-1][5]:.1f}")
