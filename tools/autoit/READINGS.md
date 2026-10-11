# GwAu3 bridge: readings from the AutoIt interpreter

**What was measured, and by what.** `tools/autoit/probe_bridge_stdio.au3`, run under the AutoIt
interpreter installed on this machine (`C:\Program Files (x86)\AutoIt3\AutoIt3.exe`, version
**3.3.16.1**, x86), against the worker launched by `tools/autoit/run_bridge_worker.py`. The raw output
is `probe_bridge_stdio_out.txt` beside this file. Nothing here is inferred from documentation.

## Readings

| Question | AutoIt's answer |
| --- | --- |
| Can AutoIt start a Python worker and talk to it? | **yes** — `Run($cmd, $dir, @SW_HIDE, $STDIN_CHILD + $STDOUT_CHILD + $STDERR_CHILD)` returned a pid |
| Does a written line arrive? | **yes** — `StdinWrite($pid, $json & @LF)` and the worker answered |
| Can a whole reply line be read? | **yes** — `StdoutRead` in a loop, splitting on `@CRLF`/`@LF` |
| Does the channel carry more than one request? | **yes** — a second request was answered, and its reply echoed `"id":2` |
| Where does the worker's own output go? | **stderr** — the banner `gwa3 worker: protocol 1, 12 routines, one JSON object per line` arrived on `StderrRead`, leaving stdout carrying only protocol replies |
| Is a reply one line? | **yes** — the JSON is emitted with `separators=(",", ":")` and no newline inside |

The two readings, verbatim:

```text
reply: {"ok":false,"id":1,"error":{"kind":"unknown","detail":"no function named NoSuchFunction -- not in this layer and not declared by GwAu3"}}
reply 2: {"ok":false,"id":2,"error":{"kind":"error","detail":"RuntimeError: No Guild Wars client is connected. Call py4gw.connect() first."}}
```

Both are failures **without a client**, which is the point: the transport was proven with no Guild Wars
running and no elevation, and the second reading shows a routine that needs the client reporting a
described error rather than a stand-in value.

## Two things the probe taught, both about AutoIt rather than about the bridge

1. **`#RequireAdmin` makes a script produce no output at all when run unelevated.** The first version
   carried it, and running it from an ordinary shell produced nothing — no error, no console line. The
   directive makes AutoIt refuse to start rather than fail loudly. The probe does not need elevation
   (it asks only for names that need no client), so the directive is gone; **the real UDF must not
   carry it either**, because the *connection* needs elevation, not the transport, and an author
   should get a described refusal from the worker rather than a script that silently does nothing.
2. **`Run()` takes an executable, not a document.** The first version launched `@AutoItExe` on the
   `.py` path, which ran AutoIt against a file it cannot parse; the probe then waited for a reply that
   was never coming. The worker is started as `python -u <script>`, and `-u` matters — without it
   Python buffers stdout and the reply would sit in the pipe.

## `@error` does not survive `Return Inner_()` — measured, and it changed the UDF

The bridge's whole failure contract for an AutoIt caller is `If @error Then`. So whether `@error` can
cross a function boundary is not a detail: if it cannot, every failure the bridge reports is invisible
to a migrated script, and only the global carries it.

`probe_error_macro.au3` asked the interpreter, and the answer is two rules:

```text
direct call, then local:     value=99 @error=2
Return Inner_():             value=99 @error=0   <- LOST
Return SetError(@error,...): value=99 @error=2   <- kept
three levels, re-set each:   value=99 @error=2   <- kept
optional arg positional:     value=0 @error=2
```

1. **`Return Inner_()` loses it.** AutoIt resets `@error` when a function returns a *call expression*,
   so the value comes back and the macro does not. A wrapper written `Return _Stealth_Call(...)` —
   which is the obvious way to write one, and what the generator emitted first — silently swallows
   every failure's `@error`.
2. **`Return SetError(@error, 0, $v)` keeps it**, because the macro is read as an argument *before*
   the new function resets it. That is the shape both the generated wrappers and `_Stealth_Call` now
   use, at every level — a helper that returned its result straight through would lose it for the same
   reason, so each one captures and re-sets.

Without this reading the UDF would have shipped with a documented `If @error Then` contract that never
fired, and `tests/...` could not have caught it: the failure is a property of the interpreter, not of
the code being generated.

## An undeclared function is fatal, and that decides what the UDF must declare

