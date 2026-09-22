from ctypes import Structure
from typing import Any, Optional

from ..scanner import PatternCatalog, RemoteScanner
from .gw_array import RemoteMemoryReader
from .game_context import GameContext


class CinematicStruct(Structure):
    h0000: int
    h0004: int


class Cinematic:
    _ptr: int
    _cached_ctx: CinematicStruct | None
    _callback_name: str

    def __init__(
        self, reader: RemoteMemoryReader, game_context: GameContext
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
    def get_context() -> Optional[CinematicStruct]: ...

    def resolve_address(self) -> int | None: ...

    def read(self) -> CinematicStruct | None: ...


def get() -> CinematicStruct | None: ...
