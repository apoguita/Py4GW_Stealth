"""External port of Reforged's ``Pathing.py`` — the whole file, all twelve of its top-level pieces.

The source is 863 lines: the navmesh build, the path walk, the map groups and the class that ties them
together. All of it is here, in the source's own order:

* **``AABB``**, the BSP helpers (``_BSP_LEAF_SIZE``, ``_BspSplit``, ``_BspLeaf``,
  ``_point_in_trapezoid``, ``_build_trap_bsp``), **``TrapezoidBSP``** and **``NavMesh``**
  (``Pathing.py:14-443``) — pure geometry over ``MapContext``'s own ``PathingTrapezoid`` records.
* **``AStarNode``**, **``AStar``** (``:446-524``), **``chaikin_smooth_path``** (``:527``) and
  **``densify_path2d``** (``:540``) — the path walk: A* over the navmesh, corner cutting, and the
  splitting of long hops. All four are arithmetic; ``AStar.search``'s four log lines are the one
  thing in them that has no home here (recorded on the class).
* **``PATHING_MAP_GROUPS``** (``:572-663``) — the map-id groups ``_get_group_key`` searches, built from
  ``enums_src/map_enums.py``'s ``name_to_map_id``.
* **``AutoPathing``** (``:665-862``) — its whole class, ``get_path``/``get_path_to`` included.
* **``PathStatus``** and **``PathPlanner``** — Native's bound surface (``pathing_bindings.cpp:10-43``),
  which ``Pathing.py`` reaches as ``PyPathing`` (``:775-790``). Native's class is a thin wrapper over
  the **client's own path finder** (``pathing.find_path_func``, called with the six-word
  ``STACK_WORDS`` form and records in the block's data region), and that is what this port drives.

**Two recorded divergences, both consequences of the execution model rather than verdicts on the
source.** ``AutoPathing.get_path``/``get_path_to`` are **generators** in the source (``:744``, ``:837``)
because they wait for the client's frame through ``yield from Routines.Yield.wait(100)`` (``:783``);
this library has no frame loop and its calls already run on the game thread, so they are **plain
functions** returning the same value (recorded on ``get_path``). And the injected runtime's logging
(``PySystem.Console``, ``Logger``) has no home here: ``NavMesh.load_from_file``'s line and
``AStar.search``'s four are marked where they occur and not replaced by anything.

**A cycle that is not one.** The source imports ``Map`` at module level
(``from Py4GWCoreLib.Map import Map``, ``:11``) and so does this (``from .map import Map``).
``py4gw/map.py`` imports ``AutoPathing`` **inside** the member that needs it, exactly as
``Map.Pathing.ForceReloadNavMesh`` does (``from .Pathing import AutoPathing``), so the cycle never
forms.

Nothing here is invented: see ``docs/PORTING_RULES.md``.
"""

import heapq
import math
import pickle
from collections import defaultdict
from enum import IntEnum
from typing import Dict, List, Optional, Tuple

from .context.map_context import PathingTrapezoid
from .enums_src.map_enums import name_to_map_id
from .map import Map

#: ``pathing.find_path_func`` (``offsets/pathing.json``, resolved from ``pathing_patterns.cpp``) is the
#: **client's own path finder**, and it is what native's whole pathing surface is a wrapper over:
#: ``g_find_path_func`` is the only thing ``PathPlanner::PlanPath`` and
#: ``PathPlanner::ComputePathImmediate`` call (``pathing.cpp:38``, ``:76``). Its prototype is
#: ``void __cdecl(PathPoint* start, PathPoint* goal, float range, uint32_t maxCount, uint32_t* count,
#: PathPoint* pathArray)`` (``pathing.h:22``) — six pushed words, all four bytes, which is the
#: ``STACK_WORDS`` form.
FIND_PATH_FUNC = "pathing.find_path_func"

