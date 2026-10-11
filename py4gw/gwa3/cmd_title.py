"""GwAu3's ``Title_*`` actions, over this project's own routes.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

One function, and GwAu3's own body has **two** packets in it: ``$a_i_Title = 0`` forges
``HEADER_TITLE_HIDE`` and anything else forges ``HEADER_TITLE_DISPLAY`` with the id. This project has a
member for each half -- `Player.RemoveActiveTitle` and `Player.SetActiveTitle` -- so the branch is the
source's, and which half runs is decided by the same test.
"""

from __future__ import annotations

from typing import Any

from ..player import Player

__all__ = ["Title_SetDisplayedTitle"]

#: GwAu3's own sentinel: title ``0`` means "hide the title" rather than "display title zero"
#: (``GwAu3_Cmd_Title.au3``).
_NO_TITLE = 0


def Title_SetDisplayedTitle(title: Any = 0) -> bool:
    """Display a title, or hide it (``GwAu3_Cmd_Title.au3``).

    GwAu3 forges ``HEADER_TITLE_DISPLAY`` with the id, and ``HEADER_TITLE_HIDE`` when the id is
    ``0``. The ported members are the client's own display and hide, chosen by GwAu3's own test.
    """

    if int(title) == _NO_TITLE:
        Player.RemoveActiveTitle()
    else:
        Player.SetActiveTitle(int(title))
    return True
