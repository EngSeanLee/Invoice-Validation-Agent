import type { LedgerRecord, ProcessInvoiceResult } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function parseErrorDetail(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body?.detail === "string") return body.detail;
  } catch {
    // fall through to a generic message
  }
  return `Request failed (${response.status})`;
}

export async function uploadInvoice(file: File): Promise<ProcessInvoiceResult> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/invoices`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await parseErrorDetail(response));
  }
  return response.json();
}

export async function fetchLedger(): Promise<LedgerRecord[]> {
  const response = await fetch(`${API_BASE_URL}/api/ledger`);
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response));
  }
  const body: { records: LedgerRecord[] } = await response.json();
  return body.records;
}

export async function resolveFlag(invoiceId: string, reviewer: string): Promise<LedgerRecord> {
  const response = await fetch(`${API_BASE_URL}/api/ledger/${invoiceId}/resolve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reviewer }),
  });

  if (!response.ok) {
    throw new Error(await parseErrorDetail(response));
  }
  return response.json();
}
