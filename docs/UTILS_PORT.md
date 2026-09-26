# Utils port

**Source:** `Py4GWCoreLib/py4gwcorelib_src/Utils.py` — 842 lines, `class Utils` at line 12 with
**40** `@staticmethod`s. Ported as `py4gw/py4gwcorelib_src/utils.py`, with the one dependency it
imports, `py4gwcorelib_src/Color.py` (414 lines, `Color` + `ColorPalette`), at
`py4gw/py4gwcorelib_src/color.py`.

**Where the files live.** `py4gw/py4gwcorelib_src/` is the source's own relative path under this
project's package root — the rule `py4gw/enums_src/` already follows for
`Py4GWCoreLib/enums_src/` — with the file names in this project's casing (`docs/STYLE.md`) and every
name inside them the source's. `Utils.py:9`'s `from .Color import Color` is therefore a sibling
import here too.

**Verdict: INCOMPLETE.** 37 of the 40 members work; **3 remain**, and each names what it needs:

| Member | What it needs |
| --- | --- |
| `TokenizeMarkupText` | the client's own ImGui text measure — `PyImGui.StyleConfig()` (pushed and restored around the measure) and `PyImGui.calc_text_size(...)`, which is the only thing that can answer how wide a string renders. `PyImGui` is an in-client binding module this port does not load; the work item is on [`TARGET_SIDE_WORK.md`](TARGET_SIDE_WORK.md), and it is the **first** member in this port that needs the client's ImGui at all. The tokenizer's regex work around the measure is not what is missing. |
| `GwinchToPixels` | `Map.MissionMap.GetScale()` — both bodies are the source's, and the raise a caller sees is `MissionMap.GetScale`'s own. `Map.MissionMap.GetZoom()` is ported; the frame viewport scale is the missing read, and it is blocked on the render viewport: Reforged's `frame_info.viewport_scale()` reads `viewport_scale_x/y`, which native *computes* in `FramePosition::GetViewportScale` from `GW::render::GetViewportWidth/Height()` (`include/GW/ui/ui.h:553-561`), and those come from the DX context native only learns from its `EndScene`/`Reset` detours (`render.cpp:75-111`). The `GwDxContext` row in [`TARGET_SIDE_WORK.md`](TARGET_SIDE_WORK.md) is that capture. |
| `PixelsToGwinch` | the same two reads as `GwinchToPixels`. |

**`GenerateSkillbarTemplate` landed with the `Skillbar` port** (2026-09-26): it is the source's own
body over the ported `SkillBar.GetSkillIDBySlot` — with one recorded route difference, because the
source reaches the same line through the `GLOBAL_CACHE.SkillBar` mirror this project does not port.
The member's docstring carries it and [`SKILLBAR_PORT.md`](SKILLBAR_PORT.md) has the detail.

The two that raise through `Map` are in the source's own call graph, which is how `Agent`'s
delegating members are recorded too: the member is written as the source writes it, and the raise
comes from the member that owns the missing piece.

## What it unblocked, in the same change

`Utils` was the queue head because four members of other classes were waiting on it. Three answer
now, and the fourth is ported with its missing half named at the call site:

| Member | What changed |
| --- | --- |
| `Player.BuySkill` | ported: `Utils.SkillIdToDialogId(skill_id)` then the already-ported `Player.SendRawDialog` — the source's `PlayerMethods.SendSkillTrainerDialog` (`native_src/methods/PlayerMethods.py:426-436`) without the `ActionQueueManager` that queued it |
| `Player.UnlockBalthazarSkill` | **complete**: `Utils.BalthazarSkillIdToDialogId` runs its PvP remap through `Skill.ExtraData.GetIDPvP`, which landed with the `Skill` port ([`SKILL_PORT.md`](SKILL_PORT.md)), then the same ported `SendRawDialog` (`PlayerMethods.py:438-450`) |
| `Agent.GetEnergyPips` | ported: the record's `max_energy`/`energy_regen` through `Utils.calculate_energy_pips` |
| `Agent.GetHealthPips` | ported: the record's `max_hp`/`hp_pips` through `Utils.calculate_health_pips` |
| `Utils.GenerateSkillbarTemplate` | **complete**: the source's body over the ported `SkillBar.GetSkillIDBySlot`, which landed with [`SKILLBAR_PORT.md`](SKILLBAR_PORT.md)'s class |

