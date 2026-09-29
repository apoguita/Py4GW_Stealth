# Merchant port

Plan and progress record for porting Reforged's `Py4GWCoreLib/Merchant.py` (197 lines) and the
`PyMerchant` binding class it wraps, into `py4gw/merchant.py`.

The rules this follows are in [`PORTING_RULES.md`](PORTING_RULES.md): port everything, and name
what each member still needs as the next work item. No redesign, no additions, no substitutes.

## Source structure

Nested exactly as `Merchant.py` declares it. Line numbers are the source's.

```text
Trading                                        17 members   lines 5-197
|
+-- merchant_instance, IsTransactionComplete    2   7,17
|
+-- class Trader                                8   lines 26-111
|     GetQuotedItemID, GetQuotedValue,          8   28,38,49,60,70,80,90,102
|     GetOfferedItems, GetOfferedItems2,
|     RequestQuote, RequestSellQuote,
|     BuyItem, SellItem
|
+-- class Merchant                              3   lines 113-147
+-- class Crafter                               2   lines 149-172
+-- class Collector                             2   lines 174-197
```

**The file is `Merchant.py`; the class inside it is `Trading`.** This port keeps both spellings, and
keeps `PyMerchant` for the binding — the name native binds it under
(`PYBIND11_EMBEDDED_MODULE(PyMerchant, m)`, `merchant_bindings.cpp:210`).

`PyMerchant` is ported here too. Native's class (`merchant_bindings.cpp:18-206`) is **stateless** —
fifteen methods and no fields — so `Trading.merchant_instance()` returns a real object of this
port's own class and not a stand-in, exactly as `PyEffects` is a real object in `py4gw/effect.py`.

## Current state (rounds 1-3)

**All 32 declarations answer.** Round 1 declared the surface, round 2 built the packet stub, round 3
built the host half under it and the twelve members that were waiting on listener state.

| | Source | `py4gw/merchant.py` today |
| --- | ---: | ---: |
| Declarations | 32 (17 `Trading` + 15 `PyMerchant`) | **32 declared — 32 answer, 0 name a requirement** |
| Undeclared | — | **0** |
| Member order | source order | preserved |
| Nesting | `Trading.Trader.…` | preserved; the suite pins it |

Two of them need nothing from the client, and they are the two native itself answers without the
listener:

| member | why it needs nothing |
| --- | --- |
| `Trading.merchant_instance` | native's `PyMerchant` has no state, so the object *is* the answer |
| `Trading.Trader.GetOfferedItems2` → `PyMerchant.get_trader_item_list2` | native's own body is `return {};` — *"legacy never populated"* (`merchant_bindings.cpp:200`) |
| `PyMerchant.update` | native's own body is an empty block — *"legacy no-op - state refreshed by listeners"* (`:205`) |

`update` is a no-op because **the source is a no-op**, not because this port left it out; the
distinction is the whole of [`PORTING_RULES.md`](PORTING_RULES.md) § *A no-op is very hard to
justify*, and this one is the source's.

## What the other 29 read and write, in one place

Five of them read **`PY4GW::listeners::Merchant()`** (`listeners.h:51-92`) — five pieces of state
filled by **five StoC packet callbacks** registered in `Install()` (`listeners.cpp:96-128`).

| packet | what it sets |
| --- | --- |
| `QuotedItemPrice` | `quoted_item_id_`, `quoted_value_` |
| `TransactionDone` | `transaction_complete_` |
| `ItemStreamEnd` | when `unk1 == 12`, latches `GW::Context::GetMerchantItemsArray()` into `merch_items_` |
| `WindowItems` | appends to `merchant_window_items_`, with the listener's own 1000 ms clear throttle |
| `WindowItemsEnd` | **nothing** — native keeps the hook for parity (`:121-125`) |

**How native registers them is not a function hook**, and it is now built here:

```c
// stoc_methods.cpp:55-57
if (g_game_server_handlers && g_game_server_handlers->size() > header) {
    g_game_server_handlers->at(header).handler_func = &StoCHandler_Func;
}
```

It **replaces the client's own packet handler** for that header, keeping the client's original to
chain to, and `Uninstall()` puts it back (`:130-136`). See
[`TARGET_SIDE_WORK.md`](TARGET_SIDE_WORK.md) for the capability's own row and
`` § Round 2 `` below for what the port places.

## Nearly everything else the class needs was already here

This is worth stating plainly, because it made the remaining work one capability rather than a
cascade:

| what | state |
| --- | --- |
| `GW::item::GetItemById` — six of the eight writes fetch the live record and hand the client `&item->item_id` | **ported** (`py4gw/context/item_context.py`); the record's own address *is* that field's address, because it is the record's first field |
| `merchant.transact_item_func` / `merchant.request_quote_func` | **both resolvers in the catalog** (`offsets/merchant.json`) |
| `GW::game_thread::Enqueue` (four of the writes) | **subsumed** — this port's call path already runs on the client's thread |
| `GW::Context::GetMerchantItemsArray()` → `WorldContext.merch_items` (`world.h:179, 301`) | **already read** (`py4gw/context/world_context.py`) |
| the two `TransactionInfo` / `QuoteInfo` records (`ui.h:364-374`) | **declared** in `py4gw/merchant.py`, with the source's field names |
| the call form the two records need | **built**: `CallForm.STACK_WORDS`, nine and eight words passed by value |

## Work order

1. ~~**The packet-callback capability** on `py4gw/game_thread/`~~ — **built**: the emitted stub
   (round 2) and the handler-array reader, installer and restore (round 3,
   `py4gw/game_thread/packets.py`).
2. ~~**`PY4GW::listeners::Merchant()`**~~ — **built**: `py4gw/listeners.py`, over that capability,
   with `PY4GW::Timer` ported for its own 1000 ms throttle.
3. ~~**The 28 members**, ported whole.~~ — **built**: every declaration answers.
4. **The live pass at a merchant** — the reads against a real trade window, then the writes one at
   a time with the owner present. **This is what is still owed.**

## Round 2 — the packet stub

**What native's stub is, and where the port's differs.** `StoCHandler_Func` is **one function shared
by every header**: it reads `packet->header` and indexes both the callback table and the saved
originals with it (`stoc.cpp:80`, `:92`). It can only be written that way because its callbacks are
compiled C++ that read each packet's fields through that packet's own struct. **Emitted code cannot
do that**, so the port carries the header and how much of the packet its listener reads as
immediates, and the stub is built **per header** — the same way every other stub in `payload.py`
carries its own data. What the client observes is unchanged: its handler pointer for a watched header
goes to this project's code, the packet is recorded, and the client's own handler runs afterwards.

**What the stub does, in the source's order** (`build_packet_stub`, `payload.py`):

1. validate the block, exactly as the observer does, so a block that is not this bridge's is left
   alone — and **still chain**, because a stale block must not stop the client handling its packets;
2. append one event: `kind = PACKET`, `sequence = header`, and the packet's first `words` words;
3. call the header's original **with the frame the client gave it**, and answer `true`.

**The chain is native's, including its return value.** `stoc.cpp:91-93` calls the saved original when
a callback did not block and ignores what it returns; `:102` answers `true`. So does this. A tail
call was written first and removed: it is one instruction shorter and gives the original a
byte-identical frame, but it hands the **client** the original's answer instead of `true`, which is
this port inventing a behaviour in a slot the source pins. The stub therefore pushes the packet a
second time — a `call` puts our own return address where a callee reads its argument — and takes it
back afterwards.

**`words` is what that header's listener reads, and it is per header** (`stoc.h:356-359`, `:546-548`,
`:599-602`; `listeners.cpp:99-119`):

| header | what its callback reads | words carried (header included) |
| --- | --- | ---: |
| `QuotedItemPrice` | `itemid`, `price` | 3 |
| `TransactionDone` | **nothing** | 1 |
| `ItemStreamEnd` | `unk1` | 2 |
| `WindowItems` | `count`, `item_ids[16]` | **18** |
| `WindowItemsEnd` | **nothing** | 1 |

Zero is a legitimate count for a callback that reads nothing: the packet still has to be recorded as
having arrived, because that is what `OnTransactionComplete()` is triggered by. Eighteen is the
widest, and it is the bound the block now carries.

**The copy travels in the event record, and the record grew for it.** A packet is the client's own
buffer, reused for the next packet, so its fields have to be read where the callback runs — the same
argument that makes the observer copy a dialog's string (`docs/RESEARCH.md`, 2026-09-25). The record
gained a second bounded copy beside the string's (`EVENT_WORDS_OFFSET`, `EVENT_WORDS` words) and a
`word_count` field saying how many of them belong to this record, so a slot that last held a packet
does not hand its words to a message event and vice versa. **`EVENT_SIZE` is 1024 → 2048** (it has to
stay a power of two: the payload addresses a record by shifting its slot) and the block is
**version 6**; every offset after the event region moved with it, and the string copy's own area,
bound and offsets are unchanged.

