"""Offline tests for the two dependencies `Map.Pathing` needed.

`Map.Pathing` reaches three classes that are not its own, and this file is their gate:

* **``py4gw/native_src/methods/ffna_map_methods.py``** — the port of Reforged's ``native_src/methods/FfnaMapMethods.py``,
  the ``gw.dat`` FFNA reader the offline pathing branch calls. Its two things are checked against
  the source itself: the whole top-level surface name for name, and its **404-entry**
  ``_MAP_ID_TO_DAT_FILE_ID`` table **value for value**. The parsers are then driven on synthetic
  FFNA bytes, so the chunk walk, the trapezoid unpack, the spawn groups and the ``PathingMap``
  builder are all exercised without a client.
* **``py4gw/routines_src/Checks.py``** — the ``Checks.Map`` namespace ``GetPathingMaps`` guards on.
  Its member list is compared against the source's own ``class Map`` body.
* **``py4gw/pathing.py``** — the navmesh half of Reforged's ``Pathing.py``: ``AABB``,
  ``TrapezoidBSP``, ``NavMesh`` and ``AutoPathing``. Every one is pure geometry over
  ``MapContext``'s own ``PathingTrapezoid`` records, so plain trapezoid fixtures drive them.
"""

from __future__ import annotations

import ast
import math
import struct
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

from py4gw.context.map_context import Node, PathingMap, PathingTrapezoid
from py4gw.native_src.methods.ffna_map_methods import (
    CHUNK_TYPE_SPAWN,
    CHUNK_TYPE_TRAPEZOID,
    FFNA_MAGIC,
    FFNASpawnData,
    FFNAPlaneData,
    FfnaMapMethods,
    _MAP_ID_TO_DAT_FILE_ID,
    _build_pathing_maps,
    _parse_chunks,
    is_ffna_pathing,
    parse_ffna_spawns,
)
from py4gw.pathing import (
    AABB,
    FIND_PATH_RANGE,
    MAX_PATH_POINTS,
    PATHING_ARGUMENTS_OFFSET,
    PATHING_ARRAY_OFFSET,
    PATHING_COUNT_OFFSET,
    PATHING_GOAL_OFFSET,
    PATHING_START_OFFSET,
    AStar,
    AStarNode,
    AutoPathing,
    NavMesh,
    PathPlanner,
    PathStatus,
    TrapezoidBSP,
    chaikin_smooth_path,
    densify_path2d,
)
from py4gw.routines_src.Checks import Checks

REFORGED_METHODS = Path(
    r"C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib\native_src\methods\FfnaMapMethods.py"
)
REFORGED_CHECKS = Path(r"C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib\routines_src\Checks.py")
REFORGED_PATHING = Path(r"C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib\Pathing.py")
PORT_DIR = Path(__file__).resolve().parent.parent.joinpath("py4gw")


def _trap(tid: int, *, yt=100.0, yb=0.0, xtl=0.0, xtr=100.0, xbl=0.0, xbr=100.0,
          neighbors=()) -> PathingTrapezoid:
    return PathingTrapezoid(
        id=tid, portal_left=0, portal_right=0,
        XTL=xtl, XTR=xtr, YT=yt, XBL=xbl, XBR=xbr, YB=yb,
        neighbor_ids=list(neighbors),
    )


def _ffna(chunks: list[tuple[int, bytes]]) -> bytes:
    """One FFNA type-3 file: 4-byte magic, 1-byte type, then the chunks."""
    out = struct.pack("<I", FFNA_MAGIC) + bytes((3,))
    for chunk_type, payload in chunks:
        out += struct.pack("<ii", chunk_type, len(payload)) + payload
    return out


class FfnaSurfaceTests(unittest.TestCase):
    """The port is the source's module, name for name and entry for entry."""

    def test_the_top_level_surface_is_the_sources(self) -> None:
        if not REFORGED_METHODS.is_file():
            self.skipTest(f"Reforged's FfnaMapMethods.py is not at {REFORGED_METHODS}")

        def surface(path: Path) -> list[str]:
            names: list[str] = []
            for node in ast.parse(path.read_text(encoding="utf-8")).body:
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    names.append(node.name)
                elif isinstance(node, ast.Assign):
                    names.extend(
                        target.id for target in node.targets if isinstance(target, ast.Name)
                    )
            return names

        source = surface(REFORGED_METHODS)
        port = surface(PORT_DIR.joinpath("native_src/methods/ffna_map_methods.py"))
        self.assertEqual(port, source)

    def test_the_map_id_table_is_the_sources_own(self) -> None:
        """404 entries, and every value identical to the source's."""

        if not REFORGED_METHODS.is_file():
            self.skipTest(f"Reforged's FfnaMapMethods.py is not at {REFORGED_METHODS}")

        source: dict[int, int] = {}
        for node in ast.parse(REFORGED_METHODS.read_text(encoding="utf-8")).body:
            if isinstance(node, ast.Assign) and any(
                getattr(t, "id", "") == "_MAP_ID_TO_DAT_FILE_ID" for t in node.targets
            ):
                source = ast.literal_eval(node.value)

        self.assertEqual(len(source), 404)
        self.assertEqual(dict(_MAP_ID_TO_DAT_FILE_ID), source)
        self.assertEqual(FfnaMapMethods.GetAvailableMapIds(), set(source))
        self.assertTrue(FfnaMapMethods.HasDatEntry(639))
        self.assertFalse(FfnaMapMethods.HasDatEntry(1))


