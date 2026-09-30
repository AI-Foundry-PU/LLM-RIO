"""Sample live GPU memory without starting models or changing the running service."""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import UTC, datetime

from llm_rio.gpu_memory import read_gpu_memory
from llm_rio.inventory import discover_inventory


def positive_int(value: str) -> int:
    result = int(value)
    if result <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return result


def positive_float(value: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise argparse.ArgumentTypeError("must be finite and positive")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gpu", action="append", default=[], help="GPU UUID; repeat to select GPUs"
    )
    parser.add_argument("--samples", type=positive_int, default=1)
    parser.add_argument(
        "--interval", type=positive_float, default=1.0, help="Seconds between samples"
    )
    args = parser.parse_args()
    try:
        inventory = discover_inventory("vram-monitor", args.gpu)
        gpu_uuids = tuple(device.uuid for device in inventory.gpus)
        peaks: dict[str, int] = {}
        for index in range(args.samples):
            if index:
                time.sleep(args.interval)
            samples = read_gpu_memory(gpu_uuids)
            records = []
            for device in inventory.gpus:
                sample = samples[device.uuid]
                used = sample.total_mib - sample.free_mib
                peaks[device.uuid] = max(peaks.get(device.uuid, 0), used)
                records.append(
                    {
                        "uuid": device.uuid,
                        "name": device.name,
                        "total_mib": sample.total_mib,
                        "used_mib": used,
                        "free_mib": sample.free_mib,
                        "peak_used_mib": peaks[device.uuid],
                        "process_group_mib": sample.process_group_mib,
                    }
                )
            print(
                json.dumps(
                    {"timestamp": datetime.now(UTC).isoformat(), "gpus": records}, sort_keys=True
                ),
                flush=True,
            )
    except KeyboardInterrupt:
        raise SystemExit(130) from None
    except Exception as exc:
        print(f"VRAM measurement failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
