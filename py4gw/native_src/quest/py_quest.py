"""Port of Native's ``PyQuest`` module (``src/GW/quest/quest_bindings.cpp``, 506 lines).

The binding is two halves and its own comment says which is which
(``quest_bindings.cpp:27-33``): the data half — ``QuestData`` and the quest log — is read from the
process, while what the module *does* is the game-side work a plain context read cannot do: the
client's own decoders for the five quest text fields, and the calls that change which quest is
active. This port keeps that split; the record reads come from
``py4gw/context/world_context.py`` (``QuestStruct``, ``active_quest_id``, ``quest_log_array``,
``mission_objectives_array``), which is where the source's own Python reads them too.

**Where each member's behaviour comes from**, so nothing here is this port's invention:

| member group | source |
| --- | --- |
| ``get_quest_data`` / ``get_quest_log`` / ``get_quest_log_ids`` / the two ``is_quest_*`` bits | ``quest_bindings.cpp:241-267, 321-356`` and ``quest_methods.cpp:56-70`` (the log walk that matches ``quest_id``) |
| ``set_active_quest_id`` / ``abandon_quest_id`` | ``quest_bindings.cpp:293-310`` → ``quest_methods.cpp:20-46`` → **the hook's own body**, ``quest.cpp:34-44`` |
| ``request_quest_info`` | ``quest_bindings.cpp:357-365`` → ``quest_methods.cpp:106-117`` (both functions, in that order, behind the same guard) |
| ``is_mission_map_quest_available`` | ``quest_bindings.cpp:81-84`` (the mission-objective array is not empty) |
| the five ``(request / is_ready / get)`` trios | ``quest_bindings.cpp:58-239`` — one store per field, the client's decoder, and the mission-map constants for a negative id |
| ``get_quest_entry_group_name`` | ``quest_methods.cpp:72-93`` (the ``log_state`` switch and its three literal formats) |

**Three recorded divergences, all of them the execution model and none a change in behaviour:**

1. **No worker thread; the source's own bound is kept.** The binding pre-creates a store entry,
   decodes on a detached ``std::thread``, and waits up to **1000 ms** for the game thread to run the
   decode, writing ``"Timeout"`` when it does not (``quest_bindings.cpp:90-113``, and the same bound
   per objective at ``:216-225``). This port's call path *is* the game thread, so the decode is
   started inline — the detached thread is the part that cannot exist here, because there is nothing
   to wait for. **The bound and its literal are kept**: a decode the client does not answer inside
   ``DECODE_TIMEOUT_SECONDS`` answers ``"Timeout"`` with the entry ready, exactly as the source's
   worker writes it, and the decode slot goes back to the pool on this side because a slot left in
   flight is one the next request cannot have.
2. **Set-active and abandon call the client's own functions.** The source calls the client's own
   ``g_set_active_quest_func``/``g_abandon_quest_func`` and *hooks* them; the hook body replaces the
   client's behaviour with ``ui::SendUIMessage(kSendSetActiveQuest / kSendAbandonQuest, quest_id)``
   (``quest.cpp:34-44``). An earlier version of this port sent that message, because it places no hook
   on those two functions. **A live run on 2026-10-06 refuted it** — on a client with a real quest log
   the message left the active quest at 1098 for a full 12 s, while calling the function moved it to
   167 instantly — so the port calls. That is also the closer port: the source's inner layer calls
   these functions, and with Native's runtime present its hook intercepts the call exactly as it does
   for Native's own callers, while with no runtime present the client's own implementation runs.
3. **The guards are the source's, in the source's order**: ``< 0`` first, then the function has to be
   resolvable, then the quest has to be in the log (``quest_methods.cpp:20-26``, ``:38-46``). They
   gate the **call**, and the answer stays the binding's ``true`` — see
   :meth:`PyQuest.set_active_quest_id`.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

from ...game_thread.shared_block import CallForm, DecodeState

#: ``g_quest_*_map``'s counterpart: one store per decoded field, keyed by quest id, holding the
#: value and whether the client has answered (``AsyncStrEntry``, ``quest_bindings.cpp:58-61``).
_NAME: dict[int, tuple[str, bool]] = {}
_DESCRIPTION: dict[int, tuple[str, bool]] = {}
_OBJECTIVES: dict[int, tuple[str, bool]] = {}
_LOCATION: dict[int, tuple[str, bool]] = {}
_NPC: dict[int, tuple[str, bool]] = {}

#: The decode slot each store is waiting on, with the moment the request started — the pair the
#: source keeps inside its worker thread. Here it is what ``is_*_ready`` polls, what ``get_*`` takes
#: from, and what the source's own ``DECODE_TIMEOUT_SECONDS`` bound is measured against.
_PENDING: dict[tuple[str, int], tuple[int, float]] = {}

_STORES: dict[str, dict[int, tuple[str, bool]]] = {
    "name": _NAME,
    "description": _DESCRIPTION,
    "objectives": _OBJECTIVES,
    "location": _LOCATION,
    "npc": _NPC,
}

#: What the binding writes for a negative quest id (``quest_bindings.cpp:115-151``).
_MISSION_OBJECTIVES = "Mission Objectives"
_MISSION_ONGOING = "Mission Ongoing"
_NO_ACTIVE_MISSION = "No Active Mission"

#: The mission-objective bullet markers the binding composes with (``quest_bindings.cpp:229-235``).
_BULLET = "{s}"
_BULLET_COMPLETED = "{sc}"

#: The binding's decode wait and the value it writes when the client does not answer inside it
#: (``quest_bindings.cpp:100-108``: 1000 ms, then ``store[quest_id].value = "Timeout"``).
DECODE_TIMEOUT_SECONDS = 1.0
TIMEOUT = "Timeout"

#: The binding's own call forms: ``RequestQuestInfoFn = void(__cdecl*)(uint32_t)`` and
#: ``RequestQuestDataFn = void(__cdecl*)(uint32_t, bool)`` (``quest.cpp:14-16``).
_U32 = CallForm.U32
_U32_U32 = CallForm.U32_U32


@dataclass
class QuestData:
    """``struct QuestData`` (``quest_bindings.cpp:272-289``) — the record the binding hands back.

    The field names are the binding's own, spelled as it binds them. ``name``/``description``/
    ``objectives``/``location``/``npc`` stay empty when the value comes from ``get_quest_data`` or
    ``get_quest_log``: those two fill the numeric and the two bit fields only
    (``quest_bindings.cpp:321-356``), and the strings come from the decode trios.
    """

    quest_id: int = 0
    log_state: int = 0
    location: str = ""
    name: str = ""
    npc: str = ""
    map_from: int = 0
    marker_x: float = 0.0
    marker_y: float = 0.0
    h0024: int = 0
    map_to: int = 0
    description: str = ""
    objectives: str = ""
    is_completed: bool = False
    is_current_mission_quest: bool = False
    is_area_primary: bool = False
    is_primary: bool = False


def _client() -> Any:
    from ...client import require_client

    return require_client()


def _world(client: Any) -> Any:
    try:
        return client.read_world_context()
    except (OSError, RuntimeError):
        return None


def _quest_log(client: Any) -> list[Any]:
    """The quest log, as ``GW::Context::GetQuestLog()`` answers it (``context_methods.cpp:328``)."""

    world = _world(client)
    if world is None:
        return []
    return list(world.quests or [])


def _get_quest(client: Any, quest_id: int) -> Any | None:
    """``GW::quest::GetQuest`` (``quest_methods.cpp:56-70``): id 0 is nothing, else a log match."""

    if quest_id == 0:
        return None
    for quest in _quest_log(client):
        if int(quest.quest_id) == int(quest_id):
            return quest
    return None


def _quest_data(record: Any) -> QuestData:
    """``PyQuest::GetQuest``'s filled fields (``quest_bindings.cpp:321-335``).

    **Seven fields and no more.** The source copies ``log_state``, ``map_from``, ``map_to``,
    ``marker_x``, ``marker_y``, ``is_completed`` and ``is_primary``; ``h0024``,
    ``is_current_mission_quest`` and ``is_area_primary`` are left exactly as the struct's defaults,
    even when the record itself carries those bits. An earlier version of this port copied ``h0024``
    across because the record has a field of that name — which the source does not do, and which the
    test below now pins.
    """

    data = QuestData(quest_id=int(record.quest_id), log_state=int(record.log_state))
    marker = record.marker_ptr
    data.map_from = int(record.map_from)
    data.map_to = int(record.map_to)
    data.marker_x = float(marker.x)
    data.marker_y = float(marker.y)
    data.is_completed = bool(record.is_completed)
    data.is_primary = bool(record.is_primary)
    return data


def _log_data(record: Any) -> QuestData:
    """``PyQuest::GetQuestLog``'s lighter copy (``quest_bindings.cpp:342-356``).

    It fills the ids, the state word, the two maps and the marker — and deliberately neither of the
    bit flags nor the strings, which is the source's own difference between the two members.
    """

    data = QuestData(quest_id=int(record.quest_id), log_state=int(record.log_state))
    data.map_from = int(record.map_from)
    data.map_to = int(record.map_to)
    marker = record.marker_ptr
    data.marker_x = float(marker.x)
    data.marker_y = float(marker.y)
    return data


def _encoded_bytes(text: str | None) -> bytes | None:
    """The client's own bytes for one record string, terminator included.

    ``AsyncDecodeStr`` is handed the wide string as it stands in the client
    (``quest_methods.cpp:119-139``); the record's code units are what the reader already produced,
    so this puts them back into that form.
    """

    if not text:
        return None
    return text.encode("utf-16-le") + b"\x00\x00"


# The per-field decoders, one per store: the binding passes ``&GW::quest::AsyncGetQuestName`` and
# its four siblings as the ``decode`` parameter of ``RunNormalQuestString``
# (``quest_bindings.cpp:86-121``), and these are that parameter here — a named function per field
# rather than a field name reached dynamically.
def _decode_name(record: Any) -> bytes | None:
    return _encoded_bytes(record.name_encoded_str)


def _decode_description(record: Any) -> bytes | None:
    return _encoded_bytes(record.description_encoded_str)


def _decode_objectives(record: Any) -> bytes | None:
    return _encoded_bytes(record.objectives_encoded_str)


def _decode_location(record: Any) -> bytes | None:
    return _encoded_bytes(record.location_encoded_str)


def _decode_npc(record: Any) -> bytes | None:
    return _encoded_bytes(record.npc_encoded_str)


_DECODERS: dict[str, Callable[[Any], bytes | None]] = {
    "name": _decode_name,
    "description": _decode_description,
    "objectives": _decode_objectives,
    "location": _decode_location,
    "npc": _decode_npc,
}


def _start(field_name: str, quest_id: int, encoded: bytes) -> bool:
    """Place the string, start the client's decoder, and record the slot for that store.

    ``begin_string_decode`` is the port's ``param`` — what native allocates and fills before it calls
    the decoder — and the request is recorded **before** the call, exactly as the source's callers
    do, so a completion that arrives inside the call belongs to this request.
    """

    from ...ui.async_decode import async_decode_str, begin_string_decode

    store = _STORES[field_name]
    store[quest_id] = ("", False)
    try:
        slot = begin_string_decode(encoded)
    except (OSError, RuntimeError):
        return False
    _PENDING[(field_name, quest_id)] = (slot, time.monotonic())
    return bool(async_decode_str(encoded, slot))


def _release(slot: int) -> None:
    """Give one decode slot back, which is what a caller does with a decode that will not arrive.

    ``async_decode``'s slots are a bounded pool and a slot is only free once it is taken or released;
    the source has no such bookkeeping because its region is its own, so this is the port's side of a
    decode the client never answered — the same case the source covers by writing ``"Timeout"``.
    """

    from ...client import require_client

    try:
        require_client().bridge.release_decode(slot)
    except (OSError, RuntimeError):
        pass


def _collect(field_name: str, quest_id: int) -> tuple[str, bool]:
    """Take the client's answer for one store if it has arrived, and say what the store holds.

    The source's worker writes ``value``/``ready`` and its getters read them; here the slot is
    polled the same way ``is_*_ready`` polls it, and a completed decode is moved into the store once.

    **The source's own timeout, in the source's own place.** The worker gives the client
    ``DECODE_TIMEOUT_MS`` and then writes ``"Timeout"`` with the entry ready anyway
    (``quest_bindings.cpp:100-108``), so a caller that waits never waits forever and the value it
    gets says what happened. Here the same bound is measured from the request and the same literal is
    written — and the decode slot goes back to the pool first, because this side owns it
    (``async_decode``'s slots are taken or released, and a slot left in flight is one the next request
    cannot have).
    """

    from ...ui.async_decode import decode_state, decoded_text

    store = _STORES[field_name]
    entry = store.get(quest_id)
    if entry is not None and entry[1]:
        return entry
    pending = _PENDING.get((field_name, quest_id))
    if pending is None:
        return entry if entry is not None else ("", False)
    slot, started = pending
    if decode_state(slot) is DecodeState.DONE:
        text, _ready = decoded_text(slot)
        _PENDING.pop((field_name, quest_id), None)
        store[quest_id] = (text, True)
        return text, True
    if time.monotonic() - started >= DECODE_TIMEOUT_SECONDS:
        _release(slot)
        _PENDING.pop((field_name, quest_id), None)
        store[quest_id] = (TIMEOUT, True)
        return TIMEOUT, True
    return entry if entry is not None else ("", False)


def _ready(field_name: str, quest_id: int) -> bool:
    return _collect(field_name, quest_id)[1]


def _value(field_name: str, quest_id: int) -> str:
    return _collect(field_name, quest_id)[0]


def _mission_map_available(client: Any) -> bool:
    """``IsMissionMapQuestAvailable`` (``quest_bindings.cpp:81-84``): objectives are present."""

    world = _world(client)
    if world is None:
        return False
    return len(world.mission_objectives or []) > 0


def _uint32_to_enc_str(value: int) -> bytes | None:
    """``ui::UInt32ToEncStr(value, buffer, 8)`` (``ui_bindings.cpp:1132-1136``)."""

    from ...ui_manager import UIManager

    return _encoded_bytes(UIManager.UInt32ToEncStr(int(value)))


def _await_slot(slot: int, started: float) -> tuple[str, bool]:
    """Read one decode slot on this call path, under the binding's own bound.

    The source's mission-objective worker waits up to 1000 ms per objective and then puts
    ``"Timeout"`` in that objective's text (``quest_bindings.cpp:216-225``); this is that bound, with
    the slot given back when the answer never comes so the pool does not lose it.
    """

    from ...ui.async_decode import decode_state, decoded_text

    if decode_state(slot) is DecodeState.DONE:
        return decoded_text(slot)
    if time.monotonic() - started >= DECODE_TIMEOUT_SECONDS:
        _release(slot)
        return TIMEOUT, True
    return "", False


def _request_mission_location(client: Any, quest_id: int) -> None:
    """The negative-id location: the current map's own name (``quest_bindings.cpp:152-178``).

    The binding takes ``GW::map::GetCurrentMapInfo()->name_id`` (or ``3`` when it is zero), encodes
    it into eight code units with ``ui::UInt32ToEncStr``, and hands *that* to the decoder.
    """

    from ...map import Map
    from ...ui.async_decode import async_decode_str, begin_string_decode

    name_id = int(Map.GetNameID()) or 3
    encoded = _uint32_to_enc_str(name_id)
    if encoded is None:
        return
    try:
        slot = begin_string_decode(encoded)
    except (OSError, RuntimeError):
        return
    _PENDING[("location", quest_id)] = (slot, time.monotonic())
    async_decode_str(encoded, slot)


def _request_mission_objectives(client: Any, quest_id: int) -> None:
    """The negative-id objectives: every mission objective, composed as the binding composes them.

    ``quest_bindings.cpp:186-238``: each objective's encoded string is decoded, a bullet marker is
    prefixed for a bullet objective (``{sc}`` when completed, ``{s}`` otherwise), and every line ends
    with a newline. ``"No Active Mission"`` is the whole answer when there is no mission.

    **The string handed to the decoder is the record's raw one.** ``MissionObjectiveStruct`` carries
    the encoded text as ``enc_str_encoded_str`` and its ``enc_str`` is the *printable rendering* this
    port's reader produces (``\\\\xNNNN`` escapes) — the source hands the client the string itself
    (``AsyncDecodeAnyEncStr(obj.enc_str, ...)``), so an earlier version of this that passed ``enc_str``
    was giving the client's decoder an escaped copy of a string it had produced.
    """

    from ...ui.async_decode import async_decode_str, begin_string_decode

    world = _world(client)
    if world is None:
        return
    if not _mission_map_available(client):
        _OBJECTIVES[quest_id] = (_NO_ACTIVE_MISSION, True)
        return
    lines: list[str] = []
    for objective in world.mission_objectives or []:
        encoded = _encoded_bytes(objective.enc_str_encoded_str)
        if encoded is None:
            continue
        try:
            slot = begin_string_decode(encoded)
        except (OSError, RuntimeError):
            continue
        started = time.monotonic()
        async_decode_str(encoded, slot)
        text, _ready = _await_slot(slot, started)
        if int(objective.type) & 0x1:
            lines.append((_BULLET_COMPLETED if int(objective.type) & 0x2 else _BULLET) + text)
        else:
            lines.append(text)
    _OBJECTIVES[quest_id] = ("".join(line + "\n" for line in lines), True)


def _request_field(field_name: str, quest_id: int) -> None:
    """One field's request: a negative id answers a mission value, otherwise the client decodes.

    The per-field mission values are the binding's own (``quest_bindings.cpp:115-151, 181-239``).
    """

    client = _client()
    store = _STORES[field_name]
    if quest_id < 0:
        available = _mission_map_available(client)
        if field_name == "location":
            if not available:
                store[quest_id] = (_NO_ACTIVE_MISSION, True)
                return
            store[quest_id] = ("", False)
            _request_mission_location(client, quest_id)
            return
        if field_name == "objectives":
            store[quest_id] = ("", False)
            _request_mission_objectives(client, quest_id)
            return
        if field_name == "name":
            store[quest_id] = (_MISSION_OBJECTIVES if available else _NO_ACTIVE_MISSION, True)
            return
        store[quest_id] = (_MISSION_ONGOING if available else _NO_ACTIVE_MISSION, True)
        return

    record = _get_quest(client, quest_id)
    if record is None:
        store[quest_id] = ("", False)
        return
    encoded = _DECODERS[field_name](record)
    if encoded is None:
        store[quest_id] = ("", False)
        return
    _start(field_name, quest_id, encoded)


class PyQuest:
    """``struct PyQuest`` (``quest_bindings.cpp:292-366``) — the binding's own static surface."""

    @staticmethod
    def set_active_quest_id(quest_id: int) -> bool:
        """``quest_bindings.cpp:293-299`` → ``quest_methods.cpp:20-26``: **the call**, with its guards.

        The source calls ``g_set_active_quest_func(quest_id)`` — the client's own function — behind two
        guards (it resolves, and the quest is in the log) and answers ``true`` for any id that is not
        negative, because the guards run inside the enqueued lambda and their result is discarded.

        **Native hooks that function, and its hook body sends ``kSendSetActiveQuest`` instead. An
        earlier version of this port sent that message rather than calling, and a live run on
        2026-10-06 settled the question**: the message left the active quest untouched for a full
        12 s, while calling the function moved it instantly (1098 → 167). The call is also the closer
        port of the source: with the injected runtime present, Reforged's own hook intercepts the call
        exactly as it does for Reforged's callers, and without it the client's own implementation runs.
        """

        if quest_id < 0:
            return False
        client = _client()
        if client.resolves("quest.set_active_quest_func") and _get_quest(client, quest_id) is not None:
            client.call_function("quest.set_active_quest_func", _U32, int(quest_id))
        return True

    @staticmethod
    def get_active_quest_id() -> int:
        """``quest_bindings.cpp:300-303`` — ``WorldContext::active_quest_id``."""

        world = _world(_client())
        return int(world.active_quest_id) if world is not None else 0

    @staticmethod
    def abandon_quest_id(quest_id: int) -> bool:
        """``quest_bindings.cpp:304-310`` → ``quest_methods.cpp:38-46``: the call, as its sibling above.

        ``abandon_quest_func`` is the function Reforged's inner layer calls and its hook intercepts —
        the same shape as :meth:`set_active_quest_id`, including the two guards and the answer.
        """

        if quest_id < 0:
            return False
        client = _client()
        if client.resolves("quest.abandon_quest_func") and _get_quest(client, quest_id) is not None:
            client.call_function("quest.abandon_quest_func", _U32, int(quest_id))
        return True

    @staticmethod
    def is_quest_completed(quest_id: int) -> bool:
        """``quest_bindings.cpp:311-315`` — the record's ``log_state & 0x2``."""

        if quest_id < 0:
            return False
        record = _get_quest(_client(), quest_id)
        return bool(record is not None and record.is_completed)

    @staticmethod
    def is_quest_primary(quest_id: int) -> bool:
        """``quest_bindings.cpp:316-320`` — the record's ``log_state & 0x20``."""

        if quest_id < 0:
            return False
        record = _get_quest(_client(), quest_id)
        return bool(record is not None and record.is_primary)

    @staticmethod
    def is_mission_map_quest_available() -> bool:
        """``quest_bindings.cpp:81-84``."""

        return _mission_map_available(_client())

    @staticmethod
    def get_quest_data(quest_id: int) -> QuestData:
        """``quest_bindings.cpp:321-335``."""

        record = _get_quest(_client(), int(quest_id))
        if record is None:
            return QuestData(quest_id=int(quest_id))
        return _quest_data(record)

    @staticmethod
    def get_quest_log() -> list[QuestData]:
        """``quest_bindings.cpp:342-356``."""

        return [_log_data(record) for record in _quest_log(_client())]

    @staticmethod
    def get_quest_log_ids() -> list[int]:
        """``quest_bindings.cpp:336-341``."""

        return [int(record.quest_id) for record in _quest_log(_client())]

    @staticmethod
    def request_quest_info(quest_id: int, update_markers: bool = False) -> bool:
        """``quest_bindings.cpp:357-365`` → ``quest_methods.cpp:106-117``: both calls, in order.

        The answer is ``true`` for an id that is not negative, as the source answers it — the guards
        (both functions resolving, the quest being in the log) belong to
        ``GW::quest::RequestQuestInfoId`` inside the enqueued lambda, and they decide only whether the
        two calls are made. When they are, the order is the source's: the info call, then the data
        call with ``update_markers``.
        """

        if quest_id < 0:
            return False
        client = _client()
        if (
            client.resolves("quest.request_quest_info_func")
            and client.resolves("quest.request_quest_data_func")
            and _get_quest(client, quest_id) is not None
        ):
            client.call_function("quest.request_quest_info_func", _U32, int(quest_id))
            client.call_function(
                "quest.request_quest_data_func", _U32_U32, int(quest_id), int(bool(update_markers))
            )
        return True

    # -- the five (request / is_ready / get) trios (``quest_bindings.cpp:398-412``) ---------

    @staticmethod
    def request_quest_name(quest_id: int) -> None:
        """``quest_bindings.cpp:115-122``."""

        _request_field("name", int(quest_id))

    @staticmethod
    def is_quest_name_ready(quest_id: int) -> bool:
        """``quest_bindings.cpp:399`` — the store's ready flag."""

        return _ready("name", int(quest_id))

    @staticmethod
    def get_quest_name(quest_id: int) -> str:
        """``quest_bindings.cpp:400`` — the store's value, or the empty string."""

        return _value("name", int(quest_id))

    @staticmethod
    def request_quest_description(quest_id: int) -> None:
        """``quest_bindings.cpp:124-131``."""

        _request_field("description", int(quest_id))

    @staticmethod
    def is_quest_description_ready(quest_id: int) -> bool:
        """``quest_bindings.cpp:402``."""

        return _ready("description", int(quest_id))

    @staticmethod
    def get_quest_description(quest_id: int) -> str:
        """``quest_bindings.cpp:403``."""

        return _value("description", int(quest_id))

    @staticmethod
    def request_quest_objectives(quest_id: int) -> None:
        """``quest_bindings.cpp:181-239``."""

        _request_field("objectives", int(quest_id))

    @staticmethod
    def is_quest_objectives_ready(quest_id: int) -> bool:
        """``quest_bindings.cpp:405``."""

        return _ready("objectives", int(quest_id))

    @staticmethod
    def get_quest_objectives(quest_id: int) -> str:
        """``quest_bindings.cpp:406``."""

        return _value("objectives", int(quest_id))

    @staticmethod
    def request_quest_location(quest_id: int) -> None:
        """``quest_bindings.cpp:142-179``."""

        _request_field("location", int(quest_id))

    @staticmethod
    def is_quest_location_ready(quest_id: int) -> bool:
        """``quest_bindings.cpp:408``."""

        return _ready("location", int(quest_id))

    @staticmethod
    def get_quest_location(quest_id: int) -> str:
        """``quest_bindings.cpp:409``."""

        return _value("location", int(quest_id))

    @staticmethod
    def request_quest_npc(quest_id: int) -> None:
        """``quest_bindings.cpp:133-140``."""

        _request_field("npc", int(quest_id))

    @staticmethod
    def is_quest_npc_ready(quest_id: int) -> bool:
        """``quest_bindings.cpp:411``."""

        return _ready("npc", int(quest_id))

    @staticmethod
    def get_quest_npc(quest_id: int) -> str:
        """``quest_bindings.cpp:412``."""

        return _value("npc", int(quest_id))


