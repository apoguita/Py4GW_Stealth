"""The client's own preference and frame-limit reads (``GW::ui``).

**Source:** ``src/GW/ui/ui_methods.cpp`` — ``PrefsInitialised`` (``364-367``),
``GetPreference(Constants::EnumPreference)`` (``1432-1436``) and ``GetFrameLimit`` (``1833-1858``),
with the two constants from ``include/GW/common/constants/ui.h``:
``NumberCommandLineParameter::FPS`` = **3** (``Unk1, Unk2, Unk3, FPS``) and
``EnumPreference::FrameLimiter`` = **7** (``CharSortOrder … InterfaceSize, FrameLimiter``,
``Count = 0x8``).

**Why these members and not the module.** ``Agent.GetInstanceUptime`` divides the agent's timer by
the frame limit, and Reforged reaches it through ``UIManager.GetFPSLimit`` →
``PyUIManager.UIManager.get_frame_limit()`` → **this** function. When this module was written
``UIManager`` had no ported home, so the port reached the native function the wrapper ends at, one
layer lower. **It has one since 2026-09-27** (``py4gw/ui_manager.py``), and that class's members call
the functions here — the same route Reforged takes, with the binding in between named. The preference
getters and ``set_frame_limit`` were added with it, for the members that reach them:
``UIManager.GetTextLanguage`` (``GetPreference(NumberPreference::TextLanguage)``),
``GetIntPreference``, ``GetStringPreference``, ``GetBoolPreference`` and ``SetFPSLimit``.

**Where each input comes from**, exactly as ``GetFrameLimit`` reads it:

| input | native | here |
| --- | --- | --- |
| the command-line FPS | ``g_command_line_number_buffer[FPS]`` | the catalog's ``ui.command_line_number_buffer``, resolved once (a ``.data`` array the client fills at startup, so it reads as zero in the file and carries the value at runtime) |
| vsync and the monitor rate | ``g_get_graphics_renderer_value_func(nullptr, 0xF)`` and ``(nullptr, 0x16)`` | the same function through the catalog, called on the client's own thread with the same two metric ids |
| the frame-limiter preference | ``GetPreference(EnumPreference::FrameLimiter)`` | :func:`get_enum_preference`, which is native's own guard — function resolved, preferences initialised, index below ``Count`` |

Everything here is a read except ``set_frame_limit``. ``SetFrameLimit``
(``ui_methods.cpp:1860-1864``) is one write into the client's command-line buffer, and it landed with
``UIManager.SetFPSLimit`` — the member that needs it; the write goes through the payload's
``WRITE_MEMORY`` operation on the game's own thread, which is where Native's ``Enqueue`` runs it.
"""

from __future__ import annotations

import struct
from typing import TYPE_CHECKING

from ..game_thread.shared_block import CallForm, Operation

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

#: The three remaining typed getters, each with its own resolver and its own bound
#: (``ui_methods.cpp:1450-1466``, ``common/constants/ui.h:229-321``).
GET_NUMBER_PREFERENCE = "ui.get_number_preference_func"
GET_FLAG_PREFERENCE = "ui.get_flag_preference_func"
GET_STRING_PREFERENCE = "ui.get_string_preference_func"
NUMBER_PREFERENCE_COUNT = 44
FLAG_PREFERENCE_COUNT = 0x5E
STRING_PREFERENCE_COUNT = 0x3

#: ``Constants::NumberPreference::TextLanguage`` (``common/constants/ui.h:247``), the index
#: ``GetTextLanguage`` reads (``ui_methods.cpp:1428-1430``).
TEXT_LANGUAGE = 10

#: How many code units of a preference string this port reads. Native hands the client's own
#: ``wchar_t*`` straight to Python and converts it unbounded (``ui_bindings.cpp:1043-1045``,
#: ``SafeWide``); an external reader cannot walk a pointer without a bound, so the port uses the
#: same one it reads every wide string with (``FrameArray.read_wide_string``'s label limit), and a
#: string that is not one costs a bounded number of reads rather than an unbounded one.
STRING_PREFERENCE_LIMIT = 32768

