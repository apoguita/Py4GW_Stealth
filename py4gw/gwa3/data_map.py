"""GwAu3's `Map_GetAreaInfo`, over the record this project already reads.
**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_family.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

GwAu3's map-area reader. GwAu3 indexes the client's own area-info table -- its ``Map_GetAreaPtr`` is ``$g_p_AreaInfo + (0x7C * $aMapID)`` -- and this project reads the same table with the same stride: `MapMethods.GetMapInfo(map_id)` walks the catalog's area-info address and materializes `AreaInfoStruct`, whose size is asserted at ``0x7C`` (`py4gw/context/instance_info_context.py:239`).

Every field offset lines up: ``campaign`` at ``+0x0``, ``type`` at ``+0xC``, ``flags`` at ``+0x10``, ``min_party_size`` at ``+0x18``, ``file_id`` at ``+0x68``, ``description_id`` at ``+0x78``.

The file's **instance** reader is carried as a snippet (`tools/gwa3_snippets/data_map_instance_info.py`): `Map_GetInstanceInfo` answers what kind of place the client is in -- outpost, explorable or loading -- from `Map.GetInstanceType`, compared with the source's own three literals. `py4gw/gwa3/uai_cache.py` and `UAI_Fight` both gate on it.

`Map_GetAreaInfo` is one ``Switch`` over 40 keys in GwAu3
(``GwAu3_Data_Map.au3``). 38 of the 40 field keys resolve to a **named
attribute** of the structure this project reads, chosen by offset against ctypes' own view of the
record. The reader for each key names its attribute literally, so nothing here reaches a field through
a dynamic name.

**The return shapes are GwAu3's.** An unknown field name answers ``0`` and a record that cannot be
resolved answers ``0`` -- AutoIt has no exceptions in this role and a script branches on the return.
A key this layer cannot answer **raises**, naming what it needs, rather than answering a wrong value
of the right type, which a caller could not detect.
"""

from __future__ import annotations

import struct

from typing import Any

from ..client import require_client
from ..context import AreaInfoStruct
from ..native_src.methods.map_methods import MapMethods
_UNIMPLEMENTED: dict[str, str] = {}

_COMPUTED: frozenset[str] = frozenset(['FileID1', 'FileID2'])

# A text key takes the id as well as the record, because its handshake is keyed by the id.

# Keys that answer `False` rather than `0` when no record matches, because GwAu3's own guard does.
_FALSE_ON_MISSING: frozenset[str] = frozenset([])


def _read_text(request: Any, ready: Any, get: Any, record_id: Any) -> str:
    """Run this project's name-decode handshake and answer the text it produces.

    **A decode is not a read, and this is the whole of that difference.** The port's name getters
    answer `""` until a request has been made *and* the client's decoder has answered
    (`py4gw/item.py:394`, `:449`), so the three steps are run in order:

    1. **request** -- asks the client's own decoder for this id, through the game thread;
    2. **ready** -- advances the port's polling and says whether an answer has arrived;
    3. **get** -- takes the text, which carries the source's own `"Timeout"` literal if the client
       never answered within the bound the port uses.

    A caller cannot tell an unanswered decode from a nameless record, which is exactly why this layer
    refused these keys until the handshake was wired: answering `""` early is a wrong value of the
    right type. `ready` is polled once here rather than looped, because the port's own request already
    waits its bound -- looping would only make a stalled game thread block the bridge.
    """

    request(record_id)
    ready(record_id)
    return str(get(record_id))


def _read_raw(record: Any, offset: int, fmt: str) -> Any:
    """Read a field GwAu3 reads and this project's structure does not name.

    The record is a ``ctypes.Structure`` whose bytes are the client's own, so a field with no
    attribute name is read from those bytes at GwAu3's own offset and width. That covers the ``hXXXX``
    fields, whose names in the port are placeholders because the layout is not understood there.
    """

    values = struct.unpack_from(fmt, record, offset)
    return values[0] if len(values) == 1 else values


