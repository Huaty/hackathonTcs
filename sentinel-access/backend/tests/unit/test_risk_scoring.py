import pytest

from app.services.risk_scoring import calculate_risk, severity_for_score

# -- clamp(policyScore + aiAdjustmentApplied, 0, 100) ------------------------


def test_calculate_risk_basic_sum_with_no_floor():
    calc, severity = calculate_risk(policy_score=50, ai_adjustment_applied=10)
    assert calc.policyScore == 50
    assert calc.aiAdjustmentApplied == 10
    assert calc.preFloorScore == 60
    assert calc.severityFloorMinimum == 0
    assert calc.finalRiskScore == 60
    assert severity == "Medium"


def test_calculate_risk_negative_adjustment_reduces_score():
    calc, _ = calculate_risk(policy_score=50, ai_adjustment_applied=-15)
    assert calc.preFloorScore == 35
    assert calc.finalRiskScore == 35


def test_calculate_risk_positive_adjustment_clamps_at_100():
    calc, severity = calculate_risk(policy_score=90, ai_adjustment_applied=25)
    assert calc.preFloorScore == 100
    assert calc.finalRiskScore == 100
    assert severity == "Critical"


def test_calculate_risk_negative_adjustment_clamps_at_0():
    calc, severity = calculate_risk(policy_score=5, ai_adjustment_applied=-15)
    assert calc.preFloorScore == 0
    assert calc.finalRiskScore == 0
    assert severity == "Low"


def test_calculate_risk_zero_adjustment_is_identity():
    calc, _ = calculate_risk(policy_score=42, ai_adjustment_applied=0)
    assert calc.preFloorScore == 42
    assert calc.finalRiskScore == 42


# -- finalRiskScore = max(preFloorScore, severityFloorMinimum) --------------


def test_high_floor_raises_a_low_pre_floor_score():
    calc, severity = calculate_risk(policy_score=20, ai_adjustment_applied=0, severity_floor_minimum=65)
    assert calc.preFloorScore == 20
    assert calc.finalRiskScore == 65
    assert severity == "High"


def test_critical_floor_raises_a_low_pre_floor_score():
    calc, severity = calculate_risk(policy_score=10, ai_adjustment_applied=0, severity_floor_minimum=85)
    assert calc.finalRiskScore == 85
    assert severity == "Critical"


def test_floor_never_lowers_a_score_already_above_it():
    calc, severity = calculate_risk(policy_score=95, ai_adjustment_applied=0, severity_floor_minimum=65)
    assert calc.finalRiskScore == 95
    assert severity == "Critical"


def test_negative_ai_adjustment_cannot_bypass_the_floor():
    calc, severity = calculate_risk(policy_score=75, ai_adjustment_applied=-15, severity_floor_minimum=65)
    assert calc.preFloorScore == 60  # AI alone would have dropped it below the floor
    assert calc.finalRiskScore == 65  # but the floor wins
    assert severity == "High"


# -- Severity boundaries: 0-39 Low | 40-64 Medium | 65-84 High | 85-100 Critical


@pytest.mark.parametrize(
    "score,expected",
    [
        (0, "Low"),
        (39, "Low"),
        (40, "Medium"),
        (64, "Medium"),
        (65, "High"),
        (84, "High"),
        (85, "Critical"),
        (100, "Critical"),
    ],
)
def test_severity_for_score_boundaries(score, expected):
    assert severity_for_score(score) == expected


@pytest.mark.parametrize(
    "policy_score,adjustment,expected_severity",
    [
        (39, 0, "Low"),
        (30, 10, "Medium"),  # 40
        (55, 10, "High"),  # 65
        (60, 25, "Critical"),  # 85 (clamped at 100 not needed here)
        (75, -15, "Medium"),  # 60, no floor supplied
    ],
)
def test_calculate_risk_severity_boundaries_via_full_pipeline(policy_score, adjustment, expected_severity):
    calc, severity = calculate_risk(policy_score, adjustment)
    assert severity == expected_severity
    assert calc.finalRiskScore == calc.preFloorScore


# -- Input validation ---------------------------------------------------


def test_calculate_risk_rejects_out_of_range_policy_score():
    with pytest.raises(ValueError):
        calculate_risk(policy_score=101, ai_adjustment_applied=0)
    with pytest.raises(ValueError):
        calculate_risk(policy_score=-1, ai_adjustment_applied=0)


def test_calculate_risk_rejects_invalid_floor_minimum():
    with pytest.raises(ValueError):
        calculate_risk(policy_score=50, ai_adjustment_applied=0, severity_floor_minimum=50)
