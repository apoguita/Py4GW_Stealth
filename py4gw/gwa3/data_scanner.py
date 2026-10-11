"""``GwAu3_Core_Scanner.au3``'s **window and logged-character readers**.

Read from ``tools/gwa3_snippets/`` at generation time, the same mechanism `data_map`'s instance and
character-info readers use: the module this is emitted into is rewritten whole on every run.

**What is here, and what the file's other members are.** ``GwAu3_Core_Scanner.au3`` is 859 lines and
twenty-two functions, and four of them are the readers a user-facing caller asks for:
``Scanner_GetHwnd`` (``:555-560``), ``Scanner_GetWindowHandle`` (``:562-564``),
``Scanner_GetLoggedCharNames`` (``:566-574``) and ``Scanner_ScanGW`` (``:576-596``), which the third
is built on. ``Scanner_GetHwnd`` is what ``Punch_Out_Farm.au3:708`` calls and
``Scanner_GetLoggedCharNames`` is what five of the seven example scripts call (``Punch_Out_Farm`` is
the one that does not). Everything else in the file is the **pattern engine** -- the PE section table
(``:33-135``), the two Boyer-Moore scans (``:137-359``), the assertion-pattern builder (``:361-430``),
the near-call follower (``:432-461``), ``FindInRange``/``ToFunctionStart``/
``GetCallTargetAddress`` (``:463-553``), the pattern table (``:780-859``) and ``Scanner_ScanForGwAu3``
(``:598-641``) -- and each of those either answers or consumes a **client address**, or exists to feed
the assembly GwAu3 writes into the client. That engine's job in this project is the ``offsets/``
catalog and `RemoteScanner` (`py4gw/scanner/remote.py:33`), reached through ``py4gw.connect()``, so it
is not carried here.

**A window handle is not a client address.** ``Scanner_GetHwnd`` answers an ``HWND`` -- a real Windows
handle a caller acts on -- and ``Punch_Out_Farm.au3:706-735`` is what consumes it:
``Local $l_h_Wnd = $g_h_GWWindow`` / ``If $l_h_Wnd = 0 Then $l_h_Wnd = Scanner_GetHwnd($g_i_GWProcessId)``
(``:707-708``), then ``ControlSend($l_h_Wnd, "", "", "{RIGHT}")`` (``:720``) and
``ControlSend($l_h_Wnd, "", "", "{ENTER}")`` (``:735``) on the character-selection screen. That is the
one kind of client-side value this layer hands out, and it hands this one out -- from the client's own
published handle, never from a client address.
"""


from __future__ import annotations

from typing import Any


