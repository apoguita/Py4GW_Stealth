; What does GUICtrlDelete do to a ListViewItem or a TreeViewItem?
;
; The port's own GUICtrlDelete deleted the control record and left the row in the control, which
; is what made a table that is cleared and refilled grow instead of being repopulated. The
; reference's page says only "Deletes a control ... Success: 1", so the behaviour is measured here:
; how many rows the control holds before and after, what GUICtrlRead reports for a deleted item,
; and what a deleted item's neighbours read.

#include <GUIConstantsEx.au3>
#include <WindowsConstants.au3>
#include <GuiListView.au3>
#include <GuiTreeView.au3>

Const $sReport = @ScriptDir & "\probe_autoit_delete_item_out.txt"
FileDelete($sReport)

Func _Say($sLine)
    FileWrite($sReport, $sLine & @CRLF)
EndFunc

Local $hGUI = GUICreate("delete item", 500, 400, 200, 200)
Local $idList = GUICtrlCreateListView("A|B", 10, 10, 300, 150)
Local $idOne = GUICtrlCreateListViewItem("one|1", $idList)
Local $idTwo = GUICtrlCreateListViewItem("two|2", $idList)
Local $idThree = GUICtrlCreateListViewItem("three|3", $idList)
GUISetState(@SW_SHOW, $hGUI)
Sleep(400)

_Say("listview rows before      : " & _GUICtrlListView_GetItemCount($idList))
_Say("item 2 text               : " & GUICtrlRead($idTwo))
_Say("GUICtrlDelete(item 2)     : " & GUICtrlDelete($idTwo))
Sleep(200)
_Say("listview rows after       : " & _GUICtrlListView_GetItemCount($idList))
_Say("item 1 text still reads   : " & GUICtrlRead($idOne))
_Say("item 3 text still reads   : " & GUICtrlRead($idThree))
_Say("deleted item 2 reads      : " & GUICtrlRead($idTwo))
_Say("row 0 / row 1 text        : " & _GUICtrlListView_GetItemText($idList, 0) & " / " & _
        _GUICtrlListView_GetItemText($idList, 1))
_Say("GUICtrlDelete(item 2) again: " & GUICtrlDelete($idTwo))

Local $idTree = GUICtrlCreateTreeView(320, 10, 160, 150)
Local $treeOne = GUICtrlCreateTreeViewItem("alpha", $idTree)
Local $treeTwo = GUICtrlCreateTreeViewItem("beta", $idTree)
GUICtrlCreateTreeViewItem("gamma", $idTree)
Sleep(200)
_Say("treeview items before     : " & _GUICtrlTreeView_GetCount($idTree))
_Say("GUICtrlDelete(tree item 1): " & GUICtrlDelete($treeOne))
Sleep(200)
_Say("treeview items after      : " & _GUICtrlTreeView_GetCount($idTree))
_Say("tree item 2 text          : " & GUICtrlRead($treeTwo))

; A List control: does deleting an item of it work too? (A List's items are not control IDs.)
Local $idPlainList = GUICtrlCreateList("", 10, 200, 200, 120)
GUICtrlSetData($idPlainList, "red")
GUICtrlSetData($idPlainList, "green")
GUICtrlSetData($idPlainList, "blue")
Sleep(200)
_Say("plain list reads          : " & GUICtrlRead($idPlainList))
_Say("GUICtrlDelete(list id)    : " & GUICtrlDelete($idPlainList))
Sleep(200)
_Say("after deleting the list   : " & GUICtrlRead($idPlainList))

GUIDelete($hGUI)
Exit
