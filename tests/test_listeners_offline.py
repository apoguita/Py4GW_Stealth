"""Offline tests for the merchant listener and the packet hooks under it.

Two layers, both driven without a client:

* **``py4gw/game_thread/packets.py``** — the walk from ``stoc.handler_table_addr`` to the client's
  handler array, and the replacement of one entry per watched header. The walk is exercised against
  a synthetic client memory laid out exactly as ``stoc.cpp`` describes it (a ``GameServer*`` at the
  resolved address, ``gs_codec`` at ``+0x8``, ``handlers`` at ``+0x2C``, a ``GW::GWArray`` of
  ``{template, field_count, handler_func}``), and the replacement against a bridge stand-in that
  records the ``WRITE_MEMORY`` commands and the allocations.
* **``py4gw/listeners.py``** — ``MerchantListener``'s five pieces of state, its four handlers, the
  one-second window throttle, the client-array latch, and the enable/disable lifecycle native's
  ``Listener`` base defines.

What this file cannot show is that the client's own array is where this project thinks it is: that is
the probe's job (``tests/probe_stoc_handlers.py``, which read it live and read-only) and the live
run's.
"""

from __future__ import annotations

import ctypes
import struct
import unittest
from typing import Any
from unittest import mock

from py4gw.game_thread.packets import (
    ARRAY_BUFFER_OFFSET,
    ARRAY_CAPACITY_OFFSET,
    ARRAY_SIZE,
    ARRAY_SIZE_OFFSET,
    CODEC_HANDLERS_OFFSET,
    ENTRY_FIELD_COUNT_OFFSET,
    ENTRY_HANDLER_OFFSET,
    ENTRY_SIZE,
    GAME_SERVER_CODEC_OFFSET,
    PACKET_INFLIGHT_OFFSET,
    PACKET_POINTER_OFFSET,
    PacketHooks,
    read_handler_table,
)
from py4gw.game_thread.shared_block import CommandRecord, CommandState, Operation
from py4gw.listeners import (
    BUY_TAB,
    GAME_SMSG_ITEM_PRICE_QUOTE,
    GAME_SMSG_TRANSACTION_DONE,
    GAME_SMSG_WINDOW_ADD_ITEMS,
    GAME_SMSG_WINDOW_ITEMS_END,
    GAME_SMSG_WINDOW_ITEM_STREAM_END,
    PACKET_WORDS,
    WINDOW_ITEM_THROTTLE_MS,
    Listener,
    Merchant,
    MerchantListener,
)

#: The client's own handler array, as the live probe measured it: ``GameServer`` at ``0x1D6BC90``,
#: the codec at ``0x1D63388``, 487 entries in a 504-slot array. The numbers here are this test's own
#: but the shape is that one's — and the count is above every merchant header (``0x84``-``0xF7``),
#: because a header past the array is refused rather than replaced (``stoc_methods.cpp:55``).
GAME_SERVER = 0x00B00000
CODEC = 0x00B10000
ENTRY_COUNT = 0x200
ENTRY_CAPACITY = 0x220
BUFFER = 0x00B20000
RESOLVED = 0x00A00000

#: What each header's entry holds, so a replacement can be told from an original.
ORIGINAL_HANDLER = 0x00F00000


class FakeMemory:
    """A flat target address space, read and written through the same two calls a client is."""

    def __init__(self) -> None:
        #: Wide enough to hold the whole claimed module range as well as the structures this file
        #: lays out, because the recovery reads the *bytes* at a recovered handler address to check
        #: that it is a function's entry.
        self.raw = bytearray(0x600000)
        self.base = 0x00A00000

    def read(self, address: int, size: int) -> bytes:
        offset = address - self.base
        if offset < 0 or offset + size > len(self.raw):
            raise OSError(f"read at 0x{address:08X} is outside this test's memory")
        return bytes(self.raw[offset : offset + size])

    def write(self, address: int, data: bytes) -> None:
        offset = address - self.base
        if offset < 0 or offset + len(data) > len(self.raw):
            raise OSError(f"write at 0x{address:08X} is outside this test's memory")
        self.raw[offset : offset + len(data)] = data

    def u32(self, address: int) -> int:
        return int(struct.unpack("<I", self.read(address, 4))[0])

    def put_u32(self, address: int, value: int) -> None:
        self.write(address, struct.pack("<I", value))


