# P10-I-S2-D0 run record (ADR-0035)

oracle-assisted (word-level addresses supplied by rule); lexical translation of short closed-vocabulary sentences, two capabilities of one kind; frozen English student; teacher-only training material verified by measured-precision filter; not autonomous learned memory.
POST-HOC EXPLORATORY DIAGNOSTIC OF AN OBSERVED RUN; NOT A REGISTERED LABEL

Astra review: NOT_PERFORMED. Self-check only; not independent review and not human approval. Implemented by `arbor-implementer` (Claude Sonnet 5.5, `claude-sonnet-5-5`).

## What was run

- `studies/p10is2d0` at commit `e74cbf25bac019156be34c0a51a416749a4da16a` (branch `claude/p10-i-s2-d0`), torch 2.8.0, CPU only, 3 worker processes of 6 threads, deterministic algorithms, launch `studies/p10is2d0/launch_d0.sh`.
- Specification: ADR-0035 draft 3 (approved as a specification by the lead under the human lead's delegation; not the human lead's own approval). Every pass is under the oracle route. No training, no download, no MPS.
- Output directory (git-ignored, bulk per-item records): `/Users/daniellaloush/dandush03/ArborLM/experiments/P10IS2D0-run-20261124`. Part T's run directory was read only; file lists with SHA-256 before and after are in `inputs/`.

## Gates (pass/fail and the largest deviation only)

```
{
 "identity": {
  "largest_deviation": 3.814697265625e-06,
  "pass": true
 },
 "no_write": true,
 "reproduction": {
  "largest_deviation": 0.0,
  "pass": true
 }
}
```

## Cost (measured)

```
{
 "cap_worker_hours": 8.0,
 "orchestrator_wall_seconds": 0.19582258304581046,
 "worker_hours_total": 7.714113708796148,
 "worker_seconds_total": 27770.809351666132
}
```

## Readings

### Scores, first capability (E_first; s = mean chrF-norm, G as `quantities.gap`; `differs` = share of items whose greedy output differs from the reference pass; contrast = paired per-item difference to the reference pass, standard error sd/sqrt(1000))

