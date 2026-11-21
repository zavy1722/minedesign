"""WP-23: CI policy checks (``tools/ci_checks.py``) and package exports / packaging metadata.

Each check of the tool is run on the repository (must pass) and on a small planted violation in a
temporary tree (must be reported), so a check that silently stops looking fails here.
"""
from __future__ import annotations

import importlib
import importlib.util
import json
import subprocess
import sys
import tomllib
import types
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location("wp23_ci_checks", REPO / "tools" / "ci_checks.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


ci = _load()

SUBPACKAGES = ("core", "io", "geometry", "mesh", "model", "solve", "fit", "handoff", "texture", "qa", "eval",
               "testbed", "pipeline")


# ---------------------------------------------------------------------------- the repository passes
@pytest.mark.parametrize("name", [n for n in ci.CHECKS if n != "f_pipeline_offline"])
def test_policy_ci(name):
    assert ci.CHECKS[name]() == []


def test_policy_ci_pipeline_runs_offline():
    """(f) a full synthetic pipeline run (texture included) under ``core.policy.network_guard``."""
    assert ci.check_pipeline_offline() == []


def test_policy_ci_main_lists_every_check(capsys):
    assert ci.main(["--only", "a", "b", "d", "e"]) == 0
    out = capsys.readouterr().out
    assert out.count("[ok]") == 4 and "FAIL" not in out
    assert set(ci.CHECKS) == {"a_engine_imports", "b_numpy_neutral", "c_defaults", "d_blender_ext",
                              "e_fixture_provenance", "f_pipeline_offline"}


# ---------------------------------------------------------------------------- planted violations
def _tree(tmp_path, files: dict) -> Path:
    for rel, text in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return tmp_path


def test_import_check_has_teeth(tmp_path):
    repo = _tree(tmp_path, {
        "face3d/ok.py": "import numpy as np\nfrom .x import y\nimport json\n",
        "face3d/a/b.py": "def f():\n    try:\n        import scipy.sparse as sp\n    except ImportError:\n        pass\n",
        "face3d/c.py": "from PIL import Image\nimport importlib\nm = importlib.import_module('cv2')\n",
        "face3d/d.py": "import torch, bpy\nx = __import__('mediapipe')\n",
        "tools/free.py": "import scipy\n",                                  # outside face3d/: not checked
    })
    bad = ci.check_engine_imports(repo)
    text = "\n".join(bad)
    for mod in ("scipy.sparse", "PIL", "cv2", "torch", "bpy", "mediapipe"):
        assert repr(mod) in text, (mod, bad)
    assert len(bad) == 6 and "ok.py" not in text and "tools" not in text


def test_numpy_check_has_teeth(tmp_path):
    repo = _tree(tmp_path, {
        "face3d/ok.py": "import numpy as np\nx = np.float64(1) + np.inf + np.nan\ny = np.isin([1], [1])\n",
        "face3d/bad.py": "import numpy as np\nimport numpy\na = np.float_(1)\nb = np.in1d([1], [1])\n"
                         "c = np.product([1]); d = np.alltrue([1]); e = np.sometrue([1])\n"
                         "f = numpy.Inf\ng = np.NaN\n",
        "face3d/alias.py": "import numpy as xp\nfrom numpy import in1d\nz = xp.NaN\n",
    })
    bad = ci.check_numpy_neutral(repo)
    text = "\n".join(bad)
    for a in ci.FORBIDDEN_NUMPY:
        assert f".{a}" in text, a
    assert len(bad) == 9 and "ok.py" not in text


def test_blender_ext_check_has_teeth(tmp_path):
    ext = "blender_ext/face3d_likeness"
    manifest = (REPO / ext / "blender_manifest.toml").read_text()
    hdr = ci.GPL_HEADER + "\n"
    repo = _tree(tmp_path, {
        f"{ext}/blender_manifest.toml": manifest,
        f"{ext}/bridge.py": hdr + "def f(me, b):\n    me.vertices.foreach_get('co', b)\n",
        f"{ext}/ops.py": hdr + "def g(img, b):\n    img.pixels.foreach_set(b)\n",
        f"{ext}/nohdr.py": "X = 1\n",
        "tools/build_extension.py": (REPO / "tools" / "build_extension.py").read_text(),
    })
    bad = ci.check_blender_ext(repo)
    text = "\n".join(bad)
    assert "ops.py: uses .foreach_set" in text and "ops.py: uses .pixels" in text
    assert "nohdr.py: first line" in text and "likeness/bridge.py" not in text and len(bad) == 3
    # manifest lint: a network permission is refused in a store build
    (repo / ext / "blender_manifest.toml").write_text(manifest.replace(
        "[permissions]", '[permissions]\nnetwork = "phone home"'))
    assert any("network" in b for b in ci.check_blender_ext(repo))
    (repo / ext / "blender_manifest.toml").write_text(manifest.replace("GPL-3.0-or-later", "MIT"))
    assert any("GPL" in b for b in ci.check_blender_ext(repo))


def test_provenance_check_has_teeth(tmp_path):
    lm = {"format": "face3d.landmarks", "faces": [{"uv": [[1.0, 2.0]]}]}
    repo = _tree(tmp_path, {
        "tests/test_x.py": "X = 1\n",
        "tests/golden/ok.json": json.dumps({**lm, "provenance": "synthetic"}),
        "tests/golden/ok_meta.json": json.dumps({"meta": {"provenance": "cc0"}, "vertices": [[0, 0, 0]]}),
        "tests/golden/metrics.json": json.dumps({"scenarios": {"a": {"rms": 1.0}}}),      # no geometry
        "tests/golden/missing.json": json.dumps(lm),
        "tests/golden/real.json": json.dumps({**lm, "provenance": "scraped"}),
        "tests/golden/nested.json": json.dumps({"runs": [{"detections": [[1, 2]]}]}),
        "tests/golden/mesh.obj": "v 0 0 0\n",
        "tests/golden/withside/head.obj": "v 0 0 0\n",
        "tests/golden/withside/PROVENANCE.json": json.dumps({"provenance": "consented"}),
        "tests/blender_stub/bpy/x.json": json.dumps(lm),                                   # stub: skipped
    })
    bad = ci.check_fixture_provenance(repo)
    names = sorted(Path(b.split(":")[0]).name for b in bad)
    assert names == ["mesh.obj", "missing.json", "nested.json", "real.json"], bad


def test_defaults_check_reports_a_default_without_source():
    """(c) A Default cannot be built without a badge and source (core.config), and the check reads the
    live registry: a registry entry that lost its source is reported."""
    from face3d.core import config
    with pytest.raises(ValueError):
        config.Default(1.0, "?", "src")
    with pytest.raises(ValueError):
        config.Default(1.0, config.BADGES[0], "")
    good = config.Default(1.0, config.BADGES[0], "test")
    object.__setattr__(good, "source", " ")
    config._REGISTRY["wp23_test.bad"] = good
    try:
        assert any("wp23_test.bad" in b for b in ci.check_defaults())
    finally:
        del config._REGISTRY["wp23_test.bad"]
    assert ci.check_defaults() == []


# ---------------------------------------------------------------------------- exports and packaging
def test_version_and_packaging_metadata():
    import face3d
    assert face3d.__version__ == "0.2.0"
    meta = tomllib.loads((REPO / "pyproject.toml").read_text())
    proj = meta["project"]
    assert proj["version"] == face3d.__version__ and proj["requires-python"] == ">=3.11"
    assert proj["license"] == {"text": "MIT"}                         # engine MIT (DESIGN 6.1, extension NOTICE)
    assert proj["dependencies"] == ["numpy>=1.24"]                      # engine: numpy + stdlib only
    assert proj["optional-dependencies"]["test"] == ["pytest>=7"]
    assert proj["scripts"]["face3d"] == "face3d.pipeline.cli:main"
    from face3d.pipeline.cli import main
    assert callable(main)
    data = meta["tool"]["setuptools"]["package-data"]["face3d"]
    assert set(data) == {"data/*.json", "schemes/*.json", "core/defaults.toml"}
    for pattern in data:                                                # every pattern matches a real file
        assert list((REPO / "face3d").glob(pattern)), pattern
    ini = meta["tool"]["pytest"]["ini_options"]
    assert ini["testpaths"] == ["tests"] and any(m.startswith("slow:") for m in ini["markers"])


@pytest.mark.parametrize("pkg", SUBPACKAGES)
def test_subpackage_exports(pkg):
    """Every subpackage re-exports its modules' public API (DESIGN 2.3): ``__all__`` resolves, covers
    each module's own ``__all__`` (unless the name is a submodule or exported by an earlier module), and
    submodules stay importable as attributes."""
    mod = importlib.import_module(f"face3d.{pkg}")
    assert mod.__doc__ and mod.__all__ == sorted(set(mod.__all__))
    for name in mod.__all__:
        assert hasattr(mod, name), name
    subs = sorted(p.stem for p in (REPO / "face3d" / pkg).glob("*.py") if p.stem != "__init__")
    assert subs
    for sub in subs:
        m = importlib.import_module(f"face3d.{pkg}.{sub}")
        assert isinstance(getattr(mod, sub), types.ModuleType) and getattr(mod, sub) is m
        for name in getattr(m, "__all__", []):
            if name in subs:
                continue
            assert name in mod.__all__, (pkg, sub, name)


def test_export_name_collisions():
    """Regression (WP-23 review): ``face3d.solve.MIRROR`` is the mirror-test config namespace that
    ``solve.mirror.__all__`` declares public (not ``bundle``'s x-flip vector, exported as ``MIRROR_FLIP``),
    and ``from face3d import *`` neither imports the subpackages nor rebinds ``eval`` / ``io``."""
    import numpy as np
    import face3d
    import face3d.solve as fs
    from face3d.core.config import Namespace
    from face3d.solve import bundle, mirror
    assert fs.MIRROR is mirror.MIRROR and isinstance(fs.MIRROR, Namespace)
    assert fs.MIRROR_FLIP is bundle.MIRROR and np.array_equal(fs.MIRROR_FLIP, [-1.0, 1.0, 1.0])
    for name in ("NOISE", "ROBUST", "SCALE", "EXPRESSION", "CAMERA_MODEL", "OBS", "NBV", "BUNDLE", "MIRROR"):
        assert isinstance(getattr(fs, name), Namespace), name
    ns: dict = {}
    exec("from face3d import *", ns)
    assert set(ns) - {"__builtins__"} == {"__version__", "SUBPACKAGES"}
    assert "eval" not in ns and "io" not in ns
    assert set(face3d.SUBPACKAGES) == set(SUBPACKAGES)
    code = "import sys, face3d; from face3d import *; print(sorted(m for m in sys.modules if m.startswith('face3d.')))"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=str(REPO), check=True)
    assert out.stdout.strip() == "[]"


