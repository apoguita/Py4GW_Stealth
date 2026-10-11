# GwAu3 public surface inventory — Account, Camera, Friend, Game, Guild, Other, PreGame, Quest, Title, World, Chat, Cinematic, Effect, Match

Scope: `external/GwAu3/API/Modules/Cmd/GwAu3_Cmd_<Module>.au3` and
`external/GwAu3/API/Modules/Data/GwAu3_Data_<Module>.au3` for the 14 modules named above.
Source read: the checked-out `.au3` files themselves, line by line (28 files; 7 of them are
`#include-once`-only stubs with no functions — listed in § Empty files). Nothing below is
inferred from the pre-extracted surface CSV; where the CSV and the source disagree, the source
is reported and the disagreement is noted (§ Notes on the surface CSV).

**Evidence class for every statement below: `verified` by source inspection only.** No live
client was used, and nothing here is a live observation.

Status: this is a reading of a third-party reference checkout, not a statement about this
project's own port. Per `AGENTS.md` the GwAu3 checkout is authority rank 5 (historical /
comparative behaviour), so everything here is a research lead to be revalidated independently.

## How the classification column was decided

Each function is given exactly **one** primary classification (that is what § Classifications
summary counts). Where a function also does something that falls in another category, the
extra category is named in the same cell and in § Mixed-behaviour functions.

| Class | Meaning used here |
| --- | --- |
| MEMORY READ | plain read of game memory: `Memory_Read` / `Memory_ReadPtr` / direct `ReadProcessMemory` |
| MEMORY WRITE | writes into game memory: `Memory_Write` / `Memory_WriteBinary` / direct `WriteProcessMemory` / `VirtualAllocEx` in the target |
| PACKET SEND | the effect reaches the game as a packet handed to the client's own `PacketSend` |
| GAME-THREAD CALL | a native game routine is invoked, from the client's own thread, through the injected queue (`Core_Enqueue` → the `MainStart` detour) |
| UI/INPUT SYNTHESIS | ControlSend / keybd_event / mouse / window messages |
| PURE COMPUTATION | no game access at call time (string work, arithmetic, `Sleep`) |
| OTHER | anything else, stated exactly |

### The four helper chains every classification cites

1. **Read chain.** `Memory_Read($addr, $type)` (`API/Core/GwAu3_Core_Memory.au3:33-37`) calls
   `ReadProcessMemory` at line 35 and returns `DllStructGetData` at line 36 **without checking
   the DllCall result** — a failed read is indistinguishable from a successful read of zeros.
   `Memory_ReadPtr` (`:39-60`) dereferences a pointer chain the same way and returns a 2-element
   array `[address, value]`, or `[0, 0]` (line 48-51) as soon as a link in the chain is 0.
2. **Write chain.** `Memory_Write` (`:27-31`, `WriteProcessMemory` at line 30) and
   `Memory_WriteBinary` (`:16-25`, `WriteProcessMemory` at line 24). Neither checks its result.
3. **Queue chain (this is the "game-thread call" mechanism).** `Core_Enqueue($p, $size)`
   (`API/Core/GwAu3_Core.au3:559-566`) writes `$size` bytes from the host struct at `$p` into the
   slot `256 * $g_i_QueueCounter + $g_p_QueueBase` of a queue **inside the client** — the slot's
   *first dword is a code address* — then advances/wraps `$g_i_QueueCounter` (`:561-565`).
   The client's main loop is detoured to the injected `MainProc`
   (`GwAu3_Core_Assembler.au3:1949-2030`; the detour is written at `:1905`), which each pass takes
   the current slot, treats its first dword as the target and does `jmp ebx` to it
   (`Assembler:1982-2009`). So the queued first dword is a routine that runs **on the game's own
   thread**. The slot data itself is `[command address][parameters...]`.
4. **Packet chain.** `Core_SendPacket($size, $header, ...)` (`GwAu3_Core.au3:575-589`) fills the host
   struct `$g_d_Packet` and enqueues it (`:588`); the queued routine is `CommandPacketSend`
   (`Assembler:2088-2099`), which calls the client's own `PacketSend` with `PacketLocation`.

> **Trap worth stating once: `Core_SendPacket` has no `Return` statement** (`GwAu3_Core.au3:575-589`),
> and neither does `Core_Enqueue` (`:559-566`). In AutoIt a function without `Return` evaluates to
> 0, so every `Return Core_SendPacket(...)` in the modules below returns **0**, never a success
> flag. All "Returns" cells say so explicitly.

## Account

| Function & signature (file:line) | Returns | Classification — evidence | State it depends on |
| --- | --- | --- | --- |
| `Account_GetAccountContextPtr()` — `Data/GwAu3_Data_Account.au3:4` | the `AccountContext` pointer (`ptr`), or 0 when the game-context chain is broken | **MEMORY READ.** `Return Game_GetGameInfo("AccountContext")` (`:5`), which is `Memory_Read($l_p_Ptr + 0x28, "ptr")` (`Data/GwAu3_Data_Game.au3:28-29`) reached through `Memory_ReadPtr($g_p_BasePointer, [0, 0x18])` (`Data_Game.au3:5-7`) → `ReadProcessMemory` (`GwAu3_Core_Memory.au3:35`) | `$g_p_BasePointer` (scanner result, set `GwAu3_Core.au3:159`); `$g_h_Kernel32` / `$g_h_GWProcess` from `Memory_Open` (`GwAu3_Core_Memory.au3:3-8`) |
| `Account_GetAccountInfo($a_s_Info = "")` — `Data/GwAu3_Data_Account.au3:8` | `0` if `$l_p_Ptr = 0` **or** `$a_s_Info = ""` (`:10`), and `0` for any unmatched `$a_s_Info` (`:30`); else per case: `"AccountName"` → `wchar[32]` read through the name pointer (`:14-15`), `"Wins"/"Losses"/"Rating"/"QualifierPoints"/"Rank"/"TournamentRewardPoints"` → `dword` at `+0x4/+0x8/+0xC/+0x10/+0x14/+0x18` (`:17-27`) | **MEMORY READ.** `World_GetWorldInfo("AccountInfo")` (`:9` → `Data/GwAu3_Data_World.au3:15-16`, a read at `WorldContext+0x0`) then `Memory_Read` per case | `$g_p_BasePointer` (two chains: game ctx → account ctx, world ctx → account info). Note the two entry points read *different* pointers: the context comes from the game context, the info from the world context |
| `Account_IsSkillUnlocked($a_i_SkillID)` — `Data/GwAu3_Data_Account.au3:33` | `False` if the account context is 0 (`:35`), `False` if the unlocked-skills array pointer is 0 (`:38`), `False` if `Floor($a_i_SkillID / 32) >= array size` (`:44`), else the boolean bit test `BitAND($value, 1 << Mod($SkillID, 32)) <> 0` (`:51`) | **MEMORY READ.** Two `Memory_Read` calls for array pointer/size (`:37`, `:40`) plus one read of the bitfield word (`:49`) | `$g_p_BasePointer` (via `Account_GetAccountContextPtr`). The size read is `long` while the pointer read is `ptr` — the same dword width on this x86 target |

## Camera

| Function & signature (file:line) | Returns | Classification — evidence | State it depends on |
| --- | --- | --- | --- |
| `Camera_GetCameraInfo($a_s_Info = "")` — `Data/GwAu3_Data_Camera.au3:3` | `0` when `$a_s_Info = ""` (`:4`); `"X"/"Y"/"Z"` → `float` read (`:8`, `:10`, `:12`); `"XYZ"`, `"All"` → a 3-element array `[cameraX, cameraY, cameraZ]` (`:31-35`); `0` if the bulk read errored or `ReadProcessMemory` returned false (`:29`); `0` for any unmatched `$a_s_Info` (`:38`) | **MEMORY READ.** Scalar cases use `Memory_Read($g_p_SceneContext + 0x2C/0x30/0x34, "float")` (`:8-12`); the `"XYZ"/"All"` case builds its own `DllStructCreate("float;float;float")` and calls `ReadProcessMemory` **directly** on the six-byte region starting at `$g_p_SceneContext + 0x2C` (`:14-28`), then splits it (`:32-34`) | `$g_p_SceneContext` (set `GwAu3_Core.au3:167`); direct path additionally needs `$g_h_Kernel32` and `$g_h_GWProcess` |

## Chat

There is no `Data/GwAu3_Data_Chat.au3` content (stub, § Empty files); this module is command-only.

