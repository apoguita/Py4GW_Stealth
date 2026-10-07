"""Live probe: the ported ``Quest`` class against the running client — reads first, the calls last.

Two stages, and the split is the project's own discipline (``AGENTS.md``: a live write is deliberate,
bounded and attributable):

* ``reads`` — **no elevation and no connection.** A read-only stand-in over the live process runs
  everything the class answers without a client call: the quest-log walk
  (``GetQuestLogIds``/``GetQuestLog``), the active quest, the mission-objective presence, and each
  log entry's ``QuestData`` fields. The five string trios are *not* here: each one hands the record's
  own string to the client's decoder, which is a call, so they belong to the stage that has the
  capability layer.
* ``act`` — **elevated.** Connects, then: the log and the active quest again, ``RequestQuestInfo``
  (the source's two calls), the five ``Request/IsReady/Get`` trios with the ready flag polled, and —
  **only when the owner names them on the command line** — ``SetActiveQuest`` and ``AbandonQuest``,
  which are the two members that change the game.

Usage::

    python tests/probe_quest_live.py reads [report-path]
    python tests/probe_quest_live.py act   [report-path] [--quest ID] [--set-active ID]
                                           [--restore-active ID] [--abandon ID] [--names]      # elevated

``--set-active`` and ``--abandon`` change the game and are only ever run when the owner names them;
``--restore-active`` is the way back from a flip, and ``--quest`` only chooses which quest the decode
trios are asked about. ``--names`` reads the name of every id in the log through the class's own trio,
which is what a run that has to name one quest to **remove** needs first; it changes nothing.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

REPORT_PATH = "tests/live_reports/quest_live.json"

#: How long a decode trio is given to answer before the probe records it as not ready. The client
#: decodes on its own thread; the sources' own wait is 1000 ms (``quest_bindings.cpp:103-108``).
DECODE_WAIT_SECONDS = 2.0

#: How long an acting step waits for the client to show what it was just sent. The client applies a
#: quest change when it processes the command, not inside the call that sends it, so a read taken
#: immediately can describe a record the client has not updated yet.
SETTLE_TIMEOUT_SECONDS = 12.0

#: The abandon step gets a longer window than its sibling, for one reason: **it can be run once.**
#: A 12 s window that expires would leave the question open on a quest that is already gone, and the
#: owner allows exactly one. Waiting longer costs only time; stopping early would cost the evidence.
ABANDON_SETTLE_SECONDS = 30.0

#: The window is this long because a quest change is a **server** round trip: the client sends the
#: request and updates the record when the server answers, so a 3 s window cannot tell "never" from
#: "slow" (measured live 2026-10-06).
POLL_SECONDS = 0.05

#: The five trios, as ``(field, request, is_ready, get)`` — the source's own names.
TRIOS = (
    ("name", "RequestQuestName", "IsQuestNameReady", "GetQuestName"),
    ("description", "RequestQuestDescription", "IsQuestDescriptionReady", "GetQuestDescription"),
    ("objectives", "RequestQuestObjectives", "IsQuestObjectivesReady", "GetQuestObjectives"),
    ("location", "RequestQuestLocation", "IsQuestLocationReady", "GetQuestLocation"),
    ("npc", "RequestQuestNPC", "IsQuestNPCReady", "GetQuestNPC"),
)


def _ask(call: Any) -> Any:
    """Run one member and report what it answered, or exactly how it refused."""

    try:
        return call()
    except Exception as error:  # noqa: BLE001 - reported, never hidden
        return f"{type(error).__name__}: {error}"


def _write(report: dict[str, Any], path: str, code: int) -> int:
    """Write the report, **then** print a console-safe copy of it.

    The file comes first because a decoded quest string carries the client's own code units and a
    cp1252 console cannot encode them — measured live 2026-10-06: printing the report raised
    ``UnicodeEncodeError: character '\\x81'`` *after* the whole pass had already run, which lost the
    report and hid a successful result behind a traceback.
    """

    if path:
        Path(path).write_text(
            json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
        )
    print(json.dumps(report, indent=2, ensure_ascii=True, default=str))
    return code


def _log_snapshot(report: dict[str, Any]) -> list[int]:
    """The log, the active quest and each entry's data — every read the class answers."""

    from py4gw.quest import Quest

    ids = _ask(Quest.GetQuestLogIds)
    report["quest_log_ids"] = ids
    report["active_quest_id"] = _ask(Quest.GetActiveQuest)
    report["mission_map_quest_available"] = _ask(Quest.IsMissionMapQuestAvailable)
    if not isinstance(ids, list):
        return []
    entries = _ask(Quest.GetQuestLog)
    if isinstance(entries, list):
        report["quest_log"] = [
            {
                "quest_id": entry.quest_id,
                "log_state": hex(int(entry.log_state)),
                "map_from": entry.map_from,
                "map_to": entry.map_to,
                "marker": [entry.marker_x, entry.marker_y],
            }
            for entry in entries
        ]
        report["is_completed"] = {
            str(entry.quest_id): _ask(lambda i=entry.quest_id: Quest.IsQuestCompleted(i))
            for entry in entries
        }
        report["is_primary"] = {
            str(entry.quest_id): _ask(lambda i=entry.quest_id: Quest.IsQuestPrimary(i))
            for entry in entries
        }
    if ids:
        data = _ask(lambda: Quest.GetQuestData(ids[0]))
        if not isinstance(data, str):
            report["first_quest_data"] = {
                "quest_id": data.quest_id,
                "log_state": hex(int(data.log_state)),
                "map_from": data.map_from,
                "map_to": data.map_to,
                "marker": [data.marker_x, data.marker_y],
                "is_completed": data.is_completed,
                "is_primary": data.is_primary,
                "name_is_empty_here": data.name == "",
            }
    return [int(value) for value in ids] if all(isinstance(value, int) for value in ids) else []


