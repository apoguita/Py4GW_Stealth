"""Port of Reforged's ``Py4GWCoreLib/Skillbar.py`` over the client's own skillbar state.

**Source:** ``Py4GWCoreLib/Skillbar.py`` — 209 lines, ``class SkillBar`` at line 5 with **18**
``@staticmethod``s. Every member keeps the source's name, signature and return values.

**What the source's members read, and what this file carries of it.** Reforged's members are one-line
calls on ``PySkillbar.Skillbar()`` — native's binding object (``skillbar_bindings.cpp:25-142``), which
snapshots the player's ``GW::Context::Skillbar`` and exposes a slot type beside it. So the port
carries:

- :class:`PySkillbar` — native's ``PySkillbarObject``, bound as ``PySkillbar.Skillbar``: the snapshot
  (``agent_id``, eight slots, ``disabled``, ``casting``) plus the actions, with ``GetContext()``
  doing the same map gate and the same copy (``skillbar_bindings.cpp:30-42``);
- :class:`SkillbarSkill` — native's ``PySkillbar.SkillbarSkill`` (``skillbar_bindings.cpp:153-163``)
  over the ported slot record;
- :class:`SkillBar` — Reforged's class, the source's 18 members in the source's order.

**Where each read comes from, in the source's own terms.** The snapshot is
``GW::Context::GetSkillbarArray()`` walked for the controlled character's agent id
(``skillbar_methods.cpp:467-476``); in this port that array is the already-ported
``WorldContext.party_skillbar_array`` (``py4gw/context/world_context.py``), whose ``casting`` word is
the word at ``0xB0`` that native declares under that name (the ported record carries it as the
queued-cast array's size). The cross-module calls native makes are ported members here and are called
rather than re-derived: ``agent::GetControlledCharacterId()`` is
:meth:`py4gw.player.Player.GetAgentID`, and ``agent::GetHeroAgentID(i)`` is
:meth:`py4gw.party.Party.Heroes.GetHeroAgentIDByPartyPosition` (whose docstring records the same
mapping). ``GetIsSkillUnlocked``/``GetIsSkillLearnt`` are the account and world skill bitsets
(``skillbar_methods.cpp:546-570``): the account one is the ported context's own member, and the world
one is the same word/bit test native makes, written here where native writes it.

Three groups exist, and each member says which one it is in its docstring:

``implemented``
    The value comes from a context this project reads — the skillbar array, the account/world skill
    bitsets, the heroes' agent ids, or the client's current tooltip — or the action is a single call
    through an existing catalog resolver (``ChangeHeroSecondary`` → ``skillbar.change_secondary_func``).

``raising from the binding object``
    ``SkillBar``'s members that delegate: the raise comes from :class:`PySkillbar`'s own member, which
    is where native puts the mechanism.

``not built yet``
    Five binding members need something this port does not have: ``UseSkill``, ``UseSkillTargetless``
    and ``HeroUseSkill`` drive the client's **control actions** (native's ``ui::Keypress``,
    ``ui_methods.cpp:1408-1426``: a ``kKeyDown`` frame message, then a ``kKeyUp`` enqueued on the game
    thread), ``LoadSkillTemplate``/``LoadHeroSkillTemplate`` need native's ``DecodeSkillTemplate``
    plus the attribute-requirement gating (``skillbar_methods.cpp:314-411``), and the slot type's
    ``get_recharge`` needs ``MemoryManager::GetSkillTimer``. Each raises ``NotImplementedError``
    through :func:`_unported`, naming what it needs.

**One divergence, measured rather than inferred, and it is about the tooltip.** Native's
``GetCurrentTooltip`` double-dereferences a ``TooltipInfo***`` global; on this build the global holds
the tooltip pointer directly, so :class:`py4gw.ui.tooltip.CurrentTooltip` reads it once. The evidence
(three observations, one of them live) is in that module's docstring.
"""

from __future__ import annotations

from .client import require_client
from .context.world_context import (
    SkillbarSkillStruct,
    SkillbarStruct,
    WorldContextStruct,
)
from .game_thread.shared_block import CallForm
from .skill import SkillID


