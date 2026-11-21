"""No-op gpu_extras stub; `gpu_extras.batch` is defined here (no separate file)."""
import sys
import types


def batch_for_shader(shader, type, content, indices=None):
    class _B:
        def draw(self, shader):
            pass
    return _B()


batch = types.ModuleType(__name__ + ".batch")
batch.batch_for_shader = batch_for_shader
sys.modules[batch.__name__] = batch
