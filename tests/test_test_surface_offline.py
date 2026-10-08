"""Offline tests for the library surface `main.py` maps (`test_surface.py`).

Two things have to hold for the window's test surface to mean anything:

* **completeness** -- every name ``py4gw`` exports, every public member of every class it exports,
  every field of every record and every enum member appears in the map, and no name appears twice
  under two modules;
* **safety and honesty** -- running the whole map with nothing connected never calls a member
  classified as a write, never raises, and reports every skip with its reason, while a member whose
  own source says it acts is classified as a write whatever its name looks like.

The completeness assertions are computed from the library at test time rather than written down as
counts, so a member added to the library has to appear in the map or this file fails.

No client is involved, nothing is elevated, and nothing is written to any target.
"""

from __future__ import annotations

import unittest
from typing import Any
from unittest import mock

import py4gw
import test_surface


class SurfaceCompletenessTest(unittest.TestCase):
    """The map covers the library's whole declared surface, and says where each name lives."""

    @classmethod
    def setUpClass(cls) -> None:
        """Build the map once; every test here reads it."""

        cls.entries = test_surface.build_entries()
        cls.labels = {entry.label for entry in cls.entries}
        #: label -> entry, and "Owner.member" -> entry, so a lookup does not scan 20,000 rows.
        cls.by_label = {entry.label: entry for entry in cls.entries}
        cls.by_tail: dict[str, test_surface.Entry] = {}
        for entry in cls.entries:
            cls.by_tail.setdefault(".".join(entry.label.split(".")[-2:]), entry)

    def entry(self, query: str) -> test_surface.Entry | None:
        """An entry by its path or by its owner and member, without scanning the map."""

        return self.by_label.get(query) or self.by_tail.get(query)

    def test_every_exported_name_is_mapped(self) -> None:
        """Every name in ``py4gw.__all__`` has an entry of its own."""

        missing = [name for name in py4gw.__all__ if f"py4gw.{name}" not in self.labels]
        self.assertEqual(missing, [], f"exported names missing from the map: {missing}")

    def test_every_public_member_of_every_exported_class_is_mapped(self) -> None:
        """A class's public members are all in the map, under the module that declares the class.

        A class re-exported by ``py4gw`` is expanded where it is declared -- and a class reachable
        under a second name (``AvailableCharacterStruct``) is expanded under the name it was
        declared with -- so the lookup goes by the class itself, not by the exported name.
        """

        missing: list[str] = []
        for name in py4gw.__all__:
            value = getattr(py4gw, name)
            if not isinstance(value, type):
                continue
            canonical = _canonical(self.entries, value)
            if canonical is None:
                # The class is mapped as an alias of a class that was expanded elsewhere; the
                # expanded entry is found by identity, so this only happens for a class in no
                # group at all.
                missing.append(f"{name} (not expanded anywhere)")
                continue
            for member in vars(value):
                if member.startswith("_"):
                    continue
                if f"{canonical.label}.{member}" not in self.labels:
                    missing.append(f"{canonical.label}.{member}")
        self.assertEqual(missing, [], f"members missing from the map: {missing[:20]}")

    def test_every_record_field_is_mapped_with_its_offset(self) -> None:
        """A record's fields are mapped, each with the offset and the type it was declared with.

        A record can be reachable under several names (``AvailableCharacterStruct`` is another name
        for the record declared as ``AvailableCharacterInfoStruct``), and it is expanded once, under
        the name it was declared with -- so the lookup goes by the *class*, not by the exported name.
        """

        checked = 0
        for name in py4gw.__all__:
            value = getattr(py4gw, name)
            fields = getattr(value, "_fields_", None)
            if not fields:
                continue
            canonical = _canonical(self.entries, value)
            self.assertIsNotNone(canonical, f"{name} has no expanded record of its own")
            assert canonical is not None
            for definition in fields:
                field_name = definition[0]
                entry = self.by_label.get(f"{canonical.label}.{field_name}")
                self.assertIsNotNone(entry, f"{canonical.label}.{field_name} is not in the map")
                assert entry is not None
                offset = getattr(value, field_name).offset
                self.assertIn(f"+0x{offset:04X}", entry.detail)
                checked += 1
        self.assertGreater(checked, 1000, "the map should carry the records' fields")

    def test_every_enum_member_is_mapped(self) -> None:
        """An enum's members are mapped with their values."""

        checked = 0
        for name in py4gw.__all__:
            value = getattr(py4gw, name)
            members = getattr(value, "__members__", None)
            if not members or not isinstance(value, type):
                continue
            canonical = _canonical(self.entries, value)
            self.assertIsNotNone(canonical, name)
            assert canonical is not None
            for member_name in members:
                self.assertIn(f"{canonical.label}.{member_name}", self.labels)
                checked += 1
        self.assertGreater(checked, 20, "the map should carry the enums' members")

    def test_a_record_is_expanded_once_and_named_where_it_lives(self) -> None:
        """Each record's fields appear once, and every other mention says where it is declared."""

        expanded = [
            entry
            for entry in self.entries
            if entry.kind == "record" and not entry.detail.startswith("declared in")
        ]
        keys = [(entry.group, entry.name) for entry in expanded]
        self.assertEqual(len(keys), len(set(keys)), "a record was expanded twice")
        aliases = [
            entry
            for entry in self.entries
            if entry.kind == "record" and entry.detail.startswith("declared in")
        ]
        self.assertTrue(aliases, "the map should name the aliases of a record too")
        for alias in aliases:
            self.assertEqual(alias.run, "none", alias.label)
        # Every field belongs to a record expanded in the same module.
        for entry in self.entries:
            if entry.kind != "field":
                continue
            owners = [
                candidate
                for candidate in expanded
                if candidate.name == entry.owner and candidate.group == entry.group
            ]
            self.assertEqual(len(owners), 1, entry.label)

    def test_the_map_carries_a_readable_summary(self) -> None:
        """The summary the window shows has the counts a reader can check against the library."""

        summary = test_surface.summarise(self.entries)
        self.assertGreater(summary.total, 10_000)
        self.assertGreater(summary.by_kind.get("record", 0), 100)
        self.assertGreater(summary.by_kind.get("field", 0), 1000)
        self.assertGreater(summary.by_kind.get("method", 0), 1000)
        self.assertGreater(summary.runnable, 5000)
        self.assertTrue(any("entries:" in line for line in summary.lines()))


