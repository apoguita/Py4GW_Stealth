"""Offline tests for the GW.dat read, against a synthetic client.

What is under test is the call chain ``gw_dat_reader.cpp`` runs and this port reproduces:
which client function is called, in which order, with which words, which form each one uses,
and what happens to the record and the buffer on every path — including the failure paths,
because that is where the source's own ``free``/``close`` bookkeeping lives.

The client is faked: a resolver that answers which functions exist, a call function that
records what it was given and behaves like the client's own DAT functions, a data region for
the two pointer arguments, and a reader for the copied bytes. Nothing here opens a process.

What it does not prove: that the resolvers find these functions in a live client, or that the
client's DAT functions behave as the source's declarations say. Both are live questions.
"""

from __future__ import annotations

import unittest
from typing import Any
from unittest import mock

from py4gw import dat_reader
from py4gw.game_thread.shared_block import (
    DATA_SIZE,
    CallForm,
    CommandRecord,
    CommandState,
)

#: The addresses the fake client hands out, so a test can tell them apart.
RECORD = 0x50005000
BUFFER = 0x60006000
READER_BASE = 0x70007000
FILE_BYTES = b"\x08\x00\x46oreman\x00"


class FakeDataRegion:
    """The block's data region, by offset, with addresses a caller can hand over."""

    def __init__(self, base: int = 0x4000_0000) -> None:
        self.base = base
        self.raw = bytearray(DATA_SIZE)

    def data_address(self, offset: int, size: int = 0) -> int:
        if offset < 0 or offset + size > DATA_SIZE:
            raise ValueError("span outside the data region")
        return self.base + offset

    def write_data(self, offset: int, payload: bytes) -> int:
        address = self.data_address(offset, len(payload))
        self.raw[offset : offset + len(payload)] = payload
        return address

    def read_data(self, offset: int, size: int) -> bytes:
        return bytes(self.raw[offset : offset + size])


class FakeAccess:
    """A reader that serves the bytes this test placed at a buffer address."""

    def __init__(self) -> None:
        self.contents: dict[int, bytes] = {}
        self.failures: set[int] = set()
        self.reads: list[tuple[int, int]] = []

    def read(self, address: int, size: int) -> bytes:
        self.reads.append((address, size))
        if address in self.failures:
            raise OSError(f"address 0x{address:X} is not readable")
        data = self.contents.get(address)
        if data is None or len(data) < size:
            raise OSError(f"address 0x{address:X} holds no {size} bytes")
        return data[:size]


class FakeClient:
    """A client whose DAT functions behave like the source's declarations say.

    Every call is recorded as ``(name, form, words)``, and the answers are the test's: which
    functions resolve, whether ``OpenFileByFileId`` names a record, what ``ReadFileBuffer``
    reports, and whether it hands over a buffer at all.
    """

    def __init__(self, pid: int = 4242) -> None:
        self._pid = pid
        self.bridge = FakeDataRegion()
        self.access = FakeAccess()
        self.calls: list[tuple[str, CallForm, tuple[int, ...]]] = []
        self.resolved: set[str] = set(dat_reader.REQUIRED_FUNCTIONS) | {
            dat_reader.OPEN_FILE_BY_FILE_ID
        }
        self.resolve_calls: list[str] = []
        self.opens_a_record = True
        self.reports_size: int | None = len(FILE_BYTES)
        self.hands_over_a_buffer = True
        self.access.contents[BUFFER] = FILE_BYTES

    @property
    def pid(self) -> int:
        return self._pid

    def resolves(self, name: str) -> bool:
        self.resolve_calls.append(name)
        return name in self.resolved

    def call_function(
        self, name: str, form: CallForm, *words: int
    ) -> CommandRecord:
        if name not in self.resolved:
            raise RuntimeError(f"pid {self._pid}: {name} did not resolve")
        self.calls.append((name, form, tuple(words)))

        if name == dat_reader.OPEN_FILE_BY_FILE_ID:
            value = RECORD if self.opens_a_record else 0
        elif name == dat_reader.FILE_HASH_TO_REC_OBJ:
            value = RECORD
        elif name == dat_reader.READ_FILE_BUFFER:
            size_out = words[1]
            size = 0 if self.reports_size is None else self.reports_size
            offset = size_out - self.bridge.base
            self.bridge.raw[offset : offset + 4] = size.to_bytes(4, "little")
            value = BUFFER if self.hands_over_a_buffer else 0
        else:
            value = 0

        return CommandRecord(
            sequence=len(self.calls),
            operation=5,
            state=CommandState.DONE,
            value=value,
        )

    # -- what a test asks afterwards ---------------------------------------

    def names(self) -> list[str]:
        """Return the function names that were called, in order."""

        return [name for name, _, _ in self.calls]

    def call_to(self, name: str) -> tuple[CallForm, tuple[int, ...]]:
        """Return the form and the words of the one call to ``name``."""

        matches = [(form, words) for called, form, words in self.calls if called == name]
        if len(matches) != 1:
            raise AssertionError(f"{name} was called {len(matches)} times")
        return matches[0]

    def hash_written(self) -> str:
        """Return the UTF-16 hash string that was placed in the data region."""

        return self.bridge.raw[:8].decode("utf-16-le").split("\x00")[0]


