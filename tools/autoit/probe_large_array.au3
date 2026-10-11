; Probe: does AutoIt accept a large array initialiser split across `_` continuation lines?
; `Global Const $A[2000][2] = [[0,'x'],[1,'y'],...]` on one physical line fails with
; "Error in expression" (measured, $GC_AMX2_SKILL_DATA). This asks whether the limit is the physical
; line or the statement, because that decides how the AutoIt constant table can be emitted at all.
Global Const $A[4] = [1, 2, _
	3, 4]

Global Const $B[2000] = [0, 1, _
	2, 3, _
	4, 5]

ConsoleWrite("A=" & $A[3] & " B=" & $B[5] & @CRLF)