def reads_stage(win32: Any, process: dict[str, Any], report: dict[str, Any]) -> int:
    """Everything the class answers without a client call."""

    from py4gw import client as client_module
    from py4gw.map import Map
    from py4gw.memory import ProcessMemoryReader
    from py4gw.scanner import PatternCatalog, RemoteScanner

    from tests.probe_party_live import _LiveClient

    pid = int(process["pid"])
    module = win32.get_main_module(pid)
    report["module"] = {
        "base": hex(int(module["base_address"])),
        "size": hex(int(module["size"])),
    }
    reader = ProcessMemoryReader(win32, pid)
    try:
        scanner = RemoteScanner(reader, int(module["base_address"]), int(module["size"]))
        scanner.initialize()
        patterns = PatternCatalog.from_directory("offsets")
        previous = client_module._current_client
        client_module._current_client = _LiveClient(pid, reader, scanner, patterns)
        try:
            report["map"] = {"id": _ask(Map.GetMapID), "ready": _ask(Map.IsMapReady)}
            ids = _log_snapshot(report)
            report["note"] = (
                "read stage: no connection, nothing called. The quest log, the active quest and each "
                "entry's data are reads; the five string trios need the client's decoder, so they run "
                "in the act stage."
            )
            print(
                "map=%s ready=%s | log ids=%s | active=%s | mission quests=%s"
                % (
                    report["map"]["id"],
                    report["map"]["ready"],
                    ids,
                    report.get("active_quest_id"),
                    report.get("mission_map_quest_available"),
                )
            )
            return 0
        finally:
            client_module._current_client = previous
    finally:
        reader.close()


