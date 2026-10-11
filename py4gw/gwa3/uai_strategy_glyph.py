"""GwAu3's ``UtilityAI_Glyph.au3`` strategy functions, transcribed.

**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_strategies.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

`py4gw/gwa3/uai_best_target_cache.py` and `uai_can_use_cache.py` answer a slot's skill id with the *name*
of one of these functions; GwAu3's engine resolves that name with AutoIt's ``Call``, and this layer
resolves it the same way. So these are the strategy half of the ranking: which agent a skill wants, or
which guard lets it be used at all. **26 of this file's 26 are transcribed and 0
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
from .uai_agent import UAI_GetPlayerInfo


def CanUse_GlyphOfElementalPower() -> Any:
    """``UtilityAI_Glyph.au3:8`` -- transcribed from GwAu3's own body."""

    if Anti_Glyph():
        return False
    return True


def BestTarget_GlyphOfElementalPower(a_f_AggroRange) -> Any:
    """``UtilityAI_Glyph.au3:13`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GlyphOfEnergy() -> Any:
    """``UtilityAI_Glyph.au3:22`` -- transcribed from GwAu3's own body."""

    if Anti_Glyph():
        return False
    return True


def BestTarget_GlyphOfEnergy(a_f_AggroRange) -> Any:
    """``UtilityAI_Glyph.au3:27`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GlyphOfLesserEnergy() -> Any:
    """``UtilityAI_Glyph.au3:36`` -- transcribed from GwAu3's own body."""

    if Anti_Glyph():
        return False
    return True


def BestTarget_GlyphOfLesserEnergy(a_f_AggroRange) -> Any:
    """``UtilityAI_Glyph.au3:41`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GlyphOfConcentration() -> Any:
    """``UtilityAI_Glyph.au3:50`` -- transcribed from GwAu3's own body."""

    if Anti_Glyph():
        return False
    return True


def BestTarget_GlyphOfConcentration(a_f_AggroRange) -> Any:
    """``UtilityAI_Glyph.au3:55`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GlyphOfSacrifice() -> Any:
    """``UtilityAI_Glyph.au3:64`` -- transcribed from GwAu3's own body."""

    if Anti_Glyph():
        return False
    return True


def BestTarget_GlyphOfSacrifice(a_f_AggroRange) -> Any:
    """``UtilityAI_Glyph.au3:69`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GlyphOfRenewal() -> Any:
    """``UtilityAI_Glyph.au3:78`` -- transcribed from GwAu3's own body."""

    if Anti_Glyph():
        return False
    return True


def BestTarget_GlyphOfRenewal(a_f_AggroRange) -> Any:
    """``UtilityAI_Glyph.au3:83`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_HiddenRock() -> Any:
    """``UtilityAI_Glyph.au3:92`` -- transcribed from GwAu3's own body."""

    if Anti_Glyph():
        return False
    return True


def BestTarget_HiddenRock(a_f_AggroRange) -> Any:
    """``UtilityAI_Glyph.au3:97`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GlyphOfEssence() -> Any:
    """``UtilityAI_Glyph.au3:106`` -- transcribed from GwAu3's own body."""

    if Anti_Glyph():
        return False
    return True


def BestTarget_GlyphOfEssence(a_f_AggroRange) -> Any:
    """``UtilityAI_Glyph.au3:111`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GlyphOfRestoration() -> Any:
    """``UtilityAI_Glyph.au3:120`` -- transcribed from GwAu3's own body."""

    if Anti_Glyph():
        return False
    return True


def BestTarget_GlyphOfRestoration(a_f_AggroRange) -> Any:
    """``UtilityAI_Glyph.au3:125`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GlyphOfSwiftness() -> Any:
    """``UtilityAI_Glyph.au3:134`` -- transcribed from GwAu3's own body."""

    if Anti_Glyph():
        return False
    return True


def BestTarget_GlyphOfSwiftness(a_f_AggroRange) -> Any:
    """``UtilityAI_Glyph.au3:139`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GlyphOfImmolation() -> Any:
    """``UtilityAI_Glyph.au3:148`` -- transcribed from GwAu3's own body."""

    if Anti_Glyph():
        return False
    return True


def BestTarget_GlyphOfImmolation(a_f_AggroRange) -> Any:
    """``UtilityAI_Glyph.au3:153`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PolymockGlyphOfConcentration() -> Any:
    """``UtilityAI_Glyph.au3:162`` -- transcribed from GwAu3's own body."""

    if Anti_Glyph():
        return False
    return True


def BestTarget_PolymockGlyphOfConcentration(a_f_AggroRange) -> Any:
    """``UtilityAI_Glyph.au3:167`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PolymockGlyphOfPower() -> Any:
    """``UtilityAI_Glyph.au3:176`` -- transcribed from GwAu3's own body."""

    if Anti_Glyph():
        return False
    return True


def BestTarget_PolymockGlyphOfPower(a_f_AggroRange) -> Any:
    """``UtilityAI_Glyph.au3:181`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


__all__ = [
    "BestTarget_GlyphOfConcentration",
    "BestTarget_GlyphOfElementalPower",
    "BestTarget_GlyphOfEnergy",
    "BestTarget_GlyphOfEssence",
    "BestTarget_GlyphOfImmolation",
    "BestTarget_GlyphOfLesserEnergy",
    "BestTarget_GlyphOfRenewal",
    "BestTarget_GlyphOfRestoration",
    "BestTarget_GlyphOfSacrifice",
    "BestTarget_GlyphOfSwiftness",
    "BestTarget_HiddenRock",
    "BestTarget_PolymockGlyphOfConcentration",
    "BestTarget_PolymockGlyphOfPower",
    "CanUse_GlyphOfConcentration",
    "CanUse_GlyphOfElementalPower",
    "CanUse_GlyphOfEnergy",
    "CanUse_GlyphOfEssence",
    "CanUse_GlyphOfImmolation",
    "CanUse_GlyphOfLesserEnergy",
    "CanUse_GlyphOfRenewal",
    "CanUse_GlyphOfRestoration",
    "CanUse_GlyphOfSacrifice",
    "CanUse_GlyphOfSwiftness",
    "CanUse_HiddenRock",
    "CanUse_PolymockGlyphOfConcentration",
    "CanUse_PolymockGlyphOfPower",
]
