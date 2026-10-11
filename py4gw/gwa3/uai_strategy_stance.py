"""GwAu3's ``UtilityAI_Stance.au3`` strategy functions, transcribed.

**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_strategies.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

`py4gw/gwa3/uai_best_target_cache.py` and `uai_can_use_cache.py` answer a slot's skill id with the *name*
of one of these functions; GwAu3's engine resolves that name with AutoIt's ``Call``, and this layer
resolves it the same way. So these are the strategy half of the ranking: which agent a skill wants, or
which guard lets it be used at all. **260 of this file's 260 are transcribed and 0
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
from .uai_effects import UAI_GetFeederEnchOnTop
from .uai_filter import UAI_Filter_IsDazed
from .uai_get_agent import UAI_IsAgentInRange


def CanUse_MantraOfEarth() -> Any:
    """``UtilityAI_Stance.au3:8`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_MantraOfEarth(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:13`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MantraOfFlame() -> Any:
    """``UtilityAI_Stance.au3:22`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_MantraOfFlame(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:27`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MantraOfFrost() -> Any:
    """``UtilityAI_Stance.au3:36`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_MantraOfFrost(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:41`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MantraOfLightning() -> Any:
    """``UtilityAI_Stance.au3:50`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_MantraOfLightning(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:55`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_HexBreaker() -> Any:
    """``UtilityAI_Stance.au3:64`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_HexBreaker(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:69`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Distortion() -> Any:
    """``UtilityAI_Stance.au3:78`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_Distortion(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:83`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MantraOfCelerity() -> Any:
    """``UtilityAI_Stance.au3:92`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_MantraOfCelerity(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:97`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MantraOfRecovery() -> Any:
    """``UtilityAI_Stance.au3:106`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_MantraOfRecovery(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:111`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MantraOfPersistence() -> Any:
    """``UtilityAI_Stance.au3:120`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_MantraOfPersistence(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:125`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MantraOfInscriptions() -> Any:
    """``UtilityAI_Stance.au3:134`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_MantraOfInscriptions(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:139`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MantraOfConcentration() -> Any:
    """``UtilityAI_Stance.au3:148`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_MantraOfConcentration(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:153`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MantraOfResolve() -> Any:
    """``UtilityAI_Stance.au3:162`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_MantraOfResolve(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:167`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MantraOfSignets() -> Any:
    """``UtilityAI_Stance.au3:176`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_MantraOfSignets(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:181`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ElementalResistance() -> Any:
    """``UtilityAI_Stance.au3:190`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_ElementalResistance(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:195`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PhysicalResistance() -> Any:
    """``UtilityAI_Stance.au3:204`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_PhysicalResistance(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:209`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BattleRage() -> Any:
    """``UtilityAI_Stance.au3:218`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_BattleRage(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:223`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Rush() -> Any:
    """``UtilityAI_Stance.au3:232`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_Rush(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:237`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Flurry() -> Any:
    """``UtilityAI_Stance.au3:246`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_Flurry(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:251`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DefensiveStance() -> Any:
    """``UtilityAI_Stance.au3:260`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_DefensiveStance(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:265`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Frenzy() -> Any:
    """``UtilityAI_Stance.au3:274`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_Frenzy(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:279`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Sprint() -> Any:
    """``UtilityAI_Stance.au3:288`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_Sprint(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:293`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BerserkerStance() -> Any:
    """``UtilityAI_Stance.au3:302`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_BerserkerStance(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:307`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BalancedStance() -> Any:
    """``UtilityAI_Stance.au3:316`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_BalancedStance(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:321`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GladiatorsDefense() -> Any:
    """``UtilityAI_Stance.au3:330`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_GladiatorsDefense(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:335`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DeflectArrows() -> Any:
    """``UtilityAI_Stance.au3:340`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_DeflectArrows(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:345`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DwarvenBattleStance() -> Any:
    """``UtilityAI_Stance.au3:354`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_DwarvenBattleStance(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:359`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DisciplinedStance() -> Any:
    """``UtilityAI_Stance.au3:368`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_DisciplinedStance(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:373`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_WaryStance() -> Any:
    """``UtilityAI_Stance.au3:382`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_WaryStance(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:387`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ShieldStance() -> Any:
    """``UtilityAI_Stance.au3:396`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_ShieldStance(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:401`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BullsCharge() -> Any:
    """``UtilityAI_Stance.au3:410`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_BullsCharge(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:415`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BonettisDefense() -> Any:
    """``UtilityAI_Stance.au3:424`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_BonettisDefense(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:429`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Dodge() -> Any:
    """``UtilityAI_Stance.au3:434`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_Dodge(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:439`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Escape() -> Any:
    """``UtilityAI_Stance.au3:448`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_Escape(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:453`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PracticedStance() -> Any:
    """``UtilityAI_Stance.au3:462`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_PracticedStance(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:467`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_WhirlingDefense() -> Any:
    """``UtilityAI_Stance.au3:476`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_WhirlingDefense(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:481`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MelandrusResilience() -> Any:
    """``UtilityAI_Stance.au3:490`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_MelandrusResilience(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:495`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DrydersDefenses() -> Any:
    """``UtilityAI_Stance.au3:500`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_DrydersDefenses(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:505`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_LightningReflexes() -> Any:
    """``UtilityAI_Stance.au3:510`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_LightningReflexes(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:515`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_TigersFury() -> Any:
    """``UtilityAI_Stance.au3:524`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_TigersFury(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:529`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_StormChaser() -> Any:
    """``UtilityAI_Stance.au3:534`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_StormChaser(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:539`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SerpentsQuickness() -> Any:
    """``UtilityAI_Stance.au3:548`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_SerpentsQuickness(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:553`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_JaggedCrystalSkin() -> Any:
    """``UtilityAI_Stance.au3:558`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_JaggedCrystalSkin(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:563`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_EmbraceThePain() -> Any:
    """``UtilityAI_Stance.au3:572`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_EmbraceThePain(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:577`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DeadlyParadox() -> Any:
    """``UtilityAI_Stance.au3:586`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_DeadlyParadox(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:591`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RunAsOne() -> Any:
    """``UtilityAI_Stance.au3:600`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_RunAsOne(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:605`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PrimalRage() -> Any:
    """``UtilityAI_Stance.au3:610`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_PrimalRage(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:615`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ShadowOfHaste() -> Any:
    """``UtilityAI_Stance.au3:624`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_ShadowOfHaste(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:629`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_TigerStance() -> Any:
    """``UtilityAI_Stance.au3:638`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_TigerStance(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:643`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_IceSkates() -> Any:
    """``UtilityAI_Stance.au3:652`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_IceSkates(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:657`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DarkEscape() -> Any:
    """``UtilityAI_Stance.au3:666`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_DarkEscape(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:671`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_UnseenFury() -> Any:
    """``UtilityAI_Stance.au3:680`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_UnseenFury(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:685`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FlashingBlades() -> Any:
    """``UtilityAI_Stance.au3:694`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_FlashingBlades(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:699`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Dash() -> Any:
    """``UtilityAI_Stance.au3:708`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    if not UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_IsMoving):
        return False
    return True


def BestTarget_Dash(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:714`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AuspiciousParry() -> Any:
    """``UtilityAI_Stance.au3:723`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_AuspiciousParry(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:728`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_TurtleShell() -> Any:
    """``UtilityAI_Stance.au3:737`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_TurtleShell(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:742`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RenewingCorruption() -> Any:
    """``UtilityAI_Stance.au3:751`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_RenewingCorruption(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:756`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ZojunsHaste() -> Any:
    """``UtilityAI_Stance.au3:765`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_ZojunsHaste(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:770`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BestialFury() -> Any:
    """``UtilityAI_Stance.au3:775`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_BestialFury(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:780`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FingersOfChaos() -> Any:
    """``UtilityAI_Stance.au3:789`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_FingersOfChaos(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:794`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BattleScars() -> Any:
    """``UtilityAI_Stance.au3:803`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_BattleScars(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:808`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RipostingShadows() -> Any:
    """``UtilityAI_Stance.au3:817`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_RipostingShadows(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:822`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Flail() -> Any:
    """``UtilityAI_Stance.au3:831`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_Flail(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:836`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ChargingStrike() -> Any:
    """``UtilityAI_Stance.au3:845`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_ChargingStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:850`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BurstOfAggression() -> Any:
    """``UtilityAI_Stance.au3:859`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_BurstOfAggression(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:864`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_EnragingCharge() -> Any:
    """``UtilityAI_Stance.au3:873`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_EnragingCharge(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:878`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CorruptedStrength() -> Any:
    """``UtilityAI_Stance.au3:887`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_CorruptedStrength(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:892`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_JununduTunnel() -> Any:
    """``UtilityAI_Stance.au3:901`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    if UAI_IsAgentInRange(-2, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy"):
        return True
    return False


def BestTarget_JununduTunnel(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:909`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_StormsEmbrace() -> Any:
    """``UtilityAI_Stance.au3:916`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_StormsEmbrace(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:921`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_TrappersSpeed() -> Any:
    """``UtilityAI_Stance.au3:926`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_TrappersSpeed(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:931`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PiousConcentration() -> Any:
    """``UtilityAI_Stance.au3:936`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_PiousConcentration(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:941`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PiousHaste() -> Any:
    """``UtilityAI_Stance.au3:950`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_PiousHaste(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:955`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RemoveLeadershipSkill() -> Any:
    """``UtilityAI_Stance.au3:964`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_RemoveLeadershipSkill(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:969`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RemoveQueenArmor() -> Any:
    """``UtilityAI_Stance.au3:974`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_RemoveQueenArmor(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:979`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_QueenArmor() -> Any:
    """``UtilityAI_Stance.au3:984`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_QueenArmor(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:989`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_WayOfTheAssassin() -> Any:
    """``UtilityAI_Stance.au3:998`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_WayOfTheAssassin(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1003`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ShadowWalk() -> Any:
    """``UtilityAI_Stance.au3:1012`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_ShadowWalk(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1017`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SymbolicPosture() -> Any:
    """``UtilityAI_Stance.au3:1026`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_SymbolicPosture(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1031`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SoldiersStance() -> Any:
    """``UtilityAI_Stance.au3:1040`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_SoldiersStance(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1045`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SoldiersDefense() -> Any:
    """``UtilityAI_Stance.au3:1050`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_SoldiersDefense(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1055`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FrenziedDefense() -> Any:
    """``UtilityAI_Stance.au3:1060`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_FrenziedDefense(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1065`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SteadyStance() -> Any:
    """``UtilityAI_Stance.au3:1074`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_SteadyStance(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1079`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ExpertsDexterity() -> Any:
    """``UtilityAI_Stance.au3:1088`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_ExpertsDexterity(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1093`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_NaturalStride() -> Any:
    """``UtilityAI_Stance.au3:1098`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_NaturalStride(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1103`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_HeketsRampage() -> Any:
    """``UtilityAI_Stance.au3:1112`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_HeketsRampage(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1117`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_HeartOfFury() -> Any:
    """``UtilityAI_Stance.au3:1122`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_HeartOfFury(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1127`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_NaturesSpeed() -> Any:
    """``UtilityAI_Stance.au3:1136`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_NaturesSpeed(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1141`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_InfernalRage() -> Any:
    """``UtilityAI_Stance.au3:1146`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_InfernalRage(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1151`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SpiritSenses() -> Any:
    """``UtilityAI_Stance.au3:1160`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_SpiritSenses(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1165`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_VolfenAgilityCurseOfTheNornbear() -> Any:
    """``UtilityAI_Stance.au3:1174`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_VolfenAgilityCurseOfTheNornbear(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1179`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ChargingSpirit() -> Any:
    """``UtilityAI_Stance.au3:1184`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_ChargingSpirit(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1189`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SmokePowderDefense() -> Any:
    """``UtilityAI_Stance.au3:1198`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_SmokePowderDefense(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1203`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PiousFury() -> Any:
    """``UtilityAI_Stance.au3:1212`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    if not UAI_GetFeederEnchOnTop():
        return False
    return True


def BestTarget_PiousFury(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1218`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RavenFlightAGateTooFar() -> Any:
    """``UtilityAI_Stance.au3:1227`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_RavenFlightAGateTooFar(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1232`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RageOfTheJotun() -> Any:
    """``UtilityAI_Stance.au3:1237`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_RageOfTheJotun(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1242`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SoldiersSpeed() -> Any:
    """``UtilityAI_Stance.au3:1247`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_SoldiersSpeed(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1252`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DrunkenMaster() -> Any:
    """``UtilityAI_Stance.au3:1257`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_DrunkenMaster(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1262`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BrawlingBlock() -> Any:
    """``UtilityAI_Stance.au3:1271`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    if UAI_Filter_IsDazed(UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)):
        return False
    return True


def BestTarget_BrawlingBlock(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1277`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_VolfenPounce() -> Any:
    """``UtilityAI_Stance.au3:1286`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_VolfenPounce(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1291`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RavenFlight() -> Any:
    """``UtilityAI_Stance.au3:1300`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_RavenFlight(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1305`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_UrsanForceBloodWashesBlood() -> Any:
    """``UtilityAI_Stance.au3:1314`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_UrsanForceBloodWashesBlood(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1319`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Hyahhhhh1() -> Any:
    """``UtilityAI_Stance.au3:1324`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_Hyahhhhh1(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1329`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Hyahhhhh2() -> Any:
    """``UtilityAI_Stance.au3:1334`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_Hyahhhhh2(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1339`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Hyahhhhh3() -> Any:
    """``UtilityAI_Stance.au3:1344`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_Hyahhhhh3(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1349`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Hyahhhhh4() -> Any:
    """``UtilityAI_Stance.au3:1354`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_Hyahhhhh4(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1359`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GolemBoosters() -> Any:
    """``UtilityAI_Stance.au3:1364`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_GolemBoosters(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1369`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Flee() -> Any:
    """``UtilityAI_Stance.au3:1378`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_Flee(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1383`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DistortionGwen() -> Any:
    """``UtilityAI_Stance.au3:1392`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_DistortionGwen(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1397`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_StrengthOfPurity() -> Any:
    """``UtilityAI_Stance.au3:1402`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_StrengthOfPurity(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1407`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_WayOfThePure() -> Any:
    """``UtilityAI_Stance.au3:1416`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_WayOfThePure(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1421`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MantraOfInscriptionsPvP() -> Any:
    """``UtilityAI_Stance.au3:1430`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_MantraOfInscriptionsPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1435`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_NoxFieldDash() -> Any:
    """``UtilityAI_Stance.au3:1440`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_NoxFieldDash(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1445`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ExpertsDexterityPvP() -> Any:
    """``UtilityAI_Stance.au3:1450`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_ExpertsDexterityPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1455`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_WarriorsEndurancePvP() -> Any:
    """``UtilityAI_Stance.au3:1460`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_WarriorsEndurancePvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1465`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_UnseenFuryPvP() -> Any:
    """``UtilityAI_Stance.au3:1470`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_UnseenFuryPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1475`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ConvictionPvP() -> Any:
    """``UtilityAI_Stance.au3:1480`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_ConvictionPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1485`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_EscapePvP() -> Any:
    """``UtilityAI_Stance.au3:1490`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_EscapePvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1495`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MantraOfResolvePvP() -> Any:
    """``UtilityAI_Stance.au3:1500`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_MantraOfResolvePvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1505`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SugarRushAgentOfTheMadKing() -> Any:
    """``UtilityAI_Stance.au3:1510`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_SugarRushAgentOfTheMadKing(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1515`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_LightningReflexesPvP() -> Any:
    """``UtilityAI_Stance.au3:1520`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_LightningReflexesPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1525`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SoldiersStancePvP() -> Any:
    """``UtilityAI_Stance.au3:1530`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_SoldiersStancePvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1535`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DrunkenStumbling() -> Any:
    """``UtilityAI_Stance.au3:1540`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_DrunkenStumbling(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1545`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MantraOfSignetsPvP() -> Any:
    """``UtilityAI_Stance.au3:1554`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_MantraOfSignetsPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1559`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ToriimosBurningFury() -> Any:
    """``UtilityAI_Stance.au3:1564`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_ToriimosBurningFury(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1569`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DefyPainPvP() -> Any:
    """``UtilityAI_Stance.au3:1574`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_DefyPainPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1579`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_NaturesBlessing() -> Any:
    """``UtilityAI_Stance.au3:1584`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_NaturesBlessing(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1589`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SurvivorsWill() -> Any:
    """``UtilityAI_Stance.au3:1594`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_SurvivorsWill(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1599`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RiotShield() -> Any:
    """``UtilityAI_Stance.au3:1604`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_RiotShield(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1609`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_HeartOfFuryPvP() -> Any:
    """``UtilityAI_Stance.au3:1618`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_HeartOfFuryPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1623`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PiousFuryPvP() -> Any:
    """``UtilityAI_Stance.au3:1628`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_PiousFuryPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1633`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SevenWeaponsStance() -> Any:
    """``UtilityAI_Stance.au3:1638`` -- transcribed from GwAu3's own body."""

    if Anti_Stance():
        return False
    return True


