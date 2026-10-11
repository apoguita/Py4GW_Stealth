"""GwAu3's `Party_GetPartyContextInfo`, over the record this project already reads.
**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_family.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

GwAu3's party-**context** reader -- flags, invitation counts and the pointer to the player's own party. This project reads the same record as `PartyContextStruct`.

The context points at a second record (`player_party_ptr` at ``+0x54``) which holds the member counts and arrays, and GwAu3 reads through that pointer for `PlayerCount`, `HenchmenCount`, `HeroCount`, `OtherCount` and `PlayerPartyID`. **This layer follows it** (`PartyContextStruct.player_party`, `py4gw/context/party_context.py:357-367`, a bound `PartyInfoStruct`), so those five keys answer from the party record's own fields -- the array's ``m_size`` for a count, ``party_id`` for the id.

The file's **member** accessors are carried as a snippet (`tools/gwa3_snippets/data_party_my_party.py`): `Party_GetMyPartyInfo`, `Party_GetMyPartyPlayerMemberInfo`, `Party_GetMyPartyHeroInfo` and `Party_GetMyPartyHenchmanInfo` over the port's `PlayerPartyMember` (``0xC``), `HeroPartyMember` (``0x18``) and `HenchmanPartyMember` (``0x34``) -- the same strides GwAu3 multiplies by -- while `Party_GetHeroFlagInfo` refuses, naming the world array whose elements it needs. The four ``Array*PartyMember`` keys still refuse: they answer a client *address*, and `MyPartyPtr` with them.

`Party_GetPartyContextInfo` is one ``Switch`` over 14 keys in GwAu3
(``GwAu3_Data_Party.au3``). 7 of the 14 field keys resolve to a **named
attribute** of the structure this project reads, chosen by offset against ctypes' own view of the
record. The reader for each key names its attribute literally, so nothing here reaches a field through
a dynamic name.

**The return shapes are GwAu3's.** An unknown field name answers ``0`` and a record that cannot be
resolved answers ``0`` -- AutoIt has no exceptions in this role and a script branches on the return.
A key this layer cannot answer **raises**, naming what it needs, rather than answering a wrong value
of the right type, which a caller could not detect.
"""

from __future__ import annotations

import struct

from typing import Any

from ..client import require_client
from ..context import PartyContextStruct
from .data_agent import Agent_GetAgentInfo
_UNIMPLEMENTED: dict[str, str] = {'MyPartyPtr': "GwAu3_Data_Party.au3:35-36 returns the client address held at context ``+0x54``. This project's structure names that field `player_party_ptr` (`py4gw/context/party_context.py:257`), and a client address is of no use to a caller here -- the same shape difference `Agent_GetAgentPtr` records. Its `player_party` property (`py4gw/context/party_context.py:357-367`) is what follows it, and `Party_GetMyPartyInfo` (the next accessor in this file) is what a caller wants."}

_COMPUTED: frozenset[str] = frozenset(['HenchmenCount', 'HeroCount', 'OtherCount', 'PlayerCount', 'PlayerPartyID', 'TotalPartySize'])

# A text key takes the id as well as the record, because its handshake is keyed by the id.

# Keys that answer `False` rather than `0` when no record matches, because GwAu3's own guard does.
_FALSE_ON_MISSING: frozenset[str] = frozenset([])


def _read_text(request: Any, ready: Any, get: Any, record_id: Any) -> str:
    """Run this project's name-decode handshake and answer the text it produces.

    **A decode is not a read, and this is the whole of that difference.** The port's name getters
    answer `""` until a request has been made *and* the client's decoder has answered
    (`py4gw/item.py:394`, `:449`), so the three steps are run in order:

    1. **request** -- asks the client's own decoder for this id, through the game thread;
    2. **ready** -- advances the port's polling and says whether an answer has arrived;
    3. **get** -- takes the text, which carries the source's own `"Timeout"` literal if the client
       never answered within the bound the port uses.

    A caller cannot tell an unanswered decode from a nameless record, which is exactly why this layer
    refused these keys until the handshake was wired: answering `""` early is a wrong value of the
    right type. `ready` is polled once here rather than looped, because the port's own request already
    waits its bound -- looping would only make a stalled game thread block the bridge.
    """

    request(record_id)
    ready(record_id)
    return str(get(record_id))


def _read_raw(record: Any, offset: int, fmt: str) -> Any:
    """Read a field GwAu3 reads and this project's structure does not name.

    The record is a ``ctypes.Structure`` whose bytes are the client's own, so a field with no
    attribute name is read from those bytes at GwAu3's own offset and width. That covers the ``hXXXX``
    fields, whose names in the port are placeholders because the layout is not understood there.
    """

    values = struct.unpack_from(fmt, record, offset)
    return values[0] if len(values) == 1 else values


