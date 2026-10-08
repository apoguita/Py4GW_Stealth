; Logs its UpDown's own position (UDM_GETPOS32, in-process) and what the input reads, every 200 ms,
; so a controller can click the arrows and see both numbers. This answers whether AutoIt lets the
; control change the value or applies the direction itself.
;
; Run: "C:\Program Files (x86)\AutoIt3\AutoIt3.exe" /ErrorStdOut probe_autoit_updown3.au3
; Writes probe_autoit_updown3_out.txt next to itself.

#include <GUIConstantsEx.au3>
#include <WindowsConstants.au3>
#include <SendMessage.au3>
#include <WinAPI.au3>

Opt("GUIOnEventMode", 1)

Const $sReport = @ScriptDir & "\probe_autoit_updown3_out.txt"
FileDelete($sReport)

Func _Say($sLine)
    FileWrite($sReport, $sLine & @CRLF)
EndFunc

Local $hGUI = GUICreate("updown trace", 500, 300, 150, 150)
Local $idInput = GUICtrlCreateInput("5", 10, 10, 120, 22)
Local $idUpdown = GUICtrlCreateUpdown($idInput)
GUISetState(@SW_SHOW, $hGUI)
WinActivate($hGUI)
WinSetOnTop($hGUI, "", 1)
Sleep(600)

Local $hUpdown = GUICtrlGetHandle($idUpdown)
Local $aUp = ControlGetPos($hGUI, "", $hUpdown)
_Say("updown box = " & $aUp[0] & "," & $aUp[1] & "," & $aUp[2] & "," & $aUp[3])
_Say("updown style = 0x" & Hex(_WinAPI_GetWindowLong($hUpdown, $GWL_STYLE)))
_Say("upper arrow client y = " & ($aUp[1] + 4) & ", lower arrow client y = " & ($aUp[1] + $aUp[3] - 4))
_Say("updown handle = " & $hUpdown & " input handle = " & GUICtrlGetHandle($idInput))

; Tick the position and the input text for about ten seconds. The controller clicks the arrows
; meanwhile; UDM_GETPOS32 is sent from inside this process, so nothing blocks.
Local $iTicks = 0
While $iTicks < 50
    Local $iPosition = _SendMessage($hUpdown, 0x0472, 0, 0)
    _Say("tick " & $iTicks & " position=" & $iPosition & " input=" & GUICtrlRead($idInput))
    Sleep(200)
    $iTicks += 1
WEnd
GUIDelete($hGUI)