def _unported(member: str, requirement: str) -> NotImplementedError:
    """Build the error raised by a member this port has not built yet.

    The source's member is complete and working — Reforged is an in-production library — so the
    message never describes the source: it names the work item this port still owes, and the raise
    is what keeps a caller from receiving a plausible wrong value while that work is outstanding.
    """

    return NotImplementedError(
        f"{member} is declared but not built here yet: it needs {requirement}. "
        "The source's member works; this port raises at the call site and names the work "
        "item instead of returning a wrong value."
    )


#: Native's ``ValidateSlot`` (``skillbar_bindings.cpp:44-49``): a slot outside 1..8 is refused, and
#: native raises ``std::out_of_range`` rather than reading a neighbour.
_FIRST_SLOT = 1
_LAST_SLOT = 8

#: Native's ``GetHeroSkillbar`` guard (``skillbar_methods.cpp:479``).
_MAX_HERO_INDEX = 7

#: ``GW::skillbar::GetHoveredSkill`` (``skillbar_methods.cpp:492``): only a payload of this length is
#: a skill tooltip.
SKILL_TOOLTIP_PAYLOAD_LENGTH = 0x14


class SkillbarSkill:
    """Native ``PySkillbar.SkillbarSkill`` (``skillbar_bindings.cpp:153-163``): one skillbar slot.

    ``id`` answers a :class:`py4gw.skill.SkillID`, which is what makes ``.id.id`` and
    ``.id.GetName()`` work for a caller, exactly as native's property does
    (``skillbar_bindings.cpp:154-156``).
    """

    def __init__(self, slot: SkillbarSkillStruct) -> None:
        """Wrap one ported ``SkillbarSkillStruct`` record."""

        self.slot = slot

    @property
    def id(self) -> SkillID:
        """Return the slot's skill id as native's ``SkillID``."""

        return SkillID(int(self.slot.skill_id))

    @property
    def adrenaline_a(self) -> int:
        """Return the slot's first adrenaline word."""

        return int(self.slot.adrenaline_a)

    @property
    def adrenaline_b(self) -> int:
        """Return the slot's second adrenaline word."""

        return int(self.slot.adrenaline_b)

    @property
    def recharge(self) -> int:
        """Return the slot's raw recharge timestamp."""

        return int(self.slot.recharge)

    @property
    def event(self) -> int:
        """Return the slot's event word."""

        return int(self.slot.event)

    @property
    def get_recharge(self) -> int:
        """``SkillbarSkill::GetRecharge`` (``skill.cpp:20-25``).

        Not built yet: it is ``recharge - PY4GW::MemoryManager::GetSkillTimer()``, and that timer is
        ``timeGetTime() + *g_skill_timer_ptr`` (``memory_manager.cpp:69-71``) — the client global the
        catalog names ``memory.skill_timer_ptr`` plus a host ``timeGetTime()``. Neither half is
        ported yet, and the same timer is what ``Effect.GetTimeElapsed``/``GetTimeRemaining`` need.
        """

        raise _unported(
            "SkillbarSkill.get_recharge",
            "PY4GW::MemoryManager::GetSkillTimer (memory_manager.cpp:69-71) = timeGetTime() + "
            "*g_skill_timer_ptr, the client global the catalog names memory.skill_timer_ptr, "
            "plus the host timeGetTime() call",
        )


def _world_skillbar_bitset(world: WorldContextStruct, skill_id: int) -> bool:
    """The word/bit test native's ``GetIsSkillLearnt`` makes (``skillbar_methods.cpp:560-570``)."""

    words = world.unlocked_character_skills
    if not words:
        return False
    index = int(skill_id)
    real_index = index // 32
    if real_index >= len(words):
        return False
    return bool(int(words[real_index]) & (1 << (index % 32)))