def _read_hasenterbutton(record: Any) -> bool:
    """``GwAu3_Data_Map.au3`` -- the ``HasEnterButton`` case."""

    return bool((record.flags & 0x100) != 0 or (record.flags & 0x40000) != 0)


def _read_hasmissionmapsto(record: Any) -> bool:
    """``GwAu3_Data_Map.au3`` -- the ``HasMissionMapsTo`` case."""

    return bool((record.flags & 0x8000000) != 0)


def _read_isguildhall(record: Any) -> bool:
    """``GwAu3_Data_Map.au3`` -- the ``IsGuildHall`` case."""

    return bool((record.flags & 0x800000) != 0)


def _read_isonworldmap(record: Any) -> bool:
    """``GwAu3_Data_Map.au3`` -- the ``IsOnWorldMap`` case."""

    return bool((record.flags & 0x20) == 0)


def _read_ispvp(record: Any) -> bool:
    """``GwAu3_Data_Map.au3`` -- the ``IsPvP`` case."""

    return bool((record.flags & 0x40001) != 0)


def _read_isunlockable(record: Any) -> bool:
    """``GwAu3_Data_Map.au3`` -- the ``IsUnlockable`` case."""

    return bool((record.flags & 0x10000) != 0)


def _read_isvanquishablearea(record: Any) -> bool:
    """``GwAu3_Data_Map.au3`` -- the ``IsVanquishableArea`` case."""

    return bool((record.flags & 0x10000000) != 0)



_READERS: dict[str, Any] = {}
_READERS.update(
    {
        "Campaign": lambda record: record.campaign,
        "Continent": lambda record: record.continent,
        "ControlledOutpostID": lambda record: record.controlled_outpost_id,
        "DescriptionID": lambda record: record.description_id,
        "FileID": lambda record: record.file_id,
        "FileID1": lambda record, record_id: ((record.file_id - 1) % 0xFF00) + 0x100,
        "FileID2": lambda record, record_id: int((record.file_id - 1) / 0xFF00) + 0x100,
        "Flags": lambda record: record.flags,
        "FractionMission": lambda record: record.fraction_mission,
        "HAMapChronology": lambda record: record.ha_map_chronology,
        "HasEnterButton": _read_hasenterbutton,
        "HasMissionMapsTo": _read_hasmissionmapsto,
        "IconEndX": lambda record: record.icon_end_x,
        "IconEndXDupe": lambda record: record.icon_end_x_dupe,
        "IconEndY": lambda record: record.icon_end_y,
        "IconEndYDupe": lambda record: record.icon_end_y_dupe,
        "IconStartX": lambda record: record.icon_start_x,
        "IconStartXDupe": lambda record: record.icon_start_x_dupe,
        "IconStartY": lambda record: record.icon_start_y,
        "IconStartYDupe": lambda record: record.icon_start_y_dupe,
        "IsGuildHall": _read_isguildhall,
        "IsOnWorldMap": _read_isonworldmap,
        "IsPvP": _read_ispvp,
        "IsUnlockable": _read_isunlockable,
        "IsVanquishableArea": _read_isvanquishablearea,
        "MaxLevel": lambda record: record.max_level,
        "MaxPartySize": lambda record: record.max_party_size,
        "MaxPlayerSize": lambda record: record.max_player_size,
        "MinLevel": lambda record: record.min_level,
        "MinPartySize": lambda record: record.min_party_size,
        "MinPlayerSize": lambda record: record.min_player_size,
        "MissionChronology": lambda record: record.mission_chronology,
        "MissionMapsTo": lambda record: record.mission_maps_to,
        "NameID": lambda record: record.name_id,
        "NeededPQ": lambda record: record.needed_pq,
        "Region": lambda record: record.region,
        "RegionType": lambda record: record.type,
        "ThumbnailID": lambda record: record.thumbnail_id,
        "X": lambda record: record.x,
        "Y": lambda record: record.y,
    }
)


