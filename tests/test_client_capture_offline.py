"""Offline tests for the connection's target capture.

The connection keeps one value the client sends it: the last target it announced,
taken from the client's own ``kChangeTarget`` message. It is the port of
``g_current_target_id``, which Reforged's runtime keeps from the same message
(``agent.cpp:161-165``), and ``Player.GetTargetID`` is what reads it.

The dialog state does **not** live here — it belongs to the dialog module, where
``dialog.cpp`` keeps it, and ``tests/test_dialog_offline.py`` covers it.

No client is involved. The handler is a message filter and a store, so it is exercised
directly rather than through a live target change, which no test can summon on demand.
The object is built with ``object.__new__`` on purpose: nothing here touches a process,
and ``ConnectedClient.__init__`` opens handles and asserts elevation.

What this does not prove: that the client sends ``kChangeTarget``, or which word of its
packet carries the id. Both are live facts, and ``tests/test_live_player.py`` asserts
them — the client announced target ``16`` and ``Player.GetTargetID`` read ``16``.
"""

from __future__ import annotations

import unittest

from py4gw.client import ConnectedClient
from py4gw.game_thread.shared_block import EventKind, EventRecord

#: ``UIMessage::kChangeTarget`` (``constants/ui.h:39``). Its packet is
#: ``ChangeTargetUIMsg``, whose first word is the manual target id — ``arg0``.
CHANGE_TARGET = 0x10000020

#: Watched messages that are not target changes, used to show the filter discriminates.
DIALOG_BODY = 0x100000A6
SEND_CALL_TARGET = 0x30000013


def event(message: int, arg0: int = 0, arg1: int = 0) -> EventRecord:
    """Build one UI-message event record."""

    return EventRecord(
        kind=EventKind.UI_MESSAGE,
        sequence=message,
        arg0=arg0,
        arg1=arg1,
        arg2=0,
        arg3=0,
        tick=0,
    )


def bare_connection() -> ConnectedClient:
    """Return a ``ConnectedClient`` with no process behind it.

    Only the target capture is under test, and it touches one attribute. Building the
    object this way keeps the test offline; it is not a pattern to copy for anything
    that actually uses the connection.
    """

    client = object.__new__(ConnectedClient)
    client._target_id = 0
    client._callbacks = None
    return client


class TargetCaptureTests(unittest.TestCase):
    """What the connection keeps from the client's target notices."""

    def test_the_handler_keeps_the_id_from_a_change_notice(self) -> None:
        client = bare_connection()

        client._capture_target(event(CHANGE_TARGET, arg0=531))

        self.assertEqual(client._target_id, 531)

    def test_a_change_to_no_target_is_kept_as_zero(self) -> None:
        """``0`` is a value here — the client saying it has no target."""

        client = bare_connection()
        client._capture_target(event(CHANGE_TARGET, arg0=531))

        client._capture_target(event(CHANGE_TARGET, arg0=0))

        self.assertEqual(client._target_id, 0)

    def test_the_handler_takes_the_first_word_and_not_the_second(self) -> None:
        """``ChangeTargetUIMsg`` is ``{manual_target_id, h0008, auto_target_id, ...}``.

        A handler reading ``arg1`` would look right against a packet that happened to
        carry the same value twice and wrong on every real one, so the words are given
        deliberately different values.
        """

        client = bare_connection()

        client._capture_target(event(CHANGE_TARGET, arg0=531, arg1=999))

        self.assertEqual(client._target_id, 531)

    def test_the_handler_ignores_every_other_message(self) -> None:
        """Two other watched messages, neither of which may touch the target."""

        client = bare_connection()
        client._capture_target(event(CHANGE_TARGET, arg0=531))

        client._capture_target(event(DIALOG_BODY, arg0=1, arg1=241))
        client._capture_target(event(SEND_CALL_TARGET, arg0=7, arg1=8))

        self.assertEqual(
            client._target_id,
            531,
            "a watched message that is not a target change must not overwrite the "
            "captured target",
        )

    def test_reading_it_needs_a_connection_that_captures(self) -> None:
        client = bare_connection()
        client._target_id = 531

        with self.assertRaises(RuntimeError) as caught:
            client.target_id

        self.assertIn("game_thread=True", str(caught.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
