from ..helpers.target_struct import TargetStruct
from ctypes import Structure
from typing import Any, ClassVar

from .gw_array import GWArray


class ObserverMatchFlags(TargetStruct):
    type: int
    reserved: int
    version: int
    state: int
    level: int
    config1: int
    config2: int
    score1: int
    score2: int
    score3: int
    stat1: int
    stat2: int
    data1: int
    data2: int


class ObserverMatch(TargetStruct):
    match_id: int
    match_id_dup: int
    map_id: int
    age: int
    flags: ObserverMatchFlags
    team_name1_ptr: int
    unknown1: list[int]
    team_name2_ptr: int

    @property
    def team_name1_encoded_str(self) -> str | None: ...

    @property
    def team_name1_str(self) -> str | None: ...

    @property
    def team_name2_encoded_str(self) -> str | None: ...

    @property
    def team_name2_str(self) -> str | None: ...


class ProgressBar(TargetStruct):
    pips: int
    color: list[int]
    background: list[int]
    unk: list[int]
    progress: float


class CharContextStruct(TargetStruct):
    h0000_array: GWArray
    h0010: int
    h0014_array: GWArray
    h0024: list[int]
    h0034_array: GWArray
    h0044_array: GWArray
    h0054: list[int]
    player_uuid_ptr: tuple[int, int, int, int]
    player_name_enc: str
    h009C: list[int]
    h00EC_array: GWArray
    h00FC: list[int]
    world_flags: int
    token1: int
    map_id: int
    is_explorable: int
    host: list[int]
    token2: int
    h01BC: list[int]
    district_number: int
    language: int
    observe_map_id: int
    current_map_id: int
    observe_map_type: int
    current_map_type: int
    h0240: list[int]
    observer_matches_array: GWArray
    h0264: list[int]
    player_flags: int
    player_number: int
    h02B0: list[int]
    progress_bar_ptr: int
    h0354: list[int]
    player_email_ptr: str

    @property
    def player_uuid(self) -> tuple[int, int, int, int]: ...

    @property
    def h0000_ptrs(self) -> list[int] | None: ...

    @property
    def h0014_ptrs(self) -> list[int] | None: ...

    @property
    def h0034_ptrs(self) -> list[int] | None: ...

    @property
    def h0044_ptrs(self) -> list[int] | None: ...

    @property
    def h00EC_ptrs(self) -> list[int] | None: ...

    @property
    def observer_matches(self) -> list[ObserverMatch] | None: ...

    @property
    def progress_bar(self) -> ProgressBar | None: ...

    @property
    def player_name_encoded_str(self) -> str | None: ...

    @property
    def player_name_str(self) -> str | None: ...

    @property
    def player_email_encoded_str(self) -> str | None: ...

    @property
    def player_email_str(self) -> str | None: ...


class CharContext:
    _ptr: ClassVar[int]
    _cached_ctx: ClassVar[CharContextStruct | None]
    _callback_name: ClassVar[str]

    def __init__(
        self,
        reader: Any,
        scanner: Any,
        patterns: Any,
        game_context: Any | None = ...,
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
    def get_context() -> CharContextStruct | None: ...

    def resolve_address(self) -> int: ...
    def initialize(self) -> int: ...

    @property
    def cached_base_pointer_address(self) -> int | None: ...

    @property
    def is_logged_in(self) -> bool: ...

    def read(self) -> CharContextStruct: ...
    def read_player_name(self) -> str: ...


def get() -> CharContextStruct | None: ...
