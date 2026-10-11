# GwAu3 public surface inventory — Party, Map, MapContext, Ui, Trade

Scope: `external\GwAu3\API\Modules\Cmd\GwAu3_Cmd_{Party,Map,Ui,Trade}.au3` and
`external\GwAu3\API\Modules\Data\GwAu3_Data_{Party,Map,MapContext,Ui,Trade}.au3`.

**165 functions** total. This is a complete enumeration — every `Func` in the nine files is listed
(counts per file: Cmd_Party 22, Data_Party 16, Cmd_Map 14, Data_Map 17, Data_MapContext 30,
Cmd_Ui 40, Data_Ui 2, Cmd_Trade 18, Data_Trade 6).

Evidence class: **verified by source inspection** only. Nothing here was executed and no live client
was read. Line numbers are those of the files as checked out; the `read` tool's numbering is used
throughout (`GwAu3_Data_MapContext.au3` is 4187 lines, not the 3682 that
`Get-Content | Measure-Object -Line` reports, because that cmdlet skips empty lines).

---

## 0. The mechanism under every classification (read this first)

The five module families reach the client through **one shared dispatcher**, and knowing it is what
makes the per-function classification meaningful rather than nominal. Three facts:

1. **`Core_Enqueue($a_p_Ptr, $a_i_Size)` is a host-side `WriteProcessMemory`** of a struct into a
   queue that lives in `Gw.exe` (`GwAu3_Core.au3:559-566`, the `WriteProcessMemory` at line 560;
   slot address `256 * $g_i_QueueCounter + $g_p_QueueBase`). It has **no `Return` statement**.

2. **An injected dispatcher runs those slots on the game's own thread.** `MainProc` is a detour
   written over the client's main function (`Memory_WriteDetour('MainStart', 'MainProc')`,
   `GwAu3_Core_Assembler.au3:1905`). It reads the head slot, takes the **first dword of the slot as a
   function pointer** and `jmp ebx` to it (`GwAu3_Core_Assembler.au3:1999-2009`). So the first dword
   of every command struct is a label inside the injected block, planted host-side from
   `Memory_GetValue('Command…')` (`GwAu3_Core.au3:485-530`).

3. **Each command label either calls a scanner-resolved native in the client, or feeds the client's
   packet sender.** Examples: `CommandMove` → `call Move` (`Assembler:2498-2503`, call at 2501);
   `CommandDialog` → `call Dialog` (2655-2659, call at 2657); `CommandUIMsg` → `call UIMessage`
   (2645-2653, call at 2651); `CommandPacketSend` → `call PacketSend` (2088-2099, call at 2095).

Consequences for this report:

- **`Core_SendPacket` is not a host-side socket write.** It fills `$g_d_Packet` and enqueues 52 bytes
  (`GwAu3_Core.au3:575-589`); the first dword is `CommandPacketSend` (`Core.au3:451`); the client
  sends it from its own thread. Under this task's taxonomy that is still **PACKET SEND** — a packet
  is built and sent to the server — but the two stages are recorded so it is not mistaken for a
  direct `DllCall`. `Core_SendPacket` also has **no `Return` statement**, so every
  `Return Core_SendPacket(...)` in these modules returns AutoIt's default for a valueless function
  (`0`; *inferred* from the language — AutoIt was not run here) and **never reports whether the
  packet was built, sent, or accepted**.
- **`Core_Enqueue` used directly is classified GAME-THREAD CALL**, per this task's own definition
  naming `Core_Enqueue`. `assumed`/`Other` are not needed: the command label it names is a native
  call, cited per function.
- **MEMORY READ and MEMORY WRITE mean the host's own `ReadProcessMemory`/`WriteProcessMemory`**
  (`GwAu3_Core_Memory.au3:33-37` and `27-31`). They do **not** cover the enqueue write, which is
  listed under the classification of the command it carries.

### Global state that these classifications depend on

| symbol | where it is set | what it is |
| --- | --- | --- |
| `$g_p_BasePointer` | `Core.au3` (scanned) | root dereference for all `Memory_ReadPtr` chains |
| `$g_i_QueueCounter`, `$g_i_QueueSize`, `$g_p_QueueBase` | `Core.au3:440-442` | host mirror of the client's queue head; every `Core_Enqueue` advances the counter (`Core.au3:561-565`) |
| `$g_p_Packet`, `$g_d_Packet` | `Const_Core.au3:18-19`, first dword `Core.au3:451` | host packet struct; 52 bytes enqueued |
| `$g_b_DisableRendering` | `Core.au3:443` ← `Memory_GetValue('DisableRendering')` | **a slot inside the injected block**, not a client field (`Assembler_CreateData` `Assembler:1920`) |
| `$g_p_MapIsLoaded` | `Core.au3:444` ← `Memory_GetValue('MapIsLoaded')` | same: injected slot (`Assembler:1921`) |
| `$g_p_TradePartner` | `Core.au3:445` ← `Memory_GetValue('TradePartner')` | same: injected slot (`Assembler:1922`), written by the `TradePartnerProc` detour (`Assembler:2078-2085`) |
| `$g_p_PropRayReady`, `$g_p_PropRayResult` | `Core.au3:527-528` | injected slots (`Assembler:1928-1929`); the guard flag for prop ray casting |
| `$g_p_TradeSessReady`, `$g_p_TradeSessResult` | `Core.au3:531-532` | injected slots (`Assembler:1930-1931`); the guard flag for trade session natives |
| `$g_p_TimeOnMap`, `$g_p_Region`, `$g_p_InstanceInfo`, `$g_p_AreaInfo`, `$g_f_ClickCoordsX`, `$g_p_Ping` | `Core.au3:291-303` (scanned) | client addresses resolved at init |
| `$g_f_LastMoveX`, `$g_f_LastMoveY` | `Const_Core.au3:135-137`, reset `Core.au3:704`, written `Cmd_Map.au3:11-12` | **host-only** state, not client state |
| `$g_a2D_MapArray[882][10]` | `Const_Map.au3:1802` | host constant table (map names); read by `Map_GetExitPortalsCoords` and `Map_GetPathWithPortalCoords` |
| `$g_h_EditText` | host GUI | log-target handle used by `Log_*` in MapContext |
| constants | `Const_Core.au3:215-221, 233-235, 244-246` | `$GC_I_PROPRAY_MAX = 8`, `$GC_I_PROPRAY_INPUT_SIZE = 28`, `$GC_I_PROPRAY_RESULT_SIZE = 12`, `$GC_F_PROPRAY_MIN_RANGE = 0.1`, `$GC_I_PROPRAY_STATE_{PENDING,DONE,SKIPPED} = {0,1,2}`, `$GC_I_TRADESESS_STATE_*` likewise, `$GC_I_TRADE_FLAG_{ACTIVE,SUBMITTED,CONFIRMED} = {1,2,4}` |

---

## 1. `GwAu3_Cmd_Party.au3` — 22 functions

| # | Function (exact params, exact defaults) | Returns | Class | Mechanism / helper — cited lines |
| --- | --- | --- | --- | --- |
| 1 | `Party_AddHero($a_i_HeroId)` | `0` (see §0) | PACKET SEND | `Core_SendPacket(0x8, $GC_I_HEADER_HERO_ADD, $a_i_HeroId)` — 4-6 |
| 2 | `Party_KickHero($a_i_HeroId)` | `0` | PACKET SEND | `Core_SendPacket(0x8, $GC_I_HEADER_HERO_KICK, …)` — 9-11 |
| 3 | `Party_KickAllHeroes()` | `0` | PACKET SEND | `Core_SendPacket(0x8, $GC_I_HEADER_HERO_KICK, 0x28)` — 14-16 |
| 4 | `Party_AddNpc($a_i_NpcId)` | `0` | PACKET SEND | `Core_SendPacket(0x8, $GC_I_HEADER_PARTY_INVITE_NPC, …)` — 19-21 |
| 5 | `Party_KickNpc($a_i_NpcId)` | `0` | PACKET SEND | `Core_SendPacket(0x8, $GC_I_HEADER_PARTY_KICK_NPC, …)` — 24-26 |
| 6 | `Party_Tick($a_b_Tick = True)` | `0` | PACKET SEND | `Core_SendPacket(0x8, $GC_I_HEADER_PARTY_TICK, $a_b_Tick)` — 29-31 |
| 7 | `Party_CancelHero($a_i_HeroNumber)` | `0` | PACKET SEND | `Party_GetMyPartyHeroInfo(…,"AgentID")` (**MEMORY READ**) then `Core_SendPacket(0x14, …HERO_FLAG_SINGLE, $l_i_AgentID, 0x7F800000, 0x7F800000, 0)` — 34-37 |
| 8 | `Party_CancelAll()` | `0` | PACKET SEND | `Core_SendPacket(0x10, …HERO_FLAG_ALL, 0x7F800000, 0x7F800000, 0)` — 40-42 |
| 9 | `Party_CommandHero($a_i_HeroNumber, $a_f_X, $a_f_Y)` | `0` | PACKET SEND | reads AgentID, `Utils_FloatToInt` (pure), then `Core_SendPacket(0x14, …)` — 45-47 |
| 10 | `Party_CommandAll($a_f_X, $a_f_Y)` | `0` | PACKET SEND | `Core_SendPacket(0x10, …HERO_FLAG_ALL, Utils_FloatToInt(…), …, 0)` — 50-52 |
| 11 | `Party_LockHeroTarget($a_i_HeroNumber, $a_i_AgentID = 0)` | `0` | PACKET SEND | reads AgentID then `Core_SendPacket(0xC, …HERO_LOCK_TARGET, …)`; `0` cancels (comment 55) — 55-57 |
| 12 | `Party_SetHeroAggression($a_i_HeroNumber, $a_i_Aggression)` | `0` | PACKET SEND | reads AgentID then `Core_SendPacket(0xC, …HERO_BEHAVIOR, …)`; `0=Fight,1=Guard,2=Avoid` (comment 60) — 60-62 |
| 13 | `Party_ToggleHeroSkillState($a_i_HeroNumber, $a_i_SkillSlot)` | `0` | PACKET SEND | reads AgentID then `Core_SendPacket(0xC, …HERO_SKILL_TOGGLE, …, $a_i_SkillSlot - 1)` — 65-67 |
| 14 | `Party_GetIsHeroSkillDisabled($a_i_HeroNumber, $a_i_SkillSlot)` | boolean from `BitAND(...) > 0` | **MEMORY READ** | `Skill_GetSkillbarInfo($a_i_SkillSlot, "Disabled", $a_i_HeroNumber)` → `Memory_Read($l_p_SkillbarPtr + 0xA4, "dword")` (`Data_Skill.au3:237`) — 70-72 |
| 15 | `Party_EnableHeroSkill($a_i_HeroNumber, $a_i_SkillSlot)` | **no `Return`** → `0` on every path | PACKET SEND (conditional) | if #14 is true, calls #13 → `Core_SendPacket` — 75-77 |
| 16 | `Party_DisableHeroSkill($a_i_HeroNumber, $a_i_SkillSlot)` | `True` (line 82); `0` if the guard is false and no toggle happens — **see §7 ambiguity A1** | PACKET SEND (conditional) | if #14 is false, calls #13 → `Core_SendPacket`; unconditional `Return True` at 82 — 80-83 |
| 17 | `Party_LeaveGroup($a_b_KickHeroes = True)` | `0` | PACKET SEND | optional #3 (a second packet) then `Core_SendPacket(0x4, …PARTY_LEAVE_GROUP)` — 86-89 |
| 18 | `Party_AddPlayer($a_i_PlayerNumber)` | **no `Return`** → `0` | GAME-THREAD CALL | `DllStructSetData($g_d_AddPlayer, 2, …)` then `Core_Enqueue($g_p_AddPlayer, 8)` — 92-95; label `CommandAddPlayer` (`Core.au3:516`) → `call AddPlayer` (`Assembler:2762-2766`, call at 2764) |
| 19 | `Party_KickPlayer($a_i_PlayerNumber)` | `0` | GAME-THREAD CALL | `Core_Enqueue($g_p_KickPlayer, 8)` — 98-101 → `CommandKickPlayer` (`Core.au3:517`) → `call KickPlayer` (`Assembler:2768-2772`, call 2770) |
| 20 | `Party_KickInvitedPlayer($a_i_PartyID)` | `0` | GAME-THREAD CALL | `Core_Enqueue($g_p_KickInvitedPlayer, 8)` — 104-107 → `CommandKickInvitedPlayer` (`Core.au3:518`) → `call KickInvitedPlayer` (`Assembler:2774-2778`, call 2776) |
| 21 | `Party_RejectInvitation($a_i_PartyID)` | `0` | GAME-THREAD CALL | `Core_Enqueue($g_p_RejectInvitation, 8)` — 110-113 → `CommandRejectInvitation` (`Core.au3:519`) → `call RejectInvitation` (`Assembler:2780-2784`, call 2782) |
| 22 | `Party_AcceptInvitation($a_i_PartyID)` | `0` | GAME-THREAD CALL | `Core_Enqueue($g_p_AcceptInvitation, 8)` — 116-119 → `CommandAcceptInvitation` (`Core.au3:520`) → `call AcceptInvitation` (`Assembler:2786-2790`, call 2788) |

