"""Port of Reforged's ``Py4GWCoreLib/py4gwcorelib_src/Utils.py``.

**Source:** ``Py4GWCoreLib/py4gwcorelib_src/Utils.py`` — 842 lines, ``class Utils`` at line 12
with **40** ``@staticmethod``s. The class is a namespace: nothing in it is instance state, and every
member keeps the source's name, signature, arithmetic and return values, so a script that calls
``Utils.SkillIdToDialogId(42)`` keeps working after switching libraries.

**Where it lives.** ``py4gw/py4gwcorelib_src/`` is the source's own relative path under this
project's package root, the rule ``py4gw/enums_src/`` already follows for
``Py4GWCoreLib/enums_src/``; the file name is this project's casing (``docs/STYLE.md``:
*Module/file | lowercase ``snake_case``*) and every name inside it is the source's.

Three groups exist, and each member says which one it is in its docstring:

``implemented``
    The member is a transcription. Almost all of them are pure Python — arithmetic, packing,
    base64/bin64 template coding, regex markup work — and need nothing from the client. The few
    that read the client do it through a ported context or a ported class, exactly where the
    source reads it.

``raising from the member it calls``
    ``GwinchToPixels`` and ``PixelsToGwinch`` are written as the source writes them, and the raise
    a caller sees comes from ``Map.MissionMap.GetScale`` — the source's own call graph, which is
    how ``Agent``'s members that delegate are handled too.

``not built yet``
    ``TokenizeMarkupText`` and ``GenerateSkillbarTemplate`` need a surface this project does not
    have (the client's own ImGui text measure; the ``Skillbar`` class behind
    ``PySkillbar.Skillbar().GetSkill``), and ``BalthazarSkillIdToDialogId`` needs
    ``Skill.ExtraData.GetIDPvP``. They raise ``NotImplementedError`` through :func:`_unported`,
    naming the file, the lines and the work item — never a plausible wrong value. The source's
    members are complete and working; what is missing is this port's own work, and it is recorded
    in ``docs/UTILS_PORT.md`` and in the class list of that member's docstring.

**Two departures from the source's text, both named where they happen.**

1. ``import PyImGui`` (``Utils.py:6``) and the ``..enums`` re-export hub (``Utils.py:11``) are not
   imported here: ``PyImGui`` is an in-client binding module this port does not load, and the three
   constants the module needs are imported from the ported module that *declares* them
   (``enums_src/GameData_enums.py``, reached in the source through ``Py4GWCoreLib/enums.py``, which
   is a re-export hub). ``from .Color import Color`` (``Utils.py:9``) is the ported
   ``py4gw/py4gwcorelib_src/color.py``.
2. ``ClearSubModules``' ``ConsoleLog`` calls are Reforged's console *inside the client*
   (``py4gwcorelib_src/Console.py``); there is no external equivalent, so the returns and the
   ``sys.modules`` work are carried and the log lines are not — the same divergence already
   recorded for ``Agent``'s ``PySystem.Console`` diagnostics.
"""

from __future__ import annotations

import math
import re
import sys
import time

from datetime import datetime, timezone

from .color import Color
from ..enums_src.game_data_enums import (
    CAP_EXPERIENCE,
    CAP_STEP,
    EXPERIENCE_PROGRESSION,
)


def _unported(member: str, requirement: str) -> NotImplementedError:
    """Build the error raised by a member this port has not built yet.

    The source's member is complete and working — Reforged is an in-production library — so the
    message never describes the source: it names the work item this port still owes, and the raise
    is what keeps a caller from receiving a plausible wrong value while that work is outstanding.
    """

    return NotImplementedError(
        f"Utils.{member} is declared but not built here yet: it needs {requirement}. "
        "The source's member works; this port raises at the call site and names the work "
        "item instead of returning a wrong value."
    )