| Function & signature (file:line) | Returns | Classification — evidence | State it depends on |
| --- | --- | --- | --- |
| `Chat_WriteChat($a_s_Message, $a_s_Sender = 'GwAu3')` — `Cmd/GwAu3_Cmd_Chat.au3:4` | no `Return`; the function evaluates to **0**. Nothing distinguishes success from failure | **MEMORY WRITE (with the dispatch unresolved — see the ambiguity note below).** Computes the slot address `256 * $g_i_QueueCounter + $g_p_QueueBase` (`:6`), advances/wraps `$g_i_QueueCounter` (`:8-12`), writes the sender as `wchar[20]` at `slot + 4` (`Memory_Write`, `:20`), the message as `wchar[101]` at `slot + 44` (`Memory_Write`, `:28`), then writes **4 bytes from `$g_p_WriteChatPtr`** into the slot's first dword with a direct `WriteProcessMemory` (`:29`) — i.e. it tries to place a routine address in the queue slot for the game thread to `jmp` to (mechanism: `Assembler:1982-2009`) | `$g_i_QueueCounter`, `$g_i_QueueSize`, `$g_p_QueueBase` (set `GwAu3_Core.au3:440-442`), `$g_h_GWProcess`, `$g_h_Kernel32`. **`$g_p_WriteChatPtr` is declared at `API/Constants/GwAu3_Const_Chat.au3:3` and assigned nowhere in the whole checkout** (grep of `external/GwAu3` for `WriteChat` finds only that declaration, this use, and two DevTools call sites) |
| `Chat_SendWhisper($a_s_Receiver, $a_s_Message)` — `Cmd/GwAu3_Cmd_Chat.au3:35` | no `Return`; evaluates to **0** | **PACKET SEND** by delegation only: builds `'whisper ' & $a_s_Receiver & ',' & $a_s_Message` (`:36`), truncates to 120 characters (`:39-43`), calls `Chat_SendChat($l_s_Message, '/')` (`:45`), and recurses with the remainder (`:47`). No game access of its own | none of its own; inherits all of `Chat_SendChat`'s |
| `Chat_SendChat($a_s_Message, $a_s_Channel = '!')` — `Cmd/GwAu3_Cmd_Chat.au3:52` | no `Return`; evaluates to **0** | **PACKET SEND.** Fills a queue slot: channel+message as `wchar[122]` at `slot + 12` (`Memory_Write`, `:68`), then `WriteProcessMemory` of **8 bytes from the host struct pointer `$g_p_SendChat`** into the slot base (`:69`). `$g_p_SendChat = DllStructGetPtr($g_d_SendChat)` where `$g_d_SendChat = DllStructCreate('ptr;dword')` (`API/Constants/GwAu3_Const_Core.au3:12-13`), whose field 1 is set to `Memory_GetValue('CommandSendChat')` and field 2 to `$GC_I_HEADER_SEND_CHAT` (`GwAu3_Core.au3:453-454`). So the slot receives `[address of the injected CommandSendChat stub][chat header]`, and the stub runs on the game thread and calls the client's own `PacketSend` with the payload at `slot + 4`, length `0x11C` (`Assembler:2120-2131`) | `$g_i_QueueCounter`, `$g_i_QueueSize`, `$g_p_QueueBase`, `$g_p_SendChat`/`$g_d_SendChat`, `$g_h_GWProcess`. Recourse: messages over 120 chars recurse (`:71`) |

**Ambiguity, stated explicitly (Chat_WriteChat).** The code writes three things into the queue slot
but the *only* dispatch-relevant field (the slot's first dword, read as a code pointer by
`MainProc` at `Assembler:1986-1988`) is sourced from `$g_p_WriteChatPtr`, an AutoIt scalar that the
checkout never assigns. Consequences that are visible in the source but cannot be resolved from it:
(a) if the unassigned variable converts to 0, `WriteProcessMemory` receives a null source buffer and
the slot keeps its previous first dword — and if that dword is 0, `MainProc` skips the slot
(`test ebx,ebx` / `jz MainExit`, `Assembler:1987-1988`); (b) if some build sets it, the routine it
points at is not written anywhere in the checkout, and `CommandSendChat`-style stubs in
`Assembler_CreateCommands` are for the server chat path only. Classification is therefore recorded as
MEMORY WRITE (that is what the source does) with the dispatch target **unresolved**, not as
GAME-THREAD CALL. Lines that create the ambiguity: `Cmd_Chat.au3:29` versus
`Const_Chat.au3:3`.

## Cinematic

No `Data` file content (stub); command-only.

| Function & signature (file:line) | Returns | Classification — evidence | State it depends on |
| --- | --- | --- | --- |
| `Cinematic_SkipCinematic()` — `Cmd/GwAu3_Cmd_Cinematic.au3:4` | `Return Core_SendPacket(0x4, $GC_I_HEADER_CINEMATIC_SKIP)` (`:5`) → **0** (no `Return` inside `Core_SendPacket`) | **PACKET SEND.** 4-byte packet, header only, through `Core_SendPacket` (`GwAu3_Core.au3:575-589`) → `Core_Enqueue` (`:588`) → `CommandPacketSend` stub → client `PacketSend` (`Assembler:2088-2099`) | queue globals (`$g_i_QueueCounter`, `$g_i_QueueSize`, `$g_p_QueueBase`), `$g_d_Packet` |
| `Cinematic_WaitCinematic($a_i_Timeout = 15000, $a_i_SkipAttempts = 5, $a_b_CutsceneOnMap = False, $a_i_CutsceneCount = 1)` — `Cmd/GwAu3_Cmd_Cinematic.au3:9` | `SetError(1, 0, False)` on timeout — once while waiting for the cinematic to start (`:13`) and once inside the skip loop (`:21`); `True` after all `$a_i_CutsceneCount` rounds complete (`:35`) | **PACKET SEND (loop) + MEMORY READ polling.** Polls `Game_GetGameInfo("IsCinematic")` (`:12`, `:26` — memory reads at `Data_Game.au3:36-37`), sleeps via `Other_PingSleep(1500)` (`:17`, itself a memory read of `$g_p_Ping`), then repeatedly calls `Cinematic_SkipCinematic()` (`:22` → packet send) and waits for either the cinematic flag to clear (`:23-28`) or `Map_WaitMapIsLoaded(...)` (`:30`) | `$g_p_Ping` (via `Other_PingSleep`), `$g_p_MapIsLoaded` and its injected flag `MapIsLoaded` (via `Map_WaitMapIsLoaded` → `Map_MapIsLoaded`, `Cmd_Map.au3:158-183`), queue globals via the skip call |

## Effect

| Function & signature (file:line) | Returns | Classification — evidence | State it depends on |
| --- | --- | --- | --- |
| `Effect_DropBond($a_i_SkillID, $a_i_AgentID = -2, $a_i_TargetID = 0)` — `Cmd/GwAu3_Cmd_Effect.au3:4` | bare `Return` (`:6`) → **0** when no matching bond is found; otherwise `Return Core_SendPacket(0x8, $GC_I_HEADER_BOND_DROP, $l_i_BondID)` (`:8`) → **also 0**. Both paths return 0 | **PACKET SEND**, guarded by a MEMORY READ. The guard is `Agent_GetAgentBondInfo($a_i_AgentID, $a_i_SkillID, $a_i_TargetID, "BondID")` (`:5`) — a pure read chain over the agent's bond array (`Data/GwAu3_Data_Agent.au3:914+`, `Memory_Read` at `:928`). The action is the 8-byte packet (`:8`) | agent-context pointers behind `Agent_GetAgentEffectArrayInfo`; queue globals for the send |
| `Effect_GetEffectArg($a_i_SkillID, $a_s_Argument = "", $a_i_HeroNumber = 0)` — `Data/GwAu3_Data_Effect.au3:3` | `"Duration"` → `Round(Duration0 + ((Duration15 - Duration0) / 15) * AttrLevel)` (`:14`); `"Scale"` → `Floor(Scale0 + ((Scale15 - Scale0) / 15) * AttrLevel)` (`:24`); `"BonusScale"` → `Floor(...)` (`:34`); **`Case Else` → `0` (`:35-36`)** — which includes the default `$a_s_Argument = ""` | **MEMORY READ + PURE COMPUTATION.** Reads: `Skill_GetSkillInfo($a_i_SkillID, "Duration0"/"Duration15"/"Scale0"/"Scale15"/"BonusScale0"/"BonusScale15")` (`Data/GwAu3_Data_Skill.au3:22+`), `Agent_GetAgentEffectInfo(-2, $a_i_SkillID, "AttributeLevel")` (`Data_Agent.au3:867-891`), or for heroes `Party_GetMyPartyHeroInfo($a_i_HeroNumber, "AgentID")` first (`:11`, `:21`, `:31`). All arithmetic/serialisation is host-side | agent/party/skill context pointers reached through the scanner set (`$g_p_BasePointer`, `$g_p_AgentBase`, skill base) |

## Friend