class FakeAccess:
    """The transport: a flat memory, plus the code allocations the stubs are placed in."""

    def __init__(self, memory: FakeMemory) -> None:
        self.memory = memory
        self.allocations: dict[int, bytes] = {}
        self.protections: list[tuple[int, int, int]] = []
        self.freed: list[int] = []
        self._next = 0x00C00000

    def read(self, address: int, size: int) -> bytes:
        return self.memory.read(address, size)

    def write(self, address: int, data: bytes) -> None:
        self.memory.write(address, data)
        if address in self.allocations:
            self.allocations[address] = bytes(data)

    def allocate(self, size: int) -> int:
        address = self._next
        self._next += max(size, 16)
        self.allocations[address] = b""
        return address

    def free(self, address: int) -> None:
        self.freed.append(address)
        self.allocations.pop(address, None)

    def protect(self, address: int, size: int, protection: int) -> int:
        self.protections.append((address, size, protection))
        return protection

    def flush_instruction_cache(self, address: int, size: int) -> None:
        return None


class FakeBridge:
    """The bridge stand-in: the block address, the write path, and what was submitted."""

    REGION_BASE = 0x00D00000

    #: The client module, which is where the client's own handlers live. The originals this file
    #: lays down (``ORIGINAL_HANDLER`` upward) are inside it, as the probe measured the real ones.
    MODULE_RANGE = (0x00F00000, 0x00100000)

    def __init__(self, access: FakeAccess, block: int = 0x00E00000) -> None:
        self.access = access
        self.block_address = block
        self.data: dict[int, bytes] = {}
        self.submitted: list[tuple[int, int, int, int]] = []
        self.complete = True

    @property
    def module_range(self) -> tuple[int, int]:
        return self.MODULE_RANGE

    #: Every other module loaded in the client. Empty by default, so a pointer outside the client module is
    #: memory no module covers — a controller's own stub — which is the refusal the tests below drive. A
    #: test that wants the *other* answer — another runtime's compiled handler — sets this.
    loaded_modules: tuple[tuple[int, int], ...] = ()

    def write_data(self, offset: int, payload: bytes) -> int:
        address = self.REGION_BASE + int(offset)
        self.access.write(address, payload)
        self.data[int(offset)] = bytes(payload)
        return address

    def submit(
        self,
        operation: Operation | int,
        arg0: int = 0,
        arg1: int = 0,
        arg2: int = 0,
        arg3: int = 0,
        arg4: int = 0,
        arg5: int = 0,
        timeout_ms: int | None = None,
    ) -> CommandRecord:
        self.submitted.append((int(operation), int(arg0), int(arg1), int(arg2)))
        if int(operation) == int(Operation.WRITE_MEMORY) and self.complete:
            source = self.REGION_BASE + int(arg1)
            self.access.write(int(arg0), self.access.read(source, int(arg2)))
        return CommandRecord(
            sequence=1,
            operation=int(operation),
            state=CommandState.DONE if self.complete else CommandState.FAILED,
        )


def build_client_memory() -> FakeMemory:
    """Lay out native's chain exactly as ``stoc.cpp`` and ``gw_array.h`` describe it."""

    memory = FakeMemory()
    memory.put_u32(RESOLVED, GAME_SERVER)
    memory.put_u32(GAME_SERVER + GAME_SERVER_CODEC_OFFSET, CODEC)
    handlers = CODEC + CODEC_HANDLERS_OFFSET
    memory.put_u32(handlers + ARRAY_BUFFER_OFFSET, BUFFER)
    memory.put_u32(handlers + ARRAY_CAPACITY_OFFSET, ENTRY_CAPACITY)
    memory.put_u32(handlers + ARRAY_SIZE_OFFSET, ENTRY_COUNT)
    for header in range(ENTRY_COUNT):
        entry = BUFFER + header * ENTRY_SIZE
        memory.put_u32(entry, 0x00F10000 + header)
        memory.put_u32(entry + ENTRY_FIELD_COUNT_OFFSET, 3)
        memory.put_u32(entry + ENTRY_HANDLER_OFFSET, ORIGINAL_HANDLER + header * 0x10)
        # A function's entry on this build: the recovery reads these two bytes at an address it
        # recovered before it will write it back as a handler.
        memory.write(ORIGINAL_HANDLER + header * 0x10, b"\x55\x8b\xec")
    return memory


