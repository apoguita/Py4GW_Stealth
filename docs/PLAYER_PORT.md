# Player port

`py4gw/player.py` ports Reforged's `Py4GWCoreLib/Player.py`. Every member keeps
its Reforged name and signature, so `Player.GetLevel()` means the same thing
after switching libraries. What differs is which members can produce a value, and
which can act.

| | Count |
| --- | ---: |
| Reforged members | 71 |
| ... that read a value | 51 |
| ... that act on the game | 18 |
| ... that raise `NotImplementedError` | 2 |
| Stealth-only additions | 3 public, from native `PyPlayer` (see below), and 8 private helpers |
| Reforged members renamed | 1 (`_hwnd_account_fallback` → `_account_fallback`) |
| Members that write to `Gw.exe` | **0** — the action members call the client's own functions through `py4gw/game_thread`, which is the layer that patches |

`Player` is a namespace of static methods, as in Reforged. It resolves the
selected client through `py4gw.client.current_client`, the same way the context
readers do, so `py4gw.connect(...)` must run first. Implemented members return
Reforged's own defaults when a context is unavailable; a member called with *no*
client raises `RuntimeError`, because that is a usage error rather than a game
state.

## The four groups

**Reads (51).** The value comes from a game context this project can read, or from a
capture the connection keeps from the client's own messages. Each member's docstring
names its source.

**Actions (18).** The member changes the game, and does it by calling the client's
own function on the client's own thread through `py4gw/game_thread`. These need a
connection carrying the capability layer, which `py4gw.connect()` installs by
default; on a read-only connection (`game_thread=False`) they raise that
connection's own error. They never raise `NotImplementedError` — the mechanism
they need exists. Each one's docstring names the exact function, its source
declaration, and its source line. Listed in full below.

**Still to port (2).** The value lives inside Reforged's runtime rather than in
this process, or the mechanism that would carry the action is not built yet. These raise
`NotImplementedError` naming the missing mechanism
and the member, so a ported script fails at the call site instead of silently
receiving a wrong value. They are present, not omitted, which is the point: a
`hasattr` check passes and the failure is attributable.

**Adapted.** Reachable, but by a different route than Reforged uses. Listed in
full below.

## Action members

Eighteen members act. The rule that decides *what* each one calls was established by
the live target work and is recorded in [`RESEARCH.md`](RESEARCH.md): a Native
action is two things — the `kSend*` message the runtime broadcasts and the
function the runtime calls in response — and only the second is ours to make. The
runtime's handler is the authority for which function that is, and its argument
order comes from the packet the sender filled.

