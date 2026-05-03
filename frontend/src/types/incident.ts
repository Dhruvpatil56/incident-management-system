export type IncidentState = "OPEN" | "INVESTIGATING" | "RESOLVED" | "CLOSED";
export type Severity = "P0" | "P1" | "P2" | "P3";
export type RcaCategory =
  | "code_deploy"
  | "resource_exhaustion"
  | "external_outage"
  | "config_change"
  | "dependency_failure"
  | "human_error"
  | "security_incident"
  | "unknown";

export interface RcaSubmitPayload {
  root_cause: string;
  rca_category: RcaCategory;
  incident_start_at: string;
  incident_end_at: string;
  fix_applied: string;
  prevention_steps: string;
  rca_verified_by?: string;
}

export interface Incident {
  id: string;
  title: string;
  description: string;
  source: string;
  root_cause: string;
  rca_description: string;
  rca_verified_by?: string | null;
  state: IncidentState;
  severity: Severity;
  component: string;
  mttr_seconds?: number | null;
  created_at: string;
}
