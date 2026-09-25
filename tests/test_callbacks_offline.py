"""Offline tests for the callback registry.

No client and no block: the source of events is a list this test controls, so what
is tested is the part that decides *which* handler runs for which record, and in
what order.
"""

from __future__ import annotations

import time
import unittest

from py4gw.game_thread.callbacks import Callbacks, EventListener
from py4gw.game_thread.shared_block import EventKind, EventRecord


class FakeSource:
    """An event source the test fills by hand."""

    def __init__(self, records: list[EventRecord] | None = None) -> None:
        self.records: list[EventRecord] = list(records or ())
        self.reads = 0

    def events(self) -> list[EventRecord]:
        self.reads += 1
        records, self.records = self.records, []
        return records


class RegistryTests(unittest.TestCase):
    """What runs, when, and in what order."""

    def setUp(self) -> None:
        self.source = FakeSource()
        self.callbacks = Callbacks(self.source)
        self.seen: list[EventRecord] = []

    def record(self, kind: EventKind, sequence: int = 0) -> EventRecord:
        return EventRecord(kind=int(kind), sequence=sequence)

    def test_a_handler_runs_for_its_own_kind_only(self) -> None:
        self.callbacks.register(EventKind.UI_MESSAGE, self.seen.append)

        dispatched = self.callbacks.handle(
            [
                self.record(EventKind.UI_MESSAGE, 1),
                self.record(EventKind.COMMAND_COMPLETE, 2),
                self.record(EventKind.UI_MESSAGE, 3),
            ]
        )

        self.assertEqual(dispatched, 2)
        self.assertEqual([record.sequence for record in self.seen], [1, 3])

    def test_handlers_run_in_the_order_they_were_registered(self) -> None:
        order: list[str] = []
        self.callbacks.register(EventKind.UI_MESSAGE, lambda _: order.append("first"))
        self.callbacks.register(EventKind.UI_MESSAGE, lambda _: order.append("second"))

        self.callbacks.handle([self.record(EventKind.UI_MESSAGE)])

        self.assertEqual(order, ["first", "second"])

    def test_the_same_handler_registered_twice_runs_twice(self) -> None:
        self.callbacks.register(EventKind.UI_MESSAGE, self.seen.append)
        self.callbacks.register(EventKind.UI_MESSAGE, self.seen.append)

        dispatched = self.callbacks.handle([self.record(EventKind.UI_MESSAGE)])

        self.assertEqual(dispatched, 2)

    def test_unregistering_stops_delivery(self) -> None:
        self.callbacks.register(EventKind.UI_MESSAGE, self.seen.append)
        self.callbacks.unregister(EventKind.UI_MESSAGE, self.seen.append)

        dispatched = self.callbacks.handle([self.record(EventKind.UI_MESSAGE)])

        self.assertEqual(dispatched, 0)
        self.assertEqual(self.callbacks.kinds(), ())

    def test_unregistering_something_never_registered_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            self.callbacks.unregister(EventKind.UI_MESSAGE, self.seen.append)

    def test_an_event_nobody_asked_for_is_ignored(self) -> None:
        dispatched = self.callbacks.handle([self.record(EventKind.UI_MESSAGE)])

        self.assertEqual(dispatched, 0)

    def test_two_kinds_do_not_interfere(self) -> None:
        messages: list[int] = []
        completions: list[int] = []
        self.callbacks.register(EventKind.UI_MESSAGE, lambda r: messages.append(r.sequence))
        self.callbacks.register(
            EventKind.COMMAND_COMPLETE, lambda r: completions.append(r.sequence)
        )

        self.callbacks.handle(
            [
                self.record(EventKind.COMMAND_COMPLETE, 7),
                self.record(EventKind.UI_MESSAGE, 9),
            ]
        )

        self.assertEqual(messages, [9])
        self.assertEqual(completions, [7])

    def test_a_handler_that_raises_is_not_swallowed(self) -> None:
        def broken(_: EventRecord) -> None:
            raise RuntimeError("handler failure")

        self.callbacks.register(EventKind.UI_MESSAGE, broken)

        with self.assertRaises(RuntimeError):
            self.callbacks.handle([self.record(EventKind.UI_MESSAGE)])

    def test_a_handler_may_register_while_it_runs(self) -> None:
        """The batch in hand must not change under the handler that is running."""

        late: list[int] = []

        def registering(record: EventRecord) -> None:
            self.seen.append(record)
            self.callbacks.register(EventKind.UI_MESSAGE, lambda r: late.append(r.sequence))

        self.callbacks.register(EventKind.UI_MESSAGE, registering)

        dispatched = self.callbacks.handle(
            [self.record(EventKind.UI_MESSAGE, 1), self.record(EventKind.UI_MESSAGE, 2)]
        )

        # The new handler starts working on the next record, not on the one that
        # registered it. Two records, the original handler twice, the new one once.
        self.assertEqual(len(self.seen), 2)
        self.assertEqual(late, [2])
        self.assertEqual(dispatched, 3)

    def test_pump_reads_the_source_and_dispatches_it(self) -> None:
        self.callbacks.register(EventKind.UI_MESSAGE, self.seen.append)
        self.source.records = [self.record(EventKind.UI_MESSAGE, 4)]

        dispatched = self.callbacks.pump()

        self.assertEqual(dispatched, 1)
        self.assertEqual([record.sequence for record in self.seen], [4])
        self.assertEqual(self.source.reads, 1)

    def test_pumping_with_nothing_recorded_runs_nothing(self) -> None:
        self.callbacks.register(EventKind.UI_MESSAGE, self.seen.append)

        self.assertEqual(self.callbacks.pump(), 0)
        self.assertEqual(self.seen, [])

    def test_kinds_reports_what_has_handlers(self) -> None:
        self.callbacks.register(EventKind.UI_MESSAGE, self.seen.append)

        self.assertEqual(self.callbacks.kinds(), (int(EventKind.UI_MESSAGE),))


