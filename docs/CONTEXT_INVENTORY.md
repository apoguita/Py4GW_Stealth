# Context Inventory

This document is the source inventory for Guild Wars contexts. It compares
the current `Py4GW_Reforged_Native` C++ context layer with the
`Py4GW_Reforged` Python context layer, then records what has and has not been
ported to Stealth.

An inventory is not an implementation. It tells us what exists, how the two
source projects name it, and what still needs an external reader.

## Sources and meaning

The native inventory comes from:

```text
Py4GW_Reforged_Native/include/GW/context/
Py4GW_Reforged_Native/include/GW/context/context.h
```

The Python inventory comes from:

```text
Py4GW_Reforged/Py4GWCoreLib/native_src/context/
Py4GW_Reforged/Py4GWCoreLib/Context.py
```

The native headers are the broader source. They contain root contexts,
nested data structures, and support types. The Python package groups some of
those structures together, so the lists are not expected to match one for
one.

The native and Reforged projects are comparative sources for Stealth. A
source entry is not yet a live-client result, and a context is not ready for
Stealth until its address resolution, layout, pointer fields, and live read
behavior have been verified externally.

## Native C++ context headers

The native context directory currently contains these 30 headers:

| Header | Main context or data surface |
| --- | --- |
| `account.h` | `AccountContext` and account character/unlock data |
| `agent.h` | `AgentContext`, agent records, effects, equipment, and snapshots |
| `attribute.h` | Attribute and party-attribute records |
| `camera.h` | `Camera` |
| `character.h` | `CharContext`, progress bars, and observer data |
| `chat.h` | Chat messages and chat buffers |
| `cinematic.h` | `Cinematic` |
| `context.h` | Root accessors and the runtime pointer snapshot |
| `friend_list.h` | `FriendList` and friend records |
| `gadget.h` | Gadget records and `GadgetContext` |
| `game.h` | `GameContext` |
| `gameplay.h` | `GameplayContext` |
| `guild.h` | `GuildContext` and guild records |
| `hero.h` | Hero flags, hero records, and related data |
| `item.h` | Item, bag, inventory, PvP, and salvage data |
| `map.h` | `MapContext`, instance, area, mission-map, and world-map data |
| `match.h` | Observer-match data |
| `npc.h` | NPC records |
| `party.h` | `PartyContext`, party members, and party search data |
| `pathing.h` | Pathing, map-prop, and prop data |
| `player.h` | Player records |
| `pregame.h` | `PreGameContext` and login-character data |
| `quest.h` | Quest and mission-objective data |
| `render.h` | `GwDxContext` render data |
| `skill.h` | Skills, skill bars, effects, buffs, and templates |
| `text_parser.h` | `TextParser` and text-cache data |
| `title.h` | Titles, tiers, and title client data |
| `trade.h` | `TradeContext` and trade records |
| `ui.h` | UI frames, windows, tooltips, and UI support records |
| `world.h` | `WorldContext` and player/world state records |

### Native root accessors

`context.h` declares these process-global accessors:

```text
GetGameContext
GetPreGameContext
GetWorldContext
GetPartyContext
GetCharContext
GetGuildContext
GetItemContext
GetAgentContext
GetMapContext
GetAccountContext
GetTradeContext
GetGameplayContext
GetTextParser
GetCamera
GetFriendList
GetMissionMapContext
GetWorldMapContext
GetSalvageSessionInfo
GetRenderContext
GetWindowHandlePtrAddress
GetControlledCharacterId
```

The native `RuntimePointersSnapshot` also records the currently resolved
addresses for the mission map, world map, gameplay, instance, map, game,
pregame, world, character, agent, guild, party, trade, item, friend, render,
text, camera, and window-handle surfaces. These are runtime pointer values;
they are not separate structure definitions.

The native implementation resolves the stable `context.base_ptr` location
once, then follows the current pointer chain when a context is requested.
This distinction matters for Stealth: the resolver location can be cached,
but dynamic context pointers must be re-read at operation boundaries because
login, map, and character state can change.

## Reforged Python context modules

The Reforged Python context directory currently contains 17 context modules
(not counting `__init__.py`):