**The offline witness** is `tests/test_payload_offline.py::PacketStubTests` (13 tests), which executes
the bytes rather than describing them: the event and its words, the per-header counts, the ring
stride at the new record size, the chain (a witness original records the pointer it was handed), the
block-header refusal, a null block, a full ring — each of those last three asserting the original
**still ran** — the `__cdecl` return, and guards intact on both sides of the block.

## Round 3 — the host half, and the class

**The installer** (`py4gw/game_thread/packets.py`) walks native's own chain: the resolver
``stoc.handler_table_addr`` gives the address of the ``GameServer*`` **variable**, native casts it to
``GameServer**`` and dereferences it (``stoc_patterns.cpp:43-47``), ``gs_codec`` is at ``+0x8`` and
``handlers`` at ``+0x2C`` (``stoc.cpp:26-41``), and the array is a ``GW::GWArray`` whose buffer,
capacity and size sit at ``+0``, ``+4`` and ``+8`` (``gw_array.h:61-64``) with 12-byte entries.

**That was measured before it was written.** ``tests/probe_stoc_handlers.py`` is read-only and needs
no elevation: it reads the client's memory directly and walked the whole chain on this build — the
server at ``0x1D6BC90``, the codec at ``0x1D63388``, **487 entries in a 504-slot array**, and all
five merchant headers in range holding real code in ``.text``
(``live_reports/stoc_handlers.json``). It also walked the *other* reading of the resolver's value and
showed it is not the right one, so the cast above is evidence rather than inference.

**What the installer does, in the source's order** (``EnableHooks``, ``stoc.cpp:118-128``): read the
array, check every wanted header is in range, save each original, place one stub per header, then
replace the entry. The replacement is written by the payload's ``WRITE_MEMORY`` — on the game's own
thread, where every other client-state write in this project happens — and **the entry is read back
afterwards**, because a replacement that did not land would leave the client running its own handler
while this side believes it is watching.

**One refusal is this port's own, and it is the port's existing recovery discipline.** Native
snapshots whatever the array holds and chains to it, which is safe in a runtime that injected itself
into a fresh process. A controller here can attach to a client that **outlived a previous
controller**, and a handler pointer left outside the client module by one that died is a jump into
freed memory taken on the client's own thread. So a wanted header's handler is checked against the
client's module before anything is placed; outside it, the install is refused by name. That is what
``ConnectedClient._prepare_target`` does for a stale entry patch, applied to the other kind of
pointer this project replaces.

**The restore** is native's: every saved pointer goes back unconditionally
(``DisableHooks``, ``stoc.cpp:130-140``), and **before anything is freed** — the write needs the block
and the hook this bridge placed. Every entry is attempted even when one write fails, and the failures
are raised together with the headers that did go back, because a restore that stopped at the first
refusal would leave the client dispatching into code this is about to release. Code is freed only
when ``free_code`` is asked for and only after the stubs' own **in-flight count** reaches zero — a
packet handler can run on a thread this controller never sees, and the count is the same answer
``Hooker.remove`` uses (``hooker.py:783-805``).

**The listener** (``py4gw/listeners.py``) is the source's ``Listener`` base and
``MerchantListener``: the five accessors, the two resets, the four handlers, the 1000 ms throttle
over a ported ``PY4GW::Timer`` (``base/timer.h``, whose clock is ``std::clock()`` — processor time —
so the port reads ``time.process_time()``), and the client-array latch on ``ItemStreamEnd``. It is
enabled where native's bootstrap enables it: after the connection's layer is installed, over
``Registry()``/``Initialize()``/``Shutdown()``, and its callbacks are registered **before** the
listener thread starts so no packet can arrive with nothing listening for it.

**The two records, and the one thing a write does differently.** ``TransactItems`` takes nine words
by value and ``RequestQuote`` eight — ``type``, ``gold_give``, the three of ``give``, ``gold_recv``
and the three of ``recv`` — which no command record can carry, so ``CallForm.STACK_WORDS`` pushes
them from the block's data region and releases them, as ``__cdecl`` requires. And native passes
pointers into **its own address space**: ``&item->item_id`` (an address this port computes from the
record it read), ``std::vector::data()`` of its ingredient lists, and ``&item_id`` — the address of a
function parameter on its stack. The port places those words in the block's data region, which is
exactly what that region is documented for.

## Evidence, and what is still owed