def reset_hooks() -> None:
    """Forget the module's resolved-once answer, so each test asks its own client."""

    dat_reader._hooks_pid = 0
    dat_reader._hooks_ready = False
    dat_reader._open_ready = False


class FileHashTests(unittest.TestCase):
    """The two hash conversions, which are pure and are what address the archive."""

    def test_a_file_id_round_trips_through_its_hash(self) -> None:
        for file_id in (1, 2, 0xFF, 0x12345, 0x7F00, 0xFF00, 0xFF_FFFF):
            with self.subTest(file_id=file_id):
                self.assertEqual(
                    dat_reader.file_hash_to_file_id(
                        dat_reader.file_id_to_file_hash(file_id)
                    ),
                    file_id,
                )

    def test_a_hash_is_two_code_units_above_the_ascii_range(self) -> None:
        """Which is why it is not text, and why the client reads it as a string."""

        file_hash = dat_reader.file_id_to_file_hash(1)

        self.assertEqual(len(file_hash), 2)
        self.assertTrue(all(ord(unit) > 0xFF for unit in file_hash))

    def test_the_high_unit_truncates_like_a_wchar(self) -> None:
        """The source stores it in a ``wchar_t``, so sixteen bits is the whole story."""

        file_hash = dat_reader.file_id_to_file_hash(0xFF_FFFF)

        self.assertTrue(all(ord(unit) <= 0xFFFF for unit in file_hash))

    def test_an_impossible_file_id_is_refused(self) -> None:
        for file_id in (0, -1, 2**32):
            with self.subTest(file_id=file_id):
                with self.assertRaises(ValueError):
                    dat_reader.file_id_to_file_hash(file_id)

    def test_a_string_that_is_not_a_hash_is_zero(self) -> None:
        """The source's own answer for anything that is not one of its two shapes."""

        for value in ("", "a", "ab", "ABC", "ab\x00c", "\x01\x02", "\u0100\u0101\u0102\u0103"):
            with self.subTest(value=repr(value)):
                self.assertEqual(dat_reader.file_hash_to_file_id(value), 0)

    def test_a_three_unit_hash_is_a_hash_with_a_subtype(self) -> None:
        file_hash = dat_reader.file_id_to_file_hash(0x12345) + "\u0200"

        self.assertEqual(
            dat_reader.file_hash_to_file_id(file_hash),
            dat_reader.file_hash_to_file_id(file_hash[:2]),
            "the subtype does not change the id",
        )


