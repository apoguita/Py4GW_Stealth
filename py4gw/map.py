"""External port of Reforged's ``Py4GWCoreLib/Map.py``.

``Map.py`` is 2327 lines: one ``Map`` class carrying five nested namespaces and
two nested projections, 178 members in total. This module ports that surface in
the source's own shape and nesting -- ``Map.MissionMap.MapProjection`` and
``Map.MiniMap.MapProjection`` are nested, not top-level.

Members whose read works from outside ``Gw.exe`` read the client. Members whose read does not are
declared and refuse, naming the work item they are waiting on, so a ported script fails at the call
site instead of returning a wrong value. The docstrings distinguish two kinds of refusal: a table or
route this port has not built yet, and a named in-process mechanism this project cannot run yet.
Either way the source's member is complete and working — the refusal describes this port's
outstanding work and never the source.

Four sources only, all of them the source's own:

* the game contexts, through ``ConnectedClient.read_*``;
* the UI frame tree, for window geometry;
* the local map and region tables under ``enums_src/``;
* native ``MapMethods``.

The port is staged; ``docs/MAP_PORT.md`` is the plan and the progress record.
Nothing here is invented: see ``docs/PORTING_RULES.md``.
"""

from __future__ import annotations

import math
import struct
from typing import Any

from .context.available_character_context import AvailableCharacterStruct
from .context.gw_context import GWContext
from .context.instance_info_context import AreaInfoStruct
from .context.map_context import (
    PathingMap,
    PathingMapStruct,
    PathingTrapezoid,
    SpawnPoint,
    TravelPortal,
)
from .enums_src.map_enums import InstanceType, InstanceTypeName, outposts
from .enums_src.region_enums import (
    CampaignName,
    ContinentName,
    RegionTypeName,
    ServerLanguageName,
    ServerRegionName,
)
from .enums_src.ui_enums import FlagPreference, UIMessage
from .frame_tree import Frame, FrameId
from .internals.types import Vec2f
from .map_methods import MapMethods
from .ui_manager import UIManager

#: Where ``Pregame.InCharacterSelectScreen``'s ``ui_state`` word lives. Native keeps it on its own
#: stack frame and hands ``&ui_state`` to the client (``system/system_methods.cpp:188-197``); the
#: block's data region is this port's equivalent of an address the client may write through.
#: Placed in the gap above ``ui_manager.py``'s ``_UI_PAYLOAD_OFFSET``, beside ``map_methods.py``'s
#: two — the region's lower half is far more crowded than it looks, because
#: ``chat.LOG_MESSAGE_OFFSET`` alone spans ``0x200..0x600``.
#: ``tests/test_map_offline.py::BlockRegionTests`` pins all three against every other region.
_UI_STATE_OFFSET = 0xF40


