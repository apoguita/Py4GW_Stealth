"""``GwAu3_Data_Party.au3``'s party-**member** accessors, hand-written into the generated module.

Read from ``tools/gwa3_snippets/`` at generation time by ``tools/generate_gwa3_family.py``, the same
mechanism the item resolvers use: ``data_party.py`` is rewritten whole on every run, so a function
written straight into it would be lost the next time the generator ran.

**Why these exist now, and why they are the piece the engine needed.** The UtilityAI combat engine's
party layer (`API/Plugins/UtilityAI/Core/UtilityAI_Utils.au3:29-140`) reaches four of these accessors --
`Party_GetMyPartyInfo`, `Party_GetMyPartyHeroInfo`, `Party_GetMyPartyPlayerMemberInfo` and
`Party_GetHeroFlagInfo` -- and this file refused the fields behind them until now because it read only
the **context** record: ``PlayerCount``, ``HenchmenCount``, ``HeroCount``, ``OtherCount`` and
``PlayerPartyID`` are second-level reads through ``player_party_ptr``, and the refusal said so.

**The pointer is followed here, and the reading is the port's own.** `PartyContextStruct.player_party`
(`py4gw/context/party_context.py:357-367`) resolves that pointer and answers a **bound**
`PartyInfoStruct`, whose `players`/`heroes`/`henchmen`/`others` properties read the member arrays. The
strides agree exactly with GwAu3's own: `PlayerPartyMember` is ``0x0C``, `HeroPartyMember` ``0x18``,
`HenchmanPartyMember` ``0x34`` -- the same numbers GwAu3 multiplies by -- and the field names are the
same fields, so a count is read from the array's own ``m_size`` and a member's field from the member record,
not from a hand-kept offset.

**Two things are still refused, and each names its own reason** rather than sharing one: the four
``Array*PartyMember`` keys, which answer a **client address** GwAu3's callers only use to walk the array
with a stride -- a caller here wants the members, and `Party.GetPlayers()`/`GetHeroes()` answer them --
and `Party_GetHeroFlagInfo`, which reads the *world's* hero-flag array
(``World_GetWorldInfo("HeroFlagArray")``), a record this layer holds as a field and does not yet read the
elements of.
"""

#: The four keys of `Party_GetMyPartyInfo` that answer a **client address** (`GwAu3_Data_Party.au3:76-94`).
#: Each names the array whose members the caller wants, and the ported property that answers them.
_MEMBER_ARRAY_POINTERS: dict[str, str] = {
    "ArrayPlayerPartyMember": "PartyInfoStruct.players",
    "ArrayHenchmanPartyMember": "PartyInfoStruct.henchmen",
    "ArrayHeroPartyMember": "PartyInfoStruct.heroes",
    "ArrayOthersPartyMember": "PartyInfoStruct.others",
}


def _party(record: Any) -> Any:
    """The player's own party record: ``player_party_ptr`` followed, as GwAu3 does at every level.

    GwAu3 reads ``Memory_Read($l_p_PartyPtr + offset, type)`` where ``$l_p_PartyPtr`` is
    ``Party_GetPartyContextInfo("MyPartyPtr")`` -- the context's ``+0x54``. This project's context names
    that field `player_party_ptr` and its `player_party` property performs the same follow, answering a
    record bound to the same reader so the member arrays can be read from it. ``None`` when the pointer is
    zero, which is GwAu3's own "no party" case and answers ``0`` at every caller below.
    """

    return record.player_party


def Party_GetPartyContextPtr() -> Any:
    """The party context record (``GwAu3_Data_Party.au3:4-8``).

    GwAu3 resolves ``BasePointer[0][0x18][0x4C]`` with its own ``Memory_ReadPtr`` and answers that
    client *address*; this answers **the record** that slot holds, read through this project's own
    member: `py4gw.client.ConnectedClient.read_party_context` (``py4gw/client.py:1500``) over
    `PartyContextStruct` (`py4gw/context/party_context.py:257`) -- the record this file's readers and the
    family accessor `Party_GetPartyContextInfo` both read, and the ``0x4C`` is that structure's own
    offset in the game context (`GameContextStruct.party_context`,
    `py4gw/context/game_context.py:49`). GwAu3's own caller tests it for zero
    (``Party_GetPartyContextInfo``, ``:11``); ``0`` here is that same answer for a context the client
    does not hold.

    **The divergence, in one sentence:** GwAu3 hands back a client address and this hands back the record
    that address holds, the substitution `World_GetWorldContextPtr` (`py4gw/gwa3/data_world.py:429`) and
    `Agent_GetAgentPtr` already record.
    """

    context = require_client().read_party_context()
    return 0 if context is None else context


