"""``GwAu3_Data_Party.au3``'s hero, morale, minion and pet-identity accessors, hand-written into the
generated module.

Read from ``tools/gwa3_snippets/`` at generation time by ``tools/generate_gwa3_family.py``, beside
``data_party_my_party.py``: ``data_party.py`` is rewritten whole on every run, so a function written
straight into it would be lost the next time the generator ran.

**What they are.** Four readers from one source file, each over this project's own read of the same
record: ``Party_GetHeroInfo`` (``GwAu3_Data_Party.au3:404-445``) over the world's hero-info array as
`HeroInfoStruct` (`py4gw/context/world_context.py:757`), ``Party_GetMoraleInfo`` (``:202-232``) over the
party-morale links, ``Party_GetControlledMinionsInfo`` (``:340-363``) over the controlled-minion array as
`ControlledMinionsStruct` (``world_context.py:790``), and ``Party_IsPet`` (``:313-315``) over the pet
array `Party_GetPetInfo` already reads in ``data_party_my_party.py``. ``Party_GetPartyContextInfo`` is
**not** redefined here: it is the family's generated accessor.

**One offset disagreement is recorded rather than smoothed over, and it is a stride.** GwAu3 walks the
hero-info array at a ``0x9C`` stride and reads the hero's name at element ``+0x74``; this project's
`HeroInfoStruct` is ``0x78`` bytes, asserted (``world_context.py:2073``), with ``52`` bytes of unknown
``h001C`` and its ``name_encoded_str`` at ``+0x50``. Both layouts are internally consistent -- GwAu3's
name is its record's last field, ending exactly at its stride, and so is this port's -- so the two
sources write different sizes for one record and a name at two offsets (``+0x74`` against ``+0x50``).
Every other offset GwAu3 reads for this record agrees with a named field of the port's (``+0x0``
`hero_id`, ``+0x4`` `agent_id`, ``+0x8`` `level`, ``+0xC`` `primary`, ``+0x10`` `secondary`, ``+0x14``
`hero_file_id`, ``+0x18`` `model_file_id`), which is why the keys are routed and the divergence is
written on the one key it touches: ``Name`` answers the port's own `name_str` of its own record rather
than reading ``+0x74`` under a field this port names at ``+0x50``.

**The morale word agrees exactly.** GwAu3's morale read ends at a fixed ``+0x18`` inside the record it
hashes the agent id into, and this project's `PartyMemberMoraleInfoStruct.morale` sits at ``+0x18`` too
(``agent_id``, its dupe, four unknown words, then ``morale``; ``world_context.py:797-806``).
"""


def Party_GetMoraleInfo(agent_id: Any = -2, info: str = "") -> Any:
    """One field of one agent's **morale** record (``GwAu3_Data_Party.au3:202-232``).

    GwAu3 converts the id first (``:203``, so ``-2`` is the controlled character), indexes its morale
    array with the id and reads one word; a record it cannot resolve answers ``0`` before the switch
    (``:214``), and its ``Case Else`` answers ``0`` for an unrecognised key (``:229-230``) -- an empty
    key included, which is why the empty key is **not** guarded first here, unlike the source's other
    accessors. ``Morale`` is that word less ``100`` and the four flag keys are comparisons on the raw
    word (``>= 110``, ``<= 40``, ``> 100``, ``< 100``), each answered as the source's own boolean.

    This walks `Party.GetPartyMorale` (`py4gw/party.py:1024-1047`) -- the port's read of the same
    links-and-records chain, whose word is this record's own ``morale`` -- and takes the pair whose
    agent id matches. GwAu3 hashes the id; this scans a list, the same fact answered the port's way. The
    port's member also skips entries whose agent id does not resolve as a live agent
    (``Party.GetPartyMorale``'s own guard), so an id GwAu3 would still index answers ``0`` here.
    """

    from ..party import Party
    from .data_agent import Agent_ConvertID

    resolved = int(Agent_ConvertID(agent_id))

    raw = None
    for member_agent_id, morale in Party.GetPartyMorale():
        if int(member_agent_id) == resolved:
            raw = int(morale)
            break

    if raw is None:
        return 0

    if info == "Morale":
        return raw - 100
    if info == "RawMorale":
        return raw
    if info == "IsMaxMorale":
        return raw >= 110
    if info == "IsMinMorale":
        return raw <= 40
    if info == "IsMoraleBoost":
        return raw > 100
    if info == "IsMoralePenalty":
        return raw < 100

    return 0


def Party_IsPet(agent_id: Any) -> Any:
    """Whether an agent is a charmed pet (``GwAu3_Data_Party.au3:313-315``).

    GwAu3's whole body is ``Party_GetPetNumberByAgentID($a_v_AgentID) <> 0``, and that helper's own
    chain is reproduced here in its order (``:318-329``): the id is converted (``:319``), a zero id
    answers ``0`` -- hence ``False`` -- before anything is read (``:320``), a non-positive pet-array
    size answers ``0`` (``:322-323``), and the array is walked from **one** to the count asking
    `Party_GetPetInfo` for each pet's ``AgentID`` (``:325-327``). The walk is the port's own
    `Party_GetPetInfo` from the same generated module, which reads the same `PetInfoStruct` array at the
    same ``0x1C`` stride, so the comparison is the source's comparison. A pet number is never returned,
    only the boolean the source's ``<> 0`` produces.
    """

    from ..client import require_client
    from .data_agent import Agent_ConvertID

    resolved = int(Agent_ConvertID(agent_id))
    if resolved == 0:
        return False

    world = require_client().read_world_context()
    if world is None:
        return False

    count = int(world.pets_array.m_size)
    if count <= 0:
        return False

    for number in range(1, count + 1):
        if Party_GetPetInfo(number, "AgentID") == resolved:
            return True

    return False


