"""GwAu3's ``Core_*``: opening the client, the status words a script gates on, and ``Memory_Read``.

**Every GwAu3 script's first two lines are here** -- ``Core_Initialize`` and ``Core_AutoStart`` -- so
this module is the door. GwAu3's ``Core_Initialize`` opens the process, scans its own byte signatures,
resolves the pointers it keeps in a global table and reads the character name; this project's
equivalent is one call, because the scan and the resolution are what ``py4gw.connect()`` already is
(``offsets/`` plus ``RemoteScanner``, ported from Reforged Native).

**The module splits three ways, and the split is the port.** ``Core_Initialize`` is bridged: it is the
connection. ``Core_AutoStart`` and ``Core_GetGuildWarsWindow`` are AutoIt-side and are transcribed in
``tools/autoit/Stealth_GwAu3.au3``, because they call back into the *script* (``StartBot()``,
``$g_bAutoStart``) and drive the script's own window -- there is nothing for Python to do. The status
words are **refused**: GwAu3 reads three client globals this project has no resolver for, and the
route map records that rather than approximating them from a different predicate.

**``GwAu3_Core_Memory.au3``'s two readers are here too** -- ``Memory_Read`` and ``Memory_ReadPtr``,
below. They are the pair every GwAu3 module reaches the client's bytes through, and the layer's answer
to them is the same substitution the rest of the layer makes: a caller here holds no client address, so
what they accept is what **this layer** produces -- a record it read, or the address
`Memory_ReadPtr` itself answered -- and both are read through this project's own
`ProcessMemoryReader` (`py4gw/memory/memory.py:18`, the port of ``ReadProcessMemory``).

From GwAu3's own contract (``GwAu3_Core.au3:9-...``): ``Core_Initialize`` answers **1** on success and
**0** on failure, with ``@error`` 1 for "no such client or character" and 2 for "the scan failed".
"""

from __future__ import annotations

import ctypes
import re
import struct
from typing import Any

import py4gw
from ..client import require_client
from ..player import Player
from ..ui_manager import UIManager
from ..win32 import Win32
from . import constants as _constants

#: The three status words GwAu3 reads, and the rule each refuses by.
#:
#: GwAu3 resolves them by its own byte patterns -- ``Login`` = ``83C420D955ECD955F0`` + 0x33,
#: ``InGame`` = ``8D7E388907`` + 0x4D, ``StatusCode`` = ``8945088D45086A04`` - 0x10 -- and stores the
#: addresses in ``Memory_SetValue`` for every reader to use. This project's catalog has no resolver for
#: any of the three (`offsets/gwau3_leads.json` carries one GwAu3 lead, ``current_target_anchor``, and
#: none of these), so a value cannot be produced without inventing a route.
#:
#: **The temptation this refuses is real and it is worth naming.** ``Map.IsMapReady()`` and
#: ``Player.GetAgentID() != 0`` both say something about whether the client is in a game, and either
#: could be dressed up as ``Core_IsIngame()``. They are not the same predicate: ``IsMapReady`` is a
#: compound of three other reads (``py4gw/map.py:164-171``) and the route map's own note on
#: ``Map_MapIsLoaded`` says "loaded" and "ready" are not stated to be the same thing. A script that
#: gates on ``Core_IsIngame()`` would then be gating on a different question than it asked.
_STATUS_RULE = (
    "GwAu3 resolves this by its own byte pattern into a client global ({lead}), and this project has "
    "no resolver for that address: `offsets/` carries no entry for it and `offsets/gwau3_leads.json` "
    "holds only `current_target_anchor`. Answering it from a different predicate -- `Map.IsMapReady()` "
    "or `Player.GetAgentID()` -- would be a different question answered with the same name, which is "
    "the substitution this layer refuses. The work is a resolver for the address, and it is recorded "
    "in `docs/GWA3_ROUTE_MAP.md`."
)


def _client_entries() -> list[dict[str, Any]]:
    """Every ``Gw.exe`` the machine has, as this project's own discovery reports them."""

    return list(Win32().find_guild_wars())


