# Pathing migration plan

Pathing is a first-class part of the Guild Wars data model. It is not an
optional detail of `MapContext` and it is not being replaced by the spawn
arrays.

## Source relationship

The source-defined relationship is:

```text
MapContext (+0x74 path_ptr)
  -> PathContext (+0x00 static_data_ptr)
    -> MapStaticData (+0x18 pmaps_array)
      -> PathingMap records
         -> trapezoids, sink/x/y nodes, and portals
```

`MapContext.props_ptr` points to the separate `PropsContext`, which owns
map-prop records and the prop arrays used by the Reforged travel-portal helper.
The native layouts are defined in `context/map.h` and `context/pathing.h`.
The Reforged Python implementation is in
`Py4GWCoreLib/native_src/context/MapContext.py`.

## Current Stealth status

Stealth declares the Reforged pathing/props structures and native C++ pathing/
props record views with checked x86 sizes and source field ordering. It reads
the fixed `MapContext` root and its three bounded spawn arrays, plus the
current `PathContext`, `MapStaticData`, and bounded `PathingMap` root records.
It exposes raw child-buffer addresses and counts and now reads bounded
contiguous arrays of trapezoids, sink nodes, X nodes, Y nodes, and portals.
It follows trapezoid neighbors, X/Y node children, portal pairs and portal
trapezoid lists. It also reads the reachable `PropsContext` groups, prop models,
map-prop pointer array, each `MapProp`'s two source pointer properties, and the
`MapStaticData` blocking-prop values.

These direct reads are live-verified. Reforged's runtime `.py` and native C++
declare `SinkNode.trapezoid_ptr_ptr` and its pointer-list helpers, while its
`.pyi` describes a single pointer. The live observation found direct pointers
into each owning trapezoid array, not the pointer-to-pointer shape. Source
inspection found that Reforged's snapshot leaves `sink_nodes` empty and the
searched source contains no active consumer of those helpers. The source
helpers remain represented and offline-tested for parity, but are not used to
interpret the live field and do not affect the active pathing reads.
Those offline tests verify only the implemented helper logic; they do not prove
that the unused source interpretation matches the client. The raw live value
is preserved as observed. Portal's pointer-to-pointer field
has a similar runtime/stub mismatch; that is a separate source-backed behavior
and is not changed by the SinkNode finding. Source pathing snapshots (including
paired-portal indices) and the travel-portal helper remain live-verified. The
source pathing cache/facade helpers are migrated and live-tested; automatic
callback registration is not ported.

## Immediate migration boundary

The first pathing step will read the current target context structures only:

1. `PathContext` root; **implemented**;
2. `MapStaticData` root; **implemented**;
3. bounded `pmaps_array` headers and `PathingMap` root records;
   **implemented**; and
4. bounded trapezoid, sink-node, X-node, Y-node, and portal arrays;
   **implemented and live-verified**;
5. trapezoid neighbors, X/Y children, portal pairs, portal trapezoid lists,
   and the source-defined SinkNode single/list pointer properties;
   **implemented and offline-tested; SinkNode helpers are unused by the
   current source snapshot and are not applied to the live field**;
6. reachable `PropsContext` arrays, lists, and `MapProp` pointer fields;
   **implemented and live-verified**; and
7. `MapStaticData.blocking_props` values; **implemented and live-verified**;
8. Python-owned pathing snapshots and paired-portal index resolution;
   **implemented and live-verified**; and
9. the source travel-portal file-hash helper;
   **implemented and live-verified**.

This step remains read-only, bounded, and tied to the selected process.
Pathing snapshot and raw-record caches are keyed by both PID and map ID, so
different clients cannot reuse one another's target addresses. They are
cleared by the source helper or when that process connection closes.
Array readers return every advertised entry or raise when the configured safety
cap is exceeded; they do not silently return partial arrays. The observed
`pmaps_array` has 39 entries, so the former default limit of 32 was raised.

## Remaining pathing work

The external facade methods and source cache gates are implemented. The
remaining difference is that Stealth refreshes explicitly through the selected
client instead of registering the source's per-frame in-process callback.

Every step needs fixed-width layout assertions, offline bounded-read tests, and
a separate live-client observation before it is marked complete. On
2026-09-22, a live read returned 1,270 trapezoids, 1,270 sink nodes, 4,271 X
nodes, 1,980 Y nodes, and 164 portals across all 39 pathing maps. It also read
27 blocking props and the `PropsContext` arrays (16 groups, 23 `PropByType`
records, 1 model, and 516 map props). A bounded linked-record sample read 353
trapezoid neighbors, 830 node children, 112 portal pairs, and 193 portal
trapezoid indices. The raw SinkNode check found all 1,270 field values inside
their owning trapezoid arrays, which conflicts with the source pointer-to-pointer
declaration. The source snapshot leaves `sink_nodes` empty and the searched
source has no active consumer of the helper properties, so this mismatch is
recorded but does not affect the active MapContext read paths. The snapshot pass
materialized 1,270 trapezoids and 164 portals and resolved all 164 portal pair
indices. The source travel-portal helper returned 7 portals.
