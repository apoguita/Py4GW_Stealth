"""Offline tests for the ported agent-array facade (``py4gw/agent_array.py``).

The rule is the porting rule for a class: **the source's members, in the source's order, doing the
source's work**. Reforged's ``AgentArray.py`` cannot be imported here — its first line is
``import PyAgent`` — so its surface is read with :mod:`ast` and compared member for member, and its
pure helpers are exercised through this port with the ``Agent`` members they call faked.

The twelve array getters are the one place the port diverges, and the source says why itself: their
live path is the injected runtime's shared-memory channel (``SystemShaMemMgr``), with the
``GWContext.AgentArray.GetContext()`` route unreachable after the ``return``. This port has no such
channel and answers from that second route, so the delegation is pinned here instead of assumed.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path
from unittest import mock

import py4gw
from py4gw import agent as agent_module
from py4gw.agent_array import AgentArray

SOURCE = Path(r"C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib\AgentArray.py")

#: The source's own order, so a member that moves or disappears fails here.
SOURCE_MEMBERS = (
    "GetAgentArray",
    "GetAllyArray",
    "GetNeutralArray",
    "GetEnemyArray",
    "GetSpiritPetArray",
    "GetMinionArray",
    "GetNPCMinipetArray",
    "GetItemArray",
    "GetOwnedItemArray",
    "GetGadgetArray",
    "GetDeadAllyArray",
    "GetDeadEnemyArray",
    "GetAgentByID",
)

#: getter -> the *context view* member it must ask for. The three item/gadget names differ between
#: the two source files and the source bridges them itself: ``AgentArray.py:145`` calls
#: ``GetItemAgentArray`` for ``GetItemArray``, and the same for the owned-item and gadget pairs.
GETTER_ROUTES = {
    "GetAgentArray": "GetAgentArray",
    "GetAllyArray": "GetAllyArray",
    "GetNeutralArray": "GetNeutralArray",
    "GetEnemyArray": "GetEnemyArray",
    "GetSpiritPetArray": "GetSpiritPetArray",
    "GetMinionArray": "GetMinionArray",
    "GetNPCMinipetArray": "GetNPCMinipetArray",
    "GetItemArray": "GetItemAgentArray",
    "GetOwnedItemArray": "GetOwnedItemAgentArray",
    "GetGadgetArray": "GetGadgetAgentArray",
    "GetDeadAllyArray": "GetDeadAllyArray",
    "GetDeadEnemyArray": "GetDeadEnemyArray",
    "GetAgentByID": "GetAgentByID",
}


def _load_source_tree() -> ast.Module:
    if not SOURCE.is_file():
        raise unittest.SkipTest(f"the Reforged source is not on this machine: {SOURCE}")
    return ast.parse(SOURCE.read_text(encoding="utf-8"))


def _class_defs(tree: ast.Module) -> dict[str, ast.ClassDef]:
    return {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}


def _methods(node: ast.ClassDef) -> list[str]:
    return [
        item.name
        for item in node.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]


class AgentArraySurfaceTests(unittest.TestCase):
    """The source's class surface, name for name and in order."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.tree = _load_source_tree()
        cls.source_class = _class_defs(cls.tree)["AgentArray"]

    def test_every_top_level_member_is_here_in_the_source_s_order(self) -> None:
        """The thirteen getters first, then the four nested helper classes."""

        source_functions = _methods(self.source_class)
        self.assertEqual(tuple(source_functions), SOURCE_MEMBERS)
        for name in SOURCE_MEMBERS:
            with self.subTest(member=name):
                self.assertTrue(hasattr(AgentArray, name), f"{name} is missing")

        source_nested = [
            item.name for item in self.source_class.body if isinstance(item, ast.ClassDef)
        ]
        self.assertEqual(source_nested, ["Manipulation", "Sort", "Filter", "Routines"])
        for name in source_nested:
            with self.subTest(nested=name):
                self.assertTrue(hasattr(AgentArray, name))

    def test_every_nested_member_is_here(self) -> None:
        """Each helper class's members, in the source's order."""

        source_nested = {
            item.name: item
            for item in self.source_class.body
            if isinstance(item, ast.ClassDef)
        }
        for name, node in source_nested.items():
            ported = getattr(AgentArray, name)
            with self.subTest(nested=name):
                self.assertEqual(
                    _methods(node),
                    [member for member in _methods(node) if hasattr(ported, member)],
                    f"{name} lost a member",
                )

    def test_the_package_exposes_the_class_where_reforged_does(self) -> None:
        """``from Py4GWCoreLib import AgentArray`` gives the class, not the context view.

        Reforged's ``__init__.py:101`` does ``from .AgentArray import *``, and the *context*
        accessor is reached as ``GWContext.AgentArray`` (``Context.py:54``). This port keeps that
        split: the package name is this class, the context view is ``py4gw.context.AgentArray``.
        """

        from py4gw.context.agent_array import AgentArray as context_view

        self.assertIs(py4gw.AgentArray, AgentArray)
        self.assertIsNot(py4gw.AgentArray, context_view)
        self.assertIs(py4gw.context.AgentArray, context_view)