Measured 2026-10-09, AutoIt 3.3.16.1 (x86), `tools/autoit/probe_undeclared_call.au3` — one line calling
`Core_Initialize(1234, True)`, a GwAu3 function this layer's UDF does not declare:

```
probe_undeclared_call.au3 (4) : ==> Unknown function name.:
Local $v = Core_Initialize(1234, True)
Local $v = ^ ERROR
exit=1
```

**AutoIt refuses to run the script at all.** It does not call the function, return zero, or set
`@error` — the file is rejected when it is compiled. So the UDF's *declared* surface is not a
convenience: a migrated GwAu3 script that calls a routine with no wrapper **does not load**, however
good the implementation behind it is.

That is why `tools/analyze_gwa3_example_parity.py` reports the two surfaces separately.
`tools/autoit/Stealth_GwAu3.au3` declares 648 wrappers — **322 of the 667 GwAu3 functions the checkout
calls** — which leaves **345 called names with no wrapper at all** (`UAI_` 113, `Assembler_` 40,
`Memory_` 23, `Utils_` 23, `Scanner_` 22, `Anti_` 18, `Core_` 10, `Log_` 8, `Pathfinder_` 7 …). Each of
those is a script that cannot start.

## A GwAu3 script, running on the layer (2026-10-10)

`tools/autoit/test_ported_script.au3` is written the way a GwAu3 author writes one — GwAu3's include,
GwAu3's function names, GwAu3's `$GC_*` constants, GwAu3's own ordering (`Core_Initialize` first, then
the reads) — and it runs against the live client through this layer. It is
`Exemple_AutoitGUI_Tester.au3`'s sequence without the Koda GUI, because a GUI needs a hand on the Start
button and this has to run unattended.

Launcher: `tests/scratch/_elev_2026-10-09_ported_script.cmd`; log: `tests/live_reports/ported_script.log`.
Elevated, because `Core_Initialize` connects.

```
=== a GwAu3 script on the Stealth layer ===
PASS  the bridge started
PASS  Guild Wars is running
PASS  Core_Initialize answered 1
[INFO] [script] Core_Initialize opened pid 19696
[INFO] [SetDebugMode] Debug Mode Enabled
[DEBUG] [script] this line must appear: debug mode is on
[WARNING] [script] a warning renders through the same callback
PASS  Agent_GetAgentInfo(-2, "X") is a number
...
[INFO] [script] at -947,3347 level 20 hp 585 as 'Fezzik The Untamed'
PASS  Party_GetPartyContextInfo("IsPartyLeader") is a boolean
PASS  a quest the log does not hold answers False
PASS  Skill_GetSkillInfo(1, "EnergyCost") answered
PASS  Skill_GetSkillInfo takes a $GC_* constant as its key
PASS  Core_IsIngame is refused rather than guessed
PASS  Cache_SkillBar is declared and reports itself unbuilt
PASS  UAI_Fight is declared and reports itself unbuilt
=== 17 passed, 0 failed ===
```

