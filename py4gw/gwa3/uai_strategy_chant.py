"""GwAu3's ``UtilityAI_Chant.au3`` strategy functions, transcribed.

**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_strategies.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

`py4gw/gwa3/uai_best_target_cache.py` and `uai_can_use_cache.py` answer a slot's skill id with the *name*
of one of these functions; GwAu3's engine resolves that name with AutoIt's ``Call``, and this layer
resolves it the same way. So these are the strategy half of the ranking: which agent a skill wants, or
which guard lets it be used at all. **58 of this file's 58 are transcribed and 0
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


def CanUse_AnthemOfFury() -> Any:
    """``UtilityAI_Chant.au3:16`` -- transcribed from GwAu3's own body."""

    if Anti_Chant():
        return False
    return True


def BestTarget_AnthemOfFury(a_f_AggroRange) -> Any:
    """``UtilityAI_Chant.au3:21`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CripplingAnthem() -> Any:
    """``UtilityAI_Chant.au3:29`` -- transcribed from GwAu3's own body."""

    if Anti_Chant():
        return False
    return True


def BestTarget_CripplingAnthem(a_f_AggroRange) -> Any:
    """``UtilityAI_Chant.au3:34`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DefensiveAnthem() -> Any:
    """``UtilityAI_Chant.au3:42`` -- transcribed from GwAu3's own body."""

    if Anti_Chant():
        return False
    return True


def BestTarget_DefensiveAnthem(a_f_AggroRange) -> Any:
    """``UtilityAI_Chant.au3:47`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AnthemOfFlame() -> Any:
    """``UtilityAI_Chant.au3:55`` -- transcribed from GwAu3's own body."""

    if Anti_Chant():
        return False
    return True


def BestTarget_AnthemOfFlame(a_f_AggroRange) -> Any:
    """``UtilityAI_Chant.au3:60`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AnthemOfEnvy() -> Any:
    """``UtilityAI_Chant.au3:68`` -- transcribed from GwAu3's own body."""

    if Anti_Chant():
        return False
    return True


def BestTarget_AnthemOfEnvy(a_f_AggroRange) -> Any:
    """``UtilityAI_Chant.au3:73`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SongOfPower() -> Any:
    """``UtilityAI_Chant.au3:81`` -- transcribed from GwAu3's own body."""

    if Anti_Chant():
        return False
    return True


def BestTarget_SongOfPower(a_f_AggroRange) -> Any:
    """``UtilityAI_Chant.au3:86`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ZealousAnthem() -> Any:
    """``UtilityAI_Chant.au3:94`` -- transcribed from GwAu3's own body."""

    if Anti_Chant():
        return False
    return True


def BestTarget_ZealousAnthem(a_f_AggroRange) -> Any:
    """``UtilityAI_Chant.au3:99`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AriaOfZeal() -> Any:
    """``UtilityAI_Chant.au3:107`` -- transcribed from GwAu3's own body."""

    if Anti_Chant():
        return False
    return True


def BestTarget_AriaOfZeal(a_f_AggroRange) -> Any:
    """``UtilityAI_Chant.au3:112`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_LyricOfZeal() -> Any:
    """``UtilityAI_Chant.au3:120`` -- transcribed from GwAu3's own body."""

    if Anti_Chant():
        return False
    return True


def BestTarget_LyricOfZeal(a_f_AggroRange) -> Any:
    """``UtilityAI_Chant.au3:125`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BalladOfRestoration() -> Any:
    """``UtilityAI_Chant.au3:133`` -- transcribed from GwAu3's own body."""

    if Anti_Chant():
        return False
    return True


def BestTarget_BalladOfRestoration(a_f_AggroRange) -> Any:
    """``UtilityAI_Chant.au3:138`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ChorusOfRestoration() -> Any:
    """``UtilityAI_Chant.au3:146`` -- transcribed from GwAu3's own body."""

    if Anti_Chant():
        return False
    return True


def BestTarget_ChorusOfRestoration(a_f_AggroRange) -> Any:
    """``UtilityAI_Chant.au3:151`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AriaOfRestoration() -> Any:
    """``UtilityAI_Chant.au3:159`` -- transcribed from GwAu3's own body."""

    if Anti_Chant():
        return False
    return True


