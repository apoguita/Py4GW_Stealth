"""Offline tests for the ported ``Agent`` class (``py4gw/agent.py``).

Two things are pinned here, and neither needs a client.

**The surface is the source's.** The 148 member names are read out of Reforged's own
``Py4GWCoreLib/Agent.py`` at test time — not copied into this file — and compared with what the
port declares, in the source's order, so a member that is dropped, renamed or added fails here.
The two class constants and the ``RequestName`` alias are pinned the same way.

**The values are the source's.** Every member the port implements is driven against a synthetic
agent record and checked against what the source's body returns for that record, and again against
the source's default for an agent that does not exist. The records are real instances of the ported
``ctypes`` structures, so the field offsets, widths and derived properties are exercised too; the
only thing standing in for the client is a two-method object, injected where
``py4gw.client.require_client`` looks.

The members that raise are pinned as well: each names itself and what it still needs, the set of
raising members is compared against the class's own ``ast`` (13 of 148 — eight direct, four
transitive and the ``RequestName`` alias), and every member's docstring reference is checked against
the real range of that member in the source, so a drifted reference fails here too.
"""

from __future__ import annotations

import ast
import ctypes
import inspect
import re
import unittest
from pathlib import Path
from typing import Any, cast
from unittest import mock

from py4gw import agent as agent_module
from py4gw.agent import Agent
from py4gw.context.acc_agent_context import (
    AccAgentContextStruct,
    AgentMovementStruct,
    AgentSummaryInfoStruct,
    AgentSummaryInfoSubStruct,
)
from py4gw.context.agent_array import (
    AgentGadgetStruct,
    AgentItemStruct,
    AgentLivingStruct,
    AgentStruct,
    AgentType,
    TagInfoStruct,
)
from py4gw.context.gadget_context import GadgetContextStruct, GadgetInfoStruct
from py4gw.context.gw_array import GWArray
from py4gw.context.item_context import ItemContextStruct, ItemStruct
from py4gw.context.world_context import (
    AgentNameInfoStruct,
    AttributeStruct,
    NPC_ModelStruct,
    PlayerStruct,
    WorldContextStruct,
)
#: Reforged's own file. It is the specification for the surface, so it is read rather than quoted.
SOURCE = Path(r"C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib\Agent.py")

#: An agent id for the members that take one.
ID = 7

#: Every value below is chosen to be exactly representable in ``float32``, so the 32-bit record
#: fields round-trip and the assertions can be equalities rather than tolerances.
LIVING = {
    "timer": 12_500,
    "z": 4.5,
    "width1": 1.5, "height1": 2.5,
    "width2": 3.5, "height2": 4.5,
    "width3": 5.5, "height3": 6.5,
    "rotation_angle": 0.25, "rotation_cos": 0.5, "rotation_sin": 0.75,
    "name_properties": 0x1234,
    "visual_effects": 0x77,
    "ground": 7,
    "hp": 480.0, "max_hp": 480, "hp_pips": 3.5,
    "energy": 25.5, "max_energy": 30, "energy_regen": 0.75,
    "level": 20, "primary": 5, "secondary": 6,
    "player_number": 3, "login_number": 0,
    "owner": 42, "team_id": 1,
    "agent_model_type": 0x1234, "transmog_npc_id": 77,
    "weapon_type": 2, "weapon_item_type": 3, "offhand_item_type": 4,
    "weapon_item_id": 11, "offhand_item_id": 12,
    "dagger_status": 1,
    "animation_type": 1.5, "animation_code": 44, "animation_id": 22, "animation_speed": 0.5,
    "weapon_attack_speed": 1.75, "attack_speed_modifier": 0.5,
    "skill": 1234, "effects": 0, "type_map": 0, "model_state": 0,
    "h0128": 5,
    "allegiance": 4,
}


class _FakeReader:
    """A reader that answers the one read the tag property makes.

    The ported records carry their reader (``AgentArray._read_record`` binds it,
    ``agent_array.py:2580-2587``), which is what makes ``living.tags`` a record or ``None`` — the
    shape the source's member expects — instead of the port's unbound refusal.
    """

    def __init__(self, tags: TagInfoStruct | None = None, tag_address: int = 0x100000) -> None:
        self.tags = tags
        self.tag_address = tag_address

    def read(self, address: int, size: int) -> bytes:
        if self.tags is not None and address == self.tag_address:
            return bytes(self.tags)[:size]
        return bytes(size)


class MemoryFixtureReader:
    """Serve fixed byte ranges as a small deterministic remote reader."""

    def __init__(self) -> None:
        self._ranges: dict[int, bytes] = {}

    def add(self, address: int, value: bytes) -> None:
        self._ranges[address] = value

    def read(self, address: int, size: int) -> bytes:
        for start, value in self._ranges.items():
            end = start + len(value)
            if start <= address and address + size <= end:
                offset = address - start
                return value[offset : offset + size]
        raise OSError(299, f"unmapped fixture read at 0x{address:08X}")


class _FakeClient:
    """The reads the ported members make, standing in for a connection.

    ``Agent.GetAgentByID`` goes the source's chain — ``AgentArray.GetAgentByID`` and then the
    agent-array *context view* (``AgentContext.py:1476-1497``) — so the fake connection offers the
    facade and the view it hands out, which is the source's own route.
    """

    def __init__(
        self,
        agent: Any = None,
        world: Any = None,
        agent_ids: tuple[int, ...] = (),
        refusal: Exception | None = None,
    ) -> None:
        self.agent = agent
        self.world = world
        self.agent_ids = agent_ids
        self.refusal = refusal

    @property
    def agent_array(self) -> "_FakeAgentArrayFacade":
        return _FakeAgentArrayFacade(self)

    def read_world_context(self) -> Any:
        return self.world

    def read_skill(self, skill_id: int) -> Any:
        """``Skill.GetID``'s lookup (``skill.py:210``).

        The name table answers the id, so the record is not needed — the source's own
        ``GetContext`` returns early on a missing record, and this fake has none.
        """

        return None


class _FakeAgentArrayFacade:
    """The client's array facade: the address the resolver answered, and the view.

    Two readers use it, and they are different members: Reforged's Python ``Agent.GetAgentByID``
    asks ``get_context()`` for the view, while the ported binding's own lookup — native's
    ``GW::agent::GetAgentByID`` — reads the array the address names, so it asks for the address
    first (``AgentContext.py:1403-1408``).
    """

    def __init__(self, client: Any) -> None:
        self._client = client

    def get_context(self) -> "_FakeAgentArrayView":
        return _FakeAgentArrayView(self._client)

    def get_ptr(self) -> int:
        return int(getattr(self._client, "array_address", 0) or 0)

    def initialize(self) -> int:
        return self.get_ptr()


class _FakeAgentArrayView:
    """The context view: the record lookups the ported members make."""

    def __init__(self, client: Any) -> None:
        self._client = client

    def GetAgentByID(self, agent_id: int) -> Any:
        if self._client.refusal is not None:
            raise self._client.refusal
        return self._client.agent

    def GetAgentArray(self) -> list[int]:
        return list(self._client.agent_ids)


class _FakeWorld:
    """A world context with the reads the ported members make."""

    def __init__(
        self,
        attributes: list[AttributeStruct] | None = None,
        npc_models: list[NPC_ModelStruct] | None = None,
        party_effects: list[Any] | None = None,
    ) -> None:
        self._attributes = attributes or []
        self._npc_models = npc_models or []
        self._party_effects = party_effects or []

    def get_attributes_by_agent_id(self, agent_id: int) -> list[AttributeStruct]:
        return self._attributes

    @property
    def npc_models(self) -> list[NPC_ModelStruct] | None:
        return self._npc_models

    @property
    def party_effects(self) -> list[Any]:
        """The effects blocks ``Effects`` walks (``effects_methods.cpp:29-41``)."""

        return self._party_effects


def _living_record() -> AgentLivingStruct:
    """One living agent record with every field the ported members read."""

    record = AgentLivingStruct()
    record.type = int(AgentType.LIVING)
    for name, value in LIVING.items():
        setattr(record, name, value)
    record.pos.x = 1.5
    record.pos.y = -2.5
    record.pos.zplane = 9
    record.name_tag_x = 0.25
    record.name_tag_y = 0.5
    record.name_tag_z = 0.75
    record.terrain_normal.x = 0.125
    record.terrain_normal.y = 0.25
    record.terrain_normal.z = 1.0
    record.velocity.x = 0.25
    record.velocity.y = -0.5
    return record


def _item_record() -> AgentItemStruct:
    """One item agent record.

    It carries its own ``agent_id``, as a record in the client's table does — native's
    ``GetAgentByID`` checks the movement entry for exactly that id, so a record without one is a
    record that lookup answers null for.
    """

    record = AgentItemStruct()
    record.type = int(AgentType.ITEM)
    record.agent_id = ID
    record.owner = 1234
    record.item_id = 5678
    record.extra_type = 3
    record.h00CC = 0x0C
    return record


