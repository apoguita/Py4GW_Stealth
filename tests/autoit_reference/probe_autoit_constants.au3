#NoTrayIcon

; Prints the values the AutoIt interpreter itself assigns to the GUI-relevant macros
; and the default values of the GUI options. Written for Py4GW_Stealth's AutoIt-compatible
; GUI layer: these numbers are read from the running interpreter, not from documentation.

Local $sOut = ""

$sOut &= "[macros]" & @CRLF
$sOut &= "@SW_HIDE=" & @SW_HIDE & @CRLF
$sOut &= "@SW_SHOWNORMAL=" & @SW_SHOWNORMAL & @CRLF
$sOut &= "@SW_SHOWMINIMIZED=" & @SW_SHOWMINIMIZED & @CRLF
$sOut &= "@SW_SHOWMAXIMIZED=" & @SW_SHOWMAXIMIZED & @CRLF
$sOut &= "@SW_SHOWNOACTIVATE=" & @SW_SHOWNOACTIVATE & @CRLF
$sOut &= "@SW_SHOW=" & @SW_SHOW & @CRLF
$sOut &= "@SW_MINIMIZE=" & @SW_MINIMIZE & @CRLF
$sOut &= "@SW_SHOWMINNOACTIVE=" & @SW_SHOWMINNOACTIVE & @CRLF
$sOut &= "@SW_SHOWNA=" & @SW_SHOWNA & @CRLF
$sOut &= "@SW_RESTORE=" & @SW_RESTORE & @CRLF
$sOut &= "@SW_SHOWDEFAULT=" & @SW_SHOWDEFAULT & @CRLF
$sOut &= "@SW_DISABLE=" & @SW_DISABLE & @CRLF
$sOut &= "@SW_ENABLE=" & @SW_ENABLE & @CRLF
$sOut &= "@SW_LOCK=" & @SW_LOCK & @CRLF
$sOut &= "@SW_UNLOCK=" & @SW_UNLOCK & @CRLF

$sOut &= "[options-defaults]" & @CRLF
$sOut &= "GUIOnEventMode=" & Opt("GUIOnEventMode") & @CRLF
$sOut &= "GUIEventOptions=" & Opt("GUIEventOptions") & @CRLF
$sOut &= "GUICoordMode=" & Opt("GUICoordMode") & @CRLF
$sOut &= "GUIResizeMode=" & Opt("GUIResizeMode") & @CRLF
$sOut &= "GUICloseOnESC=" & Opt("GUICloseOnESC") & @CRLF

FileWrite(@ScriptDir & "\probe_constants_out.txt", $sOut)
