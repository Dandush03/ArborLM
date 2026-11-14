# ArborLM — notes for Claude sessions

**`AGENTS.md` is the operating policy. Read it first; this file only adds pointers and does not override it.**

ArborLM is unproven research. Never describe a result as a success unless a validated experiment and a recorded human approval exist.

## Read before doing anything

1. `AGENTS.md`
2. `docs/RESEARCH_HANDOFF.md`, `docs/EXPERIMENT_PROTOCOL.md`, `docs/RESEARCH_LOG.md`
3. `docs/decisions/` — ADR-0010 (P5) and ADR-0011 (P6, human-approved, executed once) are completed studies. ADR-0012 (governance) and ADR-0013 (P7-A proposal) are **not approved** until their approval records are filled in. Check each ADR's status line and approval record; do not rely on this summary.
4. `docs/reviews/` — Claude-workflow reviews of completed studies.

## Standing rules

- P1–P5 are immutable: do not edit existing code under `src/arborlm/`, `configs/`, `tests/`, existing ADRs, `results/` or `experiments/`. New work goes in new files.
- No implementation or execution of a new study before its specification has a recorded human approval. No training, SSD work, downloads, paid services, merges, pushes of weights or publication without explicit human approval.
- Thresholds are fixed before observation. Never relax one, select seeds, or count logical work as measured efficiency.
- `Astra review: NOT_PERFORMED` is historically true. Claude review is not Astra review.
- Record negative and null results and keep failed runs and failed checker attempts.

## Roles (proposed in ADR-0012, pending human approval)

Subagents in `.claude/agents/`: `arbor-lead` (Fable 5.2, science and orchestration), `arbor-auditor` (Opus 5.5, independent verification), `arbor-implementer` (Sonnet 5.5, code/figures/benchmarks), `arbor-clerk` (Haiku 5.5, read-only inventory). Record which model actually ran each delegated task from session metadata; never claim a delegation that did not happen.

## Commands

```sh
uv run --locked ruff check .
uv run --locked mypy src/arborlm
uv run --locked pytest
```

Local binaries live in `experiments/` and the corpus in `data/` (both git-ignored). `uv.lock` and `pyproject.toml` do not change without an approved amendment; use `uv run --locked --with <pkg>==<version>` for analysis-only tools such as plotting.
