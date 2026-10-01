"""Live test: this project and the injected Reforged runtime in one client.

Both runtimes hook the **same four client functions** — ``game_thread.leave_game_thread_func``,
``ui.send_ui_message_func``, ``effects.post_process_effect_func`` and ``render.end_scene_func``
(``game_thread.cpp:76``, ``ui.cpp:725``, ``effects.cpp:142``, ``render.cpp:136``) — so "who connects
first" decides whether they coexist or one of them silently loses its hooks. The supported arrangement,
and why the reverse is refused, is in ``docs/NATIVE_EXECUTION_PLAN.md``; this file is the live
verification of both directions.

**Two classes, because the client has to be in a different state for each:**

- :class:`ReforgedFirstTests` — Reforged is injected and this project is not connected. This project must
  **refuse** and write nothing, and Reforged's hooks must be exactly as they were afterwards. This is the
  direction that used to be silent: the install treated another runtime's entry jump as this project's own
  stale patch and wrote the client's original bytes over it.
- :class:`StealthFirstTests` — this project connects first, and Reforged is injected **while the test is
  waiting**. Reforged then follows this project's entry jump and hooks this project's generated stub
  (``base/hooker.cpp:78-80`` → ``base/scanner.cpp:113-133``), both runtimes run on every call, and the
  disconnect must refuse to free the stub Reforged's trampoline returns into.

Run from an **elevated** shell with Guild Wars running::

    python -m unittest tests.test_live_coexistence -v

Each class skips itself when the client is not in the state it needs, so running both is safe: on a
client that already has Reforged injected, ``StealthFirstTests`` skips and ``ReforgedFirstTests`` runs.

**Every attempt restores what it touched**, and each class prints what it is doing. The refusal paths are
the point of the test: a refusal that leaves the client patched would be worse than the bug it prevents.
"""

from __future__ import annotations

import struct
import time
import unittest
from typing import Any, cast

import py4gw
from py4gw.client import (
    _EFFECTS_HOOK,
    _EFFECTS_HOOK_BYTES,
    _GAME_THREAD_HOOK,
    _GAME_THREAD_HOOK_BYTES,
    _GAME_THREAD_OBSERVE,
    _GAME_THREAD_OBSERVE_BYTES,
    _RENDER_HOOK,
    _RENDER_HOOK_BYTES,
    ConnectedClient,
)
from py4gw.game_thread.hooker import MINIMUM_PATCH, STUB_PROLOGUE, is_generated_stub
from py4gw.memory import ProcessMemoryReader
from py4gw.scanner import PatternCatalog, RemoteScanner
from py4gw.win32 import Win32
from py4gw.win32.write_access import WriteAccess

#: The four shared entries, exactly as the connection declares them.
TARGETS = (
    (_GAME_THREAD_HOOK, _GAME_THREAD_HOOK_BYTES),
    (_GAME_THREAD_OBSERVE, _GAME_THREAD_OBSERVE_BYTES),
    (_EFFECTS_HOOK, _EFFECTS_HOOK_BYTES),
    (_RENDER_HOOK, _RENDER_HOOK_BYTES),
)

JMP_REL32 = 0xE9

#: How long the Stealth-first class waits for Reforged to be injected mid-run, and how often it looks.
INJECTION_TIMEOUT_SECONDS = 300.0
INJECTION_POLL_SECONDS = 0.5

#: How long a hooked function may take to fire, and how long a client read may take to answer after a
#: disconnect — both generous, because the client's own thread decides when it runs.
HIT_TIMEOUT_MS = 10000
ALIVE_TIMEOUT_SECONDS = 10.0

ACCESS_DENIED = 5


