#NoTrayIcon
; Parity probe 2: the control types the port still refuses.
; Reads what AutoIt returns for Date, MonthCal, Icon and Avi controls, what GUICtrlSetData
; does to them, whether they report handles, and their default sizes. Windows stay hidden.

#include <GUIConstantsEx.au3>
#include <DateTimeConstants.au3>
#include <StaticConstants.au3>
#include <AVIConstants.au3>

Global $g_hFile = FileOpen(@ScriptDir & "\probe_parity2_out.txt", 2)

Func Note($text)
    FileWrite($g_hFile, $text & @CRLF)
EndFunc

Func Size_Of($id)
    Local $h = GUICtrlGetHandle($id)
    If $h = 0 Then Return "no-handle"
    Local $a = WinGetClientSize($h)
    Return $a[0] & "x" & $a[1]
EndFunc

Opt("GUIOnEventMode", 0)
Local $hWin = GUICreate("probe2", 500, 400)

; --- Date control ---
Local $date = GUICtrlCreateDate("2026/01/02", 10, 10, 160, 22)
Note("[date] read=[" & GUICtrlRead($date) & "] handle=" & GUICtrlGetHandle($date) & " size=" & Size_Of($date))
Local $ret = GUICtrlSetData($date, "2027/03/04")
Note("[date] SetData ret=" & $ret & " read=[" & GUICtrlRead($date) & "]")
Note("[date] getstate=" & GUICtrlGetState($date))
GUICtrlSetState($date, $GUI_DISABLE)
Note("[date] after disable getstate=" & GUICtrlGetState($date))
GUICtrlSetState($date, $GUI_ENABLE)
Note("[date] getstyle ret=" & GUICtrlSetStyle($date, $DTS_SHORTDATEFORMAT) & " read=[" & GUICtrlRead($date) & "]")

; --- MonthCal control ---
Local $mc = GUICtrlCreateMonthCal("2026/01/02", 10, 50, 220, 160)
Note("[mc] read=[" & GUICtrlRead($mc) & "] handle=" & GUICtrlGetHandle($mc) & " size=" & Size_Of($mc))
Local $retMc = GUICtrlSetData($mc, "2027/03/04")
Note("[mc] SetData ret=" & $retMc & " read=[" & GUICtrlRead($mc) & "]")
Note("[mc] getstate=" & GUICtrlGetState($mc))

; --- Icon control ---
Local $icon = GUICtrlCreateIcon(@SystemDir & "\shell32.dll", -1, 10, 220)
Note("[icon] read=[" & GUICtrlRead($icon) & "] handle=" & GUICtrlGetHandle($icon) & " size=" & Size_Of($icon))
Note("[icon] getstate=" & GUICtrlGetState($icon))

; --- Avi control ---
Local $avi = GUICtrlCreateAvi(@ScriptDir & "\..\Examples\GUI\sampleAVI.avi", 0, 10, 260, 120, 120)
Note("[avi] read=[" & GUICtrlRead($avi) & "] handle=" & GUICtrlGetHandle($avi) & " size=" & Size_Of($avi))
Note("[avi] getstate=" & GUICtrlGetState($avi))
Note("[avi] start ret=" & GUICtrlSetState($avi, $GUI_AVISTART))
Note("[avi] stop ret=" & GUICtrlSetState($avi, $GUI_AVISTOP))
Note("[avi] close ret=" & GUICtrlSetState($avi, $GUI_AVICLOSE))

; --- default sizes when width/height are omitted ---
GUISwitch($hWin)
Local $dateSmall = GUICtrlCreateDate("2026/01/02", 300, 10)
Note("[defaults] Date=" & Size_Of($dateSmall))
Local $mcSmall = GUICtrlCreateMonthCal("2026/01/02", 300, 60)
Note("[defaults] MonthCal=" & Size_Of($mcSmall))
Local $iconSmall = GUICtrlCreateIcon(@SystemDir & "\shell32.dll", -1, 300, 260)
Note("[defaults] Icon=" & Size_Of($iconSmall))

FileClose($g_hFile)
