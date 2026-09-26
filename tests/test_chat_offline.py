"""Offline tests for ``py4gw/chat.py``: the send half of ``GW::chat``.

No client is involved. ``GW::chat::SendChat`` builds a ``wchar_t buffer[140]`` and hands its
address to the client's sender (``chat_methods.cpp:88-142``); this port builds the same buffer in
the block's data region and calls the same function through the capability layer. So what these
tests drive is a client that records **the bytes it was handed** and **the call it was asked
for**, which is exactly the evidence the source's own behaviour is about:

- the buffer's first code unit is the channel opcode and the rest is the message;
- a message longer than 120 code units is cut, because the source cuts it;
- the buffer ends in a terminator, because the client reads it as a C string;
- a message that is not sent is *not* placed and *not* called;
- the whisper form is ``L"\\"%s,%s"``, quote and comma included;
- ``GetChannel``'s seven opcodes, and what it answers for anything else.

What it does not prove: that the client's own sender accepts the buffer. That needs a live run
and is what ``tests/probe_chat_send.py`` does.
"""

from __future__ import annotations

import unittest
from typing import Any, cast
from unittest import mock

from py4gw import chat
from py4gw.game_thread.shared_block import CallForm

PLACED_ADDRESS = 0x00A00000


class _FakeBridge:
    """The bridge surface a chat send uses: one span of the data region, and what went in it."""

    def __init__(self) -> None:
        self.written: list[tuple[int, bytes]] = []

    def write_data(self, offset: int, payload: bytes) -> int:
        self.written.append((offset, payload))
        return PLACED_ADDRESS + offset


class _FakeClient:
    """A client that records the calls it is asked to make."""

    def __init__(self, resolves: bool = True) -> None:
        self.bridge = _FakeBridge()
        self.calls: list[tuple[str, CallForm, tuple[int, ...]]] = []
        self._resolves = resolves

    def resolves(self, name: str) -> bool:
        return self._resolves

    def call_function(self, name: str, form: CallForm, *words: int) -> Any:
        self.calls.append((name, form, tuple(words)))
        return None


class ChatSendTests(unittest.TestCase):
    """What ``SendChat`` hands the client, for each of the source's overloads."""

    def setUp(self) -> None:
        self.client = _FakeClient()
        # ``chat.py`` imports ``require_client`` inside each function, so patching it on the
        # client module is what redirects the module, and the side effect reads ``self.client``
        # at call time — a test that swaps the client mid-test gets the new one.
        self._patch = mock.patch(
            "py4gw.client.require_client", side_effect=lambda: self.client
        )
        self._patch.start()
        self.addCleanup(self._patch.stop)

    def placed_text(self) -> str:
        """The buffer this client was handed, decoded back out of its UTF-16 bytes."""

        self.assertEqual(len(self.client.bridge.written), 1, "one buffer was placed")
        _, payload = self.client.bridge.written[0]
        self.assertEqual(payload[-2:], b"\x00\x00", "the buffer ends in a terminator")
        return payload[:-2].decode("utf-16-le")

    def test_a_channel_message_is_the_opcode_then_the_text(self) -> None:
        """``buffer[0] = channel; wcsncpy(&buffer[1], msg, len)`` (``chat_methods.cpp:98-100``)."""

        self.assertTrue(chat.SendChat("!", "hello"))

        self.assertEqual(self.placed_text(), "!hello")
        self.assertEqual(
            self.client.calls,
            [
                (
                    chat.SEND_CHAT_FUNC,
                    CallForm.U32_U32,
                    (PLACED_ADDRESS + chat.BUFFER_OFFSET, 0),
                )
            ],
            "the sender takes the buffer's address in the client's own memory, and agent id 0",
        )

    def test_every_opcode_GetChannel_knows_is_accepted(self) -> None:
        for opcode in ("!", "@", "#", "$", "%", '"', "/"):
            with self.subTest(opcode=opcode):
                self.client = _FakeClient()
                self.assertTrue(chat.SendChat(opcode, "x"), f"{opcode} is an opcode")
                self.assertEqual(self.placed_text(), f"{opcode}x")

    def test_a_message_longer_than_the_clamp_is_cut_not_refused(self) -> None:
        """``len = len > 120 ? 120 : len`` (``chat_methods.cpp:95-96``)."""

        message = "a" * 500

        self.assertTrue(chat.SendChat("!", message))

        self.assertEqual(self.placed_text(), "!" + "a" * chat.MAX_MESSAGE_CODE_UNITS)

    def test_an_empty_message_sends_nothing(self) -> None:
        """``msg && *msg`` is part of the source's guard (``chat_methods.cpp:89``)."""

        self.assertFalse(chat.SendChat("!", ""))

        self.assertEqual(self.client.bridge.written, [])
        self.assertEqual(self.client.calls, [])

    def test_an_opcode_the_sender_does_not_know_sends_nothing(self) -> None:
        """``GetChannel(channel) != CHANNEL_UNKNOWN`` — the source's own refusal."""

        self.assertFalse(chat.SendChat("A", "hello"))

        self.assertEqual(self.client.bridge.written, [])
        self.assertEqual(self.client.calls, [])

    def test_a_channel_enum_value_is_not_an_opcode(self) -> None:
        """``CHANNEL_ALL`` is ``3``, and ``3`` is not what ``GetChannel`` knows.

        Reforged's own binding passes the value straight through as the ``char`` the sender
        takes, so the source refuses it too. This pins that the port refuses it for the same
        reason rather than quietly translating it.
        """

        self.assertFalse(chat.SendChat(chat.ChatChannel.CHANNEL_ALL, "hello"))

        self.assertEqual(self.client.bridge.written, [])
        self.assertEqual(self.client.calls, [])

    def test_an_unresolved_sender_sends_nothing(self) -> None:
        """``g_send_chat_func`` being null is the first thing the source checks."""

        self.client = _FakeClient(resolves=False)

        self.assertFalse(chat.SendChat("!", "hello"))

        self.assertEqual(self.client.bridge.written, [])
        self.assertEqual(self.client.calls, [])

    def test_a_whisper_is_the_quoted_form_the_source_formats(self) -> None:
        """``swprintf(buffer, 140, L"\\"%s,%s", from, msg)`` (``chat_methods.cpp:120``)."""

        self.assertTrue(chat.SendChat("Apo The Great", "hello"))

        self.assertEqual(self.placed_text(), '"Apo The Great,hello')
        self.assertEqual(
            self.client.calls,
            [
                (
                    chat.SEND_CHAT_FUNC,
                    CallForm.U32_U32,
                    (PLACED_ADDRESS + chat.BUFFER_OFFSET, 0),
                )
            ],
        )

    def test_a_whisper_that_does_not_fit_the_buffer_is_refused(self) -> None:
        """``written < 140`` is the source's own bound on the formatted buffer."""

        self.assertFalse(chat.SendChat("n" * 100, "m" * 100))

        self.assertEqual(self.client.bridge.written, [])
        self.assertEqual(self.client.calls, [])

    def test_a_whisper_needs_a_name_and_a_message(self) -> None:
        """``from && *from && msg && *msg`` (``chat_methods.cpp:117``)."""

        self.assertFalse(chat.SendChat("Apo", ""))
        self.assertFalse(chat.SendChat("", "hello"))

        self.assertEqual(self.client.calls, [])

    def test_a_buffer_that_would_not_fit_the_source_array_is_refused(self) -> None:
        """``wchar_t buffer[140]`` is the source's array; the port refuses to overrun its span."""

        with self.assertRaises(ValueError):
            chat._place(cast(Any, self.client), "x" * chat.BUFFER_CODE_UNITS)


