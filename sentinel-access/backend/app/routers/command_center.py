import random

from fastapi import APIRouter, Depends, HTTPException

from app.ai_client import AIServiceError, call_chat_completions
from app.schemas.entities import (
    CommandCenterResponse,
    Finding,
    FindingExplanation,
    StatusUpdateRequest,
)
from app.store import Store, get_store

router = APIRouter(prefix="/api", tags=["command-center"])

_SIMULATED_SERVICES = ["AWS IAM", "AWS Secrets Manager", "Azure AD", "GitHub Enterprise", "GCP Audit Logs"]
_SIMULATED_REGIONS = ["Singapore, SG", "Dublin, IE", "Sao Paulo, BR", "Tokyo, JP"]


@router.get("/command-center", response_model=CommandCenterResponse)
def get_command_center(store: Store = Depends(get_store)) -> CommandCenterResponse:
    return CommandCenterResponse(
        summaryMetrics=store.compute_summary_metrics(),
        findings=store.get_findings(),
        modelRationale=store.model_rationale,
        accessTrend=store.access_trend,
        accessTrendPeakLabel=store.access_trend_peak_label,
        serviceRisk=store.service_risk,
        serviceRiskSummary=store.service_risk_summary,
    )


@router.get("/findings/{finding_id}", response_model=Finding)
def get_finding(finding_id: str, store: Store = Depends(get_store)) -> Finding:
    finding = store.get_finding(finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail=f"Finding {finding_id} not found")
    return finding


@router.get("/findings/{finding_id}/explanation", response_model=FindingExplanation)
def get_finding_explanation(finding_id: str, store: Store = Depends(get_store)) -> FindingExplanation:
    finding = store.get_finding(finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail=f"Finding {finding_id} not found")

    cached = store.get_finding_explanation(finding_id)
    if cached is not None:
        return FindingExplanation(findingId=finding_id, explanation=cached, source="ai")

    prompt = (
        "You are a security analyst assistant. In 2-3 plain-language sentences, "
        "explain why the following cloud-access finding was flagged, based only "
        "on its own evidence. Do not invent details beyond what is given.\n\n"
        f"Title: {finding.title}\n"
        f"Entity: {finding.entity} ({finding.role})\n"
        f"Service: {finding.service}\n"
        f"Signals: {', '.join(finding.signals)}\n"
        f"Baseline (normally expected): {finding.baseline}\n"
        f"Description: {finding.description}\n"
    )
    try:
        message = call_chat_completions([{"role": "user", "content": prompt}])
        explanation = (message.get("content") or "").strip()
        if not explanation:
            raise AIServiceError("liteLLM proxy returned an empty explanation")
        store.cache_finding_explanation(finding_id, explanation)
        return FindingExplanation(findingId=finding_id, explanation=explanation, source="ai")
    except AIServiceError:
        fallback = f"{finding.description} {finding.baseline}".strip()
        return FindingExplanation(findingId=finding_id, explanation=fallback, source="fallback")


@router.post("/findings/{finding_id}/status", response_model=Finding)
def update_finding_status(
    finding_id: str, body: StatusUpdateRequest, store: Store = Depends(get_store)
) -> Finding:
    finding = store.update_finding_status(finding_id, body.status)
    if finding is None:
        raise HTTPException(status_code=404, detail=f"Finding {finding_id} not found")
    return finding


@router.post("/findings/simulate-anomaly", response_model=Finding, status_code=201)
def simulate_anomaly(store: Store = Depends(get_store)) -> Finding:
    finding = Finding(
        id=store.next_finding_id(),
        severity="High",
        title="Simulated anomalous access pattern",
        entity="demo.simulated.user",
        role="Cloud Engineer",
        source="203.0.113.42",
        region=random.choice(_SIMULATED_REGIONS),
        service=random.choice(_SIMULATED_SERVICES),
        score=random.randint(70, 95),
        time="just now",
        description="A synthetic high-severity event was injected to demonstrate the detection workflow.",
        signals=["Simulated event", "Injected for demo"],
        baseline="This is a synthetic event; no real baseline applies.",
        recommended="Review as you would any other finding, then dismiss once the demo is complete.",
        status=None,
    )
    return store.add_finding(finding)
