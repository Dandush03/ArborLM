"""P8 shared contract: registry, constants, identities, verified backbone and training-data loading.

Specification: docs/decisions/ADR-0015-p8-locality-aware-memory-training.md. Every constant below is
copied from that ADR; nothing here chooses a scientific value. The regularizer constants (BETA,
ALPHA, GROUP, WINDOW) live here and nowhere else.

Nothing in this module returns validation or evaluation data: ``load_training`` opens the frozen
training bytes and the dataset manifest only.

Status: implementation self-checked only. Not independent review, not Astra validation.
"""

import random
import tempfile
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, cast

from .config import _validate
from .io import canonical_json, file_sha256, read_json, sha256
from .p5_config import FIXED as FIXED
from .p5_config import FLAT as FLAT
from .p5_config import LEARNED as LEARNED
from .p5_config import PARENT_RESULTS, PARENT_SUITE

if TYPE_CHECKING:
    import torch

    from .p4_model import Backbone
    from .p5_model import Model

SPEC = "docs/decisions/ADR-0015-p8-locality-aware-memory-training.md"
STUDY = "P8"
FAMILY = "P8_LOCALITY_AWARE_MEMORY_TRAINING"
SCHEMA = 1
DEFAULT_CONFIG = Path("configs/p8_locality_training.toml")

# --- local inputs (names only; the roots are always CLI arguments) -------------------------------
P4_SUITE = PARENT_SUITE
P5_SUITE = "P5HIER-20261113T125206040109Z-8a40c493791641028f8eb8dfa26f71be"
P5_QUALITY = "P5QUALITY-20261113T125206040450Z-aa1f203f012e4112bf137cd09944bb92"
P5_RESULTS = Path("results/p5-2026-11-13")
STAGE_PREFIX = "P8T"  # training stage run directories: P8T-<utc>-<uuid>; dry runs: P8TD-...
RESTORE_PREFIX = "P8TR"
INVARIANCE_PREFIX = "P8TI"
REHEARSAL_PREFIX = "P8TH"

# --- matrix (ADR section 5) ----------------------------------------------------------------------
CASES = ("C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08", "C09", "C10")
CASE_VARIANT = {
    "C01": FLAT,
    "C02": FIXED,
    "C03": LEARNED,
    "C04": FLAT,
    "C05": LEARNED,
    "C06": FLAT,
    "C07": LEARNED,
    "C08": FLAT,
    "C09": LEARNED,
    "C10": LEARNED,
}
REG_CONC, REG_CO, REG_TEMP = "conc", "co", "temp"
REGULARIZERS = (REG_CONC, REG_CO, REG_TEMP)
CASE_OBJECTIVE: dict[str, tuple[str, ...]] = {
    "C01": (),
    "C02": (),
    "C03": (),
    "C04": (REG_CONC,),
    "C05": (REG_CONC,),
    "C06": (REG_CO,),
    "C07": (REG_CO,),
    "C08": (REG_TEMP,),
    "C09": (REG_TEMP,),
    "C10": (REG_CO, REG_TEMP),
}
CASE_BASELINE = {
    "C04": "C01",
    "C05": "C03",
    "C06": "C01",
    "C07": "C03",
    "C08": "C01",
    "C09": "C03",
    "C10": "C03",
}
CASE_FLAT_COUNTERPART = {"C02": "C01", "C03": "C01", "C05": "C04", "C07": "C06", "C09": "C08"}
PARENTS = ((101, 301), (102, 302), (103, 303))
SEEDS = (601, 602)
STEPS, BATCH, CONTEXT, CYCLE_ROWS = 512, 8, 64, 2048
TRAIN_TARGETS = STEPS * BATCH * CONTEXT
CHECKPOINT_STEPS = (0, 256, 512)
REACH_UPDATES = (1, 128, 256, 384, 512)
SLOTS, BRANCHES, PER_BRANCH, TOP, KEY_WIDTH = 4096, 16, 256, 8, 16
FROZEN_PARAMETERS = 27392
ADDITION_PARAMETERS = {FLAT: 198145, FIXED: 198145, LEARNED: 198401}

