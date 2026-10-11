"""``GwAu3_Data_Match.au3``'s **observer-match** reader, hand-written into the generated module.

Read from ``tools/gwa3_snippets/`` at generation time by ``tools/generate_gwa3_family.py``, the same
mechanism the map and party snippets use: ``data_match.py`` is rewritten whole on every run, so a function
written straight into it would be lost the next time the generator ran.

**What it is.** ``Match_GetObserverMatchInfo`` (``GwAu3_Data_Match.au3:11-66``) answers one field of one
observer-match record -- the record the client holds while a match is being observed. GwAu3 resolves the
record first: ``Match_GetObserverMatchPtr`` (``:4-9``) walks ``$g_p_BasePointer`` by ``[0, 0x18, 0x44,
0x24C]`` and reads the pointer at ``+ ($a_i_MatchNumber * 4)`` of the table it lands on. This project reads
the **same records** through its own reader: `CharContextStruct.observer_matches`
(``py4gw/context/char_context.py:263-271``) walks the character context's ``observer_matches_array``
(``+0x258``, `py4gw/context/char_context.py:190`) and materializes each entry as `ObserverMatch`
(``:50-63``), bound to the reader so the two team-name pointers can be followed.

**The pairing convention, which is what ``Map_GetCharacterInfo("ObserverMatch")`` means.** GwAu3 hands back
the *pointer* to a match record there; this layer hands out no address, so that key answers ``0`` and names
its work (``tools/gwa3_snippets/data_map_character_info.py:71-75``, `py4gw/gwa3/data_map.py:356-358`). The
pairing is **the list of match records, indexed**: this family's first argument is the index into
`CharContextStruct.observer_matches` -- the array GwAu3's pointer table indexes -- and the record itself is
the answer, never an address.

**The record's own offsets line up key for key.** ``match_id`` ``+0x0``, ``match_id_dup`` ``+0x4``,
``map_id`` ``+0x8``, ``age`` ``+0xC``, then the fourteen words of `ObserverMatchFlags`
(``py4gw/context/char_context.py:33-46``) -- ``type`` ``+0x10`` through ``data2`` ``+0x44`` -- which is
every ``long`` GwAu3 reads at ``:16-51``. The port's ``team_name1_ptr`` is ``+0x48`` (GwAu3's
``TeamNamesPtr``), its ``team_name2_ptr`` is ``+0x74`` (its ``TeamNames2Ptr``), and its ``unknown1``
(``+0x4C``, ten words) is the gap GwAu3 never reads between them.

**One of GwAu3's own constants for this family disagrees with another, and the port's is the later one.**
Its chain ends at ``0x24C`` (``:5``) while the same project's research record already has the field as
``read at +0x254, dereferenced at +0x24C``, marked *self-contradictory* (``docs/RESEARCH.md:4365``). This
port's ``observer_matches_array`` sits at ``+0x258``, the offset the client update moved it to
(``docs/HANDOVER_GW_2026-09-30_UPDATE.md:216``), and the records are answered from there. The number is a
finding for the owner, not something reconciled by arithmetic here.

**Two keys refuse, and they are the two pointer keys.** ``TeamNamesPtr`` (``:52-53``) and
``TeamNames2Ptr`` (``:57-58``) answer a client *address*; this layer hands out none, and the two strings a
caller wants from them are answered by ``Team1Name``/``Team2Name``. ``Match_CleanTeamName`` (``:68-73``) is
declared in the same file and no script calls it -- its effect lives inside the port's two name reads -- so
it is not a member here.
"""


def _observer_match(client: Any, match_number: Any) -> Any:
    """The observer-match record at one index, from the character context read **now**.

    ``Match_GetObserverMatchPtr`` (``GwAu3_Data_Match.au3:4-9``) resolves the record from a pointer table
    indexed by ``$a_i_MatchNumber * 4`` (`:8`). This project's reader answers the same records as a list
    (`CharContextStruct.observer_matches`), so the index is the same index and a record the list does not
    hold is GwAu3's own "the pointer read answered zero" case -- ``None`` here, which its one guard answers
    ``0`` for (`:13`). Nothing is cached: a stored record is a dereferenced read, and this project keeps
    none.
    """

    matches = client.read_char_context().observer_matches
    if matches is None:
        return None
    index = int(match_number)
    if index < 0 or index >= len(matches):
        return None
    return matches[index]


