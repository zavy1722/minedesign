# SPDX-License-Identifier: GPL-3.0-or-later
"""Solve, fit, texture and cancel job launchers; decision cards (DESIGN 6.3, 6.4, D-10).

Conventions
-----------
* `solve`, `fit` and `texture_project` only START a background job (JobRunner, WP-21); they carry no
  UNDO flag. Results are applied by `face3d.apply_result` (ops_apply). Both `solve` and `fit` run the
  engine pipeline up to ``report`` (cameras, shape keys and the claims ledger come from one run); `fit`
  can additionally request the limit-fitted cage (``handoff.cage``, face3d.mesh.subdiv.fit_cage_to_limit)
  and `texture_project` adds the texture stage (consent scope TEXTURE and the photo rights, eth F7).
* Job inputs are the job protocol of face3d.pipeline.jobs: project.json path, plain landmark sets (session
  data, D-25), the consent record JSON, ``apply_mirror = []``. A mirror flip is applied ONLY through a
  recorded decision (D-10): the engine reads ``project.decisions``; this UI never passes a flip itself.
* Cards (`F3DCard`) carry QA findings and mirror suggestions. `card_accept` / `card_dismiss` are the only
  way a card changes anything: accepting a mirror card records ``mirror_flip`` (dismissing records
  ``mirror_keep``) in ``project.decisions`` and the audit log (hash + code only, eth F19). The engine
  never flips on its own.
"""
import json
import os

import bpy
from bpy.props import BoolProperty, IntProperty

from . import ensure_engine_on_path
from . import ops_landmarks
from . import ops_photos
from . import ops_project as P
from .jobs import CANCEL_SENTINEL, JobRunner

ensure_engine_on_path()

from face3d.pipeline.project import ProjectError  # noqa: E402
from face3d.pipeline.stages import landmark_set_to_plain  # noqa: E402

MIRROR_CODE = "MIRROR"
#: {project path string: JobRunner}; one runner per project so a running job survives panel redraws.
RUNNERS = {}


def runner(context):
    path = str(P.project_root(context))
    r = RUNNERS.get(path)
    if r is None:
        r = RUNNERS[path] = JobRunner(path)
    return r


def missing_landmark_photos(context):
    """(included photo ids without an imported landmark set, number of included photos).

    The engine fits ONLY from imported landmark sets (stage_landmarks raises ``missing_landmarks`` for every
    usable photo without one); pins refine a set, they never replace it. The rail applies the same rule.
    """
    s = P.settings(context)
    sets = ops_landmarks.session_sets(context)
    inc = [p.id for p in s.photos if p.include != "exclude"]
    return [pid for pid in inc if pid not in sets], len(inc)


def _launch_gate(cls, context, operation="reconstruct"):
    """Shared poll: returns True or denies with the reason (project, consent, photos, landmarks, job)."""
    root = P.project_root(context)
    if root is None:
        return P.deny(cls, "no_project")
    if P.job_is_running(context):
        return P.deny(cls, "job_running")
    s = P.settings(context)
    ok, key = P.consent_state(root, operation, None)
    if not ok:
        return P.deny(cls, key)
    if not len(s.photos):
        return P.deny(cls, "no_photos")
    shas = [p.sha256 for p in s.photos if p.include != "exclude"]
    ok, key = P.consent_state(root, "reconstruct", shas)
    if not ok:
        return P.deny(cls, key)
    missing, n_inc = missing_landmark_photos(context)
    if missing:
        return P.deny(cls, "no_landmarks" if len(missing) == n_inc else "landmarks_incomplete")
    return True


def build_inputs(context, project, consent, texture=False):
    """Job inputs (face3d.pipeline.jobs protocol). Landmark sets are session data and travel in the job."""
    ids = {p.id for p in project.photos}
    sets = {pid: landmark_set_to_plain(ls) for pid, ls in ops_landmarks.session_sets(context).items() if pid in ids}
    return {"project": str(project.path), "landmark_sets": sets, "consent": consent.to_json(),
            "apply_mirror": [], "texture": bool(texture), "extra": {}}


def _launch(op, context, config, texture=False):
    try:
        prj = P.load_project(context)
        consent = P.load_consent(prj.root)
        if consent is None:
            return P.fail(op, "consent_missing")
        prj.save()                                            # pins and decisions are on disk before the job
        r = runner(context)
        job_dir = r.start("report", build_inputs(context, prj, consent, texture), config, prj.seed)
        if job_dir is None:
            return P.fail(op, "job_failed" if r.status == "failed" else "job_running")
        P.info(op, "job_started")
        return {"FINISHED"}
    except (ProjectError, OSError, ValueError, TypeError):
        return P.fail(op, "job_failed")
    except Exception:  # noqa: BLE001 - UI boundary
        return P.fail(op, "internal_error")


