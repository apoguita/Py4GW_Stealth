"""Source-faithful layout for the native render context."""

from __future__ import annotations

from ..helpers.target_struct import TargetStruct

import ctypes
from ctypes import Structure, c_uint8, c_uint16, c_uint32


class GwDxContextStruct(TargetStruct):
    """The fixed-width x86 layout declared by native ``render.h``.

    ``device`` is a target-process pointer and is therefore stored as a
    32-bit address. The render context's pointer is published through native
    render-hook state; this declaration does not claim to resolve that pointer.
    """

    _pack_ = 1
    _fields_ = [
        ("h0000_1", c_uint8 * 0x128),
        ("h0000", c_uint8 * 24),
        ("h0018", c_uint32),
        ("h001C", c_uint8 * 44),
        ("gpu_name", c_uint16 * 32),
        ("h0088", c_uint8 * 8),
        ("device", c_uint32),
        ("h0094", c_uint8 * 12),
        ("framecount", c_uint32),
        ("h00A4", c_uint8 * 2936),
        ("viewport_width", c_uint32),
        ("viewport_height", c_uint32),
        ("h0C24", c_uint8 * 148),
        ("window_width", c_uint32),
        ("window_height", c_uint32),
        ("h0CC0", c_uint8 * 952),
    ]


assert ctypes.sizeof(GwDxContextStruct) == 0x11A0
