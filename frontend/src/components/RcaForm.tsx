import { useState } from "react";
import type { RcaCategory, RcaSubmitPayload } from "../types/incident";

export function RcaForm({ onSubmit }: { onSubmit: (v: RcaSubmitPayload) => Promise<void> }) {
  const [rootCause, setRootCause] = useState("");
  const [category, setCategory] = useState<RcaCategory>("unknown");
  const [startAt, setStartAt] = useState("");
  const [endAt, setEndAt] = useState("");
  const [fixApplied, setFixApplied] = useState("");
  const [preventionSteps, setPreventionSteps] = useState("");
  const [verifiedBy, setVerifiedBy] = useState("");

  return (
    <form
      onSubmit={async (e) => {
        e.preventDefault();
        await onSubmit({
          root_cause: rootCause,
          rca_category: category,
          incident_start_at: new Date(startAt).toISOString(),
          incident_end_at: new Date(endAt).toISOString(),
          fix_applied: fixApplied,
          prevention_steps: preventionSteps,
          rca_verified_by: verifiedBy,
        });
      }}
    >
      <input value={rootCause} onChange={(e) => setRootCause(e.target.value)} placeholder="Root cause" />
      <select value={category} onChange={(e) => setCategory(e.target.value as RcaCategory)}>
        <option value="code_deploy">Code Bug</option>
        <option value="resource_exhaustion">Infrastructure</option>
        <option value="external_outage">Third-Party</option>
        <option value="config_change">Configuration</option>
        <option value="dependency_failure">Dependency Failure</option>
        <option value="human_error">Human Error</option>
        <option value="security_incident">Security Incident</option>
        <option value="unknown">Unknown</option>
      </select>
      <input type="datetime-local" aria-label="Incident Start" value={startAt} onChange={(e) => setStartAt(e.target.value)} />
      <input type="datetime-local" aria-label="Incident End" value={endAt} onChange={(e) => setEndAt(e.target.value)} />
      <textarea value={fixApplied} onChange={(e) => setFixApplied(e.target.value)} placeholder="Fix applied" />
      <textarea value={preventionSteps} onChange={(e) => setPreventionSteps(e.target.value)} placeholder="Prevention steps" />
      <input value={verifiedBy} onChange={(e) => setVerifiedBy(e.target.value)} placeholder="Verified by" />
      <button type="submit">Submit RCA</button>
    </form>
  );
}
