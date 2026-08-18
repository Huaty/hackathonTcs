from app.schemas.entities import SecurityEvent
from app.services.baseline import BASELINE_DAYS, MIN_ACTIVE_DAYS, MIN_EVENTS, build_baseline, event_frequency, parse_utc

IDENTITY_ID = "id-test"
TARGET = "2026-08-01T09:05:00Z"


def make_event(event_id: str, timestamp: str, **overrides) -> SecurityEvent:
    fields = dict(
        eventId=event_id,
        identityId=IDENTITY_ID,
        timestampUtc=timestamp,
        sourceIp="10.0.0.5",
        location="US",
        cloudService="s3",
        action="GetObject",
        resource="bucket/x",
        outcome="success",
    )
    fields.update(overrides)
    return SecurityEvent(**fields)


def established_history(days: int = 8, per_day: int = 3, **event_overrides) -> list[SecurityEvent]:
    """Events on `days` distinct calendar days within the 30-day window
    before TARGET, `per_day` events each — enough to satisfy FR-004
    (>=20 events, >=7 active days) by default."""
    events = []
    for day in range(days):
        for k in range(per_day):
            timestamp = f"2026-07-{10 + day:02d}T09:0{k}:00Z"
            events.append(make_event(f"EVT-{day}-{k}", timestamp, **event_overrides))
    return events


# -- 20-events / 7-active-days confidence threshold (FR-004) ----------------


def test_baseline_is_high_confidence_with_enough_events_and_active_days():
    history = established_history(days=8, per_day=3)  # 24 events, 8 active days
    baseline = build_baseline(IDENTITY_ID, TARGET, history)
    assert baseline.sampleCount == 24
    assert baseline.activeDayCount == 8
    assert baseline.confidence == "high"
    assert baseline.unknownFields == []


def test_baseline_is_low_confidence_with_fewer_than_20_events():
    history = established_history(days=8, per_day=2)  # 16 events, 8 active days
    baseline = build_baseline(IDENTITY_ID, TARGET, history)
    assert baseline.sampleCount == 16
    assert baseline.confidence == "low"
    assert baseline.unknownFields == ["source", "location", "hours", "services", "actions", "frequency"]


def test_baseline_is_low_confidence_with_fewer_than_7_active_days():
    # 24 events but crammed into a single day.
    history = [make_event(f"EVT-{k}", f"2026-07-15T09:{k:02d}:00Z") for k in range(24)]
    baseline = build_baseline(IDENTITY_ID, TARGET, history)
    assert baseline.sampleCount == 24
    assert baseline.activeDayCount == 1
    assert baseline.confidence == "low"


def test_baseline_exactly_at_threshold_is_high_confidence():
    history = established_history(days=MIN_ACTIVE_DAYS, per_day=3)  # 21 events, 7 active days
    baseline = build_baseline(IDENTITY_ID, TARGET, history)
    assert baseline.sampleCount == 21 >= MIN_EVENTS
    assert baseline.activeDayCount == MIN_ACTIVE_DAYS
    assert baseline.confidence == "high"


# -- 30-day window ------------------------------------------------------


def test_baseline_excludes_events_outside_30_day_window():
    assert BASELINE_DAYS == 30
    in_window = established_history(days=8, per_day=3)
    too_old = [make_event("EVT-OLD", "2026-05-01T09:00:00Z")]  # more than 30 days before TARGET
    baseline = build_baseline(IDENTITY_ID, TARGET, in_window + too_old)
    assert baseline.sampleCount == 24  # the too-old event is excluded


def test_baseline_excludes_events_at_or_after_target_time():
    history = established_history(days=8, per_day=3)
    future = [make_event("EVT-FUTURE", TARGET)]  # not strictly before target
    baseline = build_baseline(IDENTITY_ID, TARGET, history + future)
    assert baseline.sampleCount == 24


# -- Usual hours/IPs/locations/services/actions --------------------------


