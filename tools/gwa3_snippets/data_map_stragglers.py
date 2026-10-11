"""``GwAu3_Data_Map.au3``'s **stragglers**: the click coordinates, the move coordinates and the map-unlock test.

Read from ``tools/gwa3_snippets/`` at generation time, the same mechanism `data_map_character_info.py`
and `data_map_current_area.py` use: ``data_map.py`` is rewritten whole on every run.

**What is here, and where each answer comes from.**

* ``Map_GetLastMoveCoords`` (``GwAu3_Data_Map.au3:19-22``) answers two **controller-side globals**,
  ``$g_f_LastMoveX``/``$g_f_LastMoveY``. They are not client memory and there is nothing in the client
  to read for them: GwAu3 declares them ``Global $g_f_LastMoveX = 0`` / ``= 0``
  (``GwAu3_Const_Core.au3:135-136``), resets them at ``GwAu3_Core.au3:704-705``, and its own move
  function stores the point it decided on there (``GwAu3_Cmd_Map.au3:11-12``). So this layer
  **transcribes the state**, the way ``py4gw/gwa3/uai_const.py`` transcribes the UtilityAI plugin's own
  mutable globals -- and this layer's own ``Map_Move`` (``py4gw/gwa3/cmd_map.py:55``) is the function
  that stores them here too, with GwAu3's two assignments at ``GwAu3_Cmd_Map.au3:11-12`` as its model.
  **Without that writer the member below is a constant ``[0.0, 0.0]``**, which is why the two lines are
  part of this port rather than an optional extra.
* ``Map_GetClickCoords`` (``:24-29``) reads two client floats that GwAu3 resolves by its own signature
  scan (``$g_f_ClickCoordsX``/``$g_f_ClickCoordsY``, wired at ``GwAu3_Core.au3:293-294``). This project
  has no resolver for that pattern; it reads the same fact from the client's own record instead, and
  says so on the member.
* ``Map_IsMapUnlocked`` (``:386-406``) is parity: GwAu3's hand-written walk of the world context's
  unlock bitfield against this project's member of the same name, ``Map.IsMapUnlocked``.

``Map_GetCurrentRegionType`` is **not** here: it was already ported
(`tools/gwa3_snippets/data_map_current_area.py:68`, exported by the ``data_map`` family), and this file
does not restate it.
"""

#: ``GwAu3_Const_Core.au3:135-136`` -- GwAu3's own last-move coordinates, transcribed as module state.
#:
#: These are **controller-side**, not client memory: GwAu3's own move function writes the point it
#: decided on into them (``GwAu3_Cmd_Map.au3:11-12``, *after* the randomisation its own ``Map_Move``
#: applies), its cleanup returns them to ``0`` (``GwAu3_Core.au3:704-705``), and the file declared here
#: starts them at ``0``. The names keep GwAu3's spelling with the leading ``$`` dropped, which is the
#: convention ``py4gw/gwa3/constants.py`` already uses for its names.
#:
#: **The writer is part of this port**: ``Map_Move`` (``py4gw/gwa3/cmd_map.py:55``) stores the two
#: coordinates it passed to ``Player.Move`` here, with GwAu3's own two assignments as the model
#: (``GwAu3_Cmd_Map.au3:11-12``). ``Map_MoveLayer`` writes neither, in either project. If those two
#: assignments are not in ``Map_Move``, the reader below answers a constant ``[0.0, 0.0]`` -- a wrong
#: value of the right type, which is why they are not optional.
#:
#: **They live with their reader rather than in a module of their own.** ``py4gw/gwa3/uai_const.py`` is
#: the precedent for transcribing a ``Global`` -- the generated ``constants.py`` reads ``Global Const``
#: and ``Global Enum`` only, deliberately, because a ``Global`` is state -- but that module exists
#: because many ported plugin modules read and write the same settings. Here one member reads this pair
#: (`Map_GetLastMoveCoords`) and one function writes it (`Map_Move`), and the file that *declares* them
#: (``GwAu3_Const_Core.au3``) declares exactly two more globals of this group --
#: ``$g_f_ClickCoordsX``/``$g_f_ClickCoordsY`` (``:137-138``) -- which are client addresses GwAu3
#: resolves by its own scan and this layer answers from the client's own record, so there is no second
#: reader a ``GwAu3_Const_Core.au3`` module would be shared with.
g_f_LastMoveX: float = 0.0
g_f_LastMoveY: float = 0.0


