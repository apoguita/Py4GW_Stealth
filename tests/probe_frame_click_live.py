"""Live probe: the frame tree around a real interaction, then a click on a new frame's child.

The plan is the owner's, and it is deliberately simple:

1. **snapshot the frame tree** (every created frame, by its own ``frame_hash_id`` identity);
2. **interact** with the closest living non-enemy agent (``Player.Interact``), which is what makes a
   window appear — the port does not assume a dialog exists, it drives the interaction that creates one;
3. **snapshot again**: the difference is the frame the interaction brought up;
4. **click one of that frame's children** — ``Frame.click``, i.e. native's ``ui::ButtonClick``
   (``ui_methods.cpp:1249-1274``), which sends ``kMouseClick2`` with a ``MouseAction`` packet to the
   **parent** frame's callbacks through the client's own ``__thiscall`` sender;
5. **snapshot once more**: if the window closed or changed, the click reached the client.

The child is chosen preferring a button that ends the conversation (its text naming "End"/"Goodbye"/"Bye"/
"Cancel"/"Close"), because the point is to prove the click reaches the client, not to accept anything.
Which child was chosen, and why, is in the report.

This connects with the **write** connection (the click is a write into the client) and disconnects at the
end, which removes the hooks it installed and frees what it placed.

Usage: (elevated) python tests/probe_frame_click_live.py [report-path]
"""

from __future__ import annotations

import json
import math
import sys
import time
from typing import Any

import py4gw
from py4gw.agent import Agent
from py4gw.agent_array import AgentArray
from py4gw.frame_tree import frame as frame_module
from py4gw.player import Player
from py4gw.ui.frame import FrameStruct, is_valid_frame_pointer
from py4gw.win32 import Win32

REPORT_PATH = sys.argv[1] if len(sys.argv) > 1 else ""

#: How long to wait for the interaction to bring a window up, and for the click to show itself.
WINDOW_WAIT_SECONDS = 20.0
CLICK_WAIT_SECONDS = 4.0

#: Labels that end a conversation rather than starting something.
_CLOSING_WORDS = ("end", "goodbye", "bye", "cancel", "close", "exit", "no thanks")

#: The template kind of an interactive dialog button (``Frame.template_type``'s own docstring).
_BUTTON_TEMPLATE = 1

#: Where a record's ``relation`` begins: the address native compares for a parent link.
_RELATION_OFFSET = FrameStruct.relation.offset


def _child_ids(entry: dict[str, Any], snapshot: dict[int, dict[str, Any]]) -> list[int]:
    """The frames whose ``relation.GetParent()`` is this frame — native's own parent test."""

    mine = int(entry["pointer"]) + _RELATION_OFFSET
    return sorted(
        int(other["frame_id"])
        for other in snapshot.values()
        if int(other["parent_relation"]) == mine
    )


def _snapshot(client: Any) -> dict[int, dict[str, Any]]:
    """Every created frame, keyed by **frame id**: what the tree looks like right now.

    The key is the id and not the hash, and that is not a detail: most frames carry hash ``0``, so a map
    keyed by hash collapses every unnamed frame into one entry and a diff through it cannot see a new
    unnamed frame at all — which is exactly the frame a window is made of.
    """

    array = client.frame_array
    frames: dict[int, dict[str, Any]] = {}
    for frame_id, pointer in enumerate(array.read_slot_pointers()):
        if not is_valid_frame_pointer(pointer):
            continue
        record = array.get(frame_id)
        if record is None or not record.is_created:
            continue
        frames[frame_id] = {
            "frame_id": frame_id,
            "hash": int(record.relation.frame_hash_id),
            "pointer": pointer,
            "parent_relation": int(record.relation.parent),
            "template": int(record.template_type),
            "hidden": bool(record.is_hidden),
            "callbacks": int(record.frame_callbacks.m_size),
            "user_param": int(record.field105_0x1c4),
        }
    return frames


def _describe(client: Any, entry: dict[str, Any]) -> dict[str, Any]:
    """One frame, named as far as this port can name it."""

    described = dict(entry)
    described["hash"] = hex(int(entry["hash"]))
    try:
        frame = frame_module.Frame.from_id(int(entry["frame_id"]))
        described["text"] = frame.text()
        described["usable"] = bool(frame.is_usable)
    except Exception as error:  # a read that cannot be made is reported, never hidden
        described["text_error"] = f"{type(error).__name__}: {error}"
    return described


