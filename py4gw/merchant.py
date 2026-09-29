"""External port of Reforged's ``Py4GWCoreLib/Merchant.py`` and the ``PyMerchant`` binding behind it.

**The source file** is 197 lines and one class: **``Trading``**, with four nested namespaces —
``Trader`` (8 members), ``Merchant`` (3), ``Crafter`` (2), ``Collector`` (2) — and two of its own
(``merchant_instance`` and ``IsTransactionComplete``). **17 members.** Every one of them is
``Trading.merchant_instance().<binding method>()``, so the class is a thin facade over native's
``PyMerchant``.

**``PyMerchant`` is ported here too, and it is not an artifact.** Native's class
(``merchant_bindings.cpp:18-206``) is **stateless** — fifteen methods and no fields — so
``merchant_instance()`` is a real object of this port's own class, exactly as ``PyEffects`` is in
``py4gw/effect.py``. The binding is declared first, the way that file declares it, and ``Trading``
follows in the source's own member order.

**What each layer of the dependency is:**

| layer | state here |
| --- | --- |
| ``PyMerchant``'s fifteen methods (``merchant_bindings.cpp:216-232``) | **this file** |
| two of them need nothing | ``update`` is native's own no-op (*"legacy no-op - state refreshed by listeners"*, ``:205``), and ``get_trader_item_list2`` is native's own constant ``{}`` (*"legacy never populated"*, ``:200``) |
| ``GW::item::GetItemById`` | ported — ``py4gw/context/item_context.py`` |
| ``merchant.transact_item_func`` / ``merchant.request_quote_func`` | the catalog carries both (``offsets/merchant.json``), and the call form they need is ``CallForm.STACK_WORDS`` |
| ``GW::game_thread::Enqueue`` (four of the writes) | subsumed — this port's call path already runs on the client's thread |
| ``PY4GW::listeners::Merchant()`` | ported — ``py4gw/listeners.py``, over the packet handlers in ``py4gw/game_thread/packets.py`` |

**The merchant listener, and how it got here.** ``listeners.h:51-92`` holds five pieces of state
filled by **five StoC packet callbacks** (``listeners.cpp:96-128``): ``QuotedItemPrice`` → the quoted
id and value, ``TransactionDone`` → the complete flag, ``ItemStreamEnd`` → latch the world context's
merchant array when ``unk1 == 12``, ``WindowItems`` → the window's item list, and ``WindowItemsEnd``
(which changes no state). Native registers each by **replacing the client's own handler**
(``g_game_server_handlers->at(header).handler_func = &StoCHandler_Func``, ``stoc_methods.cpp:55-57``)
and keeps the original to chain to. This port does the same thing through its own layer: an emitted
stub per header (``payload.build_packet_stub``) placed by ``game_thread.packets``, the packet
travelling to the host as a ``PACKET`` event, and the listener dispatching by header.

**Two things a write does that the source does with a pointer into its own address space.** Native
hands the client `&item->item_id` — the live record's own field — and, for the crafter and collector,
`std::vector::data()` of lists it owns in-process. The first is an address the port can compute from
the item record it read; the second has to be placed in the block's data region, because a Python
list is not in the client. That region is exactly what it exists for: *"The source's own callers keep
those in their stack frames; this project has no frame in the client, so it keeps them here."*
"""

from __future__ import annotations

import struct
from typing import Any

from .game_thread.shared_block import CallForm, CommandRecord
from .listeners import Merchant

#: The resolver names the six write members reach (``offsets/merchant.json``). They are what
#: ``GW::merchant::TransactItems``/``RequestQuote`` call (``merchant_methods.cpp:16-30``): the
#: client's own functions, whose prototypes are
#: ``void __cdecl(TransactionType type, uint32_t gold_give, TransactionInfo give, uint32_t gold_recv,
#: TransactionInfo recv)`` and ``void __cdecl(TransactionType type, uint32_t unknown, QuoteInfo give,
#: QuoteInfo recv)``.
TRANSACT_ITEM_FUNC = "merchant.transact_item_func"
REQUEST_QUOTE_FUNC = "merchant.request_quote_func"

