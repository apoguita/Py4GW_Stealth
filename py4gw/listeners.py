"""Port of Native's listeners (``include/listeners/listeners.h``, ``src/listeners/listeners.cpp``).

A listener is a named piece of state filled from the client's own events, switched on and off as a
unit: ``Enable`` installs whatever it watches, ``Disable`` takes it out, and both are idempotent
(``listeners.cpp:29-55``). **This module carries the base class and the merchant listener** — the one
``Trading`` waits on — in the source's own order. Native declares fourteen listeners in its registry
(``listeners.cpp:145-166``); the other thirteen are their own classes in their own units and are not
declared here, exactly as ``py4gw/routines_src/Checks.py`` declares one of ``Checks``' eight
namespaces.

**``MerchantListener`` is where the merchant's state lives.** Its five pieces are filled by five StoC
packet callbacks (``listeners.cpp:96-128``), and native registers each by *replacing the client's own
handler* for that header. In this port the replacing is ``game_thread.packets``' job, the packet
travels to the host as a ``PACKET`` event carrying the header and that header's own words, and the
dispatch below is by header — which is what ``g_packet_entries[packet->header]`` does in native
(``stoc.cpp:80``).

**Every handler runs on the event listener's thread**, which is the port's own consequence: native's
callbacks run inside the client, on whatever thread dispatched the packet, and this side has a single
thread that drains the event region. So the state below is written by that thread and read by
whoever asks; a Python list and three scalars, replaced and cleared whole, with the source's own
order kept.
"""

from __future__ import annotations

from .game_thread.shared_block import EventKind, EventRecord
from .timer import Timer

#: The StoC headers this listener replaces, as native's packet names them. Their values are
#: ``GW/common/opcodes.h``'s, which is where native reads them:
#:
#: * ``GAME_SMSG_WINDOW_ADD_ITEMS (0x0084)``
#: * ``GAME_SMSG_WINDOW_ITEMS_END (0x0085)``
#: * ``GAME_SMSG_WINDOW_ITEM_STREAM_END (0x0086)``
#: * ``GAME_SMSG_TRANSACTION_DONE (0x00CC)``
#: * ``GAME_SMSG_ITEM_PRICE_QUOTE (0x00F7)``
#:
#: The rest of that header is not ported: it declares the whole server-to-client opcode space, and
#: nothing here reads any of it yet.
GAME_SMSG_WINDOW_ADD_ITEMS = 0x0084
GAME_SMSG_WINDOW_ITEMS_END = 0x0085
GAME_SMSG_WINDOW_ITEM_STREAM_END = 0x0086
GAME_SMSG_TRANSACTION_DONE = 0x00CC
GAME_SMSG_ITEM_PRICE_QUOTE = 0x00F7

#: What each replaced handler's stub copies, per header: the packet's own fields plus the header word
#: it starts with. The counts are the source's struct declarations, and they are what
#: ``stoc.h`` says each callback reads:
#:
#: * ``QuotedItemPrice``: ``itemid``, ``price`` (``stoc.h:599-602``) — **3**
#: * ``TransactionDone``: **nothing**; its callback reads no field at all, and the packet is recorded
#:   because its arrival is the whole signal (``listeners.cpp:103-107``) — **1**
#: * ``ItemStreamEnd``: ``unk1`` (``stoc.h:367-370``) — **2**
#: * ``WindowItems``: ``count``, ``item_ids[16]`` (``stoc.h:356-359``) — **18**
#: * ``WindowItemsEnd``: **nothing** (``stoc.h:362-365``, ``listeners.cpp:121-125``) — **1**
PACKET_WORDS: dict[int, int] = {
    GAME_SMSG_WINDOW_ADD_ITEMS: 18,
    GAME_SMSG_WINDOW_ITEMS_END: 1,
    GAME_SMSG_WINDOW_ITEM_STREAM_END: 2,
    GAME_SMSG_TRANSACTION_DONE: 1,
    GAME_SMSG_ITEM_PRICE_QUOTE: 3,
}

#: The buy tab's own identifier: ``OnItemStreamEnd`` latches the client's merchant array only for
#: ``unk1 == 12`` (``listeners.cpp:80-83``).
BUY_TAB = 12

#: How long the window-item list is left alone before a fresh stream clears it, in milliseconds
#: (``listeners.cpp:70``).
WINDOW_ITEM_THROTTLE_MS = 1000.0


