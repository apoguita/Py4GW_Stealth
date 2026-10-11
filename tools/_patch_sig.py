"""One-off: swap the generated accessor's first parameter for the family's own spelling.

`World_GetWorldInfo`'s only parameter is the field name -- GwAu3 writes
`Func World_GetWorldInfo($a_s_Info = "")` (`GwAu3_Data_World.au3:10`) -- so emitting a record-id
parameter shifts the caller's argument into the wrong slot. Delete after running.
"""

from __future__ import annotations

from pathlib import Path

PATH = Path(__file__).resolve().parent / "generate_gwa3_family.py"
text = PATH.read_text(encoding="utf-8")

old = 'def {family.function}(record_id: Any, info: str = "") -> Any:'
new = 'def {family.function}({family.record_arg}, info: str = "") -> Any:'

if old not in text:
    raise SystemExit("the signature line was not found; it may already be patched")
PATH.write_text(text.replace(old, new), encoding="utf-8")
print("patched the accessor signature")
