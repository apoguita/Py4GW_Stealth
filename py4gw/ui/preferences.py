"""The client's own preference and frame-limit reads (``GW::ui``).

**Source:** ``src/GW/ui/ui_methods.cpp`` — ``PrefsInitialised`` (``364-367``),
``GetPreference(Constants::EnumPreference)`` (``1432-1436``) and ``GetFrameLimit`` (``1833-1858``),
with the two constants from ``include/GW/common/constants/ui.h``:
``NumberCommandLineParameter::FPS`` = **3** (``Unk1, Unk2, Unk3, FPS``) and
``EnumPreference::FrameLimiter`` = **7** (``CharSortOrder … InterfaceSize, FrameLimiter``,
``Count = 0x8``).

**Why these three members and not the module.** ``Agent.GetInstanceUptime`` divides the agent's
timer by the frame limit, and Reforged reaches it through ``UIManager.GetFPSLimit`` →
``PyUIManager.UIManager.get_frame_limit()`` → **this** function. ``UIManager`` has no ported home
yet, so the port reaches the native function the wrapper ends at, one layer lower; the route
difference is recorded on the member that makes the call.

**Where each input comes from**, exactly as ``GetFrameLimit`` reads it:

| input | native | here |
| --- | --- | --- |
| the command-line FPS | ``g_command_line_number_buffer[FPS]`` | the catalog's ``ui.command_line_number_buffer``, resolved once (a ``.data`` array the client fills at startup, so it reads as zero in the file and carries the value at runtime) |
| vsync and the monitor rate | ``g_get_graphics_renderer_value_func(nullptr, 0xF)`` and ``(nullptr, 0x16)`` | the same function through the catalog, called on the client's own thread with the same two metric ids |
| the frame-limiter preference | ``GetPreference(EnumPreference::FrameLimiter)`` | :func:`get_enum_preference`, which is native's own guard — function resolved, preferences initialised, index below ``Count`` |

Everything here is a read. ``SetFrameLimit`` (``ui_methods.cpp:1860-1864``) writes the client's
command-line buffer and is not ported: nothing in this port's `Player`/`Agent` path sets a limit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..game_thread.shared_block import CallForm

if TYPE_CHECKING:
    from ..client import ConnectedClient


#: ``Constants::EnumPreference::FrameLimiter`` (``common/constants/ui.h:225``).
FRAME_LIMITER = 7

#: ``Constants::EnumPreference::Count`` (``common/constants/ui.h:226``): the guard's own bound.
ENUM_PREFERENCE_COUNT = 0x8

#: ``Constants::NumberCommandLineParameter::FPS`` (``common/constants/ui.h:213``).
COMMAND_LINE_FPS = 3

#: The two renderer metrics ``GetFrameLimit`` asks for (``ui_methods.cpp:1837-1838``).
VSYNC_METRIC = 0xF
MONITOR_REFRESH_METRIC = 0x16

#: The three frame limits the preference selects (``ui_methods.cpp:1840-1852``).
FRAME_LIMIT_30 = 30
FRAME_LIMIT_60 = 60

#: The catalog entry for the client's command-line number array and the resolved-preferences flag.
COMMAND_LINE_BUFFER = "ui.command_line_number_buffer"
PREFERENCES_INITIALIZED = "ui.preferences_initialized_addr"
GET_ENUM_PREFERENCE = "ui.get_enum_preference_func"
GET_GRAPHICS_RENDERER_VALUE = "ui.get_graphics_renderer_value_func"


def read_u32(client: ConnectedClient, address: int) -> int:
    """Read one word of the client, which is what every member here does."""

    return int.from_bytes(client._reader.read(address, 4), "little")


def prefs_initialised() -> bool:
    """``bool PrefsInitialised()`` (``ui_methods.cpp:364-367``): the flag reads ``1``."""

    from ..client import require_client

    client = require_client()
    address = client._resolve(PREFERENCES_INITIALIZED)
    return bool(address) and read_u32(client, address) == 1


def get_enum_preference(preference: int) -> int:
    """``uint32_t GetPreference(Constants::EnumPreference)`` (``ui_methods.cpp:1432-1436``).

    Native's guard is three conditions in one expression — the function resolved, the preferences
    initialised, and the index below ``Count`` — and each of them answers ``0`` rather than raising.
    """

    from ..client import require_client

    client = require_client()
    if not client.resolves(GET_ENUM_PREFERENCE):
        return 0
    if not prefs_initialised():
        return 0
    if preference >= ENUM_PREFERENCE_COUNT:
        return 0
    return int(
        client.call_function(
            GET_ENUM_PREFERENCE, CallForm.U32, int(preference)
        ).value
    )


def get_command_line_number(parameter: int) -> int:
    """``g_command_line_number_buffer[parameter]`` (``ui_methods.cpp:1834-1836``).

    The resolver answers the array's own address — the client fills it at startup, so the file's
    bytes there are zero and the value only exists in the running process — and the read is one
    word past the parameter index. A resolver that did not answer is the source's null pointer,
    which ``GetFrameLimit`` reads as ``0``.
    """

    from ..client import require_client

    client = require_client()
    address = client._resolve(COMMAND_LINE_BUFFER)
    if not address:
        return 0
    return read_u32(client, address + int(parameter) * 4)


def get_renderer_value(metric: int) -> int:
    """``g_get_graphics_renderer_value_func(nullptr, metric)`` (``ui_methods.cpp:1837-1838``)."""

    from ..client import require_client

    client = require_client()
    if not client.resolves(GET_GRAPHICS_RENDERER_VALUE):
        return 0
    return int(
        client.call_function(
            GET_GRAPHICS_RENDERER_VALUE, CallForm.U32_U32, 0, int(metric)
        ).value
    )


def get_frame_limit() -> int:
    """``uint32_t GW::ui::GetFrameLimit()`` (``ui_methods.cpp:1833-1858``), branch for branch.

    The command line wins when it carries an FPS; otherwise the preference selects between 30, 60
    and the monitor's refresh rate; and a vsync'd client never reports more than that refresh rate.
    ``Agent.GetInstanceUptime`` divides by this, which is what Reforged's
    ``UIManager.GetFPSLimit`` returns.
    """

    frame_limit = get_command_line_number(COMMAND_LINE_FPS)
    vsync_enabled = get_renderer_value(VSYNC_METRIC)
    monitor_refresh_rate = get_renderer_value(MONITOR_REFRESH_METRIC)

    if not frame_limit:
        preference = get_enum_preference(FRAME_LIMITER)
        if preference == 1:
            frame_limit = FRAME_LIMIT_30
        elif preference == 2:
            frame_limit = FRAME_LIMIT_60
        elif preference == 3:
            frame_limit = monitor_refresh_rate

    if vsync_enabled and monitor_refresh_rate and frame_limit > monitor_refresh_rate:
        frame_limit = monitor_refresh_rate

    return frame_limit
