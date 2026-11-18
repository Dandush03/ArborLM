# ruff: noqa: E501
"""P10IR plan, freeze identity and registered preconditions (ADR-0029 section 13).

``freeze/plan.json`` is the one source of every stage's items: the list of cells, checkpoints and reads (each read with its status RUN or NOT APPLICABLE and the reason), the checkpoint digests, the
stage caps, the hashes of P10-S1's data manifests and (for A2) of the bridge draws' manifests. Every stage derives its items from the plan file only; ``Plan.items`` never looks at the config.

The frozen-input set is exactly section 13's: ``studies/p10ir/**`` (code, launch scripts, freeze files other than the plan itself), the config (which holds every threshold), ``freeze/plan.json``, the stage
caps, the checkpoint digests, P10-S1's data manifests and the bridge manifests. Identity is by SHA-256 of each listed file. **The ADR text is not in it**: the plan stores the ADR's hash for provenance
only (``adr.sha256``), and no check compares it.

Registered entry points refuse (``check_preconditions``, ``load_plan``, ``verify_plan``, ``require_decision_2``) unless the tree is clean, the freeze commit is an ancestor of HEAD and equal to HEAD on
the frozen files, the plan exists and every identity in it holds, and a committed Decision 2 for the stage's group names the freeze commit.
"""

import fnmatch
import subprocess
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from arborlm.io import canonical_json, file_sha256, read_json, sha256

from . import core, gates

REGISTERED, REHEARSAL, TEST = "registered", "rehearsal", "test"
MODES = (REGISTERED, REHEARSAL, TEST)
REGISTERED_STAGES = ("gates-a1", "a1", "gates-a2", "a2-train", "a2", "analysis", "report")
STAGE_GROUP = {"gates-a1": "A1", "a1": "A1", "gates-a2": "A2", "a2-train": "A2", "a2": "A2", "analysis": "A1", "report": "A1"}
STAGE_CAP_KEY = {"gates-a1": "a1", "a1": "a1", "gates-a2": "a2", "a2-train": "a2", "a2": "a2", "analysis": "a1", "report": "a1"}
DECISION_2_GLOB = "results/p10ir-freeze-*/DECISION_2_{group}.md"
DECISION_RUN_LINE = "DECISION: RUN"
DECISION_NO_RUN_LINE = "DECISION: DO NOT RUN"
FROZEN_ROOTS = ("studies/p10ir",)
SEAL_ACCESSES_DECLARED = [
    "REVIEW_ADR-0024.md: key names of eval.json listed, no value of the two sealed keys displayed",
    "REVIEW2_ADR-0024_ADR-0029.md: key names listed, no value of the two sealed keys displayed",
    "REVIEW3_ADR-0029.md: P_T-OQ_f8192_n4096_d1_i2101/eval/u0008192/eval.json and P_F-OQ_f8192_n4096_d1_i2101/eval/u0016384/eval.json loaded in a script that printed key paths only; no value of the two sealed keys displayed",
]  # fmt: skip


class StageRefused(RuntimeError):
    """A registered entry point refuses to run (no plan, no freeze, no Decision 2, a dirty tree, an identity that differs)."""


