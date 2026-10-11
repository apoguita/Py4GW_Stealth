"""GwAu3's ``Core/UtilityAI_CanCast.au3``: whether a slot may be used, and why not.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

**What the file is.** The gate between "the ranking says this skill is the right one" and the cast:
`UAI_CanUse` prices the slot in health, overcast and energy -- with every modifier GwAu3's own build
knowledge applies -- and `UAI_CanAutoAttack` decides whether attacking is even safe, by pricing the hexes
that punish it. `UAI_IsCastSensible` handles the one case the ranking cannot see: a **self-targeted** skill
whose effect is already up is a wasted cast. `UAI_CanDrop` is the item-spell side of the same question.

**Everything these bodies read is already this layer's own**: the static skill table
(`py4gw/gwa3/uai_static_skill_cache.py`), the live skillbar words including recharge
(`uai_dynamic_skill_cache.py`), the player's effect properties *including the computed scale columns*
(`uai_effects.py`), the agent queries (`uai_get_agent.py`) and the skill record itself
(`data_skill.py`). That is why the file could be written now: every one of those was a named work item in
an earlier round.

**One divergence is recorded on the member that carries it**, rather than left in the code: the answer
of `UAI_PlayerHasEffectType` arrives in **two channels** -- the boolean, and the effect's skill id
through AutoIt's ``@extended``. This layer has no out-of-band return, so that member answers the
boolean and the skill id comes from the private `_player_effect_of_type`, which makes the same scan
over the same live effect list and is named in the member's docstring as its documented twin. **Both
spellings of the source's own scan are in this file**: `UAI_PlayerHasEffectType` is the source's
member, and `_UAI_EffectEndingSoon` is the source's private helper under the name the source gives it
(the layer keeps an underscore-prefixed GwAu3 name as written -- `_GetArmorScore`,
`_UAI_BestCoveragePosition` and `_UAI_CountAlliesInRange` in `uai_get_agent.py` are the same rule).
"""

from __future__ import annotations

import math
import time
from typing import Any

from . import constants as _constants
from .cmd_map import Map_Move
from .data_agent import Agent_GetAgentInfo
from .data_skill import Skill_GetSkillInfo
from .uai_agent import UAI_GetPlayerInfo
from .uai_dynamic_skill_cache import UAI_GetDynamicSkillInfo
from .uai_effects import (
    UAI_GetPlayerEffectInfo,
    UAI_PlayerHasEffect,
    UAI_PlayerHasEffectType,
)
from .uai_filter import UAI_Filter_IsLivingAlly
from .uai_get_agent import (
    UAI_CountAgents,
    UAI_GetAgentInfoByID,
    UAI_GetBestMartialEnemyPosition,
    UAI_GetBestOffensiveWardPosition,
    UAI_GetNearestAgent,
    _cached_ids,
)
from .uai_static_skill_cache import UAI_GetStaticSkillInfo

__all__ = [
    "UAI_CanAutoAttack",
    "UAI_CanDrop",
    "UAI_CanUse",
    "UAI_IsCastSensible",
]


def _static(skill_slot: Any, column: str) -> Any:
    """One column of the slot's static skill data, by the column's GwAu3 name."""

    return UAI_GetStaticSkillInfo(skill_slot, getattr(_constants, f"GC_UAI_STATIC_SKILL_{column}"))


def _dynamic(skill_slot: Any, column: str) -> Any:
    """One column of the slot's live words, by the column's GwAu3 name."""

    return UAI_GetDynamicSkillInfo(skill_slot, getattr(_constants, f"GC_UAI_DYNAMIC_SKILL_{column}"))


def _effect_scale(skill_id: int) -> Any:
    """The player's effect from a skill, priced by its ``Scale`` column (``:101`` and its neighbours)."""

    return UAI_GetPlayerEffectInfo(skill_id, _constants.GC_UAI_EFFECT_Scale)


def _UAI_EffectEndingSoon(skill_id: Any, skill_slot: Any) -> bool:
    """Whether the effect a self-targeted skill would re-apply is nearly over
    (``UtilityAI_CanCast.au3:406-409``).

    ``TimeRemaining`` against the skill's own ``Activation`` in milliseconds plus a second of slack --
    which is the source's arithmetic, over the activation column of the *static* table and the
    ``TimeRemaining`` this layer computes from the client's effect record.
    """

    remaining = UAI_GetPlayerEffectInfo(skill_id, _constants.GC_UAI_EFFECT_TimeRemaining)
    activation = _static(skill_slot, "Activation")
    return remaining <= (activation * 1000 + 1000)


