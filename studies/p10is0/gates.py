# ruff: noqa: E501
"""P10IS0 gates (ADR-0023 section 3 and stage 1): the two-part identity gate, the end-to-end gate at the new sizes, the resume-from-snapshot test and the seed gate.

Part (a) compares this study's path with P10-S0's own code (``studies.p10s0.train.run_job`` and ``studies.p10s0.evaluate.evaluate_readout``) at 4,096 and 16,384 slots, on P10-S0's rehearsal set (the declared re-use of the registry's section 4.6): initial
state dict, the logits of one forward, the state dict after one update and after N updates (P10-S0's path at its cadence of 64, this path at its own), and every measured field of one full evaluation record at the last of them. The fields excluded
from the comparison are listed in the result. Part (b) compares this path at any slot count with a reference written here from the definitions: the model equals ``studies.p9ii.model.build_model`` tensor for tensor, and after one update the loss
and every parameter equal a direct float32 computation of the alphabet loss, L_div, the clip at 1.0 and the AdamW step within 1e-6 (the forward is the model's own; the memory selection is checked against a brute-force top-8 of the cosine scores).
The auditor writes an independent reference. Bit-exact assertions are made on the platform of record only.

Recorded for the auditor (implementer's observation, not a result): with L_div written as exp-sum the reference differed from the trainer by 8.4e-6 in ONE element of ``wq`` at 8,192 slots (A5-D). Cause: AdamW's first step is
lr * g / (|g| + 1e-8), which is about lr * sign(g) for |g| above eps and has slope about lr / (4 eps) = 75,000 per unit of g near |g| = eps, so a float32 difference of 1e-10 in a gradient entry near eps becomes up to 7.5e-6 in the
parameter. The tolerance stays 1e-6 and the reference reproduces float32 operation order (``torch.logsumexp``, ``F.cross_entropy``), after which the worst difference is 7e-9. The reference now has its OWN forward of the memory read (R9; the frozen backbone modules and the oracle code table are re-used, see ``reference_update``) and checks selection by a brute-force top-8. P10-S0's own A6 records carry no read swap: this study computes a_use for A6
(``reference_swap``) because Stage R's reference validity reads condition 6 on A6; the identity gate ignores that key.
"""

import json
import math
from pathlib import Path
from typing import Any

import torch

from studies.p9ii import model as p9iimodel
from studies.p10s0 import core as s0core
from studies.p10s0 import evaluate as s0eval
from studies.p10s0 import model as s0model
from studies.p10s0 import train as s0train

from . import adapter, core
from .core import Cell


def s0_celltype(real_facts: int, slots: int) -> str:
    """P10-S0's cell type for a (facts, slots) pair (its fixed registry)."""
    for name, ct in s0core.CELLTYPES.items():
        if (ct.facts, ct.slots) == (real_facts, slots):
            return name
    raise ValueError(f"P10-S0 has no cell type with {real_facts} facts and {slots} slots")


def tensors_equal(a: dict[str, torch.Tensor], b: dict[str, torch.Tensor]) -> list[str]:
    """The names whose tensors differ (``torch.equal`` per tensor; a missing key differs)."""
    return sorted(k for k in a.keys() | b.keys() if k not in a or k not in b or not torch.equal(a[k], b[k]))


def _same(x: Any, y: Any) -> bool:
    if isinstance(x, dict) and isinstance(y, dict):
        return x.keys() == y.keys() and all(_same(x[k], y[k]) for k in x)
    if isinstance(x, list | tuple) and isinstance(y, list | tuple):
        return len(x) == len(y) and all(_same(p, q) for p, q in zip(x, y, strict=True))
    if isinstance(x, float) and isinstance(y, float):
        return x == y or (math.isnan(x) and math.isnan(y))
    return bool(x == y)


def measured_fields(record: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in record.items() if k not in adapter.EXCLUDED_FROM_IDENTITY}


