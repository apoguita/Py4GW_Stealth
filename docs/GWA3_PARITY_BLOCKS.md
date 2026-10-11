# The same routine, in AutoIt and in the port

**Generated** by `python tools/report_gwa3_parity_blocks.py` -- the AutoIt side is read from `external/GwAu3`, the Python side from the layer with `inspect.getsource`, so this cannot describe anything but the code as it stands.

A migrated script keeps its own AutoIt body; these pairs put GwAu3's routine beside the Stealth member that answers the same call, so the shape can be compared directly.

## `Map_Move`

*AutoIt: `external/GwAu3/API/Cmd/GwAu3_Cmd_Map.au3`*

```autoit
Func Map_Move($a_f_X, $a_f_Y, $a_f_Randomize = 50)
    ; Add randomization if requested
    If $a_f_Randomize > 0 Then
        $a_f_X += Random(-$a_f_Randomize, $a_f_Randomize)
        $a_f_Y += Random(-$a_f_Randomize, $a_f_Randomize)
    EndIf

    ; Store last move coordinates
    $g_f_LastMoveX = $a_f_X
    $g_f_LastMoveY = $a_f_Y

    ; Set move data
    DllStructSetData($g_d_Move, 2, $a_f_X)
    DllStructSetData($g_d_Move, 3, $a_f_Y)
    DllStructSetData($g_d_Move, 4, 0)  ; Z coordinate (usually 0)

    Core_Enqueue($g_p_Move, 16)

    Return True
EndFunc
```

*Ported:*

```python
def Map_Move(x: float, y: float, randomize: float = 50) -> bool:
    """Move to a point, with GwAu3's own randomisation (``GwAu3_Cmd_Map.au3:2-25``).

    **GwAu3's randomisation is part of this function and is kept.** Its own default is
    ``$a_f_Randomize = 50``, and when it is above zero it adds ``Random(-r, r)`` to each coordinate
    *before* storing them -- so the destination is never exactly the point asked for. The layer keeps
    that, because a migrating script's ``Map_Move($x, $y)`` is asking for GwAu3's wobble as much as for
    the destination. ``Player.Move`` (``py4gw/player.py:1188``) is handed the point this function
    decided on, which is the same division of labour as GwAu3's.
    """

    if randomize > 0:
        x += random.uniform(-randomize, randomize)
        y += random.uniform(-randomize, randomize)

    # `GwAu3_Cmd_Map.au3:10-12` stores the point it decided on -- after the randomisation, before the
    # move is sent -- and `Map_GetLastMoveCoords` answers that pair. It reads it from `data_map`, the
    # module of the source file that declares the reader (`GwAu3_Data_Map.au3:19-22`), so the layer's
    # transcription of `$g_f_LastMoveX/Y` lives where its reader lives. Without these two lines the
    # reader would answer the pair it was initialised with for ever.
    from . import data_map

    data_map.g_f_LastMoveX = x
    data_map.g_f_LastMoveY = y

    Player.Move(x, y, 0)
    return True
```

## `Merchant_IsValidQuote`

*AutoIt: `external/GwAu3/API/Modules/Data/GwAu3_Data_Merchant.au3`*

```autoit
Func Merchant_IsValidQuote()
    Local $l_i_CostID = Memory_Read($g_i_TraderCostID, 'dword')
    Local $l_i_CostValue = Memory_Read($g_f_TraderCostValue, 'dword')
    Return ($l_i_CostID > 0 And $l_i_CostValue > 0)
EndFunc
```

*Ported:*

```python
def Merchant_IsValidQuote() -> bool:
    """Whether a quote is standing (``GwAu3_Data_Merchant.au3:28-32``).

    GwAu3's own two reads and its own test, in its own order: the cost id, then the cost value, then
    ``cost id > 0 And cost value > 0`` (``:29-31``). Both values come from the same two routed members
    the getters above answer from, so the boolean is the source's own arithmetic over the port's state --
    including its answer for the states that matter: no quote yet is ``False`` on both sides, and a
    quote is ``True`` on both.
    """

    from ..merchant import Trading

    cost_id = int(Trading.Trader.GetQuotedItemID())
    cost_value = int(Trading.Trader.GetQuotedValue())
    return cost_id > 0 and cost_value > 0
```

## `World_IsSkillLearnt`

