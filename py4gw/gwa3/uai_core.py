"""GwAu3's ``UtilityAI_Core.au3``: the combat engine a ``UAI_Fight`` call runs.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

**This is the plugin's user-facing entry point, and it is the one UAI file a script calls.** The census
in the spec measured it: of the 65 ``UAI_*`` functions this layer has not built, **63 have no call site
outside ``API/Plugins/UtilityAI/``** -- they are the plugin's own machinery -- and **two are called from
outside**: `UAI_CacheSkillBar` and `UAI_Fight` (``Scripts/Exemples/Exemple_AutoitGUI_Tester.au3:137``,
``Pathfinder_Movements.au3:224``). So this file is the remaining *user-facing* surface of the plugin, and
every member here says which of the engine's parts it still needs.

**What the engine is, in the source's own terms.** ``UAI_Fight`` sets the fight mode and the target
bookkeeping, then loops: refresh the agent cache, optionally choose weapon sets, run `UAI_UseSkills`
(which walks the eight skill slots), and stop on a wiped party, a dead player, a map change or an exit
callback (``:57-68``). Each member below is one step of that, and each is written against the source's
own body and lines. What the port cannot yet express is the *decision* half:

* the **static skill cache** -- `UAI_StaticDataSkill` and `UAI_GetStaticSkillInfo`
  (``UtilityAI_Cache.au3``), which answer a slot's skill id and type. `UAI_UseSkills`,
  `UAI_PrioritySkills` and `UAI_DropBundle` all begin by asking it which slot holds what;
* the **per-slot decision caches** -- ``$g_as_BestTargetCache[9]`` and ``$g_as_CanUseCache[9]``
  (``UtilityAI_Const.au3:9-10``), filled by the skill modules and dispatched with AutoIt's ``Call``.
  They are the plugin's *skill ranking* boundary: the functions behind them live in
  ``API/Plugins/UtilityAI/Skills/``, and ``UtilityAI_Spell.au3`` alone is 1,119 functions over 300 KB.
  **This is the part with no shortcut in a port**: what to cast is the source's content, and it has to be
  read out of the same tables rather than re-derived.
* the **casting pointer** -- ``$g_p_StaticSkillbarPtr`` (``:251``, ``:255``), one of the client pointers
  GwAu3 fills by scanning its own byte signatures in ``Core_Initialize``. Two members read it, and this
  project has no resolver for that pointer (``py4gw/gwa3/core.py`` states the same gap on the three
  status words).

What *is* portable is here already: `UAI_TargetIsValid`, which is two lines and a boolean in the source,
and it is ported exactly.
"""

from __future__ import annotations

import time
from typing import Any

from ..skillbar import SkillBar
from . import constants as _constants
from . import uai_const
from .cmd_agent import Agent_Attack, Agent_CallTarget, Agent_ChangeTarget
from .cmd_item import Item_DropBundle
from .cmd_map import Map_Move
from .core import Core_ControlAction
from .data_agent import (
    Agent_GetAgentInfo,
    Agent_GetDistance,
    Agent_GetDistanceSq,
    Agent_GetDistanceToXY,
    Agent_GetMyID,
)
from .data_map import Map_GetInstanceInfo, Map_GetMapID
from .data_skill import Skill_GetSkillbarInfo
from .uai_agent import UAI_GetAgentInfoByID, UAI_GetPlayerInfo
from .uai_best_target_cache import UAI_GetBestTargetFunc
from .uai_cache import (
    Cache_EndFormChangeBuild,
    Cache_FormChangeBuild,
    UAI_UpdateAgentCache,
    UAI_UpdatePlayerCache,
)
from .uai_can_cast import UAI_CanAutoAttack, UAI_CanDrop, UAI_CanUse
from .uai_can_use_cache import UAI_GetCanUseFunc
from .uai_effects import UAI_PlayerHasEffect
from .uai_filter import UAI_Filter_IsNotAvoided
from .uai_get_agent import UAI_FindAgentByPlayerNumber, UAI_GetNearestAgent, UAI_IsAgentInRange
from .uai_static_skill_cache import UAI_GetStaticSkillInfo, UAI_SlotIsPriority
from .uai_utils import (
    Party_IsWiped,
    UAI_CountEnemyInPartyAggroRange,
    UAI_GetNearestEnemyInPartyRange,
    UAI_GetPartyCalledTarget,
    UAI_IsEnemyInPartyAggroRange,
)
from .uai_weaponsets import (
    UAI_DetermineWeaponSets,
    UAI_GetBestWeaponSetBySkillSlot,
    UAI_ShouldSwitchWeaponSet,
)

