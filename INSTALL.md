# Py4GW Stealth

## What this project is

Py4GW Stealth is an external-first Windows/Python research project for
understanding what can be observed from a Guild Wars client without placing a
runtime inside the game process.

The current implementation is intentionally small. It provides a `py4gw`
Python package with a `Win32` class that can:

- list running Windows processes;
- find every process whose executable name is `Gw.exe`; and
- report each matching process's PID and executable path when Windows allows
  that lookup.

This is read-only process discovery. The current package does not read target
memory, write to a process, inject code, create remote threads, install hooks,
or automate Guild Wars.

## Requirements

- Windows
- Python 3.13 32-bit for the current x86-oriented research setup

Python 3.12 or another supported Python version may run the current process
discovery code, but the controller and target should match bitness before any
future memory work is considered.

Check the active interpreter with:

```text
python -c "import struct,sys; print(sys.executable); print(struct.calcsize('P') * 8)"
```

## Installation

From the project directory, install the package in editable mode:

```text
python -m pip install -e .
```

Editable installation means Python uses the files in this working directory.
After changing the code, there is no package rebuild step.

## Using the library

Any Python script can import the package after installation:

```python
from py4gw import Win32

win32 = Win32()
processes = win32.find_guild_wars()
print(win32.format_processes(processes))
```

Scripts do not need to be placed in the project root. They may live in a
separate `scripts/` directory or another location, as long as they use the
same Python environment where the editable package was installed.

## Project layout

```text
py4gw/          The Python package
tests/          Automated tests for the current package behavior
docs/           Design and programming-style rules
external/       Local research checkouts; intentionally excluded from Git
```

## Research boundary

The package currently identifies `Gw.exe` candidates by executable filename.
That is not proof of a particular game build and does not validate any Guild
Wars memory layout. New capabilities must be designed and documented before
they are added.