| Member | Calls | Form | Source of the pairing |
| --- | --- | --- | --- |
| `ChangeTarget(agent_id)` | `agent.change_target_func(agent_id, 0)` | `U32_U32` | `kSendChangeTarget` carries `{target_id, auto_target_id}` (`agent.cpp:94-95`) and the handler passes both to `ChangeTargetFn` (`agent.cpp:143-155`, `agent_methods.cpp:19`) |
| `CallTarget(agent_id)` | `agent.call_target_func(0xA, agent_id)` for an enemy, else `agent.do_world_action_func(1, agent_id, 1)` | `U32_U32` / `U32_U32_U32` | `agent_methods.cpp:202-229` picks the branch; the handlers pass the packet fields through (`agent.cpp:166-183`) |
| `Interact(agent_id, call_target)` | `agent.do_world_action_func(action_id, agent_id, call_target)`, after `CallTarget` when asked | `U32_U32_U32` | `agent_methods.cpp:157-189`, `PlayerMethods.py:114-154` |
| `Move(x, y, zPlane)` | `agent.move_to_func(&[x, y, float(zplane), 0.0])` | `FLOAT_PTR` | `MoveToFn` is `void __cdecl(float*)` (`agent_methods.cpp:21`, `149-153`) |
| `DepositFaction(faction_id)` | `player.deposit_faction_func(0, faction_id, 5000)` | `U32_U32_U32` | `player_methods.cpp:199-205`; the leading `0` and the `5000` are the source's |
| `SetActiveTitle(title_id)` | `player.set_active_title_func(title_id)` | `U32` | `SetActiveTitleFn` (`player_methods.cpp:40`, `74-80`) |
| `RemoveActiveTitle()` | `player.remove_active_title_func()` | `NO_ARGS` | `RemoveActiveTitleFn` is `void __cdecl(void)` (`player_methods.cpp:39`, `82-88`) |
| `SendRawDialog(dialog_id)` | `agent.send_agent_dialog_func(dialog_id)` | `U32` | `SendDialogFn` is `void __cdecl(uint32_t)` (`agent_methods.cpp:18`); the handler hands `wparam` through as that argument (`agent.cpp:138-141`) |
| `SendDialog(dialog_id)` | `agent.send_gadget_dialog_func(dialog_id)` when the dialog's agent is a gadget, otherwise `agent.send_agent_dialog_func(dialog_id)` | `U32` | `agent_methods.cpp:28-37` picks the sender from `g_dialog_agent_id`; the two handlers pass `wparam` through (`agent.cpp:138-159`) |
| `SendAutomaticDialog(button_number)` | `SendDialog`'s two senders, with the id of the button at that position | `U32` | `Player.py:854-900` reads the open dialog's buttons through `Dialog.get_active_dialog_buttons()`, keeps the ones that carry a dialog id, and sends the selected one's id through `SendDialog`; the sender choice is `agent_methods.cpp:28-37` |
| `SetPlayerStatus(status)` | `friend_list.set_online_status_func(status)` | `U32` | `PyPlayer::SetPlayerStatus` ends at `SetFriendListStatus` (`player_bindings.cpp:338`), which calls `SetOnlineStatusFn` (`friend_list_methods.cpp:13`, `121-127`) |
| `SendChatCommand(command)` | `chat.SendChat("/", command)` | `U32_U32` | `PyPlayer::SendChatCommand` is `GW::chat::SendChat('/', msg.c_str())` (`player_bindings.cpp:327`); the port is the port of `GW::chat`'s sender (`chat_methods.cpp:88-113`) |
| `SendChat(channel, message)` | `chat.SendChat(channel, message)` | `U32_U32` | `PyPlayer::SendChat` (`player_bindings.cpp:328`) → the same sender |
| `SendWhisper(name, message)` | `chat.SendChat(name, message)` | `U32_U32` | `PyPlayer::SendWhisper` (`player_bindings.cpp:329`) → the whisper overload, `L"\"%s,%s"` (`chat_methods.cpp:115-127`) |
| `SendFakeChat(channel, message)` | `chat.SendFakeChat(channel, message)` | `UI_MESSAGE` | `PyPlayer::SendFakeChat` (`player_bindings.cpp:330`) → `GW::chat::SendFakeChat` → `WriteChat` → `kWriteToChatLog` (`chat_methods.cpp:156-202`, `262-267`) |
| `SendFakeChatColored(channel, message, r, g, b)` | `chat.SendFakeChatColored(...)` | `UI_MESSAGE` | the same write, after `FormatChatMessage` (`chat_methods.cpp:269-275`) |
| `BuySkill(skill_id)` | `Utils.SkillIdToDialogId(skill_id)` then `Player.SendRawDialog` | `U32` | `Player.py:816-822` → `PlayerMethods.SendSkillTrainerDialog` (`native_src/methods/PlayerMethods.py:426-436`) → `PlayerMethods.SendRawDialog` → `UIManager.SendUIMessageRaw(kSendAgentDialog, dialog_id, 0)`; the port calls the function that handler reaches, exactly as `SendRawDialog` does |
| `UnlockBalthazarSkill(skill_id, use_pvp_remap)` | `Utils.BalthazarSkillIdToDialogId(...)` then `Player.SendRawDialog` | `U32` | `Player.py:824-831` → `PlayerMethods.SendBalthazarSkillUnlockDialog` (`PlayerMethods.py:438-450`). Both halves are ported: the conversion's PvP remap reads the skill constant record through `Skill.ExtraData.GetIDPvP` (`py4gw/skill.py`, [`SKILL_PORT.md`](SKILL_PORT.md)) and the send is the same ported `SendRawDialog` |

Every function in that table is resolved from this project's own `offsets/`
catalog by the name in the first column of the second — no address is written
down here, and the dispatcher rejects a target outside the client's module before
it calls anything.

### Two boundary differences, recorded

**The message is not sent.** Reforged's own path *sends* `kSendChangeTarget` and
its runtime handler makes the call. Stealth calls the function directly and sends
no message, so another in-client observer of that message would not see it. In a
client with no Reforged runtime the message has no listener at all — that was
measured, not assumed: sending it changed nothing, and calling the function moved
the target ([`RESEARCH.md`](RESEARCH.md)).

**Resolution failure raises.** The sources resolve their function pointers at
startup and an action silently does nothing when the resolve failed. This project
resolves on first use, and a resolver that does not match the build raises
`RuntimeError` naming the resolver instead. That is a divergence in the loud
direction: it cannot produce a wrong value, and it cannot be mistaken for the game
declining the action.

### The first capture: which agent a dialog belongs to

Nine of the eighteen actions need nothing from the client except the function to call.
`SendDialog` needs one thing more: **which agent the open dialog belongs to**,
because the source sends the gadget dialog or the agent dialog depending on it.

Reforged's runtime keeps that in `g_dialog_agent_id`, a variable its own handler for
the client's `kDialogBody` message sets (`agent.cpp:133-137`). Stealth keeps the same
value the same way — the observer records that message, and the handler the connection
registers in `py4gw/dialog.py` stores the packet's second word in that module's state,
where `Dialog` reads it. `Player.SendDialog` reads the same value and picks the sender
exactly as `agent_methods.cpp:28-37` does, including the case where the id no longer
resolves: then nothing is sent, because the source returns without sending.

**This is the callback layer's first consumer.** The mechanism — a hook, an event
region, a registry keyed by event kind, a listener — was built and live-verified with
nothing using it; the first ported member that needed captured state is what changed
that. It is also the shape the **31 `enable()` members still to port** want: one per
context, each waiting for a value its source's callback publishes. Those are the next
consumers, not a new mechanism.