__all__ = [
    "UAI_AutoAttack",
    "UAI_DropBundle",
    "UAI_Fight",
    "UAI_GetIsCastingSkill",
    "UAI_GetIsIdle",
    "UAI_PrioritySkills",
    "UAI_TargetIsValid",
    "UAI_TryUseSkill",
    "UAI_UseSkillEx",
    "UAI_UseSkills",
]

_CACHES = (
    "the static skill cache (`UAI_StaticDataSkill`/`UAI_GetStaticSkillInfo`, now ported in "
    "`py4gw/gwa3/uai_static_skill_cache.py` over the live skillbar) *and* the per-slot decision caches "
    "`$g_as_BestTargetCache[9]` and `$g_as_CanUseCache[9]` (`UtilityAI_Const.au3:9-10`), whose functions "
    "live in `API/Plugins/UtilityAI/Skills/`"
)
_RANKING = (
    "the per-slot decision caches `$g_as_BestTargetCache[9]` and `$g_as_CanUseCache[9]` "
    "(`UtilityAI_Const.au3:9-10`), whose functions live in `API/Plugins/UtilityAI/Skills/` -- "
    "`UtilityAI_Spell.au3` alone is 1,119 functions over 300 KB, and what to cast is the source's content"
)
_SKILLBAR = (
    "the client pointer `$g_p_StaticSkillbarPtr` (`:251`), which GwAu3 fills by scanning its own byte "
    "signatures in `Core_Initialize`; this project has no resolver for it, and `py4gw/gwa3/core.py` "
    "records the same gap for the status words"
)


def UAI_TargetIsValid(agent_id: Any, is_res: Any) -> bool:
    """Whether a target is in the state a resurrection (or a normal) skill needs
    (``UtilityAI_Core.au3:245-248``).

    One read and one choice, and the choice is GwAu3's own: ``$a_b_IsRes`` asks for a **dead** agent and
    anything else asks for a living one -- the same ``IsDead`` key, inverted for the common case. Both
    answers are routed: ``IsDead`` is a type-map comparison over the agent record
    (`py4gw/gwa3/data_agent.py`), live-verified for every record type.
    """

    is_dead = Agent_GetAgentInfo(agent_id, "IsDead")
    return is_dead if is_res else not is_dead


def UAI_GetIsIdle(agent_id: Any) -> bool:
    """Whether an agent is doing nothing (``:250-252``).

    GwAu3's two conditions, both routed: the **casting word** -- ``Memory_Read($g_p_StaticSkillbarPtr +
    0xB0)``, which is the skillbar's in-flight cast -- is zero, *and* the agent's own ``Skill`` column is
    zero. That word is answered here by `Skill_GetSkillbarInfo`'s ``Casting`` key, which reads the
    matched skillbar's cast-array size (`py4gw/gwa3/data_skill.py`), i.e. the same word through the same
    record: **the pointer the old refusal named turned out not to be needed**, because this layer reaches
    the skillbar by its agent id instead of by GwAu3's signature-scanned global.
    """

    casting = Skill_GetSkillbarInfo(1, "Casting")
    return casting == 0 and Agent_GetAgentInfo(agent_id, "Skill") == 0


def UAI_GetIsCastingSkill(agent_id: Any, skill_id: Any) -> bool:
    """Whether an agent's in-flight cast is a given skill (``:254-256``).

    The same two reads as `UAI_GetIsIdle`, with the casting word required to be **non-zero** and the
    agent's ``Skill`` column to equal the skill asked about.
    """

    casting = Skill_GetSkillbarInfo(1, "Casting")
    return casting != 0 and Agent_GetAgentInfo(agent_id, "Skill") == skill_id


