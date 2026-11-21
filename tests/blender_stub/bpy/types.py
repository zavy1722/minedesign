"""Minimal stub of bpy.types for the Face3D add-on tests."""
import numpy as np


class Collection(list):
    """Stand-in for a bpy_prop_collection of PropertyGroups."""

    def __init__(self, item_type=None):
        super().__init__()
        self._type = item_type

    def add(self):
        item = self._type()
        self.append(item)
        return item

    def remove(self, index):
        del self[index]

    def clear(self):
        del self[:]

    def get(self, name, default=None):
        for it in self:
            if getattr(it, "name", None) == name:
                return it
        return default

    def keys(self):
        return [getattr(i, "name", None) for i in self]


class _PropHost:
    """Fallback attribute creation from class annotations (PropertyGroup semantics)."""

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        for klass in type(self).__mro__:
            ann = klass.__dict__.get("__annotations__", {})
            if name in ann and hasattr(ann[name], "make"):
                value = ann[name].make()
                self.__dict__[name] = value
                return value
        raise AttributeError(name)


class PropertyGroup(_PropHost):
    pass


class Operator(_PropHost):
    bl_idname = ""
    bl_label = ""
    bl_options = set()
    _poll_messages = []

    def __init__(self):
        self.reports = []

    def report(self, kind, message):
        self.reports.append((set(kind), message))

    @classmethod
    def poll_message_set(cls, message, *args):
        cls._poll_messages = list(getattr(cls, "_poll_messages", [])) + [message % args if args else message]

    @classmethod
    def poll(cls, context):
        return True


class Panel(_PropHost):
    bl_idname = ""
    bl_label = ""


class Menu(Panel):
    pass


class WorkSpaceTool:
    bl_idname = ""
    bl_label = ""


class AddonPreferences(_PropHost):
    bl_idname = ""


class ID(_PropHost):
    """ID-like object with custom properties (obj["key"])."""

    def __init__(self, name=""):
        self.name = name
        self._custom = {}

    def __setitem__(self, k, v):
        self._custom[k] = v

    def __getitem__(self, k):
        return self._custom[k]

    def __contains__(self, k):
        return k in self._custom

    def get(self, k, default=None):
        return self._custom.get(k, default)

    def keys(self):
        return list(self._custom)


class Scene(ID):
    pass


class Camera(ID):
    def __init__(self, name=""):
        super().__init__(name)
        self.lens = 50.0
        self.sensor_width = 36.0
        self.sensor_fit = "AUTO"
        self.shift_x = 0.0
        self.shift_y = 0.0


# ---------------------------------------------------------------- data blocks
class DataArray:
    """bpy_prop_collection-like with foreach_get / foreach_set on named flat arrays.

    Mirrors Blender's contract that the buffer is a contiguous array of the
    property's dtype and exactly the right length (checked here).
    """

    def __init__(self, n=0, arrays=None):
        self._n = n
        self._arrays = dict(arrays or {})

    def __len__(self):
        return self._n

    def _check(self, attr, buf):
        if attr not in self._arrays:
            raise AttributeError(attr)
        ref = self._arrays[attr]
        if not isinstance(buf, np.ndarray):
            raise TypeError("buffer must be a numpy array")
        if buf.dtype != ref.dtype:
            raise TypeError("dtype %s != %s for %r" % (buf.dtype, ref.dtype, attr))
        if not buf.flags["C_CONTIGUOUS"]:
            raise ValueError("buffer must be contiguous")
        if buf.size != ref.size:
            raise RuntimeError("size mismatch: %d != %d" % (buf.size, ref.size))

    def foreach_get(self, attr, buf):
        self._check(attr, buf)
        buf[:] = self._arrays[attr].reshape(buf.shape)

    def foreach_set(self, attr, buf):
        self._check(attr, buf)
        self._arrays[attr] = np.array(buf, copy=True).reshape(-1)


class Vertices(DataArray):
    def __init__(self):
        super().__init__(0, {"co": np.zeros(0, np.float32)})

    def add(self, n):
        self._n += n
        self._arrays["co"] = np.zeros(self._n * 3, np.float32)


class Attribute:
    def __init__(self, name, type_, domain, n):
        self.name, self.data_type, self.domain = name, type_, domain
        dt, key, k = {"FLOAT": (np.float32, "value", 1), "INT": (np.int32, "value", 1),
                      "FLOAT_VECTOR": (np.float32, "vector", 3),
                      "BOOLEAN": (np.bool_, "value", 1)}[type_]
        self.data = DataArray(n, {key: np.zeros(n * k, dt)})


