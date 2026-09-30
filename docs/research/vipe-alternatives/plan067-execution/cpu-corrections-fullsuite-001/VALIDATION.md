# First integrated correction full-suite outcome

Full suite exited1 without timeout after189.449 seconds under600 seconds:1123 tests,153 errors,5 skips,zero failures. Six errors were known unrelated dependency/deadline cases. The new errors came from a missing literal SUBTEST_CASES declaration for the new five-case generated-source binding test; canonical collection rejected it and dependent fixtures could not initialize.

Direct canonical collection reproduced `ValueError: missing or extraneous parameter declarations`. The relevant fix declares the five callback identities without weakening production collection. Collection then passed306 methods/1035 subtests and15 generated-source/declaration tests passed in0.376 seconds. Under the clarified AGENTS.md policy, a fresh full-suite capture follows this validated fix; the failed capture remains immutable. No GPU work or approval bypass occurred.
