# ruff: noqa: E501
"""P10S0 shared contract: constants of ADR-0020 revision 4, the cell registry (pipeline check 3, Q1 230 or 190, WX 20, probe 6), seeds and their disjointness (gate G9),
the schedules in exposures per fact, config, identity hashes, record IO, run manifests with the environment, and the one charged-time ledger (16 hours).

Specification: ``docs/decisions/ADR-0020-p10-s0-addressing-qualification.md`` (design revision 4). Every number below is copied from the ADR with its section. Nothing here trains
or evaluates a model. The arms A0, A1, A2, A5-D, A6 and A7 are ``studies.p9ii``'s, unedited (ADR-0020 section 5.1).

Status: implementation self-checked only. Not independent review, not Astra validation, not human approval. The registered run has not happened.
"""

import hashlib
import json
import math
import os
import platform
import re
import sys
import tomllib
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any, NamedTuple

import torch

from arborlm.config import _validate
from arborlm.io import canonical_json, file_sha256, read_json, sha256, write_json
from studies.p9 import core as p9core
from studies.p9i import core as p9icore
from studies.p9ii import core as p9iicore

# --- identity of the study -------------------------------------------------------------------------------------
SPEC = "docs/decisions/ADR-0020-p10-s0-addressing-qualification.md"
STUDY = "P10S0"
FAMILY = "P10S0_ADDRESSING_QUALIFICATION"
SCHEMA = 1
DEFAULT_CONFIG = Path("configs/p10s0_qualification.toml")  # the ADR header's name (the lead's ruling on item 1 of the implementation audit)
LAUNCH_DIR = Path("studies/p10s0/launch")
FREEZE_DIR = Path("studies/p10s0/freeze")
P9II_RECORDS = {
    "results": "results/p9ii-run-2026-11-15/results.json",
    "outcome": "results/p9ii-run-2026-11-15/OUTCOME.md",
    "calibration": "results/p9ii-calibration-2026-11-15/calibration.json",
}
IMPORTED_P9_MODULES = p9iicore.IMPORTED_P9_MODULES
IMPORTED_P9I_MODULES = p9iicore.IMPORTED_P9I_MODULES

# --- task and memory (ADR-0019 section 3 through studies.p9ii; one namespace) ------------------------------------
ALPHABET_SIZE = p9iicore.ALPHABET_SIZE
CONTEXT_BYTES, INPUT_LENGTH = p9iicore.CONTEXT_BYTES, p9iicore.INPUT_LENGTH
RECORDS_PER_CONTEXT, ANSWER_SITES_PER_BATCH = p9iicore.RECORDS_PER_CONTEXT, p9iicore.ANSWER_SITES_PER_BATCH
KEY_WIDTH, TOP, TEMPERATURE, HIDDEN_WIDTH = p9iicore.KEY_WIDTH, p9iicore.TOP, p9iicore.TEMPERATURE, p9iicore.HIDDEN_WIDTH
WINDOW = p9iicore.WINDOW  # 7
FULL_WINDOW = 64  # WX: the backbone's context length (ADR-0020 section 5.2)
WX_FEATURES = FULL_WINDOW * HIDDEN_WIDTH  # 2,048 = fan-in of W_X
LEARNING_RATE, CLIP_NORM = p9iicore.LEARNING_RATE, p9iicore.CLIP_NORM
UPDATES = p9iicore.UPDATES  # U = 8,192
DIAG_EVERY, PROBE_FACTS = p9iicore.DIAG_EVERY, p9iicore.PROBE_FACTS

# --- arms (section 3.4) --------------------------------------------------------------------------------------------
CORE_LEARNED_ARMS = ("A0", "A1", "A2", "A5-D")  # C4 = A5-D (section 3.4); n_L = 4
REFERENCE_ARMS = ("A6", "A7")
WX_ARMS = ("WX-A5-D", "WX-A1")  # WX of each arm that can still be the candidate (section 3.5)
ARMS = (*CORE_LEARNED_ARMS, *REFERENCE_ARMS, *WX_ARMS)
LEARNED_ARMS = (*CORE_LEARNED_ARMS, *WX_ARMS)
PREFERENCE_ORDER = ("A0", "A5-D", "A2", "A1")  # section 8.5: A0, then C4, then A2, then A1
CANDIDATE_ARMS = ("A5-D", "A1")  # the arms that can still be the candidate (computed by arm_selection, asserted by G10)
LABEL_FREE = ("A0", "A5-D")
SUPERVISED = ("A1", "A2")
SUPERVISION_LABEL = {"A0": "(LABEL-FREE)", "A5-D": "(LABEL-FREE)", "A1": "(ADDRESS-SUPERVISED IN TRAINING — needs a target slot per fact)", "A2": "(ADDRESS-SUPERVISED IN TRAINING — needs a target slot per fact)"}
NO_TARGET_INJECTION = "NOT RUN — NO TARGET INJECTION"
CALIBRATED = {"lambda": 1.0, "u_pre": 2048.0, "mu": 1.0, "k0_fraction": 0.125}  # P9-II's audited calibration record (k0_fraction is not used: A4 is not in S0)
Hyper = p9iicore.Hyper
exposures_per_fact = p9iicore.exposures_per_fact
ANSWER_SITES_PER_CONTEXT = p9iicore.ANSWER_SITES_PER_CONTEXT
GENERATION_FLOOR_SECONDS = 60.0  # per draw (the lead's ruling on item 2)
GENERATION_PROVISIONAL_CAP_SECONDS = 1800.0  # a placeholder: the rehearsal sets the cap (2 x the measured generation time of the rehearsal draw, floor 60 s); the freeze refuses while provisional
HYPER = Hyper(lambda_=CALIBRATED["lambda"], u_pre=CALIBRATED["u_pre"], k0_fraction=CALIBRATED["k0_fraction"], mu=CALIBRATED["mu"])


def base_arm(arm: str) -> str:
    """The arm whose objective an arm trains with (WX-X is trained exactly as X)."""
    return arm[3:] if arm.startswith("WX-") else arm


def is_wx(arm: str) -> bool:
    return arm.startswith("WX-")


# --- cell types (sections 5.3, 6) ----------------------------------------------------------------------------------
@dataclass(frozen=True)
class CellType:
    """One cell type: facts, slots, updates in units of U, the readouts (in units of U; the last one decides the class) and the studies.p9ii stage number whose schedule
    multiplier applies to A2's U_pre (ADR-0019 section 5: schedules in exposures per fact)."""

    name: str
    token: str
    facts: int
    slots: int
    multiplier: int
    readouts: tuple[int, ...]
    stage: int

    @property
    def facts_per_slot(self) -> float:
        return self.facts / self.slots

    def updates(self, unit: int = UPDATES) -> int:
        return self.multiplier * unit

    def readout_updates(self, unit: int = UPDATES) -> tuple[int, ...]:
        return tuple(m * unit for m in self.readouts)

    def decisive(self, unit: int = UPDATES) -> int:
        return self.readouts[-1] * unit

    def exposures_per_fact(self, unit: int = UPDATES) -> float:
        return p9iicore.exposures_per_fact(self.updates(unit), self.facts)