class FfnaParserTests(unittest.TestCase):
    """The parsers, on synthetic FFNA bytes."""

    def test_is_ffna_pathing_needs_the_magic_and_type_three(self) -> None:
        self.assertFalse(is_ffna_pathing(b""))
        self.assertFalse(is_ffna_pathing(struct.pack("<I", FFNA_MAGIC)))
        self.assertFalse(is_ffna_pathing(struct.pack("<IB", FFNA_MAGIC, 2)))
        self.assertTrue(is_ffna_pathing(struct.pack("<IB", FFNA_MAGIC, 3)))

    def test_parse_chunks_walks_the_chunk_list(self) -> None:
        data = _ffna([(0x20000008, b"abcd"), (0x20000007, b"xy")])
        chunks = _parse_chunks(data)
        self.assertEqual([c[0] for c in chunks], [0x20000008, 0x20000007])
        self.assertEqual([c[2] for c in chunks], [b"abcd", b"xy"])

    def test_parse_chunks_stops_on_a_length_that_overruns(self) -> None:
        data = struct.pack("<IB", FFNA_MAGIC, 3) + struct.pack("<ii", 1, 9999)
        self.assertEqual(_parse_chunks(data), [])

    def test_spawn_groups_are_tagged_twice_then_floats(self) -> None:
        """The source's own layout: 29-byte header, then 13-byte, 13-byte, 8-byte entries."""

        header = bytes(29)
        tagged = struct.pack("<H", 1) + struct.pack("<iiBI", 100, -200, 0, 0x41424344)
        tagged += struct.pack("<H", 0)          # the second group is empty
        floats = struct.pack("<H", 2) + struct.pack("<ff", 1.5, 2.5) + struct.pack("<ff", 3.5, 4.5)
        chunk = header + tagged + floats
        data = _ffna([(CHUNK_TYPE_SPAWN, chunk)])

        parsed = parse_ffna_spawns(data)
        self.assertIsInstance(parsed, FFNASpawnData)
        assert parsed is not None
        self.assertEqual(len(parsed.spawns1), 1)
        self.assertEqual(parsed.spawns1[0].x, 100.0)
        self.assertEqual(parsed.spawns1[0].y, -200.0)
        self.assertEqual(parsed.spawns1[0].tag, "ABCD")
        self.assertEqual(parsed.spawns2, [])
        self.assertEqual([(s.x, s.y) for s in parsed.spawns3], [(1.5, 2.5), (3.5, 4.5)])

    def test_spawns_answer_none_for_a_file_with_no_spawn_chunk(self) -> None:
        self.assertIsNone(parse_ffna_spawns(_ffna([(CHUNK_TYPE_TRAPEZOID, bytes(32))])))

    def test_build_pathing_maps_offsets_ids_per_plane(self) -> None:
        """Two planes of two trapezoids: the second plane's ids start where the first's ended."""

        from py4gw.native_src.methods.ffna_map_methods import GWPathingTrapezoid

        def gw(adj=(0, -1, -1, -1)) -> GWPathingTrapezoid:
            return GWPathingTrapezoid(
                adjacent1=adj[0], adjacent2=adj[1], adjacent3=adj[2], adjacent4=adj[3],
                transition1=0, transition2=0,
                yt=100.0, yb=0.0, xtl=0.0, xtr=100.0, xbl=0.0, xbr=100.0,
            )

        planes = [FFNAPlaneData(trapezoids=[gw(), gw()]), FFNAPlaneData(trapezoids=[gw()])]
        maps = _build_pathing_maps(planes)

        self.assertEqual(len(maps), 2)
        self.assertIsInstance(maps[0], PathingMap)
        self.assertEqual([t.id for t in maps[0].trapezoids], [0, 1])
        self.assertEqual([t.id for t in maps[1].trapezoids], [2])
        # ``a >= 0`` is the source's own filter; -1 entries drop out.
        self.assertEqual(maps[0].trapezoids[0].neighbor_ids, [0])
        self.assertEqual(maps[1].trapezoids[0].neighbor_ids, [2])
        self.assertEqual(maps[0].zplane, 0)
        self.assertEqual(maps[1].zplane, 1)
        self.assertEqual(maps[0].root_node_id, 0xFFFFFFFF)


class ChecksMapTests(unittest.TestCase):
    """`Checks.Map` is the source's namespace, member for member."""

    def test_the_map_namespace_matches_the_source(self) -> None:
        if not REFORGED_CHECKS.is_file():
            self.skipTest(f"Reforged's Checks.py is not at {REFORGED_CHECKS}")

        tree = ast.parse(REFORGED_CHECKS.read_text(encoding="utf-8"))
        checks = next(
            n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Checks"
        )
        source_map = next(
            n for n in checks.body if isinstance(n, ast.ClassDef) and n.name == "Map"
        )
        expected = [
            m.name for m in source_map.body if isinstance(m, ast.FunctionDef)
        ]
        actual = [
            n
            for n in vars(Checks.Map)
            if not n.startswith("_") and callable(getattr(Checks.Map, n))
        ]
        self.assertEqual(actual, expected)

    def test_the_gate_answers_without_a_client(self) -> None:
        """No client is no map: `MapValid` is False and `IsLoading` is True, as the source says."""

        self.assertFalse(Checks.Map.MapValid())
        self.assertTrue(Checks.Map.IsLoading())
        self.assertFalse(Checks.Map.IsExplorable())
        self.assertFalse(Checks.Map.IsOutpost())
        self.assertFalse(Checks.Map.IsInCinematic())
        self.assertFalse(Checks.Map.IsCombatReady())
        self.assertFalse(Checks.Map.IsMapReady())