| Function & signature (file:line) | Returns | Classification — evidence | State it depends on |
| --- | --- | --- | --- |
| `Friend_SetPlayerStatus($a_i_Status)` — `Cmd/GwAu3_Cmd_Friend.au3:4` | `False` when `$a_i_Status < 0` or `> $GC_I_FRIEND_STATUS_AWAY (=3)` (`:5-8`); `True` early when the current status already equals the requested one (`:12-15`); `True` after enqueueing (`:24`) | **GAME-THREAD CALL.** `DllStructSetData($g_d_ChangeStatus, 2, $a_i_Status)` (`:17`) then `Core_Enqueue($g_p_ChangeStatus, 8)` (`:19`); the slot carries `[CommandPlayerStatus][status]` (`Const_Core.au3:56-57`, address set at `GwAu3_Core.au3:460`), and the queued stub calls the native `PlayerStatus` routine on the game thread (`Assembler:2168-2173`) | `$g_d_ChangeStatus` field 1 (code address, set in `Core_Initialize`), `$g_i_QueueCounter`, `$g_i_QueueSize`, `$g_p_QueueBase`; **also reads** `Friend_GetMyStatus()` (`:11`) so it depends on `$g_p_FriendList`; **writes** the global `$g_i_LastStatus` (`:21`) |
| `Friend_SetOnlineStatus()` — `Cmd/GwAu3_Cmd_Friend.au3:27` | whatever `Friend_SetPlayerStatus($GC_I_FRIEND_STATUS_ONLINE)` returns (`:28`) | **GAME-THREAD CALL** (delegation) | as above |
| `Friend_SetOfflineStatus()` — `Cmd/GwAu3_Cmd_Friend.au3:31` | `Friend_SetPlayerStatus($GC_I_FRIEND_STATUS_OFFLINE)` (`:32`) | **GAME-THREAD CALL** (delegation) | as above |
| `Friend_SetDNDStatus()` — `Cmd/GwAu3_Cmd_Friend.au3:35` | `Friend_SetPlayerStatus($GC_I_FRIEND_STATUS_DND)` (`:36`) | **GAME-THREAD CALL** (delegation) | as above |
| `Friend_SetAwayStatus()` — `Cmd/GwAu3_Cmd_Friend.au3:39` | `Friend_SetPlayerStatus($GC_I_FRIEND_STATUS_AWAY)` (`:40`) | **GAME-THREAD CALL** (delegation) | as above |
| `Friend_AddFriend($a_s_CharacterName, $a_s_Alias = "", $a_i_FriendType = $GC_I_FRIEND_TYPE_FRIEND /* = 1 */)` — `Cmd/GwAu3_Cmd_Friend.au3:45` | `False` on empty name or name longer than `$GC_I_FRIEND_CHARNAME_MAX_LENGTH (=20)` (`:46-49`); `False` if type is outside 1..2 (`:51-54`); `False` if the person is already a friend (`:56-60`); `False` if either `VirtualAllocEx` returned 0 (`:71-74`); **no `Return` on the success path → 0** | **GAME-THREAD CALL + MEMORY WRITE.** MEMORY WRITE: two `VirtualAllocEx` in the client (`:65`, `:68`), two `WriteProcessMemory` of the name and alias strings (`:82-83`), and a `ReadProcessMemory` verification read that is never inspected (`:86`, result unused — `$l_d_VerifyStruct` is created and never read). GAME-THREAD CALL: `DllStructSetData` of name ptr/alias ptr/type (`:88-90`) then `Core_Enqueue($g_p_AddFriend, 16)` (`:92`) → `CommandAddFriend` → native `AddFriend` (`Assembler:2175-2184`). Then `Sleep(500)` (`:93`) and `VirtualFreeEx` of the alias block (`:94`) — note only the **alias** block is freed; the name block allocated at `:65` is not | `$g_d_AddFriend`/`$g_p_AddFriend` field 1 (set `GwAu3_Core.au3:461`), queue globals, `$g_h_GWProcess`, and a MEMORY READ dependency on `$g_p_FriendList` through `Friend_IsFriend($a_s_CharacterName)` (`:56`) |
| `Friend_RemoveFriend($a_s_NameOrAlias)` — `Cmd/GwAu3_Cmd_Friend.au3:97` | `False` when the friend array pointer is 0 or the size is 0 (`:102-105`), `False` when no entry matches name or alias (`:126-129`), `False` when the alias `VirtualAllocEx` returned 0 (`:145-148`); **no `Return` on the success path → 0** | **GAME-THREAD CALL + MEMORY WRITE (and MEMORY READ for the search).** Reads the array header (`:99-100`), walks the pointer array reading `wchar[20]` name at `+0x2C` and alias at `+0x18` (`:112-117`); reads the 16-byte UUID with a direct `ReadProcessMemory` (`:133`); copies it into `$g_d_RemoveFriend` byte by byte (`:136-138`); `VirtualAllocEx` + `WriteProcessMemory` for the alias (`:142`, `:153`); sets struct fields 3 and 4 (`:156-157`) and `Core_Enqueue($g_p_RemoveFriend, 24)` (`:159`) → `CommandRemoveFriend` → native `RemoveFriend` (`Assembler:2186-2195`); `Sleep(500)` (`:161`) and `VirtualFreeEx` (`:162`) | `$g_p_FriendList` (set `GwAu3_Core.au3:215-216`), `$g_d_RemoveFriend`/`$g_p_RemoveFriend` field 1 (set `:462`), queue globals, `$g_h_GWProcess` |
| `Friend_AddIgnore($a_s_CharacterName, $a_s_Alias = "")` — `Cmd/GwAu3_Cmd_Friend.au3:165` | `Return Friend_AddFriend($a_s_CharacterName, $a_s_Alias, $GC_I_FRIEND_TYPE_IGNORE)` (`:166`) → `True`/`False`/`0` exactly as `Friend_AddFriend`, i.e. **also 0 on success** | **GAME-THREAD CALL** (delegation) | as `Friend_AddFriend` |
| `Friend_RemoveIgnore($a_s_CharacterName)` — `Cmd/GwAu3_Cmd_Friend.au3:169` | `False` when the friend array pointer is 0 or the size is 0 (`:174-177`), `False` when no entry matches (`:204-207`), `False` when the matching entry's type is not `$GC_I_FRIEND_TYPE_IGNORE (=2)` (`:210-213`), else the result of `Friend_RemoveFriend($a_s_CharacterName)` (`:216`) → **0 on success** | **GAME-THREAD CALL** with a MEMORY READ search first. Reads the array header (`:171-172`), walks entries reading type at `+0x0`, name at `+0x2C`, alias at `+0x18` (`:184-201`), then delegates to `Friend_RemoveFriend` (`:216`, which enqueues the native call) | `$g_p_FriendList`, `$g_d_RemoveFriend`, queue globals |
| `Friend_GetMyStatus()` — `Data/GwAu3_Data_Friend.au3:3` | `dword` at `$g_p_FriendList + 0xA0` (`:4`) | **MEMORY READ.** `Memory_Read(..., 'dword')` → `ReadProcessMemory` (`GwAu3_Core_Memory.au3:35`) | `$g_p_FriendList` |
| `Friend_GetFriendListPtr()` — `Data/GwAu3_Data_Friend.au3:7` | the value of the global `$g_p_FriendList` (`:8`) | **PURE COMPUTATION (no game access at call time).** It returns a host-side copy of the scanner result; it performs no read. Classified here rather than as MEMORY READ because no `ReadProcessMemory` happens in this call; the address it returns is whatever the scanner resolved during `Core_Initialize` | `$g_p_FriendList` |
| `Friend_GetFriendListInfo($a_s_Info = "")` — `Data/GwAu3_Data_Friend.au3:11` | `0` if `$l_p_Ptr = 0` or `$a_s_Info = ""` (`:13`), `0` for an unmatched `$a_s_Info` (`:28`); else `dword` reads: `"NumberOfFriend"` `+0x24`, `"NumberOfIgnore"` `+0x28`, `"NumberOfPartner"` `+0x2C`, `"NumberOfTrade"` `+0x30`, `"PlayerStatus"` `+0xA0` (`:16-25`) | **MEMORY READ.** One `Memory_Read` per case | `$g_p_FriendList` (through `Friend_GetFriendListPtr`) |
| `Friend_GetFriendInfo($a_v_FriendIdentifier = "", $a_s_Info = "")` — `Data/GwAu3_Data_Friend.au3:31` | `0` when identifier or info is `""` (`:32`); `0` when a numeric identifier is outside `1..$l_i_TotalFriends` (`:45`); per case: `"Type"/"FriendType"` `+0x0` (`:78`), `"Status"/"FriendStatus"` `+0x4` (`:81`), `"UUID"` → 16-byte `Binary` assembled from 16 single-byte reads (`:84-88`), `"Name"/"Alias"` `+0x18` `wchar[20]` (`:91`), `"ConnectedName"/"CharName"/"Playing"` `+0x2C` `wchar[20]` (`:94`), `"FriendID"` `+0x40` (`:97`), `"MapID"/"ZoneID"` `+0x44` (`:100`), `"TypeName"`/`"StatusName"` → the corresponding name string via `Friend_GetFriendTypeName`/`Friend_GetFriendStatusName` (`:104`, `:108`), `"IsOnline"/"IsOffline"/"IsFriend"/"IsIgnored"` → boolean comparisons (`:111-120`), `"Number"/"Index"` → the searched index (`:123`), `"Ptr"` → the resolved friend pointer (`:126`), `Case Else` → `0` (`:128-129`) | **MEMORY READ.** `Memory_ReadPtr($g_p_FriendList, [0, 0x4*$idx, 0x2C/0x18], ...)` for the search (`:48`, `:53-54`, `:65-66`) and `Memory_Read` per case. **Note (recorded, not judged): there is no early return when the search failed** — `$l_p_FriendPtr` stays 0 (`:34`) and the `Switch` at `:76` still reads at `0 + offset` (`ReadProcessMemory` fails and `Memory_Read` returns the zero-valued struct, `GwAu3_Core_Memory.au3:35-36`). Callers that need the failure test it themselves (`Friend_IsFriend:135`, `Friend_IsIgnored:142`) | `$g_p_FriendList`; constants `$GC_I_FRIEND_STATUS_*`, `$GC_I_FRIEND_TYPE_*` (`Const_Friend.au3:5-16`) |
| `Friend_IsFriend($a_s_CharacterName)` — `Data/GwAu3_Data_Friend.au3:133` | `False` if the `"Ptr"` lookup is 0 (`:135`), else `Friend_GetFriendInfo(..., "Type") = $GC_I_FRIEND_TYPE_FRIEND` (`:137`) | **MEMORY READ** | `$g_p_FriendList` |
| `Friend_IsIgnored($a_s_CharacterName)` — `Data/GwAu3_Data_Friend.au3:140` | `False` if the `"Ptr"` lookup is 0 (`:142`), else `... = $GC_I_FRIEND_TYPE_IGNORE` (`:144`) | **MEMORY READ** | `$g_p_FriendList` |
| `Friend_GetFriendStatusName($a_i_FriendStatus)` — `Data/GwAu3_Data_Friend.au3:147` | `"Offline"` / `"Online"` / `"Do Not Disturb"` / `"Away"` for 0/1/2/3 (`:149-156`), `"Unknown"` otherwise (`:157-158`) | **PURE COMPUTATION.** String switch on constants only | none |
| `Friend_GetFriendTypeName($a_i_FriendType)` — `Data/GwAu3_Data_Friend.au3:162` | `"Friend"` / `"Ignore"` / `"Player"` / `"Trade"` for 1/2/3/4 (`:164-171`), `"Unknown"` otherwise (`:172-173`) | **PURE COMPUTATION.** String switch on constants only | none |

