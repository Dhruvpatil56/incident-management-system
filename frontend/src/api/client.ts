import axios from "axios";

import type { Incident, IncidentState, RcaSubmitPayload } from "../types/incident";

const http = axios.create({ baseURL: "http://localhost:8000" });

export async function fetchIncidents(): Promise<Incident[]> {
  const { data } = await http.get<Incident[]>("/api/v1/incidents");
  return data;
}

export async function fetchIncident(id: string): Promise<Incident> {
  const { data } = await http.get<Incident>(`/api/v1/incidents/${id}?include_signals=true`);
  return data;
}

export async function submitRca(id: string, payload: RcaSubmitPayload) {
  return http.post(`/api/v1/incidents/${id}/rca`, payload);
}

export async function transitionState(id: string, state: IncidentState) {
  return http.patch(`/api/v1/incidents/${id}/state`, { state });
}