class NavMeshGeometryTests(unittest.TestCase):
    """The BSP and the navmesh, on plain trapezoids."""

    def test_bsp_finds_the_trapezoid_containing_a_point(self) -> None:
        traps = [
            _trap(0, yb=0.0, yt=100.0, xbl=0.0, xbr=100.0, xtl=0.0, xtr=100.0),
            _trap(1, yb=100.0, yt=200.0, xbl=0.0, xbr=100.0, xtl=0.0, xtr=100.0),
        ]
        bsp = TrapezoidBSP(traps)
        self.assertEqual(bsp.find(50.0, 50.0), 0)
        self.assertEqual(bsp.find(50.0, 150.0), 1)
        self.assertIsNone(bsp.find(500.0, 500.0))
        self.assertTrue(bsp.find_with_margin(50.0, 50.0, 10.0))
        self.assertFalse(bsp.find_with_margin(2.0, 50.0, 10.0))

    def test_an_empty_bsp_answers_nothing(self) -> None:
        bsp = TrapezoidBSP([])
        self.assertIsNone(bsp.find(0.0, 0.0))
        self.assertFalse(bsp.find_with_margin(0.0, 0.0, 1.0))

    def test_aabb_covers_the_trapezoids_own_corners(self) -> None:
        box = AABB(_trap(0, yb=10.0, yt=90.0, xbl=5.0, xbr=95.0, xtl=15.0, xtr=85.0))
        self.assertEqual(box.m_min, (5.0, 10.0))
        self.assertEqual(box.m_max, (95.0, 90.0))

    def test_navmesh_links_neighbours_that_share_an_edge(self) -> None:
        """`neighbor_ids` plus a shared edge is what `create_all_local_portals` needs."""

        lower = _trap(0, yb=0.0, yt=100.0, xbl=0.0, xbr=100.0, xtl=0.0, xtr=100.0,
                      neighbors=(1,))
        upper = _trap(1, yb=100.0, yt=200.0, xbl=0.0, xbr=100.0, xtl=0.0, xtr=100.0,
                      neighbors=(0,))
        layer = PathingMap(
            zplane=0, h0004=0, h0008=0, h000C=0, h0010=0,
            trapezoid_count=2, sink_node_count=0, x_node_count=0, y_node_count=0,
            portal_count=0, trapezoids=[lower, upper],
            sink_nodes=[], x_nodes=[], y_nodes=[], portals=[],
            h0034=0, h0038=0, root_node=Node(type=0, id=0), root_node_id=0xFFFFFFFF,
            h0048=None, h004C=None, h0050=None,
        )
        nav = NavMesh([layer], 639)

        self.assertEqual(sorted(nav.trapezoids), [0, 1])
        # The source's own shape, pinned: ``create_all_local_portals`` walks every trap and every
        # one of its neighbours, so a pair that names each other is linked from both ends and the
        # adjacency list carries the entry twice. No dedup is added here — that would be a check
        # the source does not make.
        self.assertEqual(nav.get_neighbors(0), [1, 1])
        self.assertEqual(nav.get_neighbors(1), [0, 0])
        self.assertEqual(nav.find_trapezoid_id_by_coord((50.0, 50.0)), 0)
        self.assertTrue(nav.contains(50.0, 50.0, 10.0))
        self.assertAlmostEqual(nav.get_transition_cost(0, 1), 100.0, places=3)
        self.assertEqual(nav.get_position(0), (50.0, 50.0))

    def test_navmesh_find_nearest_reachable_answers_the_centroid(self) -> None:
        layer = PathingMap(
            zplane=0, h0004=0, h0008=0, h000C=0, h0010=0,
            trapezoid_count=1, sink_node_count=0, x_node_count=0, y_node_count=0,
            portal_count=0,
            trapezoids=[_trap(0, yb=0.0, yt=100.0, xbl=0.0, xbr=100.0, xtl=0.0, xtr=100.0)],
            sink_nodes=[], x_nodes=[], y_nodes=[], portals=[],
            h0034=0, h0038=0, root_node=Node(type=0, id=0), root_node_id=0xFFFFFFFF,
            h0048=None, h004C=None, h0050=None,
        )
        nav = NavMesh([layer], 639)
        self.assertEqual(nav.find_nearest_reachable((50.0, 50.0)), (50.0, 50.0))
        self.assertEqual(nav.find_nearest_reachable((900.0, 900.0)), (50.0, 50.0))

    def test_auto_pathing_is_a_singleton_and_reports_no_map(self) -> None:
        self.assertIs(AutoPathing(), AutoPathing())
        self.assertIsNone(AutoPathing().get_navmesh())
        AutoPathing().clear_navmesh_cache()
        AutoPathing().clear_navmesh_cache(639)
        # The generator yields once on its own early return when no map is ready, which is the
        # source's body (``Pathing.py:719-723``).
        self.assertEqual(list(AutoPathing().force_reload_navmesh()), [None])


