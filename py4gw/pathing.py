"""External port of Reforged's ``Pathing.py`` \u2014 the navmesh half.

The source file is 863 lines. ``Map.Pathing.ForceReloadNavMesh``
(``Map.py:2138-2143``) is ``AutoPathing().force_reload_navmesh()``, and that generator reaches
exactly this much of the file:

* **``AABB``**, the BSP helpers (``_BSP_LEAF_SIZE``, ``_BspSplit``, ``_BspLeaf``,
  ``_point_in_trapezoid``, ``_build_trap_bsp``), **``TrapezoidBSP``** and **``NavMesh``**
  (``Pathing.py:14-443``) \u2014 the whole of each, and all of it pure arithmetic and ``struct``-free
  geometry over ``MapContext``'s own ``PathingTrapezoid`` records: no client call, no injected
  state, no render.
* **``PATHING_MAP_GROUPS``** (``:572-663``) \u2014 the map-id groups ``_get_group_key`` searches,
  built from ``enums_src/map_enums.py``'s ``name_to_map_id``.
* **``AutoPathing``** (``:665-741``) \u2014 its whole class.

**What is not here, and why.** ``AStarNode``/``AStar`` (``:444-526``),
``chaikin_smooth_path`` (``:527``), ``densify_path2d`` (``:540``) and ``AutoPathing.get_path``
(``:744``) belong to path *finding*, not to the navmesh build. ``get_path`` is also the one member
in the file that calls ``PyPathing`` (``:775``), the injected runtime's planner object, and it is
not reached from ``Map``. ``Pathing.py``'s ``Utils`` use is inside ``densify_path2d``, and its
``heapq`` use is inside ``AStar``; neither is here.

**The one line that differs.** ``NavMesh.load_from_file`` logs through ``PySystem.Console.Log``
(``:439``) \u2014 the injected runtime's own in-client console. The log has no home here and is not
replaced by anything; the member records it and the body is otherwise the source's.

**A cycle that is not one.** The source imports ``Map`` at module level
(``from Py4GWCoreLib.Map import Map``, ``:11``) and so does this (``from .map import Map``).
``py4gw/map.py`` imports ``AutoPathing`` **inside** the member that needs it, exactly as
``Map.Pathing.ForceReloadNavMesh`` does (``from .Pathing import AutoPathing``), so the cycle never
forms.

Nothing here is invented: see ``docs/PORTING_RULES.md``.
"""

import math
import pickle
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from .context.map_context import PathingTrapezoid
from .enums_src.map_enums import name_to_map_id
from .map import Map


class AABB:
    """Axis-aligned bounding box for trapezoid geometry checks."""
    def __init__(self, t: PathingTrapezoid):
        self.m_t = t
        self.m_min = (min(t.XTL, t.XBL), t.YB)
        self.m_max = (max(t.XTR, t.XBR), t.YT)

# ─── BSP tree for O(log n) trapezoid point-location ─────────────────────────

# Leaf size balances construction speed vs query performance
_BSP_LEAF_SIZE = 16

class _BspSplit:
    __slots__ = ('split_y', 'above', 'below')
    def __init__(self, split_y: float, above, below):
        self.split_y = split_y
        self.above = above
        self.below = below

class _BspLeaf:
    __slots__ = ('traps',)
    def __init__(self, traps: list):
        self.traps = traps

def _point_in_trapezoid(x: float, y: float, t: PathingTrapezoid, tol: float = 0.0) -> bool:
    if y < t.YB - tol or y > t.YT + tol:
        return False
    height = t.YT - t.YB
    if height == 0:
        return False
    ratio = (y - t.YB) / height
    left_x = t.XBL + (t.XTL - t.XBL) * ratio
    right_x = t.XBR + (t.XTR - t.XBR) * ratio
    return left_x - tol <= x <= right_x + tol

