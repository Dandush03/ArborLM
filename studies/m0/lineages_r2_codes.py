# ruff: noqa: E501
"""R2 batch 1, family "codes": error-detecting and error-locating codes with their rule stated in the item (Luhn weighting; Hamming syndrome)."""

from __future__ import annotations

import random

from studies.m0.core import Built
from studies.m0.lineages_r2_common import batch1


def luhn_total(digits: list[int]) -> int:
    """digits written left to right; the rightmost is not doubled, the next one left is doubled, and so on."""
    total = 0
    for pos, d in enumerate(reversed(digits)):
        if pos % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total


_LUHN_RULE = ("Start at the rightmost digit and move left: leave the 1st digit as it is, double the 2nd, leave the 3rd, double the 4th, and so on. "
              "Whenever a doubled digit is more than 9, subtract 9 from it. Add up all the results.")


@batch1("codes")
def luhn_check(level: int, r: random.Random) -> Built:
    """Procedure: alternate-digit doubling checksum (Luhn). structured: {"digits": [int] (the number as written), "ask": "valid" | "check_digit"}.
    valid: yes/no, whether the whole number's total is a multiple of 10 (invalid items change exactly one digit of a valid number, which is always detected). check_digit: payload `digits`;
    the check digit is written at the right end of the payload and the rule above is applied to the whole number (so the digit written is NOT doubled and the payload's last digit IS doubled). Answer: the digit 0-9 that makes the total a multiple of 10."""
    n = 6 + level * 2
    payload = [r.randint(0, 9) for _ in range(n)]
    if r.random() < 0.5:
        cd = (-luhn_total([*payload, 0])) % 10
        full = [*payload, cd]
        want = r.choice(("yes", "no"))
        if want == "no":
            i = r.randrange(len(full))
            full[i] = (full[i] + r.randint(1, 9)) % 10
        assert (luhn_total(full) % 10 == 0) == (want == "yes")
        q = (f"{_LUHN_RULE} The number is valid if the total is a multiple of 10. Is the number {''.join(map(str, full))} valid? Answer yes or no.")
        return Built(q, {"digits": full, "ask": "valid"}, want, "yn", 2)
    cd = (-luhn_total([*payload, 0])) % 10
    q = (f"{_LUHN_RULE} A number is valid if the total is a multiple of 10. One more digit is to be written at the right end of {''.join(map(str, payload))} so that the new number is valid "
         "(the digit written there is the rightmost digit of the new number). Which digit must be written?")
    return Built(q, {"digits": payload, "ask": "check_digit"}, str(cd), "number", None)


def hamming_encode(data_bits: list[int], n: int) -> list[int]:
    word = [0] * (n + 1)  # 1-based
    it = iter(data_bits)
    for pos in range(1, n + 1):
        if pos & (pos - 1):
            word[pos] = next(it)
    p = 1
    while p <= n:
        word[p] = sum(word[q] for q in range(1, n + 1) if q & p and q != p) % 2
        p *= 2
    return word[1:]


def hamming_syndrome(bits: list[int]) -> int:
    s = 0
    for pos, b in enumerate(bits, 1):
        if b:
            s ^= pos
    return s


@batch1("codes")
def hamming_error_position(level: int, r: random.Random) -> Built:
    """Procedure: parity-check syndrome of a Hamming code. structured: {"bits": [0|1] (position 1 is the leftmost), "n": int}.
    Positions that are powers of two (1, 2, 4, 8, ...) are check positions; the check at position 2^j is set so that the count of 1s among all positions whose number has a 1 in binary place 2^j (itself included) is even.
    The word was a correct codeword before at most one position was flipped. Answer: the flipped position, or 0 when nothing was flipped (level 0 always has a flip). Half the flips are drawn from the non-check positions only."""
    n = (15, 15, 15, 31, 31, 31, 63)[level]
    ndata = n - (n + 1).bit_length() + 1
    data = [r.randint(0, 1) for _ in range(ndata)]
    word = hamming_encode(data, n)
    if level >= 1 and r.random() < 0.10:
        flip = 0
    elif r.random() < 0.5:
        flip = r.choice([q for q in range(1, n + 1) if q & (q - 1)])  # never a check position
    else:
        flip = r.randint(1, n)
    if flip:
        word[flip - 1] ^= 1
    assert hamming_syndrome(word) == flip
    q = (f"A word of {n} binary digits is written below; position 1 is the leftmost digit. Positions 1, 2, 4, 8, ... (the powers of two) are check positions. "
         "The check at position 2^j was chosen so that, among all positions whose number written in binary has a 1 in the place worth 2^j (the check position itself included), the count of 1s is even. "
         f"The word was correct when it was sent, and at most one digit has been flipped since. Word: {''.join(map(str, word))}. Which position was flipped? Answer 0 if none was.")
    return Built(q, {"bits": word, "n": n}, str(flip), "number", None)
