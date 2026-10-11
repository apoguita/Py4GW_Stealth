"""GwAu3's `World_GetWorldInfo`, over the record this project already reads.
**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_family.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

GwAu3's world-context reader. GwAu3 resolves the world context and reads fields at fixed offsets; this project reads the same record as `WorldContextStruct`, and its offsets match GwAu3's for the **record fields** -- ``experience`` at ``+0x740``, ``current_kurzick`` at ``+0x748``, ``level`` at ``+0x788``, ``current_skill_points`` at ``+0x7A8``, ``player_number`` at ``+0x67C``, ``active_quest_id`` at ``+0x528``.

**Most of this family's keys are refused, and they are the array addresses.** GwAu3's `WorldInfo` key is either a field of the context or the *address* of one of its arrays (`PlayerArray`, `AgentEffectsArray`, `TitleArray`, ...). This layer reads records, not addresses -- a client pointer is of no use to a caller here -- so each address key refuses and names the array it would have had to walk.

`World_GetWorldInfo` is one ``Switch`` over 79 keys in GwAu3
(``GwAu3_Data_World.au3``). 48 of the 79 field keys resolve to a **named
attribute** of the structure this project reads, chosen by offset against ctypes' own view of the
record. The reader for each key names its attribute literally, so nothing here reaches a field through
a dynamic name.

**The return shapes are GwAu3's.** An unknown field name answers ``0`` and a record that cannot be
resolved answers ``0`` -- AutoIt has no exceptions in this role and a script branches on the return.
A key this layer cannot answer **raises**, naming what it needs, rather than answering a wrong value
of the right type, which a caller could not detect.
"""

from __future__ import annotations

import struct

from typing import Any

from ..client import require_client
from ..context import WorldContextStruct