## The two departures from the source's text

Neither changes a value, and both are visible in the code that carries them:

1. **Imports.** `import PyImGui` (`Utils.py:6`) is not carried — it is an in-client binding module
   this port does not load, and the one member that used it names it instead. `from ..enums import
   CAP_EXPERIENCE, CAP_STEP, EXPERIENCE_PROGRESSION` (`Utils.py:11`) reaches
   `Py4GWCoreLib/enums.py`, a re-export hub; the port imports the three constants from the module
   that *declares* them, the already-ported `py4gw/enums_src/game_data_enums.py`.
2. **`ClearSubModules`' console lines.** The source logs each decision through `ConsoleLog`
   (`Utils.py:832, 837, 840`) — Reforged's console **inside the client**. There is no external
   equivalent, so the decisions and the `sys.modules` work are carried and the log lines are not,
   the same divergence already recorded for `Agent`'s `PySystem.Console` diagnostics. The table it
   edits is the running interpreter's: the client's in the source, this controller's here.

**One finding, ported as written rather than "fixed".** `GetExperienceProgression`'s docstring
promises `(level, percent, skill_points)` and its body returns the percentage alone, over a `lvl`
and a `skill_points` it computes and discards (`Utils.py:221-246`). Both branches return `pct`. That
is the source's behaviour, so the port returns the percentage; `tests/test_utils_offline.py` pins it
so a later pass does not turn the docstring into the contract.

**One guard kept where the source keeps it.** `BalthazarSkillIdToDialogId` computes `resolved` and
returns `0` for a non-positive id *before* the remap (`Utils.py:797-799`), so a zero id never reaches
the skill read — `Utils.BalthazarSkillIdToDialogId(0)` answers `0`.

**And the one difference the execution model introduces here, written down rather than worked
around.** The source wraps the `Skill` import and call in `try`/`except Exception` and carries on
with `pvp_id = 0` (`Utils.py:801-807`). In Reforged that call cannot fail for want of a connection;
here it can, so a caller with nothing connected takes the source's own handler and receives the
*unremapped* id rather than a usage error. The alternative — raising instead — would be a guard the
source does not have, so the structure is the source's and the consequence is recorded
([`SKILL_PORT.md`](SKILL_PORT.md) has the same note from the `Skill` side).

## Verification

- `tests/test_utils_offline.py` — **27 offline tests**, and the strongest of them does not restate
  the arithmetic: it loads Reforged's own `Utils.py` and `Color.py` (with `PyImGui` and the `..enums`
  hub stubbed for the duration of the load) and calls the port beside the source over a table of 33
  members, so the 68-case base64 table, the skill-template encoder and parser, the markup regexes and
  the colour packing are compared with the code Reforged ships. The surface is read out of the source
  at test time (40 members, source order, none added), and the palette is compared member for member.
  The Balthazar conversion is checked over the source's own branches and against the loaded source
  module for the same record value.
- `tests/test_skill_offline.py` — **32 offline tests** for the `Skill` class the Balthazar remap
  reaches, including records decoded out of `Gw.exe` on disk ([`SKILL_PORT.md`](SKILL_PORT.md)).
- `tests/test_player_offline.py` — `BuySkill` and `UnlockBalthazarSkill` moved from the refusing list
  to the action list (**18 actions, 5 refusals**), both with their default arguments.
- `tests/test_agent_offline.py` — `GetEnergyPips` and `GetHealthPips` moved out of the blocked list
  into the read table, with the source's own formula as the expected value; `IsMartial`/`IsMelee`
  now name `Effects.HasEffect` alone, because `Skill.GetID` is ported.
- `tests/test_map_offline.py` — `Map.MissionMap.GetZoom` recorded as implemented (45 implemented
  paths of the 178 declared members).
- No live run is needed for this change: nothing in it touches the client. `GwinchToPixels`,
  `PixelsToGwinch`, `TokenizeMarkupText` and `GenerateSkillbarTemplate` are the members a live run
  would exercise, and each of them raises before reaching the client.
