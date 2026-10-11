# How close a GwAu3 script is to running on this layer

**Generated** by `python tools/analyze_gwa3_example_parity.py` — do not edit by hand.

This is the measurement behind the layer's stated purpose: *GwAu3 supplies the names and the usage; this project supplies the implementation*. It reads GwAu3's own scripts from `external/GwAu3/Scripts/`, counts what they call, and resolves every name against this layer's surface. It is a **static** measurement: it says what would resolve, not what works. What works is the route map's per-function tier and the live run's evidence.

## The two surfaces

| | Count |
| --- | --- |
| Functions GwAu3 declares (`external/GwAu3/API/**/*.au3`) | 5685 |
| `$GC_*` constants this layer defines (`py4gw/gwa3/constants.py`) | 7373 |
| Names this layer's Python modules export | 12582 |
| AutoIt wrappers `tools/autoit/Stealth_GwAu3.au3` declares | 5645 |
| — of those, **implemented** | **5114** |

## What the scripts call

| Script | Lines | Distinct calls | Call sites | Routines implemented | Call sites implemented | Constants used | Constants defined | Lines unchanged by migration |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Scripts/Exemples/Exemple_AutoitGUI_Tester.au3` | 162 | 7 | 12 | 7 | 12 | 6 | 6 | 161/162 |
| `Scripts/Exemples/Exemple_AutoitGUI_Tester_stealth.au3` | 171 | 7 | 12 | 7 | 12 | 6 | 6 | 171/171 |
| `Scripts/Exemples/Exemple_ImGUI_Tester.au3` | 454 | 6 | 29 | 6 | 29 | 8 | 8 | 453/454 |
| `Scripts/Exemples/Exemple_ImGUI_Tester_stealth.au3` | 463 | 6 | 29 | 6 | 29 | 8 | 8 | 463/463 |
| `Scripts/Exemples/Exemple_PathFinding.au3` | 351 | 9 | 19 | 9 | 19 | 6 | 4 | 350/351 |
| `Scripts/Exemples/Exemple_PathFinding_stealth.au3` | 360 | 9 | 19 | 9 | 19 | 6 | 4 | 360/360 |
| `Scripts/Exemples/Punch_Out_Farm.au3` | 825 | 35 | 86 | 35 | 86 | 30 | 29 | 824/825 |
| `Scripts/Exemples/Punch_Out_Farm_stealth.au3` | 833 | 35 | 86 | 35 | 86 | 30 | 29 | 833/833 |
| `Scripts/Multi-Launcher/GwAu3 Multi-Launcher.au3` | 2697 | 0 | 0 | 0 | 0 | 0 | 0 | 2696/2697 |
| `Scripts/Multi-Launcher/GwAu3 Multi-Launcher_stealth.au3` | 2704 | 0 | 0 | 0 | 0 | 0 | 0 | 2704/2704 |
| `Scripts/Tools/GwAu3_DevTools.au3` | 3658 | 214 | 1612 | 214 | 1612 | 10 | 10 | 3657/3658 |
| `Scripts/Tools/GwAu3_DevTools_stealth.au3` | 3667 | 214 | 1612 | 214 | 1612 | 10 | 10 | 3667/3667 |
| `Scripts/Tools/Tools_VisibleEffect.au3` | 624 | 18 | 33 | 18 | 33 | 0 | 0 | 623/624 |
| `Scripts/Tools/Tools_VisibleEffect_stealth.au3` | 633 | 18 | 33 | 18 | 33 | 0 | 0 | 633/633 |

## The number that matters

Across every script in `external/GwAu3/Scripts/`, **243 distinct GwAu3 routines** are called, in **3582 call sites**. This layer implements **243 of those 243 routines** (100.0%), covering **3582 of 3582 call sites** (100.0%). Of the **46 distinct `$GC_*` constants** they use, this layer defines **43 (93.5%)**.

**Text parity is high and that is by construction, not by achievement.** A migration edits the `#include` and nothing else, so nearly every line is identical -- that is precisely what keeping GwAu3's names and argument order buys. A script can be pointed at this layer, load, and call routines that are not built yet; those calls set `@error` and return GwAu3's empty shape. **Text parity is not call parity**, and call parity is the table above.