def test_legacy_package_exports_still_work():
    """The exports that existed before WP-23 (M0 engine and the legacy tests' imports)."""
    from face3d.fit import (ContourView, Template, TemplateFit, edge_faces, fit_silhouettes,  # noqa: F401
                            fit_template_to_landmarks, silhouette_vertices)
    from face3d.geometry import (Camera, RBFWarp, apply_similarity, euler_xyz_deg, focal_35mm_from_px,  # noqa: F401
                                 focal_px_from_35mm, focal_px_from_sensor, look_at, nearest_rotation,
                                 procrustes_rmse, rodrigues, rotation_from_euler_deg, rotation_to_rvec,
                                 to_blender_camera, umeyama)
    from face3d.io import ExifInfo, read_exif  # noqa: F401
    from face3d.mesh import (Mesh, ReducedDeformer, Sparse, cg, cotan_laplacian, farthest_point_sample,  # noqa: F401
                             laplacian_deform, read_obj, smooth, uniform_laplacian, uv_sphere, write_obj)
    from face3d.solve import (BundleResult, LMResult, PhotoLandmarks, PnPResult, Priors, ViewObs,  # noqa: F401
                              bundle_adjust, levenberg_marquardt, numeric_jacobian, reconstruct_landmarks,
                              solve_pnp, triangulate_dlt, triangulate_points)
    # a few of the DESIGN 2.3 additions, by package
    from face3d.core import ConsentRecord, Default, StageCache, network_guard, register_defaults  # noqa: F401
    from face3d.eval import axis_coverage, nees, surface_error  # noqa: F401
    from face3d.model import FactorPrior, TemplateKit, build_procedural_head, load_scheme  # noqa: F401
    from face3d.pipeline import Project, run_job, run_pipeline  # noqa: F401
    from face3d.solve import NoiseModel, RobustSchedule, assess, mirror_test, next_best_view  # noqa: F401
    from face3d.testbed import FAULT_MATRIX, build_scorecard, out_of_prior_subject  # noqa: F401


def test_importing_face3d_is_light():
    """``import face3d`` pulls in no subpackage (the add-on probes the engine first; DESIGN 6.3)."""
    import subprocess
    code = ("import sys, face3d; "
            "print(sorted(m for m in sys.modules if m.startswith('face3d.')), 'numpy' in sys.modules)")
    out = subprocess.run([sys.executable, "-c", code], cwd=REPO, capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "[] False"
