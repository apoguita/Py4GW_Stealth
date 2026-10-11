"""GwAu3's ``UtilityAI_Const.au3``: the UtilityAI plugin's mutable state.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``).

**Why this module exists separately from ``constants.py``.** GwAu3 splits its UtilityAI settings
across two spellings: ``Global Const``/``Global Enum`` names -- which are values and never change --
and plain ``Global`` variables, which every part of the plugin reads and a script may assign. The
generator that fills ``py4gw/gwa3/constants.py`` reads the first spelling only, deliberately: a
``Global`` is state, and freezing one into a constants module would turn a running setting into a
literal. So the second spelling lives here, in a module named for the file that declares it, and a
reader of this layer assigns it the way GwAu3's own scripts do:

.. code-block:: autoit

    $g_i_FightMode = $g_i_PressureMode      ; GwAu3, in the script

.. code-block:: python

    from py4gw.gwa3 import uai_const
    from py4gw.gwa3.constants import g_i_PressureMode

    uai_const.g_i_FightMode = g_i_PressureMode

**What is here.** This module carries the globals the ported modules actually read today, with GwAu3's
own initial values: the debug switch (``:2``), the target bookkeeping (``:4-8``), the three cache flags
(``:11-13``), the target mode and fight mode (``:14-20``), the weapon-set state (``:30-72``) and the
fourteen mod tables (``:74-388``).

**One group of the file is deliberately not carried**, and it is the cached one:

* ``$g_as_BestTargetCache`` and ``$g_as_CanUseCache`` (``:9-10``) are **caches and have no twin here**:
  `py4gw/gwa3/uai_best_target_cache.py` and `uai_can_use_cache.py` answer the *names* those tables
  hold live, from the slot's own skill id, so there is nothing for a caller to fill. The two flags
  beside them (``$g_b_CanUseSkill``, ``$g_b_SkillChanged``, ``$g_b_CacheWeaponSet``) are not caches --
  they are settings the plugin reads -- so they are here.

**The weapon-set state arrived with its reader** (`py4gw/gwa3/uai_weaponsets.py`, the port of
``Equipment/UtilityAI_WeaponSets.au3``): the 2-D set table (``:48-52``), the ten best-set trackers
(``:55-63``), the mod-name table (``:65-69``) and the two hysteresis flags (``:71-72``). They are
mutable and the plugin writes them in place, so they are lists rather than tuples -- GwAu3 indexes
them, and so does the port, with the same index constants from `py4gw/gwa3/constants.py`
(``GC_UAI_WEAPONSET_*``).

**The mod tables (``:74-388``) are transcribed row for row.** Each is ``[Name, effect, mod-hex]``:
the third column is the byte sequence the item's own mod array carries for that upgrade, and
``UAI_SearchModsInArray`` searches the raw mod bytes for it (``UtilityAI_WeaponSets.au3:529``). Two
rows carry the source's own ``"????????"`` placeholder (``:103``, ``:382``) -- an upgrade whose byte
sequence GwAu3 never filled in -- and they are kept exactly as written rather than guessed at. The
arrays are declared ``[n][3]`` and every row count here matches the declared size, which
``tests/test_gwa3_uai_const_offline.py`` checks against the source itself.
"""

from __future__ import annotations

from . import constants as _constants

#: ``UtilityAI_Const.au3:2`` -- the debug switch, which the plugin's own ``_D`` helper reads.
#:
#: **``_D`` is a private helper in ``UtilityAI_Utils.au3:3-5`` and it is a no-op while this is
#: False**, which is the value the file declares and therefore the state every caller starts in:
#:
#: .. code-block:: autoit
#:
#:     Func _D($msg)
#:         If $g_b_UAI_Debug Then _D(" " & $msg)
#:     EndFunc
#:
#: ``UtilityAI_WeaponSets.au3`` calls it 41 times, and that is the whole of its use in the plugin --
#: which is why it lands here now, with the file that calls it. Read the ported `_D` in
#: `py4gw/gwa3/uai_utils.py` for what the helper does when the switch is turned on: the source's own
#: body calls ``_D`` again, so GwAu3 answers a debug print with a recursive call, and the port reports
#: that rather than inventing a print the source does not make.
g_b_UAI_Debug: bool = False

#: ``UtilityAI_Const.au3:4-8`` -- the target bookkeeping the fight loop and the ranking strategies read.
#:
#: **These are read by the strategy bodies** (`BestTarget_*`: `Anti_Spell` alone asks for
#: ``$g_i_BestTarget``'s allegiance at ``UtilityAI_Spell.au3``), which is why they are here now rather
#: than with the engine: the body of a strategy is where the value is used, and the generator that emits
#: those bodies cannot emit a name this module does not carry.
g_i_BestTarget: int = 0
g_i_ForceTarget: int = 0
g_i_AttackTarget: int = 0
g_i_LastCalledTarget: int = 0

