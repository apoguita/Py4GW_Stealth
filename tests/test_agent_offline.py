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

The members that raise are pinned as well: each names itself and what it still needs.
"""

from __future__ import annotations

import inspect
import re
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

from py4gw import agent as agent_module
from py4gw.agent import Agent
from py4gw.context.agent_array import (
    AgentGadgetStruct,
    AgentItemStruct,
    AgentLivingStruct,
    AgentStruct,
    AgentType,
    TagInfoStruct,
)
from py4gw.context.world_context import AttributeStruct, NPC_ModelStruct
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


class _FakeClient:
    """The three reads the ported members make, standing in for a connection."""

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

    def read_agent_by_id(self, agent_id: int) -> Any:
        if self.refusal is not None:
            raise self.refusal
        return self.agent

    def read_world_context(self) -> Any:
        return self.world

    def read_agent_array(self) -> Any:
        return _Snapshot(self.agent_ids)


class _Reference:
    """One agent-array reference, with the field the walkers read."""

    def __init__(self, agent_id: int) -> None:
        self.agent_id = agent_id


class _Snapshot:
    """The agent-array snapshot's shape: a tuple of references."""

    def __init__(self, agent_ids: tuple[int, ...]) -> None:
        self.references = tuple(_Reference(agent_id) for agent_id in agent_ids)


class _FakeWorld:
    """A world context with the two reads the ported members make."""

    def __init__(
        self,
        attributes: list[AttributeStruct] | None = None,
        npc_models: list[NPC_ModelStruct] | None = None,
    ) -> None:
        self._attributes = attributes or []
        self._npc_models = npc_models or []

    def get_attributes_by_agent_id(self, agent_id: int) -> list[AttributeStruct]:
        return self._attributes

    @property
    def npc_models(self) -> list[NPC_ModelStruct] | None:
        return self._npc_models


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
    """One item agent record."""

    record = AgentItemStruct()
    record.type = int(AgentType.ITEM)
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
        """``ILLUSIONARY_WEAPONRY_ID`` and ``DEAD_HEALTH_EPSILON`` (``Agent.py:14-18``)."""

        self.assertEqual(Agent.ILLUSIONARY_WEAPONRY_ID, 0)
        self.assertEqual(Agent.DEAD_HEALTH_EPSILON, 1.0 / 400.0)

    def test_every_member_is_a_staticmethod(self) -> None:
        """The source declares every member as ``@staticmethod``; none takes ``self``."""

        for name, value in vars(Agent).items():
            if name.startswith("__") or name in ("ILLUSIONARY_WEAPONRY_ID", "DEAD_HEALTH_EPSILON"):
                continue
            self.assertIsInstance(value, staticmethod, msg=name)


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

    def test_a_refused_read_is_the_sources_missing_agent(self) -> None:
        """The port's reader refuses a non-positive id where the binding answers null.

        ``AgentArray.GetAgentByID`` returns ``None`` for an unknown id including ``0``
        (``AgentContext.py:1477-1497``); the ported reader raises ``ValueError`` there, and
        :meth:`Agent.GetAgentByID` maps it to the source's ``None``.
        """

        refuser = _FakeClient(refusal=ValueError("agent_id must be positive."))
        with mock.patch("py4gw.client._current_client", refuser):
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


class AgentBlockedTests(unittest.TestCase):
    """The members that raise name themselves and what they still need."""

    #: ``(member, args, the requirement the message must name)``. Each of these bodies needs
    #: something this port does not have, so the member raises instead of answering.
    BLOCKED: tuple[tuple[str, tuple[Any, ...], str], ...] = (
        ("_invalidate_property_cache", (), "the four per-frame agent caches"),
        ("enable", (), "PyCallback.PyCallback.Register"),
        ("GetNameByID", (ID,), "PyAgent.get_agent_enc_name"),
        ("GetEncNameByID", (ID,), "PyAgent.get_agent_enc_name"),
        ("GetEncNameStrByID", (ID,), "PyAgent.get_agent_enc_name"),
        ("IsMartial", (ID,), "Effects.HasEffect"),
        ("IsMelee", (ID,), "Effects.HasEffect"),
        ("GetProfessionsTexturePaths", (ID,), "PySystem.Console.get_projects_path"),
    )

    #: ``(member, args, the member the raise belongs to)``: these bodies are the source's, and the
    #: member they call is the one that raises — the source's own call graph, not a duplicated
    #: requirement. It is shorter than it was: ``IsCaster`` and ``IsRanged`` called
    #: ``Agent.IsPet``, which the ported ``enums_src`` enums unblocked, so both answer now.
    TRANSITIVE: tuple[tuple[str, tuple[Any, ...], str], ...] = (
        ("IsNameReady", (ID,), "Agent.GetNameByID"),
        ("GetAgentIDByName", ("Bob",), "Agent.GetNameByID"),
        ("GetAgentIDByEncString", ("x",), "Agent.GetEncNameStrByID"),
        ("GetModelIDByEncString", ("x",), "Agent.GetEncNameStrByID"),
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

    def test_a_body_that_calls_a_blocked_member_raises_from_that_member(self) -> None:
        """The ported bodies keep the source's calls, so the raise names the inner member."""

        client = _FakeClient(agent=_living_record(), agent_ids=(ID,))
        with mock.patch("py4gw.client._current_client", client):
            for member, args, owner in self.TRANSITIVE:
                with self.subTest(member=member):
                    with self.assertRaises(NotImplementedError) as caught:
                        getattr(Agent, member)(*args)
                    self.assertIn(owner, str(caught.exception))


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

    def test_the_agents_own_allegiance_enum_is_not_the_one_used(self) -> None:
        """The substitute the earlier attempt refused is still not wired in (``agent_array.py``).

        ``py4gw/context/agent_array.py`` declares an ``AgentAllegiance`` with the same native
        values, which is **not** in either source project; the members read the source's
        ``enums_src.GameData_enums.Allegiance`` instead, and this pins that they do. The check is
        on the module the members import, read out of their own source text, so a later edit that
        swaps the enum back to the port's own fails here.
        """

        text = Path(agent_module.__file__).read_text(encoding="utf-8")
        self.assertNotIn("AgentAllegiance", text)
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
