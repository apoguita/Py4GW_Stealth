"""Scratch: emit the route-map table for the rows that have a ported home but no route yet.

Classification is the layer's own: a member whose body raises ``NotImplementedError`` refuses, one whose
docstring says NOT APPLICABLE has no client counterpart, and the rest answer. Grouped by module, because
the note is per family.
"""

from __future__ import annotations

import ast
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

source_of: dict[str, str] = {}
docstring_of: dict[str, str] = {}
homes: dict[str, str] = {}
for path in sorted((ROOT / "py4gw" / "gwa3").glob("*.py")):
    text = path.read_text(encoding="utf-8", errors="replace")
    for node in ast.parse(text).body:
        if isinstance(node, ast.FunctionDef):
            homes.setdefault(node.name, path.stem)
            source_of[node.name] = ast.get_source_segment(text, node) or ""
            docstring_of[node.name] = ast.get_docstring(node) or ""

rows = [
    f.name
    for f in declared
    if module.tier_for(f.name, mechanisms.get(f.name, ""))[0] == "NO ROUTE YET"
]

routed: dict[str, list[str]] = collections.defaultdict(list)
refused: dict[str, list[str]] = collections.defaultdict(list)
not_applicable: dict[str, list[str]] = collections.defaultdict(list)
for name in rows:
    home = homes.get(name)
    if home is None:
        continue
    # **The tier comes from the member's own verdict**, because the `cmd_*` modules refuse through a
    # shared `_refuse` helper and `core.py` writes ``**Refused, not answered.**`` in mixed case: a scan
    # for `NotImplementedError` in the member's body misses both, and a mixed-case marker check misses
    # the second -- either way a refused member would be reported as routed, which is the one thing the
    # map must not do. The verdict is the docstring's first line, in either case.
    first_line = (docstring_of.get(name, "").splitlines() or [""])[0].strip()
    marker = first_line.upper()
    body = source_of.get(name, "")
    if marker.startswith(("**NOT APPLICABLE", "NOT APPLICABLE")):
        not_applicable[home].append(name)
    elif marker.startswith(("**REFUSED", "REFUSED")) or "_refuse(" in body:
        refused[home].append(name)
    else:
        # **Verified by calling it.** A member that answers needs a client and says so; one that refuses
        # raises `NotImplementedError` first. Anything else is reported rather than assumed.
        module_object = importlib.import_module(f"py4gw.gwa3.{home}")
        function = getattr(module_object, name)
        try:
            function()
        except NotImplementedError:
            print(f"  RECLASSIFY (raises): {home}.{name}")
            refused[home].append(name)
            continue
        except TypeError as error:
            print(f"  needs arguments: {home}.{name}: {str(error)[:60]}")
        except RuntimeError as error:
            if "Guild Wars client" not in str(error):
                print(f"  other RuntimeError: {home}.{name}: {str(error)[:60]}")
        except Exception as error:  # noqa: BLE001 - the failure is the measurement
            print(f"  other: {home}.{name}: {type(error).__name__}: {str(error)[:60]}")
        routed[home].append(name)

print("ROUTED:")
for home, names in sorted(routed.items()):
    print(f'    "{home}": (')
    for name in sorted(names):
        print(f'        "{name}",')
    print("    ),")
print("\nREFUSED:")
for home, names in sorted(refused.items()):
    print(f"  {home}: {sorted(names)}")
print("\nNOT APPLICABLE:")
for home, names in sorted(not_applicable.items()):
    print(f"  {home}: {sorted(names)}")

report = Path(r"C:\Users\Apo\Py4GW_Stealth\tests\scratch\_family_rows.md")
lines = ["# The rows that have a ported home and no route yet", ""]
for label, groups in (("ROUTED", routed), ("REFUSED", refused), ("NOT APPLICABLE", not_applicable)):
    total = sum(len(names) for names in groups.values())
    lines.append(f"## {label} -- {total} rows")
    lines.append("")
    for home, names in sorted(groups.items()):
        lines.append(f"* `{home}` ({len(names)}): " + ", ".join(f"`{name}`" for name in sorted(names)))
    lines.append("")
report.write_text("\n".join(lines), encoding="utf-8")
print(f"\nwrote {report}")
