# Porting rules

This project ports Py4GW Reforged and Py4GW_Reforged_Native. It does not design
its own way of doing what they already do. These rules exist because that line
was crossed: a fabricated readiness layer (`ReadinessReport`,
`read_readiness()`, `evaluate_readiness()`) and a fabricated `BitmapWords` type
were built on top of the source instead of porting it, and the docs then
presented them as though they were the library's contract.

Read this before adding anything.

## The rule

**Every public member must exist in Reforged Python or in Native, spelled the
same way.** If it is not there, it does not go here.

Corollaries:

- **No new layers.** No façade type, report object, registry, decorator, or
  "accessor" that the sources do not have. If Reforged calls
  `Map.IsMapReady()` before a read, this project calls `Map.IsMapReady()` before
  that read. It does not wrap reads in a gate of its own invention.
- **No new base types.** A helper type may only exist if the sources declare the
  corresponding type (`TargetStruct`, the native `InstanceInfo`, the
  `MISSION_BITMAP_ENTRIES` constants). "It would be convenient" is not a source.
- **Port the structure, not a summary of it.** Same method order, same
  short-circuits, same return values, same defaults. `Map.IsObservingMatch()`
  returns `True` when the map data is not loaded because the source's first
  short-circuit says so — not because that is the tidier answer.
- **A divergence is a finding, not a design choice.** If the source disagrees
  with the target, say so and stop. Naming it a "deliberate divergence" and
  shipping both is how a fabricated layer grows.
- **Native and Reforged are the sources of truth; `external/GwAu3` is a
  reference project.** Where Native and Reforged Python disagree, Native wins —
  for example `PickHighest` rather than `max`, and no `750` warm-up.

## Where each member may come from

| Source | May be ported | Example |
| --- | --- | --- |
| Reforged Python (`Py4GWCoreLib/`) | yes, as written | `Map.IsMapReady`, `Party.IsPlayerLoaded`, `Player.GetMissionsCompleted` |
| Native (`Py4GW_Reforged_Native/src/`) | yes, as written | `PyPlayer::GetIsPlayerLoaded`, `PickHighest`, `unlocked_maps`, `mouse_over_id` |
| Shared-memory and UI-widget modules | **no** — out of scope | `AccountStruct`, `AgentPartyStruct`, `GlobalCache/*` |
| `external/GwAu3` | **no** — reference only | — |
| Anything else | **no** | — |

## What a member must carry

1. **The source location** in the docstring — file and line, or the enum and
   constant, so a reviewer can check it in one step.
2. **The provenance class** where it is not obvious: `context` (readable game
   memory), `capture` (DLL-owned state that only exists with code in the
   client), `computed`, or `action`.
3. **A refusal with a reason** if it cannot work externally. Present the member,
   raise `NotImplementedError` naming the missing mechanism, and never return a
   plausible wrong value.

## Before adding anything

1. Grep both source trees for the member name. No hit means no member.
2. If it exists in Native but not Reforged's Python (or the reverse), say which
   one you are following and why.
3. If it needs a helper, check the source does not already have one.
4. If you are about to write a word like "layer", "façade", "accessor",
   "registry", "unified", or "abstraction", stop and re-read this file.

## Auditing what is already here

The port is not finished and the audit is not complete. To continue it, diff
each accessor class against its source and delete every member that is not in
one of them:

```powershell
# members of the port
Select-String -Path py4gw/player.py -Pattern '^    def '

# the same surface in the source
Select-String -Path C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib\Player.py -Pattern '^    def '
Select-String -Path C:\Users\Apo\Py4GW_Reforged_Native\src\GW\player\player_bindings.cpp -Pattern 'def_readonly|\.def\('
```

Known remaining deviations at the time of writing, all listed so they are not
mistaken for the source:

- `py4gw/client.py` `require_client()` — an addition, requested explicitly, that
  replaces a check each accessor class had copied.
- `py4gw/player.py` `GetUnlockedMaps`, `GetMouseOverID`, `IsAgentIDValid` — from
  native `PyPlayer`, which Reforged's Python `Player` does not wrap.
- `py4gw/player.py` private helpers (`_world`, `_party_players`, `_agent_by_id`,
  `_uuid_of`, `_faction`, `_bitmap_words`) — implementation detail, not public
  surface, but still not in the sources.
- `py4gw/map.py` private helpers (`_area`, `_area_value`, `_char_context`, ...)
  for members that do exist in Reforged.
- `py4gw/party.py` — complete. All five namespaces are present, and
  `tests/test_party_offline.py` fails if a member is dropped. Four members
  return a constant because the source cannot produce anything else; see
  [`PARTY_PORT.md`](PARTY_PORT.md).
- `py4gw/map.py` — partial port. Members not yet ported are listed at the bottom
  of the module as pending. That list is a plan, not source.
