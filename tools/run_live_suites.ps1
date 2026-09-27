# Run live Guild Wars suites in an elevated process, one report file each.
#
# Usage (from an elevated shell, or spawned with -Verb RunAs):
#     pwsh -NoProfile -File tools\run_live_suites.ps1
#     pwsh -NoProfile -File tools\run_live_suites.ps1 tests.test_player tests.test_agent_array
#
# Every suite connects to the running client, which requires elevation. The default set is ordered:
# the read-only and observing suites first, the ones that write to the client's own state next, and
# the suite that ends with a dialog left open (it interacts with an NPC and this project does not
# synthesise the Escape key) last.

param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Suites)

$ErrorActionPreference = "Continue"
Set-Location (Split-Path -Parent $PSScriptRoot)

$reports = Join-Path (Get-Location) "live_reports"
New-Item -ItemType Directory -Force -Path $reports | Out-Null

if (-not $Suites -or $Suites.Count -eq 0) {
    $Suites = @(
        "tests/probe_agent_effects_live.py", # read-only probe: names, effects and the timer, no connect
        "tests.test_live_agent_effects",     # read-only: the name binding, Effects, the skill timer
        "tests.test_agent_array",            # read-only: the source-shaped AgentArray view
        "tests.test_live_skill",             # read-only: Skill, SkillBar, Utils over the live client
        "tests.test_live_dat",               # the GW.dat chain and the dialog text it decodes
        "tests.test_live_call",              # the bridge, the call forms and the client's own functions
        "tests/probe_chat_log_write.py",     # the chat-log witness (writes a line into the client's log)
        "tests.test_live_agent_chat",        # the chat senders' send half + agent enums
        "tests.test_live_player"             # the Player actions; leaves a dialog open at the end
    )
}

$summary = @()
$summary += "elevated: $(([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator))"
$summary += "started:  $(Get-Date -Format o)"
$summary += ""

foreach ($suite in $Suites) {
    # One report file per suite, named for the suite itself — a module entry ("tests.test_x") and a
    # probe path ("tests/probe_x.py") both land as a single flat name under live_reports\.
    $log = Join-Path $reports ((Split-Path -Leaf $suite) + ".log")
    $started = Get-Date
    Write-Host "=== $suite ==="

    # A probe script is not a unittest module: it is run as a file and reports through its own file.
    # The entry is a path relative to the repo root ("tests/probe_x.py"), kept as given — probes have
    # no TestCase, so `python -m unittest` would import them and run nothing.
    if ($suite -like "*.py") {
        $file = Join-Path (Get-Location) $suite
        & python $file *> $log
    } else {
        & python -m unittest $suite -v *> $log
    }

    $code = $LASTEXITCODE
    $elapsed = [int]((Get-Date) - $started).TotalSeconds
    $tail = (Select-String -Path $log -Pattern "^(Ran |OK|FAILED)" | ForEach-Object { $_.Line }) -join " | "
    $summary += ("{0,-34} exit={1,-3} {2,4}s  {3}" -f $suite, $code, $elapsed, $tail)
    Write-Host ("    exit={0} {1}s {2}" -f $code, $elapsed, $tail)
}

$summary += ""
$summary += "finished: $(Get-Date -Format o)"
$summary | Set-Content -Path (Join-Path $reports "summary.txt")
Write-Host ""
$summary | ForEach-Object { Write-Host $_ }