| Module | Main public types | Public facade in `context/__init__.py` |
| --- | --- | --- |
| `AccAgentContext.py` | `AccAgentContextStruct`, `AccAgentContext` | Yes |
| `AgentContext.py` | `AgentArrayStruct`, `AgentArray`, agent and effect records | Yes |
| `AvailableCharacterContext.py` | `AvailableCharacterArrayStruct`, `AvailableCharacterArray` | Yes |
| `CharContext.py` | `CharContextStruct`, `CharContext`, observer/progress records | Yes |
| `CinematicContext.py` | `CinematicStruct`, `Cinematic` | Yes |
| `GameContext.py` | `GameContextStruct` | No direct facade import |
| `GameplayContext.py` | `GameplayContextStruct`, `GameplayContext` | Yes |
| `GuildContext.py` | `GuildContextStruct`, `GuildContext` | Yes |
| `InstanceInfoContext.py` | `InstanceInfoStruct`, `AreaInfoStruct`, `InstanceInfo` | Yes |
| `MapContext.py` | `MapContextStruct`, `MapContext` and map/pathing records | Yes |
| `MissionMapContext.py` | `MissionMapContextStruct`, `MissionMapContext` | Yes |
| `PartyContext.py` | `PartyContextStruct`, `PartyContext` | Yes |
| `PreGameContext.py` | `PreGameContextStruct`, `PreGameContext` | Yes |
| `ServerRegionContext.py` | `ServerRegionStruct`, `ServerRegion` | Yes |
| `TextContext.py` | `TextParserStruct`, `TextParser` | No direct facade import |
| `WorldContext.py` | `WorldContextStruct`, `WorldContext` and many world records | Yes |
| `WorldMapContext.py` | `WorldMapContextStruct`, `WorldMapContext` | Yes |

`Py4GWCoreLib/Context.py` exposes the higher-level `GWContext` names:

```text
AccAgent, AgentArray, AvailableCharacterArray, Char, Cinematic,
Gameplay, Guild, InstanceInfo, Map, MissionMap, Party, PreGame,
ServerRegion, World, WorldMap
```

These facades generally provide `GetPtr`, `GetContext`, and `IsValid`.
`InstanceInfo` additionally exposes map information. `GameContext.py` and
`TextContext.py` still exist as source modules even though they are not
imported as direct entries by `native_src/context/__init__.py`.

## Native-to-Python mapping

This is the practical mapping we should use when planning external readers.

| Native surface | Reforged Python source | Mapping note |
| --- | --- | --- |
| `GameContext` | `GameContext.py` | Struct source only; it also contains the pointer chain used to reach `CharContext`. |
| `PreGameContext` | `PreGameContext.py` | Direct context family. |
| `WorldContext` | `WorldContext.py` | Large aggregate containing many world/player/quest/hero/skill records. |
| `PartyContext` | `PartyContext.py` | Direct context family. |
| `CharContext` | `CharContext.py` | Direct context family; the first Stealth implementation. |
| `GuildContext` | `GuildContext.py` | Direct context family. |
| `ItemContext` | `WorldContext.py` and item/inventory wrappers | No single same-named Python context module. |
| `AgentContext` | `AgentContext.py` and `WorldContext.py` | Agent arrays and agent records are grouped in Python. |
| `MapContext` | `MapContext.py`, `InstanceInfoContext.py` | Map, area, instance, and pathing data are split across modules. |
| `AccountContext` | `AccAgentContext.py`, `AvailableCharacterContext.py`, `WorldContext.py` | Account-level data is split by use. |
| `TradeContext` | trade wrappers outside this directory | No direct `TradeContext.py` module in the inspected directory. |
| `GameplayContext` | `GameplayContext.py` | Direct context family. |
| `TextParser` | `TextContext.py` | Exists as a source module but is not a direct `context/__init__` import. |
| `Camera` | camera wrappers outside this directory | Reforged exposes camera through other library surfaces. |
| `FriendList` | friend wrappers outside this directory | No direct same-named context module. |
| `MissionMapContext` | `MissionMapContext.py` | Direct context family. |
| `WorldMapContext` | `WorldMapContext.py` | Direct context family. |
| `SalvageSessionInfo` | item/salvage wrappers | Native accessor has no same-named Python context module. |
| `GwDxContext` | render wrappers outside this directory | Native render surface, not a direct context module. |
| window handle / controlled character ID | library/runtime helpers | Scalar accessors, not structure contexts. |

