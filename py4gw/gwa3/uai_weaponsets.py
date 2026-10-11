"""GwAu3's ``Equipment/UtilityAI_WeaponSets.au3``: the four weapon sets, read and chosen.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

**What the source does, and what the port can do about it.** The file has three jobs, and they have
three different outcomes here:

1. **Reading the sets out of memory** -- `UAI_DetermineWeaponSets` and everything it calls. The four
   sets' weapons are pointers in the client's own inventory struct, and the mod bytes are at the end
   of each item record; both are reads, and both are ported. This is the file's substance: eleven of
   its eighteen functions are the analysis (`UAI_SaveWeaponSetFromMemory`,
   `UAI_FindAndSaveModFromMemory`, `UAI_SearchModsInArray`, `UAI_ExtractHPBonus`,
   `UAI_ExtractEnergyBonus`) and the arithmetic that turns mods into scores.
2. **Choosing a set** -- `UAI_GetBestWeaponSetForCombat`, `UAI_GetBestWeaponSetBySkillSlot`,
   `UAI_FindWeaponSetByType`, `UAI_ShouldSwitchWeaponSet`, `UAI_GetWeaponSetForSituation`. They are
   decisions over the tables above and over the player's own health and energy; they are ported as
   written, with the source's thresholds and its hysteresis flags (which live in
   `py4gw/gwa3/uai_const.py`).
3. **Switching** -- `UAI_ChangeWeaponSet`, which is **routed**. Its first act is
   ``Core_PerformAction($GC_I_CONTROL_ACTION_CANCEL_ACTION, ...)`` and then
   ``Core_PerformAction($l_i_SetToUse, ...)``. GwAu3's own body fills its action struct and enqueues it
   (``GwAu3_Core.au3:568-573``), which is a code cave this project does not place; what the layer does
   instead is **press** the same client control action -- Reforged's own route for these actions
   (``Keybinds.ActivateWeaponSet``, ``routines_src/yield_src/keybinds.py:110-113``) -- and
   ``py4gw/gwa3/core.py``'s `Core_PerformAction` states that route, the words it refuses, and why.
   `Item_SwitchWeaponSet` presses the same four codes for GwAu3's ``HEADER_SWITCH_SET``, so both
   spellings a script can reach a weapon set by are live here.

**The three debug lines that matter are kept.** ``_D`` (``UtilityAI_Utils.au3:3-5``) is called 41
times in this file and is a no-op while ``$g_b_UAI_Debug`` is false, which is the state the plugin
starts in; every call is transcribed so that turning the switch on traces the same analysis the
source traces. See `py4gw/gwa3/uai_utils.py` for what the helper's own body does.

**Two findings are recorded rather than smoothed over**, both from reading the source's own text:

* ``UAI_GetBestWeaponSetForCombat``'s comments say "Enter defensive mode at 50%, stay until 70%" and
  "Enter low energy mode at 15, stay until 35" while the code beside them tests ``<= 0.30``/``>= 0.50``
  and ``<= 5``/``>= 25`` (``:409-427``). The code is what runs and the code is what is ported.
* ``UAI_FindAndSaveModFromMemory`` is handed an **item id** and passes it to `Item_GetModStruct`
  (``:186``), whose own body hands its argument to a reader that treats it as an **address**
  (``GwAu3_Data_Item.au3:776-781``). ``tests/probe_gwa3_inventory_live.py`` measured the consequence on
  this build: ``id + 0x10`` fails with Windows error 299, so the source's own analysis finds **no mods
  at all** when it runs. This layer's `Item_GetModStruct` takes the item the layer's callers hold -- an
  id or a record -- and reads its real mod array, which is what the source's caller means by it (its
  merchant caller passes a pointer); the divergence, and the scores it produces from the character's own
  bytes, are recorded in ``docs/GWA3_COMPAT_SPEC.md`` and asserted in
  ``tests/test_gwa3_uai_weaponsets_offline.py``.
"""

from __future__ import annotations

import re
import time
from typing import Any

from . import constants as _constants
from . import uai_const
from .core import Core_PerformAction
from .data_item import Item_GetInventoryInfo, Item_GetItemInfoByPtr, Item_GetModStruct
from .uai_agent import UAI_GetPlayerInfo
from .uai_static_skill_cache import UAI_GetStaticSkillInfo
from .uai_utils import _D

__all__ = [
    "UAI_ChangeWeaponSet",
    "UAI_DetermineWeaponSets",
    "UAI_ExtractEnergyBonus",
    "UAI_ExtractHPBonus",
    "UAI_FindAndSaveModFromMemory",
    "UAI_FindWeaponSetByType",
    "UAI_GetBestWeaponSetBySkillSlot",
    "UAI_GetBestWeaponSetForCombat",
    "UAI_GetOffhandTypeName",
    "UAI_GetWeaponSetForSituation",
    "UAI_GetWeaponTypeName",
    "UAI_IsOnWeaponSet",
    "UAI_IsRangedWeapon",
    "UAI_IsTwoHandedWeapon",
    "UAI_SaveWeaponSetFromMemory",
    "UAI_SearchModsInArray",
    "UAI_ShouldSwitchWeaponSet",
    "UAI_WeaponReqToItemType",
]


def _contains(text: Any, needle: Any) -> bool:
    """AutoIt's ``StringInStr($text, $needle) > 0`` -- **case-insensitive**, all of it.

    ``StringInStr`` compares case-insensitively unless ``Opt("StringCaseSense", 1)`` is set, and
    GwAu3 never sets it. The mod tables are upper-case hex and the byte string GwAu3 searches is the
    binary read of the item's mod array, whose text form is upper-case too -- so the case here is a
    fact about the client's own rendering, and this is the comparison the source makes either way.
    """

    return str(needle).upper() in str(text).upper()


def _replace(text: str, needle: str, replacement: str) -> str:
    """AutoIt's ``StringReplace($text, $needle, $replacement)`` -- case-insensitive, every occurrence.

    ``StringReplace``'s ``$i_Count`` defaults to ``0``, which means "replace all of them", and its
    comparison is the same case-insensitive one `_contains` records. So the mod that was found is
    struck out of the string wherever it appears, which is how the source keeps a later search from
    finding the same bytes twice.
    """

    return re.sub(re.escape(str(needle)), lambda _match: replacement, str(text), flags=re.IGNORECASE)


