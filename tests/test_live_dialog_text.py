"""Live Guild Wars test for the dialog text members.

Five members of ``PyDialog`` exist to return a dialog's text:

```text
get_dialog_text_decoded(id)          the text, or "" while the decode is queued
is_dialog_text_decode_pending(id)    whether that decode is still in flight
get_dialog_text_decode_status()      the cached rows, then the pending ones
get_dialog_info(id)                  the row's columns plus its content
enumerate_available_dialogs()        every available row, each with its content
```

The source fills the text by calling the client's ``DialogLoader_GetText`` for a dialog id and
handing the encoded string to ``AsyncDecodeStr``, which decodes it in the client and calls back.
This port calls the same loader through the capability layer and renders the string on the host
with the game's own string table (``py4gw/dat_reader.py`` + ``py4gw/internals/string_table.py``).

**What only a running client can prove**, and what this test asserts: the loader resolves and
answers for a real dialog id, the members' two-call contract holds against it (empty on the call
that queues, text on the next), and the text the port renders is readable.

**The one thing this test changes**: it connects, which installs the capability layer — two entry
hooks, a block, a dispatcher and a listener. It sends nothing and interacts with nothing. Both
hooked functions are back to their own bytes afterwards and the code section is compared with the
one hashed before the run.

Run it from an **elevated** shell, in a map, with Guild Wars running::

    python -m unittest tests.test_live_dialog_text -v
"""

from __future__ import annotations

import hashlib
import unittest

import py4gw
from py4gw import dialog
from py4gw.win32 import Win32

HOOK_RESOLVER = "game_thread.leave_game_thread_func"
OBSERVE_RESOLVER = "ui.send_ui_message_func"
HOOK_ENTRY = bytes.fromhex("55 8B EC 81 EC 20 02 00 00")
OBSERVE_ENTRY = bytes.fromhex("55 8B EC 8B 45 08 83 F8 56")

TEXT_CHUNK = 0x10000

#: How many ids the second pass reports text for before the test stops printing.
PRINTED = 6


