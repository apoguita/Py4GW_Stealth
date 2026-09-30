"""Compare ``Party``'s members between Reforged and this port, two ways.

**Arguments.** The parity the test suite checks is names and nesting. This checks the next thing a
caller sees: the parameter names and their defaults, which is where a port drifts without any test
noticing — ``Heroes.FlagHero(hero_id, x, y)`` answering a differently-named third argument is still
callable by position and wrong by keyword.

**Return values.** Whether a member hands a value back at all, which is the other half of a call-site
contract: a member that answers ``None`` where the source returns a bool, or a value where the source
returns nothing, is a caller's ``if`` behaving differently. A source that simply *falls off the end*
(no ``return`` statement) is reported apart from one that returns ``None`` explicitly: Python makes
those the same object, and the difference says which shape the source wrote.

Usage: python tools/party_signature_audit.py
"""

from __future__ import annotations

import ast
from pathlib import Path

REFORGED = Path(r"C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib\Party.py")
PORT = Path(__file__).resolve().parent.parent / "py4gw" / "party.py"


def members(path: Path, class_name: str) -> dict[str, ast.FunctionDef]:
    """Return ``{"Namespace.member": node}`` for one class and its nested namespaces."""

    tree = ast.parse(path.read_text(encoding="utf-8"))
    klass = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    found: dict[str, ast.FunctionDef] = {}

    def walk(node: ast.ClassDef, prefix: str) -> None:
        for child in node.body:
            if isinstance(child, ast.ClassDef):
                walk(child, f"{prefix}{child.name}.")
                continue
            if isinstance(child, ast.FunctionDef):
                found[f"{prefix}{child.name}"] = child

    walk(klass, "")
    return found


def signatures(path: Path, class_name: str) -> dict[str, str]:
    """Return ``{member: "arg, arg=default"}`` for one class and its nested namespaces."""

    found: dict[str, str] = {}
    for name, child in members(path, class_name).items():
        arguments = child.args
        rendered = [argument.arg for argument in arguments.posonlyargs]
        rendered += [argument.arg for argument in arguments.args]
        defaults = [ast.unparse(value) for value in arguments.defaults]
        for index, value in enumerate(defaults):
            position = len(rendered) - len(defaults) + index
            rendered[position] = f"{rendered[position]}={value}"
        if arguments.vararg:
            rendered.append(f"*{arguments.vararg.arg}")
        if arguments.kwarg:
            rendered.append(f"**{arguments.kwarg.arg}")
        found[name] = ", ".join(rendered)
    return found


def returns(node: ast.FunctionDef) -> str:
    """``"value"``, ``"none"`` or ``"falls-off"`` — what the body hands back."""

    if any(
        isinstance(statement, ast.Return) and statement.value is not None
        for statement in ast.walk(node)
    ):
        return "value"
    if any(
        isinstance(statement, ast.Return) and statement.value is None
        for statement in ast.walk(node)
    ):
        return "none"
    return "falls-off"


def names_in_order(path: Path, class_name: str) -> dict[str, list[str]]:
    """Return ``{namespace: [member, …]}`` in **declaration order**, namespaces included."""

    tree = ast.parse(path.read_text(encoding="utf-8"))
    klass = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    found: dict[str, list[str]] = {"": []}
    for child in klass.body:
        if isinstance(child, ast.ClassDef):
            found[child.name] = [
                grandchild.name
                for grandchild in child.body
                if isinstance(grandchild, ast.FunctionDef)
            ]
        elif isinstance(child, ast.FunctionDef):
            found[""].append(child.name)
    return found


def main() -> None:
    source = signatures(REFORGED, "Party")
    port = signatures(PORT, "Party")
    only_source = sorted(set(source) - set(port))
    only_port = sorted(set(port) - set(source))
    print(f"source members: {len(source)}, port members: {len(port)}")
    if only_source:
        print("missing from the port:", only_source)
    if only_port:
        print("only in the port:", only_port)

    mismatches = 0
    for name in sorted(set(source) & set(port)):
        if source[name] != port[name]:
            mismatches += 1
            print(f"  {name}\n    source: {source[name]}\n    port:   {port[name]}")
    print(f"argument-list mismatches: {mismatches}")

    source_nodes = members(REFORGED, "Party")
    port_nodes = members(PORT, "Party")
    print("\nreturn shapes, where they differ (private members excluded):")
    differences = 0
    for name in sorted(set(source_nodes) & set(port_nodes)):
        if name.startswith("_") or "._" in name:
            continue
        theirs = returns(source_nodes[name])
        ours = returns(port_nodes[name])
        if theirs == ours:
            continue
        differences += 1
        print(f"  {name}: source {theirs}, port {ours}")
    print(f"return-shape differences: {differences}")

    print("\ndeclaration order (the source's own order is the port's):")
    theirs_order = names_in_order(REFORGED, "Party")
    ours_order = names_in_order(PORT, "Party")
    for namespace in theirs_order:
        theirs_list = theirs_order[namespace]
        ours_list = [name for name in ours_order.get(namespace, []) if not name.startswith("_")]
        label = namespace or "Party"
        if theirs_list == ours_list:
            print(f"  {label}: {len(theirs_list)} members, in the source's order")
            continue
        print(f"  {label}: ORDER DIFFERS")
        print(f"    source: {theirs_list}")
        print(f"    port:   {ours_list}")


if __name__ == "__main__":
    main()
