"""Offline tests for `py4gw.gwa3.data_agent` -- GwAu3's `Agent_*` reads.

No client and no elevation. The accessor reads a *materialized* record: this project copies the
client's bytes into a `ctypes.Structure` with `from_buffer_copy`, so a test can fill a byte buffer
with known values, materialize the same structure over it, and assert what the accessor answers. That
is what makes the whole read side testable in the offline band, and it was established by probe before
this module was written.

The tests are grouped by what they are actually checking:

* the guard and sentinel behaviour GwAu3's contract is made of (`0` for nothing, `-2` and `-1`);
* every field key, read from a record built to a known value at the offset GwAu3 reads;
* the keys GwAu3 computes rather than reads, each against its own case;
* that the generated table matches GwAu3's own `Case` list, so a key cannot go missing quietly.
"""

from __future__ import annotations

import ctypes
import importlib.util
import re
import struct
import sys
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent

from py4gw.context.agent_array import AgentLivingStruct  # noqa: E402
from py4gw.gwa3 import data_agent  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "generate_gwa3_data_agent", HERE.parent / "tools" / "generate_gwa3_data_agent.py"
)
if _spec is None or _spec.loader is None:  # pragma: no cover - the file is in the tree
    raise RuntimeError("could not load tools/generate_gwa3_data_agent.py")
GENERATOR = importlib.util.module_from_spec(_spec)
sys.modules["generate_gwa3_data_agent"] = GENERATOR
_spec.loader.exec_module(GENERATOR)

RECORD_SIZE = 0x1C4


def build_record(**fields: object) -> AgentLivingStruct:
    """A record whose bytes hold the given values, materialized the way the project materializes one.

    ``fields`` are named GwAu3 keys (`X=1234.5`), resolved through the same table the accessor uses,
    so a test states a value in GwAu3's own vocabulary rather than in offsets.
    """

    buffer = (ctypes.c_uint8 * RECORD_SIZE)()
    for key, value in fields.items():
        case = _case_for(key)
        fmt = GENERATOR.WIDTHS[case.type_text.split("[")[0]]
        struct.pack_into(f"<{fmt}", buffer, case.offset, value)
    return AgentLivingStruct.from_buffer_copy(bytes(buffer))


def _case_for(key: str):
    for case in GENERATOR.parse_cases():
        if key in case.keys:
            return case
    raise KeyError(f"GwAu3 declares no key {key!r}")


class _PatchedAgent:
    """Serve one record to every `Agent_GetAgentPtr` call for the duration of a test.

    `AgentArray.GetAgentByID` is what would reach the client; replacing it is the seam that lets the
    accessor be driven with a record built here. `Agent.GetNameByID` is replaced for the same reason
    -- the `Name` key delegates to it and it reaches the connection -- and so are the two `Player`
    reads the sentinels use.
    """

    def __init__(self, record: AgentLivingStruct | None, my_id: int = 1, name: str = "Test Agent") -> None:
        self.record = record
        self.my_id = my_id
        self.name = name

    def __enter__(self) -> "_PatchedAgent":
        self._array = mock.patch.object(data_agent.AgentArray, "GetAgentByID", return_value=self.record)
        self._name = mock.patch.object(data_agent.Agent, "GetNameByID", return_value=self.name)
        self._player = mock.patch.object(data_agent.Player, "GetAgentID", return_value=self.my_id)
        self._target = mock.patch.object(data_agent.Player, "GetTargetID", return_value=77)
        self._array.start()
        self._name.start()
        self._player.start()
        self._target.start()
        return self

    def __exit__(self, *_: object) -> None:
        self._target.stop()
        self._player.stop()
        self._name.stop()
        self._array.stop()


