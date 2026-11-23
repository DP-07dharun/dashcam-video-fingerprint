import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { FileDrop } from "../components/FileDrop";
import { HashStrip } from "../components/Timeline";
import { Alert, Hash, KeyValue, Progress, SignatureBadge } from "../components/ui";
import { formatBytes, formatDuration } from "../format";
import type { FingerprintDetail } from "../types";

export function Register() {
  const [file, setFile] = useState<File | null>(null);
  const [claim, setClaim] = useState("");
  const [policy, setPolicy] = useState("");
  const [plate, setPlate] = useState("");
  const [notes, setNotes] = useState("");
  const [progress, setProgress] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<FingerprintDetail | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!file || !claim.trim()) return;
    setBusy(true);
    setError(null);
    setResult(null);
    setProgress(0);
    try {
      const record = await api.register(
        { file, claim_reference: claim.trim(), policy_number: policy, vehicle_plate: plate, notes },
        (pct) => setProgress(pct < 100 ? pct : null),
      );
      setResult(record);
      setFile(null);
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
          <h1>Register original footage</h1>
          <p className="muted">
            Create a signed fingerprint for the dashcam video as first received for a claim.
          </p>
        </div>
      </header>

      <div className="grid grid--2 grid--top">
        <form className="card form" onSubmit={submit}>
          <FileDrop file={file} onChange={setFile} disabled={busy} />
          <div className="field">
            <label htmlFor="claim">Claim reference *</label>
            <input
              id="claim"
              value={claim}
              onChange={(e) => setClaim(e.target.value)}
              placeholder="CLM-2026-00123"
              maxLength={64}
              required
              disabled={busy}
            />
          </div>
          <div className="row">
            <div className="field">
              <label htmlFor="policy">Policy number</label>
              <input
                id="policy"
                value={policy}
                onChange={(e) => setPolicy(e.target.value)}
                placeholder="POL-778812"
                maxLength={64}
                disabled={busy}
              />
            </div>
            <div className="field">
              <label htmlFor="plate">Vehicle plate</label>
              <input
                id="plate"
                value={plate}
                onChange={(e) => setPlate(e.target.value)}
                placeholder="AB-123-CD"
                maxLength={32}
                disabled={busy}
              />
            </div>
          </div>
          <div className="field">
            <label htmlFor="notes">Notes</label>
            <textarea
              id="notes"
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Rear-end collision, A13 exit 4, footage sent by policyholder"
              maxLength={2000}
              disabled={busy}
            />
          </div>
          {busy && (
            <Progress
              value={progress}
              label={progress === null ? "Fingerprinting video on the server…" : `Uploading ${progress}%`}
            />
          )}
          {error && <Alert>{error}</Alert>}
          <button className="btn btn--primary" disabled={!file || !claim.trim() || busy}>
            {busy ? "Working…" : "Create fingerprint"}
          </button>
        </form>

        <div className="card">
          {result ? (
            <>
              <div className="card__head">
                <h2>Fingerprint certificate</h2>
                <SignatureBadge valid={result.signature_valid} />
              </div>
              <Alert tone="ok">
                Registered for claim <strong>{result.claim_reference}</strong>.{" "}
                <Link to={`/records/${result.id}`}>Open record →</Link>
              </Alert>
              <KeyValue
                items={[
                  ["Record ID", <Hash value={result.id} />],
                  ["File", `${result.original_filename} · ${formatBytes(result.file_size_bytes)}`],
                  [
                    "Video",
                    `${formatDuration(result.duration_s)} · ${result.width}×${result.height} · ${result.fps} fps`,
                  ],
                  ["SHA-256", <Hash value={result.sha256} />],
                  ["Perceptual digest", <Hash value={result.perceptual_digest} />],
                  ["HMAC signature", <Hash value={result.signature} />],
                ]}
              />
              <h3 className="mt">
                {result.frame_hashes.length} frame hashes{" "}
                <span className="muted small">(one every {result.sample_interval_s}s)</span>
              </h3>
              <HashStrip hashes={result.frame_hashes} />
            </>
          ) : (
            <div className="empty">
              <h2>What gets stored</h2>
              <ul className="list">
                <li>
                  <strong>SHA-256</strong> of the exact file — proves a bit-for-bit copy.
                </li>
                <li>
                  <strong>Perceptual hashes</strong> of a frame every 0.5 s — survive re-encoding,
                  resizing and compression, but change when the picture changes.
                </li>
                <li>
                  <strong>HMAC signature</strong> over the record — reveals edits made directly in
                  the database.
                </li>
                <li>
                  The video itself is <strong>not</strong> kept, which keeps storage small and
                  personal data out of the database.
                </li>
              </ul>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
