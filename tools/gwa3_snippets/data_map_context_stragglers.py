"""``GwAu3_Data_MapContext.au3``'s readers, hand-written into the layer.

Read from ``tools/gwa3_snippets/`` as the **source of record** for the hand-written module
``py4gw/gwa3/data_map_context.py``, which is the role ``data_game_info.py`` plays for ``data_game.py``:
the wording exists in one place and the module is not generated.

**Why this source file is not a generated family.** `tools/generate_gwa3_family.py` builds one module per
source file whose accessor is a ``Switch`` over one record's offsets, and it finds the end of that function
by searching for a line whose ``strip()`` is exactly ``EndFunc``. **Every function in this file ends with
``EndFunc   ;==>Name``**, so that search runs past the function into the rest of the file: with
``Map_GetMapContextInfo`` as a family's function the parser picks up twenty keys from
``Map_GetPathingMapArrayInfo``, ``Map_GetPropInfo``, ``Map_GetPathingMapInfo`` and ``Map_GetTrapezoidInfo``
(``Buffer``, ``Size``, ``Capacity``, ``X``, ``Y``, ``Z``, ``ID``, ``YT`` ...) and resolves them against
`MapContextStruct` -- so ``Map_GetMapContextInfo("Size")`` would answer ``record.start_pos.y`` where GwAu3
answers ``0``. That is a wrong value of the right type, which is what this layer refuses to ship; so the
file is kept by hand like ``data_game.py`` and ``data_effect.py``, and the generator behaviour is a finding
for the parent rather than something this file works around.

**What is here, and what each answer is.**

* ``Map_GetMapContextInfo`` (``GwAu3_Data_MapContext.au3:10-58``) -- one word of the client's map context,
  whose record this project reads as `MapContextStruct`. Three of its keys are **pointer reads and each
  answers the record the word points at**, three answer spawn records where GwAu3 answers a
  ``[buffer, capacity, size]`` header, and two are refused because the only thing behind them is an address
  this project reads nothing through.
* ``Map_GetPathingMapArrayInfo`` (``:79-92``) -- the pathing-map array's header, by GwAu3's key.
* ``Map_GetPropsContext`` (``:139-144``) -- the map-props context, as the record rather than the address.
* ``Map_GetTotalTrapezoidCount`` (``:94-105``) -- the trapezoid count, with an **offset disagreement**
  recorded on the member.

**``Map_GetMapContextPtr`` is carried below; ``Map_GetPathingMapArray`` is still not.**
``Map_GetMapContextPtr`` (``:4-8``) answers a client *address*, and this layer hands out none -- so the
member answers **the record** that address holds, the map context every function in this file reads, which
is the substitution `Game_GetGameContextPtr` (``data_game.py``) and `Item_GetItemPtr` record.
``Map_GetPathingMapArray`` (``:60-77``) answers the *address* of the pathing-map array header **inside**
the static-data record (``$l_p_Sub2 + 0x18``, ``:75``), and this file's `Map_GetPathingMapArrayInfo`
already answers that header by key -- so the spelling is plumbing with no answer of its own to give.
"""

from __future__ import annotations

from typing import Any

from ..client import require_client

__all__ = [
    "Map_GetMapContextPtr",
    "Map_GetMapContextInfo",
    "Map_GetPathingMapArrayInfo",
    "Map_GetPropsContext",
    "Map_GetTotalTrapezoidCount",
]


def Map_GetMapContextPtr() -> Any:
    """The map context record (``GwAu3_Data_MapContext.au3:4-8``).

    GwAu3 resolves ``BasePointer[0][0x18][0x14]`` with its own ``Memory_ReadPtr`` and answers that client
    *address* -- the record every function in this file then reads a word of. This answers **the record**
    the same slot holds, through this project's own member:
    `py4gw.client.ConnectedClient.read_map_context` (``py4gw/client.py:1319``) over `MapContextStruct`
    (`py4gw/context/map_context.py:1844`), and the ``0x14`` is that structure's own offset in the game
    context (`GameContextStruct.map_context`, `py4gw/context/game_context.py:35`, the slot
    ``data_game.py``'s ``MapContext`` key resolves).

    ``0`` when the map context does not resolve, which is GwAu3's own answer at its own guard
    (``:11-15``, where the null pointer answers ``0`` after a logged error) -- and the value
    `Map_GetMapContextInfo` tests before its ``Switch``.

    **The divergence, in one sentence:** GwAu3 hands back a client address and this hands back the record
    that address holds -- the substitution `World_GetWorldContextPtr` (`py4gw/gwa3/data_world.py:429`) and
    `Agent_GetAgentPtr` already record.
    """

    context = require_client().read_map_context()
    return 0 if context is None else context