def _call_strategy(name: Any, *args: Any) -> Any:
    """AutoIt's ``Call($name, ...)``: a strategy function resolved by name through this layer.

    The two ranking tables answer a **name** (`py4gw/gwa3/uai_best_target_cache.py`,
    `uai_can_use_cache.py`) and GwAu3's engine resolves it with AutoIt's ``Call``. This layer resolves it
    in its own callable surface, exactly as `_ApplyFilters` does for the filter strings -- the same name,
    the same function -- and a name that resolves to nothing answers ``0``, which is what ``Call``
    answers for an unknown function.
    """

    from .bridge import layer_surface

    routine = layer_surface().get(str(name))
    if routine is None:
        return 0
    return routine(*args)


def _priority_slots() -> list[int]:
    """The slots GwAu3's cache tagged as priority, computed live (``UtilityAI_StaticSkillCache.au3:174-177``).

    `UAI_CacheSkillBar` fills ``$g_ai_PrioritySlots`` at cache time by asking `UAI_SlotIsPriority` about
    each slot; this layer has no cache, so the same question is asked at the same moment it is used, in
    the same slot order.
    """

    return [slot for slot in range(1, 9) if UAI_SlotIsPriority(slot)]


def _priority_skill_used(aggro_range: float = 1320) -> int:
    """The **slot** the priority list used, or ``0`` -- AutoIt's ``SetExtended`` spelled out.

    ``UAI_PrioritySkills`` answers ``True`` *and* hands the slot back through ``@extended`` (``:135``),
    which its caller reads (``UAI_UseSkills``: ``Local $l_i_UsedSlot = @extended``). Python has no
    out-of-band return, so the slot travels as this private member's answer and `UAI_PrioritySkills`
    answers the source's boolean from it -- the same two facts, one call apart.
    """

    for slot in _priority_slots():
        if UAI_TryUseSkill(slot, aggro_range):
            return slot
    return 0


def UAI_UseSkills(x: Any, y: Any, aggro_range: float = 1320, max_distance_to_xy: float = 3500) -> Any:
    """The slot loop: try every skill on the bar, in order (``:72-129``).

    GwAu3's loop, kept step for step, because each step can end the pass early or skip to the next slot:

    1. an empty slot is skipped (``:74``);
    2. a form change is closed out when the flag says so (`Cache_EndFormChangeBuild`, ``:75``);
    3. the agent cache is refreshed, then four **exit** conditions end the whole pass: no enemy in party
       aggro range, the player dead or knocked down, an instance that is not explorable, or the player
       further from the fight origin than ``$a_f_MaxDistanceToXY`` allows (``:78-84``);
    4. when no enemy is in the player's own range but a hero has aggro, the player is walked toward the
       nearest one -- **once, with a 500 ms wait** -- and the pass ends for the next call to continue
       (``:87-97``);
    5. optionally a weapon set is chosen (``:100``);
    6. auto-attack, or a cancel when the client thinks it is attacking and the plugin does not (``:103-107``);
    7. the priority skills, and a slot that was just used is *retried* rather than followed by another
       cast (``:110-117``);
    8. the bundle drop, the slot's own attempt, and a 128 ms beat between slots (``:120-125``).

    **The weapon-set branch and the cancel are both ported, and the cancel is the source's own call.**
    The weapon-set call (``:100``) asks `UAI_ShouldSwitchWeaponSet`, which reaches `UAI_ChangeWeaponSet`
    only when a switch is actually needed; that member now presses the client's weapon-set control action
    (`docs/GWA3_ROUTE_MAP.md`). The cancel (``:106``) is
    ``Core_ControlAction($GC_I_CONTROL_ACTION_CANCEL_ACTION)``, which this layer performs as a press of
    that control action -- see `py4gw/gwa3/core.py`'s `Core_PerformAction` for the route and for the two
    words it refuses -- so the branch is the source's statement rather than a refusal.
    """

    for skill_slot in range(1, 9):
        if UAI_GetStaticSkillInfo(skill_slot, _constants.GC_UAI_STATIC_SKILL_SkillID) == 0:
            continue

        if uai_const.g_b_SkillChanged and Cache_EndFormChangeBuild(skill_slot):
            uai_const.g_b_SkillChanged = False

        UAI_UpdateAgentCache(aggro_range)

        if not UAI_IsEnemyInPartyAggroRange(aggro_range):
            break
        if (
            UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_IsDead)
            or UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_IsKnockedDown)
            or Map_GetInstanceInfo("Type") != _constants.GC_I_MAP_TYPE_EXPLORABLE
        ):
            break

        if max_distance_to_xy != 0 and Agent_GetDistanceToXY(x, y) > max_distance_to_xy:
            break

        if not UAI_IsAgentInRange(
            -2, aggro_range, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsNotAvoided"
        ) and Agent_GetDistanceToXY(x, y) <= aggro_range:
            party_range_enemy = UAI_GetNearestEnemyInPartyRange(aggro_range)
            if party_range_enemy != 0:
                enemy_x = UAI_GetAgentInfoByID(party_range_enemy, _constants.GC_UAI_AGENT_X)
                enemy_y = UAI_GetAgentInfoByID(party_range_enemy, _constants.GC_UAI_AGENT_Y)
                Map_Move(enemy_x, enemy_y, 0)
                time.sleep(500 / 1000.0)
            break

        if uai_const.g_b_CacheWeaponSet:
            UAI_ShouldSwitchWeaponSet()

        if UAI_CanAutoAttack():
            UAI_AutoAttack(aggro_range)
        else:
            if UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_IsAttacking):
                Core_ControlAction(_constants.GC_I_CONTROL_ACTION_CANCEL_ACTION)

        used_slot = 0
        if UAI_PrioritySkills(aggro_range):
            used_slot = _priority_skill_used(aggro_range)
            if used_slot == skill_slot:
                time.sleep(128 / 1000.0)
                continue
            UAI_UpdateAgentCache(aggro_range)

        UAI_DropBundle(aggro_range)

        UAI_TryUseSkill(skill_slot, aggro_range)

        time.sleep(128 / 1000.0)

    return True