class ListeningSource:
    """An event source another thread can feed while the listener reads it."""

    def __init__(self) -> None:
        self.records: list[EventRecord] = []
        self.reads = 0

    def events(self) -> list[EventRecord]:
        self.reads += 1
        records, self.records = self.records, []
        return records

    def push(self, record: EventRecord) -> None:
        self.records.append(record)


def wait_until(predicate, timeout: float = 2.0) -> bool:
    """Wait for a condition, so the tests never depend on a fixed sleep."""

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.001)
    return predicate()


class ListenerTests(unittest.TestCase):
    """The thread that makes delivery a callback rather than a drain."""

    def setUp(self) -> None:
        self.source = ListeningSource()
        self.callbacks = Callbacks(self.source)
        self.seen: list[EventRecord] = []

    def listener(self, interval_ms: float = 1.0) -> EventListener:
        listener = EventListener(self.source, self.callbacks, interval_ms)
        self.addCleanup(listener.stop)
        return listener

    def record(self, sequence: int = 0) -> EventRecord:
        return EventRecord(kind=int(EventKind.UI_MESSAGE), sequence=sequence)

    def test_a_handler_runs_without_anyone_pumping(self) -> None:
        self.callbacks.register(EventKind.UI_MESSAGE, self.seen.append)
        listener = self.listener()

        listener.start()
        self.source.push(self.record(7))

        self.assertTrue(wait_until(lambda: self.seen), "the handler never ran")
        self.assertEqual(self.seen[0].sequence, 7)

    def test_it_drains_a_burst(self) -> None:
        self.callbacks.register(EventKind.UI_MESSAGE, self.seen.append)
        listener = self.listener()

        listener.start()
        for sequence in range(10):
            self.source.push(self.record(sequence))

        self.assertTrue(wait_until(lambda: len(self.seen) >= 10))
        self.assertEqual([record.sequence for record in self.seen], list(range(10)))

    def test_it_keeps_listening_after_a_batch(self) -> None:
        self.callbacks.register(EventKind.UI_MESSAGE, self.seen.append)
        listener = self.listener()

        listener.start()
        self.source.push(self.record(1))
        self.assertTrue(wait_until(lambda: len(self.seen) == 1))
        self.source.push(self.record(2))

        self.assertTrue(wait_until(lambda: len(self.seen) == 2))

    def test_stopping_ends_delivery(self) -> None:
        self.callbacks.register(EventKind.UI_MESSAGE, self.seen.append)
        listener = self.listener()

        listener.start()
        self.source.push(self.record(1))
        self.assertTrue(wait_until(lambda: len(self.seen) == 1))

        listener.stop()
        self.source.push(self.record(2))
        time.sleep(0.05)

        self.assertEqual(len(self.seen), 1)
        self.assertFalse(listener.running)

    def test_starting_twice_is_refused(self) -> None:
        listener = self.listener()

        listener.start()
        with self.assertRaises(RuntimeError):
            listener.start()

    def test_stopping_what_never_started_is_a_no_op(self) -> None:
        self.listener().stop()

    def test_a_handler_that_raises_stops_the_listener_and_is_re_raised(self) -> None:
        def broken(_: EventRecord) -> None:
            raise RuntimeError("handler failure")

        self.callbacks.register(EventKind.UI_MESSAGE, broken)
        listener = self.listener()
        listener.start()
        self.source.push(self.record(1))

        self.assertTrue(wait_until(lambda: not listener.running))
        with self.assertRaises(RuntimeError):
            listener.stop()

    def test_delivered_counts_handler_calls(self) -> None:
        self.callbacks.register(EventKind.UI_MESSAGE, self.seen.append)
        self.callbacks.register(EventKind.UI_MESSAGE, self.seen.append)
        listener = self.listener()

        listener.start()
        self.source.push(self.record(1))

        self.assertTrue(wait_until(lambda: listener.delivered == 2))

    def test_the_context_manager_starts_and_stops_it(self) -> None:
        self.callbacks.register(EventKind.UI_MESSAGE, self.seen.append)

        with self.listener() as listener:
            self.assertTrue(listener.running)
            self.source.push(self.record(3))
            self.assertTrue(wait_until(lambda: self.seen))

        self.assertFalse(listener.running)

    def test_a_non_positive_interval_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            EventListener(self.source, self.callbacks, 0)


if __name__ == "__main__":
    unittest.main()
