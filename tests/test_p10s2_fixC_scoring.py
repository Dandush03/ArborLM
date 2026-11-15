# ruff: noqa: E501
"""P10S2 fix lane C, scoring and routing (audit C-M6 with the lead's ruling, A-M5, C-m7, R-icl BOS, single-reference scores, E_open guard). Tiny sizes on the synthetic world and test seeds (229001-229999);
every number is a mechanics check, not a result. Self-check only: not independent review, not Astra validation, not human approval."""

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import torch  # noqa: E402
from test_p10s2_classes import study  # noqa: E402
from test_p10s2_support import dry_world, trained  # noqa: E402

from studies.p10s2 import analysis, cells, core, evaluate, retrieval, routing  # noqa: E402
from studies.p10s2.memory import MemoryArm  # noqa: E402
from studies.p10s2.synthetic import tgen  # noqa: E402


class PositionOnlyRouter:
    """What the audit's C-M6 describes: a router whose decision depends only on the position at which it is taken. Trained under the registered recipe, "none" prefixes of exactly 64 tokens are
    labelled none and task prompts are shorter, so it stays silent at token 64 and triggers everywhere else."""

    tasks = ("A", "B")

    def __init__(self, decision_index: int) -> None:
        self.decision_index = decision_index  # 63 in the registered run, 7 in the dry world

    def predict(self, h: torch.Tensor) -> list[str]:
        return ["none" if int(x[0]) == self.decision_index else "A" for x in h]


def _position_features(student: Any, layer: int, sequences: Any, positions: Any = None, batch: int = 64) -> torch.Tensor:
    return torch.tensor([[float(positions[i] if positions is not None else len(s) - 1)] for i, s in enumerate(sequences)])


def loud_maf_arm() -> MemoryArm:
    world, _, d, _, _ = trained()
    arm = cells.load_arm(world, 0, d, "r0/MAF/AB")
    assert isinstance(arm, MemoryArm)
    g = tgen(401, "loud arm values")
    with torch.no_grad():
        for v in arm.store.values:
            v.copy_(-30.0 * torch.randn(v.shape, generator=g))  # a perturbation that raises the loss of this random stand-in student (seed 401 found by a scan; a mechanics fixture, not a result)
        for gate in arm.store.gates:
            gate.fill_(1.0)
    return arm


def test_a_position_only_router_now_fails_gen(monkeypatch: pytest.MonkeyPatch) -> None:
    world, _, _, _, _ = trained()
    ctx = world.ctx
    arm = loud_maf_arm()
    monkeypatch.setattr(evaluate, "hidden_at_ends", _position_features)
    res = evaluate.general_quality(ctx, arm, PositionOnlyRouter(ctx.decision_index))  # type: ignore[arg-type]
    marker = [w for w in ctx.windows if w.stratum == "marker"]
    off_decision = [w for w in marker if w.marker_end != ctx.decision_index]
    assert off_decision and all(0 <= w.marker_end <= ctx.decision_index for w in marker)  # the first marker-like string ends within the decision prefix; here some end before the decision token
    assert res["false_trigger_count"] == {"marker": 0, "ordinary": 0}  # at token 64 the position-only router is silent on every window: the registered measurement alone would pass
    assert res["loss_increase"] == 0.0 and res["passes_registered_decision"] is True
    assert res["false_trigger_count_first_marker"]["marker"] == len(off_decision) and res["false_trigger_count_first_marker"]["ordinary"] == 0
    assert res["loss_increase_first_marker"] > core.CFG["gates"]["gen_loss_margin"]  # at the first marker string it triggers wherever that string does not end at the decision token
    assert res["passes_first_marker_decision"] is False and res["passes"] is False  # the existing 0.02 threshold must hold under both: GEN fails
    rec = core.jsonable(res)
    verdict = analysis.C.gen_gate(rec["loss_increase"], rec["loss_increase_first_marker"])
    assert verdict is False and analysis.C.gen_gate(rec["loss_increase"]) is True  # the same record under the old single decision would have passed


