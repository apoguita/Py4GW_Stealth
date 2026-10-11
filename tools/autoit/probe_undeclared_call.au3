; Probe: what does AutoIt do with a call to a function that is declared nowhere?
; The report claims it is a fatal compile error rather than a call that answers zero, and that claim
; decides whether the missing wrapper declarations are a convenience or a blocker.
Local $v = Core_Initialize(1234, True)
ConsoleWrite("returned: " & $v & @CRLF)
