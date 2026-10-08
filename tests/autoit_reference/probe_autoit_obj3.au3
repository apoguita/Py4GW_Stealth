; Follow-up to probe_autoit_obj2.au3, which created three object controls from *one* ObjCreate
; variable and found only one host window -- so the same object variable can host only one control,
; and the readings for the size defaults were lost. This probe gives every control its own object,
; reads the box of each host window in creation order, and measures the Obj kind's default resizing.

#include <GUIConstantsEx.au3>
#include <WindowsConstants.au3>
#include <WinAPISysWin.au3>

Const $sReport = @ScriptDir & "\probe_autoit_obj3_out.txt"
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

Func _Box($hParent, $hChild)
    Local $aPos = ControlGetPos($hParent, "", $hChild)
    If Not IsArray($aPos) Then Return "none"
    Return $aPos[0] & "," & $aPos[1] & "," & $aPos[2] & "x" & $aPos[3]
EndFunc

; The classes of the GUI's children, in z-order, with their boxes: what each control produced.
Func _List($sLabel, $hGUI)
    Local $aChildren = _WinAPI_EnumChildWindows($hGUI, False)
    If Not IsArray($aChildren) Then
        _Say($sLabel & ": no child windows")
        Return
    EndIf
    Local $sLine = $sLabel & ":"
    For $i = 1 To $aChildren[0][0]
        Local $hChild = $aChildren[$i][0]
        $sLine &= " [" & _ClassOf($hChild) & " " & _Box($hGUI, $hChild) & _
                " vis=" & _WinAPI_IsWindowVisible($hChild) & "]"
    Next
    _Say($sLine)
EndFunc

Func _NewIE()
    Return ObjCreate("Shell.Explorer.2")
EndFunc

Local $hGUI = GUICreate("obj3", 500, 400, 150, 150, BitOR($WS_OVERLAPPEDWINDOW, $WS_CLIPCHILDREN))
Local $idFirst = GUICtrlCreateObj(_NewIE(), 10, 10)
Local $idSized = GUICtrlCreateObj(_NewIE(), 10, 120, 60, 40)
Local $idAfterSized = GUICtrlCreateObj(_NewIE(), 200, 10)
Local $idLabel = GUICtrlCreateLabel("label", 200, 300)
Local $idAfterLabel = GUICtrlCreateObj(_NewIE(), 300, 300)
Local $idAfterObj = GUICtrlCreateObj(_NewIE(), 300, 350, 40, 30)
Local $idLast = GUICtrlCreateObj(_NewIE(), 400, 10)
GUISetState(@SW_SHOW, $hGUI)
Sleep(1500)
_Say("ids: first(no size)=" & $idFirst & " sized(60x40)=" & $idSized & " after sized(no size)=" & $idAfterSized & _
        " label=" & $idLabel & " after label(no size)=" & $idAfterLabel & " 40x30=" & $idAfterObj & " last(no size)=" & $idLast)
_List("after show", $hGUI)
_Say("label box = " & _Box($hGUI, GUICtrlGetHandle($idLabel)))

; The same object variable in a second control.
Local $oOnce = _NewIE()
Local $idOnceA = GUICtrlCreateObj($oOnce, 20, 350, 30, 20)
Local $idOnceB = GUICtrlCreateObj($oOnce, 60, 350, 50, 30)
Sleep(800)
_Say("same object variable twice: ids " & $idOnceA & " and " & $idOnceB)
_List("after the reuse", $hGUI)

; The Obj kind's default resizing: no GUICtrlSetResizing has been called anywhere above.
Local $aClient = WinGetClientSize($hGUI)
_Say("client before the resize = " & $aClient[0] & "x" & $aClient[1])
WinMove($hGUI, "", Default, Default, 700, 500)
Sleep(800)
_List("after the window grew to 700x500", $hGUI)
WinMove($hGUI, "", Default, Default, 420, 340)
Sleep(800)
_List("after the window shrank to 420x340", $hGUI)

GUICtrlDelete($idSized)
Sleep(400)
_Say("after deleting the 60x40 object: GUICtrlGetState(that id) = " & GUICtrlGetState($idSized))
_List("after the delete", $hGUI)

GUIDelete($hGUI)
Exit
