"""Offline tests for the two dependencies `Map.Pathing` needed.

`Map.Pathing` reaches three classes that are not its own, and this file is their gate:

* **``py4gw/ffna_map_methods.py``** — the port of Reforged's ``native_src/methods/FfnaMapMethods.py``,
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
import struct
import unittest
from pathlib import Path

from py4gw.context.map_context import Node, PathingMap, PathingTrapezoid
from py4gw.ffna_map_methods import (
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
from py4gw.pathing import AABB, AutoPathing, NavMesh, TrapezoidBSP
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
        port = surface(PORT_DIR.joinpath("ffna_map_methods.py"))
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

        from py4gw.ffna_map_methods import GWPathingTrapezoid

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


class PathingSourceParityTests(unittest.TestCase):
    """`py4gw/pathing.py` carries the navmesh half's surface, name for name."""

    def test_the_two_injected_members_name_what_they_need(self) -> None:
        """`get_path`/`get_path_to` are the members the ruling leaves unbuilt, and they refuse."""

        for label, call in (
            ("get_path", lambda: AutoPathing().get_path((0.0, 0.0, 0.0), (1.0, 1.0, 0.0))),
            ("get_path_to", lambda: AutoPathing().get_path_to(0.0, 0.0)),
        ):
            with self.subTest(member=label):
                with self.assertRaises(NotImplementedError) as caught:
                    call()
                self.assertIn("PyPathing.PathPlanner", str(caught.exception))

    def test_the_navmesh_surface_is_the_sources(self) -> None:
        if not REFORGED_PATHING.is_file():
            self.skipTest(f"Reforged's Pathing.py is not at {REFORGED_PATHING}")

        tree = ast.parse(REFORGED_PATHING.read_text(encoding="utf-8"))
        wanted = {"AABB", "TrapezoidBSP", "NavMesh", "AutoPathing"}
        source: dict[str, list[str]] = {}
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name in wanted:
                source[node.name] = [
                    m.name for m in node.body if isinstance(m, ast.FunctionDef)
                ]
        self.assertEqual(sorted(source), sorted(wanted))

        import py4gw.pathing as pathing_module

        def own_members(cls: type) -> list[str]:
            """The class's own functions, ``__init__``/``__new__`` included, in source order."""

            out: list[str] = []
            for name, value in vars(cls).items():
                if name.startswith("__") and name.endswith("__") and name not in (
                    "__init__",
                    "__new__",
                ):
                    continue
                if callable(value) or isinstance(value, (staticmethod, classmethod)):
                    out.append(name)
            return out

        for name, members in source.items():
            with self.subTest(klass=name):
                ported = getattr(pathing_module, name)
                self.assertEqual(own_members(ported), members)


if __name__ == "__main__":
    unittest.main(verbosity=2)