class GetChannelTests(unittest.TestCase):
    """``GW::chat::GetChannel`` (``chat_methods.cpp:53-68``), both overloads."""

    def test_the_seven_opcodes(self) -> None:
        self.assertEqual(chat.GetChannel("!"), chat.ChatChannel.CHANNEL_ALL)
        self.assertEqual(chat.GetChannel("@"), chat.ChatChannel.CHANNEL_GUILD)
        self.assertEqual(chat.GetChannel("#"), chat.ChatChannel.CHANNEL_GROUP)
        self.assertEqual(chat.GetChannel("$"), chat.ChatChannel.CHANNEL_TRADE)
        self.assertEqual(chat.GetChannel("%"), chat.ChatChannel.CHANNEL_ALLIANCE)
        self.assertEqual(chat.GetChannel('"'), chat.ChatChannel.CHANNEL_WHISPER)
        self.assertEqual(chat.GetChannel("/"), chat.ChatChannel.CHANNEL_COMMAND)

    def test_anything_else_is_unknown(self) -> None:
        self.assertEqual(chat.GetChannel("A"), chat.ChatChannel.CHANNEL_UNKNOWN)
        self.assertEqual(chat.GetChannel(" "), chat.ChatChannel.CHANNEL_UNKNOWN)

    def test_a_code_unit_is_the_same_function(self) -> None:
        """The ``wchar_t`` overload casts to ``char`` and calls the narrow one (``66-68``)."""

        self.assertEqual(chat.GetChannel(ord("!")), chat.ChatChannel.CHANNEL_ALL)
        self.assertEqual(chat.GetChannel(ord("A")), chat.ChatChannel.CHANNEL_UNKNOWN)

    def test_an_opcode_is_one_character(self) -> None:
        with self.assertRaises(ValueError):
            chat.GetChannel("!!")

    def test_the_channel_values_are_the_sources(self) -> None:
        """``common/constants/chat.h:17-35``."""

        self.assertEqual(chat.ChatChannel.CHANNEL_ALLIANCE, 0)
        self.assertEqual(chat.ChatChannel.CHANNEL_ALL, 3)
        self.assertEqual(chat.ChatChannel.CHANNEL_WHISPER, 14)
        self.assertEqual(chat.ChatChannel.CHANNEL_COUNT, 15)
        self.assertEqual(chat.ChatChannel.CHANNEL_COMMAND, 16)
        self.assertEqual(chat.ChatChannel.CHANNEL_UNKNOWN, -1)


