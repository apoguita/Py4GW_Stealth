# `Agent_GetAgentInfo`: which field keys this project can answer

**Generated** by `python tools/audit_gwa3_agent_fields.py` — do not edit by hand.

The read side of the GwAu3-compatible layer rests on one claim: GwAu3's field names can be answered from the structures this project already reads. This is the measurement of that claim for the accessor with the most call sites in GwAu3's own scripts — **216**, the highest of any function.

## How to read this

| Verdict | Meaning |
| --- | --- |
| **NAMED** | the structure declares a real attribute at the offset GwAu3 reads — the key is answerable by name |
| **OFFSET ONLY** | an attribute occupies the offset but its name is an `hXXXX` placeholder — answerable, but the data has no name here |
| **ABSENT** | no attribute occupies the offset — the compatibility layer would need a raw offset read, which is what the porting rules forbid outside the ported classes |
| **COMPUTED** | GwAu3's case does not read a field; it computes or delegates (a count, a decode, another accessor) |

## Result

The field offsets are read from the `ctypes` descriptors of `AgentLivingStruct` — including the fields it inherits — so the verdicts rest on the client layout this project already validates, not on arithmetic done here.

- `Agent_GetAgentInfo` `Case` groups: **137**, covering **142** keys
- structure fields parsed from `AgentLivingStruct`: **95**
- **NAMED**: 96 case groups
- **OFFSET ONLY**: 29 case groups
- **ABSENT**: 7 case groups
- **COMPUTED**: 5 case groups
- keys answerable by name: **101 of 142**

## Every case

