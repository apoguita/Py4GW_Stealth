"""``GwAu3_Data_Map.au3``'s **instance** reader, hand-written into the generated module.

Read from ``tools/gwa3_snippets/`` at generation time, the same mechanism `data_party`'s member
accessors use: ``data_map.py`` is rewritten whole on every run.

**What it is.** ``Map_GetInstanceInfo`` (`GwAu3_Data_Map.au3:32-49`) answers *what kind of place the
client is in* -- outpost, explorable, or still loading. It reads one dword: GwAu3 follows its own
``$g_p_InstanceInfo`` pointer (one of the globals it fills by signature scan) to ``+0x4`` and compares it
with three literals. This project reads the same fact through its own member: `Map.GetInstanceType`
(`py4gw/map.py:107`), which is the port's read of the client's instance record
(`py4gw/context/instance_info_context.py`), so the comparison here is the source's own arithmetic over
the same word.

**Why it was needed now.** `py4gw/gwa3/uai_cache.py`'s ``Cache_SkillBar`` opens with
``Map_GetInstanceInfo("IsExplorable")`` (`UtilityAI_Cache.au3:6`), and ``UAI_Fight`` itself gates on
``Map_GetInstanceInfo("Type")`` -- so the engine could not be written without it.
"""


def Map_GetInstanceInfo(info: str = "") -> Any:
    """One field of the client's instance record, by GwAu3's field name
    (``GwAu3_Data_Map.au3:32-49``).

    GwAu3's guard order is kept: an empty key answers ``0`` before anything is read, and an unrecognised
    key answers ``0`` -- its ``Switch`` has no ``Case Else`` and falls through to the same ``Return 0``.

    The three flags are **comparisons of the one word the source compares**, not the port's own
    predicates: ``IsExplorable`` is ``type == 1``, ``IsLoading`` is ``type == 2`` and ``IsOutpost`` is
    ``type == 0``, which is exactly what ``:41-45`` does. A caller that wants the port's richer answer
    wants `Map.IsExplorable`/`Map.IsOutpost` (`py4gw/map.py:126-137`).
    """

    if info == "":
        return 0

    from ..map import Map

    instance_type = int(Map.GetInstanceType())

    if info == "Type":
        return instance_type
    if info == "IsExplorable":
        return instance_type == 1
    if info == "IsLoading":
        return instance_type == 2
    if info == "IsOutpost":
        return instance_type == 0

    return 0


def Map_GetMapID() -> int:
    """The map the client is in (``GwAu3_Data_Map.au3:234-236``).

    GwAu3's own body is one line -- ``Return Map_GetCharacterInfo("MapID")`` -- and this is now that
    line: `Map_GetCharacterInfo` landed with the character-info block reader
    (`tools/gwa3_snippets/data_map_character_info.py`), so the port calls it exactly as the source does
    rather than reaching the same fact through `Map.GetMapID`.

    The value is the client's own current map, which is what the two callers need: ``UAI_Fight`` gates
    on it (``UtilityAI_Core.au3:17,67``), where a map change is one of the five ways its loop ends.
    """

    return int(Map_GetCharacterInfo("MapID"))
