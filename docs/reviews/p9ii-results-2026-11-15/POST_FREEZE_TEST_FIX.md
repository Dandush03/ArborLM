# A pre-freeze test that the freeze itself broke — found and fixed 2026-11-15 (UTC)

- **What failed.** `tests/test_p9ii_prefreeze.py::test_generate_script_and_freeze_readme` asserted that `studies/p9ii/freeze/plan.json` and `stage_caps.json` do not exist. That was true when the test was written and audited. The freeze commit `d2746d3` added both files, as the freeze procedure requires, so the assertion has failed on every commit since. The lead did not re-run the full suite after the freeze commit; the P10-S1 implementer (Sonnet 5.5) found it.
- **Effect on the registered run: none.** Tests are not part of the code identity of the run (the source digest covers `studies/p9ii/*.py` and its imports), no study file changed, and the Opus results audit verified the identity of the code that ran against the freeze commit.
- **Fix.** The assertion now accepts the two states the procedure allows: neither file present (before the freeze) or both present (after). One file alone still fails. No other line changed.
- **Lesson recorded.** The full suite is run after a freeze commit, not only before it.
- Astra review: NOT_PERFORMED.
