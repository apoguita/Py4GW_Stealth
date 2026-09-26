"""Port of Reforged's ``Py4GWCoreLib/Skill.py``, over the client's skill constant table.

**Source:** ``Py4GWCoreLib/Skill.py`` — 511 lines, ``class Skill`` at line 6 with its four nested
namespaces (``Data``, ``Attribute``, ``Flags``, ``Animations``) and ``ExtraData``. Every member
keeps the source's name, signature and return values.

**What the source's members are built on, and what this file carries of it.** Reforged's members are
one-line reads of ``PySkill.Skill(skill_id)`` — native's binding object (``skill_bindings.cpp:69-199``),
which copies a ``GW::Context::Skill`` record into a Python-shaped struct and derives the flag fields
from the record's ``special`` word. So the port carries three things, each named after the source it
comes from:

- :class:`py4gw.context.skill_context.SkillStruct` — the client's ``GW::Context::Skill`` record
  (``include/GW/context/skill.h``), read out of the static table the client itself indexes;
- :class:`PySkill` — native's binding struct, field for field, with ``GetContext()`` doing the same
  copy and the same derivations (``skill_bindings.cpp:134-195``);
- :class:`SkillID`, :class:`SkillType`, :class:`SkillProfession` — the three small types the binding
  exposes beside it (``skill_bindings.cpp:24-67``), whose names are the ones Reforged's Python sees.

``Skill.skill_instance(skill_id)`` is the source's own line (``Skill.py:17-19``): it answers the
binding object, and every member below is the source's transcription over it.

Three groups exist, and each member says which one it is in its docstring:

``implemented``
    The value comes from the skill constant record this project reads, or from a table native
    generates in code. That is the whole of the record surface — costs, timings, scales, animations,
    icons, string ids, every flag — plus all three of native's name tables: the 29 skill-type names
    and the 11 profession names (``skill_names.cpp:3081-3131``), which ``GetType``,
    ``GetProfession`` and the whole ``Flags`` family read, and the 3031-entry skill-name table
    (``skill_names.cpp:16-3048``) behind ``GetName`` and ``GetID``, ported beside this file as
    ``py4gw/skill_names.py``.

``not built yet``
    ``GetNameFromWiki``/``GetURL``/``GetProgressionData``/``GetDescription``/``GetConciseDescription``
    need Reforged's bundled ``skill_descriptions.json`` (1.98 MB beside ``Skill.py``),
    ``GetTexturePath`` needs ``enums_src/Texture_enums.py``'s ``SkillTextureMap`` (~3100 entries), and
    ``GetCampaign`` needs ``enums_src/Region_enums.py``'s ``CampaignName``. Each raises
    ``NotImplementedError`` through :func:`_unported`, naming the table and where it lives — never a
    plausible wrong value.
"""

from __future__ import annotations

from .client import require_client
from .context.skill_context import SkillStruct
from .skill_names import GetSkillIDByName, GetSkillNameByID


def _unported(member: str, requirement: str) -> NotImplementedError:
    """Build the error raised by a member this port has not built yet.

    The source's member is complete and working — Reforged is an in-production library — so the
    message never describes the source: it names the work item this port still owes, and the raise
    is what keeps a caller from receiving a plausible wrong value while that work is outstanding.
    """

    return NotImplementedError(
        f"Skill.{member} is declared but not built here yet: it needs {requirement}. "
        "The source's member works; this port raises at the call site and names the work "
        "item instead of returning a wrong value."
    )


#: ``GW::skillbar::GetSkillTypeNameByID`` (``skill_names.cpp:3081-3114``): the skill-type table
#: native generates from the ``SkillType`` enum. The switch's numbers are its own.
SKILL_TYPE_NAMES = {
    1: "Bounty",
    2: "Scroll",
    3: "Stance",
    4: "Hex",
    5: "Spell",
    6: "Enchantment",
    7: "Signet",
    8: "Condition",
    9: "Well",
    10: "Skill",
    11: "Ward",
    12: "Glyph",
    13: "Title",
    14: "Attack",
    15: "Shout",
    16: "Skill2",
    17: "Passive",
    18: "Environmental",
    19: "Preparation",
    20: "PetAttack",
    21: "Trap",
    22: "Ritual",
    23: "EnvironmentalTrap",
    24: "ItemSpell",
    25: "WeaponSpell",
    26: "Form",
    27: "Chant",
    28: "EchoRefrain",
    29: "Disguise",
}


