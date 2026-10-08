"""Main Py4GW Stealth window, built with the AutoIt-compatible GUI layer.

Run from the project directory with::

    python main.py

The window has these tabs:

* ``Guild Wars clients`` lists every running client (PID, name, character, status, path),
  refreshes that list, and connects to the client selected in it. A selected connection
  installs the game-thread layer.
* ``Library surface`` maps the whole library: every module, every entry, with its
  classification and the reason for it, one row per name, searchable, runnable one entry or one
  class at a time.
* ``Client data`` browses the connected client's contexts: the context list on the left
  chooses one, and its rows appear beside it with a filter box and a refresh button. Only the
  chosen context's controls are shown — ``GUICtrlSetState`` shows and hides a control, which
  is how one window carries twenty-two tables.
* ``Tests`` runs the map's entries and shows one row per run with its timing and result.
* ``Self-test`` runs a battery of checks, one row per check, each stating what it expected and
  what it saw. With a client connected it also reads the live data and judges whether it is
  *correct* -- every field of every context, twice-read facts agreeing, every write member
  blocked while it reads.
* ``Live data`` shows every value the last run read: one row per field and per property, filterable,
  and writable to a text file and a JSON file.

Everything is drawn with :mod:`py4gw.gui`, the AutoIt v3-compatible layer, so the statements
below are AutoIt's own (``GUICreate``, ``GUICtrlCreateListView``, ``GUICtrlSetOnEvent``,
``Sleep``). The window runs in AutoIt's OnEvent mode: the GUI calls a function per control
instead of the script polling ``GUIGetMsg()``.

Every button is a one-line caller of a method that returns what it saw, so the same surface can be
driven by a caller as well as by a person: :meth:`MainWindow.connect`,
:meth:`MainWindow.run_self_test`, :meth:`MainWindow.read_live_data` and
:meth:`MainWindow.dump_live_data`. The command line at the bottom of this file is that surface
without the window::

    python main.py --self-test                     # the checks that need no client
    python main.py --self-test --client            # and the live ones, from an elevated shell
    python main.py --data                          # every live value, to runtime/live_data_report.txt
    python main.py --self-test --client --elevate  # relaunch elevated: one UAC prompt

The window reads the client; a connection opened from here installs the game-thread layer, as
it did before.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence, TypedDict

import test_surface

from py4gw import (
    AvailableCharacterArrayStruct,
    PartyContextStruct,
    GuildContextStruct,
    AccAgentContextStruct,
    CharContextStruct,
    ConnectedClient,
    CinematicStruct,
    CameraStruct,
    FriendListStruct,
    ChatBufferStruct,
    WorldContextStruct,
    MapContextStruct,
    TradeContextStruct,
    ItemContextStruct,
    AccountContextStruct,
    GadgetContextStruct,
    InstanceInfoStruct,
    GameContextStruct,
    GameplayContextStruct,
    PreGameContextStruct,
    ServerRegionStruct,
    TextParserStruct,
    GWArray,
    PerfCounter,
    Win32,
)
from py4gw.gui import (
    GUI_CHECKED,
    GUI_EVENT_CLOSE,
    GUI_HIDE,
    GUI_SHOW,
    SW_SHOW,
    GUICreate,
    GUICtrlCreateButton,
    GUICtrlCreateCheckbox,
    GUICtrlCreateInput,
    GUICtrlCreateLabel,
    GUICtrlCreateList,
    GUICtrlCreateListView,
    GUICtrlCreateListViewItem,
    GUICtrlCreateTab,
    GUICtrlCreateTabItem,
    GUICtrlDelete,
    GUICtrlRead,
    GUICtrlSetData,
    GUICtrlSetOnEvent,
    GUICtrlSetState,
    GUIDelete,
    GUISetFont,
    GUISetOnEvent,
    GUISetState,
    Opt,
    Sleep,
)

#: Columns of the context tables: the layout offset, the field name and its value.
FIELD_COLUMNS: tuple[str, ...] = ("offset", "field", "value")

#: Columns of the bag-record table the ItemContext reader also produces.
ITEM_RECORD_COLUMNS: tuple[str, ...] = (
    "bag",
    "slot",
    "item_id",
    "quantity",
    "model_id",
    "type",
    "modifier_count",
    "address",
)

#: Columns of the character-selection table.
CHARACTER_COLUMNS: tuple[str, ...] = (
    "index",
    "name",
    "level",
    "map_id",
    "campaign",
    "primary",
    "secondary",
    "is_pvp",
    "uuid",
)

#: Columns of the client list.
CLIENT_COLUMNS: tuple[str, ...] = ("pid", "name", "character", "status", "path")

#: Columns of the library-surface table, the one entry's detail, and the run's output.
SURFACE_COLUMNS: tuple[str, ...] = ("kind", "access", "name", "owner", "detail", "doc")
DETAIL_COLUMNS: tuple[str, ...] = ("field", "value")
OUTPUT_COLUMNS: tuple[str, ...] = ("status", "milliseconds", "entry", "result")
SELF_TEST_COLUMNS: tuple[str, ...] = ("status", "area", "check", "expected", "saw", "ms")

#: Columns of the live-data table: every field and property of every context, one row per value.
LIVE_DATA_COLUMNS: tuple[str, ...] = ("context", "kind", "name", "value")

#: How many rows a table may hold before the window starts saying "showing the first N". A module
#: of this library can carry 5,000 entries, so the entry table's cap sits above the largest group and
#: below the whole map; the output pane's is lower on purpose, because drawing 20,000 rows costs
#: seconds *per redraw* and a run's results are read through the status filter or the report file.
#: Nothing is ever missing from the surface or the report -- only from what one table draws at once.
_SURFACE_ROWS = 6_000
_OUTPUT_ROWS = 5_000

#: Where Save reports writes the whole surface and the last run, and the short one to read first.
REPORT_PATH = Path("runtime") / "test_surface_report.txt"
SUMMARY_REPORT_PATH = Path("runtime") / "test_surface_summary.txt"
SELF_TEST_REPORT_PATH = Path("runtime") / "self_test_report.txt"
#: Where the live data goes: every field and property of every context, as text and, beside it, the
#: same values as JSON.
LIVE_DATA_REPORT_PATH = Path("runtime") / "live_data_report.txt"
#: Where the self-test's report check writes, and then removes, two files: the check proves the
#: writing works without leaving anything in the tree.
SELF_TEST_WORKING_FULL = Path("runtime") / ".self_test_full.txt"
SELF_TEST_WORKING_SUMMARY = Path("runtime") / ".self_test_summary.txt"

#: Why this window does not connect from an unelevated shell, in the library's own terms:
#: ``ConnectedClient.__init__`` asserts elevation before it resolves or writes anything, and
#: Windows denies an unelevated controller ``PROCESS_VM_WRITE``, ``PROCESS_VM_OPERATION``,
#: ``PROCESS_CREATE_THREAD`` and ``PROCESS_SUSPEND_RESUME`` with error 5. The window asks that
#: precondition itself, so an unelevated run does not attempt a connection at all.
ELEVATION_REFUSAL = (
    "this window needs an elevated shell: connecting asserts elevation, and Windows denies an "
    "unelevated controller the rights the capability layer needs (error 5). Relaunch the shell as "
    "administrator and connect again."
)


class ClientRow(TypedDict):
    """One Guild Wars client displayed by the client list."""

    pid: int
    name: str
    character: str
    status: str
    path: str


def _access_reason(entry: test_surface.Entry) -> str:
    """Why the engine classified an entry as it did."""

    return entry.access_reason or "no reason recorded"


def _parse_arguments(text: str) -> tuple[Any, ...]:
    """Turn the argument box into arguments: numbers, true/false, quoted or bare text.

    A member of this library takes ints, floats, strings and booleans, and the box is written the
    way a person reads a signature: ``0``, ``1.5``, ``Norgu``, ``true``, ``1, 2``. Nothing is
    guessed beyond that -- a token that looks like neither a number nor a boolean is passed as the
    text the caller typed, which is what a name argument wants.
    """

    stripped = text.strip()
    if not stripped:
        return ()
    arguments: list[Any] = []
    for token in stripped.split(","):
        item = token.strip()
        if not item:
            continue
        lowered = item.lower()
        if lowered in ("true", "false"):
            arguments.append(lowered == "true")
            continue
        if lowered in ("none", "null", ""):
            arguments.append(None)
            continue
        if (item.startswith('"') and item.endswith('"')) or (
            item.startswith("'") and item.endswith("'")
        ):
            arguments.append(item[1:-1])
            continue
        try:
            arguments.append(int(item, 0))
            continue
        except ValueError:
            pass
        try:
            arguments.append(float(item))
            continue
        except ValueError:
            pass
        arguments.append(item)
    return tuple(arguments)


class ContextFieldRow(TypedDict):
    """One field displayed in the live context inspector."""

    offset: str
    field: str
    value: str


class _FilteredRows:
    """A ListView showing rows of a fixed set of columns, with a text filter.

    This is the window's own view object over one ``GUICtrlCreateListView``. The previous
    window kept a table per tab carrying ``rows`` and ``filter`` state; this keeps the same
    state over an AutoIt ListView: ``set_rows()`` replaces the contents, ``set_filter()``
    narrows them, and both take effect on ``refresh()``.

    A view created without a control (``listview`` 0) is the one the window holds before it
    builds its interface: it keeps whatever rows it is given and draws nothing.
    """

    def __init__(self, columns: tuple[str, ...], listview: int = 0) -> None:
        """Bind the view to a created ListView control."""

        self.columns = columns
        self.listview = listview
        self.rows: list[Mapping[str, Any]] = []
        self.filter = ""
        self._items: dict[int, Mapping[str, Any]] = {}

    def set_rows(self, rows: Sequence[Mapping[str, Any]]) -> None:
        """Replace the rows the view holds."""

        self.rows = list(rows)

    def set_filter(self, value: str) -> None:
        """Set the text every shown row must contain in one of its columns."""

        self.filter = value or ""

    def refresh(self) -> None:
        """Redraw the ListView with the rows that match the filter."""

        self._clear_items()
        if not self.listview:
            return
        needle = self.filter.strip().lower()
        for row in self.rows:
            values = [self._format(row, column) for column in self.columns]
            if needle and not any(needle in value.lower() for value in values):
                continue
            item = GUICtrlCreateListViewItem("|".join(values), self.listview)
            self._items[item] = row

    def selected_row(self) -> Mapping[str, Any] | None:
        """Return the row of the ListView's selected item, or None."""

        if not self.listview:
            return None
        item = GUICtrlRead(self.listview)
        if not item:
            return None
        return self._items.get(int(item))

    def _format(self, row: Mapping[str, Any], column: str) -> str:
        """Format one cell of a row."""

        value = row.get(column, "")
        return "" if value is None else str(value)

    def _clear_items(self) -> None:
        """Delete every item currently in the ListView."""

        for item in list(self._items):
            GUICtrlDelete(item)
        self._items.clear()


class _Status:
    """A label a caller writes a status line into (``set_text``)."""

    def __init__(self, label: int) -> None:
        """Bind the status to a created Label control."""

        self.label = label

    def set_text(self, text: str) -> None:
        """Show a new status line."""

        if not self.label:
            return
        GUICtrlSetData(self.label, text)


class _ContextView:
    """One context of the data tab: its list view, filter box, refresh button and status."""

    def __init__(
        self,
        label: str,
        listview: int,
        filter_input: int,
        filter_label: int,
        refresh_button: int,
        refresh: Callable[[], None],
        status: _Status,
        table: _FilteredRows,
    ) -> None:
        """Record the controls and the reader that make up one context's view."""

        self.label = label
        self.listview = listview
        self.filter_input = filter_input
        self.filter_label = filter_label
        self.refresh_button = refresh_button
        self.refresh = refresh
        self.status = status
        self.table = table
        self.visible = False

    def show(self, visible: bool) -> None:
        """Show or hide this context's controls ($GUI_SHOW / $GUI_HIDE).

        Every control of the view is in this set -- including the label beside the filter box, which
        would otherwise stack one visible copy per context on the same spot.
        """

        self.visible = visible
        state = GUI_SHOW if visible else GUI_HIDE
        for control in (
            self.listview,
            self.filter_input,
            self.filter_label,
            self.refresh_button,
        ):
            GUICtrlSetState(control, state)


