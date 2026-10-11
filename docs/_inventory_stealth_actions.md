# Inventory: what Py4GW Stealth's own Python can *do* to the game (action surface)

**Scope.** This document inventories the **action surface** of the project's own Python library: what it can
*change*, as opposed to what it can read. It covers the files named in the request:

`py4gw/agent.py`, `py4gw/agent_array.py`, `py4gw/item.py`, `py4gw/inventory.py`, `py4gw/merchant.py`,
`py4gw/skill.py`, `py4gw/skillbar.py`, `py4gw/party.py`, `py4gw/map.py`, `py4gw/player.py`, `py4gw/quest.py`,
`py4gw/dialog.py`, `py4gw/pathing.py`, `py4gw/camera.py`, `py4gw/effect.py`, `py4gw/ui_manager.py`,
`py4gw/game_thread/{__init__,bridge,callbacks,shared_block,payload,hooker,patcher,packets}.py`,
`py4gw/client.py`, `py4gw/native_src/chat/chat.py`

plus the modules those files delegate to, where the delegation is the mechanism
(`py4gw/native_src/item/py_inventory.py`, `py4gw/native_src/methods/map_methods.py`,
`py4gw/native_src/quest/py_quest.py`, `py4gw/ui/preferences.py`, `py4gw/ui/async_decode.py`,
`py4gw/frame_tree/frame.py`, `py4gw/listeners.py`, `py4gw/memory/memory_manager.py`).

**Method.** Every claim below is from reading the source at the cited line. Nothing here is a live-client
result: this document is source inspection. No file was modified except this one; no script was run against a
game process; no client was touched.

**Classification used (exactly one per member).**