## What the scripts call that this layer does not answer

Grouped by what the routines are, because the groups are the work in different sizes. The `Cmd_*` and `Data_*` families are the layer's declared scope; the framework groups below are **not in it yet** and are what a real script reaches for first.

| Prefix | Call sites not answered |
| --- | --- |

## The wrapper surface a migration needs before a script will even load

AutoIt resolves function names when it compiles a script, and a call to a function that is declared **nowhere** is a **fatal error, not a call that returns zero** — measured: `tools/autoit/probe_undeclared_call.au3` calls `Core_Initialize` and the interpreter answers `Unknown function name.` and exits 1 without running the file (`tools/autoit/READINGS.md`). So a migration needs a wrapper to *exist* for every GwAu3 function a script calls, whether or not this layer can answer it: a declared wrapper returns GwAu3's empty shape and sets `@error` with the reason, which a script can act on; an undeclared one stops the script cold.

| | Count |
| --- | --- |
| GwAu3 functions the whole checkout calls | 667 |
| — declared by this layer's UDF | 667 |
| — **called and not declared at all** | **0** |

| Prefix | Named and not declared |
| --- | --- |

## Constants the scripts use that this layer does not define

| Constant | Declared by GwAu3? |
| --- | --- |
| `$GC_B_LOAD_LOGGED_CHARS` | **no** — a dangling use in GwAu3 itself, so there is nothing to copy |
| `$GC_S_BOT_TITLE` | **no** — a dangling use in GwAu3 itself, so there is nothing to copy |
| `$GC_S_CHARACTERS_INI_PATH` | **no** — a dangling use in GwAu3 itself, so there is nothing to copy |

All of them are **used by GwAu3's own scripts and declared nowhere in its API**: they are dangling references in the source, not names this layer dropped. Defining them here would invent a value GwAu3 never states, which is the one thing this layer will not do.

### `Scripts/Exemples/Exemple_AutoitGUI_Tester.au3`

* **Implemented (7):** `Agent_GetAgentInfo`, `Cache_SkillBar`, `Core_AutoStart`, `Core_Initialize`, `Log_SetDebugMode`, `Scanner_GetLoggedCharNames`, `UAI_Fight`
* **Declared but not built (0):** —
* **Not in this layer's UDF at all (0):** —

### `Scripts/Exemples/Exemple_AutoitGUI_Tester_stealth.au3`

* **Implemented (7):** `Agent_GetAgentInfo`, `Cache_SkillBar`, `Core_AutoStart`, `Core_Initialize`, `Log_SetDebugMode`, `Scanner_GetLoggedCharNames`, `UAI_Fight`
* **Declared but not built (0):** —
* **Not in this layer's UDF at all (0):** —

### `Scripts/Exemples/Exemple_ImGUI_Tester.au3`

* **Implemented (6):** `Core_AutoStart`, `Core_Initialize`, `Log_Message`, `Log_SetCallback`, `Log_SetDebugMode`, `Scanner_GetLoggedCharNames`
* **Declared but not built (0):** —
* **Not in this layer's UDF at all (0):** —

### `Scripts/Exemples/Exemple_ImGUI_Tester_stealth.au3`

* **Implemented (6):** `Core_AutoStart`, `Core_Initialize`, `Log_Message`, `Log_SetCallback`, `Log_SetDebugMode`, `Scanner_GetLoggedCharNames`
* **Declared but not built (0):** —
* **Not in this layer's UDF at all (0):** —

### `Scripts/Exemples/Exemple_PathFinding.au3`

* **Implemented (9):** `Agent_GetAgentInfo`, `Core_AutoStart`, `Core_Initialize`, `Log_SetDebugMode`, `Map_GetMapID`, `Map_Move`, `Pathfinder_Initialize`, `Pathfinder_IsMapAvailable`, `Scanner_GetLoggedCharNames`
* **Declared but not built (0):** —
* **Not in this layer's UDF at all (0):** —

### `Scripts/Exemples/Exemple_PathFinding_stealth.au3`

