"""Offline tests for `py4gw.gwa3.cmd_agent` -- GwAu3's `Agent_*` actions.

No client, no elevation, and **no action taken**: every route is a call into this project's own member,
and the project's members are replaced here, so a test asserts *what would have been called* rather than
calling it. That is the only way to test an action module safely, and it is also the sharpest check:
an action that reaches the wrong member, or the right member with the wrong arguments, is a real defect
that a value-based test would not see.

What is being established:

1. **The route**: which project member each GwAu3 action drives, with which arguments.
2. **GwAu3's guards**, in GwAu3's order -- including the zero id it allows on purpose.
3. **The refusals say why**, and refuse rather than acting on a guess.
"""

from __future__ import annotations

import unittest
from unittest import mock

from py4gw.gwa3 import cmd_agent


class ChangeTargetTests(unittest.TestCase):
    """`Agent_ChangeTarget` -- GwAu3's guard, and the route it takes."""

    def _call(self, agent_id: object, valid: bool = True) -> tuple[bool, list[int]]:
        record: list[int] = []
        with (
            mock.patch.object(cmd_agent, "Agent_ConvertID", side_effect=lambda value: int(value)),
            mock.patch.object(cmd_agent, "Agent_GetMyID", return_value=4242),
            mock.patch.object(cmd_agent.Player, "ChangeTarget", side_effect=record.append),
        ):
            result = cmd_agent.Agent_ChangeTarget(agent_id)
        return result, record

    def test_a_plain_id_is_passed_to_change_target(self) -> None:
        result, record = self._call(4242)
        self.assertTrue(result)
        self.assertEqual(record, [4242])

    def test_a_zero_id_is_allowed_on_purpose(self) -> None:
        """GwAu3's own comment records it: zero is how the native clears the selection.

        So the guard must let it through -- the first thing to get wrong here, because a guard written
        from the docstring ("refuse an invalid id") would reject the one value ``Agent_ClearTarget``
        depends on.
        """

        result, record = self._call(0)
        self.assertTrue(result)
        self.assertEqual(record, [0])

    def test_a_negative_id_is_refused_and_nothing_is_called(self) -> None:
        result, record = self._call(-5)
        self.assertFalse(result)
        self.assertEqual(record, [], "a negative id must not reach the client")

    def test_clear_target_goes_through_change_target_with_zero(self) -> None:
        with mock.patch.object(cmd_agent, "Agent_ChangeTarget", return_value=True) as change:
            self.assertTrue(cmd_agent.Agent_ClearTarget())
        change.assert_called_once_with(0)

    def test_target_self_uses_the_controlled_characters_id(self) -> None:
        with (
            mock.patch.object(cmd_agent, "Agent_GetMyID", return_value=4242),
            mock.patch.object(cmd_agent, "Agent_ChangeTarget", return_value=True) as change,
        ):
            self.assertTrue(cmd_agent.Agent_TargetSelf())
        change.assert_called_once_with(4242)


class RouteTests(unittest.TestCase):
    """Which project member each action drives, and with what."""

    def test_attack_drives_interact_with_the_call_target_flag(self) -> None:
        with (
            mock.patch.object(cmd_agent, "Agent_ConvertID", side_effect=lambda value: int(value)),
            mock.patch.object(cmd_agent.Player, "Interact") as interact,
        ):
            self.assertTrue(cmd_agent.Agent_Attack(77))
            interact.assert_called_once_with(77, False)

            interact.reset_mock()
            self.assertTrue(cmd_agent.Agent_Attack(77, call_target=True))
            interact.assert_called_once_with(77, True)

    def test_go_npc_drives_interact(self) -> None:
        with (
            mock.patch.object(cmd_agent, "Agent_ConvertID", side_effect=lambda value: int(value)),
            mock.patch.object(cmd_agent.Player, "Interact") as interact,
        ):
            self.assertTrue(cmd_agent.Agent_GoNPC(77))
            interact.assert_called_once_with(77)

    def test_go_player_and_go_signpost_drive_interact(self) -> None:
        for function in (cmd_agent.Agent_GoPlayer, cmd_agent.Agent_GoSignpost):
            with self.subTest(function=function.__name__):
                with (
                    mock.patch.object(cmd_agent, "Agent_ConvertID", side_effect=lambda value: int(value)),
                    mock.patch.object(cmd_agent.Player, "Interact") as interact,
                ):
                    self.assertTrue(function(88))
                    interact.assert_called_once_with(88)

    def test_call_target_drives_players_call_target(self) -> None:
        with (
            mock.patch.object(cmd_agent, "Agent_ConvertID", side_effect=lambda value: int(value)),
            mock.patch.object(cmd_agent.Player, "CallTarget") as call_target,
        ):
            self.assertTrue(cmd_agent.Agent_CallTarget(99))
            call_target.assert_called_once_with(99)

    def test_the_sentinels_reach_the_routes_resolved(self) -> None:
        """`-2` and `-1` go through `Agent_ConvertID` before any route sees them."""

        with (
            mock.patch.object(cmd_agent, "Agent_ConvertID", side_effect=lambda value: {(-2): 4242, (-1): 77}[value]) as convert,
            mock.patch.object(cmd_agent.Player, "Interact") as interact,
        ):
            cmd_agent.Agent_GoNPC(-2)
            interact.assert_called_once_with(4242)
            convert.assert_called_with(-2)


