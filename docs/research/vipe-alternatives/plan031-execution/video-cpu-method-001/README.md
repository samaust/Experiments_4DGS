# D9/D10 retained CPU qualification method

Preparation for issue #57. No actual video setup, model load, inference, GPU,
commercial clearance or live ledger action has been performed by this packet.

After approved setup, root runs `producer.py capture` under its independently
reviewed, metered native syscall wrapper. Arguments: `--root` canonical checkout,
`--candidate D9|D10`, immutable `--setup`, `--setup-request`, `--setup-dispatch`,
a fresh `--output`, bounded `--seconds` (at most 180) and `--artifact-bytes`.
The root wrapper must deny native networking, enforce whole-slot/global disk and
CPU bounds, meter final evidence writes and confirm descendant cleanup. Python
socket/process audit guards and the internal timer are additional controls.
They do not replace the wrapper. This method does not modify the ledger.

Capture uses the exact provisioned interpreter, verifies the accepted installed
inventory and recipe, records all installed packages and files, and performs two
strict Small architecture loads on CPU. D10 uses `metric=True`; D9 uses relative
mode. No inference or CUDA initialization is allowed. It preserves an immutable
failure capture. `complete-dependencies.json` binds the complete installed
closure; independent commercial assessment must reference that exact file.

Root subsequently runs `finalize` under another separately metered wrapper with
`--capture`, `--commercial-assessment`, `--source-review`, a fresh `--output`,
`--candidate`, and `--root`. The fresh post-setup independent source review must
bind current local source hashes and identical nonempty setup `source_files`
and `source_archive`. The resulting runtime receipt and full qualification
bundle retain those exact two native-source bindings. Neither establishes GPU
numerics, peak GPU memory, fit/check scale success, or execution admission.

Pass the **full `qualification.json` record** explicitly into admission.
The video dispatch fallback to a runtime receipt is insufficient for completed
D10 metric selection lineage. Actual dispatch also selects a fixed source-review
001 path; root must integrate a reviewed explicit immutable selector before using
a fresh post-setup review. Never overwrite previous source-review receipts.

`test_lineage.py` exercises the existing completed qualification boundary using
CPU fixtures: valid D10 lineage; runtime-only fallback rejected; missing or changed
archive/files rejected in runtime, qualification and source review. Fixture
success grants no actual runtime or commercial authority.