def _gadget_record() -> AgentGadgetStruct:
    """One gadget agent record."""

    record = AgentGadgetStruct()
    record.type = int(AgentType.GADGET)
    record.gadget_id = 4242
    record.agent_id = ID
    record.extra_type = 5
    record.h00C4 = 0xC4
    record.h00C8 = 0xC8
    record.h00D4[0] = 1
    record.h00D4[1] = 2
    record.h00D4[2] = 3
    record.h00D4[3] = 4
    return record


class AgentSurfaceTests(unittest.TestCase):
    """The port declares the source's surface, in the source's order, and nothing else."""

    def _source_text(self) -> str:
        if not SOURCE.is_file():
            self.skipTest(f"Reforged's Agent.py is not at {SOURCE}")
        return SOURCE.read_text(encoding="utf-8")

    def _source_members(self) -> list[str]:
        return re.findall(r"^    def (\w+)\s*\(", self._source_text(), re.M)

    def test_the_port_declares_every_source_member_in_order(self) -> None:
        """148 members, the source's names, the source's order — no member missing, none added.

        ``RequestName = GetNameByID`` (``Agent.py:149``) is an alias rather than a ``def``, so it
        is compared on its own below; it is excluded here because it is also a ``staticmethod``.

        The count is **148**, not the 147 an earlier pass measured: ``GetAnimationCode`` is
        declared ``def GetAnimationCode (agent_id : int)`` (``Agent.py:567-568``) — with a space
        before its parenthesis — so a ``def \\w+\\(`` pattern misses exactly that member. The
        pattern here allows the space, and the source itself is the count that matters.
        """

        source_members = self._source_members()
        self.assertEqual(len(source_members), 148)
        self.assertIn("GetAnimationCode", source_members)

        ported = [
            name
            for name, value in vars(Agent).items()
            if isinstance(value, staticmethod) and name != "RequestName"
        ]
        self.assertEqual(ported, source_members)

    def test_the_request_name_alias_is_the_sources_alias(self) -> None:
        """``RequestName`` is ``GetNameByID`` (``Agent.py:149``), the same object."""

        self.assertIn("    RequestName = GetNameByID", self._source_text())
        self.assertIs(Agent.RequestName, Agent.GetNameByID)

    def test_the_class_constants_are_the_sources(self) -> None:
        """``ILLUSIONARY_WEAPONRY_ID`` and ``DEAD_HEALTH_EPSILON`` (``Agent.py:14-18``).

        ``ILLUSIONARY_WEAPONRY_ID`` is declared ``0`` and **filled in on first use** — ``IsMartial``
        and ``IsMelee`` write ``Skill.GetID("Illusionary_Weaponry")`` into it (``Agent.py:1340-1342``
        and ``1381-1383``). It became answerable on 2026-09-26, so this asserts the pair the source
        allows: the declared zero, or the id the source's own memo writes.
        """

        from py4gw.skill import Skill

        self.assertIn("ILLUSIONARY_WEAPONRY_ID = 0", self._source_text())
        client = mock.Mock()
        client.read_skill = mock.Mock(return_value=None)
        with mock.patch("py4gw.client._current_client", client):
            self.assertIn(
                Agent.ILLUSIONARY_WEAPONRY_ID, (0, Skill.GetID("Illusionary_Weaponry"))
            )
        self.assertEqual(Agent.DEAD_HEALTH_EPSILON, 1.0 / 400.0)

    def test_every_member_is_a_staticmethod(self) -> None:
        """The source declares every member as ``@staticmethod``; none takes ``self``."""

        for name, value in vars(Agent).items():
            if name.startswith("__") or name in ("ILLUSIONARY_WEAPONRY_ID", "DEAD_HEALTH_EPSILON"):
                continue
            self.assertIsInstance(value, staticmethod, msg=name)


class AgentSourceReferenceTests(unittest.TestCase):
    """Every member names the source lines it ports, and the raising set is the documented one.

    Both checks read this project's own module with ``ast`` and Reforged's file the same way, so
    neither depends on a client, on importing the source (its first line is ``import PyAgent``), or
    on a number copied into this file by hand.
    """

    def _port_tree(self) -> ast.Module:
        return ast.parse(
            Path(agent_module.__file__).read_text(encoding="utf-8"),
            filename=str(agent_module.__file__),
        )

    def _source_tree(self) -> ast.Module:
        if not SOURCE.is_file():
            self.skipTest(f"Reforged's Agent.py is not at {SOURCE}")
        return ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))

    @staticmethod
    def _class_members(
        tree: ast.Module, name: str = "Agent"
    ) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == name:
                return {
                    member.name: member
                    for member in node.body
                    if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
                }
        raise AssertionError(f"class {name} is not declared")

    def test_every_member_names_the_source_lines_it_ports(self) -> None:
        """Each docstring's ``Agent.py:a-b`` is that member's own block, and covers all of it.

        The block starts at the member's first decorator, which is how the port has always written
        these references — the two ``@frame_cache`` members (``GetModelID``, ``GetXY``) therefore
        point at their ``@staticmethod`` line, two lines above ``def``. A reference that drifts by a
        line, or that stops before the member's last line, fails here.
        """

        source = self._class_members(self._source_tree())
        port = self._class_members(self._port_tree())

        self.assertEqual(len(source), 148)
        for name, member in source.items():
            with self.subTest(member=name):
                start = member.lineno
                for decorator in member.decorator_list:
                    start = min(start, decorator.lineno)
                end = member.end_lineno
                assert end is not None
                reference = re.search(r"Agent\.py:(\d+)(?:-(\d+))?", ast.get_docstring(port[name]) or "")
                self.assertIsNotNone(reference, f"{name} names no source lines")
                assert reference is not None
                self.assertEqual(int(reference.group(1)), start, "the block's first line")
                self.assertGreaterEqual(
                    int(reference.group(2) or reference.group(1)), end, "the member's last line"
                )

    def test_the_raising_members_are_exactly_the_documented_ones(self) -> None:
        """Three of the 148 raise, and they are the three direct ones — nothing calls one of them.

        Read from the module's own ``ast``: a member raises directly when its body calls
        ``_unported``, and transitively when it calls a member that does. Two groups have left this
        set: the name readers on 2026-09-26 with ``PyAgent.get_agent_enc_name``, and
        ``IsMartial``/``IsMelee`` with the ported ``Effects`` (``py4gw/effect.py``). What is left is
        the two frame-loop members and the native console path — and this test is what would notice
        either half changing.
        """

        tree = self._port_tree()
        members = self._class_members(tree)

        aliases: dict[str, str] = {}
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == "Agent":
                for member in node.body:
                    if isinstance(member, ast.Assign) and isinstance(member.value, ast.Name):
                        for assigned in member.targets:
                            if isinstance(assigned, ast.Name):
                                aliases[assigned.id] = member.value.id

        direct = {
            name
            for name, member in members.items()
            if any(
                isinstance(node, ast.Raise)
                and isinstance(node.exc, ast.Call)
                and isinstance(node.exc.func, ast.Name)
                and node.exc.func.id == "_unported"
                for node in ast.walk(member)
            )
        }
        self.assertEqual(len(direct), 3)
        self.assertTrue(set(aliases.values()) <= members.keys(), "an alias of a member")

        calls: dict[str, set[str]] = {}
        for name, member in members.items():
            reached: set[str] = set()
            for node in ast.walk(member):
                if isinstance(node, ast.Name) and node.id in members:
                    reached.add(node.id)
                elif isinstance(node, ast.Attribute) and node.attr in members:
                    reached.add(node.attr)
            calls[name] = reached - {name}

        transitive: set[str] = set()
        frontier = set(direct)
        while frontier:
            frontier = {
                name
                for name, reached in calls.items()
                if name not in direct and name not in transitive and reached & frontier
            }
            transitive |= frontier

        raising = direct | transitive | {
            name for name, target in aliases.items() if target in (direct | transitive)
        }
        self.assertEqual(
            raising,
            {"_invalidate_property_cache", "enable", "GetProfessionsTexturePaths"},
        )
        self.assertEqual(len(raising), 3)