def _build_trap_bsp(traps: list, sorted_indices: list, depth: int = 0):
    """Build BSP recursively using pre-sorted trapezoid indices."""
    n = len(sorted_indices)
    if n <= _BSP_LEAF_SIZE or depth >= 24:
        return _BspLeaf([traps[i] for i in sorted_indices])

    mid = n >> 1
    mid_idx = sorted_indices[mid]
    mid_prev_idx = sorted_indices[mid - 1]
    split_y = (traps[mid_prev_idx].YT + traps[mid_idx].YB) * 0.5

    above = [i for i in sorted_indices if traps[i].YT >= split_y]
    below = [i for i in sorted_indices if traps[i].YB <= split_y]

    if len(above) == n and len(below) == n:
        return _BspLeaf([traps[i] for i in sorted_indices])

    return _BspSplit(split_y,
                     _build_trap_bsp(traps, above, depth + 1),
                     _build_trap_bsp(traps, below, depth + 1))


class TrapezoidBSP:
    """BSP tree for O(log n) trapezoid point-location queries."""

    def __init__(self, trapezoids: List[PathingTrapezoid]):
        if not trapezoids:
            self._root = None
        else:
            sorted_indices = sorted(range(len(trapezoids)),
                                   key=lambda i: (trapezoids[i].YT + trapezoids[i].YB) * 0.5)
            self._root = _build_trap_bsp(trapezoids, sorted_indices)

    def find(self, x: float, y: float, tol: float = 0.0) -> Optional[int]:
        """Return trapezoid ID containing (x, y), or None."""
        if self._root is None:
            return None

        stack = [self._root]
        while stack:
            node = stack.pop()
            if isinstance(node, _BspLeaf):
                for t in node.traps:
                    if _point_in_trapezoid(x, y, t, tol):
                        return t.id
            else:
                if y > node.split_y + tol:
                    stack.append(node.above)
                elif y < node.split_y - tol:
                    stack.append(node.below)
                else:
                    stack.append(node.below)
                    stack.append(node.above)
        return None

    def find_with_margin(self, x: float, y: float, margin: float) -> bool:
        """Return True if (x, y) is inside a trapezoid with margin inset from edges."""
        if self._root is None:
            return False

        stack = [self._root]
        while stack:
            node = stack.pop()
            if isinstance(node, _BspLeaf):
                for t in node.traps:
                    if t.YB <= y <= t.YT:
                        height = t.YT - t.YB
                        if height == 0:
                            continue
                        ratio = (y - t.YB) / height
                        left_x = t.XBL + (t.XTL - t.XBL) * ratio
                        right_x = t.XBR + (t.XTR - t.XBR) * ratio
                        if left_x + margin <= x <= right_x - margin:
                            return True
            else:
                if y > node.split_y:
                    stack.append(node.above)
                elif y < node.split_y:
                    stack.append(node.below)
                else:
                    stack.append(node.below)
                    stack.append(node.above)
        return False


#region NavMesh

# Portal creation tolerances
_PORTAL_TOLERANCE = 32.0
_PORTAL_VERT_TOL = 100.2
_PORTAL_HORIZ_TOL = 100.6

