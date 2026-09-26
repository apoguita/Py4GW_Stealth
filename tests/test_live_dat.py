"""Live Guild Wars test for the GW.dat read, and the text it decodes to.

**This is the last piece of the text path.** The offline tests prove the decoder turns entries
into text and the call chain passes the words it says it passes; only a running client can
prove that the client hands over a real string-table file, that the table is this build's, and
that a real encoded string out of the client renders.

Two phases:

1. **The read.** The connection is installed, one file is read through the ported chain
   (``FileHashToFileId`` → ``OpenFileByFileId`` → ``ReadFileBuffer`` → the bounded copy →
   ``FreeFileBuffer`` → ``CloseRecObj``), its entries are parsed, and what they decode to with
   no key is counted.
2. **A real encoded string** (``test_z_...``). The closest NPC is interacted with; the client
   opens its dialog and reports the body's text pointer in its own message; the codepoints at
   that pointer are read and Route A renders them against the table Phase 1 loaded. That is the
   decode path end to end: client bytes → codepoints → (index, key) → RC4 → text.

**The two things this test changes.** Connecting installs the capability layer — two entry
hooks, a block, a dispatcher and a listener — and Phase 2 interacts with an NPC, which opens a
dialog. A dialog is closed with the Escape key and this project does not synthesise keyboard
input, so Phase 2 hands the client back with the dialog open. Everything else is a read, and
``tearDownClass`` compares both entry bytes and the whole code section with what they were
before the run.

Run it from an **elevated** shell, in a map, with Guild Wars running::

    python -m unittest tests.test_live_dat -v

What it proves: the five functions this build has are the ones the chain resolves; the client
accepts the hash string and the size word this port places in the block; the buffer it hands
over copies out; the bytes are a string table whose entries parse; and a dialog's own codepoints
render to printable text.
"""

from __future__ import annotations

import hashlib
import math
import time
import unittest
from typing import Any

import py4gw
from py4gw import dat_reader, dialog
from py4gw.context.agent_array import AgentAllegiance
from py4gw.game_thread.shared_block import EventKind, EventRecord, EventTextState
from py4gw.internals import string_table
from py4gw.player import Player
from py4gw.ui import async_decode
from py4gw.ui.encoded_str import is_valid_enc_str
from py4gw.win32 import Win32

#: The two functions the connection hooks, and the bytes they hold before it does.
HOOK_RESOLVER = "game_thread.leave_game_thread_func"
OBSERVE_RESOLVER = "ui.send_ui_message_func"
HOOK_ENTRY = bytes.fromhex("55 8B EC 81 EC 20 02 00 00")
OBSERVE_ENTRY = bytes.fromhex("55 8B EC 8B 45 08 83 F8 56")

#: Which language's table and which of its files are read. The client's own language is 0 and
#: its first file holds the table's first ``entries_per_file`` entries.
LANGUAGE = 0
SLOT = 0

#: How many of a file's entries are sampled for decoding, and how many codepoints are read at a
#: text pointer. A dialog body is a sentence or two; the read stops at the array's terminator.
SAMPLE_ENTRIES = 1024
CODEPOINT_LIMIT = 256

#: How long the client gets to open a dialog after the interaction, and how often it is asked.
OPEN_WAIT_S = 30.0
POLL_S = 0.25

#: How long the client's decoder gets to answer a decode this project handed it. It is
#: asynchronous — the client decodes on its own schedule and calls the stub back — and a couple
#: of seconds is what that costs; this is the bound the wait gives up at, not a delay.
DECODE_WAIT_S = 15.0

#: How many agent records the closest-NPC scan reads before it gives up.
SCAN_LIMIT = 400

#: How many times the announced body pointer is sampled, at most, while it reads empty.
BODY_SAMPLE_LIMIT = 256

TEXT_CHUNK = 0x10000


