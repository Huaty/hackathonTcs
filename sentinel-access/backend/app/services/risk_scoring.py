from app.schemas.entities import AIAdjustment, RiskCalculation, Severity


FLOOR_MINIMUMS = {None: 0, "High": 65, "Critical": 85}


def severity_for_score(score: int) -> Severity:
    if score >= 85:
        return "Critical"
    if score >= 65:
        return "High"
    if score >= 40:
        return "Medium"
    return "Low"


def calculate_risk(
    policy_score: int,
    ai_adjustment_applied: AIAdjustment,
    severity_floor_minimum: int = 0,
) -> tuple[RiskCalculation, Severity]:
    if not 0 <= policy_score <= 100:
        raise ValueError("policy_score must be between 0 and 100")
    if severity_floor_minimum not in (0, 65, 85):
        raise ValueError("severity_floor_minimum must be 0, 65, or 85")

    pre_floor = max(0, min(100, policy_score + ai_adjustment_applied))
    final_score = max(pre_floor, severity_floor_minimum)
    calculation = RiskCalculation(
        policyScore=policy_score,
        aiAdjustmentApplied=ai_adjustment_applied,
        preFloorScore=pre_floor,
        severityFloorMinimum=severity_floor_minimum,
        finalRiskScore=final_score,
    )
    return calculation, severity_for_score(final_score)

