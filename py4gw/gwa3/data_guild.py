"""GwAu3's `Guild_GetMyGuildInfo`, over the record this project already reads.
**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_family.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

GwAu3's guild context -- the player's guild index, rank and name, the announcement and its author, the alliance and roster sizes, the town counts, and one roster member's own fields. GwAu3 reads the record its own ``Guild_GetGuildContextPtr`` resolves; this project reads the same record as `GuildContextStruct` through `client.read_guild_context` (`py4gw/client.py:1511`), and every offset it names lands on a named field of it.

**Its four pointer keys answer the record lists, not addresses** -- the alliance, the roster, the guild array and the history -- because this layer hands out no client address, and an absent array answers `[]`, which is the falsy value GwAu3's own ``Return 0`` gave a caller's guard. `Guild_GetGuildPlayerInfo` reads its roster and size through those same two keys, exactly as the source's body does.

`Guild_GetMyGuildInfo` is one ``Switch`` over 15 keys in GwAu3
(``GwAu3_Data_Guild.au3``). 12 of the 15 field keys resolve to a **named
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
from ..context import GuildContextStruct

_UNIMPLEMENTED: dict[str, str] = {}

_COMPUTED: frozenset[str] = frozenset([])

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


def _read_announcement(record: Any) -> Any:
    """``GwAu3_Data_Guild.au3`` -- the ``Announcement`` case: the pointer read *through* ``+0x38``."""

    return record.announcement_str


def _read_announcementauthor(record: Any) -> Any:
    """``GwAu3_Data_Guild.au3`` -- the ``AnnouncementAuthor`` case: the pointer read *through* ``+0x38``."""

    return record.announcement_author_str


def _read_playername(record: Any) -> Any:
    """``GwAu3_Data_Guild.au3`` -- the ``PlayerName`` case: the pointer read *through* ``+0x38``."""

    return record.player_name_str



_READERS: dict[str, Any] = {}
_READERS.update(
    {
        "Announcement": _read_announcement,
        "AnnouncementAuthor": _read_announcementauthor,
        "GuildArrayPtr": lambda record: record.guild_array_array.m_buffer,
        "GuildArraySize": lambda record: record.guild_array_array.m_size,
        "GuildHistoryPtr": lambda record: record.player_guild_history_array.m_buffer,
        "GuildHistorySize": lambda record: record.player_guild_history_array.m_size,
        "GuildRosterPtr": lambda record: record.player_roster_array.m_buffer,
        "GuildRosterSize": lambda record: record.player_roster_array.m_size,
        "KurzickTownCount": lambda record: record.kurzick_town_count,
        "LuxonTownCount": lambda record: record.luxon_town_count,
        "PlayerGuildIndex": lambda record: record.player_guild_index,
        "PlayerGuildRank": lambda record: record.player_guild_rank,
        "PlayerName": _read_playername,
        "TownAlliance": lambda record: record.factions_outpost_guilds_array.m_buffer,
        "TownAllianceSize": lambda record: record.factions_outpost_guilds_array.m_size,
    }
)


def Guild_GetMyGuildInfo(info: str = "") -> Any:
    """One field of the record, by GwAu3's field name (``GwAu3_Data_Guild.au3``).

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

    ``client.read_guild_context()`` -- this project's own read, which is the same
    client record GwAu3 addresses by base plus stride.
    """

    client = require_client()
    return client.read_guild_context()

"""``GwAu3_Data_Guild.au3``'s guild accessors, hand-written into their generated module.

Read from ``tools/gwa3_snippets/`` at generation time by ``tools/generate_gwa3_family.py``, the same
mechanism the map and party snippets use: the generated module is rewritten whole on every run, so a
function written straight into it would be lost the next time the generator ran.

**What it is.** ``Guild_GetMyGuildInfo`` (``GwAu3_Data_Guild.au3:10-53``) answers one field of the guild
context -- the record the client holds for the character's guild -- and ``Guild_GetGuildPlayerInfo``
(``:55-91``) answers one field of one **roster member**. GwAu3 reaches the context through its own
``Guild_GetGuildContextPtr`` (``:4-8``, a pointer it resolves from ``$g_p_BasePointer``) and reads fixed
offsets. This project reads the **same record** as `GuildContextStruct`
(`py4gw/context/guild_context.py:364`) through `py4gw.client.RemoteClient.read_guild_context`
(``py4gw/client.py:1511``), and the roster as `GuildPlayerStruct`
(`py4gw/context/guild_context.py:248`), whose ``0x174`` size the port asserts
(``guild_context.py:522``).

