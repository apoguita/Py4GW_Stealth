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

**Every member of the class answers, and each one is in the source's own terms.** ``SkillBar``'s 18
members are all built: what they read comes from contexts this project already carries, and what they
do is the client's own machinery reached through catalog resolvers.

- ``UseSkill``/``UseSkillTargetless``/``HeroUseSkill`` press the client's **control actions**
  (``skillbar_methods.cpp:439-447``, ``skillbar_bindings.cpp:70-115``) — ``ControlAction_UseSkill1``
  plus the zero-based slot, and the seven ``ControlAction_Hero{N}Skill1`` bases behind a switch —
  through the ported :meth:`py4gw.ui_manager.UIManager.Keypress`, the same mechanism
  ``Party.Heroes.UseSkill`` drives.
- ``LoadSkillTemplate``/``LoadHeroSkillTemplate`` decode the template and gate it
  (``skillbar_methods.cpp:190-411``) before calling the three functions the catalog resolves:
  ``skillbar.load_skills_func``, ``skillbar.load_attributes_func`` and
  ``skillbar.change_secondary_func``. The decoder and its helpers are the block below
  :class:`SkillTemplate`; ``skillbar.attribute_array_addr`` is what reads the attribute constants they
  gate against.
- ``ChangeHeroSecondary`` → ``skillbar.change_secondary_func``, and the slot type's ``get_recharge``
  → the ported skill timer (``py4gw/memory/memory_manager.py``).

**Nothing in this file raises**, so it carries no ``_unported`` helper: the last member that needed one
was ``LoadSkillTemplate``, and the template decoder closed it.

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
from .enums_src.ui_enums import ControlAction
from .game_thread.shared_block import CallForm
from .skill import SkillID


#: Native's ``ValidateSlot`` (``skillbar_bindings.cpp:44-49``): a slot outside 1..8 is refused, and
#: native raises ``std::out_of_range`` rather than reading a neighbour.
_FIRST_SLOT = 1
_LAST_SLOT = 8

#: Native's ``GetHeroSkillbar`` guard (``skillbar_methods.cpp:479``).
_MAX_HERO_INDEX = 7

#: ``GW::skillbar::GetHoveredSkill`` (``skillbar_methods.cpp:492``): only a payload of this length is
#: a skill tooltip.
SKILL_TOOLTIP_PAYLOAD_LENGTH = 0x14