class AStarTests(unittest.TestCase):
    """`AStar`/`AStarNode` over a stand-in navmesh: the source's own walk, and the source's own edges.

    The navmesh is the port's real class where it matters (``NavMesh`` is what `smooth_path_by_los`
    lives on), but the search itself only asks it five things — ``get_position``,
    ``find_trapezoid_id_by_coord``, ``find_nearest_trapezoid_id``, ``get_neighbors`` and
    ``get_transition_cost`` — so the stand-in answers exactly those and the test stays about the
    algorithm.
    """

    class _Nav:
        """A four-trapezoid corridor: 0 -> 1 -> 2 -> 3, with positions on a line."""

        def __init__(self) -> None:
            self.positions = {0: (0.0, 0.0), 1: (100.0, 0.0), 2: (200.0, 0.0), 3: (300.0, 0.0)}
            self.neighbors = {0: [1], 1: [0, 2], 2: [1, 3], 3: [2]}

        def get_position(self, node_id: int) -> tuple[float, float]:
            return self.positions[node_id]

        def find_trapezoid_id_by_coord(self, pos: tuple[float, float]) -> int | None:
            for node_id, (x, y) in self.positions.items():
                if abs(pos[0] - x) < 1.0 and abs(pos[1] - y) < 1.0:
                    return node_id
            return None

        def find_nearest_trapezoid_id(self, x: float, y: float) -> int | None:
            return min(self.positions, key=lambda n: abs(self.positions[n][0] - x))

        def get_neighbors(self, node_id: int) -> list[int]:
            return list(self.neighbors[node_id])

        def get_transition_cost(self, a: int, b: int) -> float:
            ax, ay = self.positions[a]
            bx, by = self.positions[b]
            return math.hypot(bx - ax, by - ay)

    def test_a_node_orders_by_f(self) -> None:
        """`AStarNode.__lt__` is the heap's whole ordering, so it is pinned directly."""

        self.assertLess(AStarNode(1, 0, 1.0), AStarNode(2, 0, 2.0))
        self.assertFalse(AStarNode(2, 0, 2.0) < AStarNode(1, 0, 1.0))

    def test_the_search_walks_to_the_goal_and_brackets_exact_endpoints(self) -> None:
        """A path found is the reconstructed centroids, with the caller's exact ends inserted.

        **The source inserts them unconditionally**, and `_reconstruct` already ends at both
        trapezoids' centroids — so when the caller's own points *are* those centroids (the ordinary
        case: the start is where the player stands, the goal is the target) the two ends appear twice.
        That is the source's behaviour and this port reproduces it; `AutoPathing.get_path` is the
        member that deals with it, guarding its own prepend with the 750-unit test in `_prepend_start`.
        """

        nav = self._Nav()
        astar = AStar(nav)  # type: ignore[arg-type]

        self.assertTrue(astar.search((0.0, 0.0), (300.0, 0.0)))
        self.assertEqual(
            astar.get_path(),
            [
                (0.0, 0.0),
                (0.0, 0.0),
                (100.0, 0.0),
                (200.0, 0.0),
                (300.0, 0.0),
                (300.0, 0.0),
            ],
            "start_pos and goal_pos are inserted at the front and the back, unconditionally",
        )

    def test_offsets_that_are_not_centroids_are_the_ends(self) -> None:
        """With endpoints off the centroids, the inserted points are exactly the caller's."""

        nav = self._Nav()
        astar = AStar(nav)  # type: ignore[arg-type]

        self.assertTrue(astar.search((0.0, 0.0), (280.0, 0.0)))
        path = astar.get_path()
        self.assertEqual(path[0], (0.0, 0.0))
        self.assertEqual(path[-1], (280.0, 0.0))
        self.assertIn((200.0, 0.0), path, "the corridor's own centroids are the body of the path")

    def test_a_missing_trapezoid_is_recovered_by_the_nearest_lookup(self) -> None:
        """The source's own recovery: an off-mesh start/goal is snapped to the nearest trapezoid."""

        nav = self._Nav()
        astar = AStar(nav)  # type: ignore[arg-type]

        self.assertTrue(astar.search((0.4, 0.4), (300.4, 0.4)))
        self.assertEqual(astar.get_path()[0], (0.4, 0.4))
        self.assertEqual(astar.get_path()[-1], (300.4, 0.4))

    def test_no_route_answers_false_and_leaves_no_path(self) -> None:
        """A disconnected goal is the source's `return False`, with nothing appended to the path."""

        nav = self._Nav()
        nav.neighbors[2] = [1]  # cut the corridor between 2 and 3
        astar = AStar(nav)  # type: ignore[arg-type]

        self.assertFalse(astar.search((0.0, 0.0), (300.0, 0.0)))
        self.assertEqual(astar.get_path(), [])

    def test_an_unreachable_goal_trapezoid_answers_false_immediately(self) -> None:
        """With neither endpoint resolvable the source returns before touching the heap."""

        class _Nothing(self._Nav):
            def find_trapezoid_id_by_coord(self, pos: tuple[float, float]) -> int | None:
                return None

            def find_nearest_trapezoid_id(self, x: float, y: float) -> int | None:
                return None

        astar = AStar(_Nothing())  # type: ignore[arg-type]

        self.assertFalse(astar.search((0.0, 0.0), (300.0, 0.0)))
        self.assertEqual(astar.get_path(), [])


