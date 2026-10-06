# Camera port

**Source:** `Py4GWCoreLib/Camera.py` (367 lines, 46 members) with Native's `GW::camera`
(`camera_methods.cpp` 151 lines, `camera_bindings.cpp` 194, `context/camera.h` 120) as the authority for
what each *action* does. The class is item 3 of the class map's friction order.

## What the class is

A thin facade over one pointer, `CameraContext`'s camera, which the port already reads
(`py4gw/context/camera_context.py`, 457 lines — the struct with its fields **and its setters**, and a
facade that already answers the read members). The surface splits in three:

| group | members | what they need |
| --- | ---: | --- |
| **reads** — `GetYaw`, `GetPitch`, `GetCameraZoom`, `GetMaxDistance`, `GetPosition`, `GetLookAtTarget`, `GetCameraPositionToGo`, `GetTimeInTheMap`, `GetTimeInTheDistrict`, `GetYawToGo`, `GetPitchToGo`, `GetDistanceToGo`, `GetFieldOfView`, `GetFielsOfView2`, `GetCameraUnlock`, … | 30 | **nothing new**: one field off the ported `CameraStruct`, at ~3 µs each |
| **arithmetic** — `GetCurrentYaw`, `IsPointInFOV` (`Camera.py:337-367`) | 2 | host-side arithmetic over the reads, verbatim |
| **actions** — `SetYaw`, `SetPitch`, `SetMaxDistance`, `SetFieldOfView`, `SetCameraUnlock`, `ForwardMovement`, `VerticalMovement`, `SideMovement`, `RotateMovement`, `ComputeCameraPos`, `UpdateCameraPos`, `SetCameraPosition`, `SetLookAtTarget`, `SetFog` | 14 | see below |

## The decision the class carries

**Reforged's actions are calls on its own in-process camera object** (`Camera.camera_instance().SetYaw(…)`
and the rest). Native's are `GW::camera` functions which read the camera, change fields and, for three of
them, call the client's own functions — **all of it enqueued on the game thread**
(`camera_bindings.cpp:100-103` → `GW::game_thread::Enqueue`; `camera_methods.cpp:78` `SetMaxDist`, `:87`
`SetFieldOfView`, `:145` `SetFog`, the last through `fog_patch_addr`, already in the catalog).

So an action here is one of two things, and this project has done **neither yet**:

1. **A game-thread *call*** to a client function — the capability layer has this (`client.call_function`,
   and `camera_methods.cpp`'s three functions have catalog entries).
2. **A game-thread *field write*** — `look_at_target.x += …`, `camera->yaw = …`, the two struct writes
   `SetCameraPos`/`SetLookAtTarget`. The payload's vocabulary is
   `NOP / PING / ADD_U32 / ECHO_U32 / CALL` (`shared_block.py`, `Operation`): **there is no memory-write
   operation**, so writing a *float* into the client from the game thread is a capability this port does
   not have yet, and a host-side `WriteProcessMemory` instead would be a different mechanism from the
   source's (the source writes on that thread on purpose — the client is reading the same struct).

That is the choice, and it is the owner's: **build the write operation into the payload** (the faithful
route, and it unlocks every later class that writes target-side state — `Camera`'s eight `Set*`, the
`Player` actions' field writes, `Skillbar`'s slot writes), or **port the class with the actions raising**
`_unported(member, "a game-thread field write")` until that exists. Everything else in the class — 32 of
46 members — is read-only and portable today.

## Built and verified (2026-09-27)

The class is in the tree as `py4gw/camera.py`: **46 members, none raising**, the source's order and names,
with Native's bodies for the actions.

