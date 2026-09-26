"""Ported ``py4gwcorelib_src`` modules.

Reforged keeps its library-internal helpers in ``Py4GWCoreLib/py4gwcorelib_src/`` — ``Utils.py``,
``Color.py``, ``Console.py``, ``ActionQueue.py``, ``FrameCache.py``, ``Settings.py`` and the rest.
This package is that directory's home here, with the same relative path and the file names in this
project's ``snake_case`` (``docs/STYLE.md``: *Module/file | lowercase ``snake_case``*), the same
rule ``py4gw/enums_src/`` follows for ``Py4GWCoreLib/enums_src/``. Every name *inside* a module is
the source's — the classes, the members and the constants keep their spelling, because a ported
script imports them by that name.
"""
