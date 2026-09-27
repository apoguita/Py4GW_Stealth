"""The client's own memory-manager globals, ported from Native's ``PY4GW::MemoryManager``.

**Source.** ``include/base/memory_manager.h:9-20`` declares seven members, and
``src/base/memory_manager.cpp`` implements them:

```text
Scan()                        resolve the globals the other members use       memory_manager.cpp:38-63
GetGWVersion()                g_get_gw_version_func()          :65-67        the client's own call
GetSkillTimer()               timeGetTime() + *g_skill_timer_ptr  :69-71
GetGWWindowHandle()           *g_window_handle_ptr             :73-75
MemAlloc(size)                g_mem_alloc_helper_func(size)    :77-82
MemRealloc(buffer, size)      g_mem_realloc_helper_func(...)   :84-89
MemFree(buffer)               g_mem_free_func(buffer)          :91-93
```

**Why it is here.** ``Context::Effect::GetTimeElapsed`` is
``PY4GW::MemoryManager::GetSkillTimer() - timestamp`` and ``GetTimeRemaining`` subtracts that from
``duration * 1000`` (``skill.cpp:39-45``), so the effect snapshot Reforged's ``Effects`` class
returns cannot be built without this timer. ``SkillbarSkill::GetRecharge`` is the same subtraction
from the other side (``skill.cpp:20-25``). Two classes were raising for exactly this.

**What each member is here, in this port's terms.**

- ``GetSkillTimer``, ``GetGWWindowHandle`` and ``GetGWVersion``'s pointer are **reads**: the globals
  are in the catalog (``offsets/memory.json``: ``skill_timer_ptr``, ``window_handle_ptr``,
  ``gw_version_func``), so they are resolved with the pattern catalog and read through the process
  reader. ``timeGetTime`` is a documented ``winmm`` call from this process, which is what the
  source calls too.
- ``GetGWVersion`` and the three allocators are **calls into the client**, issued on its own thread
  through ``py4gw/game_thread`` — the port of what the injected runtime gets for free. They need a
  connection made with the capability layer (``py4gw.connect()``), and this module says so by
  letting those calls raise rather than answering a stand-in.

**One divergence, and it is the resolution model.** The source resolves every pointer once in
``Scan()`` and holds it for the process's life. This port has no startup pass to hang that on, so a
member resolves what it needs when it is first asked (the rule every reader here follows), and
``Scan()`` is kept as the source's own step for a caller that wants them all resolved at once.
"""

from __future__ import annotations

import ctypes
from typing import Optional, Protocol

from ..scanner import PatternCatalog, RemoteScanner


class _memory_reader(Protocol):
    """The byte-reading operation needed by the readable globals."""

    def read(self, address: int, size: int) -> bytes: ...


#: ``DWORD`` arithmetic wraps at 32 bits, and the client's timer is a ``DWORD``.
_DWORD_MASK = 0xFFFFFFFF

#: ``winmm!timeGetTime`` — milliseconds since Windows started, the host half of the skill timer.
#: The source links it the same way (``memory_manager.cpp:70``); nothing here reads a client field
#: for it, because the client does not have one.
_winmm: Optional[ctypes.WinDLL] = None


def _time_get_time() -> int:
    """``timeGetTime()`` (``memory_manager.cpp:70``): the host's millisecond clock."""

    global _winmm
    if _winmm is None:
        winmm = ctypes.WinDLL("winmm", use_last_error=True)
        winmm.timeGetTime.restype = ctypes.c_uint32
        winmm.timeGetTime.argtypes = []
        _winmm = winmm
    return int(_winmm.timeGetTime())