def Core_Initialize(gw: Any, change_title: bool = True) -> int:
    """Open a client and resolve the runtime (``GwAu3_Core.au3:9-...``).

    GwAu3's two argument forms are kept exactly: a **string** is a character name and GwAu3 walks the
    process list opening each client, scanning it and comparing the character name it finds, closing
    the ones that do not match; a **number** is a process id, used directly. The return contract is
    GwAu3's: ``1`` when a client was opened, ``0`` when none matched, and the same two ``@error``
    meanings the AutoIt side reads (through the bridge's own error kinds).

    **What this project supplies is the opening and the scanning.** ``py4gw.connect()`` resolves the
    patterns inside the loaded module, installs the capability layer and holds the connection --
    the job GwAu3's twenty-odd ``Scanner_AddPattern`` calls and its ``Memory_SetValue`` table do in
    its own runtime.
    """

    entries = _client_entries()
    if not entries:
        return 0

    if isinstance(gw, str):
        wanted = gw.strip()
        if not wanted:
            return 0
        # GwAu3's own loop: open, scan, read the name, compare, close. A read-only connection is what
        # this project's "open, scan and read, then close" is, and it writes nothing to the client.
        for entry in entries:
            probe = py4gw.connect(entry, game_thread=False)
            try:
                found = str(Player.GetName() or "").strip()
            except Exception:  # noqa: BLE001 - a client that cannot be read is not the one asked for
                found = ""
            finally:
                py4gw.disconnect()
            if found == wanted:
                py4gw.connect(entry)
                return 1
        return 0

    for entry in entries:
        if int(entry.get("pid", 0)) == int(gw):
            py4gw.connect(entry)
            return 1
    return 0


# ---------------------------------------------------------------------------------------------
# ``GwAu3_Core_Memory.au3`` -- the two plain reads, over this project's own reader.
#
# GwAu3's ``Memory_Read`` is ``DllStructCreate($a_s_Type)`` plus ``ReadProcessMemory`` plus
# ``DllStructGetData`` (`:33-37`), and its ``Memory_ReadPtr`` is that read at the end of an offset
# chain (`:39-60`). Both take an **address**, and a caller of this layer holds none -- so what they
# accept is what this layer produces: a record it read, or the address ``Memory_ReadPtr`` answered.
# The bytes come from the same client either way, and the reader is this project's own.
# ---------------------------------------------------------------------------------------------

#: GwAu3's ``$a_s_Type`` names, and the ``struct`` code and width each one is (``GwAu3_Core_Memory.au3:34``).
#: The type string **is** the contract -- ``DllStructCreate`` either accepts it or fails -- so the names
#: here are AutoIt's own: ``dword``/``word``/``ptr`` unsigned, ``long``/``short`` signed, and ``ptr`` a
#: four-byte target pointer because the client is x86.
_TYPES: dict[str, tuple[str, int]] = {
    "byte": ("B", 1),
    "word": ("H", 2),
    "short": ("h", 2),
    "ushort": ("H", 2),
    "long": ("i", 4),
    "int": ("i", 4),
    "dword": ("I", 4),
    "ptr": ("I", 4),
    "float": ("f", 4),
    "double": ("d", 8),
}

#: ``wchar[N]``, ``char[N]``, ``byte[N]``, ``dword[N]`` -- the array spellings GwAu3's reads use.
_ARRAY_TYPE = re.compile(r"^(?P<base>[A-Za-z]\w*)\s*\[\s*(?P<count>\d+)\s*\]$")


def _type_size(a_s_Type: str) -> int:
    """How many bytes ``DllStructGetSize`` would answer for GwAu3's type, or ``0`` for one it rejects."""

    text = str(a_s_Type or "")
    match = _ARRAY_TYPE.match(text)
    if match:
        base = match.group("base")
        count = int(match.group("count"))
        if base == "wchar":
            return 2 * count
        if base == "char":
            return count
        entry = _TYPES.get(base)
        return 0 if entry is None else entry[1] * count
    entry = _TYPES.get(text)
    return 0 if entry is None else entry[1]


