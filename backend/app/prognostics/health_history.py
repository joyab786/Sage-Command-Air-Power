"""
SageCommand Air Power System (Aero) — Health History Aggregator.
Extracts chronological health, wear, and operational observations from
persistent digital twin states and telemetry records for trend estimation.
"""

from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.db.models import AircraftTwinStateModel, AnomalyModel
from app.digital_twin.models import TwinSubsystemType
from app.prognostics.models import ComponentHealthSnapshot


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensures datetime instance is timezone-aware UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class HealthHistoryAggregator:
    """
    Retrieves and cleanses chronological health observations from digital twin state snapshots.
    Provides data to degradation trend estimators.
    """

    @staticmethod
    def get_subsystem_history(
        db: Session,
        aircraft_id: str,
        subsystem: TwinSubsystemType = TwinSubsystemType.PROPULSION,
        limit: int = 100,
    ) -> List[ComponentHealthSnapshot]:
        """
        Retrieves historical component/subsystem health observations for an aircraft,
        sorted chronologically from earliest to latest.
        """
        # 1. Fetch digital twin state records ordered chronologically
        twin_records = db.execute(
            select(AircraftTwinStateModel)
            .where(AircraftTwinStateModel.aircraft_id == aircraft_id)
            .order_by(AircraftTwinStateModel.timestamp.asc())
            .limit(limit)
        ).scalars().all()

        if not twin_records:
            return []

        # 2. Count active anomalies for the aircraft
        active_anomalies = db.execute(
            select(AnomalyModel).where(
                and_(
                    AnomalyModel.aircraft_id == aircraft_id,
                    AnomalyModel.status.in_(["NEW", "ACKNOWLEDGED"]),
                )
            )
        ).scalars().all()

        total_anomalies = len(active_anomalies)
        critical_anomalies = sum(1 for a in active_anomalies if a.severity == "CRITICAL")
        max_severity = None
        if active_anomalies:
            severity_order = {"CRITICAL": 5, "HIGH": 4, "MEDIUM": 3, "LOW": 2, "INFO": 1}
            max_severity = max(active_anomalies, key=lambda a: severity_order.get(a.severity, 0)).severity

        # 3. Build chronological snapshots
        snapshots: List[ComponentHealthSnapshot] = []
        subsystem_key = subsystem.value if hasattr(subsystem, "value") else str(subsystem)

        for record in twin_records:
            # Extract subsystem specific health and wear if available in JSON
            sub_health = record.health_score
            sub_wear = record.wear_index
            if record.subsystem_states and isinstance(record.subsystem_states, dict):
                sub_state = record.subsystem_states.get(subsystem_key)
                if isinstance(sub_state, dict):
                    if "health_score" in sub_state and sub_state["health_score"] is not None:
                        sub_health = float(sub_state["health_score"])
                    if "wear_index" in sub_state and sub_state["wear_index"] is not None:
                        sub_wear = float(sub_state["wear_index"])

            # Determine confidence based on data quality
            dq = record.data_quality or "VALID"
            conf = 0.95 if dq == "VALID" else 0.70

            snapshot = ComponentHealthSnapshot(
                snapshot_id=f"snap-{record.state_id[:12]}" if record.state_id else f"snap-{len(snapshots)}",
                aircraft_id=aircraft_id,
                subsystem=subsystem,
                timestamp=ensure_utc(record.timestamp) or datetime.now(timezone.utc),
                health_score=round(max(0.0, min(100.0, sub_health)), 2),
                wear_index=round(max(0.0, min(1.0, sub_wear)), 4),
                anomaly_count=total_anomalies,
                critical_anomaly_count=critical_anomalies,
                active_anomaly_severity=max_severity,
                data_quality=dq,
                flight_hours=record.flight_hours or 0.0,
                flight_cycles=record.flight_cycles or 0,
                source="DIGITAL_TWIN",
                confidence=conf,
            )
            snapshots.append(snapshot)

        return snapshots
