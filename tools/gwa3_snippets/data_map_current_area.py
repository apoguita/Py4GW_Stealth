"""``GwAu3_Data_Map.au3``'s **current-area and instance** readers, hand-written into the generated module.

Read from ``tools/gwa3_snippets/`` at generation time: ``data_map.py`` is rewritten whole on every run.

**What is here, and what each one is.**

* ``Map_GetCurrentAreaInfo`` (`GwAu3_Data_Map.au3:51-121`) answers one field of the area record the client
  is **in**. GwAu3 follows its own ``$g_p_InstanceInfo`` to ``+0x8`` and reads a ``0x7C`` record; that
  record is the same structure the area table holds -- which is why the key list is the table reader's
  own (``Campaign`` at ``+0x0``, ``Continent`` at ``+0x4``, ``Region`` at ``+0x8``, ``RegionType`` at
  ``+0xC``, ``ThumbnailID`` at ``+0x14``, the party and player size bounds, the icon rectangle, ``FileID``
  at ``+0x68``, ``NameID`` at ``+0x74``, ``DescriptionID`` at ``+0x78``). This project reads the same
  record for the map the client is in, through its own current-map read, so the member **delegates to
  `Map_GetAreaInfo`** with the current map id rather than keeping a second key table that could drift from
  the first. Its guard is GwAu3's: an empty key answers ``0`` before anything is read.
* ``Map_GetRegion`` (`:15-17`) reads one client global (``$g_p_Region``). This answers `Map.GetRegion`,
  the port's read of the same fact; GwAu3's answer is one number and the port's member answers a pair, so
  its first element is the number.
* ``Map_GetInstanceUpTime`` (`:4-8`) reads the instance timer out of the client's own context. This
  answers `Map.GetInstanceUptime` (`py4gw/map.py:281`), the port's read of the same clock.
* ``Map_GetCurrentRegionType`` (`:123-...`) maps the region-type **number** to one of GwAu3's own twenty
  names. This answers the port's own name for the same number (`Map.GetRegionType`,
  ``py4gw/map.py:298``) -- a documented divergence of spelling only, recorded on the member rather than
  transcribed as a second twenty-case table that could drift from the port's.
"""


def Map_GetCurrentAreaInfo(info: str = "") -> Any:
    """One field of the area the client is in, by GwAu3's field name
    (``GwAu3_Data_Map.au3:51-121``).

    GwAu3's guard is kept: an empty key answers ``0`` before anything is read, and an unrecognised key
    answers ``0`` -- its ``Switch`` has no ``Case Else`` and falls through to the same ``Return 0``. The
    key table is `Map_GetAreaInfo`'s, which is the same ``0x7C`` record, so the numbers come from one
    mapping rather than two.
    """

    if info == "":
        return 0

    return Map_GetAreaInfo(Map_GetMapID(), info)


def Map_GetRegion() -> int:
    """The client's region number (``GwAu3_Data_Map.au3:15-17``).

    GwAu3's whole body is one read of ``$g_p_Region``. This answers the same number from the port's own
    read of it (`Map.GetRegion`, ``py4gw/map.py:289``), whose pair carries the number first.
    """

    from ..map import Map

    return int(Map.GetRegion()[0])


def Map_GetInstanceUpTime() -> int:
    """How long the client has been in this instance (``GwAu3_Data_Map.au3:4-8``).

    GwAu3 walks ``BasePointer[0][0x18][0x8][0x1AC]`` for the timer; this answers the port's own read of
    the same clock (`Map.GetInstanceUptime`, ``py4gw/map.py:281``).
    """

    from ..map import Map

    return int(Map.GetInstanceUptime())


def Map_GetCurrentRegionType() -> str:
    """The current region type's **name** (``GwAu3_Data_Map.au3:123-...``).

    GwAu3 maps the region-type number to one of its own twenty literals (``"Explorable"``,
    ``"Mission Outpost"``, ``"Dungeon"`` ...). This answers the port's own name for the same number
    (`Map.GetRegionType`, ``py4gw/map.py:298``), which is the same fact spelled by this library. That is
    the divergence, and it is deliberate: a second twenty-case table here would be a second surface to
    keep in step with the port's.
    """

    from ..map import Map

    return str(Map.GetRegionType()[1])
