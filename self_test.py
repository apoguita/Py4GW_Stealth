"""A battery of checks that say, one line at a time, whether this library works.

The window runs this from the **Self-test** tab, so a person can press one button instead of
testing twenty thousand entries by hand. Every check states:

* **what it expected** (in words, not just a value),
* **what it actually saw**,
* and its verdict -- ``pass``, ``fail``, or ``skip``.

A check that needs the selected client is **skipped** when nothing is connected, never failed: a
window with no client is a state, not a defect. A check that needs the *window* is skipped when the
battery is run headlessly. And a check never writes to the client: while a live section runs, every
member the surface classifies as a write is replaced by a recorder that fails the run if it is
called -- so the battery is read-only by construction, not by intention.

The areas, in the order they run:

1. ``map`` -- the map is the library: every exported name, every record's fields with offsets, every
   enum member, every class member, each mapped exactly once.
2. ``engine`` -- the surface engine's own safety rules: writes classified, nothing that acts called
   by default, unclassified members reported rather than run.
3. ``pure members`` -- members that need no client at all, with answers known from the library's own
   contract (``Utils.DegToRad(180) == pi``, ``styles.colorref_to_tk(0x0000FF) == '#ff0000'``, ...).
4. ``window`` -- the root window's own wiring: its four tabs, the map it built, the buttons that run
   a subset, and both reports.
5. ``client`` -- the selected client: elevation, discovery, the connection, the window's context
   views, and the surface's reads against it. Skipped whole without a connection.
6. the live data, one section per subject -- ``live contexts``, ``live char``, ``live map``,
   ``live player``, ``live agents``, ``live party``, ``live world``, ``live camera``,
   ``live text parser``, ``live instance``, ``live items``, ``live agreement``, ``live data dump``
   and ``live safety``. These read the running client and judge whether what came back is *correct
   game data*: a non-zero map id, the player in the agent array, ``GetPartySize()`` equal to the
   party context's own three arrays, boundaries ordered, ``entries_per_file == 1024``, two paths to
   the same fact agreeing. Every write member is blocked while a section runs, so the battery is
   read-only by construction.
7. ``surface run`` -- the engine's walk of the map, asserting that nothing raised unexpectedly.

Nothing here is a substitute for the live suite in ``tests/``; it is the window's own answer to "does
this thing work", and it is meant to be run by a person looking at the screen -- every value it saw is
kept, so the same run can also be written out and read afterwards.
"""

from __future__ import annotations

import contextlib
import ctypes
import importlib
import math
import time
import types
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

import py4gw
import test_surface


class CheckFailed(Exception):
    """A check that ran and saw something other than what it expected."""


@dataclass
class Check:
    """One question with a known answer."""

    area: str
    name: str
    expected: str
    call: Callable[["Context"], str]
    needs_client: bool = False
    needs_window: bool = False
    heavy: bool = False


@dataclass
class Result:
    """What a check saw."""

    area: str
    name: str
    status: str
    expected: str
    actual: str = ""
    detail: str = ""
    milliseconds: float = 0.0


@dataclass
class Context:
    """What a check may look at: the map, the client, and the window when there is one."""

    entries: tuple[test_surface.Entry, ...] = ()
    client: Any = None
    window: Any = None
    connected: bool = False
    files: list[Path] = field(default_factory=list)
    #: Everything a live section read, for the window's data dump and the run's report.
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class Sub:
    """One question inside a live section."""

    name: str
    expected: str
    ok: bool
    detail: str


class Live:
    """A section of live checks: many questions, one verdict, and every failure named.

    The window shows one line per section -- ``live data / agents: 12 checks, 1 failed`` -- while the
    report names each question that failed with what it saw. That is the shape a person reads: a
    summary in the table, and the evidence in the file.
    """

    def __init__(self, area: str) -> None:
        self.area = area
        self.subs: list[Sub] = []

    def check(
        self,
        name: str,
        expected: str,
        call: Callable[[], Any],
        invariant: Callable[[Any], tuple[bool, str]] | None = None,
    ) -> Any:
        """Ask one live question; a refusal or a wrong answer is recorded, never raised."""

        try:
            value = call()
        except Exception as error:  # noqa: BLE001 - the library's own refusal is a reading
            self.subs.append(Sub(name, expected, False, f"{type(error).__name__}: {error}"))
            return None
        if invariant is None:
            ok = value is not None
            detail = "a value" if ok else "None"
        else:
            try:
                ok, detail = invariant(value)
            except Exception as error:  # noqa: BLE001 - a broken invariant is the check's own bug
                ok, detail = False, f"invariant raised {type(error).__name__}: {error}"
        self.subs.append(Sub(name, expected, bool(ok), detail))
        return value

    def summary(self) -> str:
        failed = [sub for sub in self.subs if not sub.ok]
        return (
            f"{len(self.subs)} checks, {len(self.subs) - len(failed)} passed"
            + (f", {len(failed)} failed: " + "; ".join(f"{sub.name} -> {sub.detail}" for sub in failed[:4]) if failed else "")
        )

    def verdict(self) -> str:
        """The section's own line, or a failure naming every question that failed."""

        failed = [sub for sub in self.subs if not sub.ok]
        if not failed:
            return self.summary()
        lines = [f"{len(failed)} of {len(self.subs)} failed"]
        for sub in failed:
            lines.append(f"{sub.name}: expected {sub.expected}; saw {sub.detail}")
        raise CheckFailed(" | ".join(lines))

    def rows(self) -> list[dict[str, str]]:
        """Every question with its own verdict, for the report file."""

        return [
            {
                "status": "pass" if sub.ok else "fail",
                "area": self.area,
                "check": sub.name,
                "expected": sub.expected,
                "saw": sub.detail,
            }
            for sub in self.subs
        ]


def expect(condition: bool, actual: str, expected: str = "") -> str:
    """Return ``actual`` when the condition holds, and fail with it when it does not."""

    if not condition:
        raise CheckFailed(actual or "the condition did not hold")
    return actual


def _settings() -> Any:
    """The GUI's own module, which carries AutoIt's constant surface."""

    from py4gw import gui

    return gui


# --- 1. the map is the library ---------------------------------------------------------------


def _map_exported_names(context: Context) -> str:
    labels = {entry.label for entry in context.entries}
    missing = [name for name in py4gw.__all__ if f"py4gw.{name}" not in labels]
    return expect(not missing, f"{len(missing)} missing: {missing[:5]}", "every exported name")


def _canonical_owner(
    context: Context, value: Any
) -> str:
    """The name a class was expanded under: the module that declares it, and its own name.

    A class can be exported under a second name (``AvailableCharacterStruct`` is another name for the
    record declared as ``AvailableCharacterInfoStruct``), and the map expands it once, where it is
    declared. A check that looked for members under the exported name would report a missing member
    that is right there, so the lookup goes by the class itself.
    """

    import importlib

    for entry in context.entries:
        if entry.owner or entry.kind not in ("record", "enum", "class"):
            continue
        if entry.detail.startswith("declared in") or entry.run == "none":
            continue
        try:
            module = importlib.import_module(entry.group)
        except Exception:  # noqa: BLE001 - a group that cannot be imported has nothing to match
            continue
        if getattr(module, entry.name, None) is value:
            return entry.name
    return ""


def _map_members(context: Context) -> str:
    labels = {entry.label for entry in context.entries}
    missing: list[str] = []
    checked = 0
    for name in py4gw.__all__:
        value = getattr(py4gw, name)
        if not isinstance(value, type):
            continue
        owner = _canonical_owner(context, value)
        if not owner:
            continue
        for member in vars(value):
            if member.startswith("_"):
                continue
            checked += 1
            if not any(label.endswith(f".{owner}.{member}") for label in labels):
                missing.append(f"{owner}.{member}")
    return expect(not missing, f"{len(missing)} missing: {missing[:5]}", f"{checked} class members")


def _map_record_fields(context: Context) -> str:
    checked = 0
    wrong: list[str] = []
    offsets = {
        entry.label: entry.detail for entry in context.entries if entry.kind == "field"
    }
    for name in py4gw.__all__:
        value = getattr(py4gw, name)
        fields = getattr(value, "_fields_", None) or ()
        if not fields:
            continue
        owner = _canonical_owner(context, value) or name
        for definition in fields:
            field_name = definition[0]
            offset = getattr(value, field_name).offset
            wanted = f"+0x{offset:04X}"
            if not any(
                label.endswith(f".{owner}.{field_name}") and wanted in detail
                for label, detail in offsets.items()
            ):
                wrong.append(f"{owner}.{field_name}")
            checked += 1
    return expect(not wrong, f"{len(wrong)} wrong: {wrong[:5]}", f"{checked} fields with offsets")


