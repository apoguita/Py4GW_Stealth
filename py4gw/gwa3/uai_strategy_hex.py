"""GwAu3's ``UtilityAI_Hex.au3`` strategy functions, transcribed.

**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_strategies.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

`py4gw/gwa3/uai_best_target_cache.py` and `uai_can_use_cache.py` answer a slot's skill id with the *name*
of one of these functions; GwAu3's engine resolves that name with AutoIt's ``Call``, and this layer
resolves it the same way. So these are the strategy half of the ranking: which agent a skill wants, or
which guard lets it be used at all. **454 of this file's 454 are transcribed and 0
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
from .uai_get_agent import (
    UAI_GetAgentHighest,
    UAI_GetAgentLowest,
    UAI_GetBestAOETarget,
    UAI_GetBestSingleTarget,
    UAI_GetNearestAgent,
)


def CanUse_Fragility() -> Any:
    """``UtilityAI_Hex.au3:32`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_Fragility(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:37`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, 1320, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_Confusion() -> Any:
    """``UtilityAI_Hex.au3:46`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_Confusion(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:51`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_Empathy() -> Any:
    """``UtilityAI_Hex.au3:60`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_Empathy(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:65`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsAttacking")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_Backfire() -> Any:
    """``UtilityAI_Hex.au3:77`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_Backfire(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:82`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")


def CanUse_Diversion() -> Any:
    """``UtilityAI_Hex.au3:91`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_Diversion(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:96`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")


def CanUse_ConjurePhantasm() -> Any:
    """``UtilityAI_Hex.au3:105`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_ConjurePhantasm(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:110`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_Ignorance() -> Any:
    """``UtilityAI_Hex.au3:119`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_Ignorance(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:124`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_ArcaneConundrum() -> Any:
    """``UtilityAI_Hex.au3:133`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_ArcaneConundrum(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:138`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_EtherLord() -> Any:
    """``UtilityAI_Hex.au3:143`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_EtherLord(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:148`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")


def CanUse_Clumsiness() -> Any:
    """``UtilityAI_Hex.au3:157`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_Clumsiness(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:162`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, 1320, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_PhantomPain() -> Any:
    """``UtilityAI_Hex.au3:171`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_PhantomPain(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:176`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_EtherealBurden() -> Any:
    """``UtilityAI_Hex.au3:185`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_EtherealBurden(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:190`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsMoving")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_Guilt() -> Any:
    """``UtilityAI_Hex.au3:201`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_Guilt(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:206`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")


def CanUse_Ineptitude() -> Any:
    """``UtilityAI_Hex.au3:215`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_Ineptitude(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:220`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, 1320, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_SpiritOfFailure() -> Any:
    """``UtilityAI_Hex.au3:229`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_SpiritOfFailure(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:234`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsAttacking")


def CanUse_MindWrack() -> Any:
    """``UtilityAI_Hex.au3:243`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_MindWrack(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:248`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")


def CanUse_WastrelsWorry() -> Any:
    """``UtilityAI_Hex.au3:257`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_WastrelsWorry(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:262`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, 1320, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_Shame() -> Any:
    """``UtilityAI_Hex.au3:271`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_Shame(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:276`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")


def CanUse_Panic() -> Any:
    """``UtilityAI_Hex.au3:285`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_Panic(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:290`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, 1320, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_Migraine() -> Any:
    """``UtilityAI_Hex.au3:299`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_Migraine(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:304`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")


def CanUse_CripplingAnguish() -> Any:
    """``UtilityAI_Hex.au3:313`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_CripplingAnguish(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:318`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsAttacking")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_FeveredDreams() -> Any:
    """``UtilityAI_Hex.au3:329`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_FeveredDreams(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:334`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, 1320, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_SoothingImages() -> Any:
    """``UtilityAI_Hex.au3:343`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_SoothingImages(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:348`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, 1320, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_SpiritShackles() -> Any:
    """``UtilityAI_Hex.au3:357`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_SpiritShackles(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:362`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsAttacking")


def CanUse_ImaginedBurden() -> Any:
    """``UtilityAI_Hex.au3:371`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_ImaginedBurden(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:376`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsMoving")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_ParasiticBond() -> Any:
    """``UtilityAI_Hex.au3:388`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_ParasiticBond(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:393`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|-UAI_Filter_IsHexed")


def CanUse_SoulBarbs() -> Any:
    """``UtilityAI_Hex.au3:402`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_SoulBarbs(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:407`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy")


def CanUse_Barbs() -> Any:
    """``UtilityAI_Hex.au3:416`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_Barbs(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:421`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsAttacking")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_PriceOfFailure() -> Any:
    """``UtilityAI_Hex.au3:433`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_PriceOfFailure(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:438`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, 1320, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_Suffering() -> Any:
    """``UtilityAI_Hex.au3:447`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_Suffering(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:452`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, 1320, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_LifeSiphon() -> Any:
    """``UtilityAI_Hex.au3:461`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_LifeSiphon(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:466`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_SpitefulSpirit() -> Any:
    """``UtilityAI_Hex.au3:475`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_SpitefulSpirit(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:480`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, 1320, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_MalignIntervention() -> Any:
    """``UtilityAI_Hex.au3:489`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_MalignIntervention(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:494`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_InsidiousParasite() -> Any:
    """``UtilityAI_Hex.au3:503`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_InsidiousParasite(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:508`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsAttacking")


def CanUse_SpinalShivers() -> Any:
    """``UtilityAI_Hex.au3:517`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_SpinalShivers(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:522`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_Wither() -> Any:
    """``UtilityAI_Hex.au3:527`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_Wither(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:532`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")


def CanUse_LifeTransfer() -> Any:
    """``UtilityAI_Hex.au3:541`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_LifeTransfer(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:546`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, 1320, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_MarkOfSubversion() -> Any:
    """``UtilityAI_Hex.au3:555`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_MarkOfSubversion(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:560`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")


def CanUse_SoulLeech() -> Any:
    """``UtilityAI_Hex.au3:569`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_SoulLeech(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:574`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")


def CanUse_DefileFlesh() -> Any:
    """``UtilityAI_Hex.au3:583`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_DefileFlesh(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:588`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_Faintheartedness() -> Any:
    """``UtilityAI_Hex.au3:597`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_Faintheartedness(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:602`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsAttacking")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_ShadowOfFear() -> Any:
    """``UtilityAI_Hex.au3:614`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_ShadowOfFear(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:619`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, 1320, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_RigorMortis() -> Any:
    """``UtilityAI_Hex.au3:628`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_RigorMortis(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:633`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsAttacking")


