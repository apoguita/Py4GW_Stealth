; The last two size questions about an object control: does it take part in the "previously used
; width/height" that later controls inherit, and what does an explicit width=0/height=0 give?

#include <GUIConstantsEx.au3>
#include <WindowsConstants.au3>
#include <WinAPISysWin.au3>

Const $sReport = @ScriptDir & "\probe_autoit_obj4_out.txt"
FileDelete($sReport)

Func _Say($sLine)
    FileWrite($sReport, $sLine & @CRLF)
EndFunc

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
    Local $sLine = $sLabel & ":"
    For $i = 1 To $aChildren[0][0]
        Local $sClass = _WinAPI_GetClassName($aChildren[$i][0])
        $sLine &= " [" & $sClass & " " & _Box($hGUI, $aChildren[$i][0]) & "]"
    Next
    _Say($sLine)
EndFunc

Func _NewIE()
    Return ObjCreate("Shell.Explorer.2")
EndFunc

; 1. Does an object control leave a "previously used" size behind for the next control?
Local $hGUI = GUICreate("obj4", 500, 400, 150, 150, BitOR($WS_OVERLAPPEDWINDOW, $WS_CLIPCHILDREN))
GUICtrlCreateObj(_NewIE(), 10, 10)
Local $idInputAfterObj = GUICtrlCreateInput("", 10, 60)
Local $idObjZero = GUICtrlCreateObj(_NewIE(), 10, 120, 0, 0)
Local $idInputAfterZero = GUICtrlCreateInput("", 10, 200)
GUISetState(@SW_SHOW, $hGUI)
Sleep(1200)
_Say("input after an object with no size      : " & _Box($hGUI, GUICtrlGetHandle($idInputAfterObj)))
_Say("object with width=0 height=0            : " & _Box($hGUI, GUICtrlGetHandle($idObjZero)))
_Say("input after that object                 : " & _Box($hGUI, GUICtrlGetHandle($idInputAfterZero)))
_List("children", $hGUI)

; 2. An object control in its own window, with the "previously used" size set by an Input first.
Local $hGUI2 = GUICreate("obj4b", 500, 400, 700, 150, BitOR($WS_OVERLAPPEDWINDOW, $WS_CLIPCHILDREN))
Local $idInput = GUICtrlCreateInput("", 10, 10, 70, 33)
Local $idObjAfterInput = GUICtrlCreateObj(_NewIE(), 120, 10)
GUISetState(@SW_SHOW, $hGUI2)
Sleep(1000)
_Say("input 70x33                             : " & _Box($hGUI2, GUICtrlGetHandle($idInput)))
_Say("object after that input, no size        : " & _Box($hGUI2, GUICtrlGetHandle($idObjAfterInput)))
_List("children of the second window", $hGUI2)

GUIDelete($hGUI2)
GUIDelete($hGUI)
Exit
