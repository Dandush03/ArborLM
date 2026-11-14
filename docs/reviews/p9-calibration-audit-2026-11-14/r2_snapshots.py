"""Audit item 2 (records): R2 snapshots re-evaluated with the auditor's own R2 forward and scorer.

For each of the 9 calibration cells and each of its 3 snapshots:
  * own R2 forward: slot = fact id found from the identifier bytes in the tokens via an own lookup
    (first four symbols, checked to be unique); delta = sigmoid(gate) * wo @ values[slot] added to the
    block-0 residual at answer sites only; own block-1/final-norm/tied-output forward
  * accuracy on Panels A and B restricted to F (trained facts only), compared with calibrate.json
  * per-answer-symbol accuracy (which facts fail), p(correct) renormalised over the alphabet and the
    full 256-way p(correct)
  * shared readout state: gate, sigmoid(gate), ||wo||_F and singular values, trained value-row norms,
    mean ||delta|| at answer sites
  * initialisation-seed check: value rows that never received a gradient (slots >= F at 4,096 slots)
    must equal the N(0, 0.02) init of seed 179001 / 179002 + 2000 (rehearsal), not 1701 / 1702 + 2000
Also from updates.jsonl: the answer-site task loss averaged over windows of 64 updates, so the loss
can be compared across sizes at equal update count and at equal exposure.

Usage: uv run --locked python docs/reviews/p9-calibration-audit-2026-11-14/r2_snapshots.py
"""

import json

import _common as c
import torch
from arborlm.pilot_model import _matrix

CELLS = [
    ("CAL-A5-flat-R2-n4096-b101-o301-s1701", 4096, 2048, "b101", 179001),
    ("CAL-A5-flat-R2-n4096-b101-o301-s1702", 4096, 2048, "b101", 179002),
    ("CAL-A5-flat-R2-n4096-b102-o302-s1701", 4096, 2048, "b102", 179001),
    ("CAL-A5-flat-R2-n16384-b101-o301-s1701", 16384, 8192, "b101", 179001),
    ("CAL-A5-flat-R2-n16384-b101-o301-s1702", 16384, 8192, "b101", 179002),
    ("CAL-A5-flat-R2-n16384-b102-o302-s1701", 16384, 8192, "b102", 179001),
    ("CAL-A5-flat-R2-n65536-b101-o301-s1701", 65536, 32768, "b101", 179001),
    ("CAL-A5-flat-R2-n65536-b101-o301-s1702", 65536, 32768, "b101", 179002),
    ("CAL-A5-flat-R2-n65536-b102-o302-s1701", 65536, 32768, "b102", 179001),
]
SITES = torch.tensor([8 * r + 6 for r in range(8)])


def own_slots(s, tokens):
    """fact id of each record from the identifier bytes (own lookup)."""
    code_of = {}
    ident = s.facts.ident
    codes = (ident[:, :4] * torch.tensor([1, 32, 1024, 32768])).sum(1).tolist()
    for i, k in enumerate(codes):
        assert k not in code_of
        code_of[k] = i
    sym = tokens.reshape(-1, 8, 8)[:, :, 1:5] - 0x40
    k = (sym * torch.tensor([1, 32, 1024, 32768])).sum(-1)
    return torch.tensor([code_of.get(int(v), -1) for v in k.reshape(-1)]).reshape(-1, 8)


@torch.no_grad()
def r2_eval(bb, values, wo, gate, tokens, slots, facts):
    out_c, out_ps, out_pf, out_ans, dn = [], [], [], [], []
    for st in range(0, tokens.shape[0], 512):
        tk = tokens[st : st + 512]
        sl = slots[st : st + 512]
        h = c.hidden0(bb, tk[:, :63])
        valid = (sl >= 0) & (sl < facts)
        read = values[sl.clamp_min(0)] * valid[..., None]
        delta = torch.sigmoid(gate) * read @ wo.T
        h = h.clone()
        h[:, SITES] += delta
        logits = c.head(bb, h)[:, SITES].reshape(-1, 256)
        ans = (tk.reshape(-1, 8, 8)[:, :, 7] - 0x40).reshape(-1)
        cr, ps, pf = c.score(logits, ans)
        out_c.append(cr)
        out_ps.append(ps)
        out_pf.append(pf)
        out_ans.append(ans)
        dn.append(delta.norm(dim=-1).reshape(-1))
    return torch.cat(out_c), torch.cat(out_ps), torch.cat(out_pf), torch.cat(out_ans), torch.cat(dn)


