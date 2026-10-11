"""Generate ``docs/GWA3_ROUTE_MAP.md``: what backs each GwAu3 function in this project.

Part of the GwAu3-compatible layer; see ``docs/GWA3_COMPAT_SPEC.md`` for the specification and the
meaning of the four tiers.

Run from the project root:

    python tools/generate_gwa3_route_map.py

Three inputs, and each is read rather than restated:

1. **GwAu3's own source** (``external/GwAu3/API/Modules/{Cmd,Data}/*.au3``) -- the declared
   functions, their signatures with defaults, and their file and line. Parsed on every run, because
   the surface index made in this session (``external/GwAu3_modules_surface.csv``) is known to have
   missed declarations and must not be treated as a record. Its own provenance note is beside it.
2. **The GwAu3 mechanism inventories** (``docs/_inventory_gwau3_*.md``) -- what each function does to
   reach the game, with the lines it rests on. These were produced by reading the sources line by
   line; this tool does not re-derive them, it carries them and cites where they came from.
3. **A route table written by hand in this file** (:data:`ROUTES`) -- the part that is genuinely new
   work: which Stealth member, or which of Stealth's five mechanisms, does the same thing. Every
   entry cites the Stealth file and line it was read from.

**Why the routes are hand-written and the rest is not.** A mechanism classification is a fact about
GwAu3 and can be parsed. A route is a claim about *this* project -- that `Agent_Attack` and
`Player.Interact` produce the same effect in the client -- and that claim has to be made by reading
both sides. Nothing here invents one: a function with no entry is reported as having no route
recorded yet, which is the honest answer and the next work item.

The output lists **every declared function**, not only the ones a script calls. The census of call
sites is carried as a column so the surface a migration actually has to serve sorts to the top.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GWAU3_MODULES_DIR = REPO_ROOT / "external" / "GwAu3" / "API" / "Modules"
GWAU3_API_ROOT = REPO_ROOT / "external" / "GwAu3" / "API"
GWAU3_ROOT = REPO_ROOT / "external" / "GwAu3"


def _called_surface() -> frozenset[str]:
    """Every GwAu3 function the checkout *calls*, from GwAu3's own sources.

    Read here rather than from the CSV index, which carries only the modules it was built from --
    the same narrow frame that left 345 called functions untiered. Declarations are excluded: every
    `Func` line ends in `(`, so counting them would report every declared function as calling itself.
    """

    declared: set[str] = set()
    for path in sorted(GWAU3_API_ROOT.rglob("*.au3")):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            match = FUNC_DECLARATION.match(line)
            if match:
                declared.add(match.group("name"))

    called: set[str] = set()
    for path in sorted(GWAU3_ROOT.rglob("*.au3")):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            code = line.split(";", 1)[0]
            if code.lstrip().lower().startswith("func "):
                continue
            for word in re.findall(r"\b([A-Za-z_]\w*)\s*\(", code):
                if word in declared:
                    called.add(word)
    return frozenset(called)
INVENTORY_FILES = (
    "docs/_inventory_gwau3_misc.md",
    "docs/_inventory_gwau3_agent_item.md",
    "docs/_inventory_gwau3_party_map_ui_trade.md",
)
OUTPUT_PATH = REPO_ROOT / "docs" / "GWA3_ROUTE_MAP.md"
CALL_CENSUS_PATH = REPO_ROOT / "external" / "GwAu3_modules_surface.csv"

# `Func Name($a = default, ...)` -- one line, which is how GwAu3 writes them. A declaration that
# varies from this shape would be missed, so the count this tool produces is reported next to the
# source's own and any gap is named rather than absorbed.
FUNC_DECLARATION = re.compile(r"^\s*Func\s+(?P<name>[A-Za-z_]\w*)\s*\((?P<params>[^)]*)\)")

# GwAu3's mechanism for a function, from the inventories. Kept in the same vocabulary the
# inventories use so the two can be checked against each other.
MECHANISMS = (
    "MEMORY READ",
    "MEMORY WRITE",
    "PACKET SEND",
    "GAME-THREAD CALL",
    "PURE COMPUTATION",
    "UI/INPUT SYNTHESIS",
    "OTHER",
)

# Which tier a GwAu3 mechanism maps to when no route has been recorded yet. This is the default,
# not a verdict: a row with a recorded route below overrides it, and PACKET SEND rows need a
# per-function decision because Stealth has a native route to some of those effects and none to
# others.
TIER_FOR_MECHANISM = {
    "MEMORY READ": ("NO ROUTE YET", "a read; the route is the ported class that owns the data, and none is recorded for this function yet"),
    "MEMORY WRITE": ("NO ROUTE YET", "a write performed inside the client; no route recorded for this function yet"),
    "PACKET SEND": ("REFUSED", "GwAu3's implementation is a forged packet, which this project does not send; no safe route recorded for this effect yet"),
    "GAME-THREAD CALL": ("NO ROUTE YET", "a call on the game thread, which the capability layer supports; no route recorded for this function yet"),
    "PURE COMPUTATION": ("NO ROUTE YET", "no game access; not yet implemented here"),
    "UI/INPUT SYNTHESIS": ("REFUSED", "input synthesis; this project drives the client's own callbacks instead"),
    "OTHER": ("NO ROUTE YET", "unclassified; no route recorded"),
}


@dataclass(frozen=True)
class Route:
    """A recorded route: what Stealth does the same thing with.

    ``mechanism`` names which of Stealth's five ways of reaching the client the route uses, so a
    reviewer can see at a glance whether the row is a read, a game-thread call, a UI message, an
    in-client write or a byte patch. ``note`` is the caveat, when there is one.
    """

    member: str
    citation: str
    mechanism: str = ""
    note: str = ""


@dataclass(frozen=True)
class DeclaredFunction:
    name: str
    file: str
    kind: str  # "Cmd" or "Data"
    line: int
    params: str


# ---------------------------------------------------------------------------------------------
# The routes. Each is a claim read from both sides, so each carries the Stealth line it was read
# from. GwAu3's own line is supplied by the parser.
#
# Stealth's five mechanisms, as named here:
#   M1   a typed call on the client's own thread through the capability layer
#   M2   the client's own UI-message sender
#   M3   a frame message (the client's __thiscall SendFrameUIMessage)
#   M4   a write into the client performed by the payload on the game thread
#   M5   a host-side byte patch
# See `docs/_inventory_stealth_actions.md` section 1 for all five, with lines.
# ---------------------------------------------------------------------------------------------
ROUTES: dict[str, Route] = {
    # --- Agent: targeting and interaction ------------------------------------------------
    "Agent_ChangeTarget": Route(
        "Player.ChangeTarget", "py4gw/player.py:1074-1093", "M1 / agent.change_target_func",
        "GwAu3 forges a packet; Stealth calls the client's own change-target function.",
    ),
    "Agent_CallTarget": Route(
        "Player.CallTarget", "py4gw/player.py:1096-1137", "M1 / agent.call_target_func",
        "GwAu3 forges a packet; Stealth calls the client's own call-target, choosing the enemy and non-enemy shape as the source does.",
    ),
    "Agent_Attack": Route(
        "Player.Interact", "py4gw/player.py:1140-1185", "M1 / agent.do_world_action_func",
        "GwAu3 forges an attack packet. Stealth's `Player.Interact(agent_id, call_target)` is the same world action the client issues; the `$a_b_CallTarget` argument maps to its `call_target`.",
    ),
    "Agent_GoNPC": Route(
        "Player.Interact", "py4gw/player.py:1140-1185", "M1 / agent.do_world_action_func",
    ),
    "Agent_GoPlayer": Route(
        "Player.Interact", "py4gw/player.py:1140-1185", "M1 / agent.do_world_action_func",
        "GwAu3 sends `HEADER_INTERACT_PLAYER`; Stealth's world action covers the same interaction.",
    ),
    "Agent_GoSignpost": Route(
        "Player.Interact", "py4gw/player.py:1140-1185", "M1 / agent.do_world_action_func",
    ),
    "Agent_CancelAction": Route(
        "UIManager.Keydown / UIManager.Keyup (the client's own control action)",
        "py4gw/gwa3/cmd_agent.py:188, py4gw/ui_manager.py:1049-1088",
        "M3 / client's button-action frame message",
        "GwAu3 sends `HEADER_ACTION_CANCEL` (0x0028); Reforged performs the same effect by pressing the client's own control action -- `Keybinds.CancelAction()` -> `Keybinds.PressKeybind(ControlAction_CancelAction, 75)` (`routines_src/yield_src/keybinds.py:160-161`), down and up at `routines_src/behaviourtrees_src/keybinds.py:101,119`. That is the press `Agent_CancelAction` makes, through the layer's `Core_ControlAction` with `$GC_I_CONTROL_ACTION_CANCEL_ACTION` (0xAF, the code this port's own enum carries as `ControlAction_CancelAction`). The earlier candidate recorded here -- `Player.SendRawDialog`, flagged as needing a live check -- is withdrawn in favour of the authority's own route for this effect.",
    ),
    "Agent_ClearTarget": Route(
        "Player.ChangeTarget", "py4gw/player.py:1074-1093", "M1 / agent.change_target_func",
        "GwAu3's own implementation is `Agent_ChangeTarget(0)` (`GwAu3_Cmd_Agent.au3:155-157`), and its comment records that 0 is how the native clears the selection -- so the same route, with the same zero.",
    ),
    "Agent_TargetSelf": Route(
        "Player.ChangeTarget", "py4gw/player.py:1074-1093", "M1 / agent.change_target_func",
        "`Agent_ChangeTarget(Agent_GetMyID())` in GwAu3; the same route with the controlled character's id.",
    ),
    "Agent_GetAgentPtr": Route(
        "AgentArray.GetAgentByID / Agent.GetAgentByID", "py4gw/agent_array.py:162, py4gw/agent.py:512", "read",
        "GwAu3 answers a raw client pointer; Stealth answers a materialized record, which is the same client bytes read into a typed structure. A caller that passes the result back into another GwAu3 function needs the id, not the address.",
    ),
    "Agent_GetMyID": Route("Player.GetAgentID", "py4gw/player.py:456", "read"),
    "GetMyID": Route("Player.GetAgentID", "py4gw/player.py:456", "read"),
    "Agent_GetCurrentTarget": Route(
        "Player.GetTargetID", "py4gw/player.py:552", "read",
        "The client's announced target, captured by the connection (`py4gw/client.py:616-631`).",
    ),
    "Agent_GetMaxAgents": Route(
        "AgentArray.GetAgentArray", "py4gw/agent_array.py:43", "read",
        "**Shape differs.** GwAu3 returns the array's capacity; Stealth returns the ids it holds. A caller looping `1 To Agent_GetMaxAgents()-1` is looping over a capacity, and the compatibility layer must reproduce that number rather than the id count.",
    ),
    "Agent_GetDistance": Route(
        "", "", "",
        "**No member exists; this one is genuinely the layer's own work.** GwAu3 computes the "
        "distance between two agents from their `X`/`Y` (`GwAu3_Data_Agent.au3:805-815`, plain "
        "`Sqrt` arithmetic). Nothing named `GetDistance` exists anywhere in `py4gw/` -- checked "
        "across the package, not just `agent.py` -- so the layer implements GwAu3's own arithmetic "
        "over the records it can read. That is a faithful reimplementation of a pure computation, "
        "not a new API on a ported class.",
    ),
    "Agent_GetDistanceToXY": Route(
        "", "", "",
        "As `Agent_GetDistance`: GwAu3's own arithmetic over one agent's `X`/`Y` and a point "
        "(`GwAu3_Data_Agent.au3:817-819`); no counterpart exists in `py4gw/`.",
    ),
    "Agent_GetDistanceSq": Route(
        "", "", "",
        "As `Agent_GetDistance`, without the square root (`GwAu3_Data_Agent.au3:821-831`); no "
        "counterpart exists in `py4gw/`.",
    ),
    "Agent_GetNpcInfoByAgentID": Route(
        "", "", "",
        "**No member exists.** GwAu3 returns `0` for a player and otherwise reads the NPC table by "
        "the agent's player number (`GwAu3_Data_Agent.au3:1011-1014`). `py4gw/` has no `GetNpcInfo` "
        "at all, so this is the layer's own work over the NPC records -- and note the NPC-table read "
        "is a second accessor (`Agent_GetNpcInfo`) with its own field keys.",
    ),
    "Agent_GetBestTarget": Route(
        "", "", "",
        "**No member exists.** GwAu3's own scoring loop over the living-agent array "
        "(`GwAu3_Data_Agent.au3:1096-1119`): for each enemy in range, sum its distance to every "
        "other enemy in range, and take the lowest sum. Pure computation over reads the layer has.",
    ),
    "Agent_GetAgentArray": Route(
        "AgentArray.GetAgentArray", "py4gw/agent_array.py:43", "read",
        "**Return shape differs, deliberately.** GwAu3 fills a 1-based AutoIt array whose slot 0 is the count; Stealth returns a 0-based list of ids. The compatibility layer restores GwAu3's array, because a script indexes it.",
    ),
    "VisibleEffect_Count": Route("Agent.GetAgentEffects", "py4gw/agent.py:835", "read"),
    "Agent_CountVisibleEffects": Route("Agent.GetAgentEffects", "py4gw/agent.py:835", "read"),
    "Agent_GetAgentInfo": Route("the layer's own reader", "py4gw/gwa3/data_agent.py:602", "read", "**Routed inside the layer, and live-verified.** All 143 declared keys are in the table; 139 answer and the other four refuse -- `EffectCount`, `BondCount`, `VisibleEffectCount`, `HasVisibleEffects`, all four a linked-list walk no ported member covers. Measured live 2026-10-09: 139 of 139 answered, and eleven of them equal an independent ported read (`Agent.GetXY`, `GetMaxHealth`, `GetLevel`, `IsDead`, `Allegiance`, `WeaponType`, `TypeMap`)."),

    # --- Player: status, titles, faction, chat -------------------------------------------
    "Friend_SetPlayerStatus": Route(
        "Player.SetPlayerStatus", "py4gw/player.py:1050-1070", "M1 / friend_list.set_online_status_func",
        "GwAu3 also reaches this by a game-thread call, not a packet, so the mechanisms already agree.",
    ),
    "Title_SetDisplayedTitle": Route(
        "Player.SetActiveTitle", "py4gw/player.py:1242-1251", "M1 / player.set_active_title_func",
    ),
    "Game_DonateFaction": Route(
        "Player.DepositFaction", "py4gw/player.py:1209-1226", "M1 / player.deposit_faction_func",
        "Stealth calls the native with the source's own leading `0` and trailing `5000`.",
    ),
    "Chat_SendChat": Route(
        "Player.SendChat", "py4gw/player.py:1478-1491", "M1 / chat.send_chat_func",
        "**Caution recorded in the port:** `ChatChannel.CHANNEL_ALL` is 3, which is not an opcode and therefore sends nothing (`py4gw/player.py:1486-1488`). GwAu3's channel argument is a one-character string ('!'), so the compatibility layer must map the string form, not the enum.",
    ),
    "Chat_SendWhisper": Route(
        "Player.SendWhisper", "py4gw/player.py:1494-1505", "M1 / chat.send_chat_func",
        "A target name of fewer than 3 characters would be read as an opcode (`chat.py:111-115`).",
    ),
    "Game_SwitchMode": Route("", "", "", "ROUTE NOT RECORDED -- GwAu3 changes the client's mode; the Stealth member for it has not been located."),
    "Quest_AcceptQuest": Route("", "", "", "ROUTE NOT RECORDED -- GwAu3 forges a packet; whether Stealth reaches the same effect through the dialog path is not established."),
    "Quest_QuestReward": Route("", "", "", "ROUTE NOT RECORDED -- as above."),
    "Quest_AbandonQuest": Route("", "", "", "ROUTE NOT RECORDED -- as above."),
    "Quest_RequestInfos": Route("Quest.RequestQuestInfo", "py4gw/quest.py:100", "M1", "**Needs verification:** both are named 'request quest info'; the arguments and effect must be compared before this is trusted."),

    # --- Map: travel, movement, windows --------------------------------------------------
    "Map_TravelTo": Route(
        "Map.Travel", "py4gw/map.py:816-822", "M2 raw / kTravel",
        "GwAu3 forges `HEADER_PARTY_TRAVEL`; Stealth sends the client's own travel message with the four words the client expects. The region and language arguments come from `Map_GetCharacterInfo` in GwAu3's default expression.",
    ),
    "Map_MoveMap": Route(
        "Map.TravelToRegion", "py4gw/map.py:884-892", "M2 raw / kTravel",
        "**Argument order differs between the two GwAu3 spellings** -- `Map_MoveMap(map, region, district, language)` (`GwAu3_Cmd_Map.au3:36`) against `Ui_MoveMap(map, region, language, district)` (`GwAu3_Cmd_Ui.au3:217`). Each spelling keeps its own order here.",
    ),
    "Map_Move": Route(
        "Player.Move", "py4gw/player.py:1188", "M1 / agent.move_to_func",
        "GwAu3 adds `$a_f_Randomize = 50` -- random movement around the destination. Randomness is GwAu3's own behaviour and belongs in the layer, not in `Player.Move`, which supplies the point it is given.",
    ),
    "Map_MoveLayer": Route(
        "Player.Move", "py4gw/player.py:1188", "M1 / agent.move_to_func",
        "`$a_f_Layer` maps to `Player.Move`'s `zPlane`.",
    ),
    "Map_TravelGH": Route("Map.TravelGH", "py4gw/map.py:895", "M2 raw / kGuildHall"),
    "Map_LeaveGH": Route("Map.LeaveGH", "py4gw/map.py:904", "M2 packed / kLeaveGuildHall"),
    "Map_EnterChallenge": Route("Map.EnterChallenge", "py4gw/map.py:913", "M2 packed / kSendEnterMission"),
    "Map_ReturnToOutpost": Route(
        "Party.ReturnToOutpost", "py4gw/party.py:1262-1290", "M3 / ui::ButtonClick",
        "Stealth clicks the client's own redirect button rather than forging `HEADER_PARTY_RETURN_TO_OUTPOST`.",
    ),
    "Map_MapIsLoaded": Route("Map.IsMapReady", "py4gw/map.py:164", "read", "**Compare the two before relying on them:** 'loaded' and 'ready' are not stated to be the same predicate."),
    "Map_GetMapID": Route("Map.GetMapID", "py4gw/map.py:176", "read"),
    "Map_GetAreaInfo": Route("the layer's own reader", "py4gw/gwa3/data_map.py:166", "read", "**Routed inside the layer, and live-verified.** All 40 declared keys answer, read from `MapMethods.GetMapInfo(map_id)`; `AreaInfoStruct` in that module matches GwAu3's `0x7C` offsets field for field. Measured live 2026-10-09: 40 of 40 answered, and six of them (`Region`, `Continent`, `RegionType`, `ThumbnailID`, `NameID`, `Campaign`) equal the live area record. No refusal."),

    # --- Party: heroes, henchmen, flags -------------------------------------------------
    "Party_GetPartyContextInfo": Route("the layer's own reader", "py4gw/gwa3/data_party.py:162", "read", "**Routed inside the layer, and live-verified.** All 14 declared keys are in the table. Since 2026-10-10 the five second-level keys -- `PlayerCount`, `HenchmenCount`, `HeroCount`, `OtherCount`, `PlayerPartyID` -- **answer**, because this layer now follows the `player_party_ptr` the context holds (`PartyContextStruct.player_party`), and `TotalPartySize` sums three of them; `MyPartyPtr` still refuses, because the value it answers is a *client address*. Measured live 2026-10-09: seven flags and `Flags` answered as booleans and an int (`IsPartyLeader` True, flags `0x80`); measured live 2026-10-10: the counts equal `Party.GetPlayers()`/`GetHeroes()`/`GetHenchmen()`/`GetOthers()` and `PlayerPartyID` equals `Party.GetPartyID()`. **This accessor takes no record id** -- GwAu3 declares `Party_GetPartyContextInfo($a_s_Info = \"\")` (`GwAu3_Data_Party.au3:4`), and the layer's first version carried one, which made a migrating script's own call answer `0` with no error."),
    "Party_AddHero": Route("Heroes.AddHero", "py4gw/party.py:1529-1537", "M3/M1 party callback"),
    "Party_KickHero": Route("Heroes.KickHero", "py4gw/party.py:1550-1560", "M3/M1 party callback"),
    "Party_KickAllHeroes": Route("Heroes.KickAllHeroes", "py4gw/party.py:1569-1576", "M3/M1 party callback"),
    "Party_AddNpc": Route("Henchmen.AddHenchman", "py4gw/party.py:1723-1731", "M3/M1 party callback"),
    "Party_KickNpc": Route("Henchmen.KickHenchman", "py4gw/party.py:1734-1743", "M3/M1 party callback"),
    "Party_LeaveGroup": Route(
        "Party.LeaveParty", "py4gw/party.py:1293-1304", "M3/M1 party callback",
        "**Order differs between the GwAu3 spellings:** `Party_LeaveGroup` kicks heroes then leaves; `Ui_LeaveGroup` leaves then kicks. Each keeps its own order.",
    ),
    "Party_CommandHero": Route("Heroes.FlagHero", "py4gw/party.py:1612-1623", "M1 / party.flag_hero_agent_func"),
    "Party_CommandAll": Route("Heroes.FlagAllHeroes", "py4gw/party.py:1626-1630", "M1 / party.flag_all_func"),
    "Party_CancelHero": Route(
        "Heroes.UnflagHero", "py4gw/party.py:1633-1643", "M1 / party.flag_hero_agent_func",
        "`Heroes.UnflagHero` flags to `HUGE_VALF`, which is the source's own way of clearing a flag.",
    ),
    "Party_CancelAll": Route("Heroes.UnflagAllHeroes", "py4gw/party.py:1646-1652", "M1 / party.flag_all_func"),
    "Party_ToggleHeroSkillState": Route(
        "Heroes.SetSkillAIEnabled", "py4gw/party.py:1599-1609", "M1 / party.command_hotkey_disable_ai_func",
        "**A toggle is not a set.** Stealth's member sets a state and its guard only calls when the bit differs; GwAu3's name says toggle, so the layer reads the current state first to reproduce a toggle.",
    ),
    "Party_DisableHeroSkill": Route("Heroes.SetSkillAIEnabled(False)", "py4gw/party.py:1599-1609", "M1", "**GwAu3 returns True unconditionally here** -- the guard decides whether a packet is sent, not what is returned (`GwAu3_Cmd_Party.au3:80-83`). The layer must reproduce that return, not a truthful one."),
    "Party_EnableHeroSkill": Route("Heroes.SetSkillAIEnabled(True)", "py4gw/party.py:1599-1609", "M1", "GwAu3's own version has no `Return` at all (`GwAu3_Cmd_Party.au3:75-77`), so it returns AutoIt's valueless default."),
    "Party_SetHeroAggression": Route("Heroes.SetHeroBehavior", "py4gw/party.py:1707-1717", "M1 / party.set_hero_behavior_func", "This function is one the surface index missed; it lives at `GwAu3_Cmd_Party.au3:60`."),
    "Party_LockHeroTarget": Route("", "", "", "ROUTE NOT RECORDED -- a function the surface index missed (`GwAu3_Cmd_Party.au3:55`); no Stealth member located yet."),
    "Party_GetIsHeroSkillDisabled": Route("Heroes' skill-AI reads", "py4gw/party.py:1599-1609", "read", "Stealth reads the bit to decide whether to call; the same bit is the answer."),

    # --- Item ---------------------------------------------------------------------------
    "Item_PickUpItem": Route(
        "Inventory.PickUpItem", "py4gw/inventory.py:989", "M2 / kInteractWithItem",
        "Stealth sends the client's own UI message; GwAu3 forges the packet.",
    ),
    "Item_EquipItem": Route("", "", "", "ROUTE NOT RECORDED -- GwAu3 forges `HEADER_ITEM_EQUIP`; the Stealth member for equipping by hand has not been located."),
    "Item_SwitchWeaponSet": Route(
        "UIManager.Keydown / UIManager.Keyup (the client's own control action)",
        "py4gw/gwa3/cmd_item.py:471, py4gw/ui_manager.py:1049-1088",
        "M3 / client's button-action frame message",
        "GwAu3 forges `HEADER_SWITCH_SET` (0x32) with the set number. The route is the control action Reforged presses for this effect: `Keybinds.ActivateWeaponSet($i)` presses `ControlAction_ActivateWeaponSet1.value + (index - 1)` (`routines_src/yield_src/keybinds.py:110-113`), which is the same four codes GwAu3's own constants name `$GC_I_CONTROL_INVENTORY_ACTIVATE_WEAPON_SET_1..4` (129-132) and the same four this port's enum carries. Reforged's own 1..4 guard rides with the route, so a set outside it answers False rather than pressing a different action.",
    ),
    "Item_MoveItem": Route("", "", "", "ROUTE NOT RECORDED -- GwAu3 forges `HEADER_ITEM_MOVE`; the Stealth member has not been located."),
    "Item_DestroyItem": Route("", "", "", "ROUTE NOT RECORDED -- GwAu3 forges `HEADER_ITEM_DESTROY`."),
    "Item_UseItem": Route("", "", "", "ROUTE NOT RECORDED -- GwAu3 forges `HEADER_ITEM_USE`."),
    "Item_DropItem": Route("", "", "", "ROUTE NOT RECORDED -- GwAu3 forges `HEADER_DROP_ITEM`."),
    "Item_DropBundle": Route(
        "UIManager.Keydown / UIManager.Keyup (the client's own control action)",
        "py4gw/gwa3/cmd_item.py:343, py4gw/ui_manager.py:1049-1088",
        "M3 / client's button-action frame message",
        "GwAu3 enqueues a four-byte record whose injected stub calls the client's own `DropBundle` (`GwAu3_Core_Assembler.au3:2427-2428`). Reforged releases a held bundle by pressing the client's own control action: `Keybinds.DropBundle()` -> `Keybinds.PressKeybind(ControlAction_DropItem, 75)` (`routines_src/yield_src/keybinds.py:116-117`), down and up at `routines_src/behaviourtrees_src/keybinds.py:101,119`. That is the press this row's member makes, through the layer's control-action member with `$GC_I_CONTROL_ACTION_DROP_ITEM` (0xCD, the code this port's own enum carries as `ControlAction_DropItem`).",
    ),
    "Item_DropGold": Route("", "", "", "ROUTE NOT RECORDED -- GwAu3 forges `HEADER_DROP_GOLD`."),
    "Item_OpenChest": Route("", "", "", "ROUTE NOT RECORDED -- GwAu3 forges `HEADER_CHEST_OPEN`."),
    "Item_GetItemInfoByItemID": Route("the layer's own reader", "py4gw/gwa3/data_item.py:231", "read", "**Routed inside the layer, and live-verified.** All 39 declared keys are in the table: 35 answer, and `Dye1`, `Dye2`, `Dye3` and `ExtraID` refuse because they live inside an unnamed three-byte `dye` struct this project has no member for. Measured live 2026-10-09: 32 answered, 3 -- `Name`, `CompleteName`, `SingleItemName` -- refused a connection without the game thread by name, because their readers run a decode through the client."),
    "Item_GetInventoryInfo": Route("Inventory's own members", "py4gw/inventory.py:113", "read", "**Class, not one member.** 61 field keys, each needing its own mapping. Route not yet complete."),
    "Item_GetItemBySlot": Route("Inventory.GetBags / item slot reads", "py4gw/inventory.py:1101", "read"),

    # --- Merchant -----------------------------------------------------------------------
    "Merchant_BuyItem": Route("", "", "", "ROUTE NOT RECORDED -- GwAu3 forges `HEADER_TRANSACT_ITEMS`; Stealth has a merchant listener but no buy member recorded."),
    "Merchant_SellItem": Route("", "", "", "ROUTE NOT RECORDED -- as above. GwAu3's own returns True even on its timeout and empty-stack exits (`GwAu3_Data_Merchant.au3:200/214/241`), which the layer must reproduce."),

    # --- Skill --------------------------------------------------------------------------
    "Skill_UseSkill": Route(
        "UIManager key action", "py4gw/ui_manager.py:1049-1088", "M3 / SendFrameUIMessage",
        "**A decision the route map must not make on its own.** GwAu3 forges `HEADER_SKILL_USE`; the client's own way is the skillbar key action, which Stealth already sends as a frame message. Whether the target argument and the call-target flag can be honoured through the key path is not established by reading.",
    ),
    "Skill_UseHeroSkill": Route("Heroes.UseSkill", "py4gw/party.py:1579-1596", "M3 + M1", "Stealth's argument is a hero number, not an agent id (`party.py:1591-1593`); the same target-swap-restore shape as GwAu3's."),
    "Skill_LoadSkillBar": Route("Skillbar's own members", "py4gw/skillbar.py:967", "M1", "**Class, not one member.** GwAu3's signature takes eight positional skill ids plus a hero number, which the layer reproduces. Route not yet complete."),
    "Skill_SetSkillbarSkill": Route("Skillbar.GetSkill / GetSkills", "py4gw/skillbar.py:708", "M1"),
    "Skill_BuySkillByID": Route("Player.BuySkill", "py4gw/player.py:1272-1286", "M1 / agent.send_agent_dialog_func", "Stealth converts the skill id to a dialog id exactly as the source does."),
    "Skill_UnlockSkillByID": Route("Player.UnlockBalthazarSkill", "py4gw/player.py:1289-1306", "M1"),
    "Skill_GetSkillInfo": Route("the layer's own reader", "py4gw/gwa3/data_skill.py:145", "read", "**Routed inside the layer, and live-verified.** All 63 declared keys answer and this is one of the seven dominant accessors. Measured live 2026-10-09: 63 of 63 answered, and eleven of them equal the live skill record the ported class reads. No refusal."),
    "Skill_GetSkillbarInfo": Route("Skillbar's own members", "py4gw/skillbar.py:967", "read", "**Class, not one member.** 16 field keys, each needing its own mapping. Route not yet complete."),

    # --- Spells that exist // in neither source's ported surface -------------------------
    "Other_TolSleep": Route("", "", "", "PURE COMPUTATION -- a sleep with tolerance; belongs in the layer, no game reach."),
    "Other_RndSleep": Route("", "", "", "PURE COMPUTATION -- a random sleep; belongs in the layer, no game reach."),
    "Other_WaitPingStabilized": Route("", "", "", "MEMORY READ -- GwAu3 polls a ping value; no route recorded."),
    "World_GetWorldInfo": Route("the layer's own reader", "py4gw/gwa3/data_world.py:343", "read", "**Routed inside the layer, and live-verified.** All 79 declared keys are in the table; 49 answer and the other 30 refuse -- array addresses and their counts (`PlayerArray`, `AgentInfoArray`, `QuestLog`, `SkillbarArray`, `TitleArray` and their neighbours), where GwAu3 hands out a client array this project reaches through a ported class instead, which is a different answer and so is refused rather than approximated. Measured live 2026-10-09: 49 of 49 answered. **`World_GetWorldInfo` takes no record id**: GwAu3's signature is the field name alone, and the layer keeps that shape."),
    "Quest_GetQuestInfo": Route("the layer's own reader", "py4gw/gwa3/data_quest.py:250", "read", "**Routed inside the layer, and live-verified.** All 22 declared keys are in the table; 16 answer and the other six refuse -- `NPCName`, `Objectives` and the four `*Enc` spellings. Measured live 2026-10-09: 12 answered and 4 -- `Name`, `Location`, `LocationStr`, `Description` -- answered `''` because their decode **cannot start** on a read-only connection: `Quest.RequestQuestName` reaches `_start` (`py4gw/native_src/quest/py_quest.py:242-259`), which catches the bridge's refusal and leaves the store at `(\"\", False)`, indistinguishable from a decode still in flight. The item handshake has no such swallow and raises, which is why the two families behave differently. That swallow is the finding, and the fix belongs there rather than in this layer."),

    # --- Friend -------------------------------------------------------------------------
    "Friend_AddFriend": Route("", "", "", "GAME-THREAD CALL in GwAu3 (its own injected stub calls the native). The client's own route in Stealth has not been located; note GwAu3's version never returns True (`GwAu3_Cmd_Friend.au3`)."),
    "Friend_RemoveFriend": Route("", "", "", "ROUTE NOT RECORDED -- as above."),
    "Friend_AddIgnore": Route("", "", "", "ROUTE NOT RECORDED -- as above."),
    "Friend_RemoveIgnore": Route("", "", "", "ROUTE NOT RECORDED -- as above."),
    "Friend_GetFriendInfo": Route("the layer's own reader", "py4gw/gwa3/data_friend.py:223", "read", "**Routed inside the layer for the keys whose offsets agree, and refused for the six whose offsets do not.** `Type`, `Status`, `UUID`, `Name`/`Alias` and the computed keys answer from `py4gw/context/friend_list_context.py`. `ConnectedName`/`CharName`/`Playing`, `FriendID` and `MapID`/`ZoneID` **refuse**: GwAu3 reads them at `+0x2C`, `+0x40` and `+0x44`, while this project's `FriendStruct` declares `charname` at `+0x40`, `friend_id` at `+0x68` and `zone_id` at `+0x6C`. A 20-character wide string is 40 bytes, so the port's `alias` spans `+0x18` to `+0x40` and its `charname` starts exactly where GwAu3 puts `FriendID`; GwAu3's layout is consistent only if its strings are ten characters wide. **The two disagree about the client and this layer will not choose for them** -- the finding is recorded for the owner in `docs/GWA3_COMPAT_SPEC.md`."),

    # --- Ui: the second implementation of the same actions -------------------------------
    "Ui_SetHeroBehavior": Route(
        "Heroes.SetHeroBehavior", "py4gw/party.py:1707-1717", "M1 / party.set_hero_behavior_func",
        "**Default differs between spellings:** `Ui_SetHeroBehavior` defaults `$a_i_Behavior` to 1 (`GwAu3_Cmd_Ui.au3:128`) while `Party_SetHeroAggression` has no default.",
    ),
    "Ui_SetDifficulty": Route("Party.SetHardMode / SetNormalMode", "py4gw/party.py:1193-1210", "M1 / party.set_difficulty_func"),
    "Ui_EnterChallenge": Route("Map.EnterChallenge", "py4gw/map.py:913", "M2 packed / kSendEnterMission"),
    "Ui_LeaveGroup": Route("Party.LeaveParty", "py4gw/party.py:1293-1304", "M3/M1 party callback", "Leaves then kicks -- the reverse of `Party_LeaveGroup`."),
    "Ui_AddHero": Route("Heroes.AddHero", "py4gw/party.py:1529-1537", "M3/M1 party callback"),
    "Ui_KickHero": Route("Heroes.KickHero", "py4gw/party.py:1550-1560", "M3/M1 party callback"),
    "Ui_KickAllHeroes": Route("Heroes.KickAllHeroes", "py4gw/party.py:1569-1576", "M3/M1 party callback"),
    "Ui_AddNPC": Route("Henchmen.AddHenchman", "py4gw/party.py:1723-1731", "M3/M1 party callback"),
    "Ui_KickNPC": Route("Henchmen.KickHenchman", "py4gw/party.py:1734-1743", "M3/M1 party callback"),
    "Ui_CommandHero": Route("Heroes.FlagHero", "py4gw/party.py:1612-1623", "M1 / party.flag_hero_agent_func"),
    "Ui_CommandAll": Route("Heroes.FlagAllHeroes", "py4gw/party.py:1626-1630", "M1 / party.flag_all_func"),
    "Ui_CancelHero": Route("Heroes.UnflagHero", "py4gw/party.py:1633-1643", "M1"),
    "Ui_CancelAll": Route("Heroes.UnflagAllHeroes", "py4gw/party.py:1646-1652", "M1"),
    "Ui_LockHeroTarget": Route("", "", "", "ROUTE NOT RECORDED -- GwAu3's Ui path calls its own in-client stub; the Stealth member for locking a hero's target has not been located."),
    "Ui_DisableHeroSkill": Route("Heroes.SetSkillAIEnabled(False)", "py4gw/party.py:1599-1609", "M1"),
    "Ui_EnableHeroSkill": Route("Heroes.SetSkillAIEnabled(True)", "py4gw/party.py:1599-1609", "M1"),
    "Ui_ToggleHeroSkillState": Route("Heroes.SetSkillAIEnabled (read then set)", "py4gw/party.py:1599-1609", "M1"),
    "Ui_OpenChest": Route("", "", "", "ROUTE NOT RECORDED -- GwAu3's Ui path calls its own in-client stub."),
    "Ui_Dialog": Route("Player.SendRawDialog", "py4gw/player.py:1254-1269", "M1 / agent.send_agent_dialog_func"),
    "Ui_Interact": Route("Player.SendRawDialog / Interact", "py4gw/player.py:1140-1185, :1254-1269", "M1"),
    "Ui_DisableRendering": Route("", "", "", "**NOT APPLICABLE to the client.** GwAu3's flag lives in its own injected code block (the inventory records `$g_b_DisableRendering` as a slot in the injected block, not a client field), so there is no client state to route at all. Stealth has no equivalent injected block to hold such a flag."),
    "Ui_EnableRendering": Route("", "", "", "As `Ui_DisableRendering`: the flag is GwAu3's own, in its own injected block."),
    "Ui_GetRenderDisabled": Route("", "", "", "Reports a flag in GwAu3's own injected block; nothing to route."),
    "Ui_GetRenderEnabled": Route("", "", "", "As above."),
    "Ui_ToggleRendering": Route("", "", "", "**NOT APPLICABLE / needs care.** GwAu3 toggles its own injected-block flag and also calls `WinSetState` on the game window and `Memory_Clear` (`SetProcessWorkingSetSize`) on the client's handle (`GwAu3_Cmd_Ui.au3:247-256`). Stealth has no injected-block flag; the window-state and working-set calls are host-side Win32, not game actions."),
    "Ui_PurgeHook": Route("", "", "", "**NOT APPLICABLE.** GwAu3 purges its own injected hook's queue; Stealth has no equivalent queue to purge (its shared block is drained by the dispatcher)."),

    # --- Trade --------------------------------------------------------------------------
    "Trade_InitiateTrade": Route("", "", "", "ROUTE NOT RECORDED -- GwAu3's plain spelling uses `Trade_CallSession` against a native; the Stealth member has not been located."),
    "Trade_InitiateTrade_": Route("", "", "", "**REFUSED.** This is GwAu3's *packet* spelling -- its implementation hands a record to its injected stub, which runs `call PacketSend` (`GwAu3_Core_Assembler.au3:2095`). Stealth forges no packets. The row's native twin is the one a caller should get, and it is a separate row in this map."),
    "Trade_AcceptTrade": Route("", "", "", "ROUTE NOT RECORDED -- native spelling."),
    "Trade_AcceptTrade_": Route("", "", "", "**REFUSED.** Packet spelling."),
    "Trade_SubmitOffer": Route("", "", "", "ROUTE NOT RECORDED -- native spelling."),
    "Trade_SubmitOffer_": Route("", "", "", "**REFUSED.** Packet spelling."),
    "Trade_CancelTrade": Route("", "", "", "ROUTE NOT RECORDED -- native spelling."),
    "Trade_CancelTrade_": Route("", "", "", "**REFUSED.** Packet spelling."),
    "Trade_ChangeOffer_": Route("", "", "", "**REFUSED.** Exists only as a packet spelling in GwAu3 -- there is no native twin to route."),
    "Trade_OfferItem": Route("", "", "", "ROUTE NOT RECORDED -- takes an item, converts through `Item_ItemID`."),
    "Trade_OfferItem_": Route("", "", "", "Packet spelling; and it differs in *parameter kind* -- it takes an item ID where the plain spelling takes an item."),
    "Trade_RevokeItem": Route("", "", "", "ROUTE NOT RECORDED -- native only."),
    "Trade_RevokeOffer": Route("", "", "", "ROUTE NOT RECORDED -- native only."),
    "Trade_RevokeAccept": Route("", "", "", "ROUTE NOT RECORDED -- native only."),
    "Trade_GetTradePartner": Route("", "", "", "MEMORY READ; note GwAu3's version *clears the slot it reads* (`GwAu3_Cmd_Trade.au3:42`), so two calls never return the same value. The layer must reproduce that."),
}

# ---------------------------------------------------------------------------------------------
# `UtilityAI_GetAgent.au3`: the twenty-six targeting and positioning queries (2026-10-10).
#
# All twenty-six are one shape -- a loop over the agents GwAu3 would have cached, the filter string
# `_ApplyFilters` resolves, and an answer that is an agent id, a coordinate triple or a boolean --
# and **none of them touches the client directly**: every read goes through
# `py4gw/gwa3/uai_agent.py`, whose own routes are recorded above. So the route for each is the ported
# function itself, over the same live agent reads, and the citation is the line it stands on. Two of
# them also *act*, and their route is the already-routed movement action; the one refusal refuses for
# a member this layer does not have yet, and says which.
#
# Recorded as a table rather than twenty-six copies of the same `Route`, because the claim is the
# same claim: a reviewer reading one row reads them all, and the two exceptions are named below.
# ---------------------------------------------------------------------------------------------

_UAI_GET_AGENT_LINES: dict[str, int] = {
    # Two of the module's twenty-six are **not** rows here, because this map's universe is the union of
    # GwAu3's `Modules/{Cmd,Data}` declarations and the functions its own scripts call -- and
    # `UAI_GetBestTargetByDamageType` and `UAI_GetBestAOETargetByDamageType`
    # (`UtilityAI_GetAgent.au3:315`, `:355`) are in neither: GwAu3 declares them and nothing calls them.
    # They are ported and tested all the same, in `py4gw/gwa3/uai_get_agent.py`.
    "UAI_ConvertAgentID": 134,
    "UAI_FindAgentByPlayerNumber": 144,
    "UAI_CountAgents": 186,
    "UAI_IsAgentInRange": 226,
    "UAI_GetNearestAgent": 262,
    "UAI_GetFarthestAgent": 293,
    "UAI_GetAgentLowest": 322,
    "UAI_GetAgentHighest": 363,
    "UAI_GetBestSingleTarget": 398,
    "UAI_GetBestAOETarget": 419,
    "UAI_GetBestWardPosition": 743,
    "UAI_GetBestOffensiveWardPosition": 769,
    "UAI_GetBestMartialEnemyPosition": 791,
    "UAI_PlayerHasOtherMesmerHex": 861,
    "UAI_GetBestCorpseForAllySupport": 991,
    "UAI_GetBestCorpseForEnemyPressure": 998,
    "UAI_IsCorpseNearest": 1047,
}

_UAI_GET_AGENT_NOTE = (
    "Routed inside the layer, and the claim is a shape: GwAu3 walks its own per-frame agent cache and "
    "this walks the client's agent array, asking the same questions in the same order (`_ApplyFilters` "
    "for the filter strings, the cache's own `Sqrt((X - PlayerX)^2 + (Y - PlayerY)^2)` for the "
    "`Distance` column, `$g_i_FightMode` read at call time from `py4gw/gwa3/uai_const.py`). The "
    "source's quirks are kept and are tested by name: `UAI_GetAgentLowest`'s unused reference id, and "
    "`UAI_MoveTowardCorpse`'s `True` on a timeout."
)

for _name, _line in _UAI_GET_AGENT_LINES.items():
    ROUTES[_name] = Route(
        "the layer's own function", f"py4gw/gwa3/uai_get_agent.py:{_line}", "read", _UAI_GET_AGENT_NOTE
    )

ROUTES["UAI_MoveToWardPosition"] = Route(
    "Map_Move", "py4gw/gwa3/cmd_map.py:55-72", "M1 / agent.move_to_func",
    "The search is the layer's own and the move is `Map_Move`, which is routed above. GwAu3 issues it "
    "**once** and then watches for arrival (`UtilityAI_GetAgent.au3:588-594`), bounded at five seconds; "
    "the port keeps that order, because a move per iteration would restart the path.",
)

ROUTES["UAI_MoveTowardCorpse"] = Route(
    "Map_Move", "py4gw/gwa3/cmd_map.py:55-72", "M1 / agent.move_to_func",
    "As `UAI_MoveToWardPosition`, except that GwAu3 re-issues the move every iteration while it re-asks "
    "`UAI_IsCorpseNearest` (`UtilityAI_GetAgent.au3:762-776`), and that its bounded loop answers `True` "
    "on a timeout as well as on success (`:778`). Both are kept.",
)

ROUTES["UAI_GetBestTargetByConditionCount"] = Route(
    "the layer's own function",
    "py4gw/gwa3/uai_get_agent.py:889",
    "read",
    "**Routed, and it was the last targeting query that refused.** It scores each conditioned agent by "
    "how many of seven status effects it carries, one `UAI_AgentHasVisibleEffect` call per effect "
    "(`UtilityAI_GetAgent.au3:643-646`), and that member is now ported (`py4gw/gwa3/uai_effects.py`) "
    "over the agent's own visible-effect list. The earlier refusal named this same function as the work "
    "item and refused rather than count the agent record's condition bits, which are a different test. "
    "The walk is over the live agents rather than GwAu3's cache rows, which is this file's convention "
    "for `For $i = 1 To $g_i_AgentCacheCount`.",
)

# ---------------------------------------------------------------------------------------------
# `GwAu3_Data_Party.au3`'s party-member accessors (2026-10-10).
#
# The context record's ``+0x54`` is a pointer to the party object, and these read *through* it -- which
# this layer now does (`PartyContextStruct.player_party`, `py4gw/context/party_context.py:357-367`), over
# the member records whose strides are GwAu3's own: `PlayerPartyMember` ``0xC``, `HeroPartyMember`
# ``0x18``, `HenchmanPartyMember` ``0x34``. They are the piece the UtilityAI engine's party layer needed.
# ---------------------------------------------------------------------------------------------

_PARTY_MEMBER_NOTE = (
    "Routed inside the layer: the accessor is written in `py4gw/gwa3/data_party.py` (carried from "
    "`tools/gwa3_snippets/data_party_my_party.py`) over `py4gw/context/party_context.py`'s member "
    "records, whose sizes are the strides GwAu3 multiplies by. GwAu3's own guards are kept, one-based "
    "member numbers and all."
)

ROUTES["Party_GetMyPartyInfo"] = Route(
    "the layer's own function", "py4gw/gwa3/data_party.py:239", "read",
    _PARTY_MEMBER_NOTE + " Its five scalar keys answer the party record's own fields; the four "
    "``Array*PartyMember`` keys still refuse -- each names the property that answers the members a "
    "caller wants, because what GwAu3 returns there is a client address.",
)

for _name, _line, _route_line in (
    ("Party_GetMyPartyPlayerMemberInfo", 100, 280),
    ("Party_GetMyPartyHeroInfo", 131, 320),
    ("Party_GetMyPartyHenchmanInfo", 179, 386),
):
    ROUTES[_name] = Route(
        "the layer's own function",
        f"py4gw/gwa3/data_party.py:{_route_line}",
        "read",
        _PARTY_MEMBER_NOTE + f" GwAu3 declares it at ``GwAu3_Data_Party.au3:{_line}``.",
    )

# ---------------------------------------------------------------------------------------------
# `UtilityAI_Utils.au3`'s party layer (2026-10-10).
#
# The engine's aggro questions and the called target a FOLLOW-mode fight copies. Each is a loop over the
# party's member records and the world's hero-flag array -- both routed in `py4gw/gwa3/data_party.py` --
# and each answers through the *already routed* targeting queries (`UAI_GetNearestAgent`,
# `UAI_IsAgentInRange`, `UAI_CountAgents`) with `_ApplyFilters` resolving the filter strings.
# ---------------------------------------------------------------------------------------------

_ENGINE_PARTY_NOTE = (
    "Routed inside the layer: `py4gw/gwa3/uai_utils.py`, over `py4gw/gwa3/data_party.py`'s member and "
    "hero-flag accessors and the targeting queries in `py4gw/gwa3/uai_get_agent.py`. GwAu3's guard order "
    "is kept, including the skip of a hero that stands where it was flagged."
)

#
# Three of the file's members -- `Party_GetSize`, `Party_GetHeroAgentID`, `Party_GetHeroID` -- are
# **not** rows here: this map's universe is the union of GwAu3's `Modules/{Cmd,Data}` declarations and
# the functions its own scripts call, and those three are in neither (GwAu3 declares them in this file
# and calls them from nowhere). They are ported and tested all the same, in `py4gw/gwa3/uai_utils.py`.
for _name, _line, _route_line in (
    ("UAI_CountEnemyInPartyAggroRange", 29, 336),
    ("UAI_IsEnemyInPartyAggroRange", 51, 374),
    ("UAI_GetNearestEnemyInPartyRange", 76, 408),
    ("UAI_GetPartyCalledTarget", 131, 475),
    ("Party_GetHeroCount", 148, 304),
):
    ROUTES[_name] = Route(
        "the layer's own function",
        f"py4gw/gwa3/uai_utils.py:{_route_line}",
        "read",
        _ENGINE_PARTY_NOTE + f" GwAu3 declares it at ``UtilityAI_Utils.au3:{_line}``.",
    )

# `GwAu3_Data_Skill.au3`'s skillbar reader (2026-10-10): the stride walk UtilityAI's slot loop asks what
# is on a skillbar, and the clock a slot's recharge is measured against. Both are over the port's own
# structures, whose strides are GwAu3's -- `SkillbarStruct` ``0xBC``, `SkillbarSkillStruct` ``0x14``.
ROUTES["Skill_GetSkillbarInfo"] = Route(
    "the layer's own function", "py4gw/gwa3/data_skill.py:276", "read",
    "Routed inside the layer (`tools/gwa3_snippets/data_skill_skillbar.py`): the world's skillbar array "
    "matched on agent id, every one of GwAu3's seventeen keys answered from the record the port names. "
    "Two of them (`SlotBySkillID`, `HasSkillID`) answer `0` for any real skill id, because the source's "
    "own guard rejects a slot number outside `1..8` before its `Case` -- kept as written, and recorded "
    "on the member.",
)

ROUTES["Skill_GetSkillTimer"] = Route(
    "the client's own skill timer", "py4gw/memory/memory_manager.py:126", "read",
    "GwAu3 computes `GetTickCount() + $g_i_GWExeStart` masked to 32 bits; this project reads the same "
    "sum through the connection (`client.memory_manager.GetSkillTimer`), which is the client global the "
    "catalog names `memory.skill_timer_ptr`. The same number, so the recharge keys are the source's own "
    "arithmetic.",
)

# The static skill cache (2026-10-10): the skillbar's skill data, which every per-skill decision reads.
# In this port the table is not kept -- the accessors read the live slot and the live skill record at the
# point of use, the same substitution the agent columns make (see *Caching* in the spec).
for _name, _line, _route_line in (
    ("UAI_StaticDataSkill", 56, 134),
    ("UAI_CacheSkillBar", 109, 203),
    ("UAI_SlotIsPriority", 185, 158),
    ("UAI_GetStaticSkillInfo", 208, 108),
):
    ROUTES[_name] = Route(
        "the layer's own function",
        f"py4gw/gwa3/uai_static_skill_cache.py:{_route_line}",
        "read",
        "Routed inside the layer over `py4gw/gwa3/data_skill.py`'s skillbar reader and skill-table "
        "reader -- the same two reads GwAu3's cache made, taken when they are asked for rather than once "
        "per skillbar change. The three conversions the source performs *while caching* (``Overcast``, "
        "``EnergyCost``, ``Aftercast``) are performed on the value instead. "
        f"GwAu3 declares it at ``UtilityAI_StaticSkillCache.au3:{_line}``.",
    )

# `Skill_CheckSlotByID` is **not** a row here: this map's universe is the union of GwAu3's
# `Modules/{Cmd,Data}` declarations and the functions its own scripts call, and that one is in neither.
# It is ported and tested all the same, in `py4gw/gwa3/uai_utils.py`.
ROUTES["Skill_GetSlotByID"] = Route(
    "the layer's own function",
    "py4gw/gwa3/uai_utils.py:298",
    "read",
    "Routed inside the layer: the eight slots walked in order, each asked for its ``SkillID`` through "
    "`Skill_GetSkillbarInfo`. GwAu3 declares it at ``UtilityAI_Utils.au3:10``.",
)

# The item family's inventory readers (2026-10-10): what ``Equipment/UtilityAI_WeaponSets.au3`` reads the
# four weapon sets through. Both are `GwAu3_Data_Item.au3` declarations -- `Item_GetInventoryPtr` at
# ``:10-14``, `Item_GetInventoryInfo` at ``:16-160`` -- over the port's own `InventoryStruct`, whose
# offsets are asserted field for field in `py4gw/context/item_context.py:1626-1647`.
ROUTES["Item_GetInventoryPtr"] = Route(
    "the layer's own reader",
    "py4gw/gwa3/data_item.py:474",
    "read",
    "Routed inside the layer: ``BasePointer[0x18][0x40][0xF8]`` read as `client.read_inventory`, which "
    "materializes the client's own `InventoryStruct`. `None` is GwAu3's zero pointer, which is what a "
    "client with no character in a map answers.",
)

ROUTES["Item_GetInventoryInfo"] = Route(
    "the layer's own reader",
    "py4gw/gwa3/data_item.py:631",
    "read",
    "Routed inside the layer: every key of GwAu3's ``Switch`` is in the two tables -- the forty-four bag "
    "names (reaching `Item_GetBagPtr` with the array index GwAu3's own offset gives them) and the "
    "thirty-six weapon/offhand/bundle keys. **The pointer keys answer the record the pointer addresses** "
    "rather than a client address, the divergence `Item_GetItemPtr` and `Item_GetBagPtr` already record, "
    "and `None` is GwAu3's zero pointer; the three counters (`ActiveWeaponSet`, `GoldCharacter`, "
    "`GoldStorage`) answer the structure's own fields.",
)

ROUTES["Item_GetModStruct"] = Route(
    "the layer's own reader",
    "py4gw/gwa3/data_item.py:682",
    "read",
    "**Routed, with one finding on its argument.** The source reads the record's ``ModStruct`` pointer "
    "and then ``Byte[ModStructSize * 4]`` at it (`GwAu3_Data_Item.au3:776-781`); the port reads the same "
    "bytes at the same address and answers them in the same text form -- AutoIt's binary value, whose "
    "string form is ``0x`` plus upper-case hex, which is what `UAI_SearchModsInArray` searches "
    "(`tests/scratch/_probe_modstruct.au3` records the measurement). **The finding**: the source hands "
    "its argument straight to `Item_GetItemInfoByPtr`, which reads it as an *address*, while "
    "``UtilityAI_WeaponSets.au3:107-119`` passes an **item id**; this member resolves the item its "
    "caller holds (`Item_GetItemPtr`), which is what the source's caller means by it, and the reading "
    "of ``id + 0x10`` is measured by `tests/probe_gwa3_inventory_live.py`.",
)

# The item family's inventory-id and array-count readers, and the merchant family's trader slots
# (2026-10-10, the owner's ruling that *"stealth owns the data now, if stealth has access we use stealth
# access no matter what gwau3 says"*). Each was refused until this pass; these rows record where the fact
# now comes from, and `Merchant_GetBuyItemBase` stays unreached with its missing read named.
ROUTES["Item_GetItemInventoryID"] = Route(
    "the layer's own reader",
    "py4gw/gwa3/data_item.py:1040",
    "read",
    "Routed inside the layer, and what differs is the *name* of the answered word. GwAu3 walks the item "
    "to its bag (``+0xC``, then ``+0x8`` when that is null, `GwAu3_Data_Item.au3:541-542`), the bag to "
    "the inventory that owns it (``+0x14``, `:545`) and answers that record's first dword (``:547``). "
    "Every step is a field this project names -- `ItemStruct.bag`/`bag_equipped`, `BagStruct.bag_array` "
    "and `InventoryStruct.unused_bag`, element ``0`` of the inventory's 23-entry bag array -- so the "
    "value is the same dword with no client address crossing the layer, and ``0`` stands at each of "
    "GwAu3's own guards. GwAu3 calls it the inventory *id*; this project names the same word "
    "`unused_bag`, and GwAu3's own `Item_GetBagPtr(0)` reads it as a bag pointer. Checked offline against "
    "a stand-in client (`tests/scratch/_check_stealth_owned_reads.py`); a live read is owed.",
)

ROUTES["Item_GetInventoryIDByAgentID"] = Route(
    "the layer's own reader",
    "py4gw/gwa3/data_item.py:1080",
    "read",
    "Routed inside the layer, both arms. The controlled character answers the inventory record's first "
    "dword, as the row above does. Anyone else walks the **hero flag array** -- which GwAu3 reaches by "
    "*address* (`World_GetWorldInfo(\"HeroFlagArray\")`, a key this layer refuses under that name) and "
    "strides by ``0x24`` (`GwAu3_Data_Item.au3:906-913`) -- through "
    "`WorldContextStruct.hero_flags` (`py4gw/context/world_context.py:1824-1828`), whose entries are the "
    "same ``0x24`` bytes with `agent_id` at ``+0x4`` exactly where GwAu3 compares it. **The finding is "
    "on the source**: GwAu3 calls the entry's ``+0x8`` the hero's inventory id, while this project's "
    "`HeroFlagStruct` gives that word Reforged's own name, `level` "
    "(`py4gw/context/world_context.py:733`) -- so `Item_GetHeroEquippedItemPtr` (`:925-930`), the only "
    "caller, compares a hero's level against an item's inventory word.",
)

ROUTES["Item_GetMaxItems"] = Route(
    "the layer's own reader",
    "py4gw/gwa3/data_item.py:1125",
    "read",
    "Routed inside the layer: GwAu3's ``BasePointer[0][0x18][0x40][0xB8 + 0x8]`` "
    "(`GwAu3_Data_Item.au3:739-743`) is `ItemContextStruct.item_array.m_size` -- the item context's own "
    "``GWArray`` sits at exactly ``+0xB8`` (`py4gw/context/item_context.py:1478`, asserted at ``:1645``) "
    "and the port reads it through `ConnectedClient.read_item_context` (`py4gw/client.py:1610`). "
    "GwAu3's name says *MaxItems*; the word it reads is the array's **size**, one word after its "
    "capacity. The port's own `global_items` warns that the live header may advertise a number that is "
    "not an inventory-item count, which is GwAu3's number and GwAu3's caveat both.",
)

ROUTES["Merchant_GetTraderQuoteID"] = Route(
    "the layer's own derived change detector",
    "py4gw/gwa3/data_merchant.py:113",
    "read",
    "**Derived in the layer, because the fact is GwAu3's own controller-side state and the layer never "
    "hooks the library to borrow it** -- the dependency runs one way only, the layer importing the "
    "library (`py4gw/gwa3/__init__.py:5-6`). GwAu3's slot lives in its injected block "
    "(`GwAu3_Core_Assembler.au3:1917`) and its `TraderProc` detour advances it on the client's trader "
    "call, wrapping at 200 (`:2045-2051`); a script reads it, requests the quote and polls until it "
    "moves (`GwAu3_Cmd_Merchant.au3:76`, `:89`, `:95`). This layer installs no detour, so the member "
    "derives the same detector from the quote it already reads -- `MerchantListener` through "
    "`Trading.Trader.GetQuotedItemID`/`GetQuotedValue`, the two readers the cost getters use -- and the "
    "number moves when the **standing** quote it observes changes, holding still across the no-quote "
    "state (`-1`), so a caller's read-request-poll loop ends on a real quote rather than on the request. "
    "The cost is on the member: a repeat quote of the same item at the same price does not move it, "
    "where a call-counting slot would.",
)

ROUTES["Merchant_GetTraderQuoteInfo"] = Route(
    "the layer's own readers",
    "py4gw/gwa3/data_merchant.py:196",
    "read",
    "Routed inside the layer: ``[quoteID, costID, costValue]`` in GwAu3's own order, from "
    "`Merchant_GetTraderQuoteID`, `Merchant_GetTraderCostID` and `Merchant_GetTraderCostValue` -- the "
    "same three reads GwAu3's body makes one ``Memory_Read`` at a time (`GwAu3_Data_Merchant.au3:22-24`).",
)

ROUTES["Merchant_GetSalvageGlobal"] = Route(
    "the layer's own reader",
    "py4gw/context/salvage_context.py:76",
    "read",
    "Routed to the **data**, not the address. GwAu3 answers ``$g_p_SalvageGlobal``, the client buffer "
    "its own salvage stub writes the item id and the kit item id into before the client's `Salvage` call "
    "(`GwAu3_Core_Assembler.au3:2388-2401`; this project's own source review records that the global is a "
    "write target and is never read back for state, `docs/RESEARCH.md:2256-2258`). This layer hands out "
    "no client address, so the member answers the item id of the client's own salvage session -- "
    "`SalvageSessionInfoStruct.item_id`, read through `ConnectedClient.read_salvage_session` "
    "(`py4gw/client.py:1344`) -- which is the same *which item is being salvaged* fact, and ``0`` while "
    "no session is open. The session record's `kit_id` is the sibling word.",
)

ROUTES["Merchant_GetBuyItemBase"] = Route(
    "",
    "",
    "",
    "**NO ROUTE YET, and the missing read is named.** GwAu3 answers ``$g_p_BuyItemBase``, a client "
    "address its own scan resolves (`GwAu3_Core.au3:241`); its only use of the value is a buy-record "
    "field the injected stub then never passes to the client (`GwAu3_Cmd_Merchant.au3:151`, "
    "`GwAu3_Core_Assembler.au3:2243-2263`). This project resolves no such pattern -- `offsets/merchant.json` "
    "carries only `transact_item_func` and `request_quote_func` -- and reads no record through the "
    "address, because its own buy path places its request record in the game-thread block "
    "(`py4gw/merchant.py:189-196`). The member refuses and names its two missing reads: a resolved "
    "`BuyItemBase` address **and** a named record for what it points at. The data a caller is usually "
    "after -- the merchant's offered items -- is routed by `Merchant_GetMerchantItemsSize` and "
    "`Merchant_GetMerchantItemPtr`.",
)

ROUTES["Map_GetMapContextInfo"] = Route(
    "the layer's own reader",
    "py4gw/gwa3/data_map_context.py:83",
    "read",
    "Routed inside the layer for six of its eight keys. `MapBoundaries` answers the five floats through "
    "the port's own read of them; `Sub1` and `PropsContext` answer the **records** the two words point at "
    "rather than the addresses GwAu3 answers (`MapContextStruct.path_context` and `.props`); "
    "`Spawns1`/`Spawns2`/`Spawns3` answer the spawn records the arrays hold. **Two keys refuse and now "
    "name their missing read**: `Terrain` (``+0x84``) and `Zones` (``+0x130``) are words this project "
    "names and reads no record through -- no structure here describes what they point at -- so there is "
    "nothing to materialize in the address's place, and GwAu3's own only caller prints the number "
    "(`GwAu3_DevTools.au3:2564-2565`).",
)

# The four weapon sets (2026-10-10): `Equipment/UtilityAI_WeaponSets.au3`, eighteen functions, all of
# them in `py4gw/gwa3/uai_weaponsets.py`. The file splits three ways and the rows say which way each
# function goes: the analysis is reads over the item family above, the decisions are arithmetic over the
# tables in `py4gw/gwa3/uai_const.py`, and the switch is the one enqueue this project does not perform.
_WEAPON_SET_ANALYSIS_NOTE = (
    "Routed inside the layer: the four sets' weapons are pointers in the client's own `InventoryStruct` "
    "and their mods are the bytes at the end of each item record, both read through "
    "`py4gw/gwa3/data_item.py`; the scores are the source's own weights, its own tables and its own "
    "strike-the-mod-out rule, and the trackers it fills live in `py4gw/gwa3/uai_const.py` with GwAu3's "
    "initial values. `tests/test_gwa3_uai_weaponsets_offline.py` drives the whole analysis on real "
    "upgrade bytes, and `tests/test_gwa3_uai_const_offline.py` checks all 298 table rows against the "
    "source's own text."
)

# `UAI_GetWeaponSetForSituation` is **not** a row here: this map's universe is the union of GwAu3's
# `Modules/{Cmd,Data}` declarations and the functions its own code calls, and that one is in neither --
# it is declared at ``UtilityAI_WeaponSets.au3:465`` and nothing in the checkout calls it, so it appears
# nowhere but its own declaration. It is ported and tested all the same, in
# `py4gw/gwa3/uai_weaponsets.py`.
for _name, _line in (
    ("UAI_DetermineWeaponSets", 108),
    ("UAI_SaveWeaponSetFromMemory", 164),
    ("UAI_FindAndSaveModFromMemory", 290),
    ("UAI_FindWeaponSetByType", 356),
    ("UAI_GetBestWeaponSetForCombat", 511),
    ("UAI_IsOnWeaponSet", 799),
    ("UAI_IsTwoHandedWeapon", 823),
    ("UAI_IsRangedWeapon", 841),
    ("UAI_GetWeaponTypeName", 859),
    ("UAI_GetOffhandTypeName", 883),
    ("UAI_WeaponReqToItemType", 485),
    ("UAI_ExtractHPBonus", 769),
    ("UAI_ExtractEnergyBonus", 789),
):
    ROUTES[_name] = Route(
        "the layer's own function",
        f"py4gw/gwa3/uai_weaponsets.py:{_line}",
        "read",
        _WEAPON_SET_ANALYSIS_NOTE,
    )

ROUTES["UAI_SearchModsInArray"] = Route(
    "the layer's own function",
    "py4gw/gwa3/uai_weaponsets.py:669",
    "read",
    _WEAPON_SET_ANALYSIS_NOTE + " **Its ``ByRef`` out-parameters are its return value**: "
    "``$a_s_NewModStruct`` and ``$a_i_Finding`` are written throughout the loop and Python strings and "
    "integers cannot be shared with a caller, so the member returns them as a pair -- the same twin this "
    "layer documents for ``@extended``. AutoIt's ``StringInStr`` and ``StringReplace`` are "
    "case-insensitive and the port's `_contains`/`_replace` keep that.",
)

for _name, _line in (
    ("UAI_GetBestWeaponSetBySkillSlot", 383),
    ("UAI_ShouldSwitchWeaponSet", 565),
):
    ROUTES[_name] = Route(
        "the layer's own function",
        f"py4gw/gwa3/uai_weaponsets.py:{_line}",
        "read",
        "**The decision is ported, and so is the switch it may ask for.** Every threshold and every "
        "case is the source's, over `py4gw/gwa3/uai_const.py`'s trackers, and the answer is by effect as "
        "it is in GwAu3 -- including the paths that decide to leave the set alone. When a set *is* "
        "chosen this reaches `UAI_ChangeWeaponSet`, whose own row below is the routed switch, so the "
        "switch happens exactly where the source's line is rather than at this call.",
    )

ROUTES["UAI_ChangeWeaponSet"] = Route(
    "UIManager.Keydown / UIManager.Keyup (the client's own control action)",
    "py4gw/gwa3/uai_weaponsets.py:639, py4gw/ui_manager.py:1049-1088",
    "M3 / client's button-action frame message",
    "**Routed.** The source's only effect is a switch: a double `Core_PerformAction` cancel and then the "
    "switch action, repeated until the client reports the set (`UtilityAI_WeaponSets.au3:506-521`). "
    "GwAu3's `Core_PerformAction` fills its own action struct and calls `Core_Enqueue`, whose record its "
    "injected stub turns into a call on the client's action table "
    "(`GwAu3_Core_Assembler.au3:2101-2118`) -- a code cave this project does not place. The **action** it "
    "asks for is performed instead the way Reforged performs it for this exact effect: pressed through "
    "the client's own button-action frame message (`Keybinds.ActivateWeaponSet` -> "
    "`Keybinds.PressKeybind(ControlAction_ActivateWeaponSet1.value + index - 1, 75)`, "
    "`routines_src/yield_src/keybinds.py:110-113`; down and up at "
    "`routines_src/behaviourtrees_src/keybinds.py:101,119`), which is the pair `py4gw/map.py:1013-1014` "
    "already ports for a control action. So the four codes this row's `Switch` selects -- 129-132 -- are "
    "pressed, the two cancels are pressed, and the already-on-this-set quick check that precedes them is "
    "the source's own, so a caller that asks for the set it is on pays nothing. What the route cannot "
    "carry is GwAu3's flag and type words; `py4gw/gwa3/core.py`'s `Core_PerformAction` states which two "
    "values it therefore refuses.",
)

# ---------------------------------------------------------------------------------------------
# The UtilityAI plugin's remaining rows (2026-10-10).
#
# Measured before writing this: **96 of the plugin's 145 rows had no route recorded**, and 79 of
# those 96 are members `py4gw/gwa3/` already implements -- `UAI_CanUse`, the `UAI_Filter_*`
# predicates, the `Anti_*` guards, the engine's own members and the party helpers behind it. So this
# is a **map** gap rather than a porting gap for most of them, and leaving it would have made the map
# report a built layer as unbuilt. The other 17 are GwAu3's per-frame cache machinery.
#
# The classification is the layer's own, not a guess: a member whose body refuses is REFUSED, one
# whose port answers nothing because what it maintains is controller-side state is NOT APPLICABLE, and
# the rest are ROUTED against the member that does the work -- with the line **resolved at generation
# time** from that member's own `def`, so a citation cannot drift when a module is edited.
# `tests/scratch/_emit_route_rows.py` and `_classify_plugin_rows.py` are the tools that produced the
# three lists.
# ---------------------------------------------------------------------------------------------

# `UAI_PlayerHasVisibleEffect`, `UAI_GetAgentVisibleEffectInfo`, `UAI_GetPlayerVisibleEffectInfo`,
# `UAI_GetAgentVisibleEffectCount` and `UAI_GetPlayerVisibleEffectCount` are **not** rows here: this
# map's universe is the union of GwAu3's `Modules/{Cmd,Data}` declarations and the functions its own
# code calls, and none of those five is in either -- they are declared in
# ``UtilityAI_EffectsCache.au3:494-547`` and called by nothing in the checkout. They are ported and
# tested all the same, in `py4gw/gwa3/uai_effects.py`, because they are the same walk as the one row
# that *is* called (`UAI_AgentHasVisibleEffect`).
_UAI_LAYER_ROUTES: dict[str, tuple[str, ...]] = {
    "uai_agent": (
        "UAI_GetAgentInfo",
        "UAI_GetAgentInfoByID",
        "UAI_GetPlayerInfo",
    ),
    "uai_anti": (
        "Anti_Attack",
        "Anti_Chant",
        "Anti_EchoRefrain",
        "Anti_Enchantment",
        "Anti_Form",
        "Anti_Glyph",
        "Anti_Hex",
        "Anti_ItemSpell",
        "Anti_PetAttack",
        "Anti_Preparation",
        "Anti_Shout",
        "Anti_Signet",
        "Anti_Spell",
        "Anti_Stance",
        "Anti_Trap",
        "Anti_Ward",
        "Anti_WeaponSpell",
        "Anti_Well",
    ),
    "uai_cache": (
        "Cache_EndFormChangeBuild",
        "Cache_FormChangeBuild",
        "Cache_SkillBar",
    ),
    "uai_can_cast": (
        "UAI_CanAutoAttack",
        "UAI_CanDrop",
        "UAI_CanUse",
        "UAI_IsCastSensible",
        "_UAI_EffectEndingSoon",
    ),
    "uai_core": (
        "UAI_AutoAttack",
        "UAI_DropBundle",
        "UAI_GetIsCastingSkill",
        "UAI_GetIsIdle",
        "UAI_PrioritySkills",
        "UAI_TargetIsValid",
        "UAI_TryUseSkill",
        "UAI_UseSkillEx",
        "UAI_UseSkills",
    ),
    "uai_dynamic_skill_cache": ("UAI_GetDynamicSkillInfo",),
    "uai_effects": (
        "UAI_AgentHasEffect",
        "UAI_AgentHasVisibleEffect",
        "UAI_GetFeederEnchOnTop",
        "UAI_GetPlayerEffectInfo",
        "UAI_PlayerHasEffect",
        "UAI_PlayerHasEffectType",
    ),
    "uai_filter": (
        "UAI_Filter_ExcludeMe",
        "UAI_Filter_IsDazed",
        "UAI_Filter_IsDeadEnemy",
        "UAI_Filter_IsLastStrikeLeadOrOffHand",
        "UAI_Filter_IsLivingAlly",
        "UAI_Filter_IsLivingEnemy",
    ),
    "uai_get_agent": (
        "_GetArmorScore",
        "_UAI_BestCoveragePosition",
        "_UAI_CountAlliesInRange",
        "_UAI_GetBestCorpse",
    ),
    "uai_utils": (
        "Party_GetAvailableRezz",
        "Party_GetAverageHealth",
        "Party_GetMembersArray",
        "Party_IsWiped",
        "UAI_GetAgentProfession",
        "UAI_GetArmorBonus",
        "UAI_GetBaseArmor",
        "UAI_GetDamageMultiplier",
        "UAI_GetEffectiveArmor",
        "UAI_GetElementalArmor",
        "UAI_GetEstimatedCurrentHP",
        "UAI_GetEstimatedMaxHP",
        "UAI_GetPhysicalArmor",
        "UAI_IsCaster",
        "UAI_IsMelee",
        "UAI_IsRanged",
        "_D",
    ),
}

_UAI_LAYER_NOTES: dict[str, str] = {
    "uai_agent": (
        "Routed inside the layer: the agent-cache columns answered from this project's live agent reads "
        "(`py4gw/gwa3/uai_agent.py`), since this project keeps no per-frame row to fill. The one row "
        "*index* GwAu3's cache hands back (`UAI_GetIndexByID`) refuses and says why."
    ),
    "uai_anti": (
        "Routed inside the layer: `py4gw/gwa3/uai_anti.py` holds the twenty-one `Anti_*` guards the "
        "ranking's `If Anti_X() Then Return False` bodies call, each transcribed from its own file in "
        "`API/Plugins/UtilityAI/Skills/`."
    ),
    "uai_cache": (
        "Routed inside the layer: the refresh layer (`py4gw/gwa3/uai_cache.py`) over the live skillbar, "
        "with `Cache_SkillBar` gating on the client's own instance type and calling "
        "`UAI_DetermineWeaponSets` when a script armed `$g_b_CacheWeaponSet`."
    ),
    "uai_can_cast": (
        "Routed inside the layer: the cast gate (`py4gw/gwa3/uai_can_cast.py`) -- `UAI_CanAutoAttack`, "
        "`UAI_CanUse`, `UAI_IsCastSensible` and `UAI_CanDrop`, with the private `_UAI_EffectEndingSoon` "
        "kept under the source's own spelling."
    ),
    "uai_core": (
        "Routed inside the layer: the engine's own members (`py4gw/gwa3/uai_core.py`), including the "
        "slot loop, the per-skill cast, and both `Core_ControlAction` cancels -- the mid-cast one at "
        "`:228` and the attacking-while-it-should-not one at `:106` -- which the layer performs as a "
        "press of the client's own `$GC_I_CONTROL_ACTION_CANCEL_ACTION` through the control-action member "
        "`py4gw/gwa3/core.py` routes (`Core_PerformAction`: Reforged's own `Keybinds.CancelAction` route)."
    ),
    "uai_dynamic_skill_cache": (
        "Routed inside the layer: a slot's live adrenaline words, recharge columns and event, read from "
        "the client's own slot record rather than from a per-frame table."
    ),
    "uai_effects": (
        "Routed inside the layer: presence, counts, the ten property columns, the three effect-type "
        "names, the feeder-enchantment test and **the visible-effect family** -- the agent's own list "
        "walked from its record at the same ``+0x174`` the source's fill walks "
        "(`py4gw/context/agent_array.py`), which is what made seven `UAI_Filter_*` predicates and one "
        "targeting query answerable."
    ),
    "uai_filter": (
        "Routed inside the layer: the `UAI_Filter_*` predicates over the live agent array, with the "
        "filter strings resolved by `_ApplyFilters` exactly as AutoIt's `Call` resolved them -- "
        "including the seven that read GwAu3's visible-effect rows, which now answer from the agent's "
        "own list."
    ),
    "uai_get_agent": (
        "Routed inside the layer: the targeting and positioning helpers (`py4gw/gwa3/uai_get_agent.py`) "
        "-- the armour score, the coverage search and the corpse search."
    ),
    "uai_utils": (
        "Routed inside the layer: the UtilityAI arithmetic (armour, hit points, the damage curve), the "
        "party queries the engine's wipe check needs, and `_D`, all in `py4gw/gwa3/uai_utils.py`."
    ),
}


def _layer_member_line(module: str, name: str) -> int:
    """The line a ported member is defined at, read from its own module at generation time.

    **Resolved rather than written down**, because a hand-typed line drifts the moment the module is
    edited and a drifting citation is worse than none. A name the module does not define is a defect
    in :data:`_UAI_LAYER_ROUTES` and stops the run.
    """

    path = REPO_ROOT / "py4gw" / "gwa3" / f"{module}.py"
    for number, line in enumerate(
        path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
    ):
        if line.startswith(f"def {name}("):
            return number
    raise SystemExit(f"{name} is in the plugin route table but {path} does not define it")


for _module, _names in _UAI_LAYER_ROUTES.items():
    for _name in _names:
        ROUTES[_name] = Route(
            "the layer's own function",
            f"py4gw/gwa3/{_module}.py:{_layer_member_line(_module, _name)}",
            "read",
            _UAI_LAYER_NOTES[_module],
        )

#: The plugin rows whose layer member **refuses**, and why. Each is a `NotImplementedError` in
#: `py4gw/gwa3/` today, so the row is REFUSED rather than routed.
_UAI_LAYER_REFUSALS: dict[str, tuple[str, str]] = {
    "UAI_Filter_IsMinion": (
        "uai_filter",
        "**REFUSED: the NPC flags word.** It answers on `BitAND($l_i_NpcFlags, 0x100)` from the world's "
        "NPC record, and this layer refuses those `NpcArray` columns (`py4gw/gwa3/data_world.py` records "
        "why). The first two conditions are readable; the flag is the predicate.",
    ),
    "UAI_Filter_IsSpirit": (
        "uai_filter",
        "**REFUSED: the NPC flags word**, the same refused `NpcArray` column as `IsMinion` with a "
        "different bit (`0x4000`).",
    ),
    "UAI_Filter_IsNotAvoided": (
        "uai_filter",
        "**REFUSED: it reads GwAu3's own `$g_v_AvoidPlayerNumbers`** -- the plugin's controller-side "
        "avoid list. The global exists in `py4gw/gwa3/uai_const.py`; what is missing is the resolution "
        "of the several shapes the source accepts for it.",
    ),
    "UAI_GetIndexByID": (
        "uai_agent",
        "**REFUSED: a cache row index.** It answers the row GwAu3's own `$g_m_AgentIDToIndex` map holds "
        "for an agent; this project keeps no such map and the number means nothing outside that cache. "
        "Every other accessor in the layer takes an agent id, which is what a caller has.",
    ),
}

#: The plugin rows this layer answers with **nothing**, because what they maintain is GwAu3's own
#: controller-side state rather than a client fact.
_UAI_LAYER_NOT_APPLICABLE: dict[str, tuple[str, str]] = {
    "UAI_UpdateAgentCache": (
        "uai_cache",
        "**NOT APPLICABLE: it refills GwAu3's per-frame agent cache.** `UtilityAI_Cache.au3:44-49` calls "
        "four fills; this layer has no per-frame cache and reads live instead, which the member states. "
        "It answers `None`, which is what the source's own `EndFunc` without a value answers.",
    ),
    "UAI_UpdatePlayerCache": (
        "uai_cache",
        "**NOT APPLICABLE**, as `UAI_UpdateAgentCache`: the player's cache rows are read live here.",
    ),
    "UAI_CacheDynamicSkillbarInfo": (
        "uai_dynamic_skill_cache",
        "**NOT APPLICABLE: it refills the per-slot dynamic table.** This layer answers those columns "
        "from the live slot record at the moment they are asked for, so the fill has nothing to do; the "
        "member says so and answers what the source's `EndFunc` would.",
    ),
    "UAI_GetDynamicSkillStruct": (
        "uai_dynamic_skill_cache",
        "**NOT APPLICABLE: it answers a `DllStruct` descriptor** GwAu3's injected reader uses to copy "
        "the cache. A DllStruct handle has no twin here and nothing in this layer needs one; the "
        "columns it would fill are answered by `UAI_GetDynamicSkillInfo`.",
    ),
}

#: The remaining plugin rows: GwAu3's per-frame cache machinery, which has no ported home here. Each
#: note opens with the tier word the generator reads, because that is how this file records a finding
#: with no member behind it.
_UAI_UNPORTED_PLUGIN_ROWS: dict[str, str] = {
    "UAI_BuildAgentIDMap": (
        "**NOT APPLICABLE: it builds GwAu3's own `$g_m_AgentIDToIndex` map** from its cache rows "
        "(`UtilityAI_AgentCache.au3`). The map is bookkeeping for `UAI_GetIndexByID`, which refuses for "
        "the same reason; a caller here holds an agent id."
    ),
    "UAI_CacheAgentInfo": (
        "**NOT APPLICABLE: a per-frame cache fill.** It reads the client's agent array into "
        "`$g_amx2_AgentCache`; this layer reads the same array when a column is asked for, so there is "
        "no row to fill and nothing to keep in step."
    ),
    "UAI_CacheAgentEffectsAndBonds": (
        "**NOT APPLICABLE: a per-frame cache fill**, of the agent effect and bond rows. The layer "
        "answers presence and the property columns from the client's own records "
        "(`py4gw/gwa3/uai_effects.py`), so the rows have no twin here."
    ),
    "UAI_CachePlayerInfo": (
        "**NOT APPLICABLE: a per-frame cache fill** of the controlled character's row; its columns are "
        "read live by `UAI_GetPlayerInfo`."
    ),
    "UAI_CachePlayerEffectsAndBonds": (
        "**NOT APPLICABLE: a per-frame cache fill**, as the agent form."
    ),
    "UAI_DecodeAgentInto": (
        "**NOT APPLICABLE: it decodes one agent record into a cache row** (the eighty-eight columns "
        "`UAI_GetAgentInfo` reads). This layer answers those columns from the record itself "
        "(`py4gw/gwa3/uai_agent.py`), so there is no row to decode into."
    ),
    "UAI_FillEffectRows": (
        "**NOT APPLICABLE: a cache fill** of the effect rows, from the client's own effect array. The "
        "layer reads that array directly."
    ),
    "UAI_FillBondRows": (
        "**NOT APPLICABLE: a cache fill** of the bond rows, over the client's buff list. "
        "`UAI_AgentUpkeepsBond` is the routed question."
    ),
    "UAI_CacheAgentVisibleEffects": (
        "**NOT APPLICABLE: a cache fill** of the visible-effect rows -- the cache "
        "`UAI_AgentHasVisibleEffect` used to read. The fill itself has no twin: this layer walks the "
        "agent's own list at the moment the question is asked, which that member's docstring records, "
        "and `UAI_GetVisibleEffectStruct` below is the descriptor the fill used."
    ),
    "UAI_CachePlayerVisibleEffects": (
        "**NOT APPLICABLE: a cache fill**, as the agent form."
    ),
    "UAI_FillVisEffectRows": (
        "**NOT APPLICABLE: a cache fill** of the visible-effect rows, from the client's own array."
    ),
    "UAI_GetAgentStruct": (
        "**NOT APPLICABLE: a `DllStruct` descriptor** used with `Memory_ReadArrayStruct` to copy the "
        "agent array into GwAu3's cache. A DllStruct has no twin here and nothing needs one: the same "
        "records are read through `py4gw/context/`'s structures."
    ),
    "UAI_GetBondStruct": (
        "**NOT APPLICABLE: a `DllStruct` descriptor**, as `UAI_GetAgentStruct`: the bond records are "
        "read through the port's own effect and buff structures."
    ),
    "UAI_GetEffectStruct": (
        "**NOT APPLICABLE: a `DllStruct` descriptor** whose fields (`Timestamp` at ``+0x14``, "
        "`Duration` at ``+0x10``) this layer reads as attributes of the port's own effect record -- "
        "which is what `UAI_GetAgentEffectInfo`'s ten columns are computed from."
    ),
    "UAI_GetAgentEffectStruct": (
        "**NOT APPLICABLE: a `DllStruct` descriptor**, as `UAI_GetEffectStruct`."
    ),
    "UAI_GetVisibleEffectStruct": (
        "**NOT APPLICABLE: a `DllStruct` descriptor** for the visible-effect array -- the structure "
        "`UAI_AgentHasVisibleEffect` would read through GwAu3's injected reader. A DllStruct has no twin "
        "here, and the read it describes is ported against the port's own record instead, so that "
        "member's fields (``unk``/``id``/``has_ended``) are the names the port answers from."
    ),
}

for _name, (_module, _note) in _UAI_LAYER_REFUSALS.items():
    ROUTES[_name] = Route(
        "",
        f"py4gw/gwa3/{_module}.py:{_layer_member_line(_module, _name)}",
        "",
        _note,
    )

for _name, (_module, _note) in _UAI_LAYER_NOT_APPLICABLE.items():
    ROUTES[_name] = Route(
        "",
        f"py4gw/gwa3/{_module}.py:{_layer_member_line(_module, _name)}",
        "",
        _note,
    )

for _name, _note in _UAI_UNPORTED_PLUGIN_ROWS.items():
    ROUTES[_name] = Route("", "", "", _note)


# The effect-data members (2026-10-10): ``GwAu3_Data_Effect.au3``'s single member, and the agent-side
# reader it needs, which is a ``GwAu3_Data_Agent.au3`` declaration of its own. Porting the pair is what
# un-refused three ``Anti_*`` predicates and -- through them -- the 805 strategy bodies that guard on
# those predicates.
ROUTES["Agent_GetAgentEffectInfo"] = Route(
    "the layer's own reader",
    "py4gw/gwa3/data_agent.py:821",
    "read",
    "Routed inside the layer (`tools/gwa3_snippets/data_agent_effect_info.py`): the source walks the "
    "agent's effect array in ``0x18`` strides for the record whose first dword is the skill id "
    "(`GwAu3_Data_Agent.au3:874-882`) and answers one field of it. This project reads the same array "
    "through `py4gw.effect.get_effects`, so each column is the field at the source's own offset -- the "
    "five `uai_effects.py` also reads, from the same record -- the two computed columns are the source's "
    "arithmetic, and the empty-column answer is the **record** rather than the client pointer the source "
    "answers.",
)

ROUTES["Effect_GetEffectArg"] = Route(
    "the layer's own reader",
    "py4gw/gwa3/data_effect.py:39",
    "read",
    "Routed inside the layer, and it is **the one `data_*` module written by hand**: the family "
    "generator builds a module per file whose accessor is a ``Switch`` over one record's offsets, while "
    "this member switches over three *strings* and each case composes two other ported readers. Its "
    "three cases are the source's -- ``Duration``, ``Scale`` and ``BonusScale`` -- over the skill "
    "table's own ends and the caster's effect attribute level, with ``Round`` and ``Floor`` kept apart "
    "as the source keeps them. **One divergence is the source's own**: this file divides the skill "
    "table's scale ends by ``65536`` where the plugin's ``UAI_GetAgentEffectInfo`` reads them raw "
    "(`Cache/UtilityAI_EffectsCache.au3:352-360`); both are ported as written and the live question is "
    "recorded in `docs/GWA3_COMPAT_SPEC.md`.",
)


# The attribute family (2026-10-10): ``GwAu3_Data_Attribute.au3``'s seven members, ported whole into a
# module of their own. Three read the client's attribute-constant table and three the party-attribute
# blocks, and this project already reads both -- with the source's own layouts asserted on the ported
# structures (``0x43C`` per block, ``0x14`` per record), so no offset in the file is a guess.
_ATTRIBUTE_NOTE = (
    "Routed inside the layer: `py4gw/gwa3/data_attribute.py`, written by hand because four of the "
    "file's members switch over *strings* with computed answers rather than over one record's offsets "
    "(the family generator's model). Three of them read the client's attribute-constant table through "
    "`py4gw/skillbar.py`'s ``get_attribute_constant_data``, whose `AttributeInfoStruct` names the five "
    "fields ``Attribute_GetAttributeInfo`` switches over at its own offsets; three read the party blocks "
    "through `py4gw/context/world_context.py`'s `PartyAttributeStruct` (an ``agent_id`` and 54 "
    "``0x14``-byte `AttributeStruct` records -- ``0x43C`` exactly, which is the stride GwAu3 multiplies "
    "by). The two point words are read at the source's own ``0x14 * 45 + 0xB0`` because the port's "
    "structure does not name them, and the two point *keys* are read **signed**, because the source reads "
    "them with ``long`` and compares ``> 0``. Porting the file is what un-refused the last strategy body "
    "that needed a data member."
)

for _name in (
    "Attribute_GetAttributeName",
    "Attribute_GetAttributePtr",
    "Attribute_GetAttributeInfo",
    "Attribute_GetPartyAttributeInfo",
    "Attribute_GetPartyAttributePointInfo",
    "Attribute_GetProfPrimaryAttribute",
):
    ROUTES[_name] = Route(
        "the layer's own reader",
        f"py4gw/gwa3/data_attribute.py:{_layer_member_line('data_attribute', _name)}",
        "read",
        _ATTRIBUTE_NOTE,
    )

ROUTES["Attribute_GetLastModified"] = Route(
    "",
    "py4gw/gwa3/data_attribute.py:%d" % _layer_member_line("data_attribute", "Attribute_GetLastModified"),
    "",
    "**NOT APPLICABLE: the state behind GwAu3's own attribute setter.** It answers "
    "``[$g_i_LastAttributeModified, $g_i_LastAttributeValue]`` -- two globals GwAu3 writes when *it* "
    "changes an attribute, which is a client write (a packet) this layer does not perform; the layer's "
    "own `cmd_attribute` module refuses the two setters it has for the same reason. There is no "
    "equivalent state here, and the pair's shape is kept so a caller reading it by index still works.",
)


# The two ranking dispatch tables (2026-10-10): a slot's skill id maps to a strategy *name*, which
# GwAu3's engine resolves with AutoIt's `Call`. Both tables are generated whole from the source, and the
# strategy functions the names point at are generated too (`tools/generate_gwa3_strategies.py`): 4,553
# of the 4,572 are transcribed and 19 refuse, each naming what stopped it.
for _name, _file, _line in (
    ("UAI_GetBestTargetFunc", "UtilityAI_BestTargetCache.au3", 3),
    ("UAI_GetCanUseFunc", "UtilityAI_CanUseCache.au3", 4),
):
    ROUTES[_name] = Route(
        "the layer's own function",
        "py4gw/gwa3/uai_best_target_cache.py:1",
        "read",
        f"Routed inside the layer: the generated table answers GwAu3's own strategy **name** for the "
        f"slot's skill id (`py4gw/gwa3/uai_static_skill_cache.py` reads the id), which is exactly what "
        f"the source's `Switch` answers. GwAu3 declares it at ``{_file}:{_line}``, and the functions the "
        f"names point at are generated from the same sources.",
    )

ROUTES["Party_GetHeroFlagInfo"] = Route(
    "the layer's own function",
    "py4gw/gwa3/data_party.py:420",
    "read",
    "**Routed for six of its seven keys.** `GwAu3_Data_Party.au3:368-402` walks the *world's* hero-flag "
    "array (`World_GetWorldInfo(\"HeroFlagArray\")`) at a ``0x24`` stride, matching the hero's agent id, "
    "and answers ``HeroID``/``AgentID``/``InventoryID``/``Behavior``/``FlagX``/``FlagY``. This layer "
    "reads the same elements -- `WorldContextStruct.hero_flags`, whose `HeroFlagStruct` is ``0x24`` -- "
    "and two of GwAu3's key names read the port's differently-named fields (``InventoryID`` is the word "
    "at ``+0x8``, which the port calls ``level``; ``Behavior`` is ``+0xC``, ``hero_behavior``). "
    "**``LockedTargetID`` refuses**: GwAu3 reads it at ``+0x20`` while this project's record names "
    "``+0x1C`` `locked_target_id` and leaves ``+0x20`` as ``h0020``, and which word the client writes is "
    "not established by reading either source. It is the owner's to settle, with the `Friend` family's "
    "offsets and the three model-state columns.",
)


def parse_declarations() -> list[DeclaredFunction]:
    """Every GwAu3 function the surface has to account for, with its file, line and signature.

    **The set is the union of two, and the second one is the correction.** The first is GwAu3's
    ``API/Modules/{Cmd,Data}`` declarations -- the 648 this map used to tier on its own. The second is
    every GwAu3 function the checkout actually **calls**, wherever it is declared.

    Only **322** of the 648 are called by anything, and GwAu3's own scripts call **667** functions, so
    a map built from the modules alone covered less than half of what a migration has to serve and
    reported the rest as if it did not exist: `Core_Initialize` and `Core_AutoStart` (every script's
    first two lines), `Log_*` (717 call sites), `UAI_*`, `Assembler_*`, `Scanner_*`. The denominator
    was wrong, and it was wrong in the direction that flatters the work.
    """

    declared: list[DeclaredFunction] = []
    seen: set[str] = set()
    for path in sorted(GWAU3_MODULES_DIR.rglob("*.au3")):
        kind = "Cmd" if path.parent.name == "Cmd" else "Data"
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            match = FUNC_DECLARATION.match(line)
            if match:
                seen.add(match.group("name"))
                declared.append(
                    DeclaredFunction(
                        name=match.group("name"),
                        file=path.name,
                        kind=kind,
                        line=number,
                        params=match.group("params").strip(),
                    )
                )

    # Everything else GwAu3 declares, read from its own `Func` lines across the whole API tree, added
    # when a script calls it. A declaration nothing calls is not a migration cost; a call with no
    # declaration is a script that will not compile.
    called = _called_surface()
    module_dir = GWAU3_MODULES_DIR
    for path in sorted(GWAU3_API_ROOT.rglob("*.au3")):
        if module_dir in path.parents:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for number, line in enumerate(text.splitlines(), 1):
            match = FUNC_DECLARATION.match(line)
            if not match:
                continue
            name = match.group("name")
            if name in seen or name not in called:
                continue
            seen.add(name)
            declared.append(
                DeclaredFunction(
                    name=name,
                    file=str(path.relative_to(GWAU3_API_ROOT)).replace("\\", "/"),
                    kind="Called",
                    line=number,
                    params=match.group("params").strip(),
                )
            )
    return declared


def load_call_census() -> dict[str, int]:
    """How often each function is called from GwAu3's own scripts, plugins and utilities.

    Read from the surface index, which is only used here as a *ranking* -- never as the surface of
    record. A function the index missed simply sorts as "not counted", which is why the column is
    labelled as a count from that file and not as a reachability claim.
    """

    if not CALL_CENSUS_PATH.is_file():
        return {}
    calls: dict[str, int] = {}
    for line in CALL_CENSUS_PATH.read_text(encoding="utf-8", errors="replace").splitlines()[1:]:
        parts = line.split(",")
        if len(parts) >= 3:
            calls.setdefault(parts[2].strip(), 0)
    return calls


def load_mechanisms() -> dict[str, str]:
    """Per-function mechanism: ``{name: MECHANISM}``.

    Read from ``external/GwAu3_mechanism_map.json`` when it exists, which is a JSON classification
    of every declared function produced by reading the sources -- a machine-readable artefact rather
    than prose, so it can be consumed without parsing a table. Falls back to the markdown
    inventories in ``docs/`` when it is absent.

    Either way the inventories are the evidence base and are cited in the output; this function only
    collects the classification.
    """

    json_path = REPO_ROOT / "external" / "GwAu3_mechanism_map.json"
    if json_path.is_file():
        parsed = json.loads(json_path.read_text(encoding="utf-8"))
        mechanisms: dict[str, str] = {}
        for entry in parsed.get("functions", []):
            name = entry.get("name")
            mechanism = entry.get("mechanism")
            if name and mechanism in MECHANISMS:
                mechanisms[name] = mechanism
        if mechanisms:
            return mechanisms

    mechanisms = {}
    for relative in INVENTORY_FILES:
        path = REPO_ROOT / relative
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.startswith("|"):
                continue
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) < 3:
                continue
            name_cell = cells[0]
            for mechanism in MECHANISMS:
                if mechanism in line and "GwAu3_" in line:
                    match = re.search(r"\b([A-Z][A-Za-z0-9_]*_[A-Za-z0-9_]+)\b", name_cell)
                    if match and re.search(r"(Cmd|Data)_", line):
                        mechanisms.setdefault(match.group(1), mechanism)
                    break
    return mechanisms


def tier_for(name: str, mechanism: str) -> tuple[str, str]:
    """The row's tier and its reason, from the recorded route if there is one."""

    route = ROUTES.get(name)
    if route is not None and route.member:
        return "ROUTED", route.note or f"Ã¢â€ â€™ {route.member}"
    if route is not None and route.note:
        # An explicit entry with no member: the note carries the finding, and the tier comes from
        # what the note says rather than from the mechanism, because a human already judged it.
        if route.note.startswith("**NOT APPLICABLE") or "**NOT APPLICABLE" in route.note:
            return "NOT APPLICABLE", route.note
        if route.note.startswith("**REFUSED") or "**REFUSED" in route.note:
            return "REFUSED", route.note
        return "NO ROUTE YET", route.note
    tier, reason = TIER_FOR_MECHANISM.get(mechanism, ("NO ROUTE YET", "unclassified"))
    return tier, reason


