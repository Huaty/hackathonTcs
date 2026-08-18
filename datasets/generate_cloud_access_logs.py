"""
Synthetic Cloud Access Log Generator
=====================================
Generates realistic cloud access / identity logs with per-user behavioral
baselines, then injects labeled anomalies on top — suitable for demoing a
Cloud Access Anomaly Detection & User Behavior Analytics (UBA) tool.

Usage:
    python3 generate_cloud_access_logs.py

Outputs (in ./output/):
    cloud_access_logs.csv   - full log stream (normal + anomalous), labeled
    cloud_access_logs.json  - same data as JSON (array of records)
    users.csv                - user roster with baseline profile summary
"""

import json
import random
import uuid
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from faker import Faker

fake = Faker()
random.seed(42)
np.random.seed(42)

# ----------------------------------------------------------------------
# CONFIG — tune these to control dataset size / anomaly density
# ----------------------------------------------------------------------
NUM_USERS = 40
DAYS_OF_HISTORY = 21
EVENTS_PER_USER_PER_DAY = (3, 12)      # min, max normal events/day
N_ANOMALY_INCIDENTS = 130              # number of distinct anomalous *incidents*
                                        # (a "brute force" incident = one row per attempt)
N_ATTACK_CHAINS = 6                    # multi-stage attack narratives (initial access ->
                                        # recon -> privilege escalation -> exfiltration)
N_HARD_NEGATIVES = 25                  # benign-but-unusual events, labeled is_anomaly=0,
                                        # to stop the demo from being "too easy"
QUIET_ANOMALY_FRACTION = 0.25          # fraction of single-event anomalies made subtle
                                        # (lower risk_score, smaller deviation)
OUTPUT_DIR = "output"

ROLES = ["Software Engineer", "Data Analyst", "IT Admin", "Sales Rep",
          "HR Specialist", "Finance Analyst", "DevOps Engineer", "Contractor"]
DEPARTMENTS = ["Engineering", "Data", "IT", "Sales", "HR", "Finance", "Operations"]
SERVICES = ["S3", "EC2", "IAM", "RDS", "Lambda", "CloudWatch", "VPC", "EKS"]
DEVICE_TYPES = ["Laptop-Windows", "Laptop-Mac", "Mobile-iOS", "Mobile-Android", "Linux-Workstation"]
LOGIN_METHODS = ["password", "sso", "mfa", "sso+mfa"]

NORMAL_ACTIONS = [
    ("login", "AuthService"),
    ("s3_read", "S3"),
    ("s3_list", "S3"),
    ("ec2_describe", "EC2"),
    ("lambda_invoke", "Lambda"),
    ("cloudwatch_view", "CloudWatch"),
    ("rds_query", "RDS"),
    ("file_download", "S3"),
    ("dashboard_view", "CloudWatch"),
]

SENSITIVE_ACTIONS = [
    ("iam_policy_update", "IAM"),
    ("privilege_escalation", "IAM"),
    ("security_group_change", "VPC"),
    ("root_login", "AuthService"),
    ("bulk_export", "S3"),
]

ANOMALY_TYPES = [
    "impossible_travel",
    "off_hours_access",
    "brute_force",
    "privilege_escalation",
    "data_exfiltration",
    "new_device_new_geo",
    "dormant_account_reactivation",
    "api_rate_spike",
]

# A pool of plausible cities/countries so "impossible travel" has real distance
GEO_POOL = [
    ("Singapore", "Singapore", 1.35, 103.82),
    ("Mumbai", "India", 19.08, 72.88),
    ("London", "UK", 51.51, -0.13),
    ("New York", "USA", 40.71, -74.01),
    ("Sydney", "Australia", -33.87, 151.21),
    ("Frankfurt", "Germany", 50.11, 8.68),
    ("Tokyo", "Japan", 35.68, 139.69),
    ("Sao Paulo", "Brazil", -23.55, -46.63),
    ("Toronto", "Canada", 43.65, -79.38),
    ("Lagos", "Nigeria", 6.52, 3.38),
]

# ----------------------------------------------------------------------
# STEP 1 — Build user roster with individual behavioral baselines
# ----------------------------------------------------------------------
def build_users(n):
    users = []
    for i in range(n):
        role = random.choice(ROLES)
        dept = random.choice(DEPARTMENTS)
        home_geo = random.choice(GEO_POOL)
        users.append({
            "user_id": f"u{i:04d}",
            "user_name": fake.name(),
            "role": role,
            "department": dept,
            "home_city": home_geo[0],
            "home_country": home_geo[1],
            "home_lat": home_geo[2],
            "home_lon": home_geo[3],
            "home_ip": fake.ipv4_public(),
            "usual_device": random.choice(DEVICE_TYPES),
            "usual_start_hour": random.randint(7, 10),   # local working hours
            "usual_end_hour": random.randint(17, 20),
            "is_privileged": role in ("IT Admin", "DevOps Engineer"),
            "avg_daily_bytes": random.randint(5_000_000, 50_000_000),
        })
    return users