## Game

| Function & signature (file:line) | Returns | Classification — evidence | State it depends on |
| --- | --- | --- | --- |
| `Game_Dialog($a_v_DialogID)` — `Cmd/GwAu3_Cmd_Game.au3:4` | `Return Core_SendPacket(0x8, $GC_I_HEADER_DIALOG_SEND, $a_v_DialogID)` (`:5`) → **0** | **PACKET SEND.** Through `Core_SendPacket` (`GwAu3_Core.au3:575-589`) → `Core_Enqueue` → `CommandPacketSend` → client `PacketSend` (`Assembler:2088-2099`) | queue globals, `$g_d_Packet`; the parameter is used as a raw dword (`$a_v_` = "variant" by naming convention) |
| `Game_SwitchMode($a_i_Mode)` — `Cmd/GwAu3_Cmd_Game.au3:9` | `Return Core_SendPacket(0x8, $GC_I_HEADER_PARTY_SET_DIFFICULTY, $a_i_Mode)` (`:10`) → **0** | **PACKET SEND** (same chain) | queue globals, `$g_d_Packet` |
| `Game_DonateFaction($a_s_Faction)` — `Cmd/GwAu3_Cmd_Game.au3:14` | `Return Core_SendPacket(0x10, $GC_I_HEADER_FACTION_DEPOSIT, 0, 0, 5000)` when the first character is `'k'` (`:15-16`), else `Return Core_SendPacket(0x10, $GC_I_HEADER_FACTION_DEPOSIT, 0, 1, 5000)` (`:17-18`) → **0 on both paths** | **PACKET SEND** (same chain). 0x10-byte packet; the Kurzick/Luxon choice is the second parameter (`0`/`1`); the donation amount is hard-coded `5000` in both branches | queue globals, `$g_d_Packet` |
| `Game_GetGameContextPtr()` — `Data/GwAu3_Data_Game.au3:4` | the game-context pointer, or `0` when a link in `[0, 0x18]` is 0 (`Memory_ReadPtr` early-out, `GwAu3_Core_Memory.au3:48-51`) | **MEMORY READ.** `Memory_ReadPtr($g_p_BasePointer, [0, 0x18], "ptr")` (`:5-6`), returns element `[1]` (`:7`) | `$g_p_BasePointer` |
| `Game_GetGameInfo($a_s_Info = "")` — `Data/GwAu3_Data_Game.au3:10` | `0` if `$l_p_Ptr = 0` or `$a_s_Info = ""` (`:12`), `0` for any unmatched `$a_s_Info` (`:54`); else `ptr` reads for `"AgentContext"` `+0x8`, `"MapContext"` `+0x14`, `"TextParser"` `+0x18`, `"AccountContext"` `+0x28`, `"WorldContext"` `+0x2C`, `"Cinematic"` `+0x30`, `"GadgetContext"` `+0x38`, `"GuildContext"` `+0x3C`, `"ItemContext"` `+0x40`, `"CharContext"` `+0x44`, `"PartyContext"` `+0x4C`, `"TradeContext"` `+0x58` (`:15-51`); `"GameLanguage"` → `dword` at `TextParser + 0x1d0` (`:22-24`); `"SomeNumber"` → `dword` at `+0x20` (`:26-27`); `"IsCinematic"` → **`True`/`False`** (dereferences the cinematic pointer and tests two dwords at `+0x0`/`+0x4`, `:35-38`) | **MEMORY READ.** All cases are `Memory_Read`; `"GameLanguage"` and `"IsCinematic"` are two-step chains | `$g_p_BasePointer`. This function is the root of the Account, Guild, Match and Quest chains |

## Guild

| Function & signature (file:line) | Returns | Classification — evidence | State it depends on |
| --- | --- | --- | --- |
| `Guild_InviteGuild($a_s_CharName)` — `Cmd/GwAu3_Cmd_Guild.au3:3` | no `Return`; evaluates to **0** | **PACKET SEND (enqueued), not via `Core_SendPacket`.** Fills the host struct `$g_d_InviteGuild` = `'ptr;dword;dword header;dword counter;wchar name[32];dword type'` (`Const_Core.au3:9`): size field `0x4C` (`:4`), header `0xB5` (`:5`), counter `0x01` (`:6`), the name (`:7`), type `0x02` (`:8`); then `Core_Enqueue(DllStructGetPtr($g_d_InviteGuild), DllStructGetSize($g_d_InviteGuild))` (`:9`). The struct's field 1 is the code address `Memory_GetValue('CommandPacketSend')` (set `GwAu3_Core.au3:450`), whose stub calls the client's `PacketSend` with the payload at `slot + 8` and length `dword[slot + 4]` (`Assembler:2088-2099`) | `$g_d_InviteGuild` field 1 (set in `Core_Initialize`), queue globals; type/counter bytes are literals in the function |
| `Guild_InviteGuest($a_s_CharName)` — `Cmd/GwAu3_Cmd_Guild.au3:12` | no `Return`; evaluates to **0** | **PACKET SEND (enqueued)**, identical to `Guild_InviteGuild` except the last field is `0x01` instead of `0x02` (`:17` vs `Guild_InviteGuild:8`); enqueue at `:18` | as above |
| `Guild_GetGuildContextPtr()` — `Data/GwAu3_Data_Guild.au3:4` | the guild-context pointer, or `0` if any link in `[0, 0x18, 0x3C]` is 0 | **MEMORY READ.** `Memory_ReadPtr($g_p_BasePointer, [0, 0x18, 0x3C], "ptr")` (`:5-6`); note it walks the game-context chain itself instead of calling `Game_GetGameInfo("GuildContext")` — the same two dereferences plus `+0x3C` | `$g_p_BasePointer` |
| `Guild_GetMyGuildInfo($a_s_Info = "")` — `Data/GwAu3_Data_Guild.au3:10` | `0` if the context pointer is 0 or `$a_s_Info = ""` (`:12`), `0` for an unmatched `$a_s_Info` (`:52`); else reads: `"PlayerName"` `+0x34` `wchar[20]`, `"PlayerGuildIndex"` `+0x60` `long`, `"PlayerGuildRank"` `+0x2A0` `long`, `"Announcement"` `+0x78` `wchar[256]`, `"AnnouncementAuthor"` `+0x278` `wchar[20]`, `"TownAlliance"` `+0x2A8` ptr, `"TownAllianceSize"` `+0x2A8+0x8` long, `"KurzickTownCount"` `+0x2B8`, `"LuxonTownCount"` `+0x2BC`, `"GuildRosterPtr"` `+0x358` ptr, `"GuildRosterSize"` `+0x358+0x8`, `"GuildArrayPtr"` `+0x2F8` ptr, `"GuildArraySize"` `+0x2F8+0x8`, `"GuildHistoryPtr"` `+0x2CC` ptr, `"GuildHistorySize"` `+0x2CC+0x8` (`:14-49`) | **MEMORY READ** | `$g_p_BasePointer` |
| `Guild_GetGuildPlayerInfo($a_i_PlayerIndex, $a_s_Info = "")` — `Data/GwAu3_Data_Guild.au3:55` | `0` if the roster pointer is 0, the index is negative, or the index is `>=` roster size (`:59`); `0` if the resolved player pointer is 0 or `$a_s_Info = ""` (`:62`); `0` for an unmatched `$a_s_Info` (`:90`); else reads: `"InvitedName"` `+0x8` `wchar[20]`, `"CurrentName"` `+0x30`, `"InviterName"` `+0x58`, `"InviteTime"` `+0x80` long, `"PromoterName"` `+0x84` `wchar[20]`, `"Offline"` `+0xDC`, `"MemberType"` `+0xE0`, `"Status"` `+0xE4` (`:65-87`) | **MEMORY READ.** Roster pointer and size come from `Guild_GetMyGuildInfo` (`:56-57`), then index → pointer → field reads | `$g_p_BasePointer` (via `Guild_GetMyGuildInfo`) |
| `Guild_GetGuildHistoryEvent($a_i_EventIndex, $a_s_Info = "")` — `Data/GwAu3_Data_Guild.au3:93` | `0` if the history pointer is 0, the index is negative, or the index is `>=` history size (`:97`); `0` if the resolved event pointer is 0 or `$a_s_Info = ""` (`:100`); `0` for an unmatched `$a_s_Info` (`:113`); else `"Time1"` `+0x0` long, `"Time2"` `+0x4` long, `"Name"` `+0x8` `wchar[256]` (`:104-110`) | **MEMORY READ** | `$g_p_BasePointer` (via `Guild_GetMyGuildInfo`) |
| `Guild_GetTownAllianceInfo($a_i_AllianceIndex, $a_s_Info = "")` — `Data/GwAu3_Data_Guild.au3:116` | `0` if the town-alliance pointer is 0, the index is negative, or the index is `>=` size (`:120`); `0` if the resolved alliance pointer is 0 or `$a_s_Info = ""` (`:123`); `0` for an unmatched `$a_s_Info` (`:154`); else `"Rank"` `+0x0`, `"Allegiance"` `+0x4`, `"Faction"` `+0x8`, `"Name"` `+0xC` `wchar[32]`, `"Tag"` `+0x4C` `wchar[5]`, `"CapeBackgroundColor"` `+0x58`, `"CapeDetailColor"` `+0x5C`, `"CapeEmblemColor"` `+0x60`, `"CapeShape"` `+0x64`, `"CapeDetail"` `+0x68`, `"CapeEmblem"` `+0x6C`, `"CapeTrim"` `+0x70`, `"MapID"` `+0x74` (`:126-151`) | **MEMORY READ** | `$g_p_BasePointer` (via `Guild_GetMyGuildInfo`) |

