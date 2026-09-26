"""Ported ``enums_src`` modules.

Reforged keeps its enums in ``Py4GWCoreLib/enums_src/``, one file per area (``GameData_enums.py``,
``Map_enums.py``, ``UI_enums.py``, …). This package is that directory's home here, with the same
relative path and the file names in this project's ``snake_case`` (``docs/STYLE.md``: *Module/file |
lowercase ``snake_case``*), while every name *inside* a module is the source's — the classes, the
name tables and the members keep their spelling, because a ported script imports them by that name.
"""
