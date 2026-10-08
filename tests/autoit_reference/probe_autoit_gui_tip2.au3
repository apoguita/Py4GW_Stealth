; How does AutoIt's GUICtrlSetTip use its tooltip controls? Follow-up to probe_autoit_gui_tip.au3.
;
; probe_autoit_gui_tip.au3 established: before any GUICtrlSetTip there is no tooltips_class32 in
; the process; after two tips on two controls there are two tooltips_class32 windows, each parented
; to the GUI and each holding exactly one tool.
;
; This probe asks what follows from that: whether two controls' titles are independent, what a
; second SetTip on the same control does, whether $TIP_BALLOON after a plain tip changes the
; control's style, what a tool's flags are for the plain/$TIP_CENTER/$TIP_FORCEVISIBLE options,
; and whether deleting a control removes its tooltip.
;
; Run: "C:\Program Files (x86)\AutoIt3\AutoIt3.exe" probe_autoit_gui_tip2.au3
; Writes probe_autoit_gui_tip2_out.txt next to itself, a line at a time as it goes.

#include <GUIConstantsEx.au3>
#include <AutoItConstants.au3>
#include <SendMessage.au3>
#include <WinAPI.au3>
#include <WinAPIProc.au3>
#include <WindowsConstants.au3>

; TOOLINFOW, spelled out because the include files here carry no $tagTOOLINFO.
Const $tagTOOLINFOW = "struct; uint cbSize; uint uFlags; hwnd hwnd; ulong_ptr uId; int rect[4]; ptr hinst; ptr lpszText; lparam lParam; ptr lpReserved; endstruct"
Const $TTM_ENUMTOOLSW = 0x400 + 58
Const $TTM_GETTITLE = 0x400 + 35

Const $sReport = @ScriptDir & "\probe_autoit_gui_tip2_out.txt"
FileDelete($sReport)

Func _Say($sLine)
    FileWrite($sReport, $sLine & @CRLF)
EndFunc

; Every tooltips_class32 window in this process, as "handle|style|exstyle|toolcount".
Func _Tips()
    Local $aProcess = _WinAPI_EnumProcessWindows(@AutoItPID, False)
    Local $sResult = ""
    If Not IsArray($aProcess) Then Return ""
    For $i = 1 To $aProcess[0][0]
        If $aProcess[$i][1] <> "tooltips_class32" Then ContinueLoop
        Local $hTip = $aProcess[$i][0]
        Local $iStyle = _WinAPI_GetWindowLong($hTip, $GWL_STYLE)
        Local $iExStyle = _WinAPI_GetWindowLong($hTip, $GWL_EXSTYLE)
        Local $iCount = _SendMessage($hTip, 0x400 + 13, 0, 0) ; TTM_GETTOOLCOUNT
        Local $iParent = _WinAPI_GetParent($hTip)
        $sResult &= $hTip & "|style=0x" & Hex($iStyle) & "|ex=0x" & Hex($iExStyle) _
                & "|tools=" & $iCount & "|parent=" & $iParent _
                & "|title=" & _TipTitle($hTip) & "|tool=" & _FirstTool($hTip) & @CRLF
    Next
    Return $sResult
EndFunc

; The tooltip's title and icon, read from the control (TTGETTITLE: dwSize, uTitleBitmap, cch,
; pszTitle).
Func _TipTitle($hTip)
    Local $tTitle = DllStructCreate("dword dwSize; uint uTitleBitmap; uint cch; ptr pszTitle")
    Local $tBuffer = DllStructCreate("wchar title[256]")
    DllStructSetData($tTitle, "dwSize", DllStructGetSize($tTitle))
    DllStructSetData($tTitle, "cch", 256)
    DllStructSetData($tTitle, "pszTitle", DllStructGetPtr($tBuffer))
    _SendMessage($hTip, $TTM_GETTITLE, 0, DllStructGetPtr($tTitle))
    Return "'" & DllStructGetData($tBuffer, "title") & "' icon=" & DllStructGetData($tTitle, "uTitleBitmap")
