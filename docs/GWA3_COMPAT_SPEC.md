# The GwAu3-compatible layer (`py4gw.gwa3`) â€” specification record

**Status: specification, with the constants, the route map and the read-side audit built.**

| Part | State |
| --- | --- |
| The design in this document | **settled** â€” scope, tiers, bridge, layout, order |
| `py4gw/gwa3/constants.py` + `tools/generate_gwa3_constants.py` | **built and verified offline** â€” 7,480 constants, 15 tests |
| `docs/GWA3_ROUTE_MAP.md` + `tools/generate_gwa3_route_map.py` | **built** â€” 648 declared functions, 80 recorded routes, 11 tests; `NO ROUTE YET` is the remaining work, named per row |
| `docs/GWA3_AGENT_FIELD_AUDIT.md` + `tools/audit_gwa3_agent_fields.py` | **built** â€” the read side's central claim, measured on GwAu3's highest-traffic accessor: **101 of 142 keys resolve to a named attribute** |
| `py4gw/gwa3/data_agent.py` + `tools/generate_gwa3_data_agent.py` | **built** â€” GwAu3's 8 `Agent_*` accessors over this project's records, all **143** of `Agent_GetAgentInfo`'s field keys present (4 refusing with a reason), 32 offline tests |
| `py4gw/gwa3/data_skill.py`, `data_item.py`, `data_quest.py`, `data_party.py` + `tools/generate_gwa3_family.py` | **built** â€” `Skill_GetSkillInfo` (**63/63**), `Item_GetItemInfoByItemID` (**39/39**), `Quest_GetQuestInfo` (**22/22**), `Party_GetPartyContextInfo` (**14/14**), `World_GetWorldInfo` (**79/79**); **the name-decode handshake is wired**; 35 offline tests |
| `external/GwAu3_mechanism_map.json` + `docs/GWA3_MECHANISM_MAP.md` | **built** â€” all **648** declared functions classified; the route map's mechanism column carries them |
| `py4gw/gwa3/cmd_agent.py` | **built** â€” **the first action module**: 13 of `GwAu3_Cmd_Agent.au3`'s 13 functions, 11 routed and 2 refusing with their gap named; 20 offline tests that assert *which member is called with which arguments* |
| `py4gw/gwa3/cmd_chat.py`, `cmd_map.py` | **built** â€” `GwAu3_Cmd_Chat.au3` (**3/3**) and `GwAu3_Cmd_Map.au3` (**12/14**, 2 refusing); 15 offline tests |
| `py4gw/gwa3/bridge.py` | **built** â€” the protocol and the worker: line-delimited JSON, four distinguishable failure kinds, 28 offline tests |
| `tools/autoit/Stealth_GwAu3.au3` + `generate_stealth_udf.py` | **built and run under the interpreter** â€” 648 AutoIt wrappers (12 routed, 636 reporting `not_implemented`), 13 checks passing with no client; readings in `tools/autoit/READINGS.md` |
| The remaining accessor families, the `Cmd_*` action modules, a named-pipe transport | **not written** |

So the constants a migrating script needs are real and checked against GwAu3's own sources, the
route each function will take is written down with its evidence, and the read side's core claim is
measured rather than assumed. The routines are not written, and this document says so rather than
implying otherwise.

This document is the specification record for `py4gw/gwa3`, a **Stealth-owned component** in
the same category as `py4gw/game_thread/` (spec: [`NATIVE_EXECUTION_PLAN.md`](NATIVE_EXECUTION_PLAN.md))
and `py4gw/gui` (spec: [`AUTOIT_GUI.md`](AUTOIT_GUI.md)) â€” not a port, and not an exception
to the porting rule quietly taken.

## Why it exists, in the owner's words

> *"people are already using gwau3 and are very used [to it] and some of them only know
> AutoIt, there has been much resistance when migrating to Reforged (python based), so
> Stealth is a 'reinvention' of gwau3 â€¦ we could make an AutoIt bridge and we could make a
> class that copies naming / function / usage from gwau3 so they find the migration much
> more familiar."*

The audience is a GwAu3 script author. Their script is AutoIt, it calls
`Agent_GetAgentInfo(-2, "X")`, `Map_TravelTo($mapID)`, `Skill_UseSkill(3)`, and it reads
`$GC_I_ALLEGIANCE_ENEMY`. Migration cost is the only thing standing between them and
Stealth's capability set, and that cost is almost entirely *naming* â€” the surface, not the
behaviour underneath it. This layer pays that cost once, in the library, instead of in every
script.

## The category, stated plainly

| | ported classes (`Map`, `Player`, `Party`, `Dialog`, â€¦) | Stealth-owned components |
| --- | --- | --- |
| Spec source | Reforged Python and Reforged Native, line for line | a written, external specification |
| Examples | `Map`, `Player`, `Party`, `Dialog` | `py4gw/game_thread/`, `py4gw/gui`, **`py4gw/gwa3`** |
| Parity test | member-for-member against the source file | against the specification and its reference implementation |

Neither Reforged nor Reforged Native has a GwAu3-compatible surface â€” the table in
[`PORTING_RULES.md`](PORTING_RULES.md) says so directly: *"`external/GwAu3` | **no** â€”
reference only"*. So there is no source to port here and none is claimed. The specification
is **GwAu3's own public surface** â€” its declared functions, their arguments and defaults,
their return values and its constants â€” read from the checkout at `external/GwAu3`
(MIT, `JAG-GW`, 2025). The implementation behind each name is Stealth's own.

## The first rule: the separation is structural, not a matter of discipline

`py4gw/gwa3` is a **sibling package that imports the ported classes and is imported by
none of them.** No `GwAu3_*` name, no `$GC_*` constant and no translation table appears
anywhere under `py4gw/` outside `py4gw/gwa3/`. Nothing in `Map`, `Player`, `Party`,
`Dialog`, `Item`, `Skill` or `game_thread` learns that this layer exists.

That is what makes the two rules compatible instead of contradictory:

- **The ported surface stays exactly what it is.** The member-for-member audit in
  [`PORTING_RULES.md`](PORTING_RULES.md) keeps passing, because it inspects the ported
  classes and this layer adds nothing to them. A `GwAu3_*` name is never a second spelling
  of a source member and never a licence for a new member on a ported class.
- **GwAu3's names live where GwAu3's names belong** â€” in a component whose specification
  *is* GwAu3. This is the same resolution the port already uses for `PyInventory`,
  `PySkillbar` and the rest: parity is the sources' scheme, one scheme per module, and a
  document that names which scheme a module carries.

If this separation is ever broken â€” a `GwAu3_*` function on `Map`, a `"field name"` argument
on `Agent`, a `$GC_*` constant in `offsets/` â€” the layer has become the thing the porting
rules forbid, and the audit procedure in `PORTING_RULES.md` is what finds it.

## The second rule: a migrated script's own calls must all resolve

**The layer is complete for the surface a script actually touches** â€” not for the API's whole
declaration list. The corrected scope in the next section is what that means concretely: the ~250
routines the census finds in real call sites, and the 7,480 constants they pass as arguments.

The 417 functions no user-facing script calls still belong in the layer eventually, and the reason
is worth stating so they are not written off: several of them are the *internals* of the ones that
are called (`_ApplyFilters`, `Agent_ConvertID`, `Item_ItemID`, `Utils_DecodeEncString*`, and
`World_GetWorldInfo`, which backs half the accessors), and a caller who reaches one should not hit a
hole. But they are mechanical â€” 453 of the whole surface is a read, and another 92 is a game-thread
call this project already makes â€” so they are breadth rather than risk, and they can land after the
surface a script needs does.

The constant surface is dominated by four generated tables â€” `$GC_I_SKILL_*` (3,131),
`$GC_I_QUEST_*` (1,398), `$GC_I_ITEM_*` (1,022), `$GC_I_MAP_*` (950) â€” which is why it is generated
rather than hand-picked. A script names a map or a skill by passing the constant, so a layer missing
constants moves nobody even with every function working.

## The third rule: the caller does not see the mechanism

*"its not important as long as they do the same"* â€” and that must hold in both directions. The
caller must not be able to tell **which** mechanism carried a call, and must not be told it got one
it did not get. Two consequences:

- **A `REFUSED` row must not look like a `ROUTED` row.** Where GwAu3 sends a forged packet and
  Stealth has a native route to the same effect, the row is `ROUTED` and the caller sees GwAu3's own
  return shape. Where no safe route exists, the row refuses and says so â€” it never quietly performs a
  *different* action that happens to return the same type, because a caller cannot tell the
  difference and would then trust the wrong one.
- **Where the two spellings already differ inside GwAu3, both are kept.** The `Trade_*` pairs are
  the worked case: GwAu3's packet form returns `0`, its native twin returns `True`/`False` plus
  `@error`. That difference is GwAu3's own, so the layer keeps each spelling's contract and records
  the route rather than collapsing the pair into one entry.

## The scope, corrected by the owner (2026-10-12)

The first draft of this document framed the goal as "reproduce GwAu3 entire". The owner's
correction, verbatim:

> *"i think the scope is not well defined yet, i didnt mean copy the entirety of gwau3, stealth
> is already a full library, what i need is the user end facing routines, constants, functions
> are, how they are implemented, its not important as long as they do the same, they are named
> the same and are close to being used the same."*

That is a smaller and much better-defined target, and it changes what has to be measured. The
question is not *"can we reproduce GwAu3?"* â€” it is **"what does a GwAu3 user's script actually
touch, and what does each of those things take?"** Three answers follow, and each is measured.

### 1. What a user's script actually calls: 228 of the ~660

Counted by call site across everything in the GwAu3 checkout that is not the API itself
(`Scripts/`, `Plugins/`, `Utilities/`) â€” i.e. by what GwAu3's own users and example scripts
actually invoke:

| | Count |
| --- | --- |
| GwAu3 module functions declared | **~660** (a lower bound: the 645 below, plus at least 2 the surface index missed) |
| â€¦ **called from a user-facing script, plugin or utility** | **228** |
| â€¦ never called outside the API's own internals and definitions | ~430 |

**Why the declared figure is "~660" and not a number.** It comes from
`external/GwAu3_modules_surface.csv`, a one-line-per-declaration regex extraction made in this
session, and three independent source inventories each found functions it had **missed** â€”
`Party_LockHeroTarget` (`GwAu3_Cmd_Party.au3:55`), `Party_SetHeroAggression` (`:60`) and
`PreGame_CharName` (`GwAu3_Data_PreGame.au3:19`). The extraction's own provenance note is
`external/GwAu3_modules_surface.csv.md`, and its rule is: **an extraction is an index, never a
record.** The constant surface taught the same lesson from the other direction (eight 2-D array
declarations a `$NAME[n]` rule could not see â€” see *Constants* below), so any future count must be
re-derived from the `.au3` sources at the moment it is quoted, not read from that file.

The **228 is the number that matters** and it is derived from call sites, not from the index: it is
what a migration has to serve.

Of the 228, **113 are actions** (`Cmd`) and **115 are reads** (`Data`). That 113 is the real
size of the action surface a migration has to serve â€” not the 148 the API declares.

### 2. What dominates those calls: the field-name accessors, and they map to Stealth at the host

The census is unambiguous about what GwAu3 users spend their time in:

| Function | Call sites |
| --- | --- |
| `Agent_GetAgentInfo` | 216 |
| `World_GetWorldInfo` | 116 |
| `Skill_GetSkillInfo` | 64 |
| `Party_GetPartyContextInfo` | 25 |
| `Agent_GetCurrentTarget` | 24 |
| `Skill_GetSkillbarInfo` | 23 |
| `Quest_GetQuestInfo` | 18 |
| `Item_GetItemInfoByItemID` | 15 |

Seven accessor families account for the large majority of every GwAu3 script ever written, and
they all have the same shape: `Agent_GetAgentInfo($id, "X")` â€” an id and a **field-name string**
resolved by a `Switch` (`GwAu3_Data_Agent.au3:82`).

**Here is the finding that decides the whole read side:** Stealth does not have these accessors â€”
every one of the seven names is absent from `py4gw/` â€” **but it has the records they read, with
the same data under the same layout, as typed structure attributes.** `AgentLivingStruct`
(`py4gw/context/agent_array.py:838`) carries `allegiance` where GwAu3's `"Allegiance"` case reads
`+0x1B5`, `hp` for `+0x134`, `player_number` for `+0xF4`, `login_number` for `+0x184`, and the
visible-effect list as a `GWListStruct`.

So the read side is **pure host-side translation**: GwAu3's field string â†’ the typed record's
attribute, on a record this project already reads. That means

- **no new capability is needed for the dominant case** â€” no call form, no hook, no target-side
  work at all;
- **it is testable offline**, with no client and no elevation, because it is a mapping over
  in-memory structures;
- **the semantics come out exact for free**, because the field names *are* GwAu3's own contract
  and the layout is the client's own layout, which this project already validates.

This is the opposite of a workaround. Nothing is being approximated: the same bytes are being
named the way a GwAu3 user already names them.

### 3. What the actions actually take: three mechanisms, and only one is a problem