def Map_GetAreaInfo(record_id: Any, info: str = "") -> Any:
    """One field of the record, by GwAu3's field name (``GwAu3_Data_Map.au3``).

    GwAu3's guard order is kept: an empty field name answers ``0`` before anything is read, and a
    record the client does not hold answers ``0`` rather than raising. An unrecognised field name
    answers ``0`` -- GwAu3's own ``Case Else``.

    **The key is resolved before the record is.** A key this layer refuses raises without touching the
    client, which is the whole point of refusing: a caller with no connection must still be told that
    the key is unbuilt, not that it is unconnected. The first version resolved the record first, so
    asking for a refused key without a client reported a connection error instead of the gap.
    """

    if info == "":
        return 0

    # A refused key is answered before the record is resolved, deliberately: the refusal is a fact
    # about this layer, not about the client, so a caller with no connection must still be told the
    # key is unbuilt rather than told it is unconnected. The first version resolved the record first
    # and reported a connection error for a refusal that never needed one.
    if info in _UNIMPLEMENTED:
        raise NotImplementedError(_UNIMPLEMENTED[info])

    reader = _READERS.get(info)
    if reader is None:
        return 0

    record = _record(record_id)
    if record is None:
        # GwAu3's own no-match guard answers `False` for these keys and `0` for the rest
        # (``GwAu3_Data_Quest.au3:16-21``).
        if info in _FALSE_ON_MISSING:
            return False
        return 0

    # A computed or text key re-enters this accessor, so it is handed the caller's id too. A family
    # with no id parameter -- World_GetWorldInfo -- has none of those keys, so the branch is written
    # against whatever its own first parameter is.
    if info in _COMPUTED:
        return reader(record, record_id)
    return reader(record)


def _record(record_id: Any) -> Any:
    """The record GwAu3 resolves before its ``Switch``.

    ``MapMethods.GetMapInfo(int(record_id))`` -- this project's own read, which is the same
    client record GwAu3 addresses by base plus stride.
    """

    client = require_client()
    return MapMethods.GetMapInfo(int(record_id))

"""``GwAu3_Data_Map.au3``'s **instance** reader, hand-written into the generated module.

Read from ``tools/gwa3_snippets/`` at generation time, the same mechanism `data_party`'s member
accessors use: ``data_map.py`` is rewritten whole on every run.

**What it is.** ``Map_GetInstanceInfo`` (`GwAu3_Data_Map.au3:32-49`) answers *what kind of place the
client is in* -- outpost, explorable, or still loading. It reads one dword: GwAu3 follows its own
``$g_p_InstanceInfo`` pointer (one of the globals it fills by signature scan) to ``+0x4`` and compares it
with three literals. This project reads the same fact through its own member: `Map.GetInstanceType`
(`py4gw/map.py:107`), which is the port's read of the client's instance record
(`py4gw/context/instance_info_context.py`), so the comparison here is the source's own arithmetic over
the same word.

**Why it was needed now.** `py4gw/gwa3/uai_cache.py`'s ``Cache_SkillBar`` opens with
``Map_GetInstanceInfo("IsExplorable")`` (`UtilityAI_Cache.au3:6`), and ``UAI_Fight`` itself gates on
``Map_GetInstanceInfo("Type")`` -- so the engine could not be written without it.
"""


def Map_GetInstanceInfo(info: str = "") -> Any:
    """One field of the client's instance record, by GwAu3's field name
    (``GwAu3_Data_Map.au3:32-49``).

    GwAu3's guard order is kept: an empty key answers ``0`` before anything is read, and an unrecognised
    key answers ``0`` -- its ``Switch`` has no ``Case Else`` and falls through to the same ``Return 0``.

    The three flags are **comparisons of the one word the source compares**, not the port's own
    predicates: ``IsExplorable`` is ``type == 1``, ``IsLoading`` is ``type == 2`` and ``IsOutpost`` is
    ``type == 0``, which is exactly what ``:41-45`` does. A caller that wants the port's richer answer
    wants `Map.IsExplorable`/`Map.IsOutpost` (`py4gw/map.py:126-137`).
    """

    if info == "":
        return 0

    from ..map import Map

    instance_type = int(Map.GetInstanceType())

    if info == "Type":
        return instance_type
    if info == "IsExplorable":
        return instance_type == 1
    if info == "IsLoading":
        return instance_type == 2
    if info == "IsOutpost":
        return instance_type == 0

    return 0


