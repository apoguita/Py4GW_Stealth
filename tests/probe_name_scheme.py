"""One agent's name, decoded both ways, from the live client.

The two sources answer a name with the same two steps and a different decoder:

* Reforged's Python ``Agent.GetNameByID`` (``Agent.py:142-147``) fetches ``PyAgent.get_agent_enc_name``
  and hands the bytes to ``string_table.decode`` — a table the Python side read out of ``GW.dat``.
  That is the scheme this port implements (``py4gw/internals/string_table.py``).
* Native's ``AsyncGetAgentName`` (``agent_methods.cpp:318-325``) fetches the same pointer and hands
  the string to the **client's own decoder**, ``ui::AsyncDecodeStr`` — already ported here and live
  (``py4gw/ui/async_decode.py``, used by the dialog and the chat log).

For the same agent ids this probe prints both answers and whether they agree, so "which text is
this agent's name" is answered by the client rather than by this project's reading of its tables.
It also prints what the table read keys entries by — ``entries_per_file``, the client's language,
and each file slot's own ``start_index``/``end_index`` against the ``slot_idx * entries_per_file``
that ``_parse_string_file``'s caller assumes — because that is the mapping that decides which entry
any index resolves to. For a gadget it prints native's own walk (``agent_methods.cpp:290-307``): the
summary sub-record, ``gadget_name_enc``, ``gadget_id`` and ``gadget_info``'s record for it.

Every step is written to stdout and to the report file as it happens, so an interrupted run still
leaves what was already found. Usage: ``python tests/probe_name_scheme.py [report-path]``.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from typing import Any

import py4gw
from py4gw import agent as agent_module
from py4gw.agent import Agent
from py4gw.player import Player
from py4gw.win32 import Win32

REPORT_PATH = sys.argv[1] if len(sys.argv) > 1 else ""

#: How many named agents to compare. One is what a caller does; a handful shows whether a
#: disagreement is one agent or the whole scheme.
CANDIDATE_LIMIT = 6

#: How long to wait for the client's decoder to answer one string.
CLIENT_DECODE_DEADLINE_S = 5.0

#: How long to wait for the port's own decode, whose first call reads a string file.
PORT_DECODE_DEADLINE_S = 30.0

#: How long to let the viewer's own rows finish decoding: one string file per entry index, read
#: through the client, is what the port's decode pays for the first name it does not hold.
VIEWER_TABLE_DEADLINE_S = 60.0

#: The player-prefixed encoded form (``string_table._PLAYER_PREFIX``): a player name, not an NPC's.
PLAYER_PREFIX = [0xA9, 0x0B]


def emit(stage: str, **values: Any) -> None:
    """Print one step and append it to the report, immediately."""

    line = json.dumps({"stage": stage, **values}, default=str)
    print(line, flush=True)
    if REPORT_PATH:
        with open(REPORT_PATH, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")


def _slot_metadata(client) -> None:
    """Print what the string-table read keys entries by, and each slot's own range."""

    from py4gw.context.text_parser_context import TextParser

    TextParser._update_ptr()
    context = TextParser.get_context()
    if context is None:
        emit("slots", available=False)
        return

    language = int(context.language_id)
    entries_per_file = int(context.entries_per_file)
    language_slot = context.language_slots[language]
    emit(
        "slots",
        available=True,
        language_id=language,
        entries_per_file=entries_per_file,
        slot_count=int(language_slot.slot_count),
    )

    for slot_index in range(min(int(language_slot.slot_count), 8)):
        slot = context.get_file_slot(slot_index, language)
        if slot is None:
            emit("slot", index=slot_index, present=False)
            continue
        emit(
            "slot",
            index=slot_index,
            present=True,
            lang_id=int(slot.lang_id),
            start_index=int(slot.start_index),
            end_index=int(slot.end_index),
            assumed_start_index=slot_index * entries_per_file,
            hash_code_units=len(slot.file_hash),
            hash_codepoints=[ord(unit) for unit in slot.file_hash],
        )

    # What a cache of this table would have to be keyed on, because it is what identifies the archive
    # the entries came out of: the client's build, the language, the file stride, and the file-slot
    # hashes the client itself publishes. Two runs of this probe on the same Gw.dat must print the
    # same digest; a game patch must change it.
    digest = hashlib.sha256()
    hashes: list[str] = []
    for slot_index in range(int(language_slot.slot_count)):
        slot = context.get_file_slot(slot_index, language)
        if slot is None or not int(slot.file_hash_ptr):
            continue
        hashes.append(slot.file_hash)
        digest.update(slot.file_hash.encode("utf-32-le"))
    emit(
        "cache_premise",
        language_id=language,
        entries_per_file=entries_per_file,
        slot_count=int(language_slot.slot_count),
        readable_slots=len(hashes),
        client_version=_client_version(client),
        first_hash=[ord(unit) for unit in hashes[0]] if hashes else [],
        last_hash=[ord(unit) for unit in hashes[-1]] if hashes else [],
        hash_digest=digest.hexdigest(),
    )


