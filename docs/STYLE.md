# Python Programming Style

This project uses a Python-first naming style. The goal is for code to read
naturally to a Python programmer while still preserving names that belong to a
Windows API or another external system.

## Naming rules

| Thing | Style | Example |
|---|---|---|
| Package | lowercase | `py4gw`, `win32` |
| Module/file | lowercase `snake_case` | `process_reader.py` |
| Class | `PascalCase` | `Win32`, `ProcessReader` |
| Private helper type | leading underscore + lowercase `snake_case` | `_process_entry` |
| Public method/function | lowercase `snake_case` | `find_guild_wars()` |
| Private method/function | leading underscore + `snake_case` | `_get_image_path()` |
| Instance/class attribute | lowercase `snake_case` | `self._kernel32` |
| Constant | `UPPER_SNAKE_CASE` | `_MAX_PATH_CHARS` |
| Local variable | lowercase `snake_case` | `error_code` |
| Boolean | a descriptive `is_`, `has_`, `can_`, or `should_` name | `is_running` |

`Win32` is an intentional class-name exception because it is the name of the
Windows API family. Product and API names such as `GwAu3`, `PID`, and
`Process32FirstW` keep their official spelling when they refer to the external
thing itself.

Public classes use `PascalCase`. Private helper types are an exception: they
use a leading underscore and lowercase `snake_case`, just like other private
names.

## Camel case

We do not use lower camel case (`findGuildWars`) for normal Python methods,
variables, or files. Python's standard library and tooling consistently use
`snake_case`, and following that convention makes the code easier to read and
search.

Camel-style names are preserved only at an external boundary, for example the
exact Win32 function name `Process32FirstW` or a field name required by a C
structure. The boundary code may contain that spelling; code calling the
boundary uses our `snake_case` names.

## Classes and responsibility

- A class should own one understandable area of behavior.
- Keep related operations together when that makes the first implementation
  easier to follow. Do not create a class merely to wrap one value or one
  function.
- Add another class only when it has a clear responsibility and the design
  document has been updated first.
- Keep object state explicit. Do not hide shared mutable state in module-level
  variables.

## Methods and data

- Use type hints on public methods and on important internal values.
- Prefer simple Python values (`str`, `int`, `bytes`, `list`, `dict`, and
  `None`) while the project is small. Introduce custom result objects only when
  a real need appears.
- Public methods should say what they return and what can fail in a docstring.
- Keep a method short enough that its main operation is visible without
  jumping across many helper classes.
- Use early returns for simple failure cases, but keep the normal path easy to
  read from top to bottom.

## Windows boundary code

- Keep `ctypes` declarations and native spelling inside the `Win32` class (or
  another explicitly approved Windows-boundary class).
- Declare argument and return types before calling a Windows function.
- Preserve the original Windows error number when reporting a failure.
- Close a native handle in the same method that opened it, using `try/finally`.
- Do not convert a Windows pointer or structure field to a host-sized Python
  interpretation without documenting the target architecture.

## Documentation and comments

- Write docstrings in plain language. Explain purpose, inputs, outputs, and
  important failure behavior.
- Comment why a non-obvious decision exists, not what an obvious line does.
- Keep design decisions in `docs/`, not only in comments or chat history.
- When behavior changes, update the relevant design document and tests in the
  same change.

## Formatting and verification

- Use four spaces for indentation and no tabs.
- Keep lines close to 88 characters where practical, without making a line
  harder to understand just to satisfy a number.
- Use one import per logical group: standard library, third-party packages,
  then project imports.
- Run the focused tests for the changed class before considering the change
  complete.
- Keep the first implementation small; do not add future features “because we
  will need them later.”
