"""Live checks for the bounded external AgentArray reader."""

from __future__ import annotations

import unittest
import time

import py4gw

from py4gw import (
    AgentAllegiance,
    AgentGadgetStruct,
    AgentItemStruct,
    AgentLivingStruct,
    PerfCounter,
    Win32,
)


class LiveAgentArrayTests(unittest.TestCase):
    """Verify agent references against a running Guild Wars client."""

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
        cls.connection_perf = PerfCounter()
        cls.client = py4gw.connect(clients[0])

    @classmethod
    def tearDownClass(cls) -> None:
        """Release the connection opened for the live checks."""

        py4gw.disconnect()

    def test_resolves_live_agent_array(self) -> None:
        """Resolve the native agent-array address from the JSON resolver."""

        address = self.client.agent_array.cached_array_address
        self.assertIsNotNone(address)
        self.assertGreater(address or 0, 0)
        print(f"Live AgentArray: 0x{address or 0:08X}")
        print(
            "  agent_array.resolver: "
            f"{self.connection_perf.calculate_report('agent_array.resolver').avg:.3f} ms"
        )

    def test_reads_bounded_live_references(self) -> None:
        """Traverse pointers and apply the native movement validity gate."""

        perf = PerfCounter()
        snapshot = self.client.read_agent_array(perf)
        if snapshot is None:
            self.skipTest("The connected client has no active AgentContext.")

        self.assertGreaterEqual(snapshot.reported_size, snapshot.count)
        self.assertLessEqual(snapshot.count, self.client.agent_array.max_references)
        self.assertTrue(all(reference.agent_id > 0 for reference in snapshot.references))
        self.assertTrue(all(reference.address >= 0x10000 for reference in snapshot.references))
        self.assertTrue(
            all(reference.slot < snapshot.reported_size for reference in snapshot.references)
        )
        self.assertEqual(
            len(snapshot.living)
            + len(snapshot.items)
            + len(snapshot.gadgets)
            + sum(
                1
                for reference in snapshot.references
                if not reference.is_living
                and not reference.is_item
                and not reference.is_gadget
            ),
            snapshot.count,
        )
        self.assertEqual(
            len(snapshot.dead_allies) <= len(snapshot.allies), True
        )
        self.assertEqual(
            len(snapshot.dead_enemies) <= len(snapshot.enemies), True
        )
        self.assertTrue(
            all(
                reference.allegiance is None
                or isinstance(reference.allegiance, AgentAllegiance)
                for reference in snapshot.references
            )
        )
        print(
            "Live AgentArray: "
            f"size={snapshot.reported_size}, capacity={snapshot.reported_capacity}, "
            f"scanned={snapshot.scanned_slots}, non_null={snapshot.non_null_slots}, "
            f"accepted={snapshot.count}, stale={snapshot.stale_slots}, "
            f"unreadable={snapshot.unreadable_slots}, truncated={snapshot.truncated}, "
            f"living={len(snapshot.living)}, items={len(snapshot.items)}, "
            f"gadgets={len(snapshot.gadgets)}, enemies={len(snapshot.enemies)}, "
            f"allies={len(snapshot.allies)}, unknown_allegiance="
            f"{sum(reference.allegiance is None for reference in snapshot.living)}, "
            f"dead_allies={len(snapshot.dead_allies)}, "
            f"dead_enemies={len(snapshot.dead_enemies)}, "
            f"owned_items={len(snapshot.owned_items)}, "
            f"elapsed={perf.calculate_report('agent_array.read').avg:.3f} ms"
        )
        for metric_name in (
            "agent_array.context_read",
            "agent_array.pointer_table",
            "agent_array.movement_table",
            "agent_array.classification",
        ):
            report = perf.calculate_report(metric_name)
            print(f"  {metric_name}: {report.avg:.3f} ms")

    def test_exposes_source_category_methods_and_struct_view(self) -> None:
        """Expose the source AgentArray category names over one snapshot."""

        snapshot = self.client.read_agent_array()
        if snapshot is None:
            self.skipTest("The connected client has no active AgentContext.")
        cache_started = time.perf_counter_ns()
        context = self.client.agent_array.read_context()
        cache_elapsed_ms = (time.perf_counter_ns() - cache_started) / 1_000_000
        self.assertIsNotNone(context)
        assert context is not None
        self.assertEqual(context.GetAgentArray(), snapshot.GetAgentArray())
        self.assertEqual(context.GetAllyArray(), snapshot.GetAllyArray())
        self.assertEqual(context.GetEnemyArray(), snapshot.GetEnemyArray())
        self.assertEqual(context.GetItemAgentArray(), snapshot.GetItemAgentArray())
        self.assertEqual(context.GetGadgetAgentArray(), snapshot.GetGadgetAgentArray())
        self.assertEqual(
            context.GetOwnedItemAgentArray(), snapshot.GetOwnedItemAgentArray()
        )
        if context.GetAgentArray():
            first_id = context.GetAgentArray()[0]
            first_agent = context.GetAgentByID(first_id)
            self.assertIsNotNone(first_agent)
            assert first_agent is not None
            self.assertEqual(int(first_agent.agent_id), first_id)
            self.assertIs(context.GetAgentByID(first_id), first_agent)
        self.assertLessEqual(len(context.raw_agents), self.client.agent_array.max_pointer_slots)
        print(
            "Live AgentArray source view: "
            f"cache_build={cache_elapsed_ms:.3f} ms, "
            f"all={len(context.GetAgentArray())}, "
            f"ally={len(context.GetAllyArray())}, "
            f"enemy={len(context.GetEnemyArray())}, "
            f"items={len(context.GetItemAgentArray())}, "
            f"gadgets={len(context.GetGadgetAgentArray())}, "
            f"raw={len(context.raw_agents)}"
        )

    def test_reads_one_complete_live_agent(self) -> None:
        """Materialize only one selected typed agent record."""

        snapshot = self.client.read_agent_array()
        if snapshot is None or not snapshot.references:
            self.skipTest("The connected client has no current agent references.")

        reference = snapshot.references[0]
        perf = PerfCounter()
        record = self.client.read_agent(reference, perf)
        if record is None:
            self.skipTest("The agent read is gated: the map is not ready.")

        self.assertEqual(int(record.agent_id), reference.agent_id)
        self.assertEqual(record.remote_address, reference.address)
        self.assertEqual(record.position[2] >= 0, True)
        if isinstance(record, AgentLivingStruct):
            self.assertIsInstance(record.allegiance_enum, AgentAllegiance)
        elif isinstance(record, AgentItemStruct):
            self.assertGreaterEqual(int(record.item_id), 0)
        elif isinstance(record, AgentGadgetStruct):
            self.assertGreaterEqual(int(record.gadget_id), 0)
        print(
            "Live Agent detail: "
            f"id={int(record.agent_id)}, kind={reference.kind.value}, "
            f"type=0x{int(record.type):X}, position={record.position}, "
            f"validation={perf.calculate_report('agent_array.reference_validation').avg:.3f} ms, "
            f"record={perf.calculate_report('agent_array.agent_record').avg:.3f} ms"
        )

    def test_refreshes_complete_living_snapshot(self) -> None:
        """Capture complete living records for frequent local queries."""

        perf = PerfCounter()
        snapshot = self.client.refresh_living_agents(perf)
        if snapshot is None:
            self.skipTest("The connected client has no active AgentContext.")

        self.assertGreater(snapshot.count, 0)
        self.assertTrue(all(isinstance(record, AgentLivingStruct) for record in snapshot.records))
        first = snapshot.records[0]
        self.assertIs(self.client.get_living_agent(int(first.agent_id)), first)
        self.assertGreaterEqual(int(first.effects), 0)
        print(
            "Live living snapshot: "
            f"generation={snapshot.generation}, records={snapshot.count}, "
            f"stale={snapshot.stale_count}, unreadable={snapshot.unreadable_count}, "
            f"effects_first=0x{int(first.effects):08X}, "
            f"refresh={perf.calculate_report('agent_array.living_refresh').avg:.3f} ms, "
            f"age={snapshot.age_ms:.3f} ms"
        )

    def test_reads_live_effect_surface(self) -> None:
        """Expose the native effects bitmap and visible-effect list."""

        snapshot = self.client.living_snapshot
        if snapshot is None:
            snapshot = self.client.refresh_living_agents()
        if snapshot is None or not snapshot.records:
            self.skipTest("The connected client has no living-agent records.")

        record = snapshot.records[0]
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

        snapshot = self.client.living_snapshot
        if snapshot is None:
            snapshot = self.client.refresh_living_agents()
        if snapshot is None or not snapshot.records:
            self.skipTest("The connected client has no living-agent records.")

        record = snapshot.records[0]
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