#: The three typed setters and the functions their follow-up work calls (``ui_methods.cpp:1468-1677``).
#: Every one of them is a catalog entry in ``offsets/ui.json``.
SET_ENUM_PREFERENCE = "ui.set_enum_preference_func"
SET_NUMBER_PREFERENCE = "ui.set_number_preference_func"
SET_STRING_PREFERENCE = "ui.set_string_preference_func"
SET_FLAG_PREFERENCE = "ui.set_flag_preference_func"
NUMBER_PREFERENCE_OPTIONS = "ui.number_preference_options_addr"
SET_GRAPHICS_RENDERER_VALUE = "ui.set_graphics_renderer_value_func"
SET_IN_GAME_STATIC_PREFERENCE = "ui.set_in_game_static_preference_func"
SET_IN_GAME_SHADOW_QUALITY = "ui.set_in_game_shadow_quality_func"
SET_IN_GAME_UI_SCALE = "ui.set_in_game_ui_scale_func"
TRIGGER_TERRAIN_RERENDER = "ui.trigger_terrain_rerender_func"
SET_VOLUME = "ui.set_volume_func"
SET_MASTER_VOLUME = "ui.set_master_volume_func"
GET_GAME_RENDERER_MODE = "ui.get_game_renderer_mode_func"
SET_GAME_RENDERER_MODE = "ui.set_game_renderer_mode_func"

#: ``Constants::EnumPreference`` (``common/constants/ui.h:217-227``), the members the follow-up
#: switch names. Reforged's ported ``enums_src/ui_enums.py`` table agrees with native's here,
#: member for member.
ENUM_ANTI_ALIASING = 1
ENUM_REFLECTIONS = 2
ENUM_SHADER_QUALITY = 3
ENUM_SHADOW_QUALITY = 4
ENUM_TERRAIN_QUALITY = 5
ENUM_INTERFACE_SIZE = 6

#: ``Constants::NumberPreference`` (``common/constants/ui.h:236-282``) — **native's values, and they
#: are not all Reforged's.** Reforged's ``enums_src/UI_enums.py:362-404`` (ported verbatim into
#: ``enums_src/ui_enums.py``) swaps ``EffectsVolume`` (native ``24``, Reforged ``26``) with
#: ``BackgroundVolume`` (native ``26``, Reforged ``24``) and stops at ``ClockMode = 40`` where native
#: runs to ``Count = 44``. The older runtime the Reforged binding was built from agrees with native
#: (``vendor/gwca/Include/GWCA/Managers/UIMgr.h:912-932``: ``EffectsVolume, DialogVolume,
#: BackgroundVolume``, ``Count = 44``), so the Python table is the outlier — and these are the values
#: the member below switches on, because the switch is native's own body. Recorded in
#: ``docs/UIMANAGER_PORT.md``.
NP_REFRESH_RATE = 13
NP_SCREEN_SIZE_X = 14
NP_SCREEN_SIZE_Y = 15
NP_FULLSCREEN_GAMMA = 8
NP_TEXTURE_QUALITY = 22
NP_USE_BEST_TEXTURE_FILTERING = 23
NP_EFFECTS_VOLUME = 24
NP_DIALOG_VOLUME = 25
NP_BACKGROUND_VOLUME = 26
NP_MUSIC_VOLUME = 27
NP_UI_VOLUME = 28
NP_WINDOW_POS_X = 30
NP_WINDOW_POS_Y = 31
NP_WINDOW_SIZE_X = 32
NP_WINDOW_SIZE_Y = 33
NP_SCREEN_BORDERLESS = 38
NP_MASTER_VOLUME = 39

#: ``Constants::FlagPreference::IsWindowed`` (``common/constants/ui.h:300``) — the one flag whose
#: write has a follow-up. Native and Reforged's table agree on it (``0x2E``).
FLAG_IS_WINDOWED = 0x2E