def _client_version(client: Any) -> Any:
    """The client's own version, which is what a game patch changes."""

    try:
        return int(client.memory_manager.GetGWVersion())
    except (OSError, RuntimeError, AttributeError) as error:
        return f"{type(error).__name__}: {error}"


def _gadget_walk(client, agent_id: int) -> None:
    """Print native's own gadget walk for one id (``agent_methods.cpp:290-307``)."""

    from py4gw.context.acc_agent_context import AgentSummaryInfoStruct
    from py4gw.context.gadget_context import GadgetInfoStruct
    from py4gw.context.gw_array import GWArrayValueView

    agent_context = client.read_acc_agent_context()
    gadget_context = client.read_gadget_context()
    if agent_context is None or gadget_context is None:
        emit("gadget_walk", agent_id=agent_id, available=False)
        return

    summary = GWArrayValueView(
        client.reader, agent_context.agent_summary_info, AgentSummaryInfoStruct
    )
    emit(
        "gadget_walk",
        agent_id=agent_id,
        available=True,
        summary_valid=bool(summary.valid()),
        summary_size=int(summary.size()),
    )
    if not summary.valid() or agent_id >= summary.size():
        return

    record = summary.get(agent_id)
    if not isinstance(record, AgentSummaryInfoStruct):
        emit("gadget_walk_record", agent_id=agent_id, record=False)
        return
    emit(
        "gadget_walk_record",
        agent_id=agent_id,
        record=True,
        extra_info_sub_ptr=int(record.extra_info_sub_ptr),
    )

    sub = record.extra_info_sub
    if sub is None:
        emit("gadget_walk_sub", agent_id=agent_id, sub=False)
        return
    emit(
        "gadget_walk_sub",
        agent_id=agent_id,
        sub=True,
        gadget_name_enc=int(sub.gadget_name_enc),
        gadget_id=int(sub.gadget_id),
        composite_agent_id=int(sub.composite_agent_id),
    )

    infos = GWArrayValueView(
        client.reader, gadget_context.gadget_info, GadgetInfoStruct
    )
    gadget_id = int(sub.gadget_id)
    emit(
        "gadget_walk_info",
        agent_id=agent_id,
        gadget_info_valid=bool(infos.valid()),
        gadget_info_size=int(infos.size()),
        gadget_id=gadget_id,
        agent_record_gadget_id=Agent.GetGadgetID(agent_id),
        agent_record_agent_id=Agent.GetGadgetAgentID(agent_id),
        agent_record_extra_type=Agent.GetGadgetAgentExtraType(agent_id),
    )
    if not infos.valid() or gadget_id >= infos.size():
        return
    info = infos.get(gadget_id)
    emit(
        "gadget_walk_info_record",
        agent_id=agent_id,
        record=isinstance(info, GadgetInfoStruct),
        name_enc=int(info.name_enc) if isinstance(info, GadgetInfoStruct) else 0,
    )


def _map_context() -> None:
    """Print where the character is, which is what makes an agent's name readable as a name."""

    from py4gw.map import Map

    def _value(call: Any) -> Any:
        try:
            return call()
        except (NotImplementedError, OSError, RuntimeError) as error:
            return f"{type(error).__name__}: {error}"

    emit(
        "map",
        ready=_value(Map.IsMapReady),
        map_id=_value(Map.GetMapID),
        region=_value(Map.GetRegion),
        district=_value(Map.GetDistrict),
    )
    agent_id = int(Player.GetAgentID())
    emit(
        "player",
        agent_id=agent_id,
        position=_value(lambda: Agent.GetXYZ(agent_id)),
        name=_value(lambda: Agent.GetNameByID(agent_id)),
    )