def Map_GetMapID() -> int:
    """The map the client is in (``GwAu3_Data_Map.au3:234-236``).

    GwAu3's own body is one line -- ``Return Map_GetCharacterInfo("MapID")`` -- and this is now that
    line: `Map_GetCharacterInfo` landed with the character-info block reader
    (`tools/gwa3_snippets/data_map_character_info.py`), so the port calls it exactly as the source does
    rather than reaching the same fact through `Map.GetMapID`.

    The value is the client's own current map, which is what the two callers need: ``UAI_Fight`` gates
    on it (``UtilityAI_Core.au3:17,67``), where a map change is one of the five ways its loop ends.
    """

    return int(Map_GetCharacterInfo("MapID"))
"""``GwAu3_Data_Map.au3``'s **character-info** reader, hand-written into the generated module.

Read from ``tools/gwa3_snippets/`` at generation time, the same mechanism `data_map`'s instance reader
uses: ``data_map.py`` is rewritten whole on every run.

**What it is.** ``Map_GetCharacterInfo`` (``GwAu3_Data_Map.au3:5-39``) answers one field of the
character context -- the record the client holds while a character is in the world. GwAu3 reaches it
through its own ``Map_GetCharacterContextPtr`` (a pointer it resolves from ``$g_p_CharacterContext``) and
reads fixed offsets. This project reads the **same record** as `CharContextStruct`
(``py4gw/context/char_context.py:245``) through `py4gw.client.RemoteClient.read_char_context`
(``py4gw/client.py:1745``), which is the port's own on-demand read -- nothing here is cached and nothing
is refreshed by a loop.

**The field names line up, and that is why this is parity rather than a re-invention.** GwAu3's
``+0x64`` four-word UUID is the port's ``player_uuid_ptr``; ``+0x74`` ``wchar[20]`` is
``player_name_enc`` (``c_uint16 * 0x14``, the same twenty wide characters); ``+0x190`` is
``world_flags``; ``+0x194`` ``token1``; ``+0x198`` ``map_id``; ``+0x19C`` ``is_explorable``; ``+0x1B8``
``token2``; ``+0x2A8``/``+0x2AC`` are the port's ``player_flags``/``player_number`` pair.

**One finding is recorded rather than smoothed over: the four middle keys are read four bytes earlier by
GwAu3 than this port names them.** GwAu3 reads ``DistrictNumber`` at ``+0x228``, ``Language`` at
``+0x22C``, ``ObserveMapID`` at ``+0x230`` and ``CurrentMapID`` at ``+0x234``; the port's names for those
four sit at ``+0x22C``, ``+0x230``, ``+0x234`` and ``+0x238`` -- one word later -- and GwAu3's own inline
comments on those very lines record *earlier* offsets again (``; 0x220``, ``; 0x224``, ``; 0x228``,
``; 0x22C``), so its offsets have moved at least twice. This member answers the port's names, because a
name is the fact and an offset is where the fact was when the source was written; the disagreement is
written down here and on the member, and a live read is what would settle it.
"""

#: ``{GwAu3 key: reader}`` for the keys that are a single word of the character context. Written as
#: readers rather than as field names, because this project reaches no field through a dynamic name.
_SCALAR_KEYS: dict[str, Any] = {
    "WorldFlags": lambda context: int(context.world_flags),
    "Token1": lambda context: int(context.token1),
    "MapID": lambda context: int(context.map_id),
    "IsExplorable": lambda context: int(context.is_explorable),
    "Token2": lambda context: int(context.token2),
    "DistrictNumber": lambda context: int(context.district_number),
    "Language": lambda context: int(context.language),
    "ObserveMapID": lambda context: int(context.observe_map_id),
    "CurrentMapID": lambda context: int(context.current_map_id),
    "ObserveMapType": lambda context: int(context.observe_map_type),
    "CurrentMapType": lambda context: int(context.current_map_type),
    "PlayerFlags": lambda context: int(context.player_flags),
    "PlayerNumber": lambda context: int(context.player_number),
}


