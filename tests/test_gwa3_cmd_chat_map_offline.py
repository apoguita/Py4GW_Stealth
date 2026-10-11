"""Offline tests for `py4gw.gwa3.cmd_chat` and `py4gw.gwa3.cmd_map`.

No client, no elevation, and **no action taken**: every route is a call into this project's own member and
the docs are replaced, so a test asserts *what would have been called*. For an action module that is the
only safe test and the sharpest one — an action reaching the wrong member, or the same member with the
wrong arguments, is a real defect a value-based test cannot see.
"""

from __future__ import annotations

import unittest
from unittest import mock

from py4gw.gwa3 import cmd_chat, cmd_map


class ChatSendTests(unittest.TestCase):
    """`Chat_SendChat` -- the channel opcode, and GwAu3's recursion."""

    def test_the_channel_glyph_reaches_send_chat_as_an_opcode(self) -> None:
        """GwAu3's channel argument is the opcode *character*, and it must stay one.

        The trap this pins: `ChatChannel.CHANNEL_ALL` is `3`, which is **not** an opcode — `'!'` is, and
        its ordinal is `33`. So a caller passing the enum, or an implementation passing `ord('!')`,
        reaches a channel that does not exist while looking correct.
        """

        for glyph in ("!", "@", "#", "$", "%", '"', "/"):
            with self.subTest(channel=glyph):
                with mock.patch.object(cmd_chat.chat, "SendChat", return_value=True) as send:
                    self.assertTrue(cmd_chat.Chat_SendChat("hi", glyph))
                    send.assert_called_once_with(glyph, "hi")

    def test_a_long_message_becomes_two_lines_rather_than_being_clamped(self) -> None:
        """GwAu3 trims to 120 and recurses with the remainder (`GwAu3_Cmd_Chat.au3:76-77`).

        A clamp would silently drop the tail — and the port's `SendChat` *does* clamp
        (`chat.py:139`), so the recursion is what keeps the second half from disappearing.
        """

        message = "a" * 250
        with mock.patch.object(cmd_chat.chat, "SendChat", return_value=True) as send:
            cmd_chat.Chat_SendChat(message, "!")
        self.assertEqual([call.args[1] for call in send.call_args_list], ["a" * 120, "a" * 120, "a" * 10])

    def test_an_empty_message_sends_nothing(self) -> None:
        with mock.patch.object(cmd_chat.chat, "SendChat", return_value=True) as send:
            self.assertFalse(cmd_chat.Chat_SendChat("", "!"))
        send.assert_not_called()

    def test_the_whisper_form_is_gwau3s_own_string(self) -> None:
        """`'whisper ' & $receiver & ',' & $message`, sent through the register channel `'/'`."""

        with mock.patch.object(cmd_chat, "Chat_SendChat", return_value=True) as send:
            cmd_chat.Chat_SendWhisper("Koss", "hello")
        send.assert_called_once_with("whisper Koss,hello", "/")

    def test_write_chat_bounds_the_sender_and_the_message(self) -> None:
        with mock.patch.object(cmd_chat.chat, "WriteChat") as write:
            cmd_chat.Chat_WriteChat("m" * 250, "s" * 40)
        first = write.call_args_list[0]
        self.assertEqual(len(first.args[2]), 19, "GwAu3 bounds the sender at 19")
        self.assertEqual(len(first.args[1]), 100, "GwAu3 bounds the message at 100")
        self.assertEqual(len(write.call_args_list), 3, "the remainder is recursed, not dropped")


class MapMoveTests(unittest.TestCase):
    """`Map_Move` -- GwAu3's randomisation, and the point it decides on."""

    def test_randomisation_is_applied_by_default(self) -> None:
        """GwAu3's `$a_f_Randomize = 50` adds `Random(-r, r)` to each coordinate before storing it.

        So the destination is never exactly the point asked for, and that is part of the function rather
        than an aside: a script calling `Map_Move($x, $y)` asks for GwAu3's wobble.
        """

        with mock.patch.object(cmd_map.Player, "Move") as move:
            cmd_map.Map_Move(100.0, 200.0)
        x, y, z = move.call_args.args
        self.assertAlmostEqual(x, 100.0, delta=50.0)
        self.assertAlmostEqual(y, 200.0, delta=50.0)
        self.assertEqual(z, 0)

    def test_randomisation_can_be_turned_off(self) -> None:
        with mock.patch.object(cmd_map.Player, "Move") as move:
            cmd_map.Map_Move(100.0, 200.0, randomize=0)
        move.assert_called_once_with(100.0, 200.0, 0)

    def test_move_layer_passes_the_layer_as_the_plane(self) -> None:
        with mock.patch.object(cmd_map.Player, "Move") as move:
            cmd_map.Map_MoveLayer(10.0, 20.0, layer=3)
        move.assert_called_once_with(10.0, 20.0, 3)


