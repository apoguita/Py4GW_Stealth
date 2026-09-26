"""External readers for the Guild Wars UI frame primitives.

``Gw.exe`` keeps every UI frame in one global array and routes interaction
callbacks through a per-frame callback list.  The declarations in this module
mirror ``include/GW/ui/ui.h`` in the Reforged Native source and read those
records through the external memory reader.

Nothing in this module creates, destroys, dispatches, or modifies a frame.
The frame-array head, each frame record, and its callback entries are read as
target data only.  Every pointer is a fixed-width x86 ``uint32`` target
address; none is a host pointer.

The ``GWArray`` and ``GwList`` readers used here are shared target-memory
primitives that currently live under ``py4gw.context`` because the context
readers were the first consumers.  They are not context-specific.
"""

from __future__ import annotations

from ..helpers.target_struct import TargetStruct

import ctypes
from ctypes import Structure, c_float, c_uint32
from enum import IntEnum
from typing import Any, Iterator, Protocol, cast

from ..context.gw_array import GWArray, GWArrayValueView, RemoteMemoryReader
from ..context.gw_list import GWListStruct
from ..scanner import PatternCatalog, RemoteScanner


class _memory_reader(RemoteMemoryReader, Protocol):
    """The byte-reading operation needed by frame records."""


class UIMessage(IntEnum):
    """The frame-level values of the native ``GW::Constants::UIMessage``.

    The native enum also carries agent messages at and above ``0x10000000``.
    Those are not frame messages and are not ported here yet; a frame callback
    receives the range declared below.  Only the values needed to interpret a
    frame callback are present, so this is a partial port of the native enum
    and must not be treated as complete.
    """

    kNone = 0x0
    kResize = 0x8
    kInitFrame = 0x9
    kDestroyFrame = 0xB
    kKeyDown = 0x20
    kSetFocus = 0x21
    kKeyUp = 0x22
    kMouseClick = 0x24
    kMouseCoordsClick = 0x26
    kMouseUp = 0x28
    kToggleButtonDown = 0x2E
    kMouseClick2 = 0x31
    kMouseAction = 0x32
    kSetLayout = 0x37
    kMeasureContent = 0x38
    kRefreshContent = 0x3B
    kSkillListAddSkill = 0x57


class FramePositionStruct(TargetStruct):
    """The native ``GW::ui::FramePosition`` record."""

    _pack_ = 1
    _fields_ = [
        ("flags", c_uint32),
        ("left", c_float),
        ("bottom", c_float),
        ("right", c_float),
        ("top", c_float),
        ("content_left", c_float),
        ("content_bottom", c_float),
        ("content_right", c_float),
        ("content_top", c_float),
        ("unk", c_float),
        ("scale_factor", c_float),
        ("viewport_width", c_float),
        ("viewport_height", c_float),
        ("screen_left", c_float),
        ("screen_bottom", c_float),
        ("screen_right", c_float),
        ("screen_top", c_float),
    ]


class FrameRelationStruct(TargetStruct):
    """The native ``GW::ui::FrameRelation`` record."""

    _pack_ = 1
    _fields_ = [
        ("parent", c_uint32),
        ("field67_0x124", c_uint32),
        ("field68_0x128", c_uint32),
        ("frame_hash_id", c_uint32),
        ("siblings", GWListStruct),
    ]


class FrameInteractionCallbackStruct(TargetStruct):
    """One entry of the native ``GW::ui::FrameInteractionCallback`` array.

    ``GetFrameContext`` reinterprets the frame's callback array as this record
    type.  ``uictl_context`` is the per-frame game context pointer the client
    registers with the callback; this is the slot a map UI callback dereferences
    to obtain its context.
    """

    _pack_ = 1
    _fields_ = [
        ("callback", c_uint32),
        ("uictl_context", c_uint32),
        ("h0008", c_uint32),
    ]