class PathSmoothingTests(unittest.TestCase):
    """`chaikin_smooth_path` and `densify_path2d`: the source's arithmetic, value for value."""

    def test_chaikin_keeps_the_ends_and_moves_the_middle_to_the_quarter_points(self) -> None:
        """One iteration of the source's 0.75/0.25 rule, computed by hand here."""

        smoothed = chaikin_smooth_path([(0.0, 0.0), (100.0, 0.0), (200.0, 0.0)], 1)

        self.assertEqual(
            smoothed,
            [
                (0.0, 0.0),
                (25.0, 0.0),
                (75.0, 0.0),
                (125.0, 0.0),
                (175.0, 0.0),
                (200.0, 0.0),
            ],
        )

    def test_chaikin_with_a_flat_segment_is_idempotent(self) -> None:
        """Two points have one segment, so every point it produces lands on the same line."""

        self.assertEqual(
            chaikin_smooth_path([(0.0, 0.0), (10.0, 0.0)], 2),
            [
                (0.0, 0.0),
                (0.625, 0.0),
                (1.875, 0.0),
                (3.75, 0.0),
                (6.25, 0.0),
                (8.125, 0.0),
                (9.375, 0.0),
                (10.0, 0.0),
            ],
            "the second iteration smooths the first iteration's own points",
        )

    def test_densify_splits_a_long_segment_at_the_threshold(self) -> None:
        """A 1000-unit hop at threshold 500 becomes two 500-unit steps, keeping the endpoint."""

        dense = densify_path2d([(0.0, 0.0), (1000.0, 0.0)], 500.0)

        self.assertEqual(dense, [(0.0, 0.0), (500.0, 0.0), (1000.0, 0.0)])

    def test_densify_leaves_short_segments_and_small_inputs_alone(self) -> None:
        """The source's two early returns: a non-positive threshold, and a path of one point."""

        self.assertEqual(densify_path2d([(0.0, 0.0), (400.0, 0.0)], 500.0), [(0.0, 0.0), (400.0, 0.0)])
        self.assertEqual(densify_path2d([(0.0, 0.0), (1000.0, 0.0)], 0.0), [(0.0, 0.0), (1000.0, 0.0)])
        self.assertEqual(densify_path2d([(7.0, 7.0)], 500.0), [(7.0, 7.0)])

    def test_densify_measures_from_the_last_point_it_emitted(self) -> None:
        """The source reads ``out[-1]`` — the point just appended — not the original previous point."""

        dense = densify_path2d([(0.0, 0.0), (2000.0, 0.0)], 500.0)

        self.assertEqual(
            dense,
            [(0.0, 0.0), (500.0, 0.0), (1000.0, 0.0), (1500.0, 0.0), (2000.0, 0.0)],
        )


class _FakeBridge:
    """The block's data region, as bytes, with the same bounds rule the real bridge enforces."""

    def __init__(self, size: int) -> None:
        self.memory = bytearray(size)
        self.writes: list[tuple[int, bytes]] = []

    def data_address(self, offset: int, size: int = 0) -> int:
        if offset < 0 or size < 0 or offset + size > len(self.memory):
            raise ValueError(f"data span {offset}..{offset + size} does not fit")
        return 0x100000 + offset

    def write_data(self, offset: int, payload: bytes) -> int:
        address = self.data_address(offset, len(payload))
        self.memory[offset : offset + len(payload)] = payload
        self.writes.append((offset, bytes(payload)))
        return address

    def read_data(self, offset: int, size: int) -> bytes:
        return bytes(self.memory[offset : offset + size])


class _FakeClient:
    """A client whose only jobs are answering ``resolves`` and being called."""

    def __init__(self, bridge: _FakeBridge, resolves: bool = True) -> None:
        self.bridge = bridge
        self._resolves = resolves
        self.calls: list[tuple[str, int, tuple[int, ...]]] = []
        self.on_call: Any = None

    def resolves(self, name: str) -> bool:
        return self._resolves

    def call_function(self, name: str, form: Any, *args: int) -> None:
        self.calls.append((name, int(form), tuple(int(a) for a in args)))
        if self.on_call is not None:
            self.on_call()


