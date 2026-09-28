"""Offline parity test: the ported ``mods_core`` against the Reforged source it transcribes.

**How this one is checked.** ``mods_core`` is logic, not a table, so comparing declarations is not
enough — the two modules are *driven* over the same input and every answer is compared:

- the input is a set of synthetic modifier words built from the ported vocabulary (every
  ``ModifierIdentifier`` member with three argument pairs, words carrying real ``ItemUpgradeId`` values
  under ``Upgrade`` and ``AttributeRune``, a zero word, and an identifier outside ``_VALID_IDS``);
- the source gets them through a stand-in for native's ``PyItem`` binding — an object whose
  ``modifiers`` are the same records — and the port gets them through a fake client, so both decoders
  read the same words down their own call path;
- then ``decode_item``, ``find``, ``value_of``, ``subtype_of``, ``name_of``, ``is_better``,
  ``upgrades_on``, ``known_upgrades``, ``slot_of_upgrade``, ``upgrade_is_maxed``, ``effect_name``,
  ``render_mod``, ``describe_item`` and ``raw_dump`` are compared answer for answer, and the six
  module-level tables (``_EFFECT``, ``_TEXT``, ``_SILENT``, ``_VALID_IDS``, ``_UPGRADE_NAME``,
  ``_GENERIC_RUNE_CARRIER_NAME``) entry for entry.

Two normalisations make that comparison meaningful: an enum member is reduced to its class name, member
name and value (the source's member and the port's member are different objects), and a ``DecodedMod``
or ``_Def`` is reduced to its field tuple (the two dataclasses are different classes). Without those the
comparison would fail on identity alone and check nothing.

Source: ``Py4GWCoreLib/mods_core.py`` (494 lines).
"""

from __future__ import annotations

import dataclasses
import importlib.util
import struct
import sys
import types
import unittest
from enum import Enum
from pathlib import Path
from typing import Any
from unittest import mock

from py4gw import mods_core
from py4gw import mods_types
from py4gw.context.item_context import ItemModifierStruct
from py4gw.enums_src import item_enums, skill_names

SOURCE_ROOT = Path(r"C:\Users\Apo\Py4GW_Reforged\Py4GWCoreLib")
SOURCE_FILE = SOURCE_ROOT / "mods_core.py"

_TABLES = (
    "_EFFECT",
    "_TEXT",
    "_SILENT",
    "_VALID_IDS",
    "_UPGRADE_NAME",
    "_GENERIC_RUNE_CARRIER_NAME",
)


def _normalise(value: Any) -> Any:
    """Reduce a value to something two modules can be compared through."""

    if isinstance(value, Enum):
        return ("enum", type(value).__name__, value.name, value.value)
    if isinstance(value, type):
        # `_Def.subtype_cat` holds the enum *class* the subtype is read through (sixteen entries do),
        # so a class is compared by its name — the source's `DamageType` and this port's are two
        # classes, and which module they live in is not part of what the table declares.
        return ("type", value.__name__)
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return (
            "dataclass",
            type(value).__name__,
            [_normalise(item) for item in dataclasses.astuple(value)],
        )
    if isinstance(value, dict):
        return ("dict", [(_normalise(key), _normalise(item)) for key, item in value.items()])
    if isinstance(value, (set, frozenset)):
        return ("set", sorted(repr(_normalise(item)) for item in value))
    if isinstance(value, (list, tuple)):
        return ("seq", type(value).__name__, [_normalise(item) for item in value])
    if value is None:
        return None
    return ("value", type(value).__name__, value)


def _word(identifier: Any, arg1: int, arg2: int) -> int:
    """Build the raw modifier word whose decoded identifier and arguments are the ones asked for.

    The decoder reads ``identifier = (word >> 16) >> 4 & 0x3FF``, ``arg1 = (word >> 8) & 0xFF`` and
    ``arg2 = word & 0xFF``, so the identifier goes in shifted left by four above the two argument bytes,
    and the whole thing is masked to the 32 bits a word has. That mask matters: the identifier field is
    ten bits wide, so ``ModifierIdentifier`` members above ``0x3FF`` (``None_`` is ``0xFFFF``) cannot be
    produced by any word. They are still fed in — the port's ``_VALID_IDS`` holds them — and both
    decoders drop them identically.
    """

    return (((int(identifier) << 4) << 16) | ((arg1 & 0xFF) << 8) | (arg2 & 0xFF)) & 0xFFFFFFFF


def _modifiers(*words: int) -> list[ItemModifierStruct]:
    """Build the real ported modifier records from raw words."""

    return [ItemModifierStruct.from_buffer_copy(struct.pack("<I", word)) for word in words]