The important consequence is that “add all contexts” means covering the
native surfaces and their nested data, not copying 30 headers into 17 Python
files. Some Stealth readers will correspond to a Reforged module; others will
be a small reader assembled from a native root plus structures that Reforged
keeps in another module.

## Stealth status

### Implemented

- `Win32`: read-only process discovery and module information.
- `ProcessMemoryReader`: bounded read-only `ReadProcessMemory` transport.
- `RemoteScanner`: PE section discovery and remote pattern scanning.
- `PatternCatalog`: copied JSON signatures and resolver chains.
- `ConnectedClient`: selected-process ownership and connection state.
- `context.CharContext`: external `CharContextStruct`, pointer-chain read,
  character-name decoding, and `GWArray` views.
- `context.GameContext`: external root context and cached base-pointer resolver.
- `context.PreGameContext`: optional selection-menu context and login-character
  array.
- `context.Cinematic`: optional 8-byte context reached through
  `GameContext.cinematic`.
- `context.GameplayContext`: optional gameplay structure with the maintained
  mission-map zoom field.

The implemented context readers are live-verified. Their resolver scans are
performed during connection and stable resolver locations are cached; dynamic
context pointers and structure bytes are re-read for each snapshot.

The migration sequence so far is: `CharContext`, `GameContext`,
`PreGameContext`, `Cinematic`, then `GameplayContext`. The next selected simple
context is `ServerRegion`.

### Not yet implemented in Stealth

The remaining native and Reforged contexts listed above do not yet have an
external Stealth reader. The offsets directory may already contain signatures
for several surfaces, but a signature definition alone is not a context reader.
Each new reader still needs:

1. a documented root-address resolver;
2. a fixed-width external structure definition;
3. explicit pointer and array follow rules;
4. a public context API and connection-lifetime behavior; and
5. offline tests plus a separately recorded live-client verification.

The next implementation decision should be made from this inventory. It
should not be inferred from the number of files in either source project.

## Migration complexity categories

These categories are planning estimates based on the inspected Reforged
module size, number of nested structures, number of remote pointers/arrays,
and whether the context has its own resolver. They are not claims about live
performance.

### Simple candidates

These have small structures and few dependencies, making them appropriate
next steps:

- `ServerRegionContext.py`
- `WorldMapContext.py`
- `MissionMapContext.py`
- `AvailableCharacterContext.py`
- `InstanceInfoContext.py`
- `TextContext.py` (small layout, but string pointers need a reader helper)

### Moderate candidates

These contain several arrays or related records, but are still bounded enough
to migrate as one focused task:

- `AccAgentContext.py`
- `PartyContext.py`
- `GuildContext.py`
- `PreGameContext.py` (already migrated)
- `CharContext.py` (already migrated)

### Complex candidates

These aggregate many independently meaningful structures and should be left
until the smaller roots are available:

- `MapContext.py`
- `WorldContext.py`
- `AgentContext.py`

The native-only or distributed surfaces (`ItemContext`, trade, friend list,
camera, render, UI, salvage, and related records) should be scheduled after
the root context that owns their pointers is understood. The next simple
implementation candidate is `ServerRegion` unless a different candidate is
selected deliberately.

## Migration checklist

This is the working checklist for adding external readers. A checked item
means the context has a reader in Stealth and a live verification record; it
does not mean that every nested record in the source project is complete.

### Completed

- [x] `CharContext`
- [x] `GameContext` / base context pointer surface
- [x] `PreGameContext`
- [x] `Cinematic`
- [x] `GameplayContext`

### Pending: simple contexts

- [ ] `ServerRegion`
- [ ] `WorldMapContext`
- [ ] `MissionMapContext`
- [ ] `AvailableCharacterArray`
- [ ] `InstanceInfo`
- [ ] `TextParser`

### Pending: moderate contexts

- [ ] `AccAgentContext`
- [ ] `PartyContext`
- [ ] `GuildContext`

### Pending: complex contexts

- [ ] `MapContext`
- [ ] `WorldContext`
- [ ] `AgentContext` and `AgentArray`

### Pending: native-only or distributed surfaces

- [ ] Native-only or distributed surfaces: item, trade, friend list, camera,
  render, salvage, UI, gadget, chat, quest, title, skill, hero, player, NPC,
  and pathing data.

The final line is intentionally grouped. Those native headers contain many
records that may be reached through another root context rather than through
a separate top-level pointer. They should be split into individual tasks
only after their owning root and pointer relationships are verified.
