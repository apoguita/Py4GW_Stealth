# Skill port

**Source:** `Py4GWCoreLib/Skill.py` — 511 lines, `class Skill` at line 6 with **87 members** across
the class and its five nested namespaces (`Data`, `Attribute`, `Flags`, `Animations`, `ExtraData`).
Ported as `py4gw/skill.py`, over three things the port carries with it:

| what | source | where |
| --- | --- | --- |
| the client's skill constant record | `include/GW/context/skill.h` — `GW::Context::Skill`, `static_assert(sizeof(Skill) == 0xA4)` | `py4gw/context/skill_context.py`: `SkillStruct`, its offset asserts, and `SkillConstantArray` |
| the binding object every member reads | `src/GW/skillbar/skill_bindings.cpp:69-199` — `PySkill`, with `PySkillID`/`PySkillType`/`PySkillProfession` beside it | `py4gw/skill.py`: `PySkill`, `SkillID`, `SkillType`, `SkillProfession` |
| native's generated name tables | `src/GW/skillbar/skill_names.cpp` — 3031 skill names, 29 type names, 11 profession names | `py4gw/skill_names.py` (the skill names) and `py4gw/skill.py` (the two small switches) |

**Verdict: INCOMPLETE.** **79 of the 87 members work; 8 raise**, and each names what it needs:

| Member | What it needs |
| --- | --- |
| `_load_descriptions` | Reforged's bundled `Py4GWCoreLib/skill_descriptions.json` — **1,975,988 bytes** beside `Skill.py`, which the member opens and caches (`Skill.py:9-15`). This port carries no copy of that file, and it is data rather than capability. |
| `GetNameFromWiki`, `GetURL`, `GetProgressionData`, `GetDescription`, `GetConciseDescription` | the same file — each of the five raises through `_load_descriptions`, which is the source's own call graph |
| `GetCampaign` | `enums_src/Region_enums.py`'s `CampaignName` (`Region_enums.py:132-140`), a campaign-id to name table; that module has no ported home yet. The record's own `campaign` value is readable through the binding — it is the name table that is missing. |
| `ExtraData.GetTexturePath` | `enums_src/Texture_enums.py`'s `SkillTextureMap` (~3100 entries, skill id → icon file name); that module has no ported home yet. |

## What landed, and why it is not a partial class

The record, the binding object and all three name tables are the *whole* of the surface Reforged's
members read, so every member that does not touch the three data files above works, and it works on
the source's own path: `Skill.skill_instance(skill_id)` answers `PySkill(skill_id)`, whose
`GetContext()` copies the record exactly as `skill_bindings.cpp:134-195` copies it, and each member
is the source's one-line read over it.

**The record was verified against the client before anything was written on top of it.** The table is
the client's own static data: the function this project's catalog resolves as
`skillbar.skill_array_addr` is the accessor the client itself uses, and its whole body is

```asm
005a9160  55                push ebp
005a9164  8b 75 08          mov  esi, [ebp+8]        ; esi = skill_id
005a9167  81 fe a7 0d 00 00 cmp  esi, 0xDA7          ; the table's own bound (3495)
005a9183  69 c6 a4 00 00 00 imul eax, esi, 0xA4     ; stride = sizeof(Skill)
005a918a  05 b0 b4 98 00    add  eax, 0x98B4B0       ; &skill_array[skill_id]
005a9190  c3                ret
```

The 2026-09-30 update (build 38974) moved all three of those numbers: the function is now at
`0x005A9160` (was `0x005A8D20`), the bound is `0xDA7` (3495, was `0xD94`/3476) and the table is at
`0x98B4B0` (was `0x98A370`). `SKILL_ARRAY_LENGTH` in `py4gw/context/skill_context.py` carries the
re-measured bound, and the offline test's address constant was re-pinned to `0x98B4B0` — where the
first twelve records read `0, 1, … 11`, while the old address no longer holds a table of skill ids.
The resolver needed no change: it reads the immediate out of the client's own instruction.

so the port's reader is `address + skill_id * 0xA4` behind the client's own bound, with no call, no
hook and no state involved. `tests/test_skill_offline.py` then decodes the real records out of
`Gw.exe` on disk — offline, through the port's own resolver, record and members — and pins what the
client holds: Healing Signet is a 2-second, 4-second-recharge Signet with no energy cost, Power Block
is an elite 15-energy Spell (the client's own `11` encoding), Meteor Shower is 25 energy (`12`) with a
60-second recharge, Blood Renewal costs 1 energy and 15% health, and the 25 records carrying
`special & 0x1` are exactly the exhaustion skills, whose `overcast` byte is their exhaustion
percentage.

## The one place the port's behaviour is wider than the source's, and it is recorded

`Skill.ExtraData.GetIDPvP` now answers, so `Utils.BalthazarSkillIdToDialogId` runs its remap — and
the source's own body wraps that call in `try`/`except Exception` (`Utils.py:801-807`). In Reforged
the call cannot fail for want of a connection; here, with nothing connected, the record read raises
and the source's handler takes `pvp_id = 0`. The port keeps the source's structure rather than adding
a guard of its own, which means a caller with no connection gets the *unremapped* id instead of a
usage error. That is the source's code path, and it is written down here because it is the one
observable difference the execution model introduces in this class.

**One dependency got sharper rather than smaller.** `Agent.IsMartial`/`IsMelee` needed
`Skill.GetID("Illusionary_Weaponry")` *and* `Effects.HasEffect`; `Skill.GetID` is ported now (the
name table answers `33` for that name), so the one thing those two members still wait on is
`Effects.HasEffect` (`Effect.py:102`) — the `Effect` class, which is its own queued port.

## Verification

- `tests/test_skill_offline.py` — **32 offline tests**: the 87 source member names, in the source's
  order and nesting, read out of `Skill.py` at test time; the binding object's field list against
  native's bound surface; every record offset against `skill.h`'s own offset comments; the flag bits
  and the energy-cost encoding; the three generated tables compared with `skill_names.cpp` at test
  time (3031 pairs, in source order); each implemented member against a chosen record; the members
  that raise, naming their table; and the client-bytes checks described above.
- `tests/test_utils_offline.py` — the Balthazar conversion is now checked as `<0x10000000 | id>`
  over the source's own branches, and against the loaded source module for the same record value.
- `tests/test_player_offline.py` — `UnlockBalthazarSkill` is an action member with its default
  arguments: the conversion runs, and the failure a caller sees with nothing connected is the
  connection's.
- No live run is needed for this change: the record read is a memory read, and the tests drive it
  against the client's own bytes.