class FACE3D_OT_solve(bpy.types.Operator):
    bl_idname = "face3d.solve"
    bl_label = "Solve Cameras"
    bl_description = "Solve cameras and shape from the photos and pins (background job)"
    bl_options = {"REGISTER"}

    keyed: BoolProperty(default=False, options={"HIDDEN"})

    @classmethod
    def poll(cls, context):
        return _launch_gate(cls, context)

    def invoke(self, context, event):
        if self.keyed and not P.keyed_active(context):
            return {"PASS_THROUGH"}
        return self.execute(context)

    def execute(self, context):
        return _launch(self, context, {})


class FACE3D_OT_fit(bpy.types.Operator):
    bl_idname = "face3d.fit"
    bl_label = "Fit Shape"
    bl_description = "Fit the head shape and prepare the shape keys (background job)"
    bl_options = {"REGISTER"}

    cage: BoolProperty(name="Limit-fitted cage", description="Also compute the Multires cage for sculpting "
                       "(needs an all-quad template)", default=False)

    @classmethod
    def poll(cls, context):
        return _launch_gate(cls, context)

    def execute(self, context):
        cfg = {"stages": {"handoff": {"cage": True}}} if self.cage else {}
        return _launch(self, context, cfg)


class FACE3D_OT_texture_project(bpy.types.Operator):
    bl_idname = "face3d.texture_project"
    bl_label = "Project Texture"
    bl_description = "Project a texture from the photos (needs the texture consent scope; background job)"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        if not _launch_gate(cls, context):
            return False
        root = P.project_root(context)
        try:
            rights = [p.rights_basis for p in P.load_project(context).photos]
        except ProjectError:
            return P.deny(cls, "no_project")
        ok, key = P.consent_state(root, "texture", None, rights)
        return True if ok else P.deny(cls, key)

    def execute(self, context):
        return _launch(self, context, {}, texture=True)


class FACE3D_OT_job_cancel(bpy.types.Operator):
    bl_idname = "face3d.job_cancel"
    bl_label = "Cancel Job"
    bl_description = "Stop the running job; the process is killed after one second if it does not stop"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        if P.project_root(context) is None:
            return P.deny(cls, "no_project")
        if not P.job_is_running(context):
            return P.deny(cls, "job_not_running")
        return True

    def execute(self, context):
        try:
            if reconcile_job(context.scene):                   # 'running' in the file, but nothing is running
                P.info(self, "job_reset")
                return {"FINISHED"}
            runner(context).cancel()
            P.info(self, "job_cancelling")
            return {"FINISHED"}
        except OSError:
            return P.fail(self, "job_failed")


def resolved_job_status(job_dir):
    """Status a job folder implies once nothing runs it any more: ready / cancelled / failed / idle."""
    if not job_dir:
        return "idle"
    if os.path.exists(os.path.join(job_dir, "result.json")):
        return "ready"
    if os.path.exists(os.path.join(job_dir, CANCEL_SENTINEL)):
        return "cancelled"
    if os.path.exists(os.path.join(job_dir, "error.json")):
        return "failed"
    return "idle"


def reconcile_job(scene):
    """Reset a stale 'running' status (F3DJob.status is saved in the .blend; RUNNERS and the poll timer are not).

    A file saved during a solve, a crash, or loading another file leaves 'running' behind with no JobRunner
    to finish it, which would deny every operator for good. When no live runner exists for the project the
    status is resolved from the job folder (result.json -> ready, cancel file -> cancelled, error.json ->
    failed, else idle). Returns True when the status was changed. Never called from poll().
    """
    st = scene.face3d
    job = st.job
    if job.status != "running":
        return False
    r = RUNNERS.get(str(st.project_path))
    if r is not None and r.status == "running":
        return False
    job.status = resolved_job_status(job.job_dir)
    if job.status == "failed":
        try:
            with open(os.path.join(job.job_dir, "error.json"), encoding="utf-8") as fh:
                job.msg_key = str(json.load(fh).get("msg_key") or "job_failed")
        except (OSError, ValueError, AttributeError):
            job.msg_key = "job_failed"
    elif job.status == "cancelled":
        job.msg_key = "job.error.cancelled"
    return True


def _load_post(*_args):
    try:
        for sc in bpy.data.scenes:
            reconcile_job(sc)
    except Exception:  # noqa: BLE001 - a load handler must never raise
        pass


_persistent = getattr(bpy.app.handlers, "persistent", lambda f: f)
_load_post = _persistent(_load_post)


# ------------------------------------------------------------------ cards
def cards_from_result(context, result):
    """Add mirror cards of a result (``result['cards']``); returns the new cards.

    Only suggestions that still need a user decision become cards: ``suggest_flip`` (not yet applied),
    ``undetermined`` and ``unverifiable``. A photo that already has a recorded mirror decision, or an open
    card, gets none. Creating a card changes nothing; the engine never flips by itself (D-10).
    """
    s = P.settings(context)
    try:
        prj = P.load_project(context)
    except ProjectError:
        return []
    out = []
    for c in result.get("cards", []) or []:
        pid, dec = c.get("photo"), c.get("decision")
        key = {"suggest_flip": "mirror_suggest", "undetermined": "mirror_undetermined",
               "unverifiable": "mirror_unverifiable"}.get(dec)
        if key is None or c.get("applied") or prj.mirror_state(pid) is not None:
            continue
        if any(x.code == MIRROR_CODE and x.photo_id == pid and not x.decided for x in s.cards):
            continue
        card = s.cards.add()
        card.code, card.msg_key, card.photo_id, card.decided = MIRROR_CODE, key, pid, False
        card.severity = "warn" if dec == "suggest_flip" else "info"
        out.append(card)
    return out