def Party_GetMyPartyInfo(info: str = "") -> Any:
    """One field of the **player's own party** record (``GwAu3_Data_Party.au3:69-98``).

    GwAu3's guard order is kept: an empty key answers ``0``, a party the client does not hold answers
    ``0``, and an unrecognised key answers ``0`` -- its ``Switch`` has no ``Case Else`` and falls through
    to the same ``Return 0``. The five scalar keys are answered from the party record's own fields; the
    four that answer a client address refuse, each naming the property that answers what a caller wants
    from it.
    """

    if info == "":
        return 0

    party = _party(require_client().read_party_context())
    if party is None:
        return 0

    if info == "PartyID":
        return int(party.party_id)
    if info == "ArrayPlayerPartyMemberSize":
        return int(party.players_array.m_size)
    if info == "ArrayHenchmanPartyMemberSize":
        return int(party.henchmen_array.m_size)
    if info == "ArrayHeroPartyMemberSize":
        return int(party.heroes_array.m_size)
    if info == "ArrayOthersPartyMemberSize":
        return int(party.others_array.m_size)

    if info in _MEMBER_ARRAY_POINTERS:
        raise NotImplementedError(
            f"`{info}` (GwAu3_Data_Party.au3:76-94) returns the client **address** of a member array. "
            "GwAu3's own callers use it for one thing -- to walk the array by hand with a stride "
            "(`0xC`, `0x18`, `0x34`) -- and a caller here wants the members, not the address: "
            f"`{_MEMBER_ARRAY_POINTERS[info]}` (`py4gw/context/party_context.py:147-170`) answers them "
            "as values. `MyPartyPtr`, the same shape on the context record, is refused for the same "
            "reason."
        )

    return 0


def Party_GetMyPartyPlayerMemberInfo(party_member_number: Any = 1, info: str = "") -> Any:
    """One field of one **player** party member (``GwAu3_Data_Party.au3:100-129``).

    ``$a_i_PartyMemberNumber`` is **one-based** in GwAu3 and the source converts it with
    ``$a_i_PartyMemberNumber - 1`` before its bounds test (``:103``), so ``0`` and the size itself are
    both out of range and answer ``0`` -- the same guard, in the same order, with the same ``0``.
    ``State`` is the record's own word and the two flag keys are its two bits, which the port's
    `PlayerPartyMember` already exposes as `is_connected`/`is_ticked`
    (``py4gw/context/party_context.py:69-79``, the same ``& 1`` and ``& 2``).
    """

    number = int(party_member_number) - 1

    party = _party(require_client().read_party_context())
    if party is None:
        return 0

    size = int(party.players_array.m_size)
    if number < 0 or number >= size:
        return 0

    if info == "":
        return 0

    member = party.players[number]

    if info == "LoginNumber":
        return int(member.login_number)
    if info == "CalledTargetID":
        return int(member.called_target_id)
    if info == "State":
        return int(member.state)
    if info == "IsConnected":
        return member.is_connected
    if info == "IsTicked":
        return member.is_ticked

    return 0


def Party_GetMyPartyHeroInfo(
    hero_number: Any = 1, info: str = "", include_other_hero_players: Any = False
) -> Any:
    """One field of one **hero** party member (``GwAu3_Data_Party.au3:131-177``).

    **The hero array is party-wide and GwAu3 filters it to the player's own heroes**, which is what
    ``$a_b_IncludeOtherHeroPlayers`` switches: with it false (the default) the source walks the array,
    keeps the entries whose ``+0x4`` owner equals ``Map_GetCharacterInfo("PlayerNumber")``, and takes the
    ``$a_i_HeroNumber``-th match (``:141-159``). That count is per *player*, not per party, and it is why
    ``Party_GetMyPartyHeroInfo(1, "AgentID")`` is "my first hero" while ``$a_b_IncludeOtherHeroPlayers``
    makes ``1`` mean the array's first entry of any player.

    **One substitution is recorded rather than hidden.** The owner test needs the controlled character's
    player number, and GwAu3 asks `Map_GetCharacterInfo("PlayerNumber")` -- a member this layer does not
    have. The same number is the player agent's ``PlayerNumber`` column, which is routed
    (`py4gw/gwa3/data_agent.py`, live-verified), so it is read from there. Same fact, same comparison;
    `Map_GetCharacterInfo` is the ported member that would make it identical, and until then this is the
    one line of this accessor that answers from a different source than the source's.

    The guard is GwAu3's own and so is its direction: ``$a_i_HeroNumber < 1`` or beyond the array size
    answers ``0`` (``:135``) -- **one-based**, unlike the player accessor's after-subtraction test -- and
    a number with no matching hero answers ``0`` (``:159``).
    """

    party = _party(require_client().read_party_context())
    if party is None:
        return 0

    size = int(party.heroes_array.m_size)
    if int(hero_number) < 1 or int(hero_number) > size:
        return 0

    if info == "":
        return 0

    heroes = party.heroes

    if include_other_hero_players:
        member = heroes[int(hero_number) - 1]
    else:
        mine = int(Agent_GetAgentInfo(-2, "PlayerNumber"))
        if mine == 0:
            return 0
        matched = 0
        member = None
        for candidate in heroes:
            if int(candidate.owner_player_id) == mine:
                matched += 1
                if matched == int(hero_number):
                    member = candidate
                    break
        if member is None:
            return 0

    if info == "AgentID":
        return int(member.agent_id)
    if info == "OwnerPlayerNumber":
        return int(member.owner_player_id)
    if info == "HeroID":
        return int(member.hero_id)
    if info == "Level":
        return int(member.level)

    return 0