def Map_GetMapContextInfo(info: str = "") -> Any:
    """One word of the client's map context, by GwAu3's key (``GwAu3_Data_MapContext.au3:10-58``).

    **GwAu3's guard order is kept, and it is the opposite of the generated families' order**: the map
    context is resolved *first* and a context that does not resolve answers ``0`` (``:11-15``, after a
    logged error), then an empty key answers ``0`` (``:17-20``), then the ``Switch`` runs and any
    unrecognised key falls through to the ``Return 0`` at ``:57``. In front of those stands the layer's
    own refusal for the two keys it cannot answer, which is answered before the client is touched -- the
    convention the generated modules state: a caller with no connection must be told the key is unbuilt,
    not that it is unconnected. (A client that is not connected at all raises through this layer's own
    `require_client`, ``py4gw/client.py:1937``, where GwAu3 answers ``0`` -- the divergence
    `Game_GetGameInfo` records on its first guard.)

    Key by key:

    * ``MapBoundaries`` (``:24-25``, ``float[5]`` at ``+0x0``) -- the five floats, through the port's own
      read of them (`MapContextStruct.map_boundaries`, ``py4gw/context/map_context.py:1720``), as a list.
    * ``Sub1`` (``:26-27``, the ``ptr`` at ``+0x74``) -- GwAu3 answers the address; this answers **the
      record** the word points at (`MapContextStruct.path_context`, ``py4gw/context/map_context.py:1670``;
      the word itself is ``path_ptr``, ``:1556``, asserted at ``:1814``), and ``0`` where it does not
      resolve, which is GwAu3's own answer for a null pointer.
    * ``PropsContext`` (``:28-29``, the ``ptr`` at ``+0x7C``) -- the same treatment, through
      `MapContextStruct.props` (``:1619``); it is the identical answer `Map_GetPropsContext` gives for that
      word under its own name (``GwAu3_Data_MapContext.au3:139-144``).
    * ``Terrain`` (``:30-31``) and ``Zones`` (``:32-33``) -- **refused**: each case answers a client
      address, this project names both words (`MapContextStruct.terrain`, ``:1560``, and ``.zones``,
      ``:1564``) and reads **no record through them**, so there is nothing to answer in the address's
      place.
    * ``Spawns1``/``Spawns2``/``Spawns3`` (``:34-54``) -- GwAu3 fills a three-element array of
      ``[buffer, capacity, size]`` from the ``GWArray`` at ``+0x2C``/``+0x3C``/``+0x4C``. The first element
      is a client address, which this layer never hands out, so each key answers **the spawn records the
      array holds** (`MapContextStruct.spawns1`/``spawns2``/``spawns3``,
      ``py4gw/context/map_context.py:1761-1777``) -- what a caller would walk the buffer for. The two
      numbers GwAu3 also answers are the port's own ``m_capacity``/``m_size`` at ``+0x30``/``+0x34`` of the
      same record (``:1552-1554``), which is where GwAu3 reads them.
    """

    if info == "Terrain":
        raise NotImplementedError(
            "GwAu3_Data_MapContext.au3:30-31 answers the client *address* held at ``+0x84`` of the map "
            "context. This project names that word (`MapContextStruct.terrain`, "
            "py4gw/context/map_context.py:1560) and reads no record through it, so there is no reading to "
            "route to -- and this layer hands out no client address, so the key is refused rather than "
            "answered with a number a caller cannot tell from data."
        )

    if info == "Zones":
        raise NotImplementedError(
            "GwAu3_Data_MapContext.au3:32-33 answers the client *address* held at ``+0x130`` of the map "
            "context. This project names that word (`MapContextStruct.zones`, "
            "py4gw/context/map_context.py:1564) and reads no record through it, so there is no reading to "
            "route to -- and this layer hands out no client address, so the key is refused rather than "
            "answered with a number a caller cannot tell from data."
        )

    context = require_client().read_map_context()
    if context is None:
        return 0

    if info == "":
        return 0

    if info == "MapBoundaries":
        return [float(value) for value in context.map_boundaries]
    if info == "Sub1":
        path = context.path_context
        return 0 if path is None else path
    if info == "PropsContext":
        props = context.props
        return 0 if props is None else props
    if info == "Spawns1":
        return context.spawns1
    if info == "Spawns2":
        return context.spawns2
    if info == "Spawns3":
        return context.spawns3
    return 0


