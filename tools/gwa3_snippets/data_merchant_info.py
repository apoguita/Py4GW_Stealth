"""``GwAu3_Data_Merchant.au3``'s trader-quote reads, over this project's own merchant state.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

**These are not field-name accessors, and that is why they are transcribed rather than generated.** Every
generated family is one ``Switch`` over a field name, reached through an ``info: str = ""`` first
parameter -- and the generator emits that accessor for whatever family it is given. The nine functions
here take **no arguments at all** -- ``Func Merchant_GetLastTransaction()``
(``GwAu3_Data_Merchant.au3:3``), ``:8``, ``:12``, ``:16``, ``:20``, ``:28``, ``:34``, ``:89``, ``:93``
-- and none of them switches on anything, so there is no key for the generator's offset table to resolve,
no record for it to resolve one from, and an emitted accessor would carry a parameter GwAu3 does not
have. So this file is the body of a **hand-written** module, the route `py4gw/gwa3/data_friend.py` takes
for the same reason (``docs/GWA3_COMPAT_SPEC.md``: *the eighth and last read family, and it is
hand-written rather than generated*), and ``tools/gwa3_snippets/`` is where it lives because the layer
keeps hand-written source for a family there.

**The state behind them is GwAu3's own, and this layer answers each part of it from where this project
keeps that fact -- transcribed where nothing in the client holds it, read where this project reads the
same record.** ``$g_i_TraderQuoteID``, ``$g_i_TraderCostID`` and ``$g_f_TraderCostValue`` are four-byte
slots GwAu3's assembler allocates (``GwAu3_Core_Assembler.au3:1917-1919``) and its own ``TraderProc``
detour fills on the client's trader call (``:2033-2053``); ``$g_p_BuyItemBase`` and
``$g_p_SalvageGlobal`` are scan results (``GwAu3_Core.au3:241-242``); ``$g_i_LastTransactionType`` and
its three neighbours are plain AutoIt globals (``GwAu3_Const_Core.au3:109-112``). Fact by fact:

* the **two cost slots** are kept by `py4gw/listeners.py`'s `MerchantListener`: the quoted item id and
  the price the client's own ``ITEM_PRICE_QUOTE`` packet held (``:213-217``, ``:272-276``, over
  ``stoc.h:599-602``). `Merchant_GetTraderCostID` and `Merchant_GetTraderCostValue` answer from there.
* the **quote counter** is controller-side state with no client field behind it, and this project
  installs no trader detour -- nor may the layer reach back into the ported library to hook one, because
  the dependency runs one way only (``AGENTS.md``; `py4gw/gwa3/__init__.py:5-6`). So it is **derived
  from the quote this layer already reads** instead: `MerchantListener`, through
  `Trading.Trader.GetQuotedItemID` and `GetQuotedValue`, the same two readers the cost getters use. The
  number moves when the **standing** quote it observes changes, which is the change detector GwAu3's own
  callers poll (``GwAu3_Cmd_Merchant.au3:76``, ``:89``, ``:95``), and the reader states the divergence
  and its cost in one paragraph.
* the **last-transaction globals** are transcribed verbatim (``_LAST_TRANSACTION``).
* ``$g_p_SalvageGlobal`` holds the item and the kit of a salvage in flight; this project reads the same
  facts from the client's own salvage session (`ConnectedClient.read_salvage_session`,
  ``py4gw/context/salvage_context.py:39-77``), so `Merchant_GetSalvageGlobal` answers that item id
  rather than the address.

**One member still refuses, and it names the read it is missing.** ``$g_p_BuyItemBase`` is a client
address this project resolves no pattern for and reads no record through; `Merchant_GetBuyItemBase`
carries that finding. It is *not* the merchant's item array -- that is
``Merchant_GetMerchantItemsBase``'s value, and the data a caller reads through it is answered by the two
offered-item readers of `py4gw/gwa3/cmd_merchant.py`.
"""

