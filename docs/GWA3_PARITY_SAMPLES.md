# GwAu3 script call, beside the Python that answers it

**Generated** by `python tools/report_gwa3_parity_samples.py` -- read from `external/GwAu3/Scripts/*.au3` and `py4gw/gwa3/*.py` at run time, never typed by hand.

A migrated script is the **same AutoIt file** with one include line swapped, so its call site is unchanged; what differs is who answers. Each row below is one call a real GwAu3 script makes, and the layer member that answers it under the same name.

| script calls (AutoIt) | the layer answers (Python) |
| --- | --- |
| `external/GwAu3/Scripts/Exemples/Exemple_AutoitGUI_Tester.au3`:63<br>`If Core_Initialize(ProcessExists("gw.exe"), True) = 0 Then` | `py4gw/gwa3/core.py`:71<br>`def Core_Initialize(gw: Any, change_title: bool = True) -> int:`<br>_Open a client and resolve the runtime (``GwAu3_Core.au3:9-...``)._ |
| `external/GwAu3/Scripts/Exemples/Exemple_AutoitGUI_Tester.au3`:137<br>`UAI_Fight(Agent_GetAgentInfo(-2, "X"), Agent_GetAgentInfo(-2, "Y"), 1320, 3500, $g_i_FinisherMode)` | `py4gw/gwa3/data_agent.py`:725<br>`def Agent_GetAgentInfo(agent_id: Any = -2, info: str = "") -> Any:`<br>_One field of an agent, by GwAu3's field name (``GwAu3_Data_Agent.au3:82-524``)._ |
| `external/GwAu3/Scripts/Exemples/Punch_Out_Farm.au3`:180<br>`Local $l_i_CurrentMapID = Map_GetCharacterInfo("MapID")` | `py4gw/gwa3/data_map.py`:334<br>`def Map_GetCharacterInfo(info: str = "") -> Any:`<br>_One field of the character context, by GwAu3's field name (``GwAu3_Data_Map.au3:5-39``)._ |
| `external/GwAu3/Scripts/Exemples/Punch_Out_Farm.au3`:444<br>`Local $l_av_Inventory = Item_GetInventoryArray()` | `py4gw/gwa3/data_item.py`:810<br>`def Item_GetInventoryArray(`<br>_The character's carried items as GwAu3's 2-D array (``GwAu3_Data_Item.au3:331-...``)._ |
| `external/GwAu3/Scripts/Tools/GwAu3_DevTools.au3`:2849<br>`Log_Message("SkillID: " & Skill_GetSkillInfo($id, "SkillID"), $c_UTILS_Msg_Type_Info, "DevTools")` | `py4gw/gwa3/data_skill.py`:149<br>`def Skill_GetSkillInfo(record_id: Any, info: str = "") -> Any:`<br>_One field of the record, by GwAu3's field name (``GwAu3_Data_Skill.au3``)._ |
| `external/GwAu3/Scripts/Tools/GwAu3_DevTools.au3`:2717<br>`Log_Message("HeroID: " & Party_GetHeroInfo($num, "HeroID") & ", AgentID: " & Party_GetHeroInfo($num, "AgentID"), $c_UTILS_Msg_Type_Info, "DevTools")` | `py4gw/gwa3/data_party.py`:753<br>`def Party_GetHeroInfo(hero_number: Any = 1, info: str = "") -> Any:`<br>_One field of one **hero's** information record (``GwAu3_Data_Party.au3:404-445``)._ |
| `external/GwAu3/Scripts/Exemples/Exemple_PathFinding.au3`:289<br>`Map_Move($l_f_WaypointX, $l_f_WaypointY, 0)` | `py4gw/gwa3/cmd_map.py`:55<br>`def Map_Move(x: float, y: float, randomize: float = 50) -> bool:`<br>_Move to a point, with GwAu3's own randomisation (``GwAu3_Cmd_Map.au3:2-25``)._ |
| `external/GwAu3/Scripts/Exemples/Exemple_AutoitGUI_Tester.au3`:137<br>`UAI_Fight(Agent_GetAgentInfo(-2, "X"), Agent_GetAgentInfo(-2, "Y"), 1320, 3500, $g_i_FinisherMode)` | `py4gw/gwa3/uai_core.py`:586<br>`def UAI_Fight(`<br>_The engine: what a script calls to run a fight (``:3-69``)._ |
| `external/GwAu3/Scripts/Tools/GwAu3_DevTools.au3`:2611<br>`Log_Message("CostID: " & Merchant_GetTraderCostID(), $c_UTILS_Msg_Type_Info, "DevTools")` | `py4gw/gwa3/data_merchant.py`:153<br>`def Merchant_GetTraderCostID() -> int:`<br>_The last quoted item id (``GwAu3_Data_Merchant.au3:12-14``)._ |
| `external/GwAu3/Scripts/Tools/GwAu3_DevTools.au3`:2947<br>`Log_Message("Skill " & $skillID & " learnt: " & World_IsSkillLearnt($skillID), $c_UTILS_Msg_Type_Info, "DevTools")` | `py4gw/gwa3/data_world.py`:448<br>`def World_IsSkillLearnt(a_i_SkillID: Any) -> bool:`<br>_Whether the character has learnt a skill (``GwAu3_Data_World.au3:214-233``)._ |
| `external/GwAu3/Scripts/Exemples/Punch_Out_Farm.au3`:708<br>`If $l_h_Wnd = 0 Then $l_h_Wnd = Scanner_GetHwnd($g_i_GWProcessId)` | `py4gw/gwa3/data_scanner.py`:36<br>`def Scanner_GetHwnd(a_i_Proc: Any) -> int:`<br>_The client window's handle, by process id (``GwAu3_Core_Scanner.au3:555-560``)._ |
| `external/GwAu3/Scripts/Tools/GwAu3_DevTools.au3`:2589<br>`Log_Message("MatchID: " & Match_GetObserverMatchInfo($matchNum, "MatchID"), $c_UTILS_Msg_Type_Info, "DevTools")` | `py4gw/gwa3/data_match.py`:248<br>`def Match_GetObserverMatchInfo(match_number: Any = 0, info: str = "") -> Any:`<br>_One field of one observer-match record (``GwAu3_Data_Match.au3:11-66``)._ |

