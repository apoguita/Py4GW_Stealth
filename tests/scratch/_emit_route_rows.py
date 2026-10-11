"""Scratch: emit the route-map table data for the plugin's unrouted rows.

Classification is mechanical: a ported member **refuses** when its own body raises
``NotImplementedError``, **is not applicable** when its docstring says so, and is **routed** otherwise.
Names with no ported home are listed separately for a hand-written tier.
"""

from __future__ import annotations

import ast
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

source_of: dict[str, str] = {}
homes: dict[str, str] = {}
for path in sorted((ROOT / "py4gw" / "gwa3").glob("*.py")):
    text = path.read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(text)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            homes.setdefault(node.name, path.stem)
            source_of[node.name] = ast.get_source_segment(text, node) or ""

rows = [
    f.name
    for f in declared
    if "Plugins/UtilityAI/" in f.file
    and module.tier_for(f.name, mechanisms.get(f.name, ""))[0] == "NO ROUTE YET"
]

routed: dict[str, list[str]] = {}
refused: list[str] = []
not_applicable: list[str] = []
unported: list[str] = []
for name in rows:
    home = homes.get(name)
    if home is None:
        unported.append(name)
        continue
    body = source_of.get(name, "")
    if "NotImplementedError" in body:
        refused.append(name)
    elif "NOT APPLICABLE" in body.upper()[:400]:
        not_applicable.append(name)
    else:
        routed.setdefault(home, []).append(name)

print("ROUTED by module:")
for home, names in sorted(routed.items()):
    print(f'    "{home}": (')
    for name in sorted(names):
        print(f'        "{name}",')
    print("    ),")
print()
print("REFUSED:", len(refused))
for name in sorted(refused):
    print(f'    "{name}": "{homes[name]}",')
print()
print("NOT APPLICABLE:", sorted(not_applicable))
print("UNPORTED:", len(unported))
for name in sorted(unported):
    print(f"    {name}")