CELLTYPES: dict[str, CellType] = {
    "2K/4K": CellType("2K/4K", "2K4K", 2048, 4096, 1, (1,), 1),
    "8K/16K": CellType("8K/16K", "8K16K", 8192, 16384, 4, (1, 4), 2),
    "8K/4K": CellType("8K/4K", "8K4K", 8192, 4096, 4, (1, 4), 2),
    "32K/64K": CellType("32K/64K", "32K64K", 32768, 65536, 16, (16,), 3),
}
CORE_CELLTYPES = ("2K/4K", "8K/16K")  # "both core sizes" = 4,096 and 16,384
FACT_SETS = (2048, 8192, 32768)
CELLTYPE_BY_TOKEN = {c.token: c for c in CELLTYPES.values()}
ARM_CELLTYPES: dict[str, tuple[str, ...]] = {
    "A0": ("2K/4K", "8K/16K", "8K/4K"),
    "A1": ("2K/4K", "8K/16K"),
    "A2": ("2K/4K", "8K/16K"),
    "A5-D": ("2K/4K", "8K/16K", "8K/4K"),
    "A6": ("2K/4K", "8K/16K", "8K/4K"),
    "A7": ("2K/4K", "8K/16K"),
}
Q1_DRAWS = tuple(range(1, 11))
PROBE_DRAWS = (11, 12, 13)
N_DRAWS = 13
INIT_SEEDS = (2001, 2002)
CHECK_INIT, REHEARSAL_INIT = 2091, 2092
SIZES_LABEL = {"2K/4K": "4,096", "8K/16K": "16,384"}

# --- thresholds (sections 8.2, 8.3; ADR-0019 section 8 through studies.p9ii.core) -----------------------------------
SUCCESS_FRACTION_OF_A6 = p9iicore.SUCCESS_FRACTION_OF_A6  # 0.90
A6_MIN_ACCURACY = p9iicore.A6_MIN_ACCURACY  # 0.90
A6_MIN_ACCURACY_OVERLOAD = 0.50  # 8K/4K (section 8.2) [lead's choice]
DEPENDENCE_FRACTION = 0.95  # condition 6: a_use >= 0.95 x accuracy [lead's choice]
STABLE_THRESHOLD = p9iicore.STABLE_THRESHOLD  # 0.80
RECALL_THRESHOLD = p9iicore.RECALL_THRESHOLD
LM_MARGIN, LM_FLAGGED_CELLS = p9iicore.LM_MARGIN, p9iicore.LM_FLAGGED_CELLS
PAIRED_THRESHOLD = p9iicore.PAIRED_THRESHOLD  # d >= 4
MAX_NOT_EVALUATED_DRAWS = 1
MAX_FAILED_RELIABLE = 1
MIN_SUCCESSES = {"20": 5, "10": 3}  # UNRELIABLE from this many successes (section 8.3)
CONSISTENCY_MAX_FAILED_DRAWS = 2  # section 8.5 (b) [lead's choice]
PER_DRAW_BOUND_ALPHA = 0.05
# Class-table row used for a cell type: "20" (two seeds per draw), "10" (one seed per draw), "3" (the 65,536 probe).
PRINTED_BOUNDS = {"10/10": 0.741, "9/10": 0.606, "9/9": 0.717, "8/9": 0.571, "8/10": 0.493, "3/3": 0.368}

# --- the fixed strings of ADR-0020 section 3.4 (character for character; a test compares them with the ADR) ----------
HUMAN_LEAD_WORDS = "yes s0 should include the penalty and i approve s2 download"
OVERRIDE_DATE = "2026-11-15"
FOURTH_ARM_STRING = "FOURTH ARM: A5-D — ADDED BY THE HUMAN LEAD'S DECISION OF 2026-11-15; THE REGISTERED MAPPING GAVE NONE (P9-II CARRIED A0)"
F1_ANNOTATION = "A0 is UNRELIABLE at 4,096 (4/16) and at chance at matched updates at 16,384; A5-D is the only label-free arm RELIABLE at both sizes; A5-D was not probed at 65,536 because the rule sent A0 to Stage 3."
PROVENANCE_SENTENCE = "A5-D was added after P9-II's outcome was observed, knowing it was RELIABLE there (16/16 at 4,096; 8/8 at 16,384). For A5-D, S0 is a confirmatory replication on new draws, not an unbiased first test. Its CONSISTENT ACROSS STUDIES label and pooled count include the P9-II records it was chosen on and add no independent evidence; no pooled per-draw bound is printed for A5-D."
MAPPING_NONE_TEMPLATE = "FOURTH ARM: NONE — P9-II CARRIED {arm} (ALREADY IN S0)"
MAPPING_NONE_STATUS_TEMPLATE = "FOURTH ARM: NONE — P9-II {status}"
FIXED_SENTENCES = "W7 is told the record length. The memory is told the answer position. Synthetic fixed-length records; one frozen 27,392-parameter backbone."
NOT_STARTED = "NOT STARTED — NO P9-II CALIBRATION RECORD"


CUT3_LABEL = "one initialization seed per draw at 16,384"  # ADR-0020 section 10.4, cut 3: "the label states ..."
UNSTAMPED_KINDS = ("rehearsal",)  # the whitelisted rehearsal record has a fixed set of fields; every other record ``write_record`` writes that names A5-D carries the three strings (the re-check's informational item)
A5D = "A5-D"


def a5d_fields() -> dict[str, str]:
    """The three fixed strings of section 3.4 as fields of a machine product."""
    return {"fourth_arm_string": FOURTH_ARM_STRING, "f1_annotation": F1_ANNOTATION, "provenance_sentence": PROVENANCE_SENTENCE}


def mentions_a5d(text: str) -> bool:
    stripped = text.replace(FOURTH_ARM_STRING, "").replace(F1_ANNOTATION, "").replace(PROVENANCE_SENTENCE, "")
    return A5D in stripped


def has_provenance(text: str) -> bool:
    return FOURTH_ARM_STRING in text and F1_ANNOTATION in text and PROVENANCE_SENTENCE in text


def assert_provenance(text: str, what: str = "output") -> None:
    """Section 8.7: an output that prints a class, label, annotation or reading of A5-D carries the three strings and may not shorten them away."""
    if mentions_a5d(text) and not has_provenance(text):
        raise ValueError(f"{what} names A5-D without the fourth-arm string, P9-II's F1 annotation and the fixed provenance sentence (ADR-0020 section 8.7)")


def stamp(obj: Any) -> Any:
    """A copy of ``obj`` in which every dict that is an A5-D entry (a key containing 'A5-D' whose value is a leaf dict, or a dict whose 'arm', 'candidate' or 'c4' is 'A5-D') carries ``a5d_provenance`` (the
    three strings), and the top level carries it once if A5-D is named anywhere. This is the one place a machine product gets them; ``write_record`` and ``emit_stdout`` call it."""
    import copy

    out = copy.deepcopy(obj)

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if any(node.get(k) == A5D for k in ("arm", "candidate", "c4")):
                node["a5d_provenance"] = a5d_fields()
            for k, v in list(node.items()):
                if isinstance(k, str) and A5D in k and isinstance(v, dict) and not any(isinstance(x, dict) for x in v.values()):
                    v["a5d_provenance"] = a5d_fields()  # a leaf entry keyed by A5-D; containers keyed by A5-D (per-cell-type maps) are covered by their entries' ``arm`` and by the top level
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(out)
    if isinstance(out, dict) and mentions_a5d(json.dumps(jsonable(out), default=str)):
        out["a5d_provenance"] = a5d_fields()
    return out