def Match_GetObserverMatchInfo(match_number: Any = 0, info: str = "") -> Any:
    """One field of one observer-match record (``GwAu3_Data_Match.au3:11-66``).

    GwAu3's guard order is kept: the record is resolved first (`:12`) and its absence and an empty key are
    one guard (`:13`) -- so an empty key answers ``0`` only after the character context has been read, and a
    caller with no connection is refused by this project's own `require_client` before either test. An
    unrecognised key answers ``0``, which is GwAu3's own ``Return 0`` after its ``Switch`` (`:65`).

    The eighteen ``long`` keys are the record's own fields, offset for offset (`:16-51`), fourteen of them
    through the port's `ObserverMatchFlags`. The two team-name keys answer the port's own reads of the same
    two buffers: GwAu3 reads ``wchar[256]`` at the pointer and runs ``Match_CleanTeamName`` over it
    (`:54-56`, `:59-61`), and this answers `team_name1_str`/`team_name2_str`
    (`py4gw/context/char_context.py:96`, `:109`), which is that buffer with the encoded values kept visible
    as escapes rather than stripped of them, and ``""`` where a pointer the client does not hold gives
    GwAu3 its empty wide read.

    ``TeamNamesPtr`` and ``TeamNames2Ptr`` refuse, each naming the read that answers what a caller wants
    from the address.
    """

    match = _observer_match(require_client(), match_number)
    if match is None or info == "":
        return 0

    if info == "MatchID":
        return int(match.match_id)
    if info == "MatchIDDup":
        return int(match.match_id_dup)
    if info == "MapID":
        return int(match.map_id)
    if info == "Age":
        return int(match.age)

    # GwAu3's ``+0x10``..``+0x44`` are the fourteen words of the port's `ObserverMatchFlags`, in its own
    # order (`py4gw/context/char_context.py:33-46`).
    if info == "Type":
        return int(match.flags.type)
    if info == "Reserved":
        return int(match.flags.reserved)
    if info == "Version":
        return int(match.flags.version)
    if info == "State":
        return int(match.flags.state)
    if info == "Level":
        return int(match.flags.level)
    if info == "Config1":
        return int(match.flags.config1)
    if info == "Config2":
        return int(match.flags.config2)
    if info == "Score1":
        return int(match.flags.score1)
    if info == "Score2":
        return int(match.flags.score2)
    if info == "Score3":
        return int(match.flags.score3)
    if info == "Stat1":
        return int(match.flags.stat1)
    if info == "Stat2":
        return int(match.flags.stat2)
    if info == "Data1":
        return int(match.flags.data1)
    if info == "Data2":
        return int(match.flags.data2)

    if info == "TeamNamesPtr":
        # GwAu3 reads the pointer at ``+0x48`` and hands it back (`:52-53`). This layer answers no client
        # address, and the field is one the port already names -- so it refuses, citing both.
        raise NotImplementedError(
            "GwAu3_Data_Match.au3:52-53 answers the client **address** held at record ``+0x48``. This "
            "project names that field `team_name1_ptr` (`py4gw/context/char_context.py:60`) and this layer "
            "hands out no address: the string a caller wants from it is `Team1Name`, which reads through "
            "the same pointer as `team_name1_str` (`py4gw/context/char_context.py:96`)."
        )

    if info == "Team1Name":
        return match.team_name1_str or ""

    if info == "TeamNames2Ptr":
        # The same shape at ``+0x74`` (`:57-58`).
        raise NotImplementedError(
            "GwAu3_Data_Match.au3:57-58 answers the client **address** held at record ``+0x74``. This "
            "project names that field `team_name2_ptr` (`py4gw/context/char_context.py:62`) and this layer "
            "hands out no address: the string a caller wants from it is `Team2Name`, which reads through "
            "the same pointer as `team_name2_str` (`py4gw/context/char_context.py:109`)."
        )

    if info == "Team2Name":
        return match.team_name2_str or ""

    # GwAu3's own `Return 0` for anything its `Switch` does not match (`:65`).
    return 0
