; Follow-up to probe_autoit_obj.au3: the object control has no AutoIt handle at all
; (GUICtrlGetHandle returned 0), so its geometry can only be read from the window AutoIt actually
; created. That window is a child of the GUI -- "Shell Embedding", style 0x50010000 -- and this probe
; follows its box through GUICtrlSetPos, $GUI_HIDE/$GUI_SHOW, a resize with $GUI_DOCKAUTO, and
; GUICtrlDelete, and reads the width/height defaults for an object control created with none.
;
; All reads are in-process; nothing outside the script touches the windows.

#include <GUIConstantsEx.au3>
#include <WindowsConstants.au3>
#include <WinAPISysWin.au3>

Const $sReport = @ScriptDir & "\probe_autoit_obj2_out.txt"
FileDelete($sReport)

Func _Say($sLine)
    FileWrite($sReport, $sLine & @CRLF)
EndFunc

Func _Hex($iValue)
    Return "0x" & Hex($iValue, 8)
EndFunc

Func _ClassOf($hWnd)
    If Not IsHWnd($hWnd) Then Return "no window"
    Local $sClass = _WinAPI_GetClassName($hWnd)
    If $sClass = "" Then Return "?"
    Return $sClass
EndFunc

; ControlGetPos reports a child window's box relative to its parent's client area, which is the same
; frame of reference the port stores for a control.
Func _Box($hParent, $hChild)
    Local $aPos = ControlGetPos($hParent, "", $hChild)
    If Not IsArray($aPos) Then Return "none"
    Return $aPos[0] & "," & $aPos[1] & "," & $aPos[2] & "x" & $aPos[3]
EndFunc

Func _List($sLabel, $hGUI)
    Local $aChildren = _WinAPI_EnumChildWindows($hGUI, False)
    If Not IsArray($aChildren) Then
        _Say($sLabel & ": no child windows")
        Return
    EndIf
    _Say($sLabel & ": " & $aChildren[0][0] & " children")
    For $i = 1 To $aChildren[0][0]
        Local $hChild = $aChildren[$i][0]
        _Say("   " & _ClassOf($hChild) & " box=" & _Box($hGUI, $hChild) & _
                " visible=" & _WinAPI_IsWindowVisible($hChild) & _
                " style=" & _Hex(_WinAPI_GetWindowLong($hChild, $GWL_STYLE)) & _
                " exstyle=" & _Hex(_WinAPI_GetWindowLong($hChild, $GWL_EXSTYLE)) & _
                " parentclass=" & _ClassOf(_WinAPI_GetParent($hChild)))
    Next
EndFunc

Local $oIE = ObjCreate("Shell.Explorer.2")

Local $hGUI = GUICreate("obj2", 500, 400, 150, 150, BitOR($WS_OVERLAPPEDWINDOW, $WS_CLIPCHILDREN))
Local $idObj = GUICtrlCreateObj($oIE, 10, 10, 200, 150)
_Say("GUICtrlCreateObj(ie, 10, 10, 200, 150) -> " & $idObj)
_List("before GUISetState", $hGUI)
GUISetState(@SW_SHOW, $hGUI)
Sleep(1200)
_List("after GUISetState(SW_SHOW)", $hGUI)
_Say("GUICtrlGetHandle(id) = " & GUICtrlGetHandle($idObj) & "; GUICtrlRead = '" & GUICtrlRead($idObj) & _
        "'; GUICtrlGetState = " & GUICtrlGetState($idObj))

GUICtrlSetPos($idObj, 50, 60, 120, 80)
Sleep(400)
_List("after GUICtrlSetPos(50, 60, 120, 80)", $hGUI)

GUICtrlSetState($idObj, $GUI_HIDE)
Sleep(400)
_List("after GUICtrlSetState(GUI_HIDE)", $hGUI)
_Say("GUICtrlGetState while hidden = " & GUICtrlGetState($idObj))
GUICtrlSetState($idObj, $GUI_SHOW)
Sleep(400)
_List("after GUICtrlSetState(GUI_SHOW)", $hGUI)
_Say("GUICtrlGetState after showing = " & GUICtrlGetState($idObj))

GUICtrlSetResizing($idObj, $GUI_DOCKAUTO)
WinMove($hGUI, "", Default, Default, 700, 500)
Sleep(700)
_List("after the window grew to 700x500 with GUI_DOCKAUTO", $hGUI)

GUICtrlSetResizing($idObj, $GUI_DOCKSIZE)
WinMove($hGUI, "", Default, Default, 560, 420)
Sleep(600)
_List("after the window shrank to 560x420 with GUI_DOCKSIZE", $hGUI)

GUICtrlDelete($idObj)
Sleep(500)
_List("after GUICtrlDelete", $hGUI)

; --- the size defaults ------------------------------------------------------------------------

Local $hGUI2 = GUICreate("obj2 defaults", 500, 400, 200, 200, BitOR($WS_OVERLAPPEDWINDOW, $WS_CLIPCHILDREN))
Local $oIE2 = ObjCreate("Shell.Explorer.2")
Local $idFirst = GUICtrlCreateObj($oIE2, 10, 10)
Local $idSized = GUICtrlCreateObj($oIE2, 10, 220, 60, 40)
Local $idAfterSized = GUICtrlCreateObj($oIE2, 250, 10)
Local $idLabel = GUICtrlCreateLabel("label", 250, 300)
Local $oIE3 = ObjCreate("Shell.Explorer.2")
Local $idAfterLabel = GUICtrlCreateObj($oIE3, 300, 300)
GUISetState(@SW_SHOW, $hGUI2)
Sleep(1200)
_List("second window, four objects", $hGUI2)
_Say("label box = " & _Box($hGUI2, GUICtrlGetHandle($idLabel)))
GUIDelete($hGUI2)
GUIDelete($hGUI)
Exit