class TooltipInfoStruct(TargetStruct):
    """The native ``GW::ui::TooltipInfo`` record."""

    _pack_ = 1
    _fields_ = [
        ("bit_field", c_uint32),
        ("render", c_uint32),
        ("payload", c_uint32),
        ("payload_len", c_uint32),
        ("unk1", c_uint32),
        ("unk2", c_uint32),
        ("unk3", c_uint32),
        ("unk4", c_uint32),
    ]


class InteractionMessageStruct(TargetStruct):
    """The native ``GW::ui::InteractionMessage`` passed to a UI callback.

    ``wParam`` is a ``void**`` in the native declaration.  For the map frames
    it holds the address of the frame's registered context slot, which is why
    a callback dereferences it once to obtain the context.
    """

    _pack_ = 1
    _fields_ = [
        ("frame_id", c_uint32),
        ("message_id", c_uint32),
        ("wParam", c_uint32),
    ]


class FrameStruct(TargetStruct):
    """The native ``GW::ui::Frame`` record.

    Field names follow ``include/GW/ui/ui.h`` exactly, including the native
    ``fieldNN_0xNN`` placeholder names whose suffixes record the source's own
    offsets.  ``frame_callbacks`` and ``frame_id`` are the two fields the frame
    tree depends on; the rest are preserved so the layout is a faithful port.
    """

    _pack_ = 1
    _fields_ = [
        ("field1_0x0", c_uint32),
        ("field2_0x4", c_uint32),
        ("frame_layout", c_uint32),
        ("field3_0xc", c_uint32),
        ("field4_0x10", c_uint32),
        ("field5_0x14", c_uint32),
        ("visibility_flags", c_uint32),
        ("field7_0x1c", c_uint32),
        ("type", c_uint32),
        ("template_type", c_uint32),
        ("field10_0x28", c_uint32),
        ("field11_0x2c", c_uint32),
        ("field12_0x30", c_uint32),
        ("field13_0x34", c_uint32),
        ("field14_0x38", c_uint32),
        ("field15_0x3c", c_uint32),
        ("field16_0x40", c_uint32),
        ("field17_0x44", c_uint32),
        ("field18_0x48", c_uint32),
        ("field19_0x4c", c_uint32),
        ("field20_0x50", c_uint32),
        ("field21_0x54", c_uint32),
        ("field22_0x58", c_uint32),
        ("field23_0x5c", c_uint32),
        ("field24_0x60", c_uint32),
        ("field24a_0x64", c_uint32),
        ("field24b_0x68", c_uint32),
        ("field25_0x6c", c_uint32),
        ("field26_0x70", c_uint32),
        ("field27_0x74", c_uint32),
        ("field28_0x78", c_uint32),
        ("field29_0x7c", c_uint32),
        ("field30_0x80", c_uint32),
        ("field31_0x84", GWArray),
        ("field32_0x94", c_uint32),
        ("field33_0x98", c_uint32),
        ("field34_0x9c", c_uint32),
        ("field35_0xa0", c_uint32),
        ("field36_0xa4", c_uint32),
        ("frame_callbacks", GWArray),
        ("child_offset_id", c_uint32),
        ("frame_id", c_uint32),
        ("field40_0xc0", c_uint32),
        ("field41_0xc4", c_uint32),
        ("field42_0xc8", c_uint32),
        ("field43_0xcc", c_uint32),
        ("field44_0xd0", c_uint32),
        ("field45_0xd4", c_uint32),
        ("position", FramePositionStruct),
        ("field63_0x11c", c_uint32),
        ("field64_0x120", c_uint32),
        ("field65_0x124", c_uint32),
        ("relation", FrameRelationStruct),
        ("field73_0x144", c_uint32),
        ("field74_0x148", c_uint32),
        ("field75_0x14c", c_uint32),
        ("field76_0x150", c_uint32),
        ("field77_0x154", c_uint32),
        ("field78_0x158", c_uint32),
        ("field79_0x15c", c_uint32),
        ("field80_0x160", c_uint32),
        ("field81_0x164", c_uint32),
        ("field82_0x168", c_uint32),
        ("field83_0x16c", c_uint32),
        ("field84_0x170", c_uint32),
        ("field85_0x174", c_uint32),
        ("field86_0x178", c_uint32),
        ("field87_0x17c", c_uint32),
        ("field88_0x180", c_uint32),
        ("field89_0x184", c_uint32),
        ("field90_0x188", c_uint32),
        ("frame_state", c_uint32),
        ("field92_0x190", c_uint32),
        ("field93_0x194", c_uint32),
        ("field94_0x198", c_uint32),
        ("field95_0x19c", c_uint32),
        ("field96_0x1a0", c_uint32),
        ("field97_0x1a4", c_uint32),
        ("field98_0x1a8", c_uint32),
        ("tooltip_info", c_uint32),
        ("field100_0x1b0", c_uint32),
        ("field101_0x1b4", c_uint32),
        ("field102_0x1b8", c_uint32),
        ("field103_0x1bc", c_uint32),
        ("field104_0x1c0", c_uint32),
        ("field105_0x1c4", c_uint32),
    ]

    # Target address this copy was read from.  It is not a native field; the
    # external reader records it so relations can be compared by address.
    _remote_address: int | None = None

    def bind_address(self, address: int) -> FrameStruct:
        """Record the target address this frame copy was read from."""

        self._remote_address = address
        return self

    @property
    def address(self) -> int | None:
        """Return the target address this frame copy was read from."""

        return self._remote_address

    @property
    def is_created(self) -> bool:
        """Return the native ``IsCreated`` frame-state bit."""

        return (int(self.frame_state) & 0x4) != 0

    @property
    def is_hidden(self) -> bool:
        """Return the native ``IsHidden`` frame-state bit."""

        return (int(self.frame_state) & 0x200) != 0

    @property
    def is_visible(self) -> bool:
        """Return the native ``IsVisible`` frame-state bit."""

        return not self.is_hidden

    @property
    def is_disabled(self) -> bool:
        """Return the native ``IsDisabled`` frame-state bit."""

        return (int(self.frame_state) & 0x10) != 0


