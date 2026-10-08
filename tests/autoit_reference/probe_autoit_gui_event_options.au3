; What Opt("GUIEventOptions", 1) does with a minimize request.
;
; The option's page: "0 = (default) Windows behavior on click on Minimize,Restore, Maximize, Resize.
; 1 = suppress windows behavior on minimize, restore or maximize click button or window resize.
; Just sends the notification."
;
; The request is sent as the system command a minimize button sends ($WM_SYSCOMMAND with
; $SC_MINIMIZE) rather than clicked on the title bar: that is the same message without needing the
; window to be on top, and an earlier version that clicked the button hung the interpreter.
;
; Run: "C:\Program Files (x86)\AutoIt3\AutoIt3.exe" /ErrorStdOut probe_autoit_gui_event_options.au3
; Writes probe_autoit_gui_event_options_out.txt next to itself.

#include <GUIConstantsEx.au3>
#include <WindowsConstants.au3>
#include <SendMessage.au3>

Opt("GUIOnEventMode", 1)

Const $sReport = @ScriptDir & "\probe_autoit_gui_event_options_out.txt"
FileDelete($sReport)

Func _Say($sLine)
    FileWrite($sReport, $sLine & @CRLF)
EndFunc

Global $sLog = ""

Func _Note($sWhat)
    $sLog &= $sWhat & ";"
EndFunc

Func _Run($iEventOptions)
    Opt("GUIEventOptions", $iEventOptions)
    $sLog = ""
    Local $hGUI = GUICreate("event options " & $iEventOptions, 400, 250, 200, 200)
    GUISetOnEvent($GUI_EVENT_MINIMIZE, "_OnMinimize")
    GUISetOnEvent($GUI_EVENT_RESTORE, "_OnRestore")
    GUISetState(@SW_SHOW, $hGUI)
    Sleep(600)
    Local $iBefore = WinGetState($hGUI)
    ; $WM_SYSCOMMAND (0x0112) with $SC_MINIMIZE (0xF020): what a minimize button sends.
    _SendMessage($hGUI, 0x0112, 0xF020, 0)
    Sleep(900)
    Local $iAfter = WinGetState($hGUI)
    _Say("GUIEventOptions=" & $iEventOptions & ": state before=" & $iBefore & " after=" & $iAfter _
            & " minimised=" & (BitAND($iAfter, 16) ? "yes" : "no"))
    _Say("  events: " & $sLog)
    WinSetState($hGUI, "", @SW_RESTORE)
    Sleep(600)
    _Say("  after a restore request: state=" & WinGetState($hGUI) & " events: " & $sLog)
    GUIDelete($hGUI)
    Sleep(400)
EndFunc

Func _OnMinimize()
    _Note("minimize")
EndFunc

Func _OnRestore()
    _Note("restore")
EndFunc

_Say("state bits: 16 = minimised (WinGetState); request = WM_SYSCOMMAND/SC_MINIMIZE")
_Run(0)
_Run(1)
Opt("GUIEventOptions", 0)
GUIDelete()
Exit