| cell | pass | s | G | differs | contrast | se |
|---|---|---|---|---|---|---|
| r0/AB | M1|a | 0.4534 | 0.5135 | 0.0000 | +0.00000 | 0.00000 |
| r0/AB | append|a | 0.4268 | 0.4698 | 0.8880 | -0.02657 | 0.00456 |
| r0/AB | append|d1 | 0.4102 | 0.4424 | 0.8840 | -0.04319 | 0.00469 |
| r0/AB | final|a | 0.3815 | 0.3953 | 0.9350 | -0.07188 | 0.00515 |
| r0/AB | final|b1 | 0.4534 | 0.5135 | 0.0000 | +0.00000 | 0.00000 |
| r0/AB | final|c | 0.2141 | 0.1200 | 0.9890 | -0.23924 | 0.00721 |
| r0/AB | final|d1 | 0.4075 | 0.4380 | 0.8860 | -0.04591 | 0.00449 |
| r0/AB | final|e1 | 0.4256 | 0.4678 | 0.8850 | -0.02776 | 0.00447 |
| r0/AB | final|g1 | 0.4068 | 0.4368 | 0.8890 | -0.04662 | 0.00443 |
| r0/BA | M1|a | 0.4425 | 0.5012 | 0.0000 | +0.00000 | 0.00000 |
| r0/BA | append|a | 0.4345 | 0.4884 | 0.8410 | -0.00799 | 0.00478 |
| r0/BA | append|d1 | 0.4025 | 0.4374 | 0.8430 | -0.03998 | 0.00528 |
| r0/BA | final|a | 0.3796 | 0.4007 | 0.9210 | -0.06291 | 0.00574 |
| r0/BA | final|b1 | 0.4425 | 0.5012 | 0.0000 | +0.00000 | 0.00000 |
| r0/BA | final|c | 0.1483 | 0.0315 | 1.0000 | -0.29415 | 0.00771 |
| r0/BA | final|d1 | 0.4011 | 0.4352 | 0.8330 | -0.04133 | 0.00516 |
| r0/BA | final|e1 | 0.4327 | 0.4856 | 0.8240 | -0.00978 | 0.00471 |
| r0/BA | final|g1 | 0.3876 | 0.4136 | 0.8850 | -0.05486 | 0.00530 |
| r1/AB | M1|a | 0.4537 | 0.5139 | 0.0000 | +0.00000 | 0.00000 |
| r1/AB | append|a | 0.4193 | 0.4574 | 0.8850 | -0.03437 | 0.00446 |
| r1/AB | append|d1 | 0.4026 | 0.4299 | 0.8830 | -0.05108 | 0.00467 |
| r1/AB | final|a | 0.3856 | 0.4020 | 0.9340 | -0.06803 | 0.00519 |
| r1/AB | final|b1 | 0.4537 | 0.5139 | 0.0000 | +0.00000 | 0.00000 |
| r1/AB | final|c | 0.2626 | 0.1997 | 0.9880 | -0.19104 | 0.00660 |
| r1/AB | final|d1 | 0.4073 | 0.4377 | 0.8690 | -0.04635 | 0.00460 |
| r1/AB | final|e1 | 0.4234 | 0.4641 | 0.8870 | -0.03029 | 0.00442 |
| r1/AB | final|g1 | 0.4108 | 0.4435 | 0.8870 | -0.04280 | 0.00474 |
| r1/BA | M1|a | 0.4443 | 0.5040 | 0.0000 | +0.00000 | 0.00000 |
| r1/BA | append|a | 0.4351 | 0.4895 | 0.8500 | -0.00913 | 0.00509 |
| r1/BA | append|d1 | 0.3998 | 0.4330 | 0.8510 | -0.04447 | 0.00507 |
| r1/BA | final|a | 0.3887 | 0.4154 | 0.9090 | -0.05552 | 0.00565 |
| r1/BA | final|b1 | 0.4443 | 0.5040 | 0.0000 | +0.00000 | 0.00000 |
| r1/BA | final|c | 0.0775 | -0.0816 | 1.0000 | -0.36678 | 0.00839 |
| r1/BA | final|d1 | 0.3964 | 0.4277 | 0.8520 | -0.04781 | 0.00510 |
| r1/BA | final|e1 | 0.4364 | 0.4915 | 0.8510 | -0.00786 | 0.00509 |
| r1/BA | final|g1 | 0.3870 | 0.4126 | 0.8940 | -0.05729 | 0.00528 |
| r2/AB | M1|a | 0.4489 | 0.5061 | 0.0000 | +0.00000 | 0.00000 |
| r2/AB | append|a | 0.4208 | 0.4600 | 0.8750 | -0.02807 | 0.00472 |
| r2/AB | append|d1 | 0.4077 | 0.4384 | 0.8590 | -0.04116 | 0.00475 |
| r2/AB | final|a | 0.3769 | 0.3876 | 0.9370 | -0.07206 | 0.00541 |
| r2/AB | final|b1 | 0.4489 | 0.5061 | 0.0000 | +0.00000 | 0.00000 |
| r2/AB | final|c | 0.1338 | -0.0121 | 0.9970 | -0.31509 | 0.00799 |
| r2/AB | final|d1 | 0.4107 | 0.4432 | 0.8640 | -0.03823 | 0.00468 |
| r2/AB | final|e1 | 0.4249 | 0.4667 | 0.8600 | -0.02399 | 0.00476 |
| r2/AB | final|g1 | 0.3914 | 0.4116 | 0.8950 | -0.05746 | 0.00488 |
| r2/BA | M1|a | 0.4438 | 0.5032 | 0.0000 | +0.00000 | 0.00000 |
| r2/BA | append|a | 0.4249 | 0.4732 | 0.8290 | -0.01883 | 0.00501 |
| r2/BA | append|d1 | 0.3960 | 0.4270 | 0.8330 | -0.04777 | 0.00471 |
| r2/BA | final|a | 0.3573 | 0.3653 | 0.9410 | -0.08640 | 0.00658 |
| r2/BA | final|b1 | 0.4438 | 0.5032 | 0.0000 | +0.00000 | 0.00000 |
| r2/BA | final|c | 0.1786 | 0.0799 | 0.9980 | -0.26513 | 0.00779 |
| r2/BA | final|d1 | 0.3987 | 0.4312 | 0.8370 | -0.04509 | 0.00472 |
| r2/BA | final|e1 | 0.4272 | 0.4768 | 0.8300 | -0.01654 | 0.00522 |
| r2/BA | final|g1 | 0.3883 | 0.4147 | 0.8920 | -0.05548 | 0.00538 |