# --- the regularizer constants (ADR sections 3 and 4): one place ---------------------------------
BETA = 0.25  # soft-inclusion temperature
ALPHA = 0.5  # matched-pressure dose
GROUP = 8  # reference group size, g(i) = floor(i / 8)
WINDOW = 8  # causal temporal reuse window
LAMBDA_FLOOR = 1e-12  # ||g_R|| below this: lambda = 0 and the event is counted
SOFT_TOP = 64  # pi is computed on the 64 highest-scoring candidates only (revision 2)

# --- data (ADR section 6) ------------------------------------------------------------------------
TRAIN_RANKS = (0, 2048)
CAL_RANKS = (2048, 2560)
PANEL_A_RANKS = (3072, 3584)
PANEL_B_RANKS = (3584, 4096)
PANEL_FIRST_RANKS = ((0, 512), (512, 1024), (1024, 1536), (1536, 2048), (2048, 2560), (2560, 3072))

# --- measurement constants (ADR section 7.1; consumed by the evaluation and simulation code) -----
PERMUTE_SEED_OFFSET = 80000
EVAL_QUERIES, EVAL_CONTEXTS = 32768, 512
PRIMARY_SETTING = (2, 32)  # (rows per page, cached pages)
CONFIRMATION_SETTING = (8, 8)
CRITERION_SETTINGS = (PRIMARY_SETTING, CONFIRMATION_SETTING)
TIES = ("asc", "desc")
PARTITION_SEEDS = (91601, 91602, 91603, 91604, 91605)
PANEL_A_NULL_SEEDS = (91331, 91332, 91333)
PANEL_B_NULL_SEEDS = (91341, 91342, 91343)
ORDER_SHUFFLE_SEED = 91201
NULL_GENERATOR = "random.Random(replicate_seed * 1000 + cell_index)"
TEMPORAL_WINDOW_QUERIES = 8
WARM_CONTEXTS, COUNT_CONTEXTS = 256, 256
TOP_SLOTS_SHARE = 64

# --- screening margins and guards (ADR section 7.3; data only, applied by the analysis code) -----
MATERIAL_RATIO, BAND_LOW, BAND_HIGH, WORSE_RATIO = 0.80, 0.90, 1.10, 1.25
QUALITY_DELTA = 0.005
RETENTION_MIN, QUALITY_PAIRS_ABOVE_MAX, E_NULL_FLOOR = 0.75, 1, 0.05
UTIL_RETAINED, UTIL_COLLAPSED = 0.80, 0.50

# --- stage caps (ADR section 11): seconds of active wall time; bytes --------------------------
PANEL_CAP = 600.0
TRAIN_STAGE_CAP, TRAIN_CELL_CAP = 5400.0, 600.0
EVAL_CAP = 1800.0
SIM_CAP = 5400.0
ANALYSIS_CAP = 600.0
AUDITOR_CAP = 3600.0
STUDY_CAP = 8 * 3600.0
WORKERS = 4
RSS_WORKER = 2 * 1024**3
RSS_AGGREGATE = 8 * 1024**3
REHEARSAL_MAX_FRACTION = 0.5
POLL_SECONDS = 0.1

