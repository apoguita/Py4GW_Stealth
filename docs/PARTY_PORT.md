# Party port

`py4gw/party.py` ports Reforged's `Py4GWCoreLib/Party.py`. Every member of `Party`,
`Party.Players`, `Party.Heroes`, `Party.Henchmen` and `Party.Pets` is present in the
source's own shape and nesting, and `tests/test_party_offline.py` fails if one is
dropped. **74 of the 75 declared members answer and 1 raises**, so the class's verdict is
**COMPLETE for this port's purposes (one artifact)** — the same verdict form `Player` and
`Agent` carry, for the same reason: the one member that does not answer cannot be ported,
and it is named with the line that says why. Rounds 1-6 (2026-09-30) took the whole
action surface; every function it calls was measured on the running client first (the plan
and the measurements are in § Actions).

| | Source | `py4gw/party.py` today |
| --- | ---: | ---: |
| `Party` | 35 | 39 declared — 1 raises (`party_instance`) |
| `Party.Players` | 6 | 6 declared — 0 raise |
| `Party.Heroes` | 23 | 23 declared — 0 raise |
| `Party.Henchmen` | 2 | 2 declared — 0 raise |
| `Party.Pets` | 4 | 5 declared — 0 raise |
| **Total** | **70** | **75 declared — 74 answer, 1 raises** |
| Members that write to `Gw.exe` | — | **26** — the difficulty pair, the ten party-button members, the four flag members, `ReturnToOutpost`, the behaviour/pet group (three), `SearchParty` (the wide advertisement), the three name/chat members (`chat.SendChat`/`SendChatCommand` and the player-array reads behind them) and `Heroes.UseSkill` (a control action through `ui::Keypress`) |

Parity was checked against the source file itself, not against a hand-written
list: every `def` in `Py4GWCoreLib/Party.py` at four-space indentation (the
`Party` class) and eight-space indentation (the four nested namespaces) resolves
on the ported class, and no public member exists that the source does not
declare. Three members — `IsPlayerTicked`, `Heroes.FlagHero` and
`Heroes.SetHeroBehavior` — are declared with a space before the parenthesis
(`def IsPlayerTicked (`), which a naive scan misses.

**And the port's members are in the source's own order** — the third half of the porting rule, which
round 17 found was never checked. The port had grouped `Party`'s members by subject (identity, state,
actions) and `Players`, `Heroes` and `Pets` each had one member out of place; `tools/reorder_party.py`
moved the blocks verbatim, and `tests/test_party_offline.py` now compares this module's declaration
order against the source's, so a member inserted in the wrong place fails the suite. The port's own
private helpers (`_context`, `_party`, `_world`, `_is_party_connected`, and `Pets._pet_info`) sit first
in their class, because the source has no member of that kind to order them by.

## Where each member reads from

The binding's methods delegate to `GW::party::` free functions, which read the
party context, the world context, or the player number. Native sources:

| Member | Source |
| --- | --- |
| `GetPartySize` | `players.size() + heroes.size() + henchmen.size()` |
| `GetPlayerCount` / `GetHeroCount` / `GetHenchmanCount` | the corresponding array's `size()` |
| `GetPartyID` | `PartyInfo::party_id` |
| `IsPartyConnected` (private) | `get_is_party_loaded`: every player `connected()` |
| `IsAllTicked` | `get_is_party_ticked`: every player `ticked()` |
| `IsPlayerTicked` | `get_is_player_ticked`: one player by index |
| `IsPartyLeader` | `get_is_leader`: the first **connected** player is this one |
| `IsPartyDefeated` / `IsHardMode` | `PartyContext` flag bits `0x20` / `0x10` |
| `IsHardModeUnlocked` | `world->is_hard_mode_unlocked` |
| `Heroes.GetHeroAgentIDByPartyPosition` | `get_hero_agent_id`: position 0 is the controlled character, 1..n index the hero array |
| `Heroes.IsAllFlagged` / `GetAllFlag` | `world->all_flag` read raw, as `party_bindings.cpp:378-394` does |
| `Heroes.GetTargetIDByAgentID` | `world->hero_flags` after a party-hero check |
| `Pets.*` | `get_pet_info`: `world->pets` matched on `owner_agent_id` |
| `GetPartyMorale` | `world->party_morale` links |

## Findings: members that can only return a constant

Four members look like reads but cannot produce live data, because the source's
own implementation cannot. They are ported to return what the source returns,
and named here so nobody "fixes" them into something the source never did.

| Member | Why |
| --- | --- |
| `Heroes.GetHeroNameById` | `Hero::GetName` returns the `hero_name` member, and neither `Hero` constructor assigns it (`party_bindings.cpp:214-232`) |
| `Heroes.GetNameByAgentID` | same unset field: the walk succeeds, the name it asks for is empty |
| `Heroes.GetHeroIDByAgentID` / `GetHeroIDByPartyPosition` | these return nothing on a miss in the source, so they return `None` here rather than a fabricated `0` |

### The two `others`

`others` is the one name in this file that means two different things:

| | |
| --- | --- |
| `PyParty::others` | a `std::vector<uint32_t>` the binding owns. `GetContext` calls `others.clear()` and never fills it (`party_bindings.cpp:116,280,583`) |
| `GW::Context::PartyInfo::others` | the game's own array, described in `party.h:54` as "agent id of allies, minions, pets" |

Reforged reads the **array**, in `native_src/context/PartyContext.py:78`, through
`GW_Array_Value_View(self.others_array, c_uint32)` — the same field this
project's `PartyInfoStruct.others` exposes. So `Party.GetOthers()` returns live
data here, reading the array rather than the binding's empty copy.

## Findings: one invention found, and one "finding" that was mine

Round 18 audited the **enumerators and record fields** the party reads, the same way rounds 15-17
audited surfaces, arguments, return shapes and order. It reported two things. One was real; the other
was **my own mistake**, and round 19 corrected it against the source I should have read first:

| where | what it is | decided by |
| --- | --- | --- |
| `py4gw/context/party_context.py`, `PartySearchType` | **The port had five upper-case aliases beside the header's enumerators** (`HUNTING = PartySearchType_Hunting`, …). Neither source declares them — Native has only `PartySearchType_Hunting … PartySearchType_Guild` (`context/party.h:60-66`) and Reforged has no such class anywhere — and nothing in the port used them. **Removed**, and the test that asserted them now asserts their *absence* | the two sources; a re-added convenience now fails the suite |
| `py4gw/context/world_context.py`, `HeroFlagStruct` | **Not a finding.** I called the `flag_ptr` field and its `flag` property an invention because Native's `context/hero.h:20` spells the field `flag` — but this class ports **Reforged's** `native_src/context/WorldContext.py`, and that file has both, exactly as the port did: `("flag_ptr", Vec2f)` at `:249` and a `flag` property at `:255-262` that builds a fresh `Vec2f` and answers `None` for a non-finite pair. Round 18's change was reverted in round 19, and the property now reproduces the source's body line for line | `native_src/context/WorldContext.py:242-262` |

**The lesson, written down because it will come up again**: for a class ported from Reforged's Python,
**Reforged's Python is the shape authority and Native's header is only the layout authority**. Field
*names* and *properties* come from the Python file this port ports; widths and offsets come from the
header. I compared against the header where the Python was the source, and the port was right.

The search step of `tests/probe_party_live.py` was the same kind of slip in miniature — it passed a
bare ``0`` where the client's word is an enumerator — and now passes
``int(PartySearchType.PartySearchType_Hunting)`` by name.

### And the three party-member records now carry the sources' names

The same audit, run against Reforged's Python rather than Native's header
(`tools/context_struct_audit.py`), found that this port had named three records
`PlayerPartyMemberStruct`, `HeroPartyMemberStruct` and `HenchmanPartyMemberStruct` and kept the
sources' names as **aliases** at the bottom of `party_context.py`. Both sources call them
`PlayerPartyMember` / `HeroPartyMember` / `HenchmanPartyMember` — Reforged's
`native_src/context/PartyContext.py:9,23,34` and Native's binding (`party_bindings.cpp:315`) — so round
20 inverted it: **the classes carry the sources' names and the `…Struct` spellings are gone**
(`tools/rename_party_members.py` did the rename across the eight files that mentioned them, and the
duplicate import/export entries it left behind were removed by hand). Sizes are unchanged and asserted
(`0xC`, `0x18`, `0x34`).

### The audit's own list, adjudicated member by member (round 21)

