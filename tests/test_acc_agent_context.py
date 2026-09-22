"""Live Guild Wars tests for the external AccAgentContext reader."""

from __future__ import annotations

import ctypes
import unittest

from py4gw import (
    AccAgentContext,
    AccAgentContextStruct,
    AgentMovementStruct,
    AgentSummaryInfoStruct,
    AgentSummaryInfoSubStruct,
    GameContext,
    PatternCatalog,
    ProcessMemoryReader,
    RemoteScanner,
    Win32,
)


class LiveAccAgentContextTests(unittest.TestCase):
    """Verify the native AgentContext surface against Guild Wars."""

    @classmethod
    def setUpClass(cls) -> None:
        """Open the first discovered client with read-only access."""

        cls.win32 = Win32()
        clients = cls.win32.find_guild_wars()
        if not clients:
            raise unittest.SkipTest("Start Guild Wars before running this test.")

        cls.pid = int(clients[0]["pid"])
        module = cls.win32.get_main_module(cls.pid)
        cls.reader = ProcessMemoryReader(cls.win32, cls.pid)
        cls.scanner = RemoteScanner(
            cls.reader,
            int(module["base_address"]),
            int(module["size"]),
        )
        cls.scanner.initialize()
        patterns = PatternCatalog.from_directory("offsets")
        cls.game_context = GameContext(cls.reader, cls.scanner, patterns)
        cls.game_context.initialize()
        cls.context = AccAgentContext(cls.reader, cls.game_context)

    @classmethod
    def tearDownClass(cls) -> None:
        """Close the selected process handle after the live checks."""

        if hasattr(cls, "reader"):
            cls.reader.close()

    def test_layout_matches_native_agent_context(self) -> None:
        """Keep the maintained nested records at their native offsets."""

        self.assertEqual(ctypes.sizeof(AgentSummaryInfoSubStruct), 0x1C)
        self.assertEqual(ctypes.sizeof(AgentSummaryInfoStruct), 0x0C)
        self.assertEqual(ctypes.sizeof(AgentMovementStruct), 0x80)
        self.assertEqual(ctypes.sizeof(AccAgentContextStruct), 0x1B0)
        self.assertEqual(AccAgentContextStruct.agent_summary_info_array.offset, 0x98)
        self.assertEqual(AccAgentContextStruct.agent_movement_array.offset, 0xE8)
        self.assertEqual(AccAgentContextStruct.instance_timer.offset, 0x1AC)

    def test_resolves_live_agent_context(self) -> None:
        """Follow the direct GameContext.agent pointer."""

        address = self.context.resolve_address()
        if address is None:
            self.skipTest("The connected client has no active AgentContext.")
        self.assertGreater(address, 0)
        print(f"Live AgentContext: 0x{address:08X}")

    def test_reads_live_agent_context_and_nested_arrays(self) -> None:
        """Read the maintained arrays and movement records."""

        snapshot = self.context.read()
        if snapshot is None:
            self.skipTest("The connected client has no active AgentContext.")

        self.assertEqual(len(bytes(snapshot)), 0x1B0)
        summaries = snapshot.agent_summary_info_list
        movement = snapshot.agent_movement_ptrs
        valid_ids = snapshot.valid_agents_ids
        if summaries is not None:
            self.assertLessEqual(
                len(summaries), int(snapshot.agent_summary_info_array.m_capacity)
            )
        if movement is not None:
            self.assertLessEqual(
                len(movement), int(snapshot.agent_movement_array.m_capacity)
            )
        self.assertTrue(all(isinstance(value, int) for value in valid_ids))
        print(
            "Live agents: "
            f"summary={len(summaries or [])}, movement={len(movement or [])}, "
            f"valid_ids={len(valid_ids)}, timer={int(snapshot.instance_timer)}"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
