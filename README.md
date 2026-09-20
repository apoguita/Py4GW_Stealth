# Py4GW Stealth

Py4GW Stealth is an external Python library for recreating selected Py4GW
Reforged capabilities without injecting a Python runtime or executable
payload into the Guild Wars process.

The project is being developed one capability at a time. The current capability
is read-only discovery of running `Gw.exe` processes, with a small NiceGUI
window for exercising that capability.

## Install

From the project directory:

```text
python -m pip install -e .
```

This installs the package and its Python dependencies, including NiceGUI's
native-window support. The editable install keeps Python connected to the
working source tree.

Run scripts through the selected Python interpreter:

```text
python path\to\script.py
```

This is preferred over typing `script.py` by itself, because Windows may use a
different interpreter for the `.py` file association.

## Example

```python
from py4gw import Win32

win32 = Win32()
print(win32.format_processes(win32.find_guild_wars()))
```

## Main UI

Run the current test surface from the project directory:

```text
python main.py
```

The first tab exercises the read-only Win32 process-discovery methods.

The UI is a presentation and testing surface. The `Win32` class remains the
owner of all Windows process operations.

## Documentation

- [Scope](docs/SCOPE.md) — what the project is and is not
- [Installation guide](INSTALL.md) — setup and usage details
- [Design contract](docs/DESIGN.md) — current implementation rules
- [Programming style](docs/STYLE.md) — naming and coding conventions
- [Research record](docs/RESEARCH.md) — detailed source analysis and history

## Current boundary

The current library only performs read-only process discovery. It does not
read target memory, write to a process, inject code, create remote threads, or
install hooks.
