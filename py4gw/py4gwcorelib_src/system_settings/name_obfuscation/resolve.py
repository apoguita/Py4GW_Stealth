"""Port of Reforged's ``py4gwcorelib_src/system_settings/name_obfuscation/resolve.py``.

The source file is transcribed as it stands: one function, its lazy import and its own fallback.

**What this port does not carry, and why.** The source package's ``__init__.py`` re-exports its
``controller`` — the process-wide singleton that applies the alias map and drives the settings UI —
and that controller's own module tree (``model``, ``store``, ``config_ui``) is a settings subsystem
with its own port. So the directory here is an implicit namespace package: the import path
``...name_obfuscation.resolve`` works exactly as the source spells it, and nothing of the subsystem is
pulled in. ``PyNameObfuscator`` is the **injected runtime's** module, so the source's own
``except Exception`` is the path this port takes: the obfuscator unavailable (which is every case
here) returns the input unchanged, which is what the source's docstring says happens offline.
"""


def require_real_name(name: str) -> str:
    """Return the real name for a display name, or the input unchanged.

    Uses the obfuscator's own reverse mapping (observed cache, then alias reverse). Safe in every
    case: obfuscation off / name not aliased / obfuscator unavailable (offline) all return the input.
    """
    try:
        import PyNameObfuscator  # type: ignore[import-not-found]  # the injected runtime's module

        resolved = PyNameObfuscator.require_real_name(str(name))
        return resolved if resolved else str(name)
    except Exception:
        return str(name)