def BestTarget_AriaOfRestoration(a_f_AggroRange) -> Any:
    """``UtilityAI_Chant.au3:164`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SongOfConcentration() -> Any:
    """``UtilityAI_Chant.au3:172`` -- transcribed from GwAu3's own body."""

    if Anti_Chant():
        return False
    return True


def BestTarget_SongOfConcentration(a_f_AggroRange) -> Any:
    """``UtilityAI_Chant.au3:177`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AnthemOfGuidance() -> Any:
    """``UtilityAI_Chant.au3:185`` -- transcribed from GwAu3's own body."""

    if Anti_Chant():
        return False
    return True


def BestTarget_AnthemOfGuidance(a_f_AggroRange) -> Any:
    """``UtilityAI_Chant.au3:190`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_EnergizingChorus() -> Any:
    """``UtilityAI_Chant.au3:198`` -- transcribed from GwAu3's own body."""

    if Anti_Chant():
        return False
    return True


def BestTarget_EnergizingChorus(a_f_AggroRange) -> Any:
    """``UtilityAI_Chant.au3:203`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SongOfPurification() -> Any:
    """``UtilityAI_Chant.au3:211`` -- transcribed from GwAu3's own body."""

    if Anti_Chant():
        return False
    return True


def BestTarget_SongOfPurification(a_f_AggroRange) -> Any:
    """``UtilityAI_Chant.au3:216`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_HexbreakerAria() -> Any:
    """``UtilityAI_Chant.au3:224`` -- transcribed from GwAu3's own body."""

    if Anti_Chant():
        return False
    return True


def BestTarget_HexbreakerAria(a_f_AggroRange) -> Any:
    """``UtilityAI_Chant.au3:229`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PresenceOfTheSkaleLord() -> Any:
    """``UtilityAI_Chant.au3:237`` -- transcribed from GwAu3's own body."""

    if Anti_Chant():
        return False
    return True


def BestTarget_PresenceOfTheSkaleLord(a_f_AggroRange) -> Any:
    """``UtilityAI_Chant.au3:242`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SongOfRestoration() -> Any:
    """``UtilityAI_Chant.au3:250`` -- transcribed from GwAu3's own body."""

    if Anti_Chant():
        return False
    return True


def BestTarget_SongOfRestoration(a_f_AggroRange) -> Any:
    """``UtilityAI_Chant.au3:255`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_LyricOfPurification() -> Any:
    """``UtilityAI_Chant.au3:263`` -- transcribed from GwAu3's own body."""

    if Anti_Chant():
        return False
    return True


def BestTarget_LyricOfPurification(a_f_AggroRange) -> Any:
    """``UtilityAI_Chant.au3:268`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AnthemOfAggression() -> Any:
    """``UtilityAI_Chant.au3:276`` -- transcribed from GwAu3's own body."""

    if Anti_Chant():
        return False
    return True


def BestTarget_AnthemOfAggression(a_f_AggroRange) -> Any:
    """``UtilityAI_Chant.au3:281`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AnthemOfWeariness() -> Any:
    """``UtilityAI_Chant.au3:289`` -- transcribed from GwAu3's own body."""

    if Anti_Chant():
        return False
    return True


def BestTarget_AnthemOfWeariness(a_f_AggroRange) -> Any:
    """``UtilityAI_Chant.au3:294`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AnthemOfDisruption() -> Any:
    """``UtilityAI_Chant.au3:302`` -- transcribed from GwAu3's own body."""

    if Anti_Chant():
        return False
    return True


def BestTarget_AnthemOfDisruption(a_f_AggroRange) -> Any:
    """``UtilityAI_Chant.au3:307`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AnthemOfPurity() -> Any:
    """``UtilityAI_Chant.au3:315`` -- transcribed from GwAu3's own body."""

    if Anti_Chant():
        return False
    return True


