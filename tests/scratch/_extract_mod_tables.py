"""Scratch: print UtilityAI_Const.au3's mod tables as Python literals (transcription aid)."""

from __future__ import annotations

import re
from pathlib import Path

SOURCE = Path(r"C:\Users\Apo\Py4GW_Stealth\external\GwAu3\API\Plugins\UtilityAI\UtilityAI_Const.au3")

HEAD = re.compile(r"^Global\s+\$g_(as2_\w+)\s*\[(\d+)\]\[3\]\s*=\s*\[\s*_?\s*$")
ROW = re.compile(r'^\s*\[\s*"((?:[^"]|"")*)"\s*,\s*"((?:[^"]|"")*)"\s*,\s*"((?:[^"]|"")*)"\s*\]')

text = SOURCE.read_text(encoding="utf-8", errors="replace").splitlines()
out: list[str] = []
index = 0
tables = 0
while index < len(text):
    match = HEAD.match(text[index])
    if not match:
        index += 1
        continue
    name, declared = match.group(1), int(match.group(2))
    rows: list[tuple[str, str, str]] = []
    while index < len(text):
        line = text[index]
        index += 1
        row = ROW.match(line)
        if row:
            rows.append((row.group(1), row.group(2), row.group(3)))
        if "]]" in line:
            break
    tables += 1
    status = "OK" if len(rows) == declared else f"MISMATCH declared {declared}"
    out.append(f"# {name}: {len(rows)} rows ({status})")
    out.append(f"{name}: list[list[str]] = [")
    for row in rows:
        out.append(f"    [{row[0]!r}, {row[1]!r}, {row[2]!r}],")
    out.append("]")
    out.append("")

Path(r"C:\Users\Apo\Py4GW_Stealth\tests\scratch\_mod_tables_block.txt").write_text(
    "\n".join(out), encoding="utf-8"
)
print(f"wrote {len(out)} lines for {tables} tables")