#: The seven ``ControlAction_Hero{N}Skill1`` bases, indexed by the switch's own ``hero_index - 1``
#: (``skillbar_bindings.cpp:92-101``). The bases are **not** an arithmetic series — ``0xE5``, ``0xED``,
#: ``0xF5``, then ``0x106``, ``0x10E``, ``0x116``, ``0x11E`` — which is why the source writes a switch,
#: and the values are this port's ``ControlAction`` table (``enums_src/ui_enums.py:628-682``).
#: ``PyParty::UseHeroSkill`` (``party_bindings.cpp:424-447``) writes the same switch for the same seven
#: values; the two bindings are separate members in the source and each keeps its own copy here.
_HERO_SKILL_ACTION_BASE: dict[int, int] = {
    0: int(ControlAction.ControlAction_Hero1Skill1),
    1: int(ControlAction.ControlAction_Hero2Skill1),
    2: int(ControlAction.ControlAction_Hero3Skill1),
    3: int(ControlAction.ControlAction_Hero4Skill1),
    4: int(ControlAction.ControlAction_Hero5Skill1),
    5: int(ControlAction.ControlAction_Hero6Skill1),
    6: int(ControlAction.ControlAction_Hero7Skill1),
}


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

        ``recharge == 0 ? 0 : recharge - PY4GW::MemoryManager::GetSkillTimer()``. The timer landed
        on 2026-09-26 (``py4gw/memory/memory_manager.py``: ``timeGetTime()`` plus the client global
        the catalog names ``memory.skill_timer_ptr``), which is what this member had been raising
        for — and the same timer the effect snapshot's ``time_elapsed``/``time_remaining`` need.

        The subtraction is ``uint32_t`` in the source, so it wraps; masked here the way the
        register does.
        """

        recharge = int(self.slot.recharge)
        if recharge == 0:
            return 0
        timer = require_client().memory_manager.GetSkillTimer()
        return (recharge - timer) & 0xFFFFFFFF


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


# ── Skill templates: ``skillbar_methods.cpp:190-411`` ─────────────────────────────────────────────
#
# Native decodes a build template in-process, gates it against the character's own professions and
# attributes, and only then hands the decoded arrays to the client's load functions. Everything before
# that last step is a pure function over records this port already reads, which is why it can be
# checked without a client — and why it is its own block rather than code inside the two members.

#: ``Context::GetAttributeInfoArray``'s own bound (``skillbar.cpp:41``):
#: ``uint32_t g_attribute_array_count = 0x33;``. A literal in the source, not something it measures,
#: and the same ``0x33`` the client's own accessor writes in the pattern this port's
#: ``skillbar.attribute_array_addr`` scans (``ba 33 00 00 00``, ``offsets/skillbar.json``).
ATTRIBUTE_ARRAY_COUNT = 0x33

#: ``DecodeSkillTemplate``'s own ceiling (``skillbar_methods.cpp:191``): ``const int SKILL_MAX = 3431;``
SKILL_MAX = 3431

#: ``SkillTemplate``'s two array sizes (``skill.h:165-170``): ``skills[8]`` and ``attributes[16]``.
TEMPLATE_SKILL_COUNT = 8
TEMPLATE_ATTRIBUTE_COUNT = 16

#: The template alphabet and its reverse. ``kBase64Table`` (``skillbar_methods.cpp:37-38``) is the
#: alphabet; ``kBase64ToValue`` (``:26-35``) is a 128-entry table holding ``-1`` for every character
#: outside it. The map is built from the alphabet here so the two cannot drift, and it holds the
#: source's own values: ``A``→0, ``+``→62, ``/``→63, and a ``.get`` miss is the source's ``-1``.
BASE64_TABLE = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
BASE64_TO_VALUE: dict[str, int] = {c: value for value, c in enumerate(BASE64_TABLE)}

#: ``Constants::Profession::Dervish`` — the last profession the decoder accepts
#: (``skillbar_methods.cpp:228``); ``None`` is ``0``.
PROFESSION_NONE = 0
PROFESSION_DERVISH = 8

#: ``Constants::Attribute::None`` (``constants.h:85``): the word the decoder writes into every
#: unfilled attribute slot (``skillbar_methods.cpp:276``).
ATTRIBUTE_NONE = 0xFF

#: ``Constants::InstanceType::Outpost`` — the gate both loaders make first
#: (``skillbar_methods.cpp:317``, ``:360``), read through the ported ``Map.GetInstanceType``.
INSTANCE_TYPE_OUTPOST = 0

#: The ten primary attributes, from the switch ``GetAttributeProfession`` writes
#: (``skillbar.cpp:107-119``). The ids are ``Constants::Attribute``'s own (``constants.h:73-86``):
#: the enum counts from ``FastCasting`` at ``0``, and ``DaggerMastery = 29`` fixes every value from
#: there on.
PRIMARY_ATTRIBUTES: frozenset[int] = frozenset(
    {
        0,   # FastCasting
        6,   # SoulReaping
        12,  # EnergyStorage
        16,  # DivineFavor
        17,  # Strength
        23,  # Expertise
        35,  # CriticalStrikes
        36,  # SpawningPower
        40,  # Leadership
        44,  # Mysticism
    }
)

#: Where the two load functions' arrays are built, in the block's data region. Native passes
#: ``uint32_t*`` into buffers it owns in-process (``skillbar_methods.cpp:98-103``, ``:426-427``); a
#: Python list is not in the client, so the words go here and their addresses are handed over — the
#: same substitution ``py4gw/merchant.py`` makes for its ingredient lists. The span starts above the
#: pathing region (which ends at ``0x1244``) and stays inside the block.
TEMPLATE_SKILLS_OFFSET = 0x1800
TEMPLATE_ATTRIBUTE_IDS_OFFSET = TEMPLATE_SKILLS_OFFSET + 4 * TEMPLATE_SKILL_COUNT
TEMPLATE_ATTRIBUTE_VALUES_OFFSET = TEMPLATE_ATTRIBUTE_IDS_OFFSET + 4 * TEMPLATE_ATTRIBUTE_COUNT

LOAD_SKILLS_FUNC = "skillbar.load_skills_func"
LOAD_ATTRIBUTES_FUNC = "skillbar.load_attributes_func"
CHANGE_SECONDARY_FUNC = "skillbar.change_secondary_func"
ATTRIBUTE_ARRAY_RESOLVER = "skillbar.attribute_array_addr"


class SkillTemplateAttribute:
    """``Context::SkillTemplateAttribute`` (``skill.h:160-163``): one attribute and its points."""

    __slots__ = ("attribute", "points")

    def __init__(self, attribute: int = ATTRIBUTE_NONE, points: int = 0) -> None:
        self.attribute = int(attribute)
        self.points = int(points)


class SkillTemplate:
    """``Context::SkillTemplate`` (``skill.h:165-170``).

    ``skills`` is eight ``SkillID`` slots and ``attributes`` sixteen ``SkillTemplateAttribute`` slots
    — the sizes the source's ``_countof`` calls read throughout ``DecodeSkillTemplate``.
    """

    __slots__ = ("primary", "secondary", "skills", "attributes")

    def __init__(self) -> None:
        self.primary = PROFESSION_NONE
        self.secondary = PROFESSION_NONE
        self.skills = [0] * TEMPLATE_SKILL_COUNT
        self.attributes = [SkillTemplateAttribute() for _ in range(TEMPLATE_ATTRIBUTE_COUNT)]


def _read_bits(bits: list[int], position: int, count: int) -> tuple[int, int]:
    """``ReadBits`` (``skillbar_methods.cpp:47-55``): least significant bit first, cursor advancing.

    The source walks a ``char*`` of ``0``/``1`` bytes doing ``val |= (*s++ << i)``, which is the order
    ``WriteBits`` (``:40-45``) wrote them in. The port carries the bits in a list and the cursor as an
    integer; the arithmetic is the source's.
    """

    value = 0
    for index in range(count):
        value |= bits[position + index] << index
    return value, position + count


def _skill_constant_record(skill_id: int):
    """``GetSkillConstantData`` (``skillbar_methods.cpp:73-76``): the record, or ``None`` for its null."""

    from .context.skill_context import SKILL_ARRAY_LENGTH

    if skill_id < 0 or skill_id >= SKILL_ARRAY_LENGTH:
        return None
    try:
        return require_client().read_skill(int(skill_id))
    except Exception:
        return None


def _attribute_info_array() -> list | None:
    """``Context::GetAttributeInfoArray`` — the client's attribute-constant table, or ``None``.

    The resolver is this project's ``skillbar.attribute_array_addr``, which points at the same table
    the client's own accessor fills (``ba 33 00 00 00`` writes the bound). ``None`` is native's null
    (``skillbar_methods.cpp:79``), which is what makes every reader below answer as the source does
    when the table is absent.
    """

    import ctypes

    from .context.world_context import AttributeInfoStruct

    client = require_client()
    if not client.resolves(ATTRIBUTE_ARRAY_RESOLVER):
        return None
    base = client._resolve(ATTRIBUTE_ARRAY_RESOLVER)
    if not base:
        return None
    size = ctypes.sizeof(AttributeInfoStruct)
    return [
        AttributeInfoStruct.from_buffer_copy(client.reader.read(base + index * size, size))
        for index in range(ATTRIBUTE_ARRAY_COUNT)
    ]


def get_attribute_constant_data(attribute: int):
    """``GetAttributeConstantData`` (``skillbar_methods.cpp:78-83``): the record, or ``None``.

    Native's second guard is kept: an id at or past ``g_attribute_array_count`` answers null before
    the array is indexed.
    """

    if attribute >= ATTRIBUTE_ARRAY_COUNT:
        return None
    records = _attribute_info_array()
    if not records:
        return None
    return records[attribute]


def get_attribute_profession(attribute: int, want_primary: bool = False) -> tuple[int, bool]:
    """``GetAttributeProfession`` (``skillbar.cpp:102-126``): the owning profession and the primary flag.

    Native answers ``Profession::None`` when the constant record is missing, and fills the caller's
    ``is_primary_attribute`` **only** when the caller passed the pointer — which is why the flag is a
    requested value here rather than something always computed.
    """

    info = get_attribute_constant_data(attribute)
    if info is None:
        return PROFESSION_NONE, False
    return int(info.profession_id), bool(want_primary and attribute in PRIMARY_ATTRIBUTES)


def get_skill_profession(skill_id: int) -> int:
    """``GetSkillProfession`` (``skillbar.cpp:97-100``): the record's profession, or ``None``."""

    record = _skill_constant_record(skill_id)
    if record is None:
        return PROFESSION_NONE
    return int(record.profession)


