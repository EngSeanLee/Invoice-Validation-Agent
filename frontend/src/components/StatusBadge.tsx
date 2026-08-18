import type { LedgerStatus } from "../types";

const STATUS_CLASS: Record<LedgerStatus, string> = {
  Clean: "badge badge-clean",
  Flagged: "badge badge-flagged",
  Resolved: "badge badge-resolved",
};

export default function StatusBadge({ status }: { status: LedgerStatus }) {
  return <span className={STATUS_CLASS[status]}>{status}</span>;
}