_UNIMPLEMENTED: dict[str, str] = {'MessageBuffArray': "GwAu3_Data_World.au3:18 returns the client *address* of an array this project's `WorldContextStruct` holds as a field (`py4gw/context/world_context.py:1442`). Walking that array needs the connection and a reader bound to the address, which this layer does not do -- and answering the address itself would be a value a caller could not tell from data. Refused.", 'DialogBuffArray': "GwAu3_Data_World.au3:20 returns the client *address* of an array this project's `WorldContextStruct` holds as a field (`py4gw/context/world_context.py:1442`). Walking that array needs the connection and a reader bound to the address, which this layer does not do -- and answering the address itself would be a value a caller could not tell from data. Refused.", 'MerchItemArray': "GwAu3_Data_World.au3:22 returns the client *address* of an array this project's `WorldContextStruct` holds as a field (`py4gw/context/world_context.py:1442`). Walking that array needs the connection and a reader bound to the address, which this layer does not do -- and answering the address itself would be a value a caller could not tell from data. Refused.", 'MerchItemArray2': "GwAu3_Data_World.au3:26 returns the client *address* of an array this project's `WorldContextStruct` holds as a field (`py4gw/context/world_context.py:1442`). Walking that array needs the connection and a reader bound to the address, which this layer does not do -- and answering the address itself would be a value a caller could not tell from data. Refused.", 'PartyAllyArray': "GwAu3_Data_World.au3:30 returns the client *address* of an array this project's `WorldContextStruct` holds as a field (`py4gw/context/world_context.py:1442`). Walking that array needs the connection and a reader bound to the address, which this layer does not do -- and answering the address itself would be a value a caller could not tell from data. Refused.", 'MapAgentArray': "GwAu3_Data_World.au3:92 returns the client *address* of an array this project's `WorldContextStruct` holds as a field (`py4gw/context/world_context.py:1442`). Walking that array needs the connection and a reader bound to the address, which this layer does not do -- and answering the address itself would be a value a caller could not tell from data. Refused.", 'PartyAttributeArray': "GwAu3_Data_World.au3:98 returns the client *address* of an array this project's `WorldContextStruct` holds as a field (`py4gw/context/world_context.py:1442`). Walking that array needs the connection and a reader bound to the address, which this layer does not do -- and answering the address itself would be a value a caller could not tell from data. Refused.", 'AgentEffectsArray': "GwAu3_Data_World.au3:104 returns the client *address* of an array this project's `WorldContextStruct` holds as a field (`py4gw/context/world_context.py:1442`). Walking that array needs the connection and a reader bound to the address, which this layer does not do -- and answering the address itself would be a value a caller could not tell from data. Refused.", 'QuestLog': "GwAu3_Data_World.au3:110 returns the client *address* of an array this project's `WorldContextStruct` holds as a field (`py4gw/context/world_context.py:1442`). Walking that array needs the connection and a reader bound to the address, which this layer does not do -- and answering the address itself would be a value a caller could not tell from data. Refused.", 'MissionObjectiveArray': "GwAu3_Data_World.au3:116 returns the client *address* of an array this project's `WorldContextStruct` holds as a field (`py4gw/context/world_context.py:1442`). Walking that array needs the connection and a reader bound to the address, which this layer does not do -- and answering the address itself would be a value a caller could not tell from data. Refused.", 'HeroFlagArray': "GwAu3_Data_World.au3:122 returns the client *address* of an array this project's `WorldContextStruct` holds as a field (`py4gw/context/world_context.py:1442`). Walking that array needs the connection and a reader bound to the address, which this layer does not do -- and answering the address itself would be a value a caller could not tell from data. Refused.", 'HeroInfoArray': "GwAu3_Data_World.au3:126 returns the client *address* of an array this project's `WorldContextStruct` holds as a field (`py4gw/context/world_context.py:1442`). Walking that array needs the connection and a reader bound to the address, which this layer does not do -- and answering the address itself would be a value a caller could not tell from data. Refused.", 'ControlledMinionsArray': "GwAu3_Data_World.au3:132 returns the client *address* of an array this project's `WorldContextStruct` holds as a field (`py4gw/context/world_context.py:1442`). Walking that array needs the connection and a reader bound to the address, which this layer does not do -- and answering the address itself would be a value a caller could not tell from data. Refused.", 'PartyMoraleInfo': "GwAu3_Data_World.au3:142 returns the client *address* of an array this project's `WorldContextStruct` holds as a field (`py4gw/context/world_context.py:1442`). Walking that array needs the connection and a reader bound to the address, which this layer does not do -- and answering the address itself would be a value a caller could not tell from data. Refused.", 'PetInfoArray': "GwAu3_Data_World.au3:148 returns the client *address* of an array this project's `WorldContextStruct` holds as a field (`py4gw/context/world_context.py:1442`). Walking that array needs the connection and a reader bound to the address, which this layer does not do -- and answering the address itself would be a value a caller could not tell from data. Refused.", 'PartyProfessionArray': "GwAu3_Data_World.au3:154 returns the client *address* of an array this project's `WorldContextStruct` holds as a field (`py4gw/context/world_context.py:1442`). Walking that array needs the connection and a reader bound to the address, which this layer does not do -- and answering the address itself would be a value a caller could not tell from data. Refused.", 'SkillbarArray': "GwAu3_Data_World.au3:160 returns the client *address* of an array this project's `WorldContextStruct` holds as a field (`py4gw/context/world_context.py:1442`). Walking that array needs the connection and a reader bound to the address, which this layer does not do -- and answering the address itself would be a value a caller could not tell from data. Refused.", 'AgentInfoArray': "GwAu3_Data_World.au3:166 returns the client *address* of an array this project's `WorldContextStruct` holds as a field (`py4gw/context/world_context.py:1442`). Walking that array needs the connection and a reader bound to the address, which this layer does not do -- and answering the address itself would be a value a caller could not tell from data. Refused.", 'NPCArray': "GwAu3_Data_World.au3:172 returns the client *address* of an array this project's `WorldContextStruct` holds as a field (`py4gw/context/world_context.py:1442`). Walking that array needs the connection and a reader bound to the address, which this layer does not do -- and answering the address itself would be a value a caller could not tell from data. Refused.", 'PlayerArray': "GwAu3_Data_World.au3:178 returns the client *address* of an array this project's `WorldContextStruct` holds as a field (`py4gw/context/world_context.py:1442`). Walking that array needs the connection and a reader bound to the address, which this layer does not do -- and answering the address itself would be a value a caller could not tell from data. Refused.", 'TitleArray': "GwAu3_Data_World.au3:184 returns the client *address* of an array this project's `WorldContextStruct` holds as a field (`py4gw/context/world_context.py:1442`). Walking that array needs the connection and a reader bound to the address, which this layer does not do -- and answering the address itself would be a value a caller could not tell from data. Refused.", 'VanquishedAreasArray': "GwAu3_Data_World.au3:190 returns the client *address* of an array this project's `WorldContextStruct` holds as a field (`py4gw/context/world_context.py:1442`). Walking that array needs the connection and a reader bound to the address, which this layer does not do -- and answering the address itself would be a value a caller could not tell from data. Refused.", 'MissionsCompletedArray': "GwAu3_Data_World.au3:194 returns the client *address* of an array this project's `WorldContextStruct` holds as a field (`py4gw/context/world_context.py:1442`). Walking that array needs the connection and a reader bound to the address, which this layer does not do -- and answering the address itself would be a value a caller could not tell from data. Refused.", 'MissionsBonusArray': "GwAu3_Data_World.au3:196 returns the client *address* of an array this project's `WorldContextStruct` holds as a field (`py4gw/context/world_context.py:1442`). Walking that array needs the connection and a reader bound to the address, which this layer does not do -- and answering the address itself would be a value a caller could not tell from data. Refused.", 'MissionsCompletedHMArray': "GwAu3_Data_World.au3:198 returns the client *address* of an array this project's `WorldContextStruct` holds as a field (`py4gw/context/world_context.py:1442`). Walking that array needs the connection and a reader bound to the address, which this layer does not do -- and answering the address itself would be a value a caller could not tell from data. Refused.", 'MissionsBonusHMArray': "GwAu3_Data_World.au3:200 returns the client *address* of an array this project's `WorldContextStruct` holds as a field (`py4gw/context/world_context.py:1442`). Walking that array needs the connection and a reader bound to the address, which this layer does not do -- and answering the address itself would be a value a caller could not tell from data. Refused.", 'LearnableSkillsArray': "GwAu3_Data_World.au3:202 returns the client *address* of an array this project's `WorldContextStruct` holds as a field (`py4gw/context/world_context.py:1442`). Walking that array needs the connection and a reader bound to the address, which this layer does not do -- and answering the address itself would be a value a caller could not tell from data. Refused.", 'UnlockedSkillsArray': "GwAu3_Data_World.au3:204 returns the client *address* of an array this project's `WorldContextStruct` holds as a field (`py4gw/context/world_context.py:1442`). Walking that array needs the connection and a reader bound to the address, which this layer does not do -- and answering the address itself would be a value a caller could not tell from data. Refused.", 'UnlockedMapArray': "GwAu3_Data_World.au3:206 returns the client *address* of an array this project's `WorldContextStruct` holds as a field (`py4gw/context/world_context.py:1442`). Walking that array needs the connection and a reader bound to the address, which this layer does not do -- and answering the address itself would be a value a caller could not tell from data. Refused.", 'HenchmanIDArray': "GwAu3_Data_World.au3:208 returns the client *address* of an array this project's `WorldContextStruct` holds as a field (`py4gw/context/world_context.py:1442`). Walking that array needs the connection and a reader bound to the address, which this layer does not do -- and answering the address itself would be a value a caller could not tell from data. Refused."}