For all eleven records the party reads, **no field is missing, no field's order differs and no member
Reforged declares is absent**. What round 20 left was the other half of that report: the **twenty
members this port carried beyond Reforged's declaration**, each of which had to be either a source's
member, this port's read glue, or an invention to remove. Round 21 decided them with the rule round 19
wrote down — **Reforged's Python is the shape authority for a class ported from it, Native's header is
the layout authority** — and the answer was that most of them were a **second vocabulary for one
concept**, which is the defect the porting rule names outright (*"a snake_case twin of a source
method"*).

**Every one of them is now gone.** The table is the whole list; nothing was kept "for convenience",
and nothing was removed that a source reaches by that name.

| record | removed from the port | the authority's own member, kept | why the twin was there, and why it had to go |
| --- | --- | --- | --- |
| `PlayerPartyMember` | `calledTargetId`, `connected()`, `ticked()` | `called_target_id`, `is_connected`, `is_ticked` (`PartyContext.py:9-21`) | Native's header spells them the other way (`context/party.h:13-20`) — but Native's **own Python binding renames them back** (`party_bindings.cpp:504-511` binds `called_target_id`/`is_connected`/`is_ticked`), so nothing in either source reaches the record by the C++ spelling |
| `PartyInfoStruct` | `GetPartySize()` | — (Reforged declares no counterpart on the record) | Native has it (`context/party.h:46-48`), no binding exposes it, and nothing in the port called it; the count lives where Reforged puts it, on `Party.GetPartySize` |
| `PartyContextStruct` | `h0004`, `InHardMode()`, `IsDefeated()`, `IsPartyLeader()`, `requests`, `party_search` | `h0004_array`, `in_hard_mode`, `is_defeated`, `is_party_leader`, `request_list`/`request`, `party_search_array`/`party_searches` | the same six-for-six: Native's header names the fields and helpers `h0004`, `InHardMode()`, `IsDefeated()`, `IsPartyLeader()`, `requests`, `party_search` (`context/party.h:87-103`), and the header is the layout authority — the *names* Reforged's Python gives them are the ones its own callers use. The port's `request` property now carries the source's own body instead of delegating to `requests` |
| `HeroInfoStruct` | `name`, `name_enc` | `name_encoded_str` (field), `name_str` (property) | Native's header calls the field `wchar_t name[20]` (`context/hero.h:36`); `name_enc` was the port's own "compatibility alias", and its docstring said so. The decode they wrapped is `name_str`'s body now, exactly as the source writes it (`WorldContext.py:278-281`) |
| `PetInfoStruct` | `name` | `pet_name_encoded_str`, `pet_name_str` (`WorldContext.py:506-512`) | in **neither** source: Native's field is `pet_name` (`context/world.h:85`) and Reforged's properties are the two above |
| `SkillbarStruct` | `skill_ids`, `get_skill_by_id()` | `GetSkillById()` (`WorldContext.py:444-448`) | `get_skill_by_id` was a snake_case twin of the source's own method, which the port already had and which only delegated to the twin; `skill_ids` was in neither source and nothing used it |
| `PlayerStruct` | `name_encoded`, `name`, `auxiliary_pointers` | `name_encoded_str`, `name_str`, `h0040_ptrs` (`WorldContext.py:616-638`) | the first two were a third and fourth spelling of one pointer read; `auxiliary_pointers` was the port's factored-out walk, now inlined into the source's own `h0040_ptrs` |

**What stayed is one thing, and it is the port's, not the sources':** `bind_reader`, on the five records
whose properties follow a pointer in the target (`PartyInfoStruct`, `PartyContextStruct`,
`PetInfoStruct`, `SkillbarStruct`, `PlayerStruct`). It is how a reader **outside** `Gw.exe` hands a
record the means to read itself — Reforged's views do that from inside the process, so its records need
no such member. That is the whole of the surviving list, and it is the audit's only tolerated addition.

**The list is a gate now, not a report.** `tools/context_struct_audit.py` carries an `ADJUDICATED`
table — those five `bind_reader` entries, each with its reason — and **exits non-zero** when it finds an
addition that table does not name, so a member re-added under Native's C++ spelling, an alias, or a
snake_case twin fails the check instead of waiting for someone to read the output. The removals are
pinned the other way in the tests: `tests/test_party_context_offline.py` and
`tests/test_world_context_offline.py` now assert their **absence** by name, so a re-added convenience
fails the suite (the same shape round 18 used for the five `PartySearchType` aliases).

**And the live stage earned its keep while this was being done.** Removing `PetInfoStruct.name` broke
`tests/probe_party_live.py`'s pet row, which was still reading it — and the **offline suite said
nothing**, because nothing offline drove the read stage; the live run reported `1 member(s) refused`
with `AttributeError: 'PetInfoStruct' object has no attribute 'name'` in the report. Two things came
out of that: the probe reads `pet_name_str` now (the source's member), and
`tests/test_probe_party_live_offline.py` drives `party_reads()` itself against a stand-in and fails on
an `AttributeError` that names a **port** record or a `NameError` — the guard was verified by putting
`.name` back and watching it fail with the same message. Live afterwards, unelevated and read-only:
**`reads: 0 member(s) refused`**, the `hold` plan unchanged at 23 calls of which 0 would write, and the
same readiness table.

**The same sweep found four more callers, in this project's own host tool** — `main.py`'s world-context
dump read `PlayerStruct.name`, `HeroInfoStruct.name`, `PetInfoStruct.name` and `SkillbarStruct.skill_ids`,
all of them names this round removed (the offline suite does not cover `main.py`, which is why nothing
failed): they now read the sources' own members — `name_str`, `name_str`, `pet_name_str`, and the
record's declared `skills` array for the slot ids, which is how the source's own `GetSkillById` walks it.
Nothing in this project's code reads a name that neither source declares any more, with one recorded
exception outside these eleven records (`py4gw/context/gadget_context.py:59`, `§ Progress`).

## Findings: members limited by the source

| Member | Limitation |
| --- | --- |
| `Heroes.IsHeroFlagged(hero_party_number)` | Native handles **position 0 only**, reporting whether the all-flag is set; every other position returns `False`, with the source noting that per-hero flags are not available through the context it has (`party_bindings.cpp:366-376`) |
| `Players.IsPlayerTicked(login_number)` | Native treats the argument as an **array index**; `0xFFFFFFFF` means "this player". Reforged's Python names the parameter `login_number` and passes it straight through, so the name and the meaning disagree in the source. Reforged's name is kept for call-site parity |

### Every member's return shape, and the five differences that are accounted for

`tools/party_signature_audit.py` compares the two files' ASTs a second way: **does each member hand a
value back at all?** That is the other half of a call-site contract, and it is where a port drops or
invents an answer without any value-based test noticing. Five members differ, and all five are already
recorded elsewhere in this document:

| member | source | port | why |
| --- | --- | --- | --- |
| `IsPlayerLoaded` | falls off the end (``pass``) | a value | the source's own stub; the port implements the native function its docstring names (§ Findings) |
| `party_instance` | a value | raises | the recorded artifact — native's `PyParty` object |
| `LeaveParty` | falls off the end | a bare ``return`` | native's own first line (``if (!get_party_size()) return true;``) is what the port carries; every path still answers ``None`` |
| `Players.InvitePlayer` | falls off the end | a bare ``return`` | native's ``if (!(player && player->name)) return false;``, which Reforged's Python does not need because it calls the binding |
| `Players.KickPlayer` | falls off the end | a bare ``return`` | the same guard as `InvitePlayer` |

`tests/test_party_offline.py` pins the comparison with that table transcribed, so a **sixth**
difference fails the suite.

### The one member whose body is not the source's Python: `IsPlayerLoaded`

`Party.IsPlayerLoaded` (`Party.py:247-255`) is a **stub**: its body is ``pass``, so Reforged's own
member answers ``None``. Every other member of this class is the source's Python line for line (or the
native function its binding called), so this one is called out on its own.

The port implements the function the source's own docstring names — *"parity with legacy
``GW::PartyMgr::GetIsPlayerLoaded(-1)``"* — which is Native's ``PyPlayer::IsPlayerLoaded``
(``player_bindings.cpp:30``): the map gate, the player number, the matching player-party member's
``connected()``, otherwise ``False``. **That is a recorded divergence, not a licence**: a member that
answers ``None`` where Native answers a bool is not a port of anything, and nothing in Reforged calls
the stub — its own ``IsPartyLoaded`` calls ``Player.IsPlayerLoaded`` (the other module's member) and
``GetPartyTarget`` calls ``Party.IsPartyLoaded``. The docstring on the member says the same thing, and
`tests/test_party_offline.py` pins the four steps against the party context.

### The unset all-flag is `(+inf, +inf, 0.0)`

`world->all_flag` sits at `+h009C` (`world.h:190`) and an *unset* party flag
reads back as `(+inf, +inf, 0.0)` — a sentinel, not a coordinate. Native compares
the raw floats:

```cpp
const float x = game->world->all_flag.x;
const float y = game->world->all_flag.y;
return (x != 0.0f || y != 0.0f);
```

`inf != 0.0f` is true, so **Native reports `IsAllFlagged() == True` whenever the
flag is unset**, and `GetAllFlagX()/GetAllFlagY()` return `inf` there. That is a
limitation of the source, and this port reproduces it — `GetAllFlag()` is the
signal to trust, and it is only `(0.0, 0.0)` when there is no world context.

Both members therefore read `all_flag_array` directly. `WorldContextStruct.all_flag`
is not used: it withholds non-finite values, which would turn Native's `True`
into `False` and Native's `inf` into a fabricated `0.0`.

Live evidence, map 499 (Explorable), two heroes:

| State | `all_flag_array` | `GetAllFlag()` | `IsAllFlagged()` |
| --- | --- | --- | --- |
| flag unset | `inf, inf, 0.0` | `(inf, inf)` | `True` |
| flag set | `2668.19, -321.55, 0.0` | `(2668.19, -321.55)` | `True` |

### Per-hero flags are readable, but `IsHeroFlagged` ignores them

Native's comment — "hero_flags access via context not directly available" — is
stale, and its own header contradicts it. `WorldContext::hero_flags` at `+h0584`
(`world.h:207`) is a `HeroFlagArray = GWArray<HeroFlag>`, and `HeroFlag::flag` at
`+h0010` (`hero.h:20`) holds that hero's own flag position. Stealth's
`HeroFlagStruct` matches that layout field for field, and reading it live in map
499 shows distinct finite positions per hero:

```text
agent 21 | hero 2 | flag 2635.82,  -83.34
agent 22 | hero 6 | flag 2322.76, -252.86
           all_flag 2668.19, -321.55
```

So the data is reachable; Native simply does not expose it. The port keeps the
source's `False` for every position but `0`, and
`tests/test_party.py::test_hero_flag_positions_are_readable_but_flagged_stays_false`
pins both halves — the readable array, and the `False` — so the limitation is not
mistaken for a read failure and not silently "fixed" into behaviour no source has.


## Actions

**Every action is `Party.party_instance().<binding method>()`**, and `party_instance()` is
`return PyParty.PyParty()` (`Party.py:13-18`) — a **new object every call**. `party_bindings.cpp`
(and the `GW::party` bodies in `party_methods.cpp`) is the authority for all of them, exactly as
`merchant_bindings.cpp` is for `Trading`.

### Round 1: the six that needed no new call form

| member | what the source does | what this port does |
| --- | --- | --- |
| `SetTickasToggle(enable)` | `PyParty().tick.SetTickToggle` → `GW::party::set_tick_toggle` (`party_methods.cpp:40-42`), writing the runtime's `g_tick_work_as_toggle` (`party.cpp:31`) | writes `py4gw.party.tick_work_as_toggle` — the same global, in the module where the sources keep it, not on `Party` |
| `SetTicked(ticked)` | `PyParty().tick.SetTicked` → a bool field on the object (`party_bindings.cpp:90`) | **nothing**, and that is the source — see the finding below |
| `ToggleTicked()` | two reads, then `SetTicked` (`Party.py:305-317`) | the two reads in the source's order, then the same nothing |
| `RespondToPartyRequest(party_id, accept)` | **`(void)party_id; (void)accept; return true;`** (`party_methods.cpp:194-198`) | nothing, with the source's line cited |
| `SetHardMode()` | guard `IsHardModeUnlocked() and IsNormalMode()`, then `set_hard_mode(true)` | `_call_difficulty(True)` — `GW::party::set_hard_mode`'s own body (`party_methods.cpp:109-117`): a player party must be there, and the client is told **only when the mode differs** |
| `SetNormalMode()` | guard `IsHardMode()`, then `set_hard_mode(false)` | `_call_difficulty(False)` |

#### Finding: `SetTicked` cannot ready the party, and neither can `ToggleTicked`

`party_instance()` builds a **new** `PyParty` per call, whose constructor runs `GetContext()`
(`party_bindings.cpp:128`) — which *copies* the client's ready state into the object (`:170`,
`tick = GW::party::get_is_party_ticked()`) — and `PartyTick::SetTicked` writes **that object's own
bool** (`:90`). The object is discarded with the call. So `Party.SetTicked(True/False)` changes
nothing anywhere, `Party.ToggleTicked()` runs its reads and then calls that, and `IsAllTicked()`
reads the *fresh* object's copy of the client's state (which is why it is a real answer and not the
flag `SetTicked` wrote). What actually readies the party is `party.set_ready_status_func` — the
runtime's own tick-button path (`party_methods.cpp:44-52`, guarded on the instance type being an
outpost) — and **nothing in `Party.py` reaches it.** The port reproduces the source as written, and
`tests/test_party_offline.py` pins the no-op structurally (the member's body must be its docstring
alone) so a later change cannot quietly "fix" it into a call neither source makes.

### Round 3: the ten party-button members

