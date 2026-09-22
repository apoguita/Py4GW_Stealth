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
  `+0x74`, and living-agent allegiance at `+0x1B5`.
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
- read only the small native `agent_id` field needed for validation;
- apply the movement-table validity check used by the native project;
- return lightweight references containing an agent ID and remote address;
- report whether the snapshot was truncated by the safety limit; and
- show the number of references, read cost, and rejected entries in a live
  verification script.

This stage must not materialize every `AgentStruct`, copy the full living-agent
layout, build all category lists, or add combat/pathing behavior.

## Implementation phases

### Phase 1 — Freeze the small contract

- [x] Decide the public class name and location: `py4gw.context.agent_array`.
- [x] Define a small immutable `AgentReference` value with at least:
  `agent_id` and `address`.
- [x] Define a snapshot value containing the references, reported size,
  reported capacity, and a `truncated` flag.
- [x] Define how an invalid, unreadable, null, or stale entry is represented.
  These outcomes must not be silently treated as the same thing.
- [x] Keep all target-specific offsets and resolver names in the context
  module or the existing offset/pattern system, not in `Win32`.

Acceptance condition: the contract can be reviewed without requiring a full
agent structure definition.

### Phase 2 — Resolve the pointer table

- [x] Load `agent.agent_array_addr` from the existing `offsets` directory.
- [x] Use `PatternCatalog` and `RemoteScanner`; do not add a second signature
  format.
- [x] Resolve the address once after connection and cache only the stable
  resolver result, following the existing connection cache rules.
- [x] Revalidate the remote array header at each snapshot boundary.

Acceptance condition: a live test prints the resolved address and a valid
header for the selected client.

### Phase 3 — Read a bounded pointer snapshot

- [x] Read the target array header with fixed-width x86 fields.
- [x] Reject null buffers and impossible `size > capacity` values; cap the
  inspected slot count at the configured pointer-table limit.
- [x] Read the pointer buffer in one bulk operation rather than one read per
  array slot.
- [x] Preserve the reported size and record whether the configured limit
  truncated the snapshot.

The pointer-table scan limit and the returned-reference limit are separate.
The native table can contain more entries than the shared-memory projection
publishes. The initial returned-reference limit should match the established
native/shared-memory boundary (currently 300), while the pointer-table scan
limit must be a separate named safety value. Neither limit may be a magic
number hidden in traversal code.

Acceptance condition: the live harness reports one bounded pointer-table read
and never requests bytes beyond the configured limit.

### Phase 4 — Apply movement-table validity

- [x] Read the movement-array header from the already migrated
  `AccAgentContext` surface.
- [x] Read the movement pointer table in bulk for the IDs encountered in the
  pointer-table scan.
- [x] Read each candidate's native `agent_id` field at the verified common
  agent offset (`+0x2C`), without materializing the full structure.
- [x] Apply the native rule: an agent is current only when its movement entry
  exists at that `agent_id` and is non-null.
- [x] Keep the pointer-table snapshot and movement snapshot tied to the same
  operation so their results are not mixed across refreshes.

Acceptance condition: the live result distinguishes raw non-null pointers from
references accepted as current agents.

### Phase 5 — Add lightweight classification data

This phase is deliberately after the basic snapshot. It should read only the
small fields required for classification:

- [x] Read the common type field at the verified native offset.
- [x] For living agents, read the verified allegiance field at `+0x1B5`.
- [x] Read living effects at `+0x13C` and item owner at `+0xC4` for native
  category views.
- [x] Define a small classification value or enum that does not require a
  complete `ctypes` structure.
- [x] Add basic category views only after the unclassified reference list is
  stable.

Classification must not cause every agent to be converted into a complete
`ctypes` object. If a classification field cannot be read safely, retain the
reference with an explicit unknown classification rather than discarding it.

The classification pass now includes the native dead and owned-item category
inputs. The complete living record remains the source for all other effect
properties and nested data.

Acceptance condition: a live check can report counts for the basic categories
without constructing a full structure for every entry.