class PySkillbar:
    """Native ``PySkillbar.Skillbar`` (``skillbar_bindings.cpp:25-142``).

    A snapshot of the player's skillbar, refreshed by :meth:`GetContext`, with the data members
    native exposes and the actions beside them. ``data`` is the ported
    ``py4gw.context.world_context.SkillbarStruct`` the snapshot was copied from — the same 0xBC
    record native copies (``skillbar_bindings.cpp:30-42``).
    """

    def __init__(self) -> None:
        self.data: SkillbarStruct | None = None
        self.GetContext()

    def GetContext(self) -> None:
        """Snapshot the player's skillbar (``skillbar_bindings.cpp:30-42``).

        Native's gate is ``GetIsMapLoaded() && !GetIsObserving() && instance != Loading`` — the same
        condition, in the same order, that ``dialog.cpp``'s readers make, and the port expresses it
        the same way: the ported ``Map.IsMapReady()``.
        """

        from .map import Map

        if not Map.IsMapReady():
            self.data = None
            return

        self.data = _find_skillbar(_controlled_character_id())

    def GetSkill(self, slot: int) -> SkillbarSkill:
        """Return one slot, refusing a slot outside ``1..8`` (``skillbar_bindings.cpp:44-54``)."""

        if slot < _FIRST_SLOT or slot > _LAST_SLOT:
            raise IndexError(
                "Skill slot out of range (must be between 1 and 8) Given: " + str(slot)
            )
        data = self.data
        if data is None:
            return SkillbarSkill(SkillbarSkillStruct())
        return SkillbarSkill(data.skills[slot - 1])

    def GetSkills(self) -> list[SkillbarSkill]:
        """Return all eight slots (``skillbar_bindings.cpp:56-60``)."""

        return [self.GetSkill(slot) for slot in range(_FIRST_SLOT, _LAST_SLOT + 1)]

    @property
    def agent_id(self) -> int:
        """Return the skillbar owner's agent id (``skillbar_bindings.cpp:170``)."""

        return 0 if self.data is None else int(self.data.agent_id)

    @property
    def disabled(self) -> int:
        """Return the skillbar's disabled word (``skillbar_bindings.cpp:171``)."""

        return 0 if self.data is None else int(self.data.disabled)

    @property
    def casting(self) -> int:
        """Return the skillbar's casting word (``skillbar_bindings.cpp:172``).

        Native reads ``data.casting`` (the word at ``0xB0``, ``skillbar.h:114``); the ported record
        carries that word as the queued-cast array's size, so this reads the same four bytes.
        """

        return 0 if self.data is None else int(self.data.cast_array.m_size)

    def GetHeroSkillbar(self, hero_index: int) -> list[SkillbarSkill]:
        """Return a hero's eight slots (``skillbar_bindings.cpp:122-128``).

        Native walks the same skillbar array for ``agent::GetHeroAgentID(hero_index)`` and refuses an
        index above ``7`` (``skillbar_methods.cpp:478-488``); the empty list is native's empty
        ``py::list``.
        """

        if hero_index > _MAX_HERO_INDEX:
            return []
        data = _find_skillbar(_hero_agent_id(hero_index))
        if data is None:
            return []
        return [SkillbarSkill(data.skills[slot - 1]) for slot in range(_FIRST_SLOT, _LAST_SLOT + 1)]

    def GetHoveredSkill(self) -> int:
        """Return the skill id under the cursor, or ``0`` (``skillbar_bindings.cpp:130-133``).

        ``GW::skillbar::GetHoveredSkill`` (``skillbar_methods.cpp:490-496``) requires the client's
        current tooltip to carry a ``0x14``-byte payload, reads its first word as a skill id, and
        answers the record's own ``skill_id``; the tooltip read is ``py4gw/ui/tooltip.py``.
        """

        client = require_client()
        tooltip = client.read_current_tooltip()
        if tooltip is None or int(tooltip.payload_len) != SKILL_TOOLTIP_PAYLOAD_LENGTH:
            return 0
        skill_id = client.current_tooltip.read_payload_word(tooltip)
        if skill_id is None:
            return 0
        record = client.read_skill(skill_id)
        return 0 if record is None else int(record.skill_id)

    def IsSkillUnlocked(self, skill_id: int) -> bool:
        """``GW::skillbar::GetIsSkillUnlocked`` (``skillbar_methods.cpp:546-558``)."""

        account_context = require_client().read_account_context()
        if account_context is None:
            return False
        return account_context.is_account_skill_unlocked(skill_id)

    def IsSkillLearnt(self, skill_id: int) -> bool:
        """``GW::skillbar::GetIsSkillLearnt`` (``skillbar_methods.cpp:560-570``)."""

        world = require_client().read_world_context()
        if world is None:
            return False
        return _world_skillbar_bitset(world, skill_id)

    def ChangeHeroSecondary(self, hero_index: int, profession: int) -> bool:
        """``GW::skillbar::ChangeSecondProfession`` (``skillbar_methods.cpp:85-93``)."""

        hero_agent_id = _hero_agent_id(hero_index)
        if not hero_agent_id:
            return False
        require_client().call_function(
            "skillbar.change_secondary_func",
            CallForm.U32_U32,
            hero_agent_id,
            profession,
        )
        return True

    def LoadSkillTemplate(self, skill_template: str) -> None:
        """``GW::skillbar::LoadSkillTemplate`` (``skillbar_methods.cpp:314-355``).

        Not built yet: it decodes the template (native's ``DecodeSkillTemplate``), gates it against
        the character's professions and the attribute table, and only then calls the client's
        load-skills/load-attributes/change-secondary functions — all three of which this project can
        already resolve (``skillbar.load_skills_func``, ``skillbar.load_attributes_func``,
        ``skillbar.change_secondary_func``).
        """

        raise _unported(
            "LoadSkillTemplate",
            "native's DecodeSkillTemplate and the profession/attribute gating "
            "(skillbar_methods.cpp:230-355), which stand in front of the three load functions this "
            "project already resolves: skillbar.load_skills_func, skillbar.load_attributes_func and "
            "skillbar.change_secondary_func",
        )

    def LoadHeroSkillTemplate(self, hero_index: int, skill_template: str) -> None:
        """``GW::skillbar::LoadSkillTemplate(template, hero_index)`` (``skillbar_methods.cpp:357``)."""

        raise _unported(
            "LoadHeroSkillTemplate",
            "native's DecodeSkillTemplate and the same profession/attribute gating as "
            "LoadSkillTemplate, plus the hero branch (skillbar_methods.cpp:357-411) that reads the "
            "party hero list",
        )

    def UseSkill(self, slot: int, target: int = 0) -> bool:
        """``GW::skillbar::UseSkill`` (``skillbar_methods.cpp:439-443``).

        Not built yet: it targets first and then presses the client's own control action —
        ``ui::Keypress(ControlAction_UseSkill1 + slot)``, which is a ``kKeyDown`` frame message with
        a ``KeyAction`` payload followed by a game-thread ``kKeyUp`` (``ui_methods.cpp:1408-1426``).
        The catalog has the frame-message function and the port has the UI-message form, but the
        control-action values, the button-action frame and the key pairing are not ported.
        """

        raise _unported(
            "UseSkill",
            "ui::Keypress (ui_methods.cpp:1408-1426): the kKeyDown frame message carrying a "
            "KeyAction payload, the control-action values (ControlAction_UseSkill1 + slot), the "
            "button-action frame, and the game-thread kKeyUp that follows",
        )

    def UseSkillTargetless(self, slot: int) -> bool:
        """``GW::skillbar::PointBlankUseSkill`` (``skillbar_methods.cpp:445-447``)."""

        raise _unported(
            "UseSkillTargetless",
            "the same ui::Keypress mechanism as UseSkill (ui_methods.cpp:1408-1426)",
        )

    def HeroUseSkill(self, target_agent_id: int, skill_number: int, hero_index: int) -> bool:
        """``PySkillbarObject::HeroUseSkill`` (``skillbar_bindings.cpp:88-115``)."""

        raise _unported(
            "HeroUseSkill",
            "the ui::Keypress mechanism plus the hero control actions "
            "(ControlAction_Hero1Skill1..ControlAction_Hero7Skill1, skillbar_bindings.cpp:91-101) "
            "and the target change around the press",
        )