**Verified live** (pid 20192, `tests/probe_dialog_surface.py`, read-only): the
operator talked to an npc, the client reported a dialog body naming agent `17`, and
`client.dialog_agent_id` read `17` from the same message. The same run measured the
dialog's text pointer, which is what the next section is about.

One thing to keep in mind when reading it: the capture is only as fresh as the last
dialog message the client sent. With no dialog open it holds `0`, and a response sent
then is not sent at all — which is the source's behaviour too, not a fallback.

### The second capture: the player's target, and the first captured **read**

`Player.GetTargetID` had the same gap `SendDialog` did, and is now ported
the same way. Native `GetTargetId()` returns `g_current_target_id`
(`agent_methods.cpp:65-67`), which the runtime's `kChangeTarget` handler sets from the
client's notice of the change (`agent.cpp:161-165`); the client keeps that value
nowhere a reader can reach, because `ChangeTargetUIMsg` is a message payload and no
context holds it. So the connection watches that message too, keeps the packet's first
word, and `client.target_id` reports it.

This is the shape that matters for the rest of the port, and it is a *different* shape
from the dialog one:

| | `SendDialog` | `GetTargetID` |
| --- | --- | --- |
| the capture feeds | an **action** — it picks which sender to call | a **read** — it is the value the member returns |
| freshness | must be read while the dialog is open | the last target the client announced |

Both are one watch entry, one handler, and one property on the connection. The **31
`enable()` members still to port are the read case**: each wants a pointer its source's
callback publishes, which the same pattern provides. That is why this member was taken
next — not because it was the most valuable on its own, but because it is the cheapest
complete instance of the shape the largest remaining block needs.

**Verified live** (pid 20192, `tests/test_live_player.py`): the client announced target
`16`, `Player.GetTargetID()` read `16` from that notice, and after the target was
cleared it read `0`. The same message is what the older live observation reads, so two
runs now agree about which word carries the id.

The read-only resolver recorded in `offsets/gwau3_leads.json` (the client's own
current-target global at `0x0129A174`, confirmed differentially) stays unused: it was
the route that proved the value exists, and the capture is the route the source
actually takes.

### Dialog text is encoded, and decoding is a callback

`DialogBodyInfo.message_enc` is a pointer to the dialog's text **in the client**. The
obvious hope was that it is plain UTF-16 with marker code points mixed in, in which
case a bounded read would do and no decode call would be needed. **It is not.** Read
live at that pointer, the first bytes are:

```text
03 81 66 0a a8 da 48 a9 63 33 02 00 02 01 02 00   (and on, in the same shape)
```

That is encoded data, not text with markers. So the client's own decoder is
required, and its ABI says what that costs:

```cpp
using ValidateAsyncDecodeStrFn = void(__cdecl*)(const wchar_t* value,
                                                DecodeStr_Callback callback,
                                                void* wparam);
using DoAsyncDecodeStrFn = uint32_t(__fastcall*)(void* ecx, void* edx,
                                                 wchar_t* encoded_str,
                                                 DecodeStr_Callback callback,
                                                 void* wparam);
```

Native wraps it as `AsyncDecodeStr(enc_str, buffer, size)`, which allocates a small
struct holding the destination and passes `CallbackCopyChar` plus that struct as the
callback and `wparam`. **So decoding means handing the client a function of ours to
call**, and that is the same shape as everything else in `py4gw/game_thread`: emit a
callback stub into the client, have it copy the decoded text into an area of our
block, wait on a counter, read the text out. Both functions are already resolvable
from this project's catalog (`ui.async_decode_string_func`,
`ui.validate_async_decode_str_func`), so the missing piece is the stub and the text
area, not the search.

That is the piece that leaves `Dialog`'s text and button labels, `Player.GetChatHistory`,
`IsChatHistoryReady` and `RequestChatHistory`, the party names for arbitrary agents,
and `Player.get_player_name` — all of them for the same reason. Sending strings the
other way (`Player.SendChat` and friends) needs the reverse of the same area: a place
to put a string the client reads.

### Guards
The source's checks are copied per member, in the source's order:

- `ChangeTarget` applies `PyPlayer::ChangeTarget`'s own guard first — a zero id or
  an id that resolves to no agent changes nothing (`player_bindings.cpp:237-239`).
  The runtime's handler applies a second, weaker guard before calling
  (`ManagerCanFindAgent`, `agent.cpp:146-151`); `Player.IsAgentIDValid` is the
  stricter native spelling of the same question, so using it can only reject more.
- `CallTarget` requires a nonzero id that resolves to an agent **with a living
  record** before it does anything (`player_bindings.cpp:256-267`).
- `Interact` requires a nonzero id that resolves to an agent, and returns without
  acting when a living agent has no living record (`agent_methods.cpp:157-176`).
- `SetPlayerStatus` validates the status before calling, exactly as Reforged's
  Python does, and reports `False` for a value that is not a `PlayerStatus`.

## Adaptations