class _StubContext:
    """A context *view* that records which member was asked for."""

    def __init__(self) -> None:
        self.asked: list[str] = []

    def __getattr__(self, name: str):
        def getter(*args, **kwargs):
            self.asked.append(name)
            return {"GetAgentByID": None}.get(name, [name])

        return getter


class _StubFacade:
    """The client's array facade: its ``get_context`` is the source's own route to the view."""

    def __init__(self, view: _StubContext) -> None:
        self.view = view
        self.context_asked = 0

    def get_context(self) -> _StubContext:
        self.context_asked += 1
        return self.view


class AgentArrayRouteTests(unittest.TestCase):
    """The getters and ``GetAgentByID`` ask the view the source's second route names."""

    def setUp(self) -> None:
        self.context = _StubContext()
        self.facade = _StubFacade(self.context)
        client = mock.Mock()
        client.agent_array = self.facade
        self._patch = mock.patch("py4gw.client.require_client", return_value=client)
        self._patch.start()
        self.addCleanup(self._patch.stop)

    def test_every_getter_answers_from_the_context_view(self) -> None:
        for member, route in GETTER_ROUTES.items():
            with self.subTest(member=member):
                self.context.asked.clear()
                self.facade.context_asked = 0
                argument = 7 if member == "GetAgentByID" else None
                result = (
                    getattr(AgentArray, member)(argument)
                    if argument is not None
                    else getattr(AgentArray, member)()
                )
                self.assertEqual(
                    self.facade.context_asked,
                    1,
                    "the member must reach the view through get_context(), which is the route "
                    "AgentArray.py's own second path names",
                )
                self.assertEqual(self.context.asked, [route])
                if member == "GetAgentByID":
                    self.assertIsNone(result)
                else:
                    self.assertEqual(result, [route])


class AgentArrayHelperTests(unittest.TestCase):
    """The source's pure helpers, exercised through this port."""

    def test_manipulation_is_the_source_s_set_arithmetic(self) -> None:
        self.assertEqual(
            sorted(AgentArray.Manipulation.Merge([1, 2, 3], [3, 4])), [1, 2, 3, 4]
        )
        self.assertEqual(sorted(AgentArray.Manipulation.Subtract([1, 2, 3], [3])), [1, 2])
        self.assertEqual(sorted(AgentArray.Manipulation.Intersect([1, 2], [2, 3])), [2])

    def test_sort_by_condition_and_by_health(self) -> None:
        with mock.patch.object(
            agent_module.Agent, "GetHealth", staticmethod(lambda agent_id: [50, 10, 90][agent_id])
        ):
            self.assertEqual(
                AgentArray.Sort.ByHealth([0, 1, 2]), [1, 0, 2]
            )
            self.assertEqual(
                AgentArray.Sort.ByHealth([0, 1, 2], descending=True), [2, 0, 1]
            )
            self.assertEqual(
                AgentArray.Sort.ByAttribute([0, 1, 2], "GetHealth"), [1, 0, 2]
            )

    def test_sort_and_filter_by_distance(self) -> None:
        positions = {0: (0.0, 0.0), 1: (100.0, 0.0), 2: (10.0, 0.0)}
        with mock.patch.object(
            agent_module.Agent,
            "GetXY",
            staticmethod(lambda agent_id: positions[agent_id]),
        ):
            self.assertEqual(
                AgentArray.Sort.ByDistance([0, 1, 2], (0.0, 0.0)), [0, 2, 1]
            )
            self.assertEqual(
                AgentArray.Filter.ByDistance([0, 1, 2], (0.0, 0.0), 50.0), [0, 2]
            )
            self.assertEqual(
                AgentArray.Filter.ByDistance([0, 1, 2], (0.0, 0.0), 50.0, negate=True), [1]
            )

    def test_filter_by_attribute_uses_the_source_s_negation(self) -> None:
        with mock.patch.object(
            agent_module.Agent, "IsMoving", staticmethod(lambda agent_id: agent_id == 1)
        ):
            self.assertEqual(AgentArray.Filter.ByAttribute([0, 1, 2], "IsMoving"), [1])
            self.assertEqual(
                AgentArray.Filter.ByAttribute([0, 1, 2], "IsMoving", negate=True), [0, 2]
            )

    def test_the_routines_find_the_largest_cluster_s_centre(self) -> None:
        positions = {
            1: (0.0, 0.0),
            2: (1.0, 0.0),
            3: (0.0, 1.0),
            4: (500.0, 500.0),
        }
        with mock.patch.object(
            agent_module.Agent,
            "GetXY",
            staticmethod(lambda agent_id: positions[agent_id]),
        ):
            self.assertEqual(
                AgentArray.Routines.DetectLargestAgentCluster([1, 2, 3, 4], 5.0), 1
            )
        self.assertEqual(AgentArray.Routines.DetectLargestAgentCluster([], 5.0), 0)


if __name__ == "__main__":
    unittest.main()
