from itertools import count

from app.schemas.entities import (
    ActivityEvent,
    Configuration,
    Finding,
    MostUrgentCase,
    SummaryMetrics,
)
from app.seed_data import SeedData, load_seed_data

_finding_id_counter = count(1)


class Store:
    def __init__(self, seed: SeedData):
        self._seed = seed
        self.findings: list[Finding] = list(seed.findings)
        self.model_rationale = seed.model_rationale
        self.access_trend = seed.access_trend
        self.access_trend_peak_label = seed.access_trend_peak_label
        self.service_risk = seed.service_risk
        self.service_risk_summary = seed.service_risk_summary
        self.activity_log: list[ActivityEvent] = list(seed.activity_log)
        self.activity_source: str = "seed"
        self.identities = seed.identities
        self.cloud_sources = seed.cloud_sources
        self.cloud_sources_online = seed.cloud_sources_online
        self.policies = list(seed.policies)
        self.reports = seed.reports
        self.configuration = seed.configuration

        self._needs_attention_extra = 0
        self._most_urgent = MostUrgentCase(**seed.most_urgent_case_base)
        self._top_score = max((f.score for f in self.findings), default=0)

    # -- Findings -----------------------------------------------------

    def get_findings(self) -> list[Finding]:
        return self.findings

    def get_finding(self, finding_id: str) -> Finding | None:
        return next((f for f in self.findings if f.id == finding_id), None)

    def update_finding_status(self, finding_id: str, status: str) -> Finding | None:
        finding = self.get_finding(finding_id)
        if finding is None:
            return None
        finding.status = status
        return finding

    def add_finding(self, finding: Finding) -> Finding:
        self.findings.insert(0, finding)
        self._needs_attention_extra += 1
        if finding.score > self._top_score:
            self._top_score = finding.score
            self._most_urgent = MostUrgentCase(rank="01", label=finding.title)
        return finding

    def next_finding_id(self) -> str:
        return f"ALT-SIM-{next(_finding_id_counter):04d}"

    def compute_summary_metrics(self) -> SummaryMetrics:
        # KPI figures mirror the original hardcoded demo: they don't recompute
        # from the visible queue's length (see spec SC-005 / research.md),
        # they only move in response to a newly simulated anomaly (FR-004).
        return SummaryMetrics(
            activitiesChecked=self._seed.activities_checked_base,
            needsAttention=self._seed.needs_attention_base + self._needs_attention_extra,
            mostUrgentCase=self._most_urgent,
            averageReviewTime=self._seed.average_review_time,
            signalConfidencePct=self._seed.signal_confidence_pct,
            identityCoveragePct=self._seed.identity_coverage_pct,
        )

    # -- Activity log ---------------------------------------------------

    def get_activity_log(self) -> tuple[list[ActivityEvent], str]:
        return self.activity_log, self.activity_source

    def replace_activity_log(self, events: list[ActivityEvent], source: str) -> None:
        self.activity_log = events
        self.activity_source = source

    # -- Identities / estate ---------------------------------------------

    def get_identities(self):
        return self.identities

    def get_cloud_sources(self):
        return self.cloud_sources, self.cloud_sources_online

    # -- Policies ---------------------------------------------------------

    def get_policies(self):
        return self.policies

    def toggle_policy(self, title: str):
        for policy in self.policies:
            if policy.title == title:
                policy.enabled = not policy.enabled
                return policy
        return None

    # -- Reports ------------------------------------------------------------

    def get_reports(self):
        return self.reports

    def get_report(self, title: str):
        return next((r for r in self.reports if r.title == title), None)

    # -- Configuration ----------------------------------------------------

    def get_configuration(self) -> Configuration:
        return self.configuration

    def set_configuration(self, config: Configuration) -> Configuration:
        self.configuration = config
        return self.configuration


_store: Store | None = None


def get_store() -> Store:
    global _store
    if _store is None:
        _store = Store(load_seed_data())
    return _store
