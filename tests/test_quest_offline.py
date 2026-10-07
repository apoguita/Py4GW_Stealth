"""Offline checks for the ported ``Quest`` class and the ``PyQuest`` binding behind it.

Two things are pinned here, both against the **sources** rather than against this port's own
behaviour:

* **the class**, name for name, order for order, argument list for argument list, against
  ``Py4GWCoreLib/Quest.py`` — read from the checkout, not quoted; and
* **the binding's behaviour**, from ``quest_bindings.cpp`` / ``quest_methods.cpp`` / ``quest.cpp``:
  the ``< 0`` refusals, the guards that come *before* any call, the two quest-changing members'
  call into the client's own functions (and the absence of the UI message the hook sends), the
  mission-map constants for a negative id, and the two calls ``request_quest_info`` makes in the
  source's own order.
"""

from __future__ import annotations

import ast
import inspect
import re
import ctypes
import unittest
from pathlib import Path
from unittest import mock

from py4gw.native_src.quest import py_quest
from py4gw.native_src.quest.py_quest import PyQuest, QuestData
from py4gw.quest import Quest

SOURCE = Path(r"C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib\Quest.py")
NATIVE = Path(r"C:\Users\Apo\Py4GW_Reforged_Native")


def _class_members(path: Path, name: str) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == name:
            return [
                member.name
                for member in node.body
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
    return []


def _class_signatures(path: Path, name: str) -> dict[str, list[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == name:
            return {
                member.name: [argument.arg for argument in member.args.args]
                for member in node.body
                if isinstance(member, ast.FunctionDef)
            }
    return {}


class QuestSurfaceParityTests(unittest.TestCase):
    """The class is the source's, member for member."""

    def setUp(self) -> None:
        if not SOURCE.is_file():
            self.skipTest(f"no Reforged checkout at {SOURCE}")

    def test_every_member_is_present_in_the_sources_order(self) -> None:
        source = _class_members(SOURCE, "Quest")
        port = _class_members(Path(__file__).resolve().parents[1] / "py4gw" / "quest.py", "Quest")
        self.assertEqual(source, port, "the port declares the source's members in the source's order")
        self.assertEqual(len(source), 26)

    def test_every_argument_list_is_the_sources(self) -> None:
        source = _class_signatures(SOURCE, "Quest")
        port = _class_signatures(Path(__file__).resolve().parents[1] / "py4gw" / "quest.py", "Quest")
        self.assertEqual(source, port)

    def test_every_member_delegates_to_the_binding(self) -> None:
        """``Quest.py`` is a delegation surface: each body is one ``quest_instance()`` call."""

        tree = ast.parse((Path(__file__).resolve().parents[1] / "py4gw" / "quest.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "Quest":
                for member in node.body:
                    if not isinstance(member, ast.FunctionDef) or member.name == "quest_instance":
                        continue
                    with self.subTest(member=member.name):
                        body = ast.unparse(member)
                        self.assertIn("Quest.quest_instance()", body)

    def test_the_binding_is_the_source_module_surface(self) -> None:
        """The native binding's surface and this port's are the same list, **both ways**.

        The names are read out of ``quest_bindings.cpp`` rather than out of this port, so a member the
        binding has and the port lacks fails here — and so does a member the port has that the binding
        does not, which is the direction that catches an invented helper. Measured 2026-10-05: 25
        ``.def_static`` names and 24 module-level ``m.def`` names, matching exactly.
        """

        binding = NATIVE / "src" / "GW" / "quest" / "quest_bindings.cpp"
        if not binding.is_file():
            self.skipTest(f"no Native checkout at {binding}")
        text = binding.read_text(encoding="utf-8")
        registered_statics = re.findall(r'\.def_static\("([a-z_]+)"', text)
        registered_module = re.findall(r'^\s+m\.def\("([a-z_]+)"', text, re.MULTILINE)
        self.assertEqual(len(registered_statics), 25, "the binding's static surface was read")
        self.assertEqual(len(registered_module), 24, "and its module surface")

        port_statics = {name for name in dir(PyQuest) if not name.startswith("_")}
        self.assertEqual(
            sorted(registered_statics),
            sorted(port_statics),
            "PyQuest carries the binding's statics and nothing else",
        )
        port_functions = {
            name for name, value in inspect.getmembers(py_quest, inspect.isfunction)
            if not name.startswith("_") and value.__module__ == py_quest.__name__
        }
        self.assertEqual(
            sorted(registered_module),
            sorted(port_functions),
            "and the module level carries the binding's free functions and nothing else",
        )
        self.assertEqual(
            [name for name in ("QuestData", "PyQuest") if hasattr(py_quest, name)],
            ["QuestData", "PyQuest"],
            "the binding's two classes exist here under the same names",
        )

    def test_quest_data_is_the_bindings_sixteen_fields(self) -> None:
        """``quest_bindings.cpp:272-289`` — the record the binding hands back."""

        data = QuestData()
        self.assertEqual(
            [
                "quest_id",
                "log_state",
                "location",
                "name",
                "npc",
                "map_from",
                "marker_x",
                "marker_y",
                "h0024",
                "map_to",
                "description",
                "objectives",
                "is_completed",
                "is_current_mission_quest",
                "is_area_primary",
                "is_primary",
            ],
            list(QuestData.__dataclass_fields__),
        )
        self.assertEqual(data.quest_id, 0)
        self.assertIs(data.is_completed, False)


class _Marker:
    """The record's ``GamePos``: three floats the source copies straight across."""

    def __init__(self, x: float = 1.5, y: float = -2.5, zplane: int = 0) -> None:
        self.x = x
        self.y = y
        self.zplane = zplane


class _Objective:
    """A stand-in mission objective: the encoded string and its ``type`` word."""

    def __init__(self, encoded: str, objective_type: int = 0) -> None:
        self.enc_str_encoded_str = encoded
        self.enc_str = "".join(
            character if 32 <= ord(character) <= 126 else "\\x%04X" % ord(character)
            for character in encoded
        )
        self.type = objective_type


class _Record:
    """A stand-in quest-log record with the fields the port reads, and the bit properties."""

    def __init__(self, quest_id: int, log_state: int, name: str = "Q\x01\x02", location: str = "Loc") -> None:
        self.quest_id = quest_id
        self.log_state = log_state
        self.map_from = 11
        self.map_to = 12
        self.h0024 = 0
        self.marker_ptr = _Marker()
        self.name_encoded_str = name
        self.description_encoded_str = "D\x01"
        self.objectives_encoded_str = "O\x01"
        self.location_encoded_str = location
        self.npc_encoded_str = "N\x01"

    @property
    def marker(self):
        """The port's own property: ``None`` when a component is not finite (so a port that copies
        through it instead of the raw fields is caught)."""

        values = (self.marker_ptr.x, self.marker_ptr.y, self.marker_ptr.zplane)
        if not all(value == value and abs(value) != float("inf") for value in values):
            return None
        return self.marker_ptr

    @property
    def is_completed(self) -> bool:
        return bool(self.log_state & 0x2)

    @property
    def is_current_mission_quest(self) -> bool:
        return bool(self.log_state & 0x10)

    @property
    def is_primary(self) -> bool:
        return bool(self.log_state & 0x20)

    @property
    def is_area_primary(self) -> bool:
        return bool(self.log_state & 0x40)


class _World:
    def __init__(self, records: list[_Record], objectives: list[object] | None = None, active: int = 0) -> None:
        self.quests = records
        self.active_quest_id = active
        self.mission_objectives = objectives or []


class _Client:
    def __init__(self, world: _World | None, resolved: tuple[str, ...] = ()) -> None:
        self._world = world
        self._resolved = set(resolved)
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def read_world_context(self) -> _World | None:
        return self._world

    def resolves(self, name: str) -> bool:
        return name in self._resolved

    def call_function(self, name: str, form: object, *args: object) -> None:
        self.calls.append((name, args))


class _Patch:
    """Run a member against a stand-in client, with the binding's module helpers left alone."""

    def __init__(self, client: _Client) -> None:
        self.client = client

    def __enter__(self) -> _Client:
        self._client = mock.patch.object(py_quest, "_client", lambda: self.client)
        self._client.start()
        return self.client

    def __exit__(self, *exc: object) -> None:
        self._client.stop()


class QuestBindingBehaviourTests(unittest.TestCase):
    """The binding's own refusals, guards and calls, from the native source lines."""

    def test_negative_ids_are_refused_before_anything_else(self) -> None:
        """``quest_bindings.cpp:294, 305, 312, 317, 358`` — ``< 0`` first, in that order."""

        client = _Client(None, resolved=("quest.set_active_quest_func", "quest.abandon_quest_func"))
        with _Patch(client):
            self.assertFalse(PyQuest.set_active_quest_id(-1))
            self.assertFalse(PyQuest.abandon_quest_id(-1))
            self.assertFalse(PyQuest.is_quest_completed(-1))
            self.assertFalse(PyQuest.is_quest_primary(-1))
            self.assertFalse(PyQuest.request_quest_info(-1))
        self.assertEqual(client.calls, [], "nothing is called for a negative id")

    def test_a_quest_outside_the_log_stops_the_call_but_not_the_answer(self) -> None:
        """``quest_methods.cpp:21, 39, 108`` guard the *call*; the binding's answer is the enqueue's.

        ``quest_bindings.cpp:295-298`` returns ``true`` for any id that is not negative — the guards
        run inside the enqueued lambda — so a quest outside the log answers ``true`` while the client
        is never told. Answering the guards' outcome instead is what an earlier version of this port
        did, so both halves are pinned here.
        """

        client = _Client(
            _World([_Record(7, 0)]),
            resolved=(
                "quest.set_active_quest_func",
                "quest.abandon_quest_func",
                "quest.request_quest_info_func",
                "quest.request_quest_data_func",
            ),
        )
        sent: list[tuple[int, int, int]] = []
        with _Patch(client), mock.patch(
            "py4gw.ui_manager.UIManager.SendUIMessageRaw",
            staticmethod(lambda msgid, wparam, lparam=0, skip_hooks=False: sent.append((msgid, wparam, lparam)) or True),
        ):
            self.assertTrue(PyQuest.set_active_quest_id(9), "the binding answers true")
            self.assertTrue(PyQuest.abandon_quest_id(9), "and here")
            self.assertTrue(PyQuest.request_quest_info(9), "and here")
        self.assertEqual(sent, [], "the client was never told")
        self.assertEqual(client.calls, [], "and no function was called")

    def test_a_missing_resolver_stops_the_call_but_not_the_answer(self) -> None:
        """Nothing resolves, nothing is called — and still ``true``, as the source answers it."""

        client = _Client(_World([_Record(7, 0)]))
        sent: list[tuple[int, int, int]] = []
        with _Patch(client), mock.patch(
            "py4gw.ui_manager.UIManager.SendUIMessageRaw",
            staticmethod(lambda msgid, wparam, lparam=0, skip_hooks=False: sent.append((msgid, wparam, lparam)) or True),
        ):
            self.assertTrue(PyQuest.set_active_quest_id(7))
            self.assertTrue(PyQuest.abandon_quest_id(7))
            self.assertTrue(PyQuest.request_quest_info(7))
        self.assertEqual(sent, [])
        self.assertEqual(client.calls, [])

    def test_setting_and_abandoning_call_the_clients_own_functions(self) -> None:
        """``quest_methods.cpp:20-26, 38-46`` — the call, and **no** UI message of this port's own.

        Native's hook body sends ``kSendSetActiveQuest`` / ``kSendAbandonQuest``, and an earlier
        version of this port sent those messages itself instead of calling. A live run on
        2026-10-06 settled it: the message left the active quest at 1098 for a full 12 s, while
        ``set_active_quest_func(167)`` moved it immediately. So the port calls — which is also what
        the source's inner layer does — and this test pins both halves: the call happens, and no
        message is sent. A message appearing here again is the regression this pins.
        """

        client = _Client(
            _World([_Record(7, 0x2)]),
            resolved=("quest.set_active_quest_func", "quest.abandon_quest_func"),
        )
        sent: list[tuple[int, int, int]] = []
        with _Patch(client), mock.patch(
            "py4gw.ui_manager.UIManager.SendUIMessageRaw",
            staticmethod(lambda msgid, wparam, lparam=0, skip_hooks=False: sent.append((msgid, wparam, lparam)) or True),
        ):
            self.assertTrue(PyQuest.set_active_quest_id(7))
            self.assertTrue(PyQuest.abandon_quest_id(7))
        self.assertEqual(
            client.calls,
            [
                ("quest.set_active_quest_func", (7,)),
                ("quest.abandon_quest_func", (7,)),
            ],
        )
        self.assertEqual(sent, [], "the port calls the client's function; it does not send the hook's message")

    def test_request_quest_info_calls_both_functions_in_the_sources_order(self) -> None:
        """``quest_methods.cpp:113-114`` — the info call, then the data call with its flag."""

        client = _Client(
            _World([_Record(7, 0)]),
            resolved=("quest.request_quest_info_func", "quest.request_quest_data_func"),
        )
        with _Patch(client):
            self.assertTrue(PyQuest.request_quest_info(7, True))
        self.assertEqual(
            client.calls,
            [
                ("quest.request_quest_info_func", (7,)),
                ("quest.request_quest_data_func", (7, 1)),
            ],
        )

    def test_the_log_walk_answers_the_sources_fields(self) -> None:
        """``quest_bindings.cpp:336-356`` — ids, and the lighter per-entry copy."""

        client = _Client(_World([_Record(4, 0x2), _Record(9, 0x22)]))
        with _Patch(client):
            self.assertEqual(PyQuest.get_quest_log_ids(), [4, 9])
            entries = PyQuest.get_quest_log()
            self.assertEqual([entry.quest_id for entry in entries], [4, 9])
            self.assertEqual(entries[1].log_state, 0x22)
            self.assertEqual(entries[1].marker_x, 1.5)
            self.assertEqual(entries[1].marker_y, -2.5)
            self.assertEqual(entries[1].name, "", "the log copy leaves the strings empty")
            self.assertFalse(entries[1].is_completed, "and the bit flags too")

    def test_the_bits_are_the_records_own(self) -> None:
        """``include/GW/context/quest.h:28-32`` — 0x2 completed, 0x20 primary."""

        client = _Client(_World([_Record(4, 0x22)]))
        with _Patch(client):
            self.assertTrue(PyQuest.is_quest_completed(4))
            self.assertTrue(PyQuest.is_quest_primary(4))
            self.assertFalse(PyQuest.is_quest_completed(5), "an id outside the log answers False")

    def test_get_quest_data_fills_the_numeric_and_bit_fields_only(self) -> None:
        """``quest_bindings.cpp:321-335`` — seven fields copied, three left at their defaults.

        The record here carries ``log_state = 0x42``, so it *is* an area-primary quest; the returned
        ``QuestData`` still says otherwise, because the source copies neither that bit nor
        ``is_current_mission_quest`` nor ``h0024``. Copying them would be a plausible-looking wrong
        answer, which is why it is pinned.
        """

        client = _Client(_World([_Record(4, 0x42)]))
        with _Patch(client):
            data = PyQuest.get_quest_data(4)
        self.assertEqual((data.quest_id, data.map_from, data.map_to), (4, 11, 12))
        self.assertEqual(data.log_state, 0x42)
        self.assertTrue(data.is_completed)
        self.assertFalse(data.is_primary)
        self.assertEqual(data.name, "")
        self.assertEqual(data.description, "")
        self.assertEqual(data.h0024, 0, "the source does not copy h0024")
        self.assertFalse(data.is_current_mission_quest, "nor this bit")
        self.assertFalse(data.is_area_primary, "even though the record carries it")

    def test_the_marker_is_copied_raw_with_no_guard_of_ours(self) -> None:
        """``quest_bindings.cpp:329-330`` — ``d.marker_x = q->marker.x``, whatever the record holds.

        The record type has a ``marker`` property that answers ``None`` for a non-finite one, and an
        earlier version of this port went through it and wrote ``0.0`` — a guard the source does not
        make. The source copies the two floats as they stand, so this does too.
        """

        record = _Record(4, 0)
        record.marker_ptr.x = float("inf")
        record.marker_ptr.y = float("-inf")
        client = _Client(_World([record]))
        with _Patch(client):
            data = PyQuest.get_quest_data(4)
            entry = PyQuest.get_quest_log()[0]
        self.assertEqual(data.marker_x, float("inf"))
        self.assertEqual(data.marker_y, float("-inf"))
        self.assertEqual(entry.marker_x, float("inf"), "the log copy reads the same two floats")

    def test_the_mission_objectives_hand_the_client_the_raw_string(self) -> None:
        """``quest_bindings.cpp:210-212`` — ``AsyncDecodeAnyEncStr(obj.enc_str, ...)``, the raw text.

        ``MissionObjectiveStruct.enc_str`` in this port is the *printable rendering* (``\\xNNNN``
        escapes) while ``enc_str_encoded_str`` is the string as the client holds it; handing the
        decoder the rendering would give it back an escaped copy of its own work.
        """

        raw = "\x0a\x01"
        objective = _Objective(raw)
        client = _Client(_World([], objectives=[objective]))
        seen: list[bytes] = []
        with _Patch(client), \
            mock.patch("py4gw.ui.async_decode.begin_string_decode", lambda encoded: seen.append(encoded) or 7), \
            mock.patch("py4gw.ui.async_decode.async_decode_str", lambda encoded, slot: True), \
            mock.patch("py4gw.ui.async_decode.decode_state", lambda slot: py_quest.DecodeState.DONE), \
            mock.patch("py4gw.ui.async_decode.decoded_text", lambda slot: ("OBJ", True)):
            PyQuest.request_quest_objectives(-1)
        self.assertEqual(seen, [raw.encode("utf-16-le") + b"\x00\x00"], "the raw string, terminator included")
        self.assertEqual(PyQuest.get_quest_objectives(-1), "OBJ\n", "one line, with the source's newline")

    def test_a_negative_id_answers_the_bindings_mission_constants(self) -> None:
        """``quest_bindings.cpp:115-151`` — the name and the description constants."""

        for available, expected_name, expected_description in (
            (True, "Mission Objectives", "Mission Ongoing"),
            (False, "No Active Mission", "No Active Mission"),
        ):
            objectives = [object()] if available else []
            client = _Client(_World([], objectives=objectives))
            with self.subTest(available=available), _Patch(client):
                PyQuest.request_quest_name(-1)
                self.assertTrue(PyQuest.is_quest_name_ready(-1))
                self.assertEqual(PyQuest.get_quest_name(-1), expected_name)
                PyQuest.request_quest_description(-1)
                self.assertEqual(PyQuest.get_quest_description(-1), expected_description)

    def test_an_id_outside_the_log_has_no_ready_value(self) -> None:
        """The store is left unready when the record is not there, so ``get`` answers ``""``."""

        client = _Client(_World([]))
        with _Patch(client):
            PyQuest.request_quest_name(1234)
            self.assertFalse(PyQuest.is_quest_name_ready(1234))
            self.assertEqual(PyQuest.get_quest_name(1234), "")

    def test_a_decode_the_client_never_answers_times_out_the_sources_way(self) -> None:
        """``quest_bindings.cpp:100-108`` — 1000 ms, then ``"Timeout"`` with the entry made ready.

        The slot also goes back to the pool, which is this side's own bookkeeping: a slot left in
        flight is one the next request cannot have.
        """

        client = _Client(_World([_Record(7, 0)]))
        released: list[int] = []
        with _Patch(client), \
            mock.patch("py4gw.ui.async_decode.begin_string_decode", lambda encoded: 42), \
            mock.patch("py4gw.ui.async_decode.async_decode_str", lambda encoded, slot: True), \
            mock.patch("py4gw.ui.async_decode.decode_state", lambda slot: py_quest.DecodeState.IN_FLIGHT), \
            mock.patch.object(py_quest, "_release", lambda slot: released.append(slot)), \
            mock.patch.object(py_quest, "time") as clock:
            # ``_start`` reads the clock once, then each ``_collect`` reads it: the request's own
            # moment, a poll inside the bound, and a poll at it.
            clock.monotonic.side_effect = [100.0, 100.0, 100.0 + py_quest.DECODE_TIMEOUT_SECONDS]
            PyQuest.request_quest_name(7)
            self.assertFalse(PyQuest.is_quest_name_ready(7), "not ready before the bound")
            self.assertTrue(PyQuest.is_quest_name_ready(7), "ready at the bound")
            self.assertEqual(PyQuest.get_quest_name(7), "Timeout")
        self.assertEqual(released, [42], "the slot is given back")
        self.assertEqual(py_quest.DECODE_TIMEOUT_SECONDS, 1.0, "the source's own 1000 ms")


class QuestRecordLayoutTests(unittest.TestCase):
    """The record this port reads is the one the sources declare."""

    def test_the_record_is_the_native_thirty_four_bytes(self) -> None:
        from py4gw.context.world_context import QuestStruct

        self.assertEqual(ctypes.sizeof(QuestStruct), 0x34)
        self.assertEqual(QuestStruct.quest_id.offset, 0x00)
        self.assertEqual(QuestStruct.log_state.offset, 0x04)
        self.assertEqual(QuestStruct.map_from.offset, 0x14)
        self.assertEqual(QuestStruct.map_to.offset, 0x28)

    def test_the_entry_group_switch_is_the_sources(self) -> None:
        """``quest_methods.cpp:79-91`` — 0x20, 0x40, 0x00 answer; 0x10 and anything else do not."""

        for log_state, expected_nonempty in ((0x20, True), (0x40, True), (0x00, True), (0x10, False), (0x80, False)):
            record = _Record(3, log_state)
            client = _Client(_World([record]))
            with self.subTest(log_state=hex(log_state)), _Patch(client):
                answer = py_quest.get_quest_entry_group_name(3)
                self.assertEqual(bool(answer), expected_nonempty)
                self.assertTrue(all(ord(char) < 128 for char in answer), "narrowed to '?' as the binding does")


if __name__ == "__main__":
    unittest.main(verbosity=2)
