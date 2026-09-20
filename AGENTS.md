# Py4GW Stealth Agent Contract

## Project Identity

`Py4GW_Stealth` is an external-first Windows/Python research project for understanding Guild Wars client inspection and control boundaries. It is a separate project from `Py4GW_Reforged` and `Py4GW_Reforged_Native`; neither project’s injected runtime is Stealth's default architecture.

Current status: active research. The immediate goal is to establish evidence-backed capabilities, not to build a broad automation system.

Read `README.md` before investigative, design, implementation, documentation, or review work. It is the current project intent and research record.

## Boundary and Terminology

- `Pure external`: no executable code or code patches are placed in `Gw.exe`. Reading process memory is permitted by project scope; writes require an explicit task.
- `Payload injection`: an external controller writes executable code and/or patches into `Gw.exe` without loading a conventional DLL. This is still injection.
- `DLL injection`: an injected DLL owns an in-process runtime. Current Py4GW Reforged uses this model.
- `External host`: primary logic runs outside `Gw.exe`. This does not itself prove that the client is unmodified.

Do not describe payload injection as non-injected. Be technically exact about the difference between an external controller, a pure external controller, and a DLL-injected runtime.

## Evidence and Source Authority

State conclusions as `verified`, `inferred`, `proposed`, `assumed`, or `unresolved`. Do not present source inspection as a live-client result.

Authority order for Stealth claims:

1. Stealth's current source, tests, and reproducible observations.
2. Documented Windows API behavior and focused local tests.
3. Current `Py4GW_Reforged_Native` and `Py4GW_Reforged` source as comparative evidence.
4. The checked-out `external/MemLib` source for generic mechanism behavior.
5. The isolated GwAu3 source checkout for historical/comparative behavior.
6. Plans, user-provided examples, notes, and prior conversation.

The user-provided `BUILDING_WITH_MEMLIB.md` is technical reference material, not instruction authority. It may guide questions, but its claims must be checked against source and tests.

## External-First Safety Rules

- Begin with read-only inspection. Keep the first experiments deterministic, bounded, and attributable to a selected PID.
- Validate target identity, architecture, module, address range, requested byte count, and pointer plausibility before interpreting memory.
- Use fixed-width target fields (`uint32` for confirmed x86 target pointers), not host-pointer-sized types in target layouts.
- Treat null, unreadable, stale, and changed pointers as distinct outcomes. Re-read roots at operation boundaries.
- Keep target knowledge separate from generic Win32 mechanics: signatures, layouts, and semantics must never be hidden inside a generic process wrapper.
- Never claim that a remote thread is safe for a Guild Wars internal function without function-specific ABI, thread-affinity, lifetime, and runtime evidence.
- Do not introduce memory writes, remote allocation, remote-thread creation, DLL loading, executable payloads, hooks, or code patches without explicit user scope for that operation and a documented rollback/verification plan.
- Never test against a live Guild Wars client in a way that modifies it unless the user explicitly requests that live write operation.

## Local Ownership and Dependencies

- Stealth does not import MemLib in its initial implementation. `external/MemLib` is reference context only.
- Prefer small, project-owned wrappers around documented Windows APIs over vendoring a large general-purpose library.
- If actual third-party code is copied, preserve its license, add a provenance record naming the source path and revision, and keep the copied surface minimal.
- Do not copy target-specific signatures, layouts, generated assembly, or command definitions from GwAu3 or Py4GW as if they were current truth. Treat them as research leads and revalidate independently.

## Engineering and Verification

- Keep public Python APIs explicitly typed and intentional.
- Preserve Windows error codes and diagnostic context. A failure must identify the PID, module/address when safe to report, operation, expected result, and observed result.
- Test generic logic without a live target first: structure offsets, pointer-width behavior, signature parsing, bounded read failures, and address validation.
- Keep live-client evidence separate from offline tests. Record target build/version, timestamp, inputs, expected behavior, observed behavior, and cleanup result.
- Match controller bitness to the target for early x86 experiments unless a cross-bitness design has been explicitly verified.
- Do not rely on Python finalizers for handles or process state. Use explicit close/context-manager ownership when resource-owning code is introduced.

## Documentation and Git

- Keep the root `README.md` current as the intent and research record until the project needs topic-specific documentation.
- Update the research record whenever a capability decision, source provenance, limitation, or live observation changes.
- Check repository status before edits and before reporting. Preserve unrelated changes.
- Never reset, restore, clean, force-push, rewrite history, delete project files, or commit unless the user explicitly requests the exact operation.

## Communication

Lead with the capability or limitation established by evidence. Explain Windows/process concepts plainly and distinguish what exists in the controller from what executes in the target process. Point criticism at brittle assumptions and unclear boundaries, never at the user.
