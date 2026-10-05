# D6 driver method 012 (qualification009)

Method 011 on the approved replacement runtime (torch 2.14.1+cu130 / Triton 3.8.0). It accepts only the
accepted runtime-replacement setup (`plan069-D6-setup-recovery-002`), whose lineage replaces the original
setup dispatch record, and binds the Triton 3.8 helper cache (v2), setting the bound `TRITON_LIBCUDA_PATH` so
Triton never runs ldconfig. `network_guard.py` is byte-identical to methods 007-011; every worker limit is
unchanged (no child processes, inference, forward, benchmark or kernel launch; two strict CPU loads).
