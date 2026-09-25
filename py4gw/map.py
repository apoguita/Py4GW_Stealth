"""External port of Reforged's ``Py4GWCoreLib/Map.py``.

``Map.py`` is 2327 lines: one ``Map`` class carrying five nested namespaces and
two nested projections, 178 members in total. This module ports that surface in
the source's own shape and nesting -- ``Map.MissionMap.MapProjection`` and
``Map.MiniMap.MapProjection`` are nested, not top-level.

Members whose read works from outside ``Gw.exe`` read the client. Members whose
read does not are declared and refuse, naming what blocks them, so a ported script
fails at the call site instead of returning a wrong value. Two kinds of refusal
are distinguished in the docstrings: ``not ported yet`` (the route exists and is
scheduled) and a named in-process mechanism (the member needs code in the client
and keeps refusing until this project can run it).

Four sources only, all of them the source's own:

* the game contexts, through ``ConnectedClient.read_*``;
* the UI frame tree, for window geometry;
* the local map and region tables under ``enums_src/``;
* native ``MapMethods``.

The port is staged; ``docs/MAP_PORT.md`` is the plan and the progress record.
Nothing here is invented: see ``docs/PORTING_RULES.md``.
"""

from __future__ import annotations

from .context.gw_context import GWContext
from .context.instance_info_context import (
    AreaInfoStruct,
    InstanceType,
    InstanceTypeName,
)


def _disabled(member: str, requirement: str) -> NotImplementedError:
    """Build the error raised by a member that cannot read what it needs."""

    return NotImplementedError(
        f"Map.{member} is not available yet: {requirement}. It is declared for "
        "source parity so a ported script fails at the call site and names the "
        "missing mechanism instead of returning a wrong value."
    )