def test_baseline_usual_fields_reflect_eligible_history():
    history = established_history(days=8, per_day=3, sourceIp="10.0.0.5", location="US", cloudService="s3", action="GetObject")
    baseline = build_baseline(IDENTITY_ID, TARGET, history)
    assert baseline.usualSourceIps == ["10.0.0.5"]
    assert baseline.usualLocations == ["US"]
    assert baseline.usualServices == ["s3"]
    assert baseline.usualActions == ["GetObject"]
    assert baseline.usualHours  # populated from the observed hour(s)


def test_baseline_with_no_history_is_low_confidence_with_all_unknown():
    baseline = build_baseline(IDENTITY_ID, TARGET, [])
    assert baseline.sampleCount == 0
    assert baseline.activeDayCount == 0
    assert baseline.confidence == "low"
    assert baseline.usualHours == []
    assert baseline.usualSourceIps == []
    assert set(baseline.unknownFields) == {"source", "location", "hours", "services", "actions", "frequency"}


# -- 15-minute frequency p95 -----------------------------------------------


def test_baseline_frequency_p95_reflects_15_minute_buckets():
    # 5 buckets/day with counts [1,1,1,1,5] -> p95 of the 40 bucket counts
    # across 8 days should reflect the busiest bucket appearing regularly.
    events = []
    for day in range(8):
        base_hour = 9
        for bucket in range(4):
            events.append(make_event(f"EVT-{day}-{bucket}", f"2026-07-{10 + day:02d}T{base_hour:02d}:{bucket * 15:02d}:00Z"))
        # A busy bucket with 5 events in one 15-minute window.
        for extra in range(5):
            events.append(
                make_event(f"EVT-{day}-busy-{extra}", f"2026-07-{10 + day:02d}T{base_hour + 1:02d}:0{extra}:00Z")
            )
    baseline = build_baseline(IDENTITY_ID, TARGET, events)
    assert baseline.frequencyP95 >= 5


def test_event_frequency_counts_same_service_within_15_minutes():
    target = make_event("EVT-TARGET", "2026-08-01T09:14:00Z", cloudService="s3")
    sequence = [
        make_event("EVT-A", "2026-08-01T09:01:00Z", cloudService="s3"),  # within 15 min, same service
        make_event("EVT-B", "2026-08-01T09:05:00Z", cloudService="s3"),  # within 15 min, same service
        make_event("EVT-C", "2026-08-01T08:50:00Z", cloudService="s3"),  # outside 15 min
        make_event("EVT-D", "2026-08-01T09:10:00Z", cloudService="iam"),  # different service
        target,
    ]
    assert event_frequency(target, sequence) == 3  # target itself + EVT-A + EVT-B


def test_event_frequency_is_at_least_one_for_the_event_itself():
    target = make_event("EVT-ONLY", "2026-08-01T09:00:00Z")
    assert event_frequency(target, [target]) == 1


# -- Determinism / versioning -----------------------------------------------


def test_baseline_id_is_deterministic_for_identical_inputs():
    history = established_history(days=8, per_day=3)
    first = build_baseline(IDENTITY_ID, TARGET, history)
    second = build_baseline(IDENTITY_ID, TARGET, history)
    assert first.baselineId == second.baselineId


def test_baseline_id_changes_when_history_changes():
    history = established_history(days=8, per_day=3)
    baseline_a = build_baseline(IDENTITY_ID, TARGET, history)
    baseline_b = build_baseline(IDENTITY_ID, TARGET, history + [make_event("EVT-EXTRA", "2026-07-20T09:00:00Z")])
    assert baseline_a.baselineId != baseline_b.baselineId


def test_baseline_version_is_stamped():
    baseline = build_baseline(IDENTITY_ID, TARGET, established_history())
    assert baseline.baselineVersion == "identity-baseline-v1"


def test_parse_utc_normalizes_z_suffix_and_naive_datetimes():
    assert parse_utc("2026-08-01T09:00:00Z") == parse_utc("2026-08-01T09:00:00+00:00")
