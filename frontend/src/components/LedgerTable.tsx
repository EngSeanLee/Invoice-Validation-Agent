import { useEffect, useState } from "react";
import { fetchLedger } from "../api/client";
import type { LedgerRecord } from "../types";
import FlaggedItemDetail from "./FlaggedItemDetail";
import StatusBadge from "./StatusBadge";

export default function LedgerTable({ refreshKey }: { refreshKey: number }) {
  const [records, setRecords] = useState<LedgerRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<LedgerRecord | null>(null);

  async function load() {
    setIsLoading(true);
    setError(null);
    try {
      setRecords(await fetchLedger());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load ledger.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey]);

  const hasSynthetic = records.some((r) => r.source === "Synthetic");

  return (
    <section>
      <div className="ledger-header">
        <h2>Ledger</h2>
        <button onClick={load} disabled={isLoading}>
          {isLoading ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {hasSynthetic && (
        <p className="synthetic-banner">
          Rows marked <strong>Synthetic</strong> are generated sample data used to seed the
          anomaly baseline — not real vendor spend.
        </p>
      )}

      {error && <p className="error-text">{error}</p>}

      <table className="ledger-table">
        <thead>
          <tr>
            <th>Vendor</th>
            <th>Invoice #</th>
            <th>Date</th>
            <th>Total</th>
            <th>Category</th>
            <th>Status</th>
            <th>Reviewed By</th>
            <th>Source</th>
          </tr>
        </thead>
        <tbody>
          {records.map((record) => (
            <tr
              key={record.id}
              className={record.status === "Flagged" ? "row-flagged" : undefined}
              onClick={() => record.status !== "Clean" && setSelected(record)}
              style={{ cursor: record.status !== "Clean" ? "pointer" : "default" }}
            >
              <td>{record.vendor_name}</td>
              <td>{record.invoice_number}</td>
              <td>{record.invoice_date}</td>
              <td>${record.total.toFixed(2)}</td>
              <td>{record.category ?? "—"}</td>
              <td>
                <StatusBadge status={record.status} />
              </td>
              <td>{record.reviewed_by ?? "—"}</td>
              <td>{record.source === "Synthetic" ? <span className="muted">Synthetic</span> : "Real"}</td>
            </tr>
          ))}
          {records.length === 0 && !isLoading && (
            <tr>
              <td colSpan={8} className="muted">
                No invoices yet. Upload one to get started.
              </td>
            </tr>
          )}
        </tbody>
      </table>

      {selected && (
        <FlaggedItemDetail
          record={selected}
          onClose={() => setSelected(null)}
          onResolved={(updated) => {
            setRecords((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
            setSelected(null);
          }}
        />
      )}
    </section>
  );
}
