"""GwAu3's ``Anti_*`` predicates: whether a skill of a kind is worth using right now.

**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_strategies.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``).

**What these are, and why they have a module of their own.** ``Anti_Spell`` answers "is a spell worth
casting at this moment"; its siblings ask the same about enchantments, attacks, hexes, stances, shouts,
signets, chants, weapon spells, item spells, preparations, traps, pet attacks, wards, echo/refrains,
glyphs and wells. **1,784 of the 4,572 strategy functions are a single one of these guards** -- the
largest single block in the ranking -- so they are one module, imported by every strategy module, which
also keeps the import graph acyclic.

21 of 21 are transcribed; 0 refuse, with the source line that stopped the translator.
"""

from __future__ import annotations

import math
from typing import Any

from . import constants as _constants
from . import uai_const
from .uai_agent import UAI_GetAgentInfoByID, UAI_GetPlayerInfo
from .uai_effects import (
    UAI_AgentHasEffect,
    UAI_GetPlayerEffectInfo,
    UAI_PlayerHasEffect,
)
from .uai_filter import UAI_Filter_IsLivingAlly, UAI_Filter_IsLivingEnemy, UAI_Filter_IsSpirit
from .uai_get_agent import (
    UAI_GetAgentLowest,
    UAI_GetBestSingleTarget,
    UAI_GetNearestAgent,
)
from .data_agent import Agent_GetAgentInfo
from .data_effect import Effect_GetEffectArg
from .data_party import Party_GetPetInfo
from .uai_agent import (
    UAI_GetAgentInfoByID,
    UAI_GetPlayerInfo,
)
from .uai_effects import (
    UAI_AgentHasVisibleEffect,
    UAI_GetPlayerEffectInfo,
    UAI_PlayerHasEffect,
)
from .uai_filter import UAI_Filter_IsSpirit
from .uai_get_agent import UAI_PlayerHasOtherMesmerHex


def Anti_Attack() -> Any:
    """``UtilityAI_Attack.au3:3`` -- transcribed from GwAu3's own body."""

    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_BLIND):
        return True
    if not UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_IsHexed):
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_SPIRIT_SHACKLES):
        return True
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_INEPTITUDE):
        return True
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_CLUMSINESS):
        return True
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_WANDERING_EYE):
        return True
    l_i_IncomingDamage = 0
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_EMPATHY):
        l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_EMPATHY, _constants.GC_UAI_EFFECT_Scale)
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_SPITEFUL_SPIRIT):
        l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_SPITEFUL_SPIRIT, _constants.GC_UAI_EFFECT_Scale)
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_SPOIL_VICTOR):
        l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_SPOIL_VICTOR, _constants.GC_UAI_EFFECT_Scale)
    return (l_i_IncomingDamage > (UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_CurrentHP) + UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_MaxHP * 0.15)))


def Anti_Chant() -> Any:
    """``UtilityAI_Chant.au3:3`` -- transcribed from GwAu3's own body."""

    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_VOCAL_MINORITY):
        return True
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_WELL_OF_SILENCE):
        return True
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_CACOPHONY) and UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_CACOPHONY, _constants.GC_UAI_EFFECT_Scale) > (UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_CurrentHP) + 50):
        return True

        return False


def Anti_EchoRefrain() -> Any:
    """``UtilityAI_EchoRefrain.au3:3`` -- transcribed from GwAu3's own body."""

    return False


def Anti_Enchantment() -> Any:
    """``UtilityAI_Enchantment.au3:3`` -- transcribed from GwAu3's own body."""

    if not UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_IsHexed):
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_MARK_OF_SUBVERSION):
        return True
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_SHAME):
        return True
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_DIVERSION):
        return True
    l_i_IncomingDamage = 0
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_BACKFIRE):
        l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_BACKFIRE, _constants.GC_UAI_EFFECT_Scale)
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_VISIONS_OF_REGRET):
        l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_VISIONS_OF_REGRET, _constants.GC_UAI_EFFECT_Scale)
        if not UAI_PlayerHasOtherMesmerHex(_constants.GC_I_SKILL_ID_VISIONS_OF_REGRET):
            l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_VISIONS_OF_REGRET, _constants.GC_UAI_EFFECT_BonusScale)

        if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_SOUL_LEECH):
            l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_SOUL_LEECH, _constants.GC_UAI_EFFECT_Scale)
        if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_SPITEFUL_SPIRIT):
            l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_SPITEFUL_SPIRIT, _constants.GC_UAI_EFFECT_Scale)
        if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_SPOIL_VICTOR) and UAI_GetAgentInfoByID(uai_const.g_i_BestTarget, _constants.GC_UAI_AGENT_HP) < UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_HP):
            l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_SPOIL_VICTOR, _constants.GC_UAI_EFFECT_Scale)

            return (l_i_IncomingDamage > (UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_CurrentHP) + UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_MaxHP * 0.15)))


