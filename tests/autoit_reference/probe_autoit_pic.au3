; How big is a Pic control made from a file, with and without a width and height?
;
; The reference's Pic page says "To set the picture control to the same size as the file content set
; width and height to 0", which reads as the default being something else. It also says the control
; "supports BMP, JPG, GIF and TIF images", so both formats are used here.
;
; Run: "C:\Program Files (x86)\AutoIt3\AutoIt3.exe" /ErrorStdOut probe_autoit_pic.au3
; Writes probe_autoit_pic_out.txt next to itself.

#include <GUIConstantsEx.au3>
#include <WindowsConstants.au3>

Const $sReport = @ScriptDir & "\probe_autoit_pic_out.txt"
FileDelete($sReport)

Func _Say($sLine)
    FileWrite($sReport, $sLine & @CRLF)
EndFunc

Func _Box($hGUI, $idControl)
    Local $aPos = ControlGetPos($hGUI, "", GUICtrlGetHandle($idControl))
    If Not IsArray($aPos) Then Return "none"
    Return $aPos[0] & "," & $aPos[1] & "," & $aPos[2] & "," & $aPos[3]
EndFunc

; The caller gives the BMP's path and its true size: the probe cannot write a BMP reliably with
; DllStruct (an earlier version wrote one byte per field, and a Pic that cannot read its file reports
; the window's own box through ControlGetPos, which is how that was noticed).
Local $sBmp = ""
Local $iWidth = 0, $iHeight = 0
If $CmdLine[0] >= 1 Then $sBmp = $CmdLine[1]
If $CmdLine[0] >= 3 Then
    $iWidth = Int($CmdLine[2])
    $iHeight = Int($CmdLine[3])
EndIf
_Say("bmp argument = " & $sBmp & " (given as " & $iWidth & "x" & $iHeight & ")")

; A JPG from the AutoIt installation, if it has one.
Local $sJpg = ""
Local $aCandidates = FileFindFirstFile(@ProgramFilesDir & "\..\Program Files (x86)\AutoIt3\Examples\GUI\*.jpg")
If $aCandidates <> -1 Then
    Local $sName = FileFindNextFile($aCandidates)
    If Not @error Then $sJpg = @ProgramFilesDir & "\..\Program Files (x86)\AutoIt3\Examples\GUI\" & $sName
    FileClose($aCandidates)
EndIf

Local $hGUI = GUICreate("pic sizes", 500, 400, 150, 150)
Local $idBmpDefault = GUICtrlCreatePic($sBmp, 10, 10)
Local $idBmpZero = GUICtrlCreatePic($sBmp, 10, 100, 0, 0)
Local $idBmpSized = GUICtrlCreatePic($sBmp, 10, 200, 40, 30)
GUISetState(@SW_SHOW, $hGUI)
Sleep(500)

_Say("bmp file = " & $sBmp & " (" & $iWidth & "x" & $iHeight & ")")
_Say("bmp, no width/height       : " & _Box($hGUI, $idBmpDefault))
_Say("bmp, width=0 height=0      : " & _Box($hGUI, $idBmpZero))
_Say("bmp, width=40 height=30    : " & _Box($hGUI, $idBmpSized))
_Say("bmp reads                  : " & GUICtrlRead($idBmpDefault))

If $sJpg <> "" Then
    Local $idJpgDefault = GUICtrlCreatePic($sJpg, 200, 10)
    Local $idJpgZero = GUICtrlCreatePic($sJpg, 200, 100, 0, 0)
    Sleep(400)
    _Say("jpg file = " & $sJpg)
    _Say("jpg, no width/height       : " & _Box($hGUI, $idJpgDefault))
    _Say("jpg, width=0 height=0      : " & _Box($hGUI, $idJpgZero))
    _Say("jpg reads                  : " & GUICtrlRead($idJpgDefault))
Else
    _Say("no jpg found in the AutoIt examples")
EndIf

GUIDelete($hGUI)
FileDelete($sBmp)
Exit
