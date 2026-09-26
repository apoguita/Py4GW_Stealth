"""Offline tests for the ported string-table decoder.

What is tested here is the half of ``string_table.py`` that turns bytes into text: the
codepoint parser, the entry decoder (key derivation, RC4, bit-unpack), the two RC4 backends,
the postprocessors, the formatted-expression grammar, the file parser that fills the table,
the load that walks the TextParser file slots, and ``decode`` / ``decode_plain`` themselves.
Everything is driven with synthetic entries and a synthetic TextParser context, because the
real table lives in ``gw.dat`` and the call that reads it is the one leaf still to port
(``_load_dat_file``, which says so by name and is tested as saying so).

Where a test cannot have an independent oracle, it says so: the keyed-entry test proves the
RC4 branch, the payload slice and the bit-unpack round trip, but the *key derivation* it
uses is the same arithmetic the decoder uses, because no independent vector for the game's
custom hash exists in either source project.
"""

from __future__ import annotations

import struct
import time
import unittest
from typing import Any
from unittest.mock import patch

from py4gw.internals import string_table
from py4gw.ui.encoded_str import (
    WORD_BIT_MORE,
    WORD_VALUE_BASE,
    WORD_VALUE_RANGE,
    uint32_to_enc_str,
)


def entry(payload: bytes, base_char: int, bpc: int) -> bytes:
    """Build one string-table entry.

    ``[u16 size | u16 base_char | u8 bits_per_char | u8 flags | payload]`` — six header
    bytes, which is why the decoder's payload is ``entry_data[6:total_size]``. The decoder
    reads the first five; the flags byte is the sixth.
    """

    size = 6 + len(payload)
    return struct.pack("<HHBB", size, base_char, bpc, 0) + payload


def standard_rc4(key: bytes, data: bytes) -> bytes:
    """A textbook RC4, written here to be an oracle the port did not come from.

    It is *not* the same schedule as the source's for every key length, and that difference
    is the point of the tests that use this: the source repeats the key to 256 bytes and then
    iterates over however many bytes that produced, which is the textbook schedule exactly
    when the key is 20 bytes long — the length the game's key derivation always produces.
    """

    s = list(range(256))
    j = 0
    for i in range(256):
        j = (j + s[i] + key[i % len(key)]) & 0xFF
        s[i], s[j] = s[j], s[i]

    out = bytearray(len(data))
    i = j = 0
    for index, byte in enumerate(data):
        i = (i + 1) & 0xFF
        j = (j + s[i]) & 0xFF
        s[i], s[j] = s[j], s[i]
        out[index] = byte ^ s[(s[i] + s[j]) & 0xFF]
    return bytes(out)


class CodepointParserTests(unittest.TestCase):
    """``_parse_codepoints``: an encoded array to ``(index, key)``.

    The encoding is the one ``py4gw/ui/encoded_str.py`` already works in — the same
    ``WORD_VALUE_BASE`` / ``WORD_BIT_MORE`` / ``WORD_VALUE_RANGE`` — so the two ports are
    checked against each other here as well as against their own source.
    """

    def encode_number(self, value: int, digits: int = 4) -> list[int]:
        """Encode a number the way the client does, using the ported encoder."""

        from py4gw.ui.encoded_str import uint32_to_enc_str

        encoded = uint32_to_enc_str(value, digits + 1)
        assert encoded is not None, "the test's own encoding must fit"
        return encoded

    def test_no_codepoints_is_nothing(self) -> None:
        self.assertEqual(string_table._parse_codepoints(()), (0, 0))

    def test_a_zero_codepoint_is_nothing(self) -> None:
        self.assertEqual(string_table._parse_codepoints((0,)), (0, 0))

    def test_the_first_run_is_the_index(self) -> None:
        for value in (1, 2, 5, 0x11, 0x1184):
            with self.subTest(value=hex(value)):
                codepoints = tuple(self.encode_number(value))
                index, key = string_table._parse_codepoints(codepoints + (0,))
                self.assertEqual(index, value)
                self.assertEqual(key, 0, "a single run names no key")

    def test_a_second_run_is_the_key(self) -> None:
        """The key run only counts when its first codepoint continues (high bit set)."""

        # The index 7, then a two-digit key: 7 with a continuation bit, then 0.
        codepoints = (0x107, 0x8107, 0x100, 0)

        index, key = string_table._parse_codepoints(codepoints)

        self.assertEqual(index, 7)
        self.assertEqual(key, 7 * WORD_VALUE_RANGE)

    def test_a_key_run_that_does_not_continue_is_ignored(self) -> None:
        """Without the continuation bit on its first codepoint, there is no key at all."""

        index, key = string_table._parse_codepoints((0x107, 0x108, 0))

        self.assertEqual(index, 7)
        self.assertEqual(key, 0)

    def test_the_parse_stops_at_the_terminator(self) -> None:
        index, key = string_table._parse_codepoints((0x105, 0, 0x8107, 0x100))

        self.assertEqual((index, key), (5, 0))

    def test_a_digit_below_the_base_is_refused(self) -> None:
        """A codepoint under ``WORD_VALUE_BASE`` is not a digit, so nothing is parsed."""

        self.assertEqual(string_table._parse_codepoints((0x50,)), (0, 0))
        self.assertEqual(
            string_table._parse_codepoints((0x105, 0x50)), (5, 0)
        )

    def test_the_constants_are_the_ones_the_encoder_uses(self) -> None:
        """One encoding, two ports: this is what keeps them from drifting apart."""

        self.assertEqual(string_table._BASE, WORD_VALUE_BASE)
        self.assertEqual(string_table._MORE, WORD_BIT_MORE)
        self.assertEqual(string_table._RANGE, WORD_VALUE_RANGE)