#: ``UtilityAI_Const.au3:7`` -- ``-1`` is the source's own "no avoided player numbers", and a positive
#: number or a list replaces it (``UAI_Fight`` resolves its ``$a_v_PlayerNumber`` into this).
g_v_AvoidPlayerNumbers: object = -1

#: ``UtilityAI_Const.au3:14-15`` -- the target mode, and its two values are the ``Global Enum`` on the
#: line between them: ``$GC_UAI_TARGET_MODE_CALL`` (0) and ``$GC_UAI_TARGET_MODE_FOLLOW`` (1).
g_i_TargetMode: int = _constants.GC_UAI_TARGET_MODE_CALL

#: ``UtilityAI_Const.au3:11-13`` -- the three flags the cache and cast paths read.
#:
#: **``$g_b_CacheWeaponSet`` is what `Cache_SkillBar` tests before it chooses weapon sets**, and
#: ``$g_b_SkillChanged``/``$g_b_CanUseSkill`` are the same pair `UAI_ResetRuntime` returns to these
#: values -- which is why they arrive together, with `py4gw/gwa3/uai_cache.py` (their first reader).
g_b_CanUseSkill: bool = True
g_b_SkillChanged: bool = False
g_b_CacheWeaponSet: bool = False

#: ``UtilityAI_Const.au3:20`` -- the combat mode the targeting functions read.
#:
#: **GwAu3's own default is ``1``, which is *Pressure*, not *Finisher*** -- the file assigns
#: ``$g_i_FightMode = 1`` while the two modes are declared the line below it
#: (``Global Enum $g_i_FinisherMode, $g_i_PressureMode``), so a fresh UtilityAI prefers the *highest*
#: HP target, which is the opposite of what the setting's own name suggests. That is the value a port
#: has to start from, so it is the value here, and ``py4gw/gwa3/constants.py`` carries the two mode
#: names (``g_i_FinisherMode`` = 0, ``g_i_PressureMode`` = 1).
g_i_FightMode: int = 1

# -- the weapon-set state (``UtilityAI_Const.au3:30-72``) -----------------------------------------
#
# The index constants (``$GC_UAI_WEAPONSET_WeaponType`` ... ``$GC_UAI_WEAPONSET_HasZealous``) are
# ``Global Const`` and live in `py4gw/gwa3/constants.py`; the tables they index are state and live
# here, with the file that writes them.

#: ``UtilityAI_Const.au3:48-52`` -- ``$g_a2D_WeaponSets[4][14]``: one row per weapon set, indexed by
#: the ``GC_UAI_WEAPONSET_*`` constants. ``UAI_SaveWeaponSetFromMemory`` fills a row from the client's
#: own inventory struct and ``UAI_FindAndSaveModFromMemory`` accumulates the scores in it.
g_a2D_WeaponSets: list[list[int]] = [[0] * 14 for _ in range(4)]

#: ``UtilityAI_Const.au3:55-63`` -- the ten best-set trackers, each ``[Score/Value, SetNumber]``.
#:
#: ``[0]`` is the score the winner was chosen on and ``[1]`` the set number -- and ``0`` in ``[1]``
#: means *no set qualified*, which is why every reader in ``UtilityAI_WeaponSets.au3`` tests
#: ``> 0`` before using one. ``Ranged``, ``Vampiric`` and ``Zealous`` use ``[0]`` as a flag instead
#: of a score, and the source records that on its own lines (``:61-63``).
g_ai_High_Hp_Set: list[int] = [0, 0]
g_ai_High_Energy_Set: list[int] = [0, 0]
g_ai_Best_Offensive_Set: list[int] = [0, 0]
g_ai_Best_Defensive_Set: list[int] = [0, 0]
g_ai_Best_Casting_Set: list[int] = [0, 0]
g_ai_Best_Enchant_Set: list[int] = [0, 0]
g_ai_Best_Ranged_Set: list[int] = [0, 0]
g_ai_Best_Vampiric_Set: list[int] = [0, 0]
g_ai_Best_Zealous_Set: list[int] = [0, 0]

#: ``UtilityAI_Const.au3:65-69`` -- ``$g_as3_Weapon_Mods[4][2][8]``: per set, per weapon (main hand
#: then offhand), the names of the mods found, in the order they were found.
g_as3_Weapon_Mods: list[list[list[str]]] = [
    [["", "", "", "", "", "", "", ""], ["", "", "", "", "", "", "", ""]],
    [["", "", "", "", "", "", "", ""], ["", "", "", "", "", "", "", ""]],
    [["", "", "", "", "", "", "", ""], ["", "", "", "", "", "", "", ""]],
    [["", "", "", "", "", "", "", ""], ["", "", "", "", "", "", "", ""]],
]

