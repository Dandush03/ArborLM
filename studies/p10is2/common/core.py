# ruff: noqa: E501
"""P10IS2 shared contract (ADR-0025): configs, the fixed oracle-assisted line, the listed seeds and the one seeding function, record envelopes, charged-time ledger, run-directory guard.

Part Q imports from the rest of the package only through ``common/`` (section 11, item 2). Nothing here reads a value of ``configs/p10s2_transfer.toml``: every grid, threshold and seed of this study
is in ``configs/p10is2_partq.toml`` or ``configs/p10is2_partt.toml``. Every generator is created by ``seeded_generator``, which refuses a seed that is not listed for the running mode and records seed and
purpose (section 6). No seed is derived by hashing or arithmetic beyond the listed offsets.
"""

import json
import math
import subprocess
import tomllib
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import torch

from arborlm.io import read_json, write_json

STUDY = "P10IS2"
SCHEMA = 1
SPEC = "docs/decisions/ADR-0025-p10-i-s2-sequential-teacher-transfer.md"
ROOT = Path(__file__).resolve().parents[3]
CONFIG_Q = Path("configs/p10is2_partq.toml")
CONFIG_T = Path("configs/p10is2_partt.toml")
FREEZE_DIR = Path("studies/p10is2/freeze")
PLAN_Q = FREEZE_DIR / "partq_plan.json"
PLAN_T = FREEZE_DIR / "partt_plan.json"
FREEZE_RECORD_Q = FREEZE_DIR / "partq_freeze_record.json"
FREEZE_RECORD_T = FREEZE_DIR / "partt_freeze_record.json"
LAUNCH_DIR = Path("studies/p10is2/launch")
# Part T uses the lock alone (section 13 item 6): no process of Part T may have this directory on its path. The value equals configs/p10is2_partq.toml [paths] durable_packages (a test compares them).
DURABLE_PACKAGES = "/Users/daniellaloush/dandush03/ArborLM/data/datagen-packages"
PARTS = ("Q", "T")
MODES = ("registered", "rehearsal", "test")
TASKS = ("A", "B")  # A: English -> German, B: English -> French
ORDERS = ("AB", "BA")

# Section 5.4: carried directly above every label, class, annotation, composition and cost line, table, caption, machine-readable record and terminal summary.
ORACLE_LINE = (
    "oracle-assisted (word-level addresses supplied by rule); lexical translation of short closed-vocabulary sentences, two capabilities of one kind; "
    "frozen English student; teacher-only training material verified by measured-precision filter; not autonomous learned memory."
)
LEAD_RULE = "S1 and S2 must not claim autonomous learned-memory success from oracle-assisted results."
FIXED_NOTE = "Astra review: NOT_PERFORMED. Self-check only; not independent review and not human approval."

RECORD_KINDS = (
    "freeze_plan", "freeze_record", "rehearsal", "stage_manifest", "block_record", "teacher_run", "qualification", "gates", "ledger", "panel_ledger", "partition_counts", "calibration", "cell_record", "analysis", "report",
    "sealed", "recomputation", "item_error",
)  # fmt: skip


def other_task(t: str) -> str:
    return "B" if t == "A" else "A"


class StageRefused(RuntimeError):
    """A registered entry point refuses to run (no plan, no freeze, no Decision 2, a dirty tree, an identity that differs)."""


class ForcedIdentityPause(Exception):
    """Raised by a rehearsal's identity probe ONLY after it has observed the forced PAUSED — IDENTITY (a plan with one frozen hash altered refused as such) AND the restore (the real plan verifying). A rehearsal
    counts the forced pause as done on this exception and on nothing else: any other refusal is a failure of the rehearsal, never a pass."""


class SeedRefused(RuntimeError):
    """A generator was requested with a seed that is not listed for the running mode."""


class PendingLeadReview(RuntimeError):
    """A question the ADR does not answer: the work stops and returns to the lead (section 11, item 6)."""


# --- configs ---------------------------------------------------------------------------------------------------------------------------------
def load_config(part: str, path: Path | None = None) -> dict[str, Any]:
    if part not in PARTS:
        raise ValueError(f"unknown part {part!r}")
    p = path if path is not None else ROOT / (CONFIG_Q if part == "Q" else CONFIG_T)
    with p.open("rb") as f:
        cfg = tomllib.load(f)
    if cfg.get("study") != STUDY or cfg.get("part") != part:
        raise ValueError(f"{p} is not the Part {part} config of {STUDY}")
    return cfg


def config_path(part: str, repo: Path | None = None) -> Path:
    return (repo or ROOT) / (CONFIG_Q if part == "Q" else CONFIG_T)