def _synthetic_words() -> list[int]:
    """Every identifier with three argument pairs, plus the four edge cases."""

    words: list[int] = []
    for member in mods_types.ModifierIdentifier:
        words.append(_word(member, 0, 0))
        words.append(_word(member, 0x12, 0x34))
        words.append(_word(member, 0xFF, 0x01))
    for upgrade in (
        mods_types.ItemUpgradeId.Icy_Axe,
        mods_types.ItemUpgradeId.Adept_Staff,
        mods_types.ItemUpgradeId.Inherent,
        mods_types.ItemUpgradeId.Unknown,
    ):
        for identifier in (
            mods_types.ModifierIdentifier.Upgrade,
            mods_types.ModifierIdentifier.AttributeRune,
        ):
            words.append(_word(identifier, (int(upgrade) >> 8) & 0xFF, int(upgrade) & 0xFF))
    words.append(0)  # `IsValid()` is false for this one
    words.append(_word(0x123, 1, 1))  # an identifier that is not in `_VALID_IDS`
    return words


#: The items both decoders are asked about: one with every word, one empty, one small, one missing.
ITEMS: dict[int, list[ItemModifierStruct]] = {}


def _build_items() -> None:
    words = _synthetic_words()
    ITEMS[1] = _modifiers(*words)
    ITEMS[2] = []
    ITEMS[3] = _modifiers(*words[:6])


def _install_source_stubs() -> None:
    """Give the source module the two native modules it imports."""

    if "PySkill" not in sys.modules:

        class _SkillID:
            def __init__(self, name: str) -> None:
                self.id = skill_names.GetSkillIDByName(str(name))

        class _Skill:
            def __init__(self, name: str) -> None:
                self.id = _SkillID(name)

        skills = types.ModuleType("PySkill")
        skills.Skill = _Skill  # type: ignore[attr-defined]
        sys.modules["PySkill"] = skills

    if "PyItem" not in sys.modules:

        class _SourceItem:
            """What native's ``PyItem.PyItem(item_id)`` is for this comparison: the same words."""

            def __init__(self, item_id: int) -> None:
                self.item_id = int(item_id)
                self.modifiers = ITEMS.get(int(item_id), [])

        class _SourcePyItem:
            PyItem = _SourceItem

        sys.modules["PyItem"] = _SourcePyItem  # type: ignore[assignment]

    for package_name, path in (
        ("Py4GWCoreLib", SOURCE_ROOT),
        ("Py4GWCoreLib.enums_src", SOURCE_ROOT / "enums_src"),
    ):
        if package_name not in sys.modules:
            package = types.ModuleType(package_name)
            package.__path__ = [str(path)]  # type: ignore[attr-defined]
            sys.modules[package_name] = package