| Keys | GwAu3 line | Offset | Verdict | What answers it |
| --- | --- | --- | --- | --- |
| `h0004` | `GwAu3_Data_Agent.au3:89` | `0x4` | OFFSET ONLY | `h0004` (4 bytes at 0x4) |
| `h0008` | `GwAu3_Data_Agent.au3:91` | `0x8` | OFFSET ONLY | `h0008` (4 bytes at 0x8) |
| `h000C` | `GwAu3_Data_Agent.au3:93` | `0xc` | OFFSET ONLY | `h000C` (8 bytes at 0xc) |
| `h0010` | `GwAu3_Data_Agent.au3:95` | `0x10` | ABSENT | no attribute occupies 0x10 in the structure |
| `Timer` | `GwAu3_Data_Agent.au3:97` | `0x14` | NAMED | `timer` (4 bytes at 0x14) |
| `Timer2` | `GwAu3_Data_Agent.au3:99` | `0x18` | NAMED | `timer2` (4 bytes at 0x18) |
| `h001C` | `GwAu3_Data_Agent.au3:101` | `0x1c` | NAMED | `link_link` (8 bytes at 0x1c) |
| `ID` | `GwAu3_Data_Agent.au3:103` | `0x2c` | NAMED | `agent_id` (4 bytes at 0x2c) |
| `Z` | `GwAu3_Data_Agent.au3:105` | `0x30` | NAMED | `z` (4 bytes at 0x30) |
| `Width1` | `GwAu3_Data_Agent.au3:107` | `0x34` | NAMED | `width1` (4 bytes at 0x34) |
| `Height1` | `GwAu3_Data_Agent.au3:109` | `0x38` | NAMED | `height1` (4 bytes at 0x38) |
| `Width2` | `GwAu3_Data_Agent.au3:111` | `0x3c` | NAMED | `width2` (4 bytes at 0x3c) |
| `Height2` | `GwAu3_Data_Agent.au3:113` | `0x40` | NAMED | `height2` (4 bytes at 0x40) |
| `Width3` | `GwAu3_Data_Agent.au3:115` | `0x44` | NAMED | `width3` (4 bytes at 0x44) |
| `Height3` | `GwAu3_Data_Agent.au3:117` | `0x48` | NAMED | `height3` (4 bytes at 0x48) |
| `Rotation` | `GwAu3_Data_Agent.au3:119` | `0x4c` | NAMED | `rotation_angle` (4 bytes at 0x4c) |
| `RotationCos` | `GwAu3_Data_Agent.au3:121` | `0x50` | NAMED | `rotation_cos` (4 bytes at 0x50) |
| `RotationSin` | `GwAu3_Data_Agent.au3:123` | `0x54` | NAMED | `rotation_sin` (4 bytes at 0x54) |
| `NameProperties` | `GwAu3_Data_Agent.au3:125` | `0x58` | NAMED | `name_properties` (4 bytes at 0x58) |
| `Ground` | `GwAu3_Data_Agent.au3:127` | `0x5c` | NAMED | `ground` (4 bytes at 0x5c) |
| `h0060` | `GwAu3_Data_Agent.au3:129` | `0x60` | OFFSET ONLY | `h0060` (4 bytes at 0x60) |
| `TerrainNormalX` | `GwAu3_Data_Agent.au3:131` | `0x64` | NAMED | `terrain_normal` (12 bytes at 0x64) |
| `TerrainNormalY` | `GwAu3_Data_Agent.au3:133` | `0x68` | ABSENT | no attribute occupies 0x68 in the structure |
| `TerrainNormalZ` | `GwAu3_Data_Agent.au3:135` | `0x6c` | ABSENT | no attribute occupies 0x6c in the structure |
| `h0070` | `GwAu3_Data_Agent.au3:137` | `0x70` | OFFSET ONLY | `h0070` (4 bytes at 0x70) |
| `X` | `GwAu3_Data_Agent.au3:139` | `0x74` | NAMED | `pos` (12 bytes at 0x74) |
| `Y` | `GwAu3_Data_Agent.au3:141` | `0x78` | ABSENT | no attribute occupies 0x78 in the structure |
| `Plane` | `GwAu3_Data_Agent.au3:143` | `0x7c` | ABSENT | no attribute occupies 0x7c in the structure |
| `h0080` | `GwAu3_Data_Agent.au3:145` | `0x80` | OFFSET ONLY | `h0080` (4 bytes at 0x80) |
| `NameTagX` | `GwAu3_Data_Agent.au3:147` | `0x84` | NAMED | `name_tag_x` (4 bytes at 0x84) |
| `NameTagY` | `GwAu3_Data_Agent.au3:149` | `0x88` | NAMED | `name_tag_y` (4 bytes at 0x88) |
| `NameTagZ` | `GwAu3_Data_Agent.au3:151` | `0x8c` | NAMED | `name_tag_z` (4 bytes at 0x8c) |
| `VisualEffects` | `GwAu3_Data_Agent.au3:153` | `0x90` | NAMED | `visual_effects` (2 bytes at 0x90) |
| `h0092` | `GwAu3_Data_Agent.au3:155` | `0x92` | OFFSET ONLY | `h0092` (2 bytes at 0x92) |
| `h0094` | `GwAu3_Data_Agent.au3:157` | `0x94` | OFFSET ONLY | `h0094` (8 bytes at 0x94) |
| `Type` | `GwAu3_Data_Agent.au3:161` | `0x9c` | NAMED | `type` (4 bytes at 0x9c) |
| `IsItemType` | `GwAu3_Data_Agent.au3:163` | `0x9c` | NAMED | `type` (4 bytes at 0x9c) |
| `IsGadgetType` | `GwAu3_Data_Agent.au3:165` | `0x9c` | NAMED | `type` (4 bytes at 0x9c) |
| `IsLivingType` | `GwAu3_Data_Agent.au3:167` | `0x9c` | NAMED | `type` (4 bytes at 0x9c) |
| `MoveX` | `GwAu3_Data_Agent.au3:171` | `0xa0` | NAMED | `velocity` (8 bytes at 0xa0) |
| `MoveY` | `GwAu3_Data_Agent.au3:173` | `0xa4` | ABSENT | no attribute occupies 0xa4 in the structure |
| `h00A8` | `GwAu3_Data_Agent.au3:175` | `0xa8` | OFFSET ONLY | `h00A8` (4 bytes at 0xa8) |
| `RotationCos2` | `GwAu3_Data_Agent.au3:177` | `0xac` | NAMED | `rotation_cos2` (4 bytes at 0xac) |
| `RotationSin2` | `GwAu3_Data_Agent.au3:179` | `0xb0` | NAMED | `rotation_sin2` (4 bytes at 0xb0) |
| `h00B4` | `GwAu3_Data_Agent.au3:181` | `0xb4` | OFFSET ONLY | `h00B4` (16 bytes at 0xb4) |
| `Owner` | `GwAu3_Data_Agent.au3:184` | `0xc4` | NAMED | `owner` (4 bytes at 0xc4) |
| `CanPickUp` | `GwAu3_Data_Agent.au3:186` | `0x9c` | NAMED | `type` (4 bytes at 0x9c) |
| `ItemID` | `GwAu3_Data_Agent.au3:192` | `0xc8` | OFFSET ONLY | `h00C8` (4 bytes at 0xc8) |
| `ExtraType` | `GwAu3_Data_Agent.au3:194` | `0xcc` | OFFSET ONLY | `h00CC` (4 bytes at 0xcc) |
| `GadgetID` | `GwAu3_Data_Agent.au3:196` | `0xd0` | OFFSET ONLY | `h00D0` (4 bytes at 0xd0) |
| `h00D4` | `GwAu3_Data_Agent.au3:198` | `0xd4` | OFFSET ONLY | `h00D4` (12 bytes at 0xd4) |
| `AnimationType` | `GwAu3_Data_Agent.au3:200` | `0xe0` | NAMED | `animation_type` (4 bytes at 0xe0) |
| `h00E4` | `GwAu3_Data_Agent.au3:202` | `0xe4` | OFFSET ONLY | `h00E4` (8 bytes at 0xe4) |
| `AttackSpeed` | `GwAu3_Data_Agent.au3:204` | `0xec` | NAMED | `weapon_attack_speed` (4 bytes at 0xec) |
| `AttackSpeedModifier` | `GwAu3_Data_Agent.au3:206` | `0xf0` | NAMED | `attack_speed_modifier` (4 bytes at 0xf0) |
| `PlayerNumber`, `ModelID` | `GwAu3_Data_Agent.au3:208` | `0xf4` | NAMED | `player_number` (2 bytes at 0xf4) |
| `AgentModelType` | `GwAu3_Data_Agent.au3:210` | `0xf6` | NAMED | `agent_model_type` (2 bytes at 0xf6) |
| `TransmogNpcId` | `GwAu3_Data_Agent.au3:212` | `0xf8` | NAMED | `transmog_npc_id` (4 bytes at 0xf8) |
| `Equipment` | `GwAu3_Data_Agent.au3:214` | `0xfc` | NAMED | `equipment_ptr_ptr` (4 bytes at 0xfc) |
| `h0100` | `GwAu3_Data_Agent.au3:216` | `0x100` | OFFSET ONLY | `h0100` (4 bytes at 0x100) |
| `h0104_new` | `GwAu3_Data_Agent.au3:218` | `0x104` | OFFSET ONLY | `h0104` (4 bytes at 0x104) |
| `Tags` | `GwAu3_Data_Agent.au3:220` | `0x108` | NAMED | `tags_ptr` (4 bytes at 0x108) -- GwAu3 hops a pointer first |
| `h010C` | `GwAu3_Data_Agent.au3:222` | `0x10c` | OFFSET ONLY | `h010C` (2 bytes at 0x10c) |
| `Primary` | `GwAu3_Data_Agent.au3:224` | `0x10e` | NAMED | `primary` (1 bytes at 0x10e) |
| `Secondary` | `GwAu3_Data_Agent.au3:226` | `0x10f` | NAMED | `secondary` (1 bytes at 0x10f) |
| `Level` | `GwAu3_Data_Agent.au3:228` | `0x110` | NAMED | `level` (1 bytes at 0x110) |
| `Team` | `GwAu3_Data_Agent.au3:230` | `0x111` | NAMED | `team_id` (1 bytes at 0x111) |
| `h0112` | `GwAu3_Data_Agent.au3:232` | `0x112` | OFFSET ONLY | `h0112` (2 bytes at 0x112) |
| `h0114` | `GwAu3_Data_Agent.au3:234` | `0x114` | OFFSET ONLY | `h0114` (4 bytes at 0x114) |
| `EnergyPips`, `EnergyRegen` | `GwAu3_Data_Agent.au3:236` | `0x118` | NAMED | `energy_regen` (4 bytes at 0x118) |
| `Overcast` | `GwAu3_Data_Agent.au3:238` | `0x11c` | OFFSET ONLY | `h011C` (4 bytes at 0x11c) |
| `EnergyPercent` | `GwAu3_Data_Agent.au3:240` | `0x120` | NAMED | `energy` (4 bytes at 0x120) |
| `MaxEnergy` | `GwAu3_Data_Agent.au3:242` | `0x124` | NAMED | `max_energy` (4 bytes at 0x124) |
| `CurrentEnergy` | `GwAu3_Data_Agent.au3:244` | `0x120` | NAMED | `energy` (4 bytes at 0x120) |
| `h0128` | `GwAu3_Data_Agent.au3:246` | `0x128` | OFFSET ONLY | `h0128` (4 bytes at 0x128) |
| `HPPips`, `HPRegen` | `GwAu3_Data_Agent.au3:248` | `0x12c` | NAMED | `hp_pips` (4 bytes at 0x12c) |
| `h0130` | `GwAu3_Data_Agent.au3:250` | `0x130` | OFFSET ONLY | `h0130` (4 bytes at 0x130) |
| `HP`, `HPPercent` | `GwAu3_Data_Agent.au3:252` | `0x134` | NAMED | `hp` (4 bytes at 0x134) |
| `MaxHP` | `GwAu3_Data_Agent.au3:254` | `0x138` | NAMED | `max_hp` (4 bytes at 0x138) |
| `CurrentHP` | `GwAu3_Data_Agent.au3:256` | `0x134` | NAMED | `hp` (4 bytes at 0x134) |
| `Effects` | `GwAu3_Data_Agent.au3:259` | `0x13c` | NAMED | `effects` (4 bytes at 0x13c) |
| `EffectCount` | `GwAu3_Data_Agent.au3:261` | — | COMPUTED | If $l_p_AgentEffectsBase[1] = 0 Or $l_i_AgentEffectsCount[1] <= 0 Then Return 0 |
| `BondCount` | `GwAu3_Data_Agent.au3:280` | — | COMPUTED | If $l_p_AgentEffectsBase[1] = 0 Or $l_i_AgentEffectsCount[1] <= 0 Then Return 0 |
| `IsBleeding` | `GwAu3_Data_Agent.au3:302` | `0x13c` | NAMED | `effects` (4 bytes at 0x13c) |
| `IsConditioned` | `GwAu3_Data_Agent.au3:304` | `0x13c` | NAMED | `effects` (4 bytes at 0x13c) |
| `IsCrippled` | `GwAu3_Data_Agent.au3:306` | `0x13c` | NAMED | `effects` (4 bytes at 0x13c) |
| `IsDead` | `GwAu3_Data_Agent.au3:308` | `0x13c` | NAMED | `effects` (4 bytes at 0x13c) |
| `IsDeepWounded` | `GwAu3_Data_Agent.au3:310` | `0x13c` | NAMED | `effects` (4 bytes at 0x13c) |
| `IsPoisoned` | `GwAu3_Data_Agent.au3:312` | `0x13c` | NAMED | `effects` (4 bytes at 0x13c) |
| `IsEnchanted` | `GwAu3_Data_Agent.au3:314` | `0x13c` | NAMED | `effects` (4 bytes at 0x13c) |
| `IsDegenHexed` | `GwAu3_Data_Agent.au3:316` | `0x13c` | NAMED | `effects` (4 bytes at 0x13c) |
| `IsHexed` | `GwAu3_Data_Agent.au3:318` | `0x13c` | NAMED | `effects` (4 bytes at 0x13c) |
| `IsWeaponSpelled` | `GwAu3_Data_Agent.au3:320` | `0x13c` | NAMED | `effects` (4 bytes at 0x13c) |
| `h0140` | `GwAu3_Data_Agent.au3:323` | `0x140` | OFFSET ONLY | `h0140` (4 bytes at 0x140) |
| `Hex` | `GwAu3_Data_Agent.au3:325` | `0x144` | NAMED | `hex` (1 bytes at 0x144) |
| `h0145` | `GwAu3_Data_Agent.au3:327` | `0x145` | OFFSET ONLY | `h0145` (19 bytes at 0x145) |
| `ModelState` | `GwAu3_Data_Agent.au3:330` | `0x158` | NAMED | `model_state` (4 bytes at 0x158) |
| `IsKnockedDown`, `IsKnocked` | `GwAu3_Data_Agent.au3:332` | `0x158` | NAMED | `model_state` (4 bytes at 0x158) |
| `IsMoving` | `GwAu3_Data_Agent.au3:334` | `0xa0` | NAMED | `velocity` (8 bytes at 0xa0) |
| `IsAttacking` | `GwAu3_Data_Agent.au3:338` | `0x158` | NAMED | `model_state` (4 bytes at 0x158) |
| `IsCasting` | `GwAu3_Data_Agent.au3:341` | `0x1b8` | NAMED | `skill` (2 bytes at 0x1b8) |
| `IsIdle` | `GwAu3_Data_Agent.au3:345` | `0x158` | NAMED | `model_state` (4 bytes at 0x158) |
| `TypeMap` | `GwAu3_Data_Agent.au3:349` | `0x15c` | NAMED | `type_map` (4 bytes at 0x15c) |
| `InCombatStance` | `GwAu3_Data_Agent.au3:351` | `0x15c` | NAMED | `type_map` (4 bytes at 0x15c) |
| `HasQuest` | `GwAu3_Data_Agent.au3:353` | `0x15c` | NAMED | `type_map` (4 bytes at 0x15c) |
| `IsDeadByTypeMap` | `GwAu3_Data_Agent.au3:355` | `0x15c` | NAMED | `type_map` (4 bytes at 0x15c) |
| `IsFemale` | `GwAu3_Data_Agent.au3:357` | `0x15c` | NAMED | `type_map` (4 bytes at 0x15c) |
| `HasBossGlow` | `GwAu3_Data_Agent.au3:359` | `0x15c` | NAMED | `type_map` (4 bytes at 0x15c) |
| `IsHidingCap` | `GwAu3_Data_Agent.au3:361` | `0x15c` | NAMED | `type_map` (4 bytes at 0x15c) |
| `CanBeViewedInPartyWindow` | `GwAu3_Data_Agent.au3:363` | `0x15c` | NAMED | `type_map` (4 bytes at 0x15c) |
| `IsSpawned` | `GwAu3_Data_Agent.au3:365` | `0x15c` | NAMED | `type_map` (4 bytes at 0x15c) |
| `IsBeingObserved` | `GwAu3_Data_Agent.au3:367` | `0x15c` | NAMED | `type_map` (4 bytes at 0x15c) |
| `h0160` | `GwAu3_Data_Agent.au3:370` | `0x160` | OFFSET ONLY | `h0160` (16 bytes at 0x160) |
| `InSpiritRange` | `GwAu3_Data_Agent.au3:372` | `0x170` | NAMED | `in_spirit_range` (4 bytes at 0x170) |
| `VisibleEffectsPtr` | `GwAu3_Data_Agent.au3:374` | — | COMPUTED | Return $l_p_AgentPtr + 0x174 |
| `VisibleEffectsPrevLink` | `GwAu3_Data_Agent.au3:376` | `0x174` | NAMED | `visible_effects_list` (12 bytes at 0x174) |
| `VisibleEffectsNextNode` | `GwAu3_Data_Agent.au3:378` | `0x178` | ABSENT | no attribute occupies 0x178 in the structure |
| `VisibleEffectCount` | `GwAu3_Data_Agent.au3:381` | — | COMPUTED | Return VisibleEffect_Count($a_i_AgentID) |
| `HasVisibleEffects` | `GwAu3_Data_Agent.au3:383` | — | COMPUTED | Return VisibleEffect_Count($a_i_AgentID) > 0 |
| `h0180` | `GwAu3_Data_Agent.au3:386` | `0x180` | OFFSET ONLY | `h0180` (4 bytes at 0x180) |
| `LoginNumber` | `GwAu3_Data_Agent.au3:389` | `0x184` | NAMED | `login_number` (4 bytes at 0x184) |
| `IsPlayer` | `GwAu3_Data_Agent.au3:391` | `0x184` | NAMED | `login_number` (4 bytes at 0x184) |
| `IsNPC` | `GwAu3_Data_Agent.au3:393` | `0x184` | NAMED | `login_number` (4 bytes at 0x184) |
| `AnimationSpeed` | `GwAu3_Data_Agent.au3:396` | `0x188` | NAMED | `animation_speed` (4 bytes at 0x188) |
| `AnimationCode` | `GwAu3_Data_Agent.au3:398` | `0x18c` | NAMED | `animation_code` (4 bytes at 0x18c) |
| `AnimationId` | `GwAu3_Data_Agent.au3:400` | `0x190` | NAMED | `animation_id` (4 bytes at 0x190) |
| `h0194` | `GwAu3_Data_Agent.au3:402` | `0x194` | OFFSET ONLY | `h0194` (32 bytes at 0x194) |
| `LastStrike` | `GwAu3_Data_Agent.au3:404` | `0x1b4` | NAMED | `dagger_status` (1 bytes at 0x1b4) |
| `Allegiance` | `GwAu3_Data_Agent.au3:406` | `0x1b5` | NAMED | `allegiance` (1 bytes at 0x1b5) |
| `WeaponType` | `GwAu3_Data_Agent.au3:408` | `0x1b6` | NAMED | `weapon_type` (2 bytes at 0x1b6) |
| `Skill` | `GwAu3_Data_Agent.au3:410` | `0x1b8` | NAMED | `skill` (2 bytes at 0x1b8) |
| `h01BA` | `GwAu3_Data_Agent.au3:412` | `0x1ba` | OFFSET ONLY | `h01BA` (2 bytes at 0x1ba) |
| `WeaponItemType` | `GwAu3_Data_Agent.au3:414` | `0x1bc` | NAMED | `weapon_item_type` (1 bytes at 0x1bc) |
| `OffhandItemType` | `GwAu3_Data_Agent.au3:416` | `0x1bd` | NAMED | `offhand_item_type` (1 bytes at 0x1bd) |
| `WeaponItemId` | `GwAu3_Data_Agent.au3:418` | `0x1be` | NAMED | `weapon_item_id` (2 bytes at 0x1be) |
| `OffhandItemId` | `GwAu3_Data_Agent.au3:420` | `0x1c0` | NAMED | `offhand_item_id` (2 bytes at 0x1c0) |
| `Name` | `GwAu3_Data_Agent.au3:423` | `0x9c` | NAMED | `type` (4 bytes at 0x9c) |

