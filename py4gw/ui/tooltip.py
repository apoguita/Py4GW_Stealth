"""The client's current tooltip, as native reads it.

**Source:** ``GW::ui::GetCurrentTooltip`` (``ui_methods.cpp:2658-2661``) over
``Context::GetCurrentTooltipPtr`` (``context_methods.cpp:192``):

```cpp
auto* CurrentTooltipPtr() { return Context::GetCurrentTooltipPtr(); }   // ui_methods.cpp:381-383
TooltipInfo* GetCurrentTooltip() {
    auto* current_tooltip_ptr = CurrentTooltipPtr();
    return current_tooltip_ptr && *current_tooltip_ptr ? **current_tooltip_ptr : nullptr;
}
```

with the global declared ``ui::TooltipInfo*** g_current_tooltip_ptr`` (``ui_patterns.cpp:17``).
**One divergence, measured on this build rather than inferred.** Native's expression dereferences
*twice* through that typing; on this client the global holds the tooltip pointer itself, so the port
reads it once. Three independent observations say so, and the third is a live read:

1. the client's own code compares the global's value against a tooltip record pointer
   (``cmp edi, [0x00C15050]`` at ``0x00653A23``, where ``edi`` is the record — the same function
   indexes it at ``+0x54``);
2. the client stores a record pointer into it and clears it the same way
   (``mov [0x00C15050], edi`` at ``0x00653A93``, ``mov dword ptr [0x00C15050], 0`` at
   ``0x006537D3`` — the clear ``ui.cpp:973`` performs);
3. read live through this project's own resolver on the running client, the global's value is a
   plausible heap pointer whose record carries ``payload_len`` (the struct's own word 3) at ``+0xC``
   — for the tooltip showing at the time, ``0xC``, which is not the ``0x14`` a skill tooltip
   carries, so the record and the offset both check out.

Under native's typing the extra dereference would read the record's first word (``bit_field``) as a
pointer, which is ``0`` on this client — the expression would answer "no tooltip" for a tooltip that
exists. So the port reproduces the *reading* the client performs and not the extra dereference, and
the difference is recorded here and in ``docs/SKILLBAR_PORT.md``.

The record itself is the one already declared beside the frames
(:class:`py4gw.ui.frame.TooltipInfoStruct`, ``GW::ui::TooltipInfo``). Reading it is read-only, and
nothing here sends, patches or calls anything.
"""

from __future__ import annotations

from ..helpers.target_struct import TargetStruct  # noqa: F401  (the port's target-record base)

import ctypes
from typing import Protocol

from ..scanner import PatternCatalog, RemoteScanner
from .frame import TooltipInfoStruct


class _memory_reader(Protocol):
    """The byte-reading operation needed by the tooltip reader."""

    def read(self, address: int, size: int) -> bytes: ...


#: The smallest address this project treats as a pointer inside the client.
_MIN_POINTER = 0x10000


class CurrentTooltip:
    """Resolve the tooltip global once and read the tooltip per call."""

    _RESOLVER = "ui.current_tooltip_ptr"

    def __init__(
        self,
        reader: _memory_reader,
        scanner: RemoteScanner,
        patterns: PatternCatalog,
    ) -> None:
        """Create a reader backed by one process and its offset catalog."""

        self._reader = reader
        self._scanner = scanner
        self._patterns = patterns
        self._pointer_address: int | None = None

    def initialize(self) -> int | None:
        """Scan once and cache the stable global address."""

        if self._pointer_address is None:
            result = self._patterns.resolve(self._RESOLVER, self._scanner)
            if not result.ok:
                detail = result.message or "the resolver returned no address"
                raise RuntimeError(f"{self._RESOLVER} failed: {detail}")
            self._pointer_address = result.value
        return self._pointer_address or None

    def resolve_address(self) -> int | None:
        """Return the cached global address, if it is available."""

        if self._pointer_address is None:
            return self.initialize()
        return self._pointer_address or None

    @property
    def cached_pointer_address(self) -> int | None:
        """Return the cached global address, if initialized."""

        return self._pointer_address

    def read(self) -> TooltipInfoStruct | None:
        """Read the tooltip the client is showing, or ``None`` when there is none.

        ``None`` is the source's own null: the global cleared, or a pointer that is not plausible
        inside the client. The global is read once — the divergence the module docstring records.
        """

        address = self.resolve_address()
        if address is None:
            return None

        tooltip = self._read_pointer(address)
        if tooltip is None:
            return None

        try:
            raw = self._reader.read(tooltip, ctypes.sizeof(TooltipInfoStruct))
        except OSError:
            return None
        return TooltipInfoStruct.from_buffer_copy(raw)

    def _read_pointer(self, address: int) -> int | None:
        """Read one target pointer, answering ``None`` for a null or implausible one."""

        try:
            raw = self._reader.read(address, 4)
        except OSError:
            return None
        value = int.from_bytes(raw, "little")
        return value if value >= _MIN_POINTER else None

    def read_payload_word(self, tooltip: TooltipInfoStruct) -> int | None:
        """Read the first word of the tooltip's payload (``GetHoveredSkill``'s read).

        ``GW::skillbar::GetHoveredSkill`` (``skillbar_methods.cpp:490-496``) requires
        ``payload_len == 0x14`` before it reads the payload as a skill id; the guard is the caller's,
        exactly as it is native's.
        """

        payload = int(tooltip.payload)
        if payload < _MIN_POINTER:
            return None
        try:
            raw = self._reader.read(payload, 4)
        except OSError:
            return None
        return int.from_bytes(raw, "little")