def is_primary_attribute_required(template: SkillTemplate, profession: int) -> bool:
    """``IsPrimaryAttributeRequired`` (``skillbar.cpp:128-138``)."""

    if profession == PROFESSION_NONE:
        return False
    for attribute in template.attributes:
        owner, is_primary = get_attribute_profession(attribute.attribute, want_primary=True)
        if owner == profession and is_primary:
            return True
    return False


def is_profession_required(template: SkillTemplate, profession: int) -> bool:
    """``IsProfessionRequired`` (``skillbar.cpp:140-152``): the skills first, then the attributes."""

    if profession == PROFESSION_NONE:
        return False
    for skill_id in template.skills:
        if get_skill_profession(skill_id) == profession:
            return True
    for attribute in template.attributes:
        if get_attribute_profession(attribute.attribute)[0] == profession:
            return True
    return False


def get_agent_profession_state(agent_id: int):
    """``GetAgentProfessionState`` (``skillbar.cpp:87-95``): the party record for one agent."""

    from .party import Party

    world = Party._world()
    if world is None:
        return None
    for state in world.party_profession_states or []:
        if int(state.agent_id) == int(agent_id):
            return state
    return None


def change_second_profession(profession: int, hero_index: int = 0) -> bool:
    """``ChangeSecondProfession`` (``skillbar_methods.cpp:85-93``)."""

    agent_id = _hero_agent_id(hero_index)
    if not agent_id:
        return False
    client = require_client()
    if not client.resolves(CHANGE_SECONDARY_FUNC):
        return False
    client.call_function(CHANGE_SECONDARY_FUNC, CallForm.U32_U32, agent_id, int(profession))
    return True


