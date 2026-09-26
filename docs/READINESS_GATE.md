# The map readiness gate

Guild Wars clears its map-scoped contexts while it changes maps. A read taken in
that window does not return a stale value from the previous map — the context is
**absent**, so the read either fails or resolves to nothing. Reforged therefore
checks the gate before touching map data, and so does this project.

Everything here is ported from `Py4GWCoreLib/Map.py` lines 40-118. Read
[`PORTING_RULES.md`](PORTING_RULES.md) first.

## The members

| Member | Source | Returns |
| --- | --- | --- |
| `Map.IsMapDataLoaded()` | `Map.py:42` | the map, character, instance, and world contexts all resolved |
| `Map.GetInstanceType()` | `Map.py:53` | the raw instance type, or `Loading` when the instance info is unavailable or undeclared |
| `Map.GetInstanceTypeName()` | `Map.py:65` | `InstanceTypeName.get(type, "Loading")` |
| `Map.IsOutpost()` | `Map.py:72` | instance type is `Outpost` |
| `Map.IsExplorable()` | `Map.py:80` | instance type is `Explorable` |
| `Map.IsMapLoading()` | `Map.py:88` | see below |
| `Map.IsObservingMatch()` | `Map.py:99` | see below |
| `Map.IsMapReady()` | `Map.py:109` | `IsMapDataLoaded() and not IsObservingMatch() and not IsMapLoading()` |

Two of these are easy to misread, and both are the source's behaviour, not a
tidier version of it:

```python
def IsMapLoading() -> bool:
    if not Map.IsMapDataLoaded():
        return True                       # not loaded reads as loading

    return Map.GetInstanceType() not in (
        InstanceType.Outpost.value,
        InstanceType.Explorable.value,
    )
```

```python
def IsObservingMatch() -> bool:
    if not Map.IsMapDataLoaded():
        return True                       # not loaded also reads as observing

    if not (char_context := GWContext.Char.GetContext()): return False
    return char_context.current_map_id != char_context.observe_map_id
```

So when the data is not loaded, `IsMapLoading()` **and** `IsObservingMatch()`
both return `True`. `IsMapReady()` still answers correctly because it starts with
`IsMapDataLoaded()`, and the two `True`s simply reinforce the refusal. Do not
"fix" either short-circuit: a caller reading `IsObservingMatch()` on its own is
entitled to the source's answer.

The client has exactly two real map phases — `Outpost` (0) and `Explorable` (1).
`Loading` is 2, and `IsMapLoading()` treats *anything* that is not one of the two
as loading, which is why an undeclared value is refused rather than trusted.

## What the members read

`GWContext.X.IsValid()` in Reforged is `X.GetContext() is not None`, tested
against facade objects its injected callbacks maintain. This project's readers take
no callbacks, so the equivalent is whether the reader resolved the context on that
read. Each `_char_context()`, `_map_context()`, `_instance_info_context()` and
`_world_context()` helper returns `None` when the read fails, and that `None` is
what `IsMapDataLoaded()` tests.

Nothing is cached. The gate is re-evaluated on every call, so a map change is
noticed by the first read that lands inside it. There is no window to expire and
no time-to-live anywhere in this project.

## IsPlayerLoaded is built on this gate

Native `PyPlayer::GetContext()` (`player_bindings.cpp:141`) does the map check
first and abandons the whole context refresh when it fails:

```cpp
auto instance_type = GW::map::GetInstanceType();
bool is_map_ready = GW::map::GetIsMapLoaded() && !GW::map::GetIsObserving()
    && instance_type != GW::Constants::InstanceType::Loading;
if (!is_map_ready) { ResetContext(); return; }
```

`Party.IsPlayerLoaded()` is the port of `GetIsPlayerLoaded`
(`player_bindings.cpp:30`, "parity with legacy
`GW::PartyMgr::GetIsPlayerLoaded(-1)`"): the map must be ready, the player number
must be readable, and the party member whose `login_number` matches it must
report `connected()`. Otherwise `False`.

Reforged's Python `Player.IsPlayerLoaded` adds a tail — world context, agent
validity, and `Agent.GetInstanceUptime(agent_id) > 750` — that runs only when no
party member matches, and can return `True` where Native returns `False`. The
`750` appears nowhere in the native tree. This project follows Native; see
[`PLAYER_PORT.md`](PLAYER_PORT.md).

## Verifying it live

`examples/readiness.py` prints every gate member and has a `--watch` mode for
watching the values change across a zone.

```text
IsMapDataLoaded    True
GetInstanceType    1 Explorable
IsMapLoading       False
IsObservingMatch   False
IsMapReady         True
```

## What is not here

A previous revision of this file documented a `ReadinessReport`,
`read_readiness()` and `evaluate_readiness()`. Those were invented, had no
counterpart in Reforged or Native, and have been deleted along with
`py4gw/context/readiness.py`. If any doc, test, or example still refers to them,
that reference is wrong.