def Party_GetMyPartyHenchmanInfo(henchman_number: Any = 1, info: str = "") -> Any:
    """One field of one **henchman** party member (``GwAu3_Data_Party.au3:179-203``).

    The player accessor's shape with the henchman array and its own stride (``0x34``, which is
    `HenchmanPartyMember`'s size exactly). Two offsets in the source -- ``+0x2C`` for the profession and
    ``+0x30`` for the level -- are the port's named fields, and the profession is a plain integer here
    where `py4gw/gwa3/uai_utils.py`'s `UAI_GetAgentProfession` answers a mob's by class.
    """

    number = int(henchman_number) - 1

    party = _party(require_client().read_party_context())
    if party is None:
        return 0

    size = int(party.henchmen_array.m_size)
    if number < 0 or number >= size:
        return 0

    if info == "":
        return 0

    member = party.henchmen[number]

    if info == "AgentID":
        return int(member.agent_id)
    if info == "Profession":
        return int(member.profession)
    if info == "Level":
        return int(member.level)

    return 0


def Party_GetPetInfo(pet_number: Any = 1, info: str = "") -> Any:
    """One field of one **pet** record (``GwAu3_Data_Party.au3:267-305``).

    The third world array in this file, after the skillbars and the hero flags: GwAu3 takes
    ``World_GetWorldInfo("PetInfoArray")`` and its size and walks it at a ``0x1C`` stride, which is
    `PetInfoStruct`'s own size exactly (``assert ctypes.sizeof(PetInfoStruct) == 0x1C``,
    `py4gw/context/world_context.py:952-966`). Every offset GwAu3 reads has a name there: ``+0x0``
    `agent_id`, ``+0x4`` `owner_agent_id`, ``+0x8`` `pet_name_ptr`, ``+0xC``/``+0x10`` the two model file
    ids, ``+0x14`` `behavior` and ``+0x18`` `locked_target_id` -- and `behavior` is what the four
    behaviour keys compare (`0` fighting, `1` guarding, `2` avoiding), each an equality in the source and
    each an equality here.

    GwAu3's guards in its order: a pet number outside the array answers ``0`` (the source subtracts one
    first, ``:270``), and an empty key answers ``0`` before anything is read (``:274``).

    **The two name keys are routed, and each keeps the source's own guard.** ``PetNameEnc`` answers the
    *encoded* string and ``PetName`` the display-safe one -- the port's `PetInfoStruct` exposes both
    (`pet_name_encoded_str`, `pet_name_str`) -- and both first test the name pointer for the sentinel
    GwAu3 tests: below ``0x10000`` it answers ``""`` for the encoded form and ``"Unknown"`` for the
    display one (``:285``, ``:289``), which are the source's two different answers to the same missing
    pointer.
    """

    world = require_client().read_world_context()
    if world is None:
        return 0

    pets = world.pets
    if pets is None:
        return 0

    number = int(pet_number) - 1
    if number < 0 or number >= int(world.pets_array.m_size):
        return 0
    if info == "":
        return 0

    pet = pets[number]
    name_ptr = int(pet.pet_name_ptr)

    if info == "AgentID":
        return int(pet.agent_id)
    if info == "OwnerAgentID":
        return int(pet.owner_agent_id)
    if info == "PetNamePtr":
        return name_ptr
    if info == "PetNameEnc":
        if name_ptr <= 0x10000:
            return ""
        return pet.pet_name_encoded_str
    if info == "PetName":
        if name_ptr <= 0x10000:
            return "Unknown"
        return pet.pet_name_str
    if info == "ModelFileID1":
        return int(pet.model_file_id1)
    if info == "ModelFileID2":
        return int(pet.model_file_id2)
    if info == "Behavior":
        return int(pet.behavior)
    if info == "LockedTargetID":
        return int(pet.locked_target_id)

    behavior = int(pet.behavior)
    if info == "IsFighting":
        return behavior == 0
    if info == "IsGuarding":
        return behavior == 1
    if info == "IsAvoiding":
        return behavior == 2
    if info == "HasLockedTarget":
        return int(pet.locked_target_id) != 0

    return 0