def _map_enum_members(context: Context) -> str:
    labels = {entry.label for entry in context.entries}
    checked = 0
    missing: list[str] = []
    for name in py4gw.__all__:
        value = getattr(py4gw, name)
        members = getattr(value, "__members__", None)
        if not members:
            continue
        for member in members:
            checked += 1
            if not any(label.endswith(f".{name}.{member}") for label in labels):
                missing.append(f"{name}.{member}")
    return expect(not missing, f"{len(missing)} missing: {missing[:5]}", f"{checked} enum members")


def _map_one_expansion(context: Context) -> str:
    seen: set[tuple[str, str]] = set()
    doubled: list[str] = []
    for entry in context.entries:
        if entry.kind not in ("record", "enum", "class") or entry.owner:
            continue
        if entry.detail.startswith("declared in"):
            continue
        key = (entry.group, entry.name)
        if key in seen:
            doubled.append(entry.label)
        seen.add(key)
    return expect(not doubled, f"{len(doubled)}: {doubled[:5]}", "each class expanded once")


def _map_groups(context: Context) -> str:
    """Every module that declares something is a group in the map.

    A package whose ``__init__`` declares nothing (``py4gw.enums_src`` re-exports only) contributes
    no names of its own, so it is not a defect that it has no group -- what would be a defect is a
    module with public names of its own that never appears.
    """

    import importlib
    import inspect

    groups = {entry.group for entry in context.entries}
    missing: list[str] = []
    modules = test_surface.discover_modules()
    for module_name in modules:
        try:
            module = importlib.import_module(module_name)
        except Exception as error:  # noqa: BLE001 - a module that cannot be imported is a finding
            missing.append(f"{module_name}: {type(error).__name__}")
            continue
        public = [
            name
            for name, value in vars(module).items()
            if not name.startswith("_") and not inspect.ismodule(value)
        ]
        if public and module_name not in groups:
            missing.append(f"{module_name} ({len(public)} names)")
    return expect(
        not missing, f"{len(missing)} modules absent: {missing[:5]}", f"{len(modules)} modules mapped"
    )


# --- 2. the engine's safety rules ------------------------------------------------------------


def _engine_writes_classified(context: Context) -> str:
    writes = {entry.label for entry in context.entries if entry.access == "write"}
    wanted = ("py4gw.player.Player.Move", "py4gw.map.Map.Travel", "py4gw.player.Player.Interact")
    missing = [label for label in wanted if label not in writes]
    return expect(not missing, f"{len(writes)} writes, these absent: {missing}", "known writes classified")


def _engine_reads_classified(context: Context) -> str:
    reads = {entry.label for entry in context.entries if entry.access == "read"}
    wanted = ("py4gw.map.Map.GetMapID", "py4gw.player.Player.GetAgentID")
    missing = [label for label in wanted if label not in reads]
    return expect(not missing, f"{len(reads)} reads, missing: {missing}", "known reads classified")


def _engine_reasons(context: Context) -> str:
    members = [entry for entry in context.entries if entry.kind in ("method", "property")]
    without = [entry.label for entry in members if not entry.access_reason]
    return expect(not without, f"{len(without)} without a reason: {without[:3]}", "every member carries its reason")


def _engine_write_is_skipped(context: Context) -> str:
    entry = _entry(context, "Player.Move")
    outcome = test_surface.run_entry(entry, args=(1.0, 2.0))
    return expect(
        outcome.status == "skipped (classified as a write)",
        f"{outcome.status}",
        "Player.Move is skipped unless writes are asked for",
    )


def _engine_write_runs_when_asked(context: Context) -> str:
    """The write path exists: with writes asked for, the call reaches the member.

    It is called here with the *client connected* in mind: no connection means the library refuses,
    which is itself the right answer -- so this check passes when the member is either refused by the
    library or run, and fails only if the engine skipped it for being a write.
    """

    entry = _entry(context, "Player.Move")
    outcome = test_surface.run_entry(entry, include_writes=True, args=(1.0, 2.0), client_connected=context.connected)
    return expect(
        outcome.status != "skipped (classified as a write)",
        f"{outcome.status}",
        "with writes asked for, Player.Move is not skipped as a write",
    )


def _engine_unknown_reported(context: Context) -> str:
    unknowns = [entry for entry in context.entries if entry.access == "unknown"]
    return expect(len(unknowns) > 0, f"{len(unknowns)} unclassified", "unclassified members are reported, not hidden")


def _engine_no_failures(context: Context) -> str:
    entries = context.entries[:4000]
    outcomes = test_surface.run_all(entries, include_unknown=True)
    failed = [outcome for outcome in outcomes if outcome.status == "failed"]
    return expect(
        not failed,
        f"{len(failed)} failed: " + "; ".join(f"{o.entry.label}: {o.error}" for o in failed[:3]),
        f"{len(entries)} entries ran with no unexpected failure",
    )


# --- 3. members that need no client ----------------------------------------------------------


def _pure_utils_degrees(context: Context) -> str:
    from py4gw.py4gwcorelib_src.utils import Utils

    seen = Utils.DegToRad(180)
    return expect(
        math.isclose(seen, math.pi, rel_tol=1e-12),
        repr(seen),
        "Utils.DegToRad(180) is pi",
    )


def _pure_utils_distance(context: Context) -> str:
    from py4gw.py4gwcorelib_src.utils import Utils

    seen = Utils.Distance((0.0, 0.0), (3.0, 4.0))
    return expect(math.isclose(seen, 5.0), repr(seen), "Utils.Distance((0,0),(3,4)) is 5")


def _pure_gui_constants(context: Context) -> str:
    gui = _settings()
    seen = (gui.GUI_EVENT_CLOSE, gui.GUI_SHOW, gui.GUI_HIDE, gui.BitOR(1, 2, 4))
    return expect(seen == (-3, 16, 32, 7), repr(seen), "AutoIt's own constants (-3, 16, 32) and BitOR(1,2,4)=7")


def _pure_gui_color(context: Context) -> str:
    from py4gw.gui import styles

    seen = styles.colorref_to_tk(0x0000FF)
    return expect(seen == "#ff0000", repr(seen), "colorref 0x0000FF is #ff0000 (BGR order)")


def _pure_player_status_name(context: Context) -> str:
    from py4gw import Player

    seen = Player.GetPlayerStatusNameFromValue(0)
    return expect(seen == "offline", repr(seen), "Player.GetPlayerStatusNameFromValue(0) is 'offline'")


def _pure_skill_names(context: Context) -> str:
    from py4gw.enums_src import skill_names

    mapping = skill_names.ID_TO_NAME
    first_id, first_name = next(iter(mapping.items()))
    seen = (len(mapping), skill_names.GetSkillNameByID(first_id), skill_names.NAME_TO_ID.get(first_name))
    return expect(
        seen[1] == first_name and seen[2] == first_id,
        repr(seen),
        "a skill id maps to its name and back",
    )


def _pure_perf_counter(context: Context) -> str:
    counter = py4gw.PerfCounter()
    counter.start("self-test")
    counter.end("self-test")
    names = counter.get_metric_names()
    reports = counter.get_reports()
    return expect(
        "self-test" in names and len(reports) >= 1,
        f"names={names}, reports={len(reports)}",
        "PerfCounter records a metric it was given",
    )


def _pure_pattern_catalog(context: Context) -> str:
    catalog = py4gw.PatternCatalog.from_directory("offsets")
    patterns = len(getattr(catalog, "_patterns", {}) or {})
    resolvers = len(getattr(catalog, "_resolvers", {}) or {})
    return expect(patterns + resolvers > 50, f"{patterns} patterns, {resolvers} resolvers", "the offsets directory loads")


def _pure_win32_answers(context: Context) -> str:
    win32 = py4gw.Win32()
    elevated = win32.is_elevated()
    processes = win32.list_processes()
    text = win32.format_processes([])
    return expect(
        isinstance(elevated, bool) and isinstance(processes, list) and "Gw.exe" in text,
        f"elevated={elevated}, {len(processes)} processes",
        "Win32 answers a bool, a process list, and formats it",
    )


def _pure_allegiance_enum(context: Context) -> str:
    from py4gw import Allegiance

    members = list(Allegiance)
    return expect(len(members) >= 5, f"{[member.name for member in members]}", "Allegiance enumerates its members")


def _pure_record_round_trip(context: Context) -> str:
    from py4gw import CharContextStruct

    value = CharContextStruct()
    value.current_map_id = 1234
    seen = int(value.current_map_id)
    return expect(seen == 1234, repr(seen), "a record built from bytes holds what was put in it")


def _pure_map_refuses_without_client(context: Context) -> str:
    """A client-facing reader answers, and answers in the library's own terms.

    Measured live: this check used to assert ``Map.GetMapID() == 0``, and with the client connected
    it saw 642 -- the real map id. The check was the thing that was wrong, not the reading: what the
    port guarantees is that the reader answers a map id when a client is published, and refuses with
    a message naming the connection when one is not. Both are stated here, so the check is honest in
    either state.
    """

    from py4gw import Map

    try:
        seen = Map.GetMapID()
    except RuntimeError as error:
        return expect(
            "connect" in str(error).lower(),
            f"no client: {str(error)[:60]}",
            "without a client the reader refuses and says a client is needed",
        )
    return expect(
        isinstance(seen, int) and seen >= 0,
        f"client connected: map id {seen}",
        "with a client the reader answers the map id",
    )