class MapTravelTests(unittest.TestCase):
    """`Map_TravelTo` -- GwAu3's own short-circuit, and the argument order."""

    def _serve(self, current_map: int, region: int, language: int, outpost: bool, explorable: bool = False):
        return (
            mock.patch.object(cmd_map.Map, "GetMapID", return_value=current_map),
            mock.patch.object(cmd_map.Map, "GetRegion", return_value=(region, "R")),
            mock.patch.object(cmd_map.Map, "GetLanguage", return_value=(language, "L")),
            mock.patch.object(cmd_map.Map, "IsOutpost", return_value=outpost),
            mock.patch.object(cmd_map.Map, "IsExplorable", return_value=explorable),
            mock.patch.object(cmd_map.Map, "TravelToRegion"),
        )

    def test_already_there_in_an_outpost_travels_nowhere(self) -> None:
        """GwAu3's short-circuit (`GwAu3_Cmd_Map.au3:87-92`) -- a loop calling this must not re-send."""

        patches = self._serve(100, 2, 0, outpost=True)
        with mock.patch.object(cmd_map.Map, "TravelToRegion") as travel:
            for patch in patches[:-1]:
                patch.start()
            try:
                result = cmd_map.Map_TravelTo(100, language=0, region=2, wait_to_load=False)
            finally:
                for patch in patches[:-1]:
                    patch.stop()
        self.assertTrue(result)
        travel.assert_not_called()

    def test_a_different_map_travels(self) -> None:
        patches = self._serve(100, 2, 0, outpost=True)
        with mock.patch.object(cmd_map.Map, "TravelToRegion") as travel:
            for patch in patches[:-1]:
                patch.start()
            try:
                cmd_map.Map_TravelTo(200, language=3, region=4, district=1, wait_to_load=False)
            finally:
                for patch in patches[:-1]:
                    patch.stop()
        travel.assert_called_once_with(200, 4, 1, 3)

    def test_move_map_keeps_gwau3s_argument_order(self) -> None:
        """`Map_MoveMap` is `(map, region, district, language)` -- `Ui_MoveMap` is not (`:41`, `:217`)."""

        with mock.patch.object(cmd_map.Map, "TravelToRegion") as travel:
            cmd_map.Map_MoveMap(map_id=10, region=2, district=3, language=4)
        travel.assert_called_once_with(10, 2, 3, 4)


class MapWaitTests(unittest.TestCase):
    """The waits, and the two refusals that sit beside them."""

    def test_wait_map_is_loaded_answers_as_soon_as_the_predicate_holds(self) -> None:
        with mock.patch.object(cmd_map.Map, "IsMapReady", return_value=True):
            self.assertTrue(cmd_map.Map_WaitMapIsLoaded(timeout_ms=500))

    def test_wait_map_is_loaded_gives_up_at_its_bound(self) -> None:
        with mock.patch.object(cmd_map.Map, "IsMapReady", return_value=False):
            self.assertFalse(cmd_map.Map_WaitMapIsLoaded(timeout_ms=50))

    def test_the_latch_functions_refuse_because_the_latch_is_gwau3s_own(self) -> None:
        """`Map_InitMapIsLoaded` and `Map_MapIsLoaded` touch a slot in GwAu3's injected block.

        This project installs no such block, so there is no controller-side flag to clear or read.
        `Map.IsMapReady` answers a different question, and answering it for these would be a wrong
        boolean a caller could not detect.
        """

        for function in (cmd_map.Map_InitMapIsLoaded, cmd_map.Map_MapIsLoaded):
            with self.subTest(function=function.__name__):
                with self.assertRaises(NotImplementedError) as raised:
                    function()
                message = str(raised.exception)
                self.assertIn("py4gw/map.py:164", message)
                self.assertIn("injected", message)

    def test_rnd_travel_uses_gwau3s_district_tables(self) -> None:
        """A district index picks its region and language out of GwAu3's own tables (`:103-104`)."""

        patches = [
            mock.patch.object(cmd_map.Map, "GetMapID", return_value=100),
            mock.patch.object(cmd_map.Map, "GetRegion", return_value=(2, "R")),
            mock.patch.object(cmd_map.Map, "GetLanguage", return_value=(0, "L")),
            mock.patch.object(cmd_map.Map, "IsExplorable", return_value=True),
            mock.patch.object(cmd_map.random, "randint", return_value=7),
        ]
        with mock.patch.object(cmd_map, "Map_MoveMap") as move_map:
            for patch in patches:
                patch.start()
            try:
                cmd_map.Map_RndTravel(200, wait_to_load=False)
            finally:
                for patch in patches:
                    patch.stop()

        # Index 7 is region 0, language 0 in GwAu3's tables.
        move_map.assert_called_once_with(200, 0, 0, 0)


if __name__ == "__main__":
    unittest.main()
