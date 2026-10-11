"""Generate ``tools/autoit/Stealth_GwAu3.au3`` -- the AutoIt side of the GwAu3 bridge.

Part of the GwAu3-compatible layer; see ``docs/GWA3_COMPAT_SPEC.md`` and the interpreter readings in
``tools/autoit/READINGS.md``.

Run from the project root:

    python tools/autoit/generate_stealth_udf.py

**Why generated.** One AutoIt function per routine the Python layer implements. Re-declaring them by
hand is a second surface to keep in step with ``py4gw/gwa3``, and the two would drift the first time a
module landed. The signatures are not guessed either: each is read from GwAu3's own ``Func``
declaration, with the default values GwAu3 gives them, so a migrating script's call shape is the same
on both sides of the bridge.

**What the file is.** A drop-in replacement for the includes a GwAu3 script already has. The author
includes this one instead, and their calls -- ``Agent_GetAgentInfo(-2, "X")`` -- keep their names,
their arguments and their defaults. What changes underneath is that the call travels to the worker
rather than being executed by AutoIt.

**What it is not.** It is not a reimplementation. There is no arithmetic, no memory read and no packet
here: each wrapper marshals its arguments into one JSON line, reads one reply line back, and returns
the result -- or returns GwAu3's own failure shape when the worker refused. The logic lives in Python,
where it is generated from GwAu3's sources and tested offline.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SURFACE_CSV = REPO_ROOT / "external" / "GwAu3_modules_surface.csv"
GWAU3_ROOT = REPO_ROOT / "external" / "GwAu3"
GWAU3_API = GWAU3_ROOT / "API"
OUTPUT_PATH = REPO_ROOT / "tools" / "autoit" / "Stealth_GwAu3.au3"
CONSTANTS_OUTPUT_PATH = REPO_ROOT / "tools" / "autoit" / "Stealth_GwAu3_Constants.au3"

#: GwAu3 routines this layer implements **in AutoIt**, not through the bridge, transcribed from
#: GwAu3's own bodies.
#:
#: **Why these and not others.** A bridged wrapper is the right shape when the work is a client read
#: or call. These are not: `Log_*` renders into the script's own RichEdit control and calls the
#: script's own registered callback, `Core_AutoStart` calls the script's own `StartBot()` and reads
#: the script's own `$g_bAutoStart`/`$g_s_MainCharName`, and `Core_GetGuildWarsWindow` asks *Windows*
#: for the window whose title is the character's. Round-tripping any of them through Python would mean
#: sending a window handle and a function name across a pipe to be handed straight back.
#:
#: They are transcribed rather than summarised: the same gate order, the same colours (BGR --
#: RichEdit's convention, as GwAu3's own comment warns), the same `[time] [TYPE] [author] message`
#: format, the same 30,000-character wipe, the same callback validation at registration.
#:
#: `Core_AutoStart` is the one with a deliberate divergence, and it says so in the body: GwAu3 drives
#: the character-select screen with `ControlSend(..., "{RIGHT}")` and `ControlSend(..., "{ENTER}")`,
#: and input synthesis into another process's window is the mechanism this project refuses by name.
AUTOIT_HAND_WRITTEN: dict[str, str] = {
    "Log_SetCallback": '''Func Log_SetCallback($a_s_Callback)
	If $a_s_Callback = "" Then
		$g_s_Log_Callback = ""
		Return True
	EndIf

	If Not IsFunc(Execute($a_s_Callback)) Then Return SetError(1, 0, False)

	$g_s_Log_Callback = $a_s_Callback
	Return True
EndFunc''',
    "Log_Message": '''Func Log_Message($a_s_Message, $a_i_MsgType = $GC_I_LOG_MSGTYPE_INFO, $a_s_Author = "AutoIt", $a_h_EditText = 0)
	; the DEBUG gate runs BEFORE any dispatch, so callback registrants inherit the filter
	If $a_i_MsgType = $GC_I_LOG_MSGTYPE_DEBUG And Not $g_b_DebugMode Then Return

	If $g_s_Log_Callback <> "" Then
		Call($g_s_Log_Callback, $a_s_Message, $a_i_MsgType, $a_s_Author)
		Return
	EndIf

	If $a_h_EditText = 0 Then Return ; no callback, no UI sink: nothing to render into

	Local $l_s_TypeText
	Local $l_i_Color ; BGR
	Switch $a_i_MsgType
		Case $GC_I_LOG_MSGTYPE_DEBUG
			$l_s_TypeText = "DEBUG"
			$l_i_Color = 0xFFA500
		Case $GC_I_LOG_MSGTYPE_WARNING
			$l_s_TypeText = "WARNING"
			$l_i_Color = 0x00C8FF
		Case $GC_I_LOG_MSGTYPE_ERROR
			$l_s_TypeText = "ERROR"
			$l_i_Color = 0x0000CC
		Case $GC_I_LOG_MSGTYPE_CRITICAL
			$l_s_TypeText = "CRITICAL"
			$l_i_Color = 0x0000FF
		Case Else
			$l_s_TypeText = "INFO"
			$l_i_Color = 0x008000
	EndSwitch

	Local $l_s_LogText = "[" & Log_GetCurrentTime() & "] [" & $l_s_TypeText & "] [" & $a_s_Author & "] " & $a_s_Message & @CRLF

	If _GUICtrlRichEdit_GetTextLength($a_h_EditText) > 30000 Then _GUICtrlRichEdit_SetText($a_h_EditText, "")

	_GUICtrlRichEdit_SetSel($a_h_EditText, -1, -1)
	_GUICtrlRichEdit_SetCharColor($a_h_EditText, $l_i_Color)
	_GUICtrlRichEdit_AppendText($a_h_EditText, $l_s_LogText)
	_GUICtrlEdit_Scroll($a_h_EditText, $SB_SCROLLCARET)
EndFunc''',
    "Log_Debug": '''Func Log_Debug($a_s_Message, $a_s_Author = "AutoIt", $a_h_EditText = 0)
	Log_Message($a_s_Message, $GC_I_LOG_MSGTYPE_DEBUG, $a_s_Author, $a_h_EditText)
EndFunc''',
    "Log_Info": '''Func Log_Info($a_s_Message, $a_s_Author = "AutoIt", $a_h_EditText = 0)
	Log_Message($a_s_Message, $GC_I_LOG_MSGTYPE_INFO, $a_s_Author, $a_h_EditText)
EndFunc''',
    "Log_Warning": '''Func Log_Warning($a_s_Message, $a_s_Author = "AutoIt", $a_h_EditText = 0)
	Log_Message($a_s_Message, $GC_I_LOG_MSGTYPE_WARNING, $a_s_Author, $a_h_EditText)
EndFunc''',
    "Log_Error": '''Func Log_Error($a_s_Message, $a_s_Author = "AutoIt", $a_h_EditText = 0)
	Log_Message($a_s_Message, $GC_I_LOG_MSGTYPE_ERROR, $a_s_Author, $a_h_EditText)
EndFunc''',
    "Log_Critical": '''Func Log_Critical($a_s_Message, $a_s_Author = "AutoIt", $a_h_EditText = 0)
	Log_Message($a_s_Message, $GC_I_LOG_MSGTYPE_CRITICAL, $a_s_Author, $a_h_EditText)
EndFunc''',
    "Log_SetDebugMode": '''Func Log_SetDebugMode($a_b_Enable = True)
	$g_b_DebugMode = $a_b_Enable
	Log_Message("Debug Mode " & ($a_b_Enable ? "Enabled" : "Disabled"), $GC_I_LOG_MSGTYPE_INFO, "SetDebugMode")
EndFunc''',
    "Log_GetCurrentTime": '''Func Log_GetCurrentTime()
	Return StringFormat("%02d:%02d:%02d", @HOUR, @MIN, @SEC)
EndFunc''',
    "Core_GetGuildWarsWindow": '''Func Core_GetGuildWarsWindow()
	Local $l_s_expectedTitle = "Guild Wars - " & $g_s_MainCharName

	Local $l_h_Wnd = WinGetHandle($l_s_expectedTitle)
	If $l_h_Wnd <> 0 Then Return $l_h_Wnd
EndFunc''',
    "Core_AutoStart": '''Func Core_AutoStart()
	If $g_bAutoStart And $g_s_MainCharName <> "" Then
		Sleep(2000)
		StartBot()
		Local $l_h_GWWindow = Core_GetGuildWarsWindow()
		If $l_h_GWWindow = 0 Then
			_Exit()
		EndIf

		; GwAu3 walks the character-select screen from here with `ControlSend($l_h_GWWindow, "", "",
		; "{RIGHT}")` until the wanted character is highlighted, then presses `{ENTER}`
		; (`GwAu3_Core.au3:604-647`). That arm is **refused**: synthesising keystrokes into another
		; process's window is the input-synthesis mechanism this project does not use, and
		; `docs/GWA3_ROUTE_MAP.md` names the rule. What remains is GwAu3's own waiting after the
		; character loads, which is the same call it makes.
		Map_WaitMapLoading()
		Sleep(1000)
	EndIf
EndFunc''',
}

#: Mutable globals GwAu3's own modules declare (not `Const`, so not in the generated constants file)
#: and that the hand-written block above needs. GwAu3 declares them where its log module's header says
#: they are declared -- in its constants include -- and this is the same state under the same names, so
#: a migrating script that reads or writes `$g_b_DebugMode` gets the same behaviour.
AUTOIT_HAND_WRITTEN_GLOBALS = '''; State GwAu3's log module keeps, declared here because GwAu3 declares it in its constants include
; (`GwAu3_Const_LogMessage.au3:5` is `Global $g_b_DebugMode = False`) and the generated constants file
; carries `Const`/`Enum` only. `$g_s_Log_Callback` is the log module's own (`GwAu3_Core_LogMessages.au3:21`).
Global $g_b_DebugMode = False
Global $g_s_Log_Callback = ""
'''

#: `Func Name(params)` -- GwAu3's own declaration, which is the record. The CSV index below is an
#: index, and this generator used to read *it* for both the surface and the signatures. That is how the
#: UDF came to declare 648 wrappers while GwAu3's own scripts call 667 functions: the index was built
#: from `API/Modules/{Cmd,Data}` alone, so the other 345 -- `Core_Initialize`, `Log_Message`, `UAI_*`,
#: `Assembler_*`, `Scanner_*` and the rest -- were invisible here *and* in the route map *and* in the
#: mechanism map. AutoIt rejects a call to an undeclared function at compile time
#: (`tools/autoit/READINGS.md`), so each of those was a migrated script that could not start.
FUNC_DECL = re.compile(r"^Func\s+(?P<name>[A-Za-z_]\w*)\s*\((?P<params>.*)$", re.IGNORECASE)

# GwAu3's own AutoIt parameter spellings, kept so a migrated call reads the same. A parameter name
# that collides with an AutoIt built-in or keyword is suffixed; nothing else is renamed.
RESERVED = {
    "default", "and", "or", "not", "true", "false", "if", "then", "else", "for", "next", "while",
    "wend", "do", "until", "select", "case", "switch", "endswitch", "func", "endfunc", "return",
    "local", "global", "dim", "const", "redim", "exit", "exitloop", "continueloop", "step", "to",
    "in", "null", "string", "number", "array", "obj", "ptr", "hwnd",
}


def _logical_lines(path: Path) -> list[str]:
    """Join AutoIt continuation lines, so a `Func` whose parameter list spans lines is one line."""

    joined: list[str] = []
    pending: str | None = None
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        text = raw.split(";", 1)[0].rstrip()
        if pending is not None:
            text = pending + " " + text.strip()
        if text.endswith("_"):
            pending = text[:-1].rstrip()
            continue
        pending = None
        if text.strip():
            joined.append(text)
    if pending is not None:
        joined.append(pending)
    return joined


def source_signatures() -> dict[str, tuple[str, list[tuple[str, str]]]]:
    """``{name: (source file, [(parameter, default), ...])}`` from GwAu3's own `Func` lines.

    Read from the record, not from ``GwAu3_modules_surface.csv``: the index carries only the modules it
    was built from, and a signature this UDF gets wrong is a migrated call that passes its arguments
    into the wrong slots.
    """

    signatures: dict[str, tuple[str, list[tuple[str, str]]]] = {}
    for path in sorted(GWAU3_API.rglob("*.au3")):
        for line in _logical_lines(path):
            match = FUNC_DECL.match(line)
            if match is None:
                continue
            name = match.group("name")
            body = match.group("params")
            # The parameter list ends at the paren that **closes it**, not at the first `)` on the
            # line: a default value may itself be a call -- `Map_TravelTo($id, $lang =
            # Map_GetCharacterInfo("Language"))` -- and cutting at the first paren truncated the
            # signature and produced a `Func` AutoIt refused to compile (measured: "Badly formatted
            # Func statement").
            depth = 1
            end = len(body)
            for position, character in enumerate(body):
                if character == "(":
                    depth += 1
                elif character == ")":
                    depth -= 1
                    if depth == 0:
                        end = position
                        break
            body = body[:end]
            parsed: list[tuple[str, str]] = []
            broken = False
            for piece in _split_params(body):
                piece = piece.strip()
                if not piece:
                    continue
                item = re.match(r"^(?P<name>\$?\w+)\s*(?:=\s*(?P<default>.*))?$", piece)
                if item is None:
                    broken = True
                    break
                parsed.append(
                    (item.group("name").lstrip("$"), (item.group("default") or "").strip())
                )
            signatures.setdefault(
                name,
                (str(path.relative_to(GWAU3_ROOT)).replace("\\", "/"), [] if broken else parsed),
            )
    return signatures


def called_surface() -> dict[str, int]:
    """``{name: call sites}`` for every GwAu3 function the checkout *calls*.

    Declarations are excluded: every `Func` line ends in `(` and would otherwise count as a call site
    for itself, which is how an earlier measurement reported "5,685 functions called" -- every function
    GwAu3 declares, called by nobody.
    """

    declared = set(source_signatures())
    called: dict[str, int] = {}
    for path in sorted(GWAU3_ROOT.rglob("*.au3")):
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            code = raw.split(";", 1)[0]
            if code.lstrip().lower().startswith("func "):
                continue
            for name in re.findall(r"\b([A-Za-z_]\w*)\s*\(", code):
                if name in declared:
                    called[name] = called.get(name, 0) + 1
    return called


def parse_signatures() -> dict[str, list[tuple[str, str]]]:
    """``{function: [(name, default), ...]}`` from GwAu3's own declarations.

    ``default`` is the literal text GwAu3 writes after ``=``, or ``""`` when the parameter has none.
    A trailing parameter without a default after one that has is impossible in AutoIt, so the order is
    preserved as written and emitted verbatim.
    """

    signatures = {name: params for name, (_, params) in source_signatures().items()}
    if signatures:
        return signatures

    # Only if GwAu3's sources are not where they are expected: fall back to the index, and say so by
    # returning what it has rather than silently generating an empty UDF.
    if not SURFACE_CSV.is_file():
        return signatures

    with SURFACE_CSV.open(encoding="utf-8", errors="replace", newline="") as handle:
        for row in csv.DictReader(handle):
            name = (row.get("Name") or "").strip()
            params = (row.get("Params") or "").strip()
            if not name:
                continue

            parsed: list[tuple[str, str]] = []
            if params:
                for piece in _split_params(params):
                    piece = piece.strip()
                    if not piece:
                        continue
                    match = re.match(r"^(?P<name>\$?\w+)\s*(?:=\s*(?P<default>.*))?$", piece)
                    if match is None:
                        parsed = []
                        break
                    parameter = match.group("name").lstrip("$")
                    default = (match.group("default") or "").strip()
                    parsed.append((parameter, default))
            signatures[name] = parsed
    return signatures


def _split_params(params: str) -> list[str]:
    """Split a parameter list on commas that are not inside quotes or parentheses."""

    pieces: list[str] = []
    current: list[str] = []
    quote: str | None = None
    depth = 0
    for character in params:
        if quote is not None:
            current.append(character)
            if character == quote:
                quote = None
        elif character in ("'", '"'):
            quote = character
            current.append(character)
        elif character in "([":
            depth += 1
            current.append(character)
        elif character in ")]":
            depth -= 1
            current.append(character)
        elif character == "," and depth == 0:
            pieces.append("".join(current))
            current = []
        else:
            current.append(character)
    if current:
        pieces.append("".join(current))
    return pieces


def _autoit_parameter(name: str) -> str:
    """A parameter name AutoIt accepts, keeping GwAu3's spelling where it can."""

    safe = re.sub(r"\W", "_", name)
    if safe.lower() in RESERVED or safe == "":
        safe = f"{safe}_"
    return "$" + safe