EndFunc

; The one tool a tooltip holds, as "uId flags text" (TTM_ENUMTOOLSW, index 0).
Func _FirstTool($hTip)
    Local $tInfo = DllStructCreate($tagTOOLINFOW)
    DllStructSetData($tInfo, "cbSize", DllStructGetSize($tInfo))
    _SendMessage($hTip, $TTM_ENUMTOOLSW, 0, DllStructGetPtr($tInfo))
    Local $pText = DllStructGetData($tInfo, "lpszText")
    Local $sText = ""
    If $pText Then
        Local $tText = DllStructCreate("wchar text[256]", $pText)
        $sText = DllStructGetData($tText, "text")
    EndIf
    Return "uId=" & DllStructGetData($tInfo, "uId") & " flags=0x" & _
            Hex(DllStructGetData($tInfo, "uFlags")) & " text='" & $sText & "'"
EndFunc

Local $hGUI = GUICreate("tip probe 2", 400, 240)
Local $idOne = GUICtrlCreateInput("", 10, 10, 200, 22)
Local $idTwo = GUICtrlCreateButton("OK", 10, 40, 90, 25)
Local $idThree = GUICtrlCreateInput("", 10, 70, 200, 22)
Local $idFour = GUICtrlCreateButton("Two", 10, 100, 90, 25)
GUISetState(@SW_SHOW, $hGUI)

_Say("gui=" & $hGUI)
_Say("input=" & GUICtrlGetHandle($idOne) & " button=" & GUICtrlGetHandle($idTwo))
_Say("")
_Say("[A] no tip at all:")
_Say(_Tips())

_Say("")
_Say("[B] a titled tip on the input, a plain tip on the button:")
GUICtrlSetTip($idOne, "first text", "First title", $TIP_INFOICON)
GUICtrlSetTip($idTwo, "second text")
Sleep(200)
_Say(_Tips())

_Say("")
_Say("[C] the button's tip titled, without touching the input's:")
GUICtrlSetTip($idTwo, "second text", "Second title", $TIP_ERRORICON)
Sleep(200)
_Say(_Tips())

_Say("")
_Say("[D] the input's tip set again, same parameters:")
GUICtrlSetTip($idOne, "first text", "First title", $TIP_INFOICON)
Sleep(200)
_Say(_Tips())

_Say("")
_Say("[E] the input's tip changed to a new text, title and icon:")
GUICtrlSetTip($idOne, "changed text", "Changed", $TIP_WARNINGICON)
Sleep(200)
_Say(_Tips())

_Say("")
_Say("[F] $TIP_BALLOON on the input, whose tip was plain:")
GUICtrlSetTip($idOne, "changed text", "Changed", $TIP_WARNINGICON, $TIP_BALLOON)
Sleep(200)
_Say(_Tips())

_Say("")
_Say("[G] $TIP_BALLOON on the third input, which had no tip:")
GUICtrlSetTip($idThree, "balloon text", "Balloon", $TIP_NOICON, $TIP_BALLOON)
Sleep(200)
_Say(_Tips())

_Say("")
_Say("[H] $TIP_CENTER on the fourth control:")
GUICtrlSetTip($idFour, "centred", "Centre", $TIP_NOICON, $TIP_CENTER)
Sleep(200)
_Say(_Tips())

_Say("")
_Say("[I] $TIP_FORCEVISIBLE on the fourth control:")
GUICtrlSetTip($idFour, "forced", "Force", $TIP_NOICON, $TIP_FORCEVISIBLE)
Sleep(200)
_Say(_Tips())

_Say("")
_Say("[J] after deleting the third control (the balloon one):")
GUICtrlDelete($idThree)
Sleep(400)
_Say(_Tips())

_Say("")
_Say("[K] after deleting the window:")
GUIDelete($hGUI)
Sleep(400)
_Say(_Tips())
