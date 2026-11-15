# Addendum to the attempt-1 record (2026-11-15 UTC), after the auditor's check

`docs/reviews/p9i-prefreeze-audit-2026-11-14/GATE_FIX_AUDIT.md` (Opus 5.5) confirmed the diagnosis and added two things the README did not say:

- **More was run on registered seeds than the README lists.** The gates stage's checkpoint-restoration check trained arms N and BB for 32 updates each on registered data (4,096 slots). Their per-update loss logs are in the kept run directory. Neither the lead nor the auditor has read them, and they are not read before the run is complete. No accuracy was computed and no snapshot was evaluated.
- **A second cause.** At the frozen code the gates stage could not run on rehearsal seeds at all (its restoration job was forced into calibration mode, which refuses them), so the registered attempt was that stage's first execution at real size.
- At real proportions only 256 of 4,352 Panel A rows hold facts of the 4,096-slot cell; the auditor puts the chance that the first 8 rows miss them all at about 0.61. The failure was likely on any real-size data.
- The fact ids 2,482–29,279 quoted in the README come from the lead's diagnostic on the registered Panel A; the auditor did not regenerate registered data and so did not check them. It reproduced the mechanism on rehearsal draws 0 and 2.

Astra review: NOT_PERFORMED.
