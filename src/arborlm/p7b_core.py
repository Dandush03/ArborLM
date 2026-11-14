"""P7-B shared definitions: registry, names, identities, trace access, null streams, hashes.

Specification: docs/decisions/ADR-0014-p7b-coaccess-layout-equivalence.md (HUMAN-APPROVED FOR
EXECUTION, revision 4 as pushed in commit 2908ef4, with the section 15 pre-outcome clarifications).
Every constant below is copied from that ADR; nothing here chooses a scientific value. Pure integer
bookkeeping; no model is imported at module level.

Status: implementation self-checked only. Not independent review, not Astra validation.
"""

import math
import struct
import subprocess
from pathlib import Path
from typing import Any

from torch import Tensor

from . import p7a_core as a_core
from .io import file_sha256, read_json, sha256
from .p5_config import FIXED as FIXED
from .p5_config import FLAT as FLAT
from .p5_config import LEARNED as LEARNED
from .p6_common import Pair as Pair

SPEC = "docs/decisions/ADR-0014-p7b-coaccess-layout-equivalence.md"
STUDY = "P7-B"
FAMILY = "P7B_COACCESS_LAYOUT_EQUIVALENCE"
SCHEMA_PANEL = "P7B-panel-v1"
SCHEMA_LAYOUT = "P7B-layout-v1"
SCHEMA_TRACE_B = "P7B-trace-b-v1"
SCHEMA_SIM = "P7B-simulation-v1"
SCHEMA_ANALYSIS = "P7B-analysis-v1"
SCHEMA_PANEL_CONFIRMATION = "p7b-panel-confirmation-v1"
SCHEMA_LAYOUT_CONFIRMATION = "p7b-layout-confirmation-v1"
SCHEMA_RESIM_CONFIRMATION = "p7b-resim-confirmation-v1"
P5_RESULTS = Path("results/p5-2026-11-13")
P7A_RESULTS = Path("results/p7a-2026-11-13")
DEFAULT_RESULTS = Path("results/p7b-2026-11-13")

HUMAN_APPROVAL = (
    "ADR-0014 section 15: human execution approval of 2026-11-13 ('Confirm, proceed'), revision 4 "
    "as pushed in commit 2908ef4, with the five pre-outcome engineering clarifications; "
    "study-specific Claude workflow for P7-B only; Astra review NOT_PERFORMED"
)

# --- identities of the existing inputs (ADR-0014 section 3) ---------------------------------------
IDENTITY_MANIFEST = Path("docs/reviews/p7b-spec-inputs-2026-11-13/identity_manifest.json")
IDENTITY_OVERALL_SHA256 = "77dea76d96672b13336415ff325388c9c76d8e3b09cf25f2242d9cfe44e2a86a"
P7A_TRACE_RUN = "P7AT-20261113T213133591303Z-0605157511b24311919ddfab8ac89b2e"
P7A_SIM_RUN = "P7AS-20261113T213357135402Z-af93d829f722456e95f394462eedc57b"

# --- registered constants copied from ADR-0014
SLOTS, BRANCHES, PER_BRANCH, TOP, TREE_VISIT = (
    a_core.SLOTS,
    a_core.BRANCHES,
    a_core.PER_BRANCH,
    a_core.TOP,
    a_core.TREE_VISIT,
)
CONTEXT, CONTEXTS, QUERIES = a_core.CONTEXT, a_core.CONTEXTS, a_core.QUERIES
RS = a_core.RS  # (1, 2, 8, 32, 128, 512)
CS = a_core.CS  # (8, 16, 32, 64, 128)
KINDS = a_core.KINDS
TREE_KINDS = a_core.TREE_KINDS
CAL_START, CAL_END = a_core.CAL_START, a_core.CAL_END  # training-pool ranks 2048-2559
PANEL_B_RANKS = (2560, 3072)  # zero-based, half-open: ranks 2560..3071
RAND_SEEDS = a_core.RAND_SEEDS
STREAM_A_NULL_SEEDS = a_core.FM_SEEDS  # 91301-91303
CAL_NULL_SEEDS = (91311, 91312, 91313)
STREAM_B_NULL_SEEDS = (91321, 91322, 91323)
PARTITION_SEEDS = (91601, 91602, 91603, 91604, 91605)
PARTITION_SHA256 = {
    91601: "ae626b43df264708466a8afc9c2b5434c3db053e7b57f27800b9674192b16487",
    91602: "0d310a05d82ef6eba8cc5adbeba16a88d74a5221353eb0208c1e755f3230e9f3",
    91603: "55cbff61076689e78f030d374b741aa28f448484694f51d3f65dbc56db183af5",
    91604: "98142918ba5f6ef34e6b9d3efc1f27a7c5ea9fd821bfb2b862641145af6f25a2",
    91605: "8d55366cd4d23a08e651161638e0b0cc34dbee0ad13764e3181ffa2b5db26a0c",
}
MAX_PASSES = 12  # section 4 step 2
WINDOW = 8  # section 4 sensitivity variant A8
INDEPENDENT_SELECTION_SEED = a_core.INDEPENDENT_SELECTION_SEED  # 91501
PRIMARY_SETTING = (2, 32)  # (R, C)
CONFIRMATION_SETTING = (8, 8)
CRITERION_SETTINGS = (PRIMARY_SETTING, CONFIRMATION_SETTING)
TIES = ("asc", "desc")  # eviction tie rules: ascending / descending page number
WARM_QUERIES = a_core.WARM_QUERIES