**Depends on:** `$g_d_AddPlayer`/`$g_p_AddPlayer`, `$g_d_KickPlayer`, `$g_d_KickInvitedPlayer`,
`$g_d_RejectInvitation`, `$g_d_AcceptInvitation` (`Const_Core.au3:161-172`, first dwords set
`Core.au3:516-520`) and `$g_i_QueueCounter`/`$g_p_QueueBase` for every enqueue.

**Counts:** PACKET SEND 16 · GAME-THREAD CALL 5 · MEMORY READ 1.

---

## 2. `GwAu3_Data_Party.au3` — 16 functions

| # | Function | Returns | Class | Mechanism / helper — cited lines |
| --- | --- | --- | --- | --- |
| 1 | `Party_GetPartyContextPtr()` | pointer (`$l_ap_PartyPtr[1]`; `0` when the chain dereferences to null — `Memory_ReadPtr` returns `[0,0]`, `Core_Memory.au3:48-51`) | MEMORY READ | `Memory_ReadPtr($g_p_BasePointer, [0,0x18,0x4C], 'ptr')` — 4-8 |
| 2 | `Party_GetPartyContextInfo($a_s_Info = "")` | per key: int (`Flags`, counts), boolean (the four `Is*` flags), pointer (`MyPartyPtr`); `0` if ptr null or `$a_s_Info = ""` (12) or unknown key (66). `TotalPartySize` = `PlayerCount + HenchmenCount + ArrayHeroPartyMemberSize` — note it calls `Party_GetMyPartyInfo` (62), **not** `HeroCount` | MEMORY READ | `Memory_Read($l_p_Ptr + off, …)` — 15-63 |
| 3 | `Party_GetMyPartyInfo($a_s_Info = "")` | pointer (`Array*`), int (sizes, `PartyID`), `0` if the parent ptr is null or info empty (71) or unknown (97) | MEMORY READ | via #2 `"MyPartyPtr"` (70), then `Memory_Read` — 73-94 |
| 4 | `Party_GetMyPartyPlayerMemberInfo($a_i_PartyMemberNumber = 1, $a_s_Info = "")` | int (`LoginNumber`, `CalledTargetID`, `State`), boolean (`IsConnected` = state bit 0, `IsTicked` = bit 1); `0` on bounds/empty/unknown (104, 107, 128) | MEMORY READ | stride `0xC` — 100-129 |
| 5 | `Party_GetMyPartyHeroInfo($a_i_HeroNumber = 1, $a_s_Info = "", $a_b_IncludeOtherHeroPlayers = False)` | int; `0` on: null array, `$a_i_HeroNumber < 1`, `> size` (135), `PlayerNumber = 0` (144), no match (159), unknown key (173). `"OwnerPlayerNumber"` returns the **loop-local** `$l_i_OwnerPlayerNumber` when `$a_b_IncludeOtherHeroPlayers` is false (166) — it is only defined because the `Else` branch ran | MEMORY READ | stride `0x18`; `Map_GetCharacterInfo("PlayerNumber")` — 131-175 |
| 6 | `Party_GetMyPartyHenchmanInfo($a_i_HenchmanNumber = 1, $a_s_Info = "")` | int; `0` on bounds/empty/unknown | MEMORY READ | stride `0x34` — 177-198 |
| 7 | `Party_GetMoraleInfo($a_v_AgentID = -2, $a_s_Info = "")` | `$l_av_Return[1] - 100` (`Morale`), raw value, booleans (`IsMaxMorale` ≥110, `IsMinMorale` ≤40, `IsBoost` >100, `IsPenalty` <100); **`0` if the read array is not an array or element 0 is 0** (214), and `0` for an unknown key (229/231) | MEMORY READ | `Agent_ConvertID` then two `Memory_ReadPtr` chains — 202-232 |
| 8 | `Party_GetPartyProfessionInfo($a_v_AgentID = 0, $a_s_Info = "")` | `dword` (`AgentID`, `Primary`, `Secondary`); `0` if no match in the array (250) or unknown key | MEMORY READ | `Memory_Read` at stride `0x14` — 237-262 |
| 9 | `Party_GetPetInfo($a_i_PetNumber = 1, $a_s_Info = "")` | values per key; `"PetNameEnc"` → `""` if `$l_p_NamePtr <= 0x10000` (285) else `Utils_DecodeEncString`; `"PetName"` → `"Unknown"` if `<= 0x10000` (289) else `Utils_DecodeEncStringAsync`; `0` on bounds/empty/unknown | **MEMORY READ** (primary) — but `"PetName"` is **mixed: MEMORY READ + MEMORY WRITE + GAME-THREAD CALL**, see §7 **A2** | `Memory_Read` stride `0x1C` — 267-310; `Utils_DecodeEncStringAsync` (`Utils:469-498`) writes `$g_p_DecodeReady` (480) and enqueues (483) → `CommandDecodeEncString` → `call ValidateAsyncDecodeStr` (`Assembler:2824-2849`, call 2847) |
| 10 | `Party_IsPet($a_v_AgentID)` | boolean = `#11 <> 0` | MEMORY READ | delegates to #11 — 313-315 |
| 11 | `Party_GetPetNumberByAgentID($a_v_AgentID)` | 1-based pet number, or `0` (`id = 0` → 320; count ≤ 0 → 323; no match → 328) | MEMORY READ | loops #9 — 318-329 |
| 12 | `Party_GetPetOwnerByAgentID($a_v_AgentID)` | `OwnerAgentID`, or `0` if not a pet | MEMORY READ | delegates to #11/#9 — 332-336 |
| 13 | `Party_GetControlledMinionsInfo($a_v_AgentID = 0, $a_s_Info = "")` | `AgentID`/`MinionCount`; `0` if no match (353) or unknown key | MEMORY READ | stride `0x8` — 340-363 |
| 14 | `Party_GetHeroFlagInfo($a_i_HeroNumber = 1, $a_s_Info = "")` | `dword`/`float` per key; `0` on: null array or out of range (371), AgentID 0 (374), no HeroID match (382), unknown key (401) | MEMORY READ | stride `0x24` — 368-402 |
| 15 | `Party_GetHeroInfo($a_i_HeroNumber = 1, $a_s_Info = "")` | per key; `"Name"` returns the `wchar[20]` at `+0x74` only when HeroID is 28..35, otherwise `$GC_AM2_HERO_DATA[$lHeroID][1]` (438-441); `0` on null/range/no-match/unknown. Note the bound is `>= $l_i_Size` here (407) where #14 uses `> $l_i_Size` (371) | MEMORY READ | stride `0x9C` — 404-445 |
| 16 | `Party_GetMemberAgentID($aPartyMember)` | AgentID, or `0`: `< 1` (452), player `LoginNumber = 0` (466), no living agent carries that LoginNumber (483), not found (514). Returns `Agent_GetMyID()` for self (471) | MEMORY READ | walks players → heroes (`IncludeOtherHeroPlayers = True`) → henchmen; `Agent_GetAgentArray(0xDB)` — 451-515 |

