# AgentArray implementation plan

This document is the working plan for migrating the Guild Wars agent-array
surface into Py4GW Stealth. It is intentionally limited to the next piece of
the library. It does not define the complete agent API, combat helpers, or any
write operation.

The goal is to reproduce the useful external behavior already established by
the native and Reforged projects while keeping the work incremental:

1. Find the live agent-array pointer.
2. Take a bounded snapshot of the pointer table.
3. Reject stale entries using the movement table.
4. Expose cheap agent references first.
5. Read a complete agent structure only when a caller asks for its details.

## What the source projects establish

These points are source-backed observations, not assumptions about a new
design:

- The native resolver is `agent.agent_array_addr`.
- The resolved value identifies the live `GWArray<Agent*>` surface.
- The native code uses the agent pointer table without copying every agent
  into a new array.
- A non-null pointer is not enough to prove that an entry is current. Native
  code checks the corresponding movement entry before accepting an agent.
- Agent classification needs only a small part of the agent record. The
  native layouts place the common `type` field at `+0x9C`, the position at
  `+0x74`, and living-agent allegiance at `+0xB5`.
- Reforged normally obtains bounded agent IDs and category lists from its
  shared-memory projection. It materializes a single `AgentStruct` when a
  caller requests one agent's details.
- GwAu3 has useful evidence about bounded pointer-table reads, but its injected
  assembler path is not part of Stealth and must not be copied.

The native/Reforged layouts remain the authority for field definitions. This
plan does not replace them with GwAu3's older `0x1C0` copy size.

## Scope of the first implementation

The first implementation is complete only when it can do all of the
following for a selected, live client:

- resolve `agent.agent_array_addr` through the existing JSON pattern system;
- read the agent-array header using the existing external memory reader;
- validate the reported size and capacity against a configured safety limit;
- read the pointer table in one bounded bulk read;
- keep only non-null pointers;
- apply the movement-table validity check used by the native project;
- return lightweight references containing an agent ID and remote address;
- report whether the snapshot was truncated by the safety limit; and
- show the number of references, read cost, and rejected entries in a live
  verification script.

This stage must not materialize every `AgentStruct`, copy the full living-agent
layout, build all category lists, or add combat/pathing behavior.

## Implementation phases

### Phase 1 — Freeze the small contract

- [ ] Decide the public class name and location: `py4gw.context.agent_array`.
- [ ] Define a small immutable `AgentReference` value with at least:
  `agent_id` and `address`.
- [ ] Define a snapshot value containing the references, reported size,
  reported capacity, and a `truncated` flag.
- [ ] Define how an invalid, unreadable, null, or stale entry is represented.
  These outcomes must not be silently treated as the same thing.
- [ ] Keep all target-specific offsets and resolver names in the context
  module or the existing offset/pattern system, not in `Win32`.

Acceptance condition: the contract can be reviewed without requiring a full
agent structure definition.

### Phase 2 — Resolve the pointer table

- [ ] Load `agent.agent_array_addr` from the existing `offsets` directory.
- [ ] Use `PatternCatalog` and `RemoteScanner`; do not add a second signature
  format.
- [ ] Resolve the address once after connection and cache only the stable
  resolver result, following the existing connection cache rules.
- [ ] Revalidate the remote array header at each snapshot boundary.

Acceptance condition: a live test prints the resolved address and a valid
header for the selected client.

### Phase 3 — Read a bounded pointer snapshot

- [ ] Read the target array header with fixed-width x86 fields.
- [ ] Reject null buffers, impossible sizes, `size > capacity`, and values over
  the configured safety limit.
- [ ] Read the pointer buffer in one bulk operation rather than one read per
  array slot.
- [ ] Preserve the reported size and record whether the configured limit
  truncated the snapshot.

The initial safety limit should match the established native/shared-memory
boundary (currently 300) unless a live observation demonstrates that the
source contract has changed. It must be a named configuration value, not a
magic number hidden in traversal code.

Acceptance condition: the live harness reports one bounded pointer-table read
and never requests bytes beyond the configured limit.

### Phase 4 — Apply movement-table validity

- [ ] Read the movement-array header from the already migrated
  `AccAgentContext` surface.
- [ ] Read the movement pointer table in bulk for the current snapshot.
- [ ] Apply the native rule: an agent is current only when its corresponding
  movement entry exists and is non-null.
- [ ] Keep the pointer-table snapshot and movement snapshot tied to the same
  operation so their results are not mixed across refreshes.

Acceptance condition: the live result distinguishes raw non-null pointers from
references accepted as current agents.

### Phase 5 — Add lightweight classification data

This phase is deliberately after the basic snapshot. It should read only the
small fields required for classification:

- [ ] Read the common type field at the verified native offset.
- [ ] For living agents, read the verified allegiance field.
- [ ] Define a small classification value or enum that does not require a
  complete `ctypes` structure.
- [ ] Add category views only after the unclassified reference list is stable.

Classification must not cause every agent to be converted into a complete
`ctypes` object. If a classification field cannot be read safely, retain the
reference with an explicit unknown classification rather than discarding it.

Acceptance condition: a live check can report counts for the basic categories
without constructing a full structure for every entry.

### Phase 6 — Add lazy full-agent reads

- [ ] Reuse the migrated native/Reforged layout definitions for the complete
  agent record.
- [ ] Read one selected remote structure with `from_buffer_copy` only when a
  caller requests details.
- [ ] Keep the full record read separate from pointer-table refreshes.
- [ ] Expose the first useful fields through properties, including ID, type,
  position, and (when applicable) allegiance.
- [ ] Do not copy the full agent array merely to support an ID list or count.

Acceptance condition: requesting one selected agent produces a complete,
typed record while the ordinary array refresh remains bounded and lightweight.

### Phase 7 — Verification and performance record

- [ ] Add a live test script that requires a running Guild Wars client and
  clearly says so in its output.
- [ ] Record the selected PID, reported array size, accepted references,
  rejected/stale entries, and truncation state.
- [ ] Measure resolver, pointer-table, movement-table, classification, and
  one-agent materialization separately with `PerfCounter`.
- [ ] Run the existing offline checks for malformed headers, null buffers,
  invalid bounds, and fixed-width pointer decoding.
- [ ] Run Pyright and the relevant live test before considering the phase
  complete.
- [ ] Update `docs/RESEARCH.md` with observed values, client/build context,
  and any changed limitation.
- [ ] Update `docs/CONTEXT_INVENTORY.md` only when this milestone is actually
  verified; do not mark the full `AgentContext` migration complete for a
  pointer snapshot alone.

## Explicit non-goals for this sequence

The following are postponed until the bounded reference and lazy-read path is
proven:

- full `AgentLiving`, `AgentItem`, and `AgentGadget` helper surfaces;
- eagerly copying every agent on every refresh;
- combat, targeting, movement, or pathing behavior;
- injected assembler, remote threads, hooks, or process writes;
- reproducing the Reforged shared-memory manager inside Stealth;
- assuming that an address remains valid forever without revalidation;
- copying GwAu3's historical structure size or injected command path.

## Completion rule

We move to the next phase only when the current phase has a passing test or a
recorded live observation. A phase is not considered complete because the code
imports or because a pointer was found once. The evidence must show that the
operation is bounded, read-only, and consistent with the native validity rule.