Ten members share one mechanism. Native builds **two arrays on its own stack** — `uint32_t ctx[13]`
(`ctx[14]` for the window's) and `uint32_t wparam[4]` — fills the fields the client's button handler
reads, and calls the callback with them (`party_methods.cpp:200-279`, `:474-498`). This port has no
stack inside the client, so the arrays go in the block's **data region** at `0x040` (20 words) and
`0x090` (4 words), which is the same substitution the merchant's records make; the addresses handed
over are the region's.

| member | `ctx` | `wparam` | `edx` | callback |
| --- | --- | --- | --- | --- |
| `Heroes.AddHero(id)` | `ctx[0xb]=1`, `ctx[9]=id` | `[1]=0x1`, `[2]=0x7` | 2 | search |
| `Heroes.AddHeroByName(name)` | `PyParty.Hero(name).GetID()` → the line above | | | search |
| `Heroes.KickHero(id)` | `ctx[0xb]=1`, `ctx[ctx[0xb]+8]=id` | `[1]=0x6`, `[2]=0x7` | 0 | search |
| `Heroes.KickHeroByName(name)` | `Hero(name).GetID()` → the line above | | | search |
| `Heroes.KickAllHeroes()` | `kick_hero(0x26)` — the whole body (`:245-247`) | | | search |
| `Henchmen.AddHenchman(id)` | `ctx[0xb]=2`, `ctx[10]=id` | `[1]=0x2`, `[2]=0x7` | 0 | search |
| `Henchmen.KickHenchman(id)` | `ctx[0xb]=2`, `ctx[ctx[0xb]+8]=id` | `[1]=0x6`, `[2]=0x7` | 0 | search |
| `SearchPartyCancel()` | all zero | `[2]=0x8` | 0 | search |
| `SearchPartyReply(accept)` | `ctx[0xb]=0`, `ctx[8]=accept` | `[1]=0x3`, `[2]=0x6` | 0 | search |
| `LeaveParty()` | `ctx[0xd]=1` | all zero | 0 | **window** |

Three details the port keeps because they are the source's:

- `ctx[ctx[0xb] + 8]` is the **value** at `ctx[0xb]` plus eight, so the hero kick writes `ctx[9]` and
  the henchman kick `ctx[10]` — the same slots their adds write. Both are reproduced as the
  expression, not as the index it evaluates to.
- `AddHero` is the only member that passes a second word in **EDX** (`2`); every other one passes `0`.
- `LeaveParty` calls the **window** callback, which is the one measured as a bare `ret` — so it is the
  `FASTCALL_U32_CALLER_RELEASES` form, where the search callback's `ret 4` is `FASTCALL_U32`. The two
  sources declare both with one typedef (`PartySearchButtonCallbackFn`, `:20`); the measurement wins,
  and the difference is written down above.
- `LeaveParty` answers **without calling** when the party size is zero — the source's own first line
  (`:203-204`) — and `SearchPartyReply` is the one member of the ten whose Reforged body returns the
  call's answer (`Party.py:368`), so it is the one that returns a bool here.

### Round 4: the frame path and the flag group

**`ReturnToOutpost` is native's one line** (`party_methods.cpp:119-121`)::

    return ui::ButtonClick(ui::GetChildFrame(ui::GetFrameByLabel(L"DlgRedirect"), 0));

Round 3 left it raising because the **value** had no producer in this port; round 4 built the three members
it needs and settled the value. The frame layer's own members are now the source's three steps —
`_FrameTree.by_label` (the client hashes the label, then the array is scanned for that hash),
`Frame.child_native(0)` (`GetFrameById`'s validity test, then one `U32_U32` call to the client's own
`g_get_child_frame_id_func`), and `Frame.click` (native's `ui::ButtonClick`, which answers a bool) — with
the detail in [`FRAME_TREE_PORT.md`](FRAME_TREE_PORT.md) §5, including the one **recorded divergence** that
making the value reachable required (`Frame.click` returns `ui::ButtonClick`'s bool where Reforged's
wrapper is `-> None`; every other caller in this port discards it). The member itself is native's
expression, guards included: a label no frame carries is `ButtonClick(nullptr)` → `False`, and so is a
child that is not there.

**The flag group is native's three functions over two call forms**, both built in round 2:

| member | source body | the call |
| --- | --- | --- |
| `Heroes.FlagHero(hero_id, x, y)` | `PyParty::FlagHero` → `flag_hero_agent(agent_id, GamePos(x, y))` (`party_bindings.cpp:359-361`) | `flag_hero_agent_func`, `U32_FLOAT_PTR`: the word, then x, y and `GamePos`'s own `zplane` |
| `Heroes.FlagAllHeroes(x, y)` | `flag_all(GamePos(x, y))` (`:362`) | `flag_all_func`, `FLOAT_PTR`: the same record with no word |
| `Heroes.UnflagHero(hero_id)` | `unflag_hero(agent_id)` (`:363`) = `flag_hero(index, GamePos(HUGE_VALF, HUGE_VALF, 0))` (`party_methods.cpp:334-336`) | the index resolves through `agent::GetHeroAgentID` first — the port's `GetHeroAgentIDByPartyPosition` — then the same call with the sentinel |
| `Heroes.UnflagAllHeroes()` | `unflag_all()` (`:364`) = `flag_all(GamePos(HUGE_VALF, HUGE_VALF, 0))` (`:342-344`) | `FLOAT_PTR` with the sentinel |

`flag_hero_agent`'s own guards are kept in its own order (`party_methods.cpp:326-331`): the function must
resolve, the agent id must not be `0`, and it must not be the controlled character — `agent::GetControlledCharacterId`,
read through `Player.GetAgentID` the way the port's other two modules read it. **Two source details are
carried rather than tidied**: `GW::GamePos` is `{float x; float y; uint32_t zplane;}` (`game_pos.h:255-267`),
so the two coordinates travel as their **bit patterns** (`shared_block.float_bits`) and the third word is the
record's own `zplane`; and `FlagHero`/`UnflagHero` disagree about what their argument means — the binding
passes it to `flag_hero_agent` as an **agent id**, while `unflag_hero` treats it as a **hero index** and
resolves it. Reforged calls the member's parameter `hero_id` in both cases. That is the sources' own
disagreement, written down the way `Players.IsPlayerTicked`'s is, and ported as written.

### Round 5: the behaviour and pet group

Three members, each the binding's body over one or two of the three functions the group needs —
`set_hero_behavior_func` (`void __cdecl(uint32_t, Constants::HeroBehavior)`),
`lock_pet_target_func` (`bool __cdecl(uint32_t, uint32_t)`, whose answer nothing reads) and
`command_hotkey_disable_ai_func` (`void __cdecl(uint32_t, uint32_t)`, the second word a **zero-based**
slot). All three are plain `U32_U32` calls, so no new mechanism was needed.

| member | source body | what decides the call |
| --- | --- | --- |
| `Heroes.SetHeroBehavior(hero_agent_id, behavior)` | `set_hero_behavior` (`party_methods.cpp:346-358`) | the world, the function and a **non-empty** `hero_flags` array are one guard; then the record whose `agent_id` matches is found, and the client is told **only when that record's own `hero_behavior` differs** — a record that is not there ends the member with `false` |
| `Heroes.SetSkillAIEnabled(hero_agent_id, slot, enabled)` | `set_hero_skill_ai_enabled` (`:361-389`) | four guards in the source's own order (function, non-zero agent, slot in `1..8`, the party skillbar array), then the hero's skillbar by `agent_id`, then the slot's bit out of the record's `disabled` word: `if (is_disabled == !enabled) return true;` — the call happens only when the client's state is not already the one asked for |
| `Pets.SetPetBehavior(behavior, lock_target_id)` | `set_pet_behavior` (`:391-413`) | the world, **both** functions and a non-empty `pets` array; the pet is the controlled character's own; a target is resolved **only for `Fight`** (`lock_target_id ? GetAgentByID(lock_target_id) : GetTarget()`) and must be a **living enemy**; then the lock is written when it differs and the behaviour when it differs — two separate tests |

Details the port keeps:

- **`SetSkillAIEnabled` returns a bool** — Reforged's member is `return ...SetHeroSkillAIEnabled(...)`
  (`Party.py:667`) and Native's binding returns `set_hero_skill_ai_enabled`'s value
  (`party_bindings.cpp:448-450`) — and it answers `true` in the **idempotent** case, because the
  source's own early return is `return true`. The other two members answer `None`: their bindings are
  `void` (`:416-421`) and Reforged discards even that.
- **Native's `Enqueue` is the port's call path.** `set_hero_skill_ai_enabled` wraps its call in
  `game_thread::Enqueue`, which runs its callable **inline** when it is already on the game thread
  (`game_thread_methods.cpp:33-45`); the port's dispatcher *is* the game thread, so the call is made
  directly — the same note `UIManager.Keypress` carries.
- **The pet's target is compared by value, not by enum identity.** Native writes
  `target->allegiance == Constants::Allegiance::Enemy` — a word comparison — so the port compares
  `int(living.allegiance) != int(Allegiance.Enemy)`, which cannot raise on a word the enum does not
  name. The ported `Allegiance` carries the values.
- **The two sources disagree on one enum member's name and agree on every value.** Native's
  `Constants::HeroBehavior { Fight, Guard, AvoidCombat }` (`constants/hero.h:7-11`) against Reforged's
  `PetBehavior { Fight, Guard, Heel }` (`enums_src/hero_enums.py:16-19`). Only `Fight` is compared
  anywhere in this group, and it is `0` in both, so the port uses the ported `PetBehavior.Fight` and
  records the naming difference rather than resolving it.

### Round 6: the seek call, the player walk, and the hero control action

The last three mechanisms, and with them **every member of the class answers except the artifact**.

| member | source body | what it needs |
| --- | --- | --- |
| `SearchParty(search_type, advertisement)` | `search_party` (`party_methods.cpp:467-472`) — the function, then `g_party_search_seek_func(search_type, advertisement ? advertisement : L"", 0)` | the **wide advertisement** placed in the block (`PARTY_ADVERTISEMENT_OFFSET`), then one `U32_U32_U32` call: the type, that address, native's `0`. Returns the binding's bool |
| `Players.GetPlayerNameByLoginNumber(login_number)` | `player::GetPlayerName` → `GetPlayerByID(login)->name` (`player_methods.cpp:105-117`), then the binding's **narrowing** (``*name < 128 ? *name : '?'``, ``party_bindings.cpp:403-409``) | the world's player array by login — with native's own ``if (!player_id) player_id = GetPlayerNumber();`` — then the record's ``name`` pointer through the ported reader. A non-ASCII name answers the question marks the binding produces, because that is what the source returns |
| `Players.KickPlayer(login_number)` | `kick_player` (`:292-297`) → `L"kick %s"` into a 32-unit buffer → `chat::SendChat('/', buf)` | the same record walk, then the ported `chat.SendChat` on the command channel |
| `Players.InvitePlayer(agent_id_or_name)` | Reforged's two branches (`Party.py:455-470`): an **int** goes to `invite_player(player_id)` (`:310-315`, the same shape as kick with `L"invite %s"`); a **str** goes through `Player.SendChatCommand("invite " + require_real_name(name))`; anything else raises the source's own `TypeError` | the record walk and `chat.SendChat` for the first, `Player.SendChatCommand` plus Reforged's `name_obfuscation.resolve` for the second |
| `Heroes.UseSkill(hero_agent_id, slot, target_id)` | `PyParty::UseHeroSkill` (`party_bindings.cpp:424-447`) | the **control-action switch** (seven bases, ``ControlAction_Hero{N}Skill1``), the current target remembered, `agent::ChangeTarget` (the port's `Player.ChangeTarget`), `ui::Keypress` (the port's `UIManager.Keypress`) and the restore |

Details the port keeps, all of them the sources' own:

- **The hero control actions are not an arithmetic series.** ``Hero3Skill1`` is ``0xF5`` and
  ``Hero4Skill1`` is ``0x106`` — which is exactly why the binding writes a **switch** — so the port
  keeps a seven-entry mapping (`HERO_SKILL_ACTION_BASE`) rather than a formula, and anything outside
  heroes 1..7 does nothing, as native's ``default: return;`` does. The slot is added to the base:
  ``base + slot - 1``.
- **`UseSkill`'s target dance is asymmetric in the source, and the port leaves it that way.** The
  first change is guarded by ``target_id && target_id != GetTargetId()``; the restore by
  ``curr_target && target_id != curr_target``. With ``target_id == 0`` and a target set, the source
  therefore **re-targets the target it already had** — a no-op call it still makes. The port makes it
  too, and a test pins it.
- **The name is narrowed by the binding, not by the port.** ``GetPlayerNameByLoginNumber`` answers
  ASCII by construction: every code unit below 128 is kept and everything else becomes ``'?'``. The
  two chat members send the **un-narrowed** name, because their native bodies hand ``player->name``
  straight to ``swprintf``.
- **`InvitePlayer`'s string branch is Reforged's own, and its dependency is ported with it.**
  ``require_real_name`` is ``py4gwcorelib_src/system_settings/name_obfuscation/resolve.py``, the
  source's 25-line module, ported as written. That package's ``__init__`` re-exports the settings
  subsystem's controller, which is that subsystem's own port, so the directory here is an implicit
  namespace package: the source's own import path works and nothing of the subsystem is pulled in.
  ``PyNameObfuscator`` is the **injected runtime's** module, so the source's own ``except Exception``
  is the path taken — the name comes back unchanged, which is what the source's docstring says
  happens offline.
- **One bound is the port's, and it is the region's.** Native passes the caller's advertisement
  buffer whole; the port's block span holds ``PARTY_ADVERTISEMENT_CODE_UNITS`` (48) code units, so a
  longer advertisement is truncated **at the region's end** with its terminator kept — recorded here
  because it is the one thing in this group the source does not decide. The two chat commands are
  inside it several times over: native's own buffer for them is 32 units and the port keeps that
  bound where the source keeps it, before the send.

### The one member that does not answer

| member | why |
| --- | --- |
| `party_instance` | ``return PyParty.PyParty()`` (``Party.py:13-18``) — a native binding object constructed **inside the client**. An external port has nothing to construct and no object to hand back, and every member that used it here does what its own source line does instead: the reads go to the party context, the actions call the functions the binding called. This is the third member of the artifact kind in this project, with ``Player.player_instance`` and ``Agent.GetProfessionsTexturePaths``; it is reported and never stood in for |

### The call shapes, measured before anything calls them

Every remaining action ends in **one call to a function the port's own catalog already names** — all
twelve `party.*` resolvers are in `offsets/party.json`, byte-identical to native's. What the sources
do **not** settle is the ABI: how many words the callee takes and who releases them. A declaration is
a claim about the client's own code, and this project has been burned by one before
(`SendFrameUIMessage` had to be live-read as `ret 0xc`), so each function was read on the running
client before any stub calls it: `tests/probe_party_abi.py` (read-only, unelevated, nothing called) →
`tests/live_reports/party_abi.json`.

| function | declared | measured epilogue | what the port must emit |
| --- | --- | --- | --- |
| `party.set_difficulty_func` | `void __cdecl(uint32_t)` | `ret` + `cc` padding | `U32` — **done** |
| `party.set_ready_status_func` | `void __cdecl(uint32_t)` | `ret` + `cc` padding | `U32` |
| `party.party_search_seek_func` | `void __cdecl(uint32_t, const wchar_t*, uint32_t)` | `ret` + `cc` padding | `U32_U32_U32`, advertisement placed in the block |
| `party.party_search_button_callback_func` | `void __fastcall(void*, uint32_t edx, uint32_t*)` | **`ret 4`**, twenty times through the body | `FASTCALL_U32` — **built in round 2, driven by round 3's ten members** |
| `party.party_window_button_callback_func` | the same typedef | **bare `ret`** + `cc` padding | `FASTCALL_U32_CALLER_RELEASES` — **built in round 2, driven by `LeaveParty`** |
| `party.flag_hero_agent_func` | `void __cdecl(uint32_t, GamePos*)` | `ret` + `cc` padding | `U32_FLOAT_PTR` — **built in round 2** |
| `party.flag_all_func` | `void __cdecl(GamePos*)` | `ret` + `cc` padding | `FLOAT_PTR` (the port builds `{x, y, z, 0}` and passes its address) |
| `party.set_hero_behavior_func` | `void __cdecl(uint32_t, HeroBehavior)` | `ret` + `cc` padding | `U32_U32` |
| `party.lock_pet_target_func` | `bool __cdecl(uint32_t, uint32_t)` | `ret` + `cc` padding | `U32_U32` |
| `party.command_hotkey_disable_ai_func` | `void __cdecl(uint32_t, uint32_t)` | `ret` + `cc` padding | `U32_U32` |

**The one disagreement in that table is the sources' own, not this port's.** Native declares both
callbacks with a single typedef — `PartySearchButtonCallbackFn = void(__fastcall*)(void* context,
uint32_t edx, uint32_t* wparam)` (`party_methods.cpp:20`) — and calls each as that, so its compiled
call leaves the pushed `wparam` word for the *callee* to pop. The client's
`party_window_button_callback_func` ends with a **bare `ret`** and does not pop it, so that word
stays on native's stack on every `leave_party()`. This port follows the measurement rather than the
declaration, because the measurement is the client's own code; the difference is written down here so
it is a finding and not a silent choice.

### Work order

1. ~~The members that need no new call form~~ — **round 1**, six members above.
2. ~~The three call forms~~ — **round 2**, each with its offline witness executed in
   `tests/test_payload_offline.py`: `FASTCALL_U32` (2 register words + 1 pushed, callee releases) and
   its caller-releasing variant, plus a **word + pointer** form for
   `flag_hero_agent_func(uint32_t, GamePos*)`. The context and `wparam` arrays native builds on its
   stack go in the block's data region — the substitution this port already makes for every source
   pointer into its own frame.
3. ~~The ten party-button members~~ — **round 3**: the arrays at native's indices, the measured form
   per callback, and the return contracts checked against the source's own `return`s.
4. ~~The frame path for `ReturnToOutpost`~~ — **round 4**: `_FrameTree.hash_for_label`,
   `_FrameTree.by_label` and `Frame.child_native` built, `Frame.click` reporting native's bool, and the
   member itself native's expression.
5. ~~The flag group~~ — **round 4**: `FlagHero`, `UnflagHero`, `FlagAllHeroes`, `UnflagAllHeroes` over
   `flag_hero_agent_func`/`flag_all_func` and the source's own guards and sentinel.
6. ~~The behaviour group~~ — **round 5**: `SetHeroBehavior`, `SetSkillAIEnabled` and `SetPetBehavior`,
   each the binding's body with the source's own guards and conditional writes.
7. ~~`SearchParty`, the name and chat members, `UseSkill`~~ — **round 6**, which leaves
   `party_instance` as the class's one recorded artifact.
8. **The live pass**, with the owner present: these actions move the character between outposts and
   change the party, so it is a deliberate run — the reads first, then one action at a time.


## Ported data tables

The hero name lookup is a static table in the source, not runtime state, so it is
ported as data:

- `HeroType` — `GW::Constants::HeroID`, from Reforged's `Hero_enums.py`, values
  0..39.
- `HERO_NAME_TO_ID` — `kHeroNameMap` (`party_bindings.cpp:173-212`), 38 entries.
  `Devona` and `GhostOfAlthea` have ids in the enum but no entry in the table,
  so they do not resolve by name. That gap is the source's.
- `Hero` — the native `PyParty.Hero` helper, including its clamp to
  `0..ZeiRi` and its always-empty name. **Round 15 completed its bound surface**: the two constructors
  are the port's one `__init__`, `GetID`/`GetName`/`GetProfession` were there, and
  `FlagHero`/`__eq__`/`__ne__`/`__repr__` were **missing** — the binding defines all of them
  (`party_bindings.cpp:482-493`) and a caller could construct a `Hero` but not compare or print one.
  `FlagHero(idx)` is the source's own switch: `1..7` press `ControlAction_CommandHero{N}` through
  `GW::ui::Keypress` (the port's `UIManager.Keypress(key, 0)`), anything else answers `false` without
  pressing. `__repr__` is the source's format character for character, `"<Hero name='' id=1>"` — with
  the name it never assigns.

## The live pass, run (round 24, elevated, owner present)

The last item the objective owed ran on 2026-09-29 against `Gw.exe` pid 44052, elevated (the owner
approved the UAC prompts for each batch), with the owner watching the client.

**`hold` — and it changed nothing, which is its whole claim.** `unchanged=True`, `before == after`,
`hooks_original_after_disconnect: True`, exit 0. All 23 entries answered: the tick toggle with its own
value, the source's two no-ops (`SetTicked`, `RespondToPartyRequest`), the difficulty member whose mode
already matched, `SetHeroBehavior` for both heroes with the behaviour word their own records held, all
eight `SetSkillAIEnabled` slots per hero with the state their skillbars' `disabled` words held, and the
pet step skipped for a party with no pet record. Every call was refused by the source's own comparison
rather than by a guard this port added.

**The `act` steps, one batch at a time.** `flags` (the party's flag is unset, so it cleared rather than
set: `FlagAllHeroes` reported the skip and `UnflagAllHeroes` ran), `behaviour`, `skill-ai`, `search`
(the advertisement went out and was cancelled), `use-skill` (`UseSkill(hero 1, slot 1, target 0)` — the
control action, pressed), and `difficulty` (refused, see below). Each run reported
`hooks_original_after_disconnect: True` and, once the finding below was fixed, `before == after`.

### The defect the pass found: a flip-and-restore step is racy against a client that applies later

**The client applies a party change when it processes the command, not inside the call that sends it** —
but the first version of the steps assumed otherwise. Each flip-and-restore step read the value,
flipped it, and immediately restored from the value it had read; the member's own "is it already what I
want?" guard, reading the record that had *not* been updated yet, then refused the restore as
unnecessary. **The flip is what stayed.** The stage's before/after comparison was blind to it for the
same reason: its "after" read happened before the client had applied anything.

The evidence is in the runs' own snapshots — the change appears in the **next** run's `before`, not in
the run that made it:

| run | hero 1493 `behavior` | `disabled` | what it means |
| --- | --- | --- | --- |
| `flags` (first) | 1 | 0 | the state before anything was flipped |
| `behaviour` | **0** | 0 | the flip landed; the restore did not |
| `skill-ai` | 0 | **1** | that flip landed too; its restore did not |
| `difficulty` | 0 | 1 | carried both changes forward |

**The fix is a bounded wait that reports what it saw**: `_settle(read, expected)` in
`tests/probe_party_live.py` polls the client's own record after a step sends a change, up to
`SETTLE_TIMEOUT_SECONDS` (3 s), and the step computes and sends its restore **only once the flip is
visible**. Every wait's outcome is in the report (`settled: True/False`, the value seen, the time
waited), and the stage carries one verdict line for the whole run — so a client that never shows the
change is a fact in the report, not a hang and not a silent lie. The `difficulty` step uses the same
mechanism to tell "slow" from "refused".

**The client was put back, from the recorded original.** The two fields the first run left changed
(hero at position 1: `hero_behavior` 1 → 0, skillbar slot 1 → disabled) were restored by
`tests/probe_party_restore.py`, which reads the **recorded** pre-change state out of
`tests/live_reports/party_act_flags_live.json` (the `flags` step's `before` block — that step changes neither
field) and writes each value back with the port's own members, waiting for the client to show each one.
It reported `restored: True` for both heroes, `hooks_original_after_disconnect: True`, and a read-only
pass afterwards confirms hero 1493 back at `behavior 1, disabled 0` with hero 1494's `disabled 64`
untouched.

**Proved by re-running the two steps with the fix in place**: `behaviour` flipped 1 → 0 and back to 1,
`skill-ai` flipped the slot's bit 0 → 1 and back to 0, each with `settled: True` on both halves (≈110 ms
waits), `before == after`, and no field left changed.

### Two more findings, both about the client rather than the port

- **`SetHardMode` is accepted and ignored on this account.** The member called the source's function
  with the source's word and no guard refused it; the client's own `IsHardMode` flag then stayed false
  — polled for **ten seconds** by a dedicated diagnostic — and `IsHardModeUnlocked` reads false. So the
  probe's `difficulty` step now refuses when the account has no hard mode unlocked, saying so, and
  `act_readiness` carries the same condition; the member keeps the source's behaviour exactly (no guard
  was added to the port — the refusal is the probe's, and the finding is that the client cannot apply
  the change here).