class GuardTests(unittest.TestCase):
    """GwAu3's guard order and its id sentinels."""

    def test_an_empty_field_name_answers_zero(self) -> None:
        # `GwAu3_Data_Agent.au3:84` -- the guard before anything is read.
        with _PatchedAgent(build_record(ID=4242)):
            self.assertEqual(data_agent.Agent_GetAgentInfo(4242, ""), 0)

    def test_an_agent_the_client_does_not_hold_answers_zero(self) -> None:
        with _PatchedAgent(None):
            self.assertEqual(data_agent.Agent_GetAgentInfo(9999, "X"), 0)

    def test_an_unknown_field_name_answers_zero(self) -> None:
        # GwAu3's own `Case Else`.
        with _PatchedAgent(build_record(ID=4242)):
            self.assertEqual(data_agent.Agent_GetAgentInfo(4242, "NotAField"), 0)

    def test_the_me_sentinel_is_the_controlled_character(self) -> None:
        with _PatchedAgent(build_record(ID=4242, Level=20), my_id=4242):
            self.assertEqual(data_agent.Agent_GetMyID(), 4242)
            self.assertEqual(data_agent.Agent_ConvertID(-2), 4242)
            self.assertEqual(data_agent.Agent_GetAgentInfo(-2, "Level"), 20)

    def test_the_target_sentinel_is_the_current_target(self) -> None:
        with _PatchedAgent(build_record(ID=4242)):
            self.assertEqual(data_agent.Agent_GetCurrentTarget(), 77)
            self.assertEqual(data_agent.Agent_ConvertID(-1), 77)

    def test_a_plain_id_passes_through(self) -> None:
        with _PatchedAgent(build_record(ID=4242)):
            self.assertEqual(data_agent.Agent_ConvertID(4242), 4242)


class FieldKeyTests(unittest.TestCase):
    """Every key that reads one field, against a record holding a known value at GwAu3's offset.

    The value written is distinctive per key so a reader that resolves the wrong offset fails rather
    than coincidentally passing.
    """

    def test_named_attributes(self) -> None:
        record = build_record(
            ID=4242, Level=20, Allegiance=3, Type=0xDB, LoginNumber=7, PlayerNumber=11,
        )
        with _PatchedAgent(record):
            self.assertEqual(data_agent.Agent_GetAgentInfo(1, "ID"), 4242)
            self.assertEqual(data_agent.Agent_GetAgentInfo(1, "Level"), 20)
            self.assertEqual(data_agent.Agent_GetAgentInfo(1, "Allegiance"), 3)
            self.assertEqual(data_agent.Agent_GetAgentInfo(1, "Type"), 0xDB)
            self.assertEqual(data_agent.Agent_GetAgentInfo(1, "LoginNumber"), 7)
            self.assertEqual(data_agent.Agent_GetAgentInfo(1, "PlayerNumber"), 11)

    def test_nested_position_components(self) -> None:
        """`X`/`Y`/`Plane` are components of `pos`, and must answer numbers, not a structure."""

        with _PatchedAgent(build_record(X=1234.5, Y=-678.25, Plane=0)):
            self.assertAlmostEqual(data_agent.Agent_GetAgentInfo(1, "X"), 1234.5, places=3)
            self.assertAlmostEqual(data_agent.Agent_GetAgentInfo(1, "Y"), -678.25, places=3)
            self.assertEqual(data_agent.Agent_GetAgentInfo(1, "Plane"), 0)

    def test_nested_velocity_components(self) -> None:
        with _PatchedAgent(build_record(MoveX=2.5, MoveY=-1.5)):
            self.assertAlmostEqual(data_agent.Agent_GetAgentInfo(1, "MoveX"), 2.5, places=3)
            self.assertAlmostEqual(data_agent.Agent_GetAgentInfo(1, "MoveY"), -1.5, places=3)

    def test_nested_terrain_normal_components(self) -> None:
        with _PatchedAgent(build_record(TerrainNormalX=0.5, TerrainNormalY=0.25)):
            self.assertAlmostEqual(data_agent.Agent_GetAgentInfo(1, "TerrainNormalX"), 0.5, places=3)
            self.assertAlmostEqual(data_agent.Agent_GetAgentInfo(1, "TerrainNormalY"), 0.25, places=3)

    def test_floats_are_floats(self) -> None:
        with _PatchedAgent(build_record(HP=0.75, MaxHP=480, EnergyPercent=0.5, MaxEnergy=30)):
            self.assertAlmostEqual(data_agent.Agent_GetAgentInfo(1, "HP"), 0.75, places=3)
            self.assertEqual(data_agent.Agent_GetAgentInfo(1, "MaxHP"), 480)
            self.assertAlmostEqual(data_agent.Agent_GetAgentInfo(1, "EnergyPercent"), 0.5, places=3)
            self.assertEqual(data_agent.Agent_GetAgentInfo(1, "MaxEnergy"), 30)

    def test_every_table_key_answers(self) -> None:
        """No key in the generated table may raise for a resolvable record, except the refusals.

        `_UNIMPLEMENTED` names the keys this layer declines to answer, each with its reason; every
        other key must produce a value. A key that raised for an unstated reason would be a silent
        hole in the surface.
        """

        record = build_record(ID=1, Type=0xDB)
        refusing = set(data_agent._UNIMPLEMENTED)
        with _PatchedAgent(record):
            for key in sorted(data_agent._READERS):
                with self.subTest(key=key):
                    if key in refusing:
                        with self.assertRaises(NotImplementedError) as raised:
                            data_agent.Agent_GetAgentInfo(1, key)
                        # The refusal must say what it is about, not merely that it refused: every
                        # reason names both the GwAu3 line it follows and the project line it needs.
                        message = str(raised.exception)
                        self.assertIn("GwAu3_Data_Agent.au3", message)
                        self.assertIn("py4gw/", message)
                        continue
                    value = data_agent.Agent_GetAgentInfo(1, key)
                    self.assertIsNotNone(value, f"{key} answered None")

    def test_a_refusal_states_its_reason(self) -> None:
        with _PatchedAgent(build_record(ID=1)):
            with self.assertRaises(NotImplementedError) as raised:
                data_agent.Agent_GetAgentInfo(1, "HasVisibleEffects")
            message = str(raised.exception)
            self.assertIn("GwAu3_Data_Agent.au3:383-384", message)
            self.assertIn("py4gw/context/agent_array.py:935-948", message)


