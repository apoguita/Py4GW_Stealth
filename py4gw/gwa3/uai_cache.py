"""GwAu3's ``Cache/UtilityAI_Cache.au3``: the refresh calls the engine makes every iteration.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

**What the file is.** Six members, and three of them are the *refresh* half of the plugin's caches:
``UAI_UpdateAgentCache`` and ``UAI_UpdatePlayerCache`` refill the agent and player rows, and
``Cache_SkillBar`` refills the two per-slot **name** tables (``$g_as_BestTargetCache`` and
``$g_as_CanUseCache``) from `py4gw/gwa3/uai_best_target_cache.py` and `uai_can_use_cache.py`. The other
three are the form-change paths (`Cache_FormChangeBuild`, `Cache_EndFormChangeBuild`) and the runtime
reset.

**This port keeps the calls and drops the filling, which is the same substitution the rest of the layer
makes.** There is no frame loop here and nothing to dispatch to, so there is no cached row to refresh:
the agent and player columns are read live at the point of use, the static skill data is read live
(`py4gw/gwa3/uai_static_skill_cache.py`), and the two name tables are *answered* live by their own
dispatchers rather than filled. So:

* `UAI_UpdateAgentCache` and `UAI_UpdatePlayerCache` are **NOT APPLICABLE** and say so. They are calls a
  migrating script (and the engine) makes, and they answer ``None`` -- which is what the source's own
  ``EndFunc`` without a value answers -- so a caller that ignores them, as GwAu3's do, is unaffected;
* `Cache_SkillBar`, `Cache_FormChangeBuild` and `Cache_EndFormChangeBuild` are **routed**, because their
  *answers* are real (``True``/``False`` about an explorable area and about which skill is in a slot) and
  their cache calls are the layer's own live reads;
* `UAI_ResetRuntime` is **routed**: the six globals it resets now live in `py4gw/gwa3/uai_const.py`, and
  the three the source re-declares are caches this layer does not keep, which the member says.

**One branch is armed by a global, and it is ported.** ``Cache_SkillBar`` chooses weapon sets when
``$g_b_CacheWeaponSet`` is set (``:15``) -- a global a script assigns, **false by default** -- and it
calls `UAI_DetermineWeaponSets` (`py4gw/gwa3/uai_weaponsets.py`), which reads the four sets out of the
client's inventory struct and scores them. That is a read, so the armed path runs here; what still
refuses is the *switch* itself (`UAI_ChangeWeaponSet`), and it refuses inside that member where the
source's own line is, rather than at this call.
"""

from __future__ import annotations

from typing import Any

from . import constants as _constants
from . import uai_const
from . import uai_effects
from .data_map import Map_GetInstanceInfo
from .uai_static_skill_cache import UAI_CacheSkillBar, UAI_GetStaticSkillInfo
from .uai_weaponsets import UAI_DetermineWeaponSets

__all__ = [
    "Cache_EndFormChangeBuild",
    "Cache_FormChangeBuild",
    "Cache_SkillBar",
    "UAI_ResetRuntime",
    "UAI_UpdateAgentCache",
    "UAI_UpdatePlayerCache",
]

#: The skill ids each form's *strike* skills answer `False` for, as the source lists them
#: (``:32-37``). AutoIt matches case-insensitively, which is why the source may spell one of these
#: ``$GC_I_SKILL_ID_Totem_of_Man`` where its own constants file declares
#: ``$GC_I_SKILL_ID_TOTEM_OF_MAN``; the names here are the **declared** spellings, because Python does
#: care and the generated constants module carries the declared ones.
_BLESSING_SKILLS: frozenset[int] = frozenset(
    {
        _constants.GC_I_SKILL_ID_URSAN_BLESSING,
        _constants.GC_I_SKILL_ID_VOLFEN_BLESSING,
        _constants.GC_I_SKILL_ID_RAVEN_BLESSING,
    }
)

_FORM_STRIKE_SKILLS: frozenset[int] = frozenset(
    {
        _constants.GC_I_SKILL_ID_URSAN_STRIKE,
        _constants.GC_I_SKILL_ID_URSAN_RAGE,
        _constants.GC_I_SKILL_ID_URSAN_ROAR,
        _constants.GC_I_SKILL_ID_URSAN_FORCE,
        _constants.GC_I_SKILL_ID_TOTEM_OF_MAN,
        _constants.GC_I_SKILL_ID_RAVEN_TALONS,
        _constants.GC_I_SKILL_ID_RAVEN_SWOOP,
        _constants.GC_I_SKILL_ID_RAVEN_SHRIEK,
        _constants.GC_I_SKILL_ID_RAVEN_FLIGHT,
        _constants.GC_I_SKILL_ID_VOLFEN_CLAW,
        _constants.GC_I_SKILL_ID_VOLFEN_POUNCE,
        _constants.GC_I_SKILL_ID_VOLFEN_BLOODLUST,
        _constants.GC_I_SKILL_ID_VOLFEN_AGILITY,
    }
)


