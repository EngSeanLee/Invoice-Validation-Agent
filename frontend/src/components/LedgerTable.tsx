import { useEffect, useState } from "react";
import { AuthError, fetchLedger } from "../api/client";
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
      if (err instanceof AuthError) {
        window.location.reload();
        return;
      }
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
  const cleanCount = records.filter((r) => r.status === "Clean").length;
  const flaggedCount = records.filter((r) => r.status === "Flagged").length;
  const resolvedCount = records.filter((r) => r.status === "Resolved").length;

  return (
    <section>
      <div className="ledger-header">
        <h2>Ledger</h2>
        <button onClick={load} disabled={isLoading}>
          {isLoading ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {records.length > 0 && (
        <div className="ledger-stats">
          <div className="stat-tile">
            <span className="stat-value">{records.length}</span>
            <span className="stat-label">Total</span>
          </div>
          <div className="stat-tile stat-clean">
            <span className="stat-value">{cleanCount}</span>
            <span className="stat-label">Clean</span>
          </div>
          <div className="stat-tile stat-flagged">
            <span className="stat-value">{flaggedCount}</span>
            <span className="stat-label">Flagged</span>
          </div>
          <div className="stat-tile stat-resolved">
            <span className="stat-value">{resolvedCount}</span>
            <span className="stat-label">Resolved</span>
          </div>
        </div>
      )}

      {hasSynthetic && (
        <p className="synthetic-banner">
          Rows marked <strong>Synthetic</strong> are generated sample data used to seed the
          anomaly baseline — not real vendor spend.
        </p>
      )}

      {error && <p className="error-text">{error}</p>}

      <div className="table-scroll">
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
          {records.length === 0 && isLoading && (
            <tr>
              <td colSpan={8} className="muted">
                Loading…
              </td>
            </tr>
          )}
          {records.length === 0 && !isLoading && (
            <tr>
              <td colSpan={8} className="empty-state">
                No invoices yet — head to the Upload tab to process your first one.
              </td>
            </tr>
          )}
        </tbody>
      </table>
      </div>

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
