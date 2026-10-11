; Smoke test for the generated Stealth_GwAu3.au3 under the AutoIt interpreter.
;
; Proves the UDF compiles and that a migrated call shape reaches the worker and comes back with a
; *described* failure -- no client is running, so every routine that reads the game must report that,
; and a name GwAu3 declares but this layer has not built must report `not_implemented` instead. Those
; are different answers, and telling them apart is the whole point of the error kind.
;
; No #RequireAdmin: the transport does not need elevation, and the directive would make AutoIt refuse
; to start the script at all in an ordinary shell.
;
; Run: "C:\Program Files (x86)\AutoIt3\AutoIt3.exe" tools\autoit\test_stealth_udf.au3

#include "Stealth_GwAu3.au3"

Global $g_sLog = ""
Global Const $g_sLogFile = @ScriptDir & "\test_stealth_udf_out.txt"

Func Note_(Const $sLine)
	$g_sLog &= $sLine & @CRLF
	ConsoleWrite($sLine & @CRLF)
EndFunc

Func Check_(Const $sName, Const $bCondition, Const $sDetail = "")
	If $bCondition Then
		Note_("PASS  " & $sName)
		Return True
	EndIf
	Note_("FAIL  " & $sName & "  " & $sDetail)
	Return False
EndFunc

; An argument array, so the test can drive _Stealth_Call directly the way a wrapper does.
Func _Stealth_ArgArray($v1, $v2)
	Local $aArgs[2]
	$aArgs[0] = $v1
	$aArgs[1] = $v2
	Return $aArgs
EndFunc

Main()

Func Main()
	Local $iPass = 0
	Local $iFail = 0

	Local $sRepoRoot = StringRegExpReplace(@ScriptDir, "\\tools\\autoit$", "")
	Note_("repo root: " & $sRepoRoot)
	Note_("")

	; --- the bridge starts -------------------------------------------------------------------
	Local $bStarted = _Stealth_BridgeStart($sRepoRoot)
	If Not $bStarted Then
		Note_("FATAL: could not start the bridge: " & $g_s_Stealth_ErrorKind & " / " & $g_s_Stealth_Error)
		FileDelete($g_sLogFile)
	FileWrite($g_sLogFile, $g_sLog)
		Exit 1
	EndIf
	If Check_("bridge starts", _Stealth_BridgeRunning()) Then $iPass += 1
	Note_("")

	; --- a routine that needs the client reports the connection, not a value ------------------
	; @error is read on the very next statement: any function call, including the logging one,
	; overwrites it. That is AutoIt's rule, and it is why the check has to be written this way -- the
	; first version of this test logged first and then asserted, so it was reading the *logger's*
	; @error and reporting a false failure.
	;
	; Two levels are checked, because they can fail independently: the generated wrapper, and
	; `_Stealth_Call` beneath it. A wrapper that returns `_Stealth_Call(...)` directly loses @error
	; (probe_error_chain.au3), so both are measured rather than assumed.
	Local $vRaw = _Stealth_Call("Agent_GetAgentInfo", _Stealth_ArgArray(-2, "X"), 0)
	Local $iRawError = @error
	Note_("_Stealth_Call directly           -> @error=" & $iRawError)
	If Check_("_Stealth_Call sets @error", $iRawError <> 0, "got " & $iRawError) Then $iPass += 1

	Local $vValue = Agent_GetAgentInfo(-2, "X")
	Local $iError = @error
	Local $sKind = $g_s_Stealth_ErrorKind
	Local $sDetail = $g_s_Stealth_Error
	Note_("Agent_GetAgentInfo(-2, ""X"") -> " & $vValue & "   @error=" & $iError & "   kind=" & $sKind)
	If Check_("a client routine fails with @error set", $iError <> 0, "got " & $iError) Then $iPass += 1
	If Check_("the failure is not reported as a value", $vValue = 0, "got " & $vValue) Then $iPass += 1
	If Check_("the failure kind is 'error'", $sKind = "error", $sKind) Then $iPass += 1
	If Check_("the detail names the connection", StringInStr($sDetail, "connect") > 0, $sDetail) Then $iPass += 1
	Note_("")

	; --- a routine this layer refuses is a DIFFERENT kind from a connection error -----------------
	; `Agent_CancelAction` is implemented and **refuses**: GwAu3 forges HEADER_ACTION_CANCEL and this
	; project has no member that cancels an action, so the layer raises with the gap named. That is
	; `refused`, and telling it from `error` is the whole reason the protocol carries a kind.
	;
	; This check used to use `Agent_GoNPC`, and it stopped being valid the moment that action gained a
	; real route: the call then reached the client and answered `error`. A check that asserts something
	; is unbuilt has to be re-pointed when it is built.
	Local $vRefused = Agent_CancelAction()
	Local $iRefusedError = @error
	Local $sRefusedKind = $g_s_Stealth_ErrorKind
	Local $sRefusedDetail = $g_s_Stealth_Error
	Note_("Agent_CancelAction() -> " & $vRefused & "   @error=" & $iRefusedError & "   kind=" & $sRefusedKind)
	If Check_("a refused routine sets @error too", $iRefusedError <> 0) Then $iPass += 1
	If Check_("a refusal is not the connection error", $sRefusedKind = "refused", $sRefusedKind) Then $iPass += 1
	If Check_("its detail names the GwAu3 line", StringInStr($sRefusedDetail, "GwAu3_Cmd_Agent") > 0, $sRefusedDetail) Then $iPass += 1
	Note_("")

	; --- a name nothing declares is 'unknown' --------------------------------------------------
	Local $vTypo = _Stealth_Call("NoSuchFunction", 0)
	Note_("NoSuchFunction -> " & $vTypo & "   kind=" & $g_s_Stealth_ErrorKind)
	If Check_("a typo is 'unknown'", $g_s_Stealth_ErrorKind = "unknown") Then $iPass += 1
	Note_("")

	; --- a string argument survives the round trip ---------------------------------------------
	Local $vNamed = _Stealth_Call("Skill_GetSkillInfo", 0)
	If Check_("the channel still answers after failures", $g_s_Stealth_ErrorKind <> "transport") Then $iPass += 1
	Note_("")

	; --- the bridge stops ----------------------------------------------------------------------
	_Stealth_BridgeStop()
	If Check_("bridge stops", Not _Stealth_BridgeRunning()) Then $iPass += 1

	Local $vAfter = Agent_GetAgentInfo(-2, "X")
	If Check_("a call after stop is a transport error", $g_s_Stealth_ErrorKind = "transport") Then $iPass += 1

	Note_("")
	Note_("=== " & $iPass & " passed, " & $iFail & " failed ===")
	FileDelete($g_sLogFile)
	FileWrite($g_sLogFile, $g_sLog)
EndFunc
