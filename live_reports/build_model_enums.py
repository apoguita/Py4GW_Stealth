"""Throwaway generator: build the ported Model_enums.py from the Reforged source.

The port is the source's own bytes with two things done to them:

1. this project's module docstring and ``from __future__ import annotations`` are prepended;
2. the source's one native import and its 51 ``PySkill.Skill("<Name>").id.id`` reads are replaced by
   the ported generated lookup - ``from .skill_names import GetSkillIDByName`` and
   ``GetSkillIDByName("<Name>")`` - because native's ``PySkill.Skill(name)`` takes its id from
   ``PySkillID(const std::string& name) : id(static_cast<int>(GW::skillbar::GetSkillIDByName(name)))``
   (``Py4GW_Reforged_Native/src/GW/skillbar/skill_bindings.cpp:29-30``) and that table is already
   ported in ``py4gw/enums_src/skill_names.py``.

Nothing inside the body is retyped, and the script asserts that undoing exactly those two
substitutions reproduces the source byte for byte.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

SOURCE = Path(r"C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib\enums_src\Model_enums.py")
TARGET = Path(r"C:\Users\Apo\Py4GW_Stealth\py4gw\enums_src\model_enums.py")

# The revision this port was transcribed from, as inspected.
SOURCE_SHA256 = "350D4D1B5167A8DC169CBDF34EFC2C6297076982CA0355C1B7F4B1853B645F1F"

IMPORT_OLD = "import PySkill"
IMPORT_NEW = "from .skill_names import GetSkillIDByName"
CALL_RE = re.compile(r'PySkill\.Skill\("([^"]*)"\)\.id\.id')
CALL_NEW_RE = re.compile(r'GetSkillIDByName\("([^"]*)"\)')
EXPECTED_CALLS = 51

HEADER = '''"""Port of Reforged\'s ``Py4GWCoreLib/enums_src/Model_enums.py`` (3139 lines).

The source file is transcribed as it stands: the same names in the same order, the same
members, the same comments. Nothing is added, renamed, reordered or omitted.

**Enums:** ``AgentModelID``, ``GadgetModelID``, ``SpiritModelID``, ``PetModelID``, ``ModelID``.

**Tables:** ``SPIRIT_BUFF_MAP`` (51), keyed by ``SpiritModelID``.

**Module-level constant:** ``SPIRIT_OFFSET`` (51).

**One substitution, and it is the same lookup.** The source opens with ``from enum import IntEnum``
and ``import PySkill`` (``Model_enums.py:1-2``), and reads ``PySkill.Skill("<Name>").id.id`` 51 times -
every entry of ``SPIRIT_BUFF_MAP``. ``PySkill`` is the injected runtime\'s binding module, which this
port has no module of, so both are this port\'s ported generated lookup: ``from .skill_names import
GetSkillIDByName``, and ``GetSkillIDByName("<Name>")`` in the same 51 entries. It is the same
function, not a re-implementation - native\'s constructor is
``PySkillID(const std::string& name) : id(static_cast<int>(GW::skillbar::GetSkillIDByName(name))) {}``
(``Py4GW_Reforged_Native/src/GW/skillbar/skill_bindings.cpp:29-30``), and that table is ported in
``py4gw/enums_src/skill_names.py`` (``GetSkillIDByName``, ``skill_names.cpp:3075-3079``). Every
name string, every key, the order and the indentation of ``SPIRIT_BUFF_MAP`` are the source\'s.
"""
from __future__ import annotations

'''


def main() -> int:
    body = SOURCE.read_bytes()
    digest = hashlib.sha256(body).hexdigest().upper()
    print(f"source sha256: {digest}")
    if digest != SOURCE_SHA256:
        print("source revision differs from the inspected one - stopping")
        return 1

    text = body.decode("utf-8")
    if text.count(IMPORT_OLD) != 1:
        print(f"expected exactly one {IMPORT_OLD!r} line, found {text.count(IMPORT_OLD)}")
        return 1
    calls = CALL_RE.findall(text)
    print(f"PySkill.Skill(\"<Name>\").id.id reads found: {len(calls)}")
    if len(calls) != EXPECTED_CALLS:
        print(f"expected {EXPECTED_CALLS} reads - stopping")
        return 1

    converted = CALL_RE.sub(
        lambda match: f'GetSkillIDByName("{match.group(1)}")',
        text.replace(IMPORT_OLD, IMPORT_NEW),
    )
    new_body = converted.encode("utf-8")

    # The only lines that may differ from the source are the import and the 51 reads.
    source_lines = text.splitlines(keepends=True)
    new_lines = converted.splitlines(keepends=True)
    if len(source_lines) != len(new_lines):
        print(f"line count changed: {len(source_lines)} -> {len(new_lines)} - stopping")
        return 1
    changed = [
        (index + 1, old.rstrip("\r\n"), new.rstrip("\r\n"))
        for index, (old, new) in enumerate(zip(source_lines, new_lines))
        if old != new
    ]
    print(f"lines changed vs the source: {len(changed)} (expected {EXPECTED_CALLS + 1})")
    for line_number, old, new in changed[:3] + changed[-2:]:
        print(f"    line {line_number}: {old.strip()} -> {new.strip()}")
    if len(changed) != EXPECTED_CALLS + 1:
        print("unexpected difference set - stopping")
        return 1

    # Undoing the two substitutions must reproduce the source exactly.
    round_trip = CALL_NEW_RE.sub(
        lambda m: f'PySkill.Skill("{m.group(1)}").id.id', converted
    )
    round_trip = round_trip.replace(IMPORT_NEW, IMPORT_OLD)
    print(f"round trip reproduces the source exactly: {round_trip == text}")
    if round_trip != text:
        print("round trip differs - stopping")
        return 1

    header = HEADER.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8")
    target = header + new_body
    TARGET.write_bytes(target)

    print(f"target: {TARGET}")
    print(f"target bytes: {len(target)} (header {len(header)} + body {len(new_body)})")
    written = TARGET.read_bytes()
    print(f"target sha256: {hashlib.sha256(written).hexdigest().upper()}")
    print(f"target lines: {written.decode('utf-8').count(chr(10))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