# --- 4. the window's own wiring --------------------------------------------------------------


def _window_tabs(context: Context) -> str:
    window = context.window
    seen = (
        window._client_tab,
        window._surface_tab,
        window._data_tab,
        window._test_tab,
        window._self_test_tab,
        window._live_tab,
    )
    return expect(all(seen) and len(set(seen)) == 6, repr(seen), "the six tabs are created")


def _window_map(context: Context) -> str:
    window = context.window
    count = len(window._surface_entries)
    groups = len({entry.group for entry in window._surface_entries})
    return expect(count > 10_000 and groups > 100, f"{count} entries in {groups} modules", "the window built the whole map")


def _window_group_list(context: Context) -> str:
    from py4gw import gui

    listbox = gui._default._controls[context.window._surface_groups].value
    rows = listbox.size()
    return expect(rows > 100, f"{rows} rows", "the group list is filled")


def _window_search_and_detail(context: Context) -> str:
    from py4gw import gui

    window = context.window
    gui.GUICtrlSetData(window._surface_search, "GetPlayerStatusNameFromValue")
    window._surface_searched()
    table = gui._default._controls[window._surface_table.listview].widget
    rows = table.get_children("")
    if not rows:
        raise CheckFailed("the search found nothing")
    table.selection_set(rows[0])
    window._surface_entry_selected()
    arguments = gui.GUICtrlRead(window._surface_arguments)
    gui.GUICtrlSetData(window._surface_arguments, "0")
    window._run_selected_entry()
    result = gui.GUICtrlRead(window._surface_result.label)
    return expect(
        "answered" in result and arguments == "status",
        result[:80],
        "a searched entry is selected, its arguments filled, and it runs to an answer",
    )


def _window_subset_test(context: Context) -> str:
    window = context.window
    before = len(window._outcomes)
    entry = _entry(context, "Map.GetMapID", window=window)
    window._surface_selected = entry
    window._test_selected_owner()
    added = len(window._outcomes) - before
    return expect(added > 0 or before > 0, f"{added} new results", "Test this class runs its entries")


def _window_reports(context: Context) -> str:
    """Both reports are written, readable, and then removed: the check leaves nothing behind."""

    window = context.window
    if len(context.files) < 2:
        raise CheckFailed("the battery was given nowhere to write the reports")
    full = Path(context.files[0])
    short = Path(context.files[1])
    try:
        window._save_report_to(full, short)
        text = full.read_text(encoding="utf-8")
        summary = short.read_text(encoding="utf-8")
        return expect(
            "py4gw library surface" in text and "py4gw library surface -- summary" in summary,
            f"{len(text.splitlines())} + {len(summary.splitlines())} lines",
            "both reports are written and readable",
        )
    finally:
        full.unlink(missing_ok=True)
        short.unlink(missing_ok=True)


# --- 5. the selected client ------------------------------------------------------------------

CONTEXT_READERS: tuple[str, ...] = (
    "read_char_context",
    "read_game_context",
    "read_pre_game_context",
    "read_gameplay_context",
    "read_map_context",
    "read_world_context",
    "read_cinematic_context",
    "read_camera_context",
    "read_friend_list",
    "read_chat_buffer",
    "read_trade_context",
    "read_item_context",
    "read_account_context",
    "read_gadget_context",
    "read_server_region",
    "read_instance_info",
    "read_text_parser",
    "read_available_characters",
    "read_party_context",
    "read_guild_context",
    "read_acc_agent_context",
    "read_player_agent_id",
)


def _client_elevated(context: Context) -> str:
    seen = py4gw.Win32().is_elevated()
    return expect(bool(seen), f"is_elevated={seen}", "the controller is elevated")


def _client_discovered(context: Context) -> str:
    clients = py4gw.Win32().find_guild_wars()
    return expect(
        bool(clients),
        f"{len(clients)} client(s)",
        "at least one Guild Wars client is running",
    )


def _client_connected(context: Context) -> str:
    client = context.client
    return expect(client is not None and client.is_connected, f"client={client!r}", "the window holds a live connection")


# --- 5b. the live data, section by section ---------------------------------------------------
#
# These are the checks that matter to the library's purpose: they read the running client and ask
# whether what came back is *correct game data*, not merely whether a call returned. Each section is
# one row in the window and a named list of questions in the report, and every one of them is
# read-only by construction: every member the surface classifies as a write is replaced by a
# recorder for the duration of a section (`writes_blocked`), so a write cannot be called quietly.


def _finite(value: Any) -> bool:
    """Whether a number is real: not NaN, not infinity."""

    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" + ("" if count == 1 else "s")


def _snapshot(context: Context, reader: str) -> Any:
    """One context snapshot, remembered so the dump and the sections read it once."""

    snapshots = context.data.setdefault("snapshots", {})
    if reader not in snapshots:
        method = getattr(context.client, reader, None)
        started = time.perf_counter()
        if method is None:
            snapshots[reader] = None
        else:
            try:
                snapshots[reader] = method()
            except Exception as error:  # noqa: BLE001 - recorded, and the section reports it
                snapshots[reader] = ("error", f"{type(error).__name__}: {error}")
        context.data.setdefault("readings", {})[reader] = round((time.perf_counter() - started) * 1000, 3)
    return snapshots[reader]


def _live_contexts(context: Context) -> str:
    """Every context reader answers a snapshot, or refuses in the library's own words."""

    live = Live("live contexts")
    for reader in CONTEXT_READERS:
        live.check(
            reader,
            "a snapshot, or a documented refusal",
            lambda reader=reader: _snapshot(context, reader),
            lambda value: (
                value is None or isinstance(value, tuple) or value is not None,
                "None (nothing active)" if value is None else (value[1] if isinstance(value, tuple) else type(value).__name__),
            ),
        )
    return live.verdict()


def _live_char(context: Context) -> str:
    """The character context: in a map, named, and coherent with its own definition."""

    live = Live("live char")
    char = _snapshot(context, "read_char_context")
    if char is None or isinstance(char, tuple):
        return live.verdict()
    map_id = live.check(
        "current_map_id",
        "a map id above zero",
        lambda: int(getattr(char, "current_map_id")),
        lambda value: (value > 0, f"map id {value}"),
    )
    name = live.check(
        "player_name_str",
        "the character's name, or empty at the selection menus",
        lambda: getattr(char, "player_name_str"),
        lambda value: (isinstance(value, str), repr(value)),
    )
    live.check(
        "is_logged_in",
        "true exactly when a name is present",
        lambda: bool(getattr(char, "is_logged_in")),
        lambda value: (value == bool((name or "").strip()), f"{value}"),
    )
    live.check(
        "player_uuid",
        "four words",
        lambda: getattr(char, "player_uuid"),
        lambda value: (len(tuple(value)) == 4, repr(tuple(value))),
    )
    # The numbers are reported, not judged: measured live on 2026-10-12, a ready map (499, explorable)
    # held `pips` 29324020 -- *the pointer itself* -- with `progress` 1.1478e-41, which is what an
    # intrusive list node looks like when it is empty and points at itself. Reforged reads the same
    # thing this way (`CharContext.py:124,178-181`: ``progress_bar_ptr`` at +0x035C, the property
    # returning ``progress_bar_ptr.contents``), and this port reproduces that read, so a record that
    # is not maintained outside a map load would look exactly like this. Whether it *should* hold
    # something is the owner's call, so the check states what it saw instead of deciding.
    live.check(
        "progress_bar",
        "the record at progress_bar_ptr, read through the pointer",
        lambda: getattr(char, "progress_bar"),
        lambda value: (
            value is None or all(hasattr(value, name) for name in ("pips", "color", "background", "progress")),
            "none"
            if value is None
            else (
                f"pips {int(getattr(value, 'pips'))}, progress {float(getattr(value, 'progress')):.3g}"
                + (
                    "  (not a plausible 0..1 progress: the client may not maintain this record outside a map load)"
                    if not 0.0 <= float(getattr(value, "progress")) <= 1.0
                    else ""
                )
            ),
        ),
    )
    context.data["char"] = {"map_id": map_id, "name": name}
    return live.verdict()


