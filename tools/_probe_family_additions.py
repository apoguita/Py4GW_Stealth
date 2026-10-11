"""Render-only simulation of the two family additions this work asks for (writes no file)."""

import dataclasses
import sys

sys.path.insert(0, r"C:\Users\Apo\Py4GW_Stealth")
sys.path.insert(0, r"C:\Users\Apo\Py4GW_Stealth\tools")
from generate_gwa3_family import FAMILIES, parse_cases, render

additions = {
    "data_map": {
        "extra_exports": (
            "Map_GetCharacterInfo",
            "Map_GetClickCoords",
            "Map_GetCurrentAreaInfo",
            "Map_GetCurrentRegionType",
            "Map_GetInstanceInfo",
            "Map_GetInstanceUpTime",
            "Map_GetLastMoveCoords",
            "Map_GetMapID",
            "Map_GetRegion",
            "Map_IsMapUnlocked",
        ),
        "helper_files": (
            "data_map_instance_info.py",
            "data_map_character_info.py",
            "data_map_current_area.py",
            "data_map_stragglers.py",
        ),
    },
    "data_world": {
        "extra_exports": (
            "World_GetSkillDuplicateCount",
            "World_GetWorldContextPtr",
            "World_IsSkillLearnt",
        ),
        "helper_files": ("data_world_stragglers.py",),
    },
}

for module, changes in additions.items():
    family = next(f for f in FAMILIES if f.module == module)
    upgraded = dataclasses.replace(family, **changes)
    text = render(upgraded, parse_cases(upgraded))
    compile(text, f"{module}.py", "exec")
    defs = [line.split("(")[0][4:] for line in text.splitlines() if line.startswith("def ")]
    print(f"{module}: renders and compiles ok; {len(text)} chars")
    print(f"  __all__ -> {[line for line in text.splitlines() if line.startswith('__all__')][0]}")
    for name in changes["extra_exports"]:
        count = defs.count(name)
        if count != 1:
            print(f"  !! {name} defined {count} times")
    for name in changes["extra_exports"]:
        pass
    print("  module-level state:", [line for line in text.splitlines() if line.startswith("g_f_LastMove")])
