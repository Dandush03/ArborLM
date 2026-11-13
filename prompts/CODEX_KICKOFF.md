# Codex kickoff task: initialize ArborLM correctly

Use the repository `https://github.com/Dandush03/ArborLM`.

Read `AGENTS.md`, `docs/RESEARCH_HANDOFF.md` and `docs/EXPERIMENT_PROTOCOL.md` **in full** before code changes. The research handoff is the canonical context from the originating discussions; do not reduce ArborLM to a vector DB + existing model, or claim unproven performance.

**Agent policy:** Astra handles scientific reasoning, specifications, orchestration, interpretation and validation. A lower-tier Codex coding model implements approved tasks and tests. `AGENTS.md` cannot automatically switch models. Mark pending Astra validation when it was not actually performed.

First task only:

1. Summarize the scientific objective, unproven assumptions and initial experimental controls; create an ADR-0002 phase-0 implementation specification marked `PENDING ASTRA REVIEW`.
2. Establish minimal Python/PyTorch source and test structure with exact pinned/declarative dependencies, lint/typecheck and CPU smoke-test commands.
3. After approval of ADR-0002, implement the smallest causal-transformer baseline and reproducible synthetic dataset. Do **not** begin the novel model layer or expensive training until scientific spec approval.
4. Log seeds, git SHA, environment, data checksums, loss metrics and checkpoint hash in a simple per-run manifest.
5. Add CI for unit tests and a tiny CPU training/resume/evaluation smoke test.
6. Keep all result claims honest and label unfinished work explicitly. Never make up benchmarks.
7. Open a PR containing the initial scaffold, exact test outputs, pending review items, and next tasks.

No cloud spend, production deployment, personal homelab dependence, huge model downloads or silent research-methodology changes.