# ----------------------------------------------------------------------
# STEP 2 — Generate NORMAL events for a user on a given day
# ----------------------------------------------------------------------
def gen_normal_event(user, day):
    hour = random.randint(user["usual_start_hour"], user["usual_end_hour"])
    minute = random.randint(0, 59)
    ts = day.replace(hour=hour, minute=minute, second=random.randint(0, 59))
    action, service = random.choice(NORMAL_ACTIONS)

    return {
        "event_id": str(uuid.uuid4()),
        "timestamp": ts.isoformat(),
        "user_id": user["user_id"],
        "user_name": user["user_name"],
        "role": user["role"],
        "department": user["department"],
        "source_ip": user["home_ip"],
        "city": user["home_city"],
        "country": user["home_country"],
        "device_type": user["usual_device"],
        "login_method": random.choice(LOGIN_METHODS[:3]),
        "action": action,
        "service": service,
        "status": "success" if random.random() > 0.02 else "failure",
        "session_duration_min": round(np.random.gamma(2, 8), 1),
        "bytes_transferred": int(np.random.normal(user["avg_daily_bytes"] / 8, 500_000)),
        "is_anomaly": 0,
        "anomaly_type": "none",
        "risk_score": round(random.uniform(0, 15), 1),
        "incident_id": "",
        "attack_stage": "none",
        "benign_edge_case": "none",
    }


# ----------------------------------------------------------------------
# STEP 3 — Generate an ANOMALOUS event, by type
# ----------------------------------------------------------------------
def gen_anomaly_event(user, day, anomaly_type, quiet=False):
    base = gen_normal_event(user, day)
    base["is_anomaly"] = 1
    base["anomaly_type"] = anomaly_type

    if anomaly_type == "impossible_travel":
        far_geo = random.choice([g for g in GEO_POOL if g[0] != user["home_city"]])
        ts = day.replace(hour=random.randint(0, 23), minute=random.randint(0, 59))
        base.update({
            "timestamp": ts.isoformat(),
            "city": far_geo[0], "country": far_geo[1],
            "source_ip": fake.ipv4_public(),
            "action": "login", "service": "AuthService",
            "risk_score": round(random.uniform(75, 98), 1),
        })

    elif anomaly_type == "off_hours_access":
        odd_hour = random.choice([0, 1, 2, 3, 4, 23])
        ts = day.replace(hour=odd_hour, minute=random.randint(0, 59))
        action, service = random.choice(SENSITIVE_ACTIONS if user["is_privileged"] else NORMAL_ACTIONS)
        base.update({
            "timestamp": ts.isoformat(),
            "action": action, "service": service,
            "risk_score": round(random.uniform(55, 85), 1),
        })

    elif anomaly_type == "brute_force":
        base.update({
            "action": "login", "service": "AuthService",
            "status": "failure",
            "risk_score": round(random.uniform(60, 90), 1),
        })
        # brute force is usually a burst — caller adds repeats

    elif anomaly_type == "privilege_escalation":
        action, service = random.choice(SENSITIVE_ACTIONS)
        base.update({
            "action": action, "service": service,
            "status": "success",
            "risk_score": round(random.uniform(80, 99), 1),
        })

    elif anomaly_type == "data_exfiltration":
        base.update({
            "action": "bulk_export", "service": "S3",
            "bytes_transferred": int(user["avg_daily_bytes"] * random.uniform(8, 25)),
            "session_duration_min": round(random.uniform(45, 180), 1),
            "risk_score": round(random.uniform(70, 97), 1),
        })

    elif anomaly_type == "new_device_new_geo":
        far_geo = random.choice(GEO_POOL)
        base.update({
            "city": far_geo[0], "country": far_geo[1],
            "device_type": random.choice(DEVICE_TYPES),
            "source_ip": fake.ipv4_public(),
            "login_method": "password",
            "risk_score": round(random.uniform(50, 80), 1),
        })

    elif anomaly_type == "dormant_account_reactivation":
        base.update({
            "action": "login", "service": "AuthService",
            "risk_score": round(random.uniform(45, 75), 1),
        })

    elif anomaly_type == "api_rate_spike":
        action, service = random.choice(NORMAL_ACTIONS)
        base.update({
            "action": action, "service": service,
            "risk_score": round(random.uniform(40, 70), 1),
        })

    if quiet:
        # Soften the signal: lower risk score, and where relevant pull the
        # deviating metric (bytes/duration) back toward a normal-looking range.
        # These are still real, labeled anomalies — just harder to catch, so
        # your model/detector has something to prove.
        base["risk_score"] = round(base["risk_score"] * random.uniform(0.35, 0.55), 1)
        if anomaly_type == "data_exfiltration":
            base["bytes_transferred"] = int(user["avg_daily_bytes"] * random.uniform(2.5, 4))
        if base.get("session_duration_min", 0) and anomaly_type == "data_exfiltration":
            base["session_duration_min"] = round(random.uniform(15, 30), 1)

    return base