class _Entries:
    """A read-only view of the four shared entry points, with no connection behind it.

    The reads use a read-only handle, so this works whether or not anything is connected and needs no
    elevation: what the test needs before and after a write attempt is the client's own bytes, not this
    project's.
    """

    def __init__(self, pid: int) -> None:
        self.pid = pid
        win32 = Win32()
        module = win32.get_main_module(pid)
        self.module_base = int(module["base_address"])
        self.module_size = int(module["size"])
        self._reader = ProcessMemoryReader(win32, pid)
        self._scanner = RemoteScanner(
            self._reader,
            module_base=self.module_base,
            module_size=self.module_size,
        )
        self._scanner.initialize()
        self._catalog = PatternCatalog.from_directory("offsets")

    def close(self) -> None:
        self._reader.close()

    def address_of(self, name: str) -> int:
        result = self._catalog.resolve(name, self._scanner)
        if not result.ok:
            raise AssertionError(f"{name} did not resolve: {result.message}")
        return int(result.value)

    def read(self, address: int, size: int) -> bytes:
        return self._reader.read(address, size)

    def snapshot(self) -> dict[str, dict[str, Any]]:
        """Return each entry's address and head, as an ordinary read-only observation."""

        observed: dict[str, dict[str, Any]] = {}
        for name, entry_bytes in TARGETS:
            address = self.address_of(name)
            head = self.read(address, max(len(entry_bytes), 16))
            landing = (
                (address + 5 + struct.unpack_from("<i", head, 1)[0]) & 0xFFFFFFFF
                if head[:1] == bytes((JMP_REL32,))
                else 0
            )
            observed[name] = {
                "address": address,
                "head": head,
                "expected": entry_bytes,
                "landing": landing,
                "lands_on_generated_stub": bool(
                    landing and is_generated_stub(self.read(landing, len(STUB_PROLOGUE)))
                ),
            }
        return observed

    def hooks_are_ours(self, snapshot: dict[str, dict[str, Any]]) -> dict[str, bool]:
        """Whether each entry still holds the jump this project wrote, landing on its own stub."""

        state = {}
        for name, row in snapshot.items():
            head = self.read(row["address"], 16)
            state[name] = bool(
                head[:5] == bytes((JMP_REL32,))
                + struct.pack("<I", (row["landing"] - (row["address"] + 5)) & 0xFFFFFFFF)
                and row["lands_on_generated_stub"]
            )
        return state

    def foreign_entries(self) -> dict[str, dict[str, Any]]:
        """Find each shared entry that carries another runtime's jump, **by the shipping helpers**.

        A resolver whose steps end in ``to_function_start`` answers the function *before* the declared one
        when the prologue it looks for has been replaced, so the entries cannot be found by resolving alone.
        This drives the same two calls the install drives — ``_resolve_placement`` for the address and its
        anchor, ``_entry_jump_ahead`` for the jump the walk-back hid — over a read-only handle, and returns
        what is there: the address that carries the jump, its five bytes, and where it lands. It is what the
        test compares against after a disconnect, because "Reforged is exactly as it was" is a claim about
        those bytes.
        """

        decision = object.__new__(ConnectedClient)
        decision._pid = self.pid
        decision._module_base = self.module_base
        decision._module_size = self.module_size
        # The two the install's helpers read: the catalog the connection builds and the scanner over this
        # client. Everything else they touch is the access object below.
        decision._patterns = self._catalog
        decision._scanner = self._scanner
        access = cast("WriteAccess", _ReadOnly(self._reader))

        found: dict[str, dict[str, Any]] = {}
        for name, entry_bytes in TARGETS:
            address, anchor = decision._resolve_placement(name)
            head = self.read(address, len(entry_bytes))
            target = address
            if head[:1] != bytes((JMP_REL32,)):
                ahead = decision._entry_jump_ahead(
                    access, address, len(entry_bytes), limit=anchor or 0
                )
                if ahead is None:
                    continue
                target = ahead[0]
                head = self.read(target, len(entry_bytes))
            if head[:1] != bytes((JMP_REL32,)):
                continue
            found[name] = {
                "address": target,
                "head": head,
                #: What a patch there replaces: the jump itself, which is one five-byte instruction.
                "jump": head[:MINIMUM_PATCH],
                "resolver_answered": address,
                "landing": (target + 5 + struct.unpack_from("<i", head, 1)[0]) & 0xFFFFFFFF,
            }
        return found