def CanUse_Malaise() -> Any:
    """``UtilityAI_Hex.au3:642`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_Malaise(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:647`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")


def CanUse_LingeringCurse() -> Any:
    """``UtilityAI_Hex.au3:656`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_LingeringCurse(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:661`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, 1320, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_MarkOfPain() -> Any:
    """``UtilityAI_Hex.au3:670`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_MarkOfPain(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:675`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, 1320, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_GraspingEarth() -> Any:
    """``UtilityAI_Hex.au3:684`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_GraspingEarth(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:689`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_IncendiaryBonds() -> Any:
    """``UtilityAI_Hex.au3:698`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_IncendiaryBonds(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:703`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, 1320, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_MarkOfRodgort() -> Any:
    """``UtilityAI_Hex.au3:712`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_MarkOfRodgort(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:717`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, 1320, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_Rust() -> Any:
    """``UtilityAI_Hex.au3:726`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_Rust(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:731`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, 1320, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_LightningSurge() -> Any:
    """``UtilityAI_Hex.au3:740`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_LightningSurge(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:745`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, 1320, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_MindFreeze() -> Any:
    """``UtilityAI_Hex.au3:754`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_MindFreeze(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:759`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")


def CanUse_IcePrison() -> Any:
    """``UtilityAI_Hex.au3:768`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_IcePrison(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:773`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsMoving")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_IceSpikes() -> Any:
    """``UtilityAI_Hex.au3:784`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_IceSpikes(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:789`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, 1320, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_FrozenBurst() -> Any:
    """``UtilityAI_Hex.au3:798`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_FrozenBurst(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:803`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ShardStorm() -> Any:
    """``UtilityAI_Hex.au3:812`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_ShardStorm(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:817`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsMoving")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_LightningStrike() -> Any:
    """``UtilityAI_Hex.au3:828`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_LightningStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:833`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_GlimmeringMark() -> Any:
    """``UtilityAI_Hex.au3:842`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_GlimmeringMark(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:847`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_DeepFreeze() -> Any:
    """``UtilityAI_Hex.au3:852`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_DeepFreeze(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:857`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_AREA, "UAI_Filter_IsLivingEnemy")


def CanUse_BlurredVision() -> Any:
    """``UtilityAI_Hex.au3:866`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_BlurredVision(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:871`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, 1320, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_ScourgeHealing() -> Any:
    """``UtilityAI_Hex.au3:880`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_ScourgeHealing(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:885`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_ScourgeSacrifice() -> Any:
    """``UtilityAI_Hex.au3:894`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_ScourgeSacrifice(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:899`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, 1320, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_Pacifism() -> Any:
    """``UtilityAI_Hex.au3:908`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_Pacifism(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:913`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsAttacking")


def CanUse_Amity() -> Any:
    """``UtilityAI_Hex.au3:922`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_Amity(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:927`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BurdenTotem() -> Any:
    """``UtilityAI_Hex.au3:936`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_BurdenTotem(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:941`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CrystalHaze() -> Any:
    """``UtilityAI_Hex.au3:950`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_CrystalHaze(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:955`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_CrystalBonds() -> Any:
    """``UtilityAI_Hex.au3:964`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_CrystalBonds(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:969`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsEnchanted")


def CanUse_OracleLink() -> Any:
    """``UtilityAI_Hex.au3:978`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_OracleLink(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:983`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SpontaneousCombustion() -> Any:
    """``UtilityAI_Hex.au3:992`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_SpontaneousCombustion(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:997`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MarkOfInsecurity() -> Any:
    """``UtilityAI_Hex.au3:1006`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_MarkOfInsecurity(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1011`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_WailOfDoom() -> Any:
    """``UtilityAI_Hex.au3:1020`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_WailOfDoom(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1025`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")


def CanUse_MarkOfDeath() -> Any:
    """``UtilityAI_Hex.au3:1034`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_MarkOfDeath(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1039`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_EnduringToxin() -> Any:
    """``UtilityAI_Hex.au3:1048`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_EnduringToxin(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1053`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsMoving")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_ShroudOfSilence() -> Any:
    """``UtilityAI_Hex.au3:1064`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_ShroudOfSilence(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1069`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")


def CanUse_ExposeDefenses() -> Any:
    """``UtilityAI_Hex.au3:1078`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_ExposeDefenses(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1083`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsAttacking")


def CanUse_PowerLeech() -> Any:
    """``UtilityAI_Hex.au3:1092`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_PowerLeech(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1097`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")


def CanUse_ArcaneLanguor() -> Any:
    """``UtilityAI_Hex.au3:1106`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_ArcaneLanguor(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1111`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")


def CanUse_ReapersMark1() -> Any:
    """``UtilityAI_Hex.au3:1120`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_ReapersMark1(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1125`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_Shatterstone() -> Any:
    """``UtilityAI_Hex.au3:1134`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_Shatterstone(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1139`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_ScorpionWire() -> Any:
    """``UtilityAI_Hex.au3:1148`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_ScorpionWire(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1153`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_MirroredStance() -> Any:
    """``UtilityAI_Hex.au3:1162`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_MirroredStance(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1167`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_Depravity() -> Any:
    """``UtilityAI_Hex.au3:1176`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_Depravity(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1181`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_IcyVeins() -> Any:
    """``UtilityAI_Hex.au3:1190`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_IcyVeins(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1195`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_WeakenKnees() -> Any:
    """``UtilityAI_Hex.au3:1204`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_WeakenKnees(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1209`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsMoving")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_SiphonStrength() -> Any:
    """``UtilityAI_Hex.au3:1220`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_SiphonStrength(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1225`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsAttacking")


