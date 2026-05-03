import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { fetchIncident, submitRca } from "../api/client";
import { RcaForm } from "../components/RcaForm";
import { SignalTable } from "../components/SignalTable";

export function IncidentDetail() {
  const { id = "" } = useParams();
  const { data, refetch } = useQuery({
    queryKey: ["incident", id],
    queryFn: () => fetchIncident(id),
  });

  if (!data) return <main>Loading...</main>;

  return (
    <main>
      <h1>{data.title}</h1>
      <p>{data.description}</p>
      <p>MTTR: {data.mttr_seconds ?? "Not available"}</p>
      <RcaForm
        onSubmit={async (payload) => {
          await submitRca(id, payload);
          await refetch();
        }}
      />
      <SignalTable signals={(data as any).signals ?? []} />
    </main>
  );
}
