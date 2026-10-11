# GwAu3 mechanism map

Companion to `external/GwAu3_mechanism_map.json`, which classifies **every** `Func`
declaration in `external/GwAu3/API/Modules/**/*.au3` — **648 functions** across **41
files** (18 `Cmd` files, 183 functions; 23 `Data` files, 465 functions). The other 10
`.au3` files under `API/Modules` declare no `Func` (they are include stubs).

This is a **source-reading result**. Nothing here was produced against a running client,
and nothing here says anything about what the current Stealth client build does — GwAu3 is
historical/comparative material.

## The closed list

Each function gets exactly one primary `mechanism`, spelled exactly as below:

| mechanism | meaning used here |
| --- | --- |
| `MEMORY READ` | reads game memory (`Memory_Read`, `Memory_ReadPtr`, `ReadProcessMemory`, `Utils_DecodeEncString`), nothing else |
| `MEMORY WRITE` | writes into game memory (`Memory_Write`, `WriteProcessMemory`) |
| `PACKET SEND` | builds and sends a packet to the server: `Core_SendPacket`, a direct queue write whose first dword is the `CommandPacketSend`/`CommandSendChat` stub, or `$g_d_InviteGuild` |
| `GAME-THREAD CALL` | calls a native client function: `Core_Enqueue`/`Core_PerformAction`/`Core_ControlAction` with a slot holding a `Command*` stub **other than** `CommandPacketSend`/`CommandSendChat`, `Trade_CallSession`, `Utils_Decode*StringID` |
| `UI/INPUT SYNTHESIS` | `WinSetState`, `ControlSend`, `keybd_event`, `mouse_event`, `SendMessage`/`PostMessage` |
| `PURE COMPUTATION` | no game access at all (arithmetic, strings, sleeps, constant tables, host globals) |
| `OTHER` | anything else |

`alt_mechanism` is filled only when `ambiguous` is `true`. `via` names the primitive or
delegate the classification rests on, and `citation` names the one source line that decides
it (`file:line`, verified to exist and to be the line it claims to be).

## How the classification was made

1. Every `.au3` in `Modules` was split into function bodies by its `Func`/`EndFunc` pairs.
2. Each body was read for its own mechanism-bearing lines: `Core_SendPacket`,
   `Core_Enqueue`/`Core_Enqueue_`/`Core_PerformAction`/`Core_ControlAction` together with
   the slot's command name, `Memory_Read`/`Memory_ReadPtr`/`ReadProcessMemory`,
   `Memory_Write`/`WriteProcessMemory`, `WinSetState`, `Memory_Clear`, `VirtualAllocEx`,
   `Trade_CallSession`, `Utils_Decode*StringID`.
3. The slot's meaning was resolved in `API/Core/GwAu3_Core_Assembler.au3`: only
   `CommandPacketSend` (`:2088-2099`) and `CommandSendChat` (`:2120-2131`) call the
   client's `PacketSend`; every other `Command*` label is a stub that `call`s a native
   client function, so those slots are `GAME-THREAD CALL`.