class HandlerTableTests(unittest.TestCase):
    """The walk to the client's handler array, on the layout the probe measured."""

    def setUp(self) -> None:
        self.memory = build_client_memory()
        self.access = FakeAccess(self.memory)

    def test_the_walk_reaches_the_array_native_reads(self) -> None:
        table = read_handler_table(self.access, RESOLVED)  # type: ignore[arg-type]

        self.assertEqual(table.address, CODEC + CODEC_HANDLERS_OFFSET)
        self.assertEqual(table.buffer, BUFFER)
        self.assertEqual(table.capacity, ENTRY_CAPACITY)
        self.assertEqual(table.size, ENTRY_COUNT)

    def test_one_entry_is_where_the_handler_is(self) -> None:
        table = read_handler_table(self.access, RESOLVED)  # type: ignore[arg-type]

        self.assertEqual(table.entry(7), BUFFER + 7 * ENTRY_SIZE)
        self.assertEqual(table.handler(7), BUFFER + 7 * ENTRY_SIZE + ENTRY_HANDLER_OFFSET)
        self.assertEqual(
            self.memory.u32(table.handler(7)), ORIGINAL_HANDLER + 7 * 0x10
        )

    def test_a_header_past_the_array_is_refused(self) -> None:
        """Native checks the same bound before it writes (``stoc_methods.cpp:55``)."""

        table = read_handler_table(self.access, RESOLVED)  # type: ignore[arg-type]

        for header in (ENTRY_COUNT, ENTRY_COUNT + 1, 0xFFFF):
            with self.subTest(header=header):
                with self.assertRaises(ValueError) as caught:
                    table.entry(header)
                self.assertIn(str(ENTRY_COUNT), str(caught.exception))

    def test_each_step_of_the_walk_refuses_on_its_own(self) -> None:
        """A null server, a null codec and an array with no buffer are three different failures."""

        cases = (
            (RESOLVED, 0, "game server"),
            (GAME_SERVER + GAME_SERVER_CODEC_OFFSET, 0, "codec"),
            (CODEC + CODEC_HANDLERS_OFFSET + ARRAY_BUFFER_OFFSET, 0, "buffer"),
        )
        for address, value, phrase in cases:
            with self.subTest(address=hex(address)):
                memory = build_client_memory()
                memory.put_u32(address, value)
                access = FakeAccess(memory)

                with self.assertRaises(RuntimeError) as caught:
                    read_handler_table(access, RESOLVED)  # type: ignore[arg-type]

                self.assertIn(phrase, str(caught.exception))

    def test_an_address_that_resolves_to_nothing_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            read_handler_table(self.access, 0)  # type: ignore[arg-type]


