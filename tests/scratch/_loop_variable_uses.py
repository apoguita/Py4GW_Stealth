"""Scratch: the two things the row-index loop rewrite must be safe about.

1. Every use of the loop variable in the 34 bodies that stop at
   ``For $i = 1 To $g_i_AgentCacheCount`` -- if it is used for anything other than
   ``UAI_GetAgentInfo($i, <column>)`` the substitution would be wrong.
2. The call shapes that read ``$GC_UAI_AGENT_Distance``, since that column is the one the layer
   answers through ``_cached_distance``.
"""

from __future__ import annotations

import collections
import re
from pathlib import Path

ROOT = Path(r"C:\Users\Apo\Py4GW_Stealth")
SKILLS = ROOT / "external" / "GwAu3" / "API" / "Plugins" / "UtilityAI"
DECL = re.compile(r"^Func ((?:BestTarget|CanUse|Anti)_\w+)\(", re.M)

bodies: dict[str, str] = {}
for path in sorted(SKILLS.rglob("*.au3")):
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    matches = list(DECL.finditer(text))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        bodies[match.group(1)] = text[match.start() : end]

loop_bodies = {
    name: body
    for name, body in bodies.items()
    if re.search(r"(?m)^\s*For \$i = 1 To \$g_i_AgentCacheCount\s*$", body)
}
print(f"bodies with the agent-cache loop: {len(loop_bodies)}")

uses: collections.Counter[str] = collections.Counter()
odd: list[str] = []
for name, body in loop_bodies.items():
    for line in body.splitlines():
        if "$i" not in line:
            continue
        stripped = line.strip()
        if re.match(r"^For \$i = ", stripped) or stripped == "Next":
            continue
        match = re.match(r"^UAI_GetAgentInfo\(\$i,\s*(\$[\w]+)\)$", stripped)
        if match:
            uses[match.group(1)] += 1
            continue
        uses[f"OTHER: {stripped[:70]}"] += 1
        odd.append(f"{name}: {stripped[:90]}")

for key, count in uses.most_common(20):
    print(f"{count:4}  {key}")

print(f"\n--- Distance call shapes ---")
shapes: collections.Counter[str] = collections.Counter()
for name, body in bodies.items():
    for match in re.finditer(r"([\w]+)\(([^()]*?)\$GC_UAI_AGENT_Distance\)", body):
        shapes[f"{match.group(1)}({match.group(2).strip() or '<no arg>'})"] += 1
for key, count in shapes.most_common(20):
    print(f"{count:4}  {key}")
