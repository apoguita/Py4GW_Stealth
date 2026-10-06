"""Live probe: the merchant pass — walk up to a merchant, take what its callback offers, and buy one.

This is the merchant port's live pass, and it drives the interaction itself, the way the project's own
rule says a live reader must. The character stands near a merchant; everything after that is here:

1. **where the character is** — ``Map.GetMapID``, ``IsOutpost``/``IsExplorable``/``IsGuildHall``, so a
   run that finds no merchant says *why* rather than looking like a failure of the hooks;
2. **the nearest NPC** — one pass over ``AgentArray.GetAgentArray()``, keeping living NPCs
   (``Agent.IsNPC``, which is native's own ``login_number == 0``) that are not this character, and
   taking the closest by ``Utils.Distance``. The nearest handful are reported with their names and
   allegiances, so a wrong pick is visible rather than silent;
3. **the interaction** — ``Player.ChangeTarget`` and ``Player.Interact``, then a bounded wait;
4. **what the callback offers** — this is the thing being tested. The merchant's stock reaches the
   host through the ``WindowItems`` StoC packet, which this port's stub records and the listener
   appends to ``merchant_window_items_``; ``Trading.Merchant.GetOfferedItems()`` is that list. Every
   packet that arrives is printed as it is counted, so the report shows the callback firing rather
   than only its result;
5. **the buy** — ``Trading.Merchant.BuyItem(item, value)`` on the **first offered item**, with the
   cost the source's own caller uses: ``GLOBAL_CACHE.Item.Properties.GetValue(item) * 2``
   (``botting_src/helpers_src/Merchant.py:157``, ``:160``). That is one item and its gold;
6. **the proof** — ``TransactionDone`` is *also* a callback: the stub records it, the listener latches
   ``transaction_complete_``, and ``Trading.IsTransactionComplete()`` is the answer. Gold before and
   after is read from ``Inventory.GetGoldOnCharacter`` so the purchase is visible in the wallet too.

**This one buys.** It is the owner's requested live test, it spends the price of a single first item,
and it is the only write it makes — no sell, no travel, no other member that spends anything.

Usage: (elevated) python tests/probe_merchant_pass_live.py [report-path] [window-seconds]
"""

from __future__ import annotations

import json
import sys
import time
from typing import Any

import py4gw
from py4gw.agent import Agent
from py4gw.game_thread.shared_block import EventKind
from py4gw.inventory import Inventory
from py4gw.item import Item
from py4gw.listeners import Merchant
from py4gw.map import Map
from py4gw.merchant import Trading
from py4gw.player import Player
from py4gw.py4gwcorelib_src.utils import Utils
from py4gw.win32 import Win32

REPORT_PATH = (
    sys.argv[1]
    if len(sys.argv) > 1
    else f"tests/live_reports/merchant_pass_{int(time.time())}.jsonl"
)
WINDOW_SECONDS = float(sys.argv[2]) if len(sys.argv) > 2 else 15.0

#: How long the transaction callback may take after the buy is issued.
TRANSACTION_SECONDS = 8.0

#: How long the NPC search may take, in passes. The names it filters on come from the client's string
#: table, which the connection is filling while this runs.
SEARCH_SECONDS = 20.0

#: How many nearby NPCs a run reports, so a wrong pick is visible.
CANDIDATES = 6

#: The merchant headers, so a report can say which of them arrived.
HEADER_NAMES = {
    0x0084: "WindowItems",
    0x0085: "WindowItemsEnd",
    0x0086: "ItemStreamEnd",
    0x00CC: "TransactionDone",
    0x00F7: "QuotedItemPrice",
}

_LAST_EMIT = [time.monotonic()]