### Phase 6 — Add lazy full-agent reads

- [x] Reuse the migrated native/Reforged layout definitions for the complete
  agent record.
- [x] Read one selected remote structure with `from_buffer_copy` only when a
  caller requests details.
- [x] Keep the full record read separate from pointer-table refreshes.
- [x] Expose the first useful fields through properties, including ID, type,
  position, and (when applicable) allegiance.
- [x] Revalidate the selected pointer-table slot and movement entry immediately
  before materializing a complete record.
- [x] Do not copy the full agent array merely to support an ID list or count.

Acceptance condition: requesting one selected agent produces a complete,
typed record while the ordinary array refresh remains bounded and lightweight.

### Phase 7 — Complete living-agent snapshots

- [x] Preserve the complete `AgentLivingStruct` rather than reducing living
  agents to a small status projection.
- [x] Add an explicit refresh that reads complete records for current living
  references and stores them as one local snapshot.
- [x] Replace the previous snapshot when refreshing; do not reuse records
  whose pointer or ID no longer validates.
- [x] Expose snapshot generation, local age, and stale/unreadable counts.
- [x] Serve repeated queries by agent ID from the local complete snapshot.
- [x] Measure the complete living refresh separately with `PerfCounter`.
- [x] Preserve the native effects bitmap, effect-bit properties, and bounded
  visible-effects list on complete living records.
- [x] Read optional equipment and tag records through their target pointers.

The current snapshot also exposes `owned_items`, `dead_allies`, and
`dead_enemies`, matching the native shared-memory category contract.

The complete snapshot retains effects, movement, combat, equipment pointers,
tags, and every other field in the native `0x1C4` living record. It is a local
copy with an explicit refresh boundary, not a claim that the target remains
unchanged between reads.

This completes the bounded external record path, not the entire Reforged
`AgentArray` API. Source-compatible category/materialization methods and the
Reforged `corpse_exploit_signature` helper remain tracked in
[`CONTEXT_PARITY_AUDIT.md`](CONTEXT_PARITY_AUDIT.md).

Acceptance condition: a live check captures all current living records,
reports refresh cost and rejected records, and returns repeated field queries
without another process read.

### Phase 8 — Verification and performance record

- [x] Add a live test script that requires a running Guild Wars client and
  clearly says so in its output.
- [x] Add a repeatable AgentArray performance harness for multi-refresh timing
  and nested living-data access.
- [x] Record the selected PID, reported array size, accepted references,
  rejected/stale entries, and truncation state.
- [x] Measure the pointer-table, movement-table, classification, and one-agent
  materialization stages separately with `PerfCounter`. The resolver remains a
  one-time connection step and is measured when it is first initialized.
- [x] Run offline checks for malformed headers, null buffers, invalid bounds,
  truncation, and fixed-width pointer decoding.
- [x] Run Pyright and the relevant live test before considering the phase
  complete.
- [x] Update `docs/RESEARCH.md` with observed values, client/build context,
  and any changed limitation.
- [x] Update `docs/CONTEXT_INVENTORY.md` now that the bounded traversal,
  classification, lazy records, live timing, and offline checks are verified.
  This does not mark unrelated AgentContext roots complete.

## Explicit non-goals for this sequence

The following remain postponed after the bounded reference and lazy-read path
is proven:

- future effect APIs that require native writes or callback-driven updates;
- additional context-owned effect arrays outside `AgentLiving`;
- eagerly copying non-living agents on every refresh;
- combat, targeting, movement, or pathing behavior;
- injected assembler, remote threads, hooks, or process writes;
- reproducing the Reforged shared-memory manager inside Stealth;
- assuming that an address remains valid forever without revalidation;
- treating the final pre-read check as an atomic snapshot guarantee;
- copying GwAu3's historical structure size or injected command path.

## Completion rule

We move to the next phase only when the current phase has a passing test or a
recorded live observation. A phase is not considered complete because the code
imports or because a pointer was found once. The evidence must show that the
operation is bounded, read-only, and consistent with the native validity rule.
