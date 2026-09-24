"""Read the player through the ported Reforged ``Player`` class.

``py4gw.player.Player`` keeps every member of Reforged's ``Py4GWCoreLib/Player.py``
with the same name and signature, so a ported script reads ``Player.GetLevel()``
exactly as before. What differs is which members can produce a value:

* implemented -- the value comes from a game context this project can read;
* disabled    -- the value lives in DLL-owned state, or the member performs an
  action. Calling one raises ``NotImplementedError`` naming the missing
  mechanism, rather than returning a wrong value.

``Player`` resolves the selected client the way the context readers do, so call
``py4gw.connect(...)`` first. No options argument is needed: unlike the contexts,
these are namespace methods, matching Reforged's call style.

Usage:
    python examples/player.py
"""

import py4gw
from py4gw.player import Player

py4gw.connect(py4gw.win32.list_processes()[0])

print(f"player loaded: {Player.IsPlayerLoaded()}")
print()

# ── identity ──────────────────────────────────────────────────────────────
print(f"player number    {Player.GetPlayerNumber()}")
print(f"login number     {Player.GetLoginNumber()}")
print(f"party number     {Player.GetPartyNumber()}")
print(f"agent id         {Player.GetAgentID()}")
print(f"observing id     {Player.GetObservingID()}")
print(f"name             {Player.GetName()!r}")
print(f"account name     {Player.GetAccountName()!r}")
print(f"account email    {Player.GetAccountEmail()!r}")
print(f"uuid             {Player.GetPlayerUUID()}")

xy = Player.GetXY()
print(f"position         x={xy[0]:.2f} y={xy[1]:.2f}")

agent = Player.GetAgent()
if agent is None:
    print("agent            none")
else:
    # Fields read straight off the agent record, for reference.
    print(f"agent timer      {int(agent.timer)}")
    print(f"agent xy         {agent.xy}")

# ── progression ───────────────────────────────────────────────────────────
print()
print(f"level            {Player.GetLevel()}")
print(f"experience       {Player.GetExperience()}")
print(f"morale           {Player.GetMorale()}")
print(f"skill points     {Player.GetSkillPointData()}")

rank, rating, qualifier, wins, losses = Player.GetRankData()
print(f"rank data        rank={rank} rating={rating} qualifier={qualifier} "
      f"wins={wins} losses={losses}")
print(f"tournament pts   {Player.GetTournamentRewardPoints()}")

flags = Player.GetAccountFlags()
print(f"account flags    0x{flags:X}")
print(f"  dhuums         {Player.IsDhuumsCovenant()}")
print(f"  melandru       {Player.IsMelandrusAccord()}")
print(f"  reforged       {Player.IsReforged()}")

# ── faction and titles ────────────────────────────────────────────────────
print()
print(f"kurzick          {Player.GetKurzickData()}")
print(f"luxon            {Player.GetLuxonData()}")
print(f"imperial         {Player.GetImperialData()}")
print(f"balthazar        {Player.GetBalthazarData()}")

titles = Player.GetTitleArrayRaw()
print(f"titles           {len(titles)} records")
print(f"title indices    {Player.GetTitleArray()[:8]} ...")
print(f"active title id  {Player.GetActiveTitleID()}")

title = Player.GetTitle(Player.GetActiveTitleID())
if title is not None:
    print(f"active title     points={int(title.current_points)} "
          f"tier={int(title.current_title_tier_index)} "
          f"max_rank={int(title.max_title_rank)}")

# ── missions, minions, skills ─────────────────────────────────────────────
print()
# Progress is stored as 32-bit bitmap words, not one entry per mission or skill:
# a set bit means unlocked/completed, a clear bit means locked. So the word
# count is not an item count -- ask the bitmap instead.
# Progress is stored as 32-bit bitmap words, not one entry per mission or
# skill: a set bit means unlocked/completed, a clear bit means locked. So the
# word count is not an item count, and the caller does its own bit math.
missions = Player.GetMissionsCompleted()
skills = Player.GetUnlockedCharacterSkills()
print(f"missions done    {len(missions)} bitmap words "
      f"(up to {len(missions) * 32} bits)")
print(f"mission bonuses  {len(Player.GetMissionsBonusCompleted())} bitmap words")
print(f"missions done HM {len(Player.GetMissionsCompletedHM())} bitmap words")
print(f"bonuses done HM  {len(Player.GetMissionsBonusCompletedHM())} bitmap words")
print(f"unlocked skills  {len(skills)} bitmap words "
      f"(up to {len(skills) * 32} bits)")
print(f"learnable skills {Player.GetLearnableCharacterSkills()}")
print(f"minions          {Player.GetControlledMinions()}")

# ── status and chat state ─────────────────────────────────────────────────
print()
print(f"status           {Player.GetPlayerStatus()} ({Player.GetPlayerStatusName()})")
print(f"is typing        {Player.IsTyping()}")

# Pure helpers are ported in full even though the chat senders are not.
print(f"status name      0 -> {Player.GetPlayerStatusNameFromValue(0)!r}")
print(f"status name      'dnd' -> {Player.GetPlayerStatusNameFromValue('dnd')!r}")
print(f"format chat      {Player.FormatChatMessage('hello', 255, 128, 0)!r}")

# ── disabled members ──────────────────────────────────────────────────────
print()
print("disabled members raise instead of returning a wrong value:")

for label, call in (
    ("Move", lambda: Player.Move(0.0, 0.0)),
    ("ChangeTarget", lambda: Player.ChangeTarget(1)),
    ("GetTargetID", Player.GetTargetID),
    ("GetChatHistory", Player.GetChatHistory),
):
    try:
        call()
    except NotImplementedError as error:
        print(f"  {label:<16} NotImplementedError: {error}")

py4gw.disconnect()
