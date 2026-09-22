"""Offline source-parity checks for the external agent context."""

from __future__ import annotations

import unittest

from py4gw import AccAgentContextStruct, AgentMovementStruct


class AccAgentContextParityTests(unittest.TestCase):
    """Keep movement fields and empty-array semantics source-compatible."""

    def test_agent_definition_alias(self) -> None:
        """The source ``agentDef`` name maps to the style-compliant field."""

        movement = AgentMovementStruct()
        movement.agent_def = 1

        self.assertEqual(movement.agentDef, 1)

    def test_empty_arrays_preserve_source_none_results(self) -> None:
        """Empty source arrays are reported as ``None`` rather than fabricated lists."""

        context = AccAgentContextStruct()

        self.assertIsNone(context.h0000_ptrs)
        self.assertIsNone(context.agent_summary_info_list)
        self.assertIsNone(context.agent_movement_ptrs)


if __name__ == "__main__":
    unittest.main(verbosity=2)
