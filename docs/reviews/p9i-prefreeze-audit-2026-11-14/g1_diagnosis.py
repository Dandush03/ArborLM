"""G1 (auditor, Opus 5.5): the attempt-1 G4 "gradient reach failed for R2" diagnosis, reproduced on
rehearsal draws 0 and 2 (never the registered seeds) with the verified B101 backbone, plus the DRY profile
before and after the fix (test seeds, synthetic backbone).

For each draw: the fact ids of the first 8 Panel A rows (the attempt-1 harness input), how many fall in
the 4,096-slot cell's 2,048 facts, how many identifiers hit the R2 lookup table, and the gradient reach of
R2 under my own loss (256-way cross-entropy at the 8 answer sites, my code). Then the same for the new
``stages.gate_contexts`` input and for every arm. Also the row structure of Panel A (why 8 rows can miss
2,048 of 32,768 facts so easily).

Usage: PYTHONPATH=. uv run --locked python <this> <experiments root>
"""
import sys
from pathlib import Path

import torch
from torch.nn import functional as F

from studies.p9 import controls, data as d
from studies.p9 import core as p9core
from studies.p9 import model as p9model
from studies.p9i import core, model, stages, train

torch.set_num_threads(4)
ROOT = Path(sys.argv[1])
SITES = list(core.ANSWER_SITE_POSITIONS)
FACTS_4096 = core.FACTS_PROPORTIONAL[4096]


def my_reach(net, tokens):
    """Non-zero finite gradient per trainable parameter under my own loss."""
    net.zero_grad(set_to_none=True)
    logits, _ = net(tokens[:, :-1])
    target = tokens[:, 1:][:, SITES]
    F.cross_entropy(logits[:, SITES].reshape(-1, 256), target.reshape(-1)).backward()
    out = {n: (p.grad is not None and bool(p.grad.isfinite().all()) and bool((p.grad != 0).any())) for n, p in net.named_parameters() if p.requires_grad}
    stray = [n for n, p in net.named_parameters() if not p.requires_grad and p.grad is not None]
    net.zero_grad(set_to_none=True)
    return out, stray


def row_structure(stream, facts, label):
    ids = stream.fact_ids
    any_in = (ids < facts).any(dim=1)
    all_in = (ids < facts).all(dim=1)
    spread = (ids.max(1).values - ids.min(1).values).float()
    first_hit = int(any_in.nonzero()[0]) if bool(any_in.any()) else None
    print(f"  [{label}] Panel A rows {ids.shape[0]}; rows with >=1 fact < {facts}: {int(any_in.sum())} ({float(any_in.float().mean()):.4f}); rows with all 8 < {facts}: {int(all_in.sum())}; first row holding such a fact: {first_hit}; median within-row id spread {float(spread.median()):.0f}")
    first8 = ids[:8]
    print(f"  [{label}] first 8 rows: ids min {int(first8.min())} max {int(first8.max())}; facts < {facts}: {int((first8 < facts).sum())} of {first8.numel()}")


def draw_check(draw, bb, corpus):
    seeds = core.rehearsal_draw_seeds(draw)
    core.check_seed_set("rehearsal", seeds.name)
    study = d.build_study_data(seeds, corpus)
    print(f"draw {draw} ({seeds.name}): trained {study.facts.trained}, size {study.facts.size}")
    row_structure(study.streams["panel_a"], FACTS_4096, "real size")
    lut = train.fact_lut_for(study, FACTS_4096)
    old = study.streams["panel_a"].tokens[:8]
    hits_old = int((lut[p9model.identifier_codes(old[:, : core.INPUT_LENGTH])] >= 0).sum())
    net = model.build_model("R2", 4096, core.INIT_SEEDS[0], bb, fact_lut=lut, r1_seed=study.seeds.r1_codes)
    r_old, stray = my_reach(net, old)
    impl_old = train.gradient_reach(net, old)
    print(f"  OLD harness: LUT hits {hits_old} of 64; R2 reach (mine) {r_old} stray {stray}; implementer gradient_reach agrees: {impl_old['reached'] == r_old}")
    tok, ids = stages.gate_contexts(study, FACTS_4096)
    hits_new = int((lut[p9model.identifier_codes(tok[:, : core.INPUT_LENGTH])] >= 0).sum())
    slots_ok = bool(torch.equal(lut[p9model.identifier_codes(tok[:, : core.INPUT_LENGTH])], ids))
    print(f"  NEW harness: ids min {int(ids.min())} max {int(ids.max())}; LUT hits {hits_new} of 64; LUT slot == fact id for all 64: {slots_ok}")
    for arm in core.ARMS:
        n = model.build_model(arm, 4096, core.INIT_SEEDS[0], bb, fact_lut=lut if arm == "R2" else None, r1_seed=study.seeds.r1_codes)
        r_new, s_new = my_reach(n, tok)
        r_o, s_o = my_reach(n, old)
        print(f"    {arm:5s} new: all reached {all(r_new.values())} ({len(r_new)} trainable) stray {s_new} | old: all reached {all(r_o.values())}")


def dry_check(sizes, label):
    study = d.build_study_data(core.test_seeds(0), stages.SYNTHETIC_CORPUS, sizes=sizes)
    facts = stages.DRY_FACTS[4096]
    print(f"DRY profile {label}: trained {study.facts.trained}, cell facts {facts} ({facts / study.facts.trained:.4f} of trained; registered 4,096-slot proportion {FACTS_4096 / core.FACTS_PROPORTIONAL[65536]:.4f})")
    row_structure(study.streams["panel_a"], facts, label)
    bb = controls.synthetic_backbone()
    lut = train.fact_lut_for(study, facts)
    old = study.streams["panel_a"].tokens[:8]
    net = model.build_model("R2", 4096, core.INIT_SEEDS[0], bb, fact_lut=lut, r1_seed=study.seeds.r1_codes)
    r, _ = my_reach(net, old)
    print(f"  OLD harness on this profile: R2 all reached {all(r.values())}")


if __name__ == "__main__":
    train.configure()
    corpus = p9core.load_trained_corpus(ROOT)
    bb = controls.load_backbone(core.PRIMARY_PARENT, ROOT)[0]
    for draw in (0, 2):
        draw_check(draw, bb, corpus)
    dry_check(d.DataSizes(main_trained=512, unseen=64, lane_d_per_set=128), "at dd8b205 (512 trained)")
    dry_check(stages.DRY_SIZES, "at 0e0fbfb (2,048 trained)")
