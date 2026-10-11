import sys
sys.path.insert(0, r"C:\Users\Apo\Py4GW_Stealth")
sys.path.insert(0, r"C:\Users\Apo\Py4GW_Stealth\tools")
from generate_gwa3_family import FAMILIES, GWAU3_DATA_DIR, parse_cases, declared_keys

family = next(f for f in FAMILIES if f.module == "data_item")
holder = family.source_function or family.function
parsed = {key for case in parse_cases(family) for key in case.keys}
declared = declared_keys(family)
print("parsed keys not declared :", sorted(parsed - declared))
print("declared not parsed      :", sorted(declared - parsed))
print("parsed:", len(parsed), "declared:", len(declared))
lines = (GWAU3_DATA_DIR / family.source_file).read_text(encoding="utf-8", errors="replace").splitlines()
print("--- lines 680-698 ---")
for i in range(679, 698):
    print(f"{i + 1:4d}| {lines[i]}")