#: ``UtilityAI_Const.au3:71-72`` -- the hysteresis flags `UAI_GetBestWeaponSetForCombat` sets.
#:
#: They are the whole of the "do not flip-flop" rule: the mode is entered at one threshold and left
#: at another, and the value survives between calls because it lives here rather than in the caller.
g_b_InDefensiveMode: bool = False
g_b_InLowEnergyMode: bool = False

# -- the mod tables (``UtilityAI_Const.au3:74-388``) ----------------------------------------------
#
# Each row is ``[Name, effect, mod-hex]``. The third column is what ``UAI_SearchModsInArray`` looks
# for in the item's raw mod bytes: GwAu3's ``Item_GetModStruct`` returns a byte array whose string
# form is ``0x`` followed by upper-case hex, and the four-byte groups here are those bytes -- the
# upgrade's identifier and its argument. AutoIt's ``StringInStr`` and ``StringReplace`` are
# case-insensitive and the port's `UAI_SearchModsInArray` keeps that, so the case of these literals
# does not decide the match.

#: ``UtilityAI_Const.au3:75-99`` -- ``$g_as2_OtherWeaponsMods[24][3]``. **Nothing in GwAu3 reads this
#: one**: the weapon-set analysis uses the thirteen below it, and a search of the whole checkout finds
#: no other reader. It is transcribed because a script outside the plugin may read it and because a
#: name this file declares belongs to whoever calls it -- and its third column is a second byte
#: sequence rather than a mod name, so it is not a table `UAI_SearchModsInArray` can be handed.
g_as2_OtherWeaponsMods: list[list[str]] = [
    ["Highly salvageable", "1E000826", ""],
    ["Improved sale value", "3200F805", ""],
    ["Damage +15% (-1 energy regen)", "0F003822", "0100C820"],
    ["Damage +15% (-1 HP regen)", "0F003822", "0100E820"],
    ["+30 HP", "001E4823", ""],
    ["Air Magic +1 (20% chance)", "14081824", ""],
    ["Blood Magic +1 (20% chance)", "14041824", ""],
    ["Channeling Magic +1 (20% chance)", "14221824", ""],
    ["Communing Magic +1 (20% chance)", "14201824", ""],
    ["Curse Magic +1 (20% chance)", "14071824", ""],
    ["Death Magic +1 (20% chance)", "14051824", ""],
    ["Divine Favor  +1 (20% chance)", "14101824", ""],
    ["Domination Magic +1 (20% chance)", "14021824", ""],
    ["Earth Magic +1 (20% chance)", "14091824", ""],
    ["Fire Magic +1 (20% chance)", "140A1824", ""],
    ["Healing Prayers +1 (20% chance)", "140D1824", ""],
    ["Illusion Magic +1 (20% chance)", "14011824", ""],
    ["Inspiration  +1 (20% chance)", "14031824", ""],
    ["Protection Prayers +1 (20% chance)", "140F1824", ""],
    ["Restoration Magic +1 (20% chance)", "14211824", ""],
    ["Smiting Prayers +1 (20% chance)", "140E1824", ""],
    ["Soul Reaping +1 (20% chance)", "14061824", ""],
    ["Spawning Magic +1 (20% chance)", "14241824", ""],
    ["Water Magic +1 (20% chance)", "140B1824", ""],
]

#: ``UtilityAI_Const.au3:101-112`` -- the martial-weapon inscriptions.
g_as2_MartialWeaponsInscription: list[list[str]] = [
    ["I have the power!", "Energy +5", "0500D822"],
    ["Let the Memory Live Again", "HSR10", "????????"],
    ["Strength and Honor", "Damage +15% (HP> 50%)", "0F327822"],
    ["Guided by Fate", "Damage +15% (while Enchanted)", "0F006822"],
    ["Dance with Death", "Damage +15% (while in a Stance)", "0F00A822"],
    ["Too Much Information", "Damage +15% (vs Hexed Foes)", "0F005822"],
    ["To the Pain!", "Damage +15% (-10 AL while attacking)", "0A001820"],
    ["Brawn over Brains", "Damage +15% (Energy -5)", "0500B820"],
    ["Vengeance is Mine", "Damage 20% (HP<50%)", "14328822"],
    ["Don't Fear the Reaper", "Damage 20% (while Hexed)", "14009822"],
    ["Don't Think Twice", "HCT10", "000A0822"],
]