## One call, end to end

**`Agent_GetAgentInfo`**

```autoit
; external/GwAu3/Scripts/Exemples/Exemple_AutoitGUI_Tester.au3:137  (unchanged in the migrated script)
UAI_Fight(Agent_GetAgentInfo(-2, "X"), Agent_GetAgentInfo(-2, "Y"), 1320, 3500, $g_i_FinisherMode)
```
```python
# py4gw/gwa3/data_agent.py:725
def Agent_GetAgentInfo(agent_id: Any = -2, info: str = "") -> Any:
    One field of an agent, by GwAu3's field name (``GwAu3_Data_Agent.au3:82-524``).
```

**`Map_GetCharacterInfo`**

```autoit
; external/GwAu3/Scripts/Exemples/Punch_Out_Farm.au3:180  (unchanged in the migrated script)
Local $l_i_CurrentMapID = Map_GetCharacterInfo("MapID")
```
```python
# py4gw/gwa3/data_map.py:334
def Map_GetCharacterInfo(info: str = "") -> Any:
    One field of the character context, by GwAu3's field name (``GwAu3_Data_Map.au3:5-39``).
```

**`Item_GetInventoryArray`**

```autoit
; external/GwAu3/Scripts/Exemples/Punch_Out_Farm.au3:444  (unchanged in the migrated script)
Local $l_av_Inventory = Item_GetInventoryArray()
```
```python
# py4gw/gwa3/data_item.py:810
def Item_GetInventoryArray(
    The character's carried items as GwAu3's 2-D array (``GwAu3_Data_Item.au3:331-...``).
```