# --- seeds -----------------------------------------------------------------------------------------------------------------------------------
def partq_seeds(cfg: Mapping[str, Any], mode: str) -> dict[str, int]:
    """Part Q's named partition-side seeds. Rehearsal mode uses 252901-252914, mirroring 250901-250914 in the listed order; the analysis and disjoint-draw seeds exist only in registered mode."""
    s = cfg["seeds"]
    names = ("partition", "q_fit", "q_check_reserve_order", "source_split", "source_block_order", "control_subsample", "gen_ordinary_windows", "teacher_tokenizer_sentences_and_digest", "tokenization_test_c", "equivalence_injection", "c1_pairing", "seen_items", "timing_items", "regeneration_subsample")  # 250901..250914
    if mode == "registered":
        out = {n: int(s[n]) for n in names}
        out.update({"bootstrap": int(s["bootstrap"]), "disjoint_permutation_a": int(s["disjoint_permutation_a"]), "disjoint_permutation_b": int(s["disjoint_permutation_b"]), "route_accuracy_pieces": int(s["route_accuracy_pieces"])})
        return out
    if mode == "rehearsal":
        vals = [int(s["rehearsal_partition"]), *[int(x) for x in s["rehearsal_streams"]]]
        if vals != list(range(252901, 252915)) or len(vals) != len(names):
            raise ValueError("the Part Q rehearsal seeds must be 252901-252914")
        return dict(zip(names, vals, strict=True))
    if mode == "test":
        extra = ("bootstrap", "disjoint_permutation_a", "disjoint_permutation_b", "route_accuracy_pieces")  # 250915..250918
        return {n: int(s["test_low"]) + i for i, n in enumerate((*names, *extra))}
    raise ValueError(f"unknown mode {mode!r}")


def partt_replicate_values(cfg: Mapping[str, Any], mode: str, index: int = 0) -> dict[str, Any]:
    """Part T's seeds of one replicate (registered r = 0..2), calibration draw (i = 0, 1; repeated 2, 3) or the rehearsal draw: the data seeds base + offset and the initialisation seeds by role j.

    Registered r: 330201 + 10 r + j. Calibration draws 0 and 1: 330231 + 10 i + j. Repeated calibration draws 2 and 3: the listed 330261 + j and 330271 + j, NEVER the formula at i = 2 (that would give the
    rehearsal's 330251 + j). Rehearsal: 330251 + j. Test: 330298, 330299."""
    s = cfg["seeds"]
    offs = [int(o) for o in s["offsets"]]
    roles = list(s["init_roles"])
    if mode == "registered":
        base, init0 = int(s["replicate_bases"][index]), int(s["init_registered"][index])
    elif mode == "calibration":
        if index in (0, 1):
            base, init0 = int(s["calibration_bases"][index]), int(s["init_calibration"][index])
        elif index in (2, 3):
            base, init0 = int(s["repeat_calibration_bases"][index - 2]), int(s["init_repeat_calibration"][index - 2])
        else:
            raise SeedRefused(f"calibration draw {index} has no listed seeds (one repetition is provided for)")
    elif mode == "rehearsal":
        if index != 0:
            raise SeedRefused("the Part T rehearsal uses draw 0 only")
        base, init0 = int(s["rehearsal_base"]), int(s["init_rehearsal"])
    elif mode == "test":
        base, init0 = int(s["test_low"]) + 100 * index, int(s["init_test"][index % 2])
    else:
        raise ValueError(f"unknown mode {mode!r}")
    pieces = int(s["route_accuracy_pieces"]) if mode == "registered" else base + int(s["route_pieces_offset"])  # never the router seed (base + 13) outside registered mode
    data = {"training_draw": base + offs[0], "batch_order": base + offs[1], "permutation_controls": base + offs[2], "code_hash": base + offs[3], "router": base + offs[4]}
    init = {r: init0 + j for j, r in enumerate(roles)}
    return {"base": base, "data": data, "init": init, "init_base": init0, "route_pieces": pieces}


def partt_listed_seeds(cfg: Mapping[str, Any], mode: str) -> frozenset[int]:
    out: set[int] = set()
    n = {"registered": 3, "calibration": 4, "rehearsal": 1, "test": 2}[mode]
    for i in range(n):
        v = partt_replicate_values(cfg, mode, i)
        out |= set(v["data"].values()) | set(v["init"].values())
    if mode == "registered":
        out |= {int(cfg["seeds"]["analysis_bootstrap"]), int(cfg["seeds"]["route_accuracy_pieces"])}
    return frozenset(out)


