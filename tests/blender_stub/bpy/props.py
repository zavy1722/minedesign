"""Stub of bpy.props: each *Property callable returns a descriptor record."""


class PropDef:
    """Record of a property declaration; also a data descriptor for Scene.face3d-style attachment."""

    def __init__(self, kind, **kw):
        self.kind = kind
        self.kw = kw
        self._name = "_pv_%x" % id(self)

    def default_value(self):
        k = self.kind
        if "default" in self.kw:
            return self.kw["default"]
        if k == "Enum":
            items = self.kw.get("items") or []
            return items[0][0] if items and not callable(items) else ""
        return {"String": "", "Int": 0, "Float": 0.0, "Bool": False}.get(k)

    def make(self):
        from . import types as t
        if self.kind == "Pointer":
            return self.kw["type"]()
        if self.kind == "Collection":
            return t.Collection(self.kw["type"])
        return self.default_value()

    def __get__(self, obj, owner=None):
        if obj is None:
            return self
        if self._name not in obj.__dict__:
            obj.__dict__[self._name] = self.make()
        return obj.__dict__[self._name]

    def __set__(self, obj, value):
        obj.__dict__[self._name] = value

    def __repr__(self):
        return "<PropDef %s %r>" % (self.kind, self.kw)


def _mk(kind):
    def factory(**kw):
        return PropDef(kind, **kw)
    factory.__name__ = kind + "Property"
    return factory


StringProperty = _mk("String")
IntProperty = _mk("Int")
FloatProperty = _mk("Float")
BoolProperty = _mk("Bool")
EnumProperty = _mk("Enum")
PointerProperty = _mk("Pointer")
CollectionProperty = _mk("Collection")
FloatVectorProperty = _mk("FloatVector")
IntVectorProperty = _mk("IntVector")