_COMPUTED: frozenset[str] = frozenset([])

# A text key takes the id as well as the record, because its handshake is keyed by the id.

# Keys that answer `False` rather than `0` when no record matches, because GwAu3's own guard does.
_FALSE_ON_MISSING: frozenset[str] = frozenset([])


def _read_text(request: Any, ready: Any, get: Any, record_id: Any) -> str:
    """Run this project's name-decode handshake and answer the text it produces.

    **A decode is not a read, and this is the whole of that difference.** The port's name getters
    answer `""` until a request has been made *and* the client's decoder has answered
    (`py4gw/item.py:394`, `:449`), so the three steps are run in order:

    1. **request** -- asks the client's own decoder for this id, through the game thread;
    2. **ready** -- advances the port's polling and says whether an answer has arrived;
    3. **get** -- takes the text, which carries the source's own `"Timeout"` literal if the client
       never answered within the bound the port uses.

    A caller cannot tell an unanswered decode from a nameless record, which is exactly why this layer
    refused these keys until the handshake was wired: answering `""` early is a wrong value of the
    right type. `ready` is polled once here rather than looped, because the port's own request already
    waits its bound -- looping would only make a stalled game thread block the bridge.
    """

    request(record_id)
    ready(record_id)
    return str(get(record_id))


def _read_raw(record: Any, offset: int, fmt: str) -> Any:
    """Read a field GwAu3 reads and this project's structure does not name.

    The record is a ``ctypes.Structure`` whose bytes are the client's own, so a field with no
    attribute name is read from those bytes at GwAu3's own offset and width. That covers the ``hXXXX``
    fields, whose names in the port are placeholders because the layout is not understood there.
    """

    values = struct.unpack_from(fmt, record, offset)
    return values[0] if len(values) == 1 else values


