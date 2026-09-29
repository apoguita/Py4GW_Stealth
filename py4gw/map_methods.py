"""External port of Reforged's ``native_src/methods/MapMethods.py``.

The source file is 135 lines: two module-level resolutions (a function and a data symbol,
``:13-35``) and seven methods. It is the module every ``Map`` action reaches: ``Map.SkipCinematic``,
the four travel members, ``LeaveGH``, ``EnterChallenge`` and ``Pregame.LogoutToCharacterSelect``
all call through it, and ``Map.GetUnloadedMapInfo`` is its ``GetMapInfo``.

**What replaces the injected runtime's half.**

* ``SkipCinematic_Func`` (``:13-21``) is a ``NativeFunction`` over the bytes
  ``8B 40 30 83 78 04 00`` at -0x5, declared ``Prototypes["Void_NoArgs"]``. That is a scanned
  function pointer plus a call shape, which is exactly the catalog's pairing: the same bytes are
  ``map.skip_cinematic_func`` (``offsets/map.json``, ``offsets/o`` -0x5, ``section: text``) and the
  shape is ``CallForm.NO_ARGS``, driven through ``py4gw/game_thread/``. ``NativeFunction.is_valid()``
  is this port's ``client.resolves(name)``: the sources answer "not there" rather than calling a
  null pointer, and so does this.
* ``_area_info_symbol`` (``:25-35``) is a ``NativeSymbol`` over ``6B C6 7C 5E 05`` at +5, whose
  ``read_ptr()`` is the global ``AreaInfo`` array's base. The catalog carries the same scan as
  ``map.area_info_addr``, validated into ``.rdata``.

**Two of the source's own arguments are host addresses, and that is the one thing that changes.**
``ctypes.addressof(TravelStruct(...))`` and ``ctypes.addressof(gh_key)`` are pointers the client is
handed. The sources run *inside* ``Gw.exe``, so a struct built on their own stack frame — and a
context record they are already viewing in place — are both addresses the client can read. This
process is outside it, so:

* ``Travel``'s four words go into the block's data region and that address is passed, which is the
  same route ``UIManager.SendUIMessage`` already takes for its own sixteen-word payload;
* ``TravelGH`` needs no copy at all — ``player_gh_key`` is a field of the client's own
  ``GuildContext``, and its address is ``GuildContextStruct.player_gh_key.offset`` (``0x64``,
  asserted in ``py4gw/context/guild_context.py:528``) off the resolved context. The client is
  handed the address of its own key, which is what "always use the original, working pointer"
  (``:102``) means.

``TravelGH``'s ``key`` branch (``:97-100``) writes the caller's four key bytes *into the client's
key* before sending. That is the payload's ``WRITE_MEMORY`` operation, the same mechanism
``Camera``'s field writers use. ``Map.TravelGH()`` passes no key, so that branch is not taken from
``Map``; it is ported because the member declares it.

Nothing here is invented: see ``docs/PORTING_RULES.md``.
"""

from __future__ import annotations

import ctypes
import struct
from typing import Optional

from .context.guild_context import GHKey, GuildContextStruct
from .context.gw_context import GWContext
from .context.instance_info_context import AreaInfoStruct
from .enums_src.ui_enums import UIMessage
from .game_thread.shared_block import CallForm, Operation
from .ui_manager import UIManager

#: The two things the source resolves at import (``MapMethods.py:13-35``), as the catalog names
#: the same pattern and mask are carried under.
SKIP_CINEMATIC_FUNC = "map.skip_cinematic_func"
AREA_INFO_ADDR = "map.area_info_addr"

#: Where ``Travel``'s four words are placed in the block's data region. The source hands the client
#: ``ctypes.addressof(TravelStruct(...))``; the port's equivalent of "a buffer this caller owns
#: inside the client" is the block, which is what ``UIManager.SendUIMessage`` uses for its payload.
#:
#: **These offsets were wrong twice, and both mistakes are worth naming.** They were first ``0x300``
#: and ``0x320`` — ``frame_tree/frame.py``'s ``_MOUSE_ACTION_OFFSET`` and ``_BUTTON_PARAM_OFFSET``,
#: so a travel packet and a mouse-click packet would have shared memory. Moving them to just below
#: ``0x400`` was still wrong: ``chat.LOG_MESSAGE_OFFSET`` is ``0x200`` with **0x400 bytes** of span
#: (``chat.py:190``, ``(LOG_SENDER_OFFSET - LOG_MESSAGE_OFFSET)``), so it covers ``0x200..0x600``
#: and swallows everything in between. The block's data region is 4096 bytes
#: (``shared_block.py:113``); these now sit in the gap **above** ``ui_manager.py``'s
#: ``_UI_PAYLOAD_OFFSET`` (``0xE00 + 0x40``), which nothing else claims, and
#: ``tests/test_map_offline.py::BlockRegionTests`` pins that against every other module's region.
_TRAVEL_OFFSET = 0xF00