def UAI_CanAutoAttack() -> bool:
    """Whether auto-attacking is safe right now (``UtilityAI_CanCast.au3:4-22``).

    A hex-free player can always attack (``:5``). With a hex, GwAu3 tests the three hexes that punish
    attacking outright (``Spirit Shackles``, ``Ineptitude``, ``Clumsiness``, ``Wandering Eye``) and then
    **prices** the three that reflect damage -- ``Empathy``, ``Spiteful Spirit``, ``Spoil Victor`` -- by
    their ``Scale`` column, and allows the attack only when that damage does not exceed the player's
    current hit points plus 15% of maximum (``:13-21``).

    ``CurrentHP`` and ``MaxHP`` are the port's own columns, and the ``Scale`` values are the computed
    scalars this layer answers from the live effect record and the skill's own two scale ends.
    """

    if not UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_IsHexed):
        return True

    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_SPIRIT_SHACKLES):
        return False

    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_INEPTITUDE):
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_CLUMSINESS):
        return False
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_WANDERING_EYE):
        return False

    incoming_damage = 0
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_EMPATHY):
        incoming_damage += _effect_scale(_constants.GC_I_SKILL_ID_EMPATHY)
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_SPITEFUL_SPIRIT):
        incoming_damage += _effect_scale(_constants.GC_I_SKILL_ID_SPITEFUL_SPIRIT)
    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_SPOIL_VICTOR):
        incoming_damage += _effect_scale(_constants.GC_I_SKILL_ID_SPOIL_VICTOR)

    ceiling = UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_CurrentHP) + (
        UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_MaxHP) * 0.15
    )
    return not (incoming_damage > ceiling)


def UAI_IsCastSensible(skill_slot: Any) -> bool:
    """Whether casting this slot now would do anything (``UtilityAI_CanCast.au3:378-404``).

    A skill that is not self-targeted is always sensible (``:380``) -- the ranking already chose its
    target. For a **self**-targeted skill the question is whether its own effect is still running: an
    enchantment, ward, shout, ritual, form or echo/refrain is tested only by
    `_UAI_EffectEndingSoon` (``:388``), while a stance, glyph or preparation is a waste unless the *current*
    one is the same skill (``:390-400``).

    **The three "only one at a time" cases are the source's three ``Case``s**, each asking
    `UAI_PlayerHasEffectType` and then reading the matching effect's skill id through the documented
    ``@extended`` twin `uai_effects._player_effect_of_type` -- which is the value the source compares
    with ``@extended`` on ``:391``, ``:395`` and ``:399``. An effect of that type that is *another*
    skill makes the cast not sensible, and the same skill falls through to the "nearly over" test.

    **The twin is imported here rather than at the module's top**, because it is read *at the point of
    use* exactly as ``@extended`` is: a caller that stubs the twin on `py4gw.gwa3.uai_effects` -- which
    is where it lives, beside the member whose out-of-band return it carries -- redirects this call the
    way stubbing ``@extended`` would.
    """

    from .uai_effects import _player_effect_of_type

    target_type = _static(skill_slot, "Target")
    if target_type != _constants.GC_I_SKILL_TARGET_SELF:
        return True

    skill_type = _static(skill_slot, "SkillType")
    skill_id = _static(skill_slot, "SkillID")

    if skill_type in (
        _constants.GC_I_SKILL_TYPE_ENCHANTMENT,
        _constants.GC_I_SKILL_TYPE_WARD,
        _constants.GC_I_SKILL_TYPE_SHOUT,
        _constants.GC_I_SKILL_TYPE_RITUAL,
        _constants.GC_I_SKILL_TYPE_FORM,
        _constants.GC_I_SKILL_TYPE_ECHO_REFRAIN,
    ):
        return _UAI_EffectEndingSoon(skill_id, skill_slot)

    if skill_type == _constants.GC_I_SKILL_TYPE_STANCE:
        if not UAI_PlayerHasEffectType("HasStance"):
            return True
        if _player_effect_of_type(_constants.GC_I_SKILL_TYPE_STANCE) != skill_id:
            return False
        return _UAI_EffectEndingSoon(skill_id, skill_slot)

    if skill_type == _constants.GC_I_SKILL_TYPE_GLYPH:
        if not UAI_PlayerHasEffectType("HasGlyph"):
            return True
        if _player_effect_of_type(_constants.GC_I_SKILL_TYPE_GLYPH) != skill_id:
            return False
        return _UAI_EffectEndingSoon(skill_id, skill_slot)

    if skill_type == _constants.GC_I_SKILL_TYPE_PREPARATION:
        if not UAI_PlayerHasEffectType("HasPreparation"):
            return True
        if _player_effect_of_type(_constants.GC_I_SKILL_TYPE_PREPARATION) != skill_id:
            return False
        return _UAI_EffectEndingSoon(skill_id, skill_slot)

    return True


