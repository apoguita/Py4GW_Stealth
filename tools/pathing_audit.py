"""Audit the port's ``pathing.py`` against Reforged's ``Pathing.py``, member by member.

Answers one question with evidence: **is the pathing class ported whole?** It compares, for every class
the source declares, the member names in declaration order and the parameter lists, and reports every
member of the port that raises instead of answering.

Usage: python tools/pathing_audit.py
"""

from __future__ import annotations

import ast
import io
import sys
from pathlib import Path

SOURCE = Path(r"C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib\Pathing.py")
PORT = Path(__file__).resolve().parent.parent / "py4gw" / "pathing.py"


def load(path: Path) -> ast.Module:
    return ast.parse(io.open(path, encoding="utf-8").read())


def classes(tree: ast.Module) -> dict[str, ast.ClassDef]:
    return {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}


def functions(tree: ast.Module) -> dict[str, ast.FunctionDef]:
    return {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}


def members(node: ast.ClassDef) -> list[str]:
    return [n.name for n in node.body if isinstance(n, ast.FunctionDef)]


def member_map(node: ast.ClassDef) -> dict[str, ast.FunctionDef]:
    return {n.name: n for n in node.body if isinstance(n, ast.FunctionDef)}


def signature(node: ast.FunctionDef) -> str:
    args = node.args
    names = [a.arg for a in args.posonlyargs + args.args]
    if names and names[0] in ("self", "cls"):
        names = names[1:]
    defaults = len(args.defaults)
    rendered = [
        name if index < len(names) - defaults else f"{name}=…"
        for index, name in enumerate(names)
    ]
    if args.vararg:
        rendered.append("*" + args.vararg.arg)
    rendered.extend(f"{a.arg}=…" for a in args.kwonlyargs)
    return "(" + ", ".join(rendered) + ")"


def raises(node: ast.FunctionDef) -> str | None:
    for sub in ast.walk(node):
        if isinstance(sub, ast.Raise) and sub.exc is not None:
            text = ast.dump(sub)
            if "NotImplementedError" in text or "_unported" in text:
                message = ""
                for piece in ast.walk(sub):
                    if isinstance(piece, ast.Constant) and isinstance(piece.value, str):
                        message = piece.value
                return message[:110]
    return None


def main() -> int:
    theirs, ours = load(SOURCE), load(PORT)
    their_classes, our_classes = classes(theirs), classes(ours)
    their_funcs, our_funcs = functions(theirs), functions(ours)
    problems = 0
    missing_members = 0
    raising = 0

    print("== classes ==")
    for name, node in their_classes.items():
        if name not in our_classes:
            print(f"  {name}: MISSING from the port")
            problems += 1
            continue
        source_members = members(node)
        port_members = members(our_classes[name])
        absent = [m for m in source_members if m not in port_members]
        extra = [m for m in port_members if m not in source_members]
        order_ok = [m for m in port_members if m in source_members] == [
            m for m in source_members if m in port_members
        ]
        for member in source_members:
            if member in port_members:
                their_signature = signature(member_map(node)[member])
                our_node = member_map(our_classes[name])[member]
                our_signature = signature(our_node)
                if their_signature != our_signature:
                    print(f"  {name}.{member}: signature {our_signature} vs source {their_signature}")
                    problems += 1
                message = raises(our_node)
                if message:
                    raising += 1
                    print(f"  {name}.{member}: RAISES -> {message}")
        missing_members += len(absent)
        state = "ok" if not absent and not extra and order_ok else "DIFFERS"
        if state != "ok":
            problems += 1
        print(
            f"  {name}: {len(source_members)} members, {state}"
            + (f"; absent {absent}" if absent else "")
            + (f"; extra {extra}" if extra else "")
            + ("" if order_ok else "; ORDER DIFFERS")
        )

    print("== module functions ==")
    for name, node in their_funcs.items():
        if name not in our_funcs:
            print(f"  {name}: MISSING from the port")
            problems += 1
            continue
        their_signature = signature(node)
        our_signature = signature(our_funcs[name])
        note = "" if their_signature == our_signature else f"  signature {our_signature} vs {their_signature}"
        if note:
            problems += 1
        print(f"  {name}: present{note}")
    for name in our_funcs:
        if name not in their_funcs:
            print(f"  {name}: in the port only")

    print(
        f"== totals: {problems} problem(s), {missing_members} missing member(s), "
        f"{raising} raising member(s) =="
    )
    return 1 if problems or missing_members else 0


if __name__ == "__main__":
    sys.exit(main())
