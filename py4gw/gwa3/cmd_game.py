"""GwAu3's ``Game_*`` actions, over this project's own routes.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

Three functions, three different answers, and each is recorded rather than generalised:

* ``Game_SwitchMode`` is **routed**: GwAu3's ``HEADER_PARTY_SET_DIFFICULTY`` packet and this project's
  `Party.SetHardMode`/`SetNormalMode` are the same request.
* ``Game_DonateFaction`` is **routed**: GwAu3 sends ``HEADER_FACTION_DEPOSIT`` with a leading ``0`` and
  a trailing ``5000``, and `Player.DepositFaction` is the client's own deposit of the same five
  thousand points.
* ``Game_Dialog`` is **refused**: GwAu3 forges ``HEADER_DIALOG_SEND`` with a packed dialog id. This
  project *reads* dialogs in full -- ``py4gw/dialog.py`` has the body, the buttons and the journals --
  but has no member that **sends** a dialog selection, so the packet's effect has no route. The lead is
  already in the port: ``DIALOG_SEND_AGENT_MESSAGE`` and ``DIALOG_BUTTON_MESSAGE``
  (``py4gw/dialog.py``) are the client's own messages, and the work is the member that sends one.
"""

from __future__ import annotations

from typing import Any

from ..player import Player
from ..party import Party

__all__ = [
    "Game_Dialog",
    "Game_DonateFaction",
    "Game_SwitchMode",
]

#: GwAu3's own literals for the deposit (``GwAu3_Cmd_Game.au3``: a leading ``0`` and ``5000`` points).
_DEPOSIT_LEADING = 0
_DEPOSIT_POINTS = 5000

#: GwAu3's mode values, from its own callers: ``0`` is normal, anything else is hard mode.
_HARD_MODE_FIRST = 1


def Game_SwitchMode(mode: Any) -> bool:
    """Switch the party between normal and hard mode (``GwAu3_Cmd_Game.au3``).

    GwAu3 sends ``HEADER_PARTY_SET_DIFFICULTY`` with the mode; this calls the client's own setter for
    the same mode. GwAu3's value is a plain number, so the test is the same one its callers make:
    ``0`` is normal mode and anything else is hard.
    """

    if int(mode) >= _HARD_MODE_FIRST:
        Party.SetHardMode()
    else:
        Party.SetNormalMode()
    return True


def Game_DonateFaction(faction: Any) -> bool:
    """Deposit faction (``GwAu3_Cmd_Game.au3``).

    **GwAu3's own argument test is kept, lowercase and all.** Its body is
    ``If StringLeft($a_s_Faction, 1) = 'k'`` -- a single **lowercase** ``k`` decides Kurzick, and
    everything else is Luxon. AutoIt compares strings case-sensitively here, so ``"Kurzick"`` takes
    the *Luxon* branch in GwAu3 as written, and a caller who has been getting that behaviour keeps it.
    The deposit itself is the client's own (`Player.DepositFaction`), with GwAu3's own five thousand
    points.
    """

    faction_id = 0 if str(faction)[:1] == "k" else 1
    Player.DepositFaction(faction_id)
    return True


def Game_Dialog(dialog_id: Any) -> bool:
    """**REFUSED: GwAu3 forges ``HEADER_DIALOG_SEND``, and this project has no member that sends one.**

    ``GwAu3_Cmd_Game.au3`` packs the id (``'0x008' & Hex($a_v_DialogID, 3)`` in its callers) and forges
    a dialog-send packet. This project reads dialogs thoroughly -- `py4gw/dialog.py` holds the active
    dialog, its buttons, its content id and its callback journals -- but every one of those members
    **reads**. Nothing sends a selection, so there is no route to the packet's effect, and answering
    `True` would report a click the client never saw.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Game.au3: `Game_Dialog($a_v_DialogID)` forges `HEADER_DIALOG_SEND`. This project "
        "reads dialogs (`py4gw/dialog.py`: `get_active_dialog`, `get_active_dialog_buttons`, "
        "`read_dialog_content_id`) and sends none -- there is no member that selects a dialog option. "
        "The lead is in the port already: `DIALOG_SEND_AGENT_MESSAGE` and `DIALOG_BUTTON_MESSAGE` "
        "(`py4gw/dialog.py`) are the client's own messages, and the work is the member that sends one."
    )