# --- git -----------------------------------------------------------------------------------------------------------------------------
def git(repo: Path, *argv: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", "-C", str(repo), *argv], capture_output=True, check=False)  # noqa: S603, S607


# --- frozen-input hashes ---------------------------------------------------------------------------------------------------------------
def frozen_file_hashes(repo: Path) -> dict[str, str]:
    """SHA-256 of every file of ``studies/p10ir/**`` (sources, launch scripts, freeze files other than ``plan.json``) and of the config. ``__pycache__`` is not a source. The ADR is not here."""
    out: dict[str, str] = {}
    for root in FROZEN_ROOTS:
        for p in sorted((repo / root).rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc" and p != repo / core.PLAN:
                out[str(p.relative_to(repo))] = file_sha256(p)
    out[str(core.CONFIG)] = file_sha256(repo / core.CONFIG)
    return out


def adr_provenance(repo: Path) -> dict[str, str]:
    return {"path": core.SPEC, "sha256": file_sha256(repo / core.SPEC), "note": "provenance only: the ADR text is not a frozen input and no check compares this hash"}


# --- items ---------------------------------------------------------------------------------------------------------------------------
LabelOf = Callable[[str, core.CellSpec, int], str]


def read_entries(arm: str, spec: core.CellSpec, cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Every read of one checkpoint of ``arm`` at ``spec``, each RUN or NOT APPLICABLE with the reason (feasibility is a plan item, never silently skipped, section 6)."""
    out: list[dict[str, Any]] = []
    if arm == "T-OQ":
        from .reads import tree_read_specs

        for r in tree_read_specs(spec.slots, cfg):
            out.append({"name": r.name, "status": "RUN"})
        feasible = set(core.feasible_visits(spec.slots, cfg))
        for v in cfg["reads"]["visit_sweep"]:
            if int(v) not in feasible:
                for pr in core.PRIOR_STATES:
                    out.append({"name": core.tv_name(int(v), pr), "status": "NOT APPLICABLE", "reason": f"v = {v} exceeds N/256 = {spec.slots // 256} at {spec.slots} slots"})
        return out
    out += [{"name": "F0", "status": "RUN"}, {"name": "I256@512", "status": "RUN"}]
    feasible_b = set(core.feasible_budgets(spec.slots, cfg))
    for c in cfg["reads"]["index_budgets"]:
        for s in core.i64_seeds(cfg):
            if int(c) in feasible_b:
                out.append({"name": core.i64_name(int(c), s), "status": "RUN"})
            else:
                out.append({"name": core.i64_name(int(c), s), "status": "NOT APPLICABLE", "reason": f"c = {c} is not below N = {spec.slots}"})
    return out


def build_items(
    stage: str,
    specs: Sequence[core.CellSpec],
    draws: Sequence[int],
    label_of: LabelOf,
    seed_of: Callable[[int], dict[str, Any]],
    cfg: Mapping[str, Any],
    *,
    checkpoint_root: str,
    checkpoints_of: Callable[[core.CellSpec], Sequence[tuple[str, int]]],
    table_facts: int,
    unseen: int,
    synthetic: bool = False,
    facts_of: Callable[[core.CellSpec], int] | None = None,
) -> list[dict[str, Any]]:
    """One item per checkpoint of every cell of both arms and every draw: A1 70 cells x 4 checkpoints = 280 items, A2 20 cells x 2 = 40 (registered)."""
    items: list[dict[str, Any]] = []
    for spec in specs:
        for d in draws:
            seed = seed_of(d)
            for arm in ("T-OQ", "F-OQ"):
                label = label_of(arm, spec, d)
                for cp, update in checkpoints_of(spec):
                    items.append({
                        "id": core.item_id(stage, label, update), "stage": stage, "arm": arm, "cell": label, "cell_name": spec.name, "role": spec.role, "facts": facts_of(spec) if facts_of else spec.facts, "slots": spec.slots,
                        "draw": d, "update": update, "checkpoint": cp, "u_p": spec.u_p, "run": spec.run, "init_seed": seed["init_seed"], "seed_name": seed["name"], "seed_base": seed["base"], "checkpoint_root": checkpoint_root,
                        "table_facts": table_facts, "unseen": unseen, "synthetic": synthetic, "reads": read_entries(arm, spec, cfg),
                    })  # fmt: skip
    ids = [i["id"] for i in items]
    if len(set(ids)) != len(ids):
        raise ValueError("a plan names an item twice")
    return items


def a1_checkpoints(spec: core.CellSpec) -> list[tuple[str, int]]:
    from .analysis import checkpoint_names

    return list(checkpoint_names(spec).items())


def a2_checkpoints(spec: core.CellSpec) -> list[tuple[str, int]]:
    return [("U_P", spec.u_p), ("RUN", spec.run)]


def a1_seed_of(d: int) -> dict[str, Any]:
    s = core.p10s1_draw_seeds(d)
    return {"name": s.name, "base": s.facts, "init_seed": int(core.load_config()["seeds"]["p10s1_init_base"]) + d}


def a2_seed_of(d: int) -> dict[str, Any]:
    s = core.bridge_seeds(d)
    return {"name": s.name, "base": s.facts, "init_seed": core.bridge_init_seed(d)}


def registered_items(cfg: Mapping[str, Any] | None = None) -> dict[str, list[dict[str, Any]]]:
    """The registered items of A1 (7 cells x 5 draws x 2 arms x 4 checkpoints = 280) and A2 (2 cells x 5 x 2 x 2 = 40), from the config's cells and the seeds of section 5."""
    from .analysis import default_label_of

    c = cfg or core.load_config()
    from studies.p10s1 import core as s1

    table, unseen = s1.FACT_TABLE, s1.UNSEEN_FACTS
    a1 = build_items(core.STAGE_A1, core.cell_specs(c), range(1, 6), lambda arm, s, d: default_label_of(core.STAGE_A1, c)(arm, s, d), a1_seed_of, c, checkpoint_root="s1", checkpoints_of=a1_checkpoints, table_facts=table, unseen=unseen)
    prim = core.primary_cells(c)
    a2 = build_items(core.STAGE_A2, prim, range(1, int(c["seeds"]["bridge_draws"]) + 1), lambda arm, s, d: default_label_of(core.STAGE_A2, c)(arm, s, d), a2_seed_of, c, checkpoint_root="a2", checkpoints_of=a2_checkpoints, table_facts=table, unseen=unseen)
    return {core.STAGE_A1: a1, core.STAGE_A2: a2}


# --- the plan ------------------------------------------------------------------------------------------------------------------------
class Plan:
    """The plan file, read only. ``items`` and everything else come from the file."""

    def __init__(self, data: Mapping[str, Any], path: Path | None = None) -> None:
        if data.get("kind") != "freeze_plan" or data.get("study") != core.STUDY or data.get("schema") != core.SCHEMA:
            raise StageRefused("refused: not a P10IR plan")
        self.data, self.path = dict(data), path

    @classmethod
    def load(cls, path: Path) -> "Plan":
        if not path.is_file():
            raise StageRefused(f"refused: no freeze plan at {path}: nothing registered runs before the freeze")
        return cls(read_json(path), path)

    def items(self, stage: str) -> list[dict[str, Any]]:
        if stage not in core.STAGES:
            raise ValueError(f"unknown stage {stage!r}")
        return list(self.data["items"][stage])

    def item(self, item_id: str) -> dict[str, Any]:
        for stage in core.STAGES:
            for it in self.data["items"].get(stage, []):
                if it["id"] == item_id:
                    return dict(it)
        raise StageRefused(f"refused: {item_id} is not an item of the frozen plan")

    @property
    def mode(self) -> str:
        return str(self.data["mode"])

    def cap_seconds(self, stage_name: str) -> float:
        return float(self.data["stage_caps"][f"{stage_name}_hours"]) * 3600.0

    def total_cap_seconds(self) -> float:
        return float(self.data["stage_caps"]["total_hours"]) * 3600.0

    def sha256(self) -> str:
        return sha256(canonical_json(self.data))


def build_plan(
    *,
    mode: str,
    cfg: Mapping[str, Any],
    repo: Path,
    items: Mapping[str, list[dict[str, Any]]],
    run_dir: Path,
    s1_run_dir: Path | None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """The plan record (a pure function of its inputs). Identity of every frozen file, the config, the caps, the items. The checkpoint digests, the manifest hashes, the plateau lists, the D-OQ context and
    the rehearsal record are in ``extra`` (the registered freeze computes them from the run directories; the rehearsal builds its own)."""
    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}")
    rec: dict[str, Any] = {
        **core.envelope("freeze_plan"), "mode": mode, "adr": adr_provenance(repo), "config_sha256": core.config_sha256(repo / core.CONFIG), "frozen_files": frozen_file_hashes(repo),
        "stage_caps": {k: float(v) for k, v in cfg["caps"].items() if k.endswith("_hours")}, "caps_provisional": bool(cfg["caps"]["provisional"]),
        "run_dir": str(run_dir.resolve()), "s1_run_dir": None if s1_run_dir is None else str(s1_run_dir.resolve()), "items": {k: list(v) for k, v in items.items()},
        "platform": gates.platform_record(), "seal": {"accesses_declared": SEAL_ACCESSES_DECLARED, "values_opened": False, "broken": False},
        "frozen_input_set": "studies/p10ir/** (code, launch scripts, freeze files), the config, freeze/plan.json, stage caps, checkpoint digests, P10-S1's data manifests, the bridge draws' manifests; the ADR text is not in it",
    }  # fmt: skip
    rec.update(dict(extra or {}))
    return rec


def verify_plan(plan: Plan, repo: Path, run_dir: Path, *, check_items: bool = True) -> None:
    """Every identity the plan recorded must hold now: the frozen files and the config (SHA-256), the caps (not provisional, equal to the config's), P10-S1's data manifests, the bridge manifests, the
    checkpoint digests' own record, the run directory, and (registered) the items equal to a re-derivation from the config and the seeds."""
    d = plan.data
    now = frozen_file_hashes(repo)
    differ = sorted(k for k in set(now) | set(d["frozen_files"]) if now.get(k) != d["frozen_files"].get(k))
    if differ:
        raise StageRefused("refused: frozen file(s) differ from the freeze (PAUSED — IDENTITY): " + ", ".join(differ[:8]))
    if core.config_sha256(repo / core.CONFIG) != d["config_sha256"]:
        raise StageRefused("refused: the config differs from the freeze (PAUSED — IDENTITY)")
    cfg = core.load_config(repo / core.CONFIG)
    caps = {k: float(v) for k, v in cfg["caps"].items() if k.endswith("_hours")}
    if caps != d["stage_caps"]:
        raise StageRefused("refused: the stage caps in the config differ from the plan's")
    if d["mode"] == REGISTERED and (core.caps_provisional(cfg) or d.get("caps_provisional")):
        raise StageRefused("refused: the caps are provisional: the human lead sets them after the rehearsal (section 12)")
    if Path(d["run_dir"]).resolve() != run_dir.resolve():
        raise StageRefused(f"refused: the freeze names the run directory {d['run_dir']}, not {run_dir}")
    for name, rec in (d.get("manifests") or {}).items():
        p = Path(rec["path"]) if Path(rec["path"]).is_absolute() else repo / rec["path"]
        if not p.is_file() or file_sha256(p) != rec["sha256"]:
            raise StageRefused(f"refused: {p} does not hash to the frozen manifest {name}")
    if d["mode"] == REGISTERED and check_items:
        derived = registered_items(cfg)
        if derived != {k: d["items"][k] for k in core.STAGES}:
            raise StageRefused("refused: the plan's items differ from a re-derivation from the config and the seeds")


# --- registered preconditions ---------------------------------------------------------------------------------------------------------
def check_preconditions(mode: str, repo: Path, freeze_commit: str | None) -> dict[str, str] | None:
    """A registered stage refuses unless the working tree is clean, ``freeze_commit`` is an ancestor of HEAD, ``studies/p10ir`` and the config equal their content at that commit, the machine is the
    platform of record and the frozen sources outside this study (src/arborlm, uv.lock, pyproject.toml, P8 digest) verify. Returns the freeze identity (None for rehearsal and test)."""
    if mode != REGISTERED:
        return None
    dirty = git(repo, "status", "--porcelain", "--untracked-files=all").stdout.decode().strip()
    if dirty:
        raise StageRefused("refused: the working tree is not clean:\n" + "\n".join(dirty.splitlines()[:10]))
    if not freeze_commit:
        raise StageRefused("refused: a registered stage requires --freeze-commit")
    ok = git(repo, "rev-parse", "--verify", "--quiet", f"{freeze_commit}^{{commit}}")
    if ok.returncode != 0:
        raise StageRefused(f"refused: {freeze_commit} is not a commit of this repository")
    full = ok.stdout.decode().strip()
    if git(repo, "merge-base", "--is-ancestor", full, "HEAD").returncode != 0:
        raise StageRefused(f"refused: freeze commit {full} is not an ancestor of HEAD")
    problems = [f"{p} at HEAD differs from the freeze commit" for p in (*FROZEN_ROOTS, str(core.CONFIG)) if git(repo, "rev-parse", f"{full}:{p}").stdout != git(repo, "rev-parse", f"HEAD:{p}").stdout]
    if problems:
        raise StageRefused("refused: " + "; ".join(problems))
    bad = gates.platform_problems()
    if bad:
        raise StageRefused("refused: not the platform of record (section 13): " + "; ".join(bad))
    from studies.p9 import core as p9core

    check = p9core.frozen_input_check(repo, full)
    if not check["ok"]:
        raise StageRefused("refused: frozen inputs do not verify: " + "; ".join(map(str, check["problems"][:5])))
    return {"commit": full, "tree": git(repo, "rev-parse", f"{full}^{{tree}}").stdout.decode().strip()}


def require_decision_2(repo: Path, freeze_commit: str, group: str) -> str:
    """Decision 2 for ``group`` (A1 or A2; A2 has its own) is recorded in a committed file ``results/p10ir-freeze-*/DECISION_2_<group>.md`` that holds the line ``DECISION: RUN`` (and not ``DECISION: DO
    NOT RUN``) and the full freeze commit. Without it no registered stage starts."""
    if group not in core.STAGES:
        raise ValueError(f"unknown group {group!r}")
    pattern = DECISION_2_GLOB.format(group=group)
    full = git(repo, "rev-parse", "--verify", "--quiet", f"{freeze_commit}^{{commit}}").stdout.decode().strip()
    tracked = [p for p in git(repo, "ls-tree", "-r", "--name-only", "HEAD", "--", "results").stdout.decode().split("\n") if fnmatch.fnmatch(p, pattern)]
    for name in tracked:
        text = git(repo, "show", f"HEAD:{name}").stdout.decode("utf-8", "replace")  # the committed content, not the working file
        lines = {line.strip() for line in text.splitlines()}
        if full and full in text and DECISION_RUN_LINE in lines and DECISION_NO_RUN_LINE not in lines:
            return name
    raise StageRefused(f"refused: no committed {pattern} contains the line '{DECISION_RUN_LINE}' (and not '{DECISION_NO_RUN_LINE}') and the full freeze commit {full or freeze_commit}: Decision 2 is recorded there before anything registered runs")


def load_registered_plan(repo: Path) -> Plan:
    plan = Plan.load(repo / core.PLAN)
    if plan.mode != REGISTERED:
        raise StageRefused("refused: the plan in freeze/ is not a registered plan")
    return plan