#: ``UtilityAI_Const.au3:113-128`` -- the spell-casting-weapon inscriptions.
g_as2_SpellCastingWeaponsInscription: list[list[str]] = [
    ["Hale and Hearty", "Energy +5 (HP>50%)", "05320823"],
    ["Have Faith", "Energy +5 (while Enchanted)", "0500F822"],
    ["Don't call it a comeback!", "Energy +7 (HP<50%)", "07321823"],
    ["I am Sorrow.", "Energy +7 (while hexed)", "07002823"],
    ["Seize the Day", "Energy +15 (-1 energy regen)", "0100C820"],
    ["Aptitude not Attitude", "HCT20", "22500140828"],
    ["Strength and Honor", "Damage +15% (HP> 50%)", "0F327822"],
    ["Guided by Fate", "Damage +15% (while Enchanted)", "0F006822"],
    ["Dance with Death", "Damage +15% (while in a Stance)", "0F00A822"],
    ["Too Much Information", "Damage +15% (vs Hexed Foes)", "0F005822"],
    ["To the Pain!", "Damage +15% (-10 AL while attacking)", "0A001820"],
    ["Brawn over Brains", "Damage +15% (Energy -5)", "0500B820"],
    ["Vengeance is Mine", "Damage 20% (HP<50%)", "14328822"],
    ["Don't Fear the Reaper", "Damage 20% (while Hexed)", "14009822"],
    ["Don't Think Twice", "HCT10", "000A0822"],
]

#: ``UtilityAI_Const.au3:129-163`` -- the focus/shield inscriptions, the longest table of the set.
g_as2_FocusShieldWeaponsInscription: list[list[str]] = [
    ["Master of My Domain", "+1 Attr. (Chance 20%)", "00143828"],
    ["Not the face!", "Armor +10 (vs Blunt)", "0A0018A1"],
    ["Leaf on the Wind", "Armor +10 (vs Cold)", "0A0318A1"],
    ["Like a Rolling Stone", "Armor +10 (vs Earth)", "0A0B18A1"],
    ["Sleep Now in the Fire", "Armor +10 (vs Fire)", "0A0518A1"],
    ["Riders on the Storm", "Armor +10 (vs Lightning)", "0A0418A1"],
    ["Through Thick and Thin", "Armor +10 (vs Piercing)", "0A0118A1"],
    ["The Riddle of Steel", "Armor +10 (vs Slashing)", "0A0218A1"],
    ["Sheltered by Faith", "Damage -2 (while Enchanted)", "02008820"],
    ["Run For Your Life!", "Damage -2 (while in a Stance)", "0200A820"],
    ["Nothing to Fear", "Damage -3 (while Hexed)", "03009820"],
    ["Luck of the Draw", "Damage -5 (Chance: 20%)", "05147820"],
    ["Fear Cuts Deeper", "-20% Bleeding", "00005828"],
    ["I Can See Clearly Now", "-20% Blind", "00015828"],
    ["Swift as the Wind", "-20% Crippled", "00035828"],
    ["Soundness of Mind", "-20% Dazed", "00075828"],
    ["Strength of Body", "-20% Deep Wound", "00045828"],
    ["Cast Out the Unclean", "-20% Disease", "00055828"],
    ["Pure of Heart", "-20% Poison", "00065828"],
    ["Only the Strong Survive", "-20% Weakness", "00085828"],
    ["Hail to the King", "Armor +5 (HP> 50%)", "0532A821"],
    ["Faith is My Shield", "Armor +5 (while Enchanted)", "05009821"],
    ["Might Makes Right", "Armor +5 (while attacking)", "05007821"],
    ["Knowing is Half the Battle.", "Armor +5 (while casting)", "05008821"],
    ["Man for All Seasons", "Armor +5 (vs Elemental)", "05002821"],
    ["Survival of the Fittest", "Armor +5 (vs Physical)", "05005821"],
    ["Ignorance is Bliss", "Armor +5 (Energy -5)", "0500B820"],
    ["Life is Pain", "Armor +5 (Health -20)", "1400D820"],
    ["Down But Not Out", "Armor +10 (HP< 50%)", "0A32B821"],
    ["Be Just and Fear Not", "Armor +10 (while Hexed)", "0A00C821"],
    ["Live for Today", "Energy +15 (Regen -1)", "0F00D822"],
    ["Serenity Now", "HSR10", "000AA823"],
    ["Forget Me Not", "HSR20", "00142828"],
    ["Aptitude not Attitude", "HCT20", "22500140828"],
]

