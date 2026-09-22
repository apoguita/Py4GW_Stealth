from ctypes import Structure
from typing import Any, Optional

from .game_context import GameContext
from .gw_array import RemoteMemoryReader


class TextCacheStruct(Structure):
    h0000: int


class TextParserSubStructStruct(Structure):
    h0000: int


class TextFileSlotStruct(Structure):
    _pad0: Any
    file_hash_ptr: int
    _pad1: int
    lang_id: int
    start_index: int
    end_index: int
    _pad2: Any

    def bind_reader(self, reader: RemoteMemoryReader) -> TextFileSlotStruct: ...

    @property
    def file_hash(self) -> str: ...


class LanguageSlotStruct(Structure):
    slot_array_ptr: int
    _h0004: int
    slot_count: int


class TextParserStruct(Structure):
    _h0000: Any
    dec_start_ptr: int
    dec_end_ptr: int
    substitute_1: int
    substitute_2: int
    _cache_header: Any
    language_slots: Any
    _cache_pad: Any
    entries_per_file: int
    _pad_post_cache: Any
    h0160: int
    h0164: int
    h0168: int
    _h016C: Any
    sub_struct_ptr: int
    _h0184: Any
    language_id: int

    def bind_reader(
        self, reader: RemoteMemoryReader, address: int | None = None
    ) -> TextParserStruct: ...

    @property
    def cache_ptr(self) -> int: ...

    @property
    def dec_start(self) -> int: ...

    @property
    def dec_end(self) -> int: ...

    @property
    def h0000(self) -> tuple[int, ...]: ...

    @property
    def h016c(self) -> tuple[int, ...]: ...

    @property
    def h0184(self) -> tuple[int, ...]: ...

    @property
    def cache(self) -> TextCacheStruct | None: ...

    @property
    def sub_struct(self) -> TextParserSubStructStruct | None: ...

    def get_file_slot(
        self, slot_idx: int, language: int = 0
    ) -> TextFileSlotStruct | None: ...


class TextParser:
    _ptr: int
    _cached_ctx: TextParserStruct | None
    _callback_name: str
    _string_table_triggered: bool

    def __init__(self, reader: RemoteMemoryReader, game_context: GameContext) -> None: ...

    @staticmethod
    def get_ptr() -> int: ...

    @staticmethod
    def _update_ptr() -> None: ...

    @staticmethod
    def enable() -> None: ...

    @staticmethod
    def disable() -> None: ...

    @staticmethod
    def get_context() -> Optional[TextParserStruct]: ...

    def resolve_address(self) -> int | None: ...

    def read(self) -> TextParserStruct | None: ...


def get() -> TextParserStruct | None: ...