class Map:
    """Read-only port of the Reforged ``Map`` namespace class.

    Source: ``Py4GWCoreLib/Map.py``. The readiness gate, the current map
    identity and the ``AreaInfo`` metadata are working; the rest of the surface is
    declared, with each member's state recorded in its docstring.
    """

    # -- the readiness gate (source 40-118) --------------------------------
    #
    # Literal port of ``Map.py`` lines 40-118. The structure, the short-circuits
    # and the return values are the source's, so ``IsObservingMatch`` and
    # ``IsMapLoading`` answer ``True`` when the map data is not loaded, exactly as
    # the source does.

    @staticmethod
    def IsMapDataLoaded() -> bool:
        """Check if the map data is loaded. (source 42)"""

        return (
            GWContext.Map.IsValid()
            and GWContext.Char.IsValid()
            and GWContext.InstanceInfo.IsValid()
            and GWContext.World.IsValid()
        )

    @staticmethod
    def GetInstanceType() -> int:
        """Retrieve the instance type of the current map. (source 53)"""

        if (instance_info := GWContext.InstanceInfo.GetContext()) is None:
            return InstanceType.LOADING
        return (
            instance_info.instance_type
            if instance_info.instance_type in InstanceType._value2member_map_
            else InstanceType.LOADING
        )

    @staticmethod
    def GetInstanceTypeName() -> str:
        """Retrieve the instance type name of the current map. (source 65)"""

        type = Map.GetInstanceType()
        return InstanceTypeName.get(type, "Loading")

    @staticmethod
    def IsOutpost() -> bool:
        """Check if the map instance is an outpost. (source 72)"""

        if not Map.IsMapDataLoaded():
            return False
        return Map.GetInstanceType() == InstanceType.OUTPOST

    @staticmethod
    def IsExplorable() -> bool:
        """Check if the map instance is explorable. (source 80)"""

        if not Map.IsMapDataLoaded():
            return False
        return Map.GetInstanceType() == InstanceType.EXPLORABLE

    @staticmethod
    def IsMapLoading() -> bool:
        """Check if the map is in a loading phase. (source 88)"""

        if not Map.IsMapDataLoaded():
            return True

        return Map.GetInstanceType() not in (
            InstanceType.OUTPOST,
            InstanceType.EXPLORABLE,
        )

    @staticmethod
    def IsObservingMatch() -> bool:
        """Check if the character is observing a match. (source 99)"""

        if not Map.IsMapDataLoaded():
            return True

        if not (char_context := GWContext.Char.GetContext()): return False
        return char_context.current_map_id != char_context.observe_map_id

    @staticmethod
    def IsMapReady() -> bool:
        """Check if the map is ready to be handled. (source 109)"""

        return (
            Map.IsMapDataLoaded()
            and not Map.IsObservingMatch()
            and not Map.IsMapLoading()
        )

    # -- identity (source 118-125) ----------------------------------------

    @staticmethod
    def GetMapID() -> int:
        """Retrieve the ID of the current map. (source 120)"""

        if not Map.IsMapReady():
            return 0
        if not (char_context := GWContext.Char.GetContext()): return 0
        return char_context.current_map_id

    # -- name tables (source 127-250) -------------------------------------

    @staticmethod
    def GetOutpostIDs() -> list[int]:
        """Retrieve the outpost IDs. (source 128)

        Not ported yet: the ``outposts`` table from
        ``enums_src/Map_enums.py`` (278 entries) is Stage 2.
        """

        raise _disabled(
            "GetOutpostIDs", "the map and outpost name tables are not ported yet"
        )

    @staticmethod
    def GetOutpostNames() -> list[str]:
        """Retrieve the outpost names. (source 134)

        Not ported yet: same ``outposts`` table as ``GetOutpostIDs``.
        """

        raise _disabled(
            "GetOutpostNames", "the map and outpost name tables are not ported yet"
        )

    @staticmethod
    def GetMapName(mapid: int | None = None) -> str:
        """Retrieve the name of a map by its id. (source 142)

        Not ported yet: the ``outposts`` and ``explorables`` tables are Stage 2.
        """

        raise _disabled(
            "GetMapName", "the map and outpost name tables are not ported yet"
        )

    @staticmethod
    def GetMapIDByName(name: str) -> int:
        """Retrieve the id of a map by its name, case-insensitively. (source 165)

        Not ported yet: the name-to-id catalog is built from the tables, Stage 2.
        """

        raise _disabled(
            "GetMapIDByName", "the map and outpost name tables are not ported yet"
        )

    @staticmethod
    def GetBaseMapID(map_id: int = 0) -> int:
        """Get the base map id, resolving seasonal variants. (source 188)

        Not ported yet: ``map_variants_to_base`` is Stage 2.
        """

        raise _disabled(
            "GetBaseMapID", "the map variant table is not ported yet"
        )

    @staticmethod
    def GetAllMapVariants(map_id: int) -> list[int]:
        """Get every variant of a map, including the base. (source 211)

        Not ported yet: ``base_to_all_variants`` is Stage 2.
        """

        raise _disabled(
            "GetAllMapVariants", "the map variant table is not ported yet"
        )

    @staticmethod
    def IsMapIDMatch(current_map: int = 0, target_map: int = 0) -> bool:
        """Check two map ids match, accounting for seasonal variants. (source 231)

        Not ported yet: it compares base map ids, which needs the variant table
        from Stage 2.
        """

        raise _disabled(
            "IsMapIDMatch", "the map variant table is not ported yet"
        )

    # -- region, language, instance sizes (source 252-365) ----------------

    @staticmethod
    def GetInstanceUptime() -> int:
        """Retrieve the uptime of the current instance. (source 253)

        Not ported yet: the account-agent context's instance timer is Stage 3.
        """

        raise _disabled(
            "GetInstanceUptime",
            "the account-agent context's instance timer is not ported yet",
        )

    @staticmethod
    def GetRegion() -> tuple[int, str]:
        """Retrieve the region id and name of the current server region. (source 261)

        Not ported yet: the server-region context read and ``ServerRegionName``
        are Stages 2 and 3.
        """

        raise _disabled(
            "GetRegion",
            "the server-region context read and its name table are not ported yet",
        )

    @staticmethod
    def GetRegionType() -> tuple[int, str]:
        """Retrieve the region type and name of the current map. (source 274)

        The name is empty because ``RegionTypeName`` is not ported yet (Stage 2).
        """

        _unknown_region_type = 20  # Unknown
        current_map_info = GWContext.InstanceInfo().GetMapInfo()
        if current_map_info is None:
            return _unknown_region_type, ""
        return current_map_info.type, ""

    @staticmethod
    def GetDistrict() -> int:
        """Retrieve the district of the current map. (source 289)

        Not ported yet: the char context's district number is Stage 3.
        """

        raise _disabled(
            "GetDistrict",
            "the char context's district number is not ported yet",
        )

    @staticmethod
    def GetLanguage() -> tuple[int, str]:
        """Retrieve the language id and name of the current map. (source 296)

        Not ported yet: the char context's language and ``ServerLanguageName``
        are Stages 2 and 3.
        """

        raise _disabled(
            "GetLanguage",
            "the char context's language and its name table are not ported yet",
        )

    @staticmethod
    def GetAmountOfPlayersInInstance() -> int:
        """Retrieve the amount of players in the current instance. (source 320)

        Not ported yet: the world context's player array is Stage 3.
        """

        raise _disabled(
            "GetAmountOfPlayersInInstance",
            "the world context's player array is not ported yet",
        )

    @staticmethod
    def GetMaxPartySize() -> int:
        """Retrieve the maximum party size of the current map. (source 331)"""

        current_map_info = GWContext.InstanceInfo().GetMapInfo()
        if current_map_info is None:
            return 0
        return current_map_info.max_party_size

    @staticmethod
    def GetMinPartySize() -> int:
        """Retrieve the minimum party size of the current map. (source 341)"""

        current_map_info = GWContext.InstanceInfo().GetMapInfo()
        if current_map_info is None:
            return 0
        return current_map_info.min_party_size

    @staticmethod
    def GetMinPlayerSize() -> int:
        """Retrieve the minimum player size of the current map. (source 351)"""

        current_map_info = GWContext.InstanceInfo().GetMapInfo()
        if current_map_info is None:
            return 0
        return current_map_info.min_player_size

    @staticmethod
    def GetMaxPlayerSize() -> int:
        """Retrieve the maximum player size of the current map. (source 360)"""

        current_map_info = GWContext.InstanceInfo().GetMapInfo()
        if current_map_info is None:
            return 0
        return current_map_info.max_player_size

    # -- foes, vanquish, campaign, map class (source 367-516) -------------

    @staticmethod
    def GetFoesKilled() -> int:
        """Retrieve the number of foes killed in the current map. (source 369)

        Not ported yet: the world context's foe counter is Stage 3.
        """

        raise _disabled(
            "GetFoesKilled", "the world context's foe counter is not ported yet"
        )

    @staticmethod
    def GetFoesToKill() -> int:
        """Retrieve the number of foes left to kill in the current map. (source 381)

        Not ported yet: the world context's foe counter is Stage 3.
        """

        raise _disabled(
            "GetFoesToKill", "the world context's foe counter is not ported yet"
        )

    @staticmethod
    def IsVanquishCompleted() -> bool:
        """Check if the vanquish is completed. (source 393)

        Not ported yet: it needs ``GetFoesToKill``, which is Stage 3.
        """

        raise _disabled(
            "IsVanquishCompleted",
            "the world context's foe counter it reads is not ported yet",
        )

    @staticmethod
    def IsInCinematic() -> bool:
        """Check if the map is in a cinematic. (source 401)

        The source refuses to answer unless the map is ready, because the
        character context is not trustworthy during a load.
        """

        if not Map.IsMapReady():
            return False
        if not (cinematic_ctx := GWContext.Cinematic.GetContext()):
            return False
        return cinematic_ctx.h0004 != 0

    @staticmethod
    def GetCampaign() -> tuple[int, str]:
        """Retrieve the campaign id and name of the current map. (source 411)

        The name is empty because ``CampaignName`` is not ported yet (Stage 2).
        """

        not_valid = 255
        current_map_info = GWContext.InstanceInfo().GetMapInfo()
        if current_map_info is None:
            return not_valid, ""
        return current_map_info.campaign, ""

    @staticmethod
    def GetContinent() -> tuple[int, str]:
        """Retrieve the continent id and name of the current map. (source 426)

        The name is empty because ``ContinentName`` is not ported yet (Stage 2).
        """

        not_valid = 255
        current_map_info = GWContext.InstanceInfo().GetMapInfo()
        if current_map_info is None:
            return not_valid, ""
        return current_map_info.continent, ""

    @staticmethod
    def HasEnterChallengeButton() -> bool:
        """Check if the map has an enter-challenge button. (source 440)"""

        current_map_info = GWContext.InstanceInfo().GetMapInfo()
        if current_map_info is None:
            return False
        return current_map_info.has_enter_button

    @staticmethod
    def IsOnWorldMap() -> bool:
        """Check if the map is on the world map. (source 449)"""

        current_map_info = GWContext.InstanceInfo().GetMapInfo()
        if current_map_info is None:
            return False
        return current_map_info.is_on_world_map

    @staticmethod
    def IsPVP() -> bool:
        """Check if the map is a PvP map. (source 458)"""

        current_map_info = GWContext.InstanceInfo().GetMapInfo()
        if current_map_info is None:
            return False
        return current_map_info.is_pvp

    @staticmethod
    def IsGuildHall() -> bool:
        """Check if the map is a guild hall. (source 467)"""

        current_map_info = GWContext.InstanceInfo().GetMapInfo()
        if current_map_info is None:
            return False
        return current_map_info.is_guild_hall

    @staticmethod
    def IsVanquishable() -> bool:
        """Check if the map is vanquishable. (source 476)"""

        current_map_info = GWContext.InstanceInfo().GetMapInfo()
        if current_map_info is None:
            return False
        return current_map_info.is_vanquishable_area

    @staticmethod
    def IsVanquishComplete() -> bool:
        """Check if the vanquish is complete. (source 485)

        Not ported yet: it needs ``GetFoesToKill``, which is Stage 3.
        """

        raise _disabled(
            "IsVanquishComplete",
            "the world context's foe counter it reads is not ported yet",
        )

    @staticmethod
    def IsMapUnlocked(mapid: int | None = None) -> bool:
        """Check if the map is unlocked. (source 493)

        Not ported yet: the world context's unlocked-map bitfield is Stage 3.
        """

        raise _disabled(
            "IsMapUnlocked",
            "the world context's unlocked-map bitfield is not ported yet",
        )

    # -- additional AreaInfo fields (source 518-694) ----------------------

    @staticmethod
    def GetFlags() -> int:
        """Retrieve the flags of the current map. (source 520)"""

        current_map_info = GWContext.InstanceInfo().GetMapInfo()
        if current_map_info is None:
            return 0
        return current_map_info.flags

    @staticmethod
    def GetMinLevel() -> int:
        """Retrieve the minimum level of the current map. (source 528)"""

        current_map_info = GWContext.InstanceInfo().GetMapInfo()
        if current_map_info is None:
            return 0
        return current_map_info.min_level

    @staticmethod
    def GetMaxLevel() -> int:
        """Retrieve the maximum level of the current map. (source 536)"""

        current_map_info = GWContext.InstanceInfo().GetMapInfo()
        if current_map_info is None:
            return 0
        return current_map_info.max_level

    @staticmethod
    def GetThumbnailID() -> int:
        """Retrieve the thumbnail ID of the current map. (source 544)"""

        current_map_info = GWContext.InstanceInfo().GetMapInfo()
        if current_map_info is None:
            return 0
        return current_map_info.thumbnail_id

    @staticmethod
    def GetControlledOutpostID() -> int:
        """Retrieve the controlled outpost ID of the current map. (source 552)"""

        current_map_info = GWContext.InstanceInfo().GetMapInfo()
        if current_map_info is None:
            return 0
        return current_map_info.controlled_outpost_id

    @staticmethod
    def GetFractionMission() -> int:
        """Retrieve the fraction mission of the current map. (source 560)"""

        current_map_info = GWContext.InstanceInfo().GetMapInfo()
        if current_map_info is None:
            return 0
        return current_map_info.fraction_mission

    @staticmethod
    def GetNeededPQ() -> int:
        """Retrieve the needed PQ of the current map. (source 568)"""

        current_map_info = GWContext.InstanceInfo().GetMapInfo()
        if current_map_info is None:
            return 0
        return current_map_info.needed_pq

    @staticmethod
    def HasMissionMapsTo() -> bool:
        """Check if the current map has mission maps to. (source 576)"""

        current_map_info = GWContext.InstanceInfo().GetMapInfo()
        if current_map_info is None:
            return False
        return current_map_info.mission_maps_to != 0

    @staticmethod
    def GetMissionMapsTo() -> int:
        """Retrieve the mission maps to of the current map. (source 584)"""

        current_map_info = GWContext.InstanceInfo().GetMapInfo()
        if current_map_info is None:
            return 0
        return current_map_info.mission_maps_to

    @staticmethod
    def GetIconPosition() -> tuple[int, int]:
        """Retrieve the icon position of the current map. (source 592)"""

        current_map_info = GWContext.InstanceInfo().GetMapInfo()
        if current_map_info is None:
            return 0, 0
        return current_map_info.x, current_map_info.y

    @staticmethod
    def GetIconStartPosition() -> tuple[int, int]:
        """Retrieve the icon start position of the current map. (source 600)"""

        current_map_info = GWContext.InstanceInfo().GetMapInfo()
        if current_map_info is None:
            return 0, 0
        return current_map_info.icon_start_x, current_map_info.icon_start_y

    @staticmethod
    def GetIconStartDupePosition() -> tuple[int, int]:
        """Retrieve the icon start dupe position of the current map. (source 608)"""

        current_map_info = GWContext.InstanceInfo().GetMapInfo()
        if current_map_info is None:
            return 0, 0
        return current_map_info.icon_start_x_dupe, current_map_info.icon_start_y_dupe

    @staticmethod
    def GetIconEndPosition() -> tuple[int, int]:
        """Retrieve the icon end position of the current map. (source 616)"""

        current_map_info = GWContext.InstanceInfo().GetMapInfo()
        if current_map_info is None:
            return 0, 0
        return current_map_info.icon_end_x, current_map_info.icon_end_y

    @staticmethod
    def GetIconEndDupePosition() -> tuple[int, int]:
        """Retrieve the icon end dupe position of the current map. (source 624)"""

        current_map_info = GWContext.InstanceInfo().GetMapInfo()
        if current_map_info is None:
            return 0, 0
        return current_map_info.icon_end_x_dupe, current_map_info.icon_end_y_dupe

    @staticmethod
    def GetFileID() -> int:
        """Retrieve the file ID of the current map. (source 632)"""

        current_map_info = GWContext.InstanceInfo().GetMapInfo()
        if current_map_info is None:
            return 0
        return current_map_info.file_id

    @staticmethod
    def GetMissionChronology() -> int:
        """Retrieve the mission chronology of the current map. (source 640)"""

        current_map_info = GWContext.InstanceInfo().GetMapInfo()
        if current_map_info is None:
            return 0
        return current_map_info.mission_chronology

    @staticmethod
    def GetHAChronology() -> int:
        """Retrieve the HA chronology of the current map. (source 648)"""

        current_map_info = GWContext.InstanceInfo().GetMapInfo()
        if current_map_info is None:
            return 0
        return current_map_info.ha_map_chronology

    @staticmethod
    def GetNameID() -> int:
        """Retrieve the name ID of the current map. (source 656)"""

        current_map_info = GWContext.InstanceInfo().GetMapInfo()
        if current_map_info is None:
            return 0
        return current_map_info.name_id

    @staticmethod
    def GetDescriptionID() -> int:
        """Retrieve the description ID of the current map. (source 664)"""

        current_map_info = GWContext.InstanceInfo().GetMapInfo()
        if current_map_info is None:
            return 0
        return current_map_info.description_id

    @staticmethod
    def GetFileID1() -> int:
        """Retrieve the file ID 1 of the current map. (source 672)"""

        current_map_info = GWContext.InstanceInfo().GetMapInfo()
        if current_map_info is None:
            return 0
        return current_map_info.file_id1

    @staticmethod
    def GetFileID2() -> int:
        """Retrieve the file ID 2 of the current map. (source 680)"""

        current_map_info = GWContext.InstanceInfo().GetMapInfo()
        if current_map_info is None:
            return 0
        return current_map_info.file_id2

    @staticmethod
    def IsUnlockable() -> bool:
        """Check if the current map is unlockable. (source 688)"""

        current_map_info = GWContext.InstanceInfo().GetMapInfo()
        if current_map_info is None:
            return False
        return current_map_info.is_unlockable

    # -- unloaded map, challenge, bounds (source 695-739) -----------------

    @staticmethod
    def GetUnloadedMapInfo(map_id: int) -> AreaInfoStruct | None:
        """Return ``AreaInfoStruct`` for any map id, even if not loaded. (source 696)

        Not ported yet: the global ``AreaInfo`` array scan is Stage 4.
        """

        raise _disabled(
            "GetUnloadedMapInfo",
            "the global AreaInfo array scan is not ported yet",
        )

    @staticmethod
    def IsEnteringChallenge() -> bool:
        """Check if the character is entering a challenge. (source 706)

        Not ported yet: the cancel-enter-mission frame lookup is Stage 5.
        """

        raise _disabled(
            "IsEnteringChallenge",
            "the enter-challenge frame lookup is not ported yet",
        )

    @staticmethod
    def GetMapWorldMapBounds() -> tuple[float, float, float, float]:
        """Retrieve the map's bounds in world-map space. (source 714)

        Not ported yet: it composes the four ``GetIcon*Position`` readers
        (Stage 3).
        """

        raise _disabled(
            "GetMapWorldMapBounds",
            "the AreaInfo icon bounds composition is not ported yet",
        )

    @staticmethod
    def GetMapBoundaries() -> tuple[float, float, float, float]:
        """Retrieve the boundaries of the current map. (source 734)

        Not ported yet: the map context's start and end positions are Stage 3.
        """

        raise _disabled(
            "GetMapBoundaries",
            "the map context's start and end positions are not ported yet",
        )

    # -- actions (source 741-889) -----------------------------------------

    @staticmethod
    def SkipCinematic() -> None:
        """Disabled: it calls the client's own skip-cinematic function."""

        raise _disabled(
            "SkipCinematic",
            "it calls the client's own skip-cinematic function from the game thread",
        )

    @staticmethod
    def Travel(map_id: int) -> None:
        """Disabled: travel is requested through the client's own path."""

        raise _disabled(
            "Travel",
            "it asks the client to travel, which emits the CtoS packet",
        )

    @staticmethod
    def TravelToDistrict(
        map_id: int, district: int = 0, district_number: int = 0
    ) -> None:
        """Disabled: district travel is requested through the client."""

        raise _disabled(
            "TravelToDistrict",
            "it asks the client to travel, which emits the CtoS packet",
        )

    @staticmethod
    def TravelToRegion(
        map_id: int, server_region: int, district_number: int, language: int = 0
    ) -> None:
        """Disabled: region travel is requested through the client."""

        raise _disabled(
            "TravelToRegion",
            "it asks the client to travel, which emits the CtoS packet",
        )

    @staticmethod
    def TravelGH() -> None:
        """Disabled: guild-hall travel is requested through the client."""

        raise _disabled(
            "TravelGH", "it asks the client to travel to the guild hall"
        )

    @staticmethod
    def LeaveGH() -> None:
        """Disabled: leaving the guild hall is requested through the client."""

        raise _disabled("LeaveGH", "it asks the client to leave the guild hall")

    @staticmethod
    def EnterChallenge() -> None:
        """Disabled: entering a challenge is a client dialog action."""

        raise _disabled(
            "EnterChallenge", "it dispatches the enter-challenge UI message"
        )

    @staticmethod
    def CancelEnterChallenge() -> None:
        """Disabled: cancelling a challenge is a client dialog action."""

        raise _disabled(
            "CancelEnterChallenge",
            "it dispatches the cancel-enter-challenge UI message",
        )

    @staticmethod
    def ConfirmEnterChallenge() -> None:
        """Disabled: confirming a challenge is a client dialog action."""

        raise _disabled(
            "ConfirmEnterChallenge",
            "it dispatches the confirm-enter-challenge UI message",
        )

    # -- nested: the mission map (source 891-1404) ------------------------

    class MissionMap:
        """The mission-map window. Source: ``Map.py`` lines 891-1404."""

        @staticmethod
        def GetFrame():
            """The mission map frame. (source 898)

            Not ported yet: the frame lookup by context frame id, with the
            named fallback, is Stage 5.
            """

            raise _disabled(
                "MissionMap.GetFrame", "the frame lookup is not ported yet"
            )

        @staticmethod
        def GetFrameID() -> int:
            """Frame id of the mission map, from the context. (source 916)

            Not ported yet: the mission-map context's frame id is Stage 5.
            """

            raise _disabled(
                "MissionMap.GetFrameID",
                "the mission-map context's frame id is not ported yet",
            )

        @staticmethod
        def IsWindowOpen() -> bool:
            """Check if the mission map window is open. (source 923)

            Not ported yet: it reads the frame's existence (Stage 5).
            """

            raise _disabled(
                "MissionMap.IsWindowOpen", "the frame lookup is not ported yet"
            )

        @staticmethod
        def OpenWindow() -> None:
            """Disabled: it queues the open-mission-map keybind."""

            raise _disabled(
                "MissionMap.OpenWindow",
                "it queues a keybind on the client's own game thread",
            )

        @staticmethod
        def CloseWindow() -> None:
            """Disabled: the source queues the same keybind as ``OpenWindow``."""

            raise _disabled(
                "MissionMap.CloseWindow",
                "it queues a keybind on the client's own game thread",
            )

        @staticmethod
        def IsMouseOver() -> bool:
            """Disabled: it reads the client's per-frame ImGui input state."""

            raise _disabled(
                "MissionMap.IsMouseOver",
                "it reads the client's per-frame ImGui input state, which only "
                "exists with code inside Gw.exe",
            )

        @staticmethod
        def GetLastClickCoords() -> tuple[float, float]:
            """Disabled: the frame IO-event list is filled in-process."""

            raise _disabled(
                "MissionMap.GetLastClickCoords",
                "the client's frame IO-event list is filled by an in-process "
                "callback that reads ImGui, so the events cannot be observed "
                "from outside Gw.exe",
            )

        @staticmethod
        def GetLastRightClickCoords() -> tuple[float, float]:
            """Disabled: the frame IO-event list is filled in-process."""

            raise _disabled(
                "MissionMap.GetLastRightClickCoords",
                "the client's frame IO-event list is filled by an in-process "
                "callback that reads ImGui, so the events cannot be observed "
                "from outside Gw.exe",
            )

        @staticmethod
        def GetMissionMapWindowCoords() -> tuple[float, float, float, float]:
            """Get the window coordinates of the mission map. (source 1011)

            Not ported yet: the frame rect read is Stage 5.
            """

            raise _disabled(
                "MissionMap.GetMissionMapWindowCoords",
                "the frame rect read is not ported yet",
            )

        @staticmethod
        def GetMissionMapContentsCoords() -> tuple[float, float, float, float]:
            """Get the contents coordinates of the mission map. (source 1018)

            Not ported yet: the frame content-rect read is Stage 5.
            """

            raise _disabled(
                "MissionMap.GetMissionMapContentsCoords",
                "the frame content-rect read is not ported yet",
            )

        @staticmethod
        def GetScale() -> tuple[float, float]:
            """Get the scale of the mission map. (source 1025)

            Not ported yet: the frame viewport scale read is Stage 5.
            """

            raise _disabled(
                "MissionMap.GetScale",
                "the frame viewport scale read is not ported yet",
            )

        @staticmethod
        def GetZoom() -> float:
            """Get the zoom level of the mission map. (source 1032)

            Not ported yet: the gameplay context's mission-map zoom is Stage 5.
            """

            raise _disabled(
                "MissionMap.GetZoom",
                "the gameplay context's mission-map zoom is not ported yet",
            )

        @staticmethod
        def GetAdjustedZoom(_zoom: float, zoom_offset: float = 0.0) -> float:
            """Adjust the zoom level of the mission map. (source 1039)

            Not ported yet: pure arithmetic, landed with Stage 5 so it can be
            verified against a real zoom value.
            """

            raise _disabled(
                "MissionMap.GetAdjustedZoom",
                "the zoom adjustment is not ported yet",
            )

        @staticmethod
        def GetCenter() -> tuple[float, float]:
            """Get the player position coordinates of the mission map. (source 1057)

            Not ported yet: it composes the contents coordinates (Stage 5).
            """

            raise _disabled(
                "MissionMap.GetCenter",
                "the frame content-rect read is not ported yet",
            )

        @staticmethod
        def GetPanOffset() -> tuple[float, float]:
            """Pan offset of the mission map. (source 1069)

            Not ported yet: the mission-map sub-context's pan offset is Stage 5.
            The source holds the last non-zero offset rather than reporting
            ``(0.0, 0.0)``, which is behaviour to preserve when it lands.
            """

            raise _disabled(
                "MissionMap.GetPanOffset",
                "the mission-map sub-context's pan offset is not ported yet",
            )

        @staticmethod
        def GetMapScreenCenter() -> tuple[float, float]:
            """Get the map screen center coordinates. (source 1088)

            Not ported yet: it composes the contents coordinates (Stage 5).
            """

            raise _disabled(
                "MissionMap.GetMapScreenCenter",
                "the frame content-rect read is not ported yet",
            )

        class MapProjection:
            """Mission-map coordinate transforms. Source: ``Map.py`` 1097-1403."""

            @staticmethod
            def GamePosToWorldMap(x: float, y: float) -> tuple[float, float]:
                """Convert game-space coordinates to world-map space. (source 1099)

                Not ported yet: the projection arithmetic is Stage 6.
                """

                raise _disabled(
                    "MissionMap.MapProjection.GamePosToWorldMap",
                    "the projection arithmetic is not ported yet",
                )

            @staticmethod
            def WorldMapToGamePos(x: float, y: float) -> tuple[float, float]:
                """Convert world-map coordinates to game space. (source 1133)

                Not ported yet: the projection arithmetic is Stage 6.
                """

                raise _disabled(
                    "MissionMap.MapProjection.WorldMapToGamePos",
                    "the projection arithmetic is not ported yet",
                )

            @staticmethod
            def WorldMapToScreen(
                x: float, y: float, zoom_offset: float = 0.0
            ) -> tuple[float, float]:
                """Convert world-map coordinates to screen space. (source 1169)

                Not ported yet: the projection arithmetic is Stage 6.
                """

                raise _disabled(
                    "MissionMap.MapProjection.WorldMapToScreen",
                    "the projection arithmetic is not ported yet",
                )

            @staticmethod
            def ScreenToWorldMap(
                screen_x: float, screen_y: float, zoom_offset: float = 0.0
            ) -> tuple[float, float]:
                """Convert screen coordinates to world-map space. (source 1197)

                Not ported yet: the projection arithmetic is Stage 6.
                """

                raise _disabled(
                    "MissionMap.MapProjection.ScreenToWorldMap",
                    "the projection arithmetic is not ported yet",
                )

            @staticmethod
            def GameMapToScreen(
                x: float, y: float, zoom_offset: float = 0.0
            ) -> tuple[float, float]:
                """Convert game-map coordinates to screen space. (source 1225)

                Not ported yet: the projection arithmetic is Stage 6.
                """

                raise _disabled(
                    "MissionMap.MapProjection.GameMapToScreen",
                    "the projection arithmetic is not ported yet",
                )

            @staticmethod
            def ScreenToGameMap(
                x: float, y: float, zoom_offset: float = 0.0
            ) -> tuple[float, float]:
                """Convert screen coordinates to game-map space. (source 1241)

                Not ported yet: the projection arithmetic is Stage 6.
                """

                raise _disabled(
                    "MissionMap.MapProjection.ScreenToGameMap",
                    "the projection arithmetic is not ported yet",
                )

            @staticmethod
            def NormalizedScreenToScreen(x: float, y: float) -> tuple[float, float]:
                """Convert normalized screen coordinates to screen space. (source 1254)

                Not ported yet: the projection arithmetic is Stage 6.
                """

                raise _disabled(
                    "MissionMap.MapProjection.NormalizedScreenToScreen",
                    "the projection arithmetic is not ported yet",
                )

            @staticmethod
            def ScreenToNormalizedScreen(
                screen_x: float, screen_y: float
            ) -> tuple[float, float]:
                """Convert screen coordinates to normalized screen space. (source 1278)

                Not ported yet: the projection arithmetic is Stage 6.
                """

                raise _disabled(
                    "MissionMap.MapProjection.ScreenToNormalizedScreen",
                    "the projection arithmetic is not ported yet",
                )

            @staticmethod
            def NormalizedScreenToWorldMap(
                x: float, y: float, zoom_offset: float = 0.0
            ) -> tuple[float, float]:
                """Convert normalized screen coordinates to world-map space. (source 1303)

                Not ported yet: the projection arithmetic is Stage 6.
                """

                raise _disabled(
                    "MissionMap.MapProjection.NormalizedScreenToWorldMap",
                    "the projection arithmetic is not ported yet",
                )

            @staticmethod
            def NormalizedScreenToGamePos(x: float, y: float) -> tuple[float, float]:
                """Convert normalized screen coordinates to game space. (source 1316)

                Not ported yet: the projection arithmetic is Stage 6.
                """

                raise _disabled(
                    "MissionMap.MapProjection.NormalizedScreenToGamePos",
                    "the projection arithmetic is not ported yet",
                )

            @staticmethod
            def GamePosToNormalizedScreen(x: float, y: float) -> tuple[float, float]:
                """Convert game-space coordinates to normalized screen space. (source 1328)

                Not ported yet: the projection arithmetic is Stage 6.
                """

                raise _disabled(
                    "MissionMap.MapProjection.GamePosToNormalizedScreen",
                    "the projection arithmetic is not ported yet",
                )

            @staticmethod
            def GamePosToScreen(
                x: float, y: float, zoom_offset: float = 0.0
            ) -> tuple[float, float]:
                """Convert game-space coordinates to screen space. (source 1340)

                Not ported yet: the projection arithmetic is Stage 6.
                """

                raise _disabled(
                    "MissionMap.MapProjection.GamePosToScreen",
                    "the projection arithmetic is not ported yet",
                )

            @staticmethod
            def ScreenToGamePos(
                x: float, y: float, zoom_offset: float = 0.0
            ) -> tuple[float, float]:
                """Convert screen coordinates to game space. (source 1354)

                Not ported yet: the projection arithmetic is Stage 6.
                """

                raise _disabled(
                    "MissionMap.MapProjection.ScreenToGamePos",
                    "the projection arithmetic is not ported yet",
                )

            @staticmethod
            def WorldPosToMissionMapScreen(
                x: float, y: float, zoom_offset: float = 0.0
            ) -> tuple[float, float]:
                """Convert world coordinates to mission-map screen space. (source 1368)

                Not ported yet: the projection arithmetic is Stage 6.
                """

                raise _disabled(
                    "MissionMap.MapProjection.WorldPosToMissionMapScreen",
                    "the projection arithmetic is not ported yet",
                )

            @staticmethod
            def ScreenToWorldPos(
                screen_x: float, screen_y: float, zoom_offset: float = 0.0
            ) -> tuple[float, float]:
                """Convert mission-map screen coordinates to world space. (source 1388)

                Not ported yet: the projection arithmetic is Stage 6.
                """

                raise _disabled(
                    "MissionMap.MapProjection.ScreenToWorldPos",
                    "the projection arithmetic is not ported yet",
                )

    # -- nested: the mini map (source 1406-1851) --------------------------

    class MiniMap:
        """The compass/mini-map window. Source: ``Map.py`` lines 1406-1851."""

        @staticmethod
        def GetFrame():
            """The mini-map frame. (source 1412)

            Not ported yet: the compass frame lookup is Stage 5.
            """

            raise _disabled(
                "MiniMap.GetFrame", "the compass frame lookup is not ported yet"
            )

        @staticmethod
        def GetFrameID() -> int:
            """Frame id of the mini map. (source 1417)

            Not ported yet: the compass frame lookup is Stage 5.
            """

            raise _disabled(
                "MiniMap.GetFrameID", "the compass frame lookup is not ported yet"
            )

        @staticmethod
        def IsWindowOpen() -> bool:
            """Check if the mini map window is open. (source 1425)

            Not ported yet: it reads the frame's existence (Stage 5).
            """

            raise _disabled(
                "MiniMap.IsWindowOpen", "the compass frame lookup is not ported yet"
            )

        @staticmethod
        def OpenWindow() -> None:
            """Disabled: it asks the client to set the compass window visible."""

            raise _disabled(
                "MiniMap.OpenWindow",
                "it asks the client to set a window visible from inside Gw.exe",
            )

        @staticmethod
        def CloseWindow() -> None:
            """Disabled: it asks the client to set the compass window visible."""

            raise _disabled(
                "MiniMap.CloseWindow",
                "it asks the client to set a window visible from inside Gw.exe",
            )

        @staticmethod
        def IsMouseOver() -> bool:
            """Disabled: it reads the client's per-frame ImGui input state."""

            raise _disabled(
                "MiniMap.IsMouseOver",
                "it reads the client's per-frame ImGui input state, which only "
                "exists with code inside Gw.exe",
            )

        @staticmethod
        def GetLastClickCoords() -> tuple[float, float]:
            """Disabled: the frame IO-event list is filled in-process."""

            raise _disabled(
                "MiniMap.GetLastClickCoords",
                "the client's frame IO-event list is filled by an in-process "
                "callback that reads ImGui, so the events cannot be observed "
                "from outside Gw.exe",
            )

        @staticmethod
        def GetLastRightClickCoords() -> tuple[float, float]:
            """Disabled: the frame IO-event list is filled in-process."""

            raise _disabled(
                "MiniMap.GetLastRightClickCoords",
                "the client's frame IO-event list is filled by an in-process "
                "callback that reads ImGui, so the events cannot be observed "
                "from outside Gw.exe",
            )

        @staticmethod
        def GetWindowCoords() -> tuple[float, float, float, float]:
            """Get the window coordinates of the mini map. (source 1505)

            Not ported yet: the frame rect read is Stage 5.
            """

            raise _disabled(
                "MiniMap.GetWindowCoords",
                "the frame rect read is not ported yet",
            )

        @staticmethod
        def IsLocked() -> bool:
            """Check whether the compass rotation is locked. (source 1512)

            Not ported yet: the source reads the client's ``LockCompassRotation``
            bool preference through ``UIManager``; whether that value is
            reachable read-only is determined in Stage 5.
            """

            raise _disabled(
                "MiniMap.IsLocked",
                "the client's bool-preference read has no established external "
                "route yet",
            )

        @staticmethod
        def GetPanOffset() -> list[float]:
            """Get the pan offset of the mini map. (source 1517)

            Not ported yet: the source returns a constant ``[0.0, 0.0]``;
            landed as-is with Stage 5.
            """

            raise _disabled(
                "MiniMap.GetPanOffset", "the mini-map geometry is not ported yet"
            )

        @staticmethod
        def GetScale(
            coords: tuple[float, float, float, float] | None = None,
        ) -> float:
            """Get the scale of the mini map. (source 1522)

            Not ported yet: the mini-map geometry is Stage 5.
            """

            raise _disabled(
                "MiniMap.GetScale", "the mini-map geometry is not ported yet"
            )

        @staticmethod
        def GetRotation() -> float:
            """Get the rotation of the mini map. (source 1539)

            Not ported yet: it depends on ``IsLocked`` and the camera yaw, whose
            external route is determined in Stage 5.
            """

            raise _disabled(
                "MiniMap.GetRotation",
                "the compass lock and camera yaw read is not ported yet",
            )

        @staticmethod
        def GetZoom() -> float:
            """Get the zoom level of the mini map. (source 1549)

            Not ported yet: the source returns a constant ``1.0``; landed as-is
            with Stage 5.
            """

            raise _disabled(
                "MiniMap.GetZoom", "the mini-map geometry is not ported yet"
            )

        @staticmethod
        def GetMapScreenCenter(
            coords: tuple[float, float, float, float] | None = None,
        ) -> tuple[float, float]:
            """Get the map screen center coordinates. (source 1556)

            Not ported yet: the mini-map geometry is Stage 5.
            """

            raise _disabled(
                "MiniMap.GetMapScreenCenter",
                "the mini-map geometry is not ported yet",
            )

        class MapProjection:
            """Compass coordinate transforms. Source: ``Map.py`` 1575-1850."""

            @staticmethod
            def GamePosToWorldMap(x: float, y: float) -> tuple[float, float]:
                """Convert game-space coordinates to world-map space. (source 1577)

                Not ported yet: the projection arithmetic is Stage 6.
                """

                raise _disabled(
                    "MiniMap.MapProjection.GamePosToWorldMap",
                    "the projection arithmetic is not ported yet",
                )

            @staticmethod
            def WorldMapToGamePos(x: float, y: float) -> tuple[float, float]:
                """Convert world-map coordinates to game space. (source 1601)

                Not ported yet: the projection arithmetic is Stage 6.
                """

                raise _disabled(
                    "MiniMap.MapProjection.WorldMapToGamePos",
                    "the projection arithmetic is not ported yet",
                )

            @staticmethod
            def WorldMapToScreen(x: float, y: float) -> tuple[float, float]:
                """Convert world-map coordinates to screen space. (source 1622)

                Not ported yet: the projection arithmetic is Stage 6.
                """

                raise _disabled(
                    "MiniMap.MapProjection.WorldMapToScreen",
                    "the projection arithmetic is not ported yet",
                )

            @staticmethod
            def ScreenToWorldMap(
                screen_x: float, screen_y: float
            ) -> tuple[float, float]:
                """Convert screen coordinates to world-map space. (source 1640)

                Not ported yet: the projection arithmetic is Stage 6.
                """

                raise _disabled(
                    "MiniMap.MapProjection.ScreenToWorldMap",
                    "the projection arithmetic is not ported yet",
                )

            @staticmethod
            def GameMapToScreen(x: float, y: float) -> tuple[float, float]:
                """Convert game-map coordinates to screen space. (source 1657)

                Not ported yet: the projection arithmetic is Stage 6.
                """

                raise _disabled(
                    "MiniMap.MapProjection.GameMapToScreen",
                    "the projection arithmetic is not ported yet",
                )

            @staticmethod
            def ScreenToGameMap(x: float, y: float) -> tuple[float, float]:
                """Convert screen coordinates to game-map space. (source 1662)

                Not ported yet: the projection arithmetic is Stage 6.
                """

                raise _disabled(
                    "MiniMap.MapProjection.ScreenToGameMap",
                    "the projection arithmetic is not ported yet",
                )

            @staticmethod
            def NormalizedScreenToScreen(x: float, y: float) -> tuple[float, float]:
                """Convert normalized screen coordinates to screen space. (source 1667)

                Not ported yet: the projection arithmetic is Stage 6.
                """

                raise _disabled(
                    "MiniMap.MapProjection.NormalizedScreenToScreen",
                    "the projection arithmetic is not ported yet",
                )

            @staticmethod
            def ScreenToNormalizedScreen(
                screen_x: float, screen_y: float
            ) -> tuple[float, float]:
                """Convert screen coordinates to normalized screen space. (source 1685)

                Not ported yet: the projection arithmetic is Stage 6.
                """

                raise _disabled(
                    "MiniMap.MapProjection.ScreenToNormalizedScreen",
                    "the projection arithmetic is not ported yet",
                )

            @staticmethod
            def NormalizedScreenToWorldMap(x: float, y: float) -> tuple[float, float]:
                """Convert normalized screen coordinates to world-map space. (source 1703)

                Not ported yet: the projection arithmetic is Stage 6.
                """

                raise _disabled(
                    "MiniMap.MapProjection.NormalizedScreenToWorldMap",
                    "the projection arithmetic is not ported yet",
                )

            @staticmethod
            def NormalizedScreenToGamePos(x: float, y: float) -> tuple[float, float]:
                """Convert normalized screen coordinates to game space. (source 1708)

                Not ported yet: the projection arithmetic is Stage 6.
                """

                raise _disabled(
                    "MiniMap.MapProjection.NormalizedScreenToGamePos",
                    "the projection arithmetic is not ported yet",
                )

            @staticmethod
            def GamePosToNormalizedScreen(x: float, y: float) -> tuple[float, float]:
                """Convert game-space coordinates to normalized screen space. (source 1713)

                Not ported yet: the projection arithmetic is Stage 6.
                """

                raise _disabled(
                    "MiniMap.MapProjection.GamePosToNormalizedScreen",
                    "the projection arithmetic is not ported yet",
                )

            @staticmethod
            def GamePosToScreen(x: float, y: float) -> tuple[float, float]:
                """Convert game-space coordinates to screen space. (source 1718)

                Not ported yet: the projection arithmetic is Stage 6.
                """

                raise _disabled(
                    "MiniMap.MapProjection.GamePosToScreen",
                    "the projection arithmetic is not ported yet",
                )

            @staticmethod
            def ScreenToGamePos(x: float, y: float) -> tuple[float, float]:
                """Convert screen coordinates to game space. (source 1748)

                Not ported yet: the projection arithmetic is Stage 6.
                """

                raise _disabled(
                    "MiniMap.MapProjection.ScreenToGamePos",
                    "the projection arithmetic is not ported yet",
                )

            @staticmethod
            def WorldPosToMiniMapScreen(x: float, y: float) -> tuple[float, float]:
                """Convert world coordinates to mini-map screen space. (source 1778)

                Not ported yet: the projection arithmetic is Stage 6.
                """

                raise _disabled(
                    "MiniMap.MapProjection.WorldPosToMiniMapScreen",
                    "the projection arithmetic is not ported yet",
                )

            @staticmethod
            def ScreenToWorldPos(
                screen_x: float, screen_y: float
            ) -> tuple[float, float]:
                """Convert mini-map screen coordinates to world space. (source 1789)

                Not ported yet: the projection arithmetic is Stage 6.
                """

                raise _disabled(
                    "MiniMap.MapProjection.ScreenToWorldPos",
                    "the projection arithmetic is not ported yet",
                )

            @staticmethod
            def ComputedPathingGeometryToScreen(
                geometry: object,
            ) -> list[object]:
                """Project computed pathing geometry to screen space. (source 1800)

                Not ported yet: the projection arithmetic is Stage 6.
                """

                raise _disabled(
                    "MiniMap.MapProjection.ComputedPathingGeometryToScreen",
                    "the projection arithmetic is not ported yet",
                )

    # -- nested: the world map (source 1853-2023) -------------------------

    class WorldMap:
        """The world-map window. Source: ``Map.py`` lines 1853-2023."""

        @staticmethod
        def GetFrameID() -> int:
            """Frame id of the world map. (source 1859)

            Not ported yet: the world-map context's frame id is Stage 5.
            """

            raise _disabled(
                "WorldMap.GetFrameID",
                "the world-map context's frame id is not ported yet",
            )

        @staticmethod
        def GetFrame():
            """The world-map frame. (source 1866)

            Not ported yet: the frame lookup is Stage 5.
            """

            raise _disabled(
                "WorldMap.GetFrame", "the frame lookup is not ported yet"
            )

        @staticmethod
        def IsWindowOpen() -> bool:
            """Check if the world map window is open. (source 1873)

            Not ported yet: it reads the frame's existence (Stage 5).
            """

            raise _disabled(
                "WorldMap.IsWindowOpen", "the frame lookup is not ported yet"
            )

        @staticmethod
        def OpenWindow() -> None:
            """Disabled: it queues the open-world-map keybind."""

            raise _disabled(
                "WorldMap.OpenWindow",
                "it queues a keybind on the client's own game thread",
            )

        @staticmethod
        def CloseWindow() -> None:
            """Disabled: the source queues the same keybind as ``OpenWindow``."""

            raise _disabled(
                "WorldMap.CloseWindow",
                "it queues a keybind on the client's own game thread",
            )

        @staticmethod
        def IsMouseOver() -> bool:
            """Disabled: it reads the client's per-frame ImGui input state."""

            raise _disabled(
                "WorldMap.IsMouseOver",
                "it reads the client's per-frame ImGui input state, which only "
                "exists with code inside Gw.exe",
            )

        @staticmethod
        def GetLastClickCoords() -> tuple[float, float]:
            """Disabled: the frame IO-event list is filled in-process."""

            raise _disabled(
                "WorldMap.GetLastClickCoords",
                "the client's frame IO-event list is filled by an in-process "
                "callback that reads ImGui, so the events cannot be observed "
                "from outside Gw.exe",
            )

        @staticmethod
        def GetLastRightClickCoords() -> tuple[float, float]:
            """Disabled: the frame IO-event list is filled in-process."""

            raise _disabled(
                "WorldMap.GetLastRightClickCoords",
                "the client's frame IO-event list is filled by an in-process "
                "callback that reads ImGui, so the events cannot be observed "
                "from outside Gw.exe",
            )

        @staticmethod
        def GetWindowCoords() -> tuple[float, float, float, float]:
            """Get the window coordinates of the world map. (source 1951)

            Not ported yet: the world-map context's corners are Stage 5.
            """

            raise _disabled(
                "WorldMap.GetWindowCoords",
                "the world-map context's corners are not ported yet",
            )

        @staticmethod
        def GetZoom() -> float:
            """Get the zoom level of the world map. (source 1962)

            Not ported yet: the world-map context's zoom is Stage 5.
            """

            raise _disabled(
                "WorldMap.GetZoom",
                "the world-map context's zoom is not ported yet",
            )

        @staticmethod
        def GetParams() -> list[int] | None:
            """Get the world-map parameters. (source 1969)

            Not ported yet: the world-map context's param array is Stage 5.
            """

            raise _disabled(
                "WorldMap.GetParams",
                "the world-map context's parameter array is not ported yet",
            )

        @staticmethod
        def GetExtraData() -> dict | None:
            """Get the world-map context's remaining fields. (source 1976)

            Not ported yet: the world-map context field read is Stage 5. The
            source reads these offsets through ``ctypes.addressof`` on the
            in-process structure; externally the same offsets are read from the
            structure's own address.
            """

            raise _disabled(
                "WorldMap.GetExtraData",
                "the world-map context field read is not ported yet",
            )

    # -- nested: pre-game (source 2025-2097) ------------------------------

    class Pregame:
        """The login/character-select screen. Source: ``Map.py`` 2025-2097."""

        @staticmethod
        def GetFrameID() -> int:
            """Frame id of the pre-game screen. (source 2034)

            Not ported yet: the pre-game context's frame id is Stage 5.
            """

            raise _disabled(
                "Pregame.GetFrameID",
                "the pre-game context's frame id is not ported yet",
            )

        @staticmethod
        def GetFrame():
            """The pre-game frame. (source 2041)

            Not ported yet: the frame lookup is Stage 5.
            """

            raise _disabled(
                "Pregame.GetFrame", "the frame lookup is not ported yet"
            )

        @staticmethod
        def IsWindowOpen() -> bool:
            """Check if the pre-game window is open. (source 2048)

            Not ported yet: it reads the frame's existence (Stage 5).
            """

            raise _disabled(
                "Pregame.IsWindowOpen", "the frame lookup is not ported yet"
            )

        @staticmethod
        def GetChosenCharacterIndex() -> int:
            """Get the chosen character index. (source 2055)

            Not ported yet: the pre-game context's preview index is Stage 5.
            """

            raise _disabled(
                "Pregame.GetChosenCharacterIndex",
                "the pre-game context's character index is not ported yet",
            )

        @staticmethod
        def GetContextStruct():
            """Get the pre-game context structure. (source 2062)

            Not ported yet: the pre-game context read is Stage 5.
            """

            raise _disabled(
                "Pregame.GetContextStruct",
                "the pre-game context read is not ported yet",
            )

        @staticmethod
        def GetCharList() -> list[object]:
            """Get the character list from the pre-game screen. (source 2067)

            Not ported yet: the pre-game context's character list is Stage 5.
            """

            raise _disabled(
                "Pregame.GetCharList",
                "the pre-game context's character list is not ported yet",
            )

        @staticmethod
        def GetAvailableCharacterList() -> list[object]:
            """Get the available character list. (source 2074)

            Not ported yet: the available-character array is Stage 5.
            """

            raise _disabled(
                "Pregame.GetAvailableCharacterList",
                "the available-character array read is not ported yet",
            )

        @staticmethod
        def InCharacterSelectScreen() -> bool:
            """Disabled: it calls into the client through ``PySystem``."""

            raise _disabled(
                "Pregame.InCharacterSelectScreen",
                "it calls into the client's own runtime through PySystem",
            )

        @staticmethod
        def LogoutToCharacterSelect() -> None:
            """Disabled: it queues a logout UI message on the game thread."""

            raise _disabled(
                "Pregame.LogoutToCharacterSelect",
                "it queues a logout UI message on the client's own game thread",
            )

    # -- nested: pathing (source 2099-2327) -------------------------------

    class Pathing:
        """Pathing maps, spawns, portals and geometry. Source: 2099-2327."""

        @staticmethod
        def GetPathingMaps(map_id: int | None = None) -> list[object]:
            """Get pathing maps: live from the map, or offline by map id. (source 2102)

            Not ported yet: the live map-context read is Stage 7. The offline
            branch needs ``PyDatReader.read_file_by_id`` and the FFNA format,
            which this project has no route to yet.
            """

            raise _disabled(
                "Pathing.GetPathingMaps",
                "the live pathing read is not ported yet",
            )

        @staticmethod
        def GetPathingMapsRaw() -> list[object]:
            """Get the raw pathing map records. (source 2114)

            Not ported yet: the live map-context read is Stage 7.
            """

            raise _disabled(
                "Pathing.GetPathingMapsRaw",
                "the live pathing read is not ported yet",
            )

        @staticmethod
        def ClearPathingCache(
            map_id: int | None = None, include_live: bool = False
        ) -> None:
            """Clear cached pathing data. (source 2122)

            Not ported: it clears the source project's own
            ``_pathing_cache``/``_spawn_cache``/``_portal_cache`` and the
            ``AutoPathing`` navmesh cache, none of which this port creates. What
            it does here is determined in Stage 7.
            """

            raise _disabled(
                "Pathing.ClearPathingCache",
                "it clears the source project's own pathing caches, which this "
                "port does not create",
            )

        @staticmethod
        def ForceReloadNavMesh() -> None:
            """Disabled: it builds the navmesh inside the client."""

            raise _disabled(
                "Pathing.ForceReloadNavMesh",
                "it builds the navmesh inside Gw.exe",
            )

        @staticmethod
        def GetAvailableMapIds() -> set[int]:
            """Return the map ids offline pathing can be loaded for. (source 2146)

            Not ported yet: the FFNA map-id table is Stage 7. The pathing data
            itself still needs the DAT/FFNA capability.
            """

            raise _disabled(
                "Pathing.GetAvailableMapIds",
                "the FFNA map-id table is not ported yet",
            )

        @staticmethod
        def GetSpawns(
            map_id: int | None = None,
        ) -> tuple[list[object], list[object], list[object]]:
            """Get ``(spawns1, spawns2, spawns3)``. (source 2152)

            Not ported yet: the live map-context read is Stage 7. The offline
            branch needs the DAT/FFNA capability.
            """

            raise _disabled(
                "Pathing.GetSpawns", "the live pathing read is not ported yet"
            )

        @staticmethod
        def GetTravelPortals(map_id: int | None = None) -> list[object]:
            """Get the travel portals. (source 2161)

            Not ported yet: the live map-context read is Stage 7. The offline
            branch needs the DAT/FFNA capability.
            """

            raise _disabled(
                "Pathing.GetTravelPortals",
                "the live pathing read is not ported yet",
            )

        @staticmethod
        def WorldToScreen(x: float, y: float, z: float = 0.0) -> tuple[float, float]:
            """Disabled: it projects through the client's overlay kernel."""

            raise _disabled(
                "Pathing.WorldToScreen",
                "it projects through the client's own overlay kernel",
            )

        class Quad:
            """A pathing trapezoid with its projected screen corners. (source 2177)"""

            def __init__(self, trapezoid: object) -> None:
                """Build a quad from a pathing trapezoid. (source 2178)

                Not ported yet: the quad construction and its projection are
                Stage 7.
                """

                raise _disabled(
                    "Pathing.Quad.__init__", "the quad construction is not ported yet"
                )

            def GetPoints(self) -> list[object]:
                """Return the four game-space corners. (source 2196)

                Not ported yet: the quad construction is Stage 7.
                """

                raise _disabled(
                    "Pathing.Quad.GetPoints", "the quad construction is not ported yet"
                )

            def GetScreenPoints(self) -> list[object]:
                """Return the four screen-space corners. (source 2199)

                Not ported yet: the quad construction is Stage 7.
                """

                raise _disabled(
                    "Pathing.Quad.GetScreenPoints",
                    "the quad construction is not ported yet",
                )

            def GetShiftedPoints(self, origin_x: float, origin_y: float) -> list[object]:
                """Return the four game-space corners shifted by an origin. (source 2202)

                Not ported yet: the quad construction is Stage 7.
                """

                raise _disabled(
                    "Pathing.Quad.GetShiftedPoints",
                    "the quad construction is not ported yet",
                )

            def GetShiftedScreenPoints(
                self, origin_x: float, origin_y: float
            ) -> list[object]:
                """Return the four screen corners shifted by an origin. (source 2210)

                Not ported yet: the quad construction is Stage 7.
                """

                raise _disabled(
                    "Pathing.Quad.GetShiftedScreenPoints",
                    "the quad construction is not ported yet",
                )

        @staticmethod
        def GetComputedGeometry() -> list[list[object]]:
            """Get pathing geometry as game-space quads. (source 2224)

            Not ported yet: it composes the live pathing maps and ``Quad``
            (Stage 7).
            """

            raise _disabled(
                "Pathing.GetComputedGeometry",
                "the live pathing read is not ported yet",
            )

        @staticmethod
        def GetScreenComputedGeometry() -> list[list[object]]:
            """Get pathing geometry as screen-space quads. (source 2233)

            Not ported yet: it composes the live pathing maps and ``Quad``
            (Stage 7).
            """

            raise _disabled(
                "Pathing.GetScreenComputedGeometry",
                "the live pathing read is not ported yet",
            )

        @staticmethod
        def GetShiftedComputedGeometry(
            origin_x: float, origin_y: float
        ) -> list[list[object]]:
            """Get pathing geometry shifted by an origin. (source 2242)

            Not ported yet: it composes the live pathing maps and ``Quad``
            (Stage 7).
            """

            raise _disabled(
                "Pathing.GetShiftedComputedGeometry",
                "the live pathing read is not ported yet",
            )

        @staticmethod
        def GetshiftedScreenComputedGeometry(
            origin_x: float, origin_y: float
        ) -> list[list[object]]:
            """Get screen-space pathing geometry shifted by an origin. (source 2252)

            Not ported yet: it composes the live pathing maps and ``Quad``
            (Stage 7).
            """

            raise _disabled(
                "Pathing.GetshiftedScreenComputedGeometry",
                "the live pathing read is not ported yet",
            )

        @staticmethod
        def _point_in_quad(px: float, py: float, quad: object) -> bool:
            """Return whether a point lies inside a quad. (source 2262)

            Not ported yet: the quad test is Stage 7.
            """

            raise _disabled(
                "Pathing._point_in_quad", "the quad test is not ported yet"
            )

        @staticmethod
        def GetMapQuads() -> list[object]:
            """Get the map's pathing quads. (source 2277)

            Not ported yet: it composes the live pathing maps and ``Quad``
            (Stage 7).
            """

            raise _disabled(
                "Pathing.GetMapQuads", "the live pathing read is not ported yet"
            )

        @staticmethod
        def IsPointInPathing(px: float, py: float) -> bool:
            """Check whether a game-space point is in pathing geometry. (source 2290)

            Not ported yet: it composes the live pathing maps and ``Quad``
            (Stage 7).
            """

            raise _disabled(
                "Pathing.IsPointInPathing",
                "the live pathing read is not ported yet",
            )

        @staticmethod
        def IsScreenPointInPathing(screen_x: float, screen_y: float) -> bool:
            """Check whether a screen point is in pathing geometry. (source 2303)

            Not ported yet: it composes the live pathing maps and ``Quad``
            (Stage 7).
            """

            raise _disabled(
                "Pathing.IsScreenPointInPathing",
                "the live pathing read is not ported yet",
            )

