import json
from pathlib import Path

from app.schemas.entities import (
    AccessTrendPoint,
    ActivityEvent,
    CloudSource,
    Configuration,
    Finding,
    Identity,
    ModelRationale,
    PolicyRule,
    RationaleSignal,
    ReportTemplate,
    ServiceRisk,
    ServiceRiskSummary,
)

SEED_FILE = Path(__file__).resolve().parents[2] / "server" / "data" / "synthetic-data.json"


class SeedData:
    def __init__(self, raw: dict):
        self.findings: list[Finding] = [Finding(**f) for f in raw["alerts"]]

        rationale = raw["modelRationale"]
        self.model_rationale = ModelRationale(
            topFindingId=rationale["topFindingId"],
            explanation=rationale["explanation"],
            signals=[RationaleSignal(**s) for s in rationale["signals"]],
        )

        self.access_trend: list[AccessTrendPoint] = [
            AccessTrendPoint(**p) for p in raw["accessTrend"]
        ]
        self.access_trend_peak_label: str = raw["accessTrendPeakLabel"]

        self.service_risk: list[ServiceRisk] = [ServiceRisk(**s) for s in raw["serviceRisk"]]
        self.service_risk_summary = ServiceRiskSummary(**raw["serviceRiskSummary"])

        self.activity_log: list[ActivityEvent] = [ActivityEvent(**e) for e in raw["activityLog"]]

        self.identities: list[Identity] = [Identity(**i) for i in raw["identities"]]

        self.cloud_sources: list[CloudSource] = [CloudSource(**c) for c in raw["cloudSources"]]
        self.cloud_sources_online: int = raw["cloudSourcesOnline"]

        self.policies: list[PolicyRule] = [PolicyRule(**p) for p in raw["policies"]]

        self.reports: list[ReportTemplate] = [ReportTemplate(**r) for r in raw["reports"]]

        self.activities_checked_base: int = raw["summaryMetrics"]["activitiesChecked"]
        self.needs_attention_base: int = raw["summaryMetrics"]["needsAttention"]
        self.most_urgent_case_base = raw["summaryMetrics"]["mostUrgentCase"]
        self.average_review_time: str = raw["summaryMetrics"]["averageReviewTime"]
        self.signal_confidence_pct: float = raw["summaryMetrics"]["signalConfidencePct"]
        self.identity_coverage_pct: int = raw["summaryMetrics"]["identityCoveragePct"]

        self.configuration = Configuration(
            notificationsEnabled=True,
            plainLanguageExplanations=True,
        )


def load_seed_data() -> SeedData:
    raw = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    return SeedData(raw)