# ----------------------------------------------------------------------
# STEP 3b — Multi-stage attack chains (a connected narrative, not a
# single isolated event — great for a "story" demo moment)
# ----------------------------------------------------------------------
ATTACK_CHAIN_TEMPLATE = [
    # (attack_stage, action, service, risk range, hours_offset range)
    ("initial_access", "login", "AuthService", (45, 65), (0, 0)),
    ("reconnaissance", "s3_list", "S3", (35, 55), (0.2, 0.8)),
    ("reconnaissance", "iam_policy_update".replace("update", "list"), "IAM", (35, 55), (0.3, 1.0)),
    ("privilege_escalation", "iam_policy_update", "IAM", (80, 96), (1.0, 3.0)),
    ("persistence", "iam_create_access_key", "IAM", (75, 92), (1.5, 4.0)),
    ("exfiltration", "bulk_export", "S3", (85, 99), (2.0, 6.0)),
]


def gen_attack_chain(user, day):
    """Generate one connected multi-stage attack incident tied to a single
    user, sharing one incident_id, spread over a few hours."""
    incident_id = str(uuid.uuid4())
    far_geo = random.choice(GEO_POOL)
    start_hour = random.choice([1, 2, 3, 22, 23])  # attacks often start off-hours
    base_ts = day.replace(hour=start_hour, minute=random.randint(0, 59))
    new_device = random.choice(DEVICE_TYPES)
    new_ip = fake.ipv4_public()

    events = []
    for stage, action, service, risk_range, hour_offset_range in ATTACK_CHAIN_TEMPLATE:
        offset_hours = random.uniform(*hour_offset_range)
        ts = base_ts + timedelta(hours=offset_hours, minutes=random.randint(0, 20))
        ev = gen_normal_event(user, day)  # base shape, then override
        ev.update({
            "timestamp": ts.isoformat(),
            "city": far_geo[0], "country": far_geo[1],
            "source_ip": new_ip,
            "device_type": new_device,
            "login_method": "password",
            "action": action,
            "service": service,
            "status": "success",
            "is_anomaly": 1,
            "anomaly_type": "multi_stage_attack",
            "attack_stage": stage,
            "incident_id": incident_id,
            "risk_score": round(random.uniform(*risk_range), 1),
        })
        if stage == "exfiltration":
            ev["bytes_transferred"] = int(user["avg_daily_bytes"] * random.uniform(10, 30))
            ev["session_duration_min"] = round(random.uniform(30, 120), 1)
        events.append(ev)
    return events


# ----------------------------------------------------------------------
# STEP 3c — Hard negatives: unusual-looking but legitimate activity,
# labeled is_anomaly=0. Stops a detector from just learning "anything
# unusual = bad" and gives your demo a "look, we don't over-alert" beat.
# ----------------------------------------------------------------------
def gen_hard_negative(user, day):
    scenario = random.choice(["business_travel", "on_call_shift", "scheduled_report"])
    ev = gen_normal_event(user, day)
    ev["benign_edge_case"] = scenario

    if scenario == "business_travel":
        # Genuine travel: new-ish city, but known device + strong auth (MFA)
        travel_geo = random.choice(GEO_POOL)
        ev.update({
            "city": travel_geo[0], "country": travel_geo[1],
            "login_method": "sso+mfa",
            "action": "login", "service": "AuthService",
            "risk_score": round(random.uniform(20, 35), 1),
        })

    elif scenario == "on_call_shift":
        # Off-hours, but by a privileged/on-call role doing a routine task
        odd_hour = random.choice([0, 1, 22, 23])
        ts = day.replace(hour=odd_hour, minute=random.randint(0, 59))
        ev.update({
            "timestamp": ts.isoformat(),
            "action": "cloudwatch_view", "service": "CloudWatch",
            "risk_score": round(random.uniform(15, 30), 1),
        })

    elif scenario == "scheduled_report":
        # Larger-than-usual export, but modest and via known device/geo —
        # e.g. a monthly reporting job a Data/Finance analyst runs
        ev.update({
            "action": "bulk_export", "service": "S3",
            "bytes_transferred": int(user["avg_daily_bytes"] * random.uniform(2, 3)),
            "session_duration_min": round(random.uniform(20, 40), 1),
            "risk_score": round(random.uniform(20, 38), 1),
        })

    return ev