def Map_GetCharacterInfo(info: str = "") -> Any:
    """One field of the character context, by GwAu3's field name (``GwAu3_Data_Map.au3:5-39``).

    GwAu3's guard order is kept: an empty key answers ``0`` before anything is read, an unrecognised key
    answers ``0`` (its ``Switch`` has no ``Case Else``), and a context that cannot be read answers ``0``
    -- which is what its own ``If $l_p_Ptr = 0 ... Then Return 0`` does.

    Three keys are answered the Pythonic way rather than by their offset, and each says what it is:

    * ``PlayerUUID`` -- GwAu3 builds a four-element array of longs at ``+0x64``; this answers the port's
      own four-word ``player_uuid_ptr`` field, the same four words in the same order.
    * ``PlayerName`` -- GwAu3 reads twenty wide characters at ``+0x74`` and hands back the raw buffer;
      this answers the **decoded name** through `Player.GetName` (`py4gw/player.py:491`), which is the
      port's read of that same field and the form a caller can use.
    * ``Region`` -- GwAu3 reads a client global (``$g_p_Region``) rather than the context; this answers
      `Map.GetRegion` (`py4gw/map.py:289`), the port's read of the same fact. GwAu3's key is one number,
      and the port's member answers a pair, so its first element is the number.
    * ``DistrictNumber`` -- the one key whose offsets **disagree**: GwAu3 reads ``+0x228`` and the port
      names ``district_number`` at ``+0x22C`` (with GwAu3's own inline comment on that line recording
      ``; 0x220``, an offset it has since moved from). Rather than pick a word for an offset, this
      answers `Map.GetDistrict` (`py4gw/map.py:309`) -- the port's own read of the fact the key names.

    ``ObserverMatch`` answers ``0`` and names its work: GwAu3 hands back the *pointer* to the observer
    match record, and this layer hands out no address. The pairing is the one the ``Match_*`` family now
    provides -- `Match_GetObserverMatchInfo(match_number, info)` reads the records this key's slot points
    at, by index (`py4gw/gwa3/data_match.py`) -- so the key still answers ``0`` here rather than an
    address dressed up as a record.
    """

    if info == "":
        return 0

    if info == "Region":
        from ..map import Map

        return int(Map.GetRegion()[0])

    if info == "DistrictNumber":
        from ..map import Map

        return int(Map.GetDistrict())

    if info == "PlayerName":
        from ..player import Player

        return str(Player.GetName())

    context = require_client().read_char_context()
    if context is None:
        return 0

    if info == "PlayerUUID":
        return [int(word) for word in context.player_uuid_ptr]

    reader = _SCALAR_KEYS.get(info)
    if reader is not None:
        return reader(context)

    # `ObserverMatch` and anything unrecognised: GwAu3's own `Return 0`.
    return 0
