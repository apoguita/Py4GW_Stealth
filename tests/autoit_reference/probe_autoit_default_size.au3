; What does "the previously used width/height" actually mean?
;
; Two earlier probes disagree on what a control gets when its size is omitted (probe_autoit_behavior
; read 28x17 for an Input created after other controls; probe_autoit_defaults read 200x20 for an Input
; created first in its own window). This puts the questions in one window, in a known order.
;
; Run: "C:\Program Files (x86)\AutoIt3\AutoIt3.exe" /ErrorStdOut probe_autoit_default_size.au3
; Writes probe_autoit_default_size_out.txt next to itself.

#include <GUIConstantsEx.au3>
#include <WindowsConstants.au3>

Const $sReport = @ScriptDir & "\probe_autoit_default_size_out.txt"
FileDelete($sReport)

Func _Say($sLine)
    FileWrite($sReport, $sLine & @CRLF)
EndFunc

Func _Size($hGUI, $idControl)
    Local $aPos = ControlGetPos($hGUI, "", GUICtrlGetHandle($idControl))
    If Not IsArray($aPos) Then Return "none"
    Return $aPos[2] & "x" & $aPos[3]
EndFunc

; Window 1: the order that matters, all in one window.
Local $hGUI = GUICreate("order", 600, 400, 100, 100)
Local $idInputFirst = GUICtrlCreateInput("", 10, 10)              ; 1. Input, no size
Local $idButton = GUICtrlCreateButton("OK", 10, 50)               ; 2. Button, no size (autofit?)
Local $idInputExplicit = GUICtrlCreateInput("", 10, 90, 50, 10)   ; 3. Input, explicit 50x10
Local $idInputAfter = GUICtrlCreateInput("", 10, 130)             ; 4. Input, no size
Local $idButton2 = GUICtrlCreateButton("OK", 10, 170)             ; 5. Button, no size again
Local $idInputAfter2 = GUICtrlCreateInput("", 10, 210)            ; 6. Input, no size again
GUISetState(@SW_SHOW, $hGUI)
Sleep(400)
_Say("1. Input, no size                : " & _Size($hGUI, $idInputFirst))
_Say("2. Button, no size               : " & _Size($hGUI, $idButton))
_Say("3. Input, explicit 50x10         : " & _Size($hGUI, $idInputExplicit))
_Say("4. Input, no size                : " & _Size($hGUI, $idInputAfter))
_Say("5. Button, no size               : " & _Size($hGUI, $idButton2))
_Say("6. Input, no size                : " & _Size($hGUI, $idInputAfter2))
GUIDelete($hGUI)
Sleep(300)

; Window 2: the same controls in the other order — an explicit size first.
Local $hGUI2 = GUICreate("order2", 600, 400, 100, 100)
Local $idEditExplicit = GUICtrlCreateEdit("", 10, 10, 120, 60)    ; 1. Edit, explicit 120x60
Local $idEditAfter = GUICtrlCreateEdit("", 10, 90)                ; 2. Edit, no size
Local $idListAfter = GUICtrlCreateList("", 10, 200)               ; 3. List, no size
GUISetState(@SW_SHOW, $hGUI2)
Sleep(400)
_Say("2a. Edit, explicit 120x60         : " & _Size($hGUI2, $idEditExplicit))
_Say("2b. Edit, no size                 : " & _Size($hGUI2, $idEditAfter))
_Say("2c. List, no size                 : " & _Size($hGUI2, $idListAfter))
GUIDelete($hGUI2)
Sleep(300)

; Window 3: a control created when the window is already shown.
Local $hGUI3 = GUICreate("shown", 600, 400, 100, 100)
GUISetState(@SW_SHOW, $hGUI3)
Sleep(400)
Local $idInputShown = GUICtrlCreateInput("", 10, 10)
Local $idInputShown2 = GUICtrlCreateInput("", 10, 60)
Sleep(300)
_Say("3a. Input, no size, window shown  : " & _Size($hGUI3, $idInputShown))
_Say("3b. Input, no size, again         : " & _Size($hGUI3, $idInputShown2))
GUIDelete($hGUI3)
Exit
