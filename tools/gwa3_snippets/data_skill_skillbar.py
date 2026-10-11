"""``GwAu3_Data_Skill.au3``'s **skillbar** reader, hand-written into the generated module.

Read from ``tools/gwa3_snippets/`` at generation time, the same mechanism `data_party`'s member
accessors and the item resolvers use: ``data_skill.py`` is rewritten whole on every run.

**What it is, and why the whole engine wanted it.** ``Skill_GetSkillbarInfo``
(``GwAu3_Data_Skill.au3:210-304``) is how every part of UtilityAI learns what is on a skillbar: the slot
loop in `UAI_UseSkills` asks it for a slot's ``SkillID``, `Skill_GetSlotByID` and `Skill_CheckSlotByID`
walk it, and the static skill cache is built from it. It is a stride walk over the **world's** skillbar
array -- ``0xBC`` bytes per skillbar, ``0x14`` per slot -- matching a skillbar's agent id against the
player's own or a hero's.

**The port's structures are the same two strides**, so the walk is this project's own read:
`SkillbarStruct` is ``0xBC`` and `SkillbarSkillStruct` is ``0x14``
(`py4gw/context/world_context.py:1059-1093`, with ``assert ctypes.sizeof(...)`` for both), reached
through `WorldContextStruct.skillbars`. Every offset GwAu3 reads has a name there: ``+0x0`` `agent_id`,
``+0xA4`` `disabled`, the casting word ``+0xB0`` is the cast array's ``m_size``, ``+0x8``/``+0xC``/
``+0x10``/``+0x14`` of a slot are its two adrenaline words, its recharge timestamp and its skill id.

**The recharge timer is routed too, and it is the same number.** GwAu3's `Skill_GetSkillTimer` is
``GetTickCount() + $g_i_GWExeStart`` masked to 32 bits (``:11-14``); this project's
``client.memory_manager.GetSkillTimer()`` is the same sum (``py4gw/memory/memory_manager.py``, the
client global the catalog names ``memory.skill_timer_ptr``), which is why the two recharge keys answer
rather than refuse. The subtraction wraps as ``uint32`` in both.
"""

def _signed(value: int) -> int:
    """``Utils_MakeInt32``: the same 32-bit word read as a signed integer (`:276-277`).

    The source converts *both* timestamps before it subtracts, because the client stores them unsigned
    and the wrap is what makes a recharge that has already elapsed come out negative rather than huge.
    """

    value &= 0xFFFFFFFF
    return value - 0x100000000 if value >= 0x80000000 else value


def Skill_GetSkillTimer() -> int:
    """The client's own skill timer (``GwAu3_Data_Skill.au3:11-14``).

    ``BitAND(GetTickCount() + $g_i_GWExeStart, 0xFFFFFFFF)`` -- the tick count offset by the client's
    start, which is the value a skillbar slot's recharge timestamp is measured against. This project
    reads the same sum through the connection (`client.memory_manager.GetSkillTimer`), so the two
    recharge keys below are the source's own arithmetic over the source's own clock.
    """

    return int(require_client().memory_manager.GetSkillTimer())


def _skillbar(world: Any, hero_number: Any) -> Any:
    """The skillbar GwAu3's stride walk finds, or ``None``.

    The match is on the record's first word -- the skillbar's **agent id** -- against the player's own
    id (``$a_i_HeroNumber = 0``) or the numbered hero's, exactly as ``:220-231`` does it. ``None`` is
    GwAu3's own no-match answer (``:231`` returns ``0``), and so is a zero id (``:226``).
    """

    skillbars = world.skillbars
    if skillbars is None:
        return None

    if hero_number != 0:
        wanted = Party_GetMyPartyHeroInfo(hero_number, "AgentID")
    else:
        wanted = Agent_GetMyID()

    if wanted == 0:
        return None

    for skillbar in skillbars:
        if int(skillbar.agent_id) == int(wanted):
            return skillbar
    return None


