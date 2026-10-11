"""Offline tests for `py4gw/gwa3/cmd_ui.py`.

No client and no elevation. Every function in this module refuses, so what is being established is the
*quality* of the refusals: each one cites its own body line, names the mechanism, and -- where a routed
spelling of the same action exists -- names it, because that is what a migrating script needs.
"""

from __future__ import annotations

import inspect
import unittest

from py4gw.gwa3 import cmd_ui


def _arguments(routine: object) -> tuple[object, ...]:
    """One argument per parameter that has no default, so every signature is satisfied.

    Derived from the signature rather than hand-listed: a hand-written table is one more thing that can
    disagree with the module, and the first version of this file had two entries wrong for exactly that
    reason.
    """

    supplied: list[object] = []
    for parameter in inspect.signature(routine).parameters.values():  # type: ignore[arg-type]
        if parameter.default is inspect.Parameter.empty:
            supplied.append(1)
    return tuple(supplied)


#: Every function, with arguments that satisfy each signature.
CALLS: tuple[tuple[str, tuple[object, ...]], ...] = tuple(
    (name, _arguments(getattr(cmd_ui, name))) for name in cmd_ui.__all__
)


class UiRefusalTests(unittest.TestCase):
    """The forty refusals."""

    def test_every_function_refuses(self) -> None:
        self.assertEqual(len(CALLS), 40)
        for name, args in CALLS:
            with self.subTest(function=name):
                with self.assertRaises(NotImplementedError):
                    getattr(cmd_ui, name)(*args)

    def test_every_refusal_names_the_module_and_the_line(self) -> None:
        for name, args in CALLS:
            with self.subTest(function=name):
                with self.assertRaises(NotImplementedError) as raised:
                    getattr(cmd_ui, name)(*args)
                message = str(raised.exception)
                self.assertIn("GwAu3_Cmd_Ui.au3:", message)
                # The citation carries a line number, so a reader can open the body it refuses.
                tail = message.split("GwAu3_Cmd_Ui.au3:", 1)[1]
                self.assertTrue(tail.split()[0].split(" ")[0][0].isdigit(), message[:120])

    def test_the_six_rendering_functions_are_recorded_as_not_applicable(self) -> None:
        """They write GwAu3's own injected-block flag: no client behaviour is missing."""

        rendering = (
            "Ui_EnableRendering",
            "Ui_DisableRendering",
            "Ui_ToggleRendering",
            "Ui_PurgeHook",
            "Ui_ToggleRendering_",
            "Ui_PurgeHook_",
        )
        for name in rendering:
            with self.subTest(function=name):
                with self.assertRaises(NotImplementedError) as raised:
                    getattr(cmd_ui, name)()
                self.assertIn("injected code", str(raised.exception))

    def test_the_routed_twins_are_named(self) -> None:
        """A migrating script must be told the working spelling, not just that its own is refused."""

        twins = {
            "Ui_CommandHero": "Party_CommandHero",
            "Ui_CancelHero": "Party_CancelHero",
            "Ui_CommandAll": "Party_CommandAll",
            "Ui_CancelAll": "Party_CancelAll",
            "Ui_SetHeroBehavior": "Party_SetHeroAggression",
            "Ui_AddHero": "Party_AddHero",
            "Ui_KickHero": "Party_KickHero",
            "Ui_KickAllHeroes": "Party_KickAllHeroes",
            "Ui_AddNPC": "Party_AddNpc",
            "Ui_KickNPC": "Party_KickNpc",
            "Ui_LeaveGroup": "Party_LeaveGroup",
            "Ui_SetDifficulty": "Game_SwitchMode",
            "Ui_EnterChallenge": "Map_EnterChallenge",
            "Ui_MoveMap": "Map_MoveMap",
            "Ui_EnableHeroSkill": "Party_EnableHeroSkill",
            "Ui_DisableHeroSkill": "Party_DisableHeroSkill",
            "Ui_RewardQuest": "Quest_QuestReward",
            "Ui_AcceptQuest": "Quest_AcceptQuest",
            "Ui_Dialog": "Game_Dialog",
        }
        by_name = dict(CALLS)
        for name, twin in twins.items():
            with self.subTest(function=name, twin=twin):
                with self.assertRaises(NotImplementedError) as raised:
                    getattr(cmd_ui, name)(*by_name[name])
                self.assertIn(twin, str(raised.exception))

    def test_the_swapped_argument_spellings_are_recorded(self) -> None:
        """`Map_MoveMap` and `Ui_MoveMap` take the last two arguments in the opposite order."""

        with self.assertRaises(NotImplementedError) as raised:
            cmd_ui.Ui_MoveMap(1, 2, 3, 4)
        self.assertIn("swapped", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
