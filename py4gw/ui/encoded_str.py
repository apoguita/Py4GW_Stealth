"""The client's encoded-string arithmetic, ported from ``GW::ui``.

The game does not store translatable text as text. It stores **codepoint arrays**,
and the codepoints encode numbers in base ``WORD_VALUE_RANGE`` with a continuation
bit, using ``WORD_VALUE_BASE`` as the digit base. Three of the functions that work on
those arrays are pure arithmetic and touch no client state:

- ``UInt32ToEncStr`` — a number to its encoded form;
- ``EncStrToUInt32`` — the reverse;
- ``IsValidEncStr`` — a structural validator for the whole array, which is the
  precondition ``AsyncDecodeStr`` checks before it decodes anything.

**Source:** ``src/GW/ui/ui_methods.cpp`` — the constants at ``152-159``, the character
classes at ``260-281``, the validator at ``283-362``, and the three functions at
``2613-2656``. It is a port, not a re-implementation: the branch order, the advance
rules and the return values are the source's.

Two things about the shape of this port:

- The C++ functions advance a ``const wchar_t*&`` reference. Python has no reference
  parameter, so each one takes an index and returns the index it advanced to, beside
  the boolean it returned in C++. A caller chains them the way the C++ does.
- ``term`` is what the source passes around: a position one past the codepoint that
  terminates the array. ``is_valid_enc_str`` derives it exactly as ``IsValidEncStr``
  does (``2618-2622``), bounded by the array the caller read.
"""

from __future__ import annotations

from collections.abc import Sequence

#: ``ui_methods.cpp:152-159``. Transcribed, including ``WORD_VALUE_RANGE`` being
#: derived rather than written out.
TERM_FINAL = 0x0000
TERM_INTERMEDIATE = 0x0001
CONCAT_CODED = 0x0002
CONCAT_LITERAL = 0x0003
STRING_CHAR_FIRST = 0x0010
WORD_VALUE_BASE = 0x0100
WORD_BIT_MORE = 0x8000
WORD_VALUE_RANGE = WORD_BIT_MORE - WORD_VALUE_BASE

#: The 32-bit mask the C++ gets for free: ``uint32_t`` arithmetic wraps.
_UINT32_MASK = 0xFFFFFFFF


# ── the character classes (``ui_methods.cpp:260-281``) ───────────────────────


def enc_chr_is_control_character(value: int) -> bool:
    """``EncChrIsControlCharacter``: the four codepoints that end a structure."""

    return (
        value == TERM_FINAL
        or value == TERM_INTERMEDIATE
        or value == CONCAT_CODED
        or value == CONCAT_LITERAL
    )


def enc_chr_is_param(value: int) -> bool:
    """``EncChrIsParam``: the parameter codepoint range, ``0x101``-``0x10F``."""

    return 0x101 <= value <= 0x10F


def enc_chr_is_param_segment(value: int) -> bool:
    """``EncChrIsParamSegment``: the three codepoints that open a nested segment."""

    return 0x10A <= value <= 0x10C


def enc_chr_is_param_literal(value: int) -> bool:
    """``EncChrIsParamLiteral``: the three codepoints followed by a literal run."""

    return 0x107 <= value <= 0x109


def enc_chr_is_param_numeric(value: int) -> bool:
    """``EncChrIsParamNumeric``: a parameter that is neither literal nor segment."""

    return (
        enc_chr_is_param(value)
        and not enc_chr_is_param_literal(value)
        and not enc_chr_is_param_segment(value)
    )


# ── the validator (``ui_methods.cpp:283-362``) ───────────────────────────────


def enc_str_validate_terminated_literal(
    data: Sequence[int], index: int, term: int
) -> tuple[bool, int]:
    """``EncStrValidateTerminatedLiteral``: a literal run ends at ``TERM_INTERMEDIATE``."""

    while index < term:
        value = data[index]
        index += 1
        if value < STRING_CHAR_FIRST:
            return value == TERM_INTERMEDIATE, index
    return False, index


def enc_str_validate_single_word(
    data: Sequence[int], index: int, term: int
) -> tuple[bool, int]:
    """``EncStrValidateSingleWord``: one base-``0x7F00`` digit run, high bit chained."""

    while True:
        value = data[index]
        index += 1
        if (value & ~WORD_BIT_MORE) < WORD_VALUE_BASE:
            return False, index
        if not (value & WORD_BIT_MORE):
            break
    return index < term, index


