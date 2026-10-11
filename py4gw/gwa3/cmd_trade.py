"""GwAu3's ``Trade_*`` actions: three spellings of a trade, none of them routable.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

**All eighteen refuse, and the module records which of three mechanisms each one refuses by**, because
a migrating script's trade code is not one thing:

* **The packet spellings** -- the ones with a trailing underscore (``Trade_InitiateTrade_``,
  ``Trade_AcceptTrade_`` …) -- forge a header through ``Core_SendPacket``. This project forges no
  packets.
* **The plain spellings** are GwAu3's *native* route, and each one goes through ``Trade_CallSession``,
  which writes a record into the client's command queue with its injected stub and then polls two of
  GwAu3's own memory slots for the answer (``GwAu3_Cmd_Trade.au3:87-110``). Both halves are outside
  what this project does.
* **Two are GwAu3's own controller-side state**: ``Trade_InitTradePartner`` writes zero into
  ``$g_p_TradePartner`` and ``Trade_GetTradePartner`` reads it and clears it again
  (``:34-47``). There is no client behaviour in them at all, and their "read then clear" shape means
  **two calls never return the same value** -- a property a route would have to reproduce.

This project has no trade member: ``py4gw/`` has no trade module, so there is nothing to route to even
where the mechanism would allow it. The routes are named per function as the work.
"""

from __future__ import annotations

from typing import Any, NoReturn

__all__ = [
    "Trade_AcceptTrade",
    "Trade_AcceptTrade_",
    "Trade_CallSession",
    "Trade_CancelTrade",
    "Trade_CancelTrade_",
    "Trade_ChangeOffer_",
    "Trade_GetTradePartner",
    "Trade_InitTradePartner",
    "Trade_InitiateTrade",
    "Trade_InitiateTrade_",
    "Trade_OfferItem",
    "Trade_OfferItem_",
    "Trade_RevokeAccept",
    "Trade_RevokeItem",
    "Trade_RevokeOffer",
    "Trade_SubmitOffer",
    "Trade_SubmitOffer_",
    "Trade_WaitIdle",
]

#: The rule the packet spellings refuse by. One mechanism, nine rows.
_PACKET_RULE = (
    "GwAu3_Cmd_Trade.au3:{line} forges a trade header through `Core_SendPacket` -- the packet spelling "
    "of this action, which is why its name carries a trailing underscore. This project forges no "
    "packets under any name: every effect it reaches is a member of `py4gw/`'s own classes calling the "
    "client's own function (M1), its own UI message (M2) or its own frame message (M3), and "
    "`docs/GWA3_ROUTE_MAP.md` records which of those each effect gets."
)

#: The rule the plain spellings refuse by: GwAu3's injected stub plus its own result slots.
_SESSION_RULE = (
    "GwAu3_Cmd_Trade.au3:{line} reaches the effect through `Trade_CallSession`, which writes a record "
    "into the client's command queue with GwAu3's injected assembler stub and then polls "
    "`$g_p_TradeSessReady` / `$g_p_TradeSessResult` -- two of GwAu3's own memory slots "
    "(`GwAu3_Cmd_Trade.au3:87-110`). This project writes into no such queue and keeps no such slots, "
    "so neither half of the call can be reproduced. It also has no trade member at all: `py4gw/` has "
    "no trade module."
)

#: The rule for GwAu3's own trade-partner slot.
_SLOT_RULE = (
    "GwAu3_Cmd_Trade.au3:{line} reads and clears `$g_p_TradePartner`, a slot GwAu3 keeps in its own "
    "controller-side state rather than a client record. There is no client behaviour to route -- and "
    "note its shape: the read **clears the slot** (`:42`), so two calls never answer the same value. A "
    "route would have to reproduce that, and this project holds no such state to clear; `py4gw/` has no "
    "trade module at all, so there is not even a member to place it on."
)


def _refuse(name: str, line: int, rule: str, extra: str | None = None) -> NoReturn:
    """Refuse one function, citing its body line and the mechanism it refuses by.

    ``NoReturn`` rather than ``None``: the function never comes back, and saying so is what lets the
    callers above keep GwAu3's own return annotations -- `Trade_WaitIdle` is a ``bool`` in GwAu3 and
    stays one here, even though every path raises.
    """

    message = rule.format(line=line)
    if extra is not None:
        message += " " + extra
    raise NotImplementedError(message)


# -- the packet spellings (trailing underscore) ------------------------------------------------


def Trade_InitiateTrade_(agent: Any) -> None:
    """**REFUSED: the packet spelling.** ``HEADER_TRADE_INITIATE`` with the agent's id."""

    _refuse("Trade_InitiateTrade_", 5, _PACKET_RULE)


def Trade_AcceptTrade_() -> None:
    """**REFUSED: the packet spelling.** ``HEADER_TRADE_ACCEPT``, a bare four-byte header."""

    _refuse("Trade_AcceptTrade_", 10, _PACKET_RULE)


def Trade_SubmitOffer_(gold: Any = 0) -> None:
    """**REFUSED: the packet spelling.** ``HEADER_TRADE_SUBMIT_OFFER`` with the gold."""

    _refuse("Trade_SubmitOffer_", 15, _PACKET_RULE)


def Trade_CancelTrade_() -> None:
    """**REFUSED: the packet spelling.** ``HEADER_TRADE_CANCEL``, a bare header."""

    _refuse("Trade_CancelTrade_", 20, _PACKET_RULE)