## What is left

**A verdict here is about an attribute's exact offset, not about whether the data is reachable.** Where GwAu3 reads a field *inside* a nested struct -- ``TerrainNormalX``/``Y``/``Z`` are the components of ``terrain_normal`` (a ``Vec3f``), and ``X``/``Y``/``Plane`` are the components of ``pos`` (a ``GamePos``) -- the attribute that occupies that offset is the nested struct, so a probe comparing offsets one for one reports the *first* component as named and its siblings as absent. That is a gap in this audit's reach, not a gap in the port: the data is there, one level down. The same applies to ``VisibleEffectsNextNode``, which is inside ``visible_effects_list``.

These are the keys that do not resolve to a *named* attribute at their exact offset. The fixes are different in kind, so each is labelled:

- **`h0004`** (`GwAu3_Data_Agent.au3:89`, OFFSET ONLY) — `h0004` (4 bytes at 0x4)
- **`h0008`** (`GwAu3_Data_Agent.au3:91`, OFFSET ONLY) — `h0008` (4 bytes at 0x8)
- **`h000C`** (`GwAu3_Data_Agent.au3:93`, OFFSET ONLY) — `h000C` (8 bytes at 0xc)
- **`h0010`** (`GwAu3_Data_Agent.au3:95`, ABSENT) — no attribute occupies 0x10 in the structure
- **`h0060`** (`GwAu3_Data_Agent.au3:129`, OFFSET ONLY) — `h0060` (4 bytes at 0x60)
- **`TerrainNormalY`** (`GwAu3_Data_Agent.au3:133`, ABSENT) — no attribute occupies 0x68 in the structure
- **`TerrainNormalZ`** (`GwAu3_Data_Agent.au3:135`, ABSENT) — no attribute occupies 0x6c in the structure
- **`h0070`** (`GwAu3_Data_Agent.au3:137`, OFFSET ONLY) — `h0070` (4 bytes at 0x70)
- **`Y`** (`GwAu3_Data_Agent.au3:141`, ABSENT) — no attribute occupies 0x78 in the structure
- **`Plane`** (`GwAu3_Data_Agent.au3:143`, ABSENT) — no attribute occupies 0x7c in the structure
- **`h0080`** (`GwAu3_Data_Agent.au3:145`, OFFSET ONLY) — `h0080` (4 bytes at 0x80)
- **`h0092`** (`GwAu3_Data_Agent.au3:155`, OFFSET ONLY) — `h0092` (2 bytes at 0x92)
- **`h0094`** (`GwAu3_Data_Agent.au3:157`, OFFSET ONLY) — `h0094` (8 bytes at 0x94)
- **`MoveY`** (`GwAu3_Data_Agent.au3:173`, ABSENT) — no attribute occupies 0xa4 in the structure
- **`h00A8`** (`GwAu3_Data_Agent.au3:175`, OFFSET ONLY) — `h00A8` (4 bytes at 0xa8)
- **`h00B4`** (`GwAu3_Data_Agent.au3:181`, OFFSET ONLY) — `h00B4` (16 bytes at 0xb4)
- **`ItemID`** (`GwAu3_Data_Agent.au3:192`, OFFSET ONLY) — `h00C8` (4 bytes at 0xc8)
- **`ExtraType`** (`GwAu3_Data_Agent.au3:194`, OFFSET ONLY) — `h00CC` (4 bytes at 0xcc)
- **`GadgetID`** (`GwAu3_Data_Agent.au3:196`, OFFSET ONLY) — `h00D0` (4 bytes at 0xd0)
- **`h00D4`** (`GwAu3_Data_Agent.au3:198`, OFFSET ONLY) — `h00D4` (12 bytes at 0xd4)
- **`h00E4`** (`GwAu3_Data_Agent.au3:202`, OFFSET ONLY) — `h00E4` (8 bytes at 0xe4)
- **`h0100`** (`GwAu3_Data_Agent.au3:216`, OFFSET ONLY) — `h0100` (4 bytes at 0x100)
- **`h0104_new`** (`GwAu3_Data_Agent.au3:218`, OFFSET ONLY) — `h0104` (4 bytes at 0x104)
- **`h010C`** (`GwAu3_Data_Agent.au3:222`, OFFSET ONLY) — `h010C` (2 bytes at 0x10c)
- **`h0112`** (`GwAu3_Data_Agent.au3:232`, OFFSET ONLY) — `h0112` (2 bytes at 0x112)
- **`h0114`** (`GwAu3_Data_Agent.au3:234`, OFFSET ONLY) — `h0114` (4 bytes at 0x114)
- **`Overcast`** (`GwAu3_Data_Agent.au3:238`, OFFSET ONLY) — `h011C` (4 bytes at 0x11c)
- **`h0128`** (`GwAu3_Data_Agent.au3:246`, OFFSET ONLY) — `h0128` (4 bytes at 0x128)
- **`h0130`** (`GwAu3_Data_Agent.au3:250`, OFFSET ONLY) — `h0130` (4 bytes at 0x130)
- **`h0140`** (`GwAu3_Data_Agent.au3:323`, OFFSET ONLY) — `h0140` (4 bytes at 0x140)
- **`h0145`** (`GwAu3_Data_Agent.au3:327`, OFFSET ONLY) — `h0145` (19 bytes at 0x145)
- **`h0160`** (`GwAu3_Data_Agent.au3:370`, OFFSET ONLY) — `h0160` (16 bytes at 0x160)
- **`VisibleEffectsNextNode`** (`GwAu3_Data_Agent.au3:378`, ABSENT) — no attribute occupies 0x178 in the structure
- **`h0180`** (`GwAu3_Data_Agent.au3:386`, OFFSET ONLY) — `h0180` (4 bytes at 0x180)
- **`h0194`** (`GwAu3_Data_Agent.au3:402`, OFFSET ONLY) — `h0194` (32 bytes at 0x194)
- **`h01BA`** (`GwAu3_Data_Agent.au3:412`, OFFSET ONLY) — `h01BA` (2 bytes at 0x1ba)

