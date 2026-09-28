"""Port of Reforged's ``Py4GWCoreLib/UIManager.py`` — ``class UIManager`` (lines 29-618).

**Sources.** Reforged's ``Py4GWCoreLib/UIManager.py`` is 1302 lines; ``class UIManager`` is lines
**29-618** and carries **55 declarations** (``43-618``). Lines 619-1302 are **14 window classes**
(``InventoryBagWindow`` … ``AnySalvageWindow``) and are **out of scope permanently** — the owner's
criterion, verbatim: *"the class is mostly ok up until line 611 where `InventoryBagWindow` starts,
those classes we don't need."* No singleton instance, no handler class and no per-widget class is
added beside this one. The plan and the order of work are in
[`docs/UIMANAGER_PORT.md`](../../docs/UIMANAGER_PORT.md); the verdict is in
[`docs/CLASS_PORT_MAP.md`](../../docs/CLASS_PORT_MAP.md).

**The class name.** The class is ``UIManager`` in both sources — Reforged declares ``class
UIManager`` and Native binds ``py::class_<UIManagerShim>(m, "UIManager")``
(``ui_bindings.cpp:660``). ``PyUIManager`` is the *module* the injected runtime exposes it in, and
giving that name to a class here is the shape the porting rules reject (``AGENTS.md``, the
``PyDialog`` case). The owner settled the spelling and the file on 2026-09-27:
``py4gw/ui_manager.py`` holding ``class UIManager``.

**How a member is ported.** Reforged's member bodies are one-liners over
``PyUIManager.UIManager.<binding>``, and each binding is a ``.def_static`` in Native's
``ui_bindings.cpp`` over a ``GW::ui`` function in ``ui_methods.cpp``. So every member here resolves
**the function behind its binding** and calls it through this port's own call path; nothing is
re-derived, and no member exists that the sources do not have. Three shapes come out of that:

1. **A read of one client word or one client record** — the member reads the resolved address
   itself (``IsWorldMapShowing``, ``IsUIDrawn``, ``IsShiftScreenshot``, the window positions).
2. **A call on the client's own thread** — ``client.call_function(name, form, …)`` for a catalog
   function, or the same call this port already makes for a frame action.
3. **A ported body with real logic** — ``GetFrameLimit``'s branching, the preference guards,
   ``AsyncDecodeStr``'s three refusals, the encoded-string arithmetic. Those live in this port's
   ``py4gw/ui/`` modules, where the port already keeps the ``GW::ui`` functions, and the member
   calls them. The route difference (the source reaches the binding, the port reaches the function
   behind it) is recorded on each member that makes the call.

**Two binding members Native's current revision does not bind, and one it does not have.**
Reforged's ``UIManager.py`` calls 41 distinct ``PyUIManager.UIManager`` members. Measured against
``ui_bindings.cpp`` on 2026-09-27, **eleven of them have no ``.def_static`` there** — Native's own
work list records several as pending quick wins (``docs/binding-parity-audit.md:29``,
``docs/native-binding-coverage-audit.md:81``: *"bind already-backed methods: draw_on_compass
(ui_methods.cpp:1578), async_decode_str (2444), is_valid_enc_bytes (2497), set_frame_margins
(866); wire set_window_position + register/remove_create_ui_component_callback"*). Each of those is
still resolved here, to **the function the binding would wrap**, because that is what the binding
is: ``async_decode_str`` → ``GW::ui::AsyncDecodeStr``, ``draw_on_compass`` →
``GW::ui::DrawOnCompass``, ``set_window_position`` → ``GW::ui::SetWindowPosition``, ``load_settings``
→ ``GW::ui::LoadSettings``, ``get_settings`` → ``GW::ui::GetSettings``,
``get_current_tooltip_address`` → ``GW::ui::GetCurrentTooltip``. The three that have **neither a
binding nor a function in Native's current revision** — ``get_frame_logs``, ``clear_frame_logs``,
``get_key_mappings``, ``set_key_mappings``, ``is_valid_enc_bytes``'s function, ``set_open_links``'s
effect — are handled member by member below, and each one says exactly what it is missing.

**What the port cannot reproduce, stated where it happens.** Two kinds of member return something
the injected runtime owns *in its own process*, which this project does not have:

- **its own journals** — ``GetFrameLogs``/``ClearFrameLogs`` read GWCA's ``frame_logs``
  (``vendor/gwca/Source/UIMgr.cpp:106``), which only its ``CreateUIComponent`` detour fills
  (``UIMgr.cpp:160``); ``GetUIMessageLogs``/``ClearUIMessageLogs`` read Native's ``g_ui_message_logs``
  deque (``ui.cpp:1077``), filled by Native's own message hook (``ui.cpp:1136-1150``);
- **its own dispatch flag** — ``SetOpenLinks`` writes Native's ``g_open_links`` (``ui_methods.cpp:1680``),
  which only Native's ``kOpenTemplate`` handler consults (``ui.cpp:309-324``).

Each reports that plainly and returns nothing in its place, as ``Player.player_instance`` and
``Agent.GetProfessionsTexturePaths`` do.
"""

from __future__ import annotations

import struct
from collections import defaultdict, deque
from typing import Any, Dict, List, TypedDict

from .frame_tree import Frame, FrameId, FrameTree
from .game_thread.shared_block import CallForm, DecodeState, Operation

__all__ = [
    "DIALOG_CHILD_OFFSET",
    "DEFAULT_OFFSET",
    "NPC_DIALOG_HASH",
    "UIManager",
]

# —— Constants ——————————————————  (source lines 21-24)

#: ``UIManager.py:22`` — the dialog root frame's hash, the anchor the buttons hang under.
NPC_DIALOG_HASH = 3856160816

#: ``UIManager.py:23`` — the source's default child path, used as the "not detected yet" marker.
DEFAULT_OFFSET = [2, 0, 0, 1]

#: ``UIManager.py:24`` — what ``FindDialogOffset`` overwrites; module state, as in the source.
DIALOG_CHILD_OFFSET = list(DEFAULT_OFFSET)

#: The catalog name of the client's own UI-message sender — the function this connection hooks and
#: calls (``offsets/ui.json``, ``client.py:103``). ``g_send_ui_message_original``
#: (``ui_patterns.cpp:31``: ``void __cdecl(UIMessage, void* wparam, void* lparam)``).
_SEND_UI_MESSAGE_FUNC = "ui.send_ui_message_func"

#: The client's frame-message sender, the ``__thiscall`` this port already drives for
#: `Frame.send_message` and `Frame.click` (``ui_patterns.cpp:32``).
_SEND_FRAME_UI_MESSAGE_FUNC = "ui.send_frame_ui_message_func"

#: The globals and functions behind the read members. Each name is the resolver in
#: ``offsets/ui.json`` that locates the client's own address.
_WORLD_MAP_STATE_ADDR = "ui.world_map_state_addr"
_UI_DRAWN_ADDR = "ui.ui_drawn_addr"
_SHIFT_SCREENSHOT_ADDR = "ui.shift_screenshot_addr"
_WINDOW_POSITIONS_ARRAY = "ui.window_positions_array"
_GAME_SETTINGS_ADDR = "ui.game_settings_addr"
_SET_WINDOW_VISIBLE_FUNC = "ui.set_window_visible_func"
_SET_WINDOW_POSITION_FUNC = "ui.set_window_position_func"
_DRAW_ON_COMPASS_FUNC = "ui.draw_on_compass_func"
_LOAD_SETTINGS_FUNC = "ui.load_settings_func"

#: The client's key-remap table, as the catalog derives it: the ``FrKey.cpp`` assertion
#: ``count == arrsize(s_remapTable)``, the first ``.text`` use of its message, ``+0xD`` to the
#: immediate that loads the table, and a ``.data`` check on the result. The derivation and its
#: offline measurement are on `GetKeyMappings`.
_KEY_MAPPINGS_TABLE = "ui.key_mappings_table"

#: How many words the table holds — ``arrsize(s_remapTable)``, which the entry beside it compares
#: against (``cmp [ebp+8], 0x75``) and the older runtime's binding hard-codes (``py_ui.h:4760``).
_KEY_MAPPINGS_WORDS = 0x75

#: ``GetButtonActionFrame()``'s two steps (``ui_methods.cpp:161-164``): the label the client hashes,
#: and the child index it walks to. The child walk is ``g_get_child_frame_id_func``
#: (``ui_methods.cpp:589-607``), and the label hash is ``g_create_hash_from_wchar_func``
#: (``:542-546``), whose second argument is native's ``-1``.
_BUTTON_ACTION_FRAME_LABEL = "Game"
_BUTTON_ACTION_CHILD_INDEX = 6
_CREATE_HASH_FROM_WCHAR_FUNC = "ui.create_hash_from_wchar_func"
_GET_CHILD_FRAME_ID_FUNC = "ui.get_child_frame_id_func"
_HASH_LABEL_LENGTH = 0xFFFFFFFF