__all__ = [
    "Merchant_ClearTraderQuote",
    "Merchant_GetBuyItemBase",
    "Merchant_GetLastTransaction",
    "Merchant_GetSalvageGlobal",
    "Merchant_GetTraderCostID",
    "Merchant_GetTraderCostValue",
    "Merchant_GetTraderQuoteID",
    "Merchant_GetTraderQuoteInfo",
    "Merchant_IsValidQuote",
]

#: ``GwAu3_Const_Core.au3:109-112`` -- GwAu3's own four "last transaction" globals, carrying the values
#: that file declares them with: the type ``-1`` and the item id, quantity and price ``0``.
#: ``Core_ResetRuntime`` sets them to the same four values (``GwAu3_Core.au3:699-702``), and **nothing
#: else in GwAu3's own source writes them** -- neither ``Merchant_BuyItem``
#: (``GwAu3_Cmd_Merchant.au3:42-160``) nor ``Merchant_SellItem`` (``:161-244``), whose reads of the
#: trader slots are the only merchant state they touch.
#:
#: Mutable, the way GwAu3's own globals are: a layer routine that drives a transaction has the same four
#: slots to record into that GwAu3 declares, and this is the module that reads them.
_LAST_TRANSACTION: list[int] = [-1, 0, 0, 0]


def Merchant_GetLastTransaction() -> list[int]:
    """The last transaction, as GwAu3's own four-element array (``GwAu3_Data_Merchant.au3:3-6``).

    GwAu3 builds ``[type, itemID, quantity, price]`` from the four globals above and hands back that
    **local** array (``Local $l_ai_Result[4]``, ``:4``) rather than the globals themselves, so a caller
    that writes into it changes nothing. This answers a copy for the same reason.

    **Both sides answer the same four values, and that is a fact about the source rather than a
    shortfall here**: nothing in GwAu3's own source writes those globals after the runtime reset, so
    GwAu3's answer is the constant ``[-1, 0, 0, 0]`` -- *no transaction* -- however many trades ran. The
    reader is transcribed with the source's own initial values so that a layer routine which drives a
    transaction records into the same four slots GwAu3 declares, instead of this answering ``0`` or
    refusing where the source answers an array.
    """

    return list(_LAST_TRANSACTION)


#: ``GwAu3_Core.au3:432`` -- ``$g_i_TraderQuoteID``, transcribed as this layer's own state, with the
#: value GwAu3's own block initialises it to (``0``).
#:
#: **This is GwAu3's own controller-side slot, not client memory**, which is why it is transcribed
#: rather than read: the block declares it as a four-byte slot (``GwAu3_Core_Assembler.au3:1917``) and
#: its ``TraderProc`` detour increments it on every client trader call, wrapping back to ``0`` at
#: ``200`` (``:2045-2051``). Nothing in the client holds it, and this project installs no such detour --
#: and **the layer never reaches back into the ported library to hook one**, because the dependency runs
#: one way only (``AGENTS.md``, ``py4gw/gwa3/__init__.py:5-6``). So the count is not taken from client
#: trader calls; it is **derived from the quote this layer already reads**, in the reader below.
g_i_TraderQuoteID: int = 0

#: The standing quote the counter above was last advanced for, as ``[item id, value]``.
_LAST_QUOTE_SEEN: list[int] = [0, 0]

#: GwAu3's own wrap: ``inc eax`` / ``cmp eax,200`` / ``jnz`` / ``xor eax,eax`` / ``mov [slot],eax``
#: (``GwAu3_Core_Assembler.au3:2046-2051``). Kept so the number stays in the slot's own ``0``..``199``
#: range rather than growing without bound.
_TRADER_QUOTE_ID_WRAP = 200