* **Implemented (9):** `Agent_GetAgentInfo`, `Core_AutoStart`, `Core_Initialize`, `Log_SetDebugMode`, `Map_GetMapID`, `Map_Move`, `Pathfinder_Initialize`, `Pathfinder_IsMapAvailable`, `Scanner_GetLoggedCharNames`
* **Declared but not built (0):** —
* **Not in this layer's UDF at all (0):** —

### `Scripts/Exemples/Punch_Out_Farm.au3`

* **Implemented (35):** `Agent_ChangeTarget`, `Agent_GetAgentInfo`, `Agent_GetAgentPtr`, `Agent_GetDistanceToXY`, `Agent_GetMaxAgents`, `Agent_GoNPC`, `Agent_GoSignpost`, `Core_Initialize`, `Game_Dialog`, `Game_SwitchMode`, `Item_GetBagInfo`, `Item_GetBagItemArray`, `Item_GetBagPtr`, `Item_GetInventoryArray`, `Item_GetItemArray`, `Item_GetItemInfoByPtr`, `Item_IdentifyItem`, `Map_GetCharacterInfo`, `Map_GetInstanceInfo`, `Map_MoveLayer`, `Map_RndTravel`, `Map_TravelTo`, `Map_WaitMapLoading`, `Merchant_BuyItem`, `Merchant_SellItem`, `Party_GetPartyContextInfo`, `Party_KickAllHeroes`, `PreGame_CharName`, `PreGame_ChosenCharacter`, `PreGame_Ptr`, `Quest_GetQuestInfo`, `Scanner_GetHwnd`, `UAI_CacheSkillBar`, `Ui_DisableRendering`, `Ui_EnableRendering`
* **Declared but not built (0):** —
* **Not in this layer's UDF at all (0):** —

### `Scripts/Exemples/Punch_Out_Farm_stealth.au3`

* **Implemented (35):** `Agent_ChangeTarget`, `Agent_GetAgentInfo`, `Agent_GetAgentPtr`, `Agent_GetDistanceToXY`, `Agent_GetMaxAgents`, `Agent_GoNPC`, `Agent_GoSignpost`, `Core_Initialize`, `Game_Dialog`, `Game_SwitchMode`, `Item_GetBagInfo`, `Item_GetBagItemArray`, `Item_GetBagPtr`, `Item_GetInventoryArray`, `Item_GetItemArray`, `Item_GetItemInfoByPtr`, `Item_IdentifyItem`, `Map_GetCharacterInfo`, `Map_GetInstanceInfo`, `Map_MoveLayer`, `Map_RndTravel`, `Map_TravelTo`, `Map_WaitMapLoading`, `Merchant_BuyItem`, `Merchant_SellItem`, `Party_GetPartyContextInfo`, `Party_KickAllHeroes`, `PreGame_CharName`, `PreGame_ChosenCharacter`, `PreGame_Ptr`, `Quest_GetQuestInfo`, `Scanner_GetHwnd`, `UAI_CacheSkillBar`, `Ui_DisableRendering`, `Ui_EnableRendering`
* **Declared but not built (0):** —
* **Not in this layer's UDF at all (0):** —

### `Scripts/Multi-Launcher/GwAu3 Multi-Launcher.au3`

Calls no GwAu3 API function: it is a standalone launcher that does not include the API module. Nothing to migrate.

### `Scripts/Multi-Launcher/GwAu3 Multi-Launcher_stealth.au3`

Calls no GwAu3 API function: it is a standalone launcher that does not include the API module. Nothing to migrate.

### `Scripts/Tools/GwAu3_DevTools.au3`