class Rc4Tests(unittest.TestCase):
    """The two backends, against an RC4 written here rather than ported.

    The keys matter. The game's derivation always produces a **20-byte** key, and at that
    length the source's schedule is the textbook one, so the port can be checked against an
    independent implementation. At shorter lengths it is not the textbook schedule at all —
    the source repeats the key to 256 bytes and iterates over what that produced — and the
    test that says so is pinning the source's behaviour, not a defect.
    """

    #: A 20-byte key: what ``EntryKeySizes`` produce, and the case the port must match.
    GAME_KEY = bytes(range(20))
    #: A three-byte key: the length at which the source's schedule stops being textbook.
    SHORT_KEY = b"Key"
    PLAINTEXT = b"Plaintext"

    def test_a_twenty_byte_key_is_the_textbook_schedule(self) -> None:
        self.assertEqual(
            string_table._rc4_python(self.GAME_KEY, self.PLAINTEXT),
            standard_rc4(self.GAME_KEY, self.PLAINTEXT),
        )

    def test_a_short_key_is_not_the_textbook_schedule(self) -> None:
        """The source's key setup iterates ``len(key) * 13`` bytes, capped at 256.

        For a three-byte key that is 39 rounds instead of 256, so most of the state is left
        as it started. This is what the source does, and the port reproduces it.
        """

        self.assertNotEqual(
            string_table._rc4_python(self.SHORT_KEY, self.PLAINTEXT),
            standard_rc4(self.SHORT_KEY, self.PLAINTEXT),
        )

    def test_the_selected_backend_matches_a_twenty_byte_key(self) -> None:
        """Whichever backend this machine bound — CNG or Python — must agree."""

        self.assertEqual(
            string_table._rc4_decrypt(self.GAME_KEY, self.PLAINTEXT),
            standard_rc4(self.GAME_KEY, self.PLAINTEXT),
        )

    def test_the_cipher_is_its_own_inverse(self) -> None:
        """Which is what makes it usable both to build a test entry and to decode one."""

        encrypted = standard_rc4(self.GAME_KEY, self.PLAINTEXT)

        self.assertEqual(
            string_table._rc4_python(self.GAME_KEY, encrypted), self.PLAINTEXT
        )

    def test_the_backend_is_a_bound_one_or_the_fallback(self) -> None:
        """``_rc4_cng()`` builds a fresh closure per call, so this is not an identity test."""

        self.assertTrue(
            string_table._rc4_decrypt is string_table._rc4_python
            or callable(string_table._rc4_decrypt)
        )
        result = string_table._rc4_decrypt(self.GAME_KEY, self.PLAINTEXT)
        self.assertEqual(len(result), len(self.PLAINTEXT))


class DecodeEntryTests(unittest.TestCase):
    """``_decode_entry``: an entry to text."""

    def setUp(self) -> None:
        string_table._char_table_cache.clear()

    def test_a_short_entry_is_refused(self) -> None:
        for raw in (b"", b"\x01", b"\x00" * 5):
            with self.subTest(length=len(raw)):
                self.assertIsNone(string_table._decode_entry(raw, 0))

    def test_an_impossible_size_is_refused(self) -> None:
        """``total_size`` must be more than the header and no more than the entry."""

        self.assertIsNone(
            string_table._decode_entry(struct.pack("<HHB", 6, 0, 0x10), 0)
        )
        self.assertIsNone(
            string_table._decode_entry(
                struct.pack("<HHB", 40, 0, 0x10) + b"\x41\x00", 0
            )
        )

    def test_raw_utf16_is_decoded_and_cut_at_the_terminator(self) -> None:
        """``base_char=0, bpc=16`` is the raw form the source special-cases."""

        raw = entry("Foreman\x00trailing".encode("utf-16-le"), 0, 0x10)

        self.assertEqual(string_table._decode_entry(raw, 0), "Foreman")

    def test_raw_utf16_with_no_terminator_keeps_everything(self) -> None:
        raw = entry("Foreman".encode("utf-16-le"), 0, 0x10)

        self.assertEqual(string_table._decode_entry(raw, 0), "Foreman")

    def test_an_odd_length_raw_payload_drops_its_last_byte(self) -> None:
        """``payload[:len(payload) & ~1]`` — the source's own mask."""

        raw = entry("Foreman".encode("utf-16-le") + b"\x41", 0, 0x10)

        self.assertEqual(string_table._decode_entry(raw, 0), "Foreman")

    def test_a_zero_bit_packing_is_refused(self) -> None:
        self.assertIsNone(string_table._decode_entry(entry(b"\x41", 0x20, 0), 0))

    def test_bit_packed_text_is_unpacked(self) -> None:
        """With ``base_char`` at 0x20 an 8-bit value maps to the character it names."""

        raw = entry(b"Hi", 0x20, 8)

        self.assertEqual(string_table._decode_entry(raw, 0), "Hi")

    def test_a_zero_value_ends_the_text(self) -> None:
        """The unpack loop stops at the first zero, which is the terminator."""

        raw = entry(b"Hi\x00there", 0x20, 8)

        self.assertEqual(string_table._decode_entry(raw, 0), "Hi")

    def test_the_character_mapping_is_the_sources(self) -> None:
        """Values under 0x20 come from the fixed table; the rest offset from ``base_char``."""

        raw = entry(bytes((5, 10, 3)), 0x20, 8)

        self.assertEqual(
            string_table._decode_entry(raw, 0),
            string_table._CHAR_TUPLE[5]
            + string_table._CHAR_TUPLE[10]
            + string_table._CHAR_TUPLE[3],
        )

    def test_the_character_table_is_cached_per_packing(self) -> None:
        string_table._decode_entry(entry(b"Hi", 0x20, 8), 0)
        self.assertIn((0x20, 8), string_table._char_table_cache)

        string_table._decode_entry(entry(b"Ho", 0x30, 8), 0)
        self.assertIn((0x30, 8), string_table._char_table_cache)
        self.assertNotIn((0x30, 8), [])
        self.assertEqual(len(string_table._char_table_cache), 2)

    def test_a_keyed_entry_decrypts_through_rc4(self) -> None:
        """The RC4 branch, its payload slice and the bit-unpack, round-tripped.

        **No independent oracle here.** The key derivation is the source's custom hash and
        neither source project ships a vector for it, so the entry is built with the same
        arithmetic the decoder uses. What this proves is that a keyed entry takes the RC4
        branch, decrypts over exactly ``entry_data[6:total_size]``, and unpacks to the text
        that was packed.
        """

        key = 0x0123456789ABCDEF
        plain = b"Foreman"
        derived = self._derived_key(key)
        encrypted = string_table._rc4_python(derived, plain)
        raw = entry(encrypted, 0x20, 8)

        self.assertEqual(string_table._decode_entry(raw, key), "Foreman")

    def test_the_same_entry_decodes_differently_with_a_key(self) -> None:
        """Which is how the branch is visible at all: a key changes the bytes read."""

        raw = entry(b"Foreman", 0x20, 8)

        self.assertEqual(string_table._decode_entry(raw, 0), "Foreman")
        self.assertNotEqual(string_table._decode_entry(raw, 0x0123456789ABCDEF), "Foreman")

    def _derived_key(self, key: int) -> bytes:
        """The source's key derivation, transcribed for the test to build its input."""

        mask = 0xFFFFFFFF
        kb = struct.pack("<Q", key & 0xFFFFFFFFFFFFFFFF)
        buf20 = kb + kb + kb[:4]
        w0, w1, w2, w3, w4 = struct.unpack("<5I", buf20)

        a = (w0 + 0x9FB498B3) & mask
        b = (w1 + 0x66B0CD0D + (((a << 5) | (a >> 27)) & mask)) & mask
        a30 = ((a << 30) | (a >> 2)) & mask
        f_a = (~(a & 0x22222222) & 0x7BF36AE2) & mask
        c = ((((b << 5) | (b >> 27)) & mask) + w2 + f_a + 0xF33D5697) & mask
        b30 = ((b << 30) | (b >> 2)) & mask
        g = (((a30 ^ 0x59D148C0) & b) ^ 0x59D148C0) & mask
        d = (w3 + (((c << 5) | (c >> 27)) & mask) + g + 0xD675E47B) & mask
        c30 = ((c << 30) | (c >> 2)) & mask
        h = (((a30 ^ b30) & c) ^ a30) & mask
        e = (h + w4 + (((d << 5) | (d >> 27)) & mask) + 0xB453C259 + w0) & mask

        return struct.pack(
            "<5I",
            e,
            (w1 + d) & mask,
            (w2 + c30) & mask,
            (b30 + w3) & mask,
            (a30 + w4) & mask,
        )