# P5 panel hashes registered in ADR-0010 section 4 / p5_data.py (validation ranks 0..2559)
PRIOR_PANEL_SHA256 = {
    "P1": "2e6b71b9472abf50f9c4705f2f8f13a69465a9f1b8360119ce5882872b772200",
    "P2": "8cd4ab927f9ff17f12bba56b011cf11a94d66e1b77f5f4eba97dd100fb455cd2",
    "P3": "a2d63d4ed5300c74f49374c0e0c5bd6e70d4361bc0b2933a8d5ad33a08d724b0",
    "P4": "4c6fb3f3a8f22d2e5b14c6703d3d8e02b40681482d5b93ba491e2df0583dc28f",
    "P5": "d50cbe4c303791148c922bfe9201fe00b192c44deef855077860ffc98cc72b98",
}

# Caps (section 11): seconds of sequential active worker time. RSS limit is the watchdog's 2 GiB.
LAYOUT_CAP, TRACE_B_CAP, SIM_CAP, ANALYSIS_CAP, STUDY_CAP = 2700.0, 600.0, 5400.0, 600.0, 14700.0
AUDITOR_CAP = 3600.0

# --- layout and stream names
L_ID, L_FREQ, L_BFREQ = a_core.LAYOUT_ID, a_core.LAYOUT_FREQ, a_core.LAYOUT_BFREQ
L_RANDS = a_core.LAYOUTS_RAND  # ("L-RAND-91101", ...)
L_COAX, L_BCOAX, L_NCOAX = "L-COAX", "L-BCOAX", "L-NCOAX"
L_COAX8, L_BCOAX8, L_COAXG, L_BCOAXG = "L-COAX8", "L-BCOAX8", "L-COAXg", "L-BCOAXg"
L_PCOAX = tuple(f"L-PCOAX-{i}" for i in range(1, 6))
STREAM_ACTUAL, STREAM_ORDER = "actual", "order_shuffled"
STREAMS_NULL = ("null_1", "null_2", "null_3")
STREAMS_ALL = (STREAM_ACTUAL, STREAM_ORDER, *STREAMS_NULL)
A_NULL_NAMES = dict(zip(STREAMS_NULL, a_core.STREAMS_FM, strict=True))  # P7-A names for 1..3

ROW_SIZE_LABEL = {
    1: "HYPOTHETICAL row size",
    2: "HYPOTHETICAL row size",
    8: "HYPOTHETICAL row size",
    32: "actual 128-byte value rows, 4 KiB pages",
    128: "actual 128-byte value rows, 16 KiB pages",
    512: "actual 128-byte value rows, 64 KiB pages",
}

# L-NCOAX control band (section 7, "Control L-NCOAX")
NCOAX_BAND = (0.97, 1.03)

# Which streams the two evaluation streams are called
STREAMS_EVAL = ("A", "B")


InvariantError = a_core.InvariantError  # a section 10 simulator-invariant violation: a hard stop
TraceIntegrityError = a_core.TraceIntegrityError  # a trace-integrity violation: a hard stop


class GateError(ValueError):
    """A confirmation-file gate or linkage refusal: the stage does not start."""


class StopError(ValueError):
    """A registered stop condition of ADR-0014 section 11 (identity, reproduction, invariant)."""