def g5_probe_seed(cfg: Mapping[str, Any], mode: str) -> int:
    """Gate G5's probe seed: 250919 in a registered run, the test value elsewhere (no literal in code)."""
    return int(cfg["seeds"]["g5_probe"] if mode == "registered" else cfg["seeds"]["g5_probe_test"])


_RECORDED: list[tuple[int, str]] = []


def seeded_generator(seed: int, purpose: str, allowed: frozenset[int] | set[int]) -> torch.Generator:
    """The only way a generator is made. ``allowed`` is the listed set of the running mode (``partq_seeds(...).values()``, ``partt_listed_seeds(...)`` or the test range). A seed outside it is refused; seed and
    purpose are recorded (``recorded_seeds``)."""
    if seed not in allowed:
        raise SeedRefused(f"seed {seed} ({purpose}) is not listed for this mode")
    _RECORDED.append((seed, purpose))
    g = torch.Generator()
    g.manual_seed(seed)
    return g


def recorded_seeds() -> list[tuple[int, str]]:
    return list(_RECORDED)


def test_range(cfg: Mapping[str, Any]) -> frozenset[int]:
    return frozenset(range(int(cfg["seeds"]["test_low"]), int(cfg["seeds"]["test_high"]) + 1))


# --- records ---------------------------------------------------------------------------------------------------------------------------------
def utc_stamp(now: datetime | None = None) -> str:
    return (now or datetime.now(UTC)).strftime("%Y%m%dT%H%M%S%fZ")


def envelope(kind: str, part: str) -> dict[str, Any]:
    if kind not in RECORD_KINDS:
        raise ValueError(f"unknown record kind {kind!r}")
    if part not in PARTS:
        raise ValueError(f"unknown part {part!r}")
    return {"kind": kind, "schema": SCHEMA, "study": STUDY, "part": part, "oracle_line": ORACLE_LINE}


def check_envelope(record: Mapping[str, Any], kind: str | None = None) -> None:
    if record.get("study") != STUDY or record.get("schema") != SCHEMA or record.get("kind") not in RECORD_KINDS or record.get("part") not in PARTS:
        raise ValueError("P10IS2 record needs study, schema, part and a registered kind")
    if record.get("oracle_line") != ORACLE_LINE:
        raise ValueError("a P10IS2 record carries the fixed oracle-assisted line (section 5.4)")
    if kind is not None and record.get("kind") != kind:
        raise ValueError(f"expected a {kind!r} record, got {record.get('kind')!r}")


def jsonable(v: Any) -> Any:
    """Plain JSON values: NaN and infinities become None (``write_json`` refuses them), tuples lists."""
    if isinstance(v, float):
        return v if math.isfinite(v) else None
    if isinstance(v, Mapping):
        return {str(k): jsonable(x) for k, x in v.items()}
    if isinstance(v, list | tuple | set | frozenset):
        return [jsonable(x) for x in (sorted(v) if isinstance(v, set | frozenset) else v)]
    return v


def write_record(path: Path, record: Mapping[str, Any], *, overwrite: bool = False) -> None:
    check_envelope(record)
    if path.exists() and not overwrite:
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, jsonable(dict(record)))


def read_record(path: Path, kind: str | None = None) -> dict[str, Any]:
    rec = read_json(path)
    if not isinstance(rec, dict):
        raise ValueError(f"not a P10IS2 record: {path}")
    check_envelope(rec, kind)
    return rec


def require_oracle_line(text: str) -> str:
    """Section 5.4 and ruling L8: analysis output without the fixed line is refused."""
    if ORACLE_LINE not in text:
        raise ValueError("refused: output without the fixed oracle-assisted line (section 5.4)")
    return text


def under_line(*lines: str) -> str:
    """The fixed line directly above the given lines."""
    return "\n".join([ORACLE_LINE, *lines])