| Member | Reforged | This port | Why |
| --- | --- | --- | --- |
| `_hwnd_account_fallback` | builds `<hwnd>@Py4GW` from `PySystem.Console.get_gw_window_handle()` | renamed `_account_fallback`, builds `<pid>@Py4GW` | `py4gw.win32.Win32` does not enumerate windows. Both identifiers are stable and unique per client, and the value only stands in for an unreadable email. |
| `GetName` | `Agent.GetNameByID` → native binding reading the encoded agent name | reads `CharContext.player_name_str` | The character context already carries the same name as a plain field, so no binding is needed. |
| `IsPlayerLoaded` | map gate, then a party lookup, then a fallback tail with `Agent.GetInstanceUptime(agent_id) > 750` | the native version: map gate, then the party lookup, then `False` | Native `GetIsPlayerLoaded` (`player_bindings.cpp:30`) has **no** warm-up tail and returns `False` when no party member matches. See the provenance analysis below. |
| `GetMorale`, `GetExperience`, `GetLevel`, `GetSkillPointData`, the four faction readers | `max(field, field_dupe)` | the native `PickHighest(field, field_dupe)` | Not equivalent. See below. |
| `GetInstanceUptime` | `agent.timer / GetFPSLimit() * 1000` | **not yet ported** | Reforged's body delegates: `Agent.GetInstanceUptime(Player.GetAgentID())` (`Player.py:322-329`) is `int(agent.timer / max(UIManager.GetFPSLimit(), 30) * 1000)` (`Agent.py:281-294`), so the dependency is the **Agent class**, which is not ported, and behind it `UIManager.GetFPSLimit` → `GW::ui::GetFrameLimit` (`ui_methods.cpp:1833-1858`), which is not ported either. **The call vocabulary is not a blocker and this row used to say it was** — a completed call carries the callee's return register in the command's `value` (`test_the_returned_value_lands_in_the_command`). |
| `_last_xy` | one class attribute shared by every caller | dict keyed by client pid | A single attribute would let two connected clients share a fallback position, which this project forbids for anything identity-derived. |
| `GetKurzickData` and the three other faction readers | returns a `list` on the failure path and a `tuple` on success | returns a `tuple` in both cases | Reforged's own inconsistency; the declared return type is `tuple`. |
| `CallTarget` | defined twice (lines 719 and 748) with identical bodies | defined once | The second definition wins in Reforged, so behavior is unchanged. |

### `IsPlayerLoaded`: where `750` came from

It came from nowhere. `750` does not appear anywhere in
`Py4GW_Reforged_Native\src`, and in Reforged it appears only on that one line —
every other `750` in the tree is an unrelated bot delay or a gold constant.

The native version has no threshold at all (`player_bindings.cpp:30`):

```cpp
// Parity with legacy GW::PartyMgr::GetIsPlayerLoaded(-1):
// returns true if the current player is connected in the party.
static bool GetIsPlayerLoaded() {
    auto* party_ctx = GW::Context::GetPartyContext();
    if (!(party_ctx && party_ctx->player_party && party_ctx->player_party->players.valid()))
        return false;
    uint32_t player_id = GW::player::GetPlayerNumber();
    for (const auto& player : party_ctx->player_party->players) {
        if (player.login_number == player_id)
            return player.connected();
    }
    return false;
}
```

And `PyPlayer::GetContext` (`player_bindings.cpp:141`) does the map gate first,
which is the mechanism the whole readiness gate exists for:

```cpp
auto instance_type = GW::map::GetInstanceType();
bool is_map_ready = GW::map::GetIsMapLoaded() && !GW::map::GetIsObserving()
    && instance_type != GW::Constants::InstanceType::Loading;
if (!is_map_ready) { ResetContext(); return; }
```

So Reforged's Python version diverges from the native in two ways, and this port
follows the native:

1. It adds a tail — world context, agent validity, uptime — that runs **only**
   when no party member matches the player number. The native returns `False` in
   exactly that case, so the two can disagree in a real state.
2. That tail's threshold is an undocumented magic number.

The Reforged tail is also largely not taken in the normal case: the party loop
returns as soon as it finds the player, so the world/agent/uptime checks only
matter when the player is missing from the party list.

### `PickHighest` is not `max`

The client keeps several values twice and only one copy is current. Native
`PickHighest` (`player_bindings.cpp:56`) discards a field reading `0` **or**
`0xFFFFFFFF` and returns the higher of the ones that remain, falling back to `0`:

```cpp
constexpr uint32_t INVALID = std::numeric_limits<uint32_t>::max();
bool a_ok = (a != 0 && a != INVALID);
bool b_ok = (b != 0 && b != INVALID);
if (a_ok && b_ok) return (a > b) ? a : b;
```

Reforged's Python wrappers use `max(field, field_dupe)`, which differs whenever a
duplicate holds the sentinel: `max(5, 0xFFFFFFFF)` returns `0xFFFFFFFF`, while
`PickHighest(5, 0xFFFFFFFF)` returns `5`. This port uses the native rule for
`GetMorale`, `GetExperience`, `GetLevel`, `GetSkillPointData`, and all four
faction triples. The helper is `Player.player` module-level `_pick_highest`, and
`tests/test_player_offline.py` pins the sentinel cases.

## Members still to port

Two members still raise, and eighteen act. Each row names what the member is
waiting on, and none of them is waiting on "code in the client" anymore — that layer
exists. What each one actually needs is the second column.

