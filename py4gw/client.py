"""Simple external connection objects for selected Guild Wars clients."""

from __future__ import annotations

import struct
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
    MissionMapContextStruct,
    MissionMapContext,
    SalvageSessionInfo,
    SalvageSessionInfoStruct,
    WorldMapContext,
    WorldMapContextStruct,
    GameplayContext,
    GameplayContextStruct,
    PreGameContext,
    PreGameContextStruct,
    ServerRegion,
    ServerRegionStruct,
    PlayerAgentId,
    PlayerAgentIdStruct,
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
from .perf_counter import PerfCounter
from .scanner import PatternCatalog, RemoteScanner
from .ui import FrameArray, FrameTree
from .win32 import Win32
from .win32.write_access import WriteAccess
from .game_thread.bridge import Bridge
from .game_thread.callbacks import Callbacks, EventListener
from .game_thread.patcher import Patcher
from .game_thread.shared_block import WATCH_DEPTH, WATCH_SIZE

#: The two client functions this library hooks when it connects. The first is the
#: game thread's own per-frame function, which is where our work runs; the second
#: is the message sender, which is what lets a handler hear what the client did.
_GAME_THREAD_HOOK = "game_thread.leave_game_thread_func"
_GAME_THREAD_OBSERVE = "ui.send_ui_message_func"

#: The whole instructions each entry patch replaces. The second stops before a
#: relative branch: the trampoline replays these bytes at another address, and a
#: branch replayed elsewhere goes somewhere else.
_GAME_THREAD_HOOK_BYTES = bytes.fromhex("55 8B EC 81 EC 20 02 00 00")
_GAME_THREAD_OBSERVE_BYTES = bytes.fromhex("55 8B EC 8B 45 08 83 F8 56")

#: ``jmp rel32``, the first byte of an entry patch.
_JMP_REL32 = 0xE9