def _typed_value(raw: bytes, a_s_Type: str) -> Any:
    """``DllStructGetData`` for one of GwAu3's types (``GwAu3_Core_Memory.au3:36``).

    The three array answers are AutoIt's own, and each is the one this project already answers for the
    same read elsewhere: a numeric array is a **list** (the shape
    `Map_GetMapContextInfo`'s ``MapBoundaries`` key answers for GwAu3's ``float[5]``,
    ``py4gw/gwa3/data_map_context.py:153``), a ``byte[N]`` is the **binary text** ``0x`` plus upper-case
    hex -- measured for exactly this read, `Item_GetModStruct`'s own note on the same
    ``Memory_Read($p, 'Byte[n]')`` call (`py4gw/gwa3/data_item.py:721-727`) -- and a ``char[N]`` /
    ``wchar[N]`` is the string, terminated at the first NUL as ``DllStructGetData`` terminates it.
    """

    text = str(a_s_Type or "")
    match = _ARRAY_TYPE.match(text)
    if match:
        base = match.group("base")
        count = int(match.group("count"))
        if base == "wchar":
            return raw[: 2 * count].decode("utf-16-le", errors="replace").split("\x00", 1)[0]
        if base == "char":
            return raw[:count].decode("latin-1").split("\x00", 1)[0]
        entry = _TYPES.get(base)
        if entry is None:
            return 0
        code, width = entry
        if base == "byte":
            return "0x" + raw[: count * width].hex().upper()
        return list(struct.unpack_from(f"<{count}{code}", raw, 0))

    entry = _TYPES.get(text)
    if entry is None or len(raw) < entry[1]:
        return 0
    return struct.unpack_from(f"<{entry[0]}", raw, 0)[0]


def _zero_value(a_s_Type: str) -> Any:
    """GwAu3's answer when its read never filled the struct (``GwAu3_Core_Memory.au3:35-36``).

    ``ReadProcessMemory`` failing leaves the ``DllStruct`` zero-initialised and ``DllStructGetData``
    answers that buffer, so the value of the zero-filled type **is** the answer: ``0`` for a number,
    ``0x0000…`` for a ``byte[N]``, and ``""`` for a character array. A type no ``DllStructCreate``
    accepts answers ``0``, which is the same path failing one line earlier.
    """

    size = _type_size(a_s_Type)
    return 0 if not size else _typed_value(b"\x00" * size, a_s_Type)


def _bytes_at(a_p_Source: Any, offset: int, size: int) -> bytes | None:
    """``size`` bytes at ``offset`` of whatever the caller holds, or ``None`` when there are none.

    **A record is its own bytes.** A ``ctypes`` structure or array a layer member answered is the
    client's bytes materialized, so its offset is an offset into the record and nothing is read -- the
    value at ``0`` is the value GwAu3's read at that record's address produces.

    **An address is read through this project's reader.** ``require_client().reader`` is
    `py4gw.client.ConnectedClient.reader` (``py4gw/client.py:1286``) -- this project's only read of the
    client's bytes, the port of ``ReadProcessMemory`` -- and a bounded read that fails raises ``OSError``
    (`py4gw/memory/memory.py:40-45`). That failure is **caught here deliberately**: GwAu3's read has no
    guard, and its own answer for an unreadable address is the zero-filled struct, so the caller is
    handed ``None`` and the member answers GwAu3's zero rather than an exception GwAu3 cannot produce.
    """

    if isinstance(a_p_Source, (ctypes.Structure, ctypes.Array)):
        raw = bytes(memoryview(a_p_Source))
        if offset < 0 or offset + size > len(raw):
            return None
        return raw[offset : offset + size]

    if not a_p_Source:
        return None

    try:
        raw = require_client().reader.read(int(a_p_Source) + offset, size)
    except OSError:
        return None
    return raw if len(raw) == size else None


