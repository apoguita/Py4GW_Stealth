"""Offline tests for the encoded-string arithmetic ported from ``GW::ui``.

The three functions ported here are pure arithmetic — no client, no read path — so they are
tested directly. What the tests pin is the source's behaviour, including the two places its
own length formula makes the encoding lossy, because a port that "fixed" those would return
different bytes than the game does.

The codepoint values used are the ones the game actually encodes: ids that fit in one or two
base-``0x7F00`` digits. ``UInt32ToEncStr`` is called by the source with a buffer of 8
codepoints (`quest_bindings.cpp:160`), which is its practical domain.
"""

from __future__ import annotations

import unittest

from py4gw.ui import encoded_str as encoded


class EncodedStringConstantTests(unittest.TestCase):
    """The constants the grammar and the arithmetic share (``ui_methods.cpp:152-159``)."""

    def test_every_constant_matches_the_source(self) -> None:
        self.assertEqual(encoded.TERM_FINAL, 0x0000)
        self.assertEqual(encoded.TERM_INTERMEDIATE, 0x0001)
        self.assertEqual(encoded.CONCAT_CODED, 0x0002)
        self.assertEqual(encoded.CONCAT_LITERAL, 0x0003)
        self.assertEqual(encoded.STRING_CHAR_FIRST, 0x0010)
        self.assertEqual(encoded.WORD_VALUE_BASE, 0x0100)
        self.assertEqual(encoded.WORD_BIT_MORE, 0x8000)

    def test_the_range_is_derived_from_the_two_bounds(self) -> None:
        """``WORD_VALUE_RANGE = WORD_BIT_MORE - WORD_VALUE_BASE``, as the source derives it."""

        self.assertEqual(encoded.WORD_VALUE_RANGE, 0x7F00)
        self.assertEqual(
            encoded.WORD_VALUE_RANGE,
            encoded.WORD_BIT_MORE - encoded.WORD_VALUE_BASE,
        )


class CharacterClassTests(unittest.TestCase):
    """``EncChrIs*`` (``ui_methods.cpp:260-281``)."""

    def test_control_characters_are_the_four_terminators(self) -> None:
        for value in (0x0000, 0x0001, 0x0002, 0x0003):
            with self.subTest(value=hex(value)):
                self.assertTrue(encoded.enc_chr_is_control_character(value))
        for value in (0x0004, 0x0010, 0x0100, 0x8000):
            with self.subTest(value=hex(value)):
                self.assertFalse(encoded.enc_chr_is_control_character(value))

    def test_the_param_range_is_inclusive(self) -> None:
        self.assertFalse(encoded.enc_chr_is_param(0x100))
        self.assertTrue(encoded.enc_chr_is_param(0x101))
        self.assertTrue(encoded.enc_chr_is_param(0x10F))
        self.assertFalse(encoded.enc_chr_is_param(0x110))

    def test_literal_and_segment_are_the_two_sub_ranges(self) -> None:
        for value in (0x107, 0x108, 0x109):
            with self.subTest(value=hex(value)):
                self.assertTrue(encoded.enc_chr_is_param_literal(value))
                self.assertFalse(encoded.enc_chr_is_param_segment(value))
        for value in (0x10A, 0x10B, 0x10C):
            with self.subTest(value=hex(value)):
                self.assertTrue(encoded.enc_chr_is_param_segment(value))
                self.assertFalse(encoded.enc_chr_is_param_literal(value))

    def test_numeric_is_param_minus_literal_and_segment(self) -> None:
        self.assertFalse(encoded.enc_chr_is_param_numeric(0x107))
        self.assertFalse(encoded.enc_chr_is_param_numeric(0x10A))
        self.assertTrue(encoded.enc_chr_is_param_numeric(0x101))
        self.assertTrue(encoded.enc_chr_is_param_numeric(0x10F))