class AgentReadTests(unittest.TestCase):
    """Every implemented read member returns the source's value for a record, and its default."""

    #: ``(member, args, value for the synthetic living record, value when no agent is readable)``.
    CASES: tuple[tuple[str, tuple[Any, ...], Any, Any], ...] = (
        ("GetInstanceFrames", (ID,), 12_500, 0),
        ("GetXY", (ID,), (1.5, -2.5), (0.0, 0.0)),
        ("GetXYZ", (ID,), (1.5, -2.5, 4.5), (0.0, 0.0, 0.0)),
        ("GetZPlane", (ID,), 9, 0),
        ("GetNameTagXYZ", (ID,), (0.25, 0.5, 0.75), (0.0, 0.0, 0.0)),
        ("GetModelScale1", (ID,), (1.5, 2.5), (0.0, 0.0)),
        ("GetModelScale2", (ID,), (3.5, 4.5), (0.0, 0.0)),
        ("GetModelScale3", (ID,), (5.5, 6.5), (0.0, 0.0)),
        ("GetNameProperties", (ID,), 0x1234, 0),
        ("GetVisualEffects", (ID,), 0x77, 0),
        ("GetTerrainNormalXYZ", (ID,), (0.125, 0.25, 1.0), (0.0, 0.0, 0.0)),
        ("GetGround", (ID,), 7, 0.0),
        ("GetRotationAngle", (ID,), 0.25, 0.0),
        ("GetRotationCos", (ID,), 0.5, 0.0),
        ("GetRotationSin", (ID,), 0.75, 0.0),
        ("GetVelocityXY", (ID,), (0.25, -0.5), (0.0, 0.0)),
        ("GetAnimationCode", (ID,), 44, 0),
        ("GetWeaponItemType", (ID,), 3, 0),
        ("GetOffhandItemType", (ID,), 4, 0),
        ("GetAnimationType", (ID,), 1.5, 0),
        ("GetWeaponAttackSpeed", (ID,), 1.75, 0.0),
        ("GetAttackSpeedModifier", (ID,), 0.5, 0.0),
        ("GetAgentModelType", (ID,), 0x1234, 0),
        ("GetTransmogNPCID", (ID,), 77, 0),
        ("GetTeamID", (ID,), 1, 0),
        ("GetAnimationSpeed", (ID,), 0.5, 0.0),
        ("GetAnimationID", (ID,), 22, 0),
        ("GetProfessions", (ID,), (5, 6), (0, 0)),
        ("GetProfessionIDs", (ID,), (5, 6), (0, 0)),
        ("GetLevel", (ID,), 20, 0),
        ("GetEnergy", (ID,), 25.5, 0.0),
        ("GetMaxEnergy", (ID,), 30, 0),
        ("GetEnergyRegen", (ID,), 0.75, 0.0),
        # The two pip readers are ``Utils``'s arithmetic over the record's own fields
        # (``Utils.py:749-759``): ``int(3.0 / 0.99 * 0.75 * 30)`` and ``int(480 * 3.5 / 2)``.
        ("GetEnergyPips", (ID,), 68, 0),
        ("GetHealthPips", (ID,), 840, 0),
        ("GetHealth", (ID,), 480.0, 0.0),
        ("GetMaxHealth", (ID,), 480, 0),
        ("GetHealthRegen", (ID,), 3.5, 0.0),
        ("GetOwnerID", (ID,), 42, 0),
        ("GetPlayerNumber", (ID,), 3, 0),
        ("GetLoginNumber", (ID,), 0, 0),
        ("GetModelID", (ID,), 3, 0),
        ("GetModelState", (ID,), 0, 0),
        ("GetTypeMap", (ID,), 0, 0),
        ("GetAgentEffects", (ID,), 0, 0),
        ("GetCastingSkillID", (ID,), 0, 0),
        ("GetWeaponExtraData", (ID,), (11, 3, 12, 4), (0, 0, 0, 0)),
        ("GetDaggerStatus", (ID,), 1, 0),
        ("GetOvercast", (ID,), 5, 0.0),
    )

    def _call(self, member: str, args: tuple[Any, ...], client: _FakeClient) -> Any:
        with mock.patch("py4gw.client._current_client", client):
            return getattr(Agent, member)(*args)

    def test_members_return_the_source_value_for_a_synthetic_record(self) -> None:
        """Each member returns what the source's body returns for the same record."""

        client = _FakeClient(agent=_living_record())
        for member, args, expected, _ in self.CASES:
            if expected is None:
                continue
            with self.subTest(member=member):
                self.assertEqual(self._call(member, args, client), expected)

    def test_get_instance_uptime_divides_by_the_frame_limit(self) -> None:
        """``Agent.py:281-294``: ``int(timer / max(fps_limit, 30) * 1000)`` over the record.

        The frame limit is native's ``GW::ui::GetFrameLimit`` through
        ``py4gw/ui/preferences.py``; the value is supplied here so the member's own arithmetic and
        the source's ``max(..., 30)`` guard are what this checks.
        """

        client = _FakeClient(agent=_living_record())
        with mock.patch("py4gw.client._current_client", client), mock.patch(
            "py4gw.ui.preferences.get_frame_limit", lambda: 60
        ):
            self.assertEqual(Agent.GetInstanceUptime(ID), int(12_500 / 60 * 1000))

        with mock.patch("py4gw.client._current_client", client), mock.patch(
            "py4gw.ui.preferences.get_frame_limit", lambda: 0
        ):
            # The source's own guard: a zero frame limit becomes 30 rather than dividing by zero.
            self.assertEqual(Agent.GetInstanceUptime(ID), int(12_500 / 30 * 1000))

        with mock.patch("py4gw.client._current_client", _FakeClient(agent=None)), mock.patch(
            "py4gw.ui.preferences.get_frame_limit", lambda: 60
        ):
            self.assertEqual(Agent.GetInstanceUptime(ID), 0)

    def test_members_return_the_source_default_when_the_agent_is_missing(self) -> None:
        """No readable agent gives the source's own default, never an exception."""

        client = _FakeClient(agent=None)
        for member, args, _, default in self.CASES:
            if default is None:
                continue
            with self.subTest(member=member):
                self.assertEqual(self._call(member, args, client), default)

    def test_a_missing_agent_is_the_sources_none(self) -> None:
        """``AgentArray.GetAgentByID`` answers ``None`` for an unknown id, ``0`` included.

        The source's chain looks the id up in the context's cache and then in the runtime's
        shared-memory channel, and answers ``None`` when neither holds it
        (``AgentContext.py:1477-1497``); this port's view answers from the client's agent array the
        same way, so the members that read a field off the missing record return their own
        missing-agent values.
        """

        with mock.patch("py4gw.client._current_client", _FakeClient(agent=None)):
            self.assertIsNone(Agent.GetAgentByID(0))
            self.assertEqual(Agent.GetHealth(0), 0.0)

    def test_is_valid_is_the_source_definition(self) -> None:
        """``IsValid`` is ``GetAgentByID(...) is not None`` (``Agent.py:38``)."""

        with mock.patch("py4gw.client._current_client", _FakeClient(agent=_living_record())):
            self.assertTrue(Agent.IsValid(ID))
        with mock.patch("py4gw.client._current_client", _FakeClient(agent=None)):
            self.assertFalse(Agent.IsValid(ID))

    def test_the_agent_kind_members_follow_the_type_flags(self) -> None:
        """``IsLiving``/``IsItem``/``IsGadget`` read the record's type flags (``Agent.py:345-367``)."""

        types = (
            (AgentType.LIVING, "IsLiving"),
            (AgentType.ITEM, "IsItem"),
            (AgentType.GADGET, "IsGadget"),
        )
        for flag, member in types:
            record = AgentStruct()
            record.type = int(flag)
            with mock.patch("py4gw.client._current_client", _FakeClient(agent=record)):
                answers = {
                    name: getattr(Agent, name)(ID)
                    for name in ("IsLiving", "IsItem", "IsGadget")
                }
            with self.subTest(flag=flag):
                self.assertEqual(answers[member], True)
                self.assertEqual(sum(1 for value in answers.values() if value), 1)

    def test_is_player_and_is_npc_read_the_login_number(self) -> None:
        """``IsPlayer``/``IsNPC`` are the login-number test (``Agent.py:1435-1443``)."""

        npc = _living_record()
        npc.login_number = 0
        with mock.patch("py4gw.client._current_client", _FakeClient(agent=npc)):
            self.assertFalse(Agent.IsPlayer(ID))
            self.assertTrue(Agent.IsNPC(ID))

        player = _living_record()
        player.login_number = 9
        with mock.patch("py4gw.client._current_client", _FakeClient(agent=player)):
            self.assertTrue(Agent.IsPlayer(ID))
            self.assertFalse(Agent.IsNPC(ID))


