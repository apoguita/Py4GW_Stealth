import re, sys
M = {
 "kCalledTargetChange":(0x10000115,0x10000116),"kErrorMessage":(0x10000119,0x1000011A),
 "kPartyHardModeChanged":(0x1000011A,0x1000011B),"kPartyAddHenchman":(0x1000011B,0x1000011C),
 "kPartyRemoveHenchman":(0x1000011C,0x1000011D),"kPartyAddHero":(0x1000011E,0x1000011F),
 "kPartyRemoveHero":(0x1000011F,0x10000120),"kPartyAddPlayer":(0x10000124,0x10000125),
 "kPartyRemovePlayer":(0x10000126,0x10000127),"kDisableEnterMissionBtn":(0x1000012A,0x1000012B),
 "kShowCancelEnterMissionBtn":(0x1000012D,0x1000012E),"kPartyDefeated":(0x1000012F,0x10000130),
 "kPartySearchInviteReceived":(0x10000137,0x10000138),"kPartySearchInviteSent":(0x10000139,0x1000013A),
 "kPartyShowConfirmDialog":(0x1000013A,0x1000013B),"kPreferenceEnumChanged":(0x10000140,0x10000141),
 "kPreferenceFlagChanged":(0x10000141,0x10000142),"kPreferenceValueChanged":(0x10000142,0x10000143),
 "kUIPositionChanged":(0x10000143,0x10000144),"kPreBuildLoginScene":(0x10000144,0x10000145),
 "kQuestAdded":(0x1000014E,0x10000150),"kQuestDetailsChanged":(0x1000014F,0x10000151),
 "kQuestRemoved":(0x10000150,0x10000152),"kClientActiveQuestChanged":(0x10000151,0x10000153),
 "kServerActiveQuestChanged":(0x10000153,0x10000155),"kUnknownQuestRelated":(0x10000154,0x10000156),
 "kDungeonComplete":(0x10000156,0x10000158),"kMissionComplete":(0x10000157,0x10000159),
 "kVanquishComplete":(0x10000159,0x1000015B),"kObjectiveAdd":(0x1000015A,0x1000015C),
 "kObjectiveComplete":(0x1000015B,0x1000015D),"kObjectiveUpdated":(0x1000015C,0x1000015E),
 "kTradeSessionStart":(0x10000165,0x10000167),"kTradeSessionUpdated":(0x1000016b,0x1000016D),
 "kTriggerLogoutPrompt":(0x1000016E,0x10000170),"kToggleOptionsWindow":(0x1000016F,0x10000171),
 "kRedrawItem":(0x10000174,0x10000176),"kCheckUIState":(0x10000176,0x10000178),
 "kCloseSettings":(0x10000177,0x10000179),"kChangeSettingsTab":(0x10000178,0x1000017A),
 "kDestroyUIPositionOverlay":(0x1000017D,0x1000017F),"kEnableUIPositionOverlay":(0x1000017E,0x10000180),
 "kGuildHall":(0x10000180,0x10000183),"kLeaveGuildHall":(0x10000182,0x10000185),
 "kTravel":(0x10000183,0x10000186),"kOpenWikiUrl":(0x10000184,0x10000187),
 "kSetPreGameContext_Value0":(0x10000187,0x1000018A),"kGetPreGameContext_Value0":(0x10000189,0x1000018C),
 "kSetPreGameContext_Value1":(0x1000018A,0x1000018D),"kGetPreGameContext_Value1":(0x1000018B,0x1000018E),
 "kAppendMessageToChat":(0x10000194,0x10000197),"kHideHeroPanel":(0x100001A2,0x100001A5),
 "kShowHeroPanel":(0x100001A3,0x100001A6),"kGetInventoryAgentId":(0x100001A7,0x100001AA),
 "kInventoryRelated1":(0x100001A8,0x100001AB),"kInventoryRelated2":(0x100001A9,0x100001AC),
 "kInventoryRelated3":(0x100001AA,0x100001AD),"kEquipItem":(0x100001AB,0x100001AE),
 "kMoveItem":(0x100001AC,0x100001AF),"kItemRelated_1":(0x100001AD,0x100001B0),
 "kItemTooltip":(0x100001AE,0x100001B1),"kItemRelated_3":(0x100001AF,0x100001B2),
 "kItemRelated_4":(0x100001B0,0x100001B3),"kInitiateTrade":(0x100001B1,0x100001B4),
 "kInventoryAgentChanged":(0x100001C1,0x100001C4),"kInventoryRelated_1":(0x100001C2,0x100001C5),
 "kInventoryRelated_2":(0x100001C3,0x100001C6),"kMissionStatusRelated":(0x100001C4,0x100001C7),
 "kUnused_1c2":(0x100001C5,0x100001C8),"kCollapseExpandSkillListSection":(0x100001C6,0x100001C9),
 "kTemplateRelated_1":(0x100001C7,0x100001CA),"kTemplateRelated_2":(0x100001C8,0x100001CB),
 "kPromptSaveTemplate":(0x100001C9,0x100001CC),"kOpenTemplate":(0x100001CA,0x100001CD),
 "kTemplateRelated_3":(0x100001CB,0x100001CE),"kTemplateRelated_4":(0x100001CC,0x100001CF),
}
path = sys.argv[1]
src = open(path, encoding="utf-8").read()
changed, missing, already = 0, [], 0
for name, (old, new) in M.items():
    po = re.compile(r"^(\s*" + name + r"\s*=\s*)0x%08X\b" % old, re.M | re.I)
    pn = re.compile(r"^(\s*" + name + r"\s*=\s*)0x%08X\b" % new, re.M | re.I)
    if po.search(src):
        src = po.sub(lambda m: m.group(1) + "0x%08X" % new, src); changed += 1
    elif pn.search(src): already += 1
    else: missing.append(name)
open(path, "w", encoding="utf-8", newline="").write(src)
print("%-22s changed=%d already=%d missing=%s" % (path.split("\\")[-1], changed, already, missing or "none"))