class ComputedKeyTests(unittest.TestCase):
    """The keys GwAu3 computes rather than reads, each against its own case."""

    def test_is_dead_reads_the_effect_word(self) -> None:
        # `GwAu3_Data_Agent.au3:308-309`: bit 0x0010 of the effect word.
        with _PatchedAgent(build_record(Effects=0x0010)):
            self.assertTrue(data_agent.Agent_GetAgentInfo(1, "IsDead"))
        with _PatchedAgent(build_record(Effects=0x0000)):
            self.assertFalse(data_agent.Agent_GetAgentInfo(1, "IsDead"))

    def test_is_bleeding_reads_a_different_bit(self) -> None:
        with _PatchedAgent(build_record(Effects=0x0001)):
            self.assertTrue(data_agent.Agent_GetAgentInfo(1, "IsBleeding"))
            self.assertFalse(data_agent.Agent_GetAgentInfo(1, "IsDead"))

    def test_is_crippled_needs_both_of_its_bits(self) -> None:
        """`GwAu3_Data_Agent.au3:307` is an equality against `0xA`, not a masked test.

        So `0x2` alone is not crippled, while `0xA` is -- the one key whose comparison differs from
        its neighbours, and the reason the table records it separately.
        """

        with _PatchedAgent(build_record(Effects=0x0002)):
            self.assertFalse(data_agent.Agent_GetAgentInfo(1, "IsCrippled"))
        with _PatchedAgent(build_record(Effects=0x000A)):
            self.assertTrue(data_agent.Agent_GetAgentInfo(1, "IsCrippled"))

    def test_type_word_booleans(self) -> None:
        with _PatchedAgent(build_record(Type=0xDB)):
            self.assertTrue(data_agent.Agent_GetAgentInfo(1, "IsLivingType"))
            self.assertFalse(data_agent.Agent_GetAgentInfo(1, "IsItemType"))
        with _PatchedAgent(build_record(Type=0x400)):
            self.assertTrue(data_agent.Agent_GetAgentInfo(1, "IsItemType"))

    def test_player_and_npc_are_the_login_number(self) -> None:
        with _PatchedAgent(build_record(LoginNumber=7)):
            self.assertTrue(data_agent.Agent_GetAgentInfo(1, "IsPlayer"))
            self.assertFalse(data_agent.Agent_GetAgentInfo(1, "IsNPC"))
        with _PatchedAgent(build_record(LoginNumber=0)):
            self.assertFalse(data_agent.Agent_GetAgentInfo(1, "IsPlayer"))
            self.assertTrue(data_agent.Agent_GetAgentInfo(1, "IsNPC"))

    def test_current_hp_is_the_fraction_times_the_maximum(self) -> None:
        with _PatchedAgent(build_record(HP=0.5, MaxHP=480)):
            self.assertAlmostEqual(data_agent.Agent_GetAgentInfo(1, "CurrentHP"), 240.0, places=3)

    def test_current_energy_is_the_fraction_times_the_maximum(self) -> None:
        with _PatchedAgent(build_record(EnergyPercent=0.5, MaxEnergy=30)):
            self.assertAlmostEqual(data_agent.Agent_GetAgentInfo(1, "CurrentEnergy"), 15.0, places=3)

    def test_is_moving_from_the_velocity_pair(self) -> None:
        with _PatchedAgent(build_record(MoveX=1.0, MoveY=0.0)):
            self.assertTrue(data_agent.Agent_GetAgentInfo(1, "IsMoving"))
        with _PatchedAgent(build_record(MoveX=0.0, MoveY=0.0, ModelState=12)):
            self.assertTrue(data_agent.Agent_GetAgentInfo(1, "IsMoving"))
        with _PatchedAgent(build_record(MoveX=0.0, MoveY=0.0, ModelState=0)):
            self.assertFalse(data_agent.Agent_GetAgentInfo(1, "IsMoving"))

    def test_can_pick_up_needs_the_item_type_and_an_owner(self) -> None:
        # `GwAu3_Data_Agent.au3:186-190`.
        with _PatchedAgent(build_record(Type=0x400, Owner=0), my_id=1):
            self.assertTrue(data_agent.Agent_GetAgentInfo(1, "CanPickUp"))
        with _PatchedAgent(build_record(Type=0x400, Owner=1), my_id=1):
            self.assertTrue(data_agent.Agent_GetAgentInfo(1, "CanPickUp"))
        with _PatchedAgent(build_record(Type=0x400, Owner=99), my_id=1):
            self.assertFalse(data_agent.Agent_GetAgentInfo(1, "CanPickUp"))
        with _PatchedAgent(build_record(Type=0xDB, Owner=0), my_id=1):
            self.assertFalse(data_agent.Agent_GetAgentInfo(1, "CanPickUp"))

    def test_has_bond_is_false_from_this_accessor(self) -> None:
        """This accessor takes no skill id, so no bond can match -- and the docstring says so."""

        with _PatchedAgent(build_record(ID=1)):
            self.assertFalse(data_agent.Agent_GetAgentInfo(1, "HasBond"))


