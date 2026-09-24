"""External port of Reforged's ``Py4GWCoreLib/Map.py``, started at the gate.

Reforged's ``Map`` is 2327 lines across a main class and six nested ones
(``MissionMap``, ``MapProjection``, both ``MiniMap``/``WorldMap`` projections,
``Pregame``, and ``Pathing``). Only part of that is portable, and only part is
needed yet.

What exists here is the part every other wrapper depends on: **the readiness
gate**. `Map.IsMapReady` is the check ``Party``, ``AccountStruct``, ``agents``,
``interaction`` and ``controller`` all ask before touching map-scoped data, and
it is the first thing native ``PyPlayer::GetContext`` does. It is implemented
here in full, ported from Reforged's ``Map.py`` lines 40-118, so there is
exactly one implementation of the predicate in this project.

Also implemented: the current map's identity and the ``AreaInfo`` metadata the
client already publishes for it. Everything else is recorded at the bottom of
this module as pending, rather than faked.

Not created yet: ``MissionMap``, ``MapProjection``, ``MiniMap``, ``WorldMap``,
``Pregame`` and ``Pathing``. Several of those need the frame tree and overlay
projection, which this project has separately in ``py4gw/ui``.
"""

from __future__ import annotations

from .client import ConnectedClient, require_client
from .context.char_context import CharContextStruct
from .context.instance_info_context import (
    AreaInfoStruct,
    InstanceInfoStruct,
    InstanceType,
    InstanceTypeName,
)
from .context.map_context import MapContextStruct
from .context.world_context import WorldContextStruct


def _disabled(member: str, requirement: str) -> NotImplementedError:
    """Build the error raised by a member that needs code inside the client."""

    return NotImplementedError(
        f"Map.{member} is not available from an external reader: {requirement}. "
        "It exists for source parity so a ported script fails at the call site "
        "and names the missing mechanism instead of returning a wrong value."
    )


