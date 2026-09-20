# Project Scope

## Purpose

Py4GW Stealth is the external counterpart research project for Py4GW Reforged.
Py4GW Reforged runs Python inside Guild Wars through the injected `Py4GW.dll`.
Stealth investigates how selected Reforged capabilities can be recreated from
an external Python process instead.

This is capability-by-capability work. Stealth is not currently a complete
replacement for Py4GW Reforged, and no feature is assumed to be externally
possible until it has its own design and evidence.

## In scope

- Python code running outside `Gw.exe`.
- Small project-owned Windows interfaces.
- Read-only process discovery and, when explicitly designed, other external
  observations.
- Clear separation between generic Windows behavior and Guild Wars knowledge.
- Tests and documentation that explain each capability.

## Current capability

The current `py4gw.Win32` class can:

- list running Windows processes;
- find every process whose executable filename is `Gw.exe`; and
- report its PID and executable path when Windows allows that lookup.

This identifies process candidates by filename. It does not verify a Guild
Wars build, read game state, or scan process memory.

## Out of scope for the current capability

The current implementation does not:

- read or write Guild Wars memory;
- inject a DLL, payload, executable code, or patch;
- create a remote thread or hook a game function;
- reproduce Py4GW `Py*` bindings, widgets, or automation helpers; or
- promise compatibility with every Reforged feature.

Any expansion beyond process discovery must be documented and designed before
implementation.

## Terminology

`Pure external` means that the controller runs outside `Gw.exe` and does not
place executable code or patches in it. A future remote payload would still be
injection, even if the controller itself remained external.