def Map_GetPathingMapArrayInfo(info: str = "") -> Any:
    """One word of the pathing-map array's header, by GwAu3's key (``GwAu3_Data_MapContext.au3:79-92``).

    GwAu3's guard order is kept: `Map_GetPathingMapArray` (``:60-77``) answers ``0`` when the map
    context's ``Sub1`` is null (``:62-65``) or when the pointer at ``Sub1[0]`` -- its ``Sub2`` -- is null
    (``:69-72``), and this answers ``0`` at each of those two points; then ``Buffer`` reads the ``ptr`` at
    the header ``Sub2 + 0x18`` (``:84-85``), ``Size`` the ``dword`` at ``+0x8`` (``:86-87``) and
    ``Capacity`` the ``dword`` at ``+0x4`` (``:88-89``), and any other key falls through to its own
    ``Return 0`` (``:91``) -- including the empty key, which it does not test before those reads.

    This project reads the same records: the map context's ``path_ptr`` is ``Sub1``
    (``py4gw/context/map_context.py:1556``, asserted at ``:1814``), the path context's ``static_data_ptr``
    is ``Sub2`` (``:1471``, asserted at ``:1812``) and ``MapStaticDataStruct.pmaps_array`` is that array
    header at exactly ``+0x18`` (``:1338``, asserted at ``:1811``).

    **One shape difference, stated on the member: ``Buffer`` answers the records, not the address.** GwAu3
    hands back the client pointer the header holds; this layer hands out no address, so the key answers the
    pathing-map records the array holds (`MapStaticDataStruct.pathing_maps`,
    ``py4gw/context/map_context.py:1385``) -- what a caller would stride through the buffer for, and what
    this same file's ``Map_GetPathingMap`` (``:545-562``) does with a ``0x54`` stride. ``Size`` and
    ``Capacity`` are the header's own ``m_size``/``m_capacity`` words, which is what GwAu3 reads.
    """

    context = require_client().read_map_context()
    if context is None:
        return 0

    path = context.path_context
    if path is None:
        return 0

    static_data = path.static_data
    if static_data is None:
        return 0

    if info == "Buffer":
        return static_data.pathing_maps
    if info == "Size":
        return int(static_data.pmaps_array.m_size)
    if info == "Capacity":
        return int(static_data.pmaps_array.m_capacity)
    return 0


def Map_GetPropsContext() -> Any:
    """The map-props context record (``GwAu3_Data_MapContext.au3:139-144``).

    GwAu3's body is two steps: resolve the map context, answer ``0`` when it is null (``:140-141``), and
    otherwise read the ``ptr`` at ``+0x7C`` (``:143``). **That word is the props context, and this answers
    the record it addresses** -- read through this project's own members: `MapContextStruct.props_ptr` is
    the word (``py4gw/context/map_context.py:1558``, asserted at ``:1815``) and `MapContextStruct.props`
    (``:1619``) reads the ``PropsContextStruct`` it points at. This layer hands out no client address under
    any name, so the address is not the answer; GwAu3's ``0`` for a null pointer is kept as the ``0`` this
    answers when the record does not resolve.
    """

    context = require_client().read_map_context()
    if context is None:
        return 0

    props = context.props
    return 0 if props is None else props


def Map_GetTotalTrapezoidCount() -> int:
    """The map's total trapezoid count (``GwAu3_Data_MapContext.au3:94-105``).

    GwAu3 resolves ``Sub1`` -- the word at ``+0x74`` of the map context (``:95``) -- answers ``0`` when it
    is null (``:96-99``) and otherwise reads the ``dword`` at ``Sub1 + 0x18`` (``:102``).

    **The two projects disagree about that word, and this answers this project's own name for the fact.**
    Recorded rather than papered over:

    * GwAu3 reads ``Sub1 + 0x18``.
    * This project declares ``total_trapezoid_count`` on the native view of the same record at ``+0x14``
      (`NativeMapContextSub1Struct`, ``py4gw/context/map_context.py:1049``, pinned by
      ``tests/test_map_context_offline.py:132``) -- one word earlier. That layout is corroborated by
      GwAu3's own ``Map_GetPathingMapBlockArray`` (``:107-134``), which reads that array's pointer at
      ``+0x04`` and its size at ``+0x0C``, exactly the ``GWArray`` the port declares there. The record read
      live is Reforged's `PathContextStruct` (``py4gw/context/map_context.py:1670``), which names no
      trapezoid count at all: its word at ``+0x18`` is ``path_nodes.m_size`` (``:1473``), a node count
      under a different name.
    * The trapezoid count this project *does* read live is `MapStaticDataStruct.trapezoid_count`
      (``py4gw/context/map_context.py:1342``), on the record ``Sub1[0]`` points at -- the record GwAu3's
      own ``Map_GetPathingMapArray`` follows to reach the pathing maps (``:60-77``).

    So this answers that count, from the same chain: ``0`` where ``Sub1`` does not resolve, which is
    GwAu3's own guard, and ``0`` where the record ``Sub1[0]`` points at does not resolve -- a pointer this
    answer has to follow and GwAu3's does not. A live read of both words is what would settle which one the
    client keeps.
    """

    context = require_client().read_map_context()
    if context is None:
        return 0

    path = context.path_context
    if path is None:
        return 0

    static_data = path.static_data
    if static_data is None:
        return 0

    return int(static_data.trapezoid_count)