"""``GwAu3_Data_Map.au3``'s **current-area and instance** readers, hand-written into the generated module.

Read from ``tools/gwa3_snippets/`` at generation time: ``data_map.py`` is rewritten whole on every run.

**What is here, and what each one is.**

* ``Map_GetCurrentAreaInfo`` (`GwAu3_Data_Map.au3:51-121`) answers one field of the area record the client
  is **in**. GwAu3 follows its own ``$g_p_InstanceInfo`` to ``+0x8`` and reads a ``0x7C`` record; that
  record is the same structure the area table holds -- which is why the key list is the table reader's
  own (``Campaign`` at ``+0x0``, ``Continent`` at ``+0x4``, ``Region`` at ``+0x8``, ``RegionType`` at
  ``+0xC``, ``ThumbnailID`` at ``+0x14``, the party and player size bounds, the icon rectangle, ``FileID``
  at ``+0x68``, ``NameID`` at ``+0x74``, ``DescriptionID`` at ``+0x78``). This project reads the same
  record for the map the client is in, through its own current-map read, so the member **delegates to
  `Map_GetAreaInfo`** with the current map id rather than keeping a second key table that could drift from
  the first. Its guard is GwAu3's: an empty key answers ``0`` before anything is read.
* ``Map_GetRegion`` (`:15-17`) reads one client global (``$g_p_Region``). This answers `Map.GetRegion`,
  the port's read of the same fact; GwAu3's answer is one number and the port's member answers a pair, so
  its first element is the number.
* ``Map_GetInstanceUpTime`` (`:4-8`) reads the instance timer out of the client's own context. This
  answers `Map.GetInstanceUptime` (`py4gw/map.py:281`), the port's read of the same clock.
* ``Map_GetCurrentRegionType`` (`:123-...`) maps the region-type **number** to one of GwAu3's own twenty
  names. This answers the port's own name for the same number (`Map.GetRegionType`,
  ``py4gw/map.py:298``) -- a documented divergence of spelling only, recorded on the member rather than
  transcribed as a second twenty-case table that could drift from the port's.
"""


def Map_GetCurrentAreaInfo(info: str = "") -> Any:
    """One field of the area the client is in, by GwAu3's field name
    (``GwAu3_Data_Map.au3:51-121``).

    GwAu3's guard is kept: an empty key answers ``0`` before anything is read, and an unrecognised key
    answers ``0`` -- its ``Switch`` has no ``Case Else`` and falls through to the same ``Return 0``. The
    key table is `Map_GetAreaInfo`'s, which is the same ``0x7C`` record, so the numbers come from one
    mapping rather than two.
    """

    if info == "":
        return 0

    return Map_GetAreaInfo(Map_GetMapID(), info)


def Map_GetRegion() -> int:
    """The client's region number (``GwAu3_Data_Map.au3:15-17``).

    GwAu3's whole body is one read of ``$g_p_Region``. This answers the same number from the port's own
    read of it (`Map.GetRegion`, ``py4gw/map.py:289``), whose pair carries the number first.
    """

    from ..map import Map

    return int(Map.GetRegion()[0])


def Map_GetInstanceUpTime() -> int:
    """How long the client has been in this instance (``GwAu3_Data_Map.au3:4-8``).

    GwAu3 walks ``BasePointer[0][0x18][0x8][0x1AC]`` for the timer; this answers the port's own read of
    the same clock (`Map.GetInstanceUptime`, ``py4gw/map.py:281``).
    """

    from ..map import Map

    return int(Map.GetInstanceUptime())


def Map_GetCurrentRegionType() -> str:
    """The current region type's **name** (``GwAu3_Data_Map.au3:123-...``).

    GwAu3 maps the region-type number to one of its own twenty literals (``"Explorable"``,
    ``"Mission Outpost"``, ``"Dungeon"`` ...). This answers the port's own name for the same number
    (`Map.GetRegionType`, ``py4gw/map.py:298``), which is the same fact spelled by this library. That is
    the divergence, and it is deliberate: a second twenty-case table here would be a second surface to
    keep in step with the port's.
    """

    from ..map import Map

    return str(Map.GetRegionType()[1])