| class | meaning |
| --- | --- |
| **READ** | returns data read out of the client; no side effect on the client |
| **ACTION** | changes game state (or the client's own execution/thread/CG state, where noted) |
| **CAPABILITY** | sets up or drives the in-client capability layer: hooks, typed calls, callbacks, the shared block, decodes |
| **DECLARED, NO GAME REACH** | a member the sources declare as an action whose *actual* body performs no client interaction (a documented no-op, or host-side state only) |
| **RAISES** | body not written; raises `NotImplementedError` (message quoted) |

**A member can be both ACTION and CAPABILITY in mechanism.** A member is classified by *what it does*
(ACTION if it changes game state), and the *mechanism* column says it does it by driving the capability layer.
The capability layer is never the point of an ACTION; it is how the ACTION reaches the client.

**Counting convention (stated so the headline number is reproducible).** Both the Reforged façade class and
the Native binding class it calls are **public classes**, so both are counted. `Inventory.PickUpItem` and
`PyInventory.PickUpItem` are therefore two ACTION members that implement one behaviour. See §8 for both
counts.

---

## 1. The five mechanisms a member can use to reach the game

Everything the library does to the game goes through one of these. There is no sixth.

### M1 — A typed call on the client's own thread through the capability layer

The host publishes a `CALL` command into the shared block; the client's game thread, running through a
**hook the library placed at its entry**, executes the call and writes the result back.

* publish: `ConnectedClient.call_function` (`py4gw/client.py:1097-1131`), `call_address`
  (`:1133-1165`), `send_ui_message` (`:1167-1195`), `send_ui_message_raw` (`:1197-1222`) →
  `Bridge.call` (`py4gw/game_thread/bridge.py:866-886`) → `Bridge.publish_call` (`:844-864`) →
  `Bridge.publish` (`:738-791`).
* the argument shapes are `CallForm` (`py4gw/game_thread/shared_block.py:310-424`); the operation is
  `Operation.CALL` (`:300`).
* the call runs in the **emitted dispatcher** (`py4gw/game_thread/payload.py:1373`, built by
  `build_dispatcher`, installed at `bridge.py:440-444`), which bounds the target to the client module
  (`bridge.py:392-396`) and refuses a bad target with `RESULT_NO_TARGET` / `RESULT_BAD_TARGET`
  (`shared_block.py:535-536`).
* the target is resolved from a **pattern catalog name** (`offsets/*.json`) or handed in as an address; a
  descriptor (target + form) is written into the **call table in the client**
  (`ConnectedClient._descriptor_slot`, `client.py:1224-1271`), so no address ever travels through the queue
  (`shared_block.py:1047-1062`).
* a call's return register comes back in `CommandRecord.value` (`shared_block.py:809-831`).

### M2 — A UI message sent through the client's own sender

The client's `GW::ui::SendUIMessage(UIMessage, void* wparam, void* lparam)` is itself **called through M1**
and is also the function the library *observes*. Two shapes exist:

* **packed** — `ConnectedClient.send_ui_message` → `CallForm.UI_MESSAGE`: the dispatcher builds a zeroed
  two-word payload from the command's words and calls `SendUIMessage(arg1, &payload, 0)`
  (`client.py:1183-1195`, `shared_block.py:319-330`).
* **raw** — `ConnectedClient.send_ui_message_raw` → `CallForm.U32_U32_U32`: the caller's two words go through
  untouched (`client.py:1197-1222`).

The address used is `ui.send_ui_message_func`, resolved **before** its entry was patched and then held
(`client.py:240-246`, `:477-480`, `:1191`), because re-resolving a patched entry walks back to the previous
function (`client.py:766-769`).

### M3 — A frame message (`SendFrameUIMessage`)

`ui.send_frame_ui_message_func`, a `__thiscall` whose `this` is the frame's callback array in **ECX**
(`shared_block.py:374-383`, `CallForm.FASTCALL_U32_U32_U32`), driven with `CallForm.FASTCALL_U32_U32_U32`:

* `UIManager.Keydown/Keyup/Keypress` (`py4gw/ui_manager.py:1049-1088` → `_send_key_action`,
  `:1539-1575`);
* `Frame.click` — a `packet::MouseAction` sent to the **parent** frame as `kMouseClick2`
  (`py4gw/frame_tree/frame.py:1735-1817`);
* `Frame.send_message` (`frame.py:1867-1907`).

`Frame.send_message_text` (`frame.py:1909`) is the same call with a wide string and **raises**
(`frame.py:1917-1922`), so it is not a usable mechanism today.

### M4 — A write into the client performed **inside the client**, by the payload's `WRITE_MEMORY`

`Operation.WRITE_MEMORY` (`shared_block.py:301-307`) copies bytes from the block's data region to a target
address **on the game thread, inside the hooked function** — the library's stand-in for Native's
`GW::game_thread::Enqueue` (`shared_block.py:302-307`). Used by the camera field writers
(`py4gw/camera.py:126-145`), `UIManager.SetKeyMappings` (`ui_manager.py:1038-1046`),
`UIManager.SetFPSLimit` (`ui/preferences.py:337-368`), `MapMethods.TravelGH(key=…)`
(`native_src/methods/map_methods.py:168-182`). The host writes only into the block, never into game memory.

### M5 — A byte patch written by the host (the only host-side write into the client's own code)

`Patcher.patch` (`py4gw/game_thread/patcher.py:116-148`) — read-and-verify, suspend every thread, refuse if
any thread's EIP is inside the window, re-verify, `VirtualProtectEx` + write + `FlushInstructionCache` +
restore protection, resume (`patcher.py:260-268`). `Patcher.restore` refuses when the bytes are no longer the
ones it wrote (`:150-171`). Used for:

* the four entry hooks installed by `connect()` (`bridge.py:463`, `:485-491`, `:532-538`, `:564-569`;
  `hooker.install` → `patcher.patch`, `hooker.py:772-776`);
* this library's own **stale-patch repair** and the client's own bytes going back
  (`client.py:714`, `:732`);
* the **camera unlock and fog patches** (`camera.py:228-241`) — the only ACTIONs whose mechanism is M5.

### What is *not* a mechanism here

* **No input synthesis to the game window.** There is no `SendInput`, `keybd_event` or `mouse_event`
  anywhere in `py4gw/`. "Keys" are frame messages (M3) delivered to the client's own callbacks, not OS
  input. (`py4gw/win32/win32.py` and `py4gw/gui/native.py` use `SendMessageW`/`PostMessageW` only for the
  **controller's own** windows — e.g. `gui/native.py:60-63`, `:159`, `:185`.)
* **No DLL injection.** Code and data are placed by `WriteAccess.allocate/write/protect`
  (`py4gw/win32/write_access.py:189-249`) and executed in place; no module is loaded.
* **No socket, and no packet construction.** There is no `socket`/`WSASend`, no `ToS`/StoC emulation
  implementation, and no code that builds a client→server packet. See §6.

---

## 2. `py4gw/client.py` — connect / disconnect and the capability surface

### 2.1 Module-level functions

| member (line) | signature | returns | class | mechanism |
| --- | --- | --- | --- | --- |
| `connect` (`:1894`) | `connect(process: dict[str, Any] \| int, game_thread: bool = True) -> ConnectedClient` | the current client | **CAPABILITY** | `disconnect()` first (`:1910`), then constructs `ConnectedClient` (`:1911`) |
| `disconnect` (`:1915`) | `disconnect() -> None` | `None` | **CAPABILITY** | clears the registry **before** closing (`:1925-1928`), so a refusing close cannot leave a dead current client |
| `current_client` (`:1931`) | `current_client() -> ConnectedClient \| None` | the current client or `None` | READ | registry only |
| `require_client` (`:1937`) | `require_client() -> ConnectedClient` | the current client | READ | raises `RuntimeError("No Guild Wars client is connected. Call py4gw.connect() first.")` (`:1947-1949`) |

### 2.2 `ConnectedClient` — public members

Signatures are exact. Every one of `read_*`/`is_*`/`*_context` returns data read from the client and is
**READ**; they are listed in §2.4.

| member (line) | signature | class |
| --- | --- | --- |
| `__init__` (`:210`) | `(self, process: dict[str, Any] \| int, win32: Win32 \| None = None, perf_counter: PerfCounter \| None = None, game_thread: bool = True) -> None` | **CAPABILITY** |
| `close` (`:1786`) | `close() -> None` | **CAPABILITY** |
| `callbacks` (`:1006`) | `-> Callbacks` | **CAPABILITY** |
| `bridge` (`:1017`) | `-> Bridge` | **CAPABILITY** |
| `access` (`:1028`) | `-> WriteAccess` | **CAPABILITY** |
| `watch` (`:1061`) | `(self, message: int) -> int` | **CAPABILITY** |
| `unwatch` (`:1086`) | `(self, message: int) -> None` | **CAPABILITY** |
| `call_function` (`:1097`) | `(self, name: str, form: CallForm, arg1: int = 0, arg2: int = 0, arg3: int = 0, arg4: int = 0, arg5: int = 0, timeout_ms: int \| None = None) -> CommandRecord` | **CAPABILITY** (and the M1 path every ACTION uses) |
| `call_address` (`:1133`) | `(self, target: int, form: CallForm, arg1: int = 0, …, arg5: int = 0, timeout_ms: int \| None = None) -> CommandRecord` | **CAPABILITY** |
| `send_ui_message` (`:1167`) | `(self, message_id: int, wparam: int = 0, lparam: int = 0) -> CommandRecord` | **CAPABILITY** / M2 packed |
| `send_ui_message_raw` (`:1197`) | `(self, message_id: int, wparam: int = 0, lparam: int = 0) -> CommandRecord` | **CAPABILITY** / M2 raw |
| `resume_suspended_threads` (`:976`) | `(self) -> int` | **ACTION** (client thread state, not game state) |
| `target_id` (`:1039`) | `-> int` | READ |
| `chained_hooks` (`:1768`) | `-> tuple[str, ...]` | READ |
| `suspended_threads` (`:1000`) | `-> int` | READ |
| `pid`, `process`, `reader`, `is_connected`, `is_logged_in` (`:1274`, `:1280`, `:1286`, `:1762`, `:1781`) | properties | READ |

**`__init__` — CAPABILITY.** Elevation is asserted **once, first**: `if not self._win32.is_elevated(): raise
RuntimeError(...)` naming the four refused rights (`client.py:255-263`). Then four client functions are
resolved **and their entry bytes verified before anything is written** (`:451-476`), and
`Bridge.install` is called with the placements (`:482-504`):

| hooked function | catalog name | displaced bytes | role |
| --- | --- | --- | --- |
| `game_thread.leave_game_thread_func` | `_GAME_THREAD_HOOK` (`:109`) | `55 8B EC 81 EC 20 02 00 00` (`:115`) | the game thread that runs M1 work |
| `ui.send_ui_message_func` | `_GAME_THREAD_OBSERVE` (`:110`) | `55 8B EC 8B 45 08 83 F8 56` (`:116`) | observed **after** the call |
| `effects.post_process_effect_func` | `_EFFECTS_HOOK` (`:124`) | `55 8B EC 83 EC 08` (`:125`) | observed, alcohol capture |
| `render.end_scene_func` | `_RENDER_HOOK` (`:131`) | `55 8B EC 83 EC 48` (`:136`) | argument captured into a data slot |

Then it registers the dialog/chat/effects/target callbacks (`:532-566`), installs the merchant listener —
**which replaces five of the client's own StoC packet handler entries** (`:577-577`, `listeners.py:318`) —
and starts the event listener thread (`:578-579`). A failure anywhere inside that startup calls `close()`
while the connection is still current and re-raises, adding a note if the teardown also failed
(`:580-594`). `game_thread=False` performs none of it: the read-only connection (`:423-424`, `:217-227`).

**`close` — CAPABILITY.** Order, and why: `Dialog.terminate()` **before** the listener stops (the drain needs
the listener) (`:1799-1807`); `listeners.Shutdown()` — putting the client's own packet handlers back, which
runs through the hook the bridge is about to remove (`:1809-1819`); stop the listener (`:1821-1826`); stop
the string-table warm-up (`:1832-1835`); give decode slots back (`:1840-1845`); reset the alcohol capture
(`:1849-1854`); then `bridge.remove(free_allocations=True)` and `access.close()` + `reader.close()`
(`:1861-1867`); a handler failure is re-raised at the end (`:1869-1870`).

**`watch(message: int) -> int` — CAPABILITY.** Finds an existing slot holding `message`, else writes the id
into the first empty slot of the **watch list in the client** — a direct host write of 4 bytes at
`bridge.watch_address + slot*WATCH_SIZE` (`:1070-1081`) — and returns the slot. The observer re-reads the list
on every call, so no reinstall is needed (`:1062-1068`). Precondition: a game-thread connection (`bridge`
property, `:1017-1025`). Failure: `RuntimeError("the watch list holds 8 message ids and is full.")`
(`:1082-1084`).

**`unwatch(message: int) -> None` — CAPABILITY.** Writes 8 zero bytes over the entry (`:1090-1093`), else
raises `ValueError(f"pid {self._pid}: message {message:#x} is not watched.")` (`:1095`).

**`call_function(name, form, arg1…arg5, timeout_ms=None) -> CommandRecord` — CAPABILITY.** Refuses
`CallForm.UI_MESSAGE` with `ValueError("call_function drives the typed forms; a UI message carries a packed
payload and is published with publish_call instead.")` (`:1124-1128`). A descriptor slot is allocated per
`(name, form)` and the address is resolved once (`:1130`, `_descriptor_slot:1246-1271`); the slot write is a
host write into the **call table** allocation (`:1266-1269`). **The one precondition the dispatcher cannot
make**: the target must be inside the client's `.text` section, checked on the host
(`:1250-1257`), because executing an in-module data address does not fail — it ran data on 2026-09-25
(`:1234-1243`). Failure: that `RuntimeError`, `RuntimeError` when all 16 descriptor slots are taken
(`:1259-1263`), `TimeoutError` from `Bridge.wait` (`bridge.py:814-819`), or a `CommandRecord` whose
`state is FAILED` with `result` one of `-101…-105` (`shared_block.py:528-539`). Returns the completed
`CommandRecord`; `value` is the callee's return register.

**`call_address(target, form, ...) -> CommandRecord` — CAPABILITY.** Same contract, for an address the caller
resolved because the catalog has no name for it (the dialog loader is the worked case, `:1147-1155`).

**`send_ui_message(...)` / `send_ui_message_raw(...) -> CommandRecord` — CAPABILITY.** Both call the client's
own sender through M1 (see §1/M2). `send_ui_message` passes the caller's `wparam` as the second word of a
zeroed two-word payload (`:1183-1188`); `send_ui_message_raw` passes both words untouched
(`:1202-1211`). The address is the one held from install; the fallback is a fresh resolve (`:1191`,
`:1218`).

**`resume_suspended_threads() -> int` — ACTION.** Resumes every client thread once and counts how many were
actually suspended (`:988-997`). Mechanism: `WriteAccess.suspend_thread`/`resume_thread`
(`win32/write_access.py:301-315`). Precondition: a game-thread connection — else
`RuntimeError("this connection is not managing the game thread.")` (`:984-985`).

### 2.3 `ConnectedClient` — READ members (every public read member, with line)

`read_game_context:1308`, `map_context:1314`, `read_map_context:1319`, `read_mission_map_context:1328`,
`read_salvage_session:1344`, `dialog_tables:1350`, `frame_array:1363`, `frame_tree:1375`,
`world_map_context:1381`, `mission_map_context:1387`, `salvage_session:1393`, `read_world_map_context:1398`,
`gameplay_context:1414`, `read_gameplay_context:1419`, `pre_game_context:1425`, `read_pre_game_context:1430`,
`server_region:1436`, `read_server_region:1441`, `player_agent_id:1447`, `read_player_agent_id:1452`,
`instance_info:1462`, `read_instance_info:1467`, `text_parser:1473`, `read_text_parser:1478`,
`available_characters:1484`, `read_available_characters:1489`, `party_context:1495`, `read_party_context:1500`,
`guild_context:1506`, `read_guild_context:1511`, `acc_agent_context:1517`, `read_acc_agent_context:1522`,
`memory_manager:1528`, `camera:1539`, `read_camera_context:1544`, `friend_list:1550`, `read_friend_list:1555`,
`chat_buffer:1561`, `read_chat_buffer:1566`, `is_typing:1571`, `world_context:1577`, `read_world_context:1582`,
`trade_context:1588`, `read_trade_context:1593`, `is_item_offered:1598`, `item_context:1605`,
`read_item_context:1610`, `read_item_bags:1615`, `read_item_records:1621`, `read_inventory:1629`,
`read_item_formulas:1635`, `read_composite_model_infos:1640`, `read_pvp_item_upgrades:1647`,
`read_pvp_items:1654`, `is_storage_open:1660`, `account_context:1666`, `read_account_context:1671`,
`gadget_context:1677`, `read_gadget_context:1682`, `agent_array:1688`, `skill_constants:1707`,
`read_skill:1712`, `current_tooltip:1724`, `read_current_tooltip:1729`, `cinematic:1735`,
`read_cinematic_context:1740`, `read_char_context:1745`, `character_name:1752`, `__enter__:1872`,
`__exit__:1875`.

---

## 3. The capability layer — `py4gw/game_thread/`

### 3.1 `Bridge` (`bridge.py:132`) — the host side of the queue

| member (line) | signature | returns / meaning | class |
| --- | --- | --- | --- |
| `__init__` (`:135`) | `(self, access: WritableTarget, pid: int, timeout_ms: int = DEFAULT_TIMEOUT_MS) -> None` | — | CAPABILITY |
| `install` (`:370`) | `(self, target: int, displaced: bytes, session_id: int \| None = None, calls: Mapping[int, Descriptor] \| None = None, module_base: int = 0, module_size: int = 0, watch: Sequence[tuple[int, int]] = (), observing: tuple[int, bytes] \| None = None, effects_observing: tuple[int, bytes] \| None = None, effects_watch: Sequence[tuple[int, int]] = (), capturing: tuple[int, bytes] \| None = None, loaded_modules: Sequence[tuple[int, int]] = ()) -> None` | — | CAPABILITY |
| `remove` (`:653`) | `(self, free_allocations: bool = False) -> None` | — | CAPABILITY |
| `install_packets` (`:288`) | `(self, table_address: int, wanted: Mapping[int, int]) -> tuple[PacketStub, ...]` | the placed stubs | CAPABILITY |
| `remove_packets` (`:313`) | `(self, free_code: bool = False) -> tuple[int, ...]` | restored headers | CAPABILITY |
| `publish` (`:738`) | `(self, operation: Operation \| int, arg0: int = 0, … arg5: int = 0) -> int` | the sequence number | CAPABILITY |
| `wait` (`:793`) | `(self, sequence: int, timeout_ms: int \| None = None) -> CommandRecord` | the completed record | CAPABILITY |
| `submit` (`:822`) | `(self, operation: Operation \| int, arg0: int = 0, …, arg5: int = 0, timeout_ms: int \| None = None) -> CommandRecord` | the completed record | CAPABILITY |
| `publish_call` (`:844`) | `(self, slot: int, arg1: int = 0, …, arg5: int = 0) -> int` | the sequence number | CAPABILITY |
| `call` (`:866`) | `(self, slot: int, arg1: int = 0, …, arg5: int = 0, timeout_ms: int \| None = None) -> CommandRecord` | the completed record | CAPABILITY |
| `events` (`:888`) | `(self) -> list[EventRecord]` | events since the last read, oldest first | CAPABILITY (and it advances the host's event counter — a side effect on the layer, not the game) |
| `completions` (`:925`) | `(self) -> list[EventRecord]` | the `COMMAND_COMPLETE` subset | CAPABILITY |
| `data_address` (`:1039`) | `(self, offset: int, size: int = 0) -> int` | the client address of a block span | CAPABILITY |
| `write_data` (`:1052`) | `(self, offset: int, payload: bytes) -> int` | the address the bytes now sit at | CAPABILITY |
| `read_data` (`:1059`) | `(self, offset: int, size: int) -> bytes` | — | READ |
| `begin_decode` (`:1074`) | `(self, encoded: bytes) -> int` | the decode slot | CAPABILITY |
| `complete_decode` (`:1117`) | `(self, slot: int, text: str) -> None` | — | CAPABILITY |
| `release_decode` (`:1143`) | `(self, slot: int) -> None` | — | CAPABILITY |
| `decode_state` (`:1158`) | `(self, slot: int) -> DecodeState` | — | READ |
| `take_decoded_string` (`:1167`) | `(self, slot: int) -> tuple[str, bool]` | `(text, truncated)` | CAPABILITY |
| `decode_input_address` (`:1105`), `decode_slot_address` (`:1111`) | `(self, slot: int) -> int` | an address in the client | CAPABILITY |
| `decodes_in_flight` (`:1190`) | `(self) -> int` | — | READ |
| `render_context_address` (`:637`) | `(self) -> int` | the last `EndScene` first argument | READ |
| `header` (`:725`) | `(self) -> BlockHeader` | validated header | READ |
| `hits` (`:945`) | `(self) -> int` | hook fire count | READ |
| `wait_for_hits` (`:950`) | `(self, minimum_delta: int = 1, timeout_ms: int \| None = None) -> int` | the count | CAPABILITY (turns a placement into evidence) |
| `require_hooker` (`:936`) | `(self) -> Hooker` | — | CAPABILITY |
| `packet_table` (`:337`), `read_packet_table` (`:342`) | see source | handler table | READ |
| properties `pid:184`, `timeout_ms:190`, `installed:196`, `observing:202`, `watch_address:211`, `observer_address:217`, `observing_effects:223`, `effects_watch_address:232`, `effects_observer_address:238`, `block_address:244`, `access:250`, `module_range:261`, `loaded_modules:271`, `call_table_address:281`, `dispatcher_address:352`, `decoder_address:358`, `packet_headers:326`, `packets:332`, `observing_render:629` | properties | — | READ (they report what was placed) |

**What `install` writes, and where.** Block (`bridge.py:437`, `_place_block:1011-1027`, read back and
session-checked), call table (`:438`, `_place_call_table:990-1009`), dispatcher machine code written and left
`PAGE_EXECUTE_READ` (`:440-444`), decoder stub (`:450-454`), then the hook itself **last** (`:456-463`),
then — only if asked for — the watch list (`:467`) + observer (`:468-491`), the effects observer
(`:513-538`), and the render capture (`:547-569`). On any failure every entry patch already placed is
**removed first**, then the allocations are freed (`:570-612`); if the rollback itself failed, a
`RuntimeError` says the client may still be patched (`:606-611`).

**`remove` order.** Packet handlers first — writing an entry back is itself an M1 command, so it needs the
block and the dispatch hook that the rest of the method takes away (`:653-661`, `:679`); then the render
capture, the effects observer, the observer, and the main hook (`:681-689`); with `free_allocations=True` a
decode still in flight is refused rather than freed underneath (`:691-698`) and everything is released
(`:699-721`).

**Protocols and records used above:** `WritableTarget` (`hooker.py:167-172`, extends `TargetAccess`,
`patcher.py:49-70`), `PacketBridge` (`packets.py:57-79`), `EventSource` (`callbacks.py:42-45`).

### 3.2 `Hooker` (`hooker.py:652`)

| member (line) | signature | returns / meaning | class |
| --- | --- | --- | --- |
| `__init__` (`:659`) | `(self, access: WritableTarget, pid: int, block_address: int, dispatcher_address: int, timeout_ms: int = 2000) -> None` | — | CAPABILITY |
| `install` (`:697`) | `(self, name: str, target: int, displaced: bytes, forwarded_arguments: int = 0, after: bool = False) -> None` | — | CAPABILITY |
| `enable` (`:795`) / `disable` (`:803`) | `(self, name: str) -> None` | — | CAPABILITY |
| `hits` (`:811`) | `(self, name: str) -> int` | — | READ |
| `wait_for_hits` (`:822`) | `(self, name: str, minimum_delta: int = 1, timeout_ms: int = 2000) -> int` | — | CAPABILITY |
| `in_flight` (`:848`) | `(self, name: str) -> int` | calls inside the stub now | READ |
| `remove` (`:860`) | `(self, name: str, free_code: bool = False) -> None` | — | CAPABILITY |
| `remove_all` (`:923`) | `(self) -> None` | — | CAPABILITY |
| `pid` (`:686`), `installed` (`:692`) | properties | — | READ |

`install` refuses when the name is taken, when `target <= 0`, and when `displaced` is shorter than
`MINIMUM_PATCH` (`:724-734`); the entry patch is written last, so nothing can reach the stub before it
exists (`:720-721`, `:772-776`) and an earlier failure frees only what it made (`:777-783`). `remove` refuses
to free a stub another runtime has patched (`:931`, cited at `:934-943`) and refuses to free under a live
instruction pointer — it waits on the in-flight count and raises naming the count when it does not drain
(`:897-910`).

### 3.3 `Patcher` (`patcher.py:73`)

`__init__(self, access: TargetAccess, pid: int, timeout_ms: int = DEFAULT_TIMEOUT_MS) -> None` (`:81`);
`patch(self, address: int, expected: bytes, replacement: bytes) -> None` (`:116`);
`restore(self, address: int) -> None` (`:150`); `restore_all(self) -> None` (`:173`); properties `pid`
(`:105`), `installed` (`:111`). All **CAPABILITY** (M5). `patch` refuses a length change (`:186-190`), a
re-patch of an address it already holds (`:120-124`), a byte mismatch (`:192-201`), a thread inside the
window after the deadline (`:140-145`, `TimeoutError`), and a zero instruction pointer (`:251-255`).

### 3.4 `Callbacks` (`callbacks.py:48`) and `EventListener` (`callbacks.py:109`)

| member (line) | signature | returns | class |
| --- | --- | --- | --- |
| `Callbacks.__init__` (`:51`) | `(self, source: EventSource) -> None` | — | CAPABILITY |
| `register` (`:57`) | `(self, kind: EventKind \| int, handler: EventHandler) -> None` | — | CAPABILITY |
| `unregister` (`:66`) | `(self, kind: EventKind \| int, handler: EventHandler) -> None` | — | CAPABILITY |
| `kinds` (`:78`) | `(self) -> tuple[int, ...]` | — | READ |
| `pump` (`:83`) | `(self) -> int` | handler calls run | CAPABILITY |
| `handle` (`:92`) | `(self, records: list[EventRecord]) -> int` | handler calls run | CAPABILITY |
| `EventListener.__init__` (`:130`) | `(self, source: EventSource, registry: Callbacks, interval_ms: float = DEFAULT_INTERVAL_MS) -> None` | — | CAPABILITY |
| `start` (`:161`) | `(self) -> None` | — | CAPABILITY |
| `stop` (`:173`) | `(self, timeout_ms: int = DEFAULT_STOP_TIMEOUT_MS) -> None` | — | CAPABILITY |
| `__enter__` (`:191`) / `__exit__` (`:197`) | `(self) -> EventListener` / `(self, *_: object) -> None` | — | CAPABILITY |
| `running` (`:150`), `delivered` (`:156`) | properties | — | READ |

`EventHandler = Callable[[EventRecord], None]` (`:33`). `unregister` raises
`ValueError(f"no handler is registered for event kind {int(kind)}")` (`:71-73`). `start` raises
`RuntimeError("the listener is already running.")` (`:164-165`). `stop` raises `TimeoutError` if the thread
will not stop (`:185-188`) and re-raises a handler's exception **on the caller's thread** (`:189`, `:218-223`).
A handler runs on the listener thread and must not block: it is also what drains the client's event region,
and the payload drops events when the region is full (`:120-123`).

### 3.5 `PacketHooks` (`packets.py:292`)

`__init__(self, bridge: PacketBridge) -> None` (`:299`); `install(self, table_address: int, wanted: Mapping[int, int]) -> tuple[PacketStub, ...]` (`:345`);
`remove(self, free_code: bool = False) -> tuple[int, ...]` (`:467`); properties `table` (`:315`),
`headers` (`:321`), `in_flight` (`:326`); `stub(self, header: int) -> PacketStub` (`:333`). All
**CAPABILITY**. This is the one thing that changes how the client dispatches **its own** incoming packets
(`bridge.py:296-302`), and it restores every entry before anything is freed (`bridge.py:313-323`).
`read_handler_table(access, table_address) -> HandlerTable` (`:177`) and `is_live_code(...)` (`:122`) are
READ.

### 3.6 Emitted-code builders (`payload.py`) — module-level CAPABILITY

`build_dispatcher(table_address, module_base, module_size) -> bytes` (`:1373`, `dispatcher_size:1531`);
`build_observer(watch_address, depth, kind) -> bytes` (`:904`, `observer_size:1088`);
`build_slot_capture(slot_offset, argument) -> bytes` (`:1045`);
`build_packet_stub(...) -> bytes` (`:1131`, `packet_stub_size:1268`);
`build_decoder_stub() -> bytes` (`:1295`, `decoder_stub_size:1368`).
Also in `hooker.py`: `build_entry_patch` (`:305`), `build_trampoline` (`:317`), `build_stub` (`:371`),
`stub_size` (`:472`), `is_generated_stub` (`:141`), `is_relative_jump` (`:359`).

### 3.7 The block's vocabulary — `shared_block.py` (CAPABILITY, no game reach)

`MAGIC/VERSION/…` constants (`:38-186`), `CommandState` (`:267`), `Operation` (`:283`: `NOP=0`, `PING=1`,
`ADD_U32=2`, `ECHO_U32=3`, `CALL=5`, `WRITE_MEMORY=6`), `CallForm` (`:310`: `UI_MESSAGE=1`, `U32_U32=2`,
`NO_ARGS=3`, `U32=4`, `U32_U32_U32=5`, `FLOAT_PTR=6`, `U32_U32_U32_U32_U32=7`, `U32_U32_U32_U32=8`,
`FASTCALL_U32_U32_U32=9`, `STACK_WORDS=10`, `FASTCALL_U32=11`, `FASTCALL_U32_CALLER_RELEASES=12`,
`U32_FLOAT_PTR=13`), `EventKind` (`:439`), `DecodeState` (`:477`), `EventTextState` (`:498`),
`BlockHeader` (`:721`), `CommandRecord` (`:810`), `EventRecord` (`:918`), `Descriptor` (`:1055`),
`float_bits` (`:427`), `command_offset` (`:552`), `event_offset` (`:560`), `data_offset` (`:568`),
`descriptor_offset` (`:583`), `decode_slot_offset` (`:596`), `decode_input_offset` (`:604`),
`decode_output_offset` (`:610`), `decode_slot_image` (`:616`), `write_decode_request` (`:641`),
`decode_state_from_word` (`:650`), `decode_text_from_bytes` (`:659`), `read_decode_state` (`:671`),
`read_decode_result` (`:678`), `clear_decode_slot` (`:692`), `pending` (`:700`), `free_slots` (`:704`),
`empty_block` (`:1094`), `read_header` (`:1101`), `write_command` (`:1109`), `read_command` (`:1118`),
`write_event` (`:1125`), `read_event` (`:1134`).

---

## 4. ACTION members, module by module

Each ACTION row gives: exact signature, return value and meaning, **how it reaches the game** with the
mechanism tag from §1 and file:line, whether it **sends a server packet itself**, and its **preconditions /
failure behaviour**.

A standing precondition for every row below: the member's own module calls `require_client()` /
`require_client().bridge`, so an unconnected client raises
`RuntimeError("No Guild Wars client is connected. Call py4gw.connect() first.")`
(`client.py:1945-1949`), and a connection opened with `game_thread=False` raises
`RuntimeError("this connection was opened without the game thread: pass game_thread=True to connect for the
bridge.")` (`client.py:1020-1024`). Where a member adds a precondition of its own, it is stated; where it
returns early instead of raising, that is stated too.

**On packets, once, for the whole document.** **No member of this library sends a packet to the server
itself.** There is no socket call, no ToS/StoC packet construction and no send hook anywhere in `py4gw/`
(§1, "What is not a mechanism here"). Where a row says *client sends*, it means the **client's own code**
that the library called emits its own packet on the client's own transport — the library never builds or
transmits one. The single place where packet *emulation* is even named is
`PyInventory.OpenXunlaiWindow`, and it **raises** rather than emulating (`native_src/item/py_inventory.py:596-600`,
quoting `GW::StoC::EmulatePacket` as the missing mechanism). The library's `packets.py` layer **receives** —
it replaces entries in the client's StoC handler array (`packets.py:345-466`) — and sends nothing.

### 4.1 `py4gw/player.py` — class `Player` (`:214`)

All 18 ACTIONs below are `@staticmethod`. The 47 READ members are listed in §4.1b.

| # | member (line) | signature | returns | mechanism | packet? | preconditions / failure |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `SetPlayerStatus` (`:1050`) | `(status: PlayerStatus \| int \| str) -> bool` | `True` once the call has run, `False` for a status `PlayerStatus.from_value` rejects | **M1** — `friend_list.set_online_status_func`, `CallForm.U32` (`:1068-1070`) | client sends (its own friend-list status packet) | `False` for an invalid value, no raise (`:1065-1067`) |
| 2 | `ChangeTarget` (`:1074`) | `(agent_id: int) -> None` | `None` | **M1** — `agent.change_target_func`, `CallForm.U32_U32(agent_id, 0)` (`:1091-1093`) | client sends its change-target packet | zero id or an id that resolves to no agent → returns, nothing called (`:1089-1090`) |
| 3 | `CallTarget` (`:1096`) | `(agent_id: int) -> None` | `None` | **M1** — enemy: `agent.call_target_func` `CallForm.U32_U32(0xA, agent_id)` (`:1124-1129`); otherwise `agent.do_world_action_func` `CallForm.U32_U32_U32(1, agent_id, 1)` (`:1131-1137`) | client sends | zero id, no agent, or an agent with no living record → returns (`:1114-1122`) |
| 4 | `Interact` (`:1140`) | `(agent_id: int, call_target: bool = False) -> None` | `None` | **M1** — `agent.do_world_action_func` `CallForm.U32_U32_U32(action_id, agent_id, 1 if call_target else 0)` (`:1179-1185`); when `call_target` it first calls `Player.CallTarget` (`:1176-1177`) | client sends | zero id or unresolved agent → returns (`:1154-1158`); an unresolved living record → returns (`:1166-1168`) |
| 5 | `Move` (`:1188`) | `(x: float, y: float, zPlane: int = 0) -> None` | `None` | **M1** — `agent.move_to_func`, `CallForm.FLOAT_PTR` with `float_bits(x)`, `float_bits(y)`, `float_bits(float(zPlane))`; the four-float array (`{x, y, z, 0.0f}`) is **built in the payload's own frame** (`shared_block.py:352-357`) | client sends its move packet | none beyond a connection |
| 6 | `DepositFaction` (`:1209`) | `(faction_id: int) -> None` | `None` | **M1** — `player.deposit_faction_func`, `CallForm.U32_U32_U32(0, faction_id, 5000)` (`:1220-1226`); the leading `0` and `5000` are the source's own | client sends | none |
| 7 | `RemoveActiveTitle` (`:1229`) | `() -> None` | `None` | **M1** — `player.remove_active_title_func`, `CallForm.NO_ARGS` (no arguments pushed at all, `:1237-1239`) | client sends | none |
| 8 | `SetActiveTitle` (`:1242`) | `(title_id: int) -> None` | `None` | **M1** — `player.set_active_title_func`, `CallForm.U32` (`:1249-1251`) | client sends | none |
| 9 | `SendRawDialog` (`:1254`) | `(dialog_id: int) -> None` | `None` | **M1** — `agent.send_agent_dialog_func`, `CallForm.U32` (`:1267-1269`) | client sends | none |
| 10 | `BuySkill` (`:1272`) | `(skill_id: int) -> None` | `None` | `Utils.SkillIdToDialogId` (host-side OR with `0x0A000000`) then `Player.SendRawDialog` → **M1** (`:1285-1286`) | client sends | none |
| 11 | `UnlockBalthazarSkill` (`:1289`) | `(skill_id: int, use_pvp_remap: bool = True) -> None` | `None` | `Utils.BalthazarSkillIdToDialogId(...)` then `Player.SendRawDialog` → **M1** (`:1305-1306`) | client sends | the conversion reads the skill constant table, so it needs a connection (`:1300-1302`) |
| 12 | `SendDialog` (`:1309`) | `(dialog_id: str \| int) -> None` | `None` | **M1** — gadget agent: `agent.send_gadget_dialog_func` `CallForm.U32` (`:1358-1360`); otherwise `agent.send_agent_dialog_func` `CallForm.U32` (`:1362`). Records the send first via `dialog._note_sent_dialog` (`:1351-1356`) | client sends | a hex **string** is parsed as base 16 (`:1332-1336`); no active dialog → returns (`:1339-1341`); the dialog's agent not resolvable → returns (`:1342-1344`) |
| 13 | `SendAutomaticDialog` (`:1365`) | `(button_number: int) -> None` | `None` | → `Player.SendDialog` → **M1** (`:1396-1397`) | client sends | negative index → returns (`:1384-1385`); no buttons, or an index past the end → returns (`:1391-1394`) |
| 14 | `SendChatCommand` (`:1463`) | `(command: str) -> None` | `None` | → `native_src.chat.chat.SendChat("/", command)` → **M1**, `chat.send_chat_func` (`:1475`, `chat.py:105-153`) | client sends | the command channel is `'/'`; an opcode the sender does not know sends nothing (`chat.py:146-149`) |
| 15 | `SendChat` (`:1478`) | `(channel: ChatChannel \| int \| str, message: str) -> None` | `None` | → `chat.SendChat(channel, message)` → **M1** (`:1491`) | client sends | as above; note `ChatChannel.CHANNEL_ALL` is `3`, which is **not** an opcode and therefore sends nothing (`:1486-1488`) |
| 16 | `SendWhisper` (`:1494`) | `(target_name: str, message: str) -> None` | `None` | → `chat.SendChat(target_name, message)`, the string overload → **M1** (`:1505`) | client sends | a name is ≥3 characters; a one-character string would be read as an opcode (`chat.py:111-115`) |
| 17 | `SendFakeChat` (`:1508`) | `(channel: ChatChannel \| int, message: str) -> None` | `None` | → `chat.SendFakeChat` → **M2** `kWriteToChatLog` (`:1519`) | **no** — the line exists only in this client's own log (`chat.py:173-182`) | none |
| 18 | `SendFakeChatColored` (`:1522`) | `(channel: ChatChannel \| int, message: str, r: int, g: int, b: int) -> None` | `None` | `FormatChatMessage` (pure) then `chat.SendFakeChatColored` → **M2** (`:1533`) | **no** | none |

`Player.FormatChatMessage(message: str, r: int, g: int, b: int) -> str` (`:1536`) is READ/pure (clamps to
1..255 and wraps in `<c=#RRGGBB>`).

**`Player.RequestChatHistory() -> None` (`:1400`) is CAPABILITY, not ACTION.** It fills a host-side buffer
(`_chat_history`) by driving the client's decoder: `chat.GetChatLog()` (a read) then
`_decode_chat_message` → `begin_string_decode` + `async_decode_str` (**M1** with
`ui.validate_async_decode_str_func`, `ui/async_decode.py:123-129`), waiting on the decode slot with the
source's 500 ms / 5 ms bounds (`player.py:1435-1449`). It changes nothing in the game.

#### 4.1b `Player` — the 47 READ members

`ResolvePlayerStatus:230`, `GetPlayerStatusNameFromValue:236`, `player_instance:302` (**RAISES**),
`GetPlayerNumber:325`, `GetLoginNumber:338`, `GetPartyNumber:355`, `IsPlayerLoaded:366`, `GetAgentID:456`,
`GetName:491`, `GetXY:511`, `GetAgent:529`, `GetObservingID:537`, `GetTargetID:552` (reads the last target
the client announced, captured by the connection's `_capture_target`, `client.py:616-631`),
`GetAccountName:573`, `GetAccountEmail:586`, `GetPlayerUUID:613`, `GetInstanceUptime:636`, `GetRankData:650`,
`GetTournamentRewardPoints:676`, `GetMorale:687`, `GetExperience:696`, `GetLevel:707`, `GetSkillPointData:716`,
`GetAccountFlags:738`, `IsDhuumsCovenant:752`, `IsMelandrusAccord:758`, `IsReforged:764`,
`GetMissionsCompleted:772`, `GetMissionsBonusCompleted:786`, `GetMissionsCompletedHM:795`,
`GetMissionsBonusCompletedHM:801`, `GetControlledMinions:820`, `GetLearnableCharacterSkills:832`,
`GetUnlockedCharacterSkills:845`, `GetKurzickData:861`, `GetLuxonData:869`, `GetImperialData:875`,
`GetBalthazarData:883`, `GetActiveTitleID:917`, `GetUnlockedMaps:947`, `IsAgentIDValid:962`,
`GetMouseOverID:972`, `GetTitleArrayRaw:984`, `GetTitleArray:993`, `GetTitle:999`, `GetPlayerStatus:1010`,
`GetPlayerStatusName:1028`, `IsTyping:1035`, `IsChatHistoryReady:1451`, `GetChatHistory:1457`.

### 4.2 `py4gw/party.py`

25 ACTION members. Two mechanisms dominate: **M1** into a catalog function, and **M3/M2** through
`_press_party_button` (`:187-233`), which builds Native's own `uint32_t ctx[13]` and `uint32_t wparam[4]` in
the block's data region and calls the party callback with the caller's `edx` (`:224-232`). The call form is
chosen by measurement, not taste: the **search** callback ends `ret 4` and releases its own word
(`CallForm.FASTCALL_U32`), the **window** callback ends with a bare `ret` and leaves its word to the caller
(`CallForm.FASTCALL_U32_CALLER_RELEASES`) (`:202-206`, `:228`; `shared_block.py:400-417`).

| # | member (line) | signature | returns | mechanism | packet? | preconditions / failure |
| --- | --- | --- | --- | --- | --- | --- |
| 19 | `Hero.FlagHero` (`:696`) | `(self, idx: int) -> bool` | `True` after the press, `False` for an index outside `1..7` | **M3** — `UIManager.Keypress(key, 0)` with the `ControlAction_CommandHero{N}` key the switch selects (`:710-714`) | client sends | `idx` outside the switch → `False`, nothing pressed (`:711-712`) |
| 20 | `Party.SetHardMode` (`:1193`) | `() -> None` | `None` | guard then `_call_difficulty(True)` → **M1** `party.set_difficulty_func`, `CallForm.U32(1)` (`:1202-1203`, `:236-256`) | client sends | only when `IsHardModeUnlocked() and IsNormalMode()` (`:1202`); inside `_call_difficulty` the call happens **only when the mode differs** (`:253-256`) |
| 21 | `Party.SetNormalMode` (`:1206`) | `() -> None` | `None` | guard then `_call_difficulty(False)` → **M1** `party.set_difficulty_func` `CallForm.U32(0)` (`:1209-1210`) | client sends | only when `IsHardMode()`; plus the differs-check (`:253-256`) |
| 22 | `Party.SearchParty` (`:1213`) | `(search_type: int, advertisement: str) -> bool` | `True` once called, `False` when the function is not resolved | **M1** — `party.party_search_seek_func`, `CallForm.U32_U32_U32(search_type, address, 0)`; the advertisement is placed as wide text at `PARTY_ADVERTISEMENT_OFFSET` (`:1224`, `_search_party:497-519`) | client sends | unresolved function → `False` (`:511-512`) |
| 23 | `Party.SearchPartyCancel` (`:1227`) | `() -> None` | `None` | **M3/M1** — `_press_party_button({}, {2: 0x8}, 0)` (`:1234`) | client sends | `client.resolves(PARTY_SEARCH_BUTTON_CALLBACK)` else nothing (`:214-215`) |
| 24 | `Party.SearchPartyReply` (`:1237`) | `(accept: bool = True) -> bool` | the helper's own `bool` (`False` when the callback is unresolved) | **M3/M1** — `_press_party_button({0xB: 0, 8: accept}, {1: 0x3, 2: 0x6}, 0)` (`:1247-1249`) | client sends | as above |
| 25 | `Party.ReturnToOutpost` (`:1262`) | `() -> bool` | `ui::ButtonClick`'s own bool: `False` when the frame or its child does not resolve | **M3** — `FrameTree.by_label("DlgRedirect")` → `Frame.child_native(0)` (**M1** `ui.get_child_frame_id_func`) → `Frame.click()` (`:1285-1290`) | client sends | no frame → `False` (`:1288-1289`); `Frame.click` also refuses a frame or parent not `IsCreated`, or a parent with no callbacks (`frame.py:1763-1791`) |
| 26 | `Party.LeaveParty` (`:1293`) | `() -> None` | `None` | **M3/M1** — `_press_party_button({0xD: 1}, {}, 0, window=True)` (`:1302-1304`) | client sends | a party size of zero returns **without calling** (`:1302-1303`) |
| 27 | `Players.InvitePlayer` (`:1374`) | `(agent_id_or_name: object) -> None` | `None` | `int` → `_send_chat_command("invite " + name)` → `chat.SendChat("/", …)` → **M1** `chat.send_chat_func` (`:1396-1400`); `str` → `Player.SendChatCommand` (`:1401-1402`) | client sends | record missing or no name → returns (`:1398-1399`); a command ≥32 chars → nothing sent (`:581-583`); any other type → `TypeError("Invalid argument type. Must be int (ID) or str (name).")` (`:1403-1406`) |
| 28 | `Players.KickPlayer` (`:1409`) | `(login_number: int) -> None` | `None` | `_send_chat_command("kick " + name)` → **M1** (`:1417-1420`) | client sends | record missing or no name → returns (`:1418-1419`) |
| 29 | `Heroes.AddHero` (`:1529`) | `(hero_id: int) -> None` | `None` | **M3/M1** — `_press_party_button({0xB: 1, 9: hero_id}, {1: 0x1, 2: 0x7}, 2)` (`:1537`) | client sends | the callback resolves |
| 30 | `Heroes.AddHeroByName` (`:1540`) | `(hero_name: str) -> None` | `None` | name → id through `Hero(hero_name).GetID()` then `AddHero` (`:1547`) | client sends | an unknown name resolves to `HeroType.None_` (`party.py:674-679`) |
| 31 | `Heroes.KickHero` (`:1550`) | `(hero_id: int) -> None` | `None` | **M3/M1** — `_press_party_button({0xB: 1, 9: hero_id}, {1: 0x6, 2: 0x7}, 0)` (`:1558-1560`) | client sends | as above |
| 32 | `Heroes.KickHeroByName` (`:1563`) | `(hero_name: str) -> None` | `None` | `KickHero(Hero(name).GetID())` (`:1566`) | client sends | as above |
| 33 | `Heroes.KickAllHeroes` (`:1569`) | `() -> None` | `None` | `KickHero(0x26)` (`:1576`) | client sends | as above |
| 34 | `Heroes.UseSkill` (`:1579`) | `(hero_agent_id: int, slot: int, target_id: int) -> None` | `None` | `_use_hero_skill` (`:586-613`): optional `Player.ChangeTarget` (**M1**) → `UIManager.Keypress(hero_base + slot - 1, 0)` (**M3**) → restore the previous target (**M1**) (`:1596`) | client sends | a hero number outside `1..7` returns immediately (`:605-607`); the argument is a **hero number**, not an agent id (`:1591-1593`) |
| 35 | `Heroes.SetSkillAIEnabled` (`:1599`) | `(hero_agent_id: int, slot: int, enabled: bool) -> bool` | `True` when the state already matched or the call was made, `False` on any guard | **M1** — `party.command_hotkey_disable_ai_func` `CallForm.U32_U32(agent, slot0)` (`:1609`, `_set_hero_skill_ai_enabled:375-426`) | client sends | four guards in order: function, non-zero agent, slot `1..8`, a world with a skillbar array; hero's skillbar must be found; **the call happens only when the bit differs** (`:394-425`) |
| 36 | `Heroes.FlagHero` (`:1612`) | `(hero_id: int, x: float, y: float) -> None` | `None` | `_flag_hero_agent` → **M1** `party.flag_hero_agent_func`, `CallForm.U32_FLOAT_PTR(agent, float_bits(x), float_bits(y), float_bits(0.0))` (`:1623`, `:259-286`) | client sends | function must resolve; agent id must be non-zero and **not** the controlled character (`:272-277`) |
| 37 | `Heroes.FlagAllHeroes` (`:1626`) | `(x: float, y: float) -> None` | `None` | **M1** — `party.flag_all_func`, `CallForm.FLOAT_PTR(float_bits(x), float_bits(y), float_bits(0.0))` (`:1630`, `:319-338`) | client sends | function must resolve (`:329-330`) |
| 38 | `Heroes.UnflagHero` (`:1633`) | `(hero_id: int) -> None` | `None` | `_flag_hero(id, HUGE_VALF, HUGE_VALF)` → agent id resolved through `Party.Heroes.GetHeroAgentIDByPartyPosition` then **M1** `flag_hero_agent_func` (`:1643`, `:305-316`) | client sends | same three guards; the argument is resolved as a **party position** here (`:1636-1640`) |
| 39 | `Heroes.UnflagAllHeroes` (`:1646`) | `() -> None` | `None` | `_flag_all(HUGE_VALF, HUGE_VALF)` → **M1** (`:1652`) | client sends | function must resolve |
| 40 | `Heroes.SetHeroBehavior` (`:1707`) | `(hero_agent_id: int, behavior: int) -> None` | `None` | `_set_hero_behavior` → **M1** `party.set_hero_behavior_func` `CallForm.U32_U32` (`:1717`, `:341-372`) | client sends | world, function and a non-empty `hero_flags` array; the record must contain the agent; **the call happens only when `hero_behavior` differs** (`:353-371`) |
| 41 | `Henchmen.AddHenchman` (`:1723`) | `(henchman_id: int) -> None` | `None` | **M3/M1** — `_press_party_button({0xB: 2, 10: henchman_id}, {1: 0x2, 2: 0x7}, 0)` (`:1731`) | client sends | the callback resolves |
| 42 | `Henchmen.KickHenchman` (`:1734`) | `(henchman_id: int) -> None` | `None` | **M3/M1** — `_press_party_button({0xB: 2, 10: henchman_id}, {1: 0x6, 2: 0x7}, 0)` (`:1741-1743`) | client sends | as above |
| 43 | `Pets.SetPetBehavior` (`:1770`) | `(behavior: int, lock_target_id: int) -> None` | `None` | `_set_pet_behavior` → **M1** `party.lock_pet_target_func` when the locked target differs, then `party.set_hero_behavior_func` when the behaviour differs (`:1781`, `:429-494`) | client sends | world, **both** functions resolved, a non-empty `pets` array, a pet record for the controlled character; for `Fight` only, the target must resolve to a **living enemy** else return (`:453-478`) |

#### 4.2b `Party` — DECLARED, NO GAME REACH (documented in the source's own terms)

| member (line) | signature | what it actually does |
| --- | --- | --- |
| `Party.SetTickasToggle` (`:1109`) | `(enable: bool) -> None` | writes the module global `tick_work_as_toggle` (`:165`, `:168-172`). Nothing in this port reads it — its reader in the source is the injected runtime's own tick-button hook (`:160-164`). **No client interaction.** |
| `Party.SetTicked` (`:1159`) | `(ticked: bool) -> None` | empty body. Reforged's own body writes a **newly constructed** `PyParty` object's bool, which is discarded with the call, so the client is never told anything (`:1160-1171`). The function that *does* ready the party is `party.set_ready_status_func`, which nothing in `Party.py` reaches (`:1168-1170`). |
| `Party.ToggleTicked` (`:1174`) | `() -> None` | runs the source's two reads and then `SetTicked`, which does nothing (`:1176-1190`). |
| `Party.RespondToPartyRequest` (`:1252`) | `(party_id: int, accept: bool) -> None` | empty body — native's body is `(void)party_id; (void)accept; return true;` (`:1255-1259`). |

#### 4.2c `Party` / `Party.Players` / `Heroes` / `Henchmen` / `Pets` — READ members

`Party`: `GetPartyID:815`, `GetPartyLeaderID:822`, `GetOwnPartyNumber:837`, `GetPartyTarget:851`,
`GetPlayers:870`, `GetHeroes:883`, `GetHenchmen:892`, `GetOthers:901`, `IsHardModeUnlocked:919`,
`IsHardMode:926`, `IsNormalMode:937`, `GetPartySize:943`, `GetPlayerCount:958`, `GetHeroIndex:964`,
`GetHeroCount:984`, `GetHenchmanCount:994`, `IsPartyDefeated:1000`, `IsPartyLoaded:1007`,
`GetPartyMorale:1025`, `IsPlayerLoaded:1050`, `IsPartyLeader:1088`, `IsAllTicked:1120`,
`IsPlayerTicked:1133`, `party_instance:796` (**RAISES**).
`Players`: `GetAgentIDByLoginNumber:1310`, `GetPlayerNameByLoginNumber:1330`,
`GetPartyNumberFromLoginNumber:1353`, `GetLoginNumberByAgentID:1362`.
`Heroes`: `GetHeroAgentIDByPartyPosition:1426`, `GetHeroIDByAgentID:1444`, `GetHeroIDByPartyPosition:1457`,
`GetHeroIdByName:1466`, `GetHeroNameById:1477`, `GetNameByAgentID:1488`, `GetHeroPartyPositionByAgentID:1502`,
`GetTargetIDByAgentID:1511`, `IsHeroFlagged:1655`, `IsAllFlagged:1670`, `GetAllFlag:1693`.
`Pets`: `GetPetBehavior:1784`, `GetPetInfo:1790`, `GetPetID:1801`.
`Hero`: `GetID:681`, `GetName:686`, `GetProfession:691`, `__eq__:716`, `__ne__:723`, `__hash__:730`,
`__repr__:735`.

### 4.3 `py4gw/map.py`

17 ACTION members.

| # | member (line) | signature | returns | mechanism | packet? | preconditions / failure |
| --- | --- | --- | --- | --- | --- | --- |
| 44 | `Map.SkipCinematic` (`:802`) | `() -> None` | `None` | guard, then `MapMethods.SkipCinematic()` → **M1** `map.skip_cinematic_func`, `CallForm.NO_ARGS` (`:805-813`, `native_src/methods/map_methods.py:107-118`) | client sends | the member refuses unless `Map.IsInCinematic()`, and re-checks inside the closure (`:805-810`); `MapMethods` returns `False` if the function is not resolved (`map_methods.py:114-115`) |
| 45 | `Map.Travel` (`:816`) | `(map_id: int) -> None` | `None` | `MapMethods.Travel(map_id, region, 0, language)` → four words placed at `_TRAVEL_OFFSET` then **M2 raw** `kTravel` with that address as `wparam` (`:819-822`, `map_methods.py:120-141`) | client sends | none; returns `False` (discarded) if the message is not sent |
| 46 | `Map.TravelToDistrict` (`:825`) | `(map_id: int, district: int = 0, district_number: int = 0) -> None` | `None` | region and language derived from the district, then `MapMethods.Travel(...)` → **M2 raw** (`:878-881`) | client sends | an unrecognised district falls back to the current region and language (`:852`, `:876`) |
| 47 | `Map.TravelToRegion` (`:884`) | `(map_id: int, server_region: int, district_number: int, language: int = 0) -> None` | `None` | `MapMethods.Travel(...)` → **M2 raw** (`:889-892`) | client sends | none |
| 48 | `Map.TravelGH` (`:895`) | `() -> None` | `None` | `MapMethods.TravelGH()` → **M2 raw** `kGuildHall`, `wparam` = the address of the **client's own** `GuildContext.player_gh_key` (`map_methods.py:154-185`) | client sends | guild context and its `player_gh_key` must read; else `False`, nothing sent (`map_methods.py:154-160`). (`Map.TravelGH` passes no key, so the `WRITE_MEMORY` branch at `map_methods.py:168-182` is **not** taken from here.) |
| 49 | `Map.LeaveGH` (`:904`) | `() -> None` | `None` | `MapMethods.LeaveGH()` → **M2 packed** `kLeaveGuildHall`, `[0]` (`:907-910`, `map_methods.py:187-191`) | client sends | none |
| 50 | `Map.EnterChallenge` (`:913`) | `() -> None` | `None` | `MapMethods.EnterChallenge()` → **M2 packed** `kSendEnterMission`, `[0]` (`:916-919`, `map_methods.py:193-197`) | client sends | none |
| 51 | `Map.CancelEnterChallenge` (`:922`) | `() -> None` | `None` | **M3** — `Frame(FrameId.…CancelEnterMissionButton).click()` (`:926-929`) | client sends | frame must exist, else `False` and no click (`:927-928`) |
| 52 | `Map.ConfirmEnterChallenge` (`:935`) | `() -> None` | `None` | **M3** — the same, on the confirm button (`:939-942`) | client sends | frame must exist (`:940-941`) |
| 53 | `Map.MissionMap.OpenWindow` (`:994`) | `() -> None` | `None` | **M3** — `UIManager.Keydown(ControlAction_OpenMissionMap, 0)` then `Keyup` (`:1009-1014`) | client sends | returns if the window is already open (`:1011-1012`); **no 75 ms hold** between down and up — there is no scheduler (`:1003-1006`) |
| 54 | `Map.MissionMap.CloseWindow` (`:1017`) | `() -> None` | `None` | **M3** — the **same** keybind, on the source's own guard (`:1025-1030`) | client sends | returns when the frame does not resolve (`:1027-1028`) |
| 55 | `Map.MiniMap.OpenWindow` (`:1494`) | `() -> None` | `None` | **M1** — `UIManager.SetWindowVisible(WindowID_Compass, True)` → `ui.set_window_visible_func` (`:1497-1501`) | client sends | returns if already open (`:1499-1500`) |
| 56 | `Map.MiniMap.CloseWindow` (`:1504`) | `() -> None` | `None` | **M1** — same with `False` (`:1507-1511`) | client sends | returns if not open (`:1509-1510`) |
| 57 | `Map.WorldMap.OpenWindow` (`:2003`) | `() -> None` | `None` | **M3** — `Keydown`/`Keyup` of `ControlAction_OpenWorldMap` (`:2015-2020`) | client sends | returns if already open (`:2017-2018`) |
| 58 | `Map.WorldMap.CloseWindow` (`:2023`) | `() -> None` | `None` | **M3** — the same keybind on the source's guard (`:2030-2035`) | client sends | returns when the frame does not resolve (`:2032-2033`) |
| 59 | `Map.Pregame.LogoutToCharacterSelect` (`:2282`) | `()` (no annotation) | `None` | `MapMethods.LogouttoCharacterSelect()` → **M2 packed** `kLogout`, `[0, 0]` (`:2285`, `map_methods.py:199-207`) | client sends | none |
| 60 | `Map.Pregame.InCharacterSelectScreen` (`:2249`) | `() -> bool` | `True` when the word the client wrote back is `2` | **M2 raw** `kCheckUIState` with `lparam` = an address in the block, `wparam = 0`; the client fills that word and the host reads it back (`:2272-2279`). **Classified ACTION because it sends a client message**; its purpose is a query and its answer is a read of the word the client wrote. | asks the client, which may query itself; the library sends nothing | the pre-game char buffer and size must be non-zero, else `False` (`:2268-2270`) |

`Map.Pathing.ClearPathingCache` (`:2320`), `Map.Pathing.ForceReloadNavMesh` (`:2341`) and
`Map.Pathing.GetPathingMaps` (`:2293`) touch **host-side caches only** — no game reach (`:2331-2347`).
`Map.MissionMap.GetLastClickCoords` (`:1052`) is READ.

#### 4.3b `Map` and its nested classes — READ members

`Map`: `IsMapDataLoaded:96`, `GetInstanceType:107`, `GetInstanceTypeName:119`, `IsOutpost:126`,
`IsExplorable:134`, `IsMapLoading:142`, `IsObservingMatch:154`, `IsMapReady:164`, `GetMapID:176`,
`GetOutpostIDs:187`, `GetOutpostNames:194`, `GetMapName:201`, `GetMapIDByName:219`, `GetBaseMapID:239`,
`GetAllMapVariants:255`, `IsMapIDMatch:267`, `GetInstanceUptime:281`, `GetRegion:289`, `GetRegionType:298`,
`GetDistrict:309`, `GetLanguage:316`, `GetAmountOfPlayersInInstance:335`, `GetMaxPartySize:346`,
`GetMinPartySize:355`, `GetMinPlayerSize:364`, `GetMaxPlayerSize:373`, `GetFoesKilled:384`,
`GetFoesToKill:392`, `IsVanquishCompleted:400`, `IsInCinematic:408`, `GetCampaign:422`, `GetContinent:439`,
`HasEnterChallengeButton:453`, `IsOnWorldMap:462`, `IsPVP:471`, `IsGuildHall:480`, `IsVanquishable:489`,
`IsVanquishComplete:498`, `IsMapUnlocked:506`, `GetFlags:540`, `GetMinLevel:549`, `GetMaxLevel:558`,
`GetThumbnailID:567`, `GetControlledOutpostID:576`, `GetFractionMission:585`, `GetNeededPQ:594`,
`HasMissionMapsTo:603`, `GetMissionMapsTo:612`, `GetIconPosition:621`, `GetIconStartPosition:630`,
`GetIconStartDupePosition:639`, `GetIconEndPosition:648`, `GetIconEndDupePosition:657`, `GetFileID:666`,
`GetMissionChronology:675`, `GetHAChronology:684`, `GetNameID:693`, `GetDescriptionID:702`, `GetFileID1:711`,
`GetFileID2:720`, `IsUnlockable:729`, `GetUnloadedMapInfo:740`, `IsEnteringChallenge:752`,
`GetMapWorldMapBounds:763`, `GetMapBoundaries:785`.
`MissionMap`: `GetFrame:960`, `GetFrameID:978`, `IsWindowOpen:986`, `GetLastClickCoords:1052`,
`GetLastRightClickCoords:1091`, `GetMissionMapWindowCoords:1130`, `GetMissionMapContentsCoords:1138`,
`GetScale:1146`, `GetZoom:1154`, `GetAdjustedZoom:1167`, `GetCenter:1186`, `GetPanOffset:1199`,
`GetMapScreenCenter:1218`.
`MissionMap.MapProjection`: `GamePosToWorldMap:1232`, `WorldMapToGamePos:1259`, `WorldMapToScreen:1286`,
`ScreenToWorldMap:1308`, `GameMapToScreen:1332`, `ScreenToGameMap:1341`, `NormalizedScreenToScreen:1350`,
`ScreenToNormalizedScreen:1369`, `NormalizedScreenToWorldMap:1391`, `NormalizedScreenToGamePos:1400`,
`GamePosToNormalizedScreen:1407`, `GamePosToScreen:1414`, `ScreenToGamePos:1423`,
`WorldPosToMissionMapScreen:1432`, `ScreenToWorldPos:1446`.
`MiniMap`: `GetFrame:1471`, `GetFrameID:1477`, `IsWindowOpen:1486`, `GetWindowCoords:1581`, `IsLocked:1589`,
`GetPanOffset:1595`, `GetScale:1601`, `GetRotation:1621`, `GetZoom:1632`, `GetMapScreenCenter:1638`.
`MiniMap.MapProjection`: `GamePosToWorldMap:1663`, `WorldMapToGamePos:1689`, `WorldMapToScreen:1712`,
`ScreenToWorldMap:1732`, `GameMapToScreen:1752`, `ScreenToGameMap:1759`, `NormalizedScreenToScreen:1766`,
`ScreenToNormalizedScreen:1786`, `NormalizedScreenToWorldMap:1808`, `NormalizedScreenToGamePos:1815`,
`GamePosToNormalizedScreen:1822`, `GamePosToScreen:1829`, `ScreenToGamePos:1859`,
`WorldPosToMiniMapScreen:1889`, `ScreenToWorldPos:1901`, `ComputedPathingGeometryToScreen:1915`.
`WorldMap`: `GetFrameID:1979`, `GetFrame:1987`, `IsWindowOpen:1995`, `GetWindowCoords:2105`, `GetZoom:2117`,
`GetParams:2125`, `GetExtraData:2133`.
`Pregame`: `GetFrameID:2195`, `GetFrame:2203`, `IsWindowOpen:2211`, `GetChosenCharacterIndex:2219`,
`GetContextStruct:2227`, `GetCharList:2233`, `GetAvailableCharacterList:2241`.
`Pathing`: `GetPathingMaps:2293`, `GetPathingMapsRaw:2309`, `ClearPathingCache:2320`,
`ForceReloadNavMesh:2341`, `GetAvailableMapIds:2350`, `GetSpawns:2358`, `GetTravelPortals:2373`,
`GetComputedGeometry:2471`, `GetScreenComputedGeometry:2482`, `GetShiftedComputedGeometry:2493`,
`GetshiftedScreenComputedGeometry:2507`, `GetMapQuads:2537`, `IsPointInPathing:2551`,
`IsScreenPointInPathing:2565`; `Pathing.Quad`: `GetPoints:2433`, `GetScreenPoints:2438`,
`GetShiftedPoints:2443`, `GetShiftedScreenPoints:2453`.

### 4.4 `py4gw/camera.py` — class `Camera` (`:107`)

13 ACTIONs, in two mechanisms. The **field writers** compute a value from a fresh read and place it with
**M4** (`_write_field`, `:125-145`); the two **patches** toggle bytes with **M5** (`_toggle_patch`,
`:162-246`). `_camera_address()` requires a live camera pointer and raises
`RuntimeError("The camera context is currently unavailable.")` when it is zero (`:120-123`).

| # | member (line) | signature | returns | mechanism | packet? | preconditions / failure |
| --- | --- | --- | --- | --- | --- | --- |
| 61 | `SetYaw` (`:447`) | `(yaw: float) -> None` | `None` | **M4** twice — writes `yaw_to_go` **and** `yaw` (`:455-456`); Native's own body writes both because the client steers toward `yaw_to_go` (`:450-452`) | no | camera pointer must resolve |
| 62 | `SetPitch` (`:459`) | `(pitch: float) -> None` | `None` | **M4** — `pitch_to_go` only (`:466`) | no | as above |
| 63 | `SetMaxDistance` (`:469`) | `(dist: float) -> None` | `None` | **M4** — `max_distance2` (`:472`) | no | as above |
| 64 | `SetFieldOfView` (`:475`) | `(fov: float) -> None` | `None` | **M4** — `field_of_view` (`:478`) | no | as above |
| 65 | `SetCameraUnlock` (`:481`) | `(unlock: bool) -> None` | `None` | **M5** — `_toggle_patch("update", unlock)`: resolve `camera.camera_update_patch_addr` once, read the client's own bytes as the backup, `Patcher.patch(address, backup, patch)` where the patch is `EB 0C` (vs2017) or `EB 0F` (vs2022, the fallthrough) (`:484`, `:203-235`) | no | asked for the state it is already in → nothing happens, `True` (`:197-198`); an unresolved address → `RuntimeError(f"{name} did not resolve: ...")` (`:208-211`) |
| 66 | `ForwardMovement` (`:493`) | `(amount: float, true_forward: bool) -> None` | `None` | **M4** — computes the new `look_at_target` from the current record and writes the `Vec3f` (`:496-511`) | no | `amount == 0.0` → returns without writing (`:498-499`) |
| 67 | `VerticalMovement` (`:514`) | `(amount: float) -> None` | `None` | **M4** — `look_at_target.z + amount` (`:517-523`) | no | camera pointer |
| 68 | `SideMovement` (`:526`) | `(amount: float) -> None` | `None` | **M4** — `look_at_target` offset by `-sin(yaw)`/`cos(yaw)` (`:529-541`) | no | `amount == 0.0` → returns (`:531-532`) |
| 69 | `RotateMovement` (`:544`) | `(angle: float) -> None` | `None` | **M4** ×3 — new `look_at_target`, then `SetYaw(yaw + angle)` (two field writes), then the target (`:551-562`) | no | `angle == 0.0` → returns (`:548-549`) |
| 70 | `UpdateCameraPos` (`:582`) | `() -> None` | `None` | `ComputeCameraPos()` then **M4** `position` (`:585-586`) | no | camera pointer |
| 71 | `SetCameraPosition` (`:589`) | `(x: float, y: float, z: float) -> None` | `None` | **M4** — `position` (`:592`) | no | camera pointer |
| 72 | `SetLookAtTarget` (`:595`) | `(x: float, y: float, z: float) -> None` | `None` | **M4** — `look_at_target` (`:598`) | no | camera pointer |
| 73 | `SetFog` (`:601`) | `(fog: bool) -> None` | `None` | **M5** — `_toggle_patch("fog", fog)`: `camera.fog_patch_addr`, one byte `00` (`:604`, `:56-57`, `:224`) | no | as `SetCameraUnlock` |

The 33 READ members are listed in §4.4b. Note `GetCameraUnlock` (`:487`) is a **READ of host-side patch
state**, not a client read.

#### 4.4b `Camera` — READ members

`camera_instance:251`, `GetLookAtAgentID:257`, `GetMaxDistance:263`, `GetYaw:269`, `GetCurrentYaw:275`,
`GetPitch:291`, `GetCameraZoom:297`, `GetYawRightClick:303`, `GetYawRightClick2:309`,
`GetPitchRightClick:315`, `GetDistance2:321`, `GetAccelerationConstant:327`,
`GetTimeSinceLastKeyboardRotation:333`, `GetTimeSinceLastMouseRotation:339`, `GetTimeSinceLastMouseMove:345`,
`GetTimeSinceLastAgentSelection:351`, `GetTimeInTheMap:357`, `GetTimeInTheDistrict:363`, `GetYawToGo:369`,
`GetPitchToGo:375`, `GetDistanceToGo:381`, `GetMaxDistance2:387`, `GetPosition:393`,
`GetCameraPositionToGo:400`, `GetCameraPositionInverted:407`, `GetCameraPositionInvertedToGo:414`,
`GetLookAtTarget:421`, `GetAtTargetToGo:428`, `GetFieldOfView:435`, `GetFielsOfView2:441`,
`GetCameraUnlock:487`, `ComputeCameraPos:565`, `IsPointInFOV:607`.

### 4.5 `py4gw/effect.py` — `Effects` (`:376`) and `PyEffects` (`:313`)

| # | member (line) | signature | returns | mechanism | packet? | preconditions / failure |
| --- | --- | --- | --- | --- | --- | --- |
| 74 | `PyEffects.DropBuff` (`:354`) | `(self, skill_id: int) -> None` | `None` | `drop_buff` → **M1** `effects.drop_buff_func`, `CallForm.U32` (`:361`, `:220-233`) | client sends | `False`/no call when the catalog has no such function (`:230-231`); the argument is named `skill_id` and forwarded as the **buff id** (`:356-358`) |
| 75 | `Effects.DropBuff` (`:391`) | `(buff_id: int) -> None` | `None` | `PyEffects(Player.GetAgentID()).DropBuff(buff_id)` → **M1** (`:396`) | client sends | the player must be loaded, else `GetAgentID` gates and the buff id is asked of the wrong agent |
| 76 | `PyEffects.ApplyDrunkEffect` (`:370`) | `(intensity: int = 0, tint: int = 0) -> None` | `None` | `get_drunk_af` → **M1** `effects.post_process_effect_func`, `CallForm.U32_U32(intensity, tint)` (`:373`, `:236-251`) | no | no call when the function is not resolved (`:247-248`). **Note:** this is the *same address* `connect()` hooks as an observer (`client.py:124`), so the call travels through the library's own hook and the trampoline reaches the client's body. |
| 77 | `Effects.ApplyDrunkEffect` (`:512`) | `(intensity: int, tint: int) -> None` | `None` | `PyEffects.ApplyDrunkEffect(...)` → **M1** (`:515`) | no | as above |

`GetAlcoholLevel` (`:479` → `:364` → `get_alcohol_level:254`) **RAISES** (see §5):
`NotImplementedError("PyEffects.get_alcohol_level is declared, and its capture is wired, but it is not
built here yet: the observer's emitted code reads the hooked function's second argument as a packet pointer
and drops the event when it is null (payload.py:762-765), while native's post-process handler stores the two
plain word arguments (effects.cpp:24-41). What is missing is that second event shape -- an observer that
carries the call's own arguments instead of dereferencing one. The hook, the watch list
(_WATCHED_INTENSITIES) and the handler (_on_post_process_effect) are all in place; the source's member
works, and this port raises at the call site instead of returning a number nothing stored.")**
(`effect.py:279-288`).

#### 4.5b `Effects` / `PyEffects` — READ members

`PyEffects`: `GetEffects:324`, `GetBuffs:329`, `GetEffectCount:334`, `GetBuffCount:339`, `EffectExists:344`,
`BuffExists:349`. `Effects`: `get_instance:385`, `GetBuffs:399`, `GetEffects:405`, `GetBuffCount:411`,
`GetEffectCount:417`, `BuffExists:423`, `EffectExists:429`, `HasEffect:435`, `EffectAttributeLevel:445`,
`GetEffectTimeRemaining:454`, `GetBuffID:463`.

### 4.6 `py4gw/inventory.py` (`Inventory`, `:113`) and its binding `py4gw/native_src/item/py_inventory.py` (`PyInventory`, `:335`)

16 ACTIONs in the façade, 11 in the binding. Every one of the binding's actions runs the methods layer's own
guard chain `CanInteractWithItem → IsStorageItem → IsStorageBag → CanAccessXunlaiChest`
(`py_inventory.py:32-38`, `:113-172`) before it calls anything.

| # | member (line) | signature | returns | mechanism | packet? | preconditions / failure |
| --- | --- | --- | --- | --- | --- | --- |
| 78 | `Inventory.IdentifyItem` (`:349`) | `(item_id, id_kit_id) -> None` | `None` | `PyInventory.IdentifyItem` → **M1** `item.identify_item_func`, `CallForm.U32_U32(id_kit_id, item_id)` (`:352-353`, `py_inventory.py:524-541`) | client sends | both records must pass the interact guard, else nothing (`py_inventory.py:531-536`); the function must resolve (`:537-538`) |
| 79 | `Inventory.IdentifyFirst` (`:356`) | `() -> bool` | `True` when an identify was started, `False` on either guard | first-free-kit and first-unidentified walk, then `PyInventory.IdentifyItem` → **M1** (`:363-373`) | client sends | no ID kit or no unidentified item → `False` (`:364-369`) |
| 80 | `Inventory.SalvageItem` (`:376`) | `(item_id, salvage_kit_id) -> None` | `None` | `PyInventory.Salvage` → `_salvage_start`: **M2 packed** `kPreStartSalvage` `{item_id, kit_id}` (`py_inventory.py:251`) **and then M1** `item.salvage_start_func` `CallForm.U32_U32_U32(kit, session, item)` (`py_inventory.py:252-258`) | client sends (the `kPreStartSalvage` message is client-internal; the salvage packet comes from the client's own function) | kit must classify as a salvage kit and the item as salvageable (`py_inventory.py:587-590`); both records must pass the interact guard (`:245-250`) |
| 81 | `Inventory.SalvageFirst` (`:383`) | `() -> bool` | **`False` on every path, including the one where it acted** — the source's own behaviour, pinned by a test (`:386-388`) | first kit / first salvageable, then `PyInventory.Salvage` → **M2 + M1** (`:391-402`) | client sends | no kit or no salvageable item → `False` before acting (`:392-397`) |
| 82 | `Inventory.AcceptSalvageMaterialsWindow` (`:407`) | `() -> None` | `None` (the source's body returns nothing, `:410-413`) | **M3** — `Frame(FrameId.ScreenFrame.C6.SalvageMaterialsDialog.YesButton).click()` if it exists (`:416-420`) | client sends | frame must exist (`:419`); the binding's own `AcceptSalvageWindow` is **commented out** (`:422`) |
| 83 | `Inventory.PickUpItem` (`:989`) | `(item_id, call_target=False) -> None` | `None` | `PyInventory.PickUpItem` → **M2 packed** `kSendInteractItem` with `{item.agent_id, call_target}` (`:992`, `py_inventory.py:368-382`) | client sends | item must resolve by id, else nothing (`py_inventory.py:377-379`); `item_id` is **not** an agent id (`:990`) |
| 84 | `Inventory.DropItem` (`:995`) | `(item_id, quantity=1) -> None` | the delegate's value — `PyInventory.DropItem` returns `None` (`py_inventory.py:384`), so this is `None` despite the docstring's "the one action that returns its call" (`:996`) | `PyInventory.DropItem` → **M1** `item.drop_item_func` `CallForm.U32_U32(item_id, quantity)` (`py_inventory.py:397-399`) | client sends | item must resolve and the function must resolve (`:392-396`) |
| 85 | `Inventory.EquipItem` (`:1001`) | `(item_id, agent_id) -> None` | `None` | `PyInventory.EquipItem` → **M1** `item.equip_item_func` `CallForm.U32_U32(item, agent)` (`py_inventory.py:520-522`) | client sends | item and function must resolve; the interact guard must pass; an empty agent id means the controlled character, and is refused when even that answers nothing (`:511-519`) |
| 86 | `Inventory.UseItem` (`:1007`) | `(item_id) -> None` | `None` | `PyInventory.UseItem` → **M1** `item.use_item_func` `CallForm.U32` (`py_inventory.py:501`) | client sends | item and function must resolve, and the interact guard must pass (`:496-500`) |
| 87 | `Inventory.DestroyItem` (`:1013`) | `(item_id) -> None` | `None` | `PyInventory.DestroyItem` → **M1** `item.destroy_item_func` `CallForm.U32` (`py_inventory.py:411`) | client sends | the binding has **no item check** — only the function must resolve (`:408-410`) |
| 88 | `Inventory.DepositGold` (`:1039`) | `(amount) -> None` | `None` | `PyInventory.DepositGold` → `_change_gold` → **M1** `item.change_gold_func` `CallForm.U32_U32(character, storage)` (`py_inventory.py:448`, `:470-485`) | client sends | `amount == 0` moves as much as fits; an explicit amount is refused when storage would pass 1,000,000 or the character does not hold it (`:438-445`); `_change_gold` re-reads both totals and refuses unless they add up (`:479-482`) |
| 89 | `Inventory.WithdrawGold` (`:1045`) | `(amount) -> None` | `None` | the mirror → **M1** `item.change_gold_func` (`py_inventory.py:468`, `:483-485`) | client sends | `amount == 0` moves as much as fits; refused past the character maximum or when storage does not hold it (`:458-465`) |
| 90 | `Inventory.DropGold` (`:1051`) | `(amount) -> None` | `None` | `PyInventory.DropGold` → **M1** `item.drop_gold_func` `CallForm.U32` (`py_inventory.py:423`) | client sends | the function must resolve and the character must hold at least `amount` (`:417-422`) |
| 91 | `Inventory.MoveItem` (`:1059`) | `(item_id, bag_id, slot, quantity=1) -> None` | `None` | `PyInventory.MoveItem` → **M1** `item.move_item_func`, `CallForm.U32_U32_U32_U32(item, quantity, bag.index, slot)` (`py_inventory.py:567-574`) | client sends | item and bag must resolve and the function must resolve; the bag's array must be at least `slot` long; the quantity is clamped to what the item holds, and a non-positive quantity means all of it (`:554-566`) |
| 92 | `Inventory.DepositItemToStorage` (`:1087`) | `(item_id, Anniversary_panel=True) -> bool` | `True` as soon as the requested amount has moved, else whether anything moved | repeated `Inventory.MoveItem` → **M1** (`:1101-1185`) | client sends | quantity `0` → `False` (`:1139-1140`); the storage bag list is derived from **capacity** (combined size ÷ 25) and reached by dynamic name `getattr(Bags, f"Storage{i}")` (`:1124-1130`) — the source's own reach |
| 93 | `Inventory.WithdrawItemFromStorage` (`:1188`) | `(item_id, quantity=250) -> bool` | `True` when the amount moved, else whether anything moved | repeated `Inventory.MoveItem` → **M1** (`:1205-1250`) | client sends | the amount is clamped to what the item holds, so a request of zero → `False` (`:1200-1203`) |
| — | `Inventory.OpenXunlaiWindow` (`:970`) | `() -> None` | — | delegates to `PyInventory.OpenXunlaiWindow`, which **RAISES** (`:977-978`, `py_inventory.py:596-600`) | — | see §5 |

`Inventory.IsSalvageChoiceDialogVisible` (`:487`), `IsSalvageChoiceMaterialConfirmVisible` (`:454`),
`GetHoveredItemID` (`:1019`), `GetGoldOnCharacter` (`:1027`), `GetGoldInStorage` (`:1033`),
`GetInventorySpace:137`, `GetStorageSpace:150`, `GetZeroFilledStorageArray:177`, `GetFreeSlotCount:209`,
`GetItemCount:217`, `GetModelCount:230`, `GetModelCountInStorage:244`, `GetModelCountInMaterialStorage:258`,
`GetModelCountInEquipped:272`, `GetFirstIDKit:288`, `GetFirstUnidentifiedItem:302`, `GetFirstSalvageKit:315`,
`GetFirstSalvageableItem:336`, `FindItemBagAndSlot:1069`, `IsStorageOpen:981`, `inventory_instance:129` are
READ. `Inventory._get_salvage_choice_dialog_options` etc. are private.

**`PyInventory` (`native_src/item/py_inventory.py:335`) — the same 11 ACTIONs, one layer down:**
`PickUpItem:368`, `DropItem:384`, `DestroyItem:401`, `DropGold:413`, `DepositGold:425`, `WithdrawGold:450`,
`UseItem:489`, `EquipItem:503`, `IdentifyItem:524`, `MoveItem:543`, `Salvage:576`. Its READ members:
`GetIsStorageOpen:343`, `GetGoldAmount:348`, `GetGoldAmountInStorage:354`, `GetHoveredItemID:360`.
`Bag` (`:262`): `GetContext:280`, `GetSize:296`, `GetItemCount:306`, `GetItems:311` — READ.

### 4.7 `py4gw/merchant.py` — `PyMerchant` (`:261`) and `Trading` (`:474`)

Both merchant calls pass their records **by value on the stack** (`CallForm.STACK_WORDS`,
`shared_block.py:385-398`): the words are written into the block's data region at
`TRANSACTION_RECORD_OFFSET` and the payload pushes them right-to-left and releases them
(`merchant.py:169-222`).

| # | member (line) | signature | returns | mechanism | packet? | preconditions / failure |
| --- | --- | --- | --- | --- | --- | --- |
| 94 | `PyMerchant.trader_buy_item` (`:273`) | `(self, item_id: int, cost: int) -> bool` | `False` when the live item record does not resolve, else the call's `True` | **M1** — `merchant.transact_item_func`, `CallForm.STACK_WORDS` with `TRADER_BUY=0xC`, `cost*1`, empty give, recv `{1, &item->item_id, 0}` (`:280-289`, `_transact:169-197`) | client sends | `_live_item` must return the record's address; `client.resolves(TRANSACT_ITEM_FUNC)` must hold, else `False` (`:186-187`) |
| 95 | `PyMerchant.trader_sell_item` (`:291`) | `(self, item_id: int, price: int) -> bool` | as above | **M1** — `TRADER_SELL=0xD`, give `{1, item, 0}`, empty recv (`:294-303`) | client sends | as above |
| 96 | `PyMerchant.trader_request_quote` (`:305`) | `(self, item_id: int) -> bool` | as above | **M1** — `merchant.request_quote_func` `STACK_WORDS` with `TRADER_BUY` and the id in `recv` (`:312-319`, `_request_quote:200-222`) | client sends | live item + resolved function (`:313`, `:211-212`) |
| 97 | `PyMerchant.trader_request_sell_quote` (`:321`) | `(self, item_id: int) -> bool` | as above | **M1** — `TRADER_SELL`, id in `give` (`:327-334`) | client sends | as above |
| 98 | `PyMerchant.merchant_buy_item` (`:338`) | `(self, item_id: int, cost: int) -> bool` | as above | **M1** — `MERCHANT_BUY=0x1` (`:341-350`) | client sends | as above |
| 99 | `PyMerchant.merchant_sell_item` (`:352`) | `(self, item_id: int, price: int) -> bool` | as above | **M1** — `MERCHANT_SELL=0xB` (`:355-364`) | client sends | as above |
| 100 | `PyMerchant.crafter_buy_item` (`:368`) | `(self, item_id: int, cost: int, give_item_ids: list[int], give_item_quantities: list[int]) -> bool` | `False` when the two lists differ in length, else the call's `True` | **M1** — `CRAFTER_BUY=0x3`; the two lists are placed at `GIVE_IDS_OFFSET`/`GIVE_QUANTITIES_OFFSET` and their addresses handed over (`:383-392`, `_give_lists:225-246`) | client sends | lengths must match (`:383-384`); **no** `GetItemById` guard on this one — the source's own asymmetry (`:376-380`); more than `MAX_GIVE_ITEMS=24` ids → `ValueError` naming the bound (`:233-237`) |
| 101 | `PyMerchant.collector_buy_item` (`:396`) | `(self, item_id: int, cost: int, give_item_ids: list[int], give_item_quantities: list[int]) -> bool` | as above | **M1** — `COLLECTOR_BUY=0x2`, the same two placed lists; the reset happens **after** the pointers are taken (`:405-416`) | client sends | lengths must match (`:405-406`) |
| 102-109 | `Trading.Trader.RequestQuote` (`:522`), `RequestSellQuote` (`:528`), `BuyItem` (`:534`), `SellItem` (`:540`), `Trading.Merchant.BuyItem` (`:547`), `SellItem` (`:553`), `Trading.Crafter.CraftItem` (`:566`), `Trading.Collector.ExchangeItem` (`:586`) | as the source declares them, including `ExchangeItem(item_id, cost=0, item_list=[], item_quantities=[])` with its two **mutable defaults** (`:586-591`) | `None` (the façade discards the binding's bool) | each one is `Trading.merchant_instance().<binding member>` → **M1** as above (`:522-600`) | client sends | as the binding member |

`Trading.merchant_instance:482`, `Trading.IsTransactionComplete:491`, `Trader.GetQuotedItemID:498`,
`Trader.GetQuotedValue:504`, `Trader.GetOfferedItems:510`, `Trader.GetOfferedItems2:516`,
`Merchant.GetOfferedItems:559`, `Crafter.GetOfferedItems:579`, `Collector.GetOfferedItems:603`,
`PyMerchant.get_trader_item_list:420`, `get_trader_item_list2:429`, `get_merchant_item_list:438`,
`get_quoted_value:447`, `get_quoted_item_id:456`, `is_transaction_complete:461`, `update:466` are READ.
`PyMerchant.update` is empty **because native's body is empty** (`:466-471`).
`MerchantTransactionInfo.words:111` and `MerchantQuoteInfo.words:125` are pure.

### 4.8 `py4gw/skillbar.py` — `PySkillbar` (`:679`) and `SkillBar` (`:967`)

| # | member (line) | signature | returns | mechanism | packet? | preconditions / failure |
| --- | --- | --- | --- | --- | --- | --- |
| 110 | `PySkillbar.ChangeHeroSecondary` (`:796`) | `(self, hero_index: int, profession: int) -> bool` | `False` when the hero agent id is zero, else `True` after the call | **M1** — `skillbar.change_secondary_func`, `CallForm.U32_U32(agent, profession)` (`:802-807`) | client sends | `_hero_agent_id(hero_index)` must be non-zero (`:799-801`) |
| 111 | `PySkillbar.LoadSkillTemplate` (`:810`) | `(self, skill_template: str) -> bool` | `load_skill_template`'s bool | `decode_skill_template` then `load_skillbar` (**M1**, `STACK_WORDS`) and `set_attributes` (**M1**, `STACK_WORDS`) (`:825`, `:429-479`, `:608-635`) | client sends | outpost instance, a template that decodes, a controlled character and its profession state, the primary/secondary reconciliation (`:818-822`); `load_skillbar` refuses a zero agent id (`:440-441`), `set_attributes` likewise (`:457-459`) |
| 112 | `PySkillbar.LoadHeroSkillTemplate` (`:827`) | `(self, hero_index: int, skill_template: str) -> bool` | same | `load_hero_skill_template` → the hero branch of the same two calls (`:835`, `:636-678`) | client sends | the hero branch's own guards (`:827-835`) |
| 113 | `PySkillbar.UseSkill` (`:837`) | `(self, slot: int, target: int = 0) -> bool` | `True` after the keypress | optional `Player.ChangeTarget` (**M1**) then **M3** `UIManager.Keypress(ControlAction_UseSkill1 + slot - 1, 0)` (`:866-872`) | client sends | `slot` outside `1..8` → `IndexError("Skill slot out of range (must be between 1 and 8) Given: N")` (`:861-864`); the previous target is **not** restored here (`:853-855`) |
| 114 | `PySkillbar.UseSkillTargetless` (`:874`) | `(self, slot: int) -> bool` | `True` after the keypress | **M3** — the keypress alone, no target change (`:884-891`) | client sends | the same `IndexError` (`:884-887`) |
| 115 | `PySkillbar.HeroUseSkill` (`:893`) | `(self, target_agent_id: int, skill_number: int, hero_index: int) -> bool` | `False` for a hero number outside `1..7`, else `True` | `Player.ChangeTarget` (**M1**) → **M3** `UIManager.Keypress(hero_base + skill_idx, 0)` → restore the previous target (**M1**) (`:914-928`) | client sends | `_HERO_SKILL_ACTION_BASE.get(hero_index - 1)` must hit, else `False` (`:915-917`); `skill_number` is **not** validated — only the hero number is (`:902-904`) |
| 116-121 | `SkillBar.LoadSkillTemplate` (`:971`), `LoadHeroSkillTemplate` (`:983`), `UseSkill` (`:1031`), `UseSkillTargetless` (`:1044`), `HeroUseSkill` (`:1056`), `ChangeHeroSecondary` (`:1069`) | `LoadSkillTemplate(skill_template)`, `LoadHeroSkillTemplate(hero_index, skill_template)`, `UseSkill(skill_slot, target_agent_id=0)`, `UseSkillTargetless(skill_slot)`, `HeroUseSkill(target_agent_id, skill_number, hero_number)`, `ChangeHeroSecondary(hero_index, secondary_profession)` | `None` (the façade discards the binding's bool) | each is `PySkillbar().<member>` → as above (`:979-1079`) | client sends | as the binding member |

READ members: `PySkillbar.GetContext:692`, `GetSkill:708`, `GetSkills:720`, `agent_id:726`, `disabled:732`,
`casting:738`, `GetHeroSkillbar:747`, `GetHoveredSkill:762`, `IsSkillUnlocked:780`, `IsSkillLearnt:788`;
`SkillBar.GetSkillbar:995`, `GetZeroFilledSkillbar:1009`, `GetHeroSkillbar:1018`, `GetSkillIDBySlot:1082`,
`GetSlotBySkillID:1096`, `GetSkillData:1112`, `GetHoveredSkillID:1124`, `IsSkillUnlocked:1136`,
`IsSkillLearnt:1148`, `GetAgentID:1160`, `GetDisabled:1171`, `GetCasting:1182`;
`SkillbarSkill`: `id:114`, `adrenaline_a:120`, `adrenaline_b:126`, `recharge:132`, `event:138`,
`get_recharge:144`. `SkillbarSkill.__init__:108` is a snapshot constructor.

### 4.9 `py4gw/quest.py` — class `Quest` (`:36`), over `PyQuest` (`native_src/quest/py_quest.py:460`)

| # | member (line) | signature | returns | mechanism | packet? | preconditions / failure |
| --- | --- | --- | --- | --- | --- | --- |
| 122 | `Quest.SetActiveQuest` (`:52`) | `(quest_id: int) -> None` | `None` | `PyQuest.set_active_quest_id` → **M1** `quest.set_active_quest_func`, `CallForm.U32` (`:55`, `py_quest.py:479-484`) | client sends | negative id → `False`, no call (`py_quest.py:479-480`); the function must resolve **and** the quest must be in the log, else nothing is called (`:482`) |
| 123 | `Quest.AbandonQuest` (`:58`) | `(quest_id: int) -> None` | `None` | **M1** — `quest.abandon_quest_func`, `CallForm.U32` (`:61`, `py_quest.py:501-505`) | client sends | the same two guards (`:501-504`) |
| 124 | `Quest.RequestQuestInfo` (`:100`) | `(quest_id: int, update_marker: bool = False) -> None` | `None` | **M1 twice, in the source's order** — `quest.request_quest_info_func` `CallForm.U32`, then `quest.request_quest_data_func` `CallForm.U32_U32(quest_id, update_markers)` (`:107`, `py_quest.py:564-576`) | client asks the server for the info; the library sends nothing | negative id → `False` (`:564-565`); both functions must resolve and the quest must be in the log (`:567-571`) |

**The four request members are CAPABILITY** (they drive the client's decoder, not a state change):
`Quest.RequestQuestName:110`, `RequestQuestDescription:128`, `RequestQuestObjectives:146`,
`RequestQuestLocation:164`, `RequestQuestNPC:182` → `_request_field` (`py_quest.py:422`) →
`begin_string_decode` + `async_decode_str` (**M1** `ui.validate_async_decode_str_func`), with the
per-field mission values for a negative id (`py_quest.py:359-419`).

READ: `GetActiveQuest:46`, `IsQuestCompleted:64`, `IsQuestPrimary:70`, `IsMissionMapQuestAvailable:76`,
`GetQuestData:82`, `GetQuestLog:88`, `GetQuestLogIds:94`, `IsQuestNameReady:116`, `GetQuestName:122`,
`IsQuestDescriptionReady:134`, `GetQuestDescription:140`, `IsQuestObjectivesReady:152`,
`GetQuestObjectives:158`, `IsQuestLocationReady:170`, `GetQuestLocation:176`, `IsQuestNPCReady:188`,
`GetQuestNPC:194`, `quest_instance:40`.

### 4.10 `py4gw/ui_manager.py` — class `UIManager` (`:187`)

17 ACTIONs. The preference setters are the widest: they write through the client's own setter and then
drive the client's follow-up functions (`py4gw/ui/preferences.py`).

| # | member (line) | signature | returns | mechanism | packet? | preconditions / failure |
| --- | --- | --- | --- | --- | --- | --- |
| 125 | `SendUIMessage` (`:453`) | `(msgid: int, values: list[int], skip_hooks: bool = False) -> bool` | `False` when the sender does not resolve; `True` for the masked high id range **without sending**; `True` once sent | **M2 raw** — a zeroed **sixteen-word** payload is built in the block's data region and `send_ui_message_raw(msgid, address, 0)` is called (`:486-492`); values past sixteen are dropped, as native's own copy loop does (`:470-471`) | no packet of its own; whatever the message causes is the client's | `client.resolves("ui.send_ui_message_func")` else `False` (`:477-479`); `skip_hooks` is **recorded, not reproduced** (`:466-471`) |
| 126 | `SendUIMessageRaw` (`:496`) | `(msgid: int, wparam: int, lparam: int, skip_hooks: bool = False) -> bool` | same three answers | **M2 raw** — the two words go through untouched (`:517`) | as above | the sender must resolve (`:513-514`) |
| 127 | `DrawOnCompass` (`:521`) | `(session_id: int, points: list[tuple[int, int]]) -> bool` | `False` when the function does not resolve, else `True` | **M1** — `ui.draw_on_compass_func` `CallForm.U32_U32_U32(session_id, len(points), address)`; the `CompassPoint` array (two `int`s each) is placed in the block (`:538-552`) | no | unresolved function → `False` (`:541-542`); **an empty list is not refused** — it reaches the client as `point_count == 0` (the source's function makes no such check, `:532-535`) |
| 128 | `LoadSettings` (`:555`) | `(data: list[int]) -> None` | `None` | **M1** — `ui.load_settings_func` `CallForm.U32_U32(len, address)` with the bytes placed in the block (`:568-577`) | no | unresolved function → returns, nothing called (`:573-574`) |
| 129 | `SetFPSLimit` (`:830`) | `(limit: int) -> None` | `None` | **M4** — `preferences.set_frame_limit` places the word and submits `Operation.WRITE_MEMORY` to the client's own command-line number buffer (`:840-842`, `ui/preferences.py:337-368`) | no | the buffer address must resolve, else `False` and no write (`preferences.py:337-356`) |
| 130 | `SetEnumPreference` (`:911`) | `(pref: int, value: int) -> None` | `None` | `preferences.set_enum_preference`: **M1** into `g_set_enum_preference_func` after validating against the client's own option list, then the follow-up setters it drives (`Antialiasing`/`TerrainQuality`/`ShaderQuality` rewrites and the renderer/shadow/terrain/reflection/UI-scale calls) (`:922-924`, `preferences.py:427-499`) | no | the guard chain and the option list are the source's (`:914-917`) |
| 131 | `SetIntPreference` (`:927`) | `(pref: int, value: int) -> None` | `None` | `preferences.set_number_preference`: **M1** `g_set_number_preference_func` after a clamp through the client's own `clamp_proc`, then the five volume channels, the master volume and eleven renderer metrics (`:936-938`, `preferences.py:501-583`) | no | the `PrefsInitialised()` guard (`:930-933`) |
| 132 | `SetStringPreference` (`:941`) | `(pref: int, value: str) -> None` | `None` | `preferences.set_string_preference`: the UTF-16 text is placed in the block and its address passed to **M1** `g_set_string_preference_func` (`:959-961`, `preferences.py:585-612`) | no | setter resolved, prefs initialised, index below `StringPreference::Count` (`:944-947`) |
| 133 | `SetBoolPreference` (`:964`) | `(pref: int, value: bool) -> None` | `None` | `preferences.set_flag_preference`: **M1** `g_set_flag_preference_func`, then — for `IsWindowed` only — read `g_get_game_renderer_mode_func(0)` and write `g_set_game_renderer_mode_func(0, value ? 2 : 0)` when it differs (`:973-975`, `preferences.py:614-651`) | no | the guard chain (`:964-970`) |
| 134 | `SetKeyMappings` (`:1012`) | `(mappings: List[int]) -> None` | `None` | **M4** — `min(0x75, len(mappings))` words copied **into the client's own remap table** by `Operation.WRITE_MEMORY` (the table address comes from `ui.key_mappings_table`, which derives it from the `FrKey.cpp` assertion's first `.text` use, `+0xD`, `.data`-checked) (`:1024-1046`, `:986-995`) | no | the table must resolve, else returns (`:1025-1029`); an empty list writes nothing (`:1030-1032`); a shorter list writes a prefix and leaves the tail |
| 135 | `Keydown` (`:1049`) | `(key: int, frame_id: int) -> None` | `None` | **M3** — `_send_key_action(frame_id, key, kKeyDown)`: a one-word `packet::KeyAction` in the block, sent to the frame's callbacks with the frame's `frame_callbacks` address in ECX (`:1064`, `_send_key_action:1539-1575`) | no | `frame_id == 0` means the client's **button-action frame** — `GetHashByLabel(L"Game")` then `GetChildFrame(frame, 6)` (`:1556`, `_button_action_frame_id:1483-1512`); if the sender, that frame, its pointer, or its callback array is missing, it returns without sending (`:1554-1565`) |
| 136 | `Keyup` (`:1067`) | `(key: int, frame_id: int) -> None` | `None` | **M3** — the same with `kKeyUp` (`:1071`) | no | as above |
| 137 | `Keypress` (`:1074`) | `(key: int, frame_id: int) -> None` | `None` | **M3 twice** — `Keydown` then `Keyup`, immediately: native's `game_thread::Enqueue` runs its callable **inline** when it is already on the game thread, so the key-up is not deferred (`:1077-1088`) | no | as above |
| 138 | `SetWindowVisible` (`:1153`) | `(window_id: int, visible: bool) -> None` | `None` | **M1** — `ui.set_window_visible_func` `CallForm.U32_U32_U32_U32(window_id, visible ? 1 : 0, 0, 0)` (`:1166-1177`) | no | function must resolve and `window_id < 0x66` (`WindowID_Count`, Native's bound), else returns (`:1166-1169`) |
| 139 | `SetWindowPosition` (`:1180`) | `(window_id: int, position: list[int]) -> None` | `None` | **M1** — the client's existing `state` word is read, then `{state, p1x, p1y, p2x, p2y}` is placed in the block and its address passed to `ui.set_window_position_func` `CallForm.U32_U32_U32_U32(window_id, address, 0, 0)` (`:1200-1217`) | no | fewer than four numbers → returns (`:1201-1202`); function must resolve, `window_id < 0x66` (`:1203-1206`) |
| 140 | `ClickDialogButton` (`:1331`) | `(choice: int, debug: bool = False) -> bool` | `False` for an out-of-range choice, else `True` | `GetDialogButtons` (READ: frames at the detected offset, BFS fallback) then **M3** `target.click()` (`:1339-1352`) | no | `choice - 1` must be inside the button list, else `False` (`:1340-1345`); `Frame.click` refuses an unusable frame (`frame.py:1763-1764`) |
| 141 | `ConfirmMaxAmountDialog` (`:1421`) | `() -> None` | `None` | **M3** — `Frame(FrameId.MaxButton).click()` and `Frame(FrameId.OkButton).click()`, each only if it exists (`:1424-1431`) | no | per-frame existence checks |

`UIManager.FindDialogOffset` (`:1239`) writes **host-side** module state only (`DIALOG_CHILD_OFFSET`,
`:1250`, `:1284`) — DECLARED, NO GAME REACH. `UIManager.SetOpenLinks` (`:773`) **RAISES** (§5).
`UIManager.GetIntPreference:874`, `GetEnumPreference:861`, `GetStringPreference:886`, `GetBoolPreference:899`,
`GetTextLanguage:439` and `GetFPSLimit:814` are **CAPABILITY** in mechanism (each drives a typed call into the
client's own getter — `ui.get_number_preference_func`, `ui.get_flag_preference_func`,
`ui.get_enum_preference_func`, `ui.get_string_preference_func` at `ui/preferences.py:206`, `:239`, `:291`,
`:309`, `:330`, and `get_frame_limit:245-270` which reaches `get_enum_preference` for its limiter) while
returning data. `UIManager.GetPreferenceOptions:845` is **READ**: it reads the client's own
`EnumPreferenceInfo` table and issues no call (`ui/preferences.py:369-392`).
`UIManager.AsyncDecodeStr` (`:672`) is **CAPABILITY** (it places the string, calls
`ui.validate_async_decode_str_func` **M1**, and reads the slot exactly once after the call, as the source
does — `:689-701`).

**READ members:** `GetIOEventsForFrame:331`, `GetFrameLogs:370`, `ClearFrameLogs:392` (host-side),
`GetUIMessageLogs:405`, `ClearUIMessageLogs:429`, `IsWorldMapShowing:634`, `IsUIDrawn:654`,
`IsValidEncStr:704`, `IsValidEncBytes:718`, `UInt32ToEncStr:743`, `EncStrToUInt32:760`, `IsShiftScreenshot:797`,
`GetKeyMappings:978`, `GetCurrentTooltipAddress:613`, `GetSettings:580`, `GetWindoPosition:1091`,
`IsWindowVisible:1131`, `IsLockedChestWindowVisible:1222`, `IsNPCDialogVisible:1233`,
`GetDialogButtons:1287`, `GetDialogButtonCount:1355`, `GetDialogButtonFrames:1368`, `RegisterFrameIOEventCallback:220`,
`UnregisterFrameIOEventCallback:232`, `RegisterFrameIOCallbacks:346`.

### 4.11 `py4gw/native_src/chat/chat.py` — module functions

Chat is where the CPU-side buffer is built **where the source builds it content-wise**: the same prefix, the
same clamp, the same terminator, placed in the block's data region because the client is handed a pointer
(`chat.py:10-22`).

| # | member (line) | signature | returns | mechanism | packet? | preconditions / failure |
| --- | --- | --- | --- | --- | --- | --- |
| 142 | `SendChat` (`:105`) | `(channel: ChatChannel \| int \| str, message: str) -> bool` | `True` once the call has been made, `False` on any of the source's guards | **M1** — `chat.send_chat_func`, `CallForm.U32_U32(address, 0)`; the text is placed at `BUFFER_OFFSET` (`:151-152`, `_place`) | client sends | empty message → `False` (`:133-134`); `not client.resolves(SEND_CHAT_FUNC)` → `False` (`:135-136`); a channel byte `GetChannel` does not know → `False` (`:147-148`); a whisper buffer ≥140 units → `False` (`:143-144`); a channel message is **clamped** to 120 units, not refused (`:149`, `:55-57`); a buffer that does not fit raises `ValueError` (`:163-167`) |
| 143 | `WriteChat` (`:245`) | `(channel: ChatChannel \| int, message: str, sender: str \| None = None, transient: bool = False) -> None` | `None` | wraps both strings as the encoded form and delegates to `WriteChatEnc` (`:260-265`) | **no** | none |
| 144 | `WriteChatEnc` (`:274`) | `(channel: ChatChannel \| int, message_encoded: list[int], sender_encoded: list[int] \| None = None, transient: bool = False) -> None` | `None` | **M2 packed** — `client.send_ui_message(WRITE_TO_CHAT_LOG=0x1000007F, channel, message_address)` where the line sits in the block's data region (`:310-322`) | **no** — the line exists only in this client's log (`:173-182`) | a line longer than the buffer raises `ValueError` (`:348-352`); `param.channel2` cannot be set — a two-word payload has no word for it, so it arrives `0`; that divergence is recorded (`:297-300`) |
| 145 | `SendFakeChat` (`:481`) | `(channel: ChatChannel \| int, message: str) -> None` | `None` | `WriteChat(..., transient=True)` (`:488`) | no | none |
| 146 | `SendFakeChatColored` (`:491`) | `(channel: ChatChannel \| int, message: str, r: int, g: int, b: int) -> None` | `None` | `FormatChatMessage` then `WriteChat(..., transient=True)` (`:500-502`) | no | none |

READ / pure: `GetChannel:74`, `GetChatLog:359`, `watch_entries:395`, `live_history:407`,
`reset_live_history:413`. `_on_chat_log_line:420`, `_on_string_decoded:447` are the connection's registered
handlers and drive decodes (**CAPABILITY**).

### 4.12 `py4gw/pathing.py`, `py4gw/item.py`, `py4gw/skill.py`, `py4gw/agent.py`, `py4gw/agent_array.py`, `py4gw/dialog.py`

These six modules contain **no ACTION**: nothing in them changes game state.

* **`pathing.py`** — `PathPlanner` (`:658`): `plan(self, start_x, start_y, start_z, goal_x, goal_y, goal_z)` (`:682`)
  and `compute_immediate(...)` (`:704`) are **CAPABILITY**: both call the client's own path finder through
  **M1** — `pathing.find_path_func`, `CallForm.STACK_WORDS` with six **addresses** placed in the block
  (`_find:736-805`) — and read the count and the `PathPoint` array back out of the block (`:794-805`). The
  finder writes up to thirty 0x10-byte records into the buffer the caller supplies, which is why the data
  region is 8192 bytes (`shared_block.py:135-141`). `get_status:719`, `is_ready:722`, `was_successful:725`,
  `get_path:729`, `reset:732` are pure/READ. `AutoPathing` (`:902`): `load_pathing_maps:924`,
  `clear_navmesh_cache:940`, `force_reload_navmesh:945`, `get_navmesh:956`, `get_path:975`,
  `get_path_to:1074` — host-side navmesh work over reads. `AABB:80`, `TrapezoidBSP:137`, `NavMesh:207`,
  `AStar:525`, `chaikin_smooth_path:593`, `densify_path2d:606` are pure geometry.
* **`item.py`** — `PyItem` (`:212`) and `Item` (`:503`) are READ, with one **CAPABILITY** pair:
  `PyItem.RequestName` (`:394`) places the item's complete-name encoded string and calls
  `async_decode_str` (**M1** `ui.validate_async_decode_str_func`, `:405-419`); `PyItem.IsItemNameReady`
  (`:421`) polls the decode slot with native's own 1000 ms bound and stores `"No Item"`, `"Timeout"` or the
  text (`:429-447`); `Item.RequestName:773` and `IsNameReady:779` delegate to them. `PyItem.IsItemValid:341`,
  `GetInfoString:374`, `GetNameEnc:379`, `GetCompleteNameEnc:384`, `GetSingleItemName:389`, `GetName:449`,
  `GetCompositeModelIDs:456`, `GetContext:283` are READ. `PyItemType:105`, `PyDyeColor:144`, `PyDyeInfo:179`,
  `Bag:474`, `Item.Mods:511`, `Item.Rarity:870`, `Item.Properties:914`, `Item.Type:1088`, `Item.Usage:1139`,
  `Item.Dye:1202` are all READ.
* **`skill.py`** — no member reaches the client at all: `Skill` (`:276`) and its six nested namespaces
  (`Data:398`, `Attribute:497`, `Flags:540`, `Animations:769`, `ExtraData:824`) read the client's own static
  skill-constant table through `PySkill.GetContext` (`:206`). `SkillID:71`, `SkillType:95`,
  `SkillProfession:116` are enums.
* **`agent.py`** — `Agent` (`:439`) is 148 static members, **all READ** except: `enable` (`:495`,
  **RAISES**, §5), `GetNameByID` (`:577`) / `RequestName` (`:672`, the source's alias) / `IsNameReady`
  (`:675`), which are **CAPABILITY** — they place the agent's encoded name and call the client's decoder
  (**M1**), taking the text from the slot's own state rather than the `STRING_DECODED` event, which was
  measured to read empty for this route (`:624-668`); and `GetProfessionsTexturePaths` (`:2067`, **RAISES**,
  §5). The member list, with lines, is at `§4.12b` below.
  The connection registers `agent_module._reset_name_state()` at both ends (`client.py:543-545`, `:1840-1845`).
* **`agent_array.py`** — `AgentArray` (`:40`) is READ: `GetAgentArray:43`, `GetAllyArray:53`,
  `GetNeutralArray:63`, `GetEnemyArray:73`, `GetSpiritPetArray:83`, `GetMinionArray:93`,
  `GetNPCMinipetArray:103`, `GetItemArray:113`, `GetOwnedItemArray:123`, `GetGadgetArray:133`,
  `GetDeadAllyArray:143`, `GetDeadEnemyArray:153`, `GetAgentByID:162`. `Manipulation` (`:171`),
  `Sort` (`:223`), `Filter` (`:290`) and `Routines.DetectLargestAgentCluster` (`:348`) are **pure list
  work** — they neither read nor write the client.
* **`dialog.py`** — `Dialog` (`:1047`) is READ plus journals, **except** three **CAPABILITY** members:
  `initialize` (`:1098`), `terminate` (`:1120`) and `clear_cache` (`:1154`) manage the state the
  connection's registered handlers fill and drain (`client.py:531-537`, `:1805`). `DialogTables` (`:479`):
  `get:504`, `invalidate:522`, `resolve_loader_get_text:527`, `read_uint32:546` are READ.
  **The one place a dialog member would call the client is unreachable by construction**: at
  `dialog.py:855` `_queue_dialog_text_decode` **raises** before reaching its
  `require_client().call_address(address, CallForm.U32, dialog_id)` at `:872-874`, because this build's
  `DialogLoader_GetText` is not identified (`:855-861`). So `Dialog.get_dialog_text_decoded` (`:1444`)
  cannot reach the client today. READ members: `get_active_dialog:1205`, `get_active_dialog_buttons:1230`,
  `get_last_selected_dialog_id:1257`, `is_dialog_displayed:1269`, `is_dialog_active:1281`,
  `is_dialog_available:1313`, `get_dialog_info:1323`, `enumerate_available_dialogs:1347`,
  `read_dialog_flags:1359`, `read_dialog_frame_type:1374`, `read_dialog_event_handler:1391`,
  `read_dialog_content_id:1408`, `read_dialog_property_id:1425`, `get_dialog_text_decoded:1444`,
  `is_dialog_text_decode_pending:1455`, `get_dialog_text_decode_status:1461`, `get_dialog_event_logs:1473`,
  `get_dialog_event_logs_received:1483`, `get_dialog_event_logs_sent:1489`, `clear_dialog_event_logs:1495`,
  `clear_dialog_event_logs_received:1501`, `clear_dialog_event_logs_sent:1507`,
  `get_dialog_callback_journal:1513`, `get_dialog_callback_journal_received:1524`,
  `get_dialog_callback_journal_sent:1530`, `clear_dialog_callback_journal:1536`,
  `clear_dialog_callback_journal_received:1542`, `clear_dialog_callback_journal_sent:1548`,
  `clear_dialog_callback_journal_filtered:1554`.

#### 4.12b `Agent` — READ member lines

`IsValid:473`, `GetAgentByID:512`, `GetLivingAgentByID:540`, `GetItemAgentByID:553`,
`GetGadgetAgentByID:565`, `GetEncNameByID:681`, `GetEncNameStrByID:688`, `GetAgentIDByName:701`,
`GetAgentIDByEncString:724`, `GetModelIDByEncString:749`, `GetAttributes:767`, `GetAttributesDict:788`,
`GetInstanceFrames:803`, `GetInstanceUptime:812`, `GetAgentEffects:835`, `GetTypeMap:845`,
`GetModelState:854`, `GetModelID:863`, `IsLiving:878`, `IsItem:887`, `IsGadget:896`, `GetPlayerNumber:905`,
`GetLoginNumber:914`, `IsSpirit:923`, `IsPet:935`, `IsMinion:947`, `GetOwnerID:959`, `GetXY:968`,
`GetXYZ:983`, `GetZPlane:994`, `GetNameTagXYZ:1004`, `GetModelScale1:1013`, `GetModelScale2:1023`,
`GetModelScale3:1033`, `GetNameProperties:1043`, `GetVisualEffects:1053`, `GetTerrainNormalXYZ:1063`,
`GetGround:1073`, `GetAnimationCode:1083`, `GetWeaponItemType:1093`, `GetOffhandItemType:1103`,
`GetAnimationType:1113`, `GetWeaponAttackSpeed:1123`, `GetAttackSpeedModifier:1133`, `GetAgentModelType:1143`,
`GetTransmogNPCID:1153`, `GetGuildID:1163`, `GetTeamID:1176`, `GetAnimationSpeed:1186`,
`GetAnimationID:1196`, `GetRotationAngle:1206`, `GetRotationCos:1215`, `GetRotationSin:1224`,
`GetVelocityXY:1233`, `GetProfessions:1244`, `GetProfessionNames:1254`, `GetProfessionShortNames:1271`,
`GetProfessionIDs:1288`, `GetLevel:1297`, `GetEnergy:1306`, `GetMaxEnergy:1315`, `GetEnergyRegen:1324`,
`GetEnergyPips:1333`, `GetHealth:1349`, `GetMaxHealth:1358`, `GetHealthRegen:1367`, `GetHealthPips:1376`,
`CanAct:1393`, `IsMoving:1403`, `IsKnockedDown:1412`, `GetKnockDownTimeRemaining:1421`, `IsBleeding:1430`,
`IsCrippled:1439`, `IsDeepWounded:1448`, `IsPoisoned:1457`, `IsConditioned:1466`, `IsEnchanted:1475`,
`IsHexed:1484`, `IsDegenHexed:1493`, `IsDead:1502`, `IsExploitable:1526`, `IsExploitableCorpse:1535`,
`IsUsedCorpse:1541`, `IsExploitedCorpse:1550`, `IsAlive:1556`, `IsWeaponSpelled:1579`,
`IsInCombatStance:1588`, `HasStance:1597`, `GetStanceID:1606`, `GetStanceCooldown:1612`, `IsAggressive:1618`,
`IsAttacking:1629`, `IsCasting:1638`, `GetCastingSkillID:1647`, `GetTarget:1660`, `GetCastingTarget:1671`,
`GetRemainingCastTime:1677`, `GetRemainingRechargeTime:1683`, `IsTargeted:1689`, `GetAgetsTargeting:1695`,
`IsSkillOnCooldown:1701`, `IsCooldownEstimated:1707`, `GetSkillsOnCooldown:1713`,
`GetRecentHealingReceived:1719`, `GetRecentHealingDealt:1725`, `HasEffectRenewed:1731`,
`GetObservedSkillbar:1737`, `GetAttackTarget:1743`, `IsIdle:1749`, `HasBossGlow:1758`, `GetWeaponType:1767`,
`IsHoldingItem:1785`, `GetWeaponExtraData:1795`, `IsMartial:1810`, `IsCaster:1839`, `IsMelee:1857`,
`IsRanged:1881`, `GetDaggerStatus:1896`, `GetAllegiance:1905`, `IsPlayer:1923`, `IsNPC:1930`,
`GetNPCModelByID:1937`, `GetNPCFlags:1969`, `IsFleshy:1979`, `HasQuest:1991`, `IsDeadByTypeMap:2000`,
`IsFemale:2009`, `IsHidingCape:2018`, `CanBeViewedInPartyWindow:2027`, `IsSpawned:2036`,
`IsBeingObserved:2045`, `GetOvercast:2054`, `GetItemAgentOwnerID:2100`, `GetItemAgentItemID:2111`,
`GetItemAgentExtraType:2120`, `GetItemAgenth00CC:2129`, `GetGadgetID:2140`, `GetGadgetAgentID:2149`,
`GetGadgetAgentExtraType:2158`, `GetGadgetAgenth00C4:2167`, `GetGadgetAgenth00C8:2176`,
`GetGadgetAgenth00D4:2185`. Class constants `ILLUSIONARY_WEAPONRY_ID:450`, `DEAD_HEALTH_EPSILON:455`.

---

## 5. Members that raise `NotImplementedError` (public, in the files inventoried)

All of these are declared and raise at the call site; **the quotes are the messages verbatim**. Most are
built from `_unported(member, requirement)` (`inventory.py:88-95`, `map.py:…`, `ui_manager.py:177-184`,
`party.py:43-46`, `agent.py:83-87`, `dialog.py:167-…`, `py_inventory.py:86-93`), whose text is
`f"{member} is declared but not built here yet: it needs {requirement}. The source's member works; this port
raises at the call site and names the work item instead of returning a wrong value."` — only the
`requirement` differs, so the requirements are quoted below.

| member (file:line) | requirement / full message |
| --- | --- |
| `Player.player_instance` (`player.py:302`) | its own `NotImplementedError`: *"Player.player_instance is a port artifact that is no longer valid: it returned Reforged's in-process PyPlayer binding object, and this project has no player object. Every value that object provided is answered by this class's own members — read them directly instead of through an instance."* |
| `Agent.enable` (`agent.py:495`) | *"the per-frame callback registration PyCallback.PyCallback.Register(..., Phase.PreUpdate, ...) (Agent.py:52-60; stubs/PyCallback.pyi:40), which this project has no frame loop for"* |
| `Agent.GetProfessionsTexturePaths` (`agent.py:2067`) | *"the injected runtime's own module directory, which PySystem.Console.get_projects_path() returns (system_bindings.cpp:72-74 → process_manager::GetModuleDirectory, process_manager.cpp:38-40) and where its Assets/Textures/Profession_Icons live. This project is a controller package with no such module and ships no such assets, so there is no path to build"* |
| `Party.party_instance` (`party.py:796`) | *"it returns a PyParty native binding object, which only exists inside the client"* |
| `Effects.GetAlcoholLevel` (`effect.py:479` → `:364` → `get_alcohol_level:254`) | full message quoted in §4.5 |
| `Effects.GetAlcoholTimeRemaining` (`effect.py:489`) | *"Effects.GetAlcoholTimeRemaining is declared but not built here yet: its body calls PyEffects.PyEffects.GetAlcoholTimeRemaining(), and the binding implements no such member (effects_bindings.cpp:181-183 has GetAlcoholLevel and ApplyDrunkEffect only; the stub PyEffects.pyi:41 declares it, and native tracks no alcohol time — g_alcohol_level is a bare word at effects.cpp:29). The source's member is a call on a binding member that does not exist; this port raises at the call site and names that disagreement instead of returning a wrong value."* |
| `Inventory.OpenXunlaiWindow` (`inventory.py:970`) → `PyInventory.OpenXunlaiWindow` (`native_src/item/py_inventory.py:593-600`) | *"a ported StoC path: the methods layer emulates a `DataWindow` packet (item_methods.cpp:343-349, GW::StoC::EmulatePacket)"* |
| `PyInventory.AcceptSalvageWindow` (`native_src/item/py_inventory.py:602`) | *"a ported frame-click path: the binding clicks child 6.0x62.6 of the frame labelled \"Game\" (inventory_bindings.cpp:121-125, ui::ButtonClick)"* |
| `Inventory.HandleSalvageChoiceMaterialConfirmDialog` (`inventory.py:914`) | *"Reforged's FrameTree action surface (`Frame.from_label`, `FrameId.*`, `Frame.exists`, `Frame.click`, `Frame.mouse_action`) — this port's frame layer reads frames (`py4gw/ui/frame.py`, `py4gw/ui/frame_tree.py`) and has no click path", and Reforged's coroutine driver (`ActionQueueManager`, `Routines.Yield._wait_for_empty_queue`, `Routines.Yield.wait`), which this port's execution model has no dispatcher for* (`inventory.py:98-110`) |
| `Inventory._wait_for_salvage_choice_dialog_close` (`inventory.py:948`) | the same coroutine-driver requirement |
| `Inventory.HandleSalvageChoiceDialog` (`inventory.py:951`) | the same coroutine-driver requirement |
| `UIManager.SetOpenLinks` (`ui_manager.py:773`) | *"the injected runtime's own link-opening hook: GW::ui::SetOpenLinks writes g_open_links (ui_methods.cpp:1679-1681, ui.cpp:1078), which only Native's kOpenTemplate handler consults (ui.cpp:309-324), where it blocks the message and calls ShellExecuteW"* |
| `Map.MissionMap.IsMouseOver` (`map.py:1033`) | *"PyImGui.get_io() — the injected runtime's in-process ImGui context, which this project installs nowhere and can install nowhere (Frame.is_mouse_over, FrameTree/frame.py:1430-1441)"* |
| `Map.MiniMap.IsMouseOver` (`map.py:1514`) | the same |
| `Map.MiniMap.GetLastClickCoords` (`map.py:1531`) | *"event[\"mouse_pos\"] from Frame.io_events() — UIManager.GetIOEventsForFrame, whose only producer is UIManager._UpdateFrameIOEvents reading PyImGui.get_io() (UIManager.py:74-88) … there is no client-side field behind it to read instead"* |
| `Map.MiniMap.GetLastRightClickCoords` (`map.py:1556`) | the same (`map.py:1569-1578`) |
| `Map.WorldMap.IsMouseOver` (`map.py:2038`) | the `PyImGui.get_io()` requirement |
| `Map.WorldMap.GetLastClickCoords` (`map.py:2055`) | the `event["mouse_pos"]` requirement (`map.py:2068-2077`) |
| `Map.WorldMap.GetLastRightClickCoords` (`map.py:2080`) | the same (`map.py:2093`) |
| `Map.Pathing.WorldToScreen` (`map.py:2386`) | *"PyOverlay.Overlay() and Overlay.FindZ (Map.py:2170-2175) — the injected runtime's overlay manager, which this class has no render process for"* |

For completeness, `py4gw/frame_tree/frame.py` — reachable from `UIManager`, `Map` and `Inventory` — raises in:
`set_visible:1639`, `set_disabled:1653`, `show:1668`, `set_layer:1695`, `set_opacity:1725`,
`double_click:1825`, `mouse_action:1846`, `mouse_click_action:1861`, `send_message_text:1917`,
`set_text:1972`, `draw:2240`, `draw_outline:2259`, `color_frames:2270`, `related:2401`, `item:2628`,
`tab:2641`, `io_events:2685` — and in `_FrameTree.enable:386`/`disable:393`.
`Frame.click` (`frame.py:1735`) and `Frame.send_message` (`frame.py:1867`) **are** implemented and are the
mechanism behind `UIManager.ClickDialogButton`, `UIManager.ConfirmMaxAmountDialog`,
`Inventory.AcceptSalvageMaterialsWindow`, `Party.ReturnToOutpost`, `Map.CancelEnterChallenge` and
`Map.ConfirmEnterChallenge`.

---

## 6. The three cross-cut lists

### 6.1 Every ACTION that reaches the game by calling a function **inside the client's own code**

All of these are **M1** (a typed call on the game thread through the capability layer). The resolver is the
`offsets/*.json` catalog name; the call form is the `CallForm` member. The **client's own code emits any
packet the server sees** — the library builds and sends none.

| resolver name (catalog) | call form | ACTION members that use it |
| --- | --- | --- |
| `friend_list.set_online_status_func` (`offsets/friend_list.json:65`) | `U32` | `Player.SetPlayerStatus:1068` |
| `agent.change_target_func` (`offsets/agent.json:50`) | `U32_U32` | `Player.ChangeTarget:1091`; also inside `Player.Interact`'s target path and `PySkillbar.UseSkill:869`, `PySkillbar.HeroUseSkill:922`, `Party.Heroes.UseSkill` |
| `agent.call_target_func` (`agent.json:96`) | `U32_U32` | `Player.CallTarget:1124` (enemy branch) |
| `agent.do_world_action_func` (`agent.json:90`) | `U32_U32_U32` | `Player.CallTarget:1131`, `Player.Interact:1179` |
| `agent.move_to_func` (`agent.json:84`) | `FLOAT_PTR` | `Player.Move:1200` |
| `agent.send_agent_dialog_func` (`agent.json:70`) | `U32` | `Player.SendRawDialog:1267`, `Player.SendDialog:1362` |
| `agent.send_gadget_dialog_func` (`agent.json:77`) | `U32` | `Player.SendDialog:1358` |
| `player.deposit_faction_func` (`offsets/player.json:60`) | `U32_U32_U32` | `Player.DepositFaction:1220` |
| `player.remove_active_title_func` (`player.json:52`) | `NO_ARGS` | `Player.RemoveActiveTitle:1237` |
| `player.set_active_title_func` (`player.json:45`) | `U32` | `Player.SetActiveTitle:1249` |
| `chat.send_chat_func` (`offsets/chat.json:16`) | `U32_U32` | `chat.SendChat:152`; `Player.SendChatCommand:1475`, `SendChat:1491`, `SendWhisper:1505`, `Party.Players.InvitePlayer:1400`, `Party.Players.KickPlayer:1420` |
| `party.set_difficulty_func` (`offsets/party.json:87`) | `U32` | `Party.SetHardMode`, `Party.SetNormalMode` (`party.py:254`) |
| `party.party_search_seek_func` (`party.json:93`) | `U32_U32_U32` | `Party.SearchParty:516` |
| `party.party_search_button_callback_func` (`party.json:99`) | `FASTCALL_U32` | `Party.SearchPartyCancel:1234`, `Party.SearchPartyReply:1247` |
| `party.party_window_button_callback_func` (`party.json:105`) | `FASTCALL_U32_CALLER_RELEASES` | `Party.LeaveParty:1304` |
| `party.flag_hero_agent_func` (`party.json:123`) | `U32_FLOAT_PTR` | `Party.Heroes.FlagHero:278`, `UnflagHero:314` |
| `party.flag_all_func` (`party.json:132`) | `FLOAT_PTR` | `Party.Heroes.FlagAllHeroes:331`, `UnflagAllHeroes:319` |
| `party.set_hero_behavior_func` (`party.json:150`) | `U32_U32` | `Party.Heroes.SetHeroBehavior:365`, `Party.Pets.SetPetBehavior:488` |
| `party.lock_pet_target_func` (`party.json:142`) | `U32_U32` | `Party.Pets.SetPetBehavior:481` |
| `party.command_hotkey_disable_ai_func` (`party.json:159`) | `U32_U32` | `Party.Heroes.SetSkillAIEnabled:420` |
| `item.identify_item_func` (`offsets/item.json:237`) | `U32_U32` | `Inventory.IdentifyItem`, `IdentifyFirst` (`py_inventory.py:539`) |
| `item.salvage_start_func` (`item.json:231`) | `U32_U32_U32` | `Inventory.SalvageItem`, `SalvageFirst` (`py_inventory.py:252`) |
| `item.use_item_func` (`item.json:16`) | `U32` | `Inventory.UseItem` (`py_inventory.py:501`) |
| `item.equip_item_func` (`item.json:176`) | `U32_U32` | `Inventory.EquipItem` (`py_inventory.py:520`) |
| `item.drop_item_func` (`item.json:36`) | `U32_U32` | `Inventory.DropItem` (`py_inventory.py:397`) |
| `item.destroy_item_func` (`item.json:70`) | `U32` | `Inventory.DestroyItem` (`py_inventory.py:411`) |
| `item.drop_gold_func` (`item.json:200`) | `U32` | `Inventory.DropGold` (`py_inventory.py:423`) |
| `item.change_gold_func` (`item.json:82`) | `U32_U32` | `Inventory.DepositGold`, `WithdrawGold` (`py_inventory.py:483`) |
| `item.move_item_func` (`item.json:182`) | `U32_U32_U32_U32` | `Inventory.MoveItem`, `DepositItemToStorage`, `WithdrawItemFromStorage` (`py_inventory.py:567`) |
| `merchant.transact_item_func` (`offsets/merchant.json:18`) | `STACK_WORDS` | `PyMerchant.trader_buy_item:191`, `trader_sell_item:191`, `merchant_buy_item:191`, `merchant_sell_item:191`, `crafter_buy_item:191`, `collector_buy_item:191` |
| `merchant.request_quote_func` (`merchant.json:24`) | `STACK_WORDS` | `PyMerchant.trader_request_quote:216`, `trader_request_sell_quote:216` |
| `skillbar.change_secondary_func` (`offsets/skillbar.json:53`) | `U32_U32` | `PySkillbar.ChangeHeroSecondary:802` |
| `skillbar.load_skills_func` (`skillbar.json:67`) | `STACK_WORDS` | `PySkillbar.LoadSkillTemplate`, `LoadHeroSkillTemplate` (`skillbar.py:443`) |
| `skillbar.load_attributes_func` (`skillbar.json:60`) | `STACK_WORDS` | `PySkillbar.LoadSkillTemplate`, `LoadHeroSkillTemplate` (`skillbar.py:471`) |
| `quest.set_active_quest_func` (`offsets/quest.json:56`) | `U32` | `Quest.SetActiveQuest` (`py_quest.py:483`) |
| `quest.abandon_quest_func` (`quest.json:50`) | `U32` | `Quest.AbandonQuest` (`py_quest.py:505`) |
| `quest.request_quest_info_func` (`quest.json:44`) | `U32` | `Quest.RequestQuestInfo` (`py_quest.py:572`) |
| `quest.request_quest_data_func` (`quest.json:37`) | `U32_U32` | `Quest.RequestQuestInfo` (`py_quest.py:573`) |
| `effects.drop_buff_func` (`offsets/effects.json:23`) | `U32` | `PyEffects.DropBuff`, `Effects.DropBuff` (`effect.py:232`) |
| `effects.post_process_effect_func` (`effects.json:18`) | `U32_U32` | `PyEffects.ApplyDrunkEffect`, `Effects.ApplyDrunkEffect` (`effect.py:249`) |
| `map.skip_cinematic_func` (`offsets/map.json:94`) | `NO_ARGS` | `Map.SkipCinematic` (`map_methods.py:117`) |
| `ui.draw_on_compass_func` (`offsets/ui.json:532`) | `U32_U32_U32` | `UIManager.DrawOnCompass:545` |
| `ui.load_settings_func` (`ui.json:435`) | `U32_U32` | `UIManager.LoadSettings:575` |
| `ui.set_window_visible_func` (`ui.json:474`) | `U32_U32_U32_U32` | `UIManager.SetWindowVisible:1170`; `Map.MiniMap.OpenWindow:1501`, `CloseWindow:1511` |
| `ui.set_window_position_func` (`ui.json:480`) | `U32_U32_U32_U32` | `UIManager.SetWindowPosition:1210` |
| `ui.send_ui_message_func` (`ui.json:419`) | `U32_U32_U32` and `UI_MESSAGE` | **M2 itself**, plus `UIManager.SendUIMessage:492`, `SendUIMessageRaw:517`, and every packed/raw message below |
| `ui.send_frame_ui_message_func` (`ui.json:390`) | `FASTCALL_U32_U32_U32` | `UIManager.Keydown/Keyup/Keypress:1567`, `Frame.click:1808`, `Frame.send_message` |
| `ui.get_child_frame_id_func` (`ui.json:403`) | `U32_U32` | `Party.ReturnToOutpost` (`frame.py:2361`), `_button_action_frame_id:1506` |
| `ui.create_hash_from_wchar_func` (`ui.json:397`) | `U32_U32` | `_hash_for_label:1530` (used by `Keydown`/`Keyup` and `Frame.child_named`) |
| additionally, **CAPABILITY** queries that are calls but change nothing | | `ui.validate_async_decode_str_func` (`U32_U32_U32`) for every decode; `ui.get_number_preference_func` / `ui.get_flag_preference_func` / `ui.get_enum_preference_func` / `ui.get_string_preference_func` (`ui/preferences.py:65-72`, calls at `:206`, `:291`, `:309`, `:330`); `pathing.find_path_func` (`STACK_WORDS`) via `PathPlanner._find:787`; `memory.gw_version_func`, `memory.mem_alloc_helper_func`, `memory.mem_realloc_helper_func`, `memory.mem_free_func` (`memory/memory_manager.py:81-84`, calls at `:169`, `:185`, `:198`, `:212`) |

**Messages (M2), not calls-to-functions**, are a distinct sub-list: `UIMessage.kTravel`,
`kGuildHall`, `kLeaveGuildHall`, `kSendEnterMission`, `kLogout`, `kCheckUIState`
(`native_src/methods/map_methods.py:141`, `:185`, `:191`, `:197`, `:207`, `:2275`),
`kSendInteractItem` and `kPreStartSalvage` (`py_inventory.py:381`, `:251`),
`kWriteToChatLog` (`chat.py:321`), and everything `UIManager.SendUIMessage`/`SendUIMessageRaw` is handed.

### 6.2 Every ACTION that reaches the game by writing memory

There are **two different things** this phrase can mean, and only one of them is a host-side write.

**(a) A host-side write into the client's own memory — M5, the byte patch.** Two ACTIONS:

| ACTION | what is written |
| --- | --- |
| `Camera.SetCameraUnlock(unlock)` (`camera.py:481`) | `EB 0C` or `EB 0F` over `camera.camera_update_patch_addr`, after reading the client's own bytes as the backup; disabled by putting them back (`camera.py:203-241`) |
| `Camera.SetFog(fog)` (`camera.py:601`) | `00` over `camera.fog_patch_addr`, same backup/restore shape (`camera.py:57`, `:224`, `:239-241`) |

Both go through `Patcher.patch`/`Patcher.restore` (`patcher.py:116-171`), which suspends the client's threads
and refuses if any EIP is inside the window (`patcher.py:126-146`, `:238-258`). Anything else a host-side
write touches at connect time is **CAPABILITY**, not an ACTION: the four entry patches (`hooker.py:772-776`)
and the repair of a stale patch (`client.py:714`, `:732`).

**(b) A write performed *inside* the client by the payload — M4 (`Operation.WRITE_MEMORY`).** The host
writes only into the block; the write into game memory happens on the game thread inside the hooked function
(`shared_block.py:301-307`). Actions using it:

| ACTION | target |
| --- | --- |
| `Camera.SetYaw:455-456`, `SetPitch:466`, `SetMaxDistance:472`, `SetFieldOfView:478`, `ForwardMovement:511`, `VerticalMovement:518`, `SideMovement:536`, `RotateMovement` (via `SetYaw` + `:562`), `UpdateCameraPos:586`, `SetCameraPosition:592`, `SetLookAtTarget:598` | fields of the live camera record, at `CameraStruct.<field>.offset` (`camera.py:139`) |
| `UIManager.SetKeyMappings(mappings)` (`:1012`) | up to `0x75` words of the client's own key-remap table (`ui_manager.py:1038-1046`) |
| `UIManager.SetFPSLimit(limit)` (`:830`) | the client's command-line FPS word (`ui/preferences.py:337-368`) |
| `MapMethods.TravelGH(key=…)` (`map_methods.py:168-182`) | the client's own `GuildContext.player_gh_key`. **Not reachable from `Map.TravelGH`**, which passes no key (`map.py:898-901`) |

**(c) Host writes into memory the library itself allocated inside the client** — all **CAPABILITY**: the
block and its queues (`bridge.py:1014`, `:784-790`), the call table (`client.py:1266-1269`), the watch list
(`client.py:1080`, `:1093`), the data region (`bridge.py:1052-1057`), decode slots
(`bridge.py:1099-1102`, `:1135-1141`, `:1184-1185`), the dispatcher and stubs (`bridge.py:441-454`,
`:469-476`, `:516-523`, `:550-555`), the packet stubs (`packets.py:345-466`).

### 6.3 Every ACTION implemented by a UI/frame message rather than a call to a named function

Both are still *executed by the client's own sender* through M1; what distinguishes them is that the thing
called is the **message dispatcher**, and the client's handlers decide what happens.

**Packed / raw UI messages (`ui.send_ui_message_func`):**

| ACTION | message |
| --- | --- |
| `Map.Travel`, `TravelToDistrict`, `TravelToRegion` (`map.py:816`, `:825`, `:884`) | `kTravel` (raw, `wparam` = the four-word record's address) |
| `Map.TravelGH` (`:895`) | `kGuildHall` (raw, `wparam` = the address of the client's own GH key) |
| `Map.LeaveGH` (`:904`) | `kLeaveGuildHall` (packed, `[0]`) |
| `Map.EnterChallenge` (`:913`) | `kSendEnterMission` (packed, `[0]`) |
| `Map.Pregame.LogoutToCharacterSelect` (`:2282`) | `kLogout` (packed, `[0, 0]`) |
| `Map.Pregame.InCharacterSelectScreen` (`:2249`) | `kCheckUIState` (raw; `lparam` names a word in the block the client fills) |
| `Inventory.PickUpItem` (`:989`) | `kSendInteractItem` (packed, `{item.agent_id, call_target}`) |
| `Inventory.SalvageItem` / `SalvageFirst` (`:376`, `:383`) | `kPreStartSalvage` (packed, `{item_id, kit_id}`) — **and then** a call to `item.salvage_start_func` |
| `chat.WriteChatEnc`, `chat.SendFakeChat`, `chat.SendFakeChatColored`, `Player.SendFakeChat`, `Player.SendFakeChatColored` (`chat.py:321`) | `kWriteToChatLog` (packed, `{channel, message_address}`) |
| `UIManager.SendUIMessage` (`:453`) | any `msgid` with a sixteen-word payload built in the block |
| `UIManager.SendUIMessageRaw` (`:496`) | any `msgid` with the caller's two raw words |

**Frame messages (`ui.send_frame_ui_message_func`):**

| ACTION | what is sent |
| --- | --- |
| `UIManager.Keydown:1049`, `Keyup:1067`, `Keypress:1074`; `Hero.FlagHero:696`; `PySkillbar.UseSkill:871`, `UseSkillTargetless:890`, `HeroUseSkill:924`; `Party.Heroes.UseSkill:611`; `Map.MissionMap.OpenWindow:1013-1014`, `CloseWindow:1029-1030`; `Map.WorldMap.OpenWindow:2019-2020`, `CloseWindow:2034-2035` | a one-word `packet::KeyAction` sent to a frame's callbacks as `kKeyDown` (0x20) / `kKeyUp` (0x22) (`ui_manager.py:1539-1575`) |
| `UIManager.ClickDialogButton:1331`, `ConfirmMaxAmountDialog:1421`; `Inventory.AcceptSalvageMaterialsWindow:407`; `Party.ReturnToOutpost:1262`; `Map.CancelEnterChallenge:922`, `ConfirmEnterChallenge:935` | a `packet::MouseAction` (`MouseUp`) sent to the **parent** frame as `kMouseClick2` (`frame.py:1735-1817`) |

---

## 7. What the library CANNOT do

Stated from the **absence of members and from members that raise** — not from speculation.

1. **It cannot send anything to the server itself.** No socket, no ToS/StoC packet builder, no send hook
   exists in `py4gw/` (§1). Every server-visible effect comes from a client function the library called.
   The one packet *emulation* the sources use (`GW::StoC::EmulatePacket` for `DataWindow`, which is how
   `OpenXunlaiWindow` works in the sources) is **not implemented** and raises
   (`native_src/item/py_inventory.py:596-600`).
2. **It cannot synthesise input.** No `SendInput`/`keybd_event`/`mouse_event` and no window message to the
   game window. "Pressing a key" is a frame message to the client's own callbacks (§6.3). There is therefore
   no way to hold a key for a duration: `Map.MissionMap.OpenWindow` records that the tree's 75 ms hold
   between down and up "has no home here and is not stood in for" (`map.py:1003-1006`).
3. **It cannot inject a DLL.** No module is loaded; code is placed as raw bytes and executed in place
   (`win32/write_access.py:189-249`). It also cannot **replace** another runtime: where Reforged's MinHook
   entry jump is found, the library patches **on top of it** and relocates it into its own trampoline
   (`client.py:654-707`, `hooker.py:317-357`), and it refuses a patch it cannot identify
   (`client.py:813-844`).
4. **It cannot run anything per frame.** There is no frame loop and no callback registry inside the client;
   `Hooker.enable`/`disable` only gate a stub the client calls (`hooker.py:795-809`). Consequently
   `Agent.enable` (per-frame cache invalidation) raises, and nothing refreshes a cached read.
5. **It cannot click a frame that is not created, cannot `set_visible`/`set_disabled`/`set_layer`/
   `set_opacity`/`set_text`, cannot double-click, and cannot send a mouse action at an arbitrary state**: those
   `Frame` members raise (§5). What *is* implemented is `Frame.click` and `Frame.send_message`.
6. **It cannot read the client's ImGui I/O.** `Map.MissionMap.IsMouseOver`, `Map.MiniMap.IsMouseOver`,
   `Map.WorldMap.IsMouseOver`, `MiniMap/WorldMap.GetLastClickCoords`, `GetLastRightClickCoords` and
   `UIManager.GetIOEventsForFrame`'s producer all raise on `PyImGui.get_io()` (§5).
7. **It cannot project to screen through the overlay.** `Map.Pathing.WorldToScreen` raises on
   `PyOverlay.Overlay()` / `Overlay.FindZ` (`map.py:2386-2401`).
8. **It cannot answer the alcohol level or the alcohol time remaining.** `Effects.GetAlcoholLevel` raises
   because the second event shape its observer needs does not exist; `Effects.GetAlcoholTimeRemaining` raises
   because the binding it ports declares no such member (`effect.py:254-288`, `:489-509`).
9. **It cannot read a dialog's text from the catalog's loader.** `_queue_dialog_text_decode` raises before
   its call, so `Dialog.get_dialog_text_decoded` cannot reach the client today (`dialog.py:855-874`).
10. **It cannot emulate the StoC `DataWindow` packet**, so `Inventory.OpenXunlaiWindow` raises; and it cannot
    click the salvage-window acceptor through the binding — `PyInventory.AcceptSalvageWindow` raises
    (`py_inventory.py:596-609`).
11. **It cannot drive Reforged's coroutine/queue model**, so the two salvage-choice generators raise
    (`inventory.py:914-965`).
12. **It cannot ready the party or respond to a party request as the sources declare those members**:
    `Party.SetTicked` and `Party.RespondToPartyRequest` have empty bodies because the source's own bodies
    reach no client state (`party.py:1159-1171`, `:1252-1259`), and nothing in `Party.py` reaches
    `party.set_ready_status_func` (`party.py:1168-1170`).
13. **It cannot drive state through the *event* hooks.** `py4gw/game_thread/callbacks.py:3-7` states it
    plainly: a handler "is given a record the payload wrote **after the fact**, so they observe and nothing
    more". Callbacks cannot modify or block what the client was about to do.
14. **It cannot replace the sources' in-process artefacts**: `Player.player_instance`, `Party.party_instance`,
    `Dialog._call_native_dialog_method` and `Agent.GetProfessionsTexturePaths` all raise (§5).
15. **No ACTION is a no-op by accident.** The four members in §4.2b are no-ops **because their source bodies
    are**; they are named here rather than counted as capability.

---

## 8. Counts

**ACTION members** (changing game state or the client's own execution/thread state), by module. Both a
Reforged façade member and the Native binding member it calls are counted, because both are public members of
public classes; the duplicate pairs are named in the same row.

| module | ACTION members | of which façade/binding duplicates |
| --- | --- | --- |
| `player.py` — `Player` | 18 | — |
| `party.py` — `Hero`, `Party`, `Players`, `Heroes`, `Henchmen`, `Pets` | 25 | — |
| `map.py` — `Map`, `MissionMap`, `MiniMap`, `WorldMap`, `Pregame` | 17 | — |
| `camera.py` — `Camera` | 13 | — |
| `effect.py` — `Effects`, `PyEffects` | 4 | 2 (`Effects.DropBuff`↔`PyEffects.DropBuff`; `Effects.ApplyDrunkEffect`↔`PyEffects.ApplyDrunkEffect`) |
| `inventory.py` — `Inventory` | 16 | 11 with `PyInventory` |
| `native_src/item/py_inventory.py` — `PyInventory` | 11 | (the other half of the 11) |
| `merchant.py` — `PyMerchant`, `Trading` | 16 | 8 (`Trading.*`↔`PyMerchant.*`) |
| `skillbar.py` — `PySkillbar`, `SkillBar` | 12 | 6 (`SkillBar.*`↔`PySkillbar.*`) |
| `quest.py` — `Quest` (over `PyQuest`) | 3 | 3 with `PyQuest` |
| `ui_manager.py` — `UIManager` | 17 | — |
| `native_src/chat/chat.py` | 5 | — |
| `client.py` — `ConnectedClient.resume_suspended_threads` (client thread state) | 1 | — |
| **total** | **158** | **30 duplicates → 128 distinct action implementations** |

Of the 158: **2 use M5** (a host-side code patch — `Camera.SetCameraUnlock`, `Camera.SetFog`);
**14 use M4** (a write performed inside the client by the payload); **18 have an M2 UI message as their
primary mechanism**; **21 have an M3 frame message as their primary mechanism** (several of those also make
an M1 target change alongside — e.g. `PySkillbar.HeroUseSkill`); **every one of the 158 reaches a client
entry point through M1**, and a UI/frame message is itself dispatched by an M1 call to
`ui.send_ui_message_func` / `ui.send_frame_ui_message_func`.

The numbered rows in §4 are **146** members: the 11 `PyInventory` binding actions (§4.6) and
`ConnectedClient.resume_suspended_threads` (§2.2) are counted in this table but are described in prose
rather than as numbered rows, which is the 146 + 12 = 158.

**CAPABILITY members, by module.** `client.py` 13 (`__init__`, `close`, `callbacks`, `bridge`, `access`,
`watch`, `unwatch`, `call_function`, `call_address`, `send_ui_message`, `send_ui_message_raw`, `connect`,
`disconnect`); `game_thread/bridge.py` 26 (+ 19 reporting properties); `game_thread/hooker.py` 8;
`game_thread/patcher.py` 5; `game_thread/callbacks.py` 11; `game_thread/packets.py` 6;
`game_thread/payload.py` 9 builders; `game_thread/shared_block.py` 6 enums + 4 records + 2 helper types and
21 module functions (the layer's vocabulary — no game reach); `listeners.py` `Initialize:360`, `Shutdown:369`,
`MerchantListener.Install:300`, `Uninstall:324`; `ui/async_decode.py` 5; `dialog.py` 3
(`initialize`, `terminate`, `clear_cache`); `agent.py` 3 (`GetNameByID`, `RequestName`, `IsNameReady`);
`item.py` 4 (`PyItem.RequestName`, `PyItem.IsItemNameReady`, `Item.RequestName`, `Item.IsNameReady`);
`quest.py`/`py_quest.py` 10 request members; `ui_manager.py` 7 typed-call queries
(`AsyncDecodeStr`, `GetTextLanguage`, `GetEnumPreference`, `GetIntPreference`, `GetStringPreference`,
`GetBoolPreference`, `GetFPSLimit`); `pathing.py` 2 (`PathPlanner.plan`,
`compute_immediate`); `memory/memory_manager.py` 4 (`GetGWVersion`, `MemAlloc`, `MemRealloc`, `MemFree` —
allocator state, not game state); `win32/write_access.py` 12 transport calls.

**Members that raise `NotImplementedError`:** 20 rows in §5 (19 public members plus the private helper
`Inventory._wait_for_salvage_choice_dialog_close`), plus 17 in
`py4gw/frame_tree/frame.py`, which `UIManager`, `Map` and `Inventory` reach.

**Members declared as actions with no game reach:** 4 (§4.2b) + `UIManager.FindDialogOffset` = 5.

---

## 9. Summary — how many ACTION members, and the headline mechanisms

* **158 ACTION members** (128 distinct action implementations after removing the 30 façade/binding pairs).
* **Mechanisms, in one line each:**
  * **M1 — a typed call on the game thread through the capability layer** (`connected.call_function` /
    `call_address` → `Bridge.publish_call` → the emitted dispatcher → the client's own function). This is
    the mechanism for **every** action that reaches a named client function: 49 distinct resolver names from
    `offsets/*.json`, listed in §6.1.
  * **M2 — the client's own UI-message sender** (`ui.send_ui_message_func`), packed or raw: 18 members, for
    travel, guild hall, leave-guild-hall, enter-mission, logout, `kCheckUIState`, item pickup, salvage start,
    chat-log lines, and every `UIManager.SendUIMessage*` caller.
  * **M3 — a frame message** (`ui.send_frame_ui_message_func`, a `__thiscall`): 21 members, as key actions
    (`kKeyDown`/`kKeyUp`) or as a `MouseAction` click sent to a button's parent frame.
  * **M4 — `Operation.WRITE_MEMORY`**, a write the **payload performs inside the client** on the hooked
    function's thread: 14 members (11 camera setters/movers, `SetKeyMappings`, `SetFPSLimit`, and the
    unreached `TravelGH(key=…)`).
  * **M5 — a host-side byte patch** through `Patcher` (suspend, verify, write, restore protection): 2 members
    (`Camera.SetCameraUnlock`, `Camera.SetFog`), plus the capability layer's own four entry hooks.
* **No ACTION sends a packet to the server.** Not one. The library has no socket and no packet builder; when
  a row says *client sends*, it is the client's own function that emits the client's own packet. The single
  packet-emulation the sources use is unimplemented and raises (`py_inventory.py:596-600`).
* **Connecting is a write, and it is not an action.** `py4gw.connect()` installs four entry hooks, a shared
  block, a call table, a dispatcher, a decoder stub, an observer, a capture, a listener thread and five
  replaced StoC packet-handler entries (`client.py:435-594`), and `disconnect()` puts all of it back
  (`client.py:1786-1870`). `game_thread=False` is the read-only connection.
