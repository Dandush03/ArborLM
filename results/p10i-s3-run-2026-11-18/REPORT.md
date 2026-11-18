# P10-I-S3 report (ADR-0026)

Mode: registered. Measured values below are measured; none is a success claim. `Astra review: NOT_PERFORMED`.

## Registered labels (the registered label of a line is its FRESH regime label)

- Line 1, DEPENDENCE: **DEPENDENT**
- Line 2, COMPETITIVENESS[TREE]: **INCONCLUSIVE (MEMORY RATE AT EDGE)**
- Line 2, COMPETITIVENESS[FLAT] (a separate sub-label, never merged): **MEMORY AHEAD**
- Registered positive: line 1 True, line 2 False

## Labels that qualify for ADR-0027 Route A (section 12)

- A1 (dependence, FRESH, M-TREE): label qualifies True; qualifies after the open-choice-13 ruling False
- A2 (competitiveness[TREE], FRESH): label qualifies False; qualifies after the ruling False
- D-ADAPT's registered FRESH convergence tag counts as NOT CONVERGED: True

## Regime labels (printed beside the registered label; never the line's label, never positive)

### FRESH

- line 1: DEPENDENT (M-TREE NOT CONVERGED) [RATE-AT-EDGE] (COLLAPSED cells: 0)
- line 2 [TREE]: INCONCLUSIVE (MEMORY RATE AT EDGE) (MEMORY STILL IMPROVING)
- line 2 [FLAT]: MEMORY AHEAD (DENSE STILL IMPROVING)
- D-ADAPT: NOT CONVERGED (delta +0.017225)
- M-FLAT: NOT CONVERGED (delta +0.020784)
- M-TREE: NOT CONVERGED (delta +0.018103)
- D1: mean +0.128665, cells 27, parents 9, ok True
- D2: mean +0.278791, cells 27, parents 9, ok True
- D3: mean +0.132863, cells 27, parents 9, ok True

### REP-U

- line 1: NOT EVALUABLE (COLLAPSED cells: 0)
- line 2 [TREE]: NOT EVALUABLE
- D-ADAPT: NOT CONVERGED (delta +0.010735)
- M-TREE: NOT CONVERGED (delta +0.002349)

Repeated-data regime: at 16,384 updates this is 64 passes over 131,072 target bytes with a 198k-parameter addition and no weight decay; the endpoint largely measures how each arm behaves once it can fit its training set, and a competitiveness label here can come from the dense adapter overfitting faster.
- INTEGRITY problems of M-TREE: ['M-TREE|REP-U|c21|u512|r0.03: joint permutation outside 1e-06']

### REP

- line 1: NOT EVALUABLE (COLLAPSED cells: 0)
- line 2 [TREE]: NOT EVALUABLE
- line 2 [FLAT]: NOT COMPETITIVE
- D-ADAPT: NOT CONVERGED (delta +0.009879)
- M-FLAT: CONVERGED (delta -0.001465)
- M-TREE: CONVERGED (delta +0.000266)

Repeated-data regime: at 16,384 updates this is 64 passes over 131,072 target bytes with a 198k-parameter addition and no weight decay; the endpoint largely measures how each arm behaves once it can fit its training set, and a competitiveness label here can come from the dense adapter overfitting faster.
- INTEGRITY problems of M-TREE: ['M-TREE|REP|c12|u16384|r0.01: joint permutation outside 1e-06']

## Routing and duration (descriptive; not a third outcome line)