def UAI_DetermineWeaponSets() -> None:
    """Analyse all four weapon sets and fill the best-set trackers (``:4-49``).

    The source's own order: reset the ten trackers, walk sets ``1..4`` through
    `UAI_SaveWeaponSetFromMemory` (which reads each set out of memory rather than switching to it),
    then report. The report is `_D` output, and the four extra lines at the end are guarded by the
    debug switch in the source itself (``:42-47``) -- kept because that guard is a line of the file,
    even though the helper it guards reads the same switch.
    """

    _D(" ========== STARTING WEAPON SET ANALYSIS ==========")
    _D(" Reading weapon sets directly from memory (no switching required)")

    uai_const.g_ai_High_Hp_Set[0] = 0
    uai_const.g_ai_High_Hp_Set[1] = 0
    uai_const.g_ai_High_Energy_Set[0] = 0
    uai_const.g_ai_High_Energy_Set[1] = 0
    uai_const.g_ai_Best_Offensive_Set[0] = 0
    uai_const.g_ai_Best_Offensive_Set[1] = 0
    uai_const.g_ai_Best_Defensive_Set[0] = 0
    uai_const.g_ai_Best_Defensive_Set[1] = 0
    uai_const.g_ai_Best_Casting_Set[0] = 0
    uai_const.g_ai_Best_Casting_Set[1] = 0
    uai_const.g_ai_Best_Enchant_Set[0] = 0
    uai_const.g_ai_Best_Enchant_Set[1] = 0
    uai_const.g_ai_Best_Ranged_Set[0] = 0
    uai_const.g_ai_Best_Ranged_Set[1] = 0
    uai_const.g_ai_Best_Vampiric_Set[0] = 0
    uai_const.g_ai_Best_Vampiric_Set[1] = 0
    uai_const.g_ai_Best_Zealous_Set[0] = 0
    uai_const.g_ai_Best_Zealous_Set[1] = 0

    for set_number in range(4):
        set_num = set_number + 1
        _D(" --- Analyzing Weapon Set " + str(set_num) + " ---")
        UAI_SaveWeaponSetFromMemory(set_num)

    _D(" ========== ANALYSIS COMPLETE ==========")
    _D(" Best Sets Summary:")
    _D("   HP: Set #" + str(uai_const.g_ai_High_Hp_Set[1]) + " (+" + str(uai_const.g_ai_High_Hp_Set[0]) + " HP)")
    _D("   Energy: Set #" + str(uai_const.g_ai_High_Energy_Set[1]) + " (+" + str(uai_const.g_ai_High_Energy_Set[0]) + " Energy)")
    _D("   Offensive: Set #" + str(uai_const.g_ai_Best_Offensive_Set[1]) + " (Score: " + str(uai_const.g_ai_Best_Offensive_Set[0]) + ")")
    _D("   Defensive: Set #" + str(uai_const.g_ai_Best_Defensive_Set[1]) + " (Score: " + str(uai_const.g_ai_Best_Defensive_Set[0]) + ")")
    _D("   Casting: Set #" + str(uai_const.g_ai_Best_Casting_Set[1]) + " (Score: " + str(uai_const.g_ai_Best_Casting_Set[0]) + ")")
    if uai_const.g_b_UAI_Debug:
        if uai_const.g_ai_Best_Enchant_Set[1] > 0:
            _D("  Enchanting: Set #" + str(uai_const.g_ai_Best_Enchant_Set[1]))
        if uai_const.g_ai_Best_Ranged_Set[1] > 0:
            _D("  Ranged: Set #" + str(uai_const.g_ai_Best_Ranged_Set[1]))
        if uai_const.g_ai_Best_Vampiric_Set[1] > 0:
            _D("  Vampiric: Set #" + str(uai_const.g_ai_Best_Vampiric_Set[1]))
        if uai_const.g_ai_Best_Zealous_Set[1] > 0:
            _D("  Zealous: Set #" + str(uai_const.g_ai_Best_Zealous_Set[1]))
    _D(" ========================================")