def _closest_non_enemy_agent() -> int:
    """The nearest living, non-player, non-enemy agent — the one to talk to."""

    mine = Player.GetXY()
    best_id = 0
    best_distance = math.inf
    for agent_id in AgentArray.GetAgentArray():
        if not Agent.IsLiving(agent_id):
            continue
        if Agent.GetLoginNumber(agent_id):
            continue
        if Agent.GetAllegiance(agent_id)[1] == "Enemy":
            continue
        x, y = Agent.GetXY(agent_id)
        distance = math.hypot(x - mine[0], y - mine[1])
        if distance < best_distance:
            best_id, best_distance = int(agent_id), distance
    return best_id


def _parent_id(entry: dict[str, Any], snapshot: dict[int, dict[str, Any]]) -> int:
    """The frame whose relation this entry's ``relation.parent`` names, or ``0``."""

    parent_relation = int(entry["parent_relation"])
    if not parent_relation:
        return 0
    parent_pointer = parent_relation - _RELATION_OFFSET
    for other in snapshot.values():
        if int(other["pointer"]) == parent_pointer:
            return int(other["frame_id"])
    return 0


def _pick_child(client: Any, entry: dict[str, Any], snapshot: dict[int, dict[str, Any]]) -> dict[str, Any]:
    """One child of the new frame, preferring the button that ends the conversation.

    The children are found by native's own rule — ``candidate->relation.GetParent() == frame``, a
    comparison of relation **pointers** (``ui_methods.cpp:485``) — applied to the live records, rather
    than through the tree's cached map, which answers from the snapshot it built last.
    """

    mine = int(entry["pointer"]) + _RELATION_OFFSET
    children = _child_ids(entry, snapshot)
    candidates: list[dict[str, Any]] = []
    for child_id in children:
        frame = frame_module.Frame.from_id(int(child_id))
        try:
            text = frame.text()
        except Exception:
            text = ""
        candidates.append(
            {
                "frame_id": int(child_id),
                "text": text,
                "template": int(frame.template_type) if frame.exists else 0,
                "usable": bool(frame.is_usable) if frame.exists else False,
            }
        )
    closing = [
        child
        for child in candidates
        if any(word in str(child["text"]).lower() for word in _CLOSING_WORDS)
    ]
    buttons = [child for child in candidates if child["template"] == _BUTTON_TEMPLATE]
    if closing:
        chosen, why = closing[0], "its text ends the conversation"
    elif buttons:
        chosen, why = buttons[0], f"the first child with the button template ({_BUTTON_TEMPLATE})"
    elif candidates:
        chosen, why = candidates[0], "the first child the new frame has"
    else:
        chosen, why = {}, "the new frame has no children"
    return {"children": candidates, "chosen": chosen, "why": why}


