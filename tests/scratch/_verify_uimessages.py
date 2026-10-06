"""Verify the UIMessage table in every copy against Native's ui.h, the measured-correct source.

WHY
---
PR #9 rewrote `UIMessage` in `include/GW/common/constants/ui.h`. That value set was then MEASURED
against the running client (adding a hero emitted 0x1000011F, opening the guild hall 0x10000183,
travelling 0x10000186 - all the new column), so ui.h is the authority.

The same table also exists in Python, where nothing propagates automatically:

    Py4GW_Reforged/Py4GWCoreLib/enums_src/UI_enums.py   (the library the client runs)
    Py4GW_Stealth/py4gw/enums_src/ui_enums.py           (the port)

This reports, per copy: names only in one side, and names whose VALUE differs. It also scans the
whole Reforged tree for hardcoded `0x1000xxxx` / `0x3000xxxx` literals outside the enum file, which
is where a stale id would hide from an enum-level fix.

USAGE: python tests/scratch\1_verify_uimessages.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

NATIVE_UI_H = Path(r"C:\Users\Apo\Py4GW_Reforged_Native\include\GW\common\constants\ui.h")
REFORGED = Path(r"C:\Users\Apo\Py4GW_Reforged")
STEALTH = Path(r"C:\Users\Apo\Py4GW_Stealth")

#: ``kName = 0x10000183,`` or ``kName = 0x30000000 | 0x17,`` (C++), or ``kName = 0x10000183  # ..`` (Python)
CXX = re.compile(
    r"^\s*(k\w+)\s*=\s*(0x[0-9A-Fa-f]+)\s*(?:\|\s*(0x[0-9A-Fa-f]+))?\s*,", re.M
)
PY = re.compile(r"^\s*(k\w+)\s*=\s*(0x[0-9A-Fa-f]+)\s*(?:#.*)?$", re.M)


def parse(text: str, pattern: re.Pattern[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for m in pattern.finditer(text):
        value = int(m.group(2), 16)
        if m.lastindex and m.lastindex >= 3 and m.group(3):
            value |= int(m.group(3), 16)
        out[m.group(1)] = value
    return out


def uimessage_block_cxx(text: str) -> str:
    """Only the UIMessage enum body of ui.h - other enums in that header are not this table."""

    m = re.search(r"enum\s+class\s+UIMessage[^{]*\{(.*?)\n\};", text, re.S)
    return m.group(1) if m else ""


def uimessage_block_py(text: str) -> str:
    """Only the UIMessage class body - the file also holds FrameMessage, preferences, etc."""

    m = re.search(r"^class\s+UIMessage\b[^\n]*:\n(.*?)(?=^class\s|\Z)", text, re.S | re.M)
    return m.group(1) if m else ""


def compare(label: str, ref: dict[str, int], other: dict[str, int]) -> int:
    only_ref = sorted(set(ref) - set(other))
    only_other = sorted(set(other) - set(ref))
    mismatch = sorted(n for n in set(ref) & set(other) if ref[n] != other[n])
    print(f"\n=== {label} ===")
    print(f"  UIMessage names: native={len(ref)} other={len(other)}   only-native={len(only_ref)} "
          f"only-other={len(only_other)}   VALUE MISMATCH={len(mismatch)}")
    for name in mismatch:
        print(f"    {name:<34} native {ref[name]:#010x}   other {other[name]:#010x}")
    if only_other:
        print(f"    only-other: {', '.join(only_other)}")
    if only_ref:
        print(f"    only-native: {', '.join(only_ref)}")
    if not mismatch and not only_ref and not only_other:
        print("    ALL MATCH")
    return len(mismatch)


def scan_literals(root: Path) -> None:
    """Hardcoded ui/send message ids outside the enum module - a stale id hiding from the fix."""

    print(f"\n=== hardcoded 0x1000xxxx / 0x3000xxxx literals under {root.name} ===")
    hits: list[str] = []
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts or ".git" in path.parts:
            continue
        if path.name in ("UI_enums.py", "Packet_enums.py"):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for number, line in enumerate(text.splitlines(), 1):
            for value in re.findall(r"0x1000[0-9A-Fa-f]{4}|0x3000[0-9A-Fa-f]{4}", line):
                hits.append(f"{path.relative_to(root)}:{number}: {line.strip()[:110]}")
    if not hits:
        print("  none")
    for hit in hits:
        print(f"  {hit}")


def main() -> int:
    native = parse(uimessage_block_cxx(NATIVE_UI_H.read_text(encoding="utf-8")), CXX)
    reforged_path = REFORGED / "Py4GWCoreLib" / "enums_src" / "UI_enums.py"
    stealth_path = STEALTH / "py4gw" / "enums_src" / "ui_enums.py"
    reforged = parse(uimessage_block_py(reforged_path.read_text(encoding="utf-8")), PY)
    stealth = parse(uimessage_block_py(stealth_path.read_text(encoding="utf-8")), PY)

    print(f"native   {NATIVE_UI_H}")
    print(f"reforged {reforged_path}")
    print(f"stealth  {stealth_path}")

    bad = 0
    bad += compare("Reforged Python vs Native ui.h  (the shipped library)", native, reforged)
    bad += compare("Stealth Python vs Native ui.h   (the port)", native, stealth)
    scan_literals(REFORGED)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
