#!/usr/bin/env python3
"""Pinned CPU-only entry for fixed actual monitoring and acceptance operations."""
import os
for variable in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS',
                 'NUMEXPR_NUM_THREADS','OPENCV_FOR_THREADS_NUM'):
    os.environ[variable] = '1'
os.environ['CUDA_VISIBLE_DEVICES'] = ''
from vipe_benchmark.final_render_actual_control import main
if __name__ == '__main__':
    main()
