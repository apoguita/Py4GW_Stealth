"""Offline tests for coexisting with the injected Reforged runtime.

Reforged and Reforged Native are injected runtimes that hook the **same four client functions**
this library hooks — ``game_thread.leave_game_thread_func``, ``ui.send_ui_message_func``,
``effects.post_process_effect_func`` and ``render.end_scene_func`` — through MinHook
(``src/base/hooker.cpp``, ``src/GW/render/render.cpp:136-144``, ``src/GW/effects/effects.cpp:142``,
``src/GW/game_thread/game_thread.cpp:76``, ``src/GW/ui/ui.cpp:725``). Injecting Reforged while this
library is connected was measured working live on 2026-10-01; what these tests pin down is the part
that must not be left to luck.

Two facts from the two sources decide it, and both are read from code, not assumed:

- ``HookBase::CreateHook`` resolves its target through a near branch before hooking
  (``base/hooker.cpp:78-80`` → ``Scanner::FunctionFromNearCall``), and that walk follows ``E8``/``E9``
  **without checking that the destination is inside the client's module** (``base/scanner.cpp:113-133``,
  ``check_valid_ptr`` is ``false``). With this library's entry patch in place, MinHook therefore hooks
  *this library's stub*, writes its own five-byte jump over the stub's head, and its trampoline jumps
  back into the stub past those bytes (``third_party/minhook/src/hook.c:355``,
  ``trampoline.c:281-282``). Its restore is a blind ``memcpy`` of the bytes it displaced
  (``hook.c:381-386``) and it frees its trampolines wholesale (``buffer.c:74-85``).
- This library's entry patch is a ``jmp rel32`` into memory it allocated, which is *also* outside the
  client's module. So "the jump leaves the module" identifies a live foreign hook exactly as well as
  it identifies this library's own patch left by a controller that died — which is why the repair that
  used to rely on it silently deleted the other runtime's hooks, and why it is now made to depend on
  what the jump lands on instead.

No client is involved: the target is a ``bytearray`` and the connection is built with
``object.__new__``, because ``ConnectedClient.__init__`` opens handles and asserts elevation. What is
under test is the decision the install makes about bytes, and nothing about a process.

What this does not prove: that Reforged's MinHook really follows a jump out of the client's module on
this build — that is read from its source above, and the live measurement of 2026-10-01 is the
observation that agrees with it. The live two-runtime test is the one that would prove the whole
chain end to end.
"""

from __future__ import annotations

import struct
import unittest
from typing import Any, cast

from py4gw.client import ConnectedClient
from py4gw.game_thread.hooker import STUB_PROLOGUE
from py4gw.win32.write_access import WriteAccess

#: The client module the fake target stands in for.
MODULE_BASE = 0x00400000
MODULE_SIZE = 0x100000

#: A client function this library hooks, and its own entry bytes. The nine bytes are the ones
#: ``client._GAME_THREAD_HOOK_BYTES`` declares, so the fixture is the real shape.
TARGET = 0x00401000
ORIGINAL = bytes.fromhex("55 8B EC 81 EC 20 02 00 00")

#: Where this library allocates generated code: outside the client's module, near it.
OURS = 0x01C90000

#: Where another runtime's code lives: its own DLL, well outside the client's module.
THEIRS = 0x70000000

PAGE_READWRITE = 0x04


