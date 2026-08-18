const STEPS = [
  {
    icon: "📄",
    title: "You upload an invoice",
    body: "A PDF or a photo of one — single file or a batch.",
  },
  {
    icon: "🔎",
    title: "Claude reads it",
    body: "Vendor, invoice number, line items, and totals come out as structured data.",
  },
  {
    icon: "🧮",
    title: "The math gets checked in code",
    body: "Totals are recomputed and compared against what's printed — never trusted blindly.",
  },
  {
    icon: "🚩",
    title: "It's weighed against history",
    body: "New vendor, unusual amount, duplicate, category spend trending up — combined signals, not one rule alone.",
  },
  {
    icon: "✅",
    title: "Clean invoices post automatically",
    body: "Flagged ones wait in the ledger with their reasons, for a human to approve or resolve.",
  },
];

export default function WhatIDo() {
  return (
    <section className="what-i-do">
      <h2>What this does</h2>
      <p className="what-i-do-lede">
        An agent that turns vendor invoices into a reviewed, running ledger — extracting the
        data, checking its own math, and flagging only what actually looks unusual.
      </p>
      <ol className="what-i-do-steps">
        {STEPS.map((step) => (
          <li key={step.title}>
            <span className="what-i-do-icon" aria-hidden="true">
              {step.icon}
            </span>
            <div>
              <strong>{step.title}</strong>
              <p>{step.body}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