def Scanner_GetHwnd(a_i_Proc: Any) -> int:
    """The client window's handle, by process id (``GwAu3_Core_Scanner.au3:555-560``).

    GwAu3 lists every window of its own DX window class -- ``WinList("[CLASS:" &
    $GC_S_CLASS_DX_WINDOW & "]")`` (``:556``), the class being ``"ArenaNet_Dx_Window_Class"``
    (``GwAu3_Const_Scanner.au3:4``) -- and answers the first row whose process is ``$a_i_Proc``,
    ``If WinGetProcess($l_as_Wins[$l_i_Idx][1]) = $a_i_Proc Then Return $l_as_Wins[$l_i_Idx][1]``
    (``:558``). A walk that matches nothing answers AutoIt's implicit ``0``.

    This project's own window read is the client's **published** handle, not a window walk:
    `MemoryManager.GetGWWindowHandle` (`py4gw/memory/memory_manager.py:141-153`, ported from
    ``memory_manager.cpp:73-75``) reads the client's own global through ``offsets/memory.json``'s
    ``window_handle_ptr``, and it answers a real handle live -- ``592774``
    (``docs/RESEARCH.md:3040``). That is the same handle GwAu3's walk finds for the client it
    initialized, so this member is answered from it, for the pid that owns it: this connection's own
    (`ConnectedClient.pid`, `py4gw/client.py:1274`, reached as ``client.memory_manager``,
    `py4gw/client.py:1528`).

    **The divergence, in one sentence:** GwAu3 answers by *finding* a window -- enumerating the
    top-level windows of class ``ArenaNet_Dx_Window_Class`` and matching the pid with ``WinGetProcess``
    (``:556``, ``:558``) -- where this answers the handle the **connected** client publishes about
    itself, because that is the only window read this project has.

    **The read that is missing is the window lookup itself, and a pid this connection does not own is
    refused rather than answered with another process's handle.** Nothing under ``py4gw/`` enumerates
    windows, reads a window's class, or maps a window to its owning process: `Win32`
    (`py4gw/win32/win32.py:127`) discovers ``Gw.exe`` **processes** and answers no handle, and
    ``user32`` is bound under ``py4gw/`` only for the project's own windows
    (`py4gw/gui/native.py:36`, `:60-129`). So a caller holding a *different* client's pid cannot be
    answered from any member here, and inventing an enumeration inside this member would be a second
    implementation of a read the project does not have.
    """

    from ..client import current_client

    client = current_client()
    if client is None or int(a_i_Proc) != client.pid:
        raise NotImplementedError(
            "GwAu3_Core_Scanner.au3:555-560 answers this by enumerating the windows of class "
            "`ArenaNet_Dx_Window_Class` (`GC_S_CLASS_DX_WINDOW`, `py4gw/gwa3/constants.py:8668`, from "
            "`GwAu3_Const_Scanner.au3:4`) and matching the pid with `WinGetProcess` (`:556`, `:558`). "
            "That window lookup has no member in this project: nothing under `py4gw/` enumerates "
            "windows, reads a window's class or maps a window to its owning process -- `Win32` "
            "(`py4gw/win32/win32.py:127`) discovers `Gw.exe` processes and answers no handle, and "
            "`user32` is bound under `py4gw/` only for the project's own windows "
            "(`py4gw/gui/native.py:36`). The one window handle this project reads is the **connected** "
            "client's own, `MemoryManager.GetGWWindowHandle` "
            "(`py4gw/memory/memory_manager.py:141-153`, live as `592774` in `docs/RESEARCH.md:3040`), "
            "and it answers for one pid: this connection's (`py4gw/client.py:1274`). The pid passed "
            "here is not that one -- no client is connected, or this is another `Gw.exe`. Connect to "
            "that pid and call `Scanner_GetWindowHandle()`, or add the window enumeration the source "
            "uses."
        )

    return int(client.memory_manager.GetGWWindowHandle())


def Scanner_GetWindowHandle() -> int:
    """The initialized client's window handle (``GwAu3_Core_Scanner.au3:562-564``).

    ``Return $g_h_GWWindow``: GwAu3's own global, which ``Core_Initialize`` fills with
    ``Scanner_GetHwnd($l_i_ProcessID)`` (``GwAu3_Core.au3:38``, ``:49``), returns from itself
    (``:542``) and uses for ``WinSetTitle`` (``:539``), and which is ``0`` until that ran
    (``GwAu3_Const_Memory.au3:8`` -- ``Global $g_h_GWWindow = 0``).

    This project keeps no such global, so the handle is asked of the connection that owns it:
    `current_client()` (`py4gw/client.py:1931`) stands in for the global's initialized state -- no
    client connected answers ``0``, which is exactly what GwAu3's global holds then -- and the value
    itself is `Scanner_GetHwnd`'s, for this connection's pid (`py4gw/client.py:1274`). The divergence
    is the value's home, not the value: GwAu3 caches what ``Core_Initialize`` stored, this reads it
    when it is asked for, because a read in this port happens at the point of use.
    """

    from ..client import current_client

    client = current_client()
    if client is None:
        return 0
    return Scanner_GetHwnd(client.pid)


def Scanner_GetLoggedCharNames() -> str:
    """Every logged character's name, joined with ``|`` (``GwAu3_Core_Scanner.au3:566-574``).

    GwAu3's own body and both of its answers: ``If $l_as_Array[0] = 0 Then Return ""`` (``:568``), then
    element ``1`` is taken as the first name and every element up to the count is appended as
    ``"|" & $l_as_Array[$l_i_Idx]`` (``:569-572``). The array is ``Scanner_ScanGW``'s (``:567``), which
    is where every client is walked.

    Nothing is added to what the clients answered, so a machine whose only client sits at the login
    screen answers ``""`` here exactly as it does in GwAu3 -- the join is over the names the clients
    gave, and the source contributes no placeholder of its own.
    """

    names = Scanner_ScanGW()
    if names[0] == 0:
        return ""

    joined = names[1]
    for index in range(2, int(names[0]) + 1):
        joined = f"{joined}|{names[index]}"
    return joined


