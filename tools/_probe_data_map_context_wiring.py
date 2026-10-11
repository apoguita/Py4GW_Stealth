import sys, re
sys.path.insert(0, r"C:\Users\Apo\Py4GW_Stealth")
sys.path.insert(0, r"C:\Users\Apo\Py4GW_Stealth\tools")
from generate_gwa3_family import Family, parse_cases, render, declared_keys

f = Family(
    module="data_map_context",
    source_file="GwAu3_Data_MapContext.au3",
    function="Map_GetMapContextInfo",
    summary="probe",
    structure=("context.map_context", "MapContextStruct"),
    record_call="client.read_map_context()",
    record_arg="",
    computed={
        "MapBoundaries": "[float(value) for value in record.map_boundaries]",
        "Sub1": "record.path_context if record.path_context is not None else 0",
        "PropsContext": "record.props if record.props is not None else 0",
        "Spawns1": "record.spawns1",
        "Spawns2": "record.spawns2",
        "Spawns3": "record.spawns3",
    },
    unimplemented={"Terrain": "x", "Zones": "y"},
    extra_exports=(
        "Map_GetPathingMapArrayInfo",
        "Map_GetPropsContext",
        "Map_GetTotalTrapezoidCount",
    ),
    helper_files=("data_map_context_stragglers.py",),
)

cases = parse_cases(f)
print("parsed cases:", [(c.keys, hex(c.offset), c.type_text, c.attribute, c.inner) for c in cases])
print("declared keys:", sorted(declared_keys(f)))
text = render(f, cases)
print("rendered chars:", len(text))
print("keys in table:", sorted(re.findall(r'^\s+"([^"]+)":', text, re.MULTILINE)))
print("duplicate defs:", [n for n in ("Map_GetMapContextInfo", "Map_GetPathingMapArrayInfo", "Map_GetPropsContext", "Map_GetTotalTrapezoidCount") if text.count("def " + n + "(") != 1])
compile(text, "data_map_context.py", "exec")
print("generated module compiles: ok")
print("__all__:", [l for l in text.splitlines() if l.startswith("__all__")])
for key in ("MapBoundaries", "Sub1", "PropsContext", "Spawns1", "MapGetX"):
    pass
for line in text.splitlines():
    if "MapBoundaries" in line or "Spawns1\"" in line or "PropsContext\"" in line or "Sub1\"" in line:
        print("  ", line.strip())
