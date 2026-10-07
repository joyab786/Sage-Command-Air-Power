"""
SageCommand Air Power System (Aero) — Telemetry Data Fabric Package.
Exposes normalization, quality assessment, envelope checking, buffering,
synthetic generation, and telemetry services.
"""

from app.telemetry.models import (
    QualityStatus,
    EnvelopeStatus,
    EnvelopeViolation,
    QualityAssessmentResult,
    EnvelopeAssessmentResult,
    NormalizedTelemetry,
    TelemetryInput,
    TelemetryIngestResult,
    BatchIngestRequest,
    BatchIngestResult,
    DemoGenerateRequest,
)

from app.telemetry.normalizer import (
    TelemetryNormalizer,
    convert_altitude,
    convert_airspeed,
    convert_temperature,
    convert_pressure,
    convert_vibration,
    convert_fuel_flow,
)

from app.telemetry.quality import QualityEvaluator

from app.telemetry.envelope import (
    FlightEnvelopeChecker,
    FlightEnvelopeProfile,
    ChannelBoundary,
    DEFAULT_DEMO_ENVELOPE,
)

from app.telemetry.buffer import TelemetryBuffer, default_telemetry_buffer
from app.telemetry.generator import SyntheticFlightGenerator
from app.telemetry.service import TelemetryService, default_telemetry_service

__all__ = [
    # Models
    "QualityStatus",
    "EnvelopeStatus",
    "EnvelopeViolation",
    "QualityAssessmentResult",
    "EnvelopeAssessmentResult",
    "NormalizedTelemetry",
    "TelemetryInput",
    "TelemetryIngestResult",
    "BatchIngestRequest",
    "BatchIngestResult",
    "DemoGenerateRequest",
    # Normalization
    "TelemetryNormalizer",
    "convert_altitude",
    "convert_airspeed",
    "convert_temperature",
    "convert_pressure",
    "convert_vibration",
    "convert_fuel_flow",
    # Quality & Envelope
    "QualityEvaluator",
    "FlightEnvelopeChecker",
    "FlightEnvelopeProfile",
    "ChannelBoundary",
    "DEFAULT_DEMO_ENVELOPE",
    # Buffer & Generator & Service
    "TelemetryBuffer",
    "default_telemetry_buffer",
    "SyntheticFlightGenerator",
    "TelemetryService",
    "default_telemetry_service",
]
