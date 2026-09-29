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

#: The names the source's namespace class bodies declare that are **not** members: its
#: class-level attributes (``Map.py:892-895, 1066, 1407-1410, 1854-1857, 2028-2031``) and the two
#: names ``Pregame``'s body imports (``:2026``). A method-name walk does not see either, so they
#: are carried separately — which is what let them go missing here in the first place.
REFORGED_CLASS_ATTRIBUTES: dict[str, tuple[str, ...]] = {
    "MissionMap": (
        "last_right_clicked_coords",
        "last_right_clicked_timestamp",
        "last_left_clicked_coords",
        "last_left_clicked_timestamp",
        "_last_pan_offset",
    ),
    "MiniMap": (
        "last_right_clicked_coords",
        "last_right_clicked_timestamp",
        "last_left_clicked_coords",
        "last_left_clicked_timestamp",
    ),
    "WorldMap": (
        "last_right_clicked_coords",
        "last_right_clicked_timestamp",
        "last_left_clicked_coords",
        "last_left_clicked_timestamp",
    ),
    "Pregame": (
        "PreGameContextStruct",
        "LoginCharacter",
        "last_right_clicked_coords",
        "last_right_clicked_timestamp",
        "last_left_clicked_coords",
        "last_left_clicked_timestamp",
    ),
}

#: Members that answer. ``Map`` is complete: every member of the source's own surface reads or
#: acts, so this is that surface. The nested namespaces carry their own set below, because a
#: name-only set would collapse ``GetFrame`` — declared in four namespaces — into one.
IMPLEMENTED: frozenset[str] = frozenset(REFORGED_MAP_MEMBERS)