def CanUse_VileMiasma() -> Any:
    """``UtilityAI_Hex.au3:1234`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_VileMiasma(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1239`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_RecklessHaste() -> Any:
    """``UtilityAI_Hex.au3:1248`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_RecklessHaste(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1253`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, 1320, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_BloodBond() -> Any:
    """``UtilityAI_Hex.au3:1262`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_BloodBond(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1267`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, 1320, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_ConjureNightmare() -> Any:
    """``UtilityAI_Hex.au3:1276`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_ConjureNightmare(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1281`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_Dissipation() -> Any:
    """``UtilityAI_Hex.au3:1290`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_Dissipation(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1295`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_VisionsOfRegret() -> Any:
    """``UtilityAI_Hex.au3:1300`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_VisionsOfRegret(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1305`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, 1320, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_IllusionOfPain() -> Any:
    """``UtilityAI_Hex.au3:1314`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_IllusionOfPain(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1319`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_StolenSpeed() -> Any:
    """``UtilityAI_Hex.au3:1328`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_StolenSpeed(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1333`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, 1320, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_VocalMinority() -> Any:
    """``UtilityAI_Hex.au3:1342`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_VocalMinority(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1347`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_Overload() -> Any:
    """``UtilityAI_Hex.au3:1356`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_Overload(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1361`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_ImagesOfRemorse() -> Any:
    """``UtilityAI_Hex.au3:1372`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_ImagesOfRemorse(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1377`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsAttacking")


def CanUse_SharedBurden() -> Any:
    """``UtilityAI_Hex.au3:1386`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_SharedBurden(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1391`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_SoulBind() -> Any:
    """``UtilityAI_Hex.au3:1400`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_SoulBind(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1405`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_Lamentation() -> Any:
    """``UtilityAI_Hex.au3:1414`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_Lamentation(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1419`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_ShamefulFear() -> Any:
    """``UtilityAI_Hex.au3:1428`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_ShamefulFear(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1433`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsMoving")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_ShadowShroud() -> Any:
    """``UtilityAI_Hex.au3:1444`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_ShadowShroud(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1449`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_RisingBile() -> Any:
    """``UtilityAI_Hex.au3:1458`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_RisingBile(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1463`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_AREA, "UAI_Filter_IsLivingEnemy")


def CanUse_IcyShackles() -> Any:
    """``UtilityAI_Hex.au3:1472`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_IcyShackles(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1477`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsEnchanted")
    if l_i_Target != 0:
        return l_i_Target
    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsMoving")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_ShadowyBurden() -> Any:
    """``UtilityAI_Hex.au3:1490`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_ShadowyBurden(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1495`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsMoving")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_SiphonSpeed() -> Any:
    """``UtilityAI_Hex.au3:1506`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_SiphonSpeed(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1511`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsMoving")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_PowerFlux() -> Any:
    """``UtilityAI_Hex.au3:1522`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_PowerFlux(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1527`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")


def CanUse_MarkOfInstability() -> Any:
    """``UtilityAI_Hex.au3:1536`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_MarkOfInstability(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1541`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsAttacking")


def CanUse_Mistrust() -> Any:
    """``UtilityAI_Hex.au3:1550`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_Mistrust(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1555`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_TorchHex() -> Any:
    """``UtilityAI_Hex.au3:1564`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_TorchHex(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1569`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_TorchDegenerationHex() -> Any:
    """``UtilityAI_Hex.au3:1574`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_TorchDegenerationHex(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1579`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SnowDownTheShirt() -> Any:
    """``UtilityAI_Hex.au3:1584`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_SnowDownTheShirt(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1589`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_Icicles() -> Any:
    """``UtilityAI_Hex.au3:1598`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_Icicles(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1603`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, 1320, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_SeepingWound() -> Any:
    """``UtilityAI_Hex.au3:1612`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_SeepingWound(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1617`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsMoving")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_AssassinsPromise() -> Any:
    """``UtilityAI_Hex.au3:1628`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_AssassinsPromise(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1633`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_DarkPrison() -> Any:
    """``UtilityAI_Hex.au3:1642`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_DarkPrison(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1647`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsMoving")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_EmpathyKoro() -> Any:
    """``UtilityAI_Hex.au3:1658`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_EmpathyKoro(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1663`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsAttacking")


def CanUse_RecurringInsecurity() -> Any:
    """``UtilityAI_Hex.au3:1668`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_RecurringInsecurity(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1673`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_KitahsBurden() -> Any:
    """``UtilityAI_Hex.au3:1682`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_KitahsBurden(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1687`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsMoving")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_SpoilVictor() -> Any:
    """``UtilityAI_Hex.au3:1698`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_SpoilVictor(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1703`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsAttacking")


def CanUse_ShiversOfDread() -> Any:
    """``UtilityAI_Hex.au3:1712`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_ShiversOfDread(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1717`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_AshBlast() -> Any:
    """``UtilityAI_Hex.au3:1722`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_AshBlast(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1727`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, 1320, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_SmolderingEmbers() -> Any:
    """``UtilityAI_Hex.au3:1736`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_SmolderingEmbers(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1741`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_TeinaisPrison() -> Any:
    """``UtilityAI_Hex.au3:1750`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_TeinaisPrison(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1755`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsMoving")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_MirrorOfIce() -> Any:
    """``UtilityAI_Hex.au3:1766`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_MirrorOfIce(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1771`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_StarShards() -> Any:
    """``UtilityAI_Hex.au3:1780`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_StarShards(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1785`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DulledWeapon() -> Any:
    """``UtilityAI_Hex.au3:1795`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_DulledWeapon(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1800`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, 1320, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_BindingChains() -> Any:
    """``UtilityAI_Hex.au3:1809`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_BindingChains(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1814`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_PainfulBond() -> Any:
    """``UtilityAI_Hex.au3:1823`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_PainfulBond(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1828`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, 1320, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_Meekness() -> Any:
    """``UtilityAI_Hex.au3:1837`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_Meekness(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1842`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_AREA, "UAI_Filter_IsLivingEnemy")


def CanUse_SuicidalImpulse() -> Any:
    """``UtilityAI_Hex.au3:1851`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_SuicidalImpulse(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1856`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_WastrelsDemise() -> Any:
    """``UtilityAI_Hex.au3:1865`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_WastrelsDemise(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1870`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_Frustration() -> Any:
    """``UtilityAI_Hex.au3:1881`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_Frustration(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1886`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")


def CanUse_EtherPhantom() -> Any:
    """``UtilityAI_Hex.au3:1895`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_EtherPhantom(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1900`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")


def CanUse_WebOfDisruption() -> Any:
    """``UtilityAI_Hex.au3:1909`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_WebOfDisruption(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1914`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")


def CanUse_EnchantersConundrum() -> Any:
    """``UtilityAI_Hex.au3:1923`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_EnchantersConundrum(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1928`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, 1320, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_UlcerousLungs() -> Any:
    """``UtilityAI_Hex.au3:1937`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_UlcerousLungs(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1942`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_MarkOfFury() -> Any:
    """``UtilityAI_Hex.au3:1951`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_MarkOfFury(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1956`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsAttacking")