def Skill_GetSkillbarInfo(skill_slot: Any = 1, info: str = "", hero_number: Any = 0) -> Any:
    """One field of one skillbar slot, on the player's bar or a hero's
    (``GwAu3_Data_Skill.au3:210-304``).

    GwAu3's guards, in its order: a bar array the client does not hold, a hero number outside it, a
    slot number outside ``1..8``, and an agent id of ``0`` all answer ``0`` (``:214-226``); a walk that
    matches nothing answers ``0`` (``:231``); and an unrecognised key answers ``0`` -- its ``Case Else``.

    **Two key names are GwAu3's and answer a word the port names differently**, and both are recorded
    rather than glossed: ``h00A8[2]`` and ``h00B4[2]`` are the *first* and *fourth* words of the
    cast-array header at ``+0xA8`` -- the port's `cast_array` ``m_buffer`` and ``m_param`` -- and
    ``Casting`` is the third word, ``m_size``: "is a skill in flight" is "the cast array is not empty".
    A caller that wants the queued skill itself wants `cast_array`'s elements, which this key does not
    answer.

    ``SlotBySkillID`` and ``HasSkillID`` are the source's own reversals: both take a **skill id in the
    slot parameter**. **And both are unreachable with a real skill id, because the guard above the
    ``Switch`` rejects anything outside ``1..8`` (``:217``) before the ``Case`` is reached** -- so with
    a skill id they answer ``0``, in GwAu3 exactly as here. The port keeps the guard and the order, so
    its answer is the source's; the workaround a caller wants is `UAI_GetSkillbarInfo`'s sibling in the
    plugin, which looks a slot up by walking the eight ids itself.
    """

    world = require_client().read_world_context()
    if world is None:
        return 0

    size = int(world.party_skillbar_array.m_size)
    if hero_number < 0 or hero_number >= size:
        return 0
    if skill_slot < 1 or skill_slot > 8:
        return 0

    skillbar = _skillbar(world, hero_number)
    if skillbar is None:
        return 0

    if info == "AgentID":
        return int(skillbar.agent_id)
    if info == "Disabled":
        return int(skillbar.disabled)
    if info == "Casting":
        return int(skillbar.cast_array.m_size)
    if info == "h00A8[2]":
        return int(skillbar.cast_array.m_buffer)
    if info == "h00B4[2]":
        return int(skillbar.cast_array.m_param)
    if info == "Queued":
        return int(skillbar.h00B8)

    slot = skillbar.skills[int(skill_slot) - 1]

    # Each slot key names its field literally. A table keyed by the GwAu3 name would reach the field
    # dynamically, which this project's porting rules forbid -- and the four names are GwAu3's own key
    # strings beside the port's field names, which is the mapping a reader wants to see anyway.
    if info == "SkillID":
        return int(slot.skill_id)
    if info == "Adrenaline":
        return int(slot.adrenaline_a)
    if info == "AdrenalineB":
        return int(slot.adrenaline_b)
    if info == "Event":
        return int(slot.event)

    if info == "IsRecharged":
        timestamp = int(slot.recharge)
        if timestamp == 0:
            return True
        return (timestamp - Skill_GetSkillTimer()) == 0

    if info == "RechargeTime":
        # `Utils_MakeInt32` on both sides (`:276-279`): the timestamps are unsigned words in the client
        # and the subtraction is signed in the source, then clamped at zero. `_signed` is that
        # conversion -- the same one the source's helper makes -- so the comparison is the source's.
        timestamp = int(slot.recharge)
        if timestamp == 0:
            return 0

        remaining = _signed(timestamp) - _signed(Skill_GetSkillTimer())
        if remaining <= 0:
            return 0
        return remaining

    if info == "HasSkill":
        return int(slot.skill_id) != 0

    if info == "SlotBySkillID":
        for index in range(8):
            if int(skillbar.skills[index].skill_id) == int(skill_slot):
                return index + 1
        return 0

    if info == "HasSkillID":
        for index in range(8):
            if int(skillbar.skills[index].skill_id) == int(skill_slot):
                return True
        return False

    return 0
