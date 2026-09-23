"""Offline checks for the native render-context declaration."""

from __future__ import annotations

import ctypes
import unittest

from py4gw import GwDxContextStruct


class RenderContextOfflineTests(unittest.TestCase):
    """Keep the render-context field order and x86 layout source-faithful."""

    def test_native_field_names_and_order(self) -> None:
        """Every field retains its spelling and position from render.h."""

        self.assertEqual(
            [field[0] for field in GwDxContextStruct._fields_],
            [
                "h0000_1",
                "h0000",
                "h0018",
                "h001C",
                "gpu_name",
                "h0088",
                "device",
                "h0094",
                "framecount",
                "h00A4",
                "viewport_width",
                "viewport_height",
                "h0C24",
                "window_width",
                "window_height",
                "h0CC0",
            ],
        )

    def test_x86_offsets_and_size(self) -> None:
        """Target pointers and Windows wide characters keep x86 widths."""

        self.assertEqual(ctypes.sizeof(GwDxContextStruct), 0x11A0)
        expected_offsets = {
            "h0000": 0x128,
            "h0018": 0x140,
            "gpu_name": 0x170,
            "device": 0x1B8,
            "framecount": 0x1C8,
            "viewport_width": 0xD44,
            "viewport_height": 0xD48,
            "window_width": 0xDE0,
            "window_height": 0xDE4,
        }
        for field_name, expected in expected_offsets.items():
            with self.subTest(field=field_name):
                self.assertEqual(getattr(GwDxContextStruct, field_name).offset, expected)
        self.assertEqual(GwDxContextStruct.device.size, 4)
        self.assertEqual(GwDxContextStruct.gpu_name.size, 0x40)


if __name__ == "__main__":
    unittest.main(verbosity=2)