class NavMesh:
    def __init__(self, pathing_maps, map_id: int):
        self.map_id = map_id
        self.trapezoids: Dict[int, PathingTrapezoid] = {}
        self.portal_graph: Dict[int, List[int]] = {}  # Adjacency graph for pathfinding
        self.portal_costs: Dict[int, Dict[int, float]] = {}
        self.trap_id_to_layer: Dict[int, int] = {}  # Trap ID -> layer index

        for i, layer in enumerate(pathing_maps):
            traps = layer.trapezoids
            self.trapezoids.update({t.id: t for t in traps})
            self.trap_id_to_layer.update({t.id: i for t in traps})

        self._bsp = TrapezoidBSP(list(self.trapezoids.values()))

        self.create_all_local_portals()
        self._create_cross_layer_portals_from_snapshots(pathing_maps)

    def get_adjacent_side(self, a: PathingTrapezoid, b: PathingTrapezoid) -> Optional[str]:
        if abs(a.YB - b.YT) < 1.0: return 'bottom_top'
        if abs(a.YT - b.YB) < 1.0: return 'top_bottom'
        if abs(a.XBR - b.XBL) < 1.0: return 'right_left'
        if abs(a.XBL - b.XBR) < 1.0: return 'left_right'
        return None

    def create_portal(self, box1: AABB, box2: AABB, side: Optional[str]) -> bool:
        """Create portal connection between two trapezoids in portal_graph."""
        pt1, pt2 = box1.m_t, box2.m_t

        def is_close(a, b): return abs(a - b) < _PORTAL_TOLERANCE

        # Validate geometric adjacency based on side
        if side == 'bottom_top':
            if not pt1.YB == pt2.YT:
                return False
            x_min = max(pt1.XBL, pt2.XBR)
            x_max = min(pt1.XBR, pt2.XBL)
            if is_close(x_max, x_min): return False

        elif side == 'top_bottom':
            if not pt1.YT == pt2.YB:
                return False
            x_min = max(pt1.XTL, pt2.XTR)
            x_max = min(pt1.XTR, pt2.XTL)
            if is_close(x_max, x_min): return False

        elif side == 'left_right':
            if not pt1.XTR == pt2.XTL:
                return False
            y_min = max(pt1.YT, pt2.YT)
            y_max = min(pt1.YB, pt2.YB)
            if is_close(y_max, y_min): return False

        elif side == 'right_left':
            if not pt1.XTL == pt2.XTR:
                return False
            y_min = max(pt1.YT, pt2.YT)
            y_max = min(pt1.YB, pt2.YB)
            if is_close(y_max, y_min): return False

        elif side is None:
            # Cross-layer portal - no geometric validation needed
            pass

        else:
            return False

        # Add bidirectional adjacency to portal graph
        self.portal_graph.setdefault(pt1.id, []).append(pt2.id)
        self.portal_graph.setdefault(pt2.id, []).append(pt1.id)
        transition_cost = 0.0 if side is None else math.hypot(
            self.get_position(pt2.id)[0] - self.get_position(pt1.id)[0],
            self.get_position(pt2.id)[1] - self.get_position(pt1.id)[1],
        )
        self.portal_costs.setdefault(pt1.id, {})[pt2.id] = transition_cost
        self.portal_costs.setdefault(pt2.id, {})[pt1.id] = transition_cost
        return True

    def create_all_local_portals(self):
        # Group traps by zplane
        zplane_traps = defaultdict(list)
        for trap_id, z in self.trap_id_to_layer.items():
            zplane_traps[z].append(self.trapezoids[trap_id])

        for traps in zplane_traps.values():
            trap_by_id = {t.id: t for t in traps}

            for ti in traps:
                for nid in ti.neighbor_ids:
                    tj = trap_by_id.get(nid)
                    if not tj or ti.id == tj.id:
                        continue
                    ai = AABB(ti)
                    aj = AABB(tj)
                    side = self.get_adjacent_side(ti, tj)
                    if side:
                        self.create_portal(ai, aj, side)

    def touching(self, a: AABB, b: AABB, vert_tol: float = _PORTAL_VERT_TOL, horiz_tol: float = _PORTAL_HORIZ_TOL) -> bool:
        """Check if two trapezoid bounding boxes are geometrically adjacent."""
        # Same vertical alignment
        if abs(a.m_t.YB - b.m_t.YT) < vert_tol or abs(a.m_t.YT - b.m_t.YB) < vert_tol:
            left_a = min(a.m_t.XBL, a.m_t.XTL)
            right_a = max(a.m_t.XBR, a.m_t.XTR)
            left_b = min(b.m_t.XBL, b.m_t.XTL)
            right_b = max(b.m_t.XBR, b.m_t.XTR)
            if right_a >= left_b and right_b >= left_a:
                return True

        # Same horizontal alignment
        if abs(a.m_t.XBR - b.m_t.XBL) < horiz_tol or abs(a.m_t.XBL - b.m_t.XBR) < horiz_tol:
            top_a = max(a.m_t.YT, a.m_t.YB)
            bottom_a = min(a.m_t.YT, a.m_t.YB)
            top_b = max(b.m_t.YT, b.m_t.YB)
            bottom_b = min(b.m_t.YT, b.m_t.YB)
            if top_a >= bottom_b and top_b >= bottom_a:
                return True

        return False

    def _create_cross_layer_portals_from_snapshots(self, pathing_maps):
        """Build cross-layer portal connections from snapshot portal data."""
        cross_groups: Dict[Tuple[int, int], Dict[int, List[PathingTrapezoid]]] = defaultdict(lambda: defaultdict(list))

        for plane_idx, pmap in enumerate(pathing_maps):
            for portal in pmap.portals:
                if portal.left_layer_id == portal.right_layer_id:
                    continue

                layer_pair = (min(portal.left_layer_id, portal.right_layer_id),
                              max(portal.left_layer_id, portal.right_layer_id))

                for trap_id in portal.trapezoid_indices:
                    trap = self.trapezoids.get(trap_id)
                    if trap:
                        cross_groups[layer_pair][plane_idx].append(trap)

        for plane_map in cross_groups.values():
            planes = list(plane_map.keys())
            if len(planes) < 2:
                continue

            for i in range(len(planes)):
                for j in range(i + 1, len(planes)):
                    traps_i = plane_map[planes[i]]
                    traps_j = plane_map[planes[j]]

                    for ti in traps_i:
                        ai = AABB(ti)
                        for tj in traps_j:
                            if ti.id == tj.id:
                                continue
                            aj = AABB(tj)
                            if self.touching(ai, aj):
                                self.create_portal(ai, aj, None)


    def get_position(self, t_id: int) -> Tuple[float, float]:
        t = self.trapezoids[t_id]
        cx = (t.XTL + t.XTR + t.XBL + t.XBR) / 4
        cy = (t.YT + t.YB) / 2
        return (cx, cy)

    def get_neighbors(self, t_id: int) -> List[int]:
        return self.portal_graph.get(t_id, [])

    def get_transition_cost(self, from_id: int, to_id: int) -> float:
        explicit_cost = self.portal_costs.get(from_id, {}).get(to_id)
        if explicit_cost is not None:
            return explicit_cost
        fx, fy = self.get_position(from_id)
        tx, ty = self.get_position(to_id)
        return math.hypot(tx - fx, ty - fy)

    def find_trapezoid_id_by_coord(self, point: Tuple[float, float], tol: float = 20.0) -> Optional[int]:
        """Return trapezoid ID containing point, or None."""
        return self._bsp.find(point[0], point[1], tol)

    def contains(self, x: float, y: float, margin: float = 20.0) -> bool:
        """Return True if (x, y) lies on the NavMesh with the given inset margin."""
        return self._bsp.find_with_margin(x, y, margin)

    def find_nearest_trapezoid_id(self, x: float, y: float) -> Optional[int]:
        """Return the ID of the trapezoid whose centroid is closest to (x, y).
        """
        best_id: Optional[int] = None
        best_dist = float("inf")
        for t_id, t in self.trapezoids.items():
            cx = (t.XTL + t.XTR + t.XBL + t.XBR) / 4
            cy = (t.YT + t.YB) / 2
            d = math.hypot(cx - x, cy - y)
            if d < best_dist:
                best_dist = d
                best_id = t_id
        return best_id

    def find_nearest_reachable(
        self,
        origin: Tuple[float, float],
        margin: float = 20.0,
    ) -> Optional[Tuple[float, float]]:
        """Return the nearest reachable NavMesh position to origin.

        If origin already lies on the mesh it is returned as-is.  Otherwise
        the centroid of the closest trapezoid is returned.  Returns None only
        when the NavMesh is empty.

        Can be used for any position query – player location, click
        coordinates, waypoints, etc.
        """
        if self.contains(origin[0], origin[1], margin):
            return origin

        t_id = self.find_nearest_trapezoid_id(origin[0], origin[1])
        if t_id is None:
            return None
        return self.get_position(t_id)

    def has_line_of_sight(self,
                          p1: Tuple[float, float],
                          p2: Tuple[float, float],
                          margin: float = 100,
                          step_dist: float = 200.0) -> bool:

        total_dist = math.dist(p1, p2)
        steps = int(total_dist / step_dist) + 1
        dx = (p2[0] - p1[0]) / steps
        dy = (p2[1] - p1[1]) / steps

        for i in range(1, steps):
            x = p1[0] + dx * i
            y = p1[1] + dy * i
            if not self._bsp.find_with_margin(x, y, margin):
                return False
        return True



    def smooth_path_by_los(self,
                           path: List[Tuple[float, float]],
                           margin: float = 100,
                           step_dist: float = 200.0) -> List[Tuple[float, float]]:
        if len(path) <= 2:
            return path

        result = [path[0]]
        i = 0
        while i < len(path) - 1:
            j = len(path) - 1
            while j > i + 1:
                if self.has_line_of_sight(path[i], path[j], margin, step_dist):
                    break
                j -= 1
            result.append(path[j])
            i = j
        return result

    def save_to_file(self, folder: str):
        """Serialize NavMesh portal graph and metadata to disk."""
        filepath = f"{folder}/navmesh_{self.map_id}.bin"
        data = {
            "map_id": self.map_id,
            "portal_graph": self.portal_graph,
            "portal_costs": self.portal_costs,
            "trap_id_to_layer": self.trap_id_to_layer
        }
        with open(filepath, "wb") as f:
            pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)


    @staticmethod
    def load_from_file(pathing_maps, map_id: int, folder: str) -> "NavMesh":
        """Load serialized NavMesh portal graph and rebuild BSP from current trapezoid data."""
        filepath = f"{folder}/navmesh_{map_id}.bin"

        nav = NavMesh.__new__(NavMesh)
        nav.map_id = map_id
        nav.trapezoids = {}
        nav.portal_graph = {}
        nav.portal_costs = {}
        nav.trap_id_to_layer = {}

        for i, layer in enumerate(pathing_maps):
            traps = layer.trapezoids
            nav.trapezoids.update({t.id: t for t in traps})
            nav.trap_id_to_layer.update({t.id: i for t in traps})

        nav._bsp = TrapezoidBSP(list(nav.trapezoids.values()))

        with open(filepath, "rb") as f:
            data = pickle.load(f)

        nav.portal_graph = data["portal_graph"]
        if "portal_costs" in data:
            nav.portal_costs = data["portal_costs"]
        if "trap_id_to_layer" in data:
            nav.trap_id_to_layer = data["trap_id_to_layer"]

        # The source logs the load through ``PySystem.Console`` -- the injected runtime's own
        # in-client console, which this port does not carry (``py4gwcorelib_src/Console.py`` is
        # 38 lines that *are* that console). The log has no home here and is not replaced by
        # anything; the body is otherwise the source's, and this is the only line that differs.
        return nav


