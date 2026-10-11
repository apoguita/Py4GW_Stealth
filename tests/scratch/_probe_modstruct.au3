; What does GwAu3's Item_GetModStruct actually return, and how does the weapon-set
; search read it?  GwAu3_Data_Item.au3:776-781 reads
;   Memory_Read($p, 'Byte[' & size * 4 & ']')
; which is DllStructGetData on a byte array -- so the answer's *type* decides how
; UAI_SearchModsInArray's StringInStr/StringReplace behave on it.
#include <Array.au3>

Local $g_s_Log = @ScriptDir & "\_probe_modstruct.log"

Func _w($s)
	FileWrite($g_s_Log, $s & @CRLF)
EndFunc

FileDelete($g_s_Log)

Local $t = DllStructCreate("byte[8]")
DllStructSetData($t, 1, 0xDE, 1)
DllStructSetData($t, 1, 0x01, 2)
DllStructSetData($t, 1, 0x68, 3)
DllStructSetData($t, 1, 0x24, 4)
DllStructSetData($t, 1, 0x05, 5)
DllStructSetData($t, 1, 0x00, 6)
DllStructSetData($t, 1, 0xD8, 7)
DllStructSetData($t, 1, 0x22, 8)

Local $d = DllStructGetData($t, 1)
_w("vartype       = " & VarGetType($d))
_w("as text       = " & $d)
_w("StringLen     = " & StringLen($d))
_w("IsBinary      = " & IsBinary($d))
_w("InStr upper   = " & StringInStr($d, "DE016824"))
_w("InStr lower   = " & StringInStr($d, "de016824"))
_w("InStr tail    = " & StringInStr($d, "0500D822"))
Local $r = StringReplace($d, "DE016824", "")
_w("Replace       = " & $r)
_w("ReplaceLen    = " & StringLen($r))
_w("TrimLeft2     = " & StringTrimLeft($d, 2))
_w("Mid 5,4       = " & StringMid($d, 1 + 4, 4))
