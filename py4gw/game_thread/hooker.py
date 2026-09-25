"""Place our code at the entry of a client function, and take it back out.

A hook is three pieces of generated code plus one byte patch:

    entry patch   the first bytes of the target function, replaced by a jump
                  to the stub
    stub          our code: save the flags and registers, run the dispatcher if
                  the hook is enabled, restore, then jump to the trampoline
    trampoline    the bytes the entry patch displaced, followed by a jump back
                  to the instruction after them

The client calls its function exactly as before. It runs our stub on the way in
and never notices, because the stub restores every register and flag it touches
before continuing through the trampoline.

Two things this module deliberately does not do.

It does not decode x86 instructions to work out how many bytes a jump needs. The
caller states the displaced bytes, so the *call site* owns the knowledge of where
a whole number of instructions ends. The hooker checks the bytes at the target
match what was declared, which catches a stale or wrong declaration, and nothing
more.

It does not free the generated code when a hook is removed. A thread can be inside
the stub at that moment, and unmapping code an instruction pointer is heading into
crashes the client. An ``active`` counter cannot close that hole either: a thread
that has taken the entry jump but not yet incremented is invisible. The
allocations are therefore left in place, which costs a few hundred bytes per hook,
once.
"""

from __future__ import annotations

import struct
import time
from dataclasses import dataclass
from typing import Protocol

from .patcher import (
    PAGE_EXECUTE_READ,
    Patcher,
    TargetAccess,
)

#: ``pushfd``, ``pushad``, ``popad``, ``popfd``. The stub preserves everything the
#: client's function could care about, so the hook is invisible to it.
_PUSHFD = 0x9C
_PUSHAD = 0x60
_POPAD = 0x61
_POPFD = 0x9D
#: ``jmp rel32``, the only jump a patch of five bytes or more can use.
_JMP_REL32 = 0xE9
#: ``nop``, padding the entry patch out to the displaced length.
_NOP = 0x90
#: ``je rel8``, the stub's skip over the dispatcher call.
_JE_REL8 = 0x74
#: ``push imm32``, ``push eax``, ``mov eax, imm32``, ``call eax``,
#: ``inc dword [eax+4]``, ``cmp dword [eax], 0``.
_PUSH_IMM32 = 0x68
_PUSH_EAX = 0x50
_MOV_EAX_IMM32 = 0xB8
_CALL_EAX = bytes((0xFF, 0xD0))
_INC_EAX_4 = bytes((0xFF, 0x40, 0x04))
_CMP_EAX_0 = bytes((0x83, 0x38, 0x00))

#: The state block: ``enabled``, ``hits``, then two reserved words.
STATE_SIZE = 16
STATE_ENABLED_OFFSET = 0
STATE_HITS_OFFSET = 4

#: The smallest patch that can hold ``jmp rel32``.
MINIMUM_PATCH = 5

#: How long to wait between reads of the hit counter.
HIT_POLL_SECONDS = 0.005

#: How long to wait after restoring a target before releasing its generated code,
#: when the caller asks for it to be released. A thread that took the entry jump
#: just before the restore is still inside the stub for an instant; this is a
#: courtesy wait, not proof, which is why releasing is opt-in.
FREE_WAIT_SECONDS = 0.25

_UINT32_MAX = 0xFFFFFFFF


class WritableTarget(TargetAccess, Protocol):
    """A target the hooker can also allocate and free code in."""

    def allocate(self, size: int) -> int: ...

    def free(self, address: int) -> None: ...


def _rel32(origin: int, destination: int) -> bytes:
    """Return the displacement to ``destination`` from the end of a jump at ``origin``."""

    return struct.pack("<I", (destination - origin) & _UINT32_MAX)


def build_entry_patch(address: int, stub_address: int, length: int) -> bytes:
    """Return the bytes that replace the target's first ``length`` bytes."""

    if length < MINIMUM_PATCH:
        raise ValueError(
            f"a patch needs at least {MINIMUM_PATCH} bytes to hold a jump; "
            f"{length} were given."
        )
    jump = bytes((_JMP_REL32,)) + _rel32(address + MINIMUM_PATCH, stub_address)
    return jump + bytes((_NOP,)) * (length - len(jump))


def build_trampoline(
    trampoline_address: int, displaced: bytes, resume_address: int
) -> bytes:
    """Return the displaced bytes followed by a jump back into the target."""

    if not displaced:
        raise ValueError("displaced bytes must not be empty.")
    body = bytearray(displaced)
    body.append(_JMP_REL32)
    body += _rel32(trampoline_address + len(body) + 4, resume_address)
    return bytes(body)