**Counts:** MEMORY READ 16 (one of them, #9, is internally mixed).

> Contract note (not a defect claim): the file's header comment for #16 must be read as
> `$aPartyMember` (the source writes `$aPartyMember` in the body and uses the `$a` prefix
> convention). Only the parameter name is `$aPartyMember`; there is no `$a_i_` prefix here.

---

## 3. `GwAu3_Cmd_Map.au3` — 14 functions

| # | Function | Returns | Class | Mechanism / helper — cited lines |
| --- | --- | --- | --- | --- |
| 1 | `Map_Move($a_f_X, $a_f_Y, $a_f_Randomize = 50)` | `True` always (21) | GAME-THREAD CALL | randomises when `> 0` (5-8), stores host globals `$g_f_LastMoveX/$g_f_LastMoveY` (11-12), fills `$g_d_Move` (15-17), `Core_Enqueue($g_p_Move, 16)` (19) → `CommandMove` (`Core.au3:485`) → `call Move` (`Assembler:2498-2503`, call 2501) |
| 2 | `Map_MoveLayer($a_f_X, $a_f_Y, $a_f_Layer = 0)` | `True` always (32) | GAME-THREAD CALL | `$g_d_Move` field 4 = layer (28), `Core_Enqueue($g_p_Move, 16)` (30) → same `CommandMove` |
| 3 | `Map_MoveMap($a_i_MapID, $a_i_Region, $a_i_District, $a_i_Language)` | `0` | PACKET SEND | `Core_SendPacket(0x18, …PARTY_TRAVEL, $a_i_MapID, $a_i_Region, $a_i_District, $a_i_Language, False)` — 36-38 |
| 4 | `Map_ReturnToOutpost($a_WaitToLoad = True)` | `Map_WaitMapIsLoaded()` (True/False) when `$a_WaitToLoad`; **`0`** when false (no `Return` on that path) | PACKET SEND (+ MEMORY WRITE, + MEMORY READ) — §7 **A3** | `Map_InitMapIsLoaded()` → `Memory_Write` (42); `Core_SendPacket(0x4, …RETURN_TO_OUTPOST)` (43); `Map_WaitMapIsLoaded()` (44) |
| 5 | `Map_EnterChallenge($a_WaitToLoad = True)` | as #4 | PACKET SEND (+ WRITE + READ) | `Core_SendPacket(0x8, …PARTY_ENTER_CHALLENGE, 1)` — 48-52 |
| 6 | `Map_TravelGH($a_WaitToLoad = True)` | as #4 | PACKET SEND (+ MEMORY READ of GH coords + WRITE + READ) | `Memory_ReadPtr($g_p_BasePointer, [0,0x18,0x3C])` then four `Memory_Read` (`+0x64,0x68,0x6C,0x70`) (61-65), `Core_SendPacket(0x18, …ENTER_GUILD_HALL, …)` |
| 7 | `Map_LeaveGH($a_WaitToLoad = True)` | as #4 | PACKET SEND (+ WRITE + READ) | `Core_SendPacket(0x8, …PARTY_LEAVE_GUILD_HALL, 1)` — 70-74 |
| 8 | `Map_TravelTo($a_i_MapID, $a_i_Language = Map_GetCharacterInfo("Language"), $a_i_Region = Map_GetCharacterInfo("Region"), $a_i_District = 0, $a_WaitToLoad = True)` | `True` early (82) when already on that MapID **and** `Map_GetInstanceInfo("IsOutpost")` **and** language/region match; otherwise `Map_WaitMapIsLoaded()` when `$a_WaitToLoad`, else `0` | PACKET SEND (+ MEMORY READ via the default expressions 78-81, + WRITE) | 77-87; delegates to #3 (85) |
| 9 | `Map_RndTravel($a_i_MapID, $a_WaitToLoad = True, $a_b_SwitchDistrict = True, $a_i_Mode = 0)` | `True` at 116 (one valid district) or 122 (no district switching); `Map_WaitMapIsLoaded()` when `$a_WaitToLoad`; else `0`. Mode comment 90: `0=All,1=EU,2=US,3=Asia` | PACKET SEND (+ MEMORY READ, + WRITE) | district tables 92-93, reads 108-110, `Map_MoveMap` 127 |
| 10 | `Map_WaitMapLoading($a_i_MapID = -1, $a_i_InstanceType = -1, $a_i_Timeout = 30000)` | `False` on timeout (151); `True` otherwise (155) | **MEMORY READ** (polling loop) — **mixed: PACKET SEND** via `Cinematic_SkipCinematic()` at 137, §7 **A4** | loop 134-150 reads `Agent_GetAgentPtr(-2)`, `Agent_GetMaxAgents`, `World_GetWorldInfo("SkillbarArray")`, `Party_GetPartyContextPtr` (#1 Cmd_Party), `Map_GetInstanceInfo("Type")`, `Map_GetCharacterInfo("MapID")`, `Game_GetGameInfo("IsCinematic")`, `Other_GetPing()` (`Data_Other.au3:4-6` → `Memory_Read($g_p_Ping)`) |
| 11 | `Map_InitMapIsLoaded()` | **no `Return`** → `0` | MEMORY WRITE | `Memory_Write($g_p_MapIsLoaded, 0)` — 158-160 |
| 12 | `Map_MapIsLoaded()` | `True` if the flag read as `1`; else `False` (167) — and on `True` it **clears the flag** (164) | MEMORY READ (+ MEMORY WRITE) | 162-168; `$g_p_MapIsLoaded` is an **injected-block slot** (§0) |
| 13 | `Map_WaitMapIsLoaded($a_i_Timeout = 30000)` | `True` if already loaded (171); `False` on timeout (178); `True` after a 500 ms sleep (182) | MEMORY READ (+ WRITE via #12) | 170-183 |
| 14 | `Map_WaitMapIsLoaded_Ping($a_i_Timeout = 30000)` | `True` at 188; then `Not $l_b_TimedOut` (199) — i.e. it always clears the flag (197) and returns `False` only on timeout | MEMORY READ (+ WRITE via `Map_InitMapIsLoaded` at 187/197) | 185-200; reads `$g_p_MapIsLoaded` directly (not via #12) and `Other_GetPing()` |

**Counts:** PACKET SEND 7 · MEMORY READ 4 · GAME-THREAD CALL 2 · MEMORY WRITE 1.

**Commented-out, not part of the surface:** `EnterChallengeForeign()` — 55-57.

---

## 4. `GwAu3_Data_Map.au3` — 17 functions

| # | Function | Returns | Class | Mechanism / helper — cited lines |
| --- | --- | --- | --- | --- |
| 1 | `Map_GetInstanceUpTime()` | `$l_av_Timer[1]` (ms); `0` if the chain nulls | MEMORY READ | `Memory_ReadPtr($g_p_BasePointer, [0,0x18,0x8,0x1AC])` — 4-8 |
| 2 | `Map_GetTimeOnMap()` | float, seconds | MEMORY READ | `Memory_Read($g_p_TimeOnMap,'float')` — 11-13 |
| 3 | `Map_GetRegion()` | value at the scanned region pointer | MEMORY READ | 15-17 |
| 4 | `Map_GetLastMoveCoords()` | `[X, Y]` 2-element array | **PURE COMPUTATION** | builds the array from **host** globals `$g_f_LastMoveX/$g_f_LastMoveY` — 19-22; no client access |
| 5 | `Map_GetClickCoords()` | `[X, Y]` float array | MEMORY READ | two `Memory_Read(…,'float')` at `$g_f_ClickCoordsX/Y` — 24-29 |
| 6 | `Map_GetInstanceInfo($a_s_Info = "")` | `Type` → int; `IsExplorable`/`IsLoading`/`IsOutpost` → boolean; `0` for `""` (33) and unknown keys (48) | MEMORY READ | `Memory_ReadPtr($g_p_InstanceInfo,[0x4],"dword")` — 32-49 |
| 7 | `Map_GetCurrentAreaInfo($a_s_Info = "")` | 26 keys, all `long`; `0` for `""` and unknown | MEMORY READ | `Memory_ReadPtr($g_p_InstanceInfo,[0x8],"ptr")` then `Memory_Read($l_p_Ptr + off)` — 51-121 |
| 8 | `Map_GetCurrentRegionType()` | string (0..21 mapped, `Else` → `"Unknown Else"`) | MEMORY READ | via #7 `"RegionType"` — 123-174 |
| 9 | `Map_GetCharacterContextPtr()` | pointer or `0` | MEMORY READ | `Memory_ReadPtr($g_p_BasePointer, [0,0x18,0x44], 'ptr')` — 178-182 |
| 10 | `Map_GetCharacterInfo($a_s_Info = "")` | `PlayerUUID` → 4-element array (189-194); `PlayerName` → `wchar[20]`; rest `long`; `0` if ptr null or `""` (186); **`0` for an unknown key** (229). `"Region"` reads `$g_p_Region` through `Utils_MakeInt32` (212), not the character context | MEMORY READ | 184-230 |
| 11 | `Map_GetMapID()` | `Map_GetCharacterInfo("MapID")` | MEMORY READ | 234-236 |
| 12 | `Map_IsMap($a_i_MapID)` | boolean = `Map_GetNormalizedMapID() = $a_i_MapID` | MEMORY READ | 239-241 |
| 13 | `Map_GetNormalizedMapID()` | MapID, or the normalised ID for event maps; **`SetError(1,0,0)` and returns `0`** when the ID is in 808..821 but matches no case (247, 275) | MEMORY READ | 244-276 |
| 14 | `Map_GetAreaPtr($aMapID = 0)` | `Ptr($g_p_AreaInfo + 0x7C * $aMapID)` — an address, not a read | **PURE COMPUTATION** | 279-282 |
| 15 | `Map_GetAreaInfo($aMapID, $aInfo = "")` | 40 keys: `long`/`float` reads, derived `FileID1`/`FileID2` (353-358), 7 flag booleans (359-379); `0` if ptr 0 or info empty (286) or unknown (382) | MEMORY READ | via #14 then `Memory_Read` — 284-383 |
| 16 | `Map_IsMapUnlocked($a_i_MapID)` | `True`/`False`; `False` when world context 0 (389), buffer or size 0 (395), `RealIndex >= size` (399) | MEMORY READ | `World_GetWorldContextPtr()` + `Memory_Read($l_p_ArrayStruct…,"ptr")` + bit test (401-405) — 386-406 |
| 17 | `Map_IsOutpost($a_i_MapID)` | `True` for RegionType 1,5,6,7,8,9,10,13,19; `False` otherwise and on the three early rejections (423, 424, 427, 429) | MEMORY READ | six `Map_GetAreaInfo` calls — 413-440 |

**Counts:** MEMORY READ 15 · PURE COMPUTATION 2.

**Name collision worth recording:** `Map_IsOutpost` (here, 413) is not `Map_GetInstanceInfo("IsOutpost")`
(232-49, which reports the *current* instance). Same word, different subjects.

---

## 5. `GwAu3_Data_MapContext.au3` — 30 functions (4187 lines)

| # | Function | Returns | Class | Mechanism / helper — cited lines |
| --- | --- | --- | --- | --- |
| 1 | `Map_GetMapContextPtr()` | pointer or `0` | MEMORY READ | `Memory_ReadPtr($g_p_BasePointer,[0,0x18,0x14],'ptr')` — 4-8 |
| 2 | `Map_GetMapContextInfo($a_s_Info = "")` | `MapBoundaries` → `float[5]` array; `Sub1`/`PropsContext`/`Terrain`/`Zones` → pointers; `Spawns1/2/3` → 3-element `[buffer, capacity, size]`; **`0`** when the context is null (14, with `Log_Error` at 13) **or** when `$a_s_Info = ""` (19, with `Log_Warning` at 18); **`0`** for an unknown key (falls through to 57) | MEMORY READ | 10-58 |
| 3 | `Map_GetPathingMapArray()` | `$p_Sub2 + 0x18`; `0` when `Sub1` is null (64, log 63) or `Sub2` is null (71, log 70) | MEMORY READ | 60-77 |
| 4 | `Map_GetPathingMapArrayInfo($a_s_Info = "")` | `Buffer` ptr / `Size` / `Capacity`; `0` when the array struct is 0 (81) or the key is unknown (91) | MEMORY READ | 79-92 |
| 5 | `Map_GetTotalTrapezoidCount()` | `dword` at `Sub1 + 0x18`; `0` when `Sub1` is null (98) | MEMORY READ | logs via `Log_Info` (103) — 94-105 |
| 6 | `Map_GetPathingMapBlockArray()` | `[size, dword…]`; `[0]` (single-element) when empty (122, log 119); `0` when `Sub1` is null (111) | MEMORY READ | 107-134 |
| 7 | `Map_GetPropsContext()` | pointer at `MapContext + 0x7C`; `0` when the context is 0 (141) | MEMORY READ | 139-144 |
| 8 | `Map_GetPropArray()` | `[size, ptr…]`; `[0]` when empty (156); `0` when props context is 0 (148) | MEMORY READ | stride `4` from `props + 0x194` — 146-167 |
| 9 | `Map_GetPropsByType()` | same shape; `[0]` when empty (179); `0` when context 0 (171) | MEMORY READ | from `props + 0x6C` — 169-190 |
| 10 | `Map_GetPropModels()` | `[size, ptr…]` where each entry is `$l_p_ArrayPtr + i*0x20` — the comment on 210 says **"Estimate structure size"**; `[0]` when empty (202); `0` when context 0 (194) | MEMORY READ | from `props + 0xA4` — 192-214 |
| 11 | `Map_GetPropInfo($a_p_PropPtr, $a_s_Info = "")` | `X`/`Y`/`Z` floats, `PropType` dword, `ModelInfo` ptr, `h0034` → 5-element ptr array; `0` when ptr 0 or info empty (220) or unknown (243) | MEMORY READ | 219-244 |
| 12 | `Map_GetPropModelFileId($a_p_PropPtr)` | computed file ID; **`0`** when prop ptr 0 (247), sub-deets ptr 0 (251), file-hash ptr 0 (255), or the hash shape does not match (271) | MEMORY READ | four `word` reads then arithmetic — 246-272 |
| 13 | `Map_QueryPropIntersectionMulti($a_a_Rays, $a_i_Timeout = 250)` | success → `[n][4]` of `Hit, Distance, PropIndex, PropPtr` (318-338); **`0` with `SetError`**: 1 = arguments (279, 280, 283, 296), 2 = no props (287, 315), 3 = timeout (343) | **GAME-THREAD CALL** — mixed with MEMORY WRITE (309) and MEMORY READ (314, 317, 321-334); §7 **A5** | fills `$g_d_PropRay` (299-308), `Memory_Write($g_p_PropRayReady, PENDING)` (309), `Core_Enqueue($g_p_PropRay, 8 + n*28)` (310) → `CommandPropRay` (`Core.au3:526`) → `call QueryPropIntersect` (`Assembler:2508-2568`, call 2556) |
| 14 | `Map_QueryPropIntersection($a_f_X1, $a_f_Y1, $a_f_Z1, $a_f_X2, $a_f_Y2, $a_f_Z2, $a_i_Timeout = 250)` | `[4]` = `Hit, Distance, PropIndex, PropPtr`; propagates `@error` with `0` (352) | GAME-THREAD CALL | thin adaptor over #13 — 348-356 |
| 15 | `Map_IsLineClear(…same six floats…, $a_i_Timeout = 250)` | `Not $l_a_Result[0]`; `False` with `@error` propagated when the query fails (362) | GAME-THREAD CALL | via #14 — 360-365 |
| 16 | `Map_GetNearestTravelPortal($a_f_X, $a_f_Y, $a_f_OffsetDistance = 50)` | `[TargetX, TargetY, Z, 0]` 4-element array; **`0`** when `Map_GetPropArray` is not an array or is empty (370) and when no travel portal was found (410) | MEMORY READ | per-prop `Memory_Read` at `+0x20/0x24/0x28/0x38/0x3C/0x40` (386-403); filters with #18 |
| 17 | `Map_PointInPathingMap($aX, $aY, $aTrapezoidPtr, $aTrapezoidCount)` | `True` on the first containing trapezoid, else `False` (466) | MEMORY READ | loops #23/#24 — 437-467 |
| 18 | `Map_IsTravelPortal($a_p_PropPtr)` | `False` if ptr 0 (470); `True` for 10 listed model file IDs; `False` otherwise | MEMORY READ | via #12 — 469-489 |
| 19 | `Map_IsTeleporter($a_p_PropPtr)` | `True` only for `0xefd0`; `False` otherwise and for ptr 0 (492) | MEMORY READ | via #12 — 491-502 |
| 20 | `Map_GetSpawnPoints($a_i_SpawnType = 1)` | `[size, [X,Y,unk1,unk2]…]`; `[0]` when the spawn array key is not an array (514) or empty (522) | MEMORY READ | `"Spawns" & $a_i_SpawnType`, stride 16 — 507-541 |
| 21 | `Map_GetPathingMap($a_i_Index)` | `$l_p_ArrayPtr + $a_i_Index * 0x54`; `0` when the array is null (549, log 548) or `Index >= size` (555, log 554) | MEMORY READ | 545-562 |
| 22 | `Map_GetPathingMapInfo($a_i_Index, $a_s_Info = "")` | `ZPlane`, `TrapezoidCount`, `Trapezoids` ptr, `RootNode` ptr; `0` when #21 is 0 (566), when info is `""` (570, log 569), or unknown key (585) | MEMORY READ | 564-586 |
| 23 | `Map_GetTrapezoid($a_p_TrapezoidsPtr, $a_i_Index)` | `$a_p_TrapezoidsPtr + $a_i_Index * 0x30` — an address | **PURE COMPUTATION** | 588-591 |
| 24 | `Map_GetTrapezoidInfo($a_p_TrapezoidPtr, $a_s_Info = "")` | `ID` dword, `XTL/XTR/YT/XBL/XBR/YB` floats; `0` when ptr 0 (596, log 595) or info `""` (599) | MEMORY READ | 593-620 |
| 25 | `Map_GetExitPortalsCoords($a_i_FromMapID, $a_i_ToMapID)` | 2-element coord array, or **`False`** at 3223 (`Case Else`) and at 3229 (`If Not IsDeclared("l_ai_Coords")`) — both paths log two `Out()` lines first, and both index `$g_a2D_MapArray[$a_i_FromMapID][1]` | **PURE COMPUTATION** | lines 623-3233 are a pure `Switch` over ~2600 lines of hard-coded tables; **no `Memory_Read`, `Core_*` or `DllCall` anywhere in the range** (grep-verified) |
| 26 | `Map_GetConnectedMaps($a_i_MapID)` | `$l_a_Connected` (possibly `Local …[0]`, 3242); the `Case Else` at 3904 leaves it empty | **PURE COMPUTATION** | 3241-3909, a pure `Switch`; no game access in the range |
| 27 | `Map_FindMapPath($a_i_FromMapID, $a_i_ToMapID)` | same-map → `[FromMapID]` (3920-3921); found → reconstructed path array (3991); not found → empty `[0]` array (3971-3972) | **PURE COMPUTATION** | BFS over #26; fixed `$l_a_Visited[1000]`/`$l_a_Parent[1000]` (3926-3927) |
| 28 | `Map_FindNearestUnlockedOutpost($a_i_DestMapID, $a_i_FromMapID = 0, $a_f_XInMap = 0, $a_f_YInMap = 0)` | `$a_i_DestMapID` if it is itself an unlocked valid outpost (4007); nearest neighbour MapID (4094); **`0` with `SetError(1,0,0)`** when nothing found (4050) | MEMORY READ (+ pure BFS) | calls `Map_IsMapUnlocked` (4006, 4026) and `Map_IsOutpost` (4006, 4026, 4081) + `Map_GetConnectedMaps`/`Map_FindMapPath`/`Map_GetExitPortalsCoords` — 4004-4095 |
| 29 | `Map_GetPathWithPortalCoords($a_i_FromMapID, $a_i_ToMapID)` | `[len][5]` of `MapID, MapName, PortalX, PortalY, TravelHere` (`TravelHere` is always `0`, 4148); empty `[0][5]` when the path is empty (4109-4111) | **PURE COMPUTATION** | #27 + #25 + `$g_a2D_MapArray` (4123-4124) — 4106-4152 |
| 30 | `Map_GetPathToUnlockCity($a_i_CityID, $a_f_XInMap = 0, $a_f_YInMap = 0)` | `[OutpostID, PathWithCoords]`; `[CityID, empty]` when already unlocked (4167-4169); `[0, empty]` when no outpost (4175) or no path (4180) | MEMORY READ | `Map_IsMapUnlocked` (4167) + #28 + #29 — 4160-4186 |

**Counts:** MEMORY READ 22 · PURE COMPUTATION 5 · GAME-THREAD CALL 3.

**Note on the "pure" verdicts:** #25, #26, #27, #29 contain no client access at all, but #25 and #29
**do** depend on constants and on the host table `$g_a2D_MapArray` — pure, yet not self-contained.
`Out(...)` (3221-3222, 3227-3228) writes to the controller's own output, not to the client.

---

## 6. `GwAu3_Cmd_Ui.au3` — 40 functions

Classification column first, then the wrapper column the task asks for (§6.3).

| # | Function | Returns | Class | Own work or wrapper |
| --- | --- | --- | --- | --- |
| 1 | `Ui_Dialog($a_i_DialogID)` | `0` | GAME-THREAD CALL | **own work.** `$g_d_Dialog`, `Core_Enqueue($g_p_Dialog, 8)` — 4-7; `CommandDialog` (`Core.au3:493`) → `call Dialog` (`Assembler:2655-2659`, call 2657) |
| 2 | `Ui_AcceptQuest($a_i_QuestID)` | `0` | GAME-THREAD CALL | own work; builds the packed ID `'0x008' & Hex($a_i_QuestID,3) & '01'` (11) — 10-13 |
| 3 | `Ui_UpdateQuest($a_i_QuestID)` | `0` | GAME-THREAD CALL | own work; suffix `'04'` (17) — 16-19 |
| 4 | `Ui_AboutQuest($a_i_QuestID)` | `0` | GAME-THREAD CALL | own work; suffix `'03'` (23) — 22-25 |
| 5 | `Ui_RewardQuest($a_i_QuestID)` | `0` | GAME-THREAD CALL | own work; suffix `'07'` (29) — 28-31 |
| 6 | `Ui_Interact($a_i_InteractionID)` | `0` | GAME-THREAD CALL | own work. `Core_Enqueue($g_p_Interact, 8)` — 34-37 → `CommandInteract` (`Core.au3:494`) → `call Interact` (`Assembler:2661-2665`, call 2663) |
| 7 | `Ui_OpenChest($a_b_WithLockpick = True)` | `0` | GAME-THREAD CALL | own work; `2` with lockpick, `1` without (42/44) — 40-47, same `CommandInteract` |
| 8 | `Ui_ActivateReforgedMode()` | `0` | GAME-THREAD CALL | **thin wrapper → `Ui_Interact(1)`** (51; called from 4-7 / 34-37) |
| 9 | `Ui_DeactivateReforgedMode()` | `0` | GAME-THREAD CALL | **wrapper → `Ui_Interact(2)`** (56) |
| 10 | `Ui_ActivateDhuumsCovenant()` | `0` | GAME-THREAD CALL | **wrapper → `Ui_Interact(4)`** (61) |
| 11 | `Ui_DeactivateDhuumsCovenant()` | `0` | GAME-THREAD CALL | **wrapper → `Ui_Interact(5)`** (66) |
| 12 | `Ui_Xunlai()` | `0` | GAME-THREAD CALL | own work; message `$GC_I_UIMSG_OPEN_XUNLAI` (71) — 70-73 → `CommandUIMsg` (`Core.au3:512`) → `call UIMessage` (`Assembler:2645-2653`, call 2651) |
| 13 | `Ui_CloseDialog($a_i_DialogID)` | **`False` with `SetError(1,0,False)`** for any other ID (85); `True` (90) for `$GC_I_UIDIALOG_INVUPGRADE` (0x16) and `$GC_I_UIDIALOG_SALVAGE` (0x29) | GAME-THREAD CALL | own work; maps the ID to `$GC_I_UIMSG_CLOSE_DIALOG_{INVUPGRADE,SALVAGE}` (80-86) — 77-91, `CommandUIMsg` |
| 14 | `Ui_CommandHero($a_i_HeroNumber, $a_f_X, $a_f_Y)` | `0` | GAME-THREAD CALL (+ MEMORY READ) | own work; reads `Party_GetMyPartyHeroInfo(…,"AgentID")` (95) — 94-100 → `CommandFlagHero` (`Core.au3:502`) → `call FlagHero` (`Assembler:2709-2717`, call 2715) |
| 15 | `Ui_CancelHero($a_i_HeroNumber)` | `0` | GAME-THREAD CALL (+ READ) | own work; uses `$GC_I_UIMSG_HERO_FLAG` (= `0x7F800000`, `Const_Ui.au3:8`) as both coordinates (105-106) — 103-109 |
| 16 | `Ui_CommandAll($a_f_X, $a_f_Y)` | `0` | GAME-THREAD CALL | own work — 112-117 → `CommandFlagAll` (`Core.au3:503`) → `call FlagAll` (`Assembler:2719-2725`, call 2723) |
| 17 | `Ui_CancelAll()` | `0` | GAME-THREAD CALL | own work; coordinates = `$GC_I_UIMSG_HERO_FLAG` (121-122) — 120-125 |
| 18 | `Ui_SetHeroBehavior($a_i_HeroNumber, $a_i_Behavior = 1)` | `0` | GAME-THREAD CALL (+ READ) | own work; comment 127 names `0=Fight,1=Guard,2=Avoid` — 128-132 → `CommandSetHeroBehavior` (`Core.au3:504`) → `call SetHeroBehavior` (`Assembler:2727-2732`, call 2730) |
| 19 | `Ui_DropHeroBundle($a_i_HeroNumber)` | `0` | GAME-THREAD CALL (+ READ) | own work — 135-138 → `CommandDropHeroBundle` (`Core.au3:505`) → `call DropHeroBundle` (`Assembler:2734-2738`, call 2736) |
| 20 | `Ui_LockHeroTarget($a_i_HeroNumber, $a_i_TargetAgentID = 0)` | `0` | GAME-THREAD CALL (+ READ) | own work; runs the target through `Agent_ConvertID` (143) — 141-145 → `CommandLockHeroTarget` (`Core.au3:506`) → `call LockHeroTarget` (`Assembler:2740-2745`, call 2743) |
| 21 | `Ui_ToggleHeroSkillState($a_i_HeroNumber, $a_i_Skillslot)` | `0` | GAME-THREAD CALL (+ READ) | own work; sends `$a_i_Skillslot - 1` (150) — 148-152 → `CommandToggleHeroSkillState` (`Core.au3:507`) → `call ToggleHeroSkillState` (`Assembler:2747-2752`, call 2750) |
| 22 | `Ui_EnableHeroSkill($a_i_HeroNumber, $a_i_SkillSlot)` | **no `Return`** → `0` on both paths | GAME-THREAD CALL (+ READ) | **hybrid: calls `Party_GetIsHeroSkillDisabled`** (`Cmd_Party.au3:70-72`) **and `Ui_ToggleHeroSkillState` (#21)** — 155-157 |
| 23 | `Ui_DisableHeroSkill($a_i_HeroNumber, $a_i_SkillSlot)` | `True` (162) | GAME-THREAD CALL (+ READ) | **hybrid: same two calls** — 160-163 |
| 24 | `Ui_AddNPC($a_i_AgentID)` | `0` | GAME-THREAD CALL | own work — 166-169 → `CommandAddNPC` (`Core.au3:495`) → `call AddNPC` (`Assembler:2667-2671`, call 2669) |
| 25 | `Ui_AddHero($a_i_HeroID)` | `0` | GAME-THREAD CALL | own work — 172-175 → `CommandAddHero` (`Core.au3:496`) → `call AddHero` (`Assembler:2673-2677`, call 2675) |
| 26 | `Ui_KickNPC($a_i_AgentID)` | `0` | GAME-THREAD CALL | own work — 178-181 → `CommandKickNPC` (`Core.au3:497`) → `call KickNPC` (`Assembler:2679-2683`, call 2681) |
| 27 | `Ui_KickHero($a_i_HeroID)` | `0` | GAME-THREAD CALL | own work — 184-187 → `CommandKickHero` (`Core.au3:498`) → `call KickHero` (`Assembler:2685-2689`, call 2687) |
| 28 | `Ui_KickAllHeroes()` | `0` | GAME-THREAD CALL | own work; hard-codes `0x28` (191) — 190-193 |
| 29 | `Ui_LeaveGroup($a_b_KickAllHeroes = True)` | `0` | GAME-THREAD CALL | own work **plus a call to `Ui_KickAllHeroes` (#28) after the enqueue** (199) — 196-200; note the flag does not affect the `0x28` it enqueues at 197 |
| 30 | `Ui_SetDifficulty($a_b_HardMode = False)` | `0` | GAME-THREAD CALL | own work; comment 202: `False = NM, True = HM` — 203-206 → `CommandSetDifficulty` (`Core.au3:500`) → `call SetDifficulty` (`Assembler:2697-2701`, call 2699) |
| 31 | `Ui_EnterChallenge($a_b_Foreign = False, $a_b_WaitMapIsLoaded = True)` | **no `Return`** → `0` | GAME-THREAD CALL (+ WRITE + READ) | own work; `Not $a_b_Foreign` (210), then `Map_InitMapIsLoaded()` (211) and `Map_WaitMapIsLoaded()` (213) → `CommandEnterMission` (`Core.au3:501`) → `call EnterMission` (`Assembler:2703-2707`, call 2705) |
| 32 | `Ui_MoveMap($a_i_MapID, $a_i_Region, $a_i_Language, $a_i_District)` | `0` | GAME-THREAD CALL | own work; message `$GC_I_UIMSG_TRAVEL` (218) — 217-224 → `CommandUIMsg` (`Core.au3:510`). **Parameter order differs from `Map_MoveMap`**: here it is `(MapID, Region, Language, District)` and the struct fields are 3=MapID, 4=Region, 5=Language, 6=District — whereas `Cmd_Map.au3:36` is `(MapID, Region, District, Language)` |
| 33 | `Ui_EquipItem($a_v_Item, $a_v_Agent = Agent_GetAgentPtr())` | `0` | GAME-THREAD CALL | own work; `Item_ItemID($a_v_Item)` (229), `Agent_ConvertID($a_v_Agent)` (230), message `$GC_I_UIMSG_EQUIP_ITEM` (228) — 227-232 → `CommandUIMsg` (`Core.au3:511`). The **default expression itself reads client memory** (`Agent_GetAgentPtr()`) |
| 34 | `Ui_EnableRendering()` | `1` if already enabled (236); otherwise **no `Return`** → `0` | MEMORY WRITE | `Memory_Write($g_b_DisableRendering, 0)` (237) — 235-238; `$g_b_DisableRendering` is an **injected-block slot** (§0) |
| 35 | `Ui_DisableRendering()` | `1` if already disabled (242); otherwise `0` | MEMORY WRITE | `Memory_Write($g_b_DisableRendering, 1)` (243) — 241-244 |
| 36 | `Ui_ToggleRendering()` | **no `Return`** → `0` | MEMORY WRITE — **mixed with a host window operation**, §7 **A6** | via #34/#35 (249/252) + `WinSetState(Scanner_GetWindowHandle(), "", @SW_SHOW/@SW_HIDE)` (250/253) + `Memory_Clear()` (254) — 247-256 |
| 37 | `Ui_PurgeHook($a_i_Time = 10000)` | `1` if rendering is already enabled (261); otherwise `0` | MEMORY WRITE (+ a sleep) | `Ui_ToggleRendering()` → `Sleep($a_i_Time)` → `Ui_ToggleRendering()` — 260-265 |
| 38 | `Ui_ToggleRendering_()` | **no `Return`** → `0` | MEMORY WRITE | #34/#35 + `Memory_Clear()` (273); **no `WinSetState`** — the comment at 267 says the GW window stays hidden — 268-275 |
| 39 | `Ui_PurgeHook_($a_i_Time = 10000)` | `1` if rendering is already enabled (279); otherwise `0` | MEMORY WRITE (+ sleep) | `Ui_ToggleRendering_()` → `Sleep` → `Ui_ToggleRendering_()` — 278-283 |
| 40 | `Ui_ActiveQuest($a_i_QuestID)` | `0` | GAME-THREAD CALL | own work — 285-288 → `CommandActiveQuest` (`Core.au3:508`) → `call ActiveQuest` (`Assembler:2754-2758`, call 2756) |

**Counts:** GAME-THREAD CALL 33 · MEMORY WRITE 7 · PACKET SEND 0 · MEMORY READ 0.

### 6.3 Wrapper summary for `Ui_*` (the task's question 4)

**Only six `Ui_*` functions are thin wrappers.** Everything else does its own work.

| `Ui_*` function | wrapper? | calls | lines |
| --- | --- | --- | --- |
| `Ui_ActivateReforgedMode` | **yes — one line** | `Ui_Interact(1)` | 50-52 → 34-37 |
| `Ui_DeactivateReforgedMode` | **yes — one line** | `Ui_Interact(2)` | 55-57 → 34-37 |
| `Ui_ActivateDhuumsCovenant` | **yes — one line** | `Ui_Interact(4)` | 60-62 → 34-37 |
| `Ui_DeactivateDhuumsCovenant` | **yes — one line** | `Ui_Interact(5)` | 65-67 → 34-37 |
| `Ui_EnableHeroSkill` | **hybrid** | guard `Party_GetIsHeroSkillDisabled` + action `Ui_ToggleHeroSkillState` | 155-157 → 70-72, 148-152 |
| `Ui_DisableHeroSkill` | **hybrid** | same pair, `Return True` | 160-163 → 70-72, 148-152 |
| all other 34 functions | **no** | own struct + own `Core_Enqueue`/`Memory_Write` | — |

**None of the 40 `Ui_*` functions is a wrapper over a `Party_*`, `Map_*` or `Item_*` command.**
The only cross-module relationships are the six above plus two read/delegate calls that are not
wrappers in the "duplicate a command" sense: `Ui_EnterChallenge` calls `Map_InitMapIsLoaded` (211) and
`Map_WaitMapIsLoaded` (213), and `Ui_ToggleRendering`/`Ui_PurgeHook`/`Ui_ToggleRendering_`/
`Ui_PurgeHook_` call the sibling `Ui_*` rendering functions plus `Ui_GetRenderEnabled`/
`Ui_GetRenderDisabled` (from `Data_Ui`). See §8 for the duplication result.

---

## 7. `GwAu3_Data_Ui.au3` — 2 functions

| # | Function | Returns | Class | Mechanism / helper — cited lines |
| --- | --- | --- | --- | --- |
| 1 | `Ui_GetRenderDisabled()` | boolean = `Memory_Read($g_b_DisableRendering) = 1` | MEMORY READ | 4-6 |
| 2 | `Ui_GetRenderEnabled()` | boolean = `Memory_Read($g_b_DisableRendering) = 0` | MEMORY READ | 9-11 |

**Counts:** MEMORY READ 2.

Both read the **injected block's own `DisableRendering` slot** (`Core.au3:443`,
`Assembler_CreateData` `Assembler:1920`), not a field of the client's own structures. The 4-byte
injected slot is the entire state: there is no client-side rendering flag involved.

---

## 8. `GwAu3_Cmd_Trade.au3` — 18 functions, including the `Trade_X` / `Trade_X_` pairs

| # | Function | Returns | Class | Mechanism / helper — cited lines |
| --- | --- | --- | --- | --- |
| 1 | `Trade_InitiateTrade_($a_v_Agent)` | `0` | PACKET SEND | `Core_SendPacket(0x08, …TRADE_INITIATE, Agent_ConvertID($a_v_Agent))` — 4-6 |
| 2 | `Trade_AcceptTrade_()` | `0` | PACKET SEND | `Core_SendPacket(0x4, …TRADE_ACCEPT)` — 9-11 |
| 3 | `Trade_SubmitOffer_($a_i_Gold = 0)` | `0` | PACKET SEND | `Core_SendPacket(0x8, …TRADE_SUBMIT_OFFER, $a_i_Gold)` — 14-16 |
| 4 | `Trade_CancelTrade_()` | `0` | PACKET SEND | `Core_SendPacket(0x4, …TRADE_CANCEL)` — 19-21 |
| 5 | `Trade_ChangeOffer_()` | `0` | PACKET SEND | `Core_SendPacket(0x4, …TRADE_CHANGE_OFFER)` — 24-26 |
| 6 | `Trade_OfferItem_($a_i_ItemID, $a_i_Quantity = 1)` | `0` | PACKET SEND | `Core_SendPacket(0xC, …TRADE_ADD_ITEM, $a_i_ItemID, $a_i_Quantity)` — 29-31 |
| 7 | `Trade_InitTradePartner()` | **no `Return`** → `0` | MEMORY WRITE | `Memory_Write($g_p_TradePartner, 0)` (35) — 34-36; injected slot (§0) |
| 8 | `Trade_GetTradePartner()` | the stored PlayerNumber, or `0` | MEMORY READ (+ MEMORY WRITE) — §7 **A7** | reads `$g_p_TradePartner` (40); if non-zero **clears it** (42) and returns it (43); else `0` (45) — 39-46. The value is written by the `TradePartnerProc` detour (`Assembler:2078-2085`) |
| 9 | `Trade_InitiateTrade($a_v_Agent)` | **no `Return`** → `0` | GAME-THREAD CALL | `$g_d_TradeInitiate` = `$GC_I_UIMSG_INITIATE_TRADE` (50), `Core_Enqueue($g_p_TradeInitiate, 12)` (52) — 49-53 → `CommandTradeInitiate` (`Core.au3:487`) → `call UIMessage` (`Assembler:2613-2620`, call 2618) |
| 10 | `Trade_CancelTrade()` | `Trade_WaitIdle` false → **`False` with `SetError(3,0,False)`** (57); else the session result, with `@error` propagated from `Trade_CallSession` (59) | GAME-THREAD CALL | `Trade_CallSession('TradeSessAbort')` (58) → `CommandTradeSession` (`Core.au3:530`) → `call ebx` on the scanner-resolved native (`Assembler:2573-2611`, call 2603) — 56-60 |
| 11 | `Trade_AcceptTrade()` | as #10 | GAME-THREAD CALL | `Trade_CallSession('TradeSessConfirm')` (66); comment 63 records that the local window must be open — 64-68 |
| 12 | `Trade_SubmitOffer($a_i_Gold = 0)` | as #10 | GAME-THREAD CALL | `Trade_CallSession('TradeSessSubmit', $a_i_Gold)` (73) — 71-75 |
| 13 | `Trade_OfferItem($a_v_Item, $a_i_Qty = 1)` | as #10 | GAME-THREAD CALL | `Trade_CallSession('TradeSessOfferItem', Item_ItemID($a_v_Item), $a_i_Qty)` (80) — 78-82 |
| 14 | `Trade_CallSession($a_s_Native, $a_i_Arg1 = 0, $a_i_Arg2 = 0, $a_i_Timeout = 250)` | the native's non-zero return as boolean (106); **`False` with `SetError`**: 1 = scanner unresolved (89), 2 = no trade context — either null ptr (90) or the in-client skip (105), **4 = no live trade session** (94), 3 = timeout (109) | **GAME-THREAD CALL** (+ MEMORY WRITE 99, + MEMORY READ 104, 106) | `Memory_GetValue($a_s_Native)` (88) resolves the native **by name**, fills `$g_d_TradeSession` (96-98), `Memory_Write($g_p_TradeSessReady, PENDING)` (99), `Core_Enqueue($g_p_TradeSession, 16)` (100), polls the flag (103-108) → `CommandTradeSession` → `call ebx` (`Assembler:2573-2611`, call 2603). The client resolves the context itself (comment 2571) |
| 15 | `Trade_WaitIdle($a_i_Timeout = 3000)` | `True` when `Trade_GetTradeInfo("IsBusy")` is false (116); `False` on timeout (119) | MEMORY READ (+ sleeps) | polls `Trade_GetTradeInfo` → `Memory_Read($l_p_Ptr + 0x4)` (`Data_Trade.au3:50`) — 113-120 |
| 16 | `Trade_RevokeItem($a_v_Item)` | as #10 | GAME-THREAD CALL | `Trade_CallSession('TradeSessRevokeItem', Item_ItemID($a_v_Item))` (125) — 123-127 |
| 17 | `Trade_RevokeOffer()` | as #10 | GAME-THREAD CALL | `Trade_CallSession('TradeSessRevokeSubmit')` (132) — 130-134 |
| 18 | `Trade_RevokeAccept()` | as #10 | GAME-THREAD CALL | `Trade_CallSession('TradeSessRevokeConfirm')` (139) — 137-141 |

**Counts:** GAME-THREAD CALL 9 · PACKET SEND 6 · MEMORY READ 2 · MEMORY WRITE 1.

### 8.1 The `Trade_X` / `Trade_X_` pairs — mechanism per spelling

Note the naming: the **trailing underscore names are the packet versions**; the plain names are the
newer native-call versions. They are not aliases and they are not interchangeable.

| action | `Trade_X_` (packet) | mechanism | `Trade_X` (native) | mechanism | same params? |
| --- | --- | --- | --- | --- | --- |
| initiate | `Trade_InitiateTrade_($a_v_Agent)` — line 4, `Core_SendPacket` line 5 | PACKET SEND | `Trade_InitiateTrade($a_v_Agent)` — line 49, `Core_Enqueue($g_p_TradeInitiate, 12)` line 52 | GAME-THREAD CALL (`call UIMessage`, `Assembler:2618`) | yes (both take the agent) |
| accept | `Trade_AcceptTrade_()` — line 9, `Core_SendPacket` line 10 | PACKET SEND | `Trade_AcceptTrade()` — line 64, `Trade_CallSession('TradeSessConfirm')` line 66 | GAME-THREAD CALL | yes (no args) |
| submit offer | `Trade_SubmitOffer_($a_i_Gold = 0)` — line 14, `Core_SendPacket` line 15 | PACKET SEND | `Trade_SubmitOffer($a_i_Gold = 0)` — line 71, `Trade_CallSession('TradeSessSubmit', $a_i_Gold)` line 73 | GAME-THREAD CALL | yes |
| cancel | `Trade_CancelTrade_()` — line 19, `Core_SendPacket` line 20 | PACKET SEND | `Trade_CancelTrade()` — line 56, `Trade_CallSession('TradeSessAbort')` line 58 | GAME-THREAD CALL | yes |
| offer/change item | `Trade_OfferItem_($a_i_ItemID, $a_i_Quantity = 1)` — line 29, `Core_SendPacket` line 30 | PACKET SEND, **takes an ID** | `Trade_OfferItem($a_v_Item, $a_i_Qty = 1)` — line 78, `Trade_CallSession('TradeSessOfferItem', Item_ItemID($a_v_Item), $a_i_Qty)` line 80 | GAME-THREAD CALL, **takes an item and converts it** | **no** — different parameter kind and name |
| change offer | `Trade_ChangeOffer_()` — line 24, `Core_SendPacket` line 25 | PACKET SEND | **no counterpart.** The native path reaches the same state through `Trade_RevokeOffer()` (line 130, `TradeSessRevokeSubmit`) | — | — |
| revoke item / offer / accept | **no packet counterparts** | — | `Trade_RevokeItem` (123), `Trade_RevokeOffer` (130), `Trade_RevokeAccept` (137) | GAME-THREAD CALL | — |

So: **six packet versions, nine native versions, one action (`ChangeOffer`) that exists only as a
packet, and three actions (the revokes) that exist only as natives.** Three of the five spellings that
pair up also differ in return contract (the packet form returns `0`; the native form returns
`True`/`False` plus `@error`) — that is the most consequential difference for a caller.

**Natives invoked by name** (all through `Trade_CallSession`, line 87, resolved at line 88): only
`TradeSessAbort`, `TradeSessConfirm`, `TradeSessSubmit`, `TradeSessOfferItem`, `TradeSessRevokeItem`,
`TradeSessRevokeSubmit`, `TradeSessRevokeConfirm` appear anywhere in the tree (grep-verified).

---

## 9. `GwAu3_Data_Trade.au3` — 6 functions

| # | Function | Returns | Class | Mechanism / helper — cited lines |
| --- | --- | --- | --- | --- |
| 1 | `Trade_GetTradePtr()` | pointer or `0` | MEMORY READ | `Memory_ReadPtr($g_p_BasePointer,[0,0x18,0x58],'ptr')` — 4-8 |
| 2 | `Trade_GetTradeInfo($a_s_Info = "")` | `State`/`Flags` int; `IsTradeClosed` (=0), `IsTradeInitiated` (=1), `IsPlayerTradeOffered` (=3), `IsPlayerTradeAccepted` (=7) booleans; `PlayerGold`/`PlayerItemsPtr`/`PlayerItemCount`; `PartnerGold`/`PartnerItemsPtr`/`PartnerItemCount`; `IsSubmitted`/`IsConfirmed` flag tests; `PendingOp`, `IsBusy` (≠0); `PartnerName` → `wchar[32]` or **`""` when the name ptr is 0** (53); **`0`** if the context ptr is null or info is `""` (12), and `0` for an unknown key (58) | MEMORY READ | 10-59 |
| 3 | `Trade_GetPlayerTradeItemsInfo($a_i_TradeSlot = 0, $a_s_Info = "")` | `ItemID`, `Quantity`, `ModelID` (via `Item_GetItemInfoByItemID`, 77); **`0`** when items ptr 0 or info empty (63), or when count is 0 or the slot is out of range (66), or unknown key (80) | MEMORY READ | stride `0x8` — 61-81 |
| 4 | `Trade_GetPartnerTradeItemsInfo($a_i_TradeSlot = 0, $a_s_Info = "")` | as #3 for the partner side; same three `0` paths (85, 88, 102) | MEMORY READ | 83-103 |
| 5 | `Trade_GetArrayPlayerTradeItems()` | `[count+1][2]` of `[ModelID, Quantity]`, or a **1-element `[0]`** when the count is 0 (109-110); the size is stamped in `[0][0]` (114); returns the partly-filled array if the items ptr is 0 (117) | MEMORY READ | `Item_GetItemInfoByPtr` on a `Memory_Read` (121) — 105-127 |
| 6 | `Trade_GetArrayPartnerTradeItems()` | as #5 for the partner side (134, 138, 141) | MEMORY READ | 129-151 |

**Counts:** MEMORY READ 6.

---

## 10. Classifications summary

Counts over all **165** functions in the nine in-scope files:

| classification | count | share |
| --- | --- | --- |
| MEMORY READ | **68** | 41.2% |
| GAME-THREAD CALL | **52** | 31.5% |
| PACKET SEND | **29** | 17.6% |
| MEMORY WRITE | **9** | 5.5% |
| PURE COMPUTATION | **7** | 4.2% |
| UI/INPUT SYNTHESIS | **0** | 0% |
| OTHER | **0** | 0% |
| **total** | **165** | 100% |

Per module:

| module | functions | MEMORY READ | GAME-THREAD CALL | PACKET SEND | MEMORY WRITE | PURE COMPUTATION |
| --- | --- | --- | --- | --- | --- | --- |
| `Cmd_Party` | 22 | 1 | 5 | 16 | 0 | 0 |
| `Data_Party` | 16 | 16 | 0 | 0 | 0 | 0 |
| `Cmd_Map` | 14 | 4 | 2 | 7 | 1 | 0 |
| `Data_Map` | 17 | 15 | 0 | 0 | 0 | 2 |
| `Data_MapContext` | 30 | 22 | 3 | 0 | 0 | 5 |
| `Cmd_Ui` | 40 | 0 | 33 | 0 | 7 | 0 |
| `Data_Ui` | 2 | 2 | 0 | 0 | 0 | 0 |
| `Cmd_Trade` | 18 | 2 | 9 | 6 | 1 | 0 |
| `Data_Trade` | 6 | 6 | 0 | 0 | 0 | 0 |
| **total** | **165** | **68** | **52** | **29** | **9** | **7** |

**Zero functions in scope use UI/INPUT SYNTHESIS as their mechanism.** No `ControlSend`,
`keybd_event`, `mouse_event`, or window-message click appears in any of the nine files (grep-verified);
the only host-window operation anywhere in scope is the `WinSetState` inside `Ui_ToggleRendering`
(line 250/253), which is a window *state* change, not synthesized input (see §11 **A6**).

**How the 29 PACKET SEND functions build their packet:** 27 call `Core_SendPacket` directly. The
other 2 — `Map_TravelTo` (`Cmd_Map.au3:85`) and `Map_RndTravel` (`Cmd_Map.au3:127`) — build theirs by
calling `Map_MoveMap`, which is itself one of the direct callers. The 29th kind of indirect packet
send, `Cinematic_SkipCinematic` (`Cmd_Cinematic.au3:4-6`), is reached from `Map_WaitMapLoading`
(line 137) but that function is classified MEMORY READ, so it is not counted among the 29.

---

## 11. What could not be classified cleanly, and the lines that make it ambiguous

The rule for this section: the primary label above names the mechanism that carries the function's
own state change (or, when there is none, its own read). These seven cases genuinely do more than one
thing, and each is listed with the lines rather than silently bucketed.

- **A1 — `Party_DisableHeroSkill` (Cmd_Party 80-83).** `Return True` at line 82 is **unconditional**:
  the guard at 81 decides whether a packet is sent, not what is returned. So a caller cannot tell
  "disabled" from "already disabled". `Party_EnableHeroSkill` (75-77) has no `Return` at all, so the
  twin functions disagree on their return contract. Classified PACKET SEND (conditional) — but on the
  no-op path this function touches the client not at all, which would be PURE COMPUTATION.

- **A2 — `Party_GetPetInfo` with `$a_s_Info = "PetName"` (Data_Party 287-290).** The function is
  MEMORY READ on 12 of its 13 keys. `"PetName"` calls `Utils_DecodeEncStringAsync`, which reads the
  encoded string (473), **writes** an injected guard flag (480) and **enqueues** a command (483)
  whose in-client handler calls `ValidateAsyncDecodeStr` (`Assembler:2847`). So one key of one
  function is MEMORY READ + MEMORY WRITE + GAME-THREAD CALL. `"PetNameEnc"` (283-286) uses
  `Utils_DecodeEncString`, which is a pure host-side decode over `Memory_Read` (448) — MEMORY READ
  only. The two keys look interchangeable and are not.

- **A3 — the five `Cmd_Map` wait/travel wrappers (42-44, 49-51, 64-66, 71-73, 84-86).** Each does
  `Map_InitMapIsLoaded()` (**MEMORY WRITE**), the send (**PACKET SEND** — or a delegated
  `Map_MoveMap`), and then `Map_WaitMapIsLoaded()` (**MEMORY READ** + another write). Classified
  PACKET SEND because the send is the action; the write and the reads are the surrounding ceremony.
  Also note the return contract: with `$a_WaitToLoad = False` these fall off the end and return `0`,
  which is **not** `False`-equivalent in a boolean test only by accident of AutoIt's truthiness.

- **A4 — `Map_WaitMapLoading` (Cmd_Map 131-156).** A polling loop over eight memory reads
  (142-149) that **also sends a packet** when `Game_GetGameInfo("IsCinematic")` is true, through
  `Cinematic_SkipCinematic()` (137) → `Core_SendPacket(0x4, $GC_I_HEADER_CINEMATIC_SKIP)`
  (`Cmd_Cinematic.au3:4-6`). Classified MEMORY READ (the loop is the function) with the conditional
  PACKET SEND called out. `Cinematic_SkipCinematic` is also the one in-scope packet send reached
  indirectly rather than written inline.

- **A5 — `Map_QueryPropIntersectionMulti` (MapContext 278-344).** MEMORY WRITE into the guard flag
  (309), `Core_Enqueue` (310), then MEMORY READ of the flag and of the result block (314, 321-334).
  Classified GAME-THREAD CALL because the payload is a native call (`call QueryPropIntersect`,
  `Assembler:2556`). It is the only function in the whole inventory that is *all three* of write,
  enqueue-and-call, and read **in its own body**, and the only one with a 3-state guard
  (`PENDING/DONE/SKIPPED`). `Map_QueryPropIntersection` (348-356) and `Map_IsLineClear` (360-365) are
  pure adaptors over it and inherit the label; neither touches the client itself.

- **A6 — `Ui_ToggleRendering` (Cmd_Ui 247-256).** MEMORY WRITE of the rendering flag (249/252) plus
  `WinSetState(Scanner_GetWindowHandle(), "", @SW_SHOW/@SW_HIDE)` (250/253) plus `Memory_Clear()`
  (254) — which is `SetProcessWorkingSetSize(-1,-1)`, a host-side working-set trim on the *client's*
  handle (`Core_Memory.au3:98-100`), not a memory write to a game address. `WinSetState` fits no
  bucket in the given taxonomy: it is neither memory access nor synthesized input. Classified
  MEMORY WRITE as the dominant mechanism, flagged here. `Ui_ToggleRendering_` (268-275) is the same
  function **without** the `WinSetState` — the underscore variant differs by exactly that plus the
  absence of it, and the header comments at 246 and 267 say so.

- **A7 — `Trade_GetTradePartner` (Cmd_Trade 39-46).** A read at 40 followed by an unconditional
  clear at 42 when the value is non-zero. It is a consume-once read: **two calls never return the
  same value twice**, and the second returns `0`. Classified MEMORY READ with the WRITE side effect
  named, because classification by "what the caller gets" would call it OTHER. This is also the only
  read-write pair in scope whose write is not a flag reset for the function's own use but the
  destruction of the value being returned.

- **A8 — return values of everything built on `Core_SendPacket` / `Core_Enqueue`, and the 27
  functions with no `Return` statement.** `Core_SendPacket` (`Core.au3:575-589`) and `Core_Enqueue`
  (`559-566`) have no `Return`, so `Return Core_SendPacket(...)` yields AutoIt's default for a
  valueless function. I report that as `0` **inferred from the language, not observed** — AutoIt was
  not executed here, and the report does not claim the packet's outcome is reported. This affects
  all 16 `Cmd_Party` packet functions, all 6 `Trade_*_` packet functions, 5 of the 7 `Cmd_Map`
  packet functions, and every `Core_Enqueue`-only function (`Party_AddPlayer`/`KickPlayer`/
  `KickInvitedPlayer`/`RejectInvitation`/`AcceptInvitation`, `Map_Move`/`Map_MoveLayer`,
  `Trade_InitiateTrade`, all 20 enqueue-only `Ui_*` struct functions, `Ui_SetDifficulty`,
  `Ui_EnterChallenge`, `Ui_LeaveGroup`, `Ui_KickAllHeroes`, `Ui_AddNPC`/`AddHero`/`KickNPC`/`KickHero`,
  `Ui_Dialog`/`Interact`/`Xunlai`/`ActiveQuest`, `Ui_CommandHero`/`CancelHero`/`CommandAll`/
  `CancelAll`/`SetHeroBehavior`/`DropHeroBundle`/`LockHeroTarget`/`ToggleHeroSkillState`,
  `Ui_CloseDialog` excepted — it returns `True`/`False` explicitly). A caller that treats these as
  success indicators is reading a constant.

- **A9 — the enqueue length vs the struct length, in `Ui_EquipItem`.** `$g_d_EquipItem` is declared
  `'ptr;dword;dword'` = 12 bytes (`Const_Core.au3:195`) but `Core_Enqueue($g_p_EquipItem, 16)` sends
  16 (`Cmd_Ui.au3:231`), so 4 bytes beyond the host struct are copied into the client queue. Recorded
  as an observation of what the code does. Of the 27 host-struct/enqueue-size pairs in `Cmd_Ui`,
  `Cmd_Party` and `Cmd_Trade` (`$g_d_EquipItem` counted once), this is the single mismatch: every
  other pair is equal — e.g. `$g_d_Move` `'ptr;float;float;dword'` = 16 against `Core_Enqueue(…, 16)`
  (`Const_Core.au3:133`, `Cmd_Map.au3:19`), `$g_d_TradeInitiate` `'ptr;dword;dword'` = 12 against 12
  (`Const_Core.au3:141`, `Cmd_Trade.au3:52`), `$g_d_TradeSession` `'ptr;ptr;dword;dword'` = 16
  against 16 (`Const_Core.au3:249`, `Cmd_Trade.au3:100`). A related shape observation, no verdict
  attached: `Ui_Xunlai` (70-73) and `Ui_CloseDialog` (88-89) enqueue an 8-byte `'ptr;dword'` struct,
  while their in-client handler `CommandUIMsg` passes `[eax+8]` as the payload pointer
  (`Assembler:2647-2650`) — i.e. the pointer handed to `UIMessage` is the byte after the copied
  struct rather than a field written by the caller.

- **A10 — the `GwAu3_modules_surface.csv` listing is incomplete for `Cmd_Party`.** It carries 20 rows
  for `GwAu3_Cmd_Party.au3`; the file has 22 `Func` definitions. `Party_LockHeroTarget` (line 55) and
  `Party_SetHeroAggression` (line 60) are absent from the CSV. Every other in-scope file matches its
  CSV count exactly (`Cmd_Map` 14, `Data_Map` 17, `Data_MapContext` 30, `Cmd_Ui` 40, `Data_Ui` 2,
  `Data_Party` 16, `Cmd_Trade` 18, `Data_Trade` 6). The CSV therefore cannot be used as the surface
  of record for this module; the source can.

---

## 12. The `Ui_*` duplication finding

**Result: `Cmd_Ui` is not a wrapper layer over `Party_*`/`Map_*`/`Item_*`. It is a second, parallel
implementation of the same 40 actions through a different mechanism.** The duplication is real and
function-for-function, but it is duplicated *work*, not duplicated *calls* — only 6 of the 40
functions call another GwAu3 function at all (§6.3), and none of those 6 calls a `Party_*`/`Map_*`
command.

The mechanism split is the substance of the finding:

| concern | `Party_*` / `Map_*` route | `Ui_*` route |
| --- | --- | --- |
| how the client is reached | `Core_SendPacket` → client's own packet sender (`call PacketSend`, `Assembler:2095`) | `Core_Enqueue` → a distinct native per action (`call FlagHero`, `call UIMessage`, `call AddHero`, …) |
| who validates the action | the server (a malformed or premature packet is refused remotely) | the client (the native runs locally and can refuse or assert) |
| what the caller learns | `0` — nothing (§11 **A8**) | `0` — nothing, except `Ui_CloseDialog` (`False` + `@error` 1) |
| liveness requirement | none beyond a live connection | a loaded map/UI (the natives read the client's own UI state) |

The action-for-action overlap, with both citations:

| action | packet spelling | native/UI spelling | note |
| --- | --- | --- | --- |
| add hero | `Party_AddHero` Cmd_Party 4-6 | `Ui_AddHero` Cmd_Ui 172-175 | packet takes a **HeroID**, UI takes a **HeroID** (same) |
| kick hero | `Party_KickHero` 9-11 | `Ui_KickHero` 184-187 | same |
| kick all heroes | `Party_KickAllHeroes` 14-16 (payload `0x28`) | `Ui_KickAllHeroes` 190-193 (payload `0x28`) | identical payload, different transport |
| add NPC/henchman | `Party_AddNpc` 19-21 | `Ui_AddNPC` 166-169 | packet uses `$GC_I_HEADER_PARTY_INVITE_NPC`, UI calls the client's `AddNPC` |
| kick NPC/henchman | `Party_KickNpc` 24-26 | `Ui_KickNPC` 178-181 | — |
| party tick | `Party_Tick` 29-31 | **no counterpart** | — |
| flag one hero | `Party_CommandHero` 45-47 | `Ui_CommandHero` 94-100 | both read the AgentID first |
| clear one hero's flag | `Party_CancelHero` 34-37 | `Ui_CancelHero` 103-109 | packet cancels by sending the two `0x7F800000` sentinels; UI sends `$GC_I_UIMSG_HERO_FLAG`, which **is** `0x7F800000` (`Const_Ui.au3:8`) |
| flag all | `Party_CommandAll` 50-52 | `Ui_CommandAll` 112-117 | — |
| clear all flags | `Party_CancelAll` 40-42 | `Ui_CancelAll` 120-125 | — |
| hero aggression | `Party_SetHeroAggression` 60-62 (comment `0=Fight,1=Guard,2=Avoid`) | `Ui_SetHeroBehavior` 128-132 (same comment, **default `= 1`**) | same values; the UI form defaults to Guard, the packet form has no default |
| lock hero target | `Party_LockHeroTarget` 55-57 (default `0`) | `Ui_LockHeroTarget` 141-145 (default `0`) | the UI form additionally runs the target through `Agent_ConvertID` (143) |
| toggle hero skill | `Party_ToggleHeroSkillState` 65-67 | `Ui_ToggleHeroSkillState` 148-152 | both send `$a_i_SkillSlot - 1` |
| enable hero skill | `Party_EnableHeroSkill` 75-77 | `Ui_EnableHeroSkill` 155-157 | **both guard on `Party_GetIsHeroSkillDisabled`** — the only read the two routes share |
| disable hero skill | `Party_DisableHeroSkill` 80-83 (returns `True`) | `Ui_DisableHeroSkill` 160-163 (returns `True`) | same guard, same unconditional `True` |
| leave group | `Party_LeaveGroup` 86-89 (kick-all first, then leave) | `Ui_LeaveGroup` 196-200 (leave first, then kick-all) | **order is reversed** |
| add player | `Party_AddPlayer` 92-95 | **no counterpart** (`Ui_` has no player-add) | — |
| kick player | `Party_KickPlayer` 98-101 | **no counterpart** | — |
| kick invited player | `Party_KickInvitedPlayer` 104-107 | **no counterpart** | — |
| reject invitation | `Party_RejectInvitation` 110-113 | **no counterpart** | — |
| accept invitation | `Party_AcceptInvitation` 116-119 | **no counterpart** | — |
| map travel | `Map_MoveMap` 36-38 (`(MapID, Region, District, Language)`) | `Ui_MoveMap` 217-224 (`(MapID, Region, Language, District)`) | **same 4 values, two different orders** — both spellings are live and neither defers to the other |
| enter mission | `Map_EnterChallenge` 48-52 (packet, arg `1`) | `Ui_EnterChallenge` 209-214 (native `EnterMission`, arg `Not $a_b_Foreign`) | different argument semantics: the packet sends `1`; the native sends a foreign boolean and then waits |
| item equip | `Item_*` (out of scope) | `Ui_EquipItem` 227-232 | calls `Item_ItemID` and `Agent_ConvertID`, i.e. it *consumes* `Item_*` rather than duplicating it |
| open chest / interact | `Other_*`/`Agent_Interact` (out of scope) | `Ui_Interact` 34-37, `Ui_OpenChest` 40-47 | no in-scope packet twin |
| quest dialogs | `Quest_*` (out of scope) | `Ui_Dialog`, `Ui_AcceptQuest`, `Ui_UpdateQuest`, `Ui_AboutQuest`, `Ui_RewardQuest`, `Ui_ActiveQuest` | the `Ui_*` dialogs pack suffixes `'01'/'04'/'03'/'07'` onto `0x008…` in AutoIt (11, 17, 23, 29) |
| rendering | **no `Party_*`/`Map_*` twin** | `Ui_EnableRendering`/`DisableRendering`/`ToggleRendering`/`ToggleRendering_`/`PurgeHook`/`PurgeHook_` | these 6 are the only `Ui_*` functions whose subject is not an in-game action at all: they write one injected 4-byte slot |

**What the duplication is not.** It is not a deprecation: there is no marker anywhere in the nine
files saying either spelling supersedes the other, and the `Party_*` and `Ui_*` sets are both present,
both exported, and in several cases (`Ui_CommandHero`, `Ui_SetHeroBehavior`, `Ui_EnterChallenge`)
carry defaults or argument conversions the packet twin does not. It is also not a single shared
dispatcher with two front doors: the packet route and the native route hand the client **different
payloads** (`Map`/`Ui_MoveMap` above; `0x28`-with-a-lead-UIMessage vs `0x28`-as-a-direct-payload in
`Ui_LeaveGroup` vs `Party_KickAllHeroes`) and the client resolves the target differently in each.

**Practical consequence for a port:** the two routes are not interchangeable, and neither is a
superset. A faithful port needs both surfaces as they stand, and the choice between them is a
per-action property of the client (what the native asserts on vs what the server accepts), not a
preference the port may resolve by picking the "cleaner" one.

---

## 13. Method and limits

- **Exhaustive by enumeration, not by sampling:** every file's `Func` count was taken from the source
  and every function body was read. `GwAu3_Data_MapContext.au3` was read in full except lines
  710-3204 and 3285-3879, which are two hard-coded `Switch` tables (`Map_GetExitPortalsCoords` and
  `Map_GetConnectedMaps`); those ranges were **grep-verified to contain no `Memory_Read`,
  `Memory_Write`, `Core_*`, `DllCall`, `ControlSend` or `SendPacket`** call, which is what the PURE
  COMPUTATION verdict rests on. Everything between them (function heads, all `Return`/`SetError`
  paths, the BFS and path-building tail) was read directly.
- The helper layer was read to ground the classifications, not assumed:
  `GwAu3_Core.au3:440-445, 450-451, 462-537, 546-593`; `GwAu3_Core_Memory.au3:1-70, 96-125`;
  `GwAu3_Core_Assembler.au3:1900-1947, 1975-2030, 2078-2132, 2497-2611, 2613-2659, 2661-2791,
  2793-2850`; `GwAu3_Core_Utils.au3:1-60, 435-514`; `GwAu3_Const_Core.au3:18-40, 130-250`;
  `GwAu3_Const_Ui.au3:3-14`; `GwAu3_Const_Game.au3:7`; `GwAu3_Const_Map.au3:1802`;
  `GwAu3_Data_Skill.au3:210-247`; `GwAu3_Data_Other.au3:1-6`; `GwAu3_Data_Agent.au3:1-16`;
  `GwAu3_Cmd_Cinematic.au3:1-6`.
- **Not verified:** nothing in this report was executed, and no live Guild Wars client was read or
  written. Every claim is `verified by source inspection`. The three `inferred` items — the AutoIt
  default return of a valueless function (§11 **A8**), and the two shape observations in **A9** — are
  marked as such at the point of use.
- **Not covered (out of scope by instruction):** `GwAu3_Cmd_Guild.au3` and `GwAu3_Data_Guild.au3`
  (which the CSV's `Ui` substring also matches), `Item_*`, `Agent_*`, `Skill_*`, `Quest_*` and the
  scanner/assembler internals beyond what the classifications above require.
