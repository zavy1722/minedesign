"""``python -m face3d`` entry point (see :mod:`face3d.pipeline.cli`)."""
import os
import sys

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")          # before numpy is imported (small matrices; see tests/conftest.py)

from face3d.pipeline.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
