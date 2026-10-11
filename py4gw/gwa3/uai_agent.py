"""GwAu3's ``UAI_*`` agent-cache accessors, over this project's own agent reads.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

**What this module is, and what it is not.** GwAu3's UtilityAI keeps a wide cached array of agent
columns -- ``$g_amx2_AgentCache[row][$GC_UAI_AGENT_*]``, eighty-eight columns, filled once per frame by
``UAI_CacheAgentInfo`` -- and the rest of the plugin reads it by *column index* rather than by field
name. This module answers those columns from **this project's live agent reads** instead of from a
cached row. That is a real semantic difference and it is the honest one here: this project has no frame
loop, so there is no tick to snapshot against, and a read taken now is the same fact taken later rather
than a second fact. The column table is keyed by the very constants GwAu3's own ``Global Enum``
declares, so the mapping is transcribed rather than renumbered.

**Three columns used to be refused as a finding about GwAu3, and the finding is now settled with
evidence.** The model-state sets in ``UAI_DecodeAgentInto`` (``UtilityAI_AgentCache.au3:251-259``)
**disagree with the sets in ``GwAu3_Data_Agent.au3:334-347``** for the same three keys:

| Key | ``UAI_DecodeAgentInto`` (the plugin's cache) | ``GwAu3_Data_Agent.au3`` (the Data module) |
| --- | --- | --- |
| ``IsAttacking`` | ``0x40``, ``0x60``, ``0x440``, ``0x460`` | ``0x60``, ``0x440``, ``0x460`` -- **no ``0x40``** |
| ``IsIdle`` | ``0x44``, ``0x64`` | ``0x40``, ``0x44``, ``0x64`` -- **has ``0x40``** |
| ``IsMoving`` | velocity, or ``0x4C``, ``0xCC`` | velocity, or ``0xC``, ``0x4C``, ``0xCC`` -- **has ``0xC``** |

So one GwAu3 file calls ``0x40`` *attacking* while another calls it *idle*. **This project has a third
source, and it is the authority for behaviour here: Reforged Native.** Its ported
`AgentLivingStruct.is_attacking`/`is_idle`/`is_moving` (``py4gw/context/agent_array.py``) use
``{96, 1088, 1120}``, ``{68, 64, 100}`` and ``{12, 76, 204}`` -- which are ``0x60``/``0x440``/``0x460``,
``0x44``/``0x40``/``0x64`` and ``0xC``/``0x4C``/``0xCC``. **That is `GwAu3_Data_Agent.au3`'s three sets
exactly, so the Data module agrees with the porting authority and the plugin's own cache decoder is the
outlier on all three.** The three columns are therefore **routed** to this layer's `Agent_GetAgentInfo`
(whose table was generated from the Data module, so it answers those sets), and the table below keeps the
comparison rather than deleting it.

**Measured live, read-only** (`tests/probe_gwa3_model_state_live.py`, pid 19696, 2026-10-10;
``tests/live_reports/gwa3_model_states.log``), because the disagreement is not academic: of 43 living
agents, **four held model state ``0x40``** -- the state the two GwAu3 files read differently -- while 36
held ``0x44`` (idle in both), one ``0x4C`` (moving in both) and two ``0x42`` (neither). So the choice is
visible on about a tenth of a full map, and the layer answered **the same as the ported Native members on
every one of the 43**.

**The divergence that remains is GwAu3's own and is recorded rather than hidden**: a script that reads
this layer's ``IsAttacking`` is reading the Data module's (and Native's) definition, where GwAu3's
*plugin* would answer its cache's -- differing exactly on ``0x40``, ``0xC`` and a velocity-only move. And
one nuance inside that: the Data module's ``IsMoving`` tests the velocity words *or* the state, while
Native's member tests the state alone; this layer answers the Data module's wider test because that is
the definition the column's own file gives.
"""

from __future__ import annotations

from typing import Any

from ..agent import Agent
from . import constants as _constants
from .data_agent import Agent_ConvertID, Agent_GetAgentInfo, Agent_GetAgentPtr

