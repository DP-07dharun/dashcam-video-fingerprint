import { useState, type FormEvent, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { FileDrop } from "../components/FileDrop";
import { Timeline } from "../components/Timeline";
import { Alert, Hash, KeyValue, Progress, SignatureBadge, VerdictBadge } from "../components/ui";
import { formatDuration, formatPercent, VERDICT_INFO } from "../format";
import type { VerificationResult } from "../types";

type Mode = "identify" | "claim" | "record";

export function Verify() {
  const [params] = useSearchParams();
  const presetRecord = params.get("record") ?? "";
  const [mode, setMode] = useState<Mode>(presetRecord ? "record" : "identify");
  const [target, setTarget] = useState(presetRecord);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<VerificationResult | null>(null);

  const needsTarget = mode !== "identify";

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!file || (needsTarget && !target.trim())) return;
    setBusy(true);
    setError(null);
    setResult(null);
    setProgress(0);
    try {
      const res = await api.verify(
        file,
        mode === "record"
          ? { fingerprint_id: target.trim() }
          : mode === "claim"
            ? { claim_reference: target.trim() }
            : {},
        (pct) => setProgress(pct < 100 ? pct : null),
      );
      setResult(res);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
      setProgress(null);
    }
  }

  return (
    <>
      <header className="page-head">
        <div>
          <h1>Verify submitted footage</h1>
          <p className="muted">
            Check whether a video sent with a claim matches the registered original.
          </p>
        </div>
      </header>

      <div className="grid grid--2 grid--top">
        <form className="card form" onSubmit={submit}>
          <fieldset className="segmented" disabled={busy}>
            <legend>Compare against</legend>
            {(
              [
                ["identify", "Any registered video"],
                ["claim", "A claim"],
                ["record", "A record ID"],
              ] as [Mode, string][]
            ).map(([value, label]) => (
              <label key={value} className={mode === value ? "active" : undefined}>
                <input
                  type="radio"
                  name="mode"
                  value={value}
                  checked={mode === value}
                  onChange={() => setMode(value)}
                />
                {label}
              </label>
            ))}
          </fieldset>
          {needsTarget && (
            <div className="field">
              <label htmlFor="target">{mode === "claim" ? "Claim reference" : "Record ID"}</label>
              <input
                id="target"
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                placeholder={mode === "claim" ? "CLM-2026-00123" : "e.g. 3f1c…"}
                required
                disabled={busy}
              />
            </div>
          )}
          <FileDrop file={file} onChange={setFile} disabled={busy} label="Submitted video" />
          {busy && (
            <Progress
              value={progress}
              label={progress === null ? "Fingerprinting and comparing…" : `Uploading ${progress}%`}
            />
          )}
          {error && <Alert>{error}</Alert>}
          <button
            className="btn btn--primary"
            disabled={!file || busy || (needsTarget && !target.trim())}
          >
            {busy ? "Verifying…" : "Verify video"}
          </button>
        </form>

        <div className="card">
          {result ? <ResultView result={result} /> : <VerdictGuide />}
        </div>
      </div>
    </>
  );
}

function ResultView({ result }: { result: VerificationResult }) {
  const c = result.comparison;
  const m = result.matched_fingerprint;
  const tone = VERDICT_INFO[result.verdict].tone;
  return (
    <>
      <div className={`verdict verdict--${tone}`}>
        <div>
          <VerdictBadge verdict={result.verdict} />
          <p>{result.message}</p>
        </div>
        <div className="verdict__score">
          <span>{formatPercent(result.similarity)}</span>
          <small>similarity</small>
        </div>
      </div>

      {result.record_signature_valid === false && (
        <Alert>
          The stored fingerprint record failed its signature check — someone changed it after
          registration. Treat this result as unreliable.
        </Alert>
      )}

      {c && c.reference_samples > 0 && (
        <>
          <h3 className="mt">Frame-by-frame comparison</h3>
          <Timeline
            timeline={c.timeline}
            interval={m?.sample_interval_s ?? 0.5}
            segments={c.segments}
          />
          {c.segments.length > 0 && (
            <ul className="segments">
              {c.segments.map((s, i) => (
                <li key={i} className={`segments__item segments__item--${s.kind}`}>
                  <strong>{s.kind}</strong> {formatDuration(s.start_s)} → {formatDuration(s.end_s)}
                </li>
              ))}
            </ul>
          )}
        </>
      )}

      <KeyValue
        items={[
          ...(m
            ? ([
                [
                  "Matched record",
                  <Link to={`/records/${m.id}`}>
                    {m.claim_reference} · {m.original_filename}
                  </Link>,
                ],
                ["Record signature", <SignatureBadge valid={result.record_signature_valid} />],
              ] as [string, ReactNode][])
            : []),
          ...(c
            ? ([
                ["Matched samples", `${c.matched_samples} / ${c.reference_samples}`],
                ["Mean distance", c.mean_distance === null ? "—" : `${c.mean_distance} / 64 bits`],
                ["Timeline offset", `${c.offset_s}s`],
                ["Duration difference", `${c.duration_delta_s > 0 ? "+" : ""}${c.duration_delta_s}s`],
              ] as [string, ReactNode][])
            : []),
          ["Submitted SHA-256", <Hash value={result.uploaded_sha256} />],
        ]}
      />
    </>
  );
}

function VerdictGuide() {
  return (
    <div className="empty">
      <h2>Possible outcomes</h2>
      <ul className="list">
        <li>
          <VerdictBadge verdict="AUTHENTIC_EXACT" /> the same file, byte for byte.
        </li>
        <li>
          <VerdictBadge verdict="AUTHENTIC_REENCODED" /> same footage, but re-exported, compressed
          or resized (e.g. sent through a messaging app).
        </li>
        <li>
          <VerdictBadge verdict="TAMPERED" /> the footage is the registered clip, but some seconds
          were replaced, cut or added — the timeline shows where.
        </li>
        <li>
          <VerdictBadge verdict="NO_MATCH" /> not the registered footage.
        </li>
      </ul>
    </div>
  );
}
