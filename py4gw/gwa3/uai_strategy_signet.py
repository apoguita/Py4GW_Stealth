"""GwAu3's ``UtilityAI_Signet.au3`` strategy functions, transcribed.

**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_strategies.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

`py4gw/gwa3/uai_best_target_cache.py` and `uai_can_use_cache.py` answer a slot's skill id with the *name*
of one of these functions; GwAu3's engine resolves that name with AutoIt's ``Call``, and this layer
resolves it the same way. So these are the strategy half of the ranking: which agent a skill wants, or
which guard lets it be used at all. **170 of this file's 170 are transcribed and 0
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
from .uai_agent import (
    UAI_GetAgentInfoByID,
    UAI_GetPlayerInfo,
)
from .uai_effects import UAI_PlayerHasEffect
from .uai_get_agent import (
    UAI_FindAgentByPlayerNumber,
    UAI_GetAgentLowest,
    UAI_GetBestAOETarget,
    UAI_GetBestSingleTarget,
    UAI_GetBestTargetByConditionCount,
    UAI_GetNearestAgent,
)


def CanUse_SignetOfCapture() -> Any:
    """``UtilityAI_Signet.au3:8`` -- transcribed from GwAu3's own body."""

    return False


def BestTarget_SignetOfCapture(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:12`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AntidoteSignet() -> Any:
    """``UtilityAI_Signet.au3:20`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_AntidoteSignet(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:25`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ArchersSignet() -> Any:
    """``UtilityAI_Signet.au3:33`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_ArchersSignet(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:38`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BaneSignet() -> Any:
    """``UtilityAI_Signet.au3:42`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_BaneSignet(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:47`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsAttacking")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_BarbedSignet() -> Any:
    """``UtilityAI_Signet.au3:58`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_BarbedSignet(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:63`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_BarbedSignetPvp() -> Any:
    """``UtilityAI_Signet.au3:71`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_BarbedSignetPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:76`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BlessedSignet() -> Any:
    """``UtilityAI_Signet.au3:80`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_BlessedSignet(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:85`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BoonSignet() -> Any:
    """``UtilityAI_Signet.au3:93`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_BoonSignet(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:98`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_CandyCornStrike() -> Any:
    """``UtilityAI_Signet.au3:106`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_CandyCornStrike(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:111`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_CastigationSignet() -> Any:
    """``UtilityAI_Signet.au3:119`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_CastigationSignet(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:124`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsAttacking")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_CastigationSignetSaulDalessio() -> Any:
    """``UtilityAI_Signet.au3:134`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_CastigationSignetSaulDalessio(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:139`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_CauterySignet() -> Any:
    """``UtilityAI_Signet.au3:143`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_CauterySignet(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:148`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DeathPactSignet() -> Any:
    """``UtilityAI_Signet.au3:156`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_CURSE_OF_DHUUM) or UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_FROZEN_SOIL):
        return False
    return True


def BestTarget_DeathPactSignet(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:162`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_DeathPactSignetPvp() -> Any:
    """``UtilityAI_Signet.au3:170`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_CURSE_OF_DHUUM) or UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_FROZEN_SOIL):
        return False
    return True


def BestTarget_DeathPactSignetPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:176`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_DolyakSignet() -> Any:
    """``UtilityAI_Signet.au3:180`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_DolyakSignet(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:185`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_EtherSignet() -> Any:
    """``UtilityAI_Signet.au3:193`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_EtherSignet(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:198`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_GlowingSignet() -> Any:
    """``UtilityAI_Signet.au3:206`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_GlowingSignet(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:211`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_HexEaterSignet() -> Any:
    """``UtilityAI_Signet.au3:219`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_HexEaterSignet(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:224`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_HealingSignet() -> Any:
    """``UtilityAI_Signet.au3:232`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    if UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_HP) > 0.80:
        return False
    return True


def BestTarget_HealingSignet(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:238`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_KeystoneSignet() -> Any:
    """``UtilityAI_Signet.au3:246`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_KeystoneSignet(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:251`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_LeechSignet() -> Any:
    """``UtilityAI_Signet.au3:259`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_LeechSignet(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:264`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_LightbringerSignet() -> Any:
    """``UtilityAI_Signet.au3:272`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_LightbringerSignet(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:277`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PlagueSignet() -> Any:
    """``UtilityAI_Signet.au3:285`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_PlagueSignet(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:290`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_PoisonTipSignet() -> Any:
    """``UtilityAI_Signet.au3:298`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_PoisonTipSignet(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:303`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PolymockBaneSignet() -> Any:
    """``UtilityAI_Signet.au3:311`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_PolymockBaneSignet(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:316`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_PolymockEtherSignet() -> Any:
    """``UtilityAI_Signet.au3:324`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_PolymockEtherSignet(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:329`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PolymockSignetOfClumsiness() -> Any:
    """``UtilityAI_Signet.au3:337`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_PolymockSignetOfClumsiness(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:342`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_PurgeSignet() -> Any:
    """``UtilityAI_Signet.au3:350`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_PurgeSignet(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:355`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_RemedySignet() -> Any:
    """``UtilityAI_Signet.au3:363`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_RemedySignet(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:368`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SadistsSignet() -> Any:
    """``UtilityAI_Signet.au3:376`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SadistsSignet(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:381`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_SignetOfAggression() -> Any:
    """``UtilityAI_Signet.au3:389`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfAggression(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:394`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SignetOfAgony() -> Any:
    """``UtilityAI_Signet.au3:402`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfAgony(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:407`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SignetOfAgonyPvp() -> Any:
    """``UtilityAI_Signet.au3:415`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfAgonyPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:420`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SignetOfBinding() -> Any:
    """``UtilityAI_Signet.au3:424`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfBinding(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:429`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_SignetOfClumsiness() -> Any:
    """``UtilityAI_Signet.au3:437`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfClumsiness(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:442`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsAttacking")


def CanUse_SignetOfClumsinessPvp() -> Any:
    """``UtilityAI_Signet.au3:450`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfClumsinessPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:455`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_SignetOfCorruptionKurzick() -> Any:
    """``UtilityAI_Signet.au3:459`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfCorruptionKurzick(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:464`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_SignetOfCorruptionLuxon() -> Any:
    """``UtilityAI_Signet.au3:468`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfCorruptionLuxon(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:473`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_SignetOfCreation() -> Any:
    """``UtilityAI_Signet.au3:477`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfCreation(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:482`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SignetOfCreationPvp() -> Any:
    """``UtilityAI_Signet.au3:490`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfCreationPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:495`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SignetOfDeadlyCorruption() -> Any:
    """``UtilityAI_Signet.au3:499`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfDeadlyCorruption(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:504`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestTargetByConditionCount(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsLastStrikeIsDual")


def CanUse_SignetOfDeadlyCorruptionPvp() -> Any:
    """``UtilityAI_Signet.au3:512`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfDeadlyCorruptionPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:517`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestTargetByConditionCount(-2, a_f_AggroRange, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsLastStrikeIsDual")


def CanUse_SignetOfDevotion() -> Any:
    """``UtilityAI_Signet.au3:521`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfDevotion(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:526`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_SignetOfDisenchantment() -> Any:
    """``UtilityAI_Signet.au3:534`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfDisenchantment(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:539`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_SignetOfDisruption() -> Any:
    """``UtilityAI_Signet.au3:547`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfDisruption(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:552`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_SignetOfDistraction() -> Any:
    """``UtilityAI_Signet.au3:560`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfDistraction(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:565`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_SignetOfGhostlyMight() -> Any:
    """``UtilityAI_Signet.au3:573`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfGhostlyMight(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:578`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SignetOfGhostlyMightPvp() -> Any:
    """``UtilityAI_Signet.au3:586`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfGhostlyMightPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:591`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_SignetOfHumility() -> Any:
    """``UtilityAI_Signet.au3:595`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfHumility(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:600`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_SignetOfIllusions() -> Any:
    """``UtilityAI_Signet.au3:608`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfIllusions(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:613`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SignetOfInfection() -> Any:
    """``UtilityAI_Signet.au3:621`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfInfection(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:626`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_SignetOfJudgment() -> Any:
    """``UtilityAI_Signet.au3:634`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfJudgment(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:639`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_SignetOfJudgmentPvp() -> Any:
    """``UtilityAI_Signet.au3:647`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfJudgmentPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:652`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_SignetOfLostSouls() -> Any:
    """``UtilityAI_Signet.au3:656`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfLostSouls(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:661`` -- transcribed from GwAu3's own body."""

    return UAI_GetAgentLowest(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsBelow50HP")


def CanUse_SignetOfMalice() -> Any:
    """``UtilityAI_Signet.au3:669`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfMalice(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:674`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_SignetOfMidnight() -> Any:
    """``UtilityAI_Signet.au3:682`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfMidnight(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:687`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_SignetOfMysticSpeed() -> Any:
    """``UtilityAI_Signet.au3:695`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfMysticSpeed(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:700`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SignetOfMysticWrath() -> Any:
    """``UtilityAI_Signet.au3:708`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfMysticWrath(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:713`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_SignetOfPiousLight() -> Any:
    """``UtilityAI_Signet.au3:721`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfPiousLight(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:726`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_SignetOfPiousRestraint() -> Any:
    """``UtilityAI_Signet.au3:734`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfPiousRestraint(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:739`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_SignetOfPiousRestraintPvp() -> Any:
    """``UtilityAI_Signet.au3:747`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfPiousRestraintPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:752`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_SignetOfRage() -> Any:
    """``UtilityAI_Signet.au3:756`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfRage(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:761`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_SignetOfRecall() -> Any:
    """``UtilityAI_Signet.au3:769`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfRecall(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:774`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SignetOfRejuvenation() -> Any:
    """``UtilityAI_Signet.au3:782`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfRejuvenation(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:787`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_SignetOfRemoval() -> Any:
    """``UtilityAI_Signet.au3:795`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfRemoval(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:800`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_ResurrectionSignet() -> Any:
    """``UtilityAI_Signet.au3:808`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_CURSE_OF_DHUUM) or UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_FROZEN_SOIL):
        return False
    return True


def BestTarget_ResurrectionSignet(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:814`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsDeadAlly")


def CanUse_SignetOfReturn() -> Any:
    """``UtilityAI_Signet.au3:822`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_CURSE_OF_DHUUM) or UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_FROZEN_SOIL):
        return False
    return True


def BestTarget_SignetOfReturn(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:828`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_SignetOfReturnPvp() -> Any:
    """``UtilityAI_Signet.au3:836`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_CURSE_OF_DHUUM) or UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_FROZEN_SOIL):
        return False
    return True


def BestTarget_SignetOfReturnPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:842`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_SignetOfShadows() -> Any:
    """``UtilityAI_Signet.au3:846`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfShadows(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:851`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_SignetOfSorrow() -> Any:
    """``UtilityAI_Signet.au3:859`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfSorrow(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:864`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_SignetOfSpirits() -> Any:
    """``UtilityAI_Signet.au3:872`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    l_i_Spirit1 = UAI_FindAgentByPlayerNumber(4229, -2, 5000, "UAI_Filter_IsControlledSpirit")
    l_i_Spirit2 = UAI_FindAgentByPlayerNumber(4230, -2, 5000, "UAI_Filter_IsControlledSpirit")
    l_i_Spirit3 = UAI_FindAgentByPlayerNumber(4231, -2, 5000, "UAI_Filter_IsControlledSpirit")
    if l_i_Spirit1 != 0 and l_i_Spirit2 != 0 and l_i_Spirit3 != 0:
        if UAI_GetAgentInfoByID(l_i_Spirit1, _constants.GC_UAI_AGENT_HP) < 0.20 or UAI_GetAgentInfoByID(l_i_Spirit2, _constants.GC_UAI_AGENT_HP) < 0.20 or UAI_GetAgentInfoByID(l_i_Spirit3, _constants.GC_UAI_AGENT_HP) < 0.20:
            return True
        return False

        return True


def BestTarget_SignetOfSpirits(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:887`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SignetOfSpiritsPvp() -> Any:
    """``UtilityAI_Signet.au3:895`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfSpiritsPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:900`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SignetOfStamina() -> Any:
    """``UtilityAI_Signet.au3:904`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfStamina(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:909`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SignetOfStrength() -> Any:
    """``UtilityAI_Signet.au3:917`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfStrength(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:922`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SignetOfSuffering() -> Any:
    """``UtilityAI_Signet.au3:930`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfSuffering(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:935`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SignetOfSynergy() -> Any:
    """``UtilityAI_Signet.au3:943`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfSynergy(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:948`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_SignetOfTheUnseen() -> Any:
    """``UtilityAI_Signet.au3:956`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfTheUnseen(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:961`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_SignetOfToxicShock() -> Any:
    """``UtilityAI_Signet.au3:969`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfToxicShock(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:974`` -- transcribed from GwAu3's own body."""

    return UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsPoisoned")


def CanUse_SignetOfTwilight() -> Any:
    """``UtilityAI_Signet.au3:982`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfTwilight(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:987`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_SignetOfWeariness() -> Any:
    """``UtilityAI_Signet.au3:995`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_SignetOfWeariness(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:1000`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_SunspearRebirthSignet() -> Any:
    """``UtilityAI_Signet.au3:1008`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_CURSE_OF_DHUUM) or UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_FROZEN_SOIL):
        return False
    return True


def BestTarget_SunspearRebirthSignet(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:1014`` -- transcribed from GwAu3's own body."""

    return UAI_GetNearestAgent(-2, a_f_AggroRange, "UAI_Filter_IsDeadAlly")


def CanUse_TryptophanSignet() -> Any:
    """``UtilityAI_Signet.au3:1022`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_TryptophanSignet(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:1027`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy|-UAI_Filter_IsCaster")
    if l_i_Target != 0:
        return l_i_Target
    l_i_Target = UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")
    if l_i_Target != 0:
        return l_i_Target


def CanUse_UnnaturalSignet() -> Any:
    """``UtilityAI_Signet.au3:1039`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_UnnaturalSignet(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:1044`` -- transcribed from GwAu3's own body."""

    l_i_Target = UAI_GetBestAOETarget(-2, a_f_AggroRange, _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsHexedOrEnchanted")
    if l_i_Target != 0:
        return l_i_Target
    l_i_Target = UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsHexedOrEnchanted")
    if l_i_Target != 0:
        return l_i_Target
    return UAI_GetBestSingleTarget(-2, a_f_AggroRange, _constants.GC_UAI_AGENT_HP, "UAI_Filter_IsLivingEnemy")


def CanUse_UnnaturalSignetPvp() -> Any:
    """``UtilityAI_Signet.au3:1062`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_UnnaturalSignetPvp(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:1067`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_UnnaturalSignetSaulDalessio() -> Any:
    """``UtilityAI_Signet.au3:1071`` -- transcribed from GwAu3's own body."""

    if Anti_Signet():
        return False
    return True


def BestTarget_UnnaturalSignetSaulDalessio(a_f_AggroRange) -> Any:
    """``UtilityAI_Signet.au3:1076`` -- transcribed from GwAu3's own body."""

    return 0


__all__ = [
    "BestTarget_AntidoteSignet",
    "BestTarget_ArchersSignet",
    "BestTarget_BaneSignet",
    "BestTarget_BarbedSignet",
    "BestTarget_BarbedSignetPvp",
    "BestTarget_BlessedSignet",
    "BestTarget_BoonSignet",
    "BestTarget_CandyCornStrike",
    "BestTarget_CastigationSignet",
    "BestTarget_CastigationSignetSaulDalessio",
    "BestTarget_CauterySignet",
    "BestTarget_DeathPactSignet",
    "BestTarget_DeathPactSignetPvp",
    "BestTarget_DolyakSignet",
    "BestTarget_EtherSignet",
    "BestTarget_GlowingSignet",
    "BestTarget_HealingSignet",
    "BestTarget_HexEaterSignet",
    "BestTarget_KeystoneSignet",
    "BestTarget_LeechSignet",
    "BestTarget_LightbringerSignet",
    "BestTarget_PlagueSignet",
    "BestTarget_PoisonTipSignet",
    "BestTarget_PolymockBaneSignet",
    "BestTarget_PolymockEtherSignet",
    "BestTarget_PolymockSignetOfClumsiness",
    "BestTarget_PurgeSignet",
    "BestTarget_RemedySignet",
    "BestTarget_ResurrectionSignet",
    "BestTarget_SadistsSignet",
    "BestTarget_SignetOfAggression",
    "BestTarget_SignetOfAgony",
    "BestTarget_SignetOfAgonyPvp",
    "BestTarget_SignetOfBinding",
    "BestTarget_SignetOfCapture",
    "BestTarget_SignetOfClumsiness",
    "BestTarget_SignetOfClumsinessPvp",
    "BestTarget_SignetOfCorruptionKurzick",
    "BestTarget_SignetOfCorruptionLuxon",
    "BestTarget_SignetOfCreation",
    "BestTarget_SignetOfCreationPvp",
    "BestTarget_SignetOfDeadlyCorruption",
    "BestTarget_SignetOfDeadlyCorruptionPvp",
    "BestTarget_SignetOfDevotion",
    "BestTarget_SignetOfDisenchantment",
    "BestTarget_SignetOfDisruption",
    "BestTarget_SignetOfDistraction",
    "BestTarget_SignetOfGhostlyMight",
    "BestTarget_SignetOfGhostlyMightPvp",
    "BestTarget_SignetOfHumility",
    "BestTarget_SignetOfIllusions",
    "BestTarget_SignetOfInfection",
    "BestTarget_SignetOfJudgment",
    "BestTarget_SignetOfJudgmentPvp",
    "BestTarget_SignetOfLostSouls",
    "BestTarget_SignetOfMalice",
    "BestTarget_SignetOfMidnight",
    "BestTarget_SignetOfMysticSpeed",
    "BestTarget_SignetOfMysticWrath",
    "BestTarget_SignetOfPiousLight",
    "BestTarget_SignetOfPiousRestraint",
    "BestTarget_SignetOfPiousRestraintPvp",
    "BestTarget_SignetOfRage",
    "BestTarget_SignetOfRecall",
    "BestTarget_SignetOfRejuvenation",
    "BestTarget_SignetOfRemoval",
    "BestTarget_SignetOfReturn",
    "BestTarget_SignetOfReturnPvp",
    "BestTarget_SignetOfShadows",
    "BestTarget_SignetOfSorrow",
    "BestTarget_SignetOfSpirits",
    "BestTarget_SignetOfSpiritsPvp",
    "BestTarget_SignetOfStamina",
    "BestTarget_SignetOfStrength",
    "BestTarget_SignetOfSuffering",
    "BestTarget_SignetOfSynergy",
    "BestTarget_SignetOfTheUnseen",
    "BestTarget_SignetOfToxicShock",
    "BestTarget_SignetOfTwilight",
    "BestTarget_SignetOfWeariness",
    "BestTarget_SunspearRebirthSignet",
    "BestTarget_TryptophanSignet",
    "BestTarget_UnnaturalSignet",
    "BestTarget_UnnaturalSignetPvp",
    "BestTarget_UnnaturalSignetSaulDalessio",
    "CanUse_AntidoteSignet",
    "CanUse_ArchersSignet",
    "CanUse_BaneSignet",
    "CanUse_BarbedSignet",
    "CanUse_BarbedSignetPvp",
    "CanUse_BlessedSignet",
    "CanUse_BoonSignet",
    "CanUse_CandyCornStrike",
    "CanUse_CastigationSignet",
    "CanUse_CastigationSignetSaulDalessio",
    "CanUse_CauterySignet",
    "CanUse_DeathPactSignet",
    "CanUse_DeathPactSignetPvp",
    "CanUse_DolyakSignet",
    "CanUse_EtherSignet",
    "CanUse_GlowingSignet",
    "CanUse_HealingSignet",
    "CanUse_HexEaterSignet",
    "CanUse_KeystoneSignet",
    "CanUse_LeechSignet",
    "CanUse_LightbringerSignet",
    "CanUse_PlagueSignet",
    "CanUse_PoisonTipSignet",
    "CanUse_PolymockBaneSignet",
    "CanUse_PolymockEtherSignet",
    "CanUse_PolymockSignetOfClumsiness",
    "CanUse_PurgeSignet",
    "CanUse_RemedySignet",
    "CanUse_ResurrectionSignet",
    "CanUse_SadistsSignet",
    "CanUse_SignetOfAggression",
    "CanUse_SignetOfAgony",
    "CanUse_SignetOfAgonyPvp",
    "CanUse_SignetOfBinding",
    "CanUse_SignetOfCapture",
    "CanUse_SignetOfClumsiness",
    "CanUse_SignetOfClumsinessPvp",
    "CanUse_SignetOfCorruptionKurzick",
    "CanUse_SignetOfCorruptionLuxon",
    "CanUse_SignetOfCreation",
    "CanUse_SignetOfCreationPvp",
    "CanUse_SignetOfDeadlyCorruption",
    "CanUse_SignetOfDeadlyCorruptionPvp",
    "CanUse_SignetOfDevotion",
    "CanUse_SignetOfDisenchantment",
    "CanUse_SignetOfDisruption",
    "CanUse_SignetOfDistraction",
    "CanUse_SignetOfGhostlyMight",
    "CanUse_SignetOfGhostlyMightPvp",
    "CanUse_SignetOfHumility",
    "CanUse_SignetOfIllusions",
    "CanUse_SignetOfInfection",
    "CanUse_SignetOfJudgment",
    "CanUse_SignetOfJudgmentPvp",
    "CanUse_SignetOfLostSouls",
    "CanUse_SignetOfMalice",
    "CanUse_SignetOfMidnight",
    "CanUse_SignetOfMysticSpeed",
    "CanUse_SignetOfMysticWrath",
    "CanUse_SignetOfPiousLight",
    "CanUse_SignetOfPiousRestraint",
    "CanUse_SignetOfPiousRestraintPvp",
    "CanUse_SignetOfRage",
    "CanUse_SignetOfRecall",
    "CanUse_SignetOfRejuvenation",
    "CanUse_SignetOfRemoval",
    "CanUse_SignetOfReturn",
    "CanUse_SignetOfReturnPvp",
    "CanUse_SignetOfShadows",
    "CanUse_SignetOfSorrow",
    "CanUse_SignetOfSpirits",
    "CanUse_SignetOfSpiritsPvp",
    "CanUse_SignetOfStamina",
    "CanUse_SignetOfStrength",
    "CanUse_SignetOfSuffering",
    "CanUse_SignetOfSynergy",
    "CanUse_SignetOfTheUnseen",
    "CanUse_SignetOfToxicShock",
    "CanUse_SignetOfTwilight",
    "CanUse_SignetOfWeariness",
    "CanUse_SunspearRebirthSignet",
    "CanUse_TryptophanSignet",
    "CanUse_UnnaturalSignet",
    "CanUse_UnnaturalSignetPvp",
    "CanUse_UnnaturalSignetSaulDalessio",
]