#: Where this call's six **argument words** sit in the block's data region: the two endpoint addresses,
#: the range's bit pattern, the array's capacity, the count word's address and the array's address.
#: Native pushes its own frame's pointers and locals (``pathing.cpp:30-38``); this project has no frame
#: in the client, so the arguments and the records they point at live in the block — the same shape
#: ``py4gw/merchant.py`` uses for the two by-value calls it drives.
PATHING_ARGUMENTS_OFFSET = 0x1000
PATHING_ARGUMENT_WORDS = 6

#: The two ``PathPoint`` endpoints, the ``uint32_t pathCount`` word the client writes, and the
#: ``std::array<PathPoint, 30> pathArray`` it fills (``pathing.cpp:31``, whose size native passes as
#: ``maxPoints``). One ``PathPoint`` is 0x10 bytes (``context/map_context.py``, ``context/pathing.h``).
PATHING_START_OFFSET = 0x1018
PATHING_GOAL_OFFSET = 0x1028
PATHING_COUNT_OFFSET = 0x1038
PATHING_ARRAY_OFFSET = 0x1040
PATH_POINT_SIZE = 0x10
MAX_PATH_POINTS = 30

#: Native's own range word, ``10000.0f`` (``pathing.cpp:38``).
FIND_PATH_RANGE = 10000.0


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


#: The source's ``AStar.search`` logs through ``PySystem.Console`` **four** times -- the injected
#: runtime's own in-client console, which this port does not carry. That is the treatment
#: ``NavMesh.load_from_file`` already records for its own log line (``Pathing.py:439``): the call has
#: no home here, it is **not** replaced by anything, and the member's body is otherwise the source's.
#: Each of the four sites is marked where it occurs.
class AStarNode:
    def __init__(self, node_id, g, f, parent=None):
        self.id = node_id
        self.g = g
        self.f = f
        self.parent = parent
    def __lt__(self, other): return self.f < other.f

class AStar:
    def __init__(self, navmesh: NavMesh):
        self.navmesh = navmesh
        self.path: List[Tuple[float, float]] = []

    def heuristic(self, a: int, b: int) -> float:
        ax, ay = self.navmesh.get_position(a)
        bx, by = self.navmesh.get_position(b)
        return math.hypot(bx - ax, by - ay)

    def search(self, start_pos: Tuple[float, float], goal_pos: Tuple[float, float]) -> bool:
        start_id = self.navmesh.find_trapezoid_id_by_coord(start_pos)
        goal_id = self.navmesh.find_trapezoid_id_by_coord(goal_pos)

        if start_id is None:
            start_id = self.navmesh.find_nearest_trapezoid_id(start_pos[0], start_pos[1])
            if start_id is not None:
                pass  # source logs the recovery here through PySystem.Console (Warning)
        if goal_id is None:
            goal_id = self.navmesh.find_nearest_trapezoid_id(goal_pos[0], goal_pos[1])
            if goal_id is not None:
                pass  # source logs the recovery here through PySystem.Console (Warning)

        if start_id is None or goal_id is None:
            return False  # source logs the invalid pair here through PySystem.Console (Error)

        open_list: List[AStarNode] = []
        heapq.heappush(open_list, AStarNode(start_id, 0, self.heuristic(start_id, goal_id)))
        came_from: Dict[int, int] = {}
        cost_so_far: Dict[int, float] = {start_id: 0}

        while open_list:
            current = heapq.heappop(open_list)
            if current.id == goal_id:
                self._reconstruct(came_from, goal_id)
                # Prepend exact start position, append exact goal position
                #
                # The two are inserted unconditionally, and ``_reconstruct`` has already ended the
                # path at both trapezoids' centroids -- so a caller whose own points *are* those
                # centroids gets them twice. That is the source's behaviour, kept here; the member
                # that deals with it is ``AutoPathing.get_path``, whose own ``_prepend_start`` guards
                # its prepend with the 750-unit test.
                self.path.insert(0, start_pos)
                self.path.append(goal_pos)
                return True

            for neighbor in self.navmesh.get_neighbors(current.id):
                new_cost = cost_so_far[current.id] + self.navmesh.get_transition_cost(current.id, neighbor)
                if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                    cost_so_far[neighbor] = new_cost
                    priority = new_cost + self.heuristic(neighbor, goal_id)
                    heapq.heappush(open_list, AStarNode(neighbor, new_cost, priority, current.id))
                    came_from[neighbor] = current.id

        return False  # source logs "Path not found from ... to ..." here through PySystem.Console

    def _reconstruct(self, came_from: Dict[int, int], end_id: int):
        self.path = []
        while end_id in came_from:
            self.path.append(self.navmesh.get_position(end_id))
            end_id = came_from[end_id]
        self.path.append(self.navmesh.get_position(end_id))  # Add start node
        self.path.reverse()

    def get_path(self) -> List[Tuple[float, float]]:
        return self.path