def Anti_Form() -> Any:
    """``UtilityAI_Form.au3:3`` -- transcribed from GwAu3's own body."""

    return False


def Anti_Glyph() -> Any:
    """``UtilityAI_Glyph.au3:3`` -- transcribed from GwAu3's own body."""

    return False


def Anti_Hex() -> Any:
    """``UtilityAI_Hex.au3:3`` -- transcribed from GwAu3's own body."""

    if UAI_Filter_IsSpirit(uai_const.g_i_BestTarget):
        return True
    if not UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_IsHexed):
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_GUILT):
        return True
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_MISTRUST):
        return True
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_DIVERSION):
        return True
    l_i_IncomingDamage = 0
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_BACKFIRE):
        l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_BACKFIRE, _constants.GC_UAI_EFFECT_Scale)
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_VISIONS_OF_REGRET):
        l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_VISIONS_OF_REGRET, _constants.GC_UAI_EFFECT_Scale)
        if not UAI_PlayerHasOtherMesmerHex(_constants.GC_I_SKILL_ID_VISIONS_OF_REGRET):
            l_i_IncomingDamage += Effect_GetEffectArg(_constants.GC_I_SKILL_ID_VISIONS_OF_REGRET, _constants.GC_UAI_EFFECT_BonusScale)

        if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_SOUL_LEECH):
            l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_SOUL_LEECH, _constants.GC_UAI_EFFECT_Scale)
        if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_SPITEFUL_SPIRIT):
            l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_SPITEFUL_SPIRIT, _constants.GC_UAI_EFFECT_Scale)
        if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_SPOIL_VICTOR) and UAI_GetAgentInfoByID(uai_const.g_i_BestTarget, _constants.GC_UAI_AGENT_HP) < UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_HP):
            l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_SPOIL_VICTOR, _constants.GC_UAI_EFFECT_Scale)

            return (l_i_IncomingDamage > (UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_CurrentHP) + UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_MaxHP * 0.15)))


def Anti_ItemSpell() -> Any:
    """``UtilityAI_ItemSpell.au3:3`` -- transcribed from GwAu3's own body."""

    if not UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_IsHexed):
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_DIVERSION):
        return True
    l_i_IncomingDamage = 0
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_BACKFIRE):
        l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_BACKFIRE, _constants.GC_UAI_EFFECT_Scale)
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_VISIONS_OF_REGRET):
        l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_VISIONS_OF_REGRET, _constants.GC_UAI_EFFECT_Scale)
        if not UAI_PlayerHasOtherMesmerHex(_constants.GC_I_SKILL_ID_VISIONS_OF_REGRET):
            l_i_IncomingDamage += Effect_GetEffectArg(_constants.GC_I_SKILL_ID_VISIONS_OF_REGRET, _constants.GC_UAI_EFFECT_BonusScale)

        if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_SOUL_LEECH):
            l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_SOUL_LEECH, _constants.GC_UAI_EFFECT_Scale)
        if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_SPITEFUL_SPIRIT):
            l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_SPITEFUL_SPIRIT, _constants.GC_UAI_EFFECT_Scale)
        return (l_i_IncomingDamage > (UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_CurrentHP) + UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_MaxHP * 0.15)))


def Anti_PetAttack() -> Any:
    """``UtilityAI_PetAttack.au3:3`` -- transcribed from GwAu3's own body."""

    l_i_PetAgentID = Party_GetPetInfo(1, "AgentID")
    if l_i_PetAgentID == 0:
        return True
    l_i_OwnerID = Party_GetPetInfo(1, "OwnerAgentID")
    if l_i_OwnerID != Agent_GetAgentInfo(-2, "ID"):
        return True
    l_f_PetHP = Agent_GetAgentInfo(l_i_PetAgentID, "HP")
    if l_f_PetHP <= 0:
        return True
    return UAI_AgentHasVisibleEffect(l_i_PetAgentID, _constants.GC_I_EFFECT_TYPE_STATUS, _constants.GC_I_EFFECT_ID_BLINDED)


