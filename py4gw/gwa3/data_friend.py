"""GwAu3's ``Friend_*`` reads, over the record this project already reads.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

**This is the eighth and last read family, and it is hand-written rather than generated -- because its
offsets do not all agree.** Every other family was one ``Switch`` over offsets that resolved, key for
key, against a structure this project declares; here **three of the twenty-two keys land on different
fields than GwAu3's offsets name**, and the difference is not a detail:

| GwAu3 key | GwAu3's offset | The port's field | The port's offset |
| --- | --- | --- | --- |
| ``Type`` | ``+0x0`` | ``type`` | ``+0x0`` |
| ``Status`` | ``+0x4`` | ``status`` | ``+0x4`` |
| ``UUID`` | ``+0x8`` (16 bytes) | ``uuid`` | ``+0x8`` |
| ``Name``/``Alias`` | ``+0x18`` | ``alias`` | ``+0x18`` |
| ``ConnectedName``/``CharName``/``Playing`` | ``+0x2C`` | ``charname`` | **``+0x40``** |
| ``FriendID`` | ``+0x40`` | ``friend_id`` | **``+0x68``** |
| ``MapID``/``ZoneID`` | ``+0x44`` | ``zone_id`` | **``+0x6C``** |

**What the arithmetic says.** A wide string of 20 characters is 40 bytes, so this project's ``alias``
spans ``+0x18`` to ``+0x40`` and its ``charname`` starts exactly where GwAu3 puts ``FriendID``. The
port's layout is internally consistent and 112 bytes end to end. GwAu3's is consistent only if its
strings are **ten** characters: ``alias`` ``+0x18..+0x2C``, ``charname`` ``+0x2C..+0x40``,
``FriendID`` ``+0x40``, ``MapID`` ``+0x44``. GwAu3 reads 20 characters for both and gets away with it
because a wide read stops at the first NUL -- and its own constants are already on record as
disagreeing with this client (``docs/RESEARCH.md:4362-4368``).

**So the three keys refuse rather than pick.** Answering ``ConnectedName`` from this project's
``charname`` is *probably* the same field the client calls the character name -- but "probably" is
exactly what this layer does not ship: a route that reads a field at an offset GwAu3 does not name is a
different reading wearing the same name, and the two structures disagreeing is a **finding for the
owner**, not a licence to choose. The four keys that agree are routed, the composed keys are built on
them, and the two name tables are ported verbatim.
"""

from __future__ import annotations

from typing import Any

from ..context.friend_list_context import (
    FriendStatus,
    FriendStruct,
    FriendType,
    get,
)
from ..player import Player

__all__ = [
    "Friend_GetFriendInfo",
    "Friend_GetFriendListInfo",
    "Friend_GetFriendListPtr",
    "Friend_GetFriendStatusName",
    "Friend_GetFriendTypeName",
    "Friend_GetMyStatus",
    "Friend_IsFriend",
    "Friend_IsIgnored",
]

#: The rule the three offset-disagreeing keys refuse by, with the field and the two offsets filled in.
_OFFSET_RULE = (
    "GwAu3_Data_Friend.au3 reads this key at {gwau3_offset}, and this project's `FriendStruct` declares "
    "{field} at {port_offset} -- the two structures disagree about where the field is. The arithmetic "
    "says why: a 20-character wide string is 40 bytes, so this project's `alias` spans `+0x18` to "
    "`+0x40` and its `charname` begins where GwAu3 puts `FriendID`; GwAu3's own layout is consistent "
    "only if its strings are ten characters wide, which its reads (`'wchar[20]'`) overstate. GwAu3's "
    "constant table is already on record as disagreeing with this client "
    "(`docs/RESEARCH.md:4362-4368`). Answering this key from the field that looks right would be a "
    "different reading under the same name, so it refuses: `py4gw/context/friend_list_context.py` is "
    "where the port's layout lives, and which of the two is right about the client is the owner's "
    "finding to settle."
)

#: The status names GwAu3 answers, keyed by its own constants (``GwAu3_Data_Friend.au3:147-160``).
_STATUS_NAMES: dict[int, str] = {
    0: "Offline",
    1: "Online",
    2: "Do Not Disturb",
    3: "Away",
}

#: The type names GwAu3 answers (``GwAu3_Data_Friend.au3:162-175``).
_TYPE_NAMES: dict[int, str] = {
    1: "Friend",
    2: "Ignore",
    3: "Player",
    4: "Trade",
}

#: GwAu3's own sentinels for "no such friend": an identifier of ``""`` answers before anything is read,
#: and a friend number outside ``1..total`` answers ``0`` (``GwAu3_Data_Friend.au3:32``, ``:45``).
_NO_IDENTIFIER = ""
_FIRST_FRIEND = 1


def Friend_GetMyStatus() -> int:
    """The player's own friend-list status (``GwAu3_Data_Friend.au3:3-5``).

    GwAu3 reads ``$g_p_FriendList + 0xA0``; this project's `FriendListStruct` declares
    ``player_status`` at ``+0xA0`` -- the same offset, so the two agree here -- and
    `Player.GetPlayerStatus` is the ported member for it. Both answer one of ``0..3``, the constants
    `Friend_GetFriendStatusName` names.
    """

    return int(Player.GetPlayerStatus())