class PacketHooksTests(unittest.TestCase):
    """Replacing entries, and putting them back."""

    HEADERS = {
        GAME_SMSG_WINDOW_ADD_ITEMS: 18,
        GAME_SMSG_WINDOW_ITEMS_END: 1,
        GAME_SMSG_WINDOW_ITEM_STREAM_END: 2,
        GAME_SMSG_TRANSACTION_DONE: 1,
        GAME_SMSG_ITEM_PRICE_QUOTE: 3,
    }

    def setUp(self) -> None:
        self.memory = build_client_memory()
        self.access = FakeAccess(self.memory)
        self.bridge = FakeBridge(self.access)
        self.hooks = PacketHooks(self.bridge)  # type: ignore[arg-type]

    def install(self) -> tuple[Any, ...]:
        return self.hooks.install(RESOLVED, self.HEADERS)

    def entry_handler(self, header: int) -> int:
        entry = CODEC + CODEC_HANDLERS_OFFSET
        return self.memory.u32(BUFFER + header * ENTRY_SIZE + ENTRY_HANDLER_OFFSET)

    def test_every_watched_header_points_at_this_projects_code(self) -> None:
        placed = self.install()

        self.assertEqual(len(placed), len(self.HEADERS))
        self.assertEqual(self.hooks.headers, tuple(sorted(self.HEADERS)))
        for header in self.HEADERS:
            with self.subTest(header=hex(header)):
                self.assertNotEqual(
                    self.entry_handler(header), ORIGINAL_HANDLER + header * 0x10
                )
                self.assertIn(self.entry_handler(header), self.access.allocations)

    def test_a_header_that_was_not_asked_for_keeps_its_own_handler(self) -> None:
        self.install()

        self.assertEqual(self.entry_handler(0x20), ORIGINAL_HANDLER + 0x20 * 0x10)

    def test_the_stub_is_the_one_that_header_needs(self) -> None:
        """Each stub is built for its own header and word count, and its own original."""

        self.install()

        for header, words in self.HEADERS.items():
            with self.subTest(header=hex(header)):
                stub = self.hooks.stub(header)
                code = self.access.allocations[stub.address]
                self.assertEqual(stub.words, words)
                self.assertEqual(stub.original, ORIGINAL_HANDLER + header * 0x10)
                self.assertIn(struct.pack("<I", header), code)
                self.assertIn(struct.pack("<I", stub.original), code)

    def test_the_replacement_is_written_on_the_game_thread(self) -> None:
        """The pointer travels through the block and the payload's ``WRITE_MEMORY``."""

        self.install()

        self.assertTrue(self.bridge.submitted, "the entries were written through the payload")
        entries = {stub.entry for stub in self.hooks._stubs.values()}
        for operation, target, source, size in self.bridge.submitted:
            with self.subTest(target=hex(target)):
                self.assertEqual(operation, int(Operation.WRITE_MEMORY))
                self.assertEqual(size, 4)
                self.assertEqual(
                    source,
                    PACKET_POINTER_OFFSET,
                    "the pointer is staged in the block's data region",
                )
                self.assertIn(target, entries)

    def test_the_in_flight_word_is_placed_before_the_stubs(self) -> None:
        self.install()

        self.assertIn(PACKET_INFLIGHT_OFFSET, self.bridge.data)
        self.assertIn(PACKET_POINTER_OFFSET, self.bridge.data)
        self.assertEqual(self.hooks.in_flight(), 0)

    def test_removing_puts_every_handler_back(self) -> None:
        self.install()

        restored = self.hooks.remove()

        self.assertEqual(restored, tuple(sorted(self.HEADERS)))
        self.assertEqual(self.hooks.headers, ())
        for header in self.HEADERS:
            with self.subTest(header=hex(header)):
                self.assertEqual(
                    self.entry_handler(header), ORIGINAL_HANDLER + header * 0x10
                )

    def test_removing_frees_the_code_only_when_asked(self) -> None:
        self.install()

        self.hooks.remove()

        self.assertEqual(self.access.freed, [], "a plain remove leaves the code mapped")

        self.hooks.install(RESOLVED, self.HEADERS)
        addresses = [stub.address for stub in self.hooks._stubs.values()]

        self.hooks.remove(free_code=True)

        self.assertEqual(sorted(self.access.freed), sorted(addresses))
        for address in addresses:
            self.assertNotIn(address, self.access.allocations)

    def test_freeing_waits_for_a_stub_that_is_still_running(self) -> None:
        """A count that does not drain is reported, and nothing is freed.

        The entries are back either way — that part does not wait on anything — and the stubs stay
        tracked, so a later ``remove(free_code=True)`` can try again.
        """

        self.install()
        self.hooks._inflight_address = self.bridge.REGION_BASE + PACKET_INFLIGHT_OFFSET
        self.access.write(self.hooks._inflight_address, struct.pack("<I", 1))

        with mock.patch("py4gw.game_thread.packets.FREE_WAIT_SECONDS", 0.01):
            with self.assertRaises(RuntimeError) as caught:
                self.hooks.remove(free_code=True)

        self.assertIn("still running", str(caught.exception))
        self.assertEqual(self.access.freed, [])
        for header in self.HEADERS:
            with self.subTest(header=hex(header)):
                self.assertEqual(
                    self.entry_handler(header),
                    ORIGINAL_HANDLER + header * 0x10,
                    "the client's own handler is back even though nothing was freed",
                )
        self.assertEqual(self.hooks.headers, tuple(sorted(self.HEADERS)))

    def test_a_header_past_the_array_is_refused_before_anything_is_written(self) -> None:
        with self.assertRaises(ValueError):
            self.hooks.install(RESOLVED, {ENTRY_COUNT + 5: 3})

        self.assertEqual(self.bridge.submitted, [])
        self.assertEqual(self.access.allocations, {})
        self.assertEqual(self.entry_handler(0), ORIGINAL_HANDLER)

    def test_an_entry_with_no_handler_to_chain_to_is_refused(self) -> None:
        """A stub that could not chain would stop the client handling that packet."""

        entry = BUFFER + GAME_SMSG_ITEM_PRICE_QUOTE * ENTRY_SIZE + ENTRY_HANDLER_OFFSET
        self.memory.put_u32(entry, 0)

        with self.assertRaises(RuntimeError) as caught:
            self.install()

        self.assertIn("chain", str(caught.exception))
        self.assertEqual(self.entry_handler(0), ORIGINAL_HANDLER, "nothing was replaced")
        self.assertEqual(self.hooks.headers, ())

    def test_a_handler_outside_the_client_module_is_refused(self) -> None:
        """This project's own recovery discipline: never chain to a pointer nobody owns.

        Native snapshots whatever the array holds, which is safe in a runtime that injected itself
        into a fresh process. A controller here can attach to a client that outlived one that died,
        and that pointer would be a jump into memory it no longer owns — on the client's own thread,
        on the next packet of that header. What is refused here is memory **no loaded module covers**,
        which is exactly where a dead controller's stubs are left.
        """

        entry = BUFFER + GAME_SMSG_ITEM_PRICE_QUOTE * ENTRY_SIZE + ENTRY_HANDLER_OFFSET
        outside = FakeBridge.MODULE_RANGE[0] + FakeBridge.MODULE_RANGE[1] + 0x100
        self.memory.put_u32(entry, outside)

        with self.assertRaises(RuntimeError) as caught:
            self.install()

        self.assertIn("no loaded module covers", str(caught.exception))
        self.assertIn(f"0x{outside:08X}", str(caught.exception))
        self.assertEqual(self.entry_handler(0), ORIGINAL_HANDLER, "nothing was replaced")
        self.assertEqual(self.hooks.headers, ())
        self.assertEqual(
            self.access.allocations, {}, "the stubs placed before the refusal went with it"
        )

    def test_a_handler_inside_another_loaded_module_is_chained_to(self) -> None:
        """The measured live shape: Reforged's own ``StoCHandler_Func`` lives in ``Py4GW.dll``.

        Its packet sniffer registers **all 488** headers (``packet_sniffer.cpp:129-135``), so every header
        this project wants is one of its handlers — and refusing those entries would make the merchant
        listener impossible on the arrangement the owner needs, Reforged first and this library second.
        A handler inside a *loaded module* is code that is still there; the stub chains to it exactly as it
        chains to one of the client's own, and the restore puts the pointer back.
        """

        entry = BUFFER + GAME_SMSG_ITEM_PRICE_QUOTE * ENTRY_SIZE + ENTRY_HANDLER_OFFSET
        theirs = FakeBridge.MODULE_RANGE[0] + FakeBridge.MODULE_RANGE[1] + 0x100
        self.memory.put_u32(entry, theirs)
        self.bridge.loaded_modules = ((theirs & 0xFFFF0000, 0x10000),)

        placed = self.install()

        self.assertEqual(len(placed), len(self.HEADERS))
        chained = {stub.header: stub.original for stub in placed}
        self.assertEqual(
            chained[GAME_SMSG_ITEM_PRICE_QUOTE],
            theirs,
            "the other runtime's handler is what that header's stub chains to",
        )
        self.assertNotEqual(
            self.entry_handler(GAME_SMSG_ITEM_PRICE_QUOTE),
            theirs,
            "and the entry holds this project's own stub now",
        )

        self.hooks.remove(free_code=False)

        self.assertEqual(
            self.entry_handler(GAME_SMSG_ITEM_PRICE_QUOTE),
            theirs,
            "which the restore puts back",
        )
        for header in self.HEADERS:
            if header == GAME_SMSG_ITEM_PRICE_QUOTE:
                continue
            with self.subTest(header=hex(header)):
                self.assertEqual(
                    self.entry_handler(header), ORIGINAL_HANDLER + header * 0x10
                )

    def test_an_orphaned_stub_of_this_projects_is_repaired_from_itself(self) -> None:
        """A controller's own stub says what it replaced, so the entry is put back and the install runs.

        This is the state a killed controller leaves: the entry points at emitted code whose block and
        whose owner are gone. The original is still written down **inside that stub** — as the
        immediate of the ``mov eax`` it chains through — so the recovery reads it back instead of
        asking the host to guess.
        """

        header = GAME_SMSG_ITEM_PRICE_QUOTE
        entry = BUFFER + header * ENTRY_SIZE + ENTRY_HANDLER_OFFSET
        orphan = 0x00C50000
        chained = ORIGINAL_HANDLER + header * 0x10
        stub = (
            bytes((0x60, 0xFF, 0x05))
            + struct.pack("<I", 0x00E00100)
            + bytes((0xBB,))
            + struct.pack("<I", 0x00E00000)
            + bytes((0x61, 0xFF, 0x74, 0x24, 0x04, 0xB8))
            + struct.pack("<I", chained)
            + bytes((0xFF, 0xD0))
            + bytes((0xB8, 0x01, 0x00, 0x00, 0x00, 0xC3))
        )
        self.access.write(orphan, stub)
        self.memory.put_u32(entry, orphan)

        placed = self.install()

        self.assertEqual(len(placed), len(self.HEADERS))
        stub_of_header = self.hooks.stub(header)
        self.assertEqual(stub_of_header.original, chained, "the original came back out of the stub")
        self.assertEqual(stub_of_header.repaired_from, orphan)
        self.assertNotEqual(self.entry_handler(header), orphan)
        self.assertEqual(self.entry_handler(header), stub_of_header.address)

    def test_a_stub_that_says_nothing_is_refused_rather_than_guessed(self) -> None:
        """Emitted code that is not ours, or one whose immediate is not a function, is refused."""

        header = GAME_SMSG_ITEM_PRICE_QUOTE
        entry = BUFFER + header * ENTRY_SIZE + ENTRY_HANDLER_OFFSET
        orphan = 0x00C60000
        # Ours by its opening, but the address it chains to is outside the module.
        self.access.write(
            orphan,
            bytes((0x60, 0xFF, 0x05))
            + struct.pack("<I", 0x00E00100)
            + bytes((0xBB,))
            + struct.pack("<I", 0x00E00000)
            + bytes((0xB8,))
            + struct.pack("<I", 0x30000000)
            + bytes((0xFF, 0xD0, 0xC3)),
        )
        self.memory.put_u32(entry, orphan)

        with self.assertRaises(RuntimeError) as caught:
            self.install()

        self.assertIn("cannot be read back out of it", str(caught.exception))
        self.assertEqual(self.memory.u32(entry), orphan, "the entry was left as it was found")
        self.assertEqual(self.hooks.headers, ())

    def test_a_write_that_did_not_land_is_refused(self) -> None:
        """A replacement that did not land is the one thing this must not assume away.

        The header whose entry was being written stays tracked, and nothing is freed: its handler is
        still this project's to put back.
        """

        self.bridge.complete = False

        with self.assertRaises(RuntimeError) as caught:
            self.install()

        self.assertIn("did not complete", str(caught.exception))
        self.assertEqual(self.access.freed, [])
        self.assertEqual(self.hooks.headers, (GAME_SMSG_WINDOW_ADD_ITEMS,))

    def test_installing_twice_is_refused(self) -> None:
        self.install()

        with self.assertRaises(RuntimeError):
            self.install()

    def test_asking_for_nothing_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            self.hooks.install(RESOLVED, {})