class AgentConditionTests(unittest.TestCase):
    """The condition, stance and corpse members, including the source's health epsilon."""

    def _record(self, **fields: Any) -> AgentLivingStruct:
        record = _living_record()
        for name, value in fields.items():
            setattr(record, name, value)
        return record

    def _answer(self, member: str, record: AgentLivingStruct) -> Any:
        with mock.patch("py4gw.client._current_client", _FakeClient(agent=record)):
            return getattr(Agent, member)(ID)

    def test_the_effects_bitmap_members(self) -> None:
        """Each condition member reads its own bit of ``effects`` (``Agent.py:957-1107``)."""

        cases = (
            ("IsBleeding", 0x0001),
            ("IsConditioned", 0x0002),
            ("IsUsedCorpse", 0x0004),
            ("IsDeepWounded", 0x0020),
            ("IsPoisoned", 0x0040),
            ("IsEnchanted", 0x0080),
            ("IsDegenHexed", 0x0400),
            ("IsHexed", 0x0800),
            ("IsWeaponSpelled", 0x8000),
        )
        for member, bit in cases:
            with self.subTest(member=member):
                self.assertTrue(self._answer(member, self._record(effects=bit)))
                self.assertFalse(self._answer(member, self._record(effects=0)))

    def test_is_crippled_needs_both_bits(self) -> None:
        """``IsCrippled`` is the two-bit combination the record exposes (``Agent.py:985-990``)."""

        self.assertTrue(self._answer("IsCrippled", self._record(effects=0x000A)))
        self.assertFalse(self._answer("IsCrippled", self._record(effects=0x0008)))

    def test_the_model_state_members(self) -> None:
        """Moving, knocked down, attacking, casting and idle are model-state sets."""

        cases = (
            ("IsMoving", 12), ("IsMoving", 76), ("IsMoving", 204),
            ("IsKnockedDown", 1104),
            ("IsAttacking", 96), ("IsAttacking", 1088), ("IsAttacking", 1120),
            ("IsCasting", 65), ("IsCasting", 581),
            ("IsIdle", 68), ("IsIdle", 64), ("IsIdle", 100),
        )
        for member, state in cases:
            with self.subTest(member=member, state=state):
                self.assertTrue(self._answer(member, self._record(model_state=state)))

    def test_is_aggressive_is_attacking_or_casting(self) -> None:
        """``IsAggressive`` combines the two (``Agent.py:1124-1132``)."""

        self.assertTrue(self._answer("IsAggressive", self._record(model_state=96)))
        self.assertTrue(self._answer("IsAggressive", self._record(model_state=65)))
        self.assertFalse(self._answer("IsAggressive", self._record(model_state=68)))

    def test_the_type_map_members(self) -> None:
        """The type-map bits the ported members read."""

        cases = (
            ("IsDeadByTypeMap", 0x8),
            ("IsInCombatStance", 0x1),
            ("HasQuest", 0x2),
            ("IsFemale", 0x200),
            ("HasBossGlow", 0x400),
            ("IsHidingCape", 0x1000),
            ("CanBeViewedInPartyWindow", 0x20000),
            ("IsSpawned", 0x40000),
            ("IsBeingObserved", 0x400000),
        )
        for member, bit in cases:
            with self.subTest(member=member):
                self.assertTrue(self._answer(member, self._record(type_map=bit)))
                self.assertFalse(self._answer(member, self._record(type_map=0)))

    def test_the_health_epsilon_decides_dead_and_alive(self) -> None:
        """``IsDead``/``IsAlive`` around ``DEAD_HEALTH_EPSILON`` (``Agent.py:1034-1093``)."""

        epsilon = Agent.DEAD_HEALTH_EPSILON

        alive = self._record(hp=480.0)
        self.assertFalse(self._answer("IsDead", alive))
        self.assertTrue(self._answer("IsAlive", alive))

        residual = self._record(hp=epsilon / 2)
        self.assertTrue(self._answer("IsDead", residual))
        self.assertFalse(self._answer("IsAlive", residual))

        above = self._record(hp=epsilon * 2)
        self.assertFalse(self._answer("IsDead", above))
        self.assertTrue(self._answer("IsAlive", above))

    def test_a_corpse_is_dead_exploitable_and_then_used(self) -> None:
        """``IsExploitable``/``IsUsedCorpse``/``IsExploitedCorpse`` (``Agent.py:1053-1075``)."""

        corpse = self._record(hp=0.0)
        self.assertTrue(self._answer("IsDead", corpse))
        self.assertFalse(self._answer("IsAlive", corpse))
        self.assertTrue(self._answer("IsExploitable", corpse))
        self.assertFalse(self._answer("IsUsedCorpse", corpse))
        self.assertFalse(self._answer("IsExploitedCorpse", corpse))

        used = self._record(hp=0.0, effects=0x0004)
        self.assertFalse(self._answer("IsExploitable", used))
        self.assertTrue(self._answer("IsUsedCorpse", used))
        self.assertTrue(self._answer("IsExploitedCorpse", used))

    def test_the_dead_bit_alone_is_enough(self) -> None:
        """The ``is_dead`` effects bit makes ``IsDead`` true at full health (``Agent.py:1045-1051``)."""

        record = self._record(hp=480.0, effects=0x0010)
        self.assertTrue(self._answer("IsDead", record))
        self.assertFalse(self._answer("IsAlive", record))

    def test_can_act_and_the_commented_out_members_are_their_literals(self) -> None:
        """The members whose bodies are literals in the source return those literals."""

        literals = (
            ("CanAct", True), ("GetKnockDownTimeRemaining", 0), ("HasStance", False),
            ("GetStanceID", 0), ("GetStanceCooldown", 0), ("GetTarget", 0),
            ("GetCastingTarget", 0), ("GetRemainingCastTime", 0),
            ("IsTargeted", False), ("GetAgetsTargeting", []),
            ("GetSkillsOnCooldown", []),
            ("GetRecentHealingReceived", []), ("GetRecentHealingDealt", []),
            ("GetObservedSkillbar", []), ("GetAttackTarget", 0),
        )
        with mock.patch("py4gw.client._current_client", _FakeClient(agent=None)):
            for member, expected in literals:
                with self.subTest(member=member):
                    self.assertEqual(getattr(Agent, member)(ID), expected)

            # The members whose source signature takes a skill id, an effect id or a window.
            self.assertFalse(Agent.IsSkillOnCooldown(ID, 5))
            self.assertFalse(Agent.IsCooldownEstimated(ID, 5))
            self.assertFalse(Agent.HasEffectRenewed(ID, 1234, 10000))
            self.assertEqual(Agent.GetRemainingRechargeTime(ID, 5), 0)


class AgentItemAndGadgetTests(unittest.TestCase):
    """The item and gadget members read their own records (``Agent.py:1563-1646``)."""

    def test_the_item_members(self) -> None:
        """Owner, item id, extra type and ``h00CC`` off the item record."""

        client = _FakeClient(agent=_item_record())
        with mock.patch("py4gw.client._current_client", client):
            self.assertEqual(Agent.GetItemAgentOwnerID(ID), 1234)
            self.assertEqual(Agent.GetItemAgentItemID(ID), 5678)
            self.assertEqual(Agent.GetItemAgentExtraType(ID), 3)
            self.assertEqual(Agent.GetItemAgenth00CC(ID), 0x0C)

        with mock.patch("py4gw.client._current_client", _FakeClient(agent=None)):
            self.assertEqual(Agent.GetItemAgentOwnerID(ID), 999)
            self.assertEqual(Agent.GetItemAgentItemID(ID), 0)
            self.assertEqual(Agent.GetItemAgentExtraType(ID), 0)
            self.assertEqual(Agent.GetItemAgenth00CC(ID), 0)

    def test_the_gadget_members(self) -> None:
        """Gadget id, agent id, extra type, ``h00C4``, ``h00C8`` and ``h00D4``."""

        client = _FakeClient(agent=_gadget_record())
        with mock.patch("py4gw.client._current_client", client):
            self.assertEqual(Agent.GetGadgetID(ID), 4242)
            self.assertEqual(Agent.GetGadgetAgentID(ID), ID)
            self.assertEqual(Agent.GetGadgetAgentExtraType(ID), 5)
            self.assertEqual(Agent.GetGadgetAgenth00C4(ID), 0xC4)
            self.assertEqual(Agent.GetGadgetAgenth00C8(ID), 0xC8)
            self.assertEqual(Agent.GetGadgetAgenth00D4(ID), [1, 2, 3, 4])

        with mock.patch("py4gw.client._current_client", _FakeClient(agent=None)):
            self.assertEqual(Agent.GetGadgetID(ID), 0)
            self.assertEqual(Agent.GetGadgetAgentID(ID), 0)
            self.assertEqual(Agent.GetGadgetAgentExtraType(ID), 0)
            self.assertEqual(Agent.GetGadgetAgenth00C4(ID), 0)
            self.assertEqual(Agent.GetGadgetAgenth00C8(ID), 0)
            self.assertEqual(Agent.GetGadgetAgenth00D4(ID), [])

    def test_get_guild_id_reads_the_tag_record(self) -> None:
        """``GetGuildID`` reads ``tags.guild_id``, and answers ``0`` with no tag object.

        ``living.tags`` is a property that reads the target pointer (``agent_array.py:1102-1112``),
        so the record is bound to a reader here — exactly the state the ported reader leaves a
        record in (``agent_array.py:2580-2587``).
        """

        tags = TagInfoStruct()
        tags.guild_id = 1234
        reader = _FakeReader(tags=tags)

        tagged = _living_record()
        tagged.tags_ptr = reader.tag_address
        tagged.bind_reader(reader, 0x3000)
        with mock.patch("py4gw.client._current_client", _FakeClient(agent=tagged)):
            self.assertEqual(Agent.GetGuildID(ID), 1234)

        untagged = _living_record()
        untagged.tags_ptr = 0
        untagged.bind_reader(reader, 0x3000)
        with mock.patch("py4gw.client._current_client", _FakeClient(agent=untagged)):
            self.assertEqual(Agent.GetGuildID(ID), 0)