def emit_stdout(obj: Mapping[str, Any]) -> None:
    """Print a JSON line (stage summaries) through the stamp: a summary that names A5-D carries the three strings."""
    text = json.dumps(jsonable(stamp(dict(obj))), sort_keys=True, ensure_ascii=False)
    assert_provenance(text, "stdout")
    print(text)


def csv_header_lines() -> list[str]:
    return [f"# {FOURTH_ARM_STRING}", f"# {F1_ANNOTATION}", f"# {PROVENANCE_SENTENCE}"]


def a5d_block() -> str:
    """The fourth-arm string, P9-II's F1 annotation and the fixed provenance sentence, which accompany every printed class, label, annotation or hypothesis reading of A5-D (section 8.7)."""
    return f"**{FOURTH_ARM_STRING}**\n\n*{F1_ANNOTATION}*\n\n**\"{PROVENANCE_SENTENCE}\"**"


# --- resources and budget (section 10) ------------------------------------------------------------------------------
GIB = 1024**3
RSS_WORKER_BYTES = 3 * GIB
RSS_AGGREGATE_BYTES = 18 * GIB  # S0 18 GiB (section 10.4)
REHEARSAL_PEAK_LIMIT_BYTES = int(1.5 * GIB)  # a block whose rehearsal peak per worker exceeds this is NOT RUN — MEMORY
WORKERS = 6
DEFAULT_CAP_HOURS = 16.0  # only the value the config template renders for a new file; every reader takes the cap from the config (cap_hours), the one place a pre-freeze raise is made
HEADROOM = 2.0
REHEARSAL_UPDATES = 256
REHEARSAL_BUSY_PROCESSES = 12
PROJECTED_OTHER_HOURS = 0.8  # pipeline check, rehearsal (twice), gates, generation of 15 draws, evaluation, analysis (section 10.4, a projection)
SLOWEST_RATES = {4096: 0.0112, 16384: 0.0195, 65536: 0.0619}  # P9-I's slowest registered seconds per update (section 10.4; context only)
BLOCKS = ("q1", "wx", "probe")
BLOCK_STATUSES = ("COMPLETE", "NOT RUN — NO CANDIDATE", "NOT RUN — BUDGET", "NOT RUN — MEMORY", "INCOMPLETE", "NOT_EVALUATED")

# --- run directories and records ---------------------------------------------------------------------------------------
STAGE_CODES: dict[str, str] = {
    "generate": "P", "drawplan": "L", "check": "K", "rehearse": "H", "gates": "G", "train": "T", "evaluate": "E", "gate": "S", "analyze": "A", "report": "R", "dry": "D",
}  # fmt: skip
RECORD_KINDS = (
    "train", "snapshot", "eval", "stage_manifest", "rehearsal", "analysis", "data_manifest", "gates", "draw_plan", "projection", "ledger", "arm_selection", "q1_gate", "freeze_plan",
)  # fmt: skip
PANELS = ("A", "B")
PANEL_STREAM = {"A": "panel_a", "B": "panel_b"}
MODES = ("registered", "check", "rehearsal", "dry")


# --- cells (sections 5, 6) -----------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Cell:
    """One cell. ``block``: Q1, WX, PR (65,536 probe) or PC (pipeline check). ``draw``: 1..13, or 0 for the pipeline check. ``seed_index`` j: init seed 2001 + j (the pipeline
    check: 2091)."""

    block: str
    arm: str
    celltype: str
    draw: int
    seed_index: int
    label: str

    def __post_init__(self) -> None:
        if self.block not in ("Q1", "WX", "PR", "PC") or self.arm not in ARMS or self.celltype not in CELLTYPES or self.seed_index not in (0, 1):
            raise ValueError(f"unregistered P10S0 cell: {self.label}")

    @property
    def ct(self) -> CellType:
        return CELLTYPES[self.celltype]

    @property
    def facts(self) -> int:
        return self.ct.facts

    @property
    def slots(self) -> int:
        return self.ct.slots

    @property
    def base(self) -> str:
        return base_arm(self.arm)

    @property
    def learned(self) -> bool:
        return self.arm in LEARNED_ARMS

    @property
    def init_seed(self) -> int:
        return CHECK_INIT if self.block == "PC" else INIT_SEEDS[self.seed_index]

    def p9ii_cell(self) -> p9iicore.Cell:
        """The ``studies.p9ii`` cell the trainer is built from (arm = the base arm; stage = the schedule multiplier's stage). Its label is this cell's."""
        return p9iicore.Cell(self.ct.stage, self.base, self.slots, max(1, self.draw), self.seed_index, None, self.label)


def make_label(block: str, arm: str, celltype: str, draw: int, j: int, prefix: str = "") -> str:
    return f"{prefix}{block}-{arm}-{CELLTYPES[celltype].token}-d{draw:02d}-j{j}"


def _cell(block: str, arm: str, celltype: str, draw: int, j: int) -> Cell:
    return Cell(block, arm, celltype, draw, j, make_label(block, arm, celltype, draw, j))


def alternating(draw: int) -> int:
    """j of a one-seed cell: init seed 2001 for odd draws and 2002 for even (8K/4K, WX, cut 3 at 8K/16K)."""
    return 0 if draw % 2 == 1 else 1


def q1_cells(cut3: bool = False) -> list[Cell]:
    """Q1: 230 cells (190 under cut 3): 2K/4K 100, 8K/16K 100 (60 under cut 3), 8K/4K 30. References use seed 2001 on every draw (section 6.1)."""
    out: list[Cell] = []
    for ct in CORE_CELLTYPES:
        two_seeds = not (cut3 and ct == "8K/16K")
        for arm in CORE_LEARNED_ARMS:
            for d in Q1_DRAWS:
                for j in ((0, 1) if two_seeds else (alternating(d),)):
                    out.append(_cell("Q1", arm, ct, d, j))
        out += [_cell("Q1", arm, ct, d, 0) for arm in REFERENCE_ARMS for d in Q1_DRAWS]
    out += [_cell("Q1", arm, "8K/4K", d, alternating(d) if arm != "A6" else 0) for arm in ("A0", "A5-D", "A6") for d in Q1_DRAWS]
    return out


def wx_cells(candidate: str) -> list[Cell]:
    """WX of the candidate: 2K/4K and 8K/16K x draws 1-10 x one seed (alternating): 20 cells."""
    arm = f"WX-{candidate}"
    if arm not in WX_ARMS:
        raise ValueError(f"WX is run only for an arm that can still be the candidate {CANDIDATE_ARMS}: {candidate!r}")
    return [_cell("WX", arm, ct, d, alternating(d)) for ct in CORE_CELLTYPES for d in Q1_DRAWS]


def probe_cells(candidate: str) -> list[Cell]:
    """The 65,536 probe: the candidate and A6 at 32K/64K x draws 11-13 x seed 2001: 6 cells."""
    if candidate not in CANDIDATE_ARMS:
        raise ValueError(f"the probe is run only for an arm that can still be the candidate {CANDIDATE_ARMS}: {candidate!r}")
    return [_cell("PR", arm, "32K/64K", d, 0) for arm in (candidate, "A6") for d in PROBE_DRAWS]


def check_cells() -> list[Cell]:
    """The pipeline check (section 10.1): A0, A6 and A7 at 2K/4K, one cell each, on the check draw."""
    return [_cell("PC", arm, "2K/4K", 0, 0) for arm in ("A0", "A6", "A7")]


