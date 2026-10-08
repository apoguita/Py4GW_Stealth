# The test surface: `main.py` as the library's own workbench

The window is not a demo any more -- it is the way this library is **inspected, exercised and
reported on** by a person. Everything below is what the window shows and does; the engine behind it
(`test_surface.py`) and the window's own tests are built and green.

**State.** Six tabs exist and work: the map (groups / entries / detail / search / Run this entry /
Test this group / Test this class / Rebuild map), the 22 context views with Refresh all, the
Tests tab (Test all methods, Test reads (connected), include writes, Re-run failures, Save reports,
Clear output, the status list and the output pane) feeding one output pane, the Self-test tab (the
battery: one row per check, each saying what it expected and what it saw, with the live sections that
judge whether the client's data is *correct*), and the Live data tab (every field and property of
every context as it was read, filterable, writable to text and JSON).
`tests/test_main_window_offline.py` drives every one of them headlessly (20 cases),
`tests/test_self_test_offline.py` drives the battery and its write guard (13 cases), and the whole
offline suite (2,024 tests) is green.

**The same surface without the window.** Every button is a one-line caller of a method that returns
what it saw -- `connect`, `run_self_test`, `read_live_data`, `dump_live_data` -- so the whole surface
can be driven by a script or a test as well as by a person, and the command line at the bottom of
`main.py` is that surface with no window at all (see **The command line** below).

**There is no separate live-verifier file.** An earlier `tests/live_verification.py` and
`verify_live.cmd` were deleted on the owner's instruction: the live checks belong to this one surface,
so a person clicking a button and a script calling a method run the *same* checks and read the *same*
data.

## What to do when you sit down

The order matters only in that each step needs the one before it; nothing here needs a decision from
anyone else, and nothing writes to the client unless you tick the box in step 4.

1. **`python main.py` from an elevated shell.** Unelevated the window still opens, the map is still
   complete, and every connection is refused -- with the reason in the client list -- because that is
   this library's own rule.
2. **Clients tab**: press **Refresh**. The list shows every running client with pid, name, character,
   status and path. **The status column is the client's own state, not this window's**: `online` means
   that client is running a logged-in character, `in selection menus` means it is not, `not read: needs
   an elevated shell` and `read failed: ...` are statements about *the read* (never about the client --
   a refused read is not a client sitting at the login screen). Attaching this controller is a separate
   step: select the row and press **Connect selected**; the line under the table then says
   `Connected to PID ...`, and that line is the only place the word "connected" means *this window*.
3. **Library surface tab**: the map is already built. Type a name in the box to find any of the
   ~20,000 entries, or pick a module on the left. Selecting an entry fills the detail pane -- what it
   is, whether it reads or writes **and why**, whether it needs the client -- and you can pass
   arguments (`0`, `1.5`, `Norgu`, `true`, `1, 2`) and press **Run this entry**. **Test this class**
   and **Test this group** run just that class or module, which is how a single thing is checked
   without walking everything.
4. **Tests tab**: press **Test all methods**. With no client connected that is the safe full walk --
   16,635 answers, 246 writes skipped and counted, nothing connected. With the client connected and
   **include writes** ticked, the writes run too: that is the only switch in the window that lets a
   member act on the client, and it is off by default. **Test reads (connected)** is the middle
   ground.
5. **Read the results**: the status list on the left carries every status with its count -- click
   `not answered (3377)` or `skipped (classified as a write) (246)` to see exactly those, and type in
   the box beside it to narrow further. **Save reports** writes both the full report and the short
   one to `runtime/`.
6. **Client data tab**: 22 context views, each with its own filter and refresh, and **Refresh all**
   for all of them at once.
7. **Self-test tab**: press **Run all checks**. The battery states, check by check, whether this
   library works: the map's completeness, the engine's safety rules, known answers from members that
   need no client, the window's own wiring, the connection, and then -- when a client is connected --
   fourteen **live sections** that read the running client and judge whether what came back is
   *correct game data* rather than merely a call that returned. **Offline checks only** and **Client
   checks only** run a subset; **Save test report** writes `runtime/self_test_report.txt`.
8. **Live data tab**: press **Read live data**. That runs the client checks and shows every field and
   property of every context as it was read -- one row per value, `context | kind | name | value`,
   filterable. **Write report** writes all of it to `runtime/live_data_report.txt` and
   `runtime/live_data_report.json`.

**A run with nothing connected reads nothing, and says so.** Every client check and every live section
is *skipped*, the Live data table stays empty, and the summary line carries the reason:
`no client connected: 19 client and live checks were skipped, so no live data was read -- connect
first (Clients tab: Refresh, select the row, Connect selected)`. That sentence is in the window's
status line, in `runtime/self_test_report.txt`, and in the live-data report's own text
(`connected: False`, then *"no context was read: connect a client and run the client checks"*), because
a clean `PASS 31, FAIL 0, SKIP 19` on its own reads like the live checks passed when in fact none ran.

