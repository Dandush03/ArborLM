# ruff: noqa: E501
"""P10IS2 Part T rulings 42, 43 and 44 (docs/decisions/ADR-0025-addendum-part-t-rulings-11.md): seed registry revision 6 (G9), the optimiser-step comparison of G4-MPS, and G8 reported NOT RUN on a bundle without stored reference
logits. Self-check only."""

import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import torch  # noqa: E402
from p10is2_engine_fixtures import CFG_T, world  # noqa: E402

from arborlm.io import file_sha256  # noqa: E402
from studies.p10is2 import engine, partt_g8, partt_gates, partt_mps_step  # noqa: E402
from studies.p10is2.common import core, gates  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "docs/reviews/p10-i-direction-2026-11-17"


# --- ruling 42: registry revision 6 ----------------------------------------------------------------------------------------------------------------
def test_r6_checker_is_r5_plus_one_ownership_line_and_a_note() -> None:
    r5 = (REG / "seed_registry_check_r5.py").read_text().split("\n")
    r6 = (REG / "seed_registry_check_r6.py").read_text().split("\n")
    note_end = next(i for i, line in enumerate(r6) if line.startswith("Programme-wide seed registry check for P10-I. REVISION 5"))
    assert r6[1].startswith('"""REVISION 6 (2026-11-21)')
    rebuilt = [r6[0], '"""' + r6[note_end], *r6[note_end + 1 :]]  # drop the revision-6 note, reopen the revision-5 docstring
    own6 = '    "P10-I-S0 ADR-0023": ("configs/p10is0_*", "studies/p10is0/*", "tests/test_p10is0_*"),  # revision 6'
    assert rebuilt.count(own6) == 1
    rebuilt.remove(own6)
    rebuilt = [x.replace("seed_registry_check_r6.py [--tables]", "seed_registry_check_r5.py [--tables]") for x in rebuilt]
    assert rebuilt == r5  # nothing else differs: no seed value, block or row


def test_the_config_cites_r6_by_hash_and_r5_is_unchanged() -> None:
    cfg = core.load_config("T")
    s = cfg["seeds"]
    assert s["registry_checker"].endswith("seed_registry_check_r7.py") and s["registry_addendum"].endswith("SEED_REGISTRY_R7.md")  # ruling 45 moved the citation to r7; r6 itself is pinned by tests/test_p10is2_partt_rulings13.py
    assert file_sha256(ROOT / s["registry_checker"]) == s["registry_checker_sha256"] and file_sha256(ROOT / s["registry_addendum"]) == s["registry_addendum_sha256"]
    assert file_sha256(REG / "seed_registry_check_r5.py") == "8ce47ab52abbe25b4b308ca2a1e7587f5461b13340f1faa2a0c0cff6804f4611"  # revision 5 is never edited
    assert file_sha256(REG / "SEED_REGISTRY_R5.md") == "19199e46d9f4e51d5650b9cfd9f3e1dd11730d45ae9fdada776a111e741ea865"


def test_g9_passes_on_this_tree_with_r6_and_the_checker_still_fails_planted_faults() -> None:
    res = gates.seed_gate("T", core.load_config("T"), root=ROOT)
    assert res["passed"], res["problems"]
    assert res["checker"]["result_line"] == "RESULT: PASS" and res["checker"]["unedited"] is True
    proc = subprocess.run([sys.executable, "-I", str(REG / "seed_registry_check_r7.py"), "--selftest", "--root", str(ROOT)], cwd=ROOT, capture_output=True, text=True, timeout=900, check=False)  # noqa: S603
    fails = [x for x in proc.stdout.splitlines() if x.strip().startswith("FAIL:")]
    assert proc.returncode == 1 and "RESULT: FAIL" in proc.stdout and fails and all("ADR-0031" in x for x in fails)  # every remaining failure is one of the planted P10-I-S6 faults
    assert not any(f"{s} /" in x for x in fails for s in ("P10-I-S0 ADR-0023", "P10-I-S1 ADR-0024"))  # the S0 own-files hits are the known case now; only the planted faults remain


