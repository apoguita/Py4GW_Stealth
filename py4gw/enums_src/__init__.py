"""Ported ``enums_src`` modules.

Reforged keeps its enums in ``Py4GWCoreLib/enums_src/``, one file per area (``GameData_enums.py``,
``Map_enums.py``, ``UI_enums.py``, …). This package is that directory's home here, with the same
relative path and the file names in this project's ``snake_case`` (``docs/STYLE.md``: *Module/file |
lowercase ``snake_case``*), while every name *inside* a module is the source's — the classes, the
name tables and the members keep their spelling, because a ported script imports them by that name.

**This package holds the constants and enums of both sources**, because that is where they are:

- the mirrors of Reforged's ``enums_src``, module for module (the thirteen ``*_enums.py`` files plus
  ``game_data_enums.py``); and
- ``skill_names.py``, the port of native's generated ``src/GW/skillbar/skill_names.cpp``, whose data
  is the members of ``GW::Constants::SkillID`` (``include/GW/common/constants/skills.h``) and whose
  four lookups are generated from the ``SkillID``, ``SkillType`` and ``Profession`` enums. The
  project owner's direction, 2026-09-26: enums, the hardcoded tables generated from them, and the
  handlers that read those tables belong together here — not loose in the package root, and not split
  across the modules that call them.

**A module here is the source file, not a summary of it.** Where the source's annotations are wrong,
the port keeps them wrong: ``quest_enums.get_quest_id`` is annotated ``-> int`` and returns ``None``
when a name is unknown, exactly as ``Quest_enums.py:1490`` does. `pyrightconfig.json` silences
``reportReturnType`` for this package for that reason, and the alternative — editing the source's
signature — is the kind of liberty the porting rules forbid.

**Not here yet:** ``Model_enums.py`` (its source does ``import PySkill``), ``Texture_enums.py``
(``import PySystem``), and ``Item_enums.py``/``Calendar_enums.py``, which import
``Model_enums.ModelID`` and so follow it. Each needs its native-import site decided one at a time —
that site is the only thing standing between the file and a verbatim port.
"""
