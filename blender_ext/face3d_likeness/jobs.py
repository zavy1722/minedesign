# SPDX-License-Identifier: GPL-3.0-or-later
"""Job runner for background stages (DESIGN 6.3, D-24; adapter over WP-20).

ADAPTER NOTE (WP-20 assumptions, all isolated in `_engine_jobs` and
`read_progress_budgeted`): written against the WP-20 spec, not its code.
* `face3d.pipeline.jobs.write_job(job_dir, stage, inputs, config, seed)`
* `face3d.pipeline.jobs.run_job(job_dir) -> int` (0 = success)
* job folder files: `job.json`, `progress.jsonl` (one JSON object per line:
  `{t, stage, frac, msg_key}`), `result.json` + `arrays.npz`,
  `error.json {code, msg_key, stage}`, and the `cancel` sentinel file.
Progress is read here with a byte offset and a time budget instead of
`read_progress` so that a huge progress file can never stall the UI thread.

Units: times in seconds (time.perf_counter), `frac` in [0, 1].
"""
import json
import os
import subprocess
import sys
import time
import uuid

import bpy

POLL_INTERVAL_S = 0.1
POLL_BUDGET_S = 0.020          # DESIGN 6.3 / bl A5: at most 20 ms of work per tick
KILL_AFTER_S = 1.0             # DESIGN 6.3: cancel kills the process after 1 s
_READ_CHUNK = 256 * 1024
CANCEL_SENTINEL = "cancel"