def Merchant_GetTraderQuoteID() -> int:
    """The quote's change detector, read from the quote this layer sees (``GwAu3_Data_Merchant.au3:8-10``).

    GwAu3 answers ``Memory_Read($g_i_TraderQuoteID, 'dword')`` -- a slot inside its own injected block
    (``GwAu3_Core_Assembler.au3:1917``) that its ``TraderProc`` detour advances on the client's trader
    call, wrapping at ``200`` (``:2045-2051``). A script's whole use of it is as a **change detector**:
    read it, request the quote, poll until it moves (``GwAu3_Cmd_Merchant.au3:76``, ``:89``, ``:95``).

    **One divergence, and it is the mechanism -- the value serves that caller the same way.** This
    project installs no trader detour and the layer never hooks the ported library to borrow one, so the
    count cannot come from client trader calls. It is **derived from the quote the layer already reads**:
    the port's `MerchantListener`, through `Trading.Trader.GetQuotedItemID` and `GetQuotedValue` -- the
    same two readers `Merchant_GetTraderCostID` and `Merchant_GetTraderCostValue` answer from. The
    counter advances when a **standing** quote (item id and value both positive, which is GwAu3's own
    test, ``GwAu3_Data_Merchant.au3:31``) differs from the last one this reader saw, and it holds still
    while no quote stands -- so the ``-1`` a reset writes, and the previous item id it leaves behind,
    leave it alone, which is what makes the *read, request, poll* loop end on a real quote rather than
    on the request itself. ``0`` before the first standing quote, which is GwAu3's own start value.

    **The cost of deriving it, stated** -- a repeat quote of the same item at the same price is the same
    observed quote and does not move this number, where GwAu3's call-counting slot would advance; the
    value only carries "has the quote changed since I read it", which is the whole of its use in GwAu3.
    """
    global g_i_TraderQuoteID

    from ..merchant import Trading

    cost_id = int(Trading.Trader.GetQuotedItemID())
    cost_value = int(Trading.Trader.GetQuotedValue())

    if cost_id > 0 and cost_value > 0 and [cost_id, cost_value] != _LAST_QUOTE_SEEN:
        _LAST_QUOTE_SEEN[0] = cost_id
        _LAST_QUOTE_SEEN[1] = cost_value
        g_i_TraderQuoteID += 1
        if g_i_TraderQuoteID == _TRADER_QUOTE_ID_WRAP:
            g_i_TraderQuoteID = 0

    return int(g_i_TraderQuoteID)


def Merchant_GetTraderCostID() -> int:
    """The last quoted item id (``GwAu3_Data_Merchant.au3:12-14``).

    GwAu3 reads its own slot, which its detour fills with the **first dword of the structure the client's
    trader routine carries** (``mov eax,dword[ebx+28]`` then ``mov eax,[eax]``,
    ``GwAu3_Core_Assembler.au3:2035-2037``); this answers the port's
    `MerchantListener`, filled from the client's own ``ITEM_PRICE_QUOTE`` packet -- the ``itemid`` that
    packet carries at ``+4`` (``py4gw/listeners.py:213-217``, ``:272-276``, over ``stoc.h:599-602``) --
    because that is where this project keeps the same fact. The divergence is the mechanism and not the
    value: GwAu3 snapshots a client call into a slot its own assembler owns, this reads the listener the
    port installs in the client's place, and both answer ``0`` before any quote.
    """

    from ..merchant import Trading

    return int(Trading.Trader.GetQuotedItemID())


def Merchant_GetTraderCostValue() -> int:
    """The last quoted value (``GwAu3_Data_Merchant.au3:16-18``).

    The same structure's second dword (``mov eax,[eax+4]``): GwAu3's detour fills
    ``$g_f_TraderCostValue`` from it (``GwAu3_Core_Assembler.au3:2038-2040``) and this function reads the
    slot back as a ``dword`` (``:17``), which is why the ``$g_f_`` prefix in its own name is not a
    float; this answers the listener's own quoted value, taken from the same packet's price
    (`Trading.Trader.GetQuotedValue`, ``py4gw/merchant.py:503-507``).

    **One divergence, and it is the port's own sentinel.** GwAu3 zeroes both slots before it sends a
    quote request (``GwAu3_Core_Assembler.au3:2309-2310``) and again when a caller clears them
    (``GwAu3_Data_Merchant.au3:35-36``), while this port's own reset writes ``-1``
    (`MerchantListener.ResetQuote`, ``py4gw/listeners.py:206-209``) -- the *no quote yet* value native's
    listener declares (``listeners.h:56-59``). The ordering is the same on both sides, because
    `Trading.Trader.RequestQuote` calls that reset *before* it asks (``py4gw/merchant.py:316``) exactly
    where GwAu3's command zeroes the slots; only the sentinel differs. So after a reset this answers
    ``-1`` where GwAu3 answers ``0``; `Merchant_IsValidQuote` reads both as "not a quote", and that is
    the only test GwAu3's own callers make of it.
    """

    from ..merchant import Trading

    return int(Trading.Trader.GetQuotedValue())