class DistanceTests(unittest.TestCase):
    """GwAu3's own arithmetic over `X`/`Y`, which this project has no member for."""

    def test_distance_squared_between_two_agents(self) -> None:
        me = build_record(X=0.0, Y=0.0)
        with _PatchedAgent(me):
            with mock.patch.object(
                data_agent, "Agent_GetAgentInfo", side_effect=lambda _id, key: {"X": 0.0, "Y": 0.0}[key]
            ):
                self.assertEqual(data_agent.Agent_GetDistanceSq(1, 2), 0.0)

    def test_distance_is_the_square_root(self) -> None:
        # 3-4-5, so the arithmetic is checkable by eye rather than by re-running it.
        values: dict[tuple[int, str], float] = {
            (1, "X"): 0.0, (1, "Y"): 0.0, (2, "X"): 3.0, (2, "Y"): 4.0,
        }

        def fake(agent_id: int, key: str) -> float:
            return values[(agent_id, key)]

        with mock.patch.object(data_agent, "Agent_GetAgentInfo", side_effect=fake):
            self.assertAlmostEqual(data_agent.Agent_GetDistance(1, 2), 5.0, places=5)

    def test_distance_to_a_point(self) -> None:
        with mock.patch.object(
            data_agent, "Agent_GetAgentInfo", side_effect=lambda _id, key: {"X": 0.0, "Y": 0.0}[key]
        ):
            self.assertAlmostEqual(data_agent.Agent_GetDistanceToXY(3.0, 4.0), 5.0, places=5)