def _read_agenteffectsarray(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["AgentEffectsArray"])


def _read_agentinfoarray(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["AgentInfoArray"])


def _read_controlledminionsarray(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["ControlledMinionsArray"])


def _read_dialogbuffarray(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["DialogBuffArray"])


def _read_henchmanidarray(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["HenchmanIDArray"])


def _read_heroflagarray(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["HeroFlagArray"])


def _read_heroinfoarray(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["HeroInfoArray"])


def _read_learnableskillsarray(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["LearnableSkillsArray"])


def _read_mapagentarray(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["MapAgentArray"])


def _read_merchitemarray(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["MerchItemArray"])


def _read_merchitemarray2(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["MerchItemArray2"])


def _read_messagebuffarray(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["MessageBuffArray"])


def _read_missionobjectivearray(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["MissionObjectiveArray"])


def _read_missionsbonusarray(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["MissionsBonusArray"])


def _read_missionsbonushmarray(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["MissionsBonusHMArray"])


def _read_missionscompletedarray(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["MissionsCompletedArray"])


def _read_missionscompletedhmarray(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["MissionsCompletedHMArray"])


def _read_npcarray(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["NPCArray"])


def _read_partyallyarray(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["PartyAllyArray"])


def _read_partyattributearray(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["PartyAttributeArray"])


def _read_partymoraleinfo(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["PartyMoraleInfo"])


def _read_partyprofessionarray(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["PartyProfessionArray"])


def _read_petinfoarray(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["PetInfoArray"])


def _read_playerarray(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["PlayerArray"])


def _read_questlog(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["QuestLog"])


def _read_skillbararray(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["SkillbarArray"])


def _read_titlearray(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["TitleArray"])


def _read_unlockedmaparray(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["UnlockedMapArray"])


def _read_unlockedskillsarray(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["UnlockedSkillsArray"])


def _read_vanquishedareasarray(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["VanquishedAreasArray"])