Classified per function, with cited lines, across all 648 declared functions. **The numbers below are
the classified figures**, from `external/GwAu3_mechanism_map.json` â€” 648 entries, one per `Func`
declaration, produced by reading each function's own body and resolving its command slot in GwAu3's
assembler (`docs/GWA3_MECHANISM_MAP.md`, and the route map's mechanism column now carries them):

| GwAu3 mechanism | Count | What it is here |
| --- | --- | --- |
| **MEMORY READ** | 439 | a read, from the ported class that owns that data â€” **mechanical** |
| **GAME-THREAD CALL** | 85 | already ported: a typed call on the game thread via `py4gw/game_thread` (**M1**) â€” **mechanical** |
| **PACKET SEND** | 76 | GwAu3 hands a record to an injected stub that runs `call PacketSend` (`GwAu3_Core_Assembler.au3:2095`) â€” **the only category that needs a decision**, per function |
| **PURE COMPUTATION** | 37 | host-side arithmetic â€” **mechanical** |
| **MEMORY WRITE** | 9 | a write Stealth performs inside the client (**M4**) â€” mechanical where a ported member does it |
| **UI/INPUT SYNTHESIS** | 2 | `Ui_ToggleRendering` and its twin, which also call `WinSetState` â€” host-side window state, not a game action |

So **~89 % of GwAu3's surface has a mechanical route**, and the whole design question is concentrated
in the 76 packet functions. Nothing ended in `OTHER`.

**An earlier estimate in this document said 108 packet senders and 138 game-thread calls.** Those were
derived by a keyword scan over the `.au3` text for the helper each function appeared to call, before
any function body was resolved. They were wrong: read per function and resolved through the assembler,
the packet senders are 76 and the game-thread calls 85. The classified figures are the ones to use, and
the episode is the reason the map carries a mechanism column with a citation per row rather than a
count from a scan.

**One correction the classification produced, which is worth recording because it is the opposite of
what the scan assumed.** `Agent_ClearTarget` â†’ `Agent_ChangeTarget` is a **game-thread call, not a
packet send**: `Agent_ChangeTarget` enqueues `$g_p_ChangeTarget` (`GwAu3_Cmd_Agent.au3:14`), whose
stub `CommandChangeTarget` (`GwAu3_Core_Assembler.au3:2438`) `call`s the client's own `ChangeTarget`
(`:2464`). Only `CommandPacketSend` (`:2088`) and `CommandSendChat` (`:2120`) reach `PacketSend`. The
same holds for every `$g_p_*`/`$g_d_*` slot except `Packet`, `SendChat` and `InviteGuild` â€” which is
good news for the port: those effects were already reached the way this project reaches them.

Those 76 are not 76 unknowns, because GwAu3 reaches many of the same effects twice â€” once by packet,
once by a native call â€” and Stealth has an independent route for most of the effects. The overlap the
inventories already establish:

| GwAu3 packet function | Stealth's own route (same effect, not a forged packet) |
| --- | --- |
| `Agent_Attack` | `Player.Interact(agent_id, call_target)` â€” `agent.do_world_action_func` (`player.py:1140-1185`) |
| `Agent_ChangeTarget` | `Player.ChangeTarget(agent_id)` â€” `agent.change_target_func` (`player.py:1074-1093`) |
| `Agent_CallTarget` | `Player.CallTarget(agent_id)` â€” `agent.call_target_func` (`player.py:1096-1137`) |
| `Agent_GoNPC` / `Agent_GoSignpost` | `Player.Interact` / `SendDialog` |
| `Skill_UseSkill` | the skillbar's own use path, and `UIManager.Keypress` â€” the client's key action |
| `Party_AddHero` / `Party_KickHero` / `Party_AddNpc` | `Heroes.AddHero` / `KickHero` / `Henchmen.AddHenchman` â€” the party callback (**M3/M1**, `party.py:1529`, `:1550`, `:1723`) |
| `Party_CommandHero` / `Party_CommandAll` | `Heroes.FlagHero` / `FlagAllHeroes` â€” `party.flag_hero_agent_func` (`party.py:1612`, `:1626`) |
| `Party_ToggleHeroSkillState` / `Party_DisableHeroSkill` / `Party_EnableHeroSkill` | `Heroes.SetSkillAIEnabled` â€” `party.command_hotkey_disable_ai_func` (`party.py:1599`) |
| `Party_LeaveGroup` | `Party.LeaveParty` â€” `_press_party_button` (`party.py:1293`) |
| `Map_TravelTo` / `Map_RndTravel` / `Map_MoveMap` | `Map.Travel` / `TravelToDistrict` / `TravelToRegion` â€” the client's own `kTravel` message (`map.py:816-892`) |
| `Map_Move` / `Map_MoveLayer` | `Player.Move(x, y, zPlane)` â€” `agent.move_to_func` (`player.py:1188`) |
| `Item_SwitchWeaponSet` | the item/weapon-set path in `py4gw/item.py` |
| `Item_PickUpItem` | the client's own `kInteractWithItem` UI message |
| `Chat_SendChat` / `Chat_SendWhisper` | `Player.SendChat` / `SendWhisper` â€” `chat.send_chat_func` (`player.py:1478`, `:1494`) |
| `Friend_SetPlayerStatus` and the `Friend_Add*`/`Remove*` family | `Player.SetPlayerStatus` â€” `friend_list.set_online_status_func` (`player.py:1050`) â€” and GwAu3's own versions are already **GAME-THREAD CALL**, not packets |
| `Title_SetDisplayedTitle` | `Player.SetActiveTitle` â€” `player.set_active_title_func` (`player.py:1242`) |
| `Game_DonateFaction` | `Player.DepositFaction` â€” `player.deposit_faction_func` (`player.py:1209`) |
| `Cinematic_SkipCinematic` | `Map.SkipCinematic` â€” `map.skip_cinematic_func` (`map.py:802`) |
| `Quest_AcceptQuest` / `Quest_QuestReward` / `Quest_AbandonQuest` | `Quest`'s own dialog/message path |
| `Effect_DropBond` | the effect/bond path in `py4gw/effect.py` and `party.py` |

**And note what this table is.** It is not a list of things to build. Every right-hand column is a
member that already exists and is already ported. The work in these rows is *naming*: give
GwAu3's name to a route that is already there and already verified.

The rows where no safe route exists are the ones that must refuse, and `Trade_*` is the clear
case: GwAu3's `Trade_*_` family is explicitly the packet version of its native twin, so the twin
is what gets used and the packet spelling refuses with the reason named.

### What this means for the AutoIt bridge

The bridge's job shrinks with the scope. It does not need to carry GwAu3's whole internal
machinery â€” only **the routines a user's script calls**: around **250 routines, 113 of them
actions**. And the constants do not travel over the bridge at all, because a script resolves them
at compile time in AutoIt, so they are shipped as files.

That is the corrected scope in one line: **~7,480 constants, ~250 routines, three mechanisms â€”
and only the 108 packet functions, most of which have a native twin, need a per-function
decision.**

### The cost is naming and fidelity, not capability

The owner's sentence â€” *"its not important as long as they do the same, they are named the same
and are close to being used the same"* â€” is exactly right, and the measurements above are what it
buys. What is left is the detail that makes a script run unchanged, and it is worth naming
precisely because it is where a lazy port fails:

1. **The field names and their types.** `Agent_GetAgentInfo($id, "X")` returns a float;
   `"ID"` a `long`; `"Name"` a string; the `Is*` keys a boolean. All of that is in the `.au3`
   `Switch`, per line â€” so it is transcription, not design.
2. **The sentinels.** `-2` = me, `-1` = my current target, resolved in `Agent_ConvertID`
   (`GwAu3_Data_Agent.au3:3-16`); a pointer or a DllStruct also accepted. Every heavy accessor
   goes through it.
3. **The return conventions.** AutoIt has no exceptions here: `0` for a field that does not
   exist, `""` for a name that does not resolve, `False` for a refused action. A migrated
   script branches on those. Raising where GwAu3 returns `0` would break it.
4. **The defaults**, because omitted arguments are everywhere: `Agent_GetAgentInfo($a_i_AgentID = -2, $a_s_Info = "")`,
   `Agent_GetDistance($a1, $a2 = -2)`, `Item_SalvageItem($v, "Standard", "Materials")`,
   `Party_LeaveGroup($a_b_KickHeroes = True)`.

None of those four is a design decision. They are all readable in the `.au3` files, which is the
point: the fidelity this layer needs is *reading accurately*, not *building*.

## Layout: one module per source file, so parity is checkable

The layer mirrors GwAu3's own layout exactly. `GwAu3_Cmd_Agent.au3` becomes
`py4gw/gwa3/cmd_agent.py`; `GwAu3_Data_Skill.au3` becomes `py4gw/gwa3/data_skill.py`. The
functions keep their names, their argument names, their argument order and their defaults.

Why this shape and not a tidier one:

- **Because `Map` vs `MapContext` vs `Map_Data` is a distinction GwAu3 users already hold in
  their heads**, and because collapsing the split means "which file was `Map_IsMapReady` in?"
  stops having an answer. A user searching the GwAu3 source finds the same file here.
- **Because parity becomes mechanical.** The check is a set comparison in both directions: the
  names extracted from the `.au3` files against the names the package defines. A routine a script
  calls and the package does not define is a defect; a name the package carries that GwAu3 does not
  declare is a defect in the other direction, and that second direction is the one that keeps this
  layer from becoming a place where inventing a name is allowed. Neither check needs judgement,
  which is what makes it survive contact with future edits.
- **Because it fixes the amount of invention at zero.** There is no design space left in
  "where does `Friend_AddIgnore` go" once the answer is "where GwAu3 puts it".

A single `py4gw/gwa3/__init__.py` re-exports everything, so a caller who does not care about
the split writes one import:

```python
from py4gw.gwa3 import *
```

## Naming: whose name is whose

- **Function names, argument names, argument order and default values are GwAu3's.** They
  are copied from the `.au3` declaration, not restyled and not Pythonised. Snake-casing them
  would be the one change guaranteed to break every script, which is the opposite of the
  point.
- **Argument type hints are Stealth's**, added around GwAu3's names. AutoIt is untyped and
  this project's APIs are explicitly typed (`AGENTS.md`, *Engineering and Verification*); a
  hint does not change a name, and `pyrightconfig.json` is checked in.
- **The bodies are Stealth's.** Which file a body lives in is a fact about Stealth â€” recorded
  per member, in the layer's own documents.

## Semantics: preserve the contract, change the engine â€” and never fake the engine

Two things must hold at once, and they are the whole difficulty of this layer.

**What is preserved is the caller-visible contract**, faithfully, because that is what makes
a script move:

1. The return *shapes* GwAu3 uses, including its failure values. Where GwAu3 returns `0` for
   an unreadable agent, this returns `0`; where it returns `False` from an action that the
   game refused, this returns `False`; where it returns `""`, this returns `""`. AutoIt has
   no exceptions in this role and a script tests these returns.
2. AutoIt's two argument idioms that are load-bearing in GwAu3:
   - **The sentinel agent id.** `-2` is "me" and `-1` is "my current target", resolved inside
     `Agent_ConvertID` (`GwAu3_Data_Agent.au3:3-16`). Callers pass them everywhere.
   - **The field-name argument.** `Agent_GetAgentInfo($id, "X")`, `World_GetWorldInfo("PlayerArray")`,
     `Item_GetItemInfo($id, "Name")`. The dispatch is a `Switch` on a string in GwAu3.
3. The default values, because a script that omits an argument must get GwAu3's behaviour:
   `Agent_GetAgentInfo($a_i_AgentID = -2, $a_s_Info = "")`, `Item_SalvageItem($v, "Standard", "Materials")`,
   `Map_Move($x, $y, $a_f_Randomize = 50)`.

**What is replaced is the mechanism, and it is replaced only by a safe route that already
exists here.** GwAu3 reaches the game three ways; Stealth reaches it two:

| GwAu3 mechanism | What it is in GwAu3 | In this layer |
| --- | --- | --- |
| `Core_Enqueue($ptr, $size)` (`GwAu3_Core.au3:559`) | writes a command record into a 256-slot ring buffer that an injected assembler stub drains on the game thread, and the stub calls the game's own function | **ported** as a typed call on the game thread through `py4gw/game_thread` â€” the same effect by Stealth's own verified route |
| plain memory read (`Memory_Read`, `Memory_ReadPtr`) | `ReadProcessMemory` on the client | **ported** as a read through the ported class that owns that data |
| `Core_SendPacket($size, $header, â€¦)` (`GwAu3_Core.au3:575`) | builds a 52-byte packet record the same stub turns into a message to the server â€” **a forged packet** | **refused.** This project's interactions are safe ones: it drives the game's own functions and its own messages rather than manufacturing protocol traffic |

The third row is the rule that has to be written down before any code, because it is the one
place where "copy GwAu3" and "this project's safety model" collide, and there is no middle
ground to negotiate:

> **A function whose only GwAu3 implementation is a forged packet has no implementation
> here.** It does not get a partial one, a "usually works" one, or a silently different one.
> It refuses, naming what it needs.

And the corollary that keeps the layer honest about its own gaps:

> **A function with no safe route *today* is not given one that is not in Stealth.** It
> carries its name, its GwAu3 line, and the exact capability it is waiting for â€” the same
> discipline `NotImplementedError` carries in the ported classes â€” and the capability is the
> work item. It never returns a plausible wrong value, because a wrong `True` from
> `Map_TravelTo` is worse for a migrating author than a refusal that names the gap.

`py4gw/game_thread` already has the pieces the first row needs: typed call forms (no
arguments, one, two, three, four and five words, a four-float pointer, the client's own
`__thiscall` shape, a packed UI message), a post-return observation form, and callbacks.
None of them is a packet forge, which is why the mapping lands where it does.

## The per-function route map

The route map â€” its four tiers, its size, and the rule that a row's tier is settled when the row is
implemented rather than in advance â€” is stated under *The route map, and what each tier needs* at the
end of this document, so the scheme is not written down twice.

## Constants: generated, never hand-copied

`py4gw/gwa3/constants.py` is produced by a tool, exactly as `py4gw/gui/constants.py` is:

```text
python tools/generate_gwa3_constants.py
```

It reads `Global Const $NAME = <expression>` from `external/GwAu3/API/Constants/*.au3`,
resolves each expression (`BitOR` and friends evaluated, `$` references resolved), and writes
one section per source file with a provenance header naming the file. **The `$` is dropped**,
as in the GUI layer, so an AutoIt line `$GC_I_ALLEGIANCE_ENEMY` reads
`GC_I_ALLEGIANCE_ENEMY`. GwAu3's naming scheme is preserved rather than reinterpreted:
`$GC_I_*` integer, `$GC_S_*` string, `$GC_AI_*` array of integers, `$GC_AS_*` array of
strings.

Provenance and licensing follow the rule already in `AGENTS.md`: GwAu3 is MIT (`LICENSE`,
`Copyright (c) 2025 JAG-GW`), the copied surface is kept minimal (names and values, which is
the whole content of a constant), and the provenance record names the source path and the
pinned revision.

### Built, and what building it established

**State: done and verified offline.** 7,480 constants from the 34 constant-carrying files;
`tests/test_gwa3_constants_offline.py` (15 tests) passes with no client and no elevation, checking
completeness **in both directions** against the source files â€” every `Global Const` present under
GwAu3's name, and no name declared that GwAu3 does not. Output is 1.0 MB and regeneration is
byte-identical, so a diff on that file is a meaningful signal.

Four facts about the source that only surfaced by building the generator, and that a hand-written
constant table would have got wrong:

1. **There are four array families, not two.** Beyond `$GC_AI_*` (array of int) and `$GC_AS_*`
   (array of string) the source has **2-D** tables under `$GC_AI2_*`, `$GC_AM2_*` and `$GC_AMX2_*` â€”
   `$GC_AM2_HERO_DATA[40][2]`, `$GC_AI2_ALL_ATTRIBUTES_BY_PROFESSION[10][6]`, and
   `$GC_AMX2_SKILL_DATA[3476][30]`, which is the largest single value in the surface. An earlier
   extraction of the surface missed all eight of these declarations, because a rule looking for
   `$NAME[n]` does not match `$NAME[n][m]`.
2. **Dimensions can be symbolic.** `$GC_AMX2_SKILL_DATA` is declared
   `[$GC_I_SKILL_DATA_ROWS][$GC_I_SKILL_DATA_COLUMNS]`, so a dimension has to be evaluated the same
   way an initialiser is.
3. **A declaration's dimension count includes the element itself** â€” `[40][2]` is 40 elements of 2,
   not 40 of 2 of 1 â€” which decides how the rows a source writes are folded back into the declared
   shape. Getting this wrong silently transposes a table.
4. **Some declarations do not fill their own dimensions.** Seven, all reported by the generator and
   recorded in the generated module's own header:

   | Declaration | Declares | Values written |
   | --- | --- | --- |
   | `$GC_AI_EL_TONICS` | `[68]` | 67 |
   | `$GC_AI_MONSTER_TROPHIES` | `[188]` | 187 |
   | `$GC_AI2_ALL_ATTRIBUTES_BY_PROFESSION` | `[10][6]` | rows of 6 **and** 5 (ragged) |
   | `$GC_AI2_SECONDARY_ATTRIBUTES_BY_PROFESSION` | `[10][5]` | rows of 5 **and** 4 (ragged) |
   | `$GC_AI_EVENT_ITEMS`, `$GC_AI_QUEST_ITEMS`, `$GC_AI_REWARD_TROPHIES` | `[]` | a list â€” `[]` is not valid AutoIt |

   **The values are copied, not the declaration.** Padding a short array to its declared length would
   invent a value the source does not contain, and AutoIt does not enforce the bound either, so a
   caller iterating to the declared length reads past the end in GwAu3 for the same reason. The
   mismatches are reported on every run and written into the module header so they cannot be lost.

The generator also carries the lesson from the incomplete surface index: it does not fail on a
declaration it cannot resolve, it **names** it. Exit is non-zero and the location is printed, because
a constant silently dropped is a name a migrated script would call and not find.

## The AutoIt bridge: what an AutoIt script can and cannot do

This is the part that decides the architecture, so the limits are stated before the design.

Py4GW's own `multiboxing_enums.py` and Reforged's multiboxing layer are *not* an AutoIt
bridge and say nothing about one â€” the reader should not go looking there for the answer.
The limit is a property of AutoIt: its interop is Win32 and COM (`DllCall`, `ObjCreate`,
`Run`), and a Python library is neither a DLL export table nor a COM server. So there is no
"binding" in the sense of calling into the library â€” there is a **bridge**: a channel an
AutoIt script talks over, and a Python side that answers.

Three consequences shape everything else:

1. **The Python side must be long-lived, and there must be exactly one of it per client.**
   A one-shot controller per call cannot work. `py4gw.connect()` is a *write*: it installs
   the capability layer â€” hooks on the client's game thread and message sender, the shared
   block, the dispatcher and a listener thread â€” and `disconnect()` takes it all back. Paying
   that per call would be absurd, and the queue state it owns is what makes a game-thread
   call land at all. On top of that, the selected client is **process-global**:
   `connect()` calls `disconnect()` first and publishes one `ConnectedClient`
   (`py4gw/client.py:1894-1912`), and every ported accessor reads through
   `require_client()` (`py4gw/client.py:1937`). So **one worker process serves one client,
   and multi-boxing is one worker per client.** That is the port's own model and this layer
   does not redesign it â€” inventing a per-instance connection registry to make one worker
   serve several clients would be exactly the kind of new layer the porting rules forbid.

2. **The channel is a named pipe.** It is the documented Win32 mechanism for this, AutoIt
   has `_NamedPipes_CreateNamedPipe` in its standard library (`NamedPipes.au3`, which the
   GwAu3 tree already includes at `API/_GwAu3.au3:113`), and the GwAu3 launcher already spawns
   a bot as a separate process with `Run()` (`Scripts/Multi-Launcher/GwAu3 Multi-Launcher.au3:869`)
   â€” so an AutoIt script driving an out-of-process worker is a shape that audience already
   has. (The alternative, `Run` + `StdinWrite`/`StdoutRead`, is workable â€” it is what the
   community uses for AutoIt-to-Python â€” but it is a single byte stream shared with whatever
   the worker prints, so it cannot carry a request and its result apart from any stray output.
   A pipe gives the protocol a frame of its own.)

3. **The bridge carries the layer, and the layer is where the logic is.** The bridge must
   not become a second implementation. It carries **one request and one reply per call**,
   addressed by GwAu3's own function name:

   ```json
   {"call": "Agent_GetAgentInfo", "args": [-2, "X"]}          ->  {"ok": true, "result": 1234.5}
   {"call": "Agent_GoNPC",        "args": [42]}               ->  {"ok": false, "error": {"kind": "refused", "reason": "..."}}
   ```

   Four properties make that safe to build on:
   - **The name is data, not dispatch.** `{"call": ...}` is looked up by name at the bridge,
     which is the one place name-dispatch is correct: the name arrives from AutoIt as a
     string. *Inside* the layer, no member reaches a field through a dynamic name â€” the
     field-name arguments (`"X"`, `"Name"`) are GwAu3's own contract and are resolved by the
     same explicit `if`/`elif` chain GwAu3's `Switch` is, never by `getattr`.
   - **The reply says which kind of failure it was.** `not_implemented` (no route yet, naming
     the capability), `refused` (a safety rule, naming it), `blocked` (a written precondition
     failed), `error` (the game or the OS said no, with the message intact). An AutoIt script
     can therefore tell "not built yet" from "you asked for something this project will not
     do" â€” a distinction the ported classes already make for their own callers.
   - **The protocol is transport-independent.** Line-delimited JSON over the pipe means the
     framing is separate from the payload, so the same protocol works over stdio for a
     throwaway probe. That is the test story below.
   - **It is deliberately not a general eval channel.** There is no "run this Python" entry,
     no attribute path, no expression. The address space is the ~660 names.

### The AutoIt-side library, and whose code it is

The GwAu3 API files are **MIT-licensed** (`external/GwAu3/LICENSE`, `Copyright (c) 2025
JAG-GW`), so the two options below are both legally open. They are not equivalent in effort
or in what they promise, and this is a decision for the owner rather than a fact the source
settles:

- **Option A â€” route GwAu3's own files over the bridge.** Keep `API/Modules/*.au3` as
  shipped, and replace the narrow layer underneath them (`Memory_Read`, `Memory_Write`,
  `Core_Enqueue`, `Core_SendPacket`, `Core_PerformAction`, the pointer globals) so GwAu3's own
  functions run unchanged and each one's `DllCall` becomes a bridge request. The wrappers are
  already written â€” by GwAu3 â€” so this is the smallest new surface, and the caller-facing half of
  the layer (the field-name resolution, the sentinels, the return shapes) comes for free because it
  is already written and already right. It costs a provenance record and shipping a third party's
  files, and it means the safety rule is enforced at the primitive (`Core_SendPacket` refuses,
  `Core_Enqueue` forwards) rather than per function â€” which is a *smaller* surface to get right than
  113 individual decisions.
- **Option B â€” a Stealth-owned AutoIt UDF.** Write our own `Stealth_GwAu3.au3` that exports the same
  function names as thin clients of the bridge, with our own header. Nothing of GwAu3's is
  redistributed. It costs re-declaring the signatures in AutoIt â€” mechanical from the same
  extraction the route map comes from, and only for the routines a script calls â€” but it is our
  surface to maintain, and a GwAu3 signature that changes upstream is ours to notice. It also
  duplicates the caller-facing half of Option A by hand, which is where Option A's real advantage
  lies.

A migration this size is worth doing in a fixed order, and each step leaves something that
works. **The order is by what a script touches, not by GwAu3's file list** â€” that is the corrected
scope applied to the plan:

| Step | What lands | Gate | State |
| --- | --- | --- | --- |
| 1 | `tools/generate_gwa3_constants.py` â†’ `py4gw/gwa3/constants.py` | the 7,480 names match the `.au3` sources name for name, in both directions; nothing else to judge | **done** â€” 15 offline tests pass, regeneration is byte-identical |
| 2 | The route map for the **228 called routines** â€” tier, GwAu3 citation, and the backing member for each ROUTED row | every row tiered with its evidence; the ~108 packet rows each decided individually | **maps generated** â€” 992 functions tiered, **103 routes recorded** with their Stealth line (the seven read families among them, routed to `py4gw/gwa3/` itself, and the twenty-two rows of `UtilityAI_GetAgent.au3`); the remaining rows are named work |
| 3 | The **read surface**: the seven field-name accessors and their families, which is where most call sites live | the census's top functions answer with GwAu3's types and sentinels, offline, against the structures this project already reads | **eight families done, `Friend` included** â€” all **400** declared keys are in the tables: **350 answer a value and 50 refuse** naming their rule â€” `Agent` (143 declared, 139 answer), `World` (79, 49), `Skill` (63, 63), `Map` (40, 40), `Item` (39, 35), `Quest` (22, 16), `Party` (14, 8), `Friend` (22) â€” the last of them the one whose offsets disagree, so its table is the one whose refusals are the finding; the current test count is in *Where the build stands* below |
| 4 | The **action surface**: the `Cmd` functions a script calls â€” **113 by the census**, of **183 declared** | each action reaches the client by a route already ported, or refuses naming its rule | **three modules done** â€” `cmd_agent` (13), `cmd_chat` (3) and `cmd_map` (14) present **30 of the 183**; of those 30, **27 route and 3 refuse** (`Agent_MakeAgentArray`, `Map_InitMapIsLoaded`, `Map_MapIsLoaded` â€” `Agent_CancelAction` was the fourth and is routed as of *the control-action route*). **153 declared `Cmd` functions remain** across 15 modules |
| 5 | The worker and the pipe protocol | a request over a pipe returns a value read from a live client, and a `REFUSED` row returns `refused` | **worker and protocol done, over stdio** â€” 28 offline tests and a live AutoIt run. The **pipe** is not built: stdio carries the protocol because the worker keeps its own output on stderr, and that is a discipline rather than a frame. A live-client run is still outstanding |
| 6 | The AutoIt-side library (Option A or B) | an unmodified GwAu3 example script runs against Stealth | **Option B built** â€” `tools/autoit/Stealth_GwAu3.au3`, **1,064** wrappers generated from GwAu3's own signatures, **340 implemented**; 13 interpreter checks pass. An *unmodified* script has not been run against a live client |

Step 3 before step 4 is deliberate: the reads are mechanical and offline-testable, so they land with
no live client and no risk, and they are also what a script touches most. The actions are where the
per-function decisions are.

**Where the build stands, measured at this writing.** Nothing below is a claim about the running
client, because no routine in this package has ever been executed against one:

- `py4gw/gwa3/constants.py` â€” 7,480 names, generated and byte-identical on regeneration.
- Read surface â€” **eight families, complete**: `Agent` (143 keys), `World` (79), `Skill` (63), `Map`
  (40), `Item` (39), `Quest` (22), `Party` (14) and **`Friend`** (22 across its own accessors).
  `data_party` gained the file's **member accessors** (2026-10-10) â€”
  `Party_GetMyPartyInfo`, `Party_GetMyPartyPlayerMemberInfo`, `Party_GetMyPartyHeroInfo`,
  `Party_GetMyPartyHenchmanInfo` â€” carried from `tools/gwa3_snippets/data_party_my_party.py` over the
  port's own member records, and the five keys that used to refuse because they read *through* the
  context's `player_party_ptr` now **answer**: the pointer is followed
  (`PartyContextStruct.player_party`), so `PlayerCount`/`HenchmenCount`/`HeroCount`/`OtherCount`/
  `PlayerPartyID` read the party record's own fields and `TotalPartySize` â€” which sums three of them â€”
  answers instead of refusing. Live: the counts equal `Party.GetPlayers()`/`GetHeroes()`/`GetHenchmen()`/
  `GetOthers()` and `PlayerPartyID` equals `Party.GetPartyID()`. What still refuses there is what
  answers a **client address** (the four `Array*PartyMember` keys, `MyPartyPtr`) and
  `Party_GetHeroFlagInfo`, which needs the world's hero-flag array read element-wise.
  `Friend_GetFriendInfo` is the last accessor this census names, so the read half is done. The `Friend`
  family carries a finding the other seven do not â€” see *The `Friend` family* below.
- Action surface â€” **all eighteen `Cmd_*` modules**: `cmd_agent`, `cmd_attribute`, `cmd_chat`,
  `cmd_cinematic`, `cmd_effect`, `cmd_friend`, `cmd_game`, `cmd_guild`, `cmd_item`, `cmd_map`,
  `cmd_merchant`, `cmd_other`, `cmd_party`, `cmd_quest`, `cmd_skill`, `cmd_title`, `cmd_trade` and
  `cmd_ui`, presenting **221** of GwAu3's declared `Cmd` functions. Each module is complete for itself:
  every function is either routed or refuses naming the rule and the work.
- `UAI_*` surface â€” **six modules carry it so far**, and each names what it does not do: `uai_utils.py`
  (13 arithmetic and profession helpers), `uai_agent.py` (the cache-column accessors over live reads,
  77 of 88 columns routed and three refused as a GwAu3 disagreement), `uai_effects.py` (9, presence
  routed and timing refused), `uai_filter.py` (all 64 predicates), `uai_get_agent.py` (all 26 targeting
  and positioning functions) and `uai_const.py` (the plugin's mutable settings, of which
  `$g_i_FightMode` is the one ported modules read today).
**`GwAu3_Data_Skill.au3`'s skillbar reader landed 2026-10-10** â€” the last read the slot loop needed.
`Skill_GetSkillbarInfo` (``:210-304``) is a stride walk over the **world's** skillbar array (``0xBC`` per
skillbar, ``0x14`` per slot, matched on the skillbar's agent id), and this project's structures are those
two strides exactly (`SkillbarStruct` ``0xBC``, `SkillbarSkillStruct` ``0x14``), so all seventeen keys
answer from the port's own read; `Skill_GetSkillTimer` (``:11-14``) is the client's own clock
(``client.memory_manager.GetSkillTimer``), which is why the two recharge keys are the source's signed
arithmetic rather than a refusal. **Two of the seventeen are unreachable in GwAu3 itself**:
``SlotBySkillID`` and ``HasSkillID`` take a *skill id* in the slot parameter, and the guard above the
``Switch`` rejects anything outside ``1..8`` before their ``Case`` (``:217``) â€” kept as written, so they
answer ``0`` here exactly as they do there, and recorded on the member rather than "fixed".

**MEASURED AND RESOLVED (2026-10-10): the layer was right, the first version of the test was wrong.**
The live comparison reported a one-slot shift in the `SkillID` column; a read-only probe
(	ests/live_reports/skillbar_slots.log) dumped the matched skillbar's dwords and settled it in one run:

* the client puts the ids at `+0x10 + k*0x14`, and they are `[330, 2107, 0, 1506, 343, 336, 3426, 0]`;
* the port's own slot records agree **slot for slot**, including the two empty slots;
* the layer's column is exactly that list -- so there was never a shift in the layer;
* **SkillBar.GetSkillbar() drops the empty slots** (its own body appends only non-zero ids,
  py4gw/skillbar.py:995-1005), which is what the test had compared positionally against an eight-slot
  column. The compaction rule is now asserted *as* a rule, against GetZeroFilledSkillbar for the
  positional comparison.

So the skillbar reader is **live-verified**: 28 of 28 live tests pass, with the layer's column equal to the
client's own slot records and GetSkillbar() equal to that column with the empty slots dropped. The
lesson is recorded because it is the second of its kind in this suite -- a live check is only as good as
the pair of things it compares, and a *compacted* view is not a positional one.

- Bridge â€” the worker and the line-delimited protocol, over stdio; **479 routines on `py4gw/gwa3`'s own
  hand-written surface** (the forty modules that are neither the constants table nor the generated
  dispatch and strategy tables); the named pipe not built.
- AutoIt â€” `tools/autoit/Stealth_GwAu3.au3`, **5,629 wrapper declarations** covering every function
  GwAu3's own scripts call, **5,003 of them with a wrapper that reaches the layer**, plus the 7,480-name
  constant table, GwAu3's 150 standard UDL includes and 11 hand-written `Log_*`/`Core_*` functions; 13
  interpreter checks pass.
**THE RANKING IS MEASURED, AND IT IS BOUNDED (2026-10-10).** The two files behind every per-skill
decision -- UtilityAI_BestTargetCache.au3 (4,606 lines) and UtilityAI_CanUseCache.au3 (4,593) -- turned
out to be **pure dispatch tables**: one function each, a `Switch` over the slot's skill id, 2,300 and
2,292 `Case` lines that `Return` a **strategy function's name as a string** (GwAu3 resolves it with
AutoIt's `Call`). No arithmetic, no reads, no decisions. Both are now **generated whole** from the source
(	ools/generate_gwa3_ranking.py -> py4gw/gwa3/uai_best_target_cache.py, uai_can_use_cache.py): every
case, every constant resolved through the generated constants module, in the source's own order, with the
two lookups answering GwAu3's own strings and `"` for an empty or unknown skill (the source has no
`Case Else`).

