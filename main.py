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
        self._camera_status: Any = None
        self._camera_table: Any = None
        self._camera_filter: Any = None
        self._friend_list_status: Any = None
        self._friend_list_table: Any = None
        self._friend_list_filter: Any = None
        self._chat_buffer_status: Any = None
        self._chat_buffer_table: Any = None
        self._chat_buffer_filter: Any = None
        self._world_context_status: Any = None
        self._world_context_table: Any = None
        self._world_context_filter: Any = None
        self._map_context_status: Any = None
        self._map_context_table: Any = None
        self._map_context_filter: Any = None
        self._trade_context_status: Any = None
        self._trade_context_table: Any = None
        self._trade_context_filter: Any = None
        self._item_context_status: Any = None
        self._item_context_table: Any = None
        self._item_records_table: Any = None
        self._item_context_filter: Any = None
        self._account_context_status: Any = None
        self._account_context_table: Any = None
        self._account_context_filter: Any = None
        self._gadget_context_status: Any = None
        self._gadget_context_table: Any = None
        self._gadget_context_filter: Any = None
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
            camera_tab = ui.tab("Camera")
            friend_list_tab = ui.tab("FriendList")
            chat_buffer_tab = ui.tab("ChatBuffer")
            world_context_tab = ui.tab("WorldContext")
            map_context_tab = ui.tab("MapContext")
            trade_context_tab = ui.tab("TradeContext")
            item_context_tab = ui.tab("ItemContext")
            account_context_tab = ui.tab("AccountContext")
            gadget_context_tab = ui.tab("GadgetContext")
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
            with ui.tab_panel(camera_tab).classes("w-full h-full"):
                with ui.row().classes("w-full items-center"):
                    ui.button("Refresh Camera", on_click=self._refresh_camera)
                    self._camera_filter = ui.input("Filter fields or values")
                    self._camera_filter.on(
                        "update:model-value",
                        lambda event: self._set_camera_filter(event.args),
                    )
                    self._camera_status = ui.label("Connect a client first")
                self._camera_table = ui.table(
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
                        "rowsPerPage": 15,
                        "rowsPerPageOptions": [15, 30, 0],
                    },
                ).props("bordered flat wrap-cells separator=cell")
                self._camera_table.classes("w-full h-full")
            with ui.tab_panel(friend_list_tab).classes("w-full h-full"):
                with ui.row().classes("w-full items-center"):
                    ui.button(
                        "Refresh FriendList",
                        on_click=self._refresh_friend_list,
                    )
                    self._friend_list_filter = ui.input("Filter fields or values")
                    self._friend_list_filter.on(
                        "update:model-value",
                        lambda event: self._set_friend_list_filter(event.args),
                    )
                    self._friend_list_status = ui.label("Connect a client first")
                self._friend_list_table = ui.table(
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
                        "rowsPerPage": 15,
                        "rowsPerPageOptions": [15, 30, 0],
                    },
                ).props("bordered flat wrap-cells separator=cell")
                self._friend_list_table.classes("w-full h-full")
            with ui.tab_panel(chat_buffer_tab).classes("w-full h-full"):
                with ui.row().classes("w-full items-center"):
                    ui.button(
                        "Refresh ChatBuffer",
                        on_click=self._refresh_chat_buffer,
                    )
                    self._chat_buffer_filter = ui.input("Filter fields or values")
                    self._chat_buffer_filter.on(
                        "update:model-value",
                        lambda event: self._set_chat_buffer_filter(event.args),
                    )
                    self._chat_buffer_status = ui.label("Connect a client first")
                self._chat_buffer_table = ui.table(
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
                        "rowsPerPage": 15,
                        "rowsPerPageOptions": [15, 30, 0],
                    },
                ).props("bordered flat wrap-cells separator=cell")
                self._chat_buffer_table.classes("w-full h-full")
            with ui.tab_panel(world_context_tab).classes("w-full h-full"):
                with ui.row().classes("w-full items-center"):
                    ui.button(
                        "Refresh WorldContext",
                        on_click=self._refresh_world_context,
                    )
                    self._world_context_filter = ui.input(
                        "Filter fields or values"
                    )
                    self._world_context_filter.on(
                        "update:model-value",
                        lambda event: self._set_world_context_filter(event.args),
                    )
                    self._world_context_status = ui.label(
                        "Connect a client first"
                    )
                self._world_context_table = ui.table(
                    columns=[
                        {"name": "offset", "label": "Offset", "field": "offset", "sortable": True},
                        {"name": "field", "label": "Field", "field": "field", "sortable": True},
                        {"name": "value", "label": "Value", "field": "value", "sortable": True},
                    ],
                    rows=[],
                    row_key="field",
                    selection="single",
                    pagination={"rowsPerPage": 20, "rowsPerPageOptions": [20, 40, 0]},
                ).props("bordered flat wrap-cells separator=cell")
                self._world_context_table.classes("w-full h-full")
            with ui.tab_panel(map_context_tab).classes("w-full h-full"):
                with ui.row().classes("w-full items-center"):
                    ui.button(
                        "Refresh MapContext",
                        on_click=self._refresh_map_context,
                    )
                    self._map_context_filter = ui.input("Filter fields or values")
                    self._map_context_filter.on(
                        "update:model-value",
                        lambda event: self._set_map_context_filter(event.args),
                    )
                    self._map_context_status = ui.label("Connect a client first")
                self._map_context_table = ui.table(
                    columns=[
                        {"name": "offset", "label": "Offset", "field": "offset", "sortable": True},
                        {"name": "field", "label": "Field", "field": "field", "sortable": True},
                        {"name": "value", "label": "Value", "field": "value", "sortable": True},
                    ],
                    rows=[],
                    row_key="field",
                    selection="single",
                    pagination={"rowsPerPage": 20, "rowsPerPageOptions": [20, 40, 0]},
                ).props("bordered flat wrap-cells separator=cell")
                self._map_context_table.classes("w-full h-full")
            with ui.tab_panel(trade_context_tab).classes("w-full h-full"):
                with ui.row().classes("w-full items-center"):
                    ui.button(
                        "Refresh TradeContext",
                        on_click=self._refresh_trade_context,
                    )
                    self._trade_context_filter = ui.input(
                        "Filter fields or values"
                    )
                    self._trade_context_filter.on(
                        "update:model-value",
                        lambda event: self._set_trade_context_filter(event.args),
                    )
                    self._trade_context_status = ui.label(
                        "Connect a client first"
                    )
                self._trade_context_table = ui.table(
                    columns=[
                        {"name": "offset", "label": "Offset", "field": "offset", "sortable": True},
                        {"name": "field", "label": "Field", "field": "field", "sortable": True},
                        {"name": "value", "label": "Value", "field": "value", "sortable": True},
                    ],
                    rows=[],
                    row_key="field",
                    selection="single",
                    pagination={"rowsPerPage": 15, "rowsPerPageOptions": [15, 30, 0]},
                ).props("bordered flat wrap-cells separator=cell")
                self._trade_context_table.classes("w-full h-full")
            with ui.tab_panel(item_context_tab).classes("w-full h-full"):
                with ui.row().classes("w-full items-center"):
                    ui.button(
                        "Refresh ItemContext",
                        on_click=self._refresh_item_context,
                    )
                    self._item_context_filter = ui.input(
                        "Filter fields or values"
                    )
                    self._item_context_filter.on(
                        "update:model-value",
                        lambda event: self._set_item_context_filter(event.args),
                    )
                    self._item_context_status = ui.label(
                        "Connect a client first"
                    )
                self._item_context_table = ui.table(
                    columns=[
                        {"name": "offset", "label": "Offset", "field": "offset", "sortable": True},
                        {"name": "field", "label": "Field", "field": "field", "sortable": True},
                        {"name": "value", "label": "Value", "field": "value", "sortable": True},
                    ],
                    rows=[],
                    row_key="field",
                    selection="single",
                    pagination={"rowsPerPage": 15, "rowsPerPageOptions": [15, 30, 0]},
                ).props("bordered flat wrap-cells separator=cell")
                self._item_context_table.classes("w-full h-full")
                ui.label("Items read through the maintained bag arrays").classes(
                    "text-subtitle2"
                )
                self._item_records_table = ui.table(
                    columns=[
                        {"name": "bag", "label": "Bag", "field": "bag", "sortable": True},
                        {"name": "slot", "label": "Slot", "field": "slot", "sortable": True},
                        {"name": "item_id", "label": "Item ID", "field": "item_id", "sortable": True},
                        {"name": "quantity", "label": "Quantity", "field": "quantity", "sortable": True},
                        {"name": "model_id", "label": "Model ID", "field": "model_id", "sortable": True},
                        {"name": "type", "label": "Type", "field": "type", "sortable": True},
                        {"name": "modifier_count", "label": "Modifiers", "field": "modifier_count", "sortable": True},
                        {"name": "address", "label": "Address", "field": "address", "sortable": True},
                    ],
                    rows=[],
                    row_key="address",
                    selection="single",
                    pagination={"rowsPerPage": 25, "rowsPerPageOptions": [25, 50, 0]},
                ).props("bordered flat wrap-cells separator=cell")
                self._item_records_table.classes("w-full h-full")
            with ui.tab_panel(account_context_tab).classes("w-full h-full"):
                with ui.row().classes("w-full items-center"):
                    ui.button(
                        "Refresh AccountContext",
                        on_click=self._refresh_account_context,
                    )
                    self._account_context_filter = ui.input(
                        "Filter fields or values"
                    )
                    self._account_context_filter.on(
                        "update:model-value",
                        lambda event: self._set_account_context_filter(event.args),
                    )
                    self._account_context_status = ui.label(
                        "Connect a client first"
                    )
                self._account_context_table = ui.table(
                    columns=[
                        {"name": "offset", "label": "Offset", "field": "offset", "sortable": True},
                        {"name": "field", "label": "Field", "field": "field", "sortable": True},
                        {"name": "value", "label": "Value", "field": "value", "sortable": True},
                    ],
                    rows=[],
                    row_key="field",
                    selection="single",
                    pagination={"rowsPerPage": 15, "rowsPerPageOptions": [15, 30, 0]},
                ).props("bordered flat wrap-cells separator=cell")
                self._account_context_table.classes("w-full h-full")
            with ui.tab_panel(gadget_context_tab).classes("w-full h-full"):
                with ui.row().classes("w-full items-center"):
                    ui.button(
                        "Refresh GadgetContext",
                        on_click=self._refresh_gadget_context,
                    )
                    self._gadget_context_filter = ui.input(
                        "Filter fields or values"
                    )
                    self._gadget_context_filter.on(
                        "update:model-value",
                        lambda event: self._set_gadget_context_filter(event.args),
                    )
                    self._gadget_context_status = ui.label(
                        "Connect a client first"
                    )
                self._gadget_context_table = ui.table(
                    columns=[
                        {"name": "offset", "label": "Offset", "field": "offset", "sortable": True},
                        {"name": "field", "label": "Field", "field": "field", "sortable": True},
                        {"name": "value", "label": "Value", "field": "value", "sortable": True},
                    ],
                    rows=[],
                    row_key="field",
                    selection="single",
                    pagination={"rowsPerPage": 15, "rowsPerPageOptions": [15, 30, 0]},
                ).props("bordered flat wrap-cells separator=cell")
                self._gadget_context_table.classes("w-full h-full")
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
            return

        description = character if is_logged_in else "in selection menus"
        self._connected_label.set_text(
            f"Connected to PID {pid} — {description}"
        )
        self._data_tab.enable()
        self._data_tab.update()
        self._show_pre_game_context(pre_game_snapshot)
        self._show_cinematic(cinematic_snapshot)
        self._show_camera(camera_snapshot)
        self._show_friend_list(friend_list_snapshot)
        self._show_chat_buffer(chat_buffer_snapshot)
        self._show_world_context(world_context_snapshot)
        self._show_map_context(map_context_snapshot)
        self._show_trade_context(trade_context_snapshot)
        self._show_item_context(item_context_snapshot)
        self._show_account_context(account_context_snapshot)
        self._show_gadget_context(gadget_context_snapshot)
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
        if self._camera_table is not None:
            self._camera_table.rows = []
            self._camera_table.update()
        if self._friend_list_table is not None:
            self._friend_list_table.rows = []
            self._friend_list_table.update()
        if self._chat_buffer_table is not None:
            self._chat_buffer_table.rows = []
            self._chat_buffer_table.update()
        if self._world_context_table is not None:
            self._world_context_table.rows = []
            self._world_context_table.update()
        if self._map_context_table is not None:
            self._map_context_table.rows = []
            self._map_context_table.update()
        if self._trade_context_table is not None:
            self._trade_context_table.rows = []
            self._trade_context_table.update()
        if self._item_context_table is not None:
            self._item_context_table.rows = []
            self._item_context_table.update()
        if self._item_records_table is not None:
            self._item_records_table.rows = []
            self._item_records_table.update()
        if self._account_context_table is not None:
            self._account_context_table.rows = []
            self._account_context_table.update()
        if self._gadget_context_table is not None:
            self._gadget_context_table.rows = []
            self._gadget_context_table.update()
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
        if self._camera_filter is not None:
            self._camera_filter.value = ""
            self._camera_filter.update()
        if self._friend_list_filter is not None:
            self._friend_list_filter.value = ""
            self._friend_list_filter.update()
        if self._chat_buffer_filter is not None:
            self._chat_buffer_filter.value = ""
            self._chat_buffer_filter.update()
        if self._world_context_filter is not None:
            self._world_context_filter.value = ""
            self._world_context_filter.update()
        if self._map_context_filter is not None:
            self._map_context_filter.value = ""
            self._map_context_filter.update()
        if self._trade_context_filter is not None:
            self._trade_context_filter.value = ""
            self._trade_context_filter.update()
        if self._item_context_filter is not None:
            self._item_context_filter.value = ""
            self._item_context_filter.update()
        if self._account_context_filter is not None:
            self._account_context_filter.value = ""
            self._account_context_filter.update()
        if self._gadget_context_filter is not None:
            self._gadget_context_filter.value = ""
            self._gadget_context_filter.update()
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
        if self._camera_status is not None:
            self._camera_status.set_text("Connect a client first")
        if self._friend_list_status is not None:
            self._friend_list_status.set_text("Connect a client first")
        if self._chat_buffer_status is not None:
            self._chat_buffer_status.set_text("Connect a client first")
        if self._world_context_status is not None:
            self._world_context_status.set_text("Connect a client first")
        if self._map_context_status is not None:
            self._map_context_status.set_text("Connect a client first")
        if self._trade_context_status is not None:
            self._trade_context_status.set_text("Connect a client first")
        if self._item_context_status is not None:
            self._item_context_status.set_text("Connect a client first")
        if self._account_context_status is not None:
            self._account_context_status.set_text("Connect a client first")
        if self._gadget_context_status is not None:
            self._gadget_context_status.set_text("Connect a client first")
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

    def _show_camera(self, snapshot: CameraStruct | None) -> None:
        """Display camera properties and the maintained raw fields."""

        if snapshot is None:
            self._camera_table.rows = []
            self._camera_table.update()
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
        self._camera_table.rows = rows
        self._camera_table.update()
        timing = ""
        if self._last_camera_read_ms is not None:
            timing = f" — read {self._last_camera_read_ms:.3f} ms"
        self._camera_status.set_text("Camera refreshed" + timing)

    def _set_camera_filter(self, value: Any) -> None:
        """Apply the field/value filter to the Camera table."""

        if self._camera_table is None:
            return
        self._camera_table.filter = str(value or "")
        self._camera_table.update()

    def _show_friend_list(self, snapshot: FriendListStruct | None) -> None:
        """Display friend-list counts, status, and bounded friend records."""

        if snapshot is None:
            self._friend_list_table.rows = []
            self._friend_list_table.update()
            self._friend_list_status.set_text("FriendList is not available")
            return

        try:
            friends = snapshot.friend_records
        except OSError as error:
            self._friend_list_table.rows = []
            self._friend_list_table.update()
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
        self._friend_list_table.rows = rows
        self._friend_list_table.update()
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
        self._friend_list_table.filter = str(value or "")
        self._friend_list_table.update()

    def _show_chat_buffer(self, snapshot: ChatBufferStruct | None) -> None:
        """Display chat-ring metadata and a bounded set of decoded messages."""

        if snapshot is None:
            self._chat_buffer_table.rows = []
            self._chat_buffer_table.update()
            self._chat_buffer_status.set_text("ChatBuffer is not available")
            return

        try:
            messages = snapshot.message_records
            is_typing = self._connection.is_typing() if self._connection else False
        except OSError as error:
            self._chat_buffer_table.rows = []
            self._chat_buffer_table.update()
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
        self._chat_buffer_table.rows = rows
        self._chat_buffer_table.update()
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
        self._chat_buffer_table.filter = str(value or "")
        self._chat_buffer_table.update()

    def _show_map_context(self, snapshot: MapContextStruct | None) -> None:
        """Display the MapContext root and a bounded list of spawn points."""

        if snapshot is None:
            self._map_context_table.rows = []
            self._map_context_table.update()
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
        self._map_context_table.rows = rows
        self._map_context_table.update()
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
        self._map_context_table.filter = str(value or "")
        self._map_context_table.update()

    def _show_world_context(self, snapshot: WorldContextStruct | None) -> None:
        """Display world-root scalars and array counts without child traversal."""

        if snapshot is None:
            self._world_context_table.rows = []
            self._world_context_table.update()
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
                player_name = player.name or "(unnamed)"
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
                        f"level={hero.level}, name={hero.name or '(unnamed)'}"
                    ),
                }
            )
        for index, pet in enumerate(pets[:32]):
            try:
                pet_name = pet.name or "(unnamed)"
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
                        f"skills={skillbar.skill_ids}"
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
        self._world_context_table.rows = rows
        self._world_context_table.update()
        timing = ""
        if self._last_world_context_read_ms is not None:
            timing = f" — read {self._last_world_context_read_ms:.3f} ms"
        self._world_context_status.set_text("WorldContext refreshed" + timing)

    def _set_world_context_filter(self, value: Any) -> None:
        """Apply the field/value filter to the WorldContext table."""

        if self._world_context_table is None:
            return
        self._world_context_table.filter = str(value or "")
        self._world_context_table.update()

    def _show_trade_context(self, snapshot: TradeContextStruct | None) -> None:
        """Display trade state and bounded offers without performing actions."""

        if snapshot is None:
            self._trade_context_table.rows = []
            self._trade_context_table.update()
            self._trade_context_status.set_text("TradeContext is not available")
            return

        try:
            player_offer = snapshot.player_offer
            partner_offer = snapshot.partner_offer
            player_items = player_offer.offered_items
            partner_items = partner_offer.offered_items
        except (OSError, RuntimeError) as error:
            self._trade_context_table.rows = []
            self._trade_context_table.update()
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
        self._trade_context_table.rows = rows
        self._trade_context_table.update()
        timing = ""
        if self._last_trade_context_read_ms is not None:
            timing = f" — read {self._last_trade_context_read_ms:.3f} ms"
        self._trade_context_status.set_text("TradeContext refreshed" + timing)

    def _set_trade_context_filter(self, value: Any) -> None:
        """Apply the field/value filter to the TradeContext table."""

        if self._trade_context_table is None:
            return
        self._trade_context_table.filter = str(value or "")
        self._trade_context_table.update()

    def _show_item_context(self, snapshot: ItemContextStruct | None) -> None:
        """Display the item root and bounded records reached through bags."""

        if snapshot is None:
            self._item_context_table.rows = []
            self._item_context_table.update()
            self._item_records_table.rows = []
            self._item_records_table.update()
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
        self._item_context_table.rows = rows
        self._item_context_table.update()
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
        self._item_records_table.rows = item_rows
        self._item_records_table.update()
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
        self._item_context_table.filter = str(value or "")
        self._item_context_table.update()

    def _show_account_context(
        self, snapshot: AccountContextStruct | None
    ) -> None:
        """Display account-root fields and array headers without traversal."""

        if snapshot is None:
            self._account_context_table.rows = []
            self._account_context_table.update()
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
        self._account_context_table.rows = rows
        self._account_context_table.update()
        timing = ""
        if self._last_account_context_read_ms is not None:
            timing = f" — read {self._last_account_context_read_ms:.3f} ms"
        self._account_context_status.set_text("AccountContext refreshed" + timing)

    def _set_account_context_filter(self, value: Any) -> None:
        """Apply the field/value filter to the AccountContext table."""

        if self._account_context_table is None:
            return
        self._account_context_table.filter = str(value or "")
        self._account_context_table.update()

    def _show_gadget_context(self, snapshot: GadgetContextStruct | None) -> None:
        """Display gadget-root metadata and a bounded info sample."""

        if snapshot is None:
            self._gadget_context_table.rows = []
            self._gadget_context_table.update()
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
        self._gadget_context_table.rows = rows
        self._gadget_context_table.update()
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
        self._gadget_context_table.filter = str(value or "")
        self._gadget_context_table.update()

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

    def _show_context(self, snapshot: CharContextStruct | None) -> None:
        """Display every maintained CharContext field in the table.

        ``None`` means the readiness gate is closed. The character context is
        map-scoped, so it is not readable until a map is ready; the table says so
        rather than continuing to show the previous map's rows.
        """

        if snapshot is None:
            self._context_table.rows = []
            self._context_table.update()
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