def BestTarget_AnthemOfPurity(a_f_AggroRange) -> Any:
    """``UtilityAI_Chant.au3:320`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DefensiveAnthemPvp() -> Any:
    """``UtilityAI_Chant.au3:328`` -- transcribed from GwAu3's own body."""

    if Anti_Chant():
        return False
    return True


def BestTarget_DefensiveAnthemPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Chant.au3:333`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BalladOfRestorationPvp() -> Any:
    """``UtilityAI_Chant.au3:337`` -- transcribed from GwAu3's own body."""

    if Anti_Chant():
        return False
    return True


def BestTarget_BalladOfRestorationPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Chant.au3:342`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SongOfRestorationPvp() -> Any:
    """``UtilityAI_Chant.au3:346`` -- transcribed from GwAu3's own body."""

    if Anti_Chant():
        return False
    return True


def BestTarget_SongOfRestorationPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Chant.au3:351`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AnthemOfDisruptionPvp() -> Any:
    """``UtilityAI_Chant.au3:355`` -- transcribed from GwAu3's own body."""

    if Anti_Chant():
        return False
    return True


def BestTarget_AnthemOfDisruptionPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Chant.au3:360`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AnthemOfEnvyPvp() -> Any:
    """``UtilityAI_Chant.au3:364`` -- transcribed from GwAu3's own body."""

    if Anti_Chant():
        return False
    return True


def BestTarget_AnthemOfEnvyPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Chant.au3:369`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


__all__ = [
    "BestTarget_AnthemOfAggression",
    "BestTarget_AnthemOfDisruption",
    "BestTarget_AnthemOfDisruptionPvp",
    "BestTarget_AnthemOfEnvy",
    "BestTarget_AnthemOfEnvyPvp",
    "BestTarget_AnthemOfFlame",
    "BestTarget_AnthemOfFury",
    "BestTarget_AnthemOfGuidance",
    "BestTarget_AnthemOfPurity",
    "BestTarget_AnthemOfWeariness",
    "BestTarget_AriaOfRestoration",
    "BestTarget_AriaOfZeal",
    "BestTarget_BalladOfRestoration",
    "BestTarget_BalladOfRestorationPvp",
    "BestTarget_ChorusOfRestoration",
    "BestTarget_CripplingAnthem",
    "BestTarget_DefensiveAnthem",
    "BestTarget_DefensiveAnthemPvp",
    "BestTarget_EnergizingChorus",
    "BestTarget_HexbreakerAria",
    "BestTarget_LyricOfPurification",
    "BestTarget_LyricOfZeal",
    "BestTarget_PresenceOfTheSkaleLord",
    "BestTarget_SongOfConcentration",
    "BestTarget_SongOfPower",
    "BestTarget_SongOfPurification",
    "BestTarget_SongOfRestoration",
    "BestTarget_SongOfRestorationPvp",
    "BestTarget_ZealousAnthem",
    "CanUse_AnthemOfAggression",
    "CanUse_AnthemOfDisruption",
    "CanUse_AnthemOfDisruptionPvp",
    "CanUse_AnthemOfEnvy",
    "CanUse_AnthemOfEnvyPvp",
    "CanUse_AnthemOfFlame",
    "CanUse_AnthemOfFury",
    "CanUse_AnthemOfGuidance",
    "CanUse_AnthemOfPurity",
    "CanUse_AnthemOfWeariness",
    "CanUse_AriaOfRestoration",
    "CanUse_AriaOfZeal",
    "CanUse_BalladOfRestoration",
    "CanUse_BalladOfRestorationPvp",
    "CanUse_ChorusOfRestoration",
    "CanUse_CripplingAnthem",
    "CanUse_DefensiveAnthem",
    "CanUse_DefensiveAnthemPvp",
    "CanUse_EnergizingChorus",
    "CanUse_HexbreakerAria",
    "CanUse_LyricOfPurification",
    "CanUse_LyricOfZeal",
    "CanUse_PresenceOfTheSkaleLord",
    "CanUse_SongOfConcentration",
    "CanUse_SongOfPower",
    "CanUse_SongOfPurification",
    "CanUse_SongOfRestoration",
    "CanUse_SongOfRestorationPvp",
    "CanUse_ZealousAnthem",
]
