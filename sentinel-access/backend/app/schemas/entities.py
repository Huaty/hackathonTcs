from typing import Literal, Optional

from pydantic import BaseModel

FindingStatus = Literal["open", "in_progress", "escalated"]


class Finding(BaseModel):
    id: str
    severity: Literal["Critical", "High", "Medium", "Low"]
    title: str
    entity: str
    role: str
    source: str
    region: str
    service: str
    score: int
    time: str
    description: str
    signals: list[str]
    baseline: str
    recommended: str
    status: Optional[FindingStatus] = None


class MostUrgentCase(BaseModel):
    rank: str
    label: str


class SummaryMetrics(BaseModel):
    activitiesChecked: int
    needsAttention: int
    mostUrgentCase: MostUrgentCase
    averageReviewTime: str
    signalConfidencePct: float
    identityCoveragePct: int


class RationaleSignal(BaseModel):
    label: str
    score: int
    tone: str


class ModelRationale(BaseModel):
    topFindingId: str
    explanation: str
    signals: list[RationaleSignal]


class AccessTrendPoint(BaseModel):
    label: str
    events: int
    anomalies: int


class ServiceRisk(BaseModel):
    name: str
    risk: int
    events: int


class ServiceRiskSummary(BaseModel):
    highestRiskService: str
    sensitiveAssets: int
    coverage: str


class ActivityEvent(BaseModel):
    time: str
    actor: str
    action: str
    source: str
    system: str
    status: Literal["Needs attention", "Review later", "Normal"] = "Normal"
    tone: Literal["critical", "high", "medium", "normal"] = "normal"


class Identity(BaseModel):
    name: str
    initials: str
    role: str
    activity: str
    score: int
    color: str
    description: str


class CloudSource(BaseModel):
    name: str
    type: str
    status: Literal["Connected", "Disconnected"]
    eventsToday: int
    health: Literal["Healthy", "Needs review", "Limited history"]
    icon: str
    color: str
    dataFreshnessMin: int


class PolicyRule(BaseModel):
    title: str
    description: str
    enabled: bool
    category: str


class ReportTemplate(BaseModel):
    title: str
    detail: str
    period: str
    type: str


class Configuration(BaseModel):
    notificationsEnabled: bool
    plainLanguageExplanations: bool


class DatasetImportResult(BaseModel):
    acceptedCount: int
    rejectedCount: int
    errors: list[str]


class CommandCenterResponse(BaseModel):
    summaryMetrics: SummaryMetrics
    findings: list[Finding]
    modelRationale: ModelRationale
    accessTrend: list[AccessTrendPoint]
    accessTrendPeakLabel: str
    serviceRisk: list[ServiceRisk]
    serviceRiskSummary: ServiceRiskSummary


class ActivityResponse(BaseModel):
    events: list[ActivityEvent]
    source: Literal["seed", "imported"]


class IdentitiesResponse(BaseModel):
    identities: list[Identity]


class IdentityTimelineResponse(BaseModel):
    events: list[ActivityEvent]


class EstateResponse(BaseModel):
    sources: list[CloudSource]
    sourcesOnline: int


class PoliciesResponse(BaseModel):
    policies: list[PolicyRule]


class ReportsResponse(BaseModel):
    reports: list[ReportTemplate]


class ReportPrepareResponse(BaseModel):
    title: str
    status: Literal["ready"]
    preparedAt: str


class StatusUpdateRequest(BaseModel):
    status: FindingStatus