PATHING_MAP_GROUPS = [
    [
        name_to_map_id["Great Temple of Balthazar"],
        name_to_map_id["Isle of the Nameless"],
    ],
    [
        name_to_map_id["Minister Chos Estate outpost"],
        name_to_map_id["Minister Chos Estate (explorable area)"],
    ],
    [
        name_to_map_id["Shing Jea Monastery"],
        212,  # Monastery Overlook
        285,  # Monastery Overlook
        name_to_map_id["Linnok Courtyard"],
        name_to_map_id["Saoshang Trail"],
        name_to_map_id["Seitung Harbor"],
    ],
    [
        name_to_map_id["Zen Daijun outpost"],
        name_to_map_id["Zen Daijun (explorable area)"],
    ],
    [
        name_to_map_id["Ran Musu Gardens"],
        name_to_map_id["Kinya Province"],
    ],
    [
        name_to_map_id["Tsumei Village"],
        name_to_map_id["Sunqua Vale"],
    ],#Nightfall Region - Istan Island - Below - aC
    [
        name_to_map_id["Kamadan Jewel of Istan - Halloween"],
        name_to_map_id["Kamadan Jewel of Istan - Wintersday"],
        name_to_map_id["Kamadan Jewel of Istan - Canthan New Year"],
        name_to_map_id["Kamadan Jewel of Istan"],
        name_to_map_id["Consulate"],
        name_to_map_id["Consulate Docks outpost"],
        name_to_map_id["Sun Docks"],
    ],
    [
        name_to_map_id["Sunspear Great Hall"],
        name_to_map_id["Plains of Jarin"],
    ], #Nightfall Region - Kourna - Below - aC
    [
        name_to_map_id["Nundu Bay outpost"],
        name_to_map_id["Marga Coast"],
    ],
    [
        name_to_map_id["Camp Hojanu"],
        name_to_map_id["Barbarous Shore"],
    ],
    [
        name_to_map_id["Venta Cemetery outpost"],
        name_to_map_id["Sunward Marches"],
    ],
    [
        name_to_map_id["Rilohn Refuge outpost"],
        name_to_map_id["The Floodplain of Mahnkelon"],
    ],
    [
        name_to_map_id["Chantry of Secrets"],
        name_to_map_id["Yatendi Canyons"],
    ], #Nightfall Region - Vabbi - Below - aC
    [
        name_to_map_id["Honur Hill"],
        name_to_map_id["Resplendent Makuun"],
        name_to_map_id["Bokka Amphitheatre"],
    ],
    [
        name_to_map_id["Tihark Orchard outpost"],
        name_to_map_id["Forum Highlands"],
    ],
    [
        name_to_map_id["Grand Court of Sebelkeh outpost"],
        name_to_map_id["The Mirror of Lyss"],
    ],
    [
        name_to_map_id["Dasha Vestibule outpost"],
        name_to_map_id["The Hidden City of Ahdashim"],
    ], #Nightfall Region - The Desolation - Below - aC
    [
        name_to_map_id["Bone Palace"],
        name_to_map_id["Joko's Domain"],
    ],
    [
        name_to_map_id["Ruins of Morah outpost"],
        name_to_map_id["The Alkali Pan"],
    ],
    [
        name_to_map_id["The Mouth of Torment"],
        name_to_map_id["The Ruptured Heart"]
    ],
]


