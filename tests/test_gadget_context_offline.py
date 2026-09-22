"""Offline layout checks for the external GadgetContext root."""

from __future__ import annotations

import ctypes
import unittest

from py4gw import GadgetContextStruct, GadgetInfoStruct, GWArray


class GadgetContextOfflineTests(unittest.TestCase):
    """Keep gadget root and record layouts fixed-width."""

    def test_native_layout(self) -> None:
        """The native root and gadget-info record are both 0x10 bytes."""

        self.assertEqual(ctypes.sizeof(GadgetInfoStruct), 0x10)
        self.assertEqual(ctypes.sizeof(GadgetContextStruct), 0x10)

    def test_array_size_is_reported(self) -> None:
        """The root exposes its count before any record traversal."""

        context = GadgetContextStruct()
        context.gadget_info_array = GWArray(0x120000, 128, 7, 0)
        self.assertEqual(context.array_size, 7)


if __name__ == "__main__":
    unittest.main(verbosity=2)