**Every offset GwAu3 reads lands on a named field of the port's record, and the two structures agree
throughout.** The context keys are ``+0x34`` `player_name_enc` (asserted at ``+0x34``,
``guild_context.py:527``), ``+0x60`` `player_guild_index`, ``+0x78`` `announcement_enc` (asserted at
``+0x78``, ``:529``), ``+0x278`` `announcement_author_enc`, ``+0x2A0`` `player_guild_rank`, ``+0x2A8``
`factions_outpost_guilds_array` (asserted at ``+0x2A8``, ``:530``), ``+0x2B8``/``+0x2BC`` the two town
counts, ``+0x2F8`` `guild_array_array` (asserted, ``:531``), ``+0x2CC``
`player_guild_history_array`, and ``+0x358`` `player_roster_array` (asserted, ``:532``). The four
``*Size`` keys read the third word of the array header GwAu3 calls ``+0x8``, which is the port's own
`GWArray.m_size` (`py4gw/context/gw_array.py:42`) -- the same word in the same place. The roster
member's eight offsets (``+0x8``, ``+0x30``, ``+0x58``, ``+0x80``, ``+0x84``, ``+0xDC``, ``+0xE0``,
``+0xE4``) are `GuildPlayerStruct`'s `invited_name_enc`, `current_name_enc`, `inviter_name_enc`,
`invite_time`, `promoter_name_enc`, `offline`, `member_type` and `status`, in that order.

