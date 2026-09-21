"""Small script-level example for the public client-selection facade."""

import py4gw


def main() -> None:
    """Connect to the first available client and print its character name."""

    clients = py4gw.win32.list_processes()
    if not clients:
        print("No Guild Wars clients are currently running.")
        return

    py4gw.connect(clients[0])
    try:
        char_context = py4gw.context.charcontext.get()
        if char_context is not None:
            print(char_context.player_name_str or "in selection menus")
    finally:
        py4gw.disconnect()


if __name__ == "__main__":
    main()