### Scores, second capability (E_second; s = mean chrF-norm, G as `quantities.gap`; `differs` = share of items whose greedy output differs from the reference pass; contrast = paired per-item difference to the reference pass, standard error sd/sqrt(1000))

| cell | pass | s | G | differs | contrast | se |
|---|---|---|---|---|---|---|
| r0/AB | final|a | 0.4349 | 0.4890 | 0.0000 | +0.00000 | 0.00000 |
| r0/AB | final|b2 | 0.3512 | 0.3554 | 0.9390 | -0.08370 | 0.00588 |
| r0/AB | final|c | 0.2961 | 0.2674 | 0.9680 | -0.13879 | 0.00659 |
| r0/AB | final|d2 | 0.1946 | 0.1054 | 0.9880 | -0.24023 | 0.00754 |
| r0/AB | final|e1 | 0.1464 | 0.0284 | 0.9980 | -0.28846 | 0.00763 |
| r0/AB | final|e2 | 0.3850 | 0.4095 | 0.8980 | -0.04984 | 0.00509 |
| r0/AB | final|g2 | 0.3888 | 0.4155 | 0.8820 | -0.04603 | 0.00525 |
| r0/BA | final|a | 0.4530 | 0.5129 | 0.0000 | +0.00000 | 0.00000 |
| r0/BA | final|b2 | 0.3776 | 0.3888 | 0.9340 | -0.07544 | 0.00535 |
| r0/BA | final|c | 0.3247 | 0.3019 | 0.9600 | -0.12826 | 0.00619 |
| r0/BA | final|d2 | 0.2458 | 0.1721 | 0.9930 | -0.20719 | 0.00668 |
| r0/BA | final|e1 | 0.1537 | 0.0206 | 1.0000 | -0.29936 | 0.00719 |
| r0/BA | final|e2 | 0.4062 | 0.4359 | 0.8920 | -0.04679 | 0.00484 |
| r0/BA | final|g2 | 0.3912 | 0.4111 | 0.9090 | -0.06185 | 0.00503 |
| r1/AB | final|a | 0.4422 | 0.5008 | 0.0000 | +0.00000 | 0.00000 |
| r1/AB | final|b2 | 0.3161 | 0.2993 | 0.9530 | -0.12619 | 0.00660 |
| r1/AB | final|c | 0.3239 | 0.3119 | 0.9700 | -0.11830 | 0.00608 |
| r1/AB | final|d2 | 0.2121 | 0.1333 | 0.9960 | -0.23014 | 0.00737 |
| r1/AB | final|e1 | 0.1473 | 0.0299 | 1.0000 | -0.29493 | 0.00771 |
| r1/AB | final|e2 | 0.3052 | 0.2821 | 0.9460 | -0.13700 | 0.00674 |
| r1/AB | final|g2 | 0.3876 | 0.4136 | 0.8820 | -0.05464 | 0.00488 |
| r1/BA | final|a | 0.4490 | 0.5062 | 0.0000 | +0.00000 | 0.00000 |
| r1/BA | final|b2 | 0.3179 | 0.2907 | 0.9560 | -0.13104 | 0.00642 |
| r1/BA | final|c | 0.3393 | 0.3259 | 0.9590 | -0.10969 | 0.00559 |
| r1/BA | final|d2 | 0.1699 | 0.0473 | 1.0000 | -0.27908 | 0.00734 |
| r1/BA | final|e1 | 0.1411 | -0.0001 | 1.0000 | -0.30790 | 0.00703 |
| r1/BA | final|e2 | 0.3815 | 0.3953 | 0.9280 | -0.06746 | 0.00529 |
| r1/BA | final|g2 | 0.3732 | 0.3816 | 0.9220 | -0.07576 | 0.00507 |
| r2/AB | final|a | 0.4314 | 0.4836 | 0.0000 | +0.00000 | 0.00000 |
| r2/AB | final|b2 | 0.3412 | 0.3395 | 0.9310 | -0.09022 | 0.00648 |
| r2/AB | final|c | 0.3279 | 0.3183 | 0.9670 | -0.10348 | 0.00628 |
| r2/AB | final|d2 | 0.1768 | 0.0770 | 1.0000 | -0.25458 | 0.00768 |
| r2/AB | final|e1 | 0.1514 | 0.0364 | 1.0000 | -0.28000 | 0.00785 |
| r2/AB | final|e2 | 0.3763 | 0.3956 | 0.8880 | -0.05510 | 0.00592 |
| r2/AB | final|g2 | 0.3690 | 0.3838 | 0.8810 | -0.06247 | 0.00543 |
| r2/BA | final|a | 0.4444 | 0.4987 | 0.0000 | +0.00000 | 0.00000 |
| r2/BA | final|b2 | 0.3461 | 0.3370 | 0.9530 | -0.09830 | 0.00586 |
| r2/BA | final|c | 0.3265 | 0.3047 | 0.9660 | -0.11795 | 0.00599 |
| r2/BA | final|d2 | 0.2292 | 0.1448 | 0.9990 | -0.21517 | 0.00699 |
| r2/BA | final|e1 | 0.1608 | 0.0323 | 1.0000 | -0.28358 | 0.00721 |
| r2/BA | final|e2 | 0.3818 | 0.3957 | 0.9220 | -0.06264 | 0.00546 |
| r2/BA | final|g2 | 0.3793 | 0.3916 | 0.9160 | -0.06510 | 0.00515 |

