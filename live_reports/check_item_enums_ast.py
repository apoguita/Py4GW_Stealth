"""Throwaway: compare the ported item_enums against the source at the AST level.

This needs no imports (so it works while model_enums is still being transcribed) and it compares the
*declarations*: every enum class's member names and value expressions, every method name, and every
module-level assignment's expression text. Run:

    python live_reports/check_item_enums_ast.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

SOURCE = Path(r"C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib\enums_src\Item_enums.py")
PORTED = Path(__file__).resolve().parents[1] / "py4gw" / "enums_src" / "item_enums.py"


def module_declarations(path: Path) -> dict[str, object]:
    """Return what a module declares: classes (members and methods) and module-level assignments."""

    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: dict[str, object] = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            members: list[tuple[str, str]] = []
            methods: list[str] = []
            for item in node.body:
                if isinstance(item, ast.Assign) and len(item.targets) == 1:
                    target = item.targets[0]
                    if isinstance(target, ast.Name):
                        members.append((target.id, ast.unparse(item.value)))
                elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    members.append((item.target.id, ast.unparse(item.value) if item.value else ""))
                elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    decorators = [ast.unparse(d) for d in item.decorator_list]
                    methods.append(f"{'/'.join(decorators)}:{item.name}")
            out[node.name] = {"bases": [ast.unparse(b) for b in node.bases], "members": members,
                              "methods": methods}
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                out[target.id] = ast.unparse(node.value)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            out[node.target.id] = ast.unparse(node.value) if node.value else ""
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out[node.name] = f"function:{node.name}"
    return out


def main() -> int:
    source = module_declarations(SOURCE)
    ported = module_declarations(PORTED)
    problems = 0

    for name, value in source.items():
        if name not in ported:
            print(f"MISSING {name}")
            problems += 1
            continue
        if isinstance(value, dict):
            ours = ported[name]
            assert isinstance(ours, dict)
            if ours["bases"] != value["bases"]:
                print(f"BASES {name}: {ours['bases']} != {value['bases']}")
                problems += 1
            if ours["members"] != value["members"]:
                their_names = dict(value["members"])
                our_names = dict(ours["members"])
                for member, expr in their_names.items():
                    if our_names.get(member) != expr:
                        print(f"MEMBER {name}.{member}: {our_names.get(member)!r} != {expr!r}")
                        problems += 1
                for member in our_names:
                    if member not in their_names:
                        print(f"EXTRA MEMBER {name}.{member}")
                        problems += 1
            if ours["methods"] != value["methods"]:
                print(f"METHODS {name}: {ours['methods']} != {value['methods']}")
                problems += 1
        else:
            if ported[name] != value:
                print(f"VALUE {name}:\n  ported: {ported[name]}\n  source: {value}")
                problems += 1

    for name in ported:
        if name not in source:
            print(f"EXTRA {name} (not in the source)")
            problems += 1

    print(f"item_enums AST parity: {len(source)} source declarations compared, {problems} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