def _place_array(offset: int, words: list[int]) -> int:
    """Write words into the block's data region and return the address they now sit at."""

    import struct

    payload = b"".join(struct.pack("<I", int(word)) for word in words)
    return require_client().bridge.write_data(offset, payload)


def load_skillbar(skills: list[int], hero_index: int = 0) -> bool:
    """``LoadSkillbar`` (``skillbar_methods.cpp:95-114``).

    The array is built in memory the client can read and its address passed, which is what native's
    ``malloc``/``memcpy`` pair exists for; a zero agent id refuses before the call, as native does.
    """

    client = require_client()
    if not client.resolves(LOAD_SKILLS_FUNC):
        return False
    agent_id = _hero_agent_id(hero_index)
    if not agent_id:
        return False
    address = _place_array(TEMPLATE_SKILLS_OFFSET, skills)
    client.call_function(LOAD_SKILLS_FUNC, CallForm.STACK_WORDS, agent_id, len(skills), address)
    return True


def set_attributes(attributes: list[SkillTemplateAttribute], hero_index: int = 0) -> bool:
    """``SetAttributes`` (``skillbar_methods.cpp:424-437`` over ``:413-422``).

    Native's loop stops at the first ``Attribute::None`` slot and hands over two arrays; the agent id
    is fetched and a zero one refuses, because *"agent_id 0 trips the client's own assert"* (``:419``).
    """

    client = require_client()
    if not client.resolves(LOAD_ATTRIBUTES_FUNC):
        return False
    agent_id = _hero_agent_id(hero_index)
    if not agent_id:
        return False

    ids: list[int] = []
    values: list[int] = []
    for attribute in attributes:
        if attribute.attribute == ATTRIBUTE_NONE:
            break
        ids.append(int(attribute.attribute))
        values.append(int(attribute.points))

    id_address = _place_array(TEMPLATE_ATTRIBUTE_IDS_OFFSET, ids or [0])
    value_address = _place_array(TEMPLATE_ATTRIBUTE_VALUES_OFFSET, values or [0])
    client.call_function(
        LOAD_ATTRIBUTES_FUNC,
        CallForm.STACK_WORDS,
        agent_id,
        len(ids),
        id_address,
        value_address,
    )
    return True