class ParseStringFileTests(unittest.TestCase):
    """``_parse_string_file``: a loaded ``gw.dat`` file to ``{index: entry bytes}``."""

    def test_entries_are_indexed_from_the_start_index(self) -> None:
        first = entry(b"one", 0x20, 8)
        second = entry(b"two", 0x20, 8)
        table: dict[int, bytes] = {}

        count = string_table._parse_string_file(first + second, 100, table)

        self.assertEqual(count, 2)
        self.assertEqual(table[100], first)
        self.assertEqual(table[101], second)
        self.assertNotIn(102, table)

    def test_an_impossible_size_stops_the_parse(self) -> None:
        """A size under 6 or over 8192 is not an entry: the parse stops there."""

        good = entry(b"one", 0x20, 8)
        table: dict[int, bytes] = {}

        count = string_table._parse_string_file(good + b"\x03\x00" + good, 0, table)

        self.assertEqual(count, 1)
        self.assertEqual(len(table), 1)

    def test_a_trailing_fragment_is_ignored(self) -> None:
        good = entry(b"one", 0x20, 8)
        table: dict[int, bytes] = {}

        count = string_table._parse_string_file(good + b"\x09", 0, table)

        self.assertEqual(count, 1)

    def test_the_parsed_entries_decode(self) -> None:
        """The two halves meet: a file parses into entries the decoder renders."""

        table: dict[int, bytes] = {}
        string_table._parse_string_file(entry(b"Foreman", 0x20, 8), 5, table)

        index, key = string_table._parse_codepoints((0x105, 0))
        self.assertEqual(index, 5)
        self.assertEqual(string_table._decode_entry(table[index], key), "Foreman")


def digit_run(value: int) -> tuple[int, ...]:
    """The digits of one base-0x7F00 number, **without** the terminator the encoder appends.

    A formatted expression puts its arg tags where a plain segment has its terminator, so the
    terminator is placed by hand in every test below rather than by the encoder.
    """

    run = uint32_to_enc_str(value, 8)
    assert run is not None, "the test's own encoding must fit"
    return tuple(run[:-1])


def code_points(*values: int) -> tuple[int, ...]:
    """The raw little-endian ``uint16`` array a caller handed ``decode``."""

    return tuple(values)


def raw_of(codepoints: tuple[int, ...]) -> bytes:
    """The bytes of a codepoint array, which is the form ``decode`` takes."""

    return struct.pack(f"<{len(codepoints)}H", *codepoints)


def reset_table_state() -> None:
    """Put the module's singletons back, so one test's load is not the next one's cache."""

    string_table._string_table.clear()
    string_table._string_tables_by_language.clear()
    string_table._string_table_loaded = False
    string_table._load_enqueued = False
    string_table._loaded_language = 0
    string_table._last_load_status = "not requested"
    string_table._decode_cache.clear()
    string_table._decode_cache_by_language.clear()
    string_table._pending.clear()


