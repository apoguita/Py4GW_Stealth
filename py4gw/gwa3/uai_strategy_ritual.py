"""GwAu3's ``UtilityAI_Ritual.au3`` strategy functions, transcribed.

**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_strategies.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

`py4gw/gwa3/uai_best_target_cache.py` and `uai_can_use_cache.py` answer a slot's skill id with the *name*
of one of these functions; GwAu3's engine resolves that name with AutoIt's ``Call``, and this layer
resolves it the same way. So these are the strategy half of the ranking: which agent a skill wants, or
which guard lets it be used at all. **152 of this file's 152 are transcribed and 0
refuse** -- a body the translator cannot read, or one calling a name this layer does not implement,
refuses by name rather than answering a plausible target.

Their callees are this layer's own: ``UAI_GetNearestAgent``, ``UAI_GetAgentLowest``,
``UAI_GetPlayerInfo``, ``UAI_GetBestSingleTarget``, ``UAI_PlayerHasEffect``,
``UAI_GetPlayerEffectInfo``, ``Party_GetPetInfo`` and the ``Anti_*`` predicates in
`py4gw/gwa3/uai_anti.py`.
"""

from __future__ import annotations

import math
from typing import Any

from . import constants as _constants
from . import uai_const
from .uai_agent import UAI_GetAgentInfoByID, UAI_GetPlayerInfo
from .uai_effects import UAI_AgentHasEffect, UAI_GetPlayerEffectInfo, UAI_PlayerHasEffect
from .uai_filter import (
    UAI_Filter_IsLivingAlly,
    UAI_Filter_IsLivingEnemy,
    UAI_Filter_IsMoving,
    UAI_Filter_IsSpirit,
)
from .uai_get_agent import (
    UAI_GetAgentHighest,
    UAI_GetAgentLowest,
    UAI_GetBestSingleTarget,
    UAI_GetFarthestAgent,
    UAI_GetNearestAgent,
)
from .uai_anti import (
    Anti_Attack,
    Anti_Chant,
    Anti_EchoRefrain,
    Anti_Enchantment,
    Anti_Form,
    Anti_Glyph,
    Anti_Hex,
    Anti_ItemSpell,
    Anti_PetAttack,
    Anti_Preparation,
    Anti_Ritual,
    Anti_Shout,
    Anti_Signet,
    Anti_Skill10,
    Anti_Skill16,
    Anti_Spell,
    Anti_Stance,
    Anti_Trap,
    Anti_Ward,
    Anti_WeaponSpell,
    Anti_Well,
)
from .uai_agent import (
    UAI_GetAgentInfoByID,
    UAI_GetPlayerInfo,
)
from .uai_effects import UAI_PlayerHasEffect
from .uai_get_agent import (
    UAI_CountAgents,
    UAI_FindAgentByPlayerNumber,
)


def CanUse_Winter() -> Any:
    """``UtilityAI_Ritual.au3:8`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Winter(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:12`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Winnowing() -> Any:
    """``UtilityAI_Ritual.au3:21`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Winnowing(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:25`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_EdgeOfExtinction() -> Any:
    """``UtilityAI_Ritual.au3:34`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_EdgeOfExtinction(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:38`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GreaterConflagration() -> Any:
    """``UtilityAI_Ritual.au3:47`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_GreaterConflagration(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:51`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Conflagration() -> Any:
    """``UtilityAI_Ritual.au3:60`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Conflagration(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:64`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FertileSeason() -> Any:
    """``UtilityAI_Ritual.au3:73`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_FertileSeason(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:77`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Symbiosis() -> Any:
    """``UtilityAI_Ritual.au3:86`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Symbiosis(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:90`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PrimalEchoes() -> Any:
    """``UtilityAI_Ritual.au3:99`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_PrimalEchoes(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:103`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PredatorySeason() -> Any:
    """``UtilityAI_Ritual.au3:112`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_PredatorySeason(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:116`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FrozenSoil() -> Any:
    """``UtilityAI_Ritual.au3:125`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_FrozenSoil(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:129`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FavorableWinds() -> Any:
    """``UtilityAI_Ritual.au3:138`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_FavorableWinds(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:142`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_HighWinds() -> Any:
    """``UtilityAI_Ritual.au3:151`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_HighWinds(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:155`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_EnergizingWind() -> Any:
    """``UtilityAI_Ritual.au3:164`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_EnergizingWind(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:168`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_QuickeningZephyr() -> Any:
    """``UtilityAI_Ritual.au3:177`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_QuickeningZephyr(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:181`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_NaturesRenewal() -> Any:
    """``UtilityAI_Ritual.au3:190`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_NaturesRenewal(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:194`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MuddyTerrain() -> Any:
    """``UtilityAI_Ritual.au3:199`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_MuddyTerrain(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:203`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Pestilence() -> Any:
    """``UtilityAI_Ritual.au3:212`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Pestilence(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:216`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Shadowsong() -> Any:
    """``UtilityAI_Ritual.au3:225`` -- transcribed from GwAu3's own body."""

    l_i_Spirit = UAI_FindAgentByPlayerNumber(4213, -2, 2500, "UAI_Filter_IsControlledSpirit")
    if l_i_Spirit != 0:
        if UAI_GetAgentInfoByID(l_i_Spirit, _constants.GC_UAI_AGENT_HP) < 0.20:
            return True
        return False

        return True