def decode_skill_template(template: str) -> SkillTemplate | None:
    """``DecodeSkillTemplate`` (``skillbar_methods.cpp:190-312``), every guard in the source's order.

    ``None`` is the source's ``false``, and each of its refusals is one here: a character outside the
    alphabet, a header that is neither ``0`` nor ``14``, a profession pair out of range, an attribute
    count at or past the array, an attribute id or value out of range, a skill id past ``SKILL_MAX``, a
    skill whose constant record does not read, and a skill or attribute whose profession is neither of
    the two the template names.

    Native logs each refusal through ``Logger``; this port has no logger and answers ``None``, which is
    the answer its caller acts on.
    """

    bits: list[int] = []
    for character in template:
        value = BASE64_TO_VALUE.get(character)
        if value is None:
            return None
        bits.extend((value >> index) & 1 for index in range(6))

    if not bits:
        return None
    end = 6 * len(template)

    cursor = 0
    header, cursor = _read_bits(bits, cursor, 4)
    if header != 0 and header != 14:
        return None
    if header == 14:
        _, cursor = _read_bits(bits, cursor, 4)

    prof_bits, cursor = _read_bits(bits, cursor, 2)
    bits_per_prof = 2 * prof_bits + 4
    prof1, cursor = _read_bits(bits, cursor, bits_per_prof)
    prof2, cursor = _read_bits(bits, cursor, bits_per_prof)
    if (
        prof1 <= PROFESSION_NONE
        or prof2 < PROFESSION_NONE
        or prof1 > PROFESSION_DERVISH
        or prof2 > PROFESSION_DERVISH
    ):
        return None

    result = SkillTemplate()
    attrib_count, cursor = _read_bits(bits, cursor, 4)
    if attrib_count >= TEMPLATE_ATTRIBUTE_COUNT:
        return None

    bits_per_attr, cursor = _read_bits(bits, cursor, 4)
    bits_per_attr += 4
    for index in range(attrib_count):
        attrib_id, cursor = _read_bits(bits, cursor, bits_per_attr)
        attrib_val, cursor = _read_bits(bits, cursor, 4)
        if attrib_id >= ATTRIBUTE_ARRAY_COUNT:
            return None
        if attrib_val > 12:
            return None
        if not attrib_val:
            continue
        owner, is_primary = get_attribute_profession(attrib_id, want_primary=True)
        if owner != prof1 and owner != prof2:
            return None
        if is_primary and owner != prof1:
            return None
        result.attributes[index].attribute = attrib_id
        result.attributes[index].points = attrib_val

    bits_per_skill, cursor = _read_bits(bits, cursor, 4)
    bits_per_skill += 8
    skill_count = 0
    while skill_count < TEMPLATE_SKILL_COUNT:
        if cursor + bits_per_skill > end:
            break
        skill_id, cursor = _read_bits(bits, cursor, bits_per_skill)
        if skill_id > SKILL_MAX:
            return None
        record = _skill_constant_record(skill_id)
        if record is None:
            return None
        if (
            int(record.profession) != PROFESSION_NONE
            and int(record.profession) != prof1
            and int(record.profession) != prof2
        ):
            return None
        result.skills[skill_count] = skill_id
        skill_count += 1

    result.primary = prof1
    result.secondary = prof2
    return result


def _reconcile_professions(template: SkillTemplate, state: object, hero: bool) -> bool:
    """The profession block the two loaders share, up to their own differences.

    ``skillbar_methods.cpp:332-350`` is the player's and ``:393-406`` the hero's. They differ in exactly
    two places, and both are kept: the player asks ``IsProfessionRequired`` before changing its
    secondary and the hero does not, and the player asks ``IsProfessionUnlocked`` first while the hero
    relies on ``ChangeSecondProfession``'s own guard. The hero's change passes hero index ``0``
    because the caller has already resolved the agent this block belongs to.
    """

    if template.primary != PROFESSION_NONE and int(state.primary) != template.primary:
        if is_primary_attribute_required(template, template.primary):
            return False
        if is_profession_required(template, template.primary):
            if is_profession_required(template, template.secondary):
                return False
            template.secondary = template.primary

    if hero:
        if template.secondary != PROFESSION_NONE and int(state.secondary) != template.secondary:
            change_second_profession(template.secondary, 0)
        return True

    if template.secondary != PROFESSION_NONE and is_profession_required(
        template, template.secondary
    ):
        if not state.IsProfessionUnlocked(template.secondary):
            return False
        if int(state.secondary) != template.secondary:
            change_second_profession(template.secondary, 0)
    return True


