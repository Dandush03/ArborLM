# M0: the human lead's decision on the lineage question (2026-11-25)

Recorded by the M0 implementer (Claude Sonnet 5.5) from the coordinator's message. The question and the answer are quoted; everything outside quotation marks is the implementer's reading and is marked as such. This record approves nothing beyond what ADR-0033 Decision 1 already allows (locked-environment work, no model, no download). Astra review: NOT_PERFORMED.

## The question, verbatim (put to the human lead by the coordinator)

"Which do you want for M0? 1. Treat lineages as fixed strata (ADR-0033 choice 19). M0 can proceed with the items it has... conclusions hold for those lineages only... 2. Keep lineages as clusters and repair M0 to hundreds of lineages, as its design requires. The stronger claim survives, but it means generating new items first, and I have no measured figure for how long that takes."

(The ellipses are in the coordinator's message as received; the full text of option 1 was not passed to the implementer.)

## The answer, verbatim

"2"

## Reading (the implementer's, not the human lead's)

- Lineages stay the clusters of ADR-0033 section 6.2 ("The cluster, for G and for every bootstrap, is the lineage"), so the cluster-based power rule of section 9.4 stands and B2 of the I0-a audit is settled on that basis (clusters), not on strata.
- M0's private evaluations are to be repaired to hundreds of hand-written lineages per part, as the design requires (proposed minimum 300 per private part).
- No threshold is changed by this answer. R2 (the known-truth gate's operating point) and R6 (second solvers by a separate context) remain open and are not decided here.
- The answer approves no execution beyond locked-environment work.
