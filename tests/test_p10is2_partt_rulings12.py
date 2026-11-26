# ruff: noqa: E501
"""P10IS2 Part T ruling 43 amended (clipping), ruling 44 decided (G8 identity evidence) and the G9 wording (docs/decisions/ADR-0025-addendum-part-t-rulings-12.md). Self-check only."""

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import torch  # noqa: E402
from p10is2_engine_fixtures import CFG_T, world  # noqa: E402
from test_p10is2_partt_rulings11 import PART_Q_RECORD, STEP_KW, TOL, make_step_inputs  # noqa: E402

from arborlm.io import file_sha256  # noqa: E402
from studies.p10is2 import engine, partt_g8, partt_gates, partt_mps_step  # noqa: E402
from studies.p10is2.common import core, gates  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CPU = torch.device("cpu")


def real_cell_shape() -> tuple[list[torch.Tensor], list[list[torch.Tensor]], list[str]]:
    """Shaped like the real M1 cell at update 1: the key and value gradients are exactly zero (the gate starts at 0), the gate is one scalar; the second batch's gradients are small and nonzero."""
    g = torch.Generator().manual_seed(11)
    params = [torch.randn(8, 4, generator=g) * 0.05, torch.randn(8, 4, generator=g) * 0.05, torch.zeros(1)]
    grads = [[torch.zeros(8, 4), torch.zeros(8, 4), torch.tensor([3e-5])], [torch.randn(8, 4, generator=g) * 1e-5, torch.randn(8, 4, generator=g) * 1e-5, torch.tensor([2e-5])]]
    return params, grads, ["store.keys.0", "store.values.0", "store.gates.0"]


# --- ruling 43 amended: clipping ---------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("shape", [make_step_inputs, real_cell_shape], ids=["test_world", "real_cell_shape"])
def test_a_missing_or_wrong_clip_on_one_side_fails_clearly_and_a_correct_one_passes(shape: Any) -> None:
    params, grads, names = shape()
    ok = partt_mps_step.compare_steps(params, grads, names, TOL, CPU, **STEP_KW)
    assert ok["passed"] is True and ok["clipped_gradient_agreement"]["largest"]["relative_difference"] == 0.0 and ok["clipped_gradient_agreement"]["cases_times_clip_norm"] == [0.5, 1.01, 4.0]
    missing = partt_mps_step.compare_steps(params, grads, names, TOL, CPU, device_clip=1e30, **STEP_KW)  # no clip on the device side
    assert missing["passed"] is False and missing["clipped_gradient_agreement"]["passed"] is False
    assert missing["clipped_gradient_agreement"]["largest"]["relative_difference"] > 0.5  # clearly, not at the edge of the tolerance
    for factor in (2.0, 1.1, 1.01, 1.002):  # a clip norm too large by 100 %, 10 %, 1 %, 0.2 %
        wrong = partt_mps_step.compare_steps(params, grads, names, TOL, CPU, device_clip=STEP_KW["clip"] * factor, **STEP_KW)
        assert wrong["passed"] is False and wrong["clipped_gradient_agreement"]["n_violations_over_tolerance"] >= 1, factor
    inside = partt_mps_step.compare_steps(params, grads, names, TOL, CPU, device_clip=STEP_KW["clip"] * 1.0005, **STEP_KW)
    assert inside["passed"] is True  # 5e-4, inside the registered 1e-3


def test_the_update_comparison_alone_catches_a_missing_clip_on_both_shapes() -> None:
    for shape in (make_step_inputs, real_cell_shape):
        params, grads, names = shape()
        res = partt_mps_step.compare_steps(params, grads, names, TOL, CPU, device_clip=1e30, **STEP_KW)
        assert res["update_passed"] is False and res["largest"]["relative_difference"] > 0.05  # measured 0.10 on both shapes; step 3 carries the step-1 state, so the clip factor no longer cancels


def test_step_3_loads_the_carried_state() -> None:
    params, grads, _ = make_step_inputs()
    carried = partt_mps_step.step_updates(params, grads, CPU, **STEP_KW)
    fresh = partt_mps_step.step_updates(params, grads, CPU, state_from_cpu=False, **STEP_KW)
    assert torch.equal(carried[0][0], fresh[0][0]) and not torch.equal(carried[2][0], fresh[2][0])  # step 3 differs with the carried state; step 1 is fresh in both