class LiveDialogTextTests(unittest.TestCase):
    """The five text members, against the client's own dialog catalog."""

    pid: int
    client: py4gw.ConnectedClient
    text_before: tuple[str, int]
    first: list[dialog.DialogInfo]
    second: list[dialog.DialogInfo]

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
        for name, address, expected in (
            (HOOK_RESOLVER, cls.hook_address, HOOK_ENTRY),
            (OBSERVE_RESOLVER, cls.observe_address, OBSERVE_ENTRY),
        ):
            observed = cls._read_entry(win32, cls.pid, address, len(expected))
            if observed != expected:
                raise AssertionError(
                    f"pid {cls.pid}: {name} at 0x{address:08X} holds "
                    f"{observed.hex(' ')}, not {expected.hex(' ')}. Nothing was written."
                )
        cls.text_before = cls._text_digest(win32, cls.pid)

        cls.client = py4gw.connect(clients[0])
        try:
            # The loader's address is a hardcoded client virtual address, and on this build the
            # constant the sources carry does not point at a function entry — calling it crashed
            # the client once (docs/RESEARCH.md, 2026-09-25). The port confirms the candidate's
            # bytes before it hands the address out, so this is 0 when it cannot be confirmed,
            # and the members then answer the source's own "no loader" value.
            cls.loader = cls.client.dialog_tables.resolve_loader_get_text()
            cls.first = dialog.PyDialog.enumerate_available_dialogs()
            cls.second = dialog.PyDialog.enumerate_available_dialogs()
            cls.commands = cls.client.bridge.header().command_written
        except BaseException:
            py4gw.disconnect()
            raise

        with_text = [row for row in cls.second if row.content]
        print(
            f"\n--- dialog text, live, pid {cls.pid} ---\n"
            f"module                  = 0x{cls.module_base:08X} + "
            f"0x{cls.module_size:X}\n"
            f"DialogLoader_GetText    = "
            + (f"0x{cls.loader:08X} (confirmed as a function entry)" if cls.loader
               else "refused: the rebased constant does not begin a function on this build")
            + f"\navailable dialogs       = {len(cls.first)}\n"
            f"first pass with text    = "
            f"{sum(1 for row in cls.first if row.content)}\n"
            f"second pass with text   = {len(with_text)}\n"
            f"commands published      = {cls.commands}\n"
            + "".join(
                f"    {row.dialog_id:>3}  flags=0x{row.flags:04X}  "
                f"event_handler=0x{row.event_handler:08X}  {row.content[:60]!r}\n"
                for row in with_text[:PRINTED]
            )
            + "--- end of the text run ---\n"
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
            f"game-thread entry after = {hook_after.hex(' ')}\n"
            f"message entry after     = {observe_after.hex(' ')}\n"
            f"code section before     = {cls.text_before[0][:32]}... "
            f"({cls.text_before[1]} bytes)\n"
            f"code section after      = {text_after[0][:32]}... "
            f"({text_after[1]} bytes)\n"
            "--- end of the live dialog text test ---"
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

    # -- the members -------------------------------------------------------

    def _require_loader(self) -> int:
        """Skip the text assertions when this build's loader address cannot be confirmed."""

        if not self.loader:
            raise unittest.SkipTest(
                "the rebased DialogLoader_GetText constant does not begin a function on this "
                "build, so the port refuses it and the members have no text to fetch; the "
                "confirmation and the refusal are asserted in the two tests before this one"
            )
        return self.loader

    def test_a_refused_loader_means_nothing_is_called(self) -> None:
        """The check that the crash added: an unconfirmed address is never called.

        The refusal path is ``QueueDialogTextDecode``'s own: with no loader it caches empty text
        and clears the pending flag (``dialog.cpp:1166-1177``). If the port had called the
        rebased constant anyway, a command would have been published — and on 2026-09-25 that
        is exactly what faulted the client.
        """

        if self.loader:
            self.assertGreater(
                self.commands, 0, "a confirmed loader is called for every queued dialog"
            )
            return

        self.assertEqual(
            self.commands, 0, "a refused loader must not produce a single command"
        )
        self.assertTrue(
            all(row.content == "" for row in self.second),
            "with no loader every dialog's content is empty, which is the source's answer",
        )
        raise unittest.SkipTest(
            "DialogLoader_GetText is refused on this build, so no text can be fetched; the "
            "refusal and its consequence are what this run proves"
        )

    def test_the_loader_resolves_for_this_build(self) -> None:
        loader = self._require_loader()
        self.assertTrue(
            self.module_base <= loader < self.module_base + self.module_size,
            "the loader must be inside the client's module, which is what the call path bounds",
        )

    def test_the_first_pass_queues_and_the_second_carries_the_text(self) -> None:
        """The source's own contract: "" on the call that queues, text on the next."""

        self._require_loader()
        self.assertTrue(self.first, "no dialog is available in this client")
        for row in self.first:
            with self.subTest(dialog_id=row.dialog_id):
                self.assertEqual(row.content, "", "the first pass queues, so it has no text")

        with_text = [row for row in self.second if row.content]
        self.assertTrue(
            with_text,
            "the second pass reported no text for any of the "
            f"{len(self.second)} available dialogs",
        )

    def test_the_reported_text_is_readable(self) -> None:
        self._require_loader()
        for row in self.second:
            if not row.content:
                continue
            with self.subTest(dialog_id=row.dialog_id):
                self.assertTrue(
                    all(
                        character.isprintable() or character in "\n\t"
                        for character in row.content
                    ),
                    f"dialog {row.dialog_id} rendered to {row.content!r}",
                )

    def test_the_columns_are_read_for_every_available_row(self) -> None:
        """``is_dialog_available`` is ``flags & 0x1``, so every row must carry it."""

        for row in self.second:
            with self.subTest(dialog_id=row.dialog_id):
                self.assertTrue(row.flags & 0x1)
                self.assertLessEqual(row.dialog_id, dialog.MAX_DIALOG_ID)

    def test_the_status_reports_what_was_cached(self) -> None:
        status = dialog.PyDialog.get_dialog_text_decode_status()

        cached = {row.dialog_id for row in status if not row.pending}
        self.assertTrue(cached, "nothing was reported as cached after two passes")
        self.assertTrue(
            cached <= {row.dialog_id for row in self.second},
            "the cache holds ids the enumeration did not return",
        )

    def test_a_decoded_id_is_not_pending(self) -> None:
        """The render happens in the call that queues, so the flag is down afterwards."""

        self._require_loader()
        for row in self.second:
            if not row.content:
                continue
            with self.subTest(dialog_id=row.dialog_id):
                self.assertFalse(
                    dialog.PyDialog.is_dialog_text_decode_pending(row.dialog_id)
                )
                self.assertEqual(
                    dialog.PyDialog.get_dialog_text_decoded(row.dialog_id), row.content
                )

    def test_an_id_past_the_maximum_answers_nothing(self) -> None:
        self.assertEqual(
            dialog.PyDialog.get_dialog_text_decoded(dialog.MAX_DIALOG_ID + 1), ""
        )

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _resolve(win32: Win32, pid: int, name: str) -> int:
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
        from py4gw.memory import ProcessMemoryReader

        with ProcessMemoryReader(win32, pid) as reader:
            return reader.read(address, size)

    @staticmethod
    def _text_digest(win32: Win32, pid: int) -> tuple[str, int]:
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