class Listener:
    """``PY4GW::listeners::Listener`` (``listeners.h:18-46``): a named thing that switches on and off.

    ``Enable`` and ``Disable`` are idempotent and do nothing when the state already matches; the
    install and uninstall are the subclass's (``listeners.cpp:29-43``). ``EnabledByDefault`` is
    whether the module's own ``Initialize`` turns it on, and ``Update`` is for listeners that poll
    rather than react — the merchant listener reacts, so it keeps the base's no-op.
    """

    def __init__(self) -> None:
        self._enabled = False

    def Name(self) -> str:
        """Return the listener's name, which is how the runtime addresses it."""

        raise NotImplementedError

    def Enable(self) -> None:
        """Install and mark enabled, doing nothing when it is already enabled."""

        if self._enabled:
            return
        self.Install()
        self._enabled = True

    def Disable(self) -> None:
        """Uninstall and mark disabled, doing nothing when it is already disabled."""

        if not self._enabled:
            return
        self.Uninstall()
        self._enabled = False

    def SetEnabled(self, enabled: bool) -> None:
        """``Listener::SetEnabled`` (``listeners.cpp:45-51``)."""

        if enabled:
            self.Enable()
        else:
            self.Disable()

    def Toggle(self) -> None:
        """``Listener::Toggle`` (``listeners.cpp:53-55``)."""

        self.SetEnabled(not self._enabled)

    def IsEnabled(self) -> bool:
        """``Listener::IsEnabled`` (``listeners.h:27``)."""

        return self._enabled

    def EnabledByDefault(self) -> bool:
        """``Listener::EnabledByDefault`` (``listeners.h:32``): on unless a subclass opts out."""

        return True

    def Update(self, delta_ms: float = 0.0) -> None:
        """``Listener::Update`` (``listeners.h:39``): the base does nothing."""

    def Install(self) -> None:
        """Install what this listener watches. The subclass's."""

        raise NotImplementedError

    def Uninstall(self) -> None:
        """Take out what :meth:`Install` placed. The subclass's."""

        raise NotImplementedError


class MerchantListener(Listener):
    """``PY4GW::listeners::MerchantListener`` (``listeners.h:51-92``).

    Five pieces of state — the quoted id and value, the transaction flag, the window's items and the
    merchant's — and four handlers that fill them. ``GetQuotedValue``'s ``-1`` is the source's own
    sentinel for *no quote yet*, and it is why the member is an ``int`` there and not unsigned
    (``listeners.h:56-59``): the port keeps the same arithmetic.
    """

    def __init__(self) -> None:
        super().__init__()
        self._quoted_item_id = 0
        self._quoted_value = 0
        self._transaction_complete = False
        self._merchant_window_items: list[int] = []
        self._merch_items: list[int] = []
        self._reset_merchant_window_item = Timer()
        #: The connection this listener installed onto, so taking it out does not have to ask which
        #: client is current — the connection that is closing is the one it belongs to.
        self._installed_on: object | None = None
    # -- what the state is -------------------------------------------------

    def Name(self) -> str:
        """``MerchantListener::Name`` (``listeners.h:53``)."""

        return "merchant"

    def GetQuotedItemId(self) -> int:
        """``listeners.h:55``."""

        return self._quoted_item_id

    def GetQuotedValue(self) -> int:
        """``listeners.h:59``: ``-1`` is *no quote yet*, which Python waits on."""

        return self._quoted_value

    def IsTransactionComplete(self) -> bool:
        """``listeners.h:60``."""

        return self._transaction_complete

    def GetMerchantWindowItems(self) -> list[int]:
        """``listeners.h:61``: the ids the ``WindowItems`` packets carried."""

        return list(self._merchant_window_items)

    def GetMerchantItems(self) -> list[int]:
        """``listeners.h:62``: the ids the client's own merchant array held at stream end."""

        return list(self._merch_items)

    def ResetTransaction(self) -> None:
        """``listeners.h:67``: what every buy/sell/craft/collect does before it transacts.

        Native's own comment says why it exists: *"Legacy did these inline at the top of every
        PyMerchant buy/sell/craft/collect + quote method; without them the flags latch and every
        subsequent wait short-circuits on stale state."*
        """

        self._transaction_complete = False

    def ResetQuote(self) -> None:
        """``listeners.h:68``."""

        self._quoted_value = -1

    # -- what it fills the state from --------------------------------------

    def OnPriceReceived(self, item_id: int, price: int) -> None:
        """``listeners.cpp:59-62``."""

        self._quoted_item_id = item_id
        self._quoted_value = int(price)

    def OnTransactionComplete(self) -> None:
        """``listeners.cpp:64-66``."""

        self._transaction_complete = True

    def OnNormalMerchantItemsReceived(self, item_ids: list[int], count: int) -> None:
        """``listeners.cpp:68-78``: append the ids, clearing the list at most once a second.

        The clear is guarded by the listener's own timer, and the timer is started with the install
        (``listeners.cpp:127``) — so the first stream after an install always clears, and a burst of
        packets inside the same second appends to what the first one left.
        """

        if self._reset_merchant_window_item.hasElapsed(WINDOW_ITEM_THROTTLE_MS):
            self._merchant_window_items.clear()
            self._reset_merchant_window_item.reset()

        for index in range(count):
            self._merchant_window_items.append(item_ids[index])

    def OnItemStreamEnd(self, unk1: int) -> None:
        """``listeners.cpp:80-94``: latch the client's merchant array when the buy tab ends.

        Native reads ``GW::Context::GetMerchantItemsArray()`` — the world context's ``merch_items``,
        which is ``nullptr`` unless the array is valid (``context_methods.cpp:219-222``) — clears the
        list unconditionally, and pushes whatever the array holds.
        """

        if unk1 != BUY_TAB:
            return

        from .client import require_client

        world = require_client().read_world_context()
        items = None if world is None else world.merch_items
        self._merch_items.clear()
        if items:
            for item_id in items:
                self._merch_items.append(int(item_id))

    # -- the five packet callbacks -----------------------------------------

    def OnPacket(self, event: EventRecord) -> None:
        """Dispatch one recorded packet by its header, as ``g_packet_entries[header]`` does.

        The words are the packet's own, copied inside the client because a packet is the client's
        buffer and is reused (``game_thread/packets.py``). Each branch reads the fields its source
        callback reads, at the offsets that packet's struct declares.
        """

        header = event.sequence
        words = event.words

        if header == GAME_SMSG_ITEM_PRICE_QUOTE:
            # PacketStoCQuotedItemPrice: itemid at +4, price at +8 (stoc.h:599-602), after the
            # header word the copy starts at. listeners.cpp:99-101.
            self.OnPriceReceived(words[1], words[2])
            return

        if header == GAME_SMSG_TRANSACTION_DONE:
            # The callback reads no field of the packet at all (listeners.cpp:103-107).
            self.OnTransactionComplete()
            return

        if header == GAME_SMSG_WINDOW_ITEM_STREAM_END:
            # PacketStoCItemStreamEnd: unk1 at +4 (stoc.h:367-370). listeners.cpp:109-113.
            self.OnItemStreamEnd(words[1])
            return

        if header == GAME_SMSG_WINDOW_ADD_ITEMS:
            # PacketStoCWindowItems: count at +4, item_ids[16] at +8 (stoc.h:356-359).
            # listeners.cpp:115-119 passes `pak->item_ids` and `pak->count`.
            self.OnNormalMerchantItemsReceived(list(words[2:]), words[1])
            return

        if header == GAME_SMSG_WINDOW_ITEMS_END:
            # Stream-end hook retained for parity; no state change (listeners.cpp:121-125).
            return

    # -- install and uninstall ---------------------------------------------

    def Install(self) -> None:
        """``listeners.cpp:96-128``: register the five packet callbacks, and start the timer.

        Native registers one callback per header through ``GW::StoC::RegisterPacketCallback``; here
        the five headers are replaced in one step (``game_thread.packets``), and the host-side
        dispatch is one handler that reads the header off the event — the same lookup, on the side of
        the boundary that can do it once.

        **The connection it installed onto is kept**, because taking the install out cannot be done
        through "whatever client is current": a disconnect tears its own connection down, and native
        has no equivalent question to ask (its state, its array and its callbacks are all in one
        process). This is the port's bookkeeping for that boundary, not state of the listener's.
        """

        from .client import require_client

        client = require_client()
        table_address = client._resolve("stoc.handler_table_addr")
        client.bridge.install_packets(table_address, PACKET_WORDS)
        client.callbacks.register(EventKind.PACKET, self.OnPacket)
        self._installed_on = client

        self._reset_merchant_window_item.start()

    def Uninstall(self) -> None:
        """``listeners.cpp:130-136``: remove the callbacks and put the client's handlers back."""

        client, self._installed_on = self._installed_on, None
        if client is None:
            raise RuntimeError(
                "the merchant listener is enabled but nothing says what it installed onto."
            )
        client.callbacks.unregister(EventKind.PACKET, self.OnPacket)  # type: ignore[attr-defined]
        client.bridge.remove_packets()  # type: ignore[attr-defined]


