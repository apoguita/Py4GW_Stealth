; Does AutoIt's @error survive a function that returns another function's SetError result?
;
; This is the question the bridge's failure contract depends on, and the answer changed the UDF's
; design. A migrated script writes `If @error Then` -- so if @error cannot cross a function boundary,
; every failure the bridge reports is silent to the caller and only the global carries it.
;
; Run: "C:\Program Files (x86)\AutoIt3\AutoIt3.exe" tools\autoit\probe_error_macro.au3
;
; The readings this produced are in READINGS.md. Two rules came out of it, and both are surprising
; enough to be worth re-measuring on a future AutoIt:
;
;   1. `Return Inner_()` does NOT carry @error out. AutoIt resets the macro when a function returns a
;      call expression, so a wrapper written that way swallows every failure's @error.
;   2. `Return SetError(@error, 0, $v)` DOES carry it, because the macro is read as an argument before
;      the new function resets it.
;
; The generated wrappers are written the second way, and the level below them captures and re-sets
; too, because a helper that returned its result straight through would lose it for the same reason.

#include <AutoItConstants.au3>

Func Inner_()
	Return SetError(2, 3, 99)
EndFunc

; The shape a wrapper must NOT use.
Func LostByReturn_()
	Return Inner_()
EndFunc

; The shape the generated wrappers use.
Func PreservedByReturn_()
	Local $v = Inner_()
	Return SetError(@error, 0, $v)
EndFunc

; The shape `_Stealth_Call` uses: capture at each level, re-set on the way out.
Func Middle_()
	Local $v = Inner_()
	Local $iError = @error
	Return SetError($iError, 0, $v)
EndFunc

Func Wrapper_($a_iArg, $a_sText = "")
	Local $aArgs[1]
	$aArgs[0] = $a_iArg
	Local $v = Middle_()
	Return SetError(@error, 0, $v)
EndFunc

ConsoleWrite("direct call:                 @error=" & @error & @CRLF)
Local $v = Inner_()
ConsoleWrite("direct call, then local:     value=" & $v & " @error=" & @error & @CRLF)
$v = LostByReturn_()
ConsoleWrite("Return Inner_():             value=" & $v & " @error=" & @error & "   <- LOST" & @CRLF)
$v = PreservedByReturn_()
ConsoleWrite("Return SetError(@error,...): value=" & $v & " @error=" & @error & "   <- kept" & @CRLF)
$v = Wrapper_(1)
ConsoleWrite("three levels, re-set each:   value=" & $v & " @error=" & @error & "   <- kept" & @CRLF)

; And with an optional parameter passed positionally, as the wrappers do.
Func Wrapper2_($a_sName, $aArgs, $sFallback = 0)
	Local $v = Inner_()
	Local $iError = @error
	Return SetError($iError, 0, $sFallback)
EndFunc

Local $aArgs[2]
$aArgs[0] = 1
$aArgs[1] = 2
$v = Wrapper2_("X", $aArgs, 0)
ConsoleWrite("optional arg positional:     value=" & $v & " @error=" & @error & @CRLF)
