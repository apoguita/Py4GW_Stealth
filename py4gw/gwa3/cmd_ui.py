"""GwAu3's ``Ui_*`` actions: the second implementation of the same actions, and none of it is routable.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

**Every one of the forty refuses, and the module is still worth having, because it says what to call
instead.** ``GwAu3_Cmd_Ui.au3`` is GwAu3's *other* spelling of actions the ``Cmd_*`` modules already
have -- ``Ui_CommandHero`` beside ``Party_CommandHero``, ``Ui_SetDifficulty`` beside ``Game_SwitchMode``,
``Ui_EnterChallenge`` beside ``Map_EnterChallenge``. The differences are real and recorded:

* **The mechanism is different.** Every ``Ui_*`` function fills one of GwAu3's structs and calls
  ``Core_Enqueue``, its injected assembler stub, which writes the record into the client's own command
  queue at ``256 * $g_i_QueueCounter + $g_p_QueueBase`` with ``WriteProcessMemory``
  (``GwAu3_Core.au3:559-566``). The ``Cmd_*`` twin usually forges a packet instead. This project does
  neither, so both spellings refuse -- but the twin is where a route is *recorded*, and each refusal
  here names it.
* **The order can differ.** ``Ui_LeaveGroup`` leaves the group and then kicks the heroes;
  ``Party_LeaveGroup`` kicks and then leaves. A migration that swaps one for the other changes who is
  still in the party when it dissolves, so the two are not interchangeable even once both work.
* **Six do not touch the client at all.** The rendering functions write ``$g_b_DisableRendering``,
  which is a slot in GwAu3's own injected block -- controller-side state this project has no
  equivalent for. They are **NOT APPLICABLE** rather than refused: there is no client behaviour
  missing, because there was never any client behaviour in them.
"""

from __future__ import annotations

from typing import Any, NoReturn

__all__ = [
    "Ui_AboutQuest",
    "Ui_AcceptQuest",
    "Ui_ActivateDhuumsCovenant",
    "Ui_ActivateReforgedMode",
    "Ui_ActiveQuest",
    "Ui_AddHero",
    "Ui_AddNPC",
    "Ui_CancelAll",
    "Ui_CancelHero",
    "Ui_CloseDialog",
    "Ui_CommandAll",
    "Ui_CommandHero",
    "Ui_DeactivateDhuumsCovenant",
    "Ui_DeactivateReforgedMode",
    "Ui_DisableHeroSkill",
    "Ui_DisableRendering",
    "Ui_Dialog",
    "Ui_DropHeroBundle",
    "Ui_EnableHeroSkill",
    "Ui_EnableRendering",
    "Ui_EnterChallenge",
    "Ui_EquipItem",
    "Ui_Interact",
    "Ui_KickAllHeroes",
    "Ui_KickHero",
    "Ui_KickNPC",
    "Ui_LeaveGroup",
    "Ui_LockHeroTarget",
    "Ui_MoveMap",
    "Ui_OpenChest",
    "Ui_PurgeHook",
    "Ui_PurgeHook_",
    "Ui_RewardQuest",
    "Ui_SetDifficulty",
    "Ui_SetHeroBehavior",
    "Ui_ToggleHeroSkillState",
    "Ui_ToggleRendering",
    "Ui_ToggleRendering_",
    "Ui_UpdateQuest",
    "Ui_Xunlai",
]

#: The rule every queue-writing ``Ui_*`` function refuses by, with the line its body is on filled in per
#: function. Written once because it is one mechanism, not forty.
_QUEUE_RULE = (
    "GwAu3_Cmd_Ui.au3:{line} fills one of GwAu3's structs and calls `Core_Enqueue`, its injected "
    "assembler stub, which writes the record into the client's own command queue with "
    "`WriteProcessMemory` (`GwAu3_Core.au3:559-566`). This project writes into no such queue."
)

#: The other rule: GwAu3's own injected-block flag, which has no client counterpart at all.
_BLOCK_RULE = (
    "GwAu3_Cmd_Ui.au3:{line} writes `$g_b_DisableRendering`, a slot in **GwAu3's own injected code "
    "block** rather than a client field. Nothing here holds such a flag and there is no client state "
    "to route: the behaviour lives entirely in GwAu3's injected runtime. `docs/GWA3_ROUTE_MAP.md` "
    "records these rows as NOT APPLICABLE."
)