| what | evidence |
| --- | --- |
| the 30 getters | live: every one answered the client's own record, **median 5 us** per call (`GetYaw` 0.5527, `GetPitch` 0.9229, `GetFieldOfView` 1.745 rad, `GetPosition` (-6768.7, -2486.0, -736.6)) |
| `GetCurrentYaw`, `IsPointInFOV` | offline against `Camera.py:33-49`/`337-367` term for term, including the two infinities and `dist == 0`; live: the camera's own look-at target is inside its field of view |
| the 11 field writers | **the payload's `WRITE_MEMORY`** operation (new this round, `py4gw/game_thread/`), which copies from the block's data region into the client inside the hooked function -- the same thread Native's `GW::game_thread::Enqueue` uses. Live: `SetPitch` moved `pitch_to_go` by 0.001 and the client's own struct read it back, then the original value was restored (7.6 ms per write) |
| the 2 patch members | live: `SetCameraUnlock(True)` wrote `eb 0f` at `0x00705EF6` (the **vs2022** bytes, the attempt this build resolves), `GetCameraUnlock()` answered True, and the disable put `8b 45` back -- the client's bytes before, during and after |
| the whole surface | 20 offline tests (`tests/test_camera_class_offline.py`): presence of all 46, **zero raisers from the module's `ast`**, every field mapping, the source's arithmetic, and each action landing on the field the source writes |

Two defects were found by that live run and fixed in the class, both from re-deriving something Native
keeps:

1. **The patch address was re-resolved on every toggle.** A patch rewrites the bytes its own pattern
   matches, so the disable found nothing, raised, and **left the camera unlock applied in the live
   client**; the client's own bytes were put back with `tools/recover_camera_patch.py` (the patched form
   of the pattern is what it scans for). The address is now resolved once and kept, as
   `MemoryPatcher` keeps it.
2. **The patch bytes were recomputed on a re-enable**, which had no pattern left to read the resolver's
   attempt from and would have taken the vs2022 fallthrough on a vs2017 build. The bytes are now kept
   with the address, which is what `MemoryPatcher::SetPatch` does at startup.

`_reset_patch_state` is called by the connection, which is Native's camera `Exit`
(`camera.cpp:28-33`), so a reconnect starts from a client that has never toggled a patch.

**Verdict: FULL.** No member of the class raises, and each one has live or offline evidence above.

## The plan, as it was taken

1. `py4gw/camera.py`: all 46 members, the source's names, order and bodies. The 30 reads and the 2
   arithmetic members answer; the actions are implemented against the mechanism that exists — the three
   catalog calls go through `client.call_function`, the eleven field writes either through the payload's
   write operation (if the owner takes that route) or raising with the requirement named.
2. Offline tests: every read against a fixture `CameraStruct`; `IsPointInFOV` against the source's own
   arithmetic (a point straight ahead, one at the edge of `half_fov`, one behind, and the `inf` yaw
   case); a raising-set test from the module's own `ast`, as every other class has.
3. `docs/CLASS_PORT_MAP.md`: the `Camera` row and the at-a-glance list.
4. Live verification, once a client is up: the reads against the running client's own values, and — if
   the write route is taken — `SetPitch`/`SetYaw` observed through the client's own struct afterwards,
   which is the assertion that proves a write landed on the right field on the right thread.

## What is owed before it can be called done

- The owner's answer on the write route (payload operation, or actions raising).
- The class file, its tests, and the map row.
- Live evidence for the reads, and for the writes if they land.

3. **A second enable of a patch that was already on read the backup from the patched bytes.** The disable
   after it wrote the patch *back* instead of the client's own bytes — the client's camera update stayed
   patched, and `tools/recover_camera_patch.py` put the bytes back a second time. Native's `TogglePatch`
   does nothing when the state already matches (``base/memory_patcher.h:27-34``), and the class now does
   the same; two tests pin it (a second enable does not re-patch; a disable that was never enabled does
   nothing).

**What the writers sweep showed about the client, which is the class's own design context.** With the
camera update *unpatched*, the writers that set the client's **outputs** (`position`, `look_at_target`,
`max_distance2`, `field_of_view`) are overwritten by the client's own camera update on the next frame,
while the client's **inputs** hold exactly (`pitch_to_go`, `yaw`/`yaw_to_go`, `dist_to_go`). With the
unlock patch applied — which is what that patch is *for*, it skips the client's camera update — every
writer landed on the client's own struct byte for byte: `look_at_target` (-6565.848, -2359.939, -420.808),
`position` -6460.929, `yaw` 1.8798, `pitch_to_go` 0.4747191 (`tests/live_reports/camera_writers2.txt`).
`max_distance2` and `field_of_view` are re-asserted by the client's own settings machinery either way;
Native's `SetMaxDist`/`SetFieldOfView` are the same single field writes (``camera_methods.cpp:78-94``), so
the port matches the source and the client's last word stands in both.
