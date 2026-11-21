"""face3d.pipeline: project file, cached stages, job-folder protocol and CLI (DESIGN 2.4).

Public re-exports of the modules listed in DESIGN 2.3 (finalised by WP-23).  Every name is importable
from its module path as before; a name that exists in two modules is exported once.
Submodules stay importable as attributes (``from face3d.pipeline import cli``).
"""
from .cli import (main)
from .jobs import (write_job, read_job, run_job, read_progress, new_job_dir, JOB_FORMAT, JOB_VERSION, EXIT_OK,
    EXIT_ERROR, EXIT_INVALID, EXIT_CONSENT, EXIT_CANCELLED)
from .project import (Project, PhotoRecord, Pin, ProjectError, exif_summary, exif_from_summary, FORMAT,
    VERSION, DECISION_KINDS)
from .stages import (STAGES, ORDER, Stage, run_pipeline, PipelineRun, PipelineError, ConsentError, Cancelled,
    write_solve, write_result_files, result_summary, report_text, load_kit, landmark_set_to_plain,
    lm_cancel_hook, load_working_copy, ENGINE_VERSION, PIPELINE)

__all__ = [
    'Cancelled', 'ConsentError', 'DECISION_KINDS', 'ENGINE_VERSION', 'EXIT_CANCELLED', 'EXIT_CONSENT',
    'EXIT_ERROR', 'EXIT_INVALID', 'EXIT_OK', 'FORMAT', 'JOB_FORMAT', 'JOB_VERSION', 'ORDER', 'PIPELINE',
    'PhotoRecord', 'Pin', 'PipelineError', 'PipelineRun', 'Project', 'ProjectError', 'STAGES', 'Stage',
    'VERSION', 'exif_from_summary', 'exif_summary', 'landmark_set_to_plain', 'lm_cancel_hook', 'load_kit',
    'load_working_copy', 'main', 'new_job_dir', 'read_job', 'read_progress', 'report_text',
    'result_summary', 'run_job', 'run_pipeline', 'write_job', 'write_result_files', 'write_solve',
]