#: ``GW::Constants::TransactionType`` (``constants.h:169-180``), every value the merchant layer
#: names. Native passes one of these as the first argument of both calls.
MERCHANT_BUY = 0x1
COLLECTOR_BUY = 0x2
CRAFTER_BUY = 0x3
MERCHANT_SELL = 0xB
TRADER_BUY = 0xC
TRADER_SELL = 0xD

#: Where a transaction's own words are built, in the block's data region. Native builds its records
#: and its ``std::vector``s **in its own address space** and passes pointers into them, because the
#: call it enqueues happens in-process; a Python list is not in the client, so the two lists and the
#: record are placed here and their addresses handed over. The span is the region between the
#: dat reader's own block at ``0x000`` and the chat log at ``0x200``, which nothing else claims.
MERCHANT_OFFSET = 0x100

#: How many ingredient ids (and quantities) a crafter or collector call can carry. Native's
#: ``std::vector``s grow as far as the caller's list does and the block cannot, so this is the port's
#: own bound: 24 words of ids and 24 of quantities, then the nine-word transaction record, all inside
#: the ``0x100``-byte span. A longer list is refused and the refusal names the bound.
MAX_GIVE_ITEMS = 24

#: The three parts of that span, each addressed on its own because the client is handed its address.
GIVE_IDS_OFFSET = MERCHANT_OFFSET
GIVE_QUANTITIES_OFFSET = GIVE_IDS_OFFSET + 4 * MAX_GIVE_ITEMS
TRANSACTION_RECORD_OFFSET = GIVE_QUANTITIES_OFFSET + 4 * MAX_GIVE_ITEMS

#: The transaction record's own size: ``type``, ``gold_give``, three of ``give``, ``gold_recv`` and
#: three of ``recv`` (``SendMerchantTransactItemPacket``, ``ui.h:402-408``).
TRANSACTION_RECORD_WORDS = 9

#: One word the craft-style calls hand the client as ``recv.item_ids``: native passes ``&item_id``,
#: the address of the function's own parameter, and the client reads one id through it.
RECEIVED_ID_OFFSET = TRANSACTION_RECORD_OFFSET + 4 * TRANSACTION_RECORD_WORDS


class MerchantTransactionInfo:
    """``GW::Context::MerchantTransactionInfo`` (``ui.h:364-368``): three words, passed by value.

    ``item_ids`` and ``item_quantities`` are **target addresses**, exactly as native's ``uint32_t*``
    fields are: zero is native's own ``nullptr``, and anything else is an address inside the client.
    """

    def __init__(
        self, item_count: int = 0, item_ids: int = 0, item_quantities: int = 0
    ) -> None:
        self.item_count = item_count
        self.item_ids = item_ids
        self.item_quantities = item_quantities

    def words(self) -> list[int]:
        """Return the record's three words, in declaration order."""

        return [self.item_count, self.item_ids, self.item_quantities]


class MerchantQuoteInfo:
    """``GW::Context::MerchantQuoteInfo`` (``ui.h:370-374``): three words, passed by value."""

    def __init__(self, unknown: int = 0, item_count: int = 0, item_ids: int = 0) -> None:
        self.unknown = unknown
        self.item_count = item_count
        self.item_ids = item_ids

    def words(self) -> list[int]:
        """Return the record's three words, in declaration order."""

        return [self.unknown, self.item_count, self.item_ids]


def _live_item(item_id: int) -> int:
    """Return the live item record's address, or zero — native's ``GetItemById``.

    ``Item* GetItemById(uint32_t item_id)`` returns the record itself, and the two pointers native
    builds out of it are ``&item->item_id`` — the record's own field, *"not a copy"*, its comment
    says (``merchant_bindings.cpp:19-21``). ``item_id`` is that record's first field, so the field's
    address is the record's address.
    """

    from .client import require_client

    context = require_client().read_item_context()
    if context is None:
        return 0
    item = context.GetItemById(item_id)
    if item is None:
        return 0
    address = item.address
    if address is None:
        # A record read without an address is one no pointer can be built into, which is native's
        # own answer when its lookup comes back empty.
        return 0
    return int(address)