class PathPlannerTests(unittest.TestCase):
    """The `PyPathing` surface over the client's own finder: the call, and the two answers."""

    def _client(self, points: list[tuple[float, float, int]], resolves: bool = True):
        from py4gw.game_thread.shared_block import DATA_SIZE

        bridge = _FakeBridge(DATA_SIZE)
        client = _FakeClient(bridge, resolves)

        def on_call() -> None:
            payload = b"".join(
                struct.pack("<ffI", x, y, z) + b"\x00\x00\x00\x00" for x, y, z in points
            )
            bridge.memory[PATHING_ARRAY_OFFSET : PATHING_ARRAY_OFFSET + len(payload)] = payload
            bridge.memory[PATHING_COUNT_OFFSET : PATHING_COUNT_OFFSET + 4] = struct.pack(
                "<I", len(points)
            )

        client.on_call = on_call
        return client, bridge

    def _patched(self, client: _FakeClient):
        patch = mock.patch("py4gw.client._current_client", client)
        patch.start()
        self.addCleanup(patch.stop)
        return client

    def test_the_status_enum_is_the_bindings(self) -> None:
        """``pathing_bindings.cpp:10-15``: Idle, Pending, Ready, Failed, in that order."""

        self.assertEqual(
            [(status.name, int(status)) for status in PathStatus],
            [("Idle", 0), ("Pending", 1), ("Ready", 2), ("Failed", 3)],
        )

    def test_the_planner_surface_is_the_bindings(self) -> None:
        """Every ``.def`` the binding declares, in the binding's own order."""

        declared = [
            name
            for name in vars(PathPlanner)
            if not name.startswith("__") and callable(getattr(PathPlanner, name))
        ]
        self.assertEqual(
            declared,
            [
                "plan",
                "compute_immediate",
                "get_status",
                "is_ready",
                "was_successful",
                "get_path",
                "reset",
                "_find",
            ],
            "the binding's .def order, plus the port's own private call helper at the end",
        )

    def test_the_six_argument_words_are_the_endpoints_and_the_array(self) -> None:
        """The call native makes: two endpoint pointers, the range's bits, the capacity, count, array."""

        from py4gw.game_thread.shared_block import CallForm, float_bits

        client, bridge = self._client([(10.0, 20.0, 0)])
        self._patched(client)
        planner = PathPlanner()

        planner.plan(start_x=1.5, start_y=-2.5, start_z=3, goal_x=4.5, goal_y=5.5, goal_z=6)

        self.assertEqual(
            client.calls,
            [
                (
                    "pathing.find_path_func",
                    int(CallForm.STACK_WORDS),
                    (PATHING_ARGUMENTS_OFFSET, 6),
                )
            ],
            "one call, the source's form, and the six words it pushes",
        )
        self.assertEqual(
            struct.unpack(
                "<ffI",
                bridge.read_data(PATHING_START_OFFSET, 12),
            ),
            (1.5, -2.5, 3),
            "the start record is the caller's own three words",
        )
        self.assertEqual(
            struct.unpack("<ffI", bridge.read_data(PATHING_GOAL_OFFSET, 12)),
            (4.5, 5.5, 6),
        )
        first, second, third, fourth, fifth, sixth = struct.unpack(
            "<6I", bridge.read_data(PATHING_ARGUMENTS_OFFSET, 24)
        )
        self.assertEqual(first, 0x100000 + PATHING_START_OFFSET)
        self.assertEqual(second, 0x100000 + PATHING_GOAL_OFFSET)
        self.assertEqual(third, float_bits(FIND_PATH_RANGE))
        self.assertEqual(
            struct.unpack("<f", struct.pack("<I", third))[0],
            10000.0,
            "the range is native's own 10000.0f, as its bit pattern",
        )
        self.assertEqual(fourth, MAX_PATH_POINTS)
        self.assertEqual(fifth, 0x100000 + PATHING_COUNT_OFFSET)
        self.assertEqual(sixth, 0x100000 + PATHING_ARRAY_OFFSET)

    def test_the_count_word_is_cleared_before_the_call(self) -> None:
        """Native declares a fresh local; the block is not fresh, so the count is zeroed first."""

        client, bridge = self._client([])
        self._patched(client)

        PathPlanner().plan(0.0, 0.0, 0.0, 1.0, 1.0, 0.0)

        self.assertEqual(
            bridge.writes[2],
            (PATHING_COUNT_OFFSET, b"\x00\x00\x00\x00"),
            "after the two records comes the count word",
        )

    def test_a_path_answers_ready_with_the_clients_points(self) -> None:
        """The records the client filled come back as ``(x, y, float(zplane))`` triples."""

        client, _ = self._client([(10.0, 20.0, 0), (30.0, 40.0, 7)])
        self._patched(client)
        planner = PathPlanner()

        planner.plan(10.0, 20.0, 0, 30.0, 40.0, 7)

        self.assertEqual(planner.get_status(), PathStatus.Ready)
        self.assertTrue(planner.is_ready())
        self.assertTrue(planner.was_successful())
        self.assertEqual(planner.get_path(), [(10.0, 20.0, 0.0), (30.0, 40.0, 7.0)])

    def test_no_points_is_failed(self) -> None:
        """``pathCount == 0`` is the source's first failure (``pathing.cpp:41``)."""

        client, _ = self._client([])
        self._patched(client)
        planner = PathPlanner()

        planner.plan(1.0, 2.0, 0, 3.0, 4.0, 0)

        self.assertEqual(planner.get_status(), PathStatus.Failed)
        self.assertFalse(planner.was_successful())
        self.assertEqual(planner.get_path(), [])

    def test_one_point_that_is_not_the_goal_is_failed(self) -> None:
        """The source's second failure: a single point that is not where the caller asked to go."""

        client, _ = self._client([(1.0, 2.0, 0)])
        self._patched(client)
        planner = PathPlanner()

        planner.plan(1.0, 2.0, 0, 3.0, 4.0, 0)

        self.assertEqual(planner.get_status(), PathStatus.Failed)

    def test_one_point_that_is_the_goal_is_ready(self) -> None:
        """…and one point that *is* the goal is a success, which is the source's own exception."""

        client, _ = self._client([(3.0, 4.0, 0)])
        self._patched(client)
        planner = PathPlanner()

        planner.plan(1.0, 2.0, 0, 3.0, 4.0, 0)

        self.assertEqual(planner.get_status(), PathStatus.Ready)
        self.assertEqual(planner.get_path(), [(3.0, 4.0, 0.0)])

    def test_an_unresolved_finder_fails_without_calling(self) -> None:
        """The port asks the catalog the question native asks its function pointer."""

        client, bridge = self._client([(1.0, 1.0, 0)], resolves=False)
        self._patched(client)
        planner = PathPlanner()

        planner.plan(0.0, 0.0, 0.0, 1.0, 1.0, 0.0)

        self.assertEqual(client.calls, [])
        self.assertEqual(bridge.writes, [])
        self.assertEqual(planner.get_status(), PathStatus.Failed)

    def test_compute_immediate_answers_the_list_and_leaves_the_path_field_alone(self) -> None:
        """Native's second member returns the vector; it does not touch ``planned_path``."""

        client, _ = self._client([(1.0, 1.0, 0), (2.0, 2.0, 0)])
        self._patched(client)
        planner = PathPlanner()

        self.assertEqual(
            planner.compute_immediate(1.0, 1.0, 0, 2.0, 2.0, 0),
            [(1.0, 1.0, 0.0), (2.0, 2.0, 0.0)],
        )
        self.assertEqual(planner.get_path(), [], "planned_path is only PlanPath's")

    def test_reset_returns_the_planner_to_idle(self) -> None:
        """``Reset`` clears the path and the status, which is what ``get_path`` relies on."""

        client, _ = self._client([(1.0, 1.0, 0)])
        self._patched(client)
        planner = PathPlanner()
        planner.plan(1.0, 1.0, 0, 1.0, 1.0, 0)

        planner.reset()

        self.assertEqual(planner.get_status(), PathStatus.Idle)
        self.assertEqual(planner.get_path(), [])


