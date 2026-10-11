; A minimal AutoIt probe: can AutoIt drive the GwAu3 bridge worker over stdio?
;
; This is a probe, not the deliverable. It establishes the transport before the real UDF is written:
; that AutoIt can start the worker, write a request line, and read a whole reply line back. The
; deliverable is tools/autoit/Stealth_GwAu3.au3, which this probe's findings shape.
;
; **No #RequireAdmin.** The probe asks only for names that need no client, so it runs in an ordinary
; shell. The first version carried #RequireAdmin and produced no output at all unelevated -- AutoIt
; refuses to run such a script rather than erroring loudly, which is worth knowing about the language.
; The worker's *connection* needs elevation; the transport does not.
;
; Run:  "C:\Program Files (x86)\AutoIt3\AutoIt3.exe" tools\autoit\probe_bridge_stdio.au3
; It writes its readings to stdout, and to tools\autoit\probe_bridge_stdio_out.txt.

#include <AutoItConstants.au3>

Global $g_sOut = ""
Global Const $g_sOutFile = @ScriptDir & "\probe_bridge_stdio_out.txt"

Func Log_(Const $sLine)
	$g_sOut &= $sLine & @CRLF
	ConsoleWrite($sLine & @CRLF)
EndFunc

Func RunBridge_($sBridgeScript, $sRepoRoot)
	; The worker is Python. The first version launched @AutoItExe on the .py, which ran AutoIt against a
	; script it cannot parse -- the probe sat waiting for a reply that was never coming.
	Local $sPython = "python"
	Local $sCmd = '"' & $sPython & '" -u "' & $sBridgeScript & '"'
	Log_("launching: " & $sCmd)
	Local $iPid = Run($sCmd, $sRepoRoot, @SW_HIDE, $STDIN_CHILD + $STDOUT_CHILD + $STDERR_CHILD)
	Log_("pid: " & $iPid)
	Return $iPid
EndFunc

Func MustReadLine_($iPid, $iTimeoutMs = 15000)
	Local $sBuffer = ""
	Local $iWaited = 0
	While $iWaited < $iTimeoutMs
		Local $sChunk = StdoutRead($iPid)
		If @error Then
			Return SetError(1, 0, "")
		EndIf
		If $sChunk <> "" Then
			$sBuffer &= $sChunk
			If StringInStr($sBuffer, @CRLF) Or StringInStr($sBuffer, @LF) Then
				Local $aLines = StringRegExp($sBuffer, "(.*?)(?:\r\n|\n|\r)", 3)
				If UBound($aLines) > 0 Then Return $aLines[0]
			EndIf
		EndIf
		Sleep(25)
		$iWaited += 25
	WEnd
	Return SetError(2, 0, "")
EndFunc

; --- the probe ---------------------------------------------------------------------------------

Log_("=== probe: AutoIt -> GwAu3 bridge worker over stdio ===")
Log_("@AutoItVersion: " & @AutoItVersion)
Log_("@AutoItX64: " & @AutoItX64)

Local $sRepoRoot = StringRegExpReplace(@ScriptDir, "\\tools\\autoit$", "")
Log_("repo root: " & $sRepoRoot)

Local $sScript = @ScriptDir & "\run_bridge_worker.py"
If Not FileExists($sScript) Then
	Log_("FATAL: worker launcher not found at " & $sScript)
	FileWrite($g_sOutFile, $g_sOut)
	Exit 1
EndIf

Local $iPid = RunBridge_($sScript, $sRepoRoot)
If $iPid = 0 Then
	Log_("FATAL: Run() returned 0")
	FileWrite($g_sOutFile, $g_sOut)
	Exit 1
EndIf

Sleep(1500)

; The worker writes its banner to stderr; drain it so it cannot be mistaken for a reply line.
Local $sErr = StderrRead($iPid)
If $sErr <> "" Then Log_("stderr: " & StringStripWS($sErr, 3))

; One request: a name nothing declares, so the reply needs no client and must be a described failure.
Local $sRequest = '{"call": "NoSuchFunction", "args": [], "id": 1}'
Log_("writing: " & $sRequest)
StdinWrite($iPid, $sRequest & @LF)
If @error Then Log_("StdinWrite error: " & @error)

Local $sReply = MustReadLine_($iPid)
If @error Then
	Log_("FATAL: no reply line (error " & @error & ")")
Else
	Log_("reply: " & $sReply)
	If StringInStr($sReply, '"ok":false') Then
		Log_("PASS: the worker refused a name nothing declares, in one line")
	Else
		Log_("FAIL: unexpected reply shape")
	EndIf
EndIf

; A second request, to prove the channel survives more than one call.
Local $sRequest2 = '{"call": "Agent_GetMyID", "args": [], "id": 2}'
StdinWrite($iPid, $sRequest2 & @LF)
Local $sReply2 = MustReadLine_($iPid)
If @error Then
	Log_("FAIL: no reply to the second request (error " & @error & ")")
Else
	Log_("reply 2: " & $sReply2)
	If StringInStr($sReply2, '"id":2') Then
		Log_("PASS: the channel carried a second request")
	Else
		Log_("FAIL: second reply did not echo its id")
	EndIf
EndIf

ProcessClose($iPid)
FileWrite($g_sOutFile, $g_sOut)
Log_("=== probe complete; readings in " & $g_sOutFile & " ===")