def UAI_PrioritySkills(aggro_range: float = 1320) -> Any:
    """Whether a priority skill was used, and which one through `_priority_skill_used` (``:132-139``).

    The source walks its priority slots in order and **stops at the first skill it managed to use**,
    answering ``True`` and the slot through ``@extended``; this layer's answer is the same boolean, with
    the slot available from `_priority_skill_used` -- the documented twin of that channel. The strategy
    functions the dispatch reaches are the generated ones (`py4gw/gwa3/uai_strategy_*.py`).
    """

    return _priority_skill_used(aggro_range) != 0


def UAI_TryUseSkill(skill_slot: Any, aggro_range: float = 1320) -> Any:
    """Try to use one slot: check it, resolve its target, and cast it (``:141-160``).

    GwAu3's steps, in its order: `UAI_CanUse` first (``:142``); then the slot's **best target from the
    ranking** -- `UAI_GetBestTargetFunc(slot)` answers the ``BestTarget_*`` name and this layer calls it
    (``:144``); the forced target overrides it when the best target is an enemy (``:146-148``); a zero
    target and an avoided target both end the attempt (``:150-151``); the ``CanUse_*`` strategy answers
    whether the skill may be used *at all* and the distance gate is the last condition (``:153-154``);
    then the cast, and the form-change flag (``:156-157``).

    **One channel is missing and it is recorded rather than faked.** ``:145`` reads
    ``@extended`` from the target strategy for ``$GC_I_UAI_OVERRIDE_FORCE_TARGET`` -- a flagship skill
    ("You Are All Weaklings!") telling the engine to keep the forced target. ``@extended`` has no twin
    here, and a strategy body that calls ``SetExtended`` is **refused by the generator** (it names a
    function this layer does not implement), so the flag is always ``False`` and the strategies that
    would raise it say so at their own call sites instead of silently losing it.
    """

    if not UAI_CanUse(skill_slot):
        return False

    uai_const.g_i_BestTarget = _call_strategy(UAI_GetBestTargetFunc(skill_slot), aggro_range)

    # **The source's variable here IS the global** (`$g_i_BestTarget`), in all five of its uses: the
    # assignment, the allegiance test, the override, the zero test, the avoided test and the cast. So the
    # port writes and reads `uai_const.g_i_BestTarget` rather than a local -- which is what makes the
    # override visible to the rest of the plugin, as it is in GwAu3.
    override_force_target = False  # `@extended`; see the docstring.
    if (
        not override_force_target
        and uai_const.g_i_ForceTarget != 0
        and UAI_GetAgentInfoByID(uai_const.g_i_BestTarget, _constants.GC_UAI_AGENT_Allegiance)
        == _constants.GC_I_ALLEGIANCE_ENEMY
    ):
        uai_const.g_i_BestTarget = uai_const.g_i_ForceTarget

    if uai_const.g_i_BestTarget == 0:
        return False
    if not UAI_Filter_IsNotAvoided(uai_const.g_i_BestTarget):
        return False

    uai_const.g_b_CanUseSkill = bool(_call_strategy(UAI_GetCanUseFunc(skill_slot)))
    if not (
        uai_const.g_b_CanUseSkill and Agent_GetDistance(uai_const.g_i_BestTarget) < aggro_range
    ):
        return False

    UAI_UseSkillEx(skill_slot, uai_const.g_i_BestTarget, aggro_range)
    if Cache_FormChangeBuild(skill_slot):
        uai_const.g_b_SkillChanged = True

    return True


