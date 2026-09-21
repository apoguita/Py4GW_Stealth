"""Main Py4GW Stealth window.

Run from the project directory with::

    python main.py

The window lists running Guild Wars clients, reads their current character
identity when available, and lets the user connect to one selected PID.
"""

from __future__ import annotations

import ctypes
from typing import Any, TypedDict

from nicegui import ui

from py4gw import (
    CharContextStruct,
    ConnectedClient,
    CinematicStruct,
    GameContextStruct,
    GameplayContextStruct,
    PreGameContextStruct,
    GWArray,
    PerfCounter,
    Win32,
)


class ClientRow(TypedDict):
    """One Guild Wars client displayed by the selection table."""

    pid: int
    name: str
    character: str
    status: str
    path: str


class ContextFieldRow(TypedDict):
    """One field displayed in the live context inspector."""

    offset: str
    field: str
    value: str


class MainWindow:
    """Build and run the Guild Wars client-selection window."""

    def __init__(self) -> None:
        """Create the client list and its controls."""

        self._win32 = Win32()
        self._perf = PerfCounter()
        self._last_game_context_read_ms: float | None = None
        self._last_pre_game_context_read_ms: float | None = None
        self._last_cinematic_read_ms: float | None = None
        self._last_gameplay_context_read_ms: float | None = None
        self._last_context_read_ms: float | None = None
        self._connection: ConnectedClient | None = None
        self._clients: list[dict[str, Any]] = []
        self._status: Any = None
        self._client_select: Any = None
        self._client_table: Any = None
        self._connected_label: Any = None
        self._data_tab: Any = None
        self._context_status: Any = None
        self._context_table: Any = None
        self._context_filter: Any = None
        self._game_context_status: Any = None
        self._game_context_table: Any = None
        self._game_context_filter: Any = None
        self._pre_game_context_status: Any = None
        self._pre_game_context_table: Any = None
        self._pre_game_context_filter: Any = None
        self._cinematic_status: Any = None
        self._cinematic_table: Any = None
        self._cinematic_filter: Any = None
        self._gameplay_context_status: Any = None
        self._gameplay_context_table: Any = None
        self._gameplay_context_filter: Any = None
        self._build_interface()

    def run(self) -> None:
        """Start the NiceGUI window in native desktop mode."""

        ui.run(
            native=True,
            reload=False,
            title="Py4GW Stealth",
            window_size=(1400, 900),
        )

    def _build_interface(self) -> None:
        """Create the client-selection tab."""

        with ui.tabs().classes("w-full") as tabs:
            client_tab = ui.tab("Guild Wars clients")
            self._data_tab = ui.tab("Client data")
            self._data_tab.disable()

        with ui.tab_panels(tabs, value=client_tab).classes("w-full h-full"):
            with ui.tab_panel(client_tab).classes("w-full h-full"):
                self._build_client_tab()
            with ui.tab_panel(self._data_tab).classes("w-full h-full"):
                self._build_data_tab()

    def _build_client_tab(self) -> None:
        """Create refresh, selection, and connection controls."""

        ui.label("Guild Wars clients").classes("text-h6")
        ui.label(
            "Refresh to find running clients. A character name means the client "
            "is logged in; otherwise it is in the selection menus."
        )

        with ui.row().classes("w-full items-center"):
            ui.button("Refresh", on_click=self._refresh_clients)
            self._client_select = ui.select(
                options={}, label="Client PID", with_input=True
            ).classes("min-w-64")
            ui.button("Connect selected", on_click=self._connect_selected)

        self._status = ui.label("No client scan performed")
        self._connected_label = ui.label("No client connected")
        self._client_table = ui.table(
            columns=[
                {
                    "name": "pid",
                    "label": "PID",
                    "field": "pid",
                    "sortable": True,
                },
                {
                    "name": "name",
                    "label": "Name",
                    "field": "name",
                    "sortable": True,
                },
                {
                    "name": "character",
                    "label": "Character",
                    "field": "character",
                    "sortable": True,
                },
                {
                    "name": "status",
                    "label": "Status",
                    "field": "status",
                    "sortable": True,
                },
                {
                    "name": "path",
                    "label": "Path",
                    "field": "path",
                    "sortable": True,
                },
            ],
            rows=[],
            row_key="pid",
            selection="single",
            pagination={
                "rowsPerPage": 10,
                "rowsPerPageOptions": [10, 25, 0],
                "sortBy": "pid",
                "descending": False,
            },
        ).props("bordered flat separator=cell")
        self._client_table.classes("w-full h-full")

        self._refresh_clients()

    def _build_data_tab(self) -> None:
        """Create context subtabs for the currently selected client."""

        ui.label("Connected client data").classes("text-h6")
        ui.label(
            "These values are read-only snapshots. The maintained properties "
            "appear first; raw layout fields follow."
        )

        with ui.tabs().classes("w-full") as context_tabs:
            cinematic_tab = ui.tab("Cinematic")
            gameplay_context_tab = ui.tab("GameplayContext")
            pre_game_context_tab = ui.tab("PreGameContext")
            game_context_tab = ui.tab("GameContext")
            char_context_tab = ui.tab("CharContext")

        with ui.tab_panels(context_tabs, value=char_context_tab).classes("w-full h-full"):
            with ui.tab_panel(cinematic_tab).classes("w-full h-full"):
                with ui.row().classes("w-full items-center"):
                    ui.button("Refresh Cinematic", on_click=self._refresh_cinematic)
                    self._cinematic_filter = ui.input("Filter fields or values")
                    self._cinematic_filter.on(
                        "update:model-value",
                        lambda event: self._set_cinematic_filter(event.args),
                    )
                    self._cinematic_status = ui.label("Connect a client first")
                self._cinematic_table = ui.table(
                    columns=[
                        {
                            "name": "offset",
                            "label": "Offset",
                            "field": "offset",
                            "sortable": True,
                        },
                        {
                            "name": "field",
                            "label": "Field",
                            "field": "field",
                            "sortable": True,
                        },
                        {
                            "name": "value",
                            "label": "Value",
                            "field": "value",
                            "sortable": True,
                        },
                    ],
                    rows=[],
                    row_key="field",
                    selection="single",
                    pagination={
                        "rowsPerPage": 10,
                        "rowsPerPageOptions": [10, 20, 0],
                    },
                ).props("bordered flat wrap-cells separator=cell")
                self._cinematic_table.classes("w-full h-full")
            with ui.tab_panel(gameplay_context_tab).classes("w-full h-full"):
                with ui.row().classes("w-full items-center"):
                    ui.button(
                        "Refresh GameplayContext",
                        on_click=self._refresh_gameplay_context,
                    )
                    self._gameplay_context_filter = ui.input(
                        "Filter fields or values"
                    )
                    self._gameplay_context_filter.on(
                        "update:model-value",
                        lambda event: self._set_gameplay_context_filter(event.args),
                    )
                    self._gameplay_context_status = ui.label(
                        "Connect a client first"
                    )
                self._gameplay_context_table = ui.table(
                    columns=[
                        {
                            "name": "offset",
                            "label": "Offset",
                            "field": "offset",
                            "sortable": True,
                        },
                        {
                            "name": "field",
                            "label": "Field",
                            "field": "field",
                            "sortable": True,
                        },
                        {
                            "name": "value",
                            "label": "Value",
                            "field": "value",
                            "sortable": True,
                        },
                    ],
                    rows=[],
                    row_key="field",
                    selection="single",
                    pagination={
                        "rowsPerPage": 10,
                        "rowsPerPageOptions": [10, 20, 0],
                    },
                ).props("bordered flat wrap-cells separator=cell")
                self._gameplay_context_table.classes("w-full h-full")
            with ui.tab_panel(pre_game_context_tab).classes("w-full h-full"):
                with ui.row().classes("w-full items-center"):
                    ui.button(
                        "Refresh PreGameContext",
                        on_click=self._refresh_pre_game_context,
                    )
                    self._pre_game_context_filter = ui.input(
                        "Filter fields or values"
                    )
                    self._pre_game_context_filter.on(
                        "update:model-value",
                        lambda event: self._set_pre_game_context_filter(event.args),
                    )
                    self._pre_game_context_status = ui.label(
                        "Connect a client first"
                    )
                self._pre_game_context_table = ui.table(
                    columns=[
                        {
                            "name": "offset",
                            "label": "Offset",
                            "field": "offset",
                            "sortable": True,
                        },
                        {
                            "name": "field",
                            "label": "Field",
                            "field": "field",
                            "sortable": True,
                        },
                        {
                            "name": "value",
                            "label": "Value",
                            "field": "value",
                            "sortable": True,
                        },
                    ],
                    rows=[],
                    row_key="field",
                    selection="single",
                    pagination={
                        "rowsPerPage": 10,
                        "rowsPerPageOptions": [10, 20, 0],
                    },
                ).props("bordered flat wrap-cells separator=cell")
                self._pre_game_context_table.classes("w-full h-full")
            with ui.tab_panel(game_context_tab).classes("w-full h-full"):
                with ui.row().classes("w-full items-center"):
                    ui.button("Refresh GameContext", on_click=self._refresh_game_context)
                    self._game_context_filter = ui.input("Filter fields or values")
                    self._game_context_filter.on(
                        "update:model-value",
                        lambda event: self._set_game_context_filter(event.args),
                    )
                    self._game_context_status = ui.label("Connect a client first")
                self._game_context_table = ui.table(
                    columns=[
                        {
                            "name": "offset",
                            "label": "Offset",
                            "field": "offset",
                            "sortable": True,
                        },
                        {
                            "name": "field",
                            "label": "Field",
                            "field": "field",
                            "sortable": True,
                        },
                        {
                            "name": "value",
                            "label": "Value",
                            "field": "value",
                            "sortable": True,
                        },
                    ],
                    rows=[],
                    row_key="field",
                    selection="single",
                    pagination={
                        "rowsPerPage": 10,
                        "rowsPerPageOptions": [10, 20, 0],
                    },
                ).props("bordered flat wrap-cells separator=cell")
                self._game_context_table.classes("w-full h-full")
            with ui.tab_panel(char_context_tab).classes("w-full h-full"):
                with ui.row().classes("w-full items-center"):
                    ui.button("Refresh CharContext", on_click=self._refresh_context)
                    self._context_filter = ui.input("Filter fields or values")
                    self._context_filter.on(
                        "update:model-value",
                        lambda event: self._set_context_filter(event.args),
                    )
                    self._context_status = ui.label("Connect a client first")
                self._context_table = ui.table(
                    columns=[
                        {
                            "name": "offset",
                            "label": "Offset",
                            "field": "offset",
                            "sortable": True,
                        },
                        {
                            "name": "field",
                            "label": "Field",
                            "field": "field",
                            "sortable": True,
                        },
                        {
                            "name": "value",
                            "label": "Value",
                            "field": "value",
                            "sortable": True,
                        },
                    ],
                    rows=[],
                    row_key="field",
                    selection="single",
                    pagination={
                        "rowsPerPage": 10,
                        "rowsPerPageOptions": [10, 20, 0],
                    },
                ).props("bordered flat wrap-cells separator=cell")
                self._context_table.classes("w-full h-full")

    def _refresh_clients(self) -> None:
        """Discover Guild Wars clients and read their live identity."""

        try:
            self._clients = self._win32.find_guild_wars()
            rows = [self._inspect_client(process) for process in self._clients]
        except OSError as error:
            self._show_error(error)
            return

        options = {
            str(row["pid"]): f"{row['pid']} — {row['character']}"
            for row in rows
        }
        self._client_select.options = options
        self._client_select.update()
        self._show_rows(rows, f"Found {len(rows)} Guild Wars client(s)")

        selected_pid = self._client_select.value
        if selected_pid is not None and str(selected_pid) not in options:
            self._client_select.value = None
            self._client_select.update()
            self._disconnect_current()

    def _inspect_client(self, process: dict[str, Any]) -> ClientRow:
        """Read one client's character name without keeping its handle open."""

        character = None
        is_connected = False
        try:
            connection = ConnectedClient(process, self._win32)
            try:
                snapshot = self._read_context_timed(connection)
                character = snapshot.player_name_str.strip() or None
                is_connected = snapshot.is_logged_in
            finally:
                connection.close()
        except (OSError, RuntimeError, ValueError):
            character = None

        return {
            "pid": int(process["pid"]),
            "name": str(process["name"]),
            "character": character or "in selection menus",
            "status": "connected" if is_connected else "in selection menus",
            "path": str(process.get("path") or "—"),
        }

    def _connect_selected(self) -> None:
        """Connect to the PID currently selected in the dropdown."""

        selected = self._client_select.value
        if selected is None:
            self._connected_label.set_text("Select a client PID first")
            return

        pid = int(selected)
        process = next(
            (candidate for candidate in self._clients if int(candidate["pid"]) == pid),
            None,
        )
        if process is None:
            self._connected_label.set_text("Refresh the client list first")
            return

        self._disconnect_current()
        try:
            self._connection = ConnectedClient(process, self._win32)
            cinematic_snapshot = self._read_cinematic_timed(self._connection)
            gameplay_snapshot = self._read_gameplay_context_timed(self._connection)
            pre_game_snapshot = self._read_pre_game_context_timed(self._connection)
            game_snapshot = self._read_game_context_timed(self._connection)
            snapshot = self._read_context_timed(self._connection)
            character = snapshot.player_name_str.strip() or None
            is_logged_in = snapshot.is_logged_in
        except (OSError, RuntimeError, ValueError) as error:
            self._connection = None
            self._connected_label.set_text(f"Connection failed: {error}")
            return

        description = character if is_logged_in else "in selection menus"
        self._connected_label.set_text(
            f"Connected to PID {pid} — {description}"
        )
        self._data_tab.enable()
        self._data_tab.update()
        self._show_pre_game_context(pre_game_snapshot)
        self._show_cinematic(cinematic_snapshot)
        self._show_gameplay_context(gameplay_snapshot)
        self._show_game_context(game_snapshot)
        self._show_context(snapshot)

    def _disconnect_current(self) -> None:
        """Close the currently selected client connection, if any."""

        if self._connection is not None:
            self._connection.close()
            self._connection = None
        if self._data_tab is not None:
            self._data_tab.disable()
            self._data_tab.update()
        if self._context_table is not None:
            self._context_table.rows = []
            self._context_table.update()
        if self._game_context_table is not None:
            self._game_context_table.rows = []
            self._game_context_table.update()
        if self._pre_game_context_table is not None:
            self._pre_game_context_table.rows = []
            self._pre_game_context_table.update()
        if self._cinematic_table is not None:
            self._cinematic_table.rows = []
            self._cinematic_table.update()
        if self._gameplay_context_table is not None:
            self._gameplay_context_table.rows = []
            self._gameplay_context_table.update()
        if self._game_context_filter is not None:
            self._game_context_filter.value = ""
            self._game_context_filter.update()
        if self._pre_game_context_filter is not None:
            self._pre_game_context_filter.value = ""
            self._pre_game_context_filter.update()
        if self._context_filter is not None:
            self._context_filter.value = ""
            self._context_filter.update()
        if self._cinematic_filter is not None:
            self._cinematic_filter.value = ""
            self._cinematic_filter.update()
        if self._gameplay_context_filter is not None:
            self._gameplay_context_filter.value = ""
            self._gameplay_context_filter.update()
        if self._context_status is not None:
            self._context_status.set_text("Connect a client first")
        if self._game_context_status is not None:
            self._game_context_status.set_text("Connect a client first")
        if self._pre_game_context_status is not None:
            self._pre_game_context_status.set_text("Connect a client first")
        if self._cinematic_status is not None:
            self._cinematic_status.set_text("Connect a client first")
        if self._gameplay_context_status is not None:
            self._gameplay_context_status.set_text("Connect a client first")

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

    def _read_context_timed(self, connection: ConnectedClient) -> CharContextStruct:
        """Read one CharContext snapshot and retain its elapsed time."""

        metric_name = "CharContext.read"
        self._perf.start(metric_name)
        try:
            return connection.read_char_context()
        finally:
            self._last_context_read_ms = self._perf.end(metric_name)

    def _read_game_context_timed(
        self, connection: ConnectedClient
    ) -> GameContextStruct:
        """Read one GameContext snapshot and retain its elapsed time."""

        metric_name = "GameContext.read"
        self._perf.start(metric_name)
        try:
            return connection.read_game_context()
        finally:
            self._last_game_context_read_ms = self._perf.end(metric_name)

    def _read_pre_game_context_timed(
        self, connection: ConnectedClient
    ) -> PreGameContextStruct | None:
        """Read one PreGameContext snapshot and retain its elapsed time."""

        metric_name = "PreGameContext.read"
        self._perf.start(metric_name)
        try:
            return connection.read_pre_game_context()
        finally:
            self._last_pre_game_context_read_ms = self._perf.end(metric_name)

    def _read_cinematic_timed(
        self, connection: ConnectedClient
    ) -> CinematicStruct | None:
        """Read one Cinematic snapshot and retain its elapsed time."""

        metric_name = "Cinematic.read"
        self._perf.start(metric_name)
        try:
            return connection.read_cinematic_context()
        finally:
            self._last_cinematic_read_ms = self._perf.end(metric_name)

    def _read_gameplay_context_timed(
        self, connection: ConnectedClient
    ) -> GameplayContextStruct | None:
        """Read one GameplayContext snapshot and retain its elapsed time."""

        metric_name = "GameplayContext.read"
        self._perf.start(metric_name)
        try:
            return connection.read_gameplay_context()
        finally:
            self._last_gameplay_context_read_ms = self._perf.end(metric_name)

    def _show_cinematic(self, snapshot: CinematicStruct | None) -> None:
        """Display the maintained Cinematic fields when the context is active."""

        if snapshot is None:
            self._cinematic_table.rows = []
            self._cinematic_table.update()
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
        self._cinematic_table.rows = rows
        self._cinematic_table.update()
        timing = ""
        if self._last_cinematic_read_ms is not None:
            timing = f" — read {self._last_cinematic_read_ms:.3f} ms"
        self._cinematic_status.set_text("Cinematic refreshed" + timing)

    def _set_cinematic_filter(self, value: Any) -> None:
        """Apply the field/value filter to the Cinematic table."""

        if self._cinematic_table is None:
            return
        self._cinematic_table.filter = str(value or "")
        self._cinematic_table.update()

    def _show_gameplay_context(
        self, snapshot: GameplayContextStruct | None
    ) -> None:
        """Display the maintained GameplayContext fields when active."""

        if snapshot is None:
            self._gameplay_context_table.rows = []
            self._gameplay_context_table.update()
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
        self._gameplay_context_table.rows = rows
        self._gameplay_context_table.update()
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
        self._gameplay_context_table.filter = str(value or "")
        self._gameplay_context_table.update()

    def _show_pre_game_context(
        self, snapshot: PreGameContextStruct | None
    ) -> None:
        """Display the maintained PreGameContext fields and character list."""

        if snapshot is None:
            self._pre_game_context_table.rows = []
            self._pre_game_context_table.update()
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
        self._pre_game_context_table.rows = rows
        self._pre_game_context_table.update()
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
        self._pre_game_context_table.filter = str(value or "")
        self._pre_game_context_table.update()

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
        self._game_context_table.rows = rows
        self._game_context_table.update()
        timing = ""
        if self._last_game_context_read_ms is not None:
            timing = f" — read {self._last_game_context_read_ms:.3f} ms"
        self._game_context_status.set_text("GameContext refreshed" + timing)

    def _set_game_context_filter(self, value: Any) -> None:
        """Apply the field/value filter to the GameContext table."""

        if self._game_context_table is None:
            return
        self._game_context_table.filter = str(value or "")
        self._game_context_table.update()

    def _set_context_filter(self, value: Any) -> None:
        """Apply the field/value filter to the context table."""

        if self._context_table is None:
            return
        self._context_table.filter = str(value or "")
        self._context_table.update()

    def _show_context(self, snapshot: CharContextStruct) -> None:
        """Display every maintained CharContext field in the table."""

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
        self._context_table.rows = rows
        self._context_table.update()
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

    def _show_rows(self, rows: list[ClientRow], message: str) -> None:
        """Replace the table contents and update its status text."""

        self._client_table.rows = rows
        self._client_table.update()
        self._status.set_text(message)

    def _show_error(self, error: OSError) -> None:
        """Display a Win32 failure without hiding its diagnostic message."""

        self._client_table.rows = []
        self._client_table.update()
        self._status.set_text(f"Win32 error: {error}")


if __name__ == "__main__":
    MainWindow().run()
