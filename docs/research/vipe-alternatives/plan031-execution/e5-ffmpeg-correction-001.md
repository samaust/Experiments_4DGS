# E5 FFmpeg import correction

## Observed failure

Fresh `E5-setup-recovery-001` completed its locked dependency install and offline editable DA3 build, then failed native import qualification. The retained `commands/05-native-imports.log` ends with `RuntimeError: No ffmpeg exe could be found`.

FFmpeg was already present in the hash-locked `imageio-ffmpeg==0.6.0` wheel:

- Binary: `imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2`.
- Size: 79,826,272 bytes.
- SHA-256: `e7e7fb30477f717e6f55f9180a70386c62677ef8a4d4d1a5d948f4098aa3eb99`.

The import chain is DA3 API → export utilities → MoviePy → imageio FFmpeg discovery. Discovery probes each candidate with `subprocess.check_call([executable, '-version'])`. The standalone audit guard rejects subprocess creation. imageio catches this `PermissionError` as an `OSError` and concludes that no executable exists. The diagnostic does not indicate a missing wheel or a failed FFmpeg installation.

## Implemented correction

E5 explicitly pins the already selected ancillary wheel version, preserving the prescribed Python, torch, torchvision, NumPy and xFormers versions. Before installing import isolation, qualification verifies the bundled executable's managed-environment ownership, executable permission and SHA-256/size against the wheel RECORD. It binds `IMAGEIO_FFMPEG_EXE` to the verified absolute path and forces MoviePy's `FFMPEG_BINARY=ffmpeg-imageio` branch. This branch returns the explicit path without probing a subprocess. Arbitrary inherited values are replaced.

The import result retains the binding. D2 workers verify that receipt against the immutable setup imports and inventory, require the expected managed interpreter/prefix, recheck the executable bytes and wheel RECORD, and bind the same environment values before importing the DA3 API. Missing or substituted receipts, inventory entries, hashes or runtime roots fail before the binding changes environment values.

The subprocess prohibition remains in place; network and model forwards remain prohibited during setup qualification. No real setup, model, GPU job, consumed-environment modification, allocation or retry was performed for this correction.

## Validation

- First CPU request/result test failed on the original inherited `/untrusted/ffmpeg` binding, then passed with the correction.
- Six FFmpeg tests passed, covering qualification, seven negative receipt/inventory/root cases, managed-wheel failures, D2 propagation and a real subprocess-denying audit hook in an isolated CPU fixture.
- Thirty existing runtime tests and eight E5 recovery tests passed.
- AST parsing passed for all five changed code/test files; `git diff --check` passed.
- A separate read-only CPU check imported the actual installed imageio-ffmpeg package from the consumed environment with bytecode writes disabled. Its getter returned the hash-verified bundled binary successfully under the unchanged subprocess-denying audit guard. This check did not qualify the full native DA3 API.

The integrated correction still requires independent review and fresh source qualification. Recovery `001` remains consumed and unqualified. A further E5 attempt requires a new bounded REVIEW/DO proposal and explicit user approval; this correction grants no additional attempt.