class _DialogSpy:
    """Keep the text pointers the client's own dialog messages carry.

    The dialog module reads ``DialogBodyInfo``'s agent and ``DialogButtonInfo``'s id; word 2 of
    the body and word 1 of a button are where the client puts the *text* pointer, which is what
    Phase 2 needs.
    """

    def __init__(self) -> None:
        self.body_pointer = 0
        self.body_agent = 0
        self.bodies = 0
        self.button_pointers: list[int] = []
        self.button_ids: list[int] = []
        self.timeline: list[tuple[float, int, bool, int, int, bool, bool]] = []
        self._last_state: tuple[bool, int, int, bool] | None = None
        #: When the text the body announced first appears at the pointer it announced:
        #: ``(timestamp, the first words there)``, sampled at each message the client sends
        #: while they still read empty. The module reads that pointer when the message
        #: arrives and this suite reads it a second later, so the run has to say what was
        #: there at each time.
        self.body_samples: list[tuple[float, list[int]]] = []
        #: The copy the observer took of the string each dialog message named, as it travelled:
        #: ``(state, code units)`` for the body and then for each button. This is the mechanism
        #: the label depends on — read inside the client's own call — so the run keeps it.
        self.body_copy: tuple[int, tuple[int, ...]] | None = None
        self.button_copies: list[tuple[int, tuple[int, ...]]] = []

    def _sample_body_pointer(self) -> None:
        """Read the announced body pointer's first words, until the client's text is there.

        Read-only, and bounded: it stops at the first sample with a word in it, and at
        :data:`BODY_SAMPLE_LIMIT` samples either way.
        """

        if not self.body_pointer or len(self.body_samples) >= BODY_SAMPLE_LIMIT:
            return
        if self.body_samples and self.body_samples[-1][1][0]:
            return
        read_uint32 = dialog._dialog_tables().read_uint32
        words = [
            int(read_uint32(self.body_pointer + index * 2) or 0) for index in range(2)
        ]
        self.body_samples.append((time.monotonic() * 1000.0, words))

    def __call__(self, event: EventRecord) -> None:
        """Keep the pointers from one event, and every change of the module's gate.

        ``EventRecord.kind`` is a plain ``int`` while ``EventKind`` is an ``IntEnum``, so the
        comparison is by value: an identity test against the member is false for every real
        record.
        """

        if int(event.kind) != int(EventKind.UI_MESSAGE):
            return

        is_dialog = event.sequence in (
            dialog.DIALOG_BODY_MESSAGE,
            dialog.DIALOG_BUTTON_MESSAGE,
        )
        # The gate as the dialog module left it for *this* message. The connection registers
        # the module's capture before this spy, so the module has already run: a suspended
        # gate here is the reason that message was not captured, not a state this test set.
        state = (
            dialog._callbacks_suspended,
            dialog._callbacks_resume_tick,
            dialog._last_observed_map_id,
            dialog._last_observed_map_ready,
        )
        if is_dialog or state != self._last_state:
            self.timeline.append(
                (time.monotonic() * 1000.0, event.sequence) + state + (is_dialog,)
            )
        self._last_state = state

        if event.sequence == dialog.DIALOG_BODY_MESSAGE:
            self.body_agent = int(event.arg1)
            self.body_pointer = int(event.arg2)
            self.body_copy = (int(event.text_state), tuple(event.text))
            self.bodies += 1
        elif event.sequence == dialog.DIALOG_BUTTON_MESSAGE:
            self.button_pointers.append(int(event.arg1))
            self.button_ids.append(int(event.arg2))
            self.button_copies.append((int(event.text_state), tuple(event.text)))

        # Last, so the body's own message is the first sample: what the module read when it
        # handled that message is the first thing this records.
        self._sample_body_pointer()