def identity_part_a(
    arm: str, real_facts: int, slots: int, *, backbone: Any, corpus: bytes, rows: torch.Tensor, out_dir: Path, updates: int, facts: int | None = None, tiny: bool = False, cadence_new: tuple[int, int, int] = (64, 1024, 4096),
    cadence_s0: int = 64, one_update: bool = True,
) -> dict[str, Any]:  # fmt: skip
    """Part (a) for one (arm, fact count, slot count). ``facts`` is the trained fact count (the registered ``real_facts`` unless a test shrinks it). On the registered platform the comparison is asserted; elsewhere it is
    computed and reported but ``asserted`` is false."""
    facts = facts or real_facts
    spec = s0core.test_set(0) if tiny else s0core.REHEARSAL_SET
    mode = "dry" if tiny else "rehearsal"
    init = spec.base + 41 if tiny else s0core.REHEARSAL_INIT
    data = adapter.build_data(spec.seeds(real_facts), corpus, facts, tiny=tiny)
    stream = s0train.training_stream_for(data, facts)
    ctname = s0_celltype(real_facts, slots)
    s0cell = s0core.make_cell(arm, ctname, "PC", 1, 0, "TEST-")
    mine = Cell("TEST" if tiny else "CHK", "M" if real_facts == 8192 else "S", arm, facts, slots, 1, init)
    swap_seed = spec.swap_seed(real_facts)
    target_seed = spec.target_seed(ctname, 0)
    r1 = data.seeds.r1_codes
    result: dict[str, Any] = {"arm": arm, "facts": facts, "real_facts": real_facts, "slots": slots, "updates": updates, "seed_set": spec.name, "excluded_fields": list(adapter.EXCLUDED_FROM_IDENTITY), "checks": {}}

    def s0_run(n: int, tag: str) -> Any:
        job = s0train.Job(
            cell=s0cell, mode=mode, data=data, stream=stream, backbone=backbone, out_dir=out_dir / f"s0-{tag}", init_seed=init, r1_seed=r1, target_seed=target_seed, snapshots=(), max_updates=n, diag_every=cadence_s0,
            whitelist_only=True,
        )  # fmt: skip
        return s0train.run_job(job)

    def my_run(n: int, tag: str) -> adapter.Segment:
        job = adapter.Job(mine, data, stream, backbone, out_dir / f"new-{tag}", r1, target_seed, last_update=n, diag_early=cadence_new[0], diag_late=cadence_new[1], diag_switch=cadence_new[2], identity_gate=True, write_records=False)
        return adapter.run_segment(job)

    m_s0 = s0model.build_model(arm, slots, init, backbone, r1_seed=r1)
    m_new = adapter.build_model(mine, backbone, r1)
    result["checks"]["initial_state"] = tensors_equal(m_s0.state_dict(), m_new.state_dict())
    batch = stream.batch(1)
    with torch.no_grad():
        m_s0.eval()
        m_new.eval()
        result["checks"]["one_forward_logits"] = [] if torch.equal(m_s0(batch.tokens[:, :-1])[0], m_new(batch.tokens[:, :-1])[0]) else ["logits"]
    if one_update:
        result["checks"]["state_after_one_update"] = tensors_equal(s0_run(1, "u1").model.state_dict(), my_run(1, "u1").model.state_dict())
    e_s0, e_new = s0_run(updates, "long"), my_run(updates, "long")
    result["checks"][f"state_after_{updates}_updates"] = tensors_equal(e_s0.model.state_dict(), e_new.model.state_dict())
    from studies.p9i.evaluate import next_byte_loss

    frozen = next_byte_loss(backbone, rows)
    rec_s0 = s0eval.evaluate_readout(s0cell, e_s0.model, data, facts, updates, frozen_backbone=backbone, rows=rows, target_seed=target_seed, swap_seed=swap_seed, frozen_loss=frozen)
    rec_new = adapter.evaluate_readout(mine, e_new.model, data, facts, updates, backbone=backbone, rows=rows, target_seed=0, swap_seed=swap_seed, frozen_loss=frozen)
    a, b = measured_fields(rec_s0), measured_fields(rec_new)
    result["checks"]["evaluation_record"] = sorted(k for k in a if k not in b or not _same(a[k], b[k]))
    result["fields_compared"] = sorted(a)
    result["differences"] = {k: v for k, v in result["checks"].items() if v}
    result["identical"] = not result["differences"]
    result["asserted"] = s0core.on_registered_platform()
    return result


# --- part (b): a reference written from the definitions --------------------------------------------------------------------------------------------------
def _normalize(x: torch.Tensor) -> torch.Tensor:
    return x / x.norm(dim=-1, keepdim=True).clamp_min(1e-8)


