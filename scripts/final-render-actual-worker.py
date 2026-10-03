"""Pinned registered-child entry for guarded actual final-render workers."""
import os

# Bound CPU defaults precede NumPy/native imports; actual Torch limit is checked
# separately against the admitted request and observed by the parent monitor.
for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS',
        'NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[name] = '1'

from vipe_benchmark.final_render_actual_worker import main

if __name__ == '__main__':
    main()