def UAI_SaveWeaponSetFromMemory(a_i_Set: Any) -> None:
    """Read one weapon set out of the inventory struct and score it (``:52-180``).

    **A pointer here is a record, and zero is ``None``.** GwAu3 asks the inventory for
    ``WeaponSet0WeaponPtr`` and tests it with ``<> 0``; this layer's `Item_GetInventoryInfo` answers the
    **item record** the pointer addresses, and answers ``None`` where GwAu3 answers a zero pointer --
    the same substitution `Item_GetItemPtr` and `Item_GetBagPtr` record, because a client address is of
    no use to a caller here. So the source's ``If $l_p_WeaponPtr <> 0 Then`` is
    ``if weapon_ptr is not None`` below.

    The scoring is the source's: ``MaxHP`` and ``MaxEnergy`` accumulate from the mods,
    ``DefensiveScore`` takes the same HP bonus again, `UAI_SearchModsInArray` adds the offensive,
    defensive, casting and enchant scores, and the shield's flat ``20`` is added to the defensive
    total at the end (``:150``). Then each of the ten trackers is offered this set -- and the three
    boolean ones (ranged, vampiric, zealous) **only take the first set that has the property**,
    because their test is ``And $g_ai_Best_*_Set[0] = 0`` (``:166-179``).
    """

    if a_i_Set < 1 or a_i_Set > 4:
        return

    index = a_i_Set - 1
    set_index = a_i_Set - 1

    weapon_ptr = Item_GetInventoryInfo("WeaponSet" + str(set_index) + "WeaponPtr")
    offhand_ptr = Item_GetInventoryInfo("WeaponSet" + str(set_index) + "OffhandPtr")

    weapon_id = 0
    offhand_id = 0
    weapon_type = 0
    offhand_type = 0

    if weapon_ptr is not None:
        weapon_id = Item_GetItemInfoByPtr(weapon_ptr, "ItemID")
        weapon_type = Item_GetItemInfoByPtr(weapon_ptr, "ItemType")

    if offhand_ptr is not None:
        offhand_id = Item_GetItemInfoByPtr(offhand_ptr, "ItemID")
        offhand_type = Item_GetItemInfoByPtr(offhand_ptr, "ItemType")

    # The source writes and re-reads ``$g_a2D_WeaponSets[$l_i_Index][...]``; this is that row, held
    # once, because a Python list element is mutable and the alias is the same object every one of the
    # source's brackets reaches.
    row = uai_const.g_a2D_WeaponSets[index]
    row[_constants.GC_UAI_WEAPONSET_WeaponType] = weapon_type
    row[_constants.GC_UAI_WEAPONSET_WeaponId] = weapon_id
    row[_constants.GC_UAI_WEAPONSET_OffhandType] = offhand_type
    row[_constants.GC_UAI_WEAPONSET_OffhandId] = offhand_id
    row[_constants.GC_UAI_WEAPONSET_MaxHP] = 0
    row[_constants.GC_UAI_WEAPONSET_MaxEnergy] = 0
    row[_constants.GC_UAI_WEAPONSET_OffensiveScore] = 0
    row[_constants.GC_UAI_WEAPONSET_DefensiveScore] = 0
    row[_constants.GC_UAI_WEAPONSET_CastingScore] = 0
    row[_constants.GC_UAI_WEAPONSET_EnchantScore] = 0
    row[_constants.GC_UAI_WEAPONSET_IsRanged] = 1 if UAI_IsRangedWeapon(weapon_type) else 0
    row[_constants.GC_UAI_WEAPONSET_HasShield] = 1 if offhand_type == _constants.GC_I_TYPE_SHIELD else 0
    row[_constants.GC_UAI_WEAPONSET_HasVampiric] = 0
    row[_constants.GC_UAI_WEAPONSET_HasZealous] = 0

    _D(" Saving Set " + str(a_i_Set) + " (from memory):")
    _D("   WeaponPtr: " + str(weapon_ptr) + " | OffhandPtr: " + str(offhand_ptr))
    _D("   WeaponType: " + str(weapon_type) + " (" + UAI_GetWeaponTypeName(weapon_type) + ")")
    _D("   WeaponId: " + str(weapon_id))
    _D("   OffhandType: " + str(offhand_type) + " (" + UAI_GetOffhandTypeName(offhand_type) + ")")
    _D("   OffhandId: " + str(offhand_id))

    two_handed = UAI_IsTwoHandedWeapon(weapon_type)

    if weapon_id > 0:
        _D(" Analyzing Main Weapon mods..." + (" (Two-Handed)" if two_handed else ""))
        UAI_FindAndSaveModFromMemory(weapon_id, weapon_type, a_i_Set, 1)
    else:
        _D("   => No main weapon equipped")

    if two_handed:
        _D("   => Skipping offhand (two-handed weapon equipped)")
    elif offhand_id > 0:
        _D(" Analyzing Offhand mods...")
        UAI_FindAndSaveModFromMemory(offhand_id, offhand_type, a_i_Set, 2)
    else:
        _D("   => No offhand equipped")

    # The source writes and re-reads ``$g_a2D_WeaponSets[$l_i_Index][...]``; this is that row, held
    # once, because a Python list element is mutable and the alias is the same object the source's
    # every bracket reaches. The six scores below are read back through it after the mod analysis.
    set_hp = row[_constants.GC_UAI_WEAPONSET_MaxHP]
    set_energy = row[_constants.GC_UAI_WEAPONSET_MaxEnergy]
    off_score = row[_constants.GC_UAI_WEAPONSET_OffensiveScore]
    def_score = row[_constants.GC_UAI_WEAPONSET_DefensiveScore]
    cast_score = row[_constants.GC_UAI_WEAPONSET_CastingScore]
    ench_score = row[_constants.GC_UAI_WEAPONSET_EnchantScore]

    _D("   => Set Scores: HP+" + str(set_hp) + " | Energy+" + str(set_energy) + " | Off:" + str(off_score) + " | Def:" + str(def_score) + " | Cast:" + str(cast_score) + " | Ench:" + str(ench_score))

    if set_hp > uai_const.g_ai_High_Hp_Set[0]:
        uai_const.g_ai_High_Hp_Set[0] = set_hp
        uai_const.g_ai_High_Hp_Set[1] = a_i_Set

    if set_energy > uai_const.g_ai_High_Energy_Set[0]:
        uai_const.g_ai_High_Energy_Set[0] = set_energy
        uai_const.g_ai_High_Energy_Set[1] = a_i_Set

    if off_score > uai_const.g_ai_Best_Offensive_Set[0]:
        uai_const.g_ai_Best_Offensive_Set[0] = off_score
        uai_const.g_ai_Best_Offensive_Set[1] = a_i_Set

    total_def = set_hp + def_score + (row[_constants.GC_UAI_WEAPONSET_HasShield] * 20)
    if total_def > uai_const.g_ai_Best_Defensive_Set[0]:
        uai_const.g_ai_Best_Defensive_Set[0] = total_def
        uai_const.g_ai_Best_Defensive_Set[1] = a_i_Set

    if cast_score > uai_const.g_ai_Best_Casting_Set[0]:
        uai_const.g_ai_Best_Casting_Set[0] = cast_score
        uai_const.g_ai_Best_Casting_Set[1] = a_i_Set

    if ench_score > uai_const.g_ai_Best_Enchant_Set[0]:
        uai_const.g_ai_Best_Enchant_Set[0] = ench_score
        uai_const.g_ai_Best_Enchant_Set[1] = a_i_Set

    if row[_constants.GC_UAI_WEAPONSET_IsRanged] == 1 and uai_const.g_ai_Best_Ranged_Set[0] == 0:
        uai_const.g_ai_Best_Ranged_Set[0] = 1
        uai_const.g_ai_Best_Ranged_Set[1] = a_i_Set

    if row[_constants.GC_UAI_WEAPONSET_HasVampiric] == 1 and uai_const.g_ai_Best_Vampiric_Set[0] == 0:
        uai_const.g_ai_Best_Vampiric_Set[0] = 1
        uai_const.g_ai_Best_Vampiric_Set[1] = a_i_Set

    if row[_constants.GC_UAI_WEAPONSET_HasZealous] == 1 and uai_const.g_ai_Best_Zealous_Set[0] == 0:
        uai_const.g_ai_Best_Zealous_Set[0] = 1
        uai_const.g_ai_Best_Zealous_Set[1] = a_i_Set


