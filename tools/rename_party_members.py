"""Rename the three party-member records to the names both sources use.

Reforged's ``native_src/context/PartyContext.py`` declares ``PlayerPartyMember``, ``HeroPartyMember``
and ``HenchmanPartyMember`` (``:9``, ``:23``, ``:34``) and Native's binding constructs the same names
(``party_bindings.cpp:315``); this port had named them ``…Struct`` and kept the sources' names as
aliases at the bottom of the module. A name that belongs to the sources belongs to the sources, and an
invented alias is a deviation, so round 20 inverts it: the classes carry the sources' names and the
``…Struct`` spellings are gone.

Usage: python tools/rename_party_members.py [--check]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FILES = (
    "py4gw/context/party_context.py",
    "py4gw/context/party_context.pyi",
    "py4gw/context/__init__.py",
    "py4gw/party.py",
    "tests/test_party_context.py",
    "tests/test_party_context_offline.py",
    "tests/test_player.py",
    "tools/context_struct_audit.py",
)

#: Longest first, so ``PlayerPartyMemberStruct`` becomes ``PlayerPartyMember`` and not ``PlayerPartyMemberStruct``
#: with a leftover suffix.
RENAMES = (
    ("PlayerPartyMemberStruct", "PlayerPartyMember"),
    ("HenchmanPartyMemberStruct", "HenchmanPartyMember"),
    ("HeroPartyMemberStruct", "HeroPartyMember"),
)

ALIAS_BLOCK = """PlayerPartyMember = PlayerPartyMemberStruct
HeroPartyMember = HeroPartyMemberStruct
HenchmanPartyMember = HenchmanPartyMemberStruct
"""


def main() -> int:
    check = "--check" in sys.argv
    for relative in FILES:
        path = ROOT / relative
        if not path.exists():
            print(f"{relative}: not present")
            continue
        text = path.read_text(encoding="utf-8")
        original = text
        for old, new in RENAMES:
            text = re.sub(rf"\b{old}\b", new, text)
        text = text.replace(ALIAS_BLOCK, "")
        if text == original:
            print(f"{relative}: unchanged")
            continue
        count = sum(
            len(re.findall(rf"\b{old}\b", original)) for old, _ in RENAMES
        )
        print(f"{relative}: {count} reference(s) renamed")
        if not check:
            path.write_text(text, encoding="utf-8", newline="\n")
    if check:
        print("(check only: nothing written)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
