; What does GUICtrlCreateObj actually create, and what does AutoIt let a script do with the result?
;
; The reference's page states only the parameter list, "failure: 0", "they must at least support an
; IDispatch interface", that "Document Objects will only be visible if $WS_CLIPCHILDREN has been used
; in GUICreate()", and that GUICtrlRead/GUICtrlSet have no effect on the control (it is driven through
; the object variable). Everything else a port has to reproduce -- the window the control lives in,
; what GUICtrlGetHandle returns, whether GUICtrlSetPos/GUISetState/GUICtrlDelete reach it, and the
; width/height default -- is measured here.
;
; Every read is in-process, and nothing outside the script touches the window: an earlier probe that
; clicked a title bar hung the interpreter, and a cross-process SendMessage did the same.

#include <GUIConstantsEx.au3>
#include <WindowsConstants.au3>
#include <WinAPISysWin.au3>

Const $sReport = @ScriptDir & "\probe_autoit_obj_out.txt"
FileDelete($sReport)

Func _Say($sLine)
    FileWrite($sReport, $sLine & @CRLF)
EndFunc

Func _Hex($iValue)
    Return "0x" & Hex($iValue, 8)
EndFunc

Func _Rect($hWnd)
    If Not IsHWnd($hWnd) Then Return "no window"
    Local $aRect = _WinAPI_GetWindowRect($hWnd)
    If Not IsArray($aRect) Then Return "no rect"
    Return $aRect[0] & "," & $aRect[1] & "," & ($aRect[2] - $aRect[0]) & "x" & ($aRect[3] - $aRect[1])
EndFunc

Func _ClassOf($hWnd)
    If Not IsHWnd($hWnd) Then Return "no window"
    Local $sClass = _WinAPI_GetClassName($hWnd)
    If $sClass = "" Then Return "?"
    Return $sClass
EndFunc

Func _Info($sLabel, $hWnd)
    _Say($sLabel & ": class=" & _ClassOf($hWnd) & " parentclass=" & _ClassOf(_WinAPI_GetParent($hWnd)) & _
            " rect=" & _Rect($hWnd) & " visible=" & _WinAPI_IsWindowVisible($hWnd) & _
            " style=" & _Hex(_WinAPI_GetWindowLong($hWnd, $GWL_STYLE)) & _
            " exstyle=" & _Hex(_WinAPI_GetWindowLong($hWnd, $GWL_EXSTYLE)))
EndFunc

Func _Children($sLabel, $hWnd)
    Local $aChildren = _WinAPI_EnumChildWindows($hWnd, False)
    If Not IsArray($aChildren) Then
        _Say($sLabel & ": no child windows")
        Return
    EndIf
    _Say($sLabel & ": " & $aChildren[0][0] & " child windows")
    For $i = 1 To $aChildren[0][0]
        _Say("   " & _ClassOf($aChildren[$i][0]) & " rect=" & _Rect($aChildren[$i][0]) & _
                " visible=" & _WinAPI_IsWindowVisible($aChildren[$i][0]) & _
                " style=" & _Hex(_WinAPI_GetWindowLong($aChildren[$i][0], $GWL_STYLE)))
    Next
EndFunc

; --- ObjCreate itself -------------------------------------------------------------------------

Local $oIE = ObjCreate("Shell.Explorer.2")
_Say("ObjCreate(Shell.Explorer.2): isobj=" & IsObj($oIE) & " name='" & ObjName($oIE) & "' error=" & @error)

Local $oBad = ObjCreate("No.Such.Class.Here")
_Say("ObjCreate(No.Such.Class.Here): isobj=" & IsObj($oBad) & " value=" & $oBad & " error=" & @error)

Local $oDict = ObjCreate("Scripting.Dictionary")
_Say("ObjCreate(Scripting.Dictionary): isobj=" & IsObj($oDict) & " name='" & ObjName($oDict) & "'")

; --- the control ------------------------------------------------------------------------------

Local $hGUI = GUICreate("obj", 500, 400, 150, 150, BitOR($WS_OVERLAPPEDWINDOW, $WS_CLIPCHILDREN))
Local $idObj = GUICtrlCreateObj($oIE, 10, 10, 200, 150)
_Say("GUICtrlCreateObj(ie, 10, 10, 200, 150) -> " & $idObj & " (error=" & @error & ")")