def Party_GetHeroFlagInfo(hero_number: Any = 1, info: str = "") -> Any:
    """One field of one hero's **flag record** (``GwAu3_Data_Party.au3:368-402``).

    GwAu3 does not read the hero's flag from the party at all: it takes the **world's** hero-flag array
    (``World_GetWorldInfo("HeroFlagArray")`` and its size), asks the party for the ``AgentID`` of the
    numbered hero, and then walks the array matching that id at a ``0x24`` stride (``:375-384``). This
    project holds the same array as a field -- `WorldContextStruct.hero_flags`, a list of
    `HeroFlagStruct` whose size is ``0x24`` exactly (`py4gw/context/world_context.py:1825-1828`;
    ``assert ctypes.sizeof(HeroFlagStruct) == 0x24``) -- so the walk is the port's own read of the same
    elements, and the guard order is the source's: no array, or a hero number outside it, answers ``0``;
    a hero whose agent id is ``0`` answers ``0``; and no element matching that agent id answers ``0``.

    **Two of the source's key names are read from the port's differently-named fields, and that is
    recorded rather than glossed.** GwAu3's ``InventoryID`` is the dword at ``+0x8``, which this
    project's structure names ``level``; GwAu3's ``Behavior`` is ``+0xC``, which the port names
    ``hero_behavior``. Same offsets, same words -- the *names* differ because the port reproduces
    Reforged's spelling of the record while the key names are GwAu3's. ``FlagX``/``FlagY`` are the two
    floats of the record's ``Vec2f`` at ``+0x10``/``+0x14``, read raw rather than through the port's
    ``flag`` property, because GwAu3 reads the words and the property answers ``None`` for a
    non-finite pair.
    """

    world = require_client().read_world_context()
    if world is None:
        return 0

    flags = world.hero_flags
    if flags is None:
        return 0

    size = int(world.hero_flags_array.m_size)
    if int(hero_number) < 1 or int(hero_number) > size:
        return 0

    hero_agent_id = Party_GetMyPartyHeroInfo(hero_number, "AgentID")
    if hero_agent_id == 0:
        return 0

    for flag in flags:
        if int(flag.agent_id) != int(hero_agent_id):
            continue

        if info == "HeroID":
            return int(flag.hero_id)
        if info == "AgentID":
            return int(flag.agent_id)
        if info == "InventoryID":
            return int(flag.level)
        if info == "Behavior":
            return int(flag.hero_behavior)
        if info == "FlagX":
            return float(flag.flag_ptr.x)
        if info == "FlagY":
            return float(flag.flag_ptr.y)

        if info == "LockedTargetID":
            # **The one key whose offsets disagree, and it refuses where the source would read.**
            # ``GwAu3_Data_Party.au3:398`` answers it from the element's ``+0x20``; this project's
            # `HeroFlagStruct` names ``+0x1C`` `locked_target_id` and leaves ``+0x20`` as the placeholder
            # `h0020`. Two offsets for one field in one 0x24 record, and neither source establishes which
            # word the client writes: reading ``+0x20`` would be GwAu3's offset under a field this port
            # calls unknown, and reading `locked_target_id` would be a different offset under GwAu3's key
            # name. The refusal sits exactly where the source's `Case` does -- inside the matched element
            # -- so a hero number that matches nothing still answers `0`, as GwAu3 does. It is the
            # owner's to settle, with the `Friend` family's offsets and the model-state columns.
            raise NotImplementedError(
                "GwAu3_Data_Party.au3:398 reads `LockedTargetID` at flag element ``+0x20``, while "
                "`py4gw/context/world_context.py:717-739` names ``+0x1C`` `locked_target_id` and leaves "
                "``+0x20`` as `h0020`. Which word the client writes is not established by reading either "
                "source, so the key refuses rather than answer one offset under the other's name. The "
                "record's other six keys are routed, because their offsets agree."
            )

        return 0

    return 0