#: The nested members that answer, by qualified path. ``IMPLEMENTED`` above is a name-only set for
#: the top-level class, which is why these are carried separately: ``GetFrame``, ``GetFrameID``,
#: ``IsWindowOpen`` and ``GetZoom`` are each declared in more than one namespace, so a name-only
#: set would collapse distinct members into one. ``Pathing`` and ``Pathing.Quad`` have no entry:
#: every one of their members is still to port.
NESTED_IMPLEMENTED: frozenset[str] = frozenset(
    {
        "Map.MissionMap.GetFrame",
        "Map.MissionMap.GetFrameID",
        "Map.MissionMap.IsWindowOpen",
        "Map.MissionMap.OpenWindow",
        "Map.MissionMap.CloseWindow",
        "Map.MissionMap.GetMissionMapWindowCoords",
        "Map.MissionMap.GetMissionMapContentsCoords",
        "Map.MissionMap.GetScale",
        "Map.MissionMap.GetZoom",
        "Map.MissionMap.GetAdjustedZoom",
        "Map.MissionMap.GetCenter",
        "Map.MissionMap.GetPanOffset",
        "Map.MissionMap.GetMapScreenCenter",
        "Map.MissionMap.MapProjection.GamePosToWorldMap",
        "Map.MissionMap.MapProjection.WorldMapToGamePos",
        "Map.MissionMap.MapProjection.WorldMapToScreen",
        "Map.MissionMap.MapProjection.ScreenToWorldMap",
        "Map.MissionMap.MapProjection.GameMapToScreen",
        "Map.MissionMap.MapProjection.ScreenToGameMap",
        "Map.MissionMap.MapProjection.NormalizedScreenToScreen",
        "Map.MissionMap.MapProjection.ScreenToNormalizedScreen",
        "Map.MissionMap.MapProjection.NormalizedScreenToWorldMap",
        "Map.MissionMap.MapProjection.NormalizedScreenToGamePos",
        "Map.MissionMap.MapProjection.GamePosToNormalizedScreen",
        "Map.MissionMap.MapProjection.GamePosToScreen",
        "Map.MissionMap.MapProjection.ScreenToGamePos",
        "Map.MissionMap.MapProjection.WorldPosToMissionMapScreen",
        "Map.MissionMap.MapProjection.ScreenToWorldPos",
        "Map.MiniMap.GetFrame",
        "Map.MiniMap.GetFrameID",
        "Map.MiniMap.IsWindowOpen",
        "Map.MiniMap.OpenWindow",
        "Map.MiniMap.CloseWindow",
        "Map.MiniMap.GetWindowCoords",
        "Map.MiniMap.IsLocked",
        "Map.MiniMap.GetPanOffset",
        "Map.MiniMap.GetScale",
        "Map.MiniMap.GetRotation",
        "Map.MiniMap.GetZoom",
        "Map.MiniMap.GetMapScreenCenter",
        "Map.MiniMap.MapProjection.GamePosToWorldMap",
        "Map.MiniMap.MapProjection.WorldMapToGamePos",
        "Map.MiniMap.MapProjection.WorldMapToScreen",
        "Map.MiniMap.MapProjection.ScreenToWorldMap",
        "Map.MiniMap.MapProjection.GameMapToScreen",
        "Map.MiniMap.MapProjection.ScreenToGameMap",
        "Map.MiniMap.MapProjection.NormalizedScreenToScreen",
        "Map.MiniMap.MapProjection.ScreenToNormalizedScreen",
        "Map.MiniMap.MapProjection.NormalizedScreenToWorldMap",
        "Map.MiniMap.MapProjection.NormalizedScreenToGamePos",
        "Map.MiniMap.MapProjection.GamePosToNormalizedScreen",
        "Map.MiniMap.MapProjection.GamePosToScreen",
        "Map.MiniMap.MapProjection.ScreenToGamePos",
        "Map.MiniMap.MapProjection.WorldPosToMiniMapScreen",
        "Map.MiniMap.MapProjection.ScreenToWorldPos",
        "Map.MiniMap.MapProjection.ComputedPathingGeometryToScreen",
        "Map.WorldMap.GetFrameID",
        "Map.WorldMap.GetFrame",
        "Map.WorldMap.IsWindowOpen",
        "Map.WorldMap.OpenWindow",
        "Map.WorldMap.CloseWindow",
        "Map.WorldMap.GetWindowCoords",
        "Map.WorldMap.GetZoom",
        "Map.WorldMap.GetParams",
        "Map.WorldMap.GetExtraData",
        "Map.Pregame.GetFrameID",
        "Map.Pregame.GetFrame",
        "Map.Pregame.IsWindowOpen",
        "Map.Pregame.GetChosenCharacterIndex",
        "Map.Pregame.GetContextStruct",
        "Map.Pregame.GetCharList",
        "Map.Pregame.GetAvailableCharacterList",
        "Map.Pregame.InCharacterSelectScreen",
        "Map.Pregame.LogoutToCharacterSelect",
        "Map.Pathing.GetPathingMaps",
        "Map.Pathing.GetPathingMapsRaw",
        "Map.Pathing.ClearPathingCache",
        "Map.Pathing.ForceReloadNavMesh",
        "Map.Pathing.GetAvailableMapIds",
        "Map.Pathing.GetSpawns",
        "Map.Pathing.GetTravelPortals",
        "Map.Pathing.GetComputedGeometry",
        "Map.Pathing.GetScreenComputedGeometry",
        "Map.Pathing.GetShiftedComputedGeometry",
        "Map.Pathing.GetshiftedScreenComputedGeometry",
        "Map.Pathing._point_in_quad",
        "Map.Pathing.GetMapQuads",
        "Map.Pathing.IsPointInPathing",
        "Map.Pathing.IsScreenPointInPathing",
        "Map.Pathing.Quad.__init__",
        "Map.Pathing.Quad.GetPoints",
        "Map.Pathing.Quad.GetScreenPoints",
        "Map.Pathing.Quad.GetShiftedPoints",
        "Map.Pathing.Quad.GetShiftedScreenPoints",
    }
)