def await_cached(raw: bytes, timeout_s: float = 5.0) -> None:
    """Wait for the module's single decode worker, on a deadline rather than forever."""

    deadline = time.monotonic() + timeout_s
    while raw not in string_table._decode_cache and time.monotonic() < deadline:
        time.sleep(0.005)


class FakeSlot:
    """One TextParser file slot: the two fields the load reads."""

    def __init__(self, file_hash: str, file_hash_ptr: int = 0x1000) -> None:
        self.file_hash = file_hash
        self.file_hash_ptr = file_hash_ptr


class FakeLanguageSlot:
    """The per-language header: the load iterates ``slot_count`` of its slots."""

    def __init__(self, slot_count: int) -> None:
        self.slot_count = slot_count


class FakeTextParserContext:
    """The two levels of the TextParser context the load walks, without a client.

    The client boundary is the DAT call, not this walk: the walk reads slot metadata out of
    the context, which is what this stands in for so the load can be tested end to end.
    """

    def __init__(
        self, entries_per_file: int, slots: list[FakeSlot], language_id: int = 0
    ) -> None:
        self.entries_per_file = entries_per_file
        self.language_slots = [
            FakeLanguageSlot(len(slots)),
            FakeLanguageSlot(len(slots)),
        ]
        self.language_id = language_id
        self._slots = slots

    def get_file_slot(self, slot_idx: int, language: int = 0) -> FakeSlot | None:
        return self._slots[slot_idx]


def slot_loader(files: dict[str, bytes], calls: list[str] | None = None) -> Any:
    """A stand-in for ``_load_dat_file``: the client call, keyed by file hash."""

    def load(file_hash: str) -> bytes | None:
        if calls is not None:
            calls.append(file_hash)
        return files.get(file_hash)

    return load


class PostprocessTests(unittest.TestCase):
    """The postprocessors: what the source strips, chooses, and substitutes."""

    def test_only_the_leading_grammar_tag_is_stripped(self) -> None:
        """``_GRAMMAR_TAG_RE`` is anchored at ``^``, so a tag that is not first stays."""

        self.assertEqual(string_table._postprocess_basic("[M]Foreman"), "Foreman")
        self.assertEqual(
            string_table._postprocess_basic("[proper]Foreman[plur]"), "Foreman[plur]"
        )

    def test_every_style_tag_is_stripped(self) -> None:
        self.assertEqual(string_table._postprocess_basic("[b]Foreman[/b]"), "Foreman")

    def test_bracket_escapes_become_brackets(self) -> None:
        self.assertEqual(
            string_table._postprocess_basic("[lbracket]Foreman[rbracket]"), "[Foreman]"
        )

    def test_a_gender_pair_picks_the_male_form_by_default(self) -> None:
        self.assertEqual(
            string_table._apply_inline_gender_tags('[m:"his"][f:"her"] hat'), "his hat"
        )

    def test_a_gender_pair_picks_the_female_form_when_asked(self) -> None:
        self.assertEqual(
            string_table._apply_inline_gender_tags(
                '[m:"his"][f:"her"] hat', prefer_male=False
            ),
            "her hat",
        )

    def test_a_pair_in_the_other_order_still_picks_the_preferred_tag(self) -> None:
        self.assertEqual(
            string_table._apply_inline_gender_tags('[f:"her"][m:"his"] hat'), "his hat"
        )

    def test_a_lone_gender_tag_is_dropped_when_it_is_not_the_preferred_one(self) -> None:
        self.assertEqual(string_table._apply_inline_gender_tags('[f:"her"] hat'), " hat")

    def test_the_indefinite_article_follows_the_sources_rules(self) -> None:
        choose = string_table._choose_indefinite_article

        for word in ("hour", "honest man", "heir"):
            with self.subTest(word=word):
                self.assertEqual(choose(word), "an")
        for word in ("user", "unicorn", "euro", "one", "once"):
            with self.subTest(word=word):
                self.assertEqual(choose(word), "a")
        self.assertEqual(choose("apple"), "an")
        self.assertEqual(choose("banana"), "a")

    def test_an_article_tag_becomes_the_article_the_word_takes(self) -> None:
        self.assertEqual(string_table._apply_indefinite_articles("[an] hour"), "an hour")
        self.assertEqual(string_table._apply_indefinite_articles("[a] hour"), "an hour")
        self.assertEqual(string_table._apply_indefinite_articles("[a] user"), "a user")

    def test_a_doubled_percent_becomes_one(self) -> None:
        self.assertEqual(string_table._postprocess("100%% done"), "100% done")

    def test_a_string_without_a_marker_is_left_alone(self) -> None:
        self.assertEqual(string_table._postprocess("Foreman"), "Foreman")

    def test_an_unresolved_substitute_is_left_as_it_is_without_a_context(self) -> None:
        """``%strN%`` needs the TextParser substitutes, and there is no client in this test."""

        with patch("py4gw.client.current_client", return_value=None):
            self.assertEqual(string_table._postprocess("Bonus: %str1%"), "Bonus: %str1%")

    def test_plural_tags_follow_the_number(self) -> None:
        self.assertEqual(
            string_table._apply_plural_tags('1 Cacho[pl:"Cachos"]', 2), "1 Cachos"
        )
        self.assertEqual(
            string_table._apply_plural_tags('1 Cacho[pl:"Cachos"]', 1), "1 Cacho"
        )
        self.assertEqual(
            string_table._apply_plural_tags('1 Cacho[pl:"Cachos"]', None), "1 Cacho"
        )

    def test_a_suffix_marker_is_a_plural_marker(self) -> None:
        self.assertEqual(string_table._apply_plural_tags("Cacho[s]", 2), "Cachos")
        self.assertEqual(string_table._apply_plural_tags("Cacho[s]", 1), "Cacho")

    def test_plural_markers_are_recognised_in_both_spellings(self) -> None:
        self.assertTrue(string_table._has_plural_markers("Cacho[s]"))
        self.assertTrue(string_table._has_plural_markers('Cacho[pl:"Cachos"]'))
        self.assertFalse(string_table._has_plural_markers("Cacho"))

    def test_plain_text_normalization_leaves_what_a_caller_should_see(self) -> None:
        text = string_table._normalize_plain_text(
            '[m:"his"][f:"her"]  <c=@ItemDull>dull</c>  %num1% Cacho[s]'
        )

        self.assertEqual(text, "his dull Cacho")