def GetSkillTypeNameByID(type_id: int) -> str:
    """``GW::skillbar::GetSkillTypeNameByID`` (``skill_names.cpp:3081-3114``): ``""`` when unknown."""

    return SKILL_TYPE_NAMES.get(int(type_id), "")


#: ``GW::skillbar::GetProfessionNameById`` (``skill_names.cpp:3116-3131``).
PROFESSION_NAMES = {
    0: "None",
    1: "Warrior",
    2: "Ranger",
    3: "Monk",
    4: "Necromancer",
    5: "Mesmer",
    6: "Elementalist",
    7: "Assassin",
    8: "Ritualist",
    9: "Paragon",
    10: "Dervish",
}


def GetProfessionNameById(profession_id: int) -> str:
    """``GW::skillbar::GetProfessionNameById`` (``skill_names.cpp:3116-3131``): ``""`` when unknown."""

    return PROFESSION_NAMES.get(int(profession_id), "")


class SkillID:
    """Native ``PySkill.SkillID`` (``skill_bindings.cpp:24-38``): an id, its name, and equality."""

    def __init__(self, skill_id: int | str = 0) -> None:
        if isinstance(skill_id, str):
            self.id = GetSkillIDByName(skill_id)
        else:
            self.id = int(skill_id)

    def GetName(self) -> str:
        """``PySkillID::GetName`` → ``GetSkillNameByID`` (``skill_names.cpp:3069-3073``)."""

        return GetSkillNameByID(self.id)

    def __eq__(self, other: object) -> bool:
        return self.id == (other.id if isinstance(other, SkillID) else other)

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash(self.id)


class SkillType:
    """Native ``PySkill.SkillType`` (``skill_bindings.cpp:40-52``)."""

    def __init__(self, type_id: int = 10) -> None:
        self.id = int(type_id)

    def GetName(self) -> str:
        """``PySkillType::GetName`` → ``GetSkillTypeNameByID`` (``skill_names.cpp:3081-3114``)."""

        return GetSkillTypeNameByID(self.id)

    def __eq__(self, other: object) -> bool:
        return self.id == (other.id if isinstance(other, SkillType) else other)

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash(self.id)


class SkillProfession:
    """Native ``PySkill.SkillProfession`` (``skill_bindings.cpp:57-67``)."""

    def __init__(self, profession_id: int = 0) -> None:
        self.id = int(profession_id)

    def ToInt(self) -> int:
        """``PySkillProfession::ToInt``."""

        return self.id

    def GetName(self) -> str:
        """``PySkillProfession::GetName`` → ``GetProfessionNameById`` (``skill_names.cpp:3116``)."""

        return GetProfessionNameById(self.id)


