// TS mirrors of the backend Pydantic models (see backend/app/models/*.py).
// Keep in sync manually -- this is a small enough surface that a shared
// schema/codegen step isn't worth the setup for a v1 portfolio build.

export interface LineItem {
  description: string;
  quantity: number;
  unit_price: number;
  amount: number;
}

export interface InvoiceExtraction {
  vendor_name: string;
  invoice_number: string;
  invoice_date: string; // ISO date
  due_date: string | null;
  line_items: LineItem[];
  subtotal: number;
  tax: number;
  total: number;
  category: string | null;
}

export interface ValidationResult {
  recomputed_subtotal: number;
  recomputed_total: number;
  discrepancies: string[];
  math_mismatch: boolean;
}

export type LedgerStatus = "Clean" | "Flagged" | "Resolved";
export type RecordSource = "Real" | "Synthetic";

export interface ProcessInvoiceResult {
  invoice_id: string;
  extraction: InvoiceExtraction;
  validation: ValidationResult;
  status: LedgerStatus;
  flag_reasons: string[];
}

export interface LedgerRecord {
  id: string;
  vendor_name: string;
  invoice_number: string;
  invoice_date: string;
  total: number;
  category: string | null;
  status: LedgerStatus;
  flag_reasons: string[];
  reviewed_by: string | null;
  reviewed_date: string | null;
  source: RecordSource;
}
