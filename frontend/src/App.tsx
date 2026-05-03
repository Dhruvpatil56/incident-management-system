import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";

import { Dashboard } from "./pages/Dashboard";
import { IncidentDetail } from "./pages/IncidentDetail";

const client = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={client}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/incidents/:id" element={<IncidentDetail />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