#: The one merchant listener, created on first use — native's function-local static
#: (``listeners.cpp:140-143``).
_merchant: MerchantListener | None = None


def Merchant() -> MerchantListener:
    """``PY4GW::listeners::Merchant()`` (``listeners.cpp:140-143``)."""

    global _merchant
    if _merchant is None:
        _merchant = MerchantListener()
    return _merchant


def Registry() -> list[Listener]:
    """``listeners.cpp:148-166``: every toggleable listener, in registration order.

    Native's list holds fourteen; this port declares the one class it has ported, and the order is
    the source's own first entry. Each of the others is added here when its class is ported.
    """

    return [Merchant()]


def Initialize() -> bool:
    """``listeners.cpp:179-186``: enable every listener that is on by default."""

    for listener in Registry():
        if listener.EnabledByDefault():
            listener.Enable()
    return True


def Shutdown() -> None:
    """``listeners.cpp:188-192``: disable every listener."""

    for listener in Registry():
        listener.Disable()


def Update(delta_ms: float = 0.0) -> None:
    """``listeners.cpp:194-200``: hand the tick to every enabled listener."""

    for listener in Registry():
        if listener.IsEnabled():
            listener.Update(delta_ms)


__all__ = [
    "GAME_SMSG_ITEM_PRICE_QUOTE",
    "GAME_SMSG_TRANSACTION_DONE",
    "GAME_SMSG_WINDOW_ADD_ITEMS",
    "GAME_SMSG_WINDOW_ITEMS_END",
    "GAME_SMSG_WINDOW_ITEM_STREAM_END",
    "Listener",
    "Merchant",
    "MerchantListener",
    "PACKET_WORDS",
    "Registry",
    "Initialize",
    "Shutdown",
    "Update",
]