def UAI_UseSkillEx(
    skill_slot: Any, agent_id: Any = -2, aggro_range: float = 1320
) -> Any:
    """Use a slot on an agent, waiting for the client to cast it (``:163-243``).

    GwAu3's sequence, kept whole because every stage is a real wait:

    1. the target is changed when it is not the player (``:165``);
    2. in CALL mode the target is announced to the party, once per target (``:169-176``);
    3. the slot's skill id, type, activation, special flags and the three "is this instant" tests
       (``:178-190``) -- ``IsSpell`` is the seven casting types, ``InstantCast`` adds the two sacrifice
       glyphs, and ``TrackInstantCast`` excludes shouts and stances;
    4. the **idle wait**: up to 5000 ms until the client says it is idle, re-checking the target and
       `UAI_CanUse` on every pass (``:192-199``);
    5. the cast itself -- ``Skill_UseSkill(slot, target)``, which this project routes to the client's own
       casting call (`SkillBar.UseSkill`, `py4gw/skillbar.py:837`, the same substitution `Agent_Attack`
       makes), then a **cast-start wait** (1000 ms for a tracked instant cast, 5000 ms otherwise) and, for
       a non-instant skill, a **cast-end wait** bounded by the activation time -- doubled and a bit, or
       by the attack-speed cap (``:201-241``).

    **Both branches it names are ported.** The weapon-set branch (``:167``) calls
    `UAI_GetBestWeaponSetBySkillSlot`, which decides the set from the skill's own type and -- only when it
    has one to change to -- reaches `UAI_ChangeWeaponSet`, which presses the client's own weapon-set
    control action. The mid-cast cancel (``:228``) is
    ``Core_ControlAction($GC_I_CONTROL_ACTION_CANCEL_ACTION)``, performed as a press of that control
    action by this layer (`py4gw/gwa3/core.py`'s `Core_PerformAction` states the route).
    """

    my_id = Agent_GetMyID()
    if agent_id != my_id:
        Agent_ChangeTarget(agent_id)

    if uai_const.g_b_CacheWeaponSet:
        UAI_GetBestWeaponSetBySkillSlot(skill_slot)

    if uai_const.g_i_TargetMode == _constants.GC_UAI_TARGET_MODE_CALL:
        call_target = agent_id
        if uai_const.g_i_ForceTarget != 0:
            call_target = uai_const.g_i_ForceTarget
        if call_target != 0 and call_target != my_id and call_target != uai_const.g_i_LastCalledTarget:
            Agent_CallTarget(call_target)
            uai_const.g_i_LastCalledTarget = call_target

    skill_id = UAI_GetStaticSkillInfo(skill_slot, _constants.GC_UAI_STATIC_SKILL_SkillID)
    skill_type = UAI_GetStaticSkillInfo(skill_slot, _constants.GC_UAI_STATIC_SKILL_SkillType)
    activation_time = UAI_GetStaticSkillInfo(skill_slot, _constants.GC_UAI_STATIC_SKILL_Activation)
    special = UAI_GetStaticSkillInfo(skill_slot, _constants.GC_UAI_STATIC_SKILL_Special)

    is_res = (_constants.GC_I_SKILL_SPECIAL_FLAG_RESURRECTION & special) != 0
    is_spell = skill_type in (
        _constants.GC_I_SKILL_TYPE_SPELL,
        _constants.GC_I_SKILL_TYPE_HEX,
        _constants.GC_I_SKILL_TYPE_ENCHANTMENT,
        _constants.GC_I_SKILL_TYPE_WARD,
        _constants.GC_I_SKILL_TYPE_WELL,
        _constants.GC_I_SKILL_TYPE_WEAPON_SPELL,
        _constants.GC_I_SKILL_TYPE_ITEM_SPELL,
    )
    instant_cast = (
        is_spell
        and (
            UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_GLYPH_OF_SACRIFICE)
            or UAI_PlayerHasEffect(_constants.GC_I_SKILL_ID_GLYPH_OF_ESSENCE)
        )
    ) or (skill_type != _constants.GC_I_SKILL_TYPE_ATTACK and activation_time == 0)
    track_instant_cast = instant_cast and skill_type not in (
        _constants.GC_I_SKILL_TYPE_SHOUT,
        _constants.GC_I_SKILL_TYPE_STANCE,
    )

    idle_timeout = 5000
    idle_start = time.monotonic()
    while not UAI_GetIsIdle(my_id):
        if not UAI_TargetIsValid(agent_id, is_res):
            return False
        UAI_UpdatePlayerCache()
        if not UAI_CanUse(skill_slot):
            return False
        if (time.monotonic() - idle_start) * 1000 > idle_timeout:
            return False
        time.sleep(32 / 1000.0)

    if instant_cast:
        SkillBar.UseSkill(skill_slot, agent_id)
        if track_instant_cast:
            cast_start_timeout = 1000
            cast_start = time.monotonic()
            while not UAI_GetIsCastingSkill(my_id, 0):
                if not UAI_TargetIsValid(agent_id, is_res):
                    return False
                UAI_UpdatePlayerCache()
                if not UAI_CanUse(skill_slot):
                    return False
                if (time.monotonic() - cast_start) * 1000 > cast_start_timeout:
                    return False
    else:
        SkillBar.UseSkill(skill_slot, agent_id)
        cast_start_timeout = 5000
        cast_start = time.monotonic()
        while not UAI_GetIsCastingSkill(my_id, skill_id):
            if not UAI_TargetIsValid(agent_id, is_res):
                return False
            UAI_UpdatePlayerCache()
            if not UAI_CanUse(skill_slot):
                return False
            if (time.monotonic() - cast_start) * 1000 > cast_start_timeout:
                return False
            time.sleep(32 / 1000.0)

    if not instant_cast:
        aggro_range_sq = aggro_range * aggro_range
        decreased_attack_speed_cap = 4.05
        cast_end_timeout = (
            (decreased_attack_speed_cap * 1000) * 1.05
            if skill_type == _constants.GC_I_SKILL_TYPE_ATTACK
            else (activation_time * 1000) * 2.55
        )
        cast_end = time.monotonic()

        while UAI_GetIsCastingSkill(my_id, skill_id) and not Agent_GetAgentInfo(
            my_id, "IsKnockedDown"
        ):
            if not UAI_TargetIsValid(agent_id, is_res):
                Core_ControlAction(_constants.GC_I_CONTROL_ACTION_CANCEL_ACTION)
            if Agent_GetDistanceSq(agent_id) > aggro_range_sq:
                break
            if (time.monotonic() - cast_end) * 1000 > cast_end_timeout:
                break
            time.sleep(32 / 1000.0)

    return True


