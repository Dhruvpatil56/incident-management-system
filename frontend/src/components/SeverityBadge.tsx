import type { Severity } from "../types/incident";

export function SeverityBadge({ severity }: { severity: Severity }) {
  return <span className={`badge ${severity.toLowerCase()}`}>{severity}</span>;
}