4. A function with no mechanism of its own was classified by following its delegates —
   including the *literal info key* it passes to a `Switch`-based accessor: e.g.
   `Skill_GetSkillCampaign` (`Skill_GetSkillInfo(..., "Campaign")`, `GwAu3_Data_Skill.au3:305`)
   resolves to the `"Campaign"` case's `Memory_Read`, while `Agent_GetNpcInfoByAgentID`
   (which forwards its caller's `$a_s_Info` down to `Agent_GetNpcInfo`) can reach
   `Utils_DecodeEncStringAsync` at `GwAu3_Data_Agent.au3:1003` and is therefore ambiguous.
5. Every multi-mechanism function, every write, every input-synthesis function and every
   function that initially came out empty was then read by hand and decided explicitly; the
   `notes` field of those entries records the reasoning and the conflicting lines.

## Counts

| mechanism | functions | share |
| --- | ---: | ---: |
| `MEMORY READ` | 439 | 67.7% |
| `GAME-THREAD CALL` | 85 | 13.1% |
| `PACKET SEND` | 76 | 11.7% |
| `PURE COMPUTATION` | 37 | 5.7% |
| `MEMORY WRITE` | 9 | 1.4% |
| `UI/INPUT SYNTHESIS` | 2 | 0.3% |
| `OTHER` | **0** | 0% |
| **total** | **648** | |

The `MEMORY WRITE` nine: `Chat_WriteChat`, `Map_InitMapIsLoaded`, `Trade_InitTradePartner`,
`Ui_EnableRendering`, `Ui_DisableRendering`, `Agent_ResetTargetRejectStats`,
`Merchant_ClearTraderQuote`, `Ui_ToggleRendering_`, `Ui_PurgeHook_`.

The two `UI/INPUT SYNTHESIS` functions are the only ones in `Modules` that touch a window
at all: `Ui_ToggleRendering` (`WinSetState`, `GwAu3_Cmd_Ui.au3:250`) and `Ui_PurgeHook`
(it calls it). Nothing else in the 648 sends input: no `ControlSend`, `SendMessage`,
`PostMessage`, `keybd_event` or `mouse_event` appears in any module body.

The 37 `PURE COMPUTATION` functions are the constant-table, name-table, host-global and
sleep helpers — each one carries a note saying why it has no game access, and the notes fall
into these families: nine are name/label tables (`Friend_GetFriendStatusName`,
`Skill_GetProfessionName`, `Merchant_GetTransactionTypeName`, `Item_IsRuneOrInsignia`, …);
eight return one host-side AutoIt global (`Agent_GetAgentBase`, `Friend_GetFriendListPtr`,
`Merchant_GetBuyItemBase`, `Skill_GetLastUsedSkill`, `Skill_GetLastTarget`, …) — a host-side
global is not the client's memory, which is what the note says; four are plain arithmetic
and array work (`Attribute_CalculateAttributeSpread`, `Map_GetTrapezoid`,
`_Skill_ConvertScaleValue`, `Map_GetPathWithPortalCoords`); three return an *array* of
host-side globals (`Attribute_GetLastModified`, `Map_GetLastMoveCoords`,
`Merchant_GetLastTransaction`); three return a *computed address* without reading it
(`Attribute_GetAttributePtr`, `Map_GetAreaPtr`, `Skill_GetSkillPtr`); three are constant
coordinate/connection tables or searches over one (`Map_GetExitPortalsCoords`,
`Map_GetConnectedMaps`, `Map_FindMapPath`); three are hardcoded literal-id tests
(`Skill_InflictCA`, `Skill_RequireCA`, `Skill_BenefitWithCA`); two are the `Sleep` wrappers;
one is the host tick count (`Skill_GetSkillTimer`); one is string cleanup
(`Match_CleanTeamName`). Twelve of the 37 take no arguments at all.

## Ambiguous entries: 23

Every entry below uses two mechanisms in a way that is visible to a caller, so `ambiguous`
is `true` and `alt_mechanism` carries the other one.

| function | mechanism | alt | cited line |
| --- | --- | --- | --- |
| `Agent_TargetNearestEnemy` | `GAME-THREAD CALL` | `MEMORY READ` | `GwAu3_Cmd_Agent.au3:64` |
| `Agent_TargetNearestAlly` | `GAME-THREAD CALL` | `MEMORY READ` | `GwAu3_Cmd_Agent.au3:105` |
| `Agent_TargetNearestAnimal` | `GAME-THREAD CALL` | `MEMORY READ` | `GwAu3_Cmd_Agent.au3:146` |
| `Attribute_LoadSkillTemplate` | `GAME-THREAD CALL` | `PACKET SEND` | `GwAu3_Cmd_Attribute.au3:165` |
| `Chat_WriteChat` | `MEMORY WRITE` | *(none — see below)* | `GwAu3_Cmd_Chat.au3:29` |
| `Cinematic_WaitCinematic` | `PACKET SEND` | `MEMORY READ` | `GwAu3_Cmd_Cinematic.au3:22` |
| `Item_SalvageItem` | `PACKET SEND` | `GAME-THREAD CALL` | `GwAu3_Cmd_Item.au3:164` |
| `Ui_ToggleRendering` | `UI/INPUT SYNTHESIS` | `MEMORY WRITE` | `GwAu3_Cmd_Ui.au3:250` |
| `Ui_PurgeHook` | `UI/INPUT SYNTHESIS` | `MEMORY WRITE` | `GwAu3_Cmd_Ui.au3:262` |
| `Ui_ToggleRendering_` | `MEMORY WRITE` | `OTHER` | `GwAu3_Cmd_Ui.au3:270` |
| `Ui_PurgeHook_` | `MEMORY WRITE` | `OTHER` | `GwAu3_Cmd_Ui.au3:280` |
| `Agent_GetAgentInfo` | `MEMORY READ` | `GAME-THREAD CALL` | `GwAu3_Data_Agent.au3:88` |
| `Agent_GetNpcInfo` | `MEMORY READ` | `GAME-THREAD CALL` | `GwAu3_Data_Agent.au3:973` |
| `Agent_GetNpcInfoByAgentID` | `MEMORY READ` | `GAME-THREAD CALL` | `GwAu3_Data_Agent.au3:1013` |
| `Item_GetItemInfoByItemID` | `MEMORY READ` | `GAME-THREAD CALL` | `GwAu3_Data_Item.au3:554` |
| `Item_GetItemInfoByAgentID` | `MEMORY READ` | `GAME-THREAD CALL` | `GwAu3_Data_Item.au3:563` |
| `Item_GetItemInfoByModelID` | `MEMORY READ` | `GAME-THREAD CALL` | `GwAu3_Data_Item.au3:572` |
| `Item_GetItemInfoByPtr` | `MEMORY READ` | `GAME-THREAD CALL` | `GwAu3_Data_Item.au3:578` |
| `Party_GetPetInfo` | `MEMORY READ` | `GAME-THREAD CALL` | `GwAu3_Data_Party.au3:278` |
| `Quest_GetQuestInfo` | `MEMORY READ` | `GAME-THREAD CALL` | `GwAu3_Data_Quest.au3:27` |
| `Mission_GetObjectiveInfo` | `MEMORY READ` | `GAME-THREAD CALL` | `GwAu3_Data_Quest.au3:110` |
| `Skill_GetSkillInfo` | `MEMORY READ` | `GAME-THREAD CALL` | `GwAu3_Data_Skill.au3:28` |
| `Title_GetTitleInfo` | `MEMORY READ` | `GAME-THREAD CALL` | `GwAu3_Data_Title.au3:16` |

The twelve `*_Get*Info` accessors are ambiguous for one structural reason: the one
`$a_s_Info` argument selects between ordinary `Memory_Read` cases and a string case that
hands an encoded string to the client's own decoder on the game thread (for example
`Agent_GetAgentInfo`'s `"Name"` case reaches `Utils_DecodeEncStringAsync` at
`GwAu3_Data_Agent.au3:518`). A caller asking for `"Level"` gets a read; a caller asking for
`"Name"` gets a game-thread call. Neither dominates, so both are recorded.