## Other

| Function & signature (file:line) | Returns | Classification — evidence | State it depends on |
| --- | --- | --- | --- |
| `Other_RndSleep($a_i_Amount, $a_f_Random = 0.05)` — `Cmd/GwAu3_Cmd_Other.au3:4` | no `Return`; evaluates to **0** | **PURE COMPUTATION.** `Sleep(Random($a_i_Amount - $a_i_Amount * $a_f_Random, $a_i_Amount + $a_i_Amount * $a_f_Random))` (`:5-6`). No game access | none |
| `Other_TolSleep($a_i_Amount = 150, $a_i_Tolerance = 50)` — `Cmd/GwAu3_Cmd_Other.au3:10` | no `Return`; evaluates to **0** | **PURE COMPUTATION.** `Sleep(Random($a_i_Amount - $a_i_Tolerance, $a_i_Amount + $a_i_Tolerance))` (`:11`) | none |
| `Other_PingSleep($a_i_MsExtra = 0)` — `Cmd/GwAu3_Cmd_Other.au3:15` | no `Return`; evaluates to **0** | **MEMORY READ + PURE COMPUTATION.** Reads ping and sleeps that long plus the extra: `Sleep(Other_GetPing() + $a_i_MsExtra)` (`:16`), where `Other_GetPing` = `Memory_Read($g_p_Ping)` (`Data/GwAu3_Data_Other.au3:4-5`). Primary class recorded as MEMORY READ because the sleep duration is a game value | `$g_p_Ping` (set `GwAu3_Core.au3:161`) |
| `Other_WaitPingStabilized($a_i_WaiTimer = 2000)` — `Cmd/GwAu3_Cmd_Other.au3:20` | no `Return`; evaluates to **0** | **MEMORY READ (polling loop) + PACKET SEND + PURE COMPUTATION.** Polls `Map_GetInstanceInfo("IsLoading")` (`:26`), `Game_GetGameInfo("IsCinematic")` (`:28`, `:33`, `:42`) and `Other_GetPing()` (`:37`, `:42`); calls `Cinematic_SkipCinematic()` inside the cinematic branch (`:31` → packet send) and `Sleep(16)` throughout (`:25`, `:32`, `:41`) | `$g_p_InstanceInfo`, `$g_p_BasePointer` (via `Game_GetGameInfo`), `$g_p_Ping`, queue globals via the skip call |
| `Other_GetPing()` — `Data/GwAu3_Data_Other.au3:4` | `Memory_Read($g_p_Ping)` with the default type `dword` (`:5`) | **MEMORY READ.** `Memory_Read` → `ReadProcessMemory` (`GwAu3_Core_Memory.au3:35`) | `$g_p_Ping` |

## PreGame

No `Cmd` file content (stub); data-only.

| Function & signature (file:line) | Returns | Classification — evidence | State it depends on |
| --- | --- | --- | --- |
| `PreGame_Ptr()` — `Data/GwAu3_Data_PreGame.au3:3` | `Memory_Read($g_p_PreGame, 'ptr')` (`:4`) — the pre-game context pointer, or whatever the failed read yields (0) | **MEMORY READ.** One dereference of the scanned global | `$g_p_PreGame` (scanned value `+0x33`, set `GwAu3_Core.au3:165`) |
| `PreGame_FrameID()` — `Data/GwAu3_Data_PreGame.au3:7` | `dword` at `PreGame_Ptr() + 0x0` (`:8`) | **MEMORY READ.** Chained through `PreGame_Ptr` (`:4`) | `$g_p_PreGame` |
| `PreGame_ChosenCharacter()` — `Data/GwAu3_Data_PreGame.au3:11` | `dword` at `PreGame_Ptr() + 0xD8` (`:12`) — the index of the selected character | **MEMORY READ** | `$g_p_PreGame` |
| `PreGame_LoginCharacterArray()` — `Data/GwAu3_Data_PreGame.au3:15` | `ptr` at `PreGame_Ptr() + 0xE0` (`:16`) | **MEMORY READ** | `$g_p_PreGame` |
| `PreGame_CharName($a_i_Index)` — `Data/GwAu3_Data_PreGame.au3:19` | `WCHAR[20]` at `LoginCharacterArray() + 0x50 + 0x78 * $a_i_Index` (`:20`); comment in source says index runs "from 0 to max character" | **MEMORY READ.** Three-step chain (context → array → record). No bounds check on the index in this function | `$g_p_PreGame`; callers (`Core_AutoStart`, `GwAu3_Core.au3:606-620`) pass a value obtained from `PreGame_ChosenCharacter()` |

## Quest

| Function & signature (file:line) | Returns | Classification — evidence | State it depends on |
| --- | --- | --- | --- |
| `Quest_AcceptQuest($a_i_QuestID)` — `Cmd/GwAu3_Cmd_Quest.au3:4` | `Return Core_SendPacket(0x8, $GC_I_HEADER_DIALOG_SEND, '0x008' & Hex($a_i_QuestID, 3) & '01')` (`:5`) → **0** | **PACKET SEND.** The dialog-send packet with a composed string parameter (`'0x008' & Hex(id,3) & '01'`), through `Core_SendPacket` → `Core_Enqueue` → `CommandPacketSend` → client `PacketSend` | queue globals, `$g_d_Packet` |
| `Quest_QuestReward($a_i_QuestID)` — `Cmd/GwAu3_Cmd_Quest.au3:9` | `Return Core_SendPacket(0x8, $GC_I_HEADER_DIALOG_SEND, '0x008' & Hex($a_i_QuestID, 3) & '07')` (`:10`) → **0** | **PACKET SEND.** Same shape as `Quest_AcceptQuest`, trailing `'07'` instead of `'01'` | queue globals, `$g_d_Packet` |
| `Quest_AbandonQuest($a_i_QuestID)` — `Cmd/GwAu3_Cmd_Quest.au3:14` | `Return Core_SendPacket(0x8, $GC_I_HEADER_QUEST_ABANDON, $a_i_QuestID)` (`:15`) → **0** | **PACKET SEND** | queue globals, `$g_d_Packet` |
| `Quest_RequestInfos($a_i_QuestID)` — `Cmd/GwAu3_Cmd_Quest.au3:19` | calls `Core_SendPacket(...)` **without `Return`** (`:20`) → evaluates to **0** | **PACKET SEND.** 8-byte packet with `$GC_I_HEADER_QUEST_REQUEST_INFOS` | queue globals, `$g_d_Packet` |
| `Quest_GetQuestInfo($a_i_QuestID, $a_s_Info = "")` — `Data/GwAu3_Data_Quest.au3:4` | `0` when `$a_s_Info = ""` (`:7`, returned *after* the quest-log size is read at `:6`); `False` if the quest was not found **and** `$a_s_Info = "HasQuest"` (`:16-17`); `0` if the quest was not found and info is anything else (`:19`); else `"HasQuest"` → `True` (`:25`), `"LogState"` → `long` at `+0x4` (`:27`), `"HasInfo"`/`"IsCompleted"`/`"IsCurrentQuest"`/`"IsPrimary"`/`"IsAreaPrimary"` → booleans from `BitAND` of `+0x4` with `0x1`/`0x2`/`0x10`/`0x20`/`0x40` (`:29-37`), `"Location"`/`"LocationStr"`, `"NameEnc"`/`"Name"`, `"NPCNameEnc"`/`"NPCName"`, `"DescriptionEnc"`/`"Description"`, `"ObjectivesEnc"`/`"Objectives"` → decoder results (`:39-83`), `"MapFrom"` `+0x14` dword, `"MarkerX"` `+0x18` float, `"MarkerY"` `+0x1C` float, `"MarkerZ"` `+0x20` dword, `"MapTo"` `+0x28` dword (`:60-69`), unmatched → `0` (`:86`) | **MEMORY READ as the primary mechanism, with GAME-THREAD CALL paths.** The log scan is `Memory_ReadPtr($g_p_BasePointer, [0, 0x18, 0x2C, 0x52C, 0x34 * $i], "long")` returned as `long` and re-wrapped with `Ptr()` (`:10-12`), with the size from `World_GetWorldInfo("QuestLogSize")` (`:6`). All scalar cases are `Memory_Read`. **The `*Enc` cases call `Utils_DecodeEncString($ptr)` — which is a MEMORY READ of the encoded words that returns an integer string ID, not text** (`GwAu3_Core_Utils.au3:440-462`, reads at `:448`, `Return $l_i_Val` at `:461`); the plain-text cases call `Utils_DecodeEncStringAsync($ptr)`, which is a **GAME-THREAD CALL**: it resets a flag with `Memory_Write` (`Utils:480`), `Core_Enqueue`s the decode command (`Utils:483`) so the client's own decoder runs on the game thread, then polls up to 1000 ms (`Utils:487-494`) and returns the decoded `wchar[1024]` or `""` on timeout (`Utils:497`). Note the scan does **not** exit the loop when it finds a match (`:12`) and the returned pointer keeps the *last* match | `$g_p_BasePointer`, `$g_p_DecodeInputPtr`/`$g_p_DecodeOutputPtr`/`$g_p_DecodeReady`, `$g_d_DecodeEncString`, queue globals. Note `$a_i_QuestID` is compared against a `long` read |
| `Mission_GetObjectiveCount()` — `Data/GwAu3_Data_Quest.au3:92` | `World_GetWorldInfo("MissionObjectiveArraySize")` (`:93`) — a `long` count, or 0 when the world context is 0 | **MEMORY READ** | `$g_p_BasePointer` (via `World_GetWorldInfo`) |
| `Mission_GetObjectiveInfo($a_i_Index, $a_s_Info = "")` — `Data/GwAu3_Data_Quest.au3:99` | `0` if the array pointer is 0, `$a_i_Index >= $l_i_Size`, or `$a_s_Info = ""` (`:103`); `"ObjectiveID"` → `dword` at entry `+0x0` (`:110`), `"State"` → `dword` at `+0x8` (`:112`), `"TextEnc"` → `Utils_DecodeEncString` of the pointer at `+0x4` (`:115`), `"Text"` → `Utils_DecodeEncStringAsync` of the same pointer (`:118`), `Case Else` → `0` (`:120`) | **MEMORY READ (primary) + GAME-THREAD CALL for `"Text"`.** Entry stride is `0xC` (`:106`). **No lower-bound check on `$a_i_Index`** — a negative index computes an address below the array (the comparison at `:103` only tests the upper bound), recorded as written, not judged | `$g_p_BasePointer` (via `World_GetWorldInfo`), decode globals for the `"Text"` path |

