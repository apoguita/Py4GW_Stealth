"""Simple external connection objects for selected Guild Wars clients."""

from __future__ import annotations

from typing import Any

from .context import (
    CharContext,
    CharContextStruct,
    Cinematic,
    CinematicStruct,
    GameContext,
    GameContextStruct,
    MapContext,
    MapContextStruct,
    GameplayContext,
    GameplayContextStruct,
    PreGameContext,
    PreGameContextStruct,
    ServerRegion,
    ServerRegionStruct,
    InstanceInfo,
    InstanceInfoStruct,
    TextParser,
    TextParserStruct,
    AvailableCharacterArray,
    AvailableCharacterArrayStruct,
    PartyContext,
    PartyContextStruct,
    GuildContext,
    GuildContextStruct,
    AccAgentContext,
    AccAgentContextStruct,
    Camera,
    CameraStruct,
    FriendList,
    FriendListStruct,
    ChatBuffer,
    ChatBufferStruct,
    WorldContext,
    WorldContextStruct,
    TradeContext,
    TradeContextStruct,
    ItemContext,
    ItemContextStruct,
    ItemFormulaStruct,
    PvPItemInfoStruct,
    PvPItemUpgradeInfoStruct,
    CompositeModelInfoStruct,
    BagStruct,
    InventoryStruct,
    ItemStruct,
    AccountContext,
    AccountContextStruct,
    GadgetContext,
    GadgetContextStruct,
    AgentArray,
    AgentArraySnapshot,
    AgentGadgetStruct,
    AgentItemStruct,
    AgentLivingStruct,
    AgentStruct,
    AgentReference,
    LivingAgentSnapshot,
)
from .memory import ProcessMemoryReader
from .performance import PerfCounter
from .scanner import PatternCatalog, RemoteScanner
from .win32 import Win32