def _place_words(offset: int, words: list[int]) -> int:
    """Write words into the block's data region and return the address they now sit at.

    The port's answer to a pointer into the caller's own memory: the client is handed an address it
    can read, inside the block that exists for exactly this.
    """

    from .client import require_client

    payload = b"".join(struct.pack("<I", int(word)) for word in words)
    return require_client().bridge.write_data(offset, payload)


def _transact(
    transaction_type: int,
    gold_give: int,
    give: MerchantTransactionInfo,
    gold_recv: int,
    recv: MerchantTransactionInfo,
) -> bool:
    """``GW::merchant::TransactItems`` (``merchant_methods.cpp:16-22``).

    Native answers false when its function pointer is null and true once the call is enqueued; the
    port asks the catalog whether the function is there — the same question, asked of the thing that
    holds it — and returns true once the call has run.
    """

    from .client import require_client

    client = require_client()
    if not client.resolves(TRANSACT_ITEM_FUNC):
        return False

    words = [transaction_type, gold_give] + give.words() + [gold_recv] + recv.words()
    _place_words(TRANSACTION_RECORD_OFFSET, words)
    client.call_function(
        TRANSACT_ITEM_FUNC,
        CallForm.STACK_WORDS,
        TRANSACTION_RECORD_OFFSET,
        len(words),
    )
    return True


def _request_quote(
    transaction_type: int, give: MerchantQuoteInfo, recv: MerchantQuoteInfo
) -> bool:
    """``GW::merchant::RequestQuote`` (``merchant_methods.cpp:24-30``).

    The second argument is native's own ``0`` — its ``unknown`` word (``merchant_methods.cpp:26``).
    """

    from .client import require_client

    client = require_client()
    if not client.resolves(REQUEST_QUOTE_FUNC):
        return False

    words = [transaction_type, 0] + give.words() + recv.words()
    _place_words(TRANSACTION_RECORD_OFFSET, words)
    client.call_function(
        REQUEST_QUOTE_FUNC,
        CallForm.STACK_WORDS,
        TRANSACTION_RECORD_OFFSET,
        len(words),
    )
    return True


def _give_lists(give_item_ids: list[int], give_item_quantities: list[int]) -> list[int]:
    """Place an ingredient list and its quantities, and return the two addresses native passes.

    Native hands the client ``give_item_ids.data()`` and ``give_item_quantities.data()`` — pointers
    into vectors it owns (``merchant_bindings.cpp:156-157``, ``:180-181``) — and a **null** pointer
    for an empty list, which is its own ``empty() ? nullptr : data()``.
    """

    if len(give_item_ids) > MAX_GIVE_ITEMS:
        raise ValueError(
            f"a crafter or collector call carries at most {MAX_GIVE_ITEMS} ingredient ids; "
            f"{len(give_item_ids)} were given. Native's vector grows and this block does not."
        )
    if not give_item_ids:
        return [0, 0]
    ids = _place_words(GIVE_IDS_OFFSET, list(give_item_ids))
    quantities = (
        _place_words(GIVE_QUANTITIES_OFFSET, list(give_item_quantities))
        if give_item_quantities
        else 0
    )
    return [ids, quantities]


def _received_id(item_id: int) -> int:
    """Place the one id the craft-style calls receive, and return the address native passes.

    ``recv_info.item_ids = &item_id`` (``merchant_bindings.cpp:166``, ``:192``) is the address of the
    function's own parameter, on native's stack. The port has no frame in the client, so the word
    goes in the block's data region and that address is handed over — the same substitution the
    ingredient lists need, and the reason the region exists.
    """

    return _place_words(RECEIVED_ID_OFFSET, [item_id])


