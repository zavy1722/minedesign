"""Test-session setup.

Pin BLAS/OpenMP to one thread before numpy is imported: the test-suite's
matrices are small, and on a shared/loaded machine multithreaded BLAS makes
each small LAPACK call orders of magnitude slower (observed ~1 s vs 0.02 s).
"""
import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_var, "1")
