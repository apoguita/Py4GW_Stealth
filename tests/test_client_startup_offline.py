"""Offline test for the order the connection starts its capability layer in.

The dialog module's ``Initialize`` clears its state and takes its map gate from the live
map (``dialog.cpp:1819-1845``). In this project that read reaches the client through the
current-client registry every reader resolves through, so the connection has to be
*current* before that startup runs — not after it. Native needs no such step: its runtime
is in-process, and ``Initialize`` reads the map directly.

Measured live on 2026-09-25 with the publish left to :func:`py4gw.connect`: ``Initialize``
found no client, took the gate as suspended on an observed map of ``0 / False``, and the
first dialog the client announced — a body and both of its buttons inside 1.5 ms — was
refused whole, which left both journals empty while the dialog itself was open in the
client. ``tests/test_live_dat.py`` is the end-to-end test of that path.

No client is involved. The object is built with ``object.__new__`` and the write layer is
faked, because ``ConnectedClient.__init__`` opens handles and asserts elevation; what is
under test is the order of the calls the install makes, not the process behind them.

What this does not prove: that the client's map reads answer anything, or that a
connection can be installed against a real client. It proves the order — which is what the
live failure was — and that a startup that fails does not leave the connection published.
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from typing import Any, cast
from unittest import mock

from py4gw import chat
from py4gw import client as client_module
from py4gw import dialog
from py4gw.client import ConnectedClient, current_client
from py4gw.game_thread.shared_block import CallForm, EventKind


class StartupOrderTests(unittest.TestCase):
    """When a connection becomes the client every reader resolves through."""

    def setUp(self) -> None:
        # The connection is process-wide state, so a test that publishes a stand-in puts
        # back whatever was current before it ran.
        self.addCleanup(
            setattr, client_module, "_current_client", client_module._current_client
        )

    @staticmethod
    def bare_connection() -> ConnectedClient:
        """Return a connection with no process behind it, ready for the install.

        The three steps that touch the client are replaced by stand-ins: resolving the two
        targets, counting the suspended threads, and checking the entry bytes before a
        write. Everything between them — the order this test is about — is the real code.
        """

        client = object.__new__(ConnectedClient)
        client._pid = 4321
        client._module_base = 0x400000
        client._module_size = 0x1000
        client._access = None
        client._bridge = None
        client._callbacks = None
        client._listener = None
        client._suspended_threads = 0
        client._listener = mock.MagicMock()
        client._resolve = lambda name: 0x401000  # type: ignore[method-assign]
        client._count_suspended_threads = lambda access: 0  # type: ignore[method-assign]
        client._prepare_target = lambda access, name, address, expected: None  # type: ignore[method-assign]
        return client

    def install(
        self, client: ConnectedClient, initialize: object
    ) -> mock.MagicMock:
        """Run the real install with the write layer and the dialog startup replaced.

        Returns the stand-in the install used for the listener, so a caller can see what
        the connection started.
        """

        listener = mock.MagicMock()
        with (
            mock.patch("py4gw.client.WriteAccess"),
            mock.patch("py4gw.client.Bridge"),
            mock.patch("py4gw.client.EventListener", listener),
            mock.patch.object(dialog.PyDialog, "initialize", initialize),
        ):
            client._install_game_thread()
        return listener

    def test_the_connection_is_current_before_the_dialog_module_starts(self) -> None:
        """``Initialize`` reads the live map, and that read needs a current connection."""

        client = self.bare_connection()
        seen: list[object] = []

        def record_startup() -> bool:
            seen.append(current_client())
            return True

        self.install(client, record_startup)

        self.assertEqual(
            seen,
            [client],
            "the dialog module's Initialize ran without the connection being current, so "
            "its map read reached no client",
        )

    def test_the_capture_is_registered_on_the_started_listener(self) -> None:
        """The order of the registrations is the source's: the captures, then the listener.

        The dialog module's capture is registered before the connection's own target capture, then
        the chat module's log-line capture joins them — native registers its own chat-log callback
        in the same step (``chat.cpp:205``) — and the listener, which is what delivers what they
        registered for, starts after all of them.
        """

        client = self.bare_connection()
        listener = self.install(client, lambda: True)

        assert client._callbacks is not None
        self.assertEqual(
            client._callbacks._handlers[int(EventKind.UI_MESSAGE)],
            [dialog._capture_message, client._capture_target, chat._on_chat_log_line],
        )
        self.assertEqual(
            client._callbacks._handlers[int(EventKind.STRING_DECODED)],
            [dialog._on_string_decoded, chat._on_string_decoded],
        )
        listener.return_value.start.assert_called_once_with()

    def test_a_connection_that_cannot_start_does_not_stay_current(self) -> None:
        """A refused startup is not a connection anything may read through."""

        client = self.bare_connection()

        def refuse() -> bool:
            raise RuntimeError("the dialog module could not start")

        with self.assertRaises(RuntimeError):
            self.install(client, refuse)

        self.assertIsNone(current_client())


    def test_the_dialog_module_is_shut_down_before_the_listener_stops(self) -> None:
        """``Shutdown`` runs while the callbacks that finish its decodes can still arrive.

        The dialog module's drain waits for decodes the client is still running, and the listener
        is what delivers their completions. Stopping the listener first would leave the drain
        waiting for something that can no longer arrive — so the connection calls
        ``PyDialog.terminate`` first, which is also the source's own order: native's shutdown
        drains *before* its callbacks are unregistered.
        """

        client = self.bare_connection()
        client._reader = mock.MagicMock()
        client._call_slots = {}
        client._target_id = 0
        listener_running: list[bool] = []

        def record_terminate() -> None:
            listener_running.append(client._listener is not None)

        with mock.patch.object(dialog.PyDialog, "terminate", record_terminate):
            client.close()

        self.assertEqual(
            listener_running,
            [True],
            "the dialog module was shut down with the listener already stopped",
        )
        assert client._listener is None


class CallTargetSectionTests(unittest.TestCase):
    """A call target must be code, and the host is where that is checked.

    The dispatcher refuses a target outside the client's module, which does not cover an address
    inside the module but outside its code section. On 2026-09-25 the chat sender's resolver
    answered with such an address, the module bound passed it, and the client died executing data
    (``eip=462fd617``). These tests pin the refusal.
    """

    TEXT_START = 0x00401000
    TEXT_END = 0x00800000
    DATA = 0x00B5CF08

    def connection(self) -> ConnectedClient:
        client = object.__new__(ConnectedClient)
        client._pid = 4321
        client._call_slots = {}
        client._bridge = mock.MagicMock()
        client._access = mock.MagicMock()
        scanner = mock.MagicMock()
        scanner.get_section_range.return_value = SimpleNamespace(
            start=self.TEXT_START, end=self.TEXT_END
        )
        client._scanner = scanner
        return client

    def test_a_target_in_the_code_section_is_written(self) -> None:
        client = self.connection()
        access = cast(Any, client._access)

        slot = client._descriptor_slot(("a name", 1), self.TEXT_START + 0x40, CallForm.U32)

        self.assertEqual(slot, 0)
        access.write.assert_called_once()

    def test_a_target_in_the_data_section_is_refused(self) -> None:
        """The address is inside the module, so the dispatcher's own bound would allow it."""

        client = self.connection()
        access = cast(Any, client._access)

        with self.assertRaises(RuntimeError) as caught:
            client._descriptor_slot(("a name", 1), self.DATA, CallForm.U32)

        message = str(caught.exception)
        self.assertIn(f"0x{self.DATA:08X}", message)
        self.assertIn("not inside the client's code section", message)
        self.assertEqual(access.write.call_count, 0, "nothing was written")

    def test_a_target_outside_the_module_is_refused_too(self) -> None:
        client = self.connection()

        with self.assertRaises(RuntimeError):
            client._descriptor_slot(("a name", 1), 0x462FD617, CallForm.U32)


if __name__ == "__main__":
    unittest.main(verbosity=2)