def _all_registered() -> list[Cell]:
    every = [*q1_cells(False), *check_cells()]
    for cand in CANDIDATE_ARMS:
        every += [*wx_cells(cand), *probe_cells(cand)]
    return list({c.label: c for c in every}.values())


Q1_CELL_COUNT, Q1_CUT3_CELL_COUNT, WX_CELL_COUNT, PROBE_CELL_COUNT, CHECK_CELL_COUNT = 230, 190, 20, 6, 3
WHOLE_PLAN_CELLS = Q1_CELL_COUNT + WX_CELL_COUNT + PROBE_CELL_COUNT  # 256


def _assert_registry() -> None:
    sizes = {len(q1_cells()), len(q1_cells(True)), len(wx_cells("A5-D")), len(probe_cells("A1")), len(check_cells())}
    if sizes != {Q1_CELL_COUNT, Q1_CUT3_CELL_COUNT, WX_CELL_COUNT, PROBE_CELL_COUNT, CHECK_CELL_COUNT}:
        raise ImportError("P10S0 registry counts differ from sections 6 and 10.1")
    if any(c.arm in SUPERVISED and c.celltype == "8K/4K" for c in q1_cells()):
        raise ImportError("A1 and A2 are not run at 8K/4K (section 5.1)")
    labels = [c.label for c in _all_registered()]
    if len(set(labels)) != len(labels):
        raise ImportError("P10S0 cell labels are not unique")


_assert_registry()
_BY_LABEL: dict[str, Cell] = {c.label: c for c in _all_registered()}
_LABEL = re.compile(r"^(?P<prefix>TEST-|REH-)(?P<block>Q1|WX|PR|PC)-(?P<arm>(?:WX-)?A\d(?:-[A-Z])?)-(?P<ct>2K4K|8K16K|8K4K|32K64K)-d(?P<draw>\d+)-j(?P<j>\d)$")


def make_cell(arm: str, celltype: str, block: str = "Q1", draw: int = 1, j: int = 0, prefix: str = "TEST-") -> Cell:
    """A cell of any arm at any cell type without consulting the registry (unit tests, the DRY stage, rehearsal)."""
    return Cell(block, arm, celltype, draw, j, make_label(block, arm, celltype, draw, j, prefix))


def parse_label(label: str) -> Cell:
    """The registered cell named ``label``; ``TEST-`` and ``REH-`` labels (``make_cell``) are rebuilt. ValueError otherwise."""
    cell = _BY_LABEL.get(label)
    if cell is not None:
        return cell
    m = _LABEL.match(label)
    if m is None:
        raise ValueError(f"unknown P10S0 cell label {label!r}")
    return make_cell(m["arm"], CELLTYPE_BY_TOKEN[m["ct"]].name, m["block"], int(m["draw"]), int(m["j"]), m["prefix"])


def labels_of(items: Sequence[Cell]) -> list[str]:
    return [c.label for c in items]


# --- schedules (section 5.3) --------------------------------------------------------------------------------------------
def schedule_for(arm: str, celltype: str, hyper: p9iicore.Hyper = HYPER, unit: int = UPDATES) -> p9iicore.Schedule:
    """A2's U_pre in updates of the run: ``U_pre`` (2,048) at 2,048 facts and 4 x that (8,192) at 8,192 facts, scaled by F / 2,048 (exposures per fact, as ADR-0019 section 5).
    No other arm of S0 has a schedule. A2 does not exist at 8K/4K or 32K/64K."""
    ct = CELLTYPES[celltype]
    if arm == "A2" and celltype not in CORE_CELLTYPES:
        raise ValueError(f"A2 has no cell at {celltype} (section 5.1)")
    return p9iicore.schedule_for(base_arm(arm), ct.stage, hyper, ct.slots, unit)


# --- seeds (section 7) ------------------------------------------------------------------------------------------------------
REGISTERED_BASE = 200001
DRAW_STRIDE = 100
RESERVE_BASES = {1: 201301, 2: 201401}
CHECK_BASE, REHEARSAL_BASE = 209001, 209101
TEST_SEED_BASE, TEST_SEED_TOP = 920001, 920999
FACT_SET_OFFSET = {2048: 0, 8192: 20, 32768: 60}
TARGET_OFFSET = {"2K/4K": 40, "8K/16K": 44, "8K/4K": 44, "32K/64K": 48}  # + j (8K/4K has no target-slot cell: the value is unused)
SWAP_OFFSET = {2048: 50, 8192: 51, 32768: 52}
S0_RANGE = (200001, 209999)
DRAW_NAMES = tuple(f"p10s0-draw-{k}" for k in range(1, N_DRAWS + 1))
RESERVE_NAMES = ("p10s0-reserve-1", "p10s0-reserve-2")
SET_NAMES = (*DRAW_NAMES, *RESERVE_NAMES)
MAX_REPLACEMENTS = 2


def draw_base(draw: int) -> int:
    if not 1 <= draw <= N_DRAWS:
        raise ValueError("registered draws are 1..13")
    return REGISTERED_BASE + DRAW_STRIDE * (draw - 1)


def block_seeds(name: str, base: int, facts: int) -> p9core.SeedSet:
    """The seed block of one fact set: fourteen data seeds in P9's order at block + 0..13, Panel A null seeds at + 14..16 and Panel B's at + 17..19 (P9-I's registered convention)."""
    start = base + FACT_SET_OFFSET[facts]
    values = {n: start + i for i, n in enumerate(p9core.DATA_SEEDS)}
    return p9core.SeedSet(name, **values, null_seeds_a=tuple(start + 14 + i for i in range(3)), null_seeds_b=tuple(start + 17 + i for i in range(3)))


@dataclass(frozen=True)
class SeedSetSpec:
    """A named set of S0 seed blocks (one draw, one reserve, the check draw, the rehearsal draw or a test set); ``base`` is the draw's base seed."""

    name: str
    base: int

    def seeds(self, facts: int) -> p9core.SeedSet:
        return block_seeds(self.name, self.base, facts)

    def target_seed(self, celltype: str, j: int) -> int:
        return self.base + TARGET_OFFSET[celltype] + j

    def swap_seed(self, facts: int) -> int:
        return self.base + SWAP_OFFSET[facts]

    def values(self) -> frozenset[int]:
        out: set[int] = set()
        for f in FACT_SETS:
            s = self.seeds(f)
            out |= {*s.data_values(), *s.null_seeds_a, *s.null_seeds_b}
        out |= {self.base + o + j for o in TARGET_OFFSET.values() for j in (0, 1)}
        out |= {self.base + o for o in SWAP_OFFSET.values()}
        return frozenset(out)


def registered_set(draw: int, profile: str = "registered") -> SeedSetSpec:
    if profile == "test":
        draw_base(draw)  # range check
        return SeedSetSpec(f"p10s0-test-draw-{draw}", TEST_SEED_BASE + TEST_PROFILE_STRIDE * (draw - 1))
    return SeedSetSpec(f"p10s0-draw-{draw}", draw_base(draw))


def reserve_set(reserve: int, profile: str = "registered") -> SeedSetSpec:
    if profile == "test":
        return SeedSetSpec(f"p10s0-test-reserve-{reserve}", TEST_SEED_BASE + TEST_PROFILE_STRIDE * (N_DRAWS + reserve - 1))
    return SeedSetSpec(f"p10s0-reserve-{reserve}", RESERVE_BASES[reserve])


