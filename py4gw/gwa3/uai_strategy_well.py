"""GwAu3's ``UtilityAI_Well.au3`` strategy functions, transcribed.

**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_strategies.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

`py4gw/gwa3/uai_best_target_cache.py` and `uai_can_use_cache.py` answer a slot's skill id with the *name*
of one of these functions; GwAu3's engine resolves that name with AutoIt's ``Call``, and this layer
resolves it the same way. So these are the strategy half of the ranking: which agent a skill wants, or
which guard lets it be used at all. **16 of this file's 16 are transcribed and 0
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
from .uai_get_agent import (
    UAI_GetBestCorpseForAllySupport,
    UAI_GetBestCorpseForEnemyPressure,
)


def CanUse_WellOfPower() -> Any:
    """``UtilityAI_Well.au3:24`` -- transcribed from GwAu3's own body."""

    if Anti_Well():
        return False
    return True


def BestTarget_WellOfPower(a_f_AggroRange) -> Any:
    """``UtilityAI_Well.au3:29`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestCorpseForAllySupport(a_f_AggroRange)


def CanUse_WellOfBlood() -> Any:
    """``UtilityAI_Well.au3:38`` -- transcribed from GwAu3's own body."""

    if Anti_Well():
        return False
    return True


def BestTarget_WellOfBlood(a_f_AggroRange) -> Any:
    """``UtilityAI_Well.au3:43`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestCorpseForAllySupport(a_f_AggroRange)


def CanUse_WellOfSuffering() -> Any:
    """``UtilityAI_Well.au3:52`` -- transcribed from GwAu3's own body."""

    if Anti_Well():
        return False
    return True


def BestTarget_WellOfSuffering(a_f_AggroRange) -> Any:
    """``UtilityAI_Well.au3:57`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestCorpseForEnemyPressure(a_f_AggroRange)


def CanUse_WellOfTheProfane() -> Any:
    """``UtilityAI_Well.au3:66`` -- transcribed from GwAu3's own body."""

    if Anti_Well():
        return False
    return True


def BestTarget_WellOfTheProfane(a_f_AggroRange) -> Any:
    """``UtilityAI_Well.au3:71`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestCorpseForEnemyPressure(a_f_AggroRange)


def CanUse_WellOfWeariness() -> Any:
    """``UtilityAI_Well.au3:80`` -- transcribed from GwAu3's own body."""

    if Anti_Well():
        return False
    return True


def BestTarget_WellOfWeariness(a_f_AggroRange) -> Any:
    """``UtilityAI_Well.au3:85`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestCorpseForEnemyPressure(a_f_AggroRange)


def CanUse_WellOfDarkness() -> Any:
    """``UtilityAI_Well.au3:94`` -- transcribed from GwAu3's own body."""

    if Anti_Well():
        return False
    return True


def BestTarget_WellOfDarkness(a_f_AggroRange) -> Any:
    """``UtilityAI_Well.au3:99`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestCorpseForEnemyPressure(a_f_AggroRange)


def CanUse_WellOfSilence() -> Any:
    """``UtilityAI_Well.au3:108`` -- transcribed from GwAu3's own body."""

    if Anti_Well():
        return False
    return True


def BestTarget_WellOfSilence(a_f_AggroRange) -> Any:
    """``UtilityAI_Well.au3:113`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestCorpseForEnemyPressure(a_f_AggroRange)


def CanUse_WellOfRuin() -> Any:
    """``UtilityAI_Well.au3:122`` -- transcribed from GwAu3's own body."""

    if Anti_Well():
        return False
    return True


def BestTarget_WellOfRuin(a_f_AggroRange) -> Any:
    """``UtilityAI_Well.au3:127`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestCorpseForEnemyPressure(a_f_AggroRange)


__all__ = [
    "BestTarget_WellOfBlood",
    "BestTarget_WellOfDarkness",
    "BestTarget_WellOfPower",
    "BestTarget_WellOfRuin",
    "BestTarget_WellOfSilence",
    "BestTarget_WellOfSuffering",
    "BestTarget_WellOfTheProfane",
    "BestTarget_WellOfWeariness",
    "CanUse_WellOfBlood",
    "CanUse_WellOfDarkness",
    "CanUse_WellOfPower",
    "CanUse_WellOfRuin",
    "CanUse_WellOfSilence",
    "CanUse_WellOfSuffering",
    "CanUse_WellOfTheProfane",
    "CanUse_WellOfWeariness",
]