#: ``Context::NumberPreferenceInfo`` (``context/ui.h:108-115``): ``name``, ``flags``, two unread
#: words, ``clamp_proc``, ``mapping_proc`` — 24 bytes. ``ClampPreference`` reads ``flags & 0x1`` and
#: calls ``clamp_proc`` when it is set (``ui_methods.cpp:385-395``).
NUMBER_PREFERENCE_INFO_SIZE = 0x18
NUMBER_PREFERENCE_INFO_FLAGS = 0x4
NUMBER_PREFERENCE_INFO_CLAMP_PROC = 0x10
NUMBER_PREFERENCE_INFO_CLAMP_FLAG = 0x1

#: ``Context::EnumPreferenceInfo`` (``context/ui.h:100-106``): ``name``, ``options_count``,
#: ``options``, ``unk``, ``pref_type`` — 20 bytes. This is the record ``GetPreferenceOptions`` reads
#: and the one ``SetPreference(EnumPreference, …)`` validates a value against.
ENUM_PREFERENCE_OPTIONS_ADDR = "ui.enum_preference_options_addr"
ENUM_PREFERENCE_INFO_SIZE = 0x14
ENUM_PREFERENCE_INFO_OPTIONS_COUNT = 0x4
ENUM_PREFERENCE_INFO_OPTIONS = 0x8

#: Where ``set_frame_limit``'s one word goes in the block's data region. The region's other users
#: are listed in ``py4gw/ui_manager.py``; this span sits between the camera's ``0x200`` and
#: `Frame.click`'s ``0x300``.
_PREFERENCE_WORD_OFFSET = 0x280

#: Where ``set_string_preference`` places the wide text the client reads. The caller's buffer has to
#: live in the client for the duration of the call and no longer, which is what a span of the data
#: region is for; the region's other users are listed in ``py4gw/ui_manager.py``.
_STRING_ARGUMENT_OFFSET = 0xD00


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


def get_number_preference(preference: int) -> int:
    """``uint32_t GetPreference(Constants::NumberPreference)`` (``ui_methods.cpp:1450-1454``).

    The same three conditions as :func:`get_enum_preference`, over
    ``g_get_number_preference_func`` and that enumeration's own ``Count`` (44,
    ``common/constants/ui.h:281``). ``UIManager.GetIntPreference`` is this, and
    ``UIManager.GetTextLanguage`` is this with ``NumberPreference::TextLanguage``.
    """

    from ..client import require_client

    client = require_client()
    if not client.resolves(GET_NUMBER_PREFERENCE):
        return 0
    if not prefs_initialised():
        return 0
    if preference >= NUMBER_PREFERENCE_COUNT:
        return 0
    return int(client.call_function(GET_NUMBER_PREFERENCE, CallForm.U32, int(preference)).value)


def get_flag_preference(preference: int) -> bool:
    """``bool GetPreference(Constants::FlagPreference)`` (``ui_methods.cpp:1462-1466``).

    Native answers ``false`` — not ``0`` — for each of the three refusals, so this does too.
    """

    from ..client import require_client

    client = require_client()
    if not client.resolves(GET_FLAG_PREFERENCE):
        return False
    if not prefs_initialised():
        return False
    if preference >= FLAG_PREFERENCE_COUNT:
        return False
    return bool(client.call_function(GET_FLAG_PREFERENCE, CallForm.U32, int(preference)).value)


def get_string_preference(preference: int) -> str:
    """``wchar_t* GetPreference(Constants::StringPreference)`` (``ui_methods.cpp:1456-1460``).

    The function returns the **client's own pointer**, not a copy, and the binding converts it
    (``ui_bindings.cpp:1043-1045``). A null is the binding's empty string; otherwise the port reads
    the string at that address, bounded.
    """

    from ..client import require_client

    client = require_client()
    if not client.resolves(GET_STRING_PREFERENCE):
        return ""
    if not prefs_initialised():
        return ""
    if preference >= STRING_PREFERENCE_COUNT:
        return ""
    pointer = int(
        client.call_function(GET_STRING_PREFERENCE, CallForm.U32, int(preference)).value
    )
    if not pointer:
        return ""
    return client.frame_array.read_wide_string(pointer, STRING_PREFERENCE_LIMIT)


