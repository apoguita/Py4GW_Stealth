"""Live Guild Wars tests for the ported ``Map`` class.

Every assertion is checked against the struct the member claims to read, not
against a hardcoded value, so the test holds in any map. ``setUpClass`` refuses
to run unless the map is ready, because that is the gate the source itself
applies before reading map data.

The 44 members covered here are the ones that read the client. The rest of
``Map``'s surface is declared and refuses; that is pinned offline in
``test_map_offline.py``, and the staged plan is ``docs/MAP_PORT.md``.

Run it from the project directory while Guild Wars is running::

    python -m unittest tests.test_map -v
"""

from __future__ import annotations

import unittest

import py4gw
from py4gw.client import ConnectedClient
from py4gw.context.char_context import CharContextStruct
from py4gw.context.gw_context import GWContext
from py4gw.context.instance_info_context import (
    AreaInfoStruct,
    InstanceInfoStruct,
)
from py4gw.map import Map

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


class LiveMapTests(unittest.TestCase):
    """Verify the working ``Map`` members against a live client."""

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

    def test_campaign_continent_and_region_type_ids_match(self) -> None:
        """The id half of each ``(id, name)`` member is the ``AreaInfo`` field."""

        self.assertEqual(Map.GetCampaign()[0], int(self.area.campaign))
        self.assertEqual(Map.GetContinent()[0], int(self.area.continent))
        self.assertEqual(Map.GetRegionType()[0], int(self.area.type))

    def test_name_halves_are_empty_until_the_tables_land(self) -> None:
        """Pin the Stage 2 gap so it cannot be mistaken for working.

        ``GetCampaign``/``GetContinent``/``GetRegionType`` return the id with an
        empty name because ``CampaignName``, ``ContinentName`` and
        ``RegionTypeName`` are not ported yet. Stage 2 ports the tables and
        replaces this test with name assertions.
        """

        self.assertEqual(Map.GetCampaign()[1], "")
        self.assertEqual(Map.GetContinent()[1], "")
        self.assertEqual(Map.GetRegionType()[1], "")

    # ── refusals stay refused while connected ─────────────────────────────

    def test_pending_members_still_refuse_while_connected(self) -> None:
        """A live client must not turn a pending member into a wrong value."""

        for member in (
            "GetOutpostIDs",
            "GetDistrict",
            "GetFoesKilled",
            "IsMapUnlocked",
            "GetMapBoundaries",
        ):
            with self.subTest(member=member):
                with self.assertRaises(NotImplementedError):
                    getattr(Map, member)()
