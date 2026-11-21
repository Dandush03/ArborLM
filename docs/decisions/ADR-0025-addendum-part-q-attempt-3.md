# ADR-0025 addendum — Part Q after the stop of registered attempt 2: the human lead's decision and the amendment (2026-11-19)

ADR-0025 itself is not edited. This addendum records a decision of the human lead and the one amendment it carries. `Astra review: NOT_PERFORMED`. Claude review is not Astra review.

## 1. What it follows

Registered attempt 2 of Part Q (freeze `55017df4616a81795918e21e0792fa742f77bdc4`) stopped at the `outputs` stage on a registered test: tokenization test (a) on the R-gloss-icl prompts found one mismatch where zero are required (`results/p10is2-partq-run-20261119/OUTCOME.md` and the independent reading in its `audit/STOP_P10IS2_PARTQ_ATTEMPT2.md`). The cause is the template's segment rule (section 5.2: "The prompt is a concatenation of stored segments only: the source word's segment from the bank, the separator segment, the gloss word's segment … and the newline segment"): when a source word that begins with a digit is on a line other than the first, the student's tokenizer fuses the preceding newline with the word's leading space into one token, which separately stored segments cannot reproduce. One prompt of the study is affected. No qualification value of attempt 2 has been read by the lead or the auditor.

## 2. The human lead's decision (2026-11-19, Panama time)

The lead presented the auditor's reading and three recommendations — (1) record the attempt as QUALIFICATION-ENGINEERING-FAILURE, the strict reading; (2) a third attempt with a narrow amendment of the segment rule, the registered test unchanged; (3) reuse of the six completed stages of attempt 2 under a new freeze, verified by checksum with the regeneration check repeated, in place of redoing them with the same seeds — and asked: "Do you approve a third S2 attempt with the template fix, reusing the six completed stages, or not now?" The human lead answered: **"yes I do"**.

Recorded accordingly:

- **A third registered attempt of Part Q is approved**, with the amendment of section 3 and the reuse of section 4. It needs a new freeze and a new Decision 2 after the changes are implemented and independently audited and a counting rehearsal has passed. The human lead did not say who takes that Decision 2; under the delegation of 2026-11-18 (sections 1 and 7) the lead takes it and reports it, unless he says otherwise.
- **Attempt 2 is recorded as QUALIFICATION-ENGINEERING-FAILURE**, as ADR-0025 reads strictly (sections 4.4 row 1 and 15). The human lead's answer was to the question about the third attempt; he was shown this classification as the lead's first recommendation in the same message and did not rule otherwise. If he later rules it a stop on a specification defect with no outcome registered, that ruling replaces this line. In either reading it is not a result about the teachers.

## 3. The amendment (section 5.2, the R-gloss-icl template; nothing else)

The prompt TEXT is unchanged: one line per in-vocabulary source word that has an entry, in source order, repeated words included — the source word, the separator ` =`, the top gloss word, a newline — before the task prompt, exactly as ADR-0025 gives it. What changes is how the stored segments are cut:

> The token ids of an R-gloss-icl prompt are the concatenation of stored segments, one group per gloss line. For the FIRST gloss line the group is as before: the source word's segment, the separator segment, the gloss word's segment. For every LATER gloss line, the newline that ends the previous line is stored together with that line's source word: the segment is the tokenization of the string made of the newline followed by the source word exactly as it appears in the prompt text (with whatever precedes the word on its line in that text), tokenized in one call; then the separator segment and the gloss word's segment as before. The newline that ends the last gloss line is stored together with the first piece of the task prompt in the same way, or, if the task prompt's stored segment already begins after that newline without fusing with it for every item, as its own segment; which of the two holds is decided by code from the tokenizer alone, for all items, before any teacher output is read, and is recorded.

The rule's purpose, which is also its test: **for every prompt the study builds, the concatenation of the stored segments equals the tokenization of the whole prompt string.** Tokenization test (a) of ADR-0022 section 14.2 is unchanged, is still run on the R-gloss-icl prompts of every E_A, E_B and D_cal item, and still requires zero mismatches. No source word, item or prompt is dropped or altered. The baseline's content (what the student is shown) is identical to what ADR-0025 registered; only the bookkeeping of token boundaries differs.

Disclosed: this amendment is made knowing that attempt 2 failed test (a) on one prompt, and knowing nothing else of attempt 2's values. It cannot move a qualification count: Part Q's qualification quantities are computed in stages that completed before the template is used, and the R-gloss-icl prompts are stored material for Part T.

Added by the same decision, as engineering requirements of any further attempt: a unit test of the segment rule on line boundaries followed by a digit, a letter, punctuation and a repeated word, needing no data; test (a) run over the registered PROMPT TEXTS (public inputs) before the freeze, with no teacher output read; the analysis stage derives the row-1 label after a recorded engineering failure instead of refusing; the registered cap check counts the charge before the freeze.

## 4. Reuse of attempt 2's completed stages (a ruling ADR-0025 does not contain)

The six stages of attempt 2 that completed in registered mode within their caps (inputs, partition, qfit, qcheck, generation, regeneration) are carried into attempt 3 without being recomputed, on these conditions, each checked by code at the new freeze and again at the start of every stage of attempt 3:

1. Every file those stages wrote is listed with its SHA-256 in the new plan as a frozen input, from attempt 2's run directory as it stands; a difference is PAUSED — IDENTITY. No sealed value is opened to do this: files are hashed as bytes.
2. The code and configuration that produced them are those of freeze `55017df`; the new freeze records, file by file, what differs between `55017df` and itself, and refuses unless every difference is confined to the template's segment rule, the outputs and analysis stages, the cap check, tests and documentation. Any change to code that the six stages executed voids the reuse and the stages are redone with the same registered seeds.
3. The regeneration identity check (section 4.3, rule 9) is run again in attempt 3 before `outputs`, on the platform of record, and must pass with zero differing token sequences.
4. Registered seeds are the same (250901–250914 and any others attempt 2 consumed); no seed is replaced. A re-draw after an observed stop is not permitted.
5. The charge of attempts 1 and 2 and of every rehearsal stays charged; the caps of attempt 3 are set by the rule from the charge so far and the projection of the remaining stages only.
6. The outcome record of attempt 3 states that stages 1 to 6 were computed under freeze `55017df` and reused.

If any condition cannot be met, attempt 3 redoes the stages concerned (about 7.4 charged hours for all six) with the same seeds, and says so.
