import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Alert, StatCard, VerdictBadge } from "../components/ui";
import { formatDate, formatDuration, formatPercent } from "../format";
import type { Stats, VerificationLogItem } from "../types";

export function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [log, setLog] = useState<VerificationLogItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.stats(), api.verifications(undefined, 8)])
      .then(([s, l]) => {
        setStats(s);
        setLog(l);
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  const flagged = stats ? stats.verdicts.TAMPERED : 0;

  return (
    <>
      <header className="page-head">
        <div>
          <h1>Claims video integrity</h1>
          <p className="muted">
            Fingerprint dashcam footage when a claim is opened, then verify any copy submitted
            later — re-encodes pass, edits are caught and located.
          </p>
        </div>
        <div className="actions">
          <Link to="/register" className="btn">
            Register video
          </Link>
          <Link to="/verify" className="btn btn--primary">
            Verify video
          </Link>
        </div>
      </header>

      {error && <Alert>{error}</Alert>}

      <section className="grid grid--4">
        <StatCard label="Registered videos" value={stats?.fingerprints ?? "—"} />
        <StatCard
          label="Footage fingerprinted"
          value={stats ? formatDuration(stats.total_video_seconds) : "—"}
          hint="h:mm:ss"
        />
        <StatCard label="Verifications" value={stats?.verifications ?? "—"} />
        <StatCard
          label="Tampering detected"
          value={<span className={flagged ? "text-bad" : undefined}>{stats ? flagged : "—"}</span>}
        />
      </section>

      <section className="card">
        <div className="card__head">
          <h2>Recent verifications</h2>
          <Link to="/records" className="small">
            All records →
          </Link>
        </div>
        {log.length === 0 ? (
          <p className="muted">No verifications yet. Register an original, then verify a copy.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>When</th>
                  <th>Submitted file</th>
                  <th>Verdict</th>
                  <th className="num">Similarity</th>
                  <th>Record</th>
                </tr>
              </thead>
              <tbody>
                {log.map((v) => (
                  <tr key={v.id}>
                    <td className="nowrap">{formatDate(v.created_at)}</td>
                    <td className="truncate" title={v.uploaded_filename}>
                      {v.uploaded_filename}
                    </td>
                    <td>
                      <VerdictBadge verdict={v.verdict} />
                    </td>
                    <td className="num">{formatPercent(v.similarity)}</td>
                    <td>
                      {v.fingerprint_id ? (
                        <Link to={`/records/${v.fingerprint_id}`}>Open</Link>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="grid grid--3">
        <div className="card how">
          <span className="how__step">1</span>
          <h3>Register</h3>
          <p className="muted">
            The original clip is hashed (SHA-256) and a 64-bit perceptual hash is taken every half
            second. The record is HMAC-signed and stored in Supabase — the video itself is
            discarded.
          </p>
        </div>
        <div className="card how">
          <span className="how__step">2</span>
          <h3>Verify</h3>
          <p className="muted">
            A submitted copy is fingerprinted the same way and aligned with the original, frame
            sample by frame sample, tolerating trims at the start.
          </p>
        </div>
        <div className="card how">
          <span className="how__step">3</span>
          <h3>Decide</h3>
          <p className="muted">
            Exact copy, re-encoded but unchanged, tampered (with the exact seconds that differ), or
            no match — plus a check that the stored record itself was not edited.
          </p>
        </div>
      </section>
    </>
  );
}
