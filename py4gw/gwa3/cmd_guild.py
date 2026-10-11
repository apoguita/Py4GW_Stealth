"""GwAu3's ``Guild_*`` actions.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

Both functions **refuse**, and the reason is in their own bodies: neither forges a packet. Each fills a
`DllStruct` with a header pair (``0x4C``, ``0xB5``), a direction byte, the character's name and one
final byte -- ``0x02`` for a guild invite, ``0x01`` for a guest -- and hands the struct's pointer to
``Core_Enqueue``, whose body writes it into the client's own command queue with
``WriteProcessMemory`` (``GwAu3_Core.au3:559-566``). This project does not write into that queue.

**The two differ by one byte, and that byte is the whole function.** ``Guild_InviteGuild`` sets the
last word to ``0x02`` and ``Guild_InviteGuest`` to ``0x01``; everything else, including the header and
the name, is identical. A route for one is a route for the other, and the byte is what a faithful
implementation must keep distinguishable.
"""

from __future__ import annotations

from typing import Any

__all__ = ["Guild_InviteGuest", "Guild_InviteGuild"]

#: GwAu3's own struct fields, shared by both functions: the header pair, the direction byte, and the
#: one byte that tells a guild invite from a guest invite.
_INVITE_HEADER = (0x4C, 0xB5)
_INVITE_DIRECTION = 0x01
_INVITE_KIND_GUILD = 0x02
_INVITE_KIND_GUEST = 0x01


def Guild_InviteGuild(char_name: Any) -> None:
    """**REFUSED: GwAu3 writes the invite into the client's own command queue.**

    ``GwAu3_Cmd_Guild.au3`` fills ``$g_d_InviteGuild`` (``0x4C``, ``0xB5``, ``0x01``, the name,
    ``0x02``) and calls ``Core_Enqueue``, which is a ``WriteProcessMemory`` into the client's queue at
    ``256 * $g_i_QueueCounter + $g_p_QueueBase``. This project does not write into that queue. GwAu3's
    body has no ``Return`` either, so it answers AutoIt's valueless default -- one more thing a route
    would have to reproduce.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Guild.au3: `Guild_InviteGuild($a_s_CharName)` fills a struct with "
        f"{_INVITE_HEADER[0]:#x}, {_INVITE_HEADER[1]:#x}, {_INVITE_DIRECTION:#x}, the name and "
        f"{_INVITE_KIND_GUILD:#x}, then calls `Core_Enqueue` -- a `WriteProcessMemory` into the "
        "client's command queue (`GwAu3_Core.au3:559-566`). This project does not write into that "
        "queue, and no ported member invites to a guild: `py4gw/party.py` invites *players* to a party "
        "(`RespondToPartyRequest`) and `py4gw/guild.py` does not exist. The work is the client's own "
        "guild-invite route."
    )


def Guild_InviteGuest(char_name: Any) -> None:
    """**REFUSED: the same struct with one byte changed.** As ``Guild_InviteGuild``.

    ``GwAu3_Cmd_Guild.au3`` is byte for byte ``Guild_InviteGuild`` with
    ``$INVITE_KIND_GUEST`` instead of ``$INVITE_KIND_GUILD``, so the route and the work are the same.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Guild.au3: `Guild_InviteGuest($a_s_CharName)` is `Guild_InviteGuild`'s struct with "
        f"the last word {_INVITE_KIND_GUEST:#x} instead of {_INVITE_KIND_GUILD:#x}; both call "
        "`Core_Enqueue`, a `WriteProcessMemory` into the client's command queue (`GwAu3_Core.au3:559-566`). "
        "Refused for the same reason as `Guild_InviteGuild`: no member of `py4gw/` invites anyone to a "
        "guild, and a route for one must keep this byte distinguishable for the other."
    )
