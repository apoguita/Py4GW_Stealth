#NoTrayIcon
; Behaviour probe for Py4GW_Stealth's AutoIt-compatible GUI layer.
; Answers the questions the AutoIt help pages leave unstated (default control sizes,
; GUICtrlRead / GUICtrlGetState values, the nature of item control IDs). Every window
; here stays hidden: the script never shows one. The report is written line by line so
; a failure still leaves the results gathered before it.

#include <GUIConstantsEx.au3>
#include <ButtonConstants.au3>
#include <EditConstants.au3>
#include <ComboConstants.au3>
#include <ListBoxConstants.au3>
#include <ListViewConstants.au3>
#include <TreeViewConstants.au3>
#include <TabConstants.au3>
#include <StaticConstants.au3>
#include <ProgressConstants.au3>
#include <SliderConstants.au3>
#include <MenuConstants.au3>
#include <DateTimeConstants.au3>

Global $g_hFile = FileOpen(@ScriptDir & "\probe_behavior_out.txt", 2)

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

; --- default window size when width/height are omitted ---
Local $hWin = GUICreate("probe")
Local $aClient = WinGetClientSize($hWin)
Note("[window] GUICreate-no-width-height client=" & $aClient[0] & "x" & $aClient[1])
Local $hWin2 = GUICreate("probe2", 400, 300)
Local $aClient2 = WinGetClientSize($hWin2)
Note("[window] GUICreate(400,300) client=" & $aClient2[0] & "x" & $aClient2[1])

; --- default control sizes when width/height are omitted ---
Local $idButton = GUICtrlCreateButton("OK", 10, 10)
Note("[defaults] Button=" & Size_Of($idButton))
Local $idLabel = GUICtrlCreateLabel("Hello", 10, 40)
Note("[defaults] Label=" & Size_Of($idLabel))
Local $idInput = GUICtrlCreateInput("abc", 10, 70)
Note("[defaults] Input=" & Size_Of($idInput))
Local $idCheck = GUICtrlCreateCheckbox("Check", 10, 100)
Note("[defaults] Checkbox=" & Size_Of($idCheck))
Local $idRadio = GUICtrlCreateRadio("Radio", 10, 130)
Note("[defaults] Radio=" & Size_Of($idRadio))
Local $idCombo = GUICtrlCreateCombo("item1", 10, 160)
Note("[defaults] Combo=" & Size_Of($idCombo))
Local $idList = GUICtrlCreateList("", 10, 190)
Note("[defaults] List=" & Size_Of($idList))
Local $idEdit = GUICtrlCreateEdit("text", 10, 220)
Note("[defaults] Edit=" & Size_Of($idEdit))
Local $idProgress = GUICtrlCreateProgress(10, 250)
Note("[defaults] Progress=" & Size_Of($idProgress))
Local $idSlider = GUICtrlCreateSlider(10, 280)
Note("[defaults] Slider=" & Size_Of($idSlider))
Local $idTab = GUICtrlCreateTab(10, 310)
Note("[defaults] Tab=" & Size_Of($idTab))
Local $idTabItem1 = GUICtrlCreateTabItem("one")
Local $idTabItem2 = GUICtrlCreateTabItem("two")
GUICtrlCreateTabItem("")
Local $idTree = GUICtrlCreateTreeView(10, 360)
Note("[defaults] TreeView=" & Size_Of($idTree))
Local $idTreeItem = GUICtrlCreateTreeViewItem("root", $idTree)
Local $idListview = GUICtrlCreateListView("ColA|ColB", 10, 400)
Note("[defaults] ListView=" & Size_Of($idListview))
Local $idListViewItem = GUICtrlCreateListViewItem("a|b", $idListview)
Local $idDate = GUICtrlCreateDate("2026/01/02", 10, 440)
Note("[defaults] Date=" & Size_Of($idDate))
Local $idGraphic = GUICtrlCreateGraphic(10, 470)
Note("[defaults] Graphic=" & Size_Of($idGraphic))
Local $idDummy = GUICtrlCreateDummy()
Local $idUpdown = GUICtrlCreateUpdown($idInput)
GUISwitch($hWin)

