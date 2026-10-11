"""Scratch: which of the unrouted plugin rows the layer answers, refuses or calls not applicable.

Reads each ported member's own docstring, because that is where the layer records which of the three it
is -- and the route map must not tier a refusing member as routed.
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

homes: dict[str, str] = {}
docstrings: dict[tuple[str, str], str] = {}
for path in sorted((ROOT / "py4gw" / "gwa3").glob("*.py")):
    tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            homes.setdefault(node.name, path.stem)
            docstrings[(path.stem, node.name)] = ast.get_docstring(node) or ""

rows = [
    f for f in declared if "Plugins/UtilityAI/" in f.file
    and module.tier_for(f.name, mechanisms.get(f.name, ""))[0] == "NO ROUTE YET"
]
print(f"unrouted plugin rows: {len(rows)}")
for function in sorted(rows, key=lambda f: f.name):
    home = homes.get(function.name)
    if home is None:
        print(f"NO HOME   {function.name}")
        continue
    doc = docstrings.get((home, function.name), "")
    head = " ".join(doc.split())[:120]
    flag = ""
    if "REFUSED" in head.upper()[:80]:
        flag = "  <== refuses"
    elif "NOT APPLICABLE" in head.upper()[:80]:
        flag = "  <== not applicable"
    print(f"{home:26} {function.name:42}{flag}")