def loss_windows(path, w=64):
    losses = [json.loads(line)["task_loss"] for line in path.open()]
    t = torch.tensor(losses)
    n = len(t) // w
    return [float(x) for x in t[: n * w].reshape(n, w).mean(1)]


def main():
    s = c.study()
    bbs = {p: c.backbone(p) for p in ("b101", "b102")}
    panels = {}
    for name in ("panel_a", "panel_b"):
        for facts in (2048, 8192, 32768):
            tok, ids = c.restrict(s.streams[name], facts)
            sl = own_slots(s, tok)
            assert torch.equal(sl, ids), "own slot lookup disagrees with stream bookkeeping"
            panels[(name, facts)] = (tok, sl)
    out = []
    for label, slots_n, facts, parent, init_seed in CELLS:
        cell_dir = c.RUN / "cells" / label
        recorded = json.loads((cell_dir / "calibrate.json").read_text())["r2_accuracy"]
        snaps = sorted((cell_dir / "snapshots").iterdir())
        rec = {"label": label, "slots": slots_n, "facts": facts, "parent": parent, "snapshots": []}
        for snap in snaps:
            m = torch.load(snap / "model.pt", weights_only=True)["model"]
            values, wo, gate = m["addition.values"], m["addition.wo"], m["addition.gate"]
            for k, v in m.items():
                if k.startswith("backbone."):
                    ref = bbs[parent].state_dict()[k[len("backbone."):]]
                    assert torch.equal(v, ref), f"backbone tensor {k} differs"
            update = int(snap.name[1:])
            exposure = update * 128 // facts
            row = {"update": update, "exposure": exposure}
            for name, key in (("panel_a", "A"), ("panel_b", "B")):
                tok, sl = panels[(name, facts)]
                cr, ps, pf, ans, dn = r2_eval(bbs[parent], values, wo, gate, tok, sl, facts)
                row[f"acc_{key}"] = cr.float().mean().item()
                row[f"recorded_{key}"] = recorded[str(exposure)][key]
                row[f"p_sigma_mean_{key}"] = ps.mean().item()
                row[f"p_full_mean_{key}"] = pf.mean().item()
                row[f"p_full_ge_0.95_{key}"] = (pf >= 0.95).float().mean().item()
                if key == "A":
                    per_sym = [cr[ans == a].float().mean().item() for a in range(32)]
                    row["per_symbol_acc_A"] = per_sym
                    row["failures_A"] = int((~cr).sum())
                    row["failures_by_symbol_A"] = [int((~cr[ans == a]).sum()) for a in range(32)]
                    row["delta_norm_mean"] = dn.mean().item()
            sv = torch.linalg.svdvals(wo)
            row.update(
                gate=float(gate),
                sigmoid_gate=float(torch.sigmoid(gate)),
                wo_fro=float(wo.norm()),
                wo_sv_max=float(sv[0]),
                wo_sv_min=float(sv[-1]),
                value_row_norm_mean=float(values[:facts].norm(dim=1).mean()),
            )
            if slots_n > facts:
                init = _matrix(init_seed + 2000, slots_n, 32)
                reg = _matrix(1701 + (init_seed - 179001) + 2000, slots_n, 32)
                row["unused_rows_equal_rehearsal_init"] = bool(torch.equal(values[facts:], init[facts:]))
                row["unused_rows_equal_registered_init"] = bool(torch.equal(values[facts:], reg[facts:]))
            rec["snapshots"].append(row)
            print(json.dumps({k: v for k, v in row.items() if not isinstance(v, list)}), label)
        rec["loss_windows_64"] = loss_windows(cell_dir / "updates.jsonl")
        out.append(rec)
    (c.OUT / "r2_snapshots.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