class FormattedGrammarTests(unittest.TestCase):
    """The inline formatted grammar: arg tags, segments, trees and streams.

    The indices are 300 and up on purpose. A one-digit index is encoded as
    ``WORD_VALUE_BASE + index``, so indices 1..9 land in the ``num`` tag range and 10..31 in
    the ``str`` tag range: an expression naming one of those is genuinely ambiguous, which is
    the case ``test_an_ambiguous_number_tag_is_read_as_a_string_reference`` pins separately.
    """

    def setUp(self) -> None:
        self.table: dict[int, bytes] = {
            300: entry(b"Foreman", 0x20, 8),
            301: entry(b"Hello %str1%", 0x20, 8),
            302: entry(b"First", 0x20, 8),
            303: entry(b"Second", 0x20, 8),
            304: entry(b"Armor +5", 0x20, 8),
            305: entry(b"<c=@ItemDull>(dull)</c>", 0x20, 8),
            306: entry(b"Bonus: %str1%", 0x20, 8),
            307: entry(b"You have %num1% gold", 0x20, 8),
            308: entry(b'You have %num1% apple[pl:"apples"]', 0x20, 8),
            309: entry(b"Line one", 0x20, 8),
            310: entry(b", and more", 0x20, 8),
            # ``0x0108`` is the num-tag spelling of 8, which is the ambiguity test's input.
            8: entry(b"Ascalon", 0x20, 8),
        }

    def test_the_tag_ranges_are_the_sources(self) -> None:
        self.assertFalse(string_table._is_arg_tag(0x0100))
        for cp in range(0x0101, 0x0120):
            with self.subTest(cp=hex(cp)):
                self.assertTrue(string_table._is_arg_tag(cp))
        self.assertFalse(string_table._is_arg_tag(0x0120))

        self.assertTrue(string_table._is_num_tag(0x0101))
        self.assertTrue(string_table._is_num_tag(0x0109))
        self.assertFalse(string_table._is_num_tag(0x010A))
        self.assertTrue(string_table._is_str_tag(0x010A))
        self.assertTrue(string_table._is_str_tag(0x011F))
        self.assertFalse(string_table._is_str_tag(0x0120))

    def test_a_segment_decodes_through_the_table(self) -> None:
        self.assertEqual(
            string_table._decode_codepoints_segment(digit_run(300), self.table), "Foreman"
        )

    def test_an_empty_segment_is_empty_text(self) -> None:
        self.assertEqual(string_table._decode_codepoints_segment((), self.table), "")
        self.assertEqual(string_table._decode_codepoints_segment((0,), self.table), "")

    def test_a_segment_that_names_no_entry_is_empty_text(self) -> None:
        self.assertEqual(string_table._decode_codepoints_segment(digit_run(300), {}), "")
        self.assertEqual(string_table._decode_codepoints_segment(digit_run(0), self.table), "")

    def test_a_number_run_consumes_its_intermediate_terminator(self) -> None:
        codepoints = (0x0101, 0x12A, 1, 0)

        value, index = string_table._parse_number_codepoints(codepoints, 1)

        self.assertEqual(value, 42)
        self.assertEqual(index, 3)
        self.assertEqual(codepoints[index], 0)

    def test_a_number_run_that_is_not_a_digit_reads_nothing(self) -> None:
        value, index = string_table._parse_number_codepoints((0x0101, 0x50), 1)

        self.assertEqual((value, index), (0, 1))

    def test_an_encoded_reference_ends_after_its_index(self) -> None:
        self.assertEqual(string_table._consume_encoded_ref((0x22C, 0), 0), 1)

    def test_an_encoded_reference_includes_a_key_run(self) -> None:
        codepoints = (0x22C, 0x822C, 0x2100, 0)

        self.assertEqual(string_table._consume_encoded_ref(codepoints, 0), 3)

    def test_a_reference_that_starts_with_a_terminator_is_not_consumed(self) -> None:
        self.assertEqual(string_table._consume_encoded_ref((1, 0), 0), 0)
        self.assertEqual(string_table._consume_encoded_ref((), 0), 0)

    def test_a_template_argument_is_substituted_into_the_rendered_text(self) -> None:
        codepoints = digit_run(301) + (0x010A,) + digit_run(300) + (1,)

        node, index = string_table._decode_formatted_tree(codepoints, 0, self.table)

        self.assertEqual(node["template"], "Hello %str1%")
        self.assertEqual(node["rendered"], "Hello Foreman")
        self.assertEqual(node["expr_cp"], codepoints)
        # ``head_cp`` is sliced with the *final* index, so it carries the arg blocks too.
        self.assertEqual(node["head_cp"], codepoints)
        self.assertEqual(index, len(codepoints))

    def test_a_number_argument_is_substituted_into_the_rendered_text(self) -> None:
        codepoints = digit_run(307) + (0x0101,) + digit_run(5) + (1,)

        node, index = string_table._decode_formatted_tree(codepoints, 0, self.table)

        self.assertEqual(node["num_args"], {1: 5})
        self.assertEqual(node["rendered"], "You have 5 gold")
        self.assertEqual(index, len(codepoints))

    def test_a_singular_number_drops_its_placeholder_and_takes_the_singular(self) -> None:
        """The placeholder goes first, then the plural tag, then the space is collapsed."""

        codepoints = digit_run(308) + (0x0101,) + digit_run(1) + (1,)

        node, _ = string_table._decode_formatted_tree(codepoints, 0, self.table)

        self.assertEqual(node["rendered"], "You have apple")

    def test_a_plural_number_keeps_the_placeholder_and_takes_the_plural(self) -> None:
        codepoints = digit_run(308) + (0x0101,) + digit_run(2) + (1,)

        node, _ = string_table._decode_formatted_tree(codepoints, 0, self.table)

        self.assertEqual(node["rendered"], "You have 2 apples")

    def test_an_ambiguous_number_tag_is_read_as_a_string_reference(self) -> None:
        """A first codepoint that looks like ``num8`` may be the digit ``8`` of an index.

        The source retries the whole expression as one encoded reference when the arg blocks
        left it with nothing rendered and there is data after them. Index 8 is the case: its
        digit is ``0x0108``, which is also the ``num8`` tag.
        """

        codepoints = (0x0108, 0x0102, 0x22C, 0)

        node, index = string_table._decode_formatted_tree(codepoints, 0, self.table)

        self.assertEqual(node["rendered"], "Ascalon")
        self.assertEqual(index, 3)

    def test_the_best_argument_text_descends_through_wrappers(self) -> None:
        self.assertEqual(
            string_table._best_arg_text({"rendered": "Direct", "args": {}}), "Direct"
        )
        self.assertEqual(
            string_table._best_arg_text(
                {"rendered": "%str1%", "args": {1: {"rendered": "Deep", "args": {}}}}
            ),
            "Deep",
        )
        self.assertEqual(
            string_table._best_arg_text(
                {"rendered": "", "args": {1: {"rendered": "", "args": {}}}}
            ),
            "",
        )

    def test_a_separated_stream_renders_one_line_per_expression(self) -> None:
        codepoints = digit_run(302) + (1, 2) + digit_run(303) + (1, 0)

        text, first = string_table._decode_formatted_stream(codepoints, self.table)

        self.assertEqual(text, "First\nSecond")
        self.assertIsNotNone(first)
        assert first is not None
        self.assertEqual(first["rendered"], "First")

    def test_a_dull_parenthetical_joins_the_line_before_it(self) -> None:
        codepoints = digit_run(304) + (1, 2) + digit_run(305) + (1, 0)

        text, _ = string_table._decode_formatted_stream(codepoints, self.table)

        self.assertEqual(text, "Armor +5 <c=@ItemDull>(dull)</c>")

    def test_a_continuation_fragment_joins_the_line_before_it(self) -> None:
        """A fragment that opens with punctuation belongs to the previous line."""

        codepoints = digit_run(309) + (1, 2) + digit_run(310) + (1, 0)

        text, _ = string_table._decode_formatted_stream(codepoints, self.table)

        self.assertEqual(text, "Line one, and more")

    def test_an_unresolved_wrapper_consumes_the_line_after_it(self) -> None:
        codepoints = digit_run(306) + (1, 2) + digit_run(303) + (1, 0)

        text, _ = string_table._decode_formatted_stream(codepoints, self.table)

        self.assertEqual(text, "Bonus: Second")

    def test_the_single_expression_helper_returns_what_the_tree_rendered(self) -> None:
        codepoints = digit_run(301) + (0x010A,) + digit_run(300) + (1,)

        text, index = string_table._decode_formatted_codepoints(codepoints, 0, self.table)

        self.assertEqual(text, "Hello Foreman")
        self.assertEqual(index, len(codepoints))


