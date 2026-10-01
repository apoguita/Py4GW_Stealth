import struct, sys, collections
sys.path.insert(0, r"C:\Users\Apo\Py4GW_Stealth\tools")
from pe_image import PeImage

img = PeImage(r"F:\GW\GW1\Gw.exe")
t = img.section(".text")
code = img.read_rva(t.virtual_address, t.raw_size)
base = img.image_base + t.virtual_address

# The two UI-message entry points the catalog resolves on this build.
SENDERS = {0x006345F0: "send_ui_message_func", 0x0064D190: "send_frame_ui_message_func"}

def scan(target, label):
    hits = collections.Counter()
    sites = []
    n = len(code)
    for i in range(n - 5):
        if code[i] != 0xE8:
            continue
        rel = struct.unpack_from("<i", code, i + 1)[0]
        dst = base + i + 5 + rel
        if dst != target:
            continue
        call_va = base + i
        # walk back for the argument pushes (push imm32 = 68 xx xx xx xx)
        for j in range(i - 1, max(0, i - 0x40), -1):
            if code[j] == 0x68:
                imm = struct.unpack_from("<I", code, j + 1)[0]
                if 0x10000000 <= imm < 0x10000200 or 0x30000000 <= imm < 0x30000040:
                    hits[imm] += 1
                    sites.append((call_va, imm))
                    break
    print("=== callers of %s @ %#010x : %d call site(s), %d distinct msg id(s) ==="
          % (label, target, len(sites), len(hits)))
    for imm in sorted(hits):
        print("   %#010x  x%d" % (imm, hits[imm]))
    return set(hits)

seen = set()
for target, label in SENDERS.items():
    seen |= scan(target, label)
    print()

print("=== ALL ui message ids the client pushes at those call sites ===")
for imm in sorted(seen):
    print("   %#010x" % imm)
