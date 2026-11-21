# SPDX-License-Identifier: GPL-3.0-or-later
"""Project and consent operators, plus the helpers every ops_* module shares (DESIGN 6.4).

Conventions
-----------
* A project is a folder holding ``project.json`` (face3d.pipeline.project); the scene stores only
  its path (``scene.face3d.project_path``). Engine state is re-read from disk, never cached here.
* Consent lives in ``<project>/consent.json`` (a face3d.core.policy.ConsentRecord as JSON). The
  default is DENY: a project without a record, or with a record whose scopes lack RECONSTRUCT,
  blocks every step that needs photos (eth F1-F3, DESIGN D-25).
* Operators report only through message keys (`messages.MESSAGES`); `deny`/`fail`/`info` are the
  only ways to speak to the user, and tracebacks never reach the UI.
* Main-thread mutating operators carry ``{'REGISTER', 'UNDO'}``; job launchers do not.

Shared helpers (used by the other ops modules): `deny`, `fail`, `info`, `project_root`,
`load_project`, `load_consent`, `consent_state`, `job_is_running`, `active_photo_id`.
"""
import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path

import bpy
from bpy.props import BoolProperty, EnumProperty, IntProperty, StringProperty

from . import ensure_engine_on_path
from .messages import MESSAGES, text

ensure_engine_on_path()

from face3d.core import policy  # noqa: E402
from face3d.core.policy import ConsentRecord, DataClass, Scope  # noqa: E402
from face3d.pipeline.project import Project, ProjectError  # noqa: E402

CONSENT_FILE = "consent.json"
#: Consent text version and method written by this UI (provisional labels, not a legal text).
CONSENT_TEXT_VERSION = "ui-1-provisional"
CONSENT_METHOD = "blender_ui"
#: Retention default offered in the dialog (days). PROVISIONAL: engineering choice, DESIGN D-25 says
#: raw landmarks are session-only; this only labels how long the user intends to keep the project.
DEFAULT_RETENTION_DAYS = 30


# ------------------------------------------------------------------ reporting helpers
def deny(cls, key):
    """poll() helper: set the greyed-out explanation for ``key`` and return False."""
    cls.poll_message_set(MESSAGES[key])
    return False


def fail(op, key, **fmt):
    """Report ERROR with the text of ``key`` and return {'CANCELLED'}."""
    op.report({"ERROR"}, text(key, **fmt))
    return {"CANCELLED"}


def info(op, key, **fmt):
    """Report INFO with the text of ``key``."""
    op.report({"INFO"}, text(key, **fmt))


def warn(op, key, **fmt):
    """Report WARNING with the text of ``key``."""
    op.report({"WARNING"}, text(key, **fmt))


# ------------------------------------------------------------------ project / consent access
def settings(context):
    return context.scene.face3d


def project_root(context):
    """Project folder (Path) or None when no project is open."""
    p = settings(context).project_path
    if not p:
        return None
    root = Path(bpy.path.abspath(p)) if hasattr(bpy, "path") else Path(p)
    return root if (root / "project.json").is_file() else None


def load_project(context):
    """The open Project; raises ProjectError (a ValueError) when there is none or it is unreadable."""
    root = project_root(context)
    if root is None:
        raise ProjectError("no project")
    return Project.load(root)


def consent_path(root):
    return Path(root) / CONSENT_FILE


def load_consent(root):
    """ConsentRecord of the project or None (missing, unreadable or malformed: fail closed)."""
    f = consent_path(root)
    try:
        return ConsentRecord.from_json(f.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, KeyError):
        return None


def save_consent(root, rec):
    f = consent_path(root)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(rec.to_json(), encoding="utf-8")
    os.replace(tmp, f)


def consent_state(root, operation="reconstruct", photos_sha256=None, rights_basis=()):
    """(ok, message key or None) of the consent gate for ``operation`` (face3d.core.policy.check).

    ``photos_sha256=None`` checks scope, age and expiry only (the photo-coverage rule F2 is skipped);
    a list also requires every hash to be in the record. ``rights_basis`` (photo rights bases) is only
    needed for the texture gate (eth F7).
    """
    rec = load_consent(root) if root is not None else None
    if rec is None:
        return False, "consent_missing"
    shas = tuple(photos_sha256) if photos_sha256 is not None else tuple(rec.photo_sha256)
    res = policy.check(operation, rec, photos_sha256=shas, rights_basis=tuple(rights_basis),
                       now=datetime.now(timezone.utc))
    reasons = [r for r in res.reasons if not (photos_sha256 is None and "sha256" in r)]
    if not res.missing and not reasons:
        return True, None
    if res.missing:
        return False, "consent_missing" if operation == "reconstruct" else "consent_denied_scope"
    if any("expired" in r for r in reasons):
        return False, "consent_expired"
    if any("sha256" in r for r in reasons):
        return False, "photo_not_consented"
    return False, "consent_denied_scope"


def job_is_running(context):
    return settings(context).job.status == "running"


def active_photo_id(context):
    """Photo id of the scene camera (custom property ``f3d_photo_id``), else None."""
    cam = getattr(context.scene, "camera", None)
    if cam is not None and "f3d_photo_id" in cam:
        return cam["f3d_photo_id"]
    return None