def test_a_router_that_never_triggers_passes_both_decisions_and_the_diagnostic_stays_a_diagnostic() -> None:
    world, _, d, _, _ = trained()
    arm = cells.load_arm(world, 0, d, "r0/MAF/AB")
    res = evaluate.general_quality(world.ctx, arm, None)
    assert res["loss_increase"] == 0.0 and res["loss_increase_first_marker"] == 0.0 and res["passes"] is True
    assert res["false_trigger_count_first_marker"] == {"marker": 0, "ordinary": 0}
    assert res["nll_router_first_marker"] == res["nll_base"]


def test_gen_has_the_second_decision_in_every_scored_snapshot_and_the_ordinary_stratum_is_unchanged() -> None:
    world, _, _, _, sc = trained()
    for label, rec in sc.items():
        g = rec["scores"][label].get("gen") if rec.get("scores") else None
        if g is not None:
            assert {"loss_increase", "loss_increase_first_marker", "passes", "passes_registered_decision", "passes_first_marker_decision", "false_trigger_count_first_marker"} <= set(g), label
    router = cells.build_routers(world, 0)[("A", "B")][0]
    arm = cells.load_arm(world, 0, trained()[2], "r0/MAF/AB")
    res = evaluate.general_quality(world.ctx, arm, router)
    ordinary = [w for w in world.ctx.windows if w.stratum == "ordinary"]
    assert ordinary and res["stratum_sizes"]["ordinary"] == len(ordinary)
    assert res["passes"] == (res["passes_registered_decision"] and res["passes_first_marker_decision"])


# --- A-M5: a fresh +3 generator after the initialization -----------------------------------------------------------------------------------------------
def test_the_router_initialization_and_its_sampling_use_two_fresh_plus_three_generators() -> None:
    world, _ = dry_world()
    plan = core.SeedPlan("test", 0)
    prompts = {t: [world.bank.prompt(t, x.en) for x in world.streams[0].t[t]] for t in core.TASKS}
    spec = routing.RouterSpec(0, world.router_spec.batch, world.router_spec.lr, world.router_spec.none_prefixes, world.router_spec.full_length, world.router_spec.prefix_tokens)
    core.reset_seed_record()
    r, rec = routing.train_router(world.student, world.layer, core.TASKS, prompts, world.wiki_train_ids, plan, spec)
    uses = [u for u in core.seed_record() if u.seed == plan.seed(3)]
    assert [u.purpose for u in uses] == ["router initialization", "router sampling"]  # two fresh generators on the +3 seed, in this order
    init = plan.gen(3, "check initialization")
    proj = 0.02 * torch.randn(core.KEY_WIDTH, world.cfg.width, generator=init)
    keys = 0.02 * torch.randn(3, core.KEY_WIDTH, generator=init)
    assert torch.equal(r.proj, proj) and torch.equal(r.keys, keys)
    # the sampling generator starts from the beginning of the +3 stream: the prefixes come from a fresh generator, not from the one that drew the initialization
    pieces = routing.none_pieces(world.wiki_train_ids, spec.prefix_tokens)
    samp = plan.gen(3, "check sampling")
    perm = torch.randperm(len(pieces), generator=samp).tolist()
    assert rec["held_out_piece_indices"] == perm[spec.none_prefixes : spec.none_prefixes + spec.general_prefix_count]
    core.reset_seed_record()


# --- C-m7: route accuracy is not measured on the GEN windows -------------------------------------------------------------------------------------------
def test_route_accuracy_general_prefixes_are_unseen_train_pieces_not_gen_windows() -> None:
    world, _, _, _, _ = trained()
    routers = cells.build_routers(world, 0)
    rec = cells.router_record(world, 0, routers)
    gen_ids = {tuple(w.ids[: world.ctx.decision_index + 1]) for w in world.ctx.windows}
    pieces = routing.none_pieces(world.wiki_train_ids, world.router_spec.prefix_tokens)
    for key, r in rec.items():
        held = routers[tuple(key)][1]["held_out_piece_indices"]
        assert r["general_prefixes"]["n"] == len(held) and "general" in r["accuracy"]
        assert all(tuple(pieces[i]) not in gen_ids for i in held)  # none of them is a GEN-window prefix
    for tasks, (_router, trec) in routers.items():
        assert trec["held_out_piece_indices"] and len(set(trec["held_out_piece_indices"])) == len(trec["held_out_piece_indices"])
        pick_n = world.router_spec.none_prefixes
        samp = core.SeedPlan("test", 0).gen(3, "check")
        perm = torch.randperm(len(pieces), generator=samp).tolist()
        assert not set(trec["held_out_piece_indices"]) & set(perm[:pick_n])  # never one of the 8,000 (here: the dry spec's) prefixes the router trained on, tasks {tasks}


