from collections import Counter
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from math import ceil

from app.schemas.entities import BaselineHours, IdentityBaseline, SecurityEvent
from app.services import BASELINE_VERSION


BASELINE_DAYS = 30
MIN_EVENTS = 20
MIN_ACTIVE_DAYS = 7


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _p95(values: list[int]) -> float:
    if not values:
        return 0
    ordered = sorted(values)
    return float(ordered[max(0, ceil(0.95 * len(ordered)) - 1)])


def build_baseline(identity_id: str, target_time_utc: str, history: list[SecurityEvent]) -> IdentityBaseline:
    target = parse_utc(target_time_utc)
    start = target - timedelta(days=BASELINE_DAYS)
    eligible = sorted(
        (event for event in history if start <= parse_utc(event.timestampUtc) < target),
        key=lambda event: event.timestampUtc,
    )
    active_days = {parse_utc(event.timestampUtc).date() for event in eligible}
    established = len(eligible) >= MIN_EVENTS and len(active_days) >= MIN_ACTIVE_DAYS

    hours = sorted({parse_utc(event.timestampUtc).hour for event in eligible})
    usual_hours = []
    if hours:
        usual_hours = [BaselineHours(start=f"{hours[0]:02d}:00", end=f"{hours[-1]:02d}:59")]

    buckets: Counter[tuple[str, str]] = Counter()
    for event in eligible:
        stamp = parse_utc(event.timestampUtc)
        bucket = stamp.replace(minute=(stamp.minute // 15) * 15, second=0, microsecond=0).isoformat()
        buckets[(event.cloudService, bucket)] += 1

    digest_input = f"{identity_id}|{start.isoformat()}|{target.isoformat()}|{len(eligible)}|{BASELINE_VERSION}"
    baseline_id = f"base-{sha256(digest_input.encode()).hexdigest()[:20]}"
    created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    unknown = [] if established else ["source", "location", "hours", "services", "actions", "frequency"]
    return IdentityBaseline(
        baselineId=baseline_id,
        identityId=identity_id,
        windowStartUtc=start.isoformat().replace("+00:00", "Z"),
        windowEndUtc=target.isoformat().replace("+00:00", "Z"),
        usualHours=usual_hours,
        usualSourceIps=sorted({event.sourceIp for event in eligible if event.sourceIp}),
        usualLocations=sorted({event.location for event in eligible if event.location}),
        usualServices=sorted({event.cloudService for event in eligible}),
        usualActions=sorted({event.action for event in eligible}),
        frequencyP95=_p95(list(buckets.values())),
        sampleCount=len(eligible),
        activeDayCount=len(active_days),
        confidence="high" if established else "low",
        unknownFields=unknown,
        baselineVersion=BASELINE_VERSION,
        createdAt=created_at,
    )


def event_frequency(event: SecurityEvent, sequence: list[SecurityEvent]) -> int:
    target = parse_utc(event.timestampUtc)
    start = target - timedelta(minutes=15)
    return 1 + sum(
        1
        for prior in sequence
        if prior.eventId != event.eventId
        and prior.cloudService == event.cloudService
        and start <= parse_utc(prior.timestampUtc) < target
    )

