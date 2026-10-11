"""Scratch: run the ported weapon-set analysis over the live mod bytes the probe read.

The bytes are from `tests/live_reports/gwa3_inventory.log` (pid 19696, 2026-10-10): the four weapon
sets' real item records. This prints what `UAI_FindAndSaveModFromMemory` finds in them, so the offline
test can assert the same numbers.
"""

from __future__ import annotations

import sys
from unittest import mock

sys.path.insert(0, r"C:\Users\Apo\Py4GW_Stealth")

from py4gw.gwa3 import constants as c  # noqa: E402
from py4gw.gwa3 import uai_const, uai_weaponsets  # noqa: E402

# From the probe: (set index, slot, item id, item type, mod hex)
LIVE = [
    (0, "weapon", 6096, 2, "091298270002482684000824080130250005B824260208244D0430250506A82868010824D00232250F00A822061CA8A7007898A4000000C0"),
    (1, "weapon", 6096, 2, "091298270002482684000824080130250005B824260208244D0430250506A82868010824D00232250F00A822061CA8A7007898A4000000C0"),
    (1, "offhand", 3813, 24, "091198270200A820002D88230810B8A7000000C0"),
    (2, "weapon", 122, 5, "00011826091998270001B8240F0038220A0018204801082490023025E1016824CE0008249D013025070058210F1CA8A7000000C0"),
    (3, "weapon", 94, 2, "091298270002B8240F327822A30008244601302501001825460130250100C820D9000824B3013025001E4823061CA8A7007898A4000000C0"),
    (3, "offhand", 3813, 24, "091198270200A820002D88230810B8A7000000C0"),
]

_NAMES = {
    c.GC_UAI_WEAPONSET_WeaponType: "WeaponType",
    c.GC_UAI_WEAPONSET_WeaponId: "WeaponId",
    c.GC_UAI_WEAPONSET_OffhandType: "OffhandType",
    c.GC_UAI_WEAPONSET_OffhandId: "OffhandId",
    c.GC_UAI_WEAPONSET_MaxHP: "MaxHP",
    c.GC_UAI_WEAPONSET_MaxEnergy: "MaxEnergy",
    c.GC_UAI_WEAPONSET_OffensiveScore: "OffensiveScore",
    c.GC_UAI_WEAPONSET_DefensiveScore: "DefensiveScore",
    c.GC_UAI_WEAPONSET_CastingScore: "CastingScore",
    c.GC_UAI_WEAPONSET_EnchantScore: "EnchantScore",
    c.GC_UAI_WEAPONSET_IsRanged: "IsRanged",
    c.GC_UAI_WEAPONSET_HasShield: "HasShield",
    c.GC_UAI_WEAPONSET_HasVampiric: "HasVampiric",
    c.GC_UAI_WEAPONSET_HasZealous: "HasZealous",
}


def main() -> int:
    for set_index, slot, item_id, item_type, mod_hex in LIVE:
        mods = {item_id: "0x" + mod_hex}
        info = {}
        for index, which, ident, kind, _hex in LIVE:
            if index == set_index and which == slot:
                info[f"WeaponSet{index}{'Weapon' if which == 'weapon' else 'Offhand'}Ptr"] = ident
        with mock.patch.object(
            uai_weaponsets, "Item_GetInventoryInfo", lambda key: info.get(key)
        ), mock.patch.object(
            uai_weaponsets,
            "Item_GetItemInfoByPtr",
            lambda record, field: record if field == "ItemID" else item_type,
        ), mock.patch.object(
            uai_weaponsets, "Item_GetModStruct", lambda key: mods.get(int(key), "")
        ):
            for row in uai_const.g_a2D_WeaponSets:
                row[:] = [0] * 14
            uai_weaponsets.UAI_SaveWeaponSetFromMemory(set_index + 1)

        row = uai_const.g_a2D_WeaponSets[set_index]
        print(f"--- set {set_index + 1} {slot}: item {item_id}, type {item_type} ---")
        print("   mods weapon:", [m for m in uai_const.g_as3_Weapon_Mods[set_index][0] if m])
        print("   mods offhand:", [m for m in uai_const.g_as3_Weapon_Mods[set_index][1] if m])
        print(
            "   "
            + ", ".join(
                f"{_NAMES[i]}={row[i]}" for i in sorted(_NAMES) if row[i]
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