def set_frame_limit(value: int) -> bool:
    """``bool GW::ui::SetFrameLimit(uint32_t)`` (``ui_methods.cpp:1860-1864``).

    The source's whole body is ``g_command_line_number_buffer ? (g_command_line_number_buffer[
    NumberCommandLineParameter::FPS] = value, true) : false`` — one word written at the FPS index
    of the command-line array the resolver answers, and ``false`` when that array is not there.
    The write goes through the payload's ``WRITE_MEMORY`` operation, which runs inside the hooked
    client function: the same thread the binding's ``game_thread::Enqueue`` reaches
    (``ui_bindings.cpp:689-692``).
    """

    from ..client import require_client

    client = require_client()
    address = client._resolve(COMMAND_LINE_BUFFER)
    if not address:
        return False
    bridge = client.bridge
    payload = int(value).to_bytes(4, "little")
    bridge.write_data(_PREFERENCE_WORD_OFFSET, payload)
    bridge.submit(
        Operation.WRITE_MEMORY,
        address + COMMAND_LINE_FPS * 4,
        _PREFERENCE_WORD_OFFSET,
        len(payload),
        0,
        0,
        0,
    )
    return True


def get_enum_preference_options(preference: int) -> list[int]:
    """``uint32_t GetPreferenceOptions(EnumPreference, uint32_t** out)`` (``ui_methods.cpp:1438-1448``).

    The guard is ``options && pref < Constants::EnumPreference::Count`` — **there is no
    ``PrefsInitialised()`` check here**, unlike the four getters — and the function then answers
    ``info.options_count`` while writing ``info.options`` through its out-parameter. The binding
    turns the pair into a list (``ui_bindings.cpp:1025-1033``); this reads the client's own
    ``EnumPreferenceInfo`` entry (``context/ui.h:100-106``), which is the record the function reads.
    """

    from ..client import require_client

    client = require_client()
    if not client.resolves(ENUM_PREFERENCE_OPTIONS_ADDR):
        return []
    base = client._resolve(ENUM_PREFERENCE_OPTIONS_ADDR)
    if not base or int(preference) >= ENUM_PREFERENCE_COUNT:
        return []
    entry = base + int(preference) * ENUM_PREFERENCE_INFO_SIZE
    count = read_u32(client, entry + ENUM_PREFERENCE_INFO_OPTIONS_COUNT)
    options = read_u32(client, entry + ENUM_PREFERENCE_INFO_OPTIONS)
    if not options or count <= 0:
        return []
    return [read_u32(client, options + index * 4) for index in range(count)]


def clamp_preference(preference: int, value: int) -> int:
    """``uint32_t ClampPreference(Constants::NumberPreference, uint32_t)`` (``ui_methods.cpp:385-395``).

    ``options && PrefsInitialised() && pref < Count``, then the entry's own ``flags & 0x1`` and a
    call through its ``clamp_proc`` — **a function pointer inside the client**, which is what
    ``ConnectedClient.call_address`` exists for: the address is the client's own, resolved from the
    record rather than from a catalog name (``ui_methods.cpp:391-392``). Every refusal answers the
    value unchanged, which is the source's own fall-through.
    """

    from ..client import require_client

    client = require_client()
    if not client.resolves(NUMBER_PREFERENCE_OPTIONS):
        return int(value)
    base = client._resolve(NUMBER_PREFERENCE_OPTIONS)
    if not (base and prefs_initialised() and int(preference) < NUMBER_PREFERENCE_COUNT):
        return int(value)
    entry = base + int(preference) * NUMBER_PREFERENCE_INFO_SIZE
    flags = read_u32(client, entry + NUMBER_PREFERENCE_INFO_FLAGS)
    if (flags & NUMBER_PREFERENCE_INFO_CLAMP_FLAG) == 0:
        return int(value)
    clamp_proc = read_u32(client, entry + NUMBER_PREFERENCE_INFO_CLAMP_PROC)
    if not clamp_proc:
        return int(value)
    return int(
        client.call_address(
            clamp_proc, CallForm.U32_U32, int(preference), int(value)
        ).value
    )