#: ``UtilityAI_Const.au3:164-194`` -- axe upgrades and grips.
g_as2_AxeUpgrade: list[list[str]] = [
    ["Barbed", "Bleeding +33%", "DE016824"],
    ["Cruel", "Deep Wound +33%", "E2016824"],
    ["Crippling", "Crippled +33%", "E1016824"],
    ["Heavy", "Weakness +33%", "E6016824"],
    ["Poisonous", "Poison +33%", "E4016824"],
    ["Ebon", "Earth damage", "000BB824"],
    ["Fiery", "Fire damage", "0005B824"],
    ["Icy", "Cold damage", "0003B824"],
    ["Shocking", "Lightning damage", "0004B824"],
    ["Furious", "Double adrenaline 10%", "0A00B823"],
    ["Sundering", "Armor penetration +20%", "1414F823"],
    ["Vampiric (+3)", "Life draining", "00032825"],
    ["Zealous", "Energy gain on hit", "01001825"],
    ["Axe Grip of Defense", "Armor +5", "05000821"],
    ["Axe Grip of Shelter", "+7 armor vs Physical", "07005821"],
    ["Axe Grip of Warding", "+7 Armor vs Elemental", "07002821"],
    ["Axe Grip of Enchanting", "+20% Enchantment Duration", "1400B822"],
    ["Axe Grip of Fortitude", "Health +30", "001E4823"],
    ["Axe Grip of Axe Mastery", "Axe Mastery +1 (20% chance)", "14121824"],
    ["Axe Grip of Charr slaying", "+ 20% (vs Charr)", "00018080"],
    ["Axe Grip of Demons slaying", "+ 20% (vs Demons)", "00088080"],
    ["Axe Grip of Dragons slaying", "+ 20% (vs Dragons", "00098080"],
    ["Axe Grip of Dwarves slaying", "+ 20% (vs Dwarves)", "00068080"],
    ["Axe Grip of Giants slaying", "+ 20% (vs Giants)", "00058080"],
    ["Axe Grip of Ogres slaying", "+ 20% (vs Ogres)", "000A8080"],
    ["Axe Grip of Plants slaying", "+ 20% (vs Plants)", "00038080"],
    ["Axe Grip of Skeletons slaying", "+ 20% (vs Skeletons)", "00048080"],
    ["Axe Grip of Tengu slaying", "+ 20% (vs Tengu)", "00078080"],
    ["Axe Grip of Trolls slaying", "+ 20% (vs Trolls)", "00028080"],
    ["Axe Grip of Undead slaying", "+ 20% (vs Undead)", "001448A2"],
]

#: ``UtilityAI_Const.au3:195-222`` -- hammer upgrades and hafts. No ``Barbed``, ``Crippling`` or
#: ``Poisonous``: a hammer cannot carry the condition upgrades an axe can, and the source's own table
#: is where that shows.
g_as2_HammerUpgrade: list[list[str]] = [
    ["Cruel", "Deep Wound +33%", "E2016824"],
    ["Heavy", "Weakness +33%", "E6016824"],
    ["Ebon", "Earth damage", "000BB824"],
    ["Fiery", "Fire damage", "0005B824"],
    ["Icy", "Cold damage", "0003B824"],
    ["Shocking", "Lightning damage", "0004B824"],
    ["Furious", "Double adrenaline 10%", "0A00B823"],
    ["Sundering", "Armor penetration +20%", "1414F823"],
    ["Vampiric (+3)", "Life draining", "00032825"],
    ["Zealous", "Energy gain on hit", "01001825"],
    ["Hammer Haft of Defense", "Armor +5", "05000821"],
    ["Hammer Haft of Shelter", "+7 armor vs Physical", "07005821"],
    ["Hammer Haft of Warding", "+7 Armor vs Elemental", "07002821"],
    ["Hammer Haft of Enchanting", "+20% Enchantment Duration", "1400B822"],
    ["Hammer Haft of Fortitude", "Health +30", "001E4823"],
    ["Hammer Haft of Hammer Mastery", "Hammer Mastery +1 (20% chance)", "14131824"],
    ["Hammer Haft of Charr slaying", "+ 20% (vs Charr)", "00018080"],
    ["Hammer Haft of Demons slaying", "+ 20% (vs Demons)", "00088080"],
    ["Hammer Haft of Dragons slaying", "+ 20% (vs Dragons", "00098080"],
    ["Hammer Haft of Dwarves slaying", "+ 20% (vs Dwarves)", "00068080"],
    ["Hammer Haft of Giants slaying", "+ 20% (vs Giants)", "00058080"],
    ["Hammer Haft of Ogres slaying", "+ 20% (vs Ogres)", "000A8080"],
    ["Hammer Haft of Plants slaying", "+ 20% (vs Plants)", "00038080"],
    ["Hammer Haft of Skeletons slaying", "+ 20% (vs Skeletons)", "00048080"],
    ["Hammer Haft of Tengu slaying", "+ 20% (vs Tengu)", "00078080"],
    ["Hammer Haft of Trolls slaying", "+ 20% (vs Trolls)", "00028080"],
    ["Hammer Haft of Undead slaying", "+ 20% (vs Undead)", "001448A2"],
]