def _refuse(
    name: str,
    line: int,
    *,
    twin: str | None = None,
    rule: str = _QUEUE_RULE,
    extra: str | None = None,
) -> NoReturn:
    """Refuse one function, citing its body and -- where one exists -- the routed spelling.

    The twin is the useful half: a migrating script that calls ``Ui_CommandHero`` has a working
    ``Party_CommandHero`` it can call today, and the refusal says so instead of leaving the caller to
    find it. ``extra`` carries a warning that changes what a swap *means* -- a different argument
    order, a different default, a different sequence -- because those are the places where a migration
    that looks mechanical is not.
    """

    message = rule.format(line=line)
    if twin is not None:
        message += (
            f" The same action is spelled `{twin}` in GwAu3 and that spelling is the one this layer "
            f"routes; see its entry in `py4gw/gwa3/` for what it does today."
        )
    if extra is not None:
        message += " " + extra
    raise NotImplementedError(message)


def Ui_Dialog(dialog_id: Any) -> None:
    """**REFUSED: the injected queue.** GwAu3's dialog send; see `Game_Dialog` for the same packet."""

    _refuse("Ui_Dialog", 6, twin="Game_Dialog")


def Ui_AcceptQuest(quest_id: Any) -> None:
    """**REFUSED: the injected queue.** As `Quest_AcceptQuest`, a dialog option."""

    _refuse("Ui_AcceptQuest", 12, twin="Quest_AcceptQuest")


def Ui_UpdateQuest(quest_id: Any) -> None:
    """**REFUSED: the injected queue.** A dialog option (``... & '04'``) with no ported counterpart."""

    _refuse("Ui_UpdateQuest", 18)


def Ui_AboutQuest(quest_id: Any) -> None:
    """**REFUSED: the injected queue.** A dialog option (``... & '03'``) with no ported counterpart."""

    _refuse("Ui_AboutQuest", 24)


def Ui_RewardQuest(quest_id: Any) -> None:
    """**REFUSED: the injected queue.** As `Quest_QuestReward`, a dialog option."""

    _refuse("Ui_RewardQuest", 30, twin="Quest_QuestReward")


def Ui_Interact(interaction_id: Any) -> None:
    """**REFUSED: the injected queue.** GwAu3 sends a bare *interaction id*.

    Note the mismatch a route would have to settle: GwAu3's ``Ui_Interact`` takes an id that is **not**
    an agent id -- its callers pass ``1``, ``2``, ``4``, ``5`` for shrine modes -- while this project's
    `Player.Interact` takes an agent and performs a world action. The two are the same *word* and not
    the same *thing*, so `Agent_GoNPC`'s route is not this function's route.
    """

    _refuse("Ui_Interact", 36)


def Ui_OpenChest(with_lockpick: Any = True) -> None:
    """**REFUSED: the injected queue.** GwAu3 sends ``2`` with a lockpick and ``1`` without."""

    _refuse("Ui_OpenChest", 40, twin="Item_OpenChest")


def Ui_ActivateReforgedMode() -> None:
    """**REFUSED: the injected queue**, through `Ui_Interact(1)`."""

    _refuse("Ui_ActivateReforgedMode", 51, twin="Ui_Interact")


def Ui_DeactivateReforgedMode() -> None:
    """**REFUSED: the injected queue**, through `Ui_Interact(2)`."""

    _refuse("Ui_DeactivateReforgedMode", 56, twin="Ui_Interact")


def Ui_ActivateDhuumsCovenant() -> None:
    """**REFUSED: the injected queue**, through `Ui_Interact(4)`."""

    _refuse("Ui_ActivateDhuumsCovenant", 61, twin="Ui_Interact")


def Ui_DeactivateDhuumsCovenant() -> None:
    """**REFUSED: the injected queue**, through `Ui_Interact(5)`."""

    _refuse("Ui_DeactivateDhuumsCovenant", 66, twin="Ui_Interact")


def Ui_Xunlai() -> None:
    """**REFUSED: the injected queue** -- but this project *does* have the route.

    ``Inventory.OpenXunlaiWindow`` is the client's own way to open the Xunlai chest, which is exactly
    what GwAu3's ``$GC_I_UIMSG_OPEN_XUNLAI`` message asks the client to do. It is not called here
    because this function's own mechanism is the queue and the layer does not silently swap mechanisms
    -- but the twin is named, and it is the shortest gap in this module.
    """

    _refuse("Ui_Xunlai", 72)


def Ui_CloseDialog(dialog_id: Any) -> None:
    """**REFUSED: the injected queue.** GwAu3 maps a floating-dialog index to a close message."""

    _refuse("Ui_CloseDialog", 89)


def Ui_CommandHero(hero_number: Any, x: Any, y: Any) -> None:
    """**REFUSED: the injected queue** -- and **`Party_CommandHero` is routed.** Use that name."""

    _refuse("Ui_CommandHero", 99, twin="Party_CommandHero")


def Ui_CancelHero(hero_number: Any) -> None:
    """**REFUSED: the injected queue** -- and **`Party_CancelHero` is routed.** Use that name."""

    _refuse("Ui_CancelHero", 108, twin="Party_CancelHero")