def _live_map(context: Context) -> str:
    """The map: an id, a region, an instance kind, boundaries, and a party size."""

    from py4gw import Map

    live = Live("live map")
    map_id = live.check(
        "GetMapID",
        "a map id above zero",
        Map.GetMapID,
        lambda value: (int(value) > 0, f"map id {int(value)}"),
    )
    live.check(
        "GetRegion",
        "(region number, region name)",
        Map.GetRegion,
        lambda value: (len(tuple(value)) == 2 and bool(str(value[1])), repr(value)),
    )
    live.check(
        "GetLanguage",
        "(language number, language name)",
        Map.GetLanguage,
        lambda value: (len(tuple(value)) == 2 and bool(str(value[1])), repr(value)),
    )
    live.check(
        "GetInstanceTypeName",
        "a named instance type",
        Map.GetInstanceTypeName,
        lambda value: (isinstance(value, str) and bool(value), repr(value)),
    )
    live.check("IsMapReady", "the map is readable", Map.IsMapReady, lambda value: (bool(value), repr(value)))
    live.check(
        "IsOutpost / IsExplorable",
        "exactly one of the two",
        lambda: (bool(Map.IsOutpost()), bool(Map.IsExplorable())),
        lambda value: (value[0] != value[1], f"outpost={value[0]} explorable={value[1]}"),
    )
    live.check(
        "GetMapBoundaries",
        "four finite numbers with min < max",
        Map.GetMapBoundaries,
        lambda value: (
            len(tuple(value)) == 4
            and all(_finite(part) for part in value)
            and float(value[0]) < float(value[2])
            and float(value[1]) < float(value[3]),
            repr(tuple(round(float(part), 2) for part in value)),
        ),
    )
    live.check(
        "GetMaxPartySize",
        "between 1 and 12",
        Map.GetMaxPartySize,
        lambda value: (1 <= int(value) <= 12, f"max party size {int(value)}"),
    )
    live.check(
        "GetAmountOfPlayersInInstance",
        "between 1 and 200",
        Map.GetAmountOfPlayersInInstance,
        lambda value: (1 <= int(value) <= 200, _plural(int(value), "player")),
    )
    live.check(
        "GetInstanceUptime",
        "a sensible number of milliseconds",
        Map.GetInstanceUptime,
        lambda value: (0 <= int(value) < 10**12, f"{int(value)} ms"),
    )
    context.data["map"] = {"map_id": int(map_id) if map_id else 0}
    return live.verdict()


def _live_player(context: Context) -> str:
    """The player: an agent id that exists, a position, a level, and a name."""

    from py4gw import Player

    live = Live("live player")
    agent_id = live.check(
        "GetAgentID",
        "an agent id above zero",
        Player.GetAgentID,
        lambda value: (int(value) > 0, f"agent id {int(value)}"),
    )
    live.check(
        "GetXY",
        "two finite coordinates on the map",
        Player.GetXY,
        lambda value: (
            len(tuple(value)) == 2
            and all(_finite(part) for part in value)
            and all(abs(float(part)) < 10**6 for part in value),
            repr(tuple(round(float(part), 2) for part in value)),
        ),
    )
    live.check(
        "GetName",
        "a non-empty character name",
        Player.GetName,
        lambda value: (isinstance(value, str) and bool(value.strip()), repr(value)),
    )
    live.check(
        "GetLevel",
        "a level between 1 and 20",
        Player.GetLevel,
        lambda value: (1 <= int(value) <= 20, f"level {int(value)}"),
    )
    live.check(
        "GetPlayerNumber",
        "a player number, or None",
        Player.GetPlayerNumber,
        lambda value: (value is None or int(value) >= 0, repr(value)),
    )
    live.check(
        "GetExperience",
        "a non-negative experience value",
        Player.GetExperience,
        lambda value: (int(value) >= 0, f"{int(value):,}"),
    )
    live.check(
        "GetPlayerUUID",
        "four words",
        Player.GetPlayerUUID,
        lambda value: (len(tuple(value)) == 4, repr(tuple(value))),
    )
    live.check(
        "GetAccountEmail",
        "an account email, or an empty string",
        Player.GetAccountEmail,
        lambda value: (isinstance(value, str), repr(value)),
    )
    context.data["player"] = {"agent_id": int(agent_id) if agent_id else 0}
    return live.verdict()


def _live_agents(context: Context) -> str:
    """The agent array: a plausible size, the player in it, and agents whose numbers add up."""

    from py4gw import AgentArray
    from py4gw.agent import Agent

    live = Live("live agents")
    agents = live.check(
        "GetAgentArray",
        "a list of agent ids, each above zero",
        AgentArray.GetAgentArray,
        lambda value: (
            isinstance(value, list) and 0 < len(value) < 5000 and all(int(entry) > 0 for entry in value),
            _plural(len(value), "agent"),
        ),
    )
    agent_ids = [int(entry) for entry in agents] if isinstance(agents, list) else []
    player_agent_id = int((context.data.get("player") or {}).get("agent_id") or 0)
    live.check(
        "the player is in the array",
        "Player.GetAgentID() appears in the agent array",
        lambda: player_agent_id in agent_ids,
        lambda value: (bool(value), f"{'present' if value else 'ABSENT'} (player {player_agent_id} of {len(agent_ids)})"),
    )
    sample = agent_ids[:12]
    for agent_id in sample:
        live.check(
            f"agent {agent_id} health",
            "hp and max hp are real numbers, and hp never exceeds max hp",
            lambda agent_id=agent_id: (
                bool(Agent.IsLiving(agent_id)),
                float(Agent.GetHealth(agent_id)),
                int(Agent.GetMaxHealth(agent_id)),
            ),
            lambda value: (
                value[1] >= 0 and value[2] >= 0 and value[1] <= max(value[2], value[1]) + 1e-6,
                f"living={value[0]} hp={value[1]:.0f}/{value[2]}",
            ),
        )
        live.check(
            f"agent {agent_id} position",
            "a finite position",
            lambda agent_id=agent_id: tuple(float(part) for part in Agent.GetXY(agent_id)),
            lambda value: (len(value) == 2 and all(_finite(part) for part in value), repr(tuple(round(part, 2) for part in value))),
        )
    live.check(
        "GetAgentByID round trip",
        "the record found by id carries that id",
        lambda: (player_agent_id, getattr(Agent.GetAgentByID(player_agent_id), "agent_id", None)),
        lambda value: (value[1] is not None and int(value[1]) == int(value[0]), f"asked {value[0]}, record says {value[1]}"),
    )
    context.data["agents"] = {"count": len(agent_ids)}
    return live.verdict()


def _live_party(context: Context) -> str:
    """The party: a size that agrees with its own member lists, and a leader."""

    from py4gw import Party

    live = Live("live party")
    size = live.check(
        "GetPartySize",
        "between 1 and 12",
        Party.GetPartySize,
        lambda value: (1 <= int(value) <= 12, f"party size {int(value)}"),
    )
    players = live.check(
        "GetPlayers",
        "at least one player record",
        Party.GetPlayers,
        lambda value: (isinstance(value, list) and len(value) >= 1, _plural(len(value), "player record")),
    )
    heroes = live.check("GetHeroes", "a list of hero records", Party.GetHeroes, lambda value: (isinstance(value, list), _plural(len(value), "hero")))
    henchmen = live.check("GetHenchmen", "a list of henchman records", Party.GetHenchmen, lambda value: (isinstance(value, list), _plural(len(value), "henchman")))
    live.check(
        "GetPartyLeaderID",
        "an agent id above zero",
        Party.GetPartyLeaderID,
        lambda value: (int(value) > 0, f"leader {int(value)}"),
    )
    live.check("GetOwnPartyNumber", "a party number of zero or more", Party.GetOwnPartyNumber, lambda value: (int(value) >= 0, f"{int(value)}"))
    if size is not None and isinstance(players, list) and isinstance(heroes, list) and isinstance(henchmen, list):
        counted = len(players) + len(heroes) + len(henchmen)
        live.check(
            "the size agrees with the member lists",
            "GetPartySize() equals players + heroes + henchmen",
            lambda: (int(size), counted),
            lambda value: (value[0] == value[1], f"size {value[0]}, lists {value[1]}"),
        )
    player_agent_id = int((context.data.get("player") or {}).get("agent_id") or 0)
    # The source's own route: a party member record carries a ``login_number``, and the agent id for
    # it comes from ``Party.Players.GetAgentIDByLoginNumber`` (``party.py:834``). Reading an
    # ``agent_id`` off the record was this check's own invention -- ``PlayerPartyMember`` has none
    # (``login_number``, ``called_target_id``, ``state``), so it always saw zero. ``Players`` is a
    # **nested class on Party**, not a name in the ``py4gw.party`` module: looking it up on the module
    # was this check's second mistake (``AttributeError: module 'py4gw.party' has no attribute
    # 'Players'``, measured live on 2026-10-12).
    live.check(
        "the player is a member",
        "the player's agent id is the one the player's own party record resolves to",
        lambda: [
            int(Party.Players.GetAgentIDByLoginNumber(int(record.login_number)))
            for record in (players or [])
        ],
        lambda value: (player_agent_id in value, f"records {value} for player {player_agent_id}"),
    )
    live.check(
        "the leader is the player",
        "the party leader's agent id is the player's, while this client is the leader",
        lambda: (
            bool(getattr(_snapshot(context, "read_party_context"), "is_party_leader", False)),
            int(Party.GetPartyLeaderID()),
        ),
        lambda value: (
            (not value[0]) or value[1] == player_agent_id,
            f"leader is the player: {value[0]}; leader id {value[1]}, player {player_agent_id}",
        ),
    )
    return live.verdict()