- **A disconnect can refuse to free the decoder stub while a string decode is in flight.** One run's
  teardown raised `RuntimeError: pid 44052: 1 string decodes are still in flight, and the decoder stub
  the client will call cannot be freed while they are. Drain them before removing the bridge.` from
  `py4gw/game_thread/bridge.py` via `ConnectedClient.close()`. **The client's own bytes were already
  back** — the entry patches come out before the allocations are freed, and the next run's
  `entry_is_original` check passed — but one allocation stayed in the client until the next connect's
  install path repaired it. The real fix belongs to the connection, not to `Party`:
  `close()` calls `string_table._stop_warmup()`, and what it needs is a **drain** of the decodes already
  in flight before the bridge is removed. Recorded here because this is the run that found it.


- `tests/probe_party_live.py` — **the live probe, in three stages**, and the read stage has run:
  * ``reads`` (default, **unelevated**, no connection, nothing called): a read-only client stand-in
    over the live process runs every member whose answer is a read, **decides what the elevated
    ``hold`` stage would call** (`hold_plan`), **decides which ``act`` steps can even fire in the
    current map** (`act_readiness`), **and runs `client_state`** — the very function both elevated
    stages use for their before/after comparison — so the comparison cannot die on a read during the
    run. Every guard the acting stage applies is a read, so the whole plan is checkable before
    anything connects. Live on 2026-09-30 (pid 44052, unelevated, `elevated: false`): **runnable now —
    `flags`, `behaviour`, `skill-ai`, `difficulty`, `search`, `use-skill`, `party-add`**; **not now —
    `flag-hero`** (the party's flag reads `(inf, inf)`, so there is no set position to reuse), **`pet`**
    (no pet record in this party), **`party-kick`** (Norgu is not in this party), **`leave`** (1 player:
    the step needs someone else), and **`outpost`** (**the `DlgRedirect` frame is not on screen** —
    hash `3656530105` read through the frame array, which is exactly the condition `ReturnToOutpost`
    checks before it clicks). The state function answers too: size 3, normal mode, the flag at
    `(inf, inf)`, hero 1493 with behaviour 1 and no disabled slots, hero 1494 with behaviour 1 and
    `disabled = 64` (slot 7), no pet. **Run on 2026-09-30 against
    `Gw.exe` pid 44052, elevated: false — zero errors.** Party 76, leader agent 1189, own number 0,
    ``IsPartyLeader`` true; size 3 (1 player + 2 heroes, 0 henchmen), morale ``[[1189, 100]]``, others
    ``[]``; normal mode, not defeated, party and player loaded, nothing ticked; hero agent ids 1493 and
    1494; ``GetHeroIDByPartyPosition(0)`` 26 and ``GetHeroIdByName('Norgu')`` 1; **`IsAllFlagged` true
    with `GetAllFlag` = `[inf, inf]`** and **`IsHeroFlagged(0)` true** — both documented source
    limitations, answered live exactly as the source writes them; the party member's login 48, agent
    1189, connected, not ticked, and the name **"<character name redacted>"** through
    `GetPlayerNameByLoginNumber` — the member built in round 6, answering a real name; no pet in this
    party, which is the source's own zeroed record. Report: `tests/live_reports/party_reads_live.json`.
    **Re-run after round 21's removals** (same client, same stage, unelevated): `reads: 0 member(s)
    refused`, the `hold` plan unchanged at 23 entries of which 0 would write, and the same readiness
    table — which is what a change to the records' *surface* should look like when nothing in the party
    path used the names that were removed. The one member that did use one was the probe's own pet row,
    and the live stage is what said so (`§ Findings`, round 21).
  * ``hold`` (**elevated**, changes nothing): connects and drives the acting members with **the values
    the client already reports**, which the sources' own guards turn into refusals — so the read path,
    the guards and the answers are exercised while the state stays as it was, and the report compares
    the state before and after. **What it will call is decided from reads alone and printed by the read
    stage before anything connects**: live on 2026-09-30 (pid 44052, unelevated) the plan is **23
    entries and 0 of them would write** — the tick toggle with its own value, the two no-ops, the
    difficulty member whose mode already matches, `SetHeroBehavior` for each hero with the behaviour
    word the hero-flag record already holds, all eight `SetSkillAIEnabled` slots with the state the
    skillbar's `disabled` word already holds, and the pet step **skipped** because this party has no pet
    record. Its premise is also checked offline before it is ever run:
    `tests/test_probe_party_live_offline.py` drives the stage against a stand-in client and asserts
    that the members it calls make **no call at all** — which is what makes it safe to run before the
    owner has decided anything. That test is why one step is skipped rather than risked: a pet whose
    behaviour is not ``Fight`` and which holds a locked target would have its lock **cleared** by a
    call carrying the values it already has, because the source's own body leaves
    ``target_agent_id`` at ``0`` for every behaviour but ``Fight``. `_pet_hold_call` returns the
    arguments only when the source would write nothing, and the report says when it declined.
  * ``act`` (**elevated, owner present**): **all twelve steps are now written**, each with its restore
    where the source gives one, and **nothing runs unless the owner names the step**
    (``--allow flags,behaviour``). With no ``--allow`` it prints the plan and stops — **without
    connecting at all**, so the plan can be read at any time. The four that act on the party or the
    map are driven by arguments rather than guesses: ``--hero-number``/``--slot`` for `UseSkill`,
    ``--hero <name>`` for `AddHeroByName`/`KickHeroByName`, and ``--henchman <agent_id>`` for
    `AddHenchman`/`KickHenchman` — the henchman's id is a **live agent id only the owner can name**,
    and without it the member is left alone and the report says how to get one. Each step also refuses
    when the client's own condition is not met: a hero number that is not in the party, a party with
    nobody else in it (`LeaveParty`), a map that is not an outpost (the party changes), and
    `ReturnToOutpost` answers `False` when its button is not on screen rather than clicking something
    else. **The guards themselves are tested offline** (`tests/test_probe_party_live_offline.py`), so
    a run cannot do something the owner did not ask for by accident.
- **The elevated run is pre-flighted against the live data it will use** (round 22). The plan and the
  stages are two pieces of code computing the same thing from the same reads, so
  `tests/test_probe_party_live_offline.py` replays the **live** report: `LivePlanRehearsalTests` builds a
  stand-in from `tests/live_reports/party_reads_live.json`'s own state and asserts that `hold_stage`'s calls
  are the plan's entries, in the plan's order, with the same arguments, none of them refused by
  anything but the source's own guard, no client function called and the state unchanged;
  `ActStepRehearsalTests` replays each reversible acting step with the members patched to a recorder and
  asserts that every step calls its counterpart **with the value it read** — the hero's behaviour word
  out and back, slot 1's bit, the mode, the flagged position, the advertisement and its cancel. Both
  rehearsals were proved by breaking them: a step added to the stage and not the plan failed the first,
  and a restore passing the flipped value instead of the read one failed the second.
- **The elevated run is pre-flighted against the live data it will use** (round 22), and since round 23
  **all twelve acting steps** are covered: each one's exact calls — the member, its arguments and the
  order — are asserted against a recorder, including the steps that change the party (`AddHeroByName`,
  `KickHeroByName`, `AddHenchman`/`KickHenchman` with an owner-named id) and the ones whose guards make
  them refuse (`leave` in a party of one, `party-kick` for a hero who is not there, `party-add` outside
  an outpost, `flag-hero` with an unset flag). The connection's own failure modes are read through too:
  elevation is asserted before anything is written, the read-only setup closes and re-raises before the
  capability layer is reached, the install byte-checks every target first, and the probe's `with` block
  restores and re-raises — so a stage that raises mid-run still leaves the client as it found it.
- **The live read found a defect, and it is fixed.** `Players.GetAgentIDByLoginNumber(0)` answered
  ``0`` where the source answers the caller's own player's agent id: the member went through
  Reforged's ``WorldContextStruct.GetPlayerById`` — a search by ``player_number`` — instead of native's
  ``player::GetPlayerByID``, which **indexes the array** and maps a zero login to
  ``GetPlayerNumber()``. The two members that take a login number disagreed about what zero means, and
  `GetPlayerNameByLoginNumber` (built with native's own lookup) was the one that was right. The member
  now uses that lookup, a test pins all three cases, and live it answers **1189** — the player's own
  agent id, matching the party leader and the party member row.
- `tests/test_party_offline.py` — **65 tests**: the transcribed member lists are cross-checked
  against `Py4GWCoreLib/Party.py` itself, so they cannot agree with a wrong port; full parity across
  all five namespaces; no public member beyond the source; **the raising set derived from the
  module's own AST and compared with the one recorded — ``{"party_instance"}``**, so a member that
  starts raising again fails the suite and a member that is dropped from the recorded list without
  being built fails it too; the round-1 members **not** raising, with the no-op pinned structurally;
  the ten round-3 members driven against a **stand-in client** that records every region write and
  every call, so the arrays are checked by **value and index** (`ctx[9]` really holds the hero id,
  `ctx[0xb]` the tag, the button word where the client reads it), the callback and the **call form**
  are checked per member (`FASTCALL_U32` vs `FASTCALL_U32_CALLER_RELEASES`), and the return contracts
  are pinned member by member against the source's own `return`s; the four round-4 flag members
  against the **words and the form** they hand over (`U32_FLOAT_PTR` with the agent word, `FLOAT_PTR`
  without it), their guards, and the `HUGE_VALF` sentinel's own bits (`0x7F800000`); `ReturnToOutpost`
  driven end to end — the label's bytes and address, the hash the client answers, the array scan that
  finds the frame, the child lookup's two words, the click's two structs and its `kMouseClick2` send —
  with its two refusal paths (no frame for the label, no child) answering `False` without a click; the
  round-5 group against a **world context** stand-in, where what matters is the **conditional write**
  (the behaviour member sends only when the record's word differs, the AI member only when the slot's
  `disabled` bit disagrees with the request and answers `true` either way, and the pet member resolves
  a target only for `Fight`); and the round-6 group — the advertisement's bytes, its address and the
  three words of the seek call (plus the region bound and the refusal), the name walk with the
  binding's own narrowing and native's `login 0 → GetPlayerNumber()` case, both chat commands by id
  and the by-name branch through `Player.SendChatCommand` (with the source's `TypeError` for anything
  else), and `UseSkill`'s switch, target swap and restore in the source's order, including the
  restore that runs when nothing was changed; the documented constants; and the hero table.
- `tests/probe_party_abi.py` — the ten ABI measurements above, read-only and unelevated, with the
  report in `tests/live_reports/party_abi.json`.
- `tests/test_party.py` — 24 live tests, each checked against the party context
  or an invariant in a loaded map. The four members that were first ported from
  the wrong source — `GetPartySize`, `GetHeroCount`, `IsPartyLeader`,
  `IsPartyLoaded` — are each pinned. Run in a rich party in map 499 (Explorable):
  1 player, 2 heroes, 3 henchmen, 1 pet, `others = [23]`, so the non-empty branch
  of every list, lookup and flag path is exercised, not just its early exit.
- **The twenty-six acting members have now been called on a live client** — `§ The live pass, run`
  above is that run — except the steps whose client condition was not met in that map: the pet step (no
  pet record), `flag-hero` (the flag is unset), `party-kick` (Norgu is not in the party), `leave` (one
  player) and `outpost` (`DlgRedirect` not on screen) each refused with their reason instead of acting.
  Everything else the build claims is proven offline against stand-in clients and the measured ABIs.

## Round 25: the party-changing steps, and the press that crashed a client

The owner asked for the party-changing steps to be tested — add a hero, add a henchman, kick them,
leave the party. Three of the four went through; the fourth **crashed the client**, and that is the
finding this section exists for.

**What worked, with the evidence.** `AddHeroByName('Norgu')` and `AddHenchman(10)` both landed: the
step's own verdict is now "the party **holds** the member" (the array walk `GetHeroIDByPartyPosition`
performs, 0-based, and the henchman records' `agent_id`) rather than "the count grew", because adding a
hero who is already there is a no-op the client is right to ignore. `KickHeroByName('Norgu')` and
`KickHenchman(10)` both landed as well, and the hero kick only became possible after a bug in the
**probe's own guard** was fixed — see below.

**The crash.** `tests/probe_party_leave.py` called `Party.LeaveParty()` **once**, with the party holding
a hero and a henchman, and the client died:

```
*--> Crash <--*
Assertion: childId
P:\Code\Engine\Frame\FrApi.cpp(3916)
App: Gw.exe     BaseAddr: 00A20000     Build: 38888
When: 9/29/2026 15:29:37

Pc:00aa7bdb Fr:0701fca0 Rt:00c53fa7 Arg:00000f4c 09980480 09960180 09960000
```

`0xf4c` is 3916 — the assertion's own line — and the frames above it are the client's frame API and its
UI dispatch. What the member does is native's own body, unchanged
(`party_methods.cpp`, `leave_party`):

```cpp
if (!g_party_window_button_callback_func) return false;
if (!get_party_size()) return true;               // the source's only guard
uint32_t ctx[14] = { 0 };
ctx[0xd] = 1;
g_party_window_button_callback_func(ctx, 0, 0);   // the party window's button
return true;
```

So the press is the **party window's button callback**, and it was called with no party window on
screen — the frame the engine's own handler then walked did not have the child id it expected. **The
port is not wrong here and the source is not wrong**: Reforged calls this from inside the client, in the
state its own UI put it in, and the port reproduces that call exactly. What the crash establishes is the
**precondition** the source never had to state: the press belongs to a window, and an external caller
must have that window.

**What changed because of it, and what did not.**

* **The port's `LeaveParty` is untouched.** It is the source's body; adding a guard to it would be
  inventing one the source does not make.
* **The probe's `leave` step now refuses without that window.** `_party_window_on_screen()` walks the
  frame array for the party window's own hash from this port's offline table
  (`frame_names.NAME_TO_HASH`, `'Party'` → `3332025202`) — the same shape of check
  `ReturnToOutpost`'s `DlgRedirect` readiness row uses — so it costs nothing and calls nothing. The
  refusal names the crash in its own words, `STEPS` carries the warning, and two tests pin it: the
  step refuses a party of one, and it refuses when the window is not on screen **whatever** the party
  looks like.
* **The precondition is a hypothesis until it is retried**: the window is what the press belongs to, so
  having it should be enough — but that is not yet measured, and the next attempt must be a single,
  deliberate press with the owner watching.

### And the bug the same run found in the probe's own guard

`KickHeroByName` was reported as *"skipped: 'Norgu' is not in this party"* with Norgu standing in it.
The guard walked `range(1, hero_count + 1)`, but `GetHeroIDByPartyPosition` indexes the **hero array**,
0-based — the source's own `for index, hero in enumerate(heroes): if index == hero_position`
(`Party.py`) — so a party whose only hero sits at index 0 was invisible to it. Fixed to
`range(hero_count)`, pinned by a test that gives the stand-in exactly one hero at index 0, and proved
live: the next run kicked him.

### And the pacing the owner asked for

The client processes one command at a time, and the first batches fired calls back to back. Every
**acting** call now goes through `_act`, which spaces calls by `ACTION_INTERVAL_SECONDS` (**0.75 s**),
while reads are not paced at all — they touch no client machinery. Combined with `_settle` (which waits
for the client to show each change) and pauses between invocations, the steps are issued at a rate the
client can follow rather than at the rate the port can produce them.

- [x] **Round 25** — **the party-changing steps ran: add, kick, and the press that crashed the client.**
      The owner asked for these four, and three went through. **Add**: `AddHeroByName('Norgu')` and
      `AddHenchman(10)` both landed — the step's verdict is now "the party **holds** the member" (the
      0-based array walk, and the henchman records' `agent_id`) rather than "the count grew", because
      adding a hero who is already there is a no-op the client is right to ignore and a count would
      call that a failure. **Kick**: both landed (hero and henchman), and the hero kick only became
      possible after a **bug in the probe's own guard** was fixed — `GetHeroIDByPartyPosition` indexes
      the hero array **0-based** (the source's own `enumerate`), and the guard walked
      `range(1, hero_count + 1)`, so a party whose only hero sat at index 0 looked empty and the step
      said *"not in this party"*. Fixed, pinned by a test with one hero at index 0, and proved live by
      the next run kicking him. **Leave**: the owner's `tests/probe_party_leave.py` called
      `Party.LeaveParty()` once with a hero and a henchman in the party, and the client **crashed** —
      `Assertion: childId`, `P:\Code\Engine\Frame\FrApi.cpp(3916)`, `Gw.exe` build 38888
      (`0xf4c` = 3916 in the trace's own argument). The member is native's `leave_party` unchanged:
      it presses the **party window's** button callback (`g_party_window_button_callback_func(ctx, 0, 0)`
      with `ctx[0xd] = 1`) behind the source's only guard, `get_party_size()`. The press belongs to a
      window and there was none on screen. **The port's member is untouched** — a guard on it would be
      invented — and the **probe's step now refuses without the party window**, asked through this
      port's own offline hash table (`frame_names.NAME_TO_HASH`, `'Party'` → `3332025202`, the same
      shape as the `DlgRedirect` readiness check), with the crash named in the refusal, in `STEPS`, and
      in two tests. **Pacing**, because the owner called the first batches out: every acting call goes
      through `_act` with `ACTION_INTERVAL_SECONDS = 0.75` between them (reads are not paced), on top of
      `_settle`'s waits and pauses between invocations. Verified: probe offline file **34 tests OK**,
      offline suite **1765 tests** with the one pre-existing failure, scoped `pyright` **0 errors**.
- [ ] **Round 26** — with a restarted client: retry the `leave` press **once**, deliberately, with the
      party window on screen (the precondition is a hypothesis until it is tried), and the steps this
      map still refuses (`pet`, `flag-hero`, `party-kick` for a hero who is actually in the party,
      `outpost` when its button is on screen). If the press asserts again even with its window, the
      conclusion is that this member must not be called from outside at all, and it becomes a recorded
      divergence rather than a live step.

## Verification

## Progress

- [x] **Round 1** — six members that needed no new call form; the ABI of all ten functions the party
      actions call measured live and read-only; the `SetTicked`/`ToggleTicked` finding; the two
      source-vs-client disagreements recorded; `tests/test_party_offline.py` updated to pin the new
      state; this doc
- [x] **Round 2** — **the three call forms the rest of the class needs, each witnessed by execution**
      (`tests/test_payload_offline.py`, 122 tests):
      * `FASTCALL_U32` — two register words and one pushed word, the **callee** releasing it, which is
        the party-search callback's measured `ret 4`;
      * `FASTCALL_U32_CALLER_RELEASES` — the same shape with the **caller** releasing it, which is the
        party-window callback's measured bare `ret`;
      * `U32_FLOAT_PTR` — a word and the address of a `GamePos` the payload builds in its own frame,
        which is `flag_hero_agent_func`'s shape and the `&pos` the source passes.
      The witnesses read the arguments back through the client ABI and compare the stack pointer
      across two calls, so "pushed the right words" and "left the stack where it found it" are two
      separate answers — and the first version of `U32_FLOAT_PTR` was **caught by them**: it handed
      the callee a pointer four bytes into the record, and the floats read back `[-678.25, 0, 0]`
      instead of `[1234.5, -678.25, 0]`.
- [x] **Round 3** — the ten party-button members (`AddHero`, `AddHeroByName`, `KickHero`,
      `KickHeroByName`, `KickAllHeroes`, `AddHenchman`, `KickHenchman`, `LeaveParty`,
      `SearchPartyCancel`, `SearchPartyReply`), each with its `ctx`/`wparam` arrays placed in the
      block's data region at native's own indices and handed to the callback the source names, with the
      **measured** form for each of the two callbacks. `SearchPartyReply` returns the call's bool
      because the source's own body returns it (`Party.py:368`), and the other nine answer `None`
      because their bodies discard it — checked member by member, not assumed. `ReturnToOutpost` was
      in this round's plan and **moved out on measurement**: its three steps are the frame path, and
      the click's own answer (`ui::ButtonClick`'s bool vs Reforged's `click -> None`) is what stayed
      open until round 4. The raising set is 24 → **14**, and the count is now asserted
      from the code rather than remembered.
- [x] **Round 4** — **`ReturnToOutpost` and the flag group; the raising set is 14 → 9.** The frame path
      is finished on both sides: `_FrameTree.hash_for_label` and `_FrameTree.by_label` call the client's
      own `CreateHashFromWChar` over the label (placed in the block; the region moved from `0x340` to
      `0xE40` when the block-region guard showed the first choice sat inside the chat log buffer),
      `Frame.child_native` is `GetFrameById` + one `g_get_child_frame_id_func` call, and `Frame.click`
      now reports `ui::ButtonClick`'s bool — the one recorded divergence this needed, with every other
      caller in the port checked to be indifferent. **A defect was found on the way**: `_FrameTree.root`
      read the command's **status** word instead of the callee's return register, and its test fixture
      encoded the same mistake, so the two agreed with each other and neither with the dispatcher
      (`FRAME_TREE_PORT.md` §5). The four flag members are native's `flag_hero_agent`/`flag_all` over the
      two forms round 2 built, with `flag_hero_agent`'s guards, the `GamePos` record's own `zplane`, the
      `HUGE_VALF` sentinel for the two unflag members, and the sources' own argument-role disagreement
      (`FlagHero` passes an **agent id**, `UnflagHero` a **hero index**) carried rather than tidied.
- [x] **Round 5** — **the behaviour and pet group; the raising set is 9 → 6.** `Heroes.SetHeroBehavior`
      (the `hero_flags` walk, told only when the record's own `hero_behavior` differs),
      `Heroes.SetSkillAIEnabled` (four guards, the skillbar by `agent_id`, the slot's bit out of the
      record's `disabled` word, the zero-based slot, and `true` in the idempotent case — it is the one
      member of the three whose Reforged body returns the binding's bool) and `Pets.SetPetBehavior` (the
      controlled character's pet, a target only for `Fight` and only if it is a living enemy, then the
      lock and the behaviour on their own tests). Native's `Enqueue` needed no port: the port's call
      path is already the game thread. One source-vs-source naming difference recorded — Native's
      `Constants::HeroBehavior` third member is `AvoidCombat`, Reforged's `PetBehavior` spells it
      `Heel`; the values agree and nothing compares it.
- [x] **Round 6** — **the seek call, the player walk and the hero control action; the raising set is
      6 → 1, and the class is COMPLETE for this port's purposes.** `SearchParty` places the wide
      advertisement in the block and calls `party_search_seek_func` with `U32_U32_U32`;
      `Players.GetPlayerNameByLoginNumber` walks `player::GetPlayerByID` (with native's
      `login 0 → GetPlayerNumber()`) and applies the **binding's own ASCII narrowing**;
      `Players.KickPlayer`/`InvitePlayer` build the source's `L"kick %s"`/`L"invite %s"` and send them
      through the ported `chat.SendChat` on the command channel, with `InvitePlayer`'s string branch
      going through `Player.SendChatCommand` and Reforged's ported `require_real_name`;
      `Heroes.UseSkill` is the binding's control-action switch, its target swap and its restore.
      `tests/test_party_offline.py` now derives the raising set from the module's AST and pins it at
      `{"party_instance"}` — the one in-process artifact, which is `Player.player_instance`'s and
      `Agent.GetProfessionsTexturePaths`'s kind and is reported rather than stood in for.
- [x] **Round 7** — **the live probe is written, its read stage has run green, and it found and closed a
      defect.** `tests/probe_party_live.py` has three stages: `reads` (unelevated, no connection,
      nothing called — every reading member against the live client), `hold` (elevated,
      value-preserving: the acting members driven with the values the client already reports, which
      their own guards refuse, with a before/after comparison), and `act` (elevated, owner present: the
      steps that really act, each with its restore, **none of them run unless the owner names it**).
      The read stage answered **every member with zero errors** against `Gw.exe` pid 44052
      (`tests/live_reports/party_reads_live.json`), including the two documented source limitations
      (`IsAllFlagged` true with `[inf, inf]`, `IsHeroFlagged(0)` true) and the round-6 name member
      answering a real name. **And it found a defect**: `Players.GetAgentIDByLoginNumber(0)` answered
      `0` where the source answers the caller's own player's agent id — it used Reforged's
      `GetPlayerById` (a search) instead of native's `player::GetPlayerByID` (an index, with the zero
      login mapped to `GetPlayerNumber()`), so it disagreed with the name member beside it. Fixed,
      tested, and live it now answers 1189.
- [x] **Round 8** — **the live probe's own premise is verified offline, and one step that would have
      written was caught before any client saw it.** `tests/test_probe_party_live_offline.py` drives
      the `hold` stage against a stand-in client and asserts that every call it makes with the values
      the client already reports results in **no call at all** — the claim the stage's safety rests on,
      and the kind of claim that is wrong in exactly one member and quietly changes the game. Writing
      it found one: **the pet's step was not value-preserving when the pet's behaviour is not `Fight`
      and it holds a locked target**, because the source's own body leaves `target_agent_id = 0` for
      every behaviour but `Fight` and then writes the lock when it differs. That step is now taken only
      when the source would write nothing (`_pet_hold_call`), the report names the skip, and the four
      members that cannot write at all, the behaviour member, the eight skill-AI slots and the fighting
      pet case are each pinned as no-call.
- [x] **Round 9** — **the acting stage is complete: every step is written, and its guards are tested
      offline.** The `act` stage's twelve steps all exist now — including the five that were left as
      placeholders — and the steps that change the party or the map are driven by arguments the owner
      gives (``--hero-number``/``--slot``, ``--hero``, ``--henchman <agent_id>``) instead of by a
      choice this probe would otherwise have to make on their behalf: a henchman's id is a **live
      agent id**, so without ``--henchman`` the member is not called and the report says how to find
      one (target the henchman, read `Player.GetTargetID()`). Each step also refuses when the client's
      own condition is absent — a hero number not in the party, a party with nobody else in it, a map
      that is not an outpost — and the plan can be printed **without connecting at all**
      (``act`` with no ``--allow``), so it is reviewable at any time. Seven offline tests pin those
      guards, so a run cannot do something the owner did not name by accident.
- [x] **Round 10** — **the read half was audited against the sources member by member, and two members
      were calling the wrong functions.** With the class declared complete, every read whose body came
      from an earlier round was compared to Reforged's own line: the whole `Heroes` namespace, the
      counts, the state members, the morale walk and the player members match. Two did not.
      **`GetPartyTarget`** called `Party.IsPlayerLoaded` and `Player.IsAgentIDValid` where the source's
      own body calls `Party.IsPartyLoaded` and `Agent.IsValid` — nearly the same answers from
      **different members**, which is the kind of drift a value never shows; it now calls what the
      source calls. **`GetPartyLeaderID`** carried an invented `if not players: return 0` where the
      source is ``players[0]`` with no guard at all, so an earlier round had quietly added a default the
      source does not have; removed, and the member now reads the source's own two lines. Re-running the
      live read stage after both: **zero errors**, leader 1189, target 0, own number 0 — unchanged,
      which is what a correction to *which* member is called should look like. This round also wrote
      down the class's one body that is not the source's Python at all: `IsPlayerLoaded`, whose
      Reforged body is ``pass`` (§ Findings).
- [x] **Round 11** — **round 10's two corrections are pinned by tests, and the probe now says its
      verdict in words.** `GetPartyLeaderID` and `GetPartyTarget` were the two members that answered
      the right values while doing the wrong thing, so their replacements are pinned **by the calls
      they make**: an empty party raises ``IndexError`` from ``players[0]`` exactly as the source's line
      does (and no longer answers a default), the party target's guard is `Party.IsPartyLoaded`, and its
      validity test is `Agent.IsValid` — with both outcomes pinned. The action half got the same
      read-through the reads had in round 10: `SetTickasToggle`/`SetTicked`/`ToggleTicked`/`IsAllTicked`/
      `IsPlayerTicked`/`RespondToPartyRequest`/`SetHardMode`/`SetNormalMode` were each compared to
      Reforged's own lines and match (`ToggleTicked`'s two lookups then the no-op `SetTicked`, the
      difficulty guard pairs, the binding's ``tick`` being a *copy* of ``get_is_party_ticked``). And the
      probe gained `summary_lines`: the reading stage prints how many members refused, `hold` prints
      ``unchanged=…`` with the words *"A READING MOVED — defect"* when it is False, and `act` prints one
      line per step it ran — so the owner's run can be read at a glance instead of through the JSON.
- [x] **Round 12** — **the owner's first command is pre-flighted: what `hold` will call is decided from
      reads alone, live, before anything connects.** The stage's safety claim ("every call it makes is
      refused by the source's own guard") is decided entirely by reads, so the read stage now makes that
      decision and prints it: against `Gw.exe` pid 44052, unelevated and with nothing called,
      **`hold would call 23 thing(s); 0 of them would write`** — the tick toggle with its own value, the
      two no-ops, the difficulty member whose mode already matches, `SetHeroBehavior` for each hero with
      the behaviour word its record already holds, all eight `SetSkillAIEnabled` slots with the state
      its `disabled` word already holds, and the pet step **skipped** because this party has no pet
      record. Each plan entry carries what it would pass, what the client holds, and whether the
      source's comparison refuses it, so a call that *would* write is named in words (`WOULD WRITE: …`)
      on the summary line rather than discovered during the run.
- [x] **Round 13** — **the acting steps are pre-flighted too: which of them can fire in the current map
      is decided from reads, live, before anything connects.** Every guard the `act` stage applies is a
      read, so the read stage now reports `act_readiness` beside the `hold` plan — including the
      non-obvious one, whether `ReturnToOutpost`'s `DlgRedirect` button is on screen, which is asked
      through the frame array by the label's own hash from the port's offline table rather than through
      the client's hasher. Live against pid 44052: **seven steps can fire now** (`flags`, `behaviour`,
      `skill-ai`, `difficulty`, `search`, `use-skill`, `party-add`) and five cannot, each with its
      reason — no set flag position to reuse, no pet, Norgu not in the party, one player in the party,
      and **the `DlgRedirect` frame not on screen**. The same pass aligned one step with its own
      description: `difficulty` now checks `Map.IsOutpost()` like the plan always said it did, instead
      of calling into a client that would refuse it.
- [x] **Round 14** — **the elevated stages' own comparison function is proven read-only, and every read
      in it is now failure-proof.** `hold` and `act` both bracket their calls with `client_state()`, so
      if that function could not answer the run would die with a traceback and leave you without the
      report that says what happened. Two things closed that: the read stage now **calls
      `client_state()` itself** (unelevated, nothing connected), and three of its reads that went
      straight to the world context — the per-hero behaviour word, the per-hero `disabled` word and the
      pet record — now go through `_ask` like the rest, so a refusing read becomes a string in the
      report instead of an exception. Live: the state answers in full — size 3, normal mode, the flag at
      `(inf, inf)`, hero 1493 with behaviour 1 and no disabled slots, hero 1494 with behaviour 1 and
      `disabled = 64` (slot 7), no pet — which is also what the `hold` plan's arguments were built from.
      A pipe-truncated test run is what surfaced it: the report looked stale, and the cause was the
      harness's own `Select-Object -First` closing the program's stdout before it wrote its file, not
      the probe.
- [x] **Round 15** — **the member surfaces were audited a second way, by argument list, and the `Hero`
      class was found incomplete.** `tools/party_signature_audit.py` compares every member's **parameter
      names and defaults** between Reforged's `Party.py` and the port (the suite's parity test checks
      names and nesting, not signatures — and a member whose third argument is spelled differently is
      still callable by position and wrong by keyword). Result: **70 source members, 0 argument-list
      mismatches**, and the port's five extra members are all underscore-private (`_context`, `_party`,
      `_world`, `_is_party_connected`, `Pets._pet_info`). The same pass turned to the **bound class** the
      objective names: native's `Hero` binds `FlagHero`, `__eq__`, `__ne__` and `__repr__`
      (`party_bindings.cpp:482-493`) and the port carried **none of the four** — a caller could build a
      `Hero` and not compare or print it, and `FlagHero`'s seven hero command keybinds were unreachable.
      All four are now ported: `FlagHero` is the source's switch (`1..7` → `ControlAction_CommandHero{N}`
      through `UIManager.Keypress(key, 0)`, anything else `false` without pressing), the operators
      compare the hero ids as the source's do, and `__repr__` is the source's format character for
      character. Two tests pin them, and a third pins the **whole bound surface** against the binding's
      own `.def` list, which is what would have caught the gap.
- [x] **Round 16** — **the audit read a third dimension: does every member hand a value back?**
      `tools/party_signature_audit.py` now compares the two ASTs on that as well, because a member that
      answers `None` where the source returns a bool — or a value where the source returns nothing — is
      a caller's `if` behaving differently, and it is exactly what slipped once already
      (`SearchPartyReply` had no returned bool until round 3 checked the source's own `return`).
      Result: **five differences, and all five are already accounted for** — `IsPlayerLoaded` (the
      source's `pass` stub), `party_instance` (the recorded artifact), and `LeaveParty`,
      `Players.InvitePlayer`, `Players.KickPlayer` (native's own guards, which Reforged's Python does not
      need because it calls the binding; every path still answers `None`). `tests/test_party_offline.py`
      pins the comparison with that table transcribed, so a **sixth** difference fails the suite.
- [x] **Round 17** — **the third half of the porting rule was never checked: the members are now in the
      source's own order.** Names and nesting had a test; **order** had none, and
      `tools/party_signature_audit.py` — extended with an order comparison — found the port had grouped
      `Party`'s members by **subject** (identity, state, actions) and that `Players`, `Heroes` and
      `Pets` each had one member out of place (`GetPlayerNameByLoginNumber` after the two lookups, the
      three flag reads before the action block, `SetPetBehavior` last instead of first).
      `tools/reorder_party.py` moved the blocks **verbatim** — decorators, comments and bodies taken
      line for line, only their sequence changed — and the only content it dropped was the port's own
      section banners (`# ── party identity ──…`), which grouped members the source does not group.
      Verified three ways: the audit now reports *"35 members, in the source's order"* for `Party` and
      the same for each namespace; a line-multiset comparison against a pre-change copy accounts for
      every non-blank line (1439 → 1433, the six dropped banners, **nothing added**); and the live read
      stage re-ran unchanged (23 `hold` plan entries, 12 readiness rows). The tool is idempotent, and
      `tests/test_party_offline.py` now pins the order against the source's AST so it cannot drift back.
- [x] **Round 18** — **the party's enumerators and record fields were audited the same way the members
      were, and two port-invented things came out.** `PartySearchType` carried five upper-case aliases
      (`HUNTING = PartySearchType_Hunting`, …) beside the header's own enumerators — neither source has
      them, and nothing used them; and `HeroFlagStruct` named a ``Vec2f`` **value** `flag_ptr` and put a
      `flag` **property** on top answering `None` for a non-finite position, where ``context/hero.h``
      declares a plain ``Vec2f flag`` and neither source filters it. Both are gone: the enum keeps the
      header's five names (and the test now asserts the aliases' *absence*), and the record's field
      carries its own name with the property removed. The probe had the same slip in miniature — the
      search step passed a bare `0` — and now names `PartySearchType.PartySearchType_Hunting`. Live
      re-check afterwards: unchanged (23 `hold` plan entries, 12 readiness rows), and the party tests,
      the context tests and the full suite all green.