def Memory_Read(a_p_Address: Any, a_s_Type: str = "dword") -> Any:
    """One typed read of the client's bytes (``GwAu3_Core_Memory.au3:33-37``).

    **What GwAu3 does.** It creates a ``DllStruct`` of ``$a_s_Type``, hands its pointer to
    ``ReadProcessMemory($g_h_GWProcess, $a_p_Address, …)`` (`:35`) and answers
    ``DllStructGetData($l_d_Buffer, 1)`` (`:36`). There is **no guard**: an address the read cannot fill
    answers that type's zero, and the caller cannot tell it from a real zero. This member keeps that --
    an unreadable address, a null address and a type ``DllStructCreate`` would reject all answer the
    zero value (`_zero_value`).

    **What this accepts.** A caller here holds no client address, so the argument is what this layer
    itself hands out:

    * **a record this layer answered** -- any structure or array from `Agent_GetAgentPtr`,
      `Item_GetItemPtr`, `PreGame_Ptr`, the ``*ContextPtr`` members, `Map_GetMapContextInfo`'s record
      keys. Its bytes *are* the client's bytes at the address GwAu3 would read, so
      ``Memory_Read(record, "dword")`` is that read: the value at the record's own start, in the shape
      the type names. A field further in is a **named field** of that record (or one of this layer's
      field keys), which is what a record is for here -- `Memory_Read` has no offset argument and GwAu3
      does not give it one.
    * **an address this layer produced** -- the first cell of `Memory_ReadPtr`'s answer, which is the
      only member that answers one (`Memory_ReadPtr` below). It is read through this project's own
      reader (`py4gw/client.py:1286`, the port of ``ReadProcessMemory``), which is the member doing the
      work here.

    ``0`` and ``None`` answer the type's zero without reading, which is GwAu3's own answer for the
    address ``0``. **An id is not accepted**: GwAu3's argument is an address, this layer's ids name
    records rather than addresses, and a read at an id would be a read of nothing. The layer's own
    vocabulary for "the value of a record" is the member that owns it (`Item_GetItemInfoByItemID`,
    `Agent_GetAgentInfo`), not this one.

    **Arrays keep AutoIt's answers** -- a numeric array a list, ``byte[N]`` the ``0x`` hex text,
    ``char[N]``/``wchar[N]`` the string (`_typed_value`).

    One divergence, and it is this layer's own connection guard: a caller with **no client connected**
    raises through `require_client` (`py4gw/client.py:1937`), where GwAu3 answers the type's zero -- the
    divergence `Game_GetGameInfo` states on its first guard. Everything the client *holds* answers as
    GwAu3 does, including a failed read.
    """

    size = _type_size(a_s_Type)
    if not size:
        return 0

    raw = _bytes_at(a_p_Address, 0, size)
    if raw is None:
        return _zero_value(a_s_Type)
    return _typed_value(raw, a_s_Type)


def Memory_ReadPtr(a_p_Address: Any, a_ai_Offset: Any, a_s_Type: str = "dword") -> list[Any]:
    """A read at the end of an offset chain (``GwAu3_Core_Memory.au3:39-60``).

    **GwAu3's arithmetic and its guard order, term for term.** ``$l_i_PointerCount =
    UBound($a_ai_Offset) - 2`` (`:40`), so every offset but the last is a **dereference hop** --
    ``$a_p_Address += $a_ai_Offset[$i]`` then read a ``dword`` there (`:45-46`) and continue from it
    (`:47`) -- and the last offset is the final displacement (`:54`). The moment a hop dereferences to
    ``0`` the answer is ``[0, 0]`` (`:48-51`), which this returns at both of those points: a hop that
    reads zero, and a hop whose bytes cannot be read at all -- GwAu3's failed ``ReadProcessMemory``
    leaves the buffer zero, so its own ``== 0`` guard fires on that path too. The answer is GwAu3's
    two-element array ``[address, value]`` (`:58`), a list here.

    **The address cell is the one place this layer answers an address, and it is a value this layer
    produced.** It is read out of the client by this project's reader on the way to the value, it is
    what `Memory_Read` and this member take back as their first argument, and no member answers a client
    address for its own sake -- every other ``*Ptr`` spelling in this layer answers the record instead
    (`Agent_GetAgentPtr`, `World_GetWorldContextPtr`). An offset chain is the one read a record cannot
    stand in for: the chain is arbitrary, so there is nothing to name.

    ``$a_ai_Offset`` is GwAu3's AutoIt array of offsets; here it is any Python sequence of ints.
    ``a_p_Address`` is what this layer hands out, exactly as `Memory_Read` states it: a **record**, whose
    own bytes are where the first hop reads (so ``Memory_ReadPtr(agent_record, [0x18, 0x4], "dword")``
    follows the word the record itself holds), or **an address this layer produced** (the first cell of
    another chain's answer), which is read through this project's reader. A call with no offsets is the
    flat read of the base, which is what GwAu3's own last-displacement step reduces to.
    """

    offsets = [int(value) for value in a_ai_Offset]
    size = _type_size(a_s_Type)
    if not size:
        return [0, 0]

    address: Any = a_p_Address
    for index in range(max(len(offsets) - 1, 0)):
        pointer = _bytes_at(address, offsets[index], 4)
        if pointer is None:
            return [0, 0]
        address = int.from_bytes(pointer, "little")
        if address == 0:
            return [0, 0]

    final_offset = offsets[-1] if offsets else 0
    # A record base with no hop has no address of its own here, so the first cell is GwAu3's own
    # "nothing resolved" zero; every other shape ends on an address this layer read or was handed.
    final_address = address + final_offset if isinstance(address, int) else 0
    raw = _bytes_at(address, final_offset, size)
    if raw is None:
        return [final_address, _zero_value(a_s_Type)]
    return [final_address, _typed_value(raw, a_s_Type)]


