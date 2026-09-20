"""Main Py4GW Stealth window.

Run from the project directory with::

    python main.py

The first tab is a small, read-only surface for exercising the current Win32
process-discovery methods. It deliberately does not read or modify process
memory.
"""

from __future__ import annotations

from typing import Any, TypedDict

from nicegui import ui

from py4gw import Win32


class ProcessRow(TypedDict):
    """One row displayed by the process table."""

    pid: int
    name: str
    path: str


class MainWindow:
    """Build and run the main project window."""

    def __init__(self) -> None:
        """Create the Win32 test tab and its controls."""

        self._win32 = Win32()
        self._status: Any = None
        self._process_table: Any = None
        self._build_interface()

    def run(self) -> None:
        """Start the NiceGUI window in native desktop mode."""

        ui.run(
            native=True,
            reload=False,
            title="Py4GW Stealth",
        )

    def _build_interface(self) -> None:
        """Create the tab container and the current Win32 test tab."""

        with ui.tabs().classes("w-full") as tabs:
            win32_tab = ui.tab("Win32 process test")

        with ui.tab_panels(tabs, value=win32_tab).classes("w-full"):
            with ui.tab_panel(win32_tab):
                self._build_win32_tab()

    def _build_win32_tab(self) -> None:
        """Create controls for the read-only process-discovery methods."""

        ui.label("Win32 process discovery").classes("text-h6")
        ui.label(
            "These actions only inspect the current Windows process list."
        )

        with ui.row():
            ui.button("List all processes", on_click=self._list_processes)
            ui.button("Find Gw.exe", on_click=self._find_guild_wars)

        self._status = ui.label("No scan performed")
        self._process_table = ui.table(
            columns=[
                {"name": "pid", "label": "PID", "field": "pid"},
                {"name": "name", "label": "Name", "field": "name"},
                {"name": "path", "label": "Path", "field": "path"},
            ],
            rows=[],
            row_key="pid",
        ).classes("w-full")

    def _list_processes(self) -> None:
        """Display the current read-only process snapshot."""

        try:
            processes = self._win32.list_processes()
        except OSError as error:
            self._show_error(error)
            return

        rows = [self._to_row(process) for process in processes]
        self._show_rows(rows, f"Listed {len(rows)} process(es)")

    def _find_guild_wars(self) -> None:
        """Display the current read-only ``Gw.exe`` candidates."""

        try:
            processes = self._win32.find_guild_wars()
        except OSError as error:
            self._show_error(error)
            return

        rows = [self._to_row(process) for process in processes]
        self._show_rows(rows, f"Found {len(rows)} Gw.exe candidate(s)")

    def _to_row(self, process: dict[str, Any]) -> ProcessRow:
        """Convert one Win32 record into a table row."""

        path = process.get("path")
        if path is None:
            path = "—"

        return {
            "pid": int(process["pid"]),
            "name": str(process["name"]),
            "path": str(path),
        }

    def _show_rows(self, rows: list[ProcessRow], message: str) -> None:
        """Replace the table contents and update its status text."""

        self._process_table.rows = rows
        self._process_table.update()
        self._status.set_text(message)

    def _show_error(self, error: OSError) -> None:
        """Display a Win32 failure without hiding its diagnostic message."""

        self._process_table.rows = []
        self._process_table.update()
        self._status.set_text(f"Win32 error: {error}")


if __name__ == "__main__":
    MainWindow().run()