#: Members that reach something this port does not have and cannot build: the client's own
#: in-process ImGui (``PyImGui.get_io()``, which ``Frame.is_mouse_over``/``Frame.io_events``
#: read and which nothing installs here) and the injected overlay module
#: (``PyOverlay.Overlay()``). These refuse permanently, so each one is called here to prove
#: it names itself instead of returning a value.
PERMANENT_REFUSALS: tuple[tuple[str, object], ...] = (
    ("MissionMap.IsMouseOver", Map.MissionMap.IsMouseOver),
    ("MissionMap.GetLastClickCoords", Map.MissionMap.GetLastClickCoords),
    (
        "MissionMap.GetLastRightClickCoords",
        Map.MissionMap.GetLastRightClickCoords,
    ),
    ("MiniMap.IsMouseOver", Map.MiniMap.IsMouseOver),
    ("MiniMap.GetLastClickCoords", Map.MiniMap.GetLastClickCoords),
    ("MiniMap.GetLastRightClickCoords", Map.MiniMap.GetLastRightClickCoords),
    ("WorldMap.IsMouseOver", Map.WorldMap.IsMouseOver),
    ("WorldMap.GetLastClickCoords", Map.WorldMap.GetLastClickCoords),
    ("WorldMap.GetLastRightClickCoords", Map.WorldMap.GetLastRightClickCoords),
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
                nested_declared.update(REFORGED_CLASS_ATTRIBUTES.get(path, ()))
                nested_actual = {n for n in vars(owner) if not n.startswith("_")}
                self.assertEqual(nested_actual - nested_declared, set())

    def test_every_source_class_attribute_is_declared(self) -> None:
        """The namespaces carry the state the source's own bodies declare.

        ``test_the_transcribed_surface_is_the_source_surface`` compares method names, so the
        source's class-level attributes and ``Pregame``'s two imported names were invisible to
        every check here — the defect this test exists to catch. It reads the source's class
        bodies for exactly those statements and compares them name for name.
        """

        if not REFORGED_SOURCE.exists():
            self.skipTest("The Reforged source checkout is not present.")

        tree = ast.parse(REFORGED_SOURCE.read_text(encoding="utf-8"))
        source: dict[str, list[str]] = {}

        def visit(node: ast.AST, prefix: list[str]) -> None:
            for child in node.body:  # type: ignore[attr-defined]
                if isinstance(child, ast.ClassDef):
                    names: list[str] = []
                    for statement in child.body:
                        if isinstance(statement, ast.AnnAssign) and isinstance(
                            statement.target, ast.Name
                        ):
                            names.append(statement.target.id)
                        elif isinstance(statement, ast.Assign):
                            for target in statement.targets:
                                if isinstance(target, ast.Name):
                                    names.append(target.id)
                        elif isinstance(statement, ast.ImportFrom):
                            names.extend(alias.name for alias in statement.names)
                    if names:
                        source[".".join(prefix + [child.name])] = names
                    visit(child, prefix + [child.name])

        visit(tree, [])

        for path, names in source.items():
            with self.subTest(namespace=path):
                key = path[len("Map.") :] if path.startswith("Map.") else path
                self.assertEqual(list(REFORGED_CLASS_ATTRIBUTES.get(key, ())), names)
                owner = _resolve(key)
                for name in names:
                    self.assertTrue(
                        hasattr(owner, name), f"{path}.{name} is missing"
                    )


class BlockRegionTests(unittest.TestCase):
    """The block offsets the Map family places data at must be clear of every other module's.

    ``MapMethods.Travel`` writes four words into the block's data region and hands the client that
    address; ``TravelGH`` writes four key bytes; ``Pregame.InCharacterSelectScreen`` writes the
    ``ui_state`` word the client fills in. **All three were first written at offsets that
    overlapped** ``frame_tree/frame.py``'s mouse-click packet — ``0x300`` and ``0x320`` are its
    ``_MOUSE_ACTION_OFFSET`` and ``_BUTTON_PARAM_OFFSET`` — found by reading the whole region
    instead of one module's constants. These tests are the guard.
    """

    #: Every block offset this project places data at, as ``(module, attribute, start, size)``.
    #: Transcribed, so adding a region means adding a row; the sizes are the ones the owning module
    #: uses, read from it rather than assumed.
    REGIONS: tuple[tuple[str, str, int, int], ...] = (
        ("py4gw.dat_reader", "_HASH_OFFSET/_SIZE_OFFSET", 0x000, 0x0C),
        ("py4gw.camera", "_WRITE_REGION_OFFSET", 0x200, 0x0C),
        ("py4gw.chat", "LOG_MESSAGE_OFFSET", 0x200, 0x400),
        ("py4gw.ui.preferences", "_PREFERENCE_WORD_OFFSET", 0x280, 0x04),
        ("py4gw.frame_tree.frame", "_MOUSE_ACTION_OFFSET", 0x300, 0x10),
        ("py4gw.frame_tree.frame", "_BUTTON_PARAM_OFFSET", 0x320, 0x0C),
        ("py4gw.map_methods", "_TRAVEL_OFFSET", 0xF00, 0x10),
        ("py4gw.map_methods", "_GHKEY_OFFSET", 0xF20, 0x04),
        ("py4gw.map", "_UI_STATE_OFFSET", 0xF40, 0x04),
        ("py4gw.ui_manager", "_COMPASS_POINTS_OFFSET", 0x400, 0x200),
        ("py4gw.chat", "LOG_SENDER_OFFSET", 0x600, 0x400),
        ("py4gw.ui_manager", "_KEY_MAPPINGS_OFFSET", 0x900, 0x1D4),
        ("py4gw.chat", "LOG_PARAM_OFFSET", 0xA00, 0x0C),
        ("py4gw.ui_manager", "_LABEL_ARGUMENT_OFFSET", 0xB00, 0x200),
        ("py4gw.ui_manager", "_WINDOW_POSITION_OFFSET", 0xC00, 0x14),
        ("py4gw.ui_manager", "_KEY_ACTION_OFFSET", 0xC20, 0x04),
        ("py4gw.ui_manager", "_SETTINGS_OFFSET", 0xC40, 0x40),
        ("py4gw.ui.preferences", "_STRING_ARGUMENT_OFFSET", 0xD00, 0x100),
        ("py4gw.ui_manager", "_UI_PAYLOAD_OFFSET", 0xE00, 0x40),
        ("py4gw.game_thread.packets", "PACKET_POINTER_OFFSET/_PACKET_INFLIGHT_OFFSET", 0xF50, 0x08),
        ("py4gw.merchant", "MERCHANT_OFFSET (ids, quantities, record, received id)", 0x100, 0xE8),
    )

    #: The three overlaps between modules **this suite does not own**. Recorded, not asserted away:
    #: they are real (``chat.LOG_MESSAGE_OFFSET`` spans ``0x200..0x600``, so it swallows both the
    #: camera's write region and the preference word, and the key remap table runs into the chat
    #: parameter), they are latent rather than live — the write and its consumption happen inside one
    #: synchronous call — and each belongs to the module that owns the constant. This suite reports
    #: them; changing another class's offsets is that class's change.
    KNOWN_OTHER_MODULE_OVERLAPS: tuple[tuple[str, str], ...] = (
        ("py4gw.camera._WRITE_REGION_OFFSET", "py4gw.chat.LOG_MESSAGE_OFFSET"),
        ("py4gw.chat.LOG_MESSAGE_OFFSET", "py4gw.frame_tree.frame._MOUSE_ACTION_OFFSET"),
        ("py4gw.chat.LOG_MESSAGE_OFFSET", "py4gw.frame_tree.frame._BUTTON_PARAM_OFFSET"),
        ("py4gw.chat.LOG_MESSAGE_OFFSET", "py4gw.ui.preferences._PREFERENCE_WORD_OFFSET"),
        ("py4gw.chat.LOG_MESSAGE_OFFSET", "py4gw.ui_manager._COMPASS_POINTS_OFFSET"),
        ("py4gw.chat.LOG_SENDER_OFFSET", "py4gw.ui_manager._KEY_MAPPINGS_OFFSET"),
        ("py4gw.ui_manager._KEY_MAPPINGS_OFFSET", "py4gw.chat.LOG_PARAM_OFFSET"),
        ("py4gw.ui_manager._LABEL_ARGUMENT_OFFSET", "py4gw.ui_manager._WINDOW_POSITION_OFFSET"),
        ("py4gw.ui_manager._LABEL_ARGUMENT_OFFSET", "py4gw.ui_manager._KEY_ACTION_OFFSET"),
        ("py4gw.ui_manager._LABEL_ARGUMENT_OFFSET", "py4gw.ui_manager._SETTINGS_OFFSET"),
    )

    def test_the_map_family_offsets_are_the_constants_they_claim(self) -> None:
        """The transcribed table cannot drift from the modules it describes."""

        import py4gw.map as map_module
        from py4gw import map_methods
        from py4gw.game_thread import packets as packets_module
        from py4gw import merchant as merchant_module

        self.assertEqual(map_module._UI_STATE_OFFSET, 0xF40)
        self.assertEqual(map_methods._TRAVEL_OFFSET, 0xF00)
        self.assertEqual(map_methods._GHKEY_OFFSET, 0xF20)
        self.assertEqual(packets_module.PACKET_POINTER_OFFSET, 0xF50)
        self.assertEqual(packets_module.PACKET_INFLIGHT_OFFSET, 0xF54)
        self.assertEqual(merchant_module.MERCHANT_OFFSET, 0x100)
        self.assertEqual(
            merchant_module.RECEIVED_ID_OFFSET + 4,
            merchant_module.MERCHANT_OFFSET + 0xE8,
            "the merchant span ends where the table says it does",
        )

    def test_the_map_family_sits_in_a_gap_between_other_modules(self) -> None:
        """Each Map-family span fits between the region before it and the one after it.

        Checked against the neighbouring ``start`` values rather than against guessed sizes: the
        preceding region must **end** before the Map span begins, and the Map span must end before
        the next region begins. That is the whole of "clear of everything else" and it is what the
        first version of these constants got wrong.
        """

        mine = ("py4gw.map", "py4gw.map_methods")
        others = sorted(
            (row for row in self.REGIONS if row[0] not in mine), key=lambda row: row[2]
        )

        for module, attr, start, size in (r for r in self.REGIONS if r[0] in mine):
            with self.subTest(region=f"{module}.{attr}"):
                preceding = [row for row in others if row[2] < start]
                following = [row for row in others if row[2] >= start]
                if preceding:
                    p_module, p_attr, p_start, p_size = max(preceding, key=lambda r: r[2])
                    self.assertLessEqual(
                        p_start + p_size,
                        start,
                        f"{module}.{attr} at 0x{start:X} starts inside "
                        f"{p_module}.{p_attr} (0x{p_start:X}+0x{p_size:X})",
                    )
                if following:
                    n_module, n_attr, n_start, _n_size = min(following, key=lambda r: r[2])
                    self.assertLessEqual(
                        start + size,
                        n_start,
                        f"{module}.{attr} (0x{start:X}+0x{size:X}) runs into "
                        f"{n_module}.{n_attr} at 0x{n_start:X}",
                    )

    def test_every_span_fits_the_data_region(self) -> None:
        """``shared_block.py:113`` bounds the region at 4096 bytes and refuses what runs past it."""

        for module, attr, start, size in self.REGIONS:
            with self.subTest(region=f"{module}.{attr}"):
                self.assertLessEqual(start + size, 4096)

    def test_the_other_modules_overlaps_are_the_recorded_ones(self) -> None:
        """The set of overlaps outside this family has not grown.

        A new one appearing here means a module changed its region without checking the rest of the
        block — the same mistake these three constants made on their first write.
        """

        spans = sorted(self.REGIONS, key=lambda row: row[2])
        found: set[tuple[str, str]] = set()
        for index, (module_a, attr_a, start_a, size_a) in enumerate(spans):
            for module_b, attr_b, start_b, _size_b in spans[index + 1 :]:
                if start_b < start_a + size_a:
                    found.add((f"{module_a}.{attr_a}", f"{module_b}.{attr_b}"))
                else:
                    break

        self.assertEqual(found, set(self.KNOWN_OTHER_MODULE_OVERLAPS))


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
        in ``IMPLEMENTED`` must have a body that raises ``_unported``.
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
                and first.exc.func.id == "_unported"
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
        implemented_paths.update(NESTED_IMPLEMENTED)
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
        self.assertEqual(len(implemented_paths), 168)


if __name__ == "__main__":
    unittest.main(verbosity=2)