def Cache_SkillBar() -> Any:
    """Refresh the skillbar's caches, in an explorable area only (``UtilityAI_Cache.au3:5-18``).

    GwAu3's guard comes first and is kept: outside an explorable area it answers ``False`` without
    touching anything (``:6``). In an explorable area it refills the static skillbar table and the two
    per-slot **name** tables, then -- only when a script armed weapon-set switching -- chooses weapon
    sets, and answers ``True``.

    **The two name tables are not filled here, and a caller cannot tell.** GwAu3's engine reads them by
    slot and ``Call``s the name it finds; this layer answers that name from the slot's own skill id at the
    moment it is asked (`UAI_GetBestTargetFunc`), so the fill has nothing to do. Every other line is the
    source's.
    """

    if not Map_GetInstanceInfo("IsExplorable"):
        return False

    UAI_CacheSkillBar()

    if uai_const.g_b_CacheWeaponSet:
        UAI_DetermineWeaponSets()

    return True


def Cache_FormChangeBuild(skill_slot: Any) -> bool:
    """Whether a slot is a form's **blessing** -- and if so, refresh the skillbar
    (``UtilityAI_Cache.au3:20-28``).

    A form blessing *changes what the bar holds*, which is why the source refreshes the caches and
    answers ``True`` for those three skills and ``False`` for everything else. This layer's refresh is
    its own live read, so the answer is the whole observable behaviour and it is the source's own.
    """

    skill_id = UAI_GetStaticSkillInfo(skill_slot, _constants.GC_UAI_STATIC_SKILL_SkillID)

    if skill_id in _BLESSING_SKILLS:
        UAI_CacheSkillBar()
        return True
    return False


def Cache_EndFormChangeBuild(skill_slot: Any) -> bool:
    """Whether a slot is a form's **strike** skill, in which case the bar does *not* need refreshing
    (``UtilityAI_Cache.au3:30-42``).

    The three forms' strike lists answer ``False`` -- the bar is stable while they are in use -- and
    anything else answers ``True`` *after* refreshing, which is the source's own inversion of its
    sibling's answer.
    """

    skill_id = UAI_GetStaticSkillInfo(skill_slot, _constants.GC_UAI_STATIC_SKILL_SkillID)

    if skill_id in _FORM_STRIKE_SKILLS:
        return False

    UAI_CacheSkillBar()
    return True


def UAI_UpdateAgentCache(aggro_range: Any) -> None:
    """**NOT APPLICABLE in this port: the rows it refills are read live.**

    ``:44-49`` refills the agent cache (with ``$a_f_AggroRange + 500``), the effect and bond rows, the
    visible-effect rows and the dynamic skillbar rows. This layer has none of those tables: the agent
    columns come from the client at the point of use (`py4gw/gwa3/uai_agent.py`), the effect and bond
    questions from the client's own lists (`uai_effects.py`), and the dynamic skillbar from the live
    skillbar (`uai_static_skill_cache.py`). The call is kept because the engine and GwAu3's own scripts
    make it, and it answers ``None`` -- what the source's ``EndFunc`` without a value answers -- so a
    caller that ignores the result is unaffected.

    **A divergence, stated where it lives**: the freshness GwAu3 gets from this call, this layer gets
    from reading when asked. What it does not get is a *time* to measure from, which is why nothing here
    invents one.
    """

    return None


def UAI_UpdatePlayerCache() -> None:
    """**NOT APPLICABLE**, as `UAI_UpdateAgentCache`, for the controlled character (``:51-56``)."""

    return None


def UAI_ResetRuntime() -> None:
    """Reset the plugin's runtime state (``UtilityAI_Cache.au3:58-73``).

    **Seven globals, and they are all here now**: the four target bookkeeping words
    (``$g_i_BestTarget``, ``$g_i_ForceTarget``, ``$g_i_AttackTarget``, ``$g_i_LastCalledTarget``), the
    two flags (``$g_b_SkillChanged``, ``$g_b_CanUseSkill``) and
    ``$g_i_LastFeederEnchTimestamp`` (``:72``) -- each returned to the value its own file declares for
    it, which is what the source's assignments do, one by one. The feeder timestamp lives in
    `py4gw/gwa3/uai_effects.py`, the module named for the file that declares it, and resetting it here
    is what makes `UAI_GetFeederEnchOnTop` answer again after a reset.

    **The four things it re-declares are caches and pointers, and this layer keeps none of them**: the two
    name tables, the dynamic skill cache and ``$g_p_StaticSkillbarPtr``. The source re-declares them to
    zero their contents; there is nothing to zero here, and the member says so rather than shipping four
    empties that look like state.
    """

    uai_const.g_i_BestTarget = 0
    uai_const.g_i_ForceTarget = 0
    uai_const.g_i_AttackTarget = 0
    uai_const.g_i_LastCalledTarget = 0

    uai_const.g_b_SkillChanged = False
    uai_const.g_b_CanUseSkill = True

    uai_effects.g_i_LastFeederEnchTimestamp = 0

    return None
