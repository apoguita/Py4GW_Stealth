"""Offline attribute check for the members the new snippet functions call (no client, no connection)."""

import sys

sys.path.insert(0, r"C:\Users\Apo\Py4GW_Stealth")

from py4gw.context.map_context import MapContextStruct, MapStaticDataStruct, PathContextStruct
from py4gw.context.world_context import DupeSkillStruct, WorldContextStruct

checks = [
    ("MapContextStruct.map_boundaries", hasattr(MapContextStruct, "map_boundaries")),
    ("MapContextStruct.path_context", hasattr(MapContextStruct, "path_context")),
    ("MapContextStruct.props", hasattr(MapContextStruct, "props")),
    ("MapContextStruct.props_ptr", hasattr(MapContextStruct, "props_ptr")),
    ("MapContextStruct.spawns1", hasattr(MapContextStruct, "spawns1")),
    ("MapContextStruct.spawns2", hasattr(MapContextStruct, "spawns2")),
    ("MapContextStruct.spawns3", hasattr(MapContextStruct, "spawns3")),
    ("MapContextStruct.terrain", hasattr(MapContextStruct, "terrain")),
    ("MapContextStruct.zones", hasattr(MapContextStruct, "zones")),
    ("MapStaticDataStruct.pathing_maps", hasattr(MapStaticDataStruct, "pathing_maps")),
    ("MapStaticDataStruct.pmaps_array", hasattr(MapStaticDataStruct, "pmaps_array")),
    ("MapStaticDataStruct.trapezoid_count", hasattr(MapStaticDataStruct, "trapezoid_count")),
    ("PathContextStruct.static_data", hasattr(PathContextStruct, "static_data")),
    ("WorldContextStruct.unlocked_character_skills", hasattr(WorldContextStruct, "unlocked_character_skills")),
    ("WorldContextStruct.duplicated_character_skills", hasattr(WorldContextStruct, "duplicated_character_skills")),
    ("DupeSkillStruct.skill_id", hasattr(DupeSkillStruct, "skill_id")),
    ("DupeSkillStruct.count", hasattr(DupeSkillStruct, "count")),
]

from py4gw.client import ConnectedClient

checks += [
    ("ConnectedClient.read_map_context", hasattr(ConnectedClient, "read_map_context")),
    ("ConnectedClient.read_world_context", hasattr(ConnectedClient, "read_world_context")),
]

from py4gw.map import Map

checks += [
    ("Map.IsMapUnlocked", hasattr(Map, "IsMapUnlocked")),
    ("Map.MissionMap.GetLastClickCoords", hasattr(Map.MissionMap, "GetLastClickCoords")),
]

from py4gw.gwa3 import data_map_context, data_ui

checks += [
    ("data_map_context.__all__", data_map_context.__all__ == [
        "Map_GetMapContextInfo",
        "Map_GetPathingMapArrayInfo",
        "Map_GetPropsContext",
        "Map_GetTotalTrapezoidCount",
    ]),
    ("data_ui.__all__", data_ui.__all__ == ["Ui_GetRenderDisabled", "Ui_GetRenderEnabled"]),
]

missing = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(("ok   " if ok else "MISS ") + name)
print("missing:", missing)
