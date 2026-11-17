r1_cap_rule.attempt1.*: my own imperfection, not a code defect. The boundary probes used scale 1.0, where R1 is about 35 h, so the P that puts P + 2R1 on 36/40 h is negative (unphysical).
The rule arithmetic is the same for any P, so the result (impl gives rung 2 at a cap equal to a whole hour when P + 2R1 exceeds it by < 1e-12 h) stands, but attempt 2 uses scale 0.25 so that P is positive.
The grid and random comparisons (0 mismatches) are unchanged between attempts.
pytest_pinned.attempt1_wrong_arborlm.txt: my own setup error. The interpreter's virtual environment has `arborlm` installed from another worktree (agent-a91c79a181109bb9c/src),
so `check_code_location` correctly refused (arborlm not under the checked tree) and `-x` stopped the run there. Attempt 2 sets PYTHONPATH=<pinned>/src (as the e2e exercise does) and runs without -x.
r5_frozen_clone.attempt1.*: my own error. The source-only clone copied docs/decisions/ADR-0022* only; tests/test_p10s2_fixA_fetch.py reads docs/reviews/p10-design-2026-11-15/DOWNLOAD_LEDGER.md at import,
so collection stopped. Attempt 2 copies the whole of docs/ (tracked files).
r7_freeze_inputs.attempt1.py: my own error. It built the second stand-in bundle with the clone's code, whose exercise configuration moves test_low to 229900, so the stand-in generator
(test_low + 500 + offset = 230401) was refused by the seed function (correct behaviour). The exercise itself builds its bundle in the parent process with the pinned configuration;
attempt 2 does the same (the pinned tree's code, test seeds 229501+).
r10_freeze_commit_identity.attempt1.txt: my own error: inline zsh does not word-split $G, so no git command ran; no repository was made. Attempt 2 is a sh script (scripts/r10_freeze_commit_identity.sh).
r10 attempt 2 (first sh version) stopped: git rm removed the empty folder before the re-add; attempt 3 adds mkdir -p (my error).
