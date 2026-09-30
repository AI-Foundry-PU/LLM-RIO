# Operations and recovery

## Prepare a deployment

Use a dedicated service account and explicitly assign managed GPU UUIDs on shared
hosts. The router honors `CUDA_VISIBLE_DEVICES` and refuses configured GPUs outside
that allocation. Database and GPU ownership locks coordinate instances using the
same Unix account on one host. Other accounts require disjoint GPU assignments.

Select a mode, configure engine paths, and use a new database at
`state/release/llm-rio.db`. Existing unversioned beta databases are rejected.
Register sources against the selected mode instead of copying old validation flags
or editing schema versions. Keep each engine environment and dependency lock with
its deployment configuration. Use `uv run --no-sync` after installation.

Run `./llmctl doctor --json` before startup. Start with `./llmctl serve`, or choose
**Diagnostics → Start service** in the TUI. The configuration selector and mode
override are described in [configuration](CONFIGURATION.md).

## Registration and validation

For Hugging Face models, register an immutable revision. For local artifacts, use
an absolute directory for vLLM or an absolute GGUF file for queue's optional
llama.cpp engine. Local sources are used in place. Keep them immutable while
registered; changed artifacts block serving until revalidation.

Native probes require maintenance:

```sh
./llmctl maintenance drain
./llmctl models validate MODEL_NAME
./llmctl models review MODEL_NAME
./llmctl maintenance resume
```

Wait until validation finishes before resuming. `models validate NAME --profile ID`
probes a selected edited or cloned profile. Review persisted job stages and engine
logs on failure. Launch edits invalidate evidence and drain affected workers.
Use measured context, concurrency, and placement limits for the actual installation.
Enabling a profile does not create valid measurements.

Explicit vLLM sleep memory budgets remain the initial validation budget, followed
by bounded lower-budget retries on out-of-memory failures. Unspecified sleep
budgets use conservative defaults. Queue and experimental modes keep their own
validation policy.

## Monitor GPU memory

```sh
uv run --no-sync python scripts/measure_vram.py
uv run --no-sync python scripts/measure_vram.py --gpu GPU_UUID --samples 60 --interval 1 > vram.jsonl
```

Each JSON line includes total/free/used VRAM, the maximum used VRAM observed so
far, and process-group allocations when NVML exposes them. Omit `--gpu` to honor
`CUDA_VISIBLE_DEVICES`, or repeat it for selected GPU UUIDs. Telemetry errors cause
a nonzero exit. Samples measure whole-GPU usage, including unrelated processes,
and can miss brief peaks; use registration probes for placement evidence.

Inspect `./llmctl status`, `./llmctl status --dashboard`, job logs, and runtime
events when placement is deferred. Queue releases resources after verified
teardown. Sleep budgets residual VRAM, wake peaks, host RAM, and swap. Missing
telemetry or foreign allocations can delay admission.

Before rollout, exercise your actual models and GPU placements, streaming and
cancellation, model switching, tenant quotas, maintenance, and restart recovery.
Include a representative sustained load and check resource reclamation after
drain. Optional request features require their own engine/model checks.

## Back up and restore

Drain and stop the service that owns the database and managed GPUs. Retain its
code revision, environment, configuration, database, and matching
`.<database-stem>-api-key-vault`. Protect backups as credentials.

Create an archive at a destination that does not already exist:

```sh
uv run --no-sync python -m llm_rio.operations.archive state/release/llm-rio.db \
  db_backup/before-upgrade --config config.release.toml --server-stopped
```

`--server-stopped` is your assertion that the service has stopped. The utility
checks database integrity, matching credentials, and available ownership locks
before writing `manifest.json`. A directory without that manifest is incomplete.
Verify archived hashes and retain permissions. `catalog.json` and `catalog.csv`
contain model source information without credentials.

Restore the matching database, vault, and configuration together into a fresh
location. Never pair a database with an unrelated vault. Retain the corresponding
code and engine environment for rollback.

## Maintenance and recovery

Drain before configuration changes, backups, engine upgrades, or mode changes.
Resume is rejected while validation owns GPUs. Stop the API gracefully and verify
worker termination before another service uses the same GPUs. Restart completes
persisted-job and request/worker recovery before accepting traffic.

If a worker cannot terminate, retain its PID, process group, and GPU diagnostics.
Do not clear reservations manually while its process may still own memory.
Investigate teardown before starting another service on those GPUs.

## Rollback

Stop the new service and verify that its workers and reservations are gone.
Restore the previous code and environment, configuration, and matching archived
database and vault into a separate location. Run only that installation on the
managed GPUs. Never run old code against a newer schema. Retain failed-deployment
diagnostics separately for investigation.
