"""Command line: ``python -m face3d {triage,solve,fit,report,testbed,job} ...`` (WBS WP-20, DESIGN 2.4, D-10).

Commands
--------
``triage|solve|fit|report --project PATH``
    Run the pipeline up to that stage (``--until`` overrides).  ``--seed`` overrides the project seed,
    ``--apply-mirror ID`` (repeatable) records a ``mirror_flip`` decision (``by='cli'``, with an audit
    entry) for that photo before the landmarks stage: a suggested flip is otherwise only a card
    (D-10).  ``--landmarks DIR`` holds ``<photo id>.json`` LandmarkSets (default
    ``<project>/landmarks`` when ``landmark_cache.keep``); ``--consent FILE`` the ConsentRecord JSON
    (default ``<project>/consent/<consent_id>.json``); ``--texture`` requests the texture stage;
    ``--out DIR`` the solve folder (default ``<project>/solves/NNNN``; ``report`` only).
``job run JOB_DIR``
    Run a job folder (:mod:`face3d.pipeline.jobs`).
``testbed scorecard ...``
    Delegates to :func:`face3d.testbed.scorecard.main`.

:func:`main` returns the exit code: 0 ok, 1 internal error, 2 usage or invalid input, 3 consent refused,
4 cancelled (every failure is caught at the boundary: no traceback, so no path, ever escapes).  Error output
is a code and an exception type only (no paths or coordinates).  ``--seed`` governs the run
(``result.run.seed``) and is never written to the project file; ``--revert-mirror ID`` records a
``mirror_keep`` decision (a flip is reversible, D-10).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

import numpy as np

EXIT_OK, EXIT_ERROR, EXIT_INVALID, EXIT_CONSENT, EXIT_CANCELLED = 0, 1, 2, 3, 4


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="python -m face3d", description="Photo-to-3D face engine pipeline.")
    sub = ap.add_subparsers(dest="command", required=True)
    for name, helptext in (("triage", "ingest and photo QA"), ("solve", "up to the bundle solve"),
                           ("fit", "up to the template fit"), ("report", "full pipeline and result files")):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("--project", required=True, help="project.json (or its folder)")
        p.add_argument("--seed", type=int, default=None, help="override the project seed")
        p.add_argument("--until", default=None, help="last stage to run (default: the command)")
        p.add_argument("--apply-mirror", action="append", default=[], metavar="ID",
                       help="record a mirror_flip decision for photo ID (repeatable)")
        p.add_argument("--revert-mirror", action="append", default=[], metavar="ID",
                       help="record a mirror_keep decision for photo ID, undoing a flip (repeatable)")
        p.add_argument("--landmarks", default=None, help="folder with <photo id>.json LandmarkSets")
        p.add_argument("--consent", default=None, help="ConsentRecord JSON")
        p.add_argument("--texture", action="store_true", help="also run the texture stage")
        p.add_argument("--out", default=None, help="solve output folder (report)")
        p.add_argument("--quiet", action="store_true", help="no report text on stdout")
    pj = sub.add_parser("job", help="job folders")
    pj.add_argument("action", choices=["run"])
    pj.add_argument("job_dir")
    pt = sub.add_parser("testbed", help="test bed tools", add_help=False)
    pt.add_argument("tool", choices=["scorecard"])
    pt.add_argument("rest", nargs=argparse.REMAINDER)
    return ap


def _load_landmarks(dir_: Path, project) -> dict:
    from face3d.io.landmarks import load_landmarks
    out = {}
    for p in project.photos:
        f = dir_ / f"{p.id}.json"
        if f.is_file():
            out[p.id] = load_landmarks(f)
    return out


def _run_pipeline_command(args) -> int:
    from face3d.core.cache import StageCache
    from face3d.core.policy import ConsentRecord
    from face3d.core.schema import FormatError
    from face3d.pipeline import stages as S
    from face3d.pipeline.project import Project, ProjectError

    until = args.until or args.command
    try:
        project = Project.load(args.project)
        consent = None
        cpath = Path(args.consent) if args.consent else project.root / "consent" / f"{project.consent_id}.json"
        if cpath.is_file():
            consent = ConsentRecord.from_json(cpath.read_text(encoding="utf-8"))
        sets = None
        if args.landmarks:
            sets = _load_landmarks(Path(args.landmarks), project)
        for pid in args.revert_mirror:
            project.photo(pid)                                    # KeyError for unknown ids
            if project.mirror_state(pid) == "flip":
                project.record_decision("mirror_keep", pid, "cli")
                if project.path is not None:
                    project.save()
        cache = StageCache(root=project.root / "cache")
        try:
            run = S.run_pipeline(project, until=until, cache=cache, apply_mirror=list(args.apply_mirror),
                                 landmark_sets=sets, consent=consent, texture=bool(args.texture),
                                 seed=args.seed)
        finally:
            cache.close()
        out_dir = None
        if run.outputs.get("report") is not None:
            out_dir = S.write_solve(project, run, Path(args.out) if args.out else None)
    except S.ConsentError as e:
        print(f"error: consent_refused ({e.operation}): missing={','.join(e.result.missing) or '-'}",
              file=sys.stderr)
        return EXIT_CONSENT
    except S.Cancelled:
        print("error: cancelled", file=sys.stderr)
        return EXIT_CANCELLED
    except S.PipelineError as e:
        print(f"error: {e.code}", file=sys.stderr)
        return EXIT_INVALID
    except (FormatError, ProjectError, KeyError, ValueError, TypeError, OSError) as e:
        # json.JSONDecodeError is a ValueError; messages (which may carry paths) are never printed
        print(f"error: invalid_input ({type(e).__name__})", file=sys.stderr)
        return EXIT_INVALID
    except np.linalg.LinAlgError:
        print("error: numerical", file=sys.stderr)
        return EXIT_ERROR
    except Exception as e:                                        # noqa: BLE001 - CLI boundary: code only
        print(f"error: internal ({type(e).__name__})", file=sys.stderr)
        return EXIT_ERROR
    if not args.quiet:
        if run.report_text:
            sys.stdout.write(run.report_text)
        else:
            sys.stdout.write("stages run: " + ", ".join(run.executed or run.cache_hits) + "\n")
        for c in run.outputs.get("solve", {}).get("mirror_cards", []) if "solve" in run.outputs else []:
            if c["decision"] == "suggest_flip" and not c["applied"]:
                sys.stdout.write(f"card: photo {c['photo']} may be mirrored; --apply-mirror {c['photo']} to flip\n")
    if out_dir is not None:
        sys.stdout.write(f"result: {out_dir / 'result.json'}\n")
    return EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    ap = _parser()
    try:
        args = ap.parse_args(list(argv) if argv is not None else None)
    except SystemExit as e:                      # argparse usage errors
        return int(e.code) if isinstance(e.code, int) else EXIT_INVALID
    if args.command == "job":
        from face3d.pipeline.jobs import run_job
        return run_job(args.job_dir)
    if args.command == "testbed":
        from face3d.testbed import scorecard
        return int(scorecard.main(list(args.rest)))
    return _run_pipeline_command(args)


__all__ = ["main"]