class EncodedNumberTests(unittest.TestCase):
    """``UInt32ToEncStr`` / ``EncStrToUInt32`` (``ui_methods.cpp:2631-2656``)."""

    def test_one_digit_ids_round_trip(self) -> None:
        for value in (1, 2, 0x11, 0x1184, 0x7EFF):
            with self.subTest(value=hex(value)):
                encoded_value = encoded.uint32_to_enc_str(value, 8)
                assert encoded_value is not None
                self.assertEqual(encoded_value[-1], encoded.TERM_FINAL)
                self.assertEqual(encoded.enc_str_to_uint32(encoded_value), value)

    def test_two_digit_ids_carry_the_continuation_bit(self) -> None:
        """The high digit sets ``WORD_BIT_MORE``; the low one does not."""

        encoded_value = encoded.uint32_to_enc_str(0x7F01, 8)
        assert encoded_value is not None
        self.assertEqual(encoded_value[0] & encoded.WORD_BIT_MORE, encoded.WORD_BIT_MORE)
        self.assertEqual(encoded_value[1] & encoded.WORD_BIT_MORE, 0)
        self.assertEqual(encoded.enc_str_to_uint32(encoded_value), 0x7F01)

    def test_ids_above_the_first_digit_round_trip(self) -> None:
        """The length formula over-estimates here, and the extra digits are leading zeros."""

        for value in (0x7F00 + 1, 2 * 0x7F00, 2 * 0x7F00 + 1, 3 * 0x7F00, 0xFE00 - 1):
            with self.subTest(value=hex(value)):
                encoded_value = encoded.uint32_to_enc_str(value, 8)
                assert encoded_value is not None
                self.assertEqual(encoded.enc_str_to_uint32(encoded_value), value)

    def test_the_length_formula_is_the_sources_and_it_is_lossy_twice(self) -> None:
        """``cases_required = ceil(value / RANGE)``, ported as written.

        Two values do not survive it, and the port keeps that rather than correcting it:

        - ``0`` needs no digits, so only the terminator is written and the decoder reads a
          digit of ``-0x100``, which wraps;
        - exactly one range — ``0x7F00`` — needs two digits but the formula asks for one,
          so the leading digit is dropped.

        Between two ranges the formula is exact and from there it over-estimates, which the
        decoder absorbs because the extra digits are leading zeros.
        """

        self.assertEqual(encoded.uint32_to_enc_str(0, 8), [encoded.TERM_FINAL])
        self.assertNotEqual(encoded.enc_str_to_uint32([encoded.TERM_FINAL]), 0)

        one_range = encoded.uint32_to_enc_str(encoded.WORD_VALUE_RANGE, 8)
        assert one_range is not None
        self.assertEqual(len(one_range), 2)
        self.assertEqual(encoded.enc_str_to_uint32(one_range), 0)

    def test_a_value_that_does_not_fit_returns_none(self) -> None:
        """The source returns ``false`` when ``cases_required + 1 > count``."""

        self.assertIsNone(encoded.uint32_to_enc_str(0x12345678, 8))
        self.assertIsNotNone(encoded.uint32_to_enc_str(0x1184, 2))
        self.assertIsNone(encoded.uint32_to_enc_str(0x1184, 1))

    def test_the_decoder_wraps_like_the_uint32_it_is(self) -> None:
        """The C++ accumulates in ``uint32_t``; a digit below the base wraps."""

        self.assertEqual(encoded.enc_str_to_uint32([encoded.TERM_FINAL]), 0xFFFFFF00)


class EncodedStringValidityTests(unittest.TestCase):
    """``IsValidEncStr`` (``ui_methods.cpp:2613-2629``) and the grammar it runs."""

    def test_every_encoding_the_encoder_produces_is_valid(self) -> None:
        """The encoder and the validator are two halves of one format."""

        for value in range(1, 0x200):
            with self.subTest(value=hex(value)):
                encoded_value = encoded.uint32_to_enc_str(value, 8)
                assert encoded_value is not None
                self.assertTrue(encoded.is_valid_enc_str(encoded_value))

    def test_a_single_word_and_its_terminator_is_valid(self) -> None:
        self.assertTrue(encoded.is_valid_enc_str([0x100, encoded.TERM_FINAL]))

    def test_several_words_are_valid(self) -> None:
        self.assertTrue(
            encoded.is_valid_enc_str([0x100, 0x100, encoded.TERM_FINAL])
        )

    def test_a_digit_below_the_base_is_rejected(self) -> None:
        """``EncStrValidateSingleWord`` refuses anything under ``WORD_VALUE_BASE``."""

        self.assertFalse(encoded.is_valid_enc_str([0x50, encoded.TERM_FINAL]))
        self.assertFalse(encoded.is_valid_enc_str([0xFF, encoded.TERM_FINAL]))

    def test_a_truncated_chain_is_rejected(self) -> None:
        """A digit that promises a continuation must be followed by a real digit."""

        self.assertFalse(encoded.is_valid_enc_str([0x8100, encoded.TERM_FINAL]))

    def test_a_literal_run_must_end_at_the_intermediate_terminator(self) -> None:
        """``EncStrValidateTerminatedLiteral`` returns true only on ``TERM_INTERMEDIATE``."""

        self.assertFalse(
            encoded.is_valid_enc_str([0x100, encoded.CONCAT_LITERAL, 0x41, 0])
        )
        self.assertTrue(
            encoded.is_valid_enc_str(
                [0x100, encoded.CONCAT_LITERAL, 0x41, encoded.TERM_INTERMEDIATE, 0]
            )
        )

    def test_the_validator_must_consume_exactly_to_the_terminator(self) -> None:
        """``IsValidEncStr`` requires ``data == term``, not merely "accepted".

        The grammar accepts a run of words and then the terminator, so a two-word array is
        valid. An **intermediate** terminator ends the structure early, and the validator
        then stops before ``term`` — which is exactly the case the final ``data == term``
        check exists to reject.
        """

        self.assertTrue(encoded.is_valid_enc_str([0x100, 0x100, 0]))

        self.assertFalse(
            encoded.is_valid_enc_str(
                [0x100, encoded.TERM_INTERMEDIATE, 0x100, encoded.TERM_FINAL]
            )
        )

    def test_the_terminator_bounds_what_is_judged(self) -> None:
        """``term`` comes from the first ``TERM_FINAL``, so only ``[0, term)`` is judged.

        ``IsValidEncStr`` scans for the terminator and validates up to it
        (`ui_methods.cpp:2618-2622`). Codepoints after it are outside the string, which is
        why the same three-codepoint prefix gives the same answer with or without trailing
        data — and why a bad *first* codepoint is still rejected.
        """

        self.assertTrue(encoded.is_valid_enc_str([0x100, 0x100, 0]))
        self.assertTrue(encoded.is_valid_enc_str([0x100, 0x100, 0, 0x50, 0x50]))
        self.assertFalse(encoded.is_valid_enc_str([0x50, 0x100, 0]))


if __name__ == "__main__":
    unittest.main()
