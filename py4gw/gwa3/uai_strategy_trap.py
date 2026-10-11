"""GwAu3's ``UtilityAI_Trap.au3`` strategy functions, transcribed.

**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_strategies.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

`py4gw/gwa3/uai_best_target_cache.py` and `uai_can_use_cache.py` answer a slot's skill id with the *name*
of one of these functions; GwAu3's engine resolves that name with AutoIt's ``Call``, and this layer
resolves it the same way. So these are the strategy half of the ranking: which agent a skill wants, or
which guard lets it be used at all. **34 of this file's 34 are transcribed and 0
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


def CanUse_DustTrap() -> Any:
    """``UtilityAI_Trap.au3:8`` -- transcribed from GwAu3's own body."""

    if Anti_Trap():
        return False
    return True


def BestTarget_DustTrap(a_f_AggroRange) -> Any:
    """``UtilityAI_Trap.au3:13`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BarbedTrap() -> Any:
    """``UtilityAI_Trap.au3:22`` -- transcribed from GwAu3's own body."""

    if Anti_Trap():
        return False
    return True


def BestTarget_BarbedTrap(a_f_AggroRange) -> Any:
    """``UtilityAI_Trap.au3:27`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FlameTrap() -> Any:
    """``UtilityAI_Trap.au3:36`` -- transcribed from GwAu3's own body."""

    if Anti_Trap():
        return False
    return True


def BestTarget_FlameTrap(a_f_AggroRange) -> Any:
    """``UtilityAI_Trap.au3:41`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_HealingSpring() -> Any:
    """``UtilityAI_Trap.au3:50`` -- transcribed from GwAu3's own body."""

    if Anti_Trap():
        return False
    return True


def BestTarget_HealingSpring(a_f_AggroRange) -> Any:
    """``UtilityAI_Trap.au3:55`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SpikeTrap() -> Any:
    """``UtilityAI_Trap.au3:64`` -- transcribed from GwAu3's own body."""

    if Anti_Trap():
        return False
    return True


def BestTarget_SpikeTrap(a_f_AggroRange) -> Any:
    """``UtilityAI_Trap.au3:69`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Snare() -> Any:
    """``UtilityAI_Trap.au3:78`` -- transcribed from GwAu3's own body."""

    if Anti_Trap():
        return False
    return True


def BestTarget_Snare(a_f_AggroRange) -> Any:
    """``UtilityAI_Trap.au3:83`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_VipersNest() -> Any:
    """``UtilityAI_Trap.au3:92`` -- transcribed from GwAu3's own body."""

    if Anti_Trap():
        return False
    return True


def BestTarget_VipersNest(a_f_AggroRange) -> Any:
    """``UtilityAI_Trap.au3:97`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_TwistedSpikes() -> Any:
    """``UtilityAI_Trap.au3:106`` -- transcribed from GwAu3's own body."""

    if Anti_Trap():
        return False
    return True


def BestTarget_TwistedSpikes(a_f_AggroRange) -> Any:
    """``UtilityAI_Trap.au3:111`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MarbleTrap() -> Any:
    """``UtilityAI_Trap.au3:120`` -- transcribed from GwAu3's own body."""

    if Anti_Trap():
        return False
    return True


def BestTarget_MarbleTrap(a_f_AggroRange) -> Any:
    """``UtilityAI_Trap.au3:125`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ShadowTripwire() -> Any:
    """``UtilityAI_Trap.au3:134`` -- transcribed from GwAu3's own body."""

    if Anti_Trap():
        return False
    return True


def BestTarget_ShadowTripwire(a_f_AggroRange) -> Any:
    """``UtilityAI_Trap.au3:139`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Tripwire() -> Any:
    """``UtilityAI_Trap.au3:148`` -- transcribed from GwAu3's own body."""

    if Anti_Trap():
        return False
    return True


def BestTarget_Tripwire(a_f_AggroRange) -> Any:
    """``UtilityAI_Trap.au3:153`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SmokeTrap() -> Any:
    """``UtilityAI_Trap.au3:162`` -- transcribed from GwAu3's own body."""

    if Anti_Trap():
        return False
    return True


def BestTarget_SmokeTrap(a_f_AggroRange) -> Any:
    """``UtilityAI_Trap.au3:167`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PiercingTrap() -> Any:
    """``UtilityAI_Trap.au3:176`` -- transcribed from GwAu3's own body."""

    if Anti_Trap():
        return False
    return True


def BestTarget_PiercingTrap(a_f_AggroRange) -> Any:
    """``UtilityAI_Trap.au3:181`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BlackPowderMine() -> Any:
    """``UtilityAI_Trap.au3:190`` -- transcribed from GwAu3's own body."""

    if Anti_Trap():
        return False
    return True


def BestTarget_BlackPowderMine(a_f_AggroRange) -> Any:
    """``UtilityAI_Trap.au3:195`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_WeaknessTrap() -> Any:
    """``UtilityAI_Trap.au3:204`` -- transcribed from GwAu3's own body."""

    if Anti_Trap():
        return False
    return True


def BestTarget_WeaknessTrap(a_f_AggroRange) -> Any:
    """``UtilityAI_Trap.au3:209`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SpringOfPurity() -> Any:
    """``UtilityAI_Trap.au3:218`` -- transcribed from GwAu3's own body."""

    if Anti_Trap():
        return False
    return True


def BestTarget_SpringOfPurity(a_f_AggroRange) -> Any:
    """``UtilityAI_Trap.au3:223`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_LandMine() -> Any:
    """``UtilityAI_Trap.au3:233`` -- transcribed from GwAu3's own body."""

    if Anti_Trap():
        return False
    return True


def BestTarget_LandMine(a_f_AggroRange) -> Any:
    """``UtilityAI_Trap.au3:238`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


__all__ = [
    "BestTarget_BarbedTrap",
    "BestTarget_BlackPowderMine",
    "BestTarget_DustTrap",
    "BestTarget_FlameTrap",
    "BestTarget_HealingSpring",
    "BestTarget_LandMine",
    "BestTarget_MarbleTrap",
    "BestTarget_PiercingTrap",
    "BestTarget_ShadowTripwire",
    "BestTarget_SmokeTrap",
    "BestTarget_Snare",
    "BestTarget_SpikeTrap",
    "BestTarget_SpringOfPurity",
    "BestTarget_Tripwire",
    "BestTarget_TwistedSpikes",
    "BestTarget_VipersNest",
    "BestTarget_WeaknessTrap",
    "CanUse_BarbedTrap",
    "CanUse_BlackPowderMine",
    "CanUse_DustTrap",
    "CanUse_FlameTrap",
    "CanUse_HealingSpring",
    "CanUse_LandMine",
    "CanUse_MarbleTrap",
    "CanUse_PiercingTrap",
    "CanUse_ShadowTripwire",
    "CanUse_SmokeTrap",
    "CanUse_Snare",
    "CanUse_SpikeTrap",
    "CanUse_SpringOfPurity",
    "CanUse_Tripwire",
    "CanUse_TwistedSpikes",
    "CanUse_VipersNest",
    "CanUse_WeaknessTrap",
]
