import { useRef, useState } from "react";
import { uploadInvoice } from "../api/client";
import type { ProcessInvoiceResult } from "../types";
import StatusBadge from "./StatusBadge";

type FileStatus = "pending" | "processing" | "done" | "error";

interface QueueItem {
  id: string;
  file: File;
  status: FileStatus;
  result?: ProcessInvoiceResult;
  error?: string;
}

const CONCURRENCY_LIMIT = 3;

async function runWithConcurrencyLimit<T>(
  items: T[],
  limit: number,
  worker: (item: T) => Promise<void>,
): Promise<void> {
  let next = 0;
  async function runner() {
    while (next < items.length) {
      const item = items[next];
      next += 1;
      await worker(item);
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, runner));
}

export default function UploadView({ onProcessed }: { onProcessed: () => void }) {
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function updateItem(id: string, patch: Partial<QueueItem>) {
    setQueue((prev) => prev.map((item) => (item.id === id ? { ...item, ...patch } : item)));
  }

  async function handleFilesSelected(fileList: FileList | null) {
    if (!fileList || fileList.length === 0) return;

    const newItems: QueueItem[] = Array.from(fileList).map((file) => ({
      id: `${file.name}-${file.size}-${crypto.randomUUID()}`,
      file,
      status: "pending",
    }));
    setQueue((prev) => [...prev, ...newItems]);
    setIsUploading(true);

    await runWithConcurrencyLimit(newItems, CONCURRENCY_LIMIT, async (item) => {
      updateItem(item.id, { status: "processing" });
      try {
        const result = await uploadInvoice(item.file);
        updateItem(item.id, { status: "done", result });
      } catch (err) {
        updateItem(item.id, {
          status: "error",
          error: err instanceof Error ? err.message : "Upload failed",
        });
      }
    });

    setIsUploading(false);
    onProcessed();
    if (inputRef.current) inputRef.current.value = "";
  }

  return (
    <section>
      <div className="upload-dropzone">
        <p>Upload one or more vendor invoices (PDF, PNG, JPG, WEBP).</p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept="application/pdf,image/png,image/jpeg,image/webp"
          disabled={isUploading}
          onChange={(e) => handleFilesSelected(e.target.files)}
        />
      </div>

      {queue.length > 0 && (
        <table className="upload-table">
          <thead>
            <tr>
              <th>File</th>
              <th>Status</th>
              <th>Result</th>
            </tr>
          </thead>
          <tbody>
            {queue.map((item) => (
              <tr key={item.id}>
                <td>{item.file.name}</td>
                <td>
                  {item.status === "pending" && <span className="muted">Pending…</span>}
                  {item.status === "processing" && <span className="muted">Processing…</span>}
                  {item.status === "done" && item.result && (
                    <StatusBadge status={item.result.status} />
                  )}
                  {item.status === "error" && <span className="error-text">Error</span>}
                </td>
                <td>
                  {item.status === "done" && item.result && (
                    <span>
                      {item.result.extraction.vendor_name} — $
                      {item.result.validation.recomputed_total.toFixed(2)}
                      {item.result.status === "Flagged" && (
                        <span className="muted"> ({item.result.flag_reasons.length} reason(s))</span>
                      )}
                    </span>
                  )}
                  {item.status === "error" && <span className="error-text">{item.error}</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