#: ``Constants::UIMessage::kKeyDown`` / ``kKeyUp`` (``common/constants/ui.h:12,14``).
_K_KEY_DOWN = 0x20
_K_KEY_UP = 0x22

#: ``Constants::WindowID_Count`` (``ui.h:109``): ``GetWindowPosition``'s own bound. **Native's
#: value, not Reforged's** — Reforged's ``enums_src/UI_enums.py`` carries ``0x69``
#: (``ui_enums.py:518``, ported verbatim), and the two disagree; the members below port Native's
#: bound because the bound is Native's check (``ui_methods.cpp:1683-1704``). Recorded as a finding in
#: ``docs/UIMANAGER_PORT.md``.
_WINDOW_ID_COUNT = 0x66

#: ``GetIsWorldMapShowing``'s mask (``ui_methods.cpp:1736``): ``(*state & 0x80000) != 0``.
_WORLD_MAP_SHOWING_MASK = 0x80000

#: ``RawSendUiMessage``'s early answer (``ui_methods.cpp:250-252``): a message in this range is
#: reported as sent **without being sent**.
_UI_MESSAGE_HIGH_MASK = 0x30000000

#: Native's packed UI-message payload: **sixteen zeroed words**, with ``values`` copied into the
#: front (``ui_bindings.cpp:60-74``). This port builds the same payload in the block's data region,
#: which is memory inside the client, because the client is handed a pointer to it.
_UI_PAYLOAD_BYTES = 64
_UI_PAYLOAD_WORDS = 16

#: ``Context::WindowPosition`` (``context/ui.h:532-537``): ``state``, ``p1``, ``p2`` — 20 bytes,
#: with ``visible()`` written as ``(state & 1) != 0``.
_WINDOW_POSITION_SIZE = 0x14
_WINDOW_POSITION_VISIBLE_BIT = 0x1

#: Where this module's structs go in the block's data region. The region's other users hold 0-15
#: (the render capture slot and the DAT reader's hash and size), 4 onward (the watched message's
#: string), 16-296 (the chat buffer), and the camera writes at ``0x200``; `Frame.click` uses
#: ``0x300``/``0x320``. The region is 4096 bytes and every write is bounds-checked, so a compass
#: polyline longer than the span is refused rather than allowed to run over the event ring.
_COMPASS_POINTS_OFFSET = 0x400
_KEY_MAPPINGS_OFFSET = 0x900
_LABEL_ARGUMENT_OFFSET = 0xB00
_WINDOW_POSITION_OFFSET = 0xC00
_KEY_ACTION_OFFSET = 0xC20
_SETTINGS_OFFSET = 0xC40
_UI_PAYLOAD_OFFSET = 0xE00


# --------------------------------------------------------------------------
def _unported(member: str, requirement: str) -> NotImplementedError:
    """Build the error raised by a member this port has not built yet."""

    return NotImplementedError(
        f"{member} is declared but not built here yet: it needs {requirement}. "
        "The source's member works; this port raises at the call site and names the work "
        "item instead of returning a wrong value."
    )