def UAI_DropBundle(aggro_range: float = 1320) -> Any:
    """Drop the item spell the player is holding, when the slot says so (``:259-296``).

    GwAu3 walks the eight slots looking for an **Item Spell**; for each one the player is actually
    holding (`UAI_PlayerHasEffect(skill_id)`), it re-casts it through the ranking's own target when
    `UAI_CanUse` allows, and otherwise asks `UAI_CanDrop` whether the bundle should be released -- with
    the first slot that answers dropping it and ending the walk (``:291-294``).

    The re-cast branch is `UAI_TryUseSkill`'s decision written out again by the source: the slot's
    ``BestTarget_*`` name, the forced-target override, the avoided test, the ``CanUse_*`` strategy and the
    distance gate, then `UAI_UseSkillEx` and the form-change flag. It is kept as the source writes it --
    the same steps, in the same order, with the agent-cache refresh the source makes afterwards.
    """

    for slot in range(1, 9):
        skill_type = UAI_GetStaticSkillInfo(slot, _constants.GC_UAI_STATIC_SKILL_SkillType)
        if skill_type != _constants.GC_I_SKILL_TYPE_ITEM_SPELL:
            continue

        skill_id = UAI_GetStaticSkillInfo(slot, _constants.GC_UAI_STATIC_SKILL_SkillID)
        if skill_id == 0:
            continue

        if not UAI_PlayerHasEffect(skill_id):
            continue

        if UAI_CanUse(slot):
            uai_const.g_i_BestTarget = _call_strategy(
                UAI_GetBestTargetFunc(slot), aggro_range
            )
            if (
                uai_const.g_i_ForceTarget != 0
                and UAI_GetAgentInfoByID(
                    uai_const.g_i_BestTarget, _constants.GC_UAI_AGENT_Allegiance
                )
                == _constants.GC_I_ALLEGIANCE_ENEMY
            ):
                uai_const.g_i_BestTarget = uai_const.g_i_ForceTarget
            if uai_const.g_i_BestTarget == 0:
                continue
            if not UAI_Filter_IsNotAvoided(uai_const.g_i_BestTarget):
                continue

            uai_const.g_b_CanUseSkill = bool(_call_strategy(UAI_GetCanUseFunc(slot)))

            if (
                uai_const.g_b_CanUseSkill
                and Agent_GetDistance(uai_const.g_i_BestTarget) < aggro_range
            ):
                UAI_UseSkillEx(slot, uai_const.g_i_BestTarget)
                if Cache_FormChangeBuild(slot):
                    uai_const.g_b_SkillChanged = True
                UAI_UpdateAgentCache(aggro_range)

        if UAI_CanDrop(slot):
            Item_DropBundle()
            return None

    return None