def Trade_ChangeOffer_() -> None:
    """**REFUSED: the packet spelling.** ``HEADER_TRADE_CHANGE_OFFER``, a bare header."""

    _refuse("Trade_ChangeOffer_", 25, _PACKET_RULE)


def Trade_OfferItem_(item_id: Any, quantity: Any = 1) -> None:
    """**REFUSED: the packet spelling.** ``HEADER_TRADE_ADD_ITEM`` with an item *id* and a quantity.

    **It differs from its plain twin in argument kind**: this one takes an ``$a_i_ItemID`` while
    ``Trade_OfferItem`` takes an item and resolves the id itself. A migration that renames the call
    without changing the argument passes an id where a record is expected.
    """

    _refuse(
        "Trade_OfferItem_",
        30,
        _PACKET_RULE,
        extra=(
            "**And it takes an id where its plain twin takes an item**: `Trade_OfferItem_` is "
            "`($a_i_ItemID, $a_i_Quantity = 1)` and `Trade_OfferItem` is `($a_v_Item, $a_i_Qty = 1)`."
        ),
    )


# -- the plain spellings, which go through Trade_CallSession -----------------------------------


def Trade_InitiateTrade(agent: Any) -> None:
    """**REFUSED: the injected stub.** The plain spelling of ``Trade_InitiateTrade_``."""

    _refuse("Trade_InitiateTrade", 52, _SESSION_RULE)


def Trade_CancelTrade() -> None:
    """**REFUSED: the injected stub.** The plain spelling of ``Trade_CancelTrade_``."""

    _refuse("Trade_CancelTrade", 56, _SESSION_RULE)


def Trade_AcceptTrade() -> None:
    """**REFUSED: the injected stub.** The plain spelling of ``Trade_AcceptTrade_``."""

    _refuse("Trade_AcceptTrade", 64, _SESSION_RULE)


def Trade_SubmitOffer(gold: Any = 0) -> None:
    """**REFUSED: the injected stub.** The plain spelling of ``Trade_SubmitOffer_``."""

    _refuse("Trade_SubmitOffer", 71, _SESSION_RULE)


def Trade_OfferItem(item: Any, quantity: Any = 1) -> None:
    """**REFUSED: the injected stub.** The plain spelling, taking an item rather than an id."""

    _refuse("Trade_OfferItem", 78, _SESSION_RULE)


def Trade_CallSession(native: Any, arg1: Any = 0, arg2: Any = 0, timeout: Any = 250) -> bool:
    """**REFUSED: it *is* the injected stub and the result-slot poll.**

    This is the function the plain spellings call, so it is the mechanism itself rather than a use of
    it: ``GwAu3_Cmd_Trade.au3:87-110`` resolves one of GwAu3's own native pointers, checks GwAu3's own
    trade flags, writes a record into the client's command queue with ``Core_Enqueue``, sets
    ``$g_p_TradeSessReady`` to a pending code and polls it for the answer. Its guards are worth
    recording for whoever builds a route: a native pointer of ``0`` is ``@error`` 1, a trade pointer of
    ``0`` is 2, a trade that is not **active** is 4 -- with GwAu3's own comment explaining that calling
    the natives outside a session stores a pending code no acknowledgement clears, which then blocks
    every later call -- and a timeout is 3.
    """

    _refuse("Trade_CallSession", 100, _SESSION_RULE)


def Trade_WaitIdle(timeout: Any = 3000) -> bool:
    """**REFUSED: it polls GwAu3's own trade context.**

    ``GwAu3_Cmd_Trade.au3:113-120`` loops on ``Trade_GetTradeInfo("IsBusy")``, a reading of GwAu3's own
    trade context that this project does not hold. The loop itself is trivial; the value it waits on is
    the missing piece -- and guessing it would let a caller issue a trade action the client is not
    ready to accept, which is what the wait exists to prevent.
    """

    _refuse("Trade_WaitIdle", 116, _SESSION_RULE)


def Trade_RevokeItem(item: Any) -> bool:
    """**REFUSED: it guards on `Trade_WaitIdle` and then calls the session stub.**"""

    _refuse("Trade_RevokeItem", 125, _SESSION_RULE)


def Trade_RevokeOffer() -> bool:
    """**REFUSED: as ``Trade_RevokeItem``, for the submitted offer.**"""

    _refuse("Trade_RevokeOffer", 132, _SESSION_RULE)


def Trade_RevokeAccept() -> bool:
    """**REFUSED: as ``Trade_RevokeItem``, for the player's acceptance.**"""

    _refuse("Trade_RevokeAccept", 139, _SESSION_RULE)


# -- GwAu3's own trade-partner slot ------------------------------------------------------------


def Trade_InitTradePartner() -> None:
    """**NOT APPLICABLE: GwAu3's own controller-side slot.**

    ``GwAu3_Cmd_Trade.au3:34-37`` writes zero into ``$g_p_TradePartner`` -- a slot in GwAu3's own
    memory, not in the client -- so there is no client behaviour to route.
    """

    _refuse("Trade_InitTradePartner", 35, _SLOT_RULE)


def Trade_GetTradePartner() -> int:
    """**NOT APPLICABLE: GwAu3's own controller-side slot**, and it *clears* on read.

    ``GwAu3_Cmd_Trade.au3:39-47`` reads ``$g_p_TradePartner`` and then writes zero back, so the same
    slot never answers twice. That is GwAu3's own bookkeeping, not a client record.
    """

    _refuse("Trade_GetTradePartner", 42, _SLOT_RULE)
