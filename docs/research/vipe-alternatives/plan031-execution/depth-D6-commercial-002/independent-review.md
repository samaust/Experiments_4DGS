# D6 replacement-runtime licence delta: independent review

An independent read-only reviewer recomputed the closure from METADATA: the q010 dependency manifest's 95
(name, version) pairs equal the replacement environment exactly; the 36 changed packages (18 new, 13 removed
cu12 wheels, 5 version changes) match `closure-comparison.json`. 204 licence files were hashed and 413
dist-info files grepped. All 11 cu13 CUDA wheels carry the assessed CUDA EULA byte-for-byte; cuDNN cu13 carries
the assessed SDK agreement byte-for-byte. cuda-toolkit has no payload or licence file. No new package has a
copyleft or non-commercial licence; the only GPL mentions in novel texts are LLVM-exception clauses. Two
wording errors (the nccl NVTX paragraph; the torch grep statement) were corrected before publication.

Verdict: PASS. The assessment-004 conclusions remain valid for local inference and commercial use of the
generated depth outputs, with notice preservation and NVIDIA EULA/SDK restrictions; redistribution unassessed.