class UIManager:
    """Reforged's ``class UIManager`` (``UIManager.py:29-618``), member for member.

    Every public member is a ``@staticmethod`` in the source and is one here. The class attributes
    the source declares (``:30-40``) are declared in the same order: the injected overlay object,
    the dev-text cache word, the nested ``IOEvent`` record shape, and the two IO registries.
    """

    #: ``:30`` — the source instantiates the injected ``PyOverlay.Overlay`` here. This port has no
    #: overlay object (``docs/CLASS_PORT_MAP.md``: the DX overlay needs a render hook), and **no
    #: member of the class reads this attribute** — ``:30`` is its only appearance in the file — so
    #: it is declared and left empty rather than given a stand-in.
    _overlay = None

    #: ``:31`` — declared by the source and never read or written anywhere in the class either.
    _devtext_dialog_proc_cache: int = 0

    class IOEvent(TypedDict):
        timestamp: int
        event_type: str
        mouse_pos: tuple[float, float]
        details: Dict[str, Any]

    #: ``:39`` — the frames whose IO events are tracked, appended by
    #: `RegisterFrameIOEventCallback` and read by `_UpdateFrameIOEvents`.
    frame_callbacks: list[int] = []

    #: ``:40`` — the per-frame event lists, keyed by the same handle.
    frame_io_events: Dict[int, List[IOEvent]] = defaultdict(list)

    # -- frame IO events (source lines 42-157) ----------------------------

    @staticmethod
    def RegisterFrameIOEventCallback(frame: Any) -> None:
        """Register a frame ID to track IO events.

        ``:43-50``. The docstring says "frame ID" and the body appends the **handle** it is given
        to a class-level list; this port does the same, because that list is what
        `_UpdateFrameIOEvents` iterates and what `GetIOEventsForFrame` keys its answer by.
        """

        if frame not in UIManager.frame_callbacks:
            UIManager.frame_callbacks.append(frame)

    @staticmethod
    def UnregisterFrameIOEventCallback(frame: Any) -> None:
        """Unregister a frame ID from tracking IO events (``:53-62``)."""

        if frame in UIManager.frame_callbacks:
            UIManager.frame_callbacks.remove(frame)
            if frame in UIManager.frame_io_events:
                del UIManager.frame_io_events[frame]

    @staticmethod
    def _UpdateFrameIOEvents() -> None:
        """Update IO events for registered frame IDs (``:66-129``).

        **Not built: this member reads the client's own ImGui.** The source begins with
        ``io = PyImGui.get_io()`` (``:74``) — the injected runtime's ImGui context, from which it
        takes ``mouse_pos_x``, ``mouse_pos_y`` and ``mouse_wheel``/``mouse_wheel_h`` — and asks
        ``PySystem.get_tick_count64()`` (``:76``) for the timestamp. It then walks
        ``UIManager.frame_callbacks`` and, per frame, asks ``frame.is_mouse_over()`` (which the
        frame port answers) and ``PyImGui.is_mouse_clicked``/``is_mouse_double_clicked`` (``:85-88``).

        Neither ``PyImGui`` nor ``PySystem`` exists here: ``PyImGui`` is the client's own ImGui
        (``offsets/native_ui.json`` is the name inventory for that work) and ``PySystem`` is the
        injected runtime's module (its ``get_tick_count64`` is the runtime's own clock — the port's
        ``dialog._now_ms`` is its equivalent, and the skill timer in
        ``py4gw/memory/memory_manager.py`` is the other). The body below is the source's, so the
        member is two reads away from working rather than one design away.
        """

        # The locals the source's body binds — its two client reads (``:74-90``) and the frame
        # handle its loop takes from ``frame_callbacks``. They are declared so the source's body
        # below (the loop, the nested ``_add_event`` and its six branches) is whole and in place;
        # the raise above it is the only thing that stops it running, and nothing here is used
        # before it.
        io: Any = None
        mouse_pos: tuple[float, float] = (0.0, 0.0)
        timestamp: int = 0
        is_left_mouse_clicked = False
        is_right_mouse_clicked = False
        is_middle_mouse_clicked = False
        is_double_clicked = False
        scroll_y_delta = 0.0
        scroll_x_delta = 0.0

        raise _unported(
            "UIManager._UpdateFrameIOEvents",
            "PyImGui.get_io() (mouse_pos_x, mouse_pos_y, mouse_wheel, mouse_wheel_h), "
            "PyImGui.is_mouse_clicked / is_mouse_double_clicked and PySystem.get_tick_count64() "
            "(UIManager.py:74-90) — the injected runtime's ImGui context and clock",
        )

        for frame in UIManager.frame_callbacks:
            if not frame.is_usable:
                continue

            if not frame.is_mouse_over():
                continue

            # ``:92-111`` — the source's own event recorder, nested exactly where it is written.
            def _add_event(event_type: str, details: Dict[str, Any] = {}) -> None:
                event: UIManager.IOEvent = {
                    "timestamp": timestamp,
                    "event_type": event_type,
                    "mouse_pos": mouse_pos,
                    "details": details,
                }

                # ensure list exists for this frame
                if frame not in UIManager.frame_io_events:
                    UIManager.frame_io_events[frame] = []

                # search for existing event and update instead of adding a duplicate
                for i, existing in enumerate(UIManager.frame_io_events[frame]):
                    if existing.get("event_type") == event_type:
                        UIManager.frame_io_events[frame][i] = event
                        break
                else:
                    # not found -> append new
                    UIManager.frame_io_events[frame].append(event)

            if is_left_mouse_clicked:
                _add_event("left_mouse_clicked")

            if is_right_mouse_clicked:
                _add_event("right_mouse_clicked")

            if is_middle_mouse_clicked:
                _add_event("middle_mouse_clicked")

            if is_double_clicked:
                _add_event("double_clicked")

            if scroll_y_delta != 0.0:
                _add_event("mouse_wheel_scrolled", {"scroll_y_delta": scroll_y_delta})

            if scroll_x_delta != 0.0:
                _add_event(
                    "mouse_wheel_scrolled_horizontal", {"scroll_x_delta": scroll_x_delta}
                )

    @staticmethod
    def GetIOEventsForFrame(frame: Any) -> List[IOEvent]:
        """Get the list of IO events for a specific frame ID (``:132-143``).

        The source lazy-loads the list the same way it registers: a frame this asks about joins
        ``frame_callbacks``. Ported as written, including the ``.get`` that answers the empty list
        for a frame with no events yet.
        """

        # lazy load the list if it doesn't exist
        if frame not in UIManager.frame_callbacks:
            UIManager.frame_callbacks.append(frame)

        return UIManager.frame_io_events.get(frame, [])

    @staticmethod
    def RegisterFrameIOCallbacks() -> None:
        """Register the frame IO event update callback (``:146-157``).

        **Not built: this member registers with the injected ``PyCallback``.** The source calls
        ``PyCallback.PyCallback.Register("UIManager.UpdateFrameIOEvents", PyCallback.Phase.Data,
        UIManager._UpdateFrameIOEvents, priority=2, context=PyCallback.Context.Draw)`` — Reforged's
        per-frame dispatcher, the same one ``Agent.enable`` and ``Agent._invalidate_property_cache``
        register with (``Agent.py:52-60``). This port has no frame loop to dispatch to
        (``AGENTS.md`` § Caching, ``docs/PORTING_RULES.md``), and the member it would register is
        itself waiting on the client's ImGui. The source's own call site is commented out anyway
        (``:614-617``: *"autiomatic IO events was deactivated due to instability over long sessions;
        use this feature on demand"*).
        """

        raise _unported(
            "UIManager.RegisterFrameIOCallbacks",
            "PyCallback.PyCallback.Register at PyCallback.Phase.Data with "
            "context=PyCallback.Context.Draw (UIManager.py:150-157) — the injected runtime's "
            "per-frame dispatcher, which this port's execution model has no equivalent of",
        )

    # -- the plain wrappers (source lines 159-394) ------------------------

    @staticmethod
    def GetFrameLogs() -> List[tuple[int, int, str]]:
        """Get the frame logs (``:161-167``).

        **Not portable: these are the injected runtime's own journal.** The binding resolves to
        ``GW::UI::GetFrameLogs()``, which returns a copy of GWCA's ``frame_logs`` vector — module
        state, not client state. Its only producer is GWCA's own ``OnCreateUIComponent`` detour,
        which logs the ``component_label`` the client was handed after forwarding the call
        (``vendor/gwca/Source/UIMgr.cpp:106``, ``:129-162``; entries are
        ``(uint64_t tick, uint32_t frame_id, std::string label_utf8)``, capped at 5000). A runtime
        that does not hook ``CreateUIComponent`` has nothing to return here, and no client read
        reproduces it. The work item, if the log is wanted, is a capture on this project's own hook
        layer — named in ``docs/TARGET_SIDE_WORK.md``.
        """

        raise _unported(
            "UIManager.GetFrameLogs",
            "the injected runtime's own frame-log buffer: GW::UI::GetFrameLogs returns GWCA's "
            "frame_logs, filled only by its CreateUIComponent detour "
            "(vendor/gwca/Source/UIMgr.cpp:106,129-162) — nothing in the client holds it",
        )

    @staticmethod
    def ClearFrameLogs() -> None:
        """Clear the frame logs (``:170-174``) — the other half of the runtime's own buffer.

        ``GW::UI::ClearFrameLogs()`` is ``frame_logs.clear()`` (``UIMgr.cpp:1235-1237``).
        """

        raise _unported(
            "UIManager.ClearFrameLogs",
            "the injected runtime's own frame-log buffer: GW::UI::ClearFrameLogs is "
            "frame_logs.clear() (vendor/gwca/Source/UIMgr.cpp:1235-1237)",
        )

    @staticmethod
    def GetUIMessageLogs() -> List[tuple[int, int, bool, bool, int, list[int], list[int]]]:
        """Get the UI message logs (``:177-183``).

        **Not portable: the injected runtime's own deque.** Native's ``GetUIMessageLogs``
        (``ui.cpp:1155-1163``) copies ``g_ui_message_logs``, a ``std::deque`` its own message handler
        fills on every message it sees (``ui.cpp:1136-1150``, capped at
        ``kMaxUIMessageLogEntries``, cleared by ``ClearUIMessageLogs`` at ``ui.cpp:1165-1170``).
        Each entry is ``(uint64_t tick, uint32_t msgid, bool incoming, bool is_frame_message,
        uint32_t frame_id, std::vector<uint8_t> wparam_bytes, std::vector<uint8_t> lparam_bytes)``
        (``ui.h:712``) — the source's own docstring names the same seven fields.

        This project *does* hook the client's message sender (that is how `Frame.click` and the
        dialog module see what the client did), so the equivalent log is a capture on that hook —
        work with a name, in ``docs/TARGET_SIDE_WORK.md`` — and not something to invent here.
        """

        raise _unported(
            "UIManager.GetUIMessageLogs",
            "the injected runtime's own message-log deque: GW::ui::GetUIMessageLogs copies "
            "g_ui_message_logs, which Native's message hook fills (ui.cpp:1077,1136-1163); the "
            "port's equivalent is a capture on its own sender hook",
        )

    @staticmethod
    def ClearUIMessageLogs() -> None:
        """Clear the UI message logs (``:186-190``) — the other half of the same deque."""

        raise _unported(
            "UIManager.ClearUIMessageLogs",
            "the injected runtime's own message-log deque: GW::ui::ClearUIMessageLogs clears "
            "g_ui_message_logs (ui.cpp:1165-1170)",
        )

    @staticmethod
    def GetTextLanguage() -> int:
        """``:194-195`` → ``get_text_language``.

        Native's ``GetTextLanguage`` is one expression — ``static_cast<GW::Language>(
        GetPreference(Constants::NumberPreference::TextLanguage))`` (``ui_methods.cpp:1428-1430``) —
        so this member reads the client's **number** preference the way native does: resolver
        resolved, preferences initialised, index below the count, then the client's own getter.
        """

        from .ui import preferences

        return preferences.get_number_preference(preferences.TEXT_LANGUAGE)

    @staticmethod
    def SendUIMessage(msgid: int, values: list[int], skip_hooks: bool = False) -> bool:
        """``:199-200`` → ``SendUIMessage`` → ``SendUIMessagePacked``.

        ``SendUIMessagePacked`` (``ui_bindings.cpp:60-74``) builds a **zeroed sixteen-word POD**,
        copies ``values`` into the front of it, and calls
        ``GW::ui::SendUIMessage(msgid, &payload, nullptr, skip_hooks)`` (``ui_methods.cpp:1374-1406``).
        This member does the same thing with the same shape: the sixteen words go into the block's
        data region — memory inside the client, which is the only kind of pointer the client can be
        handed — ``values`` is copied into the front, and the client's own sender is called with that
        address through ``ConnectedClient.send_ui_message_raw``, i.e. the three-word call native
        makes. Zeroing the whole payload is the contract, not a tidy-up: the client reads the fields
        the caller did not set.

        **``skip_hooks`` is recorded here rather than reproduced.** In Native it decides whether the
        message is recorded in ``g_ui_message_logs`` and whether the runtime's registered UI-message
        callbacks run before and after the send (``ui_methods.cpp:1374-1406``). This port has neither
        that log nor that registry; its own observation hook is on the sender itself and is entered
        either way. Values past native's sixteen words are dropped, which is what native's own copy
        loop does (``i < 16``).
        """

        from .client import require_client

        client = require_client()
        if not client.resolves(_SEND_UI_MESSAGE_FUNC):
            # ``RawSendUiMessage``'s first check: no sender, no send.
            return False

        # Its early answer (``ui_methods.cpp:250-252``): this id range is reported as sent
        # **without being sent**.
        if (int(msgid) & _UI_MESSAGE_HIGH_MASK) == _UI_MESSAGE_HIGH_MASK:
            return True

        payload = bytearray(_UI_PAYLOAD_BYTES)
        for index, value in enumerate(values[:_UI_PAYLOAD_WORDS]):
            payload[index * 4 : index * 4 + 4] = struct.pack(
                "<I", int(value) & 0xFFFFFFFF
            )
        address = client.bridge.write_data(_UI_PAYLOAD_OFFSET, bytes(payload))
        client.send_ui_message_raw(int(msgid), address, 0)
        return True

    @staticmethod
    def SendUIMessageRaw(msgid: int, wparam: int, lparam: int, skip_hooks: bool = False) -> bool:
        """``:203-204`` → ``SendUIMessageRaw``.

        Native's raw variant is a **direct** call: ``GW::ui::SendUIMessage(static_cast<UIMessage>(
        msgid), reinterpret_cast<void*>(wparam), reinterpret_cast<void*>(lparam), skip_hooks)``
        (``ui_bindings.cpp:1062-1065``), whose two words reach the client's own sender untouched —
        ``g_send_ui_message_original(message_id, wparam, lparam)`` (``ui_patterns.cpp:31``). The two
        casts are the whole point: a caller passes a **raw word** (``PlayerMethods.py:422``:
        ``SendUIMessageRaw(UIMessage.kSendAgentDialog, dialog_id, 0)``), which the packed form would
        turn into a pointer to two words. ``ConnectedClient.send_ui_message_raw`` is that call, and
        the answer is native's: ``false`` when there is no sender, ``true`` for the masked id range
        without sending (``ui_methods.cpp:250-252``), ``true`` once the call has been made.
        """

        from .client import require_client

        client = require_client()
        if not client.resolves(_SEND_UI_MESSAGE_FUNC):
            return False
        if (int(msgid) & _UI_MESSAGE_HIGH_MASK) == _UI_MESSAGE_HIGH_MASK:
            return True
        client.send_ui_message_raw(int(msgid), int(wparam), int(lparam))
        return True

    @staticmethod
    def DrawOnCompass(session_id: int, points: list[tuple[int, int]]) -> bool:
        """``:208-209`` → ``draw_on_compass`` → ``GW::ui::DrawOnCompass``.

        ``ui_methods.cpp:1706-1712`` is ``if (!g_draw_on_compass_func) return false;
        g_draw_on_compass_func(session_id, point_count, points); return true;`` over
        ``void __cdecl(uint32_t session_id, uint32_t point_count, CompassPoint* points)``
        (``ui_methods.cpp:33``), and ``CompassPoint`` is two ``int``s (``ui.h:292-297``). The
        binding's own work is building that array from the Python pairs
        (``py_ui.h:4640-4656``, which is also where the empty list is refused before the call).

        The array goes into the block's data region, because the client is handed a pointer to it —
        the same reason `Frame.click` places its packets there. **One recorded difference:** the
        older runtime's binding refuses an empty list before the call (``py_ui.h:4645-4646``), and
        Native's function makes no such check — this member ports Native's, so an empty list reaches
        the client as ``point_count == 0``.
        """

        from .client import require_client

        client = require_client()
        if not client.resolves(_DRAW_ON_COMPASS_FUNC):
            return False
        payload = b"".join(struct.pack("<ii", int(x), int(y)) for x, y in points)
        address = client.bridge.write_data(_COMPASS_POINTS_OFFSET, payload)
        client.call_function(
            _DRAW_ON_COMPASS_FUNC,
            CallForm.U32_U32_U32,
            int(session_id),
            len(points),
            address,
        )
        return True

    @staticmethod
    def LoadSettings(data: list[int]) -> None:
        """``:212-213`` → ``load_settings`` → ``GW::ui::LoadSettings``.

        ``ui_methods.cpp:1714-1718`` is ``if (g_load_settings_func)
        g_load_settings_func(static_cast<uint32_t>(size), data);`` over
        ``void __cdecl(uint32_t size, uint8_t* data)`` (``ui_methods.cpp:26``) — the client's own
        settings loader, handed the caller's bytes. Native's current revision has the function
        (``ui_methods.cpp:1714``) and no binding for it; Native's own audit lists it as one of the
        members to wire (``docs/native-binding-coverage-audit.md:81``).

        The bytes go into the block's data region, and their length is the size the source passes.
        """

        from .client import require_client

        client = require_client()
        payload = bytes(byte & 0xFF for byte in data)
        address = client.bridge.write_data(_SETTINGS_OFFSET, payload)
        if not client.resolves(_LOAD_SETTINGS_FUNC):
            return
        client.call_function(
            _LOAD_SETTINGS_FUNC, CallForm.U32_U32, len(payload), address
        )

    @staticmethod
    def GetSettings() -> list[int]:
        """``:216-217`` → ``get_settings`` → ``GW::ui::GetSettings``.

        ``ui_methods.cpp:1720-1722`` is ``return reinterpret_cast<ArrayByte*>(
        Context::GetGameSettingsAddress());`` — the client's settings address handed out as
        ``GW::Array<unsigned char>*`` (``ui.h:707``), with no read and no bounds check of its own.
        The array's own header is what says how much there is: ``m_buffer``/``m_capacity``/``m_size``
        (``py4gw/context/gw_array.py``, ``GWArray``), which is the same layout the frame array
        reads. This member therefore resolves that address and returns what the array holds, which
        is what the binding's ``std::vector`` conversion does with it.

        Reforged's Python is the only statement of the return shape (``list[int]``); neither
        Native's current revision nor the older shim carries a ``get_settings`` binding at all.
        """

        from .client import require_client
        from .context.gw_array import GWArray

        client = require_client()
        if not client.resolves(_GAME_SETTINGS_ADDR):
            return []
        address = client._resolve(_GAME_SETTINGS_ADDR)
        if not address:
            return []
        raw = client.reader.read(address, 0x10)
        array = GWArray.from_buffer_copy(raw)
        size = int(array.m_size)
        buffer = int(array.m_buffer)
        if not buffer or size <= 0:
            return []
        return list(client.reader.read(buffer, size))

    @staticmethod
    def GetCurrentTooltipAddress() -> int:
        """``:220-221`` → ``get_current_tooltip_address`` → ``GW::ui::GetCurrentTooltip``.

        Native's function is ``current_tooltip_ptr && *current_tooltip_ptr ? **current_tooltip_ptr :
        nullptr`` (``ui_methods.cpp:2658-2661``) and the binding hands back the pointer as an
        integer. **This port reads it once, not twice**, which is the divergence
        ``py4gw/ui/tooltip.py`` records and measured on this build: the global holds the tooltip
        pointer itself, so the second dereference would read the record's first word as a pointer
        and answer "no tooltip" for a tooltip that exists. The word read here is that one
        dereference, and ``0`` is the source's null.
        """

        from .client import require_client

        client = require_client()
        address = client.current_tooltip.resolve_address()
        if not address:
            return 0
        return int.from_bytes(client.reader.read(address, 4), "little")

    @staticmethod
    def IsWorldMapShowing() -> bool:
        """``:237-243`` → ``is_world_map_showing`` → ``GW::ui::GetIsWorldMapShowing``.

        ``ui_methods.cpp:1734-1737``: ``world_map_state ? ((*world_map_state & 0x80000U) != 0) :
        false``. The address is the client's own world-map state word
        (``Context::GetWorldMapStateAddress``), which this port already resolves.
        """

        from .client import require_client

        client = require_client()
        if not client.resolves(_WORLD_MAP_STATE_ADDR):
            return False
        address = client._resolve(_WORLD_MAP_STATE_ADDR)
        if not address:
            return False
        state = int.from_bytes(client.reader.read(address, 4), "little")
        return (state & _WORLD_MAP_SHOWING_MASK) != 0

    @staticmethod
    def IsUIDrawn() -> bool:
        """``:246-247`` → ``is_ui_drawn`` → ``GW::ui::GetIsUIDrawn``.

        ``ui_methods.cpp:1724-1727``: ``ui_drawn ? (*ui_drawn == 0) : true`` — **the flag is
        inverted**, and an address that did not resolve is the source's ``true``.
        """

        from .client import require_client

        client = require_client()
        if not client.resolves(_UI_DRAWN_ADDR):
            return True
        address = client._resolve(_UI_DRAWN_ADDR)
        if not address:
            return True
        return int.from_bytes(client.reader.read(address, 4), "little") == 0

    @staticmethod
    def AsyncDecodeStr(enc_str: str) -> str:
        """``:250-251`` → ``async_decode_str`` → ``GW::ui::AsyncDecodeStr``.

        The binding behind this member builds a ``std::wstring`` for the output and calls the
        decoder's callback overload, then reads that string **immediately after the call returns**
        (``py_ui.h:4591-4597``); whether the text is there depends on the client having called the
        callback inside the call, and the source has no wait, poll or retry around it.

        This port's decoder is that same shape with the callback in the client: the slot is placed,
        the client's validator is called with the emitted stub, and the stub *completes the slot*
        when the client calls it (`py4gw/ui/async_decode.py`). So the text is read here exactly as
        the source reads its string — once, straight after the call — and a decode the client did
        not complete inside the call answers ``""``, which is what the shim's untouched ``output``
        would have been. The slot is left where the port's own machinery left it; the source has no
        retry, so this member adds none.
        """

        from .ui.async_decode import async_decode_str, begin_string_decode, decode_state, decoded_text

        raw = _wide_bytes(enc_str)
        try:
            slot = begin_string_decode(raw)
        except RuntimeError:
            return ""
        if not async_decode_str(raw, slot):
            return ""
        if decode_state(slot) is not DecodeState.DONE:
            return ""
        text, _truncated = decoded_text(slot)
        return text

    @staticmethod
    def IsValidEncStr(enc_str: str) -> bool:
        """``:254-255`` → ``is_valid_enc_str`` → ``GW::ui::IsValidEncStr``.

        Native's binding converts the Python string to a ``std::wstring`` and passes its
        ``c_str()`` (``ui_bindings.cpp:1131``), so the array the client's validator sees ends with
        the terminator the conversion adds. The port's validator is the same walk
        (``py4gw/ui/encoded_str.py``), and the terminator is what it needs to find the range.
        """

        from .ui.encoded_str import is_valid_enc_str

        return is_valid_enc_str(_wide_units(enc_str))

    @staticmethod
    def IsValidEncBytes(enc_bytes: bytes) -> bool:
        """``:258-259`` → ``is_valid_enc_bytes``.

        Native's current revision has no such member at all — Native's own audit names
        ``is_valid_enc_bytes`` as a method to bind, with the line of the function it would call
        (``docs/binding-parity-audit.md:29``, *"is_valid_enc_bytes (2497)"*), and the function that
        line names is the **other** validator's, not this one's; there is no
        ``IsValidEncBytes`` in ``ui_methods.cpp``. The only implementation that exists is the older
        runtime's binding, and it is three preconditions followed by the same validator
        (``py_ui.h:4605-4615``): the bytes are non-empty, they are a whole number of ``wchar_t``,
        the last code unit is ``0x0000`` — and then ``GW::UI::IsValidEncStr(wide)``. That is what
        this member ports, check for check, in the source's order.
        """

        from .ui.encoded_str import is_valid_enc_str

        raw = bytes(enc_bytes or b"")
        if not raw or (len(raw) % 2) != 0:
            return False
        units = _wide_units_from_bytes(raw)
        if units[-1] != 0x0000:
            return False
        return is_valid_enc_str(units)

    @staticmethod
    def UInt32ToEncStr(value: int) -> str:
        """``:262-263`` → ``uint32_to_enc_str`` → ``GW::ui::UInt32ToEncStr``.

        Native's binding calls ``GW::ui::UInt32ToEncStr(value, buffer, 8)`` with a zeroed
        ``wchar_t[8]`` and returns ``std::wstring(buffer)`` (``ui_bindings.cpp:1132-1136``): the
        digits up to the terminator the call writes, and the empty string when the function refuses
        (the buffer then holds only its zeros).
        """

        from .ui.encoded_str import uint32_to_enc_str

        buffer = uint32_to_enc_str(int(value), 8)
        if buffer is None:
            return ""
        return "".join(chr(unit) for unit in buffer if unit != 0)

    @staticmethod
    def EncStrToUInt32(enc_str: str) -> int:
        """``:266-267`` → ``enc_str_to_uint32`` → ``GW::ui::EncStrToUInt32``.

        The binding passes the ``std::wstring``'s ``c_str()`` (``ui_bindings.cpp:1137``), so the
        walk has the terminator the conversion adds; the port's decoder keeps the source's
        arithmetic (``py4gw/ui/encoded_str.py``), including the ``uint32`` wrap.
        """

        from .ui.encoded_str import enc_str_to_uint32

        return enc_str_to_uint32(_wide_units(enc_str))

    @staticmethod
    def SetOpenLinks(toggle: bool) -> None:
        """``:270-271`` → ``set_open_links`` → ``GW::ui::SetOpenLinks``.

        **Not portable: it writes the injected runtime's own flag, and only its own hook reads
        it.** ``GW::ui::SetOpenLinks`` is one statement — ``g_open_links = toggle``
        (``ui_methods.cpp:1679-1681``) — over a variable declared ``extern bool g_open_links``
        (``ui_methods.cpp:128``) and defined in Native's UI module (``ui.cpp:1078``). Its only
        consumer is Native's ``OnOpenTemplateUiMessage`` handler, which blocks the client's
        ``kOpenTemplate`` message and calls ``ShellExecuteW`` when the flag is set and the template
        name is an ``http://``/``https://`` link (``ui.cpp:309-324``). Nothing in the client holds
        this flag; a port that set a word somewhere would change nothing and would be claiming an
        effect it does not have. The work item, if link-opening is wanted, is that handler on this
        project's own hook layer (``docs/TARGET_SIDE_WORK.md``).
        """

        raise _unported(
            "UIManager.SetOpenLinks",
            "the injected runtime's own link-opening hook: GW::ui::SetOpenLinks writes "
            "g_open_links (ui_methods.cpp:1679-1681, ui.cpp:1078), which only Native's "
            "kOpenTemplate handler consults (ui.cpp:309-324), where it blocks the message and "
            "calls ShellExecuteW",
        )

    @staticmethod
    def IsShiftScreenshot() -> bool:
        """``:274-280`` → ``is_shift_screenshot`` → ``GW::ui::GetIsShiftScreenShot``.

        ``ui_methods.cpp:1729-1732``: ``shift_screen ? (*shift_screen != 0) : false``.
        """

        from .client import require_client

        client = require_client()
        if not client.resolves(_SHIFT_SCREENSHOT_ADDR):
            return False
        address = client._resolve(_SHIFT_SCREENSHOT_ADDR)
        if not address:
            return False
        return int.from_bytes(client.reader.read(address, 4), "little") != 0

    @staticmethod
    def GetFPSLimit() -> int:
        """``:283-289`` → ``get_frame_limit`` → ``GW::ui::GetFrameLimit``.

        The source reaches ``GW::ui::GetFrameLimit`` (``ui_methods.cpp:1833-1858``) through the
        binding; this port's ``py4gw/ui/preferences.py`` already carries that function branch for
        branch — the command-line FPS, the frame-limiter preference, the monitor refresh rate and
        the vsync clamp — because ``Agent.GetInstanceUptime`` needed it before this class had a
        home. The member calls it, which is the source's own route with the one layer between them
        named here.
        """

        from .ui import preferences

        return preferences.get_frame_limit()

    @staticmethod
    def SetFPSLimit(limit: int) -> None:
        """``:292-298`` → ``set_frame_limit`` → ``GW::ui::SetFrameLimit``.

        ``ui_methods.cpp:1860-1864`` is one write: ``g_command_line_number_buffer[FPS] = value``,
        with ``false`` when the buffer is unresolved. Native's binding enqueues it on the game
        thread (``ui_bindings.cpp:689-692``); this port's write goes through the payload's
        ``WRITE_MEMORY`` operation, which runs inside the hooked client function — the same thread
        the source's enqueue reaches.
        """

        from .ui import preferences

        preferences.set_frame_limit(int(limit))

    @staticmethod
    def GetPreferenceOptions(pref: int) -> List[int]:
        """``:302-303`` → ``get_preference_options`` → ``GW::ui::GetPreferenceOptions``.

        ``ui_methods.cpp:1438-1448``: the guard is ``options && pref < Count`` — **no
        ``PrefsInitialised()`` check** — and the function then returns ``info.options_count`` while
        writing ``info.options`` through its out-parameter. The binding turns the pair into a list
        (``ui_bindings.cpp:1025-1033``). The read lives in ``py4gw/ui/preferences.py``, which is
        where this port keeps the ``GW::ui`` preference functions; this member is the source's own
        wrapper over it.
        """

        from .ui import preferences

        return preferences.get_enum_preference_options(int(pref))

    @staticmethod
    def GetEnumPreference(pref: int) -> int:
        """``:306-307`` → ``get_enum_preference`` → ``GetPreference(EnumPreference)``.

        ``ui_methods.cpp:1432-1436``: the function resolved, the preferences initialised, the index
        below ``Count``, then the client's own getter. ``py4gw/ui/preferences.py`` is that guard,
        and this member calls it.
        """

        from .ui import preferences

        return preferences.get_enum_preference(int(pref))

    @staticmethod
    def GetIntPreference(pref: int) -> int:
        """``:310-311`` → ``get_int_preference`` → ``GetPreference(NumberPreference)``.

        The same three conditions over ``g_get_number_preference_func`` and
        ``Constants::NumberPreference::Count`` (``ui_methods.cpp:1450-1454``).
        """

        from .ui import preferences

        return preferences.get_number_preference(int(pref))

    @staticmethod
    def GetStringPreference(pref: int) -> str:
        """``:314-315`` → ``get_string_preference`` → ``GetPreference(StringPreference)``.

        ``ui_methods.cpp:1456-1460`` returns the client's **own wide-string pointer**, and the
        binding converts it (``ui_bindings.cpp:1043-1045``, ``SafeWide``). The port reads the
        string at that pointer, bounded, the way it reads every wide string in the client.
        """

        from .ui import preferences

        return preferences.get_string_preference(int(pref))

    @staticmethod
    def GetBoolPreference(pref: int) -> bool:
        """``:318-319`` → ``get_bool_preference`` → ``GetPreference(FlagPreference)``.

        ``ui_methods.cpp:1462-1466``, over ``g_get_flag_preference_func`` and
        ``Constants::FlagPreference::Count``.
        """

        from .ui import preferences

        return preferences.get_flag_preference(int(pref))

    @staticmethod
    def SetEnumPreference(pref: int, value: int) -> None:
        """``:322-323`` → ``set_enum_preference`` → ``SetPreference(EnumPreference, value)``.

        ``ui_methods.cpp:1468-1540``: the guard, the value validated against the client's own option
        list, the ``AntiAliasing``/``TerrainQuality``/``ShaderQuality`` rewrites, the write through
        ``g_set_enum_preference_func``, and the follow-up that drives the renderer, shadow, terrain,
        reflection and UI-scale setters. The body is ported in ``py4gw/ui/preferences.py`` — the home
        this port keeps the ``GW::ui`` preference functions in — and this member is the source's own
        wrapper over it.
        """

        from .ui import preferences

        preferences.set_enum_preference(int(pref), int(value))

    @staticmethod
    def SetIntPreference(pref: int, value: int) -> None:
        """``:326-327`` → ``set_int_preference`` → ``SetPreference(NumberPreference, value)``.

        ``ui_methods.cpp:1542-1637``: the ``PrefsInitialised()`` guard, the clamp through the
        client's own ``clamp_proc``, the write through ``g_set_number_preference_func``, and the
        follow-up that drives the five volume channels, the master volume and the eleven renderer
        metrics. Ported in ``py4gw/ui/preferences.py``.
        """

        from .ui import preferences

        preferences.set_number_preference(int(pref), int(value))

    @staticmethod
    def SetStringPreference(pref: int, value: str) -> None:
        """``:330-331`` → ``set_string_preference`` → ``SetPreference(StringPreference, value)``.

        ``ui_methods.cpp:1639-1651``: the guard (setter resolved, preferences initialised, index below
        ``StringPreference::Count``) and then ``g_set_string_preference_func(pref, value)`` — **the
        client reads the string the caller owns**, so the binding hands over a ``std::wstring``'s own
        buffer (``ui_bindings.cpp:1055-1057``).

        **The wide-string argument form needed no new mechanism, and this member is the proof.**
        ``ConnectedClient.bridge.write_data`` places arbitrary bytes in the block's data region —
        memory inside the client — and answers that address, which is exactly the shape a pointer
        argument needs; the port had it all along, and this member writes the UTF-16 text there and
        passes the address. The port doc and ``docs/TARGET_SIDE_WORK.md`` had this filed as a missing
        capability, and that was wrong: what was missing was the body. The same correction applies to
        `Frame.send_message_text`, `Frame.set_text` and the tree's label hash, which wait on the same
        non-item.
        """

        from .ui import preferences

        preferences.set_string_preference(int(pref), value)

    @staticmethod
    def SetBoolPreference(pref: int, value: bool) -> None:
        """``:334-335`` → ``set_bool_preference`` → ``SetPreference(FlagPreference, value)``.

        ``ui_methods.cpp:1653-1677``: the guard, the write through ``g_set_flag_preference_func``,
        and then — only for ``FlagPreference::IsWindowed`` — the renderer-mode pair (read
        ``g_get_game_renderer_mode_func(0)``, write ``g_set_game_renderer_mode_func(0, value ? 2 :
        0)`` when it differs). Ported in ``py4gw/ui/preferences.py``.
        """

        from .ui import preferences

        preferences.set_flag_preference(int(pref), bool(value))

    @staticmethod
    def GetKeyMappings() -> List[int]:
        """``:338-339`` → ``get_key_mappings``.

        Native's current revision binds no such member; the older runtime's implementation scans for
        the client's ``FrKey.cpp`` assertion ``"count == arrsize(s_remapTable)"``, reads the table
        pointer the found sequence embeds, validates it against the data section, and returns
        ``0x75`` words from it (``py_ui.h:4757-4772``).

        **The table's address is derived for this build, and the derivation is in the catalog.**
        ``ui.key_mappings_table`` reads the assertion's message literal, takes the *first* of the two
        ``.text`` uses of it (GWCA's own comment: *"this address is fond twice, we only care about the
        first"*), steps **+0xD** to the immediate of the ``mov`` that loads the table — the entry
        asserts ``count == 0x75`` immediately above it — reads that immediate, and requires it to land
        in ``.data``. Measured offline on this build (``tools/key_mappings_hunt.py``): both uses read
        ``0x00C14C58``, inside ``.data``. **GWCA's own offset (``0x13``) does not reproduce here**, so
        this is not that route with a different number; it is the same evidence read directly. An
        unresolved table answers the empty list, which is what the older runtime's own ``result``
        would be.
        """

        from .client import require_client

        client = require_client()
        if not client.resolves(_KEY_MAPPINGS_TABLE):
            return []
        address = client._resolve(_KEY_MAPPINGS_TABLE)
        if not address:
            return []
        return [
            int.from_bytes(client.reader.read(address + index * 4, 4), "little")
            for index in range(_KEY_MAPPINGS_WORDS)
        ]

    @staticmethod
    def SetKeyMappings(mappings: List[int]) -> None:
        """``:342-343`` → ``set_key_mappings``.

        The same derivation, and then the older runtime's body: ``min(0x75, len(mappings))`` words
        copied **into the client's own table** on the game's own thread (``py_ui.h:4774-4790``). A
        shorter list writes a prefix and leaves the tail as it was; an empty list writes nothing,
        which is what that ``std::copy`` over ``min(...)`` does. The write goes through the payload's
        ``WRITE_MEMORY`` operation, which runs inside the hooked client function.
        """

        from .client import require_client

        client = require_client()
        if not client.resolves(_KEY_MAPPINGS_TABLE):
            return
        address = client._resolve(_KEY_MAPPINGS_TABLE)
        if not address:
            return
        count = min(_KEY_MAPPINGS_WORDS, len(mappings))
        if not count:
            return
        payload = b"".join(
            struct.pack("<I", int(value) & 0xFFFFFFFF) for value in mappings[:count]
        )
        bridge = client.bridge
        bridge.write_data(_KEY_MAPPINGS_OFFSET, payload)
        bridge.submit(
            Operation.WRITE_MEMORY,
            address,
            _KEY_MAPPINGS_OFFSET,
            len(payload),
            0,
            0,
            0,
        )

    @staticmethod
    def Keydown(key: int, frame_id: int) -> None:
        """``:346-347`` → ``key_down`` → ``GW::ui::Keydown``.

        ``ui_methods.cpp:1408-1411``: ``packet::KeyAction action{key}`` and
        ``SendFrameUIMessage(target ? target : GetButtonActionFrame(), UIMessage::kKeyDown,
        &action)``. The binding resolves the frame id and passes null for ``0``
        (``ui_bindings.cpp:1105-1112``, enqueued), so ``frame_id == 0`` means **the client's own
        button-action frame** — ``GetFrameByLabel(L"Game")`` then ``GetChildFrame(frame, 6)``
        (``ui_methods.cpp:161-164``), which this member now walks the way native does
        (``_button_action_frame_id``).

        The one-word ``KeyAction`` goes into the block's data region and is sent to that frame's
        callbacks as ``kKeyDown``, which is the action `Frame.send_message` already performs.
        """

        _send_key_action(int(frame_id), int(key), _K_KEY_DOWN)

    @staticmethod
    def Keyup(key: int, frame_id: int) -> None:
        """``:350-351`` → ``key_up`` → ``GW::ui::Keyup`` — as `Keydown`, with ``kKeyUp``
        (``ui_methods.cpp:1413-1416``)."""

        _send_key_action(int(frame_id), int(key), _K_KEY_UP)

    @staticmethod
    def Keypress(key: int, frame_id: int) -> None:
        """``:354-355`` → ``key_press`` → ``GW::ui::Keypress``.

        ``ui_methods.cpp:1418-1426`` is ``if (!Keydown(key, target)) return false;
        game_thread::Enqueue([key, target] { Keyup(key, target); }); return true;``.

        **The enqueue runs the key-up immediately on this path**, which is what makes the port's
        two calls the same sequence: the binding enqueues the whole ``Keypress`` on the game thread
        (``ui_bindings.cpp:1121-1128``), and ``Enqueue`` executes its callable inline when it is
        already on that thread (``game_thread_methods.cpp:33-45``: *"if (g_in_game_thread)
        callback()"*). So the key-up is not deferred here either.
        """

        UIManager.Keydown(key, frame_id)
        UIManager.Keyup(key, frame_id)

    @staticmethod
    def GetWindoPosition(window_id: int) -> list[int]:
        """``:358-364`` → ``get_window_position`` → ``GW::ui::GetWindowPosition`` — the source's own
        spelling of the member name, kept.

        ``ui_methods.cpp:1683-1688``: ``window_positions && window_id < WindowID_Count ?
        &window_positions[window_id] : nullptr``, and the binding returns the entry's four
        components as a tuple or ``None`` when the lookup refused (``ui_bindings.cpp:673-677``).
        The entry is ``Context::WindowPosition`` (``context/ui.h:532-537``): a ``state`` word, then
        ``p1`` and ``p2`` as two floats each — which is what the binding reads, **not** the derived
        left/top/right/bottom the older runtime computed through the render viewport
        (``py_ui.h:4843-4855`` → ``xAxis``/``yAxis``, ``UIMgr.cpp:2513-2568``, which need
        ``Render::GetViewportWidth/Height``, i.e. the DX context this port does not capture). The
        two are recorded in ``docs/UIMANAGER_PORT.md`` as a source-against-source disagreement, and
        the member ports Native's, which is the higher authority and needs no render context.
        """

        from .client import require_client

        client = require_client()
        if not client.resolves(_WINDOW_POSITIONS_ARRAY):
            return []
        base = client._resolve(_WINDOW_POSITIONS_ARRAY)
        if not base or int(window_id) >= _WINDOW_ID_COUNT:
            return []
        raw = client.reader.read(
            base + int(window_id) * _WINDOW_POSITION_SIZE, _WINDOW_POSITION_SIZE
        )
        _state, p1x, p1y, p2x, p2y = struct.unpack("<Iffff", raw)
        return [p1x, p1y, p2x, p2y]

    @staticmethod
    def IsWindowVisible(window_id: int) -> bool:
        """``:367-373`` → ``is_window_visible`` → ``GetWindowPosition(...)->visible()``.

        The binding (``ui_bindings.cpp:669-672``) and the older shim (``py_ui.h:4857-4864``) agree
        on the test: a null lookup is ``False``, otherwise ``(state & 0x1) != 0`` — the same bit
        ``WindowPosition::visible()`` tests (``context/ui.h:537``).
        """

        from .client import require_client

        client = require_client()
        if not client.resolves(_WINDOW_POSITIONS_ARRAY):
            return False
        base = client._resolve(_WINDOW_POSITIONS_ARRAY)
        if not base or int(window_id) >= _WINDOW_ID_COUNT:
            return False
        state = int.from_bytes(
            client.reader.read(base + int(window_id) * _WINDOW_POSITION_SIZE, 4), "little"
        )
        return (state & _WINDOW_POSITION_VISIBLE_BIT) != 0

    @staticmethod
    def SetWindowVisible(window_id: int, visible: bool) -> None:
        """``:376-383`` → ``set_window_visible`` → ``GW::ui::SetWindowVisible``.

        ``ui_methods.cpp:1690-1696``: ``if (!(g_set_window_visible_func && window_id <
        WindowID_Count)) return false; g_set_window_visible_func(window_id, is_visible ? 1U : 0U,
        nullptr, nullptr); return true;`` — four words, the last two null, which is the callee's
        own signature (``ui_methods.cpp:27``). The binding enqueues it on the game thread
        (``ui_bindings.cpp:678-683``); this port's call already runs there.
        """

        from .client import require_client

        client = require_client()
        if not client.resolves(_SET_WINDOW_VISIBLE_FUNC):
            return
        if int(window_id) >= _WINDOW_ID_COUNT:
            return
        client.call_function(
            _SET_WINDOW_VISIBLE_FUNC,
            CallForm.U32_U32_U32_U32,
            int(window_id),
            1 if visible else 0,
            0,
            0,
        )

    @staticmethod
    def SetWindowPosition(window_id: int, position: list[int]) -> None:
        """``:386-394`` → ``set_window_position`` → ``GW::ui::SetWindowPosition``.

        ``ui_methods.cpp:1698-1704``: ``if (!(g_set_window_position_func && window_id <
        WindowID_Count)) return false; g_set_window_position_func(window_id, info, nullptr,
        nullptr); return true;`` — the caller's ``Context::WindowPosition*`` goes to the client.
        The binding that built that struct is the older runtime's, and it is where the four
        numbers' meaning comes from (``py_ui.h:4873-4889``): ``p1.x``, ``p1.y``, ``p2.x``,
        ``p2.y``, with the client's existing ``state`` word kept.

        **One recorded difference.** That binding also writes the four floats into the client's own
        struct *before* calling the setter, and refuses a list shorter than four
        (``py_ui.h:4875-4885``). This member keeps the shorter-list refusal — it is the binding
        Reforged's member calls — and passes the struct to the client's setter rather than performing
        the extra in-place write, which is what Native's function does with the pointer it is given;
        the difference and its reason are in ``docs/UIMANAGER_PORT.md``.
        """

        from .client import require_client

        client = require_client()
        if len(position) < 4:
            return
        if not client.resolves(_SET_WINDOW_POSITION_FUNC):
            return
        if int(window_id) >= _WINDOW_ID_COUNT:
            return
        state = _window_state(client, int(window_id))
        payload = struct.pack("<Iffff", state, *[float(value) for value in position[:4]])
        address = client.bridge.write_data(_WINDOW_POSITION_OFFSET, payload)
        client.call_function(
            _SET_WINDOW_POSITION_FUNC,
            CallForm.U32_U32_U32_U32,
            int(window_id),
            address,
            0,
            0,
        )

    # -- the dialog family (source lines 396-609) -------------------------

    @staticmethod
    def IsLockedChestWindowVisible() -> bool:
        """``:397-404`` — the chest window's own frame, by its key: ``Frame(
        FrameId.NpcDialog.UseLockpickButton).is_usable``.

        No injected call at all: the source builds a handle from the key table and reads the
        frame's usability, which is the port's own `Frame`.
        """

        return Frame(FrameId.NpcDialog.UseLockpickButton).is_usable

    @staticmethod
    def IsNPCDialogVisible() -> bool:
        """``:407-413`` — ``Frame(FrameId.NpcDialog).is_usable``, as the member above."""

        return Frame(FrameId.NpcDialog).is_usable

    @staticmethod
    def FindDialogOffset() -> None:
        """``:416-454`` — auto-detect ``DIALOG_CHILD_OFFSET`` for the option container.

        Ported as written: the breadth-first walk from the dialog root over the tree's own
        ``children_map()``, the "most children with ``template_type == 1``" choice, the path built
        back up to the root, and the module global assigned at the end. The source's own note is
        kept with it — ``:440-443``: the path records sibling *indices* while the matcher compares
        child key codes, so the offset fast path cannot hit and ``GetDialogButtons`` always falls
        back to the BFS. That is the source's behaviour, preserved deliberately.
        """

        global DIALOG_CHILD_OFFSET

        root = Frame(FrameId.NpcDialog)
        if not root.exists or not root.is_visible:
            return

        children_map = FrameTree.children_map()

        # BFS: pick the container with the most template_type==1 children
        queue = deque([root])
        best = None
        best_count = 0
        while queue:
            cur = queue.popleft()
            kids = [Frame.from_id(c) for c in children_map.get(cur.frame_id, [])]
            count = sum(1 for c in kids if c.is_visible and c.template_type == 1)
            if count > best_count and count >= 2:
                best_count, best = count, cur
            queue.extend(kids)

        if best is None:
            return

        # Build the path from root -> best.
        path: list[int] = []
        cur = best
        while cur != root:
            parent = cur.parent()
            siblings = children_map.get(parent.frame_id, [])
            if cur.frame_id not in siblings:
                return
            path.insert(0, siblings.index(cur.frame_id))
            cur = parent

        DIALOG_CHILD_OFFSET = path

    @staticmethod
    def GetDialogButtons(debug: bool = False) -> list:
        """``:457-491`` — the visible ``template_type == 1`` option buttons, top to bottom.

        The offset lookup first, then the same BFS fallback `FindDialogOffset` describes, with
        ``sort_by_vertical`` ordering the result either way. Ported as written, including the
        default-offset test that triggers the detection once.

        The ``debug`` branch logs through Reforged's ``ConsoleLog``, which is the injected
        runtime's in-client console (``py4gwcorelib_src/Console.py``, 38 lines that *are* that
        console). It has nowhere to go here — the same finding `ItemArray` records for its own
        ``Console.Log`` lines — so the branch keeps the source's control flow and the log is
        replaced by nothing.
        """

        # detect offset once
        if DIALOG_CHILD_OFFSET == DEFAULT_OFFSET:
            UIManager.FindDialogOffset()

        def _is_button(frame: Frame) -> bool:
            return frame.is_visible and frame.template_type == 1

        # try the offset first
        valid = [
            f
            for f in FrameTree.frames_at_path(NPC_DIALOG_HASH, DIALOG_CHILD_OFFSET)
            if _is_button(f)
        ]
        if valid:
            ordered = FrameTree.sort_by_vertical(valid)
            if debug:
                # ``ConsoleLog("DialogHelper", f"Offset IDs -> {ordered}", Console.MessageType.Info)``
                pass
            return ordered

        # fallback BFS over the whole dialog subtree
        root = Frame(FrameId.NpcDialog)
        if not root.exists:
            return []

        valid = [f for f in FrameTree.descendants(root) if _is_button(f)]
        ordered = FrameTree.sort_by_vertical(valid)
        return ordered

    @staticmethod
    def ClickDialogButton(choice: int, debug: bool = False) -> bool:
        """``:494-513`` — click the Nth dialog option (1-based).

        The bounds test, then ``target.click()`` — this port's `Frame.click`, which is the same
        ``ui::ButtonClick`` and was verified against the live client on 2026-09-27. The debug
        branch's ``ConsoleLog`` calls have nowhere to go, as in `GetDialogButtons`.
        """

        buttons = UIManager.GetDialogButtons(debug)
        idx = choice - 1
        if idx < 0 or idx >= len(buttons):
            if debug:
                # ``ConsoleLog("DialogHelper", f"Choice #{choice} out of range", Warning)``
                pass
            return False

        target = buttons[idx]
        if debug:
            # ``ConsoleLog("DialogHelper", f"Clicking dialog choice #{choice} -> frame {target}", Info)``
            pass
        target.click()
        return True

    @staticmethod
    def GetDialogButtonCount(debug: bool = False) -> int:
        """``:516-533`` — how many visible dialog-button frames there are."""

        buttons = UIManager.GetDialogButtons(debug)
        count = len(buttons)

        if debug:
            # ``ConsoleLog("DialogHelper", f"Dialog button count {count}", Info)``
            pass

        return count

    @staticmethod
    def GetDialogButtonFrames(debug: bool = False) -> list[tuple[Frame, tuple[int, int, int, int]]]:
        """``:536-595`` — ``(frame, rect)`` for every visible dialog button, ordered.

        The offset lookup first, then the BFS fallback, and both sort by ``x[1][0]`` — which is the
        **left** edge, not the top the docstring says. The source's own note (``:590-592``) is kept
        with it: the order decides which button a choice index maps to, so it is preserved
        deliberately.

        **Two places where the source's own words and its body disagree, recorded rather than
        smoothed over.** Its annotation says ``list[tuple[int, tuple[int, int, int, int]]]`` (``:536``)
        and both comprehensions build ``(f, f.rect)`` — the **handle**, not the frame's id, which is
        what this signature states, because the handle is what a caller receives. And its docstring
        says the tuples are "sorted by their vertical position" while the key is ``x[1][0]``, the
        left edge (``:560-561``, ``593``).
        """

        if DIALOG_CHILD_OFFSET == DEFAULT_OFFSET:
            UIManager.FindDialogOffset()

        # --- Attempt offset lookup first ---
        valid_frames = [
            (f, f.rect)
            for f in FrameTree.frames_at_path(NPC_DIALOG_HASH, DIALOG_CHILD_OFFSET)
            if f.is_visible and f.template_type == 1
        ]

        if debug:
            # ``ConsoleLog("DialogHelper", f"Dialog button frames with offset ...", Info)``
            pass

        # --- Sort by top_on_screen using cached tuples ---
        valid_frames.sort(key=lambda x: x[1][0])

        # If we found frames, return immediately (no fallback needed)
        if valid_frames:
            return valid_frames

        # --- BFS fallback ---
        root = Frame(FrameId.NpcDialog)
        if not root.exists:
            return []

        result = [
            (f, f.rect)
            for f in FrameTree.descendants(root)
            if f.is_visible and f.template_type == 1
        ]

        result.sort(key=lambda x: x[1][0])

        return result

    @staticmethod
    def ConfirmMaxAmountDialog() -> None:
        """``:598-609`` — confirm the max-amount dialog by clicking the two buttons it may have."""

        max_amount = Frame(FrameId.MaxButton)
        drop_offer_confirm = Frame(FrameId.OkButton)

        if max_amount.exists:
            max_amount.click()

        if drop_offer_confirm.exists:
            drop_offer_confirm.click()