def _decode_preconditions(client) -> None:
    """Print whether the client-decode route native uses is available in this connection.

    ``py4gw/ui/async_decode.py`` answers ``""`` through its own refusals without calling the
    client at all, so a caller that sees empty text has to be told which of the two it was.
    """

    from py4gw.ui.async_decode import ASYNC_DECODE_STR

    try:
        resolves = bool(client.resolves(ASYNC_DECODE_STR))
    except (OSError, RuntimeError) as error:
        resolves = f"{type(error).__name__}: {error}"
    try:
        decoder_address = int(client.bridge.decoder_address)
    except (OSError, RuntimeError) as error:
        decoder_address = f"{type(error).__name__}: {error}"
    try:
        text_parser_address = int(client.text_parser.resolve_address() or 0)
    except (OSError, RuntimeError) as error:
        text_parser_address = f"{type(error).__name__}: {error}"

    emit(
        "decode_preconditions",
        decoder_resolves=resolves,
        decoder_stub_address=decoder_address,
        text_parser_address=text_parser_address,
    )


def _viewer_table(client) -> None:
    """Print the rows the Reforged agent viewer draws, which is the scheme being followed.

    ``Widgets/Coding/Debug/Guild Wars/Agent Info.py`` builds each row from
    ``AgentArray.GetAgentArray()`` and ``Agent.GetAgentByID(agent_id)``, and its name column is
    ``Agent.GetNameByID(agent.agent_id)`` (``42-80``, ``519-524``). These are those rows.
    """

    array = client.agent_array
    ids = [int(agent_id) for agent_id in array.get_context().GetAgentArray()]
    records = []
    for agent_id in ids:
        record = array.GetAgentByID(agent_id)
        if record is None or int(record.agent_id) == 0:
            continue
        records.append(record)
    emit("viewer_table", rows=len(records))

    # The source's decoder answers "" on the call that starts a decode and the text on a later
    # one (``decode``'s cache), which is why a viewer calls it every frame: this does the same,
    # bounded, rather than reading one name once and calling the empty answer a name.
    for record in records:
        Agent.GetNameByID(int(record.agent_id))
    names: dict[int, str] = {}
    deadline = time.time() + VIEWER_TABLE_DEADLINE_S
    while time.time() < deadline:
        missing = [
            int(record.agent_id)
            for record in records
            if not names.get(int(record.agent_id))
        ]
        if not missing:
            break
        for agent_id in missing:
            text = Agent.GetNameByID(agent_id)
            if text:
                names[agent_id] = text
        time.sleep(0.05)

    for record in records:
        agent_id = int(record.agent_id)
        emit(
            "viewer_row",
            agent_id=agent_id,
            type=int(record.type),
            is_living=bool(record.is_living_type),
            is_gadget=bool(record.is_gadget_type),
            is_item=bool(record.is_item_type),
            name=names.get(agent_id, ""),
            encoded=Agent.GetEncNameStrByID(agent_id),
            position=Agent.GetXYZ(agent_id),
        )