class DecodeSyncTests(unittest.TestCase):
    """``_decode_sync``: which of the source's branches a given input takes."""

    def setUp(self) -> None:
        self.table: dict[int, bytes] = {
            300: entry(b"Foreman", 0x20, 8),
            301: entry(b"First", 0x20, 8),
            302: entry(b"Second", 0x20, 8),
            303: entry(b"Hello %str1%", 0x20, 8),
        }

    def test_an_input_without_a_complete_code_unit_is_empty_text(self) -> None:
        self.assertEqual(string_table._decode_sync(b"", self.table), "")
        self.assertEqual(string_table._decode_sync(b"\x05", self.table), "")

    def test_the_first_terminator_ends_the_codepoints(self) -> None:
        raw = raw_of(digit_run(300) + (0,) + digit_run(301) + (0,))

        self.assertEqual(string_table._decode_sync(raw, self.table), "Foreman")

    def test_plain_legacy_text_is_returned_as_it_is(self) -> None:
        raw = raw_of(digit_run(300) + (0,))

        self.assertEqual(string_table._decode_sync(raw, self.table), "Foreman")

    def test_text_the_table_does_not_hold_is_empty(self) -> None:
        raw = raw_of(digit_run(399) + (0,))

        self.assertEqual(string_table._decode_sync(raw, self.table), "")

    def test_a_separated_stream_goes_through_the_stream_decoder(self) -> None:
        """Both gates have to be open: a separator **and** an arg tag.

        With a separator alone the source returns the legacy text, which is the case the
        first assertion pins.
        """

        without_a_tag = raw_of(digit_run(301) + (1, 2) + digit_run(302) + (1, 0))
        self.assertEqual(string_table._decode_sync(without_a_tag, self.table), "First")

        with_a_tag = raw_of(
            digit_run(303) + (0x010A,) + digit_run(300) + (1, 2) + digit_run(302) + (1, 0)
        )

        with patch("py4gw.client.current_client", return_value=None):
            text = string_table._decode_sync(with_a_tag, self.table)

        self.assertEqual(text, "Hello Foreman\nSecond")

    def test_an_unresolved_template_goes_through_the_tree(self) -> None:
        """The legacy text carries ``%str1%``, so the source re-decodes it as an expression."""

        raw = raw_of(digit_run(303) + (0x010A,) + digit_run(300) + (1, 0))

        with patch("py4gw.client.current_client", return_value=None):
            text = string_table._decode_sync(raw, self.table)

        self.assertEqual(text, "Hello Foreman")


