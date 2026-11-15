import argparse, torch
from studies.p9i import stages, train, model, core
a = argparse.Namespace(dry=False, synthetic_backbone=False, mode="registered", draw=0, experiments_root=None)
study = stages.study_data(a)
bb = stages.backbone_for(a, core.PRIMARY_PARENT)
tok = study.streams["panel_a"].tokens[:8]
lut = train.fact_lut_for(study, 2048)
net = model.build_model("R2", 4096, core.INIT_SEEDS[0], bb, fact_lut=lut, r1_seed=study.seeds.r1_codes)
r = train.gradient_reach(net, tok)
print(r["reached"])
st = study.streams["panel_a"]
print([f for f in dir(st) if not f.startswith("_")])
for name in ("fact_ids","facts","fact_index"):
    if hasattr(st, name):
        v = getattr(st, name)[:8]; print(name, v.min().item(), v.max().item(), (v < 2048).sum().item(), v.numel())
print("panel rows", st.tokens.shape)