def build_stub(
    stub_address: int,
    state_address: int,
    block_address: int,
    dispatcher_address: int,
    trampoline_address: int,
    forwarded_arguments: int = 0,
) -> bytes:
    """Return the entry stub: save, optionally dispatch, restore, continue.

    The call is ``__stdcall`` and the dispatcher pops its own argument, so there
    is no ``add esp, 4`` afterwards. That convention is a contract with the
    payload.

    ``forwarded_arguments`` passes the hooked function's own first arguments to
    the payload as well, ahead of the block. The observer needs them: it is
    placed on a function whose arguments say *what* was called. They are pushed in
    reverse, so the callee sees the block first and then the function's arguments
    in order, and the callee pops all of them — which is why a payload written for
    a forwarding stub ends in ``ret 4 + 4 * forwarded_arguments``.

    ``stub_address`` is needed because the final jump is relative. The stub's
    length does not depend on any address, so ``stub_size()`` can be asked for it
    before the code is placed.
    """

    if forwarded_arguments < 0:
        raise ValueError("forwarded_arguments cannot be negative.")

    body = bytearray()
    body.append(_PUSHFD)
    body.append(_PUSHAD)

    body.append(_MOV_EAX_IMM32)
    body += struct.pack("<I", state_address)
    body += _INC_EAX_4
    body += _CMP_EAX_0
    jump_position = len(body)
    body.append(_JE_REL8)
    body.append(0)  # patched below, once the skip target is known

    # Each push moves the stack by the same four bytes the next argument sits
    # further along, so every one of them is read at the same offset: past the
    # return address, the pushed flags and registers, and the arguments still to
    # come.
    argument_offset = 36 + forwarded_arguments * 4
    for _ in range(forwarded_arguments):
        body += bytes((0x8B, 0x44, 0x24, argument_offset))  # mov eax, [esp+offset]
        body.append(_PUSH_EAX)

    body.append(_PUSH_IMM32)
    body += struct.pack("<I", block_address)
    body.append(_MOV_EAX_IMM32)
    body += struct.pack("<I", dispatcher_address)
    body += _CALL_EAX

    skip_target = len(body)
    body.append(_POPAD)
    body.append(_POPFD)
    body.append(_JMP_REL32)
    body += _rel32(stub_address + len(body) + 4, trampoline_address)

    displacement = skip_target - (jump_position + 2)
    if not 0 <= displacement <= 0x7F:
        raise ValueError("the stub's skip branch no longer fits in one byte.")
    body[jump_position + 1] = displacement
    return bytes(body)


def stub_size(forwarded_arguments: int = 0) -> int:
    """Return the stub's length, which is the same at every address."""

    return len(build_stub(0, 0, 0, 0, 0, forwarded_arguments))


@dataclass(frozen=True)
class _InstalledHook:
    """What one installed hook needs in order to be enabled, read, or removed."""

    name: str
    target: int
    displaced: bytes
    state_address: int
    stub_address: int
    trampoline_address: int


