"""Generate deterministic, demo-safe provider-native cloud audit fixtures.

The runtime provider files contain no anomaly labels, expected scores, or
normalization answers. Test-only expectations live in a separate oracle.

Usage:
    python datasets/cloud-ingestion/generate_raw_cloud_logs.py
    python datasets/cloud-ingestion/generate_raw_cloud_logs.py --check
    python datasets/cloud-ingestion/generate_raw_cloud_logs.py --output <dir>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


GENERATOR_VERSION = "cloud-ingestion-fixtures-v1"
SEED = 501
NORMALIZER_VERSION = "cloud-normalizer-v1"
MAPPING_VERSION = "identity-map-v1"

AWS_ACCOUNT = "111122223333"
AZURE_SUBSCRIPTION = "00000000-1111-2222-3333-444444444444"
GCP_PROJECT = "sentinel-demo-001"

AWS_AISHA = f"arn:aws:iam::{AWS_ACCOUNT}:user/aisha.rahman"
AWS_MARCO = f"arn:aws:iam::{AWS_ACCOUNT}:user/marco.silva"
AWS_SERVICE = f"arn:aws:iam::{AWS_ACCOUNT}:role/demo-deploy-role"
AZURE_AISHA = "aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa"
AZURE_MARCO = "bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb"
AZURE_SERVICE = "cccccccc-3333-4333-8333-cccccccccccc"
GCP_AISHA = "aisha.rahman@example.invalid"
GCP_MARCO = "marco.silva@example.invalid"
GCP_SERVICE = f"demo-deploy@{GCP_PROJECT}.iam.gserviceaccount.com"


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def pretty_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def jsonl(values: list[dict[str, Any]]) -> bytes:
    return ("\n".join(json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True) for value in values) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def raw_event_id(provider: str, source_account_id: str, native_event_id: str | None, record: dict[str, Any]) -> str:
    record_digest = sha256_bytes(canonical_json(record))
    identity = native_event_id if native_event_id else f"sha256:{record_digest}"
    raw_key = f"{provider}\n{source_account_id}\n{identity}".encode("utf-8")
    return f"raw-{sha256_bytes(raw_key)[:32]}"


def source(ip: str | None) -> dict[str, Any]:
    return {"ip": ip, "country": None, "region": None, "city": None, "asn": None}


def normalized(
    *,
    event_id: str,
    identity_id: str,
    event_time: str,
    ip: str | None,
    service: str,
    action: str,
    resource_type: str | None,
    resource_id: str | None,
    outcome: str,
    session_id: str | None,
) -> dict[str, Any]:
    return {
        "eventId": event_id,
        "identityId": identity_id,
        "eventTimeUtc": event_time,
        "source": source(ip),
        "service": service,
        "action": action,
        "resource": {"type": resource_type, "id": resource_id},
        "outcome": outcome,
        "sessionId": session_id,
    }


def aws_event(
    native_id: str,
    event_time: str,
    principal_arn: str,
    ip: str | None,
    service: str,
    action: str,
    resource_type: str | None,
    resource_id: str | None,
    session_id: str | None,
    *,
    error_code: str | None = None,
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "eventVersion": "1.09",
        "userIdentity": {
            "type": "AssumedRole" if ":role/" in principal_arn else "IAMUser",
            "principalId": principal_arn.rsplit("/", 1)[-1],
            "arn": principal_arn,
            "accountId": AWS_ACCOUNT,
        },
        "eventTime": event_time,
        "eventSource": service,
        "eventName": action,
        "awsRegion": "ap-southeast-1",
        "sourceIPAddress": ip,
        "userAgent": "sentinel-demo-client/1.0",
        "requestParameters": {"demo": True},
        "responseElements": None if error_code else {"status": "ok"},
        "requestID": session_id,
        "eventID": native_id,
        "readOnly": action.startswith(("Get", "List", "Describe")),
        "resources": [] if resource_id is None else [{"type": resource_type, "ARN": resource_id}],
        "eventType": "AwsApiCall",
        "managementEvent": True,
        "recipientAccountId": AWS_ACCOUNT,
    }
    if error_code:
        event["errorCode"] = error_code
        event["errorMessage"] = "Synthetic access denied"
    return event


def azure_event(
    native_id: str,
    event_time: str,
    principal_id: str,
    principal_name: str,
    ip: str | None,
    provider_name: str,
    action: str,
    resource_type: str | None,
    resource_id: str | None,
    correlation_id: str | None,
    *,
    status: str = "Succeeded",
) -> dict[str, Any]:
    claims: dict[str, Any] = {
        "http://schemas.microsoft.com/identity/claims/objectidentifier": principal_id,
        "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name": principal_name,
    }
    if ip is not None:
        claims["ipaddr"] = ip
    return {
        "authorization": {"action": action, "scope": resource_id},
        "caller": principal_name,
        "claims": claims,
        "correlationId": correlation_id,
        "eventDataId": native_id,
        "eventName": {"value": "EndRequest", "localizedValue": "End request"},
        "category": {"value": "Administrative", "localizedValue": "Administrative"},
        "eventTimestamp": event_time,
        "id": f"/subscriptions/{AZURE_SUBSCRIPTION}/events/{native_id}",
        "level": "Informational" if status == "Succeeded" else "Error",
        "operationId": correlation_id,
        "operationName": {"value": action, "localizedValue": action},
        "resourceGroupName": "demo-security-rg",
        "resourceProviderName": {"value": provider_name, "localizedValue": provider_name},
        "resourceType": None if resource_type is None else {"value": resource_type, "localizedValue": resource_type},
        "resourceId": resource_id,
        "status": {"value": status, "localizedValue": status},
        "subStatus": {"value": "OK" if status == "Succeeded" else "Forbidden", "localizedValue": status},
        "subscriptionId": AZURE_SUBSCRIPTION,
        "tenantId": "dddddddd-4444-4444-8444-dddddddddddd",
        "properties": {"demo": True},
    }


def gcp_event(
    native_id: str,
    event_time: str,
    principal_email: str,
    ip: str | None,
    service: str,
    action: str,
    resource_type: str | None,
    resource_id: str | None,
    operation_id: str | None,
    *,
    status_code: int = 0,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "@type": "type.googleapis.com/google.cloud.audit.AuditLog",
        "authenticationInfo": {"principalEmail": principal_email},
        "requestMetadata": {"callerSuppliedUserAgent": "sentinel-demo-client/1.0"},
        "serviceName": service,
        "methodName": action,
        "resourceName": resource_id,
        "status": {} if status_code == 0 else {"code": status_code, "message": "Synthetic permission denied"},
    }
    if ip is not None:
        payload["requestMetadata"]["callerIp"] = ip
    event: dict[str, Any] = {
        "insertId": native_id,
        "logName": f"projects/{GCP_PROJECT}/logs/cloudaudit.googleapis.com%2Factivity",
        "protoPayload": payload,
        "receiveTimestamp": "2026-08-18T06:00:00Z",
        "resource": {"type": resource_type, "labels": {"project_id": GCP_PROJECT}},
        "severity": "NOTICE" if status_code == 0 else "ERROR",
        "timestamp": event_time,
    }
    if operation_id is not None:
        event["operation"] = {"id": operation_id, "producer": service, "first": True, "last": True}
    return event


def build_bindings() -> dict[str, Any]:
    rows = [
        ("aws_cloudtrail", AWS_ACCOUNT, AWS_AISHA, "id-aisha-rahman"),
        ("aws_cloudtrail", AWS_ACCOUNT, AWS_MARCO, "id-marco-silva"),
        ("aws_cloudtrail", AWS_ACCOUNT, AWS_SERVICE, "id-svc-deploy"),
        ("azure_activity_log", AZURE_SUBSCRIPTION, AZURE_AISHA, "id-aisha-rahman"),
        ("azure_activity_log", AZURE_SUBSCRIPTION, AZURE_MARCO, "id-marco-silva"),
        ("azure_activity_log", AZURE_SUBSCRIPTION, AZURE_SERVICE, "id-svc-deploy"),
        ("gcp_audit_log", GCP_PROJECT, GCP_AISHA, "id-aisha-rahman"),
        ("gcp_audit_log", GCP_PROJECT, GCP_MARCO, "id-marco-silva"),
        ("gcp_audit_log", GCP_PROJECT, GCP_SERVICE, "id-svc-deploy"),
    ]
    return {
        "mappingVersion": MAPPING_VERSION,
        "bindings": [
            {"provider": provider, "sourceAccountId": account, "principalKey": principal, "identityId": identity}
            for provider, account, principal, identity in rows
        ],
    }


def build_aws() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    role_arn = f"arn:aws:iam::{AWS_ACCOUNT}:role/demo-ops-role"
    object_arn = "arn:aws:s3:::sentinel-demo-bucket/reports/summary.csv"
    secret_arn = f"arn:aws:secretsmanager:ap-southeast-1:{AWS_ACCOUNT}:secret:demo/database"
    trail_arn = f"arn:aws:cloudtrail:ap-southeast-1:{AWS_ACCOUNT}:trail/demo-audit"
    events = [
        aws_event("aws-evt-0001", "2026-08-18T01:15:00Z", AWS_AISHA, "198.51.100.10", "signin.amazonaws.com", "ConsoleLogin", None, None, "aws-session-001"),
        aws_event("aws-evt-0002", "2026-08-18T01:20:00Z", AWS_MARCO, "198.51.100.11", "s3.amazonaws.com", "GetObject", "AWS::S3::Object", object_arn, "aws-session-002"),
        aws_event("aws-evt-0003", "2026-08-18T01:30:00Z", AWS_AISHA, "203.0.113.20", "iam.amazonaws.com", "AttachRolePolicy", "AWS::IAM::Role", role_arn, "aws-session-003"),
        aws_event("aws-evt-0004", "2026-08-18T01:35:00Z", AWS_SERVICE, "192.0.2.44", "secretsmanager.amazonaws.com", "GetSecretValue", "AWS::SecretsManager::Secret", secret_arn, "aws-session-004", error_code="AccessDenied"),
        aws_event("aws-evt-0005", "2026-08-18T01:40:00Z", AWS_AISHA, "203.0.113.20", "cloudtrail.amazonaws.com", "StopLogging", "AWS::CloudTrail::Trail", trail_arn, "aws-session-005"),
        aws_event("aws-evt-0006", "2026-08-18T01:45:00Z", AWS_MARCO, None, "iam.amazonaws.com", "ListRoles", None, None, None),
    ]
    events.append(dict(events[1]))
    events.append(aws_event("aws-evt-0007", "2026-08-18T01:50:00Z", f"arn:aws:iam::{AWS_ACCOUNT}:user/unmapped.user", "192.0.2.55", "ec2.amazonaws.com", "DescribeInstances", "AWS::EC2::Instance", f"arn:aws:ec2:ap-southeast-1:{AWS_ACCOUNT}:instance/i-demo0001", "aws-session-007"))
    events.append(aws_event("aws-evt-0008", "not-a-timestamp", AWS_AISHA, "198.51.100.10", "iam.amazonaws.com", "ListUsers", None, None, "aws-session-008"))

    expected = [
        normalized(event_id=f"aws:{AWS_ACCOUNT}:aws-evt-0001", identity_id="id-aisha-rahman", event_time="2026-08-18T01:15:00Z", ip="198.51.100.10", service="signin.amazonaws.com", action="ConsoleLogin", resource_type=None, resource_id=None, outcome="success", session_id="aws-session-001"),
        normalized(event_id=f"aws:{AWS_ACCOUNT}:aws-evt-0002", identity_id="id-marco-silva", event_time="2026-08-18T01:20:00Z", ip="198.51.100.11", service="s3.amazonaws.com", action="GetObject", resource_type="AWS::S3::Object", resource_id=object_arn, outcome="success", session_id="aws-session-002"),
        normalized(event_id=f"aws:{AWS_ACCOUNT}:aws-evt-0003", identity_id="id-aisha-rahman", event_time="2026-08-18T01:30:00Z", ip="203.0.113.20", service="iam.amazonaws.com", action="AttachRolePolicy", resource_type="AWS::IAM::Role", resource_id=role_arn, outcome="success", session_id="aws-session-003"),
        normalized(event_id=f"aws:{AWS_ACCOUNT}:aws-evt-0004", identity_id="id-svc-deploy", event_time="2026-08-18T01:35:00Z", ip="192.0.2.44", service="secretsmanager.amazonaws.com", action="GetSecretValue", resource_type="AWS::SecretsManager::Secret", resource_id=secret_arn, outcome="denied", session_id="aws-session-004"),
        normalized(event_id=f"aws:{AWS_ACCOUNT}:aws-evt-0005", identity_id="id-aisha-rahman", event_time="2026-08-18T01:40:00Z", ip="203.0.113.20", service="cloudtrail.amazonaws.com", action="StopLogging", resource_type="AWS::CloudTrail::Trail", resource_id=trail_arn, outcome="success", session_id="aws-session-005"),
        normalized(event_id=f"aws:{AWS_ACCOUNT}:aws-evt-0006", identity_id="id-marco-silva", event_time="2026-08-18T01:45:00Z", ip=None, service="iam.amazonaws.com", action="ListRoles", resource_type=None, resource_id=None, outcome="success", session_id=None),
    ]
    return events, expected


def build_azure() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    vm_id = f"/subscriptions/{AZURE_SUBSCRIPTION}/resourceGroups/demo-security-rg/providers/Microsoft.Compute/virtualMachines/demo-vm"
    role_id = f"/subscriptions/{AZURE_SUBSCRIPTION}/providers/Microsoft.Authorization/roleAssignments/demo-role-assignment"
    storage_id = f"/subscriptions/{AZURE_SUBSCRIPTION}/resourceGroups/demo-security-rg/providers/Microsoft.Storage/storageAccounts/demostorage"
    diagnostic_id = f"/subscriptions/{AZURE_SUBSCRIPTION}/providers/Microsoft.Insights/diagnosticSettings/demo-audit"
    events = [
        azure_event("azure-evt-0001", "2026-08-18T02:10:00Z", AZURE_AISHA, "aisha.rahman@example.invalid", "198.51.100.20", "Microsoft.Compute", "Microsoft.Compute/virtualMachines/read", "Microsoft.Compute/virtualMachines", vm_id, "azure-corr-001"),
        azure_event("azure-evt-0002", "2026-08-18T02:20:00Z", AZURE_AISHA, "aisha.rahman@example.invalid", "203.0.113.30", "Microsoft.Authorization", "Microsoft.Authorization/roleAssignments/write", "Microsoft.Authorization/roleAssignments", role_id, "azure-corr-002"),
        azure_event("azure-evt-0003", "2026-08-18T02:25:00Z", AZURE_SERVICE, "demo-deploy@example.invalid", "192.0.2.60", "Microsoft.Storage", "Microsoft.Storage/storageAccounts/listKeys/action", "Microsoft.Storage/storageAccounts", storage_id, "azure-corr-003"),
        azure_event("azure-evt-0004", "2026-08-18T02:30:00Z", AZURE_AISHA, "aisha.rahman@example.invalid", "203.0.113.30", "Microsoft.Insights", "Microsoft.Insights/diagnosticSettings/delete", "Microsoft.Insights/diagnosticSettings", diagnostic_id, "azure-corr-004"),
        azure_event("azure-evt-0005", "2026-08-18T02:35:00Z", AZURE_MARCO, "marco.silva@example.invalid", None, "Microsoft.Compute", "Microsoft.Compute/virtualMachines/start/action", "Microsoft.Compute/virtualMachines", vm_id, None),
    ]
    events.append(dict(events[0]))
    events.append(azure_event("azure-evt-0006", "2026-08-18T02:40:00Z", "eeeeeeee-5555-4555-8555-eeeeeeeeeeee", "unmapped.user@example.invalid", "192.0.2.61", "Microsoft.Compute", "Microsoft.Compute/virtualMachines/read", "Microsoft.Compute/virtualMachines", vm_id, "azure-corr-006"))
    invalid = azure_event("azure-evt-0007", "2026-08-18T02:45:00Z", AZURE_AISHA, "aisha.rahman@example.invalid", "198.51.100.20", "Microsoft.Compute", "Microsoft.Compute/virtualMachines/read", "Microsoft.Compute/virtualMachines", vm_id, "azure-corr-007")
    invalid.pop("operationName")
    events.append(invalid)

    expected = [
        normalized(event_id=f"azure:{AZURE_SUBSCRIPTION}:azure-evt-0001", identity_id="id-aisha-rahman", event_time="2026-08-18T02:10:00Z", ip="198.51.100.20", service="Microsoft.Compute", action="Microsoft.Compute/virtualMachines/read", resource_type="Microsoft.Compute/virtualMachines", resource_id=vm_id, outcome="success", session_id="azure-corr-001"),
        normalized(event_id=f"azure:{AZURE_SUBSCRIPTION}:azure-evt-0002", identity_id="id-aisha-rahman", event_time="2026-08-18T02:20:00Z", ip="203.0.113.30", service="Microsoft.Authorization", action="Microsoft.Authorization/roleAssignments/write", resource_type="Microsoft.Authorization/roleAssignments", resource_id=role_id, outcome="success", session_id="azure-corr-002"),
        normalized(event_id=f"azure:{AZURE_SUBSCRIPTION}:azure-evt-0003", identity_id="id-svc-deploy", event_time="2026-08-18T02:25:00Z", ip="192.0.2.60", service="Microsoft.Storage", action="Microsoft.Storage/storageAccounts/listKeys/action", resource_type="Microsoft.Storage/storageAccounts", resource_id=storage_id, outcome="success", session_id="azure-corr-003"),
        normalized(event_id=f"azure:{AZURE_SUBSCRIPTION}:azure-evt-0004", identity_id="id-aisha-rahman", event_time="2026-08-18T02:30:00Z", ip="203.0.113.30", service="Microsoft.Insights", action="Microsoft.Insights/diagnosticSettings/delete", resource_type="Microsoft.Insights/diagnosticSettings", resource_id=diagnostic_id, outcome="success", session_id="azure-corr-004"),
        normalized(event_id=f"azure:{AZURE_SUBSCRIPTION}:azure-evt-0005", identity_id="id-marco-silva", event_time="2026-08-18T02:35:00Z", ip=None, service="Microsoft.Compute", action="Microsoft.Compute/virtualMachines/start/action", resource_type="Microsoft.Compute/virtualMachines", resource_id=vm_id, outcome="success", session_id=None),
    ]
    return events, expected


def build_gcp() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    object_id = f"projects/_/buckets/sentinel-demo-bucket/objects/reports/summary.csv"
    project_id = f"projects/{GCP_PROJECT}"
    key_id = f"projects/{GCP_PROJECT}/serviceAccounts/{GCP_SERVICE}/keys/demo-key-metadata"
    sink_id = f"projects/{GCP_PROJECT}/sinks/demo-audit-sink"
    instance_id = f"projects/{GCP_PROJECT}/zones/asia-southeast1-a/instances/demo-vm"
    events = [
        gcp_event("gcp-evt-0001", "2026-08-18T03:05:00Z", GCP_MARCO, "198.51.100.30", "storage.googleapis.com", "storage.objects.get", "gcs_bucket", object_id, "gcp-op-001"),
        gcp_event("gcp-evt-0002", "2026-08-18T03:15:00Z", GCP_AISHA, "203.0.113.40", "cloudresourcemanager.googleapis.com", "SetIamPolicy", "project", project_id, "gcp-op-002"),
        gcp_event("gcp-evt-0003", "2026-08-18T03:20:00Z", GCP_SERVICE, "192.0.2.70", "iam.googleapis.com", "google.iam.admin.v1.CreateServiceAccountKey", "service_account", key_id, "gcp-op-003"),
        gcp_event("gcp-evt-0004", "2026-08-18T03:25:00Z", GCP_AISHA, "203.0.113.40", "logging.googleapis.com", "google.logging.v2.ConfigServiceV2.DeleteSink", "logging_sink", sink_id, "gcp-op-004"),
        gcp_event("gcp-evt-0005", "2026-08-18T03:30:00Z", GCP_MARCO, None, "compute.googleapis.com", "v1.compute.instances.start", "gce_instance", instance_id, None),
        gcp_event("gcp-evt-0006", "2026-08-18T03:35:00Z", GCP_SERVICE, "192.0.2.70", "secretmanager.googleapis.com", "google.cloud.secretmanager.v1.SecretManagerService.AccessSecretVersion", "secretmanager_secret", f"projects/{GCP_PROJECT}/secrets/demo-database", "gcp-op-006", status_code=7),
    ]
    events.append(dict(events[0]))
    events.append(gcp_event("gcp-evt-0007", "2026-08-18T03:40:00Z", "unmapped.user@example.invalid", "192.0.2.71", "compute.googleapis.com", "v1.compute.instances.get", "gce_instance", instance_id, "gcp-op-007"))
    events.append(gcp_event("gcp-evt-0008", "18-08-2026 03:45", GCP_AISHA, "198.51.100.31", "compute.googleapis.com", "v1.compute.instances.get", "gce_instance", instance_id, "gcp-op-008"))

    expected = [
        normalized(event_id=f"gcp:{GCP_PROJECT}:gcp-evt-0001", identity_id="id-marco-silva", event_time="2026-08-18T03:05:00Z", ip="198.51.100.30", service="storage.googleapis.com", action="storage.objects.get", resource_type="gcs_bucket", resource_id=object_id, outcome="success", session_id="gcp-op-001"),
        normalized(event_id=f"gcp:{GCP_PROJECT}:gcp-evt-0002", identity_id="id-aisha-rahman", event_time="2026-08-18T03:15:00Z", ip="203.0.113.40", service="cloudresourcemanager.googleapis.com", action="SetIamPolicy", resource_type="project", resource_id=project_id, outcome="success", session_id="gcp-op-002"),
        normalized(event_id=f"gcp:{GCP_PROJECT}:gcp-evt-0003", identity_id="id-svc-deploy", event_time="2026-08-18T03:20:00Z", ip="192.0.2.70", service="iam.googleapis.com", action="google.iam.admin.v1.CreateServiceAccountKey", resource_type="service_account", resource_id=key_id, outcome="success", session_id="gcp-op-003"),
        normalized(event_id=f"gcp:{GCP_PROJECT}:gcp-evt-0004", identity_id="id-aisha-rahman", event_time="2026-08-18T03:25:00Z", ip="203.0.113.40", service="logging.googleapis.com", action="google.logging.v2.ConfigServiceV2.DeleteSink", resource_type="logging_sink", resource_id=sink_id, outcome="success", session_id="gcp-op-004"),
        normalized(event_id=f"gcp:{GCP_PROJECT}:gcp-evt-0005", identity_id="id-marco-silva", event_time="2026-08-18T03:30:00Z", ip=None, service="compute.googleapis.com", action="v1.compute.instances.start", resource_type="gce_instance", resource_id=instance_id, outcome="success", session_id=None),
        normalized(event_id=f"gcp:{GCP_PROJECT}:gcp-evt-0006", identity_id="id-svc-deploy", event_time="2026-08-18T03:35:00Z", ip="192.0.2.70", service="secretmanager.googleapis.com", action="google.cloud.secretmanager.v1.SecretManagerService.AccessSecretVersion", resource_type="secretmanager_secret", resource_id=f"projects/{GCP_PROJECT}/secrets/demo-database", outcome="denied", session_id="gcp-op-006"),
    ]
    return events, expected


def oracle_rows(
    provider: str,
    source_account_id: str,
    events: list[dict[str, Any]],
    successes: list[dict[str, Any]],
    native_key: str,
    scenarios: list[str],
) -> list[dict[str, Any]]:
    success_by_native = {item["eventId"].rsplit(":", 1)[-1]: item for item in successes}
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for index, event in enumerate(events):
        native_id = event.get(native_key)
        raw_id = raw_event_id(provider, source_account_id, native_id, event)
        row: dict[str, Any] = {
            "provider": provider,
            "sourceAccountId": source_account_id,
            "recordIndex": index,
            "nativeEventId": native_id,
            "rawEventId": raw_id,
            "scenario": scenarios[index],
            "normalizerVersion": NORMALIZER_VERSION,
            "mappingVersion": MAPPING_VERSION,
        }
        if raw_id in seen:
            row.update({"expectedStatus": "duplicate", "reasonCode": None, "normalizedEvent": None})
        elif native_id in success_by_native:
            row.update({"expectedStatus": "normalized", "reasonCode": None, "normalizedEvent": success_by_native[native_id]})
        elif "unresolved" in scenarios[index]:
            row.update({"expectedStatus": "quarantined", "reasonCode": "unresolved_identity", "normalizedEvent": None})
        elif "timestamp" in scenarios[index]:
            row.update({"expectedStatus": "quarantined", "reasonCode": "invalid_event_time", "normalizedEvent": None})
        else:
            row.update({"expectedStatus": "quarantined", "reasonCode": "missing_native_fields", "normalizedEvent": None})
        seen.add(raw_id)
        rows.append(row)
    return rows


def validate_runtime_files(aws: list[dict[str, Any]], azure: list[dict[str, Any]], gcp: list[dict[str, Any]]) -> None:
    forbidden_keys = {"is_anomaly", "anomaly_type", "risk_score", "expectedScore", "scenario", "scenarioLabel"}
    allowed_prefixes = ("192.0.2.", "198.51.100.", "203.0.113.")

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            assert not (forbidden_keys & value.keys()), f"Runtime fixture contains forbidden keys: {forbidden_keys & value.keys()}"
            for key, item in value.items():
                if key in {"sourceIPAddress", "ipaddr", "callerIp"} and item is not None:
                    assert str(item).startswith(allowed_prefixes), f"Non-documentation IP found: {item}"
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(aws)
    walk(azure)
    walk(gcp)


def render_files() -> dict[str, bytes]:
    aws, aws_expected = build_aws()
    azure, azure_expected = build_azure()
    gcp, gcp_expected = build_gcp()
    validate_runtime_files(aws, azure, gcp)

    oracle = []
    oracle.extend(oracle_rows(
        "aws_cloudtrail", AWS_ACCOUNT, aws, aws_expected, "eventID",
        ["normal_login", "read_object", "permission_change", "denied_secret_access", "disable_logging", "missing_optional_source", "duplicate_record", "unresolved_identity", "invalid_timestamp"],
    ))
    oracle.extend(oracle_rows(
        "azure_activity_log", AZURE_SUBSCRIPTION, azure, azure_expected, "eventDataId",
        ["read_resource", "permission_change", "credential_key_access", "remove_logging_protection", "missing_optional_source", "duplicate_record", "unresolved_identity", "missing_operation"],
    ))
    oracle.extend(oracle_rows(
        "gcp_audit_log", GCP_PROJECT, gcp, gcp_expected, "insertId",
        ["read_object", "permission_change", "credential_key_change", "remove_logging_protection", "missing_optional_source", "denied_secret_access", "duplicate_record", "unresolved_identity", "invalid_timestamp"],
    ))

    files = {
        "aws-cloudtrail.json": pretty_json({"Records": aws}),
        "azure-activity-log.json": pretty_json({"records": azure}),
        "gcp-audit-log.jsonl": jsonl(gcp),
        "identity-bindings.json": pretty_json(build_bindings()),
        "expected-normalized-events.jsonl": jsonl(oracle),
    }
    counts: dict[str, Any] = {}
    for provider, records in (
        ("aws_cloudtrail", [row for row in oracle if row["provider"] == "aws_cloudtrail"]),
        ("azure_activity_log", [row for row in oracle if row["provider"] == "azure_activity_log"]),
        ("gcp_audit_log", [row for row in oracle if row["provider"] == "gcp_audit_log"]),
    ):
        counts[provider] = {
            "records": len(records),
            "normalized": sum(row["expectedStatus"] == "normalized" for row in records),
            "duplicates": sum(row["expectedStatus"] == "duplicate" for row in records),
            "quarantined": sum(row["expectedStatus"] == "quarantined" for row in records),
        }
    manifest = {
        "generatorVersion": GENERATOR_VERSION,
        "seed": SEED,
        "anchorDate": "2026-08-18",
        "normalizerVersion": NORMALIZER_VERSION,
        "mappingVersion": MAPPING_VERSION,
        "providers": counts,
        "identityBindingCount": len(build_bindings()["bindings"]),
        "oracleRecordCount": len(oracle),
        "fileDigests": {name: sha256_bytes(content) for name, content in sorted(files.items())},
    }
    files["manifest.json"] = pretty_json(manifest)
    return files


def check_files(output_dir: Path, rendered: dict[str, bytes]) -> int:
    failures: list[str] = []
    for name, expected in sorted(rendered.items()):
        path = output_dir / name
        if not path.exists():
            failures.append(f"missing: {path}")
            continue
        actual = path.read_bytes()
        if actual != expected:
            failures.append(f"different: {path}")
    if failures:
        print("Synthetic cloud-ingestion fixture check failed:", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1
    print(f"Verified {len(rendered)} deterministic fixture files in {output_dir}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--check", action="store_true", help="Verify checked-in files without rewriting them")
    args = parser.parse_args()

    rendered = render_files()
    if args.check:
        return check_files(args.output, rendered)

    args.output.mkdir(parents=True, exist_ok=True)
    for name, content in rendered.items():
        (args.output / name).write_bytes(content)
    manifest = json.loads(rendered["manifest.json"])
    print(f"Generated {manifest['oracleRecordCount']} raw record expectations across 3 providers")
    for provider, counts in manifest["providers"].items():
        print(f"  {provider}: {counts}")
    print(f"Saved {len(rendered)} fixture files to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
