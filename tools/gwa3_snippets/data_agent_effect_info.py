def Agent_GetAgentEffectInfo(a_i_AgentID: Any = -2, a_i_SkillID: Any = 0, a_s_Info: Any = "") -> Any:
    """One column of an agent's effect from a skill (``GwAu3_Data_Agent.au3:867-911``).

    The source's shape, kept: it walks the agent's own effect array in ``0x18`` strides looking for the
    record whose first dword is the skill id (``:874-882``), answers ``0`` when there is no such record
    (``:884``), answers the **pointer** when no column is asked for (``:885``), and otherwise switches on
    the column name (``:887-910``).

    **This project already reads that array** (`py4gw.effect.get_effects`, the ported ``PyEffects``
    binding over the same records), so the walk is the port's own and each column is the field at the
    source's own offset: ``AttributeLevel`` at ``+0x4``, ``EffectID`` at ``+0x8``, ``CasterID`` at
    ``+0xC``, ``Duration`` at ``+0x10``, ``Timestamp`` at ``+0x14`` -- the same five fields
    `py4gw/gwa3/uai_effects.py` reads for the plugin's own effect columns, from the same record. The two
    computed columns are the source's arithmetic: ``TimeElapsed`` is ``BitAND(Skill_GetSkillTimer() -
    Timestamp, 0xFFFFFFFF)`` and ``TimeRemaining`` is ``Duration * 1000`` minus that; ``HasEffect``
    answers ``True`` for any record that was found, because that is what "found it" means (``:907-908``).
    ``SkillID`` is **commented out in the source** -- "serves no actual purpose as SkillID is a required
    arg" (``:888-889``) -- so it is not a column here either, and an unknown name answers ``0``, which is
    the source's ``Case Else``.

    **The empty-column answer is a record, not a pointer.** ``:885`` answers ``$l_p_EffectPtr``, a client
    address; this answers the **materialized record** the same divergence `Item_GetItemPtr` and
    `Agent_GetAgentPtr` record, and ``None`` where the source answers a zero pointer.
    """

    from .data_skill import Skill_GetSkillTimer

    if a_s_Info == "":
        for record in _effect.get_effects(int(a_i_AgentID)):
            if int(record.skill_id) == int(a_i_SkillID):
                return record
        return None

    for record in _effect.get_effects(int(a_i_AgentID)):
        if int(record.skill_id) != int(a_i_SkillID):
            continue
        if a_s_Info == "AttributeLevel":
            return int(record.attribute_level)
        if a_s_Info == "EffectID":
            return int(record.effect_id)
        if a_s_Info == "CasterID":
            return int(record.agent_id)
        if a_s_Info == "Duration":
            return float(record.duration)
        if a_s_Info == "Timestamp":
            return int(record.timestamp)
        if a_s_Info == "TimeElapsed":
            return (int(Skill_GetSkillTimer()) - int(record.timestamp)) & 0xFFFFFFFF
        if a_s_Info == "TimeRemaining":
            return float(record.duration) * 1000 - (
                (int(Skill_GetSkillTimer()) - int(record.timestamp)) & 0xFFFFFFFF
            )
        if a_s_Info == "HasEffect":
            return True
        return 0

    return 0
