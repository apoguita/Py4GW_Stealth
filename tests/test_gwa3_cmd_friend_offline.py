"""Offline tests for `py4gw/gwa3/cmd_friend.py`.

No client and no elevation. The layer's own contract, not GwAu3's behaviour: the five status functions
reach `Player.SetPlayerStatus` with GwAu3's own guard order, and the four management functions refuse
naming the mechanism they refuse.
"""

from __future__ import annotations

import unittest
from unittest import mock

from py4gw.gwa3 import cmd_friend


class FriendStatusTests(unittest.TestCase):
    """The five routed status functions."""

    def test_a_status_outside_the_range_never_reaches_the_client(self) -> None:
        """GwAu3's first guard: outside $GC_I_FRIEND_STATUS_OFFLINE..$GC_I_FRIEND_STATUS_AWAY."""

        with mock.patch.object(cmd_friend.Player, "SetPlayerStatus") as setter, mock.patch.object(
            cmd_friend.Player, "GetPlayerStatus"
        ) as getter:
            self.assertFalse(cmd_friend.Friend_SetPlayerStatus(-1))
            self.assertFalse(cmd_friend.Friend_SetPlayerStatus(4))
            setter.assert_not_called()
            getter.assert_not_called()

    def test_a_status_already_set_answers_true_without_calling(self) -> None:
        """GwAu3's second guard: it reads the current status and returns True early."""

        with mock.patch.object(
            cmd_friend.Player, "GetPlayerStatus", return_value=1
        ), mock.patch.object(cmd_friend.Player, "SetPlayerStatus") as setter:
            self.assertTrue(cmd_friend.Friend_SetPlayerStatus(1))
            setter.assert_not_called()

    def test_a_different_status_is_set(self) -> None:
        with mock.patch.object(
            cmd_friend.Player, "GetPlayerStatus", return_value=0
        ), mock.patch.object(cmd_friend.Player, "SetPlayerStatus", return_value=True) as setter:
            self.assertTrue(cmd_friend.Friend_SetPlayerStatus(2))
            setter.assert_called_once_with(2)

    def test_the_named_statuses_use_gwau3s_own_numbers(self) -> None:
        with mock.patch.object(
            cmd_friend.Player, "GetPlayerStatus", return_value=-1
        ), mock.patch.object(cmd_friend.Player, "SetPlayerStatus", return_value=True) as setter:
            cmd_friend.Friend_SetOfflineStatus()
            cmd_friend.Friend_SetOnlineStatus()
            cmd_friend.Friend_SetDNDStatus()
            cmd_friend.Friend_SetAwayStatus()
            self.assertEqual(
                [call.args[0] for call in setter.call_args_list], [0, 1, 2, 3]
            )


class FriendRefusalTests(unittest.TestCase):
    """The four management functions, which take GwAu3's remote-allocation path."""

    CASES = (
        ("Friend_AddFriend", ("Someone",)),
        ("Friend_RemoveFriend", ("Someone",)),
        ("Friend_AddIgnore", ("Someone",)),
        ("Friend_RemoveIgnore", ("Someone",)),
    )

    def test_every_refusal_names_the_source_and_the_work(self) -> None:
        for name, args in self.CASES:
            with self.subTest(name=name):
                with self.assertRaises(NotImplementedError) as raised:
                    getattr(cmd_friend, name)(*args)
                message = str(raised.exception)
                self.assertIn("GwAu3_Cmd_Friend.au3", message)
                self.assertIn("py4gw", message)

    def test_the_declared_surface_is_the_sources_own(self) -> None:
        """Nine functions, which is what `GwAu3_Cmd_Friend.au3` declares."""

        self.assertEqual(len(cmd_friend.__all__), 9)
        for name in cmd_friend.__all__:
            self.assertTrue(callable(getattr(cmd_friend, name)), name)


if __name__ == "__main__":
    unittest.main()
