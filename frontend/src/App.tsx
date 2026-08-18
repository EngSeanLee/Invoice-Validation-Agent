import { useState } from "react";
import LedgerTable from "./components/LedgerTable";
import UploadView from "./components/UploadView";

type Tab = "upload" | "ledger";

export default function App() {
  const [tab, setTab] = useState<Tab>("upload");
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    <div className="app">
      <header className="app-header">
        <h1>Invoice Validation Agent</h1>
        <nav className="tabs">
          <button
            className={tab === "upload" ? "tab active" : "tab"}
            onClick={() => setTab("upload")}
          >
            Upload
          </button>
          <button
            className={tab === "ledger" ? "tab active" : "tab"}
            onClick={() => setTab("ledger")}
          >
            Ledger
          </button>
        </nav>
      </header>

      <main>
        {tab === "upload" ? (
          <UploadView onProcessed={() => setRefreshKey((k) => k + 1)} />
        ) : (
          <LedgerTable refreshKey={refreshKey} />
        )}
      </main>
    </div>
  );
}
