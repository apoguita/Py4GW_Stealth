"""``GwAu3_Data_Agent.au3``'s **visible-effect** readers, hand-written into the generated module.

Read from ``tools/gwa3_snippets/`` at generation time by ``tools/generate_gwa3_data_agent.py``, the same
mechanism `data_agent`'s effect-column reader and `_ApplyFilters` use: ``data_agent.py`` is rewritten
whole on every run, so a function written straight into it would be lost the next time the generator ran.

**The source file, because the task that asked for this named one that does not exist.** There is no
``GwAu3_Data_VisibleEffect.au3`` anywhere under ``external/GwAu3``: the three readers are declared in
``GwAu3_Data_Agent.au3`` -- ``VisibleEffect_Count`` at ``:1143-1159``, ``VisibleEffect_GetAll`` at
``:1161-1189`` and ``VisibleEffect_FindByID`` at ``:1191-1217`` -- between the ``#Region Visible Effect``
marker (``:1121``) and its end, which is also where the three ``Agent_*`` wrappers that call them live
(``Agent_CountVisibleEffects`` ``:1122-1124``, ``Agent_GetAllVisibleEffects`` ``:1126-1136``,
``Agent_HasVisibleEffect`` ``:1138-1141``). ``docs/GWA3_ROUTE_MAP.md:264``, ``:1008`` and ``:1009`` cite
the same file and the same lines. Their home module is therefore this one, the source file's own module.

**The walk is not written here, because this project already has it.** All three readers answer from the
same ported walk: `py4gw/gwa3/uai_effects.py:363` ``_visible_effects(agent_id)``, which reads the agent's
record through `Agent_GetAgentPtr` (this module, ``:674``) and walks the list at
``AgentLivingStruct.visible_effects_list`` -- ``+0x174``, the very offset GwAu3's own
``Agent_GetAgentInfo(..., "VisibleEffectsPtr")`` answers (``py4gw/context/agent_array.py:885``) --
through `RemoteGWListView` into `VisibleEffectStruct` records (``py4gw/context/agent_array.py:808-835``).
Those three dwords land exactly where GwAu3's ``UAI_GetVisibleEffectStruct`` puts them
(``UtilityAI_EffectsCache.au3:76-82``): the port calls the first ``unk`` where the source calls it
``EffectType``, and that is the only field-name difference.

**The record column is answered as the record.** GwAu3 puts the node's own **address** in
``VisibleEffect_GetAll``'s first column (``:1176``) and in ``VisibleEffect_FindByID``'s second cell
(``:1206``); this layer hands out no client address, so both answer the materialized
`VisibleEffectStruct` the row's other cells are read from -- the same substitution `Item_GetItemPtr` and
`Agent_GetAgentPtr` record. The column **order** is GwAu3's and is kept, because a caller indexes it:
``Agent_GetAllVisibleEffects`` reads ``[2]`` for the effect id (``:1132``) and ``Agent_HasVisibleEffect``
reads ``[0]`` of the ``FindByID`` result (``:1140``).

**One bound differs, and the difference is the walk's.** GwAu3's ``GetAll`` stops after **100** nodes
because its row array is ``[101][4]`` (``:1173``); the port's walk is bounded by its own reader at
``_MAX_VISIBLE_EFFECTS`` -- 128 (``py4gw/context/agent_array.py:841``) -- so the source's 100-row cap is
applied here, on top of the walk, and an agent carrying more than 100 visible effects is answered from
its first 100, exactly as the source answers it.

**``Utils_TList_CreateIterator``, ``Utils_TList_Iterator_Current``, ``Utils_TList_Iterator_Next`` and
``Utils_TLink_IsLinked`` are carried, in `py4gw/gwa3/core_utils.py`.**
``GwAu3_Core_Utils.au3:88-141`` builds an AutoIt array of **client addresses** (the sentinel is
``$a_p_TListPtr + 0x4``), steps it through the XOR-linked list and answers the next node's address
(``Utils_TList_Iterator_Current`` returns the dword at ``+0x4``), and ``Utils_TLink_IsLinked`` answers
whether an address's prev-link differs from the address itself. This module is the reason they could be
answered at all: the walk they need is the port's
(`py4gw/gwa3/uai_effects.py:363`, over `py4gw/context/agent_array.py:935`), and what they iterate in
`core_utils.py` is **the list that walk answers** -- the port's records -- rather than node addresses this
layer does not hand out. Their only callers in GwAu3 are the plugin's effect cache
(``UtilityAI_EffectsCache.au3:119-134``) and the two ``Tools_VisibleEffect`` scripts, both walking the
visible-effect list the three readers below read.
"""