def _default_literal(default: str) -> str:
    """GwAu3's default, as AutoIt text this UDF can carry."""

    if default == "":
        return ""
    # GwAu3 writes `True`, `False`, strings in either quote and numbers. All are valid AutoIt, so the
    # text is passed through unchanged -- a rewritten default is a different default.
    return default


def _fallback_literal(name: str) -> str:
    """What the wrapper returns when the call failed: GwAu3's own empty shape for that call.

    AutoIt has no exceptions, so a failure has to come back as a value the caller's own comparisons
    already handle. Which value depends on what the routine answers:

    * GwAu3's ``Get*``/``*Info`` readers answer ``0`` for a field they cannot resolve, so a failed one
      answers ``0``.
    * The ``X_GetName``-shaped readers answer ``""``.
    * ``_Stealth_Call``'s own default is ``0``.

    This is deliberately not a guess at a *plausible* value: it is the same empty the routine itself
    returns on its own failure paths, which is why a migrated ``If Not $x Then`` keeps working. The
    distinction reaches the caller through ``@error`` and ``$g_s_Stealth_ErrorKind``, never through the
    return value.
    """

    if name.endswith("GetName") or "_Name" in name:
        return '""'
    return "0"


def generate_wrapper(name: str, parameters: list[tuple[str, str]], implemented: bool) -> str:
    """One AutoIt function that asks the worker for ``name``."""

    declared = []
    argument_names = []
    for parameter, default in parameters:
        autoit_name = _autoit_parameter(parameter)
        literal = _default_literal(default)
        declared.append(f"{autoit_name}" + (f" = {literal}" if literal else ""))
        argument_names.append(autoit_name)

    signature = ", ".join(declared)
    fallback = _fallback_literal(name)

    # The fallback is passed positionally: `_Stealth_Call`'s third parameter is optional, and naming
    # it would be wrong when the routine itself has a parameter by that name.
    lines = [f"Func {name}({signature})"]
    if not implemented:
        lines.append("\t; GwAu3 declares this and the Python layer has not built it yet. The call is")
        lines.append("\t; still made, so the worker's own `not_implemented` answer reaches the caller")
        lines.append("\t; instead of a silent empty return.")
    lines.append(f"\tLocal $aArgs[{max(len(argument_names), 1)}]")
    if argument_names:
        for index, argument in enumerate(argument_names):
            lines.append(f"\t$aArgs[{index}] = {argument}")
    else:
        lines.append("\tReDim $aArgs[0]")

    # **@error has to be re-set on the way out, and this is measured, not defensive.**
    # `Return Inner_()` does NOT carry @error out of the function -- AutoIt resets it when a function
    # returns a call expression (tools/autoit/READINGS.md, probe_error_macro.au3: `nested return`
    # reported @error=0 where the direct call reported 2). So a wrapper written as
    # `Return _Stealth_Call(...)` would silently swallow every failure's @error, and a migrated
    # script's `If @error Then` would never fire. Capturing the result first and re-setting the macro
    # is what makes the documented contract true.
    lines.append(f'\tLocal $vResult = _Stealth_Call("{name}", $aArgs, {fallback})')
    lines.append("\tReturn SetError(@error, 0, $vResult)")
    lines.append("EndFunc")
    return "\n".join(lines)