def is_tree(kind: str) -> bool:
    return kind != FLAT


# --- registry
def registered_checkpoints() -> list[tuple[Pair, str]]:
    return a_core.registered_checkpoints()


def cell_label(pair: Pair, kind: str) -> str:
    return a_core.cell_label(pair, kind)


def cell_index(pair: Pair, kind: str) -> int:
    return a_core.cell_index(pair, kind)


def parse_label(label: str) -> tuple[Pair, str]:
    return a_core.parse_label(label)


def all_labels() -> list[str]:
    return [cell_label(p, k) for p, k in registered_checkpoints()]


def parent_of(pair: Pair) -> tuple[int, int]:
    return a_core.parent_of(pair)


def independent_selection() -> list[str]:
    """ADR-0013 section 14 item 12, as required by ADR-0014 section 10: 18 labels."""
    return a_core.independent_selection()


# --- layout sets
def r_independent_layouts(kind: str) -> tuple[str, ...]:
    base = (L_ID, *L_RANDS, L_FREQ)
    return (*base, L_BFREQ) if is_tree(kind) else base


def coaccess_layouts(kind: str) -> tuple[str, ...]:
    """The R-specific layouts built from calibration (section 11: 9 per R flat, 12 trees)."""
    flat = (L_COAX, L_NCOAX, L_COAX8, L_COAXG, *L_PCOAX)
    tree = (L_BCOAX, L_BCOAX8, L_BCOAXG)
    return (*flat, *tree) if is_tree(kind) else flat


def all_layouts(kind: str) -> tuple[str, ...]:
    return (*r_independent_layouts(kind), *coaccess_layouts(kind))


def is_r_specific(name: str) -> bool:
    return name not in (L_ID, L_FREQ, L_BFREQ, *L_RANDS)


def required_confirmation_layouts(kind: str) -> tuple[str, ...]:
    """Section 10: L-COAX, L-BCOAX, L-NCOAX and all five partition layouts (BCOAX trees only)."""
    base = (L_COAX, L_NCOAX, *L_PCOAX)
    return (*base, L_BCOAX) if is_tree(kind) else base


def layout_key(name: str, rows: int) -> str:
    return f"{name}|R{rows}"


# --- hashing and source identity
def source_hashes(root: Path | None = None) -> dict[str, str]:
    base = root or Path(__file__).resolve().parent
    return {f"src/arborlm/{p.name}": file_sha256(p) for p in sorted(base.glob("p7b_*.py"))}


def package_hashes(root: Path | None = None) -> dict[str, str]:
    """SHA-256 of every ``*.py`` file under ``src/arborlm/`` (all modules, not only ``p7b_*``).
    Cross-stage linkage binds to this map, because a stage imports ``p7a_core``, ``p6_common``,
    ``p5_model``, ``io``, ``records``, ``watchdog`` and others whose change would alter results."""
    base = root or Path(__file__).resolve().parent
    return {
        f"src/arborlm/{p.relative_to(base).as_posix()}": file_sha256(p)
        for p in sorted(base.rglob("*.py"))
    }


def spec_sha256(repo: Path | None = None) -> str:
    return file_sha256((repo or Path.cwd()) / SPEC)


# --- tracked-and-clean checks (Git) and the auditor tool binding -----------------------------
STREAM_B_MANIFEST = "stream_b_identity_manifest.json"
AUDITOR_TOOLS = {
    "panel": "docs/reviews/p7b-preflight-2026-11-13/tools/independent_panel.py",
    "layouts": "docs/reviews/p7b-preflight-2026-11-13/tools/independent_layouts.py",
    "resim": "docs/reviews/p7b-preflight-2026-11-13/tools/independent_resim.py",
}
# Labels used ONLY by the dry run (synthetic data). A gate or the Git check accepts them only when
# the stage is a dry run; a registered run refuses them.
STAND_IN_TOOL = "dry-run stand-in; NOT produced by an independent tool"
STAND_IN_TOOL_SHA256 = "DRY-RUN-STAND-IN-NOT-A-TOOL-HASH"
STAND_IN_GIT_CHECK = "dry-run stand-in: no Git check performed (synthetic data, nothing committed)"


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, check=False)