class TableIntegrityTests(unittest.TestCase):
    """The generated table against GwAu3's own `Case` list."""

    @staticmethod
    def declared_keys() -> set[str]:
        """Every key GwAu3's `Agent_GetAgentInfo` Switch accepts, read from the source independently.

        **Not** `GENERATOR.parse_cases()`, which is the thing under test: six of GwAu3's cases return
        without a `Memory_Read` and the parser cannot see them, so comparing the table against the
        parser's own output would miss exactly the keys most likely to be dropped.
        """

        text = GENERATOR.GWAU3_AGENT_SOURCE.read_text(encoding="utf-8", errors="replace")
        body = text.split("Func Agent_GetAgentInfo(", 1)[1].split("\nEndFunc", 1)[0]
        keys: set[str] = set()
        for line in body.splitlines():
            stripped = line.strip()
            if not stripped.startswith("Case ") or stripped.startswith("Case Else"):
                continue
            keys.update(re.findall(r'"([^"]+)"', stripped))
        return keys

    def test_the_source_really_declares_this_many_keys(self) -> None:
        """A floor on the source's own surface, so a parsing regression is visible as a number."""

        self.assertEqual(len(self.declared_keys()), 143)

    def test_the_parser_sees_all_but_the_six_non_field_cases(self) -> None:
        """The parser's known shortfall, pinned so it cannot grow quietly."""

        parsed = {key for case in GENERATOR.parse_cases() for key in case.keys}
        missing = sorted(self.declared_keys() - parsed)
        self.assertEqual(
            missing,
            ["BondCount", "EffectCount", "HasVisibleEffects", "VisibleEffectCount", "VisibleEffectsPtr", "vtable"],
        )

    def test_no_key_gwau3_declares_is_missing(self) -> None:
        """Every key GwAu3 accepts is in the table.

        This is the check that stops a key going missing when the generator is re-run -- and it caught
        one: `HasVisibleEffects` was hand-written, implemented, and then absent from the table, so the
        accessor answered `0` for it while the function that would have refused sat unreferenced.
        """

        missing = sorted(self.declared_keys() - set(data_agent._READERS))
        self.assertEqual(missing, [], f"{len(missing)} keys GwAu3 declares are not in the table")

    def test_no_key_the_table_carries_that_gwau3_does_not(self) -> None:
        """A table entry GwAu3 does not declare would be this project inventing a field name."""

        extra = sorted(set(data_agent._READERS) - self.declared_keys())
        self.assertEqual(extra, [], "these keys are in the table and not declared by GwAu3")

    def test_the_module_is_current(self) -> None:
        """The written module matches what the generator produces now."""

        expected = GENERATOR.render(GENERATOR.parse_cases())
        actual = (REPO_ROOT / "py4gw" / "gwa3" / "data_agent.py").read_text(encoding="utf-8")
        self.assertEqual(
            actual,
            expected,
            "py4gw/gwa3/data_agent.py is stale -- re-run tools/generate_gwa3_data_agent.py",
        )

    def test_the_hand_written_accessors_are_all_exported(self) -> None:
        for name in data_agent.__all__:
            with self.subTest(name=name):
                self.assertTrue(callable(getattr(data_agent, name, None)), f"{name} is not callable")