def _settle(read: Any, expected: Any, timeout: float = SETTLE_TIMEOUT_SECONDS) -> tuple[Any, bool, float]:
    """Poll one read until it answers ``expected``, and report the value, the flag and the wait.

    The client applies a quest change when it **processes** the command, not inside the call that
    sends it — the lesson the party probes paid for (``docs/PARTY_PORT.md``) — so a step that reads
    back immediately compares against a record the client has not updated yet. The returned **value is
    the read's own answer**, not a boolean: "it settled" and "what it settled on" are different
    findings, and an earlier version of this probe recorded only the first.
    """

    started = time.monotonic()
    value = _ask(read)
    while value != expected and time.monotonic() - started < timeout:
        time.sleep(POLL_SECONDS)
        value = _ask(read)
    return value, value == expected, round(time.monotonic() - started, 2)


def act_stage(
    report: dict[str, Any],
    set_active: int | None,
    restore_active: int | None,
    abandon: int | None,
    quest: int | None,
    set_active_via_call: int | None = None,
    names: bool = False,
) -> int:
    """The connected run: the source's own flow, with the two game-changing members named by hand."""

    from py4gw.quest import Quest

    ids = _log_snapshot(report)
    if not ids:
        report["decode_trios"] = "not attempted: the quest log is empty (no character in a map)"
        print("quest log is empty — nothing to request or decode")
        return 3

    # The decode target: the owner's ``--quest`` when given, otherwise the quest the client itself
    # reports as active, otherwise the log's first entry. ``--set-active``/``--abandon`` are the two
    # members that change the game, and choosing a decode target never implies either of them.
    active = report.get("active_quest_id")
    if quest is not None:
        quest_id = int(quest)
    elif isinstance(active, int) and active in ids:
        quest_id = int(active)
    else:
        quest_id = int(ids[0])
    report["decode_target"] = quest_id
    report["decode_target_is_the_active_quest"] = quest_id == active
    if quest_id not in ids:
        report["decode_trios"] = "not attempted: %d is not in the quest log" % quest_id
        print("quest %d is not in the log" % quest_id)
        return 3

    report["request_quest_info"] = {
        "quest_id": quest_id,
        "called": _ask(lambda: Quest.RequestQuestInfo(quest_id)),
    }
    print("RequestQuestInfo(%d) -> %s" % (quest_id, report["request_quest_info"]["called"]))

    fields: dict[str, Any] = {}
    # The five trios as the class itself declares them — the members are named here, not looked up
    # from strings, so the probe cannot drift onto a member the source does not have.
    trios = (
        ("name", Quest.RequestQuestName, Quest.IsQuestNameReady, Quest.GetQuestName),
        ("description", Quest.RequestQuestDescription, Quest.IsQuestDescriptionReady, Quest.GetQuestDescription),
        ("objectives", Quest.RequestQuestObjectives, Quest.IsQuestObjectivesReady, Quest.GetQuestObjectives),
        ("location", Quest.RequestQuestLocation, Quest.IsQuestLocationReady, Quest.GetQuestLocation),
        ("npc", Quest.RequestQuestNPC, Quest.IsQuestNPCReady, Quest.GetQuestNPC),
    )
    for field_name, request, ready, get in trios:
        _ask(lambda r=request: r(quest_id))
        started = time.monotonic()
        answered = False
        while time.monotonic() - started < DECODE_WAIT_SECONDS:
            if ready(quest_id):
                answered = True
                break
            time.sleep(POLL_SECONDS)
        fields[field_name] = {
            "ready": answered,
            "seconds": round(time.monotonic() - started, 3),
            "value": _ask(lambda g=get: g(quest_id)),
        }
    report["decode_trios"] = fields
    for field_name, row in fields.items():
        print(
            "  %-12s ready=%-5s %-6ss value=%r"
            % (field_name, row["ready"], row["seconds"], str(row["value"])[:60])
        )

    if names:
        # Which quest is which, for a run that has to name one to change. ``GetQuestLogIds`` says
        # nothing but numbers, and the one member that removes a quest cannot be taken back — so the
        # name of every id in the log is read first, through the class's own trio.
        table: dict[str, Any] = {}
        for entry_id in ids:
            entry_id = int(entry_id)
            _ask(lambda i=entry_id: Quest.RequestQuestName(i))
            started = time.monotonic()
            while time.monotonic() - started < DECODE_WAIT_SECONDS:
                if Quest.IsQuestNameReady(entry_id):
                    break
                time.sleep(POLL_SECONDS)
            table[str(entry_id)] = _ask(lambda i=entry_id: Quest.GetQuestName(i))
        report["quest_names"] = table
        for entry_id, name in table.items():
            print("  %-6s %s" % (entry_id, str(name)[:70]))

    report["set_active"] = None
    if set_active is not None:
        before = _ask(Quest.GetActiveQuest)
        called = _ask(lambda: Quest.SetActiveQuest(set_active))
        after, settled, waited = _settle(Quest.GetActiveQuest, set_active)
        report["set_active"] = {
            "quest_id": set_active,
            "called": called,
            "active_before": before,
            "active_after": after,
            "settled": settled,
            "settle_seconds": waited,
        }
        print(
            "SetActiveQuest(%d): active %s -> %s (settled=%s in %.1fs)"
            % (set_active, before, after, settled, waited)
        )

    report["restore_active"] = None
    if restore_active is not None:
        before = _ask(Quest.GetActiveQuest)
        called = _ask(lambda: Quest.SetActiveQuest(restore_active))
        after, settled, waited = _settle(Quest.GetActiveQuest, restore_active)
        report["restore_active"] = {
            "quest_id": restore_active,
            "called": called,
            "active_before": before,
            "active_after": after,
            "settled": settled,
            "settle_seconds": waited,
        }
        print(
            "SetActiveQuest(%d) restore: active %s -> %s (settled=%s in %.1fs)"
            % (restore_active, before, after, settled, waited)
        )

    # A diagnostic, not a member: the client's own function that native's inner layer calls and its
    # hook intercepts (`quest_methods.cpp:20-26`, `quest.cpp:34-44`). It answers which of the two
    # source-side mechanisms actually moves the client, which is what decides how this port should
    # reach that member — the harness is where that question belongs.
    report["set_active_via_call"] = None
    if set_active_via_call is not None:
        from py4gw.client import require_client
        from py4gw.game_thread.shared_block import CallForm

        client = require_client()
        before = _ask(Quest.GetActiveQuest)
        report["set_active_via_call"] = {
            "quest_id": set_active_via_call,
            "resolves": bool(_ask(lambda: client.resolves("quest.set_active_quest_func"))),
            "active_before": before,
        }
        _ask(
            lambda: client.call_function(
                "quest.set_active_quest_func", CallForm.U32, int(set_active_via_call)
            )
        )
        after, settled, waited = _settle(Quest.GetActiveQuest, set_active_via_call)
        report["set_active_via_call"].update(
            {"active_after": after, "settled": settled, "settle_seconds": waited}
        )
        print(
            "set_active_quest_func(%d) called directly: active %s -> %s (settled=%s in %.1fs)"
            % (set_active_via_call, before, after, settled, waited)
        )

    report["abandon"] = None
    if abandon is not None:
        before_ids = _ask(Quest.GetQuestLogIds)
        report["abandon"] = {
            "quest_id": abandon,
            "in_log_before": isinstance(before_ids, list) and abandon in before_ids,
            "log_before": before_ids,
        }
        if not report["abandon"]["in_log_before"]:
            report["abandon"]["verdict"] = "not attempted: %d is not in the log" % abandon
            print(report["abandon"]["verdict"])
        else:
            called = _ask(lambda: Quest.AbandonQuest(abandon))
            # A quest leaving the log means the id is simply absent from the next read.
            #
            # ``_settle`` answers the *predicate*, so the poll's value is a bool and the log itself has
            # to be read again afterwards. Carrying the predicate forward as "the remaining log" is
            # what the first and only permitted run did: it reported a quest that had in fact left in
            # 0.1 s as ``gone: false, others_untouched: false``, and the failure was in the harness's
            # bookkeeping rather than in the member. Nothing else may consume ``_settle``'s value as a
            # log list.
            _polled, settled, waited = _settle(
                lambda: abandon in (_ask(Quest.GetQuestLogIds) or []),
                False,
                ABANDON_SETTLE_SECONDS,
            )
            remaining = _ask(Quest.GetQuestLogIds)
            others_before = [q for q in before_ids if q != abandon]
            others_after = [q for q in remaining if q != abandon] if isinstance(remaining, list) else None
            report["abandon"].update(
                {
                    "called": called,
                    "settled": settled,
                    "settle_seconds": waited,
                    "log_after": remaining,
                    "gone": isinstance(remaining, list) and abandon not in remaining,
                    "others_untouched": others_after == others_before,
                    "verdict": (
                        "the quest left the log and nothing else moved"
                        if isinstance(remaining, list)
                        and abandon not in remaining
                        and others_after == others_before
                        else "NOT settled, or another entry moved — see the fields above"
                    ),
                }
            )
            print(
                "AbandonQuest(%d): log %d entries -> %d, gone=%s, others_untouched=%s (%s)"
                % (
                    abandon,
                    len(before_ids),
                    len(remaining) if isinstance(remaining, list) else -1,
                    report["abandon"]["gone"],
                    report["abandon"]["others_untouched"],
                    report["abandon"]["verdict"],
                )
            )
    return 0