- [x] **Round 19** — **one of round 18's two findings was my own mistake, and it is reverted.** Round 18
      reported that `HeroFlagStruct`'s `flag_ptr` field and its `flag` property were port-invented,
      because Native's `context/hero.h:20` spells the field `flag`. That comparison used the wrong
      source: this class ports **Reforged's** `native_src/context/WorldContext.py`, and that file has
      both the `flag_ptr` name (`:249`) and the `flag` property (`:255-262`) that answers `None` for a
      non-finite pair — **the port was right all along**. The field and the property are restored, with
      the property now reproducing the source's own body (it builds a fresh `Vec2f` rather than handing
      back the record's view), and the test asserts both the value and the copy. The other finding —
      `PartySearchType`'s five upper-case aliases, which neither source declares and nothing used —
      stands, and its test still asserts their absence. **The lesson is in the port doc**: for a class
      ported from Reforged's Python, Reforged's Python is the shape authority and Native's header is
      only the layout authority. `tests/test_world_context_offline.py` (with the flag assertions) plus
      the party and probe suites are green again: **101 tests OK** in the three affected files, the full
      suite unchanged at 1743 with the one pre-existing failure, and scoped pyright **0 errors**.
- [x] **Round 20** — **the records were audited against the right source, and their names were the one
      thing still wrong.** Round 19's lesson was turned into a tool: `tools/context_struct_audit.py`
      parses Reforged's `native_src/context/*.py` (the shape authority) and this port's records, and
      compares **every field, its order and every declared member** for the eleven records the party
      reads. Result: **no field missing, no order difference, no declared member absent** — round 19's
      correction was not a one-off. What it did find is a naming inversion: this port named three
      records `PlayerPartyMemberStruct` / `HeroPartyMemberStruct` / `HenchmanPartyMemberStruct` and kept
      the sources' names as **aliases** at the bottom of `party_context.py`, where Reforged
      (`PartyContext.py:9,23,34`) and Native (`party_bindings.cpp:315`) both call them
      `PlayerPartyMember` / `HeroPartyMember` / `HenchmanPartyMember`. Both sources' names are now the
      classes' own names and the `…Struct` spellings are gone
      (`tools/rename_party_members.py` renamed them across the eight files that mentioned them, and the
      duplicate import/export entries it left behind were removed by hand); sizes are unchanged and
      asserted (`0xC`, `0x18`, `0x34`). The audit also lists, per class, **what this port adds beyond
      Reforged's declaration** — Native's own members (`InHardMode`, `IsDefeated`, `IsPartyLeader`,
      `GetPartySize`, `connected`/`ticked`, `calledTargetId`), the external reader's `bind_reader` glue,
      and a short list of name readers on the world-context records that is the next item, not a
      resting place. Verified: full offline suite **1743 tests, the one pre-existing failure**, scoped
      pyright on the six touched files **0 errors**, and the live client still untouched
      (`both hooked entries original: True`).