def Ui_CommandAll(x: Any, y: Any) -> None:
    """**REFUSED: the injected queue** -- and **`Party_CommandAll` is routed.** Use that name."""

    _refuse("Ui_CommandAll", 117, twin="Party_CommandAll")


def Ui_CancelAll() -> None:
    """**REFUSED: the injected queue** -- and **`Party_CancelAll` is routed.** Use that name."""

    _refuse("Ui_CancelAll", 124, twin="Party_CancelAll")


def Ui_SetHeroBehavior(hero_number: Any, behavior: Any = 1) -> None:
    """**REFUSED: the injected queue** -- and **`Party_SetHeroAggression` is routed.**

    Note the default differs: ``Ui_SetHeroBehavior`` defaults to ``1`` (Guard) while
    ``Party_SetHeroAggression`` has no default at all, so a swap changes what a one-argument call does.
    """

    _refuse(
        "Ui_SetHeroBehavior",
        131,
        twin="Party_SetHeroAggression",
        extra=(
            "**And the default differs**: `Ui_SetHeroBehavior` defaults to `1` (Guard) while "
            "`Party_SetHeroAggression` has no default, so a one-argument call changes meaning."
        ),
    )


def Ui_DropHeroBundle(hero_number: Any) -> None:
    """**REFUSED: the injected queue.** No ported counterpart is recorded."""

    _refuse("Ui_DropHeroBundle", 137)


def Ui_LockHeroTarget(hero_number: Any, target_agent_id: Any = 0) -> None:
    """**REFUSED: the injected queue** -- and `Party_LockHeroTarget` refuses too, for want of a member."""

    _refuse("Ui_LockHeroTarget", 144, twin="Party_LockHeroTarget")


def Ui_ToggleHeroSkillState(hero_number: Any, skill_slot: Any) -> None:
    """**REFUSED: the injected queue** -- and `Party_ToggleHeroSkillState` refuses for want of the read."""

    _refuse("Ui_ToggleHeroSkillState", 151, twin="Party_ToggleHeroSkillState")


def Ui_EnableHeroSkill(hero_number: Any, skill_slot: Any) -> None:
    """**REFUSED: the injected queue** -- and **`Party_EnableHeroSkill` is routed.** Use that name."""

    _refuse("Ui_EnableHeroSkill", 156, twin="Party_EnableHeroSkill")


def Ui_DisableHeroSkill(hero_number: Any, skill_slot: Any) -> None:
    """**REFUSED: the injected queue** -- and **`Party_DisableHeroSkill` is routed.** Use that name."""

    _refuse("Ui_DisableHeroSkill", 161, twin="Party_DisableHeroSkill")


def Ui_AddNPC(agent_id: Any) -> None:
    """**REFUSED: the injected queue** -- and **`Party_AddNpc` is routed.** Use that name."""

    _refuse("Ui_AddNPC", 168, twin="Party_AddNpc")


def Ui_AddHero(hero_id: Any) -> None:
    """**REFUSED: the injected queue** -- and **`Party_AddHero` is routed.** Use that name."""

    _refuse("Ui_AddHero", 174, twin="Party_AddHero")


def Ui_KickNPC(agent_id: Any) -> None:
    """**REFUSED: the injected queue** -- and **`Party_KickNpc` is routed.** Use that name."""

    _refuse("Ui_KickNPC", 180, twin="Party_KickNpc")


def Ui_KickHero(hero_id: Any) -> None:
    """**REFUSED: the injected queue** -- and **`Party_KickHero` is routed.** Use that name."""

    _refuse("Ui_KickHero", 186, twin="Party_KickHero")


def Ui_KickAllHeroes() -> None:
    """**REFUSED: the injected queue** -- and **`Party_KickAllHeroes` is routed.** Use that name."""

    _refuse("Ui_KickAllHeroes", 192, twin="Party_KickAllHeroes")


def Ui_LeaveGroup(kick_all_heroes: Any = True) -> None:
    """**REFUSED: the injected queue** -- and **`Party_LeaveGroup` is routed**, in the *other* order.

    This is the one pair whose order is genuinely different, and it is not a detail: GwAu3 leaves the
    group first (``:198``) and kicks the heroes after (``:199``), while ``Party_LeaveGroup`` kicks
    first and leaves after. A migration that swaps the names changes who is still in the party when it
    dissolves. The route map records it on both rows.
    """

    _refuse(
        "Ui_LeaveGroup",
        198,
        twin="Party_LeaveGroup",
        extra=(
            "**And the order is the opposite.** `Ui_LeaveGroup` leaves the group first (`:198`) and "
            "kicks the heroes after (`:199`); `Party_LeaveGroup` kicks first and leaves after. A "
            "migration that swaps the names changes who is still in the party when it dissolves."
        ),
    )


