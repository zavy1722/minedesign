# SPDX-License-Identifier: GPL-3.0-or-later
"""Translation-ready English strings for every report, poll message and rail label (DESIGN 6.4).

Every `self.report` and `poll_message_set` text in the extension is looked up here by a message
key (WP-22 rule); no module formats prose inline. Keys are plain identifiers, except the engine's
own keys, which are kept verbatim so a `Finding.msg_key` / `fix_key` / job `msg_key` can be looked
up directly: ``qa.<code>`` and ``qa.<code>.fix`` (face3d.qa.checks.Finding), ``job.error.<code>``
(face3d.pipeline.jobs error.json), ``ledger.why.*`` (face3d.fit.ledger).

Pure: no bpy, no engine import. `text(key, **fmt)` formats with ``str.format`` and never raises
(an unknown key returns the key itself, so a missing translation is visible but not fatal).
Wording is plain language (DESIGN H1-H9): ranges, not point values; no claim of accuracy.
"""

#: QA finding codes of face3d.qa.checks (DESIGN 4.1 table); each gets ``qa.<code>`` and ``qa.<code>.fix``.
QA_CODES = ("Q-BLINK", "Q-BLUR", "Q-CLIP", "Q-CONSENT", "Q-CROP", "Q-DATES", "Q-EXIF-NONE", "Q-FACES",
            "Q-FRONTCAM", "Q-GROUP-SPREAD", "Q-NEAR", "Q-ORIENT", "Q-PROCESS", "Q-RETOUCH", "Q-SMALL",
            "Q-WIDE")

_QA = {
    "Q-BLINK": ("Eyes look closed in this photo.", "Use a photo with open eyes; the eyelids are not used."),
    "Q-BLUR": ("This photo is blurrier than the rest of the set.",
               "Use a sharper photo if you have one; this one is down-weighted."),
    "Q-CLIP": ("Part of the skin is blown out to white or black.",
               "Texture is not taken from this photo; geometry is still used."),
    "Q-CONSENT": ("This photo is not covered by the consent record.",
                  "Edit the consent record to cover it, or remove the photo."),
    "Q-CROP": ("This photo looks cropped or digitally zoomed, so its focal length is less certain.",
               "Use the original, uncropped file if you can; the focal length uncertainty is widened."),
    "Q-DATES": ("These photos were taken far apart in time.",
                "The set is split into date groups, because faces change with age."),
    "Q-EXIF-NONE": ("No camera information was found in this photo.",
                    "The focal length is estimated from the pins instead, which is less certain."),
    "Q-FACES": ("More than one face was found in this photo.",
                "Pick the subject. The engine never fits a second face by itself."),
    "Q-FRONTCAM": ("This looks like a front-camera (selfie) photo.",
                   "Selfies can be mirrored; the mirror test will compare them with other photos."),
    "Q-GROUP-SPREAD": ("Photos from the same camera disagree about the focal length.",
                       "Check for crops or a different lens mode; the focal length is widened."),
    "Q-NEAR": ("The camera was very close to the face, which stretches perspective.",
               "Use photos taken from at least one metre away if you can."),
    "Q-ORIENT": ("The photo may be rotated or sideways.",
                 "Save it upright (for example as PNG) and add it again."),
    "Q-PROCESS": ("This photo was processed by an editor or portrait mode.",
                  "It is down-weighted and not used for texture."),
    "Q-RETOUCH": ("This photo looks retouched or smoothed.",
                  "Its uncertainty is increased and it is not used for texture."),
    "Q-SMALL": ("The face is small in this photo.",
                "Use a photo where the face is larger; fine detail is not claimed from this one."),
    "Q-WIDE": ("A wide-angle lens near the edge of the frame can stretch the face.",
               "Use a photo with the face near the centre, or a longer lens."),
}