"""``GwAu3_Data_Map.au3``'s **stragglers**: the click coordinates, the move coordinates and the map-unlock test.

Read from ``tools/gwa3_snippets/`` at generation time, the same mechanism `data_map_character_info.py`
and `data_map_current_area.py` use: ``data_map.py`` is rewritten whole on every run.

**What is here, and where each answer comes from.**

* ``Map_GetLastMoveCoords`` (``GwAu3_Data_Map.au3:19-22``) answers two **controller-side globals**,
  ``$g_f_LastMoveX``/``$g_f_LastMoveY``. They are not client memory and there is nothing in the client
  to read for them: GwAu3 declares them ``Global $g_f_LastMoveX = 0`` / ``= 0``
  (``GwAu3_Const_Core.au3:135-136``), resets them at ``GwAu3_Core.au3:704-705``, and its own move
  function stores the point it decided on there (``GwAu3_Cmd_Map.au3:11-12``). So this layer
  **transcribes the state**, the way ``py4gw/gwa3/uai_const.py`` transcribes the UtilityAI plugin's own
  mutable globals -- and this layer's own ``Map_Move`` (``py4gw/gwa3/cmd_map.py:55``) is the function
  that stores them here too, with GwAu3's two assignments at ``GwAu3_Cmd_Map.au3:11-12`` as its model.
  **Without that writer the member below is a constant ``[0.0, 0.0]``**, which is why the two lines are
  part of this port rather than an optional extra.
* ``Map_GetClickCoords`` (``:24-29``) reads two client floats that GwAu3 resolves by its own signature
  scan (``$g_f_ClickCoordsX``/``$g_f_ClickCoordsY``, wired at ``GwAu3_Core.au3:293-294``). This project
  has no resolver for that pattern; it reads the same fact from the client's own record instead, and
  says so on the member.
* ``Map_IsMapUnlocked`` (``:386-406``) is parity: GwAu3's hand-written walk of the world context's
  unlock bitfield against this project's member of the same name, ``Map.IsMapUnlocked``.

``Map_GetCurrentRegionType`` is **not** here: it was already ported
(`tools/gwa3_snippets/data_map_current_area.py:68`, exported by the ``data_map`` family), and this file
does not restate it.
"""

#: ``GwAu3_Const_Core.au3:135-136`` -- GwAu3's own last-move coordinates, transcribed as module state.
#:
#: These are **controller-side**, not client memory: GwAu3's own move function writes the point it
#: decided on into them (``GwAu3_Cmd_Map.au3:11-12``, *after* the randomisation its own ``Map_Move``
#: applies), its cleanup returns them to ``0`` (``GwAu3_Core.au3:704-705``), and the file declared here
#: starts them at ``0``. The names keep GwAu3's spelling with the leading ``$`` dropped, which is the
#: convention ``py4gw/gwa3/constants.py`` already uses for its names.
#:
#: **The writer is part of this port**: ``Map_Move`` (``py4gw/gwa3/cmd_map.py:55``) stores the two
#: coordinates it passed to ``Player.Move`` here, with GwAu3's own two assignments as the model
#: (``GwAu3_Cmd_Map.au3:11-12``). ``Map_MoveLayer`` writes neither, in either project. If those two
#: assignments are not in ``Map_Move``, the reader below answers a constant ``[0.0, 0.0]`` -- a wrong
#: value of the right type, which is why they are not optional.
#:
#: **They live with their reader rather than in a module of their own.** ``py4gw/gwa3/uai_const.py`` is
#: the precedent for transcribing a ``Global`` -- the generated ``constants.py`` reads ``Global Const``
#: and ``Global Enum`` only, deliberately, because a ``Global`` is state -- but that module exists
#: because many ported plugin modules read and write the same settings. Here one member reads this pair
#: (`Map_GetLastMoveCoords`) and one function writes it (`Map_Move`), and the file that *declares* them
#: (``GwAu3_Const_Core.au3``) declares exactly two more globals of this group --
#: ``$g_f_ClickCoordsX``/``$g_f_ClickCoordsY`` (``:137-138``) -- which are client addresses GwAu3
#: resolves by its own scan and this layer answers from the client's own record, so there is no second
#: reader a ``GwAu3_Const_Core.au3`` module would be shared with.
g_f_LastMoveX: float = 0.0
g_f_LastMoveY: float = 0.0