What those names point at is the remaining work, and the same census bounds it: **4,551 strategy functions**
(BestTarget_*, CanUse_*) in API/Plugins/UtilityAI/Skills/, **20,115 lines**, with only **283 distinct
bodies**:

| shape of the body | functions |
| --- | --- |
| `Return` + one call | **1,934** |
| `If Anti_X() Then Return False` (17 predicates) | **1,784** |
| a literal (`True`/`False`/`0`/`1`) | **404** |
| three lines or fewer | 130 |
| longer | 299 |

Eight bodies alone cover 3,300 functions (the largest is `Return UAI_GetPlayerInfo()`,
1,125 times). So the ranking is **not** 300 KB of unique logic: it is two generated tables, 17 `Anti_*`
predicates and 283 bodies -- each of which resolves to primitives this layer already ports
(UAI_GetNearestAgent, UAI_GetAgentLowest, UAI_GetPlayerInfo, UAI_GetBestSingleTarget,
`_ApplyFilters`). The next work item is a generator for those bodies, with the ones it cannot transcribe
refusing by name. The shared dependency of those 1,784 anti-guard bodies is measured too: **21 `Anti_*` predicates**
(18-26 lines each, in `Skills/UtilityAI_*.au3`), built on UAI_PlayerHasEffect, UAI_GetPlayerInfo and
UAI_GetAgentInfoByID -- all ported -- plus `UAI_GetPlayerEffectInfo`, `Party_GetPetInfo` and the
`` global, which now exists in py4gw/gwa3/uai_const.py with the source's own initial
values and a test that reads them out of `UtilityAI_Const.au3`. Four of the 21 are not referenced by
either table.

**THE STRATEGIES LANDED (2026-10-10): all 4,572 generated, 4,505 transcribed, 67 refusing.**
`tools/generate_gwa3_strategies.py` reads every ``BestTarget_*``/``CanUse_*``/``Anti_*`` body out of
``Skills/`` and transcribes it statement by statement -- AutoIt's statement shapes and its operators, with
the ternary rewritten -- into 21 per-file modules plus `py4gw/gwa3/uai_anti.py` (the 21 predicates, one
module so the import graph stays acyclic). **Nothing is re-derived**: a strategy's content is the
source's, which is why the unit is a transcription with a refusal for whatever it cannot read.

Three checks make a generated body safe to run, and each of them caught a real defect:
**a body that calls a name this layer does not implement refuses instead of raising ``NameError``**; **a
body that names a ``GC_*`` the constants module does not carry refuses instead of raising
``AttributeError``**; and **every module is imported by the test suite**, which is how the generator's own
defects surfaced -- a `NameError` from an unimported `Anti_*`, a module importing itself, and a write that
went to `uai_strategy_attack` **without `.py`** while reporting success (the currency test compares the
files on disk with what the generator produces, and it is the check that exists for exactly this).
Generation is deterministic: two consecutive runs produce identical bytes.

**And the tables have a gap of GwAu3's own, recorded here because it is not this layer's to fill**: the two
dispatch tables answer **220 names that `Skills/` never defines** -- 77 ``*Pvp`` variants
(`BestTarget_AegisPvp`) and 143 monster, quest and explosion skills (`BestTarget_Bamph`,
`BestTarget_FirebombExplosion`, `BestTarget_JununduTunnelMonsterSkill`). GwAu3's engine ``Call``s those
names and finds nothing, so its ranking has no strategy for those skill ids either; this layer answers the
same name the table answers. The engine's **refresh layer** landed with it: py4gw/gwa3/uai_cache.py ports all six members of
Cache/UtilityAI_Cache.au3 -- the two form-change paths and the runtime reset routed, the two cache
updates NOT APPLICABLE with the reason (the rows they refill are read live here), and the one armed branch
($g_b_CacheWeaponSet) calling UAI_DetermineWeaponSets, the port of Equipment/UtilityAI_WeaponSets.au3
(see *the four weapon sets* below). Map_GetInstanceInfo (GwAu3_Data_Map.au3:32-49), which Cache_SkillBar and UAI_Fight both
gate on, is ported into data_map.py over Map.GetInstanceType with the source's own three comparisons.

