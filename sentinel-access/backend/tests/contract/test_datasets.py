from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_import_valid_csv_updates_activity():
    """003-sqlite-storage: upload appends to the activity log rather than
    replacing it, so the resulting count is prior events + acceptedCount,
    not just acceptedCount (see contracts/datasets.md)."""
    before_count = len(client.get("/api/activity").json()["events"])

    csv_content = (
        "timestamp,user,action,ip,service\n"
        "09:00,jane.doe,Deleted an admin policy,10.0.0.5,AWS IAM\n"
        "09:05,bot-runner,Ran scheduled job,10.0.0.9,GCP\n"
    )
    response = client.post(
        "/api/datasets",
        files={"file": ("test.csv", csv_content, "text/csv")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["acceptedCount"] == 2
    assert body["rejectedCount"] == 0

    activity = client.get("/api/activity").json()
    assert activity["source"] == "imported"
    assert len(activity["events"]) == before_count + 2
    new_events = activity["events"][-2:]
    assert new_events[0]["status"] == "Needs attention"


def test_import_invalid_json_rejected():
    before_count = len(client.get("/api/activity").json()["events"])

    response = client.post(
        "/api/datasets",
        files={"file": ("test.json", "not valid json", "application/json")},
    )
    assert response.status_code == 400
    assert len(client.get("/api/activity").json()["events"]) == before_count


def test_import_over_cap_rejected():
    before_count = len(client.get("/api/activity").json()["events"])

    lines = ["timestamp,user,action,ip,service"]
    for i in range(10_001):
        lines.append(f"09:00,user{i},did something,10.0.0.1,AWS IAM")
    csv_content = "\n".join(lines)
    response = client.post(
        "/api/datasets",
        files={"file": ("big.csv", csv_content, "text/csv")},
    )
    assert response.status_code == 400
    assert len(client.get("/api/activity").json()["events"]) == before_count