def UAI_AutoAttack(aggro_range: Any) -> Any:
    """Attack what should be attacked, and announce it (``:298-316``).

    Three sources for the target, in the source's order: the **forced** target if one is set; otherwise
    the remembered attack target while it is still alive; otherwise the nearest living enemy in range that
    is not avoided. A non-zero target is attacked -- `Agent_Attack(target, False)`, i.e. without calling
    it -- and the choice is remembered in ``$g_i_AttackTarget`` either way (``:310``).

    **The announcement has the source's own quirk and it is kept**: when nothing has been called yet in
    CALL mode, `Agent_CallTarget` is called with whatever the target is, *including zero* (``:312-315``) --
    GwAu3 announces "" as readily as a real target. Fixing that would change what the party sees.
    """

    attack_target = 0

    if uai_const.g_i_ForceTarget != 0:
        attack_target = uai_const.g_i_ForceTarget
    elif uai_const.g_i_AttackTarget != 0 and not UAI_GetAgentInfoByID(
        uai_const.g_i_AttackTarget, _constants.GC_UAI_AGENT_IsDead
    ):
        attack_target = uai_const.g_i_AttackTarget
    else:
        attack_target = UAI_GetNearestAgent(
            -2, aggro_range, "UAI_Filter_IsLivingEnemy|UAI_Filter_IsNotAvoided"
        )

    if attack_target != 0:
        Agent_Attack(attack_target, False)
    uai_const.g_i_AttackTarget = attack_target

    if (
        uai_const.g_i_LastCalledTarget == 0
        and uai_const.g_i_TargetMode == _constants.GC_UAI_TARGET_MODE_CALL
    ):
        Agent_CallTarget(attack_target)
        uai_const.g_i_LastCalledTarget = attack_target

    return None


