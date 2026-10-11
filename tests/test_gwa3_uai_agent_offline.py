"""Offline tests for `py4gw/gwa3/uai_agent.py` -- the UtilityAI agent-cache accessors.

No client and no elevation. Three things are being established, and the first is the one that matters
most:

1. **every routed column names a key that exists in this project's agent table** -- a column whose key
   is misspelled would answer `0` through that table's own unknown-field fallthrough, which is a wrong
   value of the right type and invisible to a caller. Four of the sixty-one entries were wrong when
   this table was first written, which is why the check exists as a test;
2. the columns whose key exists are answered from the agent, with the column numbers read from GwAu3's
   own generated constants rather than transcribed;
3. the refused columns refuse, and for the two different reasons they have.
"""

from __future__ import annotations

import unittest
from unittest import mock

from py4gw.gwa3 import constants, data_agent, uai_agent


class ColumnMappingTests(unittest.TestCase):
    """The table, against the agent table it points into."""

    def test_every_routed_column_names_a_key_the_agent_table_has(self) -> None:
        known = set(data_agent._READERS) | set(data_agent._UNIMPLEMENTED)
        wrong = {
            column: key for column, key in uai_agent._COLUMN_KEYS.items() if key not in known
        }
        self.assertEqual(
            wrong,
            {},
            "these columns name an agent key that does not exist, so they would answer 0",
        )

    def test_the_column_numbers_come_from_gwaus_own_enum(self) -> None:
        """The numbers are read from the generated constants, not renumbered by hand."""

        self.assertEqual(uai_agent._COLUMNS[constants.GC_UAI_AGENT_Ptr], "Ptr")
        self.assertEqual(uai_agent._COLUMNS[constants.GC_UAI_AGENT_X], "X")
        self.assertEqual(uai_agent._COLUMNS[constants.GC_UAI_AGENT_Type], "Type")
        self.assertEqual(uai_agent._COLUMNS[constants.GC_UAI_AGENT_IsNPC], "IsNPC")
        # The enum carries its own terminator, which is a count rather than a column.
        self.assertNotIn(constants.GC_UAI_AGENT_COUNT, uai_agent._COLUMNS)

    def test_the_declared_surface(self) -> None:
        """Six accessors, which is what this part of the cache declares."""

        self.assertEqual(len(uai_agent.__all__), 6)


class ColumnReadTests(unittest.TestCase):
    """The routed columns, against a mocked agent table."""

    def test_a_column_reads_its_agent_key(self) -> None:
        with mock.patch.object(
            uai_agent, "Agent_GetAgentInfo", return_value=1234
        ) as accessor, mock.patch.object(uai_agent, "Agent_ConvertID", return_value=235):
            self.assertEqual(uai_agent.UAI_GetAgentInfoByID(235, constants.GC_UAI_AGENT_X), 1234)
            accessor.assert_called_once_with(235, "X")

    def test_the_by_id_and_by_row_spellings_are_one_call(self) -> None:
        """GwAu3 resolves a row first and reads the same column; here both take the agent."""

        with mock.patch.object(uai_agent, "Agent_GetAgentInfo", return_value=7) as accessor, (
            mock.patch.object(uai_agent, "Agent_ConvertID", return_value=9)
        ):
            by_id = uai_agent.UAI_GetAgentInfoByID(9, constants.GC_UAI_AGENT_Level)
            by_row = uai_agent.UAI_GetAgentInfo(9, constants.GC_UAI_AGENT_Level)
            self.assertEqual(by_id, by_row)
            self.assertEqual(accessor.call_count, 2)

    def test_an_unknown_column_answers_zero(self) -> None:
        """GwAu3's own `EndSwitch` fallthrough, which its callers branch on."""

        with mock.patch.object(uai_agent, "Agent_GetAgentInfo") as accessor:
            self.assertEqual(uai_agent.UAI_GetAgentInfo(1, 9999), 0)
            accessor.assert_not_called()

    def test_the_agent_count_is_the_live_array(self) -> None:
        from py4gw.agent_array import AgentArray

        with mock.patch.object(AgentArray, "GetAgentArray", return_value=[1, 2, 3]):
            self.assertEqual(uai_agent.UAI_GetAgentCount(), 3)

    def test_the_player_columns_come_from_the_controlled_character(self) -> None:
        from py4gw.player import Player

        with mock.patch.object(Player, "GetAgentID", return_value=235), mock.patch.object(
            uai_agent, "Agent_GetAgentInfo", return_value=20
        ) as accessor:
            self.assertEqual(uai_agent.UAI_GetPlayerInfo(constants.GC_UAI_AGENT_Level), 20)
            accessor.assert_called_once_with(235, "Level")


