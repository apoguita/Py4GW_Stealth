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