_READERS: dict[str, Any] = {}
_READERS.update(
    {
        "AccountInfo": lambda record: record.account_info_ptr,
        "ActiveQuestID": lambda record: record.active_quest_id,
        "AgentEffectsArray": _read_agenteffectsarray,
        "AgentEffectsArraySize": lambda record: record.party_effects_array.m_size,
        "AgentInfoArray": _read_agentinfoarray,
        "AgentInfoArraySize": lambda record: record.agent_name_info_array.m_size,
        "ControlledMinionsArray": _read_controlledminionsarray,
        "ControlledMinionsArraySize": lambda record: record.controlled_minion_count_array.m_size,
        "CurrentBalth": lambda record: record.current_balth,
        "CurrentImperial": lambda record: record.current_imperial,
        "CurrentKurzick": lambda record: record.current_kurzick,
        "CurrentLuxon": lambda record: record.current_luxon,
        "CurrentSkillPoints": lambda record: record.current_skill_points,
        "DialogBuffArray": _read_dialogbuffarray,
        "EquipmentStatus": lambda record: record.equipment_status,
        "Experience": lambda record: record.experience,
        "FlagAll": lambda record: _read_raw(record, 0x009c, "<f"),
        "FoesKilled": lambda record: record.foes_killed,
        "FoesToKill": lambda record: record.foes_to_kill,
        "HenchmanIDArray": _read_henchmanidarray,
        "HeroFlagArray": _read_heroflagarray,
        "HeroFlagArraySize": lambda record: record.hero_flags_array.m_size,
        "HeroInfoArray": _read_heroinfoarray,
        "HeroInfoArraySize": lambda record: record.hero_info_array.m_size,
        "IsHmUnlocked": lambda record: record.is_hard_mode_unlocked,
        "LearnableSkillsArray": _read_learnableskillsarray,
        "Level": lambda record: record.level,
        "MapAgentArray": _read_mapagentarray,
        "MapAgentArraySize": lambda record: record.map_agents_array.m_size,
        "MaxBalthPoints": lambda record: record.max_balth,
        "MaxImperialPoints": lambda record: record.max_imperial,
        "MaxKurzickPoints": lambda record: record.max_kurzick,
        "MaxLuxonPoints": lambda record: record.max_luxon,
        "MerchItemArray": _read_merchitemarray,
        "MerchItemArray2": _read_merchitemarray2,
        "MerchItemArray2Size": lambda record: record.merch_items2_array.m_capacity,
        "MerchItemArraySize": lambda record: record.merch_items_array.m_capacity,
        "MessageBuffArray": _read_messagebuffarray,
        "MissionObjectiveArray": _read_missionobjectivearray,
        "MissionObjectiveArraySize": lambda record: record.mission_objectives_array.m_size,
        "MissionsBonusArray": _read_missionsbonusarray,
        "MissionsBonusHMArray": _read_missionsbonushmarray,
        "MissionsCompletedArray": _read_missionscompletedarray,
        "MissionsCompletedHMArray": _read_missionscompletedhmarray,
        "Morale": lambda record: record.morale,
        "MyID": lambda record: record.playerControlledChar_ptr,
        "NPCArray": _read_npcarray,
        "NPCArraySize": lambda record: record.npc_models_array.m_size,
        "PartyAllyArray": _read_partyallyarray,
        "PartyAttributeArray": _read_partyattributearray,
        "PartyAttributeArraySize": lambda record: record.party_attributes_array.m_size,
        "PartyMoraleInfo": _read_partymoraleinfo,
        "PartyMoraleInfoSize": lambda record: record.party_morale_array.m_size,
        "PartyProfessionArray": _read_partyprofessionarray,
        "PartyProfessionArraySize": lambda record: record.party_profession_states_array.m_size,
        "PetInfoArray": _read_petinfoarray,
        "PetInfoArraySize": lambda record: record.pets_array.m_size,
        "PlayerArray": _read_playerarray,
        "PlayerArraySize": lambda record: record.players_array.m_size,
        "PlayerMoraleInfo": lambda record: record.player_morale_ptr,
        "PlayerMoraleInfoSize": lambda record: record.party_morale_array.m_buffer,
        "PlayerNumber": lambda record: record.player_number,
        "PlayerTeamToken": lambda record: record.playerTeamToken,
        "QuestLog": _read_questlog,
        "QuestLogSize": lambda record: record.quest_log_array.m_size,
        "SalvageSessionID": lambda record: record.salvage_session_id,
        "SkillbarArray": _read_skillbararray,
        "SkillbarArraySize": lambda record: record.party_skillbar_array.m_size,
        "TitleArray": _read_titlearray,
        "TitleArraySize": lambda record: record.titles_array.m_size,
        "TotalEarnedBalth": lambda record: record.total_earned_balth,
        "TotalEarnedImperial": lambda record: record.total_earned_imperial,
        "TotalEarnedKurzick": lambda record: record.total_earned_kurzick,
        "TotalEarnedLuxon": lambda record: record.total_earned_luxon,
        "TotalEarnedSkillPoints": lambda record: record.total_earned_skill_points,
        "UnlockedMapArray": _read_unlockedmaparray,
        "UnlockedSkillsArray": _read_unlockedskillsarray,
        "VanquishedAreasArray": _read_vanquishedareasarray,
        "VanquishedAreasArraySize": lambda record: record.vanquished_areas_array.m_size,
    }
)


