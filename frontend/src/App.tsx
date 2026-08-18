import { useState } from "react";
import AuthGate from "./components/AuthGate";
import LedgerTable from "./components/LedgerTable";
import UploadView from "./components/UploadView";
import WhatIDo from "./components/WhatIDo";

type Tab = "upload" | "ledger";

function AppShell() {
  const [tab, setTab] = useState<Tab>("upload");
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-title">
          <span className="app-logo" aria-hidden="true">
            🧾
          </span>
          <div>
            <h1>Invoice Validation Agent</h1>
            <p className="app-subtitle">Extract, validate, and flag — automatically.</p>
          </div>
        </div>
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
          <>
            <WhatIDo />
            <UploadView onProcessed={() => setRefreshKey((k) => k + 1)} />
          </>
        ) : (
          <LedgerTable refreshKey={refreshKey} />
        )}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <AuthGate>
      <AppShell />
    </AuthGate>
  );
}