HEADER = '''#include-once
; =============================================================================================
; Stealth_GwAu3.au3 -- the AutoIt side of the GwAu3 bridge.
;
; GENERATED. Do not edit by hand -- run `python tools/autoit/generate_stealth_udf.py`.
;
; What this is
; ------------
; A drop-in replacement for the GwAu3 includes a script already has. A migrating script includes this
; file instead and its calls keep their names, arguments, order and defaults:
;
;     #include "Stealth_GwAu3.au3"
;
;     _Stealth_BridgeStart("C:\\Users\\you\\Py4GW_Stealth")   ; once, at the top
;     Local $fX = Agent_GetAgentInfo(-2, "X")
;     Local $iHP = Agent_GetAgentInfo(-2, "HP")
;     _Stealth_BridgeStop()
;
; What it is NOT
; --------------
; There is no game logic here. No memory is read, no packet is built and no arithmetic is done: each
; wrapper marshals its arguments into one JSON line, the Python worker answers in one JSON line, and
; the result comes back. The logic lives in `py4gw/gwa3`, where it is generated from GwAu3's own
; sources and tested offline.
;
; Elevation
; ---------
; Do NOT put #RequireAdmin in a script that uses this. The *connection* needs an elevated shell -- the
; project asserts it and refuses without it -- but the bridge transport does not, and #RequireAdmin
; makes AutoIt refuse to start the whole script unelevated, producing no output at all rather than a
; described failure. Start the script from an elevated shell instead.
;
; What a failure looks like
; -------------------------
; AutoIt has no exceptions, so a failure is reported through @error and $g_s_Stealth_Error, and the
; returned value is GwAu3's own empty shape for the call (0, False or ""):
;
;     $value = Agent_GetAgentInfo(-2, "X")
;     If @error Then
;         ConsoleWrite("bridge: " & $g_s_Stealth_Error & @CRLF)
;     EndIf
;
; The four kinds are distinguishable in $g_s_Stealth_ErrorKind, which matters because a migrating
; script should be able to tell "not built yet" from "this project will not do that":
;
;     not_implemented   GwAu3 declares the name; this layer has not built it yet
;     refused           the layer declines, and says why (a forged packet, or a key needing the client)
;     unknown           no such function -- a typo, since GwAu3 does not declare it either
;     error             the call ran and raised; the message says how
;     bad_request       the request never reached a routine -- a bridge bug, not a caller's
;     transport         the worker is not running, or died
; =============================================================================================

#include <AutoItConstants.au3>

; The worker process, or 0 when it is not running.
Global $g_i_Stealth_Pid = 0

; The last failure's kind and detail. Empty on success.
Global $g_s_Stealth_ErrorKind = ""
Global $g_s_Stealth_Error = ""

; A request's id, so a reply can be matched to its call. Not required by the worker; kept because a
; wrong reply is much easier to diagnose when it says which request it answers.
Global $g_i_Stealth_RequestId = 0

; The repo root the worker was started from, so BridgeStop can report where it was.
Global $g_s_Stealth_Root = ""


; ---------------------------------------------------------------------------------------------
; Start the worker.
;
; `$sRepoRoot` is the Py4GW_Stealth checkout. The worker is Python, started with `-u`, which matters:
; without it Python buffers stdout and the first reply never arrives.
; ---------------------------------------------------------------------------------------------
Func _Stealth_BridgeStart($sRepoRoot, $sPython = "python")
	If $g_i_Stealth_Pid <> 0 Then Return SetError(0, 0, True)

	Local $sLauncher = $sRepoRoot & "\\tools\\autoit\\run_bridge_worker.py"
	If Not FileExists($sLauncher) Then
		_Stealth_SetError("transport", "worker launcher not found: " & $sLauncher)
		Return SetError(1, 0, False)
	EndIf

	Local $sCmd = '"' & $sPython & '" -u "' & $sLauncher & '"'
	Local $iPid = Run($sCmd, $sRepoRoot, @SW_HIDE, $STDIN_CHILD + $STDOUT_CHILD + $STDERR_CHILD)
	If $iPid = 0 Then
		_Stealth_SetError("transport", "could not start the worker: " & $sCmd)
		Return SetError(2, 0, False)
	EndIf

	$g_i_Stealth_Pid = $iPid
	$g_s_Stealth_Root = $sRepoRoot

	; The worker announces itself on stderr; draining it now both confirms it started and keeps its
	; chatter out of the way of protocol replies, which only ever arrive on stdout.
	Local $sBanner = ""
	Local $iWaited = 0
	While $iWaited < 10000
		Local $sChunk = StderrRead($iPid)
		If @error Then ExitLoop
		If $sChunk <> "" Then
			$sBanner &= $sChunk
			If StringInStr($sBanner, @LF) Then ExitLoop
		EndIf
		Sleep(25)
		$iWaited += 25
	WEnd

	If $sBanner = "" Then
		_Stealth_SetError("transport", "the worker started but said nothing; it may have failed to import")
		Return SetError(3, 0, False)
	EndIf

	_Stealth_ClearError()
	Return True
EndFunc


; Stop the worker and clear the error state.
Func _Stealth_BridgeStop()
	If $g_i_Stealth_Pid = 0 Then Return False
	ProcessClose($g_i_Stealth_Pid)
	$g_i_Stealth_Pid = 0
	_Stealth_ClearError()
	Return True
EndFunc


Func _Stealth_BridgeRunning()
	Return $g_i_Stealth_Pid <> 0
EndFunc


; ---------------------------------------------------------------------------------------------
; One call: marshal the arguments, write one line, read one line.
;
; `$sFallback` is what to return when the call failed -- GwAu3's own empty shape for that call, so a
; migrating script's `If Not $x Then` keeps working. It is never a stand-in for a value the client
; would have given.
; ---------------------------------------------------------------------------------------------
Func _Stealth_Call($sName, $aArgs, $sFallback = 0)
	_Stealth_ClearError()

	If $g_i_Stealth_Pid = 0 Then
		_Stealth_SetError("transport", "the bridge is not running; call _Stealth_BridgeStart first")
		Return SetError(1, 0, $sFallback)
	EndIf

	If Not _Stealth_WorkerAlive() Then
		_Stealth_SetError("transport", "the worker process has exited")
		$g_i_Stealth_Pid = 0
		Return SetError(2, 0, $sFallback)
	EndIf

	$g_i_Stealth_RequestId += 1
	Local $sRequest = '{"call":"' & _Stealth_Escape($sName) & '","id":' & $g_i_Stealth_RequestId & ',"args":[' & _Stealth_Args($aArgs) & ']}'

	StdinWrite($g_i_Stealth_Pid, $sRequest & @LF)
	If @error Then
		_Stealth_SetError("transport", "could not write to the worker (error " & @error & ")")
		Return SetError(3, 0, $sFallback)
	EndIf

	Local $sReply = _Stealth_ReadLine()
	Local $iReadError = @error
	If $iReadError Then
		_Stealth_SetError("transport", "no reply from the worker (error " & $iReadError & ")")
		Return SetError(4, 0, $sFallback)
	EndIf

	; `_Stealth_DecodeReply` answers with `SetError` for every failure, and a helper that returned its
	; result straight through would lose that -- so it is read immediately and re-set here.
	Local $vResult = _Stealth_DecodeReply($sReply, $sFallback)
	Local $iDecodeError = @error
	Return SetError($iDecodeError, 0, $vResult)
EndFunc


; Read one whole reply line, or fail. StdoutRead hands back whatever has arrived, so a partial line is
; the normal case and has to be accumulated.
Func _Stealth_ReadLine($iTimeoutMs = 30000)
	Local $sBuffer = ""
	Local $iWaited = 0
	While $iWaited < $iTimeoutMs
		Local $sChunk = StdoutRead($g_i_Stealth_Pid)
		If @error Then Return SetError(1, 0, "")
		If $sChunk <> "" Then
			$sBuffer &= $sChunk
			Local $iEnd = _Stealth_LineEnd($sBuffer)
			If $iEnd > 0 Then Return StringLeft($sBuffer, $iEnd - 1)
		EndIf
		Sleep(10)
		$iWaited += 10
	WEnd
	Return SetError(2, 0, "")
EndFunc


; Where the first line ends, or 0 when none has arrived yet. @CRLF and a bare @LF are both accepted,
; because a pipe can deliver either and Python's own output uses @LF.
Func _Stealth_LineEnd($sText)
	Local $iLf = StringInStr($sText, @LF)
	If $iLf = 0 Then Return 0
	If $iLf > 1 And StringMid($sText, $iLf - 1, 1) = @CR Then Return $iLf
	Return $iLf + 1
EndFunc


Func _Stealth_WorkerAlive()
	Return ProcessExists($g_i_Stealth_Pid) <> 0
EndFunc


Func _Stealth_SetError($sKind, $sDetail)
	$g_s_Stealth_ErrorKind = $sKind
	$g_s_Stealth_Error = $sDetail
EndFunc


Func _Stealth_ClearError()
	$g_s_Stealth_ErrorKind = ""
	$g_s_Stealth_Error = ""
EndFunc


; A JSON string with nothing in it that can break the frame.
Func _Stealth_Escape($sText)
	Local $sOut = $sText
	$sOut = StringReplace($sOut, "\\", "\\\\")
	$sOut = StringReplace($sOut, '"', '\\"')
	$sOut = StringReplace($sOut, @CR, "\\r")
	$sOut = StringReplace($sOut, @LF, "\\n")
	$sOut = StringReplace($sOut, @TAB, "\\t")
	Return $sOut
EndFunc


; The argument array as JSON text. AutoIt's own types decide the JSON type: a String is quoted, a
; number or boolean is not. An array parameter is refused rather than mis-serialised.
Func _Stealth_Args($aArgs)
	If Not IsArray($aArgs) Then Return ""
	Local $sOut = ""
	For $i = 0 To UBound($aArgs) - 1
		If $i > 0 Then $sOut &= ","
		Local $vValue = $aArgs[$i]
		If IsArray($vValue) Then
			_Stealth_SetError("bad_request", "argument " & $i & " is an array; the bridge carries scalars only")
			Return ""
		EndIf
		If IsString($vValue) Then
			$sOut &= '"' & _Stealth_Escape($vValue) & '"'
		ElseIf IsBool($vValue) Then
			$sOut &= ($vValue ? "true" : "false")
		ElseIf IsInt($vValue) Or IsFloat($vValue) Then
			$sOut &= String($vValue)
		ElseIf $vValue = Default Or $vValue = Null Then
			$sOut &= "null"
		Else
			$sOut &= '"' & _Stealth_Escape(String($vValue)) & '"'
		EndIf
	Next
	Return $sOut
EndFunc


; A reply line -> a value, or a described failure.
Func _Stealth_DecodeReply($sReply, $sFallback)
	Local $bOk = StringInStr($sReply, '"ok":true') > 0

	If Not $bOk Then
		Local $sKind = _Stealth_JsonString($sReply, "kind")
		Local $sDetail = _Stealth_JsonString($sReply, "detail")
		If $sKind = "" And StringInStr($sReply, '"ok":false') = 0 Then
			_Stealth_SetError("bad_request", "the reply was not this protocol's shape: " & $sReply)
			Return SetError(1, 0, $sFallback)
		EndIf
		_Stealth_SetError($sKind, $sDetail)
		Return SetError(1, 0, $sFallback)
	EndIf

	Local $sResult = _Stealth_JsonValue($sReply, "result")
	If @error Then
		_Stealth_SetError("bad_request", "the reply carried no result: " & $sReply)
		Return SetError(2, 0, $sFallback)
	EndIf

	; A JSON string comes back as a string, a number as a number, a boolean as a boolean -- so a
	; migrated script's own comparisons keep their meaning.
	If StringLeft($sResult, 1) = '"' Then Return _Stealth_JsonUnescape(StringTrimRight(StringTrimLeft($sResult, 1), 1))
	If $sResult = "true" Then Return True
	If $sResult = "false" Then Return False
	If $sResult = "null" Then Return $sFallback
	If StringRegExp($sResult, "^-?\\d+$") Then Return Number($sResult)
	If StringRegExp($sResult, "^-?\\d*\\.\\d+([eE][-+]?\\d+)?$") Then Return Number($sResult)
	Return $sResult
EndFunc


; The raw text of a top-level key's value, braces and all. Deliberately simple: the replies this
; bridge produces have a flat shape, and a general JSON parser here would be a second thing to keep
; right. A value that is not found sets @error.
Func _Stealth_JsonValue($sJson, $sKey)
	Local $sNeedle = '"' & $sKey & '":'
	Local $iAt = StringInStr($sJson, $sNeedle)
	If $iAt = 0 Then Return SetError(1, 0, "")
	$iAt += StringLen($sNeedle)
	Local $sRest = StringMid($sJson, $iAt)
	Local $iLength = StringLen($sRest)

	; A string runs to its closing quote, honouring backslash escapes.
	If StringLeft($sRest, 1) = '"' Then
		Local $i = 2
		While $i <= $iLength
			Local $sChar = StringMid($sRest, $i, 1)
			If $sChar = "\\" Then
				$i += 2
				ContinueLoop
			EndIf
			If $sChar = '"' Then Return StringLeft($sRest, $i)
			$i += 1
		WEnd
		Return SetError(2, 0, "")
	EndIf

	; A structure runs to its matching brace.
	If StringLeft($sRest, 1) = "{" Then
		Local $iDepth = 0
		Local $i = 1
		While $i <= $iLength
			Local $sChar = StringMid($sRest, $i, 1)
			If $sChar = "{" Then $iDepth += 1
			If $sChar = "}" Then
				$iDepth -= 1
				If $iDepth = 0 Then Return StringLeft($sRest, $i)
			EndIf
			$i += 1
		WEnd
		Return SetError(3, 0, "")
	EndIf

	; A scalar runs to the next comma or closing brace.
	Local $iComma = StringInStr($sRest, ",")
	Local $iBrace = StringInStr($sRest, "}")
	Local $iStop = $iLength + 1
	If $iComma > 0 And $iComma < $iStop Then $iStop = $iComma
	If $iBrace > 0 And $iBrace < $iStop Then $iStop = $iBrace
	Return StringStripWS(StringLeft($sRest, $iStop - 1), 3)
EndFunc


; A top-level string value, without its quotes. Used for the error kind and detail.
Func _Stealth_JsonString($sJson, $sKey)
	Local $sValue = _Stealth_JsonValue($sJson, $sKey)
	If @error Then Return ""
	If StringLeft($sValue, 1) <> '"' Then Return $sValue
	Return _Stealth_JsonUnescape(StringTrimRight(StringTrimLeft($sValue, 1), 1))
EndFunc


Func _Stealth_JsonUnescape($sText)
	Local $sOut = $sText
	$sOut = StringReplace($sOut, "\\n", @LF)
	$sOut = StringReplace($sOut, "\\r", @CR)
	$sOut = StringReplace($sOut, "\\t", @TAB)
	$sOut = StringReplace($sOut, '\\"', '"')
	$sOut = StringReplace($sOut, "\\\\", "\\")
	Return $sOut
EndFunc
'''