The **cast gate** landed next: `py4gw/gwa3/uai_can_cast.py` ports `UAI_CanAutoAttack`,
`UAI_IsCastSensible` and `UAI_CanUse` -- the member that prices a slot in health, overcast and energy with
every modifier GwAu3's build knowledge applies, including the two asymmetries its own code has (the
adrenaline branch answers before any energy is priced; the clamp's floor is one, and only *Way of the
Empty Palm* zeroes it). **`UAI_CanDrop` is ported too** -- fifteen item-spell algorithms, several of them
the same shape (count what the drop would hit; if there is not enough, walk toward it and watch the count),
written out one by one as the source writes them, because **the repetition is the port**. So
`uai_can_cast.py` is complete for its file: `UAI_CanAutoAttack`, `UAI_IsCastSensible`, `UAI_CanUse` and
`UAI_CanDrop`, with the private effect-timing helper they share. Two divergences are recorded on the
members that carry them: the
stance/glyph/preparation branches of `UAI_IsCastSensible` scan the player's effects for a matching type
because GwAu3's `UAI_PlayerHasEffectType` returns its skill id through AutoIt's ``@extended`` and this layer
has no out-of-band return; and the whole module uses the **declared** constant spellings
(`GC_I_SKILL_ID_DIVINE_SPIRIT`), because GwAu3's plugin files reference them in mixed case and AutoIt matches
case-insensitively -- thirty of them did not resolve until the first test run said so.

The **cast chain** landed next, and it is the engine's core: `py4gw/gwa3/uai_core.py` now ports
`UAI_TryUseSkill` (the slot's target from the `BestTarget_*` ranking, the forced-target override, the
`CanUse_*` strategy, the distance gate, then the cast), `UAI_PrioritySkills` with its `@extended` slot
carried by a private `_priority_skill_used`, `UAI_UseSkillEx` (target change, CALL-mode announcement, the
three instant-cast tests, the idle wait, the cast through the client's own `SkillBar.UseSkill`, and the
cast-start and cast-end waits), and **`UAI_GetIsIdle`/`UAI_GetIsCastingSkill`, which used to refuse**: the
casting word they need is the skillbar's cast-array size, which this layer reads through
`Skill_GetSkillbarInfo`'s ``Casting`` key -- the pointer the refusal named was never needed. The strategy
dispatch resolves the ranking's **names** through this layer's surface, exactly as `_ApplyFilters` resolves
the filter strings. `UAI_UseSkillEx`'s mid-cast cancel (GwAu3's `Core_ControlAction`) **now runs**: it is
the client's own cancel control action, which the layer presses -- see *the control-action route* below.
**And UAI_Fight itself
is ported** -- the engine a script calls: the mode and bookkeeping set, the
player-number argument split into a priority list and an avoid list, the priority target found, and the
loop that ends on any of five conditions (distance from the fight origin, a wiped party, a dead player, a
map or instance-type change, or the caller's own exit callback, resolved by name as AutoIt's Call does).
UAI_DropBundle and UAI_AutoAttack are ported with it, and UAI_UseSkills too, so **every member of
UtilityAI_Core.au3 now answers**, with both of its cancels performing the client's control action --
and the three armed weapon-set branches run
since `Equipment/UtilityAI_WeaponSets.au3` landed (see the section below), including the switch itself,
`UAI_ChangeWeaponSet`, which presses the client's weapon-set control action. The four Party_* helpers that
UAI_Fight's wipe check needs (Party_GetMembersArray, Party_GetAverageHealth, Party_GetAvailableRezz,
Party_IsWiped) landed with it in uai_utils.py, and Map_GetMapID (GwAu3_Data_Map.au3:234-236) with
them.

**THE FOUR WEAPON SETS LANDED (2026-10-10): `Equipment/UtilityAI_WeaponSets.au3`, all eighteen
functions, in `py4gw/gwa3/uai_weaponsets.py`.** This was the last unported file the engine reached, and
it is the file that decides *what the character is holding* while it fights. Three pieces:

* **The analysis** -- `UAI_DetermineWeaponSets`, `UAI_SaveWeaponSetFromMemory`,
  `UAI_FindAndSaveModFromMemory`, `UAI_SearchModsInArray` and the two bonus readers. The four sets'
  weapons are pointers in the client's own inventory struct and their mods are the bytes at the end of
  each item record, so all of it is reads -- and the mod analysis is the reason the file exists: it
  searches an item's raw mod bytes for the byte sequence of each known upgrade (`DE016824` is Barbed,
  `001E4823` a Fortitude grip), strikes what it finds out of the working string so a later row cannot
  match the same bytes twice, and scores the mod with **the source's own weights** (Sundering 20,
  Vampiric 15 and its flag, Zealous 10, Furious 10, a `+33%` condition 5, `Damage +15%` 15, `Armor +` 10,
  `armor vs` 7, `Damage -` 5, `-20%` 3, HCT20/HSR20 20, HCT10/HSR10 10, `Enchantment Duration` 20) into
  the row's offensive, defensive, casting and enchant scores and its HP/energy totals.
* **The decision** -- `UAI_GetBestWeaponSetForCombat` (three priorities and a hysteresis pair whose
  *code* is ported: enter defensive at `<= 0.30`, leave at `>= 0.50`; enter low energy at `<= 5`, leave
  at `>= 25`, while the comments above them say 50/70 and 15/35), `UAI_GetBestWeaponSetBySkillSlot` (the
  skill's own type chooses the tracker, with the source's two exceptions for attacks and enchantments),
  `UAI_FindWeaponSetByType`, `UAI_ShouldSwitchWeaponSet` and `UAI_GetWeaponSetForSituation`.
* **The switch** -- `UAI_ChangeWeaponSet`, which **runs**: a double `Core_PerformAction` cancel and then
  the switch action, repeated 32 ms apart until the client reports the set or the source's own 400 ms
  deadlock expires. The two cancels and every switch are the client's own control actions
  (`$GC_I_CONTROL_ACTION_CANCEL_ACTION`, `0xAF`, and `$GC_I_CONTROL_INVENTORY_ACTIVATE_WEAPON_SET_1..4`,
  `129`-`132`), and this layer presses them -- see *the control-action route* below. The
  already-on-this-set quick check in front of it is the source's own, so asking for the set the player is
  on costs nothing.

**Two findings came out of the source's own text, and the live probe measured both.** GwAu3's
`Item_GetModStruct($a_v_Item)` hands its argument to a reader that treats it as an **address**
(`GwAu3_Data_Item.au3:776-781`) while its weapon-set caller passes an **item id**
(`UtilityAI_WeaponSets.au3:107-119`) -- its merchant caller, by contrast, passes a *pointer*
(`GwAu3_Cmd_Merchant.au3:60`). `tests/probe_gwa3_inventory_live.py` (read-only, elevated, pid 19696,
2026-10-10; log in `tests/live_reports/gwa3_inventory.log`) measured what follows from that, and it is
worth stating in the source's own terms rather than in the port's:

* **the inventory route works and holds what the source says it holds** -- `active_weapon_set=3`,
  2064 gold on the character, and eight weapon/offhand pointers that resolve to real item records
  (item 6096 type 2 axe in sets 1 and 2, item 3813 type 24 shield in sets 2 and 4, item 122 type 5 bow
  in set 3, item 94 type 2 axe in set 4, two null offhand slots);
* **every one of those records is also in the bag walk** -- `read_item_records()` answered 341
  records, all 341 with an address, and every weapon-set item's id and address is among them, which is
  what makes this layer's `Item_GetItemInfoByPtr(record, ...)` (which re-resolves by id) answer
  correctly for a weapon-set item;
* **``id + 0x10`` is not readable on this build** -- all eight tries failed with Windows error 299
  (`ERROR_PARTIAL_COPY`), so GwAu3's own analysis reads a failed buffer there and finds **no mods at
  all** when it is handed an item id: its per-set mod scores stay at the zeros the source resets them
  to, and only ``HasShield`` (from the offhand's type) survives.

This layer resolves the item its caller holds instead, so the port's analysis reads the record's real
mod array. That is a **divergence, recorded rather than hidden**: from the character's own bytes the
port finds ``Fiery`` + ``Dance with Death`` on the axe (offensive 15), ``Shield Handle of Endurance`` +
``Run For Your Life!`` on the shield (45 health, defensive 50), ``Crippling`` + ``Bow Grip of Shelter``
+ ``To the Pain!`` on the bow (offensive 20, defensive 7, ranged) and ``Zealous`` + ``Axe Grip of
Fortitude`` + ``Strength and Honor`` on the second axe (offensive 25, 30 health, the zealous flag) --
where GwAu3's own run would score nothing. Those live rows are asserted in
`tests/test_gwa3_uai_weaponsets_offline.py`, so the weights are checked against bytes the game wrote.
The choice is the source's own evident intent (its merchant caller passes a pointer, its tables exist
to score mods) against its literal call, and it is recorded here for the owner rather than settled
silently. And `UAI_SearchModsInArray`'s two `ByRef` out-parameters are Python-inexpressible, so the
member **returns them as a pair** -- the same documented twin this layer uses for `@extended`.

**The state arrived with its reader**: the 2-D set table, the ten best-set trackers, the mod-name table
and the two hysteresis flags now live in `py4gw/gwa3/uai_const.py` where `UtilityAI_Const.au3` declares
them, and the file's fourteen mod tables (298 rows) are transcribed there **row for row** --
`tests/test_gwa3_uai_const_offline.py` parses the source's own region and compares every row, because
transcription is where a silent mistake lives.

**The datum for AutoIt's string semantics was measured, not assumed** (`tests/scratch/_probe_modstruct.au3`,
`_probe_regexp.au3`): `StringInStr`/`StringReplace` are case-insensitive, a ``Byte[n]`` read answers a
binary whose text form is ``0x`` plus upper-case hex (18 characters for eight bytes), and
`StringRegExp(..., 1)` answers the **capture group**, which is why `UAI_ExtractHPBonus("Health +30")` is
30 and not 0.

**And the live suite was re-run over the whole layer after this work** (read-only, elevated, pid 19696,
2026-10-10): **28 of 28 tests pass**, with the client's code-section digest identical before and after
the connection (`53b3c20b9541f72a…`, `0x539400` bytes) -- so nothing in the layer changed the client.

### The control-action route: GwAu3's action queue, and the press that replaces it (2026-10-10)

**GwAu3's third channel, and this project's answer to it.** The layer had two kinds of refusal for
actions -- a forged packet (`Core_SendPacket`) and GwAu3's injected queue (`Core_Enqueue`) -- and three
effects were stuck behind the second one: the UtilityAI weapon-set switch, the engine's two mid-cast
cancels, and the held-bundle drop. Reading GwAu3's own stub for that queue is what moved them:

* `Core_PerformAction($a_i_Action, $a_i_Flag, $a_i_Type = 0)` fills a record whose first word is a
  **function pointer** (`$g_d_Action = DllStructCreate('ptr;dword;dword;dword')`,
  `GwAu3_Const_Core.au3:15`; the pointer comes from `Memory_GetValue('CommandAction')`,
  `GwAu3_Core.au3:452`) and enqueues it (16 bytes) into the client's queue with `WriteProcessMemory`
  (`:559-573`). The injected stub that record points at is `GwAu3_Core_Assembler.au3:2101-2118`, and
  what it does is **a real client call**: it reads the record's *type* word to choose between two action
  tables (`ActionBase+4` and `ActionBase+0xC`), adds `0xA8`, and calls the client's `Action` there as
  ``Action(flag, &action, 0)`` -- `this` in ECX, a zero in EDX, three stack words. So GwAu3's third
  channel is a code cave plus a call on the client's action table, and **this project places no code cave
  and calls no such table**: the flag and the type are real arguments there, and nothing here reproduces
  its addressing.
* **The effect, however, is a control action, and this project has a route for control actions.** Every
  caller of `Core_PerformAction`/`Core_ControlAction` in GwAu3's API and its plugins passes a
  `$GC_I_CONTROL_ACTION_*` code (the weapon-set codes 129-132, the cancel 0xAF, the held-bundle drop
  0xCD) -- the client's own control-action set, which is the same set this port's
  `enums_src/ui_enums.py` carries. Reforged performs exactly these actions **by pressing them**:
  `Keybinds.PressKeybind(keybind_index, 75)` (`routines_src/yield_src/keybinds.py:15-17`) holds
  `UIManager.Keydown(keybind_index, 0)` down for the tree's own 75 ms and then releases it with
  `UIManager.Keyup(keybind_index, 0)` (`routines_src/behaviourtrees_src/keybinds.py:101,119`), and the
  client's packet is a one-word key action sent to its own button-action frame
  (`ui_methods.cpp:1408-1411`; `KeyActionPacket`, `include/GW/context/ui.h:288-292`). That is the pair
  `py4gw/map.py:1013-1014` already ports for the mission map, so the route was in the port before this
  work -- what was missing was the *decision* that these GwAu3 effects belong on it.