class RefusalTests(unittest.TestCase):
    """The one action with no route refuses and says why; the cancel has a route now."""

    def test_cancel_action_presses_the_clients_own_cancel_control_action(self) -> None:
        """GwAu3 forges ``HEADER_ACTION_CANCEL``; Reforged presses ``ControlAction_CancelAction``.

        The press is asserted where the layer makes it: `cmd_agent` calls the layer's control-action
        member with GwAu3's own constant, and that member is what presses (``0xAF``) -- the code this
        port's own enum carries as ``ControlAction_CancelAction``.
        """

        with mock.patch.object(cmd_agent, "Core_ControlAction") as control:
            self.assertTrue(cmd_agent.Agent_CancelAction())
        control.assert_called_once_with(cmd_agent._constants.GC_I_CONTROL_ACTION_CANCEL_ACTION)
        self.assertEqual(cmd_agent._constants.GC_I_CONTROL_ACTION_CANCEL_ACTION, 0xAF)

    def test_make_agent_array_refuses_and_names_the_reader(self) -> None:
        with self.assertRaises(NotImplementedError) as raised:
            cmd_agent.Agent_MakeAgentArray()
        message = str(raised.exception)
        self.assertIn("GwAu3_Cmd_Agent.au3:22-33", message)
        self.assertIn("Agent_GetAgentArray", message)


