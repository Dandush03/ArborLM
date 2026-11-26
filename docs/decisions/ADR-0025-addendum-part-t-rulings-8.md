# ADR-0025 addendum: Part T ruling 38 (eighth addendum)

Status: ruling of the lead coordinator after the seventh check (READY at 0c8f696; two advisories adopted). It binds like the ADR and the earlier addenda (none is edited). Recorded by the implementer from the coordinator's message. `Astra review: NOT_PERFORMED`.

38. (a) A `calibrate` resume (any session after the first) requires the log commit at HEAD to be in `@{u}` (the same "head" check the plan uses) before any unit trains, so that the lead's push after each session stop is enforced and the stated residual (ruling 36) is bounded to one session by the code. (b) `[calibration_log].remote_branch` must be non-empty and `@{u}` must be exactly that branch of the recorded remote; an empty branch or another branch of the same remote is refused.
