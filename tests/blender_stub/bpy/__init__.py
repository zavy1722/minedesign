"""Minimal bpy stub (tests only; WP-21, DESIGN 6.8). Not Blender."""
import types as _pytypes
from . import types, props, utils, app  # noqa: F401


class _Coll(list):
    def __init__(self, ctor):
        super().__init__()
        self._ctor = ctor

    def new(self, name, *args):
        item = self._ctor(name, *args)
        self.append(item)
        return item

    def get(self, name, default=None):
        for i in self:
            if i.name == name:
                return i
        return default

    def remove(self, item):
        super().remove(item)


class _Images(_Coll):
    def load(self, filepath, check_existing=False):
        """Stub of bpy.data.images.load: a sized (64x64) image named after the file."""
        import os
        return self.new(os.path.basename(str(filepath)), 64, 64)


class _KeymapItems(list):
    def new(self, idname, type, value, **kw):
        item = _pytypes.SimpleNamespace(idname=idname, type=type, value=value, **kw)
        self.append(item)
        return item

    def remove(self, item):
        list.remove(self, item)


class _Keymaps(list):
    def new(self, name, **kw):
        km = _pytypes.SimpleNamespace(name=name, keymap_items=_KeymapItems(), **kw)
        self.append(km)
        return km

    def remove(self, km):
        list.remove(self, km)


class _WindowManager:
    def __init__(self):
        self.keyconfigs = _pytypes.SimpleNamespace(addon=_pytypes.SimpleNamespace(keymaps=_Keymaps()))


class _Data:
    def __init__(self):
        self.meshes = _Coll(lambda n: types.Mesh(n))
        self.cameras = _Coll(lambda n: types.Camera(n))
        self.images = _Images(lambda n, w=0, h=0: types.Image(n, w, h))
        self.objects = _Coll(lambda n, data=None: types.Object(n, data))
        self.scenes = _Coll(lambda n: types.Scene(n))


class _Context:
    def __init__(self):
        self.scene = types.Scene("Scene")
        self.window_manager = _WindowManager()
        self.object = None
        self.active_object = None


class _Ops:
    class _Group:
        def __getattr__(self, name):
            def op(*a, **k):
                if name == "mode_set" and context.object is not None:
                    context.object.mode = k.get("mode", "OBJECT")
                return {"FINISHED"}
            return op

    def __getattr__(self, name):
        return self._Group()


data = _Data()
context = _Context()
ops = _Ops()


def _reset():
    """Test helper: fresh data/context and empty registries."""
    global data, context
    data = _Data()
    context = _Context()
    utils.reset()
    app.timers.registered.clear()
    app.background = False