FOOTER = '''

; =============================================================================================
; The routines. One wrapper per routine the Python layer implements, plus the names GwAu3 declares
; that this layer has not built yet -- those still make the call, so the worker's own
; `not_implemented` answer reaches the caller instead of autoit returning a silent empty value.
; =============================================================================================
'''


def _autoit_literal(value: object) -> str:
    """One constant's value as an AutoIt literal.

    The constants are read from ``py4gw/gwa3/constants.py`` -- this project's own transcription of
    GwAu3's constant files, verified against them name for name and value for value -- so the Python
    and AutoIt sides are the same table by construction rather than two transcriptions that agree until
    someone edits one. Integers keep their value (a decimal and a hex spelling are the same number);
    strings are quoted with AutoIt's own doubling rule for a quote inside a quoted string.
    """

    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    if isinstance(value, (list, tuple)):
        return _autoit_array(value)
    raise ValueError(f"no AutoIt literal for {value!r}")


#: How long one physical line of a generated array initialiser may get before it is broken.
#:
#: **Measured, and it is why this exists.** AutoIt's parser rejects a long physical line, not a long
#: statement: `Global Const $GC_AMX2_SKILL_DATA[3476][30] = [...104,280 numbers on one line...]` failed
#: with `Error in expression` and no line number, while the same value split across `_` continuations
#: compiled and ran (`tools/autoit/probe_large_array.au3`). The table this project carries has two
#: arrays that size, so without the wrapping the whole constants file is a syntax error and every
#: migrated script fails on it.
_MAX_LINE = 160


