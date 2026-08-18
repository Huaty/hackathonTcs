import json
from pathlib import Path

from app import db
from app.services.identity_resolution import stable_identity_id

SEED_FILE = Path(__file__).resolve().parents[2] / "server" / "data" / "synthetic-data.json"


def seed_database() -> None:
    """Load SEED_FILE and INSERT its contents into the SQLite tables
    created by db.init_schema(). Called exactly once per process, from
    Store's lazy singleton (app/store.py get_store())."""
    raw = json.loads(SEED_FILE.read_text(encoding="utf-8"))

    db.executemany(
        "INSERT INTO findings (id, severity, title, entity, role, source, region, service, score, time, "
        "description, signals, baseline, recommended, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                f["id"], f["severity"], f["title"], f["entity"], f["role"], f["source"], f["region"],
                f["service"], f["score"], f["time"], f["description"], json.dumps(f["signals"]),
                f["baseline"], f["recommended"], f.get("status"),
            )
            for f in raw["alerts"]
        ],
    )

    db.executemany(
        "INSERT INTO activity_log (time, actor, action, source, system, status, tone) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (e["time"], e["actor"], e["action"], e["source"], e["system"], e["status"], e["tone"])
            for e in raw["activityLog"]
        ],
    )

    db.executemany(
        "INSERT INTO identities (identity_id, name, initials, role, activity, score, color, description) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                stable_identity_id(i["name"]), i["name"], i["initials"], i["role"], i["activity"],
                i["score"], i["color"], i["description"],
            )
            for i in raw["identities"]
        ],
    )

    db.executemany(
        "INSERT INTO cloud_sources (name, type, status, eventsToday, health, icon, color, dataFreshnessMin) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (c["name"], c["type"], c["status"], c["eventsToday"], c["health"], c["icon"], c["color"], c["dataFreshnessMin"])
            for c in raw["cloudSources"]
        ],
    )

    db.executemany(
        "INSERT INTO policies (rule_id, title, description, enabled, category, condition_key, points, "
        "severity_floor, policy_version, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                p["ruleId"], p["title"], p["description"], int(p["enabled"]), p["category"],
                p["conditionKey"], p["points"], p.get("severityFloor"), p["policyVersion"], p["updatedAt"],
            )
            for p in raw["policies"]
        ],
    )

    db.executemany(
        "INSERT INTO reports (title, detail, period, type) VALUES (?, ?, ?, ?)",
        [(r["title"], r["detail"], r["period"], r["type"]) for r in raw["reports"]],
    )

    db.executemany(
        "INSERT INTO access_trend (label, events, anomalies) VALUES (?, ?, ?)",
        [(p["label"], p["events"], p["anomalies"]) for p in raw["accessTrend"]],
    )

    db.executemany(
        "INSERT INTO service_risk (name, risk, events) VALUES (?, ?, ?)",
        [(s["name"], s["risk"], s["events"]) for s in raw["serviceRisk"]],
    )

    rationale = raw["modelRationale"]
    db.execute(
        "INSERT INTO model_rationale (top_finding_id, explanation, signals) VALUES (?, ?, ?)",
        (rationale["topFindingId"], rationale["explanation"], json.dumps(rationale["signals"])),
    )

    summary = raw["serviceRiskSummary"]
    db.execute(
        "INSERT INTO service_risk_summary (highest_risk_service, sensitive_assets, coverage) VALUES (?, ?, ?)",
        (summary["highestRiskService"], summary["sensitiveAssets"], summary["coverage"]),
    )

    db.execute(
        "INSERT INTO configuration (notifications_enabled, plain_language_explanations) VALUES (?, ?)",
        (1, 1),
    )

    metrics = raw["summaryMetrics"]
    meta_values = {
        "access_trend_peak_label": raw["accessTrendPeakLabel"],
        "cloud_sources_online": str(raw["cloudSourcesOnline"]),
        "average_review_time": metrics["averageReviewTime"],
        "signal_confidence_pct": str(metrics["signalConfidencePct"]),
        "identity_coverage_pct": str(metrics["identityCoveragePct"]),
        "activity_source": "seed",
    }
    db.executemany(
        "INSERT INTO meta (key, value) VALUES (?, ?)",
        list(meta_values.items()),
    )