class LiveDatReadTests(unittest.TestCase):
    """The archive read, and one real encoded string rendered from what it read."""

    # -- the class's own state ---------------------------------------------

    pid: int
    client: py4gw.ConnectedClient
    text_before: tuple[str, int]
    module_base: int
    module_size: int
    hook_address: int
    observe_address: int
    entries_per_file: int
    slot_count: int
    slot: Any
    file_hash: str
    file_id: int
    data: bytes
    table: dict[int, bytes]
    tables: dict[int, dict[int, bytes]]
    entry_count: int
    decoded: list[tuple[int, str]]
    spy: _DialogSpy
    rendered_body: str = ""

    # -- setup and teardown ------------------------------------------------

    @classmethod
    def setUpClass(cls) -> None:
        win32 = Win32()
        clients = win32.find_guild_wars()
        if not clients:
            raise unittest.SkipTest("Start Guild Wars before running this test.")
        cls.pid = int(clients[0]["pid"])

        if not win32.is_elevated():
            raise unittest.SkipTest(
                "The controller must be elevated: connecting asserts it, and the "
                "write rights are denied without it. Run this suite from an "
                "elevated shell."
            )

        module = win32.get_main_module(cls.pid)
        cls.module_base = int(module["base_address"])
        cls.module_size = int(module["size"])

        cls.hook_address = cls._resolve(win32, cls.pid, HOOK_RESOLVER)
        cls.observe_address = cls._resolve(win32, cls.pid, OBSERVE_RESOLVER)
        targets = (
            (HOOK_RESOLVER, cls.hook_address, HOOK_ENTRY),
            (OBSERVE_RESOLVER, cls.observe_address, OBSERVE_ENTRY),
        )

        # A run that was interrupted leaves this library's own entry patches in place, and the
        # connection repairs them when it next installs (``Client._prepare_target``: a ``jmp``
        # whose destination is outside the module is ours from a controller that died, and
        # ``_stale_patch_before`` finds it ahead of the address the resolver answered). The resolver
        # itself walks back to prologues only, as the source does (``scanner.cpp:205-210``), so a
        # patched entry is invisible to it and the recovery, not the resolver, closes that gap. The
        # client is given exactly that cycle first, and the run measures from the client that comes
        # back — which is also the check that the repair works.
        if any(
            cls._read_entry(win32, cls.pid, address, len(expected)) != expected
            for _, address, expected in targets
        ):
            print("--- the client was still patched by an interrupted run ---")
            py4gw.connect(clients[0])
            py4gw.disconnect()

        for name, address, expected in targets:
            observed = cls._read_entry(win32, cls.pid, address, len(expected))
            if observed != expected:
                raise AssertionError(
                    f"pid {cls.pid}: {name} at 0x{address:08X} holds "
                    f"{observed.hex(' ')}, not {expected.hex(' ')}. Nothing was written."
                )
        cls.text_before = cls._text_digest(win32, cls.pid)

        # Connecting installs the capability layer, which is the mode a caller uses and
        # therefore the mode under test. The dialog's own capture is registered by the
        # connection; the spy is this test's, and it only reads what the client reported.
        cls.client = py4gw.connect(clients[0])
        cls.spy = _DialogSpy()
        cls.client.callbacks.register(EventKind.UI_MESSAGE, cls.spy)
        print(cls._gate_report("--- the module's gate as the connection left it ---"))
        try:
            cls._read_one_file()
        except BaseException:
            py4gw.disconnect()
            raise

        printable = [text for _, text in cls.decoded if cls._is_printable(text)]
        print(
            f"\n--- GW.dat read, live, pid {cls.pid} ---\n"
            f"module                     = 0x{cls.module_base:08X} + "
            f"0x{cls.module_size:X}\n"
            f"leave_game_thread_func     = 0x{cls.hook_address:08X}\n"
            f"ui.send_ui_message_func    = 0x{cls.observe_address:08X}\n"
            f"resolvers                  = "
            + ", ".join(
                f"{name.rsplit('.', 1)[-1]}={cls.client.resolves(name)}"
                for name in (
                    dat_reader.OPEN_FILE_BY_FILE_ID,
                    dat_reader.FILE_HASH_TO_REC_OBJ,
                    dat_reader.READ_FILE_BUFFER,
                    dat_reader.FREE_FILE_BUFFER,
                    dat_reader.CLOSE_REC_OBJ,
                )
            )
            + "\n"
            f"language / slot            = {LANGUAGE} / {SLOT}\n"
            f"file hash code units       = "
            f"{[ord(unit) for unit in cls.slot.file_hash]}\n"
            f"file id                    = {cls.file_id}\n"
            f"entries per file           = {cls.entries_per_file}\n"
            f"slot start / end index     = {int(cls.slot.start_index)} / "
            f"{int(cls.slot.end_index)}\n"
            f"bytes read                 = {len(cls.data)}\n"
            f"entries parsed             = {len(cls.table)}\n"
            f"decoded with no key        = {len(cls.decoded)} "
            f"({len(printable)} printable)\n"
            + "".join(f"    {text[:70]!r}\n" for text in printable[:8])
            + "--- end of the read ---\n"
        )

    @classmethod
    def tearDownClass(cls) -> None:
        py4gw.disconnect()

        win32 = Win32()
        hook_after = cls._read_entry(win32, cls.pid, cls.hook_address, len(HOOK_ENTRY))
        observe_after = cls._read_entry(
            win32, cls.pid, cls.observe_address, len(OBSERVE_ENTRY)
        )
        text_after = cls._text_digest(win32, cls.pid)

        print(
            "\n--- the client was put back as follows ---\n"
            f"game-thread entry after    = {hook_after.hex(' ')}\n"
            f"message entry after        = {observe_after.hex(' ')}\n"
            f"code section before        = {cls.text_before[0][:32]}... "
            f"({cls.text_before[1]} bytes)\n"
            f"code section after         = {text_after[0][:32]}... "
            f"({text_after[1]} bytes)\n"
            "--- end of the live GW.dat test ---"
        )

        if hook_after != HOOK_ENTRY or observe_after != OBSERVE_ENTRY:
            raise AssertionError(
                f"pid {cls.pid}: a hooked function was left patched: "
                f"{hook_after.hex(' ')} and {observe_after.hex(' ')}."
            )
        if text_after != cls.text_before:
            raise AssertionError(
                f"pid {cls.pid}: the code section changed during the run: "
                f"{cls.text_before[0]} before, {text_after[0]} after."
            )

    # -- phase 1: the read -------------------------------------------------

    @classmethod
    def _read_slot(cls, slot_index: int) -> tuple[Any, bytes, dict[int, bytes], int]:
        """Read one of the language's files through the ported chain, and parse it.

        The table is ``slot_count`` files of ``entries_per_file`` entries each, which is what
        the source's own load walks; this reads the one file it is asked for. An empty slot is
        ``None`` rather than an exception: a caller that asked for a slot nobody named is a
        finding to report, and one that asked for the first slot and got nothing has no table
        to test.
        """

        parser = cls._parser()
        cls.entries_per_file = int(parser.entries_per_file)
        cls.slot_count = int(parser.language_slots[LANGUAGE].slot_count)
        slot = parser.get_file_slot(slot_index, LANGUAGE)
        if slot is None or not slot.file_hash_ptr:
            return None  # type: ignore[return-value]

        data = dat_reader.read_file_by_hash(slot.file_hash) or b""
        table: dict[int, bytes] = {}
        count = string_table._parse_string_file(data, int(slot.start_index), table)
        return slot, data, table, count

    @classmethod
    def _parser(cls) -> Any:
        """Return the client's TextParser snapshot, refusing to test without one."""

        parser = cls.client.read_text_parser()
        if parser is None:
            raise unittest.SkipTest(
                "The connected client has no readable TextParser context, so there is "
                "no string table to read."
            )
        return parser

    @classmethod
    def _read_one_file(cls) -> None:
        """Read the first file, parse it, and sample what its entries decode to."""

        loaded = cls._read_slot(SLOT)
        if loaded is None:
            raise unittest.SkipTest(f"The TextParser's file slot {SLOT} is empty.")
        cls.slot, cls.data, cls.table, cls.entry_count = loaded
        cls.file_hash = cls.slot.file_hash
        cls.file_id = dat_reader.file_hash_to_file_id(cls.file_hash)
        cls.tables = {SLOT: cls.table}

        cls.decoded = []
        for index in sorted(cls.table)[:SAMPLE_ENTRIES]:
            text = string_table._decode_entry(cls.table[index], 0)
            if text:
                cls.decoded.append((index, text))

    def _table_for(self, index: int) -> dict[int, bytes] | None:
        """Return the file that holds one table index, reading it if this run has not.

        The whole table is ``slot_count`` files; a caller that needs one entry reads the file
        that holds it, which is the same chain with a different slot's hash.
        """

        holder = index // self.entries_per_file
        if not 0 <= holder < self.slot_count:
            return None
        table = self.tables.get(holder)
        if table is not None:
            return table
        loaded = self._read_slot(holder)
        if loaded is None:
            return None
        _, data, table, count = loaded
        self.tables[holder] = table
        print(f"file slot {holder} ({count} entries, {len(data)} bytes) read for index {index}")
        return table

    def _render(self, index: int, key: int) -> str:
        """Render one table index with its key, or ``""`` when it names no entry.

        A codepoint array whose index names no file of this table renders nothing rather than
        failing the test: the two buttons of the dialog this suite opens have been observed to
        hand over the same pointer, and what their codepoints name is a finding to report.
        """

        if not index:
            return ""
        table = self._table_for(index)
        if table is None:
            return ""
        entry = table.get(index)
        if entry is None:
            return ""
        return string_table._postprocess(
            string_table._decode_entry(entry, key) or "", table
        )

    @staticmethod
    def _is_printable(text: str) -> bool:
        """Whether a decoded string is text a caller could read."""

        return bool(text) and all(character.isprintable() for character in text)

    @staticmethod
    def _gate_report(label: str) -> str:
        """One line describing the dialog module's gate, for the live record.

        Read-only: it reads the module's own state and calls nothing that would move it, so
        what it prints is what the module would decide with.
        """

        return (
            f"{label}\n    live map (id, ready)   = {dialog._map_state()}\n"
            f"    observed map           = {dialog._last_observed_map_id} / "
            f"{dialog._last_observed_map_ready}\n"
            f"    callbacks suspended    = {dialog._callbacks_suspended}\n"
            f"    resume tick / now      = {dialog._callbacks_resume_tick} / "
            f"{dialog._now_ms()}"
        )

    def test_the_five_functions_the_chain_calls_are_there(self) -> None:
        for name in (
            dat_reader.FILE_HASH_TO_REC_OBJ,
            dat_reader.OPEN_FILE_BY_FILE_ID,
            dat_reader.READ_FILE_BUFFER,
            dat_reader.FREE_FILE_BUFFER,
            dat_reader.CLOSE_REC_OBJ,
        ):
            with self.subTest(resolver=name):
                self.assertTrue(self.client.resolves(name))

    def test_the_clients_own_decoder_is_there_to_be_called(self) -> None:
        """The dialog's text is rendered by the client, so its decoder has to resolve.

        ``g_validate_async_decode_str_func`` is what native reaches through
        ``GW::ui::AsyncDecodeStr`` (``ui_patterns.cpp:41``); the port calls the same function,
        so this is the one resolver the text path depends on.
        """

        self.assertTrue(
            self.client.resolves(async_decode.ASYNC_DECODE_STR),
            f"{async_decode.ASYNC_DECODE_STR} did not resolve, so no dialog text can be "
            f"decoded on this build",
        )

    def test_the_hash_converts_to_the_id_the_client_opens(self) -> None:
        """``FileHashToFileId`` on a real slot hash: two code units above ``0xFF``."""

        self.assertEqual(len(self.file_hash), 2)
        self.assertTrue(all(ord(unit) > 0xFF for unit in self.file_hash))
        self.assertGreater(self.file_id, 0)

    def test_the_slot_covers_the_entries_its_file_holds(self) -> None:
        """``entries_per_file`` is the stride the source indexes the table with."""

        self.assertEqual(int(self.slot.start_index), SLOT * self.entries_per_file)
        self.assertEqual(
            int(self.slot.end_index) - int(self.slot.start_index), self.entries_per_file
        )

    def test_the_client_handed_over_bytes(self) -> None:
        self.assertGreater(len(self.data), 0, "the read returned nothing")
        self.assertLess(len(self.data), dat_reader.MAX_DAT_FILE_BYTES)

    def test_the_bytes_are_a_string_table(self) -> None:
        """The first word is an entry size the source's own parser accepts."""

        size = int.from_bytes(self.data[:2], "little")
        self.assertGreaterEqual(size, 6)
        self.assertLessEqual(size, 8192)

    def test_the_entries_parse_into_the_table(self) -> None:
        self.assertGreater(self.entry_count, 0)
        self.assertEqual(len(self.table), self.entry_count)
        self.assertIn(int(self.slot.start_index), self.table)
        self.assertNotIn(int(self.slot.start_index) + self.entry_count, self.table)

    def test_an_entry_that_needs_no_key_decodes_to_text(self) -> None:
        """The decoder on the client's own bytes, not on a synthetic entry.

        An entry is stored encrypted only when the codepoint array that names it carries a key,
        so the ones read here with no key are the ones a caller can render without one. What is
        asserted is that the table this client handed over contains such entries and that their
        text is readable; how many there are is reported rather than required.
        """

        printable = [text for _, text in self.decoded if self._is_printable(text)]

        self.assertTrue(
            printable,
            f"none of the first {SAMPLE_ENTRIES} entries decoded to printable text with "
            f"no key; {len(self.decoded)} decoded to something",
        )

    # -- phase 2: a real encoded string ------------------------------------

    def test_z_a_dialogs_own_codepoints_render(self) -> None:
        """The whole path, on text the client itself sent.

        The interaction and the wait are ``tests/probe_dialog_phase1.py``'s: the closest NPC,
        one ``Player.Interact``, and the client's own ``kDialogBody`` message carrying the text
        pointer. This test does not compare against what the client displays — the body is not
        published as a label (``docs/DIALOG_MIGRATION_PLAN.md`` §4) — so what it asserts is
        that the port's own decode of those codepoints is readable text, and it prints it.
        """

        if self.spy.bodies:
            raise unittest.SkipTest(
                "a dialog was already open when this test started, and the client only "
                "announces a body when it opens one"
            )

        xy = Player.GetXY()
        agent_id = self._closest_npc(xy)
        if not agent_id:
            raise unittest.SkipTest("no NPC was found to interact with.")

        print(self._gate_report("--- the gate before the interaction ---"))
        print(f"\ninteracting with agent {agent_id} (closest NPC at {xy})")
        Player.Interact(agent_id)

        waited = 0.0
        while waited < OPEN_WAIT_S and not self.spy.bodies:
            time.sleep(POLL_S)
            waited += POLL_S
        print(
            f"the client announced {self.spy.bodies} dialog bodies and "
            f"{len(self.spy.button_pointers)} buttons in {waited:.1f}s"
        )
        self._print_timeline()
        if not self.spy.bodies:
            raise unittest.SkipTest(
                f"no dialog opened within {OPEN_WAIT_S:.0f}s of the interaction, so "
                "there is no body text to decode."
            )

        read_u32 = self.client.dialog_tables.read_uint32
        codepoints = self._read_codepoints(read_u32, self.spy.body_pointer)
        self.assertIsNotNone(
            codepoints, f"the body pointer 0x{self.spy.body_pointer:08X} is unreadable"
        )
        assert codepoints is not None
        self.assertIn(0, codepoints, "the client's array is NUL-terminated")

        index, key = string_table._parse_codepoints(tuple(codepoints))
        self.assertGreater(index, 0, "the body's codepoints name no table index")

        # The index names one entry of the whole table, and the table is ``slot_count`` files
        # of ``entries_per_file`` entries: the file that holds this index is the one to read.
        table = self._table_for(index)
        self.assertIsNotNone(
            table,
            f"the body names table index {index}, which is outside the "
            f"{self.slot_count} files of {self.entries_per_file} entries this table has",
        )
        assert table is not None
        entry = table.get(index)
        self.assertIsNotNone(
            entry,
            f"the body names table index {index} of the file that holds it "
            f"({min(table)}..{max(table)})",
        )
        assert entry is not None

        text = string_table._decode_entry(entry, key) or ""
        rendered = string_table._postprocess(text, table)
        type(self).rendered_body = rendered
        print(
            f"body pointer               = 0x{self.spy.body_pointer:08X} "
            f"(agent {self.spy.body_agent})\n"
            f"body codepoints            = {len(codepoints)}\n"
            f"first eight                = "
            f"{[hex(cp) for cp in codepoints[:8]]}\n"
            f"table index / key          = {index} / 0x{key:X}\n"
            f"entry bytes                = {len(entry)}\n"
            f"decoded text               = {rendered!r}"
        )
        self._print_body_samples()

        self.assertTrue(rendered, "the body decoded to nothing")
        self.assertTrue(
            all(character.isprintable() or character in "\n\t" for character in rendered),
            f"the body decoded to characters that are not text: {rendered!r}",
        )

        # **The copy is the whole mechanism.** The observer takes the string inside the client's
        # own call, where the client still has it, and carries it out with the event; reading the
        # pointer from here is a read of a buffer the client reuses. The body's string is a table
        # reference and does not move, so this suite's own read of the same pointer a second later
        # is the ground truth to compare the copy against: they must agree word for word.
        self.assertIsNotNone(
            self.spy.body_copy, "the body's message carried no copy at all"
        )
        assert self.spy.body_copy is not None
        body_state, body_copied = self.spy.body_copy
        print(
            f"body copy (inside the call) = state {body_state}, "
            f"{len(body_copied)} code units, first "
            f"{[hex(cp) for cp in body_copied[:8]]}"
        )
        self.assertEqual(
            body_state,
            int(EventTextState.COPIED),
            "the observer did not copy the body's string inside the client",
        )
        self.assertEqual(
            list(body_copied),
            list(codepoints),
            "the copy the observer took is not the string the pointer holds",
        )

        for (state, copied), pointer, dialog_id in zip(
            self.spy.button_copies, self.spy.button_pointers, self.spy.button_ids
        ):
            # What the pointer holds now, for contrast: this is the buffer the label used to be
            # read from, and it is not the label.
            read_now = self._read_codepoints(read_u32, pointer) or []
            print(
                f"\nbutton {dialog_id}:\n"
                f"    copy (inside the call) = state {state}, {len(copied)} code units, "
                f"first {[hex(cp) for cp in copied[:8]]}\n"
                f"    the pointer now        = {[hex(cp) for cp in read_now[:8]]}"
            )
            self.assertEqual(
                state,
                int(EventTextState.COPIED),
                f"button {dialog_id}: the observer did not copy the announced label",
            )
            self.assertTrue(
                is_valid_enc_str(list(copied)),
                f"button {dialog_id}: the label the client announced is not an encoded "
                f"string, so there is nothing to decode: "
                f"{[hex(cp) for cp in copied[:8]]}",
            )
            label_index, label_key = string_table._parse_codepoints(tuple(copied))
            rendered_label = self._render(label_index, label_key)
            print(
                f"    the label it names      = index {label_index}, key 0x{label_key:X}, "
                f"text {rendered_label!r}"
            )

        # The captions the port itself reports: the label the client decoded for each button,
        # which is what the facade answers and what is on the screen in the client.
        for waited_buttons in range(int(DECODE_WAIT_S / POLL_S) + 1):
            buttons = dialog.PyDialog.get_active_dialog_buttons()
            if not any(button.message_decode_pending for button in buttons):
                break
            time.sleep(POLL_S)
        print("--- the buttons the module answers with ---")
        for button in dialog.PyDialog.get_active_dialog_buttons():
            print(
                f"    dialog id {button.dialog_id} (icon {button.button_icon}): "
                f"caption {button.message_decoded!r}, "
                f"pending={button.message_decode_pending}"
            )
        self.assertTrue(
            dialog.PyDialog.get_active_dialog_buttons(),
            "the client announced buttons and the module answers with none",
        )

        print(
            "the dialog the interaction opened is still up; press Escape in the client "
            "to close it. This test sent nothing but the interaction."
        )

    def test_z_the_journals_recorded_that_interaction(self) -> None:
        """The two journals, against the messages the client really sent.

        The interaction above is what fills them: the client announced a body and its buttons,
        the module captured them, and every one of those messages is a row here. A journal that
        answered from nothing would pass an offline test and fail this one.
        """

        logs = dialog.PyDialog.get_dialog_event_logs()
        received = dialog.PyDialog.get_dialog_event_logs_received()
        journal = dialog.PyDialog.get_dialog_callback_journal()

        # The text is the client's own decoder's answer, and it arrives asynchronously — the
        # module hands the string over and the client calls the stub back when it has decoded
        # it. So the run waits for that completion, bounded, and says how long it took.
        decode_waited = 0.0
        while decode_waited < DECODE_WAIT_S and dialog._body_decodes:
            time.sleep(POLL_S)
            decode_waited += POLL_S
        print(
            f"the client's decoder answered in {decode_waited:.2f}s "
            f"({len(dialog._body_decodes)} body decodes still in flight)"
        )
        journal = dialog.PyDialog.get_dialog_callback_journal()

        self._print_timeline()

        # What the module's own gate thinks, printed before anything is asserted: a journal
        # that is empty because the gate refused the message is a different finding from one
        # that is empty because the appender did not run.
        print(self._gate_report("--- the module's state after the interaction ---"))
        print(
            f"    captured agent / dialog = {dialog._dialog_agent_id} / {dialog._dialog_id} "
            f"(context {dialog._context_dialog_id})\n"
            f"    captured buttons        = {len(dialog._dialog_buttons)}\n"
            f"    shutdown requested      = {dialog._shutdown_requested}"
        )

        bodies = [row for row in logs if row.message_id == dialog.DIALOG_BODY_MESSAGE]
        buttons = [row for row in logs if row.message_id == dialog.DIALOG_BUTTON_MESSAGE]
        print(
            f"event log                 = {len(logs)} rows "
            f"({len(received)} received, "
            f"{len(dialog.PyDialog.get_dialog_event_logs_sent())} sent)\n"
            f"  bodies / buttons        = {len(bodies)} / {len(buttons)}\n"
            f"callback journal          = {len(journal)} rows: "
            f"{[row.event_type for row in journal]}\n"
            + "".join(
                f"    {row.event_type:<12} dialog_id={row.dialog_id} "
                f"context={row.context_dialog_id} agent={row.agent_id} "
                f"uid={row.npc_uid!r} text={row.text[:40]!r}\n"
                for row in journal[:6]
            )
        )

        self.assertTrue(bodies, "the client announced a body and the log did not record it")
        self.assertEqual(
            len(bodies) + len(buttons),
            len(logs),
            "only dialog messages are logged, and this run sent none",
        )
        self.assertEqual(len(received), len(logs))
        self.assertEqual(
            sorted({row.event_type for row in journal}),
            ["recv_body", "recv_choice"],
            "the body and the choices the client announced, and nothing else",
        )
        for row in journal:
            self.assertTrue(
                row.npc_uid.endswith(f":{row.agent_id}") if row.agent_id else row.npc_uid == "",
                f"the uid is built from the agent the row names: {row.npc_uid!r}",
            )

        # The gate the connection leaves: the module observed the live map at startup, so the
        # first message the client sends is captured rather than refused as a transition. This
        # is the live check for the ordering fix of 2026-09-25 (``ConnectedClient`` publishes
        # itself before this startup; ``tests/test_client_startup_offline.py`` pins the order).
        map_id, map_ready = dialog._map_state()
        self.assertFalse(
            dialog._callbacks_suspended,
            "the module was left suspended, so its map gate never opened",
        )
        self.assertEqual(dialog._last_observed_map_id, map_id)
        self.assertEqual(dialog._last_observed_map_ready, map_ready)

        # The body's text, which the module rendered for itself: the journal's row carries it
        # and the open dialog reports it. It is the same text this suite rendered from the same
        # codepoints by a different route (``string_table._parse_codepoints`` and
        # ``_decode_entry`` above), so the two are compared rather than one being trusted.
        body_rows = [row for row in journal if row.event_type == "recv_body"]
        self.assertEqual(len(body_rows), 1, "one body, one row")
        body_text = body_rows[0].text
        active = dialog.PyDialog.get_active_dialog()
        print(
            f"the module rendered the body as = {body_text!r}\n"
            f"the open dialog's raw message   = {active.raw_message!r}\n"
            f"the open dialog's message       = {active.message!r}"
        )
        self._print_body_samples()
        self.assertTrue(
            body_text,
            "the row the module appended from the client's own body message carries no text",
        )
        self.assertTrue(
            all(character.isprintable() or character in "\n\t" for character in body_text),
            f"the module's body text is not text: {body_text!r}",
        )
        if self.rendered_body:
            self.assertIn(
                self.rendered_body[:40],
                body_text,
                "the module's render and this test's render of the same codepoints disagree",
            )

        self.assertEqual(
            active.raw_message,
            body_text,
            "the open dialog keeps the body's own text, terminator and all, as native does",
        )
        self.assertTrue(active.message, "the sanitised message is what the facade reads")

    # -- helpers -----------------------------------------------------------

    def _print_timeline(self) -> None:
        """Print every dialog message the client sent, and every change of the module's gate.

        The spy is registered after the module's capture, so a row's ``suspended`` is the
        module's own verdict for that message: true means the message was refused. Rows are
        written when the gate changes and for every dialog message, which is the whole history
        of how the gate moved between the connection and the interaction.
        """

        if not self.spy.timeline:
            print("the client sent no dialog message this run")
            return
        first = self.spy.timeline[0][0]
        print("--- the module's gate, as every message left it ---")
        for at, sequence, suspended, tick, map_id, ready, is_dialog in self.spy.timeline:
            kind = ""
            if sequence == dialog.DIALOG_BODY_MESSAGE:
                kind = "  <-- dialog body"
            elif sequence == dialog.DIALOG_BUTTON_MESSAGE:
                kind = "  <-- dialog button"
            print(
                f"    {at - first:9.1f} ms  seq=0x{sequence:08X} "
                f"suspended={str(suspended):<5} observed={map_id}/{ready} "
                f"tick-first={tick - first:+.1f} ms{kind}"
            )

    def _print_body_samples(self) -> None:
        """Print what was at the announced body pointer each time it was looked at."""

        if not self.spy.body_samples:
            print("the client announced no body pointer this run")
            return
        first = self.spy.body_samples[0][0]
        print("--- the body pointer, sampled at each message the client sent ---")
        for at, words in self.spy.body_samples:
            print(f"    +{at - first:8.1f} ms  {[hex(word) for word in words]}")

    def _closest_npc(self, xy: tuple[float, float]) -> int:
        """Return the closest living NPC, as ``probe_dialog_open.py`` does."""

        snapshot = self.client.read_agent_array()
        if snapshot is None:
            return 0
        own_agent = int(Player.GetAgentID())
        best_id, best_distance = 0, 0.0
        read = 0
        for reference in snapshot.all:
            if reference.agent_id in (0, own_agent):
                continue
            if reference.allegiance in (None, AgentAllegiance.ENEMY):
                continue
            if not (reference.is_living or reference.is_gadget):
                continue
            if read >= SCAN_LIMIT:
                break
            read += 1
            try:
                record = self.client.read_agent(reference)
            except (OSError, RuntimeError):
                continue
            if record is None or not (record.is_living_type and not int(record.login_number)):
                continue
            distance = math.dist((float(record.pos.x), float(record.pos.y)), xy)
            if not best_id or distance < best_distance:
                best_id, best_distance = int(reference.agent_id), distance
        return best_id

    @staticmethod
    def _read_codepoints(read_u32: Any, address: int) -> list[int] | None:
        """Read a wide string's codepoints, stopping at the terminator."""

        if not address:
            return None
        codepoints: list[int] = []
        for index in range(CODEPOINT_LIMIT):
            value = read_u32(address + index * 2)
            if value is None:
                return None
            unit = int(value) & 0xFFFF
            codepoints.append(unit)
            if unit == 0:
                break
        return codepoints

    @staticmethod
    def _resolve(win32: Win32, pid: int, name: str) -> int:
        """Find one function the way every other read in this project does."""

        from py4gw.memory import ProcessMemoryReader
        from py4gw.scanner import PatternCatalog, RemoteScanner

        module = win32.get_main_module(pid)
        with ProcessMemoryReader(win32, pid) as reader:
            scanner = RemoteScanner(
                reader, int(module["base_address"]), int(module["size"])
            )
            scanner.initialize()
            catalog = PatternCatalog.from_directory("offsets")
            result = catalog.resolve(name, scanner)
        if not result.ok:
            raise AssertionError(f"pid {pid}: {name} did not resolve: {result.message}")
        return int(result.value)

    @staticmethod
    def _read_entry(win32: Win32, pid: int, address: int, size: int) -> bytes:
        """Read entry bytes through a fresh read-only handle."""

        from py4gw.memory import ProcessMemoryReader

        with ProcessMemoryReader(win32, pid) as reader:
            return reader.read(address, size)

    @staticmethod
    def _text_digest(win32: Win32, pid: int) -> tuple[str, int]:
        """Return a hash of the client's whole code section."""

        from py4gw.memory import ProcessMemoryReader
        from py4gw.scanner import RemoteScanner

        module = win32.get_main_module(pid)
        digest = hashlib.sha256()
        size = 0
        with ProcessMemoryReader(win32, pid) as reader:
            scanner = RemoteScanner(
                reader, int(module["base_address"]), int(module["size"])
            )
            scanner.initialize()
            section = scanner.get_section_range("text")
            address = section.start
            while address < section.end:
                chunk = min(TEXT_CHUNK, section.end - address)
                digest.update(reader.read(address, chunk))
                size += chunk
                address += chunk
        return digest.hexdigest(), size


if __name__ == "__main__":
    unittest.main(verbosity=2)