def _unported(member: str, requirement: str) -> NotImplementedError:
    """Build the error raised by a member this port has not built yet.

    The source's member is complete and working, so the message names the work item this port still
    owes and nothing about the source.
    """

    return NotImplementedError(
        f"Map.{member} is declared but not built here yet: it needs {requirement}. "
        "The source's member works; this port raises at the call site and names the work "
        "item instead of returning a wrong value."
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
            return InstanceType.Loading.value
        return (
            instance_info.instance_type
            if instance_info.instance_type in InstanceType._value2member_map_
            else InstanceType.Loading.value
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
        return Map.GetInstanceType() == InstanceType.Outpost.value

    @staticmethod
    def IsExplorable() -> bool:
        """Check if the map instance is explorable. (source 80)"""

        if not Map.IsMapDataLoaded():
            return False
        return Map.GetInstanceType() == InstanceType.Explorable.value

    @staticmethod
    def IsMapLoading() -> bool:
        """Check if the map is in a loading phase. (source 88)"""

        if not Map.IsMapDataLoaded():
            return True

        return Map.GetInstanceType() not in (
            InstanceType.Outpost.value,
            InstanceType.Explorable.value,
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
        """Retrieve the outpost IDs. (source 128)"""

        global outposts
        return list(outposts.keys())

    @staticmethod
    def GetOutpostNames() -> list[str]:
        """Retrieve the outpost names. (source 134)"""

        global outposts
        return list(outposts.values())

    @staticmethod
    def GetMapName(mapid: int | None = None) -> str:
        """Retrieve the name of a map by its id. (source 142)"""

        from .enums_src.map_enums import outposts, explorables

        if mapid is None:
            map_id = Map.GetMapID()
        else:
            map_id = mapid

        if map_id in outposts:
            return outposts[map_id]
        if map_id in explorables:
            return explorables[map_id]

        return "Unknown Map ID"

    @staticmethod
    def GetMapIDByName(name: str) -> int:
        """Retrieve the id of a map by its name, case-insensitively. (source 165)"""

        from .enums_src.map_enums import outposts, explorables

        # Normalize lookup key
        key = name.lower()

        catalog: dict[str, int] = {}

        # build lowercase-name -> id dictionary
        for id, nm in outposts.items():
            catalog[nm.lower()] = id

        for id, nm in explorables.items():
            catalog[nm.lower()] = id

        return int(catalog.get(key, 0))

    @staticmethod
    def GetBaseMapID(map_id: int = 0) -> int:
        """Get the base map id, resolving seasonal variants. (source 188)

        The source's own example: the Halloween Lions Arch id (808) answers the
        normal Lions Arch id (55).
        """

        from .enums_src.map_enums import map_variants_to_base

        if map_id == 0:
            map_id = Map.GetMapID()

        # Return the base map ID if this is a variant, otherwise return the map itself
        return map_variants_to_base.get(map_id, map_id)

    @staticmethod
    def GetAllMapVariants(map_id: int) -> list[int]:
        """Get every variant of a map, including the base. (source 211)"""

        from .enums_src.map_enums import base_to_all_variants

        # First normalize to base ID
        base_id = Map.GetBaseMapID(map_id)

        # Return all variants for this base (or just the base if no variants)
        return base_to_all_variants.get(base_id, [base_id])

    @staticmethod
    def IsMapIDMatch(current_map: int = 0, target_map: int = 0) -> bool:
        """Check two map ids match, accounting for seasonal variants. (source 231)"""

        if current_map == 0:
            current_map = Map.GetMapID()
        if target_map == 0:
            target_map = Map.GetMapID()

        # Compare base map IDs
        return Map.GetBaseMapID(current_map) == Map.GetBaseMapID(target_map)

    # -- region, language, instance sizes (source 252-365) ----------------

    @staticmethod
    def GetInstanceUptime() -> int:
        """Retrieve the uptime of the current instance. (source 253)"""

        if not (agent_context := GWContext.AccAgent.GetContext()):
            return 0
        return agent_context.instance_timer

    @staticmethod
    def GetRegion() -> tuple[int, str]:
        """Retrieve the region id and name of the current server region. (source 261)"""

        if not (region_ctx := GWContext.ServerRegion.GetContext()):
            return 255, ServerRegionName[255]

        return region_ctx.region_id, ServerRegionName[region_ctx.region_id]

    @staticmethod
    def GetRegionType() -> tuple[int, str]:
        """Retrieve the region type and name of the current map. (source 274)"""

        _unknown_region_type = 20  # Unknown
        current_map_info = GWContext.InstanceInfo().GetMapInfo()
        if current_map_info is None:
            return _unknown_region_type, RegionTypeName[_unknown_region_type]  # Unknown

        return current_map_info.type, RegionTypeName[current_map_info.type]

    @staticmethod
    def GetDistrict() -> int:
        """Retrieve the district of the current map. (source 289)"""

        if not (char_context := GWContext.Char.GetContext()): return -1
        return char_context.district_number

    @staticmethod
    def GetLanguage() -> tuple[int, str]:
        """Retrieve the language id and name of the current map. (source 296)"""

        unknown_language = 255  # Unknown
        lang_dict = ServerLanguageName

        if not (char_context := GWContext.Char.GetContext()):
            return unknown_language, lang_dict[unknown_language]

        language = char_context.language

        # validate the value
        if language not in lang_dict:
            language = unknown_language

        # now return the validated language
        return language, lang_dict[language]

    @staticmethod
    def GetAmountOfPlayersInInstance() -> int:
        """Retrieve the amount of players in the current instance. (source 320)"""

        if not (world_ctx := GWContext.World.GetContext()):
            return 0
        players = world_ctx.players
        if not players:
            return 0
        return len(players) - 1

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
        """Retrieve the number of foes killed in the current map. (source 369)"""

        if not (world_ctx := GWContext.World.GetContext()):
            return 0
        return world_ctx.foes_killed

    @staticmethod
    def GetFoesToKill() -> int:
        """Retrieve the number of foes to kill in the current map. (source 381)"""

        if not (world_ctx := GWContext.World.GetContext()):
            return 0
        return world_ctx.foes_to_kill

    @staticmethod
    def IsVanquishCompleted() -> bool:
        """Check if the vanquish is completed. (source 393)"""

        if Map.IsVanquishable():
            return Map.GetFoesToKill() == 0
        return False

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

        ``not_valid = 255`` and ``CampaignName`` is keyed ``0..6``
        (``Region_enums.py``: ``Campaign.Core.value`` .. ``Campaign.Undefined.value``),
        so the source's own null path reads a key its own table does not carry and
        raises ``KeyError``. Ported as written.
        """

        not_valid = 255
        current_map_info = GWContext.InstanceInfo().GetMapInfo()
        if current_map_info is None:
            return not_valid, CampaignName[not_valid]

        return current_map_info.campaign, CampaignName[current_map_info.campaign]

    @staticmethod
    def GetContinent() -> tuple[int, str]:
        """Retrieve the continent id and name of the current map. (source 426)

        The same null path as :meth:`GetCampaign`: ``not_valid = 255`` against a
        ``ContinentName`` keyed ``0..6``. Ported as written.
        """

        not_valid = 255
        current_map_info = GWContext.InstanceInfo().GetMapInfo()
        if current_map_info is None:
            return not_valid, ContinentName[not_valid]
        return current_map_info.continent, ContinentName[current_map_info.continent]

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
        """Check if the vanquish is complete. (source 485)"""

        if Map.IsVanquishable():
            return Map.GetFoesToKill() == 0
        return False

    @staticmethod
    def IsMapUnlocked(mapid: int | None = None) -> bool:
        """Check if the map is unlocked. (source 493)

        ``world_ctx.unlocked_maps`` is expected to behave like ``Array<uint32_t>``:
        the source's own comment, and the port's context property answers the same
        list of words.
        """

        # Step 1: determine map_id
        map_id = Map.GetMapID() if mapid is None else mapid
        # Step 2: retrieve context
        world_ctx = GWContext.World.GetContext()
        if not world_ctx:
            return False
        # Step 3: fetch the underlying array
        unlocked_maps = world_ctx.unlocked_maps
        if not unlocked_maps or len(unlocked_maps) == 0:
            return False
        # Step 4: compute index (element in array)
        real_index = map_id // 32
        if real_index >= len(unlocked_maps):
            return False
        # Step 5: compute bit shift
        shift = map_id % 32
        # Step 6: compute bit flag
        flag = 1 << shift
        # Step 7: access array element and test
        # world_ctx.unlocked_maps is expected to behave like Array<uint32_t>
        value = unlocked_maps[real_index]  # becomes uint32_t automatically
        return (value & flag) != 0

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

        ``MapMethods.GetMapInfo`` (``native_src/methods/MapMethods.py:41-55``), ported in
        ``py4gw/map_methods.py``: the array base is the catalog's ``map.area_info_addr`` —
        the same ``imul eax, esi, 0x7C`` scan native's ``NativeSymbol`` makes at ``:27-33``
        — and the record is indexed by ``map_id * sizeof(AreaInfoStruct)``.
        """

        return MapMethods.GetMapInfo(map_id)

    @staticmethod
    def IsEnteringChallenge() -> bool:
        """Check if the character is entering a challenge. (source 706)"""

        CancelEnterMissionButton = Frame(
            FrameId.MissionStatusAndScoreDisplay.C0.C1.CancelEnterMissionButton
        )
        if not CancelEnterMissionButton.exists:
            return False
        return True

    @staticmethod
    def GetMapWorldMapBounds() -> tuple[float, float, float, float]:
        """Retrieve the map's bounds in world-map space. (source 714)"""

        icon_start: Vec2f = Vec2f(*Map.GetIconStartPosition())
        icon_end: Vec2f = Vec2f(*Map.GetIconEndPosition())
        icon_start_dupe: Vec2f = Vec2f(*Map.GetIconStartDupePosition())
        icon_end_dupe: Vec2f = Vec2f(*Map.GetIconEndDupePosition())

        if icon_start.x == 0 and icon_start.y == 0 and icon_end.x == 0 and icon_end.y == 0:
            left = float(icon_start_dupe.x)
            top = float(icon_start_dupe.y)
            right = float(icon_end_dupe.x)
            bottom = float(icon_end_dupe.y)
        else:
            left = float(icon_start.x)
            top = float(icon_start.y)
            right = float(icon_end.x)
            bottom = float(icon_end.y)

        return left, top, right, bottom

    @staticmethod
    def GetMapBoundaries() -> tuple[float, float, float, float]:
        """Retrieve the map boundaries of the current map. (source 734)"""

        if not (map_ctx := GWContext.Map.GetContext()):
            return 0.0, 0.0, 0.0, 0.0

        return map_ctx.start_pos.x, map_ctx.start_pos.y, map_ctx.end_pos.x, map_ctx.end_pos.y

    # -- actions (source 741-889) -----------------------------------------
    #
    # Each of these hands its work to ``ActionQueueManager`` (``Map.py:753, 761, 824, 841, 849,
    # 857, 864, 875, 886``), which is Reforged's per-frame action queue. This port has no action
    # queue and no class here has one — the enqueue is the capability layer's own call path — so
    # the inner action runs where the queue would have run it. The bodies are otherwise the
    # source's, line for line, and the queue call is the only line that differs.

    @staticmethod
    def SkipCinematic() -> None:
        """Skip the cinematic. (source 743)"""

        if not Map.IsInCinematic():
            return

        def _skip_cinematic() -> bool:
            if not Map.IsInCinematic():
                return False
            return MapMethods.SkipCinematic()

        _skip_cinematic()

    @staticmethod
    def Travel(map_id: int) -> None:
        """Travel to a map by its ID. (source 757)"""

        def _travel() -> bool:
            return MapMethods.Travel(map_id, Map.GetRegion()[0], 0, Map.GetLanguage()[0])

        _travel()

    @staticmethod
    def TravelToDistrict(
        map_id: int, district: int = 0, district_number: int = 0
    ) -> None:
        """Travel to a map by its ID and district. (source 765)"""

        def _region_from_district(district: int) -> int:
            from .enums_src.region_enums import District, ServerRegion

            if district == District.International.value:
                return ServerRegion.International.value
            if district == District.American.value:
                return ServerRegion.America.value
            if district in [District.EuropeEnglish.value,
                            District.EuropeFrench.value,
                            District.EuropeGerman.value,
                            District.EuropeItalian.value,
                            District.EuropeSpanish.value,
                            District.EuropePolish.value,
                            District.EuropeRussian.value]:
                return ServerRegion.Europe.value
            if district == District.AsiaKorean.value:
                return ServerRegion.Korea.value
            if district == District.AsiaChinese.value:
                return ServerRegion.China.value
            if district == District.AsiaJapanese.value:
                return ServerRegion.Japan.value

            return Map.GetRegion()[0]

        def _language_from_district(district: int) -> int:
            from .enums_src.region_enums import District, ServerLanguage

            if district == District.EuropeFrench.value:
                return ServerLanguage.French.value
            if district == District.EuropeGerman.value:
                return ServerLanguage.German.value
            if district == District.EuropeItalian.value:
                return ServerLanguage.Italian.value
            if district == District.EuropeSpanish.value:
                return ServerLanguage.Spanish.value
            if district == District.EuropePolish.value:
                return ServerLanguage.Polish.value
            if district == District.EuropeRussian.value:
                return ServerLanguage.Russian.value
            if district in [District.EuropeEnglish.value,
                            District.AsiaKorean.value,
                            District.AsiaChinese.value,
                            District.AsiaJapanese.value,
                            District.International.value,
                            District.American.value]:
                return ServerLanguage.English.value
            return Map.GetLanguage()[0]

        def _travel_to_district() -> bool:
            return MapMethods.Travel(map_id, _region_from_district(district), district_number, _language_from_district(district))

        _travel_to_district()

    @staticmethod
    def TravelToRegion(
        map_id: int, server_region: int, district_number: int, language: int = 0
    ) -> None:
        """Travel to a map by its ID and region. (source 829)"""

        def _travel_to_region() -> bool:
            return MapMethods.Travel(map_id, server_region, district_number, language)

        _travel_to_region()

    @staticmethod
    def TravelGH() -> None:
        """Travel to the Guild Hall. (source 845)"""

        def _travel_gh() -> bool:
            return MapMethods.TravelGH()

        _travel_gh()

    @staticmethod
    def LeaveGH() -> None:
        """Leave the Guild Hall. (source 853)"""

        def _leave_gh() -> bool:
            return MapMethods.LeaveGH()

        _leave_gh()

    @staticmethod
    def EnterChallenge() -> None:
        """Enter the challenge. (source 860)"""

        def _enter_challenge() -> bool:
            return MapMethods.EnterChallenge()

        _enter_challenge()

    @staticmethod
    def CancelEnterChallenge() -> None:
        """Cancel entering the challenge. (source 867)"""

        def _cancel_enter_challenge() -> bool:
            CancelEnterMissionButton = Frame(FrameId.MissionStatusAndScoreDisplay.C0.C1.CancelEnterMissionButton)
            if not CancelEnterMissionButton.exists:
                return False
            CancelEnterMissionButton.click()
            return True

        _cancel_enter_challenge()

    @staticmethod
    def ConfirmEnterChallenge() -> None:
        """Click the extra confirm button some missions show (e.g. Ruins of Surmia). (source 878)"""

        def _confirm_enter_challenge() -> bool:
            ConfirmEnterMissionButton = Frame(FrameId.Root.C2.C6.C100.C2.ConfirmEnterMissionButton)
            if not ConfirmEnterMissionButton.exists:
                return False
            ConfirmEnterMissionButton.click()
            return True

        _confirm_enter_challenge()

    # -- nested: the mission map (source 891-1404) ------------------------

    class MissionMap:
        """The mission-map window. Source: ``Map.py`` lines 891-1404."""

        #: ``Map.py:892-895`` — the click memory the two ``GetLast*ClickCoords`` members
        #: read and write across calls.
        last_right_clicked_coords: tuple[float, float] = (0.0, 0.0)
        last_right_clicked_timestamp: int = 0
        last_left_clicked_coords: tuple[float, float] = (0.0, 0.0)
        last_left_clicked_timestamp: int = 0

        @staticmethod
        def GetFrame():
            """The mission map frame. (source 898)

            The context is the authority on which frame this is — the source's own note — and the
            named lookup in the frame tree is the fallback for the ticks where the context pointer
            reads null, not a replacement for it.
            """

            frame_id = Map.MissionMap.GetFrameID()          # from the context
            if frame_id:
                frame = Frame.from_id(frame_id)
                if frame.exists:
                    return frame

            frame = Frame(FrameId.MissionMap)               # fallback: by name
            return frame if frame.exists else None

        @staticmethod
        def GetFrameID() -> int:
            """Frame id of the mission map, from the context. (source 916)"""

            if not (misison_map_ctx := GWContext.MissionMap.GetContext()):
                return 0
            return misison_map_ctx.frame_id

        @staticmethod
        def IsWindowOpen() -> bool:
            """Check if the mission map window is open. (source 923)"""

            if not (frame_info := Map.MissionMap.GetFrame()):
                return False
            return frame_info.exists

        @staticmethod
        def OpenWindow() -> None:
            """Open the mission map window. (source 930)

            The source queues ``Routines.Yield.Keybinds.OpenMissionMap()``, whose whole action is
            ``Keybinds.PressKeybind(ControlAction_OpenMissionMap.value, 75)``
            (``routines_src/yield_src/keybinds.py:70-71``) and whose tree presses
            ``UIManager.Keydown(keybind_index, 0)`` and then ``UIManager.Keyup(keybind_index, 0)``
            (``routines_src/behaviourtrees_src/keybinds.py:101,119``). This port carries no
            coroutine driver and no behaviour tree, so the press is made where the queue would
            have run it. **The one thing with no home here is the tree's 75 ms hold between the
            down and the up** (``:139``, ``aftercast_ms=duration_ms``): there is no scheduler to
            hold a key with, and a sleep of this port's own would be a throttle the source does
            not have.
            """

            from .enums_src.ui_enums import ControlAction

            if Map.MissionMap.IsWindowOpen():
                return
            UIManager.Keydown(ControlAction.ControlAction_OpenMissionMap.value, 0)
            UIManager.Keyup(ControlAction.ControlAction_OpenMissionMap.value, 0)

        @staticmethod
        def CloseWindow() -> None:
            """Close the mission map window. (source 937)

            The source queues ``OpenMissionMap`` — the same keybind as ``OpenWindow``
            (``Map.py:943``), not a close — and this is that keybind, pressed on the source's own
            guard rather than on its window state.
            """

            from .enums_src.ui_enums import ControlAction

            if not (frame_info := Map.MissionMap.GetFrame()):
                return
            UIManager.Keydown(ControlAction.ControlAction_OpenMissionMap.value, 0)
            UIManager.Keyup(ControlAction.ControlAction_OpenMissionMap.value, 0)

        @staticmethod
        def IsMouseOver() -> bool:
            """Not built: it reads the client's in-process ImGui.

            The source is ``frame_info.is_mouse_over()`` (``Map.py:951``), whose body is
            ``PyImGui.get_io().mouse_pos_x/y`` and ``ImGui.is_mouse_in_rect``
            (``FrameTree/frame.py:1430-1441``). ``PyImGui`` is the injected runtime's own ImGui
            context; this project installs none and there is no way to install it, so this member
            reports that instead of approximating a mouse position from outside the client.
            ``Frame.is_mouse_over`` carries the same divergence.
            """

            raise _unported(
                "MissionMap.IsMouseOver",
                "PyImGui.get_io() — the injected runtime's in-process ImGui context, which this "
                "project installs nowhere and can install nowhere (Frame.is_mouse_over, "
                "FrameTree/frame.py:1430-1441)",
            )

        @staticmethod
        def GetLastClickCoords() -> tuple[float, float]:
            """Not built: the frame IO-event list is filled in-process.

            The source walks ``frame_info.io_events()`` (``Map.py:959``) —
            ``UIManager.GetIOEventsForFrame``, whose only producer is
            ``UIManager._UpdateFrameIOEvents``, and that reads ``PyImGui.get_io()`` and
            ``PyImGui.is_mouse_clicked`` (``UIManager.py:74-88``). Nothing in the client holds
            this list; it is the injected runtime's own recorder, so the answer is its absence
            rather than a stand-in reading of the mouse.
            """

            raise _unported(
                "MissionMap.GetLastClickCoords",
                "UIManager.GetIOEventsForFrame, whose only producer is "
                "UIManager._UpdateFrameIOEvents — PyImGui.get_io() and PyImGui.is_mouse_clicked "
                "(UIManager.py:74-88), the injected runtime's own recorder",
            )

        @staticmethod
        def GetLastRightClickCoords() -> tuple[float, float]:
            """Not built: the same in-process IO-event list as ``GetLastClickCoords``."""

            raise _unported(
                "MissionMap.GetLastRightClickCoords",
                "UIManager.GetIOEventsForFrame, whose only producer is "
                "UIManager._UpdateFrameIOEvents — PyImGui.get_io() and PyImGui.is_mouse_clicked "
                "(UIManager.py:74-88), the injected runtime's own recorder",
            )

        @staticmethod
        def GetMissionMapWindowCoords() -> tuple[float, float, float, float]:
            """Get the window coordinates of the mission map. (source 1011)"""

            if not (frame_info := Map.MissionMap.GetFrame()):
                return 0.0, 0.0, 0.0, 0.0
            return frame_info.coords()

        @staticmethod
        def GetMissionMapContentsCoords() -> tuple[float, float, float, float]:
            """Get the contents coordinates of the mission map. (source 1018)"""

            if not (frame_info := Map.MissionMap.GetFrame()):
                return 0.0, 0.0, 0.0, 0.0
            return frame_info.content_coords()

        @staticmethod
        def GetScale() -> tuple[float, float]:
            """Get the scale of the mission map. (source 1025)"""

            if not (frame_info := Map.MissionMap.GetFrame()):
                return 0.0, 0.0
            return frame_info.viewport_scale()

        @staticmethod
        def GetZoom() -> float:
            """Get the zoom level of the mission map. (source 1032)

            ``Gameplay.GetContext().mission_map_zoom``, and ``1.0`` when the context is
            unavailable — the source's own default (``Map.py:1031-1036``). ``Utils.GwinchToPixels``
            and ``Utils.PixelsToGwinch`` read it (``py4gwcorelib_src/Utils.py:156,168``).
            """

            if not (gameplay_ctx := GWContext.Gameplay.GetContext()):
                return 1.0
            return gameplay_ctx.mission_map_zoom

        @staticmethod
        def GetAdjustedZoom(_zoom: float, zoom_offset: float = 0.0) -> float:
            """Adjust the zoom level of the mission map. (source 1039)"""

            zoom = _zoom + zoom_offset
            if zoom == 1.0:
                return zoom + 0.0

            if 1.0 < zoom <= 1.5:
                return zoom + 0.0449

            if zoom > 1.5:
                step = 0.5
                # Snap to step count safely
                times = int((zoom - 1.5 + 1e-6) // step)  # avoids float precision issues
                return zoom + (0.0449 + (0.02449 * times))

            return zoom + 0.0

        @staticmethod
        def GetCenter() -> tuple[float, float]:
            """Get the player position coordinates of the mission map. (source 1057)"""

            dimensions = Map.MissionMap.GetMissionMapContentsCoords()
            center_x = dimensions[0] + (dimensions[2] - dimensions[0]) / 2.0
            center_y = dimensions[1] + (dimensions[3] - dimensions[1]) / 2.0
            return center_x, center_y

        #: ``Map.py:1066`` — the last non-zero pan offset, held by ``GetPanOffset`` rather than
        #: answering ``(0.0, 0.0)`` on the tick the context reads null.
        _last_pan_offset: tuple[float, float] = (0.0, 0.0)

        @staticmethod
        def GetPanOffset() -> tuple[float, float]:
            """Pan offset of the mission map - what centres it on the player. (source 1069)

            Both the context and its subcontext read null for the odd tick, and the source's own
            note says why returning ``(0.0, 0.0)`` there is not harmless: it means "panned to the
            world origin", so the whole overlay re-anchors on ``0,0`` instead of the player for
            that frame. The last real offset is held instead.
            """

            if (misison_map_ctx := GWContext.MissionMap.GetContext()):
                subcontext = misison_map_ctx.subcontext2
                if subcontext is not None:
                    offset = subcontext.mission_map_pan_offset.to_tuple()
                    if offset != (0.0, 0.0):
                        Map.MissionMap._last_pan_offset = offset
                        return offset
            return Map.MissionMap._last_pan_offset

        @staticmethod
        def GetMapScreenCenter() -> tuple[float, float]:
            """Get the map screen center coordinates. (source 1088)"""

            coords = Map.MissionMap.GetMissionMapContentsCoords()
            top_left: Vec2f = Vec2f(coords[0], coords[1])
            bottom_right: Vec2f = Vec2f(coords[2], coords[3])
            r_x = top_left.x + (bottom_right.x - top_left.x) / 2.0
            r_y = top_left.y + (bottom_right.y - top_left.y) / 2.0
            return r_x, r_y

        class MapProjection:
            """Mission-map coordinate transforms. Source: ``Map.py`` 1097-1403."""

            @staticmethod
            def GamePosToWorldMap(x: float, y: float) -> tuple[float, float]:
                """Convert game-space coordinates (gwinches) to world map coordinates. (source 1099)"""

                gwinches = 96.0

                # Step 1: Get map bounds in UI space
                left, top, right, bottom = Map.GetMapWorldMapBounds()

                # Step 2: Get game-space boundaries from map context
                boundaries = Map.GetMapBoundaries()
                if len(boundaries) < 4:
                    return 0.0, 0.0  # fail-safe

                min_x = boundaries[0]
                max_y = boundaries[3]

                # Step 3: Compute origin on the world map based on boundary distances
                origin_x = left + abs(min_x) / gwinches
                origin_y = top + abs(max_y) / gwinches

                # Step 4: Convert game-space (gwinches) to world map space (screen)
                screen_x = (x / gwinches) + origin_x
                screen_y = (-y / gwinches) + origin_y  # Inverted Y

                return screen_x, screen_y

            @staticmethod
            def WorldMapToGamePos(x: float, y: float) -> tuple[float, float]:
                """Convert world map coordinates to game-space coordinates. (source 1133)"""

                gwinches = 96.0

                # Step 1: Get the world map bounds in screen-space
                left, top, right, bottom = Map.GetMapWorldMapBounds()

                # Step 3: Get game-space boundaries (min_x, ..., max_y)
                bounds = Map.GetMapBoundaries()
                if len(bounds) < 4:
                    return 0.0, 0.0

                min_x = bounds[0]
                max_y = bounds[3]

                # Step 4: Compute the world map anchor point (same logic as forward)
                origin_x = left + abs(min_x) / gwinches
                origin_y = top + abs(max_y) / gwinches

                # Step 5: Convert world map coords to game-space
                game_x = (x - origin_x) * gwinches
                game_y = (y - origin_y) * gwinches * -1.0  # Inverted Y

                return game_x, game_y

            @staticmethod
            def WorldMapToScreen(
                x: float, y: float, zoom_offset=0.0
            ) -> tuple[float, float]:
                """Convert world map coordinates to screen coordinates. (source 1169)"""

                # World map coordinates (x, y) to screen space
                pan_offset_x, pan_offset_y = Map.MissionMap.GetPanOffset()
                offset_x = x - pan_offset_x
                offset_y = y - pan_offset_y

                scale_x, scale_y = Map.MissionMap.GetScale()
                scaled_x = offset_x * scale_x
                scaled_y = offset_y * scale_y

                zoom = Map.MissionMap.GetZoom() + zoom_offset
                mission_map_screen_center_x, mission_map_screen_center_y = Map.MissionMap.GetMapScreenCenter()
                screen_x = scaled_x * zoom + mission_map_screen_center_x
                screen_y = scaled_y * zoom + mission_map_screen_center_y

                return screen_x, screen_y

            @staticmethod
            def ScreenToWorldMap(
                screen_x: float, screen_y: float, zoom_offset=0.0
            ) -> tuple[float, float]:
                """Convert screen coordinates to world map coordinates. (source 1197)"""

                # Screen coordinates to world map coordinates (x, y)
                if not Map.MissionMap.IsWindowOpen():
                    return 0.0, 0.0

                zoom = Map.MissionMap.GetZoom() + zoom_offset
                scale_x, scale_y = Map.MissionMap.GetScale()
                center_x, center_y = Map.MissionMap.GetMapScreenCenter()
                pan_offset_x, pan_offset_y = Map.MissionMap.GetPanOffset()

                # Invert transform from screen space back to world space
                scaled_x = (screen_x - center_x) / zoom
                scaled_y = (screen_y - center_y) / zoom

                world_x = (scaled_x / scale_x) + pan_offset_x
                world_y = (scaled_y / scale_y) + pan_offset_y

                return world_x, world_y

            @staticmethod
            def GameMapToScreen(
                x: float, y: float, zoom_offset: float = 0.0
            ) -> tuple[float, float]:
                """Convert game-space coordinates to screen coordinates. (source 1225)"""

                world_x, world_y = Map.MissionMap.MapProjection.GamePosToWorldMap(x, y)
                return Map.MissionMap.MapProjection.WorldMapToScreen(world_x, world_y, zoom_offset)

            @staticmethod
            def ScreenToGameMap(
                x: float, y: float, zoom_offset: float = 0.0
            ) -> tuple[float, float]:
                """Convert screen coordinates to game-space coordinates. (source 1241)"""

                world_x, world_y = Map.MissionMap.MapProjection.ScreenToWorldMap(x, y, zoom_offset)
                return Map.MissionMap.MapProjection.WorldMapToGamePos(world_x, world_y)

            @staticmethod
            def NormalizedScreenToScreen(x: float, y: float) -> tuple[float, float]:
                """Convert normalized screen coordinates [-1, 1] to screen coordinates. (source 1254)"""

                # Convert normalized [-1,1] → [0,1]
                adjusted_x = (x + 1.0) * 0.5
                adjusted_y = (1.0 - y) * 0.5

                # Use *exact* mission-map window bounds
                left, top, right, bottom = Map.MissionMap.GetMissionMapContentsCoords()

                width = right - left
                height = bottom - top

                screen_x = left + adjusted_x * width
                screen_y = top + adjusted_y * height

                return screen_x, screen_y

            @staticmethod
            def ScreenToNormalizedScreen(
                screen_x: float, screen_y: float
            ) -> tuple[float, float]:
                """Convert screen coordinates to normalized screen coordinates [-1, 1]. (source 1278)"""

                # Compute width and height of the map frame
                coords = Map.MissionMap.GetMissionMapWindowCoords()
                left, top, right, bottom = int(coords[0]-5), int(coords[1]-1), int(coords[2]+5), int(coords[3]+2)
                width = right - left
                height = bottom - top

                # Relative position in [0, 1] range
                rel_x = (screen_x - left) / width
                rel_y = (screen_y - top) / height

                # Convert to normalized [-1, 1], Y is inverted
                norm_x = rel_x * 2.0 - 1.0
                norm_y = (1.0 - rel_y) * 2.0 - 1.0

                return norm_x, norm_y

            @staticmethod
            def NormalizedScreenToWorldMap(
                x: float, y: float, zoom_offset: float = 0.0
            ) -> tuple[float, float]:
                """Convert normalized screen coordinates [-1, 1] to world map coordinates. (source 1303)"""

                screen_x, screen_y = Map.MissionMap.MapProjection.NormalizedScreenToScreen(x, y)
                return Map.MissionMap.MapProjection.ScreenToWorldMap(screen_x, screen_y, zoom_offset)

            @staticmethod
            def NormalizedScreenToGamePos(x: float, y: float) -> tuple[float, float]:
                """Convert normalized screen coordinates [-1, 1] to game-space coordinates. (source 1316)"""

                world_x, world_y = Map.MissionMap.MapProjection.NormalizedScreenToScreen(x, y)
                return Map.MissionMap.MapProjection.ScreenToGamePos(world_x, world_y)

            @staticmethod
            def GamePosToNormalizedScreen(x: float, y: float) -> tuple[float, float]:
                """Convert game-space coordinates (gwinches) to normalized screen coordinates. (source 1328)"""

                screen_x, screen_y = Map.MissionMap.MapProjection.GameMapToScreen(x, y)
                return Map.MissionMap.MapProjection.ScreenToNormalizedScreen(screen_x, screen_y)

            @staticmethod
            def GamePosToScreen(
                x: float, y: float, zoom_offset: float = 0.0
            ) -> tuple[float, float]:
                """Convert game-space coordinates (gwinches) to screen coordinates. (source 1340)"""

                world_x, world_y = Map.MissionMap.MapProjection.GamePosToWorldMap(x, y)
                return Map.MissionMap.MapProjection.WorldMapToScreen(world_x, world_y, zoom_offset)

            @staticmethod
            def ScreenToGamePos(
                x: float, y: float, zoom_offset: float = 0.0
            ) -> tuple[float, float]:
                """Convert screen coordinates to game-space coordinates. (source 1354)"""

                world_x, world_y = Map.MissionMap.MapProjection.ScreenToWorldMap(x, y, zoom_offset)
                return Map.MissionMap.MapProjection.WorldMapToGamePos(world_x, world_y)

            @staticmethod
            def WorldPosToMissionMapScreen(
                x: float, y: float, zoom_offset: float = 0.0
            ) -> tuple[float, float]:
                """Convert world position coordinates to mission map screen coordinates. (source 1368)"""

                # 1. Convert game position (gwinches) to world map coordinates
                world_x, world_y = Map.MissionMap.MapProjection.GamePosToWorldMap(x, y)

                # 2. Project onto the mission map screen space
                screen_x, screen_y = Map.MissionMap.MapProjection.WorldMapToScreen(world_x, world_y, zoom_offset)

                return screen_x, screen_y

            @staticmethod
            def ScreenToWorldPos(
                screen_x: float, screen_y: float, zoom_offset=0.0
            ) -> tuple[float, float]:
                """Convert mission map screen coordinates to world position coordinates. (source 1388)"""

                # Step 1: Convert from screen-space to world map coordinates
                world_x, world_y = Map.MissionMap.MapProjection.ScreenToWorldMap(screen_x, screen_y, zoom_offset)

                # Step 2: Convert from world map coordinates to in-game game coordinates (gwinches)
                game_x, game_y = Map.MissionMap.MapProjection.WorldMapToGamePos(world_x, world_y)

                return game_x, game_y

    # -- nested: the mini map (source 1406-1851) --------------------------

    class MiniMap:
        """The compass/mini-map window. Source: ``Map.py`` lines 1406-1851."""

        #: ``Map.py:1407-1410`` — the same click memory as ``MissionMap``'s.
        last_right_clicked_coords: tuple[float, float] = (0.0, 0.0)
        last_right_clicked_timestamp: int = 0
        last_left_clicked_coords: tuple[float, float] = (0.0, 0.0)
        last_left_clicked_timestamp: int = 0

        @staticmethod
        def GetFrame():
            """Get the frame info of the mission map. (source 1412)"""

            return Frame(FrameId.Compass)

        @staticmethod
        def GetFrameID() -> int:
            """Get the frame ID of the mini map. (source 1417)"""

            if not (mini_map_frame := Map.MiniMap.GetFrame()):
                return 0

            return mini_map_frame.frame_id

        @staticmethod
        def IsWindowOpen() -> bool:
            """Check if the mini map window is open. (source 1425)"""

            if not (mini_map_frame := Map.MiniMap.GetFrame()):
                return False
            return mini_map_frame.exists

        @staticmethod
        def OpenWindow() -> None:
            """Open the mini map window. (source 1432)"""

            from .enums_src.ui_enums import WindowID

            if Map.MiniMap.IsWindowOpen():
                return
            UIManager.SetWindowVisible(WindowID.WindowID_Compass, True)

        @staticmethod
        def CloseWindow() -> None:
            """Close the mini map window. (source 1440)"""

            from .enums_src.ui_enums import WindowID

            if not Map.MiniMap.IsWindowOpen():
                return
            UIManager.SetWindowVisible(WindowID.WindowID_Compass, False)

        @staticmethod
        def IsMouseOver() -> bool:
            """Not built: it reads the client's in-process ImGui.

            ``mini_map_frame.is_mouse_over()`` (``Map.py:1452``) is
            ``PyImGui.get_io().mouse_pos_x/y`` and ``ImGui.is_mouse_in_rect``
            (``FrameTree/frame.py:1430-1441``). ``PyImGui`` is the injected runtime's own ImGui
            context; this project installs none and there is no way to install it.
            """

            raise _unported(
                "MiniMap.IsMouseOver",
                "PyImGui.get_io() — the injected runtime's in-process ImGui context, which this "
                "project installs nowhere and can install nowhere (Frame.is_mouse_over, "
                "FrameTree/frame.py:1430-1441)",
            )

        @staticmethod
        def GetLastClickCoords() -> tuple[float, float]:
            """Not built: the frame IO-event list is filled in-process.

            The source walks ``frame_info.io_events()`` (``Map.py:1460``), whose only producer is
            ``UIManager._UpdateFrameIOEvents`` — and that reads ``PyImGui.get_io()`` and
            ``PyImGui.is_mouse_clicked`` (``UIManager.py:74-88``).
            """

            raise _unported(
                "MiniMap.GetLastClickCoords",
                "UIManager.GetIOEventsForFrame, whose only producer is "
                "UIManager._UpdateFrameIOEvents — PyImGui.get_io() and PyImGui.is_mouse_clicked "
                "(UIManager.py:74-88), the injected runtime's own recorder",
            )

        @staticmethod
        def GetLastRightClickCoords() -> tuple[float, float]:
            """Not built: the same in-process IO-event list as ``GetLastClickCoords``."""

            raise _unported(
                "MiniMap.GetLastRightClickCoords",
                "UIManager.GetIOEventsForFrame, whose only producer is "
                "UIManager._UpdateFrameIOEvents — PyImGui.get_io() and PyImGui.is_mouse_clicked "
                "(UIManager.py:74-88), the injected runtime's own recorder",
            )

        @staticmethod
        def GetWindowCoords() -> tuple[float, float, float, float]:
            """Get the coordinates of the mini map. (source 1505)"""

            if not (mini_map_frame := Map.MiniMap.GetFrame()):
                return 0.0, 0.0, 0.0, 0.0
            return mini_map_frame.coords()

        @staticmethod
        def IsLocked() -> bool:
            """Check if the mini map is locked. (source 1512)"""

            return UIManager.GetBoolPreference(FlagPreference.LockCompassRotation)

        @staticmethod
        def GetPanOffset() -> list[float]:
            """Get the pan offset of the mini map. (source 1517)"""

            return [0.0, 0.0]

        @staticmethod
        def GetScale(
            coords: tuple[float, float, float, float] | None = None,
        ) -> float:
            """Get the scale of the mini map. (source 1522)"""

            if coords is None:
                left, top, right, bottom = Map.MiniMap.GetWindowCoords()
            else:
                left, top, right, bottom = coords

            height = bottom - top
            diff = height - (height / 1.05)
            left += diff
            right -= diff

            scale = (right - left) / 2.0

            return scale

        @staticmethod
        def GetRotation() -> float:
            """Get the rotation of the mini map. (source 1539)"""

            from .camera import Camera

            if Map.MiniMap.IsLocked():
                return 0
            else:
                return Camera.GetCurrentYaw() - math.pi / 2

        @staticmethod
        def GetZoom() -> float:
            """Get the zoom level of the mini map. (source 1549)"""

            return 1.0

        @staticmethod
        def GetMapScreenCenter(
            coords: tuple[float, float, float, float] | None = None,
        ) -> tuple[float, float]:
            """Get the map screen center coordinates. (source 1556)"""

            if coords is None:
                left, top, right, bottom = Map.MiniMap.GetWindowCoords()
            else:
                left, top, right, bottom = coords
            height = bottom - top
            diff = height - (height / 1.05)

            top += diff
            left += diff
            right -= diff

            center_x = (left + right) / 2.0
            center_y = top + (right - left) / 2.0

            return center_x, center_y

        class MapProjection:
            """Compass coordinate transforms. Source: ``Map.py`` 1575-1850."""

            @staticmethod
            def GamePosToWorldMap(x: float, y: float) -> tuple[float, float]:
                """Convert game-space coordinates to world-map space. (source 1577)"""

                gwinches = 96.0

                # Step 1: Get map bounds in UI space
                left, top, right, bottom = Map.GetMapWorldMapBounds()

                # Step 2: Get game-space boundaries from map context
                boundaries = Map.GetMapBoundaries()
                if len(boundaries) < 4:
                    return 0.0, 0.0  # fail-safe

                min_x = boundaries[0]
                max_y = boundaries[3]
                # Step 3: Compute origin on the world map based on boundary distances
                origin_x = left + abs(min_x) / gwinches
                origin_y = top + abs(max_y) / gwinches

                # Step 4: Convert game-space (gwinches) to world map space (screen)
                screen_x = (x / gwinches) + origin_x
                screen_y = (-y / gwinches) + origin_y  # Inverted Y

                return screen_x, screen_y

            @staticmethod
            def WorldMapToGamePos(x: float, y: float) -> tuple[float, float]:
                """Convert world-map coordinates to game space. (source 1601)"""

                gwinches = 96.0
                left, top, right, bottom = Map.GetMapWorldMapBounds()
                bounds = Map.GetMapBoundaries()
                if len(bounds) < 4:
                    return 0.0, 0.0

                min_x = bounds[0]
                max_y = bounds[3]

                # Step 4: Compute the world map anchor point (same logic as forward)
                origin_x = left + abs(min_x) / gwinches
                origin_y = top + abs(max_y) / gwinches

                # Step 5: Convert world map coords to game-space
                game_x = (x - origin_x) * gwinches
                game_y = (y - origin_y) * gwinches * -1.0  # Inverted Y

                return game_x, game_y

            @staticmethod
            def WorldMapToScreen(x: float, y: float) -> tuple[float, float]:
                """Convert world-map coordinates to screen space. (source 1622)"""

                # World map coordinates (x, y) to screen space
                pan_offset_x, pan_offset_y = Map.MiniMap.GetPanOffset()
                offset_x = x - pan_offset_x
                offset_y = y - pan_offset_y

                scale = Map.MiniMap.GetScale()
                scaled_x = offset_x * scale
                scaled_y = offset_y * scale

                zoom = Map.MiniMap.GetZoom()
                mission_map_screen_center_x, mission_map_screen_center_y = Map.MiniMap.GetMapScreenCenter()
                screen_x = scaled_x * zoom + mission_map_screen_center_x
                screen_y = scaled_y * zoom + mission_map_screen_center_y

                return screen_x, screen_y

            @staticmethod
            def ScreenToWorldMap(
                screen_x: float, screen_y: float
            ) -> tuple[float, float]:
                """Convert screen coordinates to world-map space. (source 1640)"""

                zoom = Map.MiniMap.GetZoom()
                scale = Map.MiniMap.GetScale()
                center_x, center_y = Map.MiniMap.GetMapScreenCenter()
                pan_offset_x, pan_offset_y = Map.MiniMap.GetPanOffset()

                # Invert transform from screen space back to world space
                scaled_x = (screen_x - center_x) / zoom
                scaled_y = (screen_y - center_y) / zoom

                world_x = (scaled_x / scale) + pan_offset_x
                world_y = (scaled_y / scale) + pan_offset_y

                return world_x, world_y

            @staticmethod
            def GameMapToScreen(x: float, y: float) -> tuple[float, float]:
                """Convert game-map coordinates to screen space. (source 1657)"""

                world_x, world_y = Map.MiniMap.MapProjection.GamePosToWorldMap(x, y)
                return Map.MiniMap.MapProjection.WorldMapToScreen(world_x, world_y)

            @staticmethod
            def ScreenToGameMap(x: float, y: float) -> tuple[float, float]:
                """Convert screen coordinates to game-map space. (source 1662)"""

                world_x, world_y = Map.MiniMap.MapProjection.ScreenToWorldMap(x, y)
                return Map.MiniMap.MapProjection.WorldMapToGamePos(world_x, world_y)

            @staticmethod
            def NormalizedScreenToScreen(x: float, y: float) -> tuple[float, float]:
                """Convert normalized screen coordinates to screen space. (source 1667)"""

                # Convert from [-1, 1] to [0, 1] with Y-inversion
                norm_x, norm_y = x, y
                adjusted_x = (norm_x + 1.0) * 0.5
                adjusted_y = (1.0 - norm_y) * 0.5

                # Compute width and height of the map frame
                coords = Map.MiniMap.GetWindowCoords()
                left, top, right, bottom = int(coords[0]), int(coords[1]), int(coords[2]), int(coords[3])
                width = right - left
                height = bottom - top

                screen_x = left + adjusted_x * width
                screen_y = top + adjusted_y * height

                return screen_x, screen_y

            @staticmethod
            def ScreenToNormalizedScreen(
                screen_x: float, screen_y: float
            ) -> tuple[float, float]:
                """Convert screen coordinates to normalized screen space. (source 1685)"""

                # Compute width and height of the map frame
                coords = Map.MiniMap.GetWindowCoords()
                left, top, right, bottom = int(coords[0]), int(coords[1]), int(coords[2]), int(coords[3])
                width = right - left
                height = bottom - top

                # Relative position in [0, 1] range
                rel_x = (screen_x - left) / width
                rel_y = (screen_y - top) / height

                # Convert to normalized [-1, 1], Y is inverted
                norm_x = rel_x * 2.0 - 1.0
                norm_y = (1.0 - rel_y) * 2.0 - 1.0

                return norm_x, norm_y

            @staticmethod
            def NormalizedScreenToWorldMap(x: float, y: float) -> tuple[float, float]:
                """Convert normalized screen coordinates to world-map space. (source 1703)"""

                screen_x, screen_y = Map.MiniMap.MapProjection.NormalizedScreenToScreen(x, y)
                return Map.MiniMap.MapProjection.ScreenToWorldMap(screen_x, screen_y)

            @staticmethod
            def NormalizedScreenToGamePos(x: float, y: float) -> tuple[float, float]:
                """Convert normalized screen coordinates to game space. (source 1708)"""

                world_x, world_y = Map.MiniMap.MapProjection.NormalizedScreenToScreen(x, y)
                return Map.MiniMap.MapProjection.ScreenToGamePos(world_x, world_y)

            @staticmethod
            def GamePosToNormalizedScreen(x: float, y: float) -> tuple[float, float]:
                """Convert game-space coordinates to normalized screen space. (source 1713)"""

                screen_x, screen_y = Map.MiniMap.MapProjection.GameMapToScreen(x, y)
                return Map.MiniMap.MapProjection.ScreenToNormalizedScreen(screen_x, screen_y)

            @staticmethod
            def GamePosToScreen(game_x: float, game_y: float,
                                player_x: float | None = None, player_y: float | None = None,
                                center_x: float | None = None, center_y: float | None = None,
                                scale: float | None = None, rotation: float | None = None) -> tuple[float, float]:
                """Convert a game position to a position on the screen relative to the compass. (source 1718)"""

                from .player import Player

                if player_x is None or player_y is None:
                    player_x, player_y = Player.GetXY()
                if center_x is None or center_y is None:
                    center_x, center_y = Map.MiniMap.GetMapScreenCenter()
                if scale is None:
                    scale = Map.MiniMap.GetScale()
                if rotation is None:
                    rotation = Map.MiniMap.GetRotation()

                if player_x is not None and player_y is not None:
                    x = center_x - (player_x - game_x)*scale/5000
                    y = center_y + (player_y - game_y)*scale/5000
                else:
                    x = center_x - (game_x)*scale/5000
                    y = center_y + (game_y)*scale/5000

                screen_x = center_x + math.cos(rotation)*(x - center_x) - math.sin(rotation)*(y - center_y)
                screen_y = center_y + math.sin(rotation)*(x - center_x) + math.cos(rotation)*(y - center_y)

                return screen_x, screen_y

            @staticmethod
            def ScreenToGamePos(screen_x: float, screen_y: float,
                                player_x: float | None = None, player_y: float | None = None,
                                center_x: float | None = None, center_y: float | None = None,
                                scale: float | None = None, rotation: float | None = None) -> tuple[float, float]:
                """Convert a screen position relative to the compass to a position in the game. (source 1748)"""

                from .player import Player

                if player_x is None or player_y is None:
                    player_x, player_y = Player.GetXY()
                if center_x is None or center_y is None:
                    center_x, center_y = Map.MiniMap.GetMapScreenCenter()
                if scale is None:
                    scale = Map.MiniMap.GetScale()
                if rotation is None:
                    rotation = Map.MiniMap.GetRotation()

                x = center_x + math.cos(-rotation)*(screen_x - center_x) - math.sin(-rotation)*(screen_y - center_y)
                y = center_y + math.sin(-rotation)*(screen_x - center_x) + math.cos(-rotation)*(screen_y - center_y)

                if player_x is not None and player_y is not None:
                    game_x = player_x + (x - center_x)*5000/scale
                    game_y = player_y - (y - center_y)*5000/scale
                else:
                    game_x = (x - center_x)*5000/scale
                    game_y = -(y - center_y)*5000/scale

                return game_x, game_y

            @staticmethod
            def WorldPosToMiniMapScreen(x: float, y: float) -> tuple[float, float]:
                """Convert world position coordinates to mini map screen coordinates. (source 1778)"""

                # 1. Convert game position (gwinches) to world map coordinates
                world_x, world_y = Map.MiniMap.MapProjection.GamePosToWorldMap(x, y)

                # 2. Project onto the mission map screen space
                screen_x, screen_y = Map.MiniMap.MapProjection.WorldMapToScreen(world_x, world_y)

                return screen_x, screen_y

            @staticmethod
            def ScreenToWorldPos(
                screen_x: float, screen_y: float
            ) -> tuple[float, float]:
                """Convert mini-map screen coordinates to world space. (source 1789)"""

                # Step 1: Convert from screen-space to world map coordinates
                world_x, world_y = Map.MiniMap.MapProjection.ScreenToWorldMap(screen_x, screen_y)

                # Step 2: Convert from world map coordinates to in-game game coordinates (gwinches)
                game_x, game_y = Map.MiniMap.MapProjection.WorldMapToGamePos(world_x, world_y)

                return game_x, game_y

            @staticmethod
            def ComputedPathingGeometryToScreen(map_bounds: tuple[float, float, float, float] | None = None,
                                                   player_x: float | None = None, player_y: float | None = None,
                                                   center_x: float | None = None, center_y: float | None = None,
                                                   scale: float | None = None, rotation: float | None = None) -> tuple[float, float, float]:
                """Convert a screen position of pathing geometry to a screen position relative to the compass. (source 1800)"""

                from .player import Player

                # Step 1: Get map bounds
                if not map_bounds:
                    map_bounds = Map.GetMapBoundaries()

                map_min_x = map_bounds[0]
                map_min_y = map_bounds[1]
                map_max_x = map_bounds[2]
                map_max_y = map_bounds[3]
                map_mid_x = (map_min_x + map_max_x)/2
                map_mid_y = (map_min_y + map_max_y)/2

                # Step 2: Get compass position/scale/rotation
                if center_x is None or center_y is None:
                    center_x, center_y = Map.MiniMap.GetMapScreenCenter()
                if scale is None:
                    scale = Map.MiniMap.GetScale()
                if rotation is None:
                    rotation = Map.MiniMap.GetRotation()

                # Step 3: Get Player position
                if player_x is None or player_y is None:
                    player_x, player_y = Player.GetXY()

                # Step 4: Get geometry zoom
                zoom = scale/5000

                # Step 5: Get Player position geometry offset
                if player_x is None or player_y is None:
                    player_x, player_y = 0.0, 0.0
                x_pos_offset = map_mid_x - player_x
                y_pos_offset = map_mid_y - player_y

                # Step 6: Get rotation offset
                player_x_rotated = player_x*math.cos(-rotation) - player_y*math.sin(-rotation)
                player_y_rotated = player_x*math.sin(-rotation) + player_y*math.cos(-rotation)

                x_rot_offset = player_x - player_x_rotated
                y_rot_offset = player_y - player_y_rotated

                # Step 7: Get final offset
                x_offset = zoom*(x_pos_offset + x_rot_offset - (map_max_x + map_min_x)/2)
                y_offset = zoom*(y_pos_offset + y_rot_offset - (map_max_y + map_min_y)/2)

                return x_offset, y_offset, zoom
    # -- nested: the world map (source 1853-2023) -------------------------

    class WorldMap:
        """The world-map window. Source: ``Map.py`` lines 1853-2023."""

        #: ``Map.py:1854-1857`` — the same click memory as ``MissionMap``'s.
        last_right_clicked_coords: tuple[float, float] = (0.0, 0.0)
        last_right_clicked_timestamp: int = 0
        last_left_clicked_coords: tuple[float, float] = (0.0, 0.0)
        last_left_clicked_timestamp: int = 0

        @staticmethod
        def GetFrameID() -> int:
            """Frame id of the world map. (source 1859)"""

            if not (world_map_ctx := GWContext.WorldMap.GetContext()):
                return 0
            return world_map_ctx.frame_id

        @staticmethod
        def GetFrame():
            """The world-map frame. (source 1866)"""

            if not (frame_id := Map.WorldMap.GetFrameID()):
                return None
            return Frame.from_id(frame_id)

        @staticmethod
        def IsWindowOpen() -> bool:
            """Check if the world map window is open. (source 1873)"""

            if not (frame_info := Map.WorldMap.GetFrame()):
                return False
            return frame_info.exists

        @staticmethod
        def OpenWindow() -> None:
            """Open the world map window. (source 1880)

            The source queues ``Routines.Yield.Keybinds.OpenWorldMap()``, whose action is
            ``Keybinds.PressKeybind(ControlAction_OpenWorldMap.value, 75)``
            (``routines_src/yield_src/keybinds.py:98-99``) and whose tree presses
            ``UIManager.Keydown``/``UIManager.Keyup`` (``routines_src/behaviourtrees_src/
            keybinds.py:101,119``). No coroutine driver or behaviour tree is carried here, so the
            press is made where the queue would have run it; the tree's 75 ms hold between the two
            has no home here and is not stood in for.
            """

            from .enums_src.ui_enums import ControlAction

            if Map.WorldMap.IsWindowOpen():
                return
            UIManager.Keydown(ControlAction.ControlAction_OpenWorldMap.value, 0)
            UIManager.Keyup(ControlAction.ControlAction_OpenWorldMap.value, 0)

        @staticmethod
        def CloseWindow() -> None:
            """Close the world map window. (source 1887)

            The source queues ``OpenWorldMap`` — the same keybind as ``OpenWindow``
            (``Map.py:1893``) — and this is that keybind, on the source's own guard.
            """

            from .enums_src.ui_enums import ControlAction

            if not (frame_info := Map.WorldMap.GetFrame()):
                return
            UIManager.Keydown(ControlAction.ControlAction_OpenWorldMap.value, 0)
            UIManager.Keyup(ControlAction.ControlAction_OpenWorldMap.value, 0)

        @staticmethod
        def IsMouseOver() -> bool:
            """Not built: it reads the client's in-process ImGui.

            ``frame_info.is_mouse_over()`` (``Map.py:1900``) is ``PyImGui.get_io().mouse_pos_x/y``
            and ``ImGui.is_mouse_in_rect`` (``FrameTree/frame.py:1430-1441``). ``PyImGui`` is the
            injected runtime's own ImGui context; this project installs none and there is no way
            to install it.
            """

            raise _unported(
                "WorldMap.IsMouseOver",
                "PyImGui.get_io() — the injected runtime's in-process ImGui context, which this "
                "project installs nowhere and can install nowhere (Frame.is_mouse_over, "
                "FrameTree/frame.py:1430-1441)",
            )

        @staticmethod
        def GetLastClickCoords() -> tuple[float, float]:
            """Not built: the frame IO-event list is filled in-process.

            The source walks ``frame_info.io_events()`` (``Map.py:1908``), whose only producer is
            ``UIManager._UpdateFrameIOEvents`` — and that reads ``PyImGui.get_io()`` and
            ``PyImGui.is_mouse_clicked`` (``UIManager.py:74-88``).
            """

            raise _unported(
                "WorldMap.GetLastClickCoords",
                "UIManager.GetIOEventsForFrame, whose only producer is "
                "UIManager._UpdateFrameIOEvents — PyImGui.get_io() and PyImGui.is_mouse_clicked "
                "(UIManager.py:74-88), the injected runtime's own recorder",
            )

        @staticmethod
        def GetLastRightClickCoords() -> tuple[float, float]:
            """Not built: the same in-process IO-event list as ``GetLastClickCoords``."""

            raise _unported(
                "WorldMap.GetLastRightClickCoords",
                "UIManager.GetIOEventsForFrame, whose only producer is "
                "UIManager._UpdateFrameIOEvents — PyImGui.get_io() and PyImGui.is_mouse_clicked "
                "(UIManager.py:74-88), the injected runtime's own recorder",
            )

        @staticmethod
        def GetWindowCoords() -> tuple[float, float, float, float]:
            """Get the coordinates of the mini map. (source 1951)"""

            if not (world_map_ctx := GWContext.WorldMap.GetContext()):
                return 0.0, 0.0, 0.0, 0.0

            top_left = world_map_ctx.top_left
            bottom_right = world_map_ctx.bottom_right

            return top_left.x, top_left.y, bottom_right.x, bottom_right.y

        @staticmethod
        def GetZoom() -> float:
            """Get the zoom level of the world map. (source 1962)"""

            if not (world_map_ctx := GWContext.WorldMap.GetContext()):
                return 1.0
            return world_map_ctx.zoom

        @staticmethod
        def GetParams() -> list[int] | None:
            """Get the parameters of the world map. (source 1969)"""

            if not (world_map_ctx := GWContext.WorldMap.GetContext()):
                return None
            return list(world_map_ctx.params)

        @staticmethod
        def GetExtraData() -> dict | None:
            """Dump all misc fields (hXXXX + params) from WorldMapContext. (source 1976)

            The source's ``misc_layout`` table names each field and its offset and reads it through
            ``ctypes.addressof(ctx) + offset``. The offsets are ``WorldMapContextStruct``'s own
            declared fields — ``py4gw/context/world_map_context.py`` asserts ``zoom`` at ``0x38``,
            ``top_left`` at ``0x3C``, ``bottom_right`` at ``0x44`` and ``params`` at ``0x70`` —
            so the same words are read here **by their declared names**, which is the port's rule
            for field access; the source's offsets are kept beside each one.
            """

            ctx = GWContext.WorldMap.GetContext()
            if not ctx:
                return None

            result: dict[str, Any] = {}

            # ---- misc values at fixed offsets ----
            result["h0004"] = int(ctx.h0004)          # 0x0004
            result["h0008"] = int(ctx.h0008)          # 0x0008
            result["h000c"] = float(ctx.h000c)        # 0x000C
            result["h0010"] = float(ctx.h0010)        # 0x0010
            result["h0014"] = int(ctx.h0014)          # 0x0014
            result["h0018"] = float(ctx.h0018)        # 0x0018
            result["h001c"] = float(ctx.h001c)        # 0x001C
            result["h0020"] = float(ctx.h0020)        # 0x0020
            result["h0024"] = float(ctx.h0024)        # 0x0024
            result["h0028"] = float(ctx.h0028)        # 0x0028
            result["h002c"] = float(ctx.h002c)        # 0x002C
            result["h0030"] = float(ctx.h0030)        # 0x0030
            result["h0034"] = float(ctx.h0034)        # 0x0034
            result["h0068"] = float(ctx.h0068)        # 0x0068
            result["h006c"] = float(ctx.h006c)        # 0x006C

            # ---- array h004c ----
            h004c_offset = 0x004C
            h004c_count = 7
            h004c = []

            for i in range(h004c_count):
                h004c.append(int(ctx.h004c[i]))

            result["h004c"] = h004c

            return result

    # -- nested: pre-game (source 2025-2097) ------------------------------

    class Pregame:
        """The login/character-select screen. Source: ``Map.py`` 2025-2097."""

        #: ``Map.py:2026`` — the source's class body imports these two names, which is what makes
        #: them attributes of ``Map.Pregame``. Same import, at the port's module path.
        from .context.pre_game_context import LoginCharacter, PreGameContextStruct

        #: ``Map.py:2028-2031`` — the same click memory as ``MissionMap``'s.
        last_right_clicked_coords: tuple[float, float] = (0.0, 0.0)
        last_right_clicked_timestamp: int = 0
        last_left_clicked_coords: tuple[float, float] = (0.0, 0.0)
        last_left_clicked_timestamp: int = 0

        @staticmethod
        def GetFrameID() -> int:
            """Frame id of the pre-game screen. (source 2034)"""

            if not (world_map_ctx := GWContext.PreGame.GetContext()):
                return 0
            return world_map_ctx.frame_id

        @staticmethod
        def GetFrame():
            """The pre-game frame. (source 2041)"""

            if not (frame_id := Map.Pregame.GetFrameID()):
                return None
            return Frame.from_id(frame_id)

        @staticmethod
        def IsWindowOpen() -> bool:
            """Check if the pre-game window is open. (source 2048)"""

            if not (frame_info := Map.Pregame.GetFrame()):
                return False
            return frame_info.exists

        @staticmethod
        def GetChosenCharacterIndex() -> int:
            """Get the chosen character index from pregame map. (source 2055)"""

            if not (pre_game_ctx := GWContext.PreGame.GetContext()):
                return -1
            return pre_game_ctx.preview_character_index

        @staticmethod
        def GetContextStruct():
            """Get the pregame map context structure. (source 2062)"""

            return GWContext.PreGame.GetContext()

        @staticmethod
        def GetCharList() -> list[Any]:
            """Get the character list from pregame map. (source 2067)"""

            if not (pre_game_ctx := GWContext.PreGame.GetContext()):
                return []
            return pre_game_ctx.chars_list

        @staticmethod
        def GetAvailableCharacterList() -> list[Any]:
            """Get the available character list from pregame map. (source 2074)"""

            if (available_chars := GWContext.AvailableCharacterArray.GetContext()) is None:
                return []
            return available_chars.available_characters_list

        @staticmethod
        def InCharacterSelectScreen() -> bool:
            """Check if in character select screen. (source 2081)

            The source's whole body is ``PySystem.in_character_select_screen()``, and what that
            calls is native ``System::InCharacterSelectScreen`` (``system/system_methods.cpp:188``):
            the pre-game context's buffer and count guard first, then **the client's own
            ``kCheckUIState`` message** with ``lparam`` pointing at a word it is expected to fill,
            and the answer is whether that word came back ``2``. Native keeps the word on its own
            stack frame and hands the client its address; this process has no frame inside the
            client, so the word lives in the block's data region — the same place
            ``UIManager.SendUIMessage`` puts its payload.

            ``PreGameContextStruct.chars_array`` is native's ``chars_buffer``/``chars_capacity``/
            ``chars_count`` (``include/GW/context/pregame.h``: ``0xE0``/``0xE4``/``0xE8``) as one
            ``GWBaseArray``, which is how Reforged declares the same three words.
            """

            from .client import require_client

            pregame = GWContext.PreGame.GetContext()
            if not pregame or not pregame.chars_array.m_buffer or not pregame.chars_array.m_size:
                return False

            client = require_client()
            bridge = client.bridge
            address = bridge.write_data(_UI_STATE_OFFSET, struct.pack("<I", 10))
            client.send_ui_message_raw(
                int(UIMessage.kCheckUIState), 0, address
            )
            ui_state = int.from_bytes(bridge.read_data(_UI_STATE_OFFSET, 4), "little")
            return ui_state == 2

        @staticmethod
        def LogoutToCharacterSelect():
            """Logout to the character select screen. (source 2088)"""

            MapMethods.LogouttoCharacterSelect()

    # -- nested: pathing (source 2099-2327) -------------------------------

    class Pathing:
        """Pathing maps, spawns, portals and geometry. Source: 2099-2327."""

        @staticmethod
        def GetPathingMaps(map_id: int | None = None) -> list[PathingMap]:
            """Get pathing maps. None = live from current map, else offline (cached). (source 2102)"""

            if map_id is None:
                from .context.map_context import MapContext
                from .routines_src.Checks import Checks

                if not Checks.Map.MapValid():
                    return []
                return MapContext.GetPathingMaps()

            from .ffna_map_methods import FfnaMapMethods

            return FfnaMapMethods.GetPathingMapsForMap(map_id)

        @staticmethod
        def GetPathingMapsRaw() -> list[PathingMapStruct]:
            """Get the raw pathing map records. (source 2114)"""

            from .context.map_context import MapContext
            from .routines_src.Checks import Checks

            if not Checks.Map.MapValid():
                return []
            return MapContext.GetPathingMapsRaw()

        @staticmethod
        def ClearPathingCache(
            map_id: int | None = None, include_live: bool = False
        ) -> None:
            """Clear cached pathing data. (source 2122)

            By default this clears offline FFNA caches. ``include_live=True`` also clears the live
            map-context snapshots and the ``AutoPathing`` navmesh cache, which is the source's own
            branch; the commented-out ``MapContext.ClearPathingCache(map_id)`` line is the
            source's too (``Map.py:2134``).
            """

            from .ffna_map_methods import FfnaMapMethods

            FfnaMapMethods.ClearCache(map_id)
            if include_live:
                from .pathing import AutoPathing

                # MapContext.ClearPathingCache(map_id)
                AutoPathing().clear_navmesh_cache(map_id)

        @staticmethod
        def ForceReloadNavMesh() -> None:
            """Clear live/offline pathing caches for the current map and rebuild navmesh. (source 2138)"""

            from .pathing import AutoPathing

            for _ in AutoPathing().force_reload_navmesh():
                pass

        @staticmethod
        def GetAvailableMapIds() -> set[int]:
            """Return the set of map IDs that offline pathing can be loaded for. (source 2146)"""

            from .ffna_map_methods import FfnaMapMethods

            return FfnaMapMethods.GetAvailableMapIds()

        @staticmethod
        def GetSpawns(
            map_id: int | None = None,
        ) -> tuple[list[SpawnPoint], list[SpawnPoint], list[SpawnPoint]]:
            """Get (spawns1, spawns2, spawns3). None = live, else offline (cached). (source 2152)"""

            if map_id is None:
                from .context.map_context import MapContext

                return MapContext.GetSpawns()

            from .ffna_map_methods import FfnaMapMethods

            return FfnaMapMethods.GetSpawnData(map_id)

        @staticmethod
        def GetTravelPortals(map_id: int | None = None) -> list[TravelPortal]:
            """Get travel portal positions. None = live from runtime props, else offline. (source 2161)"""

            if map_id is None:
                from .context.map_context import MapContext

                return MapContext.GetTravelPortals()

            from .ffna_map_methods import FfnaMapMethods

            return FfnaMapMethods.GetTravelPortalsForMap(map_id)

        @staticmethod
        def WorldToScreen(x: float, y: float, z: float = 0.0) -> tuple[float, float]:
            """Not built: it projects through the injected overlay module.

            The source is ``Overlay.FindZ(x, y)`` when ``z == 0.0``, then
            ``PyOverlay.Overlay().WorldToScreen(x, y, z)`` (``Map.py:2170-2175``). ``Overlay``'s own
            ``FindZ`` is ``Overlay().overlay_instance.FindZ(...)``, and the object both halves hang
            off is ``PyOverlay.Overlay()`` — the injected runtime's overlay manager, which exists
            because that runtime hooks the device and draws. This class has no render process, so
            the member reports what it needs rather than standing in a projection of its own.
            """

            raise _unported(
                "Pathing.WorldToScreen",
                "PyOverlay.Overlay() and Overlay.FindZ (Map.py:2170-2175) — the injected runtime's "
                "overlay manager, which this class has no render process for",
            )

        class Quad:
            """A pathing trapezoid with its projected screen corners. (source 2177)"""

            def __init__(self, trapezoid: PathingTrapezoid) -> None:
                """Build a quad from a pathing trapezoid. (source 2178)

                The source builds each corner as ``PyOverlay.Vec2f(int(...), int(...))``. Native
                binds that name to ``GW::Vec2f`` (``overlay_bindings.cpp:14-18``) — two floats with
                ``x``/``y`` — which is the record ``py4gw/internals/types.py`` already declares as
                the port of Reforged's own ``native_src/internals/types.py::Vec2f``, so that is the
                type used here: same two words, same fields, same construction.
                """

                self.trapezoid = trapezoid

                self.top_left: Vec2f = Vec2f(int(trapezoid.XTL), int(trapezoid.YT))
                self.top_right: Vec2f = Vec2f(int(trapezoid.XTR), int(trapezoid.YT))
                self.bottom_left: Vec2f = Vec2f(int(trapezoid.XBL), int(trapezoid.YB))
                self.bottom_right: Vec2f = Vec2f(int(trapezoid.XBR), int(trapezoid.YB))

                screen_TL = Map.MissionMap.MapProjection.GameMapToScreen(self.top_left.x, self.top_left.y)
                screen_TR = Map.MissionMap.MapProjection.GameMapToScreen(self.top_right.x, self.top_right.y)
                screen_BL = Map.MissionMap.MapProjection.GameMapToScreen(self.bottom_left.x, self.bottom_left.y)
                screen_BR = Map.MissionMap.MapProjection.GameMapToScreen(self.bottom_right.x, self.bottom_right.y)

                self.screen_top_left: Vec2f = Vec2f(int(screen_TL[0]), int(screen_TL[1]))
                self.screen_top_right: Vec2f = Vec2f(int(screen_TR[0]), int(screen_TR[1]))
                self.screen_bottom_left: Vec2f = Vec2f(int(screen_BL[0]), int(screen_BL[1]))
                self.screen_bottom_right: Vec2f = Vec2f(int(screen_BR[0]), int(screen_BR[1]))

            def GetPoints(self) -> list[Vec2f]:
                """Return the four game-space corners. (source 2196)"""

                return [self.top_left, self.top_right, self.bottom_left, self.bottom_right]

            def GetScreenPoints(self) -> list[Vec2f]:
                """Return the four screen-space corners. (source 2199)"""

                return [self.screen_top_left, self.screen_top_right, self.screen_bottom_left, self.screen_bottom_right]

            def GetShiftedPoints(self, origin_x: float, origin_y: float) -> list[Vec2f]:
                """Return the four game-space corners shifted by an origin. (source 2202)"""

                return [
                    Vec2f(int(self.top_left.x - origin_x), int(self.top_left.y - origin_y)),
                    Vec2f(int(self.top_right.x - origin_x), int(self.top_right.y - origin_y)),
                    Vec2f(int(self.bottom_left.x - origin_x), int(self.bottom_left.y - origin_y)),
                    Vec2f(int(self.bottom_right.x - origin_x), int(self.bottom_right.y - origin_y)),
                ]

            def GetShiftedScreenPoints(
                self, origin_x: float, origin_y: float
            ) -> list[Vec2f]:
                """Return the four screen corners shifted by an origin. (source 2210)"""

                shifted = self.GetShiftedPoints(origin_x, origin_y)
                shifted_tl = Map.MissionMap.MapProjection.GameMapToScreen(shifted[0].x, shifted[0].y)
                shifted_tr = Map.MissionMap.MapProjection.GameMapToScreen(shifted[1].x, shifted[1].y)
                shifted_bl = Map.MissionMap.MapProjection.GameMapToScreen(shifted[2].x, shifted[2].y)
                shifted_br = Map.MissionMap.MapProjection.GameMapToScreen(shifted[3].x, shifted[3].y)
                return [
                    Vec2f(int(shifted_tl[0]), int(shifted_tl[1])),
                    Vec2f(int(shifted_tr[0]), int(shifted_tr[1])),
                    Vec2f(int(shifted_bl[0]), int(shifted_bl[1])),
                    Vec2f(int(shifted_br[0]), int(shifted_br[1])),
                ]

        @staticmethod
        def GetComputedGeometry() -> list[list[Vec2f]]:
            """Get pathing geometry as game-space quads. (source 2224)"""

            pathing_maps: list[PathingMap] = Map.Pathing.GetPathingMaps()
            geometry = []
            for layer in pathing_maps:
                for trapezoid in layer.trapezoids:
                    geometry.append(Map.Pathing.Quad(trapezoid).GetPoints())
            return geometry

        @staticmethod
        def GetScreenComputedGeometry() -> list[list[Vec2f]]:
            """Get pathing geometry as screen-space quads. (source 2233)"""

            pathing_maps: list[PathingMap] = Map.Pathing.GetPathingMaps()
            geometry = []
            for layer in pathing_maps:
                for trapezoid in layer.trapezoids:
                    geometry.append(Map.Pathing.Quad(trapezoid).GetScreenPoints())
            return geometry

        @staticmethod
        def GetShiftedComputedGeometry(
            origin_x: float, origin_y: float
        ) -> list[list[Vec2f]]:
            """Get pathing geometry shifted by an origin. (source 2242)"""

            pathing_maps: list[PathingMap] = Map.Pathing.GetPathingMaps()
            geometry = []
            for layer in pathing_maps:
                for trapezoid in layer.trapezoids:
                    quad = Map.Pathing.Quad(trapezoid)
                    geometry.append(quad.GetShiftedPoints(origin_x, origin_y))
            return geometry

        @staticmethod
        def GetshiftedScreenComputedGeometry(
            origin_x: float, origin_y: float
        ) -> list[list[Vec2f]]:
            """Get screen-space pathing geometry shifted by an origin. (source 2252)"""

            pathing_maps: list[PathingMap] = Map.Pathing.GetPathingMaps()
            geometry = []
            for layer in pathing_maps:
                for trapezoid in layer.trapezoids:
                    quad = Map.Pathing.Quad(trapezoid)
                    geometry.append(quad.GetShiftedScreenPoints(origin_x, origin_y))
            return geometry

        @staticmethod
        def _point_in_quad(px: float, py: float, quad: "Map.Pathing.Quad") -> bool:
            """Check if a given x,y-point is inside a quadrilateral. (source 2262)"""

            p = [quad.top_left, quad.top_right, quad.bottom_right, quad.bottom_left]

            def sign(x1, y1, x2, y2, x3, y3):
                return (x1 - x3) * (y2 - y3) - (x2 - x3) * (y1 - y3)

            b1 = sign(px, py, p[0].x, p[0].y, p[1].x, p[1].y) < 0.0
            b2 = sign(px, py, p[1].x, p[1].y, p[2].x, p[2].y) < 0.0
            b3 = sign(px, py, p[2].x, p[2].y, p[3].x, p[3].y) < 0.0
            b4 = sign(px, py, p[3].x, p[3].y, p[0].x, p[0].y) < 0.0

            return (b1 == b2 == b3 == b4)

        @staticmethod
        def GetMapQuads() -> list["Map.Pathing.Quad"]:
            """Retrieve all pathing quads in the current map. (source 2277)"""

            pathing_maps: list[PathingMap] = Map.Pathing.GetPathingMaps()
            quads = []

            for layer in pathing_maps:
                for trapezoid in layer.trapezoids:
                    quad = Map.Pathing.Quad(trapezoid)
                    quads.append(quad)

            return quads

        @staticmethod
        def IsPointInPathing(px: float, py: float) -> bool:
            """Check if a given x,y-point is inside any pathing area. (source 2290)"""

            pathing_maps: list[PathingMap] = Map.Pathing.GetPathingMaps()

            for layer in pathing_maps:
                for trapezoid in layer.trapezoids:
                    quad = Map.Pathing.Quad(trapezoid)
                    if Map.Pathing._point_in_quad(px, py, quad):
                        return True

            return False

        @staticmethod
        def IsScreenPointInPathing(screen_x: float, screen_y: float) -> bool:
            """Check if a given screen x,y-point is inside any pathing area. (source 2303)"""

            pathing_maps: list[PathingMap] = Map.Pathing.GetPathingMaps()

            for layer in pathing_maps:
                for trapezoid in layer.trapezoids:
                    quad = Map.Pathing.Quad(trapezoid)
                    pts = quad.GetScreenPoints()

                    def sign(x1, y1, x2, y2, x3, y3):
                        return (x1 - x3) * (y2 - y3) - (x2 - x3) * (y1 - y3)

                    b1 = sign(screen_x, screen_y, pts[0].x, pts[0].y, pts[1].x, pts[1].y) < 0.0
                    b2 = sign(screen_x, screen_y, pts[1].x, pts[1].y, pts[2].x, pts[2].y) < 0.0
                    b3 = sign(screen_x, screen_y, pts[2].x, pts[2].y, pts[3].x, pts[3].y) < 0.0
                    b4 = sign(screen_x, screen_y, pts[3].x, pts[3].y, pts[0].x, pts[0].y) < 0.0

                    if b1 == b2 == b3 == b4:
                        return True

            return False