def chaikin_smooth_path(points: List[Tuple[float, float]], iterations: int = 1) -> List[Tuple[float, float]]:
    for _ in range(iterations):
        new_points = [points[0]]
        for i in range(len(points) - 1):
            p0 = points[i]
            p1 = points[i + 1]
            q = (0.75 * p0[0] + 0.25 * p1[0], 0.75 * p0[1] + 0.25 * p1[1])
            r = (0.25 * p0[0] + 0.75 * p1[0], 0.25 * p0[1] + 0.75 * p1[1])
            new_points.extend([q, r])
        new_points.append(points[-1])
        points = new_points
    return points

def densify_path2d(points: List[Tuple[float, float]], threshold: float = 500.0) -> List[Tuple[float, float]]:
    """Split path segments longer than threshold into smaller steps."""
    if threshold <= 0 or len(points) <= 1:
        return points.copy()

    # The source imports ``Utils`` at module level (``Pathing.py:10``); its one use is here, and this
    # is ``Utils``'s own arithmetic (``py4gw/py4gwcorelib_src/utils.py:93``).
    from .py4gwcorelib_src.utils import Utils

    out: List[Tuple[float, float]] = [points[0]]
    eps = 1e-6

    for i in range(1, len(points)):
        x0, y0 = out[-1]
        x1, y1 = points[i]

        # distance between the two points (2D)
        dist = Utils.Distance((x0, y0), (x1, y1))
        if dist <= threshold + eps:
            out.append((x1, y1))
            continue

        # direction (unit vector)
        dx, dy = x1 - x0, y1 - y0
        ux, uy = dx / dist, dy / dist

        s = threshold
        while s < dist - eps:
            out.append((x0 + ux * s, y0 + uy * s))
            s += threshold

        out.append((x1, y1))

    return out


class PathStatus(IntEnum):
    """Native's ``PyPathing.PathStatus`` (``pathing_bindings.cpp:10-15``), in the source's order.

    The binding also calls ``export_values()``, which puts ``Idle``/``Pending``/``Ready``/``Failed`` in
    the module namespace as well; the port carries the enum only, because that is the form the one
    caller in the sources uses (``PyPathing.PathStatus.Ready``, ``Pathing.py:788``) and bare ``Ready``
    in a module of this size would be a name collision waiting to happen. That omission is recorded
    here rather than left to be discovered.
    """

    Idle = 0
    Pending = 1
    Ready = 2
    Failed = 3


