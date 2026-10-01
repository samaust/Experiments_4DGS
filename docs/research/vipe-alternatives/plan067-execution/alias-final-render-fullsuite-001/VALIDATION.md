# Combined alias and final-render CPU integration capture

The full suite ran once after the reviewed S1 alias corrections and final-render
CPU contract/initializer corrections were integrated. `receipt.json` and
`unittest.log` preserve the exact fresh capture.

1171 tests ran in535.669 seconds; outer elapsed537.5119380459655 seconds under
the600-second cap. There were zero failures, six errors and five skips; exit1,
no timeout. This is not a passing full-suite claim.

The six errors match the preceding capture: missing matplotlib (dense report),
plyfile (temporal initialization), pytest (scene and both timing modules), and
the inherited Basketballv6 preparation deadline. No unrelated dependency/runtime
correction is included in this milestone. The new alias and final-render CPU
tests produced no errors or failures.

Current-source S1 qualification is separately captured in qualification014.
Native generation and GPU retry authority are not established by this capture.