def reference_update(model: Any, tokens: torch.Tensor, arm: str) -> dict[str, Any]:
    """One AdamW update computed directly in float32 from the definitions, on a model that is not touched, with its OWN forward (R9). Re-used, not re-written: the frozen backbone modules (token and position embeddings, block 0 and block 1,
    the final norm, the causal mask: frozen P4 code, not under test), the training batch, the initial parameter VALUES of the model (copied as plain tensors) and ``studies.p9.model.unit_code`` (the oracle code table of A6 is a fixed hash, part
    of the data definition). Written here: the window features, the W7 query and its normalisation, cosine keys, top-8 with ties by slot id through a full stable sort, softmax at temperature 0.2, the value read, the output projection and
    gate, the insertion at the answer sites, the alphabet cross-entropy, L_div, the gradients (autograd on this graph), the global-norm clip and the first AdamW step. The architecture of the memory read is written from ADR-0019 section 3,
    so a defect in the model's own read would show as a difference."""
    from studies.p9 import core as p9core
    from studies.p9.model import unit_code

    sites = list(p9core.ANSWER_SITE_POSITIONS)
    alpha0 = int(p9core.ALPHABET[0])
    bb = model.backbone
    pars = {n: p.detach().clone().requires_grad_(True) for n, p in model.trainable()}
    inp = tokens[:, :-1]
    length = inp.shape[1]
    with torch.no_grad():
        h = bb.token(inp) + bb.position(torch.arange(length))
        h = bb.blocks[0](h, bb.mask[:length, :length])
    pre = {n.split(".")[-1]: v for n, v in pars.items()}
    if arm == "A6":
        sym = (inp[:, [8 * r + 1 + i for r in range(8) for i in range(4)]].reshape(-1, 8, 4) - alpha0) & 31
        codes = (sym * torch.tensor([1, 32, 1024, 32768])).sum(-1)
        q = torch.tensor([[unit_code(model.addition.r1_seed, int(c), 16) for c in row] for row in codes.tolist()], dtype=torch.float32).reshape(-1, 16)
    else:
        feats = torch.stack([torch.cat([h[:, s + o] for o in range(-6, 1)], dim=-1) for s in sites], dim=1)  # [B, 8, 224], oldest first
        q = _normalize(feats @ pre["wq"].T).reshape(-1, 16)
    scores = q @ _normalize(pre["keys"]).T / 0.2
    order = torch.sort(scores.detach(), dim=-1, descending=True, stable=True).indices[:, :8]
    w = torch.softmax(scores.gather(1, order), dim=-1)
    read = (w[..., None] * pre["values"][order]).sum(1)
    out = torch.sigmoid(pre["gate"]) * (read @ pre["wo"].T)
    delta = torch.zeros(h.shape).index_put((torch.arange(h.shape[0])[:, None], torch.tensor(sites)[None, :]), out.reshape(h.shape[0], 8, -1))
    logits = bb.final_norm(bb.blocks[1](h + delta, bb.mask[:length, :length])) @ bb.token.weight.T
    inside = logits[:, sites][..., torch.tensor(list(p9core.ALPHABET))].reshape(-1, 32)
    target = (tokens[:, 1:][:, sites] - alpha0).reshape(-1)
    answer = -(inside.log_softmax(-1).gather(1, target[:, None])).mean()
    total, div = answer, None
    if arm == "A5-D":
        n = q.shape[0]
        sims = 2.0 * (q @ q.T)
        off = sims[~torch.eye(n, dtype=torch.bool)]
        div = torch.logsumexp(off, dim=0) - math.log(n * (n - 1))  # log of the mean of exp over the off-diagonal pairs (the stable form of the definition)
        total = answer + 1.0 * div
    names = list(pars)
    grads = torch.autograd.grad(total, [pars[n] for n in names], allow_unused=True)
    grads = [torch.zeros_like(pars[n]) if g is None else g for n, g in zip(names, grads, strict=True)]
    norm = math.sqrt(sum(float((g.double() ** 2).sum()) for g in grads))
    scale = min(1.0, 1.0 / (norm + 1e-6))
    new = {}
    for n, g in zip(names, grads, strict=True):
        g = g * scale
        mhat = (1 - 0.9) * g / (1 - 0.9)
        vhat = (1 - 0.999) * g * g / (1 - 0.999)
        new[n] = pars[n].detach() - 0.003 * mhat / (vhat.sqrt() + 1e-8)
    return {"answer_loss": float(answer), "diversity_loss": None if div is None else float(div), "new_parameters": new}


def brute_force_selection(model: Any, tokens: torch.Tensor) -> list[str]:
    """The top-8 slots of every answer-site query by brute force (cosine scores over all N keys) against ``model.select``; names the mismatches. A6 is skipped: its selection is the oracle code's, not a query's."""
    if model.arm == "A6":
        return []
    with torch.no_grad():
        model.eval()
        h = model.embed_block0(tokens[:, : s0core.INPUT_LENGTH])
        sel = model.select(h, tokens[:, : s0core.INPUT_LENGTH])
        positions = p9iimodel.SITES
        q = torch.nn.functional.normalize(model.addition._query(h, tokens[:, : s0core.INPUT_LENGTH], positions), dim=-1)
        keys = torch.nn.functional.normalize(model.addition.keys, dim=-1)
        scores = (q @ keys.T) / s0core.TEMPERATURE
        mismatched = []
        top = scores.topk(s0core.TOP, dim=-1)
        got = sel.selected.reshape(-1, s0core.TOP)
        want = top.indices.reshape(-1, s0core.TOP)
        for r in range(want.shape[0]):
            if set(got[r].tolist()) != set(want[r].tolist()):
                mismatched.append(f"row {r}")
        return mismatched[:5]