def set_enum_preference(preference: int, value: int) -> bool:
    """``bool SetPreference(Constants::EnumPreference, uint32_t)`` (``ui_methods.cpp:1468-1540``).

    Four steps, in the source's order: the guard (setter, initialised, getter, index below ``Count``);
    the value **validated against the client's own option list**; two id-specific rewrites; the write
    through the client's setter; and then the follow-up that re-reads the preference and drives what
    depends on it — the two renderer values for anti-aliasing and shader quality, the shadow quality,
    the terrain rerender, the reflections and the interface size.

    **The re-queue is not ported as a re-queue, and that is the source's own semantics.** Native
    checks ``game_thread::IsInGameThread()`` and enqueues itself when it is not (``:1472-1477``);
    every call this module makes already runs inside the hooked function, which *is* the game thread,
    and there ``Enqueue`` runs its callable inline rather than deferring it
    (``game_thread_methods.cpp:33-45``). So the follow-up below is the next call, which is what the
    source does when it is reached from the game thread — the same reading `UIManager.Keypress` is
    ported under.
    """

    from ..client import require_client

    client = require_client()
    if not (
        client.resolves(SET_ENUM_PREFERENCE)
        and prefs_initialised()
        and client.resolves(GET_ENUM_PREFERENCE)
        and int(preference) < ENUM_PREFERENCE_COUNT
    ):
        return False

    options = get_enum_preference_options(preference)
    index = 0
    count = len(options)
    while index < count:
        if options[index] == value:
            break
        index += 1
    if index == count:
        return False

    if preference == ENUM_ANTI_ALIASING and value == 2:
        value = 1
    elif preference in (ENUM_TERRAIN_QUALITY, ENUM_SHADER_QUALITY) and value == 0:
        value = 1

    client.call_function(
        SET_ENUM_PREFERENCE, CallForm.U32_U32, int(preference), int(value)
    )

    current_value = get_enum_preference(preference)
    if preference == ENUM_ANTI_ALIASING:
        _set_graphics_renderer_value(client, 2, 5, current_value)
        _set_graphics_renderer_value(client, 0, 5, current_value)
    elif preference == ENUM_SHADER_QUALITY:
        _set_graphics_renderer_value(client, 2, 9, current_value)
        _set_graphics_renderer_value(client, 0, 9, current_value)
    elif preference == ENUM_SHADOW_QUALITY:
        client.call_function(
            SET_IN_GAME_SHADOW_QUALITY, CallForm.U32, current_value
        )
    elif preference == ENUM_TERRAIN_QUALITY:
        client.call_function(
            SET_IN_GAME_STATIC_PREFERENCE, CallForm.U32_U32, 2, current_value
        )
        client.call_function(TRIGGER_TERRAIN_RERENDER, CallForm.NO_ARGS)
    elif preference == ENUM_REFLECTIONS:
        client.call_function(
            SET_IN_GAME_STATIC_PREFERENCE, CallForm.U32_U32, 1, current_value
        )
    elif preference == ENUM_INTERFACE_SIZE:
        client.call_function(SET_IN_GAME_UI_SCALE, CallForm.U32, current_value)

    return True