CHECK_SET = SeedSetSpec("p10s0-check", CHECK_BASE)
REHEARSAL_SET = SeedSetSpec("p10s0-rehearsal", REHEARSAL_BASE)


def test_set(offset: int = 0) -> SeedSetSpec:
    """Unit-test and DRY seeds: 920001 upward."""
    base = TEST_SEED_BASE + 100 * offset
    if base + 99 > TEST_SEED_TOP:
        raise ValueError("test seed offset out of range")
    return SeedSetSpec(f"p10s0-test-{offset}", base)


def set_of_name(name: str) -> SeedSetSpec:
    t = re.fullmatch(r"p10s0-test-(draw|reserve)-(\d+)", name)
    if t is not None:
        return registered_set(int(t[2]), "test") if t[1] == "draw" else reserve_set(int(t[2]), "test")
    m = re.fullmatch(r"p10s0-(draw|reserve|test)-(\d+)", name)
    if m is not None:
        index = int(m[2])
        return registered_set(index) if m[1] == "draw" else reserve_set(index) if m[1] == "reserve" else test_set(index)
    if name == CHECK_SET.name:
        return CHECK_SET
    if name == REHEARSAL_SET.name:
        return REHEARSAL_SET
    raise ValueError(f"not a P10S0 seed set name: {name!r}")


TEST_PROFILE_MARKER = "TEST_PROFILE"
TEST_PROFILE_STRIDE = 4  # test-profile sets overlap each other (they are never used for a result) and stay inside 920001-920999


def profile_of(run_dir: Path | str | None) -> str:
    """'test' when the run directory holds the marker file ``TEST_PROFILE`` (the end-to-end exercise of the registered sequence on test seeds; ``studies.p10s0.e2e``), else 'registered'. The marker only
    selects seed sets named ``p10s0-test-draw-k`` / ``p10s0-test-reserve-k`` (test seeds 920001+), tiny sizes and a synthetic backbone; no registered seed is ever read under it."""
    return "test" if run_dir is not None and (Path(run_dir) / TEST_PROFILE_MARKER).is_file() else "registered"


def draw_names(profile: str = "registered") -> tuple[str, ...]:
    return DRAW_NAMES if profile == "registered" else tuple(f"p10s0-test-draw-{k}" for k in range(1, N_DRAWS + 1))


def reserve_names(profile: str = "registered") -> tuple[str, ...]:
    return RESERVE_NAMES if profile == "registered" else ("p10s0-test-reserve-1", "p10s0-test-reserve-2")


def set_names(profile: str = "registered") -> tuple[str, ...]:
    return (*draw_names(profile), *reserve_names(profile))


def replacement_label(reserve_name: str) -> str:
    return "REPLACED BY RESERVE " + reserve_name.rsplit("-", 1)[-1]


def check_seed_set(mode: str, name: str) -> None:
    """``registered``: only ``p10s0-draw-k`` and ``p10s0-reserve-k``; ``check``: only the pipeline-check draw; ``rehearsal``: only the rehearsal draw (and P9-II's rehearsal set 5, which G4's
    identity check against ``studies.p9ii`` shares); ``dry``: test seeds (and P9-II's, for the same identity check). Anything else is refused."""
    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}")
    if mode == "registered":
        ok = bool(re.fullmatch(r"p10s0-(test-)?(draw|reserve)-\d+", name))  # the test-profile names hold test seeds only
    elif mode == "check":
        ok = name == CHECK_SET.name
    elif mode == "rehearsal":
        ok = name in (REHEARSAL_SET.name, f"rehearsal-{p9iicore.REHEARSAL_SEED_SET}")
    else:
        ok = name.startswith(("p10s0-test", "p9ii-test"))
    if not ok:
        raise ValueError(f"mode {mode!r} cannot use the {name!r} seed set")


class DrawPlan(NamedTuple):
    ok: bool
    seed_set_of: dict[int, str]
    replacements: dict[int, str]
    reason: str | None


def plan_draws(g1_passed: Mapping[str, bool], profile: str = "registered") -> DrawPlan:
    """As ADR-0019 section 9: a draw that fails G1 (any of its three fact sets) is replaced by the next unused reserve; a reserve that fails G1 when needed, or more than two failed draws,
    stops everything. A draw or reserve with no G1 result counts as failed."""
    draws, reserves = draw_names(profile), reserve_names(profile)
    failed = [k for k in range(1, N_DRAWS + 1) if g1_passed.get(draws[k - 1]) is not True]
    seed_set_of = {k: draws[k - 1] for k in range(1, N_DRAWS + 1)}
    if len(failed) > MAX_REPLACEMENTS:
        return DrawPlan(False, seed_set_of, {}, f"{len(failed)} draws failed G1 (at most {MAX_REPLACEMENTS} may be replaced)")
    replacements: dict[int, str] = {}
    for slot, reserve in zip(failed, reserves, strict=False):
        if g1_passed.get(reserve) is not True:
            return DrawPlan(False, seed_set_of, replacements, f"reserve {reserve} failed G1 or has no G1 result")
        replacements[slot] = reserve
        seed_set_of[slot] = reserve
    return DrawPlan(True, seed_set_of, replacements, None)


def seed_namespaces() -> dict[str, frozenset[int]]:
    """S0's own seed groups by name (gate G9 and a test read it)."""
    return {
        "registered": frozenset().union(*(registered_set(k).values() for k in range(1, N_DRAWS + 1))),
        "reserve": frozenset().union(*(reserve_set(r).values() for r in (1, 2))),
        "check": CHECK_SET.values(),
        "rehearsal": REHEARSAL_SET.values(),
        "init": frozenset(INIT_SEEDS),
        "check_rehearsal_init": frozenset({CHECK_INIT, REHEARSAL_INIT}),
        "test": frozenset().union(*(test_set(k).values() for k in range(8))),
    }


# Bounded namespaces of the other studies (ADR-0020 section 7, gate G9): name -> inclusive ranges. S1's and S2's are those their ADRs state (ADR-0021 and ADR-0022).
OTHER_NAMESPACES: dict[str, tuple[tuple[int, int], ...]] = {
    "P9": ((170001, 171343), (179001, 179933), (1701, 1702)),
    "P9-I": ((182001, 182020), (180101, 181900), (1791, 1792), (1801, 1802), (900001, 900233)),
    "review diagnostics": ((500001, 500004),),
    "P9-II": ((190001, 191599), (1891, 1892), (1901, 1902), (910001, 919999)),
    "S1": ((210001, 219999), (2101, 2105), (2111, 2111), (2121, 2121), (2112, 2112), (2122, 2122), (2191, 2192), (921001, 921999)),
    "S2": ((220001, 228999), (229001, 229999)),
}
S0_RANGES: dict[str, tuple[tuple[int, int], ...]] = {
    "data": (S0_RANGE,),
    "init": ((2001, 2002),),
    "check_rehearsal_init": ((2091, 2092),),
    "test": ((TEST_SEED_BASE, TEST_SEED_TOP),),
}
RANGE_OF_GROUP = {"registered": "data", "reserve": "data", "check": "data", "rehearsal": "data", "init": "init", "check_rehearsal_init": "check_rehearsal_init", "test": "test"}


def _in(value: int, ranges: Sequence[tuple[int, int]]) -> bool:
    return any(lo <= value <= hi for lo, hi in ranges)