__all__ = [
    "UAI_GetAgentCount",
    "UAI_GetAgentInfo",
    "UAI_GetAgentInfoByID",
    "UAI_GetIndexByID",
    "UAI_GetPlayerIndex",
    "UAI_GetPlayerInfo",
]

#: ``{column: the field-name key this layer's agent table answers it with}``.
#:
#: **A key table, not eighty-eight readers.** Both tables come from the same client record -- GwAu3's
#: ``UAI_DecodeAgentInto`` fills each column from ``$a_av_Data[n]``, and this project's
#: `Agent_GetAgentInfo` reads the same fields by name with the same arithmetic for the computed ones
#: (``CurrentHP`` is ``hp * max_hp`` in both, the effect bits and the type-map bits are the same
#: literals) -- so the honest port is a translation between two names for one fact, and each entry is
#: the name this layer already answers correctly.
_COLUMN_KEYS: dict[str, str] = {
    "X": "X",
    "Y": "Y",
    "Z": "Z",
    "Plane": "Plane",
    "Rotation": "Rotation",
    "Type": "Type",
    "MoveX": "MoveX",
    "MoveY": "MoveY",
    "Owner": "Owner",
    "ItemID": "ItemID",
    "PlayerNumber": "PlayerNumber",
    "AgentModelType": "AgentModelType",
    "TransmogNpcId": "TransmogNpcId",
    "Primary": "Primary",
    "Secondary": "Secondary",
    "Level": "Level",
    "Team": "Team",
    "EnergyRegen": "EnergyRegen",
    "Overcast": "Overcast",
    "MaxEnergy": "MaxEnergy",
    "CurrentEnergy": "CurrentEnergy",
    "HPPips": "HPPips",
    "HP": "HP",
    "MaxHP": "MaxHP",
    "CurrentHP": "CurrentHP",
    "Effects": "Effects",
    "ModelState": "ModelState",
    "TypeMap": "TypeMap",
    "LoginNumber": "LoginNumber",
    "Allegiance": "Allegiance",
    "WeaponType": "WeaponType",
    "Skill": "Skill",
    "WeaponItemType": "WeaponItemType",
    "OffhandItemType": "OffhandItemType",
    "WeaponItemId": "WeaponItemId",
    "OffhandItemId": "OffhandItemId",
    "IsItemType": "IsItemType",
    "IsGadgetType": "IsGadgetType",
    "IsLivingType": "IsLivingType",
    "CanPickUp": "CanPickUp",
    "IsBleeding": "IsBleeding",
    "IsConditioned": "IsConditioned",
    "IsCrippled": "IsCrippled",
    "IsDead": "IsDead",
    "IsDeepWounded": "IsDeepWounded",
    "IsPoisoned": "IsPoisoned",
    "IsEnchanted": "IsEnchanted",
    "IsDegenHexed": "IsDegenHexed",
    "IsHexed": "IsHexed",
    "IsWeaponSpelled": "IsWeaponSpelled",
    "IsKnockedDown": "IsKnockedDown",
    "IsCasting": "IsCasting",
    "InCombatStance": "InCombatStance",
    "HasQuest": "HasQuest",
    "IsDeadByTypeMap": "IsDeadByTypeMap",
    "IsFemale": "IsFemale",
    "HasBossGlow": "HasBossGlow",
    "IsHidingCap": "IsHidingCap",
    "CanBeViewedInPartyWindow": "CanBeViewedInPartyWindow",
    "IsSpawned": "IsSpawned",
    "IsBeingObserved": "IsBeingObserved",
    # The remaining columns whose GwAu3 source index and this project's field agree. They are the
    # geometric and animation fields: GwAu3 fills them from `$a_av_Data[2..8]`, `[19..21]`, `[25]`,
    # `[41..47]` and this project's table names the same offsets through the agent record.
    "ID": "ID",
    "Ground": "Ground",
    "Width1": "Width1",
    "Height1": "Height1",
    "RotationCos": "RotationCos",
    "RotationSin": "RotationSin",
    "AnimationType": "AnimationType",
    "AttackSpeed": "AttackSpeed",
    "AttackSpeedModifier": "AttackSpeedModifier",
    "Equipment": "Equipment",
    "ExtraType": "ExtraType",
    "GadgetID": "GadgetID",
    "AnimationSpeed": "AnimationSpeed",
    "AnimationCode": "AnimationCode",
    "AnimationId": "AnimationId",
    "LastStrike": "LastStrike",
    # **The three columns GwAu3's two files disagree about, routed because this project has a third
    # source and it settles them.** ``UAI_DecodeAgentInto`` (the plugin's cache decoder) reads model
    # state ``0x40`` as *attacking* and omits it from *idle*, and omits ``0xC`` from *moving*;
    # ``GwAu3_Data_Agent.au3`` does the opposite, and Reforged Native's own ported members
    # (`AgentLivingStruct.is_attacking`/`is_idle`/`is_moving`) use exactly the Data module's three sets.
    # The Data module is therefore what this layer answers -- see the module header for the table, the
    # live measurement of how often ``0x40`` appears, and the divergence that remains (a caller comparing
    # against GwAu3's *plugin* would differ on ``0x40``, on ``0xC``, and on a velocity-only move).
    "IsAttacking": "IsAttacking",
    "IsIdle": "IsIdle",
    "IsMoving": "IsMoving",
}