### Decomposition, first capability, final store (path order: slots, renormalisation, values; then values first)

| cell | T | (i) slots | (ii) renorm | (iii) values | (iv) residual vs registered F | values-first values | values-first competition | interaction | (i)+(ii) share | (iii) share | comp share (values first) | values share (values first) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| r0/AB | +0.07188 | +0.04591 | -0.01815 | +0.04412 | +0.000000000 | +0.04662 | +0.02526 | -0.00250 | +0.386 | +0.614 | +0.351 | +0.649 |
| r0/BA | +0.06291 | +0.04133 | -0.03154 | +0.05312 | +0.000000000 | +0.05486 | +0.00804 | -0.00174 | +0.156 | +0.844 | +0.128 | +0.872 |
| r1/AB | +0.06803 | +0.04635 | -0.01606 | +0.03774 | +0.000000000 | +0.04280 | +0.02523 | -0.00506 | +0.445 | +0.555 | +0.371 | +0.629 |
| r1/BA | +0.05552 | +0.04781 | -0.03995 | +0.04766 | +0.000000000 | +0.05729 | -0.00177 | -0.00963 | +0.142 | +0.858 | -0.032 | +1.032 |
| r2/AB | +0.07206 | +0.03823 | -0.01424 | +0.04807 | +0.000000000 | +0.05746 | +0.01460 | -0.00939 | +0.333 | +0.667 | +0.203 | +0.797 |
| r2/BA | +0.08640 | +0.04509 | -0.02855 | +0.06986 | +0.000000000 | +0.05548 | +0.03093 | +0.01439 | +0.191 | +0.809 | +0.358 | +0.642 |

G units (term / (teacher - S0) of E_first):