_REGISTERED: dict[str, Any] = {
    "schema_version": 1,
    "experiment_family": FAMILY,
    "spec_reference": SPEC,
    "p4_suite": P4_SUITE,
    "p5_suite": P5_SUITE,
    "p5_quality": P5_QUALITY,
    "cases": list(CASES),
    "case_variant": dict(CASE_VARIANT),
    "case_objective": {k: list(v) for k, v in CASE_OBJECTIVE.items()},
    "case_baseline": dict(CASE_BASELINE),
    "case_flat_counterpart": dict(CASE_FLAT_COUNTERPART),
    "backbones": [101, 102, 103],
    "orders": [301, 302, 303],
    "seeds": [601, 602],
    "model": {
        "slots": 4096,
        "branches": 16,
        "per_branch": 256,
        "top": 8,
        "backbone_parameters": 27392,
        "flat_parameters": 198145,
        "learned_tree_parameters": 198401,
    },
    "training": {
        "steps": 512,
        "batch": 8,
        "context": 64,
        "cycle_rows": 2048,
        "optimizer": "fresh-adr0005-AdamW-only-addition",
        "checkpoint_steps": [0, 256, 512],
        "reach_updates": [1, 128, 256, 384, 512],
    },
    "regularizer": {
        "beta": 0.25,
        "alpha": 0.5,
        "group": 8,
        "window": 8,
        "lambda_floor": 1e-12,
        "soft_top": 64,
        "clip_norm": 1.0,
    },
    "data": {
        "train_ranks": [0, 2048],
        "calibration_ranks": [2048, 2560],
        "panel_a_ranks": [3072, 3584],
        "panel_b_ranks": [3584, 4096],
    },
    "measurement": {
        "permute_seed_offset": 80000,
        "primary_setting": [2, 32],
        "confirmation_setting": [8, 8],
        "partition_seeds": [91601, 91602, 91603, 91604, 91605],
        "panel_a_null_seeds": [91331, 91332, 91333],
        "panel_b_null_seeds": [91341, 91342, 91343],
        "order_shuffle_seed": 91201,
        "warm_contexts": 256,
        "count_contexts": 256,
    },
    "margins": {
        "material_ratio": 0.80,
        "band_low": 0.90,
        "band_high": 1.10,
        "worse_ratio": 1.25,
        "quality_delta": 0.005,
        "retention_min": 0.75,
        "quality_pairs_above_max": 1,
        "e_null_floor": 0.05,
        "util_retained": 0.80,
        "util_collapsed": 0.50,
    },
    "limits": {
        "panel_seconds": 600,
        "train_stage_seconds": 5400,
        "train_cell_seconds": 600,
        "eval_seconds": 1800,
        "sim_seconds": 5400,
        "analysis_seconds": 600,
        "auditor_seconds": 3600,
        "study_seconds": 28800,
        "workers": 4,
        "rss_worker_bytes": 2147483648,
        "rss_aggregate_bytes": 8589934592,
        "rehearsal_max_fraction": 0.5,
    },
}


def validate_config(data: dict[str, Any]) -> dict[str, Any]:
    _validate(data, _REGISTERED, "P8 config")
    return data


def load_config(path: Path | None = None) -> dict[str, Any]:
    with (path or repo_root() / DEFAULT_CONFIG).open("rb") as stream:
        return validate_config(tomllib.load(stream))


def config_sha256(path: Path | None = None) -> str:
    return sha256(canonical_json(load_config(path)))


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


class Parented(Protocol):
    """Anything with a parent and an order (a P8 cell or P5's cell)."""

    @property
    def parent_label(self) -> str: ...

    @property
    def order(self) -> int: ...


# --- cells ---------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Cell:
    backbone: int
    order: int
    seed: int
    case: str

    def __post_init__(self) -> None:
        if (
            (self.backbone, self.order) not in PARENTS
            or self.seed not in SEEDS
            or self.case not in CASES
        ):
            raise ValueError("unregistered P8 cell")

    @property
    def variant(self) -> str:
        return CASE_VARIANT[self.case]

    @property
    def objective(self) -> tuple[str, ...]:
        return CASE_OBJECTIVE[self.case]

    @property
    def parent_label(self) -> str:
        return f"b{self.backbone}-o{self.order}-baseline"

    @property
    def label(self) -> str:
        return f"b{self.backbone}-o{self.order}-s{self.seed}-{self.case}"

    @property
    def index(self) -> int:
        return 20 * (self.backbone - 101) + 10 * SEEDS.index(self.seed) + CASES.index(self.case)

    def fields(self) -> dict[str, Any]:
        return asdict(self)


def cells() -> list[Cell]:
    """The 60 registered cells in index order."""
    result = [Cell(b, o, seed, case) for (b, o) in PARENTS for seed in SEEDS for case in CASES]
    if [c.index for c in result] != list(range(60)):
        raise ValueError("P8 registry index order broken")
    return result


def parse_label(label: str) -> Cell:
    for cell in cells():
        if cell.label == label:
            return cell
    raise ValueError(f"unregistered P8 cell label: {label!r}")


def all_labels() -> list[str]:
    return [cell.label for cell in cells()]