def Scanner_ScanGW() -> list[Any]:
    """The character name of every running client, behind an element holding the count
    (``GwAu3_Core_Scanner.au3:576-596``).

    GwAu3's steps, in its order: ``ProcessList("gw.exe")`` (``:577``); for each process
    ``Memory_Open``, and **only** when the handle opened and ``Scanner_InitializeSections()`` answered
    true, ``Scanner_ScanForCharname()`` (``:585``) then the count (``:586``) and
    ``Player_GetCharName()`` (``:587``); ``Memory_Close()`` for every process either way (``:589``);
    and last the count written into element ``0`` and the array trimmed (``:592-593``). The answer is
    an AutoIt array whose ``[0]`` is the count and whose ``[1..count]`` are the names -- the shape
    `Scanner_GetLoggedCharNames` indexes.

    The open-and-scan pair is this project's read-only connection: ``Memory_Open`` plus
    ``Scanner_InitializeSections`` is ``py4gw.connect(entry, game_thread=False)``, the route
    `Core_Initialize`'s port already takes for the same two steps (`py4gw/gwa3/core.py:86-88`, and
    ``:70-72`` for what that call covers of GwAu3's own open-and-scan), and a client whose open or
    scan fails is **skipped**, which is what ``$g_h_GWProcess <> 0 And
    Scanner_InitializeSections()`` does (``:584``). The process list is the layer's own discovery,
    `_client_entries` (`py4gw/gwa3/core.py:54-57`) -- ``ProcessList("gw.exe")`` written over
    `Win32.find_guild_wars` (`py4gw/win32/win32.py:127`) -- and ``Memory_Close`` is
    `py4gw.disconnect` (`py4gw/client.py:1915`), which runs for every client the loop opened, before
    the count is taken, exactly as ``:589`` runs before ``:592``.

    **The name is this project's own read, which is the one divergence here.**
    ``Scanner_ScanForCharname`` (``:643-682``) finds a fixed byte pattern in the client's ``.text``
    section (``:644``), computes the match's address (``:669``) and reads the pointer at
    ``match + 6 - 0xF`` (``:646``, ``:674``), which ``Player_GetCharName`` then reads as ``WCHAR[30]``
    (``GwAu3_Data_Player.au3:4-6``); this layer scans nothing and hands out no client address, so the
    name is `Player.GetName` (`py4gw/player.py:491`) -- ``Agent.GetNameByID(Player.GetAgentID())``, the
    same route `Core_Initialize`'s port reads the character name by (`py4gw/gwa3/core.py:88`) -- which
    is an **in-game** read where GwAu3's pointer read is not known to need a character to be in game
    (unresolved here), so a client at the character-selection screen contributes ``""`` to the count
    either way: ``:586`` counts every client that opened and ``:585`` discards the scan's own result.

    **A name read that fails answers ``""`` here rather than raising, which is GwAu3's own answer for
    that case:** ``Memory_Read``'s ``DllStructGetData`` on a structure its ``ReadProcessMemory`` never
    filled returns ``""``. This project's read raises instead, so it is caught -- the same three lines
    `Core_Initialize`'s port uses for this same call (`py4gw/gwa3/core.py:88-91`).

    **The caller's own connection does not survive this call, and it does not in GwAu3 either.**
    ``Memory_Close`` leaves ``$g_h_GWProcess`` at ``0`` (`GwAu3_Core_Memory.au3:10-14`), so GwAu3's own
    GUI callers re-initialize after asking for the name list; ``py4gw.connect`` begins by dropping the
    current connection (`py4gw/client.py:1894`), so a script that calls this while connected is left in
    the same state the source leaves its caller in -- the source's own behaviour, kept rather than
    softened with a re-connect this member would have had to invent.
    """

    import py4gw

    from ..player import Player
    from .core import _client_entries

    count = 0
    names: list[Any] = [0]

    for entry in _client_entries():
        try:
            py4gw.connect(entry, game_thread=False)
        except (OSError, RuntimeError):
            # Memory_Open left $g_h_GWProcess at 0, or Scanner_InitializeSections answered false
            # (``:583-584``): the client is skipped, and nothing was opened to close.
            continue

        try:
            name: Any = str(Player.GetName() or "")
        except Exception:  # noqa: BLE001 - the read GwAu3's Memory_Read cannot fail
            name = ""

        count += 1
        names.append(name)

        # Memory_Close() -- the end of this iteration, before the next client is opened (``:589``).
        py4gw.disconnect()

    names[0] = count
    return names

__all__ = ["Scanner_GetHwnd", "Scanner_GetWindowHandle", "Scanner_GetLoggedCharNames", "Scanner_ScanGW"]
