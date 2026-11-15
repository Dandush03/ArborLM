# Follow-up: the tolerant assertion flaked on a second Linux runner (2026-11-15 UTC)

- CI run 43681558281 on the P9-II draft pull request (a documentation-only commit on top of `main`) failed with 1 failed, 1,736 passed, 12 skipped: `tests/test_p9_model.py::test_chunked_equals_unchunked[flat]` at the non-macOS branch added in `4b932b2`. The same code passed on `main` (run 43680155917) and on PR #6 (run 43678731935). The independent diff reviewer had warned that an absolute tolerance of 1e-6 is only 2–4 units in the last place at the top of the score range and could flake on another BLAS or CPU.
- Fix (test only, non-macOS branch only): scores and candidate scores within rtol 1e-5 and atol 1e-5; logits and loss within rtol 1e-4 and atol 1e-4. Selected slots and candidate ids are still compared exactly on every platform, and macOS keeps bit-for-bit equality. No study code, record or frozen identity changes.
- Until this reaches `main`, CI on `main` can fail intermittently on this one test on Linux runners.
- Astra review: NOT_PERFORMED.