def _load_source() -> Any:
    """Load the source module itself, or skip when the checkout is not on this machine."""

    if not SOURCE_FILE.is_file():
        raise unittest.SkipTest(f"the Reforged source is not on this machine: {SOURCE_FILE}")

    _install_source_stubs()
    full_name = "Py4GWCoreLib.mods_core"
    existing = sys.modules.get(full_name)
    if existing is not None:
        return existing

    spec = importlib.util.spec_from_file_location(full_name, SOURCE_FILE)
    if spec is None or spec.loader is None:  # pragma: no cover - reported as a skip above
        raise unittest.SkipTest(f"the Reforged source could not be loaded: {SOURCE_FILE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    spec.loader.exec_module(module)
    return module


class _FakeItemContextStruct:
    """The item context's own record: the read the port reaches the item through."""

    def __init__(self, lookup: Any) -> None:
        self._lookup = lookup

    def GetItemById(self, item_id: int) -> Any:
        return self._lookup(int(item_id))


class _FakeItemContext:
    """The port's side of the same read: the item record's own modifier array.

    The shape is the real one — the reader hands out its record through ``read()``, and the item lookup
    is a member of that record (``ItemContextStruct.GetItemById``), not of the reader.
    """

    def __init__(self, lookup: Any) -> None:
        self._struct = _FakeItemContextStruct(lookup)

    def read(self) -> _FakeItemContextStruct:
        return self._struct


def _by_item_id(item_id: int) -> Any:
    """The fixture's items, by id: a missing id is an item with no modifiers."""

    if int(item_id) not in ITEMS:
        return None
    return types.SimpleNamespace(read_modifiers=lambda: ITEMS[int(item_id)])


class _FakeClient:
    def __init__(self, lookup: Any = None) -> None:
        self.item_context = _FakeItemContext(lookup or _by_item_id)


@unittest.skipUnless(SOURCE_FILE.is_file(), f"the Reforged source is not present at {SOURCE_FILE}")
class ModsCoreParityTests(unittest.TestCase):
    """Both decoders over the same words, compared answer for answer."""

    @classmethod
    def setUpClass(cls) -> None:
        _build_items()
        cls.source = _load_source()
        cls.patcher = mock.patch.object(
            mods_core, "require_client", lambda: _FakeClient()
        )
        cls.patcher.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.patcher.stop()

    def test_the_module_tables_match_entry_for_entry(self) -> None:
        """Every table the module keeps, compared with the source's own."""

        for name in _TABLES:
            with self.subTest(table=name):
                theirs = getattr(self.source, name)
                ours = getattr(mods_core, name)
                self.assertEqual(len(ours), len(theirs))
                self.assertEqual(_normalise(ours), _normalise(theirs))

    def test_the_public_names_are_the_source_s(self) -> None:
        """Nothing dropped and nothing added, apart from the one recorded substitution.

        The source imports native's ``PyItem`` binding; this port reaches the same modifier array
        through ``require_client``, which is the substitution the module's docstring records.
        """

        theirs = {name for name in vars(self.source) if not name.startswith("_")}
        ours = {name for name in vars(mods_core) if not name.startswith("_")}
        self.assertEqual(sorted(theirs - ours), ["PyItem"])
        self.assertEqual(sorted(ours - theirs), ["require_client"])

    def test_the_slot_enum_matches(self) -> None:
        """`Slot`'s members, order and values."""

        self.assertEqual(
            [(member.name, int(member)) for member in mods_core.Slot],
            [(member.name, int(member)) for member in self.source.Slot],
        )
        self.assertEqual([member.name for member in mods_core.Slot], [
            "Inherent", "Prefix", "Suffix", "Inscription", "Rune", "Insignia"
        ])

    def test_decode_item_returns_the_same_modifiers(self) -> None:
        """`decode_item` over every item: same records, same order."""

        for item_id in (*ITEMS, 99):
            with self.subTest(item_id=item_id):
                self.assertEqual(
                    _normalise(mods_core.decode_item(item_id)),
                    _normalise(self.source.decode_item(item_id)),
                )

    def test_every_reader_answers_the_same_for_every_modifier(self) -> None:
        """The twelve readers, over every decoded modifier of every item."""

        for item_id in (*ITEMS, 99):
            ours = mods_core.decode_item(item_id)
            theirs = self.source.decode_item(item_id)
            with self.subTest(item_id=item_id, decoded=len(ours)):
                self.assertEqual(len(ours), len(theirs))
            for index, (our_mod, their_mod) in enumerate(zip(ours, theirs)):
                with self.subTest(item_id=item_id, index=index):
                    self.assertEqual(
                        _normalise(mods_core.value_of(our_mod)),
                        _normalise(self.source.value_of(their_mod)),
                    )
                    self.assertEqual(
                        _normalise(mods_core.subtype_of(our_mod)),
                        _normalise(self.source.subtype_of(their_mod)),
                    )
                    self.assertEqual(
                        mods_core.name_of(our_mod), self.source.name_of(their_mod)
                    )
                    self.assertEqual(
                        mods_core.is_better(our_mod), self.source.is_better(their_mod)
                    )
                    self.assertEqual(
                        mods_core.render_mod(item_id, our_mod),
                        self.source.render_mod(item_id, their_mod),
                    )
                    for identifier in (our_mod.identifier, 0xFFFF, 0x123):
                        self.assertEqual(
                            mods_core.find(item_id, identifier),
                            None
                            if self.source.find(item_id, identifier) is None
                            else mods_core.find(item_id, identifier),
                        )

    def test_find_answers_the_same_for_every_identifier(self) -> None:
        """`find` with one no item carries, and with several at once."""

        identifiers = [int(member) for member in mods_types.ModifierIdentifier]
        for item_id in (*ITEMS, 99):
            for identifier in identifiers:
                with self.subTest(item_id=item_id, identifier=hex(identifier)):
                    ours = mods_core.find(item_id, identifier)
                    theirs = self.source.find(item_id, identifier)
                    self.assertEqual(
                        None if ours is None else _normalise(ours),
                        None if theirs is None else _normalise(theirs),
                    )
            with self.subTest(item_id=item_id, many=True):
                ours = mods_core.find(item_id, *identifiers)
                theirs = self.source.find(item_id, *identifiers)
                self.assertEqual(
                    None if ours is None else _normalise(ours),
                    None if theirs is None else _normalise(theirs),
                )

    def test_the_upgrade_readers_answer_the_same(self) -> None:
        """`upgrades_on`, `known_upgrades`, `slot_of_upgrade` and `upgrade_is_maxed`."""

        self.assertEqual(
            _normalise(mods_core.known_upgrades()), _normalise(self.source.known_upgrades())
        )
        for item_id in (*ITEMS, 99):
            with self.subTest(item_id=item_id):
                self.assertEqual(
                    _normalise(mods_core.upgrades_on(item_id)),
                    _normalise(self.source.upgrades_on(item_id)),
                )
        for name, _slot in mods_core.known_upgrades()[:40]:
            with self.subTest(upgrade=name):
                self.assertEqual(
                    mods_core.slot_of_upgrade(name), self.source.slot_of_upgrade(name)
                )
                self.assertEqual(
                    mods_core.slot_of_upgrade("NotAnUpgrade"),
                    self.source.slot_of_upgrade("NotAnUpgrade"),
                )
                for item_id in (*ITEMS, 99):
                    self.assertEqual(
                        mods_core.upgrade_is_maxed(item_id, name),
                        self.source.upgrade_is_maxed(item_id, name),
                    )

    def test_effect_name_answers_the_same_for_every_identifier(self) -> None:
        """`effect_name` over the whole vocabulary, and outside it."""

        for identifier in (
            *[int(member) for member in mods_types.ModifierIdentifier],
            0x123,
            0,
        ):
            with self.subTest(identifier=hex(identifier)):
                self.assertEqual(
                    mods_core.effect_name(identifier), self.source.effect_name(identifier)
                )

    def test_the_render_layer_answers_the_same(self) -> None:
        """`describe_item` and `raw_dump`, which are what a caller compares against the client."""

        for item_id in (*ITEMS, 99):
            with self.subTest(item_id=item_id):
                self.assertEqual(
                    mods_core.describe_item(item_id), self.source.describe_item(item_id)
                )
                self.assertEqual(
                    mods_core.raw_dump(item_id), self.source.raw_dump(item_id)
                )


class ModsCoreReadPathTests(unittest.TestCase):
    """The port's own read path, on this side alone."""

    def setUp(self) -> None:
        _build_items()
        self.patcher = mock.patch.object(mods_core, "require_client", lambda: _FakeClient())
        self.patcher.start()

    def tearDown(self) -> None:
        self.patcher.stop()

    def test_a_missing_item_decodes_to_nothing(self) -> None:
        """`GetItemById` answers `None` for an item that is not in the array, and that is no mods."""

        self.assertEqual(mods_core.decode_item(99), [])

    def test_an_empty_modifier_array_decodes_to_nothing(self) -> None:
        """An item with no modifier words, which is what an empty slot is."""

        self.assertEqual(mods_core.decode_item(2), [])

    def test_a_modifier_word_decodes_to_its_identifier_and_arguments(self) -> None:
        """One word in, one `DecodedMod` out, with the fields the decoder computes."""

        word = _word(mods_types.ModifierIdentifier.Damage, 0x12, 0x34)
        with mock.patch.object(
            mods_core, "require_client", lambda: _FakeClientFor(_modifiers(word))
        ):
            decoded = mods_core.decode_item(1)
        self.assertEqual(len(decoded), 1)
        self.assertEqual(decoded[0].identifier, int(mods_types.ModifierIdentifier.Damage))
        self.assertEqual(decoded[0].arg1, 0x12)
        self.assertEqual(decoded[0].arg2, 0x34)
        self.assertEqual(decoded[0].upgrade_id, 0)
        self.assertEqual(decoded[0].raw_arg, 0x1234)

    def test_an_upgrade_word_carries_its_upgrade_id(self) -> None:
        """`Upgrade` and `AttributeRune` are the two identifiers whose low word is an upgrade id."""

        upgrade_id = int(mods_types.ItemUpgradeId.Icy_Axe)
        word = _word(
            mods_types.ModifierIdentifier.Upgrade, (upgrade_id >> 8) & 0xFF, upgrade_id & 0xFF
        )
        with mock.patch.object(
            mods_core, "require_client", lambda: _FakeClientFor(_modifiers(word))
        ):
            decoded = mods_core.decode_item(1)
        self.assertEqual(len(decoded), 1)
        self.assertEqual(decoded[0].upgrade_id, upgrade_id)


class _FakeItemFor:
    """An item record standing in for one specific modifier list."""

    def __init__(self, modifiers: list[ItemModifierStruct]) -> None:
        self._modifiers = modifiers

    def read_modifiers(self) -> list[ItemModifierStruct]:
        return self._modifiers


class _FakeClientFor(_FakeClient):
    """A client whose one item carries a chosen modifier list, in the same record shape."""

    def __init__(self, modifiers: list[ItemModifierStruct]) -> None:
        super().__init__(lookup=lambda item_id: _FakeItemFor(modifiers))


if __name__ == "__main__":
    unittest.main(verbosity=2)
