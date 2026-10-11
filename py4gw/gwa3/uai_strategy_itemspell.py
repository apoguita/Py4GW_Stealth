"""GwAu3's ``UtilityAI_ItemSpell.au3`` strategy functions, transcribed.

**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_strategies.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

`py4gw/gwa3/uai_best_target_cache.py` and `uai_can_use_cache.py` answer a slot's skill id with the *name*
of one of these functions; GwAu3's engine resolves that name with AutoIt's ``Call``, and this layer
resolves it the same way. So these are the strategy half of the ranking: which agent a skill wants, or
which guard lets it be used at all. **38 of this file's 38 are transcribed and 0
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


def CanUse_GenerousWasTsungrai() -> Any:
    """``UtilityAI_ItemSpell.au3:24`` -- transcribed from GwAu3's own body."""

    if Anti_ItemSpell():
        return False
    return True


def BestTarget_GenerousWasTsungrai(a_f_AggroRange) -> Any:
    """``UtilityAI_ItemSpell.au3:29`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MightyWasVorizun() -> Any:
    """``UtilityAI_ItemSpell.au3:38`` -- transcribed from GwAu3's own body."""

    if Anti_ItemSpell():
        return False
    return True


def BestTarget_MightyWasVorizun(a_f_AggroRange) -> Any:
    """``UtilityAI_ItemSpell.au3:43`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BlindWasMingson() -> Any:
    """``UtilityAI_ItemSpell.au3:52`` -- transcribed from GwAu3's own body."""

    if Anti_ItemSpell():
        return False
    return True


def BestTarget_BlindWasMingson(a_f_AggroRange) -> Any:
    """``UtilityAI_ItemSpell.au3:57`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GraspingWasKuurong() -> Any:
    """``UtilityAI_ItemSpell.au3:66`` -- transcribed from GwAu3's own body."""

    if Anti_ItemSpell():
        return False
    return True


def BestTarget_GraspingWasKuurong(a_f_AggroRange) -> Any:
    """``UtilityAI_ItemSpell.au3:71`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_VengefulWasKhanhei() -> Any:
    """``UtilityAI_ItemSpell.au3:80`` -- transcribed from GwAu3's own body."""

    if Anti_ItemSpell():
        return False
    return True


def BestTarget_VengefulWasKhanhei(a_f_AggroRange) -> Any:
    """``UtilityAI_ItemSpell.au3:85`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DefiantWasXinrae() -> Any:
    """``UtilityAI_ItemSpell.au3:94`` -- transcribed from GwAu3's own body."""

    if Anti_ItemSpell():
        return False
    return True


def BestTarget_DefiantWasXinrae(a_f_AggroRange) -> Any:
    """``UtilityAI_ItemSpell.au3:99`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_TranquilWasTanasen() -> Any:
    """``UtilityAI_ItemSpell.au3:108`` -- transcribed from GwAu3's own body."""

    if Anti_ItemSpell():
        return False
    return True


def BestTarget_TranquilWasTanasen(a_f_AggroRange) -> Any:
    """``UtilityAI_ItemSpell.au3:113`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CruelWasDaoshen() -> Any:
    """``UtilityAI_ItemSpell.au3:122`` -- transcribed from GwAu3's own body."""

    if Anti_ItemSpell():
        return False
    return True


def BestTarget_CruelWasDaoshen(a_f_AggroRange) -> Any:
    """``UtilityAI_ItemSpell.au3:127`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ProtectiveWasKaolai() -> Any:
    """``UtilityAI_ItemSpell.au3:136`` -- transcribed from GwAu3's own body."""

    if Anti_ItemSpell():
        return False
    return True


def BestTarget_ProtectiveWasKaolai(a_f_AggroRange) -> Any:
    """``UtilityAI_ItemSpell.au3:141`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AttunedWasSongkai() -> Any:
    """``UtilityAI_ItemSpell.au3:150`` -- transcribed from GwAu3's own body."""

    if Anti_ItemSpell():
        return False
    return True


def BestTarget_AttunedWasSongkai(a_f_AggroRange) -> Any:
    """``UtilityAI_ItemSpell.au3:155`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ResilientWasXiko() -> Any:
    """``UtilityAI_ItemSpell.au3:164`` -- transcribed from GwAu3's own body."""

    if Anti_ItemSpell():
        return False
    return True


def BestTarget_ResilientWasXiko(a_f_AggroRange) -> Any:
    """``UtilityAI_ItemSpell.au3:169`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_LivelyWasNaomei() -> Any:
    """``UtilityAI_ItemSpell.au3:178`` -- transcribed from GwAu3's own body."""

    if Anti_ItemSpell():
        return False
    return True


