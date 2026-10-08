#NoTrayIcon
; Probe: in OnEvent mode, does an event fire while the script sits in Sleep()?
; The AutoIt OnEvent idiom is "While 1 / Sleep(100) / WEnd" (GUIRef_OnEventMode), so the
; answer decides whether a ported Sleep must pump GUI events. GUICtrlSendToDummy() is the
; event source, because it "notifies as normal" without needing a human to click.
; A 200x100 window is shown for about two seconds and then deleted.

#include <GUIConstantsEx.au3>

Global $g_iCalls = 0
Global $g_sEvent = ""
Global $g_hWin = 0

Func OnDummy()
    $g_iCalls += 1
    $g_sEvent &= "ctrlid=" & @GUI_CtrlId & ",win=" & (@GUI_WinHandle = $g_hWin) & ",ctrlhandle=" & @GUI_CtrlHandle & ";"
EndFunc

Opt("GUIOnEventMode", 1)
$g_hWin = GUICreate("probe", 200, 100)
GUISetOnEvent($GUI_EVENT_CLOSE, "")
Local $idDummy = GUICtrlCreateDummy()
GUICtrlSetOnEvent($idDummy, "OnDummy")
GUISetState(@SW_SHOW, $g_hWin)

; --- OnEvent mode: fire the event, then sleep without touching the GUI ---
GUICtrlSendToDummy($idDummy, 7)
Local $iBeforeSleep = $g_iCalls
Sleep(500)
Local $iAfterSleep = $g_iCalls

; --- message-loop mode: GUIGetMsg must report the dummy event ---
Opt("GUIOnEventMode", 0)
GUICtrlSendToDummy($idDummy, 8)
Local $iGetMsg = GUIGetMsg()
Local $iGetMsgAgain = GUIGetMsg()

FileWrite(@ScriptDir & "\probe_eventmode_out.txt", _
    "dummy-id=" & $idDummy & @CRLF & _
    "calls-before-sleep=" & $iBeforeSleep & @CRLF & _
    "calls-after-sleep=" & $iAfterSleep & @CRLF & _
    "events=" & $g_sEvent & @CRLF & _
    "msgloop-GetMsg=" & $iGetMsg & " (dummy-id match=" & ($iGetMsg = $idDummy) & ")" & @CRLF & _
    "msgloop-GetMsg-again=" & $iGetMsgAgain & @CRLF)

GUIDelete($g_hWin)
