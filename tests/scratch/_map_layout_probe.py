"""Read-only MapContext / CharContext layout prober for a running Guild Wars client.

WHAT IT DOES
------------
Opens the client READ-ONLY (PROCESS_VM_READ via the project's own `ProcessMemoryReader`) and walks
the accessor chain the DLL itself uses, taken verbatim from the source:

    g_base_ptr                       resolve "context.base_ptr"      context.cpp:64
      -> *(uintptr_t**)g_base_ptr    the context pointer array       context_methods.cpp:72
      -> base_context[0x6]           GameContext*                    context_methods.cpp:73
      -> +0x14                       MapContext*                     game.h:29
      -> +0x44                       CharContext*                    game.h:41

Then it reports what is ACTUALLY at each offset the headers CLAIM, so a layout shift introduced by
the 2026-09-30 client update shows up as a measurement instead of a guess.

THREE QUESTIONS IT ANSWERS
--------------------------
1. PATHING. `Map::GetPathingMap()` walks `MapContext->sub1->sub2->pmaps`
   (map_methods.cpp:185-191), with `sub1` declared at MapContext+0x74. The probe tests that
   declared shape at EVERY dword offset in MapContext and reports every offset that satisfies it:
   `X[0]` -> a plausible `sub2`, and `sub2+0x18` -> a `GWArray<PathingMap>` with a sane
   buffer/capacity/size. If the only hit is 0x74 the header is right; if the hit is elsewhere, that
   is the real offset and every field after it has shifted.
2. MAP ID. `Map::GetMapID()` reads `CharContext::current_map_id` (map_methods.cpp:59-62); the
   merged fix moved it 0x234 -> 0x238. Reforged's Python layer instead reads `MapContext+0x8C` -
   a field Native's `map.h` does not even declare (it covers 0x88 with an opaque `h0088[42]`).
   The probe prints both candidates so the live value decides.
3. `CharContext` SIZE. The update grew it 0x448 -> 0x458. The probe locates the account email
   EMPIRICALLY by scanning for a wide string containing '@', and reports which offset it lands at:
   0x3C8 means the old layout, 0x3D8 means the merged fix is correct. Same for `progress_bar`
   (0x350 vs 0x360) by pointer plausibility.

It writes nothing, installs nothing, hooks nothing, and calls no client function.

USAGE (needs an elevated shell - see tests/scratch\1_elev_map_probe.cmd)
    python tests/scratch\1_map_layout_probe.py [--pid N] [--out tests/live_reports/map_layout_probe.json]
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from py4gw import ProcessMemoryReader, RemoteScanner, Win32  # noqa: E402
from py4gw.scanner.patterns import PatternCatalog  # noqa: E402

GAME_CONTEXT_INDEX = 0x6          # context_methods.cpp:73
GAME_CONTEXT_MAP_OFFSET = 0x14    # game.h:29
GAME_CONTEXT_CHAR_OFFSET = 0x44   # game.h:41

MAP_CONTEXT_DUMP = 0x180

#: Where the headers say these live. The probe reports what is actually there.
DECLARED_MAP = {
    "map_boundaries": 0x00, "h0014": 0x14, "spawns1": 0x2C, "spawns2": 0x3C,
    "spawns3": 0x4C, "h005C": 0x5C, "sub1": 0x74, "props": 0x7C,
    "h0080": 0x80, "terrain": 0x84, "zones": 0x130,
}
REFORGED_MAP = {"path_ptr": 0x74, "path_engine_ptr": 0x78, "props_ptr": 0x7C, "map_id": 0x8C}


def u32(raw: bytes, off: int) -> int:
    return int(struct.unpack_from("<I", raw, off)[0])


def f32(raw: bytes, off: int) -> float:
    return float(struct.unpack_from("<f", raw, off)[0])


def plausible(v: int) -> bool:
    """A 32-bit user-space pointer that is not obviously garbage."""

    return 0x00010000 <= v < 0x7FFE0000


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int, default=0)
    ap.add_argument("--out", default=str(ROOT / "tests/live_reports" / "map_layout_probe.json"))
    args = ap.parse_args(argv)

    win32 = Win32()
    if not win32.is_elevated():
        print("REFUSING: needs an elevated shell (PROCESS_VM_READ is denied without it).")
        return 3

    pid = args.pid
    if not pid:
        found = win32.find_guild_wars()
        if not found:
            print("no Gw.exe process found.")
            return 2
        pid = int(found[0]["pid"])
    module = win32.get_main_module(pid)
    base, size = int(module["base_address"]), int(module["size"])
    report: dict[str, Any] = {"pid": pid, "module": {"base": hex(base), "size": hex(size)}}
    print(f"pid {pid}  module {base:#010x} + {size:#x}")

    with ProcessMemoryReader(win32, pid) as reader:
        scanner = RemoteScanner(reader, module_base=base, module_size=size)
        scanner.initialize()
        catalog = PatternCatalog.from_directory(ROOT / "offsets")

        res = catalog.resolve("context.base_ptr", scanner)
        if not res.ok or not res.value:
            print(f"context.base_ptr did not resolve: {res.message}")
            Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
            return 1
        g_base_ptr = int(res.value)
        print(f"context.base_ptr (global address) -> {g_base_ptr:#010x}")

        base_context = u32(reader.read(g_base_ptr, 4), 0)
        print(f"  deref -> context pointer array    {base_context:#010x}")
        if not plausible(base_context):
            print("  the global does not hold a plausible pointer; client may be at character select.")
            Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
            return 1

        table = reader.read(base_context, 0x80)
        report["context_table"] = {
            "address": hex(base_context),
            "entries": {hex(i * 4): hex(u32(table, i * 4)) for i in range(0x20)},
        }
        print("\n=== context pointer array ===")
        for i in range(0x20):
            v = u32(table, i * 4)
            print(f"  [{i:#04x}] +{i*4:#05x}  {v:#010x}{'  <- plausible' if plausible(v) else ''}")

        game_context = u32(table, GAME_CONTEXT_INDEX * 4)
        print(f"\nGameContext = array[{GAME_CONTEXT_INDEX:#x}] = {game_context:#010x}")
        if not plausible(game_context):
            Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
            return 1

        gc = reader.read(game_context, 0x5C)
        map_ctx = u32(gc, GAME_CONTEXT_MAP_OFFSET)
        char_ctx = u32(gc, GAME_CONTEXT_CHAR_OFFSET)
        report["game_context"] = {
            "address": hex(game_context),
            "map_at_0x14": hex(map_ctx),
            "character_at_0x44": hex(char_ctx),
        }
        print(f"  +0x14 MapContext  = {map_ctx:#010x}{'  <- plausible' if plausible(map_ctx) else '  <- NOT a pointer'}")
        print(f"  +0x44 CharContext = {char_ctx:#010x}{'  <- plausible' if plausible(char_ctx) else '  <- NOT a pointer'}")

        # ---------------- MapContext + pathing -------------------------------------------
        if plausible(map_ctx):
            raw = reader.read(map_ctx, MAP_CONTEXT_DUMP)
            report["map_context"] = {
                "address": hex(map_ctx),
                "declared_offsets": DECLARED_MAP,
                "reforged_view": REFORGED_MAP,
                "dwords": {hex(o): hex(u32(raw, o)) for o in range(0, MAP_CONTEXT_DUMP, 4)},
                "floats_first_0x20": [f32(raw, o) for o in range(0, 0x20, 4)],
            }
            print(f"\n=== MapContext @ {map_ctx:#010x} ===")
            print("  (f = same dword read as a float, to tell boundaries from pointers)")
            for o in range(0, MAP_CONTEXT_DUMP, 4):
                v = u32(raw, o)
                tags = []
                tags += [f"source:{k}" for k, off in DECLARED_MAP.items() if off == o]
                tags += [f"reforged:{k}" for k, off in REFORGED_MAP.items() if off == o]
                ptr = "  <- ptr" if plausible(v) else ""
                print(f"  +{o:#05x}  {v:#010x}  f={f32(raw, o): .5g}{ptr}{'   [' + ','.join(tags) + ']' if tags else ''}")

            # Test the declared pathing shape at EVERY offset: sub1[0] -> sub2, sub2+0x18 -> GWArray
            hits = []
            print("\n=== pathing shape (X[0] -> sub2, sub2+0x18 -> GWArray<PathingMap>) ===")
            for o in range(0, MAP_CONTEXT_DUMP, 4):
                sub1 = u32(raw, o)
                if not plausible(sub1):
                    continue
                try:
                    sub1_raw = reader.read(sub1, 0x24)
                except OSError:
                    continue
                sub2 = u32(sub1_raw, 0)
                if not plausible(sub2):
                    continue
                try:
                    sub2_raw = reader.read(sub2, 0x28)
                except OSError:
                    continue
                buf, cap, cnt = u32(sub2_raw, 0x18), u32(sub2_raw, 0x1C), u32(sub2_raw, 0x20)
                if not plausible(buf) or not (0 < cnt <= cap <= 0x100000):
                    continue
                hit = {
                    "map_context_offset": hex(o),
                    "sub1": hex(sub1), "sub2": hex(sub2),
                    "pmaps_buffer": hex(buf), "pmaps_capacity": cap, "pmaps_size": cnt,
                    "sub1_total_trapezoid_count": u32(sub1_raw, 0x14),
                    "is_declared_0x74": o == 0x74,
                }
                hits.append(hit)
                print(f"  HIT MapContext+{o:#05x} -> sub1 {sub1:#010x} -> sub2 {sub2:#010x} "
                      f"-> pmaps buf {buf:#010x} cap {cap} size {cnt} "
                      f"trapezoids {u32(sub1_raw, 0x14)}"
                      f"{'   (matches declared 0x74)' if o == 0x74 else '   *** SOURCE SAYS 0x74 ***'}")
            report["pathing_hits"] = hits
            if not hits:
                print("  NO hit at any offset: MapContext.sub1 is not a plain pointer here, or the "
                      "pathing sub-structure moved/reshaped.")

            # ---- go deeper: is the PathingMap RECORD itself still the declared shape? -------
            # MapContext.sub1/pmaps being right does not prove `PathingMap` is: if a field was
            # inserted inside it, `trapezoids`/`portals`/`root_node` move and every pathing read
            # breaks while the array header still looks perfect.
            primary = next((h for h in hits if h["is_declared_0x74"]), hits[0] if hits else None)
            if primary:
                pmaps_buf = int(primary["pmaps_buffer"], 16)
                print(f"\n=== PathingMap[0] @ {pmaps_buf:#010x}  (declared size 0x54) ===")
                try:
                    pm = reader.read(pmaps_buf, 0x54)
                except OSError as exc:
                    print(f"  unreadable: {exc}")
                    pm = None
                if pm is not None:
                    declared_pm = {
                        "zplane": 0x00, "trapezoid_count": 0x14, "trapezoids": 0x18,
                        "sink_node_count": 0x1C, "sink_nodes": 0x20, "x_node_count": 0x24,
                        "x_nodes": 0x28, "y_node_count": 0x2C, "y_nodes": 0x30,
                        "portal_count": 0x3C, "portals": 0x40, "root_node": 0x44,
                    }
                    pm_report = {}
                    for name, off in declared_pm.items():
                        v = u32(pm, off)
                        pm_report[name] = hex(v)
                        print(f"  +{off:#05x}  {v:#010x}  [{name}]")
                    report["pathing_map0"] = pm_report
                    print(f"  hex: {pm.hex(' ')}")

                    # The trapezoid record is the one that matters most: its floats must sit
                    # inside the map boundary box read from MapContext+0x04 (printed above).
                    trap_ptr = u32(pm, 0x18)
                    count = u32(pm, 0x14)
                    if plausible(trap_ptr) and 0 < count <= 0x100000:
                        print(f"\n=== PathingTrapezoid[0..3] @ {trap_ptr:#010x}  (declared size 0x30) ===")
                        traps = []
                        for i in range(4):
                            a = trap_ptr + i * 0x30
                            try:
                                tr = reader.read(a, 0x30)
                            except OSError:
                                break
                            xs = [f32(tr, 0x18), f32(tr, 0x1C), f32(tr, 0x24), f32(tr, 0x28)]
                            ys = [f32(tr, 0x20), f32(tr, 0x2C)]
                            traps.append({
                                "index": i, "id": u32(tr, 0x00),
                                "adjacent": [hex(u32(tr, 0x04 + k * 4)) for k in range(4)],
                                "portal_left": struct.unpack_from("<H", tr, 0x14)[0],
                                "portal_right": struct.unpack_from("<H", tr, 0x16)[0],
                                "XTL": xs[0], "XTR": xs[1], "YT": ys[0],
                                "XBL": xs[2], "XBR": xs[3], "YB": ys[1],
                            })
                            print(f"  [{i}] id={u32(tr,0x00)} portalL={struct.unpack_from('<H',tr,0x14)[0]} "
                                  f"portalR={struct.unpack_from('<H',tr,0x16)[0]}")
                            print(f"      XTL={xs[0]:.2f} XTR={xs[1]:.2f} YT={ys[0]:.2f} "
                                  f"XBL={xs[2]:.2f} XBR={xs[3]:.2f} YB={ys[1]:.2f}")
                            print(f"      adjacent={[hex(u32(tr,0x04+k*4)) for k in range(4)]}")
                            print(f"      hex: {tr.hex(' ')}")
                        report["pathing_trapezoids"] = traps
                        # A sanity verdict the caller does not have to eyeball.
                        if traps:
                            bx = (f32(raw, 0x04), f32(raw, 0x0C))
                            by = (f32(raw, 0x08), f32(raw, 0x10))
                            ok = all(
                                min(bx) - 1 <= t["XTL"] <= max(bx) + 1
                                and min(bx) - 1 <= t["XTR"] <= max(bx) + 1
                                and min(bx) - 1 <= t["XBL"] <= max(bx) + 1
                                and min(bx) - 1 <= t["XBR"] <= max(bx) + 1
                                and min(by) - 1 <= t["YT"] <= max(by) + 1
                                and min(by) - 1 <= t["YB"] <= max(by) + 1
                                for t in traps
                            )
                            report["trapezoid_inside_map_boundaries"] = ok
                            print(f"\n  VERDICT: trapezoid coords inside map_boundaries "
                                  f"x{[min(bx), max(bx)]} y{[min(by), max(by)]}: {ok}")
                            print("  (False means the PathingTrapezoid record shape is WRONG on this "
                                  "build - that is what breaks pathing while the array header still "
                                  "looks sane.)")

        # ---------------- CharContext: settle 0x448 vs 0x458 ------------------------------
        if plausible(char_ctx):
            CCHAR = 0x458
            raw = reader.read(char_ctx, CCHAR)
            # Locate the wide account email empirically: a run containing '@' with text around it.
            email_off = None
            for o in range(0, CCHAR - 4, 2):
                if u32(raw, o) == 0x00000040 and o >= 4:  # '@' as a leading wchar is unlikely
                    pass
                ch = struct.unpack_from("<H", raw, o)[0]
                if ch != 0x40:
                    continue
                # walk back to the run start
                s = o
                while s >= 2 and 0x20 <= struct.unpack_from("<H", raw, s - 2)[0] < 0x7F:
                    s -= 2
                run = []
                k = s
                while k + 2 <= CCHAR:
                    c = struct.unpack_from("<H", raw, k)[0]
                    if c == 0:
                        break
                    if not (0x20 <= c < 0x7F):
                        run = []
                        break
                    run.append(chr(c))
                    k += 2
                if len(run) >= 6 and "@" in "".join(run) and "." in "".join(run):
                    email_off = s
                    report.setdefault("char_context", {})["email_guess_offset"] = hex(s)
                    report["char_context"]["email_guess_text"] = "".join(run)
                    print(f"\n=== CharContext @ {char_ctx:#010x} ===")
                    print(f"  wide email-looking string at +{s:#05x}: {''.join(run)!r}")
                    break

            cc: dict[str, Any] = {
                "address": hex(char_ctx),
                "email_guess_offset": report.get("char_context", {}).get("email_guess_offset"),
                "district_number_at_0x228_OLD": u32(raw, 0x228),
                "district_number_at_0x22C_NEW": u32(raw, 0x22C),
                "language_at_0x22C_OLD": u32(raw, 0x22C),
                "language_at_0x230_NEW": u32(raw, 0x230),
                "current_map_id_at_0x234_OLD": u32(raw, 0x234),
                "current_map_id_at_0x238_NEW": u32(raw, 0x238),
                "observe_map_id_at_0x230_OLD": u32(raw, 0x230),
                "observe_map_id_at_0x234_NEW": u32(raw, 0x234),
                "progress_bar_at_0x350_OLD": hex(u32(raw, 0x350)),
                "progress_bar_at_0x360_NEW": hex(u32(raw, 0x360)),
            }
            report["char_context"] = {**report.get("char_context", {}), **cc}
            print(f"  district_number  0x228(old)={u32(raw,0x228):<8}   0x22C(new)={u32(raw,0x22C)}")
            print(f"  language         0x22C(old)={u32(raw,0x22C):<8}   0x230(new)={u32(raw,0x230)}")
            print(f"  observe_map_id   0x230(old)={u32(raw,0x230):<8}   0x234(new)={u32(raw,0x234)}")
            print(f"  current_map_id   0x234(old)={u32(raw,0x234):<8}   0x238(new)={u32(raw,0x238)}")
            print(f"  progress_bar     0x350(old)={u32(raw,0x350):#010x}  0x360(new)={u32(raw,0x360):#010x}")
            print("  (a MapID is a small number; the correct pair should be small and equal to the "
                  "map the client is actually in)")

            # Settle the TAIL of the struct: where does player_email really begin, and where is
            # progress_bar? PR#9 moved them to 0x360 and 0x3D8 (size 0x458); the email scan above
            # found a full address 8 bytes earlier, so dump the region as wide chars and the
            # pointer candidates as alignment-tested hex.
            print("\n  --- pointer candidates for progress_bar (a heap pointer is 4-byte aligned) ---")
            pb = {}
            for off in (0x350, 0x354, 0x358, 0x35C, 0x360, 0x364, 0x368):
                v = u32(raw, off)
                pb[hex(off)] = {"value": hex(v), "plausible": plausible(v), "aligned4": v % 4 == 0}
                print(f"    +{off:#05x} {v:#010x}  plausible={plausible(v)} aligned4={v % 4 == 0}")
            report["progress_bar_candidates"] = pb

            print("\n  --- wide-char view 0x390..0x460 ('.' = non-printable, '~' = 0x0000) ---")
            lines = {}
            for off in range(0x390, 0x460, 16):
                chars = []
                for k in range(off, min(off + 16, CCHAR), 2):
                    c = struct.unpack_from("<H", raw, k)[0]
                    chars.append("~" if c == 0 else (chr(c) if 0x20 <= c < 0x7F else "."))
                lines[hex(off)] = "".join(chars)
                print(f"    +{off:#05x}  {' '.join(chars)}")
            report["wide_view_0x390_0x460"] = lines

            # Where does the printable run that CONTAINS the address start, and what precedes it?
            print("\n  --- every printable wide run in 0x380..0x460 ---")
            runs = []
            k = 0x380
            while k < CCHAR:
                c = struct.unpack_from("<H", raw, k)[0]
                if 0x20 <= c < 0x7F:
                    s = k
                    buf = []
                    while k < CCHAR:
                        c = struct.unpack_from("<H", raw, k)[0]
                        if not (0x20 <= c < 0x7F):
                            break
                        buf.append(chr(c))
                        k += 2
                    if len(buf) >= 4:
                        runs.append({"offset": hex(s), "length": len(buf), "text": "".join(buf)})
                        print(f"    +{s:#05x} len={len(buf):<3} {''.join(buf)!r}")
                else:
                    k += 2
            report["printable_runs_0x380_0x460"] = runs

            # ---- PIN THE BASE -----------------------------------------------------------------
            # Everything above is relative to CharContext = GameContext+0x44, which the update may
            # also have moved. The struct declares two anchors that let the base be derived
            # independently: `player_name` is a wchar_t[0x14] at +0x74, and `map_id` is a MapID at
            # +0x198 that must agree with MapContext+0x8C (642 on this client). Find the name, and
            # the base falls out of (name_absolute - 0x74).
            print("\n  --- base anchors: declared +0x74 wchar_t player_name[0x14], +0x198 MapID ---")
            name_off = None
            head_runs = []
            k = 0
            while k < CCHAR:
                c = struct.unpack_from("<H", raw, k)[0]
                if 0x20 <= c < 0x7F:
                    s = k
                    buf = []
                    while k < CCHAR:
                        c = struct.unpack_from("<H", raw, k)[0]
                        if not (0x20 <= c < 0x7F):
                            break
                        buf.append(chr(c))
                        k += 2
                    if len(buf) >= 3:
                        head_runs.append({"offset": hex(s), "length": len(buf), "text": "".join(buf)})
                        print(f"    wchar run +{s:#05x} len={len(buf):<3} {''.join(buf)!r}")
                else:
                    k += 2
            report["char_context_wchar_runs"] = head_runs
            # A player name is alphabetic and sits before 0x200.
            for r in head_runs:
                off = int(r["offset"], 16)
                if off < 0x200 and r["length"] >= 3 and r["text"].isalpha():
                    name_off = off
                    break
            anchors = {
                "world_flags_0x190": u32(raw, 0x190),
                "token1_0x194": u32(raw, 0x194),
                "map_id_0x198": u32(raw, 0x198),
                "is_explorable_0x19C": u32(raw, 0x19C),
                "player_uuid_0x64": [u32(raw, 0x64 + i * 4) for i in range(4)],
            }
            report["char_context_anchors"] = anchors
            for k2, v in anchors.items():
                print(f"    +{k2} = {v:#010x}" if isinstance(v, int) else f"    +{k2} = {v}")
            if name_off is not None:
                print(f"\n  player_name found at +{name_off:#05x}; declared +0x74")
                print(f"  => derived CharContext base = 0x{char_ctx + name_off - 0x74:08X} "
                      f"(probe used 0x{char_ctx:08X}, delta {name_off - 0x74:+d} bytes)")
                report["derived_base_delta"] = name_off - 0x74
                print("  A non-zero delta means every CharContext offset above must be shifted by "
                      "that amount before it is applied to map.h.")
            else:
                print("  no alphabetic name run found below 0x200; base not pinned by name.")

    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
