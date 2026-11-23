import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { HashStrip } from "../components/Timeline";
import { Alert, Hash, KeyValue, SignatureBadge, VerdictBadge } from "../components/ui";
import { formatBytes, formatDate, formatDuration, formatPercent } from "../format";
import type { FingerprintDetail, VerificationLogItem } from "../types";

export function RecordDetail() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const [record, setRecord] = useState<FingerprintDetail | null>(null);
  const [history, setHistory] = useState<VerificationLogItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.getFingerprint(id), api.verifications(id, 50)])
      .then(([r, h]) => {
        setRecord(r);
        setHistory(h);
      })
      .catch((e: Error) => setError(e.message));
  }, [id]);

  async function remove() {
    if (!record || !confirm(`Delete the fingerprint for claim ${record.claim_reference}?`)) return;
    try {
      await api.deleteFingerprint(record.id);
      navigate("/records");
    } catch (e) {
      setError((e as Error).message);
    }
  }

  if (error) return <Alert>{error}</Alert>;
  if (!record) return <p className="muted">Loading…</p>;

  return (
    <>
      <header className="page-head">
        <div>
          <p className="small">
            <Link to="/records">← Records</Link>
          </p>
          <h1>Claim {record.claim_reference}</h1>
          <p className="muted">
            {record.original_filename} · registered {formatDate(record.created_at)}
          </p>
        </div>
        <div className="actions">
          <button className="btn btn--danger" onClick={remove}>
            Delete
          </button>
          <Link to={`/verify?record=${record.id}`} className="btn btn--primary">
            Verify a copy
          </Link>
        </div>
      </header>

      {!record.signature_valid && (
        <Alert>
          This record's HMAC signature does not match its contents: it was modified after
          registration.
        </Alert>
      )}

      <div className="grid grid--2 grid--top">
        <div className="card">
          <div className="card__head">
            <h2>Fingerprint</h2>
            <SignatureBadge valid={record.signature_valid} />
          </div>
          <KeyValue
            items={[
              ["Record ID", <Hash value={record.id} />],
              ["Policy", record.policy_number ?? "—"],
              ["Vehicle plate", record.vehicle_plate ?? "—"],
              ["File size", formatBytes(record.file_size_bytes)],
              [
                "Video",
                `${formatDuration(record.duration_s)} · ${record.width}×${record.height} · ${record.fps} fps · ${record.frame_count} frames`,
              ],
              ["SHA-256", <Hash value={record.sha256} />],
              ["Perceptual digest", <Hash value={record.perceptual_digest} />],
              ["HMAC signature", <Hash value={record.signature} />],
              ...(record.notes ? ([["Notes", record.notes]] as [string, string][]) : []),
            ]}
          />
          <h3 className="mt">
            {record.frame_hashes.length} frame hashes{" "}
            <span className="muted small">(one every {record.sample_interval_s}s)</span>
          </h3>
          <HashStrip hashes={record.frame_hashes} />
          <details className="mt">
            <summary className="small">Show raw hashes</summary>
            <ol className="rawhashes">
              {record.frame_hashes.map((h, i) => (
                <li key={i}>
                  <span className="muted">{formatDuration(i * record.sample_interval_s)}</span>{" "}
                  <code>{h}</code>
                </li>
              ))}
            </ol>
          </details>
        </div>

        <div className="card">
          <h2>Verification history</h2>
          {history.length === 0 ? (
            <p className="muted">This record has not been checked against any submission yet.</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>When</th>
                    <th>File</th>
                    <th>Verdict</th>
                    <th className="num">Similarity</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((v) => (
                    <tr key={v.id}>
                      <td className="nowrap">{formatDate(v.created_at)}</td>
                      <td className="truncate truncate--sm" title={v.uploaded_filename}>
                        {v.uploaded_filename}
                      </td>
                      <td>
                        <VerdictBadge verdict={v.verdict} />
                      </td>
                      <td className="num">{formatPercent(v.similarity)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