def launcher_path():
    """Absolute path of launcher.py next to this module."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "launcher.py")


def _engine_jobs():
    """Import face3d.pipeline.jobs (WP-20), putting the engine root on sys.path first."""
    from . import ensure_engine_on_path
    ensure_engine_on_path()
    import importlib
    return importlib.import_module("face3d.pipeline.jobs")


def read_progress_budgeted(job_dir, offset, budget_s=POLL_BUDGET_S, chunk=_READ_CHUNK):
    """Read complete progress lines from byte `offset` within a time budget.

    Returns (records, new_offset). A partial trailing line is left for the next
    call; malformed lines are skipped. Stops once `budget_s` is spent.
    """
    t0 = time.perf_counter()
    path = os.path.join(job_dir, "progress.jsonl")
    try:
        with open(path, "rb") as fh:
            fh.seek(offset)
            data = fh.read(chunk)
    except OSError:
        return [], offset
    records = []
    pos = 0
    while True:
        nl = data.find(b"\n", pos)
        if nl < 0:
            break
        line = data[pos:nl]
        pos = nl + 1
        if line.strip():
            try:
                rec = json.loads(line)
                if isinstance(rec, dict):
                    records.append(rec)
            except ValueError:
                pass
        if time.perf_counter() - t0 >= budget_s:
            break
    return records, offset + pos


class JobRunner:
    """Starts a job folder under `project_dir/jobs/<uuid>` and tracks it.

    status is one of idle/running/ready/failed/cancelled (the F3DJob enum).
    Results are applied by a separate operator (WP-22), never here.
    """

    def __init__(self, project_dir):
        self.project_dir = str(project_dir)
        self.job_dir = None
        self.stage = ""
        self.status = "idle"
        self.progress = 0.0
        self.msg_key = ""
        self.error = None
        self.proc = None
        self._offset = 0
        self._cancel_at = None

    # -------------------------------------------------------------- start
    def start(self, stage, inputs, config, seed):
        """Write the job folder and launch it; returns job_dir (None if refused/failed to spawn)."""
        if self.status == "running":
            return None     # refuse: a running job must be cancelled first (no orphaned process)
        ej = _engine_jobs()
        job_dir = os.path.join(self.project_dir, "jobs", uuid.uuid4().hex)
        os.makedirs(job_dir, exist_ok=True)
        ej.write_job(job_dir, stage, inputs, config, seed)
        self.job_dir, self.stage = job_dir, stage
        self._offset, self._cancel_at, self.error = 0, None, None
        self.progress, self.msg_key = 0.0, ""
        self.status = "running"
        self._push_props()
        if bpy.app.background:
            try:
                code = ej.run_job(job_dir)
            except Exception:  # run_job normally returns non-zero; never leak a traceback
                code = 1
            self._drain()
            self._finish(code)
            return job_dir
        try:
            self.proc = subprocess.Popen([sys.executable, "-I", launcher_path(), job_dir])
        except OSError:
            self.proc = None
            self.status = "failed"
            self.error = {"code": "spawn_failed", "msg_key": "job_failed", "stage": stage}
            self.msg_key = "job_failed"
            self._push_props()
            return None
        if not bpy.app.timers.is_registered(self.poll):
            bpy.app.timers.register(self.poll, first_interval=POLL_INTERVAL_S)
        return job_dir

    # -------------------------------------------------------------- polling
    def poll(self):
        """Timer callback: <= 20 ms of work. Returns 0.1 while running, None when finished."""
        t0 = time.perf_counter()
        self._kill_if_due()
        recs, self._offset = read_progress_budgeted(
            self.job_dir, self._offset, budget_s=POLL_BUDGET_S)
        self._note(recs)
        code = self.proc.poll() if self.proc is not None else 0
        if code is not None:
            more, self._offset = read_progress_budgeted(
                self.job_dir, self._offset,
                budget_s=max(0.0, POLL_BUDGET_S - (time.perf_counter() - t0)))
            self._note(more)
            if more:        # still unread progress: finish on a later tick
                self._push_props()
                return POLL_INTERVAL_S
            self._finish(code)
            return None
        self._push_props()
        return POLL_INTERVAL_S

    def _drain(self):
        while True:
            recs, self._offset = read_progress_budgeted(self.job_dir, self._offset, budget_s=1e9)
            if not recs:
                break
            self._note(recs)

    def _note(self, recs):
        if recs:
            last = recs[-1]
            try:
                self.progress = min(1.0, max(0.0, float(last.get("frac", self.progress))))
            except (TypeError, ValueError):
                pass
            self.msg_key = str(last.get("msg_key", self.msg_key))
            self.stage = str(last.get("stage", self.stage))

    def _finish(self, code):
        jd = self.job_dir
        if os.path.exists(os.path.join(jd, "result.json")) and not code:
            self.status = "ready"
            self.progress = 1.0
        elif os.path.exists(os.path.join(jd, CANCEL_SENTINEL)):
            self.status = "cancelled"
        else:
            self.status = "failed"
            try:
                with open(os.path.join(jd, "error.json"), encoding="utf-8") as fh:
                    err = json.load(fh)
                self.error = {k: err.get(k) for k in ("code", "msg_key", "stage")}
                self.msg_key = str(err.get("msg_key") or self.msg_key)
            except (OSError, ValueError, AttributeError):
                self.error = {"code": "exit_%s" % code, "msg_key": "job_failed", "stage": self.stage}
        self.proc = None
        self._push_props()

    # -------------------------------------------------------------- cancel
    def cancel(self):
        """Write the cancel sentinel; the process is killed after 1 s if still alive."""
        if self.job_dir is None or self.status != "running":
            return
        with open(os.path.join(self.job_dir, CANCEL_SENTINEL), "w", encoding="utf-8") as fh:
            fh.write("1")
        self._cancel_at = time.perf_counter()

    def _kill_if_due(self):
        if self._cancel_at is not None and self.proc is not None \
                and time.perf_counter() - self._cancel_at >= KILL_AFTER_S \
                and self.proc.poll() is None:
            self.proc.kill()

    # -------------------------------------------------------------- props
    def _push_props(self):
        try:
            job = bpy.context.scene.face3d.job
        except AttributeError:
            return
        job.job_dir = self.job_dir or ""
        job.stage = self.stage
        job.status = self.status
        job.progress = self.progress
        job.msg_key = self.msg_key
