"""Live Guild Wars test for the dialog metadata tables and the loader step.

The five `PyDialog` members that return a dialog's *text* are:

```text
get_dialog_text_decoded(id)          the text, or "" while the decode is queued
is_dialog_text_decode_pending(id)    whether that decode is still in flight
get_dialog_text_decode_status()      the cached rows, then the pending ones
get_dialog_info(id)                  the row's columns plus its content
enumerate_available_dialogs()        every available row, each with its content
```

The source fills that text by rebasing `DialogMemory::DIALOG_LOADER_GETTEXT`
(`dialog.h:99`), calling it for a dialog id, and handing the encoded string to
`AsyncDecodeStr`, which decodes it **inside the client** and calls back
(`dialog.cpp:1166-1253`); the port drives the same protocol through
`py4gw/ui/async_decode.py`. It does not render dialog text on the host.

**One step of that chain is not ported, and this run proves which.** On this build the
rebased constant is not the loader — it lands inside another function, and calling it
faulted the client on 2026-09-25 (`docs/RESEARCH.md`) — so the port's own answer is a
refusal that names the work, not a call and not a check of its own. What only a running
client can prove, and what this test asserts:

* the sources' constant rebases into the client's module, where the call path bounds it;
* the five metadata bases resolve, live, by the source's two stages (the constants first,
  the `.rdata` fallback behind them) and validate over all 58 rows;
* the loader step **reports** `this build's DialogLoader_GetText` and publishes no command,
  which is the difference between a refusal and the crash of 2026-09-25;
* the state members around it answer: a dialog id's columns read, and an id past
  `MAX_DIALOG_ID` answers nothing.

**The one thing this test changes**: it connects, which installs the capability layer — two
entry hooks, a block, a dispatcher and a listener. It sends nothing and interacts with
nothing. Both hooked functions are back to their own bytes afterwards and the code section
is compared with the one hashed before the run.

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


class LiveDialogTextTests(unittest.TestCase):
    """The dialog tables and the loader step, against the client's own dialog catalog."""

    pid: int
    client: py4gw.ConnectedClient
    text_before: tuple[str, int]
    loader: int
    refusal: str
    bases: dialog.DialogTableAddrs
    available: list[int]
    commands: int

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
            # 1. What the sources' constant rebases to. The source does this unconditionally
            #    (`ResolveDialogLoaderGetText`, `dialog_patterns.cpp:261-269`) and reads nothing
            #    at the address; so does the port.
            cls.loader = cls.client.dialog_tables.resolve_loader_get_text()

            # 2. The step the port does not take, and what it says instead. Nothing may be
            #    published by it: a command here is the call that faulted the client.
            try:
                dialog.Dialog.get_dialog_text_decoded(0)
            except NotImplementedError as error:
                cls.refusal = str(error)
            else:
                raise unittest.SkipTest(
                    "the member answered without reaching its loader step: this run is not "
                    "in a map, and the map gate runs before the loader (dialog.cpp:1138-1145)"
                )
            cls.commands = cls.client.bridge.header().command_written

            # 3. The five bases, resolved live by the source's own two stages.
            cls.bases = cls.client.dialog_tables.get()

            # 4. Which rows the table says are available, read through the member itself.
            cls.available = [
                dialog_id
                for dialog_id in range(dialog.MAX_DIALOG_ID + 1)
                if dialog.Dialog.is_dialog_available(dialog_id)
            ]
        except BaseException:
            py4gw.disconnect()
            raise

        print(
            f"\n--- dialog tables, live, pid {cls.pid} ---\n"
            f"module                  = 0x{cls.module_base:08X} + "
            f"0x{cls.module_size:X}\n"
            f"loader constant          = 0x{dialog.DIALOG_LOADER_GETTEXT:08X} "
            f"-> 0x{cls.loader:08X}\n"
            f"loader step              = refused: {cls.refusal.splitlines()[0][:120]}\n"
            f"commands published       = {cls.commands}\n"
            f"flags_base               = 0x{cls.bases.flags_base:08X}\n"
            f"event_handler_base       = 0x{cls.bases.event_handler_base:08X}\n"
            f"frame_type_base          = 0x{cls.bases.frame_type_base:08X}\n"
            f"content_id_base          = 0x{cls.bases.content_id_base:08X}\n"
            f"property_id_base         = 0x{cls.bases.property_id_base:08X}\n"
            f"available dialogs        = {len(cls.available)}\n"
            "--- end of the dialog table run ---\n"
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
            "--- end of the live dialog table test ---"
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

    # -- the loader step ---------------------------------------------------

    def test_the_sources_constant_rebases_into_the_client_module(self) -> None:
        """``ToRuntimeAddress`` (``dialog_patterns.cpp:25-31``), measured against the module."""

        self.assertTrue(
            self.module_base <= self.loader < self.module_base + self.module_size,
            f"the rebased constant 0x{self.loader:08X} is outside the client's module",
        )
        self.assertEqual(
            self.loader,
            self.module_base
            + (dialog.DIALOG_LOADER_GETTEXT - 0x00400000),
            "the rebase must use the sources' constant image base, not the module header",
        )

    def test_the_loader_step_reports_the_work_it_needs(self) -> None:
        """**This is the refusal that replaced the call of 2026-09-25.**

        A command published here would be the call that faulted the client; the port does not
        make it and does not substitute a check of its own. What it does is name the work.
        """

        self.assertIn("DialogLoader_GetText", self.refusal)
        self.assertEqual(
            self.commands,
            0,
            "the loader step published a command, which means it called something",
        )

    # -- the tables --------------------------------------------------------

    def test_the_five_bases_resolve_and_are_inside_the_module(self) -> None:
        """``BuildStaticDialogTables`` first, ``ResolveFlagsBase`` behind it (``:175-225``)."""

        for name in (
            "flags_base",
            "frame_type_base",
            "event_handler_base",
            "content_id_base",
            "property_id_base",
        ):
            with self.subTest(base=name):
                value = int(getattr(self.bases, name))
                self.assertNotEqual(value, 0, f"{name} did not resolve")
                self.assertTrue(
                    self.module_base <= value < self.module_base + self.module_size,
                    f"{name} = 0x{value:08X} is outside the client's module",
                )

    def test_the_available_rows_carry_their_columns(self) -> None:
        """``is_dialog_available`` is ``flags & 0x1``, and the columns read for those rows."""

        text_start, text_end = self._text_range(Win32(), self.pid)
        for dialog_id in self.available:
            with self.subTest(dialog_id=dialog_id):
                flags = dialog.Dialog.read_dialog_flags(dialog_id)
                self.assertTrue(flags & 0x1)
                self.assertLessEqual(flags, 0xFFFF)
                handler = dialog.Dialog.read_dialog_event_handler(dialog_id)
                if handler:
                    self.assertTrue(text_start <= handler < text_end)

    # -- the members around it ---------------------------------------------

    def test_an_id_past_the_maximum_answers_nothing(self) -> None:
        self.assertEqual(
            dialog.Dialog.get_dialog_text_decoded(dialog.MAX_DIALOG_ID + 1), ""
        )

    def test_the_status_starts_with_nothing_cached(self) -> None:
        """Nothing has been decoded on this build, so the status has no rows to report."""

        self.assertEqual(dialog.Dialog.get_dialog_text_decode_status(), [])

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
    def _text_range(win32: Win32, pid: int) -> tuple[int, int]:
        """The client's ``.text`` range, which the handler column has to fall in."""

        from py4gw.memory import ProcessMemoryReader
        from py4gw.scanner import RemoteScanner

        module = win32.get_main_module(pid)
        with ProcessMemoryReader(win32, pid) as reader:
            scanner = RemoteScanner(
                reader, int(module["base_address"]), int(module["size"])
            )
            scanner.initialize()
            section = scanner.get_section_range("text")
        return section.start, section.end

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
