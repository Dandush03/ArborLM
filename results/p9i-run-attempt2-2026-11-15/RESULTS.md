# ADR-0017 Part I (P9I) results

Study status: **COMPLETE** (measured: derived from the run's manifests, gates and records).
Matched updates U: 8192 (the same at every size).
Gate G1 passed: True; gate G2 passed: True; gate G4 passed: True; LEAKAGE flags: none.
Missing cells: none; non-completed tasks: none.

## Selection (section I.8.3)

Outcome: **NO_INTERFACE_SELECTED** (decided at step 4).

Scope statements carried with the outcome:
- no tested interface reached INTERFACE_WORKS at all three sizes within U updates; ADR-0017 stays blocked on this backbone

## Classes at each size (measured accuracies, rules of section I.8.1)

| arm | slots | class | dense comparison | language modelling | B102 present |
|---|---|---|---|---|---|
| A4 | 4096 | INTERFACE_FAILS | NOT COMPARED |  | False |
| A4 | 16384 | INTERFACE_FAILS | NOT COMPARED |  | True |
| A4 | 65536 | INTERFACE_FAILS | NOT COMPARED |  | False |
| A4E | 16384 | INTERFACE_FAILS | NOT COMPARED |  | False |
| BB | 4096 | INTERFACE_PARTIAL |  | LANGUAGE MODELLING DEGRADED | False |
| BB | 16384 | INTERFACE_FAILS | NOT COMPARED | LANGUAGE MODELLING DEGRADED | True |
| BB | 65536 | INTERFACE_FAILS | NOT COMPARED | LANGUAGE MODELLING DEGRADED | False |
| E7 | 16384 | INTERFACE_FAILS | NOT COMPARED |  | False |
| N | 4096 | INTERFACE_FAILS | NOT COMPARED |  | False |
| N | 16384 | INTERFACE_FAILS | NOT COMPARED |  | False |
| N | 65536 | INTERFACE_FAILS | NOT COMPARED |  | False |
| W7 | 4096 | INTERFACE_FAILS |  |  | False |
| W7 | 16384 | INTERFACE_FAILS | NOT COMPARED |  | True |
| W7 | 65536 | INTERFACE_FAILS | NOT COMPARED |  | False |

## Backbone contrast at 16,384 (annotation, does not change a class)

- A4E/A4: not printed
- E7/W7: not printed

## Exposures per fact and parameters (analytical exposure, measured counts)

| cell | facts | U | exposures per fact (analytical) | trainable | trainable backbone | optimizer-state bytes |
|---|---|---|---|---|---|---|
| A4-n16384-b101-o301-s1801 | 8192 | 8192 | 128.0 | 791041 | 0 | 6328360 |
| A4-n16384-b101-o301-s1802 | 8192 | 8192 | 128.0 | 791041 | 0 | 6328360 |
| A4-n16384-b102-o302-s1801 | 8192 | 8192 | 128.0 | 791041 | 0 | 6328360 |
| A4-n4096-b101-o301-s1801 | 2048 | 8192 | 512.0 | 201217 | 0 | 1609768 |
| A4-n4096-b101-o301-s1802 | 2048 | 8192 | 512.0 | 201217 | 0 | 1609768 |
| A4-n65536-b101-o301-s1801 | 32768 | 8192 | 32.0 | 3150337 | 0 | 25202728 |
| A4-n65536-b101-o301-s1802 | 32768 | 8192 | 32.0 | 3150337 | 0 | 25202728 |
| A4E-n16384-b101-o301-s1801 | 8192 | 8192 | 128.0 | 791041 | 0 | 6328360 |
| A4E-n16384-b101-o301-s1802 | 8192 | 8192 | 128.0 | 791041 | 0 | 6328360 |
| BB-0-n16384-b101-o301-s1801 | 8192 | 8192 | 128.0 | 4224 | 4224 | 33808 |
| BB-0-n16384-b101-o301-s1802 | 8192 | 8192 | 128.0 | 4224 | 4224 | 33808 |
| BB-0-n4096-b101-o301-s1801 | 2048 | 8192 | 512.0 | 4224 | 4224 | 33808 |
| BB-0-n4096-b101-o301-s1802 | 2048 | 8192 | 512.0 | 4224 | 4224 | 33808 |
| BB-0-n65536-b101-o301-s1801 | 32768 | 8192 | 32.0 | 4224 | 4224 | 33808 |
| BB-0-n65536-b101-o301-s1802 | 32768 | 8192 | 32.0 | 4224 | 4224 | 33808 |
| BB-D-n16384-b101-o301-s1801 | 8192 | 8192 | 128.0 | 792193 | 4224 | 6337572 |
| BB-D-n16384-b101-o301-s1802 | 8192 | 8192 | 128.0 | 792193 | 4224 | 6337572 |
| BB-D-n65536-b101-o301-s1801 | 32768 | 8192 | 32.0 | 3151489 | 4224 | 25211940 |
| BB-D-n65536-b101-o301-s1802 | 32768 | 8192 | 32.0 | 3151489 | 4224 | 25211940 |
| BB-n16384-b101-o301-s1801 | 8192 | 8192 | 128.0 | 792193 | 4224 | 6337580 |
| BB-n16384-b101-o301-s1802 | 8192 | 8192 | 128.0 | 792193 | 4224 | 6337580 |
| BB-n16384-b102-o302-s1801 | 8192 | 8192 | 128.0 | 792193 | 4224 | 6337580 |
| BB-n4096-b101-o301-s1801 | 2048 | 8192 | 512.0 | 202369 | 4224 | 1618988 |
| BB-n4096-b101-o301-s1802 | 2048 | 8192 | 512.0 | 202369 | 4224 | 1618988 |
| BB-n65536-b101-o301-s1801 | 32768 | 8192 | 32.0 | 3151489 | 4224 | 25211948 |
| BB-n65536-b101-o301-s1802 | 32768 | 8192 | 32.0 | 3151489 | 4224 | 25211948 |
| D-n16384-b101-o301-s1801 | 8192 | 8192 | 128.0 | 787969 | 0 | 6303764 |
| D-n16384-b101-o301-s1802 | 8192 | 8192 | 128.0 | 787969 | 0 | 6303764 |
| D7-n16384-b101-o301-s1801 | 8192 | 8192 | 128.0 | 791041 | 0 | 6328340 |
| D7-n16384-b101-o301-s1802 | 8192 | 8192 | 128.0 | 791041 | 0 | 6328340 |
| D7-n16384-b102-o302-s1801 | 8192 | 8192 | 128.0 | 791041 | 0 | 6328340 |
| D7-n65536-b101-o301-s1801 | 32768 | 8192 | 32.0 | 3150337 | 0 | 25202708 |
| D7-n65536-b101-o301-s1802 | 32768 | 8192 | 32.0 | 3150337 | 0 | 25202708 |
| E7-n16384-b101-o301-s1801 | 8192 | 8192 | 128.0 | 791041 | 0 | 6328348 |
| E7-n16384-b101-o301-s1802 | 8192 | 8192 | 128.0 | 791041 | 0 | 6328348 |
| N-n16384-b101-o301-s1801 | 8192 | 8192 | 128.0 | 787969 | 0 | 6303772 |
| N-n16384-b101-o301-s1802 | 8192 | 8192 | 128.0 | 787969 | 0 | 6303772 |
| N-n4096-b101-o301-s1801 | 2048 | 8192 | 512.0 | 198145 | 0 | 1585180 |
| N-n4096-b101-o301-s1802 | 2048 | 8192 | 512.0 | 198145 | 0 | 1585180 |
| N-n65536-b101-o301-s1801 | 32768 | 8192 | 32.0 | 3147265 | 0 | 25178140 |
| N-n65536-b101-o301-s1802 | 32768 | 8192 | 32.0 | 3147265 | 0 | 25178140 |
| R1-n16384-b101-o301-s1801 | 8192 | 8192 | 128.0 | 787457 | 0 | 6299672 |
| R1-n16384-b101-o301-s1802 | 8192 | 8192 | 128.0 | 787457 | 0 | 6299672 |
| R1-n16384-b102-o302-s1801 | 8192 | 8192 | 128.0 | 787457 | 0 | 6299672 |
| R1-n4096-b101-o301-s1801 | 2048 | 8192 | 512.0 | 197633 | 0 | 1581080 |
| R1-n4096-b101-o301-s1802 | 2048 | 8192 | 512.0 | 197633 | 0 | 1581080 |
| R1-n65536-b101-o301-s1801 | 32768 | 8192 | 32.0 | 3146753 | 0 | 25174040 |
| R1-n65536-b101-o301-s1802 | 32768 | 8192 | 32.0 | 3146753 | 0 | 25174040 |
| R2-n16384-b101-o301-s1801 | 8192 | 8192 | 128.0 | 525313 | 0 | 4202516 |
| R2-n16384-b101-o301-s1802 | 8192 | 8192 | 128.0 | 525313 | 0 | 4202516 |
| W7-n16384-b101-o301-s1801 | 8192 | 8192 | 128.0 | 791041 | 0 | 6328348 |
| W7-n16384-b101-o301-s1802 | 8192 | 8192 | 128.0 | 791041 | 0 | 6328348 |
| W7-n16384-b102-o302-s1801 | 8192 | 8192 | 128.0 | 791041 | 0 | 6328348 |
| W7-n4096-b101-o301-s1801 | 2048 | 8192 | 512.0 | 201217 | 0 | 1609756 |
| W7-n4096-b101-o301-s1802 | 2048 | 8192 | 512.0 | 201217 | 0 | 1609756 |
| W7-n65536-b101-o301-s1801 | 32768 | 8192 | 32.0 | 3150337 | 0 | 25202716 |
| W7-n65536-b101-o301-s1802 | 32768 | 8192 | 32.0 | 3150337 | 0 | 25202716 |

## What must not be claimed (section I.13)

- Nothing about capacity scaling, utilization, locality or incremental learning is tested here. A difference in class between sizes is not evidence about capacity: exposures per fact differ sixteenfold.
- A WORKS class for W7, E7, A4 or A4E does not show the language model communicating what it needs.
- INTERFACE_WORKS for BB does not show that a language model reliably communicates what it needs; the block-0 attention was retrained on this task's answer loss alone, with its next-byte loss unprotected.
- An interface that works here is not shown to work on natural language (fixed-length records, random identifiers).
- W7 is not a general interface: it is told the record length.
- A failure of all interfaces is not a failure of the ArborLM concept; it is a statement about this backbone within U updates.
- DENSE SUFFICES does not say memory is not needed in general.
- The oracle rungs R1 and R2 are references, not systems.
- Astra review: NOT_PERFORMED. Claude review is not Astra review; no human approval is implied by this report.

