; =============================================================================================
; A GwAu3 script, running on Py4GW_Stealth.
;
; This file is written the way a GwAu3 author writes one: GwAu3's include, GwAu3's function names,
; GwAu3's `$GC_*` constants, GwAu3's log calls, GwAu3's own ordering -- `Core_Initialize` first,
; `Core_AutoStart` after it, then the reads. The only thing that is this project's is the file the
; include names.
;
; It is the example script's own sequence without its Koda GUI, because a GUI needs a hand on the
; Start button and this has to run unattended:
;
;   Exemple_AutoitGUI_Tester.au3          this file
;   -----------------------------         -------------------------------------------
;   Core_Initialize(ProcessExists(...))    Core_Initialize(ProcessExists("Gw.exe"), True)
;   Core_AutoStart()                       (skipped: it calls the *script's* StartBot)
;   Log_SetDebugMode(True)                 Log_SetDebugMode(True)
;   Cache_SkillBar()                       (not built yet: named, and @error is checked)
;   UAI_Fight(...)                         (not built yet: named, and @error is checked)
;   Agent_GetAgentInfo(-2, "X"/"Y")        the same two calls
;
; Run with AutoIt3.exe; it needs an elevated shell, because Core_Initialize connects, and connecting
; is the write path.
; =============================================================================================
#RequireAdmin
#include "Stealth_GwAu3.au3"

; GwAu3's log contract: with no callback registered and no RichEdit handle, a message is dropped by
; design. This registers the callback instead -- GwAu3's own documented path for a script frontend.
Log_SetCallback("Ported_OnLog")

; **The four names `Core_AutoStart` uses, declared by the script -- as every GwAu3 script declares
; them.** GwAu3's own `Core_AutoStart` reads `$g_bAutoStart` and `$g_s_MainCharName` and calls
; `StartBot()` and `_Exit()` (`GwAu3_Core.au3:595-648`), and those belong to the script, not to the
; API: `Exemple_AutoitGUI_Tester.au3:18-19` declares the two globals and its `:60` and `:160` define
; the two functions. A ported script that omits them does not compile, exactly as it would not under
; GwAu3 -- and that is why the UDF's `Core_AutoStart` is a transcription rather than a wrapper.
Global $g_bAutoStart = False
Global $g_s_MainCharName = ""

Func StartBot()
EndFunc

Func _Exit()
	Exit
EndFunc

Global $g_i_Pass = 0
Global $g_i_Fail = 0

Func Ported_OnLog($a_s_Message, $a_i_MsgType, $a_s_Author)
	Local $a_s_Type[5] = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
	Local $s_Type = ($a_i_MsgType >= 0 And $a_i_MsgType <= 4) ? $a_s_Type[$a_i_MsgType] : "?"
	ConsoleWrite("[" & $s_Type & "] [" & $a_s_Author & "] " & $a_s_Message & @CRLF)
EndFunc

Func Check($a_s_What, $a_b_Condition, $a_s_Detail = "")
	If $a_b_Condition Then
		$g_i_Pass += 1
		ConsoleWrite("PASS  " & $a_s_What & @CRLF)
	Else
		$g_i_Fail += 1
		ConsoleWrite("FAIL  " & $a_s_What & "  " & $a_s_Detail & @CRLF)
	EndIf
EndFunc

ConsoleWrite("=== a GwAu3 script on the Stealth layer ===" & @CRLF)

; ---------------------------------------------------------------------------------------------
; The bridge has to be started once, and that is the one line GwAu3 has no equivalent for: GwAu3's
; API *is* AutoIt code in the same process, and this layer's is a Python worker behind a pipe.
; ---------------------------------------------------------------------------------------------
If Not _Stealth_BridgeStart("C:\Users\Apo\Py4GW_Stealth") Then
	ConsoleWrite("FAIL  the bridge did not start: " & $g_s_Stealth_Error & @CRLF)
	Exit 1
EndIf
Check("the bridge started", True)

; ---------------------------------------------------------------------------------------------
; GwAu3's first line. `ProcessExists("gw.exe")` gives a pid, which is GwAu3's own numeric form.
; ---------------------------------------------------------------------------------------------
Local $i_Pid = ProcessExists("gw.exe")
Check("Guild Wars is running", $i_Pid <> 0, "ProcessExists answered " & $i_Pid)

Local $v_Init = Core_Initialize($i_Pid, True)
Check("Core_Initialize answered 1", $v_Init = 1, "answered " & $v_Init & " @error=" & @error)
If $v_Init = 0 Then
	ConsoleWrite("       detail: " & $g_s_Stealth_Error & @CRLF)
	_Stealth_BridgeStop()
	Exit 1
EndIf
Log_Info("Core_Initialize opened pid " & $i_Pid, "script")

; ---------------------------------------------------------------------------------------------
; Logging, exactly as a GwAu3 script uses it. DEBUG is gated off until SetDebugMode(True).
; ---------------------------------------------------------------------------------------------
Log_Debug("this line must NOT appear: debug mode is still off", "script")
Log_SetDebugMode(True)
Log_Debug("this line must appear: debug mode is on", "script")
Log_Warning("a warning renders through the same callback", "script")

; ---------------------------------------------------------------------------------------------
; The reads, phrased the way the example phrases them.
; ---------------------------------------------------------------------------------------------
Local $f_X = Agent_GetAgentInfo(-2, "X")
Local $f_Y = Agent_GetAgentInfo(-2, "Y")
Local $i_Level = Agent_GetAgentInfo(-2, "Level")
Local $i_MaxHP = Agent_GetAgentInfo(-2, "MaxHP")
Local $i_MyID = Agent_GetMyID()
Local $s_Name = Agent_GetAgentInfo(-2, "Name")
Local $i_Count = Agent_GetMaxAgents()

Check("Agent_GetAgentInfo(-2, ""X"") is a number", IsNumber($f_X), "answered " & $f_X)
Check("Agent_GetAgentInfo(-2, ""Y"") is a number", IsNumber($f_Y), "answered " & $f_Y)
Check("the level is 1..20", $i_Level >= 1 And $i_Level <= 20, "answered " & $i_Level)
Check("the maximum health is positive", $i_MaxHP > 0, "answered " & $i_MaxHP)
Check("Agent_GetMyID is the controlled character", $i_MyID > 0, "answered " & $i_MyID)
Check("the character name came back", $s_Name <> "", "answered '" & $s_Name & "'")
Check("Agent_GetMaxAgents answered a count", $i_Count >= 0, "answered " & $i_Count)

Log_Message("at " & Round($f_X) & "," & Round($f_Y) & " level " & $i_Level & " hp " & $i_MaxHP & " as '" & $s_Name & "'", $GC_I_LOG_MSGTYPE_INFO, "script")

; The seven families, one call each, by GwAu3's names.
Local $i_PartyLeader = Party_GetPartyContextInfo("IsPartyLeader")
Check("Party_GetPartyContextInfo(""IsPartyLeader"") is a boolean", IsBool($i_PartyLeader), "answered " & $i_PartyLeader)

Local $i_QuestDone = Quest_GetQuestInfo(999999, "HasQuest")
Check("a quest the log does not hold answers False", $i_QuestDone = False, "answered " & $i_QuestDone)

Local $i_SkillCost = Skill_GetSkillInfo(1, "EnergyCost")
Check("Skill_GetSkillInfo(1, ""EnergyCost"") answered", IsNumber($i_SkillCost), "answered " & $i_SkillCost)

Local $i_SkillType = Skill_GetSkillInfo(1, $GC_I_SKILL_TYPE)
Check("Skill_GetSkillInfo takes a $GC_* constant as its key", IsNumber($i_SkillType), "answered " & $i_SkillType)

; ---------------------------------------------------------------------------------------------
; A refused call: the reason must reach the caller, and it must not look like a value.
; ---------------------------------------------------------------------------------------------
Local $v_InGame = Core_IsIngame()
Check("Core_IsIngame is refused rather than guessed", @error <> 0, "@error=" & @error)
If @error Then
	Log_Error("Core_IsIngame: " & $g_s_Stealth_Error, "script")
EndIf

; ---------------------------------------------------------------------------------------------
; The two calls the example makes that are not built yet. They must still be *callable* -- AutoIt
; will not compile a script that names a function declared nowhere -- and each must set @error.
; ---------------------------------------------------------------------------------------------
Local $v_SkillBar = Cache_SkillBar()
Check("Cache_SkillBar is declared and reports itself unbuilt", @error <> 0, "@error=" & @error)

Local $v_Fight = UAI_Fight($f_X, $f_Y, 1320, 3500, 0)
Check("UAI_Fight is declared and reports itself unbuilt", @error <> 0, "@error=" & @error)
If $v_Fight = 0 And @error Then
	ConsoleWrite("       detail: " & $g_s_Stealth_Error & @CRLF)
EndIf

_Stealth_BridgeStop()
ConsoleWrite("=== " & $g_i_Pass & " passed, " & $g_i_Fail & " failed ===" & @CRLF)
Exit ($g_i_Fail = 0 ? 0 : 1)
