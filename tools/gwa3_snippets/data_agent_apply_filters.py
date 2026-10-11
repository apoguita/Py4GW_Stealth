def _ApplyFilters(agent: Any, filters: str) -> bool:
    """GwAu3's filter *string* resolved to a yes/no about one agent (``GwAu3_Data_Agent.au3:1221-1243``).

    GwAu3's scripts hand this helper a pipe-separated list of filter names -- ``"UAI_Filter_IsLivingEnemy"``,
    ``"UAI_Filter_IsLivingAlly|UAI_Filter_ExcludeMe"``, and a leading ``-`` inverts one -- and it answers
    whether the agent passes all of them. It lives in ``GwAu3_Data_Agent.au3``, is used by the ``GetAgents``
    family in the same file and by every targeting function in ``UtilityAI_GetAgent.au3``, so it belongs to
    this module and is reachable from `py4gw/gwa3/uai_get_agent.py` the same way.

    **The one thing a port has to be careful about is the call itself.** GwAu3 resolves each name with
    AutoIt's ``Call($l_s_FilterName, $a_p_Agent)`` -- a lookup in the script's global function namespace --
    and Python has no such namespace to hand. What it has is this layer's own surface, which is exactly
    "every routine this port implements, by its GwAu3 name" (`py4gw/gwa3/bridge.py`'s ``layer_surface``),
    and that is what is looked the name up in. So the string a caller writes is the same string, the
    function it reaches is the same function, and the two answers that matter are the source's own:

    * a name that resolves to nothing answers ``False``, which is what ``Call`` answers for an unknown
      function -- ``0`` -- inverted by the same ``If Not $l_b_Result Then Return False`` (``:1235-1238``).
      It does not raise: an unrecognised name is the source's "no match", not this port's error;
    * an empty filter, or a filter of only blanks, answers ``True`` (``:1222`` and the ``:1228`` skip).

    The whitespace rule is ``StringStripWS($name, 3)`` (strip both ends) and the inversion test is
    ``StringLeft($name, 1) == "-"`` followed by ``StringTrimLeft($name, 1)``.
    """

    if filters == "":
        return True

    from .bridge import layer_surface

    surface = layer_surface()

    for raw in filters.split("|"):
        filter_name = raw.strip()
        if filter_name == "":
            continue

        invert = False
        if filter_name.startswith("-"):
            invert = True
            filter_name = filter_name[1:]

        routine = surface.get(filter_name)
        result = bool(routine(agent)) if routine is not None else False

        if invert:
            result = not result
        if not result:
            return False

    return True