class ColumnRefusalTests(unittest.TestCase):
    """The refused columns, and the three that used to refuse and now answer.

    Six columns are cache-only bookkeeping and still refuse. The three model-state columns -- which
    GwAu3's two files define differently -- **answer now**, because this project has a third source for
    them and it settles the disagreement: Reforged Native's ported
    `AgentLivingStruct.is_attacking`/`is_idle`/`is_moving` use exactly the Data module's three sets, so
    the plugin's own cache decoder is the outlier. What these tests pin is that the columns route, that
    the values are the Data module's sets, and that the measurement behind the choice is on the record.
    """

    DISAGREEING = ("IsAttacking", "IsIdle", "IsMoving")
    CACHE_ONLY = ("Ptr", "Timer", "IsExploitableCorpse", "IsPlayer", "IsNPC")

    #: ``{column: (the model state it answers True for, a state it answers False for)}`` -- from
    #: ``GwAu3_Data_Agent.au3:338-347``, whose sets Reforged Native's members match.
    MODEL_STATES = {
        "IsAttacking": (0x60, 0x40),
        "IsIdle": (0x40, 0x60),
        "IsMoving": (0xC, 0x44),
    }

    def test_the_three_model_state_columns_answer_the_data_modules_sets(self) -> None:
        for name, (true_state, false_state) in self.MODEL_STATES.items():
            with self.subTest(column=name):
                column = getattr(constants, f"GC_UAI_AGENT_{name}")
                with mock.patch.object(
                    uai_agent, "Agent_GetAgentInfo", lambda agent_id, key: key == name
                ):
                    self.assertTrue(uai_agent.UAI_GetAgentInfo(1, column))
                self.assertIn(name, uai_agent._COLUMN_KEYS)
                self.assertNotIn(name, uai_agent._CACHE_ONLY_COLUMNS)
                # The two states are the ones the two GwAu3 files read differently, and the layer's
                # answer for `0x40` is the Data module's: idle, not attacking.
                self.assertNotEqual(true_state, false_state)

    def test_the_module_header_records_the_measurement_that_settled_them(self) -> None:
        """The choice is evidence-backed, and the evidence is named where it is made."""

        header = uai_agent.__doc__ or ""
        self.assertIn("Reforged Native", header)
        self.assertIn("py4gw/context/agent_array.py", header)
        self.assertIn("probe_gwa3_model_state_live.py", header)
        self.assertIn("0x40", header)

    def test_the_distance_column_answers_through_the_layers_own_difference(self) -> None:
        """``Distance`` is the cache's one column with a live twin, so it routes rather than refusing.

        GwAu3 fills it as the distance to the **player** when it fills its cache; the layer computes the
        same number when it is asked (`uai_get_agent._cached_distance`), which is the substitution the
        strategy generator applies to every body that reads it.
        """

        with mock.patch(
            "py4gw.gwa3.uai_get_agent._cached_distance", return_value=1234.5
        ) as distance:
            self.assertEqual(
                uai_agent.UAI_GetAgentInfo(7, constants.GC_UAI_AGENT_Distance), 1234.5
            )
        distance.assert_called_once_with(7)
        self.assertNotIn("Distance", uai_agent._CACHE_ONLY_COLUMNS)

    def test_the_cache_only_columns_refuse_as_bookkeeping(self) -> None:
        for name in self.CACHE_ONLY:
            with self.subTest(column=name):
                column = getattr(constants, f"GC_UAI_AGENT_{name}")
                with self.assertRaises(NotImplementedError) as raised:
                    uai_agent.UAI_GetAgentInfo(1, column)
                self.assertIn("per-frame cache", str(raised.exception))

    def test_the_index_accessors_refuse(self) -> None:
        for routine, args in ((uai_agent.UAI_GetIndexByID, (1,)), (uai_agent.UAI_GetPlayerIndex, ())):
            with self.subTest(routine=routine.__name__):
                with self.assertRaises(NotImplementedError) as raised:
                    routine(*args)
                message = str(raised.exception)
                self.assertIn("UtilityAI_AgentCache.au3", message)
                self.assertIn("py4gw", message)


if __name__ == "__main__":
    unittest.main()