#: ``UtilityAI_Const.au3:223-252`` -- sword upgrades and pommels.
g_as2_SwordUpgrade: list[list[str]] = [
    ["Barbed", "Bleeding +33%", "DE016824"],
    ["Cruel", "Deep Wound +33%", "E2016824"],
    ["Crippling", "Crippled +33%", "E1016824"],
    ["Poisonous", "Poison +33%", "E4016824"],
    ["Ebon", "Earth damage", "000BB824"],
    ["Fiery", "Fire damage", "0005B824"],
    ["Icy", "Cold damage", "0003B824"],
    ["Shocking", "Lightning damage", "0004B824"],
    ["Furious", "Double adrenaline 10%", "0A00B823"],
    ["Sundering", "Armor penetration +20%", "1414F823"],
    ["Vampiric (+3)", "Life draining", "00032825"],
    ["Zealous", "Energy gain on hit", "01001825"],
    ["Sword Pommel of Defense", "Armor +5", "05000821"],
    ["Sword Pommel of Shelter", "+7 armor vs Physical", "07005821"],
    ["Sword Pommel of Warding", "+7 Armor vs Elemental", "07002821"],
    ["Sword Pommel of Enchanting", "+20% Enchantment Duration", "1400B822"],
    ["Sword Pommel of Fortitude", "Health +30", "001E4823"],
    ["Sword Pommel of Swordmanship", "Swordmanship +1 (20% chance)", "14141824"],
    ["Sword Pommel of Charr slaying", "+ 20% (vs Charr)", "00018080"],
    ["Sword Pommel of Demons slaying", "+ 20% (vs Demons)", "00088080"],
    ["Sword Pommel of Dragons slaying", "+ 20% (vs Dragons", "00098080"],
    ["Sword Pommel of Dwarves slaying", "+ 20% (vs Dwarves)", "00068080"],
    ["Sword Pommel of Giants slaying", "+ 20% (vs Giants)", "00058080"],
    ["Sword Pommel of Ogres slaying", "+ 20% (vs Ogres)", "000A8080"],
    ["Sword Pommel of Plants slaying", "+ 20% (vs Plants)", "00038080"],
    ["Sword Pommel of Skeletons slaying", "+ 20% (vs Skeletons)", "00048080"],
    ["Sword Pommel of Tengu slaying", "+ 20% (vs Tengu)", "00078080"],
    ["Sword Pommel of Trolls slaying", "+ 20% (vs Trolls)", "00028080"],
    ["Sword Pommel of Undead slaying", "+ 20% (vs Undead)", "001448A2"],
]

#: ``UtilityAI_Const.au3:253-273`` -- dagger upgrades and handles. Its last row is the mastery mod, so
#: it carries no slaying grips at all.
g_as2_DaggerUpgrade: list[list[str]] = [
    ["Barbed", "Bleeding +33%", "DE016824"],
    ["Cruel", "Deep Wound +33%", "E2016824"],
    ["Crippling", "Crippled +33%", "E1016824"],
    ["Heavy", "Weakness +33%", "E6016824"],
    ["Poisonous", "Poison +33%", "E4016824"],
    ["Silencing", "Dazed +33%", "E5016824"],
    ["Ebon", "Earth damage", "000BB824"],
    ["Fiery", "Fire damage", "0005B824"],
    ["Icy", "Cold damage", "0003B824"],
    ["Shocking", "Lightning damage", "0004B824"],
    ["Furious", "Double adrenaline 10%", "0A00B823"],
    ["Sundering", "Armor penetration +20%", "1414F823"],
    ["Vampiric (+3)", "Life draining", "00032825"],
    ["Zealous", "Energy gain on hit", "01001825"],
    ["Dagger Handle of Defense", "Armor +5", "05000821"],
    ["Dagger Handle of Shelter", "+7 armor vs Physical", "07005821"],
    ["Dagger Handle of Warding", "+7 Armor vs Elemental", "07002821"],
    ["Dagger Handle of Enchanting", "+20% Enchantment Duration", "1400B822"],
    ["Dagger Handle of Fortitude", "Health +30", "001E4823"],
    ["Dagger Handle of Dagger Mastery", "Dagger Mastery +1 (20% chance)", "141D1824"],
]

