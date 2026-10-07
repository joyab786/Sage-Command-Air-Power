"""
Unit tests for TelemetryBuffer.
Validates bounded FIFO capacity, chronological retrieval, flush operations,
and thread safety under concurrent writes.
"""

import threading
from datetime import datetime, timezone, timedelta
from app.telemetry.buffer import TelemetryBuffer
from app.telemetry.models import NormalizedTelemetry, QualityStatus, EnvelopeStatus


def _create_mock_obs(seq: int, aircraft_id: str = "ac_buf_01") -> NormalizedTelemetry:
    t0 = datetime(2026, 10, 6, 8, 0, 0, tzinfo=timezone.utc) + timedelta(seconds=seq)
    return NormalizedTelemetry(
        observation_id=f"obs_buf_{seq:04d}",
        timestamp=t0,
        aircraft_id=aircraft_id,
        altitude_m=10000.0 + seq,
        airspeed_mps=250.0,
        mach=0.82,
        quality_status=QualityStatus.VALID,
        envelope_status=EnvelopeStatus.WITHIN_ENVELOPE,
        source="TEST",
    )


def test_buffer_append_and_recent_ordering():
    buf = TelemetryBuffer(max_size=100)
    for i in range(5):
        buf.append(_create_mock_obs(i))

    assert buf.size == 5
    recent = buf.get_recent(limit=3)
    assert len(recent) == 3
    # Newest first
    assert recent[0].observation_id == "obs_buf_0004"
    assert recent[1].observation_id == "obs_buf_0003"
    assert recent[2].observation_id == "obs_buf_0002"


def test_buffer_bounded_capacity():
    buf = TelemetryBuffer(max_size=5)
    for i in range(10):
        buf.append(_create_mock_obs(i))

    # Buffer must not exceed max_size
    assert buf.size == 5
    recent = buf.get_recent(limit=10)
    assert len(recent) == 5
    # The oldest 5 (0..4) should have rolled off; newest (5..9) should remain
    assert recent[0].observation_id == "obs_buf_0009"
    assert recent[-1].observation_id == "obs_buf_0005"


def test_buffer_flush_and_clear():
    buf = TelemetryBuffer(max_size=50)
    for i in range(4):
        buf.append(_create_mock_obs(i))

    flushed = buf.flush()
    assert len(flushed) == 4
    assert buf.size == 0

    buf.append(_create_mock_obs(10))
    assert buf.size == 1
    buf.clear()
    assert buf.size == 0


def test_buffer_concurrent_thread_safety():
    buf = TelemetryBuffer(max_size=500)
    threads = []
    items_per_thread = 50
    num_threads = 4

    def worker(thread_idx: int):
        for j in range(items_per_thread):
            buf.append(_create_mock_obs(thread_idx * 100 + j))

    for t in range(num_threads):
        th = threading.Thread(target=worker, args=(t,))
        threads.append(th)
        th.start()

    for th in threads:
        th.join()

    assert buf.size == num_threads * items_per_thread