class Map:
    """Read-only port of the Reforged ``Map`` namespace class.

    Implemented here: the readiness gate, the current map identity, and the
    ``AreaInfo`` metadata. See the module docstring for what is pending.
    """

    # ── client access ──────────────────────────────────────────────────────


    # ── the readiness gate ─────────────────────────────────────────────────
    #
    # Literal port of Reforged's ``Py4GWCoreLib/Map.py`` lines 40-118. The
    # structure, the short-circuits, and the return values are the source's, so
    # ``IsObservingMatch`` and ``IsMapLoading`` answer ``True`` when the map data
    # is not loaded, exactly as the source does.
    #
    # ``GWContext.X.IsValid()`` is ``X.GetContext() is not None`` in Reforged,
    # over facade objects its callbacks maintain. Externally there are no
    # callbacks, so the equivalent is whether this reader resolved the context on
    # this read.

    @staticmethod
    def _char_context() -> CharContextStruct | None:
        """Return the character context, or ``None`` when it did not resolve."""

        try:
            return require_client().read_char_context()
        except (OSError, RuntimeError):
            return None

    @staticmethod
    def _instance_info_context() -> InstanceInfoStruct | None:
        """Return the instance-info context, or ``None`` when it did not resolve."""

        try:
            return require_client().read_instance_info()
        except (OSError, RuntimeError):
            return None

    @staticmethod
    def _map_context() -> MapContextStruct | None:
        """Return the map context, or ``None`` when it did not resolve."""

        try:
            return require_client().read_map_context()
        except (OSError, RuntimeError):
            return None

    @staticmethod
    def _world_context() -> WorldContextStruct | None:
        """Return the world context, or ``None`` when it did not resolve."""

        try:
            return require_client().read_world_context()
        except (OSError, RuntimeError):
            return None

    @staticmethod
    def IsMapDataLoaded() -> bool:
        """Check if the map data is loaded."""

        return (
            Map._map_context() is not None
            and Map._char_context() is not None
            and Map._instance_info_context() is not None
            and Map._world_context() is not None
        )

    @staticmethod
    def GetInstanceType() -> int:
        """Retrieve the instance type of the current map."""

        instance_info = Map._instance_info_context()
        if instance_info is None:
            return int(InstanceType.LOADING)
        instance_type = int(instance_info.instance_type)
        return (
            instance_type
            if instance_type in InstanceType._value2member_map_
            else int(InstanceType.LOADING)
        )

    @staticmethod
    def GetInstanceTypeName() -> str:
        """Retrieve the instance type name of the current map."""

        instance_type = Map.GetInstanceType()
        return InstanceTypeName.get(instance_type, "Loading")

    @staticmethod
    def IsOutpost() -> bool:
        """Check if the map instance is an outpost."""

        if not Map.IsMapDataLoaded():
            return False
        return Map.GetInstanceType() == InstanceType.OUTPOST

    @staticmethod
    def IsExplorable() -> bool:
        """Check if the map instance is explorable."""

        if not Map.IsMapDataLoaded():
            return False
        return Map.GetInstanceType() == InstanceType.EXPLORABLE

    @staticmethod
    def IsMapLoading() -> bool:
        """Check if the map is in a loading phase."""

        if not Map.IsMapDataLoaded():
            return True

        return Map.GetInstanceType() not in (
            InstanceType.OUTPOST,
            InstanceType.EXPLORABLE,
        )

    @staticmethod
    def IsObservingMatch() -> bool:
        """Check if the character is observing a match."""

        if not Map.IsMapDataLoaded():
            return True

        char_context = Map._char_context()
        if not char_context:
            return False
        return int(char_context.current_map_id) != int(char_context.observe_map_id)

    @staticmethod
    def IsMapReady() -> bool:
        """Check if the map is ready to be handled."""

        return (
            Map.IsMapDataLoaded()
            and not Map.IsObservingMatch()
            and not Map.IsMapLoading()
        )

    # ── current map identity ───────────────────────────────────────────────

    @staticmethod
    def GetMapID() -> int:
        """Return the current map id, or ``0`` when unavailable."""

        try:
            char_context = require_client().read_char_context()
        except (OSError, RuntimeError):
            return 0
        if char_context is None:
            return 0
        return int(char_context.current_map_id)

    @staticmethod
    def IsInCinematic() -> bool:
        """Return whether a cinematic is playing.

        Reforged refuses to answer unless the map is ready, because the
        character context is not trustworthy during a load.
        """

        client = require_client()
        if not Map.IsMapReady():
            return False
        try:
            cinematic = client.read_cinematic_context()
        except (OSError, RuntimeError):
            return False
        return cinematic is not None and int(cinematic.h0004) != 0

    # ── current map metadata (``AreaInfo``) ────────────────────────────────

    @staticmethod
    def _area() -> AreaInfoStruct | None:
        """Return the current map's ``AreaInfo``, or ``None`` when not ready.

        The client publishes this under ``InstanceInfo.current_map_info``. It
        only exists while a map is loaded, so this is gated.
        """

        client = require_client()
        if not Map.IsMapReady():
            return None
        try:
            instance_info = client.read_instance_info()
        except (OSError, RuntimeError):
            return None
        if instance_info is None:
            return None
        return instance_info.current_map_info

    @staticmethod
    def _area_value(name: str, default: int = 0) -> int:
        """Read one ``AreaInfo`` field, or ``default`` when it is unavailable."""

        area = Map._area()
        if area is None:
            return default
        return int(getattr(area, name))

    @staticmethod
    def GetCampaign() -> tuple[int, str]:
        """Return the campaign id and name."""

        return Map._area_value("campaign"), ""

    @staticmethod
    def GetContinent() -> tuple[int, str]:
        """Return the continent id and name."""

        return Map._area_value("continent"), ""

    @staticmethod
    def GetRegionType() -> tuple[int, str]:
        """Return the region type and name."""

        return Map._area_value("type"), ""

    @staticmethod
    def GetMaxPartySize() -> int:
        """Return the maximum party size for this map."""

        return Map._area_value("max_party_size")

    @staticmethod
    def GetMinPartySize() -> int:
        """Return the minimum party size for this map."""

        return Map._area_value("min_party_size")

    @staticmethod
    def GetMaxPlayerSize() -> int:
        """Return the maximum player count for this map."""

        return Map._area_value("max_player_size")

    @staticmethod
    def GetMinPlayerSize() -> int:
        """Return the minimum player count for this map."""

        return Map._area_value("min_player_size")

    @staticmethod
    def GetMinLevel() -> int:
        """Return the minimum character level for this map."""

        return Map._area_value("min_level")

    @staticmethod
    def GetMaxLevel() -> int:
        """Return the maximum character level for this map."""

        return Map._area_value("max_level")

    @staticmethod
    def GetFlags() -> int:
        """Return the raw ``AreaInfo`` flag bits."""

        return Map._area_value("flags")

    @staticmethod
    def GetThumbnailID() -> int:
        """Return the world-map thumbnail id."""

        return Map._area_value("thumbnail_id")

    @staticmethod
    def GetControlledOutpostID() -> int:
        """Return the controlled-outpost id."""

        return Map._area_value("controlled_outpost_id")

    @staticmethod
    def GetFractionMission() -> int:
        """Return the faction mission id."""

        return Map._area_value("fraction_mission")

    @staticmethod
    def GetNeededPQ() -> int:
        """Return the needed quest points."""

        return Map._area_value("needed_pq")

    @staticmethod
    def GetMissionMapsTo() -> int:
        """Return the mission's destination map id."""

        return Map._area_value("mission_maps_to")

    @staticmethod
    def HasMissionMapsTo() -> bool:
        """Return whether this area has a mission-map destination."""

        area = Map._area()
        return bool(area is not None and area.has_mission_maps_to)

    @staticmethod
    def GetFileID() -> int:
        """Return the area's file id."""

        return Map._area_value("file_id")

    @staticmethod
    def GetFileID1() -> int:
        """Return the first archive identifier."""

        area = Map._area()
        return int(area.file_id_1) if area is not None else 0

    @staticmethod
    def GetFileID2() -> int:
        """Return the second archive identifier."""

        area = Map._area()
        return int(area.file_id_2) if area is not None else 0

    @staticmethod
    def GetMissionChronology() -> int:
        """Return the mission's chronology index."""

        return Map._area_value("mission_chronology")

    @staticmethod
    def GetHAChronology() -> int:
        """Return the Hero's Ascent chronology index."""

        return Map._area_value("ha_map_chronology")

    @staticmethod
    def GetNameID() -> int:
        """Return the area name's string id."""

        return Map._area_value("name_id")

    @staticmethod
    def GetDescriptionID() -> int:
        """Return the area description's string id."""

        return Map._area_value("description_id")

    @staticmethod
    def GetIconPosition() -> tuple[int, int]:
        """Return the world-map icon position."""

        area = Map._area()
        if area is None:
            return (0, 0)
        return (int(area.x), int(area.y))

    @staticmethod
    def GetIconStartPosition() -> tuple[int, int]:
        """Return the world-map icon's start corner."""

        area = Map._area()
        if area is None:
            return (0, 0)
        return (int(area.icon_start_x), int(area.icon_start_y))

    @staticmethod
    def GetIconEndPosition() -> tuple[int, int]:
        """Return the world-map icon's end corner."""

        area = Map._area()
        if area is None:
            return (0, 0)
        return (int(area.icon_end_x), int(area.icon_end_y))

    @staticmethod
    def GetIconStartDupePosition() -> tuple[int, int]:
        """Return the duplicated world-map icon start corner."""

        area = Map._area()
        if area is None:
            return (0, 0)
        return (int(area.icon_start_x_dupe), int(area.icon_start_y_dupe))

    @staticmethod
    def GetIconEndDupePosition() -> tuple[int, int]:
        """Return the duplicated world-map icon end corner."""

        area = Map._area()
        if area is None:
            return (0, 0)
        return (int(area.icon_end_x_dupe), int(area.icon_end_y_dupe))

    @staticmethod
    def HasEnterChallengeButton() -> bool:
        """Return whether the area exposes an enter-challenge button."""

        area = Map._area()
        return bool(area is not None and area.has_enter_button)

    @staticmethod
    def IsOnWorldMap() -> bool:
        """Return whether the area is a world-map location."""

        area = Map._area()
        return bool(area is not None and area.is_on_world_map)

    @staticmethod
    def IsPVP() -> bool:
        """Return whether the area carries the PvP flags."""

        area = Map._area()
        return bool(area is not None and area.is_pvp)

    @staticmethod
    def IsGuildHall() -> bool:
        """Return whether the area is a guild hall."""

        area = Map._area()
        return bool(area is not None and area.is_guild_hall)

    @staticmethod
    def IsVanquishable() -> bool:
        """Return whether the area can be vanquished."""

        area = Map._area()
        return bool(area is not None and area.is_vanquishable_area)

    @staticmethod
    def IsUnlockable() -> bool:
        """Return whether the area is unlockable."""

        area = Map._area()
        return bool(area is not None and area.is_unlockable)

    # ── actions (disabled) ────────────────────────────────────────────────

    @staticmethod
    def SkipCinematic() -> None:
        """Disabled: skipping a cinematic calls the client's own function."""

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


