"""Write bytes into a running process, or refuse and leave it untouched.

This is the fail-closed half of the installer. It performs no Win32 calls of its
own: it takes an object that provides them, so the sequence, the checks and the
refusals can be tested with no client involved.

Why the sequence is what it is. Overwriting the first bytes of a function while
the client is *executing* them would crash it. Suspending the threads is not
enough on its own either: a thread suspended inside the window is still standing
in code that is about to change, and it would resume into the wrong instructions.
So the order is:

1. read the bytes and confirm they are what we expect, before touching anything;
2. suspend every thread of the target;
3. read each thread's instruction pointer and refuse if any of them is inside the
   range we are about to overwrite - release the threads, wait, and try again
   until the deadline, then refuse with a timeout;
4. re-read the bytes and confirm them again, because they could have changed
   while the threads were being suspended;
5. make the page writable, write, discard the instruction cache, restore the
   original page protection;
6. release every suspended thread and every handle, on every path.

Restoring is deliberately conditional. If the bytes at the address are no longer
the ones this installer wrote, it refuses and leaves the target alone: something
else has changed them, and putting our saved bytes back would corrupt code we no
longer own.
"""

from __future__ import annotations

import time
from typing import Protocol

#: ``PAGE_EXECUTE_READWRITE``. A page must be writable to be patched, and
#: executable again afterwards.
PAGE_EXECUTE_READWRITE = 0x40

#: ``PAGE_EXECUTE_READ``. What generated code is left as once it is written.
PAGE_EXECUTE_READ = 0x20

#: How long to keep retrying when a thread is standing in the window.
DEFAULT_TIMEOUT_MS = 2000

#: How long to wait between retries while a thread occupies the window.
RETRY_INTERVAL_SECONDS = 0.002


class TargetAccess(Protocol):
    """The calls the installer needs from the process it is writing to."""

    def read(self, address: int, size: int) -> bytes: ...

    def write(self, address: int, data: bytes) -> None: ...

    def protect(self, address: int, size: int, protection: int) -> int: ...

    def flush_instruction_cache(self, address: int, size: int) -> None: ...

    def list_thread_ids(self) -> list[int]: ...

    def open_thread(self, thread_id: int) -> int: ...

    def suspend_thread(self, thread_handle: int) -> int: ...

    def resume_thread(self, thread_handle: int) -> int: ...

    def thread_eip(self, thread_handle: int) -> int: ...

    def close_thread(self, thread_handle: int) -> None: ...


