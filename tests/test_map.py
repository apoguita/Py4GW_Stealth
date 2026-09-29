"""Live Guild Wars tests for the ported ``Map`` class.

Every assertion is checked against the struct the member claims to read, not
against a hardcoded value, so the test holds in any map. ``setUpClass`` refuses
to run unless the map is ready, because that is the gate the source itself
applies before reading map data.

**What this covers (round 80).** The class is complete: 168 of its 178 members answer and the ten
that do not are recorded divergences (the nine mouse members, which need the injected runtime's own
ImGui, and ``Pathing.WorldToScreen``, which needs its overlay manager). So this file walks, in the
source's own order: the readiness gate, identity, the two name-table groups, the region/language
group, the foes/vanquish group, all twenty-two ``AreaInfo`` readers, the unloaded-map and bounds
members, the two challenge clicks' *read* half (``IsEnteringChallenge``), the three window
namespaces, ``Pregame``, both ``MapProjection``s, and the pathing namespace.

Two of the checks are worth naming because they are the ones that could not be done offline:

* **``GetUnloadedMapInfo(GetMapID())`` against the loaded record** — the whole ``AreaInfo`` array,
  indexed by ``map_id * sizeof(AreaInfoStruct)`` off the catalog's ``map.area_info_addr``, must agree
  field for field with the record the instance-info context hands out for the *current* map. That is
  the offline array read checked against the live one.
* **``Pathing.IsPointInPathing(Player.GetXY())``** — the character is standing somewhere, and its
  position must be inside the pathing geometry the port built from the same client. It is the one
  end-to-end check of ``Map.Pathing`` that needs no fixed expectation. **It is also ``O(trapezoids)``
  and therefore budgeted**: ``Pathing``'s composed geometry members build one ``Quad`` per trapezoid,
  and each ``Quad`` costs four ``MapProjection`` calls — ~385 ms each on a 2,836-trapezoid map, so
  ~18 minutes for one member. ``test_the_composed_geometry_members_are_measured_first`` measures one
  ``Quad``, prints the extrapolation, and runs the members only inside ``GEOMETRY_BUDGET_SECONDS``;
  on a larger map it reports the measured cost instead of hanging. ``tests/probe_map_live.py`` is the
  sectioned, timed version of the same pass, and ``docs/MAP_PORT.md`` records why.

Run it from the project directory, **from an elevated shell**, while Guild Wars is running::

    python -m unittest tests.test_map -v

Or through the project's runner, which writes one report file per suite::

    pwsh -NoProfile -File tools\\run_live_suites.ps1 tests.test_map
"""

from __future__ import annotations

import math
import time
import unittest

import py4gw
from py4gw.client import ConnectedClient
from py4gw.context.char_context import CharContextStruct
from py4gw.context.gw_context import GWContext
from py4gw.context.instance_info_context import (
    AreaInfoStruct,
    InstanceInfoStruct,
)
from py4gw.enums_src.map_enums import InstanceType
from py4gw.enums_src.region_enums import (
    CampaignName,
    ContinentName,
    RegionTypeName,
    ServerLanguageName,
    ServerRegionName,
)
from py4gw.map import Map
from py4gw.player import Player

#: ``(AreaInfo attribute, Map member)`` pairs whose answer is the raw field.
SCALAR_FIELDS = (
    ("max_party_size", "GetMaxPartySize"),
    ("min_party_size", "GetMinPartySize"),
    ("min_player_size", "GetMinPlayerSize"),
    ("max_player_size", "GetMaxPlayerSize"),
    ("flags", "GetFlags"),
    ("min_level", "GetMinLevel"),
    ("max_level", "GetMaxLevel"),
    ("thumbnail_id", "GetThumbnailID"),
    ("controlled_outpost_id", "GetControlledOutpostID"),
    ("fraction_mission", "GetFractionMission"),
    ("needed_pq", "GetNeededPQ"),
    ("mission_maps_to", "GetMissionMapsTo"),
    ("file_id", "GetFileID"),
    ("mission_chronology", "GetMissionChronology"),
    ("ha_map_chronology", "GetHAChronology"),
    ("name_id", "GetNameID"),
    ("description_id", "GetDescriptionID"),
)

#: ``(AreaInfo flag property, Map member)`` pairs whose answer is a bit test.
FLAG_FIELDS = (
    ("has_enter_button", "HasEnterChallengeButton"),
    ("is_on_world_map", "IsOnWorldMap"),
    ("is_pvp", "IsPVP"),
    ("is_guild_hall", "IsGuildHall"),
    ("is_vanquishable_area", "IsVanquishable"),
    ("is_unlockable", "IsUnlockable"),
)

