"""Live checks for the external AgentArray reader."""

from __future__ import annotations

import unittest
import time

import py4gw

from py4gw import (
    Allegiance,
    AgentGadgetStruct,
    AgentItemStruct,
    AgentLivingStruct,
    Win32,
)


class LiveAgentArrayTests(unittest.TestCase):
    """Verify the source-shaped agent array against a running Guild Wars client."""

    @classmethod
    def setUpClass(cls) -> None:
        """Connect to the first discovered client with read-only access.

        ``py4gw.connect`` is used rather than constructing ``ConnectedClient``
        directly, because the accessor classes (``Map``, ``Party``, ``Player``)
        are namespace members that resolve the current client, exactly as
        Reforged's are namespace members over its process-global contexts. An
        unregistered client leaves ``Map.IsMapReady()`` with nothing to answer
        for, and the agent-array cache validator asks it on every rebuild.
        """

        win32 = Win32()
        clients = win32.find_guild_wars()
        if not clients:
            raise unittest.SkipTest("Start Guild Wars before running this test.")
        if not win32.is_elevated():
            raise unittest.SkipTest(
                "This suite connects to the client, and connecting requires an "
                "elevated controller. Run it from an elevated shell."
            )
        cls.client = py4gw.connect(clients[0])

    @classmethod
    def tearDownClass(cls) -> None:
        """Release the connection opened for the live checks."""

        py4gw.disconnect()

    def test_resolves_live_agent_array(self) -> None:
        """Resolve the native agent-array address from the JSON resolver."""

        started = time.perf_counter_ns()
        address = self.client.agent_array.initialize()
        elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000

        self.assertEqual(address, self.client.agent_array.cached_array_address)
        self.assertGreater(address, 0)
        print(f"Live AgentArray: 0x{address:08X}")
        print(f"  resolve (cached after connect): {elapsed_ms:.3f} ms")

    def test_reads_the_live_agent_array_header(self) -> None:
        """Read the maintained header into a local copy, externally.

        The source's ``AgentArrayStruct`` is the client's own structure, kept by its
        ``UpdatePtr`` callback (``AgentContext.py:1405-1415``). This port reads the
        fixed-width ``GWArray<Agent*>`` header addressing it into a copy and
        materializes the records that header describes through the same view. What is
        checked here is that the copy describes the array the client keeps: header
        bounds, one entry per advertised slot, and nonzero ids.
        """

        started = time.perf_counter_ns()
        context = self.client.agent_array.read_context()
        elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000

        self.assertIsNotNone(context)
        assert context is not None
        self.assertIs(self.client.agent_array.get_context(), context)

        size = int(context.agent_array.m_size)
        capacity = int(context.agent_array.m_capacity)
        self.assertGreater(capacity, 0)
        self.assertGreater(size, 0)
        self.assertLessEqual(size, capacity)
        self.assertGreater(int(context.agent_array.m_buffer), 0x10000)

        agents = context.raw_agents
        self.assertEqual(len(agents), size)
        present = [agent for agent in agents if agent is not None]
        self.assertTrue(all(int(agent.agent_id) > 0 for agent in present))

        print(
            "Live AgentArray header: "
            f"buffer=0x{int(context.agent_array.m_buffer):08X}, "
            f"size={size}, capacity={capacity}, "
            f"non_null={len(present)}, read={elapsed_ms:.3f} ms"
        )

    def test_exposes_source_category_methods(self) -> None:
        """Expose the source ``AgentArrayStruct`` category methods over one view."""

        context = self.client.agent_array.get_context()
        if context is None:
            self.skipTest("The connected client has no active AgentContext.")

        from py4gw.agent_array import AgentArray

        agents = context.GetAgentArray()
        self.assertEqual(agents, AgentArray.GetAgentArray())
        self.assertEqual(
            len(agents),
            len(set(agents)),
            "the source's category lists hold each id once",
        )

        for name, category in (
            ("ally", context.GetAllyArray()),
            ("neutral", context.GetNeutralArray()),
            ("enemy", context.GetEnemyArray()),
            ("spirit_pet", context.GetSpiritPetArray()),
            ("minion", context.GetMinionArray()),
            ("npc_minipet", context.GetNPCMinipetArray()),
            ("item", context.GetItemAgentArray()),
            ("owned_item", context.GetOwnedItemAgentArray()),
            ("gadget", context.GetGadgetAgentArray()),
            ("dead_ally", context.GetDeadAllyArray()),
            ("dead_enemy", context.GetDeadEnemyArray()),
        ):
            with self.subTest(category=name):
                self.assertTrue(set(category) <= set(agents))

        self.assertTrue(
            set(context.GetOwnedItemAgentArray()) <= set(context.GetItemAgentArray())
        )
        self.assertTrue(
            set(context.GetDeadAllyArray()) <= set(context.GetAllyArray())
        )
        self.assertTrue(
            set(context.GetDeadEnemyArray()) <= set(context.GetEnemyArray())
        )

        if agents:
            first_id = int(agents[0])
            first_agent = context.GetAgentByID(first_id)
            self.assertIsNotNone(first_agent)
            assert first_agent is not None
            self.assertEqual(int(first_agent.agent_id), first_id)
            self.assertIs(context.GetAgentByID(first_id), first_agent)

        print(
            "Live AgentArray source view: "
            f"all={len(agents)}, ally={len(context.GetAllyArray())}, "
            f"neutral={len(context.GetNeutralArray())}, "
            f"enemy={len(context.GetEnemyArray())}, "
            f"dead_ally={len(context.GetDeadAllyArray())}, "
            f"dead_enemy={len(context.GetDeadEnemyArray())}, "
            f"items={len(context.GetItemAgentArray())}, "
            f"owned_items={len(context.GetOwnedItemAgentArray())}, "
            f"gadgets={len(context.GetGadgetAgentArray())}, "
            f"raw={len(context.raw_agents)}"
        )

    def test_reads_one_complete_live_agent(self) -> None:
        """Materialize one selected typed agent record through the source's own lookup."""

        from py4gw.agent import Agent

        context = self.client.agent_array.get_context()
        if context is None:
            self.skipTest("The connected client has no active AgentContext.")
        agents = context.GetAgentArray()
        if not agents:
            self.skipTest("The connected client has no current agents.")

        agent_id = int(agents[0])
        started = time.perf_counter_ns()
        record = Agent.GetAgentByID(agent_id)
        elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
        if record is None:
            self.skipTest("The agent read is gated: the map is not ready.")

        self.assertEqual(int(record.agent_id), agent_id)
        self.assertGreater(int(record.type), 0)
        self.assertGreaterEqual(record.position[2], 0)
        if isinstance(record, AgentLivingStruct):
            self.assertIsInstance(record.allegiance_enum, Allegiance)
        elif isinstance(record, AgentItemStruct):
            self.assertGreaterEqual(int(record.item_id), 0)
        elif isinstance(record, AgentGadgetStruct):
            self.assertGreaterEqual(int(record.gadget_id), 0)
        print(
            "Live Agent detail: "
            f"id={agent_id}, type=0x{int(record.type):X}, "
            f"position={record.position}, read={elapsed_ms:.3f} ms"
        )

    def test_reads_live_effect_surface(self) -> None:
        """Expose the native effects bitmap and visible-effect list."""

        record = self._first_living_record()
        visible_effects = record.visible_effects
        self.assertGreaterEqual(int(record.effects), 0)
        self.assertTrue(all(int(effect.effect_id) >= 0 for effect in visible_effects))
        print(
            "Live effects: "
            f"agent_id={int(record.agent_id)}, bitmap=0x{int(record.effects):08X}, "
            f"bleeding={record.is_bleeding}, poisoned={record.is_poisoned}, "
            f"hexed={record.is_hexed}, visible_count={len(visible_effects)}"
        )

    def test_reads_live_equipment_and_tags(self) -> None:
        """Read optional equipment and tag records through target pointers."""

        record = self._first_living_record()
        equipment = record.equipment
        tags = record.tags
        if equipment is not None:
            self.assertEqual(len(equipment.item_ids), 9)
        if tags is not None:
            self.assertGreaterEqual(int(tags.level), 0)
        print(
            "Live living nested data: "
            f"agent_id={int(record.agent_id)}, equipment={equipment is not None}, "
            f"tags={tags is not None}, "
            f"item_ids={equipment.item_ids if equipment is not None else ()}"
        )

    def _first_living_record(self) -> AgentLivingStruct:
        """Return the first living record the client's own lookup answers with."""

        from py4gw.agent import Agent

        context = self.client.agent_array.get_context()
        if context is None:
            self.skipTest("The connected client has no active AgentContext.")
        for agent_id in context.GetAgentArray():
            record = Agent.GetAgentByID(int(agent_id))
            if isinstance(record, AgentLivingStruct):
                return record
        self.skipTest("The connected client has no living agent records.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