def Core_IsIngame() -> bool:
    """**Refused, not answered.** See `_STATUS_RULE`."""

    raise NotImplementedError(_STATUS_RULE.format(lead="`InGame` and `Login`"))


def Core_IsLoginScreen() -> bool:
    """**Refused, not answered.** See `_STATUS_RULE`."""

    raise NotImplementedError(_STATUS_RULE.format(lead="`Login` and `InGame`"))


def Core_IsCharacterSelection() -> bool:
    """**Refused, not answered.** See `_STATUS_RULE`."""

    raise NotImplementedError(_STATUS_RULE.format(lead="`Login` and `InGame`"))


def Core_GetLoginStatus() -> int:
    """**Refused, not answered.** See `_STATUS_RULE`."""

    raise NotImplementedError(_STATUS_RULE.format(lead="`Login`"))


def Core_GetInGameStatus() -> int:
    """**Refused, not answered.** See `_STATUS_RULE`."""

    raise NotImplementedError(_STATUS_RULE.format(lead="`InGame`"))


def Core_GetStatusCode() -> int:
    """**Refused, not answered.** See `_STATUS_RULE`."""

    raise NotImplementedError(_STATUS_RULE.format(lead="`StatusCode`"))


def Core_GetStatusError() -> bool:
    """**Refused, not answered.** See `_STATUS_RULE`."""

    raise NotImplementedError(_STATUS_RULE.format(lead="`StatusCode`"))


def Core_SendPacket(*args: Any, **kwargs: Any) -> int:
    """**Refused: GwAu3's own body forges a packet.** See `docs/GWA3_COMPAT_SPEC.md`."""

    raise NotImplementedError(
        "GwAu3_Core.au3:575-589 writes the packet into its own DllStruct and hands it to "
        "`Core_Enqueue`, which writes it into the client's queue with `WriteProcessMemory` -- a forged "
        "packet. This project does not forge packets under any name: every action it takes drives the "
        "client's own function instead (M1), its own UI message (M2) or its own frame message (M3). "
        "The route for each effect is recorded per function in `docs/GWA3_ROUTE_MAP.md`."
    )


def Core_Enqueue(*args: Any, **kwargs: Any) -> Any:
    """**Refused: GwAu3's own body writes into the client's queue.** See `Core_SendPacket`."""

    raise NotImplementedError(
        "GwAu3_Core.au3:559-566 is the injected-assembler stub: it writes a pointer and a size into "
        "the client's own queue at `256 * $g_i_QueueCounter + $g_p_QueueBase` with "
        "`WriteProcessMemory`. That queue is the channel GwAu3's forged packets travel on, and this "
        "project does not write into it -- not for a packet, not for a record. `Core_SendPacket` is "
        "refused for the same reason and names it here rather than restating it. (`Core_PerformAction` "
        "enqueues the same way, but the *action* it asks for is one this project can press -- see that "
        "member.)"
    )