# ----------------------------------------------------------------------
# STEP 4 — Assemble the full log stream
# ----------------------------------------------------------------------
def generate_dataset():
    users = build_users(NUM_USERS)
    start_date = datetime.now() - timedelta(days=DAYS_OF_HISTORY)
    all_events = []

    for user in users:
        for d in range(DAYS_OF_HISTORY):
            day = start_date + timedelta(days=d)
            # skip weekends for most users (more realistic baseline)
            if day.weekday() >= 5 and random.random() > 0.15:
                continue

            n_events = random.randint(*EVENTS_PER_USER_PER_DAY)
            for _ in range(n_events):
                all_events.append(gen_normal_event(user, day))

    # Inject anomalies on top of the normal stream, as distinct "incidents".
    # Each incident = one anomaly_type occurrence for one user on one day.
    # Burst-style incidents (brute force / API spike) expand into several rows
    # but are kept small so they don't dominate the dataset.
    incident_weights = {
        "impossible_travel": 1.0,
        "off_hours_access": 1.0,
        "brute_force": 0.6,
        "privilege_escalation": 1.0,
        "data_exfiltration": 1.0,
        "new_device_new_geo": 1.0,
        "dormant_account_reactivation": 1.0,
        "api_rate_spike": 0.5,
    }
    types, weights = zip(*incident_weights.items())

    for _ in range(N_ANOMALY_INCIDENTS):
        user = random.choice(users)
        day = start_date + timedelta(days=random.randint(0, DAYS_OF_HISTORY - 1))
        anomaly_type = random.choices(types, weights=weights, k=1)[0]
        quiet = (anomaly_type not in ("brute_force", "api_rate_spike")
                 and random.random() < QUIET_ANOMALY_FRACTION)

        if anomaly_type == "brute_force":
            # bursts of 4-8 failed logins within a few minutes
            burst_size = random.randint(4, 8)
            base_ts = day.replace(hour=random.randint(0, 23), minute=random.randint(0, 40))
            for i in range(burst_size):
                ev = gen_anomaly_event(user, day, anomaly_type)
                ev["timestamp"] = (base_ts + timedelta(seconds=i * random.randint(5, 40))).isoformat()
                ev["source_ip"] = fake.ipv4_public()
                all_events.append(ev)
        elif anomaly_type == "api_rate_spike":
            burst_size = random.randint(10, 20)
            base_ts = day.replace(hour=random.randint(9, 18), minute=random.randint(0, 30))
            for i in range(burst_size):
                ev = gen_anomaly_event(user, day, anomaly_type)
                ev["timestamp"] = (base_ts + timedelta(seconds=i * random.randint(1, 5))).isoformat()
                all_events.append(ev)
        else:
            all_events.append(gen_anomaly_event(user, day, anomaly_type, quiet=quiet))

    # Multi-stage attack chains — connected narratives for a stronger demo story
    for _ in range(N_ATTACK_CHAINS):
        user = random.choice(users)
        day = start_date + timedelta(days=random.randint(2, DAYS_OF_HISTORY - 1))
        all_events.extend(gen_attack_chain(user, day))

    # Hard negatives — unusual-looking but legitimate, is_anomaly=0
    for _ in range(N_HARD_NEGATIVES):
        user = random.choice(users)
        day = start_date + timedelta(days=random.randint(0, DAYS_OF_HISTORY - 1))
        all_events.append(gen_hard_negative(user, day))

    df = pd.DataFrame(all_events)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df, users


# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import os
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    df, users = generate_dataset()

    csv_path = f"{OUTPUT_DIR}/cloud_access_logs.csv"
    json_path = f"{OUTPUT_DIR}/cloud_access_logs.json"
    users_path = f"{OUTPUT_DIR}/users.csv"

    df.to_csv(csv_path, index=False)
    df.to_json(json_path, orient="records", indent=2)
    pd.DataFrame(users).to_csv(users_path, index=False)

    print(f"Generated {len(df):,} events for {NUM_USERS} users over {DAYS_OF_HISTORY} days")
    print(f"  Anomalies: {df['is_anomaly'].sum():,} ({df['is_anomaly'].mean()*100:.1f}%)")
    print(f"  Anomaly type breakdown:")
    print(df[df.is_anomaly == 1]["anomaly_type"].value_counts().to_string())
    print(f"\n  Multi-stage attack chains: {df['incident_id'].replace('', pd.NA).dropna().nunique()}")
    print(f"  Quiet/subtle anomalies (risk_score<40 & is_anomaly=1): "
          f"{((df.is_anomaly==1) & (df.risk_score<40)).sum()}")
    print(f"  Hard negatives (benign_edge_case != none): {(df['benign_edge_case']!='none').sum()}")
    print(f"\nSaved to: {csv_path}, {json_path}, {users_path}")
