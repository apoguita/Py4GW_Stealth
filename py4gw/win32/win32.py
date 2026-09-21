"""The single Windows process-handling class used by the first library step."""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from typing import Any


class Win32:
    """Handle the small Windows API surface needed to find ``Gw.exe``.

    A ``Win32`` object is a stateless helper around the Windows process list.
    Each listing is a new snapshot. The object does not keep process handles
    open between calls and never requests permission to write or execute code
    in another process.
    """

    _SNAPSHOT_PROCESSES = 0x00000002
    _SNAPSHOT_MODULES = 0x00000008 | 0x00000010
    _QUERY_LIMITED_INFORMATION = 0x00001000
    _QUERY_INFORMATION = 0x00000400
    _PROCESS_VM_READ = 0x00000010
    _ERROR_NO_MORE_FILES = 18
    _ERROR_ACCESS_DENIED = 5
    _ERROR_INSUFFICIENT_BUFFER = 122
    _ERROR_PARTIAL_COPY = 299
    _MAX_PATH_CHARS = 32768
    _GW_EXE = "Gw.exe"

    class _process_entry(ctypes.Structure):
        """The Windows structure filled by ``Process32First/NextW``."""

        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * 260),
        ]

    class _module_entry(ctypes.Structure):
        """The Windows structure filled by ``Module32First/NextW``."""

        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("th32ModuleID", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("GlblcntUsage", wintypes.DWORD),
            ("ProccntUsage", wintypes.DWORD),
            ("modBaseAddr", ctypes.c_void_p),
            ("modBaseSize", wintypes.DWORD),
            ("hModule", wintypes.HMODULE),
            ("szModule", wintypes.WCHAR * 256),
            ("szExePath", wintypes.WCHAR * 260),
        ]

    class _module_information(ctypes.Structure):
        """The small structure filled by ``GetModuleInformation``."""

        _fields_ = [
            ("lpBaseOfDll", ctypes.c_void_p),
            ("SizeOfImage", wintypes.DWORD),
            ("EntryPoint", ctypes.c_void_p),
        ]

    def __init__(self) -> None:
        """Load Kernel32 and prepare the functions used by this class."""

        if os.name != "nt":
            raise OSError("Win32 is available only on Windows.")
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._psapi = ctypes.WinDLL("psapi", use_last_error=True)
        self._set_function_signatures()

    def list_processes(self) -> list[dict[str, Any]]:
        """Return a current, PID-sorted list of running processes."""

        snapshot = self._kernel32.CreateToolhelp32Snapshot(
            self._SNAPSHOT_PROCESSES, 0
        )
        if snapshot == ctypes.c_void_p(-1).value:
            self._raise_last_error("CreateToolhelp32Snapshot")

        processes: list[dict[str, Any]] = []
        try:
            entry = self._new_process_entry()
            if not self._kernel32.Process32FirstW(snapshot, ctypes.byref(entry)):
                error_code = ctypes.get_last_error()
                if error_code == self._ERROR_NO_MORE_FILES:
                    return []
                self._raise_error("Process32FirstW", error_code)

            while True:
                processes.append(
                    {
                        "pid": int(entry.th32ProcessID),
                        "name": str(entry.szExeFile),
                    }
                )
                entry = self._new_process_entry()
                if self._kernel32.Process32NextW(snapshot, ctypes.byref(entry)):
                    continue
                error_code = ctypes.get_last_error()
                if error_code != self._ERROR_NO_MORE_FILES:
                    self._raise_error("Process32NextW", error_code)
                break
        finally:
            self._close_handle(snapshot)

        return sorted(processes, key=lambda process: process["pid"])

    def find_guild_wars(self) -> list[dict[str, Any]]:
        """Return every running process whose name is ``Gw.exe``.

        Matching is case-insensitive. A path lookup failure leaves the process
        in the result with ``path`` set to ``None`` and ``path_error`` set to
        the Windows error number.
        """

        matches: list[dict[str, Any]] = []
        for process in self.list_processes():
            if not self._is_guild_wars_name(process["name"]):
                continue
            path, error_code = self._get_image_path(process["pid"])
            matches.append(
                {
                    "pid": process["pid"],
                    "name": process["name"],
                    "path": path,
                    "path_error": error_code,
                }
            )
        return matches

    def format_processes(self, processes: list[dict[str, Any]]) -> str:
        """Turn process records into a simple table for a console or log."""

        if not processes:
            return "No Gw.exe candidates are currently running."

        rows = [("PID", "Name", "Path")]
        for process in processes:
            path = process.get("path")
            if path is None:
                path = f"<unavailable; Windows error {process.get('path_error')}>"
            rows.append((str(process["pid"]), str(process["name"]), str(path)))

        widths = [max(len(row[column]) for row in rows) for column in range(3)]
        output = [self._format_row(rows[0], widths)]
        output.append("-+-".join("-" * width for width in widths))
        output.extend(self._format_row(row, widths) for row in rows[1:])
        return "\n".join(output)

    def open_process_memory(self, pid: int) -> int:
        """Open one process for query and read-only memory access.

        The caller owns the returned handle and must pass it to
        :meth:`close_process_memory` when finished.
        """

        if pid <= 0:
            raise ValueError("pid must be positive.")
        access = self._QUERY_INFORMATION | self._PROCESS_VM_READ
        handle = self._kernel32.OpenProcess(access, False, pid)
        if not handle:
            self._raise_last_error(f"OpenProcess(pid={pid})")
        if isinstance(handle, int):
            return handle
        if isinstance(handle, ctypes.c_void_p) and handle.value is not None:
            return int(handle.value)
        raise OSError("OpenProcess returned an invalid handle.")

    def close_process_memory(self, handle: int) -> None:
        """Close a process handle returned by :meth:`open_process_memory`."""

        if handle and not self._kernel32.CloseHandle(handle):
            self._raise_last_error("CloseHandle")

    def read_process_memory(self, handle: int, address: int, size: int) -> bytes:
        """Read exactly ``size`` bytes from a process handle.

        A failed or partial read raises ``OSError`` with the original Windows
        error number. The operation never writes to the target process.
        """

        if not handle:
            raise ValueError("handle must be valid.")
        if address < 0:
            raise ValueError("address cannot be negative.")
        if size <= 0:
            raise ValueError("size must be positive.")

        buffer = ctypes.create_string_buffer(size)
        bytes_read = ctypes.c_size_t()
        success = self._kernel32.ReadProcessMemory(
            handle,
            ctypes.c_void_p(address),
            buffer,
            size,
            ctypes.byref(bytes_read),
        )
        if not success:
            error_code = ctypes.get_last_error()
            self._raise_error(
                f"ReadProcessMemory(address=0x{address:X}, size=0x{size:X})",
                error_code,
            )
        if bytes_read.value != size:
            self._raise_error(
                f"ReadProcessMemory(address=0x{address:X}, size=0x{size:X})",
                self._ERROR_PARTIAL_COPY,
            )
        return bytes(buffer.raw)

    def get_main_module(self, pid: int) -> dict[str, Any]:
        """Return the first module's base, size, name, and path for ``pid``."""

        if pid <= 0:
            raise ValueError("pid must be positive.")
        snapshot = self._kernel32.CreateToolhelp32Snapshot(
            self._SNAPSHOT_MODULES, pid
        )
        if snapshot == ctypes.c_void_p(-1).value:
            error_code = ctypes.get_last_error()
            if error_code == self._ERROR_ACCESS_DENIED:
                return self._get_main_module_with_psapi(pid)
            self._raise_error(
                f"CreateToolhelp32Snapshot(pid={pid})", error_code
            )

        try:
            entry = self._new_module_entry()
            if not self._kernel32.Module32FirstW(snapshot, ctypes.byref(entry)):
                self._raise_last_error(f"Module32FirstW(pid={pid})")
            return {
                "base_address": int(entry.modBaseAddr or 0),
                "size": int(entry.modBaseSize),
                "name": str(entry.szModule),
                "path": str(entry.szExePath),
            }
        finally:
            self._close_handle(snapshot)

    def _is_guild_wars_name(self, name: str) -> bool:
        """Apply the only Guild Wars detection rule used in this first step."""

        return name.casefold() == self._GW_EXE.casefold()

    def _get_main_module_with_psapi(self, pid: int) -> dict[str, Any]:
        """Use PSAPI when Toolhelp module enumeration is denied."""

        handle = self.open_process_memory(pid)
        try:
            modules = (wintypes.HMODULE * 256)()
            needed = wintypes.DWORD()
            if not self._psapi.EnumProcessModulesEx(
                handle,
                modules,
                ctypes.sizeof(modules),
                ctypes.byref(needed),
                0x03,
            ):
                self._raise_last_error(f"EnumProcessModulesEx(pid={pid})")
            if needed.value < ctypes.sizeof(wintypes.HMODULE):
                self._raise_error(
                    f"EnumProcessModulesEx(pid={pid})", self._ERROR_PARTIAL_COPY
                )

            module = modules[0]
            information = self._module_information()
            if not self._psapi.GetModuleInformation(
                handle,
                module,
                ctypes.byref(information),
                ctypes.sizeof(information),
            ):
                self._raise_last_error(f"GetModuleInformation(pid={pid})")

            path, path_error = self._get_image_path(pid)
            name = os.path.basename(path) if path else self._GW_EXE
            return {
                "base_address": int(information.lpBaseOfDll or 0),
                "size": int(information.SizeOfImage),
                "name": name,
                "path": path,
                "path_error": path_error,
            }
        finally:
            self.close_process_memory(handle)

    def _get_image_path(self, pid: int) -> tuple[str | None, int | None]:
        """Read one image path with limited query access and close its handle."""

        handle = self._kernel32.OpenProcess(
            self._QUERY_LIMITED_INFORMATION, False, pid
        )
        if not handle:
            return None, ctypes.get_last_error()

        try:
            capacity = 260
            while capacity <= self._MAX_PATH_CHARS:
                buffer = ctypes.create_unicode_buffer(capacity)
                size = wintypes.DWORD(capacity)
                if self._kernel32.QueryFullProcessImageNameW(
                    handle, 0, buffer, ctypes.byref(size)
                ):
                    return buffer.value, None
                error_code = ctypes.get_last_error()
                if error_code != self._ERROR_INSUFFICIENT_BUFFER:
                    return None, error_code
                capacity *= 2
            return None, self._ERROR_INSUFFICIENT_BUFFER
        finally:
            self._close_handle(handle)

    def _new_process_entry(self) -> _process_entry:
        """Create a process-entry buffer with its required size set."""

        entry = self._process_entry()
        entry.dwSize = ctypes.sizeof(self._process_entry)
        return entry

    def _new_module_entry(self) -> _module_entry:
        """Create a module-entry buffer with its required size set."""

        entry = self._module_entry()
        entry.dwSize = ctypes.sizeof(self._module_entry)
        return entry

    def _close_handle(self, handle: Any) -> None:
        """Close one handle owned by this operation."""

        self._kernel32.CloseHandle(handle)

    def _raise_last_error(self, operation: str) -> None:
        """Raise a readable exception using the current Windows error."""

        self._raise_error(operation, ctypes.get_last_error())

    def _raise_error(self, operation: str, error_code: int) -> None:
        """Keep Win32 error handling inside this class."""

        message = f"{operation} failed with Windows error {error_code}"
        raise OSError(error_code, message)

    def _format_row(self, row: tuple[str, str, str], widths: list[int]) -> str:
        """Align one display row using the widths calculated by the caller."""

        return " | ".join(
            value.ljust(widths[column]) for column, value in enumerate(row)
        )

    def _set_function_signatures(self) -> None:
        """Tell ``ctypes`` the argument and return types for each API call."""

        self._kernel32.CreateToolhelp32Snapshot.argtypes = [
            wintypes.DWORD,
            wintypes.DWORD,
        ]
        self._kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
        self._kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
        self._kernel32.Process32FirstW.restype = wintypes.BOOL
        self._kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
        self._kernel32.Process32NextW.restype = wintypes.BOOL
        self._kernel32.OpenProcess.argtypes = [
            wintypes.DWORD,
            wintypes.BOOL,
            wintypes.DWORD,
        ]
        self._kernel32.OpenProcess.restype = wintypes.HANDLE
        self._kernel32.QueryFullProcessImageNameW.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
        ]
        self._kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
        self._kernel32.ReadProcessMemory.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_size_t),
        ]
        self._kernel32.ReadProcessMemory.restype = wintypes.BOOL
        self._kernel32.Module32FirstW.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
        ]
        self._kernel32.Module32FirstW.restype = wintypes.BOOL
        self._kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self._kernel32.CloseHandle.restype = wintypes.BOOL
        self._psapi.EnumProcessModulesEx.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.HMODULE),
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            wintypes.DWORD,
        ]
        self._psapi.EnumProcessModulesEx.restype = wintypes.BOOL
        self._psapi.GetModuleInformation.argtypes = [
            wintypes.HANDLE,
            wintypes.HMODULE,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        self._psapi.GetModuleInformation.restype = wintypes.BOOL