class ListenerBaseTests(unittest.TestCase):
    """``Listener``: the base's toggle semantics (``listeners.cpp:29-55``)."""

    class _Recorder(Listener):
        def __init__(self) -> None:
            super().__init__()
            self.installs = 0
            self.uninstalls = 0

        def Name(self) -> str:
            return "recorder"

        def Install(self) -> None:
            self.installs += 1

        def Uninstall(self) -> None:
            self.uninstalls += 1

    def setUp(self) -> None:
        self.listener = self._Recorder()

    def test_enable_and_disable_are_idempotent(self) -> None:
        self.listener.Enable()
        self.listener.Enable()
        self.listener.Disable()
        self.listener.Disable()

        self.assertEqual(self.listener.installs, 1)
        self.assertEqual(self.listener.uninstalls, 1)
        self.assertFalse(self.listener.IsEnabled())

    def test_set_enabled_and_toggle_follow_the_state(self) -> None:
        self.listener.SetEnabled(True)
        self.assertTrue(self.listener.IsEnabled())
        self.listener.Toggle()
        self.assertFalse(self.listener.IsEnabled())
        self.listener.Toggle()
        self.assertTrue(self.listener.IsEnabled())

        self.assertEqual(self.listener.installs, 2)
        self.assertEqual(self.listener.uninstalls, 1)

    def test_the_base_is_enabled_by_default_and_its_update_is_a_no_op(self) -> None:
        self.assertTrue(self.listener.EnabledByDefault())
        self.assertIsNone(self.listener.Update(16.0))