def test_no_general_prefix_means_no_general_accuracy_and_the_annotation_is_not_evaluated() -> None:
    world, _ = dry_world()
    ctx = world.ctx
    router = routing.Router(("A",), world.cfg.width, tgen(402, "router"))
    acc = routing.route_accuracy(router, ctx.student, ctx.router_layer, {"A": ctx.panels["E_A"].examples}, [])
    assert set(acc) == {"A"}
    s = study()
    s["replicates"][0]["routers"]["AB"]["accuracy"] = {"A": 1.0, "B": 1.0}
    assert analysis.analyze(s)["annotations"]["ROUTER (keyword-level) QUALIFIED"] is None


# --- R-icl: a BOS token only once ------------------------------------------------------------------------------------------------------------------------
def _ex(ids: list[int], bos: bool) -> Any:
    seg0 = SimpleNamespace(text="<bos>" if bos else "x", ids=(7,) if bos else tuple(ids[:1]))
    return SimpleNamespace(ids=tuple(ids), prompt_ids=tuple(ids), segments=(seg0,))


def test_icl_prompt_keeps_one_leading_bos_not_one_per_demonstration() -> None:
    demos = [_ex([7, 1, 2], True), _ex([7, 3], True), _ex([7, 4, 5], True)]
    query = _ex([7, 8, 9], True)
    assert cells.icl_ids(demos, query) == [7, 1, 2, 3, 4, 5, 8, 9]
    assert cells.icl_ids([_ex([1, 2], False), _ex([3], False)], _ex([8, 9], False)) == [1, 2, 3, 8, 9]  # no BOS prepended by the tokenizer: nothing removed
    assert cells.icl_ids([], query) == [7, 8, 9]  # no demonstration: the query keeps its own BOS


# --- scores: single-reference items alone, reference counts, items for every retrieval baseline --------------------------------------------------------------
def test_panel_scores_carry_reference_counts_and_the_single_reference_score() -> None:
    world, _, _, _, sc = trained()
    node = sc["r0/ST1/AB"]["scores"]["r0/ST1/AB"]["panels"]["E_A"]
    p = world.ctx.panels["E_A"]
    ones = [i for i, rf in enumerate(p.refs) if len(rf) == 1]
    assert node["single_reference"]["n"] == len(ones) and sum(node["reference_counts"].values()) == len(p.refs)
    if ones:
        assert node["single_reference"]["mean"] == pytest.approx(sum(node["items"][i] for i in ones) / len(ones))
    base = cells.stage0_scores(world, with_combined=False)
    assert "single_reference" in base["student"]["E_A"]["panel"] and "single_reference" in base["student"]["E_A"]["subsample"]


def test_every_retrieval_baseline_records_its_items_for_the_intervals() -> None:
    world, _, _, _, _ = trained()
    out = cells.retrieval_scores(world, 0)
    for c in core.TASKS:
        for name in ("R-exact", "R-nn", "R-gloss", "R-icl"):
            assert len(out[c][name]["items"]) == len(world.ctx.panels["E_" + c].examples), (c, name)
    assert retrieval.r_exact([], [], "A")["items"] == []


def test_a_descriptive_panel_is_never_in_a_gap_an_ablation_or_a_learned_route() -> None:
    world, _ = dry_world()
    ctx = SimpleNamespace(panels={"E_A": 1, "E_B": 2, "E_open": 3})
    assert cells.gap_panels(ctx) == ["E_A", "E_B"]
    assert cells.gap_panels(world.ctx) == list(world.ctx.panels)