#: The columns that exist only in GwAu3's own cache and have no client field behind them.
_CACHE_ONLY_COLUMNS: dict[str, str] = {
    "Ptr": "the agent record's own address, which this layer hands out to nobody",
    "Timer": "the cache row's own timestamp, taken when GwAu3 filled it",
    "IsExploitableCorpse": "a combination of two effect bits that this layer's table does not carry",
    "IsPlayer": "computed from the login number, which is a column this layer does answer",
    "IsNPC": "computed from the login number, which is a column this layer does answer",
}

#: ``{column value: column name}``, read from the generated constants module so the numbers come from
#: GwAu3's own ``Global Enum`` rather than from a transcription of it.
_COLUMNS: dict[int, str] = {
    getattr(_constants, name): name[len("GC_UAI_AGENT_") :]
    for name in _constants.__all__
    if name.startswith("GC_UAI_AGENT_") and name != "GC_UAI_AGENT_COUNT"
}


def _column_key(info_type: Any) -> str:
    """The field-name key for a ``$GC_UAI_AGENT_*`` column, or ``""`` when there is none.

    Two guards, and only one of them refuses now: a column with **no client field behind it** raises
    naming why (six of them, all GwAu3's own per-frame bookkeeping), while the three model-state columns
    the two GwAu3 files disagree about are **answered** from the Data module's definition -- the one
    Reforged Native agrees with (see the module header).
    """

    name = _COLUMNS.get(int(info_type))
    if name is None:
        return ""
    if name in _CACHE_ONLY_COLUMNS:
        raise NotImplementedError(
            f"`$GC_UAI_AGENT_{name}` has no client field behind it: it is {_CACHE_ONLY_COLUMNS[name]} "
            "(`UtilityAI_AgentCache.au3:175-231`). GwAu3 answers it from its own per-frame cache, which "
            "this project does not keep -- and what a caller wants from it is a member of `py4gw/`'s "
            "own classes."
        )
    return _COLUMN_KEYS.get(name, "")


