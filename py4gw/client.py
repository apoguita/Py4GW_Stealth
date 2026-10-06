"""Simple external connection objects for selected Guild Wars clients."""

from __future__ import annotations

import struct
from dataclasses import dataclass
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
    SkillConstantArray,
    SkillStruct,
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
    AgentGadgetStruct,
    AgentItemStruct,
    AgentLivingStruct,
    AgentStruct,
)
from .memory import MemoryManager, ProcessMemoryReader
from .native_src.base.perf_counter import PerfCounter
from .scanner import PatternCatalog, RemoteScanner
from .ui import CurrentTooltip, FrameArray, FrameTree, TooltipInfoStruct
from .win32 import Win32
from .win32.write_access import WriteAccess
from .game_thread.bridge import Bridge
from .game_thread.callbacks import Callbacks, EventListener
from .game_thread.hooker import (
    MINIMUM_PATCH,
    STUB_PROLOGUE,
    is_generated_stub,
    is_relative_jump,
)
from .game_thread.patcher import Patcher
from .native_src.chat import chat
from . import dialog
from .internals import string_table
from .dialog import DialogTables
from .game_thread.shared_block import (
    DESCRIPTOR_DEPTH,
    WATCH_DEPTH,
    WATCH_SIZE,
    CallForm,
    CommandRecord,
    Descriptor,
    EventKind,
    EventRecord,
    descriptor_offset,
)

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

#: The third hooked function: the client's post-process effect function, which is where the
#: alcohol level comes from. Native hooks it for exactly that (``effects.cpp:51-55``) and its
#: handler keeps the ``intensity`` argument (``effects.cpp:26-41``); the effects module holds the
#: capture, and this connection only feeds it. The displaced bytes stop after the frame setup —
#: ``push ebp; mov ebp, esp; sub esp, 8`` — because the next instruction is where the arguments
#: are read, and a trampoline replays whole instructions.
_EFFECTS_HOOK = "effects.post_process_effect_func"
_EFFECTS_HOOK_BYTES = bytes.fromhex("55 8B EC 83 EC 08")

#: The render entry whose first argument is the DX context: native's own ``OnEndScene`` keeps it as
#: ``Context::g_dx_context = ctx`` (``render.cpp:75-98``), and that variable is what
#: ``GW::render::GetViewportWidth/Height`` read (``render_methods.cpp:56-63``) — the value the frame
#: geometry divides by. The capture itself is the bridge's (``docs/TARGET_SIDE_WORK.md``).
_RENDER_HOOK = "render.end_scene_func"
#: ``push ebp; mov ebp, esp; sub esp, 0x48`` — **seven whole bytes**. The instructions after them read a
#: global and set up the stack cookie, so nothing in the displaced span is a relative branch, which is what a
#: trampoline cannot replay. Read live on 2026-09-27 with ``tests/probe_render_entry.py``: the target resolved
#: to ``0x8DFF10`` inside text and its head was ``55 8b ec 83 ec 48 a1 80 74 e0 00 33 c5 89 45 fc 56 8b 75 08``.
_RENDER_HOOK_BYTES = bytes.fromhex("55 8B EC 83 EC 48")

#: ``jmp rel32``, the first byte of an entry patch.
_JMP_REL32 = 0xE9

#: How far ahead of a resolver's answer the install looks for an entry jump another runtime placed on
#: the function the resolver walked past. The two measured on 2026-10-01 were 0xE0 and 0x90 bytes ahead
#: of the answer, and a client function is far shorter than this window (``_entry_jump_ahead``).
_ENTRY_WINDOW = 0x1000


@dataclass(frozen=True)
class _Placement:
    """Where one hooked function is patched, and what the patch replaces.

    ``displaced`` is the span the entry patch overwrites, and the restore writes exactly those bytes back.
    That is what lets this library sit **on top of another runtime's entry jump** without taking it away:
    the other runtime's five-byte jump *is* the displaced span, so it returns to the entry when this
    library disconnects, and the trampoline carries a relocated copy of it for as long as this library is
    connected (``hooker.build_trampoline``).
    """

    name: str
    target: int
    displaced: bytes
    #: Whether this patch went on top of another runtime's entry jump rather than on the client's own bytes.
    chained: bool

#: ``UIMessage::kDialogBody`` (``constants/ui.h:75``) and ``kDialogButton``
#: (``constants/ui.h:74``): the two messages the dialog module's state comes from.
#: A connection watches them and registers that module's capture, because the state
#: belongs to the dialog module — where ``dialog.cpp`` keeps it — and not here.
_DIALOG_BODY_MESSAGE = 0x100000A6
_DIALOG_BUTTON_MESSAGE = 0x100000A3
_DIALOG_MESSAGES = (_DIALOG_BODY_MESSAGE, _DIALOG_BUTTON_MESSAGE)

#: ``UIMessage::kChangeTarget`` (``constants/ui.h:39``): the client's notice that its
#: target changed. Its packet is ``ChangeTargetUIMsg``, whose **first** word is the
#: manual target id (``context/ui.h:78-85``), so the observer copies it into ``arg0``.
#:
#: Reforged's runtime keeps this one too, as ``g_current_target_id``
#: (``agent.cpp:161-165``), and that global is what its ``GetTargetId()`` returns —
#: which is why this port's ``Player.GetTargetID`` had nothing to read.
#:
#: The client reports a **change**: given the target it already has, it says nothing.
#: So the capture holds the last target the client *announced*, which is the same
#: thing the source's global holds, and it starts at zero either way.
#:
#: The dialog state is **not** here: it belongs to the dialog module, which is where
#: ``dialog.cpp`` keeps it, and this connection only feeds it (see ``py4gw/dialog.py``).
_TARGET_CHANGE_MESSAGE = 0x10000020