def Anti_Preparation() -> Any:
    """``UtilityAI_Preparation.au3:3`` -- transcribed from GwAu3's own body."""

    return False


def Anti_Ritual() -> Any:
    """``UtilityAI_Ritual.au3:3`` -- transcribed from GwAu3's own body."""

    return False


def Anti_Shout() -> Any:
    """``UtilityAI_Shout.au3:3`` -- transcribed from GwAu3's own body."""

    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_VOCAL_MINORITY):
        return True
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_WELL_OF_SILENCE):
        return True
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_CACOPHONY) and UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_CACOPHONY, _constants.GC_UAI_EFFECT_Scale) > (UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_CurrentHP) + 50):
        return True

        return False


def Anti_Signet() -> Any:
    """``UtilityAI_Signet.au3:4`` -- transcribed from GwAu3's own body."""

    return UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_IGNORANCE)


def Anti_Skill10() -> Any:
    """``UtilityAI_Skill10.au3:3`` -- transcribed from GwAu3's own body."""

    return False


def Anti_Skill16() -> Any:
    """``UtilityAI_Skill16.au3:3`` -- transcribed from GwAu3's own body."""

    return False


def Anti_Spell() -> Any:
    """``UtilityAI_Spell.au3:3`` -- transcribed from GwAu3's own body."""

    if not UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_IsHexed):
        return False
    l_i_TargetAllegiance = UAI_GetAgentInfoByID(uai_const.g_i_BestTarget, _constants.GC_UAI_AGENT_Allegiance)
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_MARK_OF_SUBVERSION) and l_i_TargetAllegiance == _constants.GC_I_ALLEGIANCE_ALLY:
        return True
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_MISTRUST) and l_i_TargetAllegiance == _constants.GC_I_ALLEGIANCE_ALLY:
        return True
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_SHAME) and l_i_TargetAllegiance == _constants.GC_I_ALLEGIANCE_ALLY:
        return True
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_GUILT) and l_i_TargetAllegiance == _constants.GC_I_ALLEGIANCE_ENEMY:
        return True
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_DIVERSION):
        return True
    l_i_IncomingDamage = 0
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_BACKFIRE):
        l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_BACKFIRE, _constants.GC_UAI_EFFECT_Scale)
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_VISIONS_OF_REGRET):
        l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_VISIONS_OF_REGRET, _constants.GC_UAI_EFFECT_Scale)
        if not UAI_PlayerHasOtherMesmerHex(_constants.GC_I_SKILL_ID_VISIONS_OF_REGRET):
            l_i_IncomingDamage += Effect_GetEffectArg(_constants.GC_I_SKILL_ID_VISIONS_OF_REGRET, _constants.GC_UAI_EFFECT_BonusScale)

        if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_SOUL_LEECH):
            l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_SOUL_LEECH, _constants.GC_UAI_EFFECT_Scale)
        if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_SPITEFUL_SPIRIT):
            l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_SPITEFUL_SPIRIT, _constants.GC_UAI_EFFECT_Scale)
        if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_SPOIL_VICTOR) and UAI_GetAgentInfoByID(uai_const.g_i_BestTarget, _constants.GC_UAI_AGENT_HP) < UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_HP):
            l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_SPOIL_VICTOR, _constants.GC_UAI_EFFECT_Scale)

            return (l_i_IncomingDamage > (UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_CurrentHP) + UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_MaxHP * 0.15)))


def Anti_Stance() -> Any:
    """``UtilityAI_Stance.au3:3`` -- transcribed from GwAu3's own body."""

    return False


def Anti_Trap() -> Any:
    """``UtilityAI_Trap.au3:3`` -- transcribed from GwAu3's own body."""

    return False