def test_the_clipped_gradients_are_clipped_to_the_norm_in_the_active_cases() -> None:
    params, grads, _ = make_step_inputs()
    out = partt_mps_step.clipped_gradients(grads, CPU, clip=1.0)
    norms = [float(torch.stack([(t**2).sum() for t in case]).sum().sqrt()) for case in out]
    assert norms[0] == pytest.approx(0.5, rel=1e-5) and norms[1] == pytest.approx(1.0, rel=1e-5) and norms[2] == pytest.approx(1.0, rel=1e-5)  # inactive, clipped from 1.01, clipped from 4


@pytest.mark.skipif(not torch.backends.mps.is_available(), reason="MPS is not available on this machine")
def test_the_gate_fails_on_the_device_when_the_clip_is_missing_on_the_device(monkeypatch: pytest.MonkeyPatch) -> None:
    w = world()
    w.device = torch.device("mps")
    spec = engine.CellSpec("M1", "AB", 0)
    honest = partt_gates.g4_mps(w, spec)
    assert honest["passed"] is True and honest["optimiser_step_agreement"]["clipped_gradient_agreement"]["passed"] is True
    real = partt_mps_step.compare_steps
    monkeypatch.setattr(partt_gates, "compare_steps", lambda *a, **k: real(*a, device_clip=1e30, **k))
    bad = partt_gates.g4_mps(w, spec)
    assert bad["passed"] is False and bad["loss_ok"] is True and bad["gradient_agreement"]["passed"] is True and bad["optimiser_step_agreement"]["clipped_gradient_agreement"]["passed"] is False


# --- G9 wording ---------------------------------------------------------------------------------------------------------------------------------------
def test_the_g9_failure_message_names_the_cited_checker_not_a_literal_revision(tmp_path: Path) -> None:
    cfg = core.load_config("T")
    root = tmp_path / "root"
    rel = Path(cfg["seeds"]["registry_checker"])
    (root / rel).parent.mkdir(parents=True)
    (root / rel).write_text("print('RESULT: FAIL')\n")
    cfg2 = json.loads(json.dumps(cfg))
    cfg2["seeds"]["registry_checker_sha256"] = file_sha256(root / rel)
    add = Path(cfg["seeds"]["registry_addendum"])
    (root / add).write_text("x")
    cfg2["seeds"]["registry_addendum_sha256"] = file_sha256(root / add)
    res = gates.seed_gate_r5("T", cfg2, root=root)
    msgs = [p for p in res["problems"] if "did not print RESULT: PASS" in p]
    assert msgs and "seed_registry_check_r7.py" in msgs[0] and "revision 5" not in msgs[0]