*AutoIt: `external/GwAu3/API/Modules/Data/GwAu3_Data_World.au3`*

```autoit
Func World_IsSkillLearnt($a_i_SkillID)
    Local $l_p_WorldContext = World_GetWorldContextPtr()
    If $l_p_WorldContext = 0 Then Return False

    Local $l_p_UnlockedSkillsArray = Memory_Read($l_p_WorldContext + 0x710, "ptr")
    If $l_p_UnlockedSkillsArray = 0 Then Return False

    Local $l_i_ArraySize = Memory_Read($l_p_WorldContext + 0x710 + 0x8, "long")

    Local $l_i_RealIndex = Floor($a_i_SkillID / 32)

    If $l_i_RealIndex >= $l_i_ArraySize Then Return False

    Local $l_i_Shift = Mod($a_i_SkillID, 32)
    Local $l_i_Flag = BitShift(1, -$l_i_Shift)

    Local $l_i_Value = Memory_Read($l_p_UnlockedSkillsArray + ($l_i_RealIndex * 4), "dword")

    Return BitAND($l_i_Value, $l_i_Flag) <> 0
EndFunc
```

*Ported:*

```python
def World_IsSkillLearnt(a_i_SkillID: Any) -> bool:
    """Whether the character has learnt a skill (``GwAu3_Data_World.au3:214-233``).

    GwAu3's guard order is kept term for term: no world context answers ``False`` (``:216``), an
    unlocked-skills array that is not there answers ``False`` (``:219``), an index past the end answers
    ``False`` (``:225``), and the answer is the bit test over the word the id lands in --
    ``BitAND(word, 1 << (skill_id % 32)) <> 0`` with ``word = array[Floor(skill_id / 32)]``
    (``:227-232``).

    The array is the same one, read the way this project reads it: GwAu3 takes the ``ptr`` and ``size``
    of the ``Array<dword>`` at ``+0x710`` (``:218``, ``:221``) and this reads that word of the world
    context as the list of ``uint32`` words it holds
    (`WorldContextStruct.unlocked_character_skills`, ``py4gw/context/world_context.py:1897``, declared
    at ``+0x710``, ``:1511``) -- the same bitfield, indexed and masked the same way.
    """

    world = require_client().read_world_context()
    if world is None:
        return False

    unlocked = world.unlocked_character_skills
    if not unlocked:
        return False

    real_index = int(a_i_SkillID) // 32
    if real_index >= len(unlocked):
        return False

    shift = int(a_i_SkillID) % 32
    flag = 1 << shift
    return (int(unlocked[real_index]) & flag) != 0
```

## `Map_GetCharacterInfo`

*AutoIt: `external/GwAu3/API/Modules/Data/GwAu3_Data_Map.au3`*

```autoit
Func Map_GetCharacterInfo($a_s_Info = "")
    Local $l_p_Ptr = Map_GetCharacterContextPtr()
    If $l_p_Ptr = 0 Or $a_s_Info = "" Then Return 0

    Switch $a_s_Info
        Case "PlayerUUID"
            Local $l_ai_UUID[4]
            For $l_i_Idx = 0 To 3
                $l_ai_UUID[$l_i_Idx] = Memory_Read($l_p_Ptr + 0x64 + ($l_i_Idx * 4), "long")
            Next
            Return $l_ai_UUID
        Case "PlayerName"
            Return Memory_Read($l_p_Ptr + 0x74, "wchar[20]")
        Case "WorldFlags"
            Return Memory_Read($l_p_Ptr + 0x190, "long")
        Case "Token1" ; World ID
            Return Memory_Read($l_p_Ptr + 0x194, "long")
        Case "MapID"
            Return Memory_Read($l_p_Ptr + 0x198, "long")
        Case "IsExplorable"
            Return Memory_Read($l_p_Ptr + 0x19C, "long")
        Case "Token2" ; Player ID
            Return Memory_Read($l_p_Ptr + 0x1B8, "long")
        Case "DistrictNumber"
            Return Memory_Read($l_p_Ptr + 0x228, "long") ; 0x220
        Case "Language"
            Return Memory_Read($l_p_Ptr + 0x22C, "long") ; 0x224
        Case "Region"
            Return Utils_MakeInt32(Memory_Read($g_p_Region))
        Case "ObserveMapID"
            Return Memory_Read($l_p_Ptr + 0x230, "long") ; 0x228
        Case "CurrentMapID"
            Return Memory_Read($l_p_Ptr + 0x234, "long") ; 0x22C
        Case "ObserveMapType"
            Return Memory_Read($l_p_Ptr + 0x238, "long") ; 0x230
        Case "CurrentMapType"
            Return Memory_Read($l_p_Ptr + 0x23C, "long") ; 0x234
        Case "ObserverMatch"
            Return Memory_Read($l_p_Ptr + 0x254, "ptr") ; 0x24C
        Case "PlayerFlags"
            Return Memory_Read($l_p_Ptr + 0x2A8, "long") ; 0x2A0
        Case "PlayerNumber"
            Return Memory_Read($l_p_Ptr + 0x2AC, "long") ; 0x2A4
    EndSwitch

    Return 0
EndFunc
```

