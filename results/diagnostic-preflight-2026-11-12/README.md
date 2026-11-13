# Frozen-memory diagnostic preflight

ADR-0006 is a post-screen exploratory diagnostic; it cannot reverse ADR-0005's failed gate. Root inspected the new isolated orchestration and independently ran locked-extra-pilot Ruff, mypy (19 files), and all 67 tests, successfully. Exact command outputs are attached. Sol implemented; no original numerical source, weights or data were edited. Astra review NOT PERFORMED.

The command is `uv run --locked --extra pilot python -m arborlm.diagnose_memory --suite experiments/P1-20261113T023302942989Z-acbad32bf88f40b3b60e1993e042d5d8 --output-root experiments`.

It is deliberately tied to the retained original local checkpoint artifacts and their recorded identities. A separately reproduced pilot would require its own diagnostic registration/parent identities; published hashes alone do not include binary weights or the corpus. No real diagnostic evaluation was run at this preflight checkpoint.
