; What does GwAu3's UAI_ExtractHPBonus actually answer?
;   Local $l_a_Result = StringRegExp($a_s_Effect, "Health \+(\d+)", 1)
;   If IsArray($l_a_Result) Then Return Int($l_a_Result[0])
; Whether element [0] is the full match or the capture decides the return value.
#include <Array.au3>

Local $g_s_Log = @ScriptDir & "\_probe_regexp.log"

Func _w($s)
	FileWrite($g_s_Log, $s & @CRLF)
EndFunc

FileDelete($g_s_Log)

Func _show($subject, $pattern)
	Local $a = StringRegExp($subject, $pattern, 1)
	_w("subject=" & $subject & " pattern=" & $pattern)
	If Not IsArray($a) Then
		_w("   no match (returns 0)")
		Return
	EndIf
	_w("   UBound=" & UBound($a))
	For $i = 0 To UBound($a) - 1
		_w("   [" & $i & "] = '" & $a[$i] & "'  Int=" & Int($a[$i]))
	Next
EndFunc

_show("Health +30", "Health \+(\d+)")
_show("+30 HP", "\+(\d+) HP")
_show("+45 HP while Enchanted", "\+(\d+) HP")
_show("+60 HP while Hexed", "\+(\d+) HP")
_show("Energy +5", "Energy \+(\d+)")
_show("Energy +15 (-1 energy regen)", "Energy \+(\d+)")
_show("Armor +5", "Energy \+(\d+)")

; And what Int() does with a leading-text string, for the record.
_w("Int('Health +30') = " & Int("Health +30"))