class MemoryManager:
    """The ported ``PY4GW::MemoryManager``: one instance per connected client."""

    #: The catalog names the source's own globals under (``offsets/memory.json``).
    _SKILL_TIMER_RESOLVER = "memory.skill_timer_ptr"
    _WINDOW_HANDLE_RESOLVER = "memory.window_handle_ptr"
    _GW_VERSION_RESOLVER = "memory.gw_version_func"
    _MEM_ALLOC_RESOLVER = "memory.mem_alloc_helper_func"
    _MEM_REALLOC_RESOLVER = "memory.mem_realloc_helper_func"
    _MEM_FREE_RESOLVER = "memory.mem_free_func"

    def __init__(
        self,
        reader: _memory_reader,
        scanner: RemoteScanner,
        patterns: PatternCatalog,
    ) -> None:
        """Create a reader for one connected client's memory-manager globals."""

        self._reader = reader
        self._scanner = scanner
        self._patterns = patterns
        self._skill_timer_ptr: int | None = None
        self._window_handle_ptr: int | None = None

    def _resolve(self, name: str) -> int:
        """Resolve one catalog name, or ``0`` when it does not resolve.

        The source's own idiom: a member whose pointer is null answers its null-path rather than
        calling something that is not there (``memory_manager.cpp:66, 70, 74``).
        """

        result = self._patterns.resolve(name, self._scanner)
        if not result.ok:
            return 0
        return int(result.value)

    def Scan(self) -> bool:
        """``MemoryManager::Scan`` (``memory_manager.cpp:38-63``): resolve the globals.

        The source resolves the skill timer, the window handle, the version function and the three
        allocation helpers, and answers ``false`` unless the last three are all there. This port
        resolves the two readable globals here and reports whether they are present; the three
        helpers are resolved by the members that call them, because resolving a callable here would
        not make its calls legal — the connection is what does that.
        """

        self._skill_timer_ptr = self._resolve(self._SKILL_TIMER_RESOLVER)
        self._window_handle_ptr = self._resolve(self._WINDOW_HANDLE_RESOLVER)
        return bool(self._skill_timer_ptr and self._window_handle_ptr)

    def GetSkillTimer(self) -> int:
        """``MemoryManager::GetSkillTimer`` (``memory_manager.cpp:69-71``).

        ``g_skill_timer_ptr ? timeGetTime() + *g_skill_timer_ptr : timeGetTime()`` — the same
        short-circuit, with the client's own timer offset added to the host clock.
        """

        pointer = self._skill_timer_ptr or self._resolve(self._SKILL_TIMER_RESOLVER)
        self._skill_timer_ptr = pointer
        now = _time_get_time()
        if not pointer:
            return now
        offset = int.from_bytes(self._reader.read(pointer, 4), "little")
        return (now + offset) & _DWORD_MASK

    def GetGWWindowHandle(self) -> int:
        """``MemoryManager::GetGWWindowHandle`` (``memory_manager.cpp:73-75``).

        The source reads ``HWND`` out of its global; the value is a target-process handle, so it is
        four bytes here and never a host window handle — the same distinction every pointer in this
        port keeps.
        """

        pointer = self._window_handle_ptr or self._resolve(self._WINDOW_HANDLE_RESOLVER)
        self._window_handle_ptr = pointer
        if not pointer:
            return 0
        return int.from_bytes(self._reader.read(pointer, 4), "little")

    def GetGWVersion(self) -> int:
        """``MemoryManager::GetGWVersion`` (``memory_manager.cpp:65-67``).

        ``g_get_gw_version_func ? g_get_gw_version_func() : 0`` — the client's own version call,
        issued on its own thread, and ``0`` when the catalog has no such function.
        """

        from ..client import require_client
        from ..game_thread.shared_block import CallForm

        client = require_client()
        if not client.resolves(self._GW_VERSION_RESOLVER):
            return 0
        return int(
            client.call_function(self._GW_VERSION_RESOLVER, CallForm.NO_ARGS).value
        )

    def MemAlloc(self, size: int) -> int:
        """``MemoryManager::MemAlloc`` (``memory_manager.cpp:77-82``): the client's allocator.

        ``nullptr`` becomes ``0``, which is the answer the source gives when its helper is absent.
        """

        from ..client import require_client
        from ..game_thread.shared_block import CallForm

        client = require_client()
        if not client.resolves(self._MEM_ALLOC_RESOLVER):
            return 0
        return int(
            client.call_function(self._MEM_ALLOC_RESOLVER, CallForm.U32, int(size)).value
        )

    def MemRealloc(self, buffer: int, new_size: int) -> int:
        """``MemoryManager::MemRealloc`` (``memory_manager.cpp:84-89``)."""

        from ..client import require_client
        from ..game_thread.shared_block import CallForm

        client = require_client()
        if not client.resolves(self._MEM_REALLOC_RESOLVER):
            return 0
        return int(
            client.call_function(
                self._MEM_REALLOC_RESOLVER, CallForm.U32_U32, int(buffer), int(new_size)
            ).value
        )

    def MemFree(self, buffer: int) -> None:
        """``MemoryManager::MemFree`` (``memory_manager.cpp:91-93``): no answer, like the source."""

        from ..client import require_client
        from ..game_thread.shared_block import CallForm

        client = require_client()
        if not client.resolves(self._MEM_FREE_RESOLVER):
            return
        client.call_function(self._MEM_FREE_RESOLVER, CallForm.U32, int(buffer))