; --- are control IDs the control's window handle? ---
Note("[ids] Button id=" & $idButton & " handle=" & GUICtrlGetHandle($idButton) & " equal=" & ($idButton = GUICtrlGetHandle($idButton)))
Note("[ids] Label handle=" & GUICtrlGetHandle($idLabel) & " equal=" & ($idLabel = GUICtrlGetHandle($idLabel)))
Note("[ids] Dummy id=" & $idDummy & " handle=" & GUICtrlGetHandle($idDummy))
Note("[ids] Graphic id=" & $idGraphic & " handle=" & GUICtrlGetHandle($idGraphic))
Note("[ids] TabItem id=" & $idTabItem1 & " handle=" & GUICtrlGetHandle($idTabItem1))
Note("[ids] TreeItem id=" & $idTreeItem & " handle=" & GUICtrlGetHandle($idTreeItem))
Note("[ids] ListViewItem id=" & $idListViewItem & " handle=" & GUICtrlGetHandle($idListViewItem))
Note("[ids] Updown id=" & $idUpdown & " handle=" & GUICtrlGetHandle($idUpdown))

; --- menus ---
Local $idMenu = GUICtrlCreateMenu("File")
Local $idMenuItem = GUICtrlCreateMenuItem("Open", $idMenu)
Local $idMenuSep = GUICtrlCreateMenuItem("", $idMenu)
Note("[ids] Menu id=" & $idMenu & " handle=" & GUICtrlGetHandle($idMenu))
Note("[ids] MenuItem id=" & $idMenuItem & " handle=" & GUICtrlGetHandle($idMenuItem) & " separator=" & $idMenuSep)

; --- GUICtrlRead values ---
Note("[read] Button=" & GUICtrlRead($idButton))
Note("[read] Label=" & GUICtrlRead($idLabel))
Note("[read] Input=" & GUICtrlRead($idInput))
Note("[read] Edit=" & GUICtrlRead($idEdit))
Note("[read] Checkbox-unchecked=" & GUICtrlRead($idCheck))
GUICtrlSetState($idCheck, $GUI_CHECKED)
Note("[read] Checkbox-checked=" & GUICtrlRead($idCheck))
Note("[read] Checkbox-advanced=" & GUICtrlRead($idCheck, $GUI_READ_EXTENDED))
Note("[read] Radio=" & GUICtrlRead($idRadio))
GUICtrlSetData($idProgress, 50)
Note("[read] Progress=" & GUICtrlRead($idProgress))
GUICtrlSetData($idSlider, 30)
Note("[read] Slider=" & GUICtrlRead($idSlider))
GUICtrlSetData($idList, "a|b|c", "b")
Note("[read] List=" & GUICtrlRead($idList))
GUICtrlSetData($idCombo, "x|y|z", "z")
Note("[read] Combo=" & GUICtrlRead($idCombo))
Note("[read] Tab=" & GUICtrlRead($idTab) & " advanced=" & GUICtrlRead($idTab, $GUI_READ_EXTENDED) & " tabitem1=" & $idTabItem1)
Note("[read] TabItem=" & GUICtrlRead($idTabItem1))
Note("[read] TreeView=" & GUICtrlRead($idTree) & " treeitem=" & $idTreeItem)
Note("[read] TreeViewItem=" & GUICtrlRead($idTreeItem) & " advanced=" & GUICtrlRead($idTreeItem, $GUI_READ_EXTENDED))
Note("[read] ListView=" & GUICtrlRead($idListview) & " lvitem=" & $idListViewItem)
Note("[read] ListViewItem=" & GUICtrlRead($idListViewItem) & " advanced=" & GUICtrlRead($idListViewItem, $GUI_READ_EXTENDED))
Note("[read] Menu=" & GUICtrlRead($idMenu) & " advanced=" & GUICtrlRead($idMenu, $GUI_READ_EXTENDED))
Note("[read] MenuItem=" & GUICtrlRead($idMenuItem) & " advanced=" & GUICtrlRead($idMenuItem, $GUI_READ_EXTENDED))
Note("[read] Dummy-before=" & GUICtrlRead($idDummy))
GUICtrlSendToDummy($idDummy, 42)
Note("[read] Dummy-after-send=" & GUICtrlRead($idDummy))
Note("[read] Date=" & GUICtrlRead($idDate))