def main() -> int:
    from py4gw.win32 import Win32

    argv = list(sys.argv[1:])
    stage = argv[0] if argv and not argv[0].startswith("-") else "reads"
    if argv and not argv[0].startswith("-"):
        argv = argv[1:]
    set_active = restore_active = abandon = quest = set_active_via_call = None
    names = "--names" in argv
    if names:
        argv.remove("--names")
    for flag, target in (
        ("--set-active", "set"),
        ("--set-active-via-call", "set-call"),
        ("--restore-active", "restore"),
        ("--abandon", "abandon"),
        ("--quest", "quest"),
    ):
        if flag in argv:
            index = argv.index(flag)
            value = int(argv[index + 1])
            del argv[index : index + 2]
            if target == "set":
                set_active = value
            elif target == "set-call":
                set_active_via_call = value
            elif target == "restore":
                restore_active = value
            elif target == "quest":
                quest = value
            else:
                abandon = value
    report_path = argv[0] if argv else REPORT_PATH

    report: dict[str, Any] = {"stage": stage}
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        report["error"] = "no Guild Wars client is running"
        return _write(report, report_path, 1)
    process = clients[0]
    report["pid"] = int(process["pid"])
    report["controller_elevated"] = bool(win32.is_elevated())

    if stage == "reads":
        return _write(report, report_path, reads_stage(win32, process, report))

    from tests.probe_two_runtimes_live import connectable
    from tests.test_live_coexistence import _Entries

    import py4gw

    connectable_now, decisions = connectable(win32, int(process["pid"]))
    report["entry_decisions"] = decisions
    if not connectable_now:
        report["error"] = (
            "connect would refuse at least one of the four entries, so nothing was done: "
            + "; ".join(decisions)
        )
        return _write(report, report_path, 7)

    entries = _Entries(int(process["pid"]))
    before = entries.snapshot()
    before_jumps = entries.foreign_entries()

    with py4gw.connect(process, game_thread=True) as _client:
        code = act_stage(report, set_active, restore_active, abandon, quest, set_active_via_call, names)

    after = entries.snapshot()
    after_jumps = entries.foreign_entries()
    entries.close()
    report["entries_before"] = {name: row["head"].hex(" ") for name, row in before.items()}
    report["entries_after_disconnect"] = {name: row["head"].hex(" ") for name, row in after.items()}
    report["hooks_original_after_disconnect"] = (
        {name: row["head"] for name, row in after.items()}
        == {name: row["head"] for name, row in before.items()}
        and {name: row["head"] for name, row in after_jumps.items()}
        == {name: row["head"] for name, row in before_jumps.items()}
    )
    return _write(report, report_path, code)


if __name__ == "__main__":
    raise SystemExit(main())
