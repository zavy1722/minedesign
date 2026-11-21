"""No-op stub."""


class _Shader:
    def bind(self): pass
    def uniform_float(self, *a): pass


class shader:
    @staticmethod
    def from_builtin(name):
        return _Shader()


class state:
    @staticmethod
    def blend_set(mode): pass
    @staticmethod
    def line_width_set(w): pass
