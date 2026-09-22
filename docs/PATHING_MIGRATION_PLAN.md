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

Stealth currently reads the fixed `MapContext` root and its three bounded spawn
arrays. It now also reads the current `PathContext`, `MapStaticData`, and a
bounded list of `PathingMap` root records. It exposes the raw child-buffer
addresses and counts, but it does not yet read trapezoids, nodes, portals,
`PropsContext`, or map props.

This is an incomplete migration, not a completed pathing implementation.

## Immediate migration boundary

The first pathing step will read the current target context structures only:

1. `PathContext` root; **implemented**;
2. `MapStaticData` root; **implemented**;
3. bounded `pmaps_array` headers and `PathingMap` root records;
   **implemented**; and
4. direct pointer/count fields needed for later child reads; **implemented**.

This step must remain read-only, bounded, and tied to the selected process.
It must not create Python-owned pathing snapshots, build a map-ID cache, or
materialize the full trapezoid/node/portal graph.

## Deferred pathing work

The next focused step can add bounded reads for trapezoids, portals, and nodes,
followed by map props and travel portals. Reforged's raw and materialized
pathing-map caches are source behavior to study later; they are not part of
the current external context read.

Every step needs fixed-width layout assertions, offline bounded-read tests, and
a separate live-client observation before it is marked complete.