def CanUse_RecurringScourge() -> Any:
    """``UtilityAI_Hex.au3:1965`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_RecurringScourge(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1970`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_CorruptEnchantment() -> Any:
    """``UtilityAI_Hex.au3:1975`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_CorruptEnchantment(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1980`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsEnchanted")


def CanUse_ChillingWinds() -> Any:
    """``UtilityAI_Hex.au3:1989`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_ChillingWinds(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:1994`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, 1320, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_FreezingGust() -> Any:
    """``UtilityAI_Hex.au3:2003`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_FreezingGust(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2008`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsMoving")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_ScourgeEnchantment() -> Any:
    """``UtilityAI_Hex.au3:2019`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_ScourgeEnchantment(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2024`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_VialOfPurifiedWater() -> Any:
    """``UtilityAI_Hex.au3:2033`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_VialOfPurifiedWater(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2038`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsHarbingers")


def CanUse_CorsairsNet() -> Any:
    """``UtilityAI_Hex.au3:2047`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_CorsairsNet(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2052`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_AREA, "UAI_Filter_IsLivingEnemy")


def CanUse_LastRitesOfTorment() -> Any:
    """``UtilityAI_Hex.au3:2061`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_LastRitesOfTorment(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2066`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_EnchantmentCollapse() -> Any:
    """``UtilityAI_Hex.au3:2071`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_EnchantmentCollapse(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2076`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsEnchanted")


def CanUse_CallOfSacrifice() -> Any:
    """``UtilityAI_Hex.au3:2085`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_CallOfSacrifice(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2090`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_RenewingSurge() -> Any:
    """``UtilityAI_Hex.au3:2099`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    if UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_CurrentEnergy) > 20:
        return False
    return True


def BestTarget_RenewingSurge(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2105`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentHighest(-2, 1320, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_HiddenCaltrops() -> Any:
    """``UtilityAI_Hex.au3:2114`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_HiddenCaltrops(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2119`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsMoving")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_AuguryOfDeath() -> Any:
    """``UtilityAI_Hex.au3:2130`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_AuguryOfDeath(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2135`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_ShadowPrison() -> Any:
    """``UtilityAI_Hex.au3:2140`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_ShadowPrison(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2145`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsMoving")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_PriceOfPride() -> Any:
    """``UtilityAI_Hex.au3:2156`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_PriceOfPride(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2161`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")


def CanUse_AirOfDisenchantment() -> Any:
    """``UtilityAI_Hex.au3:2170`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_AirOfDisenchantment(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2175`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_DefendersZeal() -> Any:
    """``UtilityAI_Hex.au3:2184`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_DefendersZeal(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2189`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsAttacking")


def CanUse_WordsOfMadnessQwytzylkak() -> Any:
    """``UtilityAI_Hex.au3:2198`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_WordsOfMadnessQwytzylkak(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2203`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MadnessDart() -> Any:
    """``UtilityAI_Hex.au3:2208`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_MadnessDart(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2213`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_BondsOfTorment() -> Any:
    """``UtilityAI_Hex.au3:2218`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_BondsOfTorment(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2223`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_EtherNightmareLuxon() -> Any:
    """``UtilityAI_Hex.au3:2232`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_EtherNightmareLuxon(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2237`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_SumOfAllFears() -> Any:
    """``UtilityAI_Hex.au3:2242`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_SumOfAllFears(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2247`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsMoving")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_Cacophony() -> Any:
    """``UtilityAI_Hex.au3:2258`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_Cacophony(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2263`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_WintersEmbrace() -> Any:
    """``UtilityAI_Hex.au3:2272`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_WintersEmbrace(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2277`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsMoving")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_EarthenShackles() -> Any:
    """``UtilityAI_Hex.au3:2288`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_EarthenShackles(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2293`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_ShadowFang() -> Any:
    """``UtilityAI_Hex.au3:2302`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_ShadowFang(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2307`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_CalculatedRisk() -> Any:
    """``UtilityAI_Hex.au3:2316`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_CalculatedRisk(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2321`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsAttacking")


def CanUse_ShrinkingArmor() -> Any:
    """``UtilityAI_Hex.au3:2330`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_ShrinkingArmor(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2335`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_WanderingEye() -> Any:
    """``UtilityAI_Hex.au3:2344`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_WanderingEye(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2349`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, 1320, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_PutridBile() -> Any:
    """``UtilityAI_Hex.au3:2358`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_PutridBile(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2363`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_SnaringWeb() -> Any:
    """``UtilityAI_Hex.au3:2372`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_SnaringWeb(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2377`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_WurmBile() -> Any:
    """``UtilityAI_Hex.au3:2386`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_WurmBile(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2391`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_EtherNightmareKurzick() -> Any:
    """``UtilityAI_Hex.au3:2400`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_EtherNightmareKurzick(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2405`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_SpiritWorldRetreat() -> Any:
    """``UtilityAI_Hex.au3:2410`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_SpiritWorldRetreat(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2415`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ConfusingImages() -> Any:
    """``UtilityAI_Hex.au3:2424`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_ConfusingImages(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2429`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")


def CanUse_DefileDefenses() -> Any:
    """``UtilityAI_Hex.au3:2438`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_DefileDefenses(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2443`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsAttacking")


def CanUse_Atrophy() -> Any:
    """``UtilityAI_Hex.au3:2452`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_Atrophy(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2457`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockGlyphDestabilization() -> Any:
    """``UtilityAI_Hex.au3:2466`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_PolymockGlyphDestabilization(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2471`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockMindWreck() -> Any:
    """``UtilityAI_Hex.au3:2476`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_PolymockMindWreck(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2481`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")


def CanUse_PolymockRisingBile() -> Any:
    """``UtilityAI_Hex.au3:2486`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_PolymockRisingBile(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2491`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_AREA, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockGlyphFreeze() -> Any:
    """``UtilityAI_Hex.au3:2496`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_PolymockGlyphFreeze(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2501`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_AREA, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockCalculatedRisk() -> Any:
    """``UtilityAI_Hex.au3:2506`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_PolymockCalculatedRisk(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2511`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsAttacking")


def CanUse_PolymockRecurringInsecurity() -> Any:
    """``UtilityAI_Hex.au3:2516`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_PolymockRecurringInsecurity(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2521`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockBackfire() -> Any:
    """``UtilityAI_Hex.au3:2526`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_PolymockBackfire(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2531`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")


