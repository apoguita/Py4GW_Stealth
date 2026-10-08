"""The object an AutoIt script embeds with ``GUICtrlCreateObj``, and the functions around it.

``GUICtrlCreateObj``'s parameter is "a variable pointing to a previously opened object", and its
page says plainly what such a variable is for: "The GUI functions GUICtrlRead() and GUICtrlSet have
no effect on this control. The object can only be controlled using 'methods' or 'properties' on the
$ObjectVar" (GUICtrlCreateObj.htm). So the object half of that page is three of AutoIt's own
functions -- ``ObjCreate``, ``IsObj`` and ``ObjName`` -- with the object variable they produce.

The language difference is spelling only. AutoIt writes a member access as ``$obj.Name`` and a call
as ``$obj.Name(args)``, and resolves at run time which of the two a name is; Python has one syntax
for each, so a property is read with ``obj.Name`` and a method is called with ``obj.Name(args)``.
A name AutoIt writes bare because it takes no arguments (``$oIE.GoBack``) also runs on a plain
attribute read here, which is the same resolution the interpreter makes.

``ObjEvent`` and ``ObjGet`` are *not* here: neither is part of the GUI reference, and neither is
needed to create or embed an object.
"""

from __future__ import annotations

from typing import Any

from py4gw.gui import native

#: Invocation kinds, named as ``IDispatch`` names them.
_METHOD = native.DISPATCH_METHOD
_GET = native.DISPATCH_PROPERTYGET
_PUT = native.DISPATCH_PROPERTYPUT


class ComError(Exception):
    """A failed ``IDispatch`` call, carrying the HRESULT the object returned.

    AutoIt reports the same failure through its COM error handler (``ObjEvent("AutoIt.Error", ...)``)
    with the HRESULT in ``err.number``.
    """

    def __init__(self, name: str, hresult: int) -> None:
        super().__init__(f"object member {name!r} failed with HRESULT 0x{hresult & 0xFFFFFFFF:08X}")
        self.name = name
        self.hresult = hresult


class _MethodCall:
    """A member of an object that takes arguments, held until the caller supplies them."""

    __slots__ = ("_object", "_name", "_identifier", "_flags")

    def __init__(self, owner: "ComObject", name: str, identifier: int, flags: int) -> None:
        self._object = owner
        self._name = name
        self._identifier = identifier
        self._flags = flags

    def __call__(self, *args: Any) -> Any:
        return self._object._invoke(self._name, self._identifier, args, self._flags)

    def __repr__(self) -> str:
        return f"<method {self._name} of {self._object}>"


class ComObject:
    """An AutoIt object variable: a COM object driven by its own methods and properties.

    ``ObjCreate("Shell.Explorer.2")`` gives one; ``GUICtrlCreateObj`` embeds it; every member is
    reached by name, as in AutoIt. Dropping the last reference releases the object, which is what
    dropping the AutoIt variable does.
    """

    __slots__ = ("_dispatch", "_name", "__weakref__")

    def __init__(self, dispatch: native.DispatchArgument, name: str = "") -> None:
        object.__setattr__(self, "_dispatch", dispatch)
        object.__setattr__(self, "_name", name)

    @property
    def dispatch(self) -> native.DispatchArgument:
        """The interface pointer this variable holds, which is what the host is given."""

        return self._dispatch

    @property
    def name(self) -> str:
        """The object's name from its own type information -- AutoIt's ``ObjName``."""

        name = self._name
        if not name:
            name = native.object_name(self._dispatch)
            object.__setattr__(self, "_name", name)
        return name

    def __repr__(self) -> str:
        return f"<ComObject {self.name or 'object'}>"

    def _invoke(self, name: str, identifier: int, args: tuple[Any, ...], flags: int) -> Any:
        arguments: list[Any] = [
            value.dispatch if isinstance(value, ComObject) else value for value in args
        ]
        hresult, value = native.object_invoke(self._dispatch, name, identifier, tuple(arguments), flags)
        if hresult != 0:
            raise ComError(name, hresult)
        if isinstance(value, native.DispatchArgument):
            return ComObject(value)
        return value

    def _identifier(self, name: str) -> int:
        identifier = native.dispatch_id(self._dispatch, name)
        if identifier is None:
            raise AttributeError(f"{self.name or 'object'} has no member {name!r}")
        return identifier

    def __getattr__(self, name: str) -> Any:
        """Read a member: its value, or -- a method, or a property with arguments -- a call.

        AutoIt resolves the name against the object's own type information, and so does this: a
        property with no arguments is read as its value, and everything else is handed back as
        something to call. Python writes the two forms apart (``obj.Name`` and ``obj.Name(args)``),
        which is the whole of the difference -- an AutoIt name written bare because it takes no
        arguments (``$oIE.GoBack``) is written with empty parentheses here.
        """

        if name.startswith("_"):
            raise AttributeError(name)
        identifier = self._identifier(name)
        kind, parameters = native.member_signature(self._dispatch, identifier)
        if kind == "property" and parameters == 0:
            return self._invoke(name, identifier, (), _GET)
        if kind:
            return _MethodCall(self, name, identifier, _METHOD if kind == "method" else _GET)
        # The object declares nothing about the member, so it is asked: a read that succeeds is the
        # value, and one that reports missing arguments is a call.
        hresult, value = native.object_invoke(self._dispatch, name, identifier, (), _GET | _METHOD)
        if hresult == 0:
            if isinstance(value, native.DispatchArgument):
                return ComObject(value)
            return value
        if native.is_argument_error(hresult):
            return _MethodCall(self, name, identifier, _GET | _METHOD)
        raise ComError(name, hresult)

    def __setattr__(self, name: str, value: Any) -> None:
        """Write a member, which AutoIt writes as ``$obj.Name = value``."""

        if name.startswith("_"):
            object.__setattr__(self, name, value)
            return
        argument = value.dispatch if isinstance(value, ComObject) else value
        identifier = self._identifier(name)
        hresult, _ = native.object_invoke(self._dispatch, name, identifier, (argument,), _PUT)
        if hresult != 0:
            raise ComError(name, hresult)

    def __del__(self) -> None:
        dispatch = getattr(self, "_dispatch", None)
        if isinstance(dispatch, native.DispatchArgument):
            native.release_object(dispatch)


def ObjCreate(
    classname: str,
    servername: str = "",
    username: str = "",
    password: str = "",
) -> ComObject | int:
    """Create a reference to a COM object from the given classname -- AutoIt's ``ObjCreate``.

    ``classname`` is "appname.objectype", and it "can also be a string representation of the
    CLSID"; ``servername``/``username``/``password`` activate and authenticate on a remote
    computer, with the user given as "computer\\usercode" or "domain\\usercode" (ObjCreate.htm).

    Failure returns 0: "Success: an object. Failure: sets the @error flag to non-zero". The flag
    itself has no counterpart outside AutoIt, so the 0 return value is what a caller can test.
    """

    dispatch = native.create_object(classname, servername, username, password)
    if dispatch is None:
        return 0
    return ComObject(dispatch)


def IsObj(variable: Any) -> bool:
    """Whether a value is an object -- AutoIt's ``IsObj``."""

    return isinstance(variable, ComObject)


def ObjName(variable: Any) -> str:
    """The name of an object -- AutoIt's ``ObjName``, empty for anything that is not an object."""

    if not isinstance(variable, ComObject):
        return ""
    return variable.name
