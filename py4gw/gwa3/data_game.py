"""GwAu3's ``Game_GetGameInfo``, over the game context this project already reads.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

**Hand-written, not generated, and the reason is the shape of this function.** The other ``data_*``
modules are emitted by ``tools/generate_gwa3_family.py`` from a GwAu3 ``Switch`` whose every case is one
fixed offset of **one** record. Twelve of this function's fifteen keys are not that shape: they answer a
*different* record -- the context the slot points at -- through that context's own reader, so there is no
offset-to-attribute table to generate. It is kept by hand like ``data_attribute.py`` and
``data_effect.py``, and its source of record is ``tools/gwa3_snippets/data_game_info.py``, so the wording
exists in one place.

**What it is.** ``Game_GetGameInfo`` (`GwAu3_Data_Game.au3:10-55`) answers one slot of the client's
**game context** -- the root record every other context pointer hangs off. GwAu3 reaches it through its
own ``Game_GetGameContextPtr`` (``:4-8``, one ``Memory_ReadPtr($g_p_BasePointer, [0, 0x18], "ptr")``)
and then reads one field at a fixed offset inside that record. This project reads the **same root** as
`GameContextStruct` (`py4gw/context/game_context.py:19`), whose size is asserted at ``0x5C`` (`:98`),
and **every offset GwAu3's ``Switch`` names is that structure's own field**, so the reader below
reproduces GwAu3's offsets by naming the port's field literally:

    ``+0x8`` ``agent_context``, ``+0x14`` ``map_context``, ``+0x18`` ``text_parser``, ``+0x20``
    ``some_number``, ``+0x28`` ``account_context``, ``+0x2C`` ``world_context``, ``+0x30``
    ``cinematic``, ``+0x38`` ``gadget_context``, ``+0x3C`` ``guild_context``, ``+0x40``
    ``item_context``, ``+0x44`` ``char_context``, ``+0x4C`` ``party_context``, ``+0x58``
    ``trade_context`` (``py4gw/context/game_context.py:32-52``).

**Twelve of the fifteen keys are ``ptr`` reads, and each answers the record rather than the address.**
GwAu3 hands the caller a client address for `AgentContext` (``:16``), `MapContext` (``:18``),
`TextParser` (``:21``), `AccountContext` (``:29``), `WorldContext` (``:31``), `Cinematic` (``:34``),
`GadgetContext` (``:41``), `GuildContext` (``:43``), `ItemContext` (``:45``), `CharContext` (``:47``),
`PartyContext` (``:49``) and `TradeContext` (``:51``). **This layer hands out no client address**, so
each of those keys answers the record this project reads *from that same slot*, through the client's own
on-demand reader -- the shape `Agent_GetAgentPtr` and `Item_GetItemPtr` already record
(`py4gw/gwa3/data_agent.py:677`). Every one of those readers resolves the field of `GameContextStruct`
that GwAu3's offset names:

    * ``AgentContext`` -- ``client.read_acc_agent_context()`` (`py4gw/client.py:1522`;
      `py4gw/context/acc_agent_context.py:451`, ``agent_context`` at ``+0x8``)
    * ``MapContext`` -- ``client.read_map_context()`` (`py4gw/client.py:1319`;
      `py4gw/context/map_context.py:1844`, ``map_context`` at ``+0x14``)
    * ``TextParser`` -- ``client.read_text_parser()`` (`py4gw/client.py:1478`;
      `py4gw/context/text_parser_context.py:254`, ``text_parser`` at ``+0x18``)
    * ``AccountContext`` -- ``client.read_account_context()`` (`py4gw/client.py:1671`;
      `py4gw/context/account_context.py:222`, ``account_context`` at ``+0x28``)
    * ``WorldContext`` -- ``client.read_world_context()`` (`py4gw/client.py:1582`;
      `py4gw/context/world_context.py:2118`, ``world_context`` at ``+0x2C``)
    * ``Cinematic`` -- ``client.read_cinematic_context()`` (`py4gw/client.py:1740`;
      `py4gw/context/cinematic_context.py:101`, ``cinematic`` at ``+0x30``)
    * ``GadgetContext`` -- ``client.read_gadget_context()`` (`py4gw/client.py:1682`;
      `py4gw/context/gadget_context.py:173`, ``gadget_context`` at ``+0x38``)
    * ``GuildContext`` -- ``client.read_guild_context()`` (`py4gw/client.py:1511`;
      `py4gw/context/guild_context.py:600`, ``guild_context`` at ``+0x3C``)
    * ``ItemContext`` -- ``client.read_item_context()`` (`py4gw/client.py:1610`;
      `py4gw/context/item_context.py:1896`, ``item_context`` at ``+0x40``)
    * ``CharContext`` -- ``client.read_char_context()`` (`py4gw/client.py:1745`;
      `py4gw/context/char_context.py:446`, ``char_context`` at ``+0x44``)
    * ``PartyContext`` -- ``client.read_party_context()`` (`py4gw/client.py:1500`;
      `py4gw/context/party_context.py:462`, ``party_context`` at ``+0x4C``)
    * ``TradeContext`` -- ``client.read_trade_context()`` (`py4gw/client.py:1593`;
      `py4gw/context/trade_context.py:217`, ``trade_context`` at ``+0x58``)

Where such a slot holds no pointer the reader answers ``None`` (`py4gw/context/guild_context.py:603`,
`:609` is the shape of all twelve), and this key answers ``0`` -- which is GwAu3's own answer for a null
context pointer (``:12``).

**``Game_GetGameContextPtr`` answers the same root as a record.** ``:4-8`` is one
``Memory_ReadPtr($g_p_BasePointer, [0, 0x18], "ptr")`` whose second element is the game context's client
*address*, which is the one thing this layer never hands out. Its whole purpose in GwAu3 is to feed its
own ``Switch`` -- the twelve readers above resolve that address themselves -- so the member answers the
record that address holds, through the port's own reader (`py4gw/client.py:1308`, the port's
`GameContext` reader), and it is defined below with the one divergence the port's own null-chain
refusal introduces.

**The same records are reachable through the sources' own context facades** where the port keeps one --
`GWContext.Map.GetContext()`, `GWContext.World.GetContext()`, `GWContext.Cinematic.GetContext()`,
`GWContext.Char.GetContext()`, `GWContext.Party.GetContext()`, `GWContext.Guild.GetContext()`,
`GWContext.AccAgent.GetContext()` (`py4gw/context/gw_context.py:87-152`). This reader takes the
client's own `read_*` route because it is the one route all twelve keys have, and it is the route
`data_map`'s character-info snippet already uses.
"""