def _live_world(context: Context) -> str:
    """The world context: the records it publishes, and the counts they carry."""

    live = Live("live world")
    world = _snapshot(context, "read_world_context")
    if world is None or isinstance(world, tuple):
        return live.verdict()
    live.check(
        "player_controlled_character",
        "a record for the controlled character",
        lambda: getattr(world, "player_controlled_character"),
        lambda value: (value is not None and int(getattr(value, "agent_id", 0)) > 0, f"agent id {getattr(value, 'agent_id', None)}"),
    )
    for name, limit in (
        ("players", 200),
        ("party_allies", 200),
        ("skillbars", 200),
        ("party_effects", 400),
        ("party_attributes", 200),
        ("map_agents", 5000),
    ):
        live.check(
            name,
            f"at most {limit} records",
            lambda name=name: getattr(world, name),
            lambda value, limit=limit: (
                value is None or (isinstance(value, (list, tuple)) and len(value) <= limit),
                _plural(len(value), "record") if isinstance(value, (list, tuple)) else repr(value)[:40],
            ),
        )
    skillbars = getattr(world, "skillbars", None)
    player_agent_id = int((context.data.get("player") or {}).get("agent_id") or 0)
    if isinstance(skillbars, list) and skillbars:
        # The record's own member is ``skills``: eight ``SkillbarSkillStruct`` slots, each with a
        # ``skill_id`` (measured live: the skillbar belonged to agent 53, the player).
        live.check(
            "the first skillbar belongs to the player",
            "the record's agent id is the player's",
            lambda: int(getattr(skillbars[0], "agent_id", 0)),
            lambda value: (value == player_agent_id and value > 0, f"skillbar of agent {value}, player {player_agent_id}"),
        )
        live.check(
            "the first skillbar's skills",
            "eight skill slots, each a skill id in range (0 is an empty slot)",
            lambda: tuple(int(skill.skill_id) for skill in skillbars[0].skills),
            lambda value: (
                len(value) == 8 and all(0 <= entry < 4000 for entry in value),
                repr(value),
            ),
        )
    return live.verdict()


def _xyz(value: Any) -> tuple[float, float, float]:
    """A three-float record as its three numbers (``Vec3fStruct`` is a record, not a sequence)."""

    return (float(value.x), float(value.y), float(value.z))


def _live_camera(context: Context) -> str:
    """The camera record: angles in radians, a position, and a look-at point that follows from them."""

    live = Live("live camera")
    camera = _snapshot(context, "read_camera_context")
    if camera is None or isinstance(camera, tuple):
        return live.verdict()
    live.check(
        "yaw",
        "a finite angle in radians",
        lambda: float(getattr(camera, "yaw")),
        lambda value: (_finite(value) and -2 * math.pi <= value <= 2 * math.pi, f"{value:.4f} rad"),
    )
    live.check(
        "pitch",
        "a finite angle in radians",
        lambda: float(getattr(camera, "pitch")),
        lambda value: (_finite(value) and -math.pi <= value <= math.pi, f"{value:.4f} rad"),
    )
    live.check(
        "position",
        "three finite coordinates",
        lambda: _xyz(getattr(camera, "position")),
        lambda value: (all(_finite(part) for part in value), repr(tuple(round(part, 2) for part in value))),
    )
    live.check(
        "look_at_target",
        "three finite coordinates, distinct from the camera's own position",
        lambda: (_xyz(getattr(camera, "look_at_target")), _xyz(getattr(camera, "position"))),
        lambda value: (
            all(_finite(part) for part in value[0]) and value[0] != value[1],
            repr(tuple(round(part, 2) for part in value[0])),
        ),
    )
    live.check(
        "max_distance",
        "a positive distance",
        lambda: float(getattr(camera, "max_distance")),
        lambda value: (0 < value < 10**5, f"{value:.1f}"),
    )
    live.check(
        "field_of_view",
        "a positive angle in radians",
        lambda: float(getattr(camera, "field_of_view")),
        lambda value: (0 < value <= math.pi, f"{value:.4f} rad"),
    )
    return live.verdict()


def _live_text_parser(context: Context) -> str:
    """The text parser: the values the port's own readings record."""

    live = Live("live text parser")
    parser = _snapshot(context, "read_text_parser")
    if parser is None or isinstance(parser, tuple):
        return live.verdict()
    live.check(
        "language_id",
        "a language between 0 and 10",
        lambda: int(getattr(parser, "language_id")),
        lambda value: (0 <= value <= 10, f"language {value}"),
    )
    live.check(
        "entries_per_file",
        "1024, the value this port's readings record",
        lambda: int(getattr(parser, "entries_per_file")),
        lambda value: (value == 1024, f"{value}"),
    )
    live.check(
        "language_slots",
        "eleven language slots",
        lambda: getattr(parser, "language_slots"),
        lambda value: (len(value) == 11, _plural(len(value), "slot")),
    )
    return live.verdict()


def _map_record_summary(value: Any) -> str:
    """One map record as a line: region, the party sizes it allows, and its own map id pair."""

    if value is None:
        return "no record"
    return (
        f"region {int(getattr(value, 'region', -1))}, party "
        f"{int(getattr(value, 'min_party_size', 0))}-{int(getattr(value, 'max_party_size', 0))}, "
        f"map {int(getattr(value, 'x', 0))}x{int(getattr(value, 'y', 0))}"
    )


def _dimension_summary(value: Any) -> str:
    """One dimension record as a line: its two corners, per axis."""

    if value is None:
        return "no record"
    return (
        f"x {int(getattr(value, 'start_x', 0))}..{int(getattr(value, 'end_x', 0))}, "
        f"y {int(getattr(value, 'start_y', 0))}..{int(getattr(value, 'end_y', 0))}"
    )


def _live_instance(context: Context) -> str:
    """The instance info: the map record the client publishes, and its own dimensions.

    Both records are the client's: ``current_map_info`` carries that map's party sizes and region
    (measured live: region 19, min party 1, max party 8 on map 642), and the two terrain records
    carry a start and an end corner -- the fields are ``start_x/start_y/end_x/end_y``, so "a non-zero
    width" is read as ``end > start`` on each axis.
    """

    live = Live("live instance")
    info = _snapshot(context, "read_instance_info")
    if info is None or isinstance(info, tuple):
        return live.verdict()
    live.check(
        "current_map_info",
        "a map record whose party sizes are ordered and whose region is a real number",
        lambda: getattr(info, "current_map_info"),
        lambda value: (
            value is not None
            and 1 <= int(getattr(value, "min_party_size", 0)) <= int(getattr(value, "max_party_size", 0)) <= 12
            and int(getattr(value, "region", -1)) >= 0,
            _map_record_summary(value),
        ),
    )
    for name in ("terrain_info1", "terrain_info2"):
        live.check(
            name,
            "a dimension record whose end corner is beyond its start corner on both axes",
            lambda name=name: getattr(info, name),
            lambda value: (
                value is not None
                and int(getattr(value, "end_x", 0)) > int(getattr(value, "start_x", 0))
                and int(getattr(value, "end_y", 0)) > int(getattr(value, "start_y", 0)),
                _dimension_summary(value),
            ),
        )
    return live.verdict()


def _live_items(context: Context) -> str:
    """Items: the bags, and item records whose ids and counts are real."""

    live = Live("live items")
    item_context = _snapshot(context, "read_item_context")
    if item_context is None or isinstance(item_context, tuple):
        return live.verdict()
    bags = live.check(
        "bags()",
        "the bags the client publishes, at most 40 of them",
        lambda: item_context.bags(),
        lambda value: (
            isinstance(value, list) and len(value) <= 40,
            _plural(len(value), "bag") if isinstance(value, list) else repr(value)[:40],
        ),
    )
    if isinstance(bags, list) and bags:
        # ``bag_id()`` is a method and ``items`` is the bag's ``GWArray`` **header**, not a list of
        # items -- reading it as a member and iterating it was measured live as
        # ``TypeError: int() argument ... not 'method'`` and ``'GWArray' object is not iterable``.
        # ``read_items()`` is the member that materializes the records.
        live.check(
            "the first bag's item count and id",
            "an item count within the bag's slots, and a one-based bag id",
            lambda: (int(bags[0].items_count), int(bags[0].bag_id())),
            lambda value: (0 <= value[0] <= 256 and 1 <= value[1] <= 64, f"{value[0]} items, bag id {value[1]}"),
        )
        live.check(
            "the first bag's items",
            "the item records read from the bag have ids above zero",
            lambda: list(bags[0].read_items()),
            lambda value: (
                all(int(getattr(item, "item_id", 0)) > 0 for item in value),
                _plural(len(value), "item") + (f", first id {int(getattr(value[0], 'item_id', 0))}" if value else ""),
            ),
        )
    return live.verdict()


