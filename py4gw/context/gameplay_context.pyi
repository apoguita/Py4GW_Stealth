from ..helpers.target_struct import TargetStruct
from ctypes import Structure
from typing import Any, Optional

from ..scanner import PatternCatalog, RemoteScanner
from .gw_array import RemoteMemoryReader


class GameplayContextStruct(TargetStruct):
    h0000: Any
    mission_map_zoom: float
    unk: Any


class GameplayContext:
    _ptr: int
    _cached_ctx: GameplayContextStruct | None
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
    def get_context() -> Optional[GameplayContextStruct]: ...

    def resolve_address(self) -> int | None: ...

    def initialize(self) -> int | None: ...

    @property
    def cached_pointer_address(self) -> int | None: ...

    def read(self) -> GameplayContextStruct | None: ...


def get() -> GameplayContextStruct | None: ...