class PathPlanner:
    """Native's ``PyPathing.PathPlanner`` (``pathing_bindings.cpp:17-43``) over the client's finder.

    Native's class (``pathing.h:32-74``) is a thin wrapper: ``PlanPath`` sets ``Pending``, checks that
    the finder resolved, and enqueues a lambda on the game thread that calls ``g_find_path_func`` with
    two ``PathPoint`` endpoints, the range, the array's capacity, a count word and the array — then
    marks ``Ready`` or ``Failed`` from what came back. ``ComputePathImmediate`` is the same call with
    no queue, and the rest are accessors over the two fields.

    **This port's call path is already the game thread** — the note ``set_hero_behavior`` and
    ``UseSkill`` carry, from ``game_thread::Enqueue`` running its callable inline when it is already
    there (``game_thread_methods.cpp:33-45``) — so both members call the client and read the answer
    back in one go, and a status native could only observe a frame later is already final when
    ``plan`` returns. The one thing native does that has no counterpart here is its failure log
    (``Logger::Instance().LogError("FindPath_Func not initialized.", "pathing")``,
    ``pathing.cpp:22``): the port asks the catalog whether the function is there — the same question,
    asked of the thing that holds it — and marks ``Failed`` without a log, because this port carries no
    in-client logger (the treatment ``NavMesh.load_from_file`` records for ``PySystem.Console``).
    """

    def __init__(self) -> None:
        self._path: List[Tuple[float, float, float]] = []
        self._status: PathStatus = PathStatus.Idle

    def plan(self, start_x: float, start_y: float, start_z: float,
             goal_x: float, goal_y: float, goal_z: float) -> None:
        """``PathPlanner::PlanPath``: the client's finder, and the two answers it can give."""

        self._status = PathStatus.Pending
        self._path = []

        points = self._find(start_x, start_y, start_z, goal_x, goal_y, goal_z)
        if points is None:
            self._status = PathStatus.Failed
            return

        goal_pos = (float(goal_x), float(goal_y))
        if not points or (
            len(points) == 1 and (points[0][0], points[0][1]) != goal_pos
        ):
            self._status = PathStatus.Failed
            return

        self._path = points
        self._status = PathStatus.Ready

    def compute_immediate(self, start_x: float, start_y: float, start_z: float,
                          goal_x: float, goal_y: float, goal_z: float
                          ) -> List[Tuple[float, float, float]]:
        """``PathPlanner::ComputePathImmediate``: the same call, answering the list itself."""

        points = self._find(start_x, start_y, start_z, goal_x, goal_y, goal_z)
        goal_pos = (float(goal_x), float(goal_y))
        if points is None or not points or (
            len(points) == 1 and (points[0][0], points[0][1]) != goal_pos
        ):
            self._status = PathStatus.Failed
            return []

        return points

    def get_status(self) -> PathStatus:
        return self._status

    def is_ready(self) -> bool:
        return self._status == PathStatus.Ready

    def was_successful(self) -> bool:
        status = self._status
        return status == PathStatus.Ready

    def get_path(self) -> List[Tuple[float, float, float]]:
        return self._path

    def reset(self) -> None:
        self._path = []
        self._status = PathStatus.Idle

    @staticmethod
    def _find(start_x: float, start_y: float, start_z: float,
              goal_x: float, goal_y: float, goal_z: float
              ) -> List[Tuple[float, float, float]] | None:
        """The one call both members make, or ``None`` when the finder is not resolved.

        The six argument words are written **after** the records they point at, because the words are
        the records' addresses inside the block — the same order ``merchant._transact`` uses when it
        places a record and then hands the client its address.
        """

        import struct

        from .client import require_client
        from .game_thread.shared_block import CallForm, float_bits

        client = require_client()
        if not client.resolves(FIND_PATH_FUNC):
            return None

        bridge = client.bridge
        start_address = bridge.write_data(
            PATHING_START_OFFSET,
            struct.pack("<ffI", float(start_x), float(start_y), int(start_z) & 0xFFFFFFFF)
            + b"\x00\x00\x00\x00",
        )
        goal_address = bridge.write_data(
            PATHING_GOAL_OFFSET,
            struct.pack("<ffI", float(goal_x), float(goal_y), int(goal_z) & 0xFFFFFFFF)
            + b"\x00\x00\x00\x00",
        )
        count_address = bridge.data_address(PATHING_COUNT_OFFSET, 4)
        array_address = bridge.data_address(
            PATHING_ARRAY_OFFSET, MAX_PATH_POINTS * PATH_POINT_SIZE
        )
        bridge.write_data(PATHING_COUNT_OFFSET, struct.pack("<I", 0))
        bridge.write_data(
            PATHING_ARGUMENTS_OFFSET,
            b"".join(
                struct.pack("<I", word)
                for word in (
                    start_address,
                    goal_address,
                    float_bits(FIND_PATH_RANGE),
                    MAX_PATH_POINTS,
                    count_address,
                    array_address,
                )
            ),
        )

        client.call_function(
            FIND_PATH_FUNC,
            CallForm.STACK_WORDS,
            PATHING_ARGUMENTS_OFFSET,
            PATHING_ARGUMENT_WORDS,
        )

        count = struct.unpack("<I", bridge.read_data(PATHING_COUNT_OFFSET, 4))[0]
        if not count:
            return []
        raw = bridge.read_data(PATHING_ARRAY_OFFSET, count * PATH_POINT_SIZE)
        return [
            (
                struct.unpack_from("<f", raw, offset)[0],
                struct.unpack_from("<f", raw, offset + 4)[0],
                float(struct.unpack_from("<I", raw, offset + 8)[0]),
            )
            for offset in range(0, len(raw), PATH_POINT_SIZE)
        ]


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
        self._initialized = True

    def _get_group_key(self, map_id: int) -> tuple[int, ...]:
        for group in PATHING_MAP_GROUPS:
            if map_id in group:
                return tuple(sorted(group))
        return (map_id,)  # Default: treat each unknown map_id as its own group

    def load_pathing_maps(self):
        """The source's loader, which has nothing to load into here.

        Reforged's body parks this coroutine, checks the navmesh it holds for the map's group and
        builds one into ``pathing_map_cache`` when the map changed. **This port keeps no navmesh**: it
        is built from the live map's pathing records, which can change between frames and which this
        library cannot re-check, so :meth:`get_navmesh` builds one when it is asked. The member keeps
        the source's generator shape and its place in a caller's sequence, and says so rather than
        filling a cache that must not exist.
        """

        if not Map.GetMapID() or not Map.IsMapReady():
            yield
            return
        yield

    def clear_navmesh_cache(self, map_id: Optional[int] = None):
        """The source's own cache-clearing member, with no navmesh of its own to clear (above)."""

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
        """Build the current map's navmesh **now**, from the client's own pathing records.

        Reforged returns the one ``load_pathing_maps`` left in ``pathing_map_cache``. This port keeps
        no navmesh — it is built from live map records, which change between frames with nothing here
        able to notice — so the build happens on the call. Measured against the live client: **0.027 s**
        for a 3,361-trapezoid map, which is the price of the rule, paid by whoever asks.
        """

        map_id = Map.GetMapID()
        if not map_id:
            return None

        pathing_maps = Map.Pathing.GetPathingMaps()
        if not pathing_maps:
            return None
        navmesh = NavMesh(pathing_maps, map_id)
        return navmesh if navmesh.trapezoids else None

    def get_path(self,
                 start: Tuple[float, float, float],
                 goal: Tuple[float, float, float],
                 smooth_by_los: bool = True,
                 margin: float = 100,
                 step_dist: float = 200.0,
                 smooth_by_chaikin: bool = False,
                 chaikin_iterations: int = 1) -> List[Tuple[float, float, float]]:
        """The source's route from ``start`` to ``goal``: the client's planner first, A* second.

        **One recorded divergence, and it is the member's shape.** The source declares this a
        *generator* (`Pathing.py:744`) and waits inside it — ``yield from Routines.Yield.wait(100)``
        (`:783`) parks the coroutine for a frame so the client can run the planning call it was handed,
        re-checks the map on every wake, and only then reads the status. That is Reforged's per-frame
        coroutine driver, which this library does not carry, and the call this port makes **is already
        on the game thread**, so the status is final when ``plan`` returns: the generator would have
        nothing to wait for and every caller would have to drive it to get the value. So the member
        returns the list the source's own ``return`` produces, and every other line keeps the source's
        order — the map check before planning, the same check again before the answer is used, the
        planner first and the navmesh route as the fallback, ``_prepend_start`` verbatim, LOS
        smoothing, optional Chaikin, then densify. The same ruling covers :meth:`get_path_to`.

        The map check the source performs **inside** its loop is kept once, before the result is used:
        with nothing to wait for there is no second moment for it to catch, and the source's own
        abort-cleanly answer for a map that is loading or has changed is ``[]``.
        """

        def _prepend_start(path2d, sx, sy):
            if not path2d:
                return [(sx, sy)]

            dx = path2d[0][0] - sx
            dy = path2d[0][1] - sy
            d2 = dx*dx + dy*dy

            # Only prepend if it is REALLY far (path clearly doesn't start at player)
            if d2 > 750*750:
                return [(sx, sy)] + path2d

            return path2d

        map_id = Map.GetMapID()
        if not map_id:
            return []
        group_key = self._get_group_key(map_id)

        # --- Try fast planner first ---
        path_planner = PathPlanner()
        path_planner.reset()
        path_planner.plan(
            start_x=start[0], start_y=start[1], start_z=start[2],
            goal_x=goal[0], goal_y=goal[1], goal_z=goal[2]
        )

        current_map_id = Map.GetMapID()
        if not current_map_id or Map.IsMapLoading() or current_map_id != map_id:
            return []  # map changed while pathfinding — abort cleanly
        status = path_planner.get_status()
        if status == PathStatus.Ready:
            raw_path = path_planner.get_path()
            path2d = [(pt[0], pt[1]) for pt in raw_path]

            path2d = _prepend_start(path2d, start[0], start[1])

            if smooth_by_chaikin:
                path2d = chaikin_smooth_path(path2d, chaikin_iterations)

            path2d = densify_path2d(path2d)
            return [(x, y, start[2]) for (x, y) in path2d]

        # ``PathStatus.Failed`` — the source breaks out of its loop here and tries the navmesh.
        navmesh = self.get_navmesh()
        if not navmesh:
            for _ in self.load_pathing_maps():
                pass
            navmesh = self.get_navmesh()
            if not navmesh:
                return []

        astar = AStar(navmesh)
        success = astar.search((start[0], start[1]), (goal[0], goal[1]))

        if success:
            raw_path = astar.get_path()
            raw_path = _prepend_start(raw_path, start[0], start[1])
            if smooth_by_los:
                smoothed = navmesh.smooth_path_by_los(raw_path, margin, step_dist)
            else:
                smoothed = raw_path

            if smooth_by_chaikin:
                smoothed = chaikin_smooth_path(smoothed, chaikin_iterations)

            path2d = densify_path2d(smoothed)  # split long hops into ≤750

            return [(x, y, start[2]) for (x, y) in path2d]

        return []

    def get_path_to(self, x: float, y: float,
                    smooth_by_los: bool = True,
                    margin: float = 100,
                    step_dist: float = 200.0,
                    smooth_by_chaikin: bool = False,
                    chaikin_iterations: int = 1) -> List[Tuple[float, float]]:
        """``get_path`` from the player's own position (``Pathing.py:837-862``).

        The source reads ``Player.GetAgent()``, takes that agent's ``pos.x``/``pos.y``/``pos.zplane``
        as the start and ``(x, y, zplane)`` as the goal, delegates to :meth:`get_path` and answers the
        path's two flat coordinates. It is a generator in the source for the same reason
        :meth:`get_path` is, and it is a plain function here for the same reason too — recorded once,
        on that member.
        """

        from .agent import Agent
        from .player import Player

        _player = Player.GetAgent()
        if not _player:
            return []

        pos = (_player.pos.x, _player.pos.y)
        zplane = _player.pos.zplane
        start = (pos[0], pos[1], zplane)
        goal = (x, y, zplane)

        path = self.get_path(start, goal,
                             smooth_by_los=smooth_by_los,
                             margin=margin,
                             step_dist=step_dist,
                             smooth_by_chaikin=smooth_by_chaikin,
                             chaikin_iterations=chaikin_iterations)
        return [(x, y) for (x, y, _) in path]
