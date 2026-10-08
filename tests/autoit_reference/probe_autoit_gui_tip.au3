; Does AutoIt's own GUICtrlSetTip create the Windows tooltip control (tooltips_class32)?
;
; The port attaches that control, so this asks the interpreter what it attaches: the classes of
; every child of the GUI window, and of every window in the script's own process (hidden ones
; included), plus the tooltip's parent, style and exStyle.
;
; Run: "C:\Program Files (x86)\AutoIt3\AutoIt3.exe" probe_autoit_gui_tip.au3
; Writes probe_autoit_gui_tip_out.txt next to itself.

#include <GUIConstantsEx.au3>
#include <AutoItConstants.au3>
#include <SendMessage.au3>
#include <WinAPI.au3>
#include <WinAPIProc.au3>
#include <WindowsConstants.au3>

Local $hGUI = GUICreate("tip probe", 400, 200)
Local $idInput = GUICtrlCreateInput("", 10, 10, 200, 22)
Local $idButton = GUICtrlCreateButton("OK", 10, 40, 90, 25)
GUISetState(@SW_SHOW, $hGUI)

Local $sOut = ""
$sOut &= "pid=" & @AutoItPID & @CRLF
$sOut &= "gui=" & $hGUI & @CRLF
$sOut &= "input=" & GUICtrlGetHandle($idInput) & @CRLF
$sOut &= "button=" & GUICtrlGetHandle($idButton) & @CRLF

; Before any tip is set: what does the window hold?
Local $aChildren = _WinAPI_EnumChildWindows($hGUI)
$sOut &= "children before SetTip=" & (IsArray($aChildren) ? $aChildren[0][0] : 0) & @CRLF
If IsArray($aChildren) Then
    For $i = 1 To $aChildren[0][0]
        $sOut &= "  child " & $aChildren[$i][0] & " class=" & $aChildren[$i][1] & @CRLF
    Next
EndIf

Local $aProcess = _WinAPI_EnumProcessWindows(@AutoItPID, False)
Local $iTipBefore = 0
If IsArray($aProcess) Then
    For $i = 1 To $aProcess[0][0]
        If $aProcess[$i][1] = "tooltips_class32" Then $iTipBefore += 1
    Next
EndIf
$sOut &= "tooltips_class32 in process before SetTip=" & $iTipBefore & @CRLF

; The parameters are the reference's: title, icon, options.
GUICtrlSetTip($idInput, "an input tip", "Title here", $TIP_INFOICON)
GUICtrlSetTip($idButton, "a button tip", "", $TIP_NOICON, $TIP_BALLOON)
Sleep(200)

Local $aChildren2 = _WinAPI_EnumChildWindows($hGUI)
$sOut &= "children after SetTip=" & (IsArray($aChildren2) ? $aChildren2[0][0] : 0) & @CRLF
If IsArray($aChildren2) Then
    For $i = 1 To $aChildren2[0][0]
        $sOut &= "  child " & $aChildren2[$i][0] & " class=" & $aChildren2[$i][1] & @CRLF
    Next
EndIf

Local $aProcess2 = _WinAPI_EnumProcessWindows(@AutoItPID, False)
Local $iTips = 0
If IsArray($aProcess2) Then
    For $i = 1 To $aProcess2[0][0]
        Local $hWindow = $aProcess2[$i][0]
        Local $sClass = $aProcess2[$i][1]
        If $sClass <> "tooltips_class32" Then ContinueLoop
        $iTips += 1
        Local $iStyle = _WinAPI_GetWindowLong($hWindow, $GWL_STYLE)
        Local $iExStyle = _WinAPI_GetWindowLong($hWindow, $GWL_EXSTYLE)
        $sOut &= "tooltip " & $hWindow & ": parent=" & _WinAPI_GetParent($hWindow) _
                & " style=0x" & Hex($iStyle) & " exstyle=0x" & Hex($iExStyle) & @CRLF
    Next
EndIf
$sOut &= "tooltips_class32 in process after SetTip=" & $iTips & @CRLF

; What tool does it hold? AutoIt's own internals are not exposed, so this is the control's own
; report: a TTM_GETTOOLCOUNT on each tooltip window found.
If IsArray($aProcess2) Then
    For $i = 1 To $aProcess2[0][0]
        If $aProcess2[$i][1] <> "tooltips_class32" Then ContinueLoop
        Local $iCount = _SendMessage($aProcess2[$i][0], $WM_USER + 13, 0, 0) ; TTM_GETTOOLCOUNT
        $sOut &= "tooltip " & $aProcess2[$i][0] & " tool count=" & $iCount & @CRLF
    Next
EndIf

FileDelete(@ScriptDir & "\probe_autoit_gui_tip_out.txt")
FileWrite(@ScriptDir & "\probe_autoit_gui_tip_out.txt", $sOut)
GUIDelete($hGUI)