def audit(project, event, data_class, sha256="", scope="RECONSTRUCT", detail=""):
    """Append one audit line (codes and hashes only, eth F19)."""
    project.audit_log().write(event, data_class, sha256, scope=scope, detail_code=detail)


def _reset_scene_state(s):
    s.photos.clear()
    s.pins.clear()
    s.cards.clear()


# ------------------------------------------------------------------ operators
class FACE3D_OT_project_new(bpy.types.Operator):
    bl_idname = "face3d.project_new"
    bl_label = "New Face3D Project"
    bl_description = "Create a project folder with an empty project file"
    bl_options = {"REGISTER", "UNDO"}

    directory: StringProperty(name="Folder", subtype="DIR_PATH")

    @classmethod
    def poll(cls, context):
        if job_is_running(context):
            return deny(cls, "job_running")
        return True

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        try:
            if not self.directory:
                return fail(self, "project_dir_missing")
            folder = Path(bpy.path.abspath(self.directory)) if hasattr(bpy, "path") else Path(self.directory)
            folder.mkdir(parents=True, exist_ok=True)
            prj = Project()
            prj.save(folder)
            s = settings(context)
            s.project_path = str(folder)
            _reset_scene_state(s)
            s.rail_stage = "consent"
            info(self, "project_created")
            return {"FINISHED"}
        except (OSError, ProjectError, ValueError):
            return fail(self, "project_load_failed")
        except Exception:  # noqa: BLE001 - UI boundary: never leak a traceback
            return fail(self, "internal_error")


class FACE3D_OT_consent_edit(bpy.types.Operator):
    bl_idname = "face3d.consent_edit"
    bl_label = "Edit Consent Record"
    bl_description = "Record who consented and what the photos may be used for (default: nothing)"
    bl_options = {"REGISTER", "UNDO"}

    subject_pseudonym: StringProperty(name="Subject (pseudonym)", default="subject")
    signer_role: EnumProperty(name="Signer", items=[(r, r.capitalize(), "") for r in policy.SIGNER_ROLES],
                              default="self")
    attested_age: IntProperty(name="Age (0 = not stated)", default=0, min=0, max=130)
    deceased: BoolProperty(name="Subject is deceased", default=False)
    allow_reconstruct: BoolProperty(name="Allow reconstruction from the photos", default=False)
    allow_texture: BoolProperty(name="Allow texture from the photos", default=False)
    allow_rig_animate: BoolProperty(name="Allow expression and rig keys", default=False)
    allow_store_raw: BoolProperty(name="Allow storing the original photos", default=False)
    retention_days: IntProperty(name="Retention (days)", default=DEFAULT_RETENTION_DAYS, min=0)
    revocation_contact: StringProperty(name="Revocation contact", default="")
    cover_project_photos: BoolProperty(name="Cover the photos already in the project", default=False)

    @classmethod
    def poll(cls, context):
        if project_root(context) is None:
            return deny(cls, "no_project")
        if job_is_running(context):
            return deny(cls, "job_running")
        return True

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        try:
            root = project_root(context)
            if root is None:
                return fail(self, "no_project")
            prj = Project.load(root)
            old = load_consent(root)
            scopes = Scope(0)
            for flag, sc in ((self.allow_reconstruct, Scope.RECONSTRUCT), (self.allow_texture, Scope.TEXTURE),
                             (self.allow_rig_animate, Scope.RIG_ANIMATE), (self.allow_store_raw, Scope.STORE_RAW)):
                if flag:
                    scopes |= sc
            shas = set(old.photo_sha256) if old is not None else set()
            if self.cover_project_photos:
                shas |= {p.sha256 for p in prj.photos}
            signed = datetime.now(timezone.utc).isoformat(timespec="seconds")
            cid = hashlib.sha256(("%s|%s|%d" % (self.subject_pseudonym, signed, int(scopes))).encode()).hexdigest()[:16]
            rec = ConsentRecord(
                consent_id=cid, subject_pseudonym=self.subject_pseudonym, signer_role=self.signer_role,
                consent_text_version=CONSENT_TEXT_VERSION, method=CONSENT_METHOD, signed_at=signed,
                expires_at=None, jurisdiction_tags=[], photo_sha256=sorted(shas),
                retention_days=int(self.retention_days), revocation_contact=self.revocation_contact,
                scopes=scopes, attested_age=self.attested_age or None, deceased=bool(self.deceased))
            save_consent(root, rec)
            prj.consent_id = cid
            prj.save()
            audit(prj, "consent_recorded", DataClass.PERSONAL_IMAGE, "", "RECONSTRUCT",
                  "scopes_%d" % int(scopes))
            info(self, "consent_saved")
            return {"FINISHED"}
        except (OSError, ProjectError, ValueError, TypeError):
            return fail(self, "project_load_failed")
        except Exception:  # noqa: BLE001
            return fail(self, "internal_error")


CLASSES = (FACE3D_OT_project_new, FACE3D_OT_consent_edit)


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
