from ..helpers.target_struct import TargetStruct
from ctypes import Structure, Union
from typing import Any, Optional

from .game_context import GameContext
from .gw_array import GWArray, RemoteMemoryReader


class GHKeyStruct(Union):
    key_data: Any
    k: Any

    @property
    def as_string(self) -> str: ...

    @property
    def is_valid(self) -> bool: ...

    @classmethod
    def from_hex(cls, hex_string: str) -> GHKeyStruct: ...


GHKey = GHKeyStruct


class CapeDesignStruct(TargetStruct):
    cape_bg_color: int
    cape_detail_color: int
    cape_emblem_color: int
    cape_shape: int
    cape_detail: int
    cape_emblem: int
    cape_trim: int


CapeDesign = CapeDesignStruct


class TownAllianceStruct(TargetStruct):
    rank: int
    allegiance: int
    faction: int
    name_enc: Any
    tag_enc: Any
    cape: CapeDesignStruct
    map_id: int

    @property
    def name(self) -> Any: ...

    @property
    def tag(self) -> Any: ...

    @property
    def name_encoded_str(self) -> str: ...

    @property
    def name_str(self) -> str: ...

    @property
    def tag_encoded_str(self) -> str: ...

    @property
    def tag_str(self) -> str: ...


TownAlliance = TownAllianceStruct


class GuildHistoryEventStruct(TargetStruct):
    time1: int
    time2: int
    name_enc: Any

    @property
    def name(self) -> Any: ...

    @property
    def name_encoded_str(self) -> str: ...

    @property
    def name_str(self) -> str: ...


GuildHistoryEvent = GuildHistoryEventStruct


class GuildStruct(TargetStruct):
    key: GHKeyStruct
    h0010: Any
    index: int
    rank: int
    features: int
    name_enc: Any
    rating: int
    faction: int
    faction_point: int
    qualifier_point: int
    tag_enc: Any
    cape: CapeDesignStruct

    @property
    def name(self) -> Any: ...

    @property
    def tag(self) -> Any: ...

    @property
    def name_encoded_str(self) -> str: ...

    @property
    def name_str(self) -> str: ...

    @property
    def tag_encoded_str(self) -> str: ...

    @property
    def tag_str(self) -> str: ...


Guild = GuildStruct


class GuildPlayerStruct(TargetStruct):
    vtable: int
    name_ptr: int
    invited_name_enc: Any
    current_name_enc: Any
    inviter_name_enc: Any
    invite_time: int
    promoter_name_enc: Any
    h00AC: Any
    offline: int
    member_type: int
    status: int
    h00E8: Any

    @property
    def invited_name(self) -> Any: ...

    @property
    def current_name(self) -> Any: ...

    @property
    def inviter_name(self) -> Any: ...

    @property
    def promoter_name(self) -> Any: ...

    @property
    def name_encoded_str(self) -> str | None: ...

    @property
    def name_str(self) -> str | None: ...

    @property
    def invited_name_encoded_str(self) -> str: ...

    @property
    def invited_name_str(self) -> str: ...

    @property
    def current_name_encoded_str(self) -> str: ...

    @property
    def current_name_str(self) -> str: ...

    @property
    def inviter_name_encoded_str(self) -> str: ...

    @property
    def inviter_name_str(self) -> str: ...

    @property
    def promoter_name_encoded_str(self) -> str: ...

    @property
    def promoter_name_str(self) -> str: ...


GuildPlayer = GuildPlayerStruct


class GuildContextStruct(TargetStruct):
    h0000: int
    h0004: int
    h0008: int
    h000C: int
    h0010: int
    h0014: int
    h0018: int
    h001C: int
    h0020_array: GWArray
    h0030: int
    player_name_enc: Any
    h005C: int
    player_guild_index: int
    player_gh_key: GHKeyStruct
    h0074: int
    announcement_enc: Any
    announcement_author_enc: Any
    player_guild_rank: int
    h02A4: int
    factions_outpost_guilds_array: GWArray
    kurzick_town_count: int
    luxon_town_count: int
    h02C0: int
    h02C4: int
    h02C8: int
    player_guild_history_array: GWArray
    h02DC: Any
    guild_array_array: GWArray
    h0308: Any
    h0318_array: GWArray
    h0328: int
    h032C_array: GWArray
    h033C: Any
    player_roster_array: GWArray

    def bind_reader(
        self, reader: RemoteMemoryReader, address: int | None = ...
    ) -> GuildContextStruct: ...

    @property
    def h0020_ptrs(self) -> list[int] | None: ...

    @property
    def h0020(self) -> GWArray: ...

    @property
    def player_name_encoded_str(self) -> str: ...

    @property
    def player_name_str(self) -> str | None: ...

    @property
    def announcement_encoded_str(self) -> str: ...

    @property
    def announcement_str(self) -> str | None: ...

    @property
    def announcement_author_encoded_str(self) -> str: ...

    @property
    def announcement_author_str(self) -> str | None: ...

    @property
    def factions_outpost_guilds(self) -> list[TownAllianceStruct] | None: ...

    @property
    def player_guild_history(self) -> list[GuildHistoryEventStruct] | None: ...

    @property
    def guild_array(self) -> list[GuildStruct] | None: ...

    @property
    def h0318_ptrs(self) -> list[int] | None: ...

    @property
    def h0318(self) -> GWArray: ...

    @property
    def h032C_ptrs(self) -> list[int] | None: ...

    @property
    def h032C(self) -> GWArray: ...

    @property
    def player_roster(self) -> list[GuildPlayerStruct] | None: ...

    @property
    def guilds(self) -> list[GuildStruct] | None: ...


class GuildContext:
    _ptr: int
    _cached_ctx: GuildContextStruct | None
    _callback_name: str

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
    def get_context() -> Optional[GuildContextStruct]: ...

    def resolve_address(self) -> int | None: ...

    def read(self) -> GuildContextStruct | None: ...


def get() -> GuildContextStruct | None: ...

def get_guild_array() -> GWArray | None: ...

GetGuildArray = get_guild_array
