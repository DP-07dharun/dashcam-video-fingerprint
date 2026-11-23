import type { ReactNode } from "react";
import { VERDICT_INFO } from "../format";
import type { Verdict } from "../types";

export function VerdictBadge({ verdict }: { verdict: Verdict }) {
  const info = VERDICT_INFO[verdict];
  return <span className={`badge badge--${info.tone}`}>{info.label}</span>;
}

export function SignatureBadge({ valid }: { valid: boolean | null }) {
  if (valid === null) return <span className="badge badge--muted">No record</span>;
  return valid ? (
    <span className="badge badge--ok">Signature valid</span>
  ) : (
    <span className="badge badge--bad">Signature INVALID</span>
  );
}

export function StatCard({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="card stat">
      <span className="stat__label">{label}</span>
      <span className="stat__value">{value}</span>
      {hint && <span className="muted small">{hint}</span>}
    </div>
  );
}

export function Alert({ tone = "bad", children }: { tone?: "bad" | "warn" | "ok"; children: ReactNode }) {
  return (
    <div className={`alert alert--${tone}`} role={tone === "bad" ? "alert" : "status"}>
      {children}
    </div>
  );
}

export function Progress({ value, label }: { value: number | null; label: string }) {
  return (
    <div className="progress" aria-live="polite">
      <div className="progress__bar">
        <div
          className={`progress__fill ${value === null ? "progress__fill--busy" : ""}`}
          style={value === null ? undefined : { width: `${value}%` }}
        />
      </div>
      <span className="muted small">{label}</span>
    </div>
  );
}

export function KeyValue({ items }: { items: [string, ReactNode][] }) {
  return (
    <dl className="kv">
      {items.map(([k, v]) => (
        <div key={k} className="kv__row">
          <dt>{k}</dt>
          <dd>{v}</dd>
        </div>
      ))}
    </dl>
  );
}

export function Hash({ value }: { value: string }) {
  return (
    <code className="hash" title={value}>
      {value}
    </code>
  );
}
