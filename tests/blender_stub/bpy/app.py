"""Stub of bpy.app."""
version = (4, 5, 0)
version_string = "4.5.0"
background = False
online_access = False
translations = type("translations", (), {"registered": {}})()


class _Timers:
    def __init__(self):
        self.registered = []   # [(fn, first_interval, persistent)]

    def register(self, function, first_interval=0.0, persistent=False):
        self.registered.append((function, first_interval, persistent))

    def unregister(self, function):
        for i, (fn, _a, _b) in enumerate(self.registered):
            if fn == function:
                del self.registered[i]
                return
        raise ValueError("function not registered")

    def is_registered(self, function):
        return any(fn == function for fn, _a, _b in self.registered)


class _Handlers:
    def __init__(self):
        for n in ("load_post", "load_pre", "undo_post", "redo_post", "depsgraph_update_post",
                  "save_pre", "save_post"):
            setattr(self, n, [])


timers = _Timers()
handlers = _Handlers()