| Member | What it needs |
| --- | --- |
| `player_instance` | **obsolete port artifact, not a work item.** Reforged reaches every value through ``Player.player_instance().X()``; that object is a ``PyPlayer`` binding the injected runtime owns in-process, and this project has no player object and needs none — every value it provided is answered by this class's own members. The member is kept only for surface parity, raises, and says exactly that. |
| `GetInstanceUptime` | the **Agent class**'s own `GetInstanceUptime` and, behind it, `UIManager.GetFPSLimit` → `GW::ui::GetFrameLimit` (`ui_methods.cpp:1833-1858`). This member's own body is a delegation to `Agent.GetInstanceUptime` (`Player.py:322-329`), so porting it alone would be porting a member of an unported class through the back door; the unit of work is `Agent`. **The value-returning call is not missing** — `CommandRecord.value` carries the callee's return register and `client.call_function` answers with it. |
| ~~`IsChatHistoryReady`, `GetChatHistory`, `RequestChatHistory`~~ | **ported 2026-09-26** — the trio is native's own statics (`g_chat_history`/`g_chat_ready`, `player_bindings.cpp:273-325`) over ``GW::chat::GetChatLog()`` (``chat_methods.cpp:70-73``, ported as :func:`py4gw.chat.GetChatLog`): the walk over the ``CHAT_LOG_LENGTH`` ring, the decode of each line through the client's own decoder, the source's shared 500 ms deadline with its 5 ms poll and its ``"[ERROR: Timeout]"`` text, and the narrow conversion that replaces every non-ASCII code unit with ``?``. Two execution-model adaptations are recorded on the member: the walk runs at the point of request (no ``std::thread``, no frame loop), and the wait is on the decode slot the emitted stub fills rather than on native's ``std::wstring``. **And one deliberate divergence, at the owner's direction**: the buffer is also kept *warm* by the connection — it watches ``kWriteToChatLog`` and decodes each announced line as it arrives (`py4gw/chat.py`, the message native's own chat module registers a callback for, ``chat.cpp:205``), so a history read after the fact does not depend on someone having called ``RequestChatHistory`` first. Native fills its buffer only on request; here the listener fills it continuously, and ``RequestChatHistory`` keeps the source's clear-and-replace behaviour when it is called. |
| ~~`BuySkill`~~ | **ported 2026-09-26** — `Utils` landed (`py4gw/py4gwcorelib_src/utils.py`, [`UTILS_PORT.md`](UTILS_PORT.md)), so the member is `Utils.SkillIdToDialogId(skill_id)` followed by the already-ported `Player.SendRawDialog`, which is `PlayerMethods.SendSkillTrainerDialog`'s whole body (`PlayerMethods.py:426-436`). |
| ~~`UnlockBalthazarSkill`~~ | **ported and complete 2026-09-26** on the same chain (`PlayerMethods.py:438-450`). Its PvP remap reads `Skill.ExtraData.GetIDPvP`, which landed with the `Skill` port (`py4gw/skill.py`, [`SKILL_PORT.md`](SKILL_PORT.md)), so the default path runs the source's conversion and then the same ported send. With nothing connected the record read is unavailable and the source's own `except Exception` branch (`Utils.py:801-807`) is what runs — recorded in [`UTILS_PORT.md`](UTILS_PORT.md). |
| ~~`SendChatCommand`, `SendChat`~~ | **ported** — `py4gw/chat.py` builds the source's buffer in the block's data region and calls `g_send_chat_func(buffer, 0)` (`chat_methods.cpp:88-113`) | **unblocked 2026-09-26**: the resolver answered mid-instruction because of *this port's* `to_function_start`, not a stale pattern — it preferred a `jmp`-shaped byte inside the instruction before the match site to the real prologue. The member is the source's again (`scanner.cpp:205-210`), the crash recovery moved to `client.py` where it is verified, and the resolver now answers `0x0082D620`: the client's chat send, decompiled to the source's `void __cdecl (wchar_t* message, uint32_t agent_id)`. What is left for these two members is a live verification, not a resolver (`docs/CHAT_PORT.md`, `docs/RESEARCH.md`). |
| ~~`SendWhisper`~~ | **ported** — the source's `SendChat(from, msg)` whisper overload, `L"\"%s,%s"` (`chat_methods.cpp:115-127`), not `StartWhisperFn` | unblocked by the same fix, and waiting on the same live verification. The row here used to name a `__fastcall` form; the binding never goes near that function. |
| ~~`SendFakeChat`, `SendFakeChatColored`~~ | **ported and live-verified 2026-09-26** — `py4gw/chat.py` carries `WriteChat`/`WriteChatEnc` (`chat_methods.cpp:156-202`): the source's wrap, the sender forms, the transient marker, and the line placed in the block's data region, sent as `kWriteToChatLog` through the client's own UI-message entry point. `FormatChatMessage`, the colour part, is ported. | `tests/probe_chat_log_write.py`, pid 46544: one line on channel 1, the client's own log **14 → 15**, the marker in it, and what the client stores is exactly the source's encoding (`U+0108 U+0107` + text + `U+0001`). One crash preceded it, diagnosed in [`CHAT_PORT.md`](CHAT_PORT.md): the port passed a *pointer to* a `UIChatMessage` where this port's UI-message form carries two payload **words** (`payload.py:645-669`), so the client read `0` as the message and asserted its own null check at `CtChatLog.cpp:765`. Nothing is sent to the server — the line goes into this client's log only. |