class ApplyFiltersTests(unittest.TestCase):
    """``_ApplyFilters`` -- the pipe-separated filter *string* (``GwAu3_Data_Agent.au3:1221-1243``).

    GwAu3 resolves each name with AutoIt's ``Call``, a lookup in the script's global function
    namespace; this port looks the name up in its own callable surface
    (``py4gw/gwa3/bridge.py``'s ``layer_surface``). The two answers that matter are the source's own,
    and both are checked here: a name that resolves is called with the agent, and a name that resolves
    to nothing answers ``False`` rather than raising -- which is what ``Call`` returns for an unknown
    function, ``0``, inverted by ``:1237-1238``.
    """

    def test_a_name_resolves_through_the_layers_own_surface(self) -> None:
        surface = {"UAI_Filter_IsGadget": lambda agent: agent == 7}
        with mock.patch("py4gw.gwa3.bridge.layer_surface", return_value=surface):
            self.assertTrue(data_agent._ApplyFilters(7, "UAI_Filter_IsGadget"))
            self.assertFalse(data_agent._ApplyFilters(8, "UAI_Filter_IsGadget"))

    def test_a_real_filter_name_reaches_the_real_predicate(self) -> None:
        from py4gw.gwa3 import uai_filter

        with mock.patch.object(uai_filter, "UAI_Filter_IsGadget", return_value=True) as predicate:
            self.assertTrue(data_agent._ApplyFilters(1, "UAI_Filter_IsGadget"))
        predicate.assert_called_once_with(1)

    def test_an_empty_filter_answers_true_before_anything_else(self) -> None:
        with mock.patch("py4gw.gwa3.bridge.layer_surface", side_effect=AssertionError("looked up")):
            self.assertTrue(data_agent._ApplyFilters(1, ""))

    def test_blanks_are_skipped(self) -> None:
        with mock.patch("py4gw.gwa3.bridge.layer_surface", return_value={}):
            self.assertTrue(data_agent._ApplyFilters(1, "   |  | "))

    def test_a_pipe_joined_list_must_pass_every_filter(self) -> None:
        surface = {"A": lambda agent: True, "B": lambda agent: False}
        with mock.patch("py4gw.gwa3.bridge.layer_surface", return_value=surface):
            self.assertTrue(data_agent._ApplyFilters(1, "A"))
            self.assertFalse(data_agent._ApplyFilters(1, "A|B"))

    def test_a_leading_minus_inverts_one_filter(self) -> None:
        surface = {"A": lambda agent: True, "B": lambda agent: False}
        with mock.patch("py4gw.gwa3.bridge.layer_surface", return_value=surface):
            self.assertFalse(data_agent._ApplyFilters(1, "-A"))
            self.assertTrue(data_agent._ApplyFilters(1, "-B"))

    def test_whitespace_around_a_name_is_stripped(self) -> None:
        surface = {"A": lambda agent: True, "B": lambda agent: False}
        with mock.patch("py4gw.gwa3.bridge.layer_surface", return_value=surface):
            self.assertTrue(data_agent._ApplyFilters(1, "  A  | -B  "))

    def test_a_name_that_resolves_to_nothing_answers_false(self) -> None:
        with mock.patch("py4gw.gwa3.bridge.layer_surface", return_value={}):
            self.assertFalse(data_agent._ApplyFilters(1, "NoSuchFilter"))

    def test_the_agent_is_passed_through_unchanged(self) -> None:
        seen: list[object] = []

        def record(agent: object) -> bool:
            seen.append(agent)
            return True

        with mock.patch("py4gw.gwa3.bridge.layer_surface", return_value={"A": record}):
            data_agent._ApplyFilters(4321, "A")
        self.assertEqual(seen, [4321])


class _FakeReader:
    """A stand-in for the record's bound remote reader: it answers bytes from a dictionary."""

    def __init__(self, answers: dict[tuple[int, int], bytes]) -> None:
        self.answers = answers
        self.asked: list[tuple[int, int]] = []

    def read(self, address: int, size: int) -> bytes:
        self.asked.append((address, size))
        return self.answers[(address, size)]