# --- git and run directory -------------------------------------------------------------------------------------------------------------------
def git(repo: Path, *argv: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", "-C", str(repo), *argv], capture_output=True, check=False)  # noqa: S603, S607


def records_dir(run_dir: Path) -> Path:
    """Where a run's registry, per-item records, side and combined records, analysis and report go: the run directory itself in a registered run, its ``sealed/`` subdirectory in a rehearsal (ADR section 10: the
    rehearsal's scores are sealed and not displayed; its label-worded report is plumbing)."""
    marker = run_dir / "run_mode.json"
    if marker.is_file() and json.loads(marker.read_text()).get("mode") == "rehearsal":
        d = run_dir / "sealed"
        d.mkdir(parents=True, exist_ok=True)
        return d
    return run_dir


CALIBRATION_NAME = "P10IS2-T-calibration"
CALIBRATION_LOG = Path("results/p10is2-partt-calibration/CALIBRATION_LOG.jsonl")


def experiments_dir(repo: Path) -> Path:
    """The experiments directory of the repository this worktree belongs to (the main checkout's, where Part Q's run directories are), derived from git, never typed."""
    common = git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout.decode().strip()
    return Path(common).parent / "experiments"


def calibration_dir(repo: Path) -> Path:
    """Ruling 21: the ONE calibration directory (no free path on the real path)."""
    return experiments_dir(repo) / CALIBRATION_NAME


def require_ignored_run_dir(repo: Path, run_dir: Path) -> None:
    """Ruling L11: a registered stage refuses to start in a directory git would track (the first record would dirty the tree and every later worker would refuse)."""
    try:
        rel = run_dir.resolve().relative_to(repo.resolve())
    except ValueError:
        return  # outside the repository: cannot dirty it
    if git(repo, "check-ignore", "-q", str(rel) + "/x").returncode != 0:
        raise StageRefused(f"refused: the run directory {run_dir} is inside the repository and is not git-ignored")


def require_ignored_path(repo: Path, path: Path) -> None:
    """A file this study writes inside the repository (the ledger) must be git-ignored."""
    try:
        rel = path.resolve().relative_to(repo.resolve())
    except ValueError:
        return
    if git(repo, "check-ignore", "-q", str(rel)).returncode != 0:
        raise StageRefused(f"refused: {path} is inside the repository and is not git-ignored: writing it would dirty the tree")


# --- charged time (ruling L2) ----------------------------------------------------------------------------------------------------------------
class LedgerRefused(RuntimeError):
    """A stage cannot start: the total cap is spent."""


class Ledger:
    """Charged time of one part: the SUM over worker processes of each process's wall time, every attempt (rehearsals and paused attempts included), appended to one JSON file (section 10 item 3, ruling L2).
    One entry per worker process; a stage run by two workers charges both."""

    def __init__(self, path: Path, part: str, total_seconds: float) -> None:
        if not math.isfinite(total_seconds) or total_seconds <= 0:
            raise ValueError("the cap must be a positive number of seconds")
        self.path, self.part, self.total_seconds = path, part, float(total_seconds)

    def entries(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        data = read_json(self.path)
        if not isinstance(data, dict) or data.get("study") != STUDY or data.get("kind") != "ledger" or data.get("part") != self.part:
            raise ValueError(f"not a P10IS2 Part {self.part} ledger: {self.path}")
        return list(data["entries"])

    def charged(self, stage: str | None = None) -> float:
        return float(sum(float(e["seconds"]) for e in self.entries() if stage is None or e["stage"] == stage))

    def remaining(self) -> float:
        return max(0.0, self.total_seconds - self.charged())

    def require_room(self, stage: str, stage_cap_seconds: float) -> None:
        if not math.isfinite(stage_cap_seconds) or stage_cap_seconds <= 0:
            raise LedgerRefused(f"stage {stage}: the stage cap must be a positive number")
        if self.remaining() <= 0:
            raise LedgerRefused(f"stage {stage}: the total cap of {self.total_seconds:.0f} s is spent; the stage is PAUSED and the extension is the lead's (section 9)")

    def charge_process(self, stage: str, run: str, worker: str, seconds: float) -> None:
        """One worker process's wall time (ruling L2)."""
        entries = self.entries()
        entries.append({"stage": stage, "run": run, "worker": worker, "seconds": max(0.0, float(seconds)), "utc": datetime.now(UTC).isoformat()})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        write_json(self.path, {"study": STUDY, "kind": "ledger", "schema": SCHEMA, "part": self.part, "total_seconds": self.total_seconds, "entries": entries})


def stage_cap_seconds(projected_seconds: float) -> float:
    """Section 10 item 3: each registered stage's cap is 2 x its projected time."""
    if not math.isfinite(projected_seconds) or projected_seconds < 0:
        raise ValueError("the projected time must be finite and not negative")
    return 2.0 * projected_seconds


def total_cap_seconds(charged_before_freeze: float, projected_seconds_by_stage: Mapping[str, float]) -> float:
    """Section 10 item 3: the part's total cap is the part's charge before its freeze + 2 x the projected time of ALL its registered stages (the pre-freeze charge counted once, in the total)."""
    if charged_before_freeze < 0:
        raise ValueError("the charge is not negative")
    return float(charged_before_freeze) + 2.0 * float(sum(projected_seconds_by_stage.values()))