## Title

| Function & signature (file:line) | Returns | Classification — evidence | State it depends on |
| --- | --- | --- | --- |
| `Title_SetDisplayedTitle($a_i_Title = 0)` — `Cmd/GwAu3_Cmd_Title.au3:3` | `Return Core_SendPacket(0x8, $GC_I_HEADER_TITLE_DISPLAY, $a_i_Title)` when `$a_i_Title <> 0` (`:4-5`); `Return Core_SendPacket(0x4, $GC_I_HEADER_TITLE_HIDE)` otherwise (`:7`) → **0 on both paths** | **PACKET SEND.** Two different headers and lengths (8-byte display vs 4-byte hide) through `Core_SendPacket` → queue → `CommandPacketSend` → client `PacketSend` | queue globals, `$g_d_Packet` |
| `Title_GetTitleInfo($a_i_Title = 0, $a_s_Info = "")` — `Data/GwAu3_Data_Title.au3:6` | `0` if the title-array pointer is 0, `$a_i_Title < 0`, or `$a_i_Title >= $l_i_Size` (`:9`); `0` if `$a_s_Info = ""` (`:12`); else `"Props"` `+0x0`, `"CurrentPoints"` `+0x4`, `"CurrentTitleTierIndex"/"CurrentTitleTier"` `+0x8`, `"PointsNeededCurrentRank"` `+0xC`, `"Unknown10"` `+0x10`, `"NextTitleTierIndex"/"NextTitleTier"` `+0x14`, `"PointsNeededNextRank"` `+0x18`, `"MaxTitleRank"` `+0x1C`, `"MaxTitleTierIndex"/"MaxTitleTier"` `+0x20` → `dword` reads (`:16-32`); `"PointsDescriptionEnc"`/`"TitleDescriptionEnc"` → `Utils_DecodeEncString` of the pointer at `+0x24`/`+0x28` (`:33-35`, `:39-41`); `"PointsDescription"`/`"TitleDescription"` → `Utils_DecodeEncStringAsync` of the same pointers (`:36-38`, `:42-44`); unmatched → `0` (`:47`) | **MEMORY READ (primary) + GAME-THREAD CALL for the decoded-text cases.** Record stride `0x2C` (`:11`, comment at `:4-5` records a structure change from `0x28`). `Utils_DecodeEncString` is the read-only decoder returning a numeric ID (`Utils:440-462`); `Utils_DecodeEncStringAsync` is the enqueued native decode (`Utils:469-498`) | `$g_p_BasePointer` (via `World_GetWorldInfo("TitleArray"/"TitleArraySize")`), decode globals for the async cases |

## World

No `Cmd` file content (stub); data-only.

| Function & signature (file:line) | Returns | Classification — evidence | State it depends on |
| --- | --- | --- | --- |
| `World_GetWorldContextPtr()` — `Data/GwAu3_Data_World.au3:4` | the world-context pointer, or `0` if any link in `[0, 0x18, 0x2C]` is 0 | **MEMORY READ.** `Memory_ReadPtr($g_p_BasePointer, [0, 0x18, 0x2C], "ptr")` (`:5-6`) | `$g_p_BasePointer` |
| `World_GetWorldInfo($a_s_Info = "")` — `Data/GwAu3_Data_World.au3:10` | `0` if the context pointer is 0 or `$a_s_Info = ""` (`:12`), `0` for an unmatched `$a_s_Info` (`:211`); otherwise one `Memory_Read` per case: `ptr` for `"AccountInfo"` `+0x0`, `"MessageBuffArray"` `+0x4`, `"DialogBuffArray"` `+0x14`, `"MerchItemArray"` `+0x24`, `"MerchItemArray2"` `+0x34`, `"PartyAllyArray"` `+0x8C`, `"MapAgentArray"` `+0x7C`, `"PartyAttributeArray"` `+0xAC`, `"AgentEffectsArray"` `+0x508`, `"QuestLog"` `+0x52C`, `"MissionObjectiveArray"` `+0x564`, `"HeroFlagArray"` `+0x584`, `"HeroInfoArray"` `+0x594`, `"ControlledMinionsArray"` `+0x5BC`, `"PlayerMoraleInfo"` `+0x624`, `"PartyMoraleInfo"` `+0x62C`, `"PetInfoArray"` `+0x6AC`, `"PartyProfessionArray"` `+0x6BC`, `"SkillbarArray"` `+0x6F0`, `"AgentInfoArray"` `+0x7CC`, `"NPCArray"` `+0x7FC`, `"PlayerArray"` `+0x80C`, `"TitleArray"` `+0x81C`, `"VanquishedAreasArray"` `+0x83C`, `"MissionsCompletedArray"` `+0x5CC`, `"MissionsBonusArray"` `+0x5DC`, `"MissionsCompletedHMArray"` `+0x5EC`, `"MissionsBonusHMArray"` `+0x5FC`, `"LearnableSkillsArray"` `+0x700`, `"UnlockedSkillsArray"` `+0x710`, `"UnlockedMapArray"` `+0x60C`, `"HenchmanIDArray"` `+0x574` (`:15-208`); the matching `*Size` cases read `offset + 0x8` as `dword`/`long`; scalar `dword` values for `"ActiveQuestID"` `+0x528`, `"PlayerNumber"` `+0x67C`, `"IsHmUnlocked"` `+0x684`, `"SalvageSessionID"` `+0x690`, `"PlayerTeamToken"` `+0x6A8`, `"Experience"` `+0x740`, `"CurrentKurzick"` `+0x748`, `"TotalEarnedKurzick"` `+0x750`, `"CurrentLuxon"` `+0x758`, `"TotalEarnedLuxon"` `+0x760`, `"CurrentImperial"` `+0x768`, `"TotalEarnedImperial"` `+0x770`, `"Level"` `+0x788`, `"Morale"` `+0x790`, `"CurrentBalth"` `+0x798`, `"TotalEarnedBalth"` `+0x7A0`, `"CurrentSkillPoints"` `+0x7A8`, `"TotalEarnedSkillPoints"` `+0x7B0`, `"MaxKurzickPoints"` `+0x7B8`, `"MaxLuxonPoints"` `+0x7BC`, `"MaxBalthPoints"` `+0x7C0`, `"MaxImperialPoints"` `+0x7C4`, `"EquipmentStatus"` `+0x7C8`, `"FoesKilled"` `+0x84C`, `"FoesToKill"` `+0x850`; **`"FlagAll"` returns a 3-element `float` array** (`:31-35`); `"MyID"` is a two-step read (`+0x680` then `+0x14`, `:40-42`) | **MEMORY READ.** Every case is `Memory_Read`; only `"MyID"` and `"FlagAll"` are multi-step | `$g_p_BasePointer`. This function feeds the Account, Quest, Title, Mission and Party reads |
| `World_IsSkillLearnt($a_i_SkillID)` — `Data/GwAu3_Data_World.au3:214` | `False` if the world context is 0 (`:216`), `False` if the unlocked-skills array pointer at `+0x710` is 0 (`:219`), `False` if `Floor($a_i_SkillID / 32) >= size` (`:225`), else `BitAND($value, 1 << Mod($SkillID, 32)) <> 0` (`:232`) | **MEMORY READ.** Pointer, size and bitfield-word reads (`:218`, `:221`, `:230`) | `$g_p_BasePointer` |
| `World_GetSkillDuplicateCount($a_i_SkillID)` — `Data/GwAu3_Data_World.au3:235` | `0` if the world context is 0 (`:237`), `0` if the dupe array pointer at `+0x720` is 0 (`:240`), `0` if no entry's skill id matches (`:255`), else the `long` count at that entry's `+0x4` (`:250-251`) | **MEMORY READ.** Array pointer/size reads plus a linear scan of `long` pairs (`:242-253`) | `$g_p_BasePointer` |
| `World_MissionGetState($a_i_MapID, $a_b_HardMode = False)` — `Data/GwAu3_Data_World.au3:278` | `0` if `Map_GetAreaInfo($a_i_MapID, "RegionType") = 0` (`:281`); `0` if the region type is none of cooperative mission / mission outpost / dungeon (`:284-289`); `0` if the world context is 0 (`:293`); else a **bitfield `0..7`**: bit `1` = `$c_MissionState_Primary`, bit `2` = `$c_MissionState_Expert`, bit `4` = `$c_MissionState_Master` (`:333-338`, constants at `:261-264`). For Factions and Nightfall the roles are swapped: Master = bonus, Expert = completed, Primary = either (`:325-330`). **A returned 0 is therefore ambiguous in-band: it means "not a mission map", "world context missing" and "not completed" alike** | **MEMORY READ + PURE COMPUTATION.** Reads `Map_GetAreaInfo(..., "RegionType"/"Campaign")` (`:280`, `:315` → `Data/GwAu3_Data_Map.au3:284-296`, reads of the `$g_p_AreaInfo` table), the four completion/bonus array pointers and sizes (`:299-307`), and the bits through `Utils_Array_BoolAt` (`:311-312` → `GwAu3_Core_Utils.au3:296-308`, one `Memory_Read` at `:305`). The campaign branching and bitfield assembly (`:314-338`) are host-side arithmetic | `$g_p_BasePointer` (via `Map_GetAreaInfo` path is `$g_p_AreaInfo`), `$g_p_AreaInfo`, constants `$GC_I_MAP_REGIONTYPE_*`, `$GC_I_MAP_CAMPAIGN_*` |
| `World_MissionIsCompleted($a_i_MapID, $a_b_HardMode = False)` — `Data/GwAu3_Data_World.au3:348` | `BitAND(World_MissionGetState(...), $c_MissionState_Primary) <> 0` (`:349`) — `True`/`False`, inheriting the ambiguity of 0 above | **MEMORY READ** (delegation) | as `World_MissionGetState` |
| `World_MissionHasExpert($a_i_MapID, $a_b_HardMode = False)` — `Data/GwAu3_Data_World.au3:359` | `BitAND(World_MissionGetState(...), $c_MissionState_Expert) <> 0` (`:360`) | **MEMORY READ** (delegation) | as `World_MissionGetState` |
| `World_MissionHasMaster($a_i_MapID, $a_b_HardMode = False)` — `Data/GwAu3_Data_World.au3:370` | `BitAND(World_MissionGetState(...), $c_MissionState_Master) <> 0` (`:371`) | **MEMORY READ** (delegation) | as `World_MissionGetState` |