def Merchant_GetTraderQuoteInfo() -> list[int]:
    """The three trader-quote words, as GwAu3's own array (``GwAu3_Data_Merchant.au3:20-26``).

    GwAu3 builds ``[quoteID, costID, costValue]`` from its three slots, one ``Memory_Read`` each
    (``:22-24``), and hands back the three-element array. This answers the same three values from the
    same three members the getters above answer from -- the derived change detector, the listener's
    quoted item id and the listener's quoted value -- in GwAu3's own order, so element ``0`` is the
    number a caller polls for change (``GwAu3_Cmd_Merchant.au3:76``, ``:89``, ``:95``).
    """

    return [
        Merchant_GetTraderQuoteID(),
        Merchant_GetTraderCostID(),
        Merchant_GetTraderCostValue(),
    ]


def Merchant_IsValidQuote() -> bool:
    """Whether a quote is standing (``GwAu3_Data_Merchant.au3:28-32``).

    GwAu3's own two reads and its own test, in its own order: the cost id, then the cost value, then
    ``cost id > 0 And cost value > 0`` (``:29-31``). Both values come from the same two routed members
    the getters above answer from, so the boolean is the source's own arithmetic over the port's state --
    including its answer for the states that matter: no quote yet is ``False`` on both sides, and a
    quote is ``True`` on both.
    """

    from ..merchant import Trading

    cost_id = int(Trading.Trader.GetQuotedItemID())
    cost_value = int(Trading.Trader.GetQuotedValue())
    return cost_id > 0 and cost_value > 0


def Merchant_ClearTraderQuote() -> None:
    """Clear the standing quote (``GwAu3_Data_Merchant.au3:34-38``).

    GwAu3 writes ``0`` into its own two slots (``:35-36``) and logs a debug line through
    ``$g_h_EditText`` (``:37``). This answers with the port's own reset of the same state --
    `MerchantListener.ResetQuote` (``py4gw/listeners.py:206-209``), the member
    `Trading.Trader.RequestQuote` itself calls before it asks for a quote (``py4gw/merchant.py:316``) --
    which is a write to this layer's own listener and never a write into the client.

    **Two divergences, both visible to a caller, and neither is a reason to refuse the clear.** The reset
    moves the quoted *value* to the port's ``-1`` sentinel rather than to ``0``, and it does **not** clear
    the quoted *item id*, because no member here does: after a clear `Merchant_GetTraderCostID` still
    answers the previous quote's id where GwAu3 answers ``0`` (``Merchant_GetTraderCostValue`` records the
    same sentinel on its own member). And the debug line is not made -- this layer has no ``Log_*`` route
    (``docs/GWA3_ROUTE_MAP.md``) and ``$g_h_EditText`` is GwAu3's own control. GwAu3's own return is the
    implicit ``0`` of a routine with no ``Return`` (``:34-38``); this answers ``None``, which is what the
    layer's other no-``Return`` routines answer (``Party_AcceptInvitation``,
    ``py4gw/gwa3/cmd_party.py:226-234``, whose docstring records the same rule).
    """

    from ..listeners import Merchant

    Merchant().ResetQuote()