class AgentContextTests(unittest.TestCase):
    """The world-context members: attributes and NPC models (``Agent.py:242-265``, ``1445-1481``)."""

    def _attribute(self, attribute_id: int, level: int) -> AttributeStruct:
        attribute = AttributeStruct()
        attribute.attribute_id = attribute_id
        attribute.level_base = level
        return attribute

    def _model(self, model_file_id: int, npc_flags: int) -> NPC_ModelStruct:
        model = NPC_ModelStruct()
        model.model_file_id = model_file_id
        model.npc_flags = npc_flags
        return model

    def test_get_attributes_and_the_dict_form(self) -> None:
        """``GetAttributes`` returns the context's list; the dict form keeps positive levels."""

        world = _FakeWorld(attributes=[self._attribute(1, 12), self._attribute(2, 0), self._attribute(3, 5)])
        with mock.patch("py4gw.client._current_client", _FakeClient(world=world)):
            attributes = Agent.GetAttributes(ID)
            self.assertEqual([int(attr.attribute_id) for attr in attributes], [1, 2, 3])
            self.assertEqual(Agent.GetAttributesDict(ID), {1: 12, 3: 5})

    def test_get_attributes_without_a_world_context(self) -> None:
        """No world context, or a failed read, is the source's empty list."""

        with mock.patch("py4gw.client._current_client", _FakeClient(world=None)):
            self.assertEqual(Agent.GetAttributes(ID), [])
            self.assertEqual(Agent.GetAttributesDict(ID), {})

    def test_get_npc_model_by_id_indexes_then_scans(self) -> None:
        """The record at the id's index when valid, otherwise the scan by ``model_file_id``."""

        models = [self._model(0, 0) for _ in range(6)]
        models[5] = self._model(5, 0x8)
        models[2] = self._model(9, 0)
        world = _FakeWorld(npc_models=models)
        with mock.patch("py4gw.client._current_client", _FakeClient(world=world)):
            indexed = Agent.GetNPCModelByID(5)
            self.assertIsNotNone(indexed)
            assert indexed is not None
            self.assertEqual(int(indexed.model_file_id), 5)

            # 9 is past the array, so the scan by model_file_id answers.
            scanned = Agent.GetNPCModelByID(9)
            self.assertIsNotNone(scanned)
            assert scanned is not None
            self.assertEqual(int(scanned.model_file_id), 9)

            # The indexed record at 3 is not valid and nothing else carries that id.
            self.assertIsNone(Agent.GetNPCModelByID(3))

            # The member's own guard, before any context read.
            self.assertIsNone(Agent.GetNPCModelByID(0))

    def test_the_npc_flag_and_fleshiness_members(self) -> None:
        """``GetNPCFlags``/``IsFleshy`` read the model under the record's player number."""

        models = [self._model(0, 0) for _ in range(6)]
        models[3] = self._model(3, 0x8)
        world = _FakeWorld(npc_models=models)

        npc = _living_record()
        npc.login_number = 0
        with mock.patch("py4gw.client._current_client", _FakeClient(agent=npc, world=world)):
            self.assertEqual(Agent.GetNPCFlags(ID), 0x8)
            self.assertTrue(Agent.IsFleshy(ID))

        player = _living_record()
        player.login_number = 4
        with mock.patch("py4gw.client._current_client", _FakeClient(agent=player, world=world)):
            self.assertEqual(Agent.GetNPCFlags(ID), 0)
            self.assertTrue(Agent.IsFleshy(ID))

    def test_a_player_corpse_is_exploitable_when_fleshy(self) -> None:
        """``IsExploitableCorpse`` is ``IsExploitable and IsFleshy`` (``Agent.py:1060-1063``)."""

        models = [self._model(0, 0) for _ in range(4)]
        models[3] = self._model(3, 0x8)
        world = _FakeWorld(npc_models=models)

        corpse = _living_record()
        corpse.hp = 0.0
        corpse.login_number = 4
        with mock.patch("py4gw.client._current_client", _FakeClient(agent=corpse, world=world)):
            self.assertTrue(Agent.IsExploitable(ID))
            self.assertTrue(Agent.IsFleshy(ID))
            self.assertTrue(Agent.IsExploitableCorpse(ID))

        living = _living_record()
        living.login_number = 4
        with mock.patch("py4gw.client._current_client", _FakeClient(agent=living, world=world)):
            self.assertFalse(Agent.IsExploitableCorpse(ID))