# --- ruling 43: the optimiser-step comparison --------------------------------------------------------------------------------------------------------
def make_step_inputs() -> tuple[list[torch.Tensor], list[list[torch.Tensor]], list[str]]:
    g = torch.Generator().manual_seed(7)
    params = [torch.randn(6, 4, generator=g), torch.randn(5, generator=g), torch.randn(3, 3, generator=g)]
    grads = [[torch.randn(6, 4, generator=g) * 1e-3, torch.randn(5, generator=g) * 1e-3, torch.zeros(3, 3)], [torch.randn(6, 4, generator=g) * 1e-3, torch.randn(5, generator=g) * 1e-3, torch.zeros(3, 3)]]
    return params, grads, ["a", "b", "zero_gate"]


STEP_KW: dict[str, Any] = {"lr": 3e-3, "weight_decay": 0.0, "clip": 1.0}
TOL = {"mps_gradient_relative_tolerance": 1.0e-3}  # the registered figure, ruling 39


def test_an_identical_device_agrees_exactly_and_three_steps_are_compared() -> None:
    params, grads, names = make_step_inputs()
    res = partt_mps_step.compare_steps(params, grads, names, TOL, torch.device("cpu"), **STEP_KW)
    assert res["passed"] is True and res["largest"]["relative_difference"] == 0.0 and len(res["steps"]) == 3
    assert res["exact_zero_clause"]["cases"] == 3 and res["tolerance"] == 1.0e-3  # the zero tensor has an exactly zero update in each of the 3 steps
    ups = partt_mps_step.step_updates(params, grads, torch.device("cpu"), **STEP_KW)
    assert len(ups) == 3 and all(float(u[0].norm()) > 0.0 for u in ups) and all(float(u[2].norm()) == 0.0 for u in ups)


def test_a_wrong_step_on_the_device_fails_each_way() -> None:
    params, grads, names = make_step_inputs()
    real = partt_mps_step.step_updates

    def lr_off(p: Any, g: Any, dev: Any, **kw: Any) -> list[list[torch.Tensor]]:
        return real(p, g, dev, **{**kw, "lr": kw["lr"] * 1.01})  # a 1 % wrong learning rate

    res = partt_mps_step.compare_steps(params, grads, names, TOL, torch.device("cpu"), other_step=lr_off, **STEP_KW)
    assert res["passed"] is False and res["n_violations_over_tolerance"] >= 3 and res["largest"]["relative_difference"] > 1e-3

    def leak(p: Any, g: Any, dev: Any, **kw: Any) -> list[list[torch.Tensor]]:
        out = real(p, g, dev, **kw)
        out[1][2] = out[1][2] + 1e-12  # the zero-gradient tensor moves on the device
        return out

    res = partt_mps_step.compare_steps(params, grads, names, TOL, torch.device("cpu"), other_step=leak, **STEP_KW)
    assert res["passed"] is False and res["exact_zero_clause"]["ok"] is False

    def tiny(p: Any, g: Any, dev: Any, **kw: Any) -> list[list[torch.Tensor]]:
        out = real(p, g, dev, **kw)
        return [[x * (1 + 5e-4) for x in u] for u in out]  # arithmetic noise inside the registered tolerance passes

    assert partt_mps_step.compare_steps(params, grads, names, TOL, torch.device("cpu"), other_step=tiny, **STEP_KW)["passed"] is True


def test_the_gate_uses_the_registered_gradient_tolerance_and_no_new_key() -> None:
    gates_cfg = core.load_config("T")["gates"]
    assert gates_cfg["mps_gradient_relative_tolerance"] == 1.0e-3 and not any("step" in k for k in gates_cfg)


