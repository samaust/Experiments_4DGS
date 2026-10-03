#!/usr/bin/env python3
"""Owned CPU fixture launcher; no actual native dispatch authority."""
import sys
from vipe_benchmark.final_render_dispatch import run_fixture_invocation

if __name__=='__main__':
    if len(sys.argv)!=2:raise ValueError('exact fixture invocation path required')
    run_fixture_invocation(sys.argv[1])
