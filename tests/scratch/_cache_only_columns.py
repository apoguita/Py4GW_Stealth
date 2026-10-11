"""Scratch: which cache-only agent columns the strategy bodies read, refused or transcribed.

`UAI_GetAgentInfo` refuses six cache-only columns (``Distance``, ``Ptr``, ``Timer``,
``IsExploitableCorpse``, ``IsPlayer``, ``IsNPC``) and three the two GwAu3 files disagree about
(``IsMoving``, ``IsAttacking``, ``IsIdle``). A body that reads one of them cannot simply be
transcribed -- so this measures which bodies do, and whether they are refused today.
"""

from __future__ import annotations

import ast
import collections
import pathlib
import re

ROOT = pathlib.Path(r"C:\Users\Apo\Py4GW_Stealth")
SKILLS = ROOT / "external" / "GwAu3" / "API" / "Plugins" / "UtilityAI" / "Skills"
GENERATED = ROOT / "py4gw" / "gwa3"

COLUMNS = (
    "Distance",
    "Ptr",
    "Timer",
    "IsExploitableCorpse",
    "IsPlayer",
    "IsNPC",
    "IsMoving",
    "IsAttacking",
    "IsIdle",
)

# {function name: refused?} over the generated modules
refused: dict[str, bool] = {}
names: set[str] = set()
for path in sorted(GENERATED.glob("uai_*.py")):
    text = path.read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(text)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            names.add(node.name)
            body = ast.get_source_segment(text, node) or ""
            if "raise NotImplementedError" in body:
                refused[node.name] = True
            else:
                refused.setdefault(node.name, False)

DECL = re.compile(r"^Func ((?:BestTarget|CanUse|Anti)_\w+)\(", re.M)
hits: collections.Counter[str] = collections.Counter()
per_column: dict[str, list[str]] = collections.defaultdict(list)
bodies: dict[str, str] = {}
for path in sorted(SKILLS.glob("*.au3")):
    text = path.read_text(encoding="utf-8", errors="replace")
    matches = list(DECL.finditer(text))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        bodies[match.group(1)] = text[match.start() : end]

for name, body in bodies.items():
    wanted = [column for column in COLUMNS if f"$GC_UAI_AGENT_{column}" in body]
    if not wanted:
        continue
    state = "REFUSED" if refused.get(name) else "transcribed"
    hits[state] += 1
    for column in wanted:
        per_column[column].append(f"{name}({state})")

print(f"bodies reading a cache-only/disagreeing column: {sum(hits.values())} {dict(hits)}")
for column in COLUMNS:
    entries = per_column.get(column, [])
    if entries:
        print(f"\n{column}: {len(entries)}")
        for entry in entries[:12]:
            print("   ", entry)