def UAI_CanUse(skill_slot: Any) -> bool:
    """Whether a slot can be cast right now (``UtilityAI_CanCast.au3:24-156``).

    GwAu3's own order, kept step for step, because each step can end the question early:

    1. **sensibility** -- a self-targeted skill whose effect is still up is out (``:26``);
    2. **adrenaline** -- a skill that costs adrenaline answers on adrenaline alone, and never reaches the
       energy pricing (``:29-32``): enough adrenaline is a *yes*;
    3. **cooldown** -- a recharging slot is out (``:35``);
    4. **health cost** -- the sacrifice cost from the skill's own ``HealthCost`` column, plus the two
       effects that modify it (``Awaken the Blood`` +50%, ``Scourge Sacrifice`` double) and
       ``Masochism``'s 5% on *any* spell, refused when that total is at or above the player's current hit
       points (``:41-54``);
    5. **overcast** -- refused when the cast would put overcast at half the player's maximum energy, with
       ``Glyph of Energy`` zeroing the cost (``:57-63``);
    6. **energy** -- the whole modifier chain (`:66-152`): the ungated ``Quickening Zephyr`` +30%, then the
       **type-gated** increases and reductions for the skill's one type, then ``Energizing Wind``, then
       the **attribute-gated** reductions, then the weapon-requirement and combo gates, and finally the
       clamp -- **minimum one energy, and zero only under Way of the Empty Palm** -- with the cast
       allowed when current energy reaches ``Ceiling`` of the cost (``:153``).

    The arithmetic is GwAu3's, including the two asymmetries a reader should not "fix": the adrenaline
    branch answers before any energy is priced, and the clamp's floor is one rather than zero.
    """

    if not UAI_IsCastSensible(skill_slot):
        return False

    if _static(skill_slot, "Adrenaline") != 0:
        if _dynamic(skill_slot, "Adrenaline") < _static(skill_slot, "Adrenaline"):
            return False
        return True

    if not _dynamic(skill_slot, "IsRecharged"):
        return False

    skill_id = _static(skill_slot, "SkillID")

    total_health_cost = 0.0
    base_sacrifice_cost = Skill_GetSkillInfo(skill_id, "HealthCost")
    if base_sacrifice_cost != 0:
        total_health_cost = UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_MaxHP) * base_sacrifice_cost / 100

        if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_AWAKEN_THE_BLOOD):
            total_health_cost = total_health_cost + (total_health_cost * 0.5)
        if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_SCOURGE_SACRIFICE):
            total_health_cost = total_health_cost * 2

    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_MASOCHISM):
        total_health_cost = total_health_cost + (UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_MaxHP) * 0.05)

    if total_health_cost > 0 and (
        UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_CurrentHP) <= total_health_cost
    ):
        return False

    overcast_cost = Skill_GetSkillInfo(skill_id, "Overcast")
    if overcast_cost != 0:
        current_overcast = UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_Overcast)
        max_energy = UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_MaxEnergy)
        if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_GLYPH_OF_ENERGY):
            overcast_cost = 0
        if (current_overcast + overcast_cost) >= (max_energy * 0.5):
            return False

    base_energy_cost = _static(skill_slot, "EnergyCost")
    energy_cost = base_energy_cost
    current_energy = UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_CurrentEnergy)

    skill_type = _static(skill_slot, "SkillType")
    attribute = _static(skill_slot, "Attribute")
    target = _static(skill_slot, "Target")
    weapon_req = _static(skill_slot, "WeaponReq")
    combo = _static(skill_slot, "Combo")
    way_of_the_empty_palm = False

    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_QUICKENING_ZEPHYR):
        energy_cost *= 1.3

    if skill_type == _constants.GC_I_SKILL_TYPE_HEX:
        if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_NATURES_RENEWAL):
            energy_cost *= 2
        if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_ANGUISHED_WAS_LINGWAH) and attribute in (
            _constants.GC_I_ATTRIBUTE_COMMUNING,
            _constants.GC_I_ATTRIBUTE_RESTORATION_MAGIC,
            _constants.GC_I_ATTRIBUTE_CHANNELING_MAGIC,
            _constants.GC_I_ATTRIBUTE_SPAWNING_POWER,
        ):
            energy_cost -= 5

    elif skill_type == _constants.GC_I_SKILL_TYPE_ENCHANTMENT:
        if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_NATURES_RENEWAL):
            energy_cost *= 2

    elif skill_type == _constants.GC_I_SKILL_TYPE_SIGNET:
        if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_PRIMAL_ECHOES):
            energy_cost += 10

    elif skill_type in (_constants.GC_I_SKILL_TYPE_CHANT, _constants.GC_I_SKILL_TYPE_SHOUT):
        if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_ROARING_WINDS):
            energy_cost += _effect_scale(_constants.GC_I_SKILL_ID_ROARING_WINDS)

    elif skill_type == _constants.GC_I_SKILL_TYPE_SPELL:
        if target != _constants.GC_I_SKILL_TARGET_SELF and (
            UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_SELFLESS_SPIRIT_LUXON)
            or UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_SELFLESS_SPIRIT_KURZICK)
        ):
            energy_cost -= 3
        if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_GLYPH_OF_LESSER_ENERGY):
            energy_cost -= _effect_scale(_constants.GC_I_SKILL_ID_GLYPH_OF_LESSER_ENERGY)
        elif UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_GLYPH_OF_ENERGY):
            energy_cost -= _effect_scale(_constants.GC_I_SKILL_ID_GLYPH_OF_ENERGY)
        if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_ATTUNED_WAS_SONGKAI):
            energy_cost -= base_energy_cost * _effect_scale(_constants.GC_I_SKILL_ID_ATTUNED_WAS_SONGKAI)

    elif skill_type == _constants.GC_I_SKILL_TYPE_RITUAL:
        if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_ATTUNED_WAS_SONGKAI):
            energy_cost -= base_energy_cost * _effect_scale(_constants.GC_I_SKILL_ID_ATTUNED_WAS_SONGKAI)
        if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_SOUL_TWISTING):
            energy_cost -= 15

    elif skill_type in (
        _constants.GC_I_SKILL_TYPE_WEAPON_SPELL,
        _constants.GC_I_SKILL_TYPE_ITEM_SPELL,
    ):
        if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_RENEWING_MEMORIES):
            energy_cost -= base_energy_cost * _effect_scale(_constants.GC_I_SKILL_ID_RENEWING_MEMORIES)

    if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_ENERGIZING_WIND):
        energy_cost -= 15

    if attribute == _constants.GC_I_ATTRIBUTE_HEALING_PRAYERS:
        if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_DIVINE_SPIRIT):
            energy_cost -= 5
        if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_HEALERS_COVENANT):
            energy_cost -= 3

    elif attribute in (
        _constants.GC_I_ATTRIBUTE_SMITING_PRAYERS,
        _constants.GC_I_ATTRIBUTE_PROTECTION_PRAYERS,
        _constants.GC_I_ATTRIBUTE_DIVINE_FAVOR,
    ):
        if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_DIVINE_SPIRIT):
            energy_cost -= 5

    elif _constants.GC_I_ATTRIBUTE_BLOOD_MAGIC <= attribute <= _constants.GC_I_ATTRIBUTE_SOUL_REAPING:
        if UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_CULTISTS_FERVOR):
            energy_cost -= _effect_scale(_constants.GC_I_SKILL_ID_CULTISTS_FERVOR)

    if weapon_req == _constants.GC_I_WEAPON_TYPE_BOW and UAI_PlayerHasEffect(
        _constants.GC_I_SKILL_ID_EXPERT_FOCUS
    ):
        energy_cost -= 2

    if combo in (
        _constants.GC_I_SKILL_COMBO_OFF_HAND_ATTACK,
        _constants.GC_I_SKILL_COMBO_DUAL_ATTACK,
    ):
        way_of_the_empty_palm = bool(
            UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_WAY_OF_THE_EMPTY_PALM)
        )
        if way_of_the_empty_palm:
            energy_cost = 0

    if energy_cost < 1 and not way_of_the_empty_palm:
        energy_cost = 1
    if energy_cost < 0:
        energy_cost = 0

    if current_energy < math.ceil(energy_cost):
        return False

    return True