def main() -> int:
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        emit("no_client")
        return 1
    emit("client", pid=int(clients[0]["pid"]), path=clients[0].get("path"))
    if not win32.is_elevated():
        emit("not_elevated", note="a name needs the client's decoder, which needs a write connection")
        return 3

    client = py4gw.connect(clients[0])
    try:
        from py4gw.game_thread.shared_block import EventKind
        from py4gw.internals import string_table
        from py4gw.ui.async_decode import (
            async_decode_str,
            begin_string_decode,
            decode_state,
            decoded_text,
        )

        answers: dict[int, str] = {}
        states: dict[int, str] = {}
        owned: set[int] = set()

        def on_string_decoded(event: object) -> None:
            """Note a completion for a slot *this probe* placed.

            ``STRING_DECODED`` is one kind for every decode in the process, and the dialog and chat
            ports own their own slots: taking theirs here would consume their answers (the earlier
            version of this probe did, which is why every answer looked empty while the slot read
            ``FREE``). Only the state is recorded; the text is taken by the caller, from its own slot.
            """

            slot = int(getattr(event, "sequence"))
            if slot in owned:
                states[slot] = decode_state(slot).name

        client.callbacks.register(EventKind.STRING_DECODED, on_string_decoded)

        def client_decode(encoded: bytes, label: str, agent_id: int) -> str:
            """Hand one string to the client's decoder and report how it answered.

            The wait is on **this slot's own state**, not on the shared event: the dialog and chat
            ports complete decodes of their own on the same kind, so an event is not evidence that
            this string was answered.
            """

            from py4gw.game_thread.shared_block import DecodeState

            started = time.perf_counter()
            slot = begin_string_decode(encoded)
            owned.add(slot)
            placed = time.perf_counter()
            started_call = async_decode_str(encoded, slot)
            returned = time.perf_counter()

            finished = None
            deadline = time.time() + CLIENT_DECODE_DEADLINE_S
            while time.time() < deadline:
                if decode_state(slot) in (DecodeState.DONE, DecodeState.FAILED):
                    finished = time.perf_counter()
                    break
                time.sleep(0.005)

            text = ""
            if finished is not None:
                text, _ = decoded_text(slot)
            owned.discard(slot)
            emit(
                "client_decode",
                agent_id=agent_id,
                label=label,
                text=text,
                call_started=bool(started_call),
                state=states.pop(slot, decode_state(slot).name),
                place_ms=round((placed - started) * 1000, 3),
                call_ms=round((returned - placed) * 1000, 3),
                wait_ms=None if finished is None else round((finished - returned) * 1000, 3),
            )
            return text

        emit(
            "connected",
            string_table_loaded=bool(string_table._string_table_loaded),
            table_status=string_table._last_load_status,
        )
        _decode_preconditions(client)
        _slot_metadata(client)
        _map_context()

        own_agent = int(Player.GetAgentID())
        view = client.agent_array.get_context()
        agents = [int(agent_id) for agent_id in view.GetAgentArray()]
        emit("agents", total=len(agents), own_agent=own_agent)

        candidates: list[tuple[int, list[int]]] = []
        for agent_id in agents:
            if len(candidates) >= CANDIDATE_LIMIT:
                break
            if agent_id == own_agent:
                continue
            encoded = Agent.GetEncNameByID(agent_id)
            if not encoded or encoded[:2] == PLAYER_PREFIX:
                continue
            candidates.append((agent_id, encoded))
        emit("candidates", ids=[agent_id for agent_id, _ in candidates])
        if not candidates:
            emit("no_named_agent")
            return 2

        for agent_id, encoded in candidates:
            raw = bytes(encoded)
            record = client.agent_array.GetAgentByID(agent_id)
            emit(
                "agent",
                agent_id=agent_id,
                type=int(record.type) if record is not None else 0,
                is_gadget=bool(record.is_gadget_type) if record is not None else False,
                model_id=Agent.GetModelID(agent_id),
                position=Agent.GetXYZ(agent_id),
                name_bytes=list(raw),
                pointer=agent_module._get_agent_enc_name_by_id(agent_id),
            )

            client_text = client_decode(raw, "agent", agent_id)

            started = time.perf_counter()
            port_text = Agent.GetNameByID(agent_id)
            deadline = time.time() + PORT_DECODE_DEADLINE_S
            while not port_text and time.time() < deadline:
                time.sleep(0.02)
                port_text = Agent.GetNameByID(agent_id)
            port_ms = round((time.perf_counter() - started) * 1000, 3)

            emit(
                "compare",
                agent_id=agent_id,
                client_name=client_text,
                port_name=port_text,
                port_ms=port_ms,
                agree=bool(client_text) and client_text == port_text,
                table_status=string_table._last_load_status,
            )

            if record is not None and bool(record.is_gadget_type):
                _gadget_walk(client, agent_id)

        # The control: the client renders the local player's name on the nameplate, so its own
        # decoder must answer text for this string. An empty answer here is this side of the
        # boundary (the stub or the slot the host reads), not the client refusing a string.
        own_encoded = bytes(Agent.GetEncNameByID(own_agent) or [])
        own_client_text = client_decode(own_encoded, "player-control", own_agent)
        emit(
            "control",
            agent_id=own_agent,
            bytes=list(own_encoded),
            port_name=Agent.GetNameByID(own_agent),
            client_name=own_client_text,
            agree=bool(own_client_text) and own_client_text == Agent.GetNameByID(own_agent),
        )

        emit("done", compared=len(candidates))
        _viewer_table(client)
        emit("finished")
        return 0
    finally:
        py4gw.disconnect()
        emit("disconnected")


if __name__ == "__main__":
    raise SystemExit(main())