**What the layer does now, and what it refuses.** `Core_PerformAction` presses `a_i_Action` through
`UIManager.Keydown`/`Keyup` with frame `0` (the client's own button-action frame), and `Core_ControlAction`
forwards to it with its own default flag. The two words the key-action packet has no room for are
**refused by name** rather than dropped: `$GC_I_CONTROL_TYPE_DEACTIVATE` (`0x22`, which only GwAu3's
DevTools screen uses) and a non-zero type (the second action table). On that route, four members moved
from refusing to answering -- `Item_DropBundle` (Reforged's `Keybinds.DropBundle`,
`ControlAction_DropItem`), `Item_SwitchWeaponSet` and `UAI_ChangeWeaponSet` (Reforged's
`Keybinds.ActivateWeaponSet`, `ControlAction_ActivateWeaponSet1 + index - 1`), and `Agent_CancelAction`
(Reforged's `Keybinds.CancelAction`) -- and with `UAI_ChangeWeaponSet` answering, the UtilityAI engine's
weapon-set branches run. The route map's totals moved with them: **223 ROUTED / 30 REFUSED / 24 NOT
APPLICABLE / 715 NO ROUTE YET** of 992 declared, and the plugin's own 145 rows stand at **121 ROUTED /
4 REFUSED / 20 NOT APPLICABLE**.

**Two divergences ride with the route, and both are recorded on the member rather than smoothed:**

* **the flag and the type are not carried** (above). Every API and plugin caller passes the activate
  flag and the default type, so the domain the layer answers is exactly the domain GwAu3's own code uses;
  the two values outside it refuse.
* **the 75 ms hold between the press and the release has no home here.** Reforged's hold is a behaviour
  tree's `aftercast_ms` and this project carries no behaviour tree and no per-frame scheduler; the press
  is made down-then-up, which is what the client acts on. `py4gw/map.py:1001-1006` records the same
  finding for the same pair.
* **`Item_SwitchWeaponSet` answers `False` for a set outside `1..4`**, because Reforged's own guard rides
  with the only route there is (`0x80` is `ATTACK_INTERACT`, not "set zero"); GwAu3 sent the number
  through a packet regardless. That single answer is the divergence, and the member says so.

**Verified where it can be, and honest about where it is not.** Offline, `tests/test_gwa3_core_offline.py`
asserts the press (the action word, frame `0`, the two refuses); `tests/test_gwa3_cmd_item_offline.py` and
`tests/test_gwa3_uai_weaponsets_offline.py` assert the four members' action codes, including the source's
own order -- cancel, cancel, then the set. **Live, the route was still unverified when this section was
written**: `tests/probe_gwa3_control_action_live.py` presses the switch through `Item_SwitchWeaponSet` and
through `UAI_ChangeWeaponSet` against the running client, reads the client's own `active_weapon_set` back
for the effect, restores the original set and reports. It is a **write** connection (`game_thread=True`)
and needs an answered elevation prompt, so it is queued rather than assumed; its result belongs in the
next revision of this section.

### The strategy generator's four new rules, and the three landmines they exposed (2026-10-10)

**The largest remaining block of the layer was not missing capability -- it was four statement shapes the
strategy generator could not read.** Measured first (`tests/scratch/_unreadable_shapes.py` prints every
refused body's first unreadable line with its source context): 34 of the 57 refusals stopped at
``For $i = 1 To $g_i_AgentCacheCount``, seven at an accumulating ``+=`` line, and the rest at a bare
``Return``, a discarded call, a ``UBound``, a ``_``-continued ``If`` and two other loops. Four rules
closed all of them:

* **the cache-count loop walks the live agent ids.** The bound is the plugin's own per-frame cache count;
  this layer keeps no cache and has no rows, so ``for $i`` becomes ``for <i> in _cached_ids()`` and the
  body's ``UAI_GetAgentInfo($i, <column>)`` reads become reads *by id* -- the substitution
  `py4gw/gwa3/uai_get_agent.py` already documents. It is safe **because the loop variable is used for
  nothing else**: all 34 bodies were checked and every use of ``$i`` is one of those reads;
* ``+=`` as a statement, a bare ``Return``, ``UBound($x)`` -> ``len(x)``, and a call whose answer is
  discarded;
* ``_`` line continuation joined **before** any rule sees a line, so ``If A And _`` / ``Then`` is one
  ``If``;
* an **inline statement** after ``If ... Then`` translated *as a statement* -- because
  ``translate_expression`` rewrites a lone ``=`` into ``==``, which is right for a condition and wrong for
  the assignment ``If $a = 0 Then $a = $b`` (``UtilityAI_EchoRefrain.au3:393``).

**Three landmines came out of that work, all of one species: a generated body that would raise at run
time instead of refusing.** Each was invisible offline and each is now a check:

1. **A refused agent column, read by transcribed bodies.** Nine bodies read ``$GC_UAI_AGENT_Distance`` --
   which this layer refuses as cache-only -- or one of the three columns GwAu3's two files disagree about,
   and would have raised inside a fight. ``Distance`` now has a **rewrite**
   (``_cached_distance(<agent>)``, the same number the cache filled) and every *other* refused column
   makes its body refuse, with the column named. The refused set is read from `py4gw/gwa3/uai_agent.py`
   rather than restated in the generator.
2. **A refused predicate was still "available".** 1,099 bodies guard on ``Anti_Attack``/``Anti_Hex``/
   ``Anti_ItemSpell``/``Anti_Spell``; the *names* were in ``uai_anti.__all__``, so the caller check
   passed and the bodies were transcribed into calls that raised inside the predicate. The anti pass now
   returns the names whose own body refused and the strategy pass treats them as unavailable.
3. **``ContinueLoop`` after an inline ``Then``** was emitted as a bare expression -- 78 lines across the
   four bodies the loop rule un-refused, every one an undefined name at run time, and pyright's
   ``reportUndefinedVariable`` found all 78.

**And the effect data pair landed with it**, because it is what the three refused predicates needed:
`Agent_GetAgentEffectInfo` (``GwAu3_Data_Agent.au3:867-911``, the agent-side effect-column reader, over
the same records `uai_effects.py` reads) and `Effect_GetEffectArg` (``GwAu3_Data_Effect.au3:3-38``, the
effect-argument reader that prices a skill by its caster's attribute level). Porting the pair un-refused
``Anti_Hex``, ``Anti_ItemSpell`` and ``Anti_Spell`` -- and with them the **805 strategy bodies** that
guard on those predicates, which had been transcribed into calls that raised. A case-insensitive constant
lookup (AutoIt variable names are case-insensitive; Python is not) un-refused ``Anti_Attack``, so **all
twenty-one `Anti_*` predicates now answer**. `Effect_GetEffectArg` is **the one ``data_*`` module written
by hand**: the family generator builds modules whose accessor switches over one record's offsets, and this
member switches over three *strings* and composes two other readers. And it carries a **divergence of
GwAu3's own**, pinned in its tests: it divides the skill table's scale ends by ``65536`` where the plugin's
``UAI_GetAgentEffectInfo`` reads them raw -- both are ported as written, and which one the client's table
holds is a live question rather than a choice this layer makes.

**The strategy result: 4,571 of 4,572 transcribed, 1 refusing** -- and the last big block fell to a
*measurement* rather than to a rule, which is the section after this one. The one that refuses is
`BestTarget_YouAreAllWeaklings`: it calls ``SetExtended``, the AutoIt channel this layer has no twin for
(GwAu3 uses it there to tell its engine to keep the forced target, and `UAI_TryUseSkill` records the same
gap on the reading side). **No transcribed body can raise**: that is checked in three ways -- the column
check, the predicate check, and pyright over the generated modules, which is clean.

**And the second-to-last one fell to the attribute family** (`GwAu3_Data_Attribute.au3`, seven members,
`py4gw/gwa3/data_attribute.py`): `BestTarget_HeroicRefrain` asked for
``Attribute_GetPartyAttributeInfo``, which is ported now with its six siblings. Three of the file's
members read the client's attribute-constant table through `py4gw/skillbar.py`'s
``get_attribute_constant_data`` -- whose `AttributeInfoStruct` names the five fields
``Attribute_GetAttributeInfo`` switches over, at the source's own offsets -- and three read the
party-attribute blocks through `py4gw/context/world_context.py`'s `PartyAttributeStruct`, which is an
``agent_id`` plus **fifty-four** ``0x14``-byte `AttributeStruct` records: **``0x43C`` exactly**, the
stride GwAu3 multiplies by. So no offset in that file is a guess, and its two point words are read at
the source's own ``0x14 * 45 + 0xB0`` because the port's structure does not name them. Two details are
kept rather than tidied: the two point *keys* are read **signed** because the source reads them with
``long`` and compares ``> 0`` (an unsigned read of the same bytes answers ``True`` for a stored ``-1``),
and the file's seventh member, ``Attribute_GetLastModified``, is **NOT APPLICABLE** -- it answers two
globals GwAu3's own attribute *setter* maintains, and setting an attribute is a client write this layer
does not perform. The live suite carries a test that checks the layer's party-attribute level for the
player against `Agent.GetAttributesDict`, which reads the same blocks by a different path.


### The model-state disagreement, settled by the porting authority and measured live (2026-10-10)

**The finding that had been left to the owner has an answer, and it was in this project all along.**
GwAu3 defines three agent predicates from the client's model state, and its own two files disagree:

| Key | ``UAI_DecodeAgentInto`` (the plugin's cache) | ``GwAu3_Data_Agent.au3`` (the Data module) |
| --- | --- | --- |
| ``IsAttacking`` | ``0x40``, ``0x60``, ``0x440``, ``0x460`` | ``0x60``, ``0x440``, ``0x460`` -- **no ``0x40``** |
| ``IsIdle`` | ``0x44``, ``0x64`` | ``0x40``, ``0x44``, ``0x64`` -- **has ``0x40``** |
| ``IsMoving`` | velocity, or ``0x4C``, ``0xCC`` | velocity, or ``0xC``, ``0x4C``, ``0xCC`` -- **has ``0xC``** |

**Reforged Native is the third source, and it is this project's authority for behaviour**, so it settles
the question rather than leaving it open: the ported `AgentLivingStruct.is_attacking`/`is_idle`/`is_moving`
(``py4gw/context/agent_array.py``) use ``{96, 1088, 1120}``, ``{68, 64, 100}`` and ``{12, 76, 204}`` --
which are exactly ``GwAu3_Data_Agent.au3``'s three sets. **The Data module agrees with the porting
authority and the plugin's own cache decoder is the outlier on all three**, so the three columns are
routed to `Agent_GetAgentInfo` (whose table was generated from the Data module) and reported as such on
the member. The comparison table stays in `py4gw/gwa3/uai_agent.py` rather than being deleted.

**Measured live, and the disagreement is not academic** (`tests/probe_gwa3_model_state_live.py`, pid
19696, 2026-10-10; ``tests/live_reports/gwa3_model_states.log``): of 43 living agents, **four held model
state ``0x40``** -- the state the two files read differently -- while 36 held ``0x44`` (idle in both),
one ``0x4C`` (moving in both) and two ``0x42`` (neither). So the choice changes the answer for about a
tenth of a full map, and **the layer's three predicates matched the ported Native members on every one
of the 43**.

**What that unblocked, and what it costs.** Seventeen strategy bodies read one of those columns and had
refused for it, some of them since they were written; they answer now, which is what took the strategy
set from 4,553 to 4,570. **The divergence that remains is GwAu3's own and is recorded rather than
hidden**: a script reading this layer's ``IsAttacking`` gets the Data module's (and Native's) definition,
where GwAu3's *plugin* would answer its cache's -- differing exactly on ``0x40``, on ``0xC``, and on an
agent whose velocity is non-zero while its model state is not a moving one. The filters and the columns
carry that note where they are defined.

**And the same reasoning retired one more refusal**: ``Distance`` was refused as cache-only, but it is the
one cache column with a live twin -- GwAu3 fills it as the distance to the *player*, and
``uai_get_agent._cached_distance`` computes that number from the same two coordinates when it is asked.
`UAI_GetAgentInfo` now answers it that way, which is the substitution the generator already applied to
every transcribed body reading it, so a script and a strategy now get the same quantity instead of one
refusing and the other working. Five cache-only columns still refuse, and each names why.

### The visible-effect family, and the plugin rows that had no route (2026-10-10)

**`UAI_AgentHasVisibleEffect` was the last plugin row with no route, and it is ported now** -- with its
five uncalled siblings, because they are the same walk. GwAu3 fills a fourth cache by walking the TList
at ``agent pointer + 0x174`` with a struct this file declares as ``dword EffectType; dword EffectID;
dword HasEnded`` (``UtilityAI_EffectsCache.au3:76-82``, ``:116-137``). This project already had that
walk: `AgentLivingStruct.visible_effects_list` sits at the same ``+0x174`` and
`AgentLivingStruct.visible_effects` reads the same 12-byte nodes -- so the mapping is field-for-field,
and the one name difference is that the port calls the first dword ``unk`` where the source calls it
``EffectType``. Six members landed in `py4gw/gwa3/uai_effects.py`: the question
(`UAI_AgentHasVisibleEffect`), its player form, the two count members and the two info members (whose
AutoIt ``[1 + count][3]`` array shape is kept, row ``0`` carrying the count, as
`Party_GetMembersArray`'s one-dimensional twin does).

**What it unblocked, and it was seven predicates plus two callers**: the seven `UAI_Filter_*` condition
predicates (Diseased, Dazed, Weakness, Poisoned, Blind, Burning, Bleeding) which had refused since they
were written, `UAI_GetBestTargetByConditionCount` -- the **last targeting query that refused**, and the
one whose refusal named this very member -- and one strategy body (`UtilityAI_PetAttack.au3:17`). Three
of the ten `UAI_Filter_*` predicates that refused before this work still do, and for a different reason
each: `IsMinion` and `IsSpirit` need the world's `NpcArray` flags word, and `IsNotAvoided` needs
GwAu3's own avoid list. The
wrong answer they refused against is still wrong: GwAu3's own comment records that the agent record's
condition bit is a *different* test from its visible-effect rows, which is why nothing was approximated
while the member was missing.

**Measured live, read-only** (`tests/probe_gwa3_visible_effects_live.py`, pid 19696, 2026-10-10;
``tests/live_reports/gwa3_visible_effects.log``), and the measurement settles the field mapping rather
than assuming it: of the client's 39 agents, twelve carried nodes -- most one ``[2, 0, 0]``, one two
(``[2, 0, 0], [1, 42, 0]``), one ``[3, 5, 0]``. That second agent is the evidence: a node whose first
dword is ``1`` (``$GC_I_EFFECT_TYPE_STATUS``) and whose second is ``42``, a status id **outside** the
seven condition ids GwAu3 filters on (23..29), so the first dword is the effect *type* and the second
the effect *id*. The live suite carries two tests for the family (29 pass, code-section digest
unchanged), and **what they do not establish** is stated plainly: no agent in that map was carrying one
of the seven condition ids, so the filter path is verified structurally (a type-1 node is matched) and
not yet against a live conditioned agent.

**And every plugin row is tiered now: 120 ROUTED, 5 REFUSED, 20 NOT APPLICABLE, none left with no
route.** The tiers moved with the code and again with the strategy work above: the eleven `Anti_*`
guards that refused were un-refused by the effect-data pair, so they are ROUTED rows now. The five
remaining refusals are all real work with a name: the two NPC-flag predicates, the avoid-list predicate,
the cache row index, and the weapon-set switch.



Checking the plugin's unrouted rows against the layer turned up **two members whose absence was a
divergence rather than a gap**, and both are now ported into their own source's home:

* **`UAI_PlayerHasEffectType`** was not ported at all, and `UAI_IsCastSensible` carried an **inline
  scan** where the source calls it (`py4gw/gwa3/uai_can_cast.py` used to say so in its own header).
  That is exactly the substitution the porting rule forbids -- the source's member has a name a script
  calls, and the source declares it in ``Cache/UtilityAI_EffectsCache.au3:587-610``, so it belongs in
  `py4gw/gwa3/uai_effects.py`, beside the other questions that file declares. `UAI_IsCastSensible` now
  calls it, in the source's own three-``Case`` shape, with the ``@extended`` skill id read through the
  documented twin `_player_effect_of_type`.
* **That twin scanned forwards and the source scans backwards.** ``For $i = ($l_i_EffectCount - 1) To 0
  Step -1`` (``UtilityAI_EffectsCache.au3:603``) means that with two stances up, the id the source hands
  back through ``@extended`` is the **last** one, and `UAI_IsCastSensible` compares *that* with the slot.
  A forward scan answers a different skill for the same client state. The scan is now
  ``reversed(...)``, and the test asserts it with two stances up.
* `UAI_GetFeederEnchOnTop` (``:549-585``) is **ported**, with the global it remembers between calls
  (``$g_i_LastFeederEnchTimestamp``, declared at ``:51``) living in `py4gw/gwa3/uai_effects.py` -- the
  module named for the file that declares it -- and `UAI_ResetRuntime` now zeroes it, which is the
  source's own line (``UtilityAI_Cache.au3:72``) and was missing until now. **Seven strategy bodies
  call it**, so they un-refused with it: the generated set is 4,514 transcribed and 58 refusing.
  Its membership test is worth a note for the next reader: the source tests its eight-skill list with
  ``_ArrayBinarySearch(...) < 0``, which is only a membership test because **that list is sorted**
  (1493, 1495, 1496, 1497, 1498, 1499, 1524, 1763) -- checked, and the port keeps both the list and the
  fact.
* `_UAI_EffectEndingSoon` was spelled ``_effect_ending_soon`` here, while the layer keeps every other
  underscore-prefixed GwAu3 name as written (`_GetArmorScore`, `_UAI_BestCoveragePosition`,
  `_UAI_CountAlliesInRange`). It is the source's own `Func` on ``:406``, and it is now under the
  source's spelling -- a name deviation in one direction only, which the surface test now pins.

**And the route map's plugin rows were written**, because leaving them would have made the map report
a built layer as unbuilt: 96 rows, of which **59 are now ROUTED** (201 hand routes in all, was 139) and
the other 37 are tiered for what they are. Every one of the **79 citations those rows carry is
resolved from the member's own `def` line at generation time** -- a hand-typed line drifts the moment
a module is edited, and a drifting citation is worse than none. The generator **stops** if a name in
that table is not defined in the module it names, so the table cannot rot silently.

The **dynamic skill cache** landed with it: `py4gw/gwa3/uai_dynamic_skill_cache.py` ports all three
members of `Cache/UtilityAI_DynamicSkillCache.au3` -- `UAI_GetDynamicSkillInfo` answers a slot's adrenaline
words, skill id, event and its two **recharge** columns from the live slot record with the source's own
signed arithmetic, over the same ``0x14`` record and the same offsets as `Skill_GetSkillbarInfo`, while the
fill member and the runtime struct descriptor are NOT APPLICABLE and say so. Adding `Map_GetInstanceInfo`
also **un-refused two strategy bodies that called it** -- the generated-code call check working in both
directions. The strategies now stand at **4,571 transcribed and 1 refusing** (2026-10-10; see *the
strategy generator's four new rules* and *the model-state disagreement* below for what moved them from
4,507 and 65).

- **708 offline tests**, pyright clean, and **30 live tests** (see below); the action surface has been
  exercised through a GwAu3-style script's first lines, and the control-action route is verified live
  separately by `tests/probe_gwa3_control_action_live.py` (see *the control-action route* above).

### `UAI_*`: GwAu3's combat AI, and what is portable in it (2026-10-10)

GwAu3's UtilityAI plugin is the largest thing in its checkout â€” 44 files, about 4,700 functions, 1.9 MB
â€” and **113 of those functions are what its own scripts call**. **Where the plugin stands now is measured
by the route map itself** (`tests/scratch/_count_plugin_tiers.py` reads the generator's own `tier_for`
over its declarations): **every one of its 145 rows is tiered** -- **121 ROUTED**, **4 REFUSED** and
**20 NOT APPLICABLE**, with none left unclassified. **That is new (2026-10-10):** the earlier count was
47 routed and 96 unrouted, and 79 of those 96 turned out to be members the layer already implements --
`UAI_CanUse`, the `UAI_Filter_*` predicates, the `Anti_*` guards, the engine's own
members and the party helpers behind it -- so their rows were written with **the line resolved from
each member's own `def` at generation time**, which is why they cannot drift. The rest are tiered for
what they are: four members whose bodies refuse (two NPC-flag predicates, the avoid-list predicate and the
cache row index), twenty that maintain GwAu3's own per-frame state or hand
out a `DllStruct` (NOT APPLICABLE), and none with no route at all -- `UAI_AgentHasVisibleEffect`, the
last one, is ported (see *the visible-effect family* above), and the weapon-set switch, the fifth
refusal in the count above, is routed as of *the control-action route*. The engine
itself -- the cast chain, the weapon-set analysis and `UAI_Fight` -- is built. The sixty-four
`UAI_Filter_*` predicates are *not* in that 113 â€” GwAu3's scripts
pass their **names as strings** to `_ApplyFilters`, so a call scan cannot see them â€” and all sixty-four
are ported. The split is what `py4gw/gwa3/uai_utils.py` starts to work through:

**Where the plugin's own machinery is called from, measured (2026-10-10, the same census the UDF
generator uses).** This
is the scope question the layer's contract turns on, so it is answered with a count rather than an
impression: **63 of the 65 unbuilt functions of that 113 have no call site outside
`API/Plugins/UtilityAI/`** â€” they are the plugin's
own machinery, called by its other files and by nothing a user writes. **Two are called from outside**:
`UAI_Fight` (`Scripts/Exemples/Exemple_AutoitGUI_Tester.au3:137`, and `Pathfinder_Movements.au3:224`)
and `UAI_CacheSkillBar` (`Scripts/Exemples`). So the remaining *user-facing* surface of UtilityAI is
**`UAI_Fight` and the engine under it**, and the other 63 names are how that engine is built rather than
what a script calls. That is the owner's own scope ruling applied to the plugin â€” *the user-facing
routines, named the same and used the same; how they are implemented is not the parity that matters* â€”
and it makes the rest of this work one deliverable with a known size instead of 65 items:

* the engine (`UtilityAI_Core.au3`'s ten functions plus the `Core/` files behind them:
  `UAI_UseSkills`' slot loop, `UAI_TryUseSkill`, `UAI_PrioritySkills`, `UAI_AutoAttack`,
  `UAI_CanUse`/`UAI_CanAutoAttack`, the party-aggro and called-target queries), which is what a
  `UAI_Fight(...)` call runs. **Its dependency chain was walked member by member (2026-10-10), and the
  first unported thing it reaches is not in the plugin at all** â€” the party queries in
  `Core/UtilityAI_Utils.au3` (`UAI_CountEnemyInPartyAggroRange:29`, `UAI_IsEnemyInPartyAggroRange:51`,
  `UAI_GetNearestEnemyInPartyRange:76`, `UAI_GetPartyCalledTarget:131`) call four accessors of
  **`Modules/Data/GwAu3_Data_Party.au3`** that this layer does not have yet:
  `Party_GetMyPartyInfo:69`, `Party_GetMyPartyPlayerMemberInfo:100`, `Party_GetMyPartyHeroInfo:131` and
  `Party_GetHeroFlagInfo:368`. So the engine's next step is a *read* one â€” the eighth family's
  member-array accessors, over the same party context `Party_GetPartyContextInfo` already answers from â€”
  and the slot loop's first read, `Skill_GetSkillbarInfo` (`Modules/Data/GwAu3_Data_Skill.au3:210`), is
  the same kind of gap on the skill side. `UAI_TargetIsValid` is ported and routed
  (`py4gw/gwa3/uai_core.py`), and the rest of that file refuses by name with what each member needs;
* the skill decision the engine depends on â€” the per-skill ranking modules, `UtilityAI_Spell.au3` alone
  being 1,119 functions over 300 KB, reached through the two dispatch tables
  `UtilityAI_BestTargetCache.au3` (4,606 lines, one function) and `UtilityAI_CanUseCache.au3` (4,593
  lines, one function). This is the one part with no shortcut: what to cast is the source's content, and
  the port has to read it out of the same tables.
* the caches and the weapon-set analysis, whose *accessors* are already ported over live reads; what is
  left of them is the fill side, which this project's execution model does not have (see *Caching*).

**The engine's party layer landed 2026-10-10 and is live-verified.** It was blocked on two things and
both are now done: `GwAu3_Data_Party.au3`'s member accessors, and the world's hero-flag array read
element-wise (`WorldContextStruct.hero_flags`, whose `HeroFlagStruct` is ``0x24`` â€” GwAu3's own stride).
`py4gw/gwa3/uai_utils.py` now ports `UAI_CountEnemyInPartyAggroRange` (``:29``),
`UAI_IsEnemyInPartyAggroRange` (``:51``), `UAI_GetNearestEnemyInPartyRange` (``:76``) and
`UAI_GetPartyCalledTarget` (``:131``), with `Party_GetSize`/`Party_GetHeroCount`/`Party_GetHeroAgentID`/
`Party_GetHeroID` beside them. Each keeps the source's guard order â€” including the skip of a hero that
stands where it was flagged, which is why the flag array was needed at all â€” and two of the source's own
oddities are recorded on the members rather than tidied: `UAI_CountEnemyInPartyAggroRange` answers an
*agent id* from the player branch and a *count* from the hero branch, and the range search qualifies an
enemy by its distance to a **hero** but chooses by its distance to the **player**. Live (2026-10-10):
size ``1``, heroes ``0``, `UAI_IsEnemyInPartyAggroRange` ``False`` with
`UAI_CountEnemyInPartyAggroRange` ``0`` â€” the same loop asked two ways â€” and `Party_GetHeroAgentID(0)`
equal to `Player.GetAgentID()`.

**One new offset disagreement is the owner's to settle**, the third of its kind alongside the `Friend`
family and the three model-state columns: `Party_GetHeroFlagInfo`'s ``LockedTargetID``. GwAu3 reads it at
flag-record ``+0x20``; this project's `HeroFlagStruct` names ``+0x1C`` ``locked_target_id`` and leaves
``+0x20`` as the placeholder ``h0020``. The key **refuses where the source's ``Case`` would read** â€”
inside the matched element, so an unmatched hero number still answers ``0`` as GwAu3 does â€” rather than
answer one offset under the other codebase's name. The record's other six keys are routed.


* **Arithmetic on agent reads** â€” the thirteen functions in `UtilityAI_Utils.au3` that this layer now
  ports: armour ratings by profession, hit-point estimates, the damage curve, and the three profession
  predicates. GwAu3's constants are transcribed with their own citations, because a changed armour
  bonus or hit-point slope changes what a bot decides to attack and none of the numbers is derivable
  from the others. **One mechanism difference** is recorded on `UAI_GetAgentProfession`: GwAu3 answers a
  mob's profession from the world's NPC array (`index Ã— 0x30 + 0x14`), while this reads the ported
  `Agent.GetProfessions` for every agent type. Both answer the agent's primary profession from the
  client; a live comparison is what would settle an edge-case mob, and the docstring says so.
* **Reads over GwAu3's own per-frame caches** â€” `py4gw/gwa3/uai_agent.py` ports the agent-cache
  accessors: `UAI_GetAgentInfo`, `UAI_GetAgentInfoByID`, `UAI_GetAgentCount` and `UAI_GetPlayerInfo`,
  answering **77 of the 88 columns** from this project's live agent reads. GwAu3 reads
  `$g_amx2_AgentCache[row][$GC_UAI_AGENT_*]`, filled once per frame; this project has no frame loop, so
  there is no tick to snapshot against and a read taken now is the same fact taken later. The column
  table is keyed by the constants GwAu3's own `Global Enum` declares, and a test asserts that **every
  routed column names a key this project's agent table actually has** â€” four of the first sixty-one did
  not, and a misspelled key would have answered `0` through that table's unknown-field fallthrough.
  **Eleven columns refuse, for two reasons, and the first is a finding about GwAu3 itself:**

  | Column | ``UAI_DecodeAgentInto`` | ``GwAu3_Data_Agent.au3`` |
  | --- | --- | --- |
  | ``IsAttacking`` | ``0x40``, ``0x60``, ``0x440``, ``0x460`` | ``0x60``, ``0x440``, ``0x460`` â€” **no ``0x40``** |
  | ``IsIdle`` | ``0x44``, ``0x64`` | ``0x40``, ``0x44``, ``0x64`` â€” **has ``0x40``** |
  | ``IsMoving`` | ``0x4C``, ``0xCC`` | ``0xC``, ``0x4C``, ``0xCC`` â€” **has ``0xC``** |

  One GwAu3 file calls ``0x40`` *attacking* while another calls it *idle*, and they disagree about
  whether ``0xC`` is movement. Delegating those three would answer whichever set this project ported
  under the name of the other, so they refuse â€” **and which set the client uses is the owner's finding
  to settle**, as with the `Friend` offsets. The other eight are GwAu3's own bookkeeping: `Ptr`,
  `Timer`, `Distance` (to the *player* at fill time), `IsExploitableCorpse`, the two `IsPlayer`/`IsNPC`
  derivatives, and the two cache row indices.
* **The effect and bond questions** â€” `py4gw/gwa3/uai_effects.py` ports nine of them, and it is the
  layer's clearest case of a split a caller feels. **Presence is routed**: `UAI_AgentHasEffect`,
  `UAI_PlayerHasEffect`, `UAI_AgentUpkeepsBond`, `UAI_PlayerUpkeepsBond` and the two effect counts ask
  the client directly (`py4gw.effect`, over ``PyEffects``' own bindings). **Timing is routed too (corrected 2026-10-10)**: GwAu3's
  ``TimeElapsed``, ``TimeRemaining``, ``Scale`` and ``BonusScale`` are computed from
  ``$GC_UAI_EFFECT_Timestamp`` â€” a field this document called GwAu3's own snapshot, and **that was
  wrong**: the cache is filled from the **client's** effect record
  (`Memory_ReadArrayStruct($l_p_EffectArray, ...)`, `UtilityAI_EffectsCache.au3:181-183`, with `Duration`
  at `+0x10` and `Timestamp` at `+0x14` per `:59-62`), so all ten columns are routed over
  `py4gw.effect.get_effects`, the four computed ones with the source's own arithmetic. ``AttributeLevel``,
  ``EffectID`` and ``CasterID`` read the port record's fields by name; a test asserts that **every**
  column of the enum has a reader, and `py4gw/gwa3/uai_effects.py`'s own docstring carries the finding.
* **The agent predicates** â€” `py4gw/gwa3/uai_filter.py` ports **all sixty-four** of `UAI_Filter_*`,
  the set GwAu3's skill modules use to decide who a spell may be cast at. It reads as a map of what an
  agent question costs: the allegiance, last-strike, health-fraction, effect-word and profession-class
  predicates route straight through `py4gw/gwa3/uai_agent.py` and `uai_utils.py`, while the refusals
  fall into four groups that each name something different â€” the three columns **GwAu3's own two files
  disagree about** (`IsMoving`, `IsAttacking`, `IsIdle`) plus `IsExploitableCorpse`; the seven
  **visible-effect** predicates, which need `UAI_AgentHasVisibleEffect` and its own cache; the four
  **NPC-flag** predicates (`IsSpirit`, `IsMinion` and their controlled forms), which need the world's
  `NpcArray`; and two that read GwAu3's own globals (`$g_i_BestTarget`, `$g_v_AvoidPlayerNumbers`). The
  profession predicates keep GwAu3's guard that a player, hero or henchman answers `False` â€” they mean
  "an NPC of this profession", not "any agent of it".
* **The targeting and positioning queries** â€” `py4gw/gwa3/uai_get_agent.py` ports **all twenty-six** of
  `UtilityAI_GetAgent.au3`'s functions: the agent searches (`UAI_FindAgentByPlayerNumber`,
  `UAI_CountAgents`, `UAI_IsAgentInRange`, `UAI_GetNearestAgent`, `UAI_GetFarthestAgent`), the
  best-target selectors (`UAI_GetBestSingleTarget`, `UAI_GetBestAOETarget`,
  `UAI_GetBestTargetByDamageType`, `UAI_GetBestAOETargetByDamageType`,
  `UAI_GetBestTargetByConditionCount`), the ward and corpse placement queries
  (`UAI_GetBestWardPosition`, `UAI_GetBestOffensiveWardPosition`, `UAI_GetBestMartialEnemyPosition`,
  `UAI_MoveToWardPosition`, `UAI_GetBestCorpseForAllySupport`, `UAI_GetBestCorpseForEnemyPressure`,
  `UAI_MoveTowardCorpse`, `UAI_IsCorpseNearest`) and the two helpers (`UAI_PlayerHasOtherMesmerHex`,
  `UAI_ConvertAgentID`). Twenty-five route; **one refuses**, and it is the condition counter, which
  needs `UAI_AgentHasVisibleEffect` â€” the same missing member that holds seven filter predicates, and
  the one place where "how many effects" (answerable) and "how many *status* effects by skill id" (not)
  can be told apart only by the caller's intent.
  - **The filter strings work, and that is what makes the module usable.** `_ApplyFilters`
    (`GwAu3_Data_Agent.au3:1221-1243`, ported into `py4gw/gwa3/data_agent.py`) resolves a
    pipe-separated list like `"UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe"`, inverts a name with a
    leading `-`, and answers `False` for a name that resolves to nothing â€” GwAu3's own answer for
    AutoIt's `Call` on an unknown function. AutoIt resolves the name in the script's global function
    namespace; this port resolves it in its own callable surface, which is the same set of names.
  - **The distance column is computed rather than refused.** Six of the functions range-test and compare
    on `$GC_UAI_AGENT_Distance`, which `py4gw/gwa3/uai_agent.py` refuses as a cached column. The cache
    fills it as `Sqrt((X - PlayerX)^2 + (Y - PlayerY)^2)` (`UtilityAI_AgentCache.au3:163-165,231`), so
    the module performs that arithmetic over the same two live reads â€” the same number, without the
    frame of staleness â€” and says so on `_cached_distance`.
  - **`$g_i_FightMode` now has a home.** The mode is UtilityAI's mutable setting, so it cannot be a
    constant: `py4gw/gwa3/uai_const.py` carries it with GwAu3's own initial value, which is **`1`, or
    *Pressure*** (`UtilityAI_Const.au3:20-21`) â€” a fresh UtilityAI prefers the *highest*-HP target, the
    opposite of what the setting's name suggests, and the port starts where the source starts. The rest
    of that file's globals land with the modules that read them, and the module names them.
  - **Three of the source's own quirks are kept and tested**, because they stop looking like accidents
    once a test names them: `UAI_GetAgentLowest`/`Highest` compute the reference id and never consult it
    (`:177`, `:204`), so they can answer the reference agent; `UAI_MoveTowardCorpse` answers `True` on a
    timeout as well as on success (`:778`); and `UAI_GetBestMartialEnemyPosition`'s trailing comment
    names its sibling's function (`:568`).
* **The rest of the caches and the combat engine** â€” `UtilityAI_StaticSkillCache`, `DynamicSkillCache`,
  `BestTargetCache`, `CanUseCache` and `WeaponSets`, then `UAI_Fight`,
  `UAI_UseSkills`, `UAI_TryUseSkill`, `UAI_AutoAttack`, `UAI_PrioritySkills` and the per-skill ranking
  modules (`UtilityAI_Spell.au3` alone is 1,119 functions over 300 KB). The remaining caches read the
  same live data this layer already reads; the ranking modules decide *what to cast* from it and act
  through GwAu3's injected queue, which is the part that needs the routes above first. `UAI_AgentHasVisibleEffect`
  and its visible-effect rows are the single most-reached of these: one refused targeting function and
  seven refused filter predicates stand behind it.

### The `Friend` family: the one whose offsets disagree (2026-10-10)

Seven of the eight read families resolved key for key against a structure this project declares. The
eighth does not, and the disagreement is worth the owner's attention because it is a finding about the
**client**, not about either codebase's style:

| GwAu3 key | GwAu3's offset | This project's field | Its offset |
| --- | --- | --- | --- |
| `Type`, `Status`, `UUID`, `Name`/`Alias` | `+0x0`, `+0x4`, `+0x8`, `+0x18` | `type`, `status`, `uuid`, `alias` | the same |
| `ConnectedName`/`CharName`/`Playing` | `+0x2C` | `charname` | **`+0x40`** |
| `FriendID` | `+0x40` | `friend_id` | **`+0x68`** |
| `MapID`/`ZoneID` | `+0x44` | `zone_id` | **`+0x6C`** |

**The arithmetic says why they cannot both be right.** A 20-character wide string is 40 bytes, so this
project's `alias` spans `+0x18` to `+0x40` and its `charname` begins exactly where GwAu3 puts
`FriendID`. The port's layout is internally consistent and 112 bytes end to end. GwAu3's is consistent
only if its strings are **ten** characters wide â€” and it reads `'wchar[20]'` for both, which overruns
into the next field and works anyway because a wide read stops at the first NUL.

**So the six affected keys refuse rather than choose.** Answering `ConnectedName` from this project's
`charname` is *probably* the same field the client calls the character name â€” but a route that reads a
field at an offset GwAu3 does not name is a different reading wearing the same name, and the two
structures disagreeing is a finding, not a licence to pick. **Which layout matches the client is the
owner's call**, and the work to settle it is one live read of a friend record against both offsets.

Everything else in the family is routed: the four agreeing keys, the computed keys built on them
(`TypeName`, `StatusName`, `IsOnline`, `IsOffline`, `IsFriend`, `IsIgnored`, `Number`/`Index`), the five
list counts whose offsets all agree, `Friend_GetMyStatus`, and the two name tables â€” ported verbatim,
`"Do Not Disturb"` with its spaces and capitalisation, because a script that compares the string
compares that text.

### The example-script measurement, and what it says about parity (2026-10-09)

The layer's purpose is *parity of usage*: a GwAu3 author keeps their script and changes as little as
possible. `tools/analyze_gwa3_example_parity.py` measures that directly, on GwAu3's own scripts in
`external/GwAu3/Scripts/`, writes `docs/GWA3_EXAMPLE_PARITY.md`, and writes a migrated copy of each
script **beside its original** as `<name>_stealth.au3` â€” beside it because a GwAu3 script's include
graph is relative to its own directory, and a copy placed anywhere else reports undeclared globals on
lines the migration never touched.

**Text parity is 8,764 of 8,771 lines â€” 99.9% â€” and that number is by construction, not an
achievement.** A migration edits the `#include` and nothing else: every identifier, every argument
order, every `$GC_*` is untouched, because the names and shapes are GwAu3's. That is precisely what
the layer was built to buy, and it is worth nothing on its own, because a script can be pointed at
this layer, load, and call routines that are not built.

**Call parity is the real number, and it is 14.8%.** Across every script:

| | |
| --- | --- |
| Distinct GwAu3 routines the scripts call | **243** |
| â€” implemented by this layer | **36 (14.8%)** |
| Call sites | **1,791** |
| â€” answered by this layer | **462 (25.8%)** |
| Distinct `$GC_*` constants they use | 46 |
| â€” defined by this layer | **43 (93.5%)** |

**And the shape of the gap is the finding.** The routines the scripts call most are not the `Cmd_*`
and `Data_*` accessors this layer was scoped to â€” they are GwAu3's **framework** functions, which the
layer has never addressed:

| Prefix | Call sites not answered | What it is |
| --- | --- | --- |
| `Log_` | 717 | logging â€” 40% of every unanswered call site |
| `Party_` | 75 | party actions |
| `Item_` | 68 | item/inventory actions |
| `Ui_` | 65 | rendering and window toggles |
| `Attribute_` | 42 | attribute and template actions |
| `Trade_` | 42 | trade actions |
| `Map_` | 41 | map actions |
| `Core_` | 25 | **`Core_Initialize` and `Core_AutoStart` â€” the first two lines of every example** |

`Core_Initialize`/`Core_AutoStart` are in every example script and are the door: no script runs
without them. They are also *session lifecycle* rather than a read or an action â€” in this project the
equivalent is `py4gw.connect()` â€” so wiring them is a **scope decision for the owner**, not a
mechanical port. `Log_*` is the other half: 717 call sites, and a logging surface is a decision about
where a migrated script's output goes.

**One more thing the analysis found, and it was a real defect in this layer.** Reading the scripts and
asking which constants they use showed that `py4gw/gwa3/constants.py` was missing **129 names** â€”
every `$GC_I_INVENTORY_*` field key, every `$GC_I_HERO_ID_*` hero id, the `$GC_I_SKILL_*` and
`$GC_S_SKILL_*` field keys, the `$GC_E_TITLEID_*` title ids. GwAu3 declares constants in **two** forms
and the generator read only one:

```autoit
Global Const $GC_I_RARITY_WHITE = 2621          ; read
Global Enum _                                   ; not read at all
    $GC_I_INVENTORY_PTR, _                      ; 0
    $GC_I_INVENTORY_ITEMID, _                   ; 1
```

Both forms are read now â€” **7,480 constants**, up from 7,020 â€” and the offline constant test reads
both too. **That test could not have caught the loss before, and that is the lesson worth keeping:** it
compared the module against the generator's own extraction in both directions, which is an index
checked against an index. A surface verified against its own parser is not verified against the
source. The names were found by reading what scripts *use*, not by re-reading the parser.

The three constants the scripts use that this layer still does not define
(`$GC_B_LOAD_LOGGED_CHARS`, `$GC_S_BOT_TITLE`, `$GC_S_CHARACTERS_INI_PATH`) are declared **nowhere in
GwAu3's API** â€” dangling references in GwAu3's own scripts. Defining them here would invent a value
GwAu3 never states, so they stay undefined.

### The scope error this exposed, and the three defects it was hiding

**The layer's surface was built from a chosen set of directories, and each time the real usage turned
out to be wider.** `docs/GWA3_ROUTE_MAP.md` tiers 648 functions from `API/Modules/{Cmd,Data}`; the
mechanism map, the bridge's declared-name set and the AutoIt UDF were all built from that same
extraction. Measured against GwAu3's own scripts:

| | |
| --- | --- |
| Functions GwAu3 declares | 5,685 |
| â€” of which `API/Modules/{Cmd,Data}` | 648 |
| â€” of those 648, **actually called anywhere** | **322** |
| Functions GwAu3's scripts **call** | **667** |
| â€” never tiered, never declared, never read | **345** |

The same defect, three times, each found by reading usage rather than the extraction:

1. **345 called functions had no wrapper at all.** AutoIt rejects a call to an undeclared function at
   compile time â€” measured: `Unknown function name.` and exit 1, the file never runs
   (`tools/autoit/READINGS.md`). Each of those 345 was a migrated script that could not start. The UDF
   now declares **993 wrappers** (46 implemented, 602 tiered-but-unbuilt, 345 called outside the tiered
   surface), each signature parsed from GwAu3's own `Func` lines instead of from the CSV index.
2. **129 constants declared with `Global Enum`** â€” every `$GC_I_INVENTORY_*` field key, every
   `$GC_I_HERO_ID_*`, the `$GC_I_SKILL_*`/`$GC_S_SKILL_*` field keys, the `$GC_E_TITLEID_*` â€” were
   missing, because the constants generator read only `Global Const`.
3. **287 constants declared outside `API/Constants/`** â€” `$GC_UAI_TARGET_MODE_CALL`,
   `$GC_I_UAI_WARDTYPE_DEFENSIVE`, `$GC_I_ASSERTLOG_STOLEN` and their neighbours live in
   `API/Plugins/**`, and GwAu3's own parameter defaults name them
   (`UAI_Fight(..., $a_i_FightMode = $g_i_FinisherMode)`).

`py4gw/gwa3/constants.py` now reads **the whole `API/` tree in both declaration forms: 7,480 names**,
up from 7,020. The AutoIt side carries the same table
(`tools/autoit/Stealth_GwAu3_Constants.au3`) plus the **150 standard UDL includes** GwAu3's own
aggregator pulls in, because a replacement include that omits them is not a drop-in.

**The lesson is about the denominator, and it is the same one the constant test taught.** Every one of
these was invisible to a check that compared an artifact against the extraction it was generated from.
`tests/test_gwa3_constants_offline.py` now reads the whole tree in both forms, and the parity tool
reads GwAu3's *scripts* and asks what they use. **A surface verified against its own parser is an index
checked against an index** â€” the names only come out right when something reads the callers.

### What a migrated script compiles to

`Au3Check.exe` over each script and its migrated copy (`tools/autoit/READINGS.md` carries the detail):

| Script | As shipped | Migrated |
| --- | --- | --- |
| `Exemple_AutoitGUI_Tester.au3` | 10 | **0** |
| `Multi-Launcher.au3` | 0 | **0** |
| `Exemple_ImGUI_Tester.au3` | 14 | 2 |
| `Tools_VisibleEffect.au3` | 10 | 4 |
| `GwAu3_DevTools.au3` | 16 | 4 |
| `Exemple_PathFinding.au3` | 11 | 26 â€” duplicate-`Const` collisions, see below |
| `Punch_Out_Farm.au3` | 47 | not measurable â€” five of its companion files are not in the repository |

**Two things the compile pass established, both recorded rather than papered over.** A script whose
include graph *also* reaches GwAu3 API or plugin files declares the shared constants twice â€” AutoIt
answers `previously declared as a 'Const'` â€” so **the UDF replaces `_GwAu3.au3`, it does not sit
beside it**. And constants GwAu3 declares as *mutable* `Global`s (`$c_UTILS_Msg_Type_*`,
`$ImGuiWindowFlags_*`) are not a name table and are not carried; they are why three scripts still
report one or two undeclared globals.

### The first live run, and what only a live run could find (2026-10-09)

`tests/test_gwa3_live.py` reads a running client for the first time. It connects **read-only**
(`game_thread=False`: no hook, no patch, no call into the client), hashes the client's whole code
section before and after, and asserts the hash is unchanged â€” measured, pid 23044, `0x539400` bytes,
`b78fe64f3f748e19â€¦` both times. Nothing in this layer has ever acted on the client.

**What it exercised.** All 400 declared keys of the seven families: 350 are asked for a value,
50 must refuse with their own rule. Result: **342 answered a value, 1 refused inside its own reader
(`TotalPartySize`, GwAu3's sum of three keys this layer refuses), 3 refused a connection without the
game thread by name, 4 answered `''`**, and **all 50 refusals refused live, each with the reason it
records.** Eleven agent keys, eleven skill keys, six map keys and every party flag were also compared
for equality against an independent route to the same number â€” the ported members and the live records.

**Five defects, and every one of them was invisible offline.** The offline tests are not wrong; they
structurally cannot see these, because a materialized record is not a client read:

| # | The defect | Why offline could not see it | Fixed by |
| --- | --- | --- | --- |
| 1 | `Agent_GetAgentInfo` handed its readers the **base `AgentStruct`**, which carries none of the fields GwAu3's cases read. Every living key raised `AttributeError` live. | the offline test served a hand-built `AgentLivingStruct`, so the record always had the fields | `Agent_GetAgentPtr` converts the record by the agent's own type, in the order the agent cache uses (gadget, item, living) |
| 2 | `Party_GetPartyContextInfo` carried a `record_id` parameter **GwAu3 does not declare** (`GwAu3_Data_Party.au3:4` is `($a_s_Info = "")`). A migrating script's own call `Party_GetPartyContextInfo("IsHardMode")` answered `0` â€” GwAu3's empty-key guard â€” with no error at all. | the offline test passed the id the generated signature asked for, so it never made the call a migrating script makes | the family is emitted with GwAu3's arity |
| 3 | `data_party._record` read `client.party_context.get_context()` â€” the port's **in-process facade cache**, which nothing in this project refreshes, so it answered `None` with a party standing right there. | the offline test patched `_record` out entirely | `client.read_party_context()`, the port's on-demand read, which is the rule this project's execution model requires |
| 4 | `h000C` answered a **`c_ulong * 2`** where GwAu3 reads a dword at `+0xC`. | the offline test asserts the value the table maps, and the table mapped the array | a scalar case whose offset this project declares as an array or structure is read from the record's bytes at GwAu3's own offset and width |
| 5 | `VisibleEffectsNextNode` answered the list structure, **dropping GwAu3's `BitAND($l_p_Next, 0xFFFFFFFE)`** â€” a wrong value, not merely a wrong shape. | the case reads into a `Local` first, and the offline tests never looked at the case's body | cases whose body derives from a local read get a hand-written reader; the generator marks them, and a marked key with no reader refuses rather than answers the raw pointer |

Defects 1â€“3 were fixed and **the fix was verified live** in the same session; 4 and 5 as well, and the
run above is the one after all five.

**A sixth defect, found by the second live run (2026-10-10) â€” and it is defect 1's other half.** The
first run read one *living* record (the player), so it never met a record type whose view lacks the
fields GwAu3's cases read. The UtilityAI targeting queries iterate **every** agent in the client's array,
as GwAu3's own per-frame cache does, and the run raised
``AttributeError: 'AgentGadgetStruct' object has no attribute 'allegiance'``.

| The defect | The measurement that settled the fix | Fixed by |
| --- | --- | --- |
| A field GwAu3 answers for *every* agent raised for the records whose view does not declare it â€” a **gadget** (0xE4 bytes) has no `allegiance`, `hp`, `type_map`, `model_state`, `skill` or `owner`, and `Agent_GetAgentPtr` answers each agent's own view by design | GwAu3's `Allegiance` offset is **0x1B5**, which is *beyond the gadget view entirely*, so reading the record's own bytes cannot answer what GwAu3 answers. The record carries the reader and address it was materialized from (`bind_reader`), and a read through it answers `194` where the local copy cannot be read at all â€” `tests/live_reports/agent_view_sizes.log` | `_read_field_bytes`: the named field for a view that declares it, and otherwise GwAu3's own read at GwAu3's own offset, through the record's bound reader. `_RAW_READERS` carries each key's offset and width from its own `Case`, and the mask-and-compare keys (`IsDead` and its neighbours) plus the computed readers (`CurrentHP`, `CurrentEnergy`, `IsMoving`, `IsCasting`, `CanPickUp`) follow the same rule |

Two lessons are recorded with it rather than left in the code: the first attempt at the fix read the
record's bytes and raised ``struct.error`` instead of ``AttributeError`` â€” *a fix that changes which
exception a defect raises has not been measured against the client's own layout* â€” and the reason the
old suite could not see any of it is that a single living record is a sample of one. The live suite now
asks **22 of those keys of every agent in the array**, whatever its type, which is the regression test.

The run after that fix is **23 live tests, all passing** (``tests/live_reports/gwa3_live_uai.log``), with
the client's code section unchanged before and after (``53b3c20b9541f72aâ€¦``, ``0x539400`` bytes). It
includes the first live verification of the targeting arithmetic end to end: `UAI_GetBestWardPosition`
answered ``[-1097.5, 4952.5, 6]`` and an independent count over the client's own ally records found
exactly **6** allies inside that ward's radius, and `UAI_CountAgents` matched an independent count
computed through `py4gw.Agent` (``0`` in the outpost the run took place in, which is the honest answer
there rather than a weaker test).

**What the run also established, and is not a defect in this layer.** Eight keys need a connection with
the game thread, and they are the layer's only non-reads:

- three item keys â€” `Name`, `CompleteName`, `SingleItemName` â€” **refuse by name**
  (`pass game_thread=True to connect for the bridge`), which is the honest answer;
- four quest keys â€” `Name`, `Location`, `LocationStr`, `Description` â€” answer `''`, which is **not**
  honest, and the layer cannot tell. `Quest.RequestQuestName` reaches the client through `_start`
  (`py4gw/native_src/quest/py_quest.py:242-259`), which catches `(OSError, RuntimeError)` from
  `begin_string_decode` and returns `False`; the store is left at `("", False)`, which is the same state
  as a decode still in flight, so `ready` never turns true and the source's own `"Timeout"` is never
  written. The fix is that swallow, in the port's request path, and it is a change to a ported file â€”
  the owner's call, not this layer's.

`Agent_GetCurrentTarget` and GwAu3's `-1` sentinel are in the same boat for a different reason:
`Player.GetTargetID()` answers the target the connection's listener captured from the client's own
`kChangeTarget` notice, and read-only there is no listener, so it raises. The suite asserts that raise
rather than skipping the sentinel.

### What a GwAu3 author's script looks like afterwards

The target is that the answer is "the includes change and nothing else". A script that today
reads

```autoit
#include <GwAu3.au3>
Agent_ChangeTarget(Agent_TargetNearestEnemy())
Map_TravelTo($GC_I_MAP_KAMADAN)
```

reads

```autoit
#include <Stealth_GwAu3.au3>
Agent_ChangeTarget(Agent_TargetNearestEnemy())
Map_TravelTo($GC_I_MAP_KAMADAN)
```

or, for an author who would rather write Python now that the names are not the obstacle:

```python
from py4gw.gwa3 import *

Agent_ChangeTarget(Agent_TargetNearestEnemy())
Map_TravelTo(GC_I_MAP_KAMADAN)
```

That is the whole promise: **the names, the arguments, the defaults, the return shapes and
the constants come across; the engine underneath is Stealth's.** Where the engine cannot do
what GwAu3's did, the author gets a refusal that names the gap.

## Tests

The layer is testable in the same three bands the project already uses:

- **Offline, no client, no elevation** â€” the largest band, and the one that can be written
  first. The constant surface against its sources; the name parity check in both directions against
  the extraction (names missing are defects; names present that GwAu3 does not declare are defects
  too); each field-name key resolving to the structure attribute it should and returning GwAu3's own
  type and sentinel behaviour; every `REFUSED` row refusing with its named rule; the protocol's
  framing over an in-process pipe. None of this needs Guild Wars running â€” and the read surface,
  which is the larger half, is entirely in this band.
- **The protocol without the client** â€” the worker against a stub that answers every call
  with a fixed value, so a bridge bug is separable from a game bug.
- **Live, with a client** â€” the same shape the project already uses for live tests
  (`tests/test_live_*.py`): every ported member's live test is the evidence for the route
  map's ROUTED rows, so a live run of the layer is a run of routes that are already verified
  one by one. Dialog-driven rows follow the project's own rule: a test that reads a dialog
  drives the interaction itself (`AGENTS.md`, *Live verification*).

## The action surface: what a script *does*

The read surface answers questions; the `Cmd_*` modules are what a script acts with, and
`py4gw/gwa3/cmd_agent.py` is the first of them. It is **hand-written while the readers are generated**,
and the split is deliberate: a reader is one `Switch` over field names, which is transcription; an
action is control flow â€” a guard, a loop, a choice of mechanism â€” and its effects are real, so each
function is written against GwAu3's own body with its lines cited.

**Two generated modules now carry hand-written source, and it goes through `tools/gwa3_snippets/`.**
`data_item.py` carries the six item resolvers and `data_agent.py` carries `_ApplyFilters` â€” GwAu3's
filter-string dispatcher, declared in that module's own source file at `GwAu3_Data_Agent.au3:1221`. A
function written straight into a generated module is lost the next time the generator runs, and a test
compares each generated module against its generator for exactly that reason, so the snippet directory
is where such a function lives and the generator reads it at run time. That is what keeps both true at
once: the module is regenerable, and a function GwAu3 declares in that file has its home in that file.

**Every packet function became a game-thread call, and that is the layer's central substitution.** GwAu3
reaches these effects by forging packets â€” `Core_SendPacket(0xC, $GC_I_HEADER_ACTION_ATTACK, $id, $call)`
and its neighbours. This project does not forge packets, so each one drives the client's own function:

| GwAu3 action | GwAu3's mechanism | This layer's route |
| --- | --- | --- |
| `Agent_ChangeTarget` | game-thread call | `Player.ChangeTarget` (`py4gw/player.py:1074`) â€” the same `agent.change_target_func` GwAu3's stub calls |
| `Agent_Attack` | packet `HEADER_ACTION_ATTACK` | `Player.Interact` (`:1140`) â€” `agent.do_world_action_func` |
| `Agent_GoNPC` / `Agent_GoPlayer` / `Agent_GoSignpost` | packet | `Player.Interact`, the same world action |
| `Agent_CallTarget` | packet `HEADER_CALL_TARGET` | `Player.CallTarget` (`:1096`) |
| `Agent_TargetNearest*` | search + `Agent_ChangeTarget` | the same search over `AgentArray.GetAgentArray()` |

**`Agent_CallTarget` is the sharpest evidence that the routes are the same calls.** GwAu3's packet
carries the literal `0xA`; `Player.CallTarget` branches on allegiance and, for an enemy, passes
`CallTargetType.ATTACKING_OR_TARGETTING` â€” which **is** `0xA`, for the same case. The number did not have
to be guessed at: the port's own docstring records that its runtime's handler for `kSendCallTarget` is
what reaches `call_target_func` (`player.py:1105-1112`).

**One function refuses rather than guess, and the cancel above it no longer has to:**

* `Agent_CancelAction` â€” GwAu3 forges `HEADER_ACTION_CANCEL` (0x28), and this project's route is the
  client's own cancel **control action** (`$GC_I_CONTROL_ACTION_CANCEL_ACTION`, `0xAF`), pressed the way
  Reforged presses it (`Keybinds.CancelAction`, `routines_src/yield_src/keybinds.py:160-161`). The
  earlier refusal stood because `Player.SendRawDialog` was the nearest candidate and the route map
  flagged it *needing a live check*; the authority's own route for this effect replaced the guess. See
  *the control-action route* above.
* `Agent_MakeAgentArray` â€” GwAu3's call asks the **client** to build a snapshot array. This project reads
  the client's array on demand and has no such request, so there is no mechanism to reproduce.

**A return-shape divergence, recorded per function.** GwAu3's `Core_SendPacket` has no `Return`, so every
packet function in GwAu3 answers `0` on every path â€” including success, which is why its own callers test
nothing. These functions answer `True` when the call was made, because a constant is not something a
caller can act on. The divergence is on each docstring rather than hidden.

**And one value that does not line up.** GwAu3's `$GC_I_ALLEGIANCE_ANIMAL` is `0x2`, which this project
names `Allegiance.Neutral`; this project's `Allegiance.SpiritPet` is `4`, which is GwAu3's
*`$GC_I_ALLEGIANCE_SPIRIT`*. So `Agent_TargetNearestAnimal` filters on `Neutral` â€” the same byte GwAu3
tests â€” and the module says so where a reader might expect `SpiritPet`.

### The channel opcode: two numbers that look alike and are not

`cmd_chat` carries the sharpest trap in the layer so far, and it is worth its own note because the wrong
answer is a *plausible* number rather than a crash.

GwAu3's chat functions take the channel as the **opcode character** â€” `'!'` all, `'@'` guild, `'#'` team,
`'$'` trade, `'%'` alliance, `'"'` whisper (`GwAu3_Cmd_Chat.au3:54-55`). This project's
`chat.SendChat` takes that same opcode (`py4gw/native_src/chat/chat.py:105`), which is why a migrated
`Chat_SendChat("hi", "!")` reaches the same channel by the same spelling.

**But the numbers are a different scale.** Measured, not assumed:

| argument | value | `chat.GetChannel` answers |
| --- | --- | --- |
| `'!'` | the opcode `33` | `CHANNEL_ALL` (`3`) |
| `ChatChannel.CHANNEL_ALL` | `3` | `CHANNEL_UNKNOWN` (`-1`) |
| `ord('!')` | `33` interpreted as an opcode | *not a channel* â€” `GetChannel` masks `& 0xFF` and finds nothing |

So there are three ways to write "all" and only one of them works: the **character**. Passing the enum
gives a silent no-op, and an implementation that "helpfully" converts the glyph to its ordinal is worse â€”
it answers a channel that does not exist while reading as if it were doing the obvious thing. The tests
pin the glyph through to `SendChat`, per channel, rather than spot-checking one.

### Two more mechanisms that are refused because the state is GwAu3's own

`Map_InitMapIsLoaded` and `Map_MapIsLoaded` clear and read `$g_p_MapIsLoaded` â€” a slot inside GwAu3's
**injected code block**, not a field of the client (`docs/_inventory_gwau3_party_map_ui_trade.md`). Every
GwAu3 travel action brackets itself with them: clear, send, wait.

This project has no injected block and no map-loaded latch, and `Map.IsMapReady` (`py4gw/map.py:164`) is a
predicate over the **client's own data** â€” a different question from "has GwAu3 seen a load since it
cleared its flag". Both are refused, naming the predicate to use instead, and the travel actions keep
GwAu3's *ordering* and its optional wait while polling the client's predicate.

**That is the pattern for this whole family of divergences:** keep everything the caller can observe â€” the
order of the calls, the parameters, the optional wait, the return â€” and refuse only the part whose state
belongs to a runtime this project does not install.

## What this document does not claim

- **The constants, three accessor families and the route map are built; nothing else is.** `py4gw/gwa3`
  holds `constants` (7,480 names), `data_agent` (143 keys), `data_skill` (63) and `data_party` (14).
  There is no `Cmd_*` module, no worker, no bridge and no AutoIt side in the tree today.

### The offset-resolution rule, learned the hard way

**A GwAu3 offset may only resolve to a *primitive* field, never to a container's internal member.**
The family generator's first version accepted any field covering an offset, and it produced two
defects of the worst kind -- wrong values of the right type, which a caller cannot detect:

- `Party_GetPartyContextInfo("Flags")` resolved to `record.henchmen_array.m_buffer`, because
  `henchmen_array` *starts* at 0x14 and `m_buffer` is its first member. Party flags have nothing to do
  with an array's storage pointer.
- `PlayerCount`, `HenchmenCount`, `HeroCount`, `OtherCount` and `PlayerPartyID` all resolved to
  `record.player_party_ptr` -- the pointer GwAu3 reads *through*, at exactly the offset it reads.

Both were caught by the integrity test comparing the generated table against the source's own `Case`
list, read independently of the parser. The rule the generator now follows: a candidate must be a
scalar, or a scalar member of a nested structure; a container's internal pointer is never an answer.

**And a second-level read is refused rather than approximated.** Five of the party keys need a record
the context points at (`player_party_ptr` at `+0x54`). This layer reads one record, so they raise
naming the pointer and the project file that holds the second record. Following a pointer is the next
piece of work, not something to guess at.

### The gate: `connect()` refuses to read unelevated, and reads do not need it

Measured 2026-10-12, unelevated shell, `Gw.exe` PID 23044 running. `connect(pid, game_thread=False)`
raises before it consults `game_thread` at all (`py4gw/client.py:250-263`), so the "read-only
connection" the docstring promises is not reachable without an administrator.

**But the OS does not require it.** The lower-level pieces, driven directly:

| Step | Result unelevated |
| --- | --- |
| `Win32.open_process_memory(pid)` | **works** â€” handle 468 |
| `Win32.get_main_module(pid)` | **works** â€” `Gw.exe`, base `0x500000`, size `0xf4c000` |
| `ProcessMemoryReader.read(base, 32)` | **works** â€” `4d 5a 90 00 â€¦`, the PE header |
| `RemoteScanner.initialize()` | **works** |
| `MemoryManager.Scan()` | **works** â€” pattern resolution succeeds |

The four rights the write path needs (`PROCESS_VM_WRITE`, `PROCESS_VM_OPERATION`,
`PROCESS_CREATE_THREAD`, `PROCESS_SUSPEND_RESUME`) are exactly what a read does not touch, and the
refusal's own message says so.

**This is recorded as a finding, not acted on.** `AGENTS.md` is explicit that `connect()` asserts
elevation and refuses without it, and that callers must not catch the refusal to keep going â€” so the
gate is not this layer's to weaken. What it means for the migration is practical: **an AutoIt author
who cannot run an elevated shell cannot use the bridge at all**, because the connection refuses before
any routine is reached. That is worth the owner's attention, and the two consistent resolutions are
(a) launch the worker from an elevated shell, or (b) a documented read-only connection that skips the
assertion â€” which is a change to the port's contract, not to this layer.

### Three case shapes, not one

`Item_GetItemInfoByPtr` showed that an offset alone does not say what a case *answers*. Three shapes
exist, and the family generator carries a table for each:

| Shape | Example | Why the offset is not enough |
| --- | --- | --- |
| a plain read | `ModelFileID` at `+0x1C` | the offset is the answer |
| a masked word | `IsIdentified` = `BitAND(interaction, 0x1)` | the answer is a bool; returning the word is a wrong value of a plausible type |
| a comparison | `IsMaterial`: `If type <> 11 Then Return False` | the answer is `type == 11`, and the resolved reader answered the type byte |
| a nested member | `MarkerX` at `+0x18`, inside this project's `marker_ptr` | the offset is a structure's interior, so the reader names the component |
| a no-match answer | `HasQuest` answers `False`, not `0`, when no record matched | GwAu3's own guard distinguishes the two (`GwAu3_Data_Quest.au3:16-21`) |

`IsMaterial` is the worked case: the generator's first run emitted `lambda record: record.type`, so a
non-material item answered `5` where GwAu3 answers `False`. `IsCompleted` did the same thing on the
quest record â€” `lambda record: record.log_state` where GwAu3 answers `BitAND(log_state, 0x2) <> 0`.
Both were caught by reading the case body rather than trusting the offset, which is why each family's
non-field cases are written out by hand.

### The text keys: a decode is a request, and one handshake now runs it

Every accessor family has keys whose GwAu3 case hands a pointer to the client's decoder
(`Utils_DecodeEncStringAsync`). **A decode is not a read**, and that was the read surface's largest
gap: `PyItem.GetName` answers `""` until `PyItem.RequestName` has filled its map
(`py4gw/item.py:394`, `:449`), and a caller cannot tell an unanswered decode from a record with no
name â€” a wrong value of the right type.

**The handshake is now wired**, for every key where the port offers one. `_read_text` runs the port's
own three steps in the port's own order:

| Step | Item | Quest |
| --- | --- | --- |
| request | `Item.RequestName(record_id)` | `Quest.RequestQuestName(record_id)` |
| ready | `Item.IsNameReady(record_id)` | `Quest.IsQuestNameReady(record_id)` |
| take | `Item.GetName(record_id)` | `Quest.GetQuestName(record_id)` |

Seven keys answer through it â€” `Name`, `CompleteName`, `SingleItemName` on the item record, and
`Name`, `Location`, `LocationStr`, `Description` on the quest record. The port carries the source's own
`"Timeout"` literal and its timeout bound, so a decode the client never answers says so rather than
hanging.

**Six keys still refuse, and each one's reason is that the port has no route to take:** `NPCName` and
`Objectives` on the quest record have no `Request*`/`Is*Ready` trio in `py4gw/quest.py`, and the four
`*Enc` spellings return encoded bytes rather than text. Each refusal names that specifically.

**Why this mattered more than another family.** Thirteen keys across two families were blocked on one
decision â€” *when to wait* â€” and it was a decision, not a mechanism: the port already had both halves.
Answering `""` without requesting is the failure it guards against, and that is why the layer refused
rather than approximating.
- **The route map does not exist yet.** The mechanism census above is from source inspection and
  gives the shape of the work (453 read / 92 game-thread call / 108 packet / 63 pure / 12 write),
  but no function has yet been assigned its final tier or its backing member. Those assignments are
  the table, and the table is the next deliverable.
- **The action-route table above is a correspondence, not a live result.** Each right-hand column
  is a member read out of Stealth's source; that the two produce the *same effect in the client* is
  asserted from what each does, and is confirmed only when its row is exercised live.
- **`py4gw.gwa3` is not a port of Reforged**, and no member of the ported surface changes
  because of it.
- **The bridge is not a binding.** AutoIt still cannot call Python; it talks to a worker over
  a pipe, and this document says so rather than implying otherwise.
- **The 228-call-site census measures GwAu3's own scripts**, which is the best available proxy for
  what a GwAu3 user calls and is not a measurement of the wider user population.

## The route map, and what each tier needs

The layer's central artefact is a table with one row per GwAu3 function, carrying the GwAu3
declaration and what backs it here. Each row's verdict is one of exactly four, and there is no
fifth:

| Tier | Meaning |
| --- | --- |
| **ROUTED** | Stealth has a safe route to the same effect; the row names it (the ported class and member, or the game-thread call form and the resolved function). |
| **NO ROUTE YET** | The effect is real and GwAu3 reaches it, but Stealth has no route today. The row names the missing capability, and that name is the work item. |
| **REFUSED** | The effect is one Stealth declines to produce (a forged packet, in practice). The row names the safety rule it would break. |
| **NOT APPLICABLE** | The function manipulates GwAu3's *own* controller-side state and has no counterpart to route at all â€” the diagnostics counters `Agent_GetTargetOrderCount` / `Agent_GetTargetRejectCount` / `Agent_GetTargetRejectLast` count what GwAu3's own target guard rejected (`GwAu3_Data_Agent.au3:48-68`), and `Ui_GetRenderDisabled`/`Enabled` report a 4-byte flag inside GwAu3's own injected block. The row says which of GwAu3's own globals it was reading. |

### The tier table is bigger than the thing it plans

Classifying every declared function was unnecessary. **This document supersedes that plan: the route map is built
for the ~250 routines a script calls, and the rest are classified only when they are reached.** A
row's tier is settled when the row is implemented or refused â€” never in advance for its own sake.
That is the same discipline the class port map uses ("the verdict is updated in the same change that
moves the class"), applied to this layer.

Two facts from the tier-5 audit already recorded in [`RESEARCH.md`](RESEARCH.md) shape how each row
is built, and neither is an argument for skipping a row:

- **A GwAu3 function existing is not evidence that it does anything.** The chat path is the worked
  case: GwAu3's chat slot reads a global declared at `Const_Chat.au3:3` and assigned nowhere in the
  tree, so it treats a null entry as "skip" â€” recorded at `RESEARCH.md:4377-4380`. A row that
  routes to an effect must say what the effect actually is.
- **GwAu3's own constant tables disagree with its own evidence** in at least one place
  (`CharContext` four bytes low, `RESEARCH.md:4362-4368`). Where a row takes a *number* from a GwAu3
  table and lives and dies in the client, the number is a lead to check, which is what `AGENTS.md`
  already requires of GwAu3-derived data â€” and it is why the layout here comes from this project's
  own verified structures, with GwAu3 supplying only the **names**.

**That is the layer's one-line contract, and it is the same line whether the subject is a field, an
offset or an action:**

> **GwAu3 supplies the names, the arguments, the defaults and the return shapes. Stealth supplies
> the implementation, the layout and the safety rules.**

A migration is therefore not a copy of GwAu3 into Python â€” it is GwAu3's *interface* put in front of
what this project already does. Where the two cannot meet, the caller is told which one gave way and
why, by name.