class AutoPathing:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AutoPathing, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.load_time: float = 0.0
        self.is_ready: bool = False
        self.pathing_map_cache: dict[tuple[int, ...], NavMesh] = {}
        self._last_group_key: Optional[tuple[int, ...]] = None
        self._initialized = True

    def _get_group_key(self, map_id: int) -> tuple[int, ...]:
        for group in PATHING_MAP_GROUPS:
            if map_id in group:
                return tuple(sorted(group))
        return (map_id,)  # Default: treat each unknown map_id as its own group

    def load_pathing_maps(self):
        map_id = Map.GetMapID()
        if not map_id or not Map.IsMapReady():
            yield
            return

        group_key = self._get_group_key(map_id)
        yield

        cached = self.pathing_map_cache.get(group_key)
        if cached is not None and cached.map_id == map_id and cached.trapezoids:
            yield
            return
        pathing_maps = Map.Pathing.GetPathingMaps()
        navmesh = NavMesh(pathing_maps, map_id) if pathing_maps else None
        if navmesh and navmesh.trapezoids:
            self.pathing_map_cache[group_key] = navmesh
        yield

    def clear_navmesh_cache(self, map_id: Optional[int] = None):
        if map_id is None:
            self.pathing_map_cache.clear()
            self._last_group_key = None
            return

        group_key = self._get_group_key(map_id)
        self.pathing_map_cache.pop(group_key, None)
        if self._last_group_key == group_key:
            self._last_group_key = None

    def force_reload_navmesh(self):
        map_id = Map.GetMapID()
        if not map_id or not Map.IsMapReady():
            yield
            return

        Map.Pathing.ClearPathingCache(map_id=map_id, include_live=True)
        self.clear_navmesh_cache(map_id)
        yield from self.load_pathing_maps()


    def get_navmesh(self) -> Optional[NavMesh]:
        map_id = Map.GetMapID()
        if not map_id:
            return None

        group_key = self._get_group_key(map_id)
        nav = self.pathing_map_cache.get(group_key)

        if nav is None or nav.map_id != map_id or not nav.trapezoids:
            return None

        return nav

    def get_path(self,
                 start: Tuple[float, float, float],
                 goal: Tuple[float, float, float],
                 smooth_by_los: bool = True,
                 margin: float = 100,
                 step_dist: float = 200.0,
                 smooth_by_chaikin: bool = False,
                 chaikin_iterations: int = 1):
        """Not built: it needs the injected planner and the coroutine driver.

        The source's body (``Pathing.py:744-835``) drives ``PyPathing.PathPlanner``
        (``:775-790``: ``plan``, then ``get_status``/``get_path`` against
        ``PyPathing.PathStatus.Ready`` and ``.Failed``), yields through
        ``Routines.Yield.wait(100)`` (``:783``) — Reforged's per-frame coroutine driver — and falls
        back to ``AStar(navmesh).search(...)`` (``:815-816``), smoothing with
        ``chaikin_smooth_path`` and ``densify_path2d`` (``:796, 798``).

        **Nothing here is on ``Map.Pathing``'s path.** ``ForceReloadNavMesh`` reaches
        ``force_reload_navmesh``, ``clear_navmesh_cache`` and ``load_pathing_maps`` only. Two
        things would have to exist first, and both are named rather than stood in for:
        ``PyPathing`` is the injected runtime's planner object — it owns a planner instance, not a
        client function this port could call — and the ``Routines`` driver is Reforged's frame
        loop, which this port does not carry at all (no class here has an action queue, a coroutine
        driver, a behaviour tree or ``GLOBAL_CACHE``; the enqueue is the capability layer's own call
        path). ``AStar``, ``AStarNode``, ``chaikin_smooth_path`` and ``densify_path2d`` are this
        member's own helpers and are not ported here, because nothing reached them.
        """

        raise _unported(
            "Pathing.AutoPathing.get_path",
            "PyPathing.PathPlanner with its PathStatus (Pathing.py:775-790) and the "
            "Routines.Yield.wait coroutine driver (:783) — the injected runtime's planner object "
            "and its frame loop; plus AStar, chaikin_smooth_path and densify_path2d, which are "
            "this member's own helpers",
        )

    def get_path_to(self, x: float, y: float,
                    smooth_by_los: bool = True,
                    margin: float = 100,
                    step_dist: float = 200.0,
                    smooth_by_chaikin: bool = False,
                    chaikin_iterations: int = 1):
        """Not built: it is ``get_path`` from the player's own position.

        The source's body (``Pathing.py:837-862``) reads ``Player.GetAgent()``, takes that agent's
        ``pos.x``/``pos.y``/``pos.zplane`` as the start point and ``(x, y, zplane)`` as the goal,
        then delegates to ``get_path``. It fails for exactly the reason that member does, and it is
        not on ``Map.Pathing``'s path either.
        """

        raise _unported(
            "Pathing.AutoPathing.get_path_to",
            "Pathing.AutoPathing.get_path — the injected runtime's PyPathing.PathPlanner and the "
            "Routines coroutine driver (Pathing.py:856-861)",
        )


def _unported(member: str, requirement: str) -> NotImplementedError:
    """Build the error raised by a member this port has not built yet.

    The source's member is complete and working, so the message names the work item this port
    still owes and nothing about the source. The same builder ``py4gw/map.py`` uses, with the
    class's own name in front of the member.
    """

    return NotImplementedError(
        f"{member} is declared but not built here yet: it needs {requirement}. "
        "The source's member works; this port raises at the call site and names the work "
        "item instead of returning a wrong value."
    )