def Friend_GetFriendListPtr() -> int:
    """**REFUSED: GwAu3 answers its own list pointer, and this layer hands out no client addresses.**

    ``GwAu3_Data_Friend.au3:7-9`` answers ``$g_p_FriendList`` -- a client address a caller then reads
    with ``Memory_Read``. This project hands out none (the same divergence `Agent_GetAgentPtr` and
    `Item_GetItemPtr` record), and an address is useless across the bridge. What a caller wants from the
    pointer is already routed: `Friend_GetFriendListInfo` for the counts and
    `Friend_GetFriendInfo` for a member.
    """

    raise NotImplementedError(
        "GwAu3_Data_Friend.au3:7-9 answers `$g_p_FriendList`, a raw client address. This project hands "
        "out no client addresses (`Agent_GetAgentPtr` and `Item_GetItemPtr` record the same divergence "
        "and answer a record instead), and an address cannot cross the bridge usefully. The values a "
        "caller reads through it are routed: `Friend_GetFriendListInfo` "
        "(`py4gw/context/friend_list_context.py` carries `get_number_of_friends` and its siblings) and "
        "`Friend_GetFriendInfo`."
    )


def Friend_GetFriendListInfo(info: str = "") -> Any:
    """One of the friend list's own counts (``GwAu3_Data_Friend.au3:11-29``).

    **All five keys are routed and every offset agrees**, which is worth stating because the member
    records do not: ``number_of_friend``/``number_of_ignore``/``number_of_partner``/``number_of_trade``
    sit at ``+0x24``/``+0x28``/``+0x2C``/``+0x30`` in both, and ``PlayerStatus`` at ``+0xA0`` in both.

    GwAu3's guard order is kept: an empty field name answers ``0`` before the list is read, and a list
    that cannot be read answers ``0``. An unrecognised field name answers ``0`` -- its own ``EndSwitch``
    fallthrough.
    """

    if info == "":
        return 0

    listing = get()
    if listing is None:
        return 0

    if info == "NumberOfFriend":
        return int(listing.get_number_of_friends())
    if info == "NumberOfIgnore":
        return int(listing.get_number_of_ignores())
    if info == "NumberOfPartner":
        return int(listing.get_number_of_partners())
    if info == "NumberOfTrade":
        return int(listing.get_number_of_traders())
    if info == "PlayerStatus":
        return int(listing.get_my_status())
    return 0


def _resolve(identifier: Any) -> tuple[Any, int]:
    """GwAu3's identifier resolution: a **number** is a one-based index, a **string** a name or alias.

    GwAu3 walks the whole list twice for a string -- once comparing the name at ``+0x2C`` and once the
    alias at ``+0x18`` -- and answers the record and the number it matched. This project's
    `FriendListStruct.find_friend` takes the alias and the character name as separate arguments, so the
    two walks become one call with both names offered, and the number comes from the record's position.

    The number is answered as GwAu3 answers it: **one-based**, and ``0`` when nothing matched.
    """

    listing = get()
    if listing is None:
        return None, 0

    if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.isdigit()):
        number = int(identifier)
        total = (
            int(listing.get_number_of_friends())
            + int(listing.get_number_of_ignores())
            + int(listing.get_number_of_partners())
            + int(listing.get_number_of_traders())
        )
        if number < _FIRST_FRIEND or number > total:
            return None, 0
        # GwAu3 indexes the record at `4 * number`; the ported reader takes a native array index, which
        # is the same stride, and its own bounds check answers None for anything it does not hold.
        return listing.get_friend(number - 1), number

    name = str(identifier)
    if name == _NO_IDENTIFIER:
        return None, 0

    record = listing.find_friend(alias=name)
    if record is None:
        record = listing.find_friend(character_name=name)
    if record is None:
        return None, 0

    # GwAu3 walks the list itself and keeps the index it matched, so its number is the record's
    # position. This project's `find_friend` answers the record **without** its position, so the
    # position is found by scanning for it -- first by identity, then by the two fields that name a
    # record (its 16-byte UUID and its alias). Comparing `friend_id` alone was the first attempt and it
    # was wrong: a record whose id is zero compares equal to every other such record, so the *first*
    # one won and the number was off by however many empty ids preceded it.
    wanted_uuid = bytes(bytearray(record.uuid))
    wanted_alias = _decode(record.alias)
    for index in range(0, 64):
        candidate = listing.get_friend(index)
        if candidate is None:
            break
        if candidate is record:
            return record, index + 1
        if (
            bytes(bytearray(candidate.uuid)) == wanted_uuid
            and _decode(candidate.alias) == wanted_alias
        ):
            return record, index + 1
    # The record was found and its position was not: GwAu3 would answer the position, and this answers
    # `0` -- GwAu3's own "no such friend" -- rather than a position it cannot establish.
    return record, 0


