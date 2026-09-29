# Plan049 correction005 — post-C process working-directory restoration

Append-only clarification of Plan049 corrections003/004, issued by Main under the user's CPU-only completion authorization.

The S1 tracker handoff temporarily changes the process working directory before entering an opaque constructor. If that constructor returns only after C, restoration to the original directory is required to avoid contaminating the shared supervisor process and later owned work. A fresh pathname lookup after C is forbidden and cannot safely substitute for the retained directory identity.

Permit after C only `os.fchdir()` using the already-retained descriptor for the exact original working directory, followed by closing that retained descriptor. This is process-state safety restoration, not another S1 production operation. Do not resolve or read a path, inspect directory contents, change to any other directory, or perform any unrelated cleanup. Record restoration/close outcome in the existing in-memory ordered secondary record; preserve the original primary. If restoration or descriptor close fails, retain the identity/ownership uncertainty and fail B4. Do not blindly retry a potentially reused descriptor. Normal in-window restoration remains W/C-gated.

Add collected before/after-C controls for restoration success/failure, prove no path lookup/content I/O and no constructor successor after C, and verify primary preservation plus exact descriptor retirement. Independent validation must inspect this exception alongside corrections003/004. This is the only post-C process-state operation allowed beyond the exact-root safety-retirement operations already listed.
