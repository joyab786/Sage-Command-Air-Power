"""
SageCommand Air Power System (Aero) — Prognostics Service.
Orchestrates health history aggregation, degradation trend estimation,
Remaining Useful Life (RUL) prediction, maintenance forecasting, and readiness impact integration.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.db.models import (
    AircraftModel,
    AircraftTwinStateModel,
    AnomalyModel,
    PrognosticRecordModel,
    utc_now,
)
from app.digital_twin.models import AircraftTwinState, TwinSubsystemType
from app.digital_twin.service import default_digital_twin_service
from app.intelligence.models import Anomaly, MaintenanceRecommendation
from app.intelligence.service import default_intelligence_service
from app.prognostics.models import (
    DegradationTrend,
    MaintenanceForecast,
    MaintenanceForecastPriority,
    PredictionMethod,
    PrognosticAssessment,
    RULPrediction,
    TrendDirection,
)
from app.prognostics.health_history import HealthHistoryAggregator
from app.prognostics.trend import DegradationTrendEstimator
from app.prognostics.rul import BaseRULPredictor, default_rul_predictor
from app.prognostics.forecast import MaintenanceForecaster, default_maintenance_forecaster

logger = get_logger(__name__)


class PrognosticsService:
    """
    Prognostics & Remaining Useful Life (RUL) Service (SIH MVP).
    Provides transparent, deterministic degradation estimation and maintenance forecasting.
    """

    def __init__(
        self,
        trend_estimator: Optional[DegradationTrendEstimator] = None,
        rul_predictor: Optional[BaseRULPredictor] = None,
        forecaster: Optional[MaintenanceForecaster] = None,
    ) -> None:
        self.trend_estimator = trend_estimator or DegradationTrendEstimator()
        self.rul_predictor = rul_predictor or default_rul_predictor
        self.forecaster = forecaster or default_maintenance_forecaster
        self._latest_assessments: Dict[str, PrognosticAssessment] = {}

    def assess_aircraft_prognostics(
        self,
        db: Session,
        aircraft_id: str,
        subsystem: Optional[TwinSubsystemType] = None,
        persist: bool = True,
    ) -> PrognosticAssessment:
        """
        Executes a complete prognostic assessment for an aircraft.
        Synthesizes degradation trends, RUL bounds, maintenance forecast, and readiness impact.
        """
        # 1. Authoritative aircraft existence verification
        aircraft = db.execute(
            select(AircraftModel).where(AircraftModel.aircraft_id == aircraft_id)
        ).scalar_one_or_none()
        if not aircraft:
            raise NotFoundError(
                f"Aircraft '{aircraft_id}' not found for prognostics assessment",
                details={"aircraft_id": aircraft_id},
            )

        # 2. Retrieve current digital twin state
        current_twin: Optional[AircraftTwinState] = None
        try:
            current_twin = default_digital_twin_service.get_current_state(db, aircraft_id)
        except NotFoundError:
            pass

        # 3. Retrieve active anomalies and maintenance recommendations
        active_anomalies: List[Anomaly] = []
        try:
            anoms_new, _ = default_intelligence_service.get_anomalies(
                db, aircraft_id, status="NEW"
            )
            anoms_ack, _ = default_intelligence_service.get_anomalies(
                db, aircraft_id, status="ACKNOWLEDGED"
            )
            active_anomalies = anoms_new + anoms_ack
        except Exception as exc:
            logger.debug(f"Could not load active anomalies for {aircraft_id}: {exc}")

        recommendations: List[MaintenanceRecommendation] = []
        try:
            recommendations = default_intelligence_service.get_maintenance_recommendations(
                db, aircraft_id
            )
        except Exception as exc:
            logger.debug(f"Could not load maintenance recommendations for {aircraft_id}: {exc}")

        # 4. Evaluate primary subsystem (default to PROPULSION or user-selected)
        target_subsystem = subsystem or TwinSubsystemType.PROPULSION

        # Retrieve chronological health history
        snapshots = HealthHistoryAggregator.get_subsystem_history(
            db, aircraft_id, subsystem=target_subsystem, limit=100
        )

        # Compute degradation trend
        trend = self.trend_estimator.estimate_trend(snapshots, subsystem=target_subsystem)

        # Filter anomalies relevant to this subsystem or multi-signal
        subsystem_anoms = [
            a for a in active_anomalies
            if a.subsystem == target_subsystem or a.anomaly_type.value == "MULTI_SIGNAL_ANOMALY"
        ]

        # Compute RUL prediction
        rul = self.rul_predictor.predict(
            trend=trend,
            current_state=current_twin,
            active_anomalies=subsystem_anoms,
        )

        # Compute maintenance forecast
        forecast = self.forecaster.generate_forecast(
            rul=rul,
            active_anomalies=subsystem_anoms,
            recommendations=recommendations,
        )

        # 5. Readiness impact estimation
        if forecast.priority == MaintenanceForecastPriority.GROUND_FOR_REVIEW:
            readiness_impact = "NMC_GROUNDED"
        elif forecast.priority in (
            MaintenanceForecastPriority.PRIORITY_INSPECTION,
            MaintenanceForecastPriority.INSPECT_SOON,
        ):
            readiness_impact = "PMC_RESTRICTED"
        else:
            readiness_impact = "FMC_SUPPORTED"

        cur_health = current_twin.health_score if current_twin else trend.current_health
        cur_wear = current_twin.wear_index if current_twin else 0.0

        explanation = (
            f"Prognostic assessment for {aircraft_id} on subsystem {target_subsystem.value}: "
            f"Health trend is {trend.trend_direction.value} with slope {trend.slope:.3f} pts/hr. "
            f"Projected remaining useful life is {rul.estimated_rul_hours:.1f} flight hours "
            f"[{rul.lower_bound_hours:.1f} - {rul.upper_bound_hours:.1f} h]. "
            f"Consolidated forecast priority: {forecast.priority.value}. Readiness impact: {readiness_impact}."
        )

        composite_confidence = round(min(trend.confidence, rul.confidence, forecast.confidence), 4)

        assessment = PrognosticAssessment(
            aircraft_id=aircraft_id,
            timestamp=datetime.now(timezone.utc),
            primary_subsystem=target_subsystem,
            current_health_score=cur_health,
            current_wear_index=cur_wear,
            trend=trend,
            rul=rul,
            forecast=forecast,
            subsystem_predictions={target_subsystem.value: rul},
            readiness_impact=readiness_impact,
            confidence=composite_confidence,
            explanation=explanation,
        )

        # 6. Relational persistence
        if persist:
            record = PrognosticRecordModel(
                record_id=assessment.assessment_id,
                aircraft_id=aircraft_id,
                timestamp=assessment.timestamp,
                subsystem=target_subsystem.value,
                health_score=cur_health,
                wear_index=cur_wear,
                trend_direction=trend.trend_direction.value,
                degradation_rate=trend.degradation_rate,
                slope=trend.slope,
                estimated_rul_hours=rul.estimated_rul_hours,
                estimated_rul_cycles=rul.estimated_rul_cycles,
                lower_bound_hours=rul.lower_bound_hours,
                upper_bound_hours=rul.upper_bound_hours,
                confidence=composite_confidence,
                forecast_priority=forecast.priority.value,
                prediction_method=rul.prediction_method.value,
                limiting_factors=rul.limiting_factors,
                explanation=explanation,
                recommended_action=rul.recommended_action,
                created_at=utc_now(),
            )
            db.add(record)
            db.commit()

        self._latest_assessments[aircraft_id] = assessment
        return assessment

    def get_health_trend(
        self,
        db: Session,
        aircraft_id: str,
        subsystem: Optional[TwinSubsystemType] = None,
    ) -> DegradationTrend:
        """Computes and returns the current degradation trend for an aircraft subsystem."""
        # Authoritative aircraft verification
        aircraft = db.execute(
            select(AircraftModel).where(AircraftModel.aircraft_id == aircraft_id)
        ).scalar_one_or_none()
        if not aircraft:
            raise NotFoundError(
                f"Aircraft '{aircraft_id}' not found for health trend query",
                details={"aircraft_id": aircraft_id},
            )

        target_subsystem = subsystem or TwinSubsystemType.PROPULSION
        snapshots = HealthHistoryAggregator.get_subsystem_history(
            db, aircraft_id, subsystem=target_subsystem, limit=100
        )
        return self.trend_estimator.estimate_trend(snapshots, subsystem=target_subsystem)

    def get_maintenance_forecast(
        self,
        db: Session,
        aircraft_id: str,
    ) -> MaintenanceForecast:
        """Retrieves or derives the latest maintenance forecast for an aircraft."""
        assessment = self.assess_aircraft_prognostics(db, aircraft_id, persist=False)
        return assessment.forecast

    def get_historical_predictions(
        self,
        db: Session,
        aircraft_id: str,
        limit: int = 50,
    ) -> List[PrognosticRecordModel]:
        """Queries historical persisted prognostic records for an aircraft."""
        aircraft = db.execute(
            select(AircraftModel).where(AircraftModel.aircraft_id == aircraft_id)
        ).scalar_one_or_none()
        if not aircraft:
            raise NotFoundError(
                f"Aircraft '{aircraft_id}' not found for historical prognostics query",
                details={"aircraft_id": aircraft_id},
            )

        records = db.execute(
            select(PrognosticRecordModel)
            .where(PrognosticRecordModel.aircraft_id == aircraft_id)
            .order_by(desc(PrognosticRecordModel.timestamp))
            .limit(limit)
        ).scalars().all()
        return list(records)


default_prognostics_service = PrognosticsService()