* **Implemented (214):** `Account_GetAccountContextPtr`, `Account_GetAccountInfo`, `Account_IsSkillUnlocked`, `Agent_Attack`, `Agent_CallTarget`, `Agent_CancelAction`, `Agent_ChangeTarget`, `Agent_ClearTarget`, `Agent_GetAgentBondInfo`, `Agent_GetAgentEffectInfo`, `Agent_GetAgentInfo`, `Agent_GetBestTarget`, `Agent_GetCurrentTarget`, `Agent_GetMyID`, `Agent_GetNpcInfo`, `Agent_GetPlayerInfo`, `Agent_GoNPC`, `Agent_GoPlayer`, `Agent_GoSignpost`, `Agent_TargetNearestAlly`, `Agent_TargetNearestEnemy`, `Agent_TargetSelf`, `Attribute_ChangeSecondProfession`, `Attribute_DecreaseAttribute`, `Attribute_GetAttributeInfo`, `Attribute_GetAttributeName`, `Attribute_GetLastModified`, `Attribute_GetPartyAttributeInfo`, `Attribute_GetProfPrimaryAttribute`, `Attribute_IncreaseAttribute`, `Attribute_LoadSkillTemplate`, `Chat_SendChat`, `Chat_SendWhisper`, `Chat_WriteChat`, `Cinematic_SkipCinematic`, `Core_ControlAction`, `Core_Enqueue`, `Core_Initialize`, `Core_SendPacket`, `Effect_DropBond`, `Effect_GetEffectArg`, `Friend_AddFriend`, `Friend_GetFriendInfo`, `Friend_GetFriendListInfo`, `Friend_GetFriendListPtr`, `Friend_GetMyStatus`, `Friend_IsFriend`, `Friend_IsIgnored`, `Friend_RemoveFriend`, `Friend_SetPlayerStatus`, `Game_Dialog`, `Game_DonateFaction`, `Game_GetGameContextPtr`, `Game_GetGameInfo`, `Game_SwitchMode`, `Guild_GetGuildContextPtr`, `Guild_GetGuildPlayerInfo`, `Guild_GetMyGuildInfo`, `Guild_InviteGuest`, `Guild_InviteGuild`, `Item_AcceptAllItems`, `Item_DestroyItem`, `Item_DropGold`, `Item_DropItem`, `Item_EquipItem`, `Item_FindItemByModelID`, `Item_GetBagInfo`, `Item_GetInventoryInfo`, `Item_GetInventoryPtr`, `Item_GetItemBySlot`, `Item_GetItemContextPtr`, `Item_GetItemInfoByItemID`, `Item_GetMaxItems`, `Item_IdentifyItem`, `Item_MoveItem`, `Item_OpenChest`, `Item_PickUpItem`, `Item_SalvageItem`, `Item_SwitchWeaponSet`, `Item_UseItem`, `Log_Message`, `Log_SetCallback`, `Log_SetDebugMode`, `Map_EnterChallenge`, `Map_GetAreaInfo`, `Map_GetCharacterInfo`, `Map_GetClickCoords`, `Map_GetCurrentAreaInfo`, `Map_GetCurrentRegionType`, `Map_GetInstanceInfo`, `Map_GetInstanceUpTime`, `Map_GetLastMoveCoords`, `Map_GetMapContextInfo`, `Map_GetMapContextPtr`, `Map_GetMapID`, `Map_GetPathingMapArrayInfo`, `Map_GetPropsContext`, `Map_GetRegion`, `Map_GetTotalTrapezoidCount`, `Map_IsMapUnlocked`, `Map_LeaveGH`, `Map_Move`, `Map_ReturnToOutpost`, `Map_TravelGH`, `Map_TravelTo`, `Match_GetObserverMatchInfo`, `Merchant_BuyItem`, `Merchant_ClearTraderQuote`, `Merchant_CollectorExchange`, `Merchant_GetBuyItemBase`, `Merchant_GetLastTransaction`, `Merchant_GetSalvageGlobal`, `Merchant_GetTraderCostID`, `Merchant_GetTraderCostValue`, `Merchant_GetTraderQuoteID`, `Merchant_GetTraderQuoteInfo`, `Merchant_IsValidQuote`, `Merchant_SellItem`, `Party_AddHero`, `Party_AddNpc`, `Party_CancelAll`, `Party_CancelHero`, `Party_CommandAll`, `Party_CommandHero`, `Party_GetControlledMinionsInfo`, `Party_GetHeroFlagInfo`, `Party_GetHeroInfo`, `Party_GetMoraleInfo`, `Party_GetMyPartyHenchmanInfo`, `Party_GetMyPartyHeroInfo`, `Party_GetMyPartyInfo`, `Party_GetMyPartyPlayerMemberInfo`, `Party_GetPartyContextInfo`, `Party_GetPartyContextPtr`, `Party_GetPetInfo`, `Party_IsPet`, `Party_KickAllHeroes`, `Party_KickHero`, `Party_KickNpc`, `Party_LeaveGroup`, `Party_LockHeroTarget`, `Party_SetHeroAggression`, `Party_ToggleHeroSkillState`, `PreGame_CharName`, `PreGame_ChosenCharacter`, `PreGame_FrameID`, `PreGame_LoginCharacterArray`, `PreGame_Ptr`, `Quest_AbandonQuest`, `Quest_AcceptQuest`, `Quest_GetQuestInfo`, `Quest_QuestReward`, `Scanner_GetLoggedCharNames`, `Skill_BuySkillByID`, `Skill_CancelHeroSkill`, `Skill_GetSkillInfo`, `Skill_GetSkillbarInfo`, `Skill_LoadSkillBar`, `Skill_SetSkillbarSkill`, `Skill_SkillForQuest`, `Skill_UnlockSkillBossByID`, `Skill_UnlockSkillByID`, `Skill_UnlockTomeSkillByID`, `Skill_UseHeroSkill`, `Skill_UseSkill`, `Title_GetTitleInfo`, `Title_SetDisplayedTitle`, `Trade_AcceptTrade`, `Trade_AcceptTrade_`, `Trade_CancelTrade`, `Trade_CancelTrade_`, `Trade_ChangeOffer_`, `Trade_GetArrayPartnerTradeItems`, `Trade_GetArrayPlayerTradeItems`, `Trade_GetPartnerTradeItemsInfo`, `Trade_GetPlayerTradeItemsInfo`, `Trade_GetTradeInfo`, `Trade_GetTradePtr`, `Trade_InitiateTrade`, `Trade_InitiateTrade_`, `Trade_OfferItem`, `Trade_OfferItem_`, `Trade_SubmitOffer`, `Trade_SubmitOffer_`, `Ui_AddHero`, `Ui_AddNPC`, `Ui_CancelAll`, `Ui_CancelHero`, `Ui_CommandAll`, `Ui_CommandHero`, `Ui_Dialog`, `Ui_DisableHeroSkill`, `Ui_DisableRendering`, `Ui_DropHeroBundle`, `Ui_EnableHeroSkill`, `Ui_EnableRendering`, `Ui_EnterChallenge`, `Ui_GetRenderDisabled`, `Ui_GetRenderEnabled`, `Ui_KickAllHeroes`, `Ui_KickHero`, `Ui_KickNPC`, `Ui_LeaveGroup`, `Ui_LockHeroTarget`, `Ui_OpenChest`, `Ui_PurgeHook`, `Ui_SetDifficulty`, `Ui_SetHeroBehavior`, `Ui_ToggleHeroSkillState`, `Ui_ToggleRendering`, `World_GetSkillDuplicateCount`, `World_GetWorldContextPtr`, `World_GetWorldInfo`, `World_IsSkillLearnt`
* **Declared but not built (0):** —
* **Not in this layer's UDF at all (0):** —

