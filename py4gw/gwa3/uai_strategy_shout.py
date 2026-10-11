"""GwAu3's ``UtilityAI_Shout.au3`` strategy functions, transcribed.

**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_strategies.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

`py4gw/gwa3/uai_best_target_cache.py` and `uai_can_use_cache.py` answer a slot's skill id with the *name*
of one of these functions; GwAu3's engine resolves that name with AutoIt's ``Call``, and this layer
resolves it the same way. So these are the strategy half of the ranking: which agent a skill wants, or
which guard lets it be used at all. **235 of this file's 236 are transcribed and 1
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
from .uai_effects import UAI_PlayerHasEffect
from .uai_get_agent import UAI_GetBestSingleTarget


def CanUse_ToTheLimit() -> Any:
    """``UtilityAI_Shout.au3:16`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_ToTheLimit(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:21`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_IWillAvengeYou() -> Any:
    """``UtilityAI_Shout.au3:25`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_IWillAvengeYou(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:30`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ForGreatJustice() -> Any:
    """``UtilityAI_Shout.au3:38`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_ForGreatJustice(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:43`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_WatchYourself() -> Any:
    """``UtilityAI_Shout.au3:47`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_WatchYourself(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:52`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Charge() -> Any:
    """``UtilityAI_Shout.au3:60`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_Charge(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:65`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_VictoryIsMine() -> Any:
    """``UtilityAI_Shout.au3:73`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_VictoryIsMine(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:78`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FearMe() -> Any:
    """``UtilityAI_Shout.au3:82`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_FearMe(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:87`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ShieldsUp() -> Any:
    """``UtilityAI_Shout.au3:95`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_ShieldsUp(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:100`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_IWillSurvive() -> Any:
    """``UtilityAI_Shout.au3:108`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_IWillSurvive(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:113`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DontBelieveTheirLies() -> Any:
    """``UtilityAI_Shout.au3:121`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_DontBelieveTheirLies(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:126`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CallOfFerocity() -> Any:
    """``UtilityAI_Shout.au3:130`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_CallOfFerocity(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:135`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CallOfProtection() -> Any:
    """``UtilityAI_Shout.au3:143`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_CallOfProtection(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:148`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CallOfElementalProtection() -> Any:
    """``UtilityAI_Shout.au3:156`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_CallOfElementalProtection(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:161`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CallOfVitality() -> Any:
    """``UtilityAI_Shout.au3:169`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_CallOfVitality(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:174`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CallOfHaste() -> Any:
    """``UtilityAI_Shout.au3:182`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_CallOfHaste(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:187`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CallOfHealing() -> Any:
    """``UtilityAI_Shout.au3:195`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_CallOfHealing(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:200`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CallOfResilience() -> Any:
    """``UtilityAI_Shout.au3:208`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_CallOfResilience(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:213`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CallOfFeeding() -> Any:
    """``UtilityAI_Shout.au3:221`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_CallOfFeeding(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:226`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CallOfTheHunter() -> Any:
    """``UtilityAI_Shout.au3:234`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_CallOfTheHunter(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:239`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CallOfBrutality() -> Any:
    """``UtilityAI_Shout.au3:247`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_CallOfBrutality(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:252`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CallOfDisruption() -> Any:
    """``UtilityAI_Shout.au3:260`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_CallOfDisruption(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:265`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SymbioticBond() -> Any:
    """``UtilityAI_Shout.au3:273`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_SymbioticBond(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:278`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_OtyughsCry() -> Any:
    """``UtilityAI_Shout.au3:286`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_OtyughsCry(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:291`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Retreat() -> Any:
    """``UtilityAI_Shout.au3:295`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_Retreat(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:300`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_KilroyStonekin() -> Any:
    """``UtilityAI_Shout.au3:308`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_KilroyStonekin(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:313`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AimTrue() -> Any:
    """``UtilityAI_Shout.au3:321`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_AimTrue(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:326`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Coward() -> Any:
    """``UtilityAI_Shout.au3:330`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_Coward(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:335`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Headshot() -> Any:
    """``UtilityAI_Shout.au3:343`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_Headshot(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:348`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_NoneShallPass() -> Any:
    """``UtilityAI_Shout.au3:352`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_NoneShallPass(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:357`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_OnYourKnees() -> Any:
    """``UtilityAI_Shout.au3:361`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_OnYourKnees(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:366`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RemoveWithHaste() -> Any:
    """``UtilityAI_Shout.au3:370`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_RemoveWithHaste(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:375`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MmmmSnowcone() -> Any:
    """``UtilityAI_Shout.au3:379`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_MmmmSnowcone(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:384`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_LetsGetEm() -> Any:
    """``UtilityAI_Shout.au3:388`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_LetsGetEm(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:393`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_YouWillDie() -> Any:
    """``UtilityAI_Shout.au3:397`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_YouWillDie(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:402`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SongOfTheMists() -> Any:
    """``UtilityAI_Shout.au3:406`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_SongOfTheMists(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:411`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PredatoryBond() -> Any:
    """``UtilityAI_Shout.au3:419`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_PredatoryBond(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:424`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_EchoingBanishment() -> Any:
    """``UtilityAI_Shout.au3:432`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_EchoingBanishment(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:437`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_YoureAllAlone() -> Any:
    """``UtilityAI_Shout.au3:445`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_YoureAllAlone(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:450`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_EnemiesMustDie() -> Any:
    """``UtilityAI_Shout.au3:454`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_EnemiesMustDie(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:459`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_StrikeAsOne() -> Any:
    """``UtilityAI_Shout.au3:463`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_StrikeAsOne(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:468`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Godspeed() -> Any:
    """``UtilityAI_Shout.au3:472`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_Godspeed(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:477`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GoForTheEyes() -> Any:
    """``UtilityAI_Shout.au3:485`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_GoForTheEyes(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:490`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BraceYourself() -> Any:
    """``UtilityAI_Shout.au3:494`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_BraceYourself(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:499`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_StandYourGround() -> Any:
    """``UtilityAI_Shout.au3:507`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_StandYourGround(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:512`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_LeadTheWay() -> Any:
    """``UtilityAI_Shout.au3:516`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_LeadTheWay(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:521`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MakeHaste() -> Any:
    """``UtilityAI_Shout.au3:525`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_MakeHaste(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:530`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_WeShallReturn() -> Any:
    """``UtilityAI_Shout.au3:534`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_CURSE_OF_DHUUM) or UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_FROZEN_SOIL):
        return False
    return True


def BestTarget_WeShallReturn(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:540`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_NeverGiveUp() -> Any:
    """``UtilityAI_Shout.au3:544`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_NeverGiveUp(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:549`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_HelpMe() -> Any:
    """``UtilityAI_Shout.au3:553`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_HelpMe(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:558`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FallBack() -> Any:
    """``UtilityAI_Shout.au3:562`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_FallBack(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:567`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Incoming() -> Any:
    """``UtilityAI_Shout.au3:575`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_Incoming(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:580`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_TheyreOnFire() -> Any:
    """``UtilityAI_Shout.au3:588`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_TheyreOnFire(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:593`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_NeverSurrender() -> Any:
    """``UtilityAI_Shout.au3:597`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_NeverSurrender(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:602`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ItsJustAFleshWound() -> Any:
    """``UtilityAI_Shout.au3:606`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_ItsJustAFleshWound(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:611`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RemoveQueenWail() -> Any:
    """``UtilityAI_Shout.au3:615`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_RemoveQueenWail(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:620`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_QueenWail() -> Any:
    """``UtilityAI_Shout.au3:624`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_QueenWail(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:629`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MakeYourTime() -> Any:
    """``UtilityAI_Shout.au3:637`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_MakeYourTime(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:642`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CantTouchThis() -> Any:
    """``UtilityAI_Shout.au3:650`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_CantTouchThis(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:655`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FindTheirWeakness() -> Any:
    """``UtilityAI_Shout.au3:659`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_FindTheirWeakness(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:664`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ThePowerIsYours() -> Any:
    """``UtilityAI_Shout.au3:668`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_ThePowerIsYours(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:673`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ForgeTheWay() -> Any:
    """``UtilityAI_Shout.au3:681`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_ForgeTheWay(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:686`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SteadyAim() -> Any:
    """``UtilityAI_Shout.au3:690`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_SteadyAim(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:695`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SaveYourselvesLuxon() -> Any:
    """``UtilityAI_Shout.au3:703`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_SaveYourselvesLuxon(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:708`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SaveYourselvesKurzick() -> Any:
    """``UtilityAI_Shout.au3:712`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_SaveYourselvesKurzick(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:717`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_IMeantToDoThat() -> Any:
    """``UtilityAI_Shout.au3:721`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_IMeantToDoThat(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:726`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_TheresNothingToFear() -> Any:
    """``UtilityAI_Shout.au3:730`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_TheresNothingToFear(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:735`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SpiritRoar() -> Any:
    """``UtilityAI_Shout.au3:739`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_SpiritRoar(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:744`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_VolfenBloodlustCurseOfTheNornbear() -> Any:
    """``UtilityAI_Shout.au3:752`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_VolfenBloodlustCurseOfTheNornbear(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:757`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RavenShriekAGateTooFar() -> Any:
    """``UtilityAI_Shout.au3:761`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_RavenShriekAGateTooFar(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:766`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Tremor() -> Any:
    """``UtilityAI_Shout.au3:770`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_Tremor(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:775`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ThunderingRoar() -> Any:
    """``UtilityAI_Shout.au3:783`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_ThunderingRoar(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:788`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DontTrip() -> Any:
    """``UtilityAI_Shout.au3:792`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_DontTrip(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:797`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ByUralsHammer() -> Any:
    """``UtilityAI_Shout.au3:805`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_CURSE_OF_DHUUM) or UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_FROZEN_SOIL):
        return False
    return True


def BestTarget_ByUralsHammer(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:811`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_KraksCharge() -> Any:
    """``UtilityAI_Shout.au3:815`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_KraksCharge(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:820`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_StandUp() -> Any:
    """``UtilityAI_Shout.au3:824`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_StandUp(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:829`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FinishHim() -> Any:
    """``UtilityAI_Shout.au3:833`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_FinishHim(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:838`` -- transcribed from GwAu3's own body."""

    l_i_TargetID = UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsBelow50HP|UAI_Filter_NotIsDeepWounded")
    if l_i_TargetID == 0:
        return UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsBelow50HP")
    return l_i_TargetID