class FakeTarget:
    """A target with three regions: the client's module, our generated code, and theirs.

    They are separate so a test can say which of the two owners a jump lands on, which is the whole
    question these tests ask.
    """

    #: ``(base, offset)`` per region: where it starts, and where it lives in the backing buffer.
    REGIONS = (
        (MODULE_BASE, 0x00000),
        (OURS, 0x10000),
        (THEIRS, 0x20000),
    )

    def __init__(self, entry: bytes) -> None:
        self.memory = bytearray(0x30000)
        self._write(TARGET, entry)

    def _write(self, address: int, data: bytes) -> None:
        start = self._index(address)
        self.memory[start : start + len(data)] = data

    def _index(self, address: int) -> int:
        for base, offset in self.REGIONS:
            if base <= address < base + 0x10000:
                return offset + (address - base)
        raise ValueError(f"address 0x{address:08X} is outside the fake's regions")

    # -- what the patcher needs -------------------------------------------

    def read(self, address: int, size: int) -> bytes:
        start = self._index(address)
        return bytes(self.memory[start : start + size])

    def write(self, address: int, data: bytes) -> None:
        self._write(address, data)

    def protect(self, address: int, size: int, protection: int) -> int:
        return PAGE_READWRITE

    def flush_instruction_cache(self, address: int, size: int) -> None:
        pass

    def list_thread_ids(self) -> list[int]:
        return [4321]

    def open_thread(self, thread_id: int) -> int:
        return 0x1000

    def suspend_thread(self, thread_handle: int) -> int:
        return 0

    def resume_thread(self, thread_handle: int) -> int:
        return 0

    def thread_eip(self, thread_handle: int) -> int:
        return 0x00402000

    def close_thread(self, thread_handle: int) -> None:
        pass

    # -- fixtures ----------------------------------------------------------

    def put_generated_stub_at(self, address: int) -> None:
        """Write the prologue every stub this library emits begins with, at ``address``."""

        self._write(address, STUB_PROLOGUE + bytes(5))

    def put_foreign_code_at(self, address: int) -> None:
        """Write a compiled function's prologue, the way another runtime's detour begins."""

        self._write(address, bytes.fromhex("55 8B EC 83 EC 10"))

    def entry(self) -> bytes:
        return self.read(TARGET, len(ORIGINAL))

    def at(self, address: int, size: int) -> bytes:
        return self.read(address, size)


def jump_from(address: int, destination: int) -> bytes:
    """Return the five bytes of a ``jmp rel32`` at ``address`` that lands on ``destination``."""

    return bytes((0xE9,)) + struct.pack("<I", (destination - (address + 5)) & 0xFFFFFFFF)


def bare_connection() -> ConnectedClient:
    """A connection with no process behind it: only what ``_prepare_target`` reads."""

    client = object.__new__(ConnectedClient)
    client._pid = 4321
    client._module_base = MODULE_BASE
    client._module_size = MODULE_SIZE
    return client


def prepare_target(target: FakeTarget, anchor: int | None = None) -> Any:
    """Run the install's placement decision against the fake, which stands in for the write layer.

    ``WriteAccess`` is the real transport and opens a handle to the client, so it is cast rather than
    built: what is under test is which bytes the check reads, decides on, and writes. The returned
    placement is what the install would hand the bridge — where to patch, and what the patch replaces.

    ``anchor`` is what :meth:`ConnectedClient._resolve_placement` found: ``None`` for a resolver that does
    not walk back to a prologue (``game_thread``, ``effects`` — a single ``scan`` with an offset), or the
    address the pattern matched for one that does (``ui``, ``render``).
    """

    return bare_connection()._prepare_target(
        cast("WriteAccess", target), "game_thread", TARGET, ORIGINAL, anchor
    )


class StalePatchRepairTests(unittest.TestCase):
    """This library's own patch, left by a controller that died, is still repaired."""

    def test_a_clean_entry_is_placed_on_the_clients_own_bytes(self) -> None:
        """The ordinary case: the address the resolver gave, and the bytes the catalog declares."""

        target = FakeTarget(ORIGINAL)

        placement = prepare_target(target)

        self.assertEqual(placement.target, TARGET)
        self.assertEqual(placement.displaced, ORIGINAL)
        self.assertFalse(placement.chained)
        self.assertEqual(target.entry(), ORIGINAL, "and nothing was written yet")

    def test_a_jump_onto_our_own_generated_code_is_repaired(self) -> None:
        target = FakeTarget(jump_from(TARGET, OURS) + bytes(4))
        target.put_generated_stub_at(OURS)

        placement = prepare_target(target)

        self.assertEqual(target.entry(), ORIGINAL, "the client's own bytes go back")
        self.assertEqual(placement.target, TARGET)
        self.assertEqual(placement.displaced, ORIGINAL)
        self.assertFalse(placement.chained)

    def test_an_unknown_entry_is_still_refused(self) -> None:
        target = FakeTarget(bytes.fromhex("55 8B EC 83 EC 10 00 00 00"))

        with self.assertRaises(RuntimeError) as caught:
            prepare_target(target)

        self.assertIn("no entry jump was found", str(caught.exception))
        self.assertNotEqual(target.entry(), ORIGINAL, "and nothing was written")