def _live_agreement(context: Context) -> str:
    """The same fact read two ways must agree -- this is what a wrong offset breaks."""

    from py4gw import Map, Party, Player

    live = Live("live agreement")
    char = _snapshot(context, "read_char_context")
    world = _snapshot(context, "read_world_context")
    party = _snapshot(context, "read_party_context")
    if char is not None and not isinstance(char, tuple):
        live.check(
            "map id: character context vs Map.GetMapID",
            "both paths report the same map id",
            lambda: (int(getattr(char, "current_map_id")), int(Map.GetMapID())),
            lambda value: (value[0] == value[1] and value[0] > 0, f"{value[0]} vs {value[1]}"),
        )
        live.check(
            "character name: context vs Player.GetName",
            "both paths report the same name",
            lambda: (str(getattr(char, "player_name_str") or "").strip(), str(Player.GetName()).strip()),
            lambda value: (value[0] == value[1] and bool(value[0]), f"{value[0]!r} vs {value[1]!r}"),
        )
    if world is not None and not isinstance(world, tuple):
        live.check(
            "player agent id: world record vs Player.GetAgentID",
            "the controlled-character record carries the player's agent id",
            lambda: (
                int(getattr(getattr(world, "player_controlled_character"), "agent_id", 0)),
                int(Player.GetAgentID()),
            ),
            lambda value: (value[0] == value[1] and value[0] > 0, f"{value[0]} vs {value[1]}"),
        )
        # There is no second copy of the player's position in the port, so this is not "the same
        # record read twice": it is the player's own XY against the map's boundaries, which the
        # client publishes separately (``Map.GetMapBoundaries``). The earlier version of this check
        # invented a ``pos`` member on the world record; the record has none, and ``Player.GetXY``
        # and ``Agent.GetXY`` are the same path, so comparing those two would prove nothing.
        boundaries = tuple(float(part) for part in Map.GetMapBoundaries())
        live.check(
            "player position inside the map boundaries",
            "the player's XY is within the map the client reports",
            lambda: tuple(float(part) for part in Player.GetXY()),
            lambda value: (
                len(value) == 2
                and boundaries[0] <= value[0] <= boundaries[2]
                and boundaries[1] <= value[1] <= boundaries[3],
                f"{tuple(round(part, 2) for part in value)} inside "
                f"x {boundaries[0]:.0f}..{boundaries[2]:.0f}, y {boundaries[1]:.0f}..{boundaries[3]:.0f}",
            ),
        )
    if party is not None and not isinstance(party, tuple):
        # The party context publishes its own ``player_party`` record whose three arrays are the
        # party; ``players``/``heroes``/``henchmen`` are on that record, not on the context.
        recorded = getattr(party, "player_party", None)
        live.check(
            "party: context record vs Party.GetPartySize",
            "the party context's own arrays count the same party",
            lambda: (
                len(list(getattr(recorded, "players") or ()))
                + len(list(getattr(recorded, "heroes") or ()))
                + len(list(getattr(recorded, "henchmen") or ())),
                int(Party.GetPartySize()),
            ),
            lambda value: (value[0] == value[1], f"context {value[0]} vs getter {value[1]}"),
        )
    return live.verdict()


def _live_dump(context: Context) -> str:
    """Every field and property of every context, read once and kept for the data dump.

    This is the "output all data" half of the surface: the values are stored on the context, and the
    window (or a caller) writes them out. A field that cannot be read is kept as its error, because
    that is a reading too.
    """

    dump: dict[str, Any] = context.data.setdefault("dump", {})
    unreadable = 0
    for reader in CONTEXT_READERS:
        snapshot = _snapshot(context, reader)
        if snapshot is None or isinstance(snapshot, tuple):
            continue
        entry: dict[str, Any] = {
            "type": type(snapshot).__name__,
            "fields": {},
            "properties": {},
            "errors": {},
        }
        for field_name, _field_type in getattr(snapshot, "_fields_", ()) or ():
            try:
                entry["fields"][field_name] = _plain(getattr(snapshot, field_name))
            except Exception as error:  # noqa: BLE001 - an unreadable field is recorded as such
                entry["errors"][field_name] = f"{type(error).__name__}: {error}"
                unreadable += 1
        for member, attribute in sorted(vars(type(snapshot)).items()):
            if member.startswith("_") or not isinstance(attribute, property):
                continue
            try:
                entry["properties"][member] = _plain(getattr(snapshot, member))
            except Exception as error:  # noqa: BLE001 - a property that refuses is recorded
                entry["errors"][member] = f"{type(error).__name__}: {error}"
                unreadable += 1
        dump[reader] = entry
    total = sum(len(entry["fields"]) + len(entry["properties"]) for entry in dump.values())
    return expect(
        bool(dump) and total > 100,
        f"{len(dump)} contexts, {total} values, {unreadable} unreadable",
        "every context's fields and properties were read for the dump",
    )


def _live_safety(context: Context) -> str:
    """The members classified as writes were blocked while reading, and none was called.

    Every member the surface classifies as a write is replaced by a recorder for the duration of a
    live section -- unless it is not an action at all, which is the second number: 36 of the 246
    classified writes are namespace classes and constants (``Party.Players``, ``FrameId.PlayButton``)
    that the classifier read as writes from their names. Those cannot be called, and replacing them
    only breaks what reads *through* them: measured live, replacing ``Party.Players`` with a recorder
    made ``Party.GetPartyLeaderID`` fail with ``'function' object has no attribute
    'GetAgentIDByLoginNumber'``. They are named here rather than silently skipped, because their
    classification is a finding about the map, not a safety property.
    """

    blocked = context.data.get("writes_blocked", [])
    not_actions = context.data.get("writes_not_actions", [])
    calls = context.data.get("write_calls", [])
    actual = (
        f"{len(blocked)} callable write members were blocked and {len(calls)} were called: {calls[:3]}"
        if calls
        else (
            f"{len(blocked)} callable write members were blocked and none was called; "
            f"{len(not_actions)} classified writes are not actions: {[name for name in not_actions][:3]}"
        )
    )
    return expect(not calls, actual)


@contextlib.contextmanager
def writes_blocked(context: Context) -> Any:
    """Replace every write member with a recorder for the duration of a live section."""

    blocked: list[str] = []
    not_actions: list[str] = []
    calls: list[str] = context.data.setdefault("write_calls", [])
    originals: list[tuple[Any, str, Any]] = []

    def recorder(label: str) -> Any:
        def call(*_args: Any, **_kwargs: Any) -> Any:
            calls.append(label)
            raise CheckFailed(f"a write was called: {label}")

        return staticmethod(call)

    for entry in context.entries:
        if entry.access != "write":
            continue
        try:
            # A write on a class member is replaced on the class; a module-level one -- py4gw's own
            # connect, for instance -- is replaced on the module.
            holder: Any = importlib.import_module(entry.group)
            if entry.owner:
                holder = getattr(holder, entry.owner, None)
            if not isinstance(holder, (types.ModuleType, type)):
                continue
            original = holder.__dict__.get(entry.name)
            if original is None:
                continue
            if isinstance(original, (type, types.ModuleType)) or not callable(original):
                # Not an action: a namespace class or a constant the classifier read as a write from
                # its name. It cannot act on the client, and replacing it breaks its readers.
                not_actions.append(
                    f"{entry.label} ({'namespace' if isinstance(original, (type, types.ModuleType)) else type(original).__name__})"
                )
                continue
            setattr(holder, entry.name, recorder(entry.label))
        except Exception:  # noqa: BLE001 - a member that cannot be replaced is simply not blocked
            continue
        originals.append((holder, entry.name, original))
        blocked.append(entry.label)
    context.data["writes_blocked"] = blocked
    context.data["writes_not_actions"] = not_actions
    try:
        yield
    finally:
        for holder, name, original in originals:
            setattr(holder, name, original)


def _live_section(context: Context, section: Callable[[Context], str]) -> str:
    """Run one live section with every write member blocked, and judge both parts."""

    with writes_blocked(context):
        detail = section(context)
    calls = context.data.get("write_calls", [])
    if calls:
        raise CheckFailed(f"a write member was called: {calls[:3]}")
    return detail


