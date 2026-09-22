"""Offline layout checks for the external AccountContext root."""

from __future__ import annotations

import ctypes
import unittest

from py4gw import AccountContextStruct, AccountUnlockedCountStruct, GWArray


class _Memory:
    """Deterministic byte store for bounded account-array reads."""

    def __init__(self) -> None:
        self._blocks: dict[int, bytes] = {}

    def add(self, address: int, value: bytes) -> None:
        self._blocks[address] = value

    def read(self, address: int, size: int) -> bytes:
        for start, value in self._blocks.items():
            if start <= address and address + size <= start + len(value):
                offset = address - start
                return value[offset : offset + size]
        raise AssertionError(f"unmapped read: 0x{address:08X}+{size}")


class AccountContextOfflineTests(unittest.TestCase):
    """Keep account records fixed-width and root reads bounded."""

    def test_native_layout(self) -> None:
        """The root and nested records match the native x86 layout."""

        self.assertEqual(ctypes.sizeof(AccountContextStruct), 0x138)
        self.assertEqual(AccountContextStruct.unlocked_pvp_heros.offset, 0xB4)
        self.assertEqual(AccountContextStruct.h00C4.offset, 0xC4)
        self.assertEqual(AccountContextStruct.unlocked_pvp_item_info.offset, 0xD4)
        self.assertEqual(AccountContextStruct.unlocked_pvp_items.offset, 0xE4)
        self.assertEqual(AccountContextStruct.unlocked_account_skills.offset, 0x124)
        self.assertEqual(AccountContextStruct.account_flags.offset, 0x134)

    def test_array_sizes_do_not_traverse_remote_data(self) -> None:
        """Header counts are available without reading any child array."""

        context = AccountContextStruct()
        context.account_unlocked_counts = GWArray(0x100000, 32, 4, 0)
        context.unlocked_account_skills = GWArray(0x110000, 512, 18, 0)
        self.assertEqual(context.array_sizes["account_unlocked_counts"], 4)
        self.assertEqual(context.array_sizes["unlocked_account_skills"], 18)

    def test_source_account_queries_read_bounded_arrays(self) -> None:
        """Native account unlock counters and skill bits are externally readable."""

        memory = _Memory()
        count_address = 0x00200000
        skill_address = 0x00210000
        count = AccountUnlockedCountStruct()
        count.id = 0x83
        count.unknown_1 = 3
        memory.add(count_address, bytes(count))
        memory.add(skill_address, (1 << 7).to_bytes(4, "little"))

        context = AccountContextStruct().bind_reader(memory)
        context.account_unlocked_counts = GWArray(count_address, 1, 1, 0)
        context.unlocked_account_skills = GWArray(skill_address, 1, 1, 0)

        self.assertEqual(context.material_storage_stack_size, 1000)
        self.assertTrue(context.is_account_skill_unlocked(7))
        self.assertFalse(context.is_account_skill_unlocked(8))
        unlock = context.get_unlocked_count(0x83)
        self.assertIsNotNone(unlock)
        assert unlock is not None
        self.assertEqual(unlock.unk1, 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