def Friend_GetFriendInfo(identifier: Any = "", info: str = "") -> Any:
    """One field of one friend, by GwAu3's field name (``GwAu3_Data_Friend.au3:31-131``).

    GwAu3's two guards are kept in its own order: an empty identifier **or** an empty field name
    answers ``0`` before anything is read, and a record that cannot be resolved answers ``0``.

    The keys sit in three groups:

    * **routed** -- ``Type``/``FriendType``, ``Status``/``FriendStatus``, ``UUID``,
      ``Name``/``Alias``, and the computed ``TypeName``, ``StatusName``, ``IsOnline``, ``IsOffline``,
      ``IsFriend``, ``IsIgnored``, ``Number``/``Index``;
    * **refused** -- ``ConnectedName``/``CharName``/``Playing``, ``FriendID``, ``MapID``/``ZoneID``,
      because their offsets disagree between the two structures (see this module's header);
    * **refused** -- ``Ptr``, which is a client address.
    """

    if identifier == _NO_IDENTIFIER or info == "":
        return 0
    if info == "Ptr":
        raise NotImplementedError(
            "GwAu3_Data_Friend.au3:125-126 answers the friend record's own address. This project hands "
            "out no client addresses, and its records are materialized -- `Friend_GetFriendInfo` answers "
            "the *fields* of a friend, which is what a caller reads through the pointer. "
            "`py4gw/context/friend_list_context.py` is where the record lives."
        )
    if info in ("ConnectedName", "CharName", "Playing"):
        raise NotImplementedError(
            _OFFSET_RULE.format(
                gwau3_offset="``+0x2C``", field="``charname``", port_offset="``+0x40``"
            )
        )
    if info == "FriendID":
        raise NotImplementedError(
            _OFFSET_RULE.format(
                gwau3_offset="``+0x40``", field="``friend_id``", port_offset="``+0x68``"
            )
        )
    if info in ("MapID", "ZoneID"):
        raise NotImplementedError(
            _OFFSET_RULE.format(
                gwau3_offset="``+0x44``", field="``zone_id``", port_offset="``+0x6C``"
            )
        )

    record, number = _resolve(identifier)
    if record is None:
        return 0

    if info in ("Type", "FriendType"):
        return int(record.type)
    if info in ("Status", "FriendStatus"):
        return int(record.status)
    if info == "UUID":
        return bytes(bytearray(record.uuid))
    if info in ("Name", "Alias"):
        return _decode(record.alias)
    if info == "TypeName":
        return Friend_GetFriendTypeName(int(record.type))
    if info == "StatusName":
        return Friend_GetFriendStatusName(int(record.status))
    if info == "IsOnline":
        return int(record.status) == int(FriendStatus.online)
    if info == "IsOffline":
        return int(record.status) == int(FriendStatus.offline)
    if info == "IsFriend":
        return int(record.type) == int(FriendType.friend)
    if info == "IsIgnored":
        return int(record.type) == int(FriendType.ignore)
    if info in ("Number", "Index"):
        return number
    return 0


def _decode(wide: Any) -> str:
    """A wide character array as text, up to its first NUL.

    The port's `FriendStruct` holds raw ``c_ushort`` arrays rather than decoded strings, so the decode
    is explicit -- and stopping at the NUL is what makes a fixed-width array a string, which is also
    why GwAu3's own over-long ``'wchar[20]'`` reads return the right text.
    """

    characters = []
    for value in wide:
        if int(value) == 0:
            break
        characters.append(chr(int(value)))
    return "".join(characters)


def Friend_IsFriend(character_name: Any) -> bool:
    """Whether a name is on the friend list (``GwAu3_Data_Friend.au3:133-138``).

    GwAu3's own shape is kept: it resolves the record through ``Friend_GetFriendInfo($name, "Ptr")``
    first and answers ``False`` when there is none -- which is why a name that is on the *ignore* list
    answers ``False`` here too, and must: GwAu3's record lookup is by name across the whole list, and
    the type is what decides.
    """

    if Friend_GetFriendInfo(character_name, "Number") == 0:
        return False
    return bool(Friend_GetFriendInfo(character_name, "IsFriend"))


def Friend_IsIgnored(character_name: Any) -> bool:
    """Whether a name is on the ignore list (``GwAu3_Data_Friend.au3:140-145``). As `Friend_IsFriend`."""

    if Friend_GetFriendInfo(character_name, "Number") == 0:
        return False
    return bool(Friend_GetFriendInfo(character_name, "IsIgnored"))


def Friend_GetFriendStatusName(status: Any) -> str:
    """The name of a status (``GwAu3_Data_Friend.au3:147-160``).

    **A pure table, ported verbatim** -- GwAu3's four names and its ``Unknown`` fallthrough, in its own
    spelling: ``"Do Not Disturb"`` with its spaces and capitalisation, because a script that prints or
    compares the string is comparing this text.
    """

    return _STATUS_NAMES.get(int(status), "Unknown")


def Friend_GetFriendTypeName(friend_type: Any) -> str:
    """The name of a friend type (``GwAu3_Data_Friend.au3:162-175``). Also a pure table."""

    return _TYPE_NAMES.get(int(friend_type), "Unknown")


# `FriendStruct` is imported for its own sake: the module's docstring cites its layout, and the type is
# what a caller receives from the ported reader this module routes through.
_ = FriendStruct
