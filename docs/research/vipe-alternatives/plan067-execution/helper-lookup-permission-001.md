# Optional helper lookup permission failure

The optional read-only command was:

```bash
rg --files /tmp -g 'plan067*py' -g '!prompts/**' -g '!node_modules/**' -g '!Experiments_4DGS*/**' -g '!pytest-of-*/**'
```

It returned exit 2 and `Permission denied (os error 13)` for system-private
directories such as `/tmp/snap-private-tmp` and
`/tmp/systemd-private-ba1b4efeee43408886df706c41cfac12-polkit.service-jNm2In`.
The one authorized exact outside-sandbox retry also returned exit 2 with the
same host directory errors. This was not an automatic approval denial; host
filesystem permissions remain the cause. The read-only retry was approved and
no missing allow rule was indicated. A duplicate Codex rule cannot fix host
directory ownership/access.

The affected scan stopped and will not be retried or worked around. The helper
path had already appeared in the permitted results. CPU validation using that
known task helper does not depend on access to the private directories. No
private file contents were read and no state was changed by either lookup.
