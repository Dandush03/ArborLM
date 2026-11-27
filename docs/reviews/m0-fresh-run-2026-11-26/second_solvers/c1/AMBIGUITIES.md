# AMBIGUITIES: C1 (NAME = c1)

Number of ambiguities found: **0**.

Every one of the 7280 items uses the same wording ("Here is a Python program. ... What exactly does it print? It prints a single line."), and the program is fixed Python source with no input, so the expected line is determined by Python's semantics. I found no item where two readings of the text give different answers.

Points I considered and did not count as ambiguities (they do not change any answer here):
- Python semantics vs another language's: the source is stated to be Python, so `//` and `%` floor (110 items have a negative operand: 48 in bytecode_loop_f3, 62 in func_compose_f4, e.g. func_compose_f4 L0 #10 where `-3 % 19` is 16 in Python and -3 under truncation) and slices clamp. A reader using C-like truncation would answer differently; that is a misreading of Python, not an ambiguity of the text.
- How `print` separates several arguments: no program calls `print` with more than one argument, so the separator never matters.
- Recursion depth and int-to-str digit limits of CPython: no item comes near either (measured by `limits_census.py`: maximum user-call depth 18, recursive_calls_r2 L6 #0; longest printed int 13 digits, digit_peel_f3 L6 #11; maximum 580 interpreter steps per item).
