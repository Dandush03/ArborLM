# ruff: noqa: E501
"""P10S2 training, the router recipe, the cells of a replicate, scoring sections, composites (ADR-0022 sections 5.4, 6, 6.3, 6.4, 7, 9). Tiny sizes on a synthetic world and test
seeds; every number is a mechanics check, not a result. Self-check only: not independent review, not Astra validation, not human approval."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import torch  # noqa: E402
from test_p10s2_support import dry_world, trained  # noqa: E402

from studies.p10s2 import cells, core, evaluate, memory, retrieval, routing, train  # noqa: E402
from studies.p10s2.memory import MemoryArm, NullArm, SparseStore  # noqa: E402
from studies.p10s2.synthetic import tgen  # noqa: E402


# --- batches and the loss -----------------------------------------------------------------------------------------------------------------------------
def test_batch_plan_concatenates_epochs_and_a_fresh_generator_repeats_it() -> None:
    a = train.batch_plan(7, 5, 4, tgen(81, "order"))
    b = train.batch_plan(7, 5, 4, tgen(81, "order"))
    assert a == b and len(a) == 5 and all(len(x) == 4 for x in a)
    flat = [i for batch in a for i in batch]
    assert sorted(flat[:7]) == list(range(7)) and sorted(flat[7:14]) == list(range(7))  # epoch permutations, the tail carries over
    assert a != train.batch_plan(7, 5, 4, tgen(82, "other order"))


def test_collate_masks_the_prompt_and_reads_each_example_under_its_task() -> None:
    world, _ = dry_world()
    exs = world.train_examples(0, "A")[:3] + world.train_examples(0, "B")[:2]
    ids, labels, reads = train.collate(exs, world.marker_index)
    assert ids.shape == labels.shape == (5, max(len(e.ids) for e in exs))
    for b, e in enumerate(exs):
        assert (labels[b, : e.prompt_len - 1] == -100).all()  # prompt positions are masked
        assert labels[b, e.prompt_len - 1 : len(e.ids) - 1].tolist() == list(e.ids[e.prompt_len :])  # the target is the translation and the newline
        assert (labels[b, len(e.ids) - 1 :] == -100).all()
        assert {t for _p, t, _j in reads[b]} == {e.task} and (e.marker, e.task, world.marker_index) in reads[b]
    assert train.reads_of(exs[0], [], world.marker_index) == []  # route "none": no read


def test_the_pipeline_can_fit_a_few_examples_and_training_is_deterministic() -> None:
    world, _ = dry_world()
    ex = world.train_examples(0, "A")[:8]
    plan = core.SeedPlan("test", 0)

    def run() -> tuple[train.TrainRecord, str]:
        arm = MemoryArm(SparseStore.new(world.cfg.width, 16, plan.gen(0, "store")), world.layer, world.codes(0))
        rec = train.train_arm(world.student, arm, ex, 150, 8, 0.1, plan.gen(2, "order"), world.marker_index)
        return rec, arm.state_hash()

    r1, h1 = run()
    r2, h2 = run()
    assert r1.status == "completed" and r1.last_loss < r1.first_loss - 0.5  # mechanics only: the read, the gate and the loss are wired so that the store's loss goes down (the stand-in student is a random network)
    assert (r1.losses, h1) == (r2.losses, h2)  # the same updates repeat bit-identically on CPU
    assert r1.rows_per_update == 8 and r1.trainable_parameters == 16 * (core.KEY_WIDTH + world.cfg.width) + 1
    lora = memory.new_lora_arm(world.cfg, 4, plan.gen(8, "lora"))
    rl = train.train_arm(world.student, lora, ex, 150, 8, 0.01, plan.gen(2, "order"), world.marker_index)
    assert rl.last_loss < 0.6 * rl.first_loss  # an adapter on the same stand-in fits much faster, as the structural asymmetry of section 7 says


def test_replay_rows_are_added_to_every_batch_and_use_their_own_order_stream() -> None:
    world, _ = dry_world()
    plan = core.SeedPlan("test", 0)
    a, b = world.train_examples(0, "A"), world.train_examples(0, "B")
    arm = MemoryArm(SparseStore.new(world.cfg.width, 16, plan.gen(0, "store")), world.layer, world.codes(0))
    rec = train.train_arm(world.student, arm, b, 3, 4, 0.01, plan.gen(2, "order"), world.marker_index, replay=a, replay_rows=4, replay_generator=plan.gen(2, "replay order"))
    assert rec.batch == 4 and rec.replay_rows == 4 and rec.rows_per_update == 8  # twice the rows per update; reported
    core.reset_seed_record()
    plan.gen(2, "order")
    plan.gen(2, "replay order")
    assert [u.seed for u in core.seed_record()] == [plan.seed(2), plan.seed(2)]  # a fresh +2 generator also orders the replayed rows
    core.reset_seed_record()


def test_a_non_finite_loss_gives_a_failed_record_and_dependants_are_skipped() -> None:
    world, _ = dry_world()
    plan = core.SeedPlan("test", 0)
    arm = MemoryArm(SparseStore.new(world.cfg.width, 16, plan.gen(0, "store")), world.layer, world.codes(0))
    with torch.no_grad():
        arm.store.values[0].fill_(float("nan"))
        arm.store.gates[0].fill_(1.0)
    rec = train.train_arm(world.student, arm, world.train_examples(0, "A")[:8], 3, 4, 0.01, plan.gen(2, "order"), world.marker_index)
    assert rec.status == "failed" and "non-finite" in rec.error and rec.updates == 1
    with tempfile.TemporaryDirectory() as d:
        out = cells.train_replicate(world, 0, Path(d), only={"r0/ST1/AB", "r0/MAF/AB"})
        assert out["r0/ST1/AB"]["status"] == "completed" and "r0/MAF/AB" in out
    bad = {"r0/ST1/AB": {"status": "failed"}}
    parent_missing = [c for c in cells.replicate_cells(0) if c.depends_on == "r0/ST1/AB"]
    assert {c.group for c in parent_missing} == {"MAF", "MSEQ"}  # these are skipped when ST1 fails
    assert bad


def test_gradient_reach_and_device_selection() -> None:
    world, _ = dry_world()
    arm = MemoryArm(SparseStore.new(world.cfg.width, 16, tgen(83, "reach")), world.layer, world.codes(0))
    r = train.gradient_reach(world.student, arm, world.train_examples(0, "A")[:4], world.marker_index)
    assert r["arm_with_gradient"] == r["arm_parameters"] == 3 and r["student_with_gradient"] == 0
    assert train.select_device("cpu").type == "cpu"
    with pytest.raises(ValueError):
        train.select_device("tpu")
    import os

    os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
    try:
        with pytest.raises(RuntimeError):
            train.select_device("mps")  # a fallback must be an error (gate G4)
    finally:
        del os.environ["PYTORCH_ENABLE_MPS_FALLBACK"]
    ok = train.update_agreement([1.0, 2.0], [1.0005, 2.0], [torch.ones(3)], [torch.ones(3) * (1 + 5e-5)])
    assert ok["ok"] and not train.update_agreement([1.0], [1.01], [torch.ones(3)], [torch.ones(3)])["ok"] and not train.update_agreement([1.0], [1.0], [torch.ones(3)], [torch.ones(3) * 1.001])["ok"]


# --- the router recipe (section 5.4) -----------------------------------------------------------------------------------------------------------------
def test_class_counts_balance_with_the_remainder_to_none() -> None:
    assert routing.class_counts(64, 3) == [21, 21, 22] and routing.class_counts(64, 2) == [32, 32] and routing.class_counts(10, 3) == [3, 3, 4]


def test_router_recipe_prefix_lengths_seed_order_and_scratch_initialization() -> None:
    world, _ = dry_world()
    plan = core.SeedPlan("test", 0)
    spec = world.router_spec
    prompts = {t: [world.bank.prompt(t, x.en) for x in world.streams[0].t[t]] for t in core.TASKS}
    zero = routing.RouterSpec(0, spec.batch, spec.lr, spec.none_prefixes, spec.full_length, spec.prefix_tokens)
    r0, rec0 = routing.train_router(world.student, world.layer, core.TASKS, prompts, world.wiki_train_ids, plan, zero)
    # initialization: the projection, then the keys, from one fresh +3 generator
    g = plan.gen(3, "check")
    proj = 0.02 * torch.randn(core.KEY_WIDTH, world.cfg.width, generator=g)
    keys = 0.02 * torch.randn(3, core.KEY_WIDTH, generator=g)
    assert torch.equal(r0.proj, proj) and torch.equal(r0.keys, keys)
    r, rec = routing.train_router(world.student, world.layer, core.TASKS, prompts, world.wiki_train_ids, plan, spec)
    assert rec["prefixes"] == spec.none_prefixes and rec["full_length_prefixes"] == spec.full_length and rec["class_counts"] == routing.class_counts(spec.batch, 3)
    lengths = [len(e.prompt_ids) for t in core.TASKS for e in prompts[t]]
    assert 1 <= rec["cut_length_min"] <= max(lengths)  # the cut prefixes take their length from the task prompts
    r_again, _ = routing.train_router(world.student, world.layer, core.TASKS, prompts, world.wiki_train_ids, plan, spec)
    assert r.state_hash() == r_again.state_hash() and r.state_hash() != r0.state_hash()  # trained from the same initialization every time, not continued
    one, _ = routing.train_router(world.student, world.layer, ("A",), {"A": prompts["A"]}, world.wiki_train_ids, plan, spec)
    assert one.classes == ("A", "none") and r.classes == ("A", "B", "none")  # a router knows the set of tasks of its snapshot
    assert rec0["updates"] == 0


def test_router_separates_keyword_prompts_and_false_triggers_are_counted() -> None:
    world, _ = dry_world()
    plan = core.SeedPlan("test", 0)
    prompts = {t: [world.bank.prompt(t, x.en) for x in world.streams[0].t[t]] for t in core.TASKS}
    spec = routing.RouterSpec(300, 24, 0.05, world.router_spec.none_prefixes, world.router_spec.full_length, world.router_spec.prefix_tokens)
    r, _ = routing.train_router(world.student, world.layer, core.TASKS, prompts, world.wiki_train_ids, plan, spec)
    ctx = world.ctx
    fit = routing.route_accuracy(r, world.student, world.layer, {c: prompts[c] for c in core.TASKS}, [])
    assert fit["A"] >= 0.95 and fit["B"] >= 0.95  # the router learns its classes on its own training prompts
    acc = routing.route_accuracy(r, world.student, world.layer, {c: ctx.panels["E_" + c].examples for c in core.TASKS}, [w.ids[: ctx.decision_index + 1] for w in ctx.windows])
    assert set(acc) == {"A", "B", "general"} and min(acc.values()) > 1 / 3  # held-out prompts: above chance on this random stand-in student (a mechanics check, not the 0.99 of the annotation)
    marker = [w for w in ctx.windows if w.stratum == "marker"]
    ft = routing.false_triggers(r, world.student, world.layer, [w.ids for w in marker], [w.marker_end for w in marker])
    assert ft["n"] == len(marker) and 0 <= ft["count"] <= ft["n"]
    assert routing.false_triggers(r, world.student, world.layer, [], [])["n"] == 0


# --- one replicate's cells (the shared trained fixture) -----------------------------------------------------------------------------------------------
def test_all_eighteen_cells_trained_and_scored_with_the_right_sections() -> None:
    world, _, d, tr, sc = trained()
    assert len(tr) == 18 and all(v["status"] == "completed" for v in tr.values())
    for label, rec in sc.items():
        g = label.split("/")[1]
        s = rec["scores"][label]
        assert set(s["panels"]) == {"E_A", "E_B"}
        assert ("ablations" in s) == (g in ("ST1", "MAF", "MII", "MSEQ", "MJOINT", "MAGOLD"))  # the five ablations on the 11 memory cells; E-table has none
        assert ("gen" in s) == (g in ("ST1", "MAF", "MII", "MSEQ", "MJOINT", "LSEQ"))  # GEN for every ST1 and stage-2 snapshot, and L-seq for comparison
        assert ("combined" in s) == (g in ("MAF", "MII", "MJOINT", "LSEQ", "LJOINT"))
        assert ("learned_route" in s) == (g in ("ST1", "MAF"))
        assert ("seen" in s) == (g in ("ST1", "MAF"))
        if "gen" in s:
            assert s["gen_by_construction"]["bit_identical_to_student"] is True and s["gen_by_construction"]["label"] == "BY CONSTRUCTION"
            assert ("always_on_loss_increase" in s["gen"]) == (g in ("MAF", "LSEQ"))  # the always-on diagnostic: M-append-frozen and L-seq only
    assert "r0/MAF/AB@append" in sc["r0/MAF/AB"]["scores"]  # the append point is scored before any update
    ab = sc["r0/MAF/AB"]["scores"]["r0/MAF/AB"]["ablations"]["E_B"]
    assert set(ab) == {"subsample_indices", "unablated", "off", "value_perm", "code_perm", "marker_only", "words_only"} and len(ab["subsample_indices"]) == core.CFG["dry"]["ablation_subsample"]


def test_first_stage_of_the_append_arm_is_frozen_bit_for_bit_and_the_append_cost_is_measured() -> None:
    _, _, d, tr, sc = trained()
    for o in core.ORDERS:
        ex = sc[f"r0/MAF/{o}"]["extras"]["append"]
        assert ex["stage0_hash_equals_v1"] is True  # keys, values and gate of the first-stage rows after training equal V1's
        assert 0.0 <= ex["interference"]["weight_on_new_rows"] <= 1.0 and ex["first_stage_rows"] == core.CFG["dry"]["rows_per_stage"]
    # M-ii changes the first-stage rows, and reports how much
    c = sc["r0/MII/AB"]["extras"]["consolidation"]
    assert set(c) >= {"d_con", "rejected", "relative_change", "changed_row_share", "g1_change", "below_floor", "published"} and c["relative_change"] > 0.0
    assert c["scored_on"] == "selected on D_con, then confirmed on E"
    assert c["below_floor"] == (c["relative_change"] < core.CFG["training"]["modification_floor"]) and c["published"] == (not c["rejected"])


def test_seeds_of_the_training_uses_follow_the_table() -> None:
    world, _ = dry_world()
    core.reset_seed_record()
    with tempfile.TemporaryDirectory() as d:
        cells.train_replicate(world, 0, Path(d))
    base = core.SeedPlan("test", 0).base
    offs = [u.seed - base for u in core.seed_record()]
    assert offs.count(0) == 4 and offs.count(6) == 2 and offs.count(7) == 1 and offs.count(8) == 3 and offs.count(9) == 2  # +0: ST1 x2, MA-gold x2; +6: both orders; +7 M-joint; +8: LoRA-1 x2 and L-joint; +9: E-table x2
    assert set(offs) <= {0, 2, 6, 7, 8, 9} and offs.count(2) == 18 + 2  # one fresh batch-order generator per cell, plus M-ii's replay order
    core.reset_seed_record()


def test_oracle_route_gives_ordinary_text_unchanged_logits_for_every_arm_kind() -> None:
    world, _, d, tr, _ = trained()
    w = world.ctx.windows[0]
    ids = torch.tensor([list(w.ids)])
    base = world.student(ids)
    for label in ("r0/ST1/AB", "r0/MAF/AB", "r0/LORA1/AB", "r0/ETABLE/A", "r0/MJOINT/-"):
        arm = cells.load_arm(world, 0, d, label)
        out = memory.run_student(world.student, arm, ids, [[]])  # route "none": no read and no adapter
        assert torch.equal(out, base), label


def test_memory_off_equals_the_student_and_a_read_changes_the_prompt_logits() -> None:
    world, _, d, tr, _ = trained()
    arm = cells.load_arm(world, 0, d, "r0/ST1/AB")
    assert isinstance(arm, MemoryArm)
    with torch.no_grad():  # give the store a non-trivial read (the 4-update store is small)
        arm.store.values[0].copy_(torch.randn(arm.store.values[0].shape, generator=tgen(84, "values")))
        arm.store.gates[0].fill_(1.0)
    ex = world.ctx.panels["E_A"].examples[0]
    ids = torch.tensor([list(ex.prompt_ids)])
    reads = [train.reads_of(ex, ["A"], world.marker_index)]
    base = world.student(ids)
    assert not torch.equal(memory.run_student(world.student, arm, ids, reads), base)
    assert torch.equal(memory.run_student(world.student, arm, ids, reads, memory.Ablation("off")), base)
    a = evaluate.generate(world.ctx, arm, ex, ["A"], memory.Ablation("off"))
    b = evaluate.generate(world.ctx, NullArm(), ex, [])
    assert a == b


def test_general_quality_with_no_router_read_is_exactly_the_student() -> None:
    world, _, d, tr, _ = trained()
    arm = cells.load_arm(world, 0, d, "r0/MAF/AB")
    res = evaluate.general_quality(world.ctx, arm, None)  # no router: route "none" on every window
    assert res["loss_increase"] == 0.0 and res["false_trigger_count"] == {"marker": 0, "ordinary": 0} and res["passes"] is True
    assert res["stratum_sizes"]["marker"] == core.CFG["dry"]["general_windows_marker_like"]
    assert evaluate.general_by_construction(world.ctx, arm)["bit_identical_to_student"]


def test_assembled_composites_equal_their_parts_by_construction() -> None:
    world, _, d, tr, sc = trained()
    a = cells.assembled_scores(world, 0, d)
    assert a["label"] == "BY CONSTRUCTION"
    for name, group in (("M-i-separate", "ST1"), ("L-sep", "LORA1")):
        assert a[name]["E_A"]["mean"] == sc[f"r0/{group}/AB"]["scores"][f"r0/{group}/AB"]["panels"]["E_A"]["mean"]
        assert a[name]["E_B"]["mean"] == sc[f"r0/{group}/BA"]["scores"][f"r0/{group}/BA"]["panels"]["E_B"]["mean"]
    for name in ("M-i-separate", "L-sep"):
        assert a[name]["combined"]["C1"]["n"] == len(world.ctx.ec.sentences) and a[name]["combined"]["arm"] in ("memory", "lora")  # scored on the combined tasks (addendum section 7)


def test_retrieval_baselines_and_ensemble() -> None:
    world, _ = dry_world()
    rr = cells.retrieval_scores(world, 0)
    for c in core.TASKS:
        assert rr[c]["R-exact"]["hits"] == 0  # zero hits on held-out items: the panels are held out
        assert 0.0 <= rr[c]["R-gloss"]["mean"] <= 1.0 and rr[c]["R-icl"]["prompt_tokens_mean"] > 0 and rr[c]["R-nn"]["comparisons_per_item"] == len(world.streams[0].t[c])
    items = world.streams[0].t["A"]
    lex = retrieval.gloss_lexicon(items)
    assert lex and all(isinstance(k, str) for k in lex)
    idx = retrieval.TfidfIndex(items)
    assert items[idx.nearest(items[3].en)[0]].en == items[3].en
    ens = retrieval.ensemble_scores({"A": ["x"], "B": ["y"]}, {"A": [["x"]], "B": [["y"]]}, lambda c, _i: c)
    assert ens == {"A": 1.0, "B": 1.0}
    assert retrieval.ensemble_scores({"A": ["x"], "B": ["y"]}, {"A": [["x"]], "B": [["y"]]}, lambda c, _i: "none") == {"A": 0.0, "B": 0.0}  # a wrongly routed item scores 0
    assert retrieval.ensemble_scores({"A": ["x"], "B": ["y"]}, {"A": [["x"]], "B": [["y"]]}, lambda c, _i: "B")["A"] == 0.0


def test_stage0_teacher_and_the_oracle_routed_ensemble_equal_the_teacher() -> None:
    from studies.p10s2 import stages

    world, _ = dry_world()
    s0 = cells.stage0_scores(world)
    for c in core.TASKS:
        assert stages.evaluate_mean_teacher(world, c) == s0["teacher"]["E_" + c]["mean"]  # section 11.3: a difference would be ENGINEERING-FAILURE
        assert s0["student"]["E_" + c]["panel"]["mean"] >= 0.0 and "exact_rate" in s0["teacher"]["E_" + c]


def test_truncation_percentile_and_work_counts_are_analytical() -> None:
    assert evaluate.truncation_percentile(list(range(1, 201))) == 199  # the 99.5th percentile of 200 values
    assert evaluate.truncation_percentile([]) == 0
    world, _, d, tr, sc = trained()
    arm = cells.load_arm(world, 0, d, "r0/MAF/AB")
    w = evaluate.active_work(arm, reads_per_item=10.0, generated_tokens_per_item=5.0)
    assert w["key_products_per_read"] == 2 * core.CFG["dry"]["rows_per_stage"] and w["value_rows_read_per_item"] == 80.0 and w["type"] == "analytical count"
    assert w["value_parameters_read_per_generated_token"] == 80.0 * world.cfg.width / 5.0
    lw = evaluate.active_work(cells.load_arm(world, 0, d, "r0/LORA1/AB"), 10.0, 5.0)
    assert lw["adapter_parameters_applied_per_generated_token"] > 0
    t = evaluate.timing_benchmark(lambda: None, repetitions=3)
    assert t["repetitions"] == 3 and "descriptive" in t["type"]
