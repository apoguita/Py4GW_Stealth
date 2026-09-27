"""Port of Reforged's ``native_src/internals/types.py``.

The source file is transcribed as it stands: the same names, the same members, the same
operators, the same comments. Nothing is added and nothing is renamed.

**Three of these names are what the agent records use, and this project did not have them.**
``AgentStruct.terrain_normal`` is a ``Vec3f``, its ``velocity`` a ``Vec2f`` and its ``pos`` a
``GamePos`` (``native_src/context/AgentContext.py:428,431,442``) — and where this port had no such
module it invented ``Vec2fStruct`` and ``GamePositionStruct`` inside the agent context instead of
porting the file those types come from. That is the shape the porting rules forbid: the missing
piece was a source file, so the answer was to port it, not to write a look-alike. The two invented
names are on their way out of the agent context as it is rebuilt on this module.

Terms the source declares for callers, carried as they stand: ``Point2D``, ``Point2DInt``,
``PointOrPath`` (a type alias) and ``PointPath`` (`as_path`/`final_point`).
"""

from __future__ import annotations

import ctypes
from ctypes import Structure, c_uint32, c_float, sizeof

from typing import Generic, TypeAlias, TypeVar

class Vec2f(Structure):
    _fields_ = [
        ("x", c_float),
        ("y", c_float),
    ]
    
    def __init__(self, x: float = 0.0, y: float = 0.0):
        super().__init__()   # keep ctypes initialization intact
        self.x = x
        self.y = y
        
    def to_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)
    
    def to_list(self) -> list[float]:
        return [self.x, self.y]
    
    #operators
    def __add__(self, other):
        if isinstance(other, Vec2f):
            return Vec2f(self.x + other.x, self.y + other.y)
        return NotImplemented
    
    def __sub__(self, other):
        if isinstance(other, Vec2f):
            return Vec2f(self.x - other.x, self.y - other.y)
        return NotImplemented
    
    def __mul__(self, scalar: float):
        return Vec2f(self.x * scalar, self.y * scalar)
    
    def __truediv__(self, scalar: float):
        if scalar != 0:
            return Vec2f(self.x / scalar, self.y / scalar)
        raise ValueError("Cannot divide by zero")
    
    def __repr__(self):
        return f"Vec2f(x={self.x}, y={self.y})"
    
    def __eq__(self, value):
        return super().__eq__(value)


Point2D = tuple[float, float]
Point2DInt = tuple[int, int]
PointOrPath: TypeAlias = Vec2f | Point2D | Point2DInt | list[Vec2f] | list[Point2D] | list[Point2DInt]


class PointPath:
    Value: TypeAlias = PointOrPath

    @staticmethod
    def as_path(pos: PointOrPath) -> list[Vec2f]:
        if isinstance(pos, list):
            path: list[Vec2f] = []
            for point in pos:
                if isinstance(point, Vec2f):
                    path.append(point)
                else:
                    path.append(Vec2f(float(point[0]), float(point[1])))
            return path
        if isinstance(pos, tuple):
            return [Vec2f(float(pos[0]), float(pos[1]))]
        return [pos]

    @staticmethod
    def final_point(pos: PointOrPath) -> Vec2f | None:
        points = PointPath.as_path(pos)
        return points[-1] if points else None
        
        
class Vec3f(Structure):
    _fields_ = [
        ("x", c_float),
        ("y", c_float),
        ("z", c_float),
    ]  
    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0):
        super().__init__()   # keep ctypes initialization intact
        self.x = x
        self.y = y
        self.z = z
        
    def to_tuple(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)

    def to_list(self) -> list[float]:
        return [self.x, self.y, self.z]

class GamePos(Structure):
    _fields_ = [
        ("x", c_float),
        ("y", c_float),
        ("zplane", c_uint32),
    ]
    
    def __init__(self, x: float = 0.0, y: float = 0.0, zplane: int = 0):
        super().__init__()   # keep ctypes initialization intact
        self.x = x
        self.y = y
        self.zplane = zplane
        
    def to_tuple(self) -> tuple[float, float, int]:
        return (self.x, self.y, self.zplane)
