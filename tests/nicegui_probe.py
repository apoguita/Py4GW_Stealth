"""Small manual check for NiceGUI native-window support.

Run from the project directory with::

    python tests\nicegui_probe.py

This deliberately does not use the Py4GW Stealth library yet. It only checks
that NiceGUI, pywebview, and the Windows webview backend can open a window.
"""

from nicegui import ui


def show_button_result() -> None:
    """Update the status text when the test button is pressed."""

    status.set_text(
        f"Button works: target={target.value}, view={view.value}"
    )


ui.label("NiceGUI native-window probe")
ui.label("This test does not scan processes yet.")

status = ui.label("Choose options and press the button")
ui.button("Test button", on_click=show_button_result)
target = ui.select(
    ["Guild Wars", "All processes"],
    value="Guild Wars",
    label="Target",
)
ui.label("View")
view = ui.radio(["Summary", "Details"], value="Summary")


if __name__ == "__main__":
    ui.run(
        native=True,
        reload=False,
        title="Py4GW Stealth - NiceGUI test",
    )
