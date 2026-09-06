"""Reuse the shared contender evaluator with the FreeTimeGS native renderer."""
from pathlib import Path
import runpy
import sys

if __name__ == '__main__':
    repo = Path(__file__).resolve().parents[1]
    sys.argv[1:1] = ['--model', 'freetimegs', '--checkout', str(repo / '.local/FreeTimeGsVanilla')]
    runpy.run_path(str(Path(__file__).with_name('evaluate-atgs-checkpoint.py')), run_name='__main__')
