# LLM-RIO

LLM-RIO is a machine-local, multi-tenant LLM inference router for GPU research
hosts. It schedules measured GPU placements, manages model workers and API keys,
and serves OpenAI-compatible chat completions and model-list endpoints.
Administration is available through a terminal UI, CLI, and HTTP API.

| Mode | Behavior | Engines |
| --- | --- | --- |
| `queue` | Launch workers on demand and release them after draining | vLLM; optional llama.cpp |
| `vllm-sleep` | Cache workers with native level-1 sleep and wake from host RAM | vLLM |
| `kv-cached` | Experimental elastic KV placement | vLLM with the optional pinned compatibility layer |

Select one mode per service. Model and hardware compatibility is determined by
the selected engine and validation on your actual deployment. There is no
automatic engine fallback. Local model directories and GGUF files are reused
in place.

## Install

The router supports Python 3.11–3.13. Native GPU setup requires Linux and a working
NVIDIA driver; the engine has its own platform requirements. Install
[uv](https://docs.astral.sh/uv/getting-started/installation/), then:

```sh
git clone https://github.com/AI-Foundry-PU/LLM-RIO.git
cd LLM-RIO
uv sync --locked --extra engine
cp examples/config/queue.toml config.release.toml
export LLMRIO_CONFIG_FILE="$PWD/config.release.toml"
```

Edit the configuration for your host, especially the managed GPU UUIDs, paths,
and API binding. Use a new database, normally `state/release/llm-rio.db`.
Preserve existing installations with the [backup procedure](docs/OPERATIONS.md).

For an externally managed engine, install with `uv sync --locked` and configure
its executable path under `[engines]`. Keep that engine environment reproducible.
The optional [setup helper](setup.sh) installs the native engine and checks host
diagnostics. See [configuration](docs/CONFIGURATION.md) for all settings and
[experimental installation](docs/EXPERIMENTAL.md) for kv-cached.

## Start and register a model

```sh
uv run --no-sync llm-rio doctor
uv run --no-sync llm-rio serve
```

First startup creates the `admin` credential and logs its value. It is also
stored in the protected local credential vault. Local administration can recover
it; remote administration uses `LLMRIO_API_URL` and `LLMRIO_API_KEY`.

In another terminal, select the same configuration and register a model:

```sh
export LLMRIO_CONFIG_FILE="$PWD/config.release.toml"
./llmctl maintenance drain
./llmctl models add example organization/model --revision COMMIT_SHA
# Alternatively, reuse a local model directory:
# ./llmctl models add example --local-path /absolute/model/directory
./llmctl models review example
./llmctl maintenance resume
```

Replace the example repository and revision with your own. Wait for validation
to complete before resuming. `models validate NAME` runs probes again and retries
failed registration jobs. Run `./llmctl` for the TUI or `./llmctl --help` for CLI help.

## Operations and helpers

- [Configuration and installation](docs/CONFIGURATION.md)
- [Mode selection](docs/MODES.md)
- [Administration actions](docs/ACTIONS.md)
- [Inference API examples](docs/INFERENCE.md)
- [Operations, backup, recovery, and rollback](docs/OPERATIONS.md)
- [Experimental kv-cached](docs/EXPERIMENTAL.md)

Take a live VRAM snapshot or record a time series without loading models:

```sh
uv run --no-sync python scripts/measure_vram.py
uv run --no-sync python scripts/measure_vram.py --samples 60 --interval 1 > vram.jsonl
```

The helper honors `CUDA_VISIBLE_DEVICES`; use repeatable `--gpu GPU_UUID` arguments
to select particular GPUs. Its samples include other GPU processes and can miss
brief peaks. Model registration measures placements for serving.

LLM-RIO is distributed under the [MIT license](LICENSE).