def UAI_CanDrop(skill_slot: Any) -> Any:
    """Whether this slot's **item spell** should be dropped now (``UtilityAI_CanCast.au3:158-376``).

    Fifteen cases, one per item spell, each with its own evidence -- and several of them are the same
    shape: count what the drop would hit, and if there is not enough, walk toward where it is and watch the
    count. Those walks are written out one by one, as the source writes them, rather than factored into a
    helper: **the repetition is the port**, and a reader of a case has to be able to check it against its
    own lines.

    Three things a reader should not "fix":

    * ``Energetic Was Lee Sa``'s comment says "below 25% or below 10 energy" while its code tests ``< 15``
      (``:303``) -- the code is the source, and ``15`` is what is ported;
    * each bounded walk **returns its count once more** after the loop, so a walk that times out at 3000 ms
      can still answer ``True`` on a single enemy (``:202`` and its neighbours);
    * the answer for a slot holding none of the fifteen is ``False``, from the ``Switch``'s fall-through
      and the trailing ``Return False`` (``:375``).
    """

    skill_id = _static(skill_slot, "SkillID")
    nearby = _constants.GC_I_RANGE_NEARBY
    area = _constants.GC_I_RANGE_AREA
    earshot = _constants.GC_I_RANGE_EARSHOT

    if skill_id == _constants.GC_I_SKILL_ID_ANGUISHED_WAS_LINGWAH:
        # Drop if every Ritualist hex on the bar is recharging (`:160-172`).
        has_ritualist_hex = False
        for slot in range(1, 9):
            if slot == skill_slot:
                continue
            skill_type = _static(slot, "SkillType")
            profession = _static(slot, "Profession")
            if (
                skill_type == _constants.GC_I_SKILL_TYPE_HEX
                and profession == _constants.GC_I_PROFESSION_RITUALIST
            ):
                has_ritualist_hex = True
                if _dynamic(slot, "IsRecharged"):
                    return False
        return has_ritualist_hex

    if skill_id == _constants.GC_I_SKILL_ID_BLIND_WAS_MINGSON:
        # Drop if physical attackers (melee/ranged, not casters) are in nearby range (`:173-202`).
        if UAI_CountAgents(-2, nearby, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsNotCaster") >= 2:
            return True

        best_pos = UAI_GetBestMartialEnemyPosition(nearby)
        if best_pos[2] <= 1:
            return False

        target_x = best_pos[0]
        target_y = best_pos[1]
        timeout = 0

        while True:
            Map_Move(target_x, target_y, 0)
            time.sleep(32 / 1000.0)
            timeout += 32

            if UAI_CountAgents(-2, nearby, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsNotCaster") >= 2:
                return True

            diff_x = target_x - Agent_GetAgentInfo(-2, "X")
            diff_y = target_y - Agent_GetAgentInfo(-2, "Y")
            if (diff_x * diff_x + diff_y * diff_y) ** 0.5 < 80:
                return True

            if timeout >= 3000:
                break

        return UAI_CountAgents(-2, nearby, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsNotCaster") >= 1

    if skill_id in (
        _constants.GC_I_SKILL_ID_CRUEL_WAS_DAOSHEN,
        _constants.GC_I_SKILL_ID_GRASPING_WAS_KUURONG,
        _constants.GC_I_SKILL_ID_DEFIANT_WAS_XINRAE,
    ):
        # Lightning damage, and damage plus knockdown, to all nearby foes (`:203-225`, `:251-296`).
        if UAI_CountAgents(-2, nearby, "UAI_Filter_IsLivingEnemy") >= 2:
            return True

        best_pos = UAI_GetBestOffensiveWardPosition(nearby)
        if best_pos[2] <= 1:
            return False

        target_x = best_pos[0]
        target_y = best_pos[1]
        timeout = 0

        while True:
            Map_Move(target_x, target_y, 0)
            time.sleep(32 / 1000.0)
            timeout += 32

            if UAI_CountAgents(-2, nearby, "UAI_Filter_IsLivingEnemy") >= 2:
                return True

            diff_x = target_x - Agent_GetAgentInfo(-2, "X")
            diff_y = target_y - Agent_GetAgentInfo(-2, "Y")
            if (diff_x * diff_x + diff_y * diff_y) ** 0.5 < 80:
                return True

            if timeout >= 3000:
                break

        return UAI_CountAgents(-2, nearby, "UAI_Filter_IsLivingEnemy") >= 1

    if skill_id == _constants.GC_I_SKILL_ID_DESTRUCTIVE_WAS_GLAIVE:
        # The same, against the larger AREA range (`:227-249`).
        if UAI_CountAgents(-2, area, "UAI_Filter_IsLivingEnemy") >= 2:
            return True

        best_pos = UAI_GetBestOffensiveWardPosition(area)
        if best_pos[2] <= 1:
            return False

        target_x = best_pos[0]
        target_y = best_pos[1]
        timeout = 0

        while True:
            Map_Move(target_x, target_y, 0)
            time.sleep(32 / 1000.0)
            timeout += 32

            if UAI_CountAgents(-2, area, "UAI_Filter_IsLivingEnemy") >= 2:
                return True

            diff_x = target_x - Agent_GetAgentInfo(-2, "X")
            diff_y = target_y - Agent_GetAgentInfo(-2, "Y")
            if (diff_x * diff_x + diff_y * diff_y) ** 0.5 < 80:
                return True

            if timeout >= 3000:
                break

        return UAI_CountAgents(-2, area, "UAI_Filter_IsLivingEnemy") >= 1

    if skill_id == _constants.GC_I_SKILL_ID_ENERGETIC_WAS_LEE_SA:
        # Drop to gain energy when running low (`:297-304`).
        current_energy = UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_CurrentEnergy)
        max_energy = UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_MaxEnergy)

        if current_energy < (max_energy * 0.25) or current_energy < 15:
            return True
        return False

    if skill_id == _constants.GC_I_SKILL_ID_GENEROUS_WAS_TSUNGRAI:
        # Drop to heal when health is low (`:305-312`).
        current_hp = UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_CurrentHP)
        max_hp = UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_MaxHP)

        if current_hp < (max_hp * 0.50):
            return True
        return False

    if skill_id == _constants.GC_I_SKILL_ID_LIVELY_WAS_NAOMEI:
        # Drop to resurrect dead party members in area (`:313-343`).
        if UAI_CountAgents(-2, area, "UAI_Filter_IsDeadAlly") >= 1:
            return True

        dead_ally = UAI_GetNearestAgent(-2, 1200, "UAI_Filter_IsDeadAlly")
        if dead_ally == 0:
            return False

        target_x = UAI_GetAgentInfoByID(dead_ally, _constants.GC_UAI_AGENT_X)
        target_y = UAI_GetAgentInfoByID(dead_ally, _constants.GC_UAI_AGENT_Y)
        timeout = 0

        while True:
            Map_Move(target_x, target_y, 0)
            time.sleep(32 / 1000.0)
            timeout += 32

            if UAI_CountAgents(-2, area, "UAI_Filter_IsDeadAlly") >= 1:
                return True

            diff_x = target_x - Agent_GetAgentInfo(-2, "X")
            diff_y = target_y - Agent_GetAgentInfo(-2, "Y")
            if (diff_x * diff_x + diff_y * diff_y) ** 0.5 < 80:
                return True

            if timeout >= 3000:
                break

        return UAI_CountAgents(-2, area, "UAI_Filter_IsDeadAlly") >= 1

    if skill_id == _constants.GC_I_SKILL_ID_PROTECTIVE_WAS_KAOLAI:
        # Drop to heal the party when several allies need it, or the player does (`:344-363`).
        injured_allies = 0

        for agent_id in _cached_ids():
            if not UAI_Filter_IsLivingAlly(agent_id):
                continue
            if UAI_GetAgentInfoByID(agent_id, _constants.GC_UAI_AGENT_HP) < 0.75:
                injured_allies += 1

        current_hp = UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_CurrentHP)
        max_hp = UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_MaxHP)
        player_low = current_hp < (max_hp * 0.70)

        if injured_allies >= 2 or player_low:
            return True
        return False

    if skill_id == _constants.GC_I_SKILL_ID_PURE_WAS_LI_MING:
        # Drop to strip conditions from allies in earshot (`:364-366`).
        return UAI_CountAgents(-2, earshot, "UAI_Filter_IsLivingAlly|UAI_Filter_IsConditioned") >= 2

    if skill_id == _constants.GC_I_SKILL_ID_RESILIENT_WAS_XIKO:
        # Drop to strip conditions from the player (`:367-369`).
        return bool(UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_IsConditioned))

    if skill_id in (
        _constants.GC_I_SKILL_ID_VOCAL_WAS_SOGOLON,
        _constants.GC_I_SKILL_ID_ATTUNED_WAS_SONGKAI,
        _constants.GC_I_SKILL_ID_VENGEFUL_WAS_KHANHEI,
        _constants.GC_I_SKILL_ID_TRANQUIL_WAS_TANASEN,
        _constants.GC_I_SKILL_ID_MIGHTY_WAS_VORIZUN,
    ):
        # Five item spells the source never drops (`:370-372`).
        return False

    return False