class ConnectedClient:
    """Own the read-only resources for one selected ``Gw.exe`` process."""



    def __init__(
        self,
        process: dict[str, Any] | int,
        win32: Win32 | None = None,
        perf_counter: PerfCounter | None = None,
        game_thread: bool = True,
    ) -> None:
        """Connect to a discovered client and optionally time setup stages.

        ``perf_counter`` is only a diagnostic sink; it does not change the
        read-only connection behavior.

        ``game_thread`` is on by default, which makes connecting a **write**: this
        library hooks two of the client's functions, starts a listener thread that
        reads what they report, and hands the hooks back on :meth:`close`. It is
        off for a connection that only reads — a client-list refresh, a probe —
        where patching a client per row would be absurd.
        """

        self._win32 = win32 or Win32()
        self._process = self._resolve_process(process)
        self._pid = int(self._process["pid"])
        self._game_thread_enabled = game_thread
        self._bridge: Bridge | None = None
        self._callbacks: Callbacks | None = None
        self._listener: EventListener | None = None
        self._access: WriteAccess | None = None
        self._suspended_threads = 0

        # Elevation is asserted here, once, rather than left to surface later as a
        # bare "Windows error 5" from the first operation that needs it. The pid is
        # resolved first so the failure can name the process it refused.
        if not self._win32.is_elevated():
            raise RuntimeError(
                f"pid {self._pid}: this controller is not elevated, and connecting "
                "requires it. Windows gives an unelevated shell a filtered token "
                "and denies it PROCESS_VM_WRITE, PROCESS_VM_OPERATION, "
                "PROCESS_CREATE_THREAD and PROCESS_SUSPEND_RESUME with error 5. "
                "Those are every right this library needs beyond reading. Relaunch "
                "the shell as administrator and connect again."
            )

        module = self._win32.get_main_module(self._pid)
        self._module_base = int(module["base_address"])
        self._module_size = int(module["size"])
        self._reader = ProcessMemoryReader(self._win32, self._pid)
        try:
            self._scanner = RemoteScanner(
                self._reader,
                int(module["base_address"]),
                int(module["size"]),
            )
            self._scanner.initialize()
            patterns = PatternCatalog.from_directory("offsets")
            self._patterns = patterns
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
            self._player_agent_id = PlayerAgentId(
                self._reader,
                self._scanner,
                patterns,
            )
            self._player_agent_id.initialize()
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
                cache_context_validator=self._agent_array_cache_contexts_are_valid,
            )
            self._agent_array.initialize(perf_counter)
            self._context = CharContext(
                self._reader,
                self._scanner,
                patterns,
                game_context=self._game_context,
            )
            self._context.initialize()
            # The frame array resolver is not yet verified on a live client, so
            # it is built but not resolved here; a failure must not stop a
            # connection that every other reader still supports.
            self._frame_array = FrameArray(self._reader, self._scanner, patterns)
            # Some frames register a short jmp thunk rather than the handler a
            # signature resolves, so the walk needs the near-jump follower.
            self._frame_tree = FrameTree(
                self._frame_array, self._scanner.function_from_near_call
            )
            self._world_map_context = WorldMapContext(
                self._reader,
                self._scanner,
                patterns,
                self._frame_tree,
            )
            self._mission_map_context = MissionMapContext(
                self._reader,
                self._scanner,
                patterns,
                self._frame_tree,
            )
            self._salvage_session = SalvageSessionInfo(
                self._reader,
                self._scanner,
                patterns,
                self._frame_tree,
            )
        except Exception:
            self._reader.close()
            raise

        # Last, so a failure in the read-only setup never leaves the client
        # patched, and so the connection that reads contexts exists first.
        if self._game_thread_enabled:
            self._install_game_thread()

    def _install_game_thread(self) -> None:
        """Hook the game thread and the message sender, and start listening.

        The two targets are resolved from the catalog and their entry bytes
        checked *before* anything is written, so a client that changed underneath
        us is refused rather than patched at the wrong place. A patch left by a
        controller that died is repaired first, because refusing there would make
        the only recovery a client restart.
        """

        hook_target = self._resolve(_GAME_THREAD_HOOK)
        observe_target = self._resolve(_GAME_THREAD_OBSERVE)

        access = WriteAccess(self._pid)
        try:
            self._suspended_threads = self._count_suspended_threads(access)
            for name, address, expected in (
                (_GAME_THREAD_HOOK, hook_target, _GAME_THREAD_HOOK_BYTES),
                (_GAME_THREAD_OBSERVE, observe_target, _GAME_THREAD_OBSERVE_BYTES),
            ):
                self._prepare_target(access, name, address, expected)

            bridge = Bridge(access, self._pid)
            bridge.install(
                hook_target,
                _GAME_THREAD_HOOK_BYTES,
                calls={},
                module_base=self._module_base,
                module_size=self._module_size,
                watch=(),
                observing=(observe_target, _GAME_THREAD_OBSERVE_BYTES),
            )
        except BaseException:
            access.close()
            raise

        self._access = access
        self._bridge = bridge
        self._callbacks = Callbacks(bridge)
        self._listener = EventListener(bridge, self._callbacks)
        self._listener.start()

    def _resolve(self, name: str) -> int:
        """Resolve one address the way every other read in this project does."""

        result = self._patterns.resolve(name, self._scanner)
        if not result.ok:
            raise RuntimeError(
                f"pid {self._pid}: {name} did not resolve: {result.message}"
            )
        return int(result.value)

    def _prepare_target(
        self, access: WriteAccess, name: str, address: int, expected: bytes
    ) -> None:
        """Check a target's entry bytes, repairing this library's own stale patch.

        The patch is a relative jump; if the bytes are one whose destination is
        outside the client's module, it is ours from a controller that died, and
        the known original bytes go back. Anything else is refused: this does not
        guess at another tool's patch.
        """

        current = access.read(address, len(expected))
        if current == expected:
            return

        if current[0] == _JMP_REL32:
            destination = (
                address + 5 + struct.unpack_from("<i", current, 1)[0]
            ) & 0xFFFFFFFF
            if not (
                self._module_base <= destination < self._module_base + self._module_size
            ):
                Patcher(access, self._pid).patch(address, current, expected)
                return

        raise RuntimeError(
            f"pid {self._pid}: {name} at 0x{address:08X} starts with "
            f"{current.hex(' ')}, not {expected.hex(' ')}, and that is not a jump "
            "out of the module. Refusing to patch it."
        )

    def _count_suspended_threads(self, access: WriteAccess) -> int:
        """Count client threads that are suspended, and leave every count as it was.

        ``SuspendThread`` returns the count *before* the call, so suspending and
        resuming in a pair restores the count exactly while reporting whether a
        dead controller left the thread suspended. Nothing is resumed here: a
        thread can be suspended for the client's own reasons, and guessing wrong
        would be worse than reporting it.
        """

        suspended = 0
        for thread_id in access.list_thread_ids():
            handle = access.open_thread(thread_id)
            try:
                previous = access.suspend_thread(handle)
                access.resume_thread(handle)
            finally:
                access.close_thread(handle)
            if previous > 0:
                suspended += 1
        return suspended

    def resume_suspended_threads(self) -> int:
        """Resume the client's suspended threads once each, and say how many.

        For the one case a dead controller can leave behind: killed inside the
        window where the installer had the client's threads suspended, so its
        ``finally`` never resumed them and the client is frozen.
        """

        if self._access is None:
            raise RuntimeError("this connection is not managing the game thread.")

        resumed = 0
        for thread_id in self._access.list_thread_ids():
            handle = self._access.open_thread(thread_id)
            try:
                if self._access.suspend_thread(handle) > 0:
                    self._access.resume_thread(handle)
                    resumed += 1
                self._access.resume_thread(handle)
            finally:
                self._access.close_thread(handle)
        return resumed

    @property
    def suspended_threads(self) -> int:
        """Return how many client threads were suspended when this connected."""

        return self._suspended_threads

    @property
    def callbacks(self) -> Callbacks:
        """Return the handler registry, so a kind can be listened for."""

        if self._callbacks is None:
            raise RuntimeError(
                "this connection was opened without the game thread: pass "
                "game_thread=True to connect for callbacks."
            )
        return self._callbacks

    @property
    def bridge(self) -> Bridge:
        """Return the bridge: the queue, the hooks and everything they placed."""

        if self._bridge is None:
            raise RuntimeError(
                "this connection was opened without the game thread: pass "
                "game_thread=True to connect for the bridge."
            )
        return self._bridge

    @property
    def access(self) -> WriteAccess:
        """Return the transport this connection writes through, if it has one."""

        if self._access is None:
            raise RuntimeError(
                "this connection was opened without the game thread: pass "
                "game_thread=True to connect to hook the client."
            )
        return self._access

    def watch(self, message: int) -> int:
        """Ask the observer to record one client message id, and return its slot.

        The watch list lives in the client and the observer re-reads it on every
        call, so this takes effect immediately and needs no reinstall. A slot
        already holding the message is reused; when the list is full this refuses
        rather than dropping a watch the caller asked for.
        """

        bridge = self.bridge
        for slot in range(WATCH_DEPTH):
            held = struct.unpack(
                "<I", self.access.read(bridge.watch_address + slot * WATCH_SIZE, 4)
            )[0]
            if held == message:
                return slot
        for slot in range(WATCH_DEPTH):
            address = bridge.watch_address + slot * WATCH_SIZE
            if struct.unpack("<I", self.access.read(address, 4))[0] == 0:
                self.access.write(address, struct.pack("<I", message))
                return slot
        raise RuntimeError(
            f"the watch list holds {WATCH_DEPTH} message ids and is full."
        )

    def unwatch(self, message: int) -> None:
        """Stop recording one message id, or refuse because it was not watched."""

        bridge = self.bridge
        for slot in range(WATCH_DEPTH):
            address = bridge.watch_address + slot * WATCH_SIZE
            if struct.unpack("<I", self.access.read(address, 4))[0] == message:
                self.access.write(address, bytes(WATCH_SIZE))
                return
        raise ValueError(f"pid {self._pid}: message {message:#x} is not watched.")

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

    def read_mission_map_context(
        self, address: int | None = None, max_subcontexts: int = 100_000
    ) -> MissionMapContextStruct | None:
        """Read the mission-map context, acquiring its address when omitted.

        When ``address`` is supplied the reader uses it directly.  When it is
        omitted the address is acquired from the client's UI frame array;
        ``None`` then means no frame currently publishes the context.
        """

        if address is not None:
            return MissionMapContextStruct.read_at(
                self._reader, address, max_subcontexts
            )
        return self._mission_map_context.read(max_subcontexts)

    def read_salvage_session(self) -> SalvageSessionInfoStruct | None:
        """Read the salvage session, or ``None`` when no popup is open."""

        return self._salvage_session.read()

    @property
    def frame_tree(self) -> FrameTree:
        """Return the read-only UI frame-tree reader for this client."""

        return self._frame_tree

    @property
    def world_map_context(self) -> WorldMapContext:
        """Return the frame-array-backed WorldMapContext reader."""

        return self._world_map_context

    @property
    def mission_map_context(self) -> MissionMapContext:
        """Return the frame-array-backed MissionMapContext reader."""

        return self._mission_map_context

    @property
    def salvage_session(self) -> SalvageSessionInfo:
        """Return the frame-array-backed salvage-session reader."""

        return self._salvage_session

    def read_world_map_context(
        self, address: int | None = None
    ) -> WorldMapContextStruct | None:
        """Read the world-map context, acquiring its address when omitted.

        When ``address`` is supplied the reader uses it directly, which is how
        offline checks exercise the structure half.  When it is omitted the
        address is acquired from the client's UI frame array; ``None`` then
        means no frame currently publishes the context.
        """

        if address is not None:
            return WorldMapContextStruct.read_at(self._reader, address)
        return self._world_map_context.read()

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
    def player_agent_id(self) -> PlayerAgentId:
        """Return the external player-agent-id reader for this client."""

        return self._player_agent_id

    def read_player_agent_id(self) -> PlayerAgentIdStruct | None:
        """Read the game global holding the player's current agent id.

        The value covers both ordinary play and spectating, matching native
        ``Context::GetObservingId()``.
        """

        return self._player_agent_id.read()

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
            items.extend(bag.read_items(limit_per_bag))
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

    def _agent_array_cache_contexts_are_valid(self) -> bool:
        """Apply Reforged's required-context gate to the external array cache."""

        from .map import Map

        return Map.IsMapReady()



    def read_agent(
        self, reference: AgentReference, perf_counter: PerfCounter | None = None
    ) -> AgentStruct | AgentLivingStruct | AgentItemStruct | AgentGadgetStruct | None:
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
        """Read and return the current complete CharContext snapshot.

        """

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
        """Take the hooks out, release what they placed, and close the handle.

        The order matters. The listener stops first because it is the only reader
        of the event region and would otherwise read a block that is being
        released; then both entry patches go back, then the allocations are freed,
        and only then is the process handle closed. A handler that raised is
        re-raised at the end, after the client has been put back, so a failure in
        the caller's own code cannot leave the client patched.
        """

        failure: BaseException | None = None

        listener, self._listener = self._listener, None
        if listener is not None:
            try:
                listener.stop()
            except BaseException as error:
                failure = error

        bridge, self._bridge = self._bridge, None
        access, self._access = self._access, None
        self._callbacks = None
        try:
            if bridge is not None and bridge.installed:
                bridge.remove(free_allocations=True)
        finally:
            if access is not None:
                access.close()
            MapContext._clear_pathing_cache_for_pid(self._pid)
            self._reader.close()

        if failure is not None:
            raise failure

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


def connect(process: dict[str, Any] | int, game_thread: bool = True) -> ConnectedClient:
    """Select one Guild Wars client and make it the current connection.

    ``game_thread`` defaults to on, which makes this a write: the client's game
    thread and message sender are hooked, a listener thread starts, and both are
    given back by :func:`disconnect`. Pass ``False`` for a connection that only
    reads.
    """

    global _current_client
    disconnect()
    _current_client = ConnectedClient(process, game_thread=game_thread)
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


def require_client() -> ConnectedClient:
    """Return the current selected client, or fail because none is connected.

    The accessor every accessor class uses. Each wrapper previously carried its
    own private copy of this check, which is the same three lines restated four
    times; a missing connection is a usage error, not a per-class concern.
    """

    client = _current_client
    if client is None:
        raise RuntimeError(
            "No Guild Wars client is connected. Call py4gw.connect() first."
        )
    return client
