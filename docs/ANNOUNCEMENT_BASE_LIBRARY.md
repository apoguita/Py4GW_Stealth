Py4GW Stealth — the base library is done.

It's a mini Py4GW (Reforged): the base library is ported and live-verified, except it runs outside the
game — no injected DLL. It reaches all in-game data and all in-game functions, and it acts like the
real client does instead of faking packets.

Barebones on purpose, the way GWA2 was.

Next: a GWA3 compatibility class so migrating here is easy, and an AutoIt bridge to interface Stealth
and AutoIt.
