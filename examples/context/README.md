# One script per context

Each file connects to one running Guild Wars client, reads a single context,
and shows three ways to get at its data: the whole structure at a glance,
individual fields read directly, and the same fields as plain Python data.
They contain no argument parsing, no error handling, and no UI.

```text
python examples/context/camera_context.py
```

Run them from an **elevated shell**: `py4gw.connect(...)` refuses to connect
without one, with a message naming the pid and the rights Windows withheld.

These scripts read, but `connect(...)` writes: it installs `py4gw/game_thread/` —
two entry hooks on the client's own functions, an emitted dispatcher and an
observer — and removes them again at `py4gw.disconnect()`. That is the default, so
the examples exercise the same connection a caller gets by default. Pass
`game_thread=False` for a connection that only reads and patches nothing.

Every script has the same shape, with the field lines chosen for that context:

```python
import py4gw

client = py4gw.connect(py4gw.win32.list_processes()[0])
context = py4gw.context.cameracontext.get()

# the whole structure at a glance
print(context)
print()

# individual fields, read directly
print("looking at agent:", context.look_at_agent_id)
print("distance:", context.distance)
print("yaw:", context.yaw)

# every field as plain data, decoded, for use in code
print("as dict:", context.to_dict())

py4gw.disconnect()
```

## The three access styles

| Style | Use it for |
| --- | --- |
| `print(context)` | a glance at the whole structure; values are decoded, records recurse, long buffers are shortened |
| `context.field_name` | one value, read directly, exactly as the source layout declares it |
| `context.to_dict()` | every field as plain data, complete, for code rather than for reading |

`iter_fields()` is also available when you want `(name, value)` pairs in layout
order.  Raw attributes keep their source `ctypes` types, so `to_dict()` is the
one to use when you want decoded values without printing.

Nested records read through the attribute, for example
`context.player.gold` in `trade_context.py` or `context.start_pos.x` in
`map_context.py`.  `GW_Array`-backed fields expose their header, so
`context.map_agents_array.m_size` gives the element count.

## Scripts

| Script | Context | Reads |
| --- | --- | --- |
| `char_context.py` | `CharContext` | the character and map state of the logged-in character |
| `game_context.py` | `GameContext` | the root game context and its child pointers |
| `world_context.py` | `WorldContext` | parties, players, agents, quests, skillbar, titles |
| `map_context.py` | `MapContext` | the current map, its pathing grids, and props |
| `mission_map_context.py` | `MissionMapContext` | the mission map |
| `world_map_context.py` | `WorldMapContext` | the world map |
| `salvage_context.py` | `SalvageSessionInfo` | the salvage session |
| `gameplay_context.py` | `GameplayContext` | gameplay state including mission-map zoom |
| `pre_game_context.py` | `PreGameContext` | the character-selection menus |
| `instance_info_context.py` | `InstanceInfo` | the current instance, map dimensions, area info |
| `server_region_context.py` | `ServerRegion` | the connected region |
| `text_parser_context.py` | `TextParser` | the text parser and its language/file slots |
| `cinematic_context.py` | `Cinematic` | cinematic playback state |
| `camera_context.py` | `Camera` | camera position, zoom, yaw, pitch |
| `party_context.py` | `PartyContext` | the party, heroes, henchmen, flags |
| `guild_context.py` | `GuildContext` | the guild, its members, and its history |
| `friend_list_context.py` | `FriendList` | friends and ignored players |
| `chat_buffer_context.py` | `ChatBuffer` | the encoded chat message ring |
| `trade_context.py` | `TradeContext` | an open trade and both sides' offers |
| `item_context.py` | `ItemContext` | bags, items, formulas, storage state |
| `account_context.py` | `AccountContext` | account unlocks and stored items |
| `gadget_context.py` | `GadgetContext` | gadgets such as chests and signposts |
| `acc_agent_context.py` | `AccAgentContext` | the agent context root and movement arrays |
| `available_character_context.py` | `AvailableCharacterArray` | the account's character roster |
| `agent_array.py` | `AgentArray` | the bounded agent snapshot |

## When a script prints `None`

Five of these legitimately return `None`, and it is not an error:

| Script | Prints `None` when |
| --- | --- |
| `mission_map_context.py` | the mission map is not open |
| `world_map_context.py` | the world map is not open |
| `salvage_context.py` | no salvage window is open |
| `pre_game_context.py` | a character is logged in |
| `instance_info_context.py` | a map is loading, so the instance pointer is null |

The three map/salvage contexts are published only through the UI frame that
owns them, so they do not exist while their surface is closed.  This is the
intended behaviour, not a failure to resolve a pointer.  See
[`../../docs/UI_FRAME_TREE.md`](../../docs/UI_FRAME_TREE.md).

The instance info is different: it is published through a module-global pointer
that the client nulls while a map loads, and the reader deliberately
re-dereferences that pointer on every read instead of caching it, so `None`
means "the map is not ready yet".  That is the same signal the native runtime
reports as `InstanceType.Loading`.  Call `py4gw.Map.IsMapReady()` before
reading, and see [`../../docs/READINESS_GATE.md`](../../docs/READINESS_GATE.md).

Those five scripts wrap their field reads in `if context is not None:` because
there is nothing to read while the surface is closed or the map is loading.

The other twenty check first and stop with a clear message:

```python
if context is None:
    raise SystemExit("no Guild Wars client is connected")
```

`get()` is typed `X | None` because it returns `None` when nothing is
connected, so the checker requires narrowing before a field can be read. An
explicit check is used rather than `assert` because `assert` is removed under
`python -O`, which would turn a clear message into a late `AttributeError`.

The two patterns mean different things and are not interchangeable: for the map,
salvage, pre-game, and instance-info contexts, `None` is a **normal state**
meaning the surface is closed or the map is loading; for the other twenty it
means **nothing is connected**, which is a usage error worth stopping on.

Printing is handled by the library, not by these scripts. Game text can hold
characters a Windows console cannot encode, so the printed form escapes only
those characters while `to_dict()` always returns the real string. Nothing has
to configure stdout.

## Reading without writing a loop

```python
context = py4gw.context.charcontext.get()

print(context)                  # glance: every field, values decoded
context.to_dict()               # every field, complete data
context.iter_fields()           # (name, value) pairs in layout order
context.map_id                  # the raw source field, unchanged
```

Long buffers are shortened in the printed form only, so `to_dict()` never
hides data from a program.