def _controlled_character_id() -> int:
    """``agent::GetControlledCharacterId()`` (``agent_methods.cpp:60``), through the ported member."""

    from .player import Player

    return int(Player.GetAgentID())


def _hero_agent_id(hero_index: int) -> int:
    """``agent::GetHeroAgentID(hero_index)`` (``agent_methods.cpp:240-247``)."""

    from .party import Party

    return int(Party.Heroes.GetHeroAgentIDByPartyPosition(hero_index))


def _skillbar_array() -> list[SkillbarStruct]:
    """``GW::Context::GetSkillbarArray()`` (``context_methods.cpp:234-237``)."""

    world = require_client().read_world_context()
    if world is None:
        return []
    return list(world.skillbars or [])


def _find_skillbar(agent_id: int) -> SkillbarStruct | None:
    """The skillbar whose ``agent_id`` matches, as ``GetPlayerSkillbar``/``GetHeroSkillbar`` walk it."""

    if not agent_id:
        return None
    for skillbar in _skillbar_array():
        if int(skillbar.agent_id) == agent_id:
            return skillbar
    return None


class SkillBar:
    """The Reforged ``SkillBar`` class (``Skillbar.py:5-209``): 18 static members."""

    @staticmethod
    def LoadSkillTemplate(skill_template):
        """
        Purpose: Load a skill template by name.
        Args:
            template_name (str): The name of the skill template to load.
        Returns: None
        (``Skillbar.py:6-15``)
        """
        skillbar_instance = PySkillbar()
        skillbar_instance.LoadSkillTemplate(skill_template)

    @staticmethod
    def LoadHeroSkillTemplate(hero_index, skill_template):
        """
        Purpose: Load a Hero skill template by Hero index and Template.
        Args:
            hero_index: int, template_name (str): The name of the skill template to load.
        Returns: None
        (``Skillbar.py:17-26``)
        """
        skillbar_instance = PySkillbar()
        skillbar_instance.LoadHeroSkillTemplate(hero_index, skill_template)

    @staticmethod
    def GetSkillbar() -> list[int]:
        """
        Purpose: Retrieve the IDs of all 8 skills in the skill bar.
        Returns: list: A list containing the IDs of all 8 skills.
        (``Skillbar.py:28-39``)
        """
        skill_ids = []
        for slot in range(1, 9):  # Loop through skill slots 1 to 8
            skill_id = SkillBar.GetSkillIDBySlot(slot)
            if skill_id != 0:
                skill_ids.append(skill_id)
        return skill_ids

    @staticmethod
    def GetZeroFilledSkillbar():
        """``Skillbar.py:41-47``."""
        skill_ids: dict[int, int] = {}
        for slot in range(1, 9):  # Loop through skill slots 1 to 8
            skill_ids[slot] = SkillBar.GetSkillIDBySlot(slot)

        return skill_ids

    @staticmethod
    def GetHeroSkillbar(hero_index):
        """
        Purpose: Retrieve the skill bar of a hero.
        Args:
            hero_index (int): The index of the hero to retrieve the skill bar from.
        Returns: list: A list of dictionaries containing skill details.
        (``Skillbar.py:49-59``)
        """
        skillbar_instance = PySkillbar()
        hero_skillbar = skillbar_instance.GetHeroSkillbar(hero_index)
        return hero_skillbar

    @staticmethod
    def UseSkill(skill_slot, target_agent_id=0):
        """
        Purpose: Use a skill from the skill bar.
        Args:
            skill_slot (int): The slot number of the skill to use (1-8).
            target_agent_id (int, optional): The ID of the target agent. Default is 0.
        Returns: None
        (``Skillbar.py:62-72``)
        """
        skillbar_instance = PySkillbar()
        skillbar_instance.UseSkill(skill_slot, target_agent_id)

    @staticmethod
    def UseSkillTargetless(skill_slot):
        """
        Purpose: Use a skill from the skill bar without a target.
        Args:
            skill_slot (int): The slot number of the skill to use (1-8).
        Returns: None
        (``Skillbar.py:74-83``)
        """
        skillbar_instance = PySkillbar()
        skillbar_instance.UseSkillTargetless(skill_slot)

    @staticmethod
    def HeroUseSkill(target_agent_id, skill_number, hero_number):
        """
        Have a hero use a skill.
        Args:
            target_agent_id (int): The target agent ID.
            skill_number (int): The skill number (1-8)
            hero_number (int): The hero number (1-7)
        (``Skillbar.py:85-95``)
        """
        skillbar_instance = PySkillbar()
        skillbar_instance.HeroUseSkill(target_agent_id, skill_number, hero_number)

    @staticmethod
    def ChangeHeroSecondary(hero_index, secondary_profession):
        """
        Purpose: Change the secondary profession of a hero.
        Args:
            hero_index (int): The index of the hero to change.
            secondary_profession (int): The ID of the secondary profession to change to.
        Returns: None
        (``Skillbar.py:97-107``)
        """
        skillbar_instance = PySkillbar()
        skillbar_instance.ChangeHeroSecondary(hero_index, secondary_profession)

    @staticmethod
    def GetSkillIDBySlot(skill_slot):
        """
        Purpose: Retrieve the data of a skill by its slot number.
        Args:
            skill_slot (int): The slot number of the skill to retrieve (1-8).
        Returns: dict: A dictionary containing skill details retrieved by slot.
        (``Skillbar.py:109-119``)
        """
        skillbar_instance = PySkillbar()
        skill = skillbar_instance.GetSkill(skill_slot)
        return skill.id.id

    #get the slot by skillid
    @staticmethod
    def GetSlotBySkillID(skill_id):
        """
        Purpose: Retrieve the slot number of a skill by its ID.
        Args:
            skill_id (int): The ID of the skill to retrieve.
        Returns: int: The slot number of the skill.
        (``Skillbar.py:121-135``)
        """
        #search for all slots until skill found and return it
        for i in range(1, 9):
            if SkillBar.GetSkillIDBySlot(i) == skill_id:
                return i

        return 0

    @staticmethod
    def GetSkillData(slot):
        """
        Purpose: Retrieve the data of a skill by its ID.
        Args:
            slot (int): The slot number of the skill to retrieve (1-8).
        Returns: dict: A SkillbarSkill object containing skill details.
        (``Skillbar.py:137-146``)
        """
        skill_instance = PySkillbar()
        return skill_instance.GetSkill(slot)

    @staticmethod
    def GetHoveredSkillID():
        """
        Purpose: Retrieve the ID of the skill that is currently hovered.
        Args: None
        Returns: int: The ID of the skill that is currently hovered.
        (``Skillbar.py:148-157``)
        """
        skillbar_instance = PySkillbar()
        hovered_skill_id = skillbar_instance.GetHoveredSkill()
        return hovered_skill_id

    @staticmethod
    def IsSkillUnlocked(skill_id):
        """
        Purpose: Check if a skill is unlocked.
        Args:
            skill_id (int): The ID of the skill to check.
        Returns: bool: True if the skill is unlocked, False otherwise.
        (``Skillbar.py:159-168``)
        """
        skillbar_instance = PySkillbar()
        return skillbar_instance.IsSkillUnlocked(skill_id)

    @staticmethod
    def IsSkillLearnt(skill_id):
        """
        Purpose: Check if a skill is learnt.
        Args:
            skill_id (int): The ID of the skill to check.
        Returns: bool: True if the skill is learnt, False otherwise.
        (``Skillbar.py:170-179``)
        """
        skillbar_instance = PySkillbar()
        return skillbar_instance.IsSkillLearnt(skill_id)

    @staticmethod
    def GetAgentID():
        """
        Purpose: Retrieve the agent ID of the skill bar owner.
        Args: None
        Returns: int: The agent ID of the skill bar owner.
        (``Skillbar.py:181-189``)
        """
        skillbar_instance = PySkillbar()
        return skillbar_instance.agent_id

    @staticmethod
    def GetDisabled():
        """
        Purpose: Check if the skill bar is disabled.
        Args: None
        Returns: bool: True if the skill bar is disabled, False otherwise.
        (``Skillbar.py:191-199``)
        """
        skillbar_instance = PySkillbar()
        return skillbar_instance.disabled

    @staticmethod
    def GetCasting():
        """
        Purpose: Check if the skill bar is currently casting.
        Args: None
        Returns: bool: True if the skill bar is currently casting, False otherwise.
        (``Skillbar.py:201-209``)
        """
        skillbar_instance = PySkillbar()
        return skillbar_instance.casting