**Four keys answer the client *address* GwAu3 reads, and each answers this project's records instead.**
``TownAlliance``, ``GuildRosterPtr``, ``GuildArrayPtr`` and ``GuildHistoryPtr`` are pointers in GwAu3 --
its own callers use them only as an array base to walk with a stride -- and this layer hands out no
address (the owner's ruling at the top of ``docs/GWA3_COMPAT_SPEC.md``). Each answers the array's own
elements through the port's property, so the value is the record list a caller wants; an absent array
answers the empty list, which is the falsy value GwAu3's own ``Return 0`` produced for a caller's guard.
``GuildRosterPtr`` in particular is what `Guild_GetGuildPlayerInfo` itself walks, so it answers what
that accessor indexes by number.

**The name keys are answered as decoded text.** GwAu3's ``Memory_Read(..., "wchar[20]")`` hands back the
wide characters as they sit in the record; this answers the port's display-safe decode of the same field
(`GuildPlayerStruct.current_name_str`, `GuildContextStruct.player_name_str`), which is the port's own
read of those twenty characters (``guild_context.py:422-446``, ``:332-361``).
"""

#: ``{GwAu3 key: reader}`` for the guild **context**'s keys (``GwAu3_Data_Guild.au3:14-50``). Written as
#: readers rather than as field names, because this project reaches no field through a dynamic name.
_CONTEXT_KEYS: dict[str, Any] = {
    "PlayerName": lambda context: context.player_name_str or "",
    "PlayerGuildIndex": lambda context: int(context.player_guild_index),
    "PlayerGuildRank": lambda context: int(context.player_guild_rank),
    "Announcement": lambda context: context.announcement_str or "",
    "AnnouncementAuthor": lambda context: context.announcement_author_str or "",
    # The four pointer keys: GwAu3 answers an address, this answers the array's own records.
    "TownAlliance": lambda context: context.factions_outpost_guilds or [],
    "TownAllianceSize": lambda context: int(context.factions_outpost_guilds_array.m_size),
    "KurzickTownCount": lambda context: int(context.kurzick_town_count),
    "LuxonTownCount": lambda context: int(context.luxon_town_count),
    "GuildRosterPtr": lambda context: context.player_roster or [],
    "GuildRosterSize": lambda context: int(context.player_roster_array.m_size),
    "GuildArrayPtr": lambda context: context.guild_array or [],
    "GuildArraySize": lambda context: int(context.guild_array_array.m_size),
    "GuildHistoryPtr": lambda context: context.player_guild_history or [],
    "GuildHistorySize": lambda context: int(context.player_guild_history_array.m_size),
}

#: ``{GwAu3 key: reader}`` for one **roster member**'s keys (``GwAu3_Data_Guild.au3:64-88``).
_ROSTER_KEYS: dict[str, Any] = {
    "InvitedName": lambda member: member.invited_name_str,
    "CurrentName": lambda member: member.current_name_str,
    "InviterName": lambda member: member.inviter_name_str,
    "InviteTime": lambda member: int(member.invite_time),
    "PromoterName": lambda member: member.promoter_name_str,
    "Offline": lambda member: int(member.offline),
    "MemberType": lambda member: int(member.member_type),
    "Status": lambda member: int(member.status),
}


def Guild_GetGuildContextPtr() -> Any:
    """The guild context record (``GwAu3_Data_Guild.au3:4-8``).

    GwAu3 resolves ``BasePointer[0][0x18][0x3C]`` through its own ``Memory_ReadPtr`` and answers that
    client *address*. This answers **the record** read from the same slot:
    `py4gw.client.ConnectedClient.read_guild_context` (``py4gw/client.py:1511``) over
    `GuildContextStruct` (`py4gw/context/guild_context.py:364`) -- the record every key of
    `Guild_GetMyGuildInfo` in this same module reads, and the ``0x3C`` GwAu3 walks is that structure's
    own offset in the game context (`GameContextStruct.guild_context`,
    `py4gw/context/game_context.py:45`, the slot ``data_game.py``'s ``GuildContext`` key resolves).

    ``0`` when the client holds no guild context, which is GwAu3's own answer for a null pointer.

    **The divergence, in one sentence:** GwAu3 hands back a client address and this hands back the record
    that address holds -- the substitution `World_GetWorldContextPtr` (`py4gw/gwa3/data_world.py:429`)
    and `Agent_GetAgentPtr` already record.
    """

    context = require_client().read_guild_context()
    return 0 if context is None else context


def Guild_GetMyGuildInfo(info: str = "") -> Any:
    """One field of the guild context, by GwAu3's field name (``GwAu3_Data_Guild.au3:10-53``).

    GwAu3's guard order is kept: an empty key answers ``0`` before anything is read, a context the
    client does not hold answers ``0`` -- its own ``If $l_p_Ptr = 0 ... Then Return 0`` (``:12``) -- and
    an unrecognised key answers ``0``, which its ``Switch`` reaches by falling out of the block to the
    same ``Return 0`` (``:52``).

    The four pointer keys are the one divergence, and they widen rather than refuse: GwAu3 hands back
    the client address held at ``+0x2A8``, ``+0x2F8``, ``+0x2CC`` and ``+0x358``; this answers the
    records those arrays hold, through the port's own `factions_outpost_guilds`, `guild_array`,
    `player_guild_history` and `player_roster` properties, because a client address is never an answer
    here. A caller that only guards the return keeps its behaviour: an absent array answers the empty
    list, which is falsy, exactly as GwAu3's ``0`` was.
    """

    from ..client import require_client

    if info == "":
        return 0

    context = require_client().read_guild_context()
    if context is None:
        return 0

    reader = _CONTEXT_KEYS.get(info)
    if reader is None:
        return 0
    return reader(context)


def Guild_GetGuildPlayerInfo(player_index: Any, info: str = "") -> Any:
    """One field of one guild-roster member (``GwAu3_Data_Guild.au3:55-91``).

    ``$a_i_PlayerIndex`` is **zero-based** in GwAu3 -- the source tests ``< 0`` and ``>=`` the roster
    size without subtracting one (``:59``), unlike its party accessors -- so index ``0`` is the first
    member and the size itself is out of range.

    GwAu3's guard order is kept, including the two guards' order: the roster pointer and size are tested
    first and answer ``0``, and only then is the empty key tested (``:62``), so an empty key with an
    out-of-range index still answers ``0`` -- the same ``0`` the index guard would have produced, by the
    source's own route. The roster and its size are read through `Guild_GetMyGuildInfo`'s own two keys,
    which is the source's own body (``:56-57``), so the index is validated against the same array this
    member indexes. Two name keys answer this project's display-safe decode of the record's twenty
    characters where GwAu3 hands back the raw wide buffer; the other six are the record's own fields.
    """

    roster = Guild_GetMyGuildInfo("GuildRosterPtr")
    size = Guild_GetMyGuildInfo("GuildRosterSize")

    if not roster or int(player_index) < 0 or int(player_index) >= int(size):
        return 0

    if info == "":
        return 0

    member = roster[int(player_index)]

    reader = _ROSTER_KEYS.get(info)
    if reader is None:
        return 0
    return reader(member)

__all__ = ['Guild_GetMyGuildInfo', 'Guild_GetGuildContextPtr', 'Guild_GetGuildPlayerInfo']