class MainWindow:
    """Build and run the Guild Wars client window."""

    def __init__(self) -> None:
        """Create the window state and the connection state."""

        self._win32 = Win32()
        self._perf = PerfCounter()
        self._last_game_context_read_ms: float | None = None
        self._last_pre_game_context_read_ms: float | None = None
        self._last_cinematic_read_ms: float | None = None
        self._last_camera_read_ms: float | None = None
        self._last_friend_list_read_ms: float | None = None
        self._last_chat_buffer_read_ms: float | None = None
        self._last_world_context_read_ms: float | None = None
        self._last_map_context_read_ms: float | None = None
        self._last_trade_context_read_ms: float | None = None
        self._last_item_context_read_ms: float | None = None
        self._last_account_context_read_ms: float | None = None
        self._last_gadget_context_read_ms: float | None = None
        self._last_gameplay_context_read_ms: float | None = None
        self._last_server_region_read_ms: float | None = None
        self._last_instance_info_read_ms: float | None = None
        self._last_text_parser_read_ms: float | None = None
        self._last_available_characters_read_ms: float | None = None
        self._last_party_context_read_ms: float | None = None
        self._last_guild_context_read_ms: float | None = None
        self._last_acc_agent_context_read_ms: float | None = None
        self._last_context_read_ms: float | None = None
        self._connection: ConnectedClient | None = None
        self._clients: list[dict[str, Any]] = []
        self._closed = False
        self._window = 0
        self._tabs = 0
        self._client_tab = 0
        self._data_tab = 0
        self._surface_tab = 0
        self._test_tab = 0
        self._contexts_select = 0
        self._context_views: list[_ContextView] = []
        # The library surface: the map itself, the group list, the entry table, the detail pane, and
        # what a run produced.
        self._surface_entries: tuple[test_surface.Entry, ...] = ()
        self._surface_summary = test_surface.Summary()
        self._surface_group_names: list[str] = []
        self._surface_groups_counts: dict[str, int] = {}
        self._surface_search = 0
        self._surface_groups = 0
        self._surface_arguments = 0
        self._surface_status = _Status(0)
        self._surface_result = _Status(0)
        self._surface_selected: test_surface.Entry | None = None
        self._writes_check = 0
        self._test_status = _Status(0)
        self._status_list = 0
        self._output_filter = ""
        self._output_filter_input = 0
        self._outcomes: list[test_surface.Outcome] = []
        self._output_rows: list[dict[str, Any]] = []
        self._self_test_tab = 0
        self._live_tab = 0
        self._self_test_status = _Status(0)
        self._self_test_results: list[Any] = []
        # What the last battery run read: the snapshot cache, the dump, and the reader timings. The
        # live-data tab and ``dump_live_data`` both read from here, so one run fills the screen and
        # the report with the same values.
        self._self_test_context: Any = None
        self._live_data_status = _Status(0)
        self._live_data_filter_input = 0
        # The views the readers write through. The build replaces each of these with the view
        # that owns its real ListView control; until then they hold rows and draw nothing.
        self._client_table = _FilteredRows(CLIENT_COLUMNS)
        self._surface_table = _FilteredRows(SURFACE_COLUMNS)
        self._surface_detail = _FilteredRows(DETAIL_COLUMNS)
        self._output_table = _FilteredRows(OUTPUT_COLUMNS)
        self._self_test_table = _FilteredRows(SELF_TEST_COLUMNS)
        self._live_data_table = _FilteredRows(LIVE_DATA_COLUMNS)
        self._client_status = _Status(0)
        self._connected_label = _Status(0)
        self._data_status = _Status(0)
        # Every context status is the one data status label: a hidden context's reader would
        # otherwise write its status into a label nobody can see.
        self._context_status = self._data_status
        self._game_context_status = self._data_status
        self._pre_game_context_status = self._data_status
        self._cinematic_status = self._data_status
        self._camera_status = self._data_status
        self._friend_list_status = self._data_status
        self._chat_buffer_status = self._data_status
        self._world_context_status = self._data_status
        self._map_context_status = self._data_status
        self._trade_context_status = self._data_status
        self._item_context_status = self._data_status
        self._account_context_status = self._data_status
        self._gadget_context_status = self._data_status
        self._gameplay_context_status = self._data_status
        self._server_region_status = self._data_status
        self._instance_info_status = self._data_status
        self._text_parser_status = self._data_status
        self._available_characters_status = self._data_status
        self._party_context_status = self._data_status
        self._guild_context_status = self._data_status
        self._acc_agent_context_status = self._data_status
        # The tables each reader writes through, replaced by the build below.
        self._context_table = _FilteredRows(FIELD_COLUMNS)
        self._game_context_table = _FilteredRows(FIELD_COLUMNS)
        self._pre_game_context_table = _FilteredRows(FIELD_COLUMNS)
        self._cinematic_table = _FilteredRows(FIELD_COLUMNS)
        self._camera_table = _FilteredRows(FIELD_COLUMNS)
        self._friend_list_table = _FilteredRows(FIELD_COLUMNS)
        self._chat_buffer_table = _FilteredRows(FIELD_COLUMNS)
        self._world_context_table = _FilteredRows(FIELD_COLUMNS)
        self._map_context_table = _FilteredRows(FIELD_COLUMNS)
        self._trade_context_table = _FilteredRows(FIELD_COLUMNS)
        self._item_context_table = _FilteredRows(FIELD_COLUMNS)
        self._item_records_table = _FilteredRows(ITEM_RECORD_COLUMNS)
        self._account_context_table = _FilteredRows(FIELD_COLUMNS)
        self._gadget_context_table = _FilteredRows(FIELD_COLUMNS)
        self._gameplay_context_table = _FilteredRows(FIELD_COLUMNS)
        self._server_region_table = _FilteredRows(FIELD_COLUMNS)
        self._instance_info_table = _FilteredRows(FIELD_COLUMNS)
        self._text_parser_table = _FilteredRows(FIELD_COLUMNS)
        self._available_characters_table = _FilteredRows(CHARACTER_COLUMNS)
        self._party_context_table = _FilteredRows(FIELD_COLUMNS)
        self._guild_context_table = _FilteredRows(FIELD_COLUMNS)
        self._acc_agent_context_table = _FilteredRows(FIELD_COLUMNS)

    def run(self) -> None:
        """Build the window, show it, and serve its events until it is closed."""

        # AutoIt's OnEvent mode: the GUI calls the registered function for a control instead
        # of the script polling GUIGetMsg(). Sleep() delivers those events while it waits, so
        # the idle loop below is the one the reference's OnEvent page describes.
        Opt("GUIOnEventMode", 1)
        self._build_interface()
        GUISetState(SW_SHOW, self._window)
        while not self._closed:
            Sleep(50)
        self._disconnect_current()

    # --- window construction ----------------------------------------------------------

    def _build_interface(self) -> None:
        """Create the window and its tabs: clients, the library surface, the data, the tests."""

        self._window = GUICreate("Py4GW Stealth", 1400, 900, -1, -1)
        GUISetOnEvent(GUI_EVENT_CLOSE, self._on_close, self._window)
        GUISetFont(9, 400, 0, "Segoe UI", self._window)
        self._tabs = GUICtrlCreateTab(8, 8, 1384, 862)
        self._client_tab = GUICtrlCreateTabItem("Guild Wars clients")
        self._build_client_tab()
        self._surface_tab = GUICtrlCreateTabItem("Library surface")
        self._build_surface_tab()
        self._data_tab = GUICtrlCreateTabItem("Client data")
        self._build_data_tab()
        self._test_tab = GUICtrlCreateTabItem("Tests")
        self._build_test_tab()
        self._self_test_tab = GUICtrlCreateTabItem("Self-test")
        self._build_self_test_tab()
        self._live_tab = GUICtrlCreateTabItem("Live data")
        self._build_live_tab()
        GUICtrlCreateTabItem("")

    def _build_client_tab(self) -> None:
        """Create refresh, selection and connection controls."""

        GUICtrlCreateLabel("Guild Wars clients", 16, 14, 300, 22)
        GUICtrlCreateLabel(
            "Refresh to find running clients. The status column is the client's own state -- "
            "\"online\" means it is running a logged-in character, \"in selection menus\" means it is "
            "not. Attaching this controller to one is a separate step: select the row and press "
            "Connect selected, and the line under the table then says which client this window is "
            "attached to.",
            16,
            40,
            1340,
            20,
        )
        refresh_button = GUICtrlCreateButton("Refresh", 16, 66, 100, 26)
        GUICtrlSetOnEvent(refresh_button, self._refresh_clients)
        connect_button = GUICtrlCreateButton("Connect selected", 126, 66, 140, 26)
        GUICtrlSetOnEvent(connect_button, self._connect_selected)
        disconnect_button = GUICtrlCreateButton("Disconnect", 276, 66, 110, 26)
        GUICtrlSetOnEvent(disconnect_button, self._disconnect_current)
        self._client_status = _Status(
            GUICtrlCreateLabel("No client scan performed", 400, 70, 960, 20)
        )
        self._client_table = _FilteredRows(
            CLIENT_COLUMNS,
            GUICtrlCreateListView("|".join(CLIENT_COLUMNS), 16, 104, 1340, 560),
        )
        self._connected_label = _Status(
            GUICtrlCreateLabel(
                "No client connected — this controller is not attached to a client", 16, 674, 1340, 20
            )
        )
        GUICtrlCreateLabel(
            "Attached client data is on the Client data tab; the checks that read it are on the "
            "Self-test tab.",
            16,
            700,
            1340,
            20,
        )
        self._refresh_clients()

    def _build_data_tab(self) -> None:
        """Create the context selector and one hidden set of controls per context."""

        GUICtrlCreateLabel("Connected client data", 16, 14, 300, 22)
        GUICtrlCreateLabel(
            "Choose a context on the left. These values are read-only snapshots: the "
            "maintained properties appear first, raw layout fields follow.",
            16,
            40,
            1340,
            20,
        )
        self._contexts_select = GUICtrlCreateList("", 16, 66, 240, 780)
        GUICtrlSetOnEvent(self._contexts_select, self._context_selected)
        refresh_all = GUICtrlCreateButton("Refresh all contexts", 1140, 14, 200, 26)
        GUICtrlSetOnEvent(refresh_all, self._refresh_all_contexts)
        self._data_status = _Status(GUICtrlCreateLabel("Connect a client first", 272, 852,
                                                       1108, 20))
        # Every context writes its status into this one label -- a hidden context's reader must not
        # write into a label nobody can see. The aliases made in __init__ point at the placeholder
        # that existed before the window was built, so they are re-pointed at the real label here;
        # without this every "refreshed", "not available" and "read failed" line went nowhere.
        for status_name in (
            "_context_status",
            "_game_context_status",
            "_pre_game_context_status",
            "_cinematic_status",
            "_camera_status",
            "_friend_list_status",
            "_chat_buffer_status",
            "_world_context_status",
            "_map_context_status",
            "_trade_context_status",
            "_item_context_status",
            "_account_context_status",
            "_gadget_context_status",
            "_gameplay_context_status",
            "_server_region_status",
            "_instance_info_status",
            "_text_parser_status",
            "_available_characters_status",
            "_party_context_status",
            "_guild_context_status",
            "_acc_agent_context_status",
        ):
            setattr(self, status_name, self._data_status)

        self._pre_game_context_table = self._create_context_view(
            "PreGameContext", FIELD_COLUMNS, self._refresh_pre_game_context
        )
        self._cinematic_table = self._create_context_view(
            "Cinematic", FIELD_COLUMNS, self._refresh_cinematic
        )
        self._camera_table = self._create_context_view(
            "Camera", FIELD_COLUMNS, self._refresh_camera
        )
        self._friend_list_table = self._create_context_view(
            "FriendList", FIELD_COLUMNS, self._refresh_friend_list
        )
        self._chat_buffer_table = self._create_context_view(
            "ChatBuffer", FIELD_COLUMNS, self._refresh_chat_buffer
        )
        self._world_context_table = self._create_context_view(
            "WorldContext", FIELD_COLUMNS, self._refresh_world_context
        )
        self._map_context_table = self._create_context_view(
            "MapContext", FIELD_COLUMNS, self._refresh_map_context
        )
        self._trade_context_table = self._create_context_view(
            "TradeContext", FIELD_COLUMNS, self._refresh_trade_context
        )
        self._item_context_table = self._create_context_view(
            "ItemContext", FIELD_COLUMNS, self._refresh_item_context
        )
        self._item_records_table = self._create_context_view(
            "ItemContext records", ITEM_RECORD_COLUMNS, self._refresh_item_context
        )
        self._account_context_table = self._create_context_view(
            "AccountContext", FIELD_COLUMNS, self._refresh_account_context
        )
        self._gadget_context_table = self._create_context_view(
            "GadgetContext", FIELD_COLUMNS, self._refresh_gadget_context
        )
        self._gameplay_context_table = self._create_context_view(
            "GameplayContext", FIELD_COLUMNS, self._refresh_gameplay_context
        )
        self._server_region_table = self._create_context_view(
            "ServerRegion", FIELD_COLUMNS, self._refresh_server_region
        )
        self._instance_info_table = self._create_context_view(
            "InstanceInfo", FIELD_COLUMNS, self._refresh_instance_info
        )
        self._text_parser_table = self._create_context_view(
            "TextParser", FIELD_COLUMNS, self._refresh_text_parser
        )
        self._available_characters_table = self._create_context_view(
            "AvailableCharacters", CHARACTER_COLUMNS, self._refresh_available_characters
        )
        self._party_context_table = self._create_context_view(
            "PartyContext", FIELD_COLUMNS, self._refresh_party_context
        )
        self._guild_context_table = self._create_context_view(
            "GuildContext", FIELD_COLUMNS, self._refresh_guild_context
        )
        self._acc_agent_context_table = self._create_context_view(
            "AccAgentContext", FIELD_COLUMNS, self._refresh_acc_agent_context
        )
        self._game_context_table = self._create_context_view(
            "GameContext", FIELD_COLUMNS, self._refresh_game_context
        )
        self._context_table = self._create_context_view(
            "CharContext", FIELD_COLUMNS, self._refresh_context
        )
        self._show_context_view(0)

    def _create_context_view(
        self,
        label: str,
        columns: tuple[str, ...],
        refresh: Callable[[], None],
    ) -> _FilteredRows:
        """Create one context's controls, hidden, and return its table.

        Every context's controls are created in the same place: the chosen one is shown with
        ``GUICtrlSetState($GUI_SHOW)`` and the others are hidden, which is how one window
        carries a table per context without a tab per context.
        """

        listview = GUICtrlCreateListView(
            "|".join(columns), 272, 104, 1108, 740
        )
        refresh_button = GUICtrlCreateButton("Refresh " + label, 272, 66, 150, 26)
        filter_input = GUICtrlCreateInput("", 432, 68, 400, 22)
        filter_label = GUICtrlCreateLabel("Filter fields or values", 842, 70, 300, 20)
        table = _FilteredRows(columns, listview)
        view = _ContextView(
            label,
            listview,
            filter_input,
            filter_label,
            refresh_button,
            refresh,
            self._data_status,
            table,
        )
        self._context_views.append(view)
        # The refresh button runs the reader *through* the guard, so a read the display makes can
        # never reach Tk as an unhandled exception.
        GUICtrlSetOnEvent(refresh_button, lambda v=view: self._run_context_reader(v))
        GUICtrlSetOnEvent(filter_input, self._context_filter_changed)
        # A List's items are added by GUICtrlSetData(); a leading separator would destroy the
        # list first (GUICtrlSetData.htm), so each label is appended as it is.
        GUICtrlSetData(self._contexts_select, label)
        view.show(False)
        return table

    def _on_close(self) -> None:
        """Close the window and let the run loop finish."""

        self._closed = True
        GUIDelete(self._window)

    # --- the library surface: every module, class, member, field and constant -------------

    def _build_surface_tab(self) -> None:
        """Create the map's three panes: the groups, their entries, and one entry's detail."""

        GUICtrlCreateLabel(
            "The library, mapped: every module of py4gw, and every name, record field, enum "
            "member, class member and constant it declares.",
            16,
            14,
            900,
            20,
        )
        GUICtrlCreateLabel("Search", 16, 44, 54, 20)
        self._surface_search = GUICtrlCreateInput("", 70, 42, 420, 22)
        GUICtrlSetOnEvent(self._surface_search, self._surface_searched)
        search_button = GUICtrlCreateButton("Search", 500, 40, 90, 26)
        GUICtrlSetOnEvent(search_button, self._surface_searched)
        reset_button = GUICtrlCreateButton("Show group", 596, 40, 110, 26)
        GUICtrlSetOnEvent(reset_button, self._surface_group_selected)
        group_test_button = GUICtrlCreateButton("Test this group", 712, 40, 130, 26)
        GUICtrlSetOnEvent(group_test_button, self._test_selected_group)
        owner_test_button = GUICtrlCreateButton("Test this class", 848, 40, 130, 26)
        GUICtrlSetOnEvent(owner_test_button, self._test_selected_owner)
        rebuild_button = GUICtrlCreateButton("Rebuild map", 984, 40, 110, 26)
        GUICtrlSetOnEvent(rebuild_button, self._rebuild_surface_map)
        self._surface_status = _Status(
            GUICtrlCreateLabel("Building the map...", 1104, 44, 252, 20)
        )

        self._surface_groups = GUICtrlCreateList("", 16, 76, 272, 736)
        GUICtrlSetOnEvent(self._surface_groups, self._surface_group_selected)
        self._surface_table = _FilteredRows(
            SURFACE_COLUMNS,
            GUICtrlCreateListView("|".join(SURFACE_COLUMNS), 298, 76, 1084, 428),
        )
        GUICtrlSetOnEvent(self._surface_table.listview, self._surface_entry_selected)

        self._surface_detail = _FilteredRows(
            DETAIL_COLUMNS,
            GUICtrlCreateListView("|".join(DETAIL_COLUMNS), 298, 512, 1084, 168),
        )
        GUICtrlCreateLabel("Arguments", 298, 692, 80, 20)
        self._surface_arguments = GUICtrlCreateInput("", 380, 690, 420, 22)
        run_button = GUICtrlCreateButton("Run this entry", 810, 688, 140, 26)
        GUICtrlSetOnEvent(run_button, self._run_selected_entry)
        self._surface_result = _Status(
            GUICtrlCreateLabel(
                "Select an entry, then Run it. Arguments are comma separated: "
                "numbers, text, true/false.",
                958,
                692,
                424,
                40,
            )
        )
        GUICtrlCreateLabel(
            "Reads run freely; a member classified as a write runs only if the Tests tab's "
            "include-writes box is ticked.",
            298,
            722,
            1084,
            20,
        )
        self._build_surface_map()

    def _build_surface_map(self) -> None:
        """Build the map once and fill the group list with it."""

        started = time.perf_counter()
        self._surface_entries = test_surface.build_entries()
        self._surface_summary = test_surface.summarise(self._surface_entries)
        groups: dict[str, int] = {}
        for entry in self._surface_entries:
            groups[entry.group] = groups.get(entry.group, 0) + 1
        self._surface_groups_counts = groups
        # The declared exports first: a caller looks there first, and the rest follow by name.
        self._surface_group_names = sorted(groups, key=lambda name: (name != "py4gw", name))
        # An empty string empties a List first, which is what a rebuild needs.
        GUICtrlSetData(self._surface_groups, "")
        for group in self._surface_group_names:
            GUICtrlSetData(self._surface_groups, f"{group}  ({groups[group]})")
        self._surface_status.set_text(
            f"{self._surface_summary.total} entries in {len(groups)} modules, "
            f"mapped in {time.perf_counter() - started:.2f} s — pick a module or search"
        )
        self._surface_table.set_rows([])
        self._surface_table.refresh()
        self._surface_detail.set_rows([])
        self._surface_detail.refresh()

    def _rebuild_surface_map(self) -> None:
        """Build the map again, for a library that changed while the window was open."""

        self._build_surface_map()

    def _selected_group(self) -> str:
        """The module chosen in the group list, from its row text."""

        text = GUICtrlRead(self._surface_groups)
        for group in self._surface_group_names:
            if text == group or text.startswith(group + " "):
                return group
        return ""

    def _surface_group_selected(self) -> None:
        """Show the chosen module's entries."""

        group = self._selected_group()
        if not group:
            self._surface_status.set_text("Pick a module on the left, or search for a name.")
            return
        rows = [entry for entry in self._surface_entries if entry.group == group]
        self._show_surface_rows(rows, f"{group}: {len(rows)} entries")

    def _surface_searched(self) -> None:
        """Filter the whole map by name -- a caller knows the member, not the module."""

        needle = GUICtrlRead(self._surface_search).strip().lower()
        if not needle:
            self._surface_group_selected()
            return
        rows = [
            entry
            for entry in self._surface_entries
            if needle in entry.label.lower() or needle in entry.doc.lower()
        ]
        self._show_surface_rows(rows, f"search {needle!r}: {len(rows)} entries")

    def _show_surface_rows(self, rows: list[test_surface.Entry], message: str) -> None:
        """Put entries in the table, capped so a 20,000-entry map stays responsive."""

        shown = rows[: _SURFACE_ROWS]
        self._surface_table.set_rows(
            [
                {
                    "kind": entry.kind,
                    "access": entry.access,
                    "name": entry.name,
                    "owner": entry.owner or entry.name,
                    "detail": entry.detail,
                    "doc": entry.doc,
                }
                for entry in shown
            ]
        )
        self._surface_table.refresh()
        cap = ""
        if len(rows) > len(shown):
            cap = f" (showing the first {len(shown)}; search to narrow it down)"
        self._surface_status.set_text(message + cap)

    def _surface_entry_selected(self) -> None:
        """Fill the detail pane for the chosen entry, and say what the engine will do with it."""

        row = self._surface_table.selected_row()
        entry = self._entry_of_row(row)
        self._surface_selected = entry
        if entry is None:
            return
        rows = [
            {"field": "path", "value": entry.label},
            {"field": "kind", "value": entry.kind},
            {"field": "access", "value": f"{entry.access} — {_access_reason(entry)}"},
            {"field": "needs the client", "value": "yes" if entry.needs_client else "no"},
            {"field": "engine will", "value": entry.run},
            {"field": "parameters", "value": ", ".join(entry.parameters) or "(none)"},
            {"field": "signature", "value": f"{entry.name}{entry.signature}"},
            {"field": "detail", "value": entry.detail or "(none)"},
            {"field": "docstring", "value": entry.doc or "(none)"},
        ]
        self._surface_detail.set_rows(rows)
        self._surface_detail.refresh()
        GUICtrlSetData(self._surface_arguments, ", ".join(entry.parameters))
        self._surface_result.set_text(
            f"{entry.label} — {_access_reason(entry)}; the engine will {entry.run}."
        )

    def _entry_of_row(self, row: Any) -> test_surface.Entry | None:
        """The entry a table row stands for."""

        if not isinstance(row, dict):
            return None
        owner = str(row.get("owner", ""))
        name = str(row.get("name", ""))
        for entry in self._surface_entries:
            if entry.name == name and (entry.owner or entry.name) == owner:
                return entry
        return None

    def _run_selected_entry(self) -> None:
        """Run the chosen entry with the arguments in the box, and show what it answered."""

        entry = self._surface_selected
        if entry is None:
            self._surface_result.set_text("Select an entry in the table first.")
            return
        arguments = _parse_arguments(GUICtrlRead(self._surface_arguments))
        if entry.parameters and len(arguments) != len(entry.parameters):
            self._surface_result.set_text(
                f"{entry.name} takes {len(entry.parameters)} argument(s): "
                + ", ".join(entry.parameters)
            )
            return
        outcome = test_surface.run_entry(
            entry,
            include_writes=self._include_writes(),
            include_unknown=not self._connected(),
            client_connected=self._connected(),
            args=arguments,
        )
        self._outcomes.append(outcome)
        self._output_rows.append(
            {
                "status": outcome.status,
                "milliseconds": f"{outcome.milliseconds:.1f}",
                "entry": outcome.entry.display,
                "result": outcome.value or outcome.error or outcome.output,
            }
        )
        self._refresh_output_rows()
        answer = outcome.value or outcome.error or outcome.output or "(nothing)"
        self._surface_result.set_text(
            f"{entry.name}: {outcome.status} in {outcome.milliseconds:.1f} ms — {answer}"
        )

    def _connected(self) -> bool:
        """Whether this window holds a live connection.

        Both halves are asked, because they can disagree: ``_connection`` is this window's handle,
        and ``is_connected`` is the port's own answer (``not reader.is_closed``). A connection that
        was closed by another path leaves the handle set, and a window that reported "connected" on
        the strength of the handle alone is what made a battery run skip every client check while the
        label still said *Connected to PID ...* -- measured live on 2026-10-12. The handle is not the
        connection; the port's own answer is.
        """

        return self._connection is not None and bool(self._connection.is_connected)

    # --- the tests ------------------------------------------------------------------------

    def _build_test_tab(self) -> None:
        """Create the run buttons and the one output pane they all feed."""

        GUICtrlCreateLabel(
            "One button runs the whole surface. With no client connected every read and every "
            "unclassified member is exercised, and the library's own refusals are the results.",
            16,
            14,
            1340,
            20,
        )
        all_button = GUICtrlCreateButton("Test all methods", 16, 42, 150, 28)
        GUICtrlSetOnEvent(all_button, self._test_all_methods)
        reads_button = GUICtrlCreateButton("Test reads (connected)", 174, 42, 170, 28)
        GUICtrlSetOnEvent(reads_button, self._test_reads_connected)
        self._writes_check = GUICtrlCreateCheckbox("include writes (acts on the client)", 352, 44, 260, 24)
        rerun_button = GUICtrlCreateButton("Re-run failures", 620, 42, 130, 28)
        GUICtrlSetOnEvent(rerun_button, self._rerun_failures)
        save_button = GUICtrlCreateButton("Save reports", 758, 42, 110, 28)
        GUICtrlSetOnEvent(save_button, self._save_report)
        clear_button = GUICtrlCreateButton("Clear output", 876, 42, 110, 28)
        GUICtrlSetOnEvent(clear_button, self._clear_output)
        self._test_status = _Status(
            GUICtrlCreateLabel("Nothing has been run yet.", 994, 48, 362, 20)
        )
        GUICtrlCreateLabel("Show", 16, 80, 60, 20)
        # The status list is the filter and the reading of the run at once: every status with its
        # count, so "what refused" is a click rather than a scroll through twenty thousand rows.
        self._status_list = GUICtrlCreateList("", 16, 104, 300, 716)
        GUICtrlSetOnEvent(self._status_list, self._output_filter_changed)
        self._output_filter = ""
        self._output_filter_input = GUICtrlCreateInput("", 330, 80, 1026, 22)
        GUICtrlSetOnEvent(self._output_filter_input, self._output_filter_changed)
        self._output_table = _FilteredRows(
            OUTPUT_COLUMNS,
            GUICtrlCreateListView("|".join(OUTPUT_COLUMNS), 330, 110, 1026, 710),
        )
        self._outcomes: list[test_surface.Outcome] = []
        self._output_rows: list[dict[str, Any]] = []

    def _include_writes(self) -> bool:
        """Whether the include-writes box is ticked."""

        return bool(GUICtrlRead(self._writes_check) == GUI_CHECKED)

    def _test_all_methods(self) -> None:
        """Run the whole surface. With no client this is the safe walk; with one, reads only."""

        if not self._surface_entries:
            self._build_surface_map()
        connected = self._connected()
        include_writes = self._include_writes()
        self._clear_output()
        entries = self._surface_entries
        outcomes: list[test_surface.Outcome] = []
        started = time.perf_counter()
        for index, entry in enumerate(entries, start=1):
            outcomes.append(
                test_surface.run_entry(
                    entry,
                    include_writes=include_writes,
                    include_unknown=not connected,
                    client_connected=connected,
                )
            )
            if index % 2000 == 0:
                # The status line is the progress: the output table is filled once, at the end,
                # because drawing rows during the run costs far more than the run itself.
                self._test_status.set_text(f"ran {index} of {len(entries)} entries...")
        self._outcomes = outcomes
        self._refresh_status_filter()
        self._show_outcomes(outcomes)
        self._summarise_run(entries, outcomes, seconds=time.perf_counter() - started)

    def _test_reads_connected(self) -> None:
        """Run the reads against the connected client, leaving writes alone."""

        if not self._connected():
            self._test_status.set_text("Connect a client first.")
            return
        self._clear_output()
        started = time.perf_counter()
        outcomes = test_surface.run_all(
            self._surface_entries,
            include_writes=False,
            include_unknown=False,
            client_connected=True,
        )
        self._outcomes = outcomes
        self._refresh_status_filter()
        self._show_outcomes(outcomes)
        self._summarise_run(
            self._surface_entries, outcomes, seconds=time.perf_counter() - started
        )

    def _rerun_failures(self) -> None:
        """Run again only what did not answer."""

        if not self._outcomes:
            self._test_status.set_text("Run the surface first.")
            return
        failed = {
            outcome.entry.label
            for outcome in self._outcomes
            if outcome.status not in ("answered", "not runnable")
        }
        entries = [entry for entry in self._surface_entries if entry.label in failed]
        started = time.perf_counter()
        outcomes = test_surface.run_all(
            entries,
            include_writes=self._include_writes(),
            include_unknown=not self._connected(),
            client_connected=self._connected(),
        )
        for outcome in outcomes:
            for index, previous in enumerate(self._outcomes):
                if previous.entry.label == outcome.entry.label:
                    self._outcomes[index] = outcome
        self._show_outcomes(self._outcomes)
        self._summarise_run(
            entries, outcomes, seconds=time.perf_counter() - started, prefix="re-ran "
        )

    def _test_selected_group(self) -> None:
        """Run only the chosen module's entries -- one module at a time is how a class is debugged."""

        group = self._selected_group()
        if not group:
            self._surface_status.set_text("Pick a module on the left first.")
            return
        entries = [entry for entry in self._surface_entries if entry.group == group]
        self._run_entries(entries, f"{group}")

    def _test_selected_owner(self) -> None:
        """Run only the selected entry's class -- every member of one class, in one press."""

        entry = self._surface_selected
        if entry is None or not entry.owner:
            self._surface_status.set_text("Select a class member in the table first.")
            return
        entries = [
            candidate
            for candidate in self._surface_entries
            if candidate.owner == entry.owner and candidate.group == entry.group
        ]
        self._run_entries(entries, f"{entry.owner}")

    def _run_entries(self, entries: Sequence[test_surface.Entry], label: str) -> None:
        """Run one selection of entries through the same flags the big button uses."""

        connected = self._connected()
        include_writes = self._include_writes()
        started = time.perf_counter()
        outcomes = [
            test_surface.run_entry(
                entry,
                include_writes=include_writes,
                include_unknown=not connected,
                client_connected=connected,
            )
            for entry in entries
        ]
        by_label = {outcome.entry.label: outcome for outcome in outcomes}
        for index, previous in enumerate(self._outcomes):
            if previous.entry.label in by_label:
                self._outcomes[index] = by_label.pop(previous.entry.label)
        self._outcomes.extend(by_label.values())
        self._refresh_status_filter()
        self._show_outcomes(self._outcomes)
        self._surface_status.set_text(
            f"{label}: ran {len(outcomes)} entries -- the results are on the Tests tab"
        )
        self._summarise_run(
            entries, outcomes, seconds=time.perf_counter() - started, prefix=f"{label}: "
        )

    def _summarise_run(
        self,
        entries: Sequence[test_surface.Entry],
        outcomes: Sequence[test_surface.Outcome],
        seconds: float = 0.0,
        prefix: str = "",
    ) -> None:
        """Say what a run did, in the status line and as the first row of the output."""

        counts: dict[str, int] = {}
        for outcome in outcomes:
            counts[outcome.status] = counts.get(outcome.status, 0) + 1
        parts = ", ".join(f"{status}={count}" for status, count in sorted(counts.items()))
        summary = test_surface.summarise(entries)
        self._output_rows.insert(
            0,
            {
                "status": "summary",
                "milliseconds": f"{seconds:.1f}s",
                "entry": f"{len(outcomes)} entries run",
                "result": parts + "   |   " + "   ".join(summary.lines()),
            },
        )
        self._test_status.set_text(f"{prefix}{len(outcomes)} entries in {seconds:.1f} s: {parts}")
        self._refresh_output_rows()

    def _show_outcomes(self, outcomes: Sequence[test_surface.Outcome]) -> None:
        """Fill the output pane with the results the current filter selects, drawn once."""

        selected = test_surface.outcomes_with_status(
            outcomes,
            self._output_filter,
            GUICtrlRead(self._output_filter_input),
        )
        self._output_rows = [
            {
                "status": outcome.status,
                "milliseconds": f"{outcome.milliseconds:.1f}",
                "entry": outcome.entry.display,
                "result": outcome.value or outcome.error or outcome.output,
            }
            for outcome in selected
        ]
        self._refresh_output_rows()
        if self._output_filter or GUICtrlRead(self._output_filter_input):
            self._test_status.set_text(
                f"{len(selected)} of {len(outcomes)} results shown"
            )

    def _output_filter_changed(self) -> None:
        """Apply the status list and the text box to the results already on hand."""

        self._output_filter = self._selected_status_filter()
        self._show_outcomes(self._outcomes)

    def _selected_status_filter(self) -> str:
        """The status chosen in the list: its name, or "" for every status.

        A status can contain parentheses of its own ("skipped (classified as a write)"), so the
        count is taken off the *end* of the row rather than at the first bracket.
        """

        text = GUICtrlRead(self._status_list)
        if not text or text.startswith("all "):
            return ""
        return text.rsplit(" (", 1)[0]

    def _refresh_status_filter(self) -> None:
        """Redraw the status list with the counts of the run so far."""

        counts = test_surface.statuses(self._outcomes)
        answered = counts.get("answered", 0)
        GUICtrlSetData(self._status_list, "")
        GUICtrlSetData(self._status_list, f"all ({len(self._outcomes)})")
        GUICtrlSetData(self._status_list, f"answered ({answered})")
        GUICtrlSetData(self._status_list, f"not answered ({len(self._outcomes) - answered})")
        for status, count in counts.items():
            if status == "answered":
                continue
            GUICtrlSetData(self._status_list, f"{status} ({count})")

    def _refresh_output_rows(self) -> None:
        """Draw the output rows, capped only if the map ever grows past the cap."""

        shown = self._output_rows[: _OUTPUT_ROWS]
        self._output_table.set_rows(shown)
        self._output_table.refresh()
        if len(self._output_rows) > len(shown):
            self._test_status.set_text(
                f"{self._test_status_text()}   (showing {len(shown)} of "
                f"{len(self._output_rows)} rows; Save report has them all)"
            )

    def _test_status_text(self) -> str:
        """The status line as it stands, without the cap note."""

        return GUICtrlRead(self._test_status.label)

    def _clear_output(self) -> None:
        """Empty the output pane and forget the last run."""

        self._output_rows = []
        self._outcomes = []
        self._output_table.set_rows([])
        self._output_table.refresh()
        self._refresh_status_filter()

    def _save_report(self) -> None:
        """Write the whole surface and the last run: the full report, and a short one to read first."""

        if not self._surface_entries:
            self._build_surface_map()
        full, summary = self._save_report_to(REPORT_PATH, SUMMARY_REPORT_PATH)
        self._test_status.set_text(
            f"{len(self._surface_entries)} entries and {len(self._outcomes)} results: "
            f"full report {full.name} ({full.stat().st_size // 1024} KiB), "
            f"summary {summary.name} in {summary.parent}"
        )

    def _save_report_to(self, full_path: Path, summary_path: Path) -> tuple[Path, Path]:
        """Write both reports where asked, and return where they went.

        The self-test battery calls this with its own paths, so the report writing the user presses is
        the same code the battery checks.
        """

        if not self._surface_entries:
            self._build_surface_map()
        full = test_surface.write_report(
            test_surface.report(self._surface_entries, self._outcomes), full_path
        )
        summary = test_surface.write_summary_report(
            self._surface_entries, self._outcomes, summary_path
        )
        return full, summary

    def _refresh_all_contexts(self) -> None:
        """Run every context reader once, which is what the data tab shows."""

        for view in self._context_views:
            self._run_context_reader(view)
        self._data_status.set_text(f"all {len(self._context_views)} contexts refreshed")

    def show_data_tab(self) -> None:
        """Select the data tab, which is where the context views are."""

        GUISetState(SW_SHOW, self._window)
        GUICtrlSetState(self._data_tab, GUI_SHOW)

    # --- the self-test battery --------------------------------------------------------------

    def _build_live_tab(self) -> None:
        """Create the live-data table: every value the client's contexts held at the last read.

        This is the "output all data" half of the surface. The rows come from the same battery run the
        Self-test tab performs -- reading them is not a second read of the client, it is the values
        that were kept -- so what is on screen, what the report file holds, and what a caller gets
        back from :meth:`read_live_data` are one set of readings.
        """

        GUICtrlCreateLabel("Live data", 16, 14, 300, 22)
        GUICtrlCreateLabel(
            "Every field and property of every context, as it was read. Press Read to run the client "
            "checks and fill the table; filter narrows the rows; Write report puts all of it in a file.",
            16,
            40,
            1340,
            20,
        )
        read_button = GUICtrlCreateButton("Read live data", 16, 66, 140, 28)
        GUICtrlSetOnEvent(read_button, self._read_live_data_clicked)
        write_button = GUICtrlCreateButton("Write report", 164, 66, 130, 28)
        GUICtrlSetOnEvent(write_button, self._write_live_data_report)
        clear_button = GUICtrlCreateButton("Clear", 302, 66, 90, 28)
        GUICtrlSetOnEvent(clear_button, self._clear_live_data)
        GUICtrlCreateLabel("Filter:", 410, 72, 40, 20)
        self._live_data_filter_input = GUICtrlCreateInput("", 452, 68, 300, 22)
        GUICtrlSetOnEvent(self._live_data_filter_input, self._live_data_filter_changed)
        self._live_data_status = _Status(GUICtrlCreateLabel("No live data read yet.", 770, 72, 590, 40))
        self._live_data_table = _FilteredRows(
            LIVE_DATA_COLUMNS,
            GUICtrlCreateListView("|".join(LIVE_DATA_COLUMNS), 16, 108, 1340, 728),
        )

    def _run_self_test(self, only_client: bool = False, offline_only: bool = False) -> None:
        """Run the battery and fill the table, one line per check."""

        self.run_self_test(only_client=only_client, offline_only=offline_only)

    # --- the programmatic interface ----------------------------------------------------
    #
    # Everything the buttons do is here as a method that returns what it saw, so the same surface
    # can be driven by a caller -- a script, a test, or the command line at the bottom of this file
    # -- and not only by a person clicking. The buttons are one-line callers of these methods.

    def connect(self, pid: int | None = None) -> ConnectedClient:
        """Connect to a running client and read every context.

        Connecting is a write to the client (the capability layer is installed), so this refuses from
        an unelevated shell before a client is looked at: the library asserts elevation itself, and
        the window does not attempt a connection that will be refused. The pid defaults to the first
        client found.
        """

        if not self._may_connect():
            raise PermissionError(ELEVATION_REFUSAL)

        if not self._clients:
            self._clients = self._win32.find_guild_wars()
        if pid is None:
            if not self._clients:
                raise OSError("no Guild Wars client is running")
            pid = int(self._clients[0]["pid"])
        process = next(
            (candidate for candidate in self._clients if int(candidate["pid"]) == pid),
            None,
        )
        if process is None:
            raise OSError(f"no Guild Wars client with PID {pid} is running")

        self._disconnect_current()
        try:
            self._connection = ConnectedClient(process, self._win32)
            cinematic_snapshot = self._read_cinematic_timed(self._connection)
            camera_snapshot = self._read_camera_timed(self._connection)
            friend_list_snapshot = self._read_friend_list_timed(self._connection)
            chat_buffer_snapshot = self._read_chat_buffer_timed(self._connection)
            world_context_snapshot = self._read_world_context_timed(self._connection)
            map_context_snapshot = self._read_map_context_timed(self._connection)
            trade_context_snapshot = self._read_trade_context_timed(self._connection)
            item_context_snapshot = self._read_item_context_timed(self._connection)
            account_context_snapshot = self._read_account_context_timed(
                self._connection
            )
            gadget_context_snapshot = self._read_gadget_context_timed(
                self._connection
            )
            gameplay_snapshot = self._read_gameplay_context_timed(self._connection)
            server_region_snapshot = self._read_server_region_timed(self._connection)
            instance_info_snapshot = self._read_instance_info_timed(self._connection)
            text_parser_snapshot = self._read_text_parser_timed(self._connection)
            available_characters_snapshot = self._read_available_characters_timed(
                self._connection
            )
            party_context_snapshot = self._read_party_context_timed(self._connection)
            guild_context_snapshot = self._read_guild_context_timed(self._connection)
            acc_agent_context_snapshot = self._read_acc_agent_context_timed(
                self._connection
            )
            pre_game_snapshot = self._read_pre_game_context_timed(self._connection)
            game_snapshot = self._read_game_context_timed(self._connection)
            snapshot = self._read_context_timed(self._connection)
            if snapshot is None:
                character = None
                is_logged_in = False
            else:
                character = (
                    snapshot.player_name_str.strip()
                    if snapshot.player_name_str is not None
                    else None
                ) or None
                is_logged_in = snapshot.is_logged_in
        except (OSError, RuntimeError, ValueError) as error:
            self._connection = None
            self._connected_label.set_text(f"Connection failed: {error}")
            raise

        description = character if is_logged_in else "in selection menus"
        self._connected_label.set_text(f"Connected to PID {pid} — {description}")
        # A snapshot is a *lazy* view: a property that follows a pointer reads the client when it is
        # called, which is here, while the tables are being filled. Reforged reads those fields
        # in-process, where a stale pointer yields garbage; this port's read is external and raises,
        # and an exception raised inside a GUI event handler is Tk's to print -- the window would
        # carry on with a half-filled tab. So each context is displayed on its own and the ones that
        # fail are named, instead of the first failure taking the rest of the window with it.
        display: tuple[tuple[str, Callable[[], None]], ...] = (
            ("PreGameContext", lambda: self._show_pre_game_context(pre_game_snapshot)),
            ("Cinematic", lambda: self._show_cinematic(cinematic_snapshot)),
            ("Camera", lambda: self._show_camera(camera_snapshot)),
            ("FriendList", lambda: self._show_friend_list(friend_list_snapshot)),
            ("ChatBuffer", lambda: self._show_chat_buffer(chat_buffer_snapshot)),
            ("WorldContext", lambda: self._show_world_context(world_context_snapshot)),
            ("MapContext", lambda: self._show_map_context(map_context_snapshot)),
            ("TradeContext", lambda: self._show_trade_context(trade_context_snapshot)),
            ("ItemContext", lambda: self._show_item_context(item_context_snapshot)),
            ("AccountContext", lambda: self._show_account_context(account_context_snapshot)),
            ("GadgetContext", lambda: self._show_gadget_context(gadget_context_snapshot)),
            ("GameplayContext", lambda: self._show_gameplay_context(gameplay_snapshot)),
            ("ServerRegion", lambda: self._show_server_region(server_region_snapshot)),
            ("InstanceInfo", lambda: self._show_instance_info(instance_info_snapshot)),
            ("TextParser", lambda: self._show_text_parser(text_parser_snapshot)),
            (
                "AvailableCharacters",
                lambda: self._show_available_characters(available_characters_snapshot),
            ),
            ("PartyContext", lambda: self._show_party_context(party_context_snapshot)),
            ("GuildContext", lambda: self._show_guild_context(guild_context_snapshot)),
            ("AccAgentContext", lambda: self._show_acc_agent_context(acc_agent_context_snapshot)),
            ("GameContext", lambda: self._show_game_context(game_snapshot)),
            ("CharContext", lambda: self._show_context(snapshot)),
        )
        failures: list[str] = []
        for context_label, show in display:
            try:
                show()
            except (OSError, RuntimeError, ValueError) as error:
                failures.append(f"{context_label} ({error})")
        if failures:
            self._connected_label.set_text(
                f"Connected to PID {pid} — {description}; could not display: "
                + "; ".join(failures)
            )
        return self._connection

    def disconnect(self) -> None:
        """Close the connection and empty every context table."""

        self._disconnect_current()

    def self_test_context(self) -> Any:
        """The battery's view of this window: the map, the connection, and the window itself.

        ``window`` is only set once the interface exists, so a headless caller -- the command line
        below -- runs the checks that need no window and skips the rest rather than failing them.
        """

        import self_test

        if not self._surface_entries:
            self._build_surface_map()
        return self_test.Context(
            entries=self._surface_entries,
            client=self._connection,
            window=self if self._window else None,
            connected=self._connected(),
            # Inside the workspace, and the check removes them: nothing is left behind.
            files=[SELF_TEST_WORKING_FULL, SELF_TEST_WORKING_SUMMARY],
        )

    def run_self_test(
        self,
        only_client: bool = False,
        offline_only: bool = False,
        areas: Sequence[str] | None = None,
    ) -> list[Any]:
        """Run the battery, fill both tables, and return the results."""

        import self_test

        if offline_only:
            areas = tuple(area for area in self_test.areas() if area not in ("client", "live safety"))
        self._self_test_status.set_text("running the checks...")
        started = time.perf_counter()
        context = self.self_test_context()
        results = self_test.run_checks(context, areas=areas, only_client=only_client)
        self._self_test_context = context
        self._self_test_results = list(results)
        self._self_test_table.set_rows(self_test.as_rows(results))
        self._self_test_table.refresh()
        self._fill_live_data(context)
        summary = self_test.summarise(results)
        # The first line is what a person reads, so a run with no client says so *in* that line: a
        # clean-looking "PASS 31, FAIL 0, SKIP 19" beside an empty live-data table is how the run of
        # 2026-10-12 was read as a regression when in fact nothing had been read at all.
        head = summary.splitlines()[0]
        if not self._connected():
            head += "  (NO CLIENT CONNECTED: no live data was read)"
        self._self_test_status.set_text(
            f"{head}  in {time.perf_counter() - started:.1f} s"
            + ("" if len(summary.splitlines()) == 1 else "  --  " + " / ".join(summary.splitlines()[1:]))
        )
        return list(results)

    def read_live_data(self, run_checks: bool = True) -> list[dict[str, str]]:
        """Read every value the client's contexts hold, and return them as table rows.

        With ``run_checks`` the client checks are run first -- reading the contexts and judging what
        came back -- and the dump they keep is shown. Without it, the last run's values are shown
        again, which is what the table's own filter does.
        """

        import self_test

        if run_checks:
            self.run_self_test(only_client=True)
        if self._self_test_context is None:
            self._self_test_context = self.self_test_context()
        return self._fill_live_data(self._self_test_context)

    def dump_live_data(
        self,
        path: str | Path | None = None,
        *,
        json_path: str | Path | None = None,
        run_checks: bool = True,
    ) -> tuple[Path, Path]:
        """Write all the live data to a text file and a JSON file, and return both paths.

        The JSON goes beside the text file unless a second path is given.
        """

        import self_test

        if run_checks and not (self._self_test_context and self._self_test_context.data.get("dump")):
            self.run_self_test(only_client=True)
        if self._self_test_context is None:
            self._self_test_context = self.self_test_context()
        context = self._self_test_context
        results = self._self_test_results
        text_path = Path(path) if path is not None else LIVE_DATA_REPORT_PATH
        data_path = Path(json_path) if json_path is not None else text_path.with_suffix(".json")
        written = self_test.write_data_report(context, results, text_path)
        self_test.write_data_report(context, results, data_path, as_json=True)
        return written, data_path

    def _fill_live_data(self, context: Any) -> list[dict[str, str]]:
        """Show every value of the run in the live-data table and say how many there are."""

        import self_test

        rows = self_test.data_rows(context)
        self._live_data_table.set_rows(rows)
        self._live_data_table.refresh()
        contexts = len(context.data.get("dump") or {})
        self._live_data_status.set_text(
            f"{len(rows)} values from {contexts} contexts"
            + ("" if self._connected() else " — no client connected: connect first")
        )
        return rows

    def _read_live_data_clicked(self) -> None:
        """The Read live data button."""

        try:
            self.read_live_data()
        except (OSError, RuntimeError, ValueError) as error:
            self._live_data_status.set_text(f"could not read the client: {error}")

    def _write_live_data_report(self) -> None:
        """The Write report button: all the live data, as text and as JSON."""

        if self._self_test_context is None:
            self._live_data_status.set_text("Press Read live data first.")
            return
        try:
            text_path, json_path = self.dump_live_data(run_checks=False)
        except (OSError, RuntimeError, ValueError) as error:
            self._live_data_status.set_text(f"could not write the data: {error}")
            return
        self._live_data_status.set_text(f"written to {text_path} and {json_path}")

    def _clear_live_data(self) -> None:
        """The Clear button: empty the live-data table without forgetting the readings."""

        self._live_data_table.set_rows([])
        self._live_data_table.refresh()
        self._live_data_status.set_text("cleared — press Read live data to read the client again")

    def _live_data_filter_changed(self) -> None:
        """Apply the filter box to the live-data table."""

        self._live_data_table.set_filter(GUICtrlRead(self._live_data_filter_input))
        self._live_data_table.refresh()

    def _build_self_test_tab(self) -> None:
        """Create the battery's buttons and its one results table."""

        GUICtrlCreateLabel(
            "One button asks whether this library works, check by check: the map's completeness, the "
            "engine's safety rules, known answers from members that need no client, the window's own "
            "wiring, and -- when a client is connected -- every context reader and live read.",
            16,
            14,
            1340,
            20,
        )
        all_button = GUICtrlCreateButton("Run all checks", 16, 42, 140, 28)
        GUICtrlSetOnEvent(all_button, lambda: self._run_self_test(only_client=False))
        offline_button = GUICtrlCreateButton("Offline checks only", 164, 42, 170, 28)
        GUICtrlSetOnEvent(
            offline_button,
            lambda: self._run_self_test(only_client=False, offline_only=True),
        )
        client_button = GUICtrlCreateButton("Client checks only", 342, 42, 160, 28)
        GUICtrlSetOnEvent(client_button, lambda: self._run_self_test(only_client=True))
        save_button = GUICtrlCreateButton("Save test report", 510, 42, 150, 28)
        GUICtrlSetOnEvent(save_button, self._save_self_test_report)
        self._self_test_status = _Status(
            GUICtrlCreateLabel("Press Run all checks.", 674, 48, 682, 40)
        )
        self._self_test_table = _FilteredRows(
            SELF_TEST_COLUMNS,
            GUICtrlCreateListView("|".join(SELF_TEST_COLUMNS), 16, 96, 1340, 740),
        )
        self._self_test_results: list[Any] = []

    def _save_self_test_report(self) -> None:
        """Write the battery's verdict to a file."""

        import self_test

        if not self._self_test_results:
            self._self_test_status.set_text("Run the checks first.")
            return
        path = self_test.write_report(
            self._self_test_results,
            SELF_TEST_REPORT_PATH,
            header=self._connection_line(),
        )
        self._self_test_status.set_text(
            f"{len(self._self_test_results)} checks written to {path}"
        )

    # --- event handlers ---------------------------------------------------------------

    def _show_context_view(self, index: int) -> None:
        """Show one context's controls and hide the others."""

        for position, view in enumerate(self._context_views):
            view.show(position == index)

    def _run_context_reader(self, view: _ContextView) -> None:
        """Run one context's reader *and its display*, reporting a read that fails.

        Both happen together because a snapshot is a lazy view: the pointer-following properties are
        read while the table is filled, not when the snapshot is made, so a context whose field no
        longer points anywhere raises here rather than in the read. An exception raised inside a GUI
        event handler is Tk's to print and the window would carry on with a half-filled table, so a
        failure is written where that context's status goes.
        """

        try:
            view.refresh()
        except (OSError, RuntimeError, ValueError) as error:
            view.status.set_text(f"{view.label} could not be displayed: {error}")

    def _context_selected(self) -> None:
        """Handle a new selection in the context list: show it and read it.

        Choosing a context reads it, so the table beside the list holds that context's current
        values rather than whatever was captured when the client was connected. An unconnected
        window answers "Connect a client first", which is what the context's own reader reports.
        """

        selected = GUICtrlRead(self._contexts_select)
        for index, view in enumerate(self._context_views):
            if view.label == selected:
                self._show_context_view(index)
                self._run_context_reader(view)
                return

    def _selected_context_view(self) -> _ContextView | None:
        """Return the context whose controls are shown."""

        for view in self._context_views:
            if view.visible:
                return view
        return None

    def _context_filter_changed(self) -> None:
        """Apply the shown context's filter box to its table."""

        view = self._selected_context_view()
        if view is None:
            return
        view.table.set_filter(GUICtrlRead(view.filter_input))
        view.table.refresh()

    def _refresh_clients(self) -> None:
        """Discover Guild Wars clients and read their live identity.

        Without an elevated shell the scan still lists the clients -- that reads the process list,
        which needs no elevation -- but nothing is connected: the library's own precondition is
        asked once here, and neither this refresh nor the Connect button goes near a client.
        """

        try:
            self._clients = self._win32.find_guild_wars()
            rows = [self._inspect_client(process) for process in self._clients]
        except OSError as error:
            self._show_error(error)
            return

        selected = self._client_table.selected_row()
        message = f"Found {len(rows)} Guild Wars client(s)"
        if not self._may_connect():
            message += " — " + ELEVATION_REFUSAL
        self._show_rows(rows, message)
        if selected is not None and all(
            int(candidate["pid"]) != int(selected["pid"]) for candidate in rows
        ):
            self._disconnect_current(
                "No client connected — the client that was selected, PID "
                f"{int(selected['pid'])}, is no longer running"
            )

    def _connection_line(self) -> str:
        """One line about the connection a run used, for the report's own header.

        A report that does not say whether it had a client is the report that gets misread: the run of
        2026-10-12 was `PASS 31, FAIL 0, SKIP 19` with nothing connected, and that reads like a clean
        live run. This line is written into `runtime/self_test_report.txt` beside the summary.
        """

        if self._connected() and self._connection is not None:
            return f"client: connected ({self._connection!r})"
        return "client: NOT CONNECTED — the client and live checks were skipped, no live data was read"

    def _may_connect(self) -> bool:
        """Whether this shell may connect at all -- the library's own precondition, asked once.

        ``ConnectedClient.__init__`` asserts elevation before it resolves or writes anything, so
        an unelevated controller never reaches a client. The window asks the same question up
        front rather than meeting that refusal once per client row: an unelevated run is meant to
        not connect at all.
        """

        return bool(self._win32.is_elevated())

    def _inspect_client(self, process: dict[str, Any]) -> ClientRow:
        """Read one client's character name without keeping its handle open.

        A read that fails is reported as the failure it is: a refused read is not a statement
        about the client, and "in selection menus" is. The two were the same text before, which
        made a refused connection look like a client sitting at the login screen.

        An unelevated shell does not get as far as a read: see :meth:`_may_connect`.
        """

        if not self._may_connect():
            return {
                "pid": int(process["pid"]),
                "name": str(process["name"]),
                "character": "(elevation required)",
                "status": "not read: needs an elevated shell",
                "path": str(process.get("path") or "—"),
            }

        character = None
        is_connected = False
        failure: str | None = None
        try:
            connection = ConnectedClient(process, self._win32, game_thread=False)
            try:
                snapshot = self._read_context_timed(connection)
                if snapshot is None:
                    character = None
                    is_connected = False
                else:
                    character = (
                        snapshot.player_name_str.strip()
                        if snapshot.player_name_str is not None
                        else None
                    ) or None
                    is_connected = snapshot.is_logged_in
            finally:
                connection.close()
        except (OSError, RuntimeError, ValueError) as error:
            character = None
            first_line = str(error).splitlines()[0] if str(error) else type(error).__name__
            # The status column is one table cell: the first line of the failure, kept short.
            failure = first_line if len(first_line) <= 120 else first_line[:117] + "..."

        if failure is not None:
            return {
                "pid": int(process["pid"]),
                "name": str(process["name"]),
                "character": "(unread)",
                "status": f"read failed: {failure}",
                "path": str(process.get("path") or "—"),
            }

        return {
            "pid": int(process["pid"]),
            "name": str(process["name"]),
            "character": character or "in selection menus",
            # "online", not "connected": this column is the *client's* own state, and the word
            # "connected" belongs to the controller's connection, which is the line under the table
            # ("Connected to PID ..."). Measured live on 2026-10-12: this cell read "connected" for a
            # client the controller was not attached to, and the run that followed was trusted because
            # of it. One word, one meaning.
            "status": "online" if is_connected else "in selection menus",
            "path": str(process.get("path") or "—"),
        }

    def _connect_selected(self) -> None:
        """Connect to the client selected in the client list.

        An unelevated shell is refused here, before a client is looked at: connecting asserts
        elevation, and this window does not attempt a connection the library will refuse. The work
        itself is :meth:`connect`, which a caller can use and which returns the connection.
        """

        if not self._may_connect():
            self._connected_label.set_text(ELEVATION_REFUSAL)
            return

        selected = self._client_table.selected_row()
        if selected is None:
            self._connected_label.set_text("Select a client row first")
            return

        pid = int(selected["pid"])
        if not any(int(candidate["pid"]) == pid for candidate in self._clients):
            self._connected_label.set_text("Refresh the client list first")
            return

        try:
            self.connect(pid)
        except (OSError, RuntimeError, ValueError) as error:
            self._connected_label.set_text(f"Connection failed: {error}")

    def _disconnect_current(self, reason: str = "") -> None:
        """Close the current connection, empty every context table, and say so.

        The label is part of the connection's state, not decoration: dropping the connection without
        changing it left the window saying *Connected to PID ...* over a closed client, and a battery
        run then skipped every client check under a prompt that claimed otherwise (measured live,
        2026-10-12). Whatever closes the connection says so, in the caller's own words when it has
        them (``reason``).
        """

        was_connected = self._connection is not None
        if self._connection is not None:
            self._connection.close()
            self._connection = None
        for view in self._context_views:
            view.table.set_rows([])
            view.table.set_filter("")
            view.table.refresh()
        self._data_status.set_text("Connect a client first")
        if was_connected:
            self._connected_label.set_text(reason or "No client connected — the connection was closed")
        self._live_data_status.set_text("No live data: no client is connected.")

    def _show_rows(self, rows: list[ClientRow], message: str) -> None:
        """Replace the client list's contents and update its status text."""

        self._client_table.set_rows(rows)
        self._client_table.refresh()
        self._client_status.set_text(message)

    def _show_error(self, error: OSError) -> None:
        """Display a Win32 failure without hiding its diagnostic message."""

        self._client_table.set_rows([])
        self._client_table.refresh()
        self._client_status.set_text(f"Win32 error: {error}")

    def _refresh_cinematic(self) -> None:
        """Read a fresh Cinematic snapshot for the selected client."""

        if self._connection is None or not self._connection.is_connected:
            self._cinematic_status.set_text("Connect a client first")
            return
        try:
            snapshot = self._read_cinematic_timed(self._connection)
        except (OSError, RuntimeError) as error:
            self._cinematic_status.set_text(f"Context read failed: {error}")
            return
        self._show_cinematic(snapshot)

    def _refresh_camera(self) -> None:
        """Read a fresh read-only Camera snapshot for the selected client."""

        if self._connection is None or not self._connection.is_connected:
            self._camera_status.set_text("Connect a client first")
            return
        try:
            snapshot = self._read_camera_timed(self._connection)
        except (OSError, RuntimeError) as error:
            self._camera_status.set_text(f"Context read failed: {error}")
            return
        self._show_camera(snapshot)

    def _refresh_friend_list(self) -> None:
        """Read a fresh bounded FriendList snapshot for the selected client."""

        if self._connection is None or not self._connection.is_connected:
            self._friend_list_status.set_text("Connect a client first")
            return
        try:
            snapshot = self._read_friend_list_timed(self._connection)
        except (OSError, RuntimeError) as error:
            self._friend_list_status.set_text(f"Context read failed: {error}")
            return
        self._show_friend_list(snapshot)

    def _refresh_chat_buffer(self) -> None:
        """Read a fresh bounded ChatBuffer snapshot for the selected client."""

        if self._connection is None or not self._connection.is_connected:
            self._chat_buffer_status.set_text("Connect a client first")
            return
        try:
            snapshot = self._read_chat_buffer_timed(self._connection)
        except (OSError, RuntimeError) as error:
            self._chat_buffer_status.set_text(f"Context read failed: {error}")
            return
        self._show_chat_buffer(snapshot)

    def _refresh_world_context(self) -> None:
        """Read a fresh WorldContext root for the selected client."""

        if self._connection is None or not self._connection.is_connected:
            self._world_context_status.set_text("Connect a client first")
            return
        try:
            snapshot = self._read_world_context_timed(self._connection)
        except (OSError, RuntimeError) as error:
            self._world_context_status.set_text(f"Context read failed: {error}")
            return
        self._show_world_context(snapshot)

    def _refresh_map_context(self) -> None:
        """Read a fresh MapContext root and bounded spawn snapshot."""

        if self._connection is None or not self._connection.is_connected:
            self._map_context_status.set_text("Connect a client first")
            return
        try:
            snapshot = self._read_map_context_timed(self._connection)
        except (OSError, RuntimeError, ValueError) as error:
            self._map_context_status.set_text(f"Context read failed: {error}")
            return
        self._show_map_context(snapshot)

    def _refresh_trade_context(self) -> None:
        """Read a fresh TradeContext snapshot for the selected client."""

        if self._connection is None or not self._connection.is_connected:
            self._trade_context_status.set_text("Connect a client first")
            return
        try:
            snapshot = self._read_trade_context_timed(self._connection)
        except (OSError, RuntimeError) as error:
            self._trade_context_status.set_text(f"Context read failed: {error}")
            return
        self._show_trade_context(snapshot)

    def _refresh_item_context(self) -> None:
        """Read a fresh ItemContext root for the selected client."""

        if self._connection is None or not self._connection.is_connected:
            self._item_context_status.set_text("Connect a client first")
            return
        try:
            snapshot = self._read_item_context_timed(self._connection)
        except (OSError, RuntimeError) as error:
            self._item_context_status.set_text(f"Context read failed: {error}")
            return
        self._show_item_context(snapshot)

    def _refresh_account_context(self) -> None:
        """Read a fresh AccountContext root for the selected client."""

        if self._connection is None or not self._connection.is_connected:
            self._account_context_status.set_text("Connect a client first")
            return
        try:
            snapshot = self._read_account_context_timed(self._connection)
        except (OSError, RuntimeError) as error:
            self._account_context_status.set_text(
                f"Context read failed: {error}"
            )
            return
        self._show_account_context(snapshot)

    def _refresh_gadget_context(self) -> None:
        """Read a fresh GadgetContext root for the selected client."""

        if self._connection is None or not self._connection.is_connected:
            self._gadget_context_status.set_text("Connect a client first")
            return
        try:
            snapshot = self._read_gadget_context_timed(self._connection)
        except (OSError, RuntimeError) as error:
            self._gadget_context_status.set_text(
                f"Context read failed: {error}"
            )
            return
        self._show_gadget_context(snapshot)

    def _refresh_gameplay_context(self) -> None:
        """Read a fresh GameplayContext snapshot for the selected client."""

        if self._connection is None or not self._connection.is_connected:
            self._gameplay_context_status.set_text("Connect a client first")
            return
        try:
            snapshot = self._read_gameplay_context_timed(self._connection)
        except (OSError, RuntimeError) as error:
            self._gameplay_context_status.set_text(
                f"Context read failed: {error}"
            )
            return
        self._show_gameplay_context(snapshot)

    def _refresh_server_region(self) -> None:
        """Read a fresh ServerRegion snapshot for the selected client."""

        if self._connection is None or not self._connection.is_connected:
            self._server_region_status.set_text("Connect a client first")
            return
        try:
            snapshot = self._read_server_region_timed(self._connection)
        except (OSError, RuntimeError) as error:
            self._server_region_status.set_text(f"Context read failed: {error}")
            return
        self._show_server_region(snapshot)

    def _refresh_instance_info(self) -> None:
        """Read a fresh InstanceInfo snapshot for the selected client."""

        if self._connection is None or not self._connection.is_connected:
            self._instance_info_status.set_text("Connect a client first")
            return
        try:
            snapshot = self._read_instance_info_timed(self._connection)
        except (OSError, RuntimeError) as error:
            self._instance_info_status.set_text(
                f"Context read failed: {error}"
            )
            return
        self._show_instance_info(snapshot)

    def _refresh_text_parser(self) -> None:
        """Read a fresh TextParser snapshot for the selected client."""

        if self._connection is None or not self._connection.is_connected:
            self._text_parser_status.set_text("Connect a client first")
            return
        try:
            snapshot = self._read_text_parser_timed(self._connection)
        except (OSError, RuntimeError) as error:
            self._text_parser_status.set_text(f"Context read failed: {error}")
            return
        self._show_text_parser(snapshot)

    def _refresh_available_characters(self) -> None:
        """Read a fresh account-roster snapshot for the selected client."""

        if self._connection is None or not self._connection.is_connected:
            self._available_characters_status.set_text("Connect a client first")
            return
        try:
            snapshot = self._read_available_characters_timed(self._connection)
        except (OSError, RuntimeError) as error:
            self._available_characters_status.set_text(
                f"Context read failed: {error}"
            )
            return
        self._show_available_characters(snapshot)

    def _refresh_party_context(self) -> None:
        """Read a fresh PartyContext snapshot for the selected client."""

        if self._connection is None or not self._connection.is_connected:
            self._party_context_status.set_text("Connect a client first")
            return
        try:
            snapshot = self._read_party_context_timed(self._connection)
        except (OSError, RuntimeError) as error:
            self._party_context_status.set_text(f"Context read failed: {error}")
            return
        self._show_party_context(snapshot)

    def _refresh_guild_context(self) -> None:
        """Read a fresh GuildContext snapshot for the selected client."""

        if self._connection is None or not self._connection.is_connected:
            self._guild_context_status.set_text("Connect a client first")
            return
        try:
            snapshot = self._read_guild_context_timed(self._connection)
        except (OSError, RuntimeError) as error:
            self._guild_context_status.set_text(f"Context read failed: {error}")
            return
        self._show_guild_context(snapshot)

    def _refresh_acc_agent_context(self) -> None:
        """Read a fresh AccAgentContext snapshot for the selected client."""

        if self._connection is None or not self._connection.is_connected:
            self._acc_agent_context_status.set_text("Connect a client first")
            return
        try:
            snapshot = self._read_acc_agent_context_timed(self._connection)
        except (OSError, RuntimeError) as error:
            self._acc_agent_context_status.set_text(
                f"Context read failed: {error}"
            )
            return
        self._show_acc_agent_context(snapshot)

    def _refresh_pre_game_context(self) -> None:
        """Read a fresh PreGameContext snapshot for the selected client."""

        if self._connection is None or not self._connection.is_connected:
            self._pre_game_context_status.set_text("Connect a client first")
            return
        try:
            snapshot = self._read_pre_game_context_timed(self._connection)
        except (OSError, RuntimeError) as error:
            self._pre_game_context_status.set_text(
                f"Context read failed: {error}"
            )
            return
        self._show_pre_game_context(snapshot)

    def _refresh_game_context(self) -> None:
        """Read a fresh GameContext snapshot for the selected client."""

        if self._connection is None or not self._connection.is_connected:
            self._game_context_status.set_text("Connect a client first")
            return
        try:
            snapshot = self._read_game_context_timed(self._connection)
        except (OSError, RuntimeError) as error:
            self._game_context_status.set_text(f"Context read failed: {error}")
            return
        self._show_game_context(snapshot)

    def _refresh_context(self) -> None:
        """Read a fresh CharContext snapshot for the selected client."""

        if self._connection is None or not self._connection.is_connected:
            self._context_status.set_text("Connect a client first")
            return
        try:
            snapshot = self._read_context_timed(self._connection)
        except (OSError, RuntimeError) as error:
            self._context_status.set_text(f"Context read failed: {error}")
            return
        self._show_context(snapshot)

    def _recent_ms(self, metric_name: str) -> float | None:
        """Return the newest stored sample for a metric, or ``None``.

        The ported counter stores one averaged sample per six completed
        measurements, so this is the most recent completed sample rather than
        the last single read. The source's ``Profiler::End`` returns nothing,
        and ``GetMetricHistory`` is the function that exposes stored samples.
        """

        history = self._perf.get_history(metric_name)
        return history[-1] if history else None

    def _read_context_timed(
        self, connection: ConnectedClient
    ) -> CharContextStruct | None:
        """Read one CharContext snapshot and retain its elapsed time.

        Returns ``None`` while the readiness gate is closed, which the caller
        already treats as "no context to display".
        """

        metric_name = "CharContext.read"
        self._perf.start(metric_name)
        try:
            return connection.read_char_context()
        finally:
            self._last_context_read_ms = self._recent_ms(metric_name)

    def _read_game_context_timed(
        self, connection: ConnectedClient
    ) -> GameContextStruct:
        """Read one GameContext snapshot and retain its elapsed time."""

        metric_name = "GameContext.read"
        self._perf.start(metric_name)
        try:
            return connection.read_game_context()
        finally:
            self._last_game_context_read_ms = self._recent_ms(metric_name)

    def _read_pre_game_context_timed(
        self, connection: ConnectedClient
    ) -> PreGameContextStruct | None:
        """Read one PreGameContext snapshot and retain its elapsed time."""

        metric_name = "PreGameContext.read"
        self._perf.start(metric_name)
        try:
            return connection.read_pre_game_context()
        finally:
            self._last_pre_game_context_read_ms = self._recent_ms(metric_name)

    def _read_cinematic_timed(
        self, connection: ConnectedClient
    ) -> CinematicStruct | None:
        """Read one Cinematic snapshot and retain its elapsed time."""

        metric_name = "Cinematic.read"
        self._perf.start(metric_name)
        try:
            return connection.read_cinematic_context()
        finally:
            self._last_cinematic_read_ms = self._recent_ms(metric_name)

    def _read_camera_timed(
        self, connection: ConnectedClient
    ) -> CameraStruct | None:
        """Read one Camera snapshot and retain its elapsed time."""

        metric_name = "Camera.read"
        self._perf.start(metric_name)
        try:
            return connection.read_camera_context()
        finally:
            self._last_camera_read_ms = self._recent_ms(metric_name)

    def _read_friend_list_timed(
        self, connection: ConnectedClient
    ) -> FriendListStruct | None:
        """Read one FriendList snapshot and retain its elapsed time."""

        metric_name = "FriendList.read"
        self._perf.start(metric_name)
        try:
            return connection.read_friend_list()
        finally:
            self._last_friend_list_read_ms = self._recent_ms(metric_name)

    def _read_chat_buffer_timed(
        self, connection: ConnectedClient
    ) -> ChatBufferStruct | None:
        """Read one ChatBuffer snapshot and retain its elapsed time."""

        metric_name = "ChatBuffer.read"
        self._perf.start(metric_name)
        try:
            return connection.read_chat_buffer()
        finally:
            self._last_chat_buffer_read_ms = self._recent_ms(metric_name)

    def _read_world_context_timed(
        self, connection: ConnectedClient
    ) -> WorldContextStruct | None:
        """Read one WorldContext root and retain its elapsed time."""

        metric_name = "WorldContext.read"
        self._perf.start(metric_name)
        try:
            return connection.read_world_context()
        finally:
            self._last_world_context_read_ms = self._recent_ms(metric_name)

    def _read_map_context_timed(
        self, connection: ConnectedClient
    ) -> MapContextStruct | None:
        """Read one MapContext root and retain its elapsed time."""

        metric_name = "MapContext.read"
        self._perf.start(metric_name)
        try:
            return connection.read_map_context()
        finally:
            self._last_map_context_read_ms = self._recent_ms(metric_name)

    def _read_trade_context_timed(
        self, connection: ConnectedClient
    ) -> TradeContextStruct | None:
        """Read one TradeContext snapshot and retain its elapsed time."""

        metric_name = "TradeContext.read"
        self._perf.start(metric_name)
        try:
            return connection.read_trade_context()
        finally:
            self._last_trade_context_read_ms = self._recent_ms(metric_name)

    def _read_item_context_timed(
        self, connection: ConnectedClient
    ) -> ItemContextStruct | None:
        """Read one ItemContext root and retain its elapsed time."""

        metric_name = "ItemContext.read"
        self._perf.start(metric_name)
        try:
            return connection.read_item_context()
        finally:
            self._last_item_context_read_ms = self._recent_ms(metric_name)

    def _read_account_context_timed(
        self, connection: ConnectedClient
    ) -> AccountContextStruct | None:
        """Read one AccountContext root and retain its elapsed time."""

        metric_name = "AccountContext.read"
        self._perf.start(metric_name)
        try:
            return connection.read_account_context()
        finally:
            self._last_account_context_read_ms = self._recent_ms(metric_name)

    def _read_gadget_context_timed(
        self, connection: ConnectedClient
    ) -> GadgetContextStruct | None:
        """Read one GadgetContext root and retain its elapsed time."""

        metric_name = "GadgetContext.read"
        self._perf.start(metric_name)
        try:
            return connection.read_gadget_context()
        finally:
            self._last_gadget_context_read_ms = self._recent_ms(metric_name)

    def _read_gameplay_context_timed(
        self, connection: ConnectedClient
    ) -> GameplayContextStruct | None:
        """Read one GameplayContext snapshot and retain its elapsed time."""

        metric_name = "GameplayContext.read"
        self._perf.start(metric_name)
        try:
            return connection.read_gameplay_context()
        finally:
            self._last_gameplay_context_read_ms = self._recent_ms(metric_name)

    def _read_server_region_timed(
        self, connection: ConnectedClient
    ) -> ServerRegionStruct | None:
        """Read one ServerRegion snapshot and retain its elapsed time."""

        metric_name = "ServerRegion.read"
        self._perf.start(metric_name)
        try:
            return connection.read_server_region()
        finally:
            self._last_server_region_read_ms = self._recent_ms(metric_name)

    def _read_instance_info_timed(
        self, connection: ConnectedClient
    ) -> InstanceInfoStruct | None:
        """Read one InstanceInfo snapshot and retain its elapsed time."""

        metric_name = "InstanceInfo.read"
        self._perf.start(metric_name)
        try:
            return connection.read_instance_info()
        finally:
            self._last_instance_info_read_ms = self._recent_ms(metric_name)

    def _read_text_parser_timed(
        self, connection: ConnectedClient
    ) -> TextParserStruct | None:
        """Read one TextParser snapshot and retain its elapsed time."""

        metric_name = "TextParser.read"
        self._perf.start(metric_name)
        try:
            return connection.read_text_parser()
        finally:
            self._last_text_parser_read_ms = self._recent_ms(metric_name)

    def _read_available_characters_timed(
        self, connection: ConnectedClient
    ) -> AvailableCharacterArrayStruct | None:
        """Read one account-roster snapshot and retain its elapsed time."""

        metric_name = "AvailableCharacters.read"
        self._perf.start(metric_name)
        try:
            return connection.read_available_characters()
        finally:
            self._last_available_characters_read_ms = self._recent_ms(metric_name)

    def _read_party_context_timed(
        self, connection: ConnectedClient
    ) -> PartyContextStruct | None:
        """Read one PartyContext snapshot and retain its elapsed time."""

        metric_name = "PartyContext.read"
        self._perf.start(metric_name)
        try:
            return connection.read_party_context()
        finally:
            self._last_party_context_read_ms = self._recent_ms(metric_name)

    def _read_guild_context_timed(
        self, connection: ConnectedClient
    ) -> GuildContextStruct | None:
        """Read one GuildContext snapshot and retain its elapsed time."""

        metric_name = "GuildContext.read"
        self._perf.start(metric_name)
        try:
            return connection.read_guild_context()
        finally:
            self._last_guild_context_read_ms = self._recent_ms(metric_name)

    def _read_acc_agent_context_timed(
        self, connection: ConnectedClient
    ) -> AccAgentContextStruct | None:
        """Read one AccAgentContext snapshot and retain its elapsed time."""

        metric_name = "AccAgentContext.read"
        self._perf.start(metric_name)
        try:
            return connection.read_acc_agent_context()
        finally:
            self._last_acc_agent_context_read_ms = self._recent_ms(metric_name)

    def _show_cinematic(self, snapshot: CinematicStruct | None) -> None:
        """Display the maintained Cinematic fields when the context is active."""

        if snapshot is None:
            self._cinematic_table.set_rows([])
            self._cinematic_table.refresh()
            self._cinematic_status.set_text(
                "Cinematic is not active — no cinematic data is available"
            )
            return

        rows: list[ContextFieldRow] = []
        for field_info in CinematicStruct._fields_:
            field_name = field_info[0]
            field = getattr(CinematicStruct, field_name)
            value = getattr(snapshot, field_name)
            rows.append(
                {
                    "offset": f"0x{field.offset:04X}",
                    "field": field_name,
                    "value": self._format_context_value(value),
                }
            )
        self._cinematic_table.set_rows(rows)
        self._cinematic_table.refresh()
        timing = ""
        if self._last_cinematic_read_ms is not None:
            timing = f" — read {self._last_cinematic_read_ms:.3f} ms"
        self._cinematic_status.set_text("Cinematic refreshed" + timing)

    def _set_cinematic_filter(self, value: Any) -> None:
        """Apply the field/value filter to the Cinematic table."""

        if self._cinematic_table is None:
            return
        self._cinematic_table.set_filter(str(value or ""))
        self._cinematic_table.refresh()

    def _show_camera(self, snapshot: CameraStruct | None) -> None:
        """Display camera properties and the maintained raw fields."""

        if snapshot is None:
            self._camera_table.set_rows([])
            self._camera_table.refresh()
            self._camera_status.set_text(
                "Camera is not available — no camera data was resolved"
            )
            return

        rows: list[ContextFieldRow] = [
            {
                "offset": "property",
                "field": "is_unlocked",
                "value": str(snapshot.is_unlocked),
            },
            {
                "offset": "property",
                "field": "position",
                "value": self._format_context_value(snapshot.position),
            },
            {
                "offset": "property",
                "field": "look_at_target",
                "value": self._format_context_value(snapshot.look_at_target),
            },
        ]
        for field_info in CameraStruct._fields_:
            field_name = field_info[0]
            field = getattr(CameraStruct, field_name)
            value = getattr(snapshot, field_name)
            rows.append(
                {
                    "offset": f"0x{field.offset:04X}",
                    "field": field_name,
                    "value": self._format_context_value(value),
                }
            )
        self._camera_table.set_rows(rows)
        self._camera_table.refresh()
        timing = ""
        if self._last_camera_read_ms is not None:
            timing = f" — read {self._last_camera_read_ms:.3f} ms"
        self._camera_status.set_text("Camera refreshed" + timing)

    def _set_camera_filter(self, value: Any) -> None:
        """Apply the field/value filter to the Camera table."""

        if self._camera_table is None:
            return
        self._camera_table.set_filter(str(value or ""))
        self._camera_table.refresh()

    def _show_friend_list(self, snapshot: FriendListStruct | None) -> None:
        """Display friend-list counts, status, and bounded friend records."""

        if snapshot is None:
            self._friend_list_table.set_rows([])
            self._friend_list_table.refresh()
            self._friend_list_status.set_text("FriendList is not available")
            return

        try:
            friends = snapshot.friend_records
        except OSError as error:
            self._friend_list_table.set_rows([])
            self._friend_list_table.refresh()
            self._friend_list_status.set_text(f"FriendList read failed: {error}")
            return

        rows: list[ContextFieldRow] = [
            {
                "offset": "property",
                "field": "player_status",
                "value": snapshot.status.name,
            },
            {
                "offset": "property",
                "field": "friend_records",
                "value": f"count={len(friends)}",
            },
        ]
        for index, friend in enumerate(friends):
            rows.append(
                {
                    "offset": "array",
                    "field": f"friend[{index}]",
                    "value": (
                        f"type={friend.friend_type.name}, status={friend.friend_status.name}, "
                        f"alias={friend.alias_str or '(none)'}, "
                        f"character={friend.character_name_str or '(none)'}, "
                        f"friend_id={friend.friend_id}, zone_id={friend.zone_id}"
                    ),
                }
            )
        for field_info in FriendListStruct._fields_:
            field_name = field_info[0]
            field = getattr(FriendListStruct, field_name)
            value = getattr(snapshot, field_name)
            rows.append(
                {
                    "offset": f"0x{field.offset:04X}",
                    "field": field_name,
                    "value": self._format_context_value(value),
                }
            )
        self._friend_list_table.set_rows(rows)
        self._friend_list_table.refresh()
        timing = ""
        if self._last_friend_list_read_ms is not None:
            timing = f" — read {self._last_friend_list_read_ms:.3f} ms"
        self._friend_list_status.set_text(
            f"FriendList refreshed ({len(friends)} records)" + timing
        )

    def _set_friend_list_filter(self, value: Any) -> None:
        """Apply the field/value filter to the FriendList table."""

        if self._friend_list_table is None:
            return
        self._friend_list_table.set_filter(str(value or ""))
        self._friend_list_table.refresh()

    def _show_chat_buffer(self, snapshot: ChatBufferStruct | None) -> None:
        """Display chat-ring metadata and a bounded set of decoded messages."""

        if snapshot is None:
            self._chat_buffer_table.set_rows([])
            self._chat_buffer_table.refresh()
            self._chat_buffer_status.set_text("ChatBuffer is not available")
            return

        try:
            messages = snapshot.message_records
            is_typing = self._connection.is_typing() if self._connection else False
        except OSError as error:
            self._chat_buffer_table.set_rows([])
            self._chat_buffer_table.refresh()
            self._chat_buffer_status.set_text(f"ChatBuffer read failed: {error}")
            return

        rows: list[ContextFieldRow] = [
            {
                "offset": "property",
                "field": "is_typing",
                "value": str(is_typing),
            },
            {
                "offset": "property",
                "field": "message_count",
                "value": f"count={len(messages)}",
            },
        ]
        for index, message in enumerate(messages[:128]):
            try:
                text = message.message_str
            except OSError:
                text = "(unreadable)"
            timestamp = message.timestamp_utc
            timestamp_text = timestamp.isoformat() if timestamp else "(invalid)"
            rows.append(
                {
                    "offset": "array",
                    "field": f"message[{index}]",
                    "value": (
                        f"channel={message.channel}, timestamp={timestamp_text}, "
                        f"text={text}"
                    ),
                }
            )
        for field_info in ChatBufferStruct._fields_[:3]:
            field_name = field_info[0]
            field = getattr(ChatBufferStruct, field_name)
            value = getattr(snapshot, field_name)
            rows.append(
                {
                    "offset": f"0x{field.offset:04X}",
                    "field": field_name,
                    "value": self._format_context_value(value),
                }
            )
        self._chat_buffer_table.set_rows(rows)
        self._chat_buffer_table.refresh()
        timing = ""
        if self._last_chat_buffer_read_ms is not None:
            timing = f" — read {self._last_chat_buffer_read_ms:.3f} ms"
        self._chat_buffer_status.set_text(
            f"ChatBuffer refreshed ({len(messages)} messages; displaying up to 128)"
            + timing
        )

    def _set_chat_buffer_filter(self, value: Any) -> None:
        """Apply the field/value filter to the ChatBuffer table."""

        if self._chat_buffer_table is None:
            return
        self._chat_buffer_table.set_filter(str(value or ""))
        self._chat_buffer_table.refresh()

    def _show_map_context(self, snapshot: MapContextStruct | None) -> None:
        """Display the MapContext root and a bounded list of spawn points."""

        if snapshot is None:
            self._map_context_table.set_rows([])
            self._map_context_table.refresh()
            self._map_context_status.set_text("MapContext is not available")
            return

        rows: list[ContextFieldRow] = [
            {
                "offset": "property",
                "field": "address",
                "value": (
                    f"0x{snapshot.address:08X}"
                    if snapshot.address is not None
                    else "(unknown)"
                ),
            },
            {"offset": "property", "field": "map_type", "value": str(int(snapshot.map_type))},
            {"offset": "property", "field": "map_id", "value": str(int(snapshot.map_id))},
            {"offset": "property", "field": "start_pos", "value": self._format_context_value((float(snapshot.start_pos.x), float(snapshot.start_pos.y)))},
            {"offset": "property", "field": "end_pos", "value": self._format_context_value((float(snapshot.end_pos.x), float(snapshot.end_pos.y)))},
            {"offset": "property", "field": "map_boundaries", "value": self._format_context_value(snapshot.map_boundaries)},
            {"offset": "property", "field": "spawn_array_sizes", "value": self._format_context_value(snapshot.spawn_array_sizes)},
            {"offset": "property", "field": "path_address", "value": self._format_pointer(snapshot.path_address)},
            {"offset": "property", "field": "props_address", "value": self._format_pointer(snapshot.props_address)},
            {"offset": "property", "field": "terrain_address", "value": self._format_pointer(snapshot.terrain_address)},
            {"offset": "property", "field": "zones_address", "value": self._format_pointer(snapshot.zones_address)},
        ]

        try:
            path_context = snapshot.path_context
            static_data = path_context.static_data if path_context is not None else None
            pathing_maps = static_data.pathing_maps if static_data is not None else []
        except (OSError, RuntimeError, ValueError) as error:
            path_context = None
            static_data = None
            pathing_maps = []
            rows.append(
                {"offset": "property", "field": "pathing_read_error", "value": str(error)}
            )

        rows.extend(
            [
                {
                    "offset": "property",
                    "field": "path_context_address",
                    "value": self._format_pointer(
                        path_context.address if path_context is not None else None
                    ),
                },
                {
                    "offset": "property",
                    "field": "static_data_address",
                    "value": self._format_pointer(
                        static_data.address if static_data is not None else None
                    ),
                },
                {
                    "offset": "property",
                    "field": "pathing_map_sizes",
                    "value": self._format_context_value(
                        static_data.pathing_map_sizes if static_data is not None else None
                    ),
                },
                {
                    "offset": "property",
                    "field": "pathing_maps_read",
                    "value": str(len(pathing_maps)),
                },
            ]
        )
        for index, pathing_map in enumerate(pathing_maps):
            rows.append(
                {
                    "offset": "pathing",
                    "field": f"pathing_maps[{index}]",
                    "value": (
                        f"zplane={pathing_map.zplane}, "
                        f"trapezoids={pathing_map.trapezoid_count}, "
                        f"sink_nodes={pathing_map.sink_node_count}, "
                        f"x_nodes={pathing_map.x_node_count}, "
                        f"y_nodes={pathing_map.y_node_count}, "
                        f"portals={pathing_map.portal_count}, "
                        f"trapezoids_ptr={self._format_pointer(pathing_map.trapezoids_address)}, "
                        f"sink_nodes_ptr={self._format_pointer(pathing_map.sink_nodes_address)}, "
                        f"x_nodes_ptr={self._format_pointer(pathing_map.x_nodes_address)}, "
                        f"y_nodes_ptr={self._format_pointer(pathing_map.y_nodes_address)}, "
                        f"portals_ptr={self._format_pointer(pathing_map.portals_address)}, "
                        f"root_node_ptr={self._format_pointer(pathing_map.root_node_address)}"
                    ),
                }
            )

        arrays = (
            ("spawns1", lambda: snapshot.spawns1),
            ("spawns2", lambda: snapshot.spawns2),
            ("spawns3", lambda: snapshot.spawns3),
        )
        for array_name, read_array in arrays:
            try:
                spawn_points = read_array()
            except (OSError, RuntimeError, ValueError) as error:
                rows.append(
                    {
                        "offset": "array",
                        "field": f"{array_name}.error",
                        "value": str(error),
                    }
                )
                continue
            rows.append(
                {
                    "offset": "array",
                    "field": f"{array_name}.count",
                    "value": str(len(spawn_points)),
                }
            )
            for index, spawn in enumerate(spawn_points[:64]):
                rows.append(
                    {
                        "offset": "array",
                        "field": f"{array_name}[{index}]",
                        "value": (
                            f"x={spawn.x:.3f}, y={spawn.y:.3f}, "
                            f"angle={spawn.angle:.3f}, tag={spawn.tag or '(empty)'}, "
                            f"map_id={spawn.map_id}, default={spawn.is_default}"
                        ),
                    }
                )

        for field_info in MapContextStruct._fields_:
            field_name = field_info[0]
            field = getattr(MapContextStruct, field_name)
            value = getattr(snapshot, field_name)
            rows.append(
                {
                    "offset": f"0x{field.offset:04X}",
                    "field": field_name,
                    "value": self._format_context_value(value),
                }
            )
        self._map_context_table.set_rows(rows)
        self._map_context_table.refresh()
        timing = ""
        if self._last_map_context_read_ms is not None:
            timing = f" — read {self._last_map_context_read_ms:.3f} ms"
        self._map_context_status.set_text(
            f"MapContext refreshed; {len(rows)} rows{timing}"
        )

    def _set_map_context_filter(self, value: Any) -> None:
        """Apply the field/value filter to the MapContext table."""

        if self._map_context_table is None:
            return
        self._map_context_table.set_filter(str(value or ""))
        self._map_context_table.refresh()

    def _show_world_context(self, snapshot: WorldContextStruct | None) -> None:
        """Display world-root scalars and array counts without child traversal."""

        if snapshot is None:
            self._world_context_table.set_rows([])
            self._world_context_table.refresh()
            self._world_context_status.set_text("WorldContext is not available")
            return

        try:
            message_buffer = snapshot.message_buffer
        except (OSError, RuntimeError):
            message_buffer = "(unreadable)"
        try:
            dialog_buffer = snapshot.dialog_buffer
        except (OSError, RuntimeError):
            dialog_buffer = "(unreadable)"
        try:
            party_attributes = snapshot.party_attributes or []
        except (OSError, RuntimeError):
            party_attributes = []
        try:
            party_effects = snapshot.party_effects or []
        except (OSError, RuntimeError):
            party_effects = []
        try:
            players = snapshot.players or []
        except (OSError, RuntimeError):
            players = []
        try:
            npc_models = snapshot.npc_models or []
        except (OSError, RuntimeError):
            npc_models = []
        try:
            hero_flags = snapshot.hero_flags or []
        except (OSError, RuntimeError):
            hero_flags = []
        try:
            hero_info = snapshot.hero_info or []
        except (OSError, RuntimeError):
            hero_info = []
        try:
            pets = snapshot.pets or []
        except (OSError, RuntimeError):
            pets = []
        try:
            skillbars = snapshot.skillbars or []
        except (OSError, RuntimeError):
            skillbars = []
        try:
            learnable_skills = snapshot.learnable_character_skills or []
        except (OSError, RuntimeError):
            learnable_skills = []
        try:
            unlocked_skills = snapshot.unlocked_character_skills or []
        except (OSError, RuntimeError):
            unlocked_skills = []
        try:
            duplicated_skills = snapshot.duplicated_character_skills or []
        except (OSError, RuntimeError):
            duplicated_skills = []
        try:
            quests = snapshot.quests or []
        except (OSError, RuntimeError):
            quests = []
        try:
            mission_objectives = snapshot.mission_objectives or []
        except (OSError, RuntimeError):
            mission_objectives = []
        try:
            titles = snapshot.titles or []
        except (OSError, RuntimeError):
            titles = []
        try:
            title_tiers = snapshot.title_tiers or []
        except (OSError, RuntimeError):
            title_tiers = []

        rows: list[ContextFieldRow] = [
            {
                "offset": "property",
                "field": "address",
                "value": (
                    f"0x{snapshot.address:08X}"
                    if snapshot.address is not None
                    else "(unknown)"
                ),
            },
            {
                "offset": "property",
                "field": "all_flag_value",
                "value": self._format_context_value(snapshot.all_flag_value),
            },
            {
                "offset": "property",
                "field": "array_sizes",
                "value": self._format_context_value(snapshot.array_sizes),
            },
            {
                "offset": "property",
                "field": "message_buffer",
                "value": message_buffer,
            },
            {
                "offset": "property",
                "field": "dialog_buffer",
                "value": dialog_buffer,
            },
            {
                "offset": "property",
                "field": "party_attribute_blocks",
                "value": f"count={len(party_attributes)}",
            },
            {
                "offset": "property",
                "field": "party_effect_blocks",
                "value": f"count={len(party_effects)}",
            },
            {
                "offset": "property",
                "field": "players",
                "value": f"count={len(players)}",
            },
            {
                "offset": "property",
                "field": "npc_models",
                "value": f"count={len(npc_models)}",
            },
            {
                "offset": "property",
                "field": "hero_flags",
                "value": f"count={len(hero_flags)}",
            },
            {
                "offset": "property",
                "field": "hero_info",
                "value": f"count={len(hero_info)}",
            },
            {
                "offset": "property",
                "field": "pets",
                "value": f"count={len(pets)}",
            },
            {
                "offset": "property",
                "field": "skillbars",
                "value": f"count={len(skillbars)}",
            },
            {
                "offset": "property",
                "field": "learnable_character_skills",
                "value": f"count={len(learnable_skills)}",
            },
            {
                "offset": "property",
                "field": "unlocked_character_skills",
                "value": f"count={len(unlocked_skills)}",
            },
            {
                "offset": "property",
                "field": "duplicated_character_skills",
                "value": f"count={len(duplicated_skills)}",
            },
            {
                "offset": "property",
                "field": "quests",
                "value": f"count={len(quests)}",
            },
            {
                "offset": "property",
                "field": "mission_objectives",
                "value": f"count={len(mission_objectives)}",
            },
            {
                "offset": "property",
                "field": "titles",
                "value": f"count={len(titles)}",
            },
            {
                "offset": "property",
                "field": "title_tiers",
                "value": f"count={len(title_tiers)}",
            },
        ]
        for index, attributes in enumerate(party_attributes[:64]):
            rows.append(
                {
                    "offset": "array",
                    "field": f"party_attributes[{index}]",
                    "value": (
                        f"agent_id={attributes.agent_id}, "
                        f"valid_attributes={len(attributes.valid_attributes)}"
                    ),
                }
            )
        for index, effects in enumerate(party_effects[:64]):
            try:
                buff_count = len(effects.buffs)
                effect_count = len(effects.effects)
            except (OSError, RuntimeError):
                buff_count = effect_count = -1
            rows.append(
                {
                    "offset": "array",
                    "field": f"party_effects[{index}]",
                    "value": (
                        f"agent_id={effects.agent_id}, buffs={buff_count}, "
                        f"effects={effect_count}"
                    ),
                }
            )
        for index, player in enumerate(players[:32]):
            try:
                player_name = player.name_str or "(unnamed)"
            except OSError:
                player_name = "(unreadable)"
            rows.append(
                {
                    "offset": "array",
                    "field": f"players[{index}]",
                    "value": (
                        f"player_number={player.player_number}, "
                        f"agent_id={player.agent_id}, name={player_name}"
                    ),
                }
            )
        for index, npc in enumerate(npc_models[:32]):
            try:
                npc_name = npc.name or "(unnamed)"
            except OSError:
                npc_name = "(unreadable)"
            rows.append(
                {
                    "offset": "array",
                    "field": f"npc_models[{index}]",
                    "value": (
                        f"model_file_id={npc.model_file_id}, "
                        f"flags=0x{npc.npc_flags:08X}, name={npc_name}"
                    ),
                }
            )
        for index, hero in enumerate(hero_info[:32]):
            rows.append(
                {
                    "offset": "array",
                    "field": f"hero_info[{index}]",
                    "value": (
                        f"hero_id={hero.hero_id}, agent_id={hero.agent_id}, "
                        f"level={hero.level}, name={hero.name_str or '(unnamed)'}"
                    ),
                }
            )
        for index, pet in enumerate(pets[:32]):
            try:
                pet_name = pet.pet_name_str or "(unnamed)"
            except OSError:
                pet_name = "(unreadable)"
            rows.append(
                {
                    "offset": "array",
                    "field": f"pets[{index}]",
                    "value": (
                        f"agent_id={pet.agent_id}, owner={pet.owner_agent_id}, "
                        f"name={pet_name}"
                    ),
                }
            )
        for index, skillbar in enumerate(skillbars[:32]):
            rows.append(
                {
                    "offset": "array",
                    "field": f"skillbars[{index}]",
                    "value": (
                        f"agent_id={skillbar.agent_id}, "
                        f"valid={skillbar.is_valid}, "
                        f"skills={[int(skill.skill_id) for skill in skillbar.skills]}"
                    ),
                }
            )
        for index, quest in enumerate(quests[:32]):
            try:
                quest_name = quest.name or "(unnamed)"
            except OSError:
                quest_name = "(unreadable)"
            rows.append(
                {
                    "offset": "array",
                    "field": f"quests[{index}]",
                    "value": (
                        f"quest_id={quest.quest_id}, primary={quest.is_primary}, "
                        f"completed={quest.is_completed}, name={quest_name}"
                    ),
                }
            )
        for index, objective in enumerate(mission_objectives[:32]):
            try:
                objective_text = objective.text or "(unnamed)"
            except OSError:
                objective_text = "(unreadable)"
            rows.append(
                {
                    "offset": "array",
                    "field": f"mission_objectives[{index}]",
                    "value": (
                        f"objective_id={objective.objective_id}, "
                        f"type={objective.type}, text={objective_text}"
                    ),
                }
            )
        for index, title in enumerate(titles[:32]):
            rows.append(
                {
                    "offset": "array",
                    "field": f"titles[{index}]",
                    "value": (
                        f"tier={title.current_title_tier_index}, "
                        f"points={title.current_points}, tiers={title.has_tiers}"
                    ),
                }
            )
        for index, tier in enumerate(title_tiers[:32]):
            try:
                tier_name = tier.name or "(unnamed)"
            except OSError:
                tier_name = "(unreadable)"
            rows.append(
                {
                    "offset": "array",
                    "field": f"title_tiers[{index}]",
                    "value": (
                        f"tier_number={tier.tier_number}, name={tier_name}"
                    ),
                }
            )
        for field_info in WorldContextStruct._fields_:
            field_name = field_info[0]
            field = getattr(WorldContextStruct, field_name)
            value = getattr(snapshot, field_name)
            rows.append(
                {
                    "offset": f"0x{field.offset:04X}",
                    "field": field_name,
                    "value": self._format_context_value(value),
                }
            )
        self._world_context_table.set_rows(rows)
        self._world_context_table.refresh()
        timing = ""
        if self._last_world_context_read_ms is not None:
            timing = f" — read {self._last_world_context_read_ms:.3f} ms"
        self._world_context_status.set_text("WorldContext refreshed" + timing)

    def _set_world_context_filter(self, value: Any) -> None:
        """Apply the field/value filter to the WorldContext table."""

        if self._world_context_table is None:
            return
        self._world_context_table.set_filter(str(value or ""))
        self._world_context_table.refresh()

    def _show_trade_context(self, snapshot: TradeContextStruct | None) -> None:
        """Display trade state and bounded offers without performing actions."""

        if snapshot is None:
            self._trade_context_table.set_rows([])
            self._trade_context_table.refresh()
            self._trade_context_status.set_text("TradeContext is not available")
            return

        try:
            player_offer = snapshot.player_offer
            partner_offer = snapshot.partner_offer
            player_items = player_offer.offered_items
            partner_items = partner_offer.offered_items
        except (OSError, RuntimeError) as error:
            self._trade_context_table.set_rows([])
            self._trade_context_table.refresh()
            self._trade_context_status.set_text(f"TradeContext read failed: {error}")
            return

        rows: list[ContextFieldRow] = [
            {"offset": "property", "field": "is_trade_initiated", "value": str(snapshot.is_trade_initiated)},
            {"offset": "property", "field": "is_trade_offered", "value": str(snapshot.is_trade_offered)},
            {"offset": "property", "field": "is_trade_accepted", "value": str(snapshot.is_trade_accepted)},
            {"offset": "property", "field": "player_items", "value": f"count={len(player_items)}"},
            {"offset": "property", "field": "partner_items", "value": f"count={len(partner_items)}"},
            {"offset": "property", "field": "player_gold", "value": str(player_offer.gold)},
            {"offset": "property", "field": "partner_gold", "value": str(partner_offer.gold)},
        ]
        for side, items in (("player", player_items), ("partner", partner_items)):
            for index, item in enumerate(items):
                rows.append(
                    {
                        "offset": "array",
                        "field": f"{side}_items[{index}]",
                        "value": f"item_id={item.item_id}, quantity={item.quantity}",
                    }
                )
        for field_info in TradeContextStruct._fields_:
            field_name = field_info[0]
            field = getattr(TradeContextStruct, field_name)
            value = getattr(snapshot, field_name)
            rows.append(
                {
                    "offset": f"0x{field.offset:04X}",
                    "field": field_name,
                    "value": self._format_context_value(value),
                }
            )
        self._trade_context_table.set_rows(rows)
        self._trade_context_table.refresh()
        timing = ""
        if self._last_trade_context_read_ms is not None:
            timing = f" — read {self._last_trade_context_read_ms:.3f} ms"
        self._trade_context_status.set_text("TradeContext refreshed" + timing)

    def _set_trade_context_filter(self, value: Any) -> None:
        """Apply the field/value filter to the TradeContext table."""

        if self._trade_context_table is None:
            return
        self._trade_context_table.set_filter(str(value or ""))
        self._trade_context_table.refresh()

    def _show_item_context(self, snapshot: ItemContextStruct | None) -> None:
        """Display the item root and bounded records reached through bags."""

        if snapshot is None:
            self._item_context_table.set_rows([])
            self._item_context_table.refresh()
            self._item_records_table.set_rows([])
            self._item_records_table.refresh()
            self._item_context_status.set_text("ItemContext is not available")
            return

        rows: list[ContextFieldRow] = [
            {
                "offset": "property",
                "field": "address",
                "value": (
                    f"0x{snapshot.address:08X}"
                    if snapshot.address is not None
                    else "(unknown)"
                ),
            },
            {
                "offset": "property",
                "field": "array_sizes",
                "value": self._format_context_value(snapshot.array_sizes),
            },
        ]
        for field_info in ItemContextStruct._fields_:
            field_name = field_info[0]
            field = getattr(ItemContextStruct, field_name)
            value = getattr(snapshot, field_name)
            rows.append(
                {
                    "offset": f"0x{field.offset:04X}",
                    "field": field_name,
                    "value": self._format_context_value(value),
                }
            )
        self._item_context_table.set_rows(rows)
        self._item_context_table.refresh()
        item_rows: list[dict[str, Any]] = []
        item_error: str | None = None
        try:
            for bag in snapshot.bags():
                for item in bag.read_items():
                    item_rows.append(
                        {
                            "bag": bag.bag_id_value,
                            "slot": int(item.slot),
                            "item_id": int(item.item_id),
                            "quantity": int(item.quantity),
                            "model_id": int(item.model_id),
                            "type": int(item.type),
                            "modifier_count": item.modifier_count,
                            "address": (
                                f"0x{item.address:08X}"
                                if item.address is not None
                                else "(unknown)"
                            ),
                        }
                    )
        except (OSError, RuntimeError, ValueError) as error:
            item_error = str(error)
        self._item_records_table.set_rows(item_rows)
        self._item_records_table.refresh()
        timing = ""
        if self._last_item_context_read_ms is not None:
            timing = f" — read {self._last_item_context_read_ms:.3f} ms"
        suffix = f"; item read failed: {item_error}" if item_error else ""
        self._item_context_status.set_text(
            f"ItemContext refreshed; {len(item_rows)} bag items" + timing + suffix
        )

    def _set_item_context_filter(self, value: Any) -> None:
        """Apply the field/value filter to the ItemContext table."""

        if self._item_context_table is None:
            return
        self._item_context_table.set_filter(str(value or ""))
        self._item_context_table.refresh()

    def _show_account_context(
        self, snapshot: AccountContextStruct | None
    ) -> None:
        """Display account-root fields and array headers without traversal."""

        if snapshot is None:
            self._account_context_table.set_rows([])
            self._account_context_table.refresh()
            self._account_context_status.set_text(
                "AccountContext is not available"
            )
            return

        rows: list[ContextFieldRow] = [
            {
                "offset": "property",
                "field": "address",
                "value": (
                    f"0x{snapshot.address:08X}"
                    if snapshot.address is not None
                    else "(unknown)"
                ),
            },
            {
                "offset": "property",
                "field": "array_sizes",
                "value": self._format_context_value(snapshot.array_sizes),
            },
        ]
        for field_info in AccountContextStruct._fields_:
            field_name = field_info[0]
            field = getattr(AccountContextStruct, field_name)
            value = getattr(snapshot, field_name)
            rows.append(
                {
                    "offset": f"0x{field.offset:04X}",
                    "field": field_name,
                    "value": self._format_context_value(value),
                }
            )
        self._account_context_table.set_rows(rows)
        self._account_context_table.refresh()
        timing = ""
        if self._last_account_context_read_ms is not None:
            timing = f" — read {self._last_account_context_read_ms:.3f} ms"
        self._account_context_status.set_text("AccountContext refreshed" + timing)

    def _set_account_context_filter(self, value: Any) -> None:
        """Apply the field/value filter to the AccountContext table."""

        if self._account_context_table is None:
            return
        self._account_context_table.set_filter(str(value or ""))
        self._account_context_table.refresh()

    def _show_gadget_context(self, snapshot: GadgetContextStruct | None) -> None:
        """Display gadget-root metadata and a bounded info sample."""

        if snapshot is None:
            self._gadget_context_table.set_rows([])
            self._gadget_context_table.refresh()
            self._gadget_context_status.set_text("GadgetContext is not available")
            return

        try:
            records = snapshot.gadget_infos(limit=128)
        except (OSError, RuntimeError):
            records = []
        rows: list[ContextFieldRow] = [
            {
                "offset": "property",
                "field": "address",
                "value": (
                    f"0x{snapshot.address:08X}"
                    if snapshot.address is not None
                    else "(unknown)"
                ),
            },
            {
                "offset": "property",
                "field": "gadget_info_count",
                "value": f"advertised={snapshot.array_size}, sample={len(records)}",
            },
        ]
        for index, record in enumerate(records):
            try:
                name = record.name_encoded or "(unnamed)"
            except OSError:
                name = "(unreadable)"
            rows.append(
                {
                    "offset": "array",
                    "field": f"gadget_info[{index}]",
                    "value": (
                        f"h0000=0x{int(record.h0000):08X}, "
                        f"h0004=0x{int(record.h0004):08X}, "
                        f"h0008=0x{int(record.h0008):08X}, name={name}"
                    ),
                }
            )
        for field_info in GadgetContextStruct._fields_:
            field_name = field_info[0]
            field = getattr(GadgetContextStruct, field_name)
            value = getattr(snapshot, field_name)
            rows.append(
                {
                    "offset": f"0x{field.offset:04X}",
                    "field": field_name,
                    "value": self._format_context_value(value),
                }
            )
        self._gadget_context_table.set_rows(rows)
        self._gadget_context_table.refresh()
        timing = ""
        if self._last_gadget_context_read_ms is not None:
            timing = f" — read {self._last_gadget_context_read_ms:.3f} ms"
        self._gadget_context_status.set_text(
            f"GadgetContext refreshed (displaying up to 128)" + timing
        )

    def _set_gadget_context_filter(self, value: Any) -> None:
        """Apply the field/value filter to the GadgetContext table."""

        if self._gadget_context_table is None:
            return
        self._gadget_context_table.set_filter(str(value or ""))
        self._gadget_context_table.refresh()

    def _show_gameplay_context(
        self, snapshot: GameplayContextStruct | None
    ) -> None:
        """Display the maintained GameplayContext fields when active."""

        if snapshot is None:
            self._gameplay_context_table.set_rows([])
            self._gameplay_context_table.refresh()
            self._gameplay_context_status.set_text(
                "GameplayContext is not active — no gameplay data is available"
            )
            return

        rows: list[ContextFieldRow] = []
        for field_info in GameplayContextStruct._fields_:
            field_name = field_info[0]
            field = getattr(GameplayContextStruct, field_name)
            value = getattr(snapshot, field_name)
            rows.append(
                {
                    "offset": f"0x{field.offset:04X}",
                    "field": field_name,
                    "value": self._format_context_value(value),
                }
            )
        self._gameplay_context_table.set_rows(rows)
        self._gameplay_context_table.refresh()
        timing = ""
        if self._last_gameplay_context_read_ms is not None:
            timing = f" — read {self._last_gameplay_context_read_ms:.3f} ms"
        self._gameplay_context_status.set_text(
            "GameplayContext refreshed" + timing
        )

    def _set_gameplay_context_filter(self, value: Any) -> None:
        """Apply the field/value filter to the GameplayContext table."""

        if self._gameplay_context_table is None:
            return
        self._gameplay_context_table.set_filter(str(value or ""))
        self._gameplay_context_table.refresh()

    def _show_server_region(self, snapshot: ServerRegionStruct | None) -> None:
        """Display the maintained ServerRegion value when available."""

        if snapshot is None:
            self._server_region_table.set_rows([])
            self._server_region_table.refresh()
            self._server_region_status.set_text(
                "ServerRegion is not active — no region data is available"
            )
            return

        rows: list[ContextFieldRow] = []
        for field_info in ServerRegionStruct._fields_:
            field_name = field_info[0]
            field = getattr(ServerRegionStruct, field_name)
            value = getattr(snapshot, field_name)
            rows.append(
                {
                    "offset": f"0x{field.offset:04X}",
                    "field": field_name,
                    "value": self._format_context_value(value),
                }
            )
        self._server_region_table.set_rows(rows)
        self._server_region_table.refresh()
        timing = ""
        if self._last_server_region_read_ms is not None:
            timing = f" — read {self._last_server_region_read_ms:.3f} ms"
        self._server_region_status.set_text("ServerRegion refreshed" + timing)

    def _set_server_region_filter(self, value: Any) -> None:
        """Apply the field/value filter to the ServerRegion table."""

        if self._server_region_table is None:
            return
        self._server_region_table.set_filter(str(value or ""))
        self._server_region_table.refresh()

    def _show_instance_info(self, snapshot: InstanceInfoStruct | None) -> None:
        """Display InstanceInfo fields and its maintained nested records."""

        if snapshot is None:
            self._instance_info_table.set_rows([])
            self._instance_info_table.refresh()
            self._instance_info_status.set_text(
                "InstanceInfo is not available"
            )
            return

        rows: list[ContextFieldRow] = []
        for field_name in (
            "terrain_info1",
            "current_map_info",
            "terrain_info2",
        ):
            value = getattr(snapshot, field_name)
            rows.append(
                {
                    "offset": "property",
                    "field": field_name,
                    "value": self._format_context_value(value)
                    if value is not None
                    else "(none)",
                }
            )
        for field_info in InstanceInfoStruct._fields_:
            field_name = field_info[0]
            field = getattr(InstanceInfoStruct, field_name)
            value = getattr(snapshot, field_name)
            rows.append(
                {
                    "offset": f"0x{field.offset:04X}",
                    "field": field_name,
                    "value": self._format_context_value(value),
                }
            )
        self._instance_info_table.set_rows(rows)
        self._instance_info_table.refresh()
        timing = ""
        if self._last_instance_info_read_ms is not None:
            timing = f" — read {self._last_instance_info_read_ms:.3f} ms"
        self._instance_info_status.set_text("InstanceInfo refreshed" + timing)

    def _set_instance_info_filter(self, value: Any) -> None:
        """Apply the field/value filter to the InstanceInfo table."""

        if self._instance_info_table is None:
            return
        self._instance_info_table.set_filter(str(value or ""))
        self._instance_info_table.refresh()

    def _show_text_parser(self, snapshot: TextParserStruct | None) -> None:
        """Display the TextParser's maintained raw fields.

        The source declares this record's fields, ``get_file_slot`` and ``file_hash``, and nothing
        else: the two properties this table used to show (``cache`` and ``sub_struct``) were members
        of Native's header that Reforged's Python does not declare, and ``sub_struct`` read offset
        ``+0x180`` as a pointer where this client holds ``0x4C`` -- the read that raised inside this
        window's Connect handler. The field itself is still here, as the raw word
        ``sub_struct_ptr``, which is exactly what the source's record carries.
        """

        if snapshot is None:
            self._text_parser_table.set_rows([])
            self._text_parser_table.refresh()
            self._text_parser_status.set_text(
                "TextParser is not available"
            )
            return

        rows: list[ContextFieldRow] = []
        for field_info in TextParserStruct._fields_:
            field_name = field_info[0]
            field = getattr(TextParserStruct, field_name)
            value = getattr(snapshot, field_name)
            rows.append(
                {
                    "offset": f"0x{field.offset:04X}",
                    "field": field_name,
                    "value": self._format_context_value(value),
                }
            )
        self._text_parser_table.set_rows(rows)
        self._text_parser_table.refresh()
        timing = ""
        if self._last_text_parser_read_ms is not None:
            timing = f" — read {self._last_text_parser_read_ms:.3f} ms"
        self._text_parser_status.set_text("TextParser refreshed" + timing)

    def _set_text_parser_filter(self, value: Any) -> None:
        """Apply the field/value filter to the TextParser table."""

        if self._text_parser_table is None:
            return
        self._text_parser_table.set_filter(str(value or ""))
        self._text_parser_table.refresh()

    def _show_available_characters(
        self, snapshot: AvailableCharacterArrayStruct | None
    ) -> None:
        """Display the live account-wide roster and decoded properties."""

        if snapshot is None:
            self._available_characters_table.set_rows([])
            self._available_characters_table.refresh()
            self._available_characters_status.set_text(
                "Available character roster is not available"
            )
            return

        rows: list[dict[str, Any]] = []
        for index, character in enumerate(snapshot.available_characters_list):
            rows.append(
                {
                    "index": index,
                    "name": character.player_name_str or "(unnamed)",
                    "level": character.level,
                    "map_id": character.map_id,
                    "campaign": character.campaign,
                    "primary": character.primary,
                    "secondary": character.secondary,
                    "is_pvp": character.is_pvp,
                    "uuid": self._format_context_value(character.uuid),
                }
            )
        self._available_characters_table.set_rows(rows)
        self._available_characters_table.refresh()
        timing = ""
        if self._last_available_characters_read_ms is not None:
            timing = f" — read {self._last_available_characters_read_ms:.3f} ms"
        self._available_characters_status.set_text(
            f"AvailableCharacters refreshed ({len(rows)} entries)" + timing
        )

    def _set_available_characters_filter(self, value: Any) -> None:
        """Apply the field/value filter to the account-roster table."""

        if self._available_characters_table is None:
            return
        self._available_characters_table.set_filter(str(value or ""))
        self._available_characters_table.refresh()

    def _show_party_context(self, snapshot: PartyContextStruct | None) -> None:
        """Display PartyContext flags, counts, and maintained fields."""

        if snapshot is None:
            self._party_context_table.set_rows([])
            self._party_context_table.refresh()
            self._party_context_status.set_text(
                "PartyContext is not active"
            )
            return

        parties = snapshot.parties
        player_party = snapshot.player_party
        searches = snapshot.party_searches
        rows: list[ContextFieldRow] = [
            {
                "offset": "property",
                "field": "in_hard_mode",
                "value": str(snapshot.in_hard_mode),
            },
            {
                "offset": "property",
                "field": "is_defeated",
                "value": str(snapshot.is_defeated),
            },
            {
                "offset": "property",
                "field": "is_party_leader",
                "value": str(snapshot.is_party_leader),
            },
            {
                "offset": "property",
                "field": "parties",
                "value": f"count={len(parties)}",
            },
            {
                "offset": "property",
                "field": "player_party",
                "value": (
                    f"party_id={player_party.party_id}, "
                    f"players={len(player_party.players)}, "
                    f"heroes={len(player_party.heroes)}, "
                    f"henchmen={len(player_party.henchmen)}"
                    if player_party is not None
                    else "(none)"
                ),
            },
            {
                "offset": "property",
                "field": "party_searches",
                "value": f"count={len(searches)}",
            },
        ]
        for field_info in PartyContextStruct._fields_:
            field_name = field_info[0]
            field = getattr(PartyContextStruct, field_name)
            value = getattr(snapshot, field_name)
            rows.append(
                {
                    "offset": f"0x{field.offset:04X}",
                    "field": field_name,
                    "value": self._format_context_value(value),
                }
            )
        self._party_context_table.set_rows(rows)
        self._party_context_table.refresh()
        timing = ""
        if self._last_party_context_read_ms is not None:
            timing = f" — read {self._last_party_context_read_ms:.3f} ms"
        self._party_context_status.set_text("PartyContext refreshed" + timing)

    def _set_party_context_filter(self, value: Any) -> None:
        """Apply the field/value filter to the PartyContext table."""

        if self._party_context_table is None:
            return
        self._party_context_table.set_filter(str(value or ""))
        self._party_context_table.refresh()

    def _show_guild_context(self, snapshot: GuildContextStruct | None) -> None:
        """Display GuildContext properties, nested counts, and raw fields."""

        if snapshot is None:
            self._guild_context_table.set_rows([])
            self._guild_context_table.refresh()
            self._guild_context_status.set_text("GuildContext is not active")
            return

        guilds = snapshot.guild_array or []
        roster = snapshot.player_roster or []
        history = snapshot.player_guild_history or []
        alliances = snapshot.factions_outpost_guilds or []
        rows: list[ContextFieldRow] = [
            {"offset": "property", "field": "player_name_str", "value": snapshot.player_name_str or "in selection menus"},
            {"offset": "property", "field": "announcement_str", "value": snapshot.announcement_str or ""},
            {"offset": "property", "field": "announcement_author_str", "value": snapshot.announcement_author_str or ""},
            {"offset": "property", "field": "guild_array", "value": f"count={len(guilds)}"},
            {"offset": "property", "field": "guild_names", "value": ", ".join(guild.name_str for guild in guilds[:10]) or "(none)"},
            {"offset": "property", "field": "player_roster", "value": f"count={len(roster)}"},
            {"offset": "property", "field": "roster_names", "value": ", ".join((member.name_str or member.current_name_str) for member in roster[:10]) or "(none)"},
            {"offset": "property", "field": "player_guild_history", "value": f"count={len(history)}"},
            {"offset": "property", "field": "history_names", "value": ", ".join(event.name_str for event in history[:10]) or "(none)"},
            {"offset": "property", "field": "factions_outpost_guilds", "value": f"count={len(alliances)}"},
            {"offset": "property", "field": "alliance_names", "value": ", ".join(alliance.name_str for alliance in alliances[:10]) or "(none)"},
        ]
        for field_info in GuildContextStruct._fields_:
            field_name = field_info[0]
            field = getattr(GuildContextStruct, field_name)
            value = getattr(snapshot, field_name)
            rows.append(
                {
                    "offset": f"0x{field.offset:04X}",
                    "field": field_name,
                    "value": self._format_context_value(value),
                }
            )
        self._guild_context_table.set_rows(rows)
        self._guild_context_table.refresh()
        timing = ""
        if self._last_guild_context_read_ms is not None:
            timing = f" — read {self._last_guild_context_read_ms:.3f} ms"
        self._guild_context_status.set_text(
            f"GuildContext refreshed ({len(guilds)} guilds, {len(roster)} roster entries)" + timing
        )

    def _set_guild_context_filter(self, value: Any) -> None:
        """Apply the field/value filter to the GuildContext table."""

        if self._guild_context_table is None:
            return
        self._guild_context_table.set_filter(str(value or ""))
        self._guild_context_table.refresh()

    def _show_acc_agent_context(
        self, snapshot: AccAgentContextStruct | None
    ) -> None:
        """Display useful agent counts and the maintained raw root fields."""

        if snapshot is None:
            self._acc_agent_context_table.set_rows([])
            self._acc_agent_context_table.refresh()
            self._acc_agent_context_status.set_text(
                "AccAgentContext is not active"
            )
            return

        movement_count = int(snapshot.agent_movement_array.m_size)
        summary_count = int(snapshot.agent_summary_info_array.m_size)
        valid_ids = snapshot.valid_agents_ids
        rows: list[ContextFieldRow] = [
            {"offset": "property", "field": "summary_count", "value": str(summary_count)},
            {"offset": "property", "field": "movement_count", "value": str(movement_count)},
            {"offset": "property", "field": "valid_agents_ids", "value": ", ".join(str(value) for value in valid_ids[:50]) or "(none)"},
        ]
        for field_info in AccAgentContextStruct._fields_:
            field_name = field_info[0]
            field = getattr(AccAgentContextStruct, field_name)
            value = getattr(snapshot, field_name)
            rows.append(
                {
                    "offset": f"0x{field.offset:04X}",
                    "field": field_name,
                    "value": self._format_context_value(value),
                }
            )
        self._acc_agent_context_table.set_rows(rows)
        self._acc_agent_context_table.refresh()
        timing = ""
        if self._last_acc_agent_context_read_ms is not None:
            timing = f" — read {self._last_acc_agent_context_read_ms:.3f} ms"
        self._acc_agent_context_status.set_text(
            f"AccAgentContext refreshed ({movement_count} movement entries)" + timing
        )

    def _set_acc_agent_context_filter(self, value: Any) -> None:
        """Apply the field/value filter to the AccAgentContext table."""

        if self._acc_agent_context_table is None:
            return
        self._acc_agent_context_table.set_filter(str(value or ""))
        self._acc_agent_context_table.refresh()

    def _show_pre_game_context(
        self, snapshot: PreGameContextStruct | None
    ) -> None:
        """Display the maintained PreGameContext fields and character list."""

        if snapshot is None:
            self._pre_game_context_table.set_rows([])
            self._pre_game_context_table.refresh()
            self._pre_game_context_status.set_text(
                "PreGameContext is not active — client is outside the selection menus"
            )
            return

        rows: list[ContextFieldRow] = [
            {
                "offset": "property",
                "field": "chars_list",
                "value": self._format_login_characters(snapshot),
            }
        ]
        for field_info in PreGameContextStruct._fields_:
            field_name = field_info[0]
            field = getattr(PreGameContextStruct, field_name)
            value = getattr(snapshot, field_name)
            rows.append(
                {
                    "offset": f"0x{field.offset:04X}",
                    "field": field_name,
                    "value": self._format_context_value(value),
                }
            )
        self._pre_game_context_table.set_rows(rows)
        self._pre_game_context_table.refresh()
        timing = ""
        if self._last_pre_game_context_read_ms is not None:
            timing = f" — read {self._last_pre_game_context_read_ms:.3f} ms"
        self._pre_game_context_status.set_text(
            "PreGameContext refreshed" + timing
        )

    def _format_login_characters(self, snapshot: PreGameContextStruct) -> str:
        """Format the live character records exposed by the pre-game array."""

        characters = snapshot.chars_list
        if not characters:
            return "count=0"
        names = [character.character_name_str or "(unnamed)" for character in characters]
        return f"count={len(names)}: " + ", ".join(names)

    def _set_pre_game_context_filter(self, value: Any) -> None:
        """Apply the field/value filter to the PreGameContext table."""

        if self._pre_game_context_table is None:
            return
        self._pre_game_context_table.set_filter(str(value or ""))
        self._pre_game_context_table.refresh()

    def _show_game_context(self, snapshot: GameContextStruct) -> None:
        """Display every maintained GameContext field in the table."""

        rows: list[ContextFieldRow] = []
        for field_info in GameContextStruct._fields_:
            field_name = field_info[0]
            field = getattr(GameContextStruct, field_name)
            value = getattr(snapshot, field_name)
            rows.append(
                {
                    "offset": f"0x{field.offset:04X}",
                    "field": field_name,
                    "value": self._format_context_value(value),
                }
            )
        self._game_context_table.set_rows(rows)
        self._game_context_table.refresh()
        timing = ""
        if self._last_game_context_read_ms is not None:
            timing = f" — read {self._last_game_context_read_ms:.3f} ms"
        self._game_context_status.set_text("GameContext refreshed" + timing)

    def _set_game_context_filter(self, value: Any) -> None:
        """Apply the field/value filter to the GameContext table."""

        if self._game_context_table is None:
            return
        self._game_context_table.set_filter(str(value or ""))
        self._game_context_table.refresh()

    def _set_context_filter(self, value: Any) -> None:
        """Apply the field/value filter to the context table."""

        if self._context_table is None:
            return
        self._context_table.set_filter(str(value or ""))
        self._context_table.refresh()

    def _show_context(self, snapshot: CharContextStruct | None) -> None:
        """Display every maintained CharContext field in the table.

        ``None`` means the readiness gate is closed. The character context is
        map-scoped, so it is not readable until a map is ready; the table says so
        rather than continuing to show the previous map's rows.
        """

        if snapshot is None:
            self._context_table.set_rows([])
            self._context_table.refresh()
            self._context_status.set_text(
                "CharContext is not available: no ready map"
            )
            return

        property_values = {
            "is_logged_in": snapshot.is_logged_in,
            "player_uuid": snapshot.player_uuid,
            "player_name_encoded_str": snapshot.player_name_encoded_str,
            "player_name_str": snapshot.player_name_str or "in selection menus",
            "player_email_encoded_str": snapshot.player_email_encoded_str,
            "player_email_str": snapshot.player_email_str,
            "h0000_ptrs": snapshot.h0000_ptrs,
            "h0014_ptrs": snapshot.h0014_ptrs,
            "h0034_ptrs": snapshot.h0034_ptrs,
            "h0044_ptrs": snapshot.h0044_ptrs,
            "h00EC_ptrs": snapshot.h00EC_ptrs,
            "observer_matches": snapshot.observer_matches,
            "progress_bar": snapshot.progress_bar,
        }
        rows: list[ContextFieldRow] = [
            {
                "offset": "property",
                "field": field_name,
                "value": self._format_property_value(field_name, value),
            }
            for field_name, value in property_values.items()
        ]
        for field_info in CharContextStruct._fields_:
            field_name = field_info[0]
            field = getattr(CharContextStruct, field_name)
            value = getattr(snapshot, field_name)
            rows.append(
                {
                    "offset": f"0x{field.offset:04X}",
                    "field": field_name,
                    "value": self._format_context_field(snapshot, field_name, value),
                }
            )
        self._context_table.set_rows(rows)
        self._context_table.refresh()
        timing = ""
        if self._last_context_read_ms is not None:
            timing = f" — read {self._last_context_read_ms:.3f} ms"
        self._context_status.set_text(
            "CharContext refreshed — "
            f"{'logged in' if snapshot.is_logged_in else 'in selection menus'}"
            + timing
        )

    def _format_property_value(self, field_name: str, value: Any) -> str:
        """Format the user-facing properties exposed by CharContextStruct."""

        if value is None:
            return "(none)"
        if field_name == "progress_bar":
            if not isinstance(value, ctypes.Structure):
                return str(value)
            pips = getattr(value, "pips", 0)
            progress = getattr(value, "progress", 0.0)
            return f"pips={pips}, progress={progress:.3f}"
        if field_name == "observer_matches":
            if not isinstance(value, list):
                return str(value)
            matches = []
            for match in value[:10]:
                matches.append(
                    "{" + ", ".join(
                        [
                            f"match_id={getattr(match, 'match_id', 0)}",
                            f"map_id={getattr(match, 'map_id', 0)}",
                            f"team1={match.team_name1_str or '(none)'}",
                            f"team2={match.team_name2_str or '(none)'}",
                        ]
                    ) + "}"
                )
            suffix = " ..." if len(value) > len(matches) else ""
            return f"count={len(value)}: " + ", ".join(matches) + suffix
        if isinstance(value, (list, tuple)):
            formatted_values = [self._format_context_value(item) for item in value]
            if field_name.endswith("_ptrs"):
                sample = formatted_values[:8]
                suffix = " ..." if len(formatted_values) > len(sample) else ""
                return f"count={len(value)}, sample=[" + ", ".join(sample) + "]" + suffix
            if len(formatted_values) > 32:
                formatted_values = formatted_values[:16] + ["..."] + formatted_values[-4:]
            return (
                f"count={len(value)}: ["
                + ", ".join(formatted_values)
                + "]"
            )
        return self._format_context_value(value)

    def _format_context_field(
        self, snapshot: CharContextStruct, field_name: str, value: Any
    ) -> str:
        """Format one field using its maintained context meaning."""

        if field_name == "player_name_enc":
            return snapshot.player_name_str or "(empty)"
        if field_name == "player_email_ptr":
            return snapshot.player_email_str or "(empty)"
        if field_name == "player_uuid_ptr":
            return "-".join(f"{part:08X}" for part in snapshot.player_uuid)
        if isinstance(value, GWArray):
            return self._format_gw_array(snapshot, field_name, value)
        return self._format_context_value(value)

    def _format_gw_array(
        self, snapshot: CharContextStruct, field_name: str, array: GWArray
    ) -> str:
        """Format an array through its header and maintained view behavior."""

        is_valid = bool(array.m_buffer) and array.m_size <= array.m_capacity
        item_count = 0
        if is_valid:
            view_names = {
                "h0000_array": "h0000_ptrs",
                "h0014_array": "h0014_ptrs",
                "h0034_array": "h0034_ptrs",
                "h0044_array": "h0044_ptrs",
                "h00EC_array": "h00EC_ptrs",
            }
            if field_name in view_names:
                values = getattr(snapshot, view_names[field_name])
                item_count = len(values or [])
            elif field_name == "observer_matches_array":
                item_count = len(snapshot.observer_matches or [])
        return (
            f"valid={is_valid}, size={int(array.m_size)}, "
            f"capacity={int(array.m_capacity)}, items={item_count}"
        )

    @staticmethod
    def _format_pointer(value: int | None) -> str:
        """Format an optional target-process pointer without implying validity."""

        return f"0x{value:08X}" if value else "(null)"

    def _format_context_value(self, value: Any) -> str:
        """Format remaining ctypes values without local pointer dereferences."""

        if isinstance(value, ctypes.Array):
            values = list(value)
            return "[" + ", ".join(
                self._format_context_value(item) for item in values
            ) + "]"
        if isinstance(value, ctypes.Structure):
            parts = []
            for field_info in type(value)._fields_:
                field_name = field_info[0]
                field_value = getattr(value, field_name)
                parts.append(
                    f"{field_name}={self._format_context_value(field_value)}"
                )
            return "{" + ", ".join(parts) + "}"
        if hasattr(value, "value"):
            scalar = value.value
            if isinstance(scalar, int) and scalar > 0xFFFF:
                return f"{scalar} (0x{scalar:08X})"
            return str(scalar)
        if isinstance(value, int) and value > 0xFFFF:
            return f"{value} (0x{value:08X})"
        return str(value)