#: Where the caller's four key bytes are placed before ``WRITE_MEMORY`` names them.
_GHKEY_OFFSET = 0xF20


class MapMethods:
    _GHKEY_SCRATCH = GHKey()

    @staticmethod
    def GetMapInfo(map_id: int):
        """Return AreaInfoStruct for any map_id (not just the current map). (source 41-55)"""

        from .client import require_client

        if map_id <= 0:
            return None

        client = require_client()
        if not client.resolves(AREA_INFO_ADDR):
            return None

        base = client._resolve(AREA_INFO_ADDR)
        if not base:
            return None

        size = ctypes.sizeof(AreaInfoStruct)
        target_addr = base + (map_id * size)
        try:
            return AreaInfoStruct.from_buffer_copy(client.reader.read(target_addr, size))
        except (ValueError, OSError):
            return None

    @staticmethod
    def SkipCinematic() -> bool:
        """Skip the current map cinematic. (source 57-64)"""

        from .client import require_client

        client = require_client()
        if not client.resolves(SKIP_CINEMATIC_FUNC):
            return False

        client.call_function(SKIP_CINEMATIC_FUNC, CallForm.NO_ARGS)
        return True

    @staticmethod
    def Travel(map_id: int, region: int = 0, district_number: int = 0, language: int = 0) -> bool:
        """``Travel`` (source 66-80) — ``kTravel`` with the four words it carries.

        The source's own record is ``TravelStruct`` (``:68-74``): ``map_id`` as ``uint32`` and
        ``region``/``language``/``district_number`` as ``int32``, filled by keyword so the memory
        order is the declaration order. The signature order is ``(map_id, region, district_number,
        language)`` and the memory order is not, which is the source's own shape and is kept.
        """

        from .client import require_client

        client = require_client()
        payload = struct.pack(
            "<Iiii",
            int(map_id),
            int(region),
            int(language),
            int(district_number),
        )
        address = client.bridge.write_data(_TRAVEL_OFFSET, payload)
        return UIManager.SendUIMessageRaw(UIMessage.kTravel, address, 0)

    @staticmethod
    def TravelGH(key: Optional[GHKey] = None) -> bool:
        """Travel to a Guild Hall. (source 82-108)

        ``player_gh_key`` is a field of the client's own ``GuildContext``, so the pointer the
        client is handed is that field's address: the resolved context plus
        ``GuildContextStruct.player_gh_key.offset`` (``0x64``, asserted in
        ``py4gw/context/guild_context.py``). The source's own comment on the line says why it is
        the context's key and not a copy — *"Always use the original, working pointer"*.
        """

        guild_ctx = GWContext.Guild.GetContext()
        if guild_ctx is None:
            return False

        gh_key = guild_ctx.player_gh_key
        if gh_key is None:
            return False

        base = GWContext.Guild.GetPtr()
        if not base:
            return False
        gh_key_address = base + GuildContextStruct.player_gh_key.offset

        # If a custom key was provided, stuff its value into the real GH key
        if key is not None:
            from .client import require_client

            client = require_client()
            value = bytes(key.key_data)
            client.bridge.write_data(_GHKEY_OFFSET, value)
            client.bridge.submit(
                Operation.WRITE_MEMORY,
                gh_key_address,
                _GHKEY_OFFSET,
                len(value),
                0,
                0,
                0,
            )

        # Always use the original, working pointer
        return UIManager.SendUIMessageRaw(UIMessage.kGuildHall, gh_key_address, 0)

    @staticmethod
    def LeaveGH() -> bool:
        """Leave the current Guild Hall. (source 110-117)"""

        return UIManager.SendUIMessage(UIMessage.kLeaveGuildHall, [0], False)

    @staticmethod
    def EnterChallenge() -> bool:
        """Enter the challenge mode from the Guild Hall. (source 119-126)"""

        return UIManager.SendUIMessage(UIMessage.kSendEnterMission, [0], False)

    @staticmethod
    def LogouttoCharacterSelect() -> None:
        """``LogouttoCharacterSelect`` (source 129-134).

        The source runs the send on the game thread through ``PyGameThread.enqueue``; that enqueue
        is the capability layer's own call path here, so the send is made where it was enqueued.
        """

        UIManager.SendUIMessage(UIMessage.kLogout, [0, 0])