class Patcher:
    """Install and remove byte patches in one target process.

    One patcher owns one process. It remembers what it wrote, so :meth:`restore`
    can put the exact original bytes back and can tell whether the bytes are
    still its own.
    """

    def __init__(
        self,
        access: TargetAccess,
        pid: int,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
    ) -> None:
        """Create a patcher over an already-open target.

        ``access`` performs the calls; ``pid`` is carried only so failures can
        name the process they happened in.
        """

        if pid <= 0:
            raise ValueError("pid must be positive.")
        if timeout_ms <= 0:
            raise ValueError("timeout_ms must be positive.")

        self._access = access
        self._pid = pid
        self._timeout_ms = timeout_ms
        self._installed: dict[int, tuple[bytes, bytes]] = {}
        self._suspended: list[int] = []

    @property
    def pid(self) -> int:
        """Return the process this patcher writes to."""

        return self._pid

    @property
    def installed(self) -> tuple[int, ...]:
        """Return the addresses this patcher currently holds patched."""

        return tuple(sorted(self._installed))

    def patch(self, address: int, expected: bytes, replacement: bytes) -> None:
        """Replace ``expected`` with ``replacement`` at ``address``, or refuse."""

        self._validate(address, expected, replacement)
        if address in self._installed:
            raise RuntimeError(
                f"0x{address:08X} is already patched by this installer in pid "
                f"{self._pid}; restore it before patching again."
            )

        deadline = time.monotonic() + self._timeout_ms / 1000.0
        while True:
            self._verify(address, expected, "before the patch")
            self._suspend_target()
            try:
                if not self._any_thread_in(address, len(expected)):
                    # Re-read now that nothing can change it: the bytes could
                    # have moved between the first check and the suspension.
                    self._verify(address, expected, "while preparing the patch")
                    self._write_code(address, replacement)
                    break
            finally:
                self._resume_target()

            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"a thread of pid {self._pid} was still inside "
                    f"0x{address:08X}..0x{address + len(expected):08X} after "
                    f"{self._timeout_ms} ms. Nothing was written."
                )
            time.sleep(RETRY_INTERVAL_SECONDS)

        self._installed[address] = (expected, replacement)

    def restore(self, address: int) -> None:
        """Put the saved bytes back at ``address``, or refuse.

        Refuses when the address is not patched by this installer, and refuses
        when the bytes there are no longer the ones this installer wrote.
        """

        if address not in self._installed:
            raise RuntimeError(
                f"0x{address:08X} is not patched by this installer in pid "
                f"{self._pid}; there is nothing to restore."
            )

        expected, replacement = self._installed[address]
        self._verify(address, replacement, "before the restore")
        self._suspend_target()
        try:
            self._write_code(address, expected)
        finally:
            self._resume_target()

        del self._installed[address]

    def restore_all(self) -> None:
        """Restore every patch this installer holds, newest first."""

        for address in sorted(self._installed, reverse=True):
            self.restore(address)

    # -- internals ---------------------------------------------------------

    def _validate(self, address: int, expected: bytes, replacement: bytes) -> None:
        if address <= 0:
            raise ValueError("address must be positive.")
        if not expected:
            raise ValueError("expected bytes must not be empty.")
        if len(expected) != len(replacement):
            raise ValueError(
                f"the patch must not change length: {len(expected)} bytes "
                f"expected, {len(replacement)} supplied."
            )

    def _verify(self, address: int, expected: bytes, when: str) -> None:
        """Confirm the bytes on the target, or refuse and say what was found."""

        observed = self._access.read(address, len(expected))
        if observed != expected:
            raise RuntimeError(
                f"code at 0x{address:08X} {when} is not what this installer "
                f"expected in pid {self._pid}: expected {expected.hex(' ')}, "
                f"observed {observed.hex(' ')}. Nothing was written."
            )

    def _suspend_target(self) -> None:
        """Suspend every thread of the target, remembering the handles."""

        if self._suspended:
            raise RuntimeError(
                "the target is already suspended; patches are not re-entrant."
            )

        handles: list[int] = []
        try:
            for thread_id in self._access.list_thread_ids():
                handle = self._access.open_thread(thread_id)
                try:
                    self._access.suspend_thread(handle)
                except BaseException:
                    self._access.close_thread(handle)
                    raise
                handles.append(handle)
        except BaseException:
            self._suspended = handles
            self._resume_target()
            raise

        self._suspended = handles

    def _resume_target(self) -> None:
        """Release every suspended thread, in reverse, closing each handle."""

        handles, self._suspended = self._suspended, []
        for handle in reversed(handles):
            try:
                self._access.resume_thread(handle)
            finally:
                self._access.close_thread(handle)

    def _any_thread_in(self, address: int, length: int) -> bool:
        """Return whether any suspended thread is standing in the patch window.

        Only a zero instruction pointer is treated as implausible, which is what
        a context that was never filled reads back as. The stricter test of
        requiring the pointer to sit inside a known executable region is
        deliberately not used: a thread parked in a system DLL is ordinary, and
        that test refuses legitimate patches.
        """

        end = address + length
        for handle in self._suspended:
            eip = self._access.thread_eip(handle)
            if eip == 0:
                raise RuntimeError(
                    f"a thread of pid {self._pid} reported a zero instruction "
                    "pointer, so the context cannot be trusted. Nothing was written."
                )
            if address <= eip < end:
                return True
        return False

    def _write_code(self, address: int, data: bytes) -> None:
        """Write ``data`` as executable code and put the protection back."""

        previous = self._access.protect(address, len(data), PAGE_EXECUTE_READWRITE)
        try:
            self._access.write(address, data)
            self._access.flush_instruction_cache(address, len(data))
        finally:
            self._access.protect(address, len(data), previous)