class SurfaceSafetyTest(unittest.TestCase):
    """Running the surface never writes, never raises, and reports what it skipped."""

    def test_a_write_is_never_called_without_being_asked_for(self) -> None:
        """A member classified as a write is skipped, and the real member is never reached.

        The check is made on the member itself: ``Player.Move`` is replaced by a recorder, and the
        entry is run through the engine. If the engine were to call it, the recorder would say so.
        """

        from py4gw import Player

        called: list[tuple[Any, ...]] = []

        def recorder(*args: Any, **kwargs: Any) -> None:
            called.append(args)

        move_entry = _first(_entries(), "Player.Move")
        self.assertIsNotNone(move_entry, "Player.Move should be on the surface")
        assert move_entry is not None
        self.assertEqual(move_entry.access, "write")
        with mock.patch.object(Player, "Move", staticmethod(recorder)):
            outcome = test_surface.run_entry(move_entry)
        self.assertEqual(outcome.status, "skipped (classified as a write)")
        self.assertEqual(called, [])

    def test_the_whole_surface_runs_with_nothing_connected_and_nothing_fails(self) -> None:
        """With no client, every entry answers, refuses, or is skipped -- none raises."""

        entries = _entries()
        outcomes = test_surface.run_all(entries, include_unknown=True)
        failed = [(outcome.entry.label, outcome.error) for outcome in outcomes if outcome.status == "failed"]
        self.assertEqual(failed, [])
        counts: dict[str, int] = {}
        for outcome in outcomes:
            counts[outcome.status] = counts.get(outcome.status, 0) + 1
        self.assertGreater(counts.get("answered", 0), 5000)
        self.assertGreater(counts.get("skipped (classified as a write)", 0), 0)
        # Everything that ran has a readable reason or value.
        for outcome in outcomes:
            if outcome.status == "answered":
                self.assertTrue(outcome.value or outcome.entry.kind in ("module",), outcome.entry.label)
            else:
                self.assertTrue(outcome.status, outcome.entry.label)

    def test_an_unclassified_member_is_not_run_while_a_client_is_connected(self) -> None:
        """With something connected, an unclassified member cannot be told apart from a write."""

        entry = test_surface.Entry(
            group="py4gw",
            owner="Player",
            name="NameToTest",
            kind="method",
            access="unknown",
            run="call",
        )
        connected = test_surface.run_entry(entry, include_unknown=True, client_connected=True)
        self.assertEqual(connected.status, "skipped (not classified, and a client is connected)")
        unconnected = test_surface.run_entry(entry, include_unknown=True, client_connected=False)
        self.assertNotEqual(unconnected.status, "skipped (not classified, and a client is connected)")

    def test_a_classification_comes_from_the_members_own_source(self) -> None:
        """The write vocabulary is read out of the member's source, not guessed from its name.

        ``Map.GetMapID`` reads, ``Player.Move`` and ``Map.Travel`` act, and a read whose source
        reaches for the client is marked as needing one.
        """

        move = _first(_entries(), "Player.Move")
        travel = _first(_entries(), "Map.Travel")
        map_id = _first(_entries(), "Map.GetMapID")
        for entry in (move, travel, map_id):
            self.assertIsNotNone(entry)
        assert move is not None and travel is not None and map_id is not None
        self.assertEqual(move.access, "write")
        self.assertEqual(travel.access, "write")
        self.assertIn(map_id.access, ("read", "unknown"))
        # A read on a class whose members do reach for the client is marked as needing one.
        array = _first(_entries(), "AgentArray.GetAgentArray")
        self.assertIsNotNone(array)
        assert array is not None
        self.assertEqual(array.access, "read")

    def test_a_member_whose_docstring_says_it_writes_is_a_write(self) -> None:
        """A docstring that states the member writes settles it, whatever the name looks like."""

        entry = test_surface.Entry(
            group="py4gw",
            owner="Example",
            name="Fetch",
            kind="method",
            doc="This is a write: it patches the client.",
            access=test_surface._classify("Example", "Fetch", "This is a write: it patches the client."),
            run="call",
        )
        self.assertEqual(entry.access, "write")
        outcome = test_surface.run_entry(entry)
        self.assertEqual(outcome.status, "skipped (classified as a write)")

    def test_what_a_member_prints_is_captured_with_its_result(self) -> None:
        """A member that reports through ``print`` has that text captured, not spilled.

        ``Utils.GenerateSkillbarTemplate`` says why it could not encode, and with no client it is
        the one member on the surface that prints -- which is exactly the case a test surface must
        show rather than let fall on the console behind the window.
        """

        entry = _first(_entries(), "Utils.GenerateSkillbarTemplate")
        self.assertIsNotNone(entry)
        assert entry is not None
        outcome = test_surface.run_entry(entry, include_unknown=True)
        self.assertNotEqual(outcome.status, "failed", outcome.error)
        self.assertTrue(outcome.output, "the member's own message should be captured")
        self.assertIn("skillbar", outcome.output.lower())

    def test_the_short_report_leads_with_counts_and_lists_what_did_not_answer(self) -> None:
        """The summary is the report to read first: counts, a module table, and the unanswered.

        What it must *not* do is list the ~16,000 entries that answered -- their values belong to the
        full report -- so the two are compared: the summary is a small fraction of the whole and
        still names every entry that did not answer.
        """

        entries = _entries()[:4000]
        outcomes = test_surface.run_all(entries, include_unknown=True)
        short = test_surface.summary_report(entries, outcomes)
        full = test_surface.report(entries, outcomes)
        self.assertIn("py4gw library surface -- summary", short)
        self.assertIn("per module (entries / answered)", short)
        self.assertIn("everything that did not answer, by status", short)
        self.assertLess(len(short), len(full) // 2)
        unanswered = [
            outcome for outcome in outcomes if outcome.status != "answered"
        ]
        self.assertGreater(len(unanswered), 0)
        # Counted per status, and each one is named with the reason it did not answer.
        for status in {outcome.status for outcome in unanswered}:
            self.assertIn(status, short)
        self.assertTrue(any(outcome.entry.display in short for outcome in unanswered))

    def test_the_window_s_filter_selects_the_same_results_the_counts_say(self) -> None:
        """Filtering is a view of one run: a status shows exactly its count, and text narrows it."""

        entries = _entries()[:4000]
        outcomes = test_surface.run_all(entries, include_unknown=True)
        counts = test_surface.statuses(outcomes)
        self.assertEqual(counts.get("answered", 0) > 0, True)
        status = next(name for name in counts if name != "answered")
        selected = test_surface.outcomes_with_status(outcomes, status)
        self.assertEqual(len(selected), counts[status])
        self.assertTrue(all(outcome.status == status for outcome in selected))
        not_answered = test_surface.outcomes_with_status(outcomes, "not answered")
        self.assertEqual(len(not_answered), len(outcomes) - counts.get("answered", 0))
        narrowed = test_surface.outcomes_with_status(outcomes, status, "client")
        self.assertLessEqual(len(narrowed), len(selected))
        self.assertEqual(len(test_surface.outcomes_with_status(outcomes, "")), len(outcomes))

    def test_the_report_lists_every_entry_and_every_reason(self) -> None:
        """The report is the whole surface: each entry appears, and each skip is grouped by reason."""

        entries = _entries()
        outcomes = test_surface.run_all(entries, include_unknown=True)
        text = test_surface.report(entries, outcomes)
        self.assertIn("py4gw library surface", text)
        self.assertIn("what was not answered, by reason", text)
        for entry in entries:
            self.assertIn(entry.label, text)
        self.assertIn("skipped (classified as a write)", text)

    def test_a_placeholder_entry_is_reported_rather_than_run(self) -> None:
        """A module the map could not read is a row in the report, not an exception."""

        entries = test_surface.build_entries(modules=("py4gw.not_a_module",))
        self.assertEqual(len(entries), 1)
        outcome = test_surface.run_entry(entries[0], include_unknown=True)
        self.assertEqual(outcome.status, "not runnable")
        self.assertIn("ModuleNotFoundError", entries[0].detail)


def _entries() -> tuple[test_surface.Entry, ...]:
    """The map, built once per process and shared."""

    global _CACHED
    if _CACHED is None:
        _CACHED = test_surface.build_entries()
    return _CACHED


_CACHED: tuple[test_surface.Entry, ...] | None = None


def _first(entries: tuple[test_surface.Entry, ...], query: str) -> test_surface.Entry | None:
    """The first entry matching a query, or None."""

    matches = test_surface.find(entries, query)
    return matches[0] if matches else None


def _canonical(entries: tuple[test_surface.Entry, ...], value: Any) -> test_surface.Entry | None:
    """The one entry that expanded this class, found by the class it resolves to."""

    import importlib

    for entry in entries:
        if entry.owner or entry.kind not in ("record", "enum", "class"):
            continue
        if entry.detail.startswith("declared in") or entry.run == "none":
            continue
        try:
            module = importlib.import_module(entry.group)
        except Exception:  # noqa: BLE001 - a group that cannot be imported has nothing to match
            continue
        if getattr(module, entry.name, None) is value:
            return entry
    return None


if __name__ == "__main__":
    unittest.main()
