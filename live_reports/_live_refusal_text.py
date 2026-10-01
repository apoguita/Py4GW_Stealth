"""Print the refusal this project gives when another runtime already holds the four shared entries.

Elevated, one connect attempt, nothing written: the client is expected to report the address that carries
the other runtime's entry jump and where it lands. Companion to ``tests/test_live_coexistence.py``, which
asserts the same text; this one exists so the exact message can be quoted in the record.

Usage: python live_reports/_live_refusal_text.py
"""

from __future__ import annotations

import py4gw
from py4gw.win32 import Win32


def main() -> int:
    clients = Win32().find_guild_wars()
    if not clients:
        print("no Guild Wars client is running")
        return 1
    pid = int(clients[0]["pid"])
    print(f"pid {pid}: attempting a capability-layer connection (this writes nothing if it refuses)")
    try:
        py4gw.connect(pid)
    except BaseException as error:  # noqa: BLE001 - the message is the subject
        print(f"\n{type(error).__name__}:\n{error}")
        return 0
    finally:
        py4gw.disconnect()
    print("\nconnected: the entries were not held by another runtime on this attempt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
