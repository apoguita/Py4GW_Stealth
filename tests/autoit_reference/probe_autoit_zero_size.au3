; What does an explicit width=0/height=0 give for ordinary controls? The object probe found that an
; object control with width=0 height=0 came out 0x0 and left 0x0 as the "previously used" size for
; the next control, which is not what the port assumed for a control created with no size.

#include <GUIConstantsEx.au3>
#include <WindowsConstants.au3>
#include <WinAPISysWin.au3>

Const $sReport = @ScriptDir & "\probe_autoit_zero_size_out.txt"
FileDelete($sReport)

Func _Say($sLine)
    FileWrite($sReport, $sLine & @CRLF)
EndFunc

Func _Box($hParent, $hChild)
    Local $aPos = ControlGetPos($hParent, "", $hChild)
    If Not IsArray($aPos) Then Return "none"
    Return $aPos[0] & "," & $aPos[1] & "," & $aPos[2] & "x" & $aPos[3]
EndFunc

Local $hGUI = GUICreate("zero sizes", 600, 500, 150, 150, BitOR($WS_OVERLAPPEDWINDOW, $WS_CLIPCHILDREN))
GUISetState(@SW_SHOW, $hGUI)
Sleep(400)

Local $idInput = GUICtrlCreateInput("input", 10, 10, 0, 0)
Local $idEdit = GUICtrlCreateEdit("edit", 200, 10, 0, 0)
Local $idList = GUICtrlCreateList("list", 400, 10, 0, 0)
Local $idLabel = GUICtrlCreateLabel("label", 10, 200, 0, 0)
Local $idButton = GUICtrlCreateButton("button", 10, 300, 0, 0)
Local $idGroup = GUICtrlCreateGroup("group", 200, 200, 0, 0)
Local $idAfterZero = GUICtrlCreateInput("after zeros", 10, 400)
Sleep(500)

_Say("input  width=0 height=0 : " & _Box($hGUI, GUICtrlGetHandle($idInput)))
_Say("edit   width=0 height=0 : " & _Box($hGUI, GUICtrlGetHandle($idEdit)))
_Say("list   width=0 height=0 : " & _Box($hGUI, GUICtrlGetHandle($idList)))
_Say("label  width=0 height=0 : " & _Box($hGUI, GUICtrlGetHandle($idLabel)))
_Say("button width=0 height=0 : " & _Box($hGUI, GUICtrlGetHandle($idButton)))
_Say("group  width=0 height=0 : " & _Box($hGUI, GUICtrlGetHandle($idGroup)))
_Say("input with no size after : " & _Box($hGUI, GUICtrlGetHandle($idAfterZero)))

GUIDelete($hGUI)
Exit