# --------------------------------------------------------------------------
def _wide_units(text: str) -> list[int]:
    """One Python string as the wide array a ``std::wstring`` conversion hands the client.

    ``py::`` converts a ``str`` to ``std::wstring``, so the client's validator and its decoder see
    one code unit per character — and a terminator after them, which is what
    ``std::wstring::c_str()`` adds and what both of those walks need to find the end of the range.
    """

    return [ord(character) for character in text] + [0x0000]


def _wide_units_from_bytes(raw: bytes) -> list[int]:
    """One ``py::bytes`` as the wide array a ``reinterpret_cast<const wchar_t*>`` gives the client.

    ``UIManager.IsValidEncBytes``'s own source reads the buffer as raw ``wchar_t`` units
    (``py_ui.h:4606-4615``), so this is a little-endian word walk and not a decode.
    """

    return [
        int.from_bytes(raw[index : index + 2], "little")
        for index in range(0, len(raw) - (len(raw) % 2), 2)
    ]


def _wide_bytes(text: str) -> bytes:
    """A Python string as the wide bytes the port places in the client for a decode."""

    return b"".join(struct.pack("<H", unit) for unit in _wide_units(text))


def _window_state(client: Any, window_id: int) -> int:
    """The client's own ``state`` word for a built-in window (``context/ui.h:533``).

    ``SetWindowPosition``'s caller passes four floats and no state, and the binding that built the
    struct for it kept the client's word (``py_ui.h:4873-4889``); this is that read, once, at the
    entry the call is about.
    """

    if not client.resolves(_WINDOW_POSITIONS_ARRAY):
        return 0
    base = client._resolve(_WINDOW_POSITIONS_ARRAY)
    if not base:
        return 0
    return int.from_bytes(
        client.reader.read(base + window_id * _WINDOW_POSITION_SIZE, 4), "little"
    )