def BestTarget_SevenWeaponsStance(a_f_AggroRange) -> Any:
    """``UtilityAI_Stance.au3:1643`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


__all__ = [
    "BestTarget_AuspiciousParry",
    "BestTarget_BalancedStance",
    "BestTarget_BattleRage",
    "BestTarget_BattleScars",
    "BestTarget_BerserkerStance",
    "BestTarget_BestialFury",
    "BestTarget_BonettisDefense",
    "BestTarget_BrawlingBlock",
    "BestTarget_BullsCharge",
    "BestTarget_BurstOfAggression",
    "BestTarget_ChargingSpirit",
    "BestTarget_ChargingStrike",
    "BestTarget_ConvictionPvP",
    "BestTarget_CorruptedStrength",
    "BestTarget_DarkEscape",
    "BestTarget_Dash",
    "BestTarget_DeadlyParadox",
    "BestTarget_DefensiveStance",
    "BestTarget_DeflectArrows",
    "BestTarget_DefyPainPvP",
    "BestTarget_DisciplinedStance",
    "BestTarget_Distortion",
    "BestTarget_DistortionGwen",
    "BestTarget_Dodge",
    "BestTarget_DrunkenMaster",
    "BestTarget_DrunkenStumbling",
    "BestTarget_DrydersDefenses",
    "BestTarget_DwarvenBattleStance",
    "BestTarget_ElementalResistance",
    "BestTarget_EmbraceThePain",
    "BestTarget_EnragingCharge",
    "BestTarget_Escape",
    "BestTarget_EscapePvP",
    "BestTarget_ExpertsDexterity",
    "BestTarget_ExpertsDexterityPvP",
    "BestTarget_FingersOfChaos",
    "BestTarget_Flail",
    "BestTarget_FlashingBlades",
    "BestTarget_Flee",
    "BestTarget_Flurry",
    "BestTarget_FrenziedDefense",
    "BestTarget_Frenzy",
    "BestTarget_GladiatorsDefense",
    "BestTarget_GolemBoosters",
    "BestTarget_HeartOfFury",
    "BestTarget_HeartOfFuryPvP",
    "BestTarget_HeketsRampage",
    "BestTarget_HexBreaker",
    "BestTarget_Hyahhhhh1",
    "BestTarget_Hyahhhhh2",
    "BestTarget_Hyahhhhh3",
    "BestTarget_Hyahhhhh4",
    "BestTarget_IceSkates",
    "BestTarget_InfernalRage",
    "BestTarget_JaggedCrystalSkin",
    "BestTarget_JununduTunnel",
    "BestTarget_LightningReflexes",
    "BestTarget_LightningReflexesPvP",
    "BestTarget_MantraOfCelerity",
    "BestTarget_MantraOfConcentration",
    "BestTarget_MantraOfEarth",
    "BestTarget_MantraOfFlame",
    "BestTarget_MantraOfFrost",
    "BestTarget_MantraOfInscriptions",
    "BestTarget_MantraOfInscriptionsPvP",
    "BestTarget_MantraOfLightning",
    "BestTarget_MantraOfPersistence",
    "BestTarget_MantraOfRecovery",
    "BestTarget_MantraOfResolve",
    "BestTarget_MantraOfResolvePvP",
    "BestTarget_MantraOfSignets",
    "BestTarget_MantraOfSignetsPvP",
    "BestTarget_MelandrusResilience",
    "BestTarget_NaturalStride",
    "BestTarget_NaturesBlessing",
    "BestTarget_NaturesSpeed",
    "BestTarget_NoxFieldDash",
    "BestTarget_PhysicalResistance",
    "BestTarget_PiousConcentration",
    "BestTarget_PiousFury",
    "BestTarget_PiousFuryPvP",
    "BestTarget_PiousHaste",
    "BestTarget_PracticedStance",
    "BestTarget_PrimalRage",
    "BestTarget_QueenArmor",
    "BestTarget_RageOfTheJotun",
    "BestTarget_RavenFlight",
    "BestTarget_RavenFlightAGateTooFar",
    "BestTarget_RemoveLeadershipSkill",
    "BestTarget_RemoveQueenArmor",
    "BestTarget_RenewingCorruption",
    "BestTarget_RiotShield",
    "BestTarget_RipostingShadows",
    "BestTarget_RunAsOne",
    "BestTarget_Rush",
    "BestTarget_SerpentsQuickness",
    "BestTarget_SevenWeaponsStance",
    "BestTarget_ShadowOfHaste",
    "BestTarget_ShadowWalk",
    "BestTarget_ShieldStance",
    "BestTarget_SmokePowderDefense",
    "BestTarget_SoldiersDefense",
    "BestTarget_SoldiersSpeed",
    "BestTarget_SoldiersStance",
    "BestTarget_SoldiersStancePvP",
    "BestTarget_SpiritSenses",
    "BestTarget_Sprint",
    "BestTarget_SteadyStance",
    "BestTarget_StormChaser",
    "BestTarget_StormsEmbrace",
    "BestTarget_StrengthOfPurity",
    "BestTarget_SugarRushAgentOfTheMadKing",
    "BestTarget_SurvivorsWill",
    "BestTarget_SymbolicPosture",
    "BestTarget_TigerStance",
    "BestTarget_TigersFury",
    "BestTarget_ToriimosBurningFury",
    "BestTarget_TrappersSpeed",
    "BestTarget_TurtleShell",
    "BestTarget_UnseenFury",
    "BestTarget_UnseenFuryPvP",
    "BestTarget_UrsanForceBloodWashesBlood",
    "BestTarget_VolfenAgilityCurseOfTheNornbear",
    "BestTarget_VolfenPounce",
    "BestTarget_WarriorsEndurancePvP",
    "BestTarget_WaryStance",
    "BestTarget_WayOfTheAssassin",
    "BestTarget_WayOfThePure",
    "BestTarget_WhirlingDefense",
    "BestTarget_ZojunsHaste",
    "CanUse_AuspiciousParry",
    "CanUse_BalancedStance",
    "CanUse_BattleRage",
    "CanUse_BattleScars",
    "CanUse_BerserkerStance",
    "CanUse_BestialFury",
    "CanUse_BonettisDefense",
    "CanUse_BrawlingBlock",
    "CanUse_BullsCharge",
    "CanUse_BurstOfAggression",
    "CanUse_ChargingSpirit",
    "CanUse_ChargingStrike",
    "CanUse_ConvictionPvP",
    "CanUse_CorruptedStrength",
    "CanUse_DarkEscape",
    "CanUse_Dash",
    "CanUse_DeadlyParadox",
    "CanUse_DefensiveStance",
    "CanUse_DeflectArrows",
    "CanUse_DefyPainPvP",
    "CanUse_DisciplinedStance",
    "CanUse_Distortion",
    "CanUse_DistortionGwen",
    "CanUse_Dodge",
    "CanUse_DrunkenMaster",
    "CanUse_DrunkenStumbling",
    "CanUse_DrydersDefenses",
    "CanUse_DwarvenBattleStance",
    "CanUse_ElementalResistance",
    "CanUse_EmbraceThePain",
    "CanUse_EnragingCharge",
    "CanUse_Escape",
    "CanUse_EscapePvP",
    "CanUse_ExpertsDexterity",
    "CanUse_ExpertsDexterityPvP",
    "CanUse_FingersOfChaos",
    "CanUse_Flail",
    "CanUse_FlashingBlades",
    "CanUse_Flee",
    "CanUse_Flurry",
    "CanUse_FrenziedDefense",
    "CanUse_Frenzy",
    "CanUse_GladiatorsDefense",
    "CanUse_GolemBoosters",
    "CanUse_HeartOfFury",
    "CanUse_HeartOfFuryPvP",
    "CanUse_HeketsRampage",
    "CanUse_HexBreaker",
    "CanUse_Hyahhhhh1",
    "CanUse_Hyahhhhh2",
    "CanUse_Hyahhhhh3",
    "CanUse_Hyahhhhh4",
    "CanUse_IceSkates",
    "CanUse_InfernalRage",
    "CanUse_JaggedCrystalSkin",
    "CanUse_JununduTunnel",
    "CanUse_LightningReflexes",
    "CanUse_LightningReflexesPvP",
    "CanUse_MantraOfCelerity",
    "CanUse_MantraOfConcentration",
    "CanUse_MantraOfEarth",
    "CanUse_MantraOfFlame",
    "CanUse_MantraOfFrost",
    "CanUse_MantraOfInscriptions",
    "CanUse_MantraOfInscriptionsPvP",
    "CanUse_MantraOfLightning",
    "CanUse_MantraOfPersistence",
    "CanUse_MantraOfRecovery",
    "CanUse_MantraOfResolve",
    "CanUse_MantraOfResolvePvP",
    "CanUse_MantraOfSignets",
    "CanUse_MantraOfSignetsPvP",
    "CanUse_MelandrusResilience",
    "CanUse_NaturalStride",
    "CanUse_NaturesBlessing",
    "CanUse_NaturesSpeed",
    "CanUse_NoxFieldDash",
    "CanUse_PhysicalResistance",
    "CanUse_PiousConcentration",
    "CanUse_PiousFury",
    "CanUse_PiousFuryPvP",
    "CanUse_PiousHaste",
    "CanUse_PracticedStance",
    "CanUse_PrimalRage",
    "CanUse_QueenArmor",
    "CanUse_RageOfTheJotun",
    "CanUse_RavenFlight",
    "CanUse_RavenFlightAGateTooFar",
    "CanUse_RemoveLeadershipSkill",
    "CanUse_RemoveQueenArmor",
    "CanUse_RenewingCorruption",
    "CanUse_RiotShield",
    "CanUse_RipostingShadows",
    "CanUse_RunAsOne",
    "CanUse_Rush",
    "CanUse_SerpentsQuickness",
    "CanUse_SevenWeaponsStance",
    "CanUse_ShadowOfHaste",
    "CanUse_ShadowWalk",
    "CanUse_ShieldStance",
    "CanUse_SmokePowderDefense",
    "CanUse_SoldiersDefense",
    "CanUse_SoldiersSpeed",
    "CanUse_SoldiersStance",
    "CanUse_SoldiersStancePvP",
    "CanUse_SpiritSenses",
    "CanUse_Sprint",
    "CanUse_SteadyStance",
    "CanUse_StormChaser",
    "CanUse_StormsEmbrace",
    "CanUse_StrengthOfPurity",
    "CanUse_SugarRushAgentOfTheMadKing",
    "CanUse_SurvivorsWill",
    "CanUse_SymbolicPosture",
    "CanUse_TigerStance",
    "CanUse_TigersFury",
    "CanUse_ToriimosBurningFury",
    "CanUse_TrappersSpeed",
    "CanUse_TurtleShell",
    "CanUse_UnseenFury",
    "CanUse_UnseenFuryPvP",
    "CanUse_UrsanForceBloodWashesBlood",
    "CanUse_VolfenAgilityCurseOfTheNornbear",
    "CanUse_VolfenPounce",
    "CanUse_WarriorsEndurancePvP",
    "CanUse_WaryStance",
    "CanUse_WayOfTheAssassin",
    "CanUse_WayOfThePure",
    "CanUse_WhirlingDefense",
    "CanUse_ZojunsHaste",
]