def CanUse_DodgeThis() -> Any:
    """``UtilityAI_Shout.au3:844`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_DODGE_THIS):
        return False
    return True


def BestTarget_DodgeThis(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:850`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_IAmTheStrongest() -> Any:
    """``UtilityAI_Shout.au3:858`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_I_AM_THE_STRONGEST):
        return False
    return True


def BestTarget_IAmTheStrongest(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:864`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_IAmUnstoppable() -> Any:
    """``UtilityAI_Shout.au3:872`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    if UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_IsCrippled) or UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_IsKnockedDown):
        return True
    if UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_HP) >= 0.95:
        return False
    return True


def BestTarget_IAmUnstoppable(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:879`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_YouMoveLikeADwarf() -> Any:
    """``UtilityAI_Shout.au3:887`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_YouMoveLikeADwarf(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:892`` -- transcribed from GwAu3's own body."""

    l_f_Range = (_constants.GC_I_RANGE_SPELLCASTING if a_f_AggroRange > _constants.GC_I_RANGE_SPELLCASTING else a_f_AggroRange)
    l_i_Target = UAI_GetBestSingleTarget(-2, l_f_Range, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsMonk")
    if l_i_Target != 0:
        return l_i_Target
    l_i_Target = UAI_GetBestSingleTarget(-2, l_f_Range, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")
    if l_i_Target != 0:
        return l_i_Target
    l_i_Target = UAI_GetBestSingleTarget(-2, l_f_Range, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsMelee")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetBestSingleTarget(-2, l_f_Range, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_YouAreAllWeaklings() -> Any:
    """``UtilityAI_Shout.au3:915`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_YouAreAllWeaklings(a_f_AggroRange) -> Any:
    """**REFUSED: this body is not transcribed.**

    ``UtilityAI_Shout.au3:920`` -- calls a name this layer does not implement. The body is

    .. code-block:: text

        SetExtended

    A strategy is the source's content -- which agent a skill wants, under which guard -- so
    it is transcribed or refused, never re-derived. The line above is what stopped this one,
    and it is this function's work item.
    """

    raise NotImplementedError(
        "`BestTarget_YouAreAllWeaklings` (`UtilityAI_Shout.au3:920`) has a body this layer does not port: "
        "calls a name this layer does not implement: SetExtended"
    )