class PySkill:
    """Native ``PySkill.Skill`` (``skill_bindings.cpp:69-199``): the binding object Reforged reads.

    The declaration is native's, field for field, with the same defaults (``skill_bindings.cpp``
    :70-133) and the same ``GetContext()`` copy (``:134-195``). ``GetContext`` leaves every field at
    its default when the record is missing, which is the source's own early return
    (``skill_bindings.cpp:136``); the only difference from native is *where* the record comes from —
    this project reads it out of the client's table instead of dereferencing a DLL-side pointer,
    which is the same table native's ``GetSkillConstantData`` returns (``skillbar_methods.cpp:73-76``).
    """

    def __init__(self, skill_id: int | str = 0) -> None:
        self.id = SkillID(skill_id)
        self.campaign = 0
        self.type = SkillType()
        self.special = 0
        self.combo_req = 0
        self.effect1 = 0
        self.condition = 0
        self.effect2 = 0
        self.weapon_req = 0
        self.profession = SkillProfession()
        self.attribute = 0
        self.title = 0
        self.id_pvp = 0
        self.combo = 0
        self.target = 0
        self.skill_equip_type = 0
        self.overcast = 0
        self.energy_cost = 0
        self.health_cost = 0
        self.adrenaline = 0
        self.activation = 0.0
        self.aftercast = 0.0
        self.duration_0pts = 0
        self.duration_15pts = 0
        self.recharge = 0
        self.skill_arguments = 0
        self.scale_0pts = 0
        self.scale_15pts = 0
        self.bonus_scale_0pts = 0
        self.bonus_scale_15pts = 0
        self.aoe_range = 0.0
        self.const_effect = 0.0
        self.caster_overhead_animation_id = 0
        self.caster_body_animation_id = 0
        self.target_body_animation_id = 0
        self.target_overhead_animation_id = 0
        self.projectile_animation1_id = 0
        self.projectile_animation2_id = 0
        self.icon_file_id = 0
        self.icon_file2_id = 0
        self.icon_file_hi_res_id = 0
        self.name_id = 0
        self.concise = 0
        self.description_id = 0
        self.is_touch_range = False
        self.is_elite = False
        self.is_half_range = False
        self.is_pvp = False
        self.is_pve = False
        self.is_playable = False
        self.is_stacking = False
        self.is_non_stacking = False
        self.is_unused = False
        self.adrenaline_a = 0
        self.adrenaline_b = 0
        self.recharge2 = 0
        self.h0004 = 0
        self.h0032 = 0
        self.h0037 = 0
        self.GetContext()

    def GetContext(self) -> None:
        """Copy the skill constant record into this object (``skill_bindings.cpp:134-195``)."""

        record = require_client().read_skill(int(self.id.id))
        if record is None:
            return
        self._copy(record)

    def _copy(self, record: SkillStruct) -> None:
        """The binding's field-by-field copy (``skill_bindings.cpp:138-194``)."""

        self.campaign = int(record.campaign)
        self.type = SkillType(int(record.type))
        self.special = int(record.special)
        self.combo_req = int(record.combo_req)
        self.effect1 = int(record.effect1)
        self.condition = int(record.condition)
        self.effect2 = int(record.effect2)
        self.weapon_req = int(record.weapon_req)
        self.profession = SkillProfession(int(record.profession))
        self.attribute = int(record.attribute)
        self.title = int(record.title)
        self.id_pvp = int(record.skill_id_pvp)
        self.combo = int(record.combo)
        self.target = int(record.target)
        self.skill_equip_type = int(record.skill_equip_type)
        self.overcast = int(record.overcast)
        self.energy_cost = record.GetEnergyCost()
        self.health_cost = int(record.health_cost)
        self.adrenaline = int(record.adrenaline)
        self.activation = float(record.activation)
        self.aftercast = float(record.aftercast)
        self.duration_0pts = int(record.duration0)
        self.duration_15pts = int(record.duration15)
        self.recharge = int(record.recharge)
        self.skill_arguments = int(record.skill_arguments)
        self.scale_0pts = int(record.scale0)
        self.scale_15pts = int(record.scale15)
        self.bonus_scale_0pts = int(record.bonus_scale0)
        self.bonus_scale_15pts = int(record.bonus_scale15)
        self.aoe_range = float(record.aoe_range)
        self.const_effect = float(record.const_effect)
        self.caster_overhead_animation_id = int(record.caster_overhead_animation_id)
        self.caster_body_animation_id = int(record.caster_body_animation_id)
        self.target_body_animation_id = int(record.target_body_animation_id)
        self.target_overhead_animation_id = int(record.target_overhead_animation_id)
        self.projectile_animation1_id = int(record.projectile_animation_1_id)
        self.projectile_animation2_id = int(record.projectile_animation_2_id)
        self.icon_file_id = int(record.icon_file_id)
        self.icon_file2_id = int(record.icon_file_id_2)
        self.icon_file_hi_res_id = int(record.icon_file_id_hi_res)
        self.name_id = int(record.name)
        self.concise = int(record.concise)
        self.description_id = int(record.description)

        self.is_touch_range = record.IsTouchRange()
        self.is_elite = record.IsElite()
        self.is_half_range = record.IsHalfRange()
        self.is_pvp = record.IsPvP()
        self.is_pve = record.IsPvE()
        self.is_playable = record.IsPlayable()
        self.is_stacking = record.IsStacking()
        self.is_non_stacking = record.IsNonStacking()
        self.is_unused = record.IsUnused()

        self.h0004 = int(record.h0004)
        self.h0032 = int(record.h0032)
        self.h0037 = int(record.h0037)