def Core_PerformAction(a_i_Action: Any, a_i_Flag: Any, a_i_Type: Any = 0) -> None:
    """Perform a control action (``GwAu3_Core.au3:568-573``) -- **routed**, and the route is Reforged's.

    **What GwAu3 does.** It fills its own action struct -- ``ptr;dword;dword;dword``
    (``GwAu3_Const_Core.au3:15``), whose first word is the pointer to its stub -- with the action, the
    flag and the type, and hands it to `Core_Enqueue`, which writes the record into the client's command
    queue (``:559-566``). The action is performed by the stub that record points at:
    ``GwAu3_Core_Assembler.au3:2101-2118`` reads ``[record+C]`` (the *type*) to choose between two action
    tables at ``ActionBase+4`` and ``ActionBase+0xC``, adds ``0xA8``, and calls the client's own function
    there as ``Action(flag, &action, 0)`` -- ``this`` in ECX, a zero in EDX, three stack words. That is a
    code cave this project does not place, so the call itself is not reproduced.

    **What this project does instead, and why it is the same effect.** ``$GC_I_CONTROL_ACTION_*`` is the
    client's **control-action** set (``GwAu3_Const_ControlAction.au3``), and Reforged performs exactly
    these actions by *pressing* them: ``Keybinds.PressKeybind(keybind_index, 75)``
    (``routines_src/yield_src/keybinds.py:15-17``) holds down and then releases
    ``UIManager.Keydown(keybind_index, 0)`` / ``UIManager.Keyup(keybind_index, 0)``
    (``routines_src/behaviourtrees_src/keybinds.py:101,119``) -- the same pair this port already uses for
    a control action (``py4gw/map.py:1013-1014``, `Map.MissionMap.OpenWindow`). That message is the
    client's own key-action packet: the action word plus the client's two constants
    (``KeyActionPacket``, ``Py4GW_Reforged_Native: include/GW/context/ui.h:288-292``), sent to the client's
    button-action frame (``ui_methods.cpp:1408-1411``). So this member presses ``a_i_Action``.

    **The flag and the type are not carried, so the member refuses the ones whose meaning is not
    established here rather than pressing something else.** ``$GC_I_CONTROL_TYPE_ACTIVATE`` (``0x20``) is
    the flag every caller of this function in GwAu3's API uses -- the weapon-set switch and both cancels
    in ``UtilityAI`` -- and ``0`` is its default type, every caller's value; the key-action packet has no
    word for either. The deactivate flag (``0x22``, used by GwAu3's DevTools screen) and a non-zero type
    (the second action table) are therefore refused by name. What the switch and the cancels *are* is
    recorded per function in `docs/GWA3_ROUTE_MAP.md`.

    Reforged's own 75 ms hold between the press and the release (``behaviourtrees_src/keybinds.py:139``)
    has no home here either: this project carries no behaviour tree and no per-frame scheduler to hold a
    key with. `py4gw/map.py:1001-1006` records the same finding for the same pair.
    """

    if a_i_Flag != _constants.GC_I_CONTROL_TYPE_ACTIVATE or a_i_Type != 0:
        raise NotImplementedError(
            "GwAu3_Core.au3:568-573 hands the flag and the type to its injected stub, which passes the "
            "flag as the client's own first argument and uses the type to choose between two action "
            "tables (`GwAu3_Core_Assembler.au3:2101-2118`). This project performs the action by pressing "
            "it -- Reforged's route for these actions (`Keybinds.PressKeybind`) -- and the client's "
            "key-action packet carries the action alone (`include/GW/context/ui.h:288-292`), so only "
            "`$GC_I_CONTROL_TYPE_ACTIVATE` with the default type 0 -- what every API and plugin caller "
            "passes -- can be performed. `$GC_I_CONTROL_TYPE_DEACTIVATE` and a non-zero type are refused "
            "rather than pressed as if they were the activate direction. The press this member does make "
            "is `py4gw/ui_manager.py:1049`'s `UIManager.Keydown`, whose one-word packet is the reason "
            "the two words have no home."
        )

    UIManager.Keydown(int(a_i_Action), 0)
    UIManager.Keyup(int(a_i_Action), 0)


def Core_ControlAction(
    a_i_Action: Any, a_i_ActionType: Any = _constants.GC_I_CONTROL_TYPE_ACTIVATE
) -> None:
    """Perform a control action with a type (``GwAu3_Core.au3:591-593``) -- **routed**.

    ``Return Core_PerformAction($a_i_Action, $a_i_ActionType)`` and nothing else: GwAu3's second
    argument is the *flag* of the member above, which is why the default here is the activate flag and
    why this member is the one `UAI_UseSkills` and `UAI_UseSkillEx` call for their mid-cast cancel
    (``UtilityAI_Core.au3:106``, ``:233``). The route, the domain and the two refused words are
    `Core_PerformAction`'s, stated there rather than restated here.
    """

    Core_PerformAction(a_i_Action, a_i_ActionType)


def Core_ResetRuntime() -> None:
    """**NOT APPLICABLE: this resets GwAu3's own controller-side state.**

    ``GwAu3_Core.au3:689-706`` clears its own globals -- the assertion cache, the section table, the
    label table, and fourteen ``$g_i_Last*``/``$g_f_Last*`` values it keeps to answer "what changed
    since I last looked". None of them is a client record and nothing here holds an equivalent: this
    project reads when it is asked (there is no per-frame runtime to reset), so there is nothing to
    clear and no value to stand in for one.
    """


__all__ = [
    "Core_ControlAction",
    "Core_Enqueue",
    "Core_GetInGameStatus",
    "Core_GetLoginStatus",
    "Core_GetStatusError",
    "Core_GetStatusCode",
    "Core_Initialize",
    "Core_IsCharacterSelection",
    "Core_IsIngame",
    "Core_IsLoginScreen",
    "Core_PerformAction",
    "Core_ResetRuntime",
    "Core_SendPacket",
    "Memory_Read",
    "Memory_ReadPtr",
]