class MissionMap:
    """Not ported yet.

    Reforged's ``Map.MissionMap`` reads the mission-map window through the UI
    frame tree. This project already reads the mission map's *context* directly
    (``ConnectedClient.read_mission_map_context``), so the frame-based helpers
    here are deferred rather than stubbed.
    """


class MapProjection:
    """Not ported yet: the ``Map`` projection helpers need the frame tree."""


class MiniMap:
    """Not ported yet: the minimap window and its projection."""


class WorldMap:
    """Not ported yet. The world-map *context* is already readable."""


class Pregame:
    """Not ported yet. The pre-game *context* is already readable."""


class Pathing:
    """Not ported yet. Pathing geometry is reachable through ``MapContext``."""


# ── pending Reforged members, recorded rather than faked ──────────────────
#
# Data members that need sources this port does not read yet:
#   GetOutpostIDs, GetOutpostNames, GetMapName, GetMapIDByName, GetBaseMapID,
#   GetAllMapVariants, IsMapIDMatch, GetRegion, GetDistrict, GetLanguage,
#   GetAmountOfPlayersInInstance, IsMapUnlocked, GetUnloadedMapInfo,
#   IsEnteringChallenge, GetFoesKilled, GetFoesToKill, IsVanquishCompleted,
#   IsVanquishComplete, GetInstanceUptime, GetMapWorldMapBounds,
#   GetMapBoundaries
#
# ``GetInstanceUptime`` is blocked for the same reason as
# ``Player.GetInstanceUptime``: the client's frame limit is only reachable
# through a client function pointer.
#
# The map-name and outpost tables come from Reforged's JSON data files rather
# than from the client, so they are a data-porting task, not a memory one.