def _read_isdefeated(record: Any) -> bool:
    """``GwAu3_Data_Party.au3`` -- the ``IsDefeated`` case: ``BitAND(flag, 0x20) <> 0``."""

    return bool(record.flag & 0x20)


def _read_ishardmode(record: Any) -> bool:
    """``GwAu3_Data_Party.au3`` -- the ``IsHardMode`` case: ``BitAND(flag, 0x10) <> 0``."""

    return bool(record.flag & 0x10)


def _read_ispartyleader(record: Any) -> bool:
    """``GwAu3_Data_Party.au3`` -- the ``IsPartyLeader`` case: ``BitAND(flag, 0x80) <> 0``."""

    return bool(record.flag & 0x80)


def _read_iswaitingformission(record: Any) -> bool:
    """``GwAu3_Data_Party.au3`` -- the ``IsWaitingForMission`` case: ``BitAND(flag, 0x8) <> 0``."""

    return bool(record.flag & 0x8)


def _read_mypartyptr(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["MyPartyPtr"])



_READERS: dict[str, Any] = {}
_READERS.update(
    {
        "Flags": lambda record: record.flag,
        "HenchmenCount": lambda record, record_id: int(p.henchmen_array.m_size) if (p := _party(record)) is not None else 0,
        "HeroCount": lambda record, record_id: int(p.heroes_array.m_size) if (p := _party(record)) is not None else 0,
        "InvitationRequestsCount": lambda record: record.requests_count,
        "InvitationSendingCount": lambda record: record.sending_count,
        "IsDefeated": _read_isdefeated,
        "IsHardMode": _read_ishardmode,
        "IsPartyLeader": _read_ispartyleader,
        "IsWaitingForMission": _read_iswaitingformission,
        "MyPartyPtr": _read_mypartyptr,
        "OtherCount": lambda record, record_id: int(p.others_array.m_size) if (p := _party(record)) is not None else 0,
        "PlayerCount": lambda record, record_id: int(p.players_array.m_size) if (p := _party(record)) is not None else 0,
        "PlayerPartyID": lambda record, record_id: int(p.party_id) if (p := _party(record)) is not None else 0,
        "TotalPartySize": lambda record, record_id: (
        Party_GetPartyContextInfo("PlayerCount")
        + Party_GetPartyContextInfo("HenchmenCount")
        + Party_GetPartyContextInfo("HeroCount")
    ),
    }
)


def Party_GetPartyContextInfo(info: str = "") -> Any:
    """One field of the record, by GwAu3's field name (``GwAu3_Data_Party.au3``).

    GwAu3's guard order is kept: an empty field name answers ``0`` before anything is read, and a
    record the client does not hold answers ``0`` rather than raising. An unrecognised field name
    answers ``0`` -- GwAu3's own ``Case Else``.

    **The key is resolved before the record is.** A key this layer refuses raises without touching the
    client, which is the whole point of refusing: a caller with no connection must still be told that
    the key is unbuilt, not that it is unconnected. The first version resolved the record first, so
    asking for a refused key without a client reported a connection error instead of the gap.
    """

    if info == "":
        return 0

    # A refused key is answered before the record is resolved, deliberately: the refusal is a fact
    # about this layer, not about the client, so a caller with no connection must still be told the
    # key is unbuilt rather than told it is unconnected. The first version resolved the record first
    # and reported a connection error for a refusal that never needed one.
    if info in _UNIMPLEMENTED:
        raise NotImplementedError(_UNIMPLEMENTED[info])

    reader = _READERS.get(info)
    if reader is None:
        return 0

    record = _record(info)
    if record is None:
        # GwAu3's own no-match guard answers `False` for these keys and `0` for the rest
        # (``GwAu3_Data_Quest.au3:16-21``).
        if info in _FALSE_ON_MISSING:
            return False
        return 0

    # A computed or text key re-enters this accessor, so it is handed the caller's id too. A family
    # with no id parameter -- World_GetWorldInfo -- has none of those keys, so the branch is written
    # against whatever its own first parameter is.
    if info in _COMPUTED:
        return reader(record, info)
    return reader(record)


def _record(record_id: Any) -> Any:
    """The record GwAu3 resolves before its ``Switch``.

    ``client.read_party_context()`` -- this project's own read, which is the same
    client record GwAu3 addresses by base plus stride.
    """

    client = require_client()
    return client.read_party_context()

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

__all__ = ['Party_GetPartyContextInfo', 'Party_GetPartyContextPtr', 'Party_GetHeroFlagInfo', 'Party_GetHeroInfo', 'Party_GetControlledMinionsInfo', 'Party_GetMoraleInfo', 'Party_IsPet', 'Party_GetMyPartyHenchmanInfo', 'Party_GetMyPartyHeroInfo', 'Party_GetMyPartyInfo', 'Party_GetMyPartyPlayerMemberInfo', 'Party_GetPetInfo']