## Classification decisions worth naming

- **`Agent_ClearTarget` is `GAME-THREAD CALL`, not `PACKET SEND`.** The task brief offered
  `Agent_ClearTarget → Agent_ChangeTarget → PACKET SEND` as the worked example of following
  a delegate. The delegate is followed, but the slot it uses is `$g_p_ChangeTarget`, whose
  command stub `CommandChangeTarget` (`GwAu3_Core_Assembler.au3:2438`) `call`s the client's
  own `ChangeTarget` (`:2464`) — it never calls `PacketSend`. Only `CommandPacketSend`
  (`:2088`) and `CommandSendChat` (`:2120`) do. `GwAu3_Cmd_Agent.au3:155-157` contains no
  `Core_SendPacket`. Per the brief's own definitions (a `Command*` stub other than
  `CommandPacketSend` is a game-thread call) this function is a `GAME-THREAD CALL`, and the
  same is true of every other `$g_p_*`/`$g_d_*` slot except `Packet`, `SendChat` and
  `InviteGuild`.
- **`Chat_WriteChat` is the one function whose *effect* could not be decided.**
  `GwAu3_Cmd_Chat.au3:4-32` writes sender and message into a command-queue slot
  (`Memory_Write` at `:20` and `:28`) and then copies the slot's command dword out of
  `$g_p_WriteChatPtr` (`:29`). That global is declared at `GwAu3_Const_Chat.au3:3` and
  assigned nowhere in the library, and no `WriteChat` command stub exists in
  `GwAu3_Core_Assembler.au3`. The **write** into the client's memory is certain, so the
  primary mechanism is `MEMORY WRITE`; whether the game thread would ever act on the slot
  cannot be determined from the source, so it is marked `ambiguous` with
  `alt_mechanism: null` and the conflicting lines named in `notes`. It was not pushed to
  `OTHER` because the mechanism itself is not in doubt — only its result is.
- **No entry ended in `OTHER` as a primary mechanism.** `Memory_Clear` is the only
  `OTHER`-class primitive in the modules (it is `SetProcessWorkingSetSize` on the client,
  `GwAu3_Core_Memory.au3:99`); it appears inside `Ui_ToggleRendering` and its variants,
  where a stronger mechanism always exists, so `OTHER` survives only as those entries'
  `alt_mechanism`.
- **Address arithmetic is not game access.** Several functions compute an address from a
  scanned host-side base (`$g_p_BasePointer`, `$g_p_SkillBase`, `$g_p_AreaInfo`, …) or from an
  argument and return it without reading it; those are `PURE COMPUTATION` and the note says so.
- **Reads that only feed a call are not treated as a second mechanism.** A function that
  polls a value to decide whether to act, or reads a value to build an argument, is
  classified by the action and says so in `notes`; it is not marked `ambiguous`. Reads that
  produce the *returned result* while the function also acts (the `Agent_TargetNearest*`
  family) are marked ambiguous.

## Functions that could not be classified

**None.** All 648 entries carry a primary mechanism from the closed list and a `citation`
that resolves to a real, non-empty source line. The only residual uncertainty is
`Chat_WriteChat`'s effect, described above.
