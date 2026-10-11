import sys
sys.path.insert(0, r"C:\Users\Apo\Py4GW_Stealth")
sys.path.insert(0, r"C:\Users\Apo\Py4GW_Stealth\tools")
from generate_gwa3_family import FAMILIES, GWAU3_DATA_DIR, declared_keys

for family in FAMILIES:
    holder = family.source_function or family.function
    lines = (GWAU3_DATA_DIR / family.source_file).read_text(encoding="utf-8", errors="replace").splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.startswith(f"Func {holder}("))
    except StopIteration:
        print(f"{family.module:18s} NO START {holder}")
        continue
    exact = next((i for i in range(start, len(lines)) if lines[i].strip() == "EndFunc"), None)
    anyform = next((i for i in range(start, len(lines)) if lines[i].strip().startswith("EndFunc")), None)
    overrun = (exact is None) or (anyform is not None and exact != anyform)
    declared = len(declared_keys(family))
    print(
        f"{family.module:18s} {holder:34s} first EndFunc any-form line {anyform + 1:6d} "
        f"({lines[anyform].strip()[:48]!r}) | parser stops at line {exact + 1 if exact is not None else None}"
        f" | OVERRUN={overrun} | declared keys {declared}"
    )