### `Scripts/Tools/GwAu3_DevTools_stealth.au3`

* **Implemented (214):** `Account_GetAccountContextPtr`, `Account_GetAccountInfo`, `Account_IsSkillUnlocked`, `Agent_Attack`, `Agent_CallTarget`, `Agent_CancelAction`, `Agent_ChangeTarget`, `Agent_ClearTarget`, `Agent_GetAgentBondInfo`, `Agent_GetAgentEffectInfo`, `Agent_GetAgentInfo`, `Agent_GetBestTarget`, `Agent_GetCurrentTarget`, `Agent_GetMyID`, `Agent_GetNpcInfo`, `Agent_GetPlayerInfo`, `Agent_GoNPC`, `Agent_GoPlayer`, `Agent_GoSignpost`, `Agent_TargetNearestAlly`, `Agent_TargetNearestEnemy`, `Agent_TargetSelf`, `Attribute_ChangeSecondProfession`, `Attribute_DecreaseAttribute`, `Attribute_GetAttributeInfo`, `Attribute_GetAttributeName`, `Attribute_GetLastModified`, `Attribute_GetPartyAttributeInfo`, `Attribute_GetProfPrimaryAttribute`, `Attribute_IncreaseAttribute`, `Attribute_LoadSkillTemplate`, `Chat_SendChat`, `Chat_SendWhisper`, `Chat_WriteChat`, `Cinematic_SkipCinematic`, `Core_ControlAction`, `Core_Enqueue`, `Core_Initialize`, `Core_SendPacket`, `Effect_DropBond`, `Effect_GetEffectArg`, `Friend_AddFriend`, `Friend_GetFriendInfo`, `Friend_GetFriendListInfo`, `Friend_GetFriendListPtr`, `Friend_GetMyStatus`, `Friend_IsFriend`, `Friend_IsIgnored`, `Friend_RemoveFriend`, `Friend_SetPlayerStatus`, `Game_Dialog`, `Game_DonateFaction`, `Game_GetGameContextPtr`, `Game_GetGameInfo`, `Game_SwitchMode`, `Guild_GetGuildContextPtr`, `Guild_GetGuildPlayerInfo`, `Guild_GetMyGuildInfo`, `Guild_InviteGuest`, `Guild_InviteGuild`, `Item_AcceptAllItems`, `Item_DestroyItem`, `Item_DropGold`, `Item_DropItem`, `Item_EquipItem`, `Item_FindItemByModelID`, `Item_GetBagInfo`, `Item_GetInventoryInfo`, `Item_GetInventoryPtr`, `Item_GetItemBySlot`, `Item_GetItemContextPtr`, `Item_GetItemInfoByItemID`, `Item_GetMaxItems`, `Item_IdentifyItem`, `Item_MoveItem`, `Item_OpenChest`, `Item_PickUpItem`, `Item_SalvageItem`, `Item_SwitchWeaponSet`, `Item_UseItem`, `Log_Message`, `Log_SetCallback`, `Log_SetDebugMode`, `Map_EnterChallenge`, `Map_GetAreaInfo`, `Map_GetCharacterInfo`, `Map_GetClickCoords`, `Map_GetCurrentAreaInfo`, `Map_GetCurrentRegionType`, `Map_GetInstanceInfo`, `Map_GetInstanceUpTime`, `Map_GetLastMoveCoords`, `Map_GetMapContextInfo`, `Map_GetMapContextPtr`, `Map_GetMapID`, `Map_GetPathingMapArrayInfo`, `Map_GetPropsContext`, `Map_GetRegion`, `Map_GetTotalTrapezoidCount`, `Map_IsMapUnlocked`, `Map_LeaveGH`, `Map_Move`, `Map_ReturnToOutpost`, `Map_TravelGH`, `Map_TravelTo`, `Match_GetObserverMatchInfo`, `Merchant_BuyItem`, `Merchant_ClearTraderQuote`, `Merchant_CollectorExchange`, `Merchant_GetBuyItemBase`, `Merchant_GetLastTransaction`, `Merchant_GetSalvageGlobal`, `Merchant_GetTraderCostID`, `Merchant_GetTraderCostValue`, `Merchant_GetTraderQuoteID`, `Merchant_GetTraderQuoteInfo`, `Merchant_IsValidQuote`, `Merchant_SellItem`, `Party_AddHero`, `Party_AddNpc`, `Party_CancelAll`, `Party_CancelHero`, `Party_CommandAll`, `Party_CommandHero`, `Party_GetControlledMinionsInfo`, `Party_GetHeroFlagInfo`, `Party_GetHeroInfo`, `Party_GetMoraleInfo`, `Party_GetMyPartyHenchmanInfo`, `Party_GetMyPartyHeroInfo`, `Party_GetMyPartyInfo`, `Party_GetMyPartyPlayerMemberInfo`, `Party_GetPartyContextInfo`, `Party_GetPartyContextPtr`, `Party_GetPetInfo`, `Party_IsPet`, `Party_KickAllHeroes`, `Party_KickHero`, `Party_KickNpc`, `Party_LeaveGroup`, `Party_LockHeroTarget`, `Party_SetHeroAggression`, `Party_ToggleHeroSkillState`, `PreGame_CharName`, `PreGame_ChosenCharacter`, `PreGame_FrameID`, `PreGame_LoginCharacterArray`, `PreGame_Ptr`, `Quest_AbandonQuest`, `Quest_AcceptQuest`, `Quest_GetQuestInfo`, `Quest_QuestReward`, `Scanner_GetLoggedCharNames`, `Skill_BuySkillByID`, `Skill_CancelHeroSkill`, `Skill_GetSkillInfo`, `Skill_GetSkillbarInfo`, `Skill_LoadSkillBar`, `Skill_SetSkillbarSkill`, `Skill_SkillForQuest`, `Skill_UnlockSkillBossByID`, `Skill_UnlockSkillByID`, `Skill_UnlockTomeSkillByID`, `Skill_UseHeroSkill`, `Skill_UseSkill`, `Title_GetTitleInfo`, `Title_SetDisplayedTitle`, `Trade_AcceptTrade`, `Trade_AcceptTrade_`, `Trade_CancelTrade`, `Trade_CancelTrade_`, `Trade_ChangeOffer_`, `Trade_GetArrayPartnerTradeItems`, `Trade_GetArrayPlayerTradeItems`, `Trade_GetPartnerTradeItemsInfo`, `Trade_GetPlayerTradeItemsInfo`, `Trade_GetTradeInfo`, `Trade_GetTradePtr`, `Trade_InitiateTrade`, `Trade_InitiateTrade_`, `Trade_OfferItem`, `Trade_OfferItem_`, `Trade_SubmitOffer`, `Trade_SubmitOffer_`, `Ui_AddHero`, `Ui_AddNPC`, `Ui_CancelAll`, `Ui_CancelHero`, `Ui_CommandAll`, `Ui_CommandHero`, `Ui_Dialog`, `Ui_DisableHeroSkill`, `Ui_DisableRendering`, `Ui_DropHeroBundle`, `Ui_EnableHeroSkill`, `Ui_EnableRendering`, `Ui_EnterChallenge`, `Ui_GetRenderDisabled`, `Ui_GetRenderEnabled`, `Ui_KickAllHeroes`, `Ui_KickHero`, `Ui_KickNPC`, `Ui_LeaveGroup`, `Ui_LockHeroTarget`, `Ui_OpenChest`, `Ui_PurgeHook`, `Ui_SetDifficulty`, `Ui_SetHeroBehavior`, `Ui_ToggleHeroSkillState`, `Ui_ToggleRendering`, `World_GetSkillDuplicateCount`, `World_GetWorldContextPtr`, `World_GetWorldInfo`, `World_IsSkillLearnt`
* **Declared but not built (0):** —
* **Not in this layer's UDF at all (0):** —

