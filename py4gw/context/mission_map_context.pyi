from ..helpers.target_struct import TargetStruct
from ctypes import Structure
from typing import Protocol

from ..scanner import PatternCatalog, RemoteScanner
from ..ui.frame_context import FrameContextCandidate
from ..ui.frame_tree import FrameTree
from .gw_array import GWArray
from .map_context import MapVec2fStruct


class _memory_reader(Protocol):
    def read(self, address: int, size: int) -> bytes: ...


class MissionMapSubContext(TargetStruct):
    h0000: list[int]


class MissionMapSubContext2(TargetStruct):
    h0000: int
    player_mission_map_pos: MapVec2fStruct
    h000c: int
    mission_map_size: MapVec2fStruct
    unk: float
    mission_map_pan_offset: MapVec2fStruct
    mission_map_pan_offset2: MapVec2fStruct
    unk2: list[float]
    unk3: list[int]


class MissionMapContextStruct(TargetStruct):
    size: MapVec2fStruct
    h0008: int
    last_mouse_location: MapVec2fStruct
    frame_id: int
    player_mission_map_pos: MapVec2fStruct
    h0020: GWArray
    h0030: int
    h0034: int
    h0038: int
    h003c: int
    h0040: int
    h0044: int

    @classmethod
    def read_at(
        cls,
        reader: _memory_reader,
        address: int,
        max_subcontexts: int = ...,
    ) -> MissionMapContextStruct: ...

    def bind_reader(
        self,
        reader: _memory_reader,
        address: int | None = ...,
        max_subcontexts: int = ...,
    ) -> MissionMapContextStruct: ...

    @property
    def address(self) -> int | None: ...

    @property
    def subcontexts(self) -> list[MissionMapSubContext]: ...

    @property
    def subcontext2(self) -> MissionMapSubContext2 | None: ...


class MissionMapContext:
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

    def read(
        self, max_subcontexts: int = ...
    ) -> MissionMapContextStruct | None: ...

    @staticmethod
    def get_ptr() -> int: ...

    @staticmethod
    def _update_ptr() -> None: ...

    @staticmethod
    def enable() -> None: ...

    @staticmethod
    def disable() -> None: ...

    @staticmethod
    def get_context() -> MissionMapContextStruct | None: ...


def get() -> MissionMapContextStruct | None: ...
