"""Port of Native's ``PY4GW::Timer`` (``base/timer.h``).

A small stopwatch the sources use for throttles and waits. It is ported whole because a member of a
ported class holds one: ``MerchantListener`` keeps a ``Timer`` and asks it whether a second has
elapsed (``listeners.h:91``, ``listeners.cpp:70``), and a port of that member has to be the source's
own arithmetic rather than a different clock wearing its name.

**The clock is ``std::clock()``, which is processor time and not wall time.** That is the source's
own choice (``timer.h:15``), and it is visible in what the timer answers: a listener that resets it
while the client is busy reaches its second sooner than one reading a wall clock would. Python's
``time.process_time()`` is the same measurement — the CPU time this process has consumed — so it is
what this port reads, and the arithmetic below is the source's, which converts its ticks with
``CLOCKS_PER_SEC`` and asks for milliseconds.
"""

from __future__ import annotations

import time

#: ``CLOCKS_PER_SEC`` in the source's own units. Python's clock counts **seconds**, so the conversion
#: the source performs — ``(now - start) / CLOCKS_PER_SEC * 1000`` — is a multiplication by 1000 here,
#: and it is written as that rather than folded into a constant so the two stay comparable line for
#: line.
CLOCKS_PER_SEC = 1


def _clock() -> float:
    """Return the source's ``std::clock()``: the processor time this process has used."""

    return time.process_time()


class Timer:
    """The source's stopwatch: start, stop, pause, resume, and what it says about itself."""

    def __init__(self) -> None:
        self._start_time = 0.0
        self._paused_time = 0.0
        self._running = False
        self._paused = False

    def start(self) -> None:
        """``Timer::start`` (``timer.h:13-20``): start it, and do nothing if it already runs."""

        if not self._running:
            self._start_time = _clock()
            self._running = True
            self._paused = False
            self._paused_time = 0.0

    def stop(self) -> None:
        """``Timer::stop`` (``timer.h:22-25``)."""

        self._running = False
        self._paused = False

    def Pause(self) -> None:
        """``Timer::Pause`` (``timer.h:27-32``)."""

        if self._running and not self._paused:
            self._paused_time = _clock() - self._start_time
            self._paused = True

    def Resume(self) -> None:
        """``Timer::Resume`` (``timer.h:34-39``)."""

        if self._running and self._paused:
            self._start_time = _clock() - self._paused_time
            self._paused = False

    def isStopped(self) -> bool:
        """``Timer::isStopped`` (``timer.h:41-43``)."""

        return not self._running

    def isRunning(self) -> bool:
        """``Timer::isRunning`` (``timer.h:45-47``): running *and* not paused."""

        return self._running and not self._paused

    def IsPaused(self) -> bool:
        """``Timer::IsPaused`` (``timer.h:49-51``)."""

        return self._paused

    def HasValidData(self) -> bool:
        """``Timer::HasValidData`` (``timer.h:53-55``)."""

        return self._start_time > 0

    def reset(self) -> None:
        """``Timer::reset`` (``timer.h:57-62``): start it again from now, running and unpaused."""

        self._start_time = _clock()
        self._running = True
        self._paused = False
        self._paused_time = 0.0

    def getElapsedTime(self) -> float:
        """``Timer::getElapsedTime`` (``timer.h:64-72``), in milliseconds.

        A stopped timer has no elapsed time at all — the source answers ``0.0`` rather than the time
        since it was started — and a paused one answers the time it had reached when it was paused.
        """

        if not self._running:
            return 0.0
        if self._paused:
            return (self._paused_time / CLOCKS_PER_SEC) * 1000.0
        return ((_clock() - self._start_time) / CLOCKS_PER_SEC) * 1000.0

    def hasElapsed(self, milliseconds: float) -> bool:
        """``Timer::hasElapsed`` (``timer.h:74-79``): false for a stopped or paused timer."""

        if not self._running or self._paused:
            return False
        return self.getElapsedTime() >= milliseconds


__all__ = ["CLOCKS_PER_SEC", "Timer"]
