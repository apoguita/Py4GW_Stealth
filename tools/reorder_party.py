"""Rewrite ``py4gw/party.py`` so ``Party``'s members sit in Reforged's own declaration order.

The porting rule is "same order, same nesting" — and the port's own tests check *presence* and check
the transcribed lists against the source, but nothing checked the **order of the port's own file**.
`tools/party_signature_audit.py` found that `Party`, `Players`, `Heroes` and `Pets` were grouped by
subject instead of by the source's sequence. This moves the blocks.

It is deliberately mechanical: every member's lines are taken verbatim (its decorators, its comments
directly above it, its body), and only their order changes. Members that the source does not have —
the port's private helpers — keep their place at the top of their class, and nothing outside the
`Party` class is touched.

Usage: python tools/reorder_party.py [--check]
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REFORGED = Path(r"C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib\Party.py")
PORT = Path(__file__).resolve().parent.parent / "py4gw" / "party.py"

#: Indentation of a member inside ``Party`` and inside one of its namespaces.
CLASS_INDENT = "    "


def _comment_start(lines: list[str], first: int) -> int:
    """Extend one block upward over the comment lines that sit directly above it."""

    start = first
    while start - 2 >= 0:
        previous = lines[start - 2]
        if previous.strip().startswith("#") and previous.strip():
            start -= 1
            continue
        break
    return start


def _blocks(lines: list[str], node: ast.ClassDef) -> dict[str, tuple[int, int]]:
    """``{member name: (first line, last line)}``, 1-based and inclusive, for one class body."""

    found: dict[str, tuple[int, int]] = {}
    for child in node.body:
        if not isinstance(child, (ast.FunctionDef, ast.ClassDef)):
            continue
        first = child.lineno
        if isinstance(child, ast.FunctionDef):
            for decorator in child.decorator_list:
                first = min(first, decorator.lineno)
        found[child.name] = (_comment_start(lines, first), int(child.end_lineno or child.lineno))
    return found


def order_of(path: Path, class_name: str) -> dict[str, list[str]]:
    """``{namespace: [member, …]}`` in the source's declaration order."""

    tree = ast.parse(path.read_text(encoding="utf-8"))
    klass = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    found: dict[str, list[str]] = {
        "": [
            child.name
            for child in klass.body
            if isinstance(child, ast.FunctionDef) and not child.name.startswith("_")
        ]
    }
    for child in klass.body:
        if isinstance(child, ast.ClassDef):
            found[child.name] = [
                grandchild.name
                for grandchild in child.body
                if isinstance(grandchild, ast.FunctionDef)
            ]
    return found


def reorder() -> tuple[str, list[str]]:
    """Return the rewritten module text and a log of what moved."""

    lines = PORT.read_text(encoding="utf-8").splitlines(keepends=True)
    tree = ast.parse("".join(lines))
    klass = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "Party"
    )
    target = order_of(REFORGED, "Party")

    class_start = _comment_start(lines, klass.lineno)
    class_end = int(klass.end_lineno or klass.lineno)
    header_end = klass.body[0].end_lineno if klass.body else klass.lineno  # the class docstring

    log: list[str] = []
    body: list[str] = []
    # The class header and its docstring stay exactly as they are.
    body.extend(lines[class_start - 1 : int(header_end or klass.lineno)])
    body.append("\n")

    members = _blocks(lines, klass)
    emitted: set[str] = set()

    def emit(name: str) -> None:
        first, last = members[name]
        body.extend(lines[first - 1 : last])
        body.append("\n")
        emitted.add(name)

    # The port's own private helpers first: the source has no members of that kind to place them by.
    for child in klass.body:
        if isinstance(child, ast.FunctionDef) and child.name.startswith("_"):
            emit(child.name)
            log.append(f"kept the private helper {child.name} at the top")

    for name in target[""]:
        if name not in members:
            raise SystemExit(f"the port does not declare {name}")
        emit(name)

    for namespace in ("Players", "Heroes", "Henchmen", "Pets"):
        nested = next(
            child
            for child in klass.body
            if isinstance(child, ast.ClassDef) and child.name == namespace
        )
        nested_start = _comment_start(lines, nested.lineno)
        nested_end = int(nested.end_lineno or nested.lineno)
        nested_body = _blocks(lines, nested)
        nested_docstring_end = int(
            nested.body[0].end_lineno
            if nested.body and nested.body[0].end_lineno
            else nested.lineno
        )
        rebuilt: list[str] = []
        rebuilt.extend(lines[nested_start - 1 : nested_docstring_end])
        rebuilt.append("\n")

        def emit_nested(name: str) -> None:
            first, last = nested_body[name]
            rebuilt.extend(lines[first - 1 : last])
            rebuilt.append("\n")
            emitted.add(f"{namespace}.{name}")

        for grandchild in nested.body:
            if isinstance(grandchild, ast.FunctionDef) and grandchild.name.startswith("_"):
                emit_nested(grandchild.name)
                log.append(f"kept the private helper {namespace}.{grandchild.name} at the top")
        for name in target[namespace]:
            if name not in nested_body:
                raise SystemExit(f"the port does not declare {namespace}.{name}")
            emit_nested(name)

        before = [line.rstrip("\n") for line in lines[nested_start - 1 : nested_end]]
        after = [line.rstrip("\n") for line in rebuilt]
        if before != after:
            log.append(f"reordered {namespace} ({len(target[namespace])} members)")
        body.extend(rebuilt)

    # One blank line between the rebuilt class and whatever follows it, whatever the tail looks like:
    # the run has to be idempotent, or a second pass would keep adding whitespace.
    while body and not body[-1].strip():
        body.pop()
    body.append("\n")
    tail = lines[class_end:]
    if tail and not tail[0].strip():
        tail = tail[1:]
    text = "".join(lines[: class_start - 1]) + "".join(body) + "".join(tail)
    return text, log


def main() -> int:
    text, log = reorder()
    for line in log:
        print(line)
    if "--check" in sys.argv:
        current = PORT.read_text(encoding="utf-8")
        print("already in the source's order" if current == text else "would change the file")
        return 0
    PORT.write_text(text, encoding="utf-8", newline="\n")
    print("written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
