"""C1b (auditor, Opus 5.5): re-check of the G6 item of c1 after my own false positive (c1 flagged ``addition.last_query`` as a
"fact-sized tensor" because 128 sites x 16 = 2,048 elements = the number of facts; it is the batch's query, not a fact table).
Here: after 20 A1 updates on TEST seeds p9ii-test-7, (a) logits on fixed tokens before and after replacing the trainer's injection
and scrambling the data's fact answers; (b) every tensor attribute of every module with its shape; (c) logits of a model rebuilt
from the state_dict alone (no trainer, no data object) equal the trained model's. Also A1-S and A5-D.

usage: c1b_g6_recheck.py EXPERIMENTS_ROOT SCRATCH_DIR
"""
import sys
from pathlib import Path

import torch

from studies.p9 import controls, data as p9data
from studies.p9 import core as p9core
from studies.p9ii import core, model, train
from studies.p9ii.diagnostics import build_probe
from studies.p9i.train import training_stream_for

ROOT, SCRATCH = Path(sys.argv[1]), Path(sys.argv[2])
train.configure()
seeds = core.test_seeds(7)
study = p9data.build_study_data(seeds, p9core.load_trained_corpus(ROOT))
backbone = controls.load_backbone(p9core.PRIMARY_PARENT, ROOT)[0]
stream = training_stream_for(study, 2048)
tok = stream.batch(3).tokens[:, :63]
for arm in ("A1", "A1-S", "A2", "A5-D", "A5-C", "A4"):
    j = train.TrainJob(cell=core.make_cell(arm, 4096), hyper=core.Hyper(lambda_=1.0, u_pre=8.0, k0_fraction=0.125, mu=1.0), updates=8192, mode="calibration", data=study, stream=stream, backbone=backbone,
                       out_dir=SCRATCH / "c1b" / arm, init_seed=919101, r1_seed=seeds.r1_codes, target_seed=core.target_seed(seeds, 0), stream_seed=core.stream_seed(seeds, 0), snapshots=())
    m = model.build_model(arm, 4096, 919101, backbone)
    if arm == "A5-C":
        m.addition.init_centre(train.initial_centre_rows(m, stream))
    t = train.Trainer(j, m, build_probe(study, 2048))
    for u in range(1, 21):
        t.step(stream.batch(u))
    m.eval()
    with torch.no_grad():
        before = m(tok)[0].clone()
    t.injection = torch.randperm(4096)[:2048] if t.injection is not None else None
    study.facts.answer[:] = study.facts.answer.flip(0)
    with torch.no_grad():
        after = m(tok)[0]
    study.facts.answer[:] = study.facts.answer.flip(0)
    attrs = [(f"{n}.{a}", tuple(v.shape)) for n, mod in m.named_modules() for a, v in vars(mod).items() if torch.is_tensor(v) and not n.startswith("backbone")]
    fresh = model.build_model(arm, 4096, 1, backbone, seed_rng=False)
    fresh.load_state_dict(m.state_dict())
    fresh.eval()
    with torch.no_grad():
        rebuilt = fresh(tok)[0]
    print(arm, "logits unchanged under changed injection/fact table:", torch.equal(before, after), "| rebuilt from state_dict alone equal:", torch.equal(before, rebuilt), "| tensor attributes:", attrs, "| state:", [k for k in m.state_dict() if not k.startswith("backbone")])
