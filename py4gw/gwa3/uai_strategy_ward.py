"""GwAu3's ``UtilityAI_Ward.au3`` strategy functions, transcribed.

**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_strategies.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

`py4gw/gwa3/uai_best_target_cache.py` and `uai_can_use_cache.py` answer a slot's skill id with the *name*
of one of these functions; GwAu3's engine resolves that name with AutoIt's ``Call``, and this layer
resolves it the same way. So these are the strategy half of the ranking: which agent a skill wants, or
which guard lets it be used at all. **32 of this file's 32 are transcribed and 0
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
from .uai_get_agent import UAI_MoveToWardPosition


def CanUse_WardAgainstElements() -> Any:
    """``UtilityAI_Ward.au3:24`` -- transcribed from GwAu3's own body."""

    if Anti_Ward():
        return False
    return True


def BestTarget_WardAgainstElements(a_f_AggroRange) -> Any:
    """``UtilityAI_Ward.au3:29`` -- transcribed from GwAu3's own body."""

    if UAI_MoveToWardPosition(_constants.GC_I_RANGE_AREA, _constants.GC_I_UAI_WARDTYPE_DEFENSIVE):
        return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)
    return 0


def CanUse_WardAgainstMelee() -> Any:
    """``UtilityAI_Ward.au3:39`` -- transcribed from GwAu3's own body."""

    if Anti_Ward():
        return False
    return True


def BestTarget_WardAgainstMelee(a_f_AggroRange) -> Any:
    """``UtilityAI_Ward.au3:44`` -- transcribed from GwAu3's own body."""

    if UAI_MoveToWardPosition(_constants.GC_I_RANGE_AREA, _constants.GC_I_UAI_WARDTYPE_DEFENSIVE):
        return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)
    return 0


def CanUse_WardAgainstFoes() -> Any:
    """``UtilityAI_Ward.au3:54`` -- transcribed from GwAu3's own body."""

    if Anti_Ward():
        return False
    return True


def BestTarget_WardAgainstFoes(a_f_AggroRange) -> Any:
    """``UtilityAI_Ward.au3:59`` -- transcribed from GwAu3's own body."""

    if UAI_MoveToWardPosition(_constants.GC_I_RANGE_AREA, _constants.GC_I_UAI_WARDTYPE_OFFENSIVE):
        return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)
    return 0


def CanUse_WardAgainstHarm() -> Any:
    """``UtilityAI_Ward.au3:70`` -- transcribed from GwAu3's own body."""

    if Anti_Ward():
        return False
    return True


def BestTarget_WardAgainstHarm(a_f_AggroRange) -> Any:
    """``UtilityAI_Ward.au3:75`` -- transcribed from GwAu3's own body."""

    if UAI_MoveToWardPosition(_constants.GC_I_RANGE_AREA, _constants.GC_I_UAI_WARDTYPE_DEFENSIVE):
        return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)
    return 0


def CanUse_WardOfStability() -> Any:
    """``UtilityAI_Ward.au3:85`` -- transcribed from GwAu3's own body."""

    if Anti_Ward():
        return False
    return True


def BestTarget_WardOfStability(a_f_AggroRange) -> Any:
    """``UtilityAI_Ward.au3:90`` -- transcribed from GwAu3's own body."""

    if UAI_MoveToWardPosition(_constants.GC_I_RANGE_AREA, _constants.GC_I_UAI_WARDTYPE_DEFENSIVE):
        return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)
    return 0


def CanUse_TeinaisHeat() -> Any:
    """``UtilityAI_Ward.au3:100`` -- transcribed from GwAu3's own body."""

    if Anti_Ward():
        return False
    return True


def BestTarget_TeinaisHeat(a_f_AggroRange) -> Any:
    """``UtilityAI_Ward.au3:105`` -- transcribed from GwAu3's own body."""

    if UAI_MoveToWardPosition(_constants.GC_I_RANGE_AREA, _constants.GC_I_UAI_WARDTYPE_OFFENSIVE):
        return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)
    return 0


def CanUse_WardOfWeakness() -> Any:
    """``UtilityAI_Ward.au3:116`` -- transcribed from GwAu3's own body."""

    if Anti_Ward():
        return False
    return True


def BestTarget_WardOfWeakness(a_f_AggroRange) -> Any:
    """``UtilityAI_Ward.au3:121`` -- transcribed from GwAu3's own body."""

    if UAI_MoveToWardPosition(_constants.GC_I_RANGE_AREA, _constants.GC_I_UAI_WARDTYPE_OFFENSIVE):
        return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)
    return 0


def CanUse_EbonBattleStandardOfCourage() -> Any:
    """``UtilityAI_Ward.au3:132`` -- transcribed from GwAu3's own body."""

    if Anti_Ward():
        return False
    return True


def BestTarget_EbonBattleStandardOfCourage(a_f_AggroRange) -> Any:
    """``UtilityAI_Ward.au3:137`` -- transcribed from GwAu3's own body."""

    if UAI_MoveToWardPosition(_constants.GC_I_RANGE_AREA, _constants.GC_I_UAI_WARDTYPE_DEFENSIVE):
        return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)
    return 0


def CanUse_EbonBattleStandardOfWisdom() -> Any:
    """``UtilityAI_Ward.au3:147`` -- transcribed from GwAu3's own body."""

    if Anti_Ward():
        return False
    return True


def BestTarget_EbonBattleStandardOfWisdom(a_f_AggroRange) -> Any:
    """``UtilityAI_Ward.au3:152`` -- transcribed from GwAu3's own body."""

    if UAI_MoveToWardPosition(_constants.GC_I_RANGE_AREA, _constants.GC_I_UAI_WARDTYPE_DEFENSIVE):
        return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)
    return 0