def assert_namespaces_disjoint(own: Mapping[str, frozenset[int]] | None = None, others: Mapping[str, Sequence[tuple[int, int]]] | None = None, extra: Mapping[str, frozenset[int]] | None = None) -> None:
    """Gate G9: S0's groups are disjoint from each other, each lies inside its own bounded range, none lies in another study's range, and none equals a seed in ``extra`` (the seeds that
    ``studies.p9``, ``p9i`` and ``p9ii`` actually use, and P1-P8's from their configs)."""
    ns = dict(own or seed_namespaces())
    names = sorted(ns)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            common = ns[a] & ns[b]
            if common:
                raise ValueError(f"seed groups {a!r} and {b!r} overlap: {sorted(common)[:5]}")
    for name, values in ns.items():
        ranges = S0_RANGES[RANGE_OF_GROUP[name]]
        outside = sorted(v for v in values if not _in(v, ranges))
        if outside:
            raise ValueError(f"group {name!r} uses {outside[:3]} outside its bounded range {ranges}")
    for other, other_ranges in (others or OTHER_NAMESPACES).items():
        for name, values in ns.items():
            inside = sorted(v for v in values if _in(v, other_ranges))
            if inside:
                raise ValueError(f"group {name!r} uses {inside[:3]} inside {other}'s range {list(other_ranges)}")
    for label, values in (extra or {}).items():
        for name, mine in ns.items():
            common = mine & values
            if common:
                raise ValueError(f"group {name!r} uses {sorted(common)[:3]}, a seed of {label}")


def implemented_study_seeds() -> dict[str, frozenset[int]]:
    """The seeds ``studies.p9``, ``p9i`` and ``p9ii`` actually use, read from their code (not from their ADRs)."""
    p9ii = p9iicore.seed_namespaces()
    return {
        "P9 code": p9core.registered_seed_values(),
        "P9-I code": p9icore.registered_seed_values() | frozenset([*p9icore.INIT_SEEDS, *p9icore.CALIBRATION_INIT_SEEDS]),
        "P9-II code": frozenset().union(*p9ii.values()),
    }


assert_namespaces_disjoint(extra=implemented_study_seeds())


def p9ii_test_seed_values() -> frozenset[int]:
    """P9-II's actual test seeds, from its committed code; G9 asserts them inside 910001-919999."""
    return p9iicore.seed_namespaces()["test"]


def config_seed_values(repo: Path | None = None) -> dict[str, frozenset[int]]:
    """Integers under any key containing ``seed`` in every ``configs/*.toml`` other than S0's own (P1-P8 and the later studies' seeds, read from their configs)."""
    base = repo or repo_root()
    out: dict[str, frozenset[int]] = {}
    for path in sorted((base / "configs").glob("*.toml")):
        if path.name == DEFAULT_CONFIG.name:
            continue
        with path.open("rb") as stream:
            data = tomllib.load(stream)
        found: set[int] = set()

        def walk(node: Any, under_seed: bool) -> None:
            if isinstance(node, dict):
                for k, v in node.items():
                    walk(v, under_seed or "seed" in str(k).lower())
            elif isinstance(node, list):
                for v in node:
                    walk(v, under_seed)
            elif isinstance(node, int) and not isinstance(node, bool) and under_seed:
                found.add(node)

        walk(data, False)
        if found:
            out[path.name] = frozenset(found)
    return out


# --- derived streams ----------------------------------------------------------------------------------------------------------------
def derive_seed(seed: int, *tags: object) -> int:
    text = "|".join([str(seed), "p10s0", *map(str, tags)]).encode()
    return int.from_bytes(hashlib.sha256(text).digest()[:8], "little") & ((1 << 62) - 1)


def json_line(record: Mapping[str, Any]) -> str:
    return json.dumps(p9iicore.jsonable(dict(record)), allow_nan=False, sort_keys=True)


NONFINITE = p9iicore.NONFINITE
nonfinite_str = p9iicore.nonfinite_str
jsonable = p9iicore.jsonable
number = p9iicore.number
median = p9iicore.median


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


# --- config ----------------------------------------------------------------------------------------------------------------------
def registered_config() -> dict[str, Any]:
    """The configuration mirrored in ``configs/p10s0_qualification.toml`` (derived from the constants)."""
    return {
        "schema_version": SCHEMA,
        "experiment_family": FAMILY,
        "spec_reference": SPEC,
        "memory": {"key_width": KEY_WIDTH, "top": TOP, "temperature": TEMPERATURE, "window": WINDOW, "wx_window": FULL_WINDOW},
        "training": {"learning_rate": LEARNING_RATE, "clip_norm": CLIP_NORM, "batch_contexts": p9iicore.BATCH_CONTEXTS, "updates": UPDATES, "diag_every": DIAG_EVERY, "probe_facts": PROBE_FACTS},
        "arms": {"core_learned": list(CORE_LEARNED_ARMS), "reference": list(REFERENCE_ARMS), "wx": list(WX_ARMS), "preference_order": list(PREFERENCE_ORDER), "candidate_arms": list(CANDIDATE_ARMS)},
        "calibrated": dict(CALIBRATED),
        "cell_types": {
            c.token: {"cell_type": c.name, "facts": c.facts, "slots": c.slots, "update_multiplier": c.multiplier, "readout_multipliers": list(c.readouts)} for c in CELLTYPES.values()
        },
        "matrix": {"q1_draws_first": Q1_DRAWS[0], "q1_draws_last": Q1_DRAWS[-1], "probe_draws": list(PROBE_DRAWS), "q1_cells": Q1_CELL_COUNT, "q1_cells_cut3": Q1_CUT3_CELL_COUNT, "wx_cells": WX_CELL_COUNT, "probe_cells": PROBE_CELL_COUNT, "check_cells": CHECK_CELL_COUNT},
        "seeds": {
            "registered_base": REGISTERED_BASE, "draw_stride": DRAW_STRIDE, "reserve_bases": [RESERVE_BASES[1], RESERVE_BASES[2]], "init": list(INIT_SEEDS),
            "check_base": CHECK_BASE, "rehearsal_base": REHEARSAL_BASE, "check_init": CHECK_INIT, "rehearsal_init": REHEARSAL_INIT,
            "test_base": TEST_SEED_BASE, "test_top": TEST_SEED_TOP, "range_low": S0_RANGE[0], "range_high": S0_RANGE[1],
            "fact_set_offsets": [FACT_SET_OFFSET[f] for f in FACT_SETS], "target_offsets": [TARGET_OFFSET["2K/4K"], TARGET_OFFSET["8K/16K"], TARGET_OFFSET["32K/64K"]], "swap_offsets": [SWAP_OFFSET[f] for f in FACT_SETS],
        },
        "thresholds": {
            "success_fraction_of_a6": SUCCESS_FRACTION_OF_A6, "a6_min_accuracy": A6_MIN_ACCURACY, "a6_min_accuracy_overload": A6_MIN_ACCURACY_OVERLOAD, "dependence_fraction": DEPENDENCE_FRACTION,
            "stable_threshold": STABLE_THRESHOLD, "lm_margin": LM_MARGIN, "paired_threshold": PAIRED_THRESHOLD, "consistency_max_failed_draws": CONSISTENCY_MAX_FAILED_DRAWS,
            "max_not_evaluated_draws": MAX_NOT_EVALUATED_DRAWS, "max_failed_reliable": MAX_FAILED_RELIABLE, "min_successes_20": MIN_SUCCESSES["20"], "min_successes_10": MIN_SUCCESSES["10"],
        },
        "generation": {"cap_seconds": GENERATION_PROVISIONAL_CAP_SECONDS, "provisional": True, "measured_seconds": 0.0, "floor_seconds": GENERATION_FLOOR_SECONDS},
        "resources": {
            "rss_worker_bytes": RSS_WORKER_BYTES, "rss_aggregate_bytes": RSS_AGGREGATE_BYTES, "rehearsal_peak_limit_bytes": REHEARSAL_PEAK_LIMIT_BYTES, "workers": WORKERS, "cap_hours": DEFAULT_CAP_HOURS,
            "headroom": HEADROOM, "rehearsal_updates": REHEARSAL_UPDATES, "rehearsal_busy_processes": REHEARSAL_BUSY_PROCESSES,
        },
    }