class AgentEncNameTests(unittest.TestCase):
    """The binding and the walk behind it (``agent_bindings.cpp:216-224``, ``agent_methods.cpp:249-316``).

    Every branch of native's ``GW::agent::GetAgentEncName`` is driven against records this test
    builds and a reader that serves them: the agent record, the world's agent-name array, the
    player array by login number, the NPC record a living agent falls back to, the agent-summary
    gadget entry, the gadget context's ``gadget_info``, and the item array by item id. Sizes and
    offsets come from the ported structures themselves, so a layout change fails here rather than
    in a live run.
    """

    #: Base addresses the fixture maps its arrays, records and names at. ``ARRAY_HEADER`` is the
    #: address ``agent.agent_array_addr`` answers with — native's ``g_agent_array_addr`` — and
    #: ``AGENT_POINTERS`` is the table it heads: one ``Agent*`` per agent id.
    NAME = 0x00600000
    OTHER_NAME = 0x00600008
    AGENT_INFOS = 0x00610000
    PLAYERS = 0x00620000
    NPCS = 0x00630000
    SUMMARY = 0x00640000
    SUMMARY_SUB = 0x00650000
    GADGET_INFO = 0x00660000
    ITEM_POINTERS = 0x00670000
    ITEMS = 0x00680000
    ARRAY_HEADER = 0x00690000
    AGENT_POINTERS = 0x006A0000
    AGENT_RECORDS = 0x006B0000
    MOVEMENT_POINTERS = 0x006C0000
    MOVEMENT_RECORD = 0x00C00000

    #: How many slots the fixture's agent table advertises (``GWArray<Agent*>``).
    ARRAY_SLOTS = 16

    def setUp(self) -> None:
        self.reader = MemoryFixtureReader()
        self.agent = _living_record()
        self.agent.agent_id = ID
        self.agent.login_number = 0
        self.agent.player_number = 1
        self.agent_ids = (ID,)

        self.world = WorldContextStruct()
        self.world.agent_name_info_array = GWArray(self.AGENT_INFOS, 8, 8, 0)
        self.world.players_array = GWArray(self.PLAYERS, 2, 2, 0)
        self.world.npc_models_array = GWArray(self.NPCS, 2, 2, 0)
        self.world.bind_reader(self.reader, 0x00100000)

        self.acc = AccAgentContextStruct()
        self.acc.agent_summary_info_array = GWArray(self.SUMMARY, 8, 8, 0)
        self.acc.bind_reader(self.reader, 0x00200000)

        self.gadget = GadgetContextStruct()
        self.gadget.gadget_info_array = GWArray(self.GADGET_INFO, 8, 8, 0)
        self.gadget.bind_reader(self.reader, 0x00300000)

        self.item_context = ItemContextStruct()
        self.item_context.item_array = GWArray(self.ITEM_POINTERS, 4, 4, 0)
        self.item_context.bind_reader(self.reader, 0x00400000)

        # The agent table native indexes: the header, the pointer table it heads, and the record the
        # pointer addresses. ``_install_agent_record`` owns the record, so a test can replace it.
        self._install_array_header()
        self._install_agent_record(self.agent)
        self._install_movement(valid=True)

        # Every array the walk can reach is mapped — as zeros — so a branch a test does not fill
        # reads an empty entry the way the client's own mapped memory would, instead of failing on
        # an address the fixture never mentioned.
        self.reader.add(self.AGENT_INFOS, bytes(ctypes.sizeof(AgentNameInfoStruct) * 8))
        self.reader.add(self.PLAYERS, bytes(ctypes.sizeof(PlayerStruct) * 2))
        self.reader.add(self.NPCS, bytes(ctypes.sizeof(NPC_ModelStruct) * 2))
        self.reader.add(self.SUMMARY, bytes(ctypes.sizeof(AgentSummaryInfoStruct) * 8))
        self.reader.add(self.GADGET_INFO, bytes(ctypes.sizeof(GadgetInfoStruct) * 8))
        self.reader.add(self.ITEM_POINTERS, bytes(4 * 4))

        self.client = _WalkClient(self.reader, self)

    def _install_array_header(self, size: int | None = None) -> None:
        """Map the ``GWArray<Agent*>`` header the resolver's address points at."""

        self.reader.add(
            self.ARRAY_HEADER,
            bytes(GWArray(self.AGENT_POINTERS, self.ARRAY_SLOTS, size or self.ARRAY_SLOTS, 0)),
        )

    def _install_agent_record(self, record: Any) -> None:
        """Map ``record`` in the table's slot for its own id (and point the slot at it)."""

        agent_id = int(record.agent_id)
        pointers = bytearray(4 * self.ARRAY_SLOTS)
        pointers[agent_id * 4 : agent_id * 4 + 4] = self.AGENT_RECORDS.to_bytes(4, "little")
        self.reader.add(self.AGENT_POINTERS, bytes(pointers))
        self.reader.add(self.AGENT_RECORDS, bytes(record))
        self.agent = record

    def _clear_agent_pointer(self) -> None:
        """Empty the table's slot, so native's ``agents->at(id)`` answers null."""

        self.reader.add(self.AGENT_POINTERS, bytes(4 * self.ARRAY_SLOTS))

    def _install_movement(self, valid: bool, slots: int = 8) -> None:
        """Map the movement-pointer array native's ``GetAgentByID`` checks after the index.

        The array is the agent context's own ``agent_movement`` (``GWArray<AgentMovement*>``,
        ``agent.h:456``); a null entry there is what makes native answer ``nullptr`` for a slot whose
        record is still in the table.
        """

        pointers = bytearray(4 * slots)
        if valid:
            pointers[ID * 4 : ID * 4 + 4] = (0x00C00000).to_bytes(4, "little")
            # The pointer has to address a movement record: the ported property reads the record it
            # names, keeping the source's indexes and nulls (``acc_agent_context.py:330-351``).
            movement = AgentMovementStruct()
            movement.agent_id = ID
            self.reader.add(self.MOVEMENT_RECORD, bytes(movement))
        self.reader.add(self.MOVEMENT_POINTERS, bytes(pointers))
        self.acc.agent_movement_array = GWArray(self.MOVEMENT_POINTERS, slots, slots, 0)

    def _use_client(self) -> None:
        patcher = mock.patch("py4gw.client._current_client", self.client)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _name_bytes(self, text: str) -> bytes:
        """One player-prefixed encoded name, in the exact form the live client hands over.

        Captured live on 2026-09-26 (``tests/probe_agent_effects_live.py``): a real player's name is
        ``0x0BA9``, then a nonzero word (``0x0107`` on this client), then the text as UTF-16LE, then
        ``0x0001``, then the terminator — 38 bytes for ``"Blacki D Dragon"``. This reproduces that
        shape: the word at code unit 2 must be nonzero because the binding's own walk stops at the
        first zero unit (``agent_bindings.cpp:219``), and the decoder skips the word because it
        starts reading at byte 4 (``string_table.py:1054``). The binding returns these bytes **with**
        the trailing terminator.
        """

        return (
            b"\xa9\x0b\x07\x01"
            + text.encode("utf-16-le")
            + b"\x01\x00"
            + b"\x00\x00"
        )

    def _map_name(self, address: int, text: str) -> bytes:
        raw = self._name_bytes(text)
        self.reader.add(address, raw)
        return raw

    def _install_record_pointer(
        self, base: int, count: int, index: int, element: type[Any], field: str, pointer: int
    ) -> None:
        """Set one pointer field inside a record array already mapped at ``base``."""

        size = ctypes.sizeof(element)
        buffer = bytearray(size * count)
        field_offset = cast(Any, getattr(element, field)).offset
        ctypes.c_uint32.from_buffer(buffer, index * size + field_offset).value = pointer
        self.reader.add(base, bytes(buffer))

    def test_the_binding_returns_the_bytes_with_their_terminator(self) -> None:
        """``get_agent_enc_name`` is the binding's own answer, terminator included."""

        from py4gw.agent import get_agent_enc_name

        raw = self._map_name(self.NAME, "Bob")
        self._install_agent_name_pointer(ID, self.NAME)
        self._use_client()

        self.assertEqual(get_agent_enc_name(ID), list(raw))
        self.assertEqual(Agent.GetEncNameByID(ID), list(raw))
        self.assertEqual(Agent.GetNameByID(ID), "Bob")
        self.assertTrue(Agent.IsNameReady(ID))

    def test_a_missing_name_is_the_bindings_empty_list(self) -> None:
        """A null pointer is ``[]`` and ``""``, which is what the binding and the source return."""

        from py4gw.agent import get_agent_enc_name

        self._install_agent_name_pointer(ID, 0)
        self._install_npc_name_pointer(1, 0)
        self._use_client()

        self.assertEqual(get_agent_enc_name(ID), [])
        self.assertEqual(Agent.GetEncNameByID(ID), [])
        self.assertEqual(Agent.GetNameByID(ID), "")
        self.assertFalse(Agent.IsNameReady(ID))
        self.assertEqual(Agent.GetEncNameStrByID(ID), "")

    def test_the_world_agent_name_array_answers_when_the_record_is_gone(self) -> None:
        """The by-id fallback reads ``world->agent_infos[agent_id].name_enc``.

        "Gone" is the table's own answer: native's ``GetAgentByID`` indexes the agent table, so a
        slot that no longer names a record is what sends the walk to the world's name array — the
        same path a movement-less slot takes a few tests down.
        """

        self._map_name(self.OTHER_NAME, "Ann")
        self._install_agent_name_pointer(ID, self.OTHER_NAME)
        self._clear_agent_pointer()
        self._use_client()

        self.assertEqual(Agent.GetNameByID(ID), "Ann")

    def test_a_player_name_comes_from_the_player_array_by_login_number(self) -> None:
        """A living agent with a login number reads ``players[login_number].name_enc``."""

        self._map_name(self.OTHER_NAME, "Cid")
        self.agent.login_number = 1
        self._install_agent_record(self.agent)
        self._install_player_name_pointer(1, self.OTHER_NAME)
        self._use_client()

        self.assertEqual(Agent.GetNameByID(ID), "Cid")

    def test_a_login_number_past_the_player_array_is_null(self) -> None:
        """The source returns null there rather than falling through to the NPC record."""

        self.agent.login_number = 7
        self._install_agent_record(self.agent)
        self._install_npc_name_pointer(1, self.NAME)
        self._use_client()

        self.assertEqual(Agent.GetEncNameByID(ID), [])

    def test_a_living_agents_name_falls_back_to_its_npc_record(self) -> None:
        """With no name in the array, ``GetNPCByID(player_number).name_enc`` answers."""

        self._map_name(self.OTHER_NAME, "Dan")
        self._install_agent_name_pointer(ID, 0)
        self._install_npc_name_pointer(1, self.OTHER_NAME)
        self._use_client()

        self.assertEqual(Agent.GetNameByID(ID), "Dan")

    def test_a_movement_less_slot_is_not_an_agent(self) -> None:
        """Native answers null for a slot whose movement entry is gone (``agent_methods.cpp:80-85``).

        The record is still in the table and the world's name array still has its name, so what is
        being checked is the second half of native's ``GetAgentByID``: the movement check that makes
        a stale slot invisible.
        """

        self._map_name(self.OTHER_NAME, "Hal")
        self._install_agent_name_pointer(ID, self.OTHER_NAME)
        self._install_movement(valid=False)
        self._use_client()

        self.assertEqual(Agent.GetNameByID(ID), "Hal")

    def test_a_gadgets_name_comes_from_the_agent_summary_entry(self) -> None:
        """The gadget branch prefers ``agent_summary_info[agent_id].extra_info_sub``."""

        self._map_name(self.OTHER_NAME, "Eve")
        self._install_agent_record(_walk_gadget_record())
        self.client.agent = self.agent
        self._install_summary_gadget_name(ID, self.OTHER_NAME, gadget_id=0)
        self._use_client()

        self.assertEqual(Agent.GetNameByID(ID), "Eve")

    def test_a_gadgets_name_falls_back_to_the_gadget_context(self) -> None:
        """With no summary name, ``gadget_info[gadget_id].name_enc`` answers."""

        self._map_name(self.OTHER_NAME, "Fay")
        self._install_agent_record(_walk_gadget_record())
        self.client.agent = self.agent
        self._install_summary_gadget_name(ID, 0, gadget_id=1)
        self._install_gadget_info_name(1, self.OTHER_NAME)
        self._use_client()

        self.assertEqual(Agent.GetNameByID(ID), "Fay")

    def test_an_items_name_comes_from_the_item_array_by_item_id(self) -> None:
        """``item::GetItemById(item_id)->name_enc`` (``item_methods.cpp:109-112``)."""

        self._map_name(self.OTHER_NAME, "Gus")
        record = _item_record()
        record.item_id = 2
        self._install_agent_record(record)
        self.client.agent = self.agent
        self._install_item_name_pointer(record.item_id, self.OTHER_NAME)
        self._use_client()

        self.assertEqual(Agent.GetNameByID(ID), "Gus")

    def test_the_copy_stops_at_the_bound(self) -> None:
        """A name that never terminates costs the bound, not an unbounded walk."""

        from py4gw.agent import MAX_ENC_NAME_CODE_UNITS, get_agent_enc_name

        self.reader.add(self.NAME, b"\x41\x00" * MAX_ENC_NAME_CODE_UNITS)
        self._install_agent_name_pointer(ID, self.NAME)
        self._use_client()

        self.assertEqual(len(get_agent_enc_name(ID)), MAX_ENC_NAME_CODE_UNITS * 2)

    def test_the_walkers_that_call_it_answer_now(self) -> None:
        """The four members that used to raise through the name readers answer on this fixture."""

        self._map_name(self.NAME, "Bob")
        self._install_agent_name_pointer(ID, self.NAME)
        self._use_client()

        literal = Agent.GetEncNameStrByID(ID, literal=True)
        self.assertEqual(Agent.GetAgentIDByName("bob"), ID)
        self.assertEqual(Agent.GetAgentIDByName("nobody"), 0)
        self.assertEqual(Agent.GetAgentIDByEncString(literal), ID)
        # ``GetModelIDByEncString`` answers ``Agent.GetModelID`` of the agent it found, which the
        # source defines as the record's ``player_number`` (``Agent.py:340-343``).
        self.assertEqual(
            Agent.GetModelIDByEncString(literal), int(self.agent.player_number)
        )

    # ── fixture helpers ────────────────────────────────────────────────────

    def _install_agent_name_pointer(self, index: int, pointer: int) -> None:
        """Set ``agent_infos[index].name_enc`` in the world's array buffer."""

        self._install_record_pointer(
            self.AGENT_INFOS, 8, index, AgentNameInfoStruct, "name_enc_ptr", pointer
        )

    def _install_player_name_pointer(self, index: int, pointer: int) -> None:
        self._install_record_pointer(
            self.PLAYERS, 2, index, PlayerStruct, "name_enc_ptr", pointer
        )

    def _install_npc_name_pointer(self, index: int, pointer: int) -> None:
        self._install_record_pointer(
            self.NPCS, 2, index, NPC_ModelStruct, "name_enc_ptr", pointer
        )

    def _install_summary_gadget_name(
        self, index: int, pointer: int, gadget_id: int
    ) -> None:
        """Map the agent-summary entry and the gadget sub-record it points at."""

        sub = bytearray(ctypes.sizeof(AgentSummaryInfoSubStruct))
        ctypes.c_uint32.from_buffer(
            sub, cast(Any, AgentSummaryInfoSubStruct.gadget_id).offset
        ).value = gadget_id
        ctypes.c_uint32.from_buffer(
            sub, cast(Any, AgentSummaryInfoSubStruct.gadget_name_enc).offset
        ).value = pointer
        self.reader.add(self.SUMMARY_SUB, bytes(sub))

        self._install_record_pointer(
            self.SUMMARY,
            8,
            index,
            AgentSummaryInfoStruct,
            "extra_info_sub_ptr",
            self.SUMMARY_SUB,
        )

    def _install_gadget_info_name(self, index: int, pointer: int) -> None:
        self._install_record_pointer(
            self.GADGET_INFO, 8, index, GadgetInfoStruct, "name_enc", pointer
        )

    def _install_item_name_pointer(self, index: int, pointer: int) -> None:
        """Map one item pointer in the array and the item record it addresses."""

        pointers = bytearray(4 * 4)
        ctypes.c_uint32.from_buffer(pointers, index * 4).value = self.ITEMS
        self.reader.add(self.ITEM_POINTERS, bytes(pointers))

        record = bytearray(ctypes.sizeof(ItemStruct))
        ctypes.c_uint32.from_buffer(record, ItemStruct.name_enc.offset).value = pointer
        self.reader.add(self.ITEMS, bytes(record))