class ReadFileByHashTests(unittest.TestCase):
    """The chain ``ReadDatFile`` runs, and what each of its calls carries."""

    def setUp(self) -> None:
        reset_hooks()
        self.client = FakeClient()
        self.client.resolved = set(dat_reader.REQUIRED_FUNCTIONS) | {
            dat_reader.OPEN_FILE_BY_FILE_ID
        }
        self.patch_client()

    def patch_client(self) -> None:
        """Make this test's client the connected one, without connecting."""

        self._patcher = mock.patch(
            "py4gw.client.require_client", return_value=self.client
        )
        self._patcher.start()
        self.addCleanup(self._patcher.stop)

    def test_the_whole_chain_runs_in_the_sources_order(self) -> None:
        data = dat_reader.read_file_by_hash(
            dat_reader.file_id_to_file_hash(0x12345)
        )

        self.assertEqual(data, FILE_BYTES)
        self.assertEqual(
            self.client.names(),
            [
                dat_reader.OPEN_FILE_BY_FILE_ID,
                dat_reader.READ_FILE_BUFFER,
                dat_reader.FREE_FILE_BUFFER,
                dat_reader.CLOSE_REC_OBJ,
            ],
        )

    def test_the_open_call_carries_the_sources_five_words(self) -> None:
        """``OpenFileByFileId(0, file_id, stream_id, 1, 0)`` — the form's whole point."""

        file_id = 0x12345
        dat_reader.read_file_by_id(file_id, stream_id=7)

        form, words = self.client.call_to(dat_reader.OPEN_FILE_BY_FILE_ID)
        self.assertEqual(form, CallForm.U32_U32_U32_U32_U32)
        self.assertEqual(words, (0, file_id, 7, 1, 0))

    def test_the_hash_read_passes_the_bindings_own_stream(self) -> None:
        """The binding passes ``1`` and takes no stream id, so neither does this function."""

        dat_reader.read_file_by_hash(dat_reader.file_id_to_file_hash(4))

        form, words = self.client.call_to(dat_reader.OPEN_FILE_BY_FILE_ID)
        self.assertEqual(words[2], dat_reader.READ_STREAM_ID)

    def test_the_buffer_call_carries_the_record_and_the_size_word(self) -> None:
        dat_reader.read_file_by_hash(dat_reader.file_id_to_file_hash(4))

        form, words = self.client.call_to(dat_reader.READ_FILE_BUFFER)
        self.assertEqual(form, CallForm.U32_U32)
        self.assertEqual(words[0], RECORD)
        self.assertEqual(words[1], self.client.bridge.data_address(8, 4))

    def test_the_buffer_and_the_record_are_given_back_in_that_order(self) -> None:
        dat_reader.read_file_by_hash(dat_reader.file_id_to_file_hash(4))

        form, words = self.client.call_to(dat_reader.FREE_FILE_BUFFER)
        self.assertEqual(form, CallForm.U32_U32)
        self.assertEqual(words, (RECORD, BUFFER))

        form, words = self.client.call_to(dat_reader.CLOSE_REC_OBJ)
        self.assertEqual(form, CallForm.U32)
        self.assertEqual(words, (RECORD,))

    def test_the_hash_string_goes_into_the_block_as_utf16_when_it_is_needed(self) -> None:
        """``c_str()`` is what the client reads, so the terminator goes in with it.

        The string is only needed by the record call: a read the sequential-id call answers
        never puts the hash in the client at all, which is the source's own short-circuit.
        """

        file_hash = dat_reader.file_id_to_file_hash(0x12345)

        dat_reader.read_file_by_hash(file_hash)
        self.assertEqual(
            self.client.hash_written(), "", "the sequential-id call takes no string"
        )

        self.client.resolved.discard(dat_reader.OPEN_FILE_BY_FILE_ID)
        reset_hooks()
        dat_reader.read_file_by_hash(file_hash)

        self.assertEqual(self.client.hash_written(), file_hash)
        self.assertEqual(self.client.bridge.raw[4:6], b"\x00\x00")

    def test_the_size_word_is_zeroed_before_the_call(self) -> None:
        """The source's own ``int size = 0;`` — a stale length must not be read as one."""

        bridge = self.client.bridge
        bridge.write_data(8, b"\xff\xff\xff\xff")
        seen: list[bytes] = []

        original = self.client.call_function

        def call(name: str, form: CallForm, *words: int) -> Any:
            if name == dat_reader.READ_FILE_BUFFER:
                seen.append(bridge.read_data(8, 4))
            return original(name, form, *words)

        self.client.call_function = call  # type: ignore[method-assign]
        dat_reader.read_file_by_hash(dat_reader.file_id_to_file_hash(4))

        self.assertEqual(seen, [bytes(4)])

    def test_the_bytes_come_back_from_the_buffer_the_client_handed_over(self) -> None:
        dat_reader.read_file_by_hash(dat_reader.file_id_to_file_hash(4))

        self.assertEqual(self.client.access.reads, [(BUFFER, len(FILE_BYTES))])

    def test_a_hash_with_a_subtype_skips_the_open_call(self) -> None:
        """``has_subtype`` is the source's own reason: the id is not the whole hash."""

        file_hash = dat_reader.file_id_to_file_hash(0x12345) + "\u0200"

        self.assertEqual(dat_reader.read_file_by_hash(file_hash), FILE_BYTES)
        self.assertEqual(self.client.names()[0], dat_reader.FILE_HASH_TO_REC_OBJ)

        form, words = self.client.call_to(dat_reader.FILE_HASH_TO_REC_OBJ)
        self.assertEqual(form, CallForm.U32_U32_U32)
        self.assertEqual(words[1:], (1, 0))
        self.assertEqual(words[0], self.client.bridge.data_address(0, 6))

    def test_the_hash_call_is_the_fallback_when_the_open_is_missing(self) -> None:
        self.client.resolved.discard(dat_reader.OPEN_FILE_BY_FILE_ID)
        reset_hooks()

        data = dat_reader.read_file_by_hash(dat_reader.file_id_to_file_hash(4))

        self.assertEqual(data, FILE_BYTES)
        self.assertEqual(
            self.client.names()[:2],
            [dat_reader.FILE_HASH_TO_REC_OBJ, dat_reader.READ_FILE_BUFFER],
        )

    def test_the_hash_call_is_the_fallback_when_the_open_names_no_record(self) -> None:
        self.client.opens_a_record = False

        self.assertEqual(
            dat_reader.read_file_by_hash(dat_reader.file_id_to_file_hash(4)),
            FILE_BYTES,
        )
        self.assertEqual(
            self.client.names()[:3],
            [
                dat_reader.OPEN_FILE_BY_FILE_ID,
                dat_reader.FILE_HASH_TO_REC_OBJ,
                dat_reader.READ_FILE_BUFFER,
            ],
        )

    def test_an_empty_hash_reads_nothing(self) -> None:
        self.assertIsNone(dat_reader.read_file_by_hash(""))
        self.assertEqual(self.client.calls, [])

    def test_a_hash_that_is_not_a_hash_still_reaches_the_client(self) -> None:
        """The source does not check the hash's shape here; it asks the client for it.

        ``FileHashToFileId`` answers zero for a two-character string that is not a hash, which
        only means the sequential-id call is skipped — the record call is still made, with the
        string itself.
        """

        dat_reader.read_file_by_hash("ab")

        self.assertEqual(self.client.names()[0], dat_reader.FILE_HASH_TO_REC_OBJ)
        self.assertEqual(self.client.hash_written(), "ab")

    def test_a_hash_too_long_for_the_region_is_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "at most 3 code units"):
            dat_reader.read_file_by_hash("\u0100\u0101\u0102\u0103")