class ForeignHookTests(unittest.TestCase):
    """Another runtime's hook at the same entry: this library places itself **on top of it**.

    Reforged is injected before this library in practice, so its five-byte ``jmp rel32`` is what the entry
    holds when this library connects. The placement replaces exactly those five bytes — a whole
    instruction, so a legal displaced span — and the trampoline relocates the jump so Reforged keeps
    running underneath (``hooker.build_trampoline``); the restore writes the five bytes back, which is why
    Reforged is byte-for-byte as it was after a disconnect.
    """

    def test_a_verified_foreign_jump_is_chained_onto_in_place(self) -> None:
        """``game_thread`` and ``effects``: their resolver does not walk back, so the tail is not needed.

        Their answer comes from a single ``scan`` with a fixed offset, so a jump at it is on the declared
        function by construction — which is what the measured client shows for both of them.
        """

        foreign = jump_from(TARGET, THEIRS)
        target = FakeTarget(foreign + ORIGINAL[5:] + bytes(4))
        target.put_foreign_code_at(THEIRS)

        placement = prepare_target(target)

        self.assertEqual(placement.target, TARGET)
        self.assertEqual(placement.displaced, foreign, "the jump is what the patch replaces")
        self.assertTrue(placement.chained)
        self.assertEqual(
            target.at(TARGET, 5), foreign, "and the decision itself wrote nothing"
        )

    def test_an_in_place_jump_with_a_walked_back_resolver_still_needs_the_tail(self) -> None:
        """``ui`` and ``render``: their answer may be the function before, so the bytes have to agree."""

        foreign = jump_from(TARGET, THEIRS)
        target = FakeTarget(foreign + bytes(9))
        target.put_foreign_code_at(THEIRS)

        with self.assertRaises(RuntimeError) as caught:
            prepare_target(target, anchor=TARGET + 0x400)

        self.assertIn("cannot tell which function", str(caught.exception))
        self.assertEqual(target.at(TARGET, 5), foreign, "their hook is untouched")

    def test_a_verified_foreign_jump_hidden_ahead_of_the_answer_is_chained_onto(self) -> None:
        """The measured live shape: the resolver answered the function before the declared one.

        ``ToFunctionStart`` looks for ``55 8B EC``, so a patched prologue makes it answer the function
        before the target. Live on 2026-10-01 that is what happened for ``ui.send_ui_message_func``
        (answered ``0x1184510``, declared function ``0x11845F0``) and ``render.end_scene_func`` (answered
        ``0x12202C0``, declared function ``0x1220350``), both carrying Reforged's jump. The placement has to
        name the *declared* function, not the answer — and the walk stops at the address the pattern
        matched, which is inside that function.
        """

        plain = bytes.fromhex("55 8B EC 83 EC 2C 53 8B 5D 08 57 8B FB")
        foreign = jump_from(TARGET + 0xE0, THEIRS)
        target = FakeTarget(plain)
        target.write(TARGET + 0xE0, foreign + ORIGINAL[5:])
        target.put_foreign_code_at(THEIRS)

        placement = prepare_target(target, anchor=TARGET + 0x400)

        self.assertEqual(placement.target, TARGET + 0xE0, "the declared function, found ahead")
        self.assertEqual(placement.displaced, foreign)
        self.assertTrue(placement.chained)
        self.assertEqual(target.at(TARGET, len(plain)), plain, "the answer was left alone")

    def test_a_stale_patch_of_ours_ahead_of_the_answer_is_still_repaired(self) -> None:
        """The window scan exists for the resolver walking past a patched prologue, and it still runs."""

        target = FakeTarget(bytes.fromhex("83 C4 04 C3 90 90 90 90 90"))
        ahead = TARGET + 0x40
        target.write(ahead, jump_from(ahead, OURS))
        target.put_generated_stub_at(OURS)

        placement = prepare_target(target)

        self.assertEqual(target.at(ahead, len(ORIGINAL)), ORIGINAL, "our own stale patch goes back")
        self.assertEqual(placement.target, ahead)
        self.assertEqual(placement.displaced, ORIGINAL)
        self.assertFalse(placement.chained)


