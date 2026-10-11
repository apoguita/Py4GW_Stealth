"""Scratch: the exact lines the strategy generator could not read, and how often each blocks a body.

Every refusal message ends with either ``no statement rule: <line>`` or ``names a constant this layer
does not carry: <name>`` or ``calls a name this layer does not implement: <name>``. Those are the
frontier: one rule can un-refuse many bodies.
"""

from __future__ import annotations

import collections
import re
from pathlib import Path

ROOT = Path(r"C:\Users\Apo\Py4GW_Stealth\py4gw\gwa3")

PATTERNS = (
    r"no statement rule: (.*?)\"",
    r"names a constant this layer does not carry: (\w+)",
    r"calls a name this layer does not implement: (\w+)",
    r"names a statement this layer does not carry: (\w+)",
    r"reads a column this layer refuses, so the body cannot answer correctly: (\$GC_UAI_AGENT_\w+)",
)

groups: dict[str, collections.Counter[str]] = {p: collections.Counter() for p in PATTERNS}
module_of: dict[tuple[str, str], set[str]] = collections.defaultdict(set)

for path in sorted(ROOT.glob("uai_*.py")):
    text = path.read_text(encoding="utf-8", errors="replace")
    for pattern in PATTERNS:
        for match in re.finditer(pattern, text):
            key = " ".join(match.group(1).split())
            groups[pattern][key] += 1
            module_of[(pattern, key)].add(path.stem)

for pattern, counter in groups.items():
    print(f"--- {pattern} : {sum(counter.values())} refusals, {len(counter)} distinct ---")
    for key, count in counter.most_common(25):
        print(f"{count:4}  {key[:96]}   {sorted(module_of[(pattern, key)])}")
    print()
