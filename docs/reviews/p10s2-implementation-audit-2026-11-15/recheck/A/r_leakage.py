"""Re-check A, task 5: leakage end to end on the synthetic stand-ins (studies.p10s2.standins, test seeds only). Builds the bundle with the
real pre-freeze code (prefreeze.build_bundle) and the world (worldio.build_world), then checks with my own code that no evaluation sentence
(E_A, E_B, E_C, E_open), its contraction-expanded form, its reference, or a teacher output on it reaches: the accepted pools, the gold pools,
any replicate stream, any training row of the example bank, the filter fit/check sets, D_cal (calibration), D_con, the router training prompts,
the 220909 tokenizer-record sentences, the rehearsal world's scoring sets. Written by the re-check auditor (Claude Opus 5.5).
Run:  <python> -I <this file> <pinned tree>
"""

import sys
import unicodedata
from pathlib import Path

PIN = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(PIN))
sys.path.insert(0, str(PIN / "src"))
from studies.p10s2 import core  # noqa: E402
from studies.p10s2.rehearsal import rehearsal_world  # noqa: E402
from studies.p10s2.standins import build_synthetic_bundle  # noqa: E402
from studies.p10s2.worldio import RunConfig, build_world  # noqa: E402

OUT: list[str] = []


def say(s: str) -> None:
    OUT.append(s)
    print(s)


def norm(t: str) -> str:
    t = unicodedata.normalize("NFC", t).lower()
    return " ".join("".join(c for c in t if unicodedata.category(c)[0] != "P").split())


core.reset_seed_record()
bundle, rec = build_synthetic_bundle(replicates=2)
world = build_world(bundle, "test", 2, RunConfig.dry(4))
EV = ("E_A", "E_B", "E_C", "E_open")
TR = ("Q_fit", "Q_check", "D_cal", "D_con")
ev_items = [it for n in EV for it in bundle.panels[n]]
ev_keys = {it.key for it in ev_items}
ev_groups = {it.group for it in ev_items if it.group >= 0}
ev_refs = {norm(r) for it in ev_items for rs in it.refs.values() for r in rs}
ev_teacher = {norm(t) for c in core.TASKS for n in EV for t in bundle.teacher_outputs[c][n]}
say(f"evaluation items {len(ev_items)} ({ {n: len(bundle.panels[n]) for n in EV} }); references {len(ev_refs)}; teacher outputs on them (both teachers) {len(ev_teacher)}")
say(f"teacher outputs stored for panels: { {c: sorted(bundle.teacher_outputs[c]) for c in core.TASKS} }")


def report(name: str, pairs: list[tuple[str, str | None]], groups: set[int] | None = None) -> None:
    src_hit = sum(1 for en, _ in pairs if norm(en) in ev_keys)
    tgt_ref = sum(1 for _, t in pairs if t is not None and norm(t) in ev_refs)
    tgt_teacher = sum(1 for _, t in pairs if t is not None and norm(t) in ev_teacher)
    g = len(groups & ev_groups) if groups is not None else "n/a"
    say(f"[{name}] n={len(pairs)}: source = an evaluation sentence: {src_hit}; target = an evaluation reference: {tgt_ref}; target = a teacher output on an evaluation sentence (string equality, informational): {tgt_teacher}; shared eval identity groups: {g}")


for c in core.TASKS:
    report(f"accepted pool {c}", [(x.en, x.target) for x in bundle.accepted[c]], {x.group for x in bundle.accepted[c] if x.group >= 0})
    report(f"gold pool {c}", [(i.en, i.refs[c][0]) for i in bundle.gold_pool[c]], {i.group for i in bundle.gold_pool[c] if i.group >= 0})
for r, s in enumerate(world.streams):
    for c in core.TASKS:
        report(f"replicate {r} T_{c}", [(x.en, x.target) for x in s.t[c]], {x.group for x in s.t[c] if x.group >= 0})
        report(f"replicate {r} Gold_{c}", [(x.en, x.target) for x in s.gold[c]], {x.group for x in s.gold[c] if x.group >= 0})
for n in TR:
    report(f"panel {n} (filter fit/check, calibration, D_con)", [(i.en, None) for i in bundle.panels[n]], {i.group for i in bundle.panels[n] if i.group >= 0})
# every training row of the example bank (examples with a target)
rows = [ex for ex in world.bank.examples.values() if ex.target_len > 0]
row_src = [ex.segments[[k for k, s in enumerate(ex.segments) if s.text == "English:"][0] + 1].text.strip() for ex in rows]
row_tgt = [ex.segments[-2].text.strip() for ex in rows]
report("example bank training rows", list(zip(row_src, row_tgt, strict=True)))
# router training prompts: the stored prompts of T^r (cells.build_routers)
for r, s in enumerate(world.streams):
    prompts = [world.bank.prompt(t, x.en) for t in core.TASKS for x in s.t[t]]
    src = [p.segments[[k for k, sg in enumerate(p.segments) if sg.text == "English:"][0] + 1].text.strip() for p in prompts]
    report(f"router prompts replicate {r}", [(x, None) for x in src])
# tokenizer record sentences (220909) and seen items (220907)
for c in core.TASKS:
    report(f"tokenizer-record sentences {c}", [(x, None) for x in rec["tokenizer_record"][c]["sentences"]])
    report(f"seen-item order {c}", [(k, None) for k in bundle.seen_order[c]])
# the rehearsal world's scoring sets (A-M3 ruling: never an evaluation panel)
rw = rehearsal_world(world)
for n, pd in rw.ctx.panels.items():
    src = [ex.segments[[k for k, sg in enumerate(ex.segments) if sg.text == "English:"][0] + 1].text.strip() for ex in pd.examples]
    report(f"rehearsal scoring panel {n}", [(x, None) for x in src])
ec_src = {norm(getattr(s, "key", "")) for s in rw.ctx.ec.sentences} if hasattr(rw.ctx.ec, "sentences") else set()
say(f"[rehearsal combined set] sentences that are evaluation sentences: {len(ec_src & ev_keys)} of {len(ec_src)}")
say(f"[rehearsal] teacher outputs the rehearsal world carries: { {c: {k: len(v) for k, v in rw.teacher_outputs[c].items()} for c in core.TASKS} } (D_cal only expected)")
say(f"[rehearsal] GEN windows still present in the rehearsal world's context: {len(rw.ctx.windows)} (the registered general-language panel)")
say(f"[G1 pool level, implementation] ok = {rec['g1']['ok']}; problems = {rec['g1']['problems'][:3]}")
say(f"[dropped teacher outputs equal to an evaluation reference] {rec['dropped_eval_equal']}")
Path(__file__).with_suffix(".out.txt").write_text("\n".join(OUT) + "\n")