def UAI_Fight(
    x: Any,
    y: Any,
    aggro_range: float = 1320,
    max_distance_to_xy: float = 3500,
    fight_mode: Any = None,
    switch_weapon_sets: bool = False,
    player_number: Any = 0,
    kill_only: bool = False,
    exit_callback: str = "",
    call_target_mode: Any = None,
) -> Any:
    """The engine: what a script calls to run a fight (``:3-69``).

    GwAu3's whole sequence, kept in its order: the mode and the bookkeeping globals are set (``:8-15``);
    ``$a_v_PlayerNumber`` is split into a **priority** list (positive numbers) and an **avoid** list
    (negative ones, absolute-valued), which is what a caller's ``[-3, 7]`` means (``:20-45``); the agent
    cache is refreshed and the priority target found when there is one (``:49-53``); the weapon sets are
    chosen when armed (``:55``); and then the loop, which ends on **any** of five conditions -- the player
    too far from the fight origin, the party wiped, the player dead, the map or its instance type changing,
    or the caller's own exit callback (``:57-68``) -- casting through `UAI_UseSkills` on every pass.

    **The weapon-set choice is ported**: the branch at ``:55`` calls `UAI_DetermineWeaponSets` when
    ``$a_b_SwitchWeaponSets`` is true (the source's own default is false), which reads and scores the
    four sets. What refuses is the *switch* `UAI_UseSkills` may then ask for, and it refuses inside
    `UAI_ChangeWeaponSet` where the source's own line is.

    **The exit callback is a name, as it is in GwAu3**, resolved through this layer's callable surface the
    way `_call_strategy` resolves a strategy: ``Call($a_s_ExitCallback)`` in the source calls a function in
    the script's own namespace, and a name that resolves to nothing answers ``0`` -- false -- which is what
    AutoIt's ``Call`` answers for an unknown function.
    """

    if fight_mode is None:
        fight_mode = _constants.g_i_FinisherMode
    if call_target_mode is None:
        call_target_mode = _constants.GC_UAI_TARGET_MODE_CALL

    uai_const.g_i_BestTarget = 0
    uai_const.g_i_ForceTarget = 0
    uai_const.g_i_AttackTarget = 0
    uai_const.g_i_LastCalledTarget = 0
    uai_const.g_i_FightMode = fight_mode
    uai_const.g_b_CacheWeaponSet = switch_weapon_sets
    uai_const.g_i_TargetMode = call_target_mode
    uai_const.g_v_AvoidPlayerNumbers = -1

    my_old_map = Map_GetMapID()
    map_loading_old = Map_GetInstanceInfo("Type")
    priority_targets: Any = 0

    if isinstance(player_number, (list, tuple)):
        prio: list[int] = []
        avoid: list[int] = []
        for number in player_number:
            if number > 0:
                prio.append(int(number))
            elif number < 0:
                avoid.append(abs(int(number)))
        if prio:
            priority_targets = prio
        if avoid:
            uai_const.g_v_AvoidPlayerNumbers = avoid
    elif player_number > 0:
        priority_targets = player_number
    elif player_number < 0:
        uai_const.g_v_AvoidPlayerNumbers = abs(int(player_number))

    has_priority = isinstance(priority_targets, (list, tuple)) or priority_targets != 0

    if has_priority:
        UAI_UpdateAgentCache(aggro_range)
        uai_const.g_i_ForceTarget = UAI_FindAgentByPlayerNumber(
            priority_targets, -2, aggro_range, "UAI_Filter_IsLivingEnemy"
        )
        if uai_const.g_i_ForceTarget == 0 and kill_only:
            return True

    if uai_const.g_b_CacheWeaponSet:
        UAI_DetermineWeaponSets()

    while True:
        if Agent_GetDistanceToXY(x, y) > aggro_range:
            break

        if uai_const.g_i_ForceTarget != 0 and UAI_GetAgentInfoByID(
            uai_const.g_i_ForceTarget, _constants.GC_UAI_AGENT_IsDead
        ):
            uai_const.g_i_ForceTarget = UAI_FindAgentByPlayerNumber(
                priority_targets, -2, aggro_range, "UAI_Filter_IsLivingEnemy"
            )
            if uai_const.g_i_ForceTarget == 0 and kill_only:
                break

        if uai_const.g_i_TargetMode == _constants.GC_UAI_TARGET_MODE_FOLLOW:
            follow_target = UAI_GetPartyCalledTarget()
            if follow_target != 0:
                uai_const.g_i_ForceTarget = follow_target

        UAI_UseSkills(x, y, aggro_range, max_distance_to_xy)

        if UAI_CountEnemyInPartyAggroRange(aggro_range) == 0:
            break
        if Agent_GetAgentInfo(-2, "IsDead"):
            break
        if Party_IsWiped():
            break
        if Map_GetMapID() != my_old_map:
            break
        if Map_GetInstanceInfo("Type") != map_loading_old:
            break
        if exit_callback != "" and _call_strategy(exit_callback):
            break

    return None
