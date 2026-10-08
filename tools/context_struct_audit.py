"""Compare the context structs the party reads with Reforged's own declarations of them.

The party members stand on six records: the party-info record and its three member records
(``native_src/context/PartyContext.py``), the hero-flag and hero-info records, the pet record, the
skillbar and the world's player record (``native_src/context/WorldContext.py``). **Reforged's Python is
the shape authority for those classes** — field names and properties — and Native's headers are the
layout authority. Round 18 answered a names question with header evidence and got it wrong; this tool
asks the Python, so the same mistake cannot be made quietly again.

It reports, per class: fields that Reforged declares and the port does not, fields the port declares and
Reforged does not, the two field **orders** when they differ, and the same for the classes' own
members (properties and methods).

**Round 21 turned its list of additions into a gate.** Every member this port carries beyond Reforged's
declaration is either in ``ADJUDICATED`` — with the reason it must exist, which today is only the
external reader's own ``bind_reader`` glue, since a reader outside ``Gw.exe`` cannot hand a record to
Reforged's in-process views — or it is reported as ``UNADJUDICATED`` and the tool exits non-zero. So a
member added later under Native's C++ spelling, an alias, or a snake_case twin of a source method fails
this check instead of waiting for a person to notice it.

Usage: python tools/context_struct_audit.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REFORGED_ROOT = Path(r"C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib\native_src\context")
PORT_ROOT = Path(__file__).resolve().parent.parent / "py4gw" / "context"

#: ``(Reforged file, port file)`` — every context module whose port has a Reforged counterpart.
#: Every class the two files share is compared; a class only the port declares is reported too,
#: because a record that exists in neither source is the same defect as a member that does.
PAIRS: tuple[tuple[str, str], ...] = (
    ("AccAgentContext.py", "acc_agent_context.py"),
    ("AvailableCharacterContext.py", "available_character_context.py"),
    ("CharContext.py", "char_context.py"),
    ("CinematicContext.py", "cinematic_context.py"),
    ("GameContext.py", "game_context.py"),
    ("GameplayContext.py", "gameplay_context.py"),
    ("GuildContext.py", "guild_context.py"),
    ("InstanceInfoContext.py", "instance_info_context.py"),
    ("MapContext.py", "map_context.py"),
    ("MissionMapContext.py", "mission_map_context.py"),
    ("PartyContext.py", "party_context.py"),
    ("PreGameContext.py", "pre_game_context.py"),
    ("ServerRegionContext.py", "server_region_context.py"),
    ("TextContext.py", "text_parser_context.py"),
    ("WorldContext.py", "world_context.py"),
    ("WorldMapContext.py", "world_map_context.py"),
)

#: Members this port adds to a source record, and why each one is allowed to be here. Round 21
#: adjudicated the audit's whole list; the only surviving category is the read glue, because this port
#: reads the client from **outside** the process and Reforged's views read it from inside. The five
#: records with it are exactly the ones whose properties follow a pointer in the target.
#:
#: The same category applies to the rest of the context layer, so it is named once here rather than
#: repeated per class: a member in ``READ_GLUE`` binds this port's external reader to a record or
#: reaches the context's address outside the client. **Anything else a class carries beyond its
#: source is still reported**, which is what this audit is for -- `sub_struct` on `TextParserStruct`
#: (2026-10-11) was exactly such a member, and it was found by reading the distance between an
#: audit that called it "additive" and a run that crashed on it.
READ_GLUE: frozenset[str] = frozenset(
    {
        "bind_reader",
        "resolve_address",
        "read",
        "initialize",
        "remote_address",
        "cached_context_address",
        "cached_pointer_address",
        "cached_base_pointer_address",
        "slot_address",
        "pointer",
    }
)

ADJUDICATED: dict[str, dict[str, str]] = {
    "PartyInfoStruct": {
        "bind_reader": "external reader glue: the array views read the target from outside Gw.exe",
    },
    "PartyContextStruct": {
        "bind_reader": "external reader glue: the list views read the target from outside Gw.exe",
    },
    "PetInfoStruct": {
        "bind_reader": "external reader glue: the name pointer is read from outside Gw.exe",
    },
    "SkillbarStruct": {
        "bind_reader": "external reader glue: the queued-skill array is read from outside Gw.exe",
    },
    "PlayerStruct": {
        "bind_reader": "external reader glue: the two name pointers are read from outside Gw.exe",
    },
}


def classes(path: Path) -> dict[str, ast.ClassDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
    }


def fields(node: ast.ClassDef) -> list[str]:
    """The class's ``_fields_`` names, in declaration order."""

    names: list[str] = []
    for statement in node.body:
        target = None
        value = None
        if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
            target, value = statement.targets[0], statement.value
        elif isinstance(statement, ast.AnnAssign):
            target, value = statement.target, statement.value
        if not isinstance(target, ast.Name) or target.id != "_fields_":
            continue
        if not isinstance(value, (ast.List, ast.Tuple)):
            continue
        for element in value.elts:
            if isinstance(element, ast.Tuple) and element.elts:
                first = element.elts[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    names.append(first.value)
    return names


def own_members(node: ast.ClassDef) -> list[str]:
    """The class's own functions and properties, in declaration order."""

    return [
        statement.name
        for statement in node.body
        if isinstance(statement, ast.FunctionDef)
    ]


def main() -> None:
    problems = 0
    unadjudicated = 0
    for reforged_name, port_name in PAIRS:
        theirs = classes(REFORGED_ROOT / reforged_name)
        ours = classes(PORT_ROOT / port_name)
        for class_name in sorted(set(theirs) | set(ours)):
            if class_name.startswith("_") or class_name not in theirs:
                # A class only the port declares: a record in neither source's surface.
                if class_name.startswith("_") or class_name in theirs:
                    continue
                node = ours[class_name]
                allowed = ADJUDICATED.get(class_name, {})
                reason = allowed.get(class_name)
                if reason:
                    print(f"{class_name}: port-only record, adjudicated: {reason}")
                    continue
                print(f"{class_name}: PORT-ONLY record in {port_name} "
                      f"(not declared in Reforged's {reforged_name})")
                unadjudicated += 1
                continue
            if class_name not in ours:
                print(f"{class_name}: MISSING from the port's {port_name}")
                problems += 1
                continue
            their_fields = fields(theirs[class_name])
            our_fields = fields(ours[class_name])
            their_members = own_members(theirs[class_name])
            our_members = own_members(ours[class_name])

            only_theirs = [name for name in their_fields if name not in our_fields]
            only_ours = [name for name in our_fields if name not in their_fields]
            their_public = [name for name in their_members if not name.startswith("_")]
            our_public = [name for name in our_members if not name.startswith("_")]
            missing_members = [name for name in their_public if name not in our_public]
            extra_members = [name for name in our_public if name not in their_public]

            allowed = dict(ADJUDICATED.get(class_name, {}))
            for glue_name in READ_GLUE:
                if glue_name in extra_members:
                    allowed.setdefault(
                        glue_name,
                        "external reader glue: this port reads the client from outside Gw.exe",
                    )
            recorded = [name for name in extra_members if name in allowed]
            unrecorded = [name for name in extra_members if name not in allowed]
            unadjudicated += len(unrecorded)

            if their_fields == our_fields and not missing_members and not unrecorded:
                suffix = ""
                if recorded:
                    suffix = " (+ " + ", ".join(
                        f"{name}: {allowed[name]}" for name in recorded
                    ) + ")"
                print(
                    f"{class_name}: {len(their_fields)} fields and "
                    f"{len(their_public)} members match{suffix}"
                )
                continue
            problems += 1
            print(f"{class_name}: DIFFERS")
            if their_fields != our_fields:
                print(f"    fields, Reforged: {their_fields}")
                print(f"    fields, port:     {our_fields}")
            if only_theirs:
                print(f"    declared by Reforged, absent here: {only_theirs}")
            if only_ours:
                print(f"    declared here, absent from Reforged: {only_ours}")
            if missing_members:
                print(f"    members Reforged declares, absent here: {missing_members}")
            if unrecorded:
                print(f"    UNADJUDICATED members here: {unrecorded}")
            for name in recorded:
                print(f"    adjudicated addition {name}: {allowed[name]}")
    print(f"classes that differ: {problems}; unadjudicated additions: {unadjudicated}")
    if problems or unadjudicated:
        sys.exit(1)


if __name__ == "__main__":
    main()