def UAI_GetAgentInfo(agent_id: Any, info_type: Any) -> Any:
    """One cached agent column, by agent id (``UtilityAI_AgentCache.au3:386-390``).

    GwAu3's signature takes a **cache row index** and its by-id sibling resolves the row first; both
    answer the same column of the same agent, so this answers from the agent directly and the two names
    are the same call here. The guard order is kept: a column this layer cannot answer raises naming
    why, and an agent the client does not hold answers ``0``.

    **``Distance`` is answered rather than refused**, and it is the one column in the cache with a live
    twin: GwAu3 fills it as the distance from the agent to the **player** when it fills its cache
    (``UtilityAI_AgentCache.au3:163-165``), and `py4gw/gwa3/uai_get_agent.py`'s ``_cached_distance``
    computes the same number from the same two coordinates at the moment it is asked. That is the
    substitution the strategy generator applies to every transcribed body that reads it, so this
    accessor answers it the same way -- the name means the same question, and the answer is the same
    quantity taken now rather than at a fill moment this project does not have.
    """

    resolved = Agent_ConvertID(agent_id)

    if _COLUMNS.get(int(info_type)) == "Distance":
        from .uai_get_agent import _cached_distance

        return _cached_distance(resolved)

    key = _column_key(info_type)
    if not key:
        return 0
    return Agent_GetAgentInfo(resolved, key)


def UAI_GetAgentInfoByID(agent_id: Any, info_type: Any) -> Any:
    """One cached agent column, by agent id (``UtilityAI_AgentCache.au3:379-383``).

    The plugin's most-used accessor -- `UAI_GetAgentProfession` and every estimation helper in
    `py4gw/gwa3/uai_utils.py` go through it -- and here it is the same call as `UAI_GetAgentInfo`,
    because the row index and the agent id resolve to one agent either way.
    """

    return UAI_GetAgentInfo(agent_id, info_type)


def UAI_GetIndexByID(agent_id: Any) -> int:
    """**REFUSED: a cache row index is GwAu3's own bookkeeping.**

    ``UtilityAI_AgentCache.au3:374-377`` answers the row its own ``$g_m_AgentIDToIndex`` map holds for
    an agent. This project keeps no such map, and the number means nothing outside GwAu3's cache: a
    caller that wants the agent wants the agent, and every other accessor here takes the id directly.
    """

    raise NotImplementedError(
        "UtilityAI_AgentCache.au3:374-377 answers a row in GwAu3's own `$g_amx2_AgentCache`, looked up "
        "through `$g_m_AgentIDToIndex` -- bookkeeping this project does not keep, because it has a "
        "single live source rather than a per-frame copy (`docs/GWA3_COMPAT_SPEC.md`, *Caching*). The "
        "number is only meaningful inside GwAu3's cache; `py4gw/gwa3/uai_agent.py`'s accessors take an "
        "agent id, which is what a caller has."
    )


def UAI_GetAgentCount() -> int:
    """How many agents GwAu3's cache holds (``UtilityAI_AgentCache.au3:401-403``).

    The live equivalent is the agent array this project reads, and that is what is answered: the count
    of ids the client's array holds **now**. GwAu3's count is how many rows the last cache fill wrote,
    which for a plugin running on its own frame loop is the same order of number.
    """

    from ..agent_array import AgentArray

    return len(AgentArray.GetAgentArray())


def UAI_GetPlayerIndex() -> int:
    """**REFUSED: a cache row index.** As `UAI_GetIndexByID`, for the player's own cached row."""

    raise NotImplementedError(
        "UtilityAI_AgentCache.au3 answers the row the controlled character's own cache copy sits in "
        "(`$g_i_PlayerCacheIndex`). This project keeps no per-frame cache and no such row "
        "(`py4gw/gwa3/uai_agent.py` reads the agent directly instead); `UAI_GetPlayerInfo` answers the "
        "player's own columns, which is what a caller wants from the index."
    )


def UAI_GetPlayerInfo(info_type: Any) -> Any:
    """One cached column of the controlled character (``UtilityAI_AgentCache.au3:392-395``).

    GwAu3 reads its ``$g_amx2_PlayerCache`` copy; this reads the controlled character's own agent
    record, which is the agent that copy was filled from. The id comes from the ported
    `Player.GetAgentID`, the same member every other accessor in this layer uses for the controlled
    character.
    """

    from ..player import Player

    return UAI_GetAgentInfo(int(Player.GetAgentID()), info_type)


# `Agent_GetAgentPtr` is imported for the columns that hand back a record rather than a value, which
# the column table above routes through the field names instead. Kept so the import list states what
# the module's own accessor reaches for.
_ = Agent_GetAgentPtr