# --- ruling 44 decided: G8 coded identity evidence -------------------------------------------------------------------------------------------------------------
class TinyStudent(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.a = torch.nn.Linear(3, 2)
        self.b = torch.nn.Linear(2, 2)


class FileDoor:
    def __init__(self, path: Path | None) -> None:
        self.path = path
        self.files = {} if path is None else {partt_g8.STUDENT_FILE: "h"}

    def verify(self, rel: str) -> Path:
        assert self.path is not None and rel == partt_g8.STUDENT_FILE
        return self.path


def saved_plain(tmp: Path, student: torch.nn.Module, mutate: Any = None) -> Path:
    state = {n: p.detach().clone() for n, p in student.named_parameters()}
    if mutate is not None:
        mutate(state)
    path = tmp / "student_plain.pt"
    torch.save({"cfg": {"width": 3}, "state": state}, path)
    return path


def test_the_weights_identity_is_bitwise_and_fails_on_one_changed_or_missing_tensor(tmp_path: Path) -> None:
    s = TinyStudent()
    same = partt_g8.student_weights_identity(FileDoor(saved_plain(tmp_path, s)), s)
    assert same["checked"] is True and same["ok"] is True and same["tensors"] == 4 and same["n_differing"] == 0
    (tmp_path / "x").mkdir()

    def flip(state: dict[str, torch.Tensor]) -> None:
        state["b.bias"] = torch.nextafter(state["b.bias"], torch.full_like(state["b.bias"], 1e9))  # one ulp in one tensor

    diff = partt_g8.student_weights_identity(FileDoor(saved_plain(tmp_path / "x", s, flip)), s)
    assert diff["ok"] is False and diff["differing"] == ["b.bias"]
    (tmp_path / "y").mkdir()

    def drop(state: dict[str, torch.Tensor]) -> None:
        del state["a.bias"]

    miss = partt_g8.student_weights_identity(FileDoor(saved_plain(tmp_path / "y", s, drop)), s)
    assert miss["ok"] is False and miss["names_equal"] is False
    assert partt_g8.student_weights_identity(FileDoor(None), s)["ok"] is None and partt_g8.student_weights_identity(None, s)["ok"] is None  # nothing listed: not checkable, never a pass


def test_the_forward_code_identity_matches_part_qs_freeze_in_this_tree_and_fails_on_a_difference(tmp_path: Path) -> None:
    real = partt_g8.forward_code_identity(ROOT)
    assert real["checked"] is True and real["ok"] is True and real["differing"] == [] and set(real["files"]) == set(partt_g8.FORWARD_CODE)
    repo = tmp_path / "repo"
    (repo / "studies/p10is2/freeze").mkdir(parents=True)
    frozen: dict[str, str] = {}
    for rel in partt_g8.FORWARD_CODE:
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(f"# {rel}\n")
        frozen[rel] = file_sha256(repo / rel)
    (repo / partt_g8.Q_PLAN).write_text(json.dumps({"frozen_files": frozen}))
    assert partt_g8.forward_code_identity(repo)["ok"] is True
    (repo / "studies/p10s2/model.py").write_text("# changed\n")
    changed = partt_g8.forward_code_identity(repo)
    assert changed["ok"] is False and changed["differing"] == ["studies/p10s2/model.py"]
    assert partt_g8.forward_code_identity(tmp_path)["ok"] is None  # no Part Q plan in the tree: not checkable


def test_a_failed_identity_fails_g8_and_the_gates_stage_and_a_good_one_is_not_a_pass(tmp_path: Path) -> None:
    w = world()
    bad = {"ok": False, "weights": {"ok": False}, "forward_code": {"ok": True}}
    res = partt_gates.g8(w, None, PART_Q_RECORD, bad)
    assert res["passed"] is False and res["identity_failed"] is True and res["student_identity_supporting_evidence"] == bad
    good = {"ok": True, "weights": {"ok": True}, "forward_code": {"ok": True}}
    res = partt_gates.g8(w, None, PART_Q_RECORD, good)
    assert res["passed"] is None and res["not_run"] is True and res["student_identity_supporting_evidence"] == good and res["identity_failed"] is None  # supporting evidence, never G8 passing
    assert partt_gates.g8(w, None, PART_Q_RECORD, None)["passed"] is None
    failing = partt_gates.run_gates(w, CFG_T, tmp_path / "g1", run_checker=False, q_equivalence_record=PART_Q_RECORD, student_identity=bad)
    assert "G8" in failing["failed"] and failing["status"] == "ENGINEERING-FAILURE"
    passing = partt_gates.run_gates(w, CFG_T, tmp_path / "g2", run_checker=False, q_equivalence_record=PART_Q_RECORD, student_identity=good)
    assert "G8" in passing["not_run"] and "G8" not in passing["failed"] and passing["gates"]["G8"]["passed"] is None


def test_student_identity_needs_a_door_and_combines_both_parts(tmp_path: Path) -> None:
    s = TinyStudent()
    assert partt_g8.student_identity(None, s, ROOT) is None
    ident = partt_g8.student_identity(FileDoor(saved_plain(tmp_path, s)), s, ROOT)
    assert ident is not None and ident["ok"] is True and ident["weights"]["ok"] is True and ident["forward_code"]["ok"] is True
    (tmp_path / "z").mkdir()

    def flip(state: dict[str, torch.Tensor]) -> None:
        state["a.weight"] = state["a.weight"] + 1.0

    ident2 = partt_g8.student_identity(FileDoor(saved_plain(tmp_path / "z", s, flip)), s, ROOT)
    assert ident2 is not None and ident2["ok"] is False and ident2["forward_code"]["ok"] is True