def BestTarget_LivelyWasNaomei(a_f_AggroRange) -> Any:
    """``UtilityAI_ItemSpell.au3:183`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AnguishedWasLingwah() -> Any:
    """``UtilityAI_ItemSpell.au3:192`` -- transcribed from GwAu3's own body."""

    if Anti_ItemSpell():
        return False
    return True


def BestTarget_AnguishedWasLingwah(a_f_AggroRange) -> Any:
    """``UtilityAI_ItemSpell.au3:197`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_VocalWasSogolon() -> Any:
    """``UtilityAI_ItemSpell.au3:206`` -- transcribed from GwAu3's own body."""

    if Anti_ItemSpell():
        return False
    return True


def BestTarget_VocalWasSogolon(a_f_AggroRange) -> Any:
    """``UtilityAI_ItemSpell.au3:211`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DestructiveWasGlaive() -> Any:
    """``UtilityAI_ItemSpell.au3:220`` -- transcribed from GwAu3's own body."""

    if Anti_ItemSpell():
        return False
    return True


def BestTarget_DestructiveWasGlaive(a_f_AggroRange) -> Any:
    """``UtilityAI_ItemSpell.au3:225`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_EnergeticWasLeeSa() -> Any:
    """``UtilityAI_ItemSpell.au3:234`` -- transcribed from GwAu3's own body."""

    if Anti_ItemSpell():
        return False
    return True


def BestTarget_EnergeticWasLeeSa(a_f_AggroRange) -> Any:
    """``UtilityAI_ItemSpell.au3:239`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PureWasLiMing() -> Any:
    """``UtilityAI_ItemSpell.au3:248`` -- transcribed from GwAu3's own body."""

    if Anti_ItemSpell():
        return False
    return True


def BestTarget_PureWasLiMing(a_f_AggroRange) -> Any:
    """``UtilityAI_ItemSpell.au3:253`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CourageousWasSaidra() -> Any:
    """``UtilityAI_ItemSpell.au3:262`` -- transcribed from GwAu3's own body."""

    if Anti_ItemSpell():
        return False
    return True


def BestTarget_CourageousWasSaidra(a_f_AggroRange) -> Any:
    """``UtilityAI_ItemSpell.au3:267`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DestructiveWasGlaivePvP() -> Any:
    """``UtilityAI_ItemSpell.au3:276`` -- transcribed from GwAu3's own body."""

    if Anti_ItemSpell():
        return False
    return True


def BestTarget_DestructiveWasGlaivePvP(a_f_AggroRange) -> Any:
    """``UtilityAI_ItemSpell.au3:281`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


__all__ = [
    "BestTarget_AnguishedWasLingwah",
    "BestTarget_AttunedWasSongkai",
    "BestTarget_BlindWasMingson",
    "BestTarget_CourageousWasSaidra",
    "BestTarget_CruelWasDaoshen",
    "BestTarget_DefiantWasXinrae",
    "BestTarget_DestructiveWasGlaive",
    "BestTarget_DestructiveWasGlaivePvP",
    "BestTarget_EnergeticWasLeeSa",
    "BestTarget_GenerousWasTsungrai",
    "BestTarget_GraspingWasKuurong",
    "BestTarget_LivelyWasNaomei",
    "BestTarget_MightyWasVorizun",
    "BestTarget_ProtectiveWasKaolai",
    "BestTarget_PureWasLiMing",
    "BestTarget_ResilientWasXiko",
    "BestTarget_TranquilWasTanasen",
    "BestTarget_VengefulWasKhanhei",
    "BestTarget_VocalWasSogolon",
    "CanUse_AnguishedWasLingwah",
    "CanUse_AttunedWasSongkai",
    "CanUse_BlindWasMingson",
    "CanUse_CourageousWasSaidra",
    "CanUse_CruelWasDaoshen",
    "CanUse_DefiantWasXinrae",
    "CanUse_DestructiveWasGlaive",
    "CanUse_DestructiveWasGlaivePvP",
    "CanUse_EnergeticWasLeeSa",
    "CanUse_GenerousWasTsungrai",
    "CanUse_GraspingWasKuurong",
    "CanUse_LivelyWasNaomei",
    "CanUse_MightyWasVorizun",
    "CanUse_ProtectiveWasKaolai",
    "CanUse_PureWasLiMing",
    "CanUse_ResilientWasXiko",
    "CanUse_TranquilWasTanasen",
    "CanUse_VengefulWasKhanhei",
    "CanUse_VocalWasSogolon",
]