def Map_GetLastMoveCoords() -> list[float]:
    """The coordinates of the last move this layer sent (``GwAu3_Data_Map.au3:19-22``).

    GwAu3's whole body is the two-element array it builds from its own globals
    (``$g_f_LastMoveX``/``$g_f_LastMoveY``, ``GwAu3_Const_Core.au3:135-136``), and this answers the same
    two numbers from the transcription above -- the values `Map_Move` stored, which is where GwAu3
    stores them (``GwAu3_Cmd_Map.au3:11-12``). The array shape is GwAu3's: two floats, x first.

    **One thing a caller has to know.** These are *this layer's* record of *its own* moves, so the pair
    is ``[0.0, 0.0]`` until a move has been made through it, exactly as GwAu3's start at ``0``
    (``GwAu3_Const_Core.au3:135-136``) and return to ``0`` on cleanup (``GwAu3_Core.au3:704-705``).
    The one writer in either project is the move function of that name -- `Map_Move`, storing the two
    coordinates it handed to the client (`GwAu3_Cmd_Map.au3:11-12`; ``py4gw/gwa3/cmd_map.py:55`` is this
    layer's copy of it, and those two assignments are part of its port). `Map_MoveLayer` writes neither,
    in either project.
    """

    return [float(g_f_LastMoveX), float(g_f_LastMoveY)]


def Map_GetClickCoords() -> list[float]:
    """The client's last click coordinates (``GwAu3_Data_Map.au3:24-29``).

    GwAu3 reads two floats at client globals it resolved by its own scan pattern
    (``$g_f_ClickCoordsX``/``$g_f_ClickCoordsY``, wired at ``GwAu3_Core.au3:293-294``). **This project
    has no reader for those two addresses** -- ``offsets/`` carries no entry for that scan and this
    layer reads no address it did not resolve -- but it reads the same fact from the client's own
    record: the mission-map context's ``last_mouse_location``, through `Map.MissionMap.GetLastClickCoords`
    (``py4gw/map.py:1052``). That is the member this project's own doc already cites GwAu3's two lines as
    corroboration for (``py4gw/map.py:1078-1083``). The array shape is GwAu3's: two floats, x first.

    **The divergence is the port's own recorded one, not a new one**: that member answers *the mouse
    location now*, because the IO-event gate that would pin it to the moment of the click is the
    injected runtime's ImGui context and is unreachable here (``py4gw/map.py:1063-1077``). The two agree
    whenever the mouse has not moved since the click, and differ otherwise.
    """

    from ..map import Map

    return [float(value) for value in Map.MissionMap.GetLastClickCoords()]


def Map_IsMapUnlocked(a_i_MapID: Any) -> bool:
    """Whether the client has a map unlocked (``GwAu3_Data_Map.au3:386-406``).

    **Parity, key for key.** GwAu3 walks the world context's unlock bitfield by hand: the array at
    ``+0x60C``, its buffer and ``m_size`` words, ``False`` when either is empty, ``False`` when
    ``Floor(map_id / 32)`` is past the end, and then the bit test
    ``BitAND(array[map_id / 32], 1 << (map_id % 32)) <> 0`` (``:389-405``). This layer has the same
    member -- `Map.IsMapUnlocked` (``py4gw/map.py:506``) -- which makes exactly that walk over the same
    array (`WorldContextStruct.unlocked_maps`, ``py4gw/context/world_context.py:1940``; the array is
    declared at ``+0x60C``, ``:1491``), with the same four guards and the same answer.

    No default argument, because GwAu3's own declaration has none (``:386``) -- the ported member's
    ``mapid: int | None = None`` is not taken here, since a migrating call always passes the id.
    """

    from ..map import Map

    return bool(Map.IsMapUnlocked(a_i_MapID))
