export function SignalTable({ signals }: { signals: Array<{ component_id: string; severity: string; created_at: string }> }) {
  return (
    <table>
      <thead>
        <tr>
          <th>Component</th>
          <th>Severity</th>
          <th>Created</th>
        </tr>
      </thead>
      <tbody>
        {signals.map((signal, idx) => (
          <tr key={idx}>
            <td>{signal.component_id}</td>
            <td>{signal.severity}</td>
            <td>{signal.created_at}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
