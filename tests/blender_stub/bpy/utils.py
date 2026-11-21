"""Stub of bpy.utils: records registrations; double registration raises like Blender."""
registered_classes = []
registered_tools = []


def register_class(cls):
    if cls in registered_classes:
        raise ValueError("register_class(...): already registered as a subclass %r" % cls.__name__)
    registered_classes.append(cls)


def unregister_class(cls):
    if cls not in registered_classes:
        raise RuntimeError("unregister_class(...): missing bl_rna attribute %r" % cls.__name__)
    registered_classes.remove(cls)


def register_tool(tool_cls, *, after=None, separator=False, group=False):
    registered_tools.append(tool_cls)


def unregister_tool(tool_cls):
    registered_tools.remove(tool_cls)


def reset():
    registered_classes.clear()
    registered_tools.clear()
