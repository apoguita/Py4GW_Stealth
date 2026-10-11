"""Scratch: the UtilityAI plugin's rows by tier, from the route-map generator itself."""

from __future__ import annotations

import collections
import importlib.util
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\Apo\Py4GW_Stealth")
spec = importlib.util.spec_from_file_location(
    "generate_gwa3_route_map", ROOT / "tools" / "generate_gwa3_route_map.py"
)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules["generate_gwa3_route_map"] = module
spec.loader.exec_module(module)

declared = module.parse_declarations()
mechanisms = module.load_mechanisms()
calls = module.load_call_census()

plugin = [f for f in declared if "Plugins/UtilityAI/" in f.file]
tiers: collections.Counter[str] = collections.Counter()
called = 0
for function in plugin:
    tier, _ = module.tier_for(function.name, mechanisms.get(function.name, ""))
    tiers[tier] += 1
    if calls.get(function.name, 0) > 0:
        called += 1

print("plugin rows:", len(plugin))
print("called by GwAu3 code (census):", called)
for tier, count in sorted(tiers.items()):
    print(f"  {tier}: {count}")
all_tiers: collections.Counter[str] = collections.Counter()
for function in declared:
    tier, _ = module.tier_for(function.name, mechanisms.get(function.name, ""))
    all_tiers[tier] += 1
print("all declared:", len(declared))
for tier, count in sorted(all_tiers.items()):
    print(f"  {tier}: {count}")
