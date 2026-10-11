"""GwAu3's ``UtilityAI_Skill10.au3`` strategy functions, transcribed.

**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_strategies.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

`py4gw/gwa3/uai_best_target_cache.py` and `uai_can_use_cache.py` answer a slot's skill id with the *name*
of one of these functions; GwAu3's engine resolves that name with AutoIt's ``Call``, and this layer
resolves it the same way. So these are the strategy half of the ranking: which agent a skill wants, or
which guard lets it be used at all. **529 of this file's 529 are transcribed and 0
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
from .data_agent import Agent_GetAgentInfo
from .data_party import Party_GetPetInfo
from .data_world import World_GetWorldInfo
from .uai_agent import (
    UAI_GetAgentInfo,
    UAI_GetPlayerInfo,
)
from .uai_effects import (
    UAI_GetPlayerEffectInfo,
    UAI_PlayerHasEffect,
)
from .uai_filter import (
    UAI_Filter_IsLivingAlly,
    UAI_Filter_IsSpirit,
)
from .uai_get_agent import (
    UAI_CountAgents,
    UAI_GetAgentLowest,
    UAI_GetBestAOETarget,
    UAI_GetBestSingleTarget,
    UAI_GetFarthestAgent,
    UAI_GetNearestAgent,
    UAI_IsAgentInRange,
    _cached_distance,
    _cached_ids,
)


def CanUse_Blackout() -> Any:
    """``UtilityAI_Skill10.au3:8`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Blackout(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:12`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PlagueTouch() -> Any:
    """``UtilityAI_Skill10.au3:22`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_PlagueTouch(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:26`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_VileTouch() -> Any:
    """``UtilityAI_Skill10.au3:36`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_VileTouch(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:40`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_VampiricTouch() -> Any:
    """``UtilityAI_Skill10.au3:50`` -- transcribed from GwAu3's own body."""

    if UAI_CountAgents(-2, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy") < 1:
        return False
    return True


def BestTarget_VampiricTouch(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:56`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_TouchOfAgony() -> Any:
    """``UtilityAI_Skill10.au3:65`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_TouchOfAgony(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:69`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_Shock() -> Any:
    """``UtilityAI_Skill10.au3:79`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Shock(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:83`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_LightningTouch() -> Any:
    """``UtilityAI_Skill10.au3:93`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_LightningTouch(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:97`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_ContemplationOfPurity() -> Any:
    """``UtilityAI_Skill10.au3:107`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ContemplationOfPurity(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:111`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_HolyStrike() -> Any:
    """``UtilityAI_Skill10.au3:120`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_HolyStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:124`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_Flourish() -> Any:
    """``UtilityAI_Skill10.au3:134`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Flourish(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:138`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CharmAnimal() -> Any:
    """``UtilityAI_Skill10.au3:147`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_CharmAnimal(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:151`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_ReviveAnimal() -> Any:
    """``UtilityAI_Skill10.au3:162`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ReviveAnimal(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:166`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ThrowDirt() -> Any:
    """``UtilityAI_Skill10.au3:175`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ThrowDirt(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:179`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_ComfortAnimal() -> Any:
    """``UtilityAI_Skill10.au3:189`` -- transcribed from GwAu3's own body."""

    l_i_PetSize = World_GetWorldInfo("PetInfoArraySize")
    lMyPet = 0
    for i in range(1,  + 1):
        if Party_GetPetInfo(i, "OwnerAgentID") == UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID):
            lMyPet = Party_GetPetInfo(i, "AgentID")
            break


        if lMyPet == 0:
            return False
        if Agent_GetAgentInfo(lMyPet, "HPPercent") < 0.5:
            return True
        return False


def BestTarget_ComfortAnimal(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:208`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_TrollUnguent() -> Any:
    """``UtilityAI_Skill10.au3:217`` -- transcribed from GwAu3's own body."""

    if UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_HP) > 0.8:
        return False
    return True


def BestTarget_TrollUnguent(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:223`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DeafeningRoar() -> Any:
    """``UtilityAI_Skill10.au3:232`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_DeafeningRoar(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:236`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ClaimResource1() -> Any:
    """``UtilityAI_Skill10.au3:245`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ClaimResource1(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:249`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ClaimResource2() -> Any:
    """``UtilityAI_Skill10.au3:254`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ClaimResource2(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:258`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ClaimResource3() -> Any:
    """``UtilityAI_Skill10.au3:263`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ClaimResource3(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:267`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ClaimResource4() -> Any:
    """``UtilityAI_Skill10.au3:272`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ClaimResource4(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:276`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ClaimResource5() -> Any:
    """``UtilityAI_Skill10.au3:281`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ClaimResource5(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:285`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ClaimResource6() -> Any:
    """``UtilityAI_Skill10.au3:290`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ClaimResource6(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:294`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ClaimResource7() -> Any:
    """``UtilityAI_Skill10.au3:299`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ClaimResource7(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:303`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ClaimResource8() -> Any:
    """``UtilityAI_Skill10.au3:308`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ClaimResource8(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:312`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ClaimResource9() -> Any:
    """``UtilityAI_Skill10.au3:317`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ClaimResource9(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:321`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ClaimResource10() -> Any:
    """``UtilityAI_Skill10.au3:326`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ClaimResource10(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:330`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CrystalHibernation() -> Any:
    """``UtilityAI_Skill10.au3:335`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_CrystalHibernation(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:339`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_LifeVortex() -> Any:
    """``UtilityAI_Skill10.au3:348`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_LifeVortex(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:352`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SpectralAgony() -> Any:
    """``UtilityAI_Skill10.au3:361`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_SpectralAgony(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:365`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ClaimResource() -> Any:
    """``UtilityAI_Skill10.au3:375`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ClaimResource(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:379`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_TeleportPlayers() -> Any:
    """``UtilityAI_Skill10.au3:388`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_TeleportPlayers(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:392`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Knock() -> Any:
    """``UtilityAI_Skill10.au3:402`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Knock(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:406`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_IronPalm() -> Any:
    """``UtilityAI_Skill10.au3:415`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_IronPalm(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:419`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsConditioned")
    if l_i_Target != 0:
        return l_i_Target
    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsHexed")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ProtectorsDefense() -> Any:
    """``UtilityAI_Skill10.au3:433`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ProtectorsDefense(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:437`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ExpungeEnchantments() -> Any:
    """``UtilityAI_Skill10.au3:442`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ExpungeEnchantments(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:446`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsEnchanted")


def CanUse_Impale() -> Any:
    """``UtilityAI_Skill10.au3:456`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Impale(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:460`` -- transcribed from GwAu3's own body."""

    UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsLastStrikeIsDual")  # pyright: ignore[reportUnusedExpression]


def CanUse_StarStrike() -> Any:
    """``UtilityAI_Skill10.au3:470`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_StarStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:474`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PalmStrike() -> Any:
    """``UtilityAI_Skill10.au3:483`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_PalmStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:487`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_StarServant() -> Any:
    """``UtilityAI_Skill10.au3:497`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_StarServant(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:501`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_VampiricBite() -> Any:
    """``UtilityAI_Skill10.au3:510`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_VampiricBite(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:514`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_WallowsBite() -> Any:
    """``UtilityAI_Skill10.au3:524`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_WallowsBite(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:528`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_EnfeeblingTouch() -> Any:
    """``UtilityAI_Skill10.au3:534`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_EnfeeblingTouch(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:538`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_CelestialStorm() -> Any:
    """``UtilityAI_Skill10.au3:548`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_CelestialStorm(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:552`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_StarShine() -> Any:
    """``UtilityAI_Skill10.au3:562`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_StarShine(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:566`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_StonesoulStrike() -> Any:
    """``UtilityAI_Skill10.au3:575`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_StonesoulStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:579`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_StormOfSwords() -> Any:
    """``UtilityAI_Skill10.au3:589`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_StormOfSwords(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:593`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Shove() -> Any:
    """``UtilityAI_Skill10.au3:602`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Shove(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:606`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_BaseDefense() -> Any:
    """``UtilityAI_Skill10.au3:616`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_BaseDefense(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:620`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CarrierDefense() -> Any:
    """``UtilityAI_Skill10.au3:630`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_CarrierDefense(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:634`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_TheChaliceOfCorruption() -> Any:
    """``UtilityAI_Skill10.au3:643`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_TheChaliceOfCorruption(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:647`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_JuggernautToss() -> Any:
    """``UtilityAI_Skill10.au3:656`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_JuggernautToss(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:660`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_LastStand() -> Any:
    """``UtilityAI_Skill10.au3:670`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_LastStand(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:674`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ConstructPossession() -> Any:
    """``UtilityAI_Skill10.au3:679`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ConstructPossession(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:683`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SiegeTurtleAttackTheEternalGrove() -> Any:
    """``UtilityAI_Skill10.au3:692`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_SiegeTurtleAttackTheEternalGrove(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:696`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SiegeTurtleAttackFortAspenwood() -> Any:
    """``UtilityAI_Skill10.au3:702`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_SiegeTurtleAttackFortAspenwood(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:706`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SiegeTurtleAttackGyalaHatchery() -> Any:
    """``UtilityAI_Skill10.au3:712`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_SiegeTurtleAttackGyalaHatchery(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:716`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_HealAsOne() -> Any:
    """``UtilityAI_Skill10.au3:721`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_HealAsOne(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:725`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CelestialStance() -> Any:
    """``UtilityAI_Skill10.au3:734`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_CelestialStance(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:738`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ArmorOfUnfeeling() -> Any:
    """``UtilityAI_Skill10.au3:747`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ArmorOfUnfeeling(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:751`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CelestialSummoning() -> Any:
    """``UtilityAI_Skill10.au3:760`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_CelestialSummoning(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:764`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AncestorsRage() -> Any:
    """``UtilityAI_Skill10.au3:773`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_AncestorsRage(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:777`` -- transcribed from GwAu3's own body."""

    l_i_BestAlly = 0
    l_i_BestEnemyCount = 0
    for i in _cached_ids():
        l_i_AgentID = UAI_GetAgentInfo(i, _constants.GC_UAI_AGENT_ID)
        if not UAI_Filter_IsLivingAlly(l_i_AgentID):
            continue
        if UAI_Filter_IsSpirit(l_i_AgentID):
            continue
        l_f_Distance = _cached_distance(i)
        if l_f_Distance > a_f_AggroRange:
            continue
        l_i_EnemyCount = UAI_CountAgents(l_i_AgentID, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")
        if l_i_EnemyCount > l_i_BestEnemyCount:
            l_i_BestEnemyCount = l_i_EnemyCount
            l_i_BestAlly = l_i_AgentID


        if l_i_BestEnemyCount >= 1:
            return l_i_BestAlly
        return 0


def CanUse_ImpossibleOdds() -> Any:
    """``UtilityAI_Skill10.au3:810`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ImpossibleOdds(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:814`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MeditationOfTheReaper1() -> Any:
    """``UtilityAI_Skill10.au3:823`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_MeditationOfTheReaper1(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:827`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ForestsBinding() -> Any:
    """``UtilityAI_Skill10.au3:832`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ForestsBinding(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:836`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ExplodingSpores() -> Any:
    """``UtilityAI_Skill10.au3:842`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ExplodingSpores(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:846`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RageOfTheSea() -> Any:
    """``UtilityAI_Skill10.au3:855`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_RageOfTheSea(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:859`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MeditationOfTheReaper2() -> Any:
    """``UtilityAI_Skill10.au3:869`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_MeditationOfTheReaper2(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:873`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_TormentSlash() -> Any:
    """``UtilityAI_Skill10.au3:879`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_TormentSlash(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:883`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_TradeWinds() -> Any:
    """``UtilityAI_Skill10.au3:893`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_TradeWinds(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:897`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return 0


def CanUse_DragonBlast() -> Any:
    """``UtilityAI_Skill10.au3:910`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_DragonBlast(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:914`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ImperialMajesty() -> Any:
    """``UtilityAI_Skill10.au3:924`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ImperialMajesty(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:928`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SymbolsOfInspiration() -> Any:
    """``UtilityAI_Skill10.au3:938`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_SymbolsOfInspiration(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:942`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SentryTrapSkill() -> Any:
    """``UtilityAI_Skill10.au3:952`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_SentryTrapSkill(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:956`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CaltropsMonster() -> Any:
    """``UtilityAI_Skill10.au3:961`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_CaltropsMonster(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:965`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SacredBranch() -> Any:
    """``UtilityAI_Skill10.au3:970`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_SacredBranch(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:974`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_LightOfSeborhin() -> Any:
    """``UtilityAI_Skill10.au3:983`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_LightOfSeborhin(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:987`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Headbutt() -> Any:
    """``UtilityAI_Skill10.au3:996`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Headbutt(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1000`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_LionsComfort() -> Any:
    """``UtilityAI_Skill10.au3:1010`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_LionsComfort(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1014`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DisarmTrap() -> Any:
    """``UtilityAI_Skill10.au3:1023`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_DisarmTrap(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1027`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CreateLightOfSeborhin() -> Any:
    """``UtilityAI_Skill10.au3:1036`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_CreateLightOfSeborhin(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1040`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_UnlockCell() -> Any:
    """``UtilityAI_Skill10.au3:1049`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_UnlockCell(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1053`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_JununduFeast() -> Any:
    """``UtilityAI_Skill10.au3:1062`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_JununduFeast(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1067`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, _constants.GC_I_RANGE_ADJACENT, "GC_UAI_AGENT_IsExploitableCorpse")


def CanUse_JununduStrike() -> Any:
    """``UtilityAI_Skill10.au3:1074`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_JununduStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1079`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_JununduSmash() -> Any:
    """``UtilityAI_Skill10.au3:1086`` -- transcribed from GwAu3's own body."""

    if not UAI_IsAgentInRange(-2, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy"):
        return False
    return True


def BestTarget_JununduSmash(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1092`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_JununduSiege1() -> Any:
    """``UtilityAI_Skill10.au3:1099`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_JununduSiege1(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1104`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetFarthestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")
    if _cached_distance(uai_const.g_i_BestTarget) > _constants.GC_I_RANGE_NEARBY:
        return l_i_Target


def CanUse_LeaveJunundu() -> Any:
    """``UtilityAI_Skill10.au3:1112`` -- transcribed from GwAu3's own body."""

    return False


def BestTarget_LeaveJunundu(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1116`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SignalFlare() -> Any:
    """``UtilityAI_Skill10.au3:1126`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_SignalFlare(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1130`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_TheElixirOfStrength() -> Any:
    """``UtilityAI_Skill10.au3:1139`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_TheElixirOfStrength(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1143`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_EhzahFromAbove() -> Any:
    """``UtilityAI_Skill10.au3:1152`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_EhzahFromAbove(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1156`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_CallToTheTorment() -> Any:
    """``UtilityAI_Skill10.au3:1162`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_CallToTheTorment(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1166`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CommandOfTorment() -> Any:
    """``UtilityAI_Skill10.au3:1171`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_CommandOfTorment(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1175`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AbaddonsFavor() -> Any:
    """``UtilityAI_Skill10.au3:1184`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_AbaddonsFavor(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1188`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ScavengersFocus() -> Any:
    """``UtilityAI_Skill10.au3:1194`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ScavengersFocus(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1198`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Awe() -> Any:
    """``UtilityAI_Skill10.au3:1203`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Awe(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1207`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsKnocked")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_LeadersZeal() -> Any:
    """``UtilityAI_Skill10.au3:1219`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_LeadersZeal(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1223`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_LeadersComfort() -> Any:
    """``UtilityAI_Skill10.au3:1228`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_LeadersComfort(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1232`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AngelicProtection() -> Any:
    """``UtilityAI_Skill10.au3:1237`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_AngelicProtection(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1241`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return 0


def CanUse_AngelicBond() -> Any:
    """``UtilityAI_Skill10.au3:1253`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_AngelicBond(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1257`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ScepterOfEther() -> Any:
    """``UtilityAI_Skill10.au3:1266`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ScepterOfEther(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1270`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_QueenHeal() -> Any:
    """``UtilityAI_Skill10.au3:1279`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_QueenHeal(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1283`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_QueenBite() -> Any:
    """``UtilityAI_Skill10.au3:1292`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_QueenBite(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1296`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_QueenThump() -> Any:
    """``UtilityAI_Skill10.au3:1306`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_QueenThump(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1310`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_QueenSiege() -> Any:
    """``UtilityAI_Skill10.au3:1319`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_QueenSiege(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1323`` -- transcribed from GwAu3's own body."""

    return UAI_GetFarthestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_AssaultEnchantments() -> Any:
    """``UtilityAI_Skill10.au3:1333`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_AssaultEnchantments(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1337`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsEnchanted|UAI_Filter_IsLastStrikeIsDual")


def CanUse_WastrelsCollapse() -> Any:
    """``UtilityAI_Skill10.au3:1347`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_WastrelsCollapse(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1351`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_LiftEnchantment() -> Any:
    """``UtilityAI_Skill10.au3:1357`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_LiftEnchantment(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1361`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsKnocked")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_CorruptPower() -> Any:
    """``UtilityAI_Skill10.au3:1373`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_CorruptPower(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1377`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GazeOfMoavukaal() -> Any:
    """``UtilityAI_Skill10.au3:1387`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_GazeOfMoavukaal(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1391`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_TheApocryphaIsChangingToAnotherForm() -> Any:
    """``UtilityAI_Skill10.au3:1397`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_TheApocryphaIsChangingToAnotherForm(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1401`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ReformCarvings() -> Any:
    """``UtilityAI_Skill10.au3:1406`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ReformCarvings(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1410`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SoulTorture() -> Any:
    """``UtilityAI_Skill10.au3:1419`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_SoulTorture(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1423`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_LightbringersGaze() -> Any:
    """``UtilityAI_Skill10.au3:1432`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_LightbringersGaze(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1436`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_MaddenedStrike() -> Any:
    """``UtilityAI_Skill10.au3:1442`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_MaddenedStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1446`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_KournanSiege() -> Any:
    """``UtilityAI_Skill10.au3:1456`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_KournanSiege(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1460`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ChokingBreath() -> Any:
    """``UtilityAI_Skill10.au3:1470`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ChokingBreath(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1475`` -- transcribed from GwAu3's own body."""

    l_i_CastingTarget = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCasting")
    if l_i_CastingTarget != 0:
        return l_i_CastingTarget
    l_i_AOETarget = UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")
    if l_i_AOETarget != 0:
        return l_i_AOETarget
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_JununduBite() -> Any:
    """``UtilityAI_Skill10.au3:1487`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_JununduBite(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1492`` -- transcribed from GwAu3's own body."""

    l_i_KnockedTarget = UAI_GetNearestAgent(-2, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsKnocked")
    if l_i_KnockedTarget != 0:
        return l_i_KnockedTarget
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_BlindingBreath() -> Any:
    """``UtilityAI_Skill10.au3:1501`` -- transcribed from GwAu3's own body."""

    if not UAI_IsAgentInRange(-2, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy"):
        return False
    return True


def BestTarget_BlindingBreath(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1507`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BurningBreath() -> Any:
    """``UtilityAI_Skill10.au3:1514`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_BurningBreath(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1519`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetFarthestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")
    if _cached_distance(uai_const.g_i_BestTarget) > _constants.GC_I_RANGE_NEARBY:
        return l_i_Target


def CanUse_JununduWail() -> Any:
    """``UtilityAI_Skill10.au3:1526`` -- transcribed from GwAu3's own body."""

    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_CURSE_OF_DHUUM) or UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_FROZEN_SOIL):
        return False
    return True


def BestTarget_JununduWail(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1532`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, _constants.GC_I_RANGE_EARSHOT, "UAI_Filter_IsDeadAlly")
    if l_i_Target != 0:
        return l_i_Target
    if not UAI_IsAgentInRange(-2, _constants.GC_I_RANGE_EARSHOT, "UAI_Filter_IsLivingEnemy") and UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_HP) <= 1.0:
        return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)



def CanUse_WordsOfMadness() -> Any:
    """``UtilityAI_Skill10.au3:1547`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_WordsOfMadness(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1551`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_UnknownJununduAbility() -> Any:
    """``UtilityAI_Skill10.au3:1561`` -- transcribed from GwAu3's own body."""

    return False


def BestTarget_UnknownJununduAbility(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1565`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_TormentSlashSmotheringTendrils() -> Any:
    """``UtilityAI_Skill10.au3:1575`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_TormentSlashSmotheringTendrils(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1579`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ConsumeTorment() -> Any:
    """``UtilityAI_Skill10.au3:1585`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ConsumeTorment(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1589`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SummoningShadows() -> Any:
    """``UtilityAI_Skill10.au3:1598`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_SummoningShadows(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1602`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_TouchOfAaaaarrrrrrggghhh() -> Any:
    """``UtilityAI_Skill10.au3:1611`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_TouchOfAaaaarrrrrrggghhh(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1615`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SideStep() -> Any:
    """``UtilityAI_Skill10.au3:1625`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_SideStep(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1629`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CharmAnimalWhiteMantle() -> Any:
    """``UtilityAI_Skill10.au3:1642`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_CharmAnimalWhiteMantle(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1646`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ClaimResourceHeroesAscent() -> Any:
    """``UtilityAI_Skill10.au3:1651`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ClaimResourceHeroesAscent(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1655`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_LunarBlessing() -> Any:
    """``UtilityAI_Skill10.au3:1660`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_LunarBlessing(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1664`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_LuckyAura() -> Any:
    """``UtilityAI_Skill10.au3:1673`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_LuckyAura(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1677`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SpiritualPossession() -> Any:
    """``UtilityAI_Skill10.au3:1686`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_SpiritualPossession(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1690`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Water() -> Any:
    """``UtilityAI_Skill10.au3:1699`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Water(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1703`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ShroudOfAsh() -> Any:
    """``UtilityAI_Skill10.au3:1712`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ShroudOfAsh(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1716`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FlameCall() -> Any:
    """``UtilityAI_Skill10.au3:1725`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_FlameCall(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1729`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_TorturersInferno() -> Any:
    """``UtilityAI_Skill10.au3:1738`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_TorturersInferno(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1742`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_WhirlingFires() -> Any:
    """``UtilityAI_Skill10.au3:1747`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_WhirlingFires(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1751`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CharrSiegeAttackWhatMustBeDone() -> Any:
    """``UtilityAI_Skill10.au3:1760`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_CharrSiegeAttackWhatMustBeDone(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1764`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_CharrSiegeAttackAgainstTheCharr() -> Any:
    """``UtilityAI_Skill10.au3:1770`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_CharrSiegeAttackAgainstTheCharr(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1774`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Grapple() -> Any:
    """``UtilityAI_Skill10.au3:1779`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Grapple(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1783`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_Berserk() -> Any:
    """``UtilityAI_Skill10.au3:1793`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Berserk(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1797`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Chomp() -> Any:
    """``UtilityAI_Skill10.au3:1806`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Chomp(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1810`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_TwistingJaws() -> Any:
    """``UtilityAI_Skill10.au3:1820`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_TwistingJaws(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1824`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_Trample() -> Any:
    """``UtilityAI_Skill10.au3:1834`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Trample(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1838`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_Necrosis() -> Any:
    """``UtilityAI_Skill10.au3:1848`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Necrosis(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1852`` -- transcribed from GwAu3's own body."""

    l_i_Conditionned = UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsConditioned")
    l_i_Hexed = UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsHexed")
    if l_i_Conditionned != 0:
        return l_i_Conditionned
    if l_i_Hexed != 0:
        return l_i_Hexed
    return 0


def CanUse_CallOfTheEye() -> Any:
    """``UtilityAI_Skill10.au3:1865`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_CallOfTheEye(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1869`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_UrsanRageBloodWashesBlood() -> Any:
    """``UtilityAI_Skill10.au3:1878`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_UrsanRageBloodWashesBlood(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1882`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_UrsanStrikeBloodWashesBlood() -> Any:
    """``UtilityAI_Skill10.au3:1887`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_UrsanStrikeBloodWashesBlood(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1891`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_Firebomb() -> Any:
    """``UtilityAI_Skill10.au3:1898`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Firebomb(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1902`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ShieldOfFire() -> Any:
    """``UtilityAI_Skill10.au3:1912`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ShieldOfFire(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1916`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_VolfenClawCurseOfTheNornbear() -> Any:
    """``UtilityAI_Skill10.au3:1925`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_VolfenClawCurseOfTheNornbear(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1929`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_VolfenBlessingCurseOfTheNornbear() -> Any:
    """``UtilityAI_Skill10.au3:1936`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_VolfenBlessingCurseOfTheNornbear(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1940`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Companionship() -> Any:
    """``UtilityAI_Skill10.au3:1945`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Companionship(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1949`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FeralAggression() -> Any:
    """``UtilityAI_Skill10.au3:1958`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_FeralAggression(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1962`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_APoolOfWater() -> Any:
    """``UtilityAI_Skill10.au3:1971`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_APoolOfWater(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1975`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PhaseShieldEffect() -> Any:
    """``UtilityAI_Skill10.au3:1980`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_PhaseShieldEffect(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1984`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def BestTarget_PhaseShieldMonsterSkill(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1989`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_VitalityTransfer() -> Any:
    """``UtilityAI_Skill10.au3:1994`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_VitalityTransfer(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:1998`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly")
    if l_i_Target != 0:
        return l_i_Target
    return 0


def CanUse_EnergyBlastGolem() -> Any:
    """``UtilityAI_Skill10.au3:2010`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_EnergyBlastGolem(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2014`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ChaoticEnergy() -> Any:
    """``UtilityAI_Skill10.au3:2020`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ChaoticEnergy(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2024`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RavenBlessingAGateTooFar() -> Any:
    """``UtilityAI_Skill10.au3:2034`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_RavenBlessingAGateTooFar(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2038`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RavenTalonsAGateTooFar() -> Any:
    """``UtilityAI_Skill10.au3:2044`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_RavenTalonsAGateTooFar(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2048`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_AspectOfOak() -> Any:
    """``UtilityAI_Skill10.au3:2054`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_AspectOfOak(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2058`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SunderingSoulcrush() -> Any:
    """``UtilityAI_Skill10.au3:2067`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_SunderingSoulcrush(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2071`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_PyroclasticShot() -> Any:
    """``UtilityAI_Skill10.au3:2081`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_PyroclasticShot(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2085`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_ExplosiveForce() -> Any:
    """``UtilityAI_Skill10.au3:2095`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ExplosiveForce(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2099`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PowderKegExplosion() -> Any:
    """``UtilityAI_Skill10.au3:2108`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_PowderKegExplosion(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2112`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SpiritleechAura() -> Any:
    """``UtilityAI_Skill10.au3:2121`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_SpiritleechAura(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2125`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_InspirationalSpeech() -> Any:
    """``UtilityAI_Skill10.au3:2134`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_InspirationalSpeech(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2138`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return 0


def CanUse_EarBite() -> Any:
    """``UtilityAI_Skill10.au3:2150`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_EarBite(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2154`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_LowBlow() -> Any:
    """``UtilityAI_Skill10.au3:2164`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_LowBlow(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2168`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsKnocked")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_BrawlingHeadbutt() -> Any:
    """``UtilityAI_Skill10.au3:2180`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_BrawlingHeadbutt(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2184`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_GelatinousCorpseConsumption() -> Any:
    """``UtilityAI_Skill10.au3:2194`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_GelatinousCorpseConsumption(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2198`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GelatinousMutation() -> Any:
    """``UtilityAI_Skill10.au3:2207`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_GelatinousMutation(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2211`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GelatinousAbsorption() -> Any:
    """``UtilityAI_Skill10.au3:2220`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_GelatinousAbsorption(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2224`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_UnstableOozeExplosion() -> Any:
    """``UtilityAI_Skill10.au3:2233`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_UnstableOozeExplosion(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2237`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_UnstableAura() -> Any:
    """``UtilityAI_Skill10.au3:2247`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_UnstableAura(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2251`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_UnstablePulse() -> Any:
    """``UtilityAI_Skill10.au3:2260`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_UnstablePulse(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2264`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SearingBreath() -> Any:
    """``UtilityAI_Skill10.au3:2273`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_SearingBreath(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2277`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Brawling() -> Any:
    """``UtilityAI_Skill10.au3:2287`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Brawling(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2291`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CallOfDestruction() -> Any:
    """``UtilityAI_Skill10.au3:2300`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_CallOfDestruction(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2304`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FlameJet() -> Any:
    """``UtilityAI_Skill10.au3:2313`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_FlameJet(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2317`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_LavaGround() -> Any:
    """``UtilityAI_Skill10.au3:2327`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_LavaGround(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2331`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_LavaWave() -> Any:
    """``UtilityAI_Skill10.au3:2340`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_LavaWave(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2344`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SpiritShield() -> Any:
    """``UtilityAI_Skill10.au3:2353`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_SpiritShield(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2357`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SummoningLord() -> Any:
    """``UtilityAI_Skill10.au3:2366`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_SummoningLord(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2370`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CharmAnimalAshlynSpiderfriend() -> Any:
    """``UtilityAI_Skill10.au3:2379`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_CharmAnimalAshlynSpiderfriend(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2383`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CharrSiegeAttackAssaultOnTheStronghold() -> Any:
    """``UtilityAI_Skill10.au3:2388`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_CharrSiegeAttackAssaultOnTheStronghold(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2392`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_TalonStrike() -> Any:
    """``UtilityAI_Skill10.au3:2398`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_TalonStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2402`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_LavaBlast() -> Any:
    """``UtilityAI_Skill10.au3:2408`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_LavaBlast(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2412`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AlkarsConcoction() -> Any:
    """``UtilityAI_Skill10.au3:2421`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_AlkarsConcoction(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2425`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_UrsanStrike() -> Any:
    """``UtilityAI_Skill10.au3:2430`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_UrsanStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2434`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_UrsanRage() -> Any:
    """``UtilityAI_Skill10.au3:2444`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_UrsanRage(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2448`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_VolfenClaw() -> Any:
    """``UtilityAI_Skill10.au3:2458`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_VolfenClaw(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2462`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_RavenTalons() -> Any:
    """``UtilityAI_Skill10.au3:2472`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_RavenTalons(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2476`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_TotemOfMan() -> Any:
    """``UtilityAI_Skill10.au3:2486`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_TotemOfMan(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2490`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SpawnPods() -> Any:
    """``UtilityAI_Skill10.au3:2499`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_SpawnPods(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2503`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_EnragedBlast() -> Any:
    """``UtilityAI_Skill10.au3:2512`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_EnragedBlast(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2516`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SpawnHatchling() -> Any:
    """``UtilityAI_Skill10.au3:2525`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_SpawnHatchling(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2529`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_UrsanAura() -> Any:
    """``UtilityAI_Skill10.au3:2538`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_UrsanAura(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2542`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ExtractInscription() -> Any:
    """``UtilityAI_Skill10.au3:2551`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ExtractInscription(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2555`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AirOfSuperiority() -> Any:
    """``UtilityAI_Skill10.au3:2564`` -- transcribed from GwAu3's own body."""

    if UAI_GetPlayerEffectInfo(_constants.GC_I_SKILL_ID_AIR_OF_SUPERIORITY, _constants.GC_UAI_EFFECT_TimeRemaining) > 5000:
        return False
    return True


def BestTarget_AirOfSuperiority(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2569`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DecipherInscriptions() -> Any:
    """``UtilityAI_Skill10.au3:2578`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_DecipherInscriptions(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2582`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AsuranFlameStaff() -> Any:
    """``UtilityAI_Skill10.au3:2592`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_AsuranFlameStaff(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2596`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_HauntedGround() -> Any:
    """``UtilityAI_Skill10.au3:2605`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_HauntedGround(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2609`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Gloat() -> Any:
    """``UtilityAI_Skill10.au3:2618`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Gloat(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2622`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Metamorphosis() -> Any:
    """``UtilityAI_Skill10.au3:2632`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Metamorphosis(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2636`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_InnerFire() -> Any:
    """``UtilityAI_Skill10.au3:2645`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_InnerFire(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2649`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FungalExplosion() -> Any:
    """``UtilityAI_Skill10.au3:2658`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_FungalExplosion(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2662`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BloodRage() -> Any:
    """``UtilityAI_Skill10.au3:2671`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_BloodRage(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2675`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_OozeCombination() -> Any:
    """``UtilityAI_Skill10.au3:2684`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_OozeCombination(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2688`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_OozeDivision() -> Any:
    """``UtilityAI_Skill10.au3:2699`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_OozeDivision(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2703`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SporeExplosion() -> Any:
    """``UtilityAI_Skill10.au3:2712`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_SporeExplosion(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2716`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DormantHusk() -> Any:
    """``UtilityAI_Skill10.au3:2725`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_DormantHusk(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2729`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MonkeySeeMonkeyDo() -> Any:
    """``UtilityAI_Skill10.au3:2738`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_MonkeySeeMonkeyDo(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2742`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FeedingFrenzy() -> Any:
    """``UtilityAI_Skill10.au3:2747`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_FeedingFrenzy(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2751`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SoulrendingShriek() -> Any:
    """``UtilityAI_Skill10.au3:2760`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_SoulrendingShriek(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2764`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsEnchanted")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SiegeDevourerFeast() -> Any:
    """``UtilityAI_Skill10.au3:2776`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_SiegeDevourerFeast(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2780`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DevourerBite() -> Any:
    """``UtilityAI_Skill10.au3:2789`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_DevourerBite(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2793`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SiegeDevourerSwipe() -> Any:
    """``UtilityAI_Skill10.au3:2803`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_SiegeDevourerSwipe(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2807`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DevourerSiege() -> Any:
    """``UtilityAI_Skill10.au3:2816`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_DevourerSiege(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2820`` -- transcribed from GwAu3's own body."""

    return UAI_GetFarthestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_DismountSiegeDevourer() -> Any:
    """``UtilityAI_Skill10.au3:2830`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_DismountSiegeDevourer(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2834`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Mount() -> Any:
    """``UtilityAI_Skill10.au3:2843`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Mount(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2847`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_TengusGaze() -> Any:
    """``UtilityAI_Skill10.au3:2857`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_TengusGaze(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2861`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ForgewightsBlessing() -> Any:
    """``UtilityAI_Skill10.au3:2866`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ForgewightsBlessing(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2870`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SelvetarmsBlessing() -> Any:
    """``UtilityAI_Skill10.au3:2875`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_SelvetarmsBlessing(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2879`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ThommissBlessing() -> Any:
    """``UtilityAI_Skill10.au3:2884`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ThommissBlessing(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2888`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RandsAttack() -> Any:
    """``UtilityAI_Skill10.au3:2893`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_RandsAttack(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2897`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_LitTorch() -> Any:
    """``UtilityAI_Skill10.au3:2903`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_LitTorch(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2907`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CharmAnimalCharrDemolisher() -> Any:
    """``UtilityAI_Skill10.au3:2916`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_CharmAnimalCharrDemolisher(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2920`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ThrowRock() -> Any:
    """``UtilityAI_Skill10.au3:2925`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ThrowRock(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2929`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_NightmarishAura() -> Any:
    """``UtilityAI_Skill10.au3:2939`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_NightmarishAura(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2943`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SiegeStrike() -> Any:
    """``UtilityAI_Skill10.au3:2952`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_SiegeStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2956`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_BarbedBomb() -> Any:
    """``UtilityAI_Skill10.au3:2966`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_BarbedBomb(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2970`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BalmBomb() -> Any:
    """``UtilityAI_Skill10.au3:2979`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_BalmBomb(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2983`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Explosives() -> Any:
    """``UtilityAI_Skill10.au3:2992`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Explosives(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:2996`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Rations() -> Any:
    """``UtilityAI_Skill10.au3:3005`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Rations(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:3009`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_StunBomb() -> Any:
    """``UtilityAI_Skill10.au3:3018`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_StunBomb(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:3022`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GiantStompTuraiOssa() -> Any:
    """``UtilityAI_Skill10.au3:3031`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_GiantStompTuraiOssa(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:3035`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_JununduSiege2() -> Any:
    """``UtilityAI_Skill10.au3:3040`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_JununduSiege2(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:3045`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetFarthestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")
    if _cached_distance(uai_const.g_i_BestTarget) > _constants.GC_I_RANGE_NEARBY:
        return l_i_Target


def CanUse_FireDart2() -> Any:
    """``UtilityAI_Skill10.au3:3053`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_FireDart2(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:3057`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AncestorsRagePvP() -> Any:
    """``UtilityAI_Skill10.au3:3064`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_AncestorsRagePvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:3068`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def BestTarget_BamphLite(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:3074`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_ReactorBlastTimer() -> Any:
    """``UtilityAI_Skill10.au3:3080`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ReactorBlastTimer(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:3084`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_InternalPowerEngaged() -> Any:
    """``UtilityAI_Skill10.au3:3093`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_InternalPowerEngaged(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:3097`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Countdown() -> Any:
    """``UtilityAI_Skill10.au3:3106`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Countdown(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:3110`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_NoxLockOn() -> Any:
    """``UtilityAI_Skill10.au3:3119`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_NoxLockOn(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:3123`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def BestTarget_BamphLifesteal(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:3129`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_DelayedBlastBamph() -> Any:
    """``UtilityAI_Skill10.au3:3141`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_DelayedBlastBamph(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:3145`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_GunthersGaze() -> Any:
    """``UtilityAI_Skill10.au3:3151`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_GunthersGaze(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:3155`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ComfortAnimalPvP() -> Any:
    """``UtilityAI_Skill10.au3:3160`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ComfortAnimalPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:3164`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CharmAnimal2() -> Any:
    """``UtilityAI_Skill10.au3:3169`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_CharmAnimal2(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:3173`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CharmAnimal3() -> Any:
    """``UtilityAI_Skill10.au3:3178`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_CharmAnimal3(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:3182`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CharmAnimalCodex() -> Any:
    """``UtilityAI_Skill10.au3:3187`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_CharmAnimalCodex(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:3191`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_TouchOfDhuum() -> Any:
    """``UtilityAI_Skill10.au3:3197`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_TouchOfDhuum(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:3201`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_HealAsOnePvP() -> Any:
    """``UtilityAI_Skill10.au3:3211`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_HealAsOnePvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:3215`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CharmDrake() -> Any:
    """``UtilityAI_Skill10.au3:3220`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_CharmDrake(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:3224`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GuildMonumentProtected() -> Any:
    """``UtilityAI_Skill10.au3:3235`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_GuildMonumentProtected(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:3239`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SacrificePawn() -> Any:
    """``UtilityAI_Skill10.au3:3248`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_SacrificePawn(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:3252`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe")
    if l_i_Target != 0:
        return l_i_Target
    return 0


def CanUse_Entourage() -> Any:
    """``UtilityAI_Skill10.au3:3265`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Entourage(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:3269`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_EntourageBuffer() -> Any:
    """``UtilityAI_Skill10.au3:3278`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_EntourageBuffer(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:3282`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DamageAssessment() -> Any:
    """``UtilityAI_Skill10.au3:3288`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_DamageAssessment(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:3292`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_SmashOfTheTitans() -> Any:
    """``UtilityAI_Skill10.au3:3303`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_SmashOfTheTitans(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:3307`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_AnnihilatorToss() -> Any:
    """``UtilityAI_Skill10.au3:3317`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_AnnihilatorToss(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:3321`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_TonicTipsiness() -> Any:
    """``UtilityAI_Skill10.au3:3331`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_TonicTipsiness(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:3335`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GiftOfBattle() -> Any:
    """``UtilityAI_Skill10.au3:3344`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_GiftOfBattle(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:3348`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ShadowTheft() -> Any:
    """``UtilityAI_Skill10.au3:3361`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_ShadowTheft(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill10.au3:3365`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


__all__ = [
    "BestTarget_APoolOfWater",
    "BestTarget_AbaddonsFavor",
    "BestTarget_AirOfSuperiority",
    "BestTarget_AlkarsConcoction",
    "BestTarget_AncestorsRage",
    "BestTarget_AncestorsRagePvP",
    "BestTarget_AngelicBond",
    "BestTarget_AngelicProtection",
    "BestTarget_AnnihilatorToss",
    "BestTarget_ArmorOfUnfeeling",
    "BestTarget_AspectOfOak",
    "BestTarget_AssaultEnchantments",
    "BestTarget_AsuranFlameStaff",
    "BestTarget_Awe",
    "BestTarget_BalmBomb",
    "BestTarget_BamphLifesteal",
    "BestTarget_BamphLite",
    "BestTarget_BarbedBomb",
    "BestTarget_BaseDefense",
    "BestTarget_Berserk",
    "BestTarget_Blackout",
    "BestTarget_BlindingBreath",
    "BestTarget_BloodRage",
    "BestTarget_Brawling",
    "BestTarget_BrawlingHeadbutt",
    "BestTarget_BurningBreath",
    "BestTarget_CallOfDestruction",
    "BestTarget_CallOfTheEye",
    "BestTarget_CallToTheTorment",
    "BestTarget_CaltropsMonster",
    "BestTarget_CarrierDefense",
    "BestTarget_CelestialStance",
    "BestTarget_CelestialStorm",
    "BestTarget_CelestialSummoning",
    "BestTarget_ChaoticEnergy",
    "BestTarget_CharmAnimal",
    "BestTarget_CharmAnimal2",
    "BestTarget_CharmAnimal3",
    "BestTarget_CharmAnimalAshlynSpiderfriend",
    "BestTarget_CharmAnimalCharrDemolisher",
    "BestTarget_CharmAnimalCodex",
    "BestTarget_CharmAnimalWhiteMantle",
    "BestTarget_CharmDrake",
    "BestTarget_CharrSiegeAttackAgainstTheCharr",
    "BestTarget_CharrSiegeAttackAssaultOnTheStronghold",
    "BestTarget_CharrSiegeAttackWhatMustBeDone",
    "BestTarget_ChokingBreath",
    "BestTarget_Chomp",
    "BestTarget_ClaimResource",
    "BestTarget_ClaimResource1",
    "BestTarget_ClaimResource10",
    "BestTarget_ClaimResource2",
    "BestTarget_ClaimResource3",
    "BestTarget_ClaimResource4",
    "BestTarget_ClaimResource5",
    "BestTarget_ClaimResource6",
    "BestTarget_ClaimResource7",
    "BestTarget_ClaimResource8",
    "BestTarget_ClaimResource9",
    "BestTarget_ClaimResourceHeroesAscent",
    "BestTarget_ComfortAnimal",
    "BestTarget_ComfortAnimalPvP",
    "BestTarget_CommandOfTorment",
    "BestTarget_Companionship",
    "BestTarget_ConstructPossession",
    "BestTarget_ConsumeTorment",
    "BestTarget_ContemplationOfPurity",
    "BestTarget_CorruptPower",
    "BestTarget_Countdown",
    "BestTarget_CreateLightOfSeborhin",
    "BestTarget_CrystalHibernation",
    "BestTarget_DamageAssessment",
    "BestTarget_DeafeningRoar",
    "BestTarget_DecipherInscriptions",
    "BestTarget_DelayedBlastBamph",
    "BestTarget_DevourerBite",
    "BestTarget_DevourerSiege",
    "BestTarget_DisarmTrap",
    "BestTarget_DismountSiegeDevourer",
    "BestTarget_DormantHusk",
    "BestTarget_DragonBlast",
    "BestTarget_EarBite",
    "BestTarget_EhzahFromAbove",
    "BestTarget_EnergyBlastGolem",
    "BestTarget_EnfeeblingTouch",
    "BestTarget_EnragedBlast",
    "BestTarget_Entourage",
    "BestTarget_EntourageBuffer",
    "BestTarget_ExplodingSpores",
    "BestTarget_ExplosiveForce",
    "BestTarget_Explosives",
    "BestTarget_ExpungeEnchantments",
    "BestTarget_ExtractInscription",
    "BestTarget_FeedingFrenzy",
    "BestTarget_FeralAggression",
    "BestTarget_FireDart2",
    "BestTarget_Firebomb",
    "BestTarget_FlameCall",
    "BestTarget_FlameJet",
    "BestTarget_Flourish",
    "BestTarget_ForestsBinding",
    "BestTarget_ForgewightsBlessing",
    "BestTarget_FungalExplosion",
    "BestTarget_GazeOfMoavukaal",
    "BestTarget_GelatinousAbsorption",
    "BestTarget_GelatinousCorpseConsumption",
    "BestTarget_GelatinousMutation",
    "BestTarget_GiantStompTuraiOssa",
    "BestTarget_GiftOfBattle",
    "BestTarget_Gloat",
    "BestTarget_Grapple",
    "BestTarget_GuildMonumentProtected",
    "BestTarget_GunthersGaze",
    "BestTarget_HauntedGround",
    "BestTarget_Headbutt",
    "BestTarget_HealAsOne",
    "BestTarget_HealAsOnePvP",
    "BestTarget_HolyStrike",
    "BestTarget_Impale",
    "BestTarget_ImperialMajesty",
    "BestTarget_ImpossibleOdds",
    "BestTarget_InnerFire",
    "BestTarget_InspirationalSpeech",
    "BestTarget_InternalPowerEngaged",
    "BestTarget_IronPalm",
    "BestTarget_JuggernautToss",
    "BestTarget_JununduBite",
    "BestTarget_JununduFeast",
    "BestTarget_JununduSiege1",
    "BestTarget_JununduSiege2",
    "BestTarget_JununduSmash",
    "BestTarget_JununduStrike",
    "BestTarget_JununduWail",
    "BestTarget_Knock",
    "BestTarget_KournanSiege",
    "BestTarget_LastStand",
    "BestTarget_LavaBlast",
    "BestTarget_LavaGround",
    "BestTarget_LavaWave",
    "BestTarget_LeadersComfort",
    "BestTarget_LeadersZeal",
    "BestTarget_LeaveJunundu",
    "BestTarget_LifeVortex",
    "BestTarget_LiftEnchantment",
    "BestTarget_LightOfSeborhin",
    "BestTarget_LightbringersGaze",
    "BestTarget_LightningTouch",
    "BestTarget_LionsComfort",
    "BestTarget_LitTorch",
    "BestTarget_LowBlow",
    "BestTarget_LuckyAura",
    "BestTarget_LunarBlessing",
    "BestTarget_MaddenedStrike",
    "BestTarget_MeditationOfTheReaper1",
    "BestTarget_MeditationOfTheReaper2",
    "BestTarget_Metamorphosis",
    "BestTarget_MonkeySeeMonkeyDo",
    "BestTarget_Mount",
    "BestTarget_Necrosis",
    "BestTarget_NightmarishAura",
    "BestTarget_NoxLockOn",
    "BestTarget_OozeCombination",
    "BestTarget_OozeDivision",
    "BestTarget_PalmStrike",
    "BestTarget_PhaseShieldEffect",
    "BestTarget_PhaseShieldMonsterSkill",
    "BestTarget_PlagueTouch",
    "BestTarget_PowderKegExplosion",
    "BestTarget_ProtectorsDefense",
    "BestTarget_PyroclasticShot",
    "BestTarget_QueenBite",
    "BestTarget_QueenHeal",
    "BestTarget_QueenSiege",
    "BestTarget_QueenThump",
    "BestTarget_RageOfTheSea",
    "BestTarget_RandsAttack",
    "BestTarget_Rations",
    "BestTarget_RavenBlessingAGateTooFar",
    "BestTarget_RavenTalons",
    "BestTarget_RavenTalonsAGateTooFar",
    "BestTarget_ReactorBlastTimer",
    "BestTarget_ReformCarvings",
    "BestTarget_ReviveAnimal",
    "BestTarget_SacredBranch",
    "BestTarget_SacrificePawn",
    "BestTarget_ScavengersFocus",
    "BestTarget_ScepterOfEther",
    "BestTarget_SearingBreath",
    "BestTarget_SelvetarmsBlessing",
    "BestTarget_SentryTrapSkill",
    "BestTarget_ShadowTheft",
    "BestTarget_ShieldOfFire",
    "BestTarget_Shock",
    "BestTarget_Shove",
    "BestTarget_ShroudOfAsh",
    "BestTarget_SideStep",
    "BestTarget_SiegeDevourerFeast",
    "BestTarget_SiegeDevourerSwipe",
    "BestTarget_SiegeStrike",
    "BestTarget_SiegeTurtleAttackFortAspenwood",
    "BestTarget_SiegeTurtleAttackGyalaHatchery",
    "BestTarget_SiegeTurtleAttackTheEternalGrove",
    "BestTarget_SignalFlare",
    "BestTarget_SmashOfTheTitans",
    "BestTarget_SoulTorture",
    "BestTarget_SoulrendingShriek",
    "BestTarget_SpawnHatchling",
    "BestTarget_SpawnPods",
    "BestTarget_SpectralAgony",
    "BestTarget_SpiritShield",
    "BestTarget_SpiritleechAura",
    "BestTarget_SpiritualPossession",
    "BestTarget_SporeExplosion",
    "BestTarget_StarServant",
    "BestTarget_StarShine",
    "BestTarget_StarStrike",
    "BestTarget_StonesoulStrike",
    "BestTarget_StormOfSwords",
    "BestTarget_StunBomb",
    "BestTarget_SummoningLord",
    "BestTarget_SummoningShadows",
    "BestTarget_SunderingSoulcrush",
    "BestTarget_SymbolsOfInspiration",
    "BestTarget_TalonStrike",
    "BestTarget_TeleportPlayers",
    "BestTarget_TengusGaze",
    "BestTarget_TheApocryphaIsChangingToAnotherForm",
    "BestTarget_TheChaliceOfCorruption",
    "BestTarget_TheElixirOfStrength",
    "BestTarget_ThommissBlessing",
    "BestTarget_ThrowDirt",
    "BestTarget_ThrowRock",
    "BestTarget_TonicTipsiness",
    "BestTarget_TormentSlash",
    "BestTarget_TormentSlashSmotheringTendrils",
    "BestTarget_TorturersInferno",
    "BestTarget_TotemOfMan",
    "BestTarget_TouchOfAaaaarrrrrrggghhh",
    "BestTarget_TouchOfAgony",
    "BestTarget_TouchOfDhuum",
    "BestTarget_TradeWinds",
    "BestTarget_Trample",
    "BestTarget_TrollUnguent",
    "BestTarget_TwistingJaws",
    "BestTarget_UnknownJununduAbility",
    "BestTarget_UnlockCell",
    "BestTarget_UnstableAura",
    "BestTarget_UnstableOozeExplosion",
    "BestTarget_UnstablePulse",
    "BestTarget_UrsanAura",
    "BestTarget_UrsanRage",
    "BestTarget_UrsanRageBloodWashesBlood",
    "BestTarget_UrsanStrike",
    "BestTarget_UrsanStrikeBloodWashesBlood",
    "BestTarget_VampiricBite",
    "BestTarget_VampiricTouch",
    "BestTarget_VileTouch",
    "BestTarget_VitalityTransfer",
    "BestTarget_VolfenBlessingCurseOfTheNornbear",
    "BestTarget_VolfenClaw",
    "BestTarget_VolfenClawCurseOfTheNornbear",
    "BestTarget_WallowsBite",
    "BestTarget_WastrelsCollapse",
    "BestTarget_Water",
    "BestTarget_WhirlingFires",
    "BestTarget_WordsOfMadness",
    "CanUse_APoolOfWater",
    "CanUse_AbaddonsFavor",
    "CanUse_AirOfSuperiority",
    "CanUse_AlkarsConcoction",
    "CanUse_AncestorsRage",
    "CanUse_AncestorsRagePvP",
    "CanUse_AngelicBond",
    "CanUse_AngelicProtection",
    "CanUse_AnnihilatorToss",
    "CanUse_ArmorOfUnfeeling",
    "CanUse_AspectOfOak",
    "CanUse_AssaultEnchantments",
    "CanUse_AsuranFlameStaff",
    "CanUse_Awe",
    "CanUse_BalmBomb",
    "CanUse_BarbedBomb",
    "CanUse_BaseDefense",
    "CanUse_Berserk",
    "CanUse_Blackout",
    "CanUse_BlindingBreath",
    "CanUse_BloodRage",
    "CanUse_Brawling",
    "CanUse_BrawlingHeadbutt",
    "CanUse_BurningBreath",
    "CanUse_CallOfDestruction",
    "CanUse_CallOfTheEye",
    "CanUse_CallToTheTorment",
    "CanUse_CaltropsMonster",
    "CanUse_CarrierDefense",
    "CanUse_CelestialStance",
    "CanUse_CelestialStorm",
    "CanUse_CelestialSummoning",
    "CanUse_ChaoticEnergy",
    "CanUse_CharmAnimal",
    "CanUse_CharmAnimal2",
    "CanUse_CharmAnimal3",
    "CanUse_CharmAnimalAshlynSpiderfriend",
    "CanUse_CharmAnimalCharrDemolisher",
    "CanUse_CharmAnimalCodex",
    "CanUse_CharmAnimalWhiteMantle",
    "CanUse_CharmDrake",
    "CanUse_CharrSiegeAttackAgainstTheCharr",
    "CanUse_CharrSiegeAttackAssaultOnTheStronghold",
    "CanUse_CharrSiegeAttackWhatMustBeDone",
    "CanUse_ChokingBreath",
    "CanUse_Chomp",
    "CanUse_ClaimResource",
    "CanUse_ClaimResource1",
    "CanUse_ClaimResource10",
    "CanUse_ClaimResource2",
    "CanUse_ClaimResource3",
    "CanUse_ClaimResource4",
    "CanUse_ClaimResource5",
    "CanUse_ClaimResource6",
    "CanUse_ClaimResource7",
    "CanUse_ClaimResource8",
    "CanUse_ClaimResource9",
    "CanUse_ClaimResourceHeroesAscent",
    "CanUse_ComfortAnimal",
    "CanUse_ComfortAnimalPvP",
    "CanUse_CommandOfTorment",
    "CanUse_Companionship",
    "CanUse_ConstructPossession",
    "CanUse_ConsumeTorment",
    "CanUse_ContemplationOfPurity",
    "CanUse_CorruptPower",
    "CanUse_Countdown",
    "CanUse_CreateLightOfSeborhin",
    "CanUse_CrystalHibernation",
    "CanUse_DamageAssessment",
    "CanUse_DeafeningRoar",
    "CanUse_DecipherInscriptions",
    "CanUse_DelayedBlastBamph",
    "CanUse_DevourerBite",
    "CanUse_DevourerSiege",
    "CanUse_DisarmTrap",
    "CanUse_DismountSiegeDevourer",
    "CanUse_DormantHusk",
    "CanUse_DragonBlast",
    "CanUse_EarBite",
    "CanUse_EhzahFromAbove",
    "CanUse_EnergyBlastGolem",
    "CanUse_EnfeeblingTouch",
    "CanUse_EnragedBlast",
    "CanUse_Entourage",
    "CanUse_EntourageBuffer",
    "CanUse_ExplodingSpores",
    "CanUse_ExplosiveForce",
    "CanUse_Explosives",
    "CanUse_ExpungeEnchantments",
    "CanUse_ExtractInscription",
    "CanUse_FeedingFrenzy",
    "CanUse_FeralAggression",
    "CanUse_FireDart2",
    "CanUse_Firebomb",
    "CanUse_FlameCall",
    "CanUse_FlameJet",
    "CanUse_Flourish",
    "CanUse_ForestsBinding",
    "CanUse_ForgewightsBlessing",
    "CanUse_FungalExplosion",
    "CanUse_GazeOfMoavukaal",
    "CanUse_GelatinousAbsorption",
    "CanUse_GelatinousCorpseConsumption",
    "CanUse_GelatinousMutation",
    "CanUse_GiantStompTuraiOssa",
    "CanUse_GiftOfBattle",
    "CanUse_Gloat",
    "CanUse_Grapple",
    "CanUse_GuildMonumentProtected",
    "CanUse_GunthersGaze",
    "CanUse_HauntedGround",
    "CanUse_Headbutt",
    "CanUse_HealAsOne",
    "CanUse_HealAsOnePvP",
    "CanUse_HolyStrike",
    "CanUse_Impale",
    "CanUse_ImperialMajesty",
    "CanUse_ImpossibleOdds",
    "CanUse_InnerFire",
    "CanUse_InspirationalSpeech",
    "CanUse_InternalPowerEngaged",
    "CanUse_IronPalm",
    "CanUse_JuggernautToss",
    "CanUse_JununduBite",
    "CanUse_JununduFeast",
    "CanUse_JununduSiege1",
    "CanUse_JununduSiege2",
    "CanUse_JununduSmash",
    "CanUse_JununduStrike",
    "CanUse_JununduWail",
    "CanUse_Knock",
    "CanUse_KournanSiege",
    "CanUse_LastStand",
    "CanUse_LavaBlast",
    "CanUse_LavaGround",
    "CanUse_LavaWave",
    "CanUse_LeadersComfort",
    "CanUse_LeadersZeal",
    "CanUse_LeaveJunundu",
    "CanUse_LifeVortex",
    "CanUse_LiftEnchantment",
    "CanUse_LightOfSeborhin",
    "CanUse_LightbringersGaze",
    "CanUse_LightningTouch",
    "CanUse_LionsComfort",
    "CanUse_LitTorch",
    "CanUse_LowBlow",
    "CanUse_LuckyAura",
    "CanUse_LunarBlessing",
    "CanUse_MaddenedStrike",
    "CanUse_MeditationOfTheReaper1",
    "CanUse_MeditationOfTheReaper2",
    "CanUse_Metamorphosis",
    "CanUse_MonkeySeeMonkeyDo",
    "CanUse_Mount",
    "CanUse_Necrosis",
    "CanUse_NightmarishAura",
    "CanUse_NoxLockOn",
    "CanUse_OozeCombination",
    "CanUse_OozeDivision",
    "CanUse_PalmStrike",
    "CanUse_PhaseShieldEffect",
    "CanUse_PlagueTouch",
    "CanUse_PowderKegExplosion",
    "CanUse_ProtectorsDefense",
    "CanUse_PyroclasticShot",
    "CanUse_QueenBite",
    "CanUse_QueenHeal",
    "CanUse_QueenSiege",
    "CanUse_QueenThump",
    "CanUse_RageOfTheSea",
    "CanUse_RandsAttack",
    "CanUse_Rations",
    "CanUse_RavenBlessingAGateTooFar",
    "CanUse_RavenTalons",
    "CanUse_RavenTalonsAGateTooFar",
    "CanUse_ReactorBlastTimer",
    "CanUse_ReformCarvings",
    "CanUse_ReviveAnimal",
    "CanUse_SacredBranch",
    "CanUse_SacrificePawn",
    "CanUse_ScavengersFocus",
    "CanUse_ScepterOfEther",
    "CanUse_SearingBreath",
    "CanUse_SelvetarmsBlessing",
    "CanUse_SentryTrapSkill",
    "CanUse_ShadowTheft",
    "CanUse_ShieldOfFire",
    "CanUse_Shock",
    "CanUse_Shove",
    "CanUse_ShroudOfAsh",
    "CanUse_SideStep",
    "CanUse_SiegeDevourerFeast",
    "CanUse_SiegeDevourerSwipe",
    "CanUse_SiegeStrike",
    "CanUse_SiegeTurtleAttackFortAspenwood",
    "CanUse_SiegeTurtleAttackGyalaHatchery",
    "CanUse_SiegeTurtleAttackTheEternalGrove",
    "CanUse_SignalFlare",
    "CanUse_SmashOfTheTitans",
    "CanUse_SoulTorture",
    "CanUse_SoulrendingShriek",
    "CanUse_SpawnHatchling",
    "CanUse_SpawnPods",
    "CanUse_SpectralAgony",
    "CanUse_SpiritShield",
    "CanUse_SpiritleechAura",
    "CanUse_SpiritualPossession",
    "CanUse_SporeExplosion",
    "CanUse_StarServant",
    "CanUse_StarShine",
    "CanUse_StarStrike",
    "CanUse_StonesoulStrike",
    "CanUse_StormOfSwords",
    "CanUse_StunBomb",
    "CanUse_SummoningLord",
    "CanUse_SummoningShadows",
    "CanUse_SunderingSoulcrush",
    "CanUse_SymbolsOfInspiration",
    "CanUse_TalonStrike",
    "CanUse_TeleportPlayers",
    "CanUse_TengusGaze",
    "CanUse_TheApocryphaIsChangingToAnotherForm",
    "CanUse_TheChaliceOfCorruption",
    "CanUse_TheElixirOfStrength",
    "CanUse_ThommissBlessing",
    "CanUse_ThrowDirt",
    "CanUse_ThrowRock",
    "CanUse_TonicTipsiness",
    "CanUse_TormentSlash",
    "CanUse_TormentSlashSmotheringTendrils",
    "CanUse_TorturersInferno",
    "CanUse_TotemOfMan",
    "CanUse_TouchOfAaaaarrrrrrggghhh",
    "CanUse_TouchOfAgony",
    "CanUse_TouchOfDhuum",
    "CanUse_TradeWinds",
    "CanUse_Trample",
    "CanUse_TrollUnguent",
    "CanUse_TwistingJaws",
    "CanUse_UnknownJununduAbility",
    "CanUse_UnlockCell",
    "CanUse_UnstableAura",
    "CanUse_UnstableOozeExplosion",
    "CanUse_UnstablePulse",
    "CanUse_UrsanAura",
    "CanUse_UrsanRage",
    "CanUse_UrsanRageBloodWashesBlood",
    "CanUse_UrsanStrike",
    "CanUse_UrsanStrikeBloodWashesBlood",
    "CanUse_VampiricBite",
    "CanUse_VampiricTouch",
    "CanUse_VileTouch",
    "CanUse_VitalityTransfer",
    "CanUse_VolfenBlessingCurseOfTheNornbear",
    "CanUse_VolfenClaw",
    "CanUse_VolfenClawCurseOfTheNornbear",
    "CanUse_WallowsBite",
    "CanUse_WastrelsCollapse",
    "CanUse_Water",
    "CanUse_WhirlingFires",
    "CanUse_WordsOfMadness",
]