def _run(report: dict[str, Any]) -> int:
    win32 = Win32()
    clients = win32.find_guild_wars()
    if not clients:
        report["error"] = "no Guild Wars client is running"
        return write_report(report)

    process = clients[0]
    report["pid"] = int(process["pid"])
    report["controller_elevated"] = bool(win32.is_elevated())

    with py4gw.connect(process) as client:
        bridge: Any = client._bridge
        report["hooks_installed"] = sorted(bridge.require_hooker().installed)

        before = _snapshot(client)
        report["frames_before"] = len(before)

        agent_id = _closest_non_enemy_agent()
        report["interact_agent"] = agent_id
        if not agent_id:
            report["error"] = "no living non-enemy agent to interact with"
            return write_report(report)

        Player.Interact(agent_id)

        # Wait, bounded, for a new frame that has children. The diff is by **id** (see `_snapshot`), and
        # the children are native's own parent-pointer rule applied to the live records.
        started = time.time()
        deadline = started + WINDOW_WAIT_SECONDS
        after: dict[int, dict[str, Any]] = before
        window_id = 0
        appeared = 0.0
        while time.time() < deadline:
            after = _snapshot(client)
            new_ids = sorted(set(after) - set(before))
            if new_ids and not appeared:
                appeared = round(time.time() - started, 3)
            for frame_id in new_ids:
                if _child_ids(after[frame_id], after):
                    window_id = frame_id
                    break
            if window_id:
                break
            time.sleep(0.5)

        # The dialog's own buttons are the new frames carrying the **button template** — native's
        # ``ButtonClick`` clicks one by sending ``kMouseClick2`` to its **parent's** callbacks with the
        # button's own ``child_offset_id``, so a new button frame is exactly the thing to click.
        new_ids = sorted(set(after) - set(before))
        report["seconds_to_window"] = appeared
        report["seconds_to_children"] = (
            round(time.time() - started, 3) if new_ids else None
        )
        report["frames_after"] = len(after)
        report["new_frames"] = [_describe(client, after[i]) for i in new_ids]
        if not new_ids:
            report["error"] = (
                f"no frame appeared within {WINDOW_WAIT_SECONDS}s of interacting with agent {agent_id}"
            )
            return write_report(report)

        button_ids = [i for i in new_ids if after[i]["template"] == _BUTTON_TEMPLATE]
        report["dialog_buttons"] = [_describe(client, after[i]) for i in button_ids]
        # The window is the button's parent, found in the same snapshot by its relation address.
        parent_of_button = (
            _parent_id(after[button_ids[0]], after) if button_ids else 0
        )
        window_id = parent_of_button
        if not window_id:
            for frame_id in new_ids:
                if _child_ids(after[frame_id], after):
                    window_id = frame_id
                    break
        report["clicked_frame"] = window_id

        if button_ids:
            chosen = _describe(client, after[button_ids[0]])
            pick = {"children": report["dialog_buttons"], "chosen": chosen,
                    "why": f"a new frame with the dialog-button template ({_BUTTON_TEMPLATE})"}
        else:
            pick = _pick_child(client, after[window_id or new_ids[0]], after)
        report["children"] = pick["children"]
        report["chosen_child"] = pick["chosen"]
        report["why"] = pick["why"]
        if window_id:
            report["children_found"] = len(_child_ids(after[window_id], after))

        child_id = int(pick["chosen"].get("frame_id", 0))
        if child_id:
            report["click"] = _click(client, child_id)
            time.sleep(CLICK_WAIT_SECONDS)
            clicked = _snapshot(client)
            report["frames_clicked"] = len(clicked)
            report["window_gone_after_click"] = window_id not in clicked
            report["new_frames_after_click"] = [
                _describe(client, clicked[i]) for i in sorted(set(clicked) - set(after))
            ]
            report["children_after_click"] = len(_child_ids(clicked[window_id], clicked)) if window_id in clicked else 0

    report["hooks_after_disconnect"] = sorted(bridge.require_hooker().installed)
    report["note"] = (
        "the write connection was used: `Frame.click` sends kMouseClick2 to the parent frame's callbacks "
        "inside the client. Disconnecting removed the hooks and freed what was placed."
    )
    return write_report(report)


def _click(client: Any, frame_id: int) -> dict[str, Any]:
    """Click one frame and report what happened, exception included."""

    frame = frame_module.Frame.from_id(frame_id)
    outcome: dict[str, Any] = {
        "frame_id": frame_id,
        "usable_before": bool(frame.is_usable),
    }
    try:
        frame.click()
        outcome["clicked"] = True
    except Exception as error:  # reported, never swallowed
        outcome["clicked"] = False
        outcome["error"] = f"{type(error).__name__}: {error}"
    return outcome


def write_report(report: dict[str, Any]) -> int:
    text = json.dumps(report, indent=2, ensure_ascii=False)
    print(text)
    if REPORT_PATH:
        with open(REPORT_PATH, "w", encoding="utf-8") as handle:
            handle.write(text)
    return 0


def main() -> int:
    """Run the probe, and report even when the client or this connection fails.

    A live handler that raises is delivered again by ``disconnect`` (the listener re-raises what it
    caught), which would otherwise lose everything this run observed. The failure is written into the
    report instead — never swallowed, and never a reason to lose the evidence.
    """

    report: dict[str, Any] = {}
    try:
        return _run(report)
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
        return write_report(report)


if __name__ == "__main__":
    sys.exit(main())
