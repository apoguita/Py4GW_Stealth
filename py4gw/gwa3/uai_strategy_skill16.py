"""GwAu3's ``UtilityAI_Skill16.au3`` strategy functions, transcribed.

**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_strategies.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

`py4gw/gwa3/uai_best_target_cache.py` and `uai_can_use_cache.py` answer a slot's skill id with the *name*
of one of these functions; GwAu3's engine resolves that name with AutoIt's ``Call``, and this layer
resolves it the same way. So these are the strategy half of the ranking: which agent a skill wants, or
which guard lets it be used at all. **74 of this file's 74 are transcribed and 0
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
from .uai_agent import UAI_GetPlayerInfo
from .uai_effects import UAI_PlayerHasEffect
from .uai_get_agent import UAI_CountAgents
from .uai_utils import Skill_GetSlotByID


def CanUse_DefyPain() -> Any:
    """``UtilityAI_Skill16.au3:8`` -- transcribed from GwAu3's own body."""

    if UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_HP) > 0.8:
        return False
    return True


def BestTarget_DefyPain(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill16.au3:14`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_EndurePain() -> Any:
    """``UtilityAI_Skill16.au3:23`` -- transcribed from GwAu3's own body."""

    if UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_HP) > 0.5:
        return False
    return True


def BestTarget_EndurePain(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill16.au3:29`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_WarriorsCunning() -> Any:
    """``UtilityAI_Skill16.au3:38`` -- transcribed from GwAu3's own body."""

    if not UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_IsAttacking):
        return False
    return True


def BestTarget_WarriorsCunning(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill16.au3:44`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ShieldBash() -> Any:
    """``UtilityAI_Skill16.au3:53`` -- transcribed from GwAu3's own body."""

    l_i_EnemyCount = UAI_CountAgents(UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID), _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")
    if l_i_EnemyCount < 1:
        return False
    return True


def BestTarget_ShieldBash(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill16.au3:60`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_WarriorsEndurance() -> Any:
    """``UtilityAI_Skill16.au3:69`` -- transcribed from GwAu3's own body."""

    if not UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_IsAttacking):
        return False
    if UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_CurrentEnergy) > 10:
        return False
    return True


