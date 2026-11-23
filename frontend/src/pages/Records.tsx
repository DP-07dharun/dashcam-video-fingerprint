import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Alert } from "../components/ui";
import { formatBytes, formatDate, formatDuration, shortHash } from "../format";
import type { FingerprintPage } from "../types";

const PAGE = 15;

export function Records() {
  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<FingerprintPage | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const t = setTimeout(() => {
      setDebounced(query);
      setOffset(0);
    }, 250);
    return () => clearTimeout(t);
  }, [query]);

  useEffect(() => {
    let cancelled = false;
    api
      .listFingerprints(debounced, PAGE, offset)
      .then((p) => !cancelled && (setPage(p), setError(null)))
      .catch((e: Error) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [debounced, offset]);

  return (
    <>
      <header className="page-head">
        <div>
          <h1>Fingerprint records</h1>
          <p className="muted">Every registered original, newest first.</p>
        </div>
        <Link to="/register" className="btn btn--primary">
          Register video
        </Link>
      </header>

      <div className="card">
        <input
          type="search"
          className="search"
          placeholder="Search claim, policy, plate, filename or SHA-256…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Search records"
        />
        {error && <Alert>{error}</Alert>}
        {page && page.items.length === 0 && (
          <p className="muted">{debounced ? "No records match that search." : "No records yet."}</p>
        )}
        {page && page.items.length > 0 && (
          <>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Claim</th>
                    <th>Plate</th>
                    <th>File</th>
                    <th className="num">Length</th>
                    <th>SHA-256</th>
                    <th>Registered</th>
                  </tr>
                </thead>
                <tbody>
                  {page.items.map((r) => (
                    <tr key={r.id}>
                      <td>
                        <Link to={`/records/${r.id}`}>
                          <strong>{r.claim_reference}</strong>
                        </Link>
                        {r.policy_number && <div className="muted small">{r.policy_number}</div>}
                      </td>
                      <td>{r.vehicle_plate ?? <span className="muted">—</span>}</td>
                      <td className="truncate" title={r.original_filename}>
                        {r.original_filename}
                        <div className="muted small">{formatBytes(r.file_size_bytes)}</div>
                      </td>
                      <td className="num">{formatDuration(r.duration_s)}</td>
                      <td>
                        <code className="small">{shortHash(r.sha256, 8)}</code>
                      </td>
                      <td className="nowrap">{formatDate(r.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="pager">
              <span className="muted small">
                {offset + 1}–{offset + page.items.length} of {page.total}
              </span>
              <div className="actions">
                <button
                  className="btn btn--sm"
                  disabled={offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - PAGE))}
                >
                  Previous
                </button>
                <button
                  className="btn btn--sm"
                  disabled={offset + PAGE >= page.total}
                  onClick={() => setOffset(offset + PAGE)}
                >
                  Next
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </>
  );
}
