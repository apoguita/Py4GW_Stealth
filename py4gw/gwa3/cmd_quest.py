"""GwAu3's ``Quest_*`` actions, over this project's own routes.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

Two of the four are routed, two refuse, and the difference is the mechanism GwAu3 chose:

* ``Quest_AbandonQuest`` forges ``HEADER_QUEST_ABANDON``, whose effect the client's own
  `Quest.AbandonQuest` performs.
* ``Quest_RequestInfos`` forges ``HEADER_QUEST_REQUEST_INFOS`` -- the client filling in the log entry
  for a quest -- which is `Quest.RequestQuestInfo`.
* ``Quest_AcceptQuest`` and ``Quest_QuestReward`` forge ``HEADER_DIALOG_SEND`` with a packed option
  (``'0x008' & Hex($a_i_QuestID, 3) & '01'`` and ``... & '07'``). That is the dialog mechanism, and
  this project has no member that **sends** a dialog selection -- the same refusal, and the same named
  work, as `Game_Dialog` in `cmd_game`.
"""

from __future__ import annotations

from typing import Any

from ..quest import Quest

__all__ = [
    "Quest_AbandonQuest",
    "Quest_AcceptQuest",
    "Quest_QuestReward",
    "Quest_RequestInfos",
]

#: The dialog option codes GwAu3 packs after the quest id (``GwAu3_Cmd_Quest.au3:5``, ``:10``):
#: ``01`` accepts the quest out of an NPC's dialog and ``07`` takes its reward. Kept as the source's
#: own hex so the two functions are visibly the same packet with a different last byte.
_DIALOG_OPTION_ACCEPT = "01"
_DIALOG_OPTION_REWARD = "07"


def Quest_AbandonQuest(quest_id: Any) -> bool:
    """Abandon a quest (``GwAu3_Cmd_Quest.au3:14-16``).

    GwAu3 forges ``HEADER_QUEST_ABANDON`` with the quest id; the ported member is the client's own
    abandon. The argument means the same thing in both.
    """

    Quest.AbandonQuest(int(quest_id))
    return True


def Quest_RequestInfos(quest_id: Any) -> None:
    """Ask the client for a quest's description and objectives (``GwAu3_Cmd_Quest.au3:19-21``).

    **GwAu3's body has no ``Return``**, so it answers AutoIt's valueless default; the same is true
    here, and the ported member answers nothing either. GwAu3's packet asks the client to fill the log
    entry in; ``Quest.RequestQuestInfo`` is that request, with the same ``update_marker`` default
    GwAu3 leaves alone (``False``).
    """

    Quest.RequestQuestInfo(int(quest_id), False)


def Quest_AcceptQuest(quest_id: Any) -> bool:
    """**REFUSED: ``HEADER_DIALOG_SEND`` has no route.** This project sends no dialog selection.

    ``GwAu3_Cmd_Quest.au3:5`` packs ``'0x008' & Hex($a_i_QuestID, 3) & '01'`` and forges a dialog-send:
    accepting a quest is a *dialog option*, reached through the NPC's dialog rather than through a
    quest action. This project reads dialogs (`py4gw/dialog.py`) and sends none, so the packet's effect
    has no route -- and the route's absence is already recorded for `Game_Dialog`, which forges the same
    header. An action that guessed at a different mechanism would accept a quest the caller did not
    select.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Quest.au3:5 forges `HEADER_DIALOG_SEND` with `'0x008' & Hex($a_i_QuestID, 3) & "
        f"'{_DIALOG_OPTION_ACCEPT}'` -- accepting a quest is a dialog option, not a quest action. "
        "This project sends no dialog selection (`py4gw/dialog.py` reads the active dialog, its "
        "buttons and its content id, and sends nothing), so the packet's effect has no route. The same "
        "refusal is recorded on `Game_Dialog`, and the same lead applies: "
        "`DIALOG_SEND_AGENT_MESSAGE` is the client's own message."
    )


def Quest_QuestReward(quest_id: Any) -> bool:
    """**REFUSED: ``HEADER_DIALOG_SEND`` has no route.** As ``Quest_AcceptQuest``.

    ``GwAu3_Cmd_Quest.au3:10`` is the same packet with the reward option ``07`` instead of ``01`` --
    one byte apart, and both are dialog selections.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Quest.au3:10 forges `HEADER_DIALOG_SEND` with `'0x008' & Hex($a_i_QuestID, 3) & "
        f"'{_DIALOG_OPTION_REWARD}'` -- the quest-reward dialog option. Refused for the same reason as "
        "`Quest_AcceptQuest`: this project's `py4gw/dialog.py` reads the active dialog, its buttons and "
        "its content id, and sends no selection, so the packet's effect has no route. The two options "
        "are one byte apart, so a route that answers one must answer the other."
    )
