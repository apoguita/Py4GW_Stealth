"""Dispatch what the payload recorded to the handlers registered for it.

Reforged's callbacks run *inside* the client: they are called as the event happens,
they see the arguments, and they can modify or block what the client was about to
do. These cannot. They are given a record the payload wrote after the fact, so they
observe and nothing more — which is the honest difference between a runtime inside
the game and a controller outside it.

There are two ways to be told, and they are the same registry underneath:

* :meth:`Callbacks.pump` reads the block once and dispatches what it finds. That is
  a drain, not a callback: a script is told nothing until it asks.
* :class:`EventListener` runs a thread that reads the block and dispatches records
  **as they arrive**, which is what a callback is supposed to be. A handler runs on
  that thread, so it must not block for long — the thread is also what drains the
  client's event region, and a slow handler means dropped events — and it must be
  written to run alongside whatever the main thread is doing.

Reading the block happens in one place either way, because the event counter has
exactly one consumer. The command side has its own counter and its own writer, which
is why a listener and a publisher never need a lock between them.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Protocol

from .shared_block import EventKind, EventRecord

#: What a handler is given: one event, exactly as the payload recorded it.
EventHandler = Callable[[EventRecord], None]

#: How long the listener waits before reading again when the client is quiet.
DEFAULT_INTERVAL_MS = 2.0

#: How long stopping waits for the listener's current read to finish.
DEFAULT_STOP_TIMEOUT_MS = 2000


class EventSource(Protocol):
    """The one thing this needs from a bridge: what the payload has recorded."""

    def events(self) -> list[EventRecord]: ...


class Callbacks:
    """Handlers keyed by the kind of event they asked for."""

    def __init__(self, source: EventSource) -> None:
        """Create a registry over one source of events."""

        self._source = source
        self._handlers: dict[int, list[EventHandler]] = {}

    def register(self, kind: EventKind | int, handler: EventHandler) -> None:
        """Add a handler for one kind of event.

        Handlers for a kind run in the order they were registered. Registering the
        same handler twice makes it run twice, which is what a registry is.
        """

        self._handlers.setdefault(int(kind), []).append(handler)

    def unregister(self, kind: EventKind | int, handler: EventHandler) -> None:
        """Remove one handler, or refuse because it was never registered."""

        handlers = self._handlers.get(int(kind))
        if not handlers or handler not in handlers:
            raise ValueError(
                f"no handler is registered for event kind {int(kind)}"
            )
        handlers.remove(handler)
        if not handlers:
            del self._handlers[int(kind)]

    def kinds(self) -> tuple[int, ...]:
        """Return the event kinds that currently have handlers."""

        return tuple(sorted(self._handlers))

    def pump(self) -> int:
        """Read what the payload recorded, dispatch it, and say how much ran.

        The count is handler calls, not events: one event with two handlers for
        its kind counts twice.
        """

        return self.handle(self._source.events())

    def handle(self, records: list[EventRecord]) -> int:
        """Dispatch records already in hand, and say how many handler calls ran.

        A handler that raises is not caught. It is the caller's own code, and a
        swallowed exception would hide the only signal that it is broken.
        """

        dispatched = 0
        for record in records:
            # A copy: a handler is allowed to register or unregister while it
            # runs, and the batch in hand should not change under it.
            for handler in tuple(self._handlers.get(int(record.kind), ())):
                handler(record)
                dispatched += 1
        return dispatched


class EventListener:
    """A thread that reads the block and runs handlers as events arrive.

    This is the difference between a drain and a callback. :meth:`Callbacks.pump`
    tells a script what happened when it asks; this tells it when it happens.

    Two costs come with that, and neither can be designed away:

    * **handlers run on this thread.** They run alongside whatever the caller's
      main thread is doing, so a handler that touches the caller's own state has to
      be written for that.
    * **a slow handler costs events.** This thread is also what empties the client's
      event region, and the payload drops an event when the region is full rather
      than making the game wait. A handler that blocks for a frame's worth of time
      will lose notices under load.

    The thread is a daemon, so a forgotten listener cannot keep a process alive, but
    it should still be stopped: :meth:`stop` joins it, and a handler that raised is
    re-raised there, on the caller's thread, rather than dying silently in a thread.
    """

    def __init__(
        self,
        source: EventSource,
        registry: Callbacks,
        interval_ms: float = DEFAULT_INTERVAL_MS,
    ) -> None:
        """Create a listener over one source and one registry."""

        if interval_ms <= 0:
            raise ValueError("interval_ms must be positive.")

        self._source = source
        self._registry = registry
        self._interval = interval_ms / 1000.0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._failure: BaseException | None = None
        self._delivered = 0

    @property
    def running(self) -> bool:
        """Return whether the listener is reading."""

        return self._thread is not None

    @property
    def delivered(self) -> int:
        """Return how many handler calls have run so far."""

        return self._delivered

    def start(self) -> None:
        """Start reading. Refuses to start twice."""

        if self._thread is not None:
            raise RuntimeError("the listener is already running.")

        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="py4gw-events", daemon=True
        )
        self._thread.start()

    def stop(self, timeout_ms: int = DEFAULT_STOP_TIMEOUT_MS) -> None:
        """Stop reading and wait for the thread, then re-raise any handler failure.

        The failure is re-raised even when the thread has already ended, which is
        what a handler that raised will have caused: it is reported here, on the
        caller's thread, instead of dying inside a thread nobody is watching.
        """

        thread, self._thread = self._thread, None
        if thread is not None:
            self._stop.set()
            thread.join(timeout_ms / 1000.0)
            if thread.is_alive():
                raise TimeoutError(
                    f"the event listener did not stop within {timeout_ms} ms."
                )
        self._raise_failure()

    def __enter__(self) -> EventListener:
        """Start the listener for a context-manager scope."""

        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        """Stop the listener when leaving a context-manager scope."""

        self.stop()

    def _run(self) -> None:
        """Read the source until stopped, dispatching everything found."""

        try:
            while not self._stop.is_set():
                records = self._source.events()
                if records:
                    # Keep draining while there is anything to drain, so a burst
                    # is emptied at the client's pace rather than the interval's.
                    self._delivered += self._registry.handle(records)
                    continue
                self._stop.wait(self._interval)
        except BaseException as error:  # noqa: BLE001 - kept for the caller's thread
            self._failure = error
            self._thread = None

    def _raise_failure(self) -> None:
        """Re-raise the failure a handler caused, on the caller's thread."""

        failure, self._failure = self._failure, None
        if failure is not None:
            raise failure