def identity_part_b(arm: str, slots: int, *, facts: int, backbone: Any, data: Any, stream: Any, cell: Cell, out_dir: Path, tolerance: float | None = None) -> dict[str, Any]:
    """Part (b) at one (arm, slot count): the model equals ``studies.p9ii.model.build_model`` tensor for tensor, and after one update the loss and every parameter equal the reference within ``tolerance`` (config: 1e-6)."""
    tol = float(core.load_config()["identity"]["tolerance"]) if tolerance is None else tolerance
    r1 = data.seeds.r1_codes
    direct = p9iimodel.build_model(arm, slots, cell.init_seed, backbone, r1_seed=r1, seed_rng=True)
    mine = adapter.build_model(cell, backbone, r1)
    out: dict[str, Any] = {"arm": arm, "slots": slots, "tolerance": tol, "model_differs": tensors_equal(direct.state_dict(), mine.state_dict())}
    batch = stream.batch(1)
    ref_model = adapter.build_model(cell, backbone, r1)
    ref_model.train()
    ref = reference_update(ref_model, batch.tokens, arm)
    out_dir = out_dir / f"partb-{core.utc_stamp()}"  # a gate re-run after an interruption writes to a fresh directory (its logs are opened exclusively)
    seg = adapter.run_segment(adapter.Job(cell, data, stream, backbone, out_dir, r1, last_update=1, identity_gate=True, write_records=True))
    state = dict(seg.model.named_parameters())
    worst = max(float((state[n].detach() - t).abs().max()) for n, t in ref["new_parameters"].items())
    first = json.loads((out_dir / "updates_00000000.jsonl").read_text(encoding="utf-8").splitlines()[0])
    loss_diff = abs(float(first["task_loss"]) - ref["answer_loss"])
    if ref["diversity_loss"] is not None:
        loss_diff = max(loss_diff, abs(float(first["diversity_loss"]) - ref["diversity_loss"]))
    out.update({"max_abs_parameter_difference": worst, "loss_difference": loss_diff, "selection_mismatches": brute_force_selection(mine, batch.tokens)})
    out["passed"] = not out["model_differs"] and worst <= tol and out["loss_difference"] <= tol and not out["selection_mismatches"]
    return out


# --- end-to-end gate at a new size (section 3) -------------------------------------------------------------------------------------------------
def end_to_end(cell: Cell, *, backbone: Any, data: Any, stream: Any, rows: torch.Tensor, out_dir: Path, updates: int, swap_seed: int, facts: int) -> dict[str, Any]:
    """The read swap (no fixed point; swapping twice restores the reads and the logits), the probe-set slot counts and ADDRESS STABLE, end to end at ``cell.slots`` on the rehearsal draw."""
    seg = adapter.run_segment(adapter.Job(cell, data, stream, backbone, out_dir, data.seeds.r1_codes, last_update=updates, identity_gate=True, write_records=False))
    rec = adapter.evaluate_readout(cell, seg.model, data, facts, updates, backbone=backbone, rows=rows, target_seed=0, swap_seed=swap_seed)
    perm = s0eval.swap_permutation(data, facts, swap_seed)
    table = torch.randn(facts, s0core.HIDDEN_WIDTH)
    back = s0model.swap_reads(s0model.swap_reads(table, perm), s0model.inverse(perm))
    answers = s0eval.fact_answers(data, facts)
    probe = rec["probe"]
    stats = rec["panel_statistics"]
    out = {
        "slots": cell.slots, "no_fixed_point": not bool((perm == torch.arange(facts)).any()), "answers_differ": not bool((answers[perm] == answers).any()), "swap_twice_restores": bool(torch.equal(back, table)),
        "probe_distinct_top1": int(probe["distinct_top1"]), "probe_facts": int(probe["probe_facts"]), "probe_slot_count_ok": 1 <= int(probe["distinct_top1"]) <= cell.slots,
        "address_stability_finite": math.isfinite(float(stats["address_stability"])), "read_swap_a_use": rec["read_swap"]["A"]["a_use"] if "read_swap" in rec else None,
    }  # fmt: skip
    out["passed"] = all(out[k] for k in ("no_fixed_point", "answers_differ", "swap_twice_restores", "probe_slot_count_ok", "address_stability_finite"))
    return out