| what | evidence |
| --- | --- |
| the stub (round 2) | ``tests/test_payload_offline.py::PacketStubTests`` — the bytes are executed: the event, the per-header counts, the chain (a witness original records the pointer it was handed), the refusals, the in-flight count |
| the call form | ``SourceAbiFormTests`` — a witness callee reads nine words in order, the stack comes back where it was, and a span past the data region is refused before a word is pushed |
| the installer and the listener | ``tests/test_listeners_offline.py`` (44 tests) — the walk, the replacement and its restore against a synthetic client memory laid out as the probe measured it; every handler; the throttle; the latch; the lifecycle |
| the members | ``tests/test_merchant_offline.py`` (26 tests) — the surface against both sources, and every write's nine or eight words by value against a stand-in client |
| the chain, live and read-only | ``tests/probe_stoc_handlers.py`` → ``live_reports/stoc_handlers.json`` |
| **the install and the restore, live** | ``tests/probe_merchant_packets_live.py`` → ``live_reports/merchant_packets.json`` (2026-09-30, elevated, 20 s): the five handlers read before anything was written, replaced on connect with this project's stubs — **``every_entry_is_the_stub: true``** and **``originals_match_the_read_before: true``** — then **``restored: true``** after the disconnect with the client still healthy and ``in_flight_at_end: 0`` |
| **the callback, live, and a real purchase** | ``tests/probe_merchant_pass_live.py`` → ``live_reports/repair_and_merchant_20260929_123146.txt`` and ``live_reports/merchant_buy_20260929_123333.txt`` (2026-09-30, elevated, twice). The character was stood in front of a merchant; the probe took **the nearest NPC**, targeted it, interacted, and then: ``WindowItems`` (``0x84``) arrived **through the port's stub** carrying ``count = 11`` and ids ``0x52a``-``0x539``; ``Trading.Merchant.GetOfferedItems()`` answered those **11 ids** — the callback is what presents the offered items, and this is it. The first offered item (``0x52a`` = 1322, model 918, ``Properties.GetValue`` 25) was bought with the source's own cost, ``value * 2`` = **50 gold** (``botting_src/helpers_src/Merchant.py:157``), and ``TransactionDone`` (``0xCC``) came back **through the stub too**: ``IsTransactionComplete()`` went true and **gold went 2040 → 1990, then 1990 → 1940** — 50 each time, two runs, one item bought per run |
| **the stub being entered by a real packet** | **done**: the two runs above are that — ``WindowItems`` and ``TransactionDone`` were dispatched by the client into generated code, recorded, delivered to the listener and read back through the ported class |
| **what the runs did not produce** | ``WindowItemsEnd`` (``0x85``), ``ItemStreamEnd`` (``0x86``) and ``QuotedItemPrice`` (``0xF7``) never arrived: a merchant's buy tab does not send them, and asking a *trader* for a quote needs the trader's window. Their handlers are the same code with different word counts, and they are pinned offline (``tests/test_listeners_offline.py``); a run at a **trader** and at the buy tab's stream end is what would exercise them live |

## Progress

- [x] **Round 1** — the structure: `PyMerchant` (15) + `Trading` (17) declared in source order,
      exported at the package root, `tests/test_merchant_offline.py` pinning the surface against both
      sources; the capability recorded
- [x] **Round 2** — the emitted packet stub, the block's words copy and `word_count`, block version 6,
      `PacketStubTests` executing it, and the two zeroing tests that keep a reused event slot honest
- [x] **Round 3** — the host half: the handler-array walk (measured live, read-only, before it was
      written), the installer with its read-back and its module check, the restore and its in-flight
      count, `PY4GW::Timer`, the merchant listener, the two records, `CallForm.STACK_WORDS`, and the
      twelve members that were waiting on all of it. **Plus the first live write**: the five entries
      replaced and restored on a running client, verified entry by entry
- [x] **Round 4** — **the live pass at a merchant, and it is green.** The offered items arrive
      through the callback (`WindowItems` → the listener → `Trading.Merchant.GetOfferedItems()`, 11
      ids), and **the first offered item was bought twice, 50 gold each time, with `TransactionDone`
      coming back through the same stub** (gold 2040 → 1990 → 1940). Three things came out of the
      round besides the result: the port now **recovers its own orphaned stubs** (a killed controller
      leaves entries pointing at emitted code whose owner is gone, and the original is still written
      inside the stub — `original_from_stub`, with `tools/restore_stoc_handlers.py` for the case
      where something else must be reasoned about), the probe refuses to run while **another
      controller is attached** (resolving a target while its entry is patched walks back past the
      entry and answers the previous function), and a run's log is written per run so evidence cannot
      be overwritten. Owed, and named: live exercise of `WindowItemsEnd`, `ItemStreamEnd` and
      `QuotedItemPrice`, which a merchant's buy tab does not send — that is a **trader's** window and
      the buy tab's stream end
