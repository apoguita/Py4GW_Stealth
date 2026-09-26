"""Read the player through the ported Reforged ``Player`` class.

``py4gw.player.Player`` keeps every member of Reforged's ``Py4GWCoreLib/Player.py``
with the same name and signature, so a ported script reads ``Player.GetLevel()``
exactly as before. What differs is which members can produce a value:

* reading    -- the value comes from a game context this project can read;
* acting     -- the member changes the game by calling the client's own function
  on the client's own thread through ``py4gw/game_thread``;
* refused    -- the value lives in DLL-owned state, or the mechanism that would
  carry the action is not ported. Calling one raises ``NotImplementedError``
  naming the missing mechanism, rather than returning a wrong value.

This example reads, then shows refused members refusing. It does **not** call an
action member: those change the game, so exercising one is a deliberate operation
with someone watching the client.

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

# ── refused members ───────────────────────────────────────────────────────
print()
print("refused members raise instead of returning a wrong value:")

for label, call in (
    ("player_instance", Player.player_instance),
    ("GetInstanceUptime", Player.GetInstanceUptime),
    ("RequestChatHistory", Player.RequestChatHistory),
    ("IsChatHistoryReady", Player.IsChatHistoryReady),
    ("GetChatHistory", Player.GetChatHistory),
    # The Balthazar default path is the source's chain with one missing piece behind it: the PvP
    # remap reads Skill.ExtraData.GetIDPvP, so the raise comes from Utils where the source calls it.
    ("UnlockBalthazarSkill", lambda: Player.UnlockBalthazarSkill(1)),
):
    try:
        call()
    except NotImplementedError as error:
        print(f"  {label:<20} NotImplementedError: {error}")

# ── action members ────────────────────────────────────────────────────────
# Not called here. These eighteen change the game — Move moves the character,
# ChangeTarget targets, the chat sends reach the client's own sender — so exercising
# one is a deliberate operation with someone watching the client, not something an
# example does on its way past. Two of them need their argument to be useful rather
# than merely safe: BuySkill and UnlockBalthazarSkill want a real skill id, and the
# interaction members want an agent.
print()
print("action members (not called by this example):")
for label in (
    "ChangeTarget(agent_id)",
    "CallTarget(agent_id)",
    "Interact(agent_id, call_target=False)",
    "Move(x, y, zPlane=0)",
    "DepositFaction(faction_id)",
    "SetActiveTitle(title_id)",
    "RemoveActiveTitle()",
    "SendRawDialog(dialog_id)",
    "SendDialog(dialog_id)",
    "SendAutomaticDialog(button_number)",
    "SetPlayerStatus(status)",
    "BuySkill(skill_id)",
    "UnlockBalthazarSkill(skill_id, use_pvp_remap=True)",
    "SendChatCommand(command)",
    "SendChat(channel, message)",
    "SendWhisper(name, message)",
    "SendFakeChat(channel, message)",
    "SendFakeChatColored(channel, message, r, g, b)",
):
    print(f"  Player.{label}")

py4gw.disconnect()