def UAI_FindAndSaveModFromMemory(a_i_ItemId: Any, a_i_ItemType: Any, a_i_Set: Any, a_i_Weapon: Any) -> None:
    """Find an item's mods and save their scores into its set's row (``:184-240``).

    The weapon's own type chooses the two tables to search -- the upgrade table for that weapon class
    and its inscription table -- and the source's ``Switch`` is the mapping: bow, axe, hammer, daggers,
    scythe, spear and sword each search their own upgrade table plus the **martial** inscriptions, and
    wand and staff share one table with the **spell-casting** inscriptions (``:195-220``). An offhand
    searches the focus or shield table plus the focus/shield inscriptions (``:223-232``), and a
    two-handed weapon never reaches here for its offhand at all (`UAI_SaveWeaponSetFromMemory` skips
    it).

    ``$l_i_Finding`` counts the mods found so far and is also the index they are written at, which is
    why the searches run in sequence over one counter rather than in parallel.
    """

    finding = 0
    mod_struct = Item_GetModStruct(a_i_ItemId)
    new_mod_struct = ""
    weapon_slot = "Main Hand" if a_i_Weapon == 1 else "Offhand"

    _D("   Item ID: " + str(a_i_ItemId) + " (" + weapon_slot + ")")
    _D("   Raw ModStruct: " + str(mod_struct))

    if a_i_Weapon == 1:
        _D("   Weapon Type: " + str(a_i_ItemType) + " (" + UAI_GetWeaponTypeName(a_i_ItemType) + ")")
        if a_i_ItemType == _constants.GC_I_TYPE_BOW:
            new_mod_struct, finding = UAI_SearchModsInArray(uai_const.g_as2_BowUpgrade, mod_struct, new_mod_struct, finding, a_i_Set, a_i_Weapon)
            new_mod_struct, finding = UAI_SearchModsInArray(uai_const.g_as2_MartialWeaponsInscription, mod_struct, new_mod_struct, finding, a_i_Set, a_i_Weapon)
        elif a_i_ItemType == _constants.GC_I_TYPE_AXE:
            new_mod_struct, finding = UAI_SearchModsInArray(uai_const.g_as2_AxeUpgrade, mod_struct, new_mod_struct, finding, a_i_Set, a_i_Weapon)
            new_mod_struct, finding = UAI_SearchModsInArray(uai_const.g_as2_MartialWeaponsInscription, mod_struct, new_mod_struct, finding, a_i_Set, a_i_Weapon)
        elif a_i_ItemType == _constants.GC_I_TYPE_HAMMER:
            new_mod_struct, finding = UAI_SearchModsInArray(uai_const.g_as2_HammerUpgrade, mod_struct, new_mod_struct, finding, a_i_Set, a_i_Weapon)
            new_mod_struct, finding = UAI_SearchModsInArray(uai_const.g_as2_MartialWeaponsInscription, mod_struct, new_mod_struct, finding, a_i_Set, a_i_Weapon)
        elif a_i_ItemType == _constants.GC_I_TYPE_DAGGERS:
            new_mod_struct, finding = UAI_SearchModsInArray(uai_const.g_as2_DaggerUpgrade, mod_struct, new_mod_struct, finding, a_i_Set, a_i_Weapon)
            new_mod_struct, finding = UAI_SearchModsInArray(uai_const.g_as2_MartialWeaponsInscription, mod_struct, new_mod_struct, finding, a_i_Set, a_i_Weapon)
        elif a_i_ItemType == _constants.GC_I_TYPE_SCYTHE:
            new_mod_struct, finding = UAI_SearchModsInArray(uai_const.g_as2_ScytheUpgrade, mod_struct, new_mod_struct, finding, a_i_Set, a_i_Weapon)
            new_mod_struct, finding = UAI_SearchModsInArray(uai_const.g_as2_MartialWeaponsInscription, mod_struct, new_mod_struct, finding, a_i_Set, a_i_Weapon)
        elif a_i_ItemType == _constants.GC_I_TYPE_SPEAR:
            new_mod_struct, finding = UAI_SearchModsInArray(uai_const.g_as2_SpearUpgrade, mod_struct, new_mod_struct, finding, a_i_Set, a_i_Weapon)
            new_mod_struct, finding = UAI_SearchModsInArray(uai_const.g_as2_MartialWeaponsInscription, mod_struct, new_mod_struct, finding, a_i_Set, a_i_Weapon)
        elif a_i_ItemType == _constants.GC_I_TYPE_SWORD:
            new_mod_struct, finding = UAI_SearchModsInArray(uai_const.g_as2_SwordUpgrade, mod_struct, new_mod_struct, finding, a_i_Set, a_i_Weapon)
            new_mod_struct, finding = UAI_SearchModsInArray(uai_const.g_as2_MartialWeaponsInscription, mod_struct, new_mod_struct, finding, a_i_Set, a_i_Weapon)
        elif a_i_ItemType in (_constants.GC_I_TYPE_WAND, _constants.GC_I_TYPE_STAFF):
            new_mod_struct, finding = UAI_SearchModsInArray(uai_const.g_as2_StaffWandUpgrade, mod_struct, new_mod_struct, finding, a_i_Set, a_i_Weapon)
            new_mod_struct, finding = UAI_SearchModsInArray(uai_const.g_as2_SpellCastingWeaponsInscription, mod_struct, new_mod_struct, finding, a_i_Set, a_i_Weapon)
    elif a_i_Weapon == 2:
        _D("   Offhand Type: " + str(a_i_ItemType) + " (" + UAI_GetOffhandTypeName(a_i_ItemType) + ")")
        if a_i_ItemType == _constants.GC_I_TYPE_OFFHAND:
            new_mod_struct, finding = UAI_SearchModsInArray(uai_const.g_as2_FocusUpgrade, mod_struct, new_mod_struct, finding, a_i_Set, a_i_Weapon)
            new_mod_struct, finding = UAI_SearchModsInArray(uai_const.g_as2_FocusShieldWeaponsInscription, mod_struct, new_mod_struct, finding, a_i_Set, a_i_Weapon)
        elif a_i_ItemType == _constants.GC_I_TYPE_SHIELD:
            new_mod_struct, finding = UAI_SearchModsInArray(uai_const.g_as2_ShieldUpgrade, mod_struct, new_mod_struct, finding, a_i_Set, a_i_Weapon)
            new_mod_struct, finding = UAI_SearchModsInArray(uai_const.g_as2_FocusShieldWeaponsInscription, mod_struct, new_mod_struct, finding, a_i_Set, a_i_Weapon)
        elif a_i_ItemType == 0:
            _D("   => Empty offhand slot")

    if finding == 0:
        _D("   => No mods found")
    else:
        _D("   => Total mods found: " + str(finding))


def UAI_FindWeaponSetByType(a_i_Type: Any) -> int:
    """Which set carries a weapon of this type (``:242-262``).

    The source's three answers, in its own order: ``5`` when the player **already** has that weapon
    type equipped, the set number ``1..4`` when a set holds one, and ``0`` when no set does. ``5`` is
    not a set number and every caller tests for it before using the number as one.
    """

    _D(" Searching for weapon type " + str(a_i_Type) + "...")
    current_type = UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_WeaponItemType)
    _D(" Current weapon type: " + str(current_type))

    if current_type == a_i_Type:
        _D(" => Already equipped type " + str(a_i_Type) + "! (returning 5)")
        return 5

    for set_number in range(4):
        set_type = uai_const.g_a2D_WeaponSets[set_number][_constants.GC_UAI_WEAPONSET_WeaponType]
        _D(" Set " + str(set_number + 1) + " has weapon type: " + str(set_type))
        if set_type == a_i_Type:
            _D(" => Found type " + str(a_i_Type) + " in Set " + str(set_number + 1) + "!")
            return set_number + 1

    _D(" => Weapon type " + str(a_i_Type) + " not found (returning 0)")
    return 0


