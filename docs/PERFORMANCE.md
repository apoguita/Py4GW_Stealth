# Performance and timing

This document records how Stealth measures controller-side work and how the
current context-read cost should be interpreted.

## What `PerfCounter` measures

`PerfCounter` uses Python's `time.perf_counter_ns()` and reports elapsed time
in milliseconds. It measures work performed by the external Python process. It
does not measure code executing inside Guild Wars and it does not change the
target process.

Each counter stores a bounded history for named operations:

```python
from py4gw import PerfCounter

perf = PerfCounter()

with perf.measure("context.read"):
    snapshot = client.read_char_context()

report = perf.report("context.read")
print(report.average_ms, report.p95_ms)
```

`measure()` always closes the timing scope, including when the wrapped code
raises. The other forms are useful when the operation is split across helper
methods:

```python
perf.start("scanner.find")
try:
    address = scanner.find(pattern)
finally:
    elapsed_ms = perf.end("scanner.find")
```

`record(name, elapsed_ms)` adds a known duration directly. `history(name)`
returns the stored samples, `metric_names()` lists measured names, and
`reports()` returns a report for every named metric.

## Reports and sampling

`PerformanceReport` contains:

- `count`
- `minimum_ms`
- `average_ms`
- `p50_ms`
- `p95_ms`
- `p99_ms`
- `maximum_ms`

The default history size is 600 samples per metric. Use
`PerfCounter(history_size=...)` to change that bound. The default
`samples_per_record=1` stores every completed measurement. Setting
`samples_per_record=6` averages each group of six measurements before storing
it, matching the grouped averaging behavior used by the native profiler.

This class is not a Python call-stack profiler. It answers “how long did this
operation take?”; it does not explain every Python function that ran inside
the operation.

## Context connection and steady-state reads

The context readers have two different kinds of work:

1. The JSON `context.base_ptr` signature scan locates a stable module-global
   pointer location. This is connection/setup work.
2. The reader follows the current values from that location to
   `GameContext`, then to a selected context such as `CharContext` or
   `Cinematic`, and reads the structure. Contexts with their own global
   resolver, such as `PreGameContext`, `GameplayContext`, `ServerRegion`,
   `InstanceInfo`, and `AvailableCharacterArray`, follow the same
   cache-then-reread pattern. `TextParser` follows the already-cached
   `GameContext` pointer instead of running a separate signature scan. This is
   per-snapshot work.

`ConnectedClient` initializes the resolver-backed contexts during connection.
That performs each required scan once and caches the stable resolver address.
Later context reads do not scan the module again. They re-read the
dynamic pointer chain because those object addresses can change during login,
logout, map changes, and other client state transitions.

This follows Reforged Native's `GW::Context` behavior: initialization resolves
`g_base_ptr` once, while `GetGameContext()` and `GetCharContext()` follow the
current pointer values whenever they are called.

Call `context.initialize()` again only when an explicit resolver refresh is
wanted. A new `ConnectedClient` also creates a new cache. A process restart or
module reload requires a new connection; cached addresses must never be
shared between processes.

## Main UI timing

The root `main.py` window measures each context read separately with the metric
names `CharContext.read`, `GameContext.read`, `PreGameContext.read`,
`Cinematic.read`, `GameplayContext.read`, `ServerRegion.read`,
`InstanceInfo.read`, `TextParser.read`, `AvailableCharacters.read`, and
`PartyContext.read`, `GuildContext.read`, and `AccAgentContext.read`. The latest duration is shown in
the corresponding `Client data` status line.

The UI timing does not include formatting the table after the snapshot is
returned. Derived properties such as `GWArray` views may perform additional
remote reads while the table is being built.

## Detailed live harness

Use the direct harness when diagnosing a slowdown:

```text
python tests/perf_context.py
```

Optional arguments:

```text
python tests/perf_context.py --samples 20
python tests/perf_context.py --pid 1234
```

The harness measures, separately:

- scanner initialization;
- one-time context initialization and its signature scan;
- the pattern scan by itself;
- the dynamic pointer chain;
- cached `context.resolve_address()`;
- complete `context.read()`;
- a structure read at an already-known address; and
- the individual array/property views used by the UI.

It also counts remote-read calls and requested bytes. A high elapsed time with
many large reads points to transport or scanning. A high elapsed time with no
remote reads points to local Python decoding or formatting. A high read count
from an array view indicates a candidate for a future batched-read design.

## Current live observation

On one tested client, before caching, the pattern scan accounted for roughly
4 ms of a 4–5 ms context read. After moving the scan to connection setup:

```text
connection initialization   about 3.8 ms
cached address resolution   about 0.012 ms
cached context.read         about 0.026 ms
```

The values are evidence from one client and host, not a performance guarantee
for every Guild Wars build or machine. Run the harness again after changing
the scanner, resolver, structure reader, or UI property set.