def render(declared: list[DeclaredFunction], mechanisms: dict[str, str], calls: dict[str, int]) -> str:
    rows_by_tier: dict[str, list[tuple[DeclaredFunction, str, str, Route | None]]] = {
        tier: [] for tier in ("ROUTED", "REFUSED", "NOT APPLICABLE", "NO ROUTE YET")
    }
    for function in declared:
        mechanism = mechanisms.get(function.name, "")
        tier, reason = tier_for(function.name, mechanism)
        rows_by_tier[tier].append((function, tier, reason, ROUTES.get(function.name)))

    routable = sum(1 for f, _, _, r in rows_by_tier["ROUTED"] if r and r.member)
    called = sorted(declared, key=lambda f: (-calls.get(f.name, 0), f.name))
    called_routed = [f for f in called if ROUTES.get(f.name) and ROUTES[f.name].member]

    lines: list[str] = []
    lines.append("# The GwAu3 route map\n")
    lines.append("**Generated** by `python tools/generate_gwa3_route_map.py` Ã¢â‚¬â€ do not edit by hand.")
    lines.append("Specification: [`GWA3_COMPAT_SPEC.md`](GWA3_COMPAT_SPEC.md).\n")
    lines.append(
        "Every function GwAu3 declares, its mechanism read from the inventories, and the Stealth member "
        "that does the same thing where one has been recorded. **A route may cite `py4gw/gwa3/` itself** Ã¢â‚¬â€ "
        "where the compatibility layer owns the implementation, its own reader is the member that does the "
        "work, and the row says so rather than pointing at a lower class.\n"
    )
    lines.append("## Where each column comes from\n")
    lines.append("| Column | Source |")
    lines.append("| --- | --- |")
    lines.append("| Function, parameters, file, line | `external/GwAu3/API/Modules/{Cmd,Data}/*.au3`, parsed on every run |")
    lines.append("| Mechanism | `docs/_inventory_gwau3_*.md`, produced by reading those sources line by line |")
    lines.append("| Call sites | `external/GwAu3_modules_surface.csv` Ã¢â‚¬â€ **a ranking only**, never the surface of record (see its `.md` note) |")
    lines.append("| Route | hand-written in `tools/generate_gwa3_route_map.py`, each citing the Stealth file and line it was read from Ã¢â‚¬â€ a ported class under `py4gw/`, or `py4gw/gwa3/` itself where the layer owns the implementation |")
    lines.append("")
    lines.append("## The four tiers\n")
    lines.append(
        "**This map tiers the union of two sets, and the second is the correction.** GwAu3's\n"
        "`API/Modules/{Cmd,Data}` declarations are the 648 this map was built from; the rest are the\n"
        "functions GwAu3's own scripts **call** from anywhere else -- `Core_Initialize`,\n"
        "`Core_AutoStart`, `Log_*`, `UAI_*`, `Assembler_*`, `Scanner_*` and their neighbours. Only 322\n"
        "of the 648 are called by anything, and the checkout calls 667 functions in all, so a map built\n"
        "from the modules alone answered a question about less than half of what a migration has to\n"
        "serve. Those added rows carry the mechanism `Ã¢â‚¬â€` (the inventories classify the `Cmd` and `Data`\n"
        "modules only) and every one of them is a work item until a route is recorded for it.\n"
    )
    lines.append("| Tier | Meaning | Count |")
    lines.append("| --- | --- | --- |")
    for tier in ("ROUTED", "REFUSED", "NOT APPLICABLE", "NO ROUTE YET"):
        lines.append(f"| **{tier}** | {TIER_MEANING[tier]} | {len(rows_by_tier[tier])} |")
    lines.append(f"| **total declared** | | **{len(declared)}** |")
    lines.append("")

    lines.append("## The surface a migration actually has to serve\n")
    lines.append(
        f"Ranked by call sites in GwAu3's own scripts, plugins and utilities. "
        f"**{len(called_routed)}** of the called functions have a recorded route; the rest are the work.\n"
    )
    lines.append("| Function | Calls | Mechanism | Tier | Route |")
    lines.append("| --- | --- | --- | --- | --- |")
    for function in called:
        count = calls.get(function.name, 0)
        if count == 0:
            continue
        mechanism = mechanisms.get(function.name, "Ã¢â‚¬â€")
        tier, _ = tier_for(function.name, mechanism)
        route = ROUTES.get(function.name)
        target = route.member if route and route.member else "Ã¢â‚¬â€"
        lines.append(f"| `{function.name}` | {count} | {mechanism} | {tier} | {target} |")
    lines.append("")

    lines.append("## Every declared function\n")
    for tier in ("ROUTED", "REFUSED", "NOT APPLICABLE", "NO ROUTE YET"):
        entries = rows_by_tier[tier]
        lines.append(f"### {tier} Ã¢â‚¬â€ {len(entries)}\n")
        if not entries:
            lines.append("_(none)_\n")
            continue
        lines.append("| GwAu3 function | Source | Mechanism | Route | Note |")
        lines.append("| --- | --- | --- | --- | --- |")
        for function, _, reason, route in sorted(entries, key=lambda item: item[0].name):
            source = f"`{function.file}:{function.line}`"
            mechanism = mechanisms.get(function.name, "Ã¢â‚¬â€")
            target = route.member if route and route.member else "Ã¢â‚¬â€"
            citation = f" ({route.citation})" if route and route.citation else ""
            note = ""
            if route and route.mechanism:
                citation = f" [{route.mechanism}]{citation}"
            if route and route.note:
                note = route.note
            elif not route or not route.member:
                note = reason
            lines.append(f"| `{function.name}` | {source} | {mechanism} | {target}{citation} | {note} |")
        lines.append("")

    lines.append("## What this map does not establish\n")
    lines.append(
        "- **A recorded route is a correspondence read from both sources, not a live result.** Each row\n"
        "  names the Stealth member and its line; that the two produce the same effect *in the client* is\n"
        "  confirmed only when the row is exercised. Rows flagged *Needs verification* say so in the note.\n"
        "- **`NO ROUTE YET` is not a verdict that no route exists.** It means none has been read yet, and\n"
        "  the note names what is missing. That is the work item, not a resting place.\n"
        "- **`REFUSED` is about the mechanism, not the wish.** A row is refused when GwAu3's own\n"
        "  implementation is a forged packet or host input synthesis and no safe route has been found to\n"
        "  the same effect. Where a native twin exists, the twin is routed and the packet spelling refuses.\n"
        "- **Mechanism coverage is partial.** The inventories cover the GwAu3 modules named in their own\n"
        "  scope; a function showing `Ã¢â‚¬â€` for its mechanism has not been classified in them yet, and its tier\n"
        "  falls back to `NO ROUTE YET` rather than to a guess.\n"
    )
    return "\n".join(lines) + "\n"


TIER_MEANING = {
    "ROUTED": "Stealth has a recorded route to the same effect; the row names it",
    "NO ROUTE YET": "the effect is real and GwAu3 reaches it, but no Stealth route is recorded Ã¢â‚¬â€ the note is the work item",
    "REFUSED": "GwAu3's implementation is a forged packet or host input synthesis and no safe route to the same effect is recorded",
    "NOT APPLICABLE": "the function manipulates GwAu3's own controller-side state and has no client counterpart to route",
}


def main() -> int:
    declared = parse_declarations()
    mechanisms = load_mechanisms()
    calls = load_call_census()
    OUTPUT_PATH.write_text(render(declared, mechanisms, calls), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} -- {len(declared)} declared functions.")
    print(f"  mechanisms classified from the inventories: {sum(1 for f in declared if f.name in mechanisms)}")
    print(f"  routes recorded by hand: {sum(1 for f in declared if ROUTES.get(f.name) and ROUTES[f.name].member)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