assert ctypes.sizeof(FramePositionStruct) == 0x44
assert ctypes.sizeof(FrameRelationStruct) == 0x1C
assert ctypes.sizeof(FrameInteractionCallbackStruct) == 0x0C
assert ctypes.sizeof(TooltipInfoStruct) == 0x20
assert ctypes.sizeof(InteractionMessageStruct) == 0x0C
assert ctypes.sizeof(FrameStruct) == 0x1C8
assert FrameStruct.frame_callbacks.offset == 0xA8
assert FrameStruct.child_offset_id.offset == 0xB8
assert FrameStruct.frame_id.offset == 0xBC
assert FrameStruct.position.offset == 0xD8
assert FrameStruct.frame_state.offset == 0x18C
assert FrameStruct.relation.offset == 0x128
assert FrameStruct.tooltip_info.offset == 0x1AC


_FRAME_SENTINEL = 0xFFFFFFFF
_MIN_POINTER = 0x10000

#: The project's documented string ceiling, used as the bound for one wide-string read.
#: A label is a line of UI text; the ceiling exists so a pointer that is not a string costs
#: a bounded number of reads instead of an unbounded one.
_LABEL_CODE_UNIT_LIMIT = 32768


def is_valid_frame_pointer(pointer: int) -> bool:
    """Return whether a frame-array slot holds a usable frame pointer.

    Frame-array slots may be null or the ``0xFFFFFFFF`` sentinel left behind by
    a deleted entry.  Reforged Native's ``IsFrameValid`` rejects both; treating
    the sentinel as a pointer faults in the client near address ``0x134``.
    """

    return pointer not in (0, _FRAME_SENTINEL) and pointer >= _MIN_POINTER


