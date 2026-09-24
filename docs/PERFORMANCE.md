# Performance and timing

This document records how Stealth measures controller-side work and how the
current context-read cost should be interpreted.

## The performance counters

`py4gw/perf_counter.py` is a port of Reforged Native's ``PyProfiler`` module
(`include/profiler/profiler.h`, `src/profiler/profiler.cpp`,
`src/profiler/profiler_bindings.cpp`). It is the **timing** instrument: named
stopwatches over a rolling history, reported as
`(min, avg, p50, p95, p99, max)` in milliseconds.

It measures work performed by the external Python process. It does not measure
code executing inside Guild Wars and it does not change the target process.

The surface is the binding's, because that is what a Python caller in Reforged
reaches:

```python
from py4gw import PerfCounter

perf = PerfCounter()

perf.start("context.read")
try:
    snapshot = client.read_char_context()
finally:
    perf.end("context.read")

summary = perf.calculate_report("context.read")
print(summary.avg, summary.p95)
```

| Member | Source |
| --- | --- |
| `start(name)` / `end(name)` | `PyProfiler.start` / `.end` |
| `get_metric_names()` | `PyProfiler.get_metric_names` |
| `get_reports()` | `PyProfiler.get_reports` |
| `get_history(name)` | `PyProfiler.get_history` |
| `reset()` | `PyProfiler.reset` |
| `calculate_report(name)` | C++ `Profiler::CalculateReport`, reached through `get_reports` |

`start` overwrites an active start, so an unpaired `start` is discarded rather
than leaked. `end` without a matching `start` is a no-op.

## Reports and sampling

`MetricSummary` is the native `MetricSummary`, a
`std::tuple<double,double,double,double,double,double>`:

- `min`, `avg`, `p50`, `p95`, `p99`, `max`

There is no `count` and no metric name in it; `get_reports()` pairs each name
with its summary, as `CalculateReportAll` does. The stored sample count comes
from `get_history(name)`.

Two constants carry the native behaviour:

- **`MAX_SAMPLES = 600`** — the rolling history per metric. Until it fills, only
  the valid prefix participates in a report.
- **`RECORD_EVERY = 6`** — one averaged sample is stored every six completed
  measurements (`MetricData::push_frame_throttled`), holding
  `accumulator / frames_in_window`. This is not optional and not a parameter.

Percentiles come from a sorted copy at `int(n * p)` with no clamp, and `max` is
the last element of that copy. Note that `p50` is therefore
`sorted[int(n * 0.50)]`, which is *not* the median: ten samples of 1..10 report
`p50 = 6.0`, not 5.5. `tests/test_perf_counter_offline.py` pins this.

A metric name enters `get_metric_names()` on its first completed measurement,
before six have accumulated and any sample is stored — the source's
`GetMetricNames` walks its history map rather than counting samples.

`end` returns nothing, as the native `void` does, and there is no context
manager over `start`/`end` — the source has neither. A caller that needs a
timed block builds one from those two members; `py4gw/context/agent_array.py`
carries a private `_timed` helper for its optional per-stage timing, and
`main.py` has its own helper for the per-tab readout.

The frame stamp is supplied internally, as the binding does with
`PY4GW::System::GetTickCount64()`. The duration uses the high-resolution counter
the way `QueryPerformanceCounter` is used; using the tick for the duration would
round every sub-millisecond metric to zero.

The one deviation from the source is that this is an instance rather than a
static namespace. Native's `Profiler` is static because the injected runtime is
one process; the controller can hold more than one client, which is the same
reason every ported context reader is an instance.

## The two instruments are separate

Reforged has two performance systems and they answer different questions:

- **`py4gw/perf_counter.py`** (ported) — *how long did this operation take?*
- **`Py4GWCoreLib/py4gwcorelib_src/Profiling.py`** (**not yet ported**) — *what
  ran, and what called it?* A `sys.setprofile` tracer (`SimpleProfiler`) with
  caller→callee edges, plus `ProfileScope` and a per-frame `ProfilingRegistry`.

This document previously claimed `PerfCounter` covered both. It never did: the
Python module is a flow and callstack instrument with no counterpart in the
counters, and the port is tracked separately.

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

The AgentArray reader keeps its steady-state work separate: one bulk read for
the agent pointer table, one bulk read for the movement-pointer table, and a
small field reads for each non-null candidate, plus type, item-owner, living
effects, and allegiance reads for accepted references. It returns at most 300 accepted references
while allowing the target table itself to contain more entries. Complete
agent records are read only on demand; complete living snapshots are available
when frequent local queries are needed.

Complete living-agent data is available through an explicit refresh. That
refresh preserves the full native `AgentLivingStruct` for every current
living reference and stores one local snapshot for repeated queries. It does
not reduce the record to effects or health fields. The snapshot reports its
generation, age, and records rejected during refresh; a later refresh replaces
the previous records after pointer and ID validation.

The live AgentArray check can pass one `PerfCounter` into the reader. It
reports `agent_array.pointer_table`, `agent_array.movement_table`,
`agent_array.classification`, and `agent_array.agent_record` independently.
`agent_array.resolver` is recorded only when the JSON resolver first runs
during connection setup; later refreshes use the cached address. The offline
checks in `tests/test_agent_array_offline.py` cover malformed headers, null
buffers, truncation, and fixed-width pointer decoding.

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

For the complete AgentArray and living-agent path, use:

```text
python tests/perf_agent_array.py --samples 10
```

This reports the one-time resolver, repeated bounded AgentArray refresh,
complete living-record refresh, validity checks, and nested visible-effect,
equipment, and tag reads. It also prints the pointer-slot and returned-reference
safety limits for the selected client.

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

The readiness gate is measured separately, because it is re-evaluated on every
map-scoped read rather than cached:

```text
instance_info slot scan (one-time)   about 27.6 ms
char chain re-dereference            about 0.016 ms   (4 reads, 16 bytes)
full readiness gate                  about 0.073 ms   (p50, 5 context reads)
```

The scan is roughly 380 times the cost of the re-dereference, which is why the
scan is what gets cached and the gate is what gets re-evaluated. See
[`READINESS_GATE.md`](READINESS_GATE.md) for the full evidence.

One live AgentArray observation was approximately:

```text
agent_array.resolver       130.9 ms (one-time connection scan)
agent_array.read           2.1 ms
agent_array.pointer_table  0.45 ms
agent_array.movement_table 0.40 ms
agent_array.classification 1.19 ms
agent_array.reference_validation 0.045 ms
agent_array.agent_record   0.03 ms
agent_array.living_refresh 3.7 ms for 56 living records
```

Classification was the largest recurring stage in that sample because it
reads the common type and living allegiance fields for accepted references.
These values are observations, not universal benchmarks.