class RefusalTests(unittest.TestCase):
    """What this library will not place itself on, and why — every refusal writes nothing.

    Two of these are the reasons a chain is refused rather than guessed at: the bytes after the jump do not
    match the catalog's declared entry, so the function the jump is on cannot be told; or the patch is not
    a shape whose relocation this library can do (``hooker.build_trampoline`` relocates one ``jmp rel32``
    by shape and says so). The rest are the cases where the resolver answered something that is not an
    entry at all.
    """

    def test_a_foreign_jump_without_the_declared_tail_is_refused(self) -> None:
        """A jump alone says somebody hooked something here; it does not say what — with a walk-back."""

        foreign = jump_from(TARGET, THEIRS)
        target = FakeTarget(foreign + bytes(9))
        target.put_foreign_code_at(THEIRS)

        with self.assertRaises(RuntimeError) as caught:
            prepare_target(target, anchor=TARGET + 0x400)

        message = str(caught.exception)
        self.assertIn(f"0x{TARGET:08X}", message)
        self.assertIn(f"0x{THEIRS:08X}", message, "the refusal names where the jump goes")
        self.assertIn("cannot tell which function", message)
        self.assertIn("Nothing was written", message)
        self.assertEqual(target.at(TARGET, 5), foreign, "the other runtime's hook is untouched")

    def test_a_foreign_jump_without_the_declared_tail_ahead_is_refused_too(self) -> None:
        target = FakeTarget(bytes.fromhex("83 C4 04 C3 90 90 90 90 90"))
        ahead = TARGET + 0x40
        target.write(ahead, jump_from(ahead, THEIRS))
        target.put_foreign_code_at(THEIRS)

        with self.assertRaises(RuntimeError) as caught:
            prepare_target(target, anchor=TARGET + 0x400)

        self.assertIn("cannot tell which function", str(caught.exception))
        self.assertEqual(
            target.at(ahead, 5), jump_from(ahead, THEIRS), "their hook ahead of the answer is kept"
        )

    def test_a_jump_past_the_anchor_is_not_taken_for_the_declared_function(self) -> None:
        """The bound the anchor gives: the entry cannot be past the address the pattern matched.

        ``anchor`` is inside the declared function, so a jump beyond it belongs to a later function. The
        walk stops there, which is what keeps the window from wandering into unrelated code.
        """

        plain = bytes.fromhex("83 C4 04 C3 90 90 90 90 90")
        target = FakeTarget(plain)
        beyond = TARGET + 0x500
        target.write(beyond, jump_from(beyond, THEIRS) + ORIGINAL[5:])
        target.put_foreign_code_at(THEIRS)

        with self.assertRaises(RuntimeError) as caught:
            prepare_target(target, anchor=TARGET + 0x100)

        self.assertIn("no entry jump was found", str(caught.exception))
        self.assertEqual(target.at(beyond, 5), jump_from(beyond, THEIRS), "it was left alone")

    def test_a_foreign_patch_of_another_shape_is_refused(self) -> None:
        """A short jump is not five bytes nor an ``E9``, so its relocation is not something this can do."""

        short = bytes.fromhex("EB 7F") + ORIGINAL[2:]
        target = FakeTarget(short)

        with self.assertRaises(RuntimeError) as caught:
            prepare_target(target)

        self.assertIn("no entry jump was found", str(caught.exception))
        self.assertEqual(target.at(TARGET, len(short)), short)

    def test_a_jump_inside_the_module_ahead_is_not_an_entry_patch(self) -> None:
        """Ordinary control flow leaves a jump behind; only a landing outside the module is considered."""

        plain = bytes.fromhex("55 8B EC 83 EC 2C 53 8B 5D 08 57 8B FB")
        target = FakeTarget(plain)
        ahead = TARGET + 0x40
        target.write(ahead, jump_from(ahead, MODULE_BASE + 0x8000))

        with self.assertRaises(RuntimeError) as caught:
            prepare_target(target)

        self.assertIn("no entry jump was found", str(caught.exception))
        self.assertEqual(target.at(TARGET, len(plain)), plain)

    def test_a_foreign_jump_into_the_module_is_chained_to_in_place(self) -> None:
        """Where the jump lands does not matter: an in-place answer from the catalog decides the rest.

        A hook whose detour sits inside the client's own module — a code cave, another tool's own block —
        is the same operation to displace and the same bytes to write back, so the landing is not a test.
        What the walk ahead uses it for is different: there, a jump that stays inside the module is
        ordinary control flow and is skipped.
        """

        inside = MODULE_BASE + 0x8000
        foreign = jump_from(TARGET, inside)
        target = FakeTarget(foreign + ORIGINAL[5:])
        target.put_foreign_code_at(inside)

        placement = prepare_target(target)

        self.assertEqual(placement.target, TARGET)
        self.assertEqual(placement.displaced, foreign)
        self.assertTrue(placement.chained)


if __name__ == "__main__":
    unittest.main()
