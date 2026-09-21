"""Explicitly owned read-only process-memory access."""

from __future__ import annotations

from typing import Protocol


class _win32_memory_api(Protocol):
    """The small Windows boundary needed by the reader."""

    def open_process_memory(self, pid: int) -> int: ...

    def close_process_memory(self, handle: int) -> None: ...

    def read_process_memory(self, handle: int, address: int, size: int) -> bytes: ...


class ProcessMemoryReader:
    """Read bytes from one process through the project's Win32 boundary."""

    def __init__(self, win32: _win32_memory_api, pid: int) -> None:
        """Open ``pid`` with query and read-only memory access."""

        self._win32 = win32
        self._pid = pid
        self._handle = win32.open_process_memory(pid)

    @property
    def pid(self) -> int:
        """Return the process ID owned by this reader."""

        return self._pid

    @property
    def is_closed(self) -> bool:
        """Return whether this reader has released its process handle."""

        return self._handle == 0

    def read(self, address: int, size: int) -> bytes:
        """Read exactly ``size`` bytes from the target address."""

        if self.is_closed:
            raise RuntimeError("The process memory reader is closed.")
        return self._win32.read_process_memory(self._handle, address, size)

    def close(self) -> None:
        """Release the process handle explicitly."""

        if self._handle:
            handle = self._handle
            self._handle = 0
            self._win32.close_process_memory(handle)

    def __enter__(self) -> ProcessMemoryReader:
        """Return this reader for a context-manager scope."""

        return self

    def __exit__(self, *_: object) -> None:
        """Close the reader when leaving a context-manager scope."""

        self.close()