class EnsureHooksTests(unittest.TestCase):
    """``EnsureHooks``: resolved once, and a missing function answers "not there"."""

    def setUp(self) -> None:
        reset_hooks()

    def test_a_missing_function_means_no_read_at_all(self) -> None:
        client = FakeClient()
        resolved: set[str] = set(dat_reader.REQUIRED_FUNCTIONS)
        resolved.discard(dat_reader.CLOSE_REC_OBJ)
        client.resolved = resolved
        with mock.patch("py4gw.client.require_client", return_value=client):
            self.assertIsNone(
                dat_reader.read_file_by_hash(dat_reader.file_id_to_file_hash(4))
            )

        self.assertEqual(client.calls, [], "nothing is called when a function is missing")

    def test_the_required_functions_are_looked_up_once_per_client(self) -> None:
        """``EnsureHooks`` resolves once; the optional one is still checked per call."""

        client = FakeClient()
        with mock.patch("py4gw.client.require_client", return_value=client):
            dat_reader.read_file_by_hash(dat_reader.file_id_to_file_hash(4))
            first = [
                name
                for name in client.resolve_calls
                if name in dat_reader.REQUIRED_FUNCTIONS
            ]
            dat_reader.read_file_by_hash(dat_reader.file_id_to_file_hash(5))
            second = [
                name
                for name in client.resolve_calls
                if name in dat_reader.REQUIRED_FUNCTIONS
            ]

        self.assertEqual(first, list(dat_reader.REQUIRED_FUNCTIONS))
        self.assertEqual(second, first, "the second read resolves nothing again")

    def test_another_client_is_asked_again(self) -> None:
        first = FakeClient(pid=1)
        second = FakeClient(pid=2)
        with mock.patch("py4gw.client.require_client", return_value=first):
            dat_reader.read_file_by_hash(dat_reader.file_id_to_file_hash(4))
        with mock.patch("py4gw.client.require_client", return_value=second):
            dat_reader.read_file_by_hash(dat_reader.file_id_to_file_hash(4))

        self.assertTrue(second.resolve_calls)


