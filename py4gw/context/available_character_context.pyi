from ..target_struct import TargetStruct
from ctypes import Structure
from typing import Any, Optional

from ..scanner import PatternCatalog, RemoteScanner
from .gw_array import GWArray, RemoteMemoryReader


class AvailableCharacterInfoStruct(TargetStruct):
    h0000: Any
    uuid_ptr: Any
    player_name_enc: Any
    props: Any

    @property
    def uuid(self) -> tuple[int, int, int, int]: ...

    @property
    def player_name_encoded_str(self) -> str: ...

    @property
    def player_name_encoded_string(self) -> str | None: ...

    @property
    def player_name_str(self) -> str: ...

    @property
    def player_name(self) -> str: ...

    @property
    def map_id(self) -> int: ...

    @property
    def primary(self) -> int: ...

    @property
    def secondary(self) -> int: ...

    @property
    def campaign(self) -> int: ...

    @property
    def level(self) -> int: ...

    @property
    def is_pvp(self) -> bool: ...


AvailableCharacterStruct = AvailableCharacterInfoStruct


class AvailableCharacterArrayStruct(TargetStruct):
    available_characters_array: GWArray

    def bind_reader(self, reader: RemoteMemoryReader) -> AvailableCharacterArrayStruct: ...

    @property
    def available_characters_list(self) -> list[AvailableCharacterInfoStruct]: ...

    @property
    def characters(self) -> list[AvailableCharacterInfoStruct]: ...


class AvailableCharacterArray:
    _ptr: int
    _cached_ctx: AvailableCharacterArrayStruct | None
    _callback_name: str

    def __init__(
        self,
        reader: RemoteMemoryReader,
        scanner: RemoteScanner,
        patterns: PatternCatalog,
    ) -> None: ...

    @staticmethod
    def get_ptr() -> int: ...

    @staticmethod
    def _update_ptr() -> None: ...

    @staticmethod
    def enable() -> None: ...

    @staticmethod
    def disable() -> None: ...

    @staticmethod
    def get_context() -> Optional[AvailableCharacterArrayStruct]: ...

    def resolve_address(self) -> int | None: ...

    def initialize(self) -> int | None: ...

    @property
    def cached_context_address(self) -> int | None: ...

    def read(self) -> AvailableCharacterArrayStruct | None: ...


def get() -> AvailableCharacterArrayStruct | None: ...