def get_quest_entry_group_name(quest_id: int) -> str:
    """``GW::quest::GetQuestEntryGroupName`` (``quest_methods.cpp:72-93``), narrowed as the binding does.

    The ``log_state`` switch and its three literal formats are the source's, including the ``\\x1``
    and ``\\x10A`` markup the client's renderer reads; the binding then keeps every code unit below
    128 and turns the rest into ``?`` (``quest_bindings.cpp:454-465``), and that narrowing is kept.
    """

    record = _get_quest(_client(), int(quest_id))
    if record is None:
        return ""
    state = int(record.log_state) & 0xF0
    location = record.location_encoded_str or ""
    if state == 0x20:
        text = "\u0564"
    elif state == 0x40:
        text = "\u8102\u1978\u010a" + location + "\u0001"
    elif state == 0x00:
        text = "\u0565\u010a" + location + "\u0001"
    else:
        return ""
    return "".join(char if ord(char) < 128 else "?" for char in text)


# -- the module-level surface the binding also exposes (``quest_bindings.cpp:416-501``) -----

set_active_quest_id = PyQuest.set_active_quest_id
get_active_quest_id = PyQuest.get_active_quest_id
abandon_quest_id = PyQuest.abandon_quest_id
is_quest_completed = PyQuest.is_quest_completed
is_quest_primary = PyQuest.is_quest_primary
is_mission_map_quest_available = PyQuest.is_mission_map_quest_available
get_quest_log_ids = PyQuest.get_quest_log_ids
request_quest_info = PyQuest.request_quest_info
request_quest_name = PyQuest.request_quest_name
is_quest_name_ready = PyQuest.is_quest_name_ready
get_quest_name = PyQuest.get_quest_name
request_quest_description = PyQuest.request_quest_description
is_quest_description_ready = PyQuest.is_quest_description_ready
get_quest_description = PyQuest.get_quest_description
request_quest_objectives = PyQuest.request_quest_objectives
is_quest_objectives_ready = PyQuest.is_quest_objectives_ready
get_quest_objectives = PyQuest.get_quest_objectives
request_quest_location = PyQuest.request_quest_location
is_quest_location_ready = PyQuest.is_quest_location_ready
get_quest_location = PyQuest.get_quest_location
request_quest_npc = PyQuest.request_quest_npc
is_quest_npc_ready = PyQuest.is_quest_npc_ready
get_quest_npc = PyQuest.get_quest_npc

__all__ = [
    "PyQuest",
    "QuestData",
    "get_quest_entry_group_name",
    "set_active_quest_id",
    "get_active_quest_id",
    "abandon_quest_id",
    "is_quest_completed",
    "is_quest_primary",
    "is_mission_map_quest_available",
    "get_quest_log_ids",
    "request_quest_info",
    "request_quest_name",
    "is_quest_name_ready",
    "get_quest_name",
    "request_quest_description",
    "is_quest_description_ready",
    "get_quest_description",
    "request_quest_objectives",
    "is_quest_objectives_ready",
    "get_quest_objectives",
    "request_quest_location",
    "is_quest_location_ready",
    "get_quest_location",
    "request_quest_npc",
    "is_quest_npc_ready",
    "get_quest_npc",
]
