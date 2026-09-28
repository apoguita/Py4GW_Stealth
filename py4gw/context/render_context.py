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


def get_viewport_size() -> tuple[float, float]:
    """``GW::render::GetViewportWidth``/``GetViewportHeight`` (``render_methods.cpp:56-63``).

    Native answers both with ``Context::GetRenderContext()->viewport_width``/``viewport_height`` — the context
    its own ``EndScene`` detour assigns (``render.cpp:88``). This port captures that same pointer on that same
    function (`py4gw/game_thread/bridge.py`), so the read here is native's: the captured context's two words.
    A missing capture or an unreadable context answers ``(0.0, 0.0)``, which is native's own
    ``dx_context ? dx_context->viewport_width : 0``.

    ``FramePosition``'s on-screen arithmetic divides by these two numbers (``ui.h:553-561``), which is what
    makes them the frame geometry's remaining input.
    """

    from ..client import require_client

    client = require_client()
    bridge = getattr(client, "_bridge", None)
    if bridge is None:
        return (0.0, 0.0)
    context = int(bridge.render_context_address())
    if not context:
        return (0.0, 0.0)
    size = ctypes.sizeof(GwDxContextStruct)
    raw = client.reader.read(context, size)
    if len(raw) != size:
        return (0.0, 0.0)
    record = GwDxContextStruct.from_buffer_copy(raw)
    return (float(record.viewport_width), float(record.viewport_height))
