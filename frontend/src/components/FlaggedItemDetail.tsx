import { useState } from "react";
import { AuthError, resolveFlag } from "../api/client";
import type { LedgerRecord } from "../types";

export default function FlaggedItemDetail({
  record,
  onResolved,
  onClose,
}: {
  record: LedgerRecord;
  onResolved: (updated: LedgerRecord) => void;
  onClose: () => void;
}) {
  const [reviewer, setReviewer] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleResolve() {
    if (!reviewer.trim()) {
      setError("Enter your name to resolve this item.");
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      const updated = await resolveFlag(record.id, reviewer.trim());
      onResolved(updated);
    } catch (err) {
      if (err instanceof AuthError) {
        window.location.reload();
        return;
      }
      setError(err instanceof Error ? err.message : "Failed to resolve.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>
          {record.vendor_name} — {record.invoice_number}
        </h3>
        <p className="muted">
          {record.invoice_date} · ${record.total.toFixed(2)} · {record.category ?? "Uncategorized"}
        </p>

        <h4>Flag reason(s)</h4>
        {record.flag_reasons.length === 0 ? (
          <p className="muted">No reasons recorded.</p>
        ) : (
          <ul>
            {record.flag_reasons.map((reason, i) => (
              <li key={i}>{reason}</li>
            ))}
          </ul>
        )}

        {record.status === "Flagged" ? (
          <div className="resolve-form">
            <label htmlFor="reviewer-name">Your name</label>
            <input
              id="reviewer-name"
              type="text"
              value={reviewer}
              onChange={(e) => setReviewer(e.target.value)}
              placeholder="e.g. Jordan Lee"
            />
            {error && <p className="error-text">{error}</p>}
            <div className="modal-actions">
              <button onClick={onClose} disabled={isSubmitting}>
                Cancel
              </button>
              <button className="primary" onClick={handleResolve} disabled={isSubmitting}>
                {isSubmitting ? "Resolving…" : "Mark resolved"}
              </button>
            </div>
          </div>
        ) : (
          <div className="modal-actions">
            <p className="muted">
              Resolved by {record.reviewed_by} on {record.reviewed_date}.
            </p>
            <button onClick={onClose}>Close</button>
          </div>
        )}
      </div>
    </div>
  );
}