def build_argument_parser() -> argparse.ArgumentParser:
    """The command line: the same surface as the window, without the window."""

    parser = argparse.ArgumentParser(
        prog="main.py",
        description=(
            "The Py4GW Stealth window. With no arguments it opens the window; the options below run "
            "the same checks and write the same reports headlessly."
        ),
    )
    parser.add_argument("--self-test", action="store_true", help="run the battery and print it")
    parser.add_argument(
        "--client",
        action="store_true",
        help=(
            "include the checks that read a running client -- they connect, which is a write to the "
            "client, so this needs an elevated shell and a running Guild Wars"
        ),
    )
    parser.add_argument("--pid", type=int, default=None, help="the client to connect to (default: the first found)")
    parser.add_argument(
        "--data",
        nargs="?",
        const=str(LIVE_DATA_REPORT_PATH),
        default=None,
        metavar="PATH",
        help="write every live value to PATH (text; the JSON goes beside it)",
    )
    parser.add_argument("--areas", default=None, help="a comma-separated list of check areas to run")
    parser.add_argument("--report", nargs="?", const=str(SELF_TEST_REPORT_PATH), default=None, metavar="PATH", help="write the battery's report to PATH")
    parser.add_argument("--json", action="store_true", help="print the result as JSON")
    parser.add_argument("--quiet", action="store_true", help="print nothing but the report paths")
    parser.add_argument(
        "--elevate",
        action="store_true",
        help="relaunch this command elevated (one UAC prompt) and let that run do the work",
    )
    return parser


