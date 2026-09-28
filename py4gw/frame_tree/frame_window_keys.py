"""Port of Reforged's ``Py4GWCoreLib/FrameTree/frame_window_keys.py`` (20 lines).

The window frame keys: the window names this library reaches frames by. A verbatim transcription — the
source file has no imports, no functions and no computed values, so the body is its own bytes.
"""

"""Legacy WindowFrames names -> registry keys.

Hand-maintained (not generated), for the few callers that select a frame by a
runtime string rather than by a FrameId constant.
"""

WINDOW_FRAME_KEYS: dict[str, str] = {
    "Inventory Bags": "InventoryBagsWindow",
    "MiniMap": "Compass",
    "PartyWindow": "PartyFormation",
    "CancelEnterMissionButton": "MissionStatusAndScoreDisplay.C0.C1.CancelEnterMissionButton",
    "ConfirmEnterMissionButton": "Root.C2.C6.C100.C2.ConfirmEnterMissionButton",
    "DeleteCharacterButton": "DeleteButton",
    "FinalDeleteCharacterButton": "ScreenFrame.Child.CharacterSelectFrame.DeleteCharacterFrame.DeleteButton",
    "CreateCharacterButton1": "CreateButton",
    "CreateCharacterButton2": "CreateButtonGreyedOut",
    "CreateCharacterTypeNextButton": "NextButton",
    "CreateCharacterNextButtonGeneric": "NextButton2",
    "FinalCreateCharacterButton": "CreateButton2",
}