def validate_config(data: dict[str, Any]) -> dict[str, Any]:
    """Everything but the ``generation`` block must equal the constants; the generation block (set by the rehearsal, before the freeze) is checked for form: cap at least the floor and not provisional
    unless it is the placeholder."""
    expected = registered_config()
    expected.pop("generation")
    expected["resources"] = {k: v for k, v in expected["resources"].items() if k != "cap_hours"}
    resources = data.get("resources")
    if not isinstance(resources, dict) or "cap_hours" not in resources:
        raise ValueError("P10S0 config needs resources.cap_hours")
    hours_value = resources["cap_hours"]
    if isinstance(hours_value, bool) or not isinstance(hours_value, int | float) or not math.isfinite(float(hours_value)) or float(hours_value) <= 0:
        raise ValueError("P10S0 config: resources.cap_hours must be a positive finite number (it is the one place the hour cap is set)")
    _validate({k: ({kk: vv for kk, vv in v.items() if kk != "cap_hours"} if k == "resources" else v) for k, v in data.items() if k != "generation"}, expected, "P10S0 config")
    g = data.get("generation")
    if not isinstance(g, dict) or set(g) != {"cap_seconds", "provisional", "measured_seconds", "floor_seconds"}:
        raise ValueError("P10S0 config needs a [generation] block")
    if g["floor_seconds"] != GENERATION_FLOOR_SECONDS or float(g["cap_seconds"]) < GENERATION_FLOOR_SECONDS or not isinstance(g["provisional"], bool):
        raise ValueError("P10S0 config: the generation cap is below the floor of 60 s or malformed")
    if not g["provisional"] and float(g["cap_seconds"]) != max(GENERATION_FLOOR_SECONDS, 2.0 * float(g["measured_seconds"])):
        raise ValueError("P10S0 config: a set generation cap must be max(60 s, 2 x the measured generation time of the rehearsal draw)")
    return data


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_config(path: Path | None = None) -> dict[str, Any]:
    with (path or repo_root() / DEFAULT_CONFIG).open("rb") as stream:
        return validate_config(tomllib.load(stream))


def render_config_toml(generation: Mapping[str, Any] | None = None, cap_hours_value: float | None = None) -> str:
    """The canonical text of ``configs/p10s0_qualification.toml`` (a test requires byte equality with the constants; ``generation`` is the block the rehearsal sets, provisional by default)."""
    from studies.p9i.core import _toml_lines

    header = [
        "# ADR-0020 revision 4 (P10S0) registered constants. Generated by studies.p10s0.core.render_config_toml",
        "# and validated against studies.p10s0.core; any difference is refused. The [generation] block is set by the",
        "# rehearsal (stages set-generation-cap) before the freeze; the freeze refuses while it is provisional.",
        "",
    ]
    cfg = registered_config()
    if generation is not None:
        cfg["generation"] = dict(generation)
    if cap_hours_value is not None:
        cfg["resources"]["cap_hours"] = float(cap_hours_value)
    return "\n".join([*header, *_toml_lines(cfg, "")]) + "\n"


def generation_block(config: Path | None = None) -> dict[str, Any]:
    return dict(load_config(config)["generation"])


def set_generation_cap(measured_seconds: float) -> dict[str, Any]:
    """The generation block the rehearsal sets: cap = max(60 s, 2 x the measured generation time of the rehearsal draw (all three fact sets)); no longer provisional."""
    if not math.isfinite(measured_seconds) or measured_seconds <= 0:
        raise ValueError("the measured generation time must be a positive finite number")
    return {"cap_seconds": max(GENERATION_FLOOR_SECONDS, 2.0 * measured_seconds), "provisional": False, "measured_seconds": float(measured_seconds), "floor_seconds": GENERATION_FLOOR_SECONDS}


def cap_hours(config: Path | None = None) -> float:
    """The hour cap of the one budget, read from the config (the only place it is set; the freeze hashes the config)."""
    return float(load_config(config)["resources"]["cap_hours"])


def resource_limits(config: Path | None = None) -> dict[str, Any]:
    """The caps read from the config file (not from the constants): per worker, aggregate, the rehearsal peak limit, the cap in charged hours and the worker count."""
    r = load_config(config)["resources"]
    return {k: r[k] for k in ("rss_worker_bytes", "rss_aggregate_bytes", "rehearsal_peak_limit_bytes", "workers", "cap_hours", "headroom")}


# --- identity hashes ------------------------------------------------------------------------------------------------------------------
def source_hashes(root: Path | None = None) -> dict[str, str]:
    """SHA-256 of every ``studies/p10s0/*.py`` and launch script, of every ``studies/p9ii/*.py`` (S0 imports it), of the imported ``studies/p9i`` and ``studies/p9`` modules."""
    base = root or repo_root()
    out: dict[str, str] = {}
    for p in sorted((base / "studies" / "p10s0").glob("*.py")):
        out[f"studies/p10s0/{p.name}"] = file_sha256(p)
    for p in sorted((base / LAUNCH_DIR).glob("*.sh")):
        out[f"studies/p10s0/launch/{p.name}"] = file_sha256(p)
    for p in sorted((base / "studies" / "p9ii").glob("*.py")):
        out[f"studies/p9ii/{p.name}"] = file_sha256(p)
    for name in IMPORTED_P9I_MODULES:
        out[f"studies/p9i/{name}.py"] = file_sha256(base / "studies" / "p9i" / f"{name}.py")
    for name in IMPORTED_P9_MODULES:
        out[f"studies/p9/{name}.py"] = file_sha256(base / "studies" / "p9" / f"{name}.py")
    return out


def source_digest(root: Path | None = None) -> str:
    return sha256(canonical_json(source_hashes(root)))


def spec_sha256(root: Path | None = None) -> str:
    return file_sha256((root or repo_root()) / SPEC)


def config_sha256(path: Path | None = None) -> str:
    return sha256(canonical_json(load_config(path)))


def code_identity(root: Path | None = None) -> dict[str, str]:
    from arborlm import p8_core

    base = root or repo_root()
    return {"source_sha256": source_digest(base), "spec_sha256": spec_sha256(base), "config_sha256": config_sha256(base / DEFAULT_CONFIG), "frozen_source_sha256": p8_core.source_digest()}


def environment() -> dict[str, Any]:
    """OS, machine, processor, Python and torch versions and thread settings (every run manifest carries it; gates assert bit-identity on the registered platform only)."""

    def version(package: str) -> str | None:
        try:
            return metadata.version(package)
        except metadata.PackageNotFoundError:
            return None

    return {
        "platform": platform.platform(), "system": platform.system(), "release": platform.release(), "machine": platform.machine(), "processor": platform.processor(),
        "python": sys.version, "python_implementation": platform.python_implementation(), "torch": torch.__version__, "psutil": version("psutil"), "cpu_count": os.cpu_count(),
        "threads": {
            "torch_num_threads": torch.get_num_threads(), "torch_interop_threads": torch.get_num_interop_threads(), "deterministic_algorithms": bool(torch.are_deterministic_algorithms_enabled()),
            "env": {k: os.environ.get(k) for k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "PYTHONHASHSEED")},
        },
    }  # fmt: skip