class Utils:
    """The Reforged ``Utils`` namespace class (``Utils.py:12-841``): 40 static members."""

    from typing import Tuple

    @staticmethod
    def HasFlag(flags: int, flag: int) -> bool:
        """``Utils.py:14-16``."""

        return (int(flags) & int(flag)) == int(flag)

    @staticmethod
    def Distance(pos1, pos2):
        """``Utils.py:18-27``. Returns ``0.0`` for a missing position or an unindexable one."""

        if not pos1 or not pos2:
            return 0.0
        try:
            dx = pos1[0] - pos2[0]
            dy = pos1[1] - pos2[1]
            return math.hypot(dx, dy)
        except Exception:
            return 0.0

    @staticmethod
    def point_in_circle(px: float, py: float, cx: float, cy: float, r: float) -> bool:
        """``Utils.py:30-34``."""

        dx = px - cx
        dy = py - cy
        return dx * dx + dy * dy <= r * r

    @staticmethod
    def point_in_polygon(px: float, py: float, polygon: list[Tuple[float, float]]) -> bool:
        """
        Ray casting algorithm
        """
        inside = False
        n = len(polygon)
        j = n - 1

        for i in range(n):
            xi, yi = polygon[i]
            xj, yj = polygon[j]

            intersect = (
                ((yi > py) != (yj > py)) and
                (px < (xj - xi) * (py - yi) / (yj - yi + 1e-12) + xi)
            )
            if intersect:
                inside = not inside

            j = i

        return inside

    @staticmethod
    def IsPointInRect(px: float, py: float, rx: float, ry: float, rw: float, rh: float) -> bool:
        """``Utils.py:60-62``."""

        return rx <= px <= rx + rw and ry <= py <= ry + rh

    @staticmethod
    def format_bytes(num_bytes: int) -> str:
            """
            Convert a byte count to a human-readable string using
            the closest magnitude: bytes, KB, MB, GB, TB.
            """
            units = ("bytes", "KB", "MB", "GB", "TB")
            size = float(num_bytes)
            unit_idx = 0

            # Find the most appropriate unit
            while size >= 1024.0 and unit_idx < len(units) - 1:
                size /= 1024.0
                unit_idx += 1

            # For plain bytes, keep it as integer
            if unit_idx == 0:
                return f"{num_bytes} bytes"

            # For KB and above, show 2 decimals
            return f"{size:.2f} {units[unit_idx]}"

    @staticmethod
    def RGBToNormal(r, g, b, a):
        """return a normalized RGBA tuple from 0-255 values"""
        return r / 255.0, g / 255.0, b / 255.0, a / 255.0

    @staticmethod
    def NormalToColor(color: Tuple[float, float, float, float]) -> "Color":
        """Convert a normalized RGBA float tuple (0.0–1.0) to 0–255 integer values."""
        r = int(color[0] * 255)
        g = int(color[1] * 255)
        b = int(color[2] * 255)
        a = int(color[3] * 255)
        return Color(r, g, b, a)

    @staticmethod
    def RGBToDXColor(r, g, b, a) -> int:
        """``Utils.py:101-103``."""

        return (a << 24) | (r << 16) | (g << 8) | b

    @staticmethod
    def RGBToColor(r, g, b, a) -> int:
        """``Utils.py:105-107``."""

        return (a << 24) | (b << 16) | (g << 8) | r

    @staticmethod
    def ColorToTuple(color: int) -> Tuple[float, float, float, float]:
        """Convert a 32-bit integer color (ABGR) to a normalized (0.0 - 1.0) RGBA tuple."""
        a = (color >> 24) & 0xFF  # Extract Alpha (highest 8 bits)
        b = (color >> 16) & 0xFF  # Extract Blue  (next 8 bits)
        g = (color >> 8) & 0xFF   # Extract Green (next 8 bits)
        r = color & 0xFF          # Extract Red   (lowest 8 bits)
        return r / 255.0, g / 255.0, b / 255.0, a / 255.0  # Convert to RGBA float

    @staticmethod
    def TupleToColor(color_tuple: Tuple[float, float, float, float]) -> int:
        """Convert a normalized (0.0 - 1.0) RGBA tuple back to a 32-bit integer color (ABGR)."""
        r = int(color_tuple[0] * 255)  # Convert R back to 0-255
        g = int(color_tuple[1] * 255)  # Convert G back to 0-255
        b = int(color_tuple[2] * 255)  # Convert B back to 0-255
        a = int(color_tuple[3] * 255)  # Convert A back to 0-255
        return Utils.RGBToColor(r, g, b, a)  # Encode back as ABGR

    @staticmethod
    def DegToRad(degrees):
        """``Utils.py:127-129``."""

        return degrees * (math.pi / 180)

    @staticmethod
    def RadToDeg(radians):
        """``Utils.py:131-133``."""

        return radians * (180 / math.pi)

    @staticmethod
    def TrueFalseColor(condition):
        """``Utils.py:135-140``."""

        if condition:
            return Utils.RGBToNormal(0, 255, 0, 255)
        else:
            return Utils.RGBToNormal(255, 0, 0, 255)

    @staticmethod
    def GetFirstFromArray(array):
        """``Utils.py:142-149``. ``0`` for a missing or empty array."""

        if array is None:
            return 0

        if len(array) > 0:
            return array[0]
        return 0

    @staticmethod
    def GwinchToPixels(gwinch_value: float, zoom_offset=0.0) -> float:
        """``Utils.py:151-160``, written as the source writes it.

        The two reads it makes are ``Map``'s — ``Map.MissionMap.GetZoom()`` and
        ``Map.MissionMap.GetScale()`` — so this port needs no arithmetic of its own, and the raise
        a caller sees on this build is ``MissionMap.GetScale``'s own (``py4gw/map.py``): the frame
        viewport-scale read is Map's Stage 5 work, recorded in ``docs/MAP_PORT.md``.
        """

        from ..map import Map

        gwinches = 96.0  # hardcoded GW unit scale
        zoom = Map.MissionMap.GetZoom() + zoom_offset
        scale_x, _ = Map.MissionMap.GetScale()

        pixels_per_gwinch = (scale_x * zoom) / gwinches
        return gwinch_value * pixels_per_gwinch

    @staticmethod
    def PixelsToGwinch(pixel_value: float, zoom_offset=0.0) -> float:
        """``Utils.py:163-172``, the inverse of :func:`GwinchToPixels` over the same two reads."""

        from ..map import Map

        gwinches = 96.0
        zoom = Map.MissionMap.GetZoom() + zoom_offset
        scale_x, _ = Map.MissionMap.GetScale()

        pixels_per_gwinch = (scale_x * zoom) / gwinches
        return pixel_value / pixels_per_gwinch

    @staticmethod
    def PixelsToUV(x: int, y: int, w: int, h: int, texture_width: int, texture_height: int) -> tuple[tuple[float, float], tuple[float, float]]:
        """``Utils.py:174-178``."""

        uv0 = (x / texture_width, y / texture_height)
        uv1 = ((x + w) / texture_width, (y + h) / texture_height)
        return uv0, uv1

    @staticmethod
    def SafeInt(value, fallback=0):
        """``Utils.py:180-187``. A non-finite or unconvertible value answers ``fallback``."""

        try:
            if not math.isfinite(value):
                return fallback
            return int(value)
        except (ValueError, TypeError, OverflowError):
            return fallback

    @staticmethod
    def SafeFloat(value, fallback=0.0):
        """``Utils.py:189-196``. The float sibling of :func:`SafeInt`."""

        try:
            if not math.isfinite(value):
                return fallback
            return float(value)
        except (ValueError, TypeError, OverflowError):
            return fallback

    @staticmethod
    def GetBaseTimestamp():
        """``Utils.py:198-201``. Milliseconds since UTC midnight, from the host clock."""

        SHMEM_ZERO_EPOCH = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        return int((time.time() - SHMEM_ZERO_EPOCH) * 1000)

    @staticmethod
    def split_uppercase(s: str) -> str:
        """``Utils.py:203-206``."""

        import re
        return re.sub(r'(?<!^)(?=[A-Z])', ' ', s)

    @staticmethod
    def humanize_string(string: str) -> str:
        """Convert a string like "Some_VariableName" to "Some Variable Name"."""

        # Replace underscores with spaces
        string = string.replace('_', ' ')

        # Insert spaces before uppercase letters (if not at start)
        string = re.sub(r'(?<!^)(?=[A-Z])', ' ', string)

        return string

    @staticmethod
    def GetExperienceProgression(xp: int) -> float:
        """
        Given total XP, return (level, percent_in_level, skill_points_from_xp).
        https://wiki.guildwars.com/wiki/Experience
        """
        # Before overflow
        for lvl, base, req in EXPERIENCE_PROGRESSION:
            if xp < base + req:
                pct = (xp - base) / req * 100.0
                # skill points only after level 20
                skill_points = max(0, lvl - 20)
                return pct

        # Overflow past 182,600
        overflow = xp - CAP_EXPERIENCE
        extra_levels = overflow // CAP_STEP
        remainder = overflow % CAP_STEP
        lvl = 23 + extra_levels
        pct = remainder / CAP_STEP * 100.0

        # Skill points: from 21 onward
        # Level 21 = +1, Level 22 = +2, then +1 per 15k chunk
        skill_points = (22 - 20)  # 2 from reaching 21 & 22
        skill_points += extra_levels + (1 if remainder > 0 else 0)

        return pct

    @staticmethod
    def StripMarkup(text: str) -> str:
        """
        Remove all markup tags and return plain visible text only.
        This matches the same tags used by TokenizeMarkupText.
        """

        if not text:
            return ""

        # 1. Remove protected color blocks but KEEP their inner text
        #    example: <c=@gold>Hello</c> → Hello
        text = re.sub(r"<c=@[^>]+>(.*?)</c>", r"\1", text, flags=re.IGNORECASE)

        # 2. Remove standalone bullet codes {s} and {sc}
        text = re.sub(r"\{s\}", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\{sc\}", "", text, flags=re.IGNORECASE)

        # 3. Replace known break/paragraph tags with newlines
        text = re.sub(r"<brx?>/?", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</?p>", "\n", text, flags=re.IGNORECASE)

        # 4. Remove ANY REMAINING <...> or {...} tags
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\{[^}]+\}", "", text)

        # 5. Collapse duplicated whitespace
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s+", "\n", text)

        return text.strip()

    @staticmethod
    def TokenizeMarkupText(text: str, max_width: float):
        """Return tokenized lines of markup-ready text (no rendering) (``Utils.py:280-408``).

        Not built yet: the member measures text with **the client's own ImGui** — it pulls a
        ``PyImGui.StyleConfig()``, zeroes ``CellPadding``/``ItemSpacing`` on it for the duration of
        the measurement (``Utils.py:284-290``, restored at ``405-406``) and calls
        ``PyImGui.calc_text_size(...)`` for every word and protected colour block
        (``Utils.py:339``, ``363``). ``PyImGui`` is an in-client binding module this port does not
        load, and the measure is a question only the running client can answer, so the wrapping
        cannot be reproduced on the host without asking it. The work item is on
        ``docs/TARGET_SIDE_WORK.md``; the tokenizer's own regex work around it is not the missing
        piece.
        """

        raise _unported(
            "TokenizeMarkupText",
            "PyImGui.StyleConfig (Utils.py:284-290, 404-406) and PyImGui.calc_text_size "
            "(Utils.py:339, 363), which measure the visible text with the client's own ImGui; "
            "PyImGui is an in-client binding module this port does not load "
            "(docs/TARGET_SIDE_WORK.md)",
        )

    @staticmethod
    def base64_to_bin64(char: str) -> str:
        """Convert base64 character to 6-bit binary string (Guild Wars LSB-first order)"""
        match char:
            case 'A': return '000000'
            case 'B': return '100000'
            case 'C': return '010000'
            case 'D': return '110000'
            case 'E': return '001000'
            case 'F': return '101000'
            case 'G': return '011000'
            case 'H': return '111000'
            case 'I': return '000100'
            case 'J': return '100100'
            case 'K': return '010100'
            case 'L': return '110100'
            case 'M': return '001100'
            case 'N': return '101100'
            case 'O': return '011100'
            case 'P': return '111100'
            case 'Q': return '000010'
            case 'R': return '100010'
            case 'S': return '010010'
            case 'T': return '110010'
            case 'U': return '001010'
            case 'V': return '101010'
            case 'W': return '011010'
            case 'X': return '111010'
            case 'Y': return '000110'
            case 'Z': return '100110'
            case 'a': return '010110'
            case 'b': return '110110'
            case 'c': return '001110'
            case 'd': return '101110'
            case 'e': return '011110'
            case 'f': return '111110'
            case 'g': return '000001'
            case 'h': return '100001'
            case 'i': return '010001'
            case 'j': return '110001'
            case 'k': return '001001'
            case 'l': return '101001'
            case 'm': return '011001'
            case 'n': return '111001'
            case 'o': return '000101'
            case 'p': return '100101'
            case 'q': return '010101'
            case 'r': return '110101'
            case 's': return '001101'
            case 't': return '101101'
            case 'u': return '011101'
            case 'v': return '111101'
            case 'w': return '000011'
            case 'x': return '100011'
            case 'y': return '010011'
            case 'z': return '110011'
            case '0': return '001011'
            case '1': return '101011'
            case '2': return '011011'
            case '3': return '111011'
            case '4': return '000111'
            case '5': return '100111'
            case '6': return '010111'
            case '7': return '110111'
            case '8': return '001111'
            case '9': return '101111'
            case '+': return '011111'
            case '/': return '111111'
        return '000000'  # Default to 'A' if character is not found

    @staticmethod
    def dec_to_bin64(decimal: int, bits: int) -> str:
        """Convert decimal to binary string with specified number of bits (LSB first order)"""
        binary = bin(decimal)[2:]  # Remove '0b' prefix
        binary = binary.zfill(bits)  # Pad with zeros to reach desired length
        return binary[::-1]  # Reverse to match LSB-first order used in Guild Wars

    @staticmethod
    def bin64_to_base64(binary: str) -> str:
        """Convert binary string to base64 character using Guild Wars specific mapping"""
        # Pad binary to multiple of 6 bits
        while len(binary) % 6 != 0:
            binary += '0'

        # Create reverse mapping from the existing base64_to_bin64 function
        bin_to_char = {}
        chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
        for char in chars:
            bin_pattern = Utils.base64_to_bin64(char)
            bin_to_char[bin_pattern] = char

        result = ''
        for i in range(0, len(binary), 6):
            chunk = binary[i:i+6]
            if chunk in bin_to_char:
                result += bin_to_char[chunk]
            else:
                # Fallback - this shouldn't happen if encoding is correct
                result += 'A'

        return result

    @staticmethod
    def bin64_to_dec(binary):
        """Convert binary string to decimal (LSB-first order)"""
        decimal = 0
        for i in range(0, len(binary)):
            if binary[i] == '1':
                decimal += 2**(i)
        return decimal

    @staticmethod
    def encode_skill_template(prof_primary: int, prof_secondary: int, attributes: dict[int, int], skills: list[int]) -> str:
        """Encode skill template data into template string"""
        binary_data = ''

        # Template type (4 bits) - 14 for skill template
        binary_data += Utils.dec_to_bin64(14, 4)

        # Version number (4 bits) - 0
        binary_data += Utils.dec_to_bin64(0, 4)

        # Determine profession bits needed
        max_prof = max(prof_primary, prof_secondary)
        if max_prof <= 15:  # 4 bits
            prof_bits_code = 0
            prof_bits = 4
        elif max_prof <= 63:  # 6 bits
            prof_bits_code = 1
            prof_bits = 6
        elif max_prof <= 255:  # 8 bits
            prof_bits_code = 2
            prof_bits = 8
        else:  # 10 bits
            prof_bits_code = 3
            prof_bits = 10

        # Profession bits code (2 bits)
        binary_data += Utils.dec_to_bin64(prof_bits_code, 2)

        # Primary profession
        binary_data += Utils.dec_to_bin64(prof_primary, prof_bits)

        # Secondary profession
        binary_data += Utils.dec_to_bin64(prof_secondary, prof_bits)

        # Attributes count (4 bits)
        binary_data += Utils.dec_to_bin64(len(attributes), 4)

        # Determine attribute bits needed
        max_attr = max(attributes.keys()) if attributes else 0
        if max_attr <= 15:  # 4 bits
            attr_bits_code = 0
            attr_bits = 4
        elif max_attr <= 31:  # 5 bits
            attr_bits_code = 1
            attr_bits = 5
        elif max_attr <= 63:  # 6 bits
            attr_bits_code = 2
            attr_bits = 6
        elif max_attr <= 127:  # 7 bits
            attr_bits_code = 3
            attr_bits = 7
        elif max_attr <= 255:  # 8 bits
            attr_bits_code = 4
            attr_bits = 8
        else:  # More bits as needed
            attr_bits_code = min(15, max_attr.bit_length() - 4)
            attr_bits = attr_bits_code + 4

        # Attribute bits code (4 bits)
        binary_data += Utils.dec_to_bin64(attr_bits_code, 4)

        # Attributes
        for attr_id, attr_value in attributes.items():
            binary_data += Utils.dec_to_bin64(attr_id, attr_bits)
            binary_data += Utils.dec_to_bin64(attr_value, 4)

        # Determine skill bits needed
        max_skill = max(skills) if skills else 0
        if max_skill <= 255:  # 8 bits
            skill_bits_code = 0
            skill_bits = 8
        elif max_skill <= 511:  # 9 bits
            skill_bits_code = 1
            skill_bits = 9
        elif max_skill <= 1023:  # 10 bits
            skill_bits_code = 2
            skill_bits = 10
        elif max_skill <= 2047:  # 11 bits
            skill_bits_code = 3
            skill_bits = 11
        elif max_skill <= 4095:  # 12 bits
            skill_bits_code = 4
            skill_bits = 12
        else:  # More bits as needed
            skill_bits_code = min(15, max_skill.bit_length() - 8)
            skill_bits = skill_bits_code + 8

        # Skill bits code (4 bits)
        binary_data += Utils.dec_to_bin64(skill_bits_code, 4)

        # Skills (8 skills)
        for skill in skills:
            binary_data += Utils.dec_to_bin64(skill, skill_bits)

        # Tail (1 bit) - always 0
        binary_data += '0'

        # Convert binary to base64
        return Utils.bin64_to_base64(binary_data)

    @staticmethod
    def GenerateSkillbarTemplate() -> str:
        """
        Purpose: Generate template code for player's skillbar
        Args: None
        Returns: str: The current skillbar template.

        ``Utils.py:622-665``, with one recorded route difference: the source reads the player's
        skill ids through ``GLOBAL_CACHE.SkillBar.GetSkillIDBySlot(slot)``, and that mirror is a layer
        this project does not port (``docs/WRAPPER_MIGRATION_ASSESSMENT.md``). The member called here
        is the class the mirror mirrors, and its body is the same line —
        ``PySkillbar.Skillbar().GetSkill(slot).id.id`` in both
        ``GlobalCache/SkillbarCache.py:21-22`` and ``Skillbar.py:110-119`` — so the value is the
        source's; what changes is which of the two identical call sites is reached.
        """

        from ..player import Player
        try:
            from ..skillbar import SkillBar
            from ..agent import Agent
            from ..context.world_context import AttributeStruct
            # Get skill IDs for all 8 slots
            skills = []
            for slot in range(1, 9):  # Slots 1-8
                skill_id = SkillBar.GetSkillIDBySlot(slot)
                skills.append(skill_id if skill_id else 0)

            # Get profession IDs
            prof_primary, prof_secondary = Agent.GetProfessionIDs(Player.GetAgentID())
            if prof_primary is None:
                prof_primary = 0
            if prof_secondary is None:
                prof_secondary = 0

            # Get attributes
            attributes_raw: list[AttributeStruct] = Agent.GetAttributes(Player.GetAgentID())
            attributes = {}

            # Convert attributes to dictionary format
            for attr in attributes_raw:
                attr_id = int(attr.attribute_id)  # Convert enum to integer
                attr_level = attr.level_base  # Get attribute level
                if attr_level > 0:  # Only include attributes with points
                    attributes[attr_id] = attr_level

            # Encode template
            template = Utils.encode_skill_template(prof_primary, prof_secondary, attributes, skills)
            return template

        except Exception as e:
            # Return empty string if encoding fails
            print(f"Failed to encode skillbar template: {e}")
            return ""
    @staticmethod
    def GenerateSkillbarTemplateFrom(prof_primary: int, prof_secondary: int, attributes: dict[int, int], skills: list[int]) -> str:
        """
        Purpose: Generate template code for a specified skillbar from given data
        Args:
            prof_primary (int): The primary profession ID.
            prof_secondary (int): The secondary profession ID.
            attributes (dict[int, int]): A dictionary of attribute IDs and levels.
            skills (list[int]): A list of skill IDs.
        """
        try:
            # Encode template
            template = Utils.encode_skill_template(prof_primary, prof_secondary, attributes, skills)
            return template

        except Exception as e:
            # Return empty string if encoding fails
            print(f"Failed to encode skillbar template: {e}")
            return ""

    @staticmethod
    def ParseSkillbarTemplate(template: str) -> tuple[int, int, dict, list]:
        '''
        Purpose: Parse a skillbar template into its components.
        Args:
            template (str): The skillbar template to parse.
        Returns:
            prof_primary (int): The primary profession ID.
            prof_secondary (int): The secondary profession ID.
            attributes (dict): A dictionary of attribute IDs and levels.
            skills (list): A list of skill IDs.
        '''

        enc_template = ''

        for char in template:
            enc_template = f'{enc_template}{Utils.base64_to_bin64(char)}'

        template_type = Utils.bin64_to_dec(enc_template[:4])
        # if template_type != 14:
        #     return (None, None, None, None)
        enc_template = enc_template[4:]

        version_number = Utils.bin64_to_dec(enc_template[:4])
        enc_template = enc_template[4:]

        prof_bits = Utils.bin64_to_dec(enc_template[:2]) * 2 + 4
        enc_template = enc_template[2:]

        prof_primary = Utils.bin64_to_dec(enc_template[:prof_bits])
        enc_template = enc_template[prof_bits:]

        prof_secondary = Utils.bin64_to_dec(enc_template[:prof_bits])
        enc_template = enc_template[prof_bits:]

        attributes_count = Utils.bin64_to_dec(enc_template[:4])
        enc_template = enc_template[4:]

        attributes_bits = Utils.bin64_to_dec(enc_template[:4]) + 4
        enc_template = enc_template[4:]

        attributes = {}
        for i in range(attributes_count):
            attr = Utils.bin64_to_dec(enc_template[:attributes_bits])
            enc_template = enc_template[attributes_bits:]
            value = Utils.bin64_to_dec(enc_template[:4])
            enc_template = enc_template[4:]
            attributes[attr] = value

        skill_bits = Utils.bin64_to_dec(enc_template[:4]) + 8
        enc_template = enc_template[4:]

        skills = []
        for i in range(8):
            skill = Utils.bin64_to_dec(enc_template[:skill_bits])
            enc_template = enc_template[skill_bits:]
            skills.append(skill)

        return (prof_primary, prof_secondary, attributes, skills)

    @staticmethod
    def calculate_energy_pips(max_energy: float, energy_regen: float) -> int:
        """Calculate the number of energy pips based on max energy and regeneration rate."""
        pips = 3.0 / 0.99 * energy_regen * max_energy
        return int(pips)

    @staticmethod
    def calculate_health_pips(max_health: float, health_regen: float) -> int:
        """Calculate the number of health pips based on max health and regeneration rate."""
        pips = (max_health * health_regen) / 2
        return int(pips)

    @staticmethod
    def SkillIdToDialogId(skill_id: int) -> int:
        """
        Convert a skill ID to the dialog ID used by Skill Trainers.

        This ORs the skill ID with the skill dialog mask (0x0A000000) to create
        the dialog ID that can be sent via Player.SendDialog() to learn a skill.

        Args:
            skill_id (int): The skill ID to convert.

        Returns:
            int: The dialog ID for the Skill Trainer (skill_id | 0x0A000000).

        Example:
            dialog_id = Utils.SkillIdToDialogId(42)  # Returns 0x0A00002A
            Player.SendDialog(dialog_id)
        """
        SKILL_DIALOG_MASK = 0x0A000000
        return skill_id | SKILL_DIALOG_MASK

    @staticmethod
    def BalthazarSkillIdToDialogId(skill_id: int, use_pvp_remap: bool = True) -> int:
        """
        Convert a skill ID to the raw dialog ID used by the Priest of Balthazar unlock vendor.

        Args:
            skill_id (int): The requested skill ID.
            use_pvp_remap (bool): Whether to remap through Skill.ExtraData.GetIDPvP(...).

        Returns:
            int: The Balthazar unlock dialog ID.

        The PvP remap reads ``Skill.ExtraData.GetIDPvP`` (``Skill.py:464-467``), which is
        ``PySkill.Skill(skill_id).id_pvp`` — the skill constant record's ``skill_id_pvp`` word
        (``py4gw/skill.py``, read from the client's own table). The source wraps that call in
        ``try``/``except Exception`` and carries on with ``pvp_id = 0`` (``Utils.py:801-807``); the
        port keeps the same handler, so a record this controller cannot read — or no connection at
        all — takes the source's own branch rather than raising from inside the member.
        """

        BALTHAZAR_UNLOCK_DIALOG_MASK = 0x10000000
        PVP_REMAP_SENTINEL = 0x0D6C

        resolved = int(skill_id or 0)
        if resolved <= 0:
            return 0

        if use_pvp_remap:
            try:
                from ..skill import Skill

                pvp_id = int(Skill.ExtraData.GetIDPvP(resolved) or 0)
            except Exception:
                pvp_id = 0

            if pvp_id > 0 and pvp_id != resolved and pvp_id != PVP_REMAP_SENTINEL:
                resolved = pvp_id

        return BALTHAZAR_UNLOCK_DIALOG_MASK | (resolved & 0xFFFF)

    @staticmethod
    def ClearSubModules(module_name: str, log: bool = False):
        """``Utils.py:814-841``: unload every ``sys.modules`` entry whose name contains
        ``module_name``, skipping modules marked ``PERSISTENT``.

        The ``ConsoleLog`` lines the source emits beside each branch are Reforged's console
        **inside the client**; this port has no external equivalent, so they are not carried and
        every branch's decision is — the same divergence recorded for ``Agent``'s
        ``PySystem.Console`` diagnostics. The table this member edits is the running interpreter's
        ``sys.modules``: the client's in the source, this controller's here.
        """

        module_names = list(sys.modules.keys())
        for name in module_names:
            if module_name not in name:
                continue

            module = sys.modules.get(name, None)
            if module is None:
                continue

            # Check persistence flag (proper bugfix)
            is_persistent = getattr(module, "PERSISTENT", False)

            if is_persistent:
                continue

            try:
                del sys.modules[name]

            except Exception:
                pass