class GetPathTests(unittest.TestCase):
    """`AutoPathing.get_path`/`get_path_to`: the planner first, the navmesh route second."""

    class _Nav:
        """Enough of a navmesh for the fallback: A* walks it and LOS smoothing passes it through."""

        def __init__(self) -> None:
            self.positions = {0: (0.0, 0.0), 1: (100.0, 0.0)}
            self.neighbors = {0: [1], 1: [0]}

        def get_position(self, node_id: int) -> tuple[float, float]:
            return self.positions[node_id]

        def find_trapezoid_id_by_coord(self, pos: tuple[float, float]) -> int | None:
            for node_id, (x, y) in self.positions.items():
                if abs(pos[0] - x) < 1.0 and abs(pos[1] - y) < 1.0:
                    return node_id
            return None

        def find_nearest_trapezoid_id(self, x: float, y: float) -> int | None:
            return min(self.positions, key=lambda n: abs(self.positions[n][0] - x))

        def get_neighbors(self, node_id: int) -> list[int]:
            return list(self.neighbors[node_id])

        def get_transition_cost(self, a: int, b: int) -> float:
            ax, ay = self.positions[a]
            bx, by = self.positions[b]
            return math.hypot(bx - ax, by - ay)

        def smooth_path_by_los(self, path, margin, step_dist):
            """The port's own member is patched in for `AutoPathing` tests elsewhere; here it is
            the identity, so the fallback's own steps are what the assertions see."""

            return path

    def _patches(self, *, map_id: int = 55, loading: bool = False,
                 points: list[tuple[float, float, int]] | None = None,
                 navmesh: Any = None):
        patches = [
            mock.patch("py4gw.map.Map.GetMapID", staticmethod(lambda: map_id)),
            mock.patch("py4gw.map.Map.IsMapLoading", staticmethod(lambda: loading)),
        ]
        if points is not None:
            planner_client, _ = PathPlannerTests()._client(points)
            patches.append(mock.patch("py4gw.client._current_client", planner_client))
        if navmesh is not None:
            patches.append(
                mock.patch.object(AutoPathing, "get_navmesh", lambda self: navmesh)
            )
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def test_the_planners_path_is_used_when_it_is_ready(self) -> None:
        """Ready short-circuits the navmesh route entirely, and the answer carries ``start[2]``."""

        self._patches(points=[(800.0, 0.0, 0), (900.0, 0.0, 0)])
        auto = AutoPathing()

        path = auto.get_path((0.0, 0.0, 4.0), (900.0, 0.0, 0.0))

        self.assertEqual(
            path,
            [
                (0.0, 0.0, 4.0),
                (500.0, 0.0, 4.0),
                (800.0, 0.0, 4.0),
                (900.0, 0.0, 4.0),
            ],
            "the caller's start is prepended (the planner's first point is 800 away), the 800-unit "
            "hop is densified into a 500-unit step, and every point carries the start's z",
        )

    def test_a_start_already_on_the_path_is_not_prepended(self) -> None:
        """``_prepend_start`` only inserts when the first point is more than 750 units away."""

        self._patches(points=[(100.0, 0.0, 0), (200.0, 0.0, 0)])
        auto = AutoPathing()

        path = auto.get_path((100.0, 0.0, 0.0), (200.0, 0.0, 0.0))

        self.assertEqual(path[0][:2], (100.0, 0.0), "the path's own first point, not a duplicate")

    def test_the_navmesh_route_answers_when_the_planner_fails(self) -> None:
        """The source's fallback: A* over the port's own navmesh, then the same shaping.

        The duplicated ends are `AStar`'s own quirk, kept as the source has it: ``search`` inserts the
        exact start and goal on top of a reconstruction that already ends at both trapezoids'
        centroids, and ``_prepend_start`` only guards the *front* of the list (and only beyond 750
        units), so a goal that coincides with a centroid appears twice.
        """

        self._patches(points=[], navmesh=self._Nav())
        auto = AutoPathing()

        path = auto.get_path((0.0, 0.0, 0.0), (100.0, 0.0, 0.0))

        self.assertEqual(
            path,
            [(0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (100.0, 0.0, 0.0), (100.0, 0.0, 0.0)],
        )

    def test_no_navmesh_and_nothing_to_load_answers_empty(self) -> None:
        """With no navmesh and no pathing maps to build one from, the answer is ``[]``."""

        self._patches(points=[])
        auto = AutoPathing()
        with mock.patch.object(AutoPathing, "get_navmesh", lambda self: None):
            with mock.patch.object(AutoPathing, "load_pathing_maps", lambda self: iter(())):
                self.assertEqual(auto.get_path((0.0, 0.0, 0.0), (1.0, 1.0, 0.0)), [])

    def test_a_loading_or_changed_map_aborts_cleanly(self) -> None:
        """The source's own abort: no map, a loading map, or a different map answers ``[]``."""

        auto = AutoPathing()
        self._patches(points=[(1.0, 1.0, 0)], map_id=0)
        self.assertEqual(auto.get_path((0.0, 0.0, 0.0), (1.0, 1.0, 0.0)), [])

        self._patches(points=[(1.0, 1.0, 0)], loading=True)
        self.assertEqual(auto.get_path((0.0, 0.0, 0.0), (1.0, 1.0, 0.0)), [])

    def test_get_path_to_starts_from_the_players_own_position(self) -> None:
        """`Player.GetAgent()`'s ``pos`` is the start; the answer is flat pairs."""

        self._patches(points=[(10.0, 20.0, 5), (30.0, 40.0, 5)])
        auto = AutoPathing()
        agent = mock.Mock()
        agent.pos.x = 10.0
        agent.pos.y = 20.0
        agent.pos.zplane = 5

        with mock.patch("py4gw.player.Player.GetAgent", staticmethod(lambda: agent)):
            path = auto.get_path_to(30.0, 40.0)

        self.assertEqual(path, [(10.0, 20.0), (30.0, 40.0)])

    def test_get_path_to_without_a_player_agent_answers_empty(self) -> None:
        """No agent is no start point, which is the source's own early return."""

        self._patches(points=[(1.0, 1.0, 0)])
        auto = AutoPathing()

        with mock.patch("py4gw.player.Player.GetAgent", staticmethod(lambda: None)):
            self.assertEqual(auto.get_path_to(1.0, 1.0), [])


class PathingSourceParityTests(unittest.TestCase):
    """`py4gw/pathing.py` carries the navmesh half's surface, name for name."""

    def test_the_two_injected_members_name_what_they_need(self) -> None:
        """Replaced with the members themselves: both answer, and neither is a generator.

        The old form of this test asserted that `get_path`/`get_path_to` raise `NotImplementedError`
        naming `PyPathing.PathPlanner`. They no longer raise — the planner is reachable through the
        client's own `find_path_func` — so the pin moved to what is still a divergence: **the source
        declares both members generators** (`Pathing.py:744`, `:837`, for the
        ``yield from Routines.Yield.wait(100)`` loop) **and this port declares both plain functions**,
        because the waits have nothing to wait for here. The source's own AST is read to prove the
        first half of that sentence rather than assert it from memory.
        """

        import inspect

        for name in ("get_path", "get_path_to"):
            with self.subTest(member=name):
                ported = getattr(AutoPathing, name)
                self.assertFalse(
                    inspect.isgeneratorfunction(ported),
                    "the recorded divergence: plain function, not a generator",
                )

        if REFORGED_PATHING.is_file():
            tree = ast.parse(REFORGED_PATHING.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == "AutoPathing":
                    for member in node.body:
                        if isinstance(member, ast.FunctionDef) and member.name in (
                            "get_path",
                            "get_path_to",
                        ):
                            with self.subTest(source_member=member.name):
                                self.assertTrue(
                                    any(
                                        isinstance(inner, (ast.Yield, ast.YieldFrom))
                                        for inner in ast.walk(member)
                                    ),
                                    "the source's member is a generator — that is why this port "
                                    "records the difference",
                                )

    def test_the_navmesh_surface_is_the_sources(self) -> None:
        if not REFORGED_PATHING.is_file():
            self.skipTest(f"Reforged's Pathing.py is not at {REFORGED_PATHING}")

        tree = ast.parse(REFORGED_PATHING.read_text(encoding="utf-8"))
        wanted = {"AABB", "TrapezoidBSP", "NavMesh", "AStarNode", "AStar", "AutoPathing"}
        source: dict[str, list[str]] = {}
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name in wanted:
                source[node.name] = [
                    m.name for m in node.body if isinstance(m, ast.FunctionDef)
                ]
        self.assertEqual(sorted(source), sorted(wanted))

        import py4gw.pathing as pathing_module

        def own_members(cls: type) -> list[str]:
            """The class's own functions, the source's own dunders included, in source order."""

            out: list[str] = []
            for name, value in vars(cls).items():
                if name.startswith("__") and name.endswith("__") and name not in (
                    "__init__",
                    "__new__",
                    "__lt__",
                ):
                    continue
                if callable(value) or isinstance(value, (staticmethod, classmethod)):
                    out.append(name)
            return out

        for name, members in source.items():
            with self.subTest(klass=name):
                ported = getattr(pathing_module, name)
                self.assertEqual(own_members(ported), members)

    def test_the_module_functions_are_the_sources(self) -> None:
        """The two module-level helpers the path walk needs are here, spelled as the source spells them."""

        if not REFORGED_PATHING.is_file():
            self.skipTest(f"Reforged's Pathing.py is not at {REFORGED_PATHING}")

        tree = ast.parse(REFORGED_PATHING.read_text(encoding="utf-8"))
        wanted = {"_point_in_trapezoid", "_build_trap_bsp", "chaikin_smooth_path", "densify_path2d"}
        source = [
            node.name
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name in wanted
        ]
        self.assertEqual(sorted(source), sorted(wanted))

        import py4gw.pathing as pathing_module

        for name in source:
            with self.subTest(function=name):
                helper = getattr(pathing_module, name)
                self.assertTrue(callable(helper))


if __name__ == "__main__":
    unittest.main(verbosity=2)