; --- GUICtrlGetState ---
Note("[state] Button=" & GUICtrlGetState($idButton))
GUICtrlSetState($idButton, $GUI_DISABLE)
Note("[state] Button-disabled=" & GUICtrlGetState($idButton))
GUICtrlSetState($idButton, $GUI_ENABLE)
GUICtrlSetState($idButton, $GUI_HIDE)
Note("[state] Button-hidden=" & GUICtrlGetState($idButton))
GUICtrlSetState($idButton, $GUI_SHOW)
Note("[state] Button-shown=" & GUICtrlGetState($idButton))
Note("[state] Checkbox-checked=" & GUICtrlGetState($idCheck))

; --- return values ---
Note("[ret] GUICtrlSetData=" & GUICtrlSetData($idLabel, "new label"))
Note("[ret] GUICtrlSetPos=" & GUICtrlSetPos($idLabel, 20, 45))
Note("[ret] GUICtrlSetState=" & GUICtrlSetState($idLabel, $GUI_SHOW))
Note("[ret] GUICtrlSetColor=" & GUICtrlSetColor($idLabel, 0xFF0000))
Note("[ret] GUICtrlSetBkColor=" & GUICtrlSetBkColor($idLabel, 0x00FF00))
Note("[ret] GUICtrlSetFont=" & GUICtrlSetFont($idLabel, 10, 700))
Note("[ret] GUICtrlSetResizing=" & GUICtrlSetResizing($idLabel, $GUI_DOCKALL))
Note("[ret] GUICtrlSetTip=" & GUICtrlSetTip($idLabel, "tip"))
Note("[ret] GUICtrlSetLimit=" & GUICtrlSetLimit($idInput, 10))
Note("[ret] GUICtrlSetStyle=" & GUICtrlSetStyle($idLabel, $SS_CENTER))
Note("[ret] GUICtrlSetOnEvent=" & GUICtrlSetOnEvent($idLabel, ""))
Note("[ret] GUISetCoord=" & GUISetCoord(5, 5))
Note("[ret] GUIStartGroup=" & GUIStartGroup())
Note("[ret] GUISetOnEvent=" & GUISetOnEvent($GUI_EVENT_CLOSE, ""))
Note("[ret] GUISetState=" & GUISetState(@SW_HIDE, $hWin))
Note("[ret] GUISetStyle=" & GUISetStyle(-1, -1, $hWin))
Local $aStyle = GUIGetStyle($hWin)
Note("[ret] GUIGetStyle=" & $aStyle[0] & "," & $aStyle[1])
Note("[ret] GUIGetMsg=" & GUIGetMsg())
Note("[ret] GUISetBkColor=" & GUISetBkColor(0xFFFFFF, $hWin))
Note("[ret] GUISetFont=" & GUISetFont(9, 400, 0, "Arial", $hWin))
Note("[ret] GUISwitch=" & (GUISwitch($hWin) = $hWin))
Note("[ret] GUICtrlDelete=" & GUICtrlDelete($idMenuSep))
Note("[ret] GUIDelete=" & GUIDelete($hWin2))

; --- option values actually in force ---
Note("[opt] GUIDataSeparatorChar=[" & Opt("GUIDataSeparatorChar") & "]")

FileClose($g_hFile)