def emit(stage: str, **values: Any) -> None:
    """Print one step and append it to the report, immediately. Every emit is a heartbeat."""

    _LAST_EMIT[0] = time.monotonic()
    line = json.dumps({"stage": stage, **values}, default=str)
    print(line, flush=True)
    if REPORT_PATH:
        with open(REPORT_PATH, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")


def ask(label: str, call: Any) -> Any:
    """Read one member, reporting a raise as the answer rather than hiding it."""

    try:
        return call()
    except BaseException as error:  # noqa: BLE001 - reported, never hidden
        return f"{type(error).__name__}: {error}"


def merchant_state() -> dict[str, Any]:
    """Every answer the merchant class gives, member by member."""

    listener = Merchant()
    return {
        "trader_offered": ask("trader_offered", Trading.Trader.GetOfferedItems),
        "merchant_offered": ask("merchant_offered", Trading.Merchant.GetOfferedItems),
        "crafter_offered": ask("crafter_offered", Trading.Crafter.GetOfferedItems),
        "collector_offered": ask("collector_offered", Trading.Collector.GetOfferedItems),
        "quoted_item_id": ask("quoted_item_id", Trading.Trader.GetQuotedItemID),
        "quoted_value": ask("quoted_value", Trading.Trader.GetQuotedValue),
        "transaction_complete": ask(
            "transaction_complete", Trading.IsTransactionComplete
        ),
        "listener_enabled": listener.IsEnabled(),
        "listener_window_items": len(listener.GetMerchantWindowItems()),
        "listener_merchant_items": len(listener.GetMerchantItems()),
        "gold": ask("gold", Inventory.GetGoldOnCharacter),
    }


def counters(counts: dict[int, int]) -> dict[str, int]:
    """The packet counts, by header name."""

    return {name: counts.get(header, 0) for header, name in HEADER_NAMES.items()}


#: The two functions the connection patches, as ``client.py`` names them, with the entry bytes this
#: build has when nothing is attached (``_GAME_THREAD_HOOK_BYTES`` and ``_GAME_THREAD_OBSERVE_BYTES``).
HOOKED = (
    ("game_thread.leave_game_thread_func", "55 8b ec 81 ec 20 02 00 00"),
    ("ui.send_ui_message_func", "55 8b ec 8b 45 08 83 f8 56"),
)


def entry_is_original(win32: Win32, pid: int) -> bool:
    """Return whether both hooked functions hold their own bytes, read directly and read-only."""

    from py4gw.memory import ProcessMemoryReader
    from py4gw.scanner import PatternCatalog, RemoteScanner

    module = win32.get_main_module(pid)
    reader = ProcessMemoryReader(win32, pid)
    try:
        scanner = RemoteScanner(reader, int(module["base_address"]), int(module["size"]))
        scanner.initialize()
        catalog = PatternCatalog.from_directory("offsets")
        for name, expected in HOOKED:
            result = catalog.resolve(name, scanner)
            if not result.ok:
                return False
            observed = reader.read(int(result.value), len(expected) // 3 + 1)
            if observed.hex(" ") != expected:
                return False
        return True
    finally:
        reader.close()


def main() -> int:
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        emit("no_client")
        return 1
    emit("client", pid=int(clients[0]["pid"]), elevated=bool(win32.is_elevated()))
    if not win32.is_elevated():
        emit("not_elevated", note="connecting asserts elevation")
        return 3

    # **Nothing else may be attached.** A previous controller that is still shutting down leaves the
    # two hooked entries patched for as long as its own disconnect takes, and a connect that resolves
    # a target while it is patched walks back past the entry and answers the *previous* function —
    # which then fails the installer's byte check. That happened twice here, both times because a run
    # was started while the one before it was still finishing.
    if not entry_is_original(win32, int(clients[0]["pid"])):
        emit(
            "client_is_patched",
            note="one of the two hooked entries does not hold the client's own bytes, so a "
            "controller is attached or was killed while attached. Nothing was done: wait for it to "
            "finish (or run tools/restore_stoc_handlers.py for the packet entries), then run again.",
        )
        return 7

    counts: dict[int, int] = {}

    def count(event: Any) -> None:
        header = int(event.sequence)
        counts[header] = counts.get(header, 0) + 1
        emit(
            "packet",
            header=hex(header),
            name=HEADER_NAMES.get(header, "?"),
            words=[hex(int(word)) for word in event.words],
            count=counts[header],
        )

    client = py4gw.connect(clients[0])
    try:
        client.callbacks.register(EventKind.PACKET, count)
        emit(
            "connect",
            headers=[hex(header) for header in client.bridge.packet_headers],
            state=merchant_state(),
            note="the connection installs the packet hooks and enables the merchant listener",
        )

        place = {
            "map_id": int(Map.GetMapID()),
            "outpost": bool(Map.IsOutpost()),
            "explorable": bool(Map.IsExplorable()),
            "guild_hall": bool(Map.IsGuildHall()),
        }
        emit("place", **place)

        own_agent = int(Player.GetAgentID())
        origin = Player.GetXY()
        emit("player", agent_id=own_agent, xy=list(origin))

        # What is actually around the character, of any kind — players included — so a run whose
        # "nearest NPC" is not the NPC in front of the player says *why* instead of leaving it to be
        # guessed. Names and allegiances are read for each, and the distances are in the client's own
        # units.
        around: list[tuple[float, int, str, str, str]] = []
        for agent_id in (
            int(candidate)
            for candidate in client.agent_array.get_context().GetAgentArray()
        ):
            if agent_id == own_agent:
                continue
            name = Agent.GetNameByID(agent_id)
            _, allegiance = Agent.GetAllegiance(agent_id)
            around.append(
                (
                    float(Utils.Distance(origin, Agent.GetXY(agent_id))),
                    agent_id,
                    name,
                    allegiance,
                    "npc" if Agent.IsNPC(agent_id) else "player",
                )
            )
        around.sort(key=lambda row: row[0])
        emit(
            "around",
            agents=len(around),
            nearest=[
                {
                    "agent_id": agent_id,
                    "name": name or "<unnamed>",
                    "allegiance": allegiance,
                    "kind": kind,
                    "distance": round(distance, 2),
                }
                for distance, agent_id, name, allegiance, kind in around[:8]
            ],
        )

        # The search polls, because the names it filters on are the client's own and the connection
        # starts the string-table warm-up without waiting for it: the first pass of the project's own
        # name probe answered nothing and its twentieth found its NPC 7.7 s after connect
        # (``tests/probe_find_npc_by_name.py``). One pass here would report "no NPC" for a client
        # whose table was still filling.
        deadline = time.time() + SEARCH_SECONDS
        nearby: list[tuple[float, int, str, str]] = []
        passes = 0
        while time.time() < deadline and not nearby:
            passes += 1
            ids = [
                int(agent_id)
                for agent_id in client.agent_array.get_context().GetAgentArray()
            ]
            nearby = []
            named = 0
            for agent_id in ids:
                if agent_id == own_agent:
                    continue
                if Agent.IsLiving(agent_id) is not True:
                    continue
                if Agent.IsNPC(agent_id) is not True:
                    continue
                _, allegiance = Agent.GetAllegiance(agent_id)
                name = Agent.GetNameByID(agent_id)
                if name:
                    named += 1
                distance = float(Utils.Distance(origin, Agent.GetXY(agent_id)))
                # **The nearest NPC, and nothing else picks it.** The character is stood in front of
                # the one being tested, so distance is the whole of the choice; a filter here would be
                # this probe deciding which NPC the character "meant", which is not its business and
                # was wrong twice — once on a minipet at 75 units, once on a Zaishen agent 1,500 units
                # away. Every candidate is reported with its name and allegiance so the log says who
                # was nearest rather than leaving it to be guessed.
                nearby.append((distance, agent_id, name or f"<unnamed {agent_id}>", allegiance))

            nearby.sort(key=lambda row: row[0])
            emit(
                "pass",
                index=passes,
                agents=len(ids),
                named=named,
                npcs=len(nearby),
                closest=[
                    {
                        "agent_id": agent_id,
                        "name": name,
                        "allegiance": allegiance,
                        "distance": round(distance, 3),
                    }
                    for distance, agent_id, name, allegiance in nearby[:CANDIDATES]
                ],
            )
            if not nearby:
                time.sleep(0.5)

        if not nearby:
            emit("no_npc", note="no living NPC appeared before the search deadline")
            return 4

        distance, agent_id, name, allegiance = nearby[0]
        emit(
            "chosen",
            agent_id=agent_id,
            name=name,
            allegiance=allegiance,
            distance=round(distance, 3),
        )

        Player.ChangeTarget(agent_id)
        time.sleep(0.1)
        emit("target", observed=int(Player.GetTargetID()), wanted=agent_id)

        Player.Interact(agent_id)
        emit("interact", agent_id=agent_id, wait_s=WINDOW_SECONDS)

        # The client walks there and opens the window; the offered items arrive as packets during and
        # after the walk, so the wait is the whole of it and the callback is what is being watched.
        deadline = time.time() + WINDOW_SECONDS
        offered: list[int] = []
        while time.time() < deadline:
            offered = [int(item_id) for item_id in Trading.Merchant.GetOfferedItems()]
            if offered:
                break
            time.sleep(0.25)

        emit(
            "offered",
            count=len(offered),
            items=[hex(item_id) for item_id in offered],
            counts=counters(counts),
            state=merchant_state(),
            note="this list is what the WindowItems callback gave the listener",
        )

        if not offered:
            emit(
                "nothing_offered",
                note="no WindowItems packet arrived: either the interaction did not open a merchant "
                "window, or the nearest NPC is not a merchant",
                **place,
            )
            return 5

        item_id = offered[0]
        value = ask("value", lambda: Item.Properties.GetValue(item_id))
        model = ask("model", lambda: Item.GetModelID(item_id))
        cost = value * 2 if isinstance(value, int) else 0
        emit(
            "chosen_item",
            item_id=hex(item_id),
            model_id=model,
            value=value,
            cost=cost,
            note="the cost is the source's own: Item.Properties.GetValue(item) * 2 "
            "(botting_src/helpers_src/Merchant.py:157)",
        )

        gold_before = ask("gold_before", Inventory.GetGoldOnCharacter)
        Trading.Merchant.BuyItem(item_id, cost)
        emit("buy_issued", item_id=hex(item_id), cost=cost, gold_before=gold_before)

        deadline = time.time() + TRANSACTION_SECONDS
        complete = False
        while time.time() < deadline:
            if Trading.IsTransactionComplete():
                complete = True
                break
            time.sleep(0.1)

        emit(
            "transaction",
            complete=complete,
            gold_before=gold_before,
            gold_after=ask("gold_after", Inventory.GetGoldOnCharacter),
            counts=counters(counts),
            state=merchant_state(),
            note="TransactionDone is a callback too: if it is true, the whole chain ran — our call, "
            "the client, the server, the packet, the stub, the event, the listener, the read",
        )
        return 0 if complete else 6
    finally:
        py4gw.disconnect()
        emit("disconnected", counts=counters(counts), state=merchant_state())


if __name__ == "__main__":
    raise SystemExit(main())