Two of these are one capability away rather than two: the four chat members are **unblocked** — the
resolver answers the client's real send function, verified offline and decompiled
(`tools/resolve_offline.py`) — so what they need is the live call; and the **Agent class** would take
`GetInstanceUptime`, whose body is a delegation to `Agent.GetInstanceUptime`, and the frame limit
that member needs is a call whose value the command record already carries.

The mechanisms these members are waiting on are the five catalogued in
[`WRAPPER_MIGRATION_ASSESSMENT.md`](WRAPPER_MIGRATION_ASSESSMENT.md). Four of the
five now have a ported delivery: A (a game function on the game thread) is what the
eighteen action members use, C (UI-message dispatch) has the `UI_MESSAGE` form, and E
(a memory write) is the transport the connection already holds. B (a native binding
call) is Reforged's own DLL code, so nothing in this port reaches it, and D (a frame
click) is a call whose address and ABI are still to be established. Nothing in this
module adds a write, a hook, or a payload of its own; the eighteen actions go through
the layer that already had them.

### The dialog class came with `SendAutomaticDialog`

The member needs `Dialog.get_active_dialog_buttons()`, which is not in `Player` at all —
so the class was ported with it: **`py4gw/dialog.py`**, the port of Reforged's 173-line
`Dialog.py` *and* of the state behind it in `src/GW/dialog/dialog.cpp`. The per-member
surface, the state machine and every member still to port are in
[`DIALOG_PORT.md`](DIALOG_PORT.md).

The state is the interesting half. Every value Reforged's Python returns comes from
`PyDialog`, and `PyDialog` is backed by 1,718 lines that keep dialog state by
**listening to four of the client's own UI messages**:

| message | what the runtime does, and what this port does |
| --- | --- |
| `kDialogBody` | records the agent, clears the button list, decodes the body text |
| `kDialogButton` | appends one button: icon, encoded label, dialog id, skill id |
| `kSendAgentDialog` / `kSendGadgetDialog` | records the sent dialog so the body that answers it can be tied to it |

So the connection watches the first two and hands them to the dialog module, and
`Dialog.get_active_dialog()` / `get_active_dialog_buttons()` read the module's state —
the same split the source has, with the module owning its own state rather than the
connection.

**What made this cheap is one measured fact.** The client's `DialogButtonInfo` packet
is sixteen bytes — `{button_icon, message, dialog_id, skill_id}` — so the **whole
packet fits in the four words the observer records**. The dialog id a caller sends is a
word in the event, not something to be decoded, so a member that clicks a button needed
no decoder. Verified live: the client reported agent `17` with **two buttons, ids 4484
and 6020**.

**Still to port**, now with a named mechanism rather than a guess: the dialog and
button *text*. `message_enc` is genuinely encoded (measured: the bytes are not UTF-16
with markers), and decoding means handing the client a callback of ours to invoke
(`AsyncDecodeStr`). Until that exists the text fields carry the value the runtime itself
reports while a decode is in flight — empty, with `message_decode_pending` true — and the
inline-choice fallback in `get_active_dialog_buttons()` finds nothing because the body
text it reads is empty.

One divergence in this member: the source reports each of those cases through
`PySystem.Console.Log`, which is Reforged's console *inside* the client. There is no
external equivalent, so the diagnostics are not ported yet and the returns they
accompany are.

## Agent id reader: `PlayerAgentId`

`Player.GetObservingID` needed a source. Native
`Context::GetObservingId()` returns `*g_player_agent_id_addr`, so the agent id of
the controlled (or observed) character is a game global, not DLL state.

`py4gw/context/player_agent_id_context.py` reads it, mirroring
`server_region_context.py`: the resolver `agent.player_agent_id_addr` is
scan → dereference → validate(`data`), so the resolved value is a stable `.data`
address and the id is one read away. Under the caching rule the address is
resolved once and the id is read per call.

Verified live: the resolved address is `0x017CAC10`, `read_uint32` of it is
`1153`, and `world.player_controlled_character.agent_id` is also `1153`. The
agreement between two independent routes is the evidence.

## Members taken from the native surface

Reforged's Python `Player` does not wrap everything native `PyPlayer` exposes, so
these come from `player_bindings.cpp` directly:

| Member | Native source | Notes |
| --- | --- | --- |
| `GetUnlockedMaps()` / `GetUnlockedMapsBitmap()` | `unlocked_maps` from `world->unlocked_map` | A bitmap, same encoding as missions and skills. Reforged's Python never wraps it. |
| `GetUnlockedMaps()` | `unlocked_maps` from `world->unlocked_map` | A bitmap word array. Reforged's Python `Player` never wraps it. |
| `GetMouseOverID()` | `mouse_over_id` | **Always `0`**: Native declares and exposes it but only ever resets it. |
| `IsAgentIDValid(agent_id)` | `IsAgentIDValid` | The public spelling of the lookup Reforged reaches through `Agent.GetAgentByID`. |
| `GetMouseOverID()` | `mouse_over_id` | **Always `0`.** Native declares the field and exposes it as a property, but `GetContext` only ever resets it to zero and nothing assigns it, so no live value exists in either base project. |