def _autoit_array(value: object, indent: str = "") -> str:
    """An array initialiser, broken across `_` continuation lines so AutoIt's parser accepts it."""

    if not isinstance(value, (list, tuple)):
        raise ValueError(f"not an array: {value!r}")

    items = list(value)
    if not items:
        return "[]"

    rendered = [_autoit_literal(item) for item in items]
    inline = "[" + ", ".join(rendered) + "]"
    if len(indent) + len(inline) <= _MAX_LINE and "\n" not in inline:
        return inline

    inner_indent = indent + "\t"
    lines = []
    for index, text in enumerate(rendered):
        if "\n" in text:
            text = text.replace("\n", "\n" + inner_indent)
        lines.append(f"{inner_indent}{text}")
    # Every element but the last carries the continuation marker, because the joined statement must
    # still be one statement.
    body = ", _\n".join(lines)
    return "[" + body + "]"


def _autoit_dimensions(value: object) -> str:
    """The ``[n]``/``[n][m]`` an AutoIt array declaration needs before its initialiser."""

    if isinstance(value, (list, tuple)):
        return f"[{max(1, len(value))}]" + (
            _autoit_dimensions(value[0]) if value and isinstance(value[0], (list, tuple)) else ""
        )
    return ""


def generate_constants() -> int:
    """Write the ``$GC_*`` table the AutoIt side needs, and answer how many names it holds.

    **GwAu3's scripts use these constants directly** -- ``Log_Message($GC_I_LOG_MSGTYPE_INFO, ...)``,
    ``Item_GetInventoryInfo($GC_I_INVENTORY_PTR)`` -- and the generated wrappers use them too, because
    GwAu3's own parameter defaults name them (``UAI_Fight(..., $GC_UAI_TARGET_MODE_CALL)``). Without
    this file a migrated script does not merely lose a value: Au3Check reports every one of them as an
    undeclared global, and AutoIt will not run a script that uses one.
    """

    from py4gw.gwa3 import constants as layer_constants

    names = sorted(layer_constants.__all__)
    parts = [
        "#include-once\n",
        "; =============================================================================================\n",
        "; Stealth_GwAu3_Constants.au3 -- GwAu3's `$GC_*` constant surface, for the AutoIt side.\n",
        ";\n",
        "; GENERATED. Do not edit by hand -- run `python tools/autoit/generate_stealth_udf.py`.\n",
        ";\n",
        f"; {len(names)} names, from `py4gw/gwa3/constants.py` -- the same table the Python layer uses,\n",
        "; itself generated from `external/GwAu3/API/Constants/*.au3` and verified against them in both\n",
        "; directions by `tests/test_gwa3_constants_offline.py`. GwAu3's spelling is kept, `$` included.\n",
        "; =============================================================================================\n\n",
    ]
    for name in names:
        value = getattr(layer_constants, name)
        parts.append(f"Global Const ${name}{_autoit_dimensions(value)} = {_autoit_literal(value)}\n")

    CONSTANTS_OUTPUT_PATH.write_text("".join(parts), encoding="utf-8")
    return len(names)


