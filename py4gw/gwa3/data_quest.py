"""GwAu3's `Quest_GetQuestInfo`, over the record this project already reads.
**Generated. Do not edit by hand** -- run ``python tools/generate_gwa3_family.py``.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

GwAu3's quest-log reader. GwAu3 walks ``BasePointer -> 0x18 -> 0x2C -> 0x52C`` with a ``0x34`` stride and matches the quest id; this project walks the same log (`py4gw/context/world_context.py:1442`, `quest_log_array` at ``+0x52C``) and reads each entry as `QuestStruct`, whose size is exactly GwAu3's ``0x34``.

`Quest_GetQuestInfo` is one ``Switch`` over 22 keys in GwAu3
(``GwAu3_Data_Quest.au3``). 15 of the 22 field keys resolve to a **named
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
from ..context import QuestStruct
from ..quest import Quest
_UNIMPLEMENTED: dict[str, str] = {'NameEnc': 'GwAu3_Data_Quest.au3:30-32 returns the pointer at ``+0xC``. This project names that field `name_ptr` (`py4gw/context/world_context.py:1169`), and a client address is of no use to a caller here -- the answer is refused rather than returned raw, because a caller cannot tell an address from an encoded string.', 'NPCNameEnc': 'GwAu3_Data_Quest.au3:36-38 returns the pointer at ``+0x10``, which this project names `npc_ptr` (`py4gw/context/world_context.py:1169`). Refused rather than returned raw: a caller cannot tell a client address from an encoded string.', 'NPCName': "GwAu3_Data_Quest.au3:39-41 decodes the pointer at ``+0x10`` on the game thread. This project's decode is the request/collect handshake in `py4gw/native_src/quest/py_quest.py:242` and `:278`, whose sequencing is outstanding. Refused rather than returning the pointer.", 'DescriptionEnc': 'GwAu3_Data_Quest.au3:63-65 returns the pointer at ``+0x2C``, which this project names `description_ptr` (`py4gw/context/world_context.py:1169`). Refused rather than returned raw: a caller cannot tell a client address from an encoded string.', 'ObjectivesEnc': 'GwAu3_Data_Quest.au3:69-71 returns the pointer at ``+0x30``, which this project names `objectives_ptr` (`py4gw/context/world_context.py:1169`). Refused rather than returned raw: a caller cannot tell a client address from an encoded string.', 'Objectives': "GwAu3_Data_Quest.au3:72-74 decodes the pointer at ``+0x30`` on the game thread. This project's decode is the request/collect handshake in `py4gw/native_src/quest/py_quest.py:242` and `:278`; `py4gw/quest.py:158` `GetQuestObjectives` is behind the same handshake. Refused rather than returning the pointer."}

_COMPUTED: frozenset[str] = frozenset(['Description', 'Location', 'LocationStr', 'Name'])

# A text key takes the id as well as the record, because its handshake is keyed by the id.

# Keys that answer `False` rather than `0` when no record matches, because GwAu3's own guard does.
_FALSE_ON_MISSING: frozenset[str] = frozenset(['HasQuest'])


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


def _read_hasinfo(record: Any) -> bool:
    """``GwAu3_Data_Quest.au3`` -- the ``HasInfo`` case: ``BitAND(log_state, 0x1) <> 0``."""

    return bool(record.log_state & 0x1)


def _read_isareaprimary(record: Any) -> bool:
    """``GwAu3_Data_Quest.au3`` -- the ``IsAreaPrimary`` case: ``BitAND(log_state, 0x40) <> 0``."""

    return bool(record.log_state & 0x40)


def _read_iscompleted(record: Any) -> bool:
    """``GwAu3_Data_Quest.au3`` -- the ``IsCompleted`` case: ``BitAND(log_state, 0x2) <> 0``."""

    return bool(record.log_state & 0x2)


def _read_iscurrentquest(record: Any) -> bool:
    """``GwAu3_Data_Quest.au3`` -- the ``IsCurrentQuest`` case: ``BitAND(log_state, 0x10) <> 0``."""

    return bool(record.log_state & 0x10)


def _read_isprimary(record: Any) -> bool:
    """``GwAu3_Data_Quest.au3`` -- the ``IsPrimary`` case: ``BitAND(log_state, 0x20) <> 0``."""

    return bool(record.log_state & 0x20)


def _read_description(record: Any, record_id: Any) -> Any:
    """``GwAu3_Data_Quest.au3`` -- the ``Description`` case, through this project's name handshake.

    The three steps are the port's own (`Quest.RequestQuestDescription(record_id)`, `Quest.IsQuestDescriptionReady(record_id)`, `Quest.GetQuestDescription(record_id)`), taken in the order
    that makes them work: a decode is not a read, and taking the value without requesting it
    answers an empty string a caller cannot tell from a nameless record.
    """

    return _read_text(Quest.RequestQuestDescription, Quest.IsQuestDescriptionReady, Quest.GetQuestDescription, record_id)


def _read_location(record: Any, record_id: Any) -> Any:
    """``GwAu3_Data_Quest.au3`` -- the ``Location`` case, through this project's name handshake.

    The three steps are the port's own (`Quest.RequestQuestLocation(record_id)`, `Quest.IsQuestLocationReady(record_id)`, `Quest.GetQuestLocation(record_id)`), taken in the order
    that makes them work: a decode is not a read, and taking the value without requesting it
    answers an empty string a caller cannot tell from a nameless record.
    """

    return _read_text(Quest.RequestQuestLocation, Quest.IsQuestLocationReady, Quest.GetQuestLocation, record_id)


def _read_locationstr(record: Any, record_id: Any) -> Any:
    """``GwAu3_Data_Quest.au3`` -- the ``LocationStr`` case, through this project's name handshake.

    The three steps are the port's own (`Quest.RequestQuestLocation(record_id)`, `Quest.IsQuestLocationReady(record_id)`, `Quest.GetQuestLocation(record_id)`), taken in the order
    that makes them work: a decode is not a read, and taking the value without requesting it
    answers an empty string a caller cannot tell from a nameless record.
    """

    return _read_text(Quest.RequestQuestLocation, Quest.IsQuestLocationReady, Quest.GetQuestLocation, record_id)


def _read_name(record: Any, record_id: Any) -> Any:
    """``GwAu3_Data_Quest.au3`` -- the ``Name`` case, through this project's name handshake.

    The three steps are the port's own (`Quest.RequestQuestName(record_id)`, `Quest.IsQuestNameReady(record_id)`, `Quest.GetQuestName(record_id)`), taken in the order
    that makes them work: a decode is not a read, and taking the value without requesting it
    answers an empty string a caller cannot tell from a nameless record.
    """

    return _read_text(Quest.RequestQuestName, Quest.IsQuestNameReady, Quest.GetQuestName, record_id)


def _read_descriptionenc(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["DescriptionEnc"])


def _read_npcname(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["NPCName"])


def _read_npcnameenc(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["NPCNameEnc"])


def _read_nameenc(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["NameEnc"])


def _read_objectives(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["Objectives"])


def _read_objectivesenc(record: Any) -> Any:
    """**Refused, not answered.** See `_UNIMPLEMENTED` for why."""

    raise NotImplementedError(_UNIMPLEMENTED["ObjectivesEnc"])


def _read_hasquest(record: Any) -> bool:
    """``GwAu3_Data_Quest.au3`` -- the ``HasQuest`` case has no record to read, so GwAu3's own
    no-match guard answers ``False`` (``GwAu3_Data_Quest.au3``, the guard before its walk)."""

    return False




def _quest_log(client: Any) -> list[QuestStruct]:
    """The quest log, as the client's own ``GetQuestLog`` answers it.

    ``py4gw/native_src/quest/py_quest.py:130-144`` reaches it the same way: the world context is read
    **now** -- a stored one is a dereferenced read, which this project does not keep -- and its quest
    array is taken as a list.
    """

    world = client.read_world_context()
    if world is None:
        return []
    return list(world.quests or [])


def _find_quest(records: list[QuestStruct], quest_id: int) -> QuestStruct | None:
    """The log entry whose id matches, from the log read on **every** call.

    The same walk GwAu3 makes, over the same array: its offsets are ``0x52C`` into the world context
    with a ``0x34`` stride, and this project's `quest_log_array` sits at ``+0x52C`` with
    `QuestStruct` sized ``0x34``. A stored record is a dereferenced read, which this project does not
    keep.
    """

    for record in records:
        if int(record.quest_id) == quest_id:
            return record
    return None

_READERS: dict[str, Any] = {}
_READERS.update(
    {
        "Description": _read_description,
        "DescriptionEnc": _read_descriptionenc,
        "HasInfo": _read_hasinfo,
        "HasQuest": _read_hasquest,
        "IsAreaPrimary": _read_isareaprimary,
        "IsCompleted": _read_iscompleted,
        "IsCurrentQuest": _read_iscurrentquest,
        "IsPrimary": _read_isprimary,
        "Location": _read_location,
        "LocationStr": _read_locationstr,
        "LogState": lambda record: record.log_state,
        "MapFrom": lambda record: record.map_from,
        "MapTo": lambda record: record.map_to,
        "MarkerX": lambda record: record.marker_ptr.x,
        "MarkerY": lambda record: record.marker_ptr.y,
        "MarkerZ": lambda record: record.marker_ptr.zplane,
        "NPCName": _read_npcname,
        "NPCNameEnc": _read_npcnameenc,
        "Name": _read_name,
        "NameEnc": _read_nameenc,
        "Objectives": _read_objectives,
        "ObjectivesEnc": _read_objectivesenc,
    }
)


def Quest_GetQuestInfo(record_id: Any, info: str = "") -> Any:
    """One field of the record, by GwAu3's field name (``GwAu3_Data_Quest.au3``).

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

    ``_find_quest(_quest_log(client), int(record_id))`` -- this project's own read, which is the same
    client record GwAu3 addresses by base plus stride.
    """

    client = require_client()
    return _find_quest(_quest_log(client), int(record_id))


__all__ = ['Quest_GetQuestInfo']
