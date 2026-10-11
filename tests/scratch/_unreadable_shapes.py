"""Scratch: the source context around each unreadable statement shape.

The generator refuses a body at its first unreadable line, and the refusal message ends with
``no statement rule: <line>``. This prints that line with its neighbours from the GwAu3 source, so a
rule can be written against the shape rather than against a guess.
"""

from __future__ import annotations

import collections
import re
from pathlib import Path

ROOT = Path(r"C:\Users\Apo\Py4GW_Stealth")
SKILLS = ROOT / "external" / "GwAu3" / "API" / "Plugins" / "UtilityAI"

PATTERN = re.compile(r"no statement rule: ([^\"]*)")
wanted: collections.Counter[str] = collections.Counter()
for path in sorted((ROOT / "py4gw" / "gwa3").glob("uai_*.py")):
    for match in PATTERN.finditer(path.read_text(encoding="utf-8", errors="replace")):
        wanted[" ".join(match.group(1).split())] += 1

print("distinct unreadable lines:", len(wanted))
for line, count in wanted.most_common():
    print(f"\n{'=' * 90}\n{count} body(ies) stop at: {line!r}")
    for source in sorted(SKILLS.rglob("*.au3")):
        lines = source.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        for index, raw in enumerate(lines):
            if raw.strip() == line.strip():
                start = max(0, index - 4)
                end = min(len(lines), index + 6)
                print(f"--- {source.name}:{index + 1}")
                for n in range(start, end):
                    marker = ">>" if n == index else "  "
                    print(f"{marker}{n + 1:5}: {lines[n]}")
                break
        else:
            continue
        break