| cell | T | (i) | (ii) | (iii) | interaction |
|---|---|---|---|---|---|
| r0/AB | +0.11821 | +0.07550 | -0.02984 | +0.07256 | -0.00411 |
| r0/BA | +0.10045 | +0.06599 | -0.05037 | +0.08483 | -0.00278 |
| r1/AB | +0.11188 | +0.07622 | -0.02640 | +0.06207 | -0.00832 |
| r1/BA | +0.08866 | +0.07634 | -0.06379 | +0.07611 | -0.01537 |
| r2/AB | +0.11850 | +0.06288 | -0.02342 | +0.07905 | -0.01545 |
| r2/BA | +0.13797 | +0.07201 | -0.04559 | +0.11156 | +0.02297 |

### Append point (first capability)

| cell | T at append | (i) | (ii) | (iii) | ((i)+(ii)) final minus append |
|---|---|---|---|---|---|
| r0/AB | +0.02657 | +0.04319 | -0.01662 | +0.00000 | +0.00119 |
| r0/BA | +0.00799 | +0.03998 | -0.03199 | +0.00000 | +0.00180 |
| r1/AB | +0.03437 | +0.05108 | -0.01671 | +0.00000 | -0.00408 |
| r1/BA | +0.00913 | +0.04447 | -0.03533 | +0.00000 | -0.00127 |
| r2/AB | +0.02807 | +0.04116 | -0.01310 | +0.00000 | -0.00408 |
| r2/BA | +0.01883 | +0.04777 | -0.02894 | +0.00000 | -0.00228 |

### Second capability: effect of the stage-1 rows on its read (not a retention loss; either sign)

| cell | T2 = s[b2]-s[a] | (i) | (ii) | (iii) | values-first values | values-first competition | interaction | s[a]-s[e1] (stage 2 switched off, trained keys) |
|---|---|---|---|---|---|---|---|---|
| r0/AB | -0.08370 | +0.15653 | -0.19039 | -0.04984 | -0.03767 | -0.04603 | -0.01217 | +0.28846 |
| r0/BA | -0.07544 | +0.13175 | -0.16041 | -0.04679 | -0.01360 | -0.06185 | -0.03319 | +0.29936 |
| r1/AB | -0.12619 | +0.10395 | -0.09314 | -0.13700 | -0.07156 | -0.05464 | -0.06545 | +0.29493 |
| r1/BA | -0.13104 | +0.14804 | -0.21162 | -0.06746 | -0.05529 | -0.07576 | -0.01218 | +0.30790 |
| r2/AB | -0.09022 | +0.16436 | -0.19948 | -0.05510 | -0.02775 | -0.06247 | -0.02735 | +0.28000 |
| r2/BA | -0.09830 | +0.11687 | -0.15253 | -0.06264 | -0.03320 | -0.06510 | -0.02944 | +0.28358 |

### Counterfactual RET arithmetic (it is not RET), beside the second capability's cost

