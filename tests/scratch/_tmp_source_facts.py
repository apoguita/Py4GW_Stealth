"""Throwaway: (1) negative control for the parity comparator, (2) the source's own oddities.

(1) builds deliberately broken copies of the ported file and runs the *real* comparison loop from
``model_enums_parity.py`` over them, to show the check reports each kind of difference. (2) lists
repeated values inside each enum class and repeated keys/values in the source's mapping.
"""

from __future__ import annotations

import enum
import importlib.util
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import model_enums_parity as parity  # noqa: E402

SOURCE_PATH = parity.SOURCE_PATH
TARGET_PATH = ROOT / "py4gw" / "enums_src" / "model_enums.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def compare_all(source_module, other_module) -> list[str]:
    problems = []
    for name in (n for n in vars(source_module) if not n.startswith("_")):
        if name not in vars(other_module):
            problems.append(f"MISMATCH {name}: missing from the port")
            continue
        problem = parity.compare(name, vars(source_module)[name], vars(other_module)[name])
        if problem is not None:
            problems.append(f"MISMATCH {name}: {problem}")
    return problems


def main() -> int:
    source_module = parity._load_source()
    text = TARGET_PATH.read_text(encoding="utf-8")

    perturbations = {
        "one member value changed": [("CHARR_AXEMASTER = 6630", "CHARR_AXEMASTER = 6631")],
        "one member added": [("    SPINED_ALOE = 1734\n", "    SPINED_ALOE = 1734\n    SPINED_EXTRA = 99999\n")],
        "one member removed": [("    FROST_WURM = 6491\n", "")],
        "one member renamed": [("    FOG_NIGHTMARE = 1732", "    FOG_NIGHTMARE_X = 1732")],
        "members reordered": [
            ("    CHARR_AXEMASTER = 6630\n    FOG_NIGHTMARE = 1732",
             "    FOG_NIGHTMARE = 1732\n    CHARR_AXEMASTER = 6630")
        ],
        "mapping entry dropped": [("    SpiritModelID.LIFE: PySkill.Skill(\"Life\").id.id,\n", "")],
        "mapping key order changed": [
            ("    SpiritModelID.FROZEN_SOIL: PySkill.Skill(\"Frozen_Soil\").id.id,\n    SpiritModelID.LIFE: PySkill.Skill(\"Life\").id.id,",
             "    SpiritModelID.LIFE: PySkill.Skill(\"Life\").id.id,\n    SpiritModelID.FROZEN_SOIL: PySkill.Skill(\"Frozen_Soil\").id.id,")
        ],
        "mapping skill name changed": [("PySkill.Skill(\"Bloodsong\")", "PySkill.Skill(\"BloodsongX\")")],
        "module constant changed": [("SPIRIT_OFFSET = 51", "SPIRIT_OFFSET = 52")],
    }

    for index, (label, replacements) in enumerate(perturbations.items()):
        broken = text
        for old, new in replacements:
            assert old in broken, f"anchor not found for {label!r}"
            broken = broken.replace(old, new, 1)
        path = ROOT / "tests/live_reports" / f"_tmp_broken_{index}.py"
        path.write_text(broken, encoding="utf-8")
        module = load(path, f"_tmp_broken_{index}")
        problems = compare_all(source_module, module)
        status = "detected" if problems else "NOT DETECTED"
        print(f"negative control [{label}]: {status}")
        for problem in problems[:4]:
            print(f"    {problem.splitlines()[0]}")
        path.unlink()

    print()
    print("=== the source's own values that repeat ===")
    for name, value in vars(source_module).items():
        if name.startswith("_"):
            continue
        if isinstance(value, enum.EnumMeta):
            groups: dict[object, list[str]] = {}
            for member_name in value.__members__:
                groups.setdefault(value.__members__[member_name].value, []).append(member_name)
            repeated = {v: names for v, names in groups.items() if len(names) > 1}
            print(f"{name}: {len(value.__members__)} declared names, "
                  f"{len(groups)} distinct values, {len(repeated)} value(s) carried by more than one name")
            for v in sorted(repeated, key=repr)[:8]:
                print(f"    {v!r} <- {repeated[v]}")
            if len(repeated) > 8:
                print(f"    ... and {len(repeated) - 8} more repeated value(s)")
        elif isinstance(value, dict):
            keys = list(value.keys())
            values = list(value.values())
            value_counts = Counter(values)
            print(f"{name}: {len(keys)} entries, {len(set(map(repr, keys)))} distinct keys, "
                  f"{len(set(map(repr, values)))} distinct values")
            for v, count in value_counts.items():
                if count > 1:
                    holders = [k for k in keys if value[k] == v]
                    print(f"    value {v!r} carried by {count} keys: {[str(k) for k in holders]}")
        else:
            print(f"{name}: {value!r}")
    return 0


raise SystemExit(main())