def set_number_preference(preference: int, value: int) -> bool:
    """``bool SetPreference(Constants::NumberPreference, uint32_t)`` (``ui_methods.cpp:1542-1637``).

    The guard here is **``PrefsInitialised()`` alone** (``:1543``) — the setter's own pointer and the
    index bound are checked at the write instead (``:1554``) — then the value is clamped through the
    client's own ``clamp_proc``, written, and followed by the id-specific work: the five volume
    channels, the master volume, and the eleven renderer metrics.

    Two shapes worth naming. The volume calls take a **float** (``current_value / 100.f``); this
    port passes it as the word its bit pattern is, which is the four bytes a ``cdecl`` callee reads
    off the stack either way — the call vocabulary's one float form is a pointer to four floats, and
    a pointer is not what these take. And the volume branches check their own pointer before calling
    (``if (g_set_volume_func)``, ``:1565``) while the renderer branches do not, so only the former
    are guarded here: the port copies the checks the source makes.
    """

    from ..client import require_client

    client = require_client()
    if not prefs_initialised():
        return False

    value = clamp_preference(preference, value)
    if not (
        client.resolves(SET_NUMBER_PREFERENCE)
        and int(preference) < NUMBER_PREFERENCE_COUNT
    ):
        return False
    client.call_function(
        SET_NUMBER_PREFERENCE, CallForm.U32_U32, int(preference), int(value)
    )

    current_value = get_number_preference(preference)
    volume_channel = None
    if preference == NP_EFFECTS_VOLUME:
        volume_channel = 0
    elif preference == NP_DIALOG_VOLUME:
        volume_channel = 4
    elif preference == NP_BACKGROUND_VOLUME:
        volume_channel = 1
    elif preference == NP_MUSIC_VOLUME:
        volume_channel = 3
    elif preference == NP_UI_VOLUME:
        volume_channel = 2
    if volume_channel is not None:
        if client.resolves(SET_VOLUME):
            client.call_function(
                SET_VOLUME, CallForm.U32_U32, volume_channel, _float_word(current_value / 100.0)
            )
    elif preference == NP_MASTER_VOLUME:
        if client.resolves(SET_MASTER_VOLUME):
            client.call_function(
                SET_MASTER_VOLUME, CallForm.U32, _float_word(current_value / 100.0)
            )
    elif preference == NP_FULLSCREEN_GAMMA:
        _set_graphics_renderer_value(client, 2, 0x4, current_value)
        _set_graphics_renderer_value(client, 0, 0x4, current_value)
    elif preference == NP_TEXTURE_QUALITY:
        _set_graphics_renderer_value(client, 2, 0xD, current_value)
        _set_graphics_renderer_value(client, 0, 0xD, current_value)
    elif preference == NP_REFRESH_RATE:
        _set_graphics_renderer_value(client, 2, 0x8, current_value)
        _set_graphics_renderer_value(client, 0, 0x8, current_value)
    elif preference == NP_USE_BEST_TEXTURE_FILTERING:
        _set_graphics_renderer_value(client, 2, 0xC, current_value)
        _set_graphics_renderer_value(client, 0, 0xC, current_value)
    elif preference == NP_SCREEN_BORDERLESS:
        _set_graphics_renderer_value(client, 2, 0x10, current_value)
    elif preference == NP_WINDOW_POS_X:
        _set_graphics_renderer_value(client, 2, 6, current_value)
    elif preference == NP_WINDOW_POS_Y:
        _set_graphics_renderer_value(client, 2, 7, current_value)
    elif preference == NP_WINDOW_SIZE_X:
        _set_graphics_renderer_value(client, 2, 0xA, current_value)
    elif preference == NP_WINDOW_SIZE_Y:
        _set_graphics_renderer_value(client, 2, 0xB, current_value)
    elif preference == NP_SCREEN_SIZE_X:
        _set_graphics_renderer_value(client, 0, 0xA, current_value)
    elif preference == NP_SCREEN_SIZE_Y:
        _set_graphics_renderer_value(client, 0, 0xB, current_value)

    return True