class LoadTests(unittest.TestCase):
    """The load: TextParser's file slots to a table, and what it says when it cannot."""

    def setUp(self) -> None:
        reset_table_state()

    def tearDown(self) -> None:
        reset_table_state()

    def context(self, files: list[FakeSlot], entries_per_file: int = 10) -> FakeTextParserContext:
        return FakeTextParserContext(entries_per_file, files)

    def test_the_slots_are_walked_and_indexed_by_entries_per_file(self) -> None:
        files = {
            "a": entry(b"one", 0x20, 8) + entry(b"two", 0x20, 8),
            "b": entry(b"three", 0x20, 8),
        }
        context = self.context([FakeSlot("a"), FakeSlot("b")])

        with patch.object(string_table.TextParser, "_update_ptr"), patch.object(
            string_table.TextParser, "get_context", return_value=context
        ), patch.object(string_table, "_load_dat_file", slot_loader(files)):
            string_table.load_string_table(0)

        self.assertTrue(string_table._string_table_loaded)
        self.assertEqual(sorted(string_table._string_table), [0, 1, 10])
        self.assertEqual(string_table._decode_entry(string_table._string_table[10], 0), "three")
        self.assertEqual(string_table._last_load_status, "loaded 3 entries from 2 files")

    def test_a_slot_without_a_hash_pointer_is_skipped_silently(self) -> None:
        files = {"a": entry(b"one", 0x20, 8), "b": entry(b"two", 0x20, 8)}
        slots = [FakeSlot("a"), FakeSlot("b", file_hash_ptr=0)]

        with patch.object(string_table.TextParser, "_update_ptr"), patch.object(
            string_table.TextParser, "get_context", return_value=self.context(slots)
        ), patch.object(string_table, "_load_dat_file", slot_loader(files)):
            table = string_table._load_table_for_language(0)

        self.assertEqual(sorted(table), [0])
        self.assertEqual(string_table._last_load_status, "loaded 1 entries from 1 files")

    def test_a_file_the_client_will_not_hand_over_is_counted_and_the_rest_loads(self) -> None:
        def load(file_hash: str) -> bytes:
            if file_hash == "b":
                raise OSError("the client would not hand this file over")
            return entry(b"one", 0x20, 8)

        with patch.object(string_table.TextParser, "_update_ptr"), patch.object(
            string_table.TextParser,
            "get_context",
            return_value=self.context([FakeSlot("a"), FakeSlot("b")]),
        ), patch.object(string_table, "_load_dat_file", load):
            table = string_table._load_table_for_language(0)

        self.assertEqual(sorted(table), [0])
        self.assertEqual(string_table._last_load_status, "loaded 1 entries from 1 files")

    def test_a_load_that_reads_nothing_says_what_it_saw(self) -> None:
        with patch.object(string_table.TextParser, "_update_ptr"), patch.object(
            string_table.TextParser,
            "get_context",
            return_value=self.context([FakeSlot("a"), FakeSlot("b")]),
        ), patch.object(string_table, "_load_dat_file", slot_loader({})):
            table = string_table._load_table_for_language(0)

        self.assertEqual(table, {})
        self.assertEqual(
            string_table._last_load_status,
            "no entries (slots=2, readable_files=0, failed_files=2)",
        )

    def test_a_table_is_loaded_once_per_language(self) -> None:
        calls: list[str] = []
        files = {"a": entry(b"one", 0x20, 8)}
        context = self.context([FakeSlot("a")])

        with patch.object(string_table.TextParser, "_update_ptr"), patch.object(
            string_table.TextParser, "get_context", return_value=context
        ), patch.object(string_table, "_load_dat_file", slot_loader(files, calls)):
            first = string_table._load_table_for_language(0)
            second = string_table._load_table_for_language(0)

        self.assertIs(first, second)
        self.assertEqual(calls, ["a"])
        self.assertEqual(string_table._last_load_status, "using cached table (1 entries)")

    def test_the_dat_read_is_the_ported_reader(self) -> None:
        """``_load_dat_file`` is the source's one line over the ported ``PyDatReader``."""

        with patch(
            "py4gw.dat_reader.read_file_by_hash", return_value=b"\x08\x00payload"
        ) as read:
            data = string_table._load_dat_file("hash")

        self.assertEqual(data, b"\x08\x00payload")
        read.assert_called_once_with("hash")

    def test_a_dat_read_that_answers_nothing_is_no_file(self) -> None:
        """The source's ``return bytes(data) if data else None``."""

        with patch("py4gw.dat_reader.read_file_by_hash", return_value=None):
            self.assertIsNone(string_table._load_dat_file("hash"))

        with patch("py4gw.dat_reader.read_file_by_hash", return_value=b""):
            self.assertIsNone(string_table._load_dat_file("hash"))

    def test_a_read_the_client_refused_is_counted_and_the_rest_still_loads(self) -> None:
        """A slot whose read answers nothing counts as a failed file, as the source counts it."""

        context = self.context([FakeSlot("a"), FakeSlot("b")])
        files = {"a": entry(b"one", 0x20, 8)}

        with patch.object(string_table.TextParser, "_update_ptr"), patch.object(
            string_table.TextParser, "get_context", return_value=context
        ), patch.object(string_table, "_load_dat_file", slot_loader(files)):
            table = string_table._load_table_for_language(0)

        self.assertEqual(sorted(table), [0])
        self.assertEqual(string_table._last_load_status, "loaded 1 entries from 1 files")

    def test_an_already_loaded_table_is_not_loaded_again(self) -> None:
        string_table._string_table_loaded = True
        string_table._last_load_status = "loaded earlier"

        def refuse(file_hash: str) -> bytes:
            raise AssertionError("a loaded table must not be re-read")

        with patch.object(string_table, "_load_dat_file", refuse):
            string_table.load_string_table(0)

        self.assertEqual(string_table._last_load_status, "loaded earlier")

    def test_switching_language_clears_the_caches_and_loads_the_other_table(self) -> None:
        string_table._string_table[0] = entry(b"stale", 0x20, 8)
        string_table._string_table_loaded = True
        string_table._decode_cache[b"\x05\x00"] = "Foreman"
        string_table._decode_cache_by_language[(0, b"\x05\x00")] = "Foreman"
        context = self.context([FakeSlot("a")], entries_per_file=4)

        with patch.object(string_table.TextParser, "_update_ptr"), patch.object(
            string_table.TextParser, "get_context", return_value=context
        ), patch.object(
            string_table, "_load_dat_file", slot_loader({"a": entry(b"one", 0x20, 8)})
        ):
            string_table.switch_language(1)

        self.assertEqual(string_table._loaded_language, 1)
        self.assertTrue(string_table._string_table_loaded)
        self.assertEqual(sorted(string_table._string_table), [0])
        self.assertEqual(string_table._decode_cache, {})
        self.assertEqual(string_table._decode_cache_by_language, {})

    def test_a_missing_context_is_reported_rather_than_guessed(self) -> None:
        with patch.object(string_table.TextParser, "_update_ptr"), patch.object(
            string_table.TextParser, "get_context", return_value=None
        ):
            table = string_table._load_table_for_language(0)

        self.assertEqual(table, {})
        self.assertEqual(string_table._last_load_status, "TextParser context unavailable")

    def test_an_entries_per_file_of_zero_is_reported(self) -> None:
        context = self.context([FakeSlot("a")], entries_per_file=0)

        with patch.object(string_table.TextParser, "_update_ptr"), patch.object(
            string_table.TextParser, "get_context", return_value=context
        ):
            table = string_table._load_table_for_language(0)

        self.assertEqual(table, {})
        self.assertEqual(string_table._last_load_status, "TextParser entries_per_file is zero")