## Match

No `Cmd` file content (stub); data-only.

| Function & signature (file:line) | Returns | Classification — evidence | State it depends on |
| --- | --- | --- | --- |
| `Match_GetObserverMatchPtr($a_i_MatchNumber = 0)` — `Data/GwAu3_Data_Match.au3:4` | `Memory_Read($l_p_Ptr + ($a_i_MatchNumber * 4), "ptr")` (`:8`) — an observer-match record pointer, or the zero-valued result of a failed read when the chain broke | **MEMORY READ.** `Memory_ReadPtr($g_p_BasePointer, [0, 0x18, 0x44, 0x24C], "ptr")` (`:5-7`) then one indexed pointer read (`:8`). Note the chain walks the game context by offset (`+0x44` = `CharContext` per `Data_Game.au3:46-47`) and then `+0x24C` | `$g_p_BasePointer` |
| `Match_GetObserverMatchInfo($a_i_MatchNumber = 0, $a_s_Info = "")` — `Data/GwAu3_Data_Match.au3:11` | `0` if the record pointer is 0 or `$a_s_Info = ""` (`:13`), `0` for an unmatched `$a_s_Info` (`:65`); else `long` reads: `"MatchID"` `+0x0`, `"MatchIDDup"` `+0x4`, `"MapID"` `+0x8`, `"Age"` `+0xC`, `"Type"` `+0x10`, `"Reserved"` `+0x14`, `"Version"` `+0x18`, `"State"` `+0x1C`, `"Level"` `+0x20`, `"Config1"` `+0x24`, `"Config2"` `+0x28`, `"Score1"` `+0x2C`, `"Score2"` `+0x30`, `"Score3"` `+0x34`, `"Stat1"` `+0x38`, `"Stat2"` `+0x3C`, `"Data1"` `+0x40`, `"Data2"` `+0x44` (`:16-51`); `"TeamNamesPtr"` `+0x48` ptr and `"TeamNames2Ptr"` `+0x74` ptr (`:52-58`); `"Team1Name"`/`"Team2Name"` → `wchar[256]` read through those pointers and passed through `Match_CleanTeamName` (`:54-61`) | **MEMORY READ.** One `Memory_Read` per case, two-step for the team names | `$g_p_BasePointer` |
| `Match_CleanTeamName($a_s_Name)` — `Data/GwAu3_Data_Match.au3:68` | the cleaned string (leading combining/marking characters stripped, control characters stripped, whitespace trimmed) — `:69-72` | **PURE COMPUTATION.** `StringRegExpReplace` twice and `StringStripWS`; no game access | none (the caller supplies a string it already read) |

## Empty files (no functions)

These seven files exist, are included by `API/Modules/_Modules.au3`, and contain only
`#include-once`:

| File | Lines | Note |
| --- | --- | --- |
| `Cmd/GwAu3_Cmd_Account.au3` | 1 | module is data-only |
| `Cmd/GwAu3_Cmd_Camera.au3` | 1 | module is data-only |
| `Cmd/GwAu3_Cmd_Match.au3` | 1 | module is data-only |
| `Cmd/GwAu3_Cmd_PreGame.au3` | 1 | module is data-only |
| `Cmd/GwAu3_Cmd_World.au3` | 1 | module is data-only |
| `Data/GwAu3_Data_Chat.au3` | 1 | module is command-only |
| `Data/GwAu3_Data_Cinematic.au3` | 1 | module is command-only |

## Cross-cutting state the modules depend on

Everything below is set by `Core_Initialize` (`GwAu3_Core.au3:9-543`) or by
`Assembler_ModifyMemory` (`GwAu3_Core_Assembler.au3:1845-1912`), i.e. **none of these modules
works unless initialization ran and the queue/hook were injected**:

| Global / label | Set at | Used by (in the covered modules) |
| --- | --- | --- |
| `$g_h_Kernel32`, `$g_h_GWProcess` | `GwAu3_Core_Memory.au3:4-6` (`Memory_Open`) | every read/write and every `DllCall` in Chat, Friend, Camera |
| `$g_p_BasePointer` | `GwAu3_Core.au3:159` | Account, Game, Guild, Match, Quest, Title, World (all context chains) |
| `$g_p_Ping` | `:161` | `Other_GetPing` → `Other_PingSleep`, `Other_WaitPingStabilized`, `Cinematic_WaitCinematic` |
| `$g_p_PreGame` | `:165` (scanned value `+0x33`) | all five `PreGame_*` |
| `$g_p_SceneContext` | `:167` | `Camera_GetCameraInfo` |
| `$g_p_FriendList` | `:215-216` (scanner result re-resolved through `Scanner_FindInRange`) | all eight `Friend_*` data functions and three of the friend commands |
| `$g_i_QueueCounter`, `$g_i_QueueSize`, `$g_p_QueueBase` | `:440-442` (`QueueSize` label set to `0x100` at `:425`, so `$g_i_QueueSize = 255`) | every `Core_Enqueue` caller: Chat, Cinematic, Effect, Friend, Game, Guild, Quest, Title |
| `$g_i_LastStatus` | written `Cmd_Friend.au3:21`, reset `GwAu3_Core.au3:696` | **written but never read anywhere in the checkout** — dead state, recorded as written |
| `$g_d_Packet` / `$g_p_Packet` field 1 | `:451` | Game, Quest, Title, Cinematic packet sends |
| `$g_d_ChangeStatus` field 1 | `:460` | `Friend_SetPlayerStatus` |
| `$g_d_AddFriend` field 1 | `:461` | `Friend_AddFriend` / `Friend_AddIgnore` |
| `$g_d_RemoveFriend` field 1 | `:462` | `Friend_RemoveFriend` / `Friend_RemoveIgnore` |
| `$g_d_InviteGuild` field 1 | `:450` | `Guild_InviteGuild`, `Guild_InviteGuest` |
| `$g_d_SendChat` fields 1 and 2 | `:453-454` | `Chat_SendChat`, `Chat_SendWhisper` |
| `$g_p_WriteChatPtr` | **nowhere** — declared `Const_Chat.au3:3` | `Chat_WriteChat` only (see the Chat ambiguity note) |
| `$g_p_DecodeInputPtr`, `$g_p_DecodeOutputPtr`, `$g_p_DecodeReady`, `$g_d_DecodeEncString` | `:534-537` | the `*Enc`/text paths of Quest and Title |
| `$g_p_MapIsLoaded` / injected label `MapIsLoaded` | `:444` / `Assembler:1921`, written by the `LoadFinished` detour (`Assembler:2070-2076`) | `Cinematic_WaitCinematic` via `Map_WaitMapIsLoaded` |
| `$g_p_AreaInfo` | `:296` | `World_MissionGetState` via `Map_GetAreaInfo` |

