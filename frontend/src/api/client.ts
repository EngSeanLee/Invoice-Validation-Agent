import type { LedgerRecord, ProcessInvoiceResult } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const PASSPHRASE_STORAGE_KEY = "iva_passphrase";

/** Thrown on a 401 -- the passphrase is missing/wrong. UI should show the gate again. */
export class AuthError extends Error {}

export function getStoredPassphrase(): string | null {
  return localStorage.getItem(PASSPHRASE_STORAGE_KEY);
}

export function setStoredPassphrase(value: string): void {
  localStorage.setItem(PASSPHRASE_STORAGE_KEY, value);
}

export function clearStoredPassphrase(): void {
  localStorage.removeItem(PASSPHRASE_STORAGE_KEY);
}

function authHeaders(): HeadersInit {
  const passphrase = getStoredPassphrase();
  return passphrase ? { "X-App-Passphrase": passphrase } : {};
}

async function parseErrorDetail(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body?.detail === "string") return body.detail;
  } catch {
    // fall through to a generic message
  }
  return `Request failed (${response.status})`;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (response.status === 401) {
    clearStoredPassphrase();
    throw new AuthError(await parseErrorDetail(response));
  }
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response));
  }
  return response.json();
}

/** Validates a passphrase against the backend. Also used to ask "is a
 * passphrase even required?" by checking with an empty string. */
export async function checkPassphrase(passphrase: string): Promise<{ required: boolean }> {
  const response = await fetch(`${API_BASE_URL}/api/auth/check`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ passphrase }),
  });
  if (response.status === 401) {
    throw new AuthError("Incorrect passphrase.");
  }
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response));
  }
  return response.json();
}

export async function uploadInvoice(file: File): Promise<ProcessInvoiceResult> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/invoices`, {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });
  return handleResponse<ProcessInvoiceResult>(response);
}

export async function fetchLedger(): Promise<LedgerRecord[]> {
  const response = await fetch(`${API_BASE_URL}/api/ledger`, { headers: authHeaders() });
  const body = await handleResponse<{ records: LedgerRecord[] }>(response);
  return body.records;
}

export async function resolveFlag(invoiceId: string, reviewer: string): Promise<LedgerRecord> {
  const response = await fetch(`${API_BASE_URL}/api/ledger/${invoiceId}/resolve`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ reviewer }),
  });
  return handleResponse<LedgerRecord>(response);
}