def _button_action_frame_id(client: Any) -> int:
    """``GetButtonActionFrame()`` (``ui_methods.cpp:161-164``), through the client's own lookups.

    Two steps, both native's: ``GetHashByLabel(L"Game")`` — the client's own hasher over the label,
    handed a wide string this project places in the block (``ui_methods.cpp:542-546``) — and then
    ``GetChildFrame(frame, 6)``, which is ``g_get_child_frame_id_func`` walked once
    (``ui_methods.cpp:589-607``, the same function ``GetChildFrameID`` uses). Between them sits
    ``GetFrameIDByHash``'s array scan (``:556-568`` for the label form, ``:575-588`` for the hash
    form), which is the port's ``FrameArray.frame_id_by_hash``.

    A step that does not resolve answers ``0``, which is the source's own ``nullptr`` — and
    ``SendFrameUIMessage`` never sees it, because the member returns first.
    """

    hash_value = _hash_for_label(client, _BUTTON_ACTION_FRAME_LABEL)
    if not hash_value:
        return 0
    parent = int(client.frame_array.frame_id_by_hash(hash_value))
    if not parent:
        return 0
    if not client.resolves(_GET_CHILD_FRAME_ID_FUNC):
        return 0
    return int(
        client.call_function(
            _GET_CHILD_FRAME_ID_FUNC,
            CallForm.U32_U32,
            parent,
            _BUTTON_ACTION_CHILD_INDEX,
        ).value
    )