def BestTarget_WarriorsEndurance(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill16.au3:76`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_HundredBlades() -> Any:
    """``UtilityAI_Skill16.au3:85`` -- transcribed from GwAu3's own body."""

    l_i_EnemyCount = UAI_CountAgents(UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID), _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")
    if l_i_EnemyCount < 2:
        return False
    return True


def BestTarget_HundredBlades(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill16.au3:92`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Riposte() -> Any:
    """``UtilityAI_Skill16.au3:101`` -- transcribed from GwAu3's own body."""

    l_i_EnemyCount = UAI_CountAgents(UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID), _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")
    if l_i_EnemyCount < 1:
        return False
    return True


def BestTarget_Riposte(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill16.au3:108`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DeadlyRiposte() -> Any:
    """``UtilityAI_Skill16.au3:117`` -- transcribed from GwAu3's own body."""

    l_i_EnemyCount = UAI_CountAgents(UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID), _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")
    if l_i_EnemyCount < 1:
        return False
    return True


def BestTarget_DeadlyRiposte(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill16.au3:124`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CriticalEye() -> Any:
    """``UtilityAI_Skill16.au3:133`` -- transcribed from GwAu3's own body."""

    if not UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_IsAttacking):
        return False
    return True


def BestTarget_CriticalEye(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill16.au3:139`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AuraOfTheJuggernaut() -> Any:
    """``UtilityAI_Skill16.au3:148`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_AuraOfTheJuggernaut(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill16.au3:152`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RitualLord() -> Any:
    """``UtilityAI_Skill16.au3:161`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_RitualLord(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill16.au3:165`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SoulTwisting() -> Any:
    """``UtilityAI_Skill16.au3:174`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_SoulTwisting(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill16.au3:178`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_EtherPrism() -> Any:
    """``UtilityAI_Skill16.au3:187`` -- transcribed from GwAu3's own body."""

    if UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_HP) > 0.5:
        return False
    return True


def BestTarget_EtherPrism(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill16.au3:193`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RageOfTheNtouka() -> Any:
    """``UtilityAI_Skill16.au3:202`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_RageOfTheNtouka(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill16.au3:206`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_ExtendEnchantments() -> Any:
    """``UtilityAI_Skill16.au3:216`` -- transcribed from GwAu3's own body."""

    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_EXTEND_ENCHANTMENTS):
        return False
    l_i_VoSSlot = Skill_GetSlotByID(_constants.GC_I_SKILL_ID_VOW_OF_STRENGTH)
    if l_i_VoSSlot > 0:
        if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_VOW_OF_STRENGTH):
            return False

        return True


def BestTarget_ExtendEnchantments(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill16.au3:226`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_CurseOfTheStaffOfTheMists() -> Any:
    """``UtilityAI_Skill16.au3:235`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_CurseOfTheStaffOfTheMists(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill16.au3:239`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_AuraOfTheStaffOfTheMists() -> Any:
    """``UtilityAI_Skill16.au3:248`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_AuraOfTheStaffOfTheMists(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill16.au3:252`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_PowerOfTheStaffOfTheMists() -> Any:
    """``UtilityAI_Skill16.au3:261`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_PowerOfTheStaffOfTheMists(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill16.au3:265`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RampageAsOne() -> Any:
    """``UtilityAI_Skill16.au3:274`` -- transcribed from GwAu3's own body."""

    l_i_PetSize = World_GetWorldInfo("PetInfoArraySize")
    lMyPet = 0
    for i in range(1,  + 1):
        if Party_GetPetInfo(i, "OwnerAgentID") == UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID):
            lMyPet = Party_GetPetInfo(i, "AgentID")
            break


        if lMyPet == 0:
            return False
        if Agent_GetAgentInfo(lMyPet, "HPPercent") == 0:
            return False
        return True


def BestTarget_RampageAsOne(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill16.au3:293`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FocusedAnger() -> Any:
    """``UtilityAI_Skill16.au3:302`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_FocusedAnger(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill16.au3:306`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_NaturalTemper() -> Any:
    """``UtilityAI_Skill16.au3:315`` -- transcribed from GwAu3's own body."""

    if UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_IsEnchanted):
        return False
    return True


def BestTarget_NaturalTemper(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill16.au3:321`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Enraged() -> Any:
    """``UtilityAI_Skill16.au3:330`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Enraged(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill16.au3:334`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_Ram() -> Any:
    """``UtilityAI_Skill16.au3:343`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Ram(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill16.au3:347`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_HardenShell() -> Any:
    """``UtilityAI_Skill16.au3:356`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_HardenShell(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill16.au3:360`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RollerbeetleDash() -> Any:
    """``UtilityAI_Skill16.au3:369`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_RollerbeetleDash(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill16.au3:373`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_SuperRollerbeetle() -> Any:
    """``UtilityAI_Skill16.au3:382`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_SuperRollerbeetle(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill16.au3:386`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RollerbeetleEcho() -> Any:
    """``UtilityAI_Skill16.au3:395`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_RollerbeetleEcho(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill16.au3:399`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_DistractingLunge() -> Any:
    """``UtilityAI_Skill16.au3:408`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_DistractingLunge(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill16.au3:412`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_RollerbeetleBlast() -> Any:
    """``UtilityAI_Skill16.au3:421`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_RollerbeetleBlast(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill16.au3:425`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_SpitRocks() -> Any:
    """``UtilityAI_Skill16.au3:434`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_SpitRocks(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill16.au3:438`` -- transcribed from GwAu3's own body."""

    return 0


def CanUse_Intensity() -> Any:
    """``UtilityAI_Skill16.au3:447`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_Intensity(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill16.au3:451`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_NeverRampageAlone() -> Any:
    """``UtilityAI_Skill16.au3:460`` -- transcribed from GwAu3's own body."""

    l_i_PetSize = World_GetWorldInfo("PetInfoArraySize")
    lMyPet = 0
    for i in range(1,  + 1):
        if Party_GetPetInfo(i, "OwnerAgentID") == UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID):
            lMyPet = Party_GetPetInfo(i, "AgentID")
            break


        if lMyPet == 0:
            return False
        if Agent_GetAgentInfo(lMyPet, "HPPercent") == 0:
            return False
        return True


def BestTarget_NeverRampageAlone(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill16.au3:479`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_BurningShield() -> Any:
    """``UtilityAI_Skill16.au3:488`` -- transcribed from GwAu3's own body."""

    l_i_EnemyCount = UAI_CountAgents(UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID), _constants.GC_I_RANGE_ADJACENT, "UAI_Filter_IsLivingEnemy")
    if l_i_EnemyCount < 1:
        return False
    return True


def BestTarget_BurningShield(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill16.au3:495`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FeelNoPain() -> Any:
    """``UtilityAI_Skill16.au3:504`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_FeelNoPain(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill16.au3:508`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_UrsanForce() -> Any:
    """``UtilityAI_Skill16.au3:517`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_UrsanForce(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill16.au3:521`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_FalkenQuick() -> Any:
    """``UtilityAI_Skill16.au3:530`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_FalkenQuick(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill16.au3:534`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


def CanUse_RitualLordPvP() -> Any:
    """``UtilityAI_Skill16.au3:543`` -- transcribed from GwAu3's own body."""

    return True


def BestTarget_RitualLordPvP(a_f_AggroRange) -> Any:
    """``UtilityAI_Skill16.au3:547`` -- transcribed from GwAu3's own body."""

    return UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_ID)


__all__ = [
    "BestTarget_AuraOfTheJuggernaut",
    "BestTarget_AuraOfTheStaffOfTheMists",
    "BestTarget_BurningShield",
    "BestTarget_CriticalEye",
    "BestTarget_CurseOfTheStaffOfTheMists",
    "BestTarget_DeadlyRiposte",
    "BestTarget_DefyPain",
    "BestTarget_DistractingLunge",
    "BestTarget_EndurePain",
    "BestTarget_Enraged",
    "BestTarget_EtherPrism",
    "BestTarget_ExtendEnchantments",
    "BestTarget_FalkenQuick",
    "BestTarget_FeelNoPain",
    "BestTarget_FocusedAnger",
    "BestTarget_HardenShell",
    "BestTarget_HundredBlades",
    "BestTarget_Intensity",
    "BestTarget_NaturalTemper",
    "BestTarget_NeverRampageAlone",
    "BestTarget_PowerOfTheStaffOfTheMists",
    "BestTarget_RageOfTheNtouka",
    "BestTarget_Ram",
    "BestTarget_RampageAsOne",
    "BestTarget_Riposte",
    "BestTarget_RitualLord",
    "BestTarget_RitualLordPvP",
    "BestTarget_RollerbeetleBlast",
    "BestTarget_RollerbeetleDash",
    "BestTarget_RollerbeetleEcho",
    "BestTarget_ShieldBash",
    "BestTarget_SoulTwisting",
    "BestTarget_SpitRocks",
    "BestTarget_SuperRollerbeetle",
    "BestTarget_UrsanForce",
    "BestTarget_WarriorsCunning",
    "BestTarget_WarriorsEndurance",
    "CanUse_AuraOfTheJuggernaut",
    "CanUse_AuraOfTheStaffOfTheMists",
    "CanUse_BurningShield",
    "CanUse_CriticalEye",
    "CanUse_CurseOfTheStaffOfTheMists",
    "CanUse_DeadlyRiposte",
    "CanUse_DefyPain",
    "CanUse_DistractingLunge",
    "CanUse_EndurePain",
    "CanUse_Enraged",
    "CanUse_EtherPrism",
    "CanUse_ExtendEnchantments",
    "CanUse_FalkenQuick",
    "CanUse_FeelNoPain",
    "CanUse_FocusedAnger",
    "CanUse_HardenShell",
    "CanUse_HundredBlades",
    "CanUse_Intensity",
    "CanUse_NaturalTemper",
    "CanUse_NeverRampageAlone",
    "CanUse_PowerOfTheStaffOfTheMists",
    "CanUse_RageOfTheNtouka",
    "CanUse_Ram",
    "CanUse_RampageAsOne",
    "CanUse_Riposte",
    "CanUse_RitualLord",
    "CanUse_RitualLordPvP",
    "CanUse_RollerbeetleBlast",
    "CanUse_RollerbeetleDash",
    "CanUse_RollerbeetleEcho",
    "CanUse_ShieldBash",
    "CanUse_SoulTwisting",
    "CanUse_SpitRocks",
    "CanUse_SuperRollerbeetle",
    "CanUse_UrsanForce",
    "CanUse_WarriorsCunning",
    "CanUse_WarriorsEndurance",
]