def UAI_GetBestWeaponSetBySkillSlot(a_i_SkillSlot: Any) -> None:
    """Choose a weapon set for one skill slot (``:269-371``).

    Three priorities, the source's own: **survival** (health under a quarter and a defensive set
    exists, unless the skill is an attack or an enchantment), then **energy** (the skill costs more
    than the player has and a high-energy set exists, with the same two skill-type exceptions), then
    the per-skill-type choice.

    **The skill's type decides which tracker is consulted**, and the source's ``Switch`` is the whole
    of that table: casting skills prefer the casting set, enchantments prefer the enchant set and fall
    back to casting, attacks resolve their weapon requirement to an item type and look for that set,
    stances and pet attacks prefer the offensive set, preparations prefer the ranged set, shouts,
    chants, echoes, traps and forms keep the current set, and an unknown type keeps it too (``:289-365``).

    The answer is by effect, not by return value: the source calls `UAI_ChangeWeaponSet` when it found
    a set, and returns nothing on every path -- including the paths that decide to leave the set alone.
    That is kept, so this member reaches the switch itself and only when a set was actually chosen.
    """

    hp = UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_HP)
    current_energy = UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_CurrentEnergy)
    skill_energy_cost = UAI_GetStaticSkillInfo(a_i_SkillSlot, _constants.GC_UAI_STATIC_SKILL_EnergyCost)
    skill_type = UAI_GetStaticSkillInfo(a_i_SkillSlot, _constants.GC_UAI_STATIC_SKILL_SkillType)
    best_set = 0

    if (
        hp < 0.25
        and uai_const.g_ai_Best_Defensive_Set[1] > 0
        and skill_type != _constants.GC_I_SKILL_TYPE_ATTACK
        and skill_type != _constants.GC_I_SKILL_TYPE_ENCHANTMENT
    ):
        UAI_ChangeWeaponSet(uai_const.g_ai_Best_Defensive_Set[1])
        return

    if (
        current_energy < skill_energy_cost
        and uai_const.g_ai_High_Energy_Set[1] > 0
        and skill_type != _constants.GC_I_SKILL_TYPE_ATTACK
        and skill_type != _constants.GC_I_SKILL_TYPE_ENCHANTMENT
    ):
        UAI_ChangeWeaponSet(uai_const.g_ai_High_Energy_Set[1])
        return

    if skill_type in (
        _constants.GC_I_SKILL_TYPE_HEX,
        _constants.GC_I_SKILL_TYPE_SPELL,
        _constants.GC_I_SKILL_TYPE_SIGNET,
        _constants.GC_I_SKILL_TYPE_CONDITION,
        _constants.GC_I_SKILL_TYPE_WELL,
        _constants.GC_I_SKILL_TYPE_WARD,
        _constants.GC_I_SKILL_TYPE_ITEM_SPELL,
        _constants.GC_I_SKILL_TYPE_WEAPON_SPELL,
    ):
        if uai_const.g_ai_Best_Casting_Set[1] > 0:
            best_set = uai_const.g_ai_Best_Casting_Set[1]
    elif skill_type == _constants.GC_I_SKILL_TYPE_ENCHANTMENT:
        if uai_const.g_ai_Best_Enchant_Set[1] > 0:
            best_set = uai_const.g_ai_Best_Enchant_Set[1]
        elif uai_const.g_ai_Best_Casting_Set[1] > 0:
            best_set = uai_const.g_ai_Best_Casting_Set[1]
    elif skill_type == _constants.GC_I_SKILL_TYPE_ATTACK:
        weapon_req = UAI_GetStaticSkillInfo(a_i_SkillSlot, _constants.GC_UAI_STATIC_SKILL_WeaponReq)
        current_weapon_type = UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_WeaponItemType)
        required_item_type = UAI_WeaponReqToItemType(weapon_req)

        if required_item_type > 0 and current_weapon_type != required_item_type:
            best_set = UAI_FindWeaponSetByType(required_item_type)
            if best_set == 5:
                return
    elif skill_type == _constants.GC_I_SKILL_TYPE_STANCE:
        if uai_const.g_ai_Best_Offensive_Set[1] > 0:
            best_set = uai_const.g_ai_Best_Offensive_Set[1]
    elif skill_type in (
        _constants.GC_I_SKILL_TYPE_SHOUT,
        _constants.GC_I_SKILL_TYPE_CHANT,
        _constants.GC_I_SKILL_TYPE_ECHO_REFRAIN,
    ):
        return
    elif skill_type == _constants.GC_I_SKILL_TYPE_PREPARATION:
        if uai_const.g_ai_Best_Ranged_Set[1] > 0:
            best_set = uai_const.g_ai_Best_Ranged_Set[1]
    elif skill_type == _constants.GC_I_SKILL_TYPE_TRAP:
        return
    elif skill_type == _constants.GC_I_SKILL_TYPE_RITUAL:
        if uai_const.g_ai_Best_Casting_Set[1] > 0:
            best_set = uai_const.g_ai_Best_Casting_Set[1]
    elif skill_type == _constants.GC_I_SKILL_TYPE_GLYPH:
        if uai_const.g_ai_Best_Casting_Set[1] > 0:
            best_set = uai_const.g_ai_Best_Casting_Set[1]
    elif skill_type == _constants.GC_I_SKILL_TYPE_FORM:
        return
    elif skill_type == _constants.GC_I_SKILL_TYPE_PETATTACK:
        if uai_const.g_ai_Best_Offensive_Set[1] > 0:
            best_set = uai_const.g_ai_Best_Offensive_Set[1]
    else:
        return

    if best_set > 0 and best_set <= 4:
        UAI_ChangeWeaponSet(best_set)


def UAI_WeaponReqToItemType(a_i_WeaponReq: Any) -> int:
    """A skill's weapon requirement as an item type (``:377-396``).

    GwAu3's own seven cases and its ``Case Else`` of ``0``. The requirement values are **bits**
    (``1`` axe, ``2`` bow, ``8`` dagger, ``16`` hammer, ``32`` scythe, ``64`` spear, ``128`` sword)
    while the item types are the constants on the right of each case -- and the two sets of numbers
    have nothing to do with each other, which is why the switch exists rather than a conversion.
    """

    if a_i_WeaponReq == 1:
        return _constants.GC_I_TYPE_AXE
    if a_i_WeaponReq == 2:
        return _constants.GC_I_TYPE_BOW
    if a_i_WeaponReq == 8:
        return _constants.GC_I_TYPE_DAGGERS
    if a_i_WeaponReq == 16:
        return _constants.GC_I_TYPE_HAMMER
    if a_i_WeaponReq == 32:
        return _constants.GC_I_TYPE_SCYTHE
    if a_i_WeaponReq == 64:
        return _constants.GC_I_TYPE_SPEAR
    if a_i_WeaponReq == 128:
        return _constants.GC_I_TYPE_SWORD
    return 0