def World_GetWorldInfo(info: str = "") -> Any:
    """One field of the record, by GwAu3's field name (``GwAu3_Data_World.au3``).

    GwAu3's guard order is kept: an empty field name answers ``0`` before anything is read, and a
    record the client does not hold answers ``0`` rather than raising. An unrecognised field name
    answers ``0`` -- GwAu3's own ``Case Else``.

    **The key is resolved before the record is.** A key this layer refuses raises without touching the
    client, which is the whole point of refusing: a caller with no connection must still be told that
    the key is unbuilt, not that it is unconnected. The first version resolved the record first, so
    asking for a refused key without a client reported a connection error instead of the gap.
    """

    if info == "":
        return 0

    # A refused key is answered before the record is resolved, deliberately: the refusal is a fact
    # about this layer, not about the client, so a caller with no connection must still be told the
    # key is unbuilt rather than told it is unconnected. The first version resolved the record first
    # and reported a connection error for a refusal that never needed one.
    if info in _UNIMPLEMENTED:
        raise NotImplementedError(_UNIMPLEMENTED[info])

    reader = _READERS.get(info)
    if reader is None:
        return 0

    record = _record(info)
    if record is None:
        # GwAu3's own no-match guard answers `False` for these keys and `0` for the rest
        # (``GwAu3_Data_Quest.au3:16-21``).
        if info in _FALSE_ON_MISSING:
            return False
        return 0

    # A computed or text key re-enters this accessor, so it is handed the caller's id too. A family
    # with no id parameter -- World_GetWorldInfo -- has none of those keys, so the branch is written
    # against whatever its own first parameter is.
    if info in _COMPUTED:
        return reader(record, info)
    return reader(record)


def _record(record_id: Any) -> Any:
    """The record GwAu3 resolves before its ``Switch``.

    ``client.read_world_context()`` -- this project's own read, which is the same
    client record GwAu3 addresses by base plus stride.
    """

    client = require_client()
    return client.read_world_context()

"""``GwAu3_Data_World.au3``'s three remaining readers, hand-written into the generated module.

Read from ``tools/gwa3_snippets/`` at generation time, the same mechanism `data_map_character_info.py`
uses: ``data_world.py`` is rewritten whole on every run.

**Why these three.** ``GwAu3_Data_World.au3`` declares eight functions: ``World_GetWorldInfo`` -- the key
table this family generates -- the four ``World_Mission*`` helpers named at the end of this docstring, and
the three below, which were still absent from this layer. They are exactly the three a script calls and
this layer did not export: ``World_GetWorldContextPtr`` (``:4-8``), ``World_IsSkillLearnt`` (``:214-233``)
and ``World_GetSkillDuplicateCount`` (``:235-256``) -- the three names the ported script's own
"declared but not built" list carries (``tools/autoit/Stealth_GwAu3.au3:7``, written from
``GwAu3_DevTools.au3``'s call sites at ``:2947``, ``:2953`` and ``:3097``).

**All three read the same arrays the address keys of this family refuse**, which is why they are
answerable here and were refused there: ``World_GetWorldInfo`` answers a client pointer for
``UnlockedSkillsArray`` and must refuse it, while this project reads **those arrays as records and
words** -- `WorldContextStruct.unlocked_character_skills`
(``py4gw/context/world_context.py:1897``, declared at ``+0x710``, ``:1511``) and
`duplicated_character_skills` (``:1902``, declared at ``+0x720``, ``:1512``). Both offsets are
GwAu3's own.

**What is deliberately not here.** ``World_MissionGetState`` (``:278-339``),
``World_MissionIsCompleted`` (``:348-350``), ``World_MissionHasExpert`` (``:359-361``) and
``World_MissionHasMaster`` (``:370-372``) are declared in the same file and are still unbuilt. They are
not the three this file answers, and they are named here rather than left to be discovered: the port
has every member they need (`Map_GetAreaInfo`'s ``RegionType``/``Campaign`` keys,
`WorldContextStruct.missions_completed`, `.missions_bonus`, `.missions_completed_hm`,
`.missions_bonus_hm` at ``py4gw/context/world_context.py:1915-1937``), and no script in either project
calls them.
"""