| cell | read | F | rho | word | second capability cost s[a]-s[c] | G_second(c) | G_second(a) | cost s[a]-s[g(2)] | G_second(g(2)) |
|---|---|---|---|---|---|---|---|---|---|
| r0/AB | c | +0.23924 | 0.2338 | COUNTERFACTUAL RET ARITHMETIC: DOES NOT HOLD | +0.13879 | 0.2674 | 0.4890 | +0.04603 | 0.4155 |
| r0/AB | g1 | +0.04662 | 0.8507 | COUNTERFACTUAL RET ARITHMETIC: DOES NOT HOLD | +0.13879 | 0.2674 | 0.4890 | +0.04603 | 0.4155 |
| r0/BA | c | +0.29415 | 0.0628 | COUNTERFACTUAL RET ARITHMETIC: DOES NOT HOLD | +0.12826 | 0.3019 | 0.5129 | +0.06185 | 0.4111 |
| r0/BA | g1 | +0.05486 | 0.8252 | COUNTERFACTUAL RET ARITHMETIC: DOES NOT HOLD | +0.12826 | 0.3019 | 0.5129 | +0.06185 | 0.4111 |
| r1/AB | c | +0.19104 | 0.3887 | COUNTERFACTUAL RET ARITHMETIC: DOES NOT HOLD | +0.11830 | 0.3119 | 0.5008 | +0.05464 | 0.4136 |
| r1/AB | g1 | +0.04280 | 0.8630 | COUNTERFACTUAL RET ARITHMETIC: DOES NOT HOLD | +0.11830 | 0.3119 | 0.5008 | +0.05464 | 0.4136 |
| r1/BA | c | +0.36678 | -0.1620 | COUNTERFACTUAL RET ARITHMETIC: DOES NOT HOLD | +0.10969 | 0.3259 | 0.5062 | +0.07576 | 0.3816 |
| r1/BA | g1 | +0.05729 | 0.8185 | COUNTERFACTUAL RET ARITHMETIC: DOES NOT HOLD | +0.10969 | 0.3259 | 0.5062 | +0.07576 | 0.3816 |
| r2/AB | c | +0.31509 | -0.0238 | COUNTERFACTUAL RET ARITHMETIC: DOES NOT HOLD | +0.10348 | 0.3183 | 0.4836 | +0.06247 | 0.3838 |
| r2/AB | g1 | +0.05746 | 0.8133 | COUNTERFACTUAL RET ARITHMETIC: DOES NOT HOLD | +0.10348 | 0.3183 | 0.4836 | +0.06247 | 0.3838 |
| r2/BA | c | +0.26513 | 0.1587 | COUNTERFACTUAL RET ARITHMETIC: DOES NOT HOLD | +0.11795 | 0.3047 | 0.4987 | +0.06510 | 0.3916 |
| r2/BA | g1 | +0.05548 | 0.8240 | COUNTERFACTUAL RET ARITHMETIC: DOES NOT HOLD | +0.11795 | 0.3047 | 0.4987 | +0.06510 | 0.3916 |

### Registered scores for scale (Part T's registry; not recomputed)

| cell | capability | S0 | TEACHER | M1 | M-append | M-sep | E-table | D-append | D-seq | D-sep | M-seq | M-ii | M-joint |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| r0/AB | first | 0.1412 | 0.7492 | 0.4534 | 0.3815 | 0.4534 | 0.4527 | 0.1473 | 0.1551 | 0.5298 | 0.1806 | 0.4555 | 0.4740 |
| r0/AB | second | 0.1286 | 0.7548 | 0.1243 | 0.4349 | 0.4425 | 0.4579 | 0.4873 | 0.5179 | 0.5019 | 0.4477 | 0.4389 | 0.4539 |
| r0/BA | first | 0.1286 | 0.7548 | 0.4425 | 0.3796 | 0.4425 | 0.4579 | 0.1421 | 0.1510 | 0.5019 | 0.1287 | 0.4458 | 0.4539 |
| r0/BA | second | 0.1412 | 0.7492 | 0.1401 | 0.4530 | 0.4534 | 0.4527 | 0.5304 | 0.5250 | 0.5298 | 0.4610 | 0.4586 | 0.4740 |
| r1/AB | first | 0.1412 | 0.7492 | 0.4537 | 0.3856 | 0.4537 | 0.4598 | 0.1566 | 0.1609 | 0.5290 | 0.1673 | 0.4608 | 0.4594 |
| r1/AB | second | 0.1286 | 0.7548 | 0.1238 | 0.4422 | 0.4443 | 0.4466 | 0.4909 | 0.5077 | 0.5037 | 0.4466 | 0.4438 | 0.4578 |
| r1/BA | first | 0.1286 | 0.7548 | 0.4443 | 0.3887 | 0.4443 | 0.4466 | 0.1463 | 0.1504 | 0.5037 | 0.0989 | 0.4439 | 0.4578 |
| r1/BA | second | 0.1412 | 0.7492 | 0.1403 | 0.4490 | 0.4537 | 0.4598 | 0.5245 | 0.5284 | 0.5290 | 0.4566 | 0.4492 | 0.4594 |
| r2/AB | first | 0.1412 | 0.7492 | 0.4489 | 0.3769 | 0.4489 | 0.4554 | 0.1464 | 0.1496 | 0.5386 | 0.0009 | 0.4566 | 0.4622 |
| r2/AB | second | 0.1286 | 0.7548 | 0.1219 | 0.4314 | 0.4438 | 0.4390 | 0.4931 | 0.4924 | 0.4836 | 0.4506 | 0.4342 | 0.4449 |
| r2/BA | first | 0.1286 | 0.7548 | 0.4438 | 0.3573 | 0.4438 | 0.4390 | 0.1435 | 0.1511 | 0.4836 | 0.1101 | 0.4354 | 0.4449 |
| r2/BA | second | 0.1412 | 0.7492 | 0.1277 | 0.4444 | 0.4489 | 0.4554 | 0.5252 | 0.5520 | 0.5386 | 0.4641 | 0.4522 | 0.4622 |

