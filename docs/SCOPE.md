# Project Scope

## Purpose

Py4GW Stealth is the external counterpart research project for Py4GW Reforged.
Py4GW Reforged runs Python inside Guild Wars through the injected
`Py4GW.dll`. Stealth investigates how selected Reforged capabilities can be
recreated from an external Python process instead.

This is capability-by-capability work. Stealth is not a complete replacement
for Py4GW Reforged, and no feature is assumed to be externally possible until
its design and evidence are clear.

## Current deliverable

The first deliverable has two deliberately small parts:

1. a project-owned `py4gw` package with a `Win32` class for read-only Windows
   process discovery; and
2. a root-level `main.py` NiceGUI window for exercising that class.

The UI is not a second process library. It is a presentation and testing
surface over the package. The Windows behavior stays inside `Win32`.

## In scope

- Python code running outside `Gw.exe`.
- Read-only Windows process enumeration.
- Case-insensitive discovery of processes named `Gw.exe`.
- Best-effort executable-path reporting with preserved Windows errors.
- A small native NiceGUI window for testing the current library behavior.
- Tests and documentation that explain each capability.
- Small project-owned wrappers around documented Windows APIs.

## Current capability

The current `py4gw.Win32` class can:

- list running Windows processes;
- find every process whose executable filename is `Gw.exe`; and
- report its PID and executable path when Windows allows that lookup.

The root UI currently exposes these operations in the `Win32 process test` tab:

- `List all processes` displays the current process snapshot; and
- `Find Gw.exe` displays the current Guild Wars candidates.

This identifies process candidates by filename. It does not verify a Guild
Wars build, read game state, or scan process memory.

## NiceGUI contract

NiceGUI is used only as the presentation layer for the current test window.
The native window is started with `ui.run(native=True)` and uses pywebview
underneath. UI callbacks may call public `Win32` methods and display their
results, but they must not contain Windows API declarations, process-handle
management, memory operations, or Guild Wars target assumptions.

The UI must remain understandable without knowing NiceGUI internals. New tabs
or controls should be added only for a capability that already has a library
method and a documented contract.

## Out of scope for the current capability

The current implementation does not:

- read or write Guild Wars memory;
- inject a DLL, payload, executable code, or patch;
- create a remote thread or hook a game function;
- reproduce Py4GW `Py*` bindings, widgets, or automation helpers;
- select a client by character, map, or memory signature; or
- promise compatibility with every Reforged feature.

Any expansion beyond process discovery must be documented and designed before
implementation.

## Terminology

`Pure external` means that the controller runs outside `Gw.exe` and does not
place executable code or patches in it. Process-memory reads and writes would
still be external operations, but they are not part of the current capability.

`External host` means that the primary logic runs outside `Gw.exe`. It does not,
by itself, prove that the game process is unmodified.

`Payload injection` means that an external program writes executable code or a
code patch into `Gw.exe` without loading a conventional DLL. It is still
injection.

`DLL injection` means that an in-process DLL owns a runtime. Current Py4GW
Reforged uses this model.

## Project rules

- Keep the public library API small and explicitly typed.
- Keep generic Windows mechanics separate from Guild Wars-specific knowledge.
- Keep all project code compatible with the checked-in `pyrightconfig.json`.
- Run Pyright with the same interpreter in which the project dependencies are
  installed.
- Record capability decisions and live observations in the documentation.
