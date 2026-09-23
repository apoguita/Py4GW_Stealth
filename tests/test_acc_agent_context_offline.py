"""Offline source-parity checks for the external agent context."""

from __future__ import annotations

import unittest
import ctypes

from py4gw import (
    AccAgentContext,
    AccAgentContextStruct,
    AgentInfoStruct,
    AgentMovementStruct,
    AgentSummaryInfoStruct,
    AgentSummaryInfoSubStruct,
    Vec3fStruct,
)


class _MemoryReader:
    """Read test bytes from explicit target addresses."""

    def __init__(self, memory: dict[int, bytes] | None = None) -> None:
        self.memory = memory or {}

    def read(self, address: int, size: int) -> bytes:
        value = self.memory.get(address, bytes(size))
        if len(value) != size:
            raise OSError("test reader received an unexpected read size")
        return value


class AccAgentContextParityTests(unittest.TestCase):
    """Keep movement fields and empty-array semantics source-compatible."""

    def test_agent_definition_alias(self) -> None:
        """The source ``agentDef`` name maps to the style-compliant field."""

        movement = AgentMovementStruct()
        movement.agent_def = 1

        self.assertEqual(movement.agentDef, 1)

    def test_empty_arrays_preserve_source_none_results(self) -> None:
        """The source's ordinary array properties return empty lists."""

        context = AccAgentContextStruct()

        self.assertEqual(context.h0000_ptrs, [])
        self.assertEqual(context.h0084_ptrs, [])
        self.assertEqual(context.agent_summary_info_list, [])
        self.assertEqual(context.h00A8_ptrs, [])
        self.assertEqual(context.h00B8_ptrs, [])
        self.assertIsNone(context.agent_movement_ptrs)
        self.assertEqual(context.valid_agents_ids, [])
        self.assertEqual(context.h00F8_ptrs, [])
        self.assertEqual(context.h014C_ptrs, [])
        self.assertEqual(context.h015C_ptrs, [])

    def test_all_fixed_layouts_and_offsets_match_source(self) -> None:
        """Check every field group used by this context's maintained records."""

        self.assertEqual(ctypes.sizeof(Vec3fStruct), 0x0C)
        self.assertEqual(ctypes.sizeof(AgentSummaryInfoSubStruct), 0x1C)
        self.assertEqual(ctypes.sizeof(AgentSummaryInfoStruct), 0x0C)
        self.assertEqual(ctypes.sizeof(AgentMovementStruct), 0x80)
        self.assertEqual(ctypes.sizeof(AgentInfoStruct), 0x38)
        self.assertEqual(ctypes.sizeof(AccAgentContextStruct), 0x1B0)
        layouts = {
            AgentSummaryInfoSubStruct: {
                "h0000": 0x00,
                "h0004": 0x04,
                "gadget_id": 0x08,
                "h000C": 0x0C,
                "gadget_name_enc": 0x10,
                "h0014": 0x14,
                "composite_agent_id": 0x18,
            },
            AgentSummaryInfoStruct: {
                "h0000": 0x00,
                "h0004": 0x04,
                "extra_info_sub_ptr": 0x08,
            },
            AgentMovementStruct: {
                "h0000": 0x00,
                "agent_id": 0x0C,
                "h0010": 0x10,
                "agent_def": 0x1C,
                "h0020": 0x20,
                "moving1": 0x38,
                "h003C": 0x3C,
                "moving2": 0x44,
                "h0048": 0x48,
                "h0064": 0x64,
                "h0070": 0x70,
                "h0074": 0x74,
            },
            AgentInfoStruct: {"h0000": 0x00, "name_enc": 0x34},
            AccAgentContextStruct: {
                "h0000_array": 0x00,
                "h0010": 0x10,
                "h0024": 0x24,
                "h0028": 0x28,
                "h0030": 0x30,
                "h0034": 0x34,
                "h003C": 0x3C,
                "h0040": 0x40,
                "h0048": 0x48,
                "h004C": 0x4C,
                "h0054": 0x54,
                "h0058": 0x58,
                "h0084_array": 0x84,
                "h0094": 0x94,
                "agent_summary_info_array": 0x98,
                "h00A8_array": 0xA8,
                "h00B8_array": 0xB8,
                "rand1": 0xC8,
                "rand2": 0xCC,
                "h00D0": 0xD0,
                "agent_movement_array": 0xE8,
                "h00F8_array": 0xF8,
                "h0108": 0x108,
                "h014C_array": 0x14C,
                "h015C_array": 0x15C,
                "h016C": 0x16C,
                "instance_timer": 0x1AC,
            },
        }
        for structure, fields in layouts.items():
            for name, offset in fields.items():
                self.assertEqual(getattr(structure, name).offset, offset, name)

    def test_native_field_aliases_match_reforged_headers(self) -> None:
        """Native array member spellings point to Reforged's same headers."""

        context = AccAgentContextStruct()
        for native_name, python_name in (
            ("h0000", "h0000_array"),
            ("h0084", "h0084_array"),
            ("agent_summary_info", "agent_summary_info_array"),
            ("h00A8", "h00A8_array"),
            ("h00B8", "h00B8_array"),
            ("agent_movement", "agent_movement_array"),
            ("h00F8", "h00F8_array"),
            ("agent_array1", "h014C_array"),
            ("agent_async_movement", "h015C_array"),
        ):
            self.assertEqual(
                bytes(getattr(context, native_name)),
                bytes(getattr(context, python_name)),
            )

    def test_nested_summary_and_indirect_name_reads(self) -> None:
        """Pointer-backed summary properties read through the supplied reader."""

        sub_address = 0x200000
        name_address = 0x210000
        name_bytes = "Gate Guard\x00".encode("utf-16-le")
        name_bytes += b"\x00" * (24 - len(name_bytes))
        sub = AgentSummaryInfoSubStruct()
        sub.gadget_id = 77
        sub.gadget_name_enc = name_address
        raw_sub = bytes(sub)
        memory = {
            sub_address: raw_sub,
            name_address: name_bytes[:2],
        }
        for index in range(1, len(name_bytes) // 2):
            memory[name_address + index * 2] = name_bytes[index * 2 : index * 2 + 2]
        reader = _MemoryReader(memory)
        summary = AgentSummaryInfoStruct()
        summary.extra_info_sub_ptr = sub_address
        summary = AgentSummaryInfoStruct.from_buffer_copy(bytes(summary)).bind_reader(reader)
        extension = summary.extra_info_sub
        self.assertIsNotNone(extension)
        if extension is None:
            self.fail("The non-null summary pointer should be readable.")
        self.assertEqual(extension.gadget_id, 77)
        self.assertEqual(extension.gadget_name_encoded_str, "Gate Guard")
        self.assertEqual(extension.gadget_name_str, "Gate Guard")

    def test_facade_declares_cache_and_callback_boundary(self) -> None:
        """The source facade remains visible and callback limits are explicit."""

        AccAgentContext.disable()
        self.assertEqual(AccAgentContext.get_ptr(), 0)
        self.assertIsNone(AccAgentContext.get_context())
        with self.assertRaises(NotImplementedError):
            AccAgentContext.enable()


if __name__ == "__main__":
    unittest.main(verbosity=2)
