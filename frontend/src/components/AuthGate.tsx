import { useEffect, useState } from "react";
import {
  checkPassphrase,
  clearStoredPassphrase,
  getStoredPassphrase,
  setStoredPassphrase,
} from "../api/client";

type GateState = "checking" | "open" | "locked";

/** Wraps the app in an optional shared-passphrase gate. If the backend has no
 * APP_PASSPHRASE configured, /api/auth/check reports required=false and this
 * renders children immediately -- local dev stays frictionless. */
export default function AuthGate({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<GateState>("checking");
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const stored = getStoredPassphrase();
    // Resolves (open) whether no passphrase is required at all, or the
    // stored one is correct; rejects (locked) if one is required and the
    // stored value is missing or wrong.
    checkPassphrase(stored ?? "")
      .then(() => setState("open"))
      .catch(() => {
        clearStoredPassphrase();
        setState("locked");
      });
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      await checkPassphrase(input);
      setStoredPassphrase(input);
      setState("open");
    } catch {
      setError("Incorrect passphrase.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (state === "checking") {
    return <div className="gate-screen" aria-busy="true" />;
  }

  if (state === "open") {
    return <>{children}</>;
  }

  return (
    <div className="gate-screen">
      <form className="gate-card" onSubmit={handleSubmit}>
        <div className="gate-icon">🔒</div>
        <h1>Invoice Validation Agent</h1>
        <p className="muted">This demo is passphrase-protected. Enter it to continue.</p>
        <input
          type="password"
          autoFocus
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Passphrase"
        />
        {error && <p className="error-text">{error}</p>}
        <button className="primary" type="submit" disabled={isSubmitting || !input}>
          {isSubmitting ? "Checking…" : "Enter"}
        </button>
      </form>
    </div>
  );
}
