# Party port

`py4gw/party.py` ports Reforged's `Py4GWCoreLib/Party.py`. The class surface is
**complete**: every member of `Party`, `Party.Players`, `Party.Heroes`,
`Party.Henchmen` and `Party.Pets` is present, and
`tests/test_party_offline.py` fails if one is dropped.

| | Count |
| --- | ---: |
| `Party` members | 35 |
| `Party.Players` | 6 |
| `Party.Heroes` | 23 |
| `Party.Henchmen` | 2 |
| `Party.Pets` | 4 |
| **Total** | **70** |
| Implemented (read a context, or compute from one) | 40 |
| Refuse with `NotImplementedError` | 30 |
| Members that write to `Gw.exe` | **0** |

Parity was checked against the source file itself, not against a hand-written
list: every `def` in `Py4GWCoreLib/Party.py` at four-space indentation (the
`Party` class) and eight-space indentation (the four nested namespaces) resolves
on the ported class, and no public member exists that the source does not
declare. Three members — `IsPlayerTicked`, `Heroes.FlagHero` and
`Heroes.SetHeroBehavior` — are declared with a space before the parenthesis
(`def IsPlayerTicked (`), which a naive scan misses.

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

## Findings: members limited by the source

| Member | Limitation |
| --- | --- |
| `Heroes.IsHeroFlagged(hero_party_number)` | Native handles **position 0 only**, reporting whether the all-flag is set; every other position returns `False`, with the source noting that per-hero flags are not reachable through the context it has (`party_bindings.cpp:366-376`) |
| `Players.IsPlayerTicked(login_number)` | Native treats the argument as an **array index**; `0xFFFFFFFF` means "this player". Reforged's Python names the parameter `login_number` and passes it straight through, so the name and the meaning disagree in the source. Reforged's name is kept for call-site parity |

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

Every action member is present and raises `NotImplementedError` naming the
mechanism it would need: `SetHardMode`, `SetNormalMode`, `ReturnToOutpost`,
`LeaveParty`, the party-search trio, `RespondToPartyRequest`, the tick trio,
`Players.InvitePlayer` / `KickPlayer`, the twelve `Heroes` actions,
`Henchmen.AddHenchman` / `KickHenchman`, and `Pets.SetPetBehavior`.

`Heroes.UseSkill` is worth noting: native drives it through
`GW::ui::ControlAction` keybinds on the game thread
(`party_bindings.cpp:424-447`), and Reforged's own source comments that "function
is not working atm".

## Ported data tables

The hero name lookup is a static table in the source, not runtime state, so it is
ported as data:

- `HeroType` — `GW::Constants::HeroID`, from Reforged's `Hero_enums.py`, values
  0..39.
- `HERO_NAME_TO_ID` — `kHeroNameMap` (`party_bindings.cpp:173-212`), 38 entries.
  `Devona` and `GhostOfAlthea` have ids in the enum but no entry in the table,
  so they do not resolve by name. That gap is the source's.
- `Hero` — the native `PyParty.Hero` helper, including its clamp to
  `0..ZeiRi` and its always-empty name.

## Verification

- `tests/test_party_offline.py` — 13 tests: the transcribed member lists are
  cross-checked against `Py4GWCoreLib/Party.py` itself, so they cannot agree with
  a wrong port; full parity across all five namespaces; no public member beyond
  the source; every disabled member refusing and naming itself; the documented
  constants; and the hero table.
- `tests/test_party.py` — 24 live tests, each checked against the party context
  or an invariant in a loaded map. The four members that were first ported from
  the wrong source — `GetPartySize`, `GetHeroCount`, `IsPartyLeader`,
  `IsPartyLoaded` — are each pinned. Run in a rich party in map 499 (Explorable):
  1 player, 2 heroes, 3 henchmen, 1 pet, `others = [23]`, so the non-empty branch
  of every list, lookup and flag path is exercised, not just its early exit.