class MerchantListenerTests(unittest.TestCase):
    """``MerchantListener``: the five pieces of state, filled by the four handlers."""

    def setUp(self) -> None:
        self.listener = MerchantListener()

    def test_the_price_handler_sets_both_quoted_fields(self) -> None:
        """``listeners.cpp:59-62``. ``quoted_value_`` is signed: ``-1`` is *no quote yet*."""

        self.listener.OnPriceReceived(0x1234, 250)

        self.assertEqual(self.listener.GetQuotedItemId(), 0x1234)
        self.assertEqual(self.listener.GetQuotedValue(), 250)

    def test_the_transaction_handler_latches_and_the_reset_clears(self) -> None:
        """``listeners.h:64-68``: *"without them the flags latch"*."""

        self.listener.OnTransactionComplete()
        self.assertTrue(self.listener.IsTransactionComplete())

        self.listener.ResetTransaction()

        self.assertFalse(self.listener.IsTransactionComplete())

    def test_the_quote_reset_is_the_sources_sentinel(self) -> None:
        self.listener.OnPriceReceived(5, 100)

        self.listener.ResetQuote()

        self.assertEqual(self.listener.GetQuotedValue(), -1)
        self.assertEqual(self.listener.GetQuotedItemId(), 5, "the id is not reset")

    def test_a_fresh_listener_starts_where_the_source_starts(self) -> None:
        """``listeners.h:86-90``: zero, zero, false, empty, empty."""

        self.assertEqual(self.listener.GetQuotedItemId(), 0)
        self.assertEqual(self.listener.GetQuotedValue(), 0)
        self.assertFalse(self.listener.IsTransactionComplete())
        self.assertEqual(self.listener.GetMerchantWindowItems(), [])
        self.assertEqual(self.listener.GetMerchantItems(), [])
        self.assertEqual(self.listener.Name(), "merchant")

    def test_the_returned_lists_are_copies(self) -> None:
        """A caller mutating what it was handed must not reach into the listener's state."""

        self.listener.OnNormalMerchantItemsReceived([1, 2], 2)

        self.listener.GetMerchantWindowItems().append(99)

        self.assertEqual(self.listener.GetMerchantWindowItems(), [1, 2])

    # -- the window items, and their one-second window ---------------------

    def test_the_window_items_are_appended_in_order(self) -> None:
        """``listeners.cpp:68-78``: the whole list, in the packet's own order."""

        self.listener._reset_merchant_window_item.start()
        self.listener.OnNormalMerchantItemsReceived([7, 8, 9], 3)

        self.assertEqual(self.listener.GetMerchantWindowItems(), [7, 8, 9])

    def test_only_the_count_the_packet_named_is_appended(self) -> None:
        """``pak->count`` bounds the copy, exactly as native's loop does."""

        self.listener._reset_merchant_window_item.start()
        self.listener.OnNormalMerchantItemsReceived([7, 8, 9, 10], 2)

        self.assertEqual(self.listener.GetMerchantWindowItems(), [7, 8])

    def test_a_second_stream_inside_the_window_appends_and_does_not_clear(self) -> None:
        """The throttle is the source's: the list is cleared at most once a second."""

        self.listener._reset_merchant_window_item.start()
        self.listener.OnNormalMerchantItemsReceived([1, 2], 2)
        self.listener.OnNormalMerchantItemsReceived([3], 1)

        self.assertEqual(self.listener.GetMerchantWindowItems(), [1, 2, 3])

    def test_a_stream_after_the_window_clears_first(self) -> None:
        """A timer that has run past the window is what the clear is guarded on."""

        self.listener.OnNormalMerchantItemsReceived([1, 2], 2)
        with mock.patch.object(
            self.listener._reset_merchant_window_item, "hasElapsed", return_value=True
        ):
            self.listener.OnNormalMerchantItemsReceived([3], 1)

        self.assertEqual(self.listener.GetMerchantWindowItems(), [3])

    def test_the_window_is_a_thousand_milliseconds(self) -> None:
        """``listeners.cpp:70``: ``hasElapsed(1000)``."""

        self.assertEqual(WINDOW_ITEM_THROTTLE_MS, 1000.0)

    # -- the client's own merchant array -----------------------------------

    def test_the_buy_tab_latches_the_clients_merchant_array(self) -> None:
        """``listeners.cpp:80-94``: only ``unk1 == 12``, and the array is read through the client."""

        world = mock.MagicMock()
        world.merch_items = [11, 12, 13]
        client = mock.MagicMock()
        client.read_world_context.return_value = world

        with mock.patch("py4gw.client._current_client", client):
            self.listener.OnItemStreamEnd(BUY_TAB)

        self.assertEqual(self.listener.GetMerchantItems(), [11, 12, 13])

    def test_another_stream_end_latches_nothing(self) -> None:
        for unk1 in (0, 11, 13, 0xFFFF):
            with self.subTest(unk1=unk1):
                client = mock.MagicMock()
                with mock.patch("py4gw.client._current_client", client):
                    self.listener.OnItemStreamEnd(unk1)

                self.assertEqual(self.listener.GetMerchantItems(), [])
                client.read_world_context.assert_not_called()

    def test_an_invalid_array_clears_the_list_and_pushes_nothing(self) -> None:
        """``context_methods.cpp:219-222``: no array is ``nullptr``, which native treats as empty."""

        self.listener._merch_items.extend([1, 2, 3])
        world = mock.MagicMock()
        world.merch_items = None
        client = mock.MagicMock()
        client.read_world_context.return_value = world

        with mock.patch("py4gw.client._current_client", client):
            self.listener.OnItemStreamEnd(BUY_TAB)

        self.assertEqual(self.listener.GetMerchantItems(), [])

    # -- the packet dispatch ------------------------------------------------

    def test_each_header_reaches_the_handler_the_source_gave_it(self) -> None:
        """The dispatch is ``g_packet_entries[packet->header]``'s lookup (``stoc.cpp:80``)."""

        from py4gw.game_thread.shared_block import EventKind, EventRecord

        self.listener._reset_merchant_window_item.start()

        self.listener.OnPacket(
            EventRecord(
                kind=EventKind.PACKET,
                sequence=GAME_SMSG_ITEM_PRICE_QUOTE,
                words=(GAME_SMSG_ITEM_PRICE_QUOTE, 0x55, 700),
            )
        )
        self.assertEqual(self.listener.GetQuotedItemId(), 0x55)
        self.assertEqual(self.listener.GetQuotedValue(), 700)

        self.listener.OnPacket(
            EventRecord(
                kind=EventKind.PACKET,
                sequence=GAME_SMSG_TRANSACTION_DONE,
                words=(GAME_SMSG_TRANSACTION_DONE,),
            )
        )
        self.assertTrue(self.listener.IsTransactionComplete())

        self.listener.OnPacket(
            EventRecord(
                kind=EventKind.PACKET,
                sequence=GAME_SMSG_WINDOW_ADD_ITEMS,
                words=(GAME_SMSG_WINDOW_ADD_ITEMS, 2, 0x71, 0x72)
                + (0,) * 14,
            )
        )
        self.assertEqual(self.listener.GetMerchantWindowItems(), [0x71, 0x72])

        self.listener.OnPacket(
            EventRecord(
                kind=EventKind.PACKET,
                sequence=GAME_SMSG_WINDOW_ITEMS_END,
                words=(GAME_SMSG_WINDOW_ITEMS_END,),
            )
        )
        self.assertEqual(self.listener.GetMerchantWindowItems(), [0x71, 0x72])

    def test_a_header_this_listener_does_not_watch_changes_nothing(self) -> None:
        from py4gw.game_thread.shared_block import EventKind, EventRecord

        self.listener.OnPacket(
            EventRecord(kind=EventKind.PACKET, sequence=0x9999, words=(0x9999, 1, 2, 3))
        )

        self.assertEqual(self.listener.GetQuotedItemId(), 0)
        self.assertEqual(self.listener.GetMerchantWindowItems(), [])

    def test_the_word_counts_cover_what_each_handler_reads(self) -> None:
        """A handler that reads a word past its header's count would index into nothing.

        The counts are what the stubs copy (``listeners.py``'s own table) and the reads are the
        offsets ``stoc.h`` declares, so this is the one place the two are checked against each other.
        """

        read_words = {
            GAME_SMSG_ITEM_PRICE_QUOTE: 3,
            GAME_SMSG_TRANSACTION_DONE: 1,
            GAME_SMSG_WINDOW_ITEM_STREAM_END: 2,
            GAME_SMSG_WINDOW_ADD_ITEMS: 18,
            GAME_SMSG_WINDOW_ITEMS_END: 1,
        }
        self.assertEqual(PACKET_WORDS, read_words)
        self.assertGreaterEqual(min(PACKET_WORDS.values()), 1)