Local $hObj = GUICtrlGetHandle($idObj)
_Say("GUICtrlGetHandle -> " & $hObj)
_Info("  before show", $hObj)
_Children("  children before show", $hObj)

GUISetState(@SW_SHOW, $hGUI)
Sleep(1200)

_Info("  after show", $hObj)
_Children("  children after show", $hObj)
_Children("  children of the GUI", $hGUI)
_Say("  GUICtrlRead        = '" & GUICtrlRead($idObj) & "'")
_Say("  GUICtrlGetState    = " & GUICtrlGetState($idObj))
_Say("  IsHWnd(handle)     = " & IsHWnd($hObj) & "  IsHWnd(controlID) = " & IsHWnd($idObj))

; GUICtrlSetPos: does the object's window follow the control?
GUICtrlSetPos($idObj, 50, 60, 120, 80)
Sleep(400)
_Info("  after GUICtrlSetPos(50, 60, 120, 80)", $hObj)
_Children("  children after SetPos", $hObj)

; GUICtrlSetState: hide and show.
GUICtrlSetState($idObj, $GUI_HIDE)
Sleep(300)
_Info("  after GUICtrlSetState(GUI_HIDE)", $hObj)
GUICtrlSetState($idObj, $GUI_SHOW)
Sleep(300)
_Info("  after GUICtrlSetState(GUI_SHOW)", $hObj)
_Say("  GUICtrlGetState after showing = " & GUICtrlGetState($idObj))

; GUICtrlSetData and GUICtrlSetStyle: what do they return on this control?
Local $iSetData = GUICtrlSetData($idObj, "text")
_Say("  GUICtrlSetData(obj, 'text') -> " & $iSetData & " (error=" & @error & ")")
Local $iSetStyle = GUICtrlSetStyle($idObj, $WS_BORDER)
_Say("  GUICtrlSetStyle(obj, WS_BORDER) -> " & $iSetStyle & " (error=" & @error & ")")

; Resizing: the reference's own example puts $GUI_DOCKAUTO on the object.
GUICtrlSetResizing($idObj, $GUI_DOCKAUTO)
WinMove($hGUI, "", Default, Default, 700, 500)
Sleep(500)
_Info("  after the window grew to 700x500", $hObj)
_Children("  children after the resize", $hObj)

; --- the size defaults ------------------------------------------------------------------------

Local $hGUI2 = GUICreate("obj defaults", 500, 400, 200, 200, BitOR($WS_OVERLAPPEDWINDOW, $WS_CLIPCHILDREN))
Local $oIE2 = ObjCreate("Shell.Explorer.2")
Local $idFirst = GUICtrlCreateObj($oIE2, 10, 10)
Local $idSized = GUICtrlCreateObj($oIE2, 10, 200, 60, 40)
Local $idAfterSized = GUICtrlCreateObj($oIE2, 200, 10)
GUISetState(@SW_SHOW, $hGUI2)
Sleep(800)
_Say("second window: first object with no size -> " & _Rect(GUICtrlGetHandle($idFirst)))
_Say("second window: object 60x40               -> " & _Rect(GUICtrlGetHandle($idSized)))
_Say("second window: object with no size after  -> " & _Rect(GUICtrlGetHandle($idAfterSized)))
GUICtrlDelete($idFirst)
Sleep(300)
_Say("after GUICtrlDelete(first): handle still a window = " & IsHWnd(GUICtrlGetHandle($idFirst)) & _
        " IsWindow(handle) = " & _WinAPI_IsWindow(GUICtrlGetHandle($idFirst)))

; --- an object that is not a control ----------------------------------------------------------

Local $hGUI3 = GUICreate("obj dict", 400, 300, 250, 250)
Local $idDict = GUICtrlCreateObj($oDict, 10, 10, 100, 100)
_Say("GUICtrlCreateObj(Scripting.Dictionary) -> " & $idDict & " (error=" & @error & ")")
If $idDict <> 0 Then
    _Info("  dictionary control", GUICtrlGetHandle($idDict))
EndIf
GUISetState(@SW_SHOW, $hGUI3)
Sleep(600)
If $idDict <> 0 Then
    _Info("  dictionary control after show", GUICtrlGetHandle($idDict))
EndIf

GUIDelete($hGUI3)
GUIDelete($hGUI2)
GUIDelete($hGUI)
Exit