class Skill:
    """The Reforged ``Skill`` class (``Skill.py:6-511``)."""

    _desc_cache = None  # Cache JSON data once loaded

    @staticmethod
    def _load_descriptions():
        """``Skill.py:9-15``: load ``skill_descriptions.json`` beside ``Skill.py``.

        Not built yet, and the missing piece is data rather than code: Reforged ships
        ``Py4GWCoreLib/skill_descriptions.json`` (1,975,988 bytes) beside the module and reads it
        here. This port has no copy of it, and five members read it.
        """

        raise _unported(
            "_load_descriptions",
            "Py4GWCoreLib/skill_descriptions.json (1,975,988 bytes), the data file Reforged reads "
            "beside Skill.py (Skill.py:12-14)",
        )

    @staticmethod
    def skill_instance(skill_id):
        """``Skill.py:17-19``: ``PySkill.Skill(skill_id)``, the binding object every member reads."""

        return PySkill(skill_id)

    @staticmethod
    def GetName(skill_id):
        """Purpose: Retrieve the name of a skill by its ID (``Skill.py:21-24``)."""

        return Skill.skill_instance(skill_id).id.GetName()

    @staticmethod
    def GetNameFromWiki(skill_id):
        """Purpose: Retrieve the name of a skill by its ID from the wiki (``Skill.py:26-30``)."""

        data = Skill._load_descriptions()
        return data.get(str(skill_id), {}).get("name", Skill.GetName(skill_id))

    @staticmethod
    def GetURL(skill_id):
        """Purpose: Retrieve the URL of a skill by its ID (``Skill.py:32-36``)."""

        data = Skill._load_descriptions()
        return data.get(str(skill_id), {}).get("url", "")

    @staticmethod
    def GetProgressionData(skill_id):
        """
        Purpose: Retrieve the progression data for a given skill.
        Returns a list of (attribute_name, field_name, values_dict)
        (``Skill.py:38-61``)
        """

        data = Skill._load_descriptions()
        entry = data.get(str(skill_id), {})
        progressions = entry.get("progression")

        if not progressions:
            return []

        if isinstance(progressions, dict):
            progressions = [progressions]

        results = []
        for prog in progressions:
            attr = prog.get("attribute", "")
            field = prog.get("field", "")
            values = {int(k): float(v) for k, v in prog.get("values", {}).items()}
            results.append((attr, field, values))

        return results

    @staticmethod
    def GetID(skill_name: str):
        """Purpose: Retrieve the ID of a skill by its ID (``Skill.py:65-68``)."""

        return Skill.skill_instance(skill_name).id.id

    @staticmethod
    def GetDescription(skill_id: int) -> str:
        """Return full description from skill_descriptions.json (``Skill.py:70-74``)."""

        data = Skill._load_descriptions()
        return data.get(str(skill_id), {}).get("desc_full", "No description available.")

    @staticmethod
    def GetConciseDescription(skill_id: int) -> str:
        """Return concise description from skill_descriptions.json (``Skill.py:76-80``)."""

        data = Skill._load_descriptions()
        return data.get(str(skill_id), {}).get("desc_concise", "No description available.")

    @staticmethod
    def GetType(skill_id):
        """Purpose: Retrieve the type of a skill by its ID. (tuple) (``Skill.py:82-85``)."""

        return Skill.skill_instance(skill_id).type.id, Skill.skill_instance(skill_id).type.GetName()

    @staticmethod
    def GetCampaign(skill_id):
        """Purpose: Retrieve the campaign of a skill by its ID (``Skill.py:87-92``).

        Not built yet: the second half is ``CampaignName`` from ``enums_src/Region_enums.py``
        (``Region_enums.py:132-140``), and that module has no ported home yet. The record's own
        ``campaign`` value is readable through the binding; it is the name table that is missing.
        """

        raise _unported(
            "GetCampaign",
            "enums_src.Region_enums.CampaignName (Region_enums.py:132-140), the campaign-id to name "
            "table the member maps the record's campaign through",
        )

    @staticmethod
    def GetProfession(skill_id):
        """Purpose: Retrieve the profession of a skill by its ID (``Skill.py:94-97``)."""

        return Skill.skill_instance(skill_id).profession.ToInt(), Skill.skill_instance(skill_id).profession.GetName()

    class Data:
        @staticmethod
        def GetCombo(skill_id):
            """Purpose: Retrieve the combo of a skill by its ID (``Skill.py:100-103``)."""

            return Skill.skill_instance(skill_id).combo

        @staticmethod
        def GetComboReq(skill_id):
            """Purpose: Retrieve the combo requirement of a skill by its ID (``Skill.py:105-108``)."""

            return Skill.skill_instance(skill_id).combo_req

        @staticmethod
        def GetWeaponReq(skill_id):
            """Purpose: Retrieve the weapon requirement of a skill by its ID (``Skill.py:110-113``)."""

            return Skill.skill_instance(skill_id).weapon_req

        @staticmethod
        def GetOvercast(skill_id):
            """Purpose: Retrieve the overcast of a skill by its ID (``Skill.py:115-121``)."""

            special = Skill.skill_instance(skill_id).special
            if (special & 0x0001) == 0:
                return 0
            return Skill.skill_instance(skill_id).overcast

        @staticmethod
        def GetEnergyCost(skill_id):
            """Purpose: Retrieve the actual energy cost of a skill by its ID (``Skill.py:123-131``)."""

            cost = Skill.skill_instance(skill_id).energy_cost
            if cost == 11:
                return 15
            elif cost == 12:
                return 25
            return cost

        @staticmethod
        def GetHealthCost(skill_id):
            """Purpose: Retrieve the health cost of a skill by its ID (``Skill.py:133-136``)."""

            return Skill.skill_instance(skill_id).health_cost

        @staticmethod
        def GetAdrenaline(skill_id):
            """Purpose: Retrieve the adrenaline cost of a skill by its ID (``Skill.py:138-141``)."""

            return Skill.skill_instance(skill_id).adrenaline

        @staticmethod
        def GetActivation(skill_id):
            """Purpose: Retrieve the activation time of a skill by its ID (``Skill.py:143-146``)."""

            return Skill.skill_instance(skill_id).activation

        @staticmethod
        def GetAftercast(skill_id):
            """Purpose: Retrieve the aftercast time of a skill by its ID (``Skill.py:148-151``)."""

            return Skill.skill_instance(skill_id).aftercast

        @staticmethod
        def GetRecharge(skill_id):
            """Purpose: Retrieve the recharge time of a skill by its ID (``Skill.py:153-157``).

            GWCA has 2 properties named the same, recharge & Recharge
            """

            return Skill.skill_instance(skill_id).recharge

        @staticmethod
        def GetRecharge2(skill_id):
            """Purpose: Retrieve the recharge time of a skill by its ID (``Skill.py:159-163``).

            GWCA has 2 properties named the same, recharge & Recharge
            """

            return Skill.skill_instance(skill_id).recharge2

        @staticmethod
        def GetAoERange(skill_id):
            """Purpose: Retrieve the AoE range of a skill by its ID (``Skill.py:165-168``)."""

            return Skill.skill_instance(skill_id).aoe_range

        @staticmethod
        def GetAdrenalineA(skill_id):
            """Purpose: Retrieve the adrenaline A value of a skill by its ID (``Skill.py:170-173``)."""

            return Skill.skill_instance(skill_id).adrenaline_a

        @staticmethod
        def GetAdrenalineB(skill_id):
            """Purpose: Retrieve the adrenaline B value of a skill by its ID (``Skill.py:175-178``)."""

            return Skill.skill_instance(skill_id).adrenaline_b

    class Attribute:
        @staticmethod
        def GetAttribute(skill_id):
            """Purpose: Retrieve the attribute of a skill by its ID (``Skill.py:181-184``)."""

            return Skill.skill_instance(skill_id).attribute

        @staticmethod
        def GetScale(skill_id):
            """
            Purpose: Retrieve the scale of a skill at 0 and 15 points by its ID.
            Args:
                skill_id (int): The ID of the skill to retrieve.
            Returns: tuple
            (``Skill.py:186-194``)
            """

            return Skill.skill_instance(skill_id).scale_0pts, Skill.skill_instance(skill_id).scale_15pts

        @staticmethod
        def GetBonusScale(skill_id):
            """
            Purpose: Retrieve the bonus scale of a skill at 0 and 15 points by its ID.
            Args:
                skill_id (int): The ID of the skill to retrieve.
            Returns: float
            (``Skill.py:196-204``)
            """

            return Skill.skill_instance(skill_id).bonus_scale_0pts, Skill.skill_instance(skill_id).bonus_scale_15pts

        @staticmethod
        def GetDuration(skill_id):
            """
            Purpose: Retrieve the duration of a skill at 0 and 15 points by its ID.
            Args:
                skill_id (int): The ID of the skill to retrieve.
            Returns: int
            (``Skill.py:206-214``)
            """

            return Skill.skill_instance(skill_id).duration_0pts, Skill.skill_instance(skill_id).duration_15pts

    class Flags:
        @staticmethod
        def IsTouchRange(skill_id):
            """Purpose: Check if a skill has touch range (``Skill.py:217-220``)."""

            return Skill.skill_instance(skill_id).is_touch_range

        @staticmethod
        def IsElite(skill_id):
            """Purpose: Check if a skill is elite (``Skill.py:222-225``)."""

            return Skill.skill_instance(skill_id).is_elite

        @staticmethod
        def IsHalfRange(skill_id):
            """Purpose: Check if a skill has half range (``Skill.py:227-230``)."""

            return Skill.skill_instance(skill_id).is_half_range

        @staticmethod
        def IsPvP(skill_id):
            """Purpose: Check if a skill is PvP (``Skill.py:232-235``)."""

            return Skill.skill_instance(skill_id).is_pvp

        @staticmethod
        def IsPvE(skill_id):
            """Purpose: Check if a skill is PvE (``Skill.py:237-240``)."""

            return Skill.skill_instance(skill_id).is_pve

        @staticmethod
        def IsPlayable(skill_id):
            """Purpose: Check if a skill is playable (``Skill.py:242-245``)."""

            return Skill.skill_instance(skill_id).is_playable

        @staticmethod
        def IsStacking(skill_id):
            """Purpose: Check if a skill is stacking (``Skill.py:247-250``)."""

            return Skill.skill_instance(skill_id).is_stacking

        @staticmethod
        def IsNonStacking(skill_id):
            """Purpose: Check if a skill is non-stacking (``Skill.py:252-255``)."""

            return Skill.skill_instance(skill_id).is_non_stacking

        @staticmethod
        def IsUnused(skill_id):
            """Purpose: Check if a skill is unused (``Skill.py:257-260``)."""

            return Skill.skill_instance(skill_id).is_unused

        @staticmethod
        def IsHex(skill_id):
            """Purpose: Check if a skill is a Hex (``Skill.py:262-265``)."""

            return Skill.GetType(skill_id)[1] == "Hex"

        @staticmethod
        def IsBounty(skill_id):
            """Purpose: Check if a skill is a Bounty (``Skill.py:267-270``)."""

            return Skill.GetType(skill_id)[1] == "Bounty"

        @staticmethod
        def IsScroll(skill_id):
            """Purpose: Check if a skill is a Scroll (``Skill.py:272-275``)."""

            return Skill.GetType(skill_id)[1] == "Scroll"

        @staticmethod
        def IsStance(skill_id):
            """ Purpose: Check if a skill is a Stance (``Skill.py:277-280``)."""

            return Skill.GetType(skill_id)[1] == "Stance"

        @staticmethod
        def IsSpell(skill_id):
            """Purpose: Check if a skill is a Spell (``Skill.py:282-285``)."""

            return Skill.GetType(skill_id)[1] == "Spell"

        @staticmethod
        def IsEnchantment(skill_id):
            """Purpose: Check if a skill is an Enchantment (``Skill.py:287-290``)."""

            return Skill.GetType(skill_id)[1] == "Enchantment"

        @staticmethod
        def IsSignet(skill_id):
            """Purpose: Check if a skill is a Signet (``Skill.py:292-295``)."""

            return Skill.GetType(skill_id)[1] == "Signet"

        @staticmethod
        def IsCondition(skill_id):
            """Purpose: Check if a skill is a Condition (``Skill.py:297-300``)."""

            return Skill.GetType(skill_id)[1] == "Condition"

        @staticmethod
        def IsWell(skill_id):
            """ Purpose: Check if a skill is a Well (``Skill.py:302-305``)."""

            return Skill.GetType(skill_id)[1] == "Well"

        @staticmethod
        def IsSkill(skill_id):
            """Purpose: Check if a skill is a Skill (``Skill.py:307-310``)."""

            return Skill.GetType(skill_id)[1] == "Skill"

        @staticmethod
        def IsWard(skill_id):
            """Purpose: Check if a skill is a Ward (``Skill.py:312-315``)."""

            return Skill.GetType(skill_id)[1] == "Ward"

        @staticmethod
        def IsGlyph(skill_id):
            """Purpose: Check if a skill is a Glyph (``Skill.py:317-320``)."""

            return Skill.GetType(skill_id)[1] == "Glyph"

        @staticmethod
        def IsTitle(skill_id):
            """Purpose: Check if a skill is a Title (``Skill.py:322-325``)."""

            return Skill.GetType(skill_id)[1] == "Title"

        @staticmethod
        def IsAttack(skill_id):
            """Purpose: Check if a skill is an Attack (``Skill.py:327-330``)."""

            return Skill.GetType(skill_id)[1] == "Attack"

        @staticmethod
        def IsShout(skill_id):
            """Purpose: Check if a skill is a Shout (``Skill.py:332-335``)."""

            return Skill.GetType(skill_id)[1] == "Shout"

        @staticmethod
        def IsSkill2(skill_id):
            """Purpose: Check if a skill is a Skill2 (``Skill.py:337-340``)."""

            return Skill.GetType(skill_id)[1] == "Skill2"

        @staticmethod
        def IsPassive(skill_id):
            """Purpose: Check if a skill is Passive (``Skill.py:342-345``)."""

            return Skill.GetType(skill_id)[1] == "Passive"

        @staticmethod
        def IsEnvironmental(skill_id):
            """Purpose: Check if a skill is Environmental (``Skill.py:347-350``)."""

            return Skill.GetType(skill_id)[1] == "Environmental"

        @staticmethod
        def IsPreparation(skill_id):
            """Purpose: Check if a skill is a Preparation (``Skill.py:352-355``)."""

            return Skill.GetType(skill_id)[1] == "Preparation"

        @staticmethod
        def IsPetAttack(skill_id):
            """Purpose: Check if a skill is a PetAttack (``Skill.py:357-360``)."""

            return Skill.GetType(skill_id)[1] == "PetAttack"

        @staticmethod
        def IsTrap(skill_id):
            """Purpose: Check if a skill is a Trap (``Skill.py:362-365``)."""

            return Skill.GetType(skill_id)[1] == "Trap"

        @staticmethod
        def IsRitual(skill_id):
            """Purpose: Check if a skill is a Ritual (``Skill.py:367-370``)."""

            return Skill.GetType(skill_id)[1] == "Ritual"

        @staticmethod
        def IsEnvironmentalTrap(skill_id):
            """Purpose: Check if a skill is an EnvironmentalTrap (``Skill.py:372-375``)."""

            return Skill.GetType(skill_id)[1] == "EnvironmentalTrap"

        @staticmethod
        def IsItemSpell(skill_id):
            """Purpose: Check if a skill is an ItemSpell (``Skill.py:377-380``)."""

            return Skill.GetType(skill_id)[1] == "ItemSpell"

        @staticmethod
        def IsWeaponSpell(skill_id):
            """Purpose: Check if a skill is a WeaponSpell (``Skill.py:382-385``)."""

            return Skill.GetType(skill_id)[1] == "WeaponSpell"

        @staticmethod
        def IsForm(skill_id):
            """Purpose: Check if a skill is a Form (``Skill.py:387-390``)."""

            return Skill.GetType(skill_id)[1] == "Form"

        @staticmethod
        def IsChant(skill_id):
            """Purpose: Check if a skill is a Chant (``Skill.py:392-395``)."""

            return Skill.GetType(skill_id)[1] == "Chant"

        @staticmethod
        def IsEchoRefrain(skill_id):
            """Purpose: Check if a skill is an EchoRefrain (``Skill.py:397-400``)."""

            return Skill.GetType(skill_id)[1] == "EchoRefrain"

        @staticmethod
        def IsDisguise(skill_id):
            """Purpose: Check if a skill is a Disguise (``Skill.py:402-405``)."""

            return Skill.GetType(skill_id)[1] == "Disguise"

    class Animations:
        @staticmethod
        def GetEffects(skill_id):
            """Purpose: Retrieve the first effect of a skill by its ID (``Skill.py:408-411``)."""

            return Skill.skill_instance(skill_id).effect1, Skill.skill_instance(skill_id).effect2

        @staticmethod
        def GetSpecial(skill_id):
            """ Purpose: Retrieve the special field (``Skill.py:413-416``)."""

            return Skill.skill_instance(skill_id).special

        @staticmethod
        def GetConstEffect(skill_id):
            """Purpose: Retrieve the constant effect of a skill by its ID (``Skill.py:418-421``)."""

            return Skill.skill_instance(skill_id).const_effect

        @staticmethod
        def GetCasterOverheadAnimationID(skill_id):
            """Purpose: Retrieve the caster overhead animation ID (``Skill.py:423-426``)."""

            return Skill.skill_instance(skill_id).caster_overhead_animation_id

        @staticmethod
        def GetCasterBodyAnimationID(skill_id):
            """Purpose: Retrieve the caster body animation ID (``Skill.py:428-431``)."""

            return Skill.skill_instance(skill_id).caster_body_animation_id

        @staticmethod
        def GetTargetBodyAnimationID(skill_id):
            """Purpose: Retrieve the target body animation ID (``Skill.py:433-436``)."""

            return Skill.skill_instance(skill_id).target_body_animation_id

        @staticmethod
        def GetTargetOverheadAnimationID(skill_id):
            """Purpose: Retrieve the target overhead animation ID (``Skill.py:438-441``)."""

            return Skill.skill_instance(skill_id).target_overhead_animation_id

        @staticmethod
        def GetProjectileAnimationID(skill_id):
            """Purpose: Retrieve the first projectile animation ID (``Skill.py:443-446``)."""

            return Skill.skill_instance(skill_id).projectile_animation1_id, Skill.skill_instance(skill_id).projectile_animation2_id

        @staticmethod
        def GetIconFileID(skill_id):
            """Purpose: Retrieve the icon file ID of a skill by its ID (``Skill.py:448-451``)."""

            return Skill.skill_instance(skill_id).icon_file_id, Skill.skill_instance(skill_id).icon_file2_id

    class ExtraData:
        @staticmethod
        def GetCondition(skill_id):
            """Purpose: Retrieve the condition of a skill by its ID (``Skill.py:454-457``)."""

            return Skill.skill_instance(skill_id).condition

        @staticmethod
        def GetTitle(skill_id):
            """Purpose: Retrieve the title of a skill by its ID (``Skill.py:459-462``)."""

            return Skill.skill_instance(skill_id).title

        @staticmethod
        def GetIDPvP(skill_id):
            """Purpose: Retrieve the PvP ID of a skill by its ID (``Skill.py:464-467``)."""

            return Skill.skill_instance(skill_id).id_pvp

        @staticmethod
        def GetTarget(skill_id):
            """Purpose: Retrieve the target of a skill by its ID (``Skill.py:469-472``)."""

            return Skill.skill_instance(skill_id).target

        @staticmethod
        def GetSkillEquipType(skill_id):
            """Purpose: Retrieve the skill equip type of a skill by its ID (``Skill.py:474-477``)."""

            return Skill.skill_instance(skill_id).skill_equip_type

        @staticmethod
        def GetSkillArguments(skill_id):
            """Purpose: Retrieve the skill arguments of a skill by its ID (``Skill.py:479-482``)."""

            return Skill.skill_instance(skill_id).skill_arguments

        @staticmethod
        def GetNameID(skill_id):
            """Purpose: Retrieve the name ID of a skill by its ID (``Skill.py:484-487``)."""

            return Skill.skill_instance(skill_id).name_id

        @staticmethod
        def GetConcise(skill_id):
            """Purpose: Retrieve the concise description of a skill by its ID (``Skill.py:489-492``)."""

            return Skill.skill_instance(skill_id).concise

        @staticmethod
        def GetDescriptionID(skill_id):
            """Purpose: Retrieve the description ID of a skill by its ID (``Skill.py:494-497``)."""

            return Skill.skill_instance(skill_id).description_id

        @staticmethod
        def GetTexturePath(skill_id: int) -> str:
            """``Skill.py:499-503``.

            Not built yet: ``SkillTextureMap`` (``enums_src/Texture_enums.py``) maps ~3100 skill ids
            to icon file names, and that module has no ported home yet.
            """

            raise _unported(
                "GetTexturePath",
                "enums.SkillTextureMap (enums_src/Texture_enums.py, ~3100 entries), the skill-id to "
                "icon-file-name table the member builds the texture path from",
            )