## What "the live sections" actually check

These are the checks that make the battery worth pressing, because each one has an answer that can be
*wrong*: a call that returns is not the same as data that is right. In the order they run:

| Section | What it insists on |
| --- | --- |
| `live contexts` | each of the 22 readers answers a snapshot or refuses in the library's own words |
| `live char` | a map id above zero, the character's name, `is_logged_in` true exactly when a name is present, a four-word uuid |
| `live map` | a region the enum knows, an instance kind, `min < max` on both axes, a party size of at least one |
| `live player` | a live agent id, finite XY, `hp <= max_hp`, a name, and the player's own record present in the agent array |
| `live agents` | the player is in the array, ids unique, positions finite, every allegiance a known member, hp in range |
| `live party` | `GetPartySize()` equals players + heroes + henchmen, each party record resolves to the player's own agent id through `Party.Players.GetAgentIDByLoginNumber`, and the leader is the player while this client is the leader |
| `live world` | the controlled-character record agrees with `Player` on id, the first skillbar belongs to the player, and its eight slots each carry a skill id in range |
| `live camera` | yaw and pitch are finite radians within a turn, the position is three finite coordinates, the look-at point is finite and distinct from it, and the field of view is positive |
| `live text parser` | `entries_per_file == 1024` and `language_slots == 11`, read from the client's own table |
| `live instance` | the instance is typed, the map record's party sizes are ordered (`1 <= min <= max <= 12`) with a real region, and both terrain records end beyond their start on each axis |
| `live items` | `bags()` returns at most 40 bags, the first bag's count and id are in range, and its items have ids above zero |
| `live agreement` | the *same fact read two ways* agrees: char context vs `Map.GetMapID`, context vs `Player.GetName`, the world record vs `Player.GetAgentID`, the player's XY **inside `Map.GetMapBoundaries()`**, and the party context's own arrays vs `Party.GetPartySize` |
| `live data dump` | every field and property of every context reads, and the values are kept for the Live data tab and the report |
| `live safety` | every member classified as a **write** that is a call was blocked for the duration, and none was called |

Two paths to one fact is the strongest check here: a wrong offset, a wrong pointer hop or a stale
record shows up as a disagreement between readings that are each plausible on their own. Where the
port has only *one* path to a fact, the check says so instead of inventing a second: there is no
second copy of the player's position (`Player.GetXY` and `Agent.GetXY` are the same read), so the
position is checked against the map's boundaries, which the client publishes separately.

## Read-only by construction: the write guard

The battery does not promise to be read-only, it *is* read-only. While a live section runs, every
member `test_surface` classifies as a write **that is a call** -- 210 of the 246 -- is replaced by a
recorder that fails the run if it is called, on its class or, for a module-level write such as
`py4gw.connect`, on its module. The originals go back in a `finally`.

The other 36 are **not actions** and are named rather than replaced: 22 frame-id strings
(`FrameId.PlayButton`) and 14 namespace classes (`Party.Players`), each classified as a write by the
name-prefix rule reading "Play". They cannot be called, and replacing them breaks what reads *through*
them -- measured live on 2026-10-12: replacing `Party.Players` made `Party.GetPartyLeaderID` fail with
`'function' object has no attribute 'GetAgentIDByLoginNumber'`. Those 36 are a finding about the map's
classification, not a safety property, and `live safety` reports both numbers.

That guard is itself tested without a client: `tests/test_self_test_offline.py` drives it directly --
a write called under the guard raises and is recorded, and every replaced member is the same object
afterwards.

## The command line

The same surface, headless, for a script or for an unattended run. Nothing here is a second
implementation: each mode builds the same `MainWindow` and calls the same methods the buttons call.

```
python main.py                                  # the window
python main.py --self-test                      # the checks that need no client
python main.py --self-test --client             # and the live sections (elevated shell + a running client)
python main.py --self-test --areas "live map,live agents"
python main.py --data                           # every live value -> runtime/live_data_report.txt (+ .json)
python main.py --self-test --client --report out.txt
python main.py --self-test --client --elevate   # relaunch elevated: one UAC prompt, and the user approves it
```

* **Exit codes**: `0` all checks passed, `1` at least one failed, `2` the run needed a client and was
  refused (unelevated shell, or the UAC prompt declined), `3` a client was asked for and none is
  running.
* **`--client` connects**, and connecting is a write to the client (the capability layer is installed),
  so this mode is for an elevated shell and for a person who has decided to run it. `--data` implies
  the same thing, because it reads the client.
* **`--elevate` starts a second, elevated process** and prints where its report goes. A process cannot
  raise its own token, so the shell that asked stays unelevated and holds no rights over the client;
  the UAC prompt is the user's to approve, which is why this is a flag and never something the window
  does by itself.
* **`--json`** prints the checks as JSON; `--quiet` prints nothing but the report paths.

