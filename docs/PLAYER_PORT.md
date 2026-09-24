# Player port

`py4gw/player.py` ports Reforged's `Py4GWCoreLib/Player.py`. Every member keeps
its Reforged name and signature, so `Player.GetLevel()` means the same thing
after switching libraries. What differs is which members can produce a value.

| | Count |
| --- | ---: |
| Reforged members ported | 70 |
| ... that return a real value | 46 |
| ... that refuse with a reason | 24 |
| Stealth-only additions | 3 public, from native `PyPlayer` (see below), and 6 private helpers |
| Reforged members renamed | 1 (`_hwnd_account_fallback` → `_account_fallback`) |
| Members that write to `Gw.exe` | **0** |

`Player` is a namespace of static methods, as in Reforged. It resolves the
selected client through `py4gw.client.current_client`, the same way the context
readers do, so `py4gw.connect(...)` must run first. Implemented members return
Reforged's own defaults when a context is unavailable; a member called with *no*
client raises `RuntimeError`, because that is a usage error rather than a game
state.

## The three groups

**Implemented (46).** The value comes from a game context this project can read.
Each member's docstring names its source.

**Disabled (24).** The value only exists inside the running client, or the member
acts on the game. These raise `NotImplementedError` naming the missing mechanism
and the member, so a ported script fails at the call site instead of silently
receiving a wrong value. They are present, not omitted, which is the point: a
`hasattr` check passes and the failure is attributable.

**Adapted.** Reachable, but by a different route than Reforged uses. Listed in
full below.

## Adaptations

| Member | Reforged | This port | Why |
| --- | --- | --- | --- |
| `_hwnd_account_fallback` | builds `<hwnd>@Py4GW` from `PySystem.Console.get_gw_window_handle()` | renamed `_account_fallback`, builds `<pid>@Py4GW` | `py4gw.win32.Win32` does not enumerate windows. Both identifiers are stable and unique per client, and the value only stands in for an unreadable email. |
| `GetName` | `Agent.GetNameByID` → native binding reading the encoded agent name | reads `CharContext.player_name_str` | The character context already carries the same name as a plain field, so no binding is needed. |
| `IsPlayerLoaded` | map gate, then a party lookup, then a fallback tail with `Agent.GetInstanceUptime(agent_id) > 750` | the native version: map gate, then the party lookup, then `False` | Native `GetIsPlayerLoaded` (`player_bindings.cpp:30`) has **no** warm-up tail and returns `False` when no party member matches. See the provenance analysis below. |
| `GetMorale`, `GetExperience`, `GetLevel`, `GetSkillPointData`, the four faction readers | `max(field, field_dupe)` | the native `PickHighest(field, field_dupe)` | Not equivalent. See below. |
| `GetInstanceUptime` | `agent.timer / GetFPSLimit() * 1000` | **disabled** | `GW::ui::GetFrameLimit` (`ui_methods.cpp:1833`) resolves the limit through `g_get_graphics_renderer_value_func`, a client function pointer, plus the graphics-option state. The divisor cannot be read. |
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

The Reforged tail is also largely unreachable in the normal case: the party loop
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

## Disabled members

| Member | Group | What it needs |
| --- | --- | --- |
| `player_instance` | binding | returns a `PyPlayer` object that only exists in-process |
| `GetTargetID` | capture | `g_current_target_id`, a DLL global set from a `kChangeTarget` UI-message hook (`agent.cpp:60,163`) |
| `IsChatHistoryReady` | capture | the runtime's chat-history buffer |
| `GetChatHistory` | capture | the runtime's chat-history buffer |
| `GetInstanceUptime` | capture | the client's frame limit, via a function pointer |
| `SetPlayerStatus` | action | client setter, so the client emits the CtoS packet |
| `ChangeTarget` | action | client target setter |
| `CallTarget` | action | `kSendCallTarget` UI message dispatched in-process |
| `Interact` | action | client agent-interaction function |
| `Move` | action | client movement function |
| `DepositFaction` | action | client faction-deposit action |
| `RemoveActiveTitle` | action | client title action |
| `SetActiveTitle` | action | client title action |
| `SendRawDialog` | action | `kSendAgentDialog` UI message |
| `BuySkill` | action | skill-trainer dialog |
| `UnlockBalthazarSkill` | action | Balthazar vendor dialog |
| `SendDialog` | action | client dialog sender |
| `SendAutomaticDialog` | action | DLL-owned active dialog plus the client dialog sender |
| `RequestChatHistory` | action | client chat-history request |
| `SendChatCommand` | action | client chat sender |
| `SendChat` | action | client chat sender |
| `SendWhisper` | action | client chat sender |
| `SendFakeChat` | action | local chat injection through the client's chat hook |
| `SendFakeChatColored` | action | local chat injection through the client's chat hook |

All five action mechanisms named above are the ones already catalogued in
[`WRAPPER_MIGRATION_ASSESSMENT.md`](WRAPPER_MIGRATION_ASSESSMENT.md); every one
requires code executing inside `Gw.exe`. Nothing here adds a write, a hook, or a
payload to the client.

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
reaches through `GetAgentID` and the disabled `GetTargetID` respectively.

## Verification

- `tests/test_player.py` — **36 live tests**. Every implemented member is checked
  against the context it claims to read, or against an invariant that must hold
  in a loaded map. Cross-checks cover the character context, the world context,
  the party list, the friend list, the player agent id global, and the agent
  record. The suite skips at the character-select screen.
- `tests/test_player_offline.py` — 21 offline tests. They assert that every one
  of the 70 Reforged member names exists and is a `staticmethod`, that each
  disabled member raises `NotImplementedError` naming itself, that each
  implemented member refuses loudly without a connection, and they exercise the
  pure helpers (`PlayerStatus` coercion and display names, `FormatChatMessage`
  clamping, UUID formatting, email sanitizing).
- `examples/player.py` — reads every implemented member live and then shows four
  disabled members refusing.
- Live run, PID 29520: player number 12, login number 12, party number 0, agent
  id 1153, observing id 1153, level 20, 47 title records, 108 unlocked skills,
  status 1 (`online`), `IsTyping` false. Account flags read `0x4`, which reports
  `IsReforged() == True` — consistent with `F:\GW\GW1\Gw.exe` being the Reforged
  build.

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
- `GetInstanceUptime` cannot be reproduced: the divisor is a client frame limit
  reachable only through a function pointer.
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