def enc_str_validate_word(
    data: Sequence[int], index: int, term: int
) -> tuple[bool, int]:
    """``EncStrValidateWord``: one word, or two when the next codepoint continues it."""

    ok, index = enc_str_validate_single_word(data, index, term)
    if not ok:
        return False, index
    if not (data[index] & WORD_BIT_MORE):
        return True, index
    return enc_str_validate_single_word(data, index, term)


def enc_str_validate(
    data: Sequence[int], index: int, term: int
) -> tuple[bool, int]:
    """``EncStrValidate``: the whole structure, parameters and segments included."""

    first_loop = True
    while index < term:
        value = 0
        if not first_loop:
            value = data[index]
            index += 1
            if value == TERM_FINAL:
                return index == term, index
            if value == TERM_INTERMEDIATE:
                return index < term, index
            if value == CONCAT_LITERAL:
                ok, index = enc_str_validate_terminated_literal(data, index, term)
                if ok:
                    continue
                return False, index

        ok, index = enc_str_validate_word(data, index, term)
        if not ok:
            return False, index

        while index < term and not enc_chr_is_control_character(data[index]):
            value = data[index]
            index += 1
            if enc_chr_is_param(value):
                if enc_chr_is_param_literal(value):
                    ok, index = enc_str_validate_terminated_literal(
                        data, index, term
                    )
                    if not ok:
                        return False, index
                elif enc_chr_is_param_segment(value):
                    ok, index = enc_str_validate(data, index, term)
                    if not ok:
                        return False, index
                elif enc_chr_is_param_numeric(value):
                    ok, index = enc_str_validate_single_word(data, index, term)
                    if not ok:
                        return False, index
                else:
                    return False, index

        first_loop = False
    return False, index


def is_valid_enc_str(enc_str: Sequence[int]) -> bool:
    """``IsValidEncStr`` (``ui_methods.cpp:2613-2629``): is this a well-formed array?

    The source walks to the terminator to find ``term`` and then requires the
    validator to consume exactly up to it. ``TERM_FINAL`` is ``0``, so the source's
    two checks (``!= TERM_FINAL`` and ``!= 0``) are the same check; this port writes
    the one that matters. The walk is bounded by the array the caller read, which is
    the external counterpart of the source's in-process pointer walk.
    """

    term = 0
    while term < len(enc_str) and enc_str[term] != TERM_FINAL:
        term += 1
    term += 1

    ok, index = enc_str_validate(enc_str, 0, term)
    if not ok:
        return False
    return index == term


# ── the conversions (``ui_methods.cpp:2631-2656``) ───────────────────────────


def uint32_to_enc_str(value: int, count: int) -> list[int] | None:
    """``UInt32ToEncStr``: encode a number, or ``None`` when it does not fit.

    ``count`` is the destination the source is given; ``None`` is the source's
    ``false``, which is what it returns when ``cases_required + 1 > count``. The
    buffer ends with ``TERM_FINAL``, and every digit except the last carries
    ``WORD_BIT_MORE``.
    """

    cases_required = (value + WORD_VALUE_RANGE - 1) // WORD_VALUE_RANGE
    if cases_required + 1 > count:
        return None

    buffer = [0] * (cases_required + 1)
    remaining = value
    for index in range(cases_required - 1, -1, -1):
        buffer[index] = WORD_VALUE_BASE + (remaining % WORD_VALUE_RANGE)
        remaining //= WORD_VALUE_RANGE
        if index != cases_required - 1:
            buffer[index] |= WORD_BIT_MORE
    return buffer


def enc_str_to_uint32(enc_str: Sequence[int]) -> int:
    """``EncStrToUInt32``: decode the number an encoded array carries.

    The source asserts every digit is at or above ``WORD_VALUE_BASE``; this port
    keeps the arithmetic (including the ``uint32`` wrap the C++ gets for free)
    rather than adding a check the source does not make.
    """

    value = 0
    index = 0
    while True:
        value = (
            value * WORD_VALUE_RANGE
            + ((enc_str[index] & ~WORD_BIT_MORE) - WORD_VALUE_BASE)
        ) & _UINT32_MASK
        more = enc_str[index] & WORD_BIT_MORE
        index += 1
        if not more:
            return value
