"""The invasive half of the Windows surface: memory writes and thread control.

Deliberately separate from :class:`py4gw.win32.win32.Win32`. That class documents
itself as never requesting permission to write or execute code in another
process, and that guarantee is worth keeping. Everything here does the opposite,
so it lives on its own and is never opened by accident.

Nothing in this module decides *whether* a write is safe. It performs the calls;
:mod:`py4gw.game_thread.patcher` owns the sequence, the checks and the refusals.

Opening a process this way needs an elevated controller. Unelevated, Windows
denies ``PROCESS_VM_WRITE``, ``PROCESS_VM_OPERATION``, ``PROCESS_CREATE_THREAD``
and ``PROCESS_SUSPEND_RESUME`` with error 5 by ordinary UAC token splitting.
That is not a client protection.
"""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes

#: A 32-bit thread context, sized for ``GetThreadContext``.
CONTEXT_SIZE = 716
#: ``Eip`` sits at this offset inside the 32-bit context, after the debug
#: registers, the 112-byte floating-save area, the segment registers and the
#: general registers.
CONTEXT_EIP_OFFSET = 184
CONTEXT_CONTROL = 0x00010001


class WriteAccess:
    """Open one process for writing, and report failure with its context.

    The caller owns the handle. Use :meth:`close`, or the context manager, so the
    handle is released even when a later step raises.
    """

    _PROCESS_CREATE_THREAD = 0x0002
    _PROCESS_VM_OPERATION = 0x0008
    _PROCESS_VM_READ = 0x0010
    _PROCESS_VM_WRITE = 0x0020
    _PROCESS_QUERY_INFORMATION = 0x0400

    _THREAD_SUSPEND_RESUME = 0x0002
    _THREAD_GET_CONTEXT = 0x0008
    _THREAD_QUERY_INFORMATION = 0x0040

    _MEM_COMMIT = 0x1000
    _MEM_RESERVE = 0x2000
    _MEM_RELEASE = 0x8000

    PAGE_READWRITE = 0x04
    PAGE_EXECUTE_READ = 0x20
    PAGE_EXECUTE_READWRITE = 0x40

    _SNAPSHOT_THREADS = 0x00000004
    _ERROR_NO_MORE_FILES = 18
    _ERROR_ACCESS_DENIED = 5
    _ERROR_PARTIAL_COPY = 299

    class _thread_entry(ctypes.Structure):
        """The Windows structure filled by ``Thread32First/Next``."""

        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ThreadID", wintypes.DWORD),
            ("th32OwnerProcessID", wintypes.DWORD),
            ("tpBasePri", ctypes.c_long),
            ("tpDeltaPri", ctypes.c_long),
            ("dwFlags", wintypes.DWORD),
        ]

    def __init__(self, pid: int) -> None:
        """Open ``pid`` for reading, writing, allocating and thread control."""

        if pid <= 0:
            raise ValueError("pid must be positive.")
        if pid == os.getpid():
            raise ValueError(
                "refusing to open a write transport to this process: suspending "
                "its threads would hang the controller."
            )

        self._pid = pid
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._set_function_signatures()

        access = (
            self._PROCESS_CREATE_THREAD
            | self._PROCESS_VM_OPERATION
            | self._PROCESS_VM_READ
            | self._PROCESS_VM_WRITE
            | self._PROCESS_QUERY_INFORMATION
        )
        handle = self._kernel32.OpenProcess(access, False, pid)
        if not handle:
            self._raise_last_error(f"OpenProcess(pid={pid}, write access)")
        self._handle = int(handle)
        if not self._handle:
            raise OSError(f"OpenProcess(pid={pid}) returned an invalid handle.")

    @property
    def pid(self) -> int:
        """Return the process this transport writes to."""

        return self._pid

    @property
    def handle(self) -> int:
        """Return the process handle, or zero once closed."""

        return self._handle

    def close(self) -> None:
        """Release the process handle. Safe to call more than once."""

        if self._handle:
            handle, self._handle = self._handle, 0
            if not self._kernel32.CloseHandle(handle):
                self._raise_last_error("CloseHandle(process)")

    def __enter__(self) -> WriteAccess:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    # -- memory ------------------------------------------------------------

    def read(self, address: int, size: int) -> bytes:
        """Read exactly ``size`` bytes, or raise ``OSError``."""

        self._require_open()
        if address < 0:
            raise ValueError("address cannot be negative.")
        if size <= 0:
            raise ValueError("size must be positive.")

        buffer = ctypes.create_string_buffer(size)
        bytes_read = ctypes.c_size_t()
        success = self._kernel32.ReadProcessMemory(
            self._handle,
            ctypes.c_void_p(address),
            buffer,
            size,
            ctypes.byref(bytes_read),
        )
        if not success:
            self._raise_last_error(
                f"ReadProcessMemory(address=0x{address:X}, size=0x{size:X})"
            )
        if bytes_read.value != size:
            self._raise_error(
                f"ReadProcessMemory(address=0x{address:X}, size=0x{size:X})",
                self._ERROR_PARTIAL_COPY,
            )
        return bytes(buffer.raw)

    def write(self, address: int, data: bytes) -> None:
        """Write ``data`` at ``address``, or raise ``OSError``."""

        self._require_open()
        if address < 0:
            raise ValueError("address cannot be negative.")
        if not data:
            raise ValueError("data must not be empty.")

        written = ctypes.c_size_t()
        buffer = ctypes.create_string_buffer(data, len(data))
        success = self._kernel32.WriteProcessMemory(
            self._handle,
            ctypes.c_void_p(address),
            buffer,
            len(data),
            ctypes.byref(written),
        )
        if not success:
            self._raise_last_error(
                f"WriteProcessMemory(address=0x{address:X}, size=0x{len(data):X})"
            )
        if written.value != len(data):
            self._raise_error(
                f"WriteProcessMemory(address=0x{address:X}, size=0x{len(data):X})",
                self._ERROR_PARTIAL_COPY,
            )

    def allocate(self, size: int) -> int:
        """Commit ``size`` writable bytes in the target and return the address."""

        self._require_open()
        if size <= 0:
            raise ValueError("size must be positive.")

        address = self._kernel32.VirtualAllocEx(
            self._handle,
            None,
            size,
            self._MEM_COMMIT | self._MEM_RESERVE,
            self.PAGE_READWRITE,
        )
        if not address:
            self._raise_last_error(f"VirtualAllocEx(size=0x{size:X})")
        return int(address)

    def free(self, address: int) -> None:
        """Release a region returned by :meth:`allocate`."""

        self._require_open()
        if not address:
            return
        if not self._kernel32.VirtualFreeEx(
            self._handle, ctypes.c_void_p(address), 0, self._MEM_RELEASE
        ):
            self._raise_last_error(f"VirtualFreeEx(address=0x{address:X})")

    def protect(self, address: int, size: int, protection: int) -> int:
        """Set page protection and return the previous value."""

        self._require_open()
        if address <= 0:
            raise ValueError("address must be positive.")
        if size <= 0:
            raise ValueError("size must be positive.")

        previous = wintypes.DWORD()
        if not self._kernel32.VirtualProtectEx(
            self._handle,
            ctypes.c_void_p(address),
            size,
            protection,
            ctypes.byref(previous),
        ):
            self._raise_last_error(
                f"VirtualProtectEx(address=0x{address:X}, protection=0x{protection:X})"
            )
        return int(previous.value)

    def flush_instruction_cache(self, address: int, size: int) -> None:
        """Discard cached instructions for a range that was just written."""

        self._require_open()
        if not self._kernel32.FlushInstructionCache(
            self._handle, ctypes.c_void_p(address), size
        ):
            self._raise_last_error(f"FlushInstructionCache(address=0x{address:X})")

    # -- threads -----------------------------------------------------------

    def list_thread_ids(self) -> list[int]:
        """Return the ids of every thread owned by the target process."""

        self._require_open()
        snapshot = self._kernel32.CreateToolhelp32Snapshot(
            self._SNAPSHOT_THREADS, 0
        )
        if snapshot == ctypes.c_void_p(-1).value:
            self._raise_last_error("CreateToolhelp32Snapshot(threads)")

        entry = self._thread_entry()
        entry.dwSize = ctypes.sizeof(self._thread_entry)
        thread_ids: list[int] = []
        try:
            ok = self._kernel32.Thread32First(snapshot, ctypes.byref(entry))
            while ok:
                if entry.th32OwnerProcessID == self._pid:
                    thread_ids.append(int(entry.th32ThreadID))
                ok = self._kernel32.Thread32Next(snapshot, ctypes.byref(entry))
            error_code = ctypes.get_last_error()
            if error_code != self._ERROR_NO_MORE_FILES:
                self._raise_error(
                    f"Thread32Next(pid={self._pid})", error_code
                )
        finally:
            self._kernel32.CloseHandle(snapshot)

        if not thread_ids:
            raise OSError(
                f"no threads were found for pid {self._pid}; refusing to patch "
                "without knowing whether the target is executing the bytes."
            )
        return thread_ids

    def open_thread(self, thread_id: int) -> int:
        """Open one thread for suspending and reading its context."""

        self._require_open()
        if thread_id <= 0:
            raise ValueError("thread_id must be positive.")
        access = (
            self._THREAD_SUSPEND_RESUME
            | self._THREAD_GET_CONTEXT
            | self._THREAD_QUERY_INFORMATION
        )
        handle = self._kernel32.OpenThread(access, False, thread_id)
        if not handle:
            self._raise_last_error(f"OpenThread(thread_id={thread_id})")
        return int(handle)

    def suspend_thread(self, thread_handle: int) -> int:
        """Suspend one thread and return its previous suspend count."""

        previous = self._kernel32.SuspendThread(thread_handle)
        if previous == 0xFFFFFFFF:
            self._raise_last_error("SuspendThread")
        return int(previous)

    def resume_thread(self, thread_handle: int) -> int:
        """Resume one thread and return its previous suspend count."""

        previous = self._kernel32.ResumeThread(thread_handle)
        if previous == 0xFFFFFFFF:
            self._raise_last_error("ResumeThread")
        return int(previous)

    def thread_eip(self, thread_handle: int) -> int:
        """Return one suspended thread's instruction pointer."""

        context = ctypes.create_string_buffer(CONTEXT_SIZE)
        ctypes.memmove(context, ctypes.byref(wintypes.DWORD(CONTEXT_CONTROL)), 4)
        if not self._kernel32.GetThreadContext(thread_handle, context):
            self._raise_last_error("GetThreadContext")
        return int.from_bytes(
            context.raw[CONTEXT_EIP_OFFSET : CONTEXT_EIP_OFFSET + 4], "little"
        )

    def close_thread(self, thread_handle: int) -> None:
        """Release a thread handle. Safe to call with zero."""

        if thread_handle and not self._kernel32.CloseHandle(thread_handle):
            self._raise_last_error("CloseHandle(thread)")

    # -- internals ---------------------------------------------------------

    def _require_open(self) -> None:
        if not self._handle:
            raise OSError(f"the write transport to pid {self._pid} is closed.")

    def _raise_last_error(self, operation: str) -> None:
        self._raise_error(operation, ctypes.get_last_error())

    def _raise_error(self, operation: str, error_code: int) -> None:
        raise OSError(
            error_code,
            f"{operation} failed for pid {self._pid}: {ctypes.FormatError(error_code)}",
        )

    def _set_function_signatures(self) -> None:
        """Tell ``ctypes`` the argument and return types for each API call."""

        k = self._kernel32
        k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k.OpenProcess.restype = wintypes.HANDLE
        k.CloseHandle.argtypes = [wintypes.HANDLE]
        k.CloseHandle.restype = wintypes.BOOL
        k.ReadProcessMemory.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_size_t),
        ]
        k.ReadProcessMemory.restype = wintypes.BOOL
        k.WriteProcessMemory.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_size_t),
        ]
        k.WriteProcessMemory.restype = wintypes.BOOL
        k.VirtualAllocEx.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
            ctypes.c_size_t,
            wintypes.DWORD,
            wintypes.DWORD,
        ]
        k.VirtualAllocEx.restype = ctypes.c_void_p
        k.VirtualFreeEx.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
            ctypes.c_size_t,
            wintypes.DWORD,
        ]
        k.VirtualFreeEx.restype = wintypes.BOOL
        k.VirtualProtectEx.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
            ctypes.c_size_t,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
        ]
        k.VirtualProtectEx.restype = wintypes.BOOL
        k.FlushInstructionCache.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
            ctypes.c_size_t,
        ]
        k.FlushInstructionCache.restype = wintypes.BOOL
        k.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
        k.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
        k.Thread32First.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
        k.Thread32First.restype = wintypes.BOOL
        k.Thread32Next.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
        k.Thread32Next.restype = wintypes.BOOL
        k.OpenThread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k.OpenThread.restype = wintypes.HANDLE
        k.SuspendThread.argtypes = [wintypes.HANDLE]
        k.SuspendThread.restype = wintypes.DWORD
        k.ResumeThread.argtypes = [wintypes.HANDLE]
        k.ResumeThread.restype = wintypes.DWORD
        k.GetThreadContext.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
        k.GetThreadContext.restype = wintypes.BOOL
