"""GwAu3's ``Friend_*`` actions, over this project's own routes.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

**Five of the nine are routed and four refuse**, and the split is exactly where GwAu3 stopped forging:
its five status functions enqueue a two-word record through ``Core_Enqueue``, and the four
management functions (add/remove friend, add/remove ignore) are the longest write paths in the whole
API -- ``Friend_AddFriend`` calls ``VirtualAllocEx`` **in the client** twice to hold the name and the
alias, writes both, and only then enqueues. The first is a status this project's own
`Player.SetPlayerStatus` sets; the second is a remote allocation this project does not make.
"""

from __future__ import annotations

from typing import Any

from ..player import Player

__all__ = [
    "Friend_AddFriend",
    "Friend_AddIgnore",
    "Friend_RemoveFriend",
    "Friend_RemoveIgnore",
    "Friend_SetAwayStatus",
    "Friend_SetDNDStatus",
    "Friend_SetOfflineStatus",
    "Friend_SetOnlineStatus",
    "Friend_SetPlayerStatus",
]

#: GwAu3's own status range, from the guard at the top of `Friend_SetPlayerStatus`: its constants are
#: ``$GC_I_FRIEND_STATUS_OFFLINE`` .. ``$GC_I_FRIEND_STATUS_AWAY``, which are ``0``..``3`` and are the
#: same numbers this project's `PlayerStatus` uses. Kept as the source's bounds.
_FIRST_STATUS = 0
_LAST_STATUS = 3

#: GwAu3's status constants, by the name it gives each (``GwAu3_Const_Friend.au3``).
_STATUS_OFFLINE = 0
_STATUS_ONLINE = 1
_STATUS_DND = 2
_STATUS_AWAY = 3


def Friend_SetPlayerStatus(status: Any) -> bool:
    """Set the player's own friend-list status (``GwAu3_Cmd_Friend.au3:4-26``).

    GwAu3's three steps are kept in its own order, and so are its two answers:

    1. a status outside ``0..3`` answers **False** without reaching the client;
    2. a status that is *already set* answers **True** without reaching the client either -- GwAu3
       reads the current one first (``Friend_GetMyStatus``) and returns early, logging at debug level;
    3. otherwise the change is enqueued and answered ``True``.

    **GwAu3 already reaches this by a game-thread call, not a packet**, so the mechanisms agree: the
    ported member is the client's own status setter. Its own validation is the same range GwAu3 guards.
    """

    status = int(status)
    if status < _FIRST_STATUS or status > _LAST_STATUS:
        return False

    if int(Player.GetPlayerStatus()) == status:
        return True

    return bool(Player.SetPlayerStatus(status))


def Friend_SetOnlineStatus() -> bool:
    """Set the player's status online (``GwAu3_Cmd_Friend.au3:29-31``)."""

    return Friend_SetPlayerStatus(_STATUS_ONLINE)


def Friend_SetOfflineStatus() -> bool:
    """Set the player's status offline (``GwAu3_Cmd_Friend.au3:34-36``)."""

    return Friend_SetPlayerStatus(_STATUS_OFFLINE)


def Friend_SetDNDStatus() -> bool:
    """Set the player's status to do-not-disturb (``GwAu3_Cmd_Friend.au3:39-41``)."""

    return Friend_SetPlayerStatus(_STATUS_DND)


def Friend_SetAwayStatus() -> bool:
    """Set the player's status away (``GwAu3_Cmd_Friend.au3:44-46``)."""

    return Friend_SetPlayerStatus(_STATUS_AWAY)


def Friend_AddFriend(
    character_name: Any, alias: Any = "", friend_type: Any = 1
) -> bool:
    """**REFUSED: GwAu3 allocates memory inside the client to hold the name and alias.**

    ``GwAu3_Cmd_Friend.au3`` guards the name's length and the friend type, checks whether the friend
    already exists, and then calls ``VirtualAllocEx`` on the client's handle **twice** -- once for the
    name and once for the alias -- writes both strings into the client, and enqueues a record pointing
    at them. That is remote allocation and a remote write, which this project does not do: its writes
    are the client's own functions called on the game thread, not memory it allocates in the target.
    The work is the client's own friend-add route, and GwAu3's guards are worth keeping when it lands
    (a name of ``0`` or more than ``$GC_I_FRIEND_CHARNAME_MAX_LENGTH``, and a type outside ``1..2``).
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Friend.au3: `Friend_AddFriend($a_s_CharacterName, $a_s_Alias = \"\", "
        "$a_i_FriendType = $GC_I_FRIEND_TYPE_FRIEND)` calls `VirtualAllocEx` on the client's process "
        "handle twice and writes the name and alias into that allocation before enqueuing. Remote "
        "allocation plus a remote write is not a mechanism this project uses -- `py4gw/` places no "
        "memory in `Gw.exe`; it calls the client's own functions (see `py4gw/context/"
        "friend_list_context.py` for what it does read, and `py4gw/player.py:1050-1070` for the one "
        "friend-status route that IS ported). The work is the client's own friend-add route."
    )


def Friend_RemoveFriend(name_or_alias: Any) -> bool:
    """**REFUSED: GwAu3 reaches it through its injected assembly stub.**

    ``GwAu3_Cmd_Friend.au3`` hands the resolved friend record to its assembler, which calls the
    client's remove function through the stub it injected (the same mechanism as
    ``Friend_AddFriend``, without the allocation). This project has no member that removes a friend:
    ``py4gw/context/friend_list_context.py`` reads the friend list and its own ``set_friend_list_status``
    is the status half only. The work is the client's own remove route.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Friend.au3: `Friend_RemoveFriend($a_s_NameOrAlias)` resolves the record and runs it "
        "through GwAu3's injected assembly stub. No member of py4gw/ removes a friend -- "
        "`py4gw/context/friend_list_context.py` reads the list (`get_my_status`, the friend records) "
        "and nothing mutates it. The work is the client's own remove route, and it is named rather than "
        "approximated."
    )


def Friend_AddIgnore(character_name: Any, alias: Any = "") -> bool:
    """**REFUSED: the same allocation path as ``Friend_AddFriend``.**

    ``GwAu3_Cmd_Friend.au3`` calls ``Friend_AddFriend`` with the ignore type after the same guards, so
    it reaches ``VirtualAllocEx`` and a remote write in the client for the same reason.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Friend.au3: `Friend_AddIgnore($a_s_CharacterName, $a_s_Alias = \"\")` is "
        "`Friend_AddFriend` with the ignore type, so it takes the same `VirtualAllocEx` path and writes "
        "the name and alias into the client (`py4gw/` places no memory in `Gw.exe`). Refused for the "
        "same reason; the work is the client's own ignore-add route."
    )


def Friend_RemoveIgnore(character_name: Any) -> bool:
    """**REFUSED: as ``Friend_RemoveFriend``, for the ignore list.**

    ``GwAu3_Cmd_Friend.au3`` resolves the ignored record and runs it through its injected stub. No
    member of ``py4gw/context/friend_list_context.py`` removes an ignore.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Friend.au3: `Friend_RemoveIgnore($a_s_CharacterName)` runs the record through "
        "GwAu3's injected assembly stub. `py4gw/context/friend_list_context.py` reads the friend list "
        "and removes nothing; the work is the client's own ignore-remove route."
    )