class RecordViewFallbackTests(unittest.TestCase):
    """A key whose record view does not declare the field answers **GwAu3's own bytes**.

    The second live finding (2026-10-10), and its regression test. The reader table is a ``Switch`` over
    living fields, and `Agent_GetAgentPtr` answers each agent's own view, so a gadget or an item record
    met a key its view does not declare -- and raised, where GwAu3 reads the bytes at its own offset and
    never consults the record's type.

    **And the first fix was wrong in a way only the client's own layout shows**: a gadget view is 0xE4
    bytes while GwAu3's ``Allegiance`` offset is 0x1B5, so reading the *record's* bytes at that offset
    cannot answer what GwAu3 answers -- measured in ``tests/live_reports/agent_view_sizes.log``. What
    answers it is the read GwAu3 makes, through the reader and address the record was materialized from,
    which is what these tests exercise with a stand-in for that reader.
    """

    def _bound(self, struct_type: Any, answers: dict[tuple[int, int], bytes], address: int = 0x10_0000) -> Any:
        record = struct_type.from_buffer_copy(bytes(ctypes.sizeof(struct_type)))
        record.bind_reader(_FakeReader(answers), address)
        return record

    def test_a_gadget_record_reads_gwau3s_offset_through_the_clients_reader(self) -> None:
        from py4gw.context.agent_array import AgentGadgetStruct

        offset, fmt = data_agent._RAW_READERS["Allegiance"]
        self.assertEqual(fmt, "<B")
        self.assertGreater(offset, ctypes.sizeof(AgentGadgetStruct), "the offset must be out of the view")

        record = self._bound(AgentGadgetStruct, {(0x10_0000 + offset, 1): bytes([194])})
        self.assertEqual(data_agent._READERS["Allegiance"](record), 194)
        self.assertEqual(record._remote_reader.asked, [(0x10_0000 + offset, 1)])

    def test_the_living_view_still_reads_its_named_field(self) -> None:
        from py4gw.context.agent_array import AgentLivingStruct

        offset, _ = data_agent._RAW_READERS["Allegiance"]
        buffer = bytearray(ctypes.sizeof(AgentLivingStruct))
        struct.pack_into("B", buffer, offset, 3)
        record = AgentLivingStruct.from_buffer_copy(bytes(buffer))
        self.assertEqual(data_agent._READERS["Allegiance"](record), 3)

    def test_the_hp_column_falls_back_to_the_same_float(self) -> None:
        from py4gw.context.agent_array import AgentGadgetStruct

        offset, fmt = data_agent._RAW_READERS["HP"]
        self.assertEqual(fmt, "<f")
        record = self._bound(
            AgentGadgetStruct, {(0x10_0000 + offset, 4): struct.pack("<f", 0.25)}
        )
        self.assertAlmostEqual(float(data_agent._READERS["HP"](record)), 0.25, places=6)

    def test_a_record_with_no_bound_reader_reads_its_own_bytes(self) -> None:
        """The offline route: no client behind the record, so the read is the record's own bytes."""

        from py4gw.context.agent_array import AgentGadgetStruct

        key = next(
            name
            for name, (offset, _) in data_agent._RAW_READERS.items()
            if name.startswith("h") and offset + 4 <= ctypes.sizeof(AgentGadgetStruct)
        )
        offset, fmt = data_agent._RAW_READERS[key]
        buffer = bytearray(ctypes.sizeof(AgentGadgetStruct))
        struct.pack_into(fmt, buffer, offset, 0x1234_5678)
        record = AgentGadgetStruct.from_buffer_copy(bytes(buffer))
        self.assertEqual(data_agent._READERS[key](record), 0x1234_5678)

    def test_the_mask_and_compare_keys_read_their_word_through_the_reader(self) -> None:
        from py4gw.context.agent_array import AgentGadgetStruct

        offset, fmt = data_agent._RAW_READERS["IsDead"]
        self.assertEqual(fmt, "<I")
        record = self._bound(AgentGadgetStruct, {(0x10_0000 + offset, 4): struct.pack("<I", 0)})
        self.assertIsInstance(data_agent._READERS["IsDead"](record), bool)

    def test_every_key_the_filters_read_has_a_raw_reader_behind_it(self) -> None:
        """The keys `uai_filter`'s predicates ask for, and each one a fallback for a non-living view."""

        for key in ("Allegiance", "HP", "IsDead", "Primary", "Secondary", "LoginNumber", "TypeMap",
                    "ModelState", "Effects", "WeaponType", "Skill", "Level"):
            with self.subTest(key=key):
                self.assertIn(key, data_agent._RAW_READERS)


if __name__ == "__main__":
    unittest.main()