class _ReadOnly:
    """The one call the install's helpers make, over a read-only handle."""

    def __init__(self, reader: ProcessMemoryReader) -> None:
        self._reader = reader

    def read(self, address: int, size: int) -> bytes:
        return self._reader.read(address, size)


def client_pid() -> int:
    """Return the running client's pid, or skip the test when there is none."""

    clients = Win32().find_guild_wars()
    if not clients:
        raise unittest.SkipTest("Start Guild Wars before running this test.")
    return int(clients[0]["pid"])


def connect_or_skip(pid: int, game_thread: bool = True):
    """Connect, turning the two not-this-test conditions into skips."""

    try:
        return py4gw.connect(pid, game_thread=game_thread)
    except RuntimeError as error:
        message = str(error)
        if "not elevated" in message:
            raise unittest.SkipTest(
                "This test writes to the client, so it needs an elevated shell: "
                f"{message}"
            ) from error
        raise


class ReforgedFirstTests(unittest.TestCase):
    """Reforged is already injected: this library chains **on top of** its entry jumps.

    This is the arrangement that happens in practice — Reforged comes with the client — and the one the
    owner ruled for on 2026-10-01. On the measured client all four shared entries carry Reforged's
    five-byte ``jmp rel32``, two of them where the resolver answered and two of them 0xE0 and 0x90 bytes
    ahead of an answer that had walked back past the patched prologue.

    What this proves: the four entries that carry Reforged's jump are found by the shipping helpers rather
    than by resolving alone (two of them are hidden behind the resolver's walk-back), the connection
    **chains on top of each of them**, this library's hooks fire while Reforged's chain still runs
    underneath, and after a disconnect every one of those entries is **byte-for-byte what it was** — which
    is the guarantee this arrangement rests on, because MinHook would otherwise be writing from a backup
    that no longer matches.

    What it does not prove: that Reforged's own callbacks ran during the connection. The chain is what
    carries them (this library's trampoline relocates Reforged's jump to its detour), and the evidence here
    is that the client keeps running and this library's hooks keep firing across it; observing Reforged's
    own callbacks needs a client event Reforged logs, which is a different test.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.pid = client_pid()
        cls.entries = _Entries(cls.pid)
        cls.foreign = cls.entries.foreign_entries()
        if not cls.foreign:
            cls.entries.close()
            raise unittest.SkipTest(
                "no entry holds another runtime's jump: this class needs a client with Reforged "
                "injected, which is the arrangement it exists to verify."
            )
        print(
            f"\n[coexistence] pid {cls.pid}: {len(cls.foreign)} of {len(TARGETS)} entries carry another "
            "runtime's jump; this project must chain on top of each and leave them byte-for-byte."
        )
        for name, row in cls.foreign.items():
            print(
                f"    {name}: jump at 0x{row['address']:08X} -> 0x{row['landing']:08X}"
                + (
                    f" (the resolver answered 0x{row['resolver_answered']:08X})"
                    if row["address"] != row["resolver_answered"]
                    else ""
                )
            )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.entries.close()

    def test_connecting_chains_on_top_of_every_foreign_jump(self) -> None:
        """The supported arrangement for this client: this library second, on Reforged's own patches."""

        client = connect_or_skip(self.pid)
        try:
            self.assertEqual(
                set(client.chained_hooks),
                set(self.foreign),
                "the install reports a chained placement for each entry that carried a jump",
            )
            for name, row in self.foreign.items():
                placement = client._placements[name]  # noqa: SLF001 - the install's own record
                self.assertEqual(placement.target, row["address"], f"{name}: patched where the jump is")
                self.assertEqual(
                    placement.displaced,
                    row["jump"],
                    f"{name}: what the patch replaces is the other runtime's jump",
                )
                self.assertTrue(placement.chained)

                head = self.entries.read(placement.target, 5)
                self.assertEqual(head[0], JMP_REL32, f"{name}: this project's own jump is there now")
                landing = (
                    placement.target + 5 + struct.unpack_from("<i", head, 1)[0]
                ) & 0xFFFFFFFF
                self.assertTrue(
                    is_generated_stub(self.entries.read(landing, len(STUB_PROLOGUE))),
                    f"{name}: and it lands on this project's generated stub",
                )

            client.bridge.wait_for_hits(1, HIT_TIMEOUT_MS)
            self.assertGreater(client.bridge.hits(), 0, "this project's hooks fire")
        finally:
            self._disconnect_reporting()

    def test_the_other_runtime_is_left_byte_for_byte_after_a_disconnect(self) -> None:
        """The chain is temporary by construction: the displaced jump is written back, unaltered.

        This is what makes chaining under Reforged safe to do at all: MinHook restores its own target from
        a backup captured before this library patched, so anything but the exact bytes that were there
        would leave the two runtimes disagreeing about what is installed.
        """

        client = connect_or_skip(self.pid)
        client.bridge.wait_for_hits(1, HIT_TIMEOUT_MS)
        self._disconnect_reporting()

        for name, row in self.foreign.items():
            self.assertEqual(
                self.entries.read(row["address"], len(row["jump"])),
                row["jump"],
                f"{name}: the other runtime's jump is back at 0x{row['address']:08X}, byte for byte",
            )

    def test_the_client_still_runs_after_a_chain_and_a_disconnect(self) -> None:
        """A chain that left the client worse off would be worse than the problem it solves."""

        client = connect_or_skip(self.pid)
        client.bridge.wait_for_hits(1, HIT_TIMEOUT_MS)
        self._disconnect_reporting()

        self.assertTrue(self.entries.read(self.entries.module_base, 2) == b"MZ", "the image header")
        self.assertTrue(self._cpu_time_advances(), "the client's own thread is still running")

    def _disconnect_reporting(self) -> None:
        """Disconnect, and let a refused free be reported rather than swallowed."""

        try:
            py4gw.disconnect()
        except RuntimeError as error:
            print(f"[coexistence] disconnect reported: {error}")
        except BaseException as error:  # noqa: BLE001 - reported, not swallowed
            print(f"[coexistence] disconnect raised {type(error).__name__}: {error}")

    @staticmethod
    def _cpu_time_advances(seconds: float = 1.5) -> bool:
        """Whether the target process is burning CPU, which a live game loop is."""

        import psutil

        try:
            process = psutil.Process(client_pid())
            before = sum(process.cpu_times()[:2])
            time.sleep(seconds)
            return sum(process.cpu_times()[:2]) > before
        except Exception:  # noqa: BLE001 - a missing process is not "alive"
            return False


