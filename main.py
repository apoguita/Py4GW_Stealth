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
    AvailableCharacterArrayStruct,
    PartyContextStruct,
    GuildContextStruct,
    AccAgentContextStruct,
    CharContextStruct,
    ConnectedClient,
    CinematicStruct,
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
        self._server_region_status: Any = None
        self._server_region_table: Any = None
        self._server_region_filter: Any = None
        self._instance_info_status: Any = None
        self._instance_info_table: Any = None
        self._instance_info_filter: Any = None
        self._text_parser_status: Any = None
        self._text_parser_table: Any = None
        self._text_parser_filter: Any = None
        self._available_characters_status: Any = None
        self._available_characters_table: Any = None
        self._available_characters_filter: Any = None
        self._party_context_status: Any = None
        self._party_context_table: Any = None
        self._party_context_filter: Any = None
        self._guild_context_status: Any = None
        self._guild_context_table: Any = None
        self._guild_context_filter: Any = None
        self._acc_agent_context_status: Any = None
        self._acc_agent_context_table: Any = None
        self._acc_agent_context_filter: Any = None
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
            server_region_tab = ui.tab("ServerRegion")
            instance_info_tab = ui.tab("InstanceInfo")
            text_parser_tab = ui.tab("TextParser")
            available_characters_tab = ui.tab("AvailableCharacters")
            party_context_tab = ui.tab("PartyContext")
            guild_context_tab = ui.tab("GuildContext")
            acc_agent_context_tab = ui.tab("AccAgentContext")
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
            with ui.tab_panel(server_region_tab).classes("w-full h-full"):
                with ui.row().classes("w-full items-center"):
                    ui.button(
                        "Refresh ServerRegion",
                        on_click=self._refresh_server_region,
                    )
                    self._server_region_filter = ui.input(
                        "Filter fields or values"
                    )
                    self._server_region_filter.on(
                        "update:model-value",
                        lambda event: self._set_server_region_filter(event.args),
                    )
                    self._server_region_status = ui.label(
                        "Connect a client first"
                    )
                self._server_region_table = ui.table(
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
                self._server_region_table.classes("w-full h-full")
            with ui.tab_panel(instance_info_tab).classes("w-full h-full"):
                with ui.row().classes("w-full items-center"):
                    ui.button(
                        "Refresh InstanceInfo",
                        on_click=self._refresh_instance_info,
                    )
                    self._instance_info_filter = ui.input(
                        "Filter fields or values"
                    )
                    self._instance_info_filter.on(
                        "update:model-value",
                        lambda event: self._set_instance_info_filter(event.args),
                    )
                    self._instance_info_status = ui.label(
                        "Connect a client first"
                    )
                self._instance_info_table = ui.table(
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
                self._instance_info_table.classes("w-full h-full")
            with ui.tab_panel(text_parser_tab).classes("w-full h-full"):
                with ui.row().classes("w-full items-center"):
                    ui.button(
                        "Refresh TextParser",
                        on_click=self._refresh_text_parser,
                    )
                    self._text_parser_filter = ui.input("Filter fields or values")
                    self._text_parser_filter.on(
                        "update:model-value",
                        lambda event: self._set_text_parser_filter(event.args),
                    )
                    self._text_parser_status = ui.label(
                        "Connect a client first"
                    )
                self._text_parser_table = ui.table(
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
                self._text_parser_table.classes("w-full h-full")
            with ui.tab_panel(available_characters_tab).classes("w-full h-full"):
                with ui.row().classes("w-full items-center"):
                    ui.button(
                        "Refresh AvailableCharacters",
                        on_click=self._refresh_available_characters,
                    )
                    self._available_characters_filter = ui.input(
                        "Filter fields or values"
                    )
                    self._available_characters_filter.on(
                        "update:model-value",
                        lambda event: self._set_available_characters_filter(
                            event.args
                        ),
                    )
                    self._available_characters_status = ui.label(
                        "Connect a client first"
                    )
                self._available_characters_table = ui.table(
                    columns=[
                        {
                            "name": "index",
                            "label": "#",
                            "field": "index",
                            "sortable": True,
                        },
                        {
                            "name": "name",
                            "label": "Name",
                            "field": "name",
                            "sortable": True,
                        },
                        {
                            "name": "level",
                            "label": "Level",
                            "field": "level",
                            "sortable": True,
                        },
                        {
                            "name": "map_id",
                            "label": "Map",
                            "field": "map_id",
                            "sortable": True,
                        },
                        {
                            "name": "campaign",
                            "label": "Campaign",
                            "field": "campaign",
                            "sortable": True,
                        },
                        {
                            "name": "primary",
                            "label": "Primary",
                            "field": "primary",
                            "sortable": True,
                        },
                        {
                            "name": "secondary",
                            "label": "Secondary",
                            "field": "secondary",
                            "sortable": True,
                        },
                        {
                            "name": "is_pvp",
                            "label": "PvP",
                            "field": "is_pvp",
                            "sortable": True,
                        },
                        {
                            "name": "uuid",
                            "label": "UUID",
                            "field": "uuid",
                            "sortable": True,
                        },
                    ],
                    rows=[],
                    row_key="index",
                    selection="single",
                    pagination={
                        "rowsPerPage": 10,
                        "rowsPerPageOptions": [10, 20, 0],
                    },
                ).props("bordered flat wrap-cells separator=cell")
                self._available_characters_table.classes("w-full h-full")
            with ui.tab_panel(party_context_tab).classes("w-full h-full"):
                with ui.row().classes("w-full items-center"):
                    ui.button(
                        "Refresh PartyContext",
                        on_click=self._refresh_party_context,
                    )
                    self._party_context_filter = ui.input(
                        "Filter fields or values"
                    )
                    self._party_context_filter.on(
                        "update:model-value",
                        lambda event: self._set_party_context_filter(event.args),
                    )
                    self._party_context_status = ui.label(
                        "Connect a client first"
                    )
                self._party_context_table = ui.table(
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
                self._party_context_table.classes("w-full h-full")
            with ui.tab_panel(guild_context_tab).classes("w-full h-full"):
                with ui.row().classes("w-full items-center"):
                    ui.button(
                        "Refresh GuildContext",
                        on_click=self._refresh_guild_context,
                    )
                    self._guild_context_filter = ui.input("Filter fields or values")
                    self._guild_context_filter.on(
                        "update:model-value",
                        lambda event: self._set_guild_context_filter(event.args),
                    )
                    self._guild_context_status = ui.label("Connect a client first")
                self._guild_context_table = ui.table(
                    columns=[
                        {"name": "offset", "label": "Offset", "field": "offset", "sortable": True},
                        {"name": "field", "label": "Field", "field": "field", "sortable": True},
                        {"name": "value", "label": "Value", "field": "value", "sortable": True},
                    ],
                    rows=[], row_key="field", selection="single",
                    pagination={"rowsPerPage": 10, "rowsPerPageOptions": [10, 20, 0]},
                ).props("bordered flat wrap-cells separator=cell")
                self._guild_context_table.classes("w-full h-full")
            with ui.tab_panel(acc_agent_context_tab).classes("w-full h-full"):
                with ui.row().classes("w-full items-center"):
                    ui.button(
                        "Refresh AccAgentContext",
                        on_click=self._refresh_acc_agent_context,
                    )
                    self._acc_agent_context_filter = ui.input(
                        "Filter fields or values"
                    )
                    self._acc_agent_context_filter.on(
                        "update:model-value",
                        lambda event: self._set_acc_agent_context_filter(event.args),
                    )
                    self._acc_agent_context_status = ui.label(
                        "Connect a client first"
                    )
                self._acc_agent_context_table = ui.table(
                    columns=[
                        {"name": "offset", "label": "Offset", "field": "offset", "sortable": True},
                        {"name": "field", "label": "Field", "field": "field", "sortable": True},
                        {"name": "value", "label": "Value", "field": "value", "sortable": True},
                    ],
                    rows=[], row_key="field", selection="single",
                    pagination={"rowsPerPage": 10, "rowsPerPageOptions": [10, 20, 0]},
                ).props("bordered flat wrap-cells separator=cell")
                self._acc_agent_context_table.classes("w-full h-full")
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
        self._show_server_region(server_region_snapshot)
        self._show_instance_info(instance_info_snapshot)
        self._show_text_parser(text_parser_snapshot)
        self._show_available_characters(available_characters_snapshot)
        self._show_party_context(party_context_snapshot)
        self._show_guild_context(guild_context_snapshot)
        self._show_acc_agent_context(acc_agent_context_snapshot)
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
        if self._server_region_table is not None:
            self._server_region_table.rows = []
            self._server_region_table.update()
        if self._instance_info_table is not None:
            self._instance_info_table.rows = []
            self._instance_info_table.update()
        if self._text_parser_table is not None:
            self._text_parser_table.rows = []
            self._text_parser_table.update()
        if self._available_characters_table is not None:
            self._available_characters_table.rows = []
            self._available_characters_table.update()
        if self._party_context_table is not None:
            self._party_context_table.rows = []
            self._party_context_table.update()
        if self._guild_context_table is not None:
            self._guild_context_table.rows = []
            self._guild_context_table.update()
        if self._acc_agent_context_table is not None:
            self._acc_agent_context_table.rows = []
            self._acc_agent_context_table.update()
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
        if self._server_region_filter is not None:
            self._server_region_filter.value = ""
            self._server_region_filter.update()
        if self._instance_info_filter is not None:
            self._instance_info_filter.value = ""
            self._instance_info_filter.update()
        if self._text_parser_filter is not None:
            self._text_parser_filter.value = ""
            self._text_parser_filter.update()
        if self._available_characters_filter is not None:
            self._available_characters_filter.value = ""
            self._available_characters_filter.update()
        if self._party_context_filter is not None:
            self._party_context_filter.value = ""
            self._party_context_filter.update()
        if self._guild_context_filter is not None:
            self._guild_context_filter.value = ""
            self._guild_context_filter.update()
        if self._acc_agent_context_filter is not None:
            self._acc_agent_context_filter.value = ""
            self._acc_agent_context_filter.update()
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
        if self._server_region_status is not None:
            self._server_region_status.set_text("Connect a client first")
        if self._instance_info_status is not None:
            self._instance_info_status.set_text("Connect a client first")
        if self._text_parser_status is not None:
            self._text_parser_status.set_text("Connect a client first")
        if self._available_characters_status is not None:
            self._available_characters_status.set_text("Connect a client first")
        if self._party_context_status is not None:
            self._party_context_status.set_text("Connect a client first")
        if self._guild_context_status is not None:
            self._guild_context_status.set_text("Connect a client first")
        if self._acc_agent_context_status is not None:
            self._acc_agent_context_status.set_text("Connect a client first")

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

    def _read_server_region_timed(
        self, connection: ConnectedClient
    ) -> ServerRegionStruct | None:
        """Read one ServerRegion snapshot and retain its elapsed time."""

        metric_name = "ServerRegion.read"
        self._perf.start(metric_name)
        try:
            return connection.read_server_region()
        finally:
            self._last_server_region_read_ms = self._perf.end(metric_name)

    def _read_instance_info_timed(
        self, connection: ConnectedClient
    ) -> InstanceInfoStruct | None:
        """Read one InstanceInfo snapshot and retain its elapsed time."""

        metric_name = "InstanceInfo.read"
        self._perf.start(metric_name)
        try:
            return connection.read_instance_info()
        finally:
            self._last_instance_info_read_ms = self._perf.end(metric_name)

    def _read_text_parser_timed(
        self, connection: ConnectedClient
    ) -> TextParserStruct | None:
        """Read one TextParser snapshot and retain its elapsed time."""

        metric_name = "TextParser.read"
        self._perf.start(metric_name)
        try:
            return connection.read_text_parser()
        finally:
            self._last_text_parser_read_ms = self._perf.end(metric_name)

    def _read_available_characters_timed(
        self, connection: ConnectedClient
    ) -> AvailableCharacterArrayStruct | None:
        """Read one account-roster snapshot and retain its elapsed time."""

        metric_name = "AvailableCharacters.read"
        self._perf.start(metric_name)
        try:
            return connection.read_available_characters()
        finally:
            self._last_available_characters_read_ms = self._perf.end(metric_name)

    def _read_party_context_timed(
        self, connection: ConnectedClient
    ) -> PartyContextStruct | None:
        """Read one PartyContext snapshot and retain its elapsed time."""

        metric_name = "PartyContext.read"
        self._perf.start(metric_name)
        try:
            return connection.read_party_context()
        finally:
            self._last_party_context_read_ms = self._perf.end(metric_name)

    def _read_guild_context_timed(
        self, connection: ConnectedClient
    ) -> GuildContextStruct | None:
        """Read one GuildContext snapshot and retain its elapsed time."""

        metric_name = "GuildContext.read"
        self._perf.start(metric_name)
        try:
            return connection.read_guild_context()
        finally:
            self._last_guild_context_read_ms = self._perf.end(metric_name)

    def _read_acc_agent_context_timed(
        self, connection: ConnectedClient
    ) -> AccAgentContextStruct | None:
        """Read one AccAgentContext snapshot and retain its elapsed time."""

        metric_name = "AccAgentContext.read"
        self._perf.start(metric_name)
        try:
            return connection.read_acc_agent_context()
        finally:
            self._last_acc_agent_context_read_ms = self._perf.end(metric_name)

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

    def _show_server_region(self, snapshot: ServerRegionStruct | None) -> None:
        """Display the maintained ServerRegion value when available."""

        if snapshot is None:
            self._server_region_table.rows = []
            self._server_region_table.update()
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
        self._server_region_table.rows = rows
        self._server_region_table.update()
        timing = ""
        if self._last_server_region_read_ms is not None:
            timing = f" — read {self._last_server_region_read_ms:.3f} ms"
        self._server_region_status.set_text("ServerRegion refreshed" + timing)

    def _set_server_region_filter(self, value: Any) -> None:
        """Apply the field/value filter to the ServerRegion table."""

        if self._server_region_table is None:
            return
        self._server_region_table.filter = str(value or "")
        self._server_region_table.update()

    def _show_instance_info(self, snapshot: InstanceInfoStruct | None) -> None:
        """Display InstanceInfo fields and its maintained nested records."""

        if snapshot is None:
            self._instance_info_table.rows = []
            self._instance_info_table.update()
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
        self._instance_info_table.rows = rows
        self._instance_info_table.update()
        timing = ""
        if self._last_instance_info_read_ms is not None:
            timing = f" — read {self._last_instance_info_read_ms:.3f} ms"
        self._instance_info_status.set_text("InstanceInfo refreshed" + timing)

    def _set_instance_info_filter(self, value: Any) -> None:
        """Apply the field/value filter to the InstanceInfo table."""

        if self._instance_info_table is None:
            return
        self._instance_info_table.filter = str(value or "")
        self._instance_info_table.update()

    def _show_text_parser(self, snapshot: TextParserStruct | None) -> None:
        """Display TextParser properties and its maintained raw fields."""

        if snapshot is None:
            self._text_parser_table.rows = []
            self._text_parser_table.update()
            self._text_parser_status.set_text(
                "TextParser is not available"
            )
            return

        cache = snapshot.cache
        sub_struct = snapshot.sub_struct
        rows: list[ContextFieldRow] = [
            {
                "offset": "property",
                "field": "cache",
                "value": self._format_context_value(cache)
                if cache is not None
                else "(none)",
            },
            {
                "offset": "property",
                "field": "sub_struct",
                "value": self._format_context_value(sub_struct)
                if sub_struct is not None
                else "(none)",
            },
        ]
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
        self._text_parser_table.rows = rows
        self._text_parser_table.update()
        timing = ""
        if self._last_text_parser_read_ms is not None:
            timing = f" — read {self._last_text_parser_read_ms:.3f} ms"
        self._text_parser_status.set_text("TextParser refreshed" + timing)

    def _set_text_parser_filter(self, value: Any) -> None:
        """Apply the field/value filter to the TextParser table."""

        if self._text_parser_table is None:
            return
        self._text_parser_table.filter = str(value or "")
        self._text_parser_table.update()

    def _show_available_characters(
        self, snapshot: AvailableCharacterArrayStruct | None
    ) -> None:
        """Display the live account-wide roster and decoded properties."""

        if snapshot is None:
            self._available_characters_table.rows = []
            self._available_characters_table.update()
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
        self._available_characters_table.rows = rows
        self._available_characters_table.update()
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
        self._available_characters_table.filter = str(value or "")
        self._available_characters_table.update()

    def _show_party_context(self, snapshot: PartyContextStruct | None) -> None:
        """Display PartyContext flags, counts, and maintained fields."""

        if snapshot is None:
            self._party_context_table.rows = []
            self._party_context_table.update()
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
        self._party_context_table.rows = rows
        self._party_context_table.update()
        timing = ""
        if self._last_party_context_read_ms is not None:
            timing = f" — read {self._last_party_context_read_ms:.3f} ms"
        self._party_context_status.set_text("PartyContext refreshed" + timing)

    def _set_party_context_filter(self, value: Any) -> None:
        """Apply the field/value filter to the PartyContext table."""

        if self._party_context_table is None:
            return
        self._party_context_table.filter = str(value or "")
        self._party_context_table.update()

    def _show_guild_context(self, snapshot: GuildContextStruct | None) -> None:
        """Display GuildContext properties, nested counts, and raw fields."""

        if snapshot is None:
            self._guild_context_table.rows = []
            self._guild_context_table.update()
            self._guild_context_status.set_text("GuildContext is not active")
            return

        guilds = snapshot.guild_array
        roster = snapshot.player_roster
        history = snapshot.player_guild_history
        alliances = snapshot.factions_outpost_guilds
        rows: list[ContextFieldRow] = [
            {"offset": "property", "field": "player_name_str", "value": snapshot.player_name_str or "in selection menus"},
            {"offset": "property", "field": "announcement_str", "value": snapshot.announcement_str},
            {"offset": "property", "field": "announcement_author_str", "value": snapshot.announcement_author_str},
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
        self._guild_context_table.rows = rows
        self._guild_context_table.update()
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
        self._guild_context_table.filter = str(value or "")
        self._guild_context_table.update()

    def _show_acc_agent_context(
        self, snapshot: AccAgentContextStruct | None
    ) -> None:
        """Display useful agent counts and the maintained raw root fields."""

        if snapshot is None:
            self._acc_agent_context_table.rows = []
            self._acc_agent_context_table.update()
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
        self._acc_agent_context_table.rows = rows
        self._acc_agent_context_table.update()
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
        self._acc_agent_context_table.filter = str(value or "")
        self._acc_agent_context_table.update()

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
