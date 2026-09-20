# First Design: The Win32 Process Class

The naming and general Python rules for this project are recorded in the
[programming style guide](STYLE.md). That guide is part of this design: new
code should follow it unless an external API requires a different spelling.

The project is a normal editable Python package. `pyproject.toml` is the only
package-configuration file required at the project root. It includes the
`py4gw` package without copying it or changing import statements in scripts.

## What we are building now

The overall purpose of Stealth is to recreate selected Py4GW Reforged
capabilities from outside `Gw.exe`, without an injected DLL or executable
payload. Reforged is an in-game Python automation and scripting library: its
launcher injects `Py4GW.dll`, which embeds Python and provides `Py*` bindings,
shared-memory game state, widgets, hooks, and higher-level automation helpers.
The current process-discovery class is only the first small capability in that
larger direction.

The first library step is small:

1. ask Windows for the running process list;
2. find processes named `Gw.exe`;
3. return their PID, name, and executable path when available; and
4. provide a simple method for displaying that list.

This step does not scan process memory. It does not change a process, inject
anything, run code in a process, or know anything about Guild Wars data. A
`Gw.exe` result is a candidate found by filename.

## Code layout

```text
py4gw/
  __init__.py
  win32/
    __init__.py     package export
    win32.py         Win32 class
tests/
  test_win32.py       automated Win32 behavior tests
  nicegui_probe.py    manual NiceGUI native-window check
```

There is one project class for this step: `Win32`.

The class owns:

- the Windows API declarations;
- process-list enumeration;
- `Gw.exe` matching;
- executable-path lookup;
- Windows error reporting;
- native handle cleanup; and
- simple text formatting.

There are no separate process model, error, scanner, presenter, or API-wrapper
classes yet. We will add another class only when the need is clear and the
design is agreed first.

## Public methods

### `Win32.list_processes()`

Returns a list like:

```python
[
    {"pid": 1234, "name": "Gw.exe"},
    {"pid": 5678, "name": "explorer.exe"},
]
```

This is a snapshot. A process can exit after the list is returned.

### `Win32.find_guild_wars()`

Returns every case-insensitive `Gw.exe` match:

```python
[
    {
        "pid": 1234,
        "name": "Gw.exe",
        "path": r"C:\Games\Guild Wars\Gw.exe",
        "path_error": None,
    }
]
```

If Windows does not allow the path lookup, the process remains in the result,
with `path` set to `None` and the Windows error number in `path_error`.

### `Win32.format_processes(processes)`

Returns a readable table for a console or log. It is only presentation; callers
should keep using the dictionaries returned by `find_guild_wars()` as data.

## Rules for this class

- Keep all Windows-specific work inside `Win32`.
- Keep error handling inside `Win32` and preserve the Windows error number.
- Request only query access needed to read an executable path.
- Close every native handle in the same method that opened it.
- Enumerate all processes and return all matches; never silently choose one.
- Match `Gw.exe` by filename only. Do not add window-title, module, signature,
  character-name, or memory rules to this step.
- Do not keep process handles open after a method returns.
- Keep methods short enough that a reader can follow the Windows operation from
  start to finish.
- Document each public method in plain language, including what it returns and
  what can fail.

## Why this is different from the earlier version

The earlier version split this small task across several custom classes. That
made the first step harder to read and harder to control. The current design
keeps the complete Win32 process-discovery behavior in one class so we can
understand and verify it before deciding whether another abstraction is needed.

GwAu3 was useful evidence for the initial `ProcessList("gw.exe")` idea, but its
later character-name scanning and broad process access are intentionally not
part of this class yet.

## Verification

- The unit tests exercise filename matching, empty display output, and a real
  read-only process-list call.
- A host integration run completed with no `Gw.exe` process currently running.
- No target process memory was read or modified.
- A user-provided live run found PID `39212` at `F:\GW\GW1\Gw.exe` with the
  client open, and no candidates after the client was closed.

After installing once from the project root with `python -m pip install -e .`,
any script can import the library from any working directory:

```python
from py4gw import Win32
```

Run the tests as modules from the project root:

```text
python -m unittest discover -s tests -v
```

For a zero-setup launch, use the project batch launcher. It supplies the
project root to Python externally; no test or library file needs an
import-path workaround. From the project root:

```text
py4gw.bat /tests/test_win32.py
```

From inside the `tests` directory:

```text
..\py4gw.bat /tests/test_win32.py
```

The first argument is the project-relative script path. Any arguments after it
through the ninth batch argument are passed to that script.