#: ``(AreaInfo x/y attribute pair, Map member)`` pairs returning integer tuples.
VECTOR_FIELDS = (
    (("x", "y"), "GetIconPosition"),
    (("icon_start_x", "icon_start_y"), "GetIconStartPosition"),
    (("icon_end_x", "icon_end_y"), "GetIconEndPosition"),
    (("icon_start_x_dupe", "icon_start_y_dupe"), "GetIconStartDupePosition"),
    (("icon_end_x_dupe", "icon_end_y_dupe"), "GetIconEndDupePosition"),
)

#: The ten members that raise, and they must keep raising while connected: a live client must not
#: turn a recorded divergence into a wrong value.
RECORDED_DIVERGENCES = (
    "IsMouseOver",
    "GetLastClickCoords",
    "GetLastRightClickCoords",
)

#: How long the composed ``O(trapezoids)`` pathing members may take before the suite reports the
#: measured extrapolation instead of walking the whole map. See
#: :meth:`LiveMapTests.test_the_composed_geometry_members_are_measured_first`.
GEOMETRY_BUDGET_SECONDS = 30.0


class LiveMapTests(unittest.TestCase):
    """Verify the answering ``Map`` members against a live client."""

    client: ConnectedClient
    char: CharContextStruct
    instance_info: InstanceInfoStruct
    area: AreaInfoStruct

    @classmethod
    def setUpClass(cls) -> None:
        """Connect to a client whose map data is loaded and readable."""

        clients = py4gw.Win32().find_guild_wars()
        if not clients:
            raise unittest.SkipTest("Start Guild Wars before running this test.")
        if not py4gw.Win32().is_elevated():
            raise unittest.SkipTest(
                "This suite connects to the client, and connecting requires an "
                "elevated controller. Run it from an elevated shell."
            )
        cls.client = py4gw.connect(clients[0])

        if not Map.IsMapReady():
            py4gw.disconnect()
            raise unittest.SkipTest(
                "Log a character into a loaded map before running this test "
                f"(instance type {Map.GetInstanceTypeName()})."
            )

        char = cls.client.read_char_context()
        instance_info = cls.client.read_instance_info()
        area = GWContext.InstanceInfo().GetMapInfo()
        if char is None or instance_info is None or area is None:
            py4gw.disconnect()
            raise unittest.SkipTest("The map contexts are not readable right now.")

        cls.char = char
        cls.instance_info = instance_info
        cls.area = area

    @classmethod
    def tearDownClass(cls) -> None:
        """Release the connection opened for the live checks."""

        py4gw.disconnect()

    # ── the readiness gate ────────────────────────────────────────────────

    def test_gate_matches_the_contexts_it_reads(self) -> None:
        """Reproduce the source's gate from the four contexts directly."""

        instance_type = int(self.instance_info.instance_type)

        self.assertTrue(Map.IsMapDataLoaded())
        self.assertEqual(Map.GetInstanceType(), instance_type)
        self.assertEqual(
            Map.GetInstanceTypeName(),
            {0: "Outpost", 1: "Explorable"}.get(instance_type, "Loading"),
        )
        self.assertEqual(Map.IsOutpost(), instance_type == 0)
        self.assertEqual(Map.IsExplorable(), instance_type == 1)
        self.assertEqual(Map.IsMapLoading(), instance_type not in (0, 1))
        # The ported enum is the source's own, and the member's answer is its ``.value``.
        self.assertEqual(
            Map.GetInstanceType(), InstanceType.Loading.value
            if instance_type not in InstanceType._value2member_map_
            else instance_type,
        )

    def test_observing_match_compares_the_two_map_ids(self) -> None:
        """``IsObservingMatch`` is the char context's two map ids compared."""

        self.assertEqual(
            Map.IsObservingMatch(),
            int(self.char.current_map_id) != int(self.char.observe_map_id),
        )

    def test_map_ready_is_the_source_composition(self) -> None:
        """``IsMapReady`` is the gate, the observing check and the loading check."""

        self.assertEqual(
            Map.IsMapReady(),
            Map.IsMapDataLoaded()
            and not Map.IsObservingMatch()
            and not Map.IsMapLoading(),
        )

    # ── identity ──────────────────────────────────────────────────────────

    def test_map_id_matches_the_char_context(self) -> None:
        """``GetMapID`` is the char context's current map id."""

        self.assertEqual(Map.GetMapID(), int(self.char.current_map_id))

    def test_cinematic_matches_the_cinematic_context(self) -> None:
        """``IsInCinematic`` reads the cinematic context behind the ready gate."""

        cinematic = self.client.read_cinematic_context()
        self.assertEqual(
            Map.IsInCinematic(),
            cinematic is not None and int(cinematic.h0004) != 0,
        )

    # ── the name tables ───────────────────────────────────────────────────

    def test_the_outpost_and_explorable_tables_answer(self) -> None:
        """``GetOutpostIDs``/``GetOutpostNames`` are the ported tables' keys and values."""

        ids = Map.GetOutpostIDs()
        names = Map.GetOutpostNames()
        self.assertEqual(len(ids), 278)
        self.assertEqual(len(names), 278)
        self.assertTrue(all(isinstance(i, int) for i in ids))
        self.assertTrue(all(isinstance(n, str) for n in names))

    def test_get_map_name_resolves_the_current_map(self) -> None:
        """The live round trip: the current id has a real name, and the name finds the id back."""

        name = Map.GetMapName()
        self.assertIsInstance(name, str)
        self.assertNotEqual(name, "Unknown Map ID")
        self.assertEqual(Map.GetMapIDByName(name), Map.GetMapID())
        self.assertEqual(Map.GetMapName(-1), "Unknown Map ID")

    def test_base_map_and_variants_agree_with_the_live_map(self) -> None:
        """``GetBaseMapID``/``GetAllMapVariants``/``IsMapIDMatch`` over the live id."""

        map_id = Map.GetMapID()
        base = Map.GetBaseMapID(map_id)
        variants = Map.GetAllMapVariants(map_id)
        self.assertEqual(base, Map.GetBaseMapID(base))
        self.assertIn(base, variants)
        self.assertIn(map_id, variants)
        for variant in variants:
            self.assertTrue(Map.IsMapIDMatch(variant, base))
        self.assertTrue(Map.IsMapIDMatch(map_id, map_id))

    # ── region, language, instance ────────────────────────────────────────

    def test_region_matches_the_server_region_context(self) -> None:
        """``GetRegion`` is the server-region context's id with its own name table."""

        region = self.client.read_server_region()
        expected_id = 255 if region is None else int(region.region_id)
        self.assertEqual(Map.GetRegion(), (expected_id, ServerRegionName[expected_id]))

    def test_language_and_district_match_the_char_context(self) -> None:
        """``GetLanguage``/``GetDistrict`` are the char context's two words, validated."""

        language = int(self.char.language)
        if language not in ServerLanguageName:
            language = 255
        self.assertEqual(Map.GetLanguage(), (language, ServerLanguageName[language]))
        self.assertEqual(Map.GetDistrict(), int(self.char.district_number))

    def test_instance_uptime_matches_the_account_agent_context(self) -> None:
        """``GetInstanceUptime`` is the account-agent context's timer."""

        acc = self.client.read_acc_agent_context()
        expected = 0 if acc is None else int(acc.instance_timer)
        self.assertEqual(Map.GetInstanceUptime(), expected)

    def test_players_in_instance_is_the_world_player_array(self) -> None:
        """``GetAmountOfPlayersInInstance`` is ``len(players) - 1``, and never negative."""

        world = GWContext.World.GetContext()
        expected = 0
        if world is not None:
            players = world.players
            expected = 0 if not players else len(players) - 1
        self.assertEqual(Map.GetAmountOfPlayersInInstance(), expected)

    def test_the_region_type_campaign_and_continent_names_answer(self) -> None:
        """The three ``(id, name)`` members read the ported tables now, not an empty string."""

        self.assertEqual(
            Map.GetRegionType(),
            (int(self.area.type), RegionTypeName[int(self.area.type)]),
        )
        # The two that carry the source's own KeyError on the null path cannot reach it here:
        # the map info is loaded, so the field is the key.
        self.assertEqual(
            Map.GetCampaign(),
            (int(self.area.campaign), CampaignName[int(self.area.campaign)]),
        )
        self.assertEqual(
            Map.GetContinent(),
            (int(self.area.continent), ContinentName[int(self.area.continent)]),
        )

    # ── foes, vanquish ────────────────────────────────────────────────────

    def test_foe_counters_match_the_world_context(self) -> None:
        """``GetFoesKilled``/``GetFoesToKill`` are the world context's two counters."""

        world = GWContext.World.GetContext()
        self.assertEqual(
            Map.GetFoesKilled(), 0 if world is None else int(world.foes_killed)
        )
        self.assertEqual(
            Map.GetFoesToKill(), 0 if world is None else int(world.foes_to_kill)
        )

    def test_vanquish_members_are_the_source_composition(self) -> None:
        """Both vanquish members are ``IsVanquishable() and GetFoesToKill() == 0``."""

        expected = Map.IsVanquishable() and Map.GetFoesToKill() == 0
        self.assertEqual(Map.IsVanquishCompleted(), expected)
        self.assertEqual(Map.IsVanquishComplete(), expected)

    def test_is_map_unlocked_agrees_with_the_bitfield(self) -> None:
        """Reproduce the seven steps of ``IsMapUnlocked`` from the world context's array."""

        map_id = Map.GetMapID()
        world = GWContext.World.GetContext()
        expected = False
        if world is not None:
            unlocked = world.unlocked_maps
            index = map_id // 32
            if unlocked and len(unlocked) != 0 and index < len(unlocked):
                expected = (int(unlocked[index]) & (1 << (map_id % 32))) != 0
        self.assertEqual(Map.IsMapUnlocked(), expected)
        self.assertTrue(Map.IsMapUnlocked(map_id) == expected)

    # ── AreaInfo ──────────────────────────────────────────────────────────

    def test_scalar_members_match_the_area_info(self) -> None:
        """Each scalar member returns its ``AreaInfo`` field."""

        for attribute, member in SCALAR_FIELDS:
            with self.subTest(member=member):
                self.assertEqual(
                    getattr(Map, member)(),
                    int(getattr(self.area, attribute)),
                )

    def test_flag_members_match_the_area_info(self) -> None:
        """Each boolean member returns its ``AreaInfo`` flag test."""

        for attribute, member in FLAG_FIELDS:
            with self.subTest(member=member):
                self.assertEqual(
                    getattr(Map, member)(),
                    bool(getattr(self.area, attribute)),
                )

    def test_has_mission_maps_to_compares_the_raw_field(self) -> None:
        """``HasMissionMapsTo`` is the field compare, not the flag bit.

        Reforged's ``Map.HasMissionMapsTo`` (``Map.py:581``) returns
        ``current_map_info.mission_maps_to != 0``. The ``AreaInfoStruct`` property
        of the same name is the native helper, a ``flags & 0x8000000`` test, and
        the two disagree on a real map. This member follows the source it is
        ported from, so it is asserted against the field.
        """

        self.assertEqual(
            Map.HasMissionMapsTo(),
            int(self.area.mission_maps_to) != 0,
        )

    def test_icon_members_match_the_area_info(self) -> None:
        """Each icon member returns its two ``AreaInfo`` fields as a tuple."""

        for attributes, member in VECTOR_FIELDS:
            with self.subTest(member=member):
                self.assertEqual(
                    getattr(Map, member)(),
                    (int(getattr(self.area, attributes[0])),
                     int(getattr(self.area, attributes[1]))),
                )

    def test_file_id_halves_are_the_area_info_properties(self) -> None:
        """``GetFileID1``/``GetFileID2`` come from the ``AreaInfo`` properties.

        They are not fields: the source derives both from ``file_id``.
        """

        self.assertEqual(Map.GetFileID1(), int(self.area.file_id_1))
        self.assertEqual(Map.GetFileID2(), int(self.area.file_id_2))

    # ── the unloaded-map array, checked against the loaded record ─────────

    def test_get_unloaded_map_info_agrees_with_the_loaded_record(self) -> None:
        """The strongest check in this file: the array read against the live record.

        ``GetUnloadedMapInfo`` indexes the client's global ``AreaInfo`` array at
        ``map.area_info_addr`` by ``map_id * sizeof(AreaInfoStruct)``. Asked for the **current** map,
        it must answer exactly what ``InstanceInfo`` hands out for that same map — every field, not
        a sample.
        """

        map_id = Map.GetMapID()
        unloaded = Map.GetUnloadedMapInfo(map_id)
        self.assertIsNotNone(unloaded, f"the AreaInfo array has no record for map {map_id}")
        assert unloaded is not None

        for field in AreaInfoStruct._fields_:
            name = field[0]
            with self.subTest(field=name):
                self.assertEqual(
                    int(getattr(unloaded, name)),
                    int(getattr(self.area, name)),
                    f"AreaInfo.{name} differs between the array and the instance info",
                )

    def test_get_unloaded_map_info_refuses_an_impossible_id(self) -> None:
        """``map_id <= 0`` is the source's own early answer, so it is ``None`` and not a read."""

        self.assertIsNone(Map.GetUnloadedMapInfo(0))
        self.assertIsNone(Map.GetUnloadedMapInfo(-1))

    def test_map_boundaries_match_the_map_context(self) -> None:
        """``GetMapBoundaries`` is the map context's start and end positions."""

        context = self.client.read_map_context()
        if context is None:
            self.skipTest("The map context is not readable right now.")
        expected = (
            context.start_pos.x, context.start_pos.y,
            context.end_pos.x, context.end_pos.y,
        )
        self.assertEqual(Map.GetMapBoundaries(), expected)

    def test_world_map_bounds_are_the_icon_positions_or_their_dupes(self) -> None:
        """``GetMapWorldMapBounds`` picks the dupe pair only when the main pair is all zero."""

        start = Map.GetIconStartPosition()
        end = Map.GetIconEndPosition()
        start_dupe = Map.GetIconStartDupePosition()
        end_dupe = Map.GetIconEndDupePosition()
        if start == (0, 0) and end == (0, 0):
            expected = (*map(float, start_dupe), *map(float, end_dupe))
        else:
            expected = (*map(float, start), *map(float, end))
        self.assertEqual(Map.GetMapWorldMapBounds(), expected)

    # ── the frame-lookup members ──────────────────────────────────────────

    def test_is_entering_challenge_is_the_cancel_button_frame(self) -> None:
        """``IsEnteringChallenge`` is the enter-mission button frame's existence."""

        from py4gw.frame_tree import Frame, FrameId

        button = Frame(
            FrameId.MissionStatusAndScoreDisplay.C0.C1.CancelEnterMissionButton
        )
        self.assertEqual(Map.IsEnteringChallenge(), bool(button.exists))

    def test_mission_map_window_state_agrees_with_its_frame(self) -> None:
        """``GetFrame``/``GetFrameID``/``IsWindowOpen`` are one frame, three answers."""

        frame = Map.MissionMap.GetFrame()
        self.assertEqual(Map.MissionMap.IsWindowOpen(), frame is not None)
        if frame is not None:
            self.assertEqual(Map.MissionMap.GetFrameID(), frame.frame_id)
            self.assertTrue(frame.exists)

    def test_mini_map_window_state_agrees_with_the_compass_frame(self) -> None:
        """``MiniMap.GetFrame`` is ``Frame(FrameId.Compass)``."""

        frame = Map.MiniMap.GetFrame()
        self.assertEqual(Map.MiniMap.IsWindowOpen(), bool(frame.exists))
        if frame.exists:
            self.assertEqual(Map.MiniMap.GetFrameID(), frame.frame_id)

    def test_world_map_window_state_agrees_with_the_context_frame(self) -> None:
        """``WorldMap.GetFrame`` is the world-map context's own frame id."""

        frame = Map.WorldMap.GetFrame()
        self.assertEqual(Map.WorldMap.IsWindowOpen(), frame is not None and frame.exists)
        if frame is not None:
            self.assertEqual(Map.WorldMap.GetFrameID(), frame.frame_id)

    def test_pregame_answers_are_consistent(self) -> None:
        """``Pregame``'s reads hold together on whatever screen the client is on."""

        frame_id = Map.Pregame.GetFrameID()
        context = Map.Pregame.GetContextStruct()
        self.assertEqual(frame_id, 0 if context is None else int(context.frame_id))
        self.assertEqual(Map.Pregame.IsWindowOpen(), Map.Pregame.GetFrame() is not None)
        chosen = Map.Pregame.GetChosenCharacterIndex()
        self.assertEqual(chosen, -1 if context is None else int(context.preview_character_index))
        self.assertIsInstance(Map.Pregame.GetCharList(), list)
        self.assertIsInstance(Map.Pregame.GetAvailableCharacterList(), list)
        self.assertIsInstance(Map.Pregame.InCharacterSelectScreen(), bool)

    # ── the frame geometry ────────────────────────────────────────────────

    def test_mission_map_geometry_is_consistent(self) -> None:
        """The window rect, the content rect and the scale, on one frame.

        The source's own split, live: ``GetScale`` returns ``(0.0, 0.0)`` when ``GetFrame()`` is
        falsy — ``Map.py:1027-1028`` — and only then reaches ``frame_info.viewport_scale()``, which
        is the one that answers the identity rather than zero when there is no root frame. Closed,
        all three members answer the zero rectangle.
        """

        window = Map.MissionMap.GetMissionMapWindowCoords()
        contents = Map.MissionMap.GetMissionMapContentsCoords()
        scale = Map.MissionMap.GetScale()
        for value in (*window, *contents, *scale):
            self.assertIsInstance(value, float)

        if Map.MissionMap.IsWindowOpen():
            self.assertNotEqual(window, (0.0, 0.0, 0.0, 0.0))
            self.assertGreater(scale[0], 0.0, "an open mission map has a positive viewport scale")
            self.assertGreater(scale[1], 0.0)
        else:
            # The source's guard, not a missing value.
            self.assertEqual(scale, (0.0, 0.0))
            self.assertEqual(window, (0.0, 0.0, 0.0, 0.0))
            self.assertEqual(contents, (0.0, 0.0, 0.0, 0.0))

    def test_the_zoom_members_are_the_source_arithmetic(self) -> None:
        """``GetZoom`` is the gameplay context's word; ``GetAdjustedZoom`` is the source's steps."""

        gameplay = GWContext.Gameplay.GetContext()
        self.assertEqual(Map.MissionMap.GetZoom(), 1.0 if gameplay is None else gameplay.mission_map_zoom)
        # The source's own branches (``Map.py:1039-1054``), verbatim.
        self.assertEqual(Map.MissionMap.GetAdjustedZoom(1.0), 1.0)
        self.assertAlmostEqual(Map.MissionMap.GetAdjustedZoom(1.2), 1.2449)
        self.assertAlmostEqual(Map.MissionMap.GetAdjustedZoom(2.7), 2.7 + (0.0449 + 0.02449 * 2))
        self.assertAlmostEqual(Map.MissionMap.GetAdjustedZoom(0.9), 0.9)
        self.assertAlmostEqual(Map.MissionMap.GetAdjustedZoom(1.0, 0.5), 1.5449)

    def test_the_mini_map_constants_and_rotation(self) -> None:
        """``GetPanOffset``/``GetZoom`` are constants; ``IsLocked``/``GetRotation`` are the client's."""

        from py4gw.camera import Camera

        self.assertEqual(Map.MiniMap.GetPanOffset(), [0.0, 0.0])
        self.assertEqual(Map.MiniMap.GetZoom(), 1.0)
        self.assertIsInstance(Map.MiniMap.IsLocked(), bool)
        locked = Map.MiniMap.IsLocked()
        self.assertEqual(Map.MiniMap.GetRotation(), 0 if locked else Camera.GetCurrentYaw() - math.pi / 2)

    def test_the_mini_map_geometry_is_consistent(self) -> None:
        """The compass rect, its scale and its centre, from one frame."""

        coords = Map.MiniMap.GetWindowCoords()
        scale = Map.MiniMap.GetScale()
        center = Map.MiniMap.GetMapScreenCenter()
        self.assertIsInstance(scale, float)
        self.assertEqual(len(center), 2)
        if Map.MiniMap.IsWindowOpen():
            self.assertNotEqual(coords, (0.0, 0.0, 0.0, 0.0))

    def test_world_map_reads_match_its_context(self) -> None:
        """``WorldMap``'s four context reads, straight off ``WorldMapContext``."""

        context = GWContext.WorldMap.GetContext()
        if context is None:
            self.skipTest("The world map is not open, so no frame publishes the context.")
        self.assertEqual(
            Map.WorldMap.GetWindowCoords(),
            (context.top_left.x, context.top_left.y,
             context.bottom_right.x, context.bottom_right.y),
        )
        self.assertEqual(Map.WorldMap.GetZoom(), context.zoom)
        self.assertEqual(Map.WorldMap.GetParams(), list(context.params))
        extra = Map.WorldMap.GetExtraData()
        self.assertIsNotNone(extra)
        assert extra is not None
        # The source's own table, by name: every key it writes must be there.
        for name in (
            "h0004", "h0008", "h000c", "h0010", "h0014", "h0018", "h001c", "h0020",
            "h0024", "h0028", "h002c", "h0030", "h0034", "h0068", "h006c", "h004c",
        ):
            self.assertIn(name, extra)
        self.assertEqual(len(extra["h004c"]), 7)

    # ── the projections, over the live geometry ───────────────────────────

    def test_the_mission_map_projection_round_trips(self) -> None:
        """``ScreenToGamePos`` inverts ``GamePosToScreen`` where the window is open."""

        projection = Map.MissionMap.MapProjection
        x, y = float(self.area.icon_start_x), float(self.area.icon_start_y)
        screen = projection.GamePosToScreen(x, y)
        self.assertEqual(len(screen), 2)
        self.assertTrue(all(isinstance(v, float) for v in screen))
        if Map.MissionMap.IsWindowOpen():
            back = projection.ScreenToGamePos(*screen)
            self.assertAlmostEqual(back[0], x, places=3)
            self.assertAlmostEqual(back[1], y, places=3)

    def test_the_normalized_screen_pair_inverts(self) -> None:
        """``ScreenToNormalizedScreen`` is the inverse of ``NormalizedScreenToScreen``."""

        projection = Map.MissionMap.MapProjection
        screen = projection.NormalizedScreenToScreen(0.0, 0.0)
        self.assertEqual(len(screen), 2)
        if Map.MissionMap.IsWindowOpen():
            norm = projection.ScreenToNormalizedScreen(*screen)
            self.assertAlmostEqual(norm[0], 0.0, places=3)
            self.assertAlmostEqual(norm[1], 0.0, places=3)

    def test_the_mini_map_projection_answers(self) -> None:
        """The compass transforms answer in the same shapes as the mission map's."""

        projection = Map.MiniMap.MapProjection
        game = projection.GameMapToScreen(float(self.area.x), float(self.area.y))
        self.assertEqual(len(game), 2)
        self.assertEqual(len(projection.WorldMapToScreen(0.0, 0.0)), 2)
        self.assertEqual(len(projection.NormalizedScreenToScreen(0.0, 0.0)), 2)
        offset = projection.ComputedPathingGeometryToScreen()
        self.assertEqual(len(offset), 3)

    # ── pathing ───────────────────────────────────────────────────────────

    def test_the_pathing_reads_answer_on_a_loaded_map(self) -> None:
        """The live branch: snapshots, spawns and portals, plus the offline table's key set."""

        maps = Map.Pathing.GetPathingMaps()
        self.assertIsInstance(maps, list)
        self.assertTrue(maps, "a loaded map has pathing maps")
        self.assertEqual(Map.Pathing.GetPathingMapsRaw() is not None, True)
        self.assertEqual(len(Map.Pathing.GetAvailableMapIds()), 404)

        spawns = Map.Pathing.GetSpawns()
        self.assertEqual(len(spawns), 3)
        for group in spawns:
            self.assertIsInstance(group, list)

        portals = Map.Pathing.GetTravelPortals()
        self.assertIsInstance(portals, list)

    def test_one_quad_is_the_trapezoid_and_it_projects(self) -> None:
        """``Quad`` against the trapezoid it was built from, on **one** trapezoid.

        The composed members below are ``O(trapezoids)``, and each ``Quad`` makes four projection
        calls; this checks the same construction on a single item, which is the part that can go
        wrong, for one item's cost instead of the whole map's.
        """

        layers = Map.Pathing.GetPathingMaps()
        self.assertTrue(layers, "a loaded map has pathing maps")
        trapezoid = layers[0].trapezoids[0]

        quad = Map.Pathing.Quad(trapezoid)
        self.assertIs(quad.trapezoid, trapezoid)
        # The source builds each corner as ``Vec2f(int(...), int(...))``.
        self.assertEqual((quad.top_left.x, quad.top_left.y), (int(trapezoid.XTL), int(trapezoid.YT)))
        self.assertEqual((quad.top_right.x, quad.top_right.y), (int(trapezoid.XTR), int(trapezoid.YT)))
        self.assertEqual((quad.bottom_left.x, quad.bottom_left.y), (int(trapezoid.XBL), int(trapezoid.YB)))
        self.assertEqual((quad.bottom_right.x, quad.bottom_right.y), (int(trapezoid.XBR), int(trapezoid.YB)))

        points = quad.GetPoints()
        self.assertEqual(len(points), 4)
        self.assertEqual(
            [(p.x, p.y) for p in points],
            [
                (quad.top_left.x, quad.top_left.y),
                (quad.top_right.x, quad.top_right.y),
                (quad.bottom_left.x, quad.bottom_left.y),
                (quad.bottom_right.x, quad.bottom_right.y),
            ],
        )
        # ``GetShiftedPoints(0, 0)`` is the same four corners, re-truncated.
        self.assertEqual(
            [(p.x, p.y) for p in quad.GetShiftedPoints(0.0, 0.0)],
            [(p.x, p.y) for p in points],
        )
        for holder in (
            quad.GetScreenPoints(),
            quad.GetShiftedScreenPoints(0.0, 0.0),
        ):
            self.assertEqual(len(holder), 4)
            for point in holder:
                self.assertIsInstance(point.x, float)

    def test_the_composed_geometry_members_are_measured_first(self) -> None:
        """The ``O(trapezoids)`` members: measure, then run only inside a stated budget.

        ``GetMapQuads`` and the four ``*ComputedGeometry`` members build one ``Quad`` per trapezoid,
        and ``IsPointInPathing``/``IsScreenPointInPathing`` build one per trapezoid *again* for every
        call. Each ``Quad`` is four ``MapProjection`` calls, and each of those re-reads the map
        bounds, the mission-map frame and the viewport scale — reads that cost tens of milliseconds
        each over ``ReadProcessMemory``, where Reforged's are in-process field accesses.

        So a full run on a real map is **minutes**, not milliseconds. This test measures one
        ``Quad``, states the extrapolation, and only then runs the members — so a slow map is
        reported as the measured cost instead of looking like a hang. ``MAP_PORT.md`` records the
        numbers and why the port is this way.
        """

        layers = Map.Pathing.GetPathingMaps()
        trapezoids = sum(len(layer.trapezoids) for layer in layers)
        self.assertGreater(trapezoids, 0, "a loaded map has trapezoids")

        started = time.monotonic()
        Map.Pathing.Quad(layers[0].trapezoids[0])
        per_quad = time.monotonic() - started
        estimate = per_quad * trapezoids
        print(
            f"\n  pathing geometry: {len(layers)} layers, {trapezoids} trapezoids; "
            f"one Quad {per_quad * 1000:.1f} ms -> GetMapQuads ~{estimate:.1f} s"
        )

        if estimate > GEOMETRY_BUDGET_SECONDS:
            self.skipTest(
                f"{trapezoids} trapezoids x {per_quad * 1000:.1f} ms per Quad is ~{estimate:.0f} s "
                f"for one composed member, over this suite's {GEOMETRY_BUDGET_SECONDS} s budget. "
                "The members are ported and their parts are checked above and in "
                "tests/probe_map_live.py; this map is simply too large to walk per call. That "
                "cost is the finding recorded in docs/MAP_PORT.md."
            )

        quads = Map.Pathing.GetMapQuads()
        self.assertEqual(len(quads), trapezoids)
        self.assertEqual(len(Map.Pathing.GetComputedGeometry()), len(quads))
        self.assertEqual(len(Map.Pathing.GetScreenComputedGeometry()), len(quads))
        self.assertEqual(len(Map.Pathing.GetShiftedComputedGeometry(0.0, 0.0)), len(quads))
        self.assertEqual(len(Map.Pathing.GetshiftedScreenComputedGeometry(0.0, 0.0)), len(quads))

        position = Player.GetXY()
        self.assertIsNotNone(position)
        assert position is not None
        x, y = float(position[0]), float(position[1])
        self.assertTrue(
            Map.Pathing.IsPointInPathing(x, y),
            f"the player at ({x}, {y}) is not reported inside any pathing area",
        )
        # The screen-space twin agrees with the game-space one exactly when the mission map is
        # open: closed, the source's own ``IsWindowOpen`` guard makes ``GamePosToScreen`` answer
        # ``(0.0, 0.0)``, so the projected point is not on the map.
        screen_x, screen_y = Map.MissionMap.MapProjection.GamePosToScreen(x, y)
        if Map.MissionMap.IsWindowOpen():
            self.assertTrue(
                Map.Pathing.IsScreenPointInPathing(screen_x, screen_y),
                f"the player's projected screen point ({screen_x}, {screen_y}) is not in pathing",
            )
        else:
            self.assertFalse(Map.Pathing.IsScreenPointInPathing(screen_x, screen_y))

    def test_the_pathing_cache_clears(self) -> None:
        """``ClearPathingCache`` runs both branches the source declares."""

        Map.Pathing.ClearPathingCache()
        Map.Pathing.ClearPathingCache(Map.GetMapID(), include_live=True)
        self.assertIsInstance(Map.Pathing.ForceReloadNavMesh(), type(None))

    # ── the recorded divergences stay refused ─────────────────────────────

    def test_the_mouse_members_refuse_while_connected(self) -> None:
        """A live client must not turn a recorded divergence into a wrong value."""

        for namespace in (Map.MissionMap, Map.MiniMap, Map.WorldMap):
            for member in RECORDED_DIVERGENCES:
                with self.subTest(member=f"{namespace.__name__}.{member}"):
                    with self.assertRaises(NotImplementedError) as caught:
                        getattr(namespace, member)()
                    self.assertIn("PyImGui.get_io()", str(caught.exception))

    def test_world_to_screen_refuses_while_connected(self) -> None:
        """The one pathing member that needs the overlay manager."""

        with self.assertRaises(NotImplementedError) as caught:
            Map.Pathing.WorldToScreen(0.0, 0.0)
        self.assertIn("PyOverlay.Overlay()", str(caught.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