class StealthFirstTests(unittest.TestCase):
    """This project connects first, then Reforged is injected while the test waits.

    **The user injects Reforged during the wait** — the test prints a prompt and polls for it, because that
    is the only moment the chain can be observed: Reforged resolves its target through a near branch with
    no module check (``base/hooker.cpp:78-80``), finds this project's entry jump, and hooks this project's
    generated stub instead of the client's function. From then on every client call runs both runtimes'
    code, and the client's own function is left holding this project's patch.

    What this proves live: this project's four entry patches survive the injection; this project's hooks
    keep firing afterwards; the stub Reforged hooked reads back with a foreign jump at its head; the
    disconnect refuses to free that stub and says why; and the client's functions come back to their own
    bytes with the client healthy.

    What it does not prove: the order of the two runtimes' callbacks inside one call. That needs a client
    function whose effect is visible from outside, which is what the ``effects``/dialog work covers
    elsewhere.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.pid = client_pid()
        cls.entries = _Entries(cls.pid)
        cls.before = cls.entries.snapshot()
        foreign = [name for name, row in cls.before.items() if row["head"][:1] == bytes((JMP_REL32,))]
        if foreign:
            cls.entries.close()
            raise unittest.SkipTest(
                f"{len(foreign)} entries already hold another runtime's jump ({', '.join(foreign)}), so "
                "this project cannot connect first on this client: restart the client without Reforged "
                "injected to run this class."
            )
        cls.original_heads = {name: row["head"] for name, row in cls.before.items()}

    @classmethod
    def tearDownClass(cls) -> None:
        cls.entries.close()

    def test_the_two_runtimes_chain_and_the_disconnect_refuses_to_free_the_stub(self) -> None:
        client = connect_or_skip(self.pid)
        installed = self.entries.snapshot()
        stub = self._stub_addresses(installed)
        try:
            self.assertTrue(client.bridge.installed, "the connection says its hook is placed")
            client.bridge.wait_for_hits(1, HIT_TIMEOUT_MS)
            print(
                "\n[coexistence] this project is connected and its hooks are firing.\n"
                "             >>> Now inject Reforged into the client. <<<\n"
                f"             waiting up to {INJECTION_TIMEOUT_SECONDS:.0f} s for one of its hooks to "
                "appear inside this project's generated stub..."
            )
            hooked = self._wait_for_a_foreign_jump_in(stub)
            if hooked is None:
                self.fail(
                    "Reforged was not injected while the test waited, so the chain could not be observed. "
                    "Nothing was written by this test; the client is as it was."
                )

            name, address, head = hooked
            print(
                f"[coexistence] Reforged hooked this project's stub for {name!r}: the stub at "
                f"0x{address:08X} now begins {head[:5].hex(' ')}."
            )

            # 1. This project's entry patches are still this project's: Reforged did not touch them.
            state = self.entries.hooks_are_ours(installed)
            self.assertEqual(
                state, {name: True for name in TARGETS}, "every entry still holds this project's jump"
            )

            # 2. Both runtimes run: the client is still reaching this project's stub after the injection.
            hits_before = client.bridge.hits()
            client.bridge.wait_for_hits(1, HIT_TIMEOUT_MS)
            self.assertGreater(client.bridge.hits(), hits_before)

            # 3. The teardown refuses to free code the other runtime's trampoline returns into.
            with self.assertRaises(RuntimeError) as caught:
                py4gw.disconnect()
            message = str(caught.exception)
            self.assertIn("no longer begins with its own head", message)
            self.assertIn("Nothing was freed", message)
            self.assertIn("Unload the other runtime", message)

            # 4. And the client's own functions have their bytes back, so the client is not left patched
            #    by this project even though the stub stays mapped.
            for name, entry_bytes in TARGETS:
                address = installed[name]["address"]
                self.assertEqual(
                    self.entries.read(address, len(entry_bytes)),
                    self.original_heads[name][: len(entry_bytes)],
                    f"{name} did not come back to the client's own bytes",
                )
        finally:
            self._best_effort_disconnect(client)

    # -- internals ---------------------------------------------------------

    def _stub_addresses(self, installed: dict[str, dict[str, Any]]) -> dict[str, int]:
        """Return where this project's generated stubs are, from the entries it just wrote."""

        return {name: row["landing"] for name, row in installed.items() if row["landing"]}

    def _wait_for_a_foreign_jump_in(
        self, stubs: dict[str, int]
    ) -> tuple[str, int, bytes] | None:
        """Poll this project's stubs until one of them carries another runtime's entry patch."""

        deadline = time.monotonic() + INJECTION_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            for name, address in stubs.items():
                head = self.entries.read(address, len(STUB_PROLOGUE))
                if head[:1] == bytes((JMP_REL32,)):
                    return name, address, head
            time.sleep(INJECTION_POLL_SECONDS)
        return None

    def _best_effort_disconnect(self, client: object) -> None:
        """Leave the client as it was, whatever happened above.

        A disconnect that refuses the free has already restored the hooked functions' own bytes; one that
        fails for any other reason is reported rather than swallowed, because a client left patched is the
        one outcome this test must never produce quietly.
        """

        try:
            py4gw.disconnect()
        except RuntimeError as error:
            if "no longer begins with its own head" in str(error):
                return
            print(f"[coexistence] disconnect reported: {error}")
        except BaseException as error:  # noqa: BLE001 - reported, not swallowed
            print(f"[coexistence] disconnect raised {type(error).__name__}: {error}")


if __name__ == "__main__":
    unittest.main()