def auditor_tool_sha256_at_head(kind: str, repo: Path | None = None) -> str:
    """SHA-256 of the tracked auditor tool file as it exists at ``HEAD`` (``git show``). Refuses if
    the file is not in ``HEAD``."""
    root = repo or Path.cwd()
    rel = AUDITOR_TOOLS[kind]
    shown = _git(root, "show", f"HEAD:{rel}")
    if shown.returncode != 0:
        raise GateError(f"refused: auditor tool {rel} is not tracked at HEAD (commit it first)")
    return sha256(shown.stdout)


def tracked_and_clean(path: Path, *, dry_run: bool) -> dict[str, Any]:
    """The file must be tracked by Git and unmodified relative to ``HEAD``
    (``git ls-files --error-unmatch`` and ``git diff --quiet HEAD --``). In a dry run (synthetic
    data, nothing is committed) a clearly labelled stand-in is returned instead; a registered run
    never takes that path."""
    if dry_run:
        return {"git_check": STAND_IN_GIT_CHECK, "stand_in": True, "file": str(path)}
    if not path.is_file():
        raise GateError(f"refused: {path} does not exist")
    cwd, name = path.resolve().parent, path.name
    if _git(cwd, "ls-files", "--error-unmatch", "--", name).returncode != 0:
        raise GateError(f"refused: {path} is not tracked by Git (commit it before any simulation)")
    if _git(cwd, "diff", "--quiet", "HEAD", "--", name).returncode != 0:
        raise GateError(f"refused: {path} differs from HEAD (staged, modified or not committed)")
    return {
        "git_check": "git ls-files --error-unmatch and git diff --quiet HEAD -- : tracked, clean",
        "stand_in": False,
        "file": str(path),
    }


def counts_sha256(counts: list[int]) -> str:
    """SHA-256 of the 4,096 per-slot selection counts as little-endian unsigned 32-bit integers."""
    return sha256(struct.pack(f"<{len(counts)}I", *counts))


def tensor_sha256_int16(tensor: Tensor) -> str:
    values = tensor.reshape(-1).tolist()
    return sha256(struct.pack(f"<{len(values)}h", *values))


def tensor_sha256_int8(tensor: Tensor) -> str:
    values = tensor.reshape(-1).tolist()
    return sha256(struct.pack(f"<{len(values)}b", *values))


def canonical_hash(order: list[int], rows_per_page: int) -> str:
    """ADR-0014 section 4 'Exactness': SHA-256 of the pages in page order, each page's slot IDs
    sorted ascending, as little-endian 16-bit integers. ``order`` lists the slot at each
    position."""
    out = bytearray()
    for start in range(0, len(order), rows_per_page):
        page = sorted(order[start : start + rows_per_page])
        out += struct.pack(f"<{len(page)}H", *page)
    return sha256(bytes(out))


def entropy_nats(counts: list[int]) -> float:
    """Shannon entropy (nats) of the slot-selection distribution; ln of the entropy-effective
    slot count (P5's ``effective_selected_slots`` is exp of this). Deterministic: math.fsum."""
    total = sum(counts)
    if total <= 0:
        raise ValueError("no selections")
    return -math.fsum(c / total * math.log(c / total) for c in counts if c)


# --- identity manifest of the P7-A traces
ROLES = (
    "calibration.selected",
    "calibration.branches",
    "evaluation.selected",
    "evaluation.branches",
)


class Identity:
    """The verified identity manifest of the 270 existing trace files (ADR-0014 section 3).

    ``entry(label)`` returns the manifest entry; ``trace_record(label, part)`` returns a record in
    the shape ``p7a_core.read_trace`` expects for ``part`` in {"calibration", "evaluation"}. The two
    parts are separate so a stage that must not open evaluation traces never asks for them.
    """

    def __init__(self, path: Path, repo: Path, data: dict[str, Any]) -> None:
        self.path, self.repo, self.data = path, repo, data
        self.by_label = {c["label"]: c for c in data["checkpoints"]}

    @property
    def file_sha256(self) -> str:
        return file_sha256(self.path)

    def entry(self, label: str) -> dict[str, Any]:
        entry: dict[str, Any] = self.by_label[label]
        return entry

    def _file(self, label: str, role: str) -> dict[str, Any] | None:
        for entry in self.by_label[label]["files"]:
            if entry["role"] == role:
                return dict(entry)
        return None

    def trace_record(self, label: str, part: str) -> tuple[Path, dict[str, Any]]:
        """(directory, record) for ``part``; a missing branch file (flat) is recorded as None."""
        if part not in ("calibration", "evaluation"):
            raise ValueError(f"unknown trace part {part!r}")
        prefix = "calib" if part == "calibration" else "eval"
        record: dict[str, Any] = {}
        directory: Path | None = None
        for name in ("selected", "branches"):
            entry = self._file(label, f"{part}.{name}")
            if entry is None:
                record[name] = None
                continue
            path = self.repo / entry["relpath"]
            if not path.name.startswith(prefix + "_"):
                raise a_core.TraceIntegrityError(f"{path.name} is not a {part} trace file")
            directory = directory or path.parent
            record[name] = {
                "file": path.name,
                "sha256": entry["recorded_sha256"],
                "shape": entry["shape"],
            }
        if directory is None:
            raise a_core.TraceIntegrityError(f"no {part} trace files recorded for {label}")
        return directory, record

    def recorded_sha(self, label: str, role: str) -> str | None:
        entry = self._file(label, role)
        return None if entry is None else str(entry["recorded_sha256"])


