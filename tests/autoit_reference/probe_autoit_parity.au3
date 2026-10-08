#NoTrayIcon
; Parity probe for Py4GW_Stealth's AutoIt-compatible GUI layer.
; Answers semantics the help file leaves open for functions the port currently refuses or
; approximates: GUICtrlSetData on a ListView, ListViewItem check state, GUICtrlRead on an
; UpDown, whether a hidden control keeps its geometry, and how long an idle GUIGetMsg takes.
; Windows stay hidden. The report is written line by line.

#include <GUIConstantsEx.au3>
#include <ListViewConstants.au3>
#include <GuiListView.au3>
#include <UpDownConstants.au3>
#include <EditConstants.au3>
#include <ButtonConstants.au3>

Global $g_hFile = FileOpen(@ScriptDir & "\probe_parity_out.txt", 2)

Func Note($text)
    FileWrite($g_hFile, $text & @CRLF)
EndFunc

Opt("GUIOnEventMode", 0)
Local $hWin = GUICreate("probe", 500, 400)

; --- GUICtrlSetData on a ListView control ---
Local $lv = GUICtrlCreateListView("ColA|ColB", 10, 10, 300, 120, -1, BitOR($LVS_EX_FULLROWSELECT, $LVS_EX_CHECKBOXES))
Local $item = GUICtrlCreateListViewItem("a|b", $lv)
Local $aCol0 = _GUICtrlListView_GetColumn($lv, 0)
Local $aCol1 = _GUICtrlListView_GetColumn($lv, 1)
Note("[lv] before: col0=" & $aCol0[5] & " col1=" & $aCol1[5] & " read=" & GUICtrlRead($lv))
Local $ret = GUICtrlSetData($lv, "X|Y")
$aCol0 = _GUICtrlListView_GetColumn($lv, 0)
$aCol1 = _GUICtrlListView_GetColumn($lv, 1)
Note("[lv] GUICtrlSetData ret=" & $ret & " col0=" & $aCol0[5] & " col1=" & $aCol1[5])
Local $aCol2 = _GUICtrlListView_GetColumn($lv, 2)
Note("[lv] after: item count=" & _GUICtrlListView_GetItemCount($lv) & " col2 text=[" & $aCol2[5] & "] count=" & _GUICtrlListView_GetColumnCount($lv))

; --- ListViewItem check state ---
Note("[lvitem] state before=" & GUICtrlGetState($item))
GUICtrlSetState($item, $GUI_CHECKED)
Note("[lvitem] read=" & GUICtrlRead($item) & " advanced=" & GUICtrlRead($item, 1) & " getstate=" & GUICtrlGetState($item))
GUICtrlSetState($item, $GUI_UNCHECKED)
Note("[lvitem] after uncheck read=" & GUICtrlRead($item) & " advanced=" & GUICtrlRead($item, 1))

; --- UpDown control ---
Local $input = GUICtrlCreateInput("5", 10, 150, 100, 20)
Local $updown = GUICtrlCreateUpdown($input, BitOR($UDS_SETBUDDYINT, $UDS_ALIGNRIGHT))
Note("[updown] read=" & GUICtrlRead($updown) & " input=" & GUICtrlRead($input) & " getstate=" & GUICtrlGetState($updown))
GUICtrlSetData($updown, 12)
Note("[updown] after SetData(12) read=" & GUICtrlRead($updown) & " input=" & GUICtrlRead($input))
GUICtrlSetLimit($updown, 30, 3)
Note("[updown] after SetLimit read=" & GUICtrlRead($updown) & " input=" & GUICtrlRead($input))

; --- a hidden control's geometry ---
Local $btn = GUICtrlCreateButton("OK", 10, 200, 90, 25)
Local $hBtn = GUICtrlGetHandle($btn)
Local $aPos = WinGetPos($hBtn)
Note("[hide] shown pos=" & $aPos[0] & "," & $aPos[1] & " size=" & $aPos[2] & "x" & $aPos[3])
GUICtrlSetState($btn, $GUI_HIDE)
GUICtrlSetPos($btn, 40, 240)
GUICtrlSetState($btn, $GUI_SHOW)
$aPos = WinGetPos($hBtn)
Note("[hide] after hide/move/show pos=" & $aPos[0] & "," & $aPos[1] & " size=" & $aPos[2] & "x" & $aPos[3])

; --- how long does an idle GUIGetMsg take? ---
Local $tStart = TimerInit()
For $i = 1 To 2000
    GUIGetMsg()
Next
Local $fPerCall = TimerDiff($tStart) / 2000
Note("[timing] GUIGetMsg idle average ms=" & StringFormat("%.4f", $fPerCall))

; --- GUICtrlSetData on a Dummy with no value, and GUICtrlSendMsg on a button ---
Local $dummy = GUICtrlCreateDummy()
Note("[dummy] read=" & GUICtrlRead($dummy))
Local $msgResult = GUICtrlSendMsg($btn, 0x00F5, 0, 0) ; BM_CLICK
Note("[sendmsg] BM_CLICK returned=" & $msgResult)

FileClose($g_hFile)
