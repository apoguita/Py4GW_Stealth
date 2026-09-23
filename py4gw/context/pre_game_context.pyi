from ..target_struct import TargetStruct
from ctypes import Structure
from typing import Any, Optional, Protocol

from ..scanner import PatternCatalog, RemoteScanner
from .gw_array import GWBaseArray, RemoteMemoryReader


class LoginCharacter(TargetStruct):
    appearance_packed: int
    pvp_flag: int
    guild_guid_0: int
    guild_guid_1: int
    guild_guid_2: int
    guild_guid_3: int
    items_data: int
    items_capacity: int
    items_count: int
    items_param: int
    level: int
    current_map_id: int
    field_0x30: int
    primary_profession: int
    profession_enum: int
    field_0x3C: int
    field_0x40: int
    field_0x44: int
    field_0x48: int
    char_model_ptr: int
    character_name_enc: Any

    @property
    def guild_guid(self) -> bytes: ...

    @property
    def character_name_encoded_str(self) -> str: ...

    @property
    def character_name_str(self) -> str: ...

    @property
    def character_name(self) -> str | None: ...


class PreGameContextStruct(TargetStruct):
    frame_id: int
    scene_type: int
    scene_controller_iface: int
    camera_pitch_frequency: float
    camera_pitch_current: float
    camera_pitch_target: float
    camera_pitch_velocity: float
    RESERVED_0x1C: Any
    camera_mode: int
    RESERVED_0x50: Any
    RESERVED_0x64: int
    camera_limits_frequency: float
    camera_limits_min_current: float
    camera_limits_max_current: float
    camera_limits_min_target: float
    camera_limits_max_target: float
    camera_limits_min_velocity: float
    camera_limits_max_velocity: float
    scroll_offset_frequency: float
    scroll_offset_current: float
    scroll_offset_target: float
    scroll_offset_velocity: float
    scroll_speed_frequency: float
    scroll_speed_current: float
    scroll_speed_target: float
    scroll_speed_velocity: float
    camera_height: float
    camera_height_min: float
    camera_height_max: float
    camera_rotation_frequency: float
    camera_rotation_current: float
    camera_rotation_target: float
    camera_rotation_velocity: float
    RESERVED_0xC0: Any
    max_characters: int
    chosen_character_index: int
    preview_character_index: int
    pending_character_index: int
    chars_array: GWBaseArray
    char_creation_flag: int
    create_slot_index: int
    sentinel_guard: int
    self_link: int
    list_head: int

    def bind_reader(
        self, reader: RemoteMemoryReader, address: int | None = None
    ) -> PreGameContextStruct: ...

    @property
    def chars_list(self) -> list[LoginCharacter]: ...


class PreGameContext:
    _ptr: int
    _cached_ctx: PreGameContextStruct | None
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
    def get_context() -> Optional[PreGameContextStruct]: ...

    def resolve_address(self) -> int | None: ...

    def initialize(self) -> int | None: ...

    @property
    def cached_pointer_address(self) -> int | None: ...

    def read(self) -> PreGameContextStruct | None: ...


def get() -> PreGameContextStruct | None: ...