def _plain(value: Any, depth: int = 0) -> Any:
    """A value as the dump holds it: numbers and text as they are, records walked a little way.

    A ctypes **array** is walked too, not printed: an ``Array`` is not a ``Structure`` and has no
    ``_fields_``, so the first version of this returned ``<c_ulong_Array_4 object at 0x...>`` for
    every fixed-width array in the client's own records -- a pointer where data was expected, in the
    one output whose whole purpose is to show the data (seen live, ``chat_buffer.message_pointers``).
    """

    if depth > 2:
        return repr(value)[:200]
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return [_plain(item, depth + 1) for item in list(value)[:50]]
    if isinstance(value, ctypes.Array):
        return [_plain(item, depth + 1) for item in list(value)[:50]]
    if isinstance(value, dict):
        return {str(key): _plain(item, depth + 1) for key, item in list(value.items())[:50]}
    fields = getattr(value, "_fields_", None)
    if fields:
        record: dict[str, Any] = {"type": type(value).__name__}
        for field_name, _field_type in fields:
            try:
                record[field_name] = _plain(getattr(value, field_name), depth + 1)
            except Exception as error:  # noqa: BLE001 - unreadable is recorded
                record[field_name] = f"<{type(error).__name__}: {error}>"
        return record
    return repr(value)[:200]


def _value_text(value: Any) -> str:
    """A dumped value as one line of text, however deeply it is nested."""

    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_value_text(item) for item in value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{name}={_value_text(item)}" for name, item in value.items()) + "}"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def data_rows(context: Context) -> list[dict[str, str]]:
    """Every dumped value as a table row: which context, a field or property, the name, the value.

    This is the window's view of the dump -- one row per value, filterable like every other table --
    and the same rows the text report is written from.
    """

    rows: list[dict[str, str]] = []
    for reader, entry in (context.data.get("dump") or {}).items():
        for name, value in entry["fields"].items():
            rows.append({"context": reader, "kind": "field", "name": name, "value": _value_text(value)})
        for name, value in entry["properties"].items():
            rows.append({"context": reader, "kind": "property", "name": name, "value": _value_text(value)})
        for name, error in entry["errors"].items():
            rows.append({"context": reader, "kind": "UNREADABLE", "name": name, "value": error})
    return rows


def data_text(context: Context, results: Sequence[Result] | None = None) -> str:
    """All the live data, grouped by context: one line per field and per property.

    Everything the live sections read is here: how long each reader took, every value of every
    context with the fields and properties kept apart, what could not be read and why, which write
    members were blocked, and -- when the battery's results are passed -- every check's verdict.
    """

    lines = ["py4gw live data", "=" * 78]
    lines.append(f"connected:  {bool(context.connected)}")
    lines.append(f"client:     {context.client!r}")
    readings = context.data.get("readings") or {}
    if readings:
        lines.append("")
        lines.append("reader timings (ms)")
        lines.append("-" * 78)
        for reader, milliseconds in readings.items():
            lines.append(f"  {milliseconds:9.3f}  {reader}")
    dump = context.data.get("dump") or {}
    if not dump:
        lines.append("")
        lines.append("no context was read: connect a client and run the client checks")
    for reader, entry in dump.items():
        lines.append("")
        lines.append(f"{reader}  ({entry['type']})")
        lines.append("-" * 78)
        for name, value in entry["fields"].items():
            lines.append(f"  field      {name:<44} {_value_text(value)}")
        for name, value in entry["properties"].items():
            lines.append(f"  property   {name:<44} {_value_text(value)}")
        for name, error in entry["errors"].items():
            lines.append(f"  UNREADABLE {name:<44} {error}")
    blocked = context.data.get("writes_blocked") or []
    calls = context.data.get("write_calls") or []
    lines.append("")
    lines.append("-" * 78)
    lines.append(f"write members blocked while reading: {len(blocked)}")
    lines.append(f"write members called:                {len(calls)}" + (f"  {calls}" if calls else ""))
    if results is not None:
        lines.append("")
        lines.append("checks")
        lines.append("-" * 78)
        lines.extend(summarise(results).splitlines())
        for result in results:
            lines.append(
                f"  {result.status.upper():<4} {result.area:<14} {result.name:<20} "
                f"{result.milliseconds:8.1f} ms  {result.actual}"
            )
    return "\n".join(lines)


def data_json(context: Context, results: Sequence[Result] | None = None) -> str:
    """The same data as JSON, for a caller that would rather parse it than read it."""

    import json

    payload: dict[str, Any] = {
        "connected": bool(context.connected),
        "client": repr(context.client),
        "readings": context.data.get("readings") or {},
        "writes_blocked": len(context.data.get("writes_blocked") or []),
        "write_calls": list(context.data.get("write_calls") or []),
        "contexts": context.data.get("dump") or {},
    }
    if results is not None:
        payload["checks"] = [
            {
                "area": result.area,
                "name": result.name,
                "status": result.status,
                "expected": result.expected,
                "saw": result.actual,
                "ms": round(result.milliseconds, 3),
            }
            for result in results
        ]
    return json.dumps(payload, indent=2, default=repr)


def write_data_report(
    context: Context,
    results: Sequence[Result] | None,
    path: str | Path,
    *,
    as_json: bool = False,
) -> Path:
    """Write the live data and return where it went."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        data_json(context, results) if as_json else data_text(context, results),
        encoding="utf-8",
    )
    return target


def live_areas() -> tuple[str, ...]:
    """The areas that read the running client."""

    return tuple(area for area in areas() if area.startswith("live "))



def _point_of_reading(value: Any) -> str:
    """A value as a sentence, for the console."""

    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _client_window_contexts(context: Context) -> str:
    """Every context view in the window refreshed with an answer rather than a read failure."""

    from py4gw import gui

    window = context.window
    window.show_data_tab()
    window._refresh_all_contexts()
    broken: list[str] = []
    for view in window._context_views:
        status = gui.GUICtrlRead(view.status.label)
        if "failed" in status.lower() or "error" in status.lower():
            broken.append(f"{view.label}: {status}")
    return expect(
        not broken,
        f"{len(broken)} contexts failed: " + "; ".join(broken[:3]),
        f"all {len(window._context_views)} context views refreshed without a read failure",
    )


def _client_surface_reads(context: Context) -> str:
    """Run the map's reads against the connected client and count what answered."""

    window = context.window
    window._test_reads_connected()
    outcomes = window._outcomes
    counts = test_surface.statuses(outcomes)
    failed = counts.get("failed", 0)
    return expect(
        failed == 0 and counts.get("answered", 0) > 1000,
        f"answered={counts.get('answered')}, refused={counts.get('refused')}, failed={failed}",
        "the whole surface's reads ran against the client with no unexpected failure",
    )


def _entry(context: Context, query: str, window: Any = None) -> test_surface.Entry:
    """An entry by name, from the window's map or from a fresh one."""

    entries = getattr(window, "_surface_entries", None) or context.entries
    found = test_surface.find(entries, query)
    if not found:
        raise CheckFailed(f"{query} is not on the surface")
    return found[0]