def UAI_GetBestWeaponSetForCombat() -> int:
    """The set combat should be fought on (``:404-442``).

    The source's three priorities and its fallback, always answering a usable set number:

    1. **defensive** while the hysteresis flag is set, then the defensive tracker and then the
       high-HP tracker;
    2. **energy** while its flag is set, then the high-energy tracker and then the zealous tracker;
    3. the offensive tracker, then the casting tracker, then the high-HP tracker, and ``1`` if nothing
       ever qualified (``:441``).

    **The flags are the flip-flop guard and their thresholds are the code's, not the comments'.** The
    comment above the health test says "Enter defensive mode at 50%, stay until 70%" and the code tests
    ``<= 0.30`` to enter and ``>= 0.50`` to leave; the energy comment says "at 15, stay until 35" and
    the code tests ``<= 5`` and ``>= 25`` (``:409-427``). The numbers that run are the numbers ported,
    and the disagreement is recorded in this module's header rather than resolved here.
    """

    hp = UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_HP)
    current_energy = UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_CurrentEnergy)

    if hp <= 0.30:
        uai_const.g_b_InDefensiveMode = True
    elif hp >= 0.50:
        uai_const.g_b_InDefensiveMode = False

    if uai_const.g_b_InDefensiveMode:
        if uai_const.g_ai_Best_Defensive_Set[1] > 0:
            return uai_const.g_ai_Best_Defensive_Set[1]
        if uai_const.g_ai_High_Hp_Set[1] > 0:
            return uai_const.g_ai_High_Hp_Set[1]

    if current_energy <= 5:
        uai_const.g_b_InLowEnergyMode = True
    elif current_energy >= 25:
        uai_const.g_b_InLowEnergyMode = False

    if uai_const.g_b_InLowEnergyMode:
        if uai_const.g_ai_High_Energy_Set[1] > 0:
            return uai_const.g_ai_High_Energy_Set[1]
        if uai_const.g_ai_Best_Zealous_Set[1] > 0:
            return uai_const.g_ai_Best_Zealous_Set[1]

    if uai_const.g_ai_Best_Offensive_Set[1] > 0:
        return uai_const.g_ai_Best_Offensive_Set[1]

    if uai_const.g_ai_Best_Casting_Set[1] > 0:
        return uai_const.g_ai_Best_Casting_Set[1]
    if uai_const.g_ai_High_Hp_Set[1] > 0:
        return uai_const.g_ai_High_Hp_Set[1]

    return 1


def UAI_ShouldSwitchWeaponSet() -> bool:
    """Whether combat should move to another set, and the move itself (``:449-458``).

    The source asks `UAI_GetBestWeaponSetForCombat` for the set it wants, answers ``False`` when the
    player is already on it (``:453``, through `UAI_IsOnWeaponSet`, which compares **item ids** and not
    weapon types), and otherwise calls `UAI_ChangeWeaponSet` and answers ``True`` to mean "the set was
    changed".

    **The ``True`` means the switch was asked for and performed as far as the client's own read can
    say.** `UAI_ChangeWeaponSet` presses the set's control action and then loops until
    `UAI_IsOnWeaponSet` reports it took, up to the source's own 400 ms deadlock, so this member's ``True``
    is the source's claim on the source's terms -- a switch that the client did not make within 400 ms is
    still ``True`` here, exactly as it is in GwAu3.
    """

    best_set = UAI_GetBestWeaponSetForCombat()

    if UAI_IsOnWeaponSet(best_set):
        return False

    UAI_ChangeWeaponSet(best_set)
    return True


def UAI_GetWeaponSetForSituation(a_s_Situation: Any) -> int:
    """The set that fits a named situation (``:465-488``).

    GwAu3's nine names -- ``"defensive"``, ``"offensive"``, ``"casting"``, ``"enchanting"``,
    ``"ranged"``, ``"energy"``, ``"hp"``, ``"vampiric"``, ``"zealous"`` -- and ``0`` for anything else.
    Each answers the tracker's own set number, so a tracker that found nothing answers ``0`` here,
    which is the source's own "no set for this situation".

    **The comparison is AutoIt's ``Switch``, which is case-insensitive for strings** unless
    ``Opt("StringCaseSense", 1)`` is set -- and GwAu3 never sets it. ``"Defensive"`` therefore matches
    the ``"defensive"`` case in the source, and the lower-casing below is that rule rather than a
    normalisation this port chose.
    """

    situation = str(a_s_Situation).lower()
    if situation == "defensive":
        return uai_const.g_ai_Best_Defensive_Set[1]
    if situation == "offensive":
        return uai_const.g_ai_Best_Offensive_Set[1]
    if situation == "casting":
        return uai_const.g_ai_Best_Casting_Set[1]
    if situation == "enchanting":
        return uai_const.g_ai_Best_Enchant_Set[1]
    if situation == "ranged":
        return uai_const.g_ai_Best_Ranged_Set[1]
    if situation == "energy":
        return uai_const.g_ai_High_Energy_Set[1]
    if situation == "hp":
        return uai_const.g_ai_High_Hp_Set[1]
    if situation == "vampiric":
        return uai_const.g_ai_Best_Vampiric_Set[1]
    if situation == "zealous":
        return uai_const.g_ai_Best_Zealous_Set[1]
    return 0