def VisibleEffect_Count(a_i_AgentID: Any = -2) -> int:
    """How many visible effects an agent carries (``GwAu3_Data_Agent.au3:1143-1159``).

    GwAu3's guard is its own line, kept verbatim: ``If Agent_GetAgentInfo($a_i_AgentID, "Type") <> 0xDB
    Then Return 0`` (``:1144``) -- a living agent, by the type word this port also reads as ``0xDB``
    (`Agent_GetAgentInfo`, this module, ``py4gw/gwa3/data_agent.py:725``; the type test itself at
    ``:207-210``) -- and an agent the client does not hold answers ``0`` from the same call.

    The count is the walk's own length: GwAu3 counts the nodes of the TList at ``VisibleEffectsPtr``
    (``:1146-1156``); `_visible_effects` (`py4gw/gwa3/uai_effects.py:363`) walks that same list from the
    agent's record, so its length is the same number. **This is the member `VisibleEffectCount` and
    `HasVisibleEffects` were waiting on** -- both of those keys of `Agent_GetAgentInfo` still refuse
    (`py4gw/gwa3/data_agent.py:48`) and can now be routed onto this one.
    """

    from .uai_effects import _visible_effects

    if int(Agent_GetAgentInfo(a_i_AgentID, "Type")) != 0xDB:
        return 0

    return len(_visible_effects(a_i_AgentID))


def VisibleEffect_GetAll(a_i_AgentID: Any = -2) -> Any:
    """Every visible effect of an agent, as rows behind a row carrying the count
    (``GwAu3_Data_Agent.au3:1161-1189``).

    **Both of GwAu3's answers are kept, and they are not the same type.** An agent whose type word is
    not ``0xDB`` answers the scalar ``0`` (``:1165``); a living agent answers an AutoIt 2-D array
    ``[1 + count][4]`` whose row ``0`` is ``(count, 0, 0, 0)`` and whose remaining rows are
    ``(node, unk, id, has_ended)`` (``:1176-1186``), a living agent with no nodes answering the
    1-row array ``(0, 0, 0, 0)`` -- which is why the guard cannot be dropped in favour of the walk's
    empty list, the walk's answer being an array where the source's is a number. The rows are answered
    as a list of rows, the same substitution `UAI_GetAgentVisibleEffectInfo` makes.

    The three dwords are the ported record's own fields -- ``unk`` at ``+0x0``, ``id`` at ``+0x4``,
    ``has_ended`` at ``+0x8`` (``py4gw/context/agent_array.py:808-816``) -- and the first cell of each
    row is the **record itself** where GwAu3 puts the node's address (``:1176``): this layer answers no
    address, and the record is what the row's other three cells were read from. The source's 100-node
    cap is applied (``:1173``).
    """

    from .uai_effects import _visible_effects

    if int(Agent_GetAgentInfo(a_i_AgentID, "Type")) != 0xDB:
        return 0

    effects = _visible_effects(a_i_AgentID)[:100]

    rows: list[Any] = [[0, 0, 0, 0]]
    for record in effects:
        rows.append([record, int(record.unk), int(record.id), int(record.has_ended)])

    rows[0][0] = len(effects)
    return rows


def VisibleEffect_FindByID(a_i_AgentID: Any = -2, a_i_EffectID: Any = 0) -> Any:
    """The visible effect of an agent whose effect id matches (``GwAu3_Data_Agent.au3:1191-1217``).

    The source's three answers, in its order and its shapes: an agent whose type word is not ``0xDB``
    answers the scalar ``0`` (``:1194``); a match answers ``(True, node, unk, has_ended)`` at the first
    node whose ``+0x4`` equals the id (``:1202-1209``); and no match answers ``(False, 0, 0, 0)``, the
    array the function starts with (``:1192``, ``:1216``). The comparison is the **id** at ``+0x4``
    only, which is why a match does not need the type word GwAu3's other readers test.

    The second cell is this project's `VisibleEffectStruct` where GwAu3's is the node's address
    (``:1206``) -- the divergence this module's header records for the other two readers -- and the id
    and ``has_ended`` cells are the record's own ``id`` and ``has_ended`` fields at ``+0x4`` and
    ``+0x8``. ``Agent_HasVisibleEffect`` (``:1138-1141``) reads cell ``0``, so the boolean stays first.
    """

    from .uai_effects import _visible_effects

    if int(Agent_GetAgentInfo(a_i_AgentID, "Type")) != 0xDB:
        return 0

    for record in _visible_effects(a_i_AgentID):
        if int(record.id) == int(a_i_EffectID):
            return [True, record, int(record.unk), int(record.has_ended)]

    return [False, 0, 0, 0]