Also present from native: `id`/`agent` and `target_id`, both of which this port
reaches through `GetAgentID` and the captured `GetTargetID` respectively.

## Verification

- `tests/test_player.py` — **40 live tests**. Every reading member is checked
  against the context it claims to read, or against an invariant that must hold
  in a loaded map. Cross-checks cover the character context, the world context,
  the party list, the friend list, the player agent id global, and the agent
  record. The suite skips at the character-select screen. It covers no action
  member: the eighteen that act change the game, and a live action check is a
  deliberate, user-present operation rather than part of a suite — see
  `tests/test_live_player.py` below. The members it lists as still to port are the
  ones that still raise, and it must never be given an action member to assert on: a
  `Player.Move(0.0, 0.0)` inside an `assertRaises` that no longer raises walks the
  character, which is what happened when the first action members were ported.
- `tests/test_live_player.py` — **10 live tests, 9 passing** by default, elevated, in
  a map. They drive the action members through the members themselves and read the
  effect out of the client's own messages and records. The results are in
  [Live-verified](#live-verified) above, including the two library facts the run
  corrected. The tenth is the enemy branch — `ChangeTarget`, `CallTarget` and
  `Interact` on an enemy, which starts a fight — and it is fenced behind
  `PY4GW_LIVE_ENEMY=1` because that is the operator's decision and not a suite's.
- `tests/test_player_offline.py` — offline tests. They assert that every one
  of the 71 Reforged member names exists and is a `staticmethod`; that the 5
  members still to port raise `NotImplementedError` naming themselves and their
  mechanism; that the 18 action members raise the *connection's* error, never
  `NotImplementedError` (with `UnlockBalthazarSkill`'s default path pinned to raise
  from `Utils`, which is where the source makes the call it needs); that the reading
  members fail loudly without a connection; that the action and still-to-port sets are
  disjoint and together account for the 23 members that once raised; and they exercise
  the pure helpers (`PlayerStatus` coercion and display names, `FormatChatMessage`
  clamping, UUID formatting, email sanitizing).
- `tests/test_payload_offline.py` — the four forms the actions use are proved by
  executing the emitted dispatcher against a callee that records its arguments and
  the stack pointer it was entered with. One test asserts the four forms push
  exactly 0, 1, 3 and 4 words; another checks the `float*` array is
  `{x, y, (float)zplane, 0.0f}`.
- `examples/player.py` — reads every reading member live and then shows four
  members still to port raising.
- Live run, PID 29520: player number 12, login number 12, party number 0, agent
  id 1153, observing id 1153, level 20, 47 title records, 108 unlocked skills,
  status 1 (`online`), `IsTyping` false. Account flags read `0x4`, which reports
  `IsReforged() == True` — consistent with `F:\GW\GW1\Gw.exe` being the Reforged
  build.

### Live-verified

`tests/test_live_player.py` — **9 tests, elevated, 9 passing**, pid 20192
(`F:\GW\GW1\Gw.exe`, module `0x00610000 + 0xF49000`), on 2026-09-24. Each action went
through the member, and the effect was read out of the client's own reports:

| Member | What the client said |
| --- | --- |
| `ChangeTarget(agent)` | its own `kChangeTarget` notice carried the agent id back |
| `ChangeTarget(0)` | published **no call at all** — the source's guard rejected it first |
| `Move(x, y)` | the character walked (4.61 units; the +X attempt was blocked by geometry and the −X attempt worked) and returned to the starting point |
| `Interact(agent)` | **the client reported a dialog for that agent** (`kDialogBody`, agent id in the packet's second word) |
| `CallTarget(agent)` | completed on the game thread on a non-enemy, taking the world-action branch |
| `RemoveActiveTitle()` | the client's active title tier went from `182` to `0` |
| `SetActiveTitle(id)` | put tier `182` back on title `1`; switching to title `0` ("Hero") moved the client to tier `6`, and switching back moved it to `182` again |
| `SetPlayerStatus(current)` | completed and the client's own friend-list field still agreed |
| `SetPlayerStatus(9)` | published **no call at all** — the source validates before calling |

The run also asserted the rollback: both hooked functions read back as their own
bytes, and the client's whole code section hashed identically before and after
(`33984c4c...`, 5,473,792 bytes). No enemy was targeted, interacted with, or called.

**Two things this run changed in the library**, which is what live testing is for:

1. **`GetActiveTitleID` had a bug, and the live suite found it.** The port dropped
   native's `!player->active_title_tier` check (`player_methods.cpp:159-161`), so a
   tier index of `0` — which is what "no title is displayed" *is* — fell through to
   the title search and matched the first title whose tier index was also `0`,
   reporting a title the player was not displaying. `RemoveActiveTitle()` was working
   the whole time; the reader was lying about the result. Fixed to the source's own
   order, and `tests/test_player.py::test_active_title_matches_the_player_tier` was
   split on the same condition, because it had encoded the buggy behaviour.
2. **Command sequences start at zero**, which the suite's first version got wrong:
   a command's sequence is the `command_written` counter's value *before* it
   advances, so the first command through a block is sequence `0`. Both facts are
   now recorded where they belong — `Bridge.publish_call`'s docstring and the test
   helper's.

### What is still not exercised live

- **`DepositFaction`**, in full: it needs 5000 faction and an ambassador to talk to.
  The form it uses (`U32_U32_U32`) is exercised live by `CallTarget` and `Interact`.
- **The enemy branch of `CallTarget`.** A real call-target is a party broadcast, and
  the suite will not choose a party's target. Interacting with an enemy is likewise
  never done: it starts a fight.
- A live check changes game state, so it is a deliberate, user-present operation.
  The suite does not run what it cannot undo — and says so when it cannot undo something:
  an interaction that opens a dialog leaves the client with a dialog open, because
  closing it needs the Escape key and this project does not synthesise input. That is
  why the interaction test runs last.

The title check needs **a title displayed on the character**, which is the operator's
to arrange: with none, the member's own reader reports nothing to remove and the
suite skips the whole check rather than pretending. It also needs a *second* title
the character has progress in to exercise the switch; a title with a tier index of
`0` cannot stand in, because displaying it is indistinguishable from having removed
the title.

## Mission and skill progress are bitmaps

These are not one entry per mission or per skill, and reading them as such gives
nonsense. The client stores both as `Array<uint32_t>` **bitmap words**:

| Field | Words | Constant |
| --- | ---: | --- |
| `missions_completed` | 25 | `MISSION_BITMAP_ENTRIES` (`Globals.py:17`) |
| `missions_bonus` | 16 | same encoding |
| `missions_completed_hm` | 25 | same encoding |
| `missions_bonus_hm` | 16 | same encoding |
| `unlocked_character_skills` | 108 | `SKILL_BITMAP_ENTRIES` (`Globals.py:19`) |

Reforged states the encoding in its own comment — *"each entry is a bitmap of a
mission flags (32 bits each)"* — and `MissionDataStruct` declares the four
mission fields as `c_uint * MISSION_BITMAP_ENTRIES` and copies the words through
verbatim. `SharedMemory.py` imports the same constants.

**A set bit means the item is completed or unlocked; a clear bit means it is
locked.** So the live client's 25-word mission array describes up to 800 bits,
and its 108-word skill array describes up to 3456 bits with **75 bits set** —
that is 75 unlocked skills, not 108 skills.

`GetMissionsCompleted` and the three other mission members plus
`GetUnlockedCharacterSkills` keep Reforged's contract as ported, which is to
return the raw words. The bitmap is the answer to "how many", so:

```python
bitmap = Player.GetUnlockedSkillsBitmap()   # Stealth addition
bitmap.word_count      # 108
bitmap.bit_capacity    # 3456
bitmap.set_count       # 75   -> unlocked skills
bitmap.is_set(index)   # is one entry unlocked?
bitmap.set_indices()   # every unlocked index
```

The four `Get*Bitmap()` mission members plus `GetUnlockedSkillsBitmap()` are
Stealth additions, marked as such in `tests/test_player_offline.py`.

**Correction to an earlier revision of this document.** It recorded the mission
arrays as an unresolved contradiction, on the reading that Reforged indexed one
element per mission. That was wrong: `MissionDataStruct.from_context` iterates
`range(MISSION_BITMAP_ENTRIES)`, which is 25 *words*, not 25 missions. Reforged
and the client agree, and the only defect was in the test written here, which
asserted the values were `0`/`1`.

## Limits

- `GetXY` keeps the last good position per client, which is retained mutable
  state. It is a documented anti-glitch fallback rather than a cache of live data:
  it is only consulted when the current read fails, and it is never used for
  anything but display.
- `IsTyping` reads the same game global the native `GetIsTyping()` reads
  (`chat_methods.cpp:84`). The runtime additionally clears that global from a
  `kDestroyFrame` hook, which writes into *game* memory, so this reader observes
  the cleared value too and the two cannot diverge.
- `GetInstanceUptime` is not yet ported: its body delegates to `Agent.GetInstanceUptime`, a
  member of the unported `Agent` class, whose frame-limit call `GW::ui::GetFrameLimit`
  (`ui_methods.cpp:1833-1858`) is unported too. The call that reads it does return its value
  (`CommandRecord.value`), so nothing about the capability layer is in the way.
- The live suite needs a logged-in character in a loaded map, so it contributes
  nothing at the character-select screen. Run it before and after any change to
  the `Player` members.
- **pyright does not check struct member names.** An unknown attribute on a
  `ctypes.Structure` subclass resolves to type `Any`, so
  `reportAttributeAccessIssue` never fires for it, in this project or in a
  `.pyi`-backed module — verified with `reveal_type`. A typo like
  `world.unlocked_map` for `world.unlocked_maps` pyrights clean and is caught
  only by the live tests, which is how that one was found. Plain classes and
  dataclasses are checked normally. Treat the live suite, not pyright, as the
  guard for context field names.
- `InstanceInfoStruct.terrain_count` is left as declared. It is read only by
  Reforged's diagnostics (`NativeContext.py:1417`, `context_diagnostic.py:235`)
  and by a native `struct` declaration; no behavior depends on it, so per
  `SCOPE.md` it is not required work.