def overall_hash(data: dict[str, Any]) -> str:
    """Recompute the manifest's own overall hash (method as stated in the manifest)."""
    import json

    triples = []
    for c in sorted(data["checkpoints"], key=lambda c: c["cell_index"]):
        for f in sorted(c["files"], key=lambda f: f["role"]):
            triples.append([c["label"], f["role"], f["recorded_sha256"]])
    return sha256(json.dumps(triples, separators=(",", ":"), ensure_ascii=True).encode())


def load_identity(
    repo: Path | None = None, path: Path | None = None, labels: list[str] | None = None
) -> Identity:
    """Read and check the identity manifest: schema, 81 checkpoints, every file matched, and the
    overall hash registered in ADR-0014 section 3. Does not open any trace file."""
    root = repo or Path.cwd()
    file = path or (root / IDENTITY_MANIFEST)
    data = read_json(file)
    if data.get("schema") != "p7b-spec-inputs-identity-manifest-v1":
        raise StopError("identity manifest has an unexpected schema")
    listed = [c["label"] for c in data["checkpoints"]]
    wanted = labels if labels is not None else all_labels()
    if sorted(listed) != sorted(wanted):
        raise StopError("identity manifest does not list exactly the registered checkpoints")
    if data.get("mismatches") or data.get("missing"):
        raise StopError("identity manifest records mismatches or missing files")
    files = sum(len(c["files"]) for c in data["checkpoints"])
    if data["totals"]["trace_files_matching"] != files or (labels is None and files != 270):
        raise StopError("identity manifest does not account for every trace file")
    if overall_hash(data) != data["overall_hash"]["sha256"]:
        raise StopError("identity manifest does not verify")
    if data["overall_hash"]["sha256"] != IDENTITY_OVERALL_SHA256 and path is None:
        raise StopError(
            "identity manifest overall hash differs from the one registered in ADR-0014"
        )
    return Identity(file, root, data)


def p7a_simulation_path(repo: Path, label: str, run: str = P7A_SIM_RUN) -> Path:
    return repo / P7A_RESULTS / "simulate" / run / "workers" / f"{label}.result.json"


def load_p7a_reference(repo: Path, label: str, run: str = P7A_SIM_RUN) -> dict[str, Any]:
    """P7-A's recorded simulation record of one checkpoint (counts only are used)."""
    return load_reference_record(p7a_simulation_path(repo, label, run), label)


def load_reference_record(path: Path, label: str) -> dict[str, Any]:
    """P7-A's recorded simulation record of ``label`` read from ``path``, refused unless the record
    is complete (outcome completed, ``record.complete``)."""
    data = read_json(path)
    if data.get("outcome") != "completed" or not data.get("record", {}).get("complete"):
        raise StopError(f"P7-A simulation record for {label} is not complete")
    record: dict[str, Any] = dict(data["record"])
    return record


def null_streams(
    counts: list[int], seeds: tuple[int, ...], index: int
) -> tuple[list[Tensor], list[dict[str, Any]]]:
    """The exact count-preserving null streams of ADR-0013 section 14 item 8 (reused code),
    generator seed ``s * 1000 + cell_index``; the stream length is ``sum(counts) / 8``."""
    queries = sum(counts) // TOP
    streams: list[Tensor] = []
    info: list[dict[str, Any]] = []
    for seed in seeds:
        stream, detail = a_core.frequency_matched_detail(counts, seed, index, queries=queries)
        streams.append(stream)
        info.append(detail)
    return streams, info