class FrameArray:
    """Resolve and read the client's global UI frame array.

    The native global is an inline ``GWArray<Frame*>`` header stored in the
    module's ``.data`` section, reached through the ``ui.frame_array_addr``
    resolver.  The array is indexed by frame id, exactly as the native
    ``GetFrameById`` does.
    """

    _RESOLVER = "ui.frame_array_addr"
    _MAX_FRAMES = 65536

    def __init__(
        self,
        reader: _memory_reader,
        scanner: RemoteScanner,
        patterns: PatternCatalog,
    ) -> None:
        """Create a reader over one connected client's frame array."""

        self._reader = reader
        self._scanner = scanner
        self._patterns = patterns
        self._array_address: int | None = None

    @property
    def cached_address(self) -> int | None:
        """Return the cached frame-array header address, if resolved."""

        return self._array_address

    def initialize(self) -> GWArray | None:
        """Resolve the frame-array global once and return its current header.

        Resolving caches the target address; later reads re-read only the
        header and the array entries.  A failed resolution raises so the caller
        can report the resolver's own failure detail.
        """

        if self._array_address is None:
            result = self._patterns.resolve(self._RESOLVER, self._scanner)
            if not result.ok:
                detail = result.message or "the resolver returned no address"
                raise RuntimeError(f"{self._RESOLVER} failed: {detail}")
            address = result.value
            if address < _MIN_POINTER:
                raise ValueError(
                    f"{self._RESOLVER} returned an unusable address: 0x{address:08X}"
                )
            self._array_address = address
        return self.read_header()

    def read_header(self) -> GWArray | None:
        """Read and validate the frame-array header.

        Returns ``None`` when the array is empty.  Raises ``ValueError`` when
        the header cannot describe a bounded array, because that means the
        resolved address is not the structure this reader expects.
        """

        if self._array_address is None:
            return self.initialize()

        raw = self._reader.read(self._array_address, ctypes.sizeof(GWArray))
        if len(raw) != ctypes.sizeof(GWArray):
            raise ValueError(
                f"Frame array header read returned {len(raw)} bytes; "
                f"expected {ctypes.sizeof(GWArray)}."
            )
        header = GWArray.from_buffer_copy(raw)
        count = int(header.m_size)
        capacity = int(header.m_capacity)
        if count > capacity:
            raise ValueError(
                f"Frame array header is inconsistent: size {count} exceeds "
                f"capacity {capacity}."
            )
        if count > self._MAX_FRAMES:
            raise ValueError(
                f"Frame array size {count} exceeds the {self._MAX_FRAMES} cap."
            )
        if count and not is_valid_frame_pointer(int(header.m_buffer)):
            raise ValueError(
                "Frame array header has a non-empty size but no usable buffer "
                f"pointer: 0x{int(header.m_buffer):08X}."
            )
        return header

    def size(self) -> int:
        """Return the number of frame slots the client currently advertises."""

        header = self.read_header()
        return int(header.m_size) if header is not None else 0

    def read_slot_pointers(self) -> list[int]:
        """Read every frame-array slot in one bounded read.

        The array holds thousands of slots and most are null or the deleted
        sentinel, so one bulk read is much cheaper than one read per slot.
        """

        header = self.read_header()
        if header is None:
            return []
        count = int(header.m_size)
        if count > self._MAX_FRAMES:
            raise ValueError(
                f"Frame array size {count} exceeds the {self._MAX_FRAMES} cap."
            )
        if count == 0:
            return []
        raw = self._reader.read(int(header.m_buffer), count * 4)
        if len(raw) != count * 4:
            raise ValueError(
                f"Frame pointer table read returned {len(raw)} bytes; "
                f"expected {count * 4}."
            )
        return [
            int.from_bytes(raw[index * 4 : index * 4 + 4], "little")
            for index in range(count)
        ]

    def read_frame_pointer(self, frame_id: int) -> int:
        """Read one raw frame-array slot, including invalid sentinel values."""

        header = self.read_header()
        if header is None or frame_id < 0 or frame_id >= int(header.m_size):
            return 0
        address = int(header.m_buffer) + frame_id * 4
        return int.from_bytes(self._reader.read(address, 4), "little")

    def iter_slots(self) -> Iterator[tuple[int, int]]:
        """Yield ``(frame_id, frame_pointer)`` for every valid slot."""

        for frame_id, pointer in enumerate(self.read_slot_pointers()):
            if is_valid_frame_pointer(pointer):
                yield frame_id, pointer

    def frame_id_for_address(self, address: int) -> int | None:
        """Return the frame-array index holding one frame address."""

        if not is_valid_frame_pointer(address):
            return None
        for frame_id, pointer in self.iter_slots():
            if pointer == address:
                return frame_id
        return None

    def frame_id_by_hash(self, frame_hash: int) -> int:
        """``GetFrameIDByHash`` (``ui_methods.cpp:575-587``): first frame with this hash.

        The source walks the array comparing ``frame->relation.frame_hash_id`` and
        returns the index, with **``0`` meaning "not found"** — its callers refuse a
        zero id before using it. Only valid slots are considered, which is the source's
        ``IsFrameValid`` filter.

        Two notes on the shape. The source reads each frame whole in-process; this port
        reads the single hash field per slot, because every slot is a separate
        ``ReadProcessMemory`` here. And the source's ``__try``-guarded callers treat an
        unreadable frame as invalid rather than as an error, so a slot whose hash cannot
        be read is skipped rather than raised — the same outcome the source's fault
        handling produces.
        """

        if not frame_hash:
            return 0
        hash_offset = FrameStruct.relation.offset + FrameRelationStruct.frame_hash_id.offset
        for frame_id, pointer in self.iter_slots():
            try:
                value = self.read_u32(pointer + hash_offset)
            except OSError:
                continue
            if value == frame_hash:
                return frame_id
        return 0

    def read_u32(self, address: int) -> int:
        """Read one 32-bit little-endian target value."""

        return int.from_bytes(self._reader.read(address, 4), "little")

    def get(self, frame_id: int) -> FrameStruct | None:
        """Read one frame by id, matching the native ``GetFrameById``.

        Returns ``None`` for an out-of-range, null, or sentinel slot.
        """

        pointer = self.read_frame_pointer(frame_id)
        if not is_valid_frame_pointer(pointer):
            return None
        raw = self._reader.read(pointer, ctypes.sizeof(FrameStruct))
        return FrameStruct.from_buffer_copy(raw).bind_address(pointer)

    def iter_frames(self) -> Iterator[tuple[int, FrameStruct]]:
        """Yield ``(frame_id, frame)`` for every valid slot in the array."""

        for frame_id, pointer in self.iter_slots():
            raw = self._reader.read(pointer, ctypes.sizeof(FrameStruct))
            yield frame_id, FrameStruct.from_buffer_copy(raw).bind_address(pointer)

    def read_callbacks_at(
        self, frame_pointer: int
    ) -> list[FrameInteractionCallbackStruct]:
        """Read a frame's callback entries using only its array address.

        This reads the callback header and entries directly instead of the
        whole 0x1C8 frame record, so a callback search can skip frames that
        register nothing without transferring their full layout.
        """

        if not is_valid_frame_pointer(frame_pointer):
            return []
        header_address = frame_pointer + FrameStruct.frame_callbacks.offset
        raw = self._reader.read(header_address, ctypes.sizeof(GWArray))
        if len(raw) != ctypes.sizeof(GWArray):
            return []
        array = GWArray.from_buffer_copy(raw)
        return self._decode_callbacks(array)

    def read_callbacks(
        self, frame: FrameStruct
    ) -> list[FrameInteractionCallbackStruct]:
        """Read every registered interaction callback of one frame."""

        return self._decode_callbacks(cast(GWArray, frame.frame_callbacks))

    def _decode_callbacks(
        self, array: GWArray
    ) -> list[FrameInteractionCallbackStruct]:
        """Decode a callback array header that was already read."""

        if not array.m_buffer or not array.m_size:
            return []
        if int(array.m_size) > int(array.m_capacity):
            return []
        view = GWArrayValueView(
            self._reader, array, FrameInteractionCallbackStruct
        )
        return [
            cast(FrameInteractionCallbackStruct, value) for value in view.to_list()
        ]

    def frame_context_address(self, frame: FrameStruct) -> int:
        """Return the frame's registered context pointer, or zero.

        This mirrors the native ``GetFrameContext``: the callback entries are
        walked from the end and the last non-null ``uictl_context`` wins.
        """

        for callback in reversed(self.read_callbacks(frame)):
            context = int(callback.uictl_context)
            if context >= _MIN_POINTER:
                return context
        return 0

    # -- text labels (``TextLabelFrame::GetEncodedLabel`` / ``GetDecodedLabel``) ----

    #: ``WIDE_CHAR_SIZE``: the client's labels are UTF-16 code units on disk and in memory.
    _WIDE_CHAR_SIZE = 2

    def read_wide_string(self, address: int, limit: int) -> str:
        """Read a NUL-terminated UTF-16 string, at most ``limit`` code units.

        The read stops at the terminator or the limit, whichever comes first, so a pointer
        that is not a string costs a bounded number of reads rather than an unbounded one.
        An unreadable address raises, which is the reader's own behaviour.
        """

        if address < _MIN_POINTER or limit <= 0:
            return ""
        units: list[int] = []
        for index in range(limit):
            unit = self.read_u32(address + index * self._WIDE_CHAR_SIZE) & 0xFFFF
            if unit == 0:
                break
            units.append(unit)
        return "".join(chr(unit) for unit in units)

    def encoded_label(self, frame: FrameStruct) -> str:
        """``TextLabelFrame::GetEncodedLabel`` (``ui_methods.cpp:2216-2222``).

        The frame's context holds ``[+4] a pointer to the encoded label`` and ``[+0xC]`` a
        size word that is zero when there is no label. The encoded string is what the
        client stores; :meth:`decoded_label` is the rendered one.
        """

        context = self.frame_context_address(frame)
        if not context:
            return ""
        if self.read_u32(context + 0xC) == 0:
            return ""
        encoded_pointer = self.read_u32(context + 0x4)
        return self.read_wide_string(encoded_pointer, _LABEL_CODE_UNIT_LIMIT)

    def decoded_label(self, frame: FrameStruct) -> str:
        """``TextLabelFrame::GetDecodedLabel`` (``ui_methods.cpp:2224-2234``).

        The client keeps the **decoded** label in the same allocation, immediately after
        the encoded one: the source computes ``len = wcslen(enc) + 1`` and returns
        ``enc + len``, guarded by the size word at ``[+0xC]``. This is a read of what the
        client has already rendered, which is why it needs no decoder here.

        Returns ``""`` where the source returns ``nullptr``: no context, a zero size word,
        or a decoded copy that does not fit inside the size word.
        """

        context = self.frame_context_address(frame)
        if not context:
            return ""
        size = self.read_u32(context + 0xC)
        if size == 0:
            return ""
        encoded_pointer = self.read_u32(context + 0x4)
        encoded = self.read_wide_string(encoded_pointer, _LABEL_CODE_UNIT_LIMIT)
        # ``wcslen`` counts UTF-16 code units, and ``Python`` strings count code points,
        # so the length is taken from the encoded form rather than from ``len(str)``.
        length = len(encoded.encode("utf-16-le")) // self._WIDE_CHAR_SIZE + 1
        if length >= size:
            return ""
        return self.read_wide_string(
            encoded_pointer + length * self._WIDE_CHAR_SIZE, _LABEL_CODE_UNIT_LIMIT
        )


FramePosition = FramePositionStruct
FrameRelation = FrameRelationStruct
FrameInteractionCallback = FrameInteractionCallbackStruct
TooltipInfo = TooltipInfoStruct
InteractionMessage = InteractionMessageStruct
Frame = FrameStruct
UIInteractionCallbackStruct = FrameInteractionCallbackStruct


__all__ = [
    "Frame",
    "FrameArray",
    "FrameInteractionCallback",
    "FrameInteractionCallbackStruct",
    "FramePosition",
    "FramePositionStruct",
    "FrameRelation",
    "FrameRelationStruct",
    "FrameStruct",
    "InteractionMessage",
    "InteractionMessageStruct",
    "TooltipInfo",
    "TooltipInfoStruct",
    "UIInteractionCallbackStruct",
    "UIMessage",
    "is_valid_frame_pointer",
]
