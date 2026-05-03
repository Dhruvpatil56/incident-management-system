import { useQuery } from "@tanstack/react-query";

import { fetchIncidents } from "../api/client";
import { IncidentCard } from "../components/IncidentCard";

const rank = { P0: 0, P1: 1, P2: 2, P3: 3 };

export function Dashboard() {
  const { data = [] } = useQuery({
    queryKey: ["incidents"],
    queryFn: fetchIncidents,
    refetchInterval: 5000,
  });

  const ordered = [...data].sort(
    (a, b) => rank[a.severity] - rank[b.severity]
  );

  return (
    <main>
      <h1>Incident Dashboard</h1>
      <div className="grid">
        {ordered.map((incident) => (
          <IncidentCard key={incident.id} incident={incident} />
        ))}
      </div>
    </main>
  );
}