from __future__ import annotations

from typing import Any

from ..client import require_client

#: ``{GwAu3 key: reader}`` for the twelve keys whose case is one pointer read of the game context.
#: Written as readers rather than as field names, because this project reaches no field through a
#: dynamic name. The order is GwAu3's own ``Switch`` order (``GwAu3_Data_Game.au3:15-51``), less the
#: three keys whose case is not a single pointer read -- `GameLanguage`, `SomeNumber` and `IsCinematic`,
#: which are branched on in the accessor below.
_CONTEXT_KEYS: dict[str, Any] = {
    "AgentContext": lambda client: client.read_acc_agent_context(),
    "MapContext": lambda client: client.read_map_context(),
    "TextParser": lambda client: client.read_text_parser(),
    "AccountContext": lambda client: client.read_account_context(),
    "WorldContext": lambda client: client.read_world_context(),
    "Cinematic": lambda client: client.read_cinematic_context(),
    "GadgetContext": lambda client: client.read_gadget_context(),
    "GuildContext": lambda client: client.read_guild_context(),
    "ItemContext": lambda client: client.read_item_context(),
    "CharContext": lambda client: client.read_char_context(),
    "PartyContext": lambda client: client.read_party_context(),
    "TradeContext": lambda client: client.read_trade_context(),
}


