"""Offline tests for ``py4gw/gwa3/core.py`` -- the door, and the layer's control-action route.

The three members tested here are the ones that move bytes into the client: ``Core_SendPacket`` and
``Core_Enqueue`` refuse (GwAu3's queue is a channel this project does not write into), and
``Core_PerformAction``/``Core_ControlAction`` are **routed** -- GwAu3's action record is not
reproduced, but the control action it asks for is pressed through the client's own frame message, the
way Reforged's own ``Keybinds`` press these actions (``routines_src/behaviourtrees_src/keybinds.py:101,119``).

No client is connected here: every press is mocked where the member makes it, so what is asserted is
the *call* -- the action word, the frame, and the two words the member refuses.
"""

from __future__ import annotations

import unittest
from unittest import mock

from py4gw.gwa3 import constants, core


class PerformActionRouteTests(unittest.TestCase):
    """`Core_PerformAction` -- one control action, pressed through the client's own frame message."""

    def test_the_action_is_pressed_down_and_released_on_the_button_action_frame(self) -> None:
        with mock.patch.object(core.UIManager, "Keydown") as down, mock.patch.object(
            core.UIManager, "Keyup"
        ) as up:
            self.assertIsNone(
                core.Core_PerformAction(
                    constants.GC_I_CONTROL_ACTION_CANCEL_ACTION,
                    constants.GC_I_CONTROL_TYPE_ACTIVATE,
                )
            )

        # ``0`` is the client's own button-action frame, which is what Reforged passes
        # (``routines_src/behaviourtrees_src/keybinds.py:101,119``) and what ``py4gw/map.py:1013-1014``
        # already does for the mission map.
        down.assert_called_once_with(constants.GC_I_CONTROL_ACTION_CANCEL_ACTION, 0)
        up.assert_called_once_with(constants.GC_I_CONTROL_ACTION_CANCEL_ACTION, 0)

    def test_the_cancel_code_is_the_one_this_ports_own_enum_carries(self) -> None:
        from py4gw.enums_src.ui_enums import ControlAction

        self.assertEqual(constants.GC_I_CONTROL_ACTION_CANCEL_ACTION, 0xAF)
        self.assertEqual(
            constants.GC_I_CONTROL_ACTION_CANCEL_ACTION,
            ControlAction.ControlAction_CancelAction.value,
        )

    def test_the_drop_item_code_is_the_one_this_ports_own_enum_carries(self) -> None:
        from py4gw.enums_src.ui_enums import ControlAction

        self.assertEqual(constants.GC_I_CONTROL_ACTION_DROP_ITEM, 0xCD)
        self.assertEqual(
            constants.GC_I_CONTROL_ACTION_DROP_ITEM,
            ControlAction.ControlAction_DropItem.value,
        )

    def test_control_action_forwards_with_the_activate_flag_by_default(self) -> None:
        """``Core_ControlAction($a_i_Action, $a_i_ActionType = $GC_I_CONTROL_TYPE_ACTIVATE)``."""

        with mock.patch.object(core.UIManager, "Keydown") as down, mock.patch.object(
            core.UIManager, "Keyup"
        ) as up:
            self.assertIsNone(core.Core_ControlAction(constants.GC_I_CONTROL_ACTION_CANCEL_ACTION))

        down.assert_called_once_with(constants.GC_I_CONTROL_ACTION_CANCEL_ACTION, 0)
        up.assert_called_once_with(constants.GC_I_CONTROL_ACTION_CANCEL_ACTION, 0)

    def test_the_two_words_the_route_cannot_carry_are_refused(self) -> None:
        """The deactivate flag and a non-zero type: GwAu3's client call takes them, this route has no word.

        Refusing them is the point -- pressing them as if they were the activate direction would be a
        different action reported as the one the caller asked for.
        """

        for flag, action_type in (
            (constants.GC_I_CONTROL_TYPE_DEACTIVATE, 0),
            (constants.GC_I_CONTROL_TYPE_ACTIVATE, 1),
        ):
            with self.subTest(flag=flag, action_type=action_type):
                with mock.patch.object(core.UIManager, "Keydown") as down:
                    with self.assertRaises(NotImplementedError) as raised:
                        core.Core_PerformAction(
                            constants.GC_I_CONTROL_ACTION_CANCEL_ACTION, flag, action_type
                        )
                down.assert_not_called()
                message = str(raised.exception)
                self.assertIn("GwAu3_Core.au3:568-573", message)
                self.assertIn("GwAu3_Core_Assembler.au3", message)
                self.assertIn("py4gw", message)

    def test_the_deactivate_flag_is_gwau3s_own_number(self) -> None:
        self.assertEqual(constants.GC_I_CONTROL_TYPE_ACTIVATE, 0x20)
        self.assertEqual(constants.GC_I_CONTROL_TYPE_DEACTIVATE, 0x22)


class RefusalTests(unittest.TestCase):
    """The two members that are GwAu3's queue itself stay refused, and say so."""

    def test_send_packet_refuses_and_names_the_route_vocabulary(self) -> None:
        with self.assertRaises(NotImplementedError) as raised:
            core.Core_SendPacket(0xC, 0x28, 1)
        message = str(raised.exception)
        self.assertIn("GwAu3_Core.au3:575-589", message)
        self.assertIn("forged", message)
        self.assertIn("docs/GWA3_ROUTE_MAP.md", message)

    def test_enqueue_refuses_the_queue_write(self) -> None:
        with self.assertRaises(NotImplementedError) as raised:
            core.Core_Enqueue(0x1000, 16)
        message = str(raised.exception)
        self.assertIn("GwAu3_Core.au3:559-566", message)
        self.assertIn("WriteProcessMemory", message)
        self.assertIn("Core_SendPacket", message)

    def test_the_three_status_words_refuse(self) -> None:
        for name in (
            "Core_GetLoginStatus",
            "Core_GetInGameStatus",
            "Core_GetStatusCode",
            "Core_GetStatusError",
        ):
            with self.subTest(member=name):
                with self.assertRaises(NotImplementedError) as raised:
                    getattr(core, name)()
                self.assertIn("offsets/", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