def standard_includes() -> list[str]:
    """The AutoIt standard UDL includes GwAu3's own aggregator pulls in.

    ``external/GwAu3/API/_GwAu3.au3`` includes 150 of them before its own code, and a GwAu3 script is
    written against that: ``$WS_EX_TOPMOST``, ``$CBS_DROPDOWN``, ``_GUICtrlRichEdit_Create`` and the
    rest come from there, not from GwAu3. A replacement include that omits them is not a drop-in -- the
    migrated script compiles to `undeclared global variable` on lines it never had to change.
    """

    aggregator = GWAU3_API / "_GwAu3.au3"
    if not aggregator.is_file():
        return []
    found = []
    for raw in aggregator.read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.match(r"^\s*#\s*include\s+<(?P<name>[^>]+)>\s*$", raw)
        if match:
            found.append(match.group("name"))
    return found


def main() -> int:
    sys.path.insert(0, str(REPO_ROOT))
    from py4gw.gwa3.bridge import gwau3_declared_names, layer_surface

    surface = layer_surface()
    signatures = parse_signatures()
    tiered = gwau3_declared_names()
    called = called_surface()

    # **The declared set is the union, and the union is the correction.** `gwau3_declared_names()` is
    # the 648 the route map tiers, built from GwAu3's `API/Modules/{Cmd,Data}`; `called` is every GwAu3
    # function the checkout actually calls. Only 322 of the 648 are called at all, and GwAu3's scripts
    # call **667** functions -- so declaring the tiered set alone left 345 called names with no wrapper,
    # and AutoIt refuses to compile a script that calls one. Both sets are declared now.
    declared = set(tiered) | set(called)

    implemented = sorted(surface)
    unbuilt = sorted(declared - set(implemented))
    # The hand-written names are taken out of **both** generated lists: a generated wrapper for one of
    # them would be a second `Func` of the same name, which AutoIt rejects as `already defined`.
    unbuilt_tiered = [n for n in unbuilt if n in tiered and n not in AUTOIT_HAND_WRITTEN]
    unbuilt_called = [n for n in unbuilt if n not in tiered and n not in AUTOIT_HAND_WRITTEN]
    implemented = [n for n in implemented if n not in AUTOIT_HAND_WRITTEN]

    parts = [HEADER]
    # The include block goes immediately after the header, because `#include-once` and the standard
    # UDLs are what make this file a drop-in for `_GwAu3.au3` rather than just a wrapper list.
    includes = standard_includes()
    parts.append("\n; --- the includes GwAu3's own aggregator pulls in, so a migrated script compiles ---\n")
    for name in includes:
        parts.append(f"#include <{name}>\n")
    parts.append('\n#include "Stealth_GwAu3_Constants.au3"\n')
    parts.append("\n")
    parts.append(AUTOIT_HAND_WRITTEN_GLOBALS)
    parts.append("\n")
    parts.append(FOOTER)
    parts.append("\n; --- transcribed from GwAu3: the routines whose work is AutoIt-side ---\n")
    parts.append("; `Log_*` renders into the script's own control, `Core_AutoStart` calls the script's own\n")
    parts.append("; `StartBot()`, and `Core_GetGuildWarsWindow` asks Windows for the client's window. GwAu3's\n")
    parts.append("; own bodies, line for line, including the BGR colours and the 30,000-character wipe.\n\n")
    for name in sorted(AUTOIT_HAND_WRITTEN):
        parts.append(AUTOIT_HAND_WRITTEN[name])
        parts.append("\n\n")

    parts.append("\n; --- implemented by py4gw/gwa3 ---\n\n")
    for name in implemented:
        parts.append(generate_wrapper(name, signatures.get(name, []), True))
        parts.append("\n\n")

    parts.append("\n; --- declared by GwAu3, not built by this layer yet ---\n")
    parts.append("; The call is made anyway: the worker answers `not_implemented` with a detail that\n")
    parts.append("; names the work, and AutoIt has no exceptions to carry it otherwise.\n\n")
    for name in unbuilt_tiered:
        parts.append(generate_wrapper(name, signatures.get(name, []), False))
        parts.append("\n\n")

    parts.append("\n; --- called by GwAu3's own scripts, outside the tiered surface ---\n")
    parts.append("; These are the framework routines a real script reaches for first -- `Core_Initialize`,\n")
    parts.append("; `Core_AutoStart`, `Log_*`, `UAI_*`, `Assembler_*`, `Scanner_*` -- and they are declared\n")
    parts.append("; here because AutoIt rejects the whole script when a called name has no `Func` at all\n")
    parts.append("; (`tools/autoit/READINGS.md`). Each answers `not_implemented`, or its own reason, from the\n")
    parts.append("; worker.\n\n")
    for name in unbuilt_called:
        parts.append(generate_wrapper(name, signatures.get(name, []), False))
        parts.append("\n\n")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("".join(parts), encoding="utf-8")
    constant_count = generate_constants()
    print(f"Wrote {OUTPUT_PATH.relative_to(REPO_ROOT)}")
    print(f"  standard UDL includes carried over from GwAu3's aggregator: {len(includes)}")
    print(f"Wrote {CONSTANTS_OUTPUT_PATH.relative_to(REPO_ROOT)} -- {constant_count} `$GC_*` names")
    print(f"  implemented wrappers: {len(implemented)}")
    print(f"  declared-but-unbuilt wrappers, inside the tiered surface: {len(unbuilt_tiered)}")
    print(f"  declared-but-unbuilt wrappers, called by GwAu3's scripts:  {len(unbuilt_called)}")
    print(f"  total declared: {len(implemented) + len(unbuilt)}")
    missing = sorted(name for name in called if name not in set(implemented) | set(unbuilt))
    if missing:
        print(f"  ** called and still undeclared ({len(missing)}): {missing[:10]}")
    without_signature = [n for n in implemented + unbuilt if n not in signatures]
    if without_signature:
        print(f"  wrappers with no signature found ({len(without_signature)}): {without_signature[:10]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