def Game_GetGameContextPtr() -> Any:
    """The game context itself (``GwAu3_Data_Game.au3:4-8``).

    **GwAu3's body is one read**: ``Memory_ReadPtr($g_p_BasePointer, [0, 0x18], "ptr")`` (`:5-6`), whose
    element ``[1]`` is answered (`:7`) -- the *address* of the game context, the root whose slots the
    twelve keys above resolve, which is why this file is where it lives. This answers **the record** that
    address holds, through this project's own member: `py4gw.client.ConnectedClient.read_game_context`
    (``py4gw/client.py:1308``, on the class at ``:205``) over `GameContextStruct`
    (`py4gw/context/game_context.py:19`, its ``0x5C`` size asserted at ``:98``). This layer hands out no
    client address under any name -- the shape `Agent_GetAgentPtr`, `Item_GetItemPtr` and
    `World_GetWorldContextPtr` (`py4gw/gwa3/data_world.py:429`) already record.

    **The one divergence is the broken chain.** GwAu3's ``Memory_ReadPtr`` answers ``[0, 0]`` the moment
    a hop dereferences to ``0`` (`GwAu3_Core_Memory.au3:48-51`), so a client whose base context or game
    context is null answers ``0`` there. This project's reader raises at each of those two points instead
    (`GameContext._read_context_address`, `py4gw/context/game_context.py:156-171`), and nothing here
    swallows that: a caller is told the chain is null rather than handed a zero it could not tell from a
    context. A caller with **no connection** raises through this layer's own `require_client`
    (``py4gw/client.py:1937``), where GwAu3 answers ``0`` -- the divergence `Game_GetGameInfo` states on
    its first guard.
    """

    return require_client().read_game_context()


def Game_GetGameInfo(info: str = "") -> Any:
    """One slot of the client's game context, by GwAu3's key name (``GwAu3_Data_Game.au3:10-55``).

    GwAu3's guard order is kept: an empty key answers ``0`` before anything is read (``:12``), and an
    unrecognised key answers ``0`` -- its ``Switch`` has no ``Case Else``, so control falls through to
    the ``Return 0`` at ``:54``.

    Three keys are the source's own arithmetic rather than a bare record, and each says what it is:

    * ``GameLanguage`` -- ``:22-24`` follows the text-parser pointer and reads a ``dword`` at ``+0x1d0``;
      this answers the port's ``language_id`` field of the record read at that same slot, which ctypes
      puts at exactly ``0x1D0`` (`py4gw/context/text_parser_context.py:119`, asserted at ``:158``).
    * ``SomeNumber`` -- ``:26-27`` reads the ``dword`` at ``+0x20``; this is the port's own ``some_number``
      field at that offset (`py4gw/context/game_context.py:38`), returned as an ``int``.
    * ``IsCinematic`` -- ``:35-38`` dereferences the cinematic pointer and tests the two words at ``+0x0``
      and ``+0x4``; this makes the same two tests over the port's `CinematicStruct`
      (`py4gw/context/cinematic_context.py:23-26`) rather than calling `Map.IsInCinematic`
      (`py4gw/map.py:408`), which reads only ``h0004`` (``:419``) and additionally gates on
      `Map.IsMapReady` (``:415``) -- a check GwAu3 does not make.

    Two divergences are stated rather than smoothed over:

    * GwAu3's first guard, ``$l_p_Ptr = 0`` (``:12``), is the *game-context* pointer; here a client that is
      not connected raises through this layer's own `require_client` (`py4gw/client.py:1937`) instead of
      answering ``0``, and a connected client whose slot holds no pointer answers ``0``.
    * ``CharContext`` is the one key that can raise where GwAu3 answers ``0``: the port's char-context
      reader treats a null slot as an error (`py4gw/context/char_context.py:449-450`), which is how the
      character-selection screen reads. The other eleven answer ``0`` as GwAu3 does.
    """

    if info == "":
        return 0

    if info == "GameLanguage":
        parser = require_client().read_text_parser()
        return 0 if parser is None else int(parser.language_id)

    if info == "SomeNumber":
        return int(require_client().read_game_context().some_number)

    if info == "IsCinematic":
        cinematic = require_client().read_cinematic_context()
        if cinematic is None:
            return False
        return bool(cinematic.h0000 != 0 or cinematic.h0004 != 0)

    reader = _CONTEXT_KEYS.get(info)
    if reader is None:
        return 0

    context = reader(require_client())
    return 0 if context is None else context

__all__ = ["Game_GetGameContextPtr", "Game_GetGameInfo"]