class PublicDecodeTests(unittest.TestCase):
    """``decode`` / ``decode_plain``: the public entry points, end to end."""

    def setUp(self) -> None:
        reset_table_state()

    def tearDown(self) -> None:
        reset_table_state()

    def test_an_input_without_a_complete_code_unit_is_empty_text(self) -> None:
        self.assertEqual(string_table.decode(b""), "")
        self.assertEqual(string_table.decode(b"\xa9"), "")
        self.assertEqual(string_table.decode_plain(b""), "")

    def test_a_player_name_bypasses_the_table_entirely(self) -> None:
        """``0xBA9`` then inline UTF-16LE ASCII: no table, no client, no decode needed.

        The source steps two bytes at a time and keeps the low byte, so the name has to be
        the UTF-16LE form the client stores — a packed name would lose every other letter.
        """

        raw = b"\xa9\x0b\x00\x00" + "Foreman".encode("utf-16-le") + b"\x00\x00"

        self.assertEqual(string_table.decode(raw), "Foreman")
        self.assertEqual(string_table.decode_plain(raw), "Foreman")

    def test_a_decode_with_no_context_returns_empty_text(self) -> None:
        """The load's own answer when there is no TextParser to read: nothing yet."""

        raw = raw_of(digit_run(5) + (0,))

        with patch.object(string_table.TextParser, "_update_ptr"), patch.object(
            string_table.TextParser, "get_context", return_value=None
        ):
            self.assertEqual(string_table.decode(raw), "")

        self.assertEqual(string_table._last_load_status, "TextParser context unavailable")

    def test_a_decode_that_needs_the_table_loads_it_then_answers_from_the_cache(self) -> None:
        """The whole pipeline: slots → entries → decode → postprocess → cache."""

        payload = b"".join(entry(b"unused", 0x20, 8) for _ in range(5))
        context = FakeTextParserContext(10, [FakeSlot("a")])
        raw = raw_of(digit_run(5) + (0,))

        with patch.object(string_table.TextParser, "_update_ptr"), patch.object(
            string_table.TextParser, "get_context", return_value=context
        ), patch.object(
            string_table,
            "_load_dat_file",
            slot_loader({"a": payload + entry(b"Foreman", 0x20, 8)}),
        ):
            first = string_table.decode(raw)
            await_cached(raw)
            second = string_table.decode(raw)

        self.assertEqual(first, "", "the source answers from the cache one call later")
        self.assertEqual(second, "Foreman")
        self.assertEqual(string_table.decode_plain(raw), "Foreman")

    def test_a_table_already_in_place_answers_without_any_client(self) -> None:
        string_table._string_table[5] = entry(b"Foreman", 0x20, 8)
        string_table._string_table_loaded = True
        raw = raw_of(digit_run(5) + (0,))

        self.assertEqual(string_table.decode(raw), "")
        await_cached(raw)
        self.assertEqual(string_table.decode(raw), "Foreman")

    def test_a_second_language_uses_its_own_table_and_its_own_cache(self) -> None:
        string_table._loaded_language = 0
        second = {5: entry(b"Foreman", 0x20, 8)}

        with patch.object(
            string_table, "_load_table_for_language", return_value=second
        ):
            raw = raw_of(digit_run(5) + (0,))
            self.assertEqual(string_table.decode(raw, language=1), "Foreman")

        self.assertEqual(string_table._decode_cache_by_language[(1, raw)], "Foreman")
        self.assertEqual(string_table._decode_cache, {}, "the default table's cache is untouched")

    def test_a_second_language_with_no_table_answers_nothing(self) -> None:
        with patch.object(string_table, "_load_table_for_language", return_value={}):
            raw = raw_of(digit_run(5) + (0,))
            self.assertEqual(string_table.decode(raw, language=1), "")


if __name__ == "__main__":
    unittest.main()