# --- hashing and identity ------------------------------------------------------------------------
def source_hashes(root: Path | None = None) -> dict[str, str]:
    """SHA-256 of every ``*.py`` file under ``src/arborlm/`` (all modules)."""
    base = root or Path(__file__).resolve().parent
    return {
        f"src/arborlm/{p.relative_to(base).as_posix()}": file_sha256(p)
        for p in sorted(base.rglob("*.py"))
    }


def source_digest(root: Path | None = None) -> str:
    return sha256(canonical_json(source_hashes(root)))


def spec_sha256(repo: Path | None = None) -> str:
    return file_sha256((repo or repo_root()) / SPEC)


def code_identity() -> dict[str, str]:
    """Compact identity written into every checkpoint and record."""
    return {
        "source_sha256": source_digest(),
        "spec_sha256": spec_sha256(),
        "config_sha256": config_sha256(),
    }


# --- model construction --------------------------------------------------------------------------
def seed_everything(cell: Cell) -> None:
    """Exactly P5's ``_cell`` seeding before model construction."""
    import torch

    random.seed(cell.seed)
    torch.default_generator.manual_seed(cell.seed)


def build_model(cell: Cell, backbone: "Backbone", *, seed_rng: bool = True) -> "Model":
    """The P5 ``Model`` for this cell's variant: same classes, parameters, names, order and init.

    P5's ``Cell`` rejects seeds 601 and 602, but ``Model`` only reads ``cell.variant`` and
    ``cell.seed`` (and ``cell.index`` / ``cell.fields()`` in P5 helpers), so a P8 cell is passed
    directly. ``Memory(variant, seed)`` is the sole initializer, as in P5.
    """
    from .p5_model import Model

    if seed_rng:
        seed_everything(cell)
    return Model(cast(Any, cell), backbone)


# --- verified backbone and training data (training rows only) ------------------------------------
def environment_record() -> dict[str, Any]:
    from .records import record_environment

    with tempfile.TemporaryDirectory() as scratch:
        return record_environment(Path(scratch), family=FAMILY)


def p5_quality_dir(experiments_root: Path) -> Path:
    return experiments_root / P5_SUITE / "quality" / P5_QUALITY


def load_backbone(
    cell: Parented,
    experiments_root: Path,
    environment: dict[str, Any] | None = None,
) -> tuple["Backbone", dict[str, Any]]:
    """Verify and extract the cell's frozen P4 parent exactly as P5's ``_cell`` did.

    Returns the backbone and a JSON-serializable provenance dict.
    """
    from .p5_parent import extract_verified, verify_parent

    quality = p5_quality_dir(experiments_root)
    manifest = read_json(quality / "manifest.json")
    mapping = read_json(quality / "parent_provenance.json")
    if sha256(canonical_json(mapping)) != manifest["parent_provenance_sha256"]:
        raise ValueError("P8 frozen P5 parent map changed")
    expected = mapping[cell.parent_label]
    environment = environment or environment_record()
    parent = verify_parent(
        experiments_root / P4_SUITE,
        repo_root() / PARENT_RESULTS,
        expected["record"],
        environment,
    )
    if parent.provenance != expected["provenance"]:
        raise ValueError("P8 actual parent does not match P5 suite preflight")
    backbone = extract_verified(parent)
    parent.check_unchanged()
    baselines = read_json(quality / "baselines.json")[cell.parent_label]
    from .p4_model import backbone_digest

    digest = backbone_digest(backbone)
    if (
        baselines["backbone_sha256"] != digest
        or baselines["parent_checkpoint_state_sha256"]
        != parent.provenance["checkpoint_state_sha256"]
    ):
        raise ValueError("P8 backbone does not match P5's verified frozen baseline")
    provenance = {
        "parent": parent.provenance,
        "backbone_sha256": digest,
        "order_sha256": parent.identity["order_sha256"],
        "order_file": str(parent.order_file),
        "p5_quality_run": P5_QUALITY,
        "p5_manifest_sha256": file_sha256(quality / "manifest.json"),
    }
    return backbone, provenance


def parent_check(cell: Parented, experiments_root: Path) -> None:
    """Re-verify that the parent checkpoint files are unchanged (cheap, run-time freeze check)."""
    from .p5_parent import verify_parent

    quality = p5_quality_dir(experiments_root)
    mapping = read_json(quality / "parent_provenance.json")
    expected = mapping[cell.parent_label]
    verify_parent(
        experiments_root / P4_SUITE,
        repo_root() / PARENT_RESULTS,
        expected["record"],
        environment_record(),
    ).check_unchanged()