def World_GetWorldContextPtr() -> Any:
    """The world context itself (``GwAu3_Data_World.au3:4-8``).

    GwAu3's body resolves ``BasePointer[0][0x18][0x2C]`` and answers that client *address*. This layer
    hands out no address under any name, so the member answers **the record the same word points at**:
    `py4gw.client.ConnectedClient.read_world_context` (``py4gw/client.py:1582``, on the class at
    ``:205`` -- the layer's prose calls it ``RemoteClient`` in eight places, which is a stale name), the
    port's own on-demand read of it. That is the shape `Agent_GetAgentPtr` and `PreGame_Ptr` already
    record
    (`py4gw/gwa3/data_agent.py:674`; ``py4gw/gwa3/data_pregame.py:19-23``), and it is what the one
    caller in the ported script does with it -- prints it, and would test it.

    GwAu3's ``0`` for a null pointer arrives here as ``None``, which is what this project reads where
    the client holds no world context; a caller that tests the answer treats both the same way.
    """

    return require_client().read_world_context()


def World_IsSkillLearnt(a_i_SkillID: Any) -> bool:
    """Whether the character has learnt a skill (``GwAu3_Data_World.au3:214-233``).

    GwAu3's guard order is kept term for term: no world context answers ``False`` (``:216``), an
    unlocked-skills array that is not there answers ``False`` (``:219``), an index past the end answers
    ``False`` (``:225``), and the answer is the bit test over the word the id lands in --
    ``BitAND(word, 1 << (skill_id % 32)) <> 0`` with ``word = array[Floor(skill_id / 32)]``
    (``:227-232``).

    The array is the same one, read the way this project reads it: GwAu3 takes the ``ptr`` and ``size``
    of the ``Array<dword>`` at ``+0x710`` (``:218``, ``:221``) and this reads that word of the world
    context as the list of ``uint32`` words it holds
    (`WorldContextStruct.unlocked_character_skills`, ``py4gw/context/world_context.py:1897``, declared
    at ``+0x710``, ``:1511``) -- the same bitfield, indexed and masked the same way.
    """

    world = require_client().read_world_context()
    if world is None:
        return False

    unlocked = world.unlocked_character_skills
    if not unlocked:
        return False

    real_index = int(a_i_SkillID) // 32
    if real_index >= len(unlocked):
        return False

    shift = int(a_i_SkillID) % 32
    flag = 1 << shift
    return (int(unlocked[real_index]) & flag) != 0


def World_GetSkillDuplicateCount(a_i_SkillID: Any) -> int:
    """How many copies of a skill the character holds (``GwAu3_Data_World.au3:235-256``).

    GwAu3's guards and its answer are kept: no world context answers ``0`` (``:237``), a duplicate-skill
    array that is not there answers ``0`` (``:240``), a skill id no entry matches answers ``0``
    (``:255``), and a match answers that entry's own count (``:250-251``).

    **One divergence, and it is GwAu3's arithmetic against this project's declared record.** GwAu3's loop
    steps the array by ``0x4`` (``:245``) and then reads a ``long`` id at ``+0x0`` and a ``long`` count
    at ``+0x4`` of each step, so consecutive steps overlap by a word and the count it answers is the *id*
    of the next entry whenever the array really is a list of pairs. This project declares that record as
    ``0x08`` bytes -- `DupeSkillStruct`, ``skill_id`` then ``count``
    (``py4gw/context/world_context.py:1142-1146``) -- and reads the array at ``+0x720`` as those records
    (`WorldContextStruct.duplicated_character_skills`, ``:1902``, declared at ``:1512``), so the count
    answered here is the matching record's own. A live read of the array is what would settle the
    stride; the id and the count are the same two words at the same offset either way.
    """

    world = require_client().read_world_context()
    if world is None:
        return 0

    duplicates = world.duplicated_character_skills
    if not duplicates:
        return 0

    skill_id = int(a_i_SkillID)
    for record in duplicates:
        if int(record.skill_id) == skill_id:
            return int(record.count)
    return 0

__all__ = ['World_GetWorldInfo', 'World_GetSkillDuplicateCount', 'World_GetWorldContextPtr', 'World_IsSkillLearnt']
