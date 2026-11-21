def batch_for_shader(shader, type, content, indices=None):
    class _B:
        def draw(self, shader): pass
    return _B()