def on_registered_platform() -> bool:
    """The registered platform is Apple silicon macOS (ADR-0020 section 10.4); bit-identity tests are asserted there only."""
    return platform.system() == "Darwin" and platform.machine() == "arm64"


# --- run names, records and paths -------------------------------------------------------------------------------------------------------
def utc_stamp(now: datetime | None = None) -> str:
    return (now or datetime.now(UTC)).strftime("%Y%m%dT%H%M%S%fZ")


def run_name(stage: str, now: datetime | None = None, unique: str | None = None) -> str:
    """``P10S0<code>-<utc>-<uuid hex>`` for a stage in ``STAGE_CODES`` (study code P10S0)."""
    if stage not in STAGE_CODES:
        raise ValueError(f"unknown P10S0 stage {stage!r}")
    return f"{STUDY}{STAGE_CODES[stage]}-{utc_stamp(now)}-{unique or uuid.uuid4().hex}"


def parse_run_name(name: str) -> tuple[str, str, str]:
    head, _, rest = name.partition("-")
    stamp, _, unique = rest.partition("-")
    codes = {code: stage for stage, code in STAGE_CODES.items()}
    if not head.startswith(STUDY) or head[len(STUDY) :] not in codes or not stamp.endswith("Z") or not unique:
        raise ValueError(f"not a P10S0 run name: {name!r}")
    return codes[head[len(STUDY) :]], stamp, unique


def envelope(kind: str) -> dict[str, Any]:
    if kind not in RECORD_KINDS:
        raise ValueError(f"unknown record kind {kind!r}")
    return {"kind": kind, "schema": SCHEMA, "study": STUDY}


def write_record(path: Path, record: Mapping[str, Any]) -> None:
    if record.get("study") != STUDY or record.get("schema") != SCHEMA or record.get("kind") not in RECORD_KINDS:
        raise ValueError("P10S0 record needs study, schema and a registered kind")
    path.parent.mkdir(parents=True, exist_ok=True)
    out = dict(record)
    if record["kind"] not in UNSTAMPED_KINDS:
        out = stamp(jsonable(out))
        assert_provenance(json.dumps(out, default=str, ensure_ascii=False), f"{record['kind']} record")
    write_json(path, out)


def read_record(path: Path, kind: str | None = None) -> dict[str, Any]:
    record = read_json(path)
    if not isinstance(record, dict) or record.get("study") != STUDY or record.get("schema") != SCHEMA:
        raise ValueError(f"not a P10S0 record: {path}")
    if kind is not None and record.get("kind") != kind:
        raise ValueError(f"expected a {kind!r} record, got {record.get('kind')!r}: {path}")
    return record


def cell_dir(run_dir: Path, label: str) -> Path:
    parse_label(label)
    return run_dir / "cells" / label


def snapshot_stem(update: int) -> str:
    return f"u{update:07d}"


def eval_path(run_dir: Path, label: str, update: int) -> Path:
    return cell_dir(run_dir, label) / "eval" / snapshot_stem(update) / "eval.json"


def default_experiments_root(repo: Path | None = None) -> Path:
    return p9core.default_experiments_root(repo)


# --- the one charged-time ledger (16 hours, section 10.4) -------------------------------------------------------------------------------------
class LedgerRefused(RuntimeError):
    """A stage cannot start: the remainder of the 16-hour cap is smaller than the stage's own cap."""


class Ledger:
    """Charged wall time of the one S0 budget. Entries are appended to one JSON file; nothing is removed. It covers the pipeline check, the rehearsal, the gates and every registered block."""

    def __init__(self, path: Path, cap_seconds: float | None = None) -> None:
        self.path = path
        self.cap_seconds = cap_seconds if cap_seconds is not None else cap_hours() * 3600.0

    def entries(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        data = read_json(self.path)
        if not isinstance(data, dict) or data.get("study") != STUDY or data.get("kind") != "ledger":
            raise ValueError(f"not a P10S0 ledger: {self.path}")
        return list(data["entries"])

    def charged(self) -> float:
        return float(sum(float(e["seconds"]) for e in self.entries()))

    def remaining(self) -> float:
        return max(0.0, self.cap_seconds - self.charged())

    def require_room(self, stage: str, stage_cap_seconds: float) -> None:
        if stage_cap_seconds <= 0:
            raise LedgerRefused(f"stage {stage}: the stage cap must be positive")
        if self.remaining() < stage_cap_seconds:
            raise LedgerRefused(f"stage {stage}: {self.remaining():.0f} s of the S0 budget ({self.cap_seconds:.0f} s) remain, less than the stage cap of {stage_cap_seconds:.0f} s; the work stops and returns to the human lead")

    def charge(self, stage: str, run: str, seconds: float) -> None:
        entries = self.entries()
        entries.append({"stage": stage, "run": run, "seconds": max(0.0, float(seconds)), "utc": datetime.now(UTC).isoformat()})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        write_json(self.path, {"study": STUDY, "schema": SCHEMA, "kind": "ledger", "cap_seconds": self.cap_seconds, "entries": entries})


def ledger_for(root: Path, config: Path | None = None) -> Ledger:
    return Ledger(root / f"{STUDY}-ledger.json", cap_hours(config) * 3600.0)


# --- analytical cost counts (labelled analytical; no efficiency claim) -----------------------------------------------------------------------------
def analytical_cost(arm: str, slots: int, updates: int) -> dict[str, Any]:
    """ANALYTICAL counts, not measurements: ``studies.p9ii.core.analytical_cost`` of the base arm, plus WX's wider projection (2,048 columns) and the read swap's extra forwards.
    Measured CPU seconds are recorded separately (descriptive; no efficiency claim; never a speedup)."""
    out = p9iicore.analytical_cost(base_arm(arm), slots, updates)
    out["query_projection_columns"] = WX_FEATURES if is_wx(arm) else (WINDOW * HIDDEN_WIDTH if arm not in ("A6", "A7") else 0)
    return out


P9II_ACCEPTANCE_QUOTE = "yes I do, yes we can raise to 16 and I approve the package"
P9II_ACCEPTANCE_SOURCE = "docs/decisions/ADR-0019-robust-sparse-address-learning.md"


def p9ii_acceptance(repo: Path | None = None) -> dict[str, Any]:
    """Whether the human lead's acceptance of the P9-II outcome is recorded (ADR-0019 section 16, verbatim) in this tree: read from the file, never assumed."""
    base = repo or repo_root()
    path = base / P9II_ACCEPTANCE_SOURCE
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    return {"accepted": P9II_ACCEPTANCE_QUOTE in text, "source": f"{P9II_ACCEPTANCE_SOURCE} section 16", "quote": P9II_ACCEPTANCE_QUOTE if P9II_ACCEPTANCE_QUOTE in text else None, "source_sha256": file_sha256(path) if path.is_file() else None}


def hours(seconds: float) -> float:
    return seconds / 3600.0


def finite(value: float) -> bool:
    return math.isfinite(value)
