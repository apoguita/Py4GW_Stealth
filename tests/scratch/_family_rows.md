# The rows that have a ported home and no route yet

## ROUTED -- 45 rows

* `cmd_agent` (3): `Agent_TargetNearestAlly`, `Agent_TargetNearestAnimal`, `Agent_TargetNearestEnemy`
* `cmd_attribute` (1): `Attribute_LoadSkillTemplate`
* `cmd_chat` (1): `Chat_WriteChat`
* `cmd_friend` (4): `Friend_SetAwayStatus`, `Friend_SetDNDStatus`, `Friend_SetOfflineStatus`, `Friend_SetOnlineStatus`
* `cmd_game` (1): `Game_SwitchMode`
* `cmd_item` (6): `Item_DestroyItem`, `Item_DropGold`, `Item_DropItem`, `Item_EquipItem`, `Item_MoveItem`, `Item_UseItem`
* `cmd_map` (3): `Map_WaitMapIsLoaded`, `Map_WaitMapIsLoaded_Ping`, `Map_WaitMapLoading`
* `cmd_merchant` (2): `Merchant_GetMerchantItemPtr`, `Merchant_GetMerchantItemsSize`
* `cmd_other` (2): `Other_RndSleep`, `Other_TolSleep`
* `cmd_party` (2): `Party_AcceptInvitation`, `Party_RejectInvitation`
* `cmd_quest` (1): `Quest_AbandonQuest`
* `core` (1): `Core_Initialize`
* `data_agent` (5): `Agent_ConvertID`, `Agent_GetDistance`, `Agent_GetDistanceSq`, `Agent_GetDistanceToXY`, `_ApplyFilters`
* `data_friend` (6): `Friend_GetFriendListInfo`, `Friend_GetFriendStatusName`, `Friend_GetFriendTypeName`, `Friend_GetMyStatus`, `Friend_IsFriend`, `Friend_IsIgnored`
* `data_item` (5): `Item_GetBagInfo`, `Item_GetBagPtr`, `Item_GetItemInfoByPtr`, `Item_GetItemPtr`, `Item_ItemID`
* `data_map` (1): `Map_GetInstanceInfo`
* `data_party` (1): `Party_GetPetInfo`

## REFUSED -- 67 rows

* `cmd_agent` (1): `Agent_MakeAgentArray`
* `cmd_attribute` (4): `Attribute_CalculateAttributeSpread`, `Attribute_DecreaseAttribute`, `Attribute_IncreaseAttribute`, `Attribute_LoadAttributes`
* `cmd_friend` (4): `Friend_AddFriend`, `Friend_AddIgnore`, `Friend_RemoveFriend`, `Friend_RemoveIgnore`
* `cmd_item` (8): `Item_ApplyUpgrade`, `Item_CanDepositAllMaterials`, `Item_CanIdentifyAll`, `Item_DepositAllMaterials`, `Item_DropBundle`, `Item_IdentifyAll`, `Item_OpenChest`, `Item_SwitchWeaponSet`
* `cmd_map` (1): `Map_InitMapIsLoaded`
* `cmd_merchant` (5): `Merchant_BuyItem`, `Merchant_CollectorExchange`, `Merchant_CraftItem`, `Merchant_GetMerchantItemsBase`, `Merchant_SellItem`
* `cmd_other` (2): `Other_PingSleep`, `Other_WaitPingStabilized`
* `cmd_party` (4): `Party_AddPlayer`, `Party_KickInvitedPlayer`, `Party_KickPlayer`, `Party_LockHeroTarget`
* `cmd_quest` (2): `Quest_AcceptQuest`, `Quest_QuestReward`
* `cmd_skill` (1): `Skill_CancelHeroSkill`
* `cmd_trade` (11): `Trade_AcceptTrade`, `Trade_CallSession`, `Trade_CancelTrade`, `Trade_InitiateTrade`, `Trade_OfferItem`, `Trade_OfferItem_`, `Trade_RevokeAccept`, `Trade_RevokeItem`, `Trade_RevokeOffer`, `Trade_SubmitOffer`, `Trade_WaitIdle`
* `cmd_ui` (16): `Ui_AboutQuest`, `Ui_AcceptQuest`, `Ui_ActivateDhuumsCovenant`, `Ui_ActivateReforgedMode`, `Ui_ActiveQuest`, `Ui_CloseDialog`, `Ui_DeactivateDhuumsCovenant`, `Ui_DeactivateReforgedMode`, `Ui_DropHeroBundle`, `Ui_EquipItem`, `Ui_LockHeroTarget`, `Ui_MoveMap`, `Ui_OpenChest`, `Ui_RewardQuest`, `Ui_UpdateQuest`, `Ui_Xunlai`
* `core` (7): `Core_ControlAction`, `Core_Enqueue`, `Core_GetInGameStatus`, `Core_GetLoginStatus`, `Core_GetStatusCode`, `Core_PerformAction`, `Core_SendPacket`
* `data_friend` (1): `Friend_GetFriendListPtr`

## NOT APPLICABLE -- 5 rows

* `cmd_trade` (2): `Trade_GetTradePartner`, `Trade_InitTradePartner`
* `cmd_ui` (3): `Ui_EnableRendering`, `Ui_PurgeHook_`, `Ui_ToggleRendering_`