def UAI_ChangeWeaponSet(a_i_Set: Any) -> None:
    """Switch to a weapon set (``:490-522``) -- **routed, and each send is the client's own press**.

    The source's steps, in its order: the **already-on-it** quick check first (``:492``, which is why
    a caller that asks for the set it is on pays nothing); then the ``Switch`` that turns a set number
    into the client's own control code (``$GC_I_CONTROL_INVENTORY_ACTIVATE_WEAPON_SET_1`` .. ``_4``,
    ``:495-504``); a timer; a **double cancel** -- two ``Core_PerformAction`` cancels 32 ms apart, to be
    sure the client will accept the switch; and then a ``Do`` loop that sends the switch every 32 ms
    until `UAI_IsOnWeaponSet` says it took, with a 400 ms deadlock (``:506-521``).

    **All four sends are ``Core_PerformAction``, and that member is routed.** GwAu3's own body fills its
    action struct and enqueues it (``GwAu3_Core.au3:568-573``); this layer performs the same control
    action by **pressing** it -- ``UIManager.Keydown``/``Keyup``, the route Reforged's
    ``Keybinds.ActivateWeaponSet`` uses for this exact effect (``routines_src/yield_src/keybinds.py:110-113``,
    down and up at ``routines_src/behaviourtrees_src/keybinds.py:101,119``). `py4gw/gwa3/core.py`'s
    `Core_PerformAction` states the route and the two words it refuses (the deactivate flag and a non-zero
    type). The four codes this member passes are the four the port's own control-action enum carries
    (``ControlAction_ActivateWeaponSet1..4``, ``0x81``-``0x84``, ``py4gw/enums_src/ui_enums.py:546-549``),
    and the loop's 32 ms beats and its 400 ms deadlock are the source's own.

    ``UAI_IsOnWeaponSet`` is a **read** of the client's active set, so the loop's exit is observable, and
    a caller can check the effect rather than trust the send: ``Item_SwitchWeaponSet`` presses the same
    four codes for GwAu3's ``HEADER_SWITCH_SET``.
    """

    if UAI_IsOnWeaponSet(a_i_Set):
        return

    set_to_use = 0
    if a_i_Set == 1:
        set_to_use = _constants.GC_I_CONTROL_INVENTORY_ACTIVATE_WEAPON_SET_1
    elif a_i_Set == 2:
        set_to_use = _constants.GC_I_CONTROL_INVENTORY_ACTIVATE_WEAPON_SET_2
    elif a_i_Set == 3:
        set_to_use = _constants.GC_I_CONTROL_INVENTORY_ACTIVATE_WEAPON_SET_3
    elif a_i_Set == 4:
        set_to_use = _constants.GC_I_CONTROL_INVENTORY_ACTIVATE_WEAPON_SET_4

    deadlock = time.monotonic() * 1000

    Core_PerformAction(_constants.GC_I_CONTROL_ACTION_CANCEL_ACTION, _constants.GC_I_CONTROL_TYPE_ACTIVATE)
    time.sleep(32 / 1000.0)
    Core_PerformAction(_constants.GC_I_CONTROL_ACTION_CANCEL_ACTION, _constants.GC_I_CONTROL_TYPE_ACTIVATE)
    time.sleep(32 / 1000.0)

    while True:
        Core_PerformAction(set_to_use, _constants.GC_I_CONTROL_TYPE_ACTIVATE)
        time.sleep(32 / 1000.0)
        if UAI_IsOnWeaponSet(a_i_Set) or (time.monotonic() * 1000 - deadlock) > 400:
            break


def UAI_SearchModsInArray(
    a_as2_UpgradeArray: Any,
    a_s_ModStruct: Any,
    a_s_NewModStruct: Any,
    a_i_Finding: Any,
    a_i_Set: Any,
    a_i_Weapon: Any,
) -> tuple[str, int]:
    """Find this table's mods in an item's mod bytes (``:525-611``).

    The source's search, step for step: walk the upgrade table in order; search either the **raw** mod
    string (while nothing has been found yet) or the **remaining** one (once something has, ``:528``);
    on a hit, record the mod's *name* in ``$g_as3_Weapon_Mods`` at the slot the finding counter points
    at, **strike the matched bytes out** of the working string so a later row cannot match the same
    bytes again, and score the mod.

    **The scoring is the file's own table of weights**, and each line is one of them: ``+33%`` condition
    mods ``5``, ``Damage +15%``/``Damage 20%`` inscriptions ``15``, ``Sundering`` ``20``, ``Vampiric``
    ``15``, ``Zealous`` ``10``, ``Furious`` ``10``; ``Armor +`` ``10``, ``armor vs`` ``7``, ``Damage -``
    ``5``, ``-20%`` condition-duration ``3``; ``HCT20``/``HSR20`` ``20`` and ``HCT10``/``HSR10`` ``10``;
    and ``Enchantment Duration`` -- or a mod whose *name* contains ``Enchanting`` -- ``20`` on the
    enchant score. Health mods also add to ``MaxHP`` and ``MaxEnergy`` through `UAI_ExtractHPBonus` and
    `UAI_ExtractEnergyBonus`, and health adds to the defensive score a second time (``:545-551``).

    **``ByRef`` is what the return value carries.** Two of the six parameters are out-parameters in
    AutoIt -- ``$a_s_NewModStruct`` and ``$a_i_Finding``, both written throughout the loop -- and Python
    strings and integers cannot be shared with a caller, so this member **returns them** as a pair, in
    the order the signature names them. A migrating caller writes
    ``new_mod_struct, finding = UAI_SearchModsInArray(...)`` where it wrote one call. The other four
    parameters are read-only in the source and stay arguments: the table, the raw mod string, the set
    number and the weapon number. This is the same twin this layer documents on `UAI_GetIsIdle` and on
    `_party_average_health` for the facts AutoIt carries outside its return value.
    """

    index = a_i_Set - 1
    for i in range(len(a_as2_UpgradeArray)):
        search_in = a_s_ModStruct if a_i_Finding == 0 else a_s_NewModStruct
        if _contains(search_in, a_as2_UpgradeArray[i][2]):
            uai_const.g_as3_Weapon_Mods[a_i_Set - 1][a_i_Weapon - 1][a_i_Finding] = a_as2_UpgradeArray[i][0]
            if a_i_Finding == 0:
                a_s_NewModStruct = _replace(a_s_ModStruct, a_as2_UpgradeArray[i][2], "")
            else:
                a_s_NewModStruct = _replace(a_s_NewModStruct, a_as2_UpgradeArray[i][2], "")

            mod_name = a_as2_UpgradeArray[i][0]
            effect = a_as2_UpgradeArray[i][1]
            _D("     [MOD #" + str(a_i_Finding) + "] " + str(mod_name) + " => " + str(effect))

            hp_bonus = UAI_ExtractHPBonus(effect)
            energy_bonus = UAI_ExtractEnergyBonus(effect)

            row = uai_const.g_a2D_WeaponSets[index]
            if hp_bonus > 0:
                row[_constants.GC_UAI_WEAPONSET_MaxHP] += hp_bonus
                row[_constants.GC_UAI_WEAPONSET_DefensiveScore] += hp_bonus
            if energy_bonus > 0:
                row[_constants.GC_UAI_WEAPONSET_MaxEnergy] += energy_bonus

            if _contains(mod_name, "Sundering"):
                row[_constants.GC_UAI_WEAPONSET_OffensiveScore] += 20
            if _contains(mod_name, "Vampiric"):
                row[_constants.GC_UAI_WEAPONSET_OffensiveScore] += 15
                row[_constants.GC_UAI_WEAPONSET_HasVampiric] = 1
            if _contains(mod_name, "Zealous"):
                row[_constants.GC_UAI_WEAPONSET_OffensiveScore] += 10
                row[_constants.GC_UAI_WEAPONSET_HasZealous] = 1
            if _contains(mod_name, "Furious"):
                row[_constants.GC_UAI_WEAPONSET_OffensiveScore] += 10

            if _contains(effect, "+33%"):
                row[_constants.GC_UAI_WEAPONSET_OffensiveScore] += 5
            if _contains(effect, "Damage +15%") or _contains(effect, "Damage 20%"):
                row[_constants.GC_UAI_WEAPONSET_OffensiveScore] += 15

            if _contains(effect, "Armor +"):
                row[_constants.GC_UAI_WEAPONSET_DefensiveScore] += 10
            if _contains(effect, "armor vs"):
                row[_constants.GC_UAI_WEAPONSET_DefensiveScore] += 7
            if _contains(effect, "Damage -"):
                row[_constants.GC_UAI_WEAPONSET_DefensiveScore] += 5
            if _contains(effect, "-20%"):
                row[_constants.GC_UAI_WEAPONSET_DefensiveScore] += 3

            if _contains(effect, "HCT20"):
                row[_constants.GC_UAI_WEAPONSET_CastingScore] += 20
            elif _contains(effect, "HCT10"):
                row[_constants.GC_UAI_WEAPONSET_CastingScore] += 10
            if _contains(effect, "HSR20"):
                row[_constants.GC_UAI_WEAPONSET_CastingScore] += 20
            elif _contains(effect, "HSR10"):
                row[_constants.GC_UAI_WEAPONSET_CastingScore] += 10

            if _contains(effect, "Enchantment Duration") or _contains(mod_name, "Enchanting"):
                row[_constants.GC_UAI_WEAPONSET_EnchantScore] += 20

            a_i_Finding += 1

    return a_s_NewModStruct, a_i_Finding


