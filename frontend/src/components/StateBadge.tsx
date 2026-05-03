import type { IncidentState } from "../types/incident";

export function StateBadge({ state }: { state: IncidentState }) {
  return <span className="badge state">{state}</span>;
}