## Classifications summary

Counts are of the **primary** classification recorded for each function. The 14 modules expose
**70 functions** (all names unique, every module function prefixed with its module name): 29 in
`Cmd` files and 41 in `Data` files. Each delegating wrapper is counted individually
(`Friend_SetOnlineStatus`, `Friend_SetOfflineStatus`, `Friend_SetDNDStatus`, `Friend_SetAwayStatus`
and `Friend_AddIgnore` each appear as their own row).

| Class | Count | Functions |
| --- | --- | --- |
| MEMORY READ | **39** | `Account_GetAccountContextPtr`, `Account_GetAccountInfo`, `Account_IsSkillUnlocked`, `Camera_GetCameraInfo`, `Effect_GetEffectArg`, `Friend_GetMyStatus`, `Friend_GetFriendListInfo`, `Friend_GetFriendInfo`, `Friend_IsFriend`, `Friend_IsIgnored`, `Game_GetGameContextPtr`, `Game_GetGameInfo`, `Guild_GetGuildContextPtr`, `Guild_GetMyGuildInfo`, `Guild_GetGuildPlayerInfo`, `Guild_GetGuildHistoryEvent`, `Guild_GetTownAllianceInfo`, `Other_PingSleep`, `Other_WaitPingStabilized`, `Other_GetPing`, `PreGame_Ptr`, `PreGame_FrameID`, `PreGame_ChosenCharacter`, `PreGame_LoginCharacterArray`, `PreGame_CharName`, `Quest_GetQuestInfo`, `Mission_GetObjectiveCount`, `Mission_GetObjectiveInfo`, `Title_GetTitleInfo`, `World_GetWorldContextPtr`, `World_GetWorldInfo`, `World_IsSkillLearnt`, `World_GetSkillDuplicateCount`, `World_MissionGetState`, `World_MissionIsCompleted`, `World_MissionHasExpert`, `World_MissionHasMaster`, `Match_GetObserverMatchPtr`, `Match_GetObserverMatchInfo` |
| MEMORY WRITE | **1** | `Chat_WriteChat` (with its dispatch target unresolved — see below) |
| PACKET SEND | **15** | `Chat_SendChat`, `Chat_SendWhisper`, `Cinematic_SkipCinematic`, `Cinematic_WaitCinematic`, `Effect_DropBond`, `Game_Dialog`, `Game_SwitchMode`, `Game_DonateFaction`, `Guild_InviteGuild`, `Guild_InviteGuest`, `Quest_AcceptQuest`, `Quest_QuestReward`, `Quest_AbandonQuest`, `Quest_RequestInfos`, `Title_SetDisplayedTitle` |
| GAME-THREAD CALL | **9** | `Friend_SetPlayerStatus`, `Friend_SetOnlineStatus`, `Friend_SetOfflineStatus`, `Friend_SetDNDStatus`, `Friend_SetAwayStatus`, `Friend_AddFriend`, `Friend_RemoveFriend`, `Friend_AddIgnore`, `Friend_RemoveIgnore` |
| UI/INPUT SYNTHESIS | **0** | none in these modules (the `ControlSend` calls in the checkout are in `Core_AutoStart`, `GwAu3_Core.au3:616`, `:639`, not in these modules) |
| PURE COMPUTATION | **6** | `Friend_GetFriendListPtr`, `Friend_GetFriendStatusName`, `Friend_GetFriendTypeName`, `Other_RndSleep`, `Other_TolSleep`, `Match_CleanTeamName` |
| OTHER | **0** | none |
| **Total** | **70** | |

### Functions with more than one mechanism (primary listed first)

| Function | Mechanisms present | Lines |
| --- | --- | --- |
| `Friend_AddFriend` | GAME-THREAD CALL + MEMORY WRITE + MEMORY READ | write/alloc `:65-86`, enqueue `:92`, read `:56` |
| `Friend_RemoveFriend` | GAME-THREAD CALL + MEMORY WRITE + MEMORY READ | read `:99-133`, write/alloc `:142-153`, enqueue `:159` |
| `Friend_RemoveIgnore` | GAME-THREAD CALL + MEMORY READ | read `:171-202`, delegate `:216` |
| `Friend_SetPlayerStatus` | GAME-THREAD CALL + MEMORY READ + host-global write | read `:11`, enqueue `:19`, `$g_i_LastStatus` `:21` |
| `Quest_GetQuestInfo`, `Mission_GetObjectiveInfo`, `Title_GetTitleInfo` | MEMORY READ + GAME-THREAD CALL (the plain-text decode paths) | `Data_Quest.au3:44,51,58,76,83`, `:118`; `Data_Title.au3:38,44` |
| `Other_WaitPingStabilized`, `Cinematic_WaitCinematic` | MEMORY READ polling + PACKET SEND + PURE COMPUTATION | `Cmd_Other.au3:26-43` (skip at `:31`); `Cmd_Cinematic.au3:12-30` (skip at `:22`) |
| `Camera_GetCameraInfo` | MEMORY READ (two different routes: `Memory_Read` for scalars, direct `ReadProcessMemory` for `"XYZ"/"All"`) | `:8-12` vs `:22-28` |
| `Effect_DropBond` | PACKET SEND + MEMORY READ guard | read `:5`, send `:8` |

### Functions whose classification is ambiguous or unresolved (stated explicitly, not guessed)

1. **`Chat_WriteChat`** — recorded as MEMORY WRITE. The only dispatch-relevant byte it writes
   (the slot's first dword, `Cmd_Chat.au3:29`) is sourced from `$g_p_WriteChatPtr`, which no file in
   the checkout assigns (`Const_Chat.au3:3` is a bare declaration). Whether the game thread ever
   executes anything for this call cannot be settled from the source; the lines that conflict are
   `Cmd_Chat.au3:29` (writes a routine address) and `Const_Chat.au3:3` (nothing ever puts one there).
   If it does dispatch, it would be a GAME-THREAD CALL; as written, the observable effect is a
   memory write into a queue slot that `MainProc` skips when its first dword is 0
   (`Assembler:1987-1988`).
2. **`Guild_InviteGuild` / `Guild_InviteGuest`** — recorded as PACKET SEND. They do not call
   `Core_SendPacket`; they enqueue the `CommandPacketSend` stub directly
   (`Cmd_Guild.au3:9`, `:18`), so the packet is handed to the client's `PacketSend` *from inside the
   queued routine* (`Assembler:2088-2099`). Under the letter of the definitions this is also a
   GAME-THREAD CALL — the two categories coincide for every `Core_SendPacket` user as well, and the
   packet-send reading was chosen for consistency with those.
3. **`Chat_SendChat` / `Chat_SendWhisper`** — recorded as PACKET SEND for the same structural reason:
   the queue slot receives the `CommandSendChat` stub address plus `$GC_I_HEADER_SEND_CHAT`
   (`Cmd_Chat.au3:68-69`, `Const_Core.au3:12-13`, `GwAu3_Core.au3:453-454`), and that stub calls the
   client's `PacketSend` (`Assembler:2120-2131`). The stub is *not* `Core_SendPacket`, and the chat
   text is written at `slot + 12` while the stub passes `slot + 4` as the payload pointer with length
   `0x11C` — the source does not make the relationship between those two offsets explicit, so the
   exact payload layout is unresolved from the source alone.
4. **`Friend_GetFriendListPtr`** — recorded as PURE COMPUTATION because the call performs no game
   access (it returns the host global `$g_p_FriendList`, `Data_Friend.au3:8`). It could equally be
   filed as "state handed over from initialization"; the read that fills the global happened earlier,
   in `Core_Initialize` (`GwAu3_Core.au3:215-216`).
5. **`Friend_AddFriend` / `Friend_AddIgnore` return value** — the success path has no `Return`
   (`Cmd_Friend.au3:92-94`, `:166`) so success evaluates to 0 while every failure returns `False`.
   Recorded as written; `True` is never returned by `Friend_AddFriend`.

## Notes on the surface CSV

`external/GwAu3_modules_surface.csv` matches the source for all covered modules **except** that it
omits `PreGame_CharName` (`Data/GwAu3_Data_PreGame.au3:19`) — the CSV's last row for that file is
`PreGame_LoginCharacterArray` at line 15. Every other row checked (file, line, name, params)
agrees with the source. The counts above (70 functions) are source-derived, not CSV-derived.
