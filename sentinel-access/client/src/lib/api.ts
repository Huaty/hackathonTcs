import axios from "axios";

export const api = axios.create({
  baseURL: "/api",
});

export type FindingExplanation = { findingId: string; explanation: string; source: "ai" | "fallback" };

export function getFindingExplanation(findingId: string) {
  return api.get<FindingExplanation>(`/findings/${findingId}/explanation`);
}

export type CopilotResponse = {
  answer: string;
  findings: Record<string, unknown>[];
  activity: Record<string, unknown>[];
  identities: Record<string, unknown>[];
};

export function queryCopilot(question: string) {
  return api.post<CopilotResponse>("/copilot/query", { question });
}

export type IdentityRiskSummary = {
  latestPolicyScore: number | null;
  latestAiAdjustment: number | null;
  latestAiStatus: "applied" | "zero" | "low_confidence" | "invalid" | "unavailable" | null;
  latestSeverityFloor: "High" | "Critical" | null;
  latestFinalRiskScore: number | null;
  matchedPolicyIds: string[];
};

export type IdentityBaselineSummary = {
  baselineId: string;
  windowStartUtc: string;
  windowEndUtc: string;
  usualHours: { start: string; end: string }[];
  usualSourceIps: string[];
  usualLocations: string[];
  usualServices: string[];
  usualActions: string[];
  sampleCount: number;
  activeDayCount: number;
  confidence: "low" | "high";
  unknownFields: string[];
};

export type ProfileEvent = {
  eventId: string;
  timestampUtc: string;
  cloudService: string;
  action: string;
  [key: string]: unknown;
};

export type IdentityProfileResponse = {
  identity: {
    identityId: string;
    name: string;
    identityType: "human" | "service" | "workload";
    role: string;
    status: string;
    homeTimezone: string;
  };
  baseline: IdentityBaselineSummary | null;
  events: ProfileEvent[];
  assessments: Record<string, unknown>[];
  riskSummary: IdentityRiskSummary;
};

export function getIdentityProfile(identityId: string) {
  return api.get<IdentityProfileResponse>(`/identities/${encodeURIComponent(identityId)}`);
}

export type RiskAssessmentResponse = {
  assessmentId: string;
  eventId: string;
  calculation: {
    policyScore: number;
    aiAdjustmentApplied: number;
    preFloorScore: number;
    severityFloorMinimum: number;
    finalRiskScore: number;
  };
  severity: "Low" | "Medium" | "High" | "Critical";
  aiContext: { status: string };
};

export function runRiskAssessment(eventId: string, forceAiRefresh = false) {
  return api.post<RiskAssessmentResponse>("/risk-assessments", { eventId, forceAiRefresh });
}

export function simulateIdentityEvent(identityId: string) {
  return api.post<ProfileEvent>(`/identities/${encodeURIComponent(identityId)}/simulated-events`);
}