class PyMerchant:
    """The port of native's ``PyMerchant`` binding class (``merchant_bindings.cpp:18-206``).

    Fifteen methods and no state, declared in the binding's own order. The four write methods that
    guard on the item (``trader_buy_item``, ``trader_sell_item``, ``merchant_buy_item``,
    ``merchant_sell_item``) each fetch the live record and hand the client ``&item->item_id`` - the
    record's own id field, not a copy (``:20-24``) - and the two craft-style methods that do not
    guard at all are native's own asymmetry, kept.
    """

    # --- Trader (buy tab) ---

    def trader_buy_item(self, item_id: int, cost: int) -> bool:
        """``PyMerchant::TraderBuyItem`` (``merchant_bindings.cpp:27-46``).

        The guard, the reset, ``cost = cost * count`` with ``count`` always one, and the two records:
        nothing given, one received whose ``item_ids`` is the live record's own id field.
        """

        item = _live_item(item_id)
        count = 1
        if not item:
            return False

        Merchant().ResetTransaction()
        cost = cost * count
        give = MerchantTransactionInfo(0, 0, 0)
        recv = MerchantTransactionInfo(count, item, 0)
        return _transact(TRADER_BUY, cost, give, 0, recv)

    def trader_sell_item(self, item_id: int, price: int) -> bool:
        """``PyMerchant::TraderSellItem`` (``merchant_bindings.cpp:47-66``)."""

        item = _live_item(item_id)
        count = 1
        if not item:
            return False

        Merchant().ResetTransaction()
        price = price * count
        give = MerchantTransactionInfo(count, item, 0)
        recv = MerchantTransactionInfo(0, 0, 0)
        return _transact(TRADER_SELL, 0, give, price, recv)

    def trader_request_quote(self, item_id: int) -> bool:
        """``PyMerchant::TraderRequestQuote`` (``merchant_bindings.cpp:67-84``).

        The quote is asked for with the **buy** transaction type — native's own line
        (``:79``) — and the id travels in ``recv``.
        """

        item = _live_item(item_id)
        if not item:
            return False

        Merchant().ResetQuote()
        give = MerchantQuoteInfo(0, 0, 0)
        recv = MerchantQuoteInfo(0, 1, item)
        return _request_quote(TRADER_BUY, give, recv)

    def trader_request_sell_quote(self, item_id: int) -> bool:
        """``PyMerchant::TraderRequestSellQuote`` (``merchant_bindings.cpp:85-102``).

        The mirror of the one above: ``TraderSell``, and the id travels in ``give``.
        """

        item = _live_item(item_id)
        if not item:
            return False

        Merchant().ResetQuote()
        give = MerchantQuoteInfo(0, 1, item)
        recv = MerchantQuoteInfo(0, 0, 0)
        return _request_quote(TRADER_SELL, give, recv)

    # --- Merchant (materials / rune trader) ---

    def merchant_buy_item(self, item_id: int, cost: int) -> bool:
        """``PyMerchant::MerchantBuyItem`` (``merchant_bindings.cpp:105-124``)."""

        item = _live_item(item_id)
        count = 1
        if not item:
            return False

        Merchant().ResetTransaction()
        cost = cost * count
        give = MerchantTransactionInfo(0, 0, 0)
        recv = MerchantTransactionInfo(count, item, 0)
        return _transact(MERCHANT_BUY, cost, give, 0, recv)

    def merchant_sell_item(self, item_id: int, price: int) -> bool:
        """``PyMerchant::MerchantSellItem`` (``merchant_bindings.cpp:125-144``)."""

        item = _live_item(item_id)
        count = 1
        if not item:
            return False

        Merchant().ResetTransaction()
        price = price * count
        give = MerchantTransactionInfo(count, item, 0)
        recv = MerchantTransactionInfo(0, 0, 0)
        return _transact(MERCHANT_SELL, 0, give, price, recv)

    # --- Crafter ---

    def crafter_buy_item(
        self,
        item_id: int,
        cost: int,
        give_item_ids: list[int],
        give_item_quantities: list[int],
    ) -> bool:
        """``PyMerchant::CrafterBuyItems`` (``merchant_bindings.cpp:148-170``).

        Native's own asymmetry, kept: this one has **no** ``GetItemById`` guard and **no**
        ``Enqueue`` (``:146-147`` says so and points at ``py_merchant.h:69-96``), it refuses when the
        two lists differ in length, and its reset happens **before** the two pointers are taken
        (``:154`` then ``:156-157``) — where the collector below resets after them.
        """

        if len(give_item_ids) != len(give_item_quantities):
            return False
        Merchant().ResetTransaction()

        pointers = _give_lists(give_item_ids, give_item_quantities)
        give_info = MerchantTransactionInfo(
            len(give_item_ids), pointers[0], pointers[1]
        )
        recv_info = MerchantTransactionInfo(1, _received_id(item_id), 0)
        return _transact(CRAFTER_BUY, cost, give_info, 0, recv_info)

    # --- Collector ---

    def collector_buy_item(
        self,
        item_id: int,
        cost: int,
        give_item_ids: list[int],
        give_item_quantities: list[int],
    ) -> bool:
        """``PyMerchant::CollectorBuyItems`` (``merchant_bindings.cpp:173-196``)."""

        if len(give_item_ids) != len(give_item_quantities):
            return False

        pointers = _give_lists(give_item_ids, give_item_quantities)

        Merchant().ResetTransaction()

        give_info = MerchantTransactionInfo(
            len(give_item_ids), pointers[0], pointers[1]
        )
        recv_info = MerchantTransactionInfo(1, _received_id(item_id), 0)
        return _transact(COLLECTOR_BUY, cost, give_info, 0, recv_info)

    # --- State getters (delegate to listeners::Merchant singleton) ---

    def get_trader_item_list(self) -> list[int]:
        """``PyMerchant::GetTraderItems`` (``merchant_bindings.cpp:199``).

        Native's own crossed names: this one reads the listener's ``merch_items_``, the list
        ``ItemStreamEnd`` latches from the client's merchant array — not the window list.
        """

        return Merchant().GetMerchantItems()

    def get_trader_item_list2(self) -> list[int]:
        """``PyMerchant::GetTraderItems2`` (``merchant_bindings.cpp:200``).

        Native's own body is ``return {};`` with the comment *"legacy never populated"* - the list
        is a constant and always has been, so this member answers without the listener.
        """

        return []

    def get_merchant_item_list(self) -> list[int]:
        """``PyMerchant::GetMerchantItems`` (``merchant_bindings.cpp:201``).

        The other half of native's crossed names: this reads ``merchant_window_items_``, the list the
        ``WindowItems`` packets carry, with the listener's own one-second clear.
        """

        return Merchant().GetMerchantWindowItems()

    def get_quoted_value(self) -> int:
        """``PyMerchant::GetQuotedValue`` (``merchant_bindings.cpp:202``).

        ``-1`` is the *no quote yet* sentinel Python waits on (``listeners.h:56-59``), which is why
        the listener's field is signed.
        """

        return Merchant().GetQuotedValue()

    def get_quoted_item_id(self) -> int:
        """``PyMerchant::GetQuotedItemID`` (``merchant_bindings.cpp:203``)."""

        return Merchant().GetQuotedItemId()

    def is_transaction_complete(self) -> bool:
        """``PyMerchant::IsTransactionComplete`` (``merchant_bindings.cpp:204``)."""

        return Merchant().IsTransactionComplete()

    def update(self) -> None:
        """``PyMerchant::Update`` (``merchant_bindings.cpp:205``).

        Native's body is ``{ /* legacy no-op - state refreshed by listeners */ }`` - the source does
        nothing here, so neither does this, and that is the port rather than a divergence.
        """


