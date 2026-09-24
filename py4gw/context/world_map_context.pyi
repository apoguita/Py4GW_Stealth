from ..helpers.target_struct import TargetStruct
from ctypes import Structure
from typing import Protocol

from ..scanner import PatternCatalog, RemoteScanner
from ..ui.frame_context import FrameContextCandidate
from ..ui.frame_tree import FrameTree
from .map_context import MapVec2fStruct


class _memory_reader(Protocol):
    def read(self, address: int, size: int) -> bytes: ...


class WorldMapContextStruct(TargetStruct):
    frame_id: int
    h0004: int
    h0008: int
    h000c: float
    h0010: float
    h0014: int
    h0018: float
    h001c: float
    h0020: float
    h0024: float
    h0028: float
    h002c: float
    h0030: float
    h0034: float
    zoom: float
    top_left: MapVec2fStruct
    bottom_right: MapVec2fStruct
    h004c: list[int]
    h0068: float
    h006c: float
    params: list[int]

    @classmethod
    def read_at(
        cls,
        reader: _memory_reader,
        address: int,
    ) -> WorldMapContextStruct: ...


class WorldMapContext:
    def __init__(
        self,
        reader: _memory_reader,
        scanner: RemoteScanner,
        patterns: PatternCatalog,
        frame_tree: FrameTree,
    ) -> None: ...

    @property
    def callback_resolver(self) -> str: ...

    @property
    def callback_address(self) -> int | None: ...

    def initialize(self) -> int | None: ...

    def resolve_address(self) -> int | None: ...

    def candidates(self) -> tuple[FrameContextCandidate, ...]: ...

    def read(self) -> WorldMapContextStruct | None: ...

    @staticmethod
    def get_ptr() -> int: ...

    @staticmethod
    def _update_ptr() -> None: ...

    @staticmethod
    def enable() -> None: ...

    @staticmethod
    def disable() -> None: ...

    @staticmethod
    def get_context() -> WorldMapContextStruct | None: ...


def get() -> WorldMapContextStruct | None: ...