def set_string_preference(preference: int, value: str) -> bool:
    """``bool SetPreference(Constants::StringPreference, wchar_t*)`` (``ui_methods.cpp:1639-1651``).

    The guard (setter resolved, preferences initialised, index below ``Count`` — three), and then one
    call: ``g_set_string_preference_func(pref, value)``. **The client reads the string the caller
    owns**, which is why the binding hands over a ``std::wstring``'s own buffer
    (``ui_bindings.cpp:1055-1057``, ``value.data()``, null-terminated).

    This port does the same thing with the transport it has: the UTF-16 text goes into the block's
    data region — memory **inside** the client, which is the only kind of pointer the client can be
    handed — and that address is the argument. The lifetime is the source's: the call and no longer.
    """

    from ..client import require_client

    client = require_client()
    if not (
        client.resolves(SET_STRING_PREFERENCE)
        and prefs_initialised()
        and int(preference) < STRING_PREFERENCE_COUNT
    ):
        return False
    address = client.bridge.write_data(_STRING_ARGUMENT_OFFSET, _wide_bytes(value))
    client.call_function(
        SET_STRING_PREFERENCE, CallForm.U32_U32, int(preference), address
    )
    return True


def set_flag_preference(preference: int, value: bool) -> bool:
    """``bool SetPreference(Constants::FlagPreference, bool)`` (``ui_methods.cpp:1653-1677``).

    The guard, the write, and — **only for ``FlagPreference::IsWindowed``** — the renderer-mode
    pair: read the current mode, and write the one the flag asks for when it differs. Both of those
    are checked in the source (``g_get_game_renderer_mode_func ? … : 0`` and
    ``g_set_game_renderer_mode_func &&``), so both are checked here.
    """

    from ..client import require_client

    client = require_client()
    if not (
        client.resolves(SET_FLAG_PREFERENCE)
        and prefs_initialised()
        and int(preference) < FLAG_PREFERENCE_COUNT
    ):
        return False

    client.call_function(
        SET_FLAG_PREFERENCE, CallForm.U32_U32, int(preference), 1 if value else 0
    )

    if preference == FLAG_IS_WINDOWED:
        pref_value = 2 if value else 0
        renderer_value = (
            int(client.call_function(GET_GAME_RENDERER_MODE, CallForm.U32, 0).value)
            if client.resolves(GET_GAME_RENDERER_MODE)
            else 0
        )
        if client.resolves(SET_GAME_RENDERER_MODE) and pref_value != renderer_value:
            client.call_function(
                SET_GAME_RENDERER_MODE, CallForm.U32_U32, 0, pref_value
            )

    return True


def _set_graphics_renderer_value(
    client: ConnectedClient, target: int, metric: int, value: int
) -> None:
    """``g_set_graphics_renderer_value_func(nullptr, target, metric, value)``.

    The four-word call the renderer follow-ups make (``ui_methods.cpp:1514-1629``): a null first
    word, the pair the source writes (``2`` for the device path, ``0`` for the screen path), the
    metric id, and the value that was just written.
    """

    client.call_function(
        SET_GRAPHICS_RENDERER_VALUE, CallForm.U32_U32_U32_U32, 0, int(target), int(metric), int(value)
    )


def _float_word(value: float) -> int:
    """One float as the word a ``cdecl`` callee reads it from.

    ``SetPreference``'s volume follow-ups pass ``static_cast<float>(current_value) / 100.f``
    (``ui_methods.cpp:1566`` and the four beside it); a 32-bit float and a 32-bit word are the same
    four bytes on the stack, so the port passes the bit pattern the call record can carry.
    """

    return int.from_bytes(struct.pack("<f", float(value)), "little")


def _wide_bytes(text: str) -> bytes:
    """One Python string as the wide buffer a ``std::wstring`` hands the client.

    ``value.data()`` (``ui_bindings.cpp:1056``) is UTF-16 code units ending in the terminator a
    ``std::wstring`` keeps, and a Windows ``wchar_t`` is 16 bits — so this is the same conversion,
    including the surrogate pairs a code point beyond the BMP becomes. The member that reads a wide
    string back (``get_string_preference``) is the mirror of it.
    """

    return text.encode("utf-16-le") + b"\x00\x00"
