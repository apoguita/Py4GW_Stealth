import struct, sys, collections, re
sys.path.insert(0, r"C:\Users\Apo\Py4GW_Stealth\tools")
from pe_image import PeImage
img = PeImage(r"F:\GW\GW1\Gw.exe")
t = img.section(".text"); code = img.read_rva(t.virtual_address, t.raw_size); base = img.image_base + t.virtual_address
SENDERS = (0x006345F0, 0x0064D190)
used = collections.Counter()
for i in range(len(code) - 5):
    if code[i] != 0xE8: continue
    if base + i + 5 + struct.unpack_from("<i", code, i+1)[0] not in SENDERS: continue
    for j in range(i-1, max(0, i-0x40), -1):
        if code[j] == 0x68:
            imm = struct.unpack_from("<I", code, j+1)[0]
            if 0x10000000 <= imm < 0x10000200 or 0x30000000 <= imm < 0x30000040:
                used[imm] += 1; break
ids = sorted(used)
print("distinct ids pushed:", len(ids), " range %#x .. %#x" % (ids[0], ids[-1]))
print("\n=== contiguous-id map 0x10000100 .. 0x100001E0  ('#'=pushed, '.'=never pushed) ===")
for start in range(0x10000100, 0x100001E0, 16):
    row = "".join("#" if (start+k) in used else "." for k in range(16))
    print("  %#010x  %s" % (start, row))
print("\n=== the travel-adjacent neighbourhood, one per line ===")
for v in range(0x1000017C, 0x100001A0):
    print("   %#010x %s" % (v, "PUSHED x%d" % used[v] if v in used else "-"))