if __name__ == "__main__":
    unittest.main(verbosity=2)

class LiveChatHistoryTests(unittest.TestCase):
    """The watched history ``chat`` keeps from the client's own announcements.

    The mechanism is native's own subscription (``OnUICallback_ChatLogLine``, ``chat.cpp:205``),
    used for what the port was asked to do with it: keep the lines, so a history read after the
    fact does not depend on someone having asked for it first.
    """

    def setUp(self) -> None:
        chat.reset_live_history()
        self.addCleanup(chat.reset_live_history)
        from py4gw import player
        from py4gw.player import Player

        player._chat_history = []
        player._chat_ready = False
        self.addCleanup(setattr, player, "_chat_history", [])
        self.addCleanup(setattr, player, "_chat_ready", False)

    def _line_event(self, text: tuple[int, ...], message_id: int = chat.WRITE_TO_CHAT_LOG) -> Any:
        return mock.Mock(sequence=message_id, text=text)

    def test_the_watch_entry_is_the_log_message_and_its_message_word(self) -> None:
        """``kWriteToChatLog`` with the ``UIChatMessage.message`` offset."""

        self.assertEqual(chat.watch_entries(), ((chat.WRITE_TO_CHAT_LOG, 4),))

    def test_an_announced_line_is_handed_to_the_decoder(self) -> None:
        """The line starts a decode; its slot is remembered until the answer arrives."""

        begun: list[bytes] = []

        with mock.patch("py4gw.ui.async_decode.begin_string_decode", lambda encoded: (begun.append(encoded), 7)[1]), mock.patch(
            "py4gw.ui.async_decode.async_decode_str", lambda encoded, slot: True
        ):
            chat._on_chat_log_line(self._line_event((104, 105, 0)))

        self.assertEqual(len(begun), 1)
        self.assertTrue(begun[0].startswith(b"h\x00i\x00"))
        self.assertTrue(begun[0].endswith(b"\x00\x00"))
        self.assertEqual(chat._live_pending, [7])

    def test_a_line_the_wrapper_refused_is_not_remembered(self) -> None:
        """``async_decode_str`` answering ``False`` means the slot was already completed."""

        with mock.patch("py4gw.ui.async_decode.begin_string_decode", lambda encoded: 7), mock.patch(
            "py4gw.ui.async_decode.async_decode_str", lambda encoded, slot: False
        ):
            chat._on_chat_log_line(self._line_event((104, 0)))

        self.assertEqual(chat._live_pending, [])

    def test_other_messages_and_empty_copies_are_ignored(self) -> None:
        """The handler is registered for every UI message, so it filters by id first."""

        with mock.patch("py4gw.ui.async_decode.begin_string_decode", lambda encoded: 7), mock.patch(
            "py4gw.ui.async_decode.async_decode_str", lambda encoded, slot: True
        ):
            chat._on_chat_log_line(self._line_event((104, 0), message_id=0x100000A6))
            chat._on_chat_log_line(self._line_event((), message_id=chat.WRITE_TO_CHAT_LOG))

        self.assertEqual(chat._live_pending, [])

    def test_the_decoded_answer_lands_in_the_history_and_in_the_player_buffer(self) -> None:
        """The completion appends the text where ``Player.GetChatHistory`` reads it."""

        from py4gw import player
        from py4gw.player import Player

        chat._live_pending.append(7)
        with mock.patch("py4gw.ui.async_decode.decoded_text", lambda slot: ("hello", False)):
            chat._on_string_decoded(mock.Mock(sequence=7))

        self.assertEqual(chat.live_history(), ["hello"])
        self.assertEqual(Player.GetChatHistory(), ["hello"])
        self.assertTrue(Player.IsChatHistoryReady())
        self.assertEqual(chat._live_pending, [])

    def test_a_completion_for_an_unknown_slot_is_ignored(self) -> None:
        """A decode this module did not start is not a chat line."""

        from py4gw import player
        from py4gw.player import Player

        with mock.patch("py4gw.ui.async_decode.decoded_text", lambda slot: ("stray", False)):
            chat._on_string_decoded(mock.Mock(sequence=99))

        self.assertEqual(chat.live_history(), [])
        self.assertEqual(Player.GetChatHistory(), [])

    def test_the_history_is_capped_like_the_clients_own_ring(self) -> None:
        """``CHAT_LOG_LENGTH`` is the cap, so a long session cannot grow without bound."""

        for index in range(chat.CHAT_LOG_LENGTH + 10):
            chat._append_live_line(f"line {index}")

        history = chat.live_history()
        self.assertEqual(len(history), chat.CHAT_LOG_LENGTH)
        self.assertEqual(history[-1], f"line {chat.CHAT_LOG_LENGTH + 9}")
        self.assertEqual(history[0], "line 10")