def CanUse_UrsanRoar() -> Any:
    """``UtilityAI_Shout.au3:933`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_UrsanRoar(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:938`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_VolfenBloodlust() -> Any:
    """``UtilityAI_Shout.au3:946`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_VolfenBloodlust(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:951`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RavenShriek() -> Any:
    """``UtilityAI_Shout.au3:959`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_RavenShriek(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:964`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_UrsanRoarBloodWashesBlood() -> Any:
    """``UtilityAI_Shout.au3:972`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_UrsanRoarBloodWashesBlood(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:977`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DestroyTheHumans() -> Any:
    """``UtilityAI_Shout.au3:981`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_DestroyTheHumans(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:986`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_TengusMimicry() -> Any:
    """``UtilityAI_Shout.au3:990`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_TengusMimicry(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:995`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CallOfHastePvp() -> Any:
    """``UtilityAI_Shout.au3:999`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_CallOfHastePvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:1004`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FormUpAndAdvance() -> Any:
    """``UtilityAI_Shout.au3:1008`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_FormUpAndAdvance(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:1013`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Advance() -> Any:
    """``UtilityAI_Shout.au3:1017`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_Advance(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:1022`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ForElona() -> Any:
    """``UtilityAI_Shout.au3:1026`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_ForElona(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:1031`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CryOfMadness() -> Any:
    """``UtilityAI_Shout.au3:1035`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_CryOfMadness(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:1040`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MotivatingInsults() -> Any:
    """``UtilityAI_Shout.au3:1048`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_MotivatingInsults(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:1053`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ItsGoodToBeKing() -> Any:
    """``UtilityAI_Shout.au3:1061`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_ItsGoodToBeKing(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:1066`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MaddeningLaughter() -> Any:
    """``UtilityAI_Shout.au3:1070`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_MaddeningLaughter(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:1075`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_WatchYourselfPvp() -> Any:
    """``UtilityAI_Shout.au3:1083`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_WatchYourselfPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:1088`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_IncomingPvp() -> Any:
    """``UtilityAI_Shout.au3:1092`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_IncomingPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:1097`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_NeverSurrenderPvp() -> Any:
    """``UtilityAI_Shout.au3:1101`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_NeverSurrenderPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:1106`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ForGreatJusticePvp() -> Any:
    """``UtilityAI_Shout.au3:1110`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_ForGreatJusticePvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:1115`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GoForTheEyesPvp() -> Any:
    """``UtilityAI_Shout.au3:1119`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_GoForTheEyesPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:1124`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BraceYourselfPvp() -> Any:
    """``UtilityAI_Shout.au3:1128`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_BraceYourselfPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:1133`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CantTouchThisPvp() -> Any:
    """``UtilityAI_Shout.au3:1137`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_CantTouchThisPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:1142`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_StandYourGroundPvp() -> Any:
    """``UtilityAI_Shout.au3:1146`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_StandYourGroundPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:1151`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_WeShallReturnPvp() -> Any:
    """``UtilityAI_Shout.au3:1155`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_CURSE_OF_DHUUM) or UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_FROZEN_SOIL):
        return False
    return True


def BestTarget_WeShallReturnPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:1161`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FindTheirWeaknessPvp() -> Any:
    """``UtilityAI_Shout.au3:1165`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_FindTheirWeaknessPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:1170`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_NeverGiveUpPvp() -> Any:
    """``UtilityAI_Shout.au3:1174`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_NeverGiveUpPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:1179`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_HelpMePvp() -> Any:
    """``UtilityAI_Shout.au3:1183`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_HelpMePvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:1188`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FallBackPvp() -> Any:
    """``UtilityAI_Shout.au3:1192`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_FallBackPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:1197`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PredatoryBondPvp() -> Any:
    """``UtilityAI_Shout.au3:1201`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_PredatoryBondPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:1206`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_StickyGround() -> Any:
    """``UtilityAI_Shout.au3:1210`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_StickyGround(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:1215`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SugarShock() -> Any:
    """``UtilityAI_Shout.au3:1223`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_SugarShock(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:1228`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_TheMadKingsInfluence() -> Any:
    """``UtilityAI_Shout.au3:1236`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_TheMadKingsInfluence(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:1241`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_TheresNotEnoughTime() -> Any:
    """``UtilityAI_Shout.au3:1245`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_TheresNotEnoughTime(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:1250`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FindTheirWeaknessThackeray() -> Any:
    """``UtilityAI_Shout.au3:1254`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_FindTheirWeaknessThackeray(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:1259`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_TheresNothingToFearThackeray() -> Any:
    """``UtilityAI_Shout.au3:1263`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_TheresNothingToFearThackeray(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:1268`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_TangoDown() -> Any:
    """``UtilityAI_Shout.au3:1272`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_TangoDown(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:1277`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_IllBeBack() -> Any:
    """``UtilityAI_Shout.au3:1281`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_IllBeBack(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:1286`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_TogetherAsOne() -> Any:
    """``UtilityAI_Shout.au3:1290`` -- transcribed from GwAu3's own body."""

    if Anti_Shout():
        return False
    return True