def Map_GetLastMoveCoords() -> list[float]:
    """The coordinates of the last move this layer sent (``GwAu3_Data_Map.au3:19-22``).

    GwAu3's whole body is the two-element array it builds from its own globals
    (``$g_f_LastMoveX``/``$g_f_LastMoveY``, ``GwAu3_Const_Core.au3:135-136``), and this answers the same
    two numbers from the transcription above -- the values `Map_Move` stored, which is where GwAu3
    stores them (``GwAu3_Cmd_Map.au3:11-12``). The array shape is GwAu3's: two floats, x first.

    **One thing a caller has to know.** These are *this layer's* record of *its own* moves, so the pair
    is ``[0.0, 0.0]`` until a move has been made through it, exactly as GwAu3's start at ``0``
    (``GwAu3_Const_Core.au3:135-136``) and return to ``0`` on cleanup (``GwAu3_Core.au3:704-705``).
    The one writer in either project is the move function of that name -- `Map_Move`, storing the two
    coordinates it handed to the client (`GwAu3_Cmd_Map.au3:11-12`; ``py4gw/gwa3/cmd_map.py:55`` is this
    layer's copy of it, and those two assignments are part of its port). `Map_MoveLayer` writes neither,
    in either project.
    """

    return [float(g_f_LastMoveX), float(g_f_LastMoveY)]


def Map_GetClickCoords() -> list[float]:
    """The client's last click coordinates (``GwAu3_Data_Map.au3:24-29``).

    GwAu3 reads two floats at client globals it resolved by its own scan pattern
    (``$g_f_ClickCoordsX``/``$g_f_ClickCoordsY``, wired at ``GwAu3_Core.au3:293-294``). **This project
    has no reader for those two addresses** -- ``offsets/`` carries no entry for that scan and this
    layer reads no address it did not resolve -- but it reads the same fact from the client's own
    record: the mission-map context's ``last_mouse_location``, through `Map.MissionMap.GetLastClickCoords`
    (``py4gw/map.py:1052``). That is the member this project's own doc already cites GwAu3's two lines as
    corroboration for (``py4gw/map.py:1078-1083``). The array shape is GwAu3's: two floats, x first.

    **The divergence is the port's own recorded one, not a new one**: that member answers *the mouse
    location now*, because the IO-event gate that would pin it to the moment of the click is the
    injected runtime's ImGui context and is unreachable here (``py4gw/map.py:1063-1077``). The two agree
    whenever the mouse has not moved since the click, and differ otherwise.
    """

    from ..map import Map

    return [float(value) for value in Map.MissionMap.GetLastClickCoords()]


def Map_IsMapUnlocked(a_i_MapID: Any) -> bool:
    """Whether the client has a map unlocked (``GwAu3_Data_Map.au3:386-406``).

    **Parity, key for key.** GwAu3 walks the world context's unlock bitfield by hand: the array at
    ``+0x60C``, its buffer and ``m_size`` words, ``False`` when either is empty, ``False`` when
    ``Floor(map_id / 32)`` is past the end, and then the bit test
    ``BitAND(array[map_id / 32], 1 << (map_id % 32)) <> 0`` (``:389-405``). This layer has the same
    member -- `Map.IsMapUnlocked` (``py4gw/map.py:506``) -- which makes exactly that walk over the same
    array (`WorldContextStruct.unlocked_maps`, ``py4gw/context/world_context.py:1940``; the array is
    declared at ``+0x60C``, ``:1491``), with the same four guards and the same answer.

    No default argument, because GwAu3's own declaration has none (``:386``) -- the ported member's
    ``mapid: int | None = None`` is not taken here, since a migrating call always passes the id.
    """

    from ..map import Map

    return bool(Map.IsMapUnlocked(a_i_MapID))

__all__ = ['Map_GetAreaInfo', 'Map_GetCharacterInfo', 'Map_GetClickCoords', 'Map_GetCurrentAreaInfo', 'Map_GetCurrentRegionType', 'Map_GetInstanceInfo', 'Map_GetInstanceUpTime', 'Map_GetLastMoveCoords', 'Map_GetMapID', 'Map_GetRegion', 'Map_IsMapUnlocked']
