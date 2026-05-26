"""Generate simulated VoLTE RTT latency logs for the TRAI QoS demo."""

from __future__ import annotations

import csv
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

OUTPUT_PATH = Path(__file__).parent / "sample_latency_logs.csv"


def generate_latency_logs(
    num_records: int = 25000,
    start_time: Optional[datetime] = None,
    mean_rtt: float = 142.0,
    std_dev: float = 25.0,
    volte_ratio: float = 0.85,
    spike_probability: float = 0.02,
    spike_multiplier: float = 2.5,
) -> None:
    """
    Generate realistic VoLTE RTT latency data.

    The generated data is designed to:
    - Have mean RTT ~142ms (PASS for 150ms threshold)
    - Have p95 RTT ~215ms (FAIL for 200ms threshold)
    - Include a mix of VoLTE and data calls
    - Include occasional latency spikes (tail latency)
    """
    if start_time is None:
        start_time = datetime(2024, 11, 14, 0, 0, 0, tzinfo=timezone.utc)

    # Generate over 24 hours
    time_span = timedelta(hours=24)
    interval = time_span / num_records

    rows = []
    current_time = start_time

    for i in range(num_records):
        call_id = f"c-{uuid.uuid4().hex[:8]}"
        call_type = "volte" if random.random() < volte_ratio else "data"

        if call_type == "volte":
            # Base latency with normal distribution
            rtt = random.gauss(mean_rtt, std_dev)

            # Add spikes for tail latency (this creates p95 > 200ms)
            if random.random() < spike_probability:
                rtt *= spike_multiplier

            rtt = max(20.0, rtt)  # Floor at 20ms
        else:
            # Data traffic has lower latency
            rtt = random.gauss(80.0, 15.0)
            rtt = max(10.0, rtt)

        rows.append({
            "timestamp": current_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "call_id": call_id,
            "call_type": call_type,
            "rtt_ms": round(rtt, 1),
        })

        current_time += interval

    # Write CSV
    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "call_id", "call_type", "rtt_ms"])
        writer.writeheader()
        writer.writerows(rows)

    # Calculate stats for verification
    volte_rows = [r for r in rows if r["call_type"] == "volte"]
    volte_rtts = [r["rtt_ms"] for r in volte_rows]
    volte_rtts.sort()

    mean = sum(volte_rtts) / len(volte_rtts)
    p95_idx = int(len(volte_rtts) * 0.95)
    p95 = volte_rtts[p95_idx]

    print(f"Generated {len(rows)} records ({len(volte_rows)} VoLTE)")
    print(f"VoLTE Mean RTT: {mean:.1f}ms (threshold: 150ms)")
    print(f"VoLTE P95 RTT:  {p95:.1f}ms (threshold: 200ms)")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    random.seed(42)  # Reproducible
    generate_latency_logs(
        mean_rtt=135.0,
        std_dev=28.0,
        spike_probability=0.05,
        spike_multiplier=2.5,
    )