def _target_index(context, index):
    s = P.settings(context)
    if 0 <= index < len(s.cards) and not s.cards[index].decided:
        return index
    order = ops_photos.card_order(s.cards)
    cur = int(context.scene.get("f3d_review_idx", -1))
    if 0 <= cur < len(s.cards) and not s.cards[cur].decided:
        return cur
    return order[0] if order else -1


def _keyed_target(context):
    """Card a key press may decide: only the card under review, and only if it belongs to the active photo.

    A key press (Ctrl-Enter / Ctrl-Backspace) must never decide a card the user is not looking at (D-10):
    no fallback to the worst open card, and a stale or foreign review index fails with card_none.
    """
    s = P.settings(context)
    cur = int(context.scene.get("f3d_review_idx", -1))
    if 0 <= cur < len(s.cards) and not s.cards[cur].decided and s.cards[cur].photo_id == P.active_photo_id(context):
        return cur
    return -1


class _CardOp:
    index: IntProperty(name="Card", default=-1, description="-1 = the card under review")

    @classmethod
    def poll(cls, context):
        if P.project_root(context) is None:
            return P.deny(cls, "no_project")
        if not ops_photos.card_order(P.settings(context).cards):
            return P.deny(cls, "card_none")
        return True

    def invoke(self, context, event):
        if getattr(self, "keyed", False) and not P.keyed_active(context):
            return {"PASS_THROUGH"}
        return self.execute(context)

    def _index(self, context):
        return _keyed_target(context) if getattr(self, "keyed", False) else _target_index(context, self.index)


class FACE3D_OT_card_accept(_CardOp, bpy.types.Operator):
    bl_idname = "face3d.card_accept"
    bl_label = "Accept Finding"
    bl_description = "Accept the finding's suggestion (a mirror flip is recorded, never applied silently)"
    bl_options = {"REGISTER", "UNDO"}

    face_index: IntProperty(name="Face", default=0, min=0, description="Subject face for a multi-face card")
    keyed: BoolProperty(default=False, options={"HIDDEN"})

    def execute(self, context):
        try:
            s = P.settings(context)
            i = self._index(context)
            if i < 0:
                return P.fail(self, "card_none")
            card = s.cards[i]
            if card.code == MIRROR_CODE:
                prj = P.load_project(context)
                prj.record_decision("mirror_flip", card.photo_id, "user")
                prj.save()
                _set_photo_mirror(s, card.photo_id, "flip")
                P.info(self, "card_flip_recorded")
            elif card.code == "Q-FACES":
                if not ops_landmarks.choose_face(context, card.photo_id, self.face_index):
                    return P.fail(self, "no_landmarks")
                P.info(self, "card_accepted")
            else:
                P.info(self, "card_accepted")
            card.decided = True
            return {"FINISHED"}
        except (ProjectError, IndexError, KeyError):
            return P.fail(self, "card_none")
        except Exception:  # noqa: BLE001
            return P.fail(self, "internal_error")


class FACE3D_OT_card_dismiss(_CardOp, bpy.types.Operator):
    bl_idname = "face3d.card_dismiss"
    bl_label = "Dismiss Finding"
    bl_description = "Dismiss the finding (a mirror card records 'keep this photo as it is')"
    bl_options = {"REGISTER", "UNDO"}

    keyed: BoolProperty(default=False, options={"HIDDEN"})

    def execute(self, context):
        try:
            s = P.settings(context)
            i = self._index(context)
            if i < 0:
                return P.fail(self, "card_none")
            card = s.cards[i]
            if card.code == MIRROR_CODE:
                prj = P.load_project(context)
                prj.record_decision("mirror_keep", card.photo_id, "user")
                prj.save()
                _set_photo_mirror(s, card.photo_id, "keep")
                P.info(self, "card_keep_recorded")
            else:
                P.info(self, "card_dismissed")
            card.decided = True
            return {"FINISHED"}
        except (ProjectError, IndexError, KeyError):
            return P.fail(self, "card_none")
        except Exception:  # noqa: BLE001
            return P.fail(self, "internal_error")


def _set_photo_mirror(s, photo_id, value):
    for ph in s.photos:
        if ph.id == photo_id:
            ph.mirror_decision = value
    cam = ops_photos.camera_for_photo(photo_id)
    if cam is not None:                                   # the engine solves the flipped image: show it flipped
        for bg in cam.data.background_images:
            bg.use_flip_x = value == "flip"


CLASSES = (FACE3D_OT_solve, FACE3D_OT_fit, FACE3D_OT_texture_project, FACE3D_OT_job_cancel,
           FACE3D_OT_card_accept, FACE3D_OT_card_dismiss)


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)
    if _load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_load_post)


def unregister():
    if _load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_load_post)
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