def relaunch_elevated(argv: Sequence[str]) -> int:
    """Start the same command in an elevated console, and say where its reports will be.

    A process cannot raise its own token, so this is a second process: the caller here stays
    unelevated and holds no rights over the client. The UAC prompt is the user's to approve, which is
    why this is a flag and never something the window does by itself.
    """

    child = [argument for argument in argv if argument != "--elevate"]
    if "--report" not in child:
        child += ["--report", str(SELF_TEST_REPORT_PATH)]
    command = " ".join(f'"{argument}"' if " " in argument else argument for argument in child)
    result = ctypes.windll.shell32.ShellExecuteW(  # type: ignore[attr-defined]
        None, "runas", sys.executable, command, str(Path.cwd()), 1
    )
    if int(result) <= 32:
        print(f"the elevated run was not started (ShellExecute returned {int(result)})")
        return 2
    print(f"started an elevated run: python {command}")
    print(f"its report goes to {SELF_TEST_REPORT_PATH}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Open the window, or run the same surface headlessly."""

    arguments = list(sys.argv[1:] if argv is None else argv)
    parser = build_argument_parser()
    options = parser.parse_args(arguments)

    if not (options.self_test or options.data):
        if options.elevate:
            return relaunch_elevated(arguments)
        MainWindow().run()
        return 0

    if options.elevate:
        return relaunch_elevated(arguments)

    import self_test

    window = MainWindow()
    needs_client = bool(options.client or options.data)
    if needs_client:
        try:
            connection = window.connect(options.pid)
            if not options.quiet:
                print(f"connected to {connection!r}")
        except PermissionError as error:
            print(f"refused: {error}")
            return 2
        except OSError as error:
            print(f"could not connect: {error}")
            return 3

    areas: Sequence[str] | None = None
    if options.areas:
        areas = tuple(part.strip() for part in options.areas.split(",") if part.strip())
    elif not needs_client:
        areas = tuple(
            area
            for area in self_test.areas()
            if area not in ("client",) and area not in self_test.live_areas()
        )

    results = window.run_self_test(areas=areas)
    summary = self_test.summarise(results)
    if not options.quiet:
        print(summary if not options.json else json.dumps(
            [
                {
                    "area": result.area,
                    "name": result.name,
                    "status": result.status,
                    "expected": result.expected,
                    "saw": result.actual,
                    "ms": round(result.milliseconds, 3),
                }
                for result in results
            ],
            indent=2,
        ))

    if options.data:
        text_path, json_path = window.dump_live_data(options.data)
        print(f"live data written to {text_path} and {json_path}")
    if options.report:
        print(f"report written to {self_test.write_report(results, options.report)}")

    failed = sum(1 for result in results if result.status == "fail")
    return 1 if failed else 0


if __name__ == "__main__":
    if len(sys.argv) > 1:
        raise SystemExit(main())
    MainWindow().run()
