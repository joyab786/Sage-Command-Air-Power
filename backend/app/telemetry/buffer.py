"""
SageCommand Air Power System (Aero) — In-Memory Telemetry Buffer.
Provides thread-safe, bounded, low-latency queuing of incoming telemetry frames
prior to persistent commit or streaming dispatch.
"""

import threading
from collections import deque
from typing import List, Optional

from app.telemetry.models import NormalizedTelemetry


class TelemetryBuffer:
    """
    Thread-safe, bounded ring buffer for flight telemetry observations.
    Maintains chronological ordering while preventing memory leaks under high-rate streaming.
    """

    def __init__(self, max_size: int = 2000):
        self.max_size = max(1, max_size)
        self._buffer: deque[NormalizedTelemetry] = deque(maxlen=self.max_size)
        self._lock = threading.Lock()

    def append(self, observation: NormalizedTelemetry) -> None:
        """Appends a single normalized telemetry observation to the buffer."""
        with self._lock:
            self._buffer.append(observation)

    def append_batch(self, observations: List[NormalizedTelemetry]) -> None:
        """Atomically appends a sequence of observations."""
        with self._lock:
            for obs in observations:
                self._buffer.append(obs)

    def get_recent(
        self, limit: int = 100, aircraft_id: Optional[str] = None
    ) -> List[NormalizedTelemetry]:
        """
        Retrieves the most recent telemetry frames in descending chronological order.
        """
        with self._lock:
            items = list(self._buffer)

        if aircraft_id:
            items = [item for item in items if item.aircraft_id == aircraft_id]

        # Reverse to get newest first
        items.reverse()
        return items[:limit]

    def flush(self) -> List[NormalizedTelemetry]:
        """Drains and returns all observations currently in the buffer."""
        with self._lock:
            items = list(self._buffer)
            self._buffer.clear()
        return items

    def clear(self) -> None:
        """Discards all observations in the buffer."""
        with self._lock:
            self._buffer.clear()

    @property
    def size(self) -> int:
        """Returns the current number of items buffered."""
        with self._lock:
            return len(self._buffer)


# Default shared singleton instance
default_telemetry_buffer = TelemetryBuffer()