def CanUse_PolymockGuilt() -> Any:
    """``UtilityAI_Hex.au3:2536`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_PolymockGuilt(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2541`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")


def CanUse_PolymockPainfulBond() -> Any:
    """``UtilityAI_Hex.au3:2546`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_PolymockPainfulBond(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2551`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_PolymockMigraine() -> Any:
    """``UtilityAI_Hex.au3:2556`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_PolymockMigraine(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2561`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")


def CanUse_PolymockDiversion() -> Any:
    """``UtilityAI_Hex.au3:2566`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_PolymockDiversion(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2571`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")


def CanUse_PolymockIcyBonds() -> Any:
    """``UtilityAI_Hex.au3:2576`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_PolymockIcyBonds(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2581`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_CrystalSnare() -> Any:
    """``UtilityAI_Hex.au3:2586`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_CrystalSnare(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2591`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ParanoidIndignation() -> Any:
    """``UtilityAI_Hex.au3:2600`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_ParanoidIndignation(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2605`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ATouchOfGuile() -> Any:
    """``UtilityAI_Hex.au3:2614`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_ATouchOfGuile(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2619`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsAttacking")


def CanUse_AsuranScan() -> Any:
    """``UtilityAI_Hex.au3:2628`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_AsuranScan(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2633`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_PainInverter() -> Any:
    """``UtilityAI_Hex.au3:2642`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_PainInverter(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2647`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_TongueLash() -> Any:
    """``UtilityAI_Hex.au3:2652`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_TongueLash(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2657`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_Unreliable() -> Any:
    """``UtilityAI_Hex.au3:2666`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_Unreliable(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2671`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_TheMastersMark() -> Any:
    """``UtilityAI_Hex.au3:2676`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_TheMastersMark(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2681`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_TongueWhip() -> Any:
    """``UtilityAI_Hex.au3:2690`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_TongueWhip(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2695`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_Dishonorable() -> Any:
    """``UtilityAI_Hex.au3:2704`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_Dishonorable(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2709`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ReapersMark2() -> Any:
    """``UtilityAI_Hex.au3:2718`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_ReapersMark2(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2723`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_SpectralAgonySaulDalessio() -> Any:
    """``UtilityAI_Hex.au3:2733`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_SpectralAgonySaulDalessio(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2738`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_SharedBurdenGwen() -> Any:
    """``UtilityAI_Hex.au3:2743`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_SharedBurdenGwen(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2748`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_SumOfAllFearsGwen() -> Any:
    """``UtilityAI_Hex.au3:2753`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_SumOfAllFearsGwen(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2758`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsMoving")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_MindWrackPvp() -> Any:
    """``UtilityAI_Hex.au3:2765`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_MindWrackPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2770`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")


def CanUse_MadKingsFan() -> Any:
    """``UtilityAI_Hex.au3:2775`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_MadKingsFan(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2780`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_MindFreezePvp() -> Any:
    """``UtilityAI_Hex.au3:2789`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_MindFreezePvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2794`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")


def CanUse_TargetAcquisition() -> Any:
    """``UtilityAI_Hex.au3:2800`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_TargetAcquisition(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2805`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_NoxPhantom() -> Any:
    """``UtilityAI_Hex.au3:2814`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_NoxPhantom(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2819`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_FragilityPvp() -> Any:
    """``UtilityAI_Hex.au3:2834`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_FragilityPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2839`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, 1320, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")


def CanUse_WeightOfDhuumHex() -> Any:
    """``UtilityAI_Hex.au3:2845`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_WeightOfDhuumHex(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2850`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_EmpathyPvp() -> Any:
    """``UtilityAI_Hex.au3:2856`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_EmpathyPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2861`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsAttacking")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_CripplingAnguishPvp() -> Any:
    """``UtilityAI_Hex.au3:2869`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_CripplingAnguishPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2874`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsAttacking")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_PanicPvp() -> Any:
    """``UtilityAI_Hex.au3:2882`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_PanicPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2887`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, 1320, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_MigrainePvp() -> Any:
    """``UtilityAI_Hex.au3:2893`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_MigrainePvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2898`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsCaster")


def CanUse_SharedBurdenPvp() -> Any:
    """``UtilityAI_Hex.au3:2904`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_SharedBurdenPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2909`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_NEARBY, "UAI_Filter_IsLivingEnemy")


def CanUse_StolenSpeedPvp() -> Any:
    """``UtilityAI_Hex.au3:2915`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_StolenSpeedPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2920`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_FrustrationPvp() -> Any:
    """``UtilityAI_Hex.au3:2925`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_FrustrationPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2930`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_MistrustPvp() -> Any:
    """``UtilityAI_Hex.au3:2935`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_MistrustPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2940`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_EnchantersConundrumPvp() -> Any:
    """``UtilityAI_Hex.au3:2945`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_EnchantersConundrumPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2950`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_WanderingEyePvp() -> Any:
    """``UtilityAI_Hex.au3:2955`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_WanderingEyePvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2960`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_CalculatedRiskPvp() -> Any:
    """``UtilityAI_Hex.au3:2965`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_CalculatedRiskPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2970`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_IsaiahsBalance() -> Any:
    """``UtilityAI_Hex.au3:2975`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_IsaiahsBalance(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2980`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_WastrelsDemisePvp() -> Any:
    """``UtilityAI_Hex.au3:2989`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_WastrelsDemisePvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:2994`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_SpoilVictorPvp() -> Any:
    """``UtilityAI_Hex.au3:2999`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_SpoilVictorPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:3004`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_VisionsOfRegretPvp() -> Any:
    """``UtilityAI_Hex.au3:3009`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_VisionsOfRegretPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:3014`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_PromiseOfDeath() -> Any:
    """``UtilityAI_Hex.au3:3019`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_PromiseOfDeath(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:3024`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_FeveredDreamsPvp() -> Any:
    """``UtilityAI_Hex.au3:3033`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_FeveredDreamsPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:3038`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_SkyNet() -> Any:
    """``UtilityAI_Hex.au3:3043`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_SkyNet(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:3048`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_IllusionOfPainPvp() -> Any:
    """``UtilityAI_Hex.au3:3057`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_IllusionOfPainPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:3062`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_WebOfDisruptionPvp() -> Any:
    """``UtilityAI_Hex.au3:3067`` -- transcribed from GwAu3's own body."""

    if Anti_Hex():
        return False
    return True