**What this establishes, which no earlier run could.** GwAu3's own first line works
(`Core_Initialize` answered 1, keeping GwAu3's contract); the log module's gate works — the DEBUG line
before `Log_SetDebugMode(True)` is absent from the log and the one after it is present, which is
GwAu3's own gate order; all seven read families answer through GwAu3's names and this layer's reads; a
refused routine reports its rule instead of a value; and **the two calls the example makes that are not
built yet are callable and report themselves**, which is the difference between a script that loads and
a script that dies at the parser.

**Two names a ported script must declare, and they are GwAu3's own requirement.** `Core_AutoStart`'s
transcription reads `$g_bAutoStart` and `$g_s_MainCharName` and calls `StartBot()` and `_Exit()`
(`GwAu3_Core.au3:595-648`); those belong to the script, and `Exemple_AutoitGUI_Tester.au3:18-19`, `:60`
and `:160` are where GwAu3's own example declares them. A ported script that omits them does not
compile, exactly as it would not under GwAu3.

## What a migrated script compiles to, measured with Au3Check

Measured 2026-10-09. `Au3Check.exe` (the syntax checker shipped with AutoIt 3.3.16.1) over each
GwAu3 script in `external/GwAu3/Scripts/` and over the migrated copy of it written beside the original
by `python tools/analyze_gwa3_example_parity.py --write`:

| Script | As shipped | Migrated | Reading |
| --- | --- | --- | --- |
| `Exemple_AutoitGUI_Tester.au3` | 10 | **0** | a clean migration |
| `Exemple_ImGUI_Tester.au3` | 14 | 2 | the 2 are `$c_UTILS_Msg_Type_*`, mutable `Global`s |
| `Exemple_PathFinding.au3` | 11 | 26 | 24 are duplicate-`Const` collisions — see below |
| `Tools_VisibleEffect.au3` | 10 | 4 | 1 undeclared (`$ImGuiWindowFlags_*` class) |
| `GwAu3_DevTools.au3` | 16 | 4 | 2 undeclared, same class |
| `Multi-Launcher.au3` | 0 | **0** | does not include the API at all; unaffected |
| `Punch_Out_Farm.au3` | 47 | 403 | **not measurable** — see below |

**The copies are written beside their originals, and that matters.** A GwAu3 script's include graph is
relative to its own directory: the launcher pulls in `../../Utilities/_GUICtrlEmoji/_GUICtrlEmoji.au3`,
the ImGui example `../../Utilities/ImGui/ImGui.au3`. Copied to another directory the launcher — which
checks *clean* as shipped — reported 22 undeclared globals, every one of them the emoji constants from
an include that could no longer be found. Migrating in place is both what this measures honestly and
what a migrating user does.

**`Punch_Out_Farm.au3` cannot be compiled from this checkout at all.** It includes five files that are
not in the repository — `GwAu3_AddOns_Punch_Out_Farm.au3`, `GUI_Punch_Out_Farm.au3`, `Security.au3`,
`PunchOut_Launcher.au3`, `GwAu3_PunchOut_GUI_Logic.au3` — so its own 47 errors and the migrated 403 are
missing companions, not a measurement.

**The duplicate-`Const` collisions are a real migration constraint, not a checker artefact.** The UDF
now declares GwAu3's whole constant surface (7,480 names) so that a script's own `$GC_*` uses resolve.
A script whose include graph *also* reaches GwAu3 API or plugin files — `Exemple_PathFinding.au3`
includes `../../API/Plugins/Pathfinder/_Pathfinder.au3`, `Punch_Out_Farm.au3` includes
`UtilityAI/_UtilityAI.au3` — then declares the same names twice, and AutoIt reports
`previously declared as a 'Const'` for each. **The UDF replaces `_GwAu3.au3`; it does not sit beside
it.** A migration must move the whole include graph, or migrate the add-on files too.

## What this establishes, and what it does not

- **Established:** a persistent AutoIt→Python channel exists, carries multiple request/response pairs,
  keeps protocol traffic on stdout and the worker's chatter on stderr, reports failures by kind, and
  **carries `@error` out to the caller** (`test_stealth_udf.au3`: 13 checks, 13 passed, with no client
  running).
- **Established:** a call to a name the UDF does not declare is a **fatal compile error** (measured
  above), so a missing wrapper is a script that will not load rather than a call that falls back.
- **Established:** with the wrapper surface extended to every GwAu3 function the checkout calls (993
  declared, 46 implemented) and the constant surface carried over (7,480 `$GC_*` names) plus GwAu3's
  own 150 standard UDL includes, one of GwAu3's example scripts goes from **10 Au3Check errors to 0**.
- **Not established:** that a migrated script *runs*. `Au3Check` is a syntax checker, and nothing here
  started a script against a live bridge -- the AutoIt→Python channel is proven separately by
  `test_stealth_udf.au3`, and the routines behind it by `tests/test_gwa3_live.py`. The compile
  evidence above says a script will load, not that its calls will succeed.
- **Not established:** constants GwAu3 declares as *mutable* `Global`s (not `Const`/`Enum`):
  `$c_UTILS_Msg_Type_*`, `$a_UTILS_Log_Messages`, `$ImGuiWindowFlags_*` and their neighbours. They are
  library state, not a name table, and they are why three of the migrated scripts still report 1-2
  undeclared globals.
- **Not established:** anything requiring a client. No routine that reads the game was exercised
  against a *client* in this file; that is `tests/test_gwa3_live.py`, which reads a running client
  read-only and passes. The transport is proven here; the routines behind it are proven separately.
- **Not established:** a named-pipe transport. `docs/GWA3_COMPAT_SPEC.md` specifies a pipe as the
  intended channel and gives the reason — a single byte stream cannot carry a request and its result
  apart from stray output. Stdio works because the worker keeps its own output on stderr, and that is
  a discipline rather than a frame. A pipe remains the right answer for a worker that must also log.
