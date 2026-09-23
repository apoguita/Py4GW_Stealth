from ..target_struct import TargetStruct
from ctypes import Structure
from typing import Optional

from ..scanner import PatternCatalog, RemoteScanner
from .gw_array import RemoteMemoryReader


class MapDimensionsStruct(TargetStruct):
    unk: int
    start_x: int
    start_y: int
    end_x: int
    end_y: int
    unk1: int


class AreaInfoStruct(TargetStruct):
    campaign: int
    continent: int
    region: int
    type: int
    flags: int
    thumbnail_id: int
    min_party_size: int
    max_party_size: int
    min_player_size: int
    max_player_size: int
    controlled_outpost_id: int
    fraction_mission: int
    min_level: int
    max_level: int
    needed_pq: int
    mission_maps_to: int
    x: int
    y: int
    icon_start_x: int
    icon_start_y: int
    icon_end_x: int
    icon_end_y: int
    icon_start_x_dupe: int
    icon_start_y_dupe: int
    icon_end_x_dupe: int
    icon_end_y_dupe: int
    file_id: int
    mission_chronology: int
    ha_map_chronology: int
    name_id: int
    description_id: int

    @property
    def file_id_1(self) -> int: ...

    @property
    def file_id1(self) -> int: ...

    @property
    def file_id_2(self) -> int: ...

    @property
    def file_id2(self) -> int: ...

    @property
    def has_enter_button(self) -> bool: ...

    @property
    def is_on_world_map(self) -> bool: ...

    @property
    def is_pvp(self) -> bool: ...

    @property
    def is_guild_hall(self) -> bool: ...

    @property
    def is_vanquishable_area(self) -> bool: ...

    @property
    def is_unlockable(self) -> bool: ...

    @property
    def has_mission_maps_to(self) -> bool: ...


class InstanceInfoStruct(TargetStruct):
    terrain_info1_ptr: int
    instance_type: int
    current_map_info_ptr: int
    terrain_count: int
    terrain_info2_ptr: int

    def bind_reader(
        self, reader: RemoteMemoryReader, address: int | None = None
    ) -> InstanceInfoStruct: ...

    @property
    def terrain_info1(self) -> Optional[MapDimensionsStruct]: ...

    @property
    def current_map_info(self) -> Optional[AreaInfoStruct]: ...

    @property
    def terrain_info2(self) -> Optional[MapDimensionsStruct]: ...


class InstanceInfo:
    _ptr: int
    _cached_ctx: InstanceInfoStruct | None
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
    def get_context() -> Optional[InstanceInfoStruct]: ...

    def resolve_address(self) -> int | None: ...

    def initialize(self) -> int | None: ...

    @property
    def cached_context_address(self) -> int | None: ...

    def read(self) -> InstanceInfoStruct | None: ...


def get() -> InstanceInfoStruct | None: ...
