"""Offline tests for the ported ``Map`` surface.

The first test is the important one: it asserts that every member of Reforged's
``Py4GWCoreLib/Map.py`` -- including its five nested namespaces and the two nested
projections -- exists here with the same spelling and the same nesting. It fails
the moment a member is dropped, which is the whole point of "port the class";
nothing else in the suite would notice a missing member.

The nesting matters as much as the names: Reforged reaches these as
``Map.MissionMap.MapProjection.GamePosToWorldMap``, so a flat port that happens to
have the same 178 names is still wrong.

The rest pin two things that must not drift: which members actually read the
client, and which members refuse. A member that is declared but not implemented
must refuse -- never return a plausible value.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

from py4gw import Map

REFORGED_SOURCE = Path(r"C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib\Map.py")

#: Members of Reforged's ``Map`` class, transcribed in source order.
REFORGED_MAP_MEMBERS = (
    "IsMapDataLoaded",
    "GetInstanceType",
    "GetInstanceTypeName",
    "IsOutpost",
    "IsExplorable",
    "IsMapLoading",
    "IsObservingMatch",
    "IsMapReady",
    "GetMapID",
    "GetOutpostIDs",
    "GetOutpostNames",
    "GetMapName",
    "GetMapIDByName",
    "GetBaseMapID",
    "GetAllMapVariants",
    "IsMapIDMatch",
    "GetInstanceUptime",
    "GetRegion",
    "GetRegionType",
    "GetDistrict",
    "GetLanguage",
    "GetAmountOfPlayersInInstance",
    "GetMaxPartySize",
    "GetMinPartySize",
    "GetMinPlayerSize",
    "GetMaxPlayerSize",
    "GetFoesKilled",
    "GetFoesToKill",
    "IsVanquishCompleted",
    "IsInCinematic",
    "GetCampaign",
    "GetContinent",
    "HasEnterChallengeButton",
    "IsOnWorldMap",
    "IsPVP",
    "IsGuildHall",
    "IsVanquishable",
    "IsVanquishComplete",
    "IsMapUnlocked",
    "GetFlags",
    "GetMinLevel",
    "GetMaxLevel",
    "GetThumbnailID",
    "GetControlledOutpostID",
    "GetFractionMission",
    "GetNeededPQ",
    "HasMissionMapsTo",
    "GetMissionMapsTo",
    "GetIconPosition",
    "GetIconStartPosition",
    "GetIconStartDupePosition",
    "GetIconEndPosition",
    "GetIconEndDupePosition",
    "GetFileID",
    "GetMissionChronology",
    "GetHAChronology",
    "GetNameID",
    "GetDescriptionID",
    "GetFileID1",
    "GetFileID2",
    "IsUnlockable",
    "GetUnloadedMapInfo",
    "IsEnteringChallenge",
    "GetMapWorldMapBounds",
    "GetMapBoundaries",
    "SkipCinematic",
    "Travel",
    "TravelToDistrict",
    "TravelToRegion",
    "TravelGH",
    "LeaveGH",
    "EnterChallenge",
    "CancelEnterChallenge",
    "ConfirmEnterChallenge",
)

REFORGED_MISSIONMAP_MEMBERS = (
    "GetFrame",
    "GetFrameID",
    "IsWindowOpen",
    "OpenWindow",
    "CloseWindow",
    "IsMouseOver",
    "GetLastClickCoords",
    "GetLastRightClickCoords",
    "GetMissionMapWindowCoords",
    "GetMissionMapContentsCoords",
    "GetScale",
    "GetZoom",
    "GetAdjustedZoom",
    "GetCenter",
    "GetPanOffset",
    "GetMapScreenCenter",
)

REFORGED_MISSIONMAP_PROJECTION_MEMBERS = (
    "GamePosToWorldMap",
    "WorldMapToGamePos",
    "WorldMapToScreen",
    "ScreenToWorldMap",
    "GameMapToScreen",
    "ScreenToGameMap",
    "NormalizedScreenToScreen",
    "ScreenToNormalizedScreen",
    "NormalizedScreenToWorldMap",
    "NormalizedScreenToGamePos",
    "GamePosToNormalizedScreen",
    "GamePosToScreen",
    "ScreenToGamePos",
    "WorldPosToMissionMapScreen",
    "ScreenToWorldPos",
)

REFORGED_MINIMAP_MEMBERS = (
    "GetFrame",
    "GetFrameID",
    "IsWindowOpen",
    "OpenWindow",
    "CloseWindow",
    "IsMouseOver",
    "GetLastClickCoords",
    "GetLastRightClickCoords",
    "GetWindowCoords",
    "IsLocked",
    "GetPanOffset",
    "GetScale",
    "GetRotation",
    "GetZoom",
    "GetMapScreenCenter",
)

REFORGED_MINIMAP_PROJECTION_MEMBERS = (
    "GamePosToWorldMap",
    "WorldMapToGamePos",
    "WorldMapToScreen",
    "ScreenToWorldMap",
    "GameMapToScreen",
    "ScreenToGameMap",
    "NormalizedScreenToScreen",
    "ScreenToNormalizedScreen",
    "NormalizedScreenToWorldMap",
    "NormalizedScreenToGamePos",
    "GamePosToNormalizedScreen",
    "GamePosToScreen",
    "ScreenToGamePos",
    "WorldPosToMiniMapScreen",
    "ScreenToWorldPos",
    "ComputedPathingGeometryToScreen",
)

REFORGED_WORLDMAP_MEMBERS = (
    "GetFrameID",
    "GetFrame",
    "IsWindowOpen",
    "OpenWindow",
    "CloseWindow",
    "IsMouseOver",
    "GetLastClickCoords",
    "GetLastRightClickCoords",
    "GetWindowCoords",
    "GetZoom",
    "GetParams",
    "GetExtraData",
)

REFORGED_PREGAME_MEMBERS = (
    "GetFrameID",
    "GetFrame",
    "IsWindowOpen",
    "GetChosenCharacterIndex",
    "GetContextStruct",
    "GetCharList",
    "GetAvailableCharacterList",
    "InCharacterSelectScreen",
    "LogoutToCharacterSelect",
)

REFORGED_PATHING_MEMBERS = (
    "GetPathingMaps",
    "GetPathingMapsRaw",
    "ClearPathingCache",
    "ForceReloadNavMesh",
    "GetAvailableMapIds",
    "GetSpawns",
    "GetTravelPortals",
    "WorldToScreen",
    "GetComputedGeometry",
    "GetScreenComputedGeometry",
    "GetShiftedComputedGeometry",
    "GetshiftedScreenComputedGeometry",
    "_point_in_quad",
    "GetMapQuads",
    "IsPointInPathing",
    "IsScreenPointInPathing",
)

REFORGED_QUAD_MEMBERS = (
    "__init__",
    "GetPoints",
    "GetScreenPoints",
    "GetShiftedPoints",
    "GetShiftedScreenPoints",
)

#: ``nested path -> members``, in the source's own nesting.
NESTED: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("MissionMap", REFORGED_MISSIONMAP_MEMBERS),
    ("MissionMap.MapProjection", REFORGED_MISSIONMAP_PROJECTION_MEMBERS),
    ("MiniMap", REFORGED_MINIMAP_MEMBERS),
    ("MiniMap.MapProjection", REFORGED_MINIMAP_PROJECTION_MEMBERS),
    ("WorldMap", REFORGED_WORLDMAP_MEMBERS),
    ("Pregame", REFORGED_PREGAME_MEMBERS),
    ("Pathing", REFORGED_PATHING_MEMBERS),
    ("Pathing.Quad", REFORGED_QUAD_MEMBERS),
)

#: Class names the source nests, which are therefore not "extra" public names.
NESTED_CLASS_NAMES: tuple[str, ...] = (
    "MissionMap",
    "MiniMap",
    "WorldMap",
    "Pregame",
    "Pathing",
    "MapProjection",
    "Quad",
)

#: Members that read the client today. Everything else must refuse.
IMPLEMENTED: frozenset[str] = frozenset(
    {
        "IsMapDataLoaded",
        "GetInstanceType",
        "GetInstanceTypeName",
        "IsOutpost",
        "IsExplorable",
        "IsMapLoading",
        "IsObservingMatch",
        "IsMapReady",
        "GetMapID",
        "GetRegionType",
        "GetMaxPartySize",
        "GetMinPartySize",
        "GetMinPlayerSize",
        "GetMaxPlayerSize",
        "IsInCinematic",
        "GetCampaign",
        "GetContinent",
        "HasEnterChallengeButton",
        "IsOnWorldMap",
        "IsPVP",
        "IsGuildHall",
        "IsVanquishable",
        "GetFlags",
        "GetMinLevel",
        "GetMaxLevel",
        "GetThumbnailID",
        "GetControlledOutpostID",
        "GetFractionMission",
        "GetNeededPQ",
        "HasMissionMapsTo",
        "GetMissionMapsTo",
        "GetIconPosition",
        "GetIconStartPosition",
        "GetIconStartDupePosition",
        "GetIconEndPosition",
        "GetIconEndDupePosition",
        "GetFileID",
        "GetMissionChronology",
        "GetHAChronology",
        "GetNameID",
        "GetDescriptionID",
        "GetFileID1",
        "GetFileID2",
        "IsUnlockable",
    }
)

#: Members that need code inside the client. These refuse permanently, so each
#: one is called here to prove it names itself instead of returning a value.
PERMANENT_REFUSALS: tuple[tuple[str, object], ...] = (
    ("Map.SkipCinematic", Map.SkipCinematic),
    ("Map.Travel", lambda: Map.Travel(0)),
    ("Map.TravelToDistrict", lambda: Map.TravelToDistrict(0)),
    ("Map.TravelToRegion", lambda: Map.TravelToRegion(0, 0, 0)),
    ("Map.TravelGH", Map.TravelGH),
    ("Map.LeaveGH", Map.LeaveGH),
    ("Map.EnterChallenge", Map.EnterChallenge),
    ("Map.CancelEnterChallenge", Map.CancelEnterChallenge),
    ("Map.ConfirmEnterChallenge", Map.ConfirmEnterChallenge),
    ("MissionMap.OpenWindow", Map.MissionMap.OpenWindow),
    ("MissionMap.CloseWindow", Map.MissionMap.CloseWindow),
    ("MissionMap.IsMouseOver", Map.MissionMap.IsMouseOver),
    ("MissionMap.GetLastClickCoords", Map.MissionMap.GetLastClickCoords),
    (
        "MissionMap.GetLastRightClickCoords",
        Map.MissionMap.GetLastRightClickCoords,
    ),
    ("MiniMap.OpenWindow", Map.MiniMap.OpenWindow),
    ("MiniMap.CloseWindow", Map.MiniMap.CloseWindow),
    ("MiniMap.IsMouseOver", Map.MiniMap.IsMouseOver),
    ("MiniMap.GetLastClickCoords", Map.MiniMap.GetLastClickCoords),
    ("MiniMap.GetLastRightClickCoords", Map.MiniMap.GetLastRightClickCoords),
    ("WorldMap.OpenWindow", Map.WorldMap.OpenWindow),
    ("WorldMap.CloseWindow", Map.WorldMap.CloseWindow),
    ("WorldMap.IsMouseOver", Map.WorldMap.IsMouseOver),
    ("WorldMap.GetLastClickCoords", Map.WorldMap.GetLastClickCoords),
    ("WorldMap.GetLastRightClickCoords", Map.WorldMap.GetLastRightClickCoords),
    ("Pregame.InCharacterSelectScreen", Map.Pregame.InCharacterSelectScreen),
    (
        "Pregame.LogoutToCharacterSelect",
        Map.Pregame.LogoutToCharacterSelect,
    ),
    ("Pathing.ForceReloadNavMesh", Map.Pathing.ForceReloadNavMesh),
    ("Pathing.WorldToScreen", lambda: Map.Pathing.WorldToScreen(0.0, 0.0)),
)


def _resolve(path: str) -> object:
    """Return the nested class or member named by a dotted path."""

    target: object = Map
    for part in path.split("."):
        target = getattr(target, part)
    return target


def _source_members() -> dict[str, list[str]]:
    """Read ``Map.py`` and return its members grouped by owning class."""

    tree = ast.parse(REFORGED_SOURCE.read_text(encoding="utf-8"))
    groups: dict[str, list[str]] = {}

    def visit(node: ast.AST, prefix: list[str]) -> None:
        for child in node.body:  # type: ignore[attr-defined]
            if isinstance(child, ast.ClassDef):
                visit(child, prefix + [child.name])
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                owner = ".".join(prefix) if prefix else "Map"
                groups.setdefault(owner, []).append(child.name)

    visit(tree, [])
    return groups


class SurfaceParityTests(unittest.TestCase):
    """Verify the whole Reforged Map surface is present, nested as declared."""

    def test_the_transcribed_surface_is_the_source_surface(self) -> None:
        """Cross-check the hand-written lists against ``Map.py`` itself.

        The lists above were transcribed by hand, so they could agree with a
        wrong port. This reads the source and compares class by class, which also
        pins the nesting: ``Map.py`` declares ``MissionMap`` inside ``Map`` and
        ``MapProjection`` inside that, so a flat port fails here.
        """

        if not REFORGED_SOURCE.exists():
            self.skipTest("The Reforged source checkout is not present.")

        source = _source_members()
        self.assertEqual(source.get("Map"), list(REFORGED_MAP_MEMBERS))
        for path, members in NESTED:
            with self.subTest(namespace=path):
                self.assertEqual(source.get(f"Map.{path}"), list(members))

    def test_every_reforged_map_member_exists(self) -> None:
        """Keep the port from dropping a member Reforged scripts call."""

        for path, members in (("Map", REFORGED_MAP_MEMBERS),) + NESTED:
            owner: object = Map if path == "Map" else _resolve(path)
            for member in members:
                with self.subTest(member=f"{path}.{member}"):
                    self.assertTrue(
                        hasattr(owner, member),
                        f"{path}.{member} is missing",
                    )

    def test_namespaces_are_nested_as_the_source_nests_them(self) -> None:
        """Reforged reaches these through ``Map``, so the port must too."""

        for path in ("MissionMap", "MiniMap", "WorldMap", "Pregame", "Pathing"):
            with self.subTest(namespace=path):
                self.assertIsInstance(vars(Map).get(path), type)

        for path in (
            "MissionMap.MapProjection",
            "MiniMap.MapProjection",
            "Pathing.Quad",
        ):
            with self.subTest(namespace=path):
                self.assertIsInstance(_resolve(path), type)

    def test_no_projection_exists_at_module_level(self) -> None:
        """``MapProjection`` belongs to both map namespaces, not to the module."""

        import py4gw.map as map_module

        self.assertFalse(hasattr(map_module, "MapProjection"))
        self.assertIsNot(Map.MissionMap.MapProjection, Map.MiniMap.MapProjection)

    def test_no_public_member_beyond_the_source(self) -> None:
        """Keep the public surface from growing past Reforged's."""

        declared = set(REFORGED_MAP_MEMBERS) | set(NESTED_CLASS_NAMES[0:5])
        actual = {n for n in vars(Map) if not n.startswith("_")}
        self.assertEqual(actual - declared, set())

        for path, members in NESTED:
            with self.subTest(namespace=path):
                owner = _resolve(path)
                nested_declared = set(members)
                if path == "MissionMap" or path == "MiniMap":
                    nested_declared.add("MapProjection")
                if path == "Pathing":
                    nested_declared.add("Quad")
                nested_actual = {n for n in vars(owner) if not n.startswith("_")}
                self.assertEqual(nested_actual - nested_declared, set())


