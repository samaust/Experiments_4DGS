"""Write validation.json for a finished S1 CPU capture, carrying qualification-018's bindings.

Usage: wrap_qualification.py CAPTURE_DIR NOTE
Validates the result with s1_validation_contract.validate_wrapper before returning.
"""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT/'scripts'))

from vipe_benchmark.files import file_record, read_json, write_json  # noqa: E402
from vipe_benchmark.s1_validation_contract import validate_wrapper  # noqa: E402

PREVIOUS = ROOT/'docs/research/vipe-alternatives/plan031-execution/qualification-018/validation.json'


def main(directory, note):
    directory = Path(directory).resolve()
    previous = read_json(PREVIOUS)
    receipt = read_json(directory/'receipt.json')
    diff = subprocess.run(['git', 'diff', '--check'], cwd=ROOT, capture_output=True, text=True)
    value = {key: previous[key] for key in ('schema', 'status', 'semantic_amendment', 'configuration', 'plan', 'baseline',
        'baseline_correction', 'receipt_milestone_complete', 'implementation_acceptance_complete',
        'ready_for_live_admission', 'objective_complete')}
    value.update(aggregate_passed=receipt['passed'] is True, sources=receipt['sources_before'],
        diff_check=dict(command='git diff --check', exit_code=diff.returncode, stdout=diff.stdout, stderr=diff.stderr),
        tests=[dict(receipt=file_record(directory/'receipt.json'), execution=file_record(directory/'execution.json'))],
        carried_flags_note=note)
    validate_wrapper(value, value['semantic_amendment'], value['configuration'])
    write_json(directory/'validation.json', value)
    print(directory/'validation.json')


if __name__ == '__main__':
    main(*sys.argv[1:])
