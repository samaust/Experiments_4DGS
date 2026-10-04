# Future reconciliation CPU admission

The private producer is in the `depth-setup-recovery` worktree:
`.local/D9-recovery-reconciliation-admission-001/prepare.py`.
It has passed syntax validation and independent read-only Standards review.
Do not run it now: D9 setup failed and no accepted recovery exists.
The reviewed file is 9,354 bytes with SHA-256
`9d6ac0328f6888444893a73a4ec21b2fc34a338f487769ba775f417462732a36`.

It requires an actual clean recovery finish and exact current D9 source review.
It preserves the original approved CPU allowance within the narrower 1,800-second
accounting envelope, includes D9-owned charges, and reserves 120 seconds for
reconciliation, 180 for qualification, 160 for maps and 10 for preparation.
It publishes a fresh private `plan069-root-cpu-fixture-admission/v1` document and
effective configuration without changing the ledger.

Before use, bind the producer bytes and current public helper closure in the
combined `plan069-delta-cpu-test-capture/v1` receipt 012. Receipt 011 is stale.
Use the explicit root virtual environment interpreter. Arguments are:

```text
prepare.py --checkout <clean canonical depth-extension checkout>
           --run <owned benchmark run>
           --output <fresh private admission directory>
           --source-review <current passing D9 recovery source review>
```

After accepted recovery and admission, the qualified canonical producer command is:

```text
<root virtual environment python> -B -m vipe_benchmark.depth_budget_reconciliation
  --candidate D9 --ledger <owned run>/ledger.jsonl
  --admission <fresh admission directory>/admission.json
  --output <owned run>/prepare/plan069-D9-setup-byte-reconciliation-001
  --seconds-limit 120
```

Run with the canonical `scripts` directory on `PYTHONPATH` and GPUs hidden.
The producer preserves its receipt, confirms no children, and charges actual
elapsed CPU time. The admission generator's outer CPU capture must also be
preserved and charged once; output metadata alone is not a full timing receipt.
No actual recovery, native maps or byte attribution is authorized by this note.