*Ported:*

```python
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
```

## `Party_GetMoraleInfo`

*AutoIt: `external/GwAu3/API/Modules/Data/GwAu3_Data_Party.au3`*

```autoit
Func Party_GetMoraleInfo($a_v_AgentID = -2, $a_s_Info = "")
    Local $l_i_AgentID = Agent_ConvertID($a_v_AgentID)

    Local $l_ai_Offset[4] = [0, 0x18, 0x2C, 0x638]
    Local $l_ai_Index = Memory_ReadPtr($g_p_BasePointer, $l_ai_Offset)

    ReDim $l_ai_Offset[6]
    $l_ai_Offset[3] = 0x62C
    $l_ai_Offset[4] = 8 + 0xC * BitAND($l_i_AgentID, $l_ai_Index[1])
    $l_ai_Offset[5] = 0x18
    Local $l_av_Return = Memory_ReadPtr($g_p_BasePointer, $l_ai_Offset)

    If Not IsArray($l_av_Return) Or $l_av_Return[0] = 0 Then Return 0

    Switch $a_s_Info
        Case "Morale"
            Return $l_av_Return[1] - 100
        Case "RawMorale"
            Return $l_av_Return[1]
        Case "IsMaxMorale"
            Return ($l_av_Return[1] >= 110)
        Case "IsMinMorale"
            Return ($l_av_Return[1] <= 40)
        Case "IsMoraleBoost"
            Return ($l_av_Return[1] > 100)
        Case "IsMoralePenalty"
            Return ($l_av_Return[1] < 100)
        Case Else
            Return 0
    EndSwitch
EndFunc
```

*Ported:*

```python
def Party_GetMoraleInfo(agent_id: Any = -2, info: str = "") -> Any:
    """One field of one agent's **morale** record (``GwAu3_Data_Party.au3:202-232``).

    GwAu3 converts the id first (``:203``, so ``-2`` is the controlled character), indexes its morale
    array with the id and reads one word; a record it cannot resolve answers ``0`` before the switch
    (``:214``), and its ``Case Else`` answers ``0`` for an unrecognised key (``:229-230``) -- an empty
    key included, which is why the empty key is **not** guarded first here, unlike the source's other
    accessors. ``Morale`` is that word less ``100`` and the four flag keys are comparisons on the raw
    word (``>= 110``, ``<= 40``, ``> 100``, ``< 100``), each answered as the source's own boolean.

    This walks `Party.GetPartyMorale` (`py4gw/party.py:1024-1047`) -- the port's read of the same
    links-and-records chain, whose word is this record's own ``morale`` -- and takes the pair whose
    agent id matches. GwAu3 hashes the id; this scans a list, the same fact answered the port's way. The
    port's member also skips entries whose agent id does not resolve as a live agent
    (``Party.GetPartyMorale``'s own guard), so an id GwAu3 would still index answers ``0`` here.
    """

    from ..party import Party
    from .data_agent import Agent_ConvertID

    resolved = int(Agent_ConvertID(agent_id))

    raw = None
    for member_agent_id, morale in Party.GetPartyMorale():
        if int(member_agent_id) == resolved:
            raw = int(morale)
            break

    if raw is None:
        return 0

    if info == "Morale":
        return raw - 100
    if info == "RawMorale":
        return raw
    if info == "IsMaxMorale":
        return raw >= 110
    if info == "IsMinMorale":
        return raw <= 40
    if info == "IsMoraleBoost":
        return raw > 100
    if info == "IsMoralePenalty":
        return raw < 100

    return 0
```

