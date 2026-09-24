from ..helpers.target_struct import TargetStruct
from ctypes import Structure
from typing import Any, Optional

from ..scanner import PatternCatalog, RemoteScanner
from .game_context import GameContext
from .gw_array import GWArray, RemoteMemoryReader
from .gw_list import GWLinkStruct, GWListStruct


class PlayerPartyMemberStruct(TargetStruct):
    login_number: int
    called_target_id: int
    state: int

    @property
    def calledTargetId(self) -> int: ...

    @property
    def is_connected(self) -> bool: ...

    @property
    def is_ticked(self) -> bool: ...

    def connected(self) -> bool: ...

    def ticked(self) -> bool: ...


PlayerPartyMember = PlayerPartyMemberStruct


class HeroPartyMemberStruct(TargetStruct):
    agent_id: int
    owner_player_id: int
    hero_id: int
    h000C: int
    h0010: int
    level: int


HeroPartyMember = HeroPartyMemberStruct


class HenchmanPartyMemberStruct(TargetStruct):
    agent_id: int
    h0004: Any
    profession: int
    level: int


HenchmanPartyMember = HenchmanPartyMemberStruct


class PartyInfoStruct(TargetStruct):
    party_id: int
    players_array: GWArray
    henchmen_array: GWArray
    heroes_array: GWArray
    others_array: GWArray
    h0044: Any
    invite_link: GWLinkStruct

    def bind_reader(
        self, reader: RemoteMemoryReader, address: int | None = ...
    ) -> PartyInfoStruct: ...

    def GetPartySize(self) -> int: ...

    @property
    def players(self) -> list[PlayerPartyMemberStruct]: ...

    @property
    def henchmen(self) -> list[HenchmanPartyMemberStruct]: ...

    @property
    def heroes(self) -> list[HeroPartyMemberStruct]: ...

    @property
    def others(self) -> list[int]: ...

    @property
    def invite_links(self) -> list[PartyInfoStruct]: ...


class PartySearchStruct(TargetStruct):
    party_search_id: int
    party_search_type: int
    hardmode: int
    district: int
    language: int
    party_size: int
    hero_count: int
    message: Any
    party_leader: Any
    primary: int
    secondary: int
    level: int
    timestamp: int

    @property
    def message_encoded_str(self) -> str: ...

    @property
    def message_str(self) -> str: ...

    @property
    def party_leader_encoded_str(self) -> str: ...

    @property
    def party_leader_str(self) -> str: ...


class PartySearchType:
    PartySearchType_Hunting: int
    PartySearchType_Mission: int
    PartySearchType_Quest: int
    PartySearchType_Trade: int
    PartySearchType_Guild: int
    HUNTING: int
    MISSION: int
    QUEST: int
    TRADE: int
    GUILD: int


class PartyContextStruct(TargetStruct):
    h0000: int
    h0004_array: GWArray
    flag: int
    h0018: int
    request_list: GWListStruct
    requests_count: int
    sending_list: GWListStruct
    sending_count: int
    h003C: int
    parties_array: GWArray
    h0050: int
    player_party_ptr: int
    h0058: Any
    party_search_array: GWArray

    def bind_reader(
        self, reader: RemoteMemoryReader, address: int | None = ...
    ) -> PartyContextStruct: ...

    @property
    def h0004(self) -> GWArray: ...

    @property
    def in_hard_mode(self) -> bool: ...

    @property
    def is_defeated(self) -> bool: ...

    @property
    def is_party_leader(self) -> bool: ...

    def InHardMode(self) -> bool: ...

    def IsDefeated(self) -> bool: ...

    def IsPartyLeader(self) -> bool: ...

    @property
    def h0004_ptrs(self) -> list[int]: ...

    @property
    def requests(self) -> list[PartyInfoStruct]: ...

    @property
    def request(self) -> list[PartyInfoStruct]: ...

    @property
    def sending(self) -> list[PartyInfoStruct]: ...

    @property
    def parties(self) -> list[PartyInfoStruct]: ...

    @property
    def player_party(self) -> PartyInfoStruct | None: ...

    @property
    def party_searches(self) -> list[PartySearchStruct]: ...

    @property
    def party_search(self) -> list[PartySearchStruct]: ...


class PartyContext:
    _ptr: int
    _cached_ptr: int
    _cached_ctx: PartyContextStruct | None
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
    def get_context() -> Optional[PartyContextStruct]: ...

    def resolve_address(self) -> int | None: ...

    def read(self) -> PartyContextStruct | None: ...


def get() -> PartyContextStruct | None: ...