#: ``UtilityAI_Const.au3:274-293`` -- scythe upgrades and grips.
g_as2_ScytheUpgrade: list[list[str]] = [
    ["Barbed", "Bleeding +33%", "DE016824"],
    ["Cruel", "Deep Wound +33%", "E2016824"],
    ["Crippling", "Crippled +33%", "E1016824"],
    ["Heavy", "Weakness +33%", "E6016824"],
    ["Poisonous", "Poison +33%", "E4016824"],
    ["Ebon", "Earth damage", "000BB824"],
    ["Fiery", "Fire damage", "0005B824"],
    ["Icy", "Cold damage", "0003B824"],
    ["Shocking", "Lightning damage", "0004B824"],
    ["Furious", "Double adrenaline 10%", "0A00B823"],
    ["Sundering", "Armor penetration +20%", "1414F823"],
    ["Vampiric (+5)", "Life draining", "00052825"],
    ["Zealous", "Energy gain on hit", "01001825"],
    ["Scythe Grip of Defense", "Armor +5", "05000821"],
    ["Scythe Grip of Shelter", "+7 armor vs Physical", "07005821"],
    ["Scythe Grip of Warding", "+7 Armor vs Elemental", "07002821"],
    ["Scythe Grip of Enchanting", "+20% Enchantment Duration", "1400B822"],
    ["Scythe Grip of Fortitude", "Health +30", "001E4823"],
    ["Scythe Grip of Scythe Mastery", "Scythe Mastery +1 (20% chance)", "14291824"],
]

#: ``UtilityAI_Const.au3:294-323`` -- bow upgrades and grips. Note ``Vampiric (+5)`` here where the
#: melee tables say ``Vampiric (+3)``: the health the mod drains per hit is what the name records.
g_as2_BowUpgrade: list[list[str]] = [
    ["Barbed", "Bleeding +33%", "DE016824"],
    ["Crippling", "Crippled +33%", "E1016824"],
    ["Poisonous", "Poison +33%", "E4016824"],
    ["Silencing", "Dazed +33%", "E5016824"],
    ["Ebon", "Earth damage", "000BB824"],
    ["Fiery", "Fire damage", "0005B824"],
    ["Icy", "Cold damage", "0003B824"],
    ["Shocking", "Lightning damage", "0004B824"],
    ["Furious", "Double adrenaline 10%", "0A00B823"],
    ["Sundering", "Armor penetration +20%", "1414F823"],
    ["Vampiric (+5)", "Life draining", "00052825"],
    ["Zealous", "Energy gain on hit", "01001825"],
    ["Bow Grip of Defense", "Armor +5", "05000821"],
    ["Bow Grip of Shelter", "+7 armor vs Physical", "07005821"],
    ["Bow Grip of Warding", "+7 Armor vs Elemental", "07002821"],
    ["Bow Grip of Enchanting", "+20% Enchantment Duration", "1400B822"],
    ["Bow Grip of Fortitude", "Health +30", "001E4823"],
    ["Bow Grip of Marksmanship", "Marksmanship +1 (20% chance)", "14191824"],
    ["Bow Grip of Charr slaying", "+ 20% (vs Charr)", "00018080"],
    ["Bow Grip of Demons slaying", "+ 20% (vs Demons)", "00088080"],
    ["Bow Grip of Dragons slaying", "+ 20% (vs Dragons", "00098080"],
    ["Bow Grip of Dwarves slaying", "+ 20% (vs Dwarves)", "00068080"],
    ["Bow Grip of Giants slaying", "+ 20% (vs Giants)", "00058080"],
    ["Bow Grip of Ogres slaying", "+ 20% (vs Ogres)", "000A8080"],
    ["Bow Grip of Plants slaying", "+ 20% (vs Plants)", "00038080"],
    ["Bow Grip of Skeletons slaying", "+ 20% (vs Skeletons)", "00048080"],
    ["Bow Grip of Tengu slaying", "+ 20% (vs Tengu)", "00078080"],
    ["Bow Grip of Trolls slaying", "+ 20% (vs Trolls)", "00028080"],
    ["Bow Grip of Undead slaying", "+ 20% (vs Undead)", "001448A2"],
]

#: ``UtilityAI_Const.au3:324-344`` -- spear upgrades and grips.
g_as2_SpearUpgrade: list[list[str]] = [
    ["Barbed", "Bleeding +33%", "DE016824"],
    ["Cruel", "Deep Wound +33%", "E2016824"],
    ["Crippling", "Crippled +33%", "E1016824"],
    ["Heavy", "Weakness +33%", "E6016824"],
    ["Poisonous", "Poison +33%", "E4016824"],
    ["Silencing", "Dazed +33%", "E5016824"],
    ["Ebon", "Earth damage", "000BB824"],
    ["Fiery", "Fire damage", "0005B824"],
    ["Icy", "Cold damage", "0003B824"],
    ["Shocking", "Lightning damage", "0004B824"],
    ["Furious", "Double adrenaline 10%", "0A00B823"],
    ["Sundering", "Armor penetration +20%", "1414F823"],
    ["Vampiric (+3)", "Life draining", "00032825"],
    ["Zealous", "Energy gain on hit", "01001825"],
    ["Spear Grip of Defense", "Armor +5", "05000821"],
    ["Spear Grip of Shelter", "+7 armor vs Physical", "07005821"],
    ["Spear Grip of Warding", "+7 Armor vs Elemental", "07002821"],
    ["Spear Grip of Enchanting", "+20% Enchantment Duration", "1400B822"],
    ["Spear Grip of Fortitude", "Health +30", "001E4823"],
    ["Spear Grip of Spear Mastery", "Spear Mastery +1 (20% chance)", "14251824"],
]