#: What the observer is told to watch: each message id, and the byte offset of the ``wchar_t*``
#: field that message carries — the string the observer copies out **inside the client's call**,
#: because that is the only moment it is the client's own (``docs/RESEARCH.md``, 2026-09-25).
#:
#: The offsets are the ported packet layouts: ``DialogBodyInfo {uint32 type; uint32 agent_id;
#: wchar_t* message_enc}`` puts its string third (``context/ui.h:54-58``), the client's
#: ``DialogButtonInfo {uint32 button_icon; wchar_t* message; uint32 dialog_id; uint32 skill_id}``
#: puts its second (``context/ui.h:60-65``), and ``ChangeTargetUIMsg`` names no string at all
#: (``context/ui.h:78-84``), which is what the zero says.
_WATCHED_MESSAGES = (
    (_DIALOG_BODY_MESSAGE, 8),
    (_DIALOG_BUTTON_MESSAGE, 4),
    (_TARGET_CHANGE_MESSAGE, 0),
) + chat.watch_entries()



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
        self._call_slots: dict[tuple[object, int], int] = {}
        self._target_id = 0
        #: ``GW::ui::SendUIMessage``'s address, resolved **once** and then held, the way the sources
        #: hold the pointer they resolved at init. Installing the layer resolves it before it patches
        #: that function's entry, so this is where a caller after that gets it from: resolving
        #: ``ui.send_ui_message_func`` again would be resolving a *patched* entry, and its pattern's
        #: ``to_function_start`` would walk back past the patched prologue to the function before it
        #: (``docs/RESEARCH.md``, 2026-09-26).
        self._ui_message_address = 0
        #: What the install found at each hooked function: where it patched, what it replaced, and whether
        #: that was another runtime's entry jump. Read back by :attr:`chained_hooks`.
        self._placements: dict[str, _Placement] = {}
        self._chained_hooks: tuple[str, ...] = ()

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
            self._dialog_tables = DialogTables(self._scanner)
            self._memory_manager = MemoryManager(
                self._reader,
                self._scanner,
                patterns,
            )
            self._memory_manager.Scan()
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
                cache_context_validator=self._agent_array_cache_contexts_are_valid,
            )
            self._agent_array.initialize()
            self._skill_constants = SkillConstantArray(
                self._reader,
                self._scanner,
                patterns,
            )
            self._skill_constants.initialize()
            self._current_tooltip = CurrentTooltip(
                self._reader,
                self._scanner,
                patterns,
            )
            self._current_tooltip.initialize()
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
            # The string table is loaded here, once, for the same reason and in the same shape as
            # the sources load it: Reforged's first frame refreshes the ``TextParser`` context, and
            # that refresh loads the table (``TextContext.py:152-155``) — so by the time any name is
            # asked for, ``string_table.decode`` is a dictionary hit. This port has no frame loop,
            # so its startup is the connection. Without this call the load happens *inside* the
            # first ``Agent.GetNameByID``: one synchronous GW.dat chain per file slot in the middle
            # of a name read, and another attempt on every later read while it has not succeeded.
            # Measured live on 2026-09-26 — see ``docs/RESEARCH.md``.
            TextParser._update_ptr()

    def _install_game_thread(self) -> None:
        """Hook the game thread and the message sender, and start listening.

        The two targets are resolved from the catalog and their entry bytes
        checked *before* anything is written, so a client that changed underneath
        us is refused rather than patched at the wrong place. A patch left by a
        controller that died is repaired first, because refusing there would make
        the only recovery a client restart.
        """

        global _current_client

        # The effects module owns the alcohol capture the same way the dialog module owns the
        # dialog's state, so its watch list — the levels native's handler stores — comes from there.
        from . import effect as effect_module

        hook_target, hook_anchor = self._resolve_placement(_GAME_THREAD_HOOK)
        observe_target, observe_anchor = self._resolve_placement(_GAME_THREAD_OBSERVE)
        effects_target, effects_anchor = self._resolve_placement(_EFFECTS_HOOK)
        render_target, render_anchor = self._resolve_placement(_RENDER_HOOK)

        access = WriteAccess(self._pid)
        try:
            self._suspended_threads = self._count_suspended_threads(access)
            # One placement per hooked function: where the patch goes, and what it replaces. On a client
            # that already has Reforged injected, three of the four answers are not the resolver's
            # address — and the bytes they replace are Reforged's own entry jump, which the restore puts
            # back. See :meth:`_prepare_target`.
            placements = {
                name: self._prepare_target(access, name, address, expected, anchor)
                for name, address, expected, anchor in (
                    (_GAME_THREAD_HOOK, hook_target, _GAME_THREAD_HOOK_BYTES, hook_anchor),
                    (
                        _GAME_THREAD_OBSERVE,
                        observe_target,
                        _GAME_THREAD_OBSERVE_BYTES,
                        observe_anchor,
                    ),
                    (_EFFECTS_HOOK, effects_target, _EFFECTS_HOOK_BYTES, effects_anchor),
                    (_RENDER_HOOK, render_target, _RENDER_HOOK_BYTES, render_anchor),
                )
            }
            # Held from here on: this is the address resolved *before* the entry is patched, which is
            # what a caller of :meth:`send_ui_message` must use afterwards. A chained placement moves the
            # target, so it is taken from the placement rather than from the resolver's answer.
            self._ui_message_address = placements[_GAME_THREAD_OBSERVE].target

            bridge = Bridge(access, self._pid)
            bridge.install(
                placements[_GAME_THREAD_HOOK].target,
                placements[_GAME_THREAD_HOOK].displaced,
                calls={},
                module_base=self._module_base,
                module_size=self._module_size,
                loaded_modules=self._loaded_module_ranges(),
                watch=_WATCHED_MESSAGES,
                observing=(
                    placements[_GAME_THREAD_OBSERVE].target,
                    placements[_GAME_THREAD_OBSERVE].displaced,
                ),
                effects_observing=(
                    placements[_EFFECTS_HOOK].target,
                    placements[_EFFECTS_HOOK].displaced,
                ),
                effects_watch=effect_module._WATCHED_INTENSITIES,
                capturing=(
                    placements[_RENDER_HOOK].target,
                    placements[_RENDER_HOOK].displaced,
                ),
            )
        except BaseException:
            access.close()
            raise

        self._chained_hooks = tuple(
            name for name, placement in placements.items() if placement.chained
        )
        self._placements = placements

        self._access = access
        self._bridge = bridge
        self._callbacks = Callbacks(bridge)
        # The dialog module keeps its own state, so it is initialised here and it is the
        # module's capture that fills it — the connection only feeds it. ``Initialize`` also
        # takes the map gate from the live map, which is what keeps the first dialog message
        # from being dropped as if a map transition were in progress.
        #
        # That read reaches the client through the current-client registry, so the connection
        # becomes current *before* the startup that reads it. Native has no such step: its
        # runtime is in-process and ``Initialize`` reads the map directly. Measured live on
        # 2026-09-25 with the publish left to :func:`connect`: ``Initialize`` found no client,
        # took the gate as suspended on an observed map of ``0 / False``, and the first dialog
        # the client announced — body and both buttons inside 1.5 ms — was refused whole,
        # which left both journals empty while the dialog itself was open in the client.
        _current_client = self
        try:
            dialog.Dialog.initialize()
            self._callbacks.register(EventKind.UI_MESSAGE, dialog._capture_message)
            self._callbacks.register(EventKind.UI_MESSAGE, self._capture_target)
            # The client's decoder calling back is what finishes a dialog string, so the
            # module's completion for it is registered like its message capture — native
            # registers its own callbacks in the same step (``dialog.cpp:1266-1295``).
            self._callbacks.register(EventKind.STRING_DECODED, dialog._on_string_decoded)
            # An agent's name is decoded by the client too (``Agent.GetNameByID``, Native's
            # ``AsyncGetAgentName`` route), but it takes its text from **its own slot's state** rather
            # than from ``STRING_DECODED``: measured live, a decode taken on that event reads empty
            # while the same slot read by state answers the text, and the dialog's strings own that
            # event. Only the module's state has to be reset here.
            from . import agent as agent_module

            agent_module._reset_name_state()

            # The camera's two patches belong to one client and one build the same way: their
            # addresses and bytes are forgotten here, which is what Native's camera ``Exit`` does
            # (``camera.cpp:28-33``).
            from . import camera as camera_module

            camera_module._reset_patch_state()

            # The alcohol level is native's captured word, so the capture is registered where
            # native registers its handler: on the client's post-process function, which is the
            # third hooked function above (``effects.cpp:26-41,51-55``). Its own event kind carries
            # the captured intensity, so no other module's handlers see it.
            effect_module._reset_alcohol_state()
            self._callbacks.register(
                EventKind.EFFECT_INTENSITY, effect_module._on_post_process_effect
            )
            # The chat history is kept the same way native's chat module watches the log message
            # (``chat.cpp:205``): the connection watches ``kWriteToChatLog`` and the module decodes
            # each line as it is announced, so the history exists without anyone asking for it.
            chat.reset_live_history()
            self._callbacks.register(EventKind.UI_MESSAGE, chat._on_chat_log_line)
            self._callbacks.register(EventKind.STRING_DECODED, chat._on_string_decoded)
            # The listeners come up last, which is where the source puts them: native's
            # ``listeners::Initialize`` is wired into its bootstrap *after* the GW layer is ready
            # (``listeners.h:94-96``), because a listener installs itself onto that layer. The
            # merchant listener is the one that exists here, and installing it replaces five of the
            # client's own packet handlers (``listeners.cpp:96-128``) — so it is a write, it is
            # undone by :meth:`close`, and it is registered before the listener thread starts so no
            # packet can arrive with nothing listening for it.
            from . import listeners as listeners_module

            listeners_module.Initialize()
            self._listener = EventListener(bridge, self._callbacks)
            self._listener.start()
        except BaseException as error:
            # A connection that could not start is not a connection anything may read
            # through, so it gives back what it placed and stops being the current one before it is
            # raised. The teardown is the same one :meth:`close` performs, and it runs while this
            # is still the current client because the modules that put things back are reached
            # through it. A teardown that fails is reported *beside* the failure that caused it
            # rather than instead of it.
            try:
                self.close()
            except BaseException as teardown_error:  # noqa: BLE001 - reported with the first failure
                error.add_note(
                    f"tearing the failed connection down also failed: {teardown_error}"
                )
            _current_client = None
            raise

    def _loaded_module_ranges(self) -> tuple[tuple[int, int], ...]:
        """Return every module loaded in the client, as ``(base, size)``.

        The bridge hands these to the packet hooks, which have to tell another runtime's compiled handler
        from a controller's own generated stub — both sit outside the client's module, and only one of them
        is code that is still there. A client whose modules cannot be enumerated answers an empty tuple,
        which makes the packet hooks refuse a foreign handler rather than chain to it, so the failure falls
        on the safe side of that question.
        """

        try:
            modules = self._win32.list_modules(self._pid)
        except OSError:
            return ()
        return tuple(
            (int(module["base_address"]), int(module["size"]))
            for module in modules
            if module["base_address"] and module["size"]
        )

    def _capture_target(self, event: EventRecord) -> None:
        """Note the last target the client announced.

        The port of ``g_current_target_id``, which Reforged's runtime keeps from this
        same message and its ``GetTargetId()`` returns (``agent.cpp:161-165``). The
        packet's first word is the manual target id.

        This one stays on the connection because nothing else owns it: the source
        keeps it in the agent module, and this project has no agent module yet — the
        same reason ``Player.GetTargetID`` reads it from here rather than from a
        context. When the state does have a module of its own, it belongs there.
        """

        if event.sequence != _TARGET_CHANGE_MESSAGE:
            return
        self._target_id = int(event.arg0)

    def _resolve(self, name: str) -> int:
        """Resolve one address the way every other read in this project does."""

        result = self._patterns.resolve(name, self._scanner)
        if not result.ok:
            raise RuntimeError(
                f"pid {self._pid}: {name} did not resolve: {result.message}"
            )
        return int(result.value)

    def resolves(self, name: str) -> bool:
        """Return whether one catalog name resolves, without calling it.

        The port of the injected runtime's ``EnsureHooks`` step: the sources resolve a
        function once and hold the pointer, and a member that needs it answers "not there"
        rather than calling a null pointer. Here the same question is asked of the pattern
        catalog, and the caller decides what a missing function means for it.
        """

        return self._patterns.resolve(name, self._scanner).ok

    def _prepare_target(
        self,
        access: WriteAccess,
        name: str,
        address: int,
        expected: bytes,
        anchor: int | None = None,
    ) -> _Placement:
        """Return where this hooked function is patched, and what the patch replaces.

        Four answers, in this order, and the first one that applies is the answer:

        1. **The entry holds the bytes this catalog declares** — the ordinary case. The placement is the
           address the resolver gave, and the patch replaces those bytes, which the caller then restores.
        2. **The entry holds this library's own stale patch**, from a controller that died: the jump lands
           on code that begins with the stub prologue (:func:`hooker.is_generated_stub`). The client's own
           bytes go back through the patcher, and the placement is the ordinary one.
        3. **The entry holds another runtime's entry patch, and it is verifiably the declared function** —
           a five-byte ``jmp rel32`` (MinHook's own shape, ``hook.c:355``). The placement is **on top of
           that jump**: the patch replaces the five bytes, and the trampoline *relocates* the jump it
           displaced (``hooker.build_trampoline``) so the other runtime keeps running underneath. This is
           the arrangement that matters, because Reforged is injected before this library, not after. The
           other runtime's jump goes back on disconnect, byte for byte, because
           :class:`~py4gw.game_thread.patcher.Patcher` restores exactly what it displaced.
        4. **The resolver answered the function *before* the declared one**, because another runtime's
           patch removed the ``55 8B EC`` prologue that ``to_function_start`` looks for. The window ahead
           is walked for an entry jump, bounded by ``anchor`` — the address the pattern matched, which is
           *inside* the declared function — and the candidate has to carry the declared entry's tail.

        **What makes a jump "verifiably the declared function" differs by how the address was obtained, and
        the resolver's own steps decide it** (:meth:`_resolve_placement`):

        - ``game_thread``'s and ``effects``' resolvers are one ``scan`` with a fixed offset and no
          walk-back, so their answer is the catalog's own answer: a jump *at* it is on the declared
          function by construction, and no tail is needed.
        - ``ui``'s and ``render``'s end in ``to_function_start``, so their answer may be the function
          before; there the walk supplies the address, the anchor bounds it, and the tail from offset five
          is the second fact — four bytes for the nine-byte entries, one for the six-byte ones, which is
          why the bound matters as much as the tail.

        **It refuses rather than guesses**, and a refusal writes nothing: a jump with no tail in a walked
        answer, a jump outside the anchor, or a foreign patch of another shape (relocating it needs a
        decoder this module deliberately does not have).

        **The resolver's recovery is this project's own, and it used to live in the resolver.**
        ``Scanner::ToFunctionStart`` walks back to a prologue (``scanner.cpp:205-210``), so an entry this
        library patched is *invisible* to it: the prologue is gone, and the walk answers the function
        before it. The port used to paper over that inside ``to_function_start`` by also treating a ``jmp``
        that leaves the module as an entry — an inference that cannot be checked without decoding, and that
        answered an address in the middle of an instruction for ``chat.send_chat_func`` on this build,
        which is the crash of 2026-09-25 (``tools/resolve_offline.py``). The walk is the source's again;
        the recovery is here, where the address's expected bytes are known, so the restore can be
        *verified* rather than guessed.
        """

        current = access.read(address, len(expected))
        if current == expected:
            return _Placement(name, address, expected, chained=False)

        if current[0] == _JMP_REL32 and self._is_our_stale_patch(access, address, current):
            Patcher(access, self._pid).patch(address, current, expected)
            return _Placement(name, address, expected, chained=False)

        if self._is_foreign_patch_on_the_declared_function(
            current, expected, anchor, found_by_the_walk=False
        ):
            return _Placement(name, address, current[:MINIMUM_PATCH], chained=True)

        # The resolver may have answered the function *before* the one this catalog declares, because its
        # walk-back looks for a prologue another runtime's patch has replaced. The window ahead is walked
        # for an entry jump, bounded by the address the pattern matched, and the landing says whose it is.
        ahead = self._entry_jump_ahead(
            access, address, len(expected), limit=anchor or 0
        )
        if ahead is not None:
            patch_address, is_ours = ahead
            patch_head = access.read(patch_address, len(expected))
            if is_ours:
                Patcher(access, self._pid).patch(patch_address, patch_head, expected)
                return _Placement(name, patch_address, expected, chained=False)
            if self._is_foreign_patch_on_the_declared_function(
                patch_head, expected, anchor, found_by_the_walk=True
            ):
                return _Placement(
                    name, patch_address, patch_head[:MINIMUM_PATCH], chained=True
                )
            raise RuntimeError(
                self._foreign_patch_refusal(
                    name, patch_address, patch_head, expected, resolved_at=address
                )
            )

        if current[0] == _JMP_REL32:
            raise RuntimeError(
                self._foreign_patch_refusal(name, address, current, expected)
            )

        raise RuntimeError(
            f"pid {self._pid}: {name} at 0x{address:08X} starts with {current.hex(' ')}, not "
            f"{expected.hex(' ')}, and no entry jump was found in the {_ENTRY_WINDOW:#x} bytes "
            "ahead of it either, so this address does not hold the function this build's catalog "
            "declares and the resolver's walk-back did not answer one either. Nothing was written."
        )

    def _resolve_placement(self, name: str) -> tuple[int, int | None]:
        """Return an address a name resolves to, and the address its resolver walked back from.

        The second value is ``None`` when the resolver's steps do **not** end in ``to_function_start`` —
        then the address is the catalog's own answer, computed from a pattern's own offset. When they do,
        the pattern's matched address is *inside* the declared function and the answer is somewhere before
        it, which is exactly what makes the returned address a bound on where the entry can be.

        Why this matters live: with Reforged injected, ``ui.send_ui_message_func`` resolved to
        ``0x01184510`` and ``render.end_scene_func`` to ``0x012202C0``, while the declared functions are
        ``0x011845F0`` and ``0x01220350`` — the walk-back had answered the function before each, because
        the prologue it looks for was replaced by Reforged's own entry patch.
        """

        result = self._patterns.resolve(name, self._scanner)
        if not result.ok:
            raise RuntimeError(
                f"pid {self._pid}: {name} did not resolve: {result.message}"
            )
        walked_back_from: int | None = None
        for step in result.trace:
            if step.operation == "to_function_start":
                # The last such step wins: its input is what the pattern matched, and its output is the
                # answer this project is being handed.
                walked_back_from = int(step.input_value)
        return int(result.value), walked_back_from

    def _is_foreign_patch_on_the_declared_function(
        self,
        head: bytes,
        expected: bytes,
        anchor: int | None,
        found_by_the_walk: bool,
    ) -> bool:
        """Whether a jump at an entry is another runtime's patch **on the function this catalog declares**.

        The address's provenance decides how much the bytes have to say:

        - found in place, with no walk-back in the resolver (``anchor is None``): the address is the
          catalog's own answer, so a five-byte ``jmp rel32`` there is a hook on the declared function and
          the tail adds nothing — ``game_thread`` and ``effects`` are this shape, and both of them resolve
          to their patched entry on the measured client;
        - found in place with a walk-back, or found ahead of the answer by the walk: the tail from offset
          five has to be the declared entry's own tail, which is what rules out a jump that happens to sit
          at an address the walk reached. With ``anchor`` set the walk also never looks past the address
          the pattern matched, so a one-byte tail (a six-byte entry) is a second fact rather than the only
          one.
        """

        if not is_relative_jump(head[:MINIMUM_PATCH]):
            return False
        if anchor is None and not found_by_the_walk:
            return True
        return self._jump_covers_part_of_declared_entry(head, expected)

    def _foreign_patch_refusal(
        self,
        name: str,
        patch_address: int,
        head: bytes,
        expected: bytes,
        resolved_at: int = 0,
    ) -> str:
        """Describe a patch this library will not place itself on, and refuse to write over it.

        Everything in the message is read from the client, so it says what was observed rather than what
        was assumed: the address that carries the patch, where its jump lands, and — when the resolver
        answered some other address — that the walk-back is why. It is reached only when the placement
        rules above do not apply: the bytes after the jump do not match the catalog's entry, so this
        library cannot tell which function it would be patching, or the patch is not a shape whose
        relocation it can do.
        """

        landing = (patch_address + 5 + struct.unpack_from("<i", head, 1)[0]) & 0xFFFFFFFF
        where = ""
        if resolved_at and resolved_at != patch_address:
            where = (
                f" (the resolver answered 0x{resolved_at:08X}, the function before it, because the "
                "prologue its walk-back looks for is gone)"
            )
        return (
            f"pid {self._pid}: {name}: the first bytes at 0x{patch_address:08X}{where} are another "
            f"runtime's entry jump to 0x{landing:08X}, and the bytes that follow it do not match this "
            "catalog's declared entry, so this library cannot tell which function that jump is on and "
            "will not write over it. Nothing was written. Unload the other runtime (Reforged) before "
            "connecting, or check this build's catalog against the client."
        )

    def _jump_covers_part_of_declared_entry(self, head: bytes, expected: bytes) -> bool:
        """Whether ``head`` is a jump followed by the rest of the entry this catalog declares.

        MinHook writes exactly five bytes at an entry (``third_party/minhook/src/hook.c:355``, its
        ``sizeof(JMP_REL)``), so a function hooked that way still shows the declared entry's own bytes
        from offset five on. That is checkable without decoding an instruction, and it is evidence about
        *which* function carries the patch.
        """

        return (
            len(expected) > 5
            and head[:1] == bytes((_JMP_REL32,))
            and head[5 : len(expected)] == expected[5:]
        )

    def _is_our_stale_patch(self, access: WriteAccess, address: int, head: bytes) -> bool:
        """Whether the ``jmp rel32`` at ``address`` is this library's own, from a controller that died.

        **"It leaves the module" was never proof, and the injected Reforged runtime is the
        counterexample.** Reforged Native is a DLL that hooks the same client functions this library
        hooks, through MinHook; its detour and the relay its entry patch jumps to live in *its* module,
        which is outside ``Gw.exe``'s — so by the old test a live foreign hook and a stale patch of
        ours looked identical, and the repair below would write the client's original bytes over the
        other runtime's hook. It would not crash anything, it would silently stop that runtime's
        callbacks while it still believed it was installed, which is the failure this method exists to
        prevent. See ``docs/NATIVE_EXECUTION_PLAN.md``, "Coexisting with the injected Reforged
        runtime".

        What *is* evidence is where the jump lands. Every stub this library places at a client
        function's entry is emitted by :mod:`py4gw.game_thread.hooker` and begins with the same three
        bytes — ``pushfd``, ``pushad``, ``mov eax, imm32`` (``hooker.STUB_PROLOGUE``) — because both
        stub forms do. A detour compiled into another module does not begin that way, and MinHook's own
        entry patch begins with a bare ``jmp rel32``, so the byte at the destination is not the first
        byte of one of our stubs either. A destination that does not read back as this library's code
        is refused by the caller rather than repaired.
        """

        destination = (address + 5 + struct.unpack_from("<i", head, 1)[0]) & 0xFFFFFFFF
        try:
            found = access.read(destination, len(STUB_PROLOGUE))
        except OSError:
            return False
        return is_generated_stub(found)

    def _leaves_the_module(self, address: int, head: bytes) -> bool:
        """Whether the ``jmp rel32`` at ``address`` lands outside the client's module.

        This is no longer what decides whether a patch is ours — :meth:`_is_our_stale_patch` is — but
        the stale-patch walk still uses it to pick its candidates, so it stays.
        """

        destination = (address + 5 + struct.unpack_from("<i", head, 1)[0]) & 0xFFFFFFFF
        return not (
            self._module_base <= destination < self._module_base + self._module_size
        )

    def _entry_jump_ahead(
        self,
        access: WriteAccess,
        address: int,
        size: int,
        window: int = _ENTRY_WINDOW,
        limit: int = 0,
    ) -> tuple[int, bool] | None:
        """Find the entry jump the resolver's walk-back hid, and say whose it is.

        ``Scanner::ToFunctionStart`` walks back to a ``55 8B EC`` prologue (``scanner.cpp:205-210``), so
        when anything at all has replaced a function's first bytes the walk answers the function
        **before** it. That is this project's own stale patch — the case this walk was written for — and
        it is equally what another runtime's entry patch does. Measured live on 2026-10-01 against a
        client with Reforged injected: ``ui.send_ui_message_func`` was answered as ``0x1184510``, whose
        bytes are a plain prologue, while the declared function is ``0x11845F0`` — ``E9 36 A8 77 56``
        followed by ``08 83 F8 56``, which is the tail of the declared entry — and
        ``render.end_scene_func`` likewise answered ``0x12202C0`` where the declared function is
        ``0x1220350``. Both jumps land in ``Py4GW.dll``.

        **"Leaves the module" selects candidates; it does not decide.** Ordinary control flow inside a
        function is a jump too, and one that lands inside ``Gw.exe`` is not an entry patch — the two
        measured clients' functions are full of those. So a candidate has to leave the module to be
        considered at all, and the caller then asks :meth:`_is_our_stale_patch` whose code it lands on:
        this library's own means repair, anything else means refuse and name it.

        Returns ``(patch_address, is_ours)`` for the first candidate, or ``None`` when there is none.
        ``limit`` bounds the search: when the resolver walked back to its answer, the address the pattern
        matched is *inside* the declared function, so the entry cannot be past it, and looking further
        would only find jumps belonging to later functions.
        """

        end = min(address + window, self._module_base + self._module_size)
        if limit:
            end = min(end, limit)
        try:
            window_bytes = access.read(address, end - address)
        except OSError:
            return None
        for offset in range(0, max(0, len(window_bytes) - size + 1)):
            if window_bytes[offset] != _JMP_REL32:
                continue
            candidate = address + offset
            head = window_bytes[offset : offset + size]
            if len(head) < 5:
                break
            if not self._leaves_the_module(candidate, head):
                continue
            return candidate, self._is_our_stale_patch(access, candidate, head)
        return None


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

    @property
    def target_id(self) -> int:
        """Return the last target the client announced, or ``0`` for none.

        The port of Reforged's ``g_current_target_id``: the runtime keeps it from the
        client's own ``kChangeTarget`` notice (``agent.cpp:161-165``) and
        ``GetTargetId()`` returns it. Kept up to date by the listener while the
        connection is open, so a script reads it after the client has said what its
        target is rather than by asking the client directly.

        The client reports **changes**, so this is the last id it named: ``0`` before
        the first change and after clearing, which is what the source's global holds
        in both cases.
        """

        if self._callbacks is None:
            raise RuntimeError(
                "this connection was opened without the game thread: pass "
                "game_thread=True to connect so the client's target changes can be "
                "captured."
            )
        return self._target_id

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

    def call_function(
        self,
        name: str,
        form: CallForm,
        arg1: int = 0,
        arg2: int = 0,
        arg3: int = 0,
        arg4: int = 0,
        arg5: int = 0,
        timeout_ms: int | None = None,
    ) -> CommandRecord:
        """Call one catalog function on the client's own thread, and wait for it.

        ``name`` is a resolver name from ``offsets/`` and ``form`` says how the
        words become its arguments, which is Native's own pairing: an address from the
        pattern catalog plus a prototype that says how to call it. The slot is
        allocated on first use and the address resolved once, so a member that calls
        the same function repeatedly resolves it once — the same rule the readers
        follow for anything a pattern produced.

        The form decides how many of the five words the callee takes, so a form with
        fewer arguments ignores the words it has no parameter for.

        The dispatcher refuses a target outside the client module before it calls
        anything, so a resolver that went wrong fails rather than jumping.
        """

        if form is CallForm.UI_MESSAGE:
            raise ValueError(
                "call_function drives the typed forms; a UI message carries a "
                "packed payload and is published with publish_call instead."
            )

        slot = self._descriptor_slot((name, int(form)), self._resolve(name), form)
        return self.bridge.call(slot, arg1, arg2, arg3, arg4, arg5, timeout_ms)

    def call_address(
        self,
        target: int,
        form: CallForm,
        arg1: int = 0,
        arg2: int = 0,
        arg3: int = 0,
        arg4: int = 0,
        arg5: int = 0,
        timeout_ms: int | None = None,
    ) -> CommandRecord:
        """Call one already-resolved address on the client's own thread, and wait for it.

        The source reaches a few functions through a pointer it resolved rather than through a
        name in a catalog. The dialog loader is one: its address is a hardcoded client virtual
        address rebased onto the module (``dialog.h:94-99``, ``dialog_patterns.cpp``), not a
        signature match, so there is no catalog name to resolve and none is invented here — the
        caller resolved the address, which is what the source's own
        ``SafeCallDialogLoader_GetText`` does with the pointer it holds.

        Everything else is the same contract as :meth:`call_function`: a descriptor slot per
        (target, form), and the dispatcher bounds the target to the client's module before it
        calls anything.
        """

        if form is CallForm.UI_MESSAGE:
            raise ValueError(
                "call_address drives the typed forms; a UI message carries a "
                "packed payload and is published with publish_call instead."
            )

        slot = self._descriptor_slot((int(target), int(form)), int(target), form)
        return self.bridge.call(slot, arg1, arg2, arg3, arg4, arg5, timeout_ms)

    def send_ui_message(
        self, message_id: int, wparam: int = 0, lparam: int = 0
    ) -> CommandRecord:
        """Send one UI message through the client's own entry point.

        ``GW::ui::SendUIMessage(UIMessage message, void* wparam = nullptr, void* lparam =
        nullptr)`` (``ui_methods.cpp:1390-1404``) is how the client is told anything, and the
        sources call it through a pointer they resolve **once**, at init. So does this: the address
        is the one the connection resolved while installing the layer
        (``ui.send_ui_message_func``, which is also the function this project observes messages
        with), and it is held rather than resolved again. Resolving it again would run that
        pattern's ``to_function_start`` against a **patched** entry — the port's hook is a jump at
        its first byte — where the walk back for a prologue answers the function *before* it, an
        address inside ``.text`` that the module bound cannot refuse (``docs/RESEARCH.md``,
        2026-09-26).

        The form is the packed one: the emitted dispatcher builds a zeroed two-word payload from
        the command's second and third words and calls ``SendUIMessage(arg1, &payload, 0)``, so
        ``message_id`` is the first argument, ``wparam`` the second and ``lparam`` the third. A
        caller places that payload in the block's data region first, because the source hands the
        client a pointer to a struct. ``chat.WriteChatEnc`` is the first caller
        (``chat_methods.cpp:197``: ``ui::SendUIMessage(kWriteToChatLog, &param)``).
        """

        address = self._ui_message_address or self._resolve(_GAME_THREAD_OBSERVE)
        slot = self._descriptor_slot(
            (address, int(CallForm.UI_MESSAGE)), address, CallForm.UI_MESSAGE
        )
        return self.bridge.call(slot, message_id, wparam, lparam)

    def send_ui_message_raw(
        self, message_id: int, wparam: int = 0, lparam: int = 0
    ) -> CommandRecord:
        """Call the client's own message sender with the caller's two words, unwrapped.

        ``GW::ui::SendUIMessage(UIMessage, void* wparam, void* lparam)`` is a three-word ``__cdecl``
        (``ui_patterns.cpp:31``, Native's ``SendUIMessageFn``), and this is that call with nothing in
        between: the id and the two words the caller named, sent as they are.
        :meth:`send_ui_message` is the **packed** form — it builds a zeroed sixteen-word payload from
        its two words and passes that payload's address as ``wparam``, which is what
        ``SendUIMessagePacked`` does (``ui_bindings.cpp:60-74``). So a caller that already holds the
        pointer the client should receive — a struct in the block's data region, or a bare word the
        client interprets — needs this one. That is what ``PyUIManager.UIManager.SendUIMessageRaw``
        does with its own two words, and what ``SendUIMessage`` does with a payload of its own making.

        The address is the one the connection holds, for the reason :meth:`send_ui_message` gives:
        it is the entry this project's observer is installed at, so the call travels through the hook
        and the trampoline reaches the client's own body. Re-resolving it is not an option — the
        entry is patched, and a second scan answers the function *before* it.
        """

        address = self._ui_message_address or self._resolve(_GAME_THREAD_OBSERVE)
        slot = self._descriptor_slot(
            (address, int(CallForm.U32_U32_U32)), address, CallForm.U32_U32_U32
        )
        return self.bridge.call(slot, message_id, wparam, lparam)

    def _descriptor_slot(
        self, key: tuple[object, int], target: int, form: CallForm
    ) -> int:
        """Return the call-table slot for one target and form, writing it on first use.

        The connection installs the table empty, so the next free slot is the number of
        descriptors already written into it, and a slot is written once per distinct
        (target, form) pair — whether the target came from a catalog name or was resolved by
        the caller.

        **The target must be code, and that check is made here.** The dispatcher refuses a
        target outside the client's module, which is not the same thing: an address inside the
        module but outside its code section is data, and executing it does not fail — it runs
        whatever bytes are there. On 2026-09-25 that is exactly what happened: the resolver for
        ``chat.send_chat_func`` answered with an address that was not code, the dispatcher's
        module bound passed it, and the client died at ``eip=462fd617`` with this project's
        command record and its chat buffer in the registers. So the section is confirmed here,
        where the address is still the host's to refuse, and the refusal names the address, the
        section and what was expected — the dispatcher cannot do this, because inside the client
        an address that is about to be executed is not distinguishable from one that is not.
        """

        slot = self._call_slots.get(key)
        if slot is not None:
            return slot

        text = self._scanner.get_section_range("text")
        if not text.start <= target < text.end:
            raise RuntimeError(
                f"pid {self._pid}: refusing to call 0x{target:08X} for {key[0]!r}: it is not "
                f"inside the client's code section (0x{text.start:08X}..0x{text.end:08X}), so "
                "executing it would run data. A resolver answered with an address that is not "
                "a function."
            )

        if len(self._call_slots) >= DESCRIPTOR_DEPTH:
            raise RuntimeError(
                f"pid {self._pid}: the call table holds {DESCRIPTOR_DEPTH} "
                "descriptors and every slot is taken."
            )
        slot = len(self._call_slots)
        descriptor = Descriptor(target=target, form=form)
        self.access.write(
            self.bridge.call_table_address + descriptor_offset(slot),
            descriptor.to_bytes(),
        )
        self._call_slots[key] = slot
        return slot

    @property
    def pid(self) -> int:
        """Return the selected process ID."""

        return self._pid

    @property
    def process(self) -> dict[str, Any]:
        """Return the process record used to create this connection."""

        return dict(self._process)

    @property
    def reader(self) -> ProcessMemoryReader:
        """Return this connection's bounded read-only process-memory reader.

        The ported ``internals`` helpers read at an address a structure handed them
        (``read_wstr``); the sources do that with ``ctypes`` against their own address space
        because they run inside the client, and the external reader is what stands in for it.
        """

        return self._reader

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
    def dialog_tables(self) -> DialogTables:
        """Return the dialog metadata table resolver for this client.

        Native keeps these tables in the module's own process and reaches them through
        ``GW::dialog::GetDialogTables()``; here they are the client's, because
        resolving them is a read of this process. What the resolver does with them —
        the rebase of the source's ``DialogMemory`` constants, the validation pass, the
        ``.rdata`` fallback — is the port of ``dialog_patterns.cpp``.
        """

        return self._dialog_tables

    @property
    def frame_array(self) -> FrameArray:
        """Return this client's global UI frame array reader.

        Native's ``GW::ui::FrameArray()`` is an in-process global holding one entry per
        frame id; here it is the same structure, reached through the
        ``ui.frame_array_addr`` resolver. The frame tree reads through this array, and
        so does anything that has to find a frame by its hash.
        """

        return self._frame_array

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
    def memory_manager(self) -> MemoryManager:
        """Return the reader for the client's own memory-manager globals.

        The port of ``PY4GW::MemoryManager``. Two classes need it: the effect snapshot's
        ``time_elapsed``/``time_remaining`` and the skillbar slot's ``get_recharge`` are both
        measured against ``GetSkillTimer``.
        """

        return self._memory_manager

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
        """Return the external agent-array reader.

        The reader is the port of ``native_src/context/AgentContext.py``'s ``AgentArray`` facade.
        Its ``get_context()`` is the source's own accessor for the agent-array *view*
        (``AgentContext.py:1473-1474``), which is where the category lists and the per-id lookups
        live; this project has no frame loop, so the view is built the first time it is asked for.
        """

        return self._agent_array

    def _agent_array_cache_contexts_are_valid(self) -> bool:
        """Apply Reforged's required-context gate to the external array cache."""

        from .map import Map

        return Map.IsMapReady()

    @property
    def skill_constants(self) -> SkillConstantArray:
        """Return the external skill-constant-table reader for this client."""

        return self._skill_constants

    def read_skill(self, skill_id: int) -> SkillStruct | None:
        """Read one skill constant record, matching native ``GetSkillConstantData``.

        The table is the client's own static data (``GW::Context::GetSkillArray()``); the record is
        the 0xA4-byte ``GW::Context::Skill``, indexed by the skill id the way the client's own
        accessor indexes it. ``None`` is the source's null — native's binding leaves its fields at
        their defaults when the record is missing (``skill_bindings.cpp:134-136``).
        """

        return self._skill_constants.read(skill_id)

    @property
    def current_tooltip(self) -> CurrentTooltip:
        """Return the external current-tooltip reader for this client."""

        return self._current_tooltip

    def read_current_tooltip(self) -> TooltipInfoStruct | None:
        """Read the tooltip the client is showing, or ``None`` when there is none."""

        return self._current_tooltip.read()

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
    def chained_hooks(self) -> tuple[str, ...]:
        """Return the hooked functions this connection patched **on top of another runtime's jump**.

        Empty on a client where the four entries held their own bytes, which is the ordinary case; the
        four catalog names on a client where Reforged was already injected, which is the arrangement that
        matters in practice. Each of those placements replaces the other runtime's five-byte ``jmp rel32``,
        relocates it into this library's trampoline so that runtime keeps running underneath, and puts it
        back on disconnect — so this is a report of what the install found, not a mode a caller selects.
        """

        return self._chained_hooks

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

        # ``Shutdown`` runs **before** the listener stops, and that order is the source's: the
        # dialog module's drain waits for decodes the client is still running, and those are
        # delivered by the listener, so stopping it first would make the drain wait for something
        # that can no longer arrive. Native's own shutdown is called the same way — its callbacks
        # are still registered while it drains, and the unregistration is a step *inside* it.
        try:
            dialog.Dialog.terminate()
        except BaseException as error:
            failure = error

        # The listeners go next, and they go before the bridge: a listener's uninstall puts the
        # client's own packet handlers back, and that write runs on the game thread through the
        # hook the bridge is about to take out. Native's shutdown has the same order —
        # ``listeners::Shutdown`` disables every listener, and the StoC layer's own ``Exit`` runs
        # after it (``listeners.cpp:188-192``, ``stoc.cpp:200-208``).
        try:
            from . import listeners as listeners_module

            listeners_module.Shutdown()
        except BaseException as error:
            failure = failure or error

        listener, self._listener = self._listener, None
        if listener is not None:
            try:
                listener.stop()
            except BaseException as error:
                failure = failure or error

        # The string table's warm-up reads GW.dat through this connection, so it must be finished
        # with it before the block it reads through is released -- the same reason the listener stops
        # first. A worker left running would also leave the dat record it was reading open in the
        # client, which is the client's own `Gw.dat still open` assertion at shutdown.
        try:
            string_table._stop_warmup()
        except BaseException as error:
            failure = failure or error

        # Names asked for and never taken hold decode slots, and a block with a decode outstanding
        # cannot be freed (``Bridge.remove``): giving those slots back here is what lets the bridge
        # come out at all. A name in flight at disconnect is a caller that stopped calling.
        try:
            from . import agent as agent_module

            agent_module._reset_name_state()
        except BaseException as error:
            failure = failure or error

        # Native's ``Exit`` forgets the captured alcohol level the same way (``effects.cpp:81``),
        # and the capture's own hook is the one coming out below.
        try:
            from . import effect as effect_module

            effect_module._reset_alcohol_state()
        except BaseException as error:
            failure = failure or error

        bridge, self._bridge = self._bridge, None
        access, self._access = self._access, None
        self._callbacks = None
        self._call_slots.clear()
        self._target_id = 0
        try:
            if bridge is not None and bridge.installed:
                bridge.remove(free_allocations=True)
        finally:
            if access is not None:
                access.close()
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

    A capability-layer connection makes itself current while it is still being built,
    because its own startup reads the client through this registry
    (:meth:`ConnectedClient._install_game_thread`). This assignment is the one that
    publishes a read-only connection, which installs no capability layer and therefore
    has no startup of its own to get ahead of.
    """

    global _current_client
    disconnect()
    _current_client = ConnectedClient(process, game_thread=game_thread)
    return _current_client


def disconnect() -> None:
    """Close and clear the current selected client, if one exists.

    **The registry is cleared before the close runs**, because a close can refuse: removing a hook whose
    generated stub another runtime has patched reports and frees nothing (``hooker.Hooker.remove``), and the
    client is closed either way — the hooked functions' own bytes are back and the handle is released. If
    the raise happened first, the module would keep pointing at a closed connection and the next
    ``require_client()`` would answer a client that has nothing behind it.
    """

    global _current_client
    client, _current_client = _current_client, None
    if client is not None:
        client.close()


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
