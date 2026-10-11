"""Scratch: the 717 rows outside the plugin that still have no route -- how many are ported?

Same question the plugin rows asked, over the whole declared surface: a row with no route may be a
member `py4gw/gwa3/` already implements (a map gap) or real work (a porting gap). This separates them.
"""

from __future__ import annotations

import collections
import importlib.util
import re
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

homes: dict[str, str] = {}
for path in sorted((ROOT / "py4gw" / "gwa3").glob("*.py")):
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.match(r"def (\w+)\(", line)
        if match:
            homes.setdefault(match.group(1), path.stem)

rows = [
    f
    for f in declared
    if module.tier_for(f.name, mechanisms.get(f.name, ""))[0] == "NO ROUTE YET"
]
print(f"NO ROUTE YET rows: {len(rows)}")

with_home = collections.Counter()
without: list[str] = []
for function in rows:
    home = homes.get(function.name)
    if home:
        with_home[home] += 1
    else:
        without.append(function.name)

print(f"  with a ported home: {sum(with_home.values())}")
print(f"  with no ported home: {len(without)}")
print()
print("by module:")
for home, count in with_home.most_common():
    print(f"  {home:28} {count}")
print()
print("no ported home (first 60):")
for name in sorted(without)[:60]:
    print("   ", name)