def _hash_for_label(client: Any, label: str) -> int:
    """``ui::GetHashByLabel`` (``ui_methods.cpp:542-546``): the client hashes the label itself.

    ``g_create_hash_from_wchar_func(frame_label, -1)`` — a two-word call over a **wide string the
    caller owns**, so the label is placed in the block's data region and its address passed, which is
    the same shape ``UIManager.SetStringPreference`` uses. The second argument is native's literal
    ``-1`` as the word it is in the record.
    """

    from .client import require_client

    if not client.resolves(_CREATE_HASH_FROM_WCHAR_FUNC):
        return 0
    address = client.bridge.write_data(_LABEL_ARGUMENT_OFFSET, _wide_bytes(label))
    return int(
        client.call_function(
            _CREATE_HASH_FROM_WCHAR_FUNC,
            CallForm.U32_U32,
            address,
            _HASH_LABEL_LENGTH,
        ).value
    )


def _send_key_action(frame_id: int, key: int, message_id: int) -> None:
    """Place one ``packet::KeyAction`` and send it to a frame, as ``GW::ui::Keydown`` does.

    ``ui_methods.cpp:1408-1416``: ``packet::KeyAction action{key}`` — a one-word packet — sent to
    ``target ? target : GetButtonActionFrame()``'s callbacks as ``kKeyDown``/``kKeyUp`` through
    ``SendFrameUIMessage``, which is the client's ``__thiscall`` sender this port already drives for
    `Frame.send_message`. The packet goes into the block's data region because the client is handed a
    pointer to it, and ``frame_id == 0`` is the source's own null: the button-action frame is
    resolved first, exactly as the binding's ``frame_id ? GetFrameById(frame_id) : nullptr`` does.
    """

    from .client import require_client
    from .ui.frame import FrameStruct, is_valid_frame_pointer

    client = require_client()
    if not client.resolves(_SEND_FRAME_UI_MESSAGE_FUNC):
        return
    target_id = int(frame_id) or _button_action_frame_id(client)
    if not target_id:
        return
    array = client.frame_array
    pointer = array.read_frame_pointer(target_id)
    if not is_valid_frame_pointer(pointer):
        return
    record = array.get(target_id)
    if record is None or not int(record.frame_callbacks.m_size):
        return
    address = client.bridge.write_data(_KEY_ACTION_OFFSET, struct.pack("<I", int(key)))
    client.call_function(
        _SEND_FRAME_UI_MESSAGE_FUNC,
        CallForm.FASTCALL_U32_U32_U32,
        pointer + FrameStruct.frame_callbacks.offset,
        0,
        int(message_id),
        address,
        0,
    )