def load_skill_template(template: str) -> bool:
    """``LoadSkillTemplate`` (``skillbar_methods.cpp:314-355``)."""

    from .map import Map
    from .player import Player

    if int(Map.GetInstanceType()) != INSTANCE_TYPE_OUTPOST:
        return False

    decoded = decode_skill_template(template)
    if decoded is None:
        return False

    agent_id = int(Player.GetAgentID())
    if not agent_id:
        return False

    state = get_agent_profession_state(agent_id)
    if state is None:
        return False
    if not _reconcile_professions(decoded, state, hero=False):
        return False

    load_skillbar(decoded.skills, 0)
    set_attributes(decoded.attributes, 0)
    return True


def load_hero_skill_template(hero_index: int, template: str) -> bool:
    """``LoadSkillTemplate(template, hero_index)`` (``skillbar_methods.cpp:357-411``).

    Hero index ``0`` **is** the player and delegates outright (``:363-364``); the party must hold that
    many heroes (``:382-383``), and the hero must belong to this player —
    ``hero.owner_player_id != me->login_number`` (``:386-387``). The load calls take the hero index.
    """

    from .map import Map
    from .party import Party
    from .player import Player

    if int(Map.GetInstanceType()) != INSTANCE_TYPE_OUTPOST:
        return False
    if int(hero_index) == 0:
        return load_skill_template(template)

    decoded = decode_skill_template(template)
    if decoded is None:
        return False

    info = Party._party()
    if info is None:
        return False
    heroes = list(info.heroes or [])
    if int(hero_index) <= 0 or len(heroes) < int(hero_index):
        return False

    hero = heroes[int(hero_index) - 1]
    if int(hero.owner_player_id) != int(Player.GetLoginNumber()):
        return False

    state = get_agent_profession_state(int(hero.agent_id))
    if state is None:
        return False
    if not _reconcile_professions(decoded, state, hero=True):
        return False

    load_skillbar(decoded.skills, int(hero_index))
    set_attributes(decoded.attributes, int(hero_index))
    return True


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

    def LoadSkillTemplate(self, skill_template: str) -> bool:
        """``PySkillbar::LoadSkillTemplate`` (``skillbar_bindings.cpp:62-64``) → ``GW::skillbar::LoadSkillTemplate``.

        **The declaration here annotated this ``-> None``, and that was a transcription slip**:
        ``skillbar_bindings.cpp:62`` returns ``bool``, the ``.def`` at ``:177-178`` carries no
        return-value policy, so Reforged's Python sees a bool. Corrected in this change; the body
        follows the binding, which is one line over `load_skill_template`.

        ``skillbar_methods.cpp:314-355`` is that function, guard for guard: an outpost instance, a
        template that decodes, a controlled character and its profession state, then the
        primary/secondary reconciliation — with the two ``Is*Required`` questions deciding whether a
        mismatch is fatal or fixable — before ``LoadSkillbar`` and ``SetAttributes`` are handed the
        decoded arrays.
        """

        return load_skill_template(skill_template)

    def LoadHeroSkillTemplate(self, hero_index: int, skill_template: str) -> bool:
        """``PySkillbar::LoadHeroSkillTemplate`` (``skillbar_bindings.cpp:66-68``) → the hero overload.

        ``skillbar_methods.cpp:357-411``, and the same ``-> bool`` correction as `LoadSkillTemplate`
        above (``skillbar_bindings.cpp:66``). The body is `load_hero_skill_template`; see it for the
        hero branch's own guards and for the one place it deliberately differs from the player's.
        """

        return load_hero_skill_template(int(hero_index), skill_template)

    def UseSkill(self, slot: int, target: int = 0) -> bool:
        """``PySkillbar::UseSkill`` (``skillbar_bindings.cpp:70-77``) → ``GW::skillbar::UseSkill``.

        The binding's own order: ``ValidateSlot`` first (``:44-49``, native's ``std::out_of_range``,
        which pybind hands over as the ``IndexError`` this port raises — the same check and the same
        message ``GetSkill`` above carries), then the slot made zero-based, then the call enqueued on
        the game thread. ``game_thread::Enqueue`` runs its callable inline when it is already on that
        thread (``game_thread_methods.cpp:33-45``) and this port's call path **is** the game thread, so
        the body runs here — the same note ``Party.Heroes.UseSkill`` carries in ``py4gw/party.py``.

        ``skillbar_methods.cpp:439-442`` is the body: the target is changed **only** when one was asked
        for and it is not already the client's target, and then the client's own control action is
        pressed — ``ControlAction_UseSkill1`` (``0xA4``) **plus the zero-based slot**, with no ``- 1``
        here because the binding already made it zero-based. ``ui::Keypress`` is this port's
        ``UIManager.Keypress(key, 0)``, which is the sequence ``Party.Heroes.UseSkill`` already drives.

        Two things the source has and this member keeps: the player's previous target is **not** put
        back (unlike the hero member below), and the binding answers ``true`` after the enqueue
        (``:76``) rather than ``ui::Keypress``'s own bool.
        """

        from .player import Player
        from .ui_manager import UIManager

        if slot < _FIRST_SLOT or slot > _LAST_SLOT:
            raise IndexError(
                "Skill slot out of range (must be between 1 and 8) Given: " + str(slot)
            )

        zero_slot = int(slot) - 1
        target_id = int(target)
        if target_id and target_id != Player.GetTargetID():
            Player.ChangeTarget(target_id)

        UIManager.Keypress(int(ControlAction.ControlAction_UseSkill1) + zero_slot, 0)
        return True

    def UseSkillTargetless(self, slot: int) -> bool:
        """``PySkillbar::UseSkillTargetless`` (``skillbar_bindings.cpp:79-86``) → ``PointBlankUseSkill``.

        The same two lines as `UseSkill` — ``ValidateSlot``, then the slot made zero-based and enqueued
        — over ``skillbar_methods.cpp:445-447``, which is the keypress **alone**: no target change, and
        no target to change. Answers ``true`` after the enqueue, as the binding does.
        """

        from .ui_manager import UIManager

        if slot < _FIRST_SLOT or slot > _LAST_SLOT:
            raise IndexError(
                "Skill slot out of range (must be between 1 and 8) Given: " + str(slot)
            )

        zero_slot = int(slot) - 1
        UIManager.Keypress(int(ControlAction.ControlAction_UseSkill1) + zero_slot, 0)
        return True

    def HeroUseSkill(self, target_agent_id: int, skill_number: int, hero_index: int) -> bool:
        """``PySkillbar::HeroUseSkill`` (``skillbar_bindings.cpp:88-115``).

        Native's own order: the skill number made zero-based, the hero number looked up in a **switch**
        of the seven ``ControlAction_Hero{N}Skill1`` bases — anything outside ``1..7`` answers ``false``
        and does nothing — the current target remembered, and then the enqueued body changes the target
        (only if one was asked for and it is not already the target), presses ``hero_action + skill_idx``
        and **puts the previous target back** (only if there was one and the caller's differs from it).

        Two asymmetries the source has and this member keeps: ``skill_number`` is **not** validated —
        only the hero number is, so a slot outside ``1..8`` presses whatever base plus that offset
        lands on — and unlike the player's `UseSkill` above, the hero's previous target *is* restored.

        ``PyParty::UseHeroSkill`` (``party_bindings.cpp:424-447``) is the same body reached through the
        other binding, and ``Party.Heroes.UseSkill`` is its port. The two bindings are separate members
        in the source, so the two members are separate here as well.
        """

        from .player import Player
        from .ui_manager import UIManager

        skill_idx = int(skill_number) - 1
        hero_action = _HERO_SKILL_ACTION_BASE.get(int(hero_index) - 1)
        if hero_action is None:
            return False

        current_target = Player.GetTargetID()
        target_id = int(target_agent_id)
        if target_id and target_id != Player.GetTargetID():
            Player.ChangeTarget(target_id)

        UIManager.Keypress(hero_action + skill_idx, 0)

        if current_target and target_id != current_target:
            Player.ChangeTarget(current_target)
        return True


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
