from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

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
    identityId: str
    name: str
    initials: str
    role: str
    activity: str
    score: int
    color: str
    description: str
    identityType: Literal["human", "service", "workload"] = "human"
    status: str = "active"
    homeTimezone: str = "UTC"
    baselineConfidence: Optional[Literal["low", "high"]] = None
    lastSeenAt: Optional[str] = None


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
    ruleId: str
    title: str
    description: str
    enabled: bool
    category: Literal["context", "action", "compound_sequence"]
    conditionKey: str
    points: int = Field(ge=0, le=100)
    severityFloor: Optional[Literal["High", "Critical"]] = None
    policyVersion: str


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
    duplicateCount: int = 0
    identitiesCreated: int = 0
    identitiesUpdated: int = 0
    eventsStored: int = 0


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
    narrative: Optional[str] = None


class StatusUpdateRequest(BaseModel):
    status: FindingStatus


class FindingExplanation(BaseModel):
    findingId: str
    explanation: str
    source: Literal["ai", "fallback"]


class CopilotQueryRequest(BaseModel):
    question: str


class CopilotResponse(BaseModel):
    answer: str
    findings: list[Finding] = []
    activity: list[ActivityEvent] = []
    identities: list[Identity] = []


# -- Feature 004: policy-first AI contextual risk scoring -----------------

Severity = Literal["Low", "Medium", "High", "Critical"]
RuleState = Literal["matched", "not_matched", "unknown", "disabled"]
AIStatus = Literal["applied", "zero", "low_confidence", "invalid", "unavailable"]
AIAdjustment = Literal[-15, -5, 0, 10, 20, 25]


class SecurityEvent(BaseModel):
    eventId: str
    identityId: str
    timestampUtc: str
    sourceIp: Optional[str] = None
    location: Optional[str] = None
    cloudService: str
    action: str
    resource: str = "—"
    outcome: str = "success"
    sessionId: Optional[str] = None
    correlationId: Optional[str] = None
    rawPayload: dict = Field(default_factory=dict)


class BaselineHours(BaseModel):
    start: str
    end: str


class IdentityBaseline(BaseModel):
    baselineId: str
    identityId: str
    windowStartUtc: str
    windowEndUtc: str
    usualHours: list[BaselineHours] = Field(default_factory=list)
    usualSourceIps: list[str] = Field(default_factory=list)
    usualLocations: list[str] = Field(default_factory=list)
    usualServices: list[str] = Field(default_factory=list)
    usualActions: list[str] = Field(default_factory=list)
    frequencyP95: float = 0
    sampleCount: int = 0
    activeDayCount: int = 0
    confidence: Literal["low", "high"] = "low"
    unknownFields: list[str] = Field(default_factory=list)
    baselineVersion: str
    createdAt: str


class PolicySnapshot(BaseModel):
    policyVersion: str
    snapshotHash: str
    rules: list[PolicyRule]


class PolicyRuleResult(BaseModel):
    ruleId: str
    category: Literal["context", "action", "compound_sequence"]
    state: RuleState
    selected: bool = False
    configuredPoints: int = Field(ge=0, le=100)
    awardedPoints: int = Field(ge=0, le=100)
    severityFloor: Optional[Literal["High", "Critical"]] = None
    evidence: str
    evidenceEventIds: list[str] = Field(default_factory=list)


class PolicyEvaluation(BaseModel):
    policyEvaluationId: str
    policyVersion: str
    policyScore: int = Field(ge=0, le=100)
    severityFloor: Optional[Literal["High", "Critical"]] = None
    severityFloorMinimum: Literal[0, 65, 85]
    ruleResults: list[PolicyRuleResult]
    snapshotHash: str


class AIContextResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    adjustment: AIAdjustment
    confidence: float = Field(ge=0, le=1)
    riskFactors: list[str]
    mitigatingFactors: list[str]
    evidenceEventIds: list[str]
    explanation: str


class AIContextDecision(BaseModel):
    aiDecisionId: str
    status: AIStatus
    adjustmentRequested: Optional[int] = None
    adjustmentApplied: AIAdjustment = 0
    confidence: Optional[float] = None
    riskFactors: list[str] = Field(default_factory=list)
    mitigatingFactors: list[str] = Field(default_factory=list)
    evidenceEventIds: list[str] = Field(default_factory=list)
    explanation: str
    validationErrors: list[str] = Field(default_factory=list)
    model: Optional[str] = None
    promptVersion: str


class RiskCalculation(BaseModel):
    policyScore: int = Field(ge=0, le=100)
    aiAdjustmentApplied: AIAdjustment
    preFloorScore: int = Field(ge=0, le=100)
    severityFloorMinimum: Literal[0, 65, 85]
    finalRiskScore: int = Field(ge=0, le=100)


class RiskBaselineRef(BaseModel):
    baselineId: str
    confidence: Literal["low", "high"]


class RiskAssessment(BaseModel):
    assessmentId: str
    eventId: str
    baseline: RiskBaselineRef
    policyEvaluation: PolicyEvaluation
    aiContext: AIContextDecision
    calculation: RiskCalculation
    severity: Severity
    scoringVersion: str
    createdAt: str


class RiskAssessmentRequest(BaseModel):
    eventId: str
    forceAiRefresh: bool = False


class RiskAssessmentList(BaseModel):
    assessments: list[RiskAssessment]


class IdentityRiskSummary(BaseModel):
    latestPolicyScore: Optional[int] = None
    latestAiAdjustment: Optional[int] = None
    latestAiStatus: Optional[AIStatus] = None
    latestSeverityFloor: Optional[Literal["High", "Critical"]] = None
    latestFinalRiskScore: Optional[int] = None
    matchedPolicyIds: list[str] = Field(default_factory=list)


class IdentityDetail(BaseModel):
    identityId: str
    name: str
    identityType: Literal["human", "service", "workload"]
    role: str
    status: str
    homeTimezone: str


class IdentityProfileResponse(BaseModel):
    identity: IdentityDetail
    baseline: Optional[IdentityBaseline] = None
    events: list[SecurityEvent]
    assessments: list[RiskAssessment]
    riskSummary: IdentityRiskSummary