def load_training(
    cell: Parented, experiments_root: Path
) -> tuple["torch.Tensor", list[int], dict[str, str]]:
    """P5's frozen training rows (ranks 0..2047 of the 4,096-row pool are the trained ones) and
    the parent's order. Opens ``dataset_manifest.json`` and ``train.bytes`` only: no validation
    file is read. Returns ``(train_tensor [4096, 65] int64, order_ids, hashes)``."""
    import torch

    from .p2_config import TRAIN_RANKED
    from .p2_data import P1_TRAIN_SHA256
    from .pilot_data import CHUNK_BYTES

    quality = p5_quality_dir(experiments_root)
    frozen = quality / "frozen-data"
    manifest_hash = read_json(quality / "manifest.json")["dataset_manifest_sha256"]
    dataset = read_json(frozen / "dataset_manifest.json")
    checksums = dataset["checksums_sha256"]
    if (
        sha256(canonical_json(dataset)) != manifest_hash
        or checksums["train.bytes"] != P1_TRAIN_SHA256
    ):
        raise ValueError("P8 frozen training data identity mismatch")
    raw = (frozen / "train.bytes").read_bytes()
    if sha256(raw) != checksums["train.bytes"] or len(raw) != TRAIN_RANKED * CHUNK_BYTES:
        raise ValueError("P8 frozen training bytes mismatch")
    train = (
        torch.frombuffer(bytearray(raw), dtype=torch.uint8)
        .long()
        .reshape(TRAIN_RANKED, CHUNK_BYTES)
    )
    mapping = read_json(quality / "parent_provenance.json")[cell.parent_label]
    order_file = (
        experiments_root / P4_SUITE / "cells" / mapping["provenance"]["run_id"] / "order.json"
    )
    order = read_json(order_file)
    ids = order["ranked_train_row_ids"]
    if (
        sorted(ids) != list(range(CYCLE_ROWS))
        or order["generator_seed"] != cell.order
        or file_sha256(order_file) != mapping["provenance"]["checkpoint_identity"]["order_sha256"]
    ):
        raise ValueError("P8 parent order mismatch")
    return (
        train,
        [int(i) for i in ids],
        {
            "dataset_manifest_sha256": manifest_hash,
            "train_bytes_sha256": checksums["train.bytes"],
            "order_sha256": file_sha256(order_file),
        },
    )


def batch_offset(step: int) -> int:
    """P5's batch schedule: two cycles over the parent-ordered rows 0..2047."""
    if not 1 <= step <= STEPS:
        raise ValueError("invalid P8 update")
    return ((step - 1) * BATCH) % CYCLE_ROWS


def ordered_rows(train: "torch.Tensor", order_ids: list[int]) -> "torch.Tensor":
    import torch

    return train[torch.tensor(order_ids, dtype=torch.int64, device="cpu")]


# --- synthetic stand-ins (dry run, rehearsal and tests only; every record is labelled dry_run) ---
def synthetic_backbone(cell: Cell) -> "Backbone":
    """Full-dimension random backbone (27,392 parameters), not a verified parent."""
    from .p2_config import CONTROL
    from .p2_config import Cell as ParentCell
    from .p2_model import FollowupModel
    from .p4_model import extract

    return extract(FollowupModel(ParentCell(cell.backbone, 201, cell.order, CONTROL)))


def synthetic_training(cell: Cell) -> tuple["torch.Tensor", list[int], dict[str, str]]:
    """Synthetic bytes at the real shape: [4096, 65] int64 rows and a permutation of 0..2047."""
    import torch

    from .p2_config import TRAIN_RANKED
    from .pilot_data import CHUNK_BYTES

    generator = torch.Generator().manual_seed(8000 + cell.backbone * 10 + cell.order)
    train = torch.randint(0, 256, (TRAIN_RANKED, CHUNK_BYTES), generator=generator)
    order = torch.randperm(CYCLE_ROWS, generator=generator).tolist()
    return train, [int(i) for i in order], {"synthetic": "true"}