def UAI_ExtractHPBonus(a_s_Effect: Any) -> int:
    """The health a mod's effect text grants (``:615-624``).

    Two patterns, in the source's order -- ``"Health +XX"`` then ``"+XX HP"`` -- and ``0`` when
    neither matches. The captured group is what is answered, not the whole match: AutoIt's
    ``StringRegExp`` with flag ``1`` returns the **groups** of the first match, so ``Int($a[0])`` on
    ``"Health +30"`` is ``30``. ``tests/scratch/_probe_regexp.au3`` records the measurement.
    """

    result = re.search(r"Health \+(\d+)", str(a_s_Effect))
    if result is not None:
        return int(result.group(1))

    result = re.search(r"\+(\d+) HP", str(a_s_Effect))
    if result is not None:
        return int(result.group(1))

    return 0


def UAI_ExtractEnergyBonus(a_s_Effect: Any) -> int:
    """The energy a mod's effect text grants (``:628-634``): ``"Energy +XX"``, or ``0``."""

    result = re.search(r"Energy \+(\d+)", str(a_s_Effect))
    if result is not None:
        return int(result.group(1))

    return 0


def UAI_IsOnWeaponSet(a_i_Set: Any) -> bool:
    """Whether the player is on a set, **by item id** (``:641-652``).

    The source compares the ids it reads from the player -- ``$GC_UAI_AGENT_WeaponItemId`` and
    ``$GC_UAI_AGENT_OffhandItemId`` -- with the ids the analysis saved for that set, and a set number
    outside ``1..4`` answers ``False`` before anything is read (``:642``). Ids rather than weapon
    types: two different swords of the same type are two different sets to this test, which is what
    the source's own comment says it is for.
    """

    if a_i_Set < 1 or a_i_Set > 4:
        return False

    index = a_i_Set - 1
    current_weapon_id = UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_WeaponItemId)
    current_offhand_id = UAI_GetPlayerInfo(_constants.GC_UAI_AGENT_OffhandItemId)
    set_weapon_id = uai_const.g_a2D_WeaponSets[index][_constants.GC_UAI_WEAPONSET_WeaponId]
    set_offhand_id = uai_const.g_a2D_WeaponSets[index][_constants.GC_UAI_WEAPONSET_OffhandId]

    return bool(
        current_weapon_id == set_weapon_id and current_offhand_id == set_offhand_id
    )


def UAI_IsTwoHandedWeapon(a_i_WeaponType: Any) -> bool:
    """Whether a weapon type occupies both hands (``:656-663``).

    The source's own list -- daggers, hammer, scythe, bow, staff -- and ``False`` for everything else,
    which is what lets `UAI_SaveWeaponSetFromMemory` skip the offhand analysis for those five.
    """

    if a_i_WeaponType in (
        _constants.GC_I_TYPE_DAGGERS,
        _constants.GC_I_TYPE_HAMMER,
        _constants.GC_I_TYPE_SCYTHE,
        _constants.GC_I_TYPE_BOW,
        _constants.GC_I_TYPE_STAFF,
    ):
        return True
    return False


def UAI_IsRangedWeapon(a_i_WeaponType: Any) -> bool:
    """Whether a weapon type is ranged (``:667-674``): bow, spear, wand, staff.

    **It is a different list from the two-handed one above**, and the difference is the point: a spear
    is ranged and single-handed (it pairs with a shield), a hammer is two-handed and melee. The
    source's two switches are independent and so are these.
    """

    if a_i_WeaponType in (
        _constants.GC_I_TYPE_BOW,
        _constants.GC_I_TYPE_SPEAR,
        _constants.GC_I_TYPE_WAND,
        _constants.GC_I_TYPE_STAFF,
    ):
        return True
    return False


def UAI_GetWeaponTypeName(a_i_Type: Any) -> str:
    """A weapon item type's name for the debug trace (``:677-700``)."""

    if a_i_Type == _constants.GC_I_TYPE_AXE:
        return "Axe"
    if a_i_Type == _constants.GC_I_TYPE_BOW:
        return "Bow"
    if a_i_Type == _constants.GC_I_TYPE_HAMMER:
        return "Hammer"
    if a_i_Type == _constants.GC_I_TYPE_WAND:
        return "Wand"
    if a_i_Type == _constants.GC_I_TYPE_STAFF:
        return "Staff"
    if a_i_Type == _constants.GC_I_TYPE_SWORD:
        return "Sword"
    if a_i_Type == _constants.GC_I_TYPE_DAGGERS:
        return "Daggers"
    if a_i_Type == _constants.GC_I_TYPE_SCYTHE:
        return "Scythe"
    if a_i_Type == _constants.GC_I_TYPE_SPEAR:
        return "Spear"
    return "Unknown (" + str(a_i_Type) + ")"


def UAI_GetOffhandTypeName(a_i_Type: Any) -> str:
    """An offhand item type's name for the debug trace (``:703-714``).

    ``$GC_I_TYPE_OFFHAND`` is ``12``, the constant GwAu3's own comment calls *Focus*, and ``0`` is the
    empty slot the analysis reaches when a set has no offhand.
    """

    if a_i_Type == _constants.GC_I_TYPE_OFFHAND:
        return "Focus"
    if a_i_Type == _constants.GC_I_TYPE_SHIELD:
        return "Shield"
    if a_i_Type == 0:
        return "Empty"
    return "Unknown (" + str(a_i_Type) + ")"