## What "the whole library" means, counted

Measured from the package on disk, not from a hand-written list:

| What | Count |
| --- | --- |
| modules of `py4gw` (each becomes a group) | 139 |
| surface entries mapped | ~20,000 |
| of those: records (ctypes) | 179 expanded, 686 names |
| record fields, each with its offset and type | 1,765 |
| enums / enum members | 231 / 5,734 |
| classes / methods / properties | 758 / 1,806 / 743 |
| module-level constants (incl. the 3,111 AutoIt names) | 7,118 |
| reach for the selected client | 106 |
| classified as writes | 246 |
| unclassified (reported, never run while connected) | 2,031 |

`test_surface.build_entries()` produces that map in ~1 s; `run_all()` walks it in ~0.1 s and, with
nothing connected, answers 16,585 entries with **zero** unexpected failures.

## The six areas of the window

### 1. Clients
Unchanged: scan (`Win32.find_guild_wars`), the list of clients with pid, name, character, status and
path, and Connect / Disconnect. Without an elevated shell nothing connects and the list says so.

### 2. Surface -- the map
Three panes, which is the organization the map's shape asks for:

* **Groups** -- one row per module (`py4gw`, `py4gw.context`, `py4gw.gui`, ...), with its entry count;
* **Entries** -- the selected group's rows: `kind`, `access`, `name`, `owner`, `detail` (a field's
  `+0xOFFSET Type`, a bitfield's width, or an alias's "declared in ..."), and the docstring's first
  line. A search box filters by name and docstring across **every** group, because a caller knows the
  member, not the module it is declared in;
* **Detail** -- the selected entry: its path, what it is, whether it reads or writes **and the reason**
  (its own name, its docstring, the write marker found in its own source, or "nothing settles it"),
  whether it needs the client, what the engine will do with it, its parameters and signature, its
  detail line and its docstring -- and the **argument box** plus **Run this entry**: the box is
  pre-filled with the parameter names, and accepts `0`, `1.5`, `Norgu`, `true`, `1, 2`.

### 3. Data -- everything read
The 22 context views that exist today (each with its filter, its own refresh, and its status line),
plus a **Refresh all** button that runs every one of them and says so.

### 4. Tests -- the buttons
* **Test all methods** -- runs the whole surface *with no client connected*: every read and every
  unclassified member (safe there, because the library refuses every client-facing call), writes
  skipped and counted, and the result of each entry written to the output pane. With a client
  connected the same button becomes the safe walk: reads only.
* **Test reads (connected)** -- reads and properties against the connected client; writes stay
  skipped, and unclassified members stay skipped because a connected client cannot tell them apart
  from writes.
* **include writes (acts on the client)** -- a tick box: with it, a member classified as a write is
  run too, and the report names every one of them. It is off by default and stays off unless a person
  ticks it.
* **Re-run failures** -- only the entries that did not answer, re-run with whatever is ticked.
* **The status list** -- every status with its count (`all`, `answered`, `not answered`, and then each
  status on its own). Choosing one shows exactly those results; the box beside it narrows further by
  text. This is how a 20,000-row run is read: `not answered` in one click.
* **Save reports** -- writes two files to `runtime/`: `test_surface_report.txt` (the whole surface,
  ~55,000 lines: every entry, why it is classified as it is, and its result) and
  `test_surface_summary.txt` (the counts, a module-by-module answered table, and **every entry that
  did not answer** with its reason -- the one to read first).
* **Clear output** -- starts again.

## The output pane

One pane, fed by the run: `status`, `milliseconds`, `label`, then the value, the error, or **what
the member printed** -- `Utils.GenerateSkillbarTemplate` reports through `print`, and the engine
captures that text with the result rather than letting it fall on the console.

### 5. Self-test -- one button, one row per check

**Run all checks**, **Offline checks only**, **Client checks only**, **Save test report**, and one
table: `status | area | check | expected | saw | ms`. The checks and their areas are in
`self_test.py`; with no client connected every client and live check is *skipped* -- with the reason
"no client connected" in the `saw` column -- because a window with no client is a state, not a defect.

### 6. Live data -- every value, as it was read

`context | kind | name | value`, one row per field and per property of every context, with
`UNREADABLE` rows for the fields that could not be read (an unreadable field is a reading too). The
rows come from the same battery run the Self-test tab performs: pressing **Read live data** runs the
client checks and shows what they kept, so the screen, the report file and a caller's return value
are one set of readings and never three.

## What must never happen

* A member classified as a **write** is never called unless the user ticked the box for it -- and in
  the battery it cannot be called at all: every write member is blocked while a live section runs.
* An **unclassified** member is never called while a client is connected.
* No member's failure is hidden: a refusal is a result, with the library's own words in it.
* No check reports an invented value: an unreadable field is reported as unreadable, and a section
  that could not read a context says so rather than showing zeroes.