def Anti_Ward() -> Any:
    """``UtilityAI_Ward.au3:3`` -- transcribed from GwAu3's own body."""

    if not UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_IsHexed):
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_DIVERSION):
        return True
    l_i_IncomingDamage = 0
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_BACKFIRE):
        l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_BACKFIRE, _constants.GC_UAI_EFFECT_Scale)
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_VISIONS_OF_REGRET):
        l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_VISIONS_OF_REGRET, _constants.GC_UAI_EFFECT_Scale)
        if not UAI_PlayerHasOtherMesmerHex(_constants.GC_I_SKILL_ID_VISIONS_OF_REGRET):
            l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_VISIONS_OF_REGRET, _constants.GC_UAI_EFFECT_BonusScale)

        if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_SOUL_LEECH):
            l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_SOUL_LEECH, _constants.GC_UAI_EFFECT_Scale)
        if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_SPITEFUL_SPIRIT):
            l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_SPITEFUL_SPIRIT, _constants.GC_UAI_EFFECT_Scale)
        return (l_i_IncomingDamage > (UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_CurrentHP) + UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_MaxHP * 0.15)))


def Anti_WeaponSpell() -> Any:
    """``UtilityAI_WeaponSpell.au3:3`` -- transcribed from GwAu3's own body."""

    if not UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_IsHexed):
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_MARK_OF_SUBVERSION):
        return True
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_SHAME):
        return True
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_DIVERSION):
        return True
    l_i_IncomingDamage = 0
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_BACKFIRE):
        l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_BACKFIRE, _constants.GC_UAI_EFFECT_Scale)
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_VISIONS_OF_REGRET):
        l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_VISIONS_OF_REGRET, _constants.GC_UAI_EFFECT_Scale)
        if not UAI_PlayerHasOtherMesmerHex(_constants.GC_I_SKILL_ID_VISIONS_OF_REGRET):
            l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_VISIONS_OF_REGRET, _constants.GC_UAI_EFFECT_BonusScale)

        if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_SOUL_LEECH):
            l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_SOUL_LEECH, _constants.GC_UAI_EFFECT_Scale)
        if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_SPITEFUL_SPIRIT):
            l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_SPITEFUL_SPIRIT, _constants.GC_UAI_EFFECT_Scale)
        if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_SPOIL_VICTOR) and UAI_GetAgentInfoByID(uai_const.g_i_BestTarget, _constants.GC_UAI_AGENT_HP) < UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_HP):
            l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_SPOIL_VICTOR, _constants.GC_UAI_EFFECT_Scale)

            return (l_i_IncomingDamage > (UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_CurrentHP) + UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_MaxHP * 0.15)))


def Anti_Well() -> Any:
    """``UtilityAI_Well.au3:3`` -- transcribed from GwAu3's own body."""

    if not UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_IsHexed):
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_DIVERSION):
        return True
    l_i_IncomingDamage = 0
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_BACKFIRE):
        l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_BACKFIRE, _constants.GC_UAI_EFFECT_Scale)
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_VISIONS_OF_REGRET):
        l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_VISIONS_OF_REGRET, _constants.GC_UAI_EFFECT_Scale)
        if not UAI_PlayerHasOtherMesmerHex(_constants.GC_I_SKILL_ID_VISIONS_OF_REGRET):
            l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_VISIONS_OF_REGRET, _constants.GC_UAI_EFFECT_BonusScale)

        if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_SOUL_LEECH):
            l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_SOUL_LEECH, _constants.GC_UAI_EFFECT_Scale)
        if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_SPITEFUL_SPIRIT):
            l_i_IncomingDamage += UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_SPITEFUL_SPIRIT, _constants.GC_UAI_EFFECT_Scale)
        return (l_i_IncomingDamage > (UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_CurrentHP) + UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_MaxHP * 0.15)))


__all__ = [
    "Anti_Attack",
    "Anti_Chant",
    "Anti_EchoRefrain",
    "Anti_Enchantment",
    "Anti_Form",
    "Anti_Glyph",
    "Anti_Hex",
    "Anti_ItemSpell",
    "Anti_PetAttack",
    "Anti_Preparation",
    "Anti_Ritual",
    "Anti_Shout",
    "Anti_Signet",
    "Anti_Skill10",
    "Anti_Skill16",
    "Anti_Spell",
    "Anti_Stance",
    "Anti_Trap",
    "Anti_Ward",
    "Anti_WeaponSpell",
    "Anti_Well",
]
