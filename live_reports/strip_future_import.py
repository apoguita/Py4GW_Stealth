import pathlib
for name in ("item_enums", "model_enums"):
    p = pathlib.Path("py4gw/enums_src") / (name + ".py")
    data = p.read_bytes()
    for variant in (b"from __future__ import annotations\r\n", b"from __future__ import annotations\n"):
        if variant in data:
            data = data.replace(variant, b"", 1)
            break
    p.write_bytes(data)
    print(name, "future-import removed,", len(data.splitlines()), "lines")