def Party_GetControlledMinionsInfo(agent_id: Any = 0, info: str = "") -> Any:
    """One field of one agent's **controlled-minion** record (``GwAu3_Data_Party.au3:340-363``).

    GwAu3 takes the world's controlled-minion array and its size, walks it at a ``0x8`` stride --
    `ControlledMinionsStruct`'s own size, asserted (``world_context.py:2074``) -- and matches the first
    element whose first word is ``Agent_ConvertID($a_v_AgentID)`` (``:345-351``); no match answers ``0``
    (``:353``), and its ``Case Else`` answers ``0`` for an unrecognised or empty key (``:360-361``).
    Both keys of the record are the port's own named fields: ``AgentID`` is ``+0x0`` `agent_id` and
    ``MinionCount`` is ``+0x4`` `minion_count``.

    One detail is a source quirk rather than reproduced: GwAu3's loop runs ``For $l_i_Idx = 0 To
    $l_i_Size``, one element past the array it was told the size of, and this reads the port's own
    `controlled_minions` property, which is the array's ``m_size`` elements and no more. The answers for
    every index the array actually holds are the same.
    """

    from ..client import require_client
    from .data_agent import Agent_ConvertID

    world = require_client().read_world_context()
    if world is None:
        return 0

    records = world.controlled_minions
    if records is None:
        return 0

    resolved = int(Agent_ConvertID(agent_id))

    for record in records:
        if int(record.agent_id) != resolved:
            continue

        if info == "AgentID":
            return int(record.agent_id)
        if info == "MinionCount":
            return int(record.minion_count)

        return 0

    return 0


def Party_GetHeroInfo(hero_number: Any = 1, info: str = "") -> Any:
    """One field of one **hero's** information record (``GwAu3_Data_Party.au3:404-445``).

    GwAu3 takes the world's hero-info array and its size, guards the number, asks the party for that
    hero's ``AgentID``, and then walks the array matching that id at ``+0x4`` (``:405-418``); this
    project holds the same array as `WorldContextStruct.hero_info`
    (`py4gw/context/world_context.py:1831`) and asks the same question of the same accessor,
    `Party_GetMyPartyHeroInfo(hero_number, "AgentID")` (``data_party_my_party.py``), so the id compared
    is the party's own answer.

    GwAu3's guard order and its own bounds are kept: ``$a_i_HeroNumber < 1`` or ``>=`` the array's size
    answers ``0`` (``:407``, **strictly** greater-or-equal, unlike `Party_GetHeroFlagInfo`'s ``>``), a
    hero whose agent id is ``0`` answers ``0`` (``:410``), and no element matching that id answers ``0``
    (``:418``). There is no empty-key guard before the walk: an empty key reaches the matched element
    and falls out of the ``Switch`` to the source's own ``Return 0`` (``:444``).

    Seven keys are the record's own named fields, by offset. ``Name`` is the one key whose reading
    differs, two ways, and both are recorded rather than hidden: this project's `HeroInfoStruct` names
    the hero's twenty wide characters at ``+0x50`` while GwAu3 reads ``+0x74`` under a ``0x9C`` stride
    against this record's asserted ``0x78`` (see this file's header), so the key answers the port's own
    `name_str` of its own record; and for a hero id outside GwAu3's ``28..35`` band the source falls
    back to its global ``$GC_AM2_HERO_DATA`` table (``:441``), where this calls
    `Party.Heroes.GetHeroNameById` (`py4gw/party.py:1477`) -- the port's own name-by-id member, which
    the port's doc records as answering ``""`` because Native's `Hero::GetName` reads a field no
    constructor sets. Same shape, same argument, the port's own answer.
    """

    from ..client import require_client
    from ..party import Party

    world = require_client().read_world_context()
    if world is None:
        return 0

    heroes = world.hero_info
    if heroes is None:
        return 0

    size = int(world.hero_info_array.m_size)
    if int(hero_number) < 1 or int(hero_number) >= size:
        return 0

    hero_agent_id = Party_GetMyPartyHeroInfo(hero_number, "AgentID")
    if hero_agent_id == 0:
        return 0

    for hero in heroes:
        if int(hero.agent_id) != int(hero_agent_id):
            continue

        if info == "HeroID":
            return int(hero.hero_id)
        if info == "AgentID":
            return int(hero.agent_id)
        if info == "Level":
            return int(hero.level)
        if info == "Primary":
            return int(hero.primary)
        if info == "Secondary":
            return int(hero.secondary)
        if info == "HeroFileID":
            return int(hero.hero_file_id)
        if info == "ModelFileID":
            return int(hero.model_file_id)

        if info == "Name":
            hero_id = int(hero.hero_id)
            if 28 <= hero_id <= 35:
                name = hero.name_str
                if name != "":
                    return name
            return Party.Heroes.GetHeroNameById(hero_id)

        return 0

    return 0
