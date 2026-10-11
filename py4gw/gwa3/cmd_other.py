"""GwAu3's ``Other_*`` helpers: the three sleeps and the ping wait.

Part of the GwAu3-compatible layer (``docs/GWA3_COMPAT_SPEC.md``). GwAu3's names, arguments, defaults
and return shapes are reproduced; the engine underneath is this project's own.

**These touch no client state at all.** ``Other_RndSleep`` and ``Other_TolSleep`` are AutoIt's own
``Sleep(Random(...))``, ``Other_PingSleep`` adds the client's ping, and ``Other_WaitPingStabilized``
polls until that ping settles. Nothing here forges a packet or calls a function: the sleeps are host
time and the ping is a client read, so two of the four are routed exactly and the other two are refused
for want of the read they need.

**Sleeping is not a no-op, and the layer does not shorten it.** A GwAu3 script's timing *is* its
behaviour -- `Punch_Out_Farm`'s waits between actions are what stop it from outpacing the client -- so
the ported sleeps take the same time the source takes, with the source's own arithmetic.
"""

from __future__ import annotations

import random
import time
from typing import Any

__all__ = [
    "Other_PingSleep",
    "Other_RndSleep",
    "Other_TolSleep",
    "Other_WaitPingStabilized",
]


def Other_RndSleep(amount: Any, random_fraction: Any = 0.05) -> None:
    """Sleep a random amount around the given one (``GwAu3_Cmd_Other.au3:4-7``).

    GwAu3's own arithmetic is kept line for line: the spread is ``$a_i_Amount * $a_f_Random`` and the
    sleep is ``Random($a_i_Amount - $spread, $a_i_Amount + $spread)`` milliseconds. AutoIt's ``Random``
    returns a float in that range; ``Sleep`` truncates it, which is what the integer conversion here
    reproduces.
    """

    spread = float(amount) * float(random_fraction)
    time.sleep(int(random.uniform(float(amount) - spread, float(amount) + spread)) / 1000.0)


def Other_TolSleep(amount: Any = 150, tolerance: Any = 50) -> None:
    """Sleep the given time plus or minus a tolerance (``GwAu3_Cmd_Other.au3:10-12``).

    ``Sleep(Random($a_i_Amount - $a_i_Tolerance, $a_i_Amount + $a_i_Tolerance))`` -- the same call with
    the tolerance given directly rather than as a fraction.
    """

    time.sleep(
        int(random.uniform(float(amount) - float(tolerance), float(amount) + float(tolerance))) / 1000.0
    )


def Other_PingSleep(ms_extra: Any = 0) -> None:
    """**REFUSED: the ping has no resolver.** GwAu3 sleeps for ``Other_GetPing() + $a_i_MsExtra``.

    ``GwAu3_Cmd_Other.au3:15-17`` reads its own ``Ping`` global, which ``Core_Initialize`` filled from
    its ``Ping`` byte pattern (``GwAu3_Core.au3:62``, ``:161``). This project has no resolver for that
    address -- ``offsets/`` carries no entry and ``offsets/gwau3_leads.json`` holds only
    ``current_target_anchor`` -- so the number to sleep for cannot be produced. **Sleeping the wrong
    amount is the failure this refusal avoids**: a PingSleep that slept only ``$a_i_MsExtra`` would
    return far sooner than the source does, and the caller would drive the client faster than GwAu3
    ever did.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Other.au3:15-17 sleeps `Other_GetPing() + $a_i_MsExtra`, and `Other_GetPing` reads "
        "GwAu3's own `Ping` global (`GwAu3_Core.au3:62` resolves it by byte pattern, `:161` reads it). "
        "This project has no resolver for that address -- `offsets/` carries no entry for it, and the "
        "pattern would be read through `py4gw/scanner.py` like every other one -- so the duration "
        "cannot be computed. A sleep of just `$a_i_MsExtra` would return early and let a script outpace "
        "the client, which is exactly what the ping term exists to prevent."
    )


def Other_WaitPingStabilized(wait_timer: Any = 2000) -> None:
    """**REFUSED: it polls the ping, which has no resolver.** As ``Other_PingSleep``, one level up.

    ``GwAu3_Cmd_Other.au3:20-52`` loops until ``Other_GetPing() <> 0`` holds for ``$a_i_WaiTimer``
    milliseconds without an interruption, and its loop also calls `Cinematic_SkipCinematic` and reads
    `Map_GetInstanceInfo("IsLoading")` and `Game_GetGameInfo("IsCinematic")`. Three of those four
    readings are themselves unrouted in this layer -- the ping, and the instance and game-info
    readers -- so the loop cannot be reproduced: a version that skipped the ping test would return
    immediately, and one that guessed a ping would return at the wrong moment. The load-wait it exists
    to perform has a ported equivalent a caller can use today, and it is named rather than substituted:
    ``Map_WaitMapLoading`` and `Map.IsMapReady`.
    """

    raise NotImplementedError(
        "GwAu3_Cmd_Other.au3:20-52 loops until `Other_GetPing() <> 0` has held for `$a_i_WaiTimer` ms, "
        "and inside that loop it also reads `Map_GetInstanceInfo(\"IsLoading\")` and "
        "`Game_GetGameInfo(\"IsCinematic\")` and calls `Cinematic_SkipCinematic`. The ping has no "
        "resolver in this project (`offsets/gwau3_leads.json` holds only `current_target_anchor`, and a "
        "resolver would be read through `py4gw/scanner.py`) and neither do the instance and game-info "
        "readers, so the loop's exit condition cannot be evaluated. Returning early would let a script "
        "act while the map is still loading. The ported equivalent of the *wait* is "
        "`py4gw/map.py`'s `Map_WaitMapLoading`, and this refuses rather than quietly substituting it."
    )