class Trading:
    """The port of Reforged's ``Merchant.py``: the class the file declares.

    The file is named ``Merchant.py`` and the class inside it is ``Trading``; this port keeps both
    spellings, as it keeps ``PyMerchant`` for the binding.
    """

    @staticmethod
    def merchant_instance() -> PyMerchant:
        """Create an instance of a Merchant object. (``Merchant.py:7-14``)

        Native's ``PyMerchant`` holds no state, so this is the object itself and not a stand-in.
        """

        return PyMerchant()

    @staticmethod
    def IsTransactionComplete() -> bool:
        """Check if the transaction is complete. (``Merchant.py:17-24``)"""

        return Trading.merchant_instance().is_transaction_complete()

    class Trader:
        @staticmethod
        def GetQuotedItemID() -> int:
            """Retrieve the quoted item ID from the merchant. (``Merchant.py:28-35``)"""

            return Trading.merchant_instance().get_quoted_item_id()

        @staticmethod
        def GetQuotedValue() -> int:
            """Retrieve the quoted value from the merchant. (``Merchant.py:38-45``)"""

            return Trading.merchant_instance().get_quoted_value()

        @staticmethod
        def GetOfferedItems() -> list[int]:
            """Retrieve the offered items from the Trader. (``Merchant.py:49-56``)"""

            return Trading.merchant_instance().get_trader_item_list()

        @staticmethod
        def GetOfferedItems2() -> list[int]:
            """Retrieve the offered items from the Trader. (``Merchant.py:60-67``)"""

            return Trading.merchant_instance().get_trader_item_list2()

        @staticmethod
        def RequestQuote(item_id: int) -> None:
            """Request a quote from the merchant. (``Merchant.py:70-77``)"""

            Trading.merchant_instance().trader_request_quote(item_id)

        @staticmethod
        def RequestSellQuote(item_id: int) -> None:
            """Request a sell quote from the merchant. (``Merchant.py:80-87``)"""

            Trading.merchant_instance().trader_request_sell_quote(item_id)

        @staticmethod
        def BuyItem(item_id: int, cost: int) -> None:
            """Buy an item from the merchant. (``Merchant.py:90-99``)"""

            Trading.merchant_instance().trader_buy_item(item_id, cost)

        @staticmethod
        def SellItem(item_id: int, cost: int) -> None:
            """Sell an item to the merchant. (``Merchant.py:102-111``)"""

            Trading.merchant_instance().trader_sell_item(item_id, cost)

    class Merchant:
        @staticmethod
        def BuyItem(item_id: int, cost: int) -> None:
            """Buy an item from the merchant. (``Merchant.py:115-124``)"""

            Trading.merchant_instance().merchant_buy_item(item_id, cost)

        @staticmethod
        def SellItem(item_id: int, cost: int) -> None:
            """Sell an item to the merchant. (``Merchant.py:127-136``)"""

            Trading.merchant_instance().merchant_sell_item(item_id, cost)

        @staticmethod
        def GetOfferedItems() -> list[int]:
            """Retrieve the offered items from the merchant. (``Merchant.py:140-147``)"""

            return Trading.merchant_instance().get_merchant_item_list()

    class Crafter:
        @staticmethod
        def CraftItem(
            item_id: int,
            cost: int,
            item_list: list[int],
            item_quantities: list[int],
        ) -> None:
            """Craft an item. (``Merchant.py:151-161``)"""

            Trading.merchant_instance().crafter_buy_item(
                item_id, cost, item_list, item_quantities
            )

        @staticmethod
        def GetOfferedItems() -> list[int]:
            """Retrieve the offered items from the merchant. (``Merchant.py:165-172``)"""

            return Trading.merchant_instance().get_merchant_item_list()

    class Collector:
        @staticmethod
        def ExchangeItem(
            item_id: int,
            cost: int = 0,
            item_list: list[int] = [],
            item_quantities: list[int] = [],
        ) -> None:
            """Exchange an item. (``Merchant.py:176-186``)

            The source's own defaults - including the two mutable ones, which are ported as written
            rather than tidied into ``None`` sentinels.
            """

            Trading.merchant_instance().collector_buy_item(
                item_id, cost, item_list, item_quantities
            )

        @staticmethod
        def GetOfferedItems() -> list[int]:
            """Retrieve the offered items from the merchant. (``Merchant.py:190-197``)"""

            return Trading.merchant_instance().get_merchant_item_list()


__all__ = ["Trading", "PyMerchant"]