class ReadDatRecordFailureTests(unittest.TestCase):
    """Every path out of ``ReadDatRecord``, with the record and the buffer accounted for."""

    def setUp(self) -> None:
        reset_hooks()
        self.client = FakeClient()

    def read(self) -> bytes | None:
        with mock.patch(
            "py4gw.client.require_client", return_value=self.client
        ):
            return dat_reader.read_file_by_hash(dat_reader.file_id_to_file_hash(4))

    def test_no_buffer_closes_the_record_and_frees_nothing(self) -> None:
        self.client.hands_over_a_buffer = False

        self.assertIsNone(self.read())
        self.assertEqual(
            self.client.names()[-1], dat_reader.CLOSE_REC_OBJ
        )
        self.assertNotIn(dat_reader.FREE_FILE_BUFFER, self.client.names())

    def test_a_length_of_zero_closes_the_record_and_frees_nothing(self) -> None:
        self.client.reports_size = 0

        self.assertIsNone(self.read())
        self.assertEqual(self.client.names()[-1], dat_reader.CLOSE_REC_OBJ)
        self.assertNotIn(dat_reader.FREE_FILE_BUFFER, self.client.names())

    def test_a_length_past_the_bound_frees_the_buffer_and_closes(self) -> None:
        self.client.reports_size = dat_reader.MAX_DAT_FILE_BYTES + 1

        self.assertIsNone(self.read())
        self.assertEqual(
            self.client.names()[-2:],
            [dat_reader.FREE_FILE_BUFFER, dat_reader.CLOSE_REC_OBJ],
        )
        self.assertEqual(self.client.access.reads, [], "nothing is allocated or read")

    def test_a_copy_that_failed_frees_the_buffer_and_closes(self) -> None:
        self.client.access.failures.add(BUFFER)

        self.assertIsNone(self.read())
        self.assertEqual(
            self.client.names()[-2:],
            [dat_reader.FREE_FILE_BUFFER, dat_reader.CLOSE_REC_OBJ],
        )

    def test_a_record_of_zero_reads_nothing(self) -> None:
        self.client.opens_a_record = False
        self.client.resolved.discard(dat_reader.OPEN_FILE_BY_FILE_ID)
        reset_hooks()

        def call(name: str, form: CallForm, *words: int) -> CommandRecord:
            self.client.calls.append((name, form, tuple(words)))
            return CommandRecord(sequence=1, operation=5, state=CommandState.DONE, value=0)

        self.client.call_function = call  # type: ignore[method-assign]

        self.assertIsNone(self.read())
        self.assertEqual(
            self.client.names(), [dat_reader.FILE_HASH_TO_REC_OBJ], "the read stops there"
        )


class ReadFileByIdTests(unittest.TestCase):
    """``PyDatReader.read_file_by_id``: the same read, opened by sequential id."""

    def setUp(self) -> None:
        reset_hooks()
        self.client = FakeClient()
        self._patcher = mock.patch(
            "py4gw.client.require_client", return_value=self.client
        )
        self._patcher.start()
        self.addCleanup(self._patcher.stop)

    def test_it_opens_by_id_and_reads_the_record(self) -> None:
        self.assertEqual(dat_reader.read_file_by_id(0x12345), FILE_BYTES)

        self.assertEqual(
            self.client.names(),
            [
                dat_reader.OPEN_FILE_BY_FILE_ID,
                dat_reader.READ_FILE_BUFFER,
                dat_reader.FREE_FILE_BUFFER,
                dat_reader.CLOSE_REC_OBJ,
            ],
        )
        form, words = self.client.call_to(dat_reader.OPEN_FILE_BY_FILE_ID)
        self.assertEqual(form, CallForm.U32_U32_U32_U32_U32)
        self.assertEqual(words, (0, 0x12345, 1, 1, 0))

    def test_a_zero_id_reads_nothing(self) -> None:
        self.assertIsNone(dat_reader.read_file_by_id(0))
        self.assertEqual(self.client.calls, [])

    def test_a_missing_open_function_answers_nothing(self) -> None:
        self.client.resolved.discard(dat_reader.OPEN_FILE_BY_FILE_ID)

        self.assertIsNone(dat_reader.read_file_by_id(4))
        self.assertEqual(self.client.calls, [])


if __name__ == "__main__":
    unittest.main()