def CanUse_EbonBattleStandardOfHonor() -> Any:
    """``UtilityAI_Ward.au3:162`` -- transcribed from GwAu3's own body."""

    if Anti_Ward():
        return False
    return True


def BestTarget_EbonBattleStandardOfHonor(a_f_AggroRange) -> Any:
    """``UtilityAI_Ward.au3:167`` -- transcribed from GwAu3's own body."""

    if UAI_MoveToWardPosition(_constants.GC_I_RANGE_AREA, _constants.GC_I_UAI_WARDTYPE_DEFENSIVE):
        return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)
    return 0


def CanUse_RadiationField() -> Any:
    """``UtilityAI_Ward.au3:177`` -- transcribed from GwAu3's own body."""

    if Anti_Ward():
        return False
    return True


def BestTarget_RadiationField(a_f_AggroRange) -> Any:
    """``UtilityAI_Ward.au3:182`` -- transcribed from GwAu3's own body."""

    if UAI_MoveToWardPosition(_constants.GC_I_RANGE_AREA, _constants.GC_I_UAI_WARDTYPE_OFFENSIVE):
        return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)
    return 0


def CanUse_BannerOfTheUnseen() -> Any:
    """``UtilityAI_Ward.au3:193`` -- transcribed from GwAu3's own body."""

    if Anti_Ward():
        return False
    return True


def BestTarget_BannerOfTheUnseen(a_f_AggroRange) -> Any:
    """``UtilityAI_Ward.au3:198`` -- transcribed from GwAu3's own body."""

    if UAI_MoveToWardPosition(_constants.GC_I_RANGE_AREA, _constants.GC_I_UAI_WARDTYPE_DEFENSIVE):
        return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)
    return 0


def CanUse_WardAgainstHarmPvP() -> Any:
    """``UtilityAI_Ward.au3:208`` -- transcribed from GwAu3's own body."""

    if Anti_Ward():
        return False
    return True


def BestTarget_WardAgainstHarmPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Ward.au3:213`` -- transcribed from GwAu3's own body."""

    if UAI_MoveToWardPosition(_constants.GC_I_RANGE_AREA, _constants.GC_I_UAI_WARDTYPE_DEFENSIVE):
        return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)
    return 0


def CanUse_WardAgainstMeleePvP() -> Any:
    """``UtilityAI_Ward.au3:223`` -- transcribed from GwAu3's own body."""

    if Anti_Ward():
        return False
    return True


def BestTarget_WardAgainstMeleePvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Ward.au3:228`` -- transcribed from GwAu3's own body."""

    if UAI_MoveToWardPosition(_constants.GC_I_RANGE_AREA, _constants.GC_I_UAI_WARDTYPE_DEFENSIVE):
        return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)
    return 0


def CanUse_EbonVanguardBattleStandardOfPower() -> Any:
    """``UtilityAI_Ward.au3:238`` -- transcribed from GwAu3's own body."""

    if Anti_Ward():
        return False
    return True


def BestTarget_EbonVanguardBattleStandardOfPower(a_f_AggroRange) -> Any:
    """``UtilityAI_Ward.au3:243`` -- transcribed from GwAu3's own body."""

    if UAI_MoveToWardPosition(_constants.GC_I_RANGE_AREA, _constants.GC_I_UAI_WARDTYPE_DEFENSIVE):
        return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)
    return 0


def CanUse_TimeWard() -> Any:
    """``UtilityAI_Ward.au3:253`` -- transcribed from GwAu3's own body."""

    if Anti_Ward():
        return False
    return True


def BestTarget_TimeWard(a_f_AggroRange) -> Any:
    """``UtilityAI_Ward.au3:258`` -- transcribed from GwAu3's own body."""

    if UAI_MoveToWardPosition(_constants.GC_I_RANGE_AREA, _constants.GC_I_UAI_WARDTYPE_DEFENSIVE):
        return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)
    return 0


__all__ = [
    "BestTarget_BannerOfTheUnseen",
    "BestTarget_EbonBattleStandardOfCourage",
    "BestTarget_EbonBattleStandardOfHonor",
    "BestTarget_EbonBattleStandardOfWisdom",
    "BestTarget_EbonVanguardBattleStandardOfPower",
    "BestTarget_RadiationField",
    "BestTarget_TeinaisHeat",
    "BestTarget_TimeWard",
    "BestTarget_WardAgainstElements",
    "BestTarget_WardAgainstFoes",
    "BestTarget_WardAgainstHarm",
    "BestTarget_WardAgainstHarmPvP",
    "BestTarget_WardAgainstMelee",
    "BestTarget_WardAgainstMeleePvP",
    "BestTarget_WardOfStability",
    "BestTarget_WardOfWeakness",
    "CanUse_BannerOfTheUnseen",
    "CanUse_EbonBattleStandardOfCourage",
    "CanUse_EbonBattleStandardOfHonor",
    "CanUse_EbonBattleStandardOfWisdom",
    "CanUse_EbonVanguardBattleStandardOfPower",
    "CanUse_RadiationField",
    "CanUse_TeinaisHeat",
    "CanUse_TimeWard",
    "CanUse_WardAgainstElements",
    "CanUse_WardAgainstFoes",
    "CanUse_WardAgainstHarm",
    "CanUse_WardAgainstHarmPvP",
    "CanUse_WardAgainstMelee",
    "CanUse_WardAgainstMeleePvP",
    "CanUse_WardOfStability",
    "CanUse_WardOfWeakness",
]