- [x] **Round 21** — **the audit's list of additions was adjudicated, and twenty members came out of
      the port on the sources' own evidence.** Round 20 left a report that named every member this port
      carried beyond Reforged's declaration and no ruling on them; this round ruled on each with the
      rule round 19 wrote down (Reforged's Python is the **shape** authority, Native's header the
      **layout** authority), and found the same defect in almost all of them: **a second spelling for
      one concept**. Removed: `PlayerPartyMember.calledTargetId`/`connected()`/`ticked()` (Native's
      header spellings — and Native's own binding renames them back to Reforged's before Python can see
      them, `party_bindings.cpp:504-511`); `PartyInfoStruct.GetPartySize()` (Native's C++ helper, no
      counterpart in either Python and no caller in the port — the count is `Party.GetPartySize`, where
      Reforged puts it); `PartyContextStruct.h0004`/`InHardMode()`/`IsDefeated()`/`IsPartyLeader()`/
      `requests`/`party_search` (the six C++ field and helper spellings beside Reforged's
      `h0004_array`/`in_hard_mode`/`is_defeated`/`is_party_leader`/`request`/`party_searches`, with
      `request` now carrying the source's own body instead of delegating to the twin);
      `HeroInfoStruct.name`/`name_enc` (Native's `wchar_t name[20]` and the port's own self-described
      "compatibility alias", with the decode moved into the source's `name_str`);
      `PetInfoStruct.name` (in neither source — Native's field is `pet_name`, Reforged's members are
      `pet_name_encoded_str`/`pet_name_str`); `SkillbarStruct.skill_ids` and `get_skill_by_id` (the
      second a snake_case twin of the source's `GetSkillById`, which now holds the body);
      `PlayerStruct.name_encoded`/`name`/`auxiliary_pointers` (two more spellings of one pointer read,
      and a factored-out walk now inlined into the source's `h0040_ptrs`). **What survived is one
      entry**: `bind_reader`, on the five records whose properties follow a target pointer — the read
      glue a controller **outside** `Gw.exe` needs and Reforged's in-process views do not. **The list is
      a gate now**: `tools/context_struct_audit.py` carries an `ADJUDICATED` table with those five and
      **exits non-zero** on any addition it does not name, and both offline test files assert the
      removals' **absence** by name. **The live stage found one more instance on its own**: the probe's
      pet row was still reading the removed `PetInfoStruct.name` — the offline suite was silent because
      nothing drove the read stage, and the live run said `1 member(s) refused` with the
      `AttributeError` in the report. The probe now reads `pet_name_str`, and
      `tests/test_probe_party_live_offline.py` drives `party_reads()` against a stand-in and fails on an
      `AttributeError` naming a port record (verified by re-introducing the defect and watching it
      fail). **And this project's own host tool had four of the removed names**: `main.py`'s
      world-context dump read `PlayerStruct.name`, `HeroInfoStruct.name`, `PetInfoStruct.name` and
      `SkillbarStruct.skill_ids` — the offline suite does not cover `main.py`, so nothing failed — and
      it now reads the sources' own `name_str`/`name_str`/`pet_name_str` and the record's declared
      `skills` array. Live afterwards: **`reads: 0 member(s) refused`**, `hold` unchanged at 23 calls
      of which **0 would write**, readiness table unchanged. Verified: the audit **exit 0** with 0
      unadjudicated additions, offline suite **1745 tests** with the one pre-existing failure, scoped
      `pyright` **0 errors** on the nine touched files, and `main.py` **0 errors** as well.
- [x] **Round 22** — **the owner's run is pre-flighted from the live data itself: the plan and the stage
      agree, and every reversible step carries its way back.** The plan is what the owner reads before
      deciding to run anything; `hold` and `act` are what actually run. They are two pieces of code
      computing the same thing from the same reads — the arrangement that drifts silently — so this
      round took the **live** report's own values and replayed both halves offline.
      * **`tests/test_probe_party_live_offline.py` → `LivePlanRehearsalTests`**: builds a stand-in from
        `tests/live_reports/party_reads_live.json`'s own state (hero 1493 behaviour 1 / disabled 0, hero 1494
        behaviour 1 / disabled 64, normal mode, the flag at `(inf, inf)`, no pet) and drives `hold_stage`
        against it. Three assertions: the calls the stage makes are the plan's entries **in the plan's
        order** (names, then names-plus-arguments), every planned call is `refused_by_the_source`, and
        the stage called **no client function at all** with the state identical afterwards. The guard was
        proved by adding a `SetTicked(False)` step to the stage that the plan does not describe: the
        rehearsal failed on the mismatched entry, exactly as it should.
      * **`ActStepRehearsalTests`**: replays each reversible acting step — `flags`, `behaviour`,
        `skill-ai`, `difficulty`, `search` — with the members patched to a recorder, and asserts the
        step calls its counterpart **with the value it read**: the hero's own behaviour word out and
        back (`SetHeroBehavior(1493, 0)` then `(1493, 1)`), slot 1's own bit (`(1493, 1, False)` then
        `(1493, 1, True)`), the mode the party was in (`SetHardMode` then `SetNormalMode`), the flagged
        position and its clear (`FlagAllHeroes(123.5, -678.25)` then `UnflagAllHeroes()`, and with the
        live unset `(inf, inf)` flag the step flags nothing and only clears), and the advertisement with
        its cancel. Proved the same way: making the behaviour restore pass the *flipped* value instead
        of the one it read failed the test.
      Both halves are the probe's own code, imported rather than copied, so a step added to the stage and
      not to the plan — or a restore that stops putting the value back — fails offline instead of
      appearing in front of the owner. Verified: **22 tests OK** in that file, offline suite **1753
      tests** with the one pre-existing failure, scoped `pyright` on the probe and its tests **0
      errors**, and the live read stage still **`0 member(s) refused`** with the same 23-entry, 0-write
      plan.
- [x] **Round 23** — **every step the owner can name now has its calls pinned offline, and the run's
      failure modes are read through.** Round 22 rehearsed the five reversible steps and the plan;
      this round finished the set, so **all twelve** `act` steps have their exact calls asserted
      against a recorder before anything is elevated:
      * `flag-hero` → `FlagHero(agent_id, x, y)` then `UnflagHero(1)` — the sources' own argument
        disagreement, pinned as the step writes it (an **agent id** one way, a **hero position** the
        other), and with the live `(inf, inf)` flag the step skips instead of flagging at infinity;
      * `use-skill` → `UseSkill(hero_number, slot, 0)`, driven by the owner's `--hero-number`/`--slot`
        and passing native's own `0` for "no target given";
      * `party-add` → `AddHeroByName('Norgu')`, plus `AddHenchman(4242)` **only** when the owner names
        the id (without it the report says how to get one), and nothing at all outside an outpost;
      * `party-kick` → `KickHeroByName('Norgu')` only when Norgu is in the party (he is not, live), and
        `KickHenchman(id)` for a named id;
      * `leave` → `LeaveParty()` only with somebody else present, and a report otherwise;
      * `outpost` → `ReturnToOutpost()`, whose `False` when its button is off screen is the **member's**
        own answer rather than a decision the step makes;
      * `pet` → `SetPetBehavior(0, 0)` for a pet that exists, nothing when the party has none.
      One of the new pins was proved by breaking it the same way: passing the hero's **position** where
      the source wants the **agent id** failed the `flag-hero` rehearsal with both argument lists in
      the message.
      **And the elevated run's failure modes were read through, because a probe that leaves a hook in a
      client would be worse than no probe**: `ConnectedClient.__init__` asserts elevation **before**
      anything is resolved or written, so a refused connection leaves the client untouched (measured —
      the unelevated example run failed cleanly and `entry_is_original` still reads `True`); a failure
      in any part of the read-only setup closes the reader and re-raises before the capability layer is
      reached; `_install_game_thread` resolves and byte-checks all four targets before it writes
      anything; and the probe drives the connection as a `with` block, whose `__exit__` calls
      `close()` — which restores both entries, frees what was placed and **re-raises** a handler
      failure after the client is put back. So a stage that raises mid-run still leaves the client as
      it found it. Verified: **29 tests OK** in the probe's offline file, offline suite **1760 tests**
      with the one pre-existing failure, scoped `pyright` **0 errors**.
- [x] **Round 24** — **the live pass ran, elevated, with the owner present — and it found a defect the
      offline gates could not.** `hold` first: **`unchanged=True`**, `before == after`,
      `hooks_original_after_disconnect: True`, all 23 calls refused by the sources' own comparisons.
      Then the acting steps, in batches the owner approved: `flags`, `behaviour`, `skill-ai`, `search`,
      `use-skill`, `difficulty`. **What it caught**: a flip-and-restore step computed its restore
      immediately, but **the client applies a party change when it processes the command, not inside
      the call that sends it** — so the member's own guard read the value it was replacing, refused the
      restore, and the flip stayed. The runs' snapshots show it: the change surfaces in the **next**
      run's `before`, never in the run that made it, which is also why the stage's before/after
      comparison was blind. Two fields were left changed by it. **The fix**: `_settle(read, expected)` —
      a bounded wait (3 s) that polls the client's own record and **reports what it saw** — placed
      between a flip and its restore, with one verdict line per run (`settled: True/False`). **The
      client was put back from the recorded original** by `tests/probe_party_restore.py`, which reads
      the pre-change state out of `tests/live_reports/party_act_flags_live.json` (that step touches neither
      field) and writes it back with the port's own members: `restored: True` for both heroes, hooks
      original afterwards, and a read-only pass confirming hero 1493 at `behavior 1, disabled 0` with
      hero 1494's `disabled 64` untouched. **Proved by re-running the two steps with the fix**:
      `behaviour` 1 → 0 → 1 and `skill-ai`'s bit 0 → 1 → 0, each `settled: True` on both halves
      (≈110 ms), `before == after`, nothing left changed. Two further findings recorded: **`SetHardMode`
      is accepted and ignored on this account** (`IsHardModeUnlocked` false; a dedicated diagnostic
      polled the client's own flag for **10 s** with no change), so the probe's step and its readiness
      row now refuse when the unlock is false rather than reporting a change nobody will see — the
      port's member keeps the source's behaviour, the refusal is the probe's; and **a disconnect can
      refuse to free the decoder stub while a string decode is in flight** (`bridge.remove` via
      `close()`: *"1 string decodes are still in flight"*), which left one allocation in the client until
      the next connect repaired it — the entry patches come out first, so the client was never left
      hooked, and the drain that is missing belongs to the connection, not to `Party`. Verified: probe
      offline file **32 tests OK**, scoped `pyright` **0 errors**, and the client clean after every
      batch.
- [ ] **Round 25** — the steps this map could not run, when the client's conditions are met: `pet` (a
      pet record), `flag-hero` (a set flag), `party-kick` (a hero that is in the party), `leave` (more
      than one player), `outpost` (the `DlgRedirect` frame on screen), and `party-add` — the one step
      that **changes the party** and restores nothing, which the owner has not yet chosen to run.
      the only item the objective still owes, and it needs an **elevated shell** (`py4gw.connect()`
      asserts elevation and a process cannot raise its own token) plus the owner's decision on which step
      may run; every guard, argument and restore it will use is now pinned offline against the live
      values, so the run is a confirmation rather than a discovery.
- [ ] **Afterwards, and outside these eleven records** — the same check found one instance in another
      module: `py4gw/context/gadget_context.py:59`'s `GadgetInfoStruct.name_encoded` property is in
      neither source (Native's `GadgetInfo` declares the field `name_enc` and no member reads it —
      `context/gadget.h:12-17`; Reforged has no such record), so it is the same kind of addition and
      that module's own pass is where it goes. Recorded here rather than fixed quietly, because the
      audit's scope is the eleven records the party reads and this one is not among them.