def BestTarget_Shadowsong(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:236`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Union() -> Any:
    """``UtilityAI_Ritual.au3:245`` -- transcribed from GwAu3's own body."""

    l_i_Spirit = UAI_FindAgentByPlayerNumber(4224, -2, 2500, "UAI_Filter_IsControlledSpirit")
    if l_i_Spirit != 0:
        if UAI_GetAgentInfoByID(l_i_Spirit, _constants.GC_UAI_AGENT_HP) < 0.20:
            return True
        return False

        return True


def BestTarget_Union(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:256`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Destruction() -> Any:
    """``UtilityAI_Ritual.au3:265`` -- transcribed from GwAu3's own body."""

    l_i_Spirit = UAI_FindAgentByPlayerNumber(4215, -2, 2500, "UAI_Filter_IsControlledSpirit")
    if l_i_Spirit != 0:
        return False
    return True


def BestTarget_Destruction(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:273`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Dissonance() -> Any:
    """``UtilityAI_Ritual.au3:282`` -- transcribed from GwAu3's own body."""

    l_i_Spirit = UAI_FindAgentByPlayerNumber(4221, -2, 2500, "UAI_Filter_IsControlledSpirit")
    if l_i_Spirit != 0:
        if UAI_GetAgentInfoByID(l_i_Spirit, _constants.GC_UAI_AGENT_HP) < 0.20:
            return True
        return False

        return True


def BestTarget_Dissonance(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:293`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Disenchantment() -> Any:
    """``UtilityAI_Ritual.au3:302`` -- transcribed from GwAu3's own body."""

    l_i_Spirit = UAI_FindAgentByPlayerNumber(4225, -2, 2500, "UAI_Filter_IsControlledSpirit")
    if l_i_Spirit != 0:
        if UAI_GetAgentInfoByID(l_i_Spirit, _constants.GC_UAI_AGENT_HP) < 0.20:
            return True
        return False

        return True


def BestTarget_Disenchantment(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:313`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Brambles() -> Any:
    """``UtilityAI_Ritual.au3:322`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Brambles(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:326`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Lacerate() -> Any:
    """``UtilityAI_Ritual.au3:335`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Lacerate(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:339`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Restoration() -> Any:
    """``UtilityAI_Ritual.au3:348`` -- transcribed from GwAu3's own body."""

    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_CURSE_OF_DHUUM) or UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_FROZEN_SOIL):
        return False
    l_i_Spirit = UAI_FindAgentByPlayerNumber(4223, -2, 2500, "UAI_Filter_IsControlledSpirit")
    if l_i_Spirit != 0:
        return False
    return True


def BestTarget_Restoration(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:358`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Recuperation() -> Any:
    """``UtilityAI_Ritual.au3:367`` -- transcribed from GwAu3's own body."""

    l_i_Spirit = UAI_FindAgentByPlayerNumber(4220, -2, 2500, "UAI_Filter_IsControlledSpirit")
    if l_i_Spirit != 0:
        if UAI_GetAgentInfoByID(l_i_Spirit, _constants.GC_UAI_AGENT_HP) < 0.20:
            return True
        return False

        return True


def BestTarget_Recuperation(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:378`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Shelter() -> Any:
    """``UtilityAI_Ritual.au3:387`` -- transcribed from GwAu3's own body."""

    l_i_Spirit = UAI_FindAgentByPlayerNumber(4223, -2, 2500, "UAI_Filter_IsControlledSpirit")
    if l_i_Spirit != 0:
        if UAI_GetAgentInfoByID(l_i_Spirit, _constants.GC_UAI_AGENT_HP) < 0.20:
            return True
        return False

        return True


def BestTarget_Shelter(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:398`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Famine() -> Any:
    """``UtilityAI_Ritual.au3:407`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Famine(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:411`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Equinox() -> Any:
    """``UtilityAI_Ritual.au3:420`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Equinox(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:424`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Tranquility() -> Any:
    """``UtilityAI_Ritual.au3:433`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Tranquility(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:437`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Pain() -> Any:
    """``UtilityAI_Ritual.au3:446`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Pain(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:450`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Displacement() -> Any:
    """``UtilityAI_Ritual.au3:459`` -- transcribed from GwAu3's own body."""

    l_i_Spirit = UAI_FindAgentByPlayerNumber(4217, -2, 2500, "UAI_Filter_IsControlledSpirit")
    if l_i_Spirit != 0:
        if UAI_GetAgentInfoByID(l_i_Spirit, _constants.GC_UAI_AGENT_HP) < 0.20:
            return True
        return False

        return True


def BestTarget_Displacement(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:470`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Preservation() -> Any:
    """``UtilityAI_Ritual.au3:479`` -- transcribed from GwAu3's own body."""

    l_i_Spirit = UAI_FindAgentByPlayerNumber(4219, -2, 2500, "UAI_Filter_IsControlledSpirit")
    if l_i_Spirit != 0:
        if UAI_GetAgentInfoByID(l_i_Spirit, _constants.GC_UAI_AGENT_HP) < 0.20:
            return True
        return False

        return True


def BestTarget_Preservation(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:490`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Life() -> Any:
    """``UtilityAI_Ritual.au3:499`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Life(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:503`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Earthbind() -> Any:
    """``UtilityAI_Ritual.au3:512`` -- transcribed from GwAu3's own body."""

    l_i_Spirit = UAI_FindAgentByPlayerNumber(4222, -2, 2500, "UAI_Filter_IsControlledSpirit")
    if l_i_Spirit != 0:
        if UAI_GetAgentInfoByID(l_i_Spirit, _constants.GC_UAI_AGENT_HP) < 0.20:
            return True
        return False

        return True


def BestTarget_Earthbind(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:523`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Bloodsong() -> Any:
    """``UtilityAI_Ritual.au3:532`` -- transcribed from GwAu3's own body."""

    l_i_Spirit = UAI_FindAgentByPlayerNumber(4227, -2, 2500, "UAI_Filter_IsControlledSpirit")
    if l_i_Spirit != 0:
        if UAI_GetAgentInfoByID(l_i_Spirit, _constants.GC_UAI_AGENT_HP) < 0.20:
            return True
        return False

        return True


def BestTarget_Bloodsong(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:543`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Wanderlust() -> Any:
    """``UtilityAI_Ritual.au3:552`` -- transcribed from GwAu3's own body."""

    l_i_Spirit = UAI_FindAgentByPlayerNumber(4228, -2, 2500, "UAI_Filter_IsControlledSpirit")
    if l_i_Spirit != 0:
        if UAI_GetAgentInfoByID(l_i_Spirit, _constants.GC_UAI_AGENT_HP) < 0.20:
            return True
        return False

        return True


def BestTarget_Wanderlust(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:563`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Soothing() -> Any:
    """``UtilityAI_Ritual.au3:572`` -- transcribed from GwAu3's own body."""

    l_i_Spirit = UAI_FindAgentByPlayerNumber(4216, -2, 2500, "UAI_Filter_IsControlledSpirit")
    if l_i_Spirit != 0:
        if UAI_GetAgentInfoByID(l_i_Spirit, _constants.GC_UAI_AGENT_HP) < 0.20:
            return True
        return False

        return True


def BestTarget_Soothing(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:583`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Toxicity() -> Any:
    """``UtilityAI_Ritual.au3:592`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Toxicity(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:596`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Quicksand() -> Any:
    """``UtilityAI_Ritual.au3:605`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Quicksand(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:609`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RoaringWinds() -> Any:
    """``UtilityAI_Ritual.au3:618`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_RoaringWinds(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:622`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_InfuriatingHeat() -> Any:
    """``UtilityAI_Ritual.au3:631`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_InfuriatingHeat(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:635`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GazeOfFury() -> Any:
    """``UtilityAI_Ritual.au3:644`` -- transcribed from GwAu3's own body."""

    l_i_Spirit = UAI_FindAgentByPlayerNumber(5722, -2, 2500, "UAI_Filter_IsControlledSpirit")
    if l_i_Spirit != 0:
        return False
    if UAI_CountAgents(-2, 1250, "UAI_Filter_IsControlledSpirit") == 0:
        return False
    return True


def BestTarget_GazeOfFury(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:654`` -- transcribed from GwAu3's own body."""

    return


def CanUse_Anguish() -> Any:
    """``UtilityAI_Ritual.au3:659`` -- transcribed from GwAu3's own body."""

    l_i_Spirit = UAI_FindAgentByPlayerNumber(5720, -2, 2500, "UAI_Filter_IsControlledSpirit")
    if l_i_Spirit != 0:
        if UAI_GetAgentInfoByID(l_i_Spirit, _constants.GC_UAI_AGENT_HP) < 0.20:
            return True
        return False

        return True


def BestTarget_Anguish(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:670`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Empowerment() -> Any:
    """``UtilityAI_Ritual.au3:679`` -- transcribed from GwAu3's own body."""

    l_i_Spirit = UAI_FindAgentByPlayerNumber(5721, -2, 2500, "UAI_Filter_IsControlledSpirit")
    if l_i_Spirit != 0:
        if UAI_GetAgentInfoByID(l_i_Spirit, _constants.GC_UAI_AGENT_HP) < 0.20:
            return True
        return False

        return True


def BestTarget_Empowerment(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:690`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Recovery() -> Any:
    """``UtilityAI_Ritual.au3:699`` -- transcribed from GwAu3's own body."""

    l_i_Spirit = UAI_FindAgentByPlayerNumber(5719, -2, 2500, "UAI_Filter_IsControlledSpirit")
    if l_i_Spirit != 0:
        if UAI_GetAgentInfoByID(l_i_Spirit, _constants.GC_UAI_AGENT_HP) < 0.20:
            return True
        return False

        return True


def BestTarget_Recovery(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:710`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_JackFrost() -> Any:
    """``UtilityAI_Ritual.au3:719`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_JackFrost(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:723`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Vampirism() -> Any:
    """``UtilityAI_Ritual.au3:732`` -- transcribed from GwAu3's own body."""

    l_i_Spirit = UAI_FindAgentByPlayerNumber(5723, -2, 2500, "UAI_Filter_IsControlledSpirit")
    if l_i_Spirit != 0:
        if UAI_GetAgentInfoByID(l_i_Spirit, _constants.GC_UAI_AGENT_HP) < 0.20:
            return True
        return False

        return True


def BestTarget_Vampirism(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:743`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Rejuvenation() -> Any:
    """``UtilityAI_Ritual.au3:752`` -- transcribed from GwAu3's own body."""

    l_i_Spirit = UAI_FindAgentByPlayerNumber(5853, -2, 2500, "UAI_Filter_IsControlledSpirit")
    if l_i_Spirit != 0:
        if UAI_GetAgentInfoByID(l_i_Spirit, _constants.GC_UAI_AGENT_HP) < 0.20:
            return True
        return False

        return True


def BestTarget_Rejuvenation(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:763`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Agony() -> Any:
    """``UtilityAI_Ritual.au3:772`` -- transcribed from GwAu3's own body."""

    l_i_Spirit = UAI_FindAgentByPlayerNumber(5854, -2, 2500, "UAI_Filter_IsControlledSpirit")
    if l_i_Spirit != 0:
        if UAI_GetAgentInfoByID(l_i_Spirit, _constants.GC_UAI_AGENT_HP) < 0.20:
            return True
        return False

        return True


def BestTarget_Agony(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:783`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Winds() -> Any:
    """``UtilityAI_Ritual.au3:792`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Winds(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:796`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CallToTheSpiritRealm() -> Any:
    """``UtilityAI_Ritual.au3:805`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_CallToTheSpiritRealm(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:809`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DisenchantmentTogo() -> Any:
    """``UtilityAI_Ritual.au3:814`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_DisenchantmentTogo(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:818`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_UnionPvp() -> Any:
    """``UtilityAI_Ritual.au3:823`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_UnionPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:827`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ShadowsongPvp() -> Any:
    """``UtilityAI_Ritual.au3:832`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ShadowsongPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:836`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PainPvp() -> Any:
    """``UtilityAI_Ritual.au3:841`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_PainPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:845`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DestructionPvp() -> Any:
    """``UtilityAI_Ritual.au3:850`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_DestructionPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:854`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SoothingPvp() -> Any:
    """``UtilityAI_Ritual.au3:859`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_SoothingPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:863`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DisplacementPvp() -> Any:
    """``UtilityAI_Ritual.au3:868`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_DisplacementPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:872`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PreservationPvp() -> Any:
    """``UtilityAI_Ritual.au3:877`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_PreservationPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:881`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_LifePvp() -> Any:
    """``UtilityAI_Ritual.au3:886`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_LifePvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:890`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RecuperationPvp() -> Any:
    """``UtilityAI_Ritual.au3:895`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_RecuperationPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:899`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DissonancePvp() -> Any:
    """``UtilityAI_Ritual.au3:904`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_DissonancePvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:908`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_EarthbindPvp() -> Any:
    """``UtilityAI_Ritual.au3:913`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_EarthbindPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:917`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ShelterPvp() -> Any:
    """``UtilityAI_Ritual.au3:922`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ShelterPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:926`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DisenchantmentPvp() -> Any:
    """``UtilityAI_Ritual.au3:931`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_DisenchantmentPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:935`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RestorationPvp() -> Any:
    """``UtilityAI_Ritual.au3:940`` -- transcribed from GwAu3's own body."""

    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_CURSE_OF_DHUUM) or UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_FROZEN_SOIL):
        return False
    return True


def BestTarget_RestorationPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:945`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BloodsongPvp() -> Any:
    """``UtilityAI_Ritual.au3:950`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_BloodsongPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:954`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_WanderlustPvp() -> Any:
    """``UtilityAI_Ritual.au3:959`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_WanderlustPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:963`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GazeOfFuryPvp() -> Any:
    """``UtilityAI_Ritual.au3:968`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_GazeOfFuryPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:972`` -- transcribed from GwAu3's own body."""

    return


def CanUse_AnguishPvp() -> Any:
    """``UtilityAI_Ritual.au3:977`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_AnguishPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:981`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_EmpowermentPvp() -> Any:
    """``UtilityAI_Ritual.au3:986`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_EmpowermentPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:990`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RecoveryPvp() -> Any:
    """``UtilityAI_Ritual.au3:995`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_RecoveryPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:999`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AgonyPvp() -> Any:
    """``UtilityAI_Ritual.au3:1004`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_AgonyPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:1008`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RejuvenationPvp() -> Any:
    """``UtilityAI_Ritual.au3:1013`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_RejuvenationPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:1017`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ShadowsongMasterRiyo() -> Any:
    """``UtilityAI_Ritual.au3:1022`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ShadowsongMasterRiyo(a_f_AggroRange) -> Any:
    """``UtilityAI_Ritual.au3:1026`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


__all__ = [
    "BestTarget_Agony",
    "BestTarget_AgonyPvp",
    "BestTarget_Anguish",
    "BestTarget_AnguishPvp",
    "BestTarget_Bloodsong",
    "BestTarget_BloodsongPvp",
    "BestTarget_Brambles",
    "BestTarget_CallToTheSpiritRealm",
    "BestTarget_Conflagration",
    "BestTarget_Destruction",
    "BestTarget_DestructionPvp",
    "BestTarget_Disenchantment",
    "BestTarget_DisenchantmentPvp",
    "BestTarget_DisenchantmentTogo",
    "BestTarget_Displacement",
    "BestTarget_DisplacementPvp",
    "BestTarget_Dissonance",
    "BestTarget_DissonancePvp",
    "BestTarget_Earthbind",
    "BestTarget_EarthbindPvp",
    "BestTarget_EdgeOfExtinction",
    "BestTarget_Empowerment",
    "BestTarget_EmpowermentPvp",
    "BestTarget_EnergizingWind",
    "BestTarget_Equinox",
    "BestTarget_Famine",
    "BestTarget_FavorableWinds",
    "BestTarget_FertileSeason",
    "BestTarget_FrozenSoil",
    "BestTarget_GazeOfFury",
    "BestTarget_GazeOfFuryPvp",
    "BestTarget_GreaterConflagration",
    "BestTarget_HighWinds",
    "BestTarget_InfuriatingHeat",
    "BestTarget_JackFrost",
    "BestTarget_Lacerate",
    "BestTarget_Life",
    "BestTarget_LifePvp",
    "BestTarget_MuddyTerrain",
    "BestTarget_NaturesRenewal",
    "BestTarget_Pain",
    "BestTarget_PainPvp",
    "BestTarget_Pestilence",
    "BestTarget_PredatorySeason",
    "BestTarget_Preservation",
    "BestTarget_PreservationPvp",
    "BestTarget_PrimalEchoes",
    "BestTarget_QuickeningZephyr",
    "BestTarget_Quicksand",
    "BestTarget_Recovery",
    "BestTarget_RecoveryPvp",
    "BestTarget_Recuperation",
    "BestTarget_RecuperationPvp",
    "BestTarget_Rejuvenation",
    "BestTarget_RejuvenationPvp",
    "BestTarget_Restoration",
    "BestTarget_RestorationPvp",
    "BestTarget_RoaringWinds",
    "BestTarget_Shadowsong",
    "BestTarget_ShadowsongMasterRiyo",
    "BestTarget_ShadowsongPvp",
    "BestTarget_Shelter",
    "BestTarget_ShelterPvp",
    "BestTarget_Soothing",
    "BestTarget_SoothingPvp",
    "BestTarget_Symbiosis",
    "BestTarget_Toxicity",
    "BestTarget_Tranquility",
    "BestTarget_Union",
    "BestTarget_UnionPvp",
    "BestTarget_Vampirism",
    "BestTarget_Wanderlust",
    "BestTarget_WanderlustPvp",
    "BestTarget_Winds",
    "BestTarget_Winnowing",
    "BestTarget_Winter",
    "CanUse_Agony",
    "CanUse_AgonyPvp",
    "CanUse_Anguish",
    "CanUse_AnguishPvp",
    "CanUse_Bloodsong",
    "CanUse_BloodsongPvp",
    "CanUse_Brambles",
    "CanUse_CallToTheSpiritRealm",
    "CanUse_Conflagration",
    "CanUse_Destruction",
    "CanUse_DestructionPvp",
    "CanUse_Disenchantment",
    "CanUse_DisenchantmentPvp",
    "CanUse_DisenchantmentTogo",
    "CanUse_Displacement",
    "CanUse_DisplacementPvp",
    "CanUse_Dissonance",
    "CanUse_DissonancePvp",
    "CanUse_Earthbind",
    "CanUse_EarthbindPvp",
    "CanUse_EdgeOfExtinction",
    "CanUse_Empowerment",
    "CanUse_EmpowermentPvp",
    "CanUse_EnergizingWind",
    "CanUse_Equinox",
    "CanUse_Famine",
    "CanUse_FavorableWinds",
    "CanUse_FertileSeason",
    "CanUse_FrozenSoil",
    "CanUse_GazeOfFury",
    "CanUse_GazeOfFuryPvp",
    "CanUse_GreaterConflagration",
    "CanUse_HighWinds",
    "CanUse_InfuriatingHeat",
    "CanUse_JackFrost",
    "CanUse_Lacerate",
    "CanUse_Life",
    "CanUse_LifePvp",
    "CanUse_MuddyTerrain",
    "CanUse_NaturesRenewal",
    "CanUse_Pain",
    "CanUse_PainPvp",
    "CanUse_Pestilence",
    "CanUse_PredatorySeason",
    "CanUse_Preservation",
    "CanUse_PreservationPvp",
    "CanUse_PrimalEchoes",
    "CanUse_QuickeningZephyr",
    "CanUse_Quicksand",
    "CanUse_Recovery",
    "CanUse_RecoveryPvp",
    "CanUse_Recuperation",
    "CanUse_RecuperationPvp",
    "CanUse_Rejuvenation",
    "CanUse_RejuvenationPvp",
    "CanUse_Restoration",
    "CanUse_RestorationPvp",
    "CanUse_RoaringWinds",
    "CanUse_Shadowsong",
    "CanUse_ShadowsongMasterRiyo",
    "CanUse_ShadowsongPvp",
    "CanUse_Shelter",
    "CanUse_ShelterPvp",
    "CanUse_Soothing",
    "CanUse_SoothingPvp",
    "CanUse_Symbiosis",
    "CanUse_Toxicity",
    "CanUse_Tranquility",
    "CanUse_Union",
    "CanUse_UnionPvp",
    "CanUse_Vampirism",
    "CanUse_Wanderlust",
    "CanUse_WanderlustPvp",
    "CanUse_Winds",
    "CanUse_Winnowing",
    "CanUse_Winter",
]
