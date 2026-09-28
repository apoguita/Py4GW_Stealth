"""Throwaway parity check: the ported ``model_enums`` against its Reforged source.

Loads ``Py4GW_Reforged/Py4GWCoreLib/enums_src/Model_enums.py`` by absolute path, imports
``py4gw.enums_src.model_enums``, and compares every public name of the source module with the
name of the same spelling in the port:

* ``enum.IntEnum``/``Enum`` subclasses - the full ordered ``[(member name, member value)]`` list,
  read from ``__members__`` so that aliases are included and counted;
* ``dict`` - equality *and* key order;
* ``set``/``frozenset``/``list``/``tuple`` - equality;
* plain values - type and equality.

Prints ``MISMATCH <name>: ...`` for every difference and ends with the parity line.

The source's second import is ``import PySkill`` - Reforged's native binding module, provided
in-process by its injected runtime, which does not exist in this environment. A deterministic shim
is installed in ``sys.modules`` so that both modules can be loaded and executed; both reads go
through the same shim, and its id is a digest of the skill name, so the two modules compare equal
only if they run the same code over the same name strings.
"""

from __future__ import annotations

import enum
import hashlib
import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = Path(r"C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib\enums_src\Model_enums.py")


class _SkillID:
    """Stands in for native's skill-id record: ``.id`` is the integer the source reads."""

    def __init__(self, value: int) -> None:
        self.id = value

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _SkillID) and other.id == self.id

    def __hash__(self) -> int:
        return hash(self.id)

    def __repr__(self) -> str:
        return f"_SkillID({self.id})"


class _Skill:
    """Stands in for native's ``PySkill.Skill``; ``Skill(<name>).id.id`` is its shape."""

    def __init__(self, name: str) -> None:
        digest = hashlib.sha256(str(name).encode("utf-8")).hexdigest()[:8]
        self.id = _SkillID(int(digest, 16))

    def __repr__(self) -> str:
        return f"_Skill(id={self.id!r})"


if "PySkill" not in sys.modules:
    _shim = types.ModuleType("PySkill")
    _shim.Skill = _Skill  # type: ignore[attr-defined]
    sys.modules["PySkill"] = _shim
    print("note: PySkill (native binding module) is absent here; a deterministic shim stands in")


def _load_source() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("_reforged_model_enums_source", SOURCE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {SOURCE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _enum_members(cls: type[enum.Enum]) -> list[tuple[str, object]]:
    """Every declared name in declaration order, aliases included, with its value."""
    return [(name, cls.__members__[name].value) for name in cls.__members__]


def _first_enum_difference(
    left: list[tuple[str, object]], right: list[tuple[str, object]]
) -> str:
    for index in range(max(len(left), len(right))):
        l_item = left[index] if index < len(left) else None
        r_item = right[index] if index < len(right) else None
        if l_item != r_item:
            return f"first difference at index {index}: source {l_item!r} vs port {r_item!r}"
    return "no difference"


def _first_key_difference(left: list[object], right: list[object]) -> str:
    for index in range(max(len(left), len(right))):
        l_item = left[index] if index < len(left) else None
        r_item = right[index] if index < len(right) else None
        if l_item != r_item:
            return f"first key difference at index {index}: source {l_item!r} vs port {r_item!r}"
    return "no difference"


def compare(name: str, source_value: object, port_value: object) -> str | None:
    """Return a mismatch description, or None when the two agree."""
    if source_value is port_value:
        return None

    if isinstance(source_value, enum.EnumMeta) or isinstance(port_value, enum.EnumMeta):
        if not isinstance(source_value, enum.EnumMeta):
            return f"source is {type(source_value).__name__}, port is an enum class"
        if not isinstance(port_value, enum.EnumMeta):
            return f"port is {type(port_value).__name__}, source is an enum class"
        left = _enum_members(source_value)
        right = _enum_members(port_value)
        if left != right:
            return (
                f"{len(left)} source members vs {len(right)} port members; "
                + _first_enum_difference(left, right)
            )
        return None

    if isinstance(source_value, dict) or isinstance(port_value, dict):
        if not isinstance(source_value, dict) or not isinstance(port_value, dict):
            return f"source is {type(source_value).__name__}, port is {type(port_value).__name__}"
        left_keys = list(source_value.keys())
        right_keys = list(port_value.keys())
        if left_keys != right_keys:
            return (
                f"{len(left_keys)} source keys vs {len(right_keys)} port keys; "
                + _first_key_difference(left_keys, right_keys)
            )
        if source_value != port_value:
            for key in left_keys:
                if source_value[key] != port_value[key]:
                    return (
                        f"value at key {key!r} differs: "
                        f"source {source_value[key]!r} vs port {port_value[key]!r}"
                    )
            return "dicts compare unequal with identical keys"
        return None

    if isinstance(source_value, (set, frozenset)) or isinstance(port_value, (set, frozenset)):
        if type(source_value) is not type(port_value):
            return f"source is {type(source_value).__name__}, port is {type(port_value).__name__}"
        if source_value != port_value:
            return f"source {sorted(map(repr, source_value))!r} vs port {sorted(map(repr, port_value))!r}"
        return None

    if isinstance(source_value, (list, tuple)) or isinstance(port_value, (list, tuple)):
        if type(source_value) is not type(port_value):
            return f"source is {type(source_value).__name__}, port is {type(port_value).__name__}"
        if list(source_value) != list(port_value):
            return f"source {source_value!r} vs port {port_value!r}"
        return None

    if type(source_value) is not type(port_value):
        return f"source type {type(source_value).__name__}, port type {type(port_value).__name__}"
    if source_value != port_value:
        return f"source {source_value!r} vs port {port_value!r}"
    return None


def main() -> int:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    source_module = _load_source()
    import py4gw.enums_src.model_enums as port_module  # noqa: E402

    print(f"source: {SOURCE_PATH}")
    print(f"port:   {Path(port_module.__file__).resolve()}")

    public = [name for name in vars(source_module) if not name.startswith("_")]
    compared = 0
    mismatches = 0
    for name in public:
        compared += 1
        if name not in vars(port_module):
            mismatches += 1
            print(f"MISMATCH {name}: missing from the port")
            continue
        problem = compare(name, vars(source_module)[name], vars(port_module)[name])
        if problem is not None:
            mismatches += 1
            print(f"MISMATCH {name}: {problem}")

    extra = sorted(
        name
        for name in vars(port_module)
        if not name.startswith("_") and name not in public
    )
    if extra:
        print(f"note: public names the port declares and the source does not: {extra}")

    print(f"model_enums parity: {compared} names compared, {mismatches} mismatches")
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
