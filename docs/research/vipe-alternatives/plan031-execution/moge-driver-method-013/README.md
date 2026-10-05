# D6 driver method 013 (qualification010)

Method 012 for qualification010 after qualification009 failed cleanly before CUDA: the replacement runtime
installed FlexGEMM from a cached wheel, so the owned `runtime/flex-cache` directory a source build had
created as a side effect was absent and `moge_native.load_adapter` rejected the binding. `load_adapter` now
creates that link-checked owned directory itself. Method 013 differs from method 012 only in its job and
labels; `network_guard.py` is byte-identical to methods 007-012 and every worker limit is unchanged.
