# Current Design Contract

The naming and general Python rules for this project are recorded in the
[programming style guide](STYLE.md). New code follows that guide unless an
external API requires a different spelling.

The project is a normal editable Python package. `pyproject.toml` is the
package-configuration file at the project root. It includes the `py4gw`
package and declares NiceGUI's native extra as a runtime dependency.

## Current architecture

```text
main.py
  MainWindow
    NiceGUI native window
      Win32 process-test tab
        py4gw.Win32
          documented Windows APIs

py4gw/
  __init__.py
  win32/
    __init__.py
    win32.py
```

The library owns process behavior. The root UI presents and exercises that
behavior. The UI must not become a second implementation of Windows process
handling.

## Current capability

The first library capability is deliberately small:

1. ask Windows for the running process list;
2. find processes named `Gw.exe`, case-insensitively;
3. return each matching process's PID, executable name, and path when
   available; and
4. provide structured records that a caller or the main UI can display.

This does not scan process memory. It does not change a process, inject
anything, run code in a process, or interpret Guild Wars data. A `Gw.exe`
result is a candidate found by filename.

## The `Win32` class

There is one project class for the current process capability: `Win32`.

The class owns:

- the Windows API declarations;
- process-list enumeration;
- `Gw.exe` matching;
- executable-path lookup;
- Windows error reporting;
- native handle cleanup; and
- simple text formatting for console callers.

There are no separate process-model, error, scanner, presenter, or API-wrapper
classes for this first slice. Another class requires a clear responsibility
and a design update first.

### Public methods

#### `Win32.list_processes()`

Returns a current, PID-sorted snapshot:

```python
[
    {"pid": 1234, "name": "Gw.exe"},
    {"pid": 5678, "name": "explorer.exe"},
]
```

A process can exit after the snapshot is returned.

#### `Win32.find_guild_wars()`

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

#### `Win32.format_processes(processes)`

Returns a readable table for a console or log. It is presentation only;
callers should keep using the structured dictionaries as data.

## Main UI contract

`main.py` contains the `MainWindow` class and is the current test surface. It
is intentionally a root-level script so it can be launched directly:

```text
python main.py
```

The first tab is named `Win32 process test` and provides:

- `List all processes`, which calls `Win32.list_processes()`;
- `Find Gw.exe`, which calls `Win32.find_guild_wars()`; and
- a table showing PID, executable name, and path.

The UI catches `OSError` from the library and displays the diagnostic message.
It does not open persistent process handles, read memory, write memory, or
apply target-specific rules.

NiceGUI is a presentation dependency, not part of the Win32 library API. UI
callbacks may call public `Win32` methods and format returned records for
display. They must not contain `ctypes` declarations, Windows handle
management, memory operations, or Guild Wars signatures.

The separate `tests/nicegui_probe.py` script remains a small manual dependency
check. It is not the main application and does not replace the root UI.

## Implementation rules

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
- Keep UI state in `MainWindow`; do not add UI state to `Win32`.
- Add a UI control only when the corresponding library behavior already has a
  documented contract.

## Verification contract

Run the focused process tests directly from the project root or from the
`tests` directory:

```text
python tests\test_win32.py
```

Run the manual NiceGUI dependency probe when the UI dependency or environment
changes:

```text
python tests\nicegui_probe.py
```

Run the main test surface with:

```text
python main.py
```

Run static type checking from the project root:

```text
pyright
```

`pyrightconfig.json` checks `main.py`, `py4gw/`, and `tests/`, while excluding
the local research checkouts under `external/`. Pyright and Pylance must use
the same interpreter where the project dependencies are installed.

## Evidence and boundary

The current implementation is pure external and read-only. It does not read
target memory or modify any process. A `Gw.exe` result is not proof of a
supported Guild Wars build.

The user-provided live observation recorded in `RESEARCH.md` found PID `39212`
at `F:\GW\GW1\Gw.exe` with the client open and no candidates after the client
was closed. The build/version and exact timestamp were not recorded.

GwAu3 remains comparative research. Its later character-name scanning,
remote payloads, and broad process access are not part of this class.