class RefusalTests(unittest.TestCase):
    """Verify members that cannot read the client refuse instead of guessing."""

    def test_permanently_refused_members_raise(self) -> None:
        """Each in-process member refuses and names itself."""

        for label, call in PERMANENT_REFUSALS:
            with self.subTest(member=label):
                with self.assertRaises(NotImplementedError) as caught:
                    call()  # type: ignore[operator]
                self.assertIn(label, str(caught.exception))

    def test_every_unimplemented_member_refuses_structurally(self) -> None:
        """No unimplemented member may return a value.

        Checked on the source of this module rather than by calling: arity varies
        per member, and a call-shaped test would drift. Every member that is not
        in ``IMPLEMENTED`` must have a body that raises ``_disabled``.
        """

        tree = ast.parse(Path(__file__).resolve().parent.parent.joinpath(
            "py4gw", "map.py"
        ).read_text(encoding="utf-8"))

        refusing: list[str] = []

        def body_raises(node: ast.AST) -> bool:
            body = list(getattr(node, "body", []))
            # Skip a leading docstring: it makes the raise the second statement.
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                body = body[1:]
            first = body[0] if body else None
            return (
                isinstance(first, ast.Raise)
                and isinstance(first.exc, ast.Call)
                and isinstance(first.exc.func, ast.Name)
                and first.exc.func.id == "_disabled"
            )

        def visit(node: ast.AST, prefix: list[str]) -> None:
            for child in node.body:  # type: ignore[attr-defined]
                if isinstance(child, ast.ClassDef):
                    visit(child, prefix + [child.name])
                elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if child.name.startswith("_") and child.name not in {
                        "_point_in_quad",
                        "__init__",
                    }:
                        continue
                    if body_raises(child):
                        refusing.append(".".join(prefix + [child.name]))

        visit(tree, [])

        # Compare qualified paths, not bare names: ``GetFrame`` is declared in
        # four namespaces and ``GetScale`` in two, so a name-only set would
        # collapse distinct members into one.
        every_path = {f"Map.{name}" for name in REFORGED_MAP_MEMBERS}
        for path, members in NESTED:
            every_path.update(f"Map.{path}.{name}" for name in members)

        implemented_paths = {f"Map.{name}" for name in IMPLEMENTED}
        refusing_paths = set(refusing)

        self.assertEqual(
            sorted(every_path - refusing_paths - implemented_paths),
            [],
            "these members are neither implemented nor refusing",
        )
        self.assertEqual(
            sorted(implemented_paths & refusing_paths),
            [],
            "these members are listed as implemented but still refuse",
        )
        self.assertEqual(len(every_path), 178)
        self.assertEqual(len(implemented_paths), 44)


if __name__ == "__main__":
    unittest.main(verbosity=2)
