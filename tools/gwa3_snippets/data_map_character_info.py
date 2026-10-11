"""``GwAu3_Data_Map.au3``'s **character-info** reader, hand-written into the generated module.

Read from ``tools/gwa3_snippets/`` at generation time, the same mechanism `data_map`'s instance reader
uses: ``data_map.py`` is rewritten whole on every run.

**What it is.** ``Map_GetCharacterInfo`` (``GwAu3_Data_Map.au3:5-39``) answers one field of the
character context -- the record the client holds while a character is in the world. GwAu3 reaches it
through its own ``Map_GetCharacterContextPtr`` (a pointer it resolves from ``$g_p_CharacterContext``) and
reads fixed offsets. This project reads the **same record** as `CharContextStruct`
(``py4gw/context/char_context.py:245``) through `py4gw.client.RemoteClient.read_char_context`
(``py4gw/client.py:1745``), which is the port's own on-demand read -- nothing here is cached and nothing
is refreshed by a loop.

**The field names line up, and that is why this is parity rather than a re-invention.** GwAu3's
``+0x64`` four-word UUID is the port's ``player_uuid_ptr``; ``+0x74`` ``wchar[20]`` is
``player_name_enc`` (``c_uint16 * 0x14``, the same twenty wide characters); ``+0x190`` is
``world_flags``; ``+0x194`` ``token1``; ``+0x198`` ``map_id``; ``+0x19C`` ``is_explorable``; ``+0x1B8``
``token2``; ``+0x2A8``/``+0x2AC`` are the port's ``player_flags``/``player_number`` pair.

**One finding is recorded rather than smoothed over: the four middle keys are read four bytes earlier by
GwAu3 than this port names them.** GwAu3 reads ``DistrictNumber`` at ``+0x228``, ``Language`` at
``+0x22C``, ``ObserveMapID`` at ``+0x230`` and ``CurrentMapID`` at ``+0x234``; the port's names for those
four sit at ``+0x22C``, ``+0x230``, ``+0x234`` and ``+0x238`` -- one word later -- and GwAu3's own inline
comments on those very lines record *earlier* offsets again (``; 0x220``, ``; 0x224``, ``; 0x228``,
``; 0x22C``), so its offsets have moved at least twice. This member answers the port's names, because a
name is the fact and an offset is where the fact was when the source was written; the disagreement is
written down here and on the member, and a live read is what would settle it.
"""

#: ``{GwAu3 key: reader}`` for the keys that are a single word of the character context. Written as
#: readers rather than as field names, because this project reaches no field through a dynamic name.
_SCALAR_KEYS: dict[str, Any] = {
    "WorldFlags": lambda context: int(context.world_flags),
    "Token1": lambda context: int(context.token1),
    "MapID": lambda context: int(context.map_id),
    "IsExplorable": lambda context: int(context.is_explorable),
    "Token2": lambda context: int(context.token2),
    "DistrictNumber": lambda context: int(context.district_number),
    "Language": lambda context: int(context.language),
    "ObserveMapID": lambda context: int(context.observe_map_id),
    "CurrentMapID": lambda context: int(context.current_map_id),
    "ObserveMapType": lambda context: int(context.observe_map_type),
    "CurrentMapType": lambda context: int(context.current_map_type),
    "PlayerFlags": lambda context: int(context.player_flags),
    "PlayerNumber": lambda context: int(context.player_number),
}


def Map_GetCharacterInfo(info: str = "") -> Any:
    """One field of the character context, by GwAu3's field name (``GwAu3_Data_Map.au3:5-39``).

    GwAu3's guard order is kept: an empty key answers ``0`` before anything is read, an unrecognised key
    answers ``0`` (its ``Switch`` has no ``Case Else``), and a context that cannot be read answers ``0``
    -- which is what its own ``If $l_p_Ptr = 0 ... Then Return 0`` does.

    Three keys are answered the Pythonic way rather than by their offset, and each says what it is:

    * ``PlayerUUID`` -- GwAu3 builds a four-element array of longs at ``+0x64``; this answers the port's
      own four-word ``player_uuid_ptr`` field, the same four words in the same order.
    * ``PlayerName`` -- GwAu3 reads twenty wide characters at ``+0x74`` and hands back the raw buffer;
      this answers the **decoded name** through `Player.GetName` (`py4gw/player.py:491`), which is the
      port's read of that same field and the form a caller can use.
    * ``Region`` -- GwAu3 reads a client global (``$g_p_Region``) rather than the context; this answers
      `Map.GetRegion` (`py4gw/map.py:289`), the port's read of the same fact. GwAu3's key is one number,
      and the port's member answers a pair, so its first element is the number.
    * ``DistrictNumber`` -- the one key whose offsets **disagree**: GwAu3 reads ``+0x228`` and the port
      names ``district_number`` at ``+0x22C`` (with GwAu3's own inline comment on that line recording
      ``; 0x220``, an offset it has since moved from). Rather than pick a word for an offset, this
      answers `Map.GetDistrict` (`py4gw/map.py:309`) -- the port's own read of the fact the key names.

    ``ObserverMatch`` answers ``0`` and names its work: GwAu3 hands back the *pointer* to the observer
    match record, and this layer hands out no address. The pairing is the one the ``Match_*`` family now
    provides -- `Match_GetObserverMatchInfo(match_number, info)` reads the records this key's slot points
    at, by index (`py4gw/gwa3/data_match.py`) -- so the key still answers ``0`` here rather than an
    address dressed up as a record.
    """

    if info == "":
        return 0

    if info == "Region":
        from ..map import Map

        return int(Map.GetRegion()[0])

    if info == "DistrictNumber":
        from ..map import Map

        return int(Map.GetDistrict())

    if info == "PlayerName":
        from ..player import Player

        return str(Player.GetName())

    context = require_client().read_char_context()
    if context is None:
        return 0

    if info == "PlayerUUID":
        return [int(word) for word in context.player_uuid_ptr]

    reader = _SCALAR_KEYS.get(info)
    if reader is not None:
        return reader(context)

    # `ObserverMatch` and anything unrecognised: GwAu3's own `Return 0`.
    return 0