class Attributes:
    def __init__(self, mesh):
        self._mesh = mesh
        self._d = {}

    def get(self, name, default=None):
        return self._d.get(name, default)

    def __contains__(self, name):
        return name in self._d

    def new(self, name, type, domain):
        n = {"POINT": len(self._mesh.vertices), "FACE": len(self._mesh.polygons),
             "CORNER": len(self._mesh.loops)}[domain]
        self._d[name] = Attribute(name, type, domain, n)
        return self._d[name]


class KeyBlock:
    def __init__(self, name, co, relative_key):
        self.name = name
        self.data = DataArray(co.size // 3, {"co": co.reshape(-1).astype(np.float32)})
        self.relative_key = relative_key
        self.slider_min = 0.0
        self._slider_max = 1.0
        self._value = 0.0
        self.mute = False

    @property
    def slider_max(self):
        return self._slider_max

    @slider_max.setter
    def slider_max(self, v):
        self._slider_max = float(v)
        self._value = min(self._value, self._slider_max)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        self._value = float(min(max(v, self.slider_min), self._slider_max))


class KeyBlocks(list):
    def get(self, name, default=None):
        for k in self:
            if k.name == name:
                return k
        return default

    def __getitem__(self, i):
        if isinstance(i, str):
            k = self.get(i)
            if k is None:
                raise KeyError(i)
            return k
        return super().__getitem__(i)


class Key:
    def __init__(self):
        self.key_blocks = KeyBlocks()


class Mesh(ID):
    def __init__(self, name=""):
        super().__init__(name)
        self.vertices = Vertices()
        self.polygons = DataArray(0, {"loop_start": np.zeros(0, np.int32),
                                      "loop_total": np.zeros(0, np.int32)})
        self.loops = DataArray(0, {"vertex_index": np.zeros(0, np.int32)})
        self.attributes = Attributes(self)
        self.shape_keys = None
        self.update_count = 0

    def update(self):
        self.update_count += 1

    def from_pydata(self, verts, edges, faces):
        verts = np.asarray(verts, np.float32).reshape(-1, 3)
        self.vertices.add(len(verts))
        self.vertices._arrays["co"] = verts.reshape(-1).copy()
        sizes = np.asarray([len(f) for f in faces], np.int32)
        flat = np.asarray([i for f in faces for i in f], np.int32)
        starts = np.concatenate([[0], np.cumsum(sizes)[:-1]]).astype(np.int32) if len(sizes) else sizes
        self.polygons = DataArray(len(faces), {"loop_start": starts, "loop_total": sizes})
        self.loops = DataArray(len(flat), {"vertex_index": flat})


class Image(ID):
    def __init__(self, name="", width=0, height=0):
        super().__init__(name)
        self.size = (width, height)
        self.channels = 4
        # Image.pixels.foreach_get(buf) takes no attribute name.
        self.pixels = _Pixels(width * height * 4)


class _Pixels:
    def __init__(self, n):
        self._a = np.zeros(n, np.float32)

    def __len__(self):
        return self._a.size

    def foreach_get(self, buf):
        if buf.dtype != np.float32 or not buf.flags["C_CONTIGUOUS"] or buf.size != self._a.size:
            raise TypeError("bad pixel buffer")
        buf[:] = self._a

    def foreach_set(self, buf):
        if buf.dtype != np.float32 or not buf.flags["C_CONTIGUOUS"] or buf.size != self._a.size:
            raise TypeError("bad pixel buffer")
        self._a = np.array(buf, copy=True).reshape(-1)


class Object(ID):
    def __init__(self, name="", data=None):
        super().__init__(name)
        self.data = data
        self.type = "MESH" if isinstance(data, Mesh) else ("CAMERA" if isinstance(data, Camera) else "EMPTY")
        self.mode = "OBJECT"
        self.matrix_world = None

    def shape_key_add(self, name="Key", from_mix=True):
        me = self.data
        if me.shape_keys is None:
            me.shape_keys = Key()
        blocks = me.shape_keys.key_blocks
        if from_mix and blocks:
            raise NotImplementedError("stub: from_mix=True not modelled")
        co = np.array(me.vertices._arrays["co"], np.float32)
        kb = KeyBlock(name, co, blocks[0] if blocks else None)
        if blocks is not None and not blocks:
            kb.relative_key = kb
        blocks.append(kb)
        return kb


class SpaceView3D:
    handlers = []

    @classmethod
    def draw_handler_add(cls, fn, args, region_type, draw_type):
        h = (fn, args, region_type, draw_type)
        cls.handlers.append(h)
        return h

    @classmethod
    def draw_handler_remove(cls, handle, region_type):
        cls.handlers.remove(handle)
