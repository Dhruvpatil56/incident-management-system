import { Link } from "react-router-dom";

import type { Incident } from "../types/incident";
import { SeverityBadge } from "./SeverityBadge";
import { StateBadge } from "./StateBadge";

export function IncidentCard({ incident }: { incident: Incident }) {
  return (
    <Link className={`card ${incident.severity === "P0" ? "pulse" : ""}`} to={`/incidents/${incident.id}`}>
      <div className="row">
        <h3>{incident.title}</h3>
        <SeverityBadge severity={incident.severity} />
      </div>
      <p>{incident.description}</p>
      <div className="row">
        <StateBadge state={incident.state} />
        <span>{incident.component}</span>
      </div>
    </Link>
  );
}