def Merchant_GetBuyItemBase() -> int:
    """**Refused, and the missing read is named: this project resolves no ``BuyItemBase``.**

    ``GwAu3_Data_Merchant.au3:89-91`` answers ``$g_p_BuyItemBase``, the pointer ``GwAu3_Core.au3:241``
    reads out of its own scan of the client's code (``:91``). What that address *is* can be stated
    exactly, because GwAu3's own use of it is one line: its merchant buy writes the value into field 5
    of its buy record (``GwAu3_Cmd_Merchant.au3:151``) -- a field its injected ``CommandBuyItem`` stub
    loads into ``esi`` and never passes to the client (``GwAu3_Core_Assembler.au3:2243-2263``; the
    call's nine words come from fields 2, 3 and 4). So the value is a client global the client's own
    buy path uses, and **this project has no read for it**: `offsets/merchant.json` carries exactly two
    resolvers -- ``transact_item_func`` and ``request_quote_func`` -- and no pattern for a buy-item
    base, and the port's own buy path hands the client a request record placed in the game-thread
    block (`py4gw/merchant.py:189-196`) instead of a client structure. Answering ``0`` for an
    unresolved address would be a value a caller cannot tell from a real one, so this refuses and names
    the gap: a resolved ``BuyItemBase`` address *and* a named record for what it points at.

    **What a caller wanting the merchant's items should use instead is already routed**: the offered
    items are `Trading.Merchant.GetOfferedItems`, which `Merchant_GetMerchantItemsSize` and
    `Merchant_GetMerchantItemPtr` read (`py4gw/gwa3/cmd_merchant.py:47-85`).
    """

    raise NotImplementedError(
        "GwAu3_Data_Merchant.au3:89-91 answers `$g_p_BuyItemBase`, a client address GwAu3_Core.au3:241 "
        "resolves from its own scan of the client's code (:91); GwAu3's only use of it is a buy-record "
        "field its injected stub never passes to the client (GwAu3_Cmd_Merchant.au3:151, "
        "GwAu3_Core_Assembler.au3:2243-2263). This project resolves no such pattern "
        "(offsets/merchant.json carries only `transact_item_func` and `request_quote_func`) and reads no "
        "record through the address -- its own buy path places its request record in the game-thread "
        "block instead (py4gw/merchant.py:189-196). The missing reads are therefore named: a resolved "
        "`BuyItemBase` address and a named record for what it points at. The data a caller wants from "
        "the merchant is already routed: `Trading.Merchant.GetOfferedItems` over "
        "`Merchant_GetMerchantItemsSize`/`Merchant_GetMerchantItemPtr` "
        "(py4gw/gwa3/cmd_merchant.py:47-85)."
    )


def Merchant_GetSalvageGlobal() -> int:
    """The item a salvage session is holding (``GwAu3_Data_Merchant.au3:93-95``).

    GwAu3 answers ``$g_p_SalvageGlobal``, which ``GwAu3_Core.au3:242`` derives from its own scan
    (``:95``) -- a client global holding the two words its ``CommandSalvage`` stub writes before the
    client's own ``Salvage`` call: the item id at ``+0`` and the kit item id at ``+4``
    (``GwAu3_Core_Assembler.au3:2388-2401``; this project's own source review records the same, that
    the global is a write target and never read back for state -- ``docs/RESEARCH.md:2256-2258``).
    This layer hands out no client address, so the member answers the **data**: the item id of the
    client's own salvage session, `SalvageSessionInfoStruct.item_id`
    (``py4gw/context/salvage_context.py:76``), read through `ConnectedClient.read_salvage_session`
    (``py4gw/client.py:1344``) -- the same "which item is being salvaged" fact GwAu3's first word
    carries, and its sibling field is the kit id (``:77``). ``0`` when no salvage session is open,
    which is what GwAu3's own word amounts to before its stub writes it.

    **The divergence is the record, not the fact.** GwAu3's two words live in a client buffer its own
    injected stub fills for the call it is about to make; this reads the client's own session record,
    which the salvage popup publishes while it is open
    (`py4gw/context/salvage_context.py:98-154`). A caller that wanted a raw address has none here, by
    this layer's rule for every pointer-valued GwAu3 name.
    """

    from ..client import require_client

    session = require_client().read_salvage_session()
    if session is None:
        return 0
    return int(session.item_id)