class ConnectedClient:
    """Own the read-only resources for one selected ``Gw.exe`` process."""

    def __init__(
        self,
        process: dict[str, Any] | int,
        win32: Win32 | None = None,
        perf_counter: PerfCounter | None = None,
    ) -> None:
        """Connect to a discovered client and optionally time setup stages.

        ``perf_counter`` is only a diagnostic sink; it does not change the
        read-only connection behavior.
        """

        self._win32 = win32 or Win32()
        self._process = self._resolve_process(process)
        self._pid = int(self._process["pid"])
        module = self._win32.get_main_module(self._pid)
        self._reader = ProcessMemoryReader(self._win32, self._pid)
        try:
            self._scanner = RemoteScanner(
                self._reader,
                int(module["base_address"]),
                int(module["size"]),
            )
            self._scanner.initialize()
            patterns = PatternCatalog.from_directory("offsets")
            self._game_context = GameContext(
                self._reader,
                self._scanner,
                patterns,
            )
            self._game_context.initialize()
            self._map_context = MapContext(self._reader, self._game_context)
            self._gameplay_context = GameplayContext(
                self._reader,
                self._scanner,
                patterns,
            )
            self._gameplay_context.initialize()
            self._cinematic = Cinematic(self._reader, self._game_context)
            self._pre_game_context = PreGameContext(
                self._reader,
                self._scanner,
                patterns,
            )
            self._pre_game_context.initialize()
            self._server_region = ServerRegion(
                self._reader,
                self._scanner,
                patterns,
            )
            self._server_region.initialize()
            self._instance_info = InstanceInfo(
                self._reader,
                self._scanner,
                patterns,
            )
            self._instance_info.initialize()
            self._text_parser = TextParser(self._reader, self._game_context)
            self._available_characters = AvailableCharacterArray(
                self._reader,
                self._scanner,
                patterns,
            )
            self._available_characters.initialize()
            self._party_context = PartyContext(self._reader, self._game_context)
            self._guild_context = GuildContext(self._reader, self._game_context)
            self._acc_agent_context = AccAgentContext(
                self._reader, self._game_context
            )
            self._camera = Camera(self._reader, self._scanner, patterns)
            self._camera.initialize()
            self._friend_list = FriendList(
                self._reader,
                self._scanner,
                patterns,
            )
            self._friend_list.initialize()
            self._chat_buffer = ChatBuffer(
                self._reader,
                self._scanner,
                patterns,
            )
            self._chat_buffer.initialize()
            self._world_context = WorldContext(self._reader, self._game_context)
            self._trade_context = TradeContext(self._reader, self._game_context)
            self._item_context = ItemContext(
                self._reader,
                self._game_context,
                self._scanner,
                patterns,
            )
            self._item_context.initialize()
            self._account_context = AccountContext(
                self._reader, self._game_context
            )
            self._gadget_context = GadgetContext(
                self._reader, self._game_context
            )
            self._agent_array = AgentArray(
                self._reader,
                self._scanner,
                patterns,
                self._acc_agent_context,
            )
            self._agent_array.initialize(perf_counter)
            self._context = CharContext(
                self._reader,
                self._scanner,
                patterns,
                game_context=self._game_context,
            )
            self._context.initialize()
        except Exception:
            self._reader.close()
            raise

    @property
    def pid(self) -> int:
        """Return the selected process ID."""

        return self._pid

    @property
    def process(self) -> dict[str, Any]:
        """Return the process record used to create this connection."""

        return dict(self._process)

    @property
    def context(self) -> CharContext:
        """Return the external CharContext reader for this client."""

        return self._context

    @property
    def game_context(self) -> GameContext:
        """Return the external GameContext reader for this client."""

        return self._game_context

    def read_game_context(self) -> GameContextStruct:
        """Read and return the current complete GameContext snapshot."""

        return self._game_context.read()

    @property
    def map_context(self) -> MapContext:
        """Return the external read-only MapContext reader."""

        return self._map_context

    def read_map_context(
        self,
        max_spawn_entries: int = 2048,
        max_pathing_maps: int = 32,
    ) -> MapContextStruct | None:
        """Read MapContext and bounded pathing-context roots."""

        return self._map_context.read(max_spawn_entries, max_pathing_maps)

    @property
    def gameplay_context(self) -> GameplayContext:
        """Return the external GameplayContext reader for this client."""

        return self._gameplay_context

    def read_gameplay_context(self) -> GameplayContextStruct | None:
        """Read and return the current GameplayContext snapshot, if present."""

        return self._gameplay_context.read()

    @property
    def pre_game_context(self) -> PreGameContext:
        """Return the external PreGameContext reader for this client."""

        return self._pre_game_context

    def read_pre_game_context(self) -> PreGameContextStruct | None:
        """Read and return the current complete PreGameContext snapshot."""

        return self._pre_game_context.read()

    @property
    def server_region(self) -> ServerRegion:
        """Return the external ServerRegion reader for this client."""

        return self._server_region

    def read_server_region(self) -> ServerRegionStruct | None:
        """Read and return the current server-region value, if available."""

        return self._server_region.read()

    @property
    def instance_info(self) -> InstanceInfo:
        """Return the external InstanceInfo reader for this client."""

        return self._instance_info

    def read_instance_info(self) -> InstanceInfoStruct | None:
        """Read and return the current InstanceInfo snapshot, if available."""

        return self._instance_info.read()

    @property
    def text_parser(self) -> TextParser:
        """Return the external TextParser reader for this client."""

        return self._text_parser

    def read_text_parser(self) -> TextParserStruct | None:
        """Read the current TextParser snapshot, if its pointer is available."""

        return self._text_parser.read()

    @property
    def available_characters(self) -> AvailableCharacterArray:
        """Return the external account-roster reader for this client."""

        return self._available_characters

    def read_available_characters(self) -> AvailableCharacterArrayStruct | None:
        """Read the current account-wide available-character roster."""

        return self._available_characters.read()

    @property
    def party_context(self) -> PartyContext:
        """Return the external PartyContext reader for this client."""

        return self._party_context

    def read_party_context(self) -> PartyContextStruct | None:
        """Read the current PartyContext snapshot, if available."""

        return self._party_context.read()

    @property
    def guild_context(self) -> GuildContext:
        """Return the external GuildContext reader for this client."""

        return self._guild_context

    def read_guild_context(self) -> GuildContextStruct | None:
        """Read the current GuildContext snapshot, if available."""

        return self._guild_context.read()

    @property
    def acc_agent_context(self) -> AccAgentContext:
        """Return the external agent-context reader for this client."""

        return self._acc_agent_context

    def read_acc_agent_context(self) -> AccAgentContextStruct | None:
        """Read the current maintained agent context, if available."""

        return self._acc_agent_context.read()

    @property
    def camera(self) -> Camera:
        """Return the external read-only camera reader."""

        return self._camera

    def read_camera_context(self) -> CameraStruct | None:
        """Read the current camera state, if its native pointer is available."""

        return self._camera.read()

    @property
    def friend_list(self) -> FriendList:
        """Return the external read-only friend-list reader."""

        return self._friend_list

    def read_friend_list(self) -> FriendListStruct | None:
        """Read the current friend-list root and its bounded records on demand."""

        return self._friend_list.read()

    @property
    def chat_buffer(self) -> ChatBuffer:
        """Return the external read-only chat-buffer reader."""

        return self._chat_buffer

    def read_chat_buffer(self) -> ChatBufferStruct | None:
        """Read the current chat ring buffer, if its pointer is available."""

        return self._chat_buffer.read()

    def is_typing(self) -> bool:
        """Return the current read-only chat typing state."""

        return self._chat_buffer.is_typing()

    @property
    def world_context(self) -> WorldContext:
        """Return the external read-only WorldContext reader."""

        return self._world_context

    def read_world_context(self) -> WorldContextStruct | None:
        """Read the current maintained WorldContext root."""

        return self._world_context.read()

    @property
    def trade_context(self) -> TradeContext:
        """Return the external read-only TradeContext reader."""

        return self._trade_context

    def read_trade_context(self) -> TradeContextStruct | None:
        """Read the current trade context, if a trade is active."""

        return self._trade_context.read()

    def is_item_offered(self, item_id: int) -> bool:
        """Return whether the current player's trade offer contains an item."""

        trade = self._trade_context.read()
        return trade is not None and trade.is_item_offered(item_id)

    @property
    def item_context(self) -> ItemContext:
        """Return the external read-only ItemContext reader."""

        return self._item_context

    def read_item_context(self) -> ItemContextStruct | None:
        """Read the current maintained ItemContext root."""

        return self._item_context.read()

    def read_item_bags(self, limit: int = 64) -> list[BagStruct]:
        """Read at most ``limit`` bags through the maintained bag array."""

        snapshot = self._item_context.read()
        return [] if snapshot is None else snapshot.bags(limit)

    def read_item_records(self, limit_per_bag: int = 256) -> list[ItemStruct]:
        """Read bounded item records through the current bag relationships."""

        items: list[ItemStruct] = []
        for bag in self.read_item_bags():
            items.extend(bag.items(limit_per_bag))
        return items

    def read_inventory(self) -> InventoryStruct | None:
        """Read the optional native inventory relationship."""

        snapshot = self._item_context.read()
        return None if snapshot is None else snapshot.read_inventory()

    def read_item_formulas(self, limit: int = 4096) -> list[ItemFormulaStruct]:
        """Read the bounded native item-formula table."""

        return self._item_context.read_item_formulas(limit)

    def read_composite_model_infos(
        self, limit: int = 4096
    ) -> list[CompositeModelInfoStruct]:
        """Read the bounded native composite-model table."""

        return self._item_context.read_composite_model_infos(limit)

    def read_pvp_item_upgrades(
        self, limit: int = 4096
    ) -> list[PvPItemUpgradeInfoStruct]:
        """Read the bounded unlocked-PvP-upgrade table."""

        return self._item_context.read_pvp_item_upgrades(limit)

    def read_pvp_items(self, limit: int = 4096) -> list[PvPItemInfoStruct]:
        """Read the bounded native PvP-item metadata table."""

        return self._item_context.read_pvp_items(limit)

    @property
    def is_storage_open(self) -> bool | None:
        """Return the current native storage-open state, if resolved."""

        return self._item_context.is_storage_open

    @property
    def account_context(self) -> AccountContext:
        """Return the external read-only AccountContext reader."""

        return self._account_context

    def read_account_context(self) -> AccountContextStruct | None:
        """Read the current maintained AccountContext root."""

        return self._account_context.read()

    @property
    def gadget_context(self) -> GadgetContext:
        """Return the external read-only GadgetContext reader."""

        return self._gadget_context

    def read_gadget_context(self) -> GadgetContextStruct | None:
        """Read the current maintained GadgetContext root."""

        return self._gadget_context.read()

    @property
    def agent_array(self) -> AgentArray:
        """Return the bounded external agent-array reader."""

        return self._agent_array

    def read_agent_array(
        self, perf_counter: PerfCounter | None = None
    ) -> AgentArraySnapshot | None:
        """Read the current bounded set of agent references."""

        return self._agent_array.read(perf_counter)

    def read_agent(
        self, reference: AgentReference, perf_counter: PerfCounter | None = None
    ) -> AgentStruct | AgentLivingStruct | AgentItemStruct | AgentGadgetStruct:
        """Read one complete typed record for an AgentArray reference."""

        return self._agent_array.read_agent(reference, perf_counter)

    def read_agent_by_id(
        self, agent_id: int
    ) -> AgentStruct | AgentLivingStruct | AgentItemStruct | AgentGadgetStruct | None:
        """Find an agent ID and read its complete typed record."""

        return self._agent_array.read_agent_by_id(agent_id)

    @property
    def living_snapshot(self) -> LivingAgentSnapshot | None:
        """Return the latest complete living-agent snapshot, if refreshed."""

        return self._agent_array.living_snapshot

    def refresh_living_agents(
        self, perf_counter: PerfCounter | None = None
    ) -> LivingAgentSnapshot | None:
        """Refresh and cache complete records for current living agents."""

        return self._agent_array.refresh_living_agents(perf_counter)

    def get_living_agent(
        self,
        agent_id: int,
        refresh: bool = False,
        perf_counter: PerfCounter | None = None,
    ) -> AgentLivingStruct | None:
        """Return one complete living record from the local snapshot cache."""

        return self._agent_array.get_living_agent(agent_id, refresh, perf_counter)

    @property
    def cinematic(self) -> Cinematic:
        """Return the external cinematic reader for this client."""

        return self._cinematic

    def read_cinematic_context(self) -> CinematicStruct | None:
        """Read and return the current cinematic snapshot, if present."""

        return self._cinematic.read()

    def read_char_context(self) -> CharContextStruct:
        """Read and return the current complete CharContext snapshot."""

        return self._context.read()

    def character_name(self) -> str | None:
        """Return the live character name, or ``None`` at the selection menu."""

        try:
            name = self._context.read_player_name().strip()
        except (OSError, RuntimeError):
            return None
        return name or None

    @property
    def is_connected(self) -> bool:
        """Return whether this client has an open read-only connection."""

        return not self._reader.is_closed

    @property
    def is_logged_in(self) -> bool:
        """Return whether this connected client has a logged-in character."""

        return self._context.is_logged_in

    def close(self) -> None:
        """Close the read-only process handle owned by this connection."""

        self._reader.close()

    def __enter__(self) -> ConnectedClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _resolve_process(self, process: dict[str, Any] | int) -> dict[str, Any]:
        if isinstance(process, int):
            pid = process
            for candidate in self._win32.find_guild_wars():
                if int(candidate["pid"]) == pid:
                    return candidate
            raise ValueError(f"PID {pid} is not a running Guild Wars client.")
        pid = int(process["pid"])
        if pid <= 0:
            raise ValueError("The selected process PID must be positive.")
        return dict(process)


_current_client: ConnectedClient | None = None


def connect(process: dict[str, Any] | int) -> ConnectedClient:
    """Select one Guild Wars client and make it the current connection."""

    global _current_client
    disconnect()
    _current_client = ConnectedClient(process)
    return _current_client


def disconnect() -> None:
    """Close and clear the current selected client, if one exists."""

    global _current_client
    if _current_client is not None:
        _current_client.close()
        _current_client = None


def current_client() -> ConnectedClient | None:
    """Return the current selected client, if one has been connected."""

    return _current_client