def Ui_SetDifficulty(hard_mode: Any = False) -> None:
    """**REFUSED: the injected queue** -- and **`Game_SwitchMode` is routed.** Use that name."""

    _refuse("Ui_SetDifficulty", 205, twin="Game_SwitchMode")


def Ui_EnterChallenge(foreign: Any = False, wait_map_is_loaded: Any = True) -> None:
    """**REFUSED: the injected queue** -- and **`Map_EnterChallenge` is routed.** Use that name.

    GwAu3's argument is inverted against its own meaning: it sends ``Not $a_b_Foreign``
    (``:210``), so the wire value is "native character". A migration must keep that straight.
    """

    _refuse(
        "Ui_EnterChallenge",
        212,
        twin="Map_EnterChallenge",
        extra=(
            "**And GwAu3's argument is inverted against its own meaning**: it sends "
            "`Not $a_b_Foreign` (`:210`), so the wire value is \"native character\"."
        ),
    )


def Ui_MoveMap(map_id: Any, region: Any, language: Any, district: Any) -> None:
    """**REFUSED: the injected queue** -- and **`Map_MoveMap` is routed**, with different arguments.

    ``GwAu3_Cmd_Ui.au3:217`` declares ``($a_i_MapID, $a_i_Region, $a_i_Language, $a_i_District)`` while
    ``GwAu3_Cmd_Map.au3:36`` declares ``($a_i_MapID, $a_i_Region, $a_i_District, $a_i_Language)`` --
    **the last two are swapped between the two spellings**, which the route map records on both rows.
    """

    _refuse(
        "Ui_MoveMap",
        223,
        twin="Map_MoveMap",
        extra=(
            "**The last two arguments are swapped between the two spellings**: `Ui_MoveMap` is "
            "($a_i_MapID, $a_i_Region, $a_i_Language, $a_i_District) and `Map_MoveMap` is "
            "($a_i_MapID, $a_i_Region, $a_i_District, $a_i_Language). A migration that renames the call "
            "without reordering the arguments sends a district where a language belongs."
        ),
    )


def Ui_EquipItem(item: Any, agent: Any = None) -> None:
    """**REFUSED: the injected queue.** The ported `Inventory.EquipItem(item_id, agent_id)` exists."""

    _refuse("Ui_EquipItem", 231, twin="Item_EquipItem")


def Ui_EnableRendering() -> None:
    """**NOT APPLICABLE: GwAu3's own injected-block flag.** See `_BLOCK_RULE`."""

    _refuse("Ui_EnableRendering", 237, rule=_BLOCK_RULE)


def Ui_DisableRendering() -> None:
    """**NOT APPLICABLE: GwAu3's own injected-block flag.** See `_BLOCK_RULE`."""

    _refuse("Ui_DisableRendering", 243, rule=_BLOCK_RULE)


def Ui_ToggleRendering() -> None:
    """**NOT APPLICABLE to the client, with a host-side tail that is also not a route.**

    ``GwAu3_Cmd_Ui.au3:247-256`` toggles its own block flag and then calls ``WinSetState`` on the
    game's window handle and ``Memory_Clear`` (``SetProcessWorkingSetSize``) on the client's. The
    window calls are host-side Win32 rather than game actions -- this layer has no member for them and
    does not need one -- and the flag has no ported counterpart.
    """

    _refuse("Ui_ToggleRendering", 253, rule=_BLOCK_RULE)


def Ui_PurgeHook(time_ms: Any = 10000) -> None:
    """**NOT APPLICABLE: it toggles GwAu3's own render flag twice with a sleep between.**"""

    _refuse("Ui_PurgeHook", 262, rule=_BLOCK_RULE)


def Ui_ToggleRendering_() -> None:
    """**NOT APPLICABLE: the same as `Ui_ToggleRendering` without the window calls.**"""

    _refuse("Ui_ToggleRendering_", 273, rule=_BLOCK_RULE)


def Ui_PurgeHook_(time_ms: Any = 10000) -> None:
    """**NOT APPLICABLE: the same as `Ui_PurgeHook` without the window calls.**"""

    _refuse("Ui_PurgeHook_", 281, rule=_BLOCK_RULE)


def Ui_ActiveQuest(quest_id: Any) -> None:
    """**REFUSED: the injected queue** -- and this project *does* have the route.

    `Quest.SetActiveQuest` is the client's own setter for the active quest, which is what GwAu3's
    record asks for. Named rather than called, for the same reason as `Ui_Xunlai`.
    """

    _refuse("Ui_ActiveQuest", 287)