class ListenerLifecycleTests(unittest.TestCase):
    """``Install``/``Uninstall``: the five callbacks, through this port's own layer."""

    def test_install_replaces_the_five_headers_and_registers_the_dispatch(self) -> None:
        """``listeners.cpp:96-128``, in this port's shape: the entries, then the host handler."""

        client = mock.MagicMock()
        client._resolve.return_value = RESOLVED
        listener = MerchantListener()

        with mock.patch("py4gw.client._current_client", client):
            listener.Install()

        client._resolve.assert_called_once_with("stoc.handler_table_addr")
        client.bridge.install_packets.assert_called_once()
        table_address, wanted = client.bridge.install_packets.call_args[0]
        self.assertEqual(table_address, RESOLVED)
        self.assertEqual(wanted, PACKET_WORDS)
        client.callbacks.register.assert_called_once()
        self.assertEqual(
            client.callbacks.register.call_args[0][1], listener.OnPacket
        )
        self.assertTrue(listener._reset_merchant_window_item.isRunning())

    def test_uninstall_removes_both_halves(self) -> None:
        """``listeners.cpp:130-136``: the callbacks come out and the entries go back."""

        client = mock.MagicMock()
        client._resolve.return_value = RESOLVED
        listener = MerchantListener()

        with mock.patch("py4gw.client._current_client", client):
            listener.Install()
            listener.Uninstall()

        client.callbacks.unregister.assert_called_once()
        client.bridge.remove_packets.assert_called_once()

    def test_the_singleton_is_one_object(self) -> None:
        """``listeners.cpp:140-143``: the function-local static."""

        self.assertIs(Merchant(), Merchant())
        self.assertIsInstance(Merchant(), MerchantListener)

    def test_the_registry_holds_the_merchant_listener(self) -> None:
        from py4gw import listeners as listeners_module

        self.assertEqual(listeners_module.Registry(), [Merchant()])
        self.assertEqual(
            [listener.Name() for listener in listeners_module.Registry()], ["merchant"]
        )

    def test_initialize_enables_the_defaults_and_shutdown_disables_them(self) -> None:
        """``listeners.cpp:179-192``, over whatever the registry holds."""

        from py4gw import listeners as listeners_module

        client = mock.MagicMock()
        client._resolve.return_value = RESOLVED

        with mock.patch("py4gw.client._current_client", client):
            self.assertTrue(listeners_module.Initialize())
            self.assertTrue(Merchant().IsEnabled())

            listeners_module.Shutdown()

        self.assertFalse(Merchant().IsEnabled())
        client.bridge.remove_packets.assert_called_once()

    def test_shutdown_with_nothing_enabled_does_nothing(self) -> None:
        from py4gw import listeners as listeners_module

        client = mock.MagicMock()
        with mock.patch("py4gw.client._current_client", client):
            listeners_module.Shutdown()

        client.bridge.remove_packets.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
