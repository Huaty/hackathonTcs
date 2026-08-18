from fastapi import APIRouter, Depends, HTTPException, Response

from app.schemas.entities import RiskAssessment, RiskAssessmentList, RiskAssessmentRequest
from app.store import EventNotFoundError, RiskAssessmentPrerequisiteError, Store, get_store

router = APIRouter(prefix="/api", tags=["risk-assessments"])


@router.post("/risk-assessments", response_model=RiskAssessment)
def create_risk_assessment(
    payload: RiskAssessmentRequest, response: Response, store: Store = Depends(get_store)
) -> RiskAssessment:
    try:
        assessment, created = store.create_risk_assessment(payload.eventId, payload.forceAiRefresh)
    except EventNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RiskAssessmentPrerequisiteError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    response.status_code = 201 if created else 200
    return assessment


@router.get("/risk-assessments/{assessment_id}", response_model=RiskAssessment)
def get_risk_assessment(assessment_id: str, store: Store = Depends(get_store)) -> RiskAssessment:
    assessment = store.get_risk_assessment(assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail=f"Risk assessment '{assessment_id}' not found")
    return assessment


@router.get("/events/{event_id}/risk-assessments", response_model=RiskAssessmentList)
def get_event_risk_assessments(event_id: str, store: Store = Depends(get_store)) -> RiskAssessmentList:
    return RiskAssessmentList(assessments=store.get_risk_assessments_for_event(event_id))