### FRESH
- 16384 updates: G_train TREE BEHIND; G_read WITHIN RESOLUTION; G_train at the primary rates +0.013470; G_prior mean +0.021127 (no label)
- 2048 updates: G_train TREE BEHIND; G_read WITHIN RESOLUTION; G_train at the primary rates +0.007365; G_prior mean +0.011525 (no label)
- 512 updates: G_train WITHIN RESOLUTION; G_read WITHIN RESOLUTION; G_train at the primary rates +0.002383; G_prior mean +0.002529 (no label)
- 8192 updates: G_train TREE BEHIND; G_read WITHIN RESOLUTION; G_train at the primary rates +0.010788; G_prior mean +0.018322 (no label)
- G_train trend: GAP CHANGES WITH DURATION; delta G mean +0.008589, positive 26, negative 1
- G_read trend: NO CHANGE AT THIS RESOLUTION; delta G mean -0.001024, positive 5, negative 22

### REP
- 16384 updates: G_train TREE AHEAD; G_read RESTRICTION HELPS; G_train at the primary rates -0.006328; G_prior mean +0.032097 (no label)
- 2048 updates: G_train TREE BEHIND; G_read WITHIN RESOLUTION; G_train at the primary rates -0.025717; G_prior mean +0.011164 (no label)
- 512 updates: G_train WITHIN RESOLUTION; G_read WITHIN RESOLUTION; G_train at the primary rates -0.013225; G_prior mean +0.002698 (no label)
- 8192 updates: G_train WITHIN RESOLUTION; G_read WITHIN RESOLUTION; G_train at the primary rates -0.004596; G_prior mean +0.025745 (no label)
- G_train trend: GAP CHANGES WITH DURATION; delta G mean -0.011225, positive 0, negative 27
- G_read trend: GAP CHANGES WITH DURATION; delta G mean -0.007697, positive 0, negative 27

## Six-parent readout (the parents not used in calibration; plain figures, no label)

- FRESH: 18 cells, 6 parents; mean C +0.135442, mean C_dense +0.135098, mean Q +0.000344; C>0 in 18/18; P_used >= half C in 18; X_mean >= half C in 18; Q within tolerance in 15; Q ahead in 9
- REP: 18 cells, 6 parents; mean C +0.094948, mean C_dense +0.107858, mean Q -0.012910; C>0 in 18/18; P_used >= half C in 18; X_mean >= half C in 18; Q within tolerance in 0; Q ahead in 0
- REP-U: 18 cells, 6 parents; mean C +0.096427, mean C_dense +0.112310, mean Q -0.015883; C>0 in 18/18; P_used >= half C in 18; X_mean >= half C in 18; Q within tolerance in 0; Q ahead in 0

## Contrasts of section 3.3 (descriptive)

- FRESH at 16384: C_dense_mean +0.129476, C_mean +0.128665, P_used_mean +0.278791, Q_mean -0.000811, X_mean_mean +0.132863
- FRESH at 512: C_dense_mean +0.043708, C_mean +0.036720, P_used_mean +0.045742, Q_mean -0.006988, X_mean_mean +0.033849
- REP at 16384: C_dense_mean +0.103779, C_mean +0.092210, P_used_mean +0.336349, Q_mean -0.011569, X_mean_mean +0.093801
- REP at 512: C_dense_mean +0.042155, C_mean +0.034470, P_used_mean +0.041836, Q_mean -0.007686, X_mean_mean +0.031344
- REP-U at 16384: C_dense_mean +0.107849, C_mean +0.093867, P_used_mean +0.347723, Q_mean -0.013982, X_mean_mean +0.096053
- REP-U at 512: C_dense_mean +0.044280, C_mean +0.036042, P_used_mean +0.044464, Q_mean -0.008238, X_mean_mean +0.033236

## P4-rate anchor (descriptive)

- M-TREE: rate for U* 0.01, mean C at 0.003 +0.091213, at the frozen rate +0.092210

## Limits

- REP and REP-U endpoints largely measure how each arm behaves once it can fit its training set (64 passes over 131,072 target bytes); a competitiveness label on repeated data can come from the dense adapter overfitting faster.
- Nine correlated parents, one corpus, byte-level text, one addition size. No p-value is computed. Seconds per update are descriptive records of this implementation and not an efficiency result.