@pytest.mark.skipif(not torch.backends.mps.is_available(), reason="MPS is not available on this machine")
def test_the_mps_step_agrees_on_the_device_and_the_gate_fails_on_a_planted_divergence(monkeypatch: pytest.MonkeyPatch) -> None:
    params, grads, names = make_step_inputs()
    res = partt_mps_step.compare_steps(params, grads, names, TOL, torch.device("mps"), **STEP_KW)
    assert res["passed"] is True, res["largest"]
    w = world()
    w.device = torch.device("mps")
    spec = engine.CellSpec("M1", "AB", 0)
    honest = partt_gates.g4_mps(w, spec)
    assert honest["passed"] is True and honest["optimiser_step_agreement"]["passed"] is True and honest["optimiser_step_agreement"]["largest"]["tensor"] is not None
    real = partt_mps_step.step_updates

    def lr_off(p: Any, g: Any, dev: Any, **kw: Any) -> list[list[torch.Tensor]]:
        return real(p, g, dev, **{**kw, "lr": kw["lr"] * 1.01})

    real_compare = partt_mps_step.compare_steps
    monkeypatch.setattr(partt_gates, "compare_steps", lambda *a, **k: real_compare(*a, other_step=lr_off, **k))
    bad = partt_gates.g4_mps(w, spec)
    assert bad["passed"] is False and bad["loss_ok"] is True and bad["gradient_agreement"]["passed"] is True and bad["optimiser_step_agreement"]["passed"] is False


# --- ruling 44: G8 NOT RUN, never a pass -------------------------------------------------------------------------------------------------------------
PART_Q_RECORD = {"4": {"injection": {"identical_top1": True, "max_abs_difference": 9e-05, "ok": True}, "logits": {"identical_top1": True, "max_abs_difference": 8e-05, "ok": True}},
                 "12": {"injection": {"identical_top1": True, "max_abs_difference": 8e-05, "ok": True}, "logits": {"identical_top1": True, "max_abs_difference": 8e-05, "ok": True}}}  # fmt: skip


def test_g8_without_stored_reference_logits_is_not_run_and_echoes_part_qs_verdicts() -> None:
    w = world()
    for rec in (None, {}):
        res = partt_gates.g8(w, rec, PART_Q_RECORD)
        assert res["passed"] is None and res["not_run"] is True and "NOT RUN" in res["skipped"]
        assert res["half_1_part_q_step_1_record"]["present"] is True and res["half_1_part_q_step_1_record"]["all_ok"] is True and set(res["half_1_part_q_step_1_record"]["layers"]) == {"4", "12"}
    none = partt_gates.g8(w, None, None)
    assert none["passed"] is None and none["not_run"] is True and none["half_1_part_q_step_1_record"] == {"present": False, "layers": {}, "all_ok": None}
    bad = {**PART_Q_RECORD, "12": {**PART_Q_RECORD["12"], "logits": {"identical_top1": False, "max_abs_difference": 0.5, "ok": False}}}
    assert partt_gates.g8(w, None, bad)["half_1_part_q_step_1_record"]["all_ok"] is False


def test_the_gates_record_names_g8_not_run_and_never_passes_it(tmp_path: Path) -> None:
    w = world()
    r = partt_gates.run_gates(w, CFG_T, tmp_path / "g", run_checker=False, q_equivalence_record=PART_Q_RECORD)
    assert "G8" in r["not_run"] and r["gates"]["G8"]["passed"] is None and "G8" in r["skipped"] and "G8" not in r["failed"]


class FakeDoor:
    def __init__(self, files: dict[str, str], record: dict[str, Any]) -> None:
        self.files, self._record = files, record

    def read_json(self, rel: str) -> Any:
        return self._record


def test_part_qs_record_is_read_only_through_the_doors_listed_files() -> None:
    assert partt_g8.q_equivalence_through_door(None) is None
    assert partt_g8.q_equivalence_through_door(FakeDoor({}, {"equivalence": PART_Q_RECORD})) is None  # not listed: no record, never read
    assert partt_g8.q_equivalence_through_door(FakeDoor({partt_g8.RECORD: "h"}, {"equivalence": PART_Q_RECORD})) == PART_Q_RECORD
    assert partt_g8.q_equivalence_through_door(FakeDoor({partt_g8.RECORD: "h"}, {})) is None


def test_g8_with_stored_records_is_unchanged() -> None:
    import inspect

    assert "q_record" in inspect.signature(partt_gates.g8).parameters and "equivalence.verify_all" in inspect.getsource(partt_gates.g8)