MESSAGES = {
    # ---- generic
    "status.done": "Done",
    "status.attention": "Needs attention",
    "status.not_started": "Not started",
    "internal_error": "Something went wrong. Nothing was changed. Details are in the system console.",
    "no_project": "Create or open a project first.",
    "project_dir_missing": "Choose a folder for the project.",
    "project_created": "Project created.",
    "project_load_failed": "The project file could not be read.",
    "job_progress": "Job: {stage} {pct}%",
    "no_mesh_object": "Select the head mesh object first.",
    "no_active_photo": "Switch to a photo camera first (View next).",
    "nothing_to_do": "Nothing to do.",
    "deferred_feature": "This feature is not available yet.",
    "undo_hint": "This step can be undone with Ctrl-Z.",
    # ---- consent (default deny, eth F1-F3)
    "consent_missing": "Record consent first: Face3D needs a consent record that allows reconstruction.",
    "consent_saved": "Consent record saved.",
    "consent_denied_scope": "The consent record does not allow this step.",
    "consent_expired": "The consent record has expired.",
    "photo_not_consented": "This photo is not covered by the consent record, so it was not added.",
    "consent_photo_added": "Photo added to the consent record at your request.",
    # ---- photos
    "no_photos": "Add at least one photo first.",
    "photo_added": "Photo added.",
    "photo_exists": "This photo is already in the project.",
    "photo_failed": "This photo could not be added.",
    "convert_to_png": "Blender cannot read this file as it is. Convert it to an upright PNG or JPEG and add it again.",
    "rights_invalid": "Choose how you have the right to use this photo.",
    "review_empty": "There are no findings to review.",
    "review_card": "Reviewing: {card}",
    "view_none": "There are no photo cameras to step through.",
    # ---- landmarks and pins
    "no_landmarks": "Import landmarks first: every included photo needs a landmark file (pins refine them, they do not replace them).",
    "landmarks_incomplete": "Some included photos have no imported landmarks. Import landmarks for them or exclude them.",
    "face_unknown": "That face number does not exist in the imported landmarks.",
    "pin_next": "Next click places: {name}.",
    "pin_next_none": "Every landmark of the scheme has a pin.",
    "card.photo": "Photo {name}",
    "card.face": "Face {n} (detector score {score:.2f})",
    "btn.card_accept": "Accept",
    "btn.card_dismiss": "Dismiss",
    "panel.cards": "Findings to decide",
    "panel.cards_none": "No open findings.",
    "ledger.sigma_unknown": "{label}: range unknown (not enough information to state a +/- range)",
    "landmarks_imported": "Landmarks imported.",
    "landmarks_scheme_missing": "The landmark file does not name its scheme, so it cannot be used.",
    "landmarks_scheme_unknown": "The landmark file uses a scheme this version does not know.",
    "landmarks_read_failed": "The landmark file could not be read.",
    "pick_subject": "More than one face was found. Choose which one is the subject, then press Accept.",
    "pin_need_camera": "Pins are placed in a photo camera view. Switch to one first.",
    "pin_placed": "Pin placed.",
    "pin_deleted": "Pin deleted.",
    "pin_help": "Click to place, drag to move, arrows nudge 1 px (Shift: 0.25 px), X deletes, Esc ends.",
    "trace_help": "Click along the outline (at least 5 points), then press Enter. Esc cancels.",
    "trace_too_few": "Place at least 5 points along the outline.",
    "trace_done": "Outline snapped to the nearest image edge.",
    # ---- jobs
    "job_running": "A job is running. Wait for it to finish or cancel it first.",
    "job_started": "Job started.",
    "job_not_running": "No job is running.",
    "job_cancelling": "Cancelling; the job stops within a second.",
    "job_failed": "The job did not finish. Nothing was changed.",
    "job_reset": "The earlier job was no longer running (the file was reopened or Blender stopped). Its status was reset.",
    "project_exists": "A project already exists in that folder. Choose an empty folder; nothing was changed.",
    "head_transform": "The head object is moved, rotated or scaled. Apply its transform (Object > Apply > All Transforms) first, so the solved cameras line up.",
    "job.start": "Starting",
    "job.done": "Finished",
    "job.cancelled": "Cancelled",
    "job.selftest.tick": "Working",
    "job.error.cancelled": "The job was cancelled.",
    "job.error.consent_refused": "The consent record does not allow this step.",
    "job.error.invalid_input": "The project or photos could not be used. Check the photos and landmarks.",
    "job.error.numerical": "The solver could not find a stable answer. Add or fix pins and try again.",
    "job.error.internal": "Something went wrong inside the solver. Nothing was changed.",
    "job.error.bad_until": "The job asked for a stage that does not exist. Nothing was changed.",
    "job.error.cage_needs_quads": "The limit-fitted cage needs an all-quad template. Fit without the cage.",
    "job.error.kit_prior_mismatch": "The template and the landmark prior do not belong together.",
    "job.error.landmarks_image_mismatch": "The landmark file was made for a different image than this photo.",
    "job.error.missing_landmarks": "A photo has no imported landmarks. Import landmarks for every included photo, or exclude it.",
    "job.error.no_face": "The landmark file contains no face.",
    "job.error.no_report": "The job finished without a report. Run it again.",
    "job.error.no_usable_photos": "No photo can be used. Check the findings and the consent record.",
    "job.error.no_working_copies": "The photo working copies are missing from the project folder.",
    "job.error.photo_sha_mismatch": "A photo changed after it was added to the project.",
    "job.error.photo_size_unknown": "The size of a photo is unknown. Add the photo again.",
    "job.error.pin_unknown_landmark": "A pin names a landmark that the scheme does not have.",
    "job.error.scheme_size_mismatch": "The landmark scheme and the template disagree on the number of points.",
    "job.error.texture_blocked": "The texture step was refused (consent scope, photo rights or photo quality).",
    "job.error.unknown_template": "The template named by the project is not available.",
    "job.error.unsupported_working_copy": "A photo working copy has a format this version cannot read.",
    "job.error.working_copy_missing": "A photo working copy is missing. Add the photo again.",
    "qa.Q-SMALL.no_iris_scale": "The face is too small in this photo to measure scale from the iris.",
    "no_result": "There is no finished result to apply. Run solve or fit first.",
    "result_unreadable": "The result files could not be read.",
    "wrong_mode": "Switch the object to Object mode first; the add-on does not edit meshes in Edit or Sculpt mode.",
    "topology_mismatch": "This mesh does not have the topology the result was made for, so nothing was changed.",
    "result_applied": "Result applied.",
    "result_reverted": "Went back to solve {n}.",
    "revert_unknown": "That solve does not exist.",
    # ---- cards and decisions (D-10: never automatic)
    "mirror_suggest": "This photo may be mirrored (flipped left-right). Flip it only if you know it is.",
    "mirror_undetermined": "Cannot tell whether this photo is mirrored: the photos do not carry enough left-right "
                           "evidence to decide.",
    "mirror_gap_significant": "This photo may be mirrored, but the evidence is not conclusive. Check it if you can.",
    "mirror_unverifiable": "All photos are selfies, so a mirror flip cannot be checked.",
    "mirror_keep": "Nothing suggests this photo is mirrored.",
    "card_none": "There is no open finding to decide.",
    "card_accepted": "Decision recorded: accepted.",
    "card_dismissed": "Decision recorded: dismissed.",
    "card_flip_recorded": "Recorded: flip this photo on the next solve. You can reverse it.",
    "card_keep_recorded": "Recorded: keep this photo as it is.",
    # ---- hand-off
    "handoff_done": "Sculpt copy created with a Multires modifier. The fitted object is untouched.",
    "handoff_multires_failed": "The sculpt copy was created, but Multires could not be added. Add it by hand.",
    "no_keys": "Apply a result first; the shape keys are missing.",
    "rebase_done": "Sculpt layer carried over to the new fit.",
    "protect_done": "Measured regions are protected: sculpt brushes cannot move them.",
    "sculpt_needs_copy": "Select the sculpt copy made by Start sculpting.",
    "share_listed": "Found {n} items to review before sharing. Nothing was deleted.",
    "share_clean": "Nothing to review before sharing.",
    "purge_done": "Removed {n} items.",
    "purge_confirm": "Delete the selected data? This cannot be undone. Photo working copies are needed to solve again.",
    # ---- compare modes (DESIGN 6.5: hold-to-flip, no blinking)
    "compare_hint": "Hold F to see the photo flipped; release to restore.",
    # ---- rail: done-when lines and button labels (DESIGN 6.4)
    "rail.consent.done_when": "Done when a consent record allows reconstruction.",
    "rail.photos.done_when": "Done when every photo is added and covered by the consent record.",
    "rail.check.done_when": "Done when every photo finding has been reviewed.",
    "rail.landmarks.done_when": "Done when each included photo has imported landmarks (pins refine them, they do not replace them).",
    "rail.cameras.done_when": "Done when the solved cameras are in the scene.",
    "rail.shape.done_when": "Done when the fitted shape keys are on your head mesh.",
    "rail.confidence.done_when": "Done when you have read what is measured and what is guessed.",
    "rail.sculpt.done_when": "Done when a sculpt copy exists.",
    "rail.texture.done_when": "Done when a texture has been projected from the photos.",
    "rail.share.done_when": "Done when you have reviewed what a shared file would contain.",
    "rail.consent": "Consent",
    "rail.photos": "Photos",
    "rail.check": "Check",
    "rail.landmarks": "Landmarks",
    "rail.cameras": "Cameras",
    "rail.shape": "Shape",
    "rail.confidence": "Confidence",
    "rail.sculpt": "Sculpt",
    "rail.texture": "Texture",
    "rail.share": "Share",
    "btn.project_new": "New project",
    "btn.consent_edit": "Edit consent",
    "btn.photos_add": "Add photos",
    "btn.review_next": "Review next finding",
    "btn.landmarks_import": "Import landmarks",
    "btn.solve": "Solve cameras",
    "btn.fit": "Fit shape",
    "btn.apply_result": "Apply result",
    "btn.handoff_sculpt": "Start sculpting",
    "btn.texture_project": "Project texture",
    "btn.prepare_for_sharing": "Prepare for sharing",
    "btn.job_cancel": "Cancel job",
    "btn.view_next": "Next photo view",
    "btn.revert_solve": "Revert to solve",
    "btn.protect_measured": "Protect measured regions",
    "btn.rebase_sculpt": "Rebase sculpt on new fit",
    "panel.expert_defaults": "Defaults (read-only)",
    "panel.expert_modes": "Symmetry, expression, focal",
    "panel.expert_history": "Solve history",
    "panel.ledger": "What is measured and what is guessed",
    "ledger.banner": "Not validated against a scan.",
    "ledger.none": "No result yet.",
    "ledger.tier": "Tier {code}: {name}",
    "ledger.region.measured": "{label}: likely within +/-{sigma:.1f} mm (measured)",
    "ledger.region.constrained": "{label}: likely within +/-{sigma:.1f} mm, partly from average proportions (constrained)",
    "ledger.region.prior-driven": "{label}: guessed from average proportions (prior-driven)",
    "ledger.region.unobserved": "{label}: not seen in any photo (unobserved)",
    "ledger.defaults": "{n} defaults are expert estimates not yet calibrated.",
    "mode.symmetry": "Symmetry: the shape keeps its asymmetry; it is never symmetrised.",
    "mode.expression": "Expression: taken from each photo's tag.",
    "mode.focal": "Focal length: {summary}",
    # ---- engine ledger and contour keys (verbatim)
    "ledger.why.unobserved": "No photo sees this region.",
    "ledger.why.measured": "Enough photos constrain this region.",
    "ledger.why.not_modelled": "This region has no landmarks in the template.",
    "ledger.why.tagged": "The photos showing this region carry an expression tag.",
    "ledger.why.coverage_missing": "A needed view of this region is missing.",
    "ledger.why.prior_no_coverage": "No view covers this region well enough.",
    "ledger.why.sigma_above_target": "The uncertainty is above the target for this region.",
    "ledger.why.partial_evidence": "Only part of the evidence needed is there.",
    "ledger.why.prior_low_evidence": "The photos say little about this region.",
    "contour.focal_or_distance_wrong": "The outline and the landmarks disagree; the focal length or distance may be wrong.",
}
for _code, (_msg, _fix) in _QA.items():
    MESSAGES["qa." + _code] = _msg
    MESSAGES["qa." + _code + ".fix"] = _fix
del _code, _msg, _fix


def text(key, **fmt):
    """English text of ``key`` formatted with ``fmt``; the key itself if unknown. Never raises."""
    s = MESSAGES.get(key)
    if s is None:
        return str(key)
    try:
        return s.format(**fmt) if fmt else s
    except (KeyError, IndexError, ValueError):
        return s


def has(key):
    return key in MESSAGES