class NearestTargetTests(unittest.TestCase):
    """`Agent_TargetNearest*` -- GwAu3's own walk, and its own defaults."""

    def _serve(self, agents: dict[int, dict[str, object]], my_id: int = 1):
        """Answer `Agent_GetAgentInfo` and the distance helper from a table, so the walk is testable."""

        def info(agent_id: int, key: str) -> object:
            return agents[agent_id][key]

        def distance(agent1_id: int, agent2_id: int = -2) -> float:
            return float(agents[agent1_id]["Distance"])  # type: ignore[arg-type]

        return (
            mock.patch.object(cmd_agent, "Agent_GetMyID", return_value=my_id),
            mock.patch.object(cmd_agent.AgentArray, "GetAgentArray", return_value=sorted(agents)),
            mock.patch.object(cmd_agent, "Agent_GetAgentInfo", side_effect=info),
            mock.patch.object(cmd_agent, "Agent_GetDistance", side_effect=distance),
            mock.patch.object(cmd_agent, "Agent_ChangeTarget", return_value=True),
        )

    def test_the_nearest_enemy_within_range_is_targeted(self) -> None:
        agents = {
            1: {"IsDead": False, "Allegiance": 1, "Distance": 0.0},      # me, an ally
            2: {"IsDead": False, "Allegiance": 3, "Distance": 500.0},    # enemy, near
            3: {"IsDead": False, "Allegiance": 3, "Distance": 200.0},    # enemy, nearer
            4: {"IsDead": False, "Allegiance": 3, "Distance": 9000.0},   # enemy, out of range
        }
        patches = self._serve(agents)
        for patch in patches[:-1]:
            patch.start()
        try:
            with mock.patch.object(cmd_agent, "Agent_ChangeTarget") as change:
                result = cmd_agent.Agent_TargetNearestEnemy()
        finally:
            for patch in patches[:-1]:
                patch.stop()

        self.assertEqual(result, 3)
        change.assert_called_once_with(3)

    def test_a_dead_enemy_is_skipped(self) -> None:
        agents = {
            1: {"IsDead": False, "Allegiance": 1, "Distance": 0.0},
            2: {"IsDead": True, "Allegiance": 3, "Distance": 100.0},
            3: {"IsDead": False, "Allegiance": 3, "Distance": 800.0},
        }
        patches = self._serve(agents)
        for patch in patches[:-1]:
            patch.start()
        try:
            with mock.patch.object(cmd_agent, "Agent_ChangeTarget"):
                result = cmd_agent.Agent_TargetNearestEnemy()
        finally:
            for patch in patches[:-1]:
                patch.stop()

        self.assertEqual(result, 3, "the dead agent at 100 must not win")

    def test_nothing_in_range_answers_zero_and_calls_nothing(self) -> None:
        agents = {
            1: {"IsDead": False, "Allegiance": 1, "Distance": 0.0},
            2: {"IsDead": False, "Allegiance": 3, "Distance": 9999.0},
        }
        patches = self._serve(agents)
        for patch in patches[:-1]:
            patch.start()
        try:
            with mock.patch.object(cmd_agent, "Agent_ChangeTarget") as change:
                result = cmd_agent.Agent_TargetNearestEnemy()
        finally:
            for patch in patches[:-1]:
                patch.stop()

        self.assertEqual(result, 0)
        change.assert_not_called()

    def test_the_ally_search_excludes_self_by_default(self) -> None:
        """`$a_b_ExcludeSelf = True` is GwAu3's own default (`GwAu3_Cmd_Agent.au3:73`)."""

        agents = {
            1: {"IsDead": False, "Allegiance": 1, "Distance": 0.0},      # me, nearest ally
            2: {"IsDead": False, "Allegiance": 1, "Distance": 400.0},
        }
        patches = self._serve(agents)
        for patch in patches[:-1]:
            patch.start()
        try:
            with mock.patch.object(cmd_agent, "Agent_ChangeTarget"):
                result = cmd_agent.Agent_TargetNearestAlly()
        finally:
            for patch in patches[:-1]:
                patch.stop()

        self.assertEqual(result, 2, "self must be excluded, or the search would target me")

    def test_the_ally_search_can_include_self(self) -> None:
        agents = {
            1: {"IsDead": False, "Allegiance": 1, "Distance": 0.0},
            2: {"IsDead": False, "Allegiance": 1, "Distance": 400.0},
        }
        patches = self._serve(agents)
        for patch in patches[:-1]:
            patch.start()
        try:
            with mock.patch.object(cmd_agent, "Agent_ChangeTarget"):
                result = cmd_agent.Agent_TargetNearestAlly(exclude_self=False)
        finally:
            for patch in patches[:-1]:
                patch.stop()

        self.assertEqual(result, 1)

    def test_the_animal_search_tests_the_neutral_byte(self) -> None:
        """GwAu3's `$GC_I_ALLEGIANCE_ANIMAL` is `0x2`, which this project names `Neutral`."""

        agents = {
            1: {"IsDead": False, "Allegiance": 1, "Distance": 0.0},
            2: {"IsDead": False, "Allegiance": 2, "Distance": 300.0},   # the animal byte
            3: {"IsDead": False, "Allegiance": 4, "Distance": 100.0},   # GwAu3's SPIRIT, not ANIMAL
        }
        patches = self._serve(agents)
        for patch in patches[:-1]:
            patch.start()
        try:
            with mock.patch.object(cmd_agent, "Agent_ChangeTarget"):
                result = cmd_agent.Agent_TargetNearestAnimal()
        finally:
            for patch in patches[:-1]:
                patch.stop()

        self.assertEqual(result, 2, "the spirit at 100 is not an animal and must be skipped")

    def test_the_default_range_is_gwau3s_own(self) -> None:
        import inspect

        for function in (
            cmd_agent.Agent_TargetNearestEnemy,
            cmd_agent.Agent_TargetNearestAlly,
            cmd_agent.Agent_TargetNearestAnimal,
        ):
            with self.subTest(function=function.__name__):
                parameters = inspect.signature(function).parameters
                self.assertEqual(parameters["max_distance"].default, 1300)

    def test_only_enemy_has_no_exclude_self(self) -> None:
        """GwAu3 gives the enemy search one parameter and the other two two (`:35`, `:73`, `:114`)."""

        import inspect

        self.assertNotIn(
            "exclude_self", inspect.signature(cmd_agent.Agent_TargetNearestEnemy).parameters
        )
        self.assertIn("exclude_self", inspect.signature(cmd_agent.Agent_TargetNearestAlly).parameters)
        self.assertIn("exclude_self", inspect.signature(cmd_agent.Agent_TargetNearestAnimal).parameters)


if __name__ == "__main__":
    unittest.main()