### `Scripts/Tools/Tools_VisibleEffect.au3`

* **Implemented (18):** `Agent_GetAgentArray`, `Agent_GetAgentInfo`, `Agent_GetAgentPtr`, `Agent_GetCurrentTarget`, `Agent_GetDistance`, `Agent_GetMyID`, `Core_AutoStart`, `Core_Initialize`, `Memory_Read`, `Memory_ReadPtr`, `Scanner_GetLoggedCharNames`, `Utils_TLink_IsLinked`, `Utils_TList_CreateIterator`, `Utils_TList_Iterator_Current`, `Utils_TList_Iterator_Next`, `VisibleEffect_Count`, `VisibleEffect_FindByID`, `VisibleEffect_GetAll`
* **Declared but not built (0):** —
* **Not in this layer's UDF at all (0):** —

### `Scripts/Tools/Tools_VisibleEffect_stealth.au3`

* **Implemented (18):** `Agent_GetAgentArray`, `Agent_GetAgentInfo`, `Agent_GetAgentPtr`, `Agent_GetCurrentTarget`, `Agent_GetDistance`, `Agent_GetMyID`, `Core_AutoStart`, `Core_Initialize`, `Memory_Read`, `Memory_ReadPtr`, `Scanner_GetLoggedCharNames`, `Utils_TLink_IsLinked`, `Utils_TList_CreateIterator`, `Utils_TList_Iterator_Current`, `Utils_TList_Iterator_Next`, `VisibleEffect_Count`, `VisibleEffect_FindByID`, `VisibleEffect_GetAll`
* **Declared but not built (0):** —
* **Not in this layer's UDF at all (0):** —