def BestTarget_TogetherAsOne(a_f_AggroRange) -> Any:
    """``UtilityAI_Shout.au3:1295`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


__all__ = [
    "BestTarget_Advance",
    "BestTarget_AimTrue",
    "BestTarget_BraceYourself",
    "BestTarget_BraceYourselfPvp",
    "BestTarget_ByUralsHammer",
    "BestTarget_CallOfBrutality",
    "BestTarget_CallOfDisruption",
    "BestTarget_CallOfElementalProtection",
    "BestTarget_CallOfFeeding",
    "BestTarget_CallOfFerocity",
    "BestTarget_CallOfHaste",
    "BestTarget_CallOfHastePvp",
    "BestTarget_CallOfHealing",
    "BestTarget_CallOfProtection",
    "BestTarget_CallOfResilience",
    "BestTarget_CallOfTheHunter",
    "BestTarget_CallOfVitality",
    "BestTarget_CantTouchThis",
    "BestTarget_CantTouchThisPvp",
    "BestTarget_Charge",
    "BestTarget_Coward",
    "BestTarget_CryOfMadness",
    "BestTarget_DestroyTheHumans",
    "BestTarget_DodgeThis",
    "BestTarget_DontBelieveTheirLies",
    "BestTarget_DontTrip",
    "BestTarget_EchoingBanishment",
    "BestTarget_EnemiesMustDie",
    "BestTarget_FallBack",
    "BestTarget_FallBackPvp",
    "BestTarget_FearMe",
    "BestTarget_FindTheirWeakness",
    "BestTarget_FindTheirWeaknessPvp",
    "BestTarget_FindTheirWeaknessThackeray",
    "BestTarget_FinishHim",
    "BestTarget_ForElona",
    "BestTarget_ForGreatJustice",
    "BestTarget_ForGreatJusticePvp",
    "BestTarget_ForgeTheWay",
    "BestTarget_FormUpAndAdvance",
    "BestTarget_GoForTheEyes",
    "BestTarget_GoForTheEyesPvp",
    "BestTarget_Godspeed",
    "BestTarget_Headshot",
    "BestTarget_HelpMe",
    "BestTarget_HelpMePvp",
    "BestTarget_IAmTheStrongest",
    "BestTarget_IAmUnstoppable",
    "BestTarget_IMeantToDoThat",
    "BestTarget_IWillAvengeYou",
    "BestTarget_IWillSurvive",
    "BestTarget_IllBeBack",
    "BestTarget_Incoming",
    "BestTarget_IncomingPvp",
    "BestTarget_ItsGoodToBeKing",
    "BestTarget_ItsJustAFleshWound",
    "BestTarget_KilroyStonekin",
    "BestTarget_KraksCharge",
    "BestTarget_LeadTheWay",
    "BestTarget_LetsGetEm",
    "BestTarget_MaddeningLaughter",
    "BestTarget_MakeHaste",
    "BestTarget_MakeYourTime",
    "BestTarget_MmmmSnowcone",
    "BestTarget_MotivatingInsults",
    "BestTarget_NeverGiveUp",
    "BestTarget_NeverGiveUpPvp",
    "BestTarget_NeverSurrender",
    "BestTarget_NeverSurrenderPvp",
    "BestTarget_NoneShallPass",
    "BestTarget_OnYourKnees",
    "BestTarget_OtyughsCry",
    "BestTarget_PredatoryBond",
    "BestTarget_PredatoryBondPvp",
    "BestTarget_QueenWail",
    "BestTarget_RavenShriek",
    "BestTarget_RavenShriekAGateTooFar",
    "BestTarget_RemoveQueenWail",
    "BestTarget_RemoveWithHaste",
    "BestTarget_Retreat",
    "BestTarget_SaveYourselvesKurzick",
    "BestTarget_SaveYourselvesLuxon",
    "BestTarget_ShieldsUp",
    "BestTarget_SongOfTheMists",
    "BestTarget_SpiritRoar",
    "BestTarget_StandUp",
    "BestTarget_StandYourGround",
    "BestTarget_StandYourGroundPvp",
    "BestTarget_SteadyAim",
    "BestTarget_StickyGround",
    "BestTarget_StrikeAsOne",
    "BestTarget_SugarShock",
    "BestTarget_SymbioticBond",
    "BestTarget_TangoDown",
    "BestTarget_TengusMimicry",
    "BestTarget_TheMadKingsInfluence",
    "BestTarget_ThePowerIsYours",
    "BestTarget_TheresNotEnoughTime",
    "BestTarget_TheresNothingToFear",
    "BestTarget_TheresNothingToFearThackeray",
    "BestTarget_TheyreOnFire",
    "BestTarget_ThunderingRoar",
    "BestTarget_ToTheLimit",
    "BestTarget_TogetherAsOne",
    "BestTarget_Tremor",
    "BestTarget_UrsanRoar",
    "BestTarget_UrsanRoarBloodWashesBlood",
    "BestTarget_VictoryIsMine",
    "BestTarget_VolfenBloodlust",
    "BestTarget_VolfenBloodlustCurseOfTheNornbear",
    "BestTarget_WatchYourself",
    "BestTarget_WatchYourselfPvp",
    "BestTarget_WeShallReturn",
    "BestTarget_WeShallReturnPvp",
    "BestTarget_YouAreAllWeaklings",
    "BestTarget_YouMoveLikeADwarf",
    "BestTarget_YouWillDie",
    "BestTarget_YoureAllAlone",
    "CanUse_Advance",
    "CanUse_AimTrue",
    "CanUse_BraceYourself",
    "CanUse_BraceYourselfPvp",
    "CanUse_ByUralsHammer",
    "CanUse_CallOfBrutality",
    "CanUse_CallOfDisruption",
    "CanUse_CallOfElementalProtection",
    "CanUse_CallOfFeeding",
    "CanUse_CallOfFerocity",
    "CanUse_CallOfHaste",
    "CanUse_CallOfHastePvp",
    "CanUse_CallOfHealing",
    "CanUse_CallOfProtection",
    "CanUse_CallOfResilience",
    "CanUse_CallOfTheHunter",
    "CanUse_CallOfVitality",
    "CanUse_CantTouchThis",
    "CanUse_CantTouchThisPvp",
    "CanUse_Charge",
    "CanUse_Coward",
    "CanUse_CryOfMadness",
    "CanUse_DestroyTheHumans",
    "CanUse_DodgeThis",
    "CanUse_DontBelieveTheirLies",
    "CanUse_DontTrip",
    "CanUse_EchoingBanishment",
    "CanUse_EnemiesMustDie",
    "CanUse_FallBack",
    "CanUse_FallBackPvp",
    "CanUse_FearMe",
    "CanUse_FindTheirWeakness",
    "CanUse_FindTheirWeaknessPvp",
    "CanUse_FindTheirWeaknessThackeray",
    "CanUse_FinishHim",
    "CanUse_ForElona",
    "CanUse_ForGreatJustice",
    "CanUse_ForGreatJusticePvp",
    "CanUse_ForgeTheWay",
    "CanUse_FormUpAndAdvance",
    "CanUse_GoForTheEyes",
    "CanUse_GoForTheEyesPvp",
    "CanUse_Godspeed",
    "CanUse_Headshot",
    "CanUse_HelpMe",
    "CanUse_HelpMePvp",
    "CanUse_IAmTheStrongest",
    "CanUse_IAmUnstoppable",
    "CanUse_IMeantToDoThat",
    "CanUse_IWillAvengeYou",
    "CanUse_IWillSurvive",
    "CanUse_IllBeBack",
    "CanUse_Incoming",
    "CanUse_IncomingPvp",
    "CanUse_ItsGoodToBeKing",
    "CanUse_ItsJustAFleshWound",
    "CanUse_KilroyStonekin",
    "CanUse_KraksCharge",
    "CanUse_LeadTheWay",
    "CanUse_LetsGetEm",
    "CanUse_MaddeningLaughter",
    "CanUse_MakeHaste",
    "CanUse_MakeYourTime",
    "CanUse_MmmmSnowcone",
    "CanUse_MotivatingInsults",
    "CanUse_NeverGiveUp",
    "CanUse_NeverGiveUpPvp",
    "CanUse_NeverSurrender",
    "CanUse_NeverSurrenderPvp",
    "CanUse_NoneShallPass",
    "CanUse_OnYourKnees",
    "CanUse_OtyughsCry",
    "CanUse_PredatoryBond",
    "CanUse_PredatoryBondPvp",
    "CanUse_QueenWail",
    "CanUse_RavenShriek",
    "CanUse_RavenShriekAGateTooFar",
    "CanUse_RemoveQueenWail",
    "CanUse_RemoveWithHaste",
    "CanUse_Retreat",
    "CanUse_SaveYourselvesKurzick",
    "CanUse_SaveYourselvesLuxon",
    "CanUse_ShieldsUp",
    "CanUse_SongOfTheMists",
    "CanUse_SpiritRoar",
    "CanUse_StandUp",
    "CanUse_StandYourGround",
    "CanUse_StandYourGroundPvp",
    "CanUse_SteadyAim",
    "CanUse_StickyGround",
    "CanUse_StrikeAsOne",
    "CanUse_SugarShock",
    "CanUse_SymbioticBond",
    "CanUse_TangoDown",
    "CanUse_TengusMimicry",
    "CanUse_TheMadKingsInfluence",
    "CanUse_ThePowerIsYours",
    "CanUse_TheresNotEnoughTime",
    "CanUse_TheresNothingToFear",
    "CanUse_TheresNothingToFearThackeray",
    "CanUse_TheyreOnFire",
    "CanUse_ThunderingRoar",
    "CanUse_ToTheLimit",
    "CanUse_TogetherAsOne",
    "CanUse_Tremor",
    "CanUse_UrsanRoar",
    "CanUse_UrsanRoarBloodWashesBlood",
    "CanUse_VictoryIsMine",
    "CanUse_VolfenBloodlust",
    "CanUse_VolfenBloodlustCurseOfTheNornbear",
    "CanUse_WatchYourself",
    "CanUse_WatchYourselfPvp",
    "CanUse_WeShallReturn",
    "CanUse_WeShallReturnPvp",
    "CanUse_YouAreAllWeaklings",
    "CanUse_YouMoveLikeADwarf",
    "CanUse_YouWillDie",
    "CanUse_YoureAllAlone",
]
