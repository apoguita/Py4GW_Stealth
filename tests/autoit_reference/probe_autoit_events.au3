; Does real input reach a native control, and does it fire that control's OnEvent function?
;
; The port's tests have never driven a native control with real input: posted messages emit no
; notifications (measured earlier with a plain Win32 host). This probe clicks the controls with the
; pointer moved to their screen positions, one window on top so the click lands on it, and records
; what its OnEvent functions see.
;
; Run: "C:\Program Files (x86)\AutoIt3\AutoIt3.exe" /ErrorStdOut probe_autoit_events.au3
; Writes probe_autoit_events_out.txt next to itself.

#include <GUIConstantsEx.au3>
#include <WindowsConstants.au3>
#include <DateTimeConstants.au3>
#include <WinAPI.au3>

Opt("GUIOnEventMode", 1)

Const $sReport = @ScriptDir & "\probe_autoit_events_out.txt"
FileDelete($sReport)

Func _Say($sLine)
    FileWrite($sReport, $sLine & @CRLF)
EndFunc

Global $sLog = ""

Func _Log($sWhat)
    $sLog &= $sWhat & ";"
EndFunc

; A client point of the window as a screen point, for MouseClick with MouseCoordMode 1.
Func _ScreenX($hWnd, $iX)
    Local $tPoint = DllStructCreate("long x; long y")
    DllStructSetData($tPoint, "x", $iX)
    DllStructSetData($tPoint, "y", 0)
    _WinAPI_ClientToScreen($hWnd, $tPoint)
    Return DllStructGetData($tPoint, "x")
EndFunc

Func _ScreenY($hWnd, $iY)
    Local $tPoint = DllStructCreate("long x; long y")
    DllStructSetData($tPoint, "x", 0)
    DllStructSetData($tPoint, "y", $iY)
    _WinAPI_ClientToScreen($hWnd, $tPoint)
    Return DllStructGetData($tPoint, "y")
EndFunc

; Move the pointer to a client point, then press and release there, then let events settle.
Func _Click($hGUI, $iClientX, $iClientY)
    Opt("MouseCoordMode", 1)
    Local $iScreenX = _ScreenX($hGUI, $iClientX)
    Local $iScreenY = _ScreenY($hGUI, $iClientY)
    MouseMove($iScreenX, $iScreenY, 0)
    Sleep(250)
    MouseDown("left")
    Sleep(80)
    MouseUp("left")
    Sleep(700)
    Return $iScreenX & "," & $iScreenY
EndFunc

Local $hGUI = GUICreate("events", 500, 400, 100, 100)
Local $idInput = GUICtrlCreateInput("5", 10, 10, 120, 22)
Local $idUpdown = GUICtrlCreateUpdown($idInput)
Local $idDate = GUICtrlCreateDate("2026/01/02", 10, 60, 160, 22)
Local $idMonth = GUICtrlCreateMonthCal("2026/01/02", 10, 100, 220, 160)

GUICtrlSetOnEvent($idUpdown, "_OnUpdown")
GUICtrlSetOnEvent($idDate, "_OnDate")
GUICtrlSetOnEvent($idMonth, "_OnMonth")

GUISetState(@SW_SHOW, $hGUI)
WinActivate($hGUI)
WinSetOnTop($hGUI, "", 1)
Sleep(600)
_Say("active window = " & WinGetTitle("[ACTIVE]"))
Local $aWindow = WinGetPos($hGUI)
_Say("window box = " & $aWindow[0] & "," & $aWindow[1] & "," & $aWindow[2] & "," & $aWindow[3])
_Say("handles: input=" & GUICtrlGetHandle($idInput) & " updown=" & GUICtrlGetHandle($idUpdown) & " date=" & GUICtrlGetHandle($idDate) & " monthcal=" & GUICtrlGetHandle($idMonth))

Local $aUp = ControlGetPos($hGUI, "", GUICtrlGetHandle($idUpdown))
Local $aInput = ControlGetPos($hGUI, "", GUICtrlGetHandle($idInput))
_Say("input box  = " & $aInput[0] & "," & $aInput[1] & "," & $aInput[2] & "," & $aInput[3])
_Say("updown box = " & $aUp[0] & "," & $aUp[1] & "," & $aUp[2] & "," & $aUp[3])
_Say("input reads before = " & GUICtrlRead($idInput))

$sLog = ""
Local $iUpX = $aUp[0] + Int($aUp[2] / 2)
Local $iUpY = $aUp[1] + Int($aUp[3] / 4)
Local $sWhere = _Click($hGUI, $iUpX, $iUpY)
_Say("click up arrow, client " & $iUpX & "," & $iUpY & " screen " & $sWhere & " -> log: " & $sLog)
_Say("input reads after  = " & GUICtrlRead($idInput))
_Say("control under that point = " & WinGetTitle("[ACTIVE]"))

$sLog = ""
_Click($hGUI, $iUpX, $aUp[1] + Int($aUp[3] * 3 / 4))
_Say("click down arrow -> log: " & $sLog)
_Say("input reads after  = " & GUICtrlRead($idInput))

$sLog = ""
Local $aDate = ControlGetPos($hGUI, "", GUICtrlGetHandle($idDate))
_Click($hGUI, $aDate[0] + $aDate[2] - 8, $aDate[1] + Int($aDate[3] / 2))
_Say("click date dropdown -> log: " & $sLog)
_Say("date reads = " & GUICtrlRead($idDate))

$sLog = ""
Local $aMonth = ControlGetPos($hGUI, "", GUICtrlGetHandle($idMonth))
_Click($hGUI, $aMonth[0] + 60, $aMonth[1] + 80)
_Say("click monthcal day -> log: " & $sLog)
_Say("monthcal reads = " & GUICtrlRead($idMonth))

; A plain Button, as the control the port's own tests do drive: does a real click fire it?
Local $idButton = GUICtrlCreateButton("OK", 300, 10, 90, 25)
GUICtrlSetOnEvent($idButton, "_OnButton")
Sleep(300)
$sLog = ""
_Click($hGUI, 330, 22)
_Say("click button -> log: " & $sLog)

Func _OnUpdown()
    _Log("updown id=" & @GUI_CtrlId & " handle=" & @GUI_CtrlHandle & " win=" & @GUI_WinHandle)
EndFunc

Func _OnDate()
    _Log("date id=" & @GUI_CtrlId & " handle=" & @GUI_CtrlHandle)
EndFunc

Func _OnMonth()
    _Log("monthcal id=" & @GUI_CtrlId & " handle=" & @GUI_CtrlHandle)
EndFunc

Func _OnButton()
    _Log("button id=" & @GUI_CtrlId & " handle=" & @GUI_CtrlHandle)
EndFunc