## Summary words (ADR-0035 section 7; descriptive; none is a label)

- path order: **MIXED**
- values-first order: **MIXED**
- final wording: **MIXED**
- cells with T not positive: []
- means beside the per-cell values: `{"T": 0.06946701207277318, "i": 0.04411896264439422, "ii": -0.02474816862258165, "iii": 0.0500962180509606, "interaction": -0.002322589573252496, "values_first_competition": 0.01704820444856008, "values_first_values": 0.0524188076242131}`

## Reported whatever the result (section 12)

- gate record: above; every table of sections 5 and 6 for every cell and panel: in `report.txt` (and `records/`), including readings that show nothing, negative shares and conditions that make the first capability worse; the interaction and both orders' words: above; the second capability's cost beside every first-capability reading: above; registered scores for scale: above; cost against the cap: above.
- failed attempts of this run and disagreements with the audit: none recorded here; the independent recomputation is a separate stage not performed by this record (the auditor's).
- `row_shares` of Part T was not opened (ADR-0035 section 1.5).

## Report-step re-run (lead decision 1)

The driver, launched at commit `e74cbf25bac019156be34c0a51a416749a4da16a`, finished all 96 counted passes (worker exit codes [0, 0, 0]) and then crashed in the report step (`finalize.render` statistics loop, `TypeError: string indices must be integers, not 'str'`). The fix (one line in `finalize.py`) and a new entry point `studies/p10is2d0/finalize_only.py` are commit `ffd29d74b6c1ceb5599dd4427ecbbf1e6b8c9e04`; `finalize_only` produced `report.txt`, `records/` and `run_complete.json` from the existing pass records (SHA-256 of every pass, statistics and gate record written first: `inputs/record_hashes_before_finalize.json`; changed files between the two commits: `inputs/finalize_code_difference.json`). No pass was recomputed. See `LEAD_DECISION_1.md` (lead decision, not human approval; Astra review: NOT_PERFORMED).

Worker hours (measured): 7.714 of the 8.0 cap (`records/cost.json` 7.7141; `run_complete.json` 7.7142 after one more ledger tick). The 24 reproduction passes are included.

Part T run directory: 412 files hashed independently before the launch and after finalize with `shasum -a 256`; the lists are identical (measured). The driver's own before/after diff: 0 added, 0 removed, 0 changed.

## Disclosures

- `chmod +x` was run once on `studies/p10is2d0/launch_d0.sh` by the implementer in the first session, against the no-chmod rule; the coordinator ruled that the bit stays (noted in `studies/p10is2d0/NOTES.md`).
- `pkill -f` by pattern was used once by the implementer (to stop its own timed-out pytest wrapper, `timeout 580 uv run ...`, while re-running the Part T test subset). It was not a signal to any run process.
- ADR-0035 draft 3 had no third review; no implementation audit was done before launch.
- The report step crashed after the last pass (above); the failed attempt and its traceback are kept (`LEAD_DECISION_1.md`, the git-ignored `launch.log`).
- The first Part T test run on the full disk was void (about 330 errors, disk full); the valid run is 376 passed, 2 xfailed.
- The deterministic-algorithms setting was ON, as ADR-0035 says, although Part T's frozen config says false; the reproduction gate passed (largest deviation 0.0), so the setting did not matter for the gate.
- `studies/p10is2/evaluate.py` in ADR-0035 section 3 means `studies/p10s2/evaluate.py` (path correction accepted by the coordinator).
- The oracle and post-hoc lines sit above every report block and in every JSON record, not on every text line (accepted).