class _WalkClient:
    """A connection whose contexts are real records over a fixture reader.

    It carries what both readers of the name walk need: Reforged's Python ``Agent.GetAgentByID``
    goes through the ``agent_array`` facade's view, and the ported binding's own lookup — native's
    ``GW::agent::GetAgentByID`` — reads the array header at ``array_address`` and the movement array
    in the agent context. Everything else is a context this fixture mapped.
    """

    def __init__(self, reader: "MemoryFixtureReader", fixture: AgentEncNameTests) -> None:
        self._reader = reader
        self._fixture = fixture
        self.agent: Any = fixture.agent
        self.agent_ids = fixture.agent_ids
        self.array_address = fixture.ARRAY_HEADER
        self.refusal: Exception | None = None

    @property
    def reader(self) -> "MemoryFixtureReader":
        return self._reader

    @property
    def agent_array(self) -> "_FakeAgentArrayFacade":
        return _FakeAgentArrayFacade(self)

    def read_world_context(self) -> Any:
        return self._fixture.world

    def read_acc_agent_context(self) -> Any:
        return self._fixture.acc

    def read_gadget_context(self) -> Any:
        return self._fixture.gadget

    def read_item_context(self) -> Any:
        return self._fixture.item_context


def _walk_gadget_record() -> AgentGadgetStruct:
    """One gadget agent record for the name walk, whose ``gadget_id`` is the one the fixture maps."""

    record = AgentGadgetStruct()
    record.type = int(AgentType.GADGET)
    record.agent_id = ID
    record.gadget_id = 1
    return record


class AgentMartialTests(unittest.TestCase):
    """``IsMartial``/``IsMelee`` answer now that ``Effects`` is ported (``Agent.py:1333-1394``).

    Both bodies are ``Skill.GetID("Illusionary_Weaponry")`` → ``Effects.HasEffect`` → ``IsPet`` →
    ``GetWeaponType``, in that order, so each test pins one step of it: the Illusionary Weaponry
    check short-circuits to ``False``, a pet answers ``True`` before the weapon is looked at, and a
    real weapon's name decides the rest. ``Effects.HasEffect`` reads the ported
    ``WorldContext.party_effects`` array through a fake block whose records are the real
    ``EffectStruct``/``BuffStruct`` — the same shape the effects suite uses.
    """

    def _record(self, **changes: Any) -> AgentLivingStruct:
        record = _living_record()
        for name, value in changes.items():
            setattr(record, name, value)
        return record

    def _effects_block(self, agent_id: int, effects: list[Any], buffs: list[Any]) -> Any:
        """One ``AgentEffects``-shaped block for the fake world."""

        block = mock.Mock()
        block.agent_id = agent_id
        block.effects = effects
        block.buffs = buffs
        return block

    def _effect(self, skill_id: int) -> Any:
        from py4gw.context.world_context import EffectStruct

        effect = EffectStruct()
        effect.skill_id = skill_id
        effect.attribute_level = 12
        effect.effect_id = 77
        effect.agent_id = ID
        effect.duration = 10.0
        effect.timestamp = 1000
        return effect

    def test_a_pet_is_martial_before_its_weapon_is_considered(self) -> None:
        """``IsPet`` answers first (``Agent.py:1349-1350``, ``1388-1389``)."""

        from py4gw.enums_src.game_data_enums import Allegiance

        record = self._record(
            allegiance=int(Allegiance.SpiritPet), login_number=0, weapon_type=0
        )
        client = _FakeClient(agent=record, agent_ids=(ID,), world=_FakeWorld())
        with mock.patch("py4gw.client._current_client", client):
            self.assertTrue(Agent.IsPet(ID))
            self.assertTrue(Agent.IsMartial(ID))
            self.assertTrue(Agent.IsMelee(ID))

    def test_the_weapon_name_decides_when_no_effect_is_up(self) -> None:
        """Axe is in both lists, Bow only in the martial one (``Agent.py:1351-1355, 1390-1394``)."""

        from py4gw.enums_src.game_data_enums import Allegiance

        axe = self._record(allegiance=int(Allegiance.Ally), weapon_type=2)
        with mock.patch(
            "py4gw.client._current_client",
            _FakeClient(agent=axe, agent_ids=(ID,), world=_FakeWorld()),
        ):
            self.assertTrue(Agent.IsMartial(ID))
            self.assertTrue(Agent.IsMelee(ID))

        bow = self._record(allegiance=int(Allegiance.Ally), weapon_type=1)
        with mock.patch(
            "py4gw.client._current_client",
            _FakeClient(agent=bow, agent_ids=(ID,), world=_FakeWorld()),
        ):
            self.assertTrue(Agent.IsMartial(ID))
            self.assertFalse(Agent.IsMelee(ID))

    def test_illusionary_weaponry_short_circuits_both_members(self) -> None:
        """``Effects.HasEffect`` answers ``False`` in the body when the effect is up."""

        from py4gw.agent import Agent as AgentClass
        from py4gw.enums_src.game_data_enums import Allegiance
        from py4gw.skill import Skill

        record = self._record(allegiance=int(Allegiance.Ally), weapon_type=2)
        world = _FakeWorld(
            party_effects=[
                self._effects_block(ID, [self._effect(33)], [])
            ]
        )
        client = _FakeClient(agent=record, agent_ids=(ID,), world=world)
        with mock.patch("py4gw.client._current_client", client):
            self.assertFalse(Agent.IsMartial(ID))
            self.assertFalse(Agent.IsMelee(ID))

            # The source's own memo, written on that first call.
            self.assertEqual(
                AgentClass.ILLUSIONARY_WEAPONRY_ID,
                Skill.GetID("Illusionary_Weaponry"),
            )
            self.assertEqual(AgentClass.ILLUSIONARY_WEAPONRY_ID, 33)

            # The same record with no effect up answers through its weapon again.
            client.world = _FakeWorld()
            self.assertTrue(Agent.IsMartial(ID))
            self.assertTrue(Agent.IsMelee(ID))


