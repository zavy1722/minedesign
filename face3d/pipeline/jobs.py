"""Job-folder protocol and the isolated-launcher contract (DESIGN 3.2 "Job folder", 6.3, D-24; eth A7, F19).

A job folder (``<project>/jobs/<uuid>/``) holds::

    job.json        {format: 'face3d.job', version: 1, stage, config, seed, inputs}
    inputs.npz      the arrays referenced by ``{"$array": name}`` placeholders inside job.json
    progress.jsonl  one JSON object per line: {t, stage, frac, msg_key}   (append-only)
    cancel          sentinel file: created by the caller to stop the job
    result.json + arrays.npz   written atomically (tmp then os.replace; arrays first) on success
    error.json      {code, msg_key, stage} on failure: no paths, arrays or coordinates (eth A7/F19)

The launcher contract (D-24): the caller runs ``[sys.executable, '-I', launcher.py, job_dir]`` where
``launcher.py`` inserts the engine directory into ``sys.path`` and calls :func:`run_job` (exit code
0 = success).  Nothing here reads the network or the environment beyond thread-count defaults.

``stage``: a pipeline stage name (``face3d.pipeline.stages.ORDER``; the job runs every stage up to it)
or ``'selftest'`` (a cancellable idle loop used by the protocol tests and launcher self-checks:
``config = {seconds, tick}``).  For a pipeline job ``inputs`` is::

    {"project": "<path to project.json>", "landmark_sets": {photo id: plain LandmarkSet},
     "consent": "<ConsentRecord JSON>" | None, "apply_mirror": [photo id, ...], "texture": bool,
     "extra": {...}}

Cancellation is checked between stages, through :func:`stages.lm_cancel_hook` before every
Levenberg-Marquardt outer iteration of the bundle solver, and through :func:`stages.poll_cancel` inside the
long non-LM loops (texture projection per view and phase, LOVO re-solves, fit, handoff).  The seed of
``job.json`` is the run's seed; ``error.json`` names the stage that was running when the job failed or was
cancelled.  Landmark arrays are BIOMETRIC_GEOMETRY with
TTL 0: ``inputs.npz`` is deleted when the job ends (success or failure) unless
``config['keep_inputs']`` is true.

Exit codes: 0 ok, 1 internal error, 2 invalid job or project, 3 consent refused, 4 cancelled.
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")      # small matrices: single-thread BLAS is much faster (tests/conftest)

import json
import time
import uuid
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from face3d.core.policy import ConsentRecord
from face3d.core.schema import FormatError, dump_json, load_json, save_arrays

JOB_FORMAT = "face3d.job"
JOB_VERSION = 1
LICENCE = "user-data (private; not for redistribution)"
EXIT_OK, EXIT_ERROR, EXIT_INVALID, EXIT_CONSENT, EXIT_CANCELLED = 0, 1, 2, 3, 4
_ARRAY_KEY = "$array"


# ------------------------------------------------------------------ job files
def _split_arrays(obj: Any, arrays: dict) -> Any:
    if isinstance(obj, np.ndarray):
        name = f"a{len(arrays):05d}"
        arrays[name] = obj
        return {_ARRAY_KEY: name}
    if isinstance(obj, Mapping):
        return {str(k): _split_arrays(v, arrays) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_split_arrays(v, arrays) for v in obj]
    if isinstance(obj, np.generic):
        return obj.item()
    return obj


def _join_arrays(obj: Any, arrays: Mapping[str, np.ndarray]) -> Any:
    if isinstance(obj, dict):
        if set(obj) == {_ARRAY_KEY}:
            return arrays[obj[_ARRAY_KEY]]
        return {k: _join_arrays(v, arrays) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_join_arrays(v, arrays) for v in obj]
    return obj


def new_job_dir(project_root: str | Path) -> Path:
    """``<project>/jobs/<uuid>/`` (created)."""
    d = Path(project_root) / "jobs" / uuid.uuid4().hex
    d.mkdir(parents=True, exist_ok=False)
    return d


def write_job(job_dir: str | Path, stage: str | list, inputs: Mapping[str, Any], config: Mapping[str, Any] | None,
              seed: int) -> Path:
    """Write ``job.json`` (and ``inputs.npz`` for the arrays in ``inputs``) into ``job_dir``."""
    d = Path(job_dir)
    d.mkdir(parents=True, exist_ok=True)
    arrays: dict[str, np.ndarray] = {}
    body = _split_arrays(dict(inputs), arrays)
    if arrays:
        save_arrays(d / "inputs.npz", **arrays)
    doc = {"format": JOB_FORMAT, "version": JOB_VERSION, "licence": LICENCE, "stage": stage,
           "config": dict(config or {}), "seed": int(seed), "inputs": body}
    tmp = d / "job.json.tmp"
    dump_json(doc, tmp)
    os.replace(tmp, d / "job.json")
    return d / "job.json"


def read_job(job_dir: str | Path) -> dict:
    """Load ``job.json`` with its arrays re-attached (:class:`FormatError` when invalid)."""
    d = Path(job_dir)
    doc = load_json(d / "job.json", expect_format=JOB_FORMAT, max_version=JOB_VERSION)
    arrays: dict[str, np.ndarray] = {}
    npz = d / "inputs.npz"
    if npz.is_file():
        with np.load(npz, allow_pickle=False) as z:
            arrays = {k: z[k] for k in z.files}
    doc["inputs"] = _join_arrays(doc.get("inputs", {}), arrays)
    return doc


def read_progress(job_dir: str | Path, offset: int = 0) -> tuple[list[dict], int]:
    """Parse the complete lines of ``progress.jsonl`` after byte ``offset``; returns (lines, new_offset).

    A trailing partial line (writer mid-append) is left for the next call.
    """
    p = Path(job_dir) / "progress.jsonl"
    if not p.is_file():
        return [], offset
    with open(p, "rb") as f:
        f.seek(offset)
        data = f.read()
    cut = data.rfind(b"\n")
    if cut < 0:
        return [], offset
    out = []
    for line in data[:cut + 1].splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out, offset + cut + 1


class _Progress:
    def __init__(self, job_dir: Path):
        self.path = job_dir / "progress.jsonl"

    def __call__(self, stage: str, frac: float, msg_key: str) -> None:
        rec = {"t": round(time.time(), 3), "stage": str(stage), "frac": round(float(frac), 4),
               "msg_key": str(msg_key)}
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, sort_keys=True) + "\n")
            f.flush()


def _write_error(job_dir: Path, code: str, stage: str) -> None:
    """error.json: a code, a message key and the stage name only (no paths, arrays or coordinates)."""
    doc = {"code": str(code), "msg_key": f"job.error.{code}", "stage": str(stage)}
    tmp = job_dir / "error.json.tmp"
    tmp.write_text(json.dumps(doc, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, job_dir / "error.json")


def _cleanup_inputs(job_dir: Path, config: Mapping[str, Any]) -> None:
    if not config.get("keep_inputs"):
        (job_dir / "inputs.npz").unlink(missing_ok=True)


# ------------------------------------------------------------------ run
def run_job(job_dir: str | Path) -> int:
    """Run the job in ``job_dir``; returns the exit code (see module docstring)."""
    from face3d.pipeline import stages as S
    from face3d.pipeline.project import Project, ProjectError

    d = Path(job_dir)
    progress = _Progress(d)
    stage_name = "job"
    config: Mapping[str, Any] = {}
    cancel_file = d / "cancel"
    current = ["job"]                      # the stage being started / run: named in error.json and cancel lines

    def track(stage: str, frac: float, msg_key: str) -> None:
        if stage in S.ORDER:
            current[0] = stage
        progress(stage, frac, msg_key)

    def cancelled() -> bool:
        return cancel_file.exists()

    def check() -> None:
        if cancelled():
            raise S.Cancelled()

    try:
        job = read_job(d)
        config = job.get("config", {})
        stage = job["stage"]
        stage_name = stage[-1] if isinstance(stage, list) else str(stage)
        inp = job.get("inputs", {})
        progress(stage_name, 0.0, "job.start")
        check()
        if stage_name == "selftest":
            rc = _selftest(d, config, progress, check)
            _cleanup_inputs(d, config)
            return rc
        if stage_name not in S.ORDER:
            raise FormatError("unknown stage")
        ppath = Path(inp["project"])
        ppath = ppath if ppath.is_absolute() else d / ppath
        project = Project.load(ppath)
        consent = ConsentRecord.from_json(inp["consent"]) if inp.get("consent") else None
        sets = _plain_to_sets(inp.get("landmark_sets") or {})
        # the job's seed (job.json) governs the run; the project file is never rewritten with it
        run = S.run_pipeline(project, until=stage_name, cache=None, apply_mirror=list(inp.get("apply_mirror", [])),
                             landmark_sets=sets, consent=consent, config=config.get("stages"),
                             texture=bool(inp.get("texture")), extra_inputs=inp.get("extra"),
                             progress=track, cancel=cancelled, seed=job.get("seed"))
        check()
        _write_job_result(d, run, stage_name)
        progress(stage_name, 1.0, "job.done")
        _cleanup_inputs(d, config)
        return EXIT_OK
    except S.Cancelled:
        stage_name = current[0] if current[0] != "job" else stage_name
        progress(stage_name, 1.0, "job.cancelled")
        _write_error(d, "cancelled", stage_name)
        _cleanup_inputs(d, config)
        return EXIT_CANCELLED
    except S.ConsentError:
        stage_name = current[0] if current[0] != "job" else stage_name
        _write_error(d, "consent_refused", stage_name)
        _cleanup_inputs(d, config)
        return EXIT_CONSENT
    except (FormatError, ProjectError, KeyError, ValueError, FileNotFoundError, S.PipelineError, OSError,
            TypeError) as e:
        code = e.code if isinstance(e, S.PipelineError) else "invalid_input"
        _write_error(d, code, current[0] if current[0] != "job" else stage_name)
        _cleanup_inputs(d, config)
        return EXIT_INVALID
    except np.linalg.LinAlgError:
        _write_error(d, "numerical", current[0] if current[0] != "job" else stage_name)
        _cleanup_inputs(d, config)
        return EXIT_ERROR
    except Exception:                                     # noqa: BLE001 - job boundary: report a code only
        _write_error(d, "internal", current[0] if current[0] != "job" else stage_name)
        _cleanup_inputs(d, config)
        return EXIT_ERROR


def _plain_to_sets(plain: Mapping[str, Any]) -> dict:
    """Plain landmark sets (job inputs) back to :class:`LandmarkSet` objects."""
    from face3d.io.landmarks import Face, LandmarkSet
    out = {}
    for pid, d in plain.items():
        faces = [Face(score=float(f["score"]), uv=np.asarray(f["uv"], float),
                      visible=None if f.get("visible") is None else np.asarray(f["visible"], bool),
                      cov=None if f.get("cov") is None else np.asarray(f["cov"], float),
                      blendshapes=f.get("blendshapes")) for f in d["faces"]]
        out[pid] = LandmarkSet(d["scheme"], d.get("detector", {}), d.get("image", {}), faces)
    return out


def _write_job_result(d: Path, run, stage_name: str) -> None:
    """result.json + arrays.npz, atomically (arrays first; result.json presence marks completion)."""
    from face3d.pipeline import stages as S
    rep = run.outputs.get("report")
    if rep is not None:
        S.write_result_files(d, rep)
        return
    last = run.outputs.get(stage_name) or {}
    arrays = {k: v for k, v in last.items() if isinstance(v, np.ndarray) and not k.startswith("_")}
    plain = {k: v for k, v in last.items() if not isinstance(v, np.ndarray) and not k.startswith("_")}
    tmp = d / "arrays.npz.tmp"
    manifest = save_arrays(tmp, **arrays) if arrays else {}
    if arrays:
        os.replace(tmp, d / "arrays.npz")
    doc = {"format": "face3d.job_result", "version": 1, "licence": LICENCE, "stage": stage_name,
           "executed": run.executed, "cache_hits": run.cache_hits, "arrays": manifest}
    summary = {}
    for k, v in plain.items():
        try:
            json.dumps(v)
            summary[k] = v
        except (TypeError, ValueError):
            continue
    doc["outputs"] = summary
    tmp_js = d / "result.json.tmp"
    dump_json(doc, tmp_js)
    os.replace(tmp_js, d / "result.json")


def _selftest(d: Path, config: Mapping[str, Any], progress, check) -> int:
    """Cancellable idle loop: ``seconds`` of ``tick`` second sleeps with progress lines."""
    seconds = float(config.get("seconds", 1.0))
    tick = float(config.get("tick", 0.05))
    t0 = time.time()
    last = -1.0
    while True:
        el = time.time() - t0
        if el >= seconds:
            break
        check()
        if el - last >= 0.25:
            progress("selftest", min(el / seconds, 1.0), "job.selftest.tick")
            last = el
        time.sleep(tick)
    arr = np.arange(3, dtype=np.float64)
    save_arrays(d / "arrays.npz.tmp", x=arr)
    os.replace(d / "arrays.npz.tmp", d / "arrays.npz")
    doc = {"format": "face3d.job_result", "version": 1, "licence": LICENCE, "stage": "selftest",
           "executed": ["selftest"], "cache_hits": [], "arrays": {}, "outputs": {"seconds": seconds}}
    dump_json(doc, d / "result.json.tmp")
    os.replace(d / "result.json.tmp", d / "result.json")
    progress("selftest", 1.0, "job.done")
    return EXIT_OK


__all__ = ["write_job", "read_job", "run_job", "read_progress", "new_job_dir", "JOB_FORMAT", "JOB_VERSION",
           "EXIT_OK", "EXIT_ERROR", "EXIT_INVALID", "EXIT_CONSENT", "EXIT_CANCELLED"]