def BestTarget_WebOfDisruptionPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Hex.au3:3072`` -- transcribed from GwAu3's own body."""

    return 0


__all__ = [
    "BestTarget_ATouchOfGuile",
    "BestTarget_AirOfDisenchantment",
    "BestTarget_Amity",
    "BestTarget_ArcaneConundrum",
    "BestTarget_ArcaneLanguor",
    "BestTarget_AshBlast",
    "BestTarget_AssassinsPromise",
    "BestTarget_AsuranScan",
    "BestTarget_Atrophy",
    "BestTarget_AuguryOfDeath",
    "BestTarget_Backfire",
    "BestTarget_Barbs",
    "BestTarget_BindingChains",
    "BestTarget_BloodBond",
    "BestTarget_BlurredVision",
    "BestTarget_BondsOfTorment",
    "BestTarget_BurdenTotem",
    "BestTarget_Cacophony",
    "BestTarget_CalculatedRisk",
    "BestTarget_CalculatedRiskPvp",
    "BestTarget_CallOfSacrifice",
    "BestTarget_ChillingWinds",
    "BestTarget_Clumsiness",
    "BestTarget_ConfusingImages",
    "BestTarget_Confusion",
    "BestTarget_ConjureNightmare",
    "BestTarget_ConjurePhantasm",
    "BestTarget_CorruptEnchantment",
    "BestTarget_CorsairsNet",
    "BestTarget_CripplingAnguish",
    "BestTarget_CripplingAnguishPvp",
    "BestTarget_CrystalBonds",
    "BestTarget_CrystalHaze",
    "BestTarget_CrystalSnare",
    "BestTarget_DarkPrison",
    "BestTarget_DeepFreeze",
    "BestTarget_DefendersZeal",
    "BestTarget_DefileDefenses",
    "BestTarget_DefileFlesh",
    "BestTarget_Depravity",
    "BestTarget_Dishonorable",
    "BestTarget_Dissipation",
    "BestTarget_Diversion",
    "BestTarget_DulledWeapon",
    "BestTarget_EarthenShackles",
    "BestTarget_Empathy",
    "BestTarget_EmpathyKoro",
    "BestTarget_EmpathyPvp",
    "BestTarget_EnchantersConundrum",
    "BestTarget_EnchantersConundrumPvp",
    "BestTarget_EnchantmentCollapse",
    "BestTarget_EnduringToxin",
    "BestTarget_EtherLord",
    "BestTarget_EtherNightmareKurzick",
    "BestTarget_EtherNightmareLuxon",
    "BestTarget_EtherPhantom",
    "BestTarget_EtherealBurden",
    "BestTarget_ExposeDefenses",
    "BestTarget_Faintheartedness",
    "BestTarget_FeveredDreams",
    "BestTarget_FeveredDreamsPvp",
    "BestTarget_Fragility",
    "BestTarget_FragilityPvp",
    "BestTarget_FreezingGust",
    "BestTarget_FrozenBurst",
    "BestTarget_Frustration",
    "BestTarget_FrustrationPvp",
    "BestTarget_GlimmeringMark",
    "BestTarget_GraspingEarth",
    "BestTarget_Guilt",
    "BestTarget_HiddenCaltrops",
    "BestTarget_IcePrison",
    "BestTarget_IceSpikes",
    "BestTarget_Icicles",
    "BestTarget_IcyShackles",
    "BestTarget_IcyVeins",
    "BestTarget_Ignorance",
    "BestTarget_IllusionOfPain",
    "BestTarget_IllusionOfPainPvp",
    "BestTarget_ImagesOfRemorse",
    "BestTarget_ImaginedBurden",
    "BestTarget_IncendiaryBonds",
    "BestTarget_Ineptitude",
    "BestTarget_InsidiousParasite",
    "BestTarget_IsaiahsBalance",
    "BestTarget_KitahsBurden",
    "BestTarget_Lamentation",
    "BestTarget_LastRitesOfTorment",
    "BestTarget_LifeSiphon",
    "BestTarget_LifeTransfer",
    "BestTarget_LightningStrike",
    "BestTarget_LightningSurge",
    "BestTarget_LingeringCurse",
    "BestTarget_MadKingsFan",
    "BestTarget_MadnessDart",
    "BestTarget_Malaise",
    "BestTarget_MalignIntervention",
    "BestTarget_MarkOfDeath",
    "BestTarget_MarkOfFury",
    "BestTarget_MarkOfInsecurity",
    "BestTarget_MarkOfInstability",
    "BestTarget_MarkOfPain",
    "BestTarget_MarkOfRodgort",
    "BestTarget_MarkOfSubversion",
    "BestTarget_Meekness",
    "BestTarget_Migraine",
    "BestTarget_MigrainePvp",
    "BestTarget_MindFreeze",
    "BestTarget_MindFreezePvp",
    "BestTarget_MindWrack",
    "BestTarget_MindWrackPvp",
    "BestTarget_MirrorOfIce",
    "BestTarget_MirroredStance",
    "BestTarget_Mistrust",
    "BestTarget_MistrustPvp",
    "BestTarget_NoxPhantom",
    "BestTarget_OracleLink",
    "BestTarget_Overload",
    "BestTarget_Pacifism",
    "BestTarget_PainInverter",
    "BestTarget_PainfulBond",
    "BestTarget_Panic",
    "BestTarget_PanicPvp",
    "BestTarget_ParanoidIndignation",
    "BestTarget_ParasiticBond",
    "BestTarget_PhantomPain",
    "BestTarget_PolymockBackfire",
    "BestTarget_PolymockCalculatedRisk",
    "BestTarget_PolymockDiversion",
    "BestTarget_PolymockGlyphDestabilization",
    "BestTarget_PolymockGlyphFreeze",
    "BestTarget_PolymockGuilt",
    "BestTarget_PolymockIcyBonds",
    "BestTarget_PolymockMigraine",
    "BestTarget_PolymockMindWreck",
    "BestTarget_PolymockPainfulBond",
    "BestTarget_PolymockRecurringInsecurity",
    "BestTarget_PolymockRisingBile",
    "BestTarget_PowerFlux",
    "BestTarget_PowerLeech",
    "BestTarget_PriceOfFailure",
    "BestTarget_PriceOfPride",
    "BestTarget_PromiseOfDeath",
    "BestTarget_PutridBile",
    "BestTarget_ReapersMark1",
    "BestTarget_ReapersMark2",
    "BestTarget_RecklessHaste",
    "BestTarget_RecurringInsecurity",
    "BestTarget_RecurringScourge",
    "BestTarget_RenewingSurge",
    "BestTarget_RigorMortis",
    "BestTarget_RisingBile",
    "BestTarget_Rust",
    "BestTarget_ScorpionWire",
    "BestTarget_ScourgeEnchantment",
    "BestTarget_ScourgeHealing",
    "BestTarget_ScourgeSacrifice",
    "BestTarget_SeepingWound",
    "BestTarget_ShadowFang",
    "BestTarget_ShadowOfFear",
    "BestTarget_ShadowPrison",
    "BestTarget_ShadowShroud",
    "BestTarget_ShadowyBurden",
    "BestTarget_Shame",
    "BestTarget_ShamefulFear",
    "BestTarget_ShardStorm",
    "BestTarget_SharedBurden",
    "BestTarget_SharedBurdenGwen",
    "BestTarget_SharedBurdenPvp",
    "BestTarget_Shatterstone",
    "BestTarget_ShiversOfDread",
    "BestTarget_ShrinkingArmor",
    "BestTarget_ShroudOfSilence",
    "BestTarget_SiphonSpeed",
    "BestTarget_SiphonStrength",
    "BestTarget_SkyNet",
    "BestTarget_SmolderingEmbers",
    "BestTarget_SnaringWeb",
    "BestTarget_SnowDownTheShirt",
    "BestTarget_SoothingImages",
    "BestTarget_SoulBarbs",
    "BestTarget_SoulBind",
    "BestTarget_SoulLeech",
    "BestTarget_SpectralAgonySaulDalessio",
    "BestTarget_SpinalShivers",
    "BestTarget_SpiritOfFailure",
    "BestTarget_SpiritShackles",
    "BestTarget_SpiritWorldRetreat",
    "BestTarget_SpitefulSpirit",
    "BestTarget_SpoilVictor",
    "BestTarget_SpoilVictorPvp",
    "BestTarget_SpontaneousCombustion",
    "BestTarget_StarShards",
    "BestTarget_StolenSpeed",
    "BestTarget_StolenSpeedPvp",
    "BestTarget_Suffering",
    "BestTarget_SuicidalImpulse",
    "BestTarget_SumOfAllFears",
    "BestTarget_SumOfAllFearsGwen",
    "BestTarget_TargetAcquisition",
    "BestTarget_TeinaisPrison",
    "BestTarget_TheMastersMark",
    "BestTarget_TongueLash",
    "BestTarget_TongueWhip",
    "BestTarget_TorchDegenerationHex",
    "BestTarget_TorchHex",
    "BestTarget_UlcerousLungs",
    "BestTarget_Unreliable",
    "BestTarget_VialOfPurifiedWater",
    "BestTarget_VileMiasma",
    "BestTarget_VisionsOfRegret",
    "BestTarget_VisionsOfRegretPvp",
    "BestTarget_VocalMinority",
    "BestTarget_WailOfDoom",
    "BestTarget_WanderingEye",
    "BestTarget_WanderingEyePvp",
    "BestTarget_WastrelsDemise",
    "BestTarget_WastrelsDemisePvp",
    "BestTarget_WastrelsWorry",
    "BestTarget_WeakenKnees",
    "BestTarget_WebOfDisruption",
    "BestTarget_WebOfDisruptionPvp",
    "BestTarget_WeightOfDhuumHex",
    "BestTarget_WintersEmbrace",
    "BestTarget_Wither",
    "BestTarget_WordsOfMadnessQwytzylkak",
    "BestTarget_WurmBile",
    "CanUse_ATouchOfGuile",
    "CanUse_AirOfDisenchantment",
    "CanUse_Amity",
    "CanUse_ArcaneConundrum",
    "CanUse_ArcaneLanguor",
    "CanUse_AshBlast",
    "CanUse_AssassinsPromise",
    "CanUse_AsuranScan",
    "CanUse_Atrophy",
    "CanUse_AuguryOfDeath",
    "CanUse_Backfire",
    "CanUse_Barbs",
    "CanUse_BindingChains",
    "CanUse_BloodBond",
    "CanUse_BlurredVision",
    "CanUse_BondsOfTorment",
    "CanUse_BurdenTotem",
    "CanUse_Cacophony",
    "CanUse_CalculatedRisk",
    "CanUse_CalculatedRiskPvp",
    "CanUse_CallOfSacrifice",
    "CanUse_ChillingWinds",
    "CanUse_Clumsiness",
    "CanUse_ConfusingImages",
    "CanUse_Confusion",
    "CanUse_ConjureNightmare",
    "CanUse_ConjurePhantasm",
    "CanUse_CorruptEnchantment",
    "CanUse_CorsairsNet",
    "CanUse_CripplingAnguish",
    "CanUse_CripplingAnguishPvp",
    "CanUse_CrystalBonds",
    "CanUse_CrystalHaze",
    "CanUse_CrystalSnare",
    "CanUse_DarkPrison",
    "CanUse_DeepFreeze",
    "CanUse_DefendersZeal",
    "CanUse_DefileDefenses",
    "CanUse_DefileFlesh",
    "CanUse_Depravity",
    "CanUse_Dishonorable",
    "CanUse_Dissipation",
    "CanUse_Diversion",
    "CanUse_DulledWeapon",
    "CanUse_EarthenShackles",
    "CanUse_Empathy",
    "CanUse_EmpathyKoro",
    "CanUse_EmpathyPvp",
    "CanUse_EnchantersConundrum",
    "CanUse_EnchantersConundrumPvp",
    "CanUse_EnchantmentCollapse",
    "CanUse_EnduringToxin",
    "CanUse_EtherLord",
    "CanUse_EtherNightmareKurzick",
    "CanUse_EtherNightmareLuxon",
    "CanUse_EtherPhantom",
    "CanUse_EtherealBurden",
    "CanUse_ExposeDefenses",
    "CanUse_Faintheartedness",
    "CanUse_FeveredDreams",
    "CanUse_FeveredDreamsPvp",
    "CanUse_Fragility",
    "CanUse_FragilityPvp",
    "CanUse_FreezingGust",
    "CanUse_FrozenBurst",
    "CanUse_Frustration",
    "CanUse_FrustrationPvp",
    "CanUse_GlimmeringMark",
    "CanUse_GraspingEarth",
    "CanUse_Guilt",
    "CanUse_HiddenCaltrops",
    "CanUse_IcePrison",
    "CanUse_IceSpikes",
    "CanUse_Icicles",
    "CanUse_IcyShackles",
    "CanUse_IcyVeins",
    "CanUse_Ignorance",
    "CanUse_IllusionOfPain",
    "CanUse_IllusionOfPainPvp",
    "CanUse_ImagesOfRemorse",
    "CanUse_ImaginedBurden",
    "CanUse_IncendiaryBonds",
    "CanUse_Ineptitude",
    "CanUse_InsidiousParasite",
    "CanUse_IsaiahsBalance",
    "CanUse_KitahsBurden",
    "CanUse_Lamentation",
    "CanUse_LastRitesOfTorment",
    "CanUse_LifeSiphon",
    "CanUse_LifeTransfer",
    "CanUse_LightningStrike",
    "CanUse_LightningSurge",
    "CanUse_LingeringCurse",
    "CanUse_MadKingsFan",
    "CanUse_MadnessDart",
    "CanUse_Malaise",
    "CanUse_MalignIntervention",
    "CanUse_MarkOfDeath",
    "CanUse_MarkOfFury",
    "CanUse_MarkOfInsecurity",
    "CanUse_MarkOfInstability",
    "CanUse_MarkOfPain",
    "CanUse_MarkOfRodgort",
    "CanUse_MarkOfSubversion",
    "CanUse_Meekness",
    "CanUse_Migraine",
    "CanUse_MigrainePvp",
    "CanUse_MindFreeze",
    "CanUse_MindFreezePvp",
    "CanUse_MindWrack",
    "CanUse_MindWrackPvp",
    "CanUse_MirrorOfIce",
    "CanUse_MirroredStance",
    "CanUse_Mistrust",
    "CanUse_MistrustPvp",
    "CanUse_NoxPhantom",
    "CanUse_OracleLink",
    "CanUse_Overload",
    "CanUse_Pacifism",
    "CanUse_PainInverter",
    "CanUse_PainfulBond",
    "CanUse_Panic",
    "CanUse_PanicPvp",
    "CanUse_ParanoidIndignation",
    "CanUse_ParasiticBond",
    "CanUse_PhantomPain",
    "CanUse_PolymockBackfire",
    "CanUse_PolymockCalculatedRisk",
    "CanUse_PolymockDiversion",
    "CanUse_PolymockGlyphDestabilization",
    "CanUse_PolymockGlyphFreeze",
    "CanUse_PolymockGuilt",
    "CanUse_PolymockIcyBonds",
    "CanUse_PolymockMigraine",
    "CanUse_PolymockMindWreck",
    "CanUse_PolymockPainfulBond",
    "CanUse_PolymockRecurringInsecurity",
    "CanUse_PolymockRisingBile",
    "CanUse_PowerFlux",
    "CanUse_PowerLeech",
    "CanUse_PriceOfFailure",
    "CanUse_PriceOfPride",
    "CanUse_PromiseOfDeath",
    "CanUse_PutridBile",
    "CanUse_ReapersMark1",
    "CanUse_ReapersMark2",
    "CanUse_RecklessHaste",
    "CanUse_RecurringInsecurity",
    "CanUse_RecurringScourge",
    "CanUse_RenewingSurge",
    "CanUse_RigorMortis",
    "CanUse_RisingBile",
    "CanUse_Rust",
    "CanUse_ScorpionWire",
    "CanUse_ScourgeEnchantment",
    "CanUse_ScourgeHealing",
    "CanUse_ScourgeSacrifice",
    "CanUse_SeepingWound",
    "CanUse_ShadowFang",
    "CanUse_ShadowOfFear",
    "CanUse_ShadowPrison",
    "CanUse_ShadowShroud",
    "CanUse_ShadowyBurden",
    "CanUse_Shame",
    "CanUse_ShamefulFear",
    "CanUse_ShardStorm",
    "CanUse_SharedBurden",
    "CanUse_SharedBurdenGwen",
    "CanUse_SharedBurdenPvp",
    "CanUse_Shatterstone",
    "CanUse_ShiversOfDread",
    "CanUse_ShrinkingArmor",
    "CanUse_ShroudOfSilence",
    "CanUse_SiphonSpeed",
    "CanUse_SiphonStrength",
    "CanUse_SkyNet",
    "CanUse_SmolderingEmbers",
    "CanUse_SnaringWeb",
    "CanUse_SnowDownTheShirt",
    "CanUse_SoothingImages",
    "CanUse_SoulBarbs",
    "CanUse_SoulBind",
    "CanUse_SoulLeech",
    "CanUse_SpectralAgonySaulDalessio",
    "CanUse_SpinalShivers",
    "CanUse_SpiritOfFailure",
    "CanUse_SpiritShackles",
    "CanUse_SpiritWorldRetreat",
    "CanUse_SpitefulSpirit",
    "CanUse_SpoilVictor",
    "CanUse_SpoilVictorPvp",
    "CanUse_SpontaneousCombustion",
    "CanUse_StarShards",
    "CanUse_StolenSpeed",
    "CanUse_StolenSpeedPvp",
    "CanUse_Suffering",
    "CanUse_SuicidalImpulse",
    "CanUse_SumOfAllFears",
    "CanUse_SumOfAllFearsGwen",
    "CanUse_TargetAcquisition",
    "CanUse_TeinaisPrison",
    "CanUse_TheMastersMark",
    "CanUse_TongueLash",
    "CanUse_TongueWhip",
    "CanUse_TorchDegenerationHex",
    "CanUse_TorchHex",
    "CanUse_UlcerousLungs",
    "CanUse_Unreliable",
    "CanUse_VialOfPurifiedWater",
    "CanUse_VileMiasma",
    "CanUse_VisionsOfRegret",
    "CanUse_VisionsOfRegretPvp",
    "CanUse_VocalMinority",
    "CanUse_WailOfDoom",
    "CanUse_WanderingEye",
    "CanUse_WanderingEyePvp",
    "CanUse_WastrelsDemise",
    "CanUse_WastrelsDemisePvp",
    "CanUse_WastrelsWorry",
    "CanUse_WeakenKnees",
    "CanUse_WebOfDisruption",
    "CanUse_WebOfDisruptionPvp",
    "CanUse_WeightOfDhuumHex",
    "CanUse_WintersEmbrace",
    "CanUse_Wither",
    "CanUse_WordsOfMadnessQwytzylkak",
    "CanUse_WurmBile",
]