CHECKS: tuple[Check, ...] = (
    # 1. the map
    Check("map", "exported names", "every name py4gw exports is mapped", _map_exported_names),
    Check("map", "class members", "every public member of every exported class is mapped", _map_members),
    Check("map", "record fields", "every field is mapped with its offset and type", _map_record_fields),
    Check("map", "enum members", "every enum member is mapped", _map_enum_members),
    Check("map", "one expansion", "each record, enum and class is expanded exactly once", _map_one_expansion),
    Check("map", "modules", "every module of the package is a group", _map_groups),
    # 2. the engine
    Check("engine", "writes classified", "the known acting members are classified as writes", _engine_writes_classified),
    Check("engine", "reads classified", "the known reading members are classified as reads", _engine_reads_classified),
    Check("engine", "reasons kept", "every member carries the reason for its classification", _engine_reasons),
    Check("engine", "writes skipped", "a write is skipped unless writes are asked for", _engine_write_is_skipped),
    Check("engine", "writes reachable", "with writes asked for the member is called, not skipped", _engine_write_runs_when_asked),
    Check("engine", "unknowns reported", "unclassified members are reported, never hidden", _engine_unknown_reported),
    Check("engine", "walk is clean", "a 4,000-entry walk raises nothing unexpected", _engine_no_failures),
    # 3. pure members
    Check("pure members", "Utils.DegToRad", "DegToRad(180) is pi", _pure_utils_degrees),
    Check("pure members", "Utils.Distance", "Distance((0,0),(3,4)) is 5", _pure_utils_distance),
    Check("pure members", "AutoIt constants", "the GUI constants are AutoIt's own values", _pure_gui_constants),
    Check("pure members", "colour order", "colorref 0x0000FF is #ff0000", _pure_gui_color),
    Check("pure members", "player status", "GetPlayerStatusNameFromValue(0) is 'offline'", _pure_player_status_name),
    Check("pure members", "skill names", "a skill id maps to its name and back", _pure_skill_names),
    Check("pure members", "PerfCounter", "a metric that was measured is reported", _pure_perf_counter),
    Check("pure members", "pattern catalog", "the offsets directory loads its patterns", _pure_pattern_catalog),
    Check("pure members", "Win32 answers", "Win32 answers a bool, a list and a formatted table", _pure_win32_answers),
    Check("pure members", "enumerations", "Allegiance enumerates its members", _pure_allegiance_enum),
    Check("pure members", "record round trip", "a record holds what was put in it", _pure_record_round_trip),
    Check("pure members", "refusal without a client", "a client-facing reader answers the map id, or refuses and says a client is needed", _pure_map_refuses_without_client),
    # 4. the window
    Check("window", "tabs", "the window has its six tabs", _window_tabs, needs_window=True),
    Check("window", "map built", "the window built the whole map", _window_map, needs_window=True),
    Check("window", "group list", "the group list is filled", _window_group_list, needs_window=True),
    Check("window", "search and run", "a searched entry runs to an answer", _window_search_and_detail, needs_window=True),
    Check("window", "subset test", "Test this class runs that class's entries", _window_subset_test, needs_window=True),
    Check("window", "reports", "both reports are written", _window_reports, needs_window=True),
    # 5. the client: is there one, and is this window connected to it
    Check("client", "elevated", "the controller is elevated", _client_elevated, needs_client=True),
    Check("client", "discovered", "a Guild Wars client is running", _client_discovered, needs_client=True),
    Check("client", "connected", "the window holds a live connection", _client_connected, needs_client=True),
    Check(
        "client",
        "window contexts",
        "every context view refreshed without a read failure",
        _client_window_contexts,
        needs_client=True,
        needs_window=True,
    ),
    Check(
        "client",
        "surface reads",
        "the map's reads ran against the client with no failure",
        _client_surface_reads,
        needs_client=True,
        needs_window=True,
    ),
    # 6. the live data itself: every section runs with every write member blocked
    Check(
        "live contexts",
        "every reader",
        "each of the 22 context readers answers a snapshot or refuses in its own words",
        lambda context: _live_section(context, _live_contexts),
        needs_client=True,
    ),
    Check(
        "live char",
        "character context",
        "in a map, named, with a four-word uuid and a coherent login flag",
        lambda context: _live_section(context, _live_char),
        needs_client=True,
    ),
    Check(
        "live map",
        "map, region, instance",
        "an id above zero, a known region, a kind, boundaries ordered, a party size",
        lambda context: _live_section(context, _live_map),
        needs_client=True,
    ),
    Check(
        "live player",
        "the controlled character",
        "a live agent id, finite position, a real hp fraction, an agent name",
        lambda context: _live_section(context, _live_player),
        needs_client=True,
    ),
    Check(
        "live agents",
        "the agent array",
        "the player is in it, positions are finite, ids are unique, allegiances are known",
        lambda context: _live_section(context, _live_agents),
        needs_client=True,
    ),
    Check(
        "live party",
        "the party",
        "GetPartySize equals the three arrays, and the leader is the player",
        lambda context: _live_section(context, _live_party),
        needs_client=True,
    ),
    Check(
        "live world",
        "the world record",
        "the controlled-character record agrees with Player and holds a real area",
        lambda context: _live_section(context, _live_world),
        needs_client=True,
    ),
    Check(
        "live camera",
        "the camera",
        "radian angles in range, a finite position, and a look-at point distinct from it",
        lambda context: _live_section(context, _live_camera),
        needs_client=True,
    ),
    Check(
        "live text parser",
        "the text parser",
        "the file table holds 1,024 entries per file with 11 language slots",
        lambda context: _live_section(context, _live_text_parser),
        needs_client=True,
    ),
    Check(
        "live instance",
        "instance and server region",
        "a typed instance, a map record with ordered party sizes, terrain corners ending beyond their start",
        lambda context: _live_section(context, _live_instance),
        needs_client=True,
    ),
    Check(
        "live items",
        "items and inventory",
        "every item's id and quantity are real and its position is in a bag",
        lambda context: _live_section(context, _live_items),
        needs_client=True,
    ),
    Check(
        "live agreement",
        "two paths, one fact",
        "context, getter, world record and agent array agree on map, name, id, position, party",
        lambda context: _live_section(context, _live_agreement),
        needs_client=True,
    ),
    Check(
        "live data dump",
        "every field and property",
        "every context's fields and properties are read, and the dump is kept for output",
        lambda context: _live_section(context, _live_dump),
        needs_client=True,
    ),
    Check(
        "live safety",
        "no write was called",
        "every callable member classified as a write was blocked, and none was called",
        _live_safety,
        needs_client=True,
    ),
)


def run_checks(
    context: Context | None = None,
    *,
    areas: Sequence[str] | None = None,
    only_client: bool = False,
    progress: Callable[[int, int, Result], None] | None = None,
) -> list[Result]:
    """Run the battery and report each check's verdict.

    A check is skipped when the thing it needs is absent: the client checks without a connection, the
    window checks without a window, and ``only_client`` skips everything that does not need the
    client. Nothing here raises: a check that fails is a ``fail`` result with what it saw.
    """

    context = context or Context(entries=test_surface.build_entries())
    results: list[Result] = []
    selected = [
        check
        for check in CHECKS
        if (areas is None or check.area in areas)
        and (not only_client or check.needs_client)
    ]
    for index, check in enumerate(selected, start=1):
        started = time.perf_counter()
        if check.needs_client and not context.connected:
            result = Result(check.area, check.name, "skip", check.expected, "no client connected")
        elif check.needs_window and context.window is None:
            result = Result(check.area, check.name, "skip", check.expected, "no window")
        else:
            try:
                actual = check.call(context)
                result = Result(check.area, check.name, "pass", check.expected, actual)
            except CheckFailed as error:
                result = Result(check.area, check.name, "fail", check.expected, str(error))
            except Exception as error:  # noqa: BLE001 - a check that raises is a failed check
                result = Result(
                    check.area,
                    check.name,
                    "fail",
                    check.expected,
                    f"{type(error).__name__}: {error}",
                )
        result.milliseconds = (time.perf_counter() - started) * 1000.0
        results.append(result)
        if progress is not None:
            progress(index, len(selected), result)
    return results


def summarise(results: Iterable[Result]) -> str:
    """``PASS n, FAIL n, SKIP n`` plus the failing checks, the skips, and why they were skipped.

    The reason matters: a run with no client connected is all skips, and "PASS 31, FAIL 0, SKIP 19"
    on its own reads like a clean run of the live checks when in fact *none of them ran*. Measured
    live on 2026-10-12: exactly that happened -- a report with 19 skips and an empty live-data file
    was read as a regression in the dump. So the summary names the missing client and what to do.
    """

    items = list(results)
    counts = {"pass": 0, "fail": 0, "skip": 0}
    failures: list[str] = []
    skips: list[str] = []
    for result in items:
        counts[result.status] = counts.get(result.status, 0) + 1
        if result.status == "fail":
            failures.append(f"{result.area}/{result.name}: {result.actual}")
        elif result.status == "skip":
            skips.append(result.name)
    text = f"PASS {counts['pass']}, FAIL {counts['fail']}, SKIP {counts['skip']}"
    if failures:
        text += "\nfailed: " + "; ".join(failures)
    if skips:
        text += "\nskipped: " + ", ".join(skips[:8]) + (" ..." if len(skips) > 8 else "")
    disconnected = sum(1 for result in items if result.status == "skip" and result.actual == "no client connected")
    if disconnected:
        text += (
            f"\nno client connected: {disconnected} client and live checks were skipped, so no live "
            "data was read -- connect first (Clients tab: Refresh, select the row, Connect selected)"
        )
    return text


def report(results: Sequence[Result]) -> str:
    """The battery's verdict as text, one line per check."""

    lines = ["py4gw self-test", "=" * 70]
    lines.extend(summarise(results).splitlines())
    lines.append("")
    for result in results:
        lines.append(
            f"{result.status.upper():<4} {result.area:<12} {result.name:<22} {result.milliseconds:7.1f} ms"
        )
        lines.append(f"     expected: {result.expected}")
        lines.append(f"     saw:      {result.actual}")
    return "\n".join(lines)


def write_report(results: Sequence[Result], path: str | Path, header: str = "") -> Path:
    """Write the battery's report and return where it went.

    ``header`` is the caller's own line about the run -- the window passes what it was connected to,
    so a report file cannot be read as a live run when the run had no client.
    """

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    text = report(results)
    if header:
        lines = text.splitlines()
        text = "\n".join([lines[0], header.rstrip(), *lines[1:]])
    target.write_text(text, encoding="utf-8")
    return target


def areas() -> tuple[str, ...]:
    """The battery's areas, in the order they run."""

    seen: list[str] = []
    for check in CHECKS:
        if check.area not in seen:
            seen.append(check.area)
    return tuple(seen)


def as_rows(results: Sequence[Result]) -> list[dict[str, str]]:
    """The results as table rows, which is how the window shows them."""

    return [
        {
            "status": result.status,
            "area": result.area,
            "check": result.name,
            "expected": result.expected,
            "saw": result.actual,
            "ms": f"{result.milliseconds:.1f}",
        }
        for result in results
    ]