class Hooker:
    """Install, enable, disable and remove hooks in one target process.

    One hooker owns one process and one shared block. Hooks are named by the
    caller, so the registry reads as the list of hook sites it is.
    """

    def __init__(
        self,
        access: WritableTarget,
        pid: int,
        block_address: int,
        dispatcher_address: int,
        timeout_ms: int = 2000,
    ) -> None:
        """Create a hooker over an already-open target.

        ``block_address`` is the shared block the dispatcher reads, and
        ``dispatcher_address`` is the entry point our stub calls.
        """

        if block_address <= 0:
            raise ValueError("block_address must be positive.")
        if dispatcher_address <= 0:
            raise ValueError("dispatcher_address must be positive.")

        self._access = access
        self._pid = pid
        self._block_address = block_address
        self._dispatcher_address = dispatcher_address
        self._patcher = Patcher(access, pid, timeout_ms)
        self._hooks: dict[str, _InstalledHook] = {}

    @property
    def pid(self) -> int:
        """Return the process this hooker writes to."""

        return self._pid

    @property
    def installed(self) -> tuple[str, ...]:
        """Return the names of the hooks currently installed."""

        return tuple(sorted(self._hooks))

    def install(
        self,
        name: str,
        target: int,
        displaced: bytes,
        forwarded_arguments: int = 0,
    ) -> None:
        """Hook ``target``, displacing exactly ``displaced`` bytes.

        ``displaced`` must cover a whole number of instructions, because it is
        replayed verbatim from the trampoline. The bytes at ``target`` are checked
        against it, and a mismatch refuses.

        ``forwarded_arguments`` hands the hooked function's first arguments to the
        payload as well, which is what an observing payload needs; the payload it
        calls must pop them. Default zero is the command dispatcher's contract.

        The entry patch is written last. Nothing can reach the stub before it
        exists, so a failure at any earlier step can free everything it made.
        """

        if not name:
            raise ValueError("a hook needs a name.")
        if name in self._hooks:
            raise ValueError(f"a hook named {name!r} is already installed.")
        if target <= 0:
            raise ValueError("target must be positive.")
        if len(displaced) < MINIMUM_PATCH:
            raise ValueError(
                f"displaced must cover at least {MINIMUM_PATCH} bytes so a jump "
                f"fits; {len(displaced)} were given."
            )

        state_address = self._access.allocate(STATE_SIZE)
        trampoline_address = 0
        stub_address = 0
        try:
            # Enabled from the start: the stub is only reachable once patched.
            self._access.write(
                state_address,
                struct.pack("<I", 1) + bytes(STATE_SIZE - 4),
            )

            trampoline_size = len(displaced) + MINIMUM_PATCH
            trampoline_address = self._access.allocate(trampoline_size)
            self._make_executable(
                trampoline_address,
                build_trampoline(
                    trampoline_address, displaced, target + len(displaced)
                ),
            )

            stub_address = self._access.allocate(stub_size(forwarded_arguments))
            self._make_executable(
                stub_address,
                build_stub(
                    stub_address=stub_address,
                    state_address=state_address,
                    block_address=self._block_address,
                    dispatcher_address=self._dispatcher_address,
                    trampoline_address=trampoline_address,
                    forwarded_arguments=forwarded_arguments,
                ),
            )

            self._patcher.patch(
                target,
                displaced,
                build_entry_patch(target, stub_address, len(displaced)),
            )
        except BaseException:
            # Nothing can be inside the stub yet, because the entry patch is the
            # last step and it did not complete.
            for address in (stub_address, trampoline_address, state_address):
                if address:
                    self._access.free(address)
            raise

        self._hooks[name] = _InstalledHook(
            name=name,
            target=target,
            displaced=bytes(displaced),
            state_address=state_address,
            stub_address=stub_address,
            trampoline_address=trampoline_address,
        )

    def enable(self, name: str) -> None:
        """Let the stub run the dispatcher again."""

        hook = self._require(name)
        self._access.write(
            hook.state_address + STATE_ENABLED_OFFSET, struct.pack("<I", 1)
        )

    def disable(self, name: str) -> None:
        """Make the stub pass through without dispatching, without unpatching."""

        hook = self._require(name)
        self._access.write(
            hook.state_address + STATE_ENABLED_OFFSET, struct.pack("<I", 0)
        )

    def hits(self, name: str) -> int:
        """Return how many times the target has reached the stub.

        Counted even while disabled: the hook still fired, only the dispatch was
        skipped.
        """

        hook = self._require(name)
        raw = self._access.read(hook.state_address + STATE_HITS_OFFSET, 4)
        return int(struct.unpack("<I", raw)[0])

    def wait_for_hits(
        self, name: str, minimum_delta: int = 1, timeout_ms: int = 2000
    ) -> int:
        """Wait until the hook has fired ``minimum_delta`` more times.

        This is how a placement is turned into evidence: the patch being written
        correctly says nothing about whether the function is running, and a
        counter that moves says it is.
        """

        if minimum_delta <= 0:
            raise ValueError("minimum_delta must be positive.")
        start = self.hits(name)
        deadline = time.monotonic() + timeout_ms / 1000.0
        while True:
            current = self.hits(name)
            if current - start >= minimum_delta:
                return current
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"pid {self._pid}: {name} fired {current - start} times in "
                    f"{timeout_ms} ms; {minimum_delta} were needed. The hook is "
                    "placed, but the function it is on did not run."
                )
            time.sleep(HIT_POLL_SECONDS)

    def remove(self, name: str, free_code: bool = False) -> None:
        """Restore the target's original bytes.

        The generated code is left mapped unless ``free_code`` is set: a thread may
        be inside the stub right now, and unmapping code an instruction pointer is
        heading into crashes the client. A caller that installs and removes hooks
        as a routine — a connection that sets this up on connect and tears it down
        on disconnect — asks for the release so its allocations do not accumulate
        in the client, and accepts the bounded wait below in place of proof.
        """

        hook = self._require(name)
        self.disable(name)
        self._patcher.restore(hook.target)
        del self._hooks[name]

        if free_code:
            time.sleep(FREE_WAIT_SECONDS)
            for address in (
                hook.stub_address,
                hook.trampoline_address,
                hook.state_address,
            ):
                self._access.free(address)

    def remove_all(self) -> None:
        """Remove every hook this hooker installed, newest first."""

        for name in reversed(sorted(self._hooks)):
            self.remove(name)

    # -- internals ---------------------------------------------------------

    def _require(self, name: str) -> _InstalledHook:
        hook = self._hooks.get(name)
        if hook is None:
            raise ValueError(f"no hook named {name!r} is installed.")
        return hook

    def _make_executable(self, address: int, data: bytes) -> None:
        """Write generated code, then make the region executable and not writable."""

        self._access.write(address, data)
        self._access.protect(address, len(data), PAGE_EXECUTE_READ)
        self._access.flush_instruction_cache(address, len(data))