#: ``UtilityAI_Const.au3:345-373`` -- staff heads and staff/wand wrappings, and the one table the
#: source gives two spellings of the same mod: ``Staff Wrapping of Fortitude`` appears twice, once for
#: ``Health +30`` and once for ``+30 HP``, because the two carry different byte sequences.
g_as2_StaffWandUpgrade: list[list[str]] = [
    ["Staff Head Adept", "HCT20", "02500140828"],
    ["Staff Head Defensive", "Armor +5", "05000821"],
    ["Staff Head Hale", "+30 HP", "A013025001E4823"],
    ["Staff Head Insightful", "Energy +5", "0500D822"],
    ["Staff Head Swift", "HCT10", "000A0822"],
    ["Staff Wrapping of Defense", "Armor +5", "05000821"],
    ["Staff Wrapping of Shelter", "+7 armor vs Physical", "07005821"],
    ["Staff Wrapping of Warding", "+7 Armor vs Elemental", "07002821"],
    ["Staff Wrapping of Enchanting", "+20% Enchantment Duration", "1400B822"],
    ["Staff Wrapping of Fortitude", "Health +30", "001E4823"],
    ["Staff Wrapping of Fortitude", "+30 HP (staff wrapping)", "9013025001E4823"],
    ["Staff Wrapping of Devotion", "+45 HP while Enchanted", "002D6823"],
    ["Staff Wrapping of Endurance", "+45 HP while in a Stance", "002D8823"],
    ["Staff Wrapping of Valor", "+60 HP while Hexed", "003C7823"],
    ["Staff Wrapping of Attr", "+1 Attr. (Chance 20%)", "00143828"],
    ["Staff Wrapping of Charr slaying", "+ 20% (vs Charr)", "00018080"],
    ["Staff Wrapping of Demons slaying", "+ 20% (vs Demons)", "00088080"],
    ["Staff Wrapping of Dragons slaying", "+ 20% (vs Dragons", "00098080"],
    ["Staff Wrapping of Dwarves slaying", "+ 20% (vs Dwarves)", "00068080"],
    ["Staff Wrapping of Giants slaying", "+ 20% (vs Giants)", "00058080"],
    ["Staff Wrapping of Ogres slaying", "+ 20% (vs Ogres)", "000A8080"],
    ["Staff Wrapping of Plants slaying", "+ 20% (vs Plants)", "00038080"],
    ["Staff Wrapping of Skeletons slaying", "+ 20% (vs Skeletons)", "00048080"],
    ["Staff Wrapping of Tengu slaying", "+ 20% (vs Tengu)", "00078080"],
    ["Staff Wrapping of Trolls slaying", "+ 20% (vs Trolls)", "00028080"],
    ["Staff Wrapping of Undead slaying", "+ 20% (vs Undead)", "001448A2"],
    ["Wand Wrapping of Quickening", "HSR20", "00142828"],
    ["Wand Wrapping of Memory", "HSR10", "000AA823"],
]

#: ``UtilityAI_Const.au3:374-379`` -- shield handles: five rows, all health mods.
g_as2_ShieldUpgrade: list[list[str]] = [
    ["Shield Handle of Fortitude", "Health +30", "001E4823"],
    ["Shield Handle of Fortitude", "+30 HP (Shield Handle)", "9013025001E4823"],
    ["Shield Handle of Devotion", "+45 HP while Enchanted", "002D6823"],
    ["Shield Handle of Endurance", "+45 HP while in a Stance", "002D8823"],
    ["Shield Handle of Valor", "+60 HP while Hexed", "003C7823"],
]

#: ``UtilityAI_Const.au3:380-387`` -- focus cores. ``Focus Core of Adptitude`` carries the source's
#: misspelling and its ``"????????"`` byte sequence, kept as written.
g_as2_FocusUpgrade: list[list[str]] = [
    ["Focus Core of Swiftness", "HCT20", "02500140828"],
    ["Focus Core of Adptitude", "HCT10", "????????"],
    ["Focus Core of Fortitude", "Health +30", "001E4823"],
    ["Focus Core of Fortitude", "+30 HP (Focus Core)", "9013025001E4823"],
    ["Focus Core of Devotion", "+45 HP while Enchanted", "002D6823"],
    ["Focus Core of Endurance", "+45 HP while in a Stance", "002D8823"],
    ["Focus Core of Valor", "+60 HP while Hexed", "003C7823"],
]