class AgentBlockedTests(unittest.TestCase):
    """The members that raise name themselves and what they still need."""

    #: ``(member, args, the requirement the message must name)``. Each of these bodies needs
    #: something this port does not have, so the member raises instead of answering.
    #:
    #: Two groups have left this list: the three name readers on 2026-09-26
    #: (``PyAgent.get_agent_enc_name`` is ported as :func:`py4gw.agent.get_agent_enc_name`), and
    #: ``IsMartial``/``IsMelee``, which answer now that ``Effects`` is ported
    #: (``tests/test_effects_offline.py``). What is left is the frame loop and the native console.
    BLOCKED: tuple[tuple[str, tuple[Any, ...], str], ...] = (
        ("_invalidate_property_cache", (), "the four per-frame agent caches"),
        ("enable", (), "PyCallback.PyCallback.Register"),
        ("GetProfessionsTexturePaths", (ID,), "PySystem.Console.get_projects_path"),
    )

    def test_the_blocked_members_raise_and_name_their_requirement(self) -> None:
        """Every blocked member raises ``NotImplementedError`` naming itself and its work item."""

        client = _FakeClient(agent=_living_record(), agent_ids=(ID,))
        with mock.patch("py4gw.client._current_client", client):
            for member, args, requirement in self.BLOCKED:
                with self.subTest(member=member):
                    with self.assertRaises(NotImplementedError) as caught:
                        getattr(Agent, member)(*args)
                    message = str(caught.exception)
                    self.assertIn(f"Agent.{member} is declared but not built here yet", message)
                    self.assertIn(requirement, message)
                    self.assertIn("The source's member works", message)


class AgentEnumBackedTests(unittest.TestCase):
    """The eight members the ported ``enums_src`` enums unblocked answer the source's values.

    The synthetic record in ``LIVING`` is allegiance ``4`` (``Allegiance.SpiritPet``), primary
    profession ``5`` (Mesmer) and secondary ``6`` (Elementalist) with weapon type ``2`` (Axe), so
    every expectation below is the source's own arithmetic on those fields — and the two
    spawn-dependent ones are derived from the record's own ``is_spawned``, which is the field
    ``IsSpirit``/``IsPet`` split on rather than something this test assumes.
    """

    def test_the_spirit_pet_split_is_the_source_s(self) -> None:
        """``IsSpirit`` needs the spawn flag, ``IsPet`` needs its absence, ``IsMinion`` neither."""

        record = _living_record()
        client = _FakeClient(agent=record, agent_ids=(ID,))
        with mock.patch("py4gw.client._current_client", client):
            self.assertEqual(Agent.IsSpirit(ID), record.is_spawned)
            self.assertEqual(Agent.IsPet(ID), not record.is_spawned)
            self.assertFalse(Agent.IsMinion(ID))

    def test_a_minion_record_is_a_minion_and_neither_spirit_nor_pet(self) -> None:
        """Allegiance ``5`` is ``Allegiance.Minion``, and the source's comparisons say so."""

        record = _living_record()
        record.allegiance = 5
        client = _FakeClient(agent=record, agent_ids=(ID,))
        with mock.patch("py4gw.client._current_client", client):
            self.assertTrue(Agent.IsMinion(ID))
            self.assertFalse(Agent.IsSpirit(ID))
            self.assertFalse(Agent.IsPet(ID))

    def test_the_allegiance_and_profession_tables_are_the_source_s(self) -> None:
        """``GetAllegiance`` and both profession name members answer their table entries."""

        record = _living_record()
        client = _FakeClient(agent=record, agent_ids=(ID,))
        with mock.patch("py4gw.client._current_client", client):
            self.assertEqual(Agent.GetAllegiance(ID), (4, "Spirit/Pet"))
            self.assertEqual(Agent.GetProfessionNames(ID), ("Mesmer", "Elementalist"))
            self.assertEqual(Agent.GetProfessionShortNames(ID), ("Me", "E"))

    def test_get_allegiance_falls_back_the_way_the_source_does(self) -> None:
        """A value outside the enum answers ``"Unknown"`` beside the raw value (``Agent.py:1427``)."""

        record = _living_record()
        record.allegiance = 99
        client = _FakeClient(agent=record, agent_ids=(ID,))
        with mock.patch("py4gw.client._current_client", client):
            self.assertEqual(Agent.GetAllegiance(ID), (99, "Unknown"))

    def test_get_weapon_type_maps_and_falls_back_the_way_the_source_does(self) -> None:
        """``Weapon_Names`` for a known id, ``"Unknown"`` for one the enum refuses."""

        record = _living_record()
        client = _FakeClient(agent=record, agent_ids=(ID,))
        with mock.patch("py4gw.client._current_client", client):
            self.assertEqual(Agent.GetWeaponType(ID), (2, "Axe"))
            record.weapon_type = 99
            self.assertEqual(Agent.GetWeaponType(ID), (99, "Unknown"))

    def test_the_weapon_derived_members_answer_once_the_pet_check_works(self) -> None:
        """``IsCaster`` and ``IsRanged`` return early for a pet, and now get that far."""

        client = _FakeClient(agent=_living_record(), agent_ids=(ID,))
        with mock.patch("py4gw.client._current_client", client):
            self.assertFalse(Agent.IsCaster(ID))
            self.assertFalse(Agent.IsRanged(ID))

    def test_a_missing_agent_gets_the_source_s_defaults(self) -> None:
        """Each of the eight answers the source's own default when the record is not there."""

        client = _FakeClient(agent=None, agent_ids=(ID,))
        with mock.patch("py4gw.client._current_client", client):
            for member, expected in (
                ("IsSpirit", False),
                ("IsPet", False),
                ("IsMinion", False),
                ("GetAllegiance", (0, "Unknown")),
                ("GetProfessionNames", ("", "")),
                ("GetProfessionShortNames", ("", "")),
                ("GetWeaponType", (0, "Unknown")),
            ):
                with self.subTest(member=member):
                    self.assertEqual(getattr(Agent, member)(ID), expected)

    def test_the_allegiance_enum_comes_from_the_enums_package(self) -> None:
        """The source's ``Allegiance`` is the one used, and nothing declares a second one.

        ``py4gw/context/agent_array.py`` **used to declare an ``AgentAllegiance`` of its own** —
        the same native values under different member names, in neither source project. It is
        gone (2026-09-26): the context imports the source's
        ``enums_src.GameData_enums.Allegiance``, with its own member names, and so do the members
        below. The check reads the modules' own text, so a later edit that declares a second enum
        fails here.
        """

        context_text = Path(
            __import__("py4gw.context.agent_array", fromlist=["x"]).__file__
        ).read_text(encoding="utf-8")
        self.assertIn("from ..enums_src.game_data_enums import Allegiance", context_text)
        self.assertNotIn("class Allegiance", context_text)

        text = Path(agent_module.__file__).read_text(encoding="utf-8")
        self.assertNotIn("class Allegiance", text)
        for member in (
            "IsSpirit",
            "IsPet",
            "IsMinion",
            "GetAllegiance",
            "GetProfessionNames",
            "GetProfessionShortNames",
            "GetWeaponType",
        ):
            with self.subTest(member=member):
                start = text.index(f"def {member}(")
                body = text[start : start + 900]
                self.assertIn("from .enums_src.game_data_enums import", body)


class AgentAdaptationTests(unittest.TestCase):
    """The documented adaptations: no frame cache, no frame tick, no call at import."""

    def test_the_source_declares_the_four_caches_and_the_port_does_not_keep_them(self) -> None:
        """The source's per-frame caches exist (``Agent.py:40-43``); this port has no frame loop.

        Reading a cached agent record would pin a map-scoped dereference for the life of the
        process, because the only invalidation is ``enable``'s per-frame tick — so the three
        ``*ByID`` members read when they are called and the class declares no cache.
        """

        source = SOURCE.read_text(encoding="utf-8") if SOURCE.is_file() else ""
        for name in ("_agent_cache", "_living_cache", "_item_cache", "_gadget_cache"):
            self.assertIn(name, source)
            self.assertFalse(hasattr(Agent, name), msg=name)

        for name in ("GetLivingAgentByID", "GetItemAgentByID", "GetGadgetAgentByID"):
            self.assertIn("per-frame cache", inspect.getdoc(getattr(Agent, name)) or "")

    def test_the_frame_cache_decorator_is_not_applied(self) -> None:
        """``@frame_cache`` is Reforged's and is dropped here (``Agent.py:337``, ``424``).

        The module mentions the decorator in its docstrings — that is the record of the drop — so
        what is pinned is that no member *carries* it: neither member is wrapped, and every member
        is still the plain ``staticmethod`` the source declares under it.
        """

        source = inspect.getsource(agent_module)
        self.assertNotIn("\n    @frame_cache", source)

        for name in ("GetModelID", "GetXY"):
            self.assertIsInstance(vars(Agent)[name], staticmethod, msg=name)
            self.assertIn("@frame_cache", SOURCE.read_text(encoding="utf-8") if SOURCE.is_file() else "n/a")

    def test_the_module_imports_without_the_sources_enable_call(self) -> None:
        """The source calls ``Agent.enable()`` at import (``Agent.py:1649``); this port does not.

        ``enable`` raises here because this project has no frame loop, so calling it at import
        would make the module unimportable.
        """

        self.assertTrue(inspect.ismodule(agent_module))
        with self.assertRaises(NotImplementedError):
            Agent.enable()


if __name__ == "__main__":
    unittest.main()
