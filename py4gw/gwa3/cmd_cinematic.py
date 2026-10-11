"""GwAu3's ``Cinematic_*`` actions.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

Both functions **refuse**, and for two different reasons. ``Cinematic_SkipCinematic`` forges
``HEADER_CINEMATIC_SKIP`` and this project has no member that skips a cutscene.
``Cinematic_WaitCinematic`` is the more interesting one: GwAu3's body does not read the client at all
-- it is a loop over its own ``$a_i_SkipAttempts`` that presses the dialog **Confirm** button with
``ControlSend`` and checks whether the cinematic is still running with ``Game_GetGameInfo
("IsCinematic")``. The keystroke is input synthesis, which this project refuses by name, and the
cinematic check has no resolver either.
"""

from __future__ import annotations

from typing import Any

__all__ = ["Cinematic_SkipCinematic", "Cinematic_WaitCinematic"]


def Cinematic_SkipCinematic() -> bool:
    """**REFUSED: ``HEADER_CINEMATIC_SKIP`` has no route.** This project has no skip member.

    ``GwAu3_Cmd_Cinematic.au3`` forges ``HEADER_CINEMATIC_SKIP`` -- a four-byte packet with only its
    header. Nothing in ``py4gw/`` skips a cutscene: the cinematic state is not resolved anywhere, so
    neither the action nor a check of whether it worked can be produced. The work is a resolver for the
    cinematic state plus the client's own skip route, and it is recorded rather than approximated.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Cinematic.au3: `Cinematic_SkipCinematic()` forges `HEADER_CINEMATIC_SKIP`. This "
        "project has no member that skips a cutscene and no resolver for the cinematic state -- "
        "`py4gw/map.py` reads the instance and the map, `py4gw/dialog.py` reads the active dialog, and "
        "neither holds a cinematic flag -- so the effect has no route. "
        "`Game_GetGameInfo(\"IsCinematic\")`, the read GwAu3's own `Cinematic_WaitCinematic` uses to "
        "tell whether it needs to skip at all, is unrouted for the same reason."
    )


def Cinematic_WaitCinematic(
    timeout: Any = 15000,
    skip_attempts: Any = 5,
    cutscene_on_map: Any = False,
    cutscene_count: Any = 1,
) -> bool:
    """**REFUSED: its body is keystroke synthesis, which this project does not do.**

    ``GwAu3_Cmd_Cinematic.au3`` loops up to ``$a_i_SkipAttempts`` times, and each pass calls
    `Cinematic_SkipCinematic` and then sends ``ControlSend($l_h_GWWindow, "", "", "{ENTER}")`` to press
    the dialog's Confirm button. **Synthesising keystrokes into another process's window is the
    input-synthesis mechanism this project refuses by name** -- it is not a packet and not a client
    call, and a route that sent it would be doing what the layering exists to avoid. The loop's exit
    test, ``Game_GetGameInfo("IsCinematic")``, is unrouted as well.

    Unlike most refusals here, there is a *ported* path for a caller who wants the same effect: the
    client's own dialog messages are `DIALOG_BUTTON_MESSAGE` and `DIALOG_SEND_AGENT_MESSAGE`
    (``py4gw/dialog.py``), which is how this project clicks a dialog button. Wiring the confirm through
    those is the work.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Cinematic.au3: `Cinematic_WaitCinematic($a_i_Timeout = 15000, $a_i_SkipAttempts = 5, "
        "$a_b_CutsceneOnMap = False, $a_i_CutsceneCount = 1)` loops calling `Cinematic_SkipCinematic` "
        "and `ControlSend($l_h_GWWindow, \"\", \"\", \"{ENTER}\")` -- keystroke synthesis into the "
        "client's window, the mechanism this project refuses by name -- and tests "
        "`Game_GetGameInfo(\"IsCinematic\")`, which has no resolver here. The ported equivalent of the "
        "*button press* is the client's own dialog message (`DIALOG_BUTTON_MESSAGE`, "
        "`py4gw/dialog.py`), and wiring the confirm through it is the work."
    )